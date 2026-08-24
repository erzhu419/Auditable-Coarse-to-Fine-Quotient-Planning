"""Freeze the failed one-shot V180r7 full-ground-fallback occurrence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_fallback_execution_authorization_v180r7 as authorization
from acfqp import construction_k7_domain_registry_extension_v180r7 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_FAILURE_ID = "bd6e022804f5be7dc7ae22e781ce121fe462277858b058bacf8f201f5b234f79"
EXPECTED_CANONICAL_BYTE_COUNT = 649
EXPECTED_CANONICAL_SHA256 = "b39a368f7299e44344108afeab84d8feef8c8a0dc19585f1a465c16557d62bdb"


@dataclass(frozen=True, slots=True)
class FrozenFullGroundFallbackExecutionFailureV180r7:
    canonical_bytes: bytes
    failure_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r7 retained failure is not a document")
        return document


def load_frozen_full_ground_fallback_execution_failure_v180r7() -> (
    FrozenFullGroundFallbackExecutionFailureV180r7
):
    root = Path(__file__).resolve().parents[2]
    base = root / ".tmp" / "exact-freeze"
    failure_path = base / "v180r7_full_ground_fallback_failure.json"
    output_root = base / "v180r7_full_ground_fallback_output"
    cas_root = base / "v180r7_full_ground_fallback_cas"
    success_path = base / "v180r7_full_ground_fallback_terminal_bundle.json"
    verification_path = base / "v180r7_full_ground_fallback_verification.json"
    raw = failure_path.read_bytes()
    document = loads_canonical_json(raw)
    if type(document) is not dict:
        raise ValueError("V180r7 retained failure is not a document")
    payload = dict(document)
    failure_id = payload.pop("failure_id", None)
    output_files = tuple(
        path.relative_to(output_root).as_posix()
        for path in sorted(output_root.rglob("*"))
        if path.is_file()
    )
    if not (
        canonical_json_bytes(document) == raw
        and set(document)
        == {
            "COUNTER_COMPLETENESS_GATE",
            "WORKLOAD_ECONOMICS_GATE",
            "cas_root_created",
            "failure_id",
            "failure_message",
            "failure_type",
            "fallback_execution_authorization_id",
            "official_execution_allowed",
            "output_root_created",
            "retained_output_file_count",
            "same_authorization_rerun_forbidden",
            "schema",
            "success_claimed",
        }
        and failure_id == EXPECTED_FAILURE_ID
        and failure_id
        == domains.extension_content_id_v180r7(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_FAILURE_V180R7_DOMAIN,
            payload,
        )
        and document["schema"] == "acfqp.full_ground_fallback_execution_failure.v180r7"
        and document["fallback_execution_authorization_id"]
        == authorization.EXPECTED_AUTHORIZATION_ID
        and document["failure_type"]
        == "V075ConstructionSourceRuntimeV2InvariantViolation"
        and document["failure_message"]
        == "construction source inputs are malformed or incomplete"
        and document["cas_root_created"] is False
        and document["output_root_created"] is True
        and document["retained_output_file_count"] == 0
        and output_root.is_dir()
        and output_files == ()
        and not cas_root.exists()
        and not success_path.exists()
        and not verification_path.exists()
        and document["same_authorization_rerun_forbidden"] is True
        and document["success_claimed"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_execution_allowed"] is False
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r7 retained failure or partial output inventory changed")
    return FrozenFullGroundFallbackExecutionFailureV180r7(raw, failure_id)


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_FAILURE_ID",
    "load_frozen_full_ground_fallback_execution_failure_v180r7",
)
