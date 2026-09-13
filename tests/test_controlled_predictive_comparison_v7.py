from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from acfqp.science import controlled_predictive_comparison_v7 as comparison
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_comparison_v3 import RefinementCase
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query


def _closure(offset=0):
    model = FiniteModel(layers={0: 2, 1: 1, 2: 1, 3: 0, 4: 0},
        terminal={0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "LOST", 4: "CUTOFF"},
        rows={(0, "A"): (Outcome(1, 1, 0),),
              (0, "B"): (Outcome(1, 2, 0),),
              (1, "A"): (Outcome(.5, 3, .1), Outcome(.5, 4, .1)),
              (1, "B"): (Outcome(1, 4, 0),),
              (2, "A"): (Outcome(1, 4, .1),),
              (2, "B"): (Outcome(1, 4, 0),)}, roots=(0,))
    return DevelopmentClosure(model, {state: (state + offset,) + (0,) * 15 for state in model.layers},
        ("fixture",), {"states": 5, "active_states": 3,
            "exact_transition_row_calls": 6, "exact_outcomes_enumerated": 7}, .25)


def _case(name="train", split="TRAIN", marker=0):
    return RefinementCase(name, name, split, (marker,) + (0,) * 15, "test", 1, 2)


class _Encoder:
    def encode(self, board, remaining_horizon):
        return remaining_horizon, "ACTIVE", ("A", "B"), board[0]

    def to_payload(self):
        return {"fixed": "test encoder"}


def _fake_fit(training, **kwargs):
    return SimpleNamespace(encoder=_Encoder(), diagnostics={"source_count": len(training)})


def _fake_compile(empirical, boards, encoder):
    compiled = comparison.compile_full_state(empirical)
    return SimpleNamespace(compiled=compiled, code_to_cell={}, diagnostics={"states_encoded": len(boards)})


def _fake_encoder(monkeypatch):
    monkeypatch.setattr(comparison, "fit_encoder", _fake_fit)
    monkeypatch.setattr(comparison, "compile_encoded", _fake_compile)
    monkeypatch.setattr(comparison, "FEATURE_NAMES", ())
    monkeypatch.setattr(comparison, "board_features", lambda board: ())


