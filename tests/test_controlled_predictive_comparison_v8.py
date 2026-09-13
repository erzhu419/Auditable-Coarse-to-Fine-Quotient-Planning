from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from acfqp.science import controlled_predictive_comparison_v8 as comparison
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_cohort_v7 import V7Case
from acfqp.science.controlled_predictive_encoder_runtime_v8 import RuntimeEncoder
from acfqp.science.controlled_predictive_encoder_v7 import EncoderFit
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


def _cases():
    return tuple(V7Case(name=name, group=name, family=family, variant="0", board=(offset,) + (0,) * 15,
        horizon=2, role=role, split=role, source="test")
        for name, family, offset, role in (("a", "A", 0, "TRAIN"), ("b", "B", 5, "TRAIN"),
            ("c", "C", 10, "TRAIN"), ("target", "A", 15, "FIT_HELD_OUT_DEVELOPMENT")))


def _roster(cases=None):
    cases = _cases() if cases is None else cases
    return {"scenarios": [
        {"name": "PRIMARY_V7_SPLIT", "source_case_names": ["a", "b", "c"],
         "evaluation_case_names": [case.name for case in cases], "target_family": None,
         "case_splits": {case.name: case.split for case in cases}},
        {"name": "LOFO_A", "source_case_names": ["b", "c"],
         "evaluation_case_names": ["b", "c", "a", "target"], "target_family": "A",
         "case_splits": {"b": "TRAIN", "c": "TRAIN", "a": "FAMILY_HELD_OUT", "target": "FAMILY_HELD_OUT"}},
    ]}


def _fake_fit(training, **kwargs):
    source = training[0].name
    return EncoderFit(RuntimeEncoder({}), {
        "all_training_predictive_constraints_satisfied": False,
        "recursive_empirical_equivalence_supported": False,
        "unresolved_signature_pairs": 1,
        "groups": [{"identical_feature_collision_witness": {
            "left": {"source_model": source, "source_state": 1},
            "right": {"source_model": source, "source_state": 2}}}],
    })


def _fake_compile(empirical, boards, encoder):
    return SimpleNamespace(compiled=comparison.compile_full_state(empirical),
                           code_to_cell={}, diagnostics={"states_encoded": len(boards)})


def _setup(monkeypatch):
    closures = {case.name: _closure(case.board[0]) for case in _cases()}
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: closures[next(iter(kwargs["boards"]))])
    monkeypatch.setattr(comparison, "fit_encoder", _fake_fit)
    monkeypatch.setattr(comparison, "fit_uncapped_sse_encoder", _fake_fit)
    monkeypatch.setattr(comparison, "fit_constraint_encoder", _fake_fit)
    monkeypatch.setattr(comparison, "compile_encoded", _fake_compile)
    return closures


