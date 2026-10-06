"""Independent fresh TARGET replication of the settled V196 frozen models."""
import argparse
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_relational_programs_v196 as previous

SCHEMA = 'acfqp.frozen_program_replication.v197'
OUTPUT = PROJECT/'reports/controlled_predictive_frozen_program_replication_v197'
ACTIONS, EPS, utility, close = previous.ACTIONS, previous.EPS, previous.utility, previous.close
MODEL_NAMES, PRIMARY, COMPARATORS = previous.MODEL_NAMES, previous.PRIMARY, previous.COMPARATORS
PAIR_MODES = (*previous.MODES, 'TREE32', 'RAW32', 'CONDITIONAL', 'PAIR98')
INPUT_NAMES = ('v196_stage_checks.json', 'v196_run.json', 'v196_summary.json', 'program_models.json', 'program_libraries.json',
    'region_models.json', 'region_libraries.json', 'conditional_models.json', 'nonlinear_model.json', 'relation_model.json',
    'expanded_models.json', 'baseline_models.json', 'learned_rule.json', 'dense_models.json')
ZERO_WORK = ('new_environment_samples', 'new_source_games', 'new_native_weight_updates', 'new_predictors_fitted',
    'new_tree_fits', 'new_neighbor_configurations', 'new_parameter_solves', 'shared_library_preparations', 'new_learning_attempts',
    'new_source_cache_roots', 'new_source_evaluation_roots', 'new_source_selection_roots')
PHASES = ('protocol_frozen', 'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete')


def merge_models(inputs):
    retained = inputs['baseline_models.json']
    return dict(inputs['expanded_models.json'], **inputs['dense_models.json'], **inputs['program_models.json'],
        **inputs['region_models.json'], **inputs['conditional_models.json'], NONLINEAR=inputs['nonlinear_model.json'],
        RELATION=inputs['relation_model.json'], OLD_SHARED=retained['SHARED'], ONE=retained['ONE'])


def models_binding(saved, models, libraries, region_libraries):
    return set(saved) == set(MODEL_NAMES) and saved == models and libraries['FULL']['library_id'] == region_libraries['FULL']['library_id'] == 'FULL' and all(
        saved[name]['library_id'] == 'FULL' for name in (*previous.MODES, 'TREE32', 'RAW32'))


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]+[(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(4):
        for index, (a, b) in enumerate(edges):
            seed = 1970200+24*replica+index; rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]; board[a] = board[b] = 1+index%10
            for position in rng.sample([p for p in range(16) if p not in (a, b)], index%3):
                board[position] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index, horizon=3, seed=seed,
                name=f'v197_target_r{replica:02d}_{index:02d}', board=board, vacancies=index%3))
    return cases


def summarize(target, labels, choices, retained_summary):
    labeled = {row['root_id']: row['action_components'] for row in labels}
    chosen = {name: {row['root_id']: row for row in rows} for name, rows in choices.items()}
    names, records = (*MODEL_NAMES, 'FALLBACK', 'ORACLE'), []
    for root in target:
        vectors = labeled[root['root_id']]; oracle = root['legal_actions'][0]
        for action in root['legal_actions'][1:]:
            if utility(vectors[action]) > utility(vectors[oracle])+EPS:
                oracle = action
        outcomes = {}
        for name in names:
            decision = None if name == 'ORACLE' else chosen[name][root['root_id']]
            action = oracle if decision is None else decision['canonical_action']; vector = list(vectors[action])
            outcomes[name] = dict(action=action, components=vector, utility=utility(vector),
                regret=utility(vectors[oracle])-utility(vector), fallback=False if decision is None else decision['fallback'])
        records.append(dict(root_id=root['root_id'], replica=root['replica'], stratum=root['stratum'], models=outcomes))
    def aggregate(rows):
        result = {}
        for name in names:
            components = [math.fsum(row['models'][name]['components'][k] for row in rows)/len(rows) for k in range(3)]
            result[name] = dict(components=components, utility=utility(components),
                positive_regret_roots=sum(row['models'][name]['regret'] > EPS for row in rows),
                fallback_roots=sum(row['models'][name]['fallback'] for row in rows))
        return result
    def contrasts(rows):
        first = [dict(root_id=row['root_id'], models={'PROGRAM': row['models']['PROGRAM']}) for row in rows]
        return {'PROGRAM_MINUS_'+name: previous.relation.coverage.coverage_effect(first,
            [dict(root_id=row['root_id'], models={'PROGRAM': row['models'][name]}) for row in rows], 'PROGRAM') for name in COMPARATORS}
    metrics, effects = aggregate(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=aggregate(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records})
        for rows in [[row for row in records if row['replica'] == replica]]]
    cross = {}
    for name in PRIMARY:
        key = 'PROGRAM_MINUS_'+name
        cross[key] = dict(V196_utility_delta=retained_summary['comparisons'][key]['utility'], V197_utility_delta=effects[key]['utility'],
            V196_positive_replicas=sum(row['comparisons'][key]['utility'] > EPS for row in retained_summary['replicas']),
            V197_positive_replicas=sum(row['comparisons'][key]['utility'] > EPS for row in replicas))
    headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    return dict(schema=SCHEMA+'.summary', complete=True, roots=len(records), SOURCE=deepcopy(retained_summary['SOURCE']),
        SOURCE_reuse=dict(retained=True, summary_ref='inputs/inherited/v196_summary.json', fields=['SOURCE', 'projection_residuals.SOURCE']),
        models=metrics, comparisons=effects, replicas=replicas, root_records=records,
        projection_residuals=dict(SOURCE=deepcopy(retained_summary['projection_residuals']['SOURCE']),
            TARGET={mode: previous.old.projection_metrics(choices[mode]) for mode in PAIR_MODES}),
        success_diagnostics=previous.success_diagnostics(records, chosen), cross_cohort_comparisons=cross,
        oracle_minus_one=headroom, oracle_minus_program=metrics['ORACLE']['utility']-metrics['PROGRAM']['utility'],
        headroom_closed_fraction=effects['PROGRAM_MINUS_ONE']['utility']/headroom if headroom > EPS else None,
        whole_cohort_positive_vs_primary=all(effects['PROGRAM_MINUS_'+name]['utility'] > EPS for name in PRIMARY),
        all_replicas_positive_vs_primary=all(row['comparisons']['PROGRAM_MINUS_'+name]['utility'] > EPS for row in replicas for name in PRIMARY),
        **{name: 0 for name in ZERO_WORK})


