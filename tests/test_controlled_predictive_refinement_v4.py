import pytest

from acfqp.science.controlled_predictive_quotient_v1 import (
    FiniteModel, Outcome, Query, _evaluate_policy, plan,
)
from acfqp.science.controlled_predictive_refinement_v3 import build_refined_quotient
from acfqp.science.controlled_predictive_refinement_v4 import build_refined_quotient_v4


def _partition(compiled):
    return {frozenset(cell.members) for cell in compiled.cells.values()}


def _assert_same_result(model, queries):
    old = build_refined_quotient(model, queries)
    new = build_refined_quotient_v4(model, queries)
    assert _partition(new.compiled) == _partition(old.compiled)
    assert new.diagnostics["refinement_rounds"] == old.diagnostics["refinement_rounds"]
    for query in queries.values():
        old_plan, new_plan = plan(old.compiled, query), plan(new.compiled, query)
        old_policy = {s: old_plan.policy[old.compiled.state_to_cell[s]]
                      for s in model.layers if model.terminal[s] == "ACTIVE"}
        new_policy = {s: new_plan.policy[new.compiled.state_to_cell[s]]
                      for s in model.layers if model.terminal[s] == "ACTIVE"}
        assert new_policy == old_policy
        for state in model.layers:
            assert new_plan.values[new.compiled.state_to_cell[state]] == pytest.approx(
                old_plan.values[old.compiled.state_to_cell[state]], abs=1e-12)
        old_audit = _evaluate_policy(model.terminal, model.rows, tuple(model.layers), old_policy, query)
        new_audit = _evaluate_policy(model.terminal, model.rows, tuple(model.layers), new_policy, query)
        assert new_audit.root_metrics == old_audit.root_metrics
    assert all(value <= 1e-10 for value in new.diagnostics["final_worst_errors"].values())
    return old, new


def test_delayed_risk_refines_upstream_after_successor_signatures_change_and_caches_unrelated_branch():
    # The first round can split only states 2/3. The 0/1 signatures become
    # distinct in round two. States 6/7 form an unaffected disconnected branch.
    model = FiniteModel(
        {0: 2, 1: 2, 2: 1, 3: 1, 4: 0, 5: 0, 6: 2, 7: 1},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "ACTIVE", 4: "LOST",
         5: "CUTOFF", 6: "ACTIVE", 7: "ACTIVE"},
        {(0, "go"): (Outcome(1, 2, 0),), (1, "go"): (Outcome(1, 3, 0),),
         (2, "go"): (Outcome(0.1, 4, 0.004), Outcome(0.9, 5, 0.004)),
         (3, "go"): (Outcome(1, 5, 0),),
         (6, "steady"): (Outcome(1, 7, 1),), (7, "steady"): (Outcome(1, 5, 1),)},
        (0, 1, 6),
    )
    old, new = _assert_same_result(model, {"reward": Query(), "risk": Query(failure_penalty=1)})
    assert new.diagnostics["refinement_rounds"] == 2
    for category in ("planning", "compiled_policy_evaluation", "empirical_policy_evaluation",
                     "greedy_scan", "partition_recompilation"):
        assert new.diagnostics["work_counts"][category]["state_action_rows"] < (
            old.diagnostics["work_counts"][category]["state_action_rows"])
    assert new.diagnostics["iterations"][1]["recomputed_states"] == 4
    assert new.diagnostics["iterations"][2]["recomputed_states"] == 2
    assert new.diagnostics["work_counts"]["dependency_metadata"]["graph_rows_read"] > 0
    assert new.diagnostics["work_counts"]["cached_error_summary"]["state_error_records_read"] > 0


def test_simultaneous_splits_rebuild_all_children_of_a_split_predecessor():
    # Immediate rewards already distinguish upstream signatures, so both
    # layers split simultaneously and every new predecessor row needs remapping.
    model = FiniteModel(
        {0: 2, 1: 2, 2: 1, 3: 1, 4: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "ACTIVE", 4: "CUTOFF"},
        {(0, "go"): (Outcome(1, 2, 0.004),), (1, "go"): (Outcome(1, 3, 0),),
         (2, "go"): (Outcome(1, 4, 0.004),), (3, "go"): (Outcome(1, 4, 0),)}, (0, 1),
    )
    _, new = _assert_same_result(model, {"reward": Query()})
    assert new.diagnostics["refinement_rounds"] == 1
    assert new.compiled.rows[new.compiled.state_to_cell[0], "go"][0].next_state == new.compiled.state_to_cell[2]
    assert new.compiled.rows[new.compiled.state_to_cell[1], "go"][0].next_state == new.compiled.state_to_cell[3]


def test_all_action_dependencies_repair_a_previously_unused_action():
    model = FiniteModel(
        {0: 2, 1: 2, 2: 1, 3: 1, 4: 1, 5: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "ACTIVE", 4: "ACTIVE", 5: "CUTOFF"},
        {(0, "a_safe"): (Outcome(1, 4, 0),), (0, "b_try"): (Outcome(1, 2, 0),),
         (1, "a_safe"): (Outcome(1, 4, 0),), (1, "b_try"): (Outcome(1, 3, 0),),
         (2, "go"): (Outcome(1, 5, 0.008),), (3, "go"): (Outcome(1, 5, 0),),
         (4, "safe"): (Outcome(1, 5, 0.005),)}, (0, 1),
    )
    _, new = _assert_same_result(model, {"reward": Query()})
    fitted = plan(new.compiled)
    assert fitted.policy[new.compiled.state_to_cell[0]] == "b_try"
    assert fitted.policy[new.compiled.state_to_cell[1]] == "a_safe"


def test_policy_equivalent_inexact_cells_need_no_refinement_or_input_at_planning_time():
    model = FiniteModel(
        {0: 1, 1: 1, 2: 0, 3: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "CUTOFF", 3: "LOST"},
        {(0, "safe"): (Outcome(1, 2, 0.02),), (1, "safe"): (Outcome(1, 2, 0.02),),
         (0, "unused"): (Outcome(1, 2, 0),),
         (1, "unused"): (Outcome(0.1, 3, 0.004), Outcome(0.9, 2, 0.004))}, (0, 1),
    )
    _, new = _assert_same_result(model, {"reward": Query(), "risk": Query(failure_penalty=1)})
    assert new.diagnostics["refinement_rounds"] == 0
    assert new.compiled.state_to_cell[0] == new.compiled.state_to_cell[1]
    expected = plan(new.compiled)
    model.rows.clear()
    assert plan(new.compiled) == expected


def test_empty_query_bank_is_not_accepted():
    model = FiniteModel({0: 0}, {0: "CUTOFF"}, {}, (0,))
    with pytest.raises(ValueError, match="nonempty query bank"):
        build_refined_quotient_v4(model, {})
