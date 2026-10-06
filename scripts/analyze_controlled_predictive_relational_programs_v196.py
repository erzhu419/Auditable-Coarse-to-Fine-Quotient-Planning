"""Independent tile-lineage witnesses and SOURCE-weighted relational programs."""
import argparse
from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_conditional_pairs_v194 as old
from scripts import analyze_controlled_predictive_pair_regions_v195 as regions
import numpy as np

relation, nonlinear = old.relation, old.nonlinear
ACTIONS, EPS, close, utility = old.ACTIONS, old.EPS, old.close, old.utility
SCHEMA = 'acfqp.relational_program_learning.v196'
RESULT_SCHEMA = 'acfqp.relational_programs.v196'
OUTPUT = PROJECT/'reports/controlled_predictive_relational_programs_v196'
MODES = ('PROGRAM', 'TERMINAL', 'PROGRAM_NEIGHBOR')
DEPTHS, MIN_ROOTS, K_VALUES = (1, 2, 4, 6), (4, 8), (1, 8, 32)
OLD_NAMES = ('TREE32', 'RAW32', 'CONDITIONAL', 'PAIR98', 'NONLINEAR', 'RELATION', 'LINEAR', 'INTERACT', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
MODEL_NAMES = (*MODES, *OLD_NAMES)
COMPARATORS = (*MODEL_NAMES[1:], 'FALLBACK')
PRIMARY = ('TERMINAL', 'PROGRAM_NEIGHBOR', 'TREE32', 'CONDITIONAL', 'LINEAR', 'NONLINEAR', 'OLD_SHARED')
INPUT_NAMES = ('v195_stage_checks.json', 'v195_run.json', 'v195_roots.json', 'region_models.json', 'region_libraries.json',
    'conditional_models.json', 'nonlinear_model.json', 'relation_model.json', 'expanded_models.json', 'baseline_models.json',
    'learned_rule.json', 'dense_models.json')
WORDS = [(a,) for a in ACTIONS]+[(a, b) for a in ACTIONS for b in ACTIONS]
ACTION_FEATURE_NAMES = ('goal_now', *(f'{"_".join(word)}:{name}' for word in WORDS for name in ('valid', 'goal', 'linked_goal', 'score')))
FEATURE_NAMES = tuple(f'{side}:{name}' for side in ('first', 'second') for name in ACTION_FEATURE_NAMES)


def line_cells(action, line):
    return {'DOWN': [12+line, 8+line, 4+line, line], 'UP': [line, 4+line, 8+line, 12+line],
        'LEFT': [4*line+i for i in range(4)], 'RIGHT': [4*line+3-i for i in range(4)]}[action]


def trace_afterstate(board, payload, counts=None):
    """Execute only payload primitives, with path-scoped two-parent genealogy."""
    work = counts if counts is not None else Counter(); primitive = payload['program']; goal_rank = payload['goal_rank']
    if not primitive['pack'] or primitive['consumption'] != 'once':
        raise ValueError('the frozen inherited pack/once primitive is required')
    tiles = tuple(dict(id=i, rank=int(rank), origins=(i,), born=0) if rank else None for i, rank in enumerate(board))
    occupied = [dict(id=tile['id'], cell=i, rank=tile['rank']) for i, tile in enumerate(tiles) if tile]
    winning = [tile['id'] for tile in tiles if tile and tile['rank'] >= goal_rank]
    work.update(program_initial_cell_reads=16, program_contracts_built=1, program_goal_rank_reads=len(occupied))
    prefixes = [dict(id=0, parent=None, action=None, executed=False, valid=True, goal=bool(winning), linked_goal=False,
        score=0., events=[], goal_ids=winning)]
    states, indices, words, values = {(): (tiles, 0, 0)}, {(): 0}, [], [float(bool(winning))]
    for word in WORDS:
        parent_word = word[:-1]; parent = prefixes[indices[parent_word]]; source, score, prior_merges = states[parent_word]
        executed = parent['valid'] and not parent['goal']; events = []
        if executed:
            work.update(program_swipe_calls=1, program_line_rewrites=4)
            output, gained, linked = [None]*16, 0, False
            for line in range(4):
                cells = line_cells(word[-1], line); packed = [source[i] for i in cells if source[i]]
                work.update(program_tile_reads=4, program_packed_tiles=len(packed)); at, destination = 0, 0
                while at < len(packed):
                    left = packed[at]; right = packed[at+1] if at+1 < len(packed) else None
                    merge = False
                    if right is not None:
                        work['program_merge_relation_checks'] += 1
                        merge = left['rank'] > 0 and right['rank'] > 0 and (primitive['merge_relation'] == 'any' or
                            primitive['merge_relation'] == 'equal' and left['rank'] == right['rank'])
                    if merge:
                        rank = max(left['rank'], right['rank'])+primitive['rank_increment']
                        reward = {'zero': 0, 'count': 1, 'left_value': 1 << left['rank'], 'output_value': 1 << rank}[primitive['reward_rule']]
                        origins = tuple(sorted(left['origins']+right['origins'])); identity = 16+prior_merges+len(events)
                        tile = dict(id=identity, rank=rank, origins=origins, born=len(word))
                        events.append(dict(id=identity, left=left['id'], right=right['id'], left_rank=left['rank'], right_rank=right['rank'],
                            rank=rank, reward=reward, origins=list(origins), step=len(word), line=line, cell=cells[destination]))
                        work.update(program_merges=1, program_dependency_edges=2, program_origin_items_read=len(origins), program_score_additions=1)
                        gained += reward; at += 2
                        linked |= rank >= goal_rank and any(0 < tile['born'] < len(word) for tile in (left, right))
                    else:
                        tile = left; at += 1
                    output[cells[destination]] = tile; destination += 1; work['program_tile_placements'] += 1
            moved = tuple(output)
            valid = [tile['rank'] if tile else 0 for tile in source] != [tile['rank'] if tile else 0 for tile in moved]
            score += gained; work.update(program_rank_comparison_reads=32, program_prefix_score_additions=1)
            winning = [tile['id'] for tile in moved if tile and tile['rank'] >= goal_rank]
            work['program_goal_rank_reads'] += sum(tile is not None for tile in moved)
            goal, linked_goal = bool(winning), parent['linked_goal'] or linked
            merge_count = prior_merges+len(events)
        else:
            moved, valid, goal, linked_goal, winning, merge_count = source, parent['valid'], parent['goal'], parent['linked_goal'], parent['goal_ids'], prior_merges
            work['program_stopped_prefix_reuses'] += 1
        prefix_id = len(prefixes)
        prefix = dict(id=prefix_id, parent=parent['id'], action=word[-1], executed=executed, valid=valid,
            goal=goal, linked_goal=linked_goal, score=score/2048., events=events, goal_ids=list(winning))
        prefixes.append(prefix); indices[word] = prefix_id; states[word] = (moved, score, merge_count)
        words.append(dict(actions=list(word), prefix_id=prefix_id, **{key: prefix[key] for key in ('valid', 'goal', 'linked_goal', 'score')}))
        values.extend((float(valid), float(goal), float(linked_goal), score/2048.)); work.update(program_word_records=1, program_feature_values_written=4)
    work.update(program_prefix_records=21, program_feature_values_written=1)
    return dict(schema=RESULT_SCHEMA+'.contract', goal_now=prefixes[0]['goal'], initial_tiles=occupied, prefixes=prefixes, words=words, values=values)


def cache_roots(roots, payload):
    work = Counter()
    for root in roots:
        if 'program_contracts' in root:
            work['program_cache_hits'] += 1
            continue
        root['program_contracts'] = {a: trace_afterstate(root['raw_afterstates'][a], payload, work) for a in ACTIONS if a in root['legal_actions']}
        work['program_cache_roots_built'] += 1
    return dict(work)


def prepare_library(examples, library_id, life=0, costs=None):
    counts = costs if costs is not None else Counter(); before = Counter(counts); counts['shared_library_attempts'] += 1
    roots = sorted((root for root in examples if root['life'] == life), key=lambda row: row['root_id'])
    source_counts, samples = dict(Counter(root['source_id'] for root in roots)), []
    for root in roots:
        legal = [a for a in ACTIONS if a in root['legal_actions']]
        vectors = {a: list(map(float, root['action_components'][a])) for a in legal}
        tails = {a: [vectors[a][0]-root['immediate_rewards'][a], *vectors[a][1:]] for a in legal}
        number = len(legal)*(len(legal)-1)
        counts.update(library_roots_read=1, library_program_feature_reads=81*len(legal), library_label_component_reads=3*len(legal),
            library_reward_reads=len(legal), library_tail_reward_subtractions=len(legal))
        for a in legal:
            for b in legal:
                if a == b:
                    continue
                samples.append(dict(root_id=root['root_id'], source_id=root['source_id'], actions=[a, b],
                    features162=list(root['program_contracts'][a]['values'])+list(root['program_contracts'][b]['values']),
                    tail_difference=[tails[a][k]-tails[b][k] for k in range(3)], root_mass=1./(source_counts[root['source_id']]*number)))
                counts.update(library_prototypes_built=1, library_pair_feature_copies=162, library_tail_component_subtractions=3)
    counts['shared_library_preparations'] += 1
    return dict(schema=SCHEMA+'.library', library_id=library_id, life=life, feature_names=list(FEATURE_NAMES),
        root_ids=[root['root_id'] for root in roots], source_ids=sorted(source_counts), source_root_counts=source_counts,
        prototypes=samples, work=dict(Counter(counts)-before))


def distance(first, second):
    return sum((a-b)**2 for a, b in zip(first, second, strict=True))


def weighted_moments(samples, indices, counts=None):
    mass, sums, squares = 0., [0.]*3, [0.]*3
    for index in indices:
        sample = samples[index]; weight, vector = sample['root_mass'], sample['tail_difference']
        mass += weight
        for component in range(3):
            sums[component] += weight*vector[component]
            squares[component] += weight*vector[component]*vector[component]
    if counts is not None:
        counts.update(tree_moment_sample_reads=len(indices), tree_moment_weight_additions=len(indices),
            tree_moment_WY_products=3*len(indices), tree_moment_WY2_products=6*len(indices), tree_moment_component_additions=6*len(indices))
    return mass, sums, squares


def sse(moments):
    mass, sums, squares = moments
    return sum(squares[k]-sums[k]*sums[k]/mass for k in range(3))


def build_tree(library, max_depth, min_leaf_roots, input_columns, counts=None):
    samples = library['prototypes']; work = counts if counts is not None else Counter()
    work['tree_fit_attempts'] += 1
    def node(indices, depth, node_id):
        moments = weighted_moments(samples, indices, work); mass, sums, _ = moments
        roots = {samples[i]['root_id'] for i in indices}; sources = {samples[i]['source_id'] for i in indices}
        value = sse(moments)
        result = dict(kind='leaf', node_id=node_id, depth=depth, prototype_count=len(indices), root_count=len(roots),
            source_count=len(sources), weight_sum=mass, mean=[v/mass for v in sums], weighted_sse=value,
            prototype_indices=indices)
        work.update(tree_nodes_built=1, tree_node_mean_divisions=3, tree_node_component_sse_terms=3)
        if depth >= max_depth or len(roots) < min_leaf_roots or len(sources) < 2:
            work['tree_leaves_built'] += 1
            return result
        best = None
        for feature, column in enumerate(input_columns):
            order = sorted(indices, key=lambda i: (samples[i]['features162'][column], i))
            work.update(tree_feature_sorts=1, tree_feature_sort_items=len(indices))
            if samples[order[0]]['features162'][column] == samples[order[-1]]['features162'][column]:
                work['tree_constant_features'] += 1
                continue
            remaining_roots = Counter(samples[i]['root_id'] for i in indices)
            remaining_sources = Counter(samples[i]['source_id'] for i in indices)
            left_roots, left_sources = set(), set()
            w, wy, wy2 = 0., [0.]*3, [0.]*3
            for at, index in enumerate(order[:-1]):
                sample = samples[index]; weight, vector = sample['root_mass'], sample['tail_difference']
                w += weight
                for k in range(3):
                    wy[k] += weight*vector[k]; wy2[k] += weight*vector[k]*vector[k]
                for key, seen, remaining in (('root_id', left_roots, remaining_roots), ('source_id', left_sources, remaining_sources)):
                    name = sample[key]; seen.add(name); remaining[name] -= 1
                    if remaining[name] == 0:
                        del remaining[name]
                work.update(tree_prefix_sample_updates=1, tree_prefix_WY_products=3, tree_prefix_WY2_products=6,
                    tree_prefix_component_additions=6, tree_prefix_support_updates=4)
                threshold = sample['features162'][column]
                if threshold == samples[order[at+1]]['features162'][column]:
                    continue
                work['tree_observed_thresholds'] += 1
                if min(len(left_roots), len(remaining_roots)) < min_leaf_roots or min(len(left_sources), len(remaining_sources)) < 2:
                    work['tree_unsupported_thresholds'] += 1
                    continue
                right = (mass-w, [sums[k]-wy[k] for k in range(3)], [moments[2][k]-wy2[k] for k in range(3)])
                gain = value-sse((w, wy, wy2))-sse(right)
                work.update(tree_supported_split_candidates=1, tree_candidate_component_sse_terms=6, tree_gain_comparisons=1)
                if gain > EPS and (best is None or gain > best[0]+EPS):
                    best = gain, feature, threshold
        if best is None:
            work['tree_leaves_built'] += 1
            return result
        gain, feature, threshold = best; column = input_columns[feature]
        left = [i for i in indices if samples[i]['features162'][column] <= threshold]
        right = [i for i in indices if samples[i]['features162'][column] > threshold]
        result.pop('prototype_indices'); result.update(kind='split', feature=feature, threshold=threshold, improvement=gain,
            left=node(left, depth+1, 2*node_id+1), right=node(right, depth+1, 2*node_id+2))
        work.update(tree_splits_built=1, tree_split_partition_tests=2*len(indices))
        return result
    result = node(list(range(len(samples))), 0, 0)
    work.update(tree_predictors_fitted=1, new_predictors_fitted=1)
    return result


def tree_identity(actual, expected):
    fields = ('kind', 'node_id', 'depth', 'prototype_count', 'root_count', 'source_count')
    if any(actual[key] != expected[key] for key in fields):
        return False
    if expected['kind'] == 'leaf':
        return actual['prototype_indices'] == expected['prototype_indices']
    return actual['feature'] == expected['feature'] and actual['threshold'] == expected['threshold'] and (
        tree_identity(actual['left'], expected['left']) and tree_identity(actual['right'], expected['right']))


def model_from_library(library, mode, counts=None, *, max_depth=1, min_leaf_roots=4, k=1):
    work = counts if counts is not None else Counter(); columns = [0, 81] if mode == 'TERMINAL' else list(range(162))
    model = dict(schema=SCHEMA+'.model', mode=mode, library_id=library['library_id'], life=library['life'],
        query='risk1', native_teacher_query=old.native_exact.QUERY, horizon=old.native_exact.HORIZON,
        label_kind='exact_enumerated_vector', input_columns=columns, feature_names=[FEATURE_NAMES[i] for i in columns],
        constants=dict(columns=len(columns), epsilon=EPS, goal_rank=11,
            projection='COMPLETE_GRAPH_ZERO_MEAN', antisymmetrization='FORWARD_MINUS_REVERSE_OVER_TWO'))
    if mode != 'PROGRAM_NEIGHBOR':
        work[mode+'_tree_fit_attempts'] += 1
        model.update(max_depth=max_depth, min_leaf_roots=min_leaf_roots,
            tree=build_tree(library, max_depth, min_leaf_roots, columns, work))
        work[mode+'_tree_predictors_fitted'] += 1
    else:
        work.update(neighbor_predictor_configurations=1, new_predictors_fitted=1); model['k'] = k
    return model


def query_inputs(root, counts):
    legal = [a for a in ACTIONS if a in root['legal_actions']]
    values = {a: list(root['program_contracts'][a]['values']) for a in legal}
    pairs = {f'{a}|{b}': dict(actions=[a, b], forward=values[a]+values[b], reverse=values[b]+values[a]) for a, b in combinations(legal, 2)}
    counts.update(query_input_roots=1, query_program_feature_reads=81*len(legal),
        query_pair_inputs=2*len(pairs), query_pair_input_copies=324*len(pairs))
    return dict(legal_actions=legal, pairs=pairs)


def prototype_matrix(library, counts):
    matrix = np.asarray([row['features162'] for row in library['prototypes']], dtype=float)
    counts.update(neighbor_matrix_preparations=1, neighbor_matrix_cells=matrix.size)
    return matrix


def neighbor_geometry(query, library, counts, matrix):
    for pair in query['pairs'].values():
        for direction in ('forward', 'reverse'):
            differences = matrix-np.asarray(pair[direction], dtype=float)
            squares = differences*differences
            rows = sorted((float(value), index) for index, value in enumerate(np.sum(squares, axis=1)))
            pair[direction+'_neighbors'] = rows; n = len(rows)
            counts.update(neighbor_distance_pairs=n, neighbor_distance_component_subtractions=162*n,
                neighbor_distance_component_squares=162*n, neighbor_distance_component_addends=162*n,
                neighbor_sorts=1, neighbor_sort_items=n)


def directional_prediction(model, pair, direction, library, counts):
    if model['mode'] != 'PROGRAM_NEIGHBOR':
        tree, values = model['tree'], pair[direction]
        while tree['kind'] == 'split':
            counts['tree_prediction_split_tests'] += 1
            tree = tree['left'] if values[model['input_columns'][tree['feature']]] <= tree['threshold'] else tree['right']
        counts.update(tree_direction_predictions=1, tree_prediction_component_reads=3)
        return dict(components=list(tree['mean']), leaf_id=tree['node_id'])
    rows = pair[direction+'_neighbors'][:model['k']]; samples = library['prototypes']
    mass = sum(samples[index]['root_mass'] for _, index in rows)
    neighbors = [dict(prototype_index=index, distance=d, weight=samples[index]['root_mass']/mass) for d, index in rows]
    vector = [sum(row['weight']*samples[row['prototype_index']]['tail_difference'][component] for row in neighbors) for component in range(3)]
    counts.update(neighbor_direction_predictions=1, neighbor_mass_addends=len(neighbors), neighbor_normalizations=len(neighbors),
        neighbor_tail_component_products=3*len(neighbors))
    return dict(components=vector, neighbors=neighbors)


def decision_from_query(model, root, library, query, counts):
    legal = query['legal_actions']; n = len(legal); theta, estimates = {a: [0.]*3 for a in legal}, {}
    for key, pair in query['pairs'].items():
        forward = directional_prediction(model, pair, 'forward', library, counts)
        reverse = directional_prediction(model, pair, 'reverse', library, counts)
        delta = [(forward['components'][k]-reverse['components'][k])/2. for k in range(3)]
        a, b = pair['actions']
        for k in range(3):
            theta[a][k] += delta[k]/n; theta[b][k] -= delta[k]/n
        estimates[key] = dict(actions=list(pair['actions']), forward=forward, reverse=reverse, estimated_tail_delta=delta)
        counts.update(pair_antisymmetric_component_subtractions=3, pair_antisymmetric_component_divisions=3,
            pair_projection_divisions=6, pair_projection_accumulations=6)
    predicted = {a: [root['immediate_rewards'][a]+theta[a][0], *theta[a][1:]] for a in legal}
    predicted_pairs, residuals = {}, []
    for key, pair in estimates.items():
        a, b = pair['actions']; projected = [theta[a][k]-theta[b][k] for k in range(3)]
        residual = [pair['estimated_tail_delta'][k]-projected[k] for k in range(3)]
        pair.update(projected_tail_delta=projected, projection_residual=residual)
        predicted_pairs[key] = [predicted[a][k]-predicted[b][k] for k in range(3)]; residuals.extend(residual)
        counts.update(pair_projected_component_subtractions=3, pair_projection_residual_subtractions=3, pair_predicted_component_subtractions=3)
    chosen, best = legal[0], None
    for action in legal:
        value = utility(predicted[action])
        if best is None or value > best+EPS:
            chosen, best = action, value
    counts.update(pair_decisions=1, pair_reward_additions=n, pair_utility_evaluations=n, pair_projection_residual_squares=len(residuals))
    return dict(canonical_action=chosen, actual_action=root['action_map'][chosen], fallback=False, leaf=0,
        reason='single_legal_action' if n == 1 else 'pair_region_projection', predicted_components=predicted,
        predicted_pairs=predicted_pairs, estimated_pairs=estimates, tail_offsets=theta,
        projection_residual_sse=sum(value*value for value in residuals), projection_residual_max=max(map(abs, residuals), default=0.))


def choose_action(model, root, library, counts=None):
    work = Counter(); query = query_inputs(root, work)
    if model['mode'] == 'PROGRAM_NEIGHBOR':
        neighbor_geometry(query, library, work, prototype_matrix(library, work))
    result = decision_from_query(model, root, library, query, work); result.update(work=dict(work), feature_work={})
    if counts is not None:
        counts.update(work)
    return result


def heldout(model, library, roots, queries, counts):
    groups, choices = {}, []
    for root in roots:
        selected = decision_from_query(model, observable(root), library, queries[root['root_id']], counts)['canonical_action']
        vector = list(map(float, root['action_components'][selected])); value = utility(vector)
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], canonical_action=selected, components=vector, utility=value))
        counts.update(heldout_action_vector_reads=1, heldout_component_reads=3, heldout_utility_evaluations=1)
    records = []
    for source in sorted(groups):
        vectors = groups[source]; mean = [sum(vector[k] for vector in vectors)/len(vectors) for k in range(3)]
        records.append(dict(source_id=source, roots=len(vectors), components=mean, utility=utility(mean)))
        counts.update(heldout_group_component_means=3, heldout_group_utility_evaluations=1)
    return records, choices


