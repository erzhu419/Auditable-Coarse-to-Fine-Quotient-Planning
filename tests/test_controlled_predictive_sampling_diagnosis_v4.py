from __future__ import annotations

from collections import defaultdict

import pytest

from acfqp.science import controlled_predictive_sampling_diagnosis_v4 as sampling
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query


def _model() -> FiniteModel:
    return FiniteModel(
        {0: 2, 1: 1, 2: 0, 3: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "LOST", 3: "CUTOFF"},
        {(0, "CONTINUE"): (Outcome(1, 1, 0),),
         (1, "RISK"): (Outcome(0.5, 2, 0.25), Outcome(0.5, 3, 0.25)),
         (1, "SAFE"): (Outcome(1, 3, 0),)}, (0,),
    )


def test_nested_sampler_defers_future_draws_and_preserves_each_row_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """An early dose must not consume later observations or move other row streams."""
    original = sampling.random.Random.choices
    draws = []

    def tracked(self, population, weights, *, k):
        draws.append(k)
        return original(self, population, weights, k=k)

    monkeypatch.setattr(sampling.random.Random, "choices", tracked)
    curve = sampling.nested_sample_curve(_model(), (8, 32), 123)
    small_n, small, small_counts = next(curve)
    assert draws == [8, 8, 8]
    large_n, large, large_counts = next(curve)
    assert draws == [8, 8, 8, 24, 24, 24]
    assert small_counts["cumulative_draws"] == 24
    assert large_counts["incremental_draws"] == 72
    assert large_counts["cumulative_draws"] == 96
    direct = next(sampling.nested_sample_curve(_model(), (32,), 123))[1]
    assert direct.rows == large.rows
    for key, row in small.rows.items():
        later = {(item.next_state, item.reward): round(item.probability * large_n) for item in large.rows[key]}
        for item in row:
            assert later[item.next_state, item.reward] >= round(item.probability * small_n)


def test_error_decomposition_separates_future_decision_from_root_kernel() -> None:
    """The only root action can still hide loss caused by an unobserved future failure."""
    exact = _model()
    empirical = FiniteModel(dict(exact.layers), dict(exact.terminal),
        {**exact.rows, (1, "RISK"): (Outcome(1, 3, 0.25),)}, exact.roots)
    diagnosis = sampling.decompose_policy_error(exact, empirical, Query(1, 1, 0))
    assert diagnosis["root_action_gap"] == pytest.approx(0)
    assert diagnosis["root_continuation_loss"] == pytest.approx(0.25)
    root = diagnosis["root_actions"]["CONTINUE"]
    assert root["signed_local_kernel_bias"]["value"] == pytest.approx(0)
    assert root["signed_continuation_prediction_bias"]["value"] == pytest.approx(0.5)
    assert root["row_error"]["true_immediate_failure_probability"] == 0
    contributor, = diagnosis["positive_reachable_decision_contributors"]
    assert contributor["state"] == 1
    assert contributor["action_rows"]["RISK"]["row_error"]["missed_true_probability_mass"] == 0.5
    assert diagnosis["sum_reach_weighted_local_gaps"] == pytest.approx(diagnosis["root_total_regret"])
    for row in diagnosis["root_actions"].values():
        for component in sampling.COMPONENTS:
            difference = row["predicted_frozen_continuation"][component] - row["true_optimal_continuation"][component]
            assert difference == pytest.approx(sum(row[field][component] for field in (
                "signed_continuation_policy_difference", "signed_local_kernel_bias", "signed_continuation_prediction_bias")))


def test_curve_pairs_identical_empirical_kernels_and_audits_all_states(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resampling a comparator or auditing only roots would invalidate this comparison."""
    model = _model()
    closure = DevelopmentClosure(model, {state: (state,) for state in model.layers}, ("test",),
        {"states": 4, "active_states": 2, "exact_transition_row_calls": 3, "exact_outcomes_enumerated": 4}, 0.1)
    monkeypatch.setattr(sampling, "build_development_closure", lambda **kwargs: closure)
    original_full, original_quotient = sampling.compile_full_state, sampling.build_quotient
    inputs = defaultdict(list)

    def full(model):
        inputs["full"].append(model)
        return original_full(model)

    def quotient(model):
        inputs["quotient"].append(model)
        return original_quotient(model)

    monkeypatch.setattr(sampling, "compile_full_state", full)
    monkeypatch.setattr(sampling, "build_quotient", quotient)
    case = sampling.RefinementCase("test", "test", "NEW_DEVELOPMENT", (1,) * 16, "test", 1, 2)
    result = sampling.run_sampling_curve(cases=(case,), budgets=(8, 32), sample_seeds=(123,))
    assert all(left is right for left, right in zip(inputs["full"][1:], inputs["quotient"]))
    doses = result["cases"][0]["sampled_runs"][0]["doses"]
    for dose in doses:
        assert dose["maximum_true_component_difference_between_matched_arms"] <= 1e-10
        for arm in dose["arms"].values():
            assert all(row["active_states"] == 2 for row in arm["queries"].values())
    assert result["actual_unique_curve_draws"] == 96


def test_cohort_retains_two_exposed_sources_and_four_fixed_new_sources() -> None:
    cases = sampling.sampling_cases()
    assert len(cases) == 6
    assert tuple(case.name for case in cases[:2]) == sampling.EXPOSED_NAMES
    assert all(case.split == "EXPOSED_SAMPLING_DIAGNOSIS" for case in cases[:2])
    assert {case.seed for case in cases[2:]} == {837101, 837201, 837102, 837202}
    assert all(case.split == "NEW_DEVELOPMENT" and case.horizon == 3 for case in cases[2:])