def source_reuse_binding(summary, retained_summary):
    return summary['SOURCE'] == retained_summary['SOURCE'] and summary['projection_residuals']['SOURCE'] == retained_summary['projection_residuals']['SOURCE'] and (
        summary['SOURCE_reuse'] == dict(retained=True, summary_ref='inputs/inherited/v196_summary.json', fields=['SOURCE', 'projection_residuals.SOURCE']))


def phase_binding(run):
    return [(row['phase'], row['input_reads']) for row in run['phase_history']] == [
        (phase, 0 if index == 0 else 14) for index, phase in enumerate(PHASES)]


def zero_source_work(run):
    return all(run[name] == 0 for name in ZERO_WORK) and not any(
        key == 'learning' or key == 'source_features' or key.startswith('source_evaluation_') for key in run['costs'])


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io, bindings = [], Counter(), Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    check('fourteen_frozen_model_library_and_evidence_inputs', [(row['saved_ref'], row['phase']) for row in inputs] ==
        [(f'inputs/inherited/{name}', 'protocol_frozen') for name in INPUT_NAMES])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    inherited = {name: read('inputs/inherited/'+name) for name in INPUT_NAMES}
    check('settled_V196_complete', inherited['v196_stage_checks.json']['valid'] and inherited['v196_run.json']['status'] == 'complete' and
        inherited['v196_summary.json']['complete'])
    models = merge_models(inherited); libraries, region_libraries = inherited['program_libraries.json'], inherited['region_libraries.json']
    check('sixteen_exact_frozen_models_with_explicit_retained_FULL_libraries', models_binding(read('models.json'), models, libraries, region_libraries) and
        run['library_refs'] == dict(program='inputs/inherited/program_libraries.json', region='inputs/inherited/region_libraries.json'))
    check('zero_SOURCE_cache_selection_evaluation_and_learning', zero_source_work(run))
    cases = cohort_cases(); relation = previous.relation
    target, observation_work = relation.observe_roots(cases)
    feature_work = relation.coverage.cache_roots(target); relation_work = relation.cache_roots(target)
    conditional_work = previous.old.cache_roots(target); raw_work = previous.regions.cache_roots(target)
    program_work = previous.cache_roots(target, inherited['learned_rule.json'])
    check('96_fresh_fixed_H3_target_cases', read('target_cases.json') == cases)
    saved_roots = read('roots.json')
    check('TARGET_only_observations_and_exact_independent_tile_lineage', set(saved_roots) == {'TARGET'} and close(saved_roots['TARGET'], target) and all(
        saved['program_contracts'] == expected['program_contracts'] for saved, expected in zip(saved_roots['TARGET'], target, strict=True)))
    observed = run['costs']['observations']
    check('once_fresh_observation_and_all_five_cache_costs', observed['counts'] == observation_work and observed['feature_counts'] == feature_work and
        observed['relation_counts'] == relation_work and observed['conditional_counts'] == conditional_work and
        observed['raw_counts'] == raw_work and observed['program_counts'] == program_work)
    choices, choice_work = previous.freeze_choices(target, models, libraries, region_libraries); saved_choices = read('choices.json')
    check('all_frozen_model_choices_before_labels', close(saved_choices, choices))
    for mode in previous.MODES:
        check(mode+'_actual_EPS_actions_and_nonnegative_normalized_direction_weights', all(
            previous.verify_decision(saved['decision'], expected['decision']) for saved, expected in zip(saved_choices[mode], choices[mode], strict=True)))
    check('paid_frozen_TARGET_decisions', run['costs']['choices']['counts'] == choice_work)
    native, cost_rows = read('native_labels.json'), read('label_costs.json'); ids = [root['root_id'] for root in target]
    check('complete_native_label_and_cost_rosters', [row['root_id'] for row in native] == [row['root_id'] for row in cost_rows] == ids)
    labels, label_work = [], Counter()
    for root, raw, row in zip(target, native, cost_rows, strict=True):
        teacher = read(f"teacher_policy/{root['root_id']}.json")
        check('settled_native_fraction_teacher_binding:'+root['root_id'], relation.coverage.native_binding(root, raw, teacher))
        bindings.update(new_label_roots_bound=1, teacher_root_records_inspected=len(teacher), exact_component_coordinates_bound=3*len(root['legal_actions']))
        labels.append(relation.exact.canonical_labels(root, raw, dict(kind='new_exact_V69_FULL', teacher_query='goal_1_risk_1',
            teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')))
        costs = row['costs']; construction, compilation, export, n = costs['construction'], costs['compilation'], costs['teacher_export'], len(teacher)
        accounting = construction['concrete_states'] <= 200000 and construction['concrete_active_states'] == construction['active_states'] == n
        accounting = accounting and compilation['model_payload_calls'] == compilation['model_reload_calls'] == 1
        accounting = accounting and compilation['payload_cells'] == construction['registered_states'] == costs['label_evaluation']['kernel_cells_read']
        accounting = accounting and compilation['payload_rows'] == costs['label_evaluation']['kernel_rows_read'] and compilation['payload_outcomes'] == costs['label_evaluation']['kernel_outcomes_read']
        accounting = accounting and costs['label_evaluation']['root_labels_emitted'] == 1 and export == dict(
            teacher_encoding_records_read=construction['concrete_states'], teacher_policy_records=n, teacher_policy_action_reads=n, teacher_policy_tile_reads=16*n)
        check('settled_acquisition_caps_and_export_costs:'+root['root_id'], accounting)
        for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
            label_work.update({kind+'.'+key: value for key, value in costs[kind].items() if type(value) is int})
    check('all_new_canonical_RFS_vectors_and_fraction_metadata', close(read('labels.json'), labels))
    summary = summarize(target, labels, choices, inherited['v196_summary.json'])
    saved_summary = read('summary.json')
    check('18_arm_RFS_16_contrasts_and_separate_cross_cohort_replication', close(saved_summary, summary))
    check('SOURCE_results_retained_exactly_without_new_evaluation', source_reuse_binding(saved_summary, inherited['v196_summary.json']))
    check('frozen_models_and_all_choices_precede_target_labels', phase_binding(run))
    check('all_paid_input_and_label_counts', run['costs']['input_counts'] == dict(json_read_operations=14,
        input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs)) and run['costs']['labels']['counts'] == dict(label_work))
    check('96_completed_target_labels_cap_and_no_new_fits', all(run[key] == 96 for key in ('new_boards_generated', 'new_reference_kernel_attempts',
        'new_reference_kernels', 'new_teacher_plans', 'new_exact_label_roots', 'completed_roots')) and zero_source_work(run) and run['resource_cap_per_board'] == 200000)
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema=SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(independent_parameter_solves=0, independent_eigen_solves=0, independent_svd_solves=0, independent_tree_fits=0,
            independent_neighbor_configurations=0, independent_shared_library_preparations=0, independent_SOURCE_feature_counts={},
            independent_source_evaluation_counts={}, independent_SOURCE_selection_roots=0, new_environment_samples=0,
            physical_branches_replayed=0, new_kernels_reintegrated=0, old_models_refitted=0,
            independent_input_counts=dict(io), independent_observation_counts=observation_work, independent_feature_counts=feature_work,
            independent_relation_counts=relation_work, independent_conditional_counts=conditional_work, independent_raw_counts=raw_work,
            independent_program_counts=program_work, independent_choice_counts=choice_work, independent_new_label_binding_counts=dict(bindings),
            reconstructed_acquisition_counts=dict(label_work), original_run_costs=run['costs'], inherited_cost_refs=run['inherited_cost_refs'],
            test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'])))


if __name__ == '__main__':
    main()
