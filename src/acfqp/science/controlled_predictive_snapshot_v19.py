"""Reconstruct fixed V18 decision snapshots without acquiring suffix samples."""

from collections import Counter
from dataclasses import asdict, dataclass
from time import perf_counter

from .controlled_predictive_comparison_v14 import _json_structure, _stage_a
from .controlled_predictive_quotient_v1 import Query
from .controlled_predictive_score_cache_v18 import CachedGapPlannerState


METHODS = {"BASE": "online_mass_bound", "CACHED": "online_cached_balanced_gap_stop"}
PHASES = ("BEFORE_LAST_BATCH", "AFTER_LAST_BATCH")
PREFIX_FIELDS = ("row_budget", "actual_rows_acquired", "physical_sample_draws_in_prefix",
                 "requested_row_order", "stop_reason", "root_intervals")


def _key(value):
    return value[0], tuple(value[1])


def _pair(value):
    return _key(value[0]), value[1]


def _batches(state):
    return state.spent_batches if hasattr(state, "spent_batches") else len(state.rows)


def _require(equal, message):
    if not equal:
        raise ValueError("V19 retained reconstruction mismatch: " + message)


@dataclass
class FrozenSnapshot:
    identity: dict
    state: object
    query_name: str
    target_key: tuple
    last_observation: dict


def _validate_node(state, node, query_name, accounting, *, before):
    started = perf_counter()
    suffix = "before" if before else "after"
    _require(len(state.rows) == node["rows_" + suffix], "distinct rows " + suffix)
    if "batches_" + suffix in node:
        _require(_batches(state) == node["batches_" + suffix], "batch count " + suffix)
    if not before:
        cache = state.solve(query_name)
        key = _key(node["key"])
        _require(cache.policy[key] == node["action"], "selected action")
        _require(cache.lower[key] == node["lower"] and cache.upper[key] == node["upper"], "decision interval")
    accounting["validated_decision_boundaries"] += 1
    accounting["state_validation_seconds"] += perf_counter() - started


def _replay_observation(state, observation, requested, accounting):
    started = perf_counter()
    pair = _pair(observation["row_key"])
    if isinstance(requested, dict):
        _require(_pair(requested["row_key"]) == pair, "requested batch row")
        _require(requested["batch_index"] == observation["batch_index"], "requested batch index")
    else:
        _require(_pair(requested) == pair, "requested first row")
    row = tuple((weight, _key(successor), reward) for weight, successor, reward in observation["outcomes"])
    if hasattr(state, "batch_counts"):
        _require(observation["batch_index"] == state.batch_counts.get(pair, 0), "retained batch index")
        state.observe_batch(*pair, row)
    else:
        _require(pair not in state.rows, "BASE cannot repeat a row")
        state.observe_row(*pair, row)
    accounting["retained_suffix_batches_replayed"] += 1
    accounting["retained_suffix_draws_replayed"] += 256
    accounting["retained_suffix_outcome_entries_replayed"] += len(row)
    accounting["retained_suffix_replay_seconds"] += perf_counter() - started


def replay_history(warm_state, trace, context, method, accounting):
    """Replay only the recorded shared path and freeze its last local batch pair."""
    started = perf_counter()
    state = warm_state.clone()
    accounting["path_clone_seconds"] += perf_counter() - started
    accounting["path_clone_count"] += 1
    query_name = context["query_name"]
    history = context["history"]
    node = trace
    snapshots = []
    for position, expected_key in enumerate(history):
        _require(node["key"] == expected_key, "shared history key")
        _validate_node(state, node, query_name, accounting, before=True)
        started = perf_counter()
        state.observe_state(_key(node["key"]))
        accounting["retained_suffix_replay_seconds"] += perf_counter() - started
        observations = node["observed_batches"] if method == "CACHED" else node["observed_rows"]
        requested = node["requested_batches"] if method == "CACHED" else node["requested_rows"]
        _require(len(observations) == len(requested), "observation/request count")
        target = position == len(history) - 1
        if target:
            _require(node["key"] == context["target_key"], "target key")
            _require(bool(observations), "target has no last local batch")
        for index, (observation, request) in enumerate(zip(observations, requested)):
            if target and index == len(observations) - 1:
                if method == "CACHED":
                    started = perf_counter()
                    _require(node["acquisition_stop_reason"] == "DECISION_QUOTA_EXHAUSTED", "target stop reason")
                    _require(len(node["gap_assessments"]) == len(observations), "target assessments before paid batches")
                    actual = _json_structure(asdict(state.assess_gap(_key(node["key"]), query_name)))
                    _require(actual == node["gap_assessments"][-1], "last pre-batch gap assessment")
                    accounting["validated_last_gap_assessments"] += 1
                    accounting["state_validation_seconds"] += perf_counter() - started
                snapshots.append(_freeze(state, context, method, PHASES[0], observation, accounting))
            _replay_observation(state, observation, request, accounting)
        _validate_node(state, node, query_name, accounting, before=False)
        if target:
            snapshots.append(_freeze(state, context, method, PHASES[1], observations[-1], accounting))
        else:
            expected_edge = context["divergence"]["history_edges"][position]
            _require(node["action"] == expected_edge["action"], "shared ancestor action")
            candidates = [edge for edge in node["children"] if edge["node"]["key"] == history[position + 1]]
            _require(len(candidates) == 1, "shared child match")
            edge = candidates[0]
            _require(edge["probability"] == expected_edge["probability"] and edge["reward"] == expected_edge["reward"], "retained history edge")
            node = edge["node"]
    return snapshots


