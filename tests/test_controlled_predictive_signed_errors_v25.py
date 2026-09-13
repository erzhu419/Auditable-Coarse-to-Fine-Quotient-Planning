from copy import deepcopy
from itertools import combinations
import math

import pytest

from acfqp.science.controlled_predictive_signed_errors_v25 import diagnose_target


def _refresh_target(actions):
    names = sorted(actions)
    selected = min(names, key=lambda name: (-actions[name]["lower"], name))
    best = max(row["q_star"] for row in actions.values())
    optimal = [name for name in names if best - actions[name]["q_star"] <= 1e-10]
    pairs = []
    for left, right in combinations(names, 2):
        a, b = actions[left], actions[right]
        pair = {"actions": [left, right], "observed_both": a["observed"] and b["observed"],
            "lower_difference_bound": a["lower"] - b["upper"],
            "upper_difference_bound": a["upper"] - b["lower"]}
        for field in ("q_hat", "q_star", "A_transition_error", "D_continuation_error", "total_error"):
            pair[field + "_difference"] = a[field] - b[field] if a[field] is not None and b[field] is not None else None
        decomposed = pair["observed_both"] and all(pair[field] is not None for field in (
            "q_hat_difference", "A_transition_error_difference", "D_continuation_error_difference"))
        pair["identity_residual"] = pair["q_hat_difference"] - pair["q_star_difference"] - math.fsum((
            pair["A_transition_error_difference"], pair["D_continuation_error_difference"])) if decomposed else None
        pairs.append(pair)
    return {"target_key": [2, [0] * 16], "query_name": "q", "actions": actions,
        "pair_margins": pairs, "selected_action": selected,
        "selected_action_in_true_optimal_set": selected in optimal,
        "selected_action_observed": actions[selected]["observed"],
        "local_regret": best - actions[selected]["q_star"], "v_star": best,
        "local_true_optimal_actions": optimal, "lower": actions[selected]["lower"],
        "upper": max(row["upper"] for row in actions.values()), "identities_pass": True}


def _target(rows):
    """Pure-number retained fixture; optional fifth entry fixes Qhat arithmetic."""
    actions = {}
    for name, values in rows.items():
        qstar, a, d, batches = values[:4]
        exact_continuation = qstar + a
        qhat = values[4] if len(values) == 5 else exact_continuation + d
        actions[name] = {"observed": True, "batch_count": batches, "lower": qhat, "upper": qhat,
            "q_hat": qhat, "q_star": qstar, "q_hat_exact_continuation": exact_continuation,
            "A_transition_error": a, "D_continuation_error": d, "total_error": qhat - qstar,
            "identity_residual": qhat - qstar - math.fsum((a, d))}
    return _refresh_target(actions)


def test_signed_pair_identity_cancellation_and_raw_error_repair_preserve_input():
    target = _target({"RIGHT": (.9, 0., 0., 5), "LEFT": (1., -2., 1.5, 2)})
    original = deepcopy(target)
    result = diagnose_target(target)
    assert target == original
    assert list(result["actions"]) == ["LEFT", "RIGHT"]
    raw, remove_a, remove_d = (result["modes"][mode] for mode in ("RAW", "REMOVE_A", "REMOVE_D"))
    assert raw["selected_action"] == "RIGHT" and raw["wrong"] and raw["regret"] == target["local_regret"]
    assert remove_a["selected_action"] == "LEFT" and not remove_a["wrong"] and remove_a["raw_wrong_repaired"]
    assert remove_d["selected_action"] == "RIGHT" and remove_d["wrong"] and not remove_d["choice_changed"]
    pair = result["pair_margins"][0]
    assert pair["actions"] == ["LEFT", "RIGHT"]
    assert pair["q_hat_difference"] == pytest.approx(-.4)
    assert pair["q_star_difference"] == pytest.approx(.1)
    assert pair["A_transition_error_difference"] == -2 and pair["D_continuation_error_difference"] == 1.5
    assert pair["opposite_sign_A_D"] and pair["cancelled_absolute_error"] == 3
    assert result["true_optimal_minus_raw_choice"] == pair
    assert result["choice_batch_counts"]["RAW"] == {"action": "RIGHT", "batch_count": 5}
    assert result["choice_batch_counts"]["true_optimal_representative"] == {"action": "LEFT", "batch_count": 2}
    assert result["validation"]["all_passed"]
    assert result["accounting"]["new_provider_calls"] == result["accounting"]["new_oracle_calls"] == result["accounting"]["new_physical_draws"] == 0


