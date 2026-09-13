"""Restore V21 observed models without replaying or acquiring any samples."""

from collections import Counter
from dataclasses import asdict
from time import perf_counter

from .controlled_predictive_comparison_v14 import _json_structure
from .controlled_predictive_partial_v12 import BoardProfile
from .controlled_predictive_quotient_v1 import Query
from .controlled_predictive_score_cache_v18 import CachedGapPlannerState
from .controlled_predictive_snapshot_v21 import (
    CommonSnapshot, ReconstructionMismatch, _key, _require, fixed_panel,
)
from .controlled_predictive_variance_v20 import VarianceGapPlannerState


def _pair(value):
    return _key(value[0]), value[1]


def restore_state(record, queries, *, query_name):
    """Restore pooled counts and prepare only the specified query's caches.

    Stored rows/profiles are the inputs. No deterministic board profiling,
    warm conversion, provider or exact closure is involved. The new engine
    accounting measures restoration/preparation, not historical observation.
    """
    started = perf_counter()
    _require(query_name in queries, "current query definition is missing")
    _require(asdict(queries[query_name]) == record["query"], "current query weights differ")
    state = object.__new__(CachedGapPlannerState)
    state.root = _key(record["root"])
    state.queries = dict(queries)
    state.mode, state.update_mode = "query_interval", "incremental"
    state.work_counts = Counter()
    state.profiles, state.rows, state.reverse_dependencies = {}, {}, {}
    state.outcome_counts, state.batch_counts = {}, {}
    state.caches, state.score_caches = {}, {}
    state.cursor, state.stop_reason = 0, None
    state.engine_seconds = state.clone_seconds = state.conversion_seconds = 0.0
    for item in record["profiles"]:
        key = _key(item["key"])
        _require(key not in state.profiles, "duplicate stored profile")
        state.profiles[key] = BoardProfile(item["status"], tuple(item["legal_actions"]),
            tuple(tuple(pair) for pair in item["immediate_rewards"]), item["mass"])
    _require(state.root in state.profiles, "stored root profile is missing")
    for item in record["rows"]:
        pair = _pair(item["row_key"])
        key, action = pair
        _require(pair not in state.rows, "duplicate stored row")
        _require(key in state.profiles and action in state.profiles[key].legal_actions,
                 "stored row has no legal parent action")
        batches = item["batch_count"]
        _require(type(batches) is int and batches > 0, "row batch count must be a positive integer")
        counts = Counter()
        for outcome in item["integer_counts"]:
            count_key = _key(outcome["successor"]), outcome["reward"]
            count = outcome["count"]
            _require(type(count) is int and count > 0, "pooled outcome count must be a positive integer")
            _require(count_key not in counts, "duplicate pooled outcome entry")
            counts[count_key] = count
        _require(sum(counts.values()) == 256 * batches, "pooled counts differ from row batch count")
        row = tuple((weight, _key(successor), reward) for weight, successor, reward in item["outcomes"])
        _require(len(row) == len(counts) and len({(s, r) for _, s, r in row}) == len(row),
                 "stored row support differs from pooled counts")
        for weight, successor, reward in row:
            _require((successor, reward) in counts and weight == counts[successor, reward] / (256 * batches),
                     "stored row probability differs from pooled counts")
            _require(successor in state.profiles and successor[0] == key[0] - 1,
                     "stored successor profile or horizon differs")
            state.reverse_dependencies.setdefault(successor, set()).add(key)
        state.rows[pair], state.outcome_counts[pair], state.batch_counts[pair] = row, counts, batches
    state.row_order = [_pair(pair) for pair in record["row_order"]]
    _require(state.row_order == list(state.rows), "stored row order differs from observed rows")
    state.spent_batches = record["spent_batches"]
    _require(type(state.spent_batches) is int and state.spent_batches == sum(state.batch_counts.values()),
             "stored total batches differ from row batch counts")
    state.work_counts.update(restored_profiles=len(state.profiles), restored_rows=len(state.rows),
        restored_pooled_entries=sum(map(len, state.outcome_counts.values())),
        restored_reverse_dependency_edges=sum(map(len, state.reverse_dependencies.values())),
        gap_cache_containers_initialized=1)
    cache = state.solve(query_name)
    state._gap_scores(query_name)
    policy = [{"key": _json_structure(key), "action": cache.policy.get(key),
        "lower": cache.lower[key], "upper": cache.upper[key]} for key in sorted(state.profiles)]
    actions = [{"row_key": _json_structure(pair), "lower": cache.q_lower[pair], "upper": upper}
        for pair, upper in sorted(cache.q_upper.items())]
    _require(policy == record["policy_and_intervals"], "restored policy or state intervals differ")
    _require(actions == record["action_intervals"], "restored action intervals differ")
    state.work_counts.update(restored_state_intervals_checked=len(policy),
                             restored_action_intervals_checked=len(actions))
    # Includes solve/gap time once, as part of this complete preparation span.
    state.engine_seconds = perf_counter() - started
    return state


