"""Greedy SOURCE applicability partitions selected by complete decision utility.

The three supplied V196 libraries remain unchanged. Temporary training views
cache full R/F/S truth and ordered-pair incidence. A split changes the current
whole-tree predictions, then earns its gain from the actual selected actions,
with equal SOURCE groups and equal roots within each group. Both child means
are installed before preorder recursion; an earlier leaf is never reopened.
Models, selections and decisions retain the V196 field layout. Split nodes add
training_utility_before/after; improvement is their difference, never SSE.
"""
from collections import Counter

import numpy as np

from . import controlled_predictive_relational_program_learning_v196 as programs

SCHEMA = 'acfqp.utility_program_partition.v198'
ACTIONS, EPSILON = programs.ACTIONS, programs.EPSILON
MAX_DEPTHS, MIN_LEAF_ROOTS = programs.MAX_DEPTHS, programs.MIN_LEAF_ROOTS
SOURCE_ROOTS, SOURCE_GROUPS = programs.SOURCE_ROOTS, programs.SOURCE_GROUPS
FEATURE_NAMES = programs.FEATURE_NAMES
PairExecutionError = programs.PairExecutionError
choose_action = programs.choose_action


def prepare_training_view(examples, library, costs=None):
    """Cache one temporary root view per supplied library, including forced roots."""
    counts = costs if costs is not None else Counter()
    counts['training_view_attempts'] += 1
    lookup = {root['root_id']: root for root in examples}
    rows = [lookup[root_id] for root_id in library['root_ids']]
    root_indices = {root['root_id']: index for index, root in enumerate(rows)}
    source_counts = Counter(root['source_id'] for root in rows)
    n = len(rows)
    legal, rewards, truth = np.zeros((n, 4), dtype=bool), np.zeros((n, 4)), np.zeros((n, 4, 3))
    weights, action_counts = np.zeros(n), np.zeros(n, dtype=int)
    for index, root in enumerate(rows):
        actions = programs._legal(root)
        action_counts[index] = len(actions)
        weights[index] = 1./(len(source_counts)*source_counts[root['source_id']])
        for action in actions:
            column = ACTIONS.index(action)
            legal[index, column] = True
            rewards[index, column] = root['immediate_rewards'][action]
            truth[index, column] = root['action_components'][action]
        counts.update(training_view_roots=1, training_view_forced_roots=int(len(actions) == 1),
                      training_view_reward_reads=len(actions), training_view_truth_component_reads=3*len(actions))
    prototypes = library['prototypes']
    prototype_roots = np.asarray([root_indices[row['root_id']] for row in prototypes], dtype=int)
    first_actions = np.asarray([ACTIONS.index(row['actions'][0]) for row in prototypes], dtype=int)
    second_actions = np.asarray([ACTIONS.index(row['actions'][1]) for row in prototypes], dtype=int)
    incidence_scale = 1./(2.*action_counts[prototype_roots])
    features = np.asarray([row['features162'] for row in prototypes], dtype=float)
    counts.update(training_view_preparations=1, training_view_prototypes=len(prototypes),
                  training_view_feature_reads=162*len(prototypes), training_view_incidence_divisions=len(prototypes),
                  training_view_source_weights=n, training_matrix_preparations=1, training_matrix_cells=features.size)
    return dict(root_ids=[row['root_id'] for row in rows], source_ids=sorted(source_counts), legal=legal,
                rewards=rewards, truth=truth, root_weights=weights, action_counts=action_counts,
                prototype_roots=prototype_roots, first_actions=first_actions, second_actions=second_actions,
                incidence_scale=incidence_scale, features=features)


def _moments(prototypes, indices, counts):
    weight, sums = 0., [0., 0., 0.]
    for index in indices:
        row, w = prototypes[index], prototypes[index]['root_mass']
        weight += w
        for component, value in enumerate(row['tail_difference']):
            sums[component] += w*value
    counts.update(tree_moment_sample_reads=len(indices), tree_moment_weight_additions=len(indices),
                  tree_moment_WY_products=3*len(indices), tree_moment_component_additions=3*len(indices))
    return weight, sums


