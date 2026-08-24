"""Outcome-free authorization for six fresh controlled V180 terminal paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r9 as domains
from acfqp.construction_k7_remaining_terminal_event_engine_v180r9 import (
    CONTROLLED_CODES_V180R9,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AUTHORIZATION_ID = (
    "d855e8cd646537687fcde2485a3f7ee83e50ac1831ab01e0f1d0b923aca5703f"
)
EXPECTED_CANONICAL_BYTE_COUNT = 20_270
EXPECTED_CANONICAL_SHA256 = (
    "5b97972a75c8b3a03cdd44b080fb978e38d2da44fe3c5227af32d7dea0c313d6"
)


def _occurrence_id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v180r9:fresh-controlled-terminal-occurrence\x00"
        + label.encode()
    ).hexdigest()


_GRAPH = [
    {"state": 0, "successors": [1, 2]},
    {"state": 1, "successors": [3]},
    {"state": 2, "successors": [3]},
    {"state": 3, "successors": []},
]
_COMMITTED = canonical_json_bytes({"role": "integrity-source", "value": 17})
_SUBMITTED = canonical_json_bytes({"role": "integrity-source", "value": 18})
_EVENT_MANIFESTS = (
    {
        "schema": "acfqp.remaining_terminal_event_manifest.v180r9",
        "terminal_code": "FULL_GROUND_EXACT_INFEASIBLE",
        "logical_occurrence_id": _occurrence_id("full-ground-exact-infeasible"),
        "input": {"graph": _GRAPH, "initial_state": 0, "target_state": 4},
    },
    {
        "schema": "acfqp.remaining_terminal_event_manifest.v180r9",
        "terminal_code": "INTEGRITY_FAILURE",
        "logical_occurrence_id": _occurrence_id("integrity-failure"),
        "input": {
            "committed_payload_hex": _COMMITTED.hex(),
            "submitted_payload_hex": _SUBMITTED.hex(),
        },
    },
    {
        "schema": "acfqp.remaining_terminal_event_manifest.v180r9",
        "terminal_code": "PROTOCOL_FAILURE",
        "logical_occurrence_id": _occurrence_id("protocol-failure"),
        "input": {"submitted_bytes_hex": b'{"x":1} '.hex()},
    },
    {
        "schema": "acfqp.remaining_terminal_event_manifest.v180r9",
        "terminal_code": "REBUILD_REQUIRED",
        "logical_occurrence_id": _occurrence_id("rebuild-required"),
        "input": {"compiled_schema": [3, 1, 2], "observed_schema": [4, 1, 2]},
    },
    {
        "schema": "acfqp.remaining_terminal_event_manifest.v180r9",
        "terminal_code": "FALLBACK_CAP_EXHAUSTED",
        "logical_occurrence_id": _occurrence_id("fallback-cap-exhausted"),
        "input": {
            "graph": _GRAPH,
            "initial_state": 0,
            "target_state": 3,
            "expansion_cap": 2,
        },
    },
    {
        "schema": "acfqp.remaining_terminal_event_manifest.v180r9",
        "terminal_code": "ATTEMPT_BUDGET_EXHAUSTED",
        "logical_occurrence_id": _occurrence_id("attempt-budget-exhausted"),
        "input": {
            "attempt_budget": 2,
            "attempt_outcomes": [False, False, False],
        },
    },
)
_EVENT_MANIFEST_BYTES = tuple(canonical_json_bytes(row) for row in _EVENT_MANIFESTS)

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v180r9.py",
    "src/acfqp/construction_k7_remaining_terminal_event_engine_v180r9.py",
    "src/acfqp/construction_k7_remaining_terminal_production_v180r9.py",
    "src/acfqp/construction_k7_remaining_terminal_independent_verifier_v180r9.py",
    "src/acfqp/construction_k7_all_path_formalization_contract_v180.py",
    "src/acfqp/construction_k7_all_path_production_execution_protocol_v180r3.py",
    "src/acfqp/construction_accounting_registry_v9.py",
    "src/acfqp/accounting_v1.py",
    "src/acfqp/actual_accounting_v1.py",
    "src/acfqp/phase3e_ids.py",
    "scripts/run_v180r9_remaining_terminal_occurrence.py",
)


def event_manifests_v180r9() -> tuple[dict[str, Any], ...]:
    documents = tuple(loads_canonical_json(raw) for raw in _EVENT_MANIFEST_BYTES)
    if any(type(row) is not dict for row in documents):
        raise AssertionError("V180r9 event manifest replay changed")
    return documents  # type: ignore[return-value]


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_remaining_terminal_execution_authorization_v180r9() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    frozen = protocol.freeze_all_path_production_execution_protocol_v180r3()
    slots = frozen.to_document()["production_execution_slots"]
    selected_slots = [
        next(row for row in slots if row["terminal_code"] == code.value)
        for code in CONTROLLED_CODES_V180R9
    ]
    manifests = event_manifests_v180r9()
    if tuple(row["terminal_code"] for row in manifests) != tuple(
        code.value for code in CONTROLLED_CODES_V180R9
    ):
        raise ValueError("V180r9 manifest order changed")
    payload = {
        "schema": "acfqp.remaining_terminal_execution_authorization.v180r9",
        "production_execution_protocol_id": frozen.production_execution_protocol_id,
        "ordered_terminal_codes": [code.value for code in CONTROLLED_CODES_V180R9],
        "production_execution_slots": selected_slots,
        "event_manifests": list(manifests),
        "event_manifest_facts": [
            {
                "terminal_code": row["terminal_code"],
                "canonical_byte_count": len(raw),
                "canonical_sha256": hashlib.sha256(raw).hexdigest(),
            }
            for row, raw in zip(manifests, _EVENT_MANIFEST_BYTES, strict=True)
        ],
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "entrypoint": (
            "acfqp.construction_k7_remaining_terminal_production_v180r9:"
            "run_remaining_terminal_production_campaign_v180r9"
        ),
        "output_root_relative_path": (
            ".tmp/exact-freeze/v180r9_remaining_terminal_production"
        ),
        "output_root_must_be_absent": True,
        "terminal_output_must_be_absent": True,
        "verification_output_must_be_absent": True,
        "failure_output_must_be_absent": True,
        "same_authorization_rerun_after_any_progress_forbidden": True,
        "fresh_controlled_execution_started": False,
        "production_outcome_accessed": False,
        "controlled_inputs_are_small_but_mechanisms_are_actually_executed": True,
        "all_269_v9_counter_paths_require_explicit_records": True,
        "all_nine_shared_resource_paths_require_source_closed_receipts": True,
        "campaign_orchestration_v9_chain_required": True,
        "producer_free_verification_required": True,
        "historical_summary_to_counter_translation_forbidden": True,
        "development_fixture_evidence_forbidden": True,
        "two_worker_cap": 2,
        "actual_worker_process_count": 0,
        "partial_campaign_cannot_unlock_any_gate": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "execution_authorization_id": domains.extension_content_id_v180r9(
            domains.CONSTRUCTION_K7_EXECUTION_AUTHORIZATION_V180R9_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RemainingTerminalExecutionAuthorizationV180r9:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_id: str

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.canonical_bytes) is not bytes
            or type(self.authorization_id) is not str
            or len(self.authorization_id) != 64
        ):
            raise ValueError("V180r9 authorization is not issuer-created")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r9 authorization is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_remaining_terminal_execution_authorization_v180r9() -> RemainingTerminalExecutionAuthorizationV180r9:
    document = build_remaining_terminal_execution_authorization_v180r9()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != "0" * 64 and not (
        document["execution_authorization_id"] == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r9 execution authorization changed")
    return RemainingTerminalExecutionAuthorizationV180r9(
        _ISSUER,
        raw,
        document["execution_authorization_id"],
    )


__all__ = (
    "EXPECTED_AUTHORIZATION_ID",
    "build_remaining_terminal_execution_authorization_v180r9",
    "event_manifests_v180r9",
    "freeze_remaining_terminal_execution_authorization_v180r9",
)
