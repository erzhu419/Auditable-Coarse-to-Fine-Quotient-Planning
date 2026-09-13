from collections import Counter
from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path
import json

import pytest

from acfqp.science import controlled_predictive_comparison_v14 as comparison
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
        def __init__(self, seed, samples_per_row=256):
            self.seed = seed
            self.samples_per_row = samples_per_row
            self.work_counts = Counter()
            self.provider_seconds = 0.0
            self.requests = []
            providers.append(self)
        def sample(self, key, action):
            row = closure.model.rows[states[key], action]
            self.requests.append((key, action))
            self.work_counts.update(physical_draws=self.samples_per_row, row_requests=1,
                exact_transition_row_calls=1, support_entries_enumerated=len(row))
            self.provider_seconds += .00001
            return tuple((outcome.probability, keys[outcome.next_state], outcome.reward) for outcome in row)
    monkeypatch.setattr(comparison, "RowSampleProvider", Provider)
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: closure)
    def acquire(closure, seed, samples_per_row):
        events.append("full_acquisition")
        return closure.model, {"acquisition_and_model_assembly_seconds": .003,
            "physical_sample_draws": len(closure.model.rows) * samples_per_row, "actual_rows_acquired": len(closure.model.rows),
            "reused_complete_support": True}
    monkeypatch.setattr(comparison, "_acquire_complete", acquire)
    monkeypatch.setattr(comparison, "_validate_legacy_reference", lambda *args: {"validation_seconds": 0.0, "toy_reference_mock": True})
    return SimpleNamespace(closure=closure, keys=keys, providers=providers, events=events)


def _run(**kwargs):
    return comparison.run_comparison_v14(cases=(_case(),), cohort_roster={}, sample_seeds=(123,),
        prefix_budgets=(2, 4), total_row_cap=4, queries={"reward": Query(), "risk_5": Query(1, 5, 0)}, **kwargs)


def test_stage_a_independent_providers_keep_safe_prefixes_and_all_numeric_maps(monkeypatch):
    """The128 continuation must not mutate32 warm data or give one engine free observations."""
    state = _setup(monkeypatch)
    queries = {"reward": Query(), "risk_5": Query(1, 5, 0)}
    full, _ = comparison._stage_a(state.keys[0], 123, queries, "LEGACY", (2, 4), 256)
    inc, _ = comparison._stage_a(state.keys[0], 123, queries, "MASS_BOUND", (2, 4), 256)
    assert len(state.providers) == 2 and state.providers[0] is not state.providers[1]
    assert state.providers[0].requests == state.providers[1].requests
    assert len(full[2].state.rows) == len(inc[2].state.rows) == 2
    assert len(full[4].state.rows) == len(inc[4].state.rows) == 4
    for budget in (2, 4):
        assert full[budget].state.rows == inc[budget].state.rows
        assert full[budget].intervals == inc[budget].intervals
    assert type(full[2].state) is comparison.PlannerState
    assert type(inc[2].state) is comparison.MassBoundPlannerState
    assert full[2].state.caches["reward"].lower is not full[4].state.caches["reward"].lower


def test_stage_a_does_not_reselect_after_earlier_convergence(monkeypatch):
    """An already stopped full engine must not be charged another round of ten-query solves."""
    state = _setup(monkeypatch)
    original = incremental.PlannerState.next_row
    def next_row(self):
        assert self.stop_reason is None, "should honor the earlier terminal acquisition status"
        return original(self)
    monkeypatch.setattr(incremental.PlannerState, "next_row", next_row)
    snapshots, _ = comparison._stage_a(state.keys[0], 123, {"reward": Query()}, "LEGACY", (10, 20), 256)
    assert snapshots[10].state.stop_reason == "ALL_QUERIES_CONVERGED"
    assert snapshots[10].state.row_order == snapshots[20].state.row_order


