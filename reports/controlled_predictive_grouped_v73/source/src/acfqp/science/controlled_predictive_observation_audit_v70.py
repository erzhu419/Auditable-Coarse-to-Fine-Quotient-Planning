"""Independently recover frozen contracts and check direct finite-domain routing.

This module reads saved exact kernels. It never calls the learned transition
rule, a game simulator, a ground closure builder, or an encoder compiler.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from time import perf_counter


def _decode(payload, work, prefix):
    cells = {state: (horizon, status) for state, horizon, status in payload['cells']}
    rows = defaultdict(dict)
    for state, action, atoms in payload['rows']:
        work[prefix + '_rows'] += 1
        converted = []
        for pn, pd, child, rn, rd in atoms:
            work[prefix + '_outcome_terms'] += 1
            probability = Fraction(pn, pd)
            if probability:
                converted.append((probability, child, Fraction(rn, rd)))
        rows[state][action] = tuple(converted)
    return cells, rows


def _signature(state, cells, rows, mapping=None):
    result = []
    for action, outcomes in sorted(rows[state].items()):
        mass = defaultdict(Fraction)
        for probability, child, reward in outcomes:
            target = child if mapping is None else mapping.get(child)
            if target is None:
                return None
            mass[target, reward] += probability
        result.append((action, tuple((child, reward, probability)
            for (child, reward), probability in sorted(mass.items()))))
    return (*cells[state], tuple(result))


def recover_mapping(full_payload, composed_payload):
    """Match every FULL joint row to saved COMPOSED contracts, with exact rationals."""
    started, work, errors = perf_counter(), Counter(), Counter()
    full_cells, full_rows = _decode(full_payload, work, 'full')
    composed_cells, composed_rows = _decode(composed_payload, work, 'composed')
    contracts, first = {}, None
    for state in composed_cells:
        signature = _signature(state, composed_cells, composed_rows)
        if signature in contracts:
            errors['duplicate_composed_contract'] += 1
            if first is None:
                first = dict(reason='duplicate_composed_contract', state=state)
        contracts[signature] = state
    mapping = {}
    for state in sorted(full_cells, key=lambda s: (full_cells[s][0], s)):
        work['full_state_contract_checks'] += 1
        signature = _signature(state, full_cells, full_rows, mapping)
        target = contracts.get(signature)
        if target is None:
            errors['unmatched_full_contract'] += 1
            if first is None:
                first = dict(reason='unmatched_full_contract', state=state,
                             horizon=full_cells[state][0])
        else:
            mapping[state] = target
            work['joint_rows_verified'] += len(full_rows[state])
    if tuple(mapping.get(s) for s in full_payload['roots']) != tuple(composed_payload['roots']):
        errors['root_mapping_difference'] += 1
        if first is None:
            first = dict(reason='root_mapping_difference')
    reached = set(mapping.values())
    if reached != set(composed_cells):
        errors['unrepresented_composed_cells'] += len(set(composed_cells) - reached)
    return dict(valid=not errors, mapping=mapping, full_states=len(full_cells),
        composed_states=len(composed_cells), errors=dict(errors), first_counterexample=first,
        counts=dict(work), elapsed_seconds=perf_counter() - started)


def audit(full_payload, composed_payload, routers, observations):
    """Check routers(board, horizon) on the entire retained active support.

    FULL_MAP returns FULL identifiers; COMPOSED_MAP and COMPOSED_DAG return
    COMPOSED identifiers. All routers return None for an unsupported observation.
    ``observations`` uses the V69 portable input fields expected/expected_full.
    """
    started = perf_counter()
    recovered = recover_mapping(full_payload, composed_payload)
    work = Counter(recovered['counts'])
    mapping = recovered['mapping']
    full_cells = {s: (h, status) for s, h, status in full_payload['cells']}
    retained, support_errors = {}, Counter()
    for horizon, board, state in full_payload['literal_boards']:
        key = horizon, tuple(board)
        if key in retained:
            support_errors['duplicate_literal_observation'] += 1
        retained[key] = state
        if full_cells.get(state) != (horizon, 'ACTIVE'):
            support_errors['literal_layer_or_status_difference'] += 1
    active_states = {s for s, (_, status) in full_cells.items() if status == 'ACTIVE'}
    if set(retained.values()) != active_states:
        support_errors['active_literal_coverage_difference'] += 1
    probes = []
    for horizon in sorted({h for h, _ in retained}):
        # A valid but unsupported active board. The probe tests refusal to
        # extrapolate; it is not a new task or a semantic generalization test.
        probe = next(((rank,) * 16 for rank in (3, 1, 2, 4, 5, 6, 7, 8, 9, 10)
                      if (horizon, (rank,) * 16) not in retained), None)
        if probe is not None:
            probes.append((horizon, probe))
    results = {}
    for name, router in routers.items():
        full_space = name == 'FULL_MAP'
        errors, first, by_horizon = Counter(), None, defaultdict(Counter)

        def compare(board, horizon, expected, kind):
            nonlocal first
            actual = router(tuple(board), horizon)
            work['router_' + name + '_' + kind] += 1
            if actual != expected:
                errors[kind] += 1
                if first is None:
                    first = dict(kind=kind, horizon=horizon, board=list(board),
                                 expected=expected, actual=actual)
            return actual == expected

        for (horizon, board), state in retained.items():
            expected = state if full_space else mapping.get(state)
            matches = compare(board, horizon, expected, 'retained_active_observation')
            by_horizon[str(horizon)]['observations'] += 1
            by_horizon[str(horizon)]['mismatches'] += int(not matches)
        for observation in observations:
            horizon, board = observation['horizon'], tuple(observation['board'])
            state = retained.get((horizon, board))
            expected = observation['expected_full' if full_space else 'expected']
            recovered_expected = state if full_space else mapping.get(state)
            if recovered_expected != expected:
                errors['portable_expected_differs_from_kernel'] += 1
            compare(board, horizon, expected, 'portable_observation')
        for horizon, board in probes:
            compare(board, horizon, None, 'unsupported_observation')
        results[name] = dict(valid=not errors, errors=dict(errors), first_counterexample=first,
            covered_observations=len(retained), portable_observations=len(observations),
            unsupported_observations=len(probes),
            by_horizon={h: dict(c) for h, c in sorted(by_horizon.items())})
    expected_routers = {'FULL_MAP', 'COMPOSED_MAP', 'COMPOSED_DAG'}
    if set(routers) != expected_routers:
        support_errors['missing_or_extra_router'] += 1
    valid = recovered['valid'] and not support_errors and all(r['valid'] for r in results.values())
    # Keep the large recovered mapping internal to this verification call.
    return dict(engineering_complete=True, valid=valid, routing_correct=valid,
        kernel_correspondence={k: v for k, v in recovered.items() if k != 'mapping'},
        support_errors=dict(support_errors), active_observations=len(retained),
        portable_observations=len(observations), routers=results,
        unsupported_probes=[dict(horizon=h, board=list(b)) for h, b in probes],
        counts=dict(work), elapsed_seconds=perf_counter() - started,
        scope='Exact routing on the retained finite active support only. Frozen V69 kernel and policy evidence can be inherited when artifact equality is established by the runner. Unsupported probes test rejection, not generalization. This audit performs no target dynamics acquisition, learning, planning, or future expansion.')
