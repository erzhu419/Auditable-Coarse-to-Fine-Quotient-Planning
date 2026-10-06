"""Fixed local/strategy features and sparse three-component residual LMS."""
from collections import Counter
from types import MappingProxyType

from .controlled_predictive_policy_modules_v151 import QUERIES

SCHEMA = 'acfqp.module_residual_lms.v156'
CELL_CLASSES = tuple(int(r in (0, 3))+int(c in (0, 3)) for r in range(4) for c in range(4))
EDGES = tuple((4*r+c, 4*r+c+1) for r in range(4) for c in range(3)) + tuple(
    (4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4))
SEMANTIC_FEATURES = ('bias', 'empty_fraction', 'legal_action_fraction', 'maximum_rank_fraction',
    'maximum_in_corner', 'equal_nonzero_adjacent_fraction', 'policy_action_disagreement',
    'own_critic_other_action_gap', 'own_critic_top_two_gap', 'own_critic_best_value',
    'selected_exit_empty_difference', 'selected_exit_score_difference')


def _board(board):
    board = tuple(board)
    if len(board) != 16 or any(rank < 0 or rank >= 11 for rank in board):
        raise ValueError('features require a nonterminal 16-cell rank board')
    return board


def build_local_features(board):
    """Exactly the V151 root feature multiset, including bias address -1."""
    board = _board(board)
    features = Counter({-1: 1})
    for index, cell_class in enumerate(CELL_CLASSES):
        features[cell_class*11+board[index]] += 1
    for first, second in EDGES:
        left, right = CELL_CLASSES[first]*11+board[first], CELL_CLASSES[second]*11+board[second]
        features[33+min(left, right)*33+max(left, right)] += 1
    work = dict(feature_board_reads=16, feature_rank_reads=64, feature_occurrences=41,
                unary_feature_occurrences=16, pair_feature_occurrences=24, bias_feature_occurrences=1)
    return dict(sorted(features.items())), work


def build_semantic_features(board, choices, target_query):
    """Use only the target critic; the other teacher supplies its selected action."""
    board = _board(board)
    own = choices[target_query]
    other_query = 'risk8' if target_query == 'risk1' else 'risk1'
    own_action, other_action = own['action'], choices[other_query]['action']
    action_values = own['action_values']
    values = {action: float(data['value']) for action, data in action_values.items()}
    best = sorted(values.values(), reverse=True)
    own_exit, other_exit = action_values[own_action], action_values[other_action]
    empty = sum(rank == 0 for rank in board)
    maximum = max(board)
    in_corner = int(sum(board[cell] == maximum for cell in (0, 3, 12, 15)) > 0)
    equal_pairs = 0
    for first, second in EDGES:
        left, right = board[first], board[second]
        equal_pairs += int(left != 0 and left == right)
    query = QUERIES[target_query]
    scale = 1.+query['failure_penalty']+query['goal_bonus']
    own_score, other_score = own_exit['score'], other_exit['score']
    dense = [1., empty/16., len(action_values)/4., maximum/11., float(in_corner), equal_pairs/24.,
        float(own_action != other_action), (values[other_action]-values[own_action])/scale,
        (best[0]-best[1])/scale if len(best) > 1 else 0., best[0]/scale,
        (sum(rank == 0 for rank in other_exit['afterstate'])-sum(rank == 0 for rank in own_exit['afterstate']))/16.,
        (other_score-own_score)/(2048.+abs(other_score)+abs(own_score))]
    features = {address: value for address, value in enumerate(dense) if value != 0.}
    work = dict(feature_board_reads=48, feature_rank_reads=116, feature_occurrences=12,
                teacher_action_value_reads=len(action_values), feature_nonzero_addresses=len(features))
    return features, work


class ResidualLMS:
    """Zero-initialized sparse residual model; OLD predictions stay outside it."""
    def __init__(self, feature_kind):
        if feature_kind not in ('LOCAL', 'SEMANTIC'):
            raise ValueError('feature_kind must be LOCAL or SEMANTIC')
        self.feature_kind = feature_kind
        self._weights = {}
        self.updates, self.frozen, self.counts = 0, False, Counter()

    @property
    def weights(self):
        return MappingProxyType(self._weights)

    def _predict(self, features):
        prediction = [0., 0., 0.]
        for address in sorted(features):
            value = features[address]
            weight = self._weights.get(address, (0., 0., 0.))
            for component in range(3):
                prediction[component] += value*weight[component]
        n = len(features)
        self.counts.update(predictions=1, feature_entries_read=n,
                           weight_address_reads=n, component_weight_reads=3*n)
        return prediction

    def predict(self, features):
        return self._predict(features)

    def update(self, features, target, alpha=.1):
        if self.frozen:
            raise RuntimeError('frozen residual weights cannot be updated')
        target = list(map(float, target))
        if len(target) != 3:
            raise ValueError('a residual target has three components')
        before = dict(self.counts)
        predicted = self._predict(features)
        error = [target[k]-predicted[k] for k in range(3)]
        denominator = sum(features[address]**2 for address in sorted(features))
        for address in sorted(features):
            value = features[address]
            prior = self._weights.get(address, (0., 0., 0.))
            updated = tuple(prior[k]+float(alpha)*value*error[k]/denominator for k in range(3))
            if any(updated):
                if address not in self._weights:
                    self.counts['allocated_weight_addresses'] += 1
                self._weights[address] = updated
            elif address in self._weights:
                del self._weights[address]
        n = len(features)
        self.counts.update(update_calls=1, feature_entries_read=2*n,
            weight_address_reads=n, component_weight_reads=3*n,
            weight_address_updates=n, component_weight_updates=3*n)
        self.updates += 1
        return dict(prediction=predicted, error=error, denominator=denominator,
                    work={key: value-before.get(key, 0) for key, value in self.counts.items()
                          if value != before.get(key, 0)})

    def freeze(self):
        self.frozen = True

    def state(self):
        return dict(feature_kind=self.feature_kind, updates=self.updates, frozen=self.frozen,
                    weights=[[address, *self._weights[address]] for address in sorted(self._weights)])

    def to_payload(self):
        n = len(self._weights)
        self.counts.update(checkpoint_saves=1, checkpoint_saved_addresses=n, checkpoint_saved_parameters=3*n)
        return dict(schema=SCHEMA, **self.state(), counts=dict(self.counts), storage=dict(
            weight_addresses=n, weight_parameters=3*n, numeric_weight_bytes=24*n, numeric_address_bytes=8*n))

    @classmethod
    def from_payload(cls, payload):
        if payload['schema'] != SCHEMA:
            raise ValueError('unsupported residual LMS schema')
        model = cls(payload['feature_kind'])
        model._weights = {int(row[0]): tuple(map(float, row[1:])) for row in payload['weights']}
        model.updates, model.frozen = int(payload['updates']), bool(payload['frozen'])
        n = len(model._weights)
        model.counts.update(checkpoint_loads=1, checkpoint_loaded_addresses=n, checkpoint_loaded_parameters=3*n)
        return model
