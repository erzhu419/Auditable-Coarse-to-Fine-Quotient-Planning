from collections import Counter
from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path
import json

import pytest

from acfqp.science import controlled_predictive_comparison_v15 as comparison
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
    return SimpleNamespace(closure=closure, keys=keys, providers=providers, events=events)


def _run(**kwargs):
    settings = dict(cases=(_case(),), cohort_roster={}, sample_seeds=(123,),
        initial_batch_cap=2, total_batch_cap=4, queries={"reward": Query(), "risk_5": Query(1, 5, 0)})
    settings.update(kwargs)
    return comparison.run_comparison_v15(**settings)


def test_one_paid_warm_and_one_conversion_are_shared_without_128_continuation(monkeypatch):
    """Three alternatives share actual warm acquisition; only candidates need integer conversion."""
    state = _setup(monkeypatch)
    stage_a, convert, execute = comparison._stage_a, comparison.ResamplingPlannerState.from_warm, comparison.evaluate_resampling_execution
    stage_calls, converted, candidate_inputs = [], [], []
    def warm(*args):
        stage_calls.append(args)
        return stage_a(*args)
    def conversion(cls, old):
        before_rows, before_work = dict(old.rows), dict(old.work_counts)
        result = convert(old)
        assert old.rows == before_rows and dict(old.work_counts) == before_work
        converted.append(result)
        return result
    def candidate(warm_state, *args, **kwargs):
        candidate_inputs.append(warm_state)
        return execute(warm_state, *args, **kwargs)
    monkeypatch.setattr(comparison, "_stage_a", warm)
    monkeypatch.setattr(comparison.ResamplingPlannerState, "from_warm", classmethod(conversion))
    monkeypatch.setattr(comparison, "evaluate_resampling_execution", candidate)
    report = _run()
    assert len(stage_calls) == 1 and stage_calls[0][4] == (2,)
    assert len(converted) == 1 and all(item is converted[0] for item in candidate_inputs)
    assert converted[0].spent_batches == 2 and len(converted[0].rows) == 2
    assert len(state.providers) == 7  # one warm plus three alternatives for each of two queries
    assert report["accounting"]["shared_candidate_conversion_count"] == 1
    assert not report["settings"]["stage_a_128_continuation_executed"]
    assert report["settings"]["source_fits"] == 0


def test_entire_current_campaign_freezes_before_truth_and_old_reference(monkeypatch):
    """Even later seeds must finish their histories before the first exact optimum is labeled."""
    state = _setup(monkeypatch)
    execute, candidate, fixed, reference = comparison.evaluate_execution, comparison.evaluate_resampling_execution, comparison.evaluate_frozen_policy, comparison._reference
    def base(*args, **kwargs):
        result = execute(*args, **kwargs); state.events.append("base"); return result
    def resample(*args, **kwargs):
        result = candidate(*args, **kwargs); state.events.append("candidate"); return result
    def frozen(*args, **kwargs):
        result = fixed(*args, **kwargs); state.events.append("fixed"); return result
    def truth(*args, **kwargs):
        assert state.events.count("base") == 4
        assert state.events.count("candidate") == 8
        assert state.events.count("fixed") == 8
        state.events.append("truth")
        return reference(*args, **kwargs)
    def old(*args):
        assert state.events.count("truth") == 2
        state.events.append("old_reference")
        return {"validation_seconds": 0.0}
    monkeypatch.setattr(comparison, "evaluate_execution", base)
    monkeypatch.setattr(comparison, "evaluate_resampling_execution", resample)
    monkeypatch.setattr(comparison, "evaluate_frozen_policy", frozen)
    monkeypatch.setattr(comparison, "_reference", truth)
    monkeypatch.setattr(comparison, "_validate_reference", old)
    report = _run(sample_seeds=(123, 124))
    assert state.events[-1] == "old_reference"
    assert report["completed_case_seed_runs"] == 2
    assert set(report["cases"][0]["sampled_runs"][0]["methods"]) == set(comparison.METHODS)
    json.dumps(report, allow_nan=False)


def test_real_batches_and_distinct_rows_have_different_charges(monkeypatch):
    """Repeated observations consume128-cap batches even when they discover no new state/action row."""
    state = _setup(monkeypatch)
    report = _run(initial_batch_cap=10, total_batch_cap=12)
    run = report["cases"][0]["sampled_runs"][0]
    accounting = report["accounting"]
    assert accounting["actual_warm_physical_draws"] == state.providers[0].work_counts["physical_draws"]
    assert accounting["actual_execution_physical_suffix_draws"] == sum(p.work_counts["physical_draws"] for p in state.providers[1:])
    assert accounting["actual_full_benchmark_physical_draws"] == 6 * 256
    assert report["all_path_batch_budgets_satisfied"]
    warm = run["shared_warm"]["prefix"]["warm_start_preparation_seconds"]
    conversion = run["shared_candidate_conversion"]["conversion_seconds"]
    repeated = 0
    for method in comparison.EXECUTION_METHODS:
        setup = warm + (0 if method == "online_mass_bound" else conversion)
        for row in run["methods"][method].values():
            d = row["deployment"]
            assert d["expected_standalone_seconds"] == pytest.approx(setup + d["expected_suffix_seconds"])
            assert d["expected_batch_amortized_seconds"] == pytest.approx(setup / 2 + d["expected_suffix_seconds"])
            assert d["maximum_total_draws"] == d["maximum_total_batches"] * 256 <= 12 * 256
            assert d["maximum_total_distinct_rows"] <= d["maximum_total_batches"]
            if method != "online_mass_bound":
                repeated += row["physical_audit"]["provider_counts"].get("repeat_batch_requests", 0)
                assert d["expected_total_batches"] > d["expected_total_distinct_rows"]
    assert repeated > 0
    assert accounting["actual_shared_conversion_seconds"] == conversion


