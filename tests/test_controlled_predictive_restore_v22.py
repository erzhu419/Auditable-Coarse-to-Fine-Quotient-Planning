from copy import deepcopy
from dataclasses import asdict
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_incremental_v13 as incremental
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_comparison_v14 import _json_structure
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_restore_v22 import load_common_snapshots, restore_state
from acfqp.science.controlled_predictive_snapshot_v21 import state_record
from acfqp.science.controlled_predictive_variance_v20 import VarianceGapPlannerState


@pytest.fixture(scope="module")
def payload():
    path = Path(__file__).resolve().parents[1] / "reports/controlled_predictive_common_snapshots_v21.json.gz"
    with gzip.open(path, "rt") as stream:
        return json.load(stream)


def _queries(payload):
    roster = payload["cohort_roster"]
    return {name: Query(**roster["queries"][name]) for name in roster["initial_query_order"]}


def _first_state(payload):
    record = payload["snapshots"][0]
    name = record["identity"]["query_name"]
    return restore_state(record["state"], _queries(payload), query_name=name), name


def _forbidden(*args, **kwargs):
    raise AssertionError("restoration must not profile boards or acquire samples/truth")


def test_all_retained_starts_match_policies_intervals_panel_gap_and_both_requests(payload, monkeypatch):
    monkeypatch.setattr(incremental, "profile", _forbidden)
    monkeypatch.setattr(BatchRowSampleProvider, "sample_batch", _forbidden)
    monkeypatch.setattr(DevelopmentClosure, "__init__", _forbidden)
    snapshots, validation, accounting = load_common_snapshots(payload)
    assert validation["all_passed"] and len(snapshots) == 22
    assert validation["contexts"] == [{"context_index": index, "status": "READY"} for index in range(22)]
    assert accounting["validated_first_requests"] == 44
    assert accounting["provider_calls"] == accounting["physical_sample_draws"] == accounting["closure_calls"] == 0
    assert accounting["state_restore_and_current_query_prepare_seconds"] > 0
    assert accounting["source_validation_seconds"] > 0
    assert accounting["restoration_wall_seconds"] >= (
        accounting["source_validation_seconds"] + accounting["state_restore_and_current_query_prepare_seconds"])
    for snapshot, record in zip(snapshots, payload["snapshots"]):
        state = snapshot.state
        assert list(state.queries) == payload["cohort_roster"]["initial_query_order"]
        assert {name: asdict(query) for name, query in state.queries.items()} == payload["cohort_roster"]["queries"]
        assert list(state.caches) == list(state.score_caches) == [snapshot.query_name]
        assert _json_structure(state_record(state, snapshot.query_name)) == record["state"]
        assert state.work_counts["batch_draws_inserted"] == state.work_counts["states_profiled"] == 0
        assert state.work_counts["query_cache_initializations"] == state.work_counts["gap_score_cache_initializations"] == 1


def test_pooled_repeats_restore_exact_scores_all_query_definitions_and_selectors(payload, monkeypatch):
    state, name = _first_state(payload)
    pair = state.row_order[-1]
    row = state.rows[pair]
    monkeypatch.setattr(incremental, "profile", _forbidden)
    monkeypatch.setattr(BatchRowSampleProvider, "sample_batch", _forbidden)
    state.observe_batch(*pair, row)
    _, successor, reward = row[0]
    state.observe_batch(*pair, ((1.0, successor, reward),))
    record = state_record(state, name)
    restored = restore_state(record, state.queries, query_name=name)
    assert restored.batch_counts[pair] == 3
    assert restored.spent_batches == state.spent_batches
    assert restored.outcome_counts == state.outcome_counts
    assert restored.rows == state.rows and restored.row_order == state.row_order
    assert restored.reverse_dependencies == state.reverse_dependencies
    assert list(restored.caches) == list(restored.score_caches) == [name]
    for query_name in state.queries:
        assert restored.solve(query_name) == state.solve(query_name)
        assert restored._gap_scores(query_name) == state._gap_scores(query_name)
        assert restored.assess_gap(state.root, query_name) == state.assess_gap(state.root, query_name)
        assert restored.select_row(state.root, query_name) == state.select_row(state.root, query_name)
        assert restored.select_resample(state.root, query_name, "BALANCED") == state.select_resample(state.root, query_name, "BALANCED")
        left, right = restored.clone(), state.clone()
        left.__class__ = right.__class__ = VarianceGapPlannerState
        assert left.select_resample(state.root, query_name, "BALANCED") == right.select_resample(state.root, query_name, "BALANCED")


