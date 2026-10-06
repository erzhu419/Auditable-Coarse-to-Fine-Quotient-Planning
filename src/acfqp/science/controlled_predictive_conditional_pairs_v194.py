"""SOURCE-selected nonnegative complete-vector action-pair transfer.

PAIR98 and CONDITIONAL share one prototype rule. Each design retains ordered
same-root tail differences once; SOURCE fold geometry/sorting is reused by all
nine configurations. Decisions retain original pair estimates, complete-graph
projections, residuals and nonnegative neighbor weights.
"""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from math import exp

from . import controlled_predictive_merge_relations_v190 as relation
from . import controlled_predictive_consequence_partition_v172 as estimation
from . import controlled_predictive_exact_h3_v177 as exact

SCHEMA = 'acfqp.conditional_pairs.v194'
ACTIONS, EPSILON = estimation.ACTIONS, estimation.EPSILON
MODES = ('PAIR98', 'CONDITIONAL')
K_VALUES, TEMPERATURES = (1, 8, 32), (.01, .1, 1.)
SOURCE_ROOTS, SOURCE_GROUPS = 143, 36
RANK_BINS = ('le7', 'rank8', 'rank9', 'rank10', 'ge11')
FEATURE_NAMES = (*relation.FEATURE_NAMES[:6],
    *(f'{rank_bin}:{kind}:{name}' for rank_bin in RANK_BINS
      for kind, names in (('node', relation.NODE_MOMENT_NAMES), ('pair', relation.PAIR_MOMENT_NAMES)) for name in names),
    *relation.VACANCY_MOMENT_NAMES)


class PairExecutionError(RuntimeError):
    def __init__(self, operation, costs, cause):
        self.record = dict(operation=operation, costs=dict(costs), error=str(cause))
        super().__init__(str(cause))


def _rank_bin(rank):
    return 0 if rank <= 7 else rank-7 if rank <= 10 else 4


def _project(contract, counts):
    nodes, pairs = [[0.]*9 for _ in RANK_BINS], [[0.]*33 for _ in RANK_BINS]
    for node in contract['nodes']:
        index = _rank_bin(node['rank'])
        for column, value in enumerate(node['moments']):
            nodes[index][column] += value
        counts.update(conditional_rank_bin_assignments=1, conditional_node_moment_accumulations=9)
    for pair in contract['equal_pairs']:
        index = _rank_bin(pair['rank'])
        for column, value in enumerate(pair['moments']):
            pairs[index][column] += value
        counts.update(conditional_rank_bin_assignments=1, conditional_pair_moment_accumulations=33)
    values = list(map(float, contract['aggregate']))
    for node_values, pair_values in zip(nodes, pairs, strict=True):
        values.extend(value/relation.NODE_NORMALIZER for value in node_values)
        values.extend(value/relation.PAIR_NORMALIZER for value in pair_values)
    values.extend(contract['vacancy_moments'])
    counts.update(conditional_node_normalizations=45, conditional_pair_normalizations=165,
                  conditional_vacancy_values_copied=8, conditional_feature_vectors_computed=1)
    return values


def action_features_from_root(root, counts=None):
    work = Counter()
    if 'conditional_features' in root:
        values = {action: list(root['conditional_features'][action]) for action in ACTIONS if action in root['legal_actions']}
        work.update(conditional_feature_cache_hits=1, conditional_cached_feature_reads=224*len(values))
    else:
        values = {action: _project(relation.build_contract(root['layout_features'][action], work), work)
                  for action in ACTIONS if action in root['legal_actions']}
        work['conditional_feature_maps_derived'] += 1
    if counts is not None:
        counts.update(work)
    return values


def cache_roots(roots):
    counts = Counter()
    for root in roots:
        root['conditional_features'] = action_features_from_root(root, counts)
    return dict(counts)


def _features(root, mode, counts):
    key, columns = ('relation_features', 98) if mode == 'PAIR98' else ('conditional_features', 224)
    values = {action: list(map(float, root[key][action])) for action in ACTIONS if action in root['legal_actions']}
    if any(len(vector) != columns for vector in values.values()):
        raise ValueError('the selected fixed feature cache is required')
    counts.update(pair_feature_cache_reads=1, pair_feature_value_reads=columns*len(values))
    return values


def _distance(first, second):
    return sum((a-b)**2 for a, b in zip(first, second, strict=True))


