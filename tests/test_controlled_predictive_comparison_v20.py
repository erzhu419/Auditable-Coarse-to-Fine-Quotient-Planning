from collections import Counter
from copy import deepcopy
from types import SimpleNamespace
import gzip
import json

import pytest

from acfqp.science import controlled_predictive_comparison_v20 as comparison
from acfqp.science import controlled_predictive_comparison_v14 as warm_comparison
from acfqp.science import controlled_predictive_incremental_v13 as incremental
from acfqp.science import controlled_predictive_partial_v12 as partial
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_cohort_v7 import V7Case
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query


def _closure():
    model = FiniteModel({0: 2, 1: 1, 2: 1, 3: 0, 4: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "LOST", 4: "CUTOFF"},
        {(0, "A"): (Outcome(1, 1, 0),), (0, "B"): (Outcome(1, 2, 0),),
         (1, "A"): (Outcome(.5, 3, .1), Outcome(.5, 4, .1)), (1, "B"): (Outcome(1, 4, 0),),
         (2, "A"): (Outcome(1, 4, .1),), (2, "B"): (Outcome(1, 4, 0),)}, (0,))
    return DevelopmentClosure(model, {state: (state,) + (0,) * 15 for state in model.layers}, ("toy",),
        {"states": 5, "active_states": 3, "exact_transition_row_calls": 6, "exact_outcomes_enumerated": 7}, .02)


def _case(name="toy"):
    return V7Case(name, name, "toy_family", "0", (0,) * 16, 2,
        "FIT_HELD_OUT_DEVELOPMENT", "FIT_HELD_OUT_DEVELOPMENT", "test")


def _setup(monkeypatch):
    closure = _closure()
    keys = {state: (closure.model.layers[state], board) for state, board in closure.boards.items()}
    states = {key: state for state, key in keys.items()}
    def profile(key, work):
        work.update(states_profiled=1, deterministic_swipe_calls=4)
        state = states[key]
        status = closure.model.terminal[state]
        legal = ("A", "B") if status == "ACTIVE" else ()
        rewards = (("A", .1 if state in (1, 2) else 0), ("B", 0)) if legal else ()
        return partial.BoardProfile(status, legal, rewards, 2048)
    monkeypatch.setattr(incremental, "profile", profile)
    monkeypatch.setattr(partial, "profile", profile)
    providers, events = [], []
    class Provider:
        def __init__(self, seed, samples_per_row=256, samples_per_batch=256):
            self.seed = seed
            self.samples_per_row = samples_per_row
            self.work_counts = Counter()
            self.provider_seconds = 0.0
            self.requests = []
            providers.append(self)
        def sample(self, key, action):
            return self.sample_batch(key, action, 0)
        def sample_batch(self, key, action, index):
            row = closure.model.rows[states[key], action]
            self.work_counts["first_batch_requests" if index == 0 else "repeat_batch_requests"] += 1
            self.requests.append((key, action, index))
            self.work_counts.update(physical_draws=self.samples_per_row, row_requests=1,
                exact_transition_row_calls=1, support_entries_enumerated=len(row))
            self.provider_seconds += .00001
            return tuple((outcome.probability, keys[outcome.next_state], outcome.reward) for outcome in row)
    monkeypatch.setattr(comparison, "BatchRowSampleProvider", Provider)
    monkeypatch.setattr(warm_comparison, "RowSampleProvider", Provider)
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: closure)
    def acquire(closure, seed, samples_per_row):
        events.append("full_acquisition")
        return closure.model, {"acquisition_and_model_assembly_seconds": .003,
            "physical_sample_draws": len(closure.model.rows) * samples_per_row, "actual_rows_acquired": len(closure.model.rows),
            "reused_complete_support": True}
    monkeypatch.setattr(comparison, "_acquire_complete", acquire)
    monkeypatch.setattr(comparison, "_validate_reference", lambda *args: {"validation_seconds": 0.0, "toy_reference_mock": True})
    monkeypatch.setattr(comparison, "_validate_cached_reference", lambda *args: {"validation_seconds": 0.0, "toy_reference_mock": True})
    return SimpleNamespace(closure=closure, keys=keys, providers=providers, events=events)


def _run(**kwargs):
    settings = dict(cases=(_case(),), cohort_roster={}, sample_seeds=(123,),
        initial_batch_cap=2, total_batch_cap=4, queries={"reward": Query(), "risk_5": Query(1, 5, 0)})
    settings.update(kwargs)
    return comparison.run_comparison_v20(**settings)


