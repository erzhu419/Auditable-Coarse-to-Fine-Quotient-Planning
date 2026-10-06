"""SOURCE-learned regions and raw neighbors for complete pair consequences.

Three libraries are shared by TREE32/RAW32 and persisted separately. Every
unordered query pair predicts both directions, antisymmetrizes the complete
R/F/S vector, and uses the same complete-graph projection and reward decoder.
"""
from collections import Counter
from itertools import combinations

from . import controlled_predictive_consequence_partition_v172 as estimation
from . import controlled_predictive_exact_h3_v177 as exact

SCHEMA = 'acfqp.pair_regions.v195'
ACTIONS, EPSILON = estimation.ACTIONS, estimation.EPSILON
MODES = ('TREE32', 'RAW32')
MAX_DEPTHS, MIN_LEAF_ROOTS, K_VALUES = (1, 2, 4, 6), (4, 8), (1, 8, 32)
SOURCE_ROOTS, SOURCE_GROUPS = 143, 36
FEATURE_NAMES = tuple(f'{side}:cell_{index}' for side in ('first', 'second') for index in range(16))


class PairExecutionError(RuntimeError):
    def __init__(self, operation, costs, cause):
        self.record = dict(operation=operation, costs=dict(costs), error=str(cause))
        super().__init__(str(cause))


def cache_roots(roots):
    counts = Counter()
    for root in roots:
        if 'raw_afterstates' in root:
            counts.update(raw_afterstate_cache_hits=1, raw_afterstate_cached_cell_reads=16*len(root['legal_actions']))
            continue
        raw = {}
        for action in ACTIONS:
            if action not in root['legal_actions']:
                continue
            values, seen = [0]*16, set()
            for token in root['layout_features'][action]['tokens']:
                counts['raw_afterstate_token_kind_reads'] += 1
                if token[0] == 'cell':
                    _, position, rank = token
                    values[position] = rank
                    seen.add(position)
                    counts.update(raw_afterstate_cell_tokens=1, raw_afterstate_position_reads=1, raw_afterstate_rank_reads=1)
            if seen != set(range(16)):
                raise ValueError('sixteen positioned cell ranks required')
            raw[action] = values
            counts['raw_afterstates_extracted'] += 1
        root['raw_afterstates'] = raw
        counts['raw_afterstate_roots_cached'] += 1
    return dict(counts)


def _legal(root):
    return [action for action in ACTIONS if action in root['legal_actions']]


def prepare_library(examples, library_id, life=0, costs=None):
    counts = costs if costs is not None else Counter()
    before = Counter(counts)
    counts['shared_library_attempts'] += 1
    roots = sorted([root for root in examples if root['life'] == life], key=lambda row: row['root_id'])
    source_counts = dict(Counter(root['source_id'] for root in roots))
    prototypes = []
    for root in roots:
        legal = _legal(root)
        if not legal or len(legal) != len(root['legal_actions']) or set(root['action_components']) != set(legal):
            raise ValueError('complete vectors for distinct SOURCE legal actions required')
        vectors = {action: list(map(float, root['action_components'][action])) for action in legal}
        if any(len(vector) != 3 for vector in vectors.values()):
            raise ValueError('complete R/F/S SOURCE vectors required')
        raw = {action: list(root['raw_afterstates'][action]) for action in legal}
        if any(len(vector) != 16 for vector in raw.values()):
            raise ValueError('sixteen-cell raw afterstate cache required')
        tails = {action: [vectors[action][0]-root['immediate_rewards'][action], *vectors[action][1:]] for action in legal}
        ordered_count = len(legal)*(len(legal)-1)
        counts.update(library_roots_read=1, library_raw_cell_reads=16*len(legal),
            library_label_component_reads=3*len(legal), library_reward_reads=len(legal), library_tail_reward_subtractions=len(legal))
        for first in legal:
            for second in legal:
                if first == second:
                    continue
                prototypes.append(dict(root_id=root['root_id'], source_id=root['source_id'], actions=[first, second],
                    features32=raw[first]+raw[second],
                    tail_difference=[tails[first][component]-tails[second][component] for component in range(3)],
                    root_mass=1./(source_counts[root['source_id']]*ordered_count)))
                counts.update(library_prototypes_built=1, library_pair_feature_copies=32, library_tail_component_subtractions=3)
    if not prototypes:
        raise ValueError('SOURCE library requires an observed action pair')
    counts['shared_library_preparations'] += 1
    return dict(schema=SCHEMA+'.library', library_id=library_id, life=life, feature_names=list(FEATURE_NAMES),
        root_ids=[root['root_id'] for root in roots], source_ids=sorted(source_counts),
        source_root_counts=source_counts, prototypes=prototypes, work=dict(Counter(counts)-before))


