"""True path weights, frozen actions, missing coverage and terminal payoffs."""

from copy import deepcopy
from dataclasses import asdict

import pytest

from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_frozen_policy_v27 import evaluate_frozen_policy
from acfqp.science.controlled_predictive_quotient_v1 import Query


ROOT, A, B, MISSING, END = (2, (1,)), (1, (2,)), (1, (3,)), (1, (4,)), (0, (0,))
HALT = (1, (5,))


def _json_key(key):
    return [key[0], list(key[1])]


def _record(oracle, policy, observed, query=Query(), omit_profiles=()):
    return {
        "root": _json_key(ROOT), "query": asdict(query),
        "profiles": [{"key": _json_key(key), "status": status,
            "legal_actions": list(oracle.actions.get(key, ())) }
            for key, status in oracle.statuses.items() if key not in omit_profiles],
        "policy_and_intervals": [{"key": _json_key(key), "action": action,
            "lower": -123., "upper": 456.} for key, action in policy.items()],
        "rows": [{"row_key": [_json_key(key), action], "batch_count": 3,
            "outcomes": [[.9, _json_key(A), 0.], [.1, _json_key(B), 0.]]}
            for key, action in observed],
    }


def numeric_fixture():
    oracle = ExactOracle({ROOT: "ACTIVE", A: "ACTIVE", B: "ACTIVE", HALT: "LOST", END: "CUTOFF"}, {
        (ROOT, "LEFT"): ((.25, A, 0.), (.75, B, 0.)),
        (ROOT, "RIGHT"): ((1., HALT, 6.),),
        (A, "LEFT"): ((1., END, 0.),), (A, "RIGHT"): ((1., END, 4.),),
        (B, "LEFT"): ((1., END, 1.),), (B, "RIGHT"): ((1., END, 2.),),
    })
    policy = {ROOT: "LEFT", A: "LEFT", B: "RIGHT", END: None}
    observed = [(ROOT, "LEFT"), (A, "LEFT"), (B, "RIGHT")]
    return _record(oracle, policy, observed), oracle


def test_true_weights_and_downstream_loss_are_independent_of_empirical_rows():
    record, oracle = numeric_fixture()
    before = deepcopy(record)
    result = evaluate_frozen_policy(record, ROOT, Query(), oracle)
    assert result["policy_evaluable"] and not result["policy_optimal"]
    assert result["initial_action"] == "LEFT" and result["first_action_wrong"]
    assert result["local_true_optimal_actions"] == ["RIGHT"]
    assert result["v_star"] == 6. and result["v_pi"] == 1.5
    assert result["first_action_regret"] == 3.5
    assert result["continuation_regret"] == 1. and result["total_regret"] == 4.5
    assert result["identity_residual"] == 0. and result["identities_pass"]
    assert result["lower"] == -123. and result["upper"] == 456.
    child = next(row for row in result["reachable_decisions"] if row["key"] == _json_key(A))
    assert child["reach_probability"] == .25 and child["weighted_regret"] == 1.
    assert result["terminal_probability"] == 1. and result["reach_probability_pass"]
    assert record == before
    for item in record["rows"]:
        item["outcomes"] = [[1., _json_key(END), 1000.]]
    repeated = evaluate_frozen_policy(record, ROOT, Query(), oracle)
    assert repeated["reachable_decisions"] == result["reachable_decisions"]
    assert repeated["v_pi"] == 1.5
    assert repeated["accounting"]["oracle_work"] == {"exact_query_cache_hits": 1}
    assert all(result["accounting"][name] == 0 for name in
               ("new_physical_draws", "new_provider_calls", "new_planner_solves"))


def test_convergent_true_support_is_merged_once_before_downstream_expansion():
    record, oracle = numeric_fixture()
    oracle.rows[ROOT, "LEFT"] = ((.125, A, 0.), (.125, A, 0.), (.75, B, 0.))
    result = evaluate_frozen_policy(record, ROOT, Query(), oracle)
    a_rows = [row for row in result["reachable_decisions"] if row["key"] == _json_key(A)]
    assert len(a_rows) == 1 and a_rows[0]["reach_probability"] == .25
    assert result["v_pi"] == 1.5 and result["continuation_regret"] == 1.
    assert len(result["reachable_terminals"]) == 1
    assert result["reachable_terminals"][0]["reach_probability"] == 1.
    assert result["accounting"]["work_counts"]["true_policy_rows_read"] == 3


