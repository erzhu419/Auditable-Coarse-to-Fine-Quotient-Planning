"""Learn the V177 exact-data partition using action-afterstate structure.

The label estimator, actual-utility crossfit objective, support and deployment
rules remain unchanged. Only the frozen split-predicate family changes.
"""
from collections import Counter
from copy import deepcopy

from acfqp.domains import standard_2048 as ground
from . import controlled_predictive_exact_h3_v177 as exact
from . import controlled_predictive_consequence_partition_v172 as estimation
from . import controlled_predictive_utility_partition_v174 as learning
from .controlled_predictive_consequence_partition_v172 import (
    ACTIONS, EPSILON, MAX_LEAVES, MIN_CHILD_ROOTS,
)

SCHEMA = 'acfqp.afterstate_structure.v178'
GOAL_RANK = 11
FEATURES_PER_ACTION = 66
FEATURE_COUNT = len(ACTIONS)*FEATURES_PER_ACTION


def _vocabulary():
    features = []
    for action in ACTIONS:
        descriptions = [dict(kind='legal', feature_id=f'{action}:legal'),
                        dict(kind='goal_reached', feature_id=f'{action}:goal_reached')]
        descriptions += [dict(kind='vacancy', cell=cell, feature_id=f'{action}:vacancy:{cell}')
                         for cell in range(16)]
        for axis in ('row', 'col'):
            for line in range(4):
                for pair in range(3):
                    for kind in ('positive_equal', 'goal_pair'):
                        descriptions.append(dict(kind=kind, axis=axis, line=line, pair=pair,
                            feature_id=f'{action}:{axis}:{line}:pair:{pair}:{kind}'))
        for description in descriptions:
            features.append(dict(index=len(features), action=action, **description))
    return features


FEATURE_VOCABULARY = _vocabulary()


def feature_from_root(root, counts=None):
    """Return the fixed 264 Boolean predicates, using a retained cache if given."""
    work = Counter()
    if 'structural_features' in root:
        features = list(root['structural_features'])
        if len(features) != FEATURE_COUNT:
            raise ValueError('the frozen structural cache has 264 features')
        work.update(structural_feature_cache_hits=1, structural_cached_feature_reads=FEATURE_COUNT)
    else:
        board, features = tuple(root['canonical_board']), []
        for action in ACTIONS:
            after, _, legal = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
            work['structural_ground_swipe_calls'] += 1
            if not legal:
                features.extend([0]*FEATURES_PER_ACTION)
                work['structural_illegal_feature_zero_assignments'] += FEATURES_PER_ACTION
                continue
            features += [1, int(max(after) >= GOAL_RANK)]
            features += [int(rank == 0) for rank in after]
            work.update(structural_goal_tile_reads=16, structural_vacancy_tile_reads=16)
            for axis in ('row', 'col'):
                for line in range(4):
                    values = after[line*4:line*4+4] if axis == 'row' else after[line::4]
                    packed = [rank for rank in values if rank > 0]
                    work.update(structural_compressed_lines=1, structural_line_tile_reads=4)
                    for pair in range(3):
                        work['structural_adjacent_slots_inspected'] += 1
                        if pair+1 < len(packed):
                            first, second = packed[pair:pair+2]
                            features += [int(first == second), int(first == second == GOAL_RANK-1)]
                            work.update(structural_positive_equal_tests=1, structural_goal_pair_tests=1)
                        else:
                            features += [0, 0]
                            work['structural_absent_pair_zero_assignments'] += 2
            work['structural_legal_feature_values_assigned'] += FEATURES_PER_ACTION
        work['structural_feature_vectors_computed'] += 1
    if counts is not None:
        counts.update(work)
    return features


