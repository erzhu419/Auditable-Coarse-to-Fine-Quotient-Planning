from collections import Counter
from dataclasses import replace
from types import SimpleNamespace
import json
import random

import pytest

from acfqp.science import controlled_predictive_comparison_v12 as comparison
from acfqp.science import controlled_predictive_partial_v12 as core
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_cohort_v7 import V7Case
from acfqp.science.controlled_predictive_encoder_v7 import RuleEncoder
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
        {"name": "LOFO_A", "source_case_names": ["b"], "evaluation_case_names": ["b", "a", "target"],
         "target_family": "A", "case_splits": {"b": "TRAIN", "a": "FAMILY_HELD_OUT", "target": "FAMILY_HELD_OUT"}},
    ]}


class ToyPolicy:
    def __init__(self, policies, profiles):
        self.policies = policies
        self.profiles = profiles
        self.work_counts = Counter()
        self.fallback_seconds = 0.0

    def action(self, key, query_name):
        self.work_counts["policy_action_calls"] += 1
        if key in self.policies[query_name]:
            return self.policies[query_name][key]
        self.work_counts.update(fallback_calls=1, deterministic_swipe_calls=4)
        self.fallback_seconds += .00001
        return "A"


class ToyPrior:
    def __init__(self, shuffled):
        self.shuffled = shuffled
        self.calls = 0

    def __call__(self, key, query):
        self.calls += 1
        return {"A": float(not self.shuffled), "B": float(self.shuffled)}

    def diagnostics(self):
        return {"calls": self.calls}


def _setup(monkeypatch, cases=None):
    cases = _cases() if cases is None else cases
    closures = {case.name: _closure(case.board[0]) for case in cases}
    key_to_state = {comparison._key(closure, state): (closure, state)
                    for closure in closures.values() for state in closure.model.layers}
    events, providers, source_inputs, partial_inputs = [], [], [], []
    def build_closure(**kwargs):
        name = next(iter(kwargs["boards"]))
        events.append(("closure", name))
        return closures[name]
    monkeypatch.setattr(comparison, "build_development_closure", build_closure)
    monkeypatch.setattr(comparison, "row_seed", lambda seed, key, action: seed * 10000 + key[0] * 100 + key[1][0] * 2 + (action == "B"))
    class Provider:
        def __init__(self, seed, samples_per_row):
            self.seed, self.samples_per_row = seed, samples_per_row
            self.work_counts = Counter()
            self.provider_seconds = 0.0
            self.requests = []
            providers.append(self)
        def sample(self, key, action):
            closure, state = key_to_state[key]
            support = closure.model.rows[state, action]
            sampled = random.Random(comparison.row_seed(self.seed, key, action)).choices(
                support, weights=[o.probability for o in support], k=self.samples_per_row)
            counts = Counter((comparison._key(closure, o.next_state), o.reward) for o in sampled)
            self.requests.append((key, action))
            self.work_counts.update(exact_transition_row_calls=1, support_entries_enumerated=len(support), physical_draws=self.samples_per_row)
            self.provider_seconds += .00001
            return tuple((count / self.samples_per_row, successor, reward) for (successor, reward), count in sorted(counts.items()))
    monkeypatch.setattr(comparison, "RowSampleProvider", Provider)
    def source_fit(training, queries):
        source_inputs.append(training)
        events.append(("source", tuple(item.name for item in training)))
        return SimpleNamespace(encoder=RuleEncoder({}), compiled=comparison.compile_full_state(training[0].empirical),
            code_to_cell={}, q_by_query={name: {} for name in queries}, diagnostics={},
            make_priority=lambda shuffled=False: ToyPrior(shuffled))
    monkeypatch.setattr(comparison, "fit_source_prior", source_fit)
    def partial(root, provider, queries, *, budgets, mode, prior=None):
        partial_inputs.append((root, provider, tuple(queries), mode, prior))
        closure, _ = key_to_state[root]
        acquired, profiles, checkpoints = {}, {}, []
        ordered = [(root, "A"), (root, "B"), (comparison._key(closure, 1), "A")]
        for budget in budgets:
            for key, action in ordered[len(acquired):budget]:
                acquired[key, action] = provider.sample(key, action)
                for observed_key in (key, *(successor for _, successor, _ in acquired[key, action])):
                    observed_closure, state = key_to_state[observed_key]
                    status = observed_closure.model.terminal[state]
                    profiles[observed_key] = core.BoardProfile(status, ("A", "B") if status == "ACTIVE" else (), (("A", .1), ("B", 0)), 4)
                if prior:
                    prior(key, next(iter(queries.values())))
            policies = {name: {key: ("B" if key == root and name == "risk" and budget >= 2 else "A")
                for key, p in profiles.items() if p.status == "ACTIVE"} for name in queries}
            cp = SimpleNamespace(budget=budget, known_rows=dict(acquired), profiles=dict(profiles),
                frozen_policy=ToyPolicy(policies, dict(profiles)),
                root_intervals={name: core.RootInterval(0, 1, policies[name][root]) for name in queries},
                work_counts={"interval_solves": budget * len(queries)}, provider_counts=dict(provider.work_counts),
                provider_seconds=provider.provider_seconds, elapsed_seconds=.001 * budget,
                checkpoint_copy_seconds=.0001 * budget, prior_seconds=.00001 * budget if prior else 0,
                prior_diagnostics=prior.diagnostics() if prior else {}, stop_reason="BUDGET_EXHAUSTED")
            checkpoints.append(cp)
        events.append(("partial_frozen", mode))
        return tuple(checkpoints)
    monkeypatch.setattr(comparison, "run_partial", partial)
    return SimpleNamespace(closures=closures, events=events, providers=providers, source_inputs=source_inputs,
        partial_inputs=partial_inputs)


