"""Evaluate a retained endpoint policy without restoring or solving its model."""

from collections import Counter
from dataclasses import asdict
import math
from time import perf_counter

from .controlled_predictive_partial_v12 import _terminal


TOLERANCE = 1e-10


def _key(value):
    return value[0], tuple(value[1])


def _json_key(value):
    return [value[0], list(value[1])]


def _delta(after, before):
    return {key: value - before.get(key, 0) for key, value in after.items()
            if value != before.get(key, 0)}


def evaluate_frozen_policy(state_record, target_key, query, oracle):
    """Follow only stored actions, with exact transitions from the H2 target.

    Missing ACTIVE policy definitions stop their branch. Any positive missing
    probability makes the complete policy value unavailable; observed-row
    membership does not restrict a stored legal action's evaluation.
    """
    started = perf_counter()
    target_key = _key(target_key)
    if state_record["query"] != asdict(query):
        raise ValueError("Retained and evaluation query weights differ")
    profiles = {_key(item["key"]): item for item in state_record["profiles"]}
    policy = {_key(item["key"]): item for item in state_record["policy_and_intervals"]}
    observed = {(_key(item["row_key"][0]), item["row_key"][1])
                for item in state_record["rows"]}
    work = Counter(retained_profiles_indexed=len(profiles),
                   retained_policy_entries_indexed=len(policy),
                   retained_observed_row_keys_indexed=len(observed))
    if (target_key[0] != 2 or target_key not in profiles
            or profiles[target_key]["status"] != "ACTIVE"
            or target_key not in policy or policy[target_key]["action"] is None):
        raise ValueError("Evaluation requires the retained ACTIVE H2 target action")
    extraction_seconds = perf_counter() - started
    oracle_work_before = Counter(oracle.work_counts)
    oracle_seconds_before = Counter(oracle.seconds_by_stage)
    truth = oracle.solution(query)
    arithmetic_started = perf_counter()

    # Parent contributions are retained separately until the whole layer has
    # arrived, so a convergent state is expanded only once at its total mass.
    contributions = {target_key: [1.0]}
    reach, selected_rows, decisions, terminals, missing = {}, {}, [], [], []
    for remaining in range(target_key[0], -1, -1):
        for key in sorted(key for key in contributions if key[0] == remaining):
            mass = math.fsum(contributions[key])
            if mass <= 0:
                continue
            reach[key] = mass
            work["true_reachable_states_visited"] += 1
            status = oracle.statuses[key]
            if key in profiles and profiles[key]["status"] != status:
                raise ValueError("Retained profile status differs from the exact model")
            if status != "ACTIVE":
                terminals.append({"key": _json_key(key), "status": status,
                    "reach_probability": mass, "terminal_value": _terminal(status, query)})
                continue
            item = policy.get(key)
            action = item["action"] if item is not None else None
            if action is None:
                reason = "NO_RETAINED_POLICY_ACTION"
                missing.append({"key": _json_key(key), "reach_probability": mass,
                                "reason": reason})
                decisions.append({"key": _json_key(key), "reach_probability": mass,
                    "action": None, "observed": None, "local_regret": None,
                    "weighted_regret": None, "policy_defined": False})
                continue
            if key not in profiles or action not in profiles[key]["legal_actions"]:
                raise ValueError("Retained policy action lacks its legal retained profile")
            pair = key, action
            if pair not in oracle.rows:
                raise ValueError("Retained policy action is absent from the exact model")
            regret = truth.values[key] - truth.q_values[pair]
            decisions.append({"key": _json_key(key), "reach_probability": mass,
                "action": action, "observed": pair in observed,
                "local_regret": regret, "weighted_regret": mass * regret,
                "policy_defined": True})
            row = oracle.rows[pair]
            selected_rows[key] = row
            work.update(true_policy_rows_read=1, true_policy_support_entries_read=len(row),
                        true_action_regret_lookups=1)
            for probability, successor, reward in row:
                if successor[0] != remaining - 1:
                    raise ValueError("Exact policy edge does not decrease remaining horizon")
                if probability > 0:
                    contributions.setdefault(successor, []).append(mass * probability)

    # Independently evaluate rewards and terminal payoffs by backward DP.
    # Do not derive Vpi by subtracting the weighted regret sum from Vstar.
    values = {}
    for key in sorted(reach):
        work["frozen_policy_dp_states_visited"] += 1
        status = oracle.statuses[key]
        if status != "ACTIVE":
            values[key] = _terminal(status, query)
        elif key not in selected_rows:
            values[key] = None
        else:
            row = selected_rows[key]
            if any(values[successor] is None for probability, successor, _ in row if probability > 0):
                values[key] = None
            else:
                values[key] = math.fsum(probability * (query.reward_weight * reward + values[successor])
                    for probability, successor, reward in row if probability > 0)
            work["frozen_policy_dp_support_entries_read"] += len(row)

    initial = policy[target_key]
    action = initial["action"]
    v_star = truth.values[target_key]
    q_star = truth.q_values[target_key, action]
    optimal = sorted(candidate for candidate in profiles[target_key]["legal_actions"]
                     if v_star - truth.q_values[target_key, candidate] <= TOLERANCE)
    missing_probability = math.fsum(item["reach_probability"] for item in missing)
    evaluable = missing_probability == 0
    v_pi = values[target_key] if evaluable else None
    first_regret = v_star - q_star
    defined_continuation = math.fsum(item["weighted_regret"] for item in decisions
        if item["policy_defined"] and _key(item["key"]) != target_key)
    continuation = defined_continuation if evaluable else None
    total = v_star - v_pi if evaluable else None
    residual = total - math.fsum((first_regret, continuation)) if evaluable else None
    terminal_probability = math.fsum(item["reach_probability"] for item in terminals)
    reach_residual = math.fsum((terminal_probability, missing_probability)) - 1.0
    return {
        "target_key": _json_key(target_key), "query": asdict(query),
        "policy_evaluable": evaluable,
        "unavailable_reason": None if evaluable else "POSITIVE_MISSING_POLICY_PROBABILITY",
        "v_pi": v_pi, "v_star": v_star, "total_regret": total,
        "first_action_regret": first_regret, "continuation_regret": continuation,
        "defined_continuation_regret": defined_continuation,
        "policy_optimal": total <= TOLERANCE if evaluable else None,
        "initial_action": action, "first_action_wrong": action not in optimal,
        "selected_action_q_star": q_star,
        "selected_action_observed": (target_key, action) in observed,
        "lower": initial["lower"], "upper": initial["upper"],
        "local_true_optimal_actions": optimal,
        "missing_probability": missing_probability,
        "weighted_unobserved_choices": math.fsum(item["reach_probability"] for item in decisions
            if item["policy_defined"] and not item["observed"]),
        "reachable_decisions": decisions, "missing_policy_frontier": missing,
        "reachable_terminals": terminals, "terminal_probability": terminal_probability,
        "identity_residual": residual,
        "identities_pass": abs(residual) <= TOLERANCE if evaluable else None,
        "reach_probability_residual": reach_residual,
        "reach_probability_pass": abs(reach_residual) <= TOLERANCE,
        "accounting": {
            "policy_extraction_seconds": extraction_seconds,
            "fixed_policy_evaluation_seconds": perf_counter() - arithmetic_started,
            "oracle_work": _delta(oracle.work_counts, oracle_work_before),
            "oracle_seconds_by_stage": _delta(oracle.seconds_by_stage, oracle_seconds_before),
            "work_counts": dict(work), "whole_evaluation_seconds": perf_counter() - started,
            "new_physical_draws": 0, "new_provider_calls": 0, "new_planner_solves": 0,
            "scope": "Whole evaluation includes extraction, oracle query work and fixed-policy arithmetic; nested times are not additive."},
        "scope": "The complete retained endpoint policy is frozen and followed from the original H2 target with true transition probabilities. Weighted unobserved choices count expected visits, not probability of any unobserved choice. Defined continuation regret is only the visited, defined portion when policy coverage is incomplete. No online acquisition or replanning is evaluated.",
    }