def test_all_history_trees_and_full_benchmark_plans_freeze_before_truth(monkeypatch):
    """Truth labeling cannot alter the adaptive histories or full sampled benchmark plans."""
    state = _setup(monkeypatch)
    execute, freeze_full, frozen, reference = comparison.evaluate_execution, comparison._full_arms, comparison.evaluate_frozen_policy, comparison._reference
    def execution(*args, **kwargs):
        assert "full_plans_frozen" in state.events
        result = execute(*args, **kwargs)
        state.events.append("execution")
        return result
    def full(*args, **kwargs):
        result = freeze_full(*args, **kwargs)
        state.events.append("full_plans_frozen")
        return result
    def fixed(*args, **kwargs):
        result = frozen(*args, **kwargs)
        state.events.append("fixed_history")
        return result
    def truth(*args, **kwargs):
        assert state.events.count("execution") == 8
        assert state.events.count("fixed_history") == 8
        state.events.append("truth")
        return reference(*args, **kwargs)
    monkeypatch.setattr(comparison, "evaluate_execution", execution)
    monkeypatch.setattr(comparison, "_full_arms", full)
    monkeypatch.setattr(comparison, "evaluate_frozen_policy", fixed)
    monkeypatch.setattr(comparison, "_reference", truth)
    def validate(*args):
        assert state.events[-1] == "truth"
        assert state.events.count("execution") == 8
        state.events.append("old_reference_loaded")
        return {"validation_seconds": 0.0}
    monkeypatch.setattr(comparison, "_validate_legacy_reference", validate)
    report = _run()
    assert state.events[-1] == "old_reference_loaded"
    assert report["all_path_row_budgets_satisfied"]
    assert report["query_contexts_per_method"] == 2 and report["settings"]["source_fits"] == 0
    assert set(report["cases"][0]["sampled_runs"][0]["methods"]) == {"full_state_empirical", "exact_empirical_quotient", "frozen32_legacy", "frozen32_mass_bound", "upfront_legacy", "upfront_mass_bound", "online_legacy", "online_mass_bound"}
    json.dumps(report, allow_nan=False)


def test_warm_cost_attribution_and_physical_counts_do_not_sum_prefixes(monkeypatch):
    """Two timing arms, shared warm prefixes and counterfactual suffixes need separate physical counts."""
    state = _setup(monkeypatch)
    report = _run()
    run = report["cases"][0]["sampled_runs"][0]
    assert len(state.providers) == 10  # two Stage A, four executions for each of two queries
    a_draws = sum(p.work_counts["physical_draws"] for p in state.providers[:2])
    b_draws = sum(p.work_counts["physical_draws"] for p in state.providers[2:])
    assert report["accounting"]["actual_stage_a_physical_draws"] == a_draws == 8 * 256
    assert report["accounting"]["actual_stage_b_physical_suffix_draws"] == b_draws
    assert report["accounting"]["actual_full_benchmark_physical_draws"] == 6 * 256
    for mode in comparison.EXECUTION_MODES:
        for update in comparison.VARIANTS:
            warm = run["stage_a"][update]["prefixes"]["2"]["warm_start_preparation_seconds"]
            for result in run["methods"][comparison._method_id(mode, update)].values():
                d = result["deployment"]
                assert d["initial_rows"] == 2
                assert d["expected_standalone_seconds"] == pytest.approx(warm + d["expected_suffix_seconds"])
                assert d["expected_batch_amortized_seconds"] == pytest.approx(warm / 2 + d["expected_suffix_seconds"])
                assert d["maximum_total_rows"] <= 4


def test_expected_variant_difference_retains_every_trace_and_observation(monkeypatch):
    """Candidate changes must not be deduplicated against or filtered by the legacy control."""
    _setup(monkeypatch)
    original = comparison.evaluate_execution
    def execution(warm, *args, **kwargs):
        result = original(warm, *args, **kwargs)
        if isinstance(warm, comparison.MassBoundPlannerState):
            result["trace"]["altered_observation_for_regression_test"] = True
        return result
    monkeypatch.setattr(comparison, "evaluate_execution", execution)
    report = _run()
    assert report["status"] == "DEVELOPMENT_COMPLETE"
    run = report["cases"][0]["sampled_runs"][0]
    for mode in comparison.EXECUTION_MODES:
        for name in report["settings"]["query_order"]:
            old = run["methods"][mode + "_legacy"][name]
            new = run["methods"][mode + "_mass_bound"][name]
            assert old["trace"] != new["trace"] and old["root_metrics"] == new["root_metrics"]
            assert "trace" in old and "trace" in new
    assert report["summary_by_split"]["ALL"]["mass_bound_versus_legacy"]["online"]["equal_value_count"] == 2


def test_closure_failure_retains_stage_a_cost_and_declared_case(monkeypatch):
    """A failed environment closure cannot remove prior acquisition work from the report."""
    _setup(monkeypatch)
    def fail(**kwargs):
        raise ValueError("complete closure exceeds max_nodes=1; no truncated model produced")
    monkeypatch.setattr(comparison, "build_development_closure", fail)
    report = _run()
    assert report["status"] == "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES"
    assert report["completed_case_seed_runs"] == 0 and report["all_declared_cases_retained"]
    assert report["accounting"]["stage_a_trajectory_count"] == 2
    assert report["accounting"]["actual_stage_a_physical_draws"] == 8 * 256
    assert report["cases"][0]["sampled_runs"][0]["status"] == "CLOSURE_BUDGET_EXCEEDED"


