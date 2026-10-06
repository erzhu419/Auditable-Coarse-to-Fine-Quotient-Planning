"""Independent shared merge/block relations, SOURCE selection and fresh scores."""
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
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_mechanism_interactions_v188 as dense

previous = dense.previous
coverage, layout, shared, exact, ridge = dense.coverage, dense.layout, dense.shared, dense.exact, dense.ridge
ACTIONS, EPS, LAMBDAS, same = dense.ACTIONS, dense.EPS, dense.LAMBDAS, dense.same
SCHEMA = 'acfqp.merge_relations.v190'
LEARNING_SCHEMA = 'acfqp.merge_relation_learning.v190'
DIRECTIONS = ('LEFT', 'RIGHT', 'UP', 'DOWN')
RANK_BASES = ('rank_over_goal', 'goal_value_fraction')
NODE_MOMENT_NAMES = ('count', 'zeros_left', 'zeros_right', 'zeros_up', 'zeros_down',
    'adjacent_zero_left', 'adjacent_zero_right', 'adjacent_zero_up', 'adjacent_zero_down')
PAIR_MOMENT_NAMES = ('same_row', 'same_col', 'row_blocker_count', 'col_blocker_count',
    'row_blocker_rank', 'col_blocker_rank', 'row_gap', 'col_gap', 'row_col_product',
    *(f'packing_{d.lower()}_gap' for d in DIRECTIONS),
    *(f'packing_{d.lower()}_clear_alignment' for d in DIRECTIONS),
    *(f'packing_{d.lower()}_blocker_rank' for d in DIRECTIONS),
    *(f'packing_{d.lower()}_blocker_{end}' for d in DIRECTIONS for end in ('first', 'last')),
    *(f'once_pair_{d.lower()}' for d in DIRECTIONS))
VACANCY_MOMENT_NAMES = tuple(f'vacancy_neighbor_{d.lower()}_rank_{r}' for d in DIRECTIONS for r in (1, 2))
FEATURE_NAMES = (*shared.FEATURE_NAMES,
    *(f'{b}:{kind}:{name}' for b in RANK_BASES
      for kind, names in (('node', NODE_MOMENT_NAMES), ('pair', PAIR_MOMENT_NAMES)) for name in names),
    *VACANCY_MOMENT_NAMES)
