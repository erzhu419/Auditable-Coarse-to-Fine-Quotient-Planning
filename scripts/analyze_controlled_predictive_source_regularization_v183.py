"""Independent SOURCE-only ridge selection using cached observable designs."""
import argparse
from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
import math
from pathlib import Path
import sys
from time import perf_counter
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_rank_layout_consequences_v182 as previous

ACTIONS, EPS, exact = previous.ACTIONS, previous.EPS, previous.exact
LAMBDAS = (0., .0001, .001, .01, .1, 1.)
OUTPUT = PROJECT/'reports/controlled_predictive_source_regularization_v183'


def ridge_coefficients(matrix, targets, roots, lambda_value, work=None):
    matrix, targets = np.asarray(matrix, dtype=float), np.asarray(targets, dtype=float)
    if lambda_value == 0:
        coefficients, _, rank, singular = np.linalg.lstsq(matrix, targets, rcond=None)
        if work is not None:
            work.update(zero_minimum_norm_lstsq_solves=1, least_squares_design_cells=matrix.size, least_squares_target_cells=targets.size)
        return coefficients, int(rank), singular
    penalty = roots*lambda_value
    gram = matrix@matrix.T+penalty*np.eye(matrix.shape[0])
    coefficients = matrix.T@np.linalg.solve(gram, targets)
    if work is not None:
        work.update(positive_row_gram_solves=1, row_gram_matrix_cells=gram.size,
                    row_gram_target_cells=targets.size, ridge_coefficients_cells=coefficients.size)
    return coefficients, None, None


def prepare_design(examples, life=0):
    counts, feature_counts, encoder_counts = Counter(), Counter(), Counter(); roots, features = [], {}
    for original in examples:
        counts['examples_examined'] += 1
        if original['life'] != life:
            counts['other_life_examples_excluded'] += 1; continue
        row = deepcopy(original); legal = [action for action in ACTIONS if action in row['legal_actions']]
        row['legal_actions'] = legal
        row['immediate_rewards'] = {action: float(row['immediate_rewards'][action]) for action in legal}
        row['action_components'] = {action: list(map(float, row['action_components'][action])) for action in legal}
        features[row['root_id']] = previous.action_features_from_root(row, feature_counts); roots.append(row)
        counts.update(examples_fitted=1, root_feature_tile_reads=16, legal_action_reads=len(legal), immediate_reward_reads=len(legal),
                      exact_action_vector_reads=len(legal), label_component_reads=3*len(legal), tail_reward_subtractions=len(legal))
    roots.sort(key=lambda row: row['root_id'])
    vocabulary = [list(token) for token in sorted({tuple(token) for root in roots for action in root['legal_actions'] for token in features[root['root_id']][action]['tokens']})]
    counts.update(source_vocabulary_tokens=len(vocabulary), vocabulary_token_records_read=sum(40*len(root['legal_actions']) for root in roots))
    indexed = previous.vocabulary_index(vocabulary, encoder_counts)
    action_roots = {action: set() for action in ACTIONS}; pair_roots = {f'{a}|{b}': set() for a, b in combinations(ACTIONS, 2)}
    labels, records = [], []
    for root in roots:
        legal = root['legal_actions']; encoded = {action: previous.encode_action(features[root['root_id']][action], indexed, encoder_counts)[0] for action in legal}
        for action in legal:
            action_roots[action].add(root['root_id'])
        pairs = []
        for ia, ib, weight, target in exact.exact_pair_samples(root):
            a, b = ACTIONS[ia], ACTIONS[ib]; columns = sorted(set(encoded[a]) | set(encoded[b]))
            design = [[column, encoded[a].get(column, 0.)-encoded[b].get(column, 0.)] for column in columns]
            sparse = [[column, value] for column, value in design if value != 0.]
            pair = dict(actions=[a, b], weight=weight, design=sparse, components=target); pairs.append(deepcopy(pair))
            records.append(dict(root_id=root['root_id'], source_id=root['source_id'], **pair)); pair_roots[f'{a}|{b}'].add(root['root_id'])
            counts.update(paired_vector_labels=1, paired_component_subtractions=3, layout_pair_rows=1, layout_design_value_lookups=2*len(columns),
                          layout_design_subtractions=len(columns), layout_nonzero_design_entries=len(sparse))
        labels.append(dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=legal, label_kind='exact_enumerated_vector', pairs=pairs))
    matrix, targets = np.zeros((len(records), 6+len(vocabulary))), np.zeros((len(records), 3))
    for index, record in enumerate(records):
        scale = math.sqrt(record['weight'])
        for column, value in record['design']:
            matrix[index, column] = scale*value
        targets[index] = [scale*value for value in record['components']]
        counts.update(layout_weight_square_roots=1, layout_weighted_design_scalings=len(record['design']), layout_weighted_target_scalings=3)
    counts.update(layout_design_matrix_cells=matrix.size, layout_target_matrix_cells=targets.size, ridge_design_preparations=1)
    sources = dict(Counter(root['source_id'] for root in roots)); pair_ids = {pair: sorted(ids) for pair, ids in pair_roots.items()}
    return dict(schema='acfqp.source_regularization.v183.design', life=life, vocabulary=vocabulary, roots=roots,
        root_ids=[root['root_id'] for root in roots], source_ids=sorted(sources), source_root_counts=sources,
        action_root_ids={action: sorted(ids) for action, ids in action_roots.items()}, pair_root_ids=pair_ids,
        connected_components=previous.previous.connected_components(pair_ids), fit_labels=labels, pair_records=records, design_format='sparse_columns',
        shape=list(matrix.shape), X=matrix, Y=targets, prepare_counts=dict(counts), feature_counts=dict(feature_counts), encoder_counts=dict(encoder_counts),
        work=dict(counts+feature_counts+encoder_counts))


