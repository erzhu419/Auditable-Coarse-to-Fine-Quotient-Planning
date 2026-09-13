"""V21 fixed-batch local allocation and separate frozen-snapshot evaluation."""

from collections import Counter
from dataclasses import asdict
from itertools import combinations
import math
from time import perf_counter

from .controlled_predictive_execution_v13 import _key, _pair
from .controlled_predictive_frontier_v24 import FrontierGapPlannerState
from .controlled_predictive_frontier_variance_v26 import FrontierVarianceGapPlannerState
from .controlled_predictive_score_cache_v18 import CachedGapPlannerState
from .controlled_predictive_variance_v20 import VarianceGapPlannerState


TOLERANCE = 1e-10
ARMS = {"CACHED": CachedGapPlannerState, "VARIANCE": VarianceGapPlannerState,
        "FRONTIER": FrontierGapPlannerState, "FRONTIER_VARIANCE": FrontierVarianceGapPlannerState}


def _delta(after, before):
    return {key: value - before.get(key, 0) for key, value in after.items()
            if value != before.get(key, 0)}


def run_local_allocation(snapshot, arm, provider, query_name, target_key, requested_batches):
    """Use a fixed original-node budget at one key; never consult an environment."""
    if requested_batches < 0 or snapshot.spent_batches + requested_batches > 128:
        raise ValueError("The original remaining decision budget must fit the 128-batch cap")
    if target_key not in snapshot.profiles or snapshot.profiles[target_key].status != "ACTIVE":
        raise ValueError("Local allocation requires the retained ACTIVE target")
    started = perf_counter()
    seconds = Counter()
    provider_before = Counter(provider.work_counts)
    provider_seconds_before = provider.provider_seconds
    tick = perf_counter()
    current = snapshot.clone()
    current.__class__ = ARMS[arm]
    current.work_counts["local_allocation_arm_initializations"] += 1
    current.clone_seconds = perf_counter() - tick
    current.engine_seconds = snapshot.engine_seconds + current.clone_seconds
    seconds["arm_clone_and_class_switch"] += current.clone_seconds
    initial_batches = current.spent_batches
    tick = perf_counter()
    current.observe_state(target_key)
    seconds["actual_state_profile"] += perf_counter() - tick
    requested, observations, assessments = [], [], []
    first_original_stop = None
    stop_reason = "FIXED_BATCH_BUDGET_COMPLETE"
    for index in range(requested_batches):
        tick = perf_counter()
        assessment = current.assess_gap(target_key, query_name)
        seconds["gap_assessment"] += perf_counter() - tick
        diagnostic = asdict(assessment)
        if assessment.pair is not None:
            diagnostic["pair"] = _pair(assessment.pair)
        assessments.append(diagnostic)
        if assessment.separated and first_original_stop is None:
            first_original_stop = index
        tick = perf_counter()
        pair = current.select_row(target_key, query_name)
        seconds["structural_selection"] += perf_counter() - tick
        kind = "FIRST_OBSERVATION"
        if pair is None:
            tick = perf_counter()
            pair = current.select_resample(target_key, query_name, mode="BALANCED")
            seconds["resampling_selection"] += perf_counter() - tick
            kind = "REPEAT_OBSERVATION"
        if pair is None:
            stop_reason = "NO_ELIGIBLE_CANDIDATE"
            break
        batch_index = current.batch_counts.get(pair, 0)
        tick = perf_counter()
        sampled = provider.sample_batch(*pair, batch_index)
        seconds["acquisition"] += perf_counter() - tick
        tick = perf_counter()
        current.observe_batch(*pair, sampled)
        seconds["model_update"] += perf_counter() - tick
        requested.append({"row_key": _pair(pair), "batch_index": batch_index, "kind": kind})
        observations.append({"row_key": _pair(pair), "batch_index": batch_index,
                             "outcomes": [[weight, _key(successor), reward]
                                          for weight, successor, reward in sampled]})
    tick = perf_counter()
    cache = current.solve(query_name)
    seconds["endpoint_solve"] += perf_counter() - tick
    action = cache.policy[target_key]
    lower, upper = cache.lower[target_key], cache.upper[target_key]
    completed = current.spent_batches - initial_batches
    report = {
        "arm": arm, "query_name": query_name, "target_key": _key(target_key),
        "requested_batch_count": requested_batches, "completed_batches": completed,
        "completed_fixed_budget": completed == requested_batches,
        "initial_batches": initial_batches, "final_batches": current.spent_batches,
        "actual_draws": 256 * completed, "stop_reason": stop_reason,
        "first_original_stop_index": first_original_stop,
        "requested_batches": requested, "observed_batches": observations,
        "gap_assessments": assessments, "final_action": action,
        "lower": lower, "upper": upper, "unresolved": upper - lower > TOLERANCE,
        "selected_action_observed": (target_key, action) in current.rows,
        "provider_counts": _delta(provider.work_counts, provider_before),
        "accounting": {"seconds_by_stage": dict(seconds),
                       "whole_run_seconds": perf_counter() - started,
                       "work_counts": _delta(current.work_counts, snapshot.work_counts),
                       "provider_seconds": provider.provider_seconds - provider_seconds_before,
                       "scope": "Whole-run time includes the listed stages; provider time is contained in acquisition. Do not add nested times twice."},
        "scope": "Fixed-key local allocation only. first_original_stop_index records only the first gap separation, which is ignored for all arms; no eligible acquisition or repeat candidate remains a stopping condition. All original accumulated counts and batch indices are retained. No environment execution or truth access.",
    }
    return current, report