CONTROLS = ('LINEAR', 'INTERACT', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
MODEL_NAMES = ('RELATION', *CONTROLS)
OUTPUT = PROJECT/'reports/controlled_predictive_merge_relations_v190'


def basis_metadata():
    return dict(columns=98, intercept=False, representation='oriented_afterstate_merge_relations',
        goal_rank=11, rank_bases=['rank/11', '2^(rank-11)'], node_normalizer=4., pair_normalizer=math.sqrt(120.),
        directions=list(DIRECTIONS), node_moments=list(NODE_MOMENT_NAMES), pair_moments=list(PAIR_MOMENT_NAMES),
        vacancy_moments=list(VACANCY_MOMENT_NAMES), vacancy_normalizer=4., packing_merges=False, packing_spawns=False)


def neighbors(position):
    r, c = divmod(position, 4)
    return (position-1 if c else None, position+1 if c < 3 else None,
            position-4 if r else None, position+4 if r < 3 else None)


def between(first, second):
    r1, c1 = divmod(first, 4); r2, c2 = divmod(second, 4)
    if r1 == r2:
        return [4*r1+c for c in range(min(c1, c2)+1, max(c1, c2))]
    if c1 == c2:
        return [4*r+c1 for r in range(min(r1, r2)+1, max(r1, r2))]
    return []


def build_contract(record, counts=None):
    work = Counter(relation_contracts_built=1); board, positions = [0]*16, set()
    for token in record['tokens']:
        work['relation_token_kind_reads'] += 1
        if token[0] == 'cell':
            position, rank = token[1:]; board[position] = rank; positions.add(position)
            work.update(relation_cell_token_records_read=1, relation_cell_positions_read=1, relation_cell_rank_reads=1)
    if positions != set(range(16)):
        raise ValueError('sixteen positioned cell tokens required')
    nodes, packing, once_pairs = [], {}, {}
    for p, rank in enumerate(board):
        work['relation_node_occupancy_tests'] += 1
        if not rank:
            continue
        r, c = divmod(p, 4)
        sides = ([4*r+x for x in range(c)], [4*r+x for x in range(c+1, 4)],
                 [4*x+c for x in range(r)], [4*x+c for x in range(r+1, 4)])
        zero = dict(zip(DIRECTIONS, [sum(board[q] == 0 for q in side) for side in sides]))
        adjacent = dict(zip(DIRECTIONS, [int(q is not None and board[q] == 0) for q in neighbors(p)]))
        packed = dict(LEFT=p-zero['LEFT'], RIGHT=p+zero['RIGHT'], UP=p-4*zero['UP'], DOWN=p+4*zero['DOWN'])
        nodes.append(dict(node_id=p, rank=rank, row=r, col=c, zeros=zero, adjacent_zero=adjacent,
            packed_positions=packed, moments=[1., *[zero[d]/3. for d in DIRECTIONS], *[float(adjacent[d]) for d in DIRECTIONS]]))
        work.update(relation_node_records=1, relation_side_rank_reads=sum(map(len, sides)),
            relation_node_neighbor_tests=4, relation_node_neighbor_rank_reads=sum(q is not None for q in neighbors(p)),
            relation_node_zero_normalizations=4, relation_packed_coordinates_computed=4)
    node_index = {n['node_id']: n for n in nodes}
    for d in DIRECTIONS:
        occupants = [None]*16
        for n in nodes:
            occupants[n['packed_positions'][d]] = n['node_id']
        selected = []
        for line in range(4):
            cells = [4*line+k for k in range(4)] if d in ('LEFT', 'RIGHT') else [4*k+line for k in range(4)]
            if d in ('RIGHT', 'DOWN'):
                cells = cells[::-1]
            ids = [occupants[cell] for cell in cells if occupants[cell] is not None]
            work.update(relation_once_scan_lines=1, relation_once_packing_cell_reads=4, relation_once_positive_tile_reads=len(ids))
            k = 0
            while k+1 < len(ids):
                work['relation_once_rank_comparisons'] += 1
                if board[ids[k]] == board[ids[k+1]]:
                    selected.append(sorted(ids[k:k+2])); k += 2
                    work['relation_once_pairs_selected'] += 1
                else:
                    k += 1
        packing[d] = dict(occupants=occupants); once_pairs[d] = selected
        work['relation_packing_node_placements'] += len(nodes)
    once = {d: set(map(tuple, rows)) for d, rows in once_pairs.items()}; pairs = []
    for first, second in combinations(nodes, 2):
        work['relation_equal_rank_pair_tests'] += 1
        if first['rank'] != second['rank']:
            continue
        a, b = first['node_id'], second['node_id']; raw_cells = between(a, b)
        raw_blockers = [p for p in raw_cells if board[p]]; total_rank = sum(board[p] for p in raw_blockers)
        same_row, same_col = first['row'] == second['row'], first['col'] == second['col']
        dr, dc = second['row']-first['row'], second['col']-first['col']
        values = [float(same_row), float(same_col), len(raw_blockers)/2. if same_row else 0.,
            len(raw_blockers)/2. if same_col else 0., total_rank/22. if same_row else 0., total_rank/22. if same_col else 0.,
            abs(dr)/3., abs(dc)/3., dr*dc/9.]
        projections, gaps, clears, rank_sums, ends = {}, [], [], [], []
        for d in DIRECTIONS:
            pa, pb = first['packed_positions'][d], second['packed_positions'][d]
            ra, ca = divmod(pa, 4); rb, cb = divmod(pb, 4)
            aligned = ca == cb if d in ('LEFT', 'RIGHT') else ra == rb
            gap = abs(ca-cb)/3. if d in ('LEFT', 'RIGHT') else abs(ra-rb)/3.
            cells = between(pa, pb) if aligned else []
            blockers = [packing[d]['occupants'][p] for p in cells if packing[d]['occupants'][p] is not None]
            ranks = [board[node_id] for node_id in blockers]
            projections[d] = dict(first_position=pa, second_position=pb, aligned=aligned, blockers=blockers, blocker_ranks=ranks)
            gaps.append(gap); clears.append(float(aligned and not ranks)); rank_sums.append(sum(ranks)/22.)
            ends.extend([ranks[0]/11. if ranks else 0., ranks[-1]/11. if ranks else 0.])
            work.update(relation_pair_packing_projections=1, relation_pair_packing_coordinate_reads=2,
                relation_pair_projected_between_cells_read=len(cells), relation_pair_projected_blocker_rank_reads=len(ranks))
        masks = {d: float((a, b) in once[d]) for d in DIRECTIONS}
        pairs.append(dict(first=a, second=b, rank=first['rank'], raw_blockers=raw_blockers, projections=projections,
            once_masks=masks, moments=values+gaps+clears+rank_sums+ends+list(masks.values())))
        work.update(relation_equal_pair_records=1, relation_pair_raw_between_rank_reads=len(raw_cells), relation_once_pair_membership_tests=4)
    vacancy = [0.]*8
    for p, rank in enumerate(board):
        work['relation_vacancy_cell_tests'] += 1
        if rank:
            continue
        for index, q in enumerate(neighbors(p)):
            work['relation_vacancy_direction_checks'] += 1
            if q is not None:
                work['relation_vacancy_neighbor_rank_reads'] += 1
                if board[q] in (1, 2):
                    vacancy[2*index+board[q]-1] += .25; work['relation_vacancy_neighbor_contributions'] += 1
    work['relation_aggregate_values_copied'] += 6
    if counts is not None:
        counts.update(work)
    return dict(schema=SCHEMA+'.contract', aggregate=list(record['aggregate']), nodes=nodes, equal_pairs=pairs,
        packing=packing, once_pairs=once_pairs, vacancy_moments=vacancy)


def action_features_from_root(root, counts=None):
    work = Counter()
    if 'relation_features' in root:
        features = {a: list(root['relation_features'][a]) for a in ACTIONS if a in root['relation_features']}
        work.update(relation_feature_cache_hits=1, relation_cached_feature_reads=98*len(features))
    else:
        features = {}
        for a in ACTIONS:
            if a not in root['layout_features']:
                continue
            contract = build_contract(root['layout_features'][a], work); vector = list(map(float, contract['aggregate']))
            for power in range(2):
                node = [0.]*9; pair = [0.]*33
                for records, values, key in ((contract['nodes'], node, 'node'), (contract['equal_pairs'], pair, 'pair')):
                    for row in records:
                        weight = row['rank']/11. if power == 0 else 2.**(row['rank']-11)
                        for k, value in enumerate(row['moments']):
                            values[k] += weight*value
                        work.update(relation_rank_basis_evaluations=1)
                        work['relation_'+key+'_moment_accumulations'] += len(values)
                vector.extend(value/4. for value in node); vector.extend(value/math.sqrt(120.) for value in pair)
            vector.extend(contract['vacancy_moments']); features[a] = vector
            work.update(relation_node_projection_normalizations=18, relation_pair_projection_normalizations=66,
                relation_vacancy_projection_values_copied=8, relation_feature_vectors_computed=1)
        work['relation_feature_maps_derived'] += 1
    if counts is not None:
        counts.update(work)
    return features


def cache_roots(roots):
    work = Counter()
    for root in roots:
        root['relation_features'] = action_features_from_root(root, work)
    return dict(work)


def prepare_design(examples, life=0):
    counts, feature_counts = Counter(), Counter(); roots, features = [], {}
    for original in examples:
        counts['examples_examined'] += 1
        if original['life'] != life:
            counts['other_life_examples_excluded'] += 1; continue
        root = deepcopy(original); legal = [a for a in ACTIONS if a in root['legal_actions']]
        root['legal_actions'] = legal
        root['immediate_rewards'] = {a: float(root['immediate_rewards'][a]) for a in legal}
        root['action_components'] = {a: list(map(float, root['action_components'][a])) for a in legal}
        features[root['root_id']] = action_features_from_root(root, feature_counts); roots.append(root)
        counts.update(examples_fitted=1, legal_action_reads=len(legal), immediate_reward_reads=len(legal),
            exact_action_vector_reads=len(legal), label_component_reads=3*len(legal), tail_reward_subtractions=len(legal))
    roots.sort(key=lambda row: row['root_id']); action_roots = {a: set() for a in ACTIONS}
    pair_roots = {f'{a}|{b}': set() for a, b in combinations(ACTIONS, 2)}; labels, records = [], []
    for root in roots:
        for a in root['legal_actions']:
            action_roots[a].add(root['root_id'])
        pairs = []
        for ia, ib, weight, target in exact.exact_pair_samples(root):
            a, b = ACTIONS[ia], ACTIONS[ib]
            differences = [features[root['root_id']][a][k]-features[root['root_id']][b][k] for k in range(98)]
            sparse = [[k, value] for k, value in enumerate(differences) if value != 0.]
            pair = dict(actions=[a, b], weight=weight, design=sparse, components=target)
            pairs.append(deepcopy(pair)); records.append(dict(root_id=root['root_id'], source_id=root['source_id'], **pair))
            pair_roots[f'{a}|{b}'].add(root['root_id'])
            counts.update(paired_vector_labels=1, paired_component_subtractions=3, relation_pair_rows=1,
                relation_design_value_reads=196, relation_design_subtractions=98, relation_nonzero_design_entries=len(sparse))
        labels.append(dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=root['legal_actions'],
            label_kind='exact_enumerated_vector', pairs=pairs))
    matrix, targets = np.zeros((len(records), 98)), np.zeros((len(records), 3))
    for index, record in enumerate(records):
        scale = math.sqrt(record['weight'])
        for k, value in record['design']:
            matrix[index, k] = scale*value
        targets[index] = [scale*value for value in record['components']]
        counts.update(relation_weight_square_roots=1, relation_weighted_design_scalings=len(record['design']), relation_weighted_target_scalings=3)
    counts.update(relation_design_matrix_cells=matrix.size, relation_target_matrix_cells=targets.size, ridge_design_preparations=1)
    sources = dict(Counter(root['source_id'] for root in roots)); pair_ids = {key: sorted(ids) for key, ids in pair_roots.items()}
    return dict(schema=LEARNING_SCHEMA+'.design', mode='RELATION', life=life, basis=basis_metadata(), feature_names=list(FEATURE_NAMES),
        roots=roots, root_ids=[root['root_id'] for root in roots], source_ids=sorted(sources), source_root_counts=sources,
        action_root_ids={a: sorted(ids) for a, ids in action_roots.items()}, pair_root_ids=pair_ids,
        connected_components=shared.connected_components(pair_ids), fit_labels=labels, pair_records=records,
        design_format='sparse_columns', shape=list(matrix.shape), X=matrix, Y=targets,
        prepare_counts=dict(counts), feature_counts=dict(feature_counts), work=dict(counts+feature_counts))


