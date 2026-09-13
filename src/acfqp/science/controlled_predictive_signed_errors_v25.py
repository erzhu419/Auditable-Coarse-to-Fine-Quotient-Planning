"""Numeric attribution of retained action values; no model or truth access."""

from itertools import combinations
import math
from time import perf_counter


TOLERANCE = 1e-10
MODES = ("RAW", "REMOVE_A", "REMOVE_D")
VALUE_FIELDS = ("q_hat", "q_star", "A_transition_error", "D_continuation_error", "total_error")
DECOMPOSITION_FIELDS = (*VALUE_FIELDS, "q_hat_exact_continuation")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _check_close(actual, expected, name, residuals):
    if actual is None or expected is None:
        _require(actual is expected, name + " availability differs")
        return
    residual = abs(actual - expected)
    _require(math.isfinite(residual) and residual <= TOLERANCE, name + " differs")
    residuals.append(residual)


def _cancellation(a, d):
    if a is None or d is None:
        return {"opposite_sign_A_D": None, "cancelled_absolute_error": None}
    opposite = a * d < 0 and abs(a) > TOLERANCE and abs(d) > TOLERANCE
    return {"opposite_sign_A_D": opposite,
            "cancelled_absolute_error": max(0., abs(a) + abs(d) - abs(math.fsum((a, d))))}


def _margin(left_name, right_name, actions):
    left, right = actions[left_name], actions[right_name]
    result = {"actions": [left_name, right_name],
        "observed_both": left["observed"] and right["observed"],
        "decomposable": left["decomposable"] and right["decomposable"],
        "batch_counts": [left["batch_count"], right["batch_count"]],
        "lower_difference_bound": left["lower"] - right["upper"],
        "upper_difference_bound": left["upper"] - right["lower"],
        "raw_lower_difference": left["lower"] - right["lower"]}
    for field in VALUE_FIELDS:
        a, b = left[field], right[field]
        result[field + "_difference"] = a - b if a is not None and b is not None else None
    a, d = result["A_transition_error_difference"], result["D_continuation_error_difference"]
    result.update(_cancellation(a, d))
    result["identity_residual"] = (result["q_hat_difference"] - result["q_star_difference"] - math.fsum((a, d))) if result["decomposable"] else None
    for mode in MODES[1:]:
        a, b = left["mode_values"][mode], right["mode_values"][mode]
        result[mode + "_difference"] = a - b if a is not None and b is not None else None
    return result