def test_source_only_fit_shared_samples_and_frozen_plans_precede_truth(monkeypatch):
    """Target samples, queries or exact labels entering fit would invalidate transfer."""
    _fake_encoder(monkeypatch)
    train, target = _closure(), _closure(7)
    events, fitted_inputs, frozen_kernels = [], [], []

    def closure(**kwargs):
        name = next(iter(kwargs["boards"]))
        events.append(("closure", name))
        return train if name == "train" else target

    monkeypatch.setattr(comparison, "build_development_closure", closure)
    sample, freeze, reference = comparison.sample_model, comparison._freeze_arm, comparison._reference

    def sampling(model, **kwargs):
        events.append(("sample", "train" if model is train.model else "target"))
        return sample(model, **kwargs)

    def fit(training, **kwargs):
        events.append(("fit", len(training)))
        fitted_inputs.append((training, kwargs))
        return _fake_fit(training, **kwargs)

    def freezing(name, empirical, closure, encoder, queries):
        events.append(("freeze", name))
        frozen_kernels.append(empirical)
        return freeze(name, empirical, closure, encoder, queries)

    def truth(*args, **kwargs):
        assert [event[0] for event in events[-4:]] == ["freeze"] * 4
        events.append(("truth", None))
        return reference(*args, **kwargs)

    monkeypatch.setattr(comparison, "sample_model", sampling)
    monkeypatch.setattr(comparison, "fit_encoder", fit)
    monkeypatch.setattr(comparison, "_freeze_arm", freezing)
    monkeypatch.setattr(comparison, "_reference", truth)
    report = comparison.run_comparison_v7(cases=(_case(), _case("target", "FIT_HELD_OUT_DEVELOPMENT", 7)),
        samples_per_row=8, sample_seeds=(123, 124), fit_queries={"reward": Query()},
        probe_queries={"risk": Query(1, 1, 0)})
    assert events[:4] == [("closure", "train"), ("closure", "target"), ("sample", "train"), ("fit", 1)]
    fit_events = [index for index, event in enumerate(events) if event[0] == "fit"]
    target_samples = [index for index, event in enumerate(events) if event == ("sample", "target")]
    assert len(fit_events) == len(target_samples) == 2
    assert all(fit_index < target_index for fit_index, target_index in zip(fit_events, target_samples))
    assert all(len(training) == 1 and training[0].name == "train" and training[0].empirical is not train.model
        and kwargs == {"max_depth": 4, "min_leaf": 2} for training, kwargs in fitted_inputs)
    assert all(all(kernel is frozen_kernels[index] for kernel in frozen_kernels[index:index + 4])
        for index in range(0, len(frozen_kernels), 4))
    assert report["accounting"]["actual_physical_draws"] == 2 * 2 * 6 * 8
    assert report["accounting"]["actual_physical_draws"] == report["accounting"]["current_case_draws_including_reused_training_kernels"]
    assert [run["training_kernel_reused_without_redrawing"] for run in report["cases"][0]["sampled_runs"]] == [True, True]
    assert report["pre_fit_closure_overlap"]["before_any_encoder_fit"]
    assert report["status"] == "DEVELOPMENT_COMPLETE"
    for record in report["cases"]:
        for run in record["sampled_runs"]:
            for name, arm in run["arms"].items():
                workload = arm["measured_cumulative_workloads"][-1]
                if name in comparison.ARM_NAMES[:2]:
                    assert workload["amortized_source_encoder_fit_seconds"] == 0
                else:
                    assert workload["standalone_additional_source_acquisition_and_fit_seconds"] > 0
                assert arm["query_count_using_same_compiled_model"] == 2
            assert run["matched_comparisons"]["exact_empirical_quotient"]["risk"]["maximum_all_state_extra_regret_over_full_state"] == pytest.approx(0)
    json.dumps(report, allow_nan=False)


def test_training_closure_failure_retains_all_cases_without_partial_fit(monkeypatch):
    """An excluded TRAIN source changes the method, so retain it and do not fit a replacement."""
    _fake_encoder(monkeypatch)
    def closure(**kwargs):
        if "train" in kwargs["boards"]:
            raise ValueError("complete closure exceeds max_nodes=1; no truncated model produced")
        return _closure()
    monkeypatch.setattr(comparison, "build_development_closure", closure)
    monkeypatch.setattr(comparison, "fit_encoder", lambda *args, **kwargs: pytest.fail("partial source pool fitted"))
    report = comparison.run_comparison_v7(cases=(_case(), _case("target", "FIT_HELD_OUT_DEVELOPMENT")),
        sample_seeds=(123,), fit_queries={"reward": Query()}, probe_queries={})
    assert [record["status"] for record in report["cases"]] == ["CLOSURE_BUDGET_EXCEEDED", "NOT_RUN_TRAINING_CLOSURE_INCOMPLETE"]
    assert report["case_count"] == 2 and report["accounting"]["actual_physical_draws"] == 0


def test_target_closure_failure_retained_without_replacement(monkeypatch):
    """A target exceeding closure limits must remain in its split denominator."""
    _fake_encoder(monkeypatch)
    def closure(**kwargs):
        if "target" in kwargs["boards"]:
            raise ValueError("complete closure exceeds max_nodes=1; no truncated model produced")
        return _closure()
    monkeypatch.setattr(comparison, "build_development_closure", closure)
    report = comparison.run_comparison_v7(cases=(_case(), _case("target", "FIT_HELD_OUT_DEVELOPMENT")),
        samples_per_row=4, sample_seeds=(123,), fit_queries={"reward": Query()}, probe_queries={})
    assert [record["status"] for record in report["cases"]] == ["COMPLETE", "CLOSURE_BUDGET_EXCEEDED"]
    assert report["summary_by_split"]["FIT_HELD_OUT_DEVELOPMENT"]["declared_case_count"] == 1
    assert report["accounting"]["actual_physical_draws"] == 6 * 4