def model_from_fit(design, decomposition, fitted, lambda_value, source_folds):
    result = dense.model_from_fit(design, decomposition, fitted, lambda_value, source_folds)
    result['schema'] = LEARNING_SCHEMA+'.model'
    return result


def choose_action(payload, root, counts=None):
    legal = [a for a in ACTIONS if a in root['legal_actions']]; feature_work = Counter()
    features = action_features_from_root(root, feature_work); work = Counter(relation_decisions=1, relation_legal_action_reads=len(legal))
    action_counts = {a: len(payload['action_root_ids'][a]) for a in legal}
    pair_counts = {f'{a}|{b}': len(payload['pair_root_ids'][f'{a}|{b}']) for a, b in combinations(legal, 2)}
    connected = deepcopy(payload['connected_components']); component = {a: i for i, group in enumerate(connected) for a in group}
    work.update(relation_action_support_lookups=len(legal), relation_pair_support_lookups=len(pair_counts), relation_component_membership_lookups=len(legal))
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif any(n < 4 for n in action_counts.values()):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component[a] for a in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback, reason = None, False, 'selected'
    predicted = {}
    for a in legal:
        vector = [sum(features[a][i]*payload['coefficients'][i][k] for i in range(98)) for k in range(3)]
        vector[0] += root['immediate_rewards'][a]; predicted[a] = vector
        work.update(relation_prediction_feature_reads=294, relation_prediction_coefficient_reads=294,
            relation_prediction_component_evaluations=3, relation_immediate_reward_reads=1, relation_reward_additions=1)
    pairs = {f'{a}|{b}': [predicted[a][k]-predicted[b][k] for k in range(3)]
        for a, b in combinations(legal, 2) if component[a] == component[b]}
    if pairs:
        work['relation_predicted_pair_subtractions'] += 3*len(pairs)
    if selected is None:
        best = None
        for a in legal:
            value = exact.utility(predicted[a]); work['relation_utility_evaluations'] += 1
            if best is None or value > best+EPS:
                selected, best = a, value
    result = dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=fallback, leaf=0, reason=reason,
        predicted_components=predicted, predicted_pairs=pairs, support=dict(action_root_counts=action_counts,
            pair_root_counts=pair_counts, connected_components=connected, required_actions=legal, complete=not fallback),
        work=dict(work), feature_work=dict(feature_work))
    if counts is not None:
        counts.update(work); counts.update(feature_work)
    return result