def _incidence(view, indices, counts):
    incidence = np.zeros_like(view['rewards'])
    for index in indices:
        root, scale = view['prototype_roots'][index], view['incidence_scale'][index]
        incidence[root, view['first_actions'][index]] += scale
        incidence[root, view['second_actions'][index]] -= scale
    counts.update(training_incidence_preparations=1, training_incidence_zero_cells=incidence.size,
                  training_incidence_sample_reads=len(indices), training_incidence_additions=2*len(indices))
    return incidence


def _training_actions(theta, view, counts):
    """Use full R/F/S arithmetic followed by the original sequential EPS decoder."""
    utilities = (view['rewards']+theta[:, :, 0])-theta[:, :, 1]+theta[:, :, 2]
    n = len(view['root_ids'])
    selected, best = np.full(n, -1, dtype=int), np.full(n, -np.inf)
    for action in range(4):
        improve = view['legal'][:, action] & ((selected < 0) | (utilities[:, action] > best+EPSILON))
        selected = np.where(improve, action, selected)
        best = np.where(improve, utilities[:, action], best)
    counts.update(training_root_decisions=n,
                  training_action_utility_evaluations=4*n, training_decoder_epsilon_checks=4*n,
                  training_reward_additions=4*n)
    return selected


def _training_utility(theta, view, counts):
    selected = _training_actions(theta, view, counts)
    n = len(view['root_ids'])
    actual = view['truth'][np.arange(n), selected]
    values = actual[:, 0]-actual[:, 1]+actual[:, 2]
    utility = float(np.sum(view['root_weights']*values))
    counts.update(training_utility_passes=1, training_actual_component_reads=3*n,
                  training_actual_utility_evaluations=n, training_root_weight_products=n,
                  training_objective_addends=n)
    return utility


def _split(library, indices, moments, mean, incidence, state, view, min_roots, counts):
    prototypes, features = library['prototypes'], view['features']
    total_weight, total_sums = moments
    root_totals = Counter(prototypes[index]['root_id'] for index in indices)
    source_totals = Counter(prototypes[index]['source_id'] for index in indices)
    n = len(view['root_ids'])
    best = None
    for feature in range(162):
        ordered = sorted(indices, key=lambda index: (features[index, feature], index))
        counts.update(tree_feature_sorts=1, tree_feature_sort_items=len(indices))
        if features[ordered[0], feature] == features[ordered[-1], feature]:
            counts['tree_constant_features'] += 1
            continue
        roots_left, sources_left = set(), set()
        roots_right, sources_right = root_totals.copy(), source_totals.copy()
        left_weight, left_sums = 0., [0., 0., 0.]
        left_incidence = np.zeros_like(incidence)
        counts.update(tree_prefix_incidence_preparations=1, tree_prefix_incidence_zero_cells=incidence.size)
        for offset, index in enumerate(ordered[:-1]):
            row, w = prototypes[index], prototypes[index]['root_mass']
            left_weight += w
            for component, value in enumerate(row['tail_difference']):
                left_sums[component] += w*value
            root_index, scale = view['prototype_roots'][index], view['incidence_scale'][index]
            left_incidence[root_index, view['first_actions'][index]] += scale
            left_incidence[root_index, view['second_actions'][index]] -= scale
            roots_left.add(row['root_id']); sources_left.add(row['source_id'])
            roots_right[row['root_id']] -= 1; sources_right[row['source_id']] -= 1
            if roots_right[row['root_id']] == 0:
                del roots_right[row['root_id']]
            if sources_right[row['source_id']] == 0:
                del sources_right[row['source_id']]
            counts.update(tree_prefix_sample_updates=1, tree_prefix_WY_products=3,
                          tree_prefix_component_additions=3, tree_prefix_incidence_additions=2,
                          tree_prefix_support_updates=4)
            threshold = float(features[index, feature])
            if threshold == features[ordered[offset+1], feature]:
                continue
            counts['tree_observed_thresholds'] += 1
            if min(len(roots_left), len(roots_right)) < min_roots or min(len(sources_left), len(sources_right)) < 2:
                counts['tree_unsupported_thresholds'] += 1
                continue
            right_weight = total_weight-left_weight
            right_sums = [total_sums[c]-left_sums[c] for c in range(3)]
            left_mean = np.asarray([value/left_weight for value in left_sums])
            right_mean = np.asarray([value/right_weight for value in right_sums])
            right_incidence = incidence-left_incidence
            candidate_theta = (state['theta']+left_incidence[:, :, None]*(left_mean-mean)
                               +right_incidence[:, :, None]*(right_mean-mean))
            counts.update(tree_supported_split_candidates=1, tree_candidate_mean_divisions=6,
                          tree_candidate_incidence_subtractions=4*n, tree_candidate_mean_subtractions=6,
                          tree_candidate_theta_products=24*n, tree_candidate_theta_additions=24*n,
                          tree_candidate_root_decisions=n)
            after = _training_utility(candidate_theta, view, counts)
            gain = after-state['utility']
            counts['tree_gain_comparisons'] += 1
            if gain > EPSILON and (best is None or gain > best['improvement']+EPSILON):
                best = dict(feature=feature, threshold=threshold, improvement=gain,
                    training_utility_before=state['utility'], training_utility_after=after,
                    left_moments=(left_weight, list(left_sums)), right_moments=(right_weight, right_sums),
                    left_mean=left_mean, right_mean=right_mean, left_incidence=left_incidence.copy(),
                    right_incidence=right_incidence, theta=candidate_theta)
                counts.update(tree_best_candidate_updates=1, tree_best_candidate_array_copies=4*n)
    return best


