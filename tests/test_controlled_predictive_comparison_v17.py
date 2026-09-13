from collections import Counter
from copy import deepcopy
from types import SimpleNamespace
import gzip
import json

import pytest

from acfqp.science import controlled_predictive_comparison_v17 as comparison
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
    monkeypatch.setattr(comparison, "_validate_balanced_reference", lambda *args: {"validation_seconds": 0.0, "toy_reference_mock": True})
    return SimpleNamespace(closure=closure, keys=keys, providers=providers, events=events)


def _run(**kwargs):
    settings = dict(cases=(_case(),), cohort_roster={}, sample_seeds=(123,),
        initial_batch_cap=2, total_batch_cap=4, queries={"reward": Query(), "risk_5": Query(1, 5, 0)})
    settings.update(kwargs)
    return comparison.run_comparison_v17(**settings)


def test_one_paid_warm_two_conversions_and_complete_method_attribution(monkeypatch):
    """Detect omitted or duplicated setup cost and accidental GAP/BALANCED warm reuse."""
    state = _setup(monkeypatch)
    stage_a = comparison._stage_a
    stage_calls, conversions, gap_inputs = [], [], []
    balanced_conversion = comparison.ResamplingPlannerState.from_warm.__func__
    gap_conversion = comparison.GapPlannerState.from_warm.__func__
    gap_execute = comparison.evaluate_balanced_gap_execution
    def balanced_convert(cls, warm):
        result = balanced_conversion(cls, warm)
        conversions.append(result)
        return result
    def gap_convert(cls, warm):
        result = gap_conversion(cls, warm)
        conversions.append(result)
        return result
    def execute_gap(warm, *args, **kwargs):
        gap_inputs.append(warm)
        return gap_execute(warm, *args, **kwargs)
    monkeypatch.setattr(comparison.ResamplingPlannerState, "from_warm", classmethod(balanced_convert))
    monkeypatch.setattr(comparison.GapPlannerState, "from_warm", classmethod(gap_convert))
    monkeypatch.setattr(comparison, "evaluate_balanced_gap_execution", execute_gap)
    def warm(*args):
        stage_calls.append(args)
        return stage_a(*args)
    monkeypatch.setattr(comparison, "_stage_a", warm)
    report = _run(initial_batch_cap=10, total_batch_cap=12)
    run = report["cases"][0]["sampled_runs"][0]
    assert len(stage_calls) == 1 and stage_calls[0][4] == (10,)
    assert len(conversions) == 2
    assert type(conversions[0]) is comparison.ResamplingPlannerState
    assert type(conversions[1]) is comparison.GapPlannerState
    assert len(gap_inputs) == 4 and all(state is conversions[1] for state in gap_inputs)
    assert len(state.providers) == 9
    accounting = report["accounting"]
    assert accounting["actual_conversion_count"] == 2
    assert accounting["shared_balanced_conversion_count"] == accounting["shared_gap_conversion_count"] == 1
    assert run["shared_balanced_conversion"]["shared_by_methods"] == ["online_balanced_resampling"]
    assert run["shared_gap_conversion"]["shared_by_methods"] == list(comparison.GAP_MODES)
    assert accounting["actual_shared_conversion_seconds"] == pytest.approx(
        accounting["actual_balanced_conversion_seconds"] + accounting["actual_gap_conversion_seconds"])
    assert accounting["actual_warm_physical_draws"] == state.providers[0].work_counts["physical_draws"]
    assert accounting["actual_execution_physical_suffix_draws"] == sum(p.work_counts["physical_draws"] for p in state.providers[1:])
    assert accounting["actual_full_benchmark_physical_draws"] == 6 * 256
    assert accounting["query_execution_count"] == 8
    assert not report["settings"]["stage_a_128_continuation_executed"]
    assert report["settings"]["source_fits"] == 0 and report["all_path_batch_budgets_satisfied"]
    for method in comparison.EXECUTION_METHODS:
        conversion = 0.0 if method == "online_mass_bound" else run[
            "shared_balanced_conversion" if method == "online_balanced_resampling" else "shared_gap_conversion"]["conversion_seconds"]
        setup = run["shared_warm"]["prefix"]["warm_start_preparation_seconds"] + conversion
        for row in run["methods"][method].values():
            d = row["deployment"]
            assert d["expected_standalone_seconds"] == pytest.approx(setup + d["expected_suffix_seconds"])
            assert d["expected_batch_amortized_seconds"] == pytest.approx(setup / 2 + d["expected_suffix_seconds"])
            assert d["maximum_total_draws"] == d["maximum_total_batches"] * 256 <= 12 * 256
            assert d["maximum_total_distinct_rows"] <= d["maximum_total_batches"]
    assert set(run["methods"]) == set(comparison.METHODS)
    assert report["summary_by_split"]["ALL"]["paired_methods"]["gap_stop_versus_continue"]["query_context_count"] == 2
    assert report["current_continue_validation"]["execution_equal_count"] == 2
    assert report["current_continue_validation"]["all_execution_trees_equal"]