def fit_models(examples, life=0):
    counts = Counter(new_linear_solves=0, new_eigen_decompositions=0, new_svd_decompositions=0,
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0)
    roots = sorted((root for root in examples if root['life'] == life), key=lambda row: row['root_id'])
    sources = sorted({root['source_id'] for root in roots}); folds = [sources[::2], sources[1::2]]
    libraries, heldouts, queries = {}, [], []; counts['source_fold_assignments'] += len(sources)
    for fold, withheld in enumerate(folds):
        library = prepare_library([root for root in roots if root['source_id'] not in withheld], f'FOLD_{fold}', life, counts)
        libraries[f'FOLD_{fold}'] = library; rows = [root for root in roots if root['source_id'] in withheld]; cached = {}; matrix = prototype_matrix(library, counts)
        for root in rows:
            query = query_inputs(observable(root), counts); neighbor_geometry(query, library, counts, matrix); cached[root['root_id']] = query
        heldouts.append(rows); queries.append(cached)
    selections, selected = {}, {}
    for mode, configurations in (('PROGRAM', [(d, r) for d in DEPTHS for r in MIN_ROOTS]), ('TERMINAL', [(d, r) for d in DEPTHS for r in MIN_ROOTS]), ('PROGRAM_NEIGHBOR', [(k,) for k in K_VALUES])):
        candidates, best, configuration = [], None, configurations[0]
        for parameters in configurations:
            results, groups = [], []
            for fold in range(2):
                library = libraries[f'FOLD_{fold}']; before = Counter(counts)
                kwargs = dict(max_depth=parameters[0], min_leaf_roots=parameters[1]) if mode != 'PROGRAM_NEIGHBOR' else dict(k=parameters[0])
                model = model_from_library(library, mode, counts, **kwargs)
                records, choices = heldout(model, library, heldouts[fold], queries[fold], counts); groups.extend(records)
                result = dict(fold=fold, library_id=library['library_id'], group_records=records, choices=choices, work=dict(Counter(counts)-before))
                if mode != 'PROGRAM_NEIGHBOR':
                    result['tree'] = model['tree']
                results.append(result)
            groups.sort(key=lambda row: row['source_id']); score = sum(row['utility'] for row in groups)/len(sources)
            metadata = dict(max_depth=parameters[0], min_leaf_roots=parameters[1]) if mode != 'PROGRAM_NEIGHBOR' else dict(k=parameters[0])
            candidates.append(dict(**metadata, utility=score, group_records=groups, fold_results=results))
            counts.update(selection_group_mean_reads=len(sources), selection_score_comparisons=1)
            if best is None or score > best+EPS:
                best, configuration = score, parameters
        selections[mode] = dict(schema=SCHEMA+'.selection', mode=mode, source_folds=folds,
            folds=[dict(fold=fold, library_id=f'FOLD_{fold}', train_sources=libraries[f'FOLD_{fold}']['source_ids'], heldout_sources=folds[fold]) for fold in range(2)],
            candidates=candidates, selected_utility=best)
        selections[mode].update(dict(selected_depth=configuration[0], selected_min_leaf_roots=configuration[1]) if mode != 'PROGRAM_NEIGHBOR' else dict(selected_k=configuration[0]))
        selected[mode] = configuration
    libraries['FULL'] = prepare_library(roots, 'FULL', life, counts)
    models = {mode: model_from_library(libraries['FULL'], mode, counts, max_depth=selected[mode][0], min_leaf_roots=selected[mode][1]) for mode in ('PROGRAM', 'TERMINAL')}
    models['PROGRAM_NEIGHBOR'] = model_from_library(libraries['FULL'], 'PROGRAM_NEIGHBOR', counts, k=selected['PROGRAM_NEIGHBOR'][0])
    return dict(models=models, selection=selections, libraries=libraries, costs=dict(counts))


