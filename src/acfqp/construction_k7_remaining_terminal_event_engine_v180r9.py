"""Actual bounded mechanisms for six fresh V180 terminal observations.

The engine receives preregistered plain-data manifests.  It executes the
mechanism named by each terminal code and returns its full deterministic
trace.  It does not materialize accounting, select an outcome, or translate a
historical summary.  The controlled inputs are intentionally small so every
negative path can be independently replayed without a long scientific run.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v180r9 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


CONTROLLED_CODES_V180R9 = (
    TerminalCode.FULL_GROUND_EXACT_INFEASIBLE,
    TerminalCode.INTEGRITY_FAILURE,
    TerminalCode.PROTOCOL_FAILURE,
    TerminalCode.REBUILD_REQUIRED,
    TerminalCode.FALLBACK_CAP_EXHAUSTED,
    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED,
)


class ConstructionK7RemainingTerminalEventEngineV180r9Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RemainingTerminalEventEngineV180r9Error(message)


def _exact_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail("V180r9 event manifest is not one mapping")
    document = loads_canonical_json(canonical_json_bytes(dict(value)))
    if type(document) is not dict:
        raise AssertionError("canonical manifest replay changed")
    return document


def _graph(value: Any) -> dict[int, tuple[int, ...]]:
    if type(value) is not list or not value:
        _fail("V180r9 graph manifest is empty")
    graph: dict[int, tuple[int, ...]] = {}
    for row in value:
        if (
            type(row) is not dict
            or set(row) != {"state", "successors"}
            or type(row["state"]) is not int
            or row["state"] < 0
            or type(row["successors"]) is not list
            or any(type(item) is not int or item < 0 for item in row["successors"])
            or row["state"] in graph
        ):
            _fail("V180r9 graph row changed")
        graph[row["state"]] = tuple(row["successors"])
    if any(successor not in graph for rows in graph.values() for successor in rows):
        _fail("V180r9 graph is not closed")
    return graph


def _bfs(
    graph: Mapping[int, Sequence[int]],
    *,
    initial: int,
    target: int,
    expansion_cap: int | None,
) -> dict[str, Any]:
    if initial not in graph or type(target) is not int or target < 0:
        _fail("V180r9 graph query changed")
    queue = deque([initial])
    visited = {initial}
    expanded = []
    edge_rows = []
    cap_exhausted = False
    while queue:
        if expansion_cap is not None and len(expanded) >= expansion_cap:
            cap_exhausted = True
            break
        state = queue.popleft()
        expanded.append(state)
        if state == target:
            break
        for successor in graph[state]:
            edge_rows.append([state, successor])
            if successor not in visited:
                visited.add(successor)
                queue.append(successor)
    return {
        "initial_state": initial,
        "target_state": target,
        "expansion_cap": expansion_cap,
        "expanded_states": expanded,
        "evaluated_edges": edge_rows,
        "frontier_at_cutoff": list(queue),
        "target_reached": target in expanded,
        "cap_exhausted": cap_exhausted,
        "state_expansion_count": len(expanded),
        "edge_evaluation_count": len(edge_rows),
    }


@dataclass(frozen=True, slots=True)
class RemainingTerminalEventObservationV180r9:
    terminal_code: TerminalCode
    logical_occurrence_id: str
    event_document: Mapping[str, Any]
    counter_updates: Mapping[str, int]
    event_evidence_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "terminal_code": self.terminal_code.value,
            "logical_occurrence_id": self.logical_occurrence_id,
            "event_document": dict(self.event_document),
            "counter_updates": [
                {"path": path, "value": self.counter_updates[path]}
                for path in sorted(self.counter_updates)
            ],
            "event_evidence_id": self.event_evidence_id,
        }


def _observation(
    code: TerminalCode,
    occurrence_id: str,
    event: dict[str, Any],
    counters: dict[str, int],
) -> RemainingTerminalEventObservationV180r9:
    payload = {
        "schema": "acfqp.remaining_terminal_event_evidence.v180r9",
        "terminal_code": code.value,
        "logical_occurrence_id": occurrence_id,
        "event_document": event,
        "counter_updates": [
            {"path": path, "value": counters[path]} for path in sorted(counters)
        ],
        "mechanism_executed_in_current_occurrence": True,
        "historical_summary_translation_used": False,
        "development_fixture_only": False,
    }
    evidence_id = domains.extension_content_id_v180r9(
        domains.CONSTRUCTION_K7_EVENT_EVIDENCE_V180R9_DOMAIN,
        payload,
    )
    return RemainingTerminalEventObservationV180r9(
        code,
        occurrence_id,
        payload,
        counters,
        evidence_id,
    )


def execute_remaining_terminal_event_v180r9(
    manifest: Mapping[str, Any],
) -> RemainingTerminalEventObservationV180r9:
    document = _exact_manifest(manifest)
    required = {
        "schema",
        "terminal_code",
        "logical_occurrence_id",
        "input",
    }
    if (
        set(document) != required
        or document["schema"] != "acfqp.remaining_terminal_event_manifest.v180r9"
        or type(document["logical_occurrence_id"]) is not str
        or len(document["logical_occurrence_id"]) != 64
        or type(document["input"]) is not dict
    ):
        _fail("V180r9 event manifest schema changed")
    try:
        code = TerminalCode(document["terminal_code"])
    except (TypeError, ValueError) as error:
        raise ConstructionK7RemainingTerminalEventEngineV180r9Error(
            "V180r9 terminal code is unknown"
        ) from error
    if code not in CONTROLLED_CODES_V180R9:
        _fail("V180r9 event code is not in the controlled denominator")
    occurrence_id = document["logical_occurrence_id"]
    inputs = document["input"]

    if code is TerminalCode.FULL_GROUND_EXACT_INFEASIBLE:
        if set(inputs) != {"graph", "initial_state", "target_state"}:
            _fail("full-ground exact input changed")
        graph = _graph(inputs["graph"])
        trace = _bfs(
            graph,
            initial=inputs["initial_state"],
            target=inputs["target_state"],
            expansion_cap=None,
        )
        if trace["target_reached"] or trace["frontier_at_cutoff"]:
            _fail("full-ground exact occurrence did not prove infeasibility")
        event = {
            "mechanism": "EXHAUSTIVE_FINITE_GRAPH_REACHABILITY",
            "trace": trace,
            "all_reachable_states_expanded": True,
            "exact_infeasibility_proved": True,
        }
        counters = {
            "fallback.actions_evaluated": trace["edge_evaluation_count"],
            "fallback.ground_steps": trace["edge_evaluation_count"],
            "fallback.outcome_rows": trace["edge_evaluation_count"],
            "fallback.states_expanded": trace["state_expansion_count"],
            "route.attempts": 1,
            "route.successes": 1,
        }
    elif code is TerminalCode.INTEGRITY_FAILURE:
        if set(inputs) != {"committed_payload_hex", "submitted_payload_hex"}:
            _fail("integrity input changed")
        committed = bytes.fromhex(inputs["committed_payload_hex"])
        submitted = bytes.fromhex(inputs["submitted_payload_hex"])
        expected = hashlib.sha256(committed).hexdigest()
        observed = hashlib.sha256(submitted).hexdigest()
        if expected == observed:
            _fail("integrity occurrence did not reject")
        event = {
            "mechanism": "EXACT_SHA256_INTEGRITY_CHECK",
            "committed_byte_count": len(committed),
            "submitted_byte_count": len(submitted),
            "expected_sha256": expected,
            "observed_sha256": observed,
            "integrity_match": False,
            "integrity_rejected": True,
        }
        counters = {
            "common.hash_invocations": 2,
            "common.integrity_checks": 1,
            "integrity.bytes_hashed": len(committed) + len(submitted),
            "io.read_bytes": len(committed) + len(submitted),
            "route.attempts": 1,
            "route.failures": 1,
        }
    elif code is TerminalCode.PROTOCOL_FAILURE:
        if set(inputs) != {"submitted_bytes_hex"}:
            _fail("protocol input changed")
        raw = bytes.fromhex(inputs["submitted_bytes_hex"])
        error_type = None
        error_message = None
        try:
            loads_canonical_json(raw)
        except Exception as error:  # exact parser failure is the observation
            error_type = type(error).__name__
            error_message = str(error)
        if error_type is None:
            _fail("protocol occurrence did not reject")
        event = {
            "mechanism": "CANONICAL_JSON_PROTOCOL_BOUNDARY",
            "submitted_bytes_hex": raw.hex(),
            "submitted_byte_count": len(raw),
            "parser_error_type": error_type,
            "parser_error_message": error_message,
            "protocol_rejected": True,
        }
        counters = {
            "common.protocol_checks": 1,
            "io.read_bytes": len(raw),
            "route.attempts": 1,
            "route.failures": 1,
        }
    elif code is TerminalCode.REBUILD_REQUIRED:
        if set(inputs) != {"compiled_schema", "observed_schema"}:
            _fail("rebuild input changed")
        compiled = tuple(inputs["compiled_schema"])
        observed = tuple(inputs["observed_schema"])
        if (
            not compiled
            or not observed
            or any(type(value) is not int or value < 0 for value in (*compiled, *observed))
            or compiled == observed
        ):
            _fail("rebuild occurrence lacks an exact schema mismatch")
        event = {
            "mechanism": "EXACT_COMPILED_TO_OBSERVED_SCHEMA_JOIN",
            "compiled_schema": list(compiled),
            "observed_schema": list(observed),
            "schema_match": False,
            "prior_model_execution_forbidden": True,
            "rebuild_required": True,
        }
        counters = {
            "rebuild.partition_candidate_evaluations": 1,
            "rebuild.outcome_rows": 1,
            "route.attempts": 1,
            "route.failures": 1,
        }
    elif code is TerminalCode.FALLBACK_CAP_EXHAUSTED:
        if set(inputs) != {"graph", "initial_state", "target_state", "expansion_cap"}:
            _fail("fallback cap input changed")
        graph = _graph(inputs["graph"])
        cap = inputs["expansion_cap"]
        if type(cap) is not int or cap <= 0:
            _fail("fallback cap is invalid")
        trace = _bfs(
            graph,
            initial=inputs["initial_state"],
            target=inputs["target_state"],
            expansion_cap=cap,
        )
        if not trace["cap_exhausted"] or trace["target_reached"]:
            _fail("fallback occurrence did not exhaust its cap")
        event = {
            "mechanism": "BOUNDED_FINITE_GRAPH_FALLBACK",
            "trace": trace,
            "fallback_cap_exhausted": True,
        }
        counters = {
            "control.cap_checks": 1,
            "control.cap_rejections": 1,
            "fallback.actions_evaluated": trace["edge_evaluation_count"],
            "fallback.ground_steps": trace["edge_evaluation_count"],
            "fallback.outcome_rows": trace["edge_evaluation_count"],
            "fallback.states_expanded": trace["state_expansion_count"],
            "route.attempts": 1,
            "route.failures": 1,
        }
    else:
        if set(inputs) != {"attempt_budget", "attempt_outcomes"}:
            _fail("attempt budget input changed")
        budget = inputs["attempt_budget"]
        outcomes = inputs["attempt_outcomes"]
        if (
            type(budget) is not int
            or budget <= 0
            or type(outcomes) is not list
            or len(outcomes) < budget
            or any(type(value) is not bool for value in outcomes)
        ):
            _fail("attempt budget manifest changed")
        trace = []
        succeeded = False
        for ordinal, outcome in enumerate(outcomes[:budget]):
            trace.append({"attempt_ordinal": ordinal, "succeeded": outcome})
            if outcome:
                succeeded = True
                break
        if succeeded or len(trace) != budget:
            _fail("attempt occurrence did not exhaust its budget")
        event = {
            "mechanism": "FINITE_ATTEMPT_BUDGET",
            "attempt_budget": budget,
            "attempt_trace": trace,
            "attempt_budget_exhausted": True,
        }
        counters = {
            "route.attempts": 1,
            "route.failures": 1,
            "solver.attempts": budget,
            "solver.failures": budget,
        }
    return _observation(code, occurrence_id, event, counters)


__all__ = (
    "CONTROLLED_CODES_V180R9",
    "ConstructionK7RemainingTerminalEventEngineV180r9Error",
    "RemainingTerminalEventObservationV180r9",
    "execute_remaining_terminal_event_v180r9",
)
