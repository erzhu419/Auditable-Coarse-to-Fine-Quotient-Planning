"""Producer-free verifier for the frozen V181r1 campaign failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r1 as domains
from acfqp import construction_k7_open_world_execution_preregistration_v181r1 as prereg
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_FAILURE_ID = (
    "51a28e11167bd114637520deb8235dd8974f7dd50742505b14b0454ed61e5b7b"
)
EXPECTED_FAILURE_BYTE_COUNT = 574
EXPECTED_FAILURE_SHA256 = (
    "482fc8aa677bbb77ec03aaefbd4596a76555fa6214358100c8845cf3fb4211c3"
)
EXPECTED_VERIFICATION_ID = (
    "a06e5b8bcfcbf772c0df12f562ccd18e0db8c794d1390de5c414e1395fa6ece5"
)
EXPECTED_VERIFICATION_BYTE_COUNT = 879
EXPECTED_VERIFICATION_SHA256 = (
    "3dc7489a0a91a79e0e0d28329a8cdb5003d391cf5577de67798bfebefd421e67"
)


def verify_open_world_campaign_failure_bytes_v181r1(raw: bytes) -> dict[str, Any]:
    document = loads_canonical_json(raw)
    keys = {
        "COUNTER_COMPLETENESS_GATE",
        "WORKLOAD_ECONOMICS_GATE",
        "execution_preregistration_id",
        "failure_id",
        "failure_message",
        "failure_type",
        "official_execution_allowed",
        "same_identity_rerun_forbidden",
        "schema",
        "success_claimed",
        "target_outcome_run_started",
    }
    if (
        type(document) is not dict
        or set(document) != keys
        or canonical_json_bytes(document) != raw
        or len(raw) != EXPECTED_FAILURE_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_FAILURE_SHA256
        or document["schema"] != "acfqp.open_world_campaign_failure.v181r1"
        or document["execution_preregistration_id"]
        != prereg.EXPECTED_EXECUTION_PREREGISTRATION_ID
        or document["failure_type"] != "OpenWorldUniversalSynthesizerV181Error"
        or document["failure_message"]
        != "no bounded finite residual support found within the run budget"
        or document["target_outcome_run_started"] is not True
        or document["same_identity_rerun_forbidden"] is not True
        or document["success_claimed"] is not False
        or document["official_execution_allowed"] is not False
        or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN"
        or document["COUNTER_COMPLETENESS_GATE"] != "NOT_RUN"
    ):
        raise ValueError("V181r1 failure bytes or semantics changed")
    payload = dict(document)
    failure_id = payload.pop("failure_id")
    if (
        failure_id != EXPECTED_FAILURE_ID
        or failure_id
        != domains.extension_content_id_v181r1(
            domains.CONSTRUCTION_K7_FAILURE_V181R1_DOMAIN,
            payload,
        )
    ):
        raise ValueError("V181r1 failure content ID changed")
    verification_payload = {
        "schema": "acfqp.open_world_campaign_failure_verification.v181r1",
        "failure_id": failure_id,
        "execution_preregistration_id": document["execution_preregistration_id"],
        "failure_bytes_sha256": EXPECTED_FAILURE_SHA256,
        "typed_resource_failure_independently_verified": True,
        "same_identity_rerun_forbidden_independently_verified": True,
        "campaign_success_independently_verified": False,
        "failure_stage_resolution": "PRIOR_ACQUISITION_CALL_STACK_ONLY",
        "durable_manifest_and_arm_progress_index_present": False,
        "sample_efficiency_claimed": False,
        "total_work_dominance_claimed": False,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **verification_payload,
        "verification_id": domains.extension_content_id_v181r1(
            domains.CONSTRUCTION_K7_VERIFICATION_V181R1_DOMAIN,
            verification_payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldCampaignFailureVerificationV181R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_campaign_failure_verification_v181r1(
    raw: bytes,
) -> OpenWorldCampaignFailureVerificationV181R1:
    document = verify_open_world_campaign_failure_bytes_v181r1(raw)
    canonical = canonical_json_bytes(document)
    if EXPECTED_VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(canonical) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(canonical).hexdigest() == EXPECTED_VERIFICATION_SHA256
    ):
        raise ValueError("V181r1 frozen failure verification changed")
    return OpenWorldCampaignFailureVerificationV181R1(
        _ISSUER,
        canonical,
        document["verification_id"],
    )


__all__ = (
    "EXPECTED_FAILURE_ID",
    "EXPECTED_VERIFICATION_ID",
    "freeze_open_world_campaign_failure_verification_v181r1",
    "verify_open_world_campaign_failure_bytes_v181r1",
)
