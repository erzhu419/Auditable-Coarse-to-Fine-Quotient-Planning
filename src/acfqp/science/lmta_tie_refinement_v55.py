"""Refine exact two-day root ties with one additional day of information."""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
import math
from time import perf_counter

from .lmta_exact_v52 import ExactAIMSolver
from .lmta_lookahead_v53 import plan as prefix_plan


def _refine(graph, statuses, budget, remaining_days, root_actions):
    kernel = ExactAIMSolver(graph, 'AVERAGE_OPTIMAL')
    root = statuses, budget, remaining_days, 3
    values, action_values = {}, []

    def value(state, b, h, d):
        if d == 0 or h == 0:
            return 0.
        key = state, b, h, d
        if key in values:
            return values[key]
        kernel.counters['dp_states'] += 1
        available = tuple(node for node, status in enumerate(state) if status == 0)
        size = min(len(available), b, (b + h - 1) // h)
        actions = root_actions if key == root else combinations(available, size)
        best_value = -math.inf
        for selected in actions:
            kernel.counters['action_value_evaluations'] += 1
            outcomes = kernel.kernel(state, selected)
            kernel.counters['bellman_expectation_terms'] += len(outcomes)
            candidate = math.fsum(probability * (reward + value(after, b - len(selected), h - 1, d - 1))
                                  for probability, after, reward in outcomes)
            if key == root:
                action_values.append(dict(selected=list(selected), value=candidate))
            if candidate > best_value:
                best_value = candidate
        values[key] = best_value
        return best_value

    value(*root)
    return action_values, dict(kernel.counters)


def plan(graph, statuses_tuple, budget, remaining_days):
    """Keep the prefix decision unless its exact best set needs a third day."""
    statuses = tuple(statuses_tuple)
    prefix = prefix_plan(graph, statuses, budget, remaining_days, min(2, remaining_days))
    prefix_work = dict(prefix['counters'])
    refinement_work = {name: 0 for name in prefix_work if name != 'forced_choice'}
    refinement_values = []
    selected = prefix['selected']
    if remaining_days > 2 and prefix['root_action_values']:
        tied_actions = [tuple(row['selected']) for row in prefix['root_action_values']
                        if row['value'] == prefix['planned_value']]
        if len(tied_actions) > 1:
            refinement_values, refinement_work = _refine(graph, statuses, budget,
                                                        remaining_days, tied_actions)
            selected = max(refinement_values, key=lambda row: row['value'])['selected']
    combined = Counter(prefix_work)
    combined.update(refinement_work)
    combined.update(refinement_calls=int(bool(refinement_values)),
                    refined_root_actions=len(refinement_values))
    return dict(selected=list(selected), planned_value=prefix['planned_value'],
        root_action_values=prefix['root_action_values'], prefix_selected=prefix['selected'],
        refinement_action_values=refinement_values, prefix_work=prefix_work,
        refinement_work=refinement_work, counters=dict(combined))


class _ResourceLimit(Exception):
    pass


def evaluate(graph, graph_id, stratum, p, budget, horizon, method, limits):
    """Fresh full policy evaluation; limits charge both decision stages first."""
    if method != 'LOOKAHEAD_2_TIE3':
        raise ValueError('V55 evaluates only LOOKAHEAD_2_TIE3')
    started = perf_counter()
    identity = dict(graph_id=graph_id, method=method, nodes=len(graph), stratum=stratum,
                    p=p, budget=budget, horizon=horizon)
    kernel = ExactAIMSolver(graph, 'AVERAGE_OPTIMAL')
    records, values, branches = {}, {}, {}
    decision_work, prefix_work, refinement_work = Counter(), Counter(), Counter()
    last_limit_check_seconds = 0.
    initial = (0,) * len(graph), budget, horizon

    def visit(statuses, b, h):
        nonlocal last_limit_check_seconds
        if h == 0:
            return 0.
        state = statuses, b, h
        if state in values:
            return values[state]
        tick = perf_counter()
        decision = plan(graph, statuses, b, h)
        elapsed = perf_counter() - tick
        action = tuple(decision['selected'])
        work = {'planner_calls': 1, **decision['counters']}
        records[state] = dict(**identity, statuses=list(statuses), remaining_budget=b,
            remaining_days=h, selected=list(action), value=None, reach_probability=None,
            planned_value=decision['planned_value'], root_action_values=decision['root_action_values'],
            prefix_selected=decision['prefix_selected'], refinement_action_values=decision['refinement_action_values'],
            prefix_work=decision['prefix_work'], refinement_work=decision['refinement_work'],
            decision_seconds=elapsed, decision_work=work)
        decision_work.update(work)
        prefix_work.update(decision['prefix_work'])
        refinement_work.update(decision['refinement_work'])
        last_limit_check_seconds = perf_counter() - started
        if decision_work['action_value_evaluations'] >= limits['max_planner_action_values']:
            raise _ResourceLimit('max_planner_action_values')
        if len(records) >= limits['max_policy_states']:
            raise _ResourceLimit('max_policy_states')
        if last_limit_check_seconds >= limits['max_wall_seconds']:
            raise _ResourceLimit('max_wall_seconds')
        outcomes = kernel.kernel(statuses, action)
        branches[state] = outcomes
        value = math.fsum(probability * (reward + visit(after, b - len(action), h - 1))
                          for probability, after, reward in outcomes)
        values[state] = value
        records[state]['value'] = value
        return value

    status, stop_reason = 'complete', None
    try:
        root_value = visit(*initial)
    except _ResourceLimit as error:
        status, stop_reason = 'resource_limit', str(error)
        root_value = None

    occupancy_terms = 0
    expected_work = expected_seconds = expected_prefix = expected_refinement = None
    if status == 'complete':
        reach = defaultdict(float, {initial: 1.})
        for days in range(horizon, 0, -1):
            contributions = defaultdict(list)
            for state, row in records.items():
                if state[2] != days:
                    continue
                row['reach_probability'] = reach[state]
                if days > 1:
                    for probability, after, _ in branches[state]:
                        successor = after, state[1] - len(row['selected']), days - 1
                        contributions[successor].append(reach[state] * probability)
                        occupancy_terms += 1
            for successor, terms in contributions.items():
                reach[successor] = math.fsum(terms)

        def weighted(field, names):
            return {name: math.fsum(row['reach_probability'] * row[field].get(name, 0)
                                    for row in records.values()) for name in names}

        expected_work = weighted('decision_work', decision_work)
        expected_prefix = weighted('prefix_work', prefix_work)
        expected_refinement = weighted('refinement_work', refinement_work)
        expected_seconds = math.fsum(row['reach_probability'] * row['decision_seconds']
                                     for row in records.values())
    rows = [records[state] for state in sorted(records)]
    decision_seconds = math.fsum(row['decision_seconds'] for row in rows)
    evaluation_work = dict(kernel.counters)
    evaluation_work.update(new_full_policy_backups=len(values), retained_value_reads=0,
                           occupancy_probability_terms=occupancy_terms)
    total = perf_counter() - started
    case = dict(**identity, status=status, stop_reason=stop_reason,
        root_value=root_value, root_selected=records[initial]['selected'] if status == 'complete' else None,
        value_source='V55_full_policy_evaluation', control_method=None,
        wall_seconds=total, decision_seconds=decision_seconds, evaluation_seconds=total - decision_seconds,
        last_limit_check_seconds=last_limit_check_seconds,
        state_records=len(rows), decision_work=dict(decision_work), expected_decision_work=expected_work,
        prefix_work=dict(prefix_work), refinement_work=dict(refinement_work),
        expected_prefix_work=expected_prefix, expected_refinement_work=expected_refinement,
        expected_decision_seconds=expected_seconds, evaluation_work=evaluation_work)
    return case, rows
