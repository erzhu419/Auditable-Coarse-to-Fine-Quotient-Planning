"""Verify symbolic construction against retained exact kernels and observations.

The oracle is the saved FULL joint kernel, not the learned spawn classifier.
No board generation, ground dynamics, fitting, or planning occurs here.
"""
from collections import Counter
import importlib.util
from pathlib import Path
from time import perf_counter


def _saved_kernel_auditor():
    path = Path(__file__).with_name('controlled_predictive_observation_audit_v70.py')
    spec = importlib.util.spec_from_file_location('acfqp_v71_saved_kernel_audit', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit(full_payload, composed_payload, candidate_payload, candidate_labels, observations):
    """Check exact core identity, joint correspondence and active MAP support.

    Labels are ``[horizon, board, contract_cell]`` records emitted from the new
    construction's active encoding. They must cover exactly the old active
    observations. Terminal and H0 board encodings are intentionally unnecessary.
    """
    started = perf_counter()
    recovered = _saved_kernel_auditor().recover_mapping(full_payload, candidate_payload)
    work = Counter(recovered['counts'])
    errors, first = Counter(), None

    def fail(reason, **detail):
        nonlocal first
        errors[reason] += 1
        if first is None:
            first = dict(reason=reason, **detail)

    fields = sorted(set(composed_payload) | set(candidate_payload))
    differing_fields = [field for field in fields
        if field not in composed_payload or field not in candidate_payload
        or composed_payload[field] != candidate_payload[field]]
    for field in differing_fields:
        fail('frozen_core_field_difference', field=field)
    full_cells = {state: (horizon, status)
                  for state, horizon, status in full_payload['cells']}
    candidate_cells = {state: (horizon, status)
                       for state, horizon, status in candidate_payload['cells']}
    retained = {}
    for horizon, board, state in full_payload['literal_boards']:
        key = horizon, tuple(board)
        if key in retained:
            fail('duplicate_retained_observation', horizon=horizon, board=list(board))
        retained[key] = state
        if full_cells.get(state) != (horizon, 'ACTIVE'):
            fail('retained_layer_or_status_difference', state=state)
    if set(retained.values()) != {state for state, (_, status) in full_cells.items()
                                  if status == 'ACTIVE'}:
        fail('retained_active_coverage_difference')

    lookup = {}
    for horizon, board, state in candidate_labels:
        key = horizon, tuple(board)
        if key in lookup:
            fail('duplicate_candidate_observation', horizon=horizon, board=list(board))
        lookup[key] = state
        work['candidate_label_checks'] += 1
        if candidate_cells.get(state) != (horizon, 'ACTIVE'):
            fail('candidate_layer_or_status_difference', state=state, horizon=horizon)
    missing, extra = set(retained) - set(lookup), set(lookup) - set(retained)
    for horizon, board in sorted(missing):
        fail('missing_active_observation', horizon=horizon, board=list(board))
    for horizon, board in sorted(extra):
        fail('extra_active_observation', horizon=horizon, board=list(board))

    by_horizon, matched = {}, 0
    for (horizon, board), full_state in retained.items():
        expected = recovered['mapping'].get(full_state)
        actual = lookup.get((horizon, board))
        correct = expected is not None and actual == expected
        matched += int(correct)
        work['retained_active_route_checks'] += 1
        layer = by_horizon.setdefault(str(horizon), dict(observations=0, mismatches=0))
        layer['observations'] += 1
        layer['mismatches'] += int(not correct)
        if not correct:
            fail('active_route_difference', horizon=horizon, board=list(board),
                 expected=expected, actual=actual)
    portable_matched = 0
    for observation in observations:
        key = observation['horizon'], tuple(observation['board'])
        full_state = retained.get(key)
        expected = recovered['mapping'].get(full_state)
        if full_state != observation['expected_full'] or expected != observation['expected']:
            fail('portable_expectation_differs_from_kernel', horizon=key[0], board=list(key[1]))
        actual = lookup.get(key)
        correct = expected is not None and actual == expected
        portable_matched += int(correct)
        work['portable_route_checks'] += 1
        if not correct:
            fail('portable_route_difference', horizon=key[0], board=list(key[1]),
                 expected=expected, actual=actual)

    valid = recovered['valid'] and not errors
    return dict(engineering_complete=True, valid=valid,
        frozen_core_exact=not differing_fields, differing_core_fields=differing_fields,
        kernel_correspondence={k: v for k, v in recovered.items() if k != 'mapping'},
        errors=dict(errors), first_counterexample=first,
        active_observations=len(retained), candidate_observations=len(lookup),
        active_routes_matched=matched, missing_observations=len(missing), extra_observations=len(extra),
        portable_observations=len(observations), portable_routes_matched=portable_matched,
        by_horizon=by_horizon, counts=dict(work), elapsed_seconds=perf_counter() - started,
        scope='Exact saved-kernel correspondence and routing on the retained finite active support. '
              'V69 ground evidence is inherited only with frozen core and policy equality. '
              'No new target dynamics, planning, sampling, or generalization test is performed.')
