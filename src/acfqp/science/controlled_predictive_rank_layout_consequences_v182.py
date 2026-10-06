"""SOURCE-trained full consequences with oriented rank/layout tokens.

The six V179 aggregates remain unscaled. Three local token blocks each have
unit squared norm; unseen target tokens have zero contribution, not fallback.
"""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from math import sqrt

import numpy as np

from acfqp.domains import standard_2048 as ground
from . import controlled_predictive_exact_h3_v177 as exact
from . import controlled_predictive_consequence_partition_v172 as estimation
from .controlled_predictive_shared_consequences_v179 import FEATURE_NAMES, ROTATIONS, GOAL_RANK
from .controlled_predictive_consequence_partition_v172 import ACTIONS, EPSILON, MIN_ACTION_ROOTS

SCHEMA = 'acfqp.rank_layout_consequences.v182'
TOKEN_WEIGHTS = dict(cell=1/4, horizontal=1/sqrt(12), vertical=1/sqrt(12))


def action_features_from_root(root, counts=None):
    """Compute each oriented afterstate once for both aggregates and tokens."""
    work, features = Counter(), {}
    if 'layout_features' in root:
        features = {action: dict(aggregate=list(record['aggregate']), tokens=[list(token) for token in record['tokens']])
                    for action, record in root['layout_features'].items()}
        work.update(layout_feature_cache_hits=1, layout_cached_aggregate_reads=6*len(features),
                    layout_cached_token_records=40*len(features), layout_cached_token_values_read=144*len(features))
    else:
        for action in ACTIONS:
            swipe = ground.Swipe2048Action(action)
            after, _, legal = ground.swipe_board_v1(tuple(root['canonical_board']), swipe)
            work['layout_ground_swipe_calls'] += 1
            if not legal:
                continue
            for transform in ROTATIONS:
                work['layout_direction_transport_tests'] += 1
                if ground.transform_action_v1(swipe, transform) == ground.Swipe2048Action.DOWN:
                    break
            oriented = ground.transform_board_v1(after, transform)
            aggregate = [int(max(oriented) >= GOAL_RANK), sum(rank == 0 for rank in oriented), 0, 0, 0, 0]
            work.update(layout_afterstate_rotations=1, layout_rotated_tile_moves=16,
                        layout_aggregate_goal_tile_reads=16, layout_aggregate_vacancy_tile_reads=16)
            for axis_index, axis in enumerate(('row', 'col')):
                for line in range(4):
                    values = oriented[line*4:line*4+4] if axis == 'row' else oriented[line::4]
                    packed = [rank for rank in values if rank > 0]
                    work.update(layout_compressed_lines=1, layout_compressed_line_tile_reads=4)
                    for pair in range(3):
                        work['layout_adjacent_slots_inspected'] += 1
                        if pair+1 < len(packed):
                            first, second = packed[pair:pair+2]
                            aggregate[2+axis_index] += int(first == second)
                            aggregate[4+axis_index] += int(first == second == GOAL_RANK-1)
                            work.update(layout_positive_equal_tests=1, layout_goal_pair_tests=1)
            tokens = [['cell', cell, rank] for cell, rank in enumerate(oriented)]
            tokens += [['horizontal', row*4+column, oriented[row*4+column], oriented[row*4+column+1]]
                       for row in range(4) for column in range(3)]
            tokens += [['vertical', row*4+column, oriented[row*4+column], oriented[(row+1)*4+column]]
                       for row in range(3) for column in range(4)]
            features[action] = dict(aggregate=aggregate, tokens=tokens)
            work.update(layout_cell_token_tile_reads=16, layout_horizontal_token_tile_reads=24,
                        layout_vertical_token_tile_reads=24, layout_tokens_formed=40)
        work['layout_feature_maps_computed'] += 1
    if counts is not None:
        counts.update(work)
    return features


def _index(vocabulary, work):
    work['vocabulary_entries_indexed'] += len(vocabulary)
    return {tuple(token): index+6 for index, token in enumerate(vocabulary)}


