"""Independent expanded-SOURCE regularization, inference and paired summaries."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_source_regularization_v183 as ridge
from scripts import analyze_controlled_predictive_fresh_h3_confirmation_v184 as fresh

layout, shared, exact = ridge.previous, ridge.previous.previous, ridge.exact
ACTIONS, EPS, LAMBDAS = ridge.ACTIONS, ridge.EPS, ridge.LAMBDAS
OUTPUT = PROJECT/'reports/controlled_predictive_source_coverage_v185'
MODEL_NAMES = ('RIDGE', 'LAYOUT', 'SHARED', 'OLD_RIDGE', 'OLD_LAYOUT', 'OLD_SHARED', 'ONE')


def same(actual, expected):
    return exact._equal(actual, expected) and exact._equal(expected, actual)


def cohort_cases(cohort):
    """Reconstruct the frozen roster only after the main experiment exists."""
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*r+c+4) for r in range(3) for c in range(4)]
    base = 1850100 if cohort == 'SOURCE' else 1850200
    rows = []
    for replica in range(4):
        for index, (first, second) in enumerate(edges):
            seed = base+24*replica+index; rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]
            board[first] = board[second] = 1+index % 10
            for cell in rng.sample([cell for cell in range(16) if cell not in (first, second)], index % 3):
                board[cell] = 0
            rows.append(dict(name=f'v185_{cohort.lower()}_r{replica:02d}_{index:02d}', split=cohort,
                horizon=3, seed=seed, replica=replica, stratum=index, board=board, vacancies=index % 3))
    return rows


def observe_roots(cases):
    roots, work = [], Counter()
    for ordinal, case in enumerate(cases):
        root = exact.root_from_case(case, ordinal, case['split'], work)
        group = f"DESIGN_SOURCE:{12+6*case['replica']+case['stratum']//4:02d}" if case['split'] == 'SOURCE' else f"FRESH_REPLICA:{case['replica']:02d}"
        root.update(source_id=group, cohort=case['split'], split=case['split'], replica=case['replica'], stratum=case['stratum'], seed=case['seed'])
        roots.append(root)
    return roots, dict(work)


def cache_roots(roots):
    work = Counter()
    for root in roots:
        root['layout_features'] = layout.action_features_from_root(root, work)
        root['action_features'] = {action: list(record['aggregate']) for action, record in root['layout_features'].items()}
        work.update(shared_feature_maps_derived=1, shared_aggregate_cache_values_copied=6*len(root['action_features']))
    return dict(work)


def fit_shared(design, source_folds, audit_work):
    matrix, targets = design['X'][:, :6], design['Y']
    coefficients, _, rank, singular = np.linalg.lstsq(matrix, targets, rcond=None)
    counts = Counter(shared_lstsq_attempts=1, shared_lstsq_solves=1, shared_predictors_fitted=1,
        shared_design_matrix_cells=matrix.size, shared_target_matrix_cells=targets.size, shared_coefficient_cells=18)
    audit_work.update(shared_six_column_lstsq_solves=1, shared_design_matrix_cells=matrix.size, shared_target_matrix_cells=targets.size)
    records, labels, losses = [], [], [0., 0., 0.]
    indexed = {root['root_id']: [] for root in design['roots']}
    for row in design['pair_records']:
        sparse = [[column, value] for column, value in row['design'] if column < 6]
        record = dict(root_id=row['root_id'], source_id=row['source_id'], actions=list(row['actions']),
            weight=row['weight'], design=sparse, components=list(row['components']))
        predicted = [float(sum(value*coefficients[column, k] for column, value in sparse)) for k in range(3)]
        residual = [predicted[k]-row['components'][k] for k in range(3)]
        weighted = [row['weight']*value*value for value in residual]
        losses = [losses[k]+weighted[k] for k in range(3)]
        indexed[row['root_id']].append({key: deepcopy(record[key]) for key in ('actions', 'weight', 'design', 'components')})
        record.update(predicted_components=predicted, residual_components=residual,
                      weighted_component_losses=weighted, weighted_loss=sum(weighted)); records.append(record)
        counts.update(shared_pair_rows=1, shared_design_entries_examined=len(row['design']),
            shared_nonzero_design_entries=len(sparse), shared_fit_prediction_coefficient_reads=3*len(sparse),
            shared_residual_component_subtractions=3, shared_weighted_component_losses=3)
    for root in design['roots']:
        labels.append(dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=list(root['legal_actions']),
                           label_kind='exact_enumerated_vector', pairs=indexed[root['root_id']]))
    return dict(schema='acfqp.source_coverage.v185.shared_model', mode='SHARED', life=design['life'], query='risk1',
        native_teacher_query='goal_1_risk_1', horizon=3, label_kind='exact_enumerated_vector', feature_names=list(shared.FEATURE_NAMES),
        coefficients=coefficients.tolist(), rank=int(rank), singular_values=singular.tolist(), component_losses=losses, loss=sum(losses),
        action_root_ids=deepcopy(design['action_root_ids']), pair_root_ids=deepcopy(design['pair_root_ids']), connected_components=deepcopy(design['connected_components']),
        constants=dict(min_action_roots=4, epsilon=EPS, goal_rank=11, features=6, intercept=False, ridge=False, rcond=None),
        root_ids=list(design['root_ids']), source_ids=list(design['source_ids']), source_folds=deepcopy(source_folds), source_root_counts=deepcopy(design['source_root_counts']),
        fit_labels=labels, fit_residuals=records, design_format='sparse_columns', training_outcomes=deepcopy(design['roots']),
        fit_counts=dict(counts), feature_counts={}, data_design_origin='shared_final_source_design')


def fit_expanded(examples, life=0):
    examples = list(examples); sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != 36:
        raise ValueError('Thirty-six fixed SOURCE design groups required')
    source_folds = [sources[::2], sources[1::2]]; costs = Counter(source_fold_assignments=36, regularization_candidates=6)
    audit_work, designs, heldouts, folds, metadata = Counter(), [], [], [], []
    for fold, heldout in enumerate(source_folds):
        train = [source for source in sources if source not in heldout]
        design = ridge.prepare_design([row for row in examples if row['life'] == life and row['source_id'] in train], life)
        designs.append(design); costs.update(design['work'])
        heldouts.append([row for row in examples if row['life'] == life and row['source_id'] in heldout])
        folds.append(dict(fold=fold, train_sources=train, heldout_sources=list(heldout), design={key: value for key, value in design.items() if key not in ('X', 'Y')}))
    candidates, selected, best = [], LAMBDAS[0], None
    for value in LAMBDAS:
        results, groups = [], []
        for fold in range(2):
            fitted, rank, singular = ridge.fit_design(designs[fold], value, audit_work); costs.update(fitted['counts'])
            if value == 0:
                meta = ridge.decomposition_metadata(designs[fold], rank, singular); metadata.append(meta)
                folds[fold]['decomposition'] = meta; costs.update(meta['work'])
            model = ridge.model_from_fit(designs[fold], metadata[fold], fitted, value, source_folds)
            records, choices, prediction_counts = ridge.score_heldout(model, heldouts[fold]); costs.update(prediction_counts); groups.extend(records)
            results.append(dict(fold=fold, coefficients=fitted['coefficients'], component_losses=fitted['component_losses'], loss=fitted['loss'],
                root_mean_loss=fitted['root_mean_loss'], penalty=fitted['penalty'], objective=fitted['objective'], group_records=records,
                choices=choices, prediction_counts=prediction_counts, coefficient_counts=fitted['counts']))
        groups.sort(key=lambda row: row['source_id']); utility = sum(row['utility'] for row in groups)/36
        costs.update(regularization_group_mean_reads=36, regularization_score_comparisons=1)
        candidates.append(dict(lambda_value=value, utility=utility, group_records=groups, fold_results=results))
        if best is None or utility > best+EPS:
            selected, best = value, utility
    full = ridge.prepare_design(examples, life); costs.update(full['work'])
    fitted, rank, singular = ridge.fit_design(full, selected, audit_work); costs.update(fitted['counts'])
    if selected > 0:
        singular = np.linalg.svd(full['X'], compute_uv=False); cutoff = np.finfo(float).eps*max(full['X'].shape)*(singular[0] if len(singular) else 0.)
        rank = int(sum(singular > cutoff)); audit_work.update(final_singular_values_only_decompositions=1, final_singular_values_matrix_cells=full['X'].size)
    meta = ridge.decomposition_metadata(full, rank, singular); costs.update(meta['work'])
    selected_model = ridge.model_from_fit(full, meta, fitted, selected, source_folds)
    zero, _, _ = ridge.fit_design(full, 0., audit_work); costs.update(zero['counts'])
    layout_model = ridge.model_from_fit(full, meta, zero, 0., source_folds)
    layout_model.update(schema='acfqp.source_coverage.v185.layout_model', mode='LAYOUT')
    shared_model = fit_shared(full, source_folds, audit_work); costs.update(shared_model['fit_counts'])
    models = dict(RIDGE=selected_model, LAYOUT=layout_model, SHARED=shared_model)
    costs['new_predictors_fitted'] = costs['ridge_predictors_fitted']+costs['shared_predictors_fitted']
    selection = dict(schema='acfqp.source_regularization.v183.selection', life=life, lambdas=list(LAMBDAS), source_folds=source_folds,
        folds=folds, candidates=candidates, selected_lambda=selected, selected_utility=best, model=selected_model, costs=dict(costs))
    return dict(models=models, selection=selection, costs=dict(costs)), dict(audit_work)


def freeze_choices(roots, models):
    choices, work = {name: [] for name in (*MODEL_NAMES, 'FALLBACK')}, Counter()
    keys = ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards',
            'fallback_action', 'action_map', 'layout_features', 'action_features')
    for root in roots:
        observed = {key: root[key] for key in keys}
        for name in MODEL_NAMES:
            chooser = shared.choose_action if name.endswith('SHARED') else exact.choose_action if name == 'ONE' else layout.choose_action
            decision = chooser(models[name], observed)
            work.update(decision['work']); work.update(decision.get('feature_work', {})); work['coverage_model_choices'] += 1
            choices[name].append(dict(root_id=root['root_id'], mode=name, canonical_action=decision['canonical_action'],
                actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']; work['coverage_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action,
            actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work=dict(coverage_fallback_choices=1))))
    return choices, dict(work)


def coverage_effect(rows, old_rows, name):
    old_index = {row['root_id']: row for row in old_rows}; records = []
    for row in rows:
        first, second = row['models'][name], old_index[row['root_id']]['models'][name]
        records.append(dict(root_id=row['root_id'], components=[a-b for a, b in zip(first['components'], second['components'])],
            utility=first['utility']-second['utility'], action_changed=first['action'] != second['action'],
            new_error=first['regret'] > EPS and second['regret'] <= EPS,
            resolved_error=first['regret'] <= EPS and second['regret'] > EPS))
    positive = [row for row in records if row['utility'] > EPS]; negative = [row for row in records if row['utility'] < -EPS]
    gain, loss = math.fsum(row['utility'] for row in positive), math.fsum(row['utility'] for row in negative)
    best = max(positive, key=lambda row: row['utility']) if positive else None
    worst = min(negative, key=lambda row: row['utility']) if negative else None
    mean = exact.mean_vectors([row['components'] for row in records])
    return dict(components=mean, utility=exact.utility(mean), improved_roots=len(positive), worsened_roots=len(negative),
        equal_value_roots=len(records)-len(positive)-len(negative), action_changes=sum(row['action_changed'] for row in records),
        new_error_roots=sum(row['new_error'] for row in records), resolved_error_roots=sum(row['resolved_error'] for row in records),
        positive_gain_sum=gain, negative_gain_sum=loss, largest_gain_root=best['root_id'] if best else None,
        largest_gain=best['utility'] if best else 0., largest_gain_share_of_positive=best['utility']/gain if best else None,
        largest_loss_root=worst['root_id'] if worst else None, largest_loss=worst['utility'] if worst else 0., root_records=records)


def summarize(roots, labels, choices, selection):
    expanded = fresh.summarize(roots['TARGET'], labels, {name: choices[name] for name in ('RIDGE', 'LAYOUT', 'SHARED', 'ONE', 'FALLBACK')})
    original = fresh.summarize(roots['TARGET'], labels, {name: choices['OLD_'+name] if name in ('RIDGE', 'LAYOUT', 'SHARED') else choices[name]
        for name in ('RIDGE', 'LAYOUT', 'SHARED', 'ONE', 'FALLBACK')})
    effects = {f'{name}_MINUS_OLD_{name}': coverage_effect(expanded['root_records'], original['root_records'], name) for name in ('RIDGE', 'LAYOUT', 'SHARED')}
    replica_effects = []
    for replica in sorted({row['replica'] for row in expanded['root_records']}):
        new_rows = [row for row in expanded['root_records'] if row['replica'] == replica]
        old_rows = [row for row in original['root_records'] if row['replica'] == replica]
        replica_effects.append(dict(replica=replica, roots=len(new_rows), effects={f'{name}_MINUS_OLD_{name}': coverage_effect(new_rows, old_rows, name)
            for name in ('RIDGE', 'LAYOUT', 'SHARED')}))
    return dict(schema='acfqp.source_coverage.v185.summary', complete=True,
        SOURCE=dict(roots=len(roots['SOURCE']), old=47, new=96, design_groups=len({row['source_id'] for row in roots['SOURCE']}), selected_lambda=selection['selected_lambda'],
            source_selection=[dict(lambda_value=row['lambda_value'], utility=row['utility']) for row in selection['candidates']]),
        expanded=expanded, original=original, coverage_effects=effects, replica_coverage_effects=replica_effects,
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=15)


def native_binding(root, native, teacher):
    """Bind unchanged V184 acquisition output without repeating its integration."""
    legal = [action for action in ACTIONS if action in root['action_map'].values()]
    if native['root_id'] != root['root_id'] or native['status'] != 'ACTIVE' or native['horizon'] != 3 or native['root_index'] != 0 or native['legal_actions'] != legal:
        return False
    fractions = {action: [Fraction(p, q) for p, q in native['action_component_fractions'][action]] for action in legal}
    if any(native['action_components'][action] != list(map(float, fractions[action])) for action in legal):
        return False
    if any(native['immediate_rewards'][actual] != root['immediate_rewards'][action] for action, actual in root['action_map'].items()):
        return False
    root_teachers = [row['action'] for row in teacher if row['horizon'] == 3 and row['board'] == root['board']]
    action = native['teacher_action']
    if root_teachers != [action] or action not in legal or native['continuation_components'] != native['action_components'][action]:
        return False
    oracle = legal[0]
    for action in legal[1:]:
        if exact.utility(fractions[action]) > exact.utility(fractions[oracle])+Fraction(1, 10**12):
            oracle = action
    return native['oracle_action'] == oracle and native['oracle_components'] == native['action_components'][oracle]


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io, binding_work = [], Counter(), Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ('stage_checks.json', 'v184_run.json', 'ridge_models.json', 'baseline_models.json', 'learned_rule.json')
    check('five_protocol_frozen_inherited_inputs', [(row['saved_ref'], row['phase']) for row in inputs] ==
        [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    stage, old_run = read('inputs/inherited/stage_checks.json'), read('inputs/inherited/v184_run.json')
    check('settled_V184_run_and_stage', stage['valid'] and old_run['status'] == 'complete')
    old_ridge = read('inputs/inherited/ridge_models.json')['RIDGE']; old_baselines = read('inputs/inherited/baseline_models.json')
    original_source = deepcopy(old_ridge['training_outcomes'])
    check('47_inherited_SOURCE_roots_in_12_groups', len(original_source) == 47 and len({row['source_id'] for row in original_source}) == 12)
    cases = {split: cohort_cases(split) for split in ('SOURCE', 'TARGET')}
    check('new_SOURCE_and_TARGET_fixed_96_board_rosters', read('source_cases.json') == cases['SOURCE'] and read('target_cases.json') == cases['TARGET'])
    source_observed, source_work = observe_roots(cases['SOURCE']); target_observed, target_work = observe_roots(cases['TARGET'])
    source_feature_work = cache_roots(original_source+source_observed); target_feature_work = cache_roots(target_observed)
    check('observation_and_cached_feature_acquisition_costs',
        run['costs']['source_observations']['counts'] == source_work and run['costs']['source_observations']['feature_counts'] == source_feature_work and
        run['costs']['target_observations']['counts'] == target_work and run['costs']['target_observations']['feature_counts'] == target_feature_work)
    native, label_costs = read('native_labels.json'), read('label_costs.json')
    expected_ids = [(split, root['root_id']) for split, rows in (('SOURCE', source_observed), ('TARGET', target_observed)) for root in rows]
    check('192_native_label_and_cost_identities', list(native) == ['SOURCE', 'TARGET'] and
        all([row['root_id'] for row in native[split]] == [root['root_id'] for root in rows] for split, rows in (('SOURCE', source_observed), ('TARGET', target_observed))))
    check('ordered_new_label_cost_roster', [(row['cohort'], row['root_id']) for row in label_costs] == expected_ids)
    cost_index = {row['root_id']: row['costs'] for row in label_costs}; canonical, label_work = {}, Counter()
    for split, observed in (('SOURCE', source_observed), ('TARGET', target_observed)):
        labels = []
        for root, raw in zip(observed, native[split], strict=True):
            teacher = read(f"teacher_policy/{root['root_id']}.json")
            check('native_fraction_canonical_and_teacher_root_binding:'+root['root_id'], native_binding(root, raw, teacher))
            binding_work.update(new_label_roots_bound=1, teacher_root_records_inspected=len(teacher),
                exact_component_coordinates_bound=3*len(root['legal_actions']), action_map_bindings=len(root['legal_actions']))
            labels.append(exact.canonical_labels(root, raw, dict(kind='new_exact_V69_FULL', teacher_query='goal_1_risk_1',
                teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')))
            costs = cost_index[root['root_id']]; construction, compilation, export = costs['construction'], costs['compilation'], costs['teacher_export']; n = len(teacher)
            check('unchanged_acquisition_cap_export_and_paid_counts:'+root['root_id'], construction['concrete_states'] <= 200000 and
                construction['concrete_active_states'] == construction['active_states'] == n and
                compilation['model_payload_calls'] == compilation['model_reload_calls'] == 1 and
                compilation['payload_cells'] == construction['registered_states'] == costs['label_evaluation']['kernel_cells_read'] and
                compilation['payload_rows'] == costs['label_evaluation']['kernel_rows_read'] and
                compilation['payload_outcomes'] == costs['label_evaluation']['kernel_outcomes_read'] and costs['label_evaluation']['root_labels_emitted'] == 1 and
                export == dict(teacher_encoding_records_read=construction['concrete_states'], teacher_policy_records=n, teacher_policy_action_reads=n, teacher_policy_tile_reads=16*n))
            for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
                label_work.update({kind+'.'+key: value for key, value in costs[kind].items() if type(value) is int})
        canonical[split] = labels
    source_labels = original_source+canonical['SOURCE']; roots = dict(SOURCE=source_labels, TARGET=target_observed)
    check('inherited_SOURCE_labels_preserved_and_new_labels_bound', same(read('source_labels.json'), source_labels) and same(read('source_new_labels.json'), canonical['SOURCE']))
    check('cached_SOURCE_and_target_observations', same(read('roots.json'), roots))
    check('target_labels_only_after_frozen_models_and_choices', same(read('target_new_labels.json'), canonical['TARGET']) and same(read('labels.json'), canonical['TARGET']))
    fitted, solver_work = fit_expanded(source_labels); selection = fitted['selection']; selection.pop('model')
    check('independent_36_SOURCE_folds_vocabulary_actual_utility_and_selection', same(read('selection.json'), selection))
    check('independent_new_RIDGE_LAYOUT_and_shared_full_vector_models', same(read('models.json'), fitted['models']))
    check('three_SVDs_fourteen_filters_one_shared_solve_and_15_predictors', run['costs']['learning']['counts'] == fitted['costs'] and
        fitted['costs']['ridge_svd_decompositions'] == 3 and fitted['costs']['ridge_coefficient_filters'] == 14 and
        fitted['costs']['shared_lstsq_solves'] == 1 and fitted['costs']['new_predictors_fitted'] == 15)
    models = dict(fitted['models'], OLD_RIDGE=old_ridge, OLD_LAYOUT=old_baselines['LAYOUT'], OLD_SHARED=old_baselines['SHARED'], ONE=old_baselines['ONE'])
    choices, choice_work = freeze_choices(target_observed, models)
    check('seven_fixed_target_models_and_observable_fallback_choices', same(read('choices.json'), choices))
    check('cached_prediction_support_coverage_and_choice_costs', run['costs']['choices']['counts'] == choice_work)
    summary = summarize(roots, canonical['TARGET'], choices, selection)
    check('independent_full_vector_old_new_replica_and_concentration_statistics', same(read('summary.json'), summary))
    phases = ['protocol_frozen', 'source_roots', 'source_labels', 'source_selection', 'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    check('SOURCE_label_selection_then_all_models_and_target_choices_then_TARGET_labels',
        [(row['phase'], row['input_reads']) for row in run['phase_history']] == [(phase, 0 if i == 0 else 5) for i, phase in enumerate(phases)])
    check('paid_input_and_five_acquisition_cost_groups', run['costs']['input_counts'] == dict(json_read_operations=5,
        input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs)) and run['costs']['labels']['counts'] == dict(label_work))
    check('192_new_boards_labels_15_SOURCE_only_fits_and_no_environment_sampling', all(run[key] == 192 for key in
        ('new_boards_generated', 'new_reference_kernel_attempts', 'new_reference_kernels', 'new_teacher_plans', 'new_exact_label_roots', 'completed_roots')) and
        run['resource_cap_per_board'] == 200000 and run['new_predictors_fitted'] == 15 and all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates')))
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema='acfqp.source_coverage.v185.analysis', valid=valid, complete=complete, primary_complete=complete,
        checks=checks, passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0, new_kernels_reintegrated=0, old_models_refitted=0,
            independent_new_label_binding_counts=dict(binding_work), independent_input_counts=dict(io),
            independent_solver_counts=solver_work, independent_ridge_coefficient_solves=14, independent_shared_six_column_solves=1,
            independent_choice_counts=choice_work, reconstructed_production_learning_counts=fitted['costs'],
            independent_observation_counts=dict(SOURCE=source_work, TARGET=target_work), independent_feature_counts=dict(SOURCE=source_feature_work, TARGET=target_feature_work),
            reconstructed_acquisition_cost_counts=dict(label_work), original_run_costs=run['costs'], inherited_cost_refs=run['inherited_cost_refs'],
            test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