def _run(**kwargs):
    return comparison.run_comparison_v12(cases=_cases(), cohort_roster=_roster(), samples_per_row=4,
        sample_seeds=(123,), row_budgets=(1, 2, 3), queries={"reward": Query(), "risk": Query(1, 1, 0)}, **kwargs)


def test_full_rows_reuse_paid_support_and_match_requested_row_stream(monkeypatch):
    """Full baselines must neither re-enumerate support nor receive different row draws."""
    closure = comparison.build_development_closure(horizon=1, boards={"tiny": (1, 1) + (0,) * 14})
    provider = core.RowSampleProvider(832101)
    expected = {(state, action): provider.sample(comparison._key(closure, state), action)
                for state, action in closure.model.rows}
    monkeypatch.setattr(core, "_step_v1", lambda *args: pytest.fail("paid full support must be reused"))
    empirical, record = comparison._acquire_complete(closure, 832101, 256)
    for row_key, row in empirical.rows.items():
        assert tuple((o.probability, comparison._key(closure, o.next_state), o.reward) for o in row) == expected[row_key]
    assert record["reused_complete_support"] and record["additional_support_enumeration_calls"] == 0
    assert record["physical_sample_draws"] == len(closure.model.rows) * 256


def test_all_partial_checkpoints_freeze_before_target_support_and_truth(monkeypatch):
    """Complete target dynamics may not be used by a partial trajectory, even for source targets."""
    state = _setup(monkeypatch)
    reference, full = comparison._reference, comparison._full_arms
    def full_freeze(*args, **kwargs):
        assert [event[0] for event in state.events[-4:]] == ["partial_frozen"] * 4 or state.events[-1] == ("closure", "target")
        result = full(*args, **kwargs)
        state.events.append(("full_frozen",))
        return result
    def truth(*args, **kwargs):
        assert state.events[-1] == ("full_frozen",)
        state.events.append(("truth",))
        return reference(*args, **kwargs)
    monkeypatch.setattr(comparison, "_full_arms", full_freeze)
    monkeypatch.setattr(comparison, "_reference", truth)
    report = _run()
    assert state.events[:4] == [("closure", "a"), ("closure", "b"), ("source", ("a", "b")), ("source", ("b",))]
    target_closure_index = state.events.index(("closure", "target"))
    assert [event[0] for event in state.events[target_closure_index - 4:target_closure_index]] == ["partial_frozen"] * 4
    assert len(state.providers) == 24 and len({id(p) for p in state.providers}) == 24
    assert all(names == ("reward", "risk") for _, _, names, _, _ in state.partial_inputs)
    assert all(item.empirical is not state.closures[item.name].model for items in state.source_inputs for item in items)
    assert report["settings"]["query_order"] == ["reward", "risk"]
    assert report["completed_scenario_case_seed_runs"] == 6
    assert report["lofo_target_aggregate"]["audited_case_seed_run_count"] == 2
    json.dumps(report, allow_nan=False)


