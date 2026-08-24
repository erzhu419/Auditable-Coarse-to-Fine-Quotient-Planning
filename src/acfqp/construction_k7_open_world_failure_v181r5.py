"""Frozen V181r5 pre-execution oracle-access failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r5 as domains
from acfqp import construction_k7_open_world_manifest_reveals_v181r5 as reveals
from acfqp import construction_k7_open_world_protocol_successor_v181r5 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_FAILURE_ID = (
    "fd95acb0a0368496eda246330d09a8ac5908b7692ac3fd5a9b52f38aa70e7d67"
)
EXPECTED_CANONICAL_BYTE_COUNT = 1_222
EXPECTED_CANONICAL_SHA256 = (
    "75bc38179263f9e0c5f56666d8791fc0b9f7ef0a6ea1f2c4c2f246fc02fb29d8"
)


def build_open_world_failure_v181r5() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.open_world_failure.v181r5",
        "protocol_successor_id": protocol.EXPECTED_SUCCESSOR_ID,
        "manifest_reveal_id": reveals.EXPECTED_REVEAL_ID,
        "failure_stage": "FOCUSED_TEST_BEFORE_EXECUTION_PREREGISTRATION",
        "failure_code": "PREMATURE_TARGET_ORACLE_ACCESS",
        "manifest_index": 0,
        "arm_query_call_counts": {
            "REUSED_SUBPROGRAM_PRIOR": 32,
            "EMPTY_ARCHIVE_NO_PRIOR": 48,
        },
        "target_oracle_query_call_count": 80,
        "unique_raw_observation_count": 48,
        "occurrence_index": 40_000,
        "query_index_union": list(range(48)),
        "target_outcomes_accessed": True,
        "execution_preregistration_frozen": False,
        "campaign_executed": False,
        "campaign_id": None,
        "same_v181r5_identity_scientific_rerun_forbidden": True,
        "successor_requires_fresh_domains_commitments_and_manifest_preimages": True,
        "failure_reclassified_as_success": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "failure_id": domains.extension_content_id_v181r5(
            domains.CONSTRUCTION_K7_FAILURE_V181R5_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldFailureV181R5:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    failure_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_failure_v181r5() -> OpenWorldFailureV181R5:
    document = build_open_world_failure_v181r5()
    raw = canonical_json_bytes(document)
    if EXPECTED_FAILURE_ID != "0" * 64 and not (
        document["failure_id"] == EXPECTED_FAILURE_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r5 frozen failure changed")
    return OpenWorldFailureV181R5(_ISSUER, raw, document["failure_id"])


__all__ = ("EXPECTED_FAILURE_ID", "freeze_open_world_failure_v181r5")