def _prepare_evaluation(state, query_name, oracle):
    context = {"started": perf_counter(), "oracle_work_before": Counter(oracle.work_counts),
               "oracle_seconds_before": Counter(oracle.seconds_by_stage)}
    tick = perf_counter()
    frozen = state.clone()
    cache = frozen.solve(query_name)
    context["clone_solve_seconds"] = perf_counter() - tick
    truth = oracle.solution(frozen.queries[query_name])
    context["arithmetic_started"] = perf_counter()
    return frozen, cache, truth, context


def _evaluation_accounting(state, frozen, oracle, context):
    return {"snapshot_clone_and_solve_seconds": context["clone_solve_seconds"],
            "snapshot_clone_and_solve_work": _delta(frozen.work_counts, state.work_counts),
            "oracle_work": _delta(oracle.work_counts, context["oracle_work_before"]),
            "oracle_seconds_by_stage": _delta(oracle.seconds_by_stage, context["oracle_seconds_before"]),
            "evaluation_arithmetic_seconds": perf_counter() - context["arithmetic_started"],
            "whole_evaluation_seconds": perf_counter() - context["started"],
            "scope": "Whole evaluation includes diagnostic clone/solve, oracle query work and arithmetic; nested times are not additive."}


def _choice(frozen, cache, truth, key, oracle):
    if key not in frozen.profiles or frozen.profiles[key].status != "ACTIVE":
        raise ValueError("Evaluation requires a retained ACTIVE state; no policy is extended")
    action = cache.policy[key]
    values = {candidate: truth.q_values[key, candidate] for candidate in frozen.profiles[key].legal_actions}
    oracle.work_counts["diagnostic_exact_q_lookups"] += len(values)
    best = truth.values[key]
    oracle.work_counts["diagnostic_exact_value_lookups"] += 1
    optimal = sorted(candidate for candidate, value in values.items() if best - value <= TOLERANCE)
    return {"key": _key(key), "selected_action": action,
            "selected_action_observed": (key, action) in frozen.rows,
            "lower": cache.lower[key], "upper": cache.upper[key],
            "interval_closed": cache.upper[key] - cache.lower[key] <= TOLERANCE,
            "local_true_optimal_actions": optimal, "true_optimal_action_count": len(optimal),
            "selected_action_in_true_optimal_set": action in optimal,
            "local_regret": best - values[action], "selected_action_q_star": values[action],
            "v_star": best}