def observable(root):
    result = {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
        'immediate_rewards', 'fallback_action', 'action_map')}
    for key in ('layout_features', 'action_features', 'relation_features'):
        if key in root:
            result[key] = root[key]
    return result


def score_heldout(model, roots):
    counts, groups, choices = Counter(), {}, []
    for root in sorted(roots, key=lambda row: row['root_id']):
        decision = choose_action(model, observable(root), counts)
        vector = list(map(float, root['action_components'][decision['canonical_action']]))
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision, components=vector, utility=exact.utility(vector)))
        counts.update(heldout_action_vector_reads=1, heldout_component_reads=3, heldout_utility_evaluations=1)
    records = []
    for source, vectors in sorted(groups.items()):
        mean = [sum(v[k] for v in vectors)/len(vectors) for k in range(3)]
        records.append(dict(source_id=source, roots=len(vectors), components=mean, utility=exact.utility(mean)))
        counts.update(heldout_group_component_means=3, heldout_group_utility_evaluations=1)
    return records, choices, dict(counts)


def select_regularization(examples, life, audit_work, saved_selection=None, saved_model=None):
    sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != 36:
        raise ValueError('thirty-six fixed SOURCE groups required')
    folds = [sources[::2], sources[1::2]]; costs = Counter(source_fold_assignments=36, regularization_candidates=6)
    designs, heldouts, saved_folds, metadata = [], [], [], []
    for fold, heldout in enumerate(folds):
        train = [source for source in sources if source not in heldout]
        design = prepare_design([row for row in examples if row['life'] == life and row['source_id'] in train], life)
        designs.append(design); costs.update(design['work'])
        heldouts.append([row for row in examples if row['life'] == life and row['source_id'] in heldout])
        saved_folds.append(dict(fold=fold, train_sources=train, heldout_sources=list(heldout),
            design={key: value for key, value in design.items() if key not in ('X', 'Y')}))
    candidates, selected, best = [], LAMBDAS[0], None
    for index, lambda_value in enumerate(LAMBDAS):
        results, groups = [], []
        for fold in range(2):
            saved = None if saved_selection is None else saved_selection['candidates'][index]['fold_results'][fold]['coefficients']
            fitted, rank, singular = previous.fit_design(designs[fold], lambda_value, audit_work, saved); costs.update(fitted['counts'])
            if lambda_value == 0:
                meta = ridge.decomposition_metadata(designs[fold], rank, singular); metadata.append(meta)
                costs.update(meta['work']); saved_folds[fold]['decomposition'] = meta
            model = model_from_fit(designs[fold], metadata[fold], fitted, lambda_value, folds)
            records, choices, prediction_counts = score_heldout(model, heldouts[fold]); costs.update(prediction_counts); groups.extend(records)
            results.append(dict(fold=fold, coefficients=fitted['coefficients'], component_losses=fitted['component_losses'],
                loss=fitted['loss'], root_mean_loss=fitted['root_mean_loss'], penalty=fitted['penalty'], objective=fitted['objective'],
                group_records=records, choices=choices, prediction_counts=prediction_counts, coefficient_counts=fitted['counts']))
        groups.sort(key=lambda row: row['source_id']); utility = sum(row['utility'] for row in groups)/len(sources)
        costs.update(regularization_group_mean_reads=36, regularization_score_comparisons=1)
        candidates.append(dict(lambda_value=lambda_value, utility=utility, group_records=groups, fold_results=results))
        if best is None or utility > best+EPS:
            selected, best = lambda_value, utility
    full = prepare_design(examples, life); costs.update(full['work'])
    saved = None if saved_model is None else saved_model['coefficients']
    fitted, rank, singular = previous.fit_design(full, selected, audit_work, saved); costs.update(fitted['counts'])
    if selected > 0:
        singular = np.linalg.svd(full['X'], compute_uv=False)
        cutoff = np.finfo(float).eps*max(full['X'].shape)*(singular[0] if len(singular) else 0.)
        rank = int(sum(singular > cutoff)); audit_work.update(final_singular_values_only_decompositions=1, final_singular_values_matrix_cells=full['X'].size)
    meta = ridge.decomposition_metadata(full, rank, singular); costs.update(meta['work']); costs['new_predictors_fitted'] = costs['ridge_predictors_fitted']
    selection = dict(schema=LEARNING_SCHEMA+'.selection', mode='RELATION', life=life, basis=basis_metadata(), lambdas=list(LAMBDAS),
        source_folds=folds, folds=saved_folds, candidates=candidates, selected_lambda=selected, selected_utility=best, costs=dict(costs))
    return selection, model_from_fit(full, meta, fitted, selected, folds)