@pytest.mark.parametrize("a,d,mode", [(-.2, .4, "REMOVE_D"), (.3, -.2, "REMOVE_A")])
def test_removing_an_error_can_destroy_helpful_cancellation(a, d, mode):
    result = diagnose_target(_target({"LEFT": (1., a, d, 3), "RIGHT": (.9, 0., 0., 1)}))
    assert not result["modes"]["RAW"]["wrong"]
    corrected = result["modes"][mode]
    assert corrected["selected_action"] == "RIGHT" and corrected["wrong"]
    assert corrected["raw_correct_new_error"] and corrected["choice_changed"]
    assert not corrected["raw_wrong_repaired"]


def test_stable_corrections_and_exact_ties_do_not_use_truth_tolerance_for_argmax():
    target = _target({"LEFT": (.3, .2, 0., 1), "RIGHT": (.1, .3, .2, 1, .6)})
    result = diagnose_target(target)
    right = result["actions"]["RIGHT"]
    assert right["q_hat"] - right["A_transition_error"] == .3
    assert right["mode_values"]["REMOVE_A"] == .1 + .2 > .3
    assert result["modes"]["REMOVE_A"]["selected_action"] == "RIGHT"
    assert result["modes"]["REMOVE_D"]["selected_action"] == "LEFT"
    near = diagnose_target(_target({"RIGHT": (1. + 5e-11, 0., 0., 1), "LEFT": (1., 0., 0., 1)}))
    assert near["true_optimal_actions"] == ["LEFT", "RIGHT"]
    assert near["true_optimal_representative"] == "LEFT"
    assert all(mode["selected_action"] == "RIGHT" and not mode["wrong"] for mode in near["modes"].values())
    tied = diagnose_target(_target({"RIGHT": (1., 0., 0., 1), "LEFT": (1., 0., 0., 1)}))
    assert all(mode["selected_action"] == "LEFT" for mode in tied["modes"].values())


@pytest.mark.parametrize("observed", [False, True])
def test_any_unknown_or_incomplete_action_disables_both_corrections_without_subset_choice(observed):
    actions = _target({"LEFT": (.5, 0., 0., 1), "RIGHT": (1., -.2, 0., 1)})["actions"]
    right = actions["RIGHT"]
    right.update(observed=observed, A_transition_error=None, q_hat_exact_continuation=None, identity_residual=None)
    if not observed:
        right.update(q_hat=None, total_error=None, D_continuation_error=None, batch_count=0, lower=.8, upper=2.)
    result = diagnose_target(_refresh_target(actions))
    assert result["modes"]["RAW"]["available"] and result["modes"]["RAW"]["selected_action"] == "RIGHT"
    for mode in ("REMOVE_A", "REMOVE_D"):
        assert not result["modes"][mode]["available"]
        assert result["modes"][mode]["selected_action"] is None and result["modes"][mode]["regret"] is None
        assert result["modes"][mode]["raw_wrong_repaired"] is None
    assert len(result["actions"]) == 2 and len(result["pair_margins"]) == 1
    assert not result["pair_margins"][0]["decomposable"]
    assert result["unavailable_actions"] == [{"action": "RIGHT", "reason": "INCOMPLETE_DECOMPOSITION" if observed else "UNOBSERVED_ACTION"}]


def test_small_opposite_terms_do_not_receive_cancellation_marker():
    result = diagnose_target(_target({"LEFT": (1., 5e-11, -5e-11, 1), "RIGHT": (.9, 0., 0., 1)}))
    assert not result["actions"]["LEFT"]["opposite_sign_A_D"]
    assert not result["pair_margins"][0]["opposite_sign_A_D"]


@pytest.mark.parametrize("damage,message", [("pair", "retained pair"), ("identity", "retained transition error"),
                                            ("raw", "RAW source reproduction")])
def test_inconsistent_retained_arithmetic_or_source_choice_is_rejected(damage, message):
    target = _target({"LEFT": (1., -.2, .4, 2), "RIGHT": (.9, 0., 0., 3)})
    if damage == "pair":
        target["pair_margins"][0]["q_hat_difference"] += .01
    elif damage == "identity":
        target["actions"]["LEFT"]["A_transition_error"] += .01
    else:
        target["selected_action"] = "RIGHT"
    with pytest.raises(ValueError, match=message):
        diagnose_target(target)
