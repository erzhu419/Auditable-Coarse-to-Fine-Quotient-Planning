#!/usr/bin/env python3
"""Replay the frozen V28 histories selected by the V29 policy regression."""

import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import json
import math
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_frozen_policy_v27 import evaluate_frozen_policy
from acfqp.science.controlled_predictive_local_v21 import ARMS, evaluate_local_snapshot
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_restore_v22 import restore_state
from acfqp.science.controlled_predictive_snapshot_v21 import state_record, _replay_batch

PROTOCOL = Path('specs/CONTROLLED_PREDICTIVE_REGRESSION_V30.md')
DEFAULT_PLAN = Path('reports/controlled_predictive_regression_plan_v30.json')
DEFAULT_OUTPUT = Path('reports/controlled_predictive_regression_v30.json.gz')
TRACE_FIELDS = ('requested_batches', 'observed_batches', 'gap_assessments')


def _json(value):
    return json.loads(json.dumps(value, allow_nan=False))


def _key(value):
    return value[0], tuple(value[1])


def _validation(checks):
    return {'passed': all(checks.values()), 'checks': checks}


def _require(value, reason):
    if not value:
        raise ValueError(reason)


def _without_accounting(evaluation):
    return {k: v for k, v in evaluation.items() if k not in ('accounting', 'scope')}


def _policy_compact(evaluation):
    return {k: v for k, v in _without_accounting(evaluation).items()
            if k not in ('reachable_decisions', 'reachable_terminals', 'missing_policy_frontier')}


def _local_compact(evaluation):
    result = _without_accounting(evaluation)
    result['actions'] = {name: {k: v for k, v in row.items() if k != 'children'}
                         for name, row in result['actions'].items()}
    return result


def signed_margin(local, action, reference):
    """Qhat(action)-Qhat(reference); unknown empirical rows remain unknown."""
    a, b = local['actions'][action], local['actions'][reference]
    both = a['observed'] and b['observed']
    result = {'action': action, 'reference_action': reference, 'observed_both': both,
        'lower_difference': a['lower'] - b['lower'],
        'q_star_difference': a['q_star'] - b['q_star']}
    for field in ('q_hat', 'A_transition_error', 'D_continuation_error'):
        result[field + '_difference'] = a[field] - b[field] if both else None
    result['identity_residual'] = (result['q_hat_difference'] - result['q_star_difference'] - math.fsum((
        result['A_transition_error_difference'], result['D_continuation_error_difference']))) if both else None
    return result


def _evaluate_boundary(state, name, target, oracle, index, accounting):
    tick = perf_counter()
    stored = _json(state_record(state, name))
    accounting['boundary_materialization_seconds'] += perf_counter() - tick
    tick = perf_counter()
    policy = evaluate_frozen_policy(stored, list((target[0], list(target[1]))), state.queries[name], oracle)
    accounting['frozen_policy_evaluation_seconds'] += perf_counter() - tick
    accounting['frozen_policy_evaluation_calls'] += 1
    tick = perf_counter()
    local = evaluate_local_snapshot(state, name, target, oracle)
    accounting['local_decomposition_seconds'] += perf_counter() - tick
    accounting['local_decomposition_calls'] += 1
    accounting['diagnostic_clone_solve_seconds'] += local['accounting']['snapshot_clone_and_solve_seconds']
    reference = local['local_true_optimal_actions'][0]
    result = {'boundary_index': index, 'spent_batches': state.spent_batches,
              'policy_evaluation': _policy_compact(policy), 'local_evaluation': _local_compact(local),
              'selected_vs_reference': signed_margin(local, local['selected_action'], reference)}
    return result, _without_accounting(local), stored, policy