def fit_model(examples, life=0, saved_selection=None, saved_model=None):
    cached, cache_counts = [], Counter()
    for original in examples:
        if original['life'] != life:
            continue
        root = deepcopy(original); root['relation_features'] = action_features_from_root(root, cache_counts); cached.append(root)
    if len(cached) != 143:
        raise ValueError('143 fixed SOURCE roots required')
    audit_work = Counter()
    selection, model = select_regularization(cached, life, audit_work, saved_selection, saved_model)
    return dict(model=model, selection=selection, costs=dict(cache_counts+Counter(selection['costs'])), cache_counts=dict(cache_counts)), dict(audit_work)


def development_diagnostics(roots, labels, previous, certificate):
    counts = Counter(); labeled = {row['root_id']: row for row in labels}
    old_alias = {row['root_id']: row for row in previous['alias']['root_records']}
    index = {row['root_id']: row for row in roots}; rows = []
    def equal_vectors(first, second, counter):
        counts.update({counter: 1, 'development_feature_values_read': 196})
        return max(abs(a-b) for a, b in zip(first, second, strict=True)) <= EPS
    for root in roots:
        groups = []
        for action in ACTIONS:
            if action not in root['legal_actions']:
                continue
            for group in groups:
                if equal_vectors(root['relation_features'][action], root['relation_features'][group[0]], 'development_vector_comparisons'):
                    group.append(action); break
            else:
                groups.append([action])
        representatives = []
        for group in groups:
            selected = group[0]
            for action in group[1:]:
                counts['development_alias_reward_comparisons'] += 1
                if root['immediate_rewards'][action] > root['immediate_rewards'][selected]+EPS:
                    selected = action
            representatives.append(selected)
        vectors = labeled[root['root_id']]['action_components']
        oracle = max(exact.utility(vectors[a]) for a in root['legal_actions'])
        accessible = max(exact.utility(vectors[a]) for a in representatives)
        old_floor, new_floor = old_alias[root['root_id']]['within_root_regret'], oracle-accessible
        rows.append(dict(root_id=root['root_id'], old_floor=old_floor, new_floor=new_floor, old_loss=old_floor > EPS,
            new_loss=new_floor > EPS, representatives=representatives, groups=groups, oracle_utility=oracle, accessible_utility=accessible))
        reads = len(vectors)+len(representatives)
        counts.update(development_roots=1, development_complete_vector_reads=reads,
            development_component_reads=3*reads, development_utility_evaluations=reads)
    occurrences = {}
    for root in previous['problem']['roots']:
        for group in root['classes']:
            occurrences.setdefault(group['vertex_id'], []).append([root['root_id'], group['representative']])
    certified = {}
    for node in certificate['dual_explanations']:
        for edge in node['edges']:
            for role in ('best', 'bad'):
                endpoint = edge[role]
                certified.setdefault(endpoint['vertex_id'], []).append([edge['root_id'], endpoint['action']])
    def vertex_rows(items, counter, retain_occurrences):
        result = []
        for vertex, actions in sorted(items.items()):
            first = index[actions[0][0]]['relation_features'][actions[0][1]]; equal = True
            for root_id, action in actions[1:]:
                current = equal_vectors(first, index[root_id]['relation_features'][action], counter)
                equal = equal and current
            result.append(dict(vertex_id=vertex, occurrences=actions if retain_occurrences else len(actions), still_equal=equal))
        return result
    vertices = vertex_rows(occurrences, 'development_vertex_vector_comparisons', False)
    certified_vertices = vertex_rows(certified, 'development_certificate_vector_comparisons', True)
    metrics = dict(roots=len(rows), old_loss_roots=sum(row['old_loss'] for row in rows),
        new_loss_roots=sum(row['new_loss'] for row in rows),
        old_loss_roots_now_accessible=sum(row['old_loss'] and not row['new_loss'] for row in rows),
        old_floor_mean=math.fsum(row['old_floor'] for row in rows)/len(rows),
        new_floor_mean=math.fsum(row['new_floor'] for row in rows)/len(rows),
        old_cycle_vertices=len(certified_vertices), old_cycle_vertices_split=sum(not row['still_equal'] for row in certified_vertices))
    return dict(root_records=rows, vertex_records=vertices, certified_vertex_records=certified_vertices, metrics=metrics, work=dict(counts))


