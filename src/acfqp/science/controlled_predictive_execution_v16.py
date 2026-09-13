"""V16 action-gap allocation with an isolated early-stop comparison."""

from collections import Counter
from dataclasses import asdict
from time import perf_counter

from .controlled_predictive_execution_v13 import (
    _HistoryEvaluator, _LocalCost, _difference, _key, _pair, _result,
)


def _distinct_path_counts(trace):
    if "action" not in trace:
        return 0.0, 0
    local = trace["rows_after"] - trace["rows_before"]
    children = [(edge["probability"], _distinct_path_counts(edge["node"]))
                for edge in trace["children"]]
    return (local + sum(p * counts[0] for p, counts in children),
            local + max((counts[1] for _, counts in children), default=0))


def evaluate_gap_execution(warm_state, provider, query_name, environment, *,
                                  mode="STOP", total_batch_cap=128):
    """Choose actions before environment lookup; clone each observed history.

    The old history integrator's local acquisition unit is one paid batch here.
    Output fields name that unit explicitly; distinct state/action rows are
    integrated separately so repeats cannot disappear from the budget.
    """
    if mode not in {"CONTINUE", "STOP"}:
        raise ValueError("gap mode must be CONTINUE or STOP")
    if total_batch_cap < warm_state.spent_batches:
        raise ValueError("total batch cap must include warm observations")
    started = perf_counter()
    state = warm_state.clone()
    initial_clone_seconds = state.clone_seconds
    initial_clone_work = _difference(state.work_counts, warm_state.work_counts)
    provider_before = Counter(provider.work_counts)
    provider_seconds_before = provider.provider_seconds

    def decide(key, current, is_root):
        cost = _LocalCost()
        if is_root:
            cost.seconds["query_initialization_clone"] += initial_clone_seconds
            cost.work.update(initial_clone_work)
        before_work = Counter(current.work_counts)
        before_provider_work = Counter(provider.work_counts)
        before_rows, before_batches = len(current.rows), current.spent_batches
        quota = (total_batch_cap - before_batches) // key[0]
        t = perf_counter()
        current.observe_state(key)
        cost.seconds["actual_state_profile"] += perf_counter() - t
        requested, observations, assessments = [], [], []
        stop_reason = "DECISION_QUOTA_EXHAUSTED"
        for _ in range(quota):
            t = perf_counter()
            assessment = current.assess_gap(key, query_name)
            cost.seconds["gap_assessment"] += perf_counter() - t
            diagnostic = asdict(assessment)
            if assessment.pair is not None:
                diagnostic["pair"] = _pair(assessment.pair)
            assessments.append(diagnostic)
            if mode == "STOP" and assessment.separated:
                stop_reason = "HEURISTIC_GAP_SEPARATED"
                break
            t = perf_counter()
            pair = current.select_row(key, query_name)
            cost.seconds["solve_and_structural_frontier"] += perf_counter() - t
            selection = "STRUCTURAL_FRONTIER" if pair is not None else "GAP_FRONTIER"
            if pair is None:
                pair = assessment.pair
            if pair is None:
                stop_reason = "NO_ELIGIBLE_CANDIDATE"
                break
            batch_index = current.batch_counts.get(pair, 0)
            kind = "FIRST_OBSERVATION" if batch_index == 0 else "REPEAT_OBSERVATION"
            t = perf_counter()
            sampled = provider.sample_batch(*pair, batch_index)
            cost.seconds["acquisition"] += perf_counter() - t
            t = perf_counter()
            current.observe_batch(*pair, sampled)
            cost.seconds["sampled_model_update_and_profiles"] += perf_counter() - t
            requested.append({"row_key": _pair(pair), "batch_index": batch_index, "kind": kind, "selection": selection})
            observations.append({"row_key": _pair(pair), "batch_index": batch_index,
                                 "outcomes": [[weight, _key(successor), reward]
                                              for weight, successor, reward in sampled]})
        t = perf_counter()
        cache = current.solve(query_name)
        cost.seconds["solve_and_structural_frontier"] += perf_counter() - t
        lower, upper = cache.lower[key], cache.upper[key]
        t = perf_counter()
        action = cache.policy[key]
        cost.seconds["action"] += perf_counter() - t
        cost.rows = current.spent_batches - before_batches
        cost.work.update(_difference(current.work_counts, before_work))
        cost.work.update({"provider_" + name: value for name, value in
                          _difference(provider.work_counts, before_provider_work).items()})
        cost.unresolved = int(upper - lower > 1e-10)
        cost.unobserved_action = int((key, action) not in current.rows)
        cost.work["execution_action_decisions"] += 1
        if current.spent_batches == total_batch_cap:
            stop_reason = "TOTAL_SAMPLE_CAP_EXHAUSTED"
        return {
            "key": _key(key), "action": action, "quota": quota,
            "batches_before": before_batches, "batches_after": current.spent_batches,
            "rows_before": before_rows, "rows_after": len(current.rows),
            "requested_batches": requested, "observed_batches": observations,
            "gap_assessments": assessments,
            "lower": lower, "upper": upper, "decision_kind": "ONLINE_GAP_" + mode,
            "acquisition_stop_reason": stop_reason,
            "unresolved": bool(cost.unresolved),
            "unobserved_action": bool(cost.unobserved_action), "fallback": False,
        }, cost

    evaluator = _HistoryEvaluator(environment, warm_state.queries[query_name], decide, fork=True)
    branch = evaluator.walk(warm_state.root, state, is_root=True)
    result = _result(branch, evaluator, warm_state.spent_batches, perf_counter() - started)
    deployment = result["deployment"]
    for name in ("initial", "expected_additional", "maximum_additional", "expected_total", "maximum_total"):
        deployment[name + "_batches"] = deployment.pop(name + "_rows")
    expected_distinct, maximum_distinct = _distinct_path_counts(result["trace"])
    deployment.update(initial_distinct_rows=len(warm_state.rows),
                      expected_additional_distinct_rows=expected_distinct,
                      maximum_additional_distinct_rows=maximum_distinct,
                      expected_total_distinct_rows=len(warm_state.rows) + expected_distinct,
                      maximum_total_distinct_rows=len(warm_state.rows) + maximum_distinct,
                      scope="Per episode: every 256-sample batch is paid, including warm and repeat batches. Warm preparation is attributed by the runner; query clone is included, counterfactual sibling clones are physical audit only.")
    result.update(mode=mode, update_mode=warm_state.update_mode, query_name=query_name,
                  total_batch_cap=total_batch_cap, samples_per_batch=256,
                  initial_query_clone_seconds=initial_clone_seconds,
                  acquisition_score_scope="Heuristic competing-action separation, not a confidence interval or optimality guarantee.")
    result["physical_audit"].update(
        provider_counts=dict(_difference(provider.work_counts, provider_before)),
        provider_seconds=provider.provider_seconds - provider_seconds_before,
        initial_query_clone_seconds=initial_clone_seconds)
    return result