def build_tree(library, view, max_depth, min_leaf_roots, costs=None):
    """Greedy preorder split gains evaluated in the current whole-tree context."""
    counts = costs if costs is not None else Counter()
    counts['tree_fit_attempts'] += 1
    prototypes = library['prototypes']
    indices = list(range(len(prototypes)))
    moments = _moments(prototypes, indices, counts)
    mean = np.asarray([value/moments[0] for value in moments[1]])
    incidence = _incidence(view, indices, counts)
    state = dict(theta=np.zeros((len(view['root_ids']), 4, 3)),
                 predictions=np.tile(mean, (len(prototypes), 1)))
    counts.update(training_initial_prediction_component_copies=3*len(prototypes),
                  training_initial_theta_zero_cells=state['theta'].size)
    state['utility'] = _training_utility(state['theta'], view, counts)

    def node(indices, depth, node_id, moments, mean):
        value = dict(node_id=node_id, depth=depth, prototype_count=len(indices),
            root_count=len({prototypes[index]['root_id'] for index in indices}),
            source_count=len({prototypes[index]['source_id'] for index in indices}),
            weight_sum=moments[0], mean=mean.tolist(), kind='leaf', prototype_indices=list(indices))
        counts.update(tree_nodes_built=1, tree_node_mean_components=3)
        return value

    def grow(current, indices, moments, mean, incidence):
        split = None
        if current['depth'] < max_depth and current['root_count'] >= min_leaf_roots and current['source_count'] >= 2:
            split = _split(library, indices, moments, mean, incidence, state, view, min_leaf_roots, counts)
        if split is None:
            counts['tree_leaves_built'] += 1
            return
        feature, threshold = split['feature'], split['threshold']
        left = [index for index in indices if view['features'][index, feature] <= threshold]
        right = [index for index in indices if view['features'][index, feature] > threshold]
        counts.update(tree_split_partition_tests=2*len(indices), tree_splits_built=1,
                      training_accepted_prediction_component_assignments=3*len(indices),
                      training_accepted_theta_bindings=1)
        state['predictions'][left] = split['left_mean']
        state['predictions'][right] = split['right_mean']
        state['theta'], state['utility'] = split['theta'], split['training_utility_after']
        left_node = node(left, current['depth']+1, 2*current['node_id']+1, split['left_moments'], split['left_mean'])
        right_node = node(right, current['depth']+1, 2*current['node_id']+2, split['right_moments'], split['right_mean'])
        del current['prototype_indices']
        current.update(kind='split', feature=feature, threshold=threshold, improvement=split['improvement'],
                       training_utility_before=split['training_utility_before'],
                       training_utility_after=split['training_utility_after'], left=left_node, right=right_node)
        grow(left_node, left, split['left_moments'], split['left_mean'], split['left_incidence'])
        grow(right_node, right, split['right_moments'], split['right_mean'], split['right_incidence'])

    tree = node(indices, 0, 0, moments, mean)
    grow(tree, indices, moments, mean, incidence)
    counts.update(tree_predictors_fitted=1, new_predictors_fitted=1)
    return tree