def freeze_choices(roots, models):
    choices, work = {name: [] for name in (*MODEL_NAMES, 'FALLBACK')}, Counter()
    for root in roots:
        observed = observable(root)
        for name in MODEL_NAMES:
            chooser = choose_action if name == 'RELATION' else dense.choose_action if name in ('LINEAR', 'INTERACT') else shared.choose_action if name in ('SHARED', 'OLD_SHARED') else exact.choose_action if name == 'ONE' else layout.choose_action
            decision = chooser(models[name], observed); work.update(decision['work']); work.update(decision.get('feature_work', {}))
            work['frozen_model_choices'] += 1
            choices[name].append(dict(root_id=root['root_id'], mode=name, canonical_action=decision['canonical_action'],
                actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']; work['frozen_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action,
            actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work=dict(frozen_fallback_choices=1))))
    return choices, dict(work)


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]+[(4*r+c, 4*r+c+4) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(4):
        for index, (first, second) in enumerate(edges):
            seed = 1900200+24*replica+index; rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]; board[first] = board[second] = 1+index % 10
            for p in rng.sample([p for p in range(16) if p not in (first, second)], index % 3):
                board[p] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index, horizon=3, seed=seed,
                name=f'v190_target_r{replica:02d}_{index:02d}', board=board, vacancies=index % 3))
    return cases


def observe_roots(cases):
    roots, work = [], Counter()
    for ordinal, case in enumerate(cases):
        root = exact.root_from_case(case, ordinal, 'FRESH', work)
        root.update(source_id=f"FRESH_REPLICA:{case['replica']:02d}", replica=case['replica'],
            stratum=case['stratum'], seed=case['seed'])
        roots.append(root)
    return roots, dict(work)