def test_source_subset_fits_share_one_bank_and_six_frozen_plans_precede_truth(monkeypatch):
    """Cross-scenario reuse must not leak held-out sources or redraw current evidence."""
    closures = _setup(monkeypatch)
    events, fit_inputs, frozen_models, sampled_models = [], [], [], []
    sample, freeze, reference = comparison.sample_model, comparison._freeze_arm, comparison._reference
    exact_names = {id(closure.model): name for name, closure in closures.items()}

    def sampling(model, **kwargs):
        events.append(("sample", exact_names[id(model)], kwargs["seed"]))
        empirical = sample(model, **kwargs)
        sampled_models.append(empirical)
        return empirical

    def fit(method):
        def wrapper(training, **kwargs):
            events.append(("fit", method, tuple(item.name for item in training)))
            fit_inputs.append((method, training, kwargs))
            return _fake_fit(training, **kwargs)
        return wrapper

    def freezing(name, empirical, closure, encoder, queries):
        events.append(("freeze", name))
        frozen_models.append(empirical)
        return freeze(name, empirical, closure, encoder, queries)

    def truth(*args, **kwargs):
        assert [event[0] for event in events[-6:]] == ["freeze"] * 6
        events.append(("truth",))
        return reference(*args, **kwargs)

    monkeypatch.setattr(comparison, "sample_model", sampling)
    monkeypatch.setattr(comparison, "fit_encoder", fit("v7"))
    monkeypatch.setattr(comparison, "fit_uncapped_sse_encoder", fit("sse"))
    monkeypatch.setattr(comparison, "fit_constraint_encoder", fit("constraint"))
    monkeypatch.setattr(comparison, "_freeze_arm", freezing)
    monkeypatch.setattr(comparison, "_reference", truth)
    report = comparison.run_comparison_v8(cases=_cases(), cohort_roster=_roster(), samples_per_row=8,
        sample_seeds=(123, 124), fit_queries={"reward": Query()}, probe_queries={"risk": Query(1, 1, 0)})
    assert report["status"] == "DEVELOPMENT_COMPLETE"
    assert report["completed_scenario_case_seed_runs"] == 16
    assert report["accounting"]["bank_model_count"] == 8
    assert report["accounting"]["actual_physical_draws"] == 8 * 6 * 8
    assert report["accounting"]["scenario_case_logical_draws_including_repeated_bank_reads"] == 16 * 6 * 8
    assert report["accounting"]["scenario_additional_physical_draws"] == 0
    assert report["accounting"]["encoder_fit_count"] == 12
    assert len(fit_inputs) == 12
    assert {tuple(item.name for item in items) for _, items, _ in fit_inputs} == {("a", "b", "c"), ("b", "c")}
    assert all(kwargs == ({"max_depth": 4, "min_leaf": 2} if method == "v7" else {})
               for method, _, kwargs in fit_inputs)
    assert all(item.empirical is not closures[item.name].model for _, items, _ in fit_inputs for item in items)
    assert {id(model) for model in frozen_models} == {id(model) for model in sampled_models}
    assert all(all(model is frozen_models[index] for model in frozen_models[index:index + 6])
               for index in range(0, len(frozen_models), 6))
    for seed in (123, 124):
        target_index = events.index(("sample", "target", seed))
        source_start = events.index(("sample", "a", seed))
        assert sum(event[0] == "fit" for event in events[source_start:target_index]) == 6
        assert not any(event[0] == "truth" for event in events[source_start:target_index])
    assert report["lofo_target_aggregate"]["declared_case_count"] == 2
    assert report["lofo_target_aggregate"]["arms"]["full_state_empirical"]["query_groups"]["ALL"]["query_evaluation_count"] == 8
    for scenario in report["scenarios"]:
        assert all(not learner["diagnostics"]["all_training_predictive_constraints_satisfied"]
            for fit_record in scenario["encoder_fits"] for learner in fit_record["learners"].values())
        for record in scenario["cases"]:
            for run in record["sampled_runs"]:
                assert set(run["arms"]) == set(comparison.ARM_NAMES)
                assert set(run["matched_comparisons"]) == set(comparison.ARM_NAMES[1:])
                assert set(run["worst_encoding_added_loss_by_arm"]) == set(comparison.LEARNER_NAMES)
                assert run["matched_comparisons"]["exact_empirical_quotient"]["risk"]["maximum_all_state_extra_regret_over_full_state"] == pytest.approx(0)
    json.dumps(report, allow_nan=False)


def test_each_source_fit_cost_is_amortized_once_and_standalone_source_is_not_double_counted(monkeypatch):
    """Repeated folds and source-as-target evaluation must not hide or duplicate fit cost."""
    closures = _setup(monkeypatch)
    report = comparison.run_comparison_v8(cases=_cases(), cohort_roster=_roster(), samples_per_row=4,
        sample_seeds=(123,), fit_queries={"reward": Query()}, probe_queries={})
    samples = {row["case_name"]: row["sampling_seconds"] for row in report["empirical_bank"]}
    for scenario in report["scenarios"]:
        sources = scenario["scenario"]["source_case_names"]
        fits = scenario["encoder_fits"][0]["learners"]
        for learner in comparison.LEARNER_NAMES:
            fit_seconds = fits[learner]["encoder_fit_seconds"]
            workloads = [record["sampled_runs"][0]["arms"][learner]["measured_cumulative_workloads"][-1]
                         for record in scenario["cases"]]
            assert sum(row["amortized_source_encoder_fit_seconds"] for row in workloads) == pytest.approx(fit_seconds)
            for record, row in zip(scenario["cases"], workloads):
                name = record["case"]["name"]
                expected = fit_seconds + sum(closures[source].elapsed_seconds + samples[source] for source in sources if source != name)
                assert row["standalone_additional_source_acquisition_and_fit_seconds"] == pytest.approx(expected)
        for record in scenario["cases"]:
            arms = record["sampled_runs"][0]["arms"]
            assert arms["action_outcome_shuffle_encoder"]["source_fit_learner"] == "frozen_rule_encoder"
            assert arms["full_state_empirical"]["measured_cumulative_workloads"][-1]["standalone_additional_source_acquisition_and_fit_seconds"] == 0


