"""Expand SOURCE coverage while keeping features and heldout selection fixed."""
from collections import Counter
from copy import deepcopy
import random

import numpy as np

from . import controlled_predictive_fresh_h3_confirmation_v184 as fresh
from . import controlled_predictive_source_regularization_v183 as ridge
from . import controlled_predictive_rank_layout_consequences_v182 as layout
from . import controlled_predictive_shared_consequences_v179 as shared
from . import controlled_predictive_exact_h3_v177 as exact

SCHEMA = 'acfqp.source_coverage.v185'
REPLICAS = 4
ROOTS_PER_REPLICA = 24
SOURCE_SEED_BASE = 1850100
TARGET_SEED_BASE = 1850200
SOURCE_GROUPS = 36
MODEL_NAMES = ('RIDGE', 'LAYOUT', 'SHARED', 'OLD_RIDGE', 'OLD_LAYOUT', 'OLD_SHARED', 'ONE')
LAMBDAS = ridge.LAMBDAS


def cohort_cases(split):
    if split not in ('SOURCE', 'TARGET'):
        raise ValueError('SOURCE or TARGET cohort required')
    start = SOURCE_SEED_BASE if split == 'SOURCE' else TARGET_SEED_BASE
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(REPLICAS):
        for index in range(ROOTS_PER_REPLICA):
            seed = start+ROOTS_PER_REPLICA*replica+index
            rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]
            first, second = edges[index]
            board[first] = board[second] = 1+index % 10
            for cell in rng.sample([i for i in range(16) if i not in (first, second)], index % 3):
                board[cell] = 0
            cases.append(dict(split=split, replica=replica, stratum=index,
                name=f'v185_{split.lower()}_r{replica:02d}_{index:02d}', horizon=3,
                seed=seed, board=board, vacancies=index % 3))
    return cases


def observe_roots(cases):
    cases = list(cases)
    roots, work = fresh.observe_roots(cases)
    for root, case in zip(roots, cases):
        root['cohort'] = root['split'] = case['split']
        root['source_id'] = (f"DESIGN_SOURCE:{12+6*case['replica']+case['stratum']//4:02d}"
                             if case['split'] == 'SOURCE' else f"FRESH_REPLICA:{case['replica']:02d}")
    return roots, work


def cache_roots(roots):
    work = Counter()
    for root in roots:
        root['layout_features'] = layout.action_features_from_root(root, work)
        root['action_features'] = {action: list(record['aggregate'])
                                   for action, record in root['layout_features'].items()}
        work.update(shared_feature_maps_derived=1,
                    shared_aggregate_cache_values_copied=6*len(root['action_features']))
    return dict(work)


def _shared_model(design, costs, source_folds):
    matrix = design['X'][:, :6].copy()
    work = Counter(shared_lstsq_attempts=1, shared_design_matrix_cells=matrix.size,
                   shared_target_matrix_cells=design['Y'].size)
    costs.update(work)
    try:
        coefficients, _, rank, singular = np.linalg.lstsq(matrix, design['Y'], rcond=None)
    except Exception as error:
        raise ridge.RegularizationExecutionError('shared_lstsq', costs, error) from error
    completed = Counter(shared_lstsq_solves=1, shared_predictors_fitted=1, shared_coefficient_cells=18)
    costs.update(completed); work.update(completed)
    losses, residuals, labels = [0., 0., 0.], [], []
    grouped = {root_id: [] for root_id in design['root_ids']}
    residual_work = Counter()
    for row in design['pair_records']:
        sparse = [[column, value] for column, value in row['design'] if column < 6]
        prediction = [float(sum(value*coefficients[column, i] for column, value in sparse)) for i in range(3)]
        residual = [prediction[i]-row['components'][i] for i in range(3)]
        weighted = [row['weight']*value*value for value in residual]
        losses = [losses[i]+weighted[i] for i in range(3)]
        record = dict(row, design=sparse, predicted_components=prediction, residual_components=residual,
                      weighted_component_losses=weighted, weighted_loss=sum(weighted))
        residuals.append(record)
        grouped[row['root_id']].append(dict(actions=list(row['actions']), weight=row['weight'],
                                          design=sparse, components=list(row['components'])))
        residual_work.update(shared_pair_rows=1, shared_design_entries_examined=len(row['design']),
            shared_nonzero_design_entries=len(sparse), shared_fit_prediction_coefficient_reads=3*len(sparse),
            shared_residual_component_subtractions=3, shared_weighted_component_losses=3)
    costs.update(residual_work); work.update(residual_work)
    for label in design['fit_labels']:
        labels.append(dict(label, pairs=grouped[label['root_id']]))
    return dict(schema=SCHEMA+'.shared_model', mode='SHARED', life=design['life'], query='risk1',
        native_teacher_query=exact.QUERY, horizon=exact.HORIZON, label_kind='exact_enumerated_vector',
        feature_names=list(shared.FEATURE_NAMES), coefficients=coefficients.tolist(), rank=int(rank),
        singular_values=singular.tolist(), component_losses=losses, loss=sum(losses),
        action_root_ids=deepcopy(design['action_root_ids']), pair_root_ids=deepcopy(design['pair_root_ids']),
        connected_components=deepcopy(design['connected_components']),
        constants=dict(min_action_roots=shared.MIN_ACTION_ROOTS, epsilon=shared.EPSILON,
            goal_rank=shared.GOAL_RANK, features=6, intercept=False, ridge=False, rcond=None),
        root_ids=list(design['root_ids']), source_ids=list(design['source_ids']),
        source_folds=deepcopy(source_folds), source_root_counts=deepcopy(design['source_root_counts']),
        fit_labels=labels, fit_residuals=residuals, design_format='sparse_columns',
        training_outcomes=deepcopy(design['roots']), fit_counts=dict(work),
        feature_counts={}, data_design_origin='shared_final_source_design')