def test_three_preregistered_history_examples_are_selected_without_extra_execution(monkeypatch):
    """Both original examples and the fixed four-query mechanism example use existing histories."""
    _setup(monkeypatch)
    cases = (_case("v6_spawn_edge_rescue_2"), _case("v6_crossing_rescue_pair_3"), _case("v6_crossing_rescue_pair_2"))
    queries = {"reward": Query(), "risk_5": Query(1, 5, 0), "risk_1": Query(1, 1, 0),
        "goal_1_risk_1": Query(1, 1, 1), "probe_risk_0_5": Query(1, .5, 0), "probe_goal_2_risk_0_5": Query(1, .5, 2)}
    report = comparison.run_comparison_v14(cases=cases, cohort_roster={}, sample_seeds=(832101, 832102),
        prefix_budgets=(2, 4), total_row_cap=4, queries=queries)
    assert report["completed_case_seed_runs"] == 6
    first, second, third = report["history_policy_examples"]
    assert first["case_name"] == "v6_spawn_edge_rescue_2" and first["query_order"] == list(queries)
    assert second["case_name"] == "v6_crossing_rescue_pair_3" and second["query_order"] == ["risk_5"]
    assert third["case_name"] == "v6_crossing_rescue_pair_2"
    assert third["query_order"] == list(queries)[2:]
    assert first["method"] == second["method"] == third["method"] == "online_mass_bound"
    assert report["accounting"]["stage_b_query_execution_count"] == 6 * len(queries) * 4


def test_old_reference_normalizes_json_keys_and_retains_real_differences(monkeypatch, tmp_path):
    """List conversion is benign; changed observations or declared prefix values are failures."""
    validate = comparison._validate_legacy_reference
    _setup(monkeypatch)
    report = _run()
    current = report["cases"][0]["sampled_runs"][0]
    old = {"sample_seed": current["sample_seed"], "stage_a": {"incremental": current["stage_a"]["LEGACY"]},
        "methods": {}, "paired_execution_semantics": {}}
    for mode in comparison.EXECUTION_MODES:
        old["methods"][mode + "_incremental"] = current["methods"][mode + "_legacy"]
        old["paired_execution_semantics"][mode] = {name: {"shared_trace": row["trace"]}
            for name, row in old["methods"][mode + "_incremental"].items()}
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"cases": [{"case": report["cases"][0]["case"], "sampled_runs": [old]}]}))
    result = validate(report["cases"], report["settings"]["queries"], path)
    assert result["prefix_comparison_count"] == result["prefix_equal_count"] == 2
    assert result["execution_comparison_count"] == result["execution_equal_count"] == 4
    payload = json.loads(path.read_text())
    previous = payload["cases"][0]["sampled_runs"][0]
    previous["stage_a"]["incremental"]["prefixes"]["2"]["actual_rows_acquired"] += 1
    previous["paired_execution_semantics"]["online"]["risk_5"]["shared_trace"]["changed_observation"] = True
    path.write_text(json.dumps(payload))
    changed = validate(report["cases"], report["settings"]["queries"], path)
    assert changed["prefix_equal_count"] == 1 and changed["execution_equal_count"] == 3
    assert not changed["all_prefixes_equal"] and not changed["all_execution_trees_equal"]


def test_goal_pair_diagnostic_uses_own_variant_warm_and_preserves_mismatch():
    """Mechanism equality is within a variant, not falsely imposed between different warm data."""
    queries = {name: Query() for pair in comparison.GOAL_PAIRS for name in pair}
    methods = {}
    for variant in comparison.VARIANTS:
        for mode in comparison.EXECUTION_MODES:
            methods[comparison._method_id(mode, variant)] = {name: {
                "trace": {"own_warm_variant": variant, "action": "A"},
                "root_metrics": {"reward": 1, "failure": 0, "success": 0, "value": 1}}
                for name in queries}
    methods["online_legacy"]["goal_1_risk_1"]["trace"]["action"] = "B"
    result = comparison._goal_pair_diagnostics(_case(), methods, queries)
    assert result["goal_mass_excluded"]
    assert len(result["comparisons"]) == 8
    assert sum(row["all_equal"] for row in result["comparisons"]) == 7
    assert all(row["all_equal"] for row in result["comparisons"] if row["variant"] == "MASS_BOUND")
    boundary = replace(_case(), board=tuple(range(3, 11)) + (0,) * 8)
    assert comparison._goal_pair_diagnostics(boundary, methods, queries)["comparisons"] == []


def test_mass_certificate_matches_all_frozen_roster_groups():
    """Board entries are ranks, so rank sums must not classify all16 roots as mass excluded."""
    path = Path(__file__).resolve().parents[1] / "reports/controlled_predictive_cohort_roster_v14.json"
    roster = json.loads(path.read_text())
    excluded = []
    for row in roster["cases"]:
        case = V7Case(**row["case"])
        result = comparison._mass_certificate(case)
        assert result == {field: row[field] for field in ("total_tile_mass", "mass_plus_4h", "goal_mass_excluded")}
        if result["goal_mass_excluded"]:
            excluded.append(case.name)
    assert len(excluded) == 5
    assert excluded == roster["root_mass_groups"]["goal_mass_excluded"]