def test_additional_regret_is_actual_policy_loss_and_can_be_negative():
    """Differences in prediction error must not be substituted for policy loss."""
    def item(values):
        return {"policy": {0: "A", 1: "B"}, "actual": {
            state: {"value": value, "reward": value, "failure": 0, "success": 0}
            for state, value in enumerate(values)}}
    private = {name: {"q": item((1, 2) if index == 0 else (.7, 2.4))}
               for index, name in enumerate(comparison.ARM_NAMES)}
    row = comparison.matched_comparisons(private, (0, 1), 0, {"q": Query()})["frozen_rule_encoder"]["q"]
    assert row["root_extra_regret_over_full_state"] == pytest.approx(.3)
    assert row["minimum_all_state_extra_regret_over_full_state"] == pytest.approx(-.4)
    assert row["states_worse_than_full_state"] == row["states_better_than_full_state"] == 1


def test_pre_fit_overlap_includes_cross_split_descendants_and_orbits():
    """A new root alone must not conceal overlap among the states used for fitting."""
    train = _closure()
    target = replace(_closure(7), boards={**_closure(7).boards, 1: train.boards[1],
        2: (0,) * 15 + (2,)})
    result = comparison._pre_fit_overlap((_case(), _case("target", "FIT_HELD_OUT_DEVELOPMENT", 7)),
        {"train": train, "target": target})
    overlap = result["case_exposure_to_training_closures"]["target"]
    assert overlap["shared_raw_boards"] == overlap["shared_board_horizon_states"] == 1
    assert overlap["shared_dihedral_board_orbits"] == 2
    assert overlap["active_states_sharing_training_raw_board"] == 1
    assert overlap["active_states_sharing_training_dihedral_orbit"] == 2
    assert result["additional_closure_calls"] == 0 and result["all_overlaps_retained"]


def test_fixed_example_exports_frozen_plans_and_no_registered_state_map(monkeypatch):
    """The actual fixed campaign export path must execute, not remain an untested optional import."""
    _fake_encoder(monkeypatch)
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: _closure())
    report = comparison.run_comparison_v7(cases=(_case("v6_spawn_edge_rescue_2"),),
        samples_per_row=4, sample_seeds=(832101,), fit_queries={"reward": Query()}, probe_queries={})
    example = report["compiled_model_example"]
    assert example["case_name"] == "v6_spawn_edge_rescue_2"
    assert example["queries"]["reward"]["expected_root_action"] == report["cases"][0]["sampled_runs"][0]["arms"]["frozen_rule_encoder"]["queries"]["reward"]["root_action"]
    assert "state_to_cell" not in example["artifact"]["compiled_model"]
    assert all(len(cell) == 3 for cell in example["artifact"]["compiled_model"]["cells"])
    assert len(example["artifact"]["example_input"]["board"]) == 16
    arm = report["cases"][0]["sampled_runs"][0]["arms"]["frozen_rule_encoder"]
    assert arm["inventory"]["portable_encoder_and_model_bytes"]["artifact_total_bytes"] > 0
    assert arm["inventory"]["registered_state_and_board_maps_are_audit_only"]


def test_added_loss_witness_is_not_selected_by_absolute_candidate_regret(monkeypatch):
    """Shared sampling loss at another state must not mask encoding's largest added loss."""
    _fake_encoder(monkeypatch)
    closure = _closure()
    full = {"policy": {0: "A", 1: "B", 2: "A"},
        "actual": {state: {"value": 1, "reward": 1, "failure": 0, "success": 0} for state in range(3)}}
    candidate = {"policy": {0: "B", 1: "A", 2: "A"},
        "actual": {state: {"value": value, "reward": value, "failure": 0, "success": 0}
                   for state, value in enumerate((.6, .9, 1))},
        "regrets": {0: .4, 1: 10.1, 2: 0}}
    result = comparison._worst_encoding_added_loss(
        {"full_state_empirical": {"q": full}, "frozen_rule_encoder": {"q": candidate}},
        closure, {"q": Query()}, _Encoder())
    assert result["state"] == 0 and result["extra_regret"] == pytest.approx(.4)
    assert result["full_state_action"] == "A" and result["candidate_action"] == "B"
