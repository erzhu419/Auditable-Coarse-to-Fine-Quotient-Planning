"""Cold finite-depth AIM planning with allocation based on the real horizon."""
from __future__ import annotations

from itertools import combinations
import math

from .lmta_exact_v52 import ExactAIMSolver


def plan(graph, statuses_tuple, budget, remaining_days, depth):
    """Choose one day's subset; all caches belong only to this invocation."""
    kernel = ExactAIMSolver(graph, 'AVERAGE_OPTIMAL')
    kernel.counters['forced_choice'] = 0
    statuses = tuple(statuses_tuple)
    inactive = tuple(node for node, status in enumerate(statuses) if status == 0)
    allocation = min(len(inactive), budget,
                     (budget + remaining_days - 1) // remaining_days)
    if allocation == 0 or allocation == len(inactive):
        kernel.counters['forced_choice'] = 1
        return dict(selected=list(inactive) if allocation else [], planned_value=None,
                    root_action_values=[], counters=dict(kernel.counters))

    root_key = statuses, budget, remaining_days, min(depth, remaining_days)
    values, root_actions = {}, []

    def value(state, b, h, d):
        if d == 0 or h == 0:
            return 0.
        key = state, b, h, d
        if key in values:
            return values[key]
        kernel.counters['dp_states'] += 1
        available = tuple(node for node, status in enumerate(state) if status == 0)
        size = min(len(available), b, (b + h - 1) // h)
        best_value = -math.inf
        for selected in combinations(available, size):
            kernel.counters['action_value_evaluations'] += 1
            outcomes = kernel.kernel(state, selected)
            kernel.counters['bellman_expectation_terms'] += len(outcomes)
            candidate = math.fsum(probability * (reward + value(next_state, b - size, h - 1, d - 1))
                                  for probability, next_state, reward in outcomes)
            if key == root_key:
                root_actions.append(dict(selected=list(selected), value=candidate))
            if candidate > best_value:
                best_value = candidate
        values[key] = best_value
        return best_value

    planned_value = value(*root_key)
    selected = max(root_actions, key=lambda row: row['value'])['selected']
    return dict(selected=selected, planned_value=planned_value,
                root_action_values=root_actions, counters=dict(kernel.counters))