def _search_node(prepared, indices, node_id, folds, source_counts, counts, records):
    counts['utility_search_nodes_evaluated'] += 1
    if any(sum(prepared[index]['fold'] == fold for index in indices) < 2*MIN_CHILD_ROOTS for fold in range(2)):
        counts['utility_nodes_without_two_fit_children'] += 1
        return None
    best = None
    for feature in FEATURE_VOCABULARY:
        record = learning._candidate(prepared, indices, node_id, feature['index'], 0, folds, source_counts, counts)
        record['feature_id'] = feature['feature_id']
        records.append(record)
        if record['score'] is None or record['score'] <= EPSILON:
            continue
        counts['utility_positive_candidate_comparisons'] += 1
        if best is None or record['score'] > best['score']+EPSILON:
            best = record
    return best


def fit_partition(examples, life=0):
    """Fit the exact-label utility tree using only the declared structural bits."""
    examples = list(examples)
    fit_counts, search_counts, node_counts, feature_counts = Counter(), Counter(), Counter(), Counter()
    prepared, folds = exact._prepare_exact(examples, life, fit_counts)
    originals = {row['root_id']: row for row in examples if row['life'] == life}
    for item in prepared:
        features = feature_from_root(originals[item['root_id']], feature_counts)
        item['board'] = features
        item['training_outcome']['structural_features'] = list(features)
    source_counts = dict(Counter(item['source_id'] for item in prepared))
    nodes, records = [dict(node_id=0, kind='leaf', leaf_id=0)], []
    active = {0: list(range(len(prepared)))}
    node_indices = {0: list(active[0])}
    candidates = {0: _search_node(prepared, active[0], 0, folds, source_counts, search_counts, records)}
    while len(active) < MAX_LEAVES:
        best = None
        for node_id in sorted(candidates):
            candidate = candidates[node_id]
            if candidate is None:
                continue
            search_counts['utility_global_candidate_comparisons'] += 1
            if best is None or candidate['score'] > best['score']+EPSILON:
                best = candidate
        if best is None:
            break
        node_id, left_id, right_id = best['node_id'], len(nodes), len(nodes)+1
        best['selected'] = True
        left = [i for i in active[node_id] if prepared[i]['board'][best['cell']] <= 0]
        right = [i for i in active[node_id] if prepared[i]['board'][best['cell']] > 0]
        nodes[node_id] = dict(node_id=node_id, kind='split', cell=best['cell'], threshold=0,
            feature_id=best['feature_id'], left=left_id, right=right_id, utility_gain=best['score'])
        del active[node_id], candidates[node_id]
        for child_id, indices in ((left_id, left), (right_id, right)):
            nodes.append(dict(node_id=child_id, kind='leaf', leaf_id=child_id))
            active[child_id], node_indices[child_id] = indices, indices
        search_counts['utility_splits_applied'] += 1
        if len(active) < MAX_LEAVES:
            for child_id in (left_id, right_id):
                candidates[child_id] = _search_node(prepared, active[child_id], child_id, folds,
                                                   source_counts, search_counts, records)
    fits = {}
    for node in nodes:
        node_id = node['node_id']
        fits[str(node_id)] = dict(leaf_id=node_id, **estimation._fit_leaf(prepared, node_indices[node_id], node_counts))
        node_counts['full_discovery_node_fits'] += 1
    leaves = [deepcopy(fits[str(node_id)]) for node_id in sorted(active)]
    payload = exact._payload(prepared, folds, nodes, {}, leaves, fits, records, fit_counts,
                             search_counts, node_counts, life, 'PART_UNPRUNED')
    payload.update(schema=SCHEMA, feature_vocabulary=deepcopy(FEATURE_VOCABULARY), feature_counts=dict(feature_counts))
    payload['constants'].update(feature_count=FEATURE_COUNT, features_per_action=FEATURES_PER_ACTION,
                                feature_thresholds=[0], goal_rank=GOAL_RANK)
    return payload


def choose_action(payload, root, counts=None):
    """Route structural bits; preserve legal actions, full coefficients and reward."""
    feature_work = Counter()
    features = feature_from_root(root, feature_work)
    feature_root = dict(root, canonical_board=features)
    decision = exact.choose_action(payload, feature_root, counts)
    decision['feature_work'] = dict(feature_work)
    if counts is not None:
        counts.update(feature_work)
    return decision