def _moments(prototypes, indices, counts):
    weight, sums, squares = 0., [0., 0., 0.], [0., 0., 0.]
    for index in indices:
        row = prototypes[index]
        w = row['root_mass']
        weight += w
        for component, y in enumerate(row['tail_difference']):
            sums[component] += w*y
            squares[component] += w*y*y
    counts.update(tree_moment_sample_reads=len(indices), tree_moment_weight_additions=len(indices),
        tree_moment_WY_products=3*len(indices), tree_moment_WY2_products=6*len(indices),
        tree_moment_component_additions=6*len(indices))
    return weight, sums, squares


def _sse(weight, sums, squares):
    return sum(squares[component]-sums[component]*sums[component]/weight for component in range(3))


def _split(prototypes, indices, moments, parent_sse, min_roots, counts):
    total_weight, total_sums, total_squares = moments
    root_totals = Counter(prototypes[index]['root_id'] for index in indices)
    source_totals = Counter(prototypes[index]['source_id'] for index in indices)
    best = None
    for feature in range(32):
        ordered = sorted(indices, key=lambda index: (prototypes[index]['features32'][feature], index))
        counts.update(tree_feature_sorts=1, tree_feature_sort_items=len(indices))
        if prototypes[ordered[0]]['features32'][feature] == prototypes[ordered[-1]]['features32'][feature]:
            counts['tree_constant_features'] += 1
            continue
        roots_left, sources_left = set(), set()
        roots_right, sources_right = root_totals.copy(), source_totals.copy()
        left_weight, left_sums, left_squares = 0., [0., 0., 0.], [0., 0., 0.]
        for offset, index in enumerate(ordered[:-1]):
            row, w = prototypes[index], prototypes[index]['root_mass']
            left_weight += w
            for component, y in enumerate(row['tail_difference']):
                left_sums[component] += w*y
                left_squares[component] += w*y*y
            roots_left.add(row['root_id']); sources_left.add(row['source_id'])
            roots_right[row['root_id']] -= 1; sources_right[row['source_id']] -= 1
            if roots_right[row['root_id']] == 0:
                del roots_right[row['root_id']]
            if sources_right[row['source_id']] == 0:
                del sources_right[row['source_id']]
            counts.update(tree_prefix_sample_updates=1, tree_prefix_WY_products=3,
                tree_prefix_WY2_products=6, tree_prefix_component_additions=6,
                tree_prefix_support_updates=4)
            threshold = row['features32'][feature]
            if threshold == prototypes[ordered[offset+1]]['features32'][feature]:
                continue
            counts['tree_observed_thresholds'] += 1
            if min(len(roots_left), len(roots_right)) < min_roots or min(len(sources_left), len(sources_right)) < 2:
                counts['tree_unsupported_thresholds'] += 1
                continue
            right_weight = total_weight-left_weight
            right_sums = [total_sums[c]-left_sums[c] for c in range(3)]
            right_squares = [total_squares[c]-left_squares[c] for c in range(3)]
            left_sse = _sse(left_weight, left_sums, left_squares)
            right_sse = _sse(right_weight, right_sums, right_squares)
            gain = parent_sse-left_sse-right_sse
            counts.update(tree_supported_split_candidates=1, tree_candidate_component_sse_terms=6,
                          tree_gain_comparisons=1)
            if gain > EPSILON and (best is None or gain > best['improvement']+EPSILON):
                best = dict(feature=feature, threshold=threshold, improvement=gain)
    return best


