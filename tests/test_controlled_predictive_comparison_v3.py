from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp.science import controlled_predictive_comparison_v3 as comparison
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query


def _case() -> comparison.RefinementCase:
    return comparison.RefinementCase("fixture", "fixture", "TEST", (1,) * 16, "test", 1, 2)


def _closure() -> DevelopmentClosure:
    # Every query starts with CONTINUE; reward/risk choices differ only below it.
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
        {"states": 5, "active_states": 3, "exact_transition_row_calls": 5, "exact_outcomes_enumerated": 6}, 0.25)


def test_descendant_conflicts_shared_samples_and_probe_exclusion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Root-only evaluation misses this conflict; probe data must not enter fitting."""
    closure = _closure()
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: closure)
    original_sample, original_fit, original_full = comparison.sample_model, comparison.build_refined_quotient, comparison.compile_full_state
    sampled, fitted, full_inputs = [], [], []

    def sample(*args, **kwargs):
        result = original_sample(*args, **kwargs)
        sampled.append(result)
        return result

    def fit(model, queries, **kwargs):
        fitted.append((model, dict(queries)))
        return original_fit(model, queries, **kwargs)

    def full(model):
        full_inputs.append(model)
        return original_full(model)

    monkeypatch.setattr(comparison, "sample_model", sample)
    monkeypatch.setattr(comparison, "build_refined_quotient", fit)
    monkeypatch.setattr(comparison, "compile_full_state", full)
    fit_bank = {"reward": Query(1, 0, 0), "risk": Query(1, 1, 0)}
    report = comparison.run_refinement_comparison(cases=(_case(),), fit_queries=fit_bank,
        probe_queries={"probe": Query(1, 0.5, 0)}, sample_seeds=(123,), samples_per_row=32)
    assert len(sampled) == 1
    assert full_inputs[1] is sampled[0]
    assert fitted[0][0] is sampled[0]
    assert all(queries == fit_bank for _, queries in fitted)
    assert len(fitted) == 2  # matched candidate and shuffled control, each once
    record = report["cases"][0]
    assert record["exact_root_required_switches"]["ALL"]["states_with_required_switch"] == 0
    assert record["exact_all_state_required_switches"]["ALL"]["states_with_required_switch"] == 1
    sampled_run = record["sampled_runs"][0]
    arm = sampled_run["arms"]["query_refined_quotient"]
    assert arm["model_build_count"] == 1
    assert arm["query_count_using_same_compiled_model"] == 3
    assert arm["all_state_required_switches"]["ALL"]["all_required_switches_preserved"]
    for name in ("reward", "risk", "probe"):
        row = arm["queries"][name]
        assert row["all_active_states"]["maximum_exact_lifted_objective_regret"] == pytest.approx(0)
        assert row["all_state_ground_audit_counts"]["active_states"] == 3
    costs = arm["measured_cumulative_workloads"][-1]
    assert costs["including_shared_closure_sample_build_plan_forecast_audit_seconds"] == pytest.approx(
        0.25 + sampled_run["sampling_seconds"] + arm["inventory"]["construction_seconds"]
        + sum(row["planning_seconds"] + row["all_cell_forecast_seconds"] + row["all_state_ground_audit_seconds"]
              for row in arm["queries"].values()))
    assert report["summary_by_source_group"]["fixture"]["source_group_count"] == 1


def test_frozen_policy_audit_charges_downstream_loss(monkeypatch: pytest.MonkeyPatch) -> None:
    """A correct root action cannot hide a harmful continuation behind reoptimization."""
    closure = _closure()
    exact = comparison.compile_full_state(closure.model)
    query = Query(1, 1, 0)
    references = comparison._reference(closure, exact, {"risk": query})
    solved = comparison.plan(exact, query)
    solved.policy[exact.state_to_cell[1]] = "REWARD"
    row, _ = comparison._evaluate(exact, closure, query, references["risk"], (0, 1, 2), (solved, 0))
    assert row["root_action_in_exact_optimal_set"]
    assert row["exact_lifted_objective_regret"] == pytest.approx(0.49)
    assert row["exact_lifted_root_metrics"]["failure"] == pytest.approx(0.5)
    assert row["all_active_states"]["optimal_full_policy_count"] == 1


def test_budget_exclusion_and_overlap_preserve_source_denominators(monkeypatch: pytest.MonkeyPatch) -> None:
    """Large closures remain declared, and duplicated boards cannot masquerade as transfer."""
    case = _case()
    excluded = comparison.run_refinement_comparison(cases=(case,), max_nodes=1,
        fit_queries={"reward": Query()}, probe_queries={}, sample_seeds=(123,))
    assert excluded["cases"][0]["status"] == "CLOSURE_BUDGET_EXCEEDED"
    assert excluded["summary_by_source_group"]["fixture"]["declared_case_count"] == 1
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: _closure())
    cases = (replace(case, split="EXPOSED_REGRESSION"), replace(case, name="new", group="new", split="NEW_DEVELOPMENT"))
    report = comparison.run_refinement_comparison(cases=cases, fit_queries={"reward": Query()},
        probe_queries={}, sample_seeds=(123,), samples_per_row=8)
    overlap = report["board_identity_overlap_excluding_horizon"]
    assert overlap["root_overlap_count"] == 1
    assert overlap["new_and_exposed_covered_board_count"] == 5
    assert not overlap["unseen_state_generalization_demonstrated"]
    assert report["summary_by_split"]["ALL"]["source_group_count"] == 2


def test_declared_cohort_keeps_exposed_case_separate_from_new_source_seeds() -> None:
    """The execution roster must not consume the deferred V2 cohort or select by outcome."""
    cases = comparison.refinement_cases()
    assert len(cases) == 13
    assert len({case.group for case in cases}) == 13
    assert cases[0].split == "EXPOSED_REGRESSION" and cases[0].horizon == 2
    assert all(case.split == "NEW_DEVELOPMENT" and case.horizon == 3 for case in cases[1:])
    assert {case.seed for case in cases[1:]} == {seed + index for seed in comparison.DEVELOPMENT_SEEDS for index in range(3)}
