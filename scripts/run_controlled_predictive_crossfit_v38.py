#!/usr/bin/env python3
"""Freeze complementary-fold root policies before evaluating any candidate."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_crossfit_v38 import pooled_root_readout, crossfit_root_readout
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_frozen_policy_v27 import evaluate_frozen_policy
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_restore_v22 import restore_state
from acfqp.science.controlled_predictive_snapshot_v21 import state_record
from run_controlled_predictive_new_starts_v28 import _identity, _key, _validate_local, TRACE_FIELDS
from run_controlled_predictive_budget_curve_v33 import _compact_evaluation
from run_controlled_predictive_endpoint_errors_v36 import _read, _json, _validation, _require, _original_repetitions

PROTOCOL = Path('specs/CONTROLLED_PREDICTIVE_CROSSFIT_V38.md')
DEFAULT_PLAN = Path('reports/controlled_predictive_crossfit_plan_v38.json')
DEFAULT_PROPOSALS = Path('reports/controlled_predictive_crossfit_proposals_v38.jsonl.gz')
DEFAULT_OUTPUT = Path('reports/controlled_predictive_crossfit_v38.json.gz')
ARMS = ('POOLED', 'CROSSFIT')


def _candidate_record(stored, target, action):
    return {'query': stored['query'], 'profiles': stored['profiles'],
        'rows': [{'row_key': row['row_key']} for row in stored['rows']],
        'policy_and_intervals': [{**row, 'action': action} if row['key'] == target else dict(row)
            for row in stored['policy_and_intervals']]}


def _compact_readout(readout):
    return {key: value for key, value in readout.items() if key not in ('split_rows', 'continuations')}


def construct_proposal(source, context, repetition, plan, aligned):
    started = perf_counter()
    accounting = Counter()
    name = context['query_name']
    order = list(ARMS if (repetition['replicate_index'] + context['context_index']) % 2 == 0 else reversed(ARMS))
    row = {'identity': _identity(context), 'target_key': context['target_key'], 'run_order': order,
        'source_validation': {'passed': False}, 'restoration_validation': {'passed': False},
        'proposal_validation': {'passed': False}, 'source_valid': False, 'complete': False,
        'original_CACHED32_costs': source.get('costs', {}), 'arms': {arm: {
            'source_valid': False, 'readout_validation': {'passed': False},
            'evaluation_validation': {'passed': False}, 'policy_evaluable': False,
            'costs': {'postprocess_seconds': 0.}, 'status': 'READOUT_UNAVAILABLE'} for arm in ARMS}}
    evidence = {'retained_local': {key: value for key, value in source.get('local', {}).items() if key not in TRACE_FIELDS},
        'candidate_state': None, 'crossfit_details': None}
    try:
        tick = perf_counter()
        validation = _validate_local(source['local'], source['state'], {**context, 'requested_batch_count': plan['fixed_local_batches']}, 'CACHED')
        validation['checks'].update(identity=aligned, source_valid=source['source_valid'],
            configuration=source['configuration'] == plan['source_configuration'],
            query=source['state']['query'] == plan['queries'][name])
        validation['passed'] = all(validation['checks'].values())
        row['source_validation'] = validation
        accounting['source_validation_seconds'] += perf_counter() - tick
        _require(validation['passed'], 'retained CACHED32 source differs')
        tick = perf_counter()
        accounting['model_restore_calls'] += 1
        try:
            state = restore_state(source['state'], {name: Query(**plan['queries'][name])}, query_name=name)
        finally:
            accounting['model_restore_seconds'] += perf_counter() - tick
        tick = perf_counter()
        rebuilt = _json(state_record(state, name))
        row['restoration_validation'] = _validation({key: rebuilt.get(key) == value for key, value in source['state'].items()})
        accounting['restoration_validation_seconds'] += perf_counter() - tick
        _require(row['restoration_validation']['passed'], 'restored CACHED32 state differs')
        readouts = {}
        for arm in order:
            tick = perf_counter()
            accounting['readout_calls_' + arm] += 1
            try:
                readout = (pooled_root_readout(state, name) if arm == 'POOLED' else
                    crossfit_root_readout(state, name, plan['partition_seed'], repetition['base_seed']))
                readouts[arm] = readout
                row['arms'][arm]['readout'] = _compact_readout(readout)
                row['arms'][arm]['readout_validation'] = readout['validation']
                row['arms'][arm]['status'] = 'READOUT_FROZEN' if readout['validation']['passed'] else 'READOUT_INVALID'
            except (ValueError, KeyError, TypeError) as error:
                row['arms'][arm]['reason'] = str(error)
            finally:
                row['arms'][arm]['costs']['postprocess_seconds'] = (readouts[arm]['accounting']['whole_readout_seconds'] if arm in readouts else perf_counter() - tick)
        _require(len(readouts) == 2 and all(readout['validation']['passed'] for readout in readouts.values()), 'readout proposal unavailable')
        tick = perf_counter()
        pooled = readouts['POOLED']
        pooled_checks = {'retained_action': pooled['root_action'] == source['local']['final_action'],
            'retained_lower': max(pooled['root_values'].values()) == source['local']['lower'],
            'all_root_values': pooled['root_values'] == {item['row_key'][1]: item['lower'] for item in source['state']['action_intervals'] if item['row_key'][0] == context['target_key']}}
        row['arms']['POOLED']['readout_validation'] = _validation(pooled_checks)
        candidate = _candidate_record(source['state'], context['target_key'], readouts['CROSSFIT']['root_action'])
        checks = {'pooled_reproduction': all(pooled_checks.values()),
            'crossfit_arithmetic': readouts['CROSSFIT']['validation']['passed'],
            'only_target_action_changed': all(new == ({**old, 'action': readouts['CROSSFIT']['root_action']} if old['key'] == context['target_key'] else old)
                for new, old in zip(candidate['policy_and_intervals'], source['state']['policy_and_intervals'])),
            'profile_and_observation_mask_preserved': candidate['profiles'] == source['state']['profiles'] and candidate['rows'] == [{'row_key': item['row_key']} for item in source['state']['rows']]}
        row['proposal_validation'] = _validation(checks)
        accounting['proposal_validation_seconds'] += perf_counter() - tick
        evidence.update(candidate_state=candidate, crossfit_details={key: readouts['CROSSFIT'][key] for key in ('split_rows', 'continuations')})
        row['source_valid'] = row['proposal_validation']['passed']
        for arm in ARMS:
            row['arms'][arm]['source_valid'] = row['source_valid'] and row['arms'][arm]['readout_validation']['passed']
    except (ValueError, KeyError, TypeError, IndexError) as error:
        row['reason'] = str(error)
    row['accounting'] = {**accounting, 'whole_construction_seconds': perf_counter() - started}
    return row, evidence


def _candidate_evaluation(evaluation):
    result = _compact_evaluation(evaluation)
    result['retained_pooled_lower'] = result.pop('lower')
    result['retained_pooled_upper'] = result.pop('upper')
    return result


def run_crossfit(plan_path, proposals_path, output_path, progress=None):
    started = perf_counter()
    for path in (proposals_path, output_path):
        if path.exists():
            raise FileExistsError(f'V38 output already exists: {path}')
    accounting = Counter()
    tick = perf_counter()
    plan, source_plan = _read(plan_path), None
    source_plan = _read(plan['source_plan'])
    accounting['source_plan_read_seconds'] += perf_counter() - tick
    checks = {field: plan[field] == source_plan[field] for field in (
        'boards', 'contexts', 'queries', 'source_query_order', 'replicates', 'samples_per_batch', 'prefix_batches_per_board', 'selection_rule')}
    checks.update(source_configurations=plan['source_configurations'] == source_plan['configurations'],
        source_configuration=plan['source_configuration'] == {'name': 'CACHED32', 'arm': 'CACHED', 'budget': 32},
        arms=plan['arms'] == list(ARMS), partition_seed=plan['partition_seed'] == 38,
        budget=plan['fixed_local_batches'] == 32)
    binding = _validation(checks)
    _require(binding['passed'], 'V38 frozen source plan binding differs before policy construction')
    repetitions = []
    with gzip.open(plan['source_endpoints'], 'rt', encoding='utf-8') as reader, gzip.open(proposals_path, 'xt', encoding='utf-8') as writer:
        accounting['source_endpoint_stream_reads'] += 1
        for repetition in plan['replicates']:
            result_rep = {**repetition, 'contexts': []}
            for context in plan['contexts']:
                tick = perf_counter()
                endpoint = json.loads(reader.readline())
                accounting['source_endpoint_read_seconds'] += perf_counter() - tick
                accounting['source_endpoint_triple_records_read'] += 1
                expected = {**repetition, 'identity': _identity(context), 'target_key': context['target_key'], 'initial_batches': context['initial_batches']}
                aligned = all(endpoint[key] == value for key, value in expected.items())
                row, evidence = construct_proposal(endpoint['configurations']['CACHED32'], context, repetition, plan, aligned)
                result_rep['contexts'].append(row)
                accounting.update(row['accounting'])
                tick = perf_counter()
                writer.write(json.dumps({**repetition, 'identity': _identity(context), 'target_key': context['target_key'],
                    'candidate_root_action': row['arms']['CROSSFIT'].get('readout', {}).get('root_action'), **evidence}, separators=(',', ':'), allow_nan=False) + '\n')
                accounting['proposal_serialization_seconds'] += perf_counter() - tick
                accounting['proposal_records_written'] += 1
            repetitions.append(result_rep)
            if progress:
                progress({**repetition, 'stage': 'PROPOSALS_FROZEN', 'source_valid': all(row['source_valid'] for row in result_rep['contexts'])})
        source_stream_complete = not reader.readline()
    # No truth object or old truth-containing result is read before every
    # candidate policy and its partition evidence have been written and closed.
    tick = perf_counter()
    source, reference = _read(plan['source_result']), _read(plan['source_analysis'])
    accounting['source_result_and_analysis_read_seconds'] += perf_counter() - tick
    checks.update(source_result_plan=source['plan'] == source_plan,
        source_analysis=reference['all_analysis_checks_passed'],
        original_source_accounting=reference['original_source_accounting'] == source['accounting'],
        historical_batches=plan['source_historical_physical_batches'] == source['accounting']['historical_plus_new_physical_batches'],
        historical_draws=plan['source_historical_physical_draws'] == source['accounting']['historical_plus_new_physical_draws'])
    binding = _validation(checks)
    _require(binding['passed'], 'V38 retained source result binding differs after proposal closure')
    oracles = {}
    for board in plan['boards']:
        tick = perf_counter()
        closure = build_development_closure(horizon=board['horizon'], max_nodes=30_000, boards={board['name']: tuple(board['board'])})
        oracles[board['board_index']] = ExactOracle.from_closure(closure)
        accounting['exact_closure_and_oracle_seconds'] += perf_counter() - tick
    originals = {(rep['replicate_index'], row['identity']['context_index']): row for rep in source['repetitions'] for row in rep['contexts']}
    with gzip.open(proposals_path, 'rt', encoding='utf-8') as reader:
        accounting['proposal_stream_reads'] += 1
        for repetition in repetitions:
            for row in repetition['contexts']:
                tick = perf_counter()
                evidence = json.loads(reader.readline())
                accounting['proposal_read_seconds'] += perf_counter() - tick
                accounting['proposal_records_read'] += 1
                old = originals[repetition['replicate_index'], row['identity']['context_index']]['configurations']['CACHED32']
                pooled, candidate = (row['arms'][arm] for arm in ARMS)
                retained_binding = _validation({'identity': evidence['identity'] == row['identity'] and evidence['replicate_index'] == repetition['replicate_index'] and evidence['base_seed'] == repetition['base_seed'],
                    'old_source_valid': old['source_valid'], 'configuration': old['configuration'] == plan['source_configuration'],
                    'local': evidence['retained_local'] == old['local'], 'original_costs': row['original_CACHED32_costs'] == old['costs'],
                    'candidate_root_action': evidence['candidate_root_action'] == candidate.get('readout', {}).get('root_action')})
                row['retained_result_validation'] = retained_binding
                for arm in ARMS:
                    row['arms'][arm]['source_valid'] &= retained_binding['passed']
                row['source_valid'] &= retained_binding['passed']
                pooled['policy_evaluation'] = _compact_evaluation(old.get('evaluation', {})) if old.get('evaluation') else {}
                pooled['evaluation_validation'] = old.get('evaluation_validation', {'passed': False})
                pooled['value_reproduction_validation'] = _validation({'original_evaluation': pooled['evaluation_validation']['passed'],
                    'retained_action': pooled.get('readout', {}).get('root_action') == old.get('evaluation', {}).get('initial_action'),
                    'retained_lower': bool(pooled.get('readout')) and max(pooled['readout']['root_values'].values()) == old.get('evaluation', {}).get('lower')})
                if candidate['source_valid'] and evidence['candidate_state'] is not None:
                    tick = perf_counter()
                    accounting['candidate_policy_evaluation_calls'] += 1
                    try:
                        evaluation = evaluate_frozen_policy(evidence['candidate_state'], row['target_key'],
                            Query(**plan['queries'][row['identity']['query_name']]), oracles[row['identity']['board_index']])
                        candidate['policy_evaluation'] = _candidate_evaluation(evaluation)
                        candidate['evaluation_validation'] = _validation({'frozen_action': evaluation['initial_action'] == candidate['readout']['root_action']})
                    except (ValueError, KeyError) as error:
                        candidate['evaluation_validation'] = {'passed': False, 'reason': str(error)}
                    accounting['candidate_policy_evaluation_seconds'] += perf_counter() - tick
                for arm in ARMS:
                    current = row['arms'][arm]
                    current['policy_evaluable'] = current['evaluation_validation']['passed'] and all(current.get('policy_evaluation', {}).get(key) is True for key in ('policy_evaluable', 'identities_pass', 'reach_probability_pass'))
                    current['status'] = 'POLICY_EVALUATED' if current['policy_evaluable'] else 'POLICY_UNAVAILABLE'
                row['complete'] = row['source_valid'] and pooled['value_reproduction_validation']['passed'] and all(current['policy_evaluable'] for current in row['arms'].values())
                row['paired_complete'] = row['complete']
            repetition.update(source_valid=all(row['source_valid'] for row in repetition['contexts']), complete=all(row['complete'] for row in repetition['contexts']))
            if progress:
                progress({key: repetition[key] for key in ('replicate_index', 'base_seed', 'source_valid', 'complete')} | {'stage': 'CANDIDATES_EVALUATED'})
        proposal_stream_complete = not reader.readline()
    accounting.update(new_provider_calls=0, new_sampling_calls=0, new_physical_batches=0, new_physical_draws=0,
        baseline_policy_evaluation_calls=0, frozen_policy_evaluation_calls=accounting['candidate_policy_evaluation_calls'],
        historical_physical_batches=plan['source_historical_physical_batches'], historical_physical_draws=plan['source_historical_physical_draws'])
    endpoints = [row for rep in repetitions for row in rep['contexts']]
    account = {**accounting,
        'readout_calls_by_arm': {arm: accounting['readout_calls_' + arm] for arm in ARMS},
        'postprocess_seconds_by_arm': {arm: sum(row['arms'][arm]['costs']['postprocess_seconds'] for row in endpoints) for arm in ARMS},
        'crossfit_work_counts': dict(sum((Counter({key: value for key, value in row['arms']['CROSSFIT'].get('readout', {}).get('accounting', {}).items() if type(value) is int}) for row in endpoints), Counter()))}
    report = {'schema': 'acfqp.controlled_predictive_crossfit.v38', 'plan': plan,
        'status': 'CROSSFIT_COMPLETE' if all(rep['complete'] for rep in repetitions) and source_stream_complete and proposal_stream_complete else 'CROSSFIT_WITH_ISSUES',
        'plan_binding_validation': binding, 'repetitions': repetitions,
        'source_valid_repetition_count': sum(rep['source_valid'] for rep in repetitions), 'complete_repetition_count': sum(rep['complete'] for rep in repetitions),
        'original_repetitions': _original_repetitions(source['repetitions']), 'original_source_accounting': source['accounting'],
        'original_all_actual_configuration_costs': reference['all_original_actual_configuration_costs'],
        'source_diagnostic_accounting': reference['accounting'], 'prior_diagnostic_accounting': reference['source_diagnostic_accounting'],
        'accounting': account, 'source_endpoint_stream_complete': source_stream_complete, 'proposal_stream_complete': proposal_stream_complete,
        'all_proposals_closed_before_oracle': True, 'oracle_used_for_policy_construction': False, 'endpoint_evaluation_replanning_calls': 0,
        'proposal_path': str(proposals_path), 'elapsed_seconds_before_report_serialization': perf_counter() - started,
        'scientific_gate': 'NOT_A_FORMAL_GATE', 'u006_assurance_started': False, 'original_deferred_24_case_cohort_loaded_or_executed': False,
        'scope': 'One complementary partition of each retained H1 row. Candidate root actions are frozen before truth is loaded; all deployed H1 actions remain pooled. Original acquisition fees and prior diagnostics are preserved. Current postprocessing cost is measured separately from restoration, storage and evaluation. Crossfit scores are point estimates, and candidate evaluation retains the original pooled interval metadata under distinct names. No new environment samples or online allocation are evaluated.'}
    tick = perf_counter()
    with gzip.open(output_path, 'xt', encoding='utf-8') as writer:
        json.dump(report, writer, separators=(',', ':'), allow_nan=False)
    return report, {'report_serialization_seconds': perf_counter() - tick, 'report_bytes': output_path.stat().st_size, 'proposal_bytes': proposals_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=DEFAULT_PLAN)
    parser.add_argument('--proposals', type=Path, default=DEFAULT_PROPOSALS)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.plan.is_file():
        parser.error('the frozen V38 protocol and plan must exist before construction')
    report, serialization = run_crossfit(args.plan, args.proposals, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({'status': report['status'], 'complete_repetition_count': report['complete_repetition_count'], 'output': str(args.output), **serialization}), flush=True)


if __name__ == '__main__':
    main()
