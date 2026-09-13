"""Freeze common V20 data immediately before the first allocation disagreement."""

from collections import Counter, deque
from dataclasses import asdict, dataclass
from time import perf_counter

from .controlled_predictive_comparison_v14 import _json_structure, _stage_a
from .controlled_predictive_quotient_v1 import Query
from .controlled_predictive_score_cache_v18 import CachedGapPlannerState
from .controlled_predictive_variance_v20 import VarianceGapPlannerState
from .controlled_predictive_snapshot_v19 import PREFIX_FIELDS


METHODS = {"CACHED": "online_cached_balanced_gap_stop", "VARIANCE": "online_variance_gap_stop"}


class ReconstructionMismatch(ValueError):
    pass


def _require(value, message):
    if not value:
        raise ReconstructionMismatch(message)


def _key(value):
    return value[0], tuple(value[1])


def _request_key(request):
    return request["row_key"], request["batch_index"], request["kind"]


def _source_node(node):
    return {key: value for key, value in node.items() if key != "children"}


def first_sampling_divergence(cached, variance):
    """Breadth-first search only paths with identical earlier data and actions."""
    queue = deque([(cached, variance, [], [], [])])
    while queue:
        left, right, ancestors, indices, edges = queue.popleft()
        _require(left["key"] == right["key"], "shared history keys differ")
        if "action" not in left or "action" not in right:
            _require(left == right, "shared terminal histories differ")
            continue
        for field in ("quota", "batches_before", "rows_before"):
            _require(left[field] == right[field], "source " + field + " differs before acquisition")
        requested = [node["requested_batches"] for node in (left, right)]
        observed = [node["observed_batches"] for node in (left, right)]
        for r, o in zip(requested, observed):
            _require(len(r) == len(o), "source request/observation lengths differ")
        for index in range(min(map(len, requested))):
            _require(left["gap_assessments"][index] == right["gap_assessments"][index], "shared pre-request gap diagnostics differ")
            if _request_key(requested[0][index]) != _request_key(requested[1][index]):
                return {"ancestors": ancestors, "history_child_indices": indices, "history_edges": edges,
                    "source_nodes": {"CACHED": _source_node(left), "VARIANCE": _source_node(right)},
                    "request_index": index, "target_key": left["key"]}
            _require(observed[0][index] == observed[1][index], "identical source requests have different observations")
        _require(len(requested[0]) == len(requested[1]), "source stopping differs before any allocation disagreement")
        for field in ("action", "lower", "upper", "batches_after", "rows_after", "gap_assessments", "acquisition_stop_reason"):
            _require(left[field] == right[field], "shared source decision differs: " + field)
        _require(len(left["children"]) == len(right["children"]), "shared child counts differ")
        for child_index, (a, b) in enumerate(zip(left["children"], right["children"])):
            _require(a["probability"] == b["probability"] and a["reward"] == b["reward"]
                     and a["node"]["key"] == b["node"]["key"], "shared history edge differs")
            queue.append((a["node"], b["node"], ancestors + [_source_node(left)],
                indices + [child_index], edges + [{"action": left["action"],
                    "probability": a["probability"], "reward": a["reward"]}]))
    return None


def _replay_batch(state, request, observed, accounting):
    started = perf_counter()
    pair = _key(request["row_key"][0]), request["row_key"][1]
    _require(request["row_key"] == observed["row_key"], "retained requested/observed row differs")
    _require(request["batch_index"] == observed["batch_index"] == state.batch_counts.get(pair, 0), "retained batch index differs")
    expected_kind = "FIRST_OBSERVATION" if pair not in state.rows else "REPEAT_OBSERVATION"
    _require(request["kind"] == expected_kind, "retained observation kind differs")
    state.observe_batch(*pair, tuple((weight, _key(successor), reward) for weight, successor, reward in observed["outcomes"]))
    accounting["retained_batches_replayed"] += 1
    accounting["retained_draws_replayed"] += 256
    accounting["retained_outcome_entries_replayed"] += len(observed["outcomes"])
    accounting["retained_replay_seconds"] += perf_counter() - started


