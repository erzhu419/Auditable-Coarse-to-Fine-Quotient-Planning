from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.science import controlled_predictive_incremental_v13 as incremental
from acfqp.science import controlled_predictive_snapshot_v19 as reconstruction
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_execution_v13 import ExactEnvironment, evaluate_execution
from acfqp.science.controlled_predictive_execution_v17 import evaluate_balanced_gap_execution
from acfqp.science.controlled_predictive_mass_bound_v14 import MassBoundPlannerState
from acfqp.science.controlled_predictive_partial_v12 import BoardProfile
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState


def _fixture(monkeypatch):
    model = FiniteModel({0: 2, 1: 1, 2: 1, 3: 0, 4: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "LOST", 4: "CUTOFF"},
        {(0, "LEFT"): (Outcome(1, 1, 0),), (0, "RIGHT"): (Outcome(1, 2, 0),),
         **{(state, action): (Outcome(.5, 3, 0), Outcome(.5, 4, 0))
            for state in (1, 2) for action in ("LEFT", "RIGHT")}}, (0,))
    boards = {state: (state,) + (0,) * 15 for state in model.layers}
    closure = DevelopmentClosure(model, boards, ("toy",), {"states": 5}, .01)
    keys = {state: (model.layers[state], board) for state, board in boards.items()}
    states = {key: state for state, key in keys.items()}
    def profile(key, work):
        work["states_profiled"] += 1
        status = model.terminal[states[key]]
        actions = ("LEFT", "RIGHT") if status == "ACTIVE" else ()
        return BoardProfile(status, actions, tuple((action, 0) for action in actions), 2048)
    monkeypatch.setattr(incremental, "profile", profile)
    queries = {"risk": Query(1, 1, 0)}
    warm = MassBoundPlannerState(keys[0], queries)
    def observed(pair):
        return tuple((row.probability, keys[row.next_state], row.reward) for row in model.rows[states[pair[0]], pair[1]])
    for action in ("LEFT", "RIGHT"):
        warm.observe_row(keys[0], action, observed((keys[0], action)))
    _, intervals = warm.freeze()
    prefix = {"row_budget": 32, "actual_rows_acquired": 2, "physical_sample_draws_in_prefix": 512,
        "requested_row_order": reconstruction._json_structure(warm.row_order), "stop_reason": "ROW_BUDGET_REACHED",
        "root_intervals": {name: asdict(value) for name, value in intervals.items()}}
    class Provider:
        def __init__(self):
            self.work_counts = Counter()
            self.provider_seconds = 0.0
        def sample(self, key, action):
            return self.sample_batch(key, action, 0)
        def sample_batch(self, key, action, index):
            self.work_counts.update(row_requests=1, physical_draws=256)
            return observed((key, action))
    environment = ExactEnvironment.from_closure(closure)
    base = evaluate_execution(warm, Provider(), "risk", environment, mode="online", total_row_cap=14)
    cached = evaluate_balanced_gap_execution(CachedGapPlannerState.from_warm(warm), Provider(), "risk", environment, total_batch_cap=14)
    assert cached["trace"]["acquisition_stop_reason"] == "DECISION_QUOTA_EXHAUSTED"
    assert any(row["batch_index"] > 0 for row in cached["trace"]["observed_batches"])
    case = {"name": "toy", "board": list(boards[0]), "horizon": 2}
    context = {"context_index": 0, "case_name": "toy", "sample_seed": 1, "query_name": "risk",
        "direction": "regression", "case": case, "history": [reconstruction._json_structure(keys[0])],
        "target_key": reconstruction._json_structure(keys[0]), "divergence": {"history_edges": []}}
    roster = {"contexts": [context], "initial_query_order": ["risk"], "queries": {"risk": asdict(queries["risk"])},
        "snapshot_manifest": [{"context_index": 0, "method": method, "phase": phase}
            for method in reconstruction.METHODS for phase in reconstruction.PHASES]}
    payload = {"settings": {"query_order": ["risk"], "queries": roster["queries"]},
        "cases": [{"case": case, "sampled_runs": [{"sample_seed": 1, "shared_warm": {"prefix": prefix},
            "methods": {"online_mass_bound": {"risk": base}, "online_cached_balanced_gap_stop": {"risk": cached}}}]}]}
    events = []
    def stage(*args):
        assert args[1] == 1 and args[3:] == ("MASS_BOUND", (32,), 256)
        events.append("warm")
        return {32: SimpleNamespace(state=warm, report=prefix)}, {"actual_rows_acquired": 2, "physical_sample_draws": 512}
    monkeypatch.setattr(reconstruction, "_stage_a", stage)
    return SimpleNamespace(warm=warm, payload=payload, roster=roster, closure=closure, events=events, provider=Provider)


