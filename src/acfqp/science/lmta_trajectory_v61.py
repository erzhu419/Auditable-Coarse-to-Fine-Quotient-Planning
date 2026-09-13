"""Paired synchronous trajectories under frozen cold analytic AIM decisions."""
from __future__ import annotations

from collections import Counter
import math
import random
from time import perf_counter

from .lmta_analytic_short_v59 import plan


ENVIRONMENT_KEYS = ('environment_calls', 'rng_draws', 'eligible_edge_attempts',
                    'successful_edge_attempts', 'seeded_nodes', 'activated_targets')
DEPTHS = {'LOOKAHEAD_1_ANALYTIC': 1, 'LOOKAHEAD_2_ANALYTIC': 2}


def _propagate(statuses, selected, edges, indegrees, rng):
    """Draw every sorted edge, then propagate only from today's active sources."""
    seeded = list(statuses)
    for node in selected:
        seeded[node] = 1
    uniforms = [rng.random() for _ in edges]
    activated, eligible, successful = set(), 0, 0
    for (source, target), uniform in zip(edges, uniforms):
        if seeded[source] == 1 and seeded[target] == 0:
            eligible += 1
            if uniform < 1. / indegrees[target]:
                successful += 1
                activated.add(target)
    after = [2 if status == 1 else status for status in seeded]
    for node in activated:
        after[node] = 1
    work = dict(environment_calls=1, rng_draws=len(edges),
                eligible_edge_attempts=eligible, successful_edge_attempts=successful,
                seeded_nodes=len(selected), activated_targets=len(activated))
    return after, len(selected) + len(activated), work


def run_block(graph, graph_id, method, replicates, budget, horizon, limits):
    """Run a fixed replicate prefix; a reached soft limit retains the paid decision."""
    started = perf_counter()
    depth = DEPTHS[method]
    edges = sorted(graph.edges())
    indegrees = dict(graph.in_degree())
    rows, decision_work = [], Counter()
    environment_work = Counter(dict.fromkeys(ENVIRONMENT_KEYS, 0))
    decision_times, environment_times = [], []
    status, stop_reason, last_limit_check_seconds = 'complete', None, 0.
    for replicate in range(replicates):
        seed = 61000000 + graph_id * 1000 + replicate
        rng = random.Random(seed)
        statuses, remaining_budget = [0] * len(graph), budget
        trajectory = dict(graph_id=graph_id, method=method, replicate=replicate,
                          seed=seed, status='complete', stop_reason=None,
                          **{'return': None}, decisions=[])
        rows.append(trajectory)
        rewards = []
        for remaining_days in range(horizon, 0, -1):
            tick = perf_counter()
            decision = plan(graph, tuple(statuses), remaining_budget, remaining_days, depth)
            elapsed = perf_counter() - tick
            work = {'planner_calls': 1, **decision['counters']}
            row = dict(statuses=list(statuses), remaining_budget=remaining_budget,
                       remaining_days=remaining_days, selected=list(decision['selected']),
                       planned_value=decision['planned_value'],
                       root_action_values=decision['root_action_values'],
                       decision_work=work, decision_seconds=elapsed,
                       next_statuses=None, reward=None,
                       environment_work=dict.fromkeys(ENVIRONMENT_KEYS, 0),
                       environment_seconds=0.)
            trajectory['decisions'].append(row)
            decision_work.update(work)
            decision_times.append(elapsed)
            last_limit_check_seconds = perf_counter() - started
            if decision_work['action_value_evaluations'] >= limits['max_planner_action_values']:
                stop_reason = 'max_planner_action_values'
            elif decision_work['planner_calls'] >= limits['max_decisions']:
                stop_reason = 'max_decisions'
            elif last_limit_check_seconds >= limits['max_wall_seconds']:
                stop_reason = 'max_wall_seconds'
            if stop_reason:
                status = trajectory['status'] = 'resource_limit'
                trajectory['stop_reason'] = stop_reason
                break
            tick = perf_counter()
            after, reward, env_work = _propagate(statuses, row['selected'], edges, indegrees, rng)
            env_elapsed = perf_counter() - tick
            row.update(next_statuses=after, reward=reward, environment_work=env_work,
                       environment_seconds=env_elapsed)
            environment_work.update(env_work)
            environment_times.append(env_elapsed)
            rewards.append(reward)
            statuses, remaining_budget = after, remaining_budget - len(row['selected'])
        if status != 'complete':
            break
        trajectory['return'] = sum(rewards)
    case = dict(graph_id=graph_id, method=method, nodes=len(graph), budget=budget, horizon=horizon,
                status=status, stop_reason=stop_reason, requested_replicates=replicates,
                completed_replicates=sum(row['status'] == 'complete' for row in rows),
                trajectory_records=len(rows), decision_records=decision_work['planner_calls'],
                total_return=sum(row['return'] for row in rows if row['return'] is not None),
                decision_work=dict(decision_work), environment_work=dict(environment_work),
                decision_seconds=math.fsum(decision_times),
                environment_seconds=math.fsum(environment_times),
                last_limit_check_seconds=last_limit_check_seconds,
                wall_seconds=perf_counter() - started)
    return case, rows
