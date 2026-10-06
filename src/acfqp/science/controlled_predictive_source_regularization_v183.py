"""SOURCE-group-heldout ridge selection on the frozen V182 cached features."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from math import sqrt

import numpy as np

from . import controlled_predictive_rank_layout_consequences_v182 as layout
from . import controlled_predictive_consequence_partition_v172 as estimation
from . import controlled_predictive_exact_h3_v177 as exact

ACTIONS, EPSILON = estimation.ACTIONS, estimation.EPSILON
LAMBDAS = (0., .0001, .001, .01, .1, 1.)
SCHEMA = 'acfqp.source_regularization.v183'
choose_action = layout.choose_action


class RegularizationExecutionError(RuntimeError):
    def __init__(self, operation, costs, cause):
        self.record = dict(operation=operation, costs=dict(costs), error=str(cause))
        super().__init__(str(cause))


def prepare_design(examples, life=0):
    """Prepare a six-group fold or full SOURCE design without reading other lives."""
    counts, feature_counts, encoder_counts = Counter(), Counter(), Counter()
    rows, seen, features = [], set(), {}
    for raw in examples:
        counts['examples_examined'] += 1
        if raw['life'] != life:
            counts['other_life_examples_excluded'] += 1
            continue
        root_id = raw['root_id']
        if root_id in seen:
            raise ValueError('duplicate exact training root')
        seen.add(root_id)
        legal = [action for action in ACTIONS if action in raw['legal_actions']]
        if not legal or len(legal) != len(raw['legal_actions']) or set(raw['action_components']) != set(legal):
            raise ValueError('one full exact vector for every distinct legal action required')
        if len(raw['canonical_board']) != 16 or 'layout_features' not in raw:
            raise ValueError('frozen sixteen-cell board and cached layout features required')
        root = deepcopy(raw)
        root['legal_actions'] = legal
        root['immediate_rewards'] = {action: float(raw['immediate_rewards'][action]) for action in legal}
        root['action_components'] = {action: list(map(float, raw['action_components'][action])) for action in legal}
        if any(len(vector) != 3 for vector in root['action_components'].values()):
            raise ValueError('complete reward/failure/success vectors required')
        features[root_id] = layout.action_features_from_root(root, feature_counts)
        rows.append(root)
        counts.update(examples_fitted=1, root_feature_tile_reads=16, legal_action_reads=len(legal),
            immediate_reward_reads=len(legal), exact_action_vector_reads=len(legal),
            label_component_reads=3*len(legal), tail_reward_subtractions=len(legal))
    rows.sort(key=lambda row: row['root_id'])
    if not rows:
        raise ValueError('same-history exact training roots required')
    tokens = {tuple(token) for row in rows for action in row['legal_actions']
              for token in features[row['root_id']][action]['tokens']}
    vocabulary = [list(token) for token in sorted(tokens)]
    counts.update(source_vocabulary_tokens=len(vocabulary),
                  vocabulary_token_records_read=sum(40*len(row['legal_actions']) for row in rows))
    indexed = layout._index(vocabulary, encoder_counts)
    action_roots = {action: set() for action in ACTIONS}
    pair_roots = {estimation._pair_key(a, b): set() for a, b in combinations(ACTIONS, 2)}
    labels, records = [], []
    for root in rows:
        legal = root['legal_actions']
        encoded = {action: layout._encode(features[root['root_id']][action], indexed, encoder_counts)[0] for action in legal}
        tails = {action: [root['action_components'][action][0]-root['immediate_rewards'][action],
                          *root['action_components'][action][1:]] for action in legal}
        for action in legal:
            action_roots[action].add(root['root_id'])
        pairs = list(combinations(legal, 2))
        weight = 1./len(pairs) if pairs else 0.
        label = dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=legal,
                     label_kind='exact_enumerated_vector', pairs=[])
        for first, second in pairs:
            columns = sorted(set(encoded[first]) | set(encoded[second]))
            design = [[column, encoded[first].get(column, 0.)-encoded[second].get(column, 0.)] for column in columns]
            sparse = [[column, value] for column, value in design if value != 0.]
            target = [tails[first][i]-tails[second][i] for i in range(3)]
            pair = dict(actions=[first, second], weight=weight, design=sparse, components=target)
            label['pairs'].append(deepcopy(pair))
            records.append(dict(root_id=root['root_id'], source_id=root['source_id'], **pair))
            pair_roots[estimation._pair_key(first, second)].add(root['root_id'])
            counts.update(paired_vector_labels=1, paired_component_subtractions=3,
                layout_pair_rows=1, layout_design_value_lookups=2*len(columns),
                layout_design_subtractions=len(columns), layout_nonzero_design_entries=len(sparse))
        labels.append(label)
    dimensions = 6+len(vocabulary)
    matrix, targets = np.zeros((len(records), dimensions)), np.zeros((len(records), 3))
    for row, record in enumerate(records):
        scale = sqrt(record['weight'])
        for column, value in record['design']:
            matrix[row, column] = value*scale
        targets[row] = [value*scale for value in record['components']]
        counts.update(layout_weight_square_roots=1, layout_weighted_design_scalings=len(record['design']),
                      layout_weighted_target_scalings=3)
    counts.update(layout_design_matrix_cells=matrix.size, layout_target_matrix_cells=targets.size,
                  ridge_design_preparations=1)
    action_ids = {action: sorted(ids) for action, ids in action_roots.items()}
    pair_ids = {pair: sorted(ids) for pair, ids in pair_roots.items()}
    source_counts = dict(Counter(row['source_id'] for row in rows))
    work = counts+feature_counts+encoder_counts
    return dict(schema=SCHEMA+'.design', life=life, vocabulary=vocabulary, roots=rows,
        root_ids=[row['root_id'] for row in rows], source_ids=sorted(source_counts), source_root_counts=source_counts,
        action_root_ids=action_ids, pair_root_ids=pair_ids, connected_components=estimation._components(pair_ids),
        fit_labels=labels, pair_records=records, design_format='sparse_columns',
        shape=list(matrix.shape), X=matrix, Y=targets,
        prepare_counts=dict(counts), feature_counts=dict(feature_counts), encoder_counts=dict(encoder_counts), work=dict(work))


def _decompose(design, costs):
    work = Counter(ridge_svd_attempts=1)
    costs.update(work)
    try:
        left, singular, right = np.linalg.svd(design['X'], full_matrices=False)
    except Exception as error:
        raise RegularizationExecutionError('svd', costs, error) from error
    cutoff = np.finfo(float).eps*max(design['X'].shape)*(float(singular[0]) if len(singular) else 0.)
    projected = left.T @ design['Y']
    completed = Counter(ridge_svd_decompositions=1, ridge_svd_matrix_cells=design['X'].size,
        ridge_svd_left_cells=left.size, ridge_svd_right_cells=right.size,
        ridge_target_projection_cells=projected.size, ridge_singular_cutoff_tests=len(singular))
    costs.update(completed); work.update(completed)
    metadata = dict(shape=list(design['X'].shape), singular_values=singular.tolist(),
        cutoff=float(cutoff), rank=int(np.sum(singular > cutoff)), work=dict(work))
    return dict(singular=singular, right=right, projected=projected, cutoff=cutoff, metadata=metadata)


def _filter(design, decomposition, lambda_value):
    singular = decomposition['singular']
    if lambda_value == 0.:
        scale = np.zeros_like(singular)
        supported = singular > decomposition['cutoff']
        scale[supported] = 1./singular[supported]
    else:
        scale = singular/(singular*singular+len(design['roots'])*lambda_value)
    coefficients = decomposition['right'].T @ (scale[:, None]*decomposition['projected'])
    work = Counter(ridge_coefficient_filters=1, ridge_predictors_fitted=1,
        ridge_singular_filter_values=len(singular), ridge_projected_component_scalings=3*len(singular),
        ridge_coefficient_cells=coefficients.size)
    losses, residuals = [0., 0., 0.], []
    for row in design['pair_records']:
        prediction = [float(sum(value*coefficients[column, i] for column, value in row['design'])) for i in range(3)]
        residual = [prediction[i]-row['components'][i] for i in range(3)]
        weighted = [row['weight']*value*value for value in residual]
        losses = [losses[i]+weighted[i] for i in range(3)]
        residuals.append(dict(**row, predicted_components=prediction, residual_components=residual,
                             weighted_component_losses=weighted, weighted_loss=sum(weighted)))
        work.update(ridge_fit_prediction_coefficient_reads=3*len(row['design']),
                    ridge_fit_residual_component_subtractions=3, ridge_fit_weighted_component_losses=3)
    penalty = float(lambda_value*np.sum(coefficients*coefficients))
    work['ridge_penalty_coefficient_squares'] += coefficients.size
    return dict(coefficients=coefficients.tolist(), component_losses=losses, loss=sum(losses),
        root_mean_loss=sum(losses)/len(design['roots']), penalty=penalty,
        objective=sum(losses)/len(design['roots'])+penalty, residuals=residuals, counts=dict(work))


def _model(design, decomposition, fitted, lambda_value, source_folds=None):
    counts = Counter(design['prepare_counts'])+Counter(decomposition['metadata']['work'])+Counter(fitted['counts'])
    return dict(schema=SCHEMA+'.model', mode='RIDGE', life=design['life'], query='risk1',
        native_teacher_query=exact.QUERY, horizon=exact.HORIZON, label_kind='exact_enumerated_vector',
        feature_names=list(layout.FEATURE_NAMES), vocabulary=deepcopy(design['vocabulary']),
        design_format='sparse_columns', coefficients=fitted['coefficients'], rank=decomposition['metadata']['rank'],
        singular_values=decomposition['metadata']['singular_values'],
        component_losses=fitted['component_losses'], loss=fitted['loss'], root_mean_loss=fitted['root_mean_loss'],
        penalty=fitted['penalty'], objective=fitted['objective'],
        constants=dict(min_action_roots=estimation.MIN_ACTION_ROOTS, epsilon=EPSILON,
            goal_rank=layout.GOAL_RANK, aggregate_columns=6, columns=6+len(design['vocabulary']),
            token_weights=dict(layout.TOKEN_WEIGHTS), intercept=False, lambda_value=lambda_value,
            penalty_normalization='ROOT_MEAN', rcond=None),
        root_ids=list(design['root_ids']), source_ids=list(design['source_ids']),
        source_root_counts=deepcopy(design['source_root_counts']), source_folds=deepcopy(source_folds or []),
        action_root_ids=deepcopy(design['action_root_ids']), pair_root_ids=deepcopy(design['pair_root_ids']),
        connected_components=deepcopy(design['connected_components']),
        fit_labels=deepcopy(design['fit_labels']), fit_residuals=fitted['residuals'],
        training_outcomes=deepcopy(design['roots']), fit_counts=dict(counts),
        feature_counts=dict(design['feature_counts']), encoder_counts=dict(design['encoder_counts']))


def fit_model(examples, lambda_value, life=0):
    """Fit a fixed-grid value; selection reuses each fold's decomposition."""
    if lambda_value not in LAMBDAS:
        raise ValueError('lambda must belong to the frozen grid')
    design = prepare_design(examples, life)
    costs = Counter(design['work'])
    decomposition = _decompose(design, costs)
    fitted = _filter(design, decomposition, lambda_value)
    sources = design['source_ids']
    return _model(design, decomposition, fitted, lambda_value, [sources[::2], sources[1::2]])