def build_tree(library, max_depth, min_leaf_roots, costs=None):
    counts = costs if costs is not None else Counter()
    counts['tree_fit_attempts'] += 1
    prototypes = library['prototypes']
    def grow(indices, depth, node_id):
        moments = _moments(prototypes, indices, counts)
        weight, sums, squares = moments
        root_count = len({prototypes[index]['root_id'] for index in indices})
        source_count = len({prototypes[index]['source_id'] for index in indices})
        weighted_sse = _sse(weight, sums, squares)
        node = dict(node_id=node_id, depth=depth, prototype_count=len(indices), root_count=root_count,
            source_count=source_count, weight_sum=weight, mean=[value/weight for value in sums], weighted_sse=weighted_sse)
        counts.update(tree_nodes_built=1, tree_node_mean_divisions=3, tree_node_component_sse_terms=3)
        split = None
        if depth < max_depth and root_count >= min_leaf_roots and source_count >= 2:
            split = _split(prototypes, indices, moments, weighted_sse, min_leaf_roots, counts)
        if split is None:
            node.update(kind='leaf', prototype_indices=list(indices))
            counts['tree_leaves_built'] += 1
        else:
            feature, threshold = split['feature'], split['threshold']
            left = [index for index in indices if prototypes[index]['features32'][feature] <= threshold]
            right = [index for index in indices if prototypes[index]['features32'][feature] > threshold]
            node.update(kind='split', **split, left=grow(left, depth+1, 2*node_id+1),
                        right=grow(right, depth+1, 2*node_id+2))
            counts.update(tree_splits_built=1, tree_split_partition_tests=2*len(indices))
        return node
    tree = grow(list(range(len(prototypes))), 0, 0)
    counts.update(tree_predictors_fitted=1, new_predictors_fitted=1)
    return tree


def _base_model(mode, library):
    return dict(schema=SCHEMA+'.model', mode=mode, library_id=library['library_id'], life=library['life'],
        query='risk1', native_teacher_query=exact.QUERY, horizon=exact.HORIZON,
        label_kind='exact_enumerated_vector', feature_names=list(FEATURE_NAMES),
        constants=dict(columns=32, epsilon=EPSILON, goal_rank=11,
                       projection='COMPLETE_GRAPH_ZERO_MEAN', antisymmetrization='FORWARD_MINUS_REVERSE_OVER_TWO'))


def _tree_model(library, max_depth, min_roots, counts):
    model = _base_model('TREE32', library)
    model.update(max_depth=max_depth, min_leaf_roots=min_roots,
                 tree=build_tree(library, max_depth, min_roots, counts))
    return model


def _raw_model(library, k, counts):
    counts.update(raw_predictor_configurations=1, new_predictors_fitted=1)
    model = _base_model('RAW32', library)
    model['k'] = k
    return model


def _query(root, counts):
    legal = _legal(root)
    raw = {action: list(root['raw_afterstates'][action]) for action in legal}
    pairs = {estimation._pair_key(first, second): dict(actions=[first, second],
        forward=raw[first]+raw[second], reverse=raw[second]+raw[first]) for first, second in combinations(legal, 2)}
    counts.update(query_input_roots=1, query_raw_cell_reads=16*len(legal),
                  query_pair_inputs=2*len(pairs), query_pair_input_copies=64*len(pairs))
    return dict(legal_actions=legal, pairs=pairs)


def _raw_geometry(query, library, counts):
    for pair in query['pairs'].values():
        for direction in ('forward', 'reverse'):
            values = pair[direction]
            ordered = sorted((sum((values[c]-row['features32'][c])**2 for c in range(32)), index)
                             for index, row in enumerate(library['prototypes']))
            pair[direction+'_neighbors'] = ordered
            n = len(ordered)
            counts.update(raw_distance_pairs=n, raw_distance_component_subtractions=32*n,
                raw_distance_component_squares=32*n, raw_distance_component_addends=32*n,
                raw_neighbor_sorts=1, raw_neighbor_sort_items=n)


def _tree_direction(model, values, counts):
    node = model['tree']
    while node['kind'] == 'split':
        counts['tree_prediction_split_tests'] += 1
        node = node['left'] if values[node['feature']] <= node['threshold'] else node['right']
    counts.update(tree_direction_predictions=1, tree_prediction_component_reads=3)
    return dict(components=list(node['mean']), leaf_id=node['node_id'])


