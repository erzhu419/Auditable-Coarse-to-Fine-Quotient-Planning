"""Exact retained V180r6 V36 failure and its immutable partial outputs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_v36_execution_authorization_v180r6 as authorization
from acfqp import construction_k7_domain_registry_extension_v180r6 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_FAILURE_ID = "ee9f5de9e43736a1e3890d84372bb0d19db1291e5121ba1749da2b4a8f655d58"
EXPECTED_CANONICAL_BYTE_COUNT = 621
EXPECTED_CANONICAL_SHA256 = "5292a15e7cabf4e1951ec6bb4b1998c4a69986ed43695463a5ddefa3453f4e47"
EXPECTED_PARTIAL_OUTPUT_FACTS: tuple[dict[str, Any], ...] = (
    {
        "relative_path": "model/evaluation-no-prior-control.json",
        "byte_count": 575317,
        "sha256": "292a12408fd96fe0441657505b5ab504dbfb3153384ba2bf334f4b4ec8478552",
    },
    {
        "relative_path": "model/operational-acquisition.json",
        "byte_count": 215272,
        "sha256": "338ff944b8b235c445f6cf56d853f4206fd82cac12a9db0b7afb2f540edf85bc",
    },
    {
        "relative_path": "model/operational-failure-frontier.json",
        "byte_count": 799895,
        "sha256": "34f2b77e1d86d9a40908d1e6797e7272a024015c0546be58e189d5dae434e3be",
    },
    {
        "relative_path": "model/operational-overlay.json",
        "byte_count": 211795,
        "sha256": "b45d2dda2c6b7cd71bf15099625304860490c7b00f5fb21b0fe4c634c31b8f1f",
    },
    {
        "relative_path": "model/operational-proof.json",
        "byte_count": 210868,
        "sha256": "30cab4ed4ae9e2daf6d79b761381be05ef7aa2731cc129fb9939733170a3741d",
    },
    {
        "relative_path": "model/operational-proposal.json",
        "byte_count": 225159,
        "sha256": "6905e16cb45ef5fd54649c8a572d1be5a652fa7ff8dbf8aedff93f4f02b2978b",
    },
)


@dataclass(frozen=True, slots=True)
class FrozenV36FailureV180r6:
    canonical_bytes: bytes
    failure_id: str
    partial_output_facts: tuple[dict[str, Any], ...]

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r6 retained failure is not a document")
        return document


def _partial_facts(output_root: Path) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "relative_path": path.relative_to(output_root).as_posix(),
            "byte_count": len(raw := path.read_bytes()),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        for path in sorted(candidate for candidate in output_root.rglob("*") if candidate.is_file())
    )


def load_frozen_v36_failure_v180r6() -> FrozenV36FailureV180r6:
    root = Path(__file__).resolve().parents[2]
    failure_path = root / ".tmp" / "exact-freeze" / "v180r6_v36_production_failure.json"
    output_root = root / ".tmp" / "exact-freeze" / "v180r6_v36_production_output"
    raw = failure_path.read_bytes()
    document = loads_canonical_json(raw)
    if type(document) is not dict:
        raise ValueError("V180r6 retained failure is not a document")
    payload = dict(document)
    failure_id = payload.pop("failure_id", None)
    partial_facts = _partial_facts(output_root)
    if not (
        canonical_json_bytes(document) == raw
        and set(document)
        == {
            "schema",
            "v36_execution_authorization_id",
            "failure_type",
            "failure_message",
            "output_root_created",
            "retained_output_file_count",
            "same_authorization_rerun_forbidden",
            "success_claimed",
            "COUNTER_COMPLETENESS_GATE",
            "WORKLOAD_ECONOMICS_GATE",
            "official_execution_allowed",
            "failure_id",
        }
        and failure_id == EXPECTED_FAILURE_ID
        and failure_id
        == domains.extension_content_id_v180r6(
            domains.CONSTRUCTION_K7_V36_EXECUTION_FAILURE_V180R6_DOMAIN,
            payload,
        )
        and document["v36_execution_authorization_id"] == authorization.EXPECTED_AUTHORIZATION_ID
        and document["failure_type"] == "BrokenProcessPool"
        and document["output_root_created"] is True
        and document["retained_output_file_count"] == len(EXPECTED_PARTIAL_OUTPUT_FACTS)
        and document["same_authorization_rerun_forbidden"] is True
        and document["success_claimed"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_execution_allowed"] is False
        and partial_facts == EXPECTED_PARTIAL_OUTPUT_FACTS
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r6 retained V36 failure or partial output changed")
    return FrozenV36FailureV180r6(raw, failure_id, partial_facts)


__all__ = (
    "EXPECTED_FAILURE_ID",
    "EXPECTED_PARTIAL_OUTPUT_FACTS",
    "load_frozen_v36_failure_v180r6",
)
