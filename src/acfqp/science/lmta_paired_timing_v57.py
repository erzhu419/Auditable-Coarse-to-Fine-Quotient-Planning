"""Fixed-query cold planning measurements with per-block garbage collection."""
from __future__ import annotations

from collections import Counter
import gc
import math
from time import perf_counter

from .lmta_lookahead_v53 import plan as full_plan
from .lmta_analytic_terminal_v56 import plan as analytic_plan


def measure(graph, identity, queries, method, limits):
    """Measure one arm; warmup and measured blocks have identical boundaries."""
    if method == 'LOOKAHEAD_FULL':
        planner = full_plan
    elif method == 'LOOKAHEAD_FULL_ANALYTIC':
        planner = analytic_plan
    else:
        raise ValueError(f'Unknown paired timing method: {method}')

    tick = perf_counter()
    gc.collect()
    prepare_gc_seconds = perf_counter() - tick
    query_seconds, weighted_seconds, mismatches = [], [], []
    work = Counter()
    status, reason, checked_seconds = 'complete', None, 0.
    loop_started = perf_counter()
    for index, reference in enumerate(queries):
        state = tuple(reference['statuses'])
        budget, days = reference['remaining_budget'], reference['remaining_days']
        args = (graph, state, budget, days, days) if method == 'LOOKAHEAD_FULL' else (graph, state, budget, days)
        tick = perf_counter()
        result = planner(*args)
        elapsed = perf_counter() - tick
        query_seconds.append(elapsed)
        weighted_seconds.append(reference['reach_probability'] * elapsed)
        counts = dict(planner_calls=1, **result['counters'])
        work.update(counts)
        actual = dict(selected=result['selected'], planned_value=result['planned_value'],
                      decision_work=counts)
        for field, value in actual.items():
            if value != reference[field]:
                mismatches.append(dict(query_index=index, field=field,
                                       expected=reference[field], actual=value))
        del result
        checked_seconds = perf_counter() - loop_started
        observed = (work['action_value_evaluations'], len(query_seconds), checked_seconds)
        for name, value in zip(('max_planner_action_values', 'max_policy_states', 'max_wall_seconds'), observed):
            if value >= limits[name]:
                status, reason = 'resource_limit', name
                break
        if reason:
            break
    loop_seconds = perf_counter() - loop_started
    tick = perf_counter()
    gc.collect()
    cleanup_seconds = perf_counter() - tick
    decision_seconds = math.fsum(query_seconds)
    return dict(**identity, method=method, status=status, stop_reason=reason,
        source_state_records=len(queries), query_count=len(query_seconds), query_seconds=query_seconds,
        decision_work=dict(work), output_mismatches=mismatches,
        prepare_gc_seconds=prepare_gc_seconds, loop_seconds=loop_seconds,
        decision_seconds=decision_seconds, cleanup_seconds=cleanup_seconds,
        decision_total_seconds=decision_seconds + cleanup_seconds,
        bookkeeping_seconds=loop_seconds - decision_seconds,
        block_seconds=loop_seconds + cleanup_seconds,
        source_weighted_planning_seconds=math.fsum(weighted_seconds) if status == 'complete' else None,
        last_limit_check_seconds=checked_seconds)