def _freeze(state, context, method, phase, observation, accounting):
    started = perf_counter()
    clone = state.clone()
    accounting["phase_clone_seconds"] += perf_counter() - started
    accounting["phase_clone_count"] += 1
    identity = {key: context[key] for key in ("context_index", "case_name", "sample_seed", "query_name", "direction")}
    identity.update(method=method, phase=phase)
    return FrozenSnapshot(identity, clone, context["query_name"], _key(context["target_key"]), observation)


def snapshot_record(snapshot):
    """Retain the complete observed model and solved current query, without exact truth."""
    state = snapshot.state
    cache = state.solve(snapshot.query_name)
    return {"identity": snapshot.identity, "query": asdict(state.queries[snapshot.query_name]),
        "root": _json_structure(state.root), "target_key": _json_structure(snapshot.target_key),
        "state_type": type(state).__name__, "last_observation": snapshot.last_observation,
        "spent_batches": _batches(state), "distinct_rows": len(state.rows),
        "profiles": [{"key": _json_structure(key), **asdict(profile)} for key, profile in sorted(state.profiles.items())],
        "row_order": _json_structure(state.row_order),
        "rows": [{"row_key": _json_structure(pair), "outcomes": _json_structure(row),
                  "batch_count": state.batch_counts[pair] if hasattr(state, "batch_counts") else 1}
                 for pair, row in state.rows.items()],
        "integer_outcome_counts": [{"row_key": _json_structure(pair),
            "counts": [{"successor": _json_structure(successor), "reward": reward, "count": count}
                       for (successor, reward), count in sorted(counts.items())]}
            for pair, counts in state.outcome_counts.items()] if hasattr(state, "outcome_counts") else [],
        "policy_and_intervals": [{"key": _json_structure(key), "action": cache.policy.get(key),
            "lower": cache.lower[key], "upper": cache.upper[key]} for key in sorted(state.profiles)],
        "action_intervals": [{"row_key": _json_structure(pair), "lower": cache.q_lower[pair], "upper": upper}
                             for pair, upper in sorted(cache.q_upper.items())]}


def reconstruct_snapshots(payload, roster):
    """Regenerate shared historical warm prefixes, then replay retained observations."""
    started_all = perf_counter()
    _require(payload["settings"]["query_order"] == roster["initial_query_order"], "frozen warm query order")
    _require(payload["settings"]["queries"] == roster["queries"], "frozen warm query weights")
    queries = {name: Query(**payload["settings"]["queries"][name]) for name in payload["settings"]["query_order"]}
    contexts = roster["contexts"]
    index = {(case["case"]["name"], run["sample_seed"]): (case["case"], run)
             for case in payload["cases"] for run in case["sampled_runs"]}
    accounting = Counter()
    warm_states = {}
    warm_checks = []
    for context in contexts:
        identity = context["case_name"], context["sample_seed"]
        if identity in warm_states:
            continue
        case, run = index[identity]
        root = case["horizon"], tuple(case["board"])
        started = perf_counter()
        snapshots, trajectory = _stage_a(root, identity[1], queries, "MASS_BOUND", (32,), 256)
        warm = snapshots[32]
        accounting["warm_regeneration_seconds"] += perf_counter() - started
        accounting["warm_prefix_count"] += 1
        accounting["warm_physical_batches"] += trajectory["actual_rows_acquired"]
        accounting["warm_physical_draws"] += trajectory["physical_sample_draws"]
        started = perf_counter()
        checks = {field: _json_structure(warm.report[field]) == run["shared_warm"]["prefix"][field] for field in PREFIX_FIELDS}
        _require(all(checks.values()), "warm prefix " + repr(identity))
        warm_checks.append({"case_name": identity[0], "sample_seed": identity[1], "field_equal": checks})
        accounting["state_validation_seconds"] += perf_counter() - started
        started = perf_counter()
        cached = CachedGapPlannerState.from_warm(warm.state)
        accounting["cached_conversion_seconds"] += perf_counter() - started
        accounting["cached_conversion_count"] += 1
        warm_states[identity] = {"BASE": warm.state, "CACHED": cached}
    frozen = []
    for context in contexts:
        identity = context["case_name"], context["sample_seed"]
        run = index[identity][1]
        for method, method_id in METHODS.items():
            frozen.extend(replay_history(warm_states[identity][method],
                run["methods"][method_id][context["query_name"]]["trace"], context, method, accounting))
    _require([{key: row.identity[key] for key in ("context_index", "method", "phase")} for row in frozen]
             == roster["snapshot_manifest"], "frozen snapshot manifest")
    accounting.update(new_independent_statistical_draws=0, suffix_provider_calls=0,
                      snapshots_frozen=len(frozen))
    accounting["reconstruction_wall_seconds"] = perf_counter() - started_all
    return frozen, {"warm_prefixes": warm_checks, "all_retained_checks_passed": True}, dict(accounting)


__all__ = ("FrozenSnapshot", "reconstruct_snapshots", "replay_history", "snapshot_record")