def _check_start(state, node):
    _require(len(state.rows) == node["rows_before"] and state.spent_batches == node["batches_before"], "decision entry row/batch totals differ")
    _require(node["quota"] == (128 - node["batches_before"]) // node["key"][0], "original decision quota differs")


def fixed_panel(state, target):
    """Only the common observed graph defines the evaluation panel."""
    pending, seen, panel = [target], set(), set()
    while pending:
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        if state.profiles[key].status != "ACTIVE":
            continue
        panel.add(key)
        for action in state.profiles[key].legal_actions:
            for _, successor, _ in state.rows.get((key, action), ()):
                pending.append(successor)
    return tuple(sorted(panel))


@dataclass
class CommonSnapshot:
    identity: dict
    state: CachedGapPlannerState
    query_name: str
    target_key: tuple
    panel: tuple
    requested_batch_count: int
    request_index: int
    source_nodes: dict
    history: list
    history_edges: list


def _reconstruct_context(warm, context, divergence, accounting):
    started = perf_counter()
    state = warm.clone()
    accounting["reconstruction_clone_seconds"] += perf_counter() - started
    accounting["reconstruction_clones"] += 1
    query_name = context["query_name"]
    for node in divergence["ancestors"]:
        started = perf_counter()
        _check_start(state, node)
        accounting["reconstruction_validation_seconds"] += perf_counter() - started
        state.observe_state(_key(node["key"]))
        for request, observed in zip(node["requested_batches"], node["observed_batches"]):
            _replay_batch(state, request, observed, accounting)
        started = perf_counter()
        cache = state.solve(query_name)
        key = _key(node["key"])
        _require(cache.policy[key] == node["action"] and cache.lower[key] == node["lower"] and cache.upper[key] == node["upper"], "replayed ancestor action/interval differs")
        _require(len(state.rows) == node["rows_after"] and state.spent_batches == node["batches_after"], "replayed ancestor final counts differ")
        accounting["reconstruction_validation_seconds"] += perf_counter() - started
    node = divergence["source_nodes"]["CACHED"]
    index = divergence["request_index"]
    started = perf_counter()
    _check_start(state, node)
    accounting["reconstruction_validation_seconds"] += perf_counter() - started
    target = _key(node["key"])
    state.observe_state(target)
    for request, observed in zip(node["requested_batches"][:index], node["observed_batches"][:index]):
        _replay_batch(state, request, observed, accounting)
    started = perf_counter()
    _require(state.spent_batches == node["batches_before"] + index, "common spent count differs")
    budget = node["quota"] - index
    _require(budget >= 0 and state.spent_batches + budget <= 128, "remaining local budget differs")
    diagnostic = _json_structure(asdict(state.assess_gap(target, query_name)))
    _require(not diagnostic["separated"], "source request occurred after original gap stop")
    for arm, state_type in (("CACHED", CachedGapPlannerState), ("VARIANCE", VarianceGapPlannerState)):
        source = divergence["source_nodes"][arm]
        _require(diagnostic == source["gap_assessments"][index], "reconstructed source gap diagnostic differs")
        probe = state.clone()
        probe.__class__ = state_type
        pair = probe.select_row(target, query_name)
        kind = "FIRST_OBSERVATION"
        if pair is None:
            pair = probe.select_resample(target, query_name, mode="BALANCED")
            kind = "REPEAT_OBSERVATION"
        _require(pair is not None, "source request has no reconstructed candidate")
        request = {"row_key": _json_structure(pair), "batch_index": probe.batch_counts.get(pair, 0), "kind": kind}
        _require(request == source["requested_batches"][index], "reconstructed first request differs for " + arm)
    accounting["reconstruction_validation_seconds"] += perf_counter() - started
    accounting["validated_first_requests"] += 2
    started = perf_counter()
    panel = fixed_panel(state, target)
    accounting["panel_construction_seconds"] += perf_counter() - started
    identity = {key: value for key, value in context.items() if key not in ("case", "query")}
    return CommonSnapshot(identity, state, query_name, target, panel, budget, index,
        divergence["source_nodes"], [node["key"] for node in divergence["ancestors"]] + [divergence["target_key"]],
        divergence["history_edges"])


def state_record(state, query_name):
    cache = state.solve(query_name)
    return {"state_type": type(state).__name__, "root": _json_structure(state.root),
        "query": asdict(state.queries[query_name]), "spent_batches": state.spent_batches,
        "profiles": [{"key": _json_structure(key), **asdict(profile)} for key, profile in sorted(state.profiles.items())],
        "row_order": _json_structure(state.row_order),
        "rows": [{"row_key": _json_structure(pair), "outcomes": _json_structure(row), "batch_count": state.batch_counts[pair],
            "integer_counts": [{"successor": _json_structure(successor), "reward": reward, "count": count}
                               for (successor, reward), count in sorted(state.outcome_counts[pair].items())]}
            for pair, row in state.rows.items()],
        "policy_and_intervals": [{"key": _json_structure(key), "action": cache.policy.get(key),
            "lower": cache.lower[key], "upper": cache.upper[key]} for key in sorted(state.profiles)],
        "action_intervals": [{"row_key": _json_structure(pair), "lower": cache.q_lower[pair], "upper": upper}
                             for pair, upper in sorted(cache.q_upper.items())]}


def common_record(snapshot):
    return {"identity": snapshot.identity, "status": "READY", "target_key": _json_structure(snapshot.target_key),
        "panel": _json_structure(snapshot.panel), "requested_batch_count": snapshot.requested_batch_count,
        "request_index": snapshot.request_index, "history": snapshot.history, "history_edges": snapshot.history_edges,
        "source_nodes": snapshot.source_nodes, "state": state_record(snapshot.state, snapshot.query_name)}


def reconstruct_common_snapshots(payload, roster):
    started_all = perf_counter()
    _require(payload["settings"]["query_order"] == roster["initial_query_order"], "warm query order differs")
    _require(payload["settings"]["queries"] == roster["queries"], "warm query weights differ")
    queries = {name: Query(**payload["settings"]["queries"][name]) for name in payload["settings"]["query_order"]}
    source = {(case["case"]["name"], run["sample_seed"]): (case["case"], run)
              for case in payload["cases"] for run in case["sampled_runs"]}
    accounting, warms, warm_errors, validation = Counter(), {}, {}, []
    for context in roster["contexts"]:
        identity = context["case_name"], context["sample_seed"]
        if identity in warms or identity in warm_errors:
            continue
        case, run = source[identity]
        started = perf_counter()
        snapshots, trajectory = _stage_a((case["horizon"], tuple(case["board"])), identity[1], queries, "MASS_BOUND", (32,), 256)
        accounting["warm_regeneration_seconds"] += perf_counter() - started
        accounting["warm_prefix_count"] += 1
        accounting["warm_physical_batches"] += trajectory["actual_rows_acquired"]
        accounting["warm_physical_draws"] += trajectory["physical_sample_draws"]
        warm = snapshots[32]
        started = perf_counter()
        checks = {field: _json_structure(warm.report[field]) == run["shared_warm"]["prefix"][field] for field in PREFIX_FIELDS}
        validation.append({"case_name": identity[0], "sample_seed": identity[1], "field_equal": checks, "passed": all(checks.values())})
        accounting["reconstruction_validation_seconds"] += perf_counter() - started
        if not all(checks.values()):
            warm_errors[identity] = "regenerated warm differs from retained prefix"
            continue
        started = perf_counter()
        warms[identity] = CachedGapPlannerState.from_warm(warm.state)
        accounting["warm_conversion_seconds"] += perf_counter() - started
        accounting["warm_conversion_count"] += 1
    frozen, records = [], []
    for context in roster["contexts"]:
        identity = context["case_name"], context["sample_seed"]
        record = {"identity": {key: value for key, value in context.items() if key not in ("case", "query")}}
        if identity in warm_errors:
            records.append(record | {"status": "RECONSTRUCTION_MISMATCH", "reason": warm_errors[identity]})
            continue
        try:
            run = source[identity][1]
            started = perf_counter()
            divergence = first_sampling_divergence(*(run["methods"][method][context["query_name"]]["trace"] for method in METHODS.values()))
            accounting["source_divergence_search_seconds"] += perf_counter() - started
            if divergence is None:
                records.append(record | {"status": "NO_SAMPLING_DIVERGENCE"})
                continue
            snapshot = _reconstruct_context(warms[identity], context, divergence, accounting)
            if snapshot.requested_batch_count == 0:
                records.append(record | {"status": "NO_REMAINING_LOCAL_QUOTA"})
                continue
            frozen.append(snapshot)
            records.append(record | {"status": "READY"})
        except ReconstructionMismatch as error:
            records.append(record | {"status": "RECONSTRUCTION_MISMATCH", "reason": str(error)})
    accounting["reconstruction_wall_seconds"] = perf_counter() - started_all
    accounting["retained_suffix_provider_calls"] = 0
    return frozen, records, {"warm_prefixes": validation}, dict(accounting)


__all__ = ("CommonSnapshot", "ReconstructionMismatch", "first_sampling_divergence", "fixed_panel",
           "reconstruct_common_snapshots", "common_record", "state_record")