def test_first_missing_frontier_keeps_merged_probability_and_original_action_result():
    record, oracle = numeric_fixture()
    oracle.statuses[MISSING] = "ACTIVE"
    oracle.rows[MISSING, "LEFT"] = ((1., END, 10.),)
    oracle.actions[MISSING] = ("LEFT",)
    oracle.rows[ROOT, "LEFT"] = ((.25, A, 0.), (.125, MISSING, 0.),
                                  (.375, MISSING, 0.), (.25, HALT, 0.))
    result = evaluate_frozen_policy(record, ROOT, Query(), oracle)
    assert not result["policy_evaluable"]
    assert result["missing_probability"] == .5 and result["terminal_probability"] == .5
    assert result["missing_policy_frontier"] == [{"key": _json_key(MISSING),
        "reach_probability": .5, "reason": "NO_RETAINED_POLICY_ACTION"}]
    assert result["v_pi"] is result["total_regret"] is result["continuation_regret"] is None
    assert result["identities_pass"] is result["policy_optimal"] is None
    assert result["initial_action"] == "LEFT" and not result["first_action_wrong"]
    assert result["first_action_regret"] == 0.
    assert result["defined_continuation_regret"] == 1.
    assert result["reach_probability_pass"]


@pytest.mark.parametrize("missing_mass", [1e-12, 0.])
def test_any_positive_missing_mass_is_unavailable_without_a_tolerance_cutoff(missing_mass):
    record, oracle = numeric_fixture()
    record["policy_and_intervals"] = [item for item in record["policy_and_intervals"]
                                       if item["key"] != _json_key(A)]
    oracle.rows[ROOT, "LEFT"] = ((missing_mass, A, 0.), (1. - missing_mass, B, 0.))
    result = evaluate_frozen_policy(record, ROOT, Query(), oracle)
    assert result["missing_probability"] == missing_mass
    assert result["policy_evaluable"] == (missing_mass == 0.)
    if missing_mass:
        assert result["v_pi"] is None
    else:
        assert result["v_pi"] == 2. and result["identities_pass"]


def test_terminal_reward_weight_goal_bonus_and_loss_penalty_are_counted_once():
    lost, won = (1, (8,)), (1, (9,))
    query = Query(2., 3., 5.)
    oracle = ExactOracle({ROOT: "ACTIVE", lost: "LOST", won: "WON", END: "CUTOFF"}, {
        (ROOT, "LEFT"): ((.5, lost, 1.), (.5, won, 2.)),
        (ROOT, "RIGHT"): ((1., won, .5),),
    })
    record = _record(oracle, {ROOT: "LEFT"}, [(ROOT, "LEFT")], query,
                     omit_profiles=(lost, won, END))
    result = evaluate_frozen_policy(record, ROOT, query, oracle)
    assert result["policy_evaluable"] and result["v_pi"] == 4.
    assert result["total_regret"] == result["first_action_regret"] == 2.
    assert result["continuation_regret"] == 0. and result["identities_pass"]
    assert sorted(row["terminal_value"] for row in result["reachable_terminals"]) == [-3., 5.]
    assert len(result["reachable_decisions"]) == 1


def test_legal_unobserved_policy_actions_remain_evaluable_without_substitution():
    record, oracle = numeric_fixture()
    record["rows"] = [row for row in record["rows"]
                      if row["row_key"] == [_json_key(A), "LEFT"]]
    result = evaluate_frozen_policy(record, ROOT, Query(), oracle)
    assert result["policy_evaluable"] and result["v_pi"] == 1.5
    assert not result["selected_action_observed"]
    assert result["weighted_unobserved_choices"] == 1.75
    assert result["initial_action"] == "LEFT" and result["first_action_wrong"]
    assert result["identities_pass"]


def test_retained_target_query_or_illegal_policy_mismatch_is_not_replanned():
    record, oracle = numeric_fixture()
    with pytest.raises(ValueError, match="query weights"):
        evaluate_frozen_policy(record, ROOT, Query(2.), oracle)
    with pytest.raises(ValueError, match="ACTIVE H2"):
        evaluate_frozen_policy(record, A, Query(), oracle)
    record["policy_and_intervals"][0]["action"] = "NO_SUCH_ACTION"
    with pytest.raises(ValueError, match="legal retained profile"):
        evaluate_frozen_policy(record, ROOT, Query(), oracle)