def observable(root):
    seen = regions.observable(root); seen['program_contracts'] = root['program_contracts']
    for key in ('layout_features', 'action_features'):
        if key in root:
            seen[key] = root[key]
    return seen


def weights_valid(decision):
    return all(all(row['weight'] >= 0. for row in pair[direction]['neighbors']) and
        abs(sum(row['weight'] for row in pair[direction]['neighbors'])-1.) <= 1e-8
        for pair in decision['estimated_pairs'].values() for direction in ('forward', 'reverse')
        if 'neighbors' in pair[direction])


def verify_decision(saved, expected):
    return close(saved, expected) and saved['canonical_action'] == expected['canonical_action'] and weights_valid(saved)


def source_diagnostics(roots, model, library):
    rows, work = [], Counter()
    for root in sorted(roots, key=lambda row: row['root_id']):
        decision = choose_action(model, observable(root), library, work)
        if not weights_valid(decision):
            raise ValueError('SOURCE direction weights must be nonnegative and normalized')
        if model['mode'] == 'PROGRAM_NEIGHBOR':
            for pair in decision['estimated_pairs'].values():
                for direction in ('forward', 'reverse'):
                    del pair[direction]['neighbors']
        legal = [a for a in ACTIONS if a in root['legal_actions']]; vectors = root['action_components']
        values = {a: utility(vectors[a]) for a in legal}; best = max(values.values())
        oracle = next(a for a in legal if values[a] >= best-EPS); chosen = decision['canonical_action']; regret = best-values[chosen]
        rows.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision, action=chosen,
            components=list(vectors[chosen]), utility=values[chosen], oracle_action=oracle, oracle_components=list(vectors[oracle]),
            oracle_utility=best, regret=regret, positive_regret=regret > EPS))
        work.update(source_observable_root_preparations=1, source_complete_component_reads=3*len(legal),
            source_action_utility_evaluations=len(legal), source_selected_component_reads=3, source_oracle_component_reads=3,
            source_regret_subtractions=1, source_oracle_action_comparisons=legal.index(oracle)+1, source_diagnostic_root_records=1)
    n = len(rows)
    metrics = dict(roots=n, components=[math.fsum(row['components'][k] for row in rows)/n for k in range(3)],
        utility=math.fsum(row['utility'] for row in rows)/n,
        oracle_components=[math.fsum(row['oracle_components'][k] for row in rows)/n for k in range(3)],
        oracle_utility=math.fsum(row['oracle_utility'] for row in rows)/n, regret_mean=math.fsum(row['regret'] for row in rows)/n,
        positive_regret_roots=sum(row['positive_regret'] for row in rows), fallback_roots=sum(row['decision']['fallback'] for row in rows))
    work.update(source_summary_component_reads=6*n, source_summary_scalar_reads=3*n, source_summary_flag_reads=2*n)
    return dict(root_records=rows, metrics=metrics, projection_residuals=old.projection_metrics(rows), work=dict(work))


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]+[(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(4):
        for index, (a, b) in enumerate(edges):
            seed = 1960200+24*replica+index; rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]; board[a] = board[b] = 1+index%10
            for position in rng.sample([p for p in range(16) if p not in (a, b)], index%3):
                board[position] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index, horizon=3, seed=seed,
                name=f'v196_target_r{replica:02d}_{index:02d}', board=board, vacancies=index%3))
    return cases


