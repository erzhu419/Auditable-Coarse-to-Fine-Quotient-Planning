#!/usr/bin/env python3
"""Evaluate frozen budget checkpoints by replaying every retained V32 history."""

import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_frozen_policy_v27 import evaluate_frozen_policy
from acfqp.science.controlled_predictive_gap_frontier_v31 import GapFrontierPlannerState
from acfqp.science.controlled_predictive_local_v21 import ARMS as LOCAL_ARMS
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_restore_v22 import restore_state
from acfqp.science.controlled_predictive_snapshot_v21 import _replay_batch, state_record
from run_controlled_predictive_new_starts_v28 import _identity, _key, TRACE_FIELDS

PROTOCOL = Path('specs/CONTROLLED_PREDICTIVE_BUDGET_CURVE_V33.md')
DEFAULT_PLAN = Path('reports/controlled_predictive_budget_curve_plan_v33.json')
DEFAULT_POLICIES = Path('reports/controlled_predictive_budget_curve_policies_v33.jsonl.gz')
DEFAULT_OUTPUT = Path('reports/controlled_predictive_budget_curve_v33.json.gz')
ARMS = ('CACHED', 'GAP_FRONTIER')
BUDGETS = (0, 4, 8, 16, 24, 32)


def _json(value):
    return json.loads(json.dumps(value, allow_nan=False))


def _read(path):
    path = Path(path)
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as reader:
            return json.load(reader)
    return json.loads(path.read_text(encoding='utf-8'))


def _validation(checks):
    return {'passed': all(checks.values()), 'checks': checks}


def _require(value, reason):
    if not value:
        raise ValueError(reason)


def _evaluation_values(evaluation):
    return {key: value for key, value in evaluation.items() if key not in ('scope', 'accounting')}


def _compact_evaluation(evaluation):
    return {key: value for key, value in _evaluation_values(evaluation).items()
            if key not in ('reachable_decisions', 'reachable_terminals', 'missing_policy_frontier')}


def _checkpoint(stored, context, oracle, budget, accounting):
    tick = perf_counter()
    result = {'budget': budget, 'spent_batches': stored['spent_batches'], 'policy_evaluable': False,
              'evaluation_validation': {'passed': False}}
    full = None
    accounting['policy_evaluation_calls'] += 1
    try:
        full = evaluate_frozen_policy(stored, context['target_key'], Query(**stored['query']), oracle)
    except ValueError as error:
        result['evaluation_validation']['reason'] = str(error)
    else:
        result.update(evaluation=_compact_evaluation(full), policy_evaluable=full['policy_evaluable'],
                      evaluation_validation={'passed': True})
    accounting['policy_evaluation_seconds'] += perf_counter() - tick
    return result, full


def _frozen_record(state, name):
    """Materialize only the evidence consumed by the frozen-policy evaluator."""
    cache = state.solve(name)
    keys = sorted(state.profiles)
    row_order = _json(state.row_order)
    return {'root': _json(state.root), 'query': asdict(state.queries[name]), 'spent_batches': state.spent_batches,
        'profiles': [{'key': _json(key), 'status': state.profiles[key].status,
                      'legal_actions': list(state.profiles[key].legal_actions)} for key in keys],
        'row_order': row_order, 'rows': [{'row_key': pair} for pair in row_order],
        'policy_and_intervals': [{'key': _json(key), 'action': cache.policy.get(key),
                                 'lower': cache.lower[key], 'upper': cache.upper[key]} for key in keys]}


def _policy_record(stored, budget):
    # Profile metadata is unchanged in the retained V32 endpoint; select the
    # profile keys present in this checkpoint's policy when reconstructing it.
    return {'budget': budget, 'spent_batches': stored['spent_batches'],
            'policy_and_intervals': stored['policy_and_intervals'],
            'observed_row_keys': stored['row_order']}


