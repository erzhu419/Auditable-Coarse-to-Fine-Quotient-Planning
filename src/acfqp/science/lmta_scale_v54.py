"""Fresh exact policy evaluation with a ledger for soft resource limits."""
from __future__ import annotations

from collections import Counter, defaultdict
import math
from time import perf_counter

from .lmta_exact_v52 import ExactAIMSolver
from .lmta_lookahead_v53 import plan


class _ResourceLimit(Exception):
    pass


def evaluate(graph, graph_id, stratum, p, budget, horizon, method, limits):
    """Evaluate a new graph; check limits after charging each full cold decision."""
    started = perf_counter()
    identity = dict(graph_id=graph_id, method=method, nodes=len(graph), stratum=stratum,
                    p=p, budget=budget, horizon=horizon)
    kernel = ExactAIMSolver(graph, 'AVERAGE_OPTIMAL')
    records, values, branches = {}, {}, {}
    decision_work = Counter()
    last_limit_check_seconds = 0.
    initial = (0,) * len(graph), budget, horizon

    def visit(statuses, b, h):
        nonlocal last_limit_check_seconds
        if h == 0:
            return 0.
        state = statuses, b, h
        if state in values:
            return values[state]
        depth = h if method == 'LOOKAHEAD_FULL' else min(int(method[-1]), h)
        tick = perf_counter()
        decision = plan(graph, statuses, b, h, depth)
        elapsed = perf_counter() - tick
        action = tuple(decision['selected'])
        work = {'planner_calls': 1, **decision['counters']}
        records[state] = dict(**identity, statuses=list(statuses), remaining_budget=b,
            remaining_days=h, selected=list(action), value=None, reach_probability=None,
            planned_value=decision['planned_value'], root_action_values=decision['root_action_values'],
            decision_seconds=elapsed, decision_work=work)
        decision_work.update(work)
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
    expected_work = expected_seconds = None
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
        expected_work = {name: math.fsum(row['reach_probability'] * row['decision_work'].get(name, 0)
                                         for row in records.values()) for name in decision_work}
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
        value_source='V54_full_policy_evaluation', control_method=None,
        wall_seconds=total, decision_seconds=decision_seconds, evaluation_seconds=total - decision_seconds,
        last_limit_check_seconds=last_limit_check_seconds,
        state_records=len(rows), decision_work=dict(decision_work), expected_decision_work=expected_work,
        expected_decision_seconds=expected_seconds, evaluation_work=evaluation_work)
    return case, rows