def freeze_choices(roots, models, libraries, region_libraries):
    choices, work = {name: [] for name in (*MODEL_NAMES, 'FALLBACK')}, Counter()
    for root in roots:
        seen = observable(root)
        for name in MODEL_NAMES:
            if name in MODES:
                decision = choose_action(models[name], seen, libraries['FULL'])
            elif name in ('TREE32', 'RAW32'):
                decision = regions.choose_action(models[name], seen, region_libraries['FULL'])
            else:
                chooser = old.choose_action if name in ('CONDITIONAL', 'PAIR98') else nonlinear.choose_action if name == 'NONLINEAR' else relation.choose_action if name == 'RELATION' else (
                    relation.dense.choose_action if name in ('LINEAR', 'INTERACT') else relation.shared.choose_action if name in ('SHARED', 'OLD_SHARED')
                    else relation.exact.choose_action if name == 'ONE' else relation.layout.choose_action)
                decision = chooser(models[name], seen)
            work.update(decision['work']); work.update(decision.get('feature_work', {})); work['frozen_model_choices'] += 1
            choices[name].append(dict(root_id=root['root_id'], mode=name, canonical_action=decision['canonical_action'],
                actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']; work['frozen_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action, actual_action=root['action_map'][action],
            fallback=False, decision=dict(reason='observable_immediate_reward', work={'frozen_fallback_choices': 1})))
    return choices, dict(work)