def _raw_direction(model, ordered, library, counts):
    nearest = ordered[:model['k']]
    total = sum(library['prototypes'][index]['root_mass'] for distance, index in nearest)
    neighbors = [dict(prototype_index=index, distance=distance, weight=library['prototypes'][index]['root_mass']/total)
                 for distance, index in nearest]
    vector = [sum(row['weight']*library['prototypes'][row['prototype_index']]['tail_difference'][component]
                  for row in neighbors) for component in range(3)]
    counts.update(raw_direction_predictions=1, raw_neighbor_mass_addends=len(neighbors),
                  raw_neighbor_normalizations=len(neighbors), raw_tail_component_products=3*len(neighbors))
    return dict(components=vector, neighbors=neighbors)


def _decision(model, root, library, query, counts):
    legal, n = query['legal_actions'], len(query['legal_actions'])
    theta, estimated = {action: [0., 0., 0.] for action in legal}, {}
    for key, pair in query['pairs'].items():
        if model['mode'] == 'TREE32':
            forward = _tree_direction(model, pair['forward'], counts)
            reverse = _tree_direction(model, pair['reverse'], counts)
        else:
            forward = _raw_direction(model, pair['forward_neighbors'], library, counts)
            reverse = _raw_direction(model, pair['reverse_neighbors'], library, counts)
        delta = [(forward['components'][c]-reverse['components'][c])/2. for c in range(3)]
        first, second = pair['actions']
        for c in range(3):
            theta[first][c] += delta[c]/n
            theta[second][c] -= delta[c]/n
        estimated[key] = dict(actions=list(pair['actions']), forward=forward, reverse=reverse, estimated_tail_delta=delta)
        counts.update(pair_antisymmetric_component_subtractions=3, pair_antisymmetric_component_divisions=3,
                      pair_projection_divisions=6, pair_projection_accumulations=6)
    predicted = {action: [root['immediate_rewards'][action]+theta[action][0], *theta[action][1:]] for action in legal}
    predicted_pairs, residuals = {}, []
    for key, pair in estimated.items():
        first, second = pair['actions']
        projected = [theta[first][c]-theta[second][c] for c in range(3)]
        residual = [pair['estimated_tail_delta'][c]-projected[c] for c in range(3)]
        pair.update(projected_tail_delta=projected, projection_residual=residual)
        predicted_pairs[key] = [predicted[first][c]-predicted[second][c] for c in range(3)]
        residuals.extend(residual)
        counts.update(pair_projected_component_subtractions=3, pair_projection_residual_subtractions=3,
                      pair_predicted_component_subtractions=3)
    selected, best = legal[0], None
    for action in legal:
        vector = predicted[action]
        value = vector[0]-vector[1]+vector[2]
        if best is None or value > best+EPSILON:
            selected, best = action, value
    counts.update(pair_decisions=1, pair_reward_additions=n, pair_utility_evaluations=n,
                  pair_projection_residual_squares=len(residuals))
    return dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=False, leaf=0,
        reason='single_legal_action' if n == 1 else 'pair_region_projection', predicted_components=predicted,
        predicted_pairs=predicted_pairs, estimated_pairs=estimated, tail_offsets=theta,
        projection_residual_sse=sum(value*value for value in residuals), projection_residual_max=max(map(abs, residuals), default=0.))


def choose_action(model, root, library, counts=None):
    if model['library_id'] != library['library_id'] or model['life'] != root['life']:
        raise ValueError('model, library and root must share the frozen teacher and library')
    work = Counter()
    query = _query(root, work)
    if model['mode'] == 'RAW32':
        _raw_geometry(query, library, work)
    result = _decision(model, root, library, query, work)
    result.update(work=dict(work), feature_work={})
    if counts is not None:
        counts.update(work)
    return result


def _observable(root):
    return {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
        'immediate_rewards', 'fallback_action', 'action_map', 'raw_afterstates')}


def _heldout(model, library, roots, queries, counts):
    groups, choices = {}, []
    for root in roots:
        decision = _decision(model, _observable(root), library, queries[root['root_id']], counts)
        action = decision['canonical_action']
        vector = list(map(float, root['action_components'][action]))
        utility = vector[0]-vector[1]+vector[2]
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], canonical_action=action,
                            components=vector, utility=utility))
        counts.update(heldout_action_vector_reads=1, heldout_component_reads=3, heldout_utility_evaluations=1)
    records = []
    for source in sorted(groups):
        mean = [sum(vector[c] for vector in groups[source])/len(groups[source]) for c in range(3)]
        records.append(dict(source_id=source, roots=len(groups[source]), components=mean, utility=mean[0]-mean[1]+mean[2]))
        counts.update(heldout_group_component_means=3, heldout_group_utility_evaluations=1)
    return records, choices