def test_source_closure_failure_blocks_only_affected_scenario_and_retains_denominators(monkeypatch):
    """A missing source cannot silently change a learner, while another complete fold remains runnable."""
    closures = _setup(monkeypatch)
    def closure(**kwargs):
        name = next(iter(kwargs["boards"]))
        if name == "a":
            raise ValueError("complete closure exceeds max_nodes=1; no truncated model produced")
        return closures[name]
    monkeypatch.setattr(comparison, "build_development_closure", closure)
    report = comparison.run_comparison_v8(cases=_cases(), cohort_roster=_roster(), samples_per_row=4,
        sample_seeds=(123,), fit_queries={"reward": Query()}, probe_queries={})
    primary, lofo = report["scenarios"]
    assert primary["source_closure_failure"] and not primary["encoder_fits"]
    assert len(primary["cases"]) == 4 and all(not row["sampled_runs"] for row in primary["cases"])
    assert len(lofo["cases"]) == 4 and len(lofo["encoder_fits"]) == 1
    assert [row["status"] for row in lofo["cases"]] == ["COMPLETE", "COMPLETE", "CLOSURE_BUDGET_EXCEEDED", "COMPLETE"]
    assert report["lofo_target_aggregate"]["declared_case_count"] == 2
    assert report["lofo_target_aggregate"]["completed_case_count"] == 1
    assert report["accounting"]["actual_physical_draws"] == 3 * 6 * 4
    assert report["accounting"]["encoder_fit_count"] == 3


def test_fold_source_from_target_family_is_rejected_before_any_closure(monkeypatch):
    """A mislabeled LOFO source would invalidate the intended family holdout."""
    roster = _roster()
    roster["scenarios"][1]["source_case_names"] = ["a", "c"]
    roster["scenarios"][1]["case_splits"]["a"] = "TRAIN"
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: pytest.fail("invalid fold executed"))
    with pytest.raises(ValueError, match="held-out target family"):
        comparison.run_comparison_v8(cases=_cases(), cohort_roster=roster)


def test_training_collision_witness_labels_come_from_existing_current_source_audit(monkeypatch):
    """Empirical feature collisions need true action labels without extra closure generation."""
    _setup(monkeypatch)
    report = comparison.run_comparison_v8(cases=_cases(), cohort_roster=_roster(), samples_per_row=4,
        sample_seeds=(123,), fit_queries={"reward": Query()}, probe_queries={"risk": Query(1, 1, 0)})
    first = report["scenarios"][0]["cases"][0]["sampled_runs"][0]
    labels = first["training_feature_collision_exact_labels_by_arm"]["frozen_rule_encoder"]
    assert set(labels) == {1, 2}
    assert labels[1]["queries"]["risk"]["exact_optimal_actions"] == ("B",)
    assert labels[2]["queries"]["risk"]["exact_optimal_actions"] == ("A",)
    assert labels[1]["source_model"] == "a" and labels[1]["remaining_horizon"] == 1
    heldout = report["scenarios"][1]["cases"][2]["sampled_runs"][0]
    assert heldout["training_feature_collision_exact_labels_by_arm"] == {}


def test_matched_comparisons_keep_capacity_control_added_loss_and_improvements():
    """Capacity-control error must be measured by actual objective, not predictions."""
    def row(values):
        return {"policy": {0: "A", 1: "B"}, "actual": {
            state: {"value": value, "reward": value, "failure": 0, "success": 0}
            for state, value in enumerate(values)}}
    private = {name: {"q": row((1, 2) if index == 0 else (.7, 2.4))}
               for index, name in enumerate(comparison.ARM_NAMES)}
    result = comparison.matched_comparisons(private, (0, 1), 0, {"q": Query()})
    assert set(result) == set(comparison.ARM_NAMES[1:])
    assert result["uncapped_sse_encoder"]["q"]["root_extra_regret_over_full_state"] == pytest.approx(.3)
    assert result["uncapped_sse_encoder"]["q"]["minimum_all_state_extra_regret_over_full_state"] == pytest.approx(-.4)


def test_fixed_primary_constraint_artifact_exports_without_ground_maps(monkeypatch):
    """The fixed real-campaign export branch must resolve its API before launch."""
    _setup(monkeypatch)
    cases = tuple(replace(case, name="v6_spawn_edge_rescue_2", group="example") if case.name == "target" else case for case in _cases())
    roster = _roster(cases)
    roster["scenarios"] = roster["scenarios"][:1]
    closures = {case.name: _closure(case.board[0]) for case in cases}
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: closures[next(iter(kwargs["boards"]))])
    report = comparison.run_comparison_v8(cases=cases, cohort_roster=roster, samples_per_row=4,
        sample_seeds=(832101,), fit_queries={"reward": Query()}, probe_queries={})
    example = report["compiled_model_example"]
    assert example["scenario"] == "PRIMARY_V7_SPLIT" and example["case_name"] == "v6_spawn_edge_rescue_2"
    assert "state_to_cell" not in example["artifact"]["compiled_model"]
    assert all(len(cell) == 3 for cell in example["artifact"]["compiled_model"]["cells"])
    assert example["queries"]["reward"]["expected_root_action"] == report["scenarios"][0]["cases"][-1]["sampled_runs"][0]["arms"]["frozen_rule_encoder"]["queries"]["reward"]["root_action"]