def success_diagnostics(records, chosen):
    result = {}
    for mode in (*MODES, 'TREE32', 'RAW32', 'CONDITIONAL', 'PAIR98'):
        eligible, missed, wrong = 0, [], []
        for root in records:
            selected, oracle = root['models'][mode], root['models']['ORACLE']
            truth = selected['components'][2]-oracle['components'][2]
            if selected['regret'] <= EPS or abs(truth) <= EPS:
                continue
            eligible += 1; first, second = sorted((selected['action'], oracle['action']), key=ACTIONS.index)
            pair = chosen[mode][root['root_id']]['decision']['estimated_pairs'][first+'|'+second]
            estimate = pair['estimated_tail_delta'][2]*(1. if pair['actions'][0] == selected['action'] else -1.)
            if abs(estimate) <= EPS:
                missed.append(root['root_id'])
            elif truth*estimate < 0.:
                wrong.append(root['root_id'])
        result[mode] = dict(eligible_roots=eligible, missed=len(missed), wrong_direction=len(wrong),
            missed_root_ids=missed, wrong_direction_root_ids=wrong)
    return result


def summarize(roots, labels, choices, selections, models, source):
    by_id = {row['root_id']: row['action_components'] for row in labels}
    chosen = {name: {row['root_id']: row for row in rows} for name, rows in choices.items()}
    names, records = (*MODEL_NAMES, 'FALLBACK', 'ORACLE'), []
    for root in roots['TARGET']:
        vectors = by_id[root['root_id']]; oracle = root['legal_actions'][0]
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
    def means(rows):
        result = {}
        for name in names:
            vector = [math.fsum(row['models'][name]['components'][k] for row in rows)/len(rows) for k in range(3)]
            result[name] = dict(components=vector, utility=utility(vector), positive_regret_roots=sum(row['models'][name]['regret'] > EPS for row in rows),
                fallback_roots=sum(row['models'][name]['fallback'] for row in rows))
        return result
    def contrasts(rows):
        tree = [dict(root_id=row['root_id'], models={'PROGRAM': row['models']['PROGRAM']}) for row in rows]
        return {'PROGRAM_MINUS_'+name: relation.coverage.coverage_effect(tree,
            [dict(root_id=row['root_id'], models={'PROGRAM': row['models'][name]}) for row in rows], 'PROGRAM') for name in COMPARATORS}
    metrics, effects = means(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=means(rows), comparisons=contrasts(rows)) for replica in sorted({row['replica'] for row in records})
        for rows in [[row for row in records if row['replica'] == replica]]]
    source_modes = {}
    for mode in MODES:
        selection = selections[mode]
        configuration = dict(selected_depth=selection['selected_depth'], selected_min_leaf_roots=selection['selected_min_leaf_roots']) if mode != 'PROGRAM_NEIGHBOR' else dict(selected_k=selection['selected_k'])
        source_modes[mode] = dict(**configuration, source_heldout_utility=selection['selected_utility'],
            feature_columns=models[mode]['constants']['columns'], actual=deepcopy(source[mode]['metrics']))
    headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    return dict(schema=RESULT_SCHEMA+'.summary', complete=True, roots=len(records),
        SOURCE=dict(roots=len(roots['SOURCE']), design_groups=len({root['source_id'] for root in roots['SOURCE']}), modes=source_modes),
        models=metrics, comparisons=effects, replicas=replicas, root_records=records,
        projection_residuals=dict(SOURCE={mode: old.projection_metrics(source[mode]['root_records']) for mode in MODES},
            TARGET={mode: old.projection_metrics(choices[mode]) for mode in (*MODES, 'TREE32', 'RAW32', 'CONDITIONAL', 'PAIR98')}),
        success_diagnostics=success_diagnostics(records, chosen), oracle_minus_one=headroom,
        oracle_minus_program=metrics['ORACLE']['utility']-metrics['PROGRAM']['utility'],
        headroom_closed_fraction=effects['PROGRAM_MINUS_ONE']['utility']/headroom if headroom > EPS else None,
        whole_cohort_positive_vs_primary=all(effects['PROGRAM_MINUS_'+name]['utility'] > EPS for name in PRIMARY),
        all_replicas_positive_vs_primary=all(row['comparisons']['PROGRAM_MINUS_'+name]['utility'] > EPS for row in replicas for name in PRIMARY),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=41,
        new_tree_fits=34, new_neighbor_configurations=7, new_parameter_solves=0)