def summarize(roots, labels, choices, selection, model, development):
    indexed_labels = {row['root_id']: row for row in labels}
    indexed_choices = {name: {row['root_id']: row for row in rows} for name, rows in choices.items()}
    modes = (*MODEL_NAMES, 'FALLBACK', 'ORACLE'); records = []
    for root in roots['TARGET']:
        vectors = indexed_labels[root['root_id']]['action_components']; oracle = root['legal_actions'][0]
        for a in root['legal_actions'][1:]:
            if exact.utility(vectors[a]) > exact.utility(vectors[oracle])+EPS:
                oracle = a
        outcomes = {}
        for name in modes:
            choice = None if name == 'ORACLE' else indexed_choices[name][root['root_id']]
            action = oracle if choice is None else choice['canonical_action']; vector = vectors[action]
            outcomes[name] = dict(action=action, components=vector, utility=exact.utility(vector),
                regret=exact.utility(vectors[oracle])-exact.utility(vector), fallback=False if choice is None else choice['fallback'])
        records.append(dict(root_id=root['root_id'], replica=root['replica'], stratum=root['stratum'], models=outcomes))
    def means(rows):
        result = {}
        for name in modes:
            mean = exact.mean_vectors([row['models'][name]['components'] for row in rows])
            result[name] = dict(components=mean, utility=exact.utility(mean), positive_regret_roots=sum(row['models'][name]['regret'] > EPS for row in rows),
                fallback_roots=sum(row['models'][name]['fallback'] for row in rows))
        return result
    def contrasts(rows):
        first = [dict(root_id=row['root_id'], models={'RELATION': row['models']['RELATION']}) for row in rows]
        return {'RELATION_MINUS_'+name: coverage.coverage_effect(first,
            [dict(root_id=row['root_id'], models={'RELATION': row['models'][name]}) for row in rows], 'RELATION') for name in CONTROLS}
    metrics, effects = means(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=means(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records}) for rows in [[row for row in records if row['replica'] == replica]]]
    headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    return dict(schema=SCHEMA+'.summary', complete=True, roots=len(records),
        SOURCE=dict(roots=len(roots['SOURCE']), design_groups=len({row['source_id'] for row in roots['SOURCE']}),
            selected_lambda=selection['selected_lambda'], source_heldout_utility=selection['selected_utility'],
            source_selection=[dict(lambda_value=row['lambda_value'], utility=row['utility']) for row in selection['candidates']],
            columns=model['constants']['columns'], source_rank=model['rank'], source_root_mean_loss=model['root_mean_loss']),
        development=development['metrics'], models=metrics, comparisons=effects, replicas=replicas, root_records=records,
        oracle_minus_one=headroom, oracle_minus_relation=metrics['ORACLE']['utility']-metrics['RELATION']['utility'],
        headroom_closed_fraction=effects['RELATION_MINUS_ONE']['utility']/headroom if headroom > EPS else None,
        whole_cohort_positive_vs_linear_ridge_old_shared=all(effects['RELATION_MINUS_'+name]['utility'] > EPS for name in ('LINEAR', 'RIDGE', 'OLD_SHARED')),
        all_replicas_positive_vs_linear_ridge_old_shared=all(row['comparisons']['RELATION_MINUS_'+name]['utility'] > EPS for row in replicas for name in ('LINEAR', 'RIDGE', 'OLD_SHARED')),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=13)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io, binding_work = [], Counter(), Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ('v189_stage_checks.json', 'v189_run.json', 'v189_diagnostics.json', 'v189_summary.json',
        'v188_roots.json', 'v188_labels.json', 'expanded_models.json', 'baseline_models.json', 'learned_rule.json', 'v188_models.json')
    check('ten_frozen_SOURCE_controls_and_development_inputs',
        [(row['saved_ref'], row['phase']) for row in inputs] == [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    stage, inherited_run = read('inputs/inherited/v189_stage_checks.json'), read('inputs/inherited/v189_run.json')
    check('settled_V189_complete', stage['valid'] and inherited_run['status'] == 'complete')
    inherited_roots = read('inputs/inherited/v188_roots.json'); source = inherited_roots['SOURCE']
    controls, old_controls, dense_controls = read('inputs/inherited/expanded_models.json'), read('inputs/inherited/baseline_models.json'), read('inputs/inherited/v188_models.json')
    fixed_source = len(source) == 143 and len({row['source_id'] for row in source}) == 36 and len(inherited_roots['TARGET']) == 96
    check('unchanged_SOURCE143_36_groups_and_known_development96', fixed_source and read('source_labels.json') == source)
    development_roots = deepcopy(inherited_roots['TARGET']); development_features = cache_roots(development_roots)
    development = development_diagnostics(development_roots, read('inputs/inherited/v188_labels.json'),
        read('inputs/inherited/v189_diagnostics.json'), read('inputs/inherited/v189_summary.json'))
    check('known_counterexample_actual_numeric_projection_and_certificate_endpoints', same(read('development.json'), development))
    check('paid_development_feature_and_regrouping_costs', run['costs']['development']['feature_counts'] == development_features and run['costs']['development']['counts'] == development['work'])
    saved_selection, saved_model = read('selection.json'), read('model.json')
    fitted, solver_work = fit_model(source, saved_selection=saved_selection, saved_model=saved_model)
    selection, new_model, counts = fitted['selection'], fitted['model'], fitted['costs']
    certificates = solver_work['independent_coefficient_arrays_checked'] == solver_work['independent_coefficient_arrays_passed'] == 13
    check('13_independent_coefficients_before_actual_EPS_scoring', certificates)
    check('SOURCE_only_group_folds_full_vector_objective_and_utility_selection', same(saved_selection, selection))
    check('new_98_column_relation_model', same(saved_model, new_model))
    budget = counts['ridge_design_preparations'] == counts['ridge_svd_decompositions'] == 3 and counts['ridge_predictors_fitted'] == counts['new_predictors_fitted'] == 13
    check('once_SOURCE_cache_three_decompositions_13_filters_and_costs', budget and run['costs']['learning']['counts'] == counts)
    cases = cohort_cases(); target, observation_work = observe_roots(cases)
    feature_work = coverage.cache_roots(target); relation_work = cache_roots(target)
    check('96_fresh_seeded_targets_without_replacement', read('target_cases.json') == cases)
    roots = dict(SOURCE=source, TARGET=target)
    check('unchanged_SOURCE_and_observable_target_relation_caches', same(read('roots.json'), roots))
    observed_costs = run['costs']['observations']
    check('one_target_geometry_cache_and_relation_construction_costs', observed_costs['counts'] == observation_work
        and observed_costs['feature_counts'] == feature_work and observed_costs['relation_counts'] == relation_work)
    models = dict(controls, **dense_controls, RELATION=new_model, OLD_SHARED=old_controls['SHARED'], ONE=old_controls['ONE'])
    choices, choice_work = freeze_choices(target, models)
    check('SOURCE_selected_relation_and_all_frozen_control_choices', same(read('choices.json'), choices))
    check('full_vector_support_and_frozen_choice_costs', run['costs']['choices']['counts'] == choice_work)
    native, label_costs = read('native_labels.json'), read('label_costs.json'); ids = [root['root_id'] for root in target]
    check('complete_native_label_and_cost_rosters', [row['root_id'] for row in native] == ids and [row['root_id'] for row in label_costs] == ids)
    labels, label_work = [], Counter()
    for root, raw, cost_row in zip(target, native, label_costs, strict=True):
        teacher = read(f"teacher_policy/{root['root_id']}.json")
        check('settled_native_fraction_teacher_binding:'+root['root_id'], coverage.native_binding(root, raw, teacher))
        binding_work.update(new_label_roots_bound=1, teacher_root_records_inspected=len(teacher), exact_component_coordinates_bound=3*len(root['legal_actions']))
        provenance = dict(kind='new_exact_V69_FULL', teacher_query='goal_1_risk_1', teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')
        labels.append(exact.canonical_labels(root, raw, provenance))
        costs = cost_row['costs']; construction, compilation, export = costs['construction'], costs['compilation'], costs['teacher_export']; n = len(teacher)
        accounting = construction['concrete_states'] <= 200000 and construction['concrete_active_states'] == construction['active_states'] == n
        accounting = accounting and compilation['model_payload_calls'] == compilation['model_reload_calls'] == 1
        accounting = accounting and compilation['payload_cells'] == construction['registered_states'] == costs['label_evaluation']['kernel_cells_read']
        accounting = accounting and compilation['payload_rows'] == costs['label_evaluation']['kernel_rows_read'] and compilation['payload_outcomes'] == costs['label_evaluation']['kernel_outcomes_read']
        accounting = accounting and costs['label_evaluation']['root_labels_emitted'] == 1
        expected_export = dict(teacher_encoding_records_read=construction['concrete_states'], teacher_policy_records=n, teacher_policy_action_reads=n, teacher_policy_tile_reads=16*n)
        check('settled_acquisition_caps_and_export_costs:'+root['root_id'], accounting and export == expected_export)
        for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
            label_work.update({kind+'.'+key: value for key, value in costs[kind].items() if type(value) is int})
    check('all_canonical_target_vectors_and_fractions_bound', same(read('labels.json'), labels))
    summary = summarize(roots, labels, choices, selection, new_model, development)
    check('actual_RFS_controls_regret_replicas_and_gain_concentration', same(read('summary.json'), summary))
    phases = ['protocol_frozen', 'development_diagnostics', 'source_selection', 'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    expected_phases = [(phase, 0 if i == 0 else 10) for i, phase in enumerate(phases)]
    check('SOURCE_selection_and_all_choices_before_target_labels', [(row['phase'], row['input_reads']) for row in run['phase_history']] == expected_phases)
    input_counts = dict(json_read_operations=10, input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs))
    check('all_paid_input_and_label_counts', run['costs']['input_counts'] == input_counts and run['costs']['labels']['counts'] == dict(label_work))
    accounting = all(run[key] == 96 for key in ('new_boards_generated', 'new_reference_kernel_attempts', 'new_reference_kernels', 'new_teacher_plans', 'new_exact_label_roots', 'completed_roots'))
    accounting = accounting and run['new_learning_attempts'] == 1 and run['new_predictors_fitted'] == 13 and run['resource_cap_per_board'] == 200000
    accounting = accounting and all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates'))
    check('one_SOURCE_selection_13_predictors_96_labels_no_sampling', accounting)
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema=SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0, new_kernels_reintegrated=0, old_models_refitted=0,
            independent_input_counts=dict(io), independent_coefficient_solver_counts=solver_work, reconstructed_learning_counts=counts,
            independent_SOURCE_cache_counts=fitted['cache_counts'], independent_development_feature_counts=development_features,
            independent_development_counts=development['work'], independent_observation_counts=observation_work,
            independent_feature_counts=feature_work, independent_relation_counts=relation_work, independent_choice_counts=choice_work,
            independent_new_label_binding_counts=dict(binding_work), reconstructed_acquisition_counts=dict(label_work),
            original_run_costs=run['costs'], inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
