"""Pilot-only allocation from empirical action-gap uncertainty.

The uncertainty is a fixed-policy, first-order sampling heuristic. In particular,
zero observed variance cannot establish that an outcome is impossible. The input
is only a sampled finite model, its row counts, and the declared query bank;
ground transitions and later observations have no role in allocation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
import time

from acfqp.science.controlled_predictive_quotient_v1 import (
    FiniteModel,
    Query,
    _actions,
    _terminal_value,
)


Row = tuple[int, str]
TIE_TOLERANCE = 1e-10
AMBIGUITY_SE_MULTIPLIER = 2.0


@dataclass(frozen=True)
class AllocationResult:
    allocations: dict[int, dict[Row, int]]
    diagnostics: dict
    # Kept separate so a runner can summarize all pairs without serializing them.
    pair_diagnostics: tuple[dict, ...]


def signed_policy_gap_influences(
    model: FiniteModel,
    policy: dict[int, str],
    state: int,
    best_action: str,
    competitor_action: str,
) -> tuple[dict[Row, float], dict[str, int]]:
    """Row-occupancy difference: competitor first minus best first.

    Both branches follow the same nominal policy after their first action.
    Incoming signed masses are combined before propagating a shared future row,
    so common continuation uncertainty cancels rather than being counted twice.
    """
    if best_action == competitor_action:
        raise ValueError("the action-gap branches must have different first actions")
    coefficients: dict[Row, float] = {
        (state, competitor_action): 1.0, (state, best_action): -1.0,
    }
    counts = {"calls": 1, "state_action_rows": 0, "outcomes": 0,
              "signed_states_combined": 0, "cancelled_states": 0}
    pending: dict[int, list[float]] = defaultdict(list)

    def propagate(key: Row, coefficient: float) -> None:
        row = model.rows[key]
        counts["state_action_rows"] += 1
        counts["outcomes"] += len(row)
        for outcome in row:
            if outcome.probability and model.terminal[outcome.next_state] == "ACTIVE":
                pending[outcome.next_state].append(coefficient * outcome.probability)

    propagate((state, competitor_action), 1.0)
    propagate((state, best_action), -1.0)
    # FiniteModel requires every edge to decrease the layer by exactly one.
    for _ in range(model.layers[state] - 1):
        current, pending = pending, defaultdict(list)
        for successor, pieces in sorted(current.items()):
            counts["signed_states_combined"] += 1
            coefficient = math.fsum(pieces)
            if coefficient == 0.0:
                counts["cancelled_states"] += 1
                continue
            key = successor, policy[successor]
            coefficients[key] = coefficient
            propagate(key, coefficient)
        if not pending:
            break
    return coefficients, counts


def _nominal_prediction(
    model: FiniteModel, counts: dict[Row, int], query: Query,
    actions: dict[int, tuple[str, ...]],
) -> tuple[dict[int, str], dict[Row, float], dict[Row, float], dict[str, int]]:
    """Backward DP and unbiased observed target variances, on the pilot only."""
    values: dict[int, float] = {}
    policy: dict[int, str] = {}
    q_values: dict[Row, float] = {}
    variances: dict[Row, float] = {}
    work = {"visited_states": 0, "active_states": 0, "dp_state_action_rows": 0,
            "dp_outcomes": 0, "variance_state_action_rows": 0, "variance_outcomes": 0}
    for state in sorted(model.layers, key=lambda item: (model.layers[item], item)):
        work["visited_states"] += 1
        if model.terminal[state] != "ACTIVE":
            values[state] = _terminal_value(model.terminal[state], query)
            continue
        work["active_states"] += 1
        for action in actions[state]:
            key = state, action
            row = model.rows[key]
            targets = [(outcome.probability,
                        query.reward_weight * outcome.reward + values[outcome.next_state])
                       for outcome in row]
            mean = math.fsum(probability * value for probability, value in targets)
            q_values[key] = mean
            variances[key] = counts[key] / (counts[key] - 1) * math.fsum(
                probability * (value - mean) ** 2 for probability, value in targets)
            work["dp_state_action_rows"] += 1
            work["dp_outcomes"] += len(row)
            work["variance_state_action_rows"] += 1
            work["variance_outcomes"] += len(row)
        # Match the compiled planner's sorted-action, strict-maximum tie rule.
        policy[state] = max(actions[state], key=lambda action: q_values[state, action])
        values[state] = q_values[state, policy[state]]
    return policy, q_values, variances, work


def _integer_allocation(scores: dict[Row, float], budget: int) -> dict[Row, int]:
    keys = sorted(scores)
    if not keys:
        return {}
    weights = {key: math.sqrt(scores[key]) for key in keys}
    total_weight = math.fsum(weights.values())
    if total_weight == 0.0:
        return {key: budget for key in keys}
    floor = budget // 2
    directed_total = (budget - floor) * len(keys)
    shares = {key: directed_total * weights[key] / total_weight for key in keys}
    directed = {key: math.floor(shares[key]) for key in keys}
    remainder = directed_total - sum(directed.values())
    order = sorted(keys, key=lambda key: (-(shares[key] - directed[key]), key))
    for key in order[:remainder]:
        directed[key] += 1
    return {key: floor + directed[key] for key in keys}


def plan_allocations(
    empirical: FiniteModel,
    counts: dict[Row, int],
    queries: dict[str, Query],
    budgets: tuple[int, ...] = (256, 1024),
) -> AllocationResult:
    """Freeze total row counts for every budget from the same pilot model.

    For each query and active state, compare every competitor to the nominal
    best action, using a shared fixed nominal continuation. A pair is ambiguous
    when its estimated standard error is positive and its nonnegative predicted
    gap is at most two standard errors. The per-row score sums its squared signed
    occupancy times its observed target variance, divided by each ambiguous
    pair's gap variance. Half of each total budget is uniform; the remaining
    half follows square-root scores with deterministic largest remainders.

    ``counts`` are pilot draws, and returned counts include those pilot draws.
    All budgets are allocated before any post-pilot observation is available.
    """
    started = time.perf_counter()
    if counts.keys() != empirical.rows.keys() or any(
        not isinstance(count, int) or count < 2 for count in counts.values()
    ):
        raise ValueError("each empirical row needs its integer pilot count of at least two")
    if not queries or not budgets or any(
        not isinstance(budget, int) or budget % 2 or budget // 2 < max(counts.values(), default=0)
        for budget in budgets
    ):
        raise ValueError("queries and even budgets with floors covering the pilot are required")
    actions = _actions(empirical)
    scores = dict.fromkeys(sorted(empirical.rows), 0.0)
    pairs: list[dict] = []
    query_summaries: dict[str, dict] = {}
    work = {
        "nominal_dp_and_variance": defaultdict(int),
        "counterfactual_propagation": defaultdict(int),
        "gap_variance": {"pairs": 0, "row_coefficients": 0},
        "score_accumulation": {"ambiguous_pairs": 0, "row_coefficients": 0},
    }
    times = {"nominal_dp_and_variance_seconds": 0.0,
             "counterfactual_and_scores_seconds": 0.0}
    top_candidates: list[dict] = []
    for query_name, query in queries.items():
        stage = time.perf_counter()
        policy, q_values, variances, nominal_work = _nominal_prediction(
            empirical, counts, query, actions)
        times["nominal_dp_and_variance_seconds"] += time.perf_counter() - stage
        work["nominal_dp_and_variance"]["queries"] += 1
        for key, value in nominal_work.items():
            work["nominal_dp_and_variance"][key] += value
        stage = time.perf_counter()
        query_pairs: list[dict] = []
        for state in sorted(actions):
            best = policy[state]
            for competitor in actions[state]:
                if competitor == best:
                    continue
                coefficients, influence_work = signed_policy_gap_influences(
                    empirical, policy, state, best, competitor)
                for key, value in influence_work.items():
                    work["counterfactual_propagation"][key] += value
                components = {
                    key: coefficient ** 2 * variances[key]
                    for key, coefficient in coefficients.items()
                }
                gap_variance = math.fsum(value / counts[key] for key, value in components.items())
                se = math.sqrt(gap_variance)
                gap = q_values[state, best] - q_values[state, competitor]
                ambiguous = se > 0.0 and gap <= AMBIGUITY_SE_MULTIPLIER * se
                record = {"query": query_name, "state": state, "layer": empirical.layers[state],
                          "best_action": best, "competitor_action": competitor,
                          "predicted_gap": gap, "gap_variance": gap_variance,
                          "standard_error": se, "ambiguous": ambiguous,
                          "nominal_numerical_tie": gap <= TIE_TOLERANCE,
                          "influential_rows": len(coefficients)}
                pairs.append(record)
                query_pairs.append(record)
                work["gap_variance"]["pairs"] += 1
                work["gap_variance"]["row_coefficients"] += len(coefficients)
                if ambiguous:
                    for key, value in components.items():
                        scores[key] += value / gap_variance
                    work["score_accumulation"]["ambiguous_pairs"] += 1
                    work["score_accumulation"]["row_coefficients"] += len(coefficients)
                    largest = sorted(components, key=lambda key: (-components[key] / counts[key], key))[:3]
                    top_candidates.append({**record, "top_variance_contributors": [
                        {"state": key[0], "action": key[1], "coefficient": coefficients[key],
                         "observed_target_variance": variances[key],
                         "gap_variance_share": components[key] / counts[key] / gap_variance}
                        for key in largest if components[key] > 0.0]})
        times["counterfactual_and_scores_seconds"] += time.perf_counter() - stage
        query_summaries[query_name] = {
            "pairs": len(query_pairs), "ambiguous_pairs": sum(p["ambiguous"] for p in query_pairs),
            "zero_estimated_gap_variance_pairs": sum(p["gap_variance"] == 0.0 for p in query_pairs),
            "numerically_tied_pairs": sum(p["nominal_numerical_tie"] for p in query_pairs),
            "rows_with_zero_observed_target_variance": sum(value == 0.0 for value in variances.values()),
        }
    stage = time.perf_counter()
    allocations = {budget: _integer_allocation(scores, budget) for budget in budgets}
    allocation_summaries = {}
    for budget, allocation in allocations.items():
        total = sum(allocation.values())
        ordered = sorted(allocation, key=lambda key: (-allocation[key], key))
        layers: dict[int, dict] = {}
        for key, count in allocation.items():
            layer = empirical.layers[key[0]]
            record = layers.setdefault(layer, {"rows": 0, "pilot_draws": 0, "allocated_draws": 0,
                                               "maximum_row_count": 0})
            record["rows"] += 1
            record["pilot_draws"] += counts[key]
            record["allocated_draws"] += count
            record["maximum_row_count"] = max(record["maximum_row_count"], count)
        for record in layers.values():
            record["mean_row_count"] = record["allocated_draws"] / record["rows"]
        allocation_summaries[budget] = {
            "total_draws": total, "uniform_comparator_draws": budget * len(allocation),
            "minimum_row_count": min(allocation.values(), default=0),
            "maximum_row_count": max(allocation.values(), default=0),
            "maximum_row_share": max(allocation.values(), default=0) / total if total else 0.0,
            "top_ten_row_share": sum(allocation[key] for key in ordered[:10]) / total if total else 0.0,
            "rows_above_uniform": sum(count > budget for count in allocation.values()),
            "rows_at_floor": sum(count == budget // 2 for count in allocation.values()),
            "by_layer": layers,
            "top_rows": [{"state": key[0], "action": key[1], "count": allocation[key],
                          "score": scores[key]} for key in ordered[:10]],
        }
    times["integer_allocation_and_summary_seconds"] = time.perf_counter() - stage
    top_candidates.sort(key=lambda pair: (
        pair["predicted_gap"] / pair["standard_error"], pair["query"], pair["state"], pair["competitor_action"]))
    diagnostics = {
        "method": "pilot_fixed_policy_signed_gap_variance_allocation_v5",
        "uncertainty_interpretation": "first_order_fixed_policy_heuristic_not_confidence_bound",
        "ambiguous_pair_rule": "positive_standard_error_and_gap_at_most_two_standard_errors",
        "numerical_tie_tolerance": TIE_TOLERANCE,
        "numerical_tie_used_to_expand_ambiguity_threshold": False,
        "pilot_rows": len(counts), "pilot_total_draws": sum(counts.values()),
        "minimum_pilot_row_count": min(counts.values(), default=0),
        "maximum_pilot_row_count": max(counts.values(), default=0),
        "query_names": list(queries), "query_summaries": query_summaries,
        "pair_weighting": "equal_weight_each_ambiguous_pair_over_all_covered_states_and_queries",
        "pairs": len(pairs), "ambiguous_pairs": sum(pair["ambiguous"] for pair in pairs),
        "positive_score_rows": sum(score > 0.0 for score in scores.values()),
        "uniform_fallback": not any(scores.values()),
        "uniform_fallback_reason": "no_positive_observed_score" if not any(scores.values()) else None,
        "allocation_summaries": allocation_summaries,
        "top_ambiguous_pair_witnesses": top_candidates[:12],
        "work_counts": {category: dict(values) for category, values in work.items()},
        "timings": times,
    }
    diagnostics["timings"]["total_allocation_seconds"] = time.perf_counter() - started
    return AllocationResult(allocations, diagnostics, tuple(pairs))
