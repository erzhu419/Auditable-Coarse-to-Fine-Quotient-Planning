"""Producer-free verification of the corrected V91r3 acceptance."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v91r3 as domains
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    verify_joint_successor_version_space_model_v42,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ACCEPTANCE_ID = "59371553fe2e1a9898f1da41abc2c94d860e6833bdada98bc10ffe699d7d444c"
ACCEPTANCE_BYTE_COUNT = 39_427
ACCEPTANCE_SHA256 = "f91d44c4230aff47ac8346727924247c09d8cc45e804728aaf3b68fd4ee4e597"
PREREGISTRATION_ID = "e1b7376e65f2c767e3c80db4eda9923f0e317612e3388663acf48e6a0dcb596d"
V91R2_CAMPAIGN_ID = "3a3d634361c16438ce9fe74f961a0c57f31f8476e8118869531fe849f68b42a6"
V91R2_VERIFICATION_ID = "1cc119b9d67a29ea439970208bdd41780038a3c4f8eba02f0a650f30fbcd7895"
VERIFICATION_ID = (
    "bf929def883b2134d32c7bc59cf4b2605b9af7ddb37a3ae37cd0efa3a2d59d7a"
)
EXPECTED_CANONICAL_BYTE_COUNT = 1_164
EXPECTED_CANONICAL_SHA256 = (
    "34851dc65148d0b3bab0e8e1f29fd2131a9dc1a3e04394a0c97e5f9c92abfd2c"
)


class ConstructionK7SourceModelAcceptanceIndependentVerifierV91R3Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SourceModelAcceptanceIndependentVerifierV91R3Error(
        message
    )


def verify_source_model_acceptance_bytes_v91r3(raw: bytes) -> bytes:
    if (
        type(raw) is not bytes
        or len(raw) != ACCEPTANCE_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != ACCEPTANCE_SHA256
    ):
        _fail("V91r3 acceptance bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V91r3 acceptance canonical bytes changed")
    payload = {
        key: value for key, value in document.items() if key != "acceptance_id"
    }
    model = document.get("accepted_joint_successor_version_space_model")
    if (
        document.get("acceptance_id") != ACCEPTANCE_ID
        or domains.extension_content_id_v91r3(
            domains.CONSTRUCTION_K7_SOURCE_MODEL_ACCEPTANCE_RESULT_V91R3_DOMAIN,
            payload,
        )
        != ACCEPTANCE_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v91r2_campaign_id") != V91R2_CAMPAIGN_ID
        or document.get("v91r2_verification_id") != V91R2_VERIFICATION_ID
        or type(model) is not dict
    ):
        _fail("V91r3 acceptance identity join changed")
    verified = verify_joint_successor_version_space_model_v42(model)
    spaces = verified["residual_version_spaces"]
    counts = [row["batch_exact_candidate_count"] for row in spaces]
    gate = document.get("corrected_gate")
    if (
        document.get("accepted_joint_successor_version_space_model_id")
        != verified["joint_successor_version_space_model_id"]
        or document.get("retained_residual_candidate_counts") != counts
        or document.get("retained_residual_candidate_count") != sum(counts)
        or document.get("observed_version_space_is_singleton")
        is not all(row == 1 for row in counts)
        or document.get("multiple_residual_proposals_observed_in_this_predecessor")
        is not any(row > 1 for row in counts)
        or type(gate) is not dict
        or gate.get("every_observation_consistent_residual_candidate_retained")
        is not True
        or gate.get("singleton_version_space_is_not_a_failure") is not True
        or gate.get("passed") is not True
        or document.get("synthetic_or_duplicate_uncertainty_inserted") is not False
        or document.get("new_source_or_target_outcomes_executed") is not False
        or document.get("accepted_model_is_proposal_not_safety_authority")
        is not True
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V91r3 corrected Gate or claim boundary changed")
    verification_payload: dict[str, Any] = {
        "schema": "acfqp.source_model_acceptance_independent_verification.v91r3",
        "acceptance_id": ACCEPTANCE_ID,
        "acceptance_byte_count": ACCEPTANCE_BYTE_COUNT,
        "acceptance_sha256": ACCEPTANCE_SHA256,
        "preregistration_id": PREREGISTRATION_ID,
        "v91r2_campaign_id": V91R2_CAMPAIGN_ID,
        "v91r2_verification_id": V91R2_VERIFICATION_ID,
        "joint_successor_version_space_model_id": verified[
            "joint_successor_version_space_model_id"
        ],
        "residual_candidate_counts": counts,
        "producer_free_model_replay": True,
        "complete_version_space_retention_verified": True,
        "singleton_without_synthetic_uncertainty_verified": True,
        "typed_result": "SOURCE_MODEL_ACCEPTED_FOR_TARGET_PLANNING",
        "fresh_outcome_count": 0,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v91r3(
            domains.CONSTRUCTION_K7_SOURCE_MODEL_ACCEPTANCE_VERIFICATION_V91R3_DOMAIN,
            verification_payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V91r3 verification changed")
    return result


__all__ = ("VERIFICATION_ID", "verify_source_model_acceptance_bytes_v91r3")