def test_one_warm_two_separate_conversions_and_complete_costs(monkeypatch):
    """Each method must pay its own setup and every physically requested batch."""
    fixture = _setup(monkeypatch)
    stage_a = comparison._stage_a
    stage_calls, conversions, stop_inputs = [], {}, []
    stop_execute = comparison.evaluate_balanced_gap_execution
    factories = [(cls, cls.from_warm.__func__) for cls in (
        comparison.CachedGapPlannerState, comparison.VarianceGapPlannerState)]
    for target, original in factories:
        def convert(cls, warm, expected=target, operation=original):
            result = operation(cls, warm)
            if cls is expected:
                conversions.setdefault(cls, []).append(result)
            return result
        monkeypatch.setattr(target, "from_warm", classmethod(convert))
    def execute_stop(warm, *args, **kwargs):
        stop_inputs.append(warm)
        return stop_execute(warm, *args, **kwargs)
    monkeypatch.setattr(comparison, "evaluate_balanced_gap_execution", execute_stop)
    def warm(*args):
        stage_calls.append(args)
        return stage_a(*args)
    monkeypatch.setattr(comparison, "_stage_a", warm)
    report = _run(initial_batch_cap=10, total_batch_cap=12)
    run = report["cases"][0]["sampled_runs"][0]
    assert len(stage_calls) == 1 and stage_calls[0][4] == (10,)
    assert len(conversions) == 2 and all(len(values) == 1 for values in conversions.values())
    assert len(stop_inputs) == 4
    assert all(sum(value is states[0] for value in stop_inputs) == 2 for states in conversions.values())
    assert len(fixture.providers) == 7
    accounting = report["accounting"]
    assert accounting["actual_conversion_count"] == 2
    assert accounting["shared_cached_gap_conversion_count"] == accounting["shared_variance_conversion_count"] == 1
    assert run["shared_cached_gap_conversion"]["shared_by_methods"] == ["online_cached_balanced_gap_stop"]
    assert run["shared_variance_conversion"]["shared_by_methods"] == ["online_variance_gap_stop"]
    assert accounting["actual_shared_conversion_seconds"] == pytest.approx(
        accounting["actual_cached_gap_conversion_seconds"] + accounting["actual_variance_conversion_seconds"])
    assert accounting["actual_warm_physical_draws"] == fixture.providers[0].work_counts["physical_draws"]
    assert accounting["actual_execution_physical_suffix_draws"] == sum(p.work_counts["physical_draws"] for p in fixture.providers[1:])
    assert accounting["actual_full_benchmark_physical_draws"] == 6 * 256
    assert accounting["query_execution_count"] == 6
    assert not report["settings"]["stage_a_128_continuation_executed"]
    assert report["settings"]["source_fits"] == 0 and report["all_path_batch_budgets_satisfied"]
    for method in comparison.EXECUTION_METHODS:
        key = {"online_cached_balanced_gap_stop": "shared_cached_gap_conversion",
               "online_variance_gap_stop": "shared_variance_conversion"}.get(method)
        conversion = run[key]["conversion_seconds"] if key else 0.0
        setup = run["shared_warm"]["prefix"]["warm_start_preparation_seconds"] + conversion
        for row in run["methods"][method].values():
            d = row["deployment"]
            assert d["expected_standalone_seconds"] == pytest.approx(setup + d["expected_suffix_seconds"])
            assert d["expected_batch_amortized_seconds"] == pytest.approx(setup / 2 + d["expected_suffix_seconds"])
            assert d["maximum_total_draws"] == d["maximum_total_batches"] * 256 <= 12 * 256
            assert d["maximum_total_distinct_rows"] <= d["maximum_total_batches"]
    assert set(run["methods"]) == set(comparison.METHODS) and len(comparison.METHODS) == 5
    online = comparison.EXECUTION_METHODS
    assert run["execution_order_by_query"] == {"reward": online, "risk_5": online[1:] + online[:1]}
    assert report["summary_by_split"]["ALL"]["paired_methods"]["variance_vs_cached"]["query_context_count"] == 2
    for method in comparison.METHODS:
        detail = report["summary_by_split"]["ALL"]["methods"][method]["cost_detail"]
        expected = sum(row["deployment"]["expected_suffix_seconds"] for row in run["methods"][method].values()) / 2
        assert sum(detail["mean_expected_seconds_by_stage"].values()) == pytest.approx(expected)