def evaluate_local_snapshot(state, query_name, target_key, exact_oracle):
    """Decompose observed target rows at any horizon using exact optimal continuation."""
    frozen, cache, truth, context = _prepare_evaluation(state, query_name, exact_oracle)
    choice = _choice(frozen, cache, truth, target_key, exact_oracle)
    query = frozen.queries[query_name]
    actions = {}
    residuals = []
    for action in sorted(frozen.profiles[target_key].legal_actions):
        pair = target_key, action
        q_star = truth.q_values[pair]
        exact_oracle.work_counts["diagnostic_exact_q_lookups"] += 1
        record = {"observed": pair in frozen.rows, "lower": cache.q_lower[pair],
                  "upper": cache.q_upper[pair], "q_star": q_star,
                  "q_hat": None, "q_hat_exact_continuation": None,
                  "A_transition_error": None, "D_continuation_error": None,
                  "total_error": None, "identity_residual": None,
                  "batch_count": frozen.batch_counts.get(pair, 0), "children": []}
        if pair in frozen.rows:
            children = []
            for probability, successor, reward in frozen.rows[pair]:
                if successor not in frozen.profiles or successor not in truth.values:
                    raise ValueError("An empirical successor lacks its retained profile or ground value")
                v_hat, v_star = cache.lower[successor], truth.values[successor]
                exact_oracle.work_counts["diagnostic_exact_value_lookups"] += 1
                children.append({"key": _key(successor), "empirical_probability": probability,
                                 "immediate_reward": reward, "status": frozen.profiles[successor].status,
                                 "empirical_lower": v_hat, "empirical_upper": cache.upper[successor],
                                 "interval_closed": cache.upper[successor] - v_hat <= TOLERANCE,
                                 "v_star": v_star, "weighted_D": probability * (v_hat - v_star)})
            q_hat = cache.q_lower[pair]
            q_hat_exact = math.fsum(child["empirical_probability"] * (
                query.reward_weight * child["immediate_reward"] + child["v_star"]) for child in children)
            transition = q_hat_exact - q_star
            continuation = math.fsum(child["weighted_D"] for child in children)
            total = q_hat - q_star
            residual = total - math.fsum((transition, continuation))
            residuals.append(abs(residual))
            record.update(q_hat=q_hat, q_hat_exact_continuation=q_hat_exact,
                          A_transition_error=transition, D_continuation_error=continuation,
                          total_error=total, identity_residual=residual, children=children)
        actions[action] = record
    margins = []
    for left, right in combinations(actions, 2):
        a, b = actions[left], actions[right]
        both = a["observed"] and b["observed"]
        row = {"actions": [left, right], "observed_both": both,
               "lower_difference_bound": a["lower"] - b["upper"],
               "upper_difference_bound": a["upper"] - b["lower"],
               "q_star_difference": a["q_star"] - b["q_star"]}
        for name in ("q_hat", "A_transition_error", "D_continuation_error", "total_error"):
            row[name + "_difference"] = a[name] - b[name] if both else None
        row["identity_residual"] = (row["q_hat_difference"] - row["q_star_difference"] - math.fsum((
            row["A_transition_error_difference"], row["D_continuation_error_difference"]))) if both else None
        if both:
            residuals.append(abs(row["identity_residual"]))
        margins.append(row)
    maximum = max(residuals, default=0.)
    return {"target_key": _key(target_key), "query_name": query_name, **choice,
            "actions": actions, "pair_margins": margins,
            "decomposed_action_count": sum(row["observed"] for row in actions.values()),
            "identities_pass": maximum <= TOLERANCE, "maximum_absolute_identity_residual": maximum,
            "accounting": _evaluation_accounting(state, frozen, exact_oracle, context),
            "scope": "Observed actions satisfy Qhat-Qstar=A+D using the frozen empirical lower continuation and exact optimal continuation. Unobserved actions retain structural bounds only. Local action regret uses optimal continuation and is not the value of a frozen or online full policy; no multi-step Vpi is defined."}


def evaluate_panel(state, query_name, panel, exact_oracle):
    """Evaluate exactly the predeclared states with one clone, solve and exact DP lookup."""
    frozen, cache, truth, context = _prepare_evaluation(state, query_name, exact_oracle)
    rows = [_choice(frozen, cache, truth, key, exact_oracle) for key in panel]
    return {"query_name": query_name, "states": rows, "state_count": len(rows),
            "selected_optimal_count": sum(row["selected_action_in_true_optimal_set"] for row in rows),
            "positive_regret_count": sum(row["local_regret"] > TOLERANCE for row in rows),
            "sum_local_regret": math.fsum(row["local_regret"] for row in rows),
            "maximum_local_regret": max((row["local_regret"] for row in rows), default=0.),
            "accounting": _evaluation_accounting(state, frozen, exact_oracle, context),
            "scope": "Only the panel frozen from the common snapshot is evaluated; new endpoint states do not expand it. State-wise regrets use true optimal continuation, not a full-policy value. Panel states are dependent and are not independent statistical samples."}
