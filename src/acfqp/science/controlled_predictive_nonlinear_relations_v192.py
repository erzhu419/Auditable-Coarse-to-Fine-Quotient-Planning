"""SOURCE-selected RBF continuation vectors on the frozen V190 relation cache."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from math import exp, sqrt

import numpy as np

from . import controlled_predictive_merge_relations_v190 as relation
from . import controlled_predictive_consequence_partition_v172 as estimation
from . import controlled_predictive_exact_h3_v177 as exact
from .controlled_predictive_source_regularization_v183 import RegularizationExecutionError

SCHEMA = 'acfqp.nonlinear_relations.v192'
ACTIONS, EPSILON = estimation.ACTIONS, estimation.EPSILON
GAMMAS, LAMBDAS = (.25, 1., 4.), (.0001, .001, .01, .1, 1.)
SOURCE_ROOTS, SOURCE_GROUPS, COLUMNS = 143, 36, 98


def _features(root, counts):
    """Read an already frozen cache; never swipe or derive new features."""
    result = {action: list(map(float, root['relation_features'][action]))
              for action in root['legal_actions']}
    if any(len(vector) != COLUMNS for vector in result.values()):
        raise ValueError('fixed 98-column V190 relation cache required')
    counts.update(nonlinear_feature_cache_reads=1,
                  nonlinear_feature_value_reads=COLUMNS*len(result))
    return result


def _distance(first, second):
    return sum((first[index]-second[index])**2 for index in range(COLUMNS))


def prepare_design(examples, life=0):
    counts, roots, seen = Counter(), [], set()
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
            raise ValueError('one complete vector for every distinct legal action required')
        root = deepcopy(raw)
        root['legal_actions'] = legal
        root['immediate_rewards'] = {a: float(raw['immediate_rewards'][a]) for a in legal}
        root['action_components'] = {a: list(map(float, raw['action_components'][a])) for a in legal}
        if any(len(vector) != 3 for vector in root['action_components'].values()):
            raise ValueError('complete reward/failure/success vectors required')
        roots.append(root)
        counts.update(examples_fitted=1, legal_action_reads=len(legal), immediate_reward_reads=len(legal),
                      exact_action_vector_reads=len(legal), label_component_reads=3*len(legal),
                      tail_reward_subtractions=len(legal))
    roots.sort(key=lambda row: row['root_id'])
    if not roots:
        raise ValueError('same-teacher exact SOURCE roots required')
    centers, labels, records = [], [], []
    action_roots = {action: set() for action in ACTIONS}
    pair_roots = {estimation._pair_key(a, b): set() for a, b in combinations(ACTIONS, 2)}
    for root in roots:
        features = _features(root, counts)
        legal, center_ids = root['legal_actions'], {}
        for action in legal:
            center_ids[action] = len(centers)
            centers.append(dict(root_id=root['root_id'], source_id=root['source_id'],
                                action=action, features=features[action]))
            action_roots[action].add(root['root_id'])
        tails = {a: [root['action_components'][a][0]-root['immediate_rewards'][a],
                     *root['action_components'][a][1:]] for a in legal}
        pairs = list(combinations(legal, 2))
        weight = 1./len(pairs) if pairs else 0.
        label = dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=legal,
                     label_kind='exact_enumerated_vector', pairs=[])
        for first, second in pairs:
            pair = dict(actions=[first, second], center_indices=[center_ids[first], center_ids[second]],
                        weight=weight, scale=sqrt(weight),
                        components=[tails[first][i]-tails[second][i] for i in range(3)])
            label['pairs'].append(deepcopy(pair))
            records.append(dict(root_id=root['root_id'], source_id=root['source_id'], **pair))
            pair_roots[estimation._pair_key(first, second)].add(root['root_id'])
            counts.update(paired_vector_labels=1, paired_component_subtractions=3,
                          nonlinear_pair_rows=1, nonlinear_weight_square_roots=1)
        labels.append(label)
    X = np.asarray([row['features'] for row in centers], dtype=float)
    Y = np.asarray([[value*row['scale'] for value in row['components']] for row in records], dtype=float).reshape(-1, 3)
    D = np.zeros((len(centers), len(centers)))
    nonzero = []
    for first, second in combinations(range(len(centers)), 2):
        value = _distance(centers[first]['features'], centers[second]['features'])
        D[first, second] = D[second, first] = value
        if value > 0.:
            nonzero.append(value)
    if not nonzero:
        raise ValueError('SOURCE centers require a nonzero distance for the frozen median bandwidth')
    median = float(np.median(nonzero))
    distance_pairs = len(centers)*(len(centers)-1)//2
    counts.update(nonlinear_design_preparations=1, nonlinear_centers=len(centers),
        nonlinear_center_matrix_cells=X.size, nonlinear_target_matrix_cells=Y.size,
        nonlinear_weighted_target_scalings=Y.size, nonlinear_distance_pairs=distance_pairs,
        nonlinear_distance_coordinate_subtractions=COLUMNS*distance_pairs,
        nonlinear_distance_coordinate_squares=COLUMNS*distance_pairs,
        nonlinear_distance_component_sums=COLUMNS*distance_pairs,
        nonlinear_distance_matrix_cells=D.size, nonlinear_nonzero_distance_tests=distance_pairs,
        nonlinear_median_distance_values=len(nonzero), nonlinear_median_computations=1)
    source_counts = dict(Counter(root['source_id'] for root in roots))
    action_ids = {action: sorted(ids) for action, ids in action_roots.items()}
    pair_ids = {pair: sorted(ids) for pair, ids in pair_roots.items()}
    return dict(schema=SCHEMA+'.design', mode='NONLINEAR', life=life,
        basis=relation.basis_metadata(), feature_names=list(relation.FEATURE_NAMES),
        roots=roots, root_ids=[root['root_id'] for root in roots], source_ids=sorted(source_counts),
        source_root_counts=source_counts, action_root_ids=action_ids, pair_root_ids=pair_ids,
        connected_components=estimation._components(pair_ids), fit_labels=labels, pair_records=records,
        centers=centers, center_shape=list(X.shape), shape=[len(records), len(centers)],
        design_format='weighted_center_differences', median_squared_distance=median,
        X=X, Y=Y, D=D, prepare_counts=dict(counts), feature_counts={}, work=dict(counts))


def _kernel_and_gram(design, gamma, costs):
    D, records = design['D'], design['pair_records']
    K = np.empty_like(D)
    for first in range(len(K)):
        K[first, first] = 1.
        for second in range(first+1, len(K)):
            K[first, second] = K[second, first] = exp(-gamma*D[first, second]/design['median_squared_distance'])
    first = np.asarray([row['center_indices'][0] for row in records], dtype=int)
    second = np.asarray([row['center_indices'][1] for row in records], dtype=int)
    scales = np.asarray([row['scale'] for row in records], dtype=float)
    H = (K[first[:, None], first[None, :]]-K[first[:, None], second[None, :]]
         -K[second[:, None], first[None, :]]+K[second[:, None], second[None, :]])
    H *= scales[:, None]*scales[None, :]
    H = (H+H.T)/2.
    pairs = len(K)*(len(K)-1)//2
    costs.update(nonlinear_kernel_matrices=1, nonlinear_kernel_exponentials=pairs,
        nonlinear_kernel_distance_reads=pairs, nonlinear_kernel_scalings=2*pairs,
        nonlinear_kernel_matrix_cells=K.size, nonlinear_gram_matrices=1,
        nonlinear_gram_kernel_reads=4*H.size, nonlinear_gram_signed_sums=3*H.size,
        nonlinear_gram_scale_products=H.size, nonlinear_gram_weight_scalings=H.size,
        nonlinear_gram_symmetrizations=1, nonlinear_gram_symmetrization_cells=H.size)
    return K, H


def _decompose(design, gamma, costs):
    before = Counter(costs)
    K, H = _kernel_and_gram(design, gamma, costs)
    costs['nonlinear_eigh_attempts'] += 1
    try:
        values, vectors = np.linalg.eigh(H)
    except Exception as error:
        raise RegularizationExecutionError('NONLINEAR:eigh', costs, error) from error
    projected = vectors.T @ design['Y']
    cutoff = np.finfo(float).eps*max(H.shape)*max(abs(float(value)) for value in values)
    costs.update(nonlinear_eigh_decompositions=1, nonlinear_eigh_matrix_cells=H.size,
        nonlinear_eigh_vector_cells=vectors.size, nonlinear_eigh_values=len(values),
        nonlinear_target_projection_cells=projected.size,
        nonlinear_target_projection_products=3*H.size,
        nonlinear_eigenvalue_rank_tests=len(values))
    metadata = dict(gamma=gamma, median_squared_distance=design['median_squared_distance'],
        shape=list(H.shape), eigenvalues=values.tolist(), cutoff=float(cutoff),
        rank=int(np.sum(values > cutoff)), minimum_eigenvalue=float(values[0]),
        work=dict(Counter(costs)-before))
    return dict(K=K, H=H, eigenvalues=values, vectors=vectors, projected=projected, metadata=metadata)


def _filter(design, decomposition, lambda_value, costs):
    before = Counter(costs)
    costs['nonlinear_filter_attempts'] += 1
    try:
        shifted = decomposition['eigenvalues']+len(design['roots'])*lambda_value
        alpha = decomposition['vectors'] @ (decomposition['projected']/shifted[:, None])
        coefficients = np.zeros((len(design['centers']), 3))
        for index, row in enumerate(design['pair_records']):
            first, second = row['center_indices']
            contribution = row['scale']*alpha[index]
            coefficients[first] += contribution
            coefficients[second] -= contribution
        prediction = decomposition['H'] @ alpha
        residual = prediction-design['Y']
        component_losses = np.sum(residual*residual, axis=0)
        energy = float(np.sum(alpha*prediction))
        penalty = lambda_value*energy
        residuals = [dict(**row,
            predicted_components=(prediction[index]/row['scale']).tolist(),
            residual_components=(residual[index]/row['scale']).tolist(),
            weighted_component_losses=(residual[index]*residual[index]).tolist(),
            weighted_loss=float(np.sum(residual[index]*residual[index])))
            for index, row in enumerate(design['pair_records'])]
    except Exception as error:
        raise RegularizationExecutionError('NONLINEAR:filter', costs, error) from error
    p, m = len(design['pair_records']), len(design['centers'])
    costs.update(nonlinear_coefficient_filters=1, nonlinear_predictors_fitted=1, new_predictors_fitted=1,
        nonlinear_eigenvalue_shifts=p, nonlinear_projected_component_divisions=3*p,
        nonlinear_dual_reconstruction_products=3*p*p, nonlinear_dual_coefficient_cells=alpha.size,
        nonlinear_center_coefficient_cells=3*m, nonlinear_center_coefficient_scalings=3*p,
        nonlinear_center_coefficient_accumulations=6*p, nonlinear_fit_prediction_products=3*p*p,
        nonlinear_fit_residual_subtractions=3*p, nonlinear_fit_residual_squares=3*p,
        nonlinear_rkhs_energy_products=3*p, nonlinear_penalty_scalings=1,
        nonlinear_residual_export_divisions=6*p)
    loss = float(np.sum(component_losses))
    return dict(coefficients=coefficients.tolist(), dual_coefficients=alpha.tolist(),
        component_losses=component_losses.tolist(), loss=loss, root_mean_loss=loss/len(design['roots']),
        rkhs_energy=energy, penalty=penalty, objective=loss/len(design['roots'])+penalty,
        residuals=residuals, counts=dict(Counter(costs)-before))


def _model(design, decomposition, fitted, lambda_value, source_folds):
    metadata = decomposition['metadata']
    counts = Counter(design['work'])+Counter(metadata['work'])+Counter(fitted['counts'])
    return dict(schema=SCHEMA+'.model', mode='NONLINEAR', life=design['life'], query='risk1',
        native_teacher_query=exact.QUERY, horizon=exact.HORIZON, label_kind='exact_enumerated_vector',
        feature_names=list(relation.FEATURE_NAMES), basis=relation.basis_metadata(),
        design_format=design['design_format'], centers=deepcopy(design['centers']),
        coefficients=fitted['coefficients'], dual_coefficients=fitted['dual_coefficients'],
        gamma=metadata['gamma'], median_squared_distance=design['median_squared_distance'],
        eigenvalues=metadata['eigenvalues'], rank=metadata['rank'],
        eigenvalue_cutoff=metadata['cutoff'], minimum_eigenvalue=metadata['minimum_eigenvalue'],
        component_losses=fitted['component_losses'], loss=fitted['loss'],
        root_mean_loss=fitted['root_mean_loss'], rkhs_energy=fitted['rkhs_energy'],
        penalty=fitted['penalty'], objective=fitted['objective'],
        constants=dict(min_action_roots=estimation.MIN_ACTION_ROOTS, epsilon=EPSILON,
            columns=COLUMNS, intercept=False, gamma=metadata['gamma'], lambda_value=lambda_value,
            bandwidth_normalization='TRAIN_CENTER_NONZERO_DISTANCE_MEDIAN',
            penalty_normalization='ROOT_MEAN', norm='RBF_RKHS'),
        root_ids=list(design['root_ids']), source_ids=list(design['source_ids']),
        source_root_counts=deepcopy(design['source_root_counts']), source_folds=deepcopy(source_folds),
        action_root_ids=deepcopy(design['action_root_ids']), pair_root_ids=deepcopy(design['pair_root_ids']),
        connected_components=deepcopy(design['connected_components']),
        fit_labels=deepcopy(design['fit_labels']), fit_residuals=fitted['residuals'],
        training_outcomes=deepcopy(design['roots']), fit_counts=dict(counts), feature_counts={})


def choose_action(payload, root, counts=None):
    if payload['life'] != root['life']:
        raise ValueError('model and root require the same frozen teacher')
    legal = [a for a in ACTIONS if a in root['legal_actions']]
    if not legal or len(legal) != len(root['legal_actions']) or root['fallback_action'] not in legal:
        raise ValueError('distinct legal actions and observable-only fallback required')
    work = Counter(nonlinear_decisions=1, nonlinear_legal_action_reads=len(legal))
    features = _features(dict(root, legal_actions=legal), work)
    action_counts = {a: len(payload['action_root_ids'][a]) for a in legal}
    pair_counts = {estimation._pair_key(a, b): len(payload['pair_root_ids'][estimation._pair_key(a, b)])
                   for a, b in combinations(legal, 2)}
    connected = deepcopy(payload['connected_components'])
    component_id = {a: index for index, group in enumerate(connected) for a in group}
    work.update(nonlinear_action_support_lookups=len(legal), nonlinear_pair_support_lookups=len(pair_counts),
                nonlinear_component_membership_lookups=len(legal))
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif any(action_counts[a] < estimation.MIN_ACTION_ROOTS for a in legal):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component_id[a] for a in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback, reason = None, False, 'selected'
    predicted = {}
    for action in legal:
        kernels = [exp(-payload['gamma']*_distance(features[action], center['features'])
                       /payload['median_squared_distance']) for center in payload['centers']]
        vector = [sum(kernels[index]*payload['coefficients'][index][component]
                      for index in range(len(kernels))) for component in range(3)]
        vector[0] += root['immediate_rewards'][action]
        predicted[action] = vector
        centers = len(kernels)
        work.update(nonlinear_prediction_distance_pairs=centers,
            nonlinear_prediction_feature_reads=2*COLUMNS*centers,
            nonlinear_prediction_distance_subtractions=COLUMNS*centers,
            nonlinear_prediction_distance_squares=COLUMNS*centers,
            nonlinear_prediction_distance_sums=COLUMNS*centers,
            nonlinear_prediction_kernel_exponentials=centers, nonlinear_prediction_kernel_scalings=2*centers,
            nonlinear_prediction_products=3*centers, nonlinear_prediction_coefficient_reads=3*centers,
            nonlinear_prediction_component_evaluations=3,
            nonlinear_immediate_reward_reads=1, nonlinear_reward_additions=1)
    pairs = {}
    for first, second in combinations(legal, 2):
        if component_id[first] == component_id[second]:
            pairs[estimation._pair_key(first, second)] = [predicted[first][i]-predicted[second][i] for i in range(3)]
            work['nonlinear_predicted_pair_subtractions'] += 3
    if selected is None:
        selected, best = legal[0], None
        for action in legal:
            vector = predicted[action]
            value = vector[0]-vector[1]+vector[2]
            work['nonlinear_utility_evaluations'] += 1
            if best is None or value > best+EPSILON:
                selected, best = action, value
    result = dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=fallback, leaf=0,
        reason=reason, predicted_components=predicted, predicted_pairs=pairs,
        support=dict(action_root_counts=action_counts, pair_root_counts=pair_counts,
                     connected_components=connected, required_actions=legal, complete=not fallback),
        work=dict(work), feature_work={})
    if counts is not None:
        counts.update(work)
    return result


def _observable(root):
    keys = ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards',
            'fallback_action', 'action_map', 'relation_features')
    return {key: root[key] for key in keys}


def _heldout(model, roots):
    counts, groups, choices = Counter(), {}, []
    for root in sorted(roots, key=lambda row: row['root_id']):
        decision = choose_action(model, _observable(root), counts)
        vector = list(map(float, root['action_components'][decision['canonical_action']]))
        utility = vector[0]-vector[1]+vector[2]
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision,
                            components=vector, utility=utility))
        counts.update(heldout_action_vector_reads=1, heldout_component_reads=3, heldout_utility_evaluations=1)
    records = []
    for source in sorted(groups):
        mean = [sum(vector[i] for vector in groups[source])/len(groups[source]) for i in range(3)]
        records.append(dict(source_id=source, roots=len(groups[source]), components=mean,
                            utility=mean[0]-mean[1]+mean[2]))
        counts.update(heldout_group_component_means=3, heldout_group_utility_evaluations=1)
    return records, choices, dict(counts)


def _retained_design(design):
    return {key: value for key, value in design.items() if key not in ('X', 'Y', 'D')}


def _select(examples, life):
    sources = sorted({root['source_id'] for root in examples})
    if len(sources) != SOURCE_GROUPS:
        raise ValueError('thirty-six fixed SOURCE groups required')
    source_folds = [sources[::2], sources[1::2]]
    costs = Counter(source_fold_assignments=len(sources), nonlinear_candidates=len(GAMMAS)*len(LAMBDAS))
    designs, heldouts, folds = [], [], []
    for fold, heldout_sources in enumerate(source_folds):
        train_sources = [source for source in sources if source not in heldout_sources]
        design = prepare_design([root for root in examples if root['source_id'] in train_sources], life)
        costs.update(design['work'])
        designs.append(design)
        heldouts.append([root for root in examples if root['source_id'] in heldout_sources])
        folds.append(dict(fold=fold, train_sources=train_sources, heldout_sources=list(heldout_sources),
                          design=_retained_design(design), decompositions=[]))
    candidates, selected_gamma, selected_lambda, best = [], GAMMAS[0], LAMBDAS[0], None
    for gamma in GAMMAS:
        decompositions = [_decompose(design, gamma, costs) for design in designs]
        for fold, decomposition in enumerate(decompositions):
            folds[fold]['decompositions'].append(deepcopy(decomposition['metadata']))
        for lambda_value in LAMBDAS:
            results, groups = [], []
            for fold in range(2):
                fitted = _filter(designs[fold], decompositions[fold], lambda_value, costs)
                model = _model(designs[fold], decompositions[fold], fitted, lambda_value, source_folds)
                group_records, choices, prediction_counts = _heldout(model, heldouts[fold])
                costs.update(prediction_counts)
                groups.extend(group_records)
                results.append(dict(fold=fold, coefficients=fitted['coefficients'],
                    dual_coefficients=fitted['dual_coefficients'], component_losses=fitted['component_losses'],
                    loss=fitted['loss'], root_mean_loss=fitted['root_mean_loss'], rkhs_energy=fitted['rkhs_energy'],
                    penalty=fitted['penalty'], objective=fitted['objective'], group_records=group_records,
                    choices=choices, prediction_counts=prediction_counts, coefficient_counts=fitted['counts']))
            groups.sort(key=lambda row: row['source_id'])
            utility = sum(row['utility'] for row in groups)/len(sources)
            candidates.append(dict(gamma=gamma, lambda_value=lambda_value, utility=utility,
                                   group_records=groups, fold_results=results))
            costs.update(nonlinear_group_mean_reads=len(sources), nonlinear_score_comparisons=1)
            if best is None or utility > best+EPSILON:
                selected_gamma, selected_lambda, best = gamma, lambda_value, utility
    final_design = prepare_design(examples, life)
    costs.update(final_design['work'])
    decomposition = _decompose(final_design, selected_gamma, costs)
    fitted = _filter(final_design, decomposition, selected_lambda, costs)
    model = _model(final_design, decomposition, fitted, selected_lambda, source_folds)
    costs['new_predictors_fitted'] = costs['nonlinear_predictors_fitted']
    selection = dict(schema=SCHEMA+'.selection', mode='NONLINEAR', life=life,
        basis=relation.basis_metadata(), gammas=list(GAMMAS), lambdas=list(LAMBDAS), source_folds=source_folds,
        folds=folds, candidates=candidates, selected_gamma=selected_gamma, selected_lambda=selected_lambda,
        selected_utility=best, costs=dict(costs))
    return selection, model


def fit_model(examples, life=0):
    """Fit two SOURCE folds and the selected full model without TARGET labels."""
    rows = [deepcopy(root) for root in examples if root['life'] == life]
    if len(rows) != SOURCE_ROOTS:
        raise ValueError('143 fixed SOURCE roots required')
    selection, model = _select(rows, life)
    return dict(model=model, selection=selection, costs=selection['costs'], cache_counts={})
