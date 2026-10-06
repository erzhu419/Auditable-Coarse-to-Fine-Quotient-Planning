"""Exact spatial n-tuple differences trained on paired terminal consequences.

The three outputs are signed differences in remaining score/2048, failure and
success under one frozen H2 continuation. The caller binds a model to one life
and query. Absolute terminal versus nonterminal values are not identified by
the retained difference targets, so terminal candidate pairs retain H2.
"""
from collections import Counter
from copy import deepcopy
from time import perf_counter
from types import MappingProxyType

import numpy as np

from .controlled_predictive_ntuple_td_v120 import symmetry_patterns
from .controlled_predictive_paired_ntuple_v130 import _delta, _same_query

SCHEMA = 'acfqp.paired_advantage.v144'
COMPONENTS = ('remaining_score_over_2048', 'failure', 'success')


class PairedAdvantage:
    def __init__(self, radix=11):
        started = perf_counter()
        self.radix, self.patterns = int(radix), symmetry_patterns()
        self._weights = {}
        self.updates, self.frozen = 0, False
        self.counts, self.setup_counts = Counter(), Counter()
        self.setup_counts.update(pattern_integer_cells=self.patterns.size,
                                 pattern_bytes=self.patterns.nbytes)
        self.setup_seconds = perf_counter()-started

    @property
    def weights(self):
        return MappingProxyType(self._weights)

    def _features(self, board):
        board = np.asarray(board, dtype=np.int32)
        if board.shape != (16,) or np.any(board < 0):
            raise ValueError('afterstates must have 16 nonnegative ranks')
        self.counts['feature_board_reads'] += 16
        if np.any(board >= self.radix):
            raise ValueError('V144 difference features require nonterminal afterstates')
        indices = np.zeros((4, 8), dtype=np.int64)
        for position in range(6):
            indices = indices*self.radix+board[self.patterns[:, :, position]]
        indices += np.arange(4, dtype=np.int64)[:, None]*self.radix**6
        self.counts.update(feature_rank_reads=192, feature_occurrences=32)
        return Counter(map(int, indices.reshape(-1)))

    def _difference(self, candidate_after, baseline_after):
        candidate, baseline = self._features(candidate_after), self._features(baseline_after)
        addresses = candidate.keys() | baseline.keys()
        difference = {index: candidate[index]-baseline[index] for index in sorted(addresses)
                      if candidate[index] != baseline[index]}
        self.counts.update(pair_distinct_addresses=len(addresses),
            pair_nonzero_difference_addresses=len(difference),
            pair_signed_difference_occurrences=sum(abs(value) for value in difference.values()))
        return difference

    def _predict(self, difference):
        value = [0., 0., 0.]
        for index, multiplicity in difference.items():
            weight = self._weights.get(index, (0., 0., 0.))
            for component in range(3):
                value[component] += multiplicity*weight[component]
        self.counts.update(pair_predictions=1, weight_address_lookups=len(difference),
                           component_weight_reads=3*len(difference))
        return value

    def predict(self, candidate_after, baseline_after):
        return self._predict(self._difference(candidate_after, baseline_after))

    def update(self, candidate_after, baseline_after, target_tail_difference, alpha=.1):
        if self.frozen:
            raise RuntimeError('frozen advantage weights cannot be updated')
        target = [float(value) for value in target_tail_difference]
        if len(target) != 3:
            raise ValueError('a paired tail target has three components')
        before = self.counts.copy()
        difference = self._difference(candidate_after, baseline_after)
        prediction = self._predict(difference)
        error = [actual-estimated for actual, estimated in zip(target, prediction)]
        denominator = sum(value*value for value in difference.values())
        self.counts['update_calls'] += 1
        if denominator:
            for index, multiplicity in difference.items():
                prior = self._weights.get(index, (0., 0., 0.))
                updated = tuple(prior[k]+float(alpha)*multiplicity*error[k]/denominator
                                for k in range(3))
                if any(updated):
                    if index not in self._weights:
                        self.counts['allocated_weight_addresses'] += 1
                    self._weights[index] = updated
                elif index in self._weights:
                    del self._weights[index]
            self.updates += 1
            self.counts.update(pair_updates=1, weight_address_updates=len(difference),
                               component_weight_updates=3*len(difference))
        else:
            self.counts['unidentifiable_pairs'] += 1
        return dict(prediction=prediction, error=error, denominator=denominator,
                    applied=bool(denominator), work=_delta(self.counts, before))

    def freeze(self):
        self.frozen = True

    def state(self):
        return dict(radix=self.radix, updates=self.updates, frozen=self.frozen,
                    weights=[[index, *self._weights[index]] for index in sorted(self._weights)])

    def to_payload(self):
        self.counts.update(checkpoint_saves=1, checkpoint_saved_addresses=len(self._weights),
                           checkpoint_saved_parameters=3*len(self._weights))
        return dict(schema=SCHEMA, components=list(COMPONENTS), **self.state(),
            counts=dict(self.counts), setup_counts=dict(self.setup_counts),
            setup_seconds=self.setup_seconds,
            storage=dict(weight_addresses=len(self._weights), weight_parameters=3*len(self._weights),
                         numeric_weight_bytes=24*len(self._weights),
                         numeric_address_bytes=8*len(self._weights)))

    @classmethod
    def from_payload(cls, payload):
        if payload['schema'] != SCHEMA:
            raise ValueError('unsupported paired advantage schema')
        model = cls(payload['radix'])
        model._weights = {int(row[0]): tuple(map(float, row[1:])) for row in payload['weights']}
        model.updates, model.frozen = int(payload['updates']), bool(payload['frozen'])
        model.setup_counts.update(loaded_weight_addresses=len(model._weights),
            loaded_weight_parameters=3*len(model._weights), loaded_numeric_weight_bytes=24*len(model._weights))
        return model


