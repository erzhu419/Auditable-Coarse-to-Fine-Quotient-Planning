from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from acfqp.science import controlled_predictive_comparison_v11 as comparison
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_cohort_v7 import V7Case
from acfqp.science.controlled_predictive_encoder_runtime_v8 import RuntimeEncoder
from acfqp.science.controlled_predictive_encoder_v7 import EncoderFit
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query


def _closure(offset=0):
    model = FiniteModel(layers={0: 2, 1: 1, 2: 1, 3: 0, 4: 0},
        terminal={0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "LOST", 4: "CUTOFF"},
        rows={(0, "A"): (Outcome(1, 1, 0),), (0, "B"): (Outcome(1, 2, 0),),
              (1, "A"): (Outcome(.5, 3, .1), Outcome(.5, 4, .1)),
              (1, "B"): (Outcome(1, 4, 0),), (2, "A"): (Outcome(1, 4, .1),),
              (2, "B"): (Outcome(1, 4, 0),)}, roots=(0,))
    return DevelopmentClosure(model, {state: (state + offset,) + (0,) * 15 for state in model.layers},
        ("fixture",), {"states": 5, "active_states": 3,
            "exact_transition_row_calls": 6, "exact_outcomes_enumerated": 7}, .25)


def _cases():
    return tuple(V7Case(name=name, group=name, family=family, variant="0", board=(offset,) + (0,) * 15,
        horizon=2, role=role, split=role, source="test") for name, family, offset, role in (
            ("a", "A", 0, "TRAIN"), ("b", "B", 5, "TRAIN"),
            ("target", "A", 10, "FIT_HELD_OUT_DEVELOPMENT")))


def _roster(cases=None):
    cases = _cases() if cases is None else cases
    return {"scenarios": [
        {"name": "PRIMARY_V7_SPLIT", "source_case_names": ["a", "b"],
         "evaluation_case_names": [case.name for case in cases], "target_family": None,
         "case_splits": {case.name: case.split for case in cases}},
        {"name": "LOFO_A", "source_case_names": ["b"],
         "evaluation_case_names": ["b", "a", "target"], "target_family": "A",
         "case_splits": {"b": "TRAIN", "a": "FAMILY_HELD_OUT", "target": "FAMILY_HELD_OUT"}},
    ]}


def _source_fit(training):
    return EncoderFit(RuntimeEncoder({}), {"all_training_predictive_constraints_satisfied": False})


def _target_build(target):
    return SimpleNamespace(encoder=RuntimeEncoder({}), compiled=comparison.compile_full_state(target.empirical),
        code_to_cell={}, diagnostics={"work_counts": {"final_pooling_passes": 1},
            "all_target_predictive_constraints_satisfied": False,
            "groups": [{"original_output_codes": [{"identical_feature_collision_witness": {
                "left": {"source_model": target.name, "source_state": 1},
                "right": {"source_model": target.name, "source_state": 2}}}]}]})


def _compile(empirical, boards, encoder):
    return SimpleNamespace(compiled=comparison.compile_full_state(empirical), code_to_cell={},
                           diagnostics={"states_encoded": len(boards)})


def _setup(monkeypatch):
    closures = {case.name: _closure(case.board[0]) for case in _cases()}
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: closures[next(iter(kwargs["boards"]))])
    monkeypatch.setattr(comparison, "fit_constraint_encoder", _source_fit)
    monkeypatch.setattr(comparison, "build_scratch_target_v9", _target_build)
    monkeypatch.setattr(comparison, "build_adapted_target_v9", lambda source, target: _target_build(target))
    monkeypatch.setattr(comparison, "compile_encoded_v8", _compile)
    monkeypatch.setattr(comparison, "build_scratch_target_v11", _target_build)
    monkeypatch.setattr(comparison, "build_adapted_target_v11", lambda source, target: _target_build(target))
    monkeypatch.setattr(comparison, "compile_encoded_v11", _compile)
    return closures


def _run(**kwargs):
    return comparison.run_comparison_v11(cases=_cases(), cohort_roster=_roster(), samples_per_row=4,
        sample_seeds=(123,), fit_queries={"reward": Query()}, probe_queries={"risk": Query(1, 1, 0)}, **kwargs)