def fit_expanded(examples, life=0):
    """Coordinate the unchanged six-lambda procedure over36 SOURCE groups."""
    examples = list(examples)
    sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != SOURCE_GROUPS:
        raise ValueError('thirty-six fixed SOURCE provenance groups required')
    source_folds = [sources[::2], sources[1::2]]
    costs = Counter(source_fold_assignments=len(sources), regularization_candidates=len(LAMBDAS))
    designs, decompositions, heldouts, folds = [], [], [], []
    for fold, heldout_sources in enumerate(source_folds):
        train_sources = [source for source in sources if source not in heldout_sources]
        training = [row for row in examples if row['life'] == life and row['source_id'] in train_sources]
        heldout = [row for row in examples if row['life'] == life and row['source_id'] in heldout_sources]
        design = ridge.prepare_design(training, life)
        costs.update(design['work'])
        decomposition = ridge._decompose(design, costs)
        designs.append(design); decompositions.append(decomposition); heldouts.append(heldout)
        folds.append(dict(fold=fold, train_sources=train_sources, heldout_sources=list(heldout_sources),
            design={key: value for key, value in design.items() if key not in ('X', 'Y')},
            decomposition=deepcopy(decomposition['metadata'])))
    candidates, selected, best = [], LAMBDAS[0], None
    for lambda_value in LAMBDAS:
        results, all_groups = [], []
        for fold in range(2):
            fitted = ridge._filter(designs[fold], decompositions[fold], lambda_value)
            costs.update(fitted['counts'])
            model = ridge._model(designs[fold], decompositions[fold], fitted, lambda_value, source_folds)
            groups, choices, prediction_counts = ridge._heldout(model, heldouts[fold])
            costs.update(prediction_counts)
            all_groups.extend(groups)
            results.append(dict(fold=fold, coefficients=fitted['coefficients'],
                component_losses=fitted['component_losses'], loss=fitted['loss'],
                root_mean_loss=fitted['root_mean_loss'], penalty=fitted['penalty'], objective=fitted['objective'],
                group_records=groups, choices=choices, prediction_counts=prediction_counts,
                coefficient_counts=fitted['counts']))
        all_groups.sort(key=lambda row: row['source_id'])
        utility = sum(row['utility'] for row in all_groups)/len(sources)
        costs.update(regularization_group_mean_reads=len(sources), regularization_score_comparisons=1)
        candidates.append(dict(lambda_value=lambda_value, utility=utility, group_records=all_groups, fold_results=results))
        if best is None or utility > best+ridge.EPSILON:
            selected, best = lambda_value, utility
    final_design = ridge.prepare_design(examples, life)
    costs.update(final_design['work'])
    final_decomposition = ridge._decompose(final_design, costs)
    fitted = ridge._filter(final_design, final_decomposition, selected)
    costs.update(fitted['counts'])
    ridge_model = ridge._model(final_design, final_decomposition, fitted, selected, source_folds)
    unregularized = ridge._filter(final_design, final_decomposition, 0.)
    costs.update(unregularized['counts'])
    layout_model = ridge._model(final_design, final_decomposition, unregularized, 0., source_folds)
    layout_model.update(schema=SCHEMA+'.layout_model', mode='LAYOUT')
    shared_model = _shared_model(final_design, costs, source_folds)
    costs['new_predictors_fitted'] = costs['ridge_predictors_fitted']+costs['shared_predictors_fitted']
    selection = dict(schema=ridge.SCHEMA+'.selection', life=life, lambdas=list(LAMBDAS),
        source_folds=source_folds, folds=folds, candidates=candidates, selected_lambda=selected,
        selected_utility=best, model=ridge_model, costs=dict(costs))
    return dict(models=dict(RIDGE=ridge_model, LAYOUT=layout_model, SHARED=shared_model),
                selection=selection, costs=dict(costs))


def freeze_choices(roots, models):
    """Use only cached observables for every expanded and old frozen model."""
    choices = {mode: [] for mode in (*MODEL_NAMES, 'FALLBACK')}
    work = Counter()
    for root in roots:
        observable = {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board',
            'legal_actions', 'immediate_rewards', 'fallback_action', 'action_map', 'layout_features', 'action_features')}
        for mode in MODEL_NAMES:
            chooser = (shared.choose_action if mode in ('SHARED', 'OLD_SHARED') else
                       exact.choose_action if mode == 'ONE' else layout.choose_action)
            decision = chooser(models[mode], observable)
            work.update(decision['work']); work.update(decision.get('feature_work', {}))
            work['coverage_model_choices'] += 1
            choices[mode].append(dict(root_id=root['root_id'], mode=mode,
                canonical_action=decision['canonical_action'], actual_action=decision['actual_action'],
                fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']
        work['coverage_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK',
            canonical_action=action, actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work=dict(coverage_fallback_choices=1))))
    return choices, dict(work)