def _heldout(model, rows):
    counts, groups, choices = Counter(), {}, []
    for root in sorted(rows, key=lambda row: row['root_id']):
        # Action choice receives no labels. Only its frozen chosen action is scored.
        observable = {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board',
            'legal_actions', 'immediate_rewards', 'fallback_action', 'layout_features')}
        if 'action_map' in root:
            observable['action_map'] = root['action_map']
        decision = choose_action(model, observable, counts)
        action = decision['canonical_action']
        vector = list(map(float, root['action_components'][action]))
        value = vector[0]-vector[1]+vector[2]
        counts.update(heldout_action_vector_reads=1, heldout_component_reads=3, heldout_utility_evaluations=1)
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision,
                            components=vector, utility=value))
    records = []
    for source in sorted(groups):
        vectors = groups[source]
        mean = [sum(vector[i] for vector in vectors)/len(vectors) for i in range(3)]
        records.append(dict(source_id=source, roots=len(vectors), components=mean,
                            utility=mean[0]-mean[1]+mean[2]))
        counts.update(heldout_group_component_means=3, heldout_group_utility_evaluations=1)
    return records, choices, dict(counts)


def select_regularization(examples, life=0):
    """Select by twelve equally weighted heldout SOURCE-group policy utilities."""
    examples = list(examples)
    sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != exact.DESIGN_GROUPS:
        raise ValueError('twelve fixed SOURCE provenance groups required')
    source_folds = [sources[::2], sources[1::2]]
    costs = Counter(source_fold_assignments=len(sources), regularization_candidates=len(LAMBDAS))
    designs, decompositions, heldouts, folds = [], [], [], []
    for fold, heldout_sources in enumerate(source_folds):
        train_sources = [source for source in sources if source not in heldout_sources]
        training = [row for row in examples if row['life'] == life and row['source_id'] in train_sources]
        heldout = [row for row in examples if row['life'] == life and row['source_id'] in heldout_sources]
        design = prepare_design(training, life)
        costs.update(design['work'])
        decomposition = _decompose(design, costs)
        designs.append(design); decompositions.append(decomposition); heldouts.append(heldout)
        saved = {key: value for key, value in design.items() if key not in ('X', 'Y')}
        folds.append(dict(fold=fold, train_sources=train_sources, heldout_sources=list(heldout_sources),
                          design=saved, decomposition=deepcopy(decomposition['metadata'])))
    candidates, selected, best = [], LAMBDAS[0], None
    for lambda_value in LAMBDAS:
        fold_results, all_groups = [], []
        for fold in range(2):
            fitted = _filter(designs[fold], decompositions[fold], lambda_value)
            costs.update(fitted['counts'])
            model = _model(designs[fold], decompositions[fold], fitted, lambda_value, source_folds)
            groups, choices, prediction_counts = _heldout(model, heldouts[fold])
            costs.update(prediction_counts)
            all_groups.extend(groups)
            fold_results.append(dict(fold=fold, coefficients=fitted['coefficients'],
                component_losses=fitted['component_losses'], loss=fitted['loss'],
                root_mean_loss=fitted['root_mean_loss'], penalty=fitted['penalty'], objective=fitted['objective'],
                group_records=groups, choices=choices, prediction_counts=prediction_counts,
                coefficient_counts=fitted['counts']))
        all_groups.sort(key=lambda row: row['source_id'])
        utility = sum(row['utility'] for row in all_groups)/len(sources)
        costs.update(regularization_group_mean_reads=len(sources), regularization_score_comparisons=1)
        candidates.append(dict(lambda_value=lambda_value, utility=utility, group_records=all_groups,
                               fold_results=fold_results))
        if best is None or utility > best+EPSILON:
            selected, best = lambda_value, utility
    final_design = prepare_design(examples, life)
    costs.update(final_design['work'])
    final_decomposition = _decompose(final_design, costs)
    fitted = _filter(final_design, final_decomposition, selected)
    costs.update(fitted['counts'])
    return dict(schema=SCHEMA+'.selection', life=life, lambdas=list(LAMBDAS), source_folds=source_folds,
        folds=folds, candidates=candidates, selected_lambda=selected, selected_utility=best,
        model=_model(final_design, final_decomposition, fitted, selected, source_folds), costs=dict(costs))