class AdvantagePlanner:
    """Compare only the unchanged H2 and H1_CONT candidates, charging both."""
    def __init__(self, teacher, candidate, model, query):
        if not model.frozen:
            raise ValueError('the V144 advantage model must be frozen before control')
        self.teacher, self.candidate, self.model = teacher, candidate, model
        self.target_query, self.radix = dict(query), model.radix
        self.counts, self.setup_counts = Counter(), Counter()
        self.setup_seconds = 0.

    def choose(self, board, query=None, *, simulation_seed=0, previous_action='DOWN'):
        if query is not None and not _same_query(query, self.target_query):
            raise ValueError('the frozen selector target query is fixed')
        before = self.counts.copy()
        self.counts['choose_calls'] += 1
        initial = self.teacher.counts.copy()
        baseline = self.teacher.choose(board, self.target_query)
        self.counts.update({f'baseline_{key}': value for key, value in
                           _delta(self.teacher.counts, initial).items()})
        initial = self.candidate.counts.copy()
        candidate = self.candidate.choose(board, self.target_query,
            simulation_seed=simulation_seed, previous_action=previous_action)
        self.counts.update({f'candidate_{key}': value for key, value in
                           _delta(self.candidate.counts, initial).items()})
        same = candidate['action'] == baseline['action']
        self.counts['candidate_disagreements'] += int(not same)
        terminal = max(candidate['afterstate']) >= self.radix or max(baseline['afterstate']) >= self.radix
        predicted = [0., 0., 0.]
        immediate = (candidate['score']-baseline['score'])/2048.
        advantage, selected = 0., False
        if terminal:
            self.counts['terminal_pair_bypasses'] += 1
        elif same:
            self.counts['same_action_bypasses'] += 1
        else:
            initial = self.model.counts.copy()
            predicted = self.model.predict(candidate['afterstate'], baseline['afterstate'])
            self.counts.update({f'learner_{key}': value for key, value in
                               _delta(self.model.counts, initial).items()})
            q = self.target_query
            advantage = (q.get('reward_weight', 1.)*(immediate+predicted[0])
                         - q.get('failure_penalty', 0.)*predicted[1]
                         + q.get('goal_bonus', 0.)*predicted[2])
            selected = advantage > 0.
            self.counts['selected_h1'] += int(selected)
        value = float(baseline['value'])+(advantage if selected else 0.)
        chosen = candidate if selected else baseline
        values = {}
        if baseline['action'] is not None:
            values[baseline['action']] = dict(afterstate=list(baseline['afterstate']),
                score=baseline['score'], value=float(baseline['value']),
                tail_value=float(baseline['value'])-baseline['score']/2048.)
        if not same and not terminal:
            estimate = float(baseline['value'])+advantage
            values[candidate['action']] = dict(afterstate=list(candidate['afterstate']),
                score=candidate['score'], value=estimate,
                tail_value=estimate-candidate['score']/2048.)
        selection = dict(baseline_action=baseline['action'], candidate_action=candidate['action'],
            baseline_score=baseline['score'], candidate_score=candidate['score'],
            baseline_choice=deepcopy(baseline), candidate_choice=deepcopy(candidate),
            predicted_tail_difference=predicted, immediate_difference=immediate,
            estimated_advantage=advantage, selected_h1=selected, same_action=same,
            terminal_pair_bypass=terminal)
        return dict(action=chosen['action'], afterstate=list(chosen['afterstate']),
            score=chosen['score'], status=chosen['status'], value=value,
            tail_value=value-chosen['score']/2048., action_values=values,
            value_kind='baseline_h2_proxy_plus_learned_advantage', selection=selection,
            counts=_delta(self.counts, before))
