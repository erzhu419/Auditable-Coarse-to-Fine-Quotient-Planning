from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp.science import controlled_predictive_comparison_v2 as comparison
from acfqp.science.controlled_predictive_2048_challenges_v2 import ChallengeCase
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure, PUBLIC_DEVELOPMENT_BOARDS
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query


def _case() -> ChallengeCase:
    return ChallengeCase("test_known_board", "test_source", "TRAIN_DEVELOPMENT",
                         PUBLIC_DEVELOPMENT_BOARDS["last_pair_spawn_risk"], "test", 1)


def test_numerical_argmax_flip_does_not_count_as_required_switch() -> None:
    """False switches would turn symmetric tied roots into positive evidence."""
    left = comparison.optimal_action_set({"LEFT": 1.0, "RIGHT": 1.0 + 1e-12})
    right = comparison.optimal_action_set({"LEFT": 1.0 + 1e-12, "RIGHT": 1.0})
    assert left == right == ("LEFT", "RIGHT")
    assert comparison.disjoint_optimal_pairs({"a": left, "b": right}) == []
    assert comparison.disjoint_optimal_pairs({"a": ("LEFT",), "b": ("RIGHT",)}) == [("a", "b")]


def test_exact_continuation_and_measured_matched_reuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Delayed risk must change exact decisions; arms must reuse one sampled kernel."""
    exact = FiniteModel(
        layers={0: 2, 1: 1, 2: 1, 3: 0, 4: 0},
        terminal={0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "LOST", 4: "CUTOFF"},
        rows={
            (0, "LEFT"): (Outcome(1, 1, 0),),
            (0, "RIGHT"): (Outcome(1, 2, 0.1),),
            (1, "CONTINUE"): (Outcome(1, 4, 1),),
            (2, "CONTINUE"): (Outcome(1, 3, 1),),
        }, roots=(0,),
    )
    closure = DevelopmentClosure(exact, {state: (state,) for state in exact.layers},
                                 ("test_known_board",),
                                 {"states": 5, "active_states": 3,
                                  "exact_transition_row_calls": 4, "exact_outcomes_enumerated": 4}, 0.25)
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: closure)
    original_sample = comparison.sample_model
    original_compile = comparison.compile_full_state
    original_fit = comparison.build_quotient
    original_plan = comparison.plan
    sampled, compiled_inputs, fitted_inputs, planned_models = [], [], [], []

    def sample(*args, **kwargs):
        result = original_sample(*args, **kwargs)
        sampled.append(result)
        return result

    def compile_model(model):
        compiled_inputs.append(model)
        return original_compile(model)

    def fit(model, **kwargs):
        fitted_inputs.append(model)
        return original_fit(model, **kwargs)

    def plan_model(model, query):
        planned_models.append(model)
        return original_plan(model, query)

    monkeypatch.setattr(comparison, "sample_model", sample)
    monkeypatch.setattr(comparison, "compile_full_state", compile_model)
    monkeypatch.setattr(comparison, "build_quotient", fit)
    monkeypatch.setattr(comparison, "plan", plan_model)
    report = comparison.run_comparison(cases=(_case(),), horizon=2, samples_per_row=8,
        sample_seeds=(123,), queries={"reward": Query(1, 0, 0), "risk": Query(1, 5, 0)})
    assert report["scientific_gate"] == "NOT_A_FORMAL_GATE"
    assert len(sampled) == 1
    assert compiled_inputs[1] is sampled[0]
    assert fitted_inputs[1] is sampled[0]
    assert len(planned_models) == 10  # Five fitted models, exactly two queries each.
    assert len({id(model) for model in planned_models}) == 5
    case = report["cases"][0]
    refs = case["decision_conflicts"]["exact_query_references"]
    assert refs["reward"]["optimal_actions"] == ("RIGHT",)
    assert refs["risk"]["optimal_actions"] == ("LEFT",)
    assert refs["risk"]["h1_optimal_actions"] == ("RIGHT",)
    assert case["decision_conflicts"]["has_required_risk_only_query_switch"]
    assert case["decision_conflicts"]["has_h1_vs_horizon_disjoint_optima"]
    sample_run = case["sampled_runs"][0]
    assert sample_run["empirical_draws"] == 32
    candidate = sample_run["arms"]["learned_controlled_quotient"]
    assert candidate["all_required_switch_pairs_preserved"]
    for name in ("reward", "risk"):
        assert candidate["queries"][name]["exact_lifted_objective_regret"] == pytest.approx(0)
        assert sample_run["matched_comparisons"][name]["quotient_extra_regret_over_full_state"] == pytest.approx(0)
    workload = candidate["measured_cumulative_workloads"][-1]
    assert workload["query_count"] == 2
    assert workload["cumulative_planning_counts"]["state_action_rows"] == sum(
        row["planning_counts"]["state_action_rows"] for row in candidate["queries"].values())
    assert workload["including_shared_exact_closure_seconds"] == pytest.approx(
        0.25 + sample_run["sampling_seconds"] + candidate["inventory"]["construction_seconds"]
        + sum(row["planning_seconds"] + row["compiled_policy_evaluation_seconds"] + row["ground_audit_seconds"]
              for row in candidate["queries"].values()))
    summary = report["summary_by_split"]["ALL"]["actual_switch_subset"]
    assert summary["declared_source_group_count"] == 1
    assert summary["actual_switch_case_count"] == 1


def test_real_board_overlap_is_reported_without_dropping_candidates() -> None:
    """Split labels must not conceal shared board identities or turn ties into evidence."""
    source = _case()
    other = replace(source, name="same_board_eval", group="other_source", split="EVALUATION")
    report = comparison.run_comparison(cases=(source, other), horizon=1, samples_per_row=8,
        sample_seeds=(123,), queries={"reward": Query(1, 0, 0), "risk": Query(1, 5, 0)})
    assert report["case_count"] == 2
    assert all(case["status"] == "COMPLETE" for case in report["cases"])
    overlap = report["board_identity_overlap_excluding_horizon"]
    assert overlap["root_cross_split_overlap_count"] == 1
    assert overlap["cross_split_covered_board_count"] > 1
    assert not overlap["unseen_state_generalization_demonstrated"]
    assert report["summary_by_split"]["ALL"]["all_declared"]["actual_switch_case_count"] == 0
    for case in report["cases"]:
        for arm in case["references"].values():
            for query in arm["queries"].values():
                assert query["exact_lifted_objective_regret"] == pytest.approx(0)


def test_declared_closure_budget_failure_is_retained() -> None:
    """A large candidate cannot silently disappear from the development denominator."""
    report = comparison.run_comparison(cases=(_case(),), max_nodes=1,
                                        sample_seeds=(123,), queries={"reward": Query()})
    assert report["all_declared_candidates_retained"]
    assert report["cases"][0]["status"] == "CLOSURE_BUDGET_EXCEEDED"
    assert report["summary_by_split"]["ALL"]["all_declared"]["status_counts"] == {"CLOSURE_BUDGET_EXCEEDED": 1}
    assert report["board_identity_overlap_excluding_horizon"]["complete_closure_case_count"] == 0


def test_exposed_custom_case_is_not_mislabeled_as_fresh() -> None:
    """Derived diagnostic states cannot enter the fresh challenge denominator."""
    case = replace(_case(), split="EXPOSED_DECISION_POINT")
    report = comparison.run_comparison(cases=(case,), max_nodes=1,
                                        sample_seeds=(123,), queries={"reward": Query()})
    assert report["fresh_challenge_case_count"] == 0
    assert report["summary_by_split"]["FRESH_CHALLENGES"]["all_declared"]["declared_case_count"] == 0
    assert report["summary_by_split"]["EXPOSED_DECISION_POINT"]["all_declared"]["declared_case_count"] == 1
