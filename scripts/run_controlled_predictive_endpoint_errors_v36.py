#!/usr/bin/env python3
"""Attribute signed root action errors at every retained CACHED24/32 endpoint."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_frozen_policy_v27 import evaluate_frozen_policy
from acfqp.science.controlled_predictive_local_v21 import evaluate_local_snapshot
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_restore_v22 import restore_state
from acfqp.science.controlled_predictive_signed_errors_v25 import diagnose_target, _margin
from acfqp.science.controlled_predictive_snapshot_v21 import state_record
from run_controlled_predictive_new_starts_v28 import _identity, _key, _validate_local, TRACE_FIELDS
from run_controlled_predictive_budget_curve_v33 import _compact_evaluation

PROTOCOL = Path('specs/CONTROLLED_PREDICTIVE_ENDPOINT_ERRORS_V36.md')
DEFAULT_PLAN = Path('reports/controlled_predictive_endpoint_errors_plan_v36.json')
DEFAULT_OUTPUT = Path('reports/controlled_predictive_endpoint_errors_v36.json.gz')
CONFIGURATIONS = ('CACHED24', 'CACHED32')


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


def _require(value, reason):
    if not value:
        raise ValueError(reason)


def _local_compact(local):
    result = {key: value for key, value in local.items() if key not in ('accounting', 'scope')}
    result['actions'] = {name: {key: value for key, value in row.items() if key != 'children'}
                         for name, row in local['actions'].items()}
    return result


def _original_repetitions(repetitions):
    result = []
    for repetition in repetitions:
        current = {key: value for key, value in repetition.items() if key != 'contexts'}
        current['contexts'] = []
        for context in repetition['contexts']:
            row = {key: value for key, value in context.items() if key != 'configurations'}
            row['configurations'] = {}
            for name, config in context['configurations'].items():
                summary = {key: value for key, value in config.items() if key != 'evaluation'}
                if 'evaluation' in config:
                    summary['evaluation'] = _compact_evaluation(config['evaluation'])
                row['configurations'][name] = summary
            current['contexts'].append(row)
        result.append(current)
    return result


def diagnose_endpoint(source, old, context, configuration, oracle, exact_reference_action, aligned, query_definition):
    started = perf_counter()
    accounting = Counter()
    name = context['query_name']
    configured_context = {**context, 'requested_batch_count': configuration['budget']}
    row = {'configuration': configuration, 'source_valid': False, 'source_validation': {'passed': False},
        'restoration_validation': {'passed': False}, 'evaluation_validation': {'passed': False},
        'value_reproduction_validation': {'passed': False}, 'local_reproduction_validation': {'passed': False},
        'diagnostic_validation': {'passed': False}, 'diagnostic_available': False,
        'status': 'ENDPOINT_DIAGNOSTIC_INCOMPLETE', 'accounting': {}}
    state = None
    try:
        validation = _validate_local(source['local'], source['state'], configured_context, configuration['arm'])
        validation['checks'].update(identity=aligned, query_weights=source['state']['query'] == query_definition, configuration=source['configuration'] == old['configuration'] == configuration,
            old_source_valid=source['source_valid'] and old['source_valid'],
            retained_costs=source['costs'] == old['costs'],
            retained_local={key: value for key, value in source['local'].items() if key not in TRACE_FIELDS} == old['local'])
        validation['passed'] = all(validation['checks'].values())
        row['source_validation'] = validation
        _require(validation['passed'], 'retained endpoint source binding differs')
        tick = perf_counter()
        accounting['model_restore_calls'] += 1
        try:
            state = restore_state(source['state'], {name: Query(**query_definition)}, query_name=name)
        finally:
            accounting['model_restore_seconds'] += perf_counter() - tick
        tick = perf_counter()
        rebuilt = _json(state_record(state, name))
        row['restoration_validation'] = _validation({key: rebuilt.get(key) == value for key, value in source['state'].items()})
        accounting['restoration_validation_seconds'] += perf_counter() - tick
        _require(row['restoration_validation']['passed'], 'restored endpoint state differs')
        row['source_valid'] = True
        tick = perf_counter()
        accounting['frozen_policy_evaluation_calls'] += 1
        try:
            policy = evaluate_frozen_policy(source['state'], context['target_key'], state.queries[name], oracle)
        except ValueError as error:
            row['evaluation_validation'] = {'passed': False, 'reason': str(error)}
        else:
            row['policy_evaluation'] = _compact_evaluation(policy)
            row['evaluation_validation'] = {'passed': True}
            row['value_reproduction_validation'] = _validation({key: policy.get(key) == value for key, value in old.get('evaluation', {}).items()
                if key not in ('scope', 'accounting')})
            row['value_reproduction_validation']['checks']['source_evaluation'] = old.get('evaluation_validation', {}).get('passed') is True and bool(old.get('evaluation'))
            row['value_reproduction_validation']['passed'] = all(row['value_reproduction_validation']['checks'].values())
        accounting['frozen_policy_evaluation_seconds'] += perf_counter() - tick
        tick = perf_counter()
        accounting['local_decomposition_calls'] += 1
        local = evaluate_local_snapshot(state, name, _key(context['target_key']), oracle)
        accounting['local_decomposition_seconds'] += perf_counter() - tick
        accounting['diagnostic_clone_solve_seconds'] += local['accounting']['snapshot_clone_and_solve_seconds']
        row['local_evaluation'] = _local_compact(local)
        row['local_reproduction_validation'] = _validation({
            'selected_action': local['selected_action'] == source['local']['final_action'],
            'lower': local['lower'] == source['local']['lower'], 'upper': local['upper'] == source['local']['upper'],
            'selected_observed': local['selected_action_observed'] == source['local']['selected_action_observed'],
            'identities': local['identities_pass'],
            'exact_reference': exact_reference_action == min(local['actions'], key=lambda action: (-local['actions'][action]['q_star'], action))})
        _require(row['local_reproduction_validation']['passed'], 'root value/action reproduction differs')
        tick = perf_counter()
        diagnostic = diagnose_target(local)
        accounting['numeric_diagnosis_seconds'] += perf_counter() - tick
        accounting['numeric_diagnosis_calls'] += 1
        accounting['action_decompositions'] += sum(action['decomposable'] for action in diagnostic['actions'].values())
        diagnostic.pop('accounting')
        diagnostic.pop('scope')
        diagnostic['exact_reference_action'] = exact_reference_action
        diagnostic['selected_minus_reference'] = _margin(local['selected_action'], exact_reference_action, diagnostic['actions'])
        diagnostic['near_optimal_representative_scope'] = 'V25 true_optimal_representative uses the existing tolerance set; V36 signed reference uses exact_reference_action.'
        checks = {'v25_raw': diagnostic['validation']['all_passed'],
            'signed_true_margin_equals_negative_regret': diagnostic['selected_minus_reference']['q_star_difference'] == -local['local_regret'],
            'mode_set': set(diagnostic['modes']) == {'RAW', 'REMOVE_A', 'REMOVE_D'}}
        row['diagnostic'] = diagnostic
        row['diagnostic_validation'] = _validation(checks)
        row['diagnostic_available'] = all(mode['available'] for mode in diagnostic['modes'].values())
        if row['diagnostic_validation']['passed'] and row['diagnostic_available'] and row['value_reproduction_validation']['passed'] and all(
                row.get('policy_evaluation', {}).get(key) is True for key in ('policy_evaluable', 'identities_pass', 'reach_probability_pass')):
            row['status'] = 'ENDPOINT_DIAGNOSTIC_COMPLETE'
    except (ValueError, KeyError, TypeError, IndexError) as error:
        row['reason'] = str(error)
    accounting.update(new_provider_calls=0, new_sampling_calls=0, new_physical_draws=0, new_physical_batches=0)
    row['accounting'] = {**accounting, 'whole_endpoint_seconds': perf_counter() - started,
        'restored_engine_work_counts': dict(state.work_counts) if state is not None else {}}
    return row


def cross_budget_pair(before, after, tolerance):
    result = {'validation': {'passed': False}, 'available': False}
    if not all(row.get('diagnostic_validation', {}).get('passed') for row in (before, after)):
        result['reason'] = 'ENDPOINT_DECOMPOSITION_UNAVAILABLE'
        return result
    left = after['diagnostic']['original_selected_action']
    right = before['diagnostic']['original_selected_action']
    first = _margin(left, right, before['diagnostic']['actions'])
    last = _margin(left, right, after['diagnostic']['actions'])
    fields = ('q_hat_difference', 'q_star_difference', 'A_transition_error_difference', 'D_continuation_error_difference',
              'total_error_difference', 'raw_lower_difference', 'REMOVE_A_difference', 'REMOVE_D_difference')
    change = {field: last[field] - first[field] if first[field] is not None and last[field] is not None else None for field in fields}
    residual = (change['q_hat_difference'] - change['q_star_difference'] - change['A_transition_error_difference'] - change['D_continuation_error_difference']) if first['decomposable'] and last['decomposable'] else None
    checks = {'fixed_actions': first['actions'] == last['actions'] == [left, right],
        'same_exact_reference': before['diagnostic']['exact_reference_action'] == after['diagnostic']['exact_reference_action'],
        'same_true_values': all(before['diagnostic']['actions'][action]['q_star'] == after['diagnostic']['actions'][action]['q_star'] for action in first['actions']),
        'change_identity': residual is None or abs(residual) <= tolerance}
    result.update(actions=[left, right], before_margin=first, after_margin=last, change=change,
        change_identity_residual=residual, validation=_validation(checks), available=first['decomposable'] and last['decomposable'])
    return result


def run_endpoint_errors(plan_path, output_path, progress=None):
    started = perf_counter()
    if output_path.exists():
        raise FileExistsError(f'V36 output already exists: {output_path}')
    accounting = Counter()
    tick = perf_counter()
    plan = _read(plan_path)
    source_plan = _read(plan['source_plan'])
    source = _read(plan['source_result'])
    reference = _read(plan['source_analysis'])
    accounting['source_metadata_and_result_read_seconds'] = perf_counter() - tick
    checks = {field: plan[field] == source_plan[field] for field in (
        'boards', 'contexts', 'queries', 'source_query_order', 'replicates', 'configurations', 'samples_per_batch',
        'prefix_batches_per_board', 'selection_rule')}
    checks.update(source_plan=source['plan'] == source_plan, source_accounting=reference['accounting'] == source['accounting'],
        source_analysis=reference['all_analysis_checks_passed'], compared_configurations=plan['compared_configurations'] == list(CONFIGURATIONS),
        historical_batches=plan['source_historical_physical_batches'] == source['accounting']['historical_physical_batches'] + source['accounting']['total_physical_batches'],
        historical_draws=plan['source_historical_physical_draws'] == source['accounting']['historical_physical_draws'] + source['accounting']['total_physical_draws'])
    binding = _validation(checks)
    _require(binding['passed'], 'V36 frozen source binding differs before endpoint diagnosis')
    oracles = {}
    for board in plan['boards']:
        tick = perf_counter()
        closure = build_development_closure(horizon=board['horizon'], max_nodes=30_000, boards={board['name']: tuple(board['board'])})
        oracles[board['board_index']] = ExactOracle.from_closure(closure)
        accounting['exact_closure_and_oracle_seconds'] += perf_counter() - tick
    exact_references = {}
    for context in plan['contexts']:
        truth = oracles[context['board_index']].solution(Query(**plan['queries'][context['query_name']]))
        target = _key(context['target_key'])
        board = next(row for row in plan['boards'] if row['board_index'] == context['board_index'])
        exact_references[context['context_index']] = min(board['legal_actions'], key=lambda action: (-truth.q_values[target, action], action))
    source_lookup = {(rep['replicate_index'], row['identity']['context_index']): row for rep in source['repetitions'] for row in rep['contexts']}
    configuration_lookup = {row['name']: row for row in plan['configurations']}
    repetitions = []
    with gzip.open(plan['source_endpoints'], 'rt', encoding='utf-8') as reader:
        accounting['source_endpoint_stream_reads'] += 1
        for repetition in plan['replicates']:
            result_rep = {**repetition, 'contexts': []}
            for context in plan['contexts']:
                tick = perf_counter()
                endpoint = json.loads(reader.readline())
                accounting['source_endpoint_read_seconds'] += perf_counter() - tick
                accounting['source_endpoint_triple_records_read'] += 1
                old = source_lookup[repetition['replicate_index'], context['context_index']]
                expected = {**repetition, 'identity': _identity(context), 'target_key': context['target_key'], 'initial_batches': context['initial_batches']}
                aligned = all(endpoint[key] == value for key, value in expected.items())
                row = {'identity': _identity(context), 'target_key': context['target_key'], 'configurations': {}}
                for configuration_name in CONFIGURATIONS:
                    diagnosed = diagnose_endpoint(endpoint['configurations'][configuration_name], old['configurations'][configuration_name],
                        context, configuration_lookup[configuration_name], oracles[context['board_index']],
                        exact_references[context['context_index']], aligned, plan['queries'][context['query_name']])
                    row['configurations'][configuration_name] = diagnosed
                    accounting.update({key: value for key, value in diagnosed['accounting'].items() if isinstance(value, (float, int))})
                row['cross_budget'] = cross_budget_pair(*(row['configurations'][name] for name in CONFIGURATIONS), plan['decomposition_tolerance'])
                row['source_valid'] = all(config['source_valid'] for config in row['configurations'].values())
                row['complete'] = row['source_valid'] and row['cross_budget']['validation']['passed'] and row['cross_budget']['available'] and all(
                    config['status'] == 'ENDPOINT_DIAGNOSTIC_COMPLETE' for config in row['configurations'].values())
                result_rep['contexts'].append(row)
            result_rep.update(source_valid=all(row['source_valid'] for row in result_rep['contexts']),
                              complete=all(row['complete'] for row in result_rep['contexts']))
            repetitions.append(result_rep)
            if progress:
                progress({**repetition, 'source_valid': result_rep['source_valid'], 'complete': result_rep['complete']})
        stream_complete = not reader.readline()
    accounting.update(new_provider_calls=0, new_sampling_calls=0, new_physical_draws=0, new_physical_batches=0,
        historical_physical_batches=plan['source_historical_physical_batches'], historical_physical_draws=plan['source_historical_physical_draws'])
    report = {'schema': 'acfqp.controlled_predictive_endpoint_errors.v36', 'plan': plan,
        'status': 'ENDPOINT_ERRORS_COMPLETE' if all(rep['complete'] for rep in repetitions) and stream_complete else 'ENDPOINT_ERRORS_WITH_ISSUES',
        'plan_binding_validation': binding, 'repetitions': repetitions,
        'source_valid_repetition_count': sum(rep['source_valid'] for rep in repetitions),
        'complete_repetition_count': sum(rep['complete'] for rep in repetitions),
        'exact_reference_actions': [{'context_index': index, 'action': action} for index, action in exact_references.items()],
        'original_repetitions': _original_repetitions(source['repetitions']), 'original_source_accounting': source['accounting'],
        'original_all_actual_configuration_costs': reference['all_actual_configuration_costs'],
        'accounting': dict(accounting), 'source_endpoint_stream_complete': stream_complete,
        'oracle_used_for_replay_selection': False, 'endpoint_evaluation_replanning_calls': 0,
        'elapsed_seconds_before_report_serialization': perf_counter() - started,
        'scientific_gate': 'NOT_A_FORMAL_GATE', 'u006_assurance_started': False, 'original_deferred_24_case_cohort_loaded_or_executed': False,
        'scope': 'All retained CACHED24/32 root endpoints, including correct and incorrect full policies. Original policies and costs for all three V35 configurations remain unchanged. A/D removals are diagnostic rankings only, with exact lower-value argmax and original lexical ties; correctness still uses the frozen tolerance. Signed V36 margins use the exact maximizing Qstar reference. All new work is restoration and evaluation; no sampling or planner decisions are changed.'}
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
        parser.error('the frozen V36 protocol and plan must exist before diagnosis')
    report, serialization = run_endpoint_errors(args.plan, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({'status': report['status'], 'complete_repetition_count': report['complete_repetition_count'],
                      'output': str(args.output), **serialization}), flush=True)


if __name__ == '__main__':
    main()