def _select(mode, configurations, libraries, heldouts, queries, folds, counts):
    candidates, selected, best = [], configurations[0], None
    for configuration in configurations:
        results, groups = [], []
        for fold in range(2):
            library = libraries[f'FOLD_{fold}']
            before = Counter(counts)
            model = (_tree_model(library, *configuration, counts) if mode == 'TREE32'
                     else _raw_model(library, configuration[0], counts))
            records, choices = _heldout(model, library, heldouts[fold], queries[fold], counts)
            groups.extend(records)
            result = dict(fold=fold, library_id=library['library_id'], group_records=records, choices=choices,
                          work=dict(Counter(counts)-before))
            if mode == 'TREE32':
                result['tree'] = model['tree']
            results.append(result)
        groups.sort(key=lambda row: row['source_id'])
        utility = sum(row['utility'] for row in groups)/SOURCE_GROUPS
        parameters = (dict(max_depth=configuration[0], min_leaf_roots=configuration[1]) if mode == 'TREE32'
                      else dict(k=configuration[0]))
        candidates.append(dict(**parameters, utility=utility, group_records=groups, fold_results=results))
        counts.update(selection_group_mean_reads=SOURCE_GROUPS, selection_score_comparisons=1)
        if best is None or utility > best+EPSILON:
            selected, best = configuration, utility
    selection = dict(schema=SCHEMA+'.selection', mode=mode, source_folds=folds,
        folds=[dict(fold=fold, library_id=f'FOLD_{fold}', train_sources=libraries[f'FOLD_{fold}']['source_ids'],
                    heldout_sources=folds[fold]) for fold in range(2)], candidates=candidates, selected_utility=best)
    selection.update(dict(selected_depth=selected[0], selected_min_leaf_roots=selected[1]) if mode == 'TREE32'
                     else dict(selected_k=selected[0]))
    return selection, selected


def fit_models(examples, life=0):
    """Learn SOURCE regions and select both arms by actual equal-group utility."""
    costs = Counter(new_linear_solves=0, new_eigen_decompositions=0, new_svd_decompositions=0,
                    new_environment_samples=0, new_source_games=0, new_native_weight_updates=0)
    rows = sorted([row for row in examples if row['life'] == life], key=lambda row: row['root_id'])
    sources = sorted({row['source_id'] for row in rows})
    if len(rows) != SOURCE_ROOTS or len(sources) != SOURCE_GROUPS:
        raise ValueError('143 fixed SOURCE roots and 36 groups required')
    folds = [sources[::2], sources[1::2]]
    libraries, heldouts, queries = {}, [], []
    try:
        costs['source_fold_assignments'] += len(sources)
        for fold, heldout_sources in enumerate(folds):
            library_id = f'FOLD_{fold}'
            library = prepare_library([row for row in rows if row['source_id'] not in heldout_sources], library_id, life, costs)
            libraries[library_id] = library
            heldout = [row for row in rows if row['source_id'] in heldout_sources]
            cached = {}
            for root in heldout:
                query = _query(_observable(root), costs)
                _raw_geometry(query, library, costs)
                cached[root['root_id']] = query
            heldouts.append(heldout); queries.append(cached)
        tree_selection, tree_configuration = _select('TREE32',
            [(depth, support) for depth in MAX_DEPTHS for support in MIN_LEAF_ROOTS],
            libraries, heldouts, queries, folds, costs)
        raw_selection, raw_configuration = _select('RAW32', [(k,) for k in K_VALUES],
            libraries, heldouts, queries, folds, costs)
        libraries['FULL'] = prepare_library(rows, 'FULL', life, costs)
        models = dict(TREE32=_tree_model(libraries['FULL'], *tree_configuration, costs),
                      RAW32=_raw_model(libraries['FULL'], raw_configuration[0], costs))
    except Exception as error:
        raise PairExecutionError('joint_source_selection', costs, error) from error
    return dict(models=models, selection=dict(TREE32=tree_selection, RAW32=raw_selection), libraries=libraries, costs=dict(costs))
