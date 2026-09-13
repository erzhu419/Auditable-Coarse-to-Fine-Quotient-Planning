#!/usr/bin/env python3
"""Separate estimation and coverage terms at all retained CACHED24/32 endpoints."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_continuation_sources_v37 import evaluate_continuation_sources, margin, MODES, VALUE_FIELDS
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_restore_v22 import restore_state
from acfqp.science.controlled_predictive_snapshot_v21 import state_record
from run_controlled_predictive_new_starts_v28 import _identity, _key, _validate_local, TRACE_FIELDS
from run_controlled_predictive_budget_curve_v33 import _compact_evaluation
from run_controlled_predictive_endpoint_errors_v36 import _read, _json, _validation, _require, _local_compact

PROTOCOL = Path('specs/CONTROLLED_PREDICTIVE_CONTINUATION_SOURCES_V37.md')
DEFAULT_PLAN = Path('reports/controlled_predictive_continuation_sources_plan_v37.json')
DEFAULT_OUTPUT = Path('reports/controlled_predictive_continuation_sources_v37.json.gz')
CONFIGURATIONS = ('CACHED24', 'CACHED32')


def _original_diagnostics(repetitions):
    return [{**{key: value for key, value in rep.items() if key != 'contexts'}, 'contexts': [
        {**{key: value for key, value in row.items() if key not in ('configurations', 'cross_budget')},
         'configurations': {name: {key: endpoint[key] for key in ('source_valid', 'diagnostic_available', 'diagnostic_validation', 'status', 'policy_evaluation') if key in endpoint}
            | {'diagnostic': {'modes': endpoint.get('diagnostic', {}).get('modes', {})}}
            for name, endpoint in row['configurations'].items()}}
        for row in rep['contexts']]} for rep in repetitions]


def diagnose_endpoint(source, old, original, context, configuration, oracle, exact_reference_action, aligned, query_definition):
    started = perf_counter()
    accounting = Counter()
    name = context['query_name']
    row = {'configuration': configuration, 'source_valid': False,
        'source_validation': {'passed': False}, 'restoration_validation': {'passed': False},
        'inherited_policy_validation': {'passed': False}, 'local_reproduction_validation': {'passed': False},
        'legacy_diagnostic_reproduction_validation': {'passed': False}, 'diagnostic_validation': {'passed': False},
        'diagnostic_available': False, 'status': 'CONTINUATION_DIAGNOSTIC_INCOMPLETE',
        'policy_evaluation': old.get('policy_evaluation', {}),
        'original_v36_modes': old.get('diagnostic', {}).get('modes', {}), 'accounting': {}}
    state = None
    try:
        validation = _validate_local(source['local'], source['state'], {**context, 'requested_batch_count': configuration['budget']}, configuration['arm'])
        validation['checks'].update(identity=aligned, query_weights=source['state']['query'] == query_definition,
            configuration=source['configuration'] == old['configuration'] == original['configuration'] == configuration,
            original_sources=source['source_valid'] and original['source_valid'] and old['source_valid'],
            v36_restoration=old['restoration_validation']['passed'],
            retained_costs=source['costs'] == original['costs'],
            retained_local={key: value for key, value in source['local'].items() if key not in TRACE_FIELDS} == original['local'])
        validation['passed'] = all(validation['checks'].values())
        row['source_validation'] = validation
        _require(validation['passed'], 'retained V35/V36 endpoint source binding differs')
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
        row['inherited_policy_validation'] = _validation({
            'v36_evaluation': old['evaluation_validation']['passed'],
            'v36_value_reproduction': old['value_reproduction_validation']['passed'],
            'original_v35_evaluation': original['evaluation_validation']['passed'],
            'exact_retained_policy_value': bool(row['policy_evaluation']) and row['policy_evaluation'] == _compact_evaluation(original['evaluation'])})
        tick = perf_counter()
        accounting['local_decomposition_calls'] += 1
        try:
            evaluated = evaluate_continuation_sources(state, name, _key(context['target_key']), oracle)
        finally:
            accounting['continuation_evaluation_seconds'] += perf_counter() - tick
        accounting.update(evaluated['accounting'])
        local, diagnostic = evaluated['local_evaluation'], evaluated['diagnostic']
        row['local_reproduction_validation'] = _validation({
            'v36_local_valid': old['local_reproduction_validation']['passed'],
            'exact_v21_local': _local_compact(local) == old['local_evaluation'],
            'selected_action': local['selected_action'] == source['local']['final_action'],
            'exact_reference': diagnostic['exact_reference_action'] == old['diagnostic']['exact_reference_action'] == exact_reference_action})
        legacy = {key: value for key, value in evaluated['original_diagnostic'].items() if key not in ('accounting', 'scope')}
        row['legacy_diagnostic_reproduction_validation'] = _validation({
            'v36_diagnostic_valid': old['diagnostic_validation']['passed'],
            'exact_v25_numeric_fields': all(old['diagnostic'].get(key) == value for key, value in legacy.items()),
            'raw_mode': diagnostic['modes']['RAW'] == old['diagnostic']['modes']['RAW']})
        _require(row['local_reproduction_validation']['passed'] and row['legacy_diagnostic_reproduction_validation']['passed'], 'V36 local or mode reproduction differs')
        row['diagnostic'] = diagnostic
        row['diagnostic_validation'] = _validation({'identities': diagnostic['validation']['all_passed'],
            'coverage_nonpositive': diagnostic['validation']['coverage_nonpositive'],
            'signed_true_margin_equals_negative_regret': diagnostic['selected_minus_reference']['q_star_difference'] == -local['local_regret'],
            'mode_set': list(diagnostic['modes']) == list(MODES)})
        row['diagnostic_available'] = all(mode['available'] for mode in diagnostic['modes'].values())
        if row['diagnostic_validation']['passed'] and row['diagnostic_available'] and row['inherited_policy_validation']['passed'] and all(
                row['policy_evaluation'].get(key) is True for key in ('policy_evaluable', 'identities_pass', 'reach_probability_pass')):
            row['status'] = 'CONTINUATION_DIAGNOSTIC_COMPLETE'
    except (ValueError, KeyError, TypeError, IndexError) as error:
        row['reason'] = str(error)
    accounting.update(new_provider_calls=0, new_sampling_calls=0, new_physical_draws=0, new_physical_batches=0, frozen_policy_evaluation_calls=0)
    row['accounting'] = {**accounting, 'whole_endpoint_seconds': perf_counter() - started,
        'restored_engine_work_counts': dict(state.work_counts) if state is not None else {}}
    return row


def cross_budget_pair(before, after, tolerance):
    result = {'validation': {'passed': False}, 'available': False}
    if not all(row.get('diagnostic_validation', {}).get('passed') for row in (before, after)):
        result['reason'] = 'ENDPOINT_DECOMPOSITION_UNAVAILABLE'
        return result
    left, right = after['diagnostic']['original_selected_action'], before['diagnostic']['original_selected_action']
    first, last = (margin(left, right, row['diagnostic']['actions']) for row in (before, after))
    fields = (*(field + '_difference' for field in VALUE_FIELDS), 'raw_lower_difference', 'REMOVE_E_difference', 'REMOVE_C_difference')
    change = {field: last[field] - first[field] if first[field] is not None and last[field] is not None else None for field in fields}
    residual, continuation_residual = None, None
    if first['decomposable'] and last['decomposable']:
        residual = change['q_hat_difference'] - change['q_star_difference'] - sum(change[field + '_difference'] for field in ('A_transition_error', 'E_estimation_error', 'C_coverage_error'))
        continuation_residual = change['D_continuation_error_difference'] - change['E_estimation_error_difference'] - change['C_coverage_error_difference']
    checks = {'fixed_actions': first['actions'] == last['actions'] == [left, right],
        'same_exact_reference': before['diagnostic']['exact_reference_action'] == after['diagnostic']['exact_reference_action'],
        'same_true_values': all(before['diagnostic']['actions'][action]['q_star'] == after['diagnostic']['actions'][action]['q_star'] for action in first['actions']),
        'change_identity': residual is None or abs(residual) <= tolerance,
        'continuation_change_identity': continuation_residual is None or abs(continuation_residual) <= tolerance}
    result.update(actions=[left, right], before_margin=first, after_margin=last, change=change,
        change_identity_residual=residual, continuation_change_identity_residual=continuation_residual,
        validation=_validation(checks), available=first['decomposable'] and last['decomposable'])
    return result


def run_continuation_sources(plan_path, output_path, progress=None):
    started = perf_counter()
    if output_path.exists():
        raise FileExistsError(f'V37 output already exists: {output_path}')
    accounting = Counter()
    tick = perf_counter()
    plan = _read(plan_path)
    source_plan = _read(plan['source_plan'])
    source = _read(plan['source_result'])
    reference = _read(plan['source_analysis'])
    accounting['source_metadata_and_result_read_seconds'] = perf_counter() - tick
    checks = {field: plan[field] == source_plan[field] for field in (
        'boards', 'contexts', 'queries', 'source_query_order', 'replicates', 'configurations', 'samples_per_batch',
        'prefix_batches_per_board', 'selection_rule', 'compared_configurations', 'decomposition_tolerance')}
    checks.update(source_plan=source['plan'] == source_plan, source_accounting=reference['accounting'] == source['accounting'],
        source_analysis=reference['all_analysis_checks_passed'], source_endpoints=plan['source_endpoints'] == source_plan['source_endpoints'],
        compared_configurations=plan['compared_configurations'] == list(CONFIGURATIONS), modes=plan['modes'] == list(MODES),
        historical_batches=plan['source_historical_physical_batches'] == source['accounting']['historical_physical_batches'],
        historical_draws=plan['source_historical_physical_draws'] == source['accounting']['historical_physical_draws'])
    binding = _validation(checks)
    _require(binding['passed'], 'V37 frozen source binding differs before endpoint diagnosis')
    oracles = {}
    for board in plan['boards']:
        tick = perf_counter()
        closure = build_development_closure(horizon=board['horizon'], max_nodes=30_000, boards={board['name']: tuple(board['board'])})
        oracles[board['board_index']] = ExactOracle.from_closure(closure)
        accounting['exact_closure_and_oracle_seconds'] += perf_counter() - tick
    exact_references = {row['context_index']: row['action'] for row in source['exact_reference_actions']}
    source_lookup = {(rep['replicate_index'], row['identity']['context_index']): row for rep in source['repetitions'] for row in rep['contexts']}
    original_lookup = {(rep['replicate_index'], row['identity']['context_index']): row for rep in source['original_repetitions'] for row in rep['contexts']}
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
                lookup = repetition['replicate_index'], context['context_index']
                old, original = source_lookup[lookup], original_lookup[lookup]
                expected = {**repetition, 'identity': _identity(context), 'target_key': context['target_key'], 'initial_batches': context['initial_batches']}
                aligned = all(endpoint[key] == value for key, value in expected.items()) and old['identity'] == original['identity'] == _identity(context)
                row = {'identity': _identity(context), 'target_key': context['target_key'], 'configurations': {}}
                for configuration_name in CONFIGURATIONS:
                    diagnosed = diagnose_endpoint(endpoint['configurations'][configuration_name], old['configurations'][configuration_name],
                        original['configurations'][configuration_name], context, configuration_lookup[configuration_name],
                        oracles[context['board_index']], exact_references[context['context_index']], aligned, plan['queries'][context['query_name']])
                    row['configurations'][configuration_name] = diagnosed
                    accounting.update({key: value for key, value in diagnosed['accounting'].items() if isinstance(value, (float, int))})
                row['cross_budget'] = cross_budget_pair(*(row['configurations'][name] for name in CONFIGURATIONS), plan['decomposition_tolerance'])
                row['source_valid'] = all(config['source_valid'] for config in row['configurations'].values())
                row['complete'] = row['source_valid'] and row['cross_budget']['validation']['passed'] and row['cross_budget']['available'] and all(
                    config['status'] == 'CONTINUATION_DIAGNOSTIC_COMPLETE' for config in row['configurations'].values())
                result_rep['contexts'].append(row)
            result_rep.update(source_valid=all(row['source_valid'] for row in result_rep['contexts']),
                              complete=all(row['complete'] for row in result_rep['contexts']))
            repetitions.append(result_rep)
            if progress:
                progress({**repetition, 'source_valid': result_rep['source_valid'], 'complete': result_rep['complete']})
        stream_complete = not reader.readline()
    accounting.update(new_provider_calls=0, new_sampling_calls=0, new_physical_draws=0, new_physical_batches=0, frozen_policy_evaluation_calls=0,
        historical_physical_batches=plan['source_historical_physical_batches'], historical_physical_draws=plan['source_historical_physical_draws'])
    report = {'schema': 'acfqp.controlled_predictive_continuation_sources.v37', 'plan': plan,
        'status': 'CONTINUATION_SOURCES_COMPLETE' if all(rep['complete'] for rep in repetitions) and stream_complete else 'CONTINUATION_SOURCES_WITH_ISSUES',
        'plan_binding_validation': binding, 'repetitions': repetitions,
        'source_valid_repetition_count': sum(rep['source_valid'] for rep in repetitions),
        'complete_repetition_count': sum(rep['complete'] for rep in repetitions),
        'exact_reference_actions': source['exact_reference_actions'],
        'original_v36_repetitions': _original_diagnostics(source['repetitions']),
        'original_repetitions': source['original_repetitions'],
        'original_source_accounting': source['original_source_accounting'],
        'source_diagnostic_accounting': source['accounting'],
        'original_all_actual_configuration_costs': source['original_all_actual_configuration_costs'],
        'accounting': dict(accounting), 'source_endpoint_stream_complete': stream_complete,
        'oracle_used_for_replay_selection': False, 'endpoint_evaluation_replanning_calls': 0,
        'elapsed_seconds_before_report_serialization': perf_counter() - started,
        'scientific_gate': 'NOT_A_FORMAL_GATE', 'u006_assurance_started': False, 'original_deferred_24_case_cohort_loaded_or_executed': False,
        'scope': 'Frozen H2 endpoints only. The H1 mask maximum replaces observed row estimates with exact values and keeps unknown structural lower bounds. E includes estimation and maximization; C is a coverage/truncation term, distinct from the V19 policy-loss term. New diagnostic rankings do not change any policy. Full-policy values and all three configuration costs are inherited from validated V36/V35 evidence. New work is restoration, local exact evaluation and arithmetic; no sampling. Nested accounting times are not additive.'}
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
        parser.error('the frozen V37 protocol and plan must exist before diagnosis')
    report, serialization = run_continuation_sources(args.plan, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({'status': report['status'], 'complete_repetition_count': report['complete_repetition_count'],
                      'output': str(args.output), **serialization}), flush=True)


if __name__ == '__main__':
    main()
