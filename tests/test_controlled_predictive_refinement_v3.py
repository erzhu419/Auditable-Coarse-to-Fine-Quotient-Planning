import pytest

from acfqp.science.controlled_predictive_quotient_v1 import (
    FiniteModel, Outcome, Query, audit_policy, build_quotient, plan,
)
from acfqp.science.controlled_predictive_refinement_v3 import build_refined_quotient


def test_wrong_action_is_repaired_even_at_a_state_unreachable_from_the_root():
    model = FiniteModel(
        {0: 1, 1: 1, 2: 0}, {0: "ACTIVE", 1: "ACTIVE", 2: "CUTOFF"},
        {(0, "a"): (Outcome(1, 2, 0.004),), (0, "b"): (Outcome(1, 2, 0),),
         (1, "a"): (Outcome(1, 2, 0),), (1, "b"): (Outcome(1, 2, 0.004),)}, (0,),
    )
    old = build_quotient(model, 0.01, 0.2)
    assert old.state_to_cell[0] == old.state_to_cell[1]
    result = build_refined_quotient(model, {"reward": Query()})
    fitted = plan(result.compiled)
    assert fitted.policy[result.compiled.state_to_cell[0]] == "a"
    assert fitted.policy[result.compiled.state_to_cell[1]] == "b"
    assert result.diagnostics["refinement_rounds"] == 1
    assert result.diagnostics["iterations"][0]["worst_errors"]["policy_residual"] == pytest.approx(0.004)
    assert all(error <= 1e-10 for error in result.diagnostics["final_worst_errors"].values())


def test_same_root_action_does_not_hide_downstream_reward_and_risk_mismatch():
    model = FiniteModel(
        {0: 2, 1: 2, 2: 1, 3: 1, 4: 0, 5: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "ACTIVE", 4: "LOST", 5: "CUTOFF"},
        {(0, "go"): (Outcome(1, 2, 0),), (1, "go"): (Outcome(1, 3, 0),),
         (2, "go"): (Outcome(0.1, 4, 0.004), Outcome(0.9, 5, 0.004)),
         (3, "go"): (Outcome(1, 5, 0),)}, (0, 1),
    )
    old = build_quotient(model, 0.01, 0.2)
    assert old.state_to_cell[0] == old.state_to_cell[1]
    result = build_refined_quotient(model, {"reward": Query(), "risk": Query(failure_penalty=1)})
    assert result.diagnostics["refinement_rounds"] == 2
    assert result.compiled.state_to_cell[0] != result.compiled.state_to_cell[1]
    assert result.compiled.state_to_cell[2] != result.compiled.state_to_cell[3]
    for query in (Query(), Query(failure_penalty=1)):
        fitted = plan(result.compiled, query)
        assert set(fitted.policy.values()) == {"go"}
        audit = audit_policy(model, result.compiled, fitted, query)
        assert audit.root_metrics[0]["reward"] == pytest.approx(0.004)
        assert audit.root_metrics[0]["failure"] == pytest.approx(0.1)
        assert audit.root_metrics[1]["reward"] == audit.root_metrics[1]["failure"] == 0
    assert result.diagnostics["work_counts"]["partition_recompilation"]["calls"] == 2


def test_policy_equivalent_inexact_action_response_merge_is_retained():
    model = FiniteModel(
        {0: 1, 1: 1, 2: 0, 3: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "CUTOFF", 3: "LOST"},
        {(0, "safe"): (Outcome(1, 2, 0.02),),
         (1, "safe"): (Outcome(1, 2, 0.02),),
         (0, "unused"): (Outcome(1, 2, 0),),
         (1, "unused"): (Outcome(0.1, 3, 0.004), Outcome(0.9, 2, 0.004))}, (0, 1),
    )
    exact = build_quotient(model)
    assert exact.state_to_cell[0] != exact.state_to_cell[1]
    result = build_refined_quotient(model, {"reward": Query(), "risk": Query(failure_penalty=1)})
    assert result.compiled.state_to_cell[0] == result.compiled.state_to_cell[1]
    assert result.diagnostics["refinement_rounds"] == 0
    cell = result.compiled.state_to_cell[0]
    assert result.compiled.diameters[cell] == pytest.approx({"reward": 0.004, "tv": 0.1})
    # A compiled policy remains executable after empirical construction input is gone.
    expected = plan(result.compiled)
    model.rows.clear()
    assert plan(result.compiled) == expected


def test_empty_query_bank_is_not_reported_as_consistent():
    model = FiniteModel({0: 0}, {0: "CUTOFF"}, {}, (0,))
    with pytest.raises(ValueError, match="nonempty query bank"):
        build_refined_quotient(model, {})