def decomposition_metadata(design, rank, singular):
    rows, columns = design['X'].shape; width = min(rows, columns)
    cutoff = np.finfo(float).eps*max(rows, columns)*(float(singular[0]) if len(singular) else 0.)
    return dict(shape=[rows, columns], singular_values=singular.tolist(), cutoff=float(cutoff), rank=int(rank),
        work=dict(ridge_svd_attempts=1, ridge_svd_decompositions=1, ridge_svd_matrix_cells=rows*columns,
                  ridge_svd_left_cells=rows*width, ridge_svd_right_cells=width*columns, ridge_target_projection_cells=3*width,
                  ridge_singular_cutoff_tests=width))


def fit_design(design, lambda_value, audit_work):
    coefficients, rank, singular = ridge_coefficients(design['X'], design['Y'], len(design['roots']), lambda_value, audit_work)
    width = min(design['X'].shape); counts = Counter(ridge_coefficient_filters=1, ridge_predictors_fitted=1,
        ridge_singular_filter_values=width, ridge_projected_component_scalings=3*width, ridge_coefficient_cells=coefficients.size)
    losses, residuals = [0., 0., 0.], []
    for row in design['pair_records']:
        prediction = [float(sum(value*coefficients[column, k] for column, value in row['design'])) for k in range(3)]
        residual = [prediction[k]-row['components'][k] for k in range(3)]; weighted = [row['weight']*value*value for value in residual]
        losses = [losses[k]+weighted[k] for k in range(3)]
        residuals.append(dict(deepcopy(row), predicted_components=prediction, residual_components=residual,
                              weighted_component_losses=weighted, weighted_loss=sum(weighted)))
        counts.update(ridge_fit_prediction_coefficient_reads=3*len(row['design']), ridge_fit_residual_component_subtractions=3, ridge_fit_weighted_component_losses=3)
    penalty = float(lambda_value*np.sum(coefficients*coefficients)); counts['ridge_penalty_coefficient_squares'] += coefficients.size
    return dict(coefficients=coefficients.tolist(), component_losses=losses, loss=sum(losses), root_mean_loss=sum(losses)/len(design['roots']),
                penalty=penalty, objective=sum(losses)/len(design['roots'])+penalty, residuals=residuals, counts=dict(counts)), rank, singular


