"""Exact finite-horizon AIM enumeration for five fixed daily policy classes."""
from __future__ import annotations

from collections import Counter
from itertools import combinations, product
import math


METHODS = ['AVERAGE_SCORE', 'AVERAGE_MYOPIC', 'AVERAGE_OPTIMAL',
           'SCORE_OPTIMAL_BUDGET', 'JOINT_OPTIMAL']


class ExactAIMSolver:
    """One graph and policy class with its own Bellman and transition caches."""

    def __init__(self, graph, method):
        if method not in METHODS:
            raise ValueError(f'Unknown exact policy: {method}')
        self.method = method
        self.n = len(graph)
        self.predecessors = [tuple(sorted(graph.predecessors(v))) for v in range(self.n)]
        self.successors = [tuple(graph.successors(v)) for v in range(self.n)]
        self.indegrees = [graph.in_degree(v) for v in range(self.n)]
        self.counters = Counter(dict(dp_states=0, action_value_evaluations=0,
            kernel_builds=0, kernel_cache_hits=0, transition_outcomes=0,
            target_probability_evaluations=0, score_node_evaluations=0,
            immediate_expectation_terms=0, bellman_expectation_terms=0))
        self._solved = {}
        self._kernels = {}

    def kernel(self, statuses, selected):
        """Return (probability, next statuses, new reward) for every outcome."""
        statuses, selected = tuple(statuses), tuple(sorted(selected))
        key = statuses, selected
        if key in self._kernels:
            self.counters['kernel_cache_hits'] += 1
            return self._kernels[key]
        self.counters['kernel_builds'] += 1
        seeded = list(statuses)
        for node in selected:
            seeded[node] = 1
        next_base = [2 if status == 1 else status for status in seeded]
        certain, uncertain = [], []
        for target, status in enumerate(seeded):
            if status != 0:
                continue
            self.counters['target_probability_evaluations'] += 1
            sources = sum(seeded[source] == 1 for source in self.predecessors[target])
            probability = (1. - (1. - 1. / self.indegrees[target]) ** sources
                           if sources else 0.)
            if probability == 1.:
                certain.append(target)
                next_base[target] = 1
            elif probability > 0.:
                uncertain.append((target, probability))
        outcomes = []
        for successes in product((False, True), repeat=len(uncertain)):
            next_status = next_base.copy()
            probability = math.prod(q if success else 1. - q
                                    for success, (_, q) in zip(successes, uncertain))
            for success, (target, _) in zip(successes, uncertain):
                if success:
                    next_status[target] = 1
            reward = float(len(selected) + len(certain) + sum(successes))
            outcomes.append((probability, tuple(next_status), reward))
        self.counters['transition_outcomes'] += len(outcomes)
        self._kernels[key] = outcomes
        return outcomes

    def _score_sequence(self, statuses, size):
        current, selected = list(statuses), []
        for _ in range(size):
            best_node, best_score = None, -math.inf
            for node, status in enumerate(current):
                if status != 0:
                    continue
                self.counters['score_node_evaluations'] += 1
                score = math.fsum(1. / self.indegrees[target]
                                  for target in self.successors[node] if current[target] == 0)
                if score > best_score:
                    best_node, best_score = node, score
            selected.append(best_node)
            current[best_node] = 1
        return selected

    def _actions(self, statuses, budget, days):
        inactive = [node for node, status in enumerate(statuses) if status == 0]
        cap = min(budget, len(inactive))
        allocation = cap if days == 1 else min(cap, (budget + days - 1) // days)
        if self.method == 'AVERAGE_SCORE':
            return [tuple(sorted(self._score_sequence(statuses, allocation)))]
        if self.method in ('AVERAGE_MYOPIC', 'AVERAGE_OPTIMAL'):
            return list(combinations(inactive, allocation))
        sizes = [cap] if days == 1 else range(cap + 1)
        if self.method == 'SCORE_OPTIMAL_BUDGET':
            sequence = self._score_sequence(statuses, cap)
            return [tuple(sorted(sequence[:size])) for size in sizes]
        return [selected for size in sizes for selected in combinations(inactive, size)]

    def _continuation(self, outcomes, budget, days):
        self.counters['bellman_expectation_terms'] += len(outcomes)
        return math.fsum(probability * (reward + self.value(next_status, budget, days))
                         for probability, next_status, reward in outcomes)

    def value(self, statuses, b, h):
        """Expected future newly activated nodes, without recounting old activity."""
        statuses = tuple(statuses)
        if h == 0:
            return 0.
        key = statuses, b, h
        if key in self._solved:
            return self._solved[key][0]
        self.counters['dp_states'] += 1
        best_value, best_selected, best_outcomes = -math.inf, None, None
        for selected in self._actions(statuses, b, h):
            self.counters['action_value_evaluations'] += 1
            outcomes = self.kernel(statuses, selected)
            if self.method == 'AVERAGE_MYOPIC':
                self.counters['immediate_expectation_terms'] += len(outcomes)
                candidate = math.fsum(probability * reward
                                      for probability, _, reward in outcomes)
            else:
                candidate = self._continuation(outcomes, b - len(selected), h - 1)
            if candidate > best_value:
                best_value, best_selected, best_outcomes = candidate, selected, outcomes
        if self.method == 'AVERAGE_MYOPIC':
            best_value = self._continuation(best_outcomes, b - len(best_selected), h - 1)
        self._solved[key] = best_value, best_selected
        return best_value

    def records(self):
        """All solved nonterminal states, including zero-budget states."""
        return [{'statuses': list(statuses), 'remaining_budget': budget,
                 'remaining_days': days, 'value': value, 'selected': list(selected)}
                for (statuses, budget, days), (value, selected)
                in sorted(self._solved.items())]