def _median(values):
    ordered, n = sorted(values), len(values)
    return ordered[n//2] if n % 2 else (ordered[n//2-1]+ordered[n//2])/2.


def prepare_design(examples, mode, life=0, costs=None):
    if mode not in MODES:
        raise ValueError('fixed PAIR98 or CONDITIONAL mode required')
    counts = costs if costs is not None else Counter()
    before = Counter(counts)
    counts['pair_design_attempts'] += 1
    roots, seen = [], set()
    for raw in examples:
        counts['pair_examples_examined'] += 1
        if raw['life'] != life:
            counts['pair_other_life_examples_excluded'] += 1
            continue
        if raw['root_id'] in seen:
            raise ValueError('distinct SOURCE roots required')
        seen.add(raw['root_id'])
        legal = [action for action in ACTIONS if action in raw['legal_actions']]
        if not legal or len(legal) != len(raw['legal_actions']) or set(raw['action_components']) != set(legal):
            raise ValueError('complete vector for every distinct legal SOURCE action required')
        root = deepcopy(raw)
        root['legal_actions'] = legal
        root['immediate_rewards'] = {action: float(raw['immediate_rewards'][action]) for action in legal}
        root['action_components'] = {action: list(map(float, raw['action_components'][action])) for action in legal}
        if any(len(vector) != 3 for vector in root['action_components'].values()):
            raise ValueError('complete R/F/S SOURCE vectors required')
        roots.append(root)
        counts.update(pair_examples_fitted=1, pair_legal_action_reads=len(legal),
            pair_immediate_reward_reads=len(legal), pair_label_component_reads=3*len(legal),
            pair_tail_reward_subtractions=len(legal))
    roots.sort(key=lambda row: row['root_id'])
    centers, prototypes = [], []
    for root in roots:
        features, indexed = _features(root, mode, counts), {}
        for action in root['legal_actions']:
            indexed[action] = len(centers)
            centers.append(dict(root_id=root['root_id'], source_id=root['source_id'], action=action, features=features[action]))
        legal = root['legal_actions']
        ordered_count = len(legal)*(len(legal)-1)
        tails = {action: [root['action_components'][action][0]-root['immediate_rewards'][action],
                          *root['action_components'][action][1:]] for action in legal}
        for first in legal:
            for second in legal:
                if first == second:
                    continue
                prototypes.append(dict(root_id=root['root_id'], source_id=root['source_id'],
                    actions=[first, second], center_indices=[indexed[first], indexed[second]], root_mass=1./ordered_count,
                    tail_difference=[tails[first][component]-tails[second][component] for component in range(3)]))
                counts.update(pair_prototypes_built=1, pair_prototype_component_subtractions=3)
    columns = 98 if mode == 'PAIR98' else 224
    distance_pairs = len(centers)*(len(centers)-1)//2
    counts.update(pair_centers_built=len(centers), pair_train_center_distance_pairs=distance_pairs,
        pair_train_distance_component_subtractions=columns*distance_pairs,
        pair_train_distance_component_squares=columns*distance_pairs,
        pair_train_distance_component_addends=columns*distance_pairs,
        pair_train_nonzero_distance_tests=distance_pairs)
    positive = []
    for first, second in combinations(range(len(centers)), 2):
        value = _distance(centers[first]['features'], centers[second]['features'])
        if value > 0.:
            positive.append(value)
    if not prototypes or not positive:
        raise ValueError('SOURCE library requires action pairs and positive center distance')
    counts.update(pair_median_attempts=1, pair_median_distance_values=len(positive))
    median = _median(positive)
    counts.update(pair_median_computations=1, pair_design_preparations=1)
    source_counts = dict(Counter(root['source_id'] for root in roots))
    return dict(schema=SCHEMA+'.design', mode=mode, life=life,
        feature_names=list(relation.FEATURE_NAMES if mode == 'PAIR98' else FEATURE_NAMES),
        columns=columns, centers=centers, prototypes=prototypes, median_squared_distance=median,
        root_ids=[root['root_id'] for root in roots], source_ids=sorted(source_counts),
        source_root_counts=source_counts, design_counts=dict(Counter(counts)-before))


def _model(design, k, temperature, folds=None):
    return dict(schema=SCHEMA+'.model', mode=design['mode'], life=design['life'], query='risk1',
        native_teacher_query=exact.QUERY, horizon=exact.HORIZON, label_kind='exact_enumerated_vector',
        k=k, temperature=temperature, median_squared_distance=design['median_squared_distance'],
        constants=dict(columns=design['columns'], epsilon=EPSILON, goal_rank=11, k=k, temperature=temperature,
            projection='COMPLETE_GRAPH_ZERO_MEAN', weights='NONNEGATIVE_ROOT_MASS_LOCAL'),
        **{key: design[key] for key in ('centers', 'prototypes', 'feature_names', 'root_ids', 'source_ids',
            'source_root_counts', 'design_counts')}, source_folds=deepcopy(folds or []))


def _geometry(model, root, counts):
    if model['life'] != root['life']:
        raise ValueError('frozen model and query require the same teacher')
    features = _features(root, model['mode'], counts)
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    if not legal or len(legal) != len(root['legal_actions']):
        raise ValueError('distinct legal query actions required')
    distances = {action: [_distance(features[action], center['features']) for center in model['centers']] for action in legal}
    pair_count = len(legal)*(len(legal)-1)//2
    sorted_pairs = {}
    for first, second in combinations(legal, 2):
        rows = [((distances[first][prototype['center_indices'][0]]+distances[second][prototype['center_indices'][1]])
                 /(2.*model['median_squared_distance']), index) for index, prototype in enumerate(model['prototypes'])]
        sorted_pairs[estimation._pair_key(first, second)] = sorted(rows)
    distance_pairs = len(legal)*len(model['centers'])
    columns = model['constants']['columns']
    counts.update(pair_geometry_preparations=1, pair_query_center_distance_pairs=distance_pairs,
        pair_query_distance_component_subtractions=columns*distance_pairs,
        pair_query_distance_component_squares=columns*distance_pairs,
        pair_query_distance_component_addends=columns*distance_pairs,
        pair_query_prototype_distance_checks=pair_count*len(model['prototypes']),
        pair_query_prototype_distance_additions=pair_count*len(model['prototypes']),
        pair_query_prototype_distance_normalizations=pair_count*len(model['prototypes']),
        pair_query_prototype_sorts=pair_count, pair_query_prototype_sort_items=pair_count*len(model['prototypes']))
    return dict(legal_actions=legal, sorted_pairs=sorted_pairs)


def _decision(model, root, geometry, counts):
    legal, n = geometry['legal_actions'], len(geometry['legal_actions'])
    theta = {action: [0., 0., 0.] for action in legal}
    estimated = {}
    for first, second in combinations(legal, 2):
        key = estimation._pair_key(first, second)
        nearest = geometry['sorted_pairs'][key][:model['k']]
        minimum = nearest[0][0]
        neighbors = [dict(prototype_index=index, distance=distance,
            raw_weight=exp(-(distance-minimum)/model['temperature'])*model['prototypes'][index]['root_mass'])
            for distance, index in nearest]
        total = sum(row['raw_weight'] for row in neighbors)
        for row in neighbors:
            row['weight'] = row['raw_weight']/total
        delta = [sum(row['weight']*model['prototypes'][row['prototype_index']]['tail_difference'][component]
                     for row in neighbors) for component in range(3)]
        for component in range(3):
            theta[first][component] += delta[component]/n
            theta[second][component] -= delta[component]/n
        estimated[key] = dict(actions=[first, second], estimated_tail_delta=delta, neighbors=neighbors)
        counts.update(pair_neighbor_exponentials=len(neighbors), pair_neighbor_root_mass_products=len(neighbors),
            pair_neighbor_weight_addends=len(neighbors), pair_neighbor_normalizations=len(neighbors),
            pair_tail_prediction_products=3*len(neighbors), pair_projection_divisions=6,
            pair_projection_accumulations=6, pair_estimates=1)
    predicted = {action: [root['immediate_rewards'][action]+theta[action][0], *theta[action][1:]] for action in legal}
    predicted_pairs, residual_values = {}, []
    for first, second in combinations(legal, 2):
        key = estimation._pair_key(first, second)
        projected = [theta[first][component]-theta[second][component] for component in range(3)]
        residual = [estimated[key]['estimated_tail_delta'][component]-projected[component] for component in range(3)]
        estimated[key].update(projected_tail_delta=projected, projection_residual=residual)
        predicted_pairs[key] = [predicted[first][component]-predicted[second][component] for component in range(3)]
        residual_values.extend(residual)
        counts.update(pair_projected_component_subtractions=3, pair_projection_residual_subtractions=3,
                      pair_predicted_component_subtractions=3)
    selected, best = legal[0], None
    for action in legal:
        vector = predicted[action]
        value = vector[0]-vector[1]+vector[2]
        if best is None or value > best+EPSILON:
            selected, best = action, value
    counts.update(pair_decisions=1, pair_reward_additions=len(legal), pair_utility_evaluations=len(legal),
                  pair_projection_residual_squares=len(residual_values))
    return dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=False, leaf=0,
        reason='single_legal_action' if n == 1 else 'local_pair_projection', predicted_components=predicted,
        predicted_pairs=predicted_pairs, estimated_pairs=estimated, tail_offsets=theta,
        projection_residual_sse=sum(value*value for value in residual_values),
        projection_residual_max=max(map(abs, residual_values), default=0.))


