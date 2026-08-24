"""Exact retained pre-execution failure for the V180r4 V34 authorization."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from acfqp import construction_k7_all_path_v34_execution_authorization_v180r4 as authorization
from acfqp import construction_k7_domain_registry_extension_v180r4 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_FAILURE_ID = (
    "b16340522ec43a6cac3cd8889758b3512b078a5034f324d2a1cb7fbe0e02cef4"
)
EXPECTED_CANONICAL_BYTE_COUNT = 618
EXPECTED_CANONICAL_SHA256 = (
    "0cd6fd32452748be799bc2170dc6c01796d3156bbbd363cc6e1371b04c606220"
)


@dataclass(frozen=True, slots=True)
class FrozenV34FailureV180r4:
    canonical_bytes: bytes
    failure_id: str

    def to_document(self) -> dict:
        return loads_canonical_json(self.canonical_bytes)


def load_frozen_v34_failure_v180r4() -> FrozenV34FailureV180r4:
    path = (
        Path(__file__).resolve().parents[2]
        / ".tmp"
        / "exact-freeze"
        / "v180r4_v34_production_failure.json"
    )
    raw = path.read_bytes()
    document = loads_canonical_json(raw)
    payload = dict(document)
    failure_id = payload.pop("failure_id", None)
    if not (
        type(document) is dict
        and canonical_json_bytes(document) == raw
        and failure_id == EXPECTED_FAILURE_ID
        and failure_id
        == domains.extension_content_id_v180r4(
            domains.CONSTRUCTION_K7_V34_EXECUTION_FAILURE_V180R4_DOMAIN,
            payload,
        )
        and document["v34_execution_authorization_id"]
        == authorization.EXPECTED_AUTHORIZATION_ID
        and document["output_root_created"] is False
        and document["retained_output_file_count"] == 0
        and document["success_claimed"] is False
        and document["same_authorization_rerun_forbidden"] is True
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r4 retained V34 failure changed")
    return FrozenV34FailureV180r4(raw, failure_id)


__all__ = (
    "EXPECTED_FAILURE_ID",
    "load_frozen_v34_failure_v180r4",
)