def _validate_source(snapshot, work):
    state, target, name = snapshot.state, snapshot.target_key, snapshot.query_name
    index, budget = snapshot.request_index, snapshot.requested_batch_count
    _require(fixed_panel(state, target) == snapshot.panel, "restored fixed panel differs")
    requests = []
    for arm, state_type in (("CACHED", CachedGapPlannerState), ("VARIANCE", VarianceGapPlannerState)):
        source = snapshot.source_nodes[arm]
        _require(_key(source["key"]) == target, "source target differs")
        _require(source["quota"] == (128 - source["batches_before"]) // target[0], "source decision quota differs")
        _require(state.spent_batches == source["batches_before"] + index, "source common batch count differs")
        _require(budget == source["quota"] - index and budget > 0 and state.spent_batches + budget <= 128,
                 "source remaining local budget differs")
        _require(len(state.rows) == source["rows_before"] + sum(
            request["kind"] == "FIRST_OBSERVATION" for request in source["requested_batches"][:index]),
            "source common row count differs")
        probe = state.clone()
        probe.__class__ = state_type
        try:
            diagnostic = _json_structure(asdict(probe.assess_gap(target, name)))
            _require(not diagnostic["separated"] and diagnostic == source["gap_assessments"][index],
                     "restored gap diagnostic differs for " + arm)
            pair = probe.select_row(target, name)
            kind = "FIRST_OBSERVATION"
            if pair is None:
                pair, kind = probe.select_resample(target, name, mode="BALANCED"), "REPEAT_OBSERVATION"
            _require(pair is not None, "restored source request has no candidate")
            request = {"row_key": _json_structure(pair), "batch_index": probe.batch_counts.get(pair, 0), "kind": kind}
            _require(request == source["requested_batches"][index], "restored first request differs for " + arm)
            requests.append(request)
        finally:
            work.update(probe.work_counts - state.work_counts)
    _require(requests[0] != requests[1], "stored first requests no longer diverge")


def load_common_snapshots(payload):
    """Keep a status for every original identity; return validated starts only."""
    started_all = perf_counter()
    roster = payload["cohort_roster"]
    queries = {name: Query(**roster["queries"][name]) for name in roster["initial_query_order"]}
    records = {}
    for record in payload["snapshots"]:
        records.setdefault(record["identity"]["context_index"], []).append(record)
    snapshots, contexts = [], []
    accounting, prepare_work, source_work = Counter(), Counter(), Counter()
    for context in roster["contexts"]:
        index = context["context_index"]
        status = {"context_index": index, "status": "RESTORATION_MISMATCH"}
        candidates = records.get(index, [])
        if not candidates:
            contexts.append(status | {"status": "MISSING_COMMON_SNAPSHOT", "reason": "no retained common snapshot"})
            continue
        try:
            _require(len(candidates) == 1, "multiple retained common snapshots for identity")
            record = candidates[0]
            expected_identity = {key: value for key, value in context.items() if key not in ("case", "query")}
            _require(record["identity"] == expected_identity, "retained snapshot identity differs from roster")
            _require(record["status"] == "READY", "retained common snapshot is not ready")
            name = context["query_name"]
            started = perf_counter()
            try:
                state = restore_state(record["state"], queries, query_name=name)
                prepare_work.update(state.work_counts)
            finally:
                accounting["state_restore_and_current_query_prepare_seconds"] += perf_counter() - started
            snapshot = CommonSnapshot(record["identity"], state, name, _key(record["target_key"]),
                tuple(_key(key) for key in record["panel"]), record["requested_batch_count"],
                record["request_index"], record["source_nodes"], record["history"], record["history_edges"])
            started = perf_counter()
            try:
                _validate_source(snapshot, source_work)
            finally:
                accounting["source_validation_seconds"] += perf_counter() - started
            snapshots.append(snapshot)
            status["status"] = "READY"
            accounting["validated_first_requests"] += 2
        except (ValueError, KeyError, TypeError, IndexError) as error:
            status["reason"] = str(error)
        contexts.append(status)
    accounting.update(restored_contexts=len(snapshots), provider_calls=0, physical_sample_draws=0, closure_calls=0)
    accounting["restoration_wall_seconds"] = perf_counter() - started_all
    return snapshots, {"contexts": contexts, "all_passed": all(row["status"] == "READY" for row in contexts)}, {
        **accounting, "preparation_work_counts": dict(prepare_work), "source_validation_work_counts": dict(source_work)}
