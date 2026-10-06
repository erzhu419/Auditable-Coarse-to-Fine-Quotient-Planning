"""One action-shared full-consequence model from exact same-root contrasts.

Six action-oriented afterstate aggregates replace root partitions and fixed
action biases. Predictions are relative vectors, never event probabilities.
"""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from math import sqrt

import numpy as np

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from . import controlled_predictive_exact_h3_v177 as exact
from . import controlled_predictive_consequence_partition_v172 as estimation
from .controlled_predictive_consequence_partition_v172 import ACTIONS, EPSILON, MIN_ACTION_ROOTS

SCHEMA = 'acfqp.shared_consequences.v179'
FEATURE_NAMES = ('goal_reached', 'vacancies', 'row_positive_equal', 'col_positive_equal',
                 'row_goal_pair', 'col_goal_pair')
ROTATIONS = (D4Transform.IDENTITY, D4Transform.ROTATE_90,
             D4Transform.ROTATE_180, D4Transform.ROTATE_270)
GOAL_RANK = 11


def action_features_from_root(root, counts=None):
    """Map each legal action's afterstate to its unique DOWN rotation."""
    work, features = Counter(), {}
    if 'action_features' in root:
        features = {action: list(root['action_features'][action]) for action in ACTIONS if action in root['action_features']}
        if any(len(vector) != len(FEATURE_NAMES) for vector in features.values()):
            raise ValueError('six frozen action-oriented features required')
        work.update(shared_feature_cache_hits=1, shared_cached_feature_reads=6*len(features))
    else:
        for action in ACTIONS:
            swipe = ground.Swipe2048Action(action)
            after, _, legal = ground.swipe_board_v1(tuple(root['canonical_board']), swipe)
            work['shared_ground_swipe_calls'] += 1
            if not legal:
                continue
            for transform in ROTATIONS:
                work['shared_direction_transport_tests'] += 1
                if ground.transform_action_v1(swipe, transform) == ground.Swipe2048Action.DOWN:
                    break
            oriented = ground.transform_board_v1(after, transform)
            work.update(shared_afterstate_rotations=1, shared_rotated_tile_moves=16,
                        shared_goal_tile_reads=16, shared_vacancy_tile_reads=16)
            vector = [int(max(oriented) >= GOAL_RANK), sum(rank == 0 for rank in oriented), 0, 0, 0, 0]
            for axis_index, axis in enumerate(('row', 'col')):
                for line in range(4):
                    values = oriented[line*4:line*4+4] if axis == 'row' else oriented[line::4]
                    packed = [rank for rank in values if rank > 0]
                    work.update(shared_compressed_lines=1, shared_line_tile_reads=4)
                    for pair in range(3):
                        work['shared_adjacent_slots_inspected'] += 1
                        if pair+1 < len(packed):
                            first, second = packed[pair:pair+2]
                            vector[2+axis_index] += int(first == second)
                            vector[4+axis_index] += int(first == second == GOAL_RANK-1)
                            work.update(shared_positive_equal_tests=1, shared_goal_pair_tests=1)
            features[action] = vector
        work['shared_feature_maps_computed'] += 1
    if counts is not None:
        counts.update(work)
    return features