def choose_action(model, root, counts=None):
    work = Counter()
    geometry = _geometry(model, root, work)
    result = _decision(model, root, geometry, work)
    result.update(work=dict(work), feature_work={})
    if counts is not None:
        counts.update(work)
    return result


def _observable(root):
    result = {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
                                        'immediate_rewards', 'fallback_action', 'action_map')}
    for key in ('relation_features', 'conditional_features'):
        if key in root:
            result[key] = root[key]
    return result


def _heldout(model, roots, geometries, counts):
    groups, choices = {}, []
    for root in sorted(roots, key=lambda row: row['root_id']):
        observable = _observable(root)
        decision = _decision(model, observable, geometries[root['root_id']], counts)
        action = decision['canonical_action']
        vector = list(map(float, root['action_components'][action]))
        utility = vector[0]-vector[1]+vector[2]
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], canonical_action=action,
                            components=vector, utility=utility))
        counts.update(pair_heldout_action_vector_reads=1, pair_heldout_component_reads=3,
                      pair_heldout_utility_evaluations=1)
    records = []
    for source in sorted(groups):
        vectors = groups[source]
        mean = [sum(vector[i] for vector in vectors)/len(vectors) for i in range(3)]
        records.append(dict(source_id=source, roots=len(vectors), components=mean, utility=mean[0]-mean[1]+mean[2]))
        counts.update(pair_heldout_group_component_means=3, pair_heldout_group_utility_evaluations=1)
    return records, choices