def _replay_arm(snapshot, prefix_validation, prefix_checkpoint, source, old, context, arm, oracle, pair_index):
    started = perf_counter()
    accounting = Counter()
    local = source['local']
    row = {'arm': arm, 'prefix_context_index': context['context_index'], 'source_valid': False,
        'source_validation': {'passed': False}, 'prefix_validation': prefix_validation,
        'chronology_validation': {'passed': False, 'requests': []}, 'endpoint_validation': {'passed': False},
        'reference_value_validation': {'passed': False}, 'original_costs': source['costs'],
        'original_local_accounting': local['accounting'], 'status': 'REPLAY_MISMATCH', 'checkpoints': [], 'accounting': {}}
    policies, chronology = [], []
    state = None
    name, target = context['query_name'], _key(context['target_key'])
    try:
        checks = {'source_valid': source['source_valid'] and old['source_valid'],
            'arm': local['arm'] == arm, 'query': local['query_name'] == name,
            'target': local['target_key'] == context['target_key'],
            'requested_budget': local['requested_batch_count'] == context['requested_batch_count'] == BUDGETS[-1],
            'initial_batches': local['initial_batches'] == snapshot.spent_batches == context['initial_batches'],
            'complete_budget': local['completed_fixed_budget'] and local['completed_batches'] == BUDGETS[-1],
            'trace_lengths': all(len(local[field]) == BUDGETS[-1] for field in TRACE_FIELDS),
            'source_costs': source['costs'] == old['costs'],
            'source_local': {k: v for k, v in local.items() if k not in TRACE_FIELDS} == old['local'],
            'physical_draws': local['actual_draws'] == 256 * local['completed_batches'] == local['provider_counts']['physical_draws']}
        row['source_validation'] = _validation(checks)
        _require(row['source_validation']['passed'] and prefix_validation['passed'], 'retained source or prefix differs')
        tick = perf_counter()
        state = snapshot.clone()
        state.__class__ = LOCAL_ARMS[arm]
        state.observe_state(target)
        accounting['arm_clone_seconds'] += perf_counter() - tick
        accounting['arm_clones'] += 1
        zero = {**prefix_checkpoint, 'policy_record_reference': {'prefix_context_index': context['context_index']}}
        row['checkpoints'].append(zero)
        final_policy = None
        for index, (request, observed, gap) in enumerate(zip(*(local[field] for field in TRACE_FIELDS))):
            tick = perf_counter()
            diagnostic = _json(asdict(state.assess_gap(target, name)))
            candidate = state.select_row(target, name)
            kind = 'FIRST_OBSERVATION'
            if candidate is None:
                candidate = state.select_resample(target, name, mode='BALANCED')
                kind = 'REPEAT_OBSERVATION'
            selected = {'row_key': _json(candidate), 'batch_index': state.batch_counts.get(candidate, 0), 'kind': kind}
            counts = [round(weight * 256) for weight, _, _ in observed['outcomes']]
            checks = {'gap': diagnostic == gap, 'request': selected == request,
                'row': request['row_key'] == observed['row_key'],
                'index': request['batch_index'] == observed['batch_index'] == state.batch_counts.get(candidate, 0),
                'integer_batch': sum(counts) == 256 and all(n > 0 and n / 256 == outcome[0]
                    for n, outcome in zip(counts, observed['outcomes']))}
            chronology.append({'request_index': index, **_validation(checks)})
            accounting['chronology_selection_seconds'] += perf_counter() - tick
            accounting['chronology_selection_calls'] += 1
            _require(all(checks.values()), f'retained chronology differs at request {index}')
            # Only the retained request controls the update; no sampled data or
            # evaluator truth reaches the selection state.
            _replay_batch(state, request, observed, accounting)
            budget = index + 1
            if budget in BUDGETS:
                tick = perf_counter()
                stored = _frozen_record(state, name)
                accounting['checkpoint_materialization_seconds'] += perf_counter() - tick
                checkpoint, full = _checkpoint(stored, context, oracle, budget, accounting)
                checkpoint['policy_record_reference'] = {'pair_index': pair_index, 'arm': arm, 'budget': budget}
                row['checkpoints'].append(checkpoint)
                policies.append(_policy_record(stored, budget))
                if budget == BUDGETS[-1]:
                    final_policy = full
        tick = perf_counter()
        final = _json(state_record(state, name))
        row['endpoint_validation'] = _validation({key: final.get(key) == value for key, value in source['state'].items()})
        row['reference_value_validation'] = _validation({key: (final_policy or {}).get(key) == value
            for key, value in old['evaluation'].items() if key not in ('scope', 'accounting')})
        accounting['endpoint_verification_seconds'] += perf_counter() - tick
        _require(row['endpoint_validation']['passed'], 'replayed endpoint state differs')
        row['status'] = 'REPLAY_COMPLETE'
    except (ValueError, KeyError, TypeError, IndexError) as error:
        row['reason'] = str(error)
    row['chronology_validation'] = {'passed': len(chronology) == BUDGETS[-1] and all(item['passed'] for item in chronology),
                                   'request_count': len(chronology), 'requests': chronology}
    row['source_valid'] = all(row[field]['passed'] for field in ('source_validation', 'prefix_validation', 'chronology_validation', 'endpoint_validation'))
    by_budget = {item['budget']: item for item in row['checkpoints']}
    row['checkpoints'] = [by_budget.get(budget, {'budget': budget, 'policy_evaluable': False,
        'evaluation_validation': {'passed': False, 'reason': 'REPLAY_DID_NOT_REACH_CHECKPOINT'}}) for budget in BUDGETS]
    accounting.update(new_provider_calls=0, new_sampling_calls=0, new_physical_draws=0, new_physical_batches=0)
    row['accounting'] = {**accounting, 'whole_replay_seconds': perf_counter() - started,
                        'replay_work_counts': dict(state.work_counts) if state is not None else {}}
    return row, policies