def fit_model(examples, life=0):
    """Fit one minimum-norm 6x3 coefficient matrix; no intercept or selection."""
    examples = list(examples)
    counts, feature_counts = Counter(), Counter()
    prepared, folds = exact._prepare_exact(examples, life, counts)
    originals = {row['root_id']: row for row in examples if row['life'] == life}
    action_roots = {action: set() for action in ACTIONS}
    pair_roots = {estimation._pair_key(a, b): set() for a, b in combinations(ACTIONS, 2)}
    design, targets, records, labels = [], [], [], []
    for item in prepared:
        features = action_features_from_root(originals[item['root_id']], feature_counts)
        item['training_outcome']['action_features'] = deepcopy(features)
        for action in item['legal']:
            action_roots[action].add(item['root_id'])
        label = dict(root_id=item['root_id'], source_id=item['source_id'],
                     legal_actions=list(item['legal']), label_kind='exact_enumerated_vector', pairs=[])
        for first, second, weight, target in item['observations']:
            row = [features[first][index]-features[second][index] for index in range(6)]
            scale = sqrt(weight)
            design.append([scale*value for value in row])
            targets.append([scale*value for value in target])
            pair_roots[estimation._pair_key(first, second)].add(item['root_id'])
            pair = dict(actions=[first, second], weight=weight, design=row, components=list(target))
            label['pairs'].append(deepcopy(pair))
            records.append(dict(root_id=item['root_id'], source_id=item['source_id'], **pair))
            counts.update(shared_pair_rows=1, shared_feature_value_reads=12,
                          shared_feature_difference_subtractions=6, shared_weight_square_roots=1,
                          shared_weighted_design_scalings=6, shared_weighted_target_scalings=3)
        labels.append(label)
    matrix, target_matrix = np.asarray(design, dtype=float).reshape(-1, 6), np.asarray(targets, dtype=float).reshape(-1, 3)
    coefficients, _, rank, singular_values = np.linalg.lstsq(matrix, target_matrix, rcond=None)
    counts.update(shared_lstsq_solves=1, shared_design_matrix_cells=matrix.size,
                  shared_target_matrix_cells=target_matrix.size, shared_coefficient_cells=18)
    component_losses = [0., 0., 0.]
    for record in records:
        prediction = np.asarray(record['design'], dtype=float) @ coefficients
        residual = prediction-np.asarray(record['components'])
        losses = [record['weight']*float(value)**2 for value in residual]
        for component in range(3):
            component_losses[component] += losses[component]
        record.update(predicted_components=list(map(float, prediction)), residual_components=list(map(float, residual)),
                      weighted_component_losses=losses, weighted_loss=sum(losses))
        counts.update(shared_fit_prediction_component_evaluations=3, shared_residual_component_subtractions=3,
                      shared_weighted_component_losses=3)
    action_ids = {action: sorted(roots) for action, roots in action_roots.items()}
    pair_ids = {pair: sorted(roots) for pair, roots in pair_roots.items()}
    sources = dict(Counter(item['source_id'] for item in prepared))
    return dict(schema=SCHEMA, mode='SHARED', life=life, query='risk1', native_teacher_query=exact.QUERY,
        horizon=exact.HORIZON, label_kind='exact_enumerated_vector', feature_names=list(FEATURE_NAMES),
        coefficients=coefficients.tolist(), rank=int(rank), singular_values=singular_values.tolist(),
        component_losses=component_losses, loss=sum(component_losses), action_root_ids=action_ids,
        pair_root_ids=pair_ids, connected_components=estimation._components(pair_ids),
        constants=dict(min_action_roots=MIN_ACTION_ROOTS, epsilon=EPSILON, goal_rank=GOAL_RANK,
                       features=6, intercept=False, ridge=False, rcond=None),
        root_ids=[item['root_id'] for item in prepared], source_ids=sorted(sources), source_folds=folds,
        source_root_counts=sources, fit_labels=labels, fit_residuals=records,
        training_outcomes=[deepcopy(item['training_outcome']) for item in prepared],
        fit_counts=dict(counts), feature_counts=dict(feature_counts))


def choose_action(payload, root, counts=None):
    """Choose from the shared relative vector plus exact current first reward."""
    if payload['life'] != root['life']:
        raise ValueError('shared model and root require the same frozen teacher')
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    if not legal or len(legal) != len(root['legal_actions']) or root['fallback_action'] not in legal:
        raise ValueError('distinct legal actions and observable-only fallback required')
    feature_work = Counter()
    features = action_features_from_root(root, feature_work)
    work = Counter(shared_decisions=1, shared_legal_action_reads=len(legal))
    action_counts = {action: len(payload['action_root_ids'][action]) for action in legal}
    pair_counts = {estimation._pair_key(a, b): len(payload['pair_root_ids'][estimation._pair_key(a, b)])
                   for a, b in combinations(legal, 2)}
    connected = deepcopy(payload['connected_components'])
    component_id = {action: index for index, group in enumerate(connected) for action in group}
    work.update(shared_action_support_lookups=len(legal), shared_pair_support_lookups=len(pair_counts),
                shared_component_membership_lookups=len(legal))
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif any(action_counts[action] < MIN_ACTION_ROOTS for action in legal):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component_id[action] for action in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback, reason = None, False, 'selected'
    predicted = {}
    for action in legal:
        vector = [sum(features[action][index]*payload['coefficients'][index][component] for index in range(6))
                  for component in range(3)]
        vector[0] += root['immediate_rewards'][action]
        predicted[action] = vector
        work.update(shared_prediction_feature_reads=18, shared_prediction_coefficient_reads=18,
                    shared_prediction_component_evaluations=3, shared_immediate_reward_reads=1,
                    shared_reward_additions=1)
    pairs = {}
    for first, second in combinations(legal, 2):
        if component_id[first] == component_id[second]:
            pairs[estimation._pair_key(first, second)] = [predicted[first][i]-predicted[second][i] for i in range(3)]
            work['shared_predicted_pair_component_subtractions'] += 3
    if selected is None:
        selected, best = legal[0], None
        for action in legal:
            vector = predicted[action]
            value = vector[0]-vector[1]+vector[2]
            work['shared_utility_evaluations'] += 1
            if best is None or value > best+EPSILON:
                selected, best = action, value
    support = dict(action_root_counts=action_counts, pair_root_counts=pair_counts,
                   connected_components=connected, required_actions=legal, complete=not fallback)
    if counts is not None:
        counts.update(work); counts.update(feature_work)
    result = dict(canonical_action=selected, fallback=fallback, leaf=0, reason=reason,
        predicted_components=predicted, predicted_pairs=pairs, support=support,
        work=dict(work), feature_work=dict(feature_work))
    if 'action_map' in root:
        result['actual_action'] = root['action_map'][selected]
    return result