def test_baseline_field_aliases_do_not_mutate_observation_trace(monkeypatch):
    """The BASE reference trace must retain original V14 row semantics unchanged."""
    _setup(monkeypatch)
    original = comparison.evaluate_execution
    originals = []
    def base(*args, **kwargs):
        row = original(*args, **kwargs)
        originals.append(json.loads(json.dumps(row["trace"])))
        return row
    monkeypatch.setattr(comparison, "evaluate_execution", base)
    report = _run()
    run = report["cases"][0]["sampled_runs"][0]
    for name, trace in zip(report["settings"]["query_order"], originals):
        row = run["methods"]["online_mass_bound"][name]
        assert row["trace"] == trace
        d = row["deployment"]
        assert d["expected_total_batches"] == d["expected_total_rows"] == d["expected_total_distinct_rows"]
    for method in comparison.CANDIDATE_MODES:
        assert all("requested_batches" in row["trace"] for row in run["methods"][method].values())


def test_closure_failure_retains_paid_warm_and_conversion(monkeypatch):
    """Already incurred acquisition/conversion work survives a declared full-closure failure."""
    _setup(monkeypatch)
    def fail(**kwargs):
        raise ValueError("complete closure exceeds max_nodes=1; no truncated model produced")
    monkeypatch.setattr(comparison, "build_development_closure", fail)
    report = _run()
    assert report["status"] == "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES"
    assert report["completed_case_seed_runs"] == 0 and report["all_declared_cases_retained"]
    assert report["accounting"]["actual_warm_physical_draws"] == 2 * 256
    assert report["accounting"]["shared_candidate_conversion_count"] == 1
    assert report["accounting"]["actual_shared_conversion_seconds"] > 0
    assert report["cases"][0]["sampled_runs"][0]["status"] == "CLOSURE_BUDGET_EXCEEDED"


def test_old_v14_reference_normalizes_prefix_keys_and_retains_trace_changes(monkeypatch, tmp_path):
    """JSON tuples/lists compare normally; a changed observed batch-zero trace fails visibly."""
    validate = comparison._validate_reference
    _setup(monkeypatch)
    report = _run()
    current = report["cases"][0]["sampled_runs"][0]
    old = {"sample_seed": current["sample_seed"],
        "stage_a": {"MASS_BOUND": {"prefixes": {"2": current["shared_warm"]["prefix"]}}},
        "methods": {"online_mass_bound": current["methods"]["online_mass_bound"]}}
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"cases": [{"case": report["cases"][0]["case"], "sampled_runs": [old]}]}))
    result = validate(report["cases"], report["settings"]["queries"], path)
    assert result["prefix_comparison_count"] == result["prefix_equal_count"] == 1
    assert result["execution_comparison_count"] == result["execution_equal_count"] == 2
    payload = json.loads(path.read_text())
    payload["cases"][0]["sampled_runs"][0]["methods"]["online_mass_bound"]["risk_5"]["trace"]["altered_observation"] = True
    path.write_text(json.dumps(payload))
    changed = validate(report["cases"], report["settings"]["queries"], path)
    assert changed["prefix_equal_count"] == 1 and changed["execution_equal_count"] == 1
    assert not changed["all_execution_trees_equal"]


def test_three_fixed_directed_examples_use_existing_query_trees(monkeypatch):
    """Example extraction must not add unseen experiment contexts or omit the mechanism subset."""
    _setup(monkeypatch)
    cases = (_case("v6_spawn_edge_rescue_2"), _case("v6_crossing_rescue_pair_3"), _case("v6_crossing_rescue_pair_2"))
    queries = {"reward": Query(), "risk_5": Query(1, 5, 0), "risk_1": Query(1, 1, 0),
        "goal_1_risk_1": Query(1, 1, 1), "probe_risk_0_5": Query(1, .5, 0), "probe_goal_2_risk_0_5": Query(1, .5, 2)}
    report = _run(cases=cases, sample_seeds=(832101, 832102), queries=queries)
    first, second, third = report["history_policy_examples"]
    assert first["query_order"] == list(queries)
    assert second["query_order"] == ["risk_5"]
    assert third["query_order"] == list(queries)[2:]
    assert all(row["method"] == "online_directed_resampling" for row in (first, second, third))
    assert report["accounting"]["query_execution_count"] == 6 * 6 * 3


def test_cli_defaults_to_lossless_gzip_and_preserves_existing_output(monkeypatch, tmp_path):
    """The retained artifact must be readable gzip and cannot overwrite existing experiment evidence."""
    import gzip
    import importlib.util
    import sys
    script = Path(__file__).resolve().parents[1] / "scripts/run_controlled_predictive_comparison_v15.py"
    spec = importlib.util.spec_from_file_location("v15_script_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    roster, protocol, output = tmp_path / "roster.json", tmp_path / "protocol.md", tmp_path / "result.json.gz"
    roster.write_text('{"cases": []}')
    protocol.write_text("frozen toy protocol")
    monkeypatch.setattr(module, "DEFAULT_ROSTER", roster)
    monkeypatch.setattr(module, "DEFAULT_OUTPUT", output)
    monkeypatch.setattr(module, "PROTOCOL", protocol)
    result = {"status": "TOY_COMPLETE", "trace": [[1, [0] * 16], {"value": .25}]}
    monkeypatch.setattr(module, "run_comparison_v15", lambda **kwargs: result)
    monkeypatch.setattr(sys, "argv", [str(script)])
    module.main()
    with gzip.open(output, "rt") as handle:
        assert json.load(handle) == result
    before = output.read_bytes()
    with pytest.raises(SystemExit):
        module.main()
    assert output.read_bytes() == before
