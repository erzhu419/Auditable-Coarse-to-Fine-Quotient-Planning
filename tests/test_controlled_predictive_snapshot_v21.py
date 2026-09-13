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
from acfqp.science import controlled_predictive_snapshot_v21 as reconstruction
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_execution_v13 import ExactEnvironment
from acfqp.science.controlled_predictive_execution_v17 import evaluate_balanced_gap_execution
from acfqp.science.controlled_predictive_mass_bound_v14 import MassBoundPlannerState
from acfqp.science.controlled_predictive_partial_v12 import BoardProfile
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState
from acfqp.science.controlled_predictive_variance_v20 import VarianceGapPlannerState


def _fixture(monkeypatch):
    model = FiniteModel({0: 2, 1: 1, 2: 1, 3: 0, 4: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "LOST", 4: "CUTOFF"},
        {(0, "LEFT"): (Outcome(1, 1, 0),), (0, "RIGHT"): (Outcome(1, 2, 0),),
         **{(state, action): (Outcome(p, 3, reward), Outcome(1-p, 4, reward))
            for state, p, reward in ((1, .5, .3125), (2, .25, 0)) for action in ("LEFT", "RIGHT")}}, (0,))
    boards = {state: (state,) + (0,) * 15 for state in model.layers}
    closure = DevelopmentClosure(model, boards, ("toy",), {"states": 5}, .01)
    keys = {state: (model.layers[state], board) for state, board in boards.items()}
    states = {key: state for state, key in keys.items()}
    def profile(key, work):
        work["states_profiled"] += 1
        state = states[key]
        status = model.terminal[state]
        actions = ("LEFT", "RIGHT") if status == "ACTIVE" else ()
        return BoardProfile(status, actions, tuple((action, .3125 if state == 1 else 0) for action in actions), 2048)
    monkeypatch.setattr(incremental, "profile", profile)
    queries = {"risk": Query(1, 1, 0)}
    warm = MassBoundPlannerState(keys[0], queries)
    def observed(pair):
        return tuple((row.probability, keys[row.next_state], row.reward) for row in model.rows[states[pair[0]], pair[1]])
    for state in (0, 1, 2):
        for action in ("LEFT", "RIGHT"):
            warm.observe_row(keys[state], action, observed((keys[state], action)))
    _, intervals = warm.freeze()
    prefix = {"row_budget": 32, "actual_rows_acquired": 6, "physical_sample_draws_in_prefix": 1536,
        "requested_row_order": reconstruction._json_structure(warm.row_order), "stop_reason": "ROW_BUDGET_REACHED",
        "root_intervals": {name: asdict(value) for name, value in intervals.items()}}
    class Provider:
        def __init__(self, seed=1):
            self.work_counts = Counter()
            self.provider_seconds = 0.0
        def sample_batch(self, key, action, index):
            self.work_counts.update(row_requests=1, physical_draws=256)
            self.work_counts["first_batch_requests" if index == 0 else "repeat_batch_requests"] += 1
            return observed((key, action))
    environment = ExactEnvironment.from_closure(closure)
    cached = evaluate_balanced_gap_execution(CachedGapPlannerState.from_warm(warm), Provider(), "risk", environment, total_batch_cap=128)
    variance = evaluate_balanced_gap_execution(VarianceGapPlannerState.from_warm(warm), Provider(), "risk", environment, total_batch_cap=128)
    assert cached["trace"]["requested_batches"][0] == variance["trace"]["requested_batches"][0]
    assert cached["trace"]["requested_batches"][1] != variance["trace"]["requested_batches"][1]
    case = {"name": "toy", "board": list(boards[0]), "horizon": 2}
    context = {"context_index": 0, "case_name": "toy", "sample_seed": 1, "query_name": "risk",
        "group": "regression", "case": case, "source_v20_changed": True, "source_old_witness": False}
    roster = {"contexts": [context], "initial_query_order": ["risk"], "queries": {"risk": asdict(queries["risk"])}}
    payload = {"settings": {"query_order": ["risk"], "queries": roster["queries"]},
        "cases": [{"case": case, "sampled_runs": [{"sample_seed": 1, "shared_warm": {"prefix": prefix},
            "methods": {"online_cached_balanced_gap_stop": {"risk": cached}, "online_variance_gap_stop": {"risk": variance}}}]}]}
    events = []
    def stage(*args):
        assert args[1] == 1 and args[3:] == ("MASS_BOUND", (32,), 256)
        events.append("warm")
        return {32: SimpleNamespace(state=warm, report=prefix)}, {"actual_rows_acquired": 6, "physical_sample_draws": 1536}
    monkeypatch.setattr(reconstruction, "_stage_a", stage)
    return SimpleNamespace(warm=warm, payload=payload, roster=roster, closure=closure, events=events, provider=Provider)


def test_common_snapshot_precedes_different_request_and_retains_repeats(monkeypatch):
    fixture = _fixture(monkeypatch)
    def forbidden(*args, **kwargs):
        raise AssertionError("common reconstruction acquired a suffix batch")
    monkeypatch.setattr(fixture.provider, "sample_batch", forbidden)
    snapshots, records, _, accounting = reconstruction.reconstruct_common_snapshots(fixture.payload, fixture.roster)
    assert [row["status"] for row in records] == ["READY"]
    snapshot = snapshots[0]
    assert snapshot.request_index == 1 and snapshot.state.spent_batches == 7
    assert snapshot.requested_batch_count == (128-6)//2 - 1 == 60
    assert max(snapshot.state.batch_counts.values()) == 2
    assert len(snapshot.panel) == 3 and snapshot.target_key in snapshot.panel
    record = reconstruction.common_record(snapshot)
    assert sum(row["batch_count"] for row in record["state"]["rows"]) == 7
    assert sum(count["count"] for row in record["state"]["rows"] for count in row["integer_counts"]) == 7*256
    assert fixture.events == ["warm"] and accounting["retained_suffix_provider_calls"] == 0
    assert accounting["retained_batches_replayed"] == 1


