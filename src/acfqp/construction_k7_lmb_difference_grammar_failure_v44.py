"""Frozen failure of the first preregistered V44 source-acquisition schedule."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_lmb_difference_grammar_preregistration_v44 as pre
from acfqp.domains.matching_buffer import LMBKernel, LMBState, LMBStatus, generate_solvable_lmb
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


PROFILE_KEY = "construction_k7_lmb_difference_grammar_source_failure_v44"
EXPECTED_FAILURE_ID = "f98b1fb28efcb7f5f311f04d6c16bf283cbe521a2cf1f0cb4bc4fe3057d19bcd"
EXPECTED_CANONICAL_BYTE_COUNT = 35_869
EXPECTED_CANONICAL_SHA256 = "cda363571b6639b5bbe5895719da72bf7aa46fb54ab31433b9fe3a96e98a09b6"


class ConstructionK7LMBDifferenceGrammarFailureV44Error(ValueError):
    """The preserved V44 source-acquisition failure changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBDifferenceGrammarFailureV44Error(message)


def _state(state: LMBState) -> dict[str, Any]:
    return {
        "removed_mask": state.removed_mask,
        "buffer_counts": list(state.buffer),
        "status": state.status.value,
    }


def _mode_complete(mode: str, rows: list[dict[str, Any]]) -> bool:
    if mode == "REWRITE_AND_SUCCESS_COVERAGE":
        return (
            any(row["selected_count_before"] < row["selected_count_after"] for row in rows)
            and any(row["selected_count_before"] > row["selected_count_after"] for row in rows)
            and any(row["post_board_empty"] and row["post_status"] == "success" for row in rows)
        )
    return (
        any(row["post_load"] == row["capacity"] and row["post_status"] == "active" for row in rows)
        and any(
            row["post_load"] == row["capacity"] + 1 and row["post_status"] == "failure"
            for row in rows
        )
    )


def _run_episode(seed: int, mode: str) -> tuple[list[dict[str, Any]], str]:
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.SOURCE_SPEC)
    del witness
    state = kernel.initial_distribution()[0][1]
    visits: dict[int, int] = {}
    rows = []
    while state.status is LMBStatus.ACTIVE:
        ranked = []
        for action in kernel.actions(state):
            selected = state.buffer[kernel.tile_types[action.tile]]
            score = (
                selected if mode == "REWRITE_AND_SUCCESS_COVERAGE" else -selected,
                -visits.get(selected, 0),
                sum(state.buffer),
                -action.tile,
            )
            ranked.append((score, action))
        score, action = max(ranked)
        component = kernel.tile_types[action.tile]
        outcome = kernel.step(state, action)[0]
        successor = outcome.next_state
        changed = [
            index
            for index, (before, after) in enumerate(zip(state.buffer, successor.buffer))
            if before != after
        ]
        payload = {
            "schema": "acfqp.lmb_raw_transition_observation.v44",
            "schema_version": pre.SCHEMA_VERSION,
            "preregistration_id": pre.PREREGISTRATION_ID,
            "mode": mode,
            "source_seed": seed,
            "decision_index": len(rows),
            "pre_state": _state(state),
            "legal_action_tiles": [candidate.tile for candidate in kernel.actions(state)],
            "action_tile": action.tile,
            "action_public_class": component,
            "selection_score": list(score),
            "post_state": _state(successor),
            "changed_buffer_components": changed,
            "selected_count_before": state.buffer[component],
            "selected_count_after": successor.buffer[component],
            "pre_load": sum(state.buffer),
            "post_load": sum(successor.buffer),
            "capacity": kernel.capacity,
            "post_board_empty": successor.removed_mask == (1 << kernel.tile_count) - 1,
            "post_status": successor.status.value,
            "source_generation_witness_accessed": False,
        }
        rows.append(
            {
                **payload,
                "observation_id": content_id(pre.FUTURE_DOMAINS["raw_observation"], payload),
            }
        )
        visits[state.buffer[component]] = visits.get(state.buffer[component], 0) + 1
        state = successor
    return rows, state.status.value


def build_lmb_difference_grammar_failure_document_v44() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    closures = []
    for schedule in pre.SOURCE_SCHEDULE:
        mode_rows: list[dict[str, Any]] = []
        for seed in schedule["ordered_seeds"]:
            episode_rows, terminal = _run_episode(seed, schedule["mode"])
            rows.extend(episode_rows)
            mode_rows.extend(episode_rows)
            closures.append(
                {
                    "mode": schedule["mode"],
                    "source_seed": seed,
                    "transition_label_count": len(episode_rows),
                    "terminal_status": terminal,
                    "mode_requirements_satisfied_after_episode": _mode_complete(
                        schedule["mode"], mode_rows
                    ),
                }
            )
            if _mode_complete(schedule["mode"], mode_rows):
                break
    facts = {
        "operated_component_join_observed": all(
            row["changed_buffer_components"] == [row["action_public_class"]] for row in rows
        ),
        "increment_difference_observed": any(
            row["selected_count_after"] == row["selected_count_before"] + 1 for row in rows
        ),
        "rewrite_difference_observed": any(
            row["selected_count_after"] < row["selected_count_before"] for row in rows
        ),
        "active_at_capacity_observed": any(
            row["post_load"] == row["capacity"] and row["post_status"] == "active"
            for row in rows
        ),
        "failure_one_above_capacity_observed": any(
            row["post_load"] == row["capacity"] + 1 and row["post_status"] == "failure"
            for row in rows
        ),
        "success_on_full_removal_observed": any(
            row["post_board_empty"] and row["post_status"] == "success" for row in rows
        ),
    }
    if facts["success_on_full_removal_observed"]:
        _fail("registered V44 failure unexpectedly acquired success evidence")
    payload = {
        "schema": "acfqp.lmb_difference_grammar_failure.v44",
        "schema_version": pre.SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "raw_observations": rows,
        "source_episode_closures": closures,
        "coverage_facts": facts,
        "offline_source_transition_label_count": len(rows),
        "target_episode_execution_count": 0,
        "target_generation_witness_access_count": 0,
        "failure_code": "PREREGISTERED_SOURCE_SUCCESS_COVERAGE_NOT_OBSERVED",
        "failure_preserved_before_successor_preregistration": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "status": "TYPED_PREREGISTERED_COVERAGE_FAILURE",
    }
    return {
        **payload,
        "failure_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBDifferenceGrammarFailureV44:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    failure_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V44 failure is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V44 failure bytes changed")
        payload = {key: value for key, value in document.items() if key != "failure_id"}
        if (
            document.get("failure_id") != self.failure_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.failure_id
        ):
            _fail("V44 failure identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V44 failure is not an object")
        return value


def freeze_lmb_difference_grammar_failure_v44() -> LMBDifferenceGrammarFailureV44:
    document = build_lmb_difference_grammar_failure_document_v44()
    raw = canonical_json_bytes(document)
    identity = document["failure_id"]
    if EXPECTED_FAILURE_ID != "0" * 64 and (
        identity != EXPECTED_FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V44 failure changed")
    return LMBDifferenceGrammarFailureV44(_ISSUER, raw, identity)


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_FAILURE_ID",
    "LMBDifferenceGrammarFailureV44",
    "build_lmb_difference_grammar_failure_document_v44",
    "freeze_lmb_difference_grammar_failure_v44",
)