def test_source_fit_and_target_builds_receive_intended_data_without_redraw_or_oracle(monkeypatch):
    """Target data are allowed only for target builders, with control reuse and frozen-before-truth ordering."""
    closures = _setup(monkeypatch)
    events, source_inputs, target_inputs, freeze_batch = [], [], [], []
    frozen_models, sampled_models = [], []
    sample, freeze, reference = comparison.sample_model, comparison._freeze_arm, comparison._reference
    semantics = comparison._runtime_semantic_equivalence
    def semantic_check(frozen, queries):
        assert len(freeze_batch) == 8
        assert all(set(arm.plans) == set(queries) for arm in frozen.values())
        events.append(("semantics",))
        return semantics(frozen, queries)
    monkeypatch.setattr(comparison, "_runtime_semantic_equivalence", semantic_check)
    exact_names = {id(closure.model): name for name, closure in closures.items()}
    def sampling(model, **kwargs):
        events.append(("sample", exact_names[id(model)]))
        empirical = sample(model, **kwargs)
        sampled_models.append(empirical)
        return empirical
    def source_fit(training):
        events.append(("source_fit", tuple(item.name for item in training)))
        source_inputs.append(training)
        return _source_fit(training)
    def scratch(target):
        events.append(("scratch", target.name))
        target_inputs.append(("scratch", target))
        return _target_build(target)
    def adapt(source, target):
        events.append(("adapt", target.name))
        target_inputs.append(("adapt", target))
        return _target_build(target)
    def freezing(name, empirical, closure, encoder, queries, **kwargs):
        result = freeze(name, empirical, closure, encoder, queries, **kwargs)
        freeze_batch.append(name)
        frozen_models.append(empirical)
        return result
    def truth(*args, **kwargs):
        assert len(freeze_batch) == 8 and freeze_batch[-1] == "action_outcome_shuffle_adapted_v11"
        assert set(freeze_batch) == set(comparison.ARM_NAMES)
        freeze_batch.clear()
        assert events[-1] == ("semantics",)
        events.append(("truth",))
        return reference(*args, **kwargs)
    monkeypatch.setattr(comparison, "sample_model", sampling)
    monkeypatch.setattr(comparison, "fit_constraint_encoder", source_fit)
    monkeypatch.setattr(comparison, "build_scratch_target_v9", scratch)
    monkeypatch.setattr(comparison, "build_adapted_target_v9", adapt)
    monkeypatch.setattr(comparison, "build_scratch_target_v11", scratch)
    monkeypatch.setattr(comparison, "build_adapted_target_v11", adapt)
    monkeypatch.setattr(comparison, "_freeze_arm", freezing)
    monkeypatch.setattr(comparison, "_reference", truth)
    report = _run()
    assert events[:5] == [("sample", "a"), ("sample", "b"), ("source_fit", ("a", "b")),
                          ("source_fit", ("b",)), ("sample", "target")]
    assert len(source_inputs) == 2 and len(target_inputs) == 24
    assert all(item.empirical is not closures[item.name].model for items in source_inputs for item in items)
    assert all(item.empirical is not closures[item.name].model for _, item in target_inputs)
    assert {id(model) for model in frozen_models} == {id(model) for model in sampled_models}
    assert all(all(model is frozen_models[index] for model in frozen_models[index:index + 8])
               for index in range(0, len(frozen_models), 8))
    assert report["status"] == "DEVELOPMENT_COMPLETE" and report["completed_scenario_case_seed_runs"] == 6
    assert report["accounting"]["actual_physical_draws"] == 3 * 6 * 4
    assert report["accounting"]["scenario_case_logical_draws_including_repeated_bank_reads"] == 6 * 6 * 4
    assert report["accounting"]["source_encoder_fit_count"] == 2
    assert report["accounting"]["target_fit_and_compile_count_by_arm"] == {arm: 6 for arm in comparison.TARGET_ARMS}
    assert report["eager_block_semantic_equivalence"]["all_equal"]
    assert report["eager_block_semantic_equivalence"]["compared_target_build_pair_count"] == 12
    for scenario in report["scenarios"]:
        for record in scenario["cases"]:
            run = record["sampled_runs"][0]
            assert run["measured_arm_order"][-1] == "action_outcome_shuffle_adapted_v11"
            assert not run["arms"]["target_adapted_encoder_v11"]["encoding_diagnostics"]["all_target_predictive_constraints_satisfied"]
            assert set(run["worst_encoding_added_loss_by_arm"]) == set(comparison.ENCODER_ARMS)
    json.dumps(report, allow_nan=False)