def diagnose_target(target):
    """Retain every action; an incomplete decomposition disables both corrections."""
    started = perf_counter()
    source_actions = target["actions"]
    names = sorted(source_actions)
    _require(bool(names), "retained target has no legal actions")
    actions, residuals, unavailable = {}, [], []
    for name in names:
        source = source_actions[name]
        row = {field: source.get(field) for field in DECOMPOSITION_FIELDS}
        row.update(observed=source["observed"], batch_count=source["batch_count"],
                   lower=source["lower"], upper=source["upper"])
        _require(all(row[field] is not None and math.isfinite(row[field]) for field in ("q_star", "lower", "upper")),
                 "retained action lacks finite truth or bounds: " + name)
        if row["q_hat"] is not None:
            _require(row["q_hat"] == row["lower"], "retained Qhat differs from empirical lower: " + name)
        row["decomposable"] = bool(row["observed"] and all(row[field] is not None for field in DECOMPOSITION_FIELDS))
        row["mode_values"] = {"RAW": row["lower"], "REMOVE_A": None, "REMOVE_D": None}
        row["signed_total_error"] = row["q_hat"] - row["q_star"] if row["q_hat"] is not None else None
        row["identity_residual"] = None
        row["removal_algebra_residuals"] = None
        if row["decomposable"]:
            qhat, qstar, a, d = (row[field] for field in ("q_hat", "q_star", "A_transition_error", "D_continuation_error"))
            _check_close(row["total_error"], qhat - qstar, "retained total error for " + name, residuals)
            _check_close(a, row["q_hat_exact_continuation"] - qstar, "retained transition error for " + name, residuals)
            row["identity_residual"] = qhat - qstar - math.fsum((a, d))
            _check_close(row["identity_residual"], 0., "action A+D identity for " + name, residuals)
            _check_close(source["identity_residual"], row["identity_residual"], "retained action identity for " + name, residuals)
            remove_a, remove_d = qstar + d, row["q_hat_exact_continuation"]
            row["mode_values"].update(REMOVE_A=remove_a, REMOVE_D=remove_d)
            row["removal_algebra_residuals"] = {"REMOVE_A": remove_a - (qhat - a), "REMOVE_D": remove_d - (qhat - d)}
            for mode, residual in row["removal_algebra_residuals"].items():
                _check_close(residual, 0., mode + " algebra for " + name, residuals)
        else:
            unavailable.append({"action": name, "reason": "UNOBSERVED_ACTION" if not row["observed"] else "INCOMPLETE_DECOMPOSITION"})
        row.update(_cancellation(row["A_transition_error"], row["D_continuation_error"]))
        actions[name] = row
    margins = [_margin(left, right, actions) for left, right in combinations(names, 2)]
    retained_margins = target["pair_margins"]
    _require([row["actions"] for row in margins] == [row["actions"] for row in retained_margins], "retained pair order or coverage differs")
    for actual, source in zip(margins, retained_margins):
        _require(actual["observed_both"] == source["observed_both"], "retained pair observation status differs")
        for field in ("lower_difference_bound", "upper_difference_bound", "identity_residual",
                      *(name + "_difference" for name in VALUE_FIELDS)):
            _check_close(source[field], actual[field], "retained pair " + field, residuals)
        if actual["decomposable"]:
            _check_close(actual["identity_residual"], 0., "pair A+D identity", residuals)
    qstar = {name: row["q_star"] for name, row in actions.items()}
    best_value = max(qstar.values())
    optimal = [name for name in names if best_value - qstar[name] <= TOLERANCE]
    _require(best_value == target["v_star"] and optimal == target["local_true_optimal_actions"], "retained true optimal values or action set differ")
    true_representative = optimal[0]
    raw_action = min(names, key=lambda name: (-actions[name]["lower"], name))
    raw_wrong, raw_regret = raw_action not in optimal, best_value - qstar[raw_action]
    raw_checks = {
        "selected_action": raw_action == target["selected_action"],
        "wrong": raw_wrong == (not target["selected_action_in_true_optimal_set"]),
        "regret": raw_regret == target["local_regret"],
        "lower": actions[raw_action]["lower"] == target["lower"],
        "upper": max(row["upper"] for row in actions.values()) == target["upper"],
        "selected_action_observed": actions[raw_action]["observed"] == target["selected_action_observed"],
        "source_identities_pass": target["identities_pass"],
    }
    _require(all(raw_checks.values()), "RAW source reproduction differs: " + ", ".join(name for name, passed in raw_checks.items() if not passed))
    modes = {}
    for mode in MODES:
        available = mode == "RAW" or not unavailable
        selected = min(names, key=lambda name: (-actions[name]["mode_values"][mode], name)) if available else None
        wrong = selected not in optimal if available else None
        modes[mode] = {"available": available, "selected_action": selected,
            "selected_value": actions[selected]["mode_values"][mode] if available else None,
            "wrong": wrong, "regret": best_value - qstar[selected] if available else None,
            "raw_wrong_repaired": bool(raw_wrong and not wrong) if available else None,
            "raw_correct_new_error": bool(not raw_wrong and wrong) if available else None,
            "choice_changed": selected != raw_action if available else None,
            "selected_action_batch_count": actions[selected]["batch_count"] if available else None}
        if not available:
            modes[mode]["reason"] = "AT_LEAST_ONE_LEGAL_ACTION_IS_NOT_DECOMPOSABLE"
    modes["RAW"].update(lower=target["lower"], upper=target["upper"],
                         selected_action_observed=target["selected_action_observed"])
    choice_counts = {"RAW": {"action": raw_action, "batch_count": actions[raw_action]["batch_count"]},
        "true_optimal_representative": {"action": true_representative, "batch_count": actions[true_representative]["batch_count"]},
        **{mode: {"action": modes[mode]["selected_action"], "batch_count": modes[mode]["selected_action_batch_count"]} for mode in MODES[1:]}}
    return {"target_key": target["target_key"], "query_name": target["query_name"],
        "actions": actions, "pair_margins": margins, "modes": modes,
        "true_optimal_actions": optimal, "true_optimal_representative": true_representative,
        "original_selected_action": raw_action, "choice_batch_counts": choice_counts,
        "true_optimal_minus_raw_choice": _margin(true_representative, raw_action, actions),
        "unavailable_actions": unavailable,
        "validation": {"all_passed": True, "raw_checks": raw_checks,
            "maximum_absolute_checked_residual": max(residuals, default=0.),
            "checked_action_count": len(actions), "checked_pair_count": len(margins)},
        "accounting": {"numeric_diagnosis_seconds": perf_counter() - started,
            "action_records_processed": len(actions), "pair_records_processed": len(margins),
            "new_provider_calls": 0, "new_oracle_calls": 0, "new_physical_draws": 0},
        "scope": "Numeric evaluation of retained values. Corrections use retained truth for attribution only; they are not acquisition or execution policies."}