def test_last_batch_snapshots_preserve_counts_observations_and_policy_without_suffix_sampling(monkeypatch):
    fixture = _fixture(monkeypatch)
    def forbidden(*args, **kwargs):
        raise AssertionError("reconstruction acquired a new suffix batch or chose a new row")
    monkeypatch.setattr(fixture.provider, "sample_batch", forbidden)
    monkeypatch.setattr(MassBoundPlannerState, "select_row", forbidden)
    monkeypatch.setattr(CachedGapPlannerState, "select_resample", forbidden)
    frozen, validation, accounting = reconstruction.reconstruct_snapshots(fixture.payload, fixture.roster)
    assert len(frozen) == 4 and fixture.events == ["warm"]
    assert validation["all_retained_checks_passed"] and accounting["validated_last_gap_assessments"] == 1
    assert accounting["new_independent_statistical_draws"] == accounting["suffix_provider_calls"] == 0
    assert accounting["warm_physical_draws"] == 512
    for before, after in (frozen[:2], frozen[2:]):
        assert reconstruction._batches(after.state) == reconstruction._batches(before.state) + 1
        cache = after.state.solve("risk")
        source = fixture.payload["cases"][0]["sampled_runs"][0]["methods"][reconstruction.METHODS[after.identity["method"]]]["risk"]["trace"]
        assert (cache.policy[after.target_key], cache.lower[after.target_key], cache.upper[after.target_key]) == (source["action"], source["lower"], source["upper"])
    record = reconstruction.snapshot_record(frozen[-1])
    assert sum(row["batch_count"] for row in record["rows"]) == record["spent_batches"]
    assert sum(count["count"] for row in record["integer_outcome_counts"] for count in row["counts"]) == 256 * record["spent_batches"]
    assert record["profiles"] and record["policy_and_intervals"]


@pytest.mark.parametrize("field", ["batch_index", "last_gap", "observation"])
def test_retained_mismatch_stops_reconstruction(monkeypatch, field):
    fixture = _fixture(monkeypatch)
    payload = deepcopy(fixture.payload)
    trace = payload["cases"][0]["sampled_runs"][0]["methods"]["online_cached_balanced_gap_stop"]["risk"]["trace"]
    if field == "batch_index":
        trace["observed_batches"][-1]["batch_index"] += 1
    elif field == "last_gap":
        trace["gap_assessments"][-1]["gap"] += .1
    else:
        row = trace["observed_batches"][-1]["outcomes"]
        # Move mass from failure to cutoff so this observed row changes the
        # retained maximizing value; an unused losing row need not do so.
        row[0][0], row[1][0] = .25, .75
    with pytest.raises(ValueError, match="V19 retained reconstruction mismatch"):
        reconstruction.reconstruct_snapshots(payload, fixture.roster)


def test_snapshot_artifact_completes_before_truth_construction(monkeypatch, tmp_path):
    fixture = _fixture(monkeypatch)
    script = Path(__file__).resolve().parents[1] / "scripts/run_controlled_predictive_decomposition_v19.py"
    spec = importlib.util.spec_from_file_location("v19_cli_test", script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    source, roster_path = tmp_path / "v18.json.gz", tmp_path / "roster.json"
    output, snapshots = tmp_path / "report.json", tmp_path / "snapshots.json.gz"
    with gzip.open(source, "wt") as handle:
        json.dump(fixture.payload, handle)
    roster_path.write_text(json.dumps(fixture.roster))
    def closure(**kwargs):
        with gzip.open(snapshots, "rt") as handle:
            artifact = json.load(handle)
        assert len(artifact["snapshots"]) == 4
        assert artifact["exact_evaluator_constructed"] is False
        assert fixture.events == ["warm"]
        fixture.events.append("truth")
        return fixture.closure
    monkeypatch.setattr(cli, "build_development_closure", closure)
    report, _ = cli.run_decomposition(source, roster_path, output, snapshots)
    assert fixture.events == ["warm", "truth"] and report["status"] == "DIAGNOSTIC_COMPLETE"
    assert report["all_snapshots_persisted_before_oracle"]
    assert len(report["last_batch_effects"]) == 2