def _transition(before, after, tolerance, root=False):
    field = 'local_evaluation' if root else 'policy_evaluation'
    metric = 'local_regret' if root else 'total_regret'
    left, right = before[field][metric], after[field][metric]
    if left is None or right is None or (left <= tolerance) == (right <= tolerance):
        return None
    return {'from_boundary_index': before['boundary_index'], 'to_boundary_index': after['boundary_index'],
        'kind': 'CORRECT_TO_WRONG' if left <= tolerance else 'WRONG_TO_CORRECT',
        'previous_action': before['policy_evaluation']['initial_action'],
        'new_action': after['policy_evaluation']['initial_action'], 'regret_before': left, 'regret_after': right}


def _trigger(before, after, before_local, after_local, request, observed, target):
    action = after_local['selected_action']
    reference = after_local['local_true_optimal_actions'][0]
    return {'after_boundary_index': after['boundary_index'], 'request': request, 'observed': observed,
        'update_location': 'ROOT' if _key(request['row_key'][0]) == target else 'DOWNSTREAM',
        'previous_action': before_local['selected_action'], 'new_action': action,
        'reference_action': reference, 'before_margin': signed_margin(before_local, action, reference),
        'after_margin': signed_margin(after_local, action, reference),
        'before_new_vs_old_margin': signed_margin(before_local, action, before_local['selected_action']),
        'after_new_vs_old_margin': signed_margin(after_local, action, before_local['selected_action']),
        'before_local': before_local, 'after_local': after_local}