def model_from_fit(design, decomposition, fitted, lambda_value, source_folds):
    counts = Counter(design['prepare_counts'])+Counter(decomposition['work'])+Counter(fitted['counts'])
    return dict(schema='acfqp.source_regularization.v183.model', mode='RIDGE', life=design['life'], query='risk1',
        native_teacher_query='goal_1_risk_1', horizon=3, label_kind='exact_enumerated_vector', feature_names=list(previous.previous.FEATURE_NAMES),
        vocabulary=deepcopy(design['vocabulary']), design_format='sparse_columns', coefficients=fitted['coefficients'],
        rank=decomposition['rank'], singular_values=decomposition['singular_values'], component_losses=fitted['component_losses'], loss=fitted['loss'],
        root_mean_loss=fitted['root_mean_loss'], penalty=fitted['penalty'], objective=fitted['objective'],
        constants=dict(min_action_roots=4, epsilon=EPS, goal_rank=11, aggregate_columns=6, columns=6+len(design['vocabulary']),
            token_weights=dict(cell=.25, horizontal=1/math.sqrt(12), vertical=1/math.sqrt(12)), intercept=False,
            lambda_value=lambda_value, penalty_normalization='ROOT_MEAN', rcond=None),
        root_ids=list(design['root_ids']), source_ids=list(design['source_ids']), source_root_counts=deepcopy(design['source_root_counts']),
        source_folds=deepcopy(source_folds), action_root_ids=deepcopy(design['action_root_ids']), pair_root_ids=deepcopy(design['pair_root_ids']),
        connected_components=deepcopy(design['connected_components']), fit_labels=deepcopy(design['fit_labels']), fit_residuals=fitted['residuals'],
        training_outcomes=deepcopy(design['roots']), fit_counts=dict(counts), feature_counts=dict(design['feature_counts']), encoder_counts=dict(design['encoder_counts']))


def score_heldout(model, roots):
    counts, groups, choices = Counter(), {}, []
    keys = ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards', 'fallback_action', 'layout_features')
    for root in sorted(roots, key=lambda row: row['root_id']):
        observable = {key: root[key] for key in keys}
        if 'action_map' in root:
            observable['action_map'] = root['action_map']
        decision = previous.choose_action(model, observable, counts); action = decision['canonical_action']
        vector = list(map(float, root['action_components'][action])); value = exact.utility(vector)
        counts.update(heldout_action_vector_reads=1, heldout_component_reads=3, heldout_utility_evaluations=1)
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision, components=vector, utility=value))
    records = []
    for source, vectors in sorted(groups.items()):
        mean = [sum(vector[k] for vector in vectors)/len(vectors) for k in range(3)]
        records.append(dict(source_id=source, roots=len(vectors), components=mean, utility=exact.utility(mean)))
        counts.update(heldout_group_component_means=3, heldout_group_utility_evaluations=1)
    return records, choices, dict(counts)


