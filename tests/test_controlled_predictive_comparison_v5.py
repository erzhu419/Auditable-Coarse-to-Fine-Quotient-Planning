from dataclasses import replace
import json

import pytest

from acfqp.science import controlled_predictive_comparison_v5 as comparison
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query


def _closure() -> DevelopmentClosure:
    model = FiniteModel(
        layers={0: 2, 1: 1, 2: 1, 3: 0, 4: 0},
        terminal={0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "LOST", 4: "CUTOFF"},
        rows={(0, "CONTINUE"): (Outcome(1, 1, 0),),
              (1, "REWARD"): (Outcome(0.5, 3, 0.01), Outcome(0.5, 4, 0.01)),
              (1, "SAFE"): (Outcome(1, 4, 0),),
              (2, "REWARD"): (Outcome(1, 4, 0.01),),
              (2, "SAFE"): (Outcome(1, 4, 0),)}, roots=(0,),
    )
    return DevelopmentClosure(model, {state: (state,) for state in model.layers}, ("fixture",),
        {"states": 5, "active_states": 3, "exact_transition_row_calls": 5,
         "exact_outcomes_enumerated": 6}, 0.25)


def _case() -> comparison.RefinementCase:
    return comparison.RefinementCase("fixture", "fixture", "TEST", (1,) * 16, "test", 1, 2)


def test_prefix_branches_copy_pilot_and_nested_draws_match() -> None:
    """Different row allocations must not alter the matched per-row RNG prefix."""
    model = _closure().model
    pilot = comparison.RowSampler(model, 123)
    pilot.advance({key: 8 for key in model.rows})
    left, _ = pilot.fork()
    right, _ = pilot.fork()
    left.advance({key: 16 for key in model.rows})
    right.advance({key: 32 if key == (1, "REWARD") else 8 for key in model.rows})
    left_model, left_info = left.advance({key: 32 for key in model.rows})
    right_model, right_info = right.advance({key: 32 for key in model.rows})
    assert left_model.rows == right_model.rows
    assert left.counts == right.counts
    assert pilot.physical_draws == 8 * len(model.rows)
    assert left.physical_draws == right.physical_draws == (32 - 8) * len(model.rows)
    assert left_info["logical_draws_in_current_model"] == right_info["logical_draws_in_current_model"] == 32 * len(model.rows)
    with pytest.raises(ValueError, match="extend"):
        left.advance({key: 16 for key in model.rows})


def test_pilot_only_allocation_and_all_plans_frozen_before_truth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Probe/exact labels or later samples in allocation would invalidate treatment."""
    closure = _closure()
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: closure)
    allocate, freeze, reference = comparison.plan_allocations, comparison._freeze_arm, comparison._reference
    events, allocation_inputs = [], []

    def wrapped_allocate(empirical, counts, queries, **kwargs):
        events.append("allocate")
        allocation_inputs.append((empirical, dict(counts), dict(queries)))
        return allocate(empirical, counts, queries, **kwargs)

    def wrapped_freeze(*args, **kwargs):
        events.append("freeze")
        return freeze(*args, **kwargs)

    def wrapped_reference(*args, **kwargs):
        events.append("truth")
        return reference(*args, **kwargs)

    monkeypatch.setattr(comparison, "plan_allocations", wrapped_allocate)
    monkeypatch.setattr(comparison, "_freeze_arm", wrapped_freeze)
    monkeypatch.setattr(comparison, "_reference", wrapped_reference)
    bank = {"reward": Query(1, 0, 0), "risk": Query(1, 1, 0)}
    report = comparison.run_comparison_v5(cases=(_case(),), fit_queries=bank,
        probe_queries={"probe": Query(1, 0.5, 0)}, sample_seeds=(123, 124),
        budgets=(8, 32), pilot_samples=4)
    assert events == ["allocate", *(["freeze"] * 4), "allocate", *(["freeze"] * 4), "truth"]
    assert len(allocation_inputs) == 2
    assert all(empirical is not closure.model and set(counts.values()) == {4} and queries == bank
               for empirical, counts, queries in allocation_inputs)
    record = report["cases"][0]
    assert record["exact_all_state_required_switches"]["ALL"]["states_with_required_switch"] == 1
    assert report["status"] == "DEVELOPMENT_COMPLETE"
    json.dumps(report, allow_nan=False)
    for run in record["sampled_runs"]:
        assert run["physical_draw_accounting"]["total_actual_draw_calls"] == (2 * 32 - 4) * 5
        for budget in (8, 32):
            stage = run["budgets"][str(budget)]
            assert stage["logical_draw_budget_per_arm"] == budget * 5
            for arm in stage["arms"].values():
                assert sum(arm["row_sample_counts_in_declared_row_order"]) == budget * 5
                assert min(arm["row_sample_counts_in_declared_row_order"]) >= budget // 2
                assert arm["model_build_count"] == 1
                assert arm["query_count_using_same_compiled_model"] == 3
                for row in arm["same_sample_full_state_comparator"]["queries"].values():
                    assert row["maximum_all_state_extra_regret_over_full_state"] == pytest.approx(0)
                    assert row["maximum_empirical_optimal_value_difference"] == pytest.approx(0)
            assert stage["arms"]["UNIFORM"]["measured_cumulative_workloads"][-1]["one_time_allocation_seconds_including_pilot_planning"] == 0
            directed = stage["arms"]["DIRECTED"]["measured_cumulative_workloads"][-1]
            assert directed["one_time_allocation_seconds_including_pilot_planning"] == run["allocation_seconds"] > 0
            assert directed["including_shared_closure_sample_allocate_build_plan_forecast_audit_seconds"] == pytest.approx(
                0.25 + directed["shared_pilot_and_branch_sampling_seconds"]
                + run["allocation_seconds"] + directed["construction_plus_planning_seconds"]
                + directed["cumulative_forecast_seconds"] + directed["cumulative_ground_audit_seconds"])


def test_pilot_flags_against_exact_sets_preserve_correct_but_uncertain_cases() -> None:
    """A flagged correct choice is not mislabeled as a false uncertainty claim."""
    closure = _closure()
    queries = {"risk": Query(1, 1, 0)}
    references = comparison._reference(closure, comparison.compile_full_state(closure.model), queries)
    report = comparison.pilot_ranking_audit((
        {"query": "risk", "state": 1, "best_action": "REWARD", "competitor_action": "SAFE", "ambiguous": False},
        {"query": "risk", "state": 2, "best_action": "REWARD", "competitor_action": "SAFE", "ambiguous": True},
    ), closure, references, queries)
    assert report["all_state_decision_counts"]["unflagged_and_wrong"] == 1
    assert report["all_state_decision_counts"]["flagged_and_correct"] == 1
    assert report["largest_true_rank_reversal_witnesses"][0]["state"] == 1


def test_allocation_row_budget_and_nested_prefix_violations_stop_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Budget drift must not silently enter an equal-budget comparison."""
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: _closure())
    original = comparison.plan_allocations

    def unequal(*args, **kwargs):
        result = original(*args, **kwargs)
        result.allocations[8][(0, "CONTINUE")] += 1
        return result

    monkeypatch.setattr(comparison, "plan_allocations", unequal)
    with pytest.raises(AssertionError, match="logical budget"):
        comparison.run_comparison_v5(cases=(_case(),), fit_queries={"reward": Query()},
            probe_queries={}, sample_seeds=(123,), budgets=(8, 32), pilot_samples=4)


