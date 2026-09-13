#!/usr/bin/env python3
"""Compare a gap-specific H2 frontier against freshly rerun CACHED allocation."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_frozen_policy_v27 import evaluate_frozen_policy
from acfqp.science.controlled_predictive_gap_frontier_v31 import GapFrontierPlannerState
from acfqp.science.controlled_predictive_local_v21 import run_local_allocation, ARMS as LOCAL_ARMS
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_restore_v22 import restore_state
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
from acfqp.science.controlled_predictive_snapshot_v21 import state_record
from run_controlled_predictive_new_starts_v28 import _identity, _key, _validate_local, TRACE_FIELDS

PROTOCOL = Path('specs/CONTROLLED_PREDICTIVE_GAP_FRONTIER_V31.md')
DEFAULT_PLAN = Path('reports/controlled_predictive_gap_frontier_plan_v31.json')
DEFAULT_ENDPOINTS = Path('reports/controlled_predictive_gap_frontier_endpoints_v31.jsonl.gz')
DEFAULT_OUTPUT = Path('reports/controlled_predictive_gap_frontier_v31.json.gz')
ARMS = ('CACHED', 'GAP_FRONTIER')
IDENTITY_FIELDS = ('replicate_index', 'base_seed', 'identity', 'target_key', 'requested_batch_count', 'initial_batches')


def _validation(checks):
    return {'passed': all(checks.values()), 'checks': checks}


def _read(path):
    path = Path(path)
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as reader:
            return json.load(reader)
    return json.loads(path.read_text(encoding='utf-8'))


def _json(value):
    return json.loads(json.dumps(value, allow_nan=False))


def _budget_status(arms, requested):
    rows = [arms[arm]['local'] for arm in ARMS]
    counts = [row['completed_batches'] for row in rows]
    complete = all(n == requested and row['completed_fixed_budget'] for n, row in zip(counts, rows))
    shared_stop = counts[0] == counts[1] < requested and all(row['stop_reason'] == 'NO_ELIGIBLE_CANDIDATE' for row in rows)
    return {'budget_matched': complete or shared_stop, 'completed_K_pair': complete,
            'shared_normal_stop_pair': shared_stop, 'unequal_budget_pair': counts[0] != counts[1]}


def _reference_validation(current, source):
    left, right = current['arms']['CACHED'], source['arms']['CACHED']
    checks = {field: current[field] == source[field] for field in IDENTITY_FIELDS}
    checks.update({'state.' + field: left['state'].get(field) == value for field, value in right['state'].items()})
    checks.update({'local.' + field: left['local'].get(field) == value for field, value in right['local'].items() if field != 'accounting'})
    return _validation(checks)


def run_gap_frontier(plan_path, endpoints_path, output_path, progress=None):
    started = perf_counter()
    for path in (endpoints_path, output_path):
        if path.exists():
            raise FileExistsError(f'V31 output already exists: {path}')
    accounting = Counter()
    tick = perf_counter()
    plan = _read(plan_path)
    source_plan = _read(plan['source_plan'])
    prefixes = _read(plan['source_prefixes'])
    source_result = _read(plan['source_result'])
    accounting['source_plan_prefix_and_result_read_seconds'] = perf_counter() - tick
    fields = ('boards', 'contexts', 'queries', 'source_query_order', 'replicates', 'samples_per_batch',
              'prefix_batches_per_board', 'requested_batches_per_arm')
    checks = {field: plan[field] == source_plan[field] for field in fields}
    checks.update(arms=plan['arms'] == list(ARMS), embedded_plan=prefixes['plan'] == source_result['plan'] == source_plan,
        historical_batches=plan['source_historical_physical_batches'] == source_result['accounting']['total_physical_batches'],
        historical_draws=plan['source_historical_physical_draws'] == source_result['accounting']['total_physical_draws'])
    plan_binding = _validation(checks)
    if not plan_binding['passed']:
        raise ValueError('V31 frozen source plan binding differs before sampling')
    queries = {name: Query(**value) for name, value in plan['queries'].items()}
    prefix_lookup = {row['board_index']: row for row in prefixes['prefixes']}
    prepared = {row['identity']['context_index']: row for row in prefixes['query_starts']}
    historical_prepared = {row['identity']['context_index']: row for row in source_result['query_preparations']}
    snapshots, restoration_records = {}, []
    for context in plan['contexts']:
        index, name = context['context_index'], context['query_name']
        retained = prepared[index]
        tick = perf_counter()
        state = restore_state(retained['state'], {name: queries[name]}, query_name=name)
        seconds = perf_counter() - tick
        accounting['prefix_restore_seconds'] += seconds
        accounting['prefix_restores'] += 1
        rebuilt = _json(state_record(state, name))
        validation = _validation({**{field: rebuilt[field] == value for field, value in retained['state'].items()},
            'identity': retained['identity'] == _identity(context), 'prefix': prefix_lookup[context['board_index']]['validation']['passed'],
            'historical_prepare': retained['accounting'] == historical_prepared[index]['accounting'],
            'source_validation': retained['validation']['passed'], 'initial_batches': state.spent_batches == context['initial_batches'],
            'target': state.root == _key(context['target_key'])})
        restoration_records.append({'identity': _identity(context), 'validation': validation,
            'accounting': {'whole_seconds': seconds, 'work_counts': dict(state.work_counts)}})
        if not validation['passed']:
            raise ValueError(f'V31 prefix restoration differs for context {index} before sampling')
        snapshots[index] = state
    restore_lookup = {row['identity']['context_index']: row for row in restoration_records}
    providers, stages, work = ({arm: Counter() for arm in ARMS} for _ in range(3))
    LOCAL_ARMS['GAP_FRONTIER'] = GapFrontierPlannerState
    tick = perf_counter()
    writer = gzip.open(endpoints_path, 'xt', encoding='utf-8')
    accounting['endpoint_stream_open_seconds'] = perf_counter() - tick
    try:
        for repetition in plan['replicates']:
            for context in plan['contexts']:
                index, name = context['context_index'], context['query_name']
                snapshot = snapshots[index]
                order = ARMS if (repetition['replicate_index'] + index) % 2 == 0 else ARMS[::-1]
                pair = {**repetition, 'identity': _identity(context), 'target_key': context['target_key'],
                    'requested_batch_count': context['requested_batch_count'], 'initial_batches': context['initial_batches'],
                    'run_order': list(order), 'initial_snapshot_validation': restore_lookup[index]['validation'], 'arms': {}}
                for arm in order:
                    provider = BatchRowSampleProvider(repetition['base_seed'])
                    state, local = run_local_allocation(snapshot, arm, provider, name, _key(context['target_key']),
                                                        requested_batches=context['requested_batch_count'])
                    accounting['local_arm_run_count'] += 1
                    accounting['reset_from_prepared_query_count'] += 1
                    accounting['local_allocation_wall_seconds'] += local['accounting']['whole_run_seconds']
                    providers[arm].update(local['provider_counts'])
                    stages[arm].update(local['accounting']['seconds_by_stage'])
                    work[arm].update(local['accounting']['work_counts'])
                    tick = perf_counter()
                    local['repeat_batches_on_rows_absent_from_common'] = sum(request['kind'] == 'REPEAT_OBSERVATION' and
                        (_key(request['row_key'][0]), request['row_key'][1]) not in snapshot.rows for request in local['requested_batches'])
                    stored = state_record(state, name)
                    accounting['endpoint_materialization_seconds'] += perf_counter() - tick
                    validation = _validate_local(local, stored, context, arm)
                    costs = {'prefix_sampling_seconds': prefix_lookup[context['board_index']]['accounting']['whole_seconds'],
                        'single_query_prepare_seconds': historical_prepared[index]['accounting']['whole_seconds'],
                        'prefix_restore_seconds': restore_lookup[index]['accounting']['whole_seconds'],
                        'local_whole_run_seconds': local['accounting']['whole_run_seconds']}
                    costs['independent_query_seconds'] = sum(costs.values())
                    pair['arms'][arm] = {'state': stored, 'local': local, 'costs': costs,
                        'source_validation': validation, 'source_valid': validation['passed'],
                        'completed_requested_budget': local['completed_batches'] == context['requested_batch_count']}
                pair['source_valid'] = all(row['source_valid'] for row in pair['arms'].values())
                pair.update(_budget_status(pair['arms'], context['requested_batch_count']))
                tick = perf_counter()
                json.dump(pair, writer, separators=(',', ':'), allow_nan=False)
                writer.write('\n')
                accounting['endpoint_stream_write_seconds'] += perf_counter() - tick
                accounting['endpoint_pair_records_written'] += 1
            if progress:
                progress({'stage': 'SAMPLING', **repetition, 'pair_count': len(plan['contexts'])})
    finally:
        tick = perf_counter()
        writer.close()
        accounting['endpoint_stream_close_seconds'] += perf_counter() - tick
    del snapshots, prefixes
    oracles = {}
    for board in plan['boards']:
        tick = perf_counter()
        closure = build_development_closure(horizon=board['horizon'], max_nodes=30_000, boards={board['name']: tuple(board['board'])})
        oracles[board['board_index']] = ExactOracle.from_closure(closure)
        accounting['exact_closure_and_oracle_seconds'] += perf_counter() - tick
    source_lookup = {(rep['replicate_index'], row['identity']['context_index']): row
                     for rep in source_result['repetitions'] for row in rep['contexts']}
    repetitions = []
    with gzip.open(endpoints_path, 'rt', encoding='utf-8') as reader, gzip.open(plan['source_endpoints'], 'rt', encoding='utf-8') as reference_reader:
        accounting['source_endpoint_stream_reads'] += 1
        for repetition in plan['replicates']:
            result_rep = {**repetition, 'contexts': []}
            for context in plan['contexts']:
                tick = perf_counter()
                endpoint = json.loads(reader.readline())
                reference = json.loads(reference_reader.readline())
                accounting['endpoint_pair_records_reloaded'] += 1
                accounting['source_endpoint_pair_records_read'] += 1
                accounting['endpoint_and_reference_reload_seconds'] += perf_counter() - tick
                expected = {**repetition, 'identity': _identity(context), 'target_key': context['target_key'],
                    'requested_batch_count': context['requested_batch_count'], 'initial_batches': context['initial_batches']}
                aligned = all(endpoint[k] == value for k, value in expected.items())
                reproduction = _reference_validation(endpoint, reference)
                old = source_lookup[repetition['replicate_index'], context['context_index']]
                result = {k: v for k, v in endpoint.items() if k not in ('arms', 'replicate_index', 'base_seed')}
                result['arms'] = {}
                for arm, row in endpoint['arms'].items():
                    compact = {k: v for k, v in row.items() if k not in ('state', 'local')}
                    compact['local'] = {k: v for k, v in row['local'].items() if k not in TRACE_FIELDS}
                    validation = _validate_local(row['local'], row['state'], context, arm)
                    validation['checks'].update(endpoint_identity=aligned, prefix_restored=restore_lookup[context['context_index']]['validation']['passed'],
                        query_weights=row['state']['query'] == plan['queries'][context['query_name']])
                    validation['passed'] = all(validation['checks'].values())
                    compact.update(source_validation=validation, source_valid=validation['passed'], policy_evaluable=False,
                                   first_action_validation={'passed': False, 'reason': 'POLICY_NOT_EVALUATED'})
                    tick = perf_counter()
                    accounting['frozen_policy_evaluation_calls'] += 1
                    try:
                        evaluation = evaluate_frozen_policy(row['state'], context['target_key'], queries[context['query_name']], oracles[context['board_index']])
                    except ValueError as error:
                        compact['evaluation_validation'] = {'passed': False, 'reason': str(error)}
                    else:
                        compact.update(evaluation=evaluation, policy_evaluable=evaluation['policy_evaluable'], evaluation_validation={'passed': True})
                        compact['first_action_validation'] = _validation({field: evaluation[field] == row['local'][local_field] for field, local_field in (
                            ('initial_action', 'final_action'), ('lower', 'lower'), ('upper', 'upper'), ('selected_action_observed', 'selected_action_observed'))})
                    accounting['frozen_policy_evaluation_seconds'] += perf_counter() - tick
                    if arm == 'CACHED':
                        compact['reference_validation'] = reproduction
                        compact['reference_value_validation'] = _validation({field: compact.get('evaluation', {}).get(field) == value
                            for field, value in old['arms']['CACHED']['evaluation'].items() if field not in ('accounting', 'scope')})
                        compact['source_valid'] = compact['source_valid'] and reproduction['passed']
                    result['arms'][arm] = compact
                result['source_valid'] = aligned and all(row['source_valid'] for row in result['arms'].values())
                result.update(_budget_status(result['arms'], context['requested_batch_count']))
                result['policy_evaluable'] = all(row['policy_evaluable'] for row in result['arms'].values())
                result['paired_complete'] = result['source_valid'] and result['budget_matched'] and result['policy_evaluable'] and result['arms']['CACHED']['reference_value_validation']['passed'] and all(
                    row['first_action_validation']['passed'] and row['evaluation']['identities_pass'] and row['evaluation']['reach_probability_pass']
                    for row in result['arms'].values())
                result['status'] = 'PAIR_COMPLETE' if result['paired_complete'] else 'SOURCE_INVALID' if not result['source_valid'] else 'QUALITY_INCOMPLETE'
                result_rep['contexts'].append(result)
            result_rep.update(source_valid=all(row['source_valid'] for row in result_rep['contexts']),
                budget_matched=all(row['budget_matched'] for row in result_rep['contexts']),
                complete=all(row['paired_complete'] for row in result_rep['contexts']))
            result_rep['status'] = 'REPETITION_COMPLETE' if result_rep['complete'] else 'REPETITION_RETAINED_WITH_ISSUES'
            repetitions.append(result_rep)
            if progress:
                progress({'stage': 'EVALUATION', **repetition, 'complete': result_rep['complete']})
        stream_lengths_valid = not reader.readline() and not reference_reader.readline()
    batches = sum(row.get('row_requests', 0) for row in providers.values())
    draws = sum(row.get('physical_draws', 0) for row in providers.values())
    report = {'schema': 'acfqp.controlled_predictive_gap_frontier.v31', 'plan': plan,
        'status': 'GAP_FRONTIER_COMPLETE' if all(row['complete'] for row in repetitions) and stream_lengths_valid else 'GAP_FRONTIER_WITH_ISSUES',
        'plan_binding_validation': plan_binding, 'all_restorations_passed': all(r['validation']['passed'] for r in restoration_records),
        'restoration_records': restoration_records, 'prefixes': source_result['prefixes'], 'query_preparations': source_result['query_preparations'],
        'repetitions': repetitions, 'source_valid_repetition_count': sum(row['source_valid'] for row in repetitions),
        'complete_repetition_count': sum(row['complete'] for row in repetitions),
        'budget_counts': {key: sum(row[key] for rep in repetitions for row in rep['contexts']) for key in (
            'completed_K_pair', 'shared_normal_stop_pair', 'unequal_budget_pair')},
        'original_source_accounting': source_result['accounting'],
        'accounting': {**accounting, 'prefix_physical_batches': 0, 'prefix_physical_draws': 0,
            'local_physical_batches': batches, 'local_physical_draws': draws, 'total_physical_batches': batches, 'total_physical_draws': draws,
            'historical_physical_batches': source_result['accounting']['total_physical_batches'],
            'historical_physical_draws': source_result['accounting']['total_physical_draws'],
            'historical_plus_new_physical_draws': source_result['accounting']['total_physical_draws'] + draws,
            'provider_counts_by_arm': {arm: dict(value) for arm, value in providers.items()},
            'local_seconds_by_stage_by_arm': {arm: dict(value) for arm, value in stages.items()},
            'local_work_counts_by_arm': {arm: dict(value) for arm, value in work.items()}, 'endpoint_artifact_bytes': endpoints_path.stat().st_size},
        'source_and_new_endpoint_lengths_valid': stream_lengths_valid, 'all_prefix_restorations_before_sampling': True,
        'all_sampling_endpoints_closed_before_oracle': True, 'endpoint_evaluation_replanning_calls': 0,
        'endpoint_artifact': str(endpoints_path), 'elapsed_seconds_before_report_serialization': perf_counter() - started,
        'scientific_gate': 'NOT_A_FORMAL_GATE', 'u006_assurance_started': False,
        'original_deferred_24_case_cohort_loaded_or_executed': False,
        'scope': 'Two contemporaneous local allocations on fixed V28 prefixes and suffix seeds. CACHED regeneration is paid physical sampling. Historical prefix acquisition/preparation, current restoration and current local run are fully attributed per independent query; actual shared restorations occur once per context. Every endpoint is closed before evaluator truth construction; nested stages are not additive.'}
    tick = perf_counter()
    with gzip.open(output_path, 'xt', encoding='utf-8') as writer:
        json.dump(report, writer, separators=(',', ':'), allow_nan=False)
    return report, {'report_serialization_seconds': perf_counter() - tick, 'report_bytes': output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=DEFAULT_PLAN)
    parser.add_argument('--endpoints', type=Path, default=DEFAULT_ENDPOINTS)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.plan.is_file():
        parser.error('the frozen V31 protocol and plan must exist before sampling')
    report, serialization = run_gap_frontier(args.plan, args.endpoints, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({'status': report['status'], 'complete_repetition_count': report['complete_repetition_count'],
                      'output': str(args.output), **serialization}), flush=True)


if __name__ == '__main__':
    main()