def replay_trajectory(prefix, endpoint, old_result, baseline, context, repetition, arm, oracle, tolerance=1e-10):
    """Retained requests control updates; selection calls only audit chronology."""
    started = perf_counter()
    local = endpoint['arms'][arm]['local']
    original = endpoint['arms'][arm]
    name, target = context['query_name'], _key(context['target_key'])
    query = Query(**prefix['state']['query'])
    identity = {k: v for k, v in context.items() if k not in ('target_key', 'requested_batch_count', 'initial_batches')}
    row = {**repetition, 'arm': arm, 'identity': identity, 'status': 'REPLAY_MISMATCH',
        'source_validation': {'passed': False}, 'prefix_validation': {'passed': False},
        'chronology_validation': {'passed': False}, 'endpoint_validation': {'passed': False},
        'original_costs': original['costs'], 'original_local_accounting': local['accounting'],
        'source_history': {field: local[field] for field in TRACE_FIELDS}, 'boundaries': [],
        'transitions': [], 'policy_transitions': [], 'first_harmful_update': None,
        'first_policy_harmful_update': None}
    accounting, chronology = Counter(), []
    state = None
    try:
        checks = {'identity': endpoint['identity'] == prefix['identity'] == identity,
            'replicate': all(endpoint[k] == v for k, v in repetition.items()),
            'target': endpoint['target_key'] == local['target_key'] == context['target_key'],
            'arm': local['arm'] == arm, 'query': local['query_name'] == name,
            'source_valid': endpoint['source_valid'] and original['source_valid'] and old_result['source_valid'],
            'prefix_valid': prefix['validation']['passed'] and baseline['source_valid'],
            'initial_batches': endpoint['initial_batches'] == local['initial_batches'] == context['initial_batches'],
            'requested_batches': endpoint['requested_batch_count'] == local['requested_batch_count'] == context['requested_batch_count'],
            'complete_budget': local['completed_fixed_budget'] and local['completed_batches'] == context['requested_batch_count'],
            'trace_lengths': all(len(local[field]) == context['requested_batch_count'] for field in TRACE_FIELDS),
            'original_costs': original['costs'] == old_result['costs'],
            'original_local': {k: v for k, v in local.items() if k not in TRACE_FIELDS} == old_result['local'],
            'physical_draws': local['actual_draws'] == 256 * local['completed_batches'] == local['provider_counts']['physical_draws']}
        row['source_validation'] = _validation(checks)
        _require(row['source_validation']['passed'], 'retained source binding differs')
        tick = perf_counter()
        state = restore_state(prefix['state'], {name: query}, query_name=name)
        accounting['prefix_restore_seconds'] += perf_counter() - tick
        accounting['prefix_restores'] += 1
        prefix_restored = _json(state_record(state, name))
        prefix_checks = {k: prefix_restored[k] == value for k, value in prefix['state'].items() if k != 'state_type'}
        state.__class__ = ARMS[arm]
        state.observe_state(target)
        boundary, previous_local, previous_stored, first_policy = _evaluate_boundary(state, name, target, oracle, 0, accounting)
        prefix_checks['policy_evaluation'] = _without_accounting(first_policy) == _without_accounting(baseline['evaluation'])
        row['prefix_validation'] = _validation(prefix_checks)
        _require(row['prefix_validation']['passed'], 'restored prefix state or value differs')
        row['boundaries'].append(boundary)
        for index, (request, observed, gap) in enumerate(zip(*(local[field] for field in TRACE_FIELDS))):
            tick = perf_counter()
            # Keep selection cache/cursor effects in their original order. The
            # resulting candidate is compared, never used to replace a request.
            probe = state.clone()
            diagnostic = _json(asdict(probe.assess_gap(target, name)))
            candidate = probe.select_row(target, name)
            kind = 'FIRST_OBSERVATION'
            if candidate is None:
                candidate = probe.select_resample(target, name, mode='BALANCED')
                kind = 'REPEAT_OBSERVATION'
            selected = {'row_key': _json(candidate), 'batch_index': probe.batch_counts.get(candidate, 0), 'kind': kind}
            counts = [round(weight * 256) for weight, _, _ in observed['outcomes']]
            checks = {'gap': diagnostic == gap, 'request': selected == request,
                'row': request['row_key'] == observed['row_key'],
                'index': request['batch_index'] == observed['batch_index'] == probe.batch_counts.get(candidate, 0),
                'integer_batch': sum(counts) == 256 and all(n > 0 and n / 256 == outcome[0]
                    for n, outcome in zip(counts, observed['outcomes']))}
            chronology.append({'request_index': index, **_validation(checks)})
            accounting['chronology_clone_and_selection_seconds'] += perf_counter() - tick
            accounting['chronology_selection_calls'] += 1
            _require(all(checks.values()), f'retained request/gap/batch differs at index {index}')
            _replay_batch(probe, request, observed, accounting)
            state = probe
            after, next_local, next_stored, _ = _evaluate_boundary(state, name, target, oracle, index + 1, accounting)
            before = row['boundaries'][-1]
            for root, transitions, trigger in ((True, 'transitions', 'first_harmful_update'),
                    (False, 'policy_transitions', 'first_policy_harmful_update')):
                event = _transition(before, after, tolerance, root)
                if event:
                    row[transitions].append(event)
                    if event['kind'] == 'CORRECT_TO_WRONG' and row[trigger] is None:
                        row[trigger] = _trigger(before, after, previous_local, next_local, request, observed, target)
                        row[trigger].update(before_state=previous_stored, after_state=next_stored)
            row['boundaries'].append(after)
            previous_local, previous_stored = next_local, next_stored
        tick = perf_counter()
        final = _json(state_record(state, name))
        final_policy = evaluate_frozen_policy(final, context['target_key'], query, oracle)
        accounting['endpoint_verification_seconds'] += perf_counter() - tick
        accounting['endpoint_verification_evaluation_calls'] += 1
        endpoint_checks = {k: final.get(k) == value for k, value in original['state'].items()}
        endpoint_checks.update(policy_evaluation=_without_accounting(final_policy) == _without_accounting(old_result['evaluation']),
            endpoint_action=final_policy['initial_action'] == local['final_action'],
            final_batch_count=state.spent_batches == local['final_batches'],
            complete_boundaries=len(row['boundaries']) == context['requested_batch_count'] + 1)
        row['endpoint_validation'] = _validation(endpoint_checks)
        _require(row['endpoint_validation']['passed'], 'replayed endpoint state or value differs')
        row['status'] = 'REPLAY_COMPLETE'
    except (ValueError, KeyError, TypeError, IndexError) as error:
        row['reason'] = str(error)
    row['chronology_validation'] = {'passed': len(chronology) == context['requested_batch_count'] and all(r['passed'] for r in chronology),
                                   'request_count': len(chronology), 'requests': chronology}
    accounting.update(new_provider_calls=0, new_sampling_calls=0, new_physical_draws=0, new_physical_batches=0)
    row['accounting'] = {**accounting, 'whole_trajectory_seconds': perf_counter() - started,
        'replay_engine_work_counts': dict(state.work_counts) if state is not None else {}}
    return row


