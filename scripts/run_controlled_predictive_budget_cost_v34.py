#!/usr/bin/env python3
"""Measure contemporary costs of the frozen V32 algorithms at five budgets."""

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
from acfqp.science.controlled_predictive_new_starts_v28 import acquire_common_prefix, prepare_query
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
from acfqp.science.controlled_predictive_snapshot_v21 import state_record
from run_controlled_predictive_new_starts_v28 import _identity, _key, _validate_local, TRACE_FIELDS
from run_controlled_predictive_gap_frontier_v31 import _budget_status
from run_controlled_predictive_budget_curve_v33 import _compact_evaluation

PROTOCOL = Path('specs/CONTROLLED_PREDICTIVE_BUDGET_COST_V34.md')
DEFAULT_PLAN = Path('reports/controlled_predictive_budget_cost_plan_v34.json')
DEFAULT_PREFIXES = Path('reports/controlled_predictive_budget_cost_prefixes_v34.json.gz')
DEFAULT_ENDPOINTS = Path('reports/controlled_predictive_budget_cost_endpoints_v34.jsonl.gz')
DEFAULT_OUTPUT = Path('reports/controlled_predictive_budget_cost_v34.json.gz')
ARMS = ('CACHED', 'GAP_FRONTIER')


def _read(path):
    path = Path(path)
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as reader:
            return json.load(reader)
    return json.loads(path.read_text(encoding='utf-8'))


def _json(value):
    return json.loads(json.dumps(value, allow_nan=False))


def _validation(checks):
    return {'passed': all(checks.values()), 'checks': checks}


def _history_validation(current, old, arm, budget):
    checks = {field: current[field] == old[field] for field in ('replicate_index', 'base_seed', 'identity', 'target_key', 'initial_batches')}
    fresh, source = current['arms'][arm]['local'], old['arms'][arm]['local']
    checks.update({'local.' + field: fresh[field] == source[field] for field in ('arm', 'query_name', 'target_key', 'initial_batches')})
    checks.update({field: fresh[field] == source[field][:budget] for field in TRACE_FIELDS})
    checks.update(source_valid=old['source_valid'] and old['arms'][arm]['source_valid'],
                  current_budget=fresh['requested_batch_count'] == budget, source_complete=source['completed_batches'] == 32)
    return _validation(checks)