def test_all_histories_freeze_before_true_labels_and_both_historical_reads(monkeypatch):
    """Later seeds must complete before the first true optimum or historical result is read."""
    state = _setup(monkeypatch)
    for attribute, label in (("evaluate_execution", "base"), ("evaluate_resampling_execution", "balanced"),
                             ("evaluate_balanced_gap_execution", "gap"), ("evaluate_frozen_policy", "fixed")):
        original = getattr(comparison, attribute)
        def execute(*args, operation=original, event=label, **kwargs):
            result = operation(*args, **kwargs)
            state.events.append(event)
            return result
        monkeypatch.setattr(comparison, attribute, execute)
    reference = comparison._reference
    def truth(*args, **kwargs):
        assert state.events.count("base") == state.events.count("balanced") == 4
        assert state.events.count("gap") == state.events.count("fixed") == 8
        state.events.append("truth")
        return reference(*args, **kwargs)
    def old(*args):
        assert state.events.count("truth") == 2
        state.events.append("old_v14")
        return {"validation_seconds": 0.0}
    def balanced_old(*args):
        assert state.events[-1] == "old_v14"
        state.events.append("old_v15")
        return {"validation_seconds": 0.0}
    monkeypatch.setattr(comparison, "_reference", truth)
    monkeypatch.setattr(comparison, "_validate_reference", old)
    monkeypatch.setattr(comparison, "_validate_balanced_reference", balanced_old)
    report = _run(sample_seeds=(123, 124))
    assert state.events[-1] == "old_v15"
    assert report["completed_case_seed_runs"] == 2
    json.dumps(report, allow_nan=False)


def test_gzip_v15_reference_reports_changed_resampling_traces(monkeypatch, tmp_path):
    """The paid BALANCED control must retain its complete previous observation history."""
    validate = comparison._validate_balanced_reference
    _setup(monkeypatch)
    report = _run()
    path = tmp_path / "previous.json.gz"
    with gzip.open(path, "wt") as handle:
        json.dump(report, handle)
    matched = validate(report["cases"], report["settings"]["queries"], path)
    assert matched["execution_comparison_count"] == matched["execution_equal_count"] == 2
    prior = json.loads(json.dumps(report))
    prior["cases"][0]["sampled_runs"][0]["methods"]["online_balanced_resampling"]["risk_5"]["trace"]["quota"] = -1
    with gzip.open(path, "wt") as handle:
        json.dump(prior, handle)
    changed = validate(report["cases"], report["settings"]["queries"], path)
    assert changed["execution_equal_count"] == 1 and not changed["all_execution_trees_equal"]


def test_base_and_balanced_dispatch_preserve_original_traces(monkeypatch):
    """New gap methods must not change the unchanged control state types or execution modes."""
    _setup(monkeypatch)
    original_base, original_balanced = comparison.evaluate_execution, comparison.evaluate_resampling_execution
    originals = {"online_mass_bound": [], "online_balanced_resampling": []}
    def base(*args, **kwargs):
        assert kwargs["mode"] == "online" and type(args[0]).__name__ == "MassBoundPlannerState"
        row = original_base(*args, **kwargs)
        originals["online_mass_bound"].append(json.loads(json.dumps(row["trace"])))
        return row
    def balanced(*args, **kwargs):
        assert kwargs["mode"] == "BALANCED" and type(args[0]) is comparison.ResamplingPlannerState
        row = original_balanced(*args, **kwargs)
        originals["online_balanced_resampling"].append(json.loads(json.dumps(row["trace"])))
        return row
    monkeypatch.setattr(comparison, "evaluate_execution", base)
    monkeypatch.setattr(comparison, "evaluate_resampling_execution", balanced)
    report = _run()
    run = report["cases"][0]["sampled_runs"][0]
    for method, traces in originals.items():
        for name, trace in zip(report["settings"]["query_order"], traces):
            assert run["methods"][method][name]["trace"] == trace


def test_continue_comparison_preserves_child_samples_actions_and_outcomes():
    """A diagnostic projection must not hide acquisition or policy drift at deeper histories."""
    leaf = {"key": [1, [1]], "action": "A", "decision_kind": "ONLINE_BALANCED_RESAMPLING",
        "observed_batches": [{"batch_index": 0, "outcomes": [[1, [0, [2]], 0.25]]}],
        "requested_batches": [{"batch_index": 0, "row_key": [[1, [1]], "A"]}],
        "children": [{"probability": 1, "reward": 0.25, "node": {"status": "CUTOFF"}}]}
    original = {"trace": {"key": [2, [0]], "action": "B",
        "decision_kind": "ONLINE_BALANCED_RESAMPLING", "observed_batches": [],
        "children": [{"probability": 1, "reward": 0, "node": leaf}]},
        "root_metrics": {"utility": 0.25}, "physical_audit": {"work_counts": {"x": 1}}}
    current = deepcopy(original)
    current["trace"]["decision_kind"] = "ONLINE_BALANCED_GAP_CONTINUE"
    current["trace"]["gap_assessments"] = [{"separated": True}]
    child = current["trace"]["children"][0]["node"]
    child["decision_kind"] = "ONLINE_BALANCED_GAP_CONTINUE"
    child["gap_assessments"] = [{"separated": False}]
    current["physical_audit"]["work_counts"]["x"] = 99
    records = [{"case": {"name": "toy"}, "sampled_runs": [{"status": "COMPLETE", "sample_seed": 1,
        "methods": {"online_balanced_resampling": {"reward": original},
                    "online_balanced_gap_continue": {"reward": current}}}]}]
    validate = lambda: comparison._validate_current_continue(records, {"reward": Query()})
    assert validate()["all_execution_trees_equal"]
    for container, key, replacement in ((child, "action", "B"),
            (child["requested_batches"][0], "batch_index", 1),
            (child["observed_batches"][0], "outcomes", [[1, [0, [2]], 0.5]]),
            (child["children"][0], "probability", 0.5),
            (current["root_metrics"], "utility", 0.5)):
        old = container[key]
        container[key] = replacement
        assert not validate()["all_execution_trees_equal"]
        container[key] = old
