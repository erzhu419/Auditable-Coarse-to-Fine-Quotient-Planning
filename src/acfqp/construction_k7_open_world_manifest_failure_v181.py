"""Typed V181 failure: two committed manifest preimages were not retained."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181 as domains
from acfqp import construction_k7_open_world_preregistration_v181 as prereg
from acfqp import construction_k7_open_world_protocol_contract_v181 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


RECOVERED_MANIFEST_INDICES = (0,)
MISSING_MANIFEST_INDICES = (1, 2)
EXPECTED_FAILURE_ID = (
    "2889b14334a54e1cc161651662c1fb1330dad22a3178f2a7e00937d490968884"
)
EXPECTED_CANONICAL_BYTE_COUNT = 1_229
EXPECTED_CANONICAL_SHA256 = (
    "f2aff4a91524224af48de685cc877ec4736b0eafdb098655bc2b60b1ee9c786e"
)


def build_open_world_manifest_failure_v181() -> dict[str, Any]:
    frozen_preregistration = prereg.freeze_open_world_preregistration_v181()
    payload = {
        "schema": "acfqp.open_world_manifest_failure.v181",
        "open_world_protocol_contract_id": protocol.EXPECTED_CONTRACT_ID,
        "open_world_preregistration_id": frozen_preregistration.preregistration_id,
        "failure_stage": "MANIFEST_REVEAL_PREIMAGE_RECOVERY",
        "failure_code": "COMMITTED_REVEAL_PREIMAGE_NOT_RETAINED",
        "manifest_commitments": list(protocol.MANIFEST_COMMITMENTS),
        "recovered_manifest_indices": list(RECOVERED_MANIFEST_INDICES),
        "missing_manifest_indices": list(MISSING_MANIFEST_INDICES),
        "complete_reveal_denominator": 3,
        "complete_reveal_count": 1,
        "target_oracle_query_count": 0,
        "target_outcomes_accessed": False,
        "campaign_started": False,
        "same_identity_rerun_forbidden": True,
        "same_identity_commitment_replacement_forbidden": True,
        "success_claimed": False,
        "sample_efficiency_claimed": False,
        "total_work_dominance_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "failure_id": domains.extension_content_id_v181(
            domains.CONSTRUCTION_K7_FAILURE_V181_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldManifestFailureV181:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    failure_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_manifest_failure_v181() -> OpenWorldManifestFailureV181:
    document = build_open_world_manifest_failure_v181()
    raw = canonical_json_bytes(document)
    if EXPECTED_FAILURE_ID != "0" * 64 and not (
        document["failure_id"] == EXPECTED_FAILURE_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181 frozen manifest failure changed")
    return OpenWorldManifestFailureV181(_ISSUER, raw, document["failure_id"])


__all__ = (
    "EXPECTED_FAILURE_ID",
    "freeze_open_world_manifest_failure_v181",
)