def test_control_attributes_adaptation_setup_but_actual_campaign_charges_it_once(monkeypatch):
    """A control requiring adapted rules must include preparation without inventing a second build."""
    closures = _setup(monkeypatch)
    report = _run()
    samples = {row["case_name"]: row["sampling_seconds"] for row in report["empirical_bank"]}
    actual_work = setup_sum = 0.0
    for scenario in report["scenarios"]:
        fit = scenario["encoder_fits"][0]["encoder_fit_seconds"]
        amortized = {arm: 0.0 for arm in comparison.SOURCE_USING_ARMS}
        for record in scenario["cases"]:
            name, run = record["case"]["name"], record["sampled_runs"][0]
            arms = run["arms"]
            adapted = arms["target_adapted_encoder_v11"]["inventory"]["actual_construction_seconds"]
            control = arms["action_outcome_shuffle_adapted_v11"]["inventory"]
            assert control["reused_target_adaptation_setup_seconds_attributed_to_workload"] == adapted
            assert control["construction_seconds"] == control["actual_construction_seconds"] + adapted
            setup_sum += adapted
            for arm, item in arms.items():
                w = item["measured_cumulative_workloads"][-1]
                actual_work += item["inventory"]["actual_construction_seconds"] + w["cumulative_planning_seconds"] + w["cumulative_forecast_seconds"] + w["cumulative_ground_audit_seconds"]
                if arm in comparison.SOURCE_USING_ARMS:
                    amortized[arm] += w["amortized_source_encoder_fit_seconds"]
                    expected = fit + sum(closures[source].elapsed_seconds + samples[source]
                        for source in scenario["scenario"]["source_case_names"] if source != name)
                    assert w["standalone_additional_source_acquisition_and_fit_seconds"] == pytest.approx(expected)
                else:
                    assert w["amortized_source_encoder_fit_seconds"] == w["standalone_additional_source_acquisition_and_fit_seconds"] == 0
            assert run["adapted_vs_scratch"]["source_cost_excluded_from_target_only_delta"]
        assert all(value == pytest.approx(fit) for value in amortized.values())
    assert report["accounting"]["actual_eight_arm_target_build_plan_forecast_audit_seconds"] == pytest.approx(actual_work)
    assert report["accounting"]["control_reused_adaptation_setup_seconds_attributed_but_not_physically_repeated"] == pytest.approx(setup_sum)


def test_shuffled_control_reuses_adapted_encoder_and_never_adapts_shuffled_data(monkeypatch):
    """Mechanism control must alter action outcomes only after target fitting is frozen."""
    _setup(monkeypatch)
    compiled_inputs, adapted_encoders = [], []
    def adapt(source, target):
        result = _target_build(target)
        adapted_encoders.append((target.empirical, result.encoder))
        return result
    def compile(empirical, boards, encoder):
        compiled_inputs.append((empirical, encoder))
        return _compile(empirical, boards, encoder)
    monkeypatch.setattr(comparison, "build_adapted_target_v11", adapt)
    monkeypatch.setattr(comparison, "compile_encoded_v11", compile)
    _run()
    assert len(adapted_encoders) == 6
    controls = [(kernel, encoder) for kernel, encoder in compiled_inputs if any(encoder is item[1] for item in adapted_encoders)]
    assert len(controls) == 6
    for kernel, encoder in controls:
        original = next(original for original, adapted in adapted_encoders if adapted is encoder)
        assert kernel is not original
        assert kernel.rows == comparison.action_outcome_shuffle(original).rows


def test_target_collision_exact_labels_retained_for_heldout_targets(monkeypatch):
    """Target feature collisions need true labels even when the case was not a source."""
    _setup(monkeypatch)
    report = _run()
    run = report["scenarios"][1]["cases"][-1]["sampled_runs"][0]
    labels = run["target_feature_collision_exact_labels_by_arm"]["target_adapted_encoder_v11"]
    assert set(labels) == {1, 2}
    assert labels[1]["target_case"] == "target"
    assert labels[1]["queries"]["risk"]["exact_optimal_actions"] == ("B",)
    assert labels[2]["queries"]["risk"]["exact_optimal_actions"] == ("A",)


def test_source_failure_retains_case_and_blocks_only_affected_scenario(monkeypatch):
    """A missing source must not silently become a different source prior."""
    closures = _setup(monkeypatch)
    def closure(**kwargs):
        name = next(iter(kwargs["boards"]))
        if name == "a":
            raise ValueError("complete closure exceeds max_nodes=1; no truncated model produced")
        return closures[name]
    monkeypatch.setattr(comparison, "build_development_closure", closure)
    report = _run()
    primary, lofo = report["scenarios"]
    assert primary["source_closure_failure"] and not primary["encoder_fits"]
    assert all(not row["sampled_runs"] for row in primary["cases"])
    assert [row["status"] for row in lofo["cases"]] == ["COMPLETE", "CLOSURE_BUDGET_EXCEEDED", "COMPLETE"]
    assert report["lofo_target_aggregate"]["declared_case_count"] == 2
    assert report["accounting"]["actual_physical_draws"] == 2 * 6 * 4