def _configuration(design, k, temperature, folds, counts):
    counts.update(pair_predictor_configurations=1, new_predictors_fitted=1)
    return _model(design, k, temperature, folds)


def _select(rows, mode, life, costs):
    sources = sorted({row['source_id'] for row in rows})
    if len(sources) != SOURCE_GROUPS:
        raise ValueError('36 fixed SOURCE groups required')
    folds = [sources[::2], sources[1::2]]
    costs.update(pair_source_fold_assignments=len(sources), pair_selection_candidates=len(K_VALUES)*len(TEMPERATURES))
    designs, heldouts, geometries, fold_records = [], [], [], []
    for fold, heldout_sources in enumerate(folds):
        training = [row for row in rows if row['source_id'] not in heldout_sources]
        heldout = sorted([row for row in rows if row['source_id'] in heldout_sources], key=lambda row: row['root_id'])
        design = prepare_design(training, mode, life, costs)
        prototype_model = _model(design, K_VALUES[0], TEMPERATURES[0], folds)
        geometry = {row['root_id']: _geometry(prototype_model, _observable(row), costs) for row in heldout}
        designs.append(design); heldouts.append(heldout); geometries.append(geometry)
        fold_records.append(dict(fold=fold, train_sources=design['source_ids'], heldout_sources=heldout_sources, design=design))
    candidates, selected_k, selected_temperature, best = [], K_VALUES[0], TEMPERATURES[0], None
    for k in K_VALUES:
        for temperature in TEMPERATURES:
            results, all_groups = [], []
            for fold in range(2):
                before = Counter(costs)
                model = _configuration(designs[fold], k, temperature, folds, costs)
                group_records, choices = _heldout(model, heldouts[fold], geometries[fold], costs)
                all_groups.extend(group_records)
                results.append(dict(fold=fold, group_records=group_records, choices=choices,
                                    prediction_counts=dict(Counter(costs)-before)))
            all_groups.sort(key=lambda row: row['source_id'])
            utility = sum(row['utility'] for row in all_groups)/len(sources)
            candidates.append(dict(k=k, temperature=temperature, utility=utility, group_records=all_groups, fold_results=results))
            costs.update(pair_selection_group_mean_reads=len(sources), pair_selection_score_comparisons=1)
            if best is None or utility > best+EPSILON:
                selected_k, selected_temperature, best = k, temperature, utility
    final_design = prepare_design(rows, mode, life, costs)
    model = _configuration(final_design, selected_k, selected_temperature, folds, costs)
    selection = dict(schema=SCHEMA+'.selection', mode=mode, life=life, k_values=list(K_VALUES),
        temperatures=list(TEMPERATURES), source_folds=folds, folds=fold_records, candidates=candidates,
        selected_k=selected_k, selected_temperature=selected_temperature, selected_utility=best, costs=dict(costs))
    return model, selection


def fit_model(examples, mode, life=0):
    """Select a prototype configuration using complete actual SOURCE utility."""
    costs = Counter(new_linear_solves=0, new_eigen_decompositions=0, new_svd_decompositions=0,
                    new_environment_samples=0, new_source_games=0, new_native_weight_updates=0)
    rows = [deepcopy(row) for row in examples if row['life'] == life]
    if len(rows) != SOURCE_ROOTS:
        raise ValueError('143 fixed SOURCE roots required')
    try:
        model, selection = _select(rows, mode, life, costs)
    except Exception as error:
        raise PairExecutionError(mode+':source_selection', costs, error) from error
    return dict(model=model, selection=selection, costs=dict(costs))