def _tree_model(library, view, max_depth, min_roots, counts):
    model = programs._base_model('UTILITY', library)
    model['schema'] = SCHEMA+'.model'
    counts['UTILITY_tree_fit_attempts'] += 1
    model.update(max_depth=max_depth, min_leaf_roots=min_roots,
                 tree=build_tree(library, view, max_depth, min_roots, counts))
    counts['UTILITY_tree_predictors_fitted'] += 1
    return model


def _select(rows, libraries, views, heldouts, queries, folds, counts):
    candidates, selected, best = [], (MAX_DEPTHS[0], MIN_LEAF_ROOTS[0]), None
    for depth in MAX_DEPTHS:
        for support in MIN_LEAF_ROOTS:
            results, groups = [], []
            for fold in range(2):
                library_id = f'FOLD_{fold}'
                library = libraries[library_id]
                before = Counter(counts)
                model = _tree_model(library, views[library_id], depth, support, counts)
                records, choices = programs._heldout(model, library, heldouts[fold], queries[fold], counts)
                groups.extend(records)
                results.append(dict(fold=fold, library_id=library_id, tree=model['tree'],
                                    group_records=records, choices=choices, work=dict(Counter(counts)-before)))
            groups.sort(key=lambda row: row['source_id'])
            utility = sum(row['utility'] for row in groups)/SOURCE_GROUPS
            candidates.append(dict(max_depth=depth, min_leaf_roots=support, utility=utility,
                                   group_records=groups, fold_results=results))
            counts.update(selection_group_mean_reads=SOURCE_GROUPS, selection_score_comparisons=1)
            if best is None or utility > best+EPSILON:
                selected, best = (depth, support), utility
    selection = dict(schema=SCHEMA+'.selection', mode='UTILITY', source_folds=folds,
        folds=[dict(fold=fold, library_id=f'FOLD_{fold}', train_sources=libraries[f'FOLD_{fold}']['source_ids'],
                    heldout_sources=folds[fold]) for fold in range(2)], candidates=candidates,
        selected_depth=selected[0], selected_min_leaf_roots=selected[1], selected_utility=best)
    return selection, selected


def fit_models(examples, libraries, life=0):
    """Fit 16 SOURCE-fold trees and one selected full tree using supplied libraries."""
    costs = Counter(shared_library_preparations=0, new_linear_solves=0, new_eigen_decompositions=0,
                    new_svd_decompositions=0, new_environment_samples=0, new_source_games=0,
                    new_native_weight_updates=0, neighbor_predictor_configurations=0)
    rows = sorted([row for row in examples if row['life'] == life], key=lambda row: row['root_id'])
    sources = sorted({row['source_id'] for row in rows})
    if len(rows) != SOURCE_ROOTS or len(sources) != SOURCE_GROUPS:
        raise ValueError('143 fixed SOURCE roots and 36 groups required')
    folds, heldouts, queries = [sources[::2], sources[1::2]], [], []
    try:
        costs['source_fold_assignments'] += len(sources)
        views = {library_id: prepare_training_view(rows, libraries[library_id], costs)
                 for library_id in ('FOLD_0', 'FOLD_1', 'FULL')}
        for heldout_sources in folds:
            heldout = [row for row in rows if row['source_id'] in heldout_sources]
            cached = {row['root_id']: programs._query(programs._observable(row), costs) for row in heldout}
            heldouts.append(heldout); queries.append(cached)
        selection, configuration = _select(rows, libraries, views, heldouts, queries, folds, costs)
        model = _tree_model(libraries['FULL'], views['FULL'], *configuration, costs)
    except Exception as error:
        raise PairExecutionError('utility_source_selection', costs, error) from error
    return dict(models={'UTILITY': model}, selection={'UTILITY': selection}, costs=dict(costs))