def test_adapted_vs_scratch_keeps_actual_gains_components_and_target_costs():
    """Equal optimal-count totals could hide policy losses and source-initialization overhead."""
    def policy(values):
        return {"policy": {0: "A", 1: "B"}, "actual": {state: {"value": value, "reward": value, "failure": 0, "success": 0}
            for state, value in enumerate(values)}}
    private = {"target_scratch_encoder_v11": {"q": policy((1, 2))}, "target_adapted_encoder_v11": {"q": policy((.7, 2.4))}}
    frozen = {arm: SimpleNamespace(inventory={"actual_construction_seconds": seconds, "active_cells": 2},
        diagnostics={"work_counts": {"rows": 5}}) for arm, seconds in (("target_scratch_encoder_v11", .1), ("target_adapted_encoder_v11", .2))}
    result = comparison._adapted_vs_scratch(private, frozen, (0, 1), 0, {"q": Query()})
    row = result["queries"]["q"]
    assert row["root_adapted_value_gain_over_scratch"] == pytest.approx(-.3)
    assert row["maximum_all_state_adapted_value_gain"] == pytest.approx(.4)
    assert row["states_adapted_better"] == row["states_adapted_worse"] == 1
    assert result["adapted_minus_scratch_target_construction_seconds"] == pytest.approx(.1)


def test_fixed_primary_example_exports_adapted_model_without_ground_maps(monkeypatch):
    """The actual artifact branch must select adapted output and exercise its serializer."""
    _setup(monkeypatch)
    cases = tuple(replace(case, name="v6_spawn_edge_rescue_2") if case.name == "target" else case for case in _cases())
    roster = _roster(cases)
    roster["scenarios"] = roster["scenarios"][:1]
    closures = {case.name: _closure(case.board[0]) for case in cases}
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: closures[next(iter(kwargs["boards"]))])
    report = comparison.run_comparison_v11(cases=cases, cohort_roster=roster, samples_per_row=4,
        sample_seeds=(832101,), fit_queries={"reward": Query()}, probe_queries={})
    example = report["compiled_model_example"]
    assert example["scenario"] == "PRIMARY_V7_SPLIT" and example["arm"] == "target_adapted_encoder_v11"
    assert "state_to_cell" not in example["artifact"]["compiled_model"]
    assert all(len(cell) == 3 for cell in example["artifact"]["compiled_model"]["cells"])
    assert example["queries"]["reward"]["expected_root_action"] == report["scenarios"][0]["cases"][-1]["sampled_runs"][0]["arms"]["target_adapted_encoder_v11"]["queries"]["reward"]["root_action"]


def test_eager_block_mismatch_is_retained_and_audited_without_filtering(monkeypatch):
    """An optimized runtime changing a reward must report failed exact equivalence and retain the run."""
    _setup(monkeypatch)
    def changed_scratch(target):
        result = _target_build(target)
        rows = dict(result.compiled.rows)
        state_action = next(iter(rows))
        rows[state_action] = tuple(replace(row, reward=row.reward + .125) for row in rows[state_action])
        result.compiled = replace(result.compiled, rows=rows)
        return result
    monkeypatch.setattr(comparison, "build_scratch_target_v11", changed_scratch)
    report = _run()
    summary = report["eager_block_semantic_equivalence"]
    assert not summary["all_equal"] and summary["failed_run_count"] == 6
    assert report["completed_scenario_case_seed_runs"] == 6
    for scenario in report["scenarios"]:
        for record in scenario["cases"]:
            run = record["sampled_runs"][0]
            check = run["eager_block_semantic_equivalence"]
            assert check["performed_before_exact_reference"]
            assert not check["pairs"]["scratch"]["model_field_equal"]["rows"]
            assert not check["pairs"]["scratch"]["query_field_equal"]["reward"]["values"]
            assert check["pairs"]["adapted"]["all_equal"]
            assert set(run["arms"]) == set(comparison.ARM_NAMES)
            assert run["arms"]["target_scratch_encoder_v11"]["queries"]