def test_all_histories_freeze_before_truth_and_both_historical_reads(monkeypatch):
    """No later seed may be constructed using exact labels or old benchmark results."""
    fixture = _setup(monkeypatch)
    for attribute, label in (("evaluate_execution", "base"),
            ("evaluate_balanced_gap_execution", "gap"), ("evaluate_frozen_policy", "fixed")):
        original = getattr(comparison, attribute)
        def execute(*args, operation=original, event=label, **kwargs):
            result = operation(*args, **kwargs)
            fixture.events.append(event)
            return result
        monkeypatch.setattr(comparison, attribute, execute)
    reference = comparison._reference
    def truth(*args, **kwargs):
        assert fixture.events.count("base") == 4
        assert fixture.events.count("gap") == fixture.events.count("fixed") == 8
        fixture.events.append("truth")
        return reference(*args, **kwargs)
    def old(*args):
        assert fixture.events.count("truth") == 2
        fixture.events.append("old_v14")
        return {"validation_seconds": 0.0}
    def cached_old(*args):
        assert fixture.events[-1] == "old_v14"
        fixture.events.append("old_v18")
        return {"validation_seconds": 0.0}
    monkeypatch.setattr(comparison, "_reference", truth)
    monkeypatch.setattr(comparison, "_validate_reference", old)
    monkeypatch.setattr(comparison, "_validate_cached_reference", cached_old)
    report = _run(sample_seeds=(123, 124))
    assert fixture.events[-1] == "old_v18" and report["completed_case_seed_runs"] == 2
    json.dumps(report, allow_nan=False)


def test_cached_reference_keeps_diagnostics_batch_indices_and_actions(monkeypatch, tmp_path):
    """Every retained CACHED trace field must remain an exact historical control."""
    validate = comparison._validate_cached_reference
    _setup(monkeypatch)
    report = _run()
    path = tmp_path / "v18.json.gz"
    previous = deepcopy(report)
    def check():
        with gzip.open(path, "wt") as handle:
            json.dump(previous, handle)
        return validate(report["cases"], report["settings"]["queries"], path)
    assert check()["execution_equal_count"] == 2
    assert check()["trace_fields_excluded"] == []
    trace = previous["cases"][0]["sampled_runs"][0]["methods"]["online_cached_balanced_gap_stop"]["risk_5"]["trace"]
    for container, field, replacement in ((trace, "action", "CHANGED"),
            (trace, "acquisition_stop_reason", "CHANGED"),
            (trace["gap_assessments"][0], "gap", 99),
            (trace["requested_batches"][0], "batch_index", 99)):
        value = container[field]
        container[field] = replacement
        result = check()
        assert result["execution_equal_count"] == 1 and not result["all_execution_trees_equal"]
        container[field] = value


def test_original_dispatch_and_candidate_allocation_identity(monkeypatch):
    """Use unchanged executors while exposing the candidate's actual allocation method."""
    _setup(monkeypatch)
    original_base, original_gap = comparison.evaluate_execution, comparison.evaluate_balanced_gap_execution
    traces = {method: [] for method in comparison.EXECUTION_METHODS}
    def base(*args, **kwargs):
        assert kwargs["mode"] == "online" and type(args[0]).__name__ == "MassBoundPlannerState"
        row = original_base(*args, **kwargs)
        traces["online_mass_bound"].append(deepcopy(row["trace"]))
        return row
    def gap(*args, **kwargs):
        assert kwargs["mode"] == "STOP"
        state_type = type(args[0])
        assert state_type in (comparison.CachedGapPlannerState, comparison.VarianceGapPlannerState)
        method = "online_cached_balanced_gap_stop" if state_type is comparison.CachedGapPlannerState else "online_variance_gap_stop"
        row = original_gap(*args, **kwargs)
        traces[method].append(deepcopy(row["trace"]))
        return row
    monkeypatch.setattr(comparison, "evaluate_execution", base)
    monkeypatch.setattr(comparison, "evaluate_balanced_gap_execution", gap)
    report = _run()
    run = report["cases"][0]["sampled_runs"][0]
    for method, original_traces in traces.items():
        for name, trace in zip(report["settings"]["query_order"], original_traces):
            assert run["methods"][method][name]["trace"] == trace
    for row in run["methods"]["online_variance_gap_stop"].values():
        assert row["allocation_method"] == "VARIANCE_REDUCTION"
        assert "unbiased sampled return variance" in row["acquisition_score_scope"]
        assert "unchanged shared V17 executor" in row["trace_operation_label_scope"]