def test_restored_clone_isolation_and_ancestor_invalidation(payload):
    state, name = _first_state(payload)
    original = state_record(state, name)
    pair = state.row_order[-1]
    child = state.clone()
    child.observe_batch(*pair, child.rows[pair])
    assert child.spent_batches == state.spent_batches + 1
    assert child.batch_counts[pair] == state.batch_counts[pair] + 1
    assert pair[0] in child.caches[name].dirty
    assert pair[0] in child.score_caches[name].dirty
    expected = {pair[0]}
    pending = [pair[0]]
    while pending:
        for parent in state.reverse_dependencies.get(pending.pop(), ()):
            if parent not in expected:
                expected.add(parent)
                pending.append(parent)
    assert expected <= child.caches[name].dirty
    assert expected <= child.score_caches[name].dirty
    child.reverse_dependencies[next(iter(child.reverse_dependencies))].clear()
    child.caches[name].lower[pair[0]] = -999
    child.score_caches[name].scores.lower[pair[0]] = -998
    assert not state.caches[name].dirty and not state.score_caches[name].dirty
    assert state_record(state, name) == original


@pytest.mark.parametrize("field,expected", [
    ("integer_counts", "pooled counts differ"),
    ("batch_count", "pooled counts differ"),
    ("spent_batches", "total batches differ"),
    ("outcomes", "probability differs"),
    ("row_order", "row order differs"),
    ("policy_and_intervals", "policy or state intervals differ"),
    ("action_intervals", "action intervals differ"),
])
def test_inconsistent_retained_model_is_rejected(payload, field, expected):
    record = deepcopy(payload["snapshots"][0]["state"])
    if field == "integer_counts":
        record["rows"][0][field][0]["count"] += 1
    elif field == "batch_count":
        record["rows"][0][field] += 1
    elif field == "spent_batches":
        record[field] += 1
    elif field == "outcomes":
        record["rows"][0][field][0][0] += 1 / 256
    elif field == "row_order":
        record[field].reverse()
    else:
        record[field][0]["lower"] += 1
    with pytest.raises(ValueError, match=expected):
        restore_state(record, _queries(payload), query_name=payload["snapshots"][0]["identity"]["query_name"])


def test_missing_and_mismatched_identities_remain_in_validation(payload):
    changed = deepcopy(payload)
    changed["snapshots"].pop(0)
    record = changed["snapshots"][0]
    record["source_nodes"]["CACHED"]["gap_assessments"][record["request_index"]]["gap"] += 1
    record = changed["snapshots"][1]
    record["source_nodes"]["VARIANCE"]["requested_batches"][record["request_index"]]["batch_index"] += 1
    snapshots, validation, accounting = load_common_snapshots(changed)
    assert not validation["all_passed"] and len(validation["contexts"]) == 22
    assert validation["contexts"][0]["status"] == "MISSING_COMMON_SNAPSHOT"
    assert "gap diagnostic differs" in validation["contexts"][1]["reason"]
    assert "first request differs" in validation["contexts"][2]["reason"]
    assert len(snapshots) == 19 and accounting["validated_first_requests"] == 38
    assert [snapshot.identity["context_index"] for snapshot in snapshots] == list(range(3, 22))
