"""Audit local H1 encoding against retained complete exact joint kernels."""
from collections import Counter
import importlib.util
from pathlib import Path
from time import perf_counter


def _saved_kernel_auditor():
    path = Path(__file__).with_name('controlled_predictive_observation_audit_v70.py')
    spec = importlib.util.spec_from_file_location('acfqp_v72_saved_kernel_audit', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit(full_old, composed_old, candidate_payload, high_labels, h1_router, observations):
    """Check the frozen contract model, exact H>1 map and procedural H1 routes.

    ``high_labels`` contains [horizon, board, cell] records for H>1 ACTIVE
    observations only. ``h1_router(board)`` returns the candidate contract cell.
    The latter is evaluated on every retained H1 board, without a retained H1
    member lookup being provided to it by this verifier.
    """
    started = perf_counter()
    recovered = _saved_kernel_auditor().recover_mapping(full_old, candidate_payload)
    work, errors, first = Counter(recovered['counts']), Counter(), None

    def fail(reason, **detail):
        nonlocal first
        errors[reason] += 1
        if first is None:
            first = dict(reason=reason, **detail)

    fields = sorted(set(composed_old) | set(candidate_payload))
    different = [field for field in fields if field not in composed_old
        or field not in candidate_payload or composed_old[field] != candidate_payload[field]]
    for field in different:
        fail('frozen_core_field_difference', field=field)
    full_cells = {state: (h, status) for state, h, status in full_old['cells']}
    candidate_cells = {state: (h, status) for state, h, status in candidate_payload['cells']}
    retained = {}
    for h, board, state in full_old['literal_boards']:
        key = h, tuple(board)
        if key in retained:
            fail('duplicate_retained_observation', horizon=h, board=list(board))
        retained[key] = state
        if full_cells.get(state) != (h, 'ACTIVE'):
            fail('retained_layer_or_status_difference', state=state)
    if set(retained.values()) != {s for s, (_, status) in full_cells.items() if status == 'ACTIVE'}:
        fail('retained_active_coverage_difference')

    high_support = {key for key in retained if key[0] > 1}
    lookup = {}
    h1_labels = 0
    for h, board, state in high_labels:
        key = h, tuple(board)
        if key in lookup:
            fail('duplicate_high_observation', horizon=h, board=list(board))
        lookup[key] = state
        work['high_label_checks'] += 1
        if h <= 1:
            h1_labels += int(h == 1)
            fail('non_high_observation_label', horizon=h, board=list(board))
        if candidate_cells.get(state) != (h, 'ACTIVE'):
            fail('high_layer_or_status_difference', state=state, horizon=h)
    missing, extra = high_support - set(lookup), set(lookup) - high_support
    for h, board in sorted(missing):
        fail('missing_high_observation', horizon=h, board=list(board))
    for h, board in sorted(extra):
        fail('extra_high_observation', horizon=h, board=list(board))

    def route(board, h, kind):
        work[kind + ('_h1_procedural_calls' if h == 1 else '_high_map_lookups')] += 1
        return h1_router(board) if h == 1 else lookup.get((h, board))

    by_horizon, matched = {}, 0
    for (h, board), full_state in retained.items():
        expected = recovered['mapping'].get(full_state)
        actual = route(board, h, 'retained')
        correct = expected is not None and actual == expected
        matched += int(correct)
        layer = by_horizon.setdefault(str(h), dict(observations=0, mismatches=0))
        layer['observations'] += 1
        layer['mismatches'] += int(not correct)
        if not correct:
            fail('active_route_difference', horizon=h, board=list(board),
                 expected=expected, actual=actual)
    portable_matched = 0
    for observation in observations:
        h, board = observation['horizon'], tuple(observation['board'])
        full_state = retained.get((h, board))
        expected = recovered['mapping'].get(full_state)
        if full_state != observation['expected_full'] or expected != observation['expected']:
            fail('portable_expectation_differs_from_kernel', horizon=h, board=list(board))
        actual = route(board, h, 'portable')
        correct = expected is not None and actual == expected
        portable_matched += int(correct)
        if not correct:
            fail('portable_route_difference', horizon=h, board=list(board),
                 expected=expected, actual=actual)

    return dict(engineering_complete=True, valid=recovered['valid'] and not errors,
        frozen_core_exact=not different, differing_core_fields=different,
        kernel_correspondence={k: v for k, v in recovered.items() if k != 'mapping'},
        errors=dict(errors), first_counterexample=first,
        active_observations=len(retained), active_routes_matched=matched,
        high_observations=len(high_support), candidate_high_labels=len(lookup),
        candidate_h1_labels=h1_labels, missing_high_observations=len(missing),
        extra_high_observations=len(extra), h1_observations=sum(h == 1 for h, _ in retained),
        portable_observations=len(observations), portable_routes_matched=portable_matched,
        by_horizon=by_horizon, counts=dict(work), elapsed_seconds=perf_counter() - started,
        scope='Exact joint-kernel and procedural-route checks on frozen V69 active support. '
              'This verifier reads no new ground transitions and performs no fitting or planning. '
              'H1 board materialization and membership removal do not establish reduced mathematical '
              'spawn support, higher-horizon abstraction, or sample-efficient strategic learning.')