def run_budget_cost(plan_path, prefixes_path, endpoints_path, output_path, progress=None):
    started = perf_counter()
    for path in (prefixes_path, endpoints_path, output_path):
        if path.exists():
            raise FileExistsError(f'V34 output already exists: {path}')
    accounting = Counter()
    tick = perf_counter()
    plan = _read(plan_path)
    source_plan = _read(plan['source_plan'])
    curve_plan = _read(plan['source_curve_plan'])
    retained = _read(plan['source_prefixes'])
    checks = {field: plan[field] == source_plan[field] == curve_plan[field] for field in (
        'boards', 'contexts', 'queries', 'source_query_order', 'replicates', 'arms', 'samples_per_batch',
        'prefix_batches_per_board', 'requested_batches_per_arm', 'selection_rule')}
    checks.update(prefix_plan=retained['plan'] == source_plan, budgets=plan['budgets'] == curve_plan['checkpoints'][1:] == [4, 8, 16, 24, 32],
        historical_batches=plan['source_historical_physical_batches'] == curve_plan['source_historical_physical_batches'],
        historical_draws=plan['source_historical_physical_draws'] == curve_plan['source_historical_physical_draws'])
    binding = _validation(checks)
    accounting['source_metadata_read_and_binding_seconds'] = perf_counter() - tick
    if not binding['passed']:
        raise ValueError('V34 frozen method/cohort/budget binding differs before acquisition')
    budgets = plan['budgets']
    queries = {name: Query(**value) for name, value in plan['queries'].items()}
    old_prefixes = {row['board_index']: row for row in retained['prefixes']}
    old_starts = {row['identity']['context_index']: row for row in retained['query_starts']}
    prefixes, preparations, snapshots = {}, {}, {}
    prefix_provider, preparation_work = Counter(), Counter()
    evidence = {'schema': 'acfqp.controlled_predictive_budget_cost_prefixes.v34', 'plan': plan,
                'prefixes': [], 'query_starts': [], 'local_acquisition_started': False, 'oracle_constructed': False}
    for board in plan['boards']:
        root = board['horizon'], tuple(board['board'])
        records, acquisition = acquire_common_prefix(root, board['prefix_seed'])
        validation = _validation({'fixed_batches': len(records) == plan['prefix_batches_per_board'],
            'legal_actions': acquisition['root_legal_actions'] == board['legal_actions'],
            'draws': acquisition['physical_draws'] == acquisition['provider_counts']['physical_draws'] == 256 * len(records),
            'reference_batches': records == old_prefixes[board['board_index']]['batches'],
            'reference_source_valid': old_prefixes[board['board_index']]['validation']['passed']})
        prefix = {'board_index': board['board_index'], 'name': board['name'], 'prefix_seed': board['prefix_seed'],
                  'accounting': acquisition, 'validation': validation}
        prefixes[board['board_index']] = prefix
        prefix_provider.update(acquisition['provider_counts'])
        accounting['prefix_acquisition_seconds'] += acquisition['whole_seconds']
        evidence['prefixes'].append({**prefix, 'batches': records})
        for context in (row for row in plan['contexts'] if row['board_index'] == board['board_index']):
            index, name = context['context_index'], context['query_name']
            state, preparation = prepare_query(root, name, queries[name], records)
            tick = perf_counter()
            stored = _json(state_record(state, name))
            checks = {'prefix_valid': validation['passed'], 'target': root == _key(context['target_key']),
                'identity': old_starts[index]['identity'] == _identity(context), 'reference_state': stored == old_starts[index]['state'],
                'reference_source_valid': old_starts[index]['validation']['passed'], 'single_query': list(state.queries) == [name],
                'initial_batches': state.spent_batches == context['initial_batches'] == plan['prefix_batches_per_board'],
                'no_preparation_sampling': preparation['new_provider_calls'] == preparation['new_physical_draws'] == 0}
            accounting['prefix_materialization_and_reference_seconds'] += perf_counter() - tick
            item = {'identity': _identity(context), 'accounting': preparation, 'validation': _validation(checks)}
            preparations[index], snapshots[index] = item, state
            accounting['single_query_preparation_seconds'] += preparation['whole_seconds']
            preparation_work.update(preparation['work_counts'])
            evidence['query_starts'].append({**item, 'state': stored})
        if progress:
            progress({'stage': 'PREFIX_AND_QUERY_PREPARATION', 'board_index': board['board_index']})
    tick = perf_counter()
    with gzip.open(prefixes_path, 'xt', encoding='utf-8') as writer:
        json.dump(evidence, writer, separators=(',', ':'), allow_nan=False)
    accounting['prefix_artifact_serialization_seconds'] = perf_counter() - tick
    del retained, evidence
    if not all(row['validation']['passed'] for row in preparations.values()):
        raise ValueError('V34 prefix reproduction failed; new physical prefix work is retained in the prefix artifact')
    providers, stages, work = ({arm: Counter() for arm in ARMS} for _ in range(3))
    LOCAL_ARMS['GAP_FRONTIER'] = GapFrontierPlannerState
    writer = gzip.open(endpoints_path, 'xt', encoding='utf-8')
    try:
        for repetition in plan['replicates']:
            for context in plan['contexts']:
                index, name = context['context_index'], context['query_name']
                offset = (repetition['replicate_index'] + index) % len(budgets)
                budget_order = budgets[offset:] + budgets[:offset]
                for budget in budget_order:
                    budget_index = budgets.index(budget)
                    order = ARMS if (repetition['replicate_index'] + index + budget_index) % 2 == 0 else ARMS[::-1]
                    current_context = {**context, 'requested_batch_count': budget}
                    pair = {**repetition, 'identity': _identity(context), 'target_key': context['target_key'],
                        'budget': budget, 'budget_index': budget_index, 'requested_batch_count': budget,
                        'initial_batches': context['initial_batches'], 'run_order': list(order), 'arms': {}}
                    snapshot = snapshots[index]
                    for arm in order:
                        provider = BatchRowSampleProvider(repetition['base_seed'])
                        state, local = run_local_allocation(snapshot, arm, provider, name, _key(context['target_key']), requested_batches=budget)
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
                        source_validation = _validate_local(local, stored, current_context, arm)
                        costs = {'prefix_sampling_seconds': prefixes[context['board_index']]['accounting']['whole_seconds'],
                            'single_query_prepare_seconds': preparations[index]['accounting']['whole_seconds'],
                            'local_whole_run_seconds': local['accounting']['whole_run_seconds']}
                        costs['independent_query_seconds'] = sum(costs.values())
                        pair['arms'][arm] = {'state': stored, 'local': local, 'costs': costs,
                            'source_validation': source_validation, 'source_valid': source_validation['passed']}
                    pair['source_valid'] = all(row['source_valid'] for row in pair['arms'].values())
                    pair.update(_budget_status(pair['arms'], budget))
                    tick = perf_counter()
                    json.dump(pair, writer, separators=(',', ':'), allow_nan=False)
                    writer.write('\n')
                    accounting['endpoint_stream_write_seconds'] += perf_counter() - tick
                    accounting['endpoint_pair_records_written'] += 1
            if progress:
                progress({'stage': 'SAMPLING', **repetition, 'budget_pair_count': len(plan['contexts']) * len(budgets)})
    finally:
        tick = perf_counter()
        writer.close()
        accounting['endpoint_stream_close_seconds'] += perf_counter() - tick
    del snapshots
    # Every physical run is complete and retained before any curve truth is read.
    tick = perf_counter()
    source_result = _read(plan['source_result'])
    curve_result = _read(plan['source_curve_result'])
    source_analysis = _read(plan['source_analysis'])
    accounting['reference_result_read_seconds'] = perf_counter() - tick
    reference_binding = _validation({'source_plan': source_result['plan'] == source_plan,
        'curve_plan': curve_result['plan'] == curve_plan,
        'source_analysis': source_analysis['all_analysis_checks_passed'],
        'historical_batches': plan['source_historical_physical_batches'] == curve_result['accounting']['historical_physical_batches'],
        'historical_draws': plan['source_historical_physical_draws'] == curve_result['accounting']['historical_physical_draws'],
        'no_curve_samples': curve_result['accounting']['new_physical_draws'] == 0})
    oracles = {}
    for board in plan['boards']:
        tick = perf_counter()
        closure = build_development_closure(horizon=board['horizon'], max_nodes=30_000, boards={board['name']: tuple(board['board'])})
        oracles[board['board_index']] = ExactOracle.from_closure(closure)
        accounting['exact_closure_and_oracle_seconds'] += perf_counter() - tick
    curve_lookup = {(rep['replicate_index'], row['identity']['context_index']): row for rep in curve_result['repetitions'] for row in rep['contexts']}
    repetitions = []
    with gzip.open(endpoints_path, 'rt', encoding='utf-8') as reader, gzip.open(plan['source_endpoints'], 'rt', encoding='utf-8') as old_reader, gzip.open(plan['source_curve_policies'], 'rt', encoding='utf-8') as policy_reader:
        accounting.update(source_endpoint_stream_reads=1, source_curve_policy_stream_reads=1)
        for repetition in plan['replicates']:
            result_rep = {**repetition, 'contexts': []}
            for context in plan['contexts']:
                tick = perf_counter()
                old = json.loads(old_reader.readline())
                policy_pair = json.loads(policy_reader.readline())
                accounting['source_endpoint_pair_records_read'] += 1
                accounting['source_curve_policy_pair_records_read'] += 1
                accounting['reference_stream_read_seconds'] += perf_counter() - tick
                index = context['context_index']
                offset = (repetition['replicate_index'] + index) % len(budgets)
                budget_order = budgets[offset:] + budgets[:offset]
                curve = curve_lookup[repetition['replicate_index'], index]
                context_result = {'identity': _identity(context), 'target_key': context['target_key'], 'budget_run_order': budget_order, 'budgets': []}
                by_budget = {}
                for budget in budget_order:
                    tick = perf_counter()
                    endpoint = json.loads(reader.readline())
                    accounting['endpoint_pair_records_reloaded'] += 1
                    accounting['endpoint_reload_read_seconds'] += perf_counter() - tick
                    expected = {**repetition, 'identity': _identity(context), 'target_key': context['target_key'], 'budget': budget,
                                'requested_batch_count': budget, 'initial_batches': context['initial_batches']}
                    aligned = all(endpoint[key] == value for key, value in expected.items())
                    policy_aligned = all(policy_pair[key] == expected[key] for key in ('replicate_index', 'base_seed', 'identity', 'target_key', 'initial_batches'))
                    result = {key: value for key, value in endpoint.items() if key not in ('arms', 'replicate_index', 'base_seed')}
                    result['arms'] = {}
                    for arm, row in endpoint['arms'].items():
                        compact = {key: value for key, value in row.items() if key not in ('state', 'local')}
                        compact['local'] = {key: value for key, value in row['local'].items() if key not in TRACE_FIELDS}
                        validation = _validate_local(row['local'], row['state'], {**context, 'requested_batch_count': budget}, arm)
                        validation['checks'].update(endpoint_identity=aligned, prefix_valid=preparations[index]['validation']['passed'])
                        validation['passed'] = all(validation['checks'].values())
                        history = _history_validation(endpoint, old, arm, budget)
                        reference_policy = next(record for record in policy_pair['arms'][arm] if record['budget'] == budget)
                        policy_checks = {'source_identity': policy_aligned,
                            'source_valid': curve['arms'][arm]['source_valid'],
                            'spent_batches': row['state']['spent_batches'] == reference_policy['spent_batches'],
                            'policy_and_intervals': row['state']['policy_and_intervals'] == reference_policy['policy_and_intervals'],
                            'observed_row_keys': row['state']['row_order'] == reference_policy['observed_row_keys']}
                        compact.update(source_validation=validation, reference_history_validation=history,
                            reference_policy_validation=_validation(policy_checks), policy_evaluable=False,
                            first_action_validation={'passed': False, 'reason': 'POLICY_NOT_EVALUATED'})
                        data_checks = [validation['passed'], history['passed'], compact['reference_policy_validation']['passed'], reference_binding['passed']]
                        if budget == 32:
                            state_checks = {key: row['state'].get(key) == value for key, value in old['arms'][arm]['state'].items()}
                            compact['reference_state_validation'] = _validation(state_checks)
                            data_checks.append(compact['reference_state_validation']['passed'])
                        compact['source_valid'] = all(data_checks)
                        checkpoint = next(cp for cp in curve['arms'][arm]['checkpoints'] if cp['budget'] == budget)
                        tick = perf_counter()
                        accounting['frozen_policy_evaluation_calls'] += 1
                        try:
                            evaluation = evaluate_frozen_policy(row['state'], context['target_key'], queries[context['query_name']], oracles[context['board_index']])
                        except ValueError as error:
                            compact['evaluation_validation'] = {'passed': False, 'reason': str(error)}
                            compact['reference_value_validation'] = {'passed': False, 'reason': 'POLICY_NOT_EVALUATED'}
                        else:
                            compact.update(evaluation=evaluation, policy_evaluable=evaluation['policy_evaluable'], evaluation_validation={'passed': True})
                            compact['first_action_validation'] = _validation({field: evaluation[field] == row['local'][other] for field, other in (
                                ('initial_action', 'final_action'), ('lower', 'lower'), ('upper', 'upper'), ('selected_action_observed', 'selected_action_observed'))})
                            compact['reference_value_validation'] = _validation({'source_evaluation': checkpoint['evaluation_validation']['passed'],
                                'values': _compact_evaluation(evaluation) == checkpoint.get('evaluation')})
                        accounting['frozen_policy_evaluation_seconds'] += perf_counter() - tick
                        result['arms'][arm] = compact
                    result['source_valid'] = all(row['source_valid'] for row in result['arms'].values())
                    result.update(_budget_status(result['arms'], budget))
                    result['policy_evaluable'] = all(row['policy_evaluable'] for row in result['arms'].values())
                    result['paired_complete'] = result['source_valid'] and result['budget_matched'] and result['policy_evaluable'] and all(
                        row['first_action_validation']['passed'] and row['reference_value_validation']['passed'] and row['evaluation']['identities_pass'] and row['evaluation']['reach_probability_pass']
                        for row in result['arms'].values())
                    result['status'] = 'PAIR_COMPLETE' if result['paired_complete'] else 'SOURCE_OR_QUALITY_INCOMPLETE'
                    by_budget[budget] = result
                context_result['budgets'] = [by_budget[budget] for budget in budgets]
                context_result['source_valid'] = all(row['source_valid'] for row in context_result['budgets'])
                context_result['complete'] = all(row['paired_complete'] for row in context_result['budgets'])
                result_rep['contexts'].append(context_result)
            result_rep.update(source_valid=all(row['source_valid'] for row in result_rep['contexts']),
                              complete=all(row['complete'] for row in result_rep['contexts']))
            repetitions.append(result_rep)
            if progress:
                progress({'stage': 'EVALUATION', **repetition, 'source_valid': result_rep['source_valid'], 'complete': result_rep['complete']})
        stream_complete = not reader.readline() and not old_reader.readline() and not policy_reader.readline()
    prefix_batches = sum(row['accounting']['physical_batches'] for row in prefixes.values())
    local_batches = sum(row.get('row_requests', 0) for row in providers.values())
    prefix_draws = sum(row['accounting']['physical_draws'] for row in prefixes.values())
    local_draws = sum(row.get('physical_draws', 0) for row in providers.values())
    report = {'schema': 'acfqp.controlled_predictive_budget_cost.v34', 'plan': plan,
        'status': 'BUDGET_COST_COMPLETE' if all(row['complete'] for row in repetitions) and stream_complete else 'BUDGET_COST_WITH_ISSUES',
        'plan_binding_validation': binding, 'reference_binding_validation': reference_binding,
        'prefixes': list(prefixes.values()), 'query_preparations': list(preparations.values()), 'repetitions': repetitions,
        'source_valid_repetition_count': sum(row['source_valid'] for row in repetitions), 'complete_repetition_count': sum(row['complete'] for row in repetitions),
        'original_source_accounting': source_result['accounting'], 'source_diagnostic_accounting': curve_result['accounting'],
        'accounting': {**accounting, 'prefix_board_count': len(prefixes), 'prepared_query_count': len(preparations),
            'prefix_physical_batches': prefix_batches, 'prefix_physical_draws': prefix_draws,
            'prefix_provider_counts': dict(prefix_provider), 'local_physical_batches': local_batches, 'local_physical_draws': local_draws,
            'total_physical_batches': prefix_batches + local_batches, 'total_physical_draws': prefix_draws + local_draws,
            'historical_physical_batches': plan['source_historical_physical_batches'], 'historical_physical_draws': plan['source_historical_physical_draws'],
            'historical_plus_new_physical_batches': plan['source_historical_physical_batches'] + prefix_batches + local_batches,
            'historical_plus_new_physical_draws': plan['source_historical_physical_draws'] + prefix_draws + local_draws,
            'independent_new_samples': 0, 'provider_counts_by_arm': {arm: dict(value) for arm, value in providers.items()},
            'local_seconds_by_stage_by_arm': {arm: dict(value) for arm, value in stages.items()},
            'local_work_counts_by_arm': {arm: dict(value) for arm, value in work.items()}, 'query_preparation_work_counts': dict(preparation_work),
            'prefix_artifact_bytes': prefixes_path.stat().st_size, 'endpoint_artifact_bytes': endpoints_path.stat().st_size},
        'all_prefix_snapshots_closed_before_local': True, 'all_sampling_endpoints_closed_before_oracle': True,
        'all_sampling_endpoints_closed_before_reference_values': True, 'source_and_new_endpoint_streams_complete': stream_complete,
        'endpoint_evaluation_replanning_calls': 0, 'prefix_artifact': str(prefixes_path), 'endpoint_artifact': str(endpoints_path),
        'elapsed_seconds_before_report_serialization': perf_counter() - started,
        'scientific_gate': 'NOT_A_FORMAL_GATE', 'u006_assurance_started': False, 'original_deferred_24_case_cohort_loaded_or_executed': False,
        'scope': 'Every budget/arm is freshly run from the same contemporary prepared prefix with its original suffix seed. All physical re-acquisitions are charged, including overlapping streams; these are not independent new samples. Current full prefix, preparation and local time form each independent-query cost. Historical chain and diagnostic work remain separate, with no proration. All acquisition ends before reference quality or evaluator truth is read.'}
    tick = perf_counter()
    with gzip.open(output_path, 'xt', encoding='utf-8') as writer:
        json.dump(report, writer, separators=(',', ':'), allow_nan=False)
    return report, {'report_serialization_seconds': perf_counter() - tick, 'report_bytes': output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=DEFAULT_PLAN)
    parser.add_argument('--prefixes', type=Path, default=DEFAULT_PREFIXES)
    parser.add_argument('--endpoints', type=Path, default=DEFAULT_ENDPOINTS)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.plan.is_file():
        parser.error('the frozen V34 protocol and plan must exist before acquisition')
    report, serialization = run_budget_cost(args.plan, args.prefixes, args.endpoints, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({'status': report['status'], 'complete_repetition_count': report['complete_repetition_count'],
                      'output': str(args.output), **serialization}), flush=True)


if __name__ == '__main__':
    main()