def run_budget_curve(plan_path, policies_path, output_path, progress=None):
    started = perf_counter()
    for path in (policies_path, output_path):
        if path.exists():
            raise FileExistsError(f'V33 output already exists: {path}')
    accounting = Counter()
    tick = perf_counter()
    plan = _read(plan_path)
    source_plan = _read(plan['source_plan'])
    prefixes = _read(plan['source_prefixes'])
    source_result = _read(plan['source_result'])
    source_analysis = _read(plan['source_analysis'])
    accounting['source_metadata_and_prefix_read_seconds'] = perf_counter() - tick
    checks = {field: plan[field] == source_plan[field] for field in (
        'boards', 'contexts', 'queries', 'source_query_order', 'replicates', 'arms', 'samples_per_batch',
        'prefix_batches_per_board', 'requested_batches_per_arm', 'selection_rule')}
    checks.update(embedded_plan=prefixes['plan'] == source_result['plan'] == source_plan,
        budgets=plan['checkpoints'] == list(BUDGETS), source_analysis=source_analysis['all_analysis_checks_passed'],
        source_accounting=source_analysis['accounting'] == source_result['accounting'],
        historical_batches=plan['source_historical_physical_batches'] == source_result['accounting']['historical_physical_batches'] + source_result['accounting']['total_physical_batches'],
        historical_draws=plan['source_historical_physical_draws'] == source_result['accounting']['historical_physical_draws'] + source_result['accounting']['total_physical_draws'])
    binding = _validation(checks)
    _require(binding['passed'], 'V33 plan/source binding differs before replay')
    prepared = {row['identity']['context_index']: row for row in prefixes['query_starts']}
    snapshots, restorations = {}, []
    for context in plan['contexts']:
        index, name = context['context_index'], context['query_name']
        retained = prepared[index]
        tick = perf_counter()
        state = restore_state(retained['state'], {name: Query(**plan['queries'][name])}, query_name=name)
        seconds = perf_counter() - tick
        rebuilt = _json(state_record(state, name))
        validation = _validation({**{key: rebuilt.get(key) == value for key, value in retained['state'].items()},
                                  'identity': retained['identity'] == _identity(context), 'source_valid': retained['validation']['passed']})
        _require(validation['passed'], f'V33 retained prefix differs for context {index}')
        snapshots[index] = state
        restorations.append({'identity': _identity(context), 'validation': validation,
                             'accounting': {'whole_seconds': seconds, 'work_counts': dict(state.work_counts)}})
        accounting['prefix_restores'] += 1
        accounting['prefix_restore_seconds'] += seconds
    validation_lookup = {row['identity']['context_index']: row['validation'] for row in restorations}
    oracles = {}
    for board in plan['boards']:
        tick = perf_counter()
        closure = build_development_closure(horizon=board['horizon'], max_nodes=30_000, boards={board['name']: tuple(board['board'])})
        oracles[board['board_index']] = ExactOracle.from_closure(closure)
        accounting['exact_closure_and_oracle_seconds'] += perf_counter() - tick
    prefix_evaluations = []
    for context in plan['contexts']:
        index = context['context_index']
        checkpoint, _ = _checkpoint(prepared[index]['state'], context, oracles[context['board_index']], 0, accounting)
        prefix_evaluations.append({'context_index': index, 'identity': _identity(context), 'checkpoint': checkpoint})
        accounting['prefix_policy_evaluation_calls'] += 1
    prefix_lookup = {row['context_index']: row['checkpoint'] for row in prefix_evaluations}
    old_lookup = {(rep['replicate_index'], row['identity']['context_index']): row for rep in source_result['repetitions'] for row in rep['contexts']}
    LOCAL_ARMS['GAP_FRONTIER'] = GapFrontierPlannerState
    repetitions, pair_index = [], 0
    with gzip.open(plan['source_endpoints'], 'rt', encoding='utf-8') as reader, gzip.open(policies_path, 'xt', encoding='utf-8') as writer:
        accounting['source_endpoint_stream_reads'] += 1
        for repetition in plan['replicates']:
            result_rep = {**repetition, 'contexts': []}
            for context in plan['contexts']:
                tick = perf_counter()
                endpoint = json.loads(reader.readline())
                accounting['source_endpoint_reload_seconds'] += perf_counter() - tick
                accounting['source_endpoint_pair_records_read'] += 1
                expected = {**repetition, 'identity': _identity(context), 'target_key': context['target_key'],
                    'requested_batch_count': context['requested_batch_count'], 'initial_batches': context['initial_batches']}
                aligned = all(endpoint[key] == value for key, value in expected.items())
                old = old_lookup[repetition['replicate_index'], context['context_index']]
                result = {key: value for key, value in expected.items() if key not in ('replicate_index', 'base_seed')}
                result['arms'] = {}
                policy_pair = {**expected, 'pair_index': pair_index, 'arms': {}}
                for arm in ARMS:
                    arm_result, policies = _replay_arm(snapshots[context['context_index']], validation_lookup[context['context_index']],
                        prefix_lookup[context['context_index']], endpoint['arms'][arm], old['arms'][arm], context, arm,
                        oracles[context['board_index']], pair_index)
                    arm_result['source_validation']['checks']['endpoint_identity'] = aligned
                    arm_result['source_validation']['passed'] = arm_result['source_validation']['passed'] and aligned
                    arm_result['source_valid'] = arm_result['source_valid'] and aligned
                    result['arms'][arm] = arm_result
                    policy_pair['arms'][arm] = policies
                    accounting.update({key: value for key, value in arm_result['accounting'].items() if isinstance(value, (int, float))})
                result['source_valid'] = all(row['source_valid'] for row in result['arms'].values())
                result['paired_complete'] = result['source_valid'] and all(row['reference_value_validation']['passed'] and all(
                    cp['evaluation_validation']['passed'] and cp['policy_evaluable'] and cp['evaluation']['identities_pass'] and cp['evaluation']['reach_probability_pass']
                    for cp in row['checkpoints']) for row in result['arms'].values())
                result['status'] = 'CURVE_COMPLETE' if result['paired_complete'] else 'REPLAY_OR_QUALITY_INCOMPLETE'
                result_rep['contexts'].append(result)
                tick = perf_counter()
                json.dump(policy_pair, writer, separators=(',', ':'), allow_nan=False)
                writer.write('\n')
                accounting['policy_stream_write_seconds'] += perf_counter() - tick
                pair_index += 1
            result_rep.update(source_valid=all(row['source_valid'] for row in result_rep['contexts']),
                              complete=all(row['paired_complete'] for row in result_rep['contexts']))
            repetitions.append(result_rep)
            if progress:
                progress({**repetition, 'source_valid': result_rep['source_valid'], 'complete': result_rep['complete']})
        stream_complete = not reader.readline()
    accounting.update(new_provider_calls=0, new_sampling_calls=0, new_physical_draws=0, new_physical_batches=0,
        historical_physical_batches=plan['source_historical_physical_batches'], historical_physical_draws=plan['source_historical_physical_draws'],
        policy_artifact_bytes=policies_path.stat().st_size, policy_pair_records_written=pair_index,
        checkpoint_policy_evaluation_calls=accounting['policy_evaluation_calls'] - accounting['prefix_policy_evaluation_calls'])
    report = {'schema': 'acfqp.controlled_predictive_budget_curve.v33', 'plan': plan,
        'status': 'BUDGET_CURVE_COMPLETE' if all(rep['complete'] for rep in repetitions) and stream_complete else 'BUDGET_CURVE_WITH_ISSUES',
        'plan_binding_validation': binding, 'restoration_records': restorations, 'prefix_evaluations': prefix_evaluations,
        'repetitions': repetitions, 'source_valid_repetition_count': sum(rep['source_valid'] for rep in repetitions),
        'complete_repetition_count': sum(rep['complete'] for rep in repetitions),
        'original_source_accounting': source_result['accounting'], 'accounting': dict(accounting),
        'source_endpoint_stream_complete': stream_complete, 'policy_artifact': str(policies_path),
        'oracle_used_for_replay_selection': False, 'endpoint_evaluation_replanning_calls': 0,
        'elapsed_seconds_before_report_serialization': perf_counter() - started,
        'scientific_gate': 'NOT_A_FORMAL_GATE', 'u006_assurance_started': False,
        'original_deferred_24_case_cohort_loaded_or_executed': False,
        'scope': 'Fixed retained V32 prefixes and suffix histories at predeclared budgets. K0 is evaluated once per context and reused; all original physical fees and measured full-budget costs remain, with no short-budget wall-time proration. Replay and evaluation are new diagnostic work only. Reconstruct positive-budget policy records using checkpoint policy keys and the unchanged profiles in their retained V32 endpoint.'}
    tick = perf_counter()
    with gzip.open(output_path, 'xt', encoding='utf-8') as writer:
        json.dump(report, writer, separators=(',', ':'), allow_nan=False)
    return report, {'report_serialization_seconds': perf_counter() - tick, 'report_bytes': output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=DEFAULT_PLAN)
    parser.add_argument('--policies', type=Path, default=DEFAULT_POLICIES)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.plan.is_file():
        parser.error('the frozen V33 protocol and plan must exist before replay')
    report, serialization = run_budget_curve(args.plan, args.policies, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({'status': report['status'], 'complete_repetition_count': report['complete_repetition_count'],
                      'output': str(args.output), **serialization}), flush=True)


if __name__ == '__main__':
    main()