def _read_json(path):
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as reader:
            return json.load(reader)
    return json.loads(path.read_text(encoding='utf-8'))


def run_regression(plan_path, output_path, progress=None):
    started = perf_counter()
    if output_path.exists():
        raise FileExistsError(f'V30 output already exists: {output_path}')
    plan = _read_json(plan_path)
    accounting = Counter()
    sources = {}
    for name in ('source_plan', 'source_prefixes', 'source_result', 'source_prefix_result', 'source_analysis'):
        tick = perf_counter()
        sources[name] = _read_json(Path(plan[name]))
        accounting[name + '_read_seconds'] += perf_counter() - tick
    context, board = plan['context'], plan['board']
    index = context['context_index']
    old_plan, old_result = sources['source_plan'], sources['source_result']
    expected_identity = {k: v for k, v in context.items() if k not in ('target_key', 'requested_batch_count', 'initial_batches')}
    checks = {'context': context in old_plan['contexts'], 'board': board in old_plan['boards'],
        'queries': plan['queries'] == old_plan['queries'], 'replicates': plan['replicates'] == old_plan['replicates'],
        'arms': plan['arms'] == old_plan['arms'], 'embedded_plan': old_result['plan'] == sources['source_prefixes']['plan'] == old_plan,
        'historical_draws': old_result['accounting']['total_physical_draws'] == plan['source_historical_physical_draws'],
        'historical_batches': old_result['accounting']['total_physical_batches'] == plan['source_historical_physical_batches']}
    selected_prefixes = [r for r in sources['source_prefixes']['query_starts'] if r['identity']['context_index'] == index]
    selected_baselines = [r for r in sources['source_prefix_result']['prefix_baselines'] if r['context_index'] == index]
    checks['one_prefix'] = len(selected_prefixes) == len(selected_baselines) == 1
    checks['baseline_identity'] = len(selected_baselines) == 1 and selected_baselines[0]['identity'] == expected_identity
    checks['requested_budget'] = context['requested_batch_count'] == plan['requested_batches']
    checks['batch_size'] = plan['samples_per_batch'] == 256
    checks['roster_size'] = plan['expected_trajectories'] == len(plan['replicates']) * len(plan['arms'])
    checks['boundary_count'] = plan['expected_boundaries_per_trajectory'] == plan['requested_batches'] + 1
    selected, records = {}, 0
    tick = perf_counter()
    with gzip.open(plan['source_endpoints'], 'rt', encoding='utf-8') as reader:
        for line in reader:
            endpoint = json.loads(line)
            records += 1
            if endpoint['identity']['context_index'] == index:
                selected.setdefault(endpoint['replicate_index'], []).append(endpoint)
    accounting['source_endpoint_stream_read_seconds'] = perf_counter() - tick
    accounting['source_endpoint_stream_reads'] = 1
    accounting['source_endpoint_pair_records_read'] = records
    accounting['source_endpoint_pair_records_selected'] = sum(map(len, selected.values()))
    checks['endpoint_roster'] = set(selected) == {r['replicate_index'] for r in plan['replicates']} and all(len(v) == 1 for v in selected.values())
    binding = _validation(checks)
    # The selected histories are bound before creating an evaluator-only oracle.
    tick = perf_counter()
    closure = build_development_closure(horizon=board['horizon'], max_nodes=30_000,
                                       boards={board['name']: tuple(board['board'])}) if binding['passed'] else None
    oracle = ExactOracle.from_closure(closure) if closure is not None else None
    accounting['exact_closure_and_oracle_seconds'] = perf_counter() - tick
    old_repetitions = {r['replicate_index']: r for r in old_result['repetitions']}
    trajectories = []
    for repetition in plan['replicates']:
        candidates = selected.get(repetition['replicate_index'], [])
        old_candidates = [r for r in old_repetitions[repetition['replicate_index']]['contexts'] if r['identity']['context_index'] == index]
        for arm in plan['arms']:
            if not binding['passed'] or len(candidates) != 1 or len(old_candidates) != 1:
                original = candidates[0]['arms'][arm] if len(candidates) == 1 else None
                compact = old_candidates[0]['arms'][arm] if len(old_candidates) == 1 else None
                retained = original if original is not None else compact
                row = {**repetition, 'arm': arm, 'identity': expected_identity, 'status': 'REPLAY_MISMATCH',
                    'source_validation': binding, 'reason': 'plan/source binding differs',
                    'prefix_validation': {'passed': False}, 'chronology_validation': {'passed': False, 'request_count': 0, 'requests': []},
                    'endpoint_validation': {'passed': False}, 'boundaries': [], 'transitions': [], 'policy_transitions': [],
                    'first_harmful_update': None, 'first_policy_harmful_update': None,
                    'original_costs': retained['costs'] if retained is not None else None,
                    'original_local_accounting': retained['local']['accounting'] if retained is not None else None,
                    'source_history': {field: original['local'][field] for field in TRACE_FIELDS} if original is not None else None,
                    'accounting': {'new_provider_calls': 0, 'new_sampling_calls': 0, 'new_physical_draws': 0,
                                   'retained_batches_replayed': 0, 'retained_draws_replayed': 0}}
            else:
                row = replay_trajectory(selected_prefixes[0], candidates[0], old_candidates[0]['arms'][arm],
                    selected_baselines[0], context, repetition, arm, oracle, plan['tolerance'])
            trajectories.append(row)
            if progress:
                progress({k: row[k] for k in ('replicate_index', 'arm', 'status')})
    for row in trajectories:
        accounting.update({k: v for k, v in row.get('accounting', {}).items() if isinstance(v, (float, int))})
    accounting.update(new_provider_calls=0, new_sampling_calls=0, new_physical_draws=0, new_physical_batches=0,
        historical_physical_draws=old_result['accounting']['total_physical_draws'],
        historical_physical_batches=old_result['accounting']['total_physical_batches'])
    report = {'schema': 'acfqp.controlled_predictive_regression.v30', 'plan': plan,
        'status': 'REGRESSION_REPLAY_COMPLETE' if all(row['status'] == 'REPLAY_COMPLETE' for row in trajectories) else 'REGRESSION_REPLAY_WITH_ISSUES',
        'plan_binding_validation': binding, 'trajectories': trajectories,
        'complete_trajectory_count': sum(row['status'] == 'REPLAY_COMPLETE' for row in trajectories),
        'original_source_accounting': old_result['accounting'], 'accounting': dict(accounting),
        'all_histories_bound_before_oracle': True, 'oracle_used_for_replay_selection': False,
        'scientific_gate': 'NOT_A_FORMAL_GATE', 'u006_assurance_started': False,
        'deferred_v2_24_case_cohort_executed': False,
        'elapsed_seconds_before_report_serialization': perf_counter() - started,
        'scope': 'Selected regression diagnosis on every retained suffix history for one fixed prefix. No new samples; original acquisition costs remain. Restoration, audit selections, retained updates and evaluator work are additional diagnostic costs. Nested stage times must not be added twice.'}
    tick = perf_counter()
    with gzip.open(output_path, 'xt', encoding='utf-8') as writer:
        json.dump(report, writer, separators=(',', ':'), allow_nan=False)
    return report, {'report_serialization_seconds': perf_counter() - tick, 'report_bytes': output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=DEFAULT_PLAN)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.plan.is_file():
        parser.error('the frozen V30 protocol and plan must exist before replay')
    report, serialization = run_regression(args.plan, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({'status': report['status'], 'complete_trajectory_count': report['complete_trajectory_count'],
                      'output': str(args.output), **serialization}), flush=True)


if __name__ == '__main__':
    main()