def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io, bindings = [], Counter(), Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = INPUT_NAMES
    check('twelve_frozen_SOURCE_and_control_inputs', [(row['saved_ref'], row['phase']) for row in inputs] ==
        [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    stage, inherited = read('inputs/inherited/v195_stage_checks.json'), read('inputs/inherited/v195_run.json')
    check('settled_V195_complete', stage['valid'] and inherited['status'] == 'complete')
    source = deepcopy(read('inputs/inherited/v195_roots.json')['SOURCE'])
    check('unchanged_SOURCE143_36_groups_and_complete_labels', len(source) == 143 and len({root['source_id'] for root in source}) == 36 and
        all(len(root['action_components'][a]) == 3 for root in source for a in root['legal_actions']))
    payload = read('inputs/inherited/learned_rule.json'); source_features = cache_roots(source, payload)
    check('once_SOURCE_tile_lineage_prefix_extraction_paid', run['costs']['source_features']['counts'] == source_features and
        source_features.get('program_cache_roots_built') == 143)
    fitted = fit_models(source); models, selections, libraries, learning = fitted['models'], fitted['selection'], fitted['libraries'], fitted['costs']
    saved_models, saved_selections, saved_libraries, saved_source = read('models.json'), read('selection.json'), read('libraries.json'), read('source_diagnostics.json')
    check('exact_shared_three_library_roster_and_SOURCE_equal_mass', set(saved_libraries) == {'FOLD_0', 'FOLD_1', 'FULL'} and
        close(saved_libraries, libraries) and all(sample['root_mass'] >= 0. for library in saved_libraries.values() for sample in library['prototypes']) and
        all(saved['features162'] == expected['features162'] for name in libraries
            for saved, expected in zip(saved_libraries[name]['prototypes'], libraries[name]['prototypes'], strict=True)))
    check('SOURCE_only_folds_full_RFS_program_terminal_neighbor_actual_utility_selection', close(saved_selections, selections))
    check('41_models_and_native_goal_teacher_metadata', close(saved_models, models))
    exact_trees = all(tree_identity(saved_models[mode]['tree'], models[mode]['tree']) and all(
        tree_identity(saved_fold['tree'], expected_fold['tree'])
        for saved_candidate, expected_candidate in zip(saved_selections[mode]['candidates'], selections[mode]['candidates'], strict=True)
        for saved_fold, expected_fold in zip(saved_candidate['fold_results'], expected_candidate['fold_results'], strict=True))
        for mode in ('PROGRAM', 'TERMINAL'))
    check('34_exact_tree_split_and_leaf_partition_identities', exact_trees)
    check('three_shared_libraries_34_trees_seven_neighbor_configs_and_geometry_reuse_paid', learning['shared_library_preparations'] == 3 and
        learning['tree_predictors_fitted'] == 34 and learning['PROGRAM_tree_predictors_fitted'] == learning['TERMINAL_tree_predictors_fitted'] == 17 and
        learning['neighbor_predictor_configurations'] == 7 and learning['new_predictors_fitted'] == 41 and
        learning['query_input_roots'] == 143 and learning['neighbor_matrix_preparations'] == 2 and all(learning[key] == 0 for key in
        ('new_linear_solves', 'new_eigen_decompositions', 'new_svd_decompositions')) and run['costs']['learning']['counts'] == learning)
    diagnostics = {}
    for mode in MODES:
        diagnostics[mode] = source_diagnostics(source, models[mode], libraries['FULL'])
        check(mode+'_actual_SOURCE_RFS_choices_and_compact_directions', close(saved_source[mode], diagnostics[mode]))
        check(mode+'_paid_actual_SOURCE_evaluation', run['costs']['source_evaluation_'+mode]['counts'] == diagnostics[mode]['work'])
    cases = cohort_cases(); target, observation_work = relation.observe_roots(cases)
    feature_work = relation.coverage.cache_roots(target); relation_work = relation.cache_roots(target)
    conditional_work = old.cache_roots(target); raw_work = regions.cache_roots(target); program_work = cache_roots(target, payload); roots = dict(SOURCE=source, TARGET=target)
    check('96_fresh_seeded_H3_cases', read('target_cases.json') == cases)
    saved_roots = read('roots.json')
    check('unchanged_SOURCE_and_FRESH_observations_all_caches', close(saved_roots, roots) and
        all(saved['program_contracts'] == expected['program_contracts'] for split in ('SOURCE', 'TARGET')
            for saved, expected in zip(saved_roots[split], roots[split], strict=True)))
    observed = run['costs']['observations']
    check('once_fresh_observation_and_all_five_cache_costs', observed['counts'] == observation_work and
        observed['feature_counts'] == feature_work and observed['relation_counts'] == relation_work and
        observed['conditional_counts'] == conditional_work and observed['raw_counts'] == raw_work and observed['program_counts'] == program_work)
    expanded, retained, dense = read('inputs/inherited/expanded_models.json'), read('inputs/inherited/baseline_models.json'), read('inputs/inherited/dense_models.json')
    all_models = dict(expanded, **dense, **models, **read('inputs/inherited/region_models.json'), **read('inputs/inherited/conditional_models.json'), NONLINEAR=read('inputs/inherited/nonlinear_model.json'),
        RELATION=read('inputs/inherited/relation_model.json'), OLD_SHARED=retained['SHARED'], ONE=retained['ONE'])
    region_libraries = read('inputs/inherited/region_libraries.json')
    choices, choice_work = freeze_choices(target, all_models, libraries, region_libraries); saved_choices = read('choices.json')
    check('all_SOURCE_selected_and_fixed_control_choices_before_labels', close(saved_choices, choices))
    for mode in MODES:
        check(mode+'_actual_EPS_actions_and_nonnegative_normalized_direction_weights',
            all(verify_decision(saved['decision'], expected['decision']) for saved, expected in zip(saved_choices[mode], choices[mode], strict=True)))
    check('paid_frozen_RFS_decisions', run['costs']['choices']['counts'] == choice_work)
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
    summary = summarize(roots, labels, choices, selections, models, diagnostics)
    check('18_arm_RFS_16_contrasts_replicas_projection_and_goal_failure_diagnostics', close(read('summary.json'), summary))
    phases = ('protocol_frozen', 'source_selection', 'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete')
    check('SOURCE_selection_and_all_choices_frozen_before_target_labels', [(row['phase'], row['input_reads']) for row in run['phase_history']] ==
        [(phase, 0 if index == 0 else 12) for index, phase in enumerate(phases)])
    check('all_paid_input_and_label_counts', run['costs']['input_counts'] == dict(json_read_operations=12,
        input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs)) and run['costs']['labels']['counts'] == dict(label_work))
    accounting = all(run[key] == 96 for key in ('new_boards_generated', 'new_reference_kernel_attempts', 'new_reference_kernels',
        'new_teacher_plans', 'new_exact_label_roots', 'completed_roots'))
    accounting = accounting and run['new_learning_attempts'] == 1 and run['new_predictors_fitted'] == 41 and run['new_tree_fits'] == 34 and (
        run['new_neighbor_configurations'] == 7 and run['shared_library_preparations'] == 3)
    accounting = accounting and run['resource_cap_per_board'] == 200000 and all(run[key] == 0 for key in
        ('new_parameter_solves', 'new_environment_samples', 'new_source_games', 'new_native_weight_updates'))
    check('one_SOURCE_selection_41_instances_shared_three_libraries_96_labels_no_parameter_solves', accounting)
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema=RESULT_SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(independent_parameter_solves=0, independent_eigen_solves=0, independent_svd_solves=0,
            independent_tree_fits=learning['tree_predictors_fitted'], independent_neighbor_configurations=learning['neighbor_predictor_configurations'],
            independent_shared_library_preparations=learning['shared_library_preparations'],
            new_environment_samples=0, physical_branches_replayed=0, new_kernels_reintegrated=0, old_models_refitted=0,
            independent_input_counts=dict(io), independent_SOURCE_feature_counts=source_features, reconstructed_learning_counts=learning,
            independent_source_evaluation_counts={mode: diagnostics[mode]['work'] for mode in MODES}, independent_observation_counts=observation_work,
            independent_feature_counts=feature_work, independent_relation_counts=relation_work, independent_conditional_counts=conditional_work,
            independent_raw_counts=raw_work, independent_program_counts=program_work, independent_choice_counts=choice_work, independent_new_label_binding_counts=dict(bindings),
            reconstructed_acquisition_counts=dict(label_work), original_run_costs=run['costs'], inherited_cost_refs=run['inherited_cost_refs'],
            test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'])))


if __name__ == '__main__':
    main()