def test_nested_budgets_and_source_repeated_work_are_counted_physically(monkeypatch):
    """Prefix snapshots must not triple acquisition and a source target must retain its full source cost."""
    _setup(monkeypatch)
    report = _run()
    accounting = report["accounting"]
    assert accounting["physical_sample_draws_by_scope"] == {"source": 2 * 6 * 4, "partial": 6 * 4 * 3 * 4, "full_target_benchmarks": 6 * 6 * 4}
    assert accounting["frozen_partial_checkpoint_count"] == 6 * 4 * 3
    assert accounting["actual_complete_support_rows_enumerated_once_per_case"] == 3 * 6
    assert accounting["actual_partial_support_rows_enumerated"] == 6 * 4 * 3
    for scenario in report["scenarios"]:
        setup = scenario["source_fits"][0]["total_source_setup_seconds_attributed"]
        for record in scenario["cases"]:
            run = record["sampled_runs"][0]
            for arm, checkpoints in run["partial_arms"].items():
                assert [cp["actual_rows_acquired"] for cp in checkpoints] == [1, 2, 3]
                for cp in checkpoints:
                    expected = setup if arm in comparison.SOURCE_ARMS else 0
                    assert cp["standalone_source_setup_seconds"] == expected
                    assert cp["construction_plus_amortized_source_setup_seconds"] == pytest.approx(cp["construction_seconds"] + expected / 3)
            for benchmark in run["full_baselines"].values():
                assert benchmark["actual_rows_acquired"] == 6
                assert benchmark["acquisition_seconds_attributed"] == run["full_target_acquisition"]["acquisition_and_model_assembly_seconds"]


def test_exact_occupancy_distinguishes_recorded_unknown_action_from_fallback():
    """Unobserved actions and fallback calls have different deployment consequences."""
    closure = _closure()
    policy = {0: "A", 1: "A", 2: "A"}
    result = comparison._occupancy(closure, policy, {0: False, 1: True, 2: True},
        {0: True, 1: True, 2: True}, {0: 0, 1: 4, 2: 4})
    assert result["probability_reaching_unrecorded_state_fallback"] == 1
    assert result["expected_unrecorded_state_fallback_calls"] == 1
    assert result["expected_fallback_deterministic_swipes"] == 4
    assert result["probability_executing_any_unobserved_action"] == 1
    assert result["expected_unobserved_action_executions"] == 2
    assert not result["online_wall_clock_measured"]


def test_partial_quality_retains_true_added_loss_and_nonroot_witness(monkeypatch):
    """Matching root values must not hide a bad downstream action outside root occupancy."""
    _setup(monkeypatch)
    report = _run()
    cp = report["scenarios"][0]["cases"][0]["sampled_runs"][0]["partial_arms"]["bfs"][1]
    row = cp["queries"]["risk"]
    assert row["exact_lifted_root_metrics"]["value"] == pytest.approx(.1)
    assert row["root_extra_regret_over_full_state"] == pytest.approx(0)
    assert row["all_active_states"]["maximum_extra_regret_over_full_state"] == pytest.approx(.4)
    assert row["all_active_states"]["worst_added_loss_witness"]["state"] == 1
    assert row["all_active_states"]["worst_added_loss_witness"]["actual_metrics"]["failure"] == .5


def test_target_closure_failure_retains_all_frozen_budget_results(monkeypatch):
    """Audit closure limits must not erase already-paid partial trajectories or replace a target."""
    state = _setup(monkeypatch)
    def closure(**kwargs):
        name = next(iter(kwargs["boards"]))
        if name == "target":
            raise ValueError("complete closure exceeds max_nodes=1; no truncated model produced")
        return state.closures[name]
    monkeypatch.setattr(comparison, "build_development_closure", closure)
    report = _run()
    assert report["status"] == "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES"
    assert report["completed_scenario_case_seed_runs"] == 4
    assert report["retained_partial_scenario_case_seed_runs"] == 6
    for scenario in report["scenarios"]:
        record = scenario["cases"][-1]
        assert record["status"] == "AUDIT_CLOSURE_BUDGET_EXCEEDED"
        assert all(len(checkpoints) == 3 for checkpoints in record["sampled_runs"][0]["partial_arms"].values())
    assert report["accounting"]["partial_trajectory_count"] == 24


def test_fixed_example_exports_declared_query_policy_with_fallback(monkeypatch):
    """Fixed delivery must export the selected partial checkpoint, without a complete dynamics map."""
    cases = tuple(replace(case, name="v6_spawn_edge_rescue_2") if case.name == "target" else case for case in _cases())
    _setup(monkeypatch, cases)
    roster = _roster(cases)
    roster["scenarios"] = roster["scenarios"][:1]
    report = comparison.run_comparison_v12(cases=cases, cohort_roster=roster, samples_per_row=4,
        sample_seeds=(832101,), row_budgets=(1, 2, 128), queries={"reward": Query(), "risk": Query(1, 1, 0)})
    example = report["partial_policy_example"]
    assert example["arm"] == "source_priority" and example["row_budget"] == 128
    assert example["expected_root_actions"] == {"reward": "A", "risk": "B"}
    assert "compiled_model" not in example["artifact"]
    assert example["artifact"]["schema"]