def select_regularization(examples, life=0):
    examples = list(examples); sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != 12:
        raise ValueError('Twelve fixed SOURCE design groups required')
    source_folds = [sources[::2], sources[1::2]]; costs = Counter(source_fold_assignments=12, regularization_candidates=6)
    audit_work, designs, heldouts, saved_folds, metadata = Counter(), [], [], [], []
    for fold, heldout in enumerate(source_folds):
        train_sources = [source for source in sources if source not in heldout]
        design = prepare_design([row for row in examples if row['life'] == life and row['source_id'] in train_sources], life)
        designs.append(design); costs.update(design['work'])
        heldouts.append([row for row in examples if row['life'] == life and row['source_id'] in heldout])
        saved_folds.append(dict(fold=fold, train_sources=train_sources, heldout_sources=list(heldout),
                                design={key: value for key, value in design.items() if key not in ('X', 'Y')}))
    candidates, selected, best = [], LAMBDAS[0], None
    for lambda_value in LAMBDAS:
        fold_results, groups = [], []
        for fold in range(2):
            fitted, rank, singular = fit_design(designs[fold], lambda_value, audit_work); costs.update(fitted['counts'])
            if lambda_value == 0:
                meta = decomposition_metadata(designs[fold], rank, singular); metadata.append(meta); costs.update(meta['work'])
                saved_folds[fold]['decomposition'] = meta
            model = model_from_fit(designs[fold], metadata[fold], fitted, lambda_value, source_folds)
            records, choices, prediction_counts = score_heldout(model, heldouts[fold]); costs.update(prediction_counts); groups.extend(records)
            fold_results.append(dict(fold=fold, coefficients=fitted['coefficients'], component_losses=fitted['component_losses'], loss=fitted['loss'],
                root_mean_loss=fitted['root_mean_loss'], penalty=fitted['penalty'], objective=fitted['objective'], group_records=records,
                choices=choices, prediction_counts=prediction_counts, coefficient_counts=fitted['counts']))
        groups.sort(key=lambda row: row['source_id']); utility = sum(row['utility'] for row in groups)/len(sources)
        costs.update(regularization_group_mean_reads=12, regularization_score_comparisons=1)
        candidates.append(dict(lambda_value=lambda_value, utility=utility, group_records=groups, fold_results=fold_results))
        if best is None or utility > best+EPS:
            selected, best = lambda_value, utility
    full = prepare_design(examples, life); costs.update(full['work'])
    fitted, rank, singular = fit_design(full, selected, audit_work); costs.update(fitted['counts'])
    if selected > 0:
        singular = np.linalg.svd(full['X'], compute_uv=False); cutoff = np.finfo(float).eps*max(full['X'].shape)*(singular[0] if len(singular) else 0.)
        rank = int(sum(singular > cutoff)); audit_work.update(final_singular_values_only_decompositions=1, final_singular_values_matrix_cells=full['X'].size)
    meta = decomposition_metadata(full, rank, singular); costs.update(meta['work'])
    return dict(schema='acfqp.source_regularization.v183.selection', life=life, lambdas=list(LAMBDAS), source_folds=source_folds,
        folds=saved_folds, candidates=candidates, selected_lambda=selected, selected_utility=best,
        model=model_from_fit(full, meta, fitted, selected, source_folds), costs=dict(costs)), dict(audit_work)