def _node(horizon, name, different=False):
    key = [horizon, [name]]
    request = {"row_key": [key, "B" if different else "A"], "batch_index": 0, "kind": "FIRST_OBSERVATION"}
    return {"key": key, "quota": 1, "batches_before": 0, "rows_before": 0,
        "requested_batches": [request], "observed_batches": [{"row_key": request["row_key"], "batch_index": 0, "outcomes": []}],
        "gap_assessments": [{"separated": False}], "action": "A", "lower": 0, "upper": 0,
        "batches_after": 1, "rows_after": 1, "acquisition_stop_reason": "DECISION_QUOTA_EXHAUSTED", "children": []}


def test_search_is_breadth_first_and_keeps_original_child_order():
    left, right = _node(3, 0), _node(3, 0)
    a, b = _node(2, 1), _node(2, 1)
    a["children"] = [{"probability": 1, "reward": 0, "node": _node(1, 2)}]
    b["children"] = [{"probability": 1, "reward": 0, "node": _node(1, 2, True)}]
    left["children"] = [{"probability": .5, "reward": 0, "node": a}, {"probability": .5, "reward": 0, "node": _node(2, 3)}]
    right["children"] = [{"probability": .5, "reward": 0, "node": b}, {"probability": .5, "reward": 0, "node": _node(2, 3, True)}]
    result = reconstruction.first_sampling_divergence(left, right)
    assert result["target_key"] == [2, [3]] and result["history_child_indices"] == [1]
    left["children"][0]["node"] = _node(2, 1)
    right["children"][0]["node"] = _node(2, 1, True)
    assert reconstruction.first_sampling_divergence(left, right)["history_child_indices"] == [0]


def test_mismatched_common_observation_and_no_divergence_are_retained(monkeypatch):
    fixture = _fixture(monkeypatch)
    methods = fixture.payload["cases"][0]["sampled_runs"][0]["methods"]
    methods["online_variance_gap_stop"]["risk"]["trace"]["observed_batches"][0]["outcomes"][0][0] = .75
    snapshots, records, _, _ = reconstruction.reconstruct_common_snapshots(fixture.payload, fixture.roster)
    assert not snapshots and records[0]["status"] == "RECONSTRUCTION_MISMATCH"
    methods["online_variance_gap_stop"] = deepcopy(methods["online_cached_balanced_gap_stop"])
    snapshots, records, _, _ = reconstruction.reconstruct_common_snapshots(fixture.payload, fixture.roster)
    assert not snapshots and records[0]["status"] == "NO_SAMPLING_DIVERGENCE"


def test_all_common_models_precede_local_and_all_endpoints_precede_truth(monkeypatch, tmp_path):
    fixture = _fixture(monkeypatch)
    script = Path(__file__).resolve().parents[1] / "scripts/run_controlled_predictive_local_v21.py"
    spec = importlib.util.spec_from_file_location("v21_cli_test", script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    source, roster_path = tmp_path / "v20.json.gz", tmp_path / "roster.json"
    common, endpoints, output = tmp_path / "common.json.gz", tmp_path / "endpoints.json.gz", tmp_path / "report.json"
    with gzip.open(source, "wt") as handle:
        json.dump(fixture.payload, handle)
    roster_path.write_text(json.dumps(fixture.roster))
    monkeypatch.setattr(cli, "BatchRowSampleProvider", fixture.provider)
    local_original = cli.run_local_allocation
    def local(*args, **kwargs):
        with gzip.open(common, "rt") as handle:
            artifact = json.load(handle)
        assert len(artifact["snapshots"]) == 1 and not artifact["local_acquisition_started"]
        assert "truth" not in fixture.events
        fixture.events.append("local")
        return local_original(*args, **kwargs)
    def closure(**kwargs):
        with gzip.open(endpoints, "rt") as handle:
            artifact = json.load(handle)
        assert len(artifact["contexts"][0]["arms"]) == 2 and not artifact["oracle_constructed"]
        assert fixture.events == ["warm", "local", "local"]
        fixture.events.append("truth")
        return fixture.closure
    monkeypatch.setattr(cli, "run_local_allocation", local)
    monkeypatch.setattr(cli, "build_development_closure", closure)
    report, _ = cli.run_comparison(source, roster_path, common, endpoints, output)
    assert report["paired_complete_count"] == 1 and report["status"] == "LOCAL_COMPLETE"
    context = report["contexts"][0]
    assert all(row["source_validation"]["passed"] for row in context["arms"].values())
    assert all(row["local"]["completed_batches"] == context["requested_batch_count"] for row in context["arms"].values())
    assert all(row["evaluation"]["panel"]["state_count"] == len(context["panel"]) for row in context["arms"].values())
    assert report["accounting"]["local_physical_draws"] == 2 * context["requested_batch_count"] * 256