def test_budget_exclusions_retained_without_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """A declared over-budget closure must remain in the denominator."""
    monkeypatch.setattr(comparison, "plan_allocations", lambda *args, **kwargs: pytest.fail("excluded case allocated"))
    report = comparison.run_comparison_v5(cases=(_case(),), max_nodes=1,
        fit_queries={"reward": Query()}, probe_queries={}, sample_seeds=(123,), budgets=(8, 32), pilot_samples=4)
    assert report["cases"][0]["status"] == "CLOSURE_BUDGET_EXCEEDED"
    assert report["case_count"] == 1
    assert report["summary_by_source_group"]["fixture"]["declared_case_count"] == 1


def test_measured_arm_order_rotates_between_doses_and_seeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timing comparisons must not always give one arm the first execution slot."""
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: _closure())
    report = comparison.run_comparison_v5(cases=(_case(), replace(_case(), name="second", group="second")),
        fit_queries={"reward": Query()}, probe_queries={}, sample_seeds=(123,), budgets=(8, 32), pilot_samples=4)
    orders = [record["sampled_runs"][0]["budgets"][str(budget)]["measured_arm_order"]
              for record in report["cases"] for budget in (8, 32)]
    assert orders == [("UNIFORM", "DIRECTED"), ("DIRECTED", "UNIFORM"),
                      ("DIRECTED", "UNIFORM"), ("UNIFORM", "DIRECTED")]


def test_closure_overlap_counts_boards_and_horizons_without_new_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Root-only provenance must not conceal shared descendant states."""
    closures = []

    def build(**kwargs):
        closure = _closure()
        if closures:
            # Same raw boards; two are reached at different remaining horizons.
            closure = replace(closure, boards={**closure.boards, 0: (1,), 1: (0,)})
        closures.append(closure)
        return closure

    monkeypatch.setattr(comparison, "build_development_closure", build)
    cases = (_case(), replace(_case(), name="other", group="other", split="EXPOSED_ROOT_REUSE"))
    report = comparison.run_comparison_v5(cases=cases,
        fit_queries={"reward": Query()}, probe_queries={}, sample_seeds=(123,), budgets=(8, 32), pilot_samples=4)
    overlap = report["within_cohort_closure_overlap"]
    assert len(closures) == 2
    assert overlap["additional_closure_or_query_calls"] == 0
    assert overlap["raw_boards_excluding_horizon"] == {
        "unique_count": 5, "cross_case_count": 5, "cross_source_group_count": 5, "cross_split_count": 5}
    assert overlap["board_and_remaining_horizon"] == {
        "unique_count": 7, "cross_case_count": 3, "cross_source_group_count": 3, "cross_split_count": 3}
    assert overlap["nonempty_cross_case_pairs"][0]["board_and_remaining_horizon_count"] == 3
    assert [record["case"]["split"] for record in report["cases"]] == ["TEST", "EXPOSED_ROOT_REUSE"]