def summarize(roots, labels, choices, selection):
    summaries = {}
    for name in ('RIDGE', 'LAYOUT', 'SHARED', 'RAW'):
        row = exact.summarize(roots, labels, choices[name], {'TREE': dict(nodes=[], candidate_records=[])})
        del row['learned_splits'], row['candidate_reasons']; row['model_kind'] = name; summaries[name] = row
    return dict(schema='acfqp.source_regularization.v183.summary', complete=True, selected_lambda=selection['selected_lambda'],
        source_selection=[dict(lambda_value=row['lambda_value'], utility=row['utility'], group_records=deepcopy(row['group_records'])) for row in selection['candidates']],
        RIDGE=summaries['RIDGE'], ridge_minus_layout=previous.previous.paired_contrast(roots, summaries['RIDGE'], summaries['LAYOUT']),
        ridge_minus_shared=previous.previous.paired_contrast(roots, summaries['RIDGE'], summaries['SHARED']),
        ridge_minus_raw=previous.previous.paired_contrast(roots, summaries['RIDGE'], summaries['RAW']),
        feature_coverage=previous.feature_coverage(choices['RIDGE']), new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=13)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, work = [], Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); work.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ['stage_checks.json', 'run.json', 'roots.json', 'choices.json', 'source_labels.json', 'labels.json']
    check('fixed_six_input_order_and_target_label_freeze', [(row['saved_ref'], row['phase']) for row in inputs] ==
          [(f'inputs/inherited/{name}', 'preparing' if i < 5 else 'target_labels') for i, name in enumerate(names)])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        work.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input_bytes:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    check('input_costs', run['costs']['input_counts'] == dict(json_read_operations=6, input_bytes_read=sum(row['bytes'] for row in inputs)))
    stage, inherited_run = read('inputs/inherited/stage_checks.json'), read('inputs/inherited/run.json')
    check('inherited_V182_settled_complete', stage['valid'] and inherited_run['status'] == 'complete')
    roots, old_choices = read('inputs/inherited/roots.json'), read('inputs/inherited/choices.json')
    source_labels = read('inputs/inherited/source_labels.json'); features = {root['root_id']: root['layout_features'] for root in roots['SOURCE']}
    selection, solver_work = select_regularization([dict(deepcopy(row), layout_features=deepcopy(features[row['root_id']])) for row in source_labels])
    model = selection.pop('model'); saved_selection, saved_model = read('selection.json'), read('models.json')
    check('independent_SOURCE_only_folds_vocab_support_ridge_and_actual_policy_selection', exact._equal(saved_selection, selection) and exact._equal(selection, saved_selection))
    check('independent_selected_full_SOURCE_ridge_model', exact._equal(saved_model, dict(RIDGE=model)) and exact._equal(dict(RIDGE=model), saved_model))
    check('three_preparations_decompositions_and_thirteen_filters_costs', run['costs']['selection_and_final_fit']['counts'] == selection['costs'] and
          selection['costs']['ridge_design_preparations'] == selection['costs']['ridge_svd_decompositions'] == 3 and selection['costs']['ridge_predictors_fitted'] == 13)
    ridge, choice_work = previous.layout_choices(roots, model, old_choices['RAW']); choices = dict(deepcopy(old_choices), RIDGE=ridge); saved_choices = read('choices.json')
    check('all_old_choices_inherited_without_refit', all(saved_choices[name] == old_choices[name] for name in ('LAYOUT', 'SHARED', 'RAW', 'STRUCTURE')))
    check('new_choices_frozen_with_selected_SOURCE_model', exact._equal(saved_choices['RIDGE'], ridge) and exact._equal(ridge, saved_choices['RIDGE']))
    check('new_choice_cache_and_encoding_costs', run['costs']['choice_counts'] == choice_work)
    labels = read('inputs/inherited/labels.json')
    check('unchanged_SOURCE_and_TARGET_labels', read('labels.json') == labels and labels['SOURCE'] == source_labels)
    summary = summarize(roots, labels, choices, selection); saved_summary = read('summary.json')
    check('independent_full_vector_policy_regret_and_feature_coverage', exact._equal(saved_summary, summary) and exact._equal(summary, saved_summary))
    check('SOURCE_selection_then_model_choices_then_target_labels', [row['phase'] for row in run['phase_history']] ==
          ['source_selection', 'models_frozen', 'target_choices_frozen', 'target_labels', 'complete'] and
          [row['input_reads'] for row in run['phase_history']] == [5, 5, 5, 5, 6])
    check('thirteen_small_independent_coefficient_solves', solver_work['zero_minimum_norm_lstsq_solves']+solver_work['positive_row_gram_solves'] == 13)
    check('cached_features_and_no_new_physical_samples_or_native_updates', run['new_predictors_fitted'] == 13 and all(run[key] == 0 for key in
          ('new_environment_samples', 'new_source_games', 'new_native_weight_updates', 'new_features_computed')))
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema='acfqp.source_regularization.v183.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0, old_models_refitted=0, features_recomputed=0,
            inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], original_run_costs=run['costs'], independent_input_counts=dict(work),
            reconstructed_production_selection_counts=selection['costs'], independent_solver_counts=solver_work,
            independent_coefficient_solves=13, independent_choice_counts=choice_work, seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
