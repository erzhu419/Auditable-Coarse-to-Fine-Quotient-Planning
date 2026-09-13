"""Cold analytic AIM planning with reused terminal parent counts and powers."""
from __future__ import annotations

from itertools import combinations
import math

from .lmta_exact_v52 import ExactAIMSolver


TERMINAL_COUNTERS = ('terminal_base_parent_checks', 'terminal_base_states',
    'terminal_selected_edge_checks', 'terminal_selected_increments',
    'terminal_probability_lookups', 'terminal_probability_cache_hits',
    'terminal_probability_cache_misses', 'terminal_zero_source_terms')


def plan(graph, statuses_tuple, budget, remaining_days, depth):
    """Preserve V59 values, actions and search while reusing terminal arithmetic."""
    kernel = ExactAIMSolver(graph, 'AVERAGE_OPTIMAL')
    kernel.counters.update(dict(forced_choice=0, analytic_expectation_calls=0,
                                analytic_probability_terms=0))
    kernel.counters.update(dict.fromkeys(TERMINAL_COUNTERS, 0))
    statuses = tuple(statuses_tuple)
    inactive = tuple(node for node, status in enumerate(statuses) if status == 0)
    allocation = min(len(inactive), budget,
                     (budget + remaining_days - 1) // remaining_days)
    if allocation == 0 or allocation == len(inactive):
        kernel.counters['forced_choice'] = 1
        return dict(selected=list(inactive) if allocation else [], planned_value=None,
                    root_action_values=[], counters=dict(kernel.counters))

    root_key = statuses, budget, remaining_days, min(depth, remaining_days)
    values, root_actions, probabilities = {}, [], {}

    def terminal_expectation(state, selected, base_counts):
        kernel.counters['analytic_expectation_calls'] += 1
        source_counts, seeded = base_counts.copy(), list(state)
        for node in selected:
            seeded[node] = 1
            for target in kernel.successors[node]:
                kernel.counters['terminal_selected_edge_checks'] += 1
                if state[target] == 0:
                    source_counts[target] += 1
                    kernel.counters['terminal_selected_increments'] += 1
        terms = [float(len(selected))]
        for target, status in enumerate(seeded):
            if status != 0:
                continue
            kernel.counters['analytic_probability_terms'] += 1
            sources = source_counts[target]
            if sources:
                key = kernel.indegrees[target], sources
                kernel.counters['terminal_probability_lookups'] += 1
                if key in probabilities:
                    kernel.counters['terminal_probability_cache_hits'] += 1
                    probability = probabilities[key]
                else:
                    kernel.counters['terminal_probability_cache_misses'] += 1
                    kernel.counters['target_probability_evaluations'] += 1
                    probability = 1. - (1. - 1. / kernel.indegrees[target]) ** sources
                    probabilities[key] = probability
            else:
                kernel.counters['terminal_zero_source_terms'] += 1
                probability = 0.
            terms.append(probability)
        return math.fsum(terms)

    def value(state, b, h, d):
        if d == 0 or h == 0:
            return 0.
        key = state, b, h, d
        if key in values:
            return values[key]
        kernel.counters['dp_states'] += 1
        available = tuple(node for node, status in enumerate(state) if status == 0)
        size = min(len(available), b, (b + h - 1) // h)
        if d == 1:
            kernel.counters['terminal_base_states'] += 1
            base_counts = [0] * len(state)
            for target in available:
                kernel.counters['terminal_base_parent_checks'] += len(kernel.predecessors[target])
                base_counts[target] = sum(state[source] == 1 for source in kernel.predecessors[target])
        best_value = -math.inf
        for selected in combinations(available, size):
            kernel.counters['action_value_evaluations'] += 1
            if d == 1:
                candidate = terminal_expectation(state, selected, base_counts)
            else:
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