def _encode(record, vocabulary, work):
    entries = {index: float(value) for index, value in enumerate(record['aggregate'])}
    known, unknown = 0, 0
    for token in record['tokens']:
        work['token_lookups'] += 1
        column = vocabulary.get(tuple(token))
        if column is None:
            unknown += 1; work['unknown_token_entries'] += 1
        else:
            entries[column] = TOKEN_WEIGHTS[token[0]]
            known += 1; work.update(known_token_entries=1, token_weight_loads=1)
    work.update(encoded_actions=1, aggregate_values_read=6)
    return entries, dict(known_tokens=known, unknown_tokens=unknown, total_tokens=len(record['tokens']))


def fit_model(examples, life=0):
    """Build the SOURCE-only vocabulary and fit one weighted minimum-norm model."""
    examples = list(examples)
    counts, feature_counts, encoder_counts = Counter(), Counter(), Counter()
    originals = {row['root_id']: row for row in examples if row['life'] == life}
    features = {root_id: action_features_from_root(row, feature_counts) for root_id, row in originals.items()}
    tokens = {tuple(token) for actions in features.values() for record in actions.values() for token in record['tokens']}
    vocabulary = [list(token) for token in sorted(tokens)]
    counts['vocabulary_token_records_read'] += sum(len(record['tokens']) for actions in features.values() for record in actions.values())
    counts['source_vocabulary_tokens'] += len(vocabulary)
    indexed = _index(vocabulary, encoder_counts)
    prepared, folds = exact._prepare_exact(examples, life, counts)
    action_roots = {action: set() for action in ACTIONS}
    pair_roots = {estimation._pair_key(a, b): set() for a, b in combinations(ACTIONS, 2)}
    labels, records = [], []
    for item in prepared:
        item_features = features[item['root_id']]
        item['training_outcome']['layout_features'] = deepcopy(item_features)
        encoded = {action: _encode(item_features[action], indexed, encoder_counts)[0] for action in item['legal']}
        for action in item['legal']:
            action_roots[action].add(item['root_id'])
        label = dict(root_id=item['root_id'], source_id=item['source_id'], legal_actions=list(item['legal']),
                     label_kind='exact_enumerated_vector', pairs=[])
        for first, second, weight, target in item['observations']:
            columns = sorted(set(encoded[first]) | set(encoded[second]))
            design = [[column, encoded[first].get(column, 0.)-encoded[second].get(column, 0.)] for column in columns]
            sparse = [[column, value] for column, value in design if value != 0.]
            pair = dict(actions=[first, second], weight=weight, design=sparse, components=list(target))
            records.append(dict(root_id=item['root_id'], source_id=item['source_id'], **pair))
            label['pairs'].append(deepcopy(pair))
            pair_roots[estimation._pair_key(first, second)].add(item['root_id'])
            counts.update(layout_pair_rows=1, layout_design_value_lookups=2*len(columns),
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
    coefficients, _, rank, singular_values = np.linalg.lstsq(matrix, targets, rcond=None)
    counts.update(layout_lstsq_solves=1, layout_design_matrix_cells=matrix.size,
                  layout_target_matrix_cells=targets.size, layout_coefficient_cells=3*dimensions)
    component_losses = [0., 0., 0.]
    for record in records:
        prediction = [sum(value*coefficients[column, component] for column, value in record['design']) for component in range(3)]
        residual = [prediction[i]-record['components'][i] for i in range(3)]
        losses = [record['weight']*value*value for value in residual]
        component_losses = [component_losses[i]+losses[i] for i in range(3)]
        record.update(predicted_components=prediction, residual_components=residual,
                      weighted_component_losses=losses, weighted_loss=sum(losses))
        counts.update(layout_fit_prediction_coefficient_reads=3*len(record['design']),
                      layout_fit_residual_component_subtractions=3, layout_fit_weighted_component_losses=3)
    action_ids = {action: sorted(roots) for action, roots in action_roots.items()}
    pair_ids = {pair: sorted(roots) for pair, roots in pair_roots.items()}
    source_counts = dict(Counter(item['source_id'] for item in prepared))
    return dict(schema=SCHEMA, mode='LAYOUT', life=life, query='risk1', native_teacher_query=exact.QUERY,
        horizon=exact.HORIZON, label_kind='exact_enumerated_vector', feature_names=list(FEATURE_NAMES),
        vocabulary=vocabulary, design_format='sparse_columns', coefficients=coefficients.tolist(), rank=int(rank),
        singular_values=singular_values.tolist(), component_losses=component_losses, loss=sum(component_losses),
        action_root_ids=action_ids, pair_root_ids=pair_ids, connected_components=estimation._components(pair_ids),
        constants=dict(min_action_roots=MIN_ACTION_ROOTS, epsilon=EPSILON, goal_rank=GOAL_RANK,
            aggregate_columns=6, columns=dimensions, token_weights=dict(TOKEN_WEIGHTS), intercept=False, ridge=False, rcond=None),
        root_ids=[item['root_id'] for item in prepared], source_ids=sorted(source_counts), source_folds=folds,
        source_root_counts=source_counts, fit_labels=labels, fit_residuals=records,
        training_outcomes=[deepcopy(item['training_outcome']) for item in prepared], fit_counts=dict(counts),
        feature_counts=dict(feature_counts), encoder_counts=dict(encoder_counts))


def choose_action(payload, root, counts=None):
    """Predict relative full vectors; novel tokens are neutral, not a fallback."""
    if payload['life'] != root['life']:
        raise ValueError('layout model and root require the same frozen teacher')
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    if not legal or len(legal) != len(root['legal_actions']) or root['fallback_action'] not in legal:
        raise ValueError('legal actions and observable-only fallback required')
    feature_work, work = Counter(), Counter(layout_decisions=1, layout_legal_action_reads=len(legal))
    features = action_features_from_root(root, feature_work)
    indexed = _index(payload['vocabulary'], work)
    action_counts = {action: len(payload['action_root_ids'][action]) for action in legal}
    pair_counts = {estimation._pair_key(a, b): len(payload['pair_root_ids'][estimation._pair_key(a, b)])
                   for a, b in combinations(legal, 2)}
    connected = deepcopy(payload['connected_components'])
    component_id = {action: index for index, group in enumerate(connected) for action in group}
    work.update(layout_action_support_lookups=len(legal), layout_pair_support_lookups=len(pair_counts),
                layout_component_membership_lookups=len(legal))
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif any(action_counts[action] < MIN_ACTION_ROOTS for action in legal):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component_id[action] for action in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback, reason = None, False, 'selected'
    predicted, coverage = {}, {}
    for action in legal:
        entries, coverage[action] = _encode(features[action], indexed, work)
        vector = [sum(value*payload['coefficients'][column][component] for column, value in entries.items())
                  for component in range(3)]
        vector[0] += root['immediate_rewards'][action]
        predicted[action] = vector
        work.update(layout_prediction_coefficient_reads=3*len(entries), layout_prediction_value_reads=3*len(entries),
                    layout_prediction_component_evaluations=3, layout_immediate_reward_reads=1, layout_reward_additions=1)
    pairs = {}
    for first, second in combinations(legal, 2):
        if component_id[first] == component_id[second]:
            pairs[estimation._pair_key(first, second)] = [predicted[first][i]-predicted[second][i] for i in range(3)]
            work['layout_predicted_pair_component_subtractions'] += 3
    if selected is None:
        selected, best = legal[0], None
        for action in legal:
            vector = predicted[action]; value = vector[0]-vector[1]+vector[2]
            work['layout_utility_evaluations'] += 1
            if best is None or value > best+EPSILON:
                selected, best = action, value
    support = dict(action_root_counts=action_counts, pair_root_counts=pair_counts,
                   connected_components=connected, required_actions=legal, complete=not fallback)
    if counts is not None:
        counts.update(work); counts.update(feature_work)
    result = dict(canonical_action=selected, fallback=fallback, leaf=0, reason=reason,
        predicted_components=predicted, predicted_pairs=pairs, support=support, coverage=coverage,
        work=dict(work), feature_work=dict(feature_work))
    if 'action_map' in root:
        result['actual_action'] = root['action_map'][selected]
    return result
