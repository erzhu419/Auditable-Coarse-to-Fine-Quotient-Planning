"""Producer-free verification of the frozen V91 source-Gate failure."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v91 as domains
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
)
from acfqp.generic_compiler_ready_acquisition_v52 import (
    run_relation_covering_compiler_ready_acquisition_v52,
)
from acfqp.generic_reference_aligned_source_pool_v65 import (
    pool_reference_aligned_source_evidence_v65,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "e9d6fd70a8cdf0d023dfaa5a3dfa60423a777632baef7b610b28da11024d7373"
CAMPAIGN_BYTE_COUNT = 561_886
CAMPAIGN_SHA256 = "ba35b013bca09e49a8d533dd86df0ef4d4e7b2c82862598942bb40a8a87f3bb9"
PREREGISTRATION_ID = "9a4d8dc9a8d40024708df19e6689d59b94aed082fa9c6468f4867c34604578de"
V90_VERIFICATION_ID = "9e98d0c4d4d63b87f5dbad9a21ff61f5509e38f63f08733981dfbe0eb7d5926c"
LAYOUT_DOMAIN = "acfqp:construction-k7-joint-factor-residual-layout:v54"
VERIFICATION_ID = "cf5c159ba8fce9c347ec34458f48cf171aa01c753b41c9cf7e27b970176b4b72"
EXPECTED_CANONICAL_BYTE_COUNT = 1_376
EXPECTED_CANONICAL_SHA256 = "813700bd05543bbd7d0861b48103471e97d208d1e8bda593e2ca34a5d2a47f77"


class ConstructionK7ReferenceAlignedSourceIndependentVerifierV91Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReferenceAlignedSourceIndependentVerifierV91Error(message)


def verify_reference_aligned_source_campaign_bytes_v91(raw: bytes) -> bytes:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V91 frozen campaign bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V91 frozen campaign canonical bytes changed")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or domains.extension_content_id_v91(
            domains.CONSTRUCTION_K7_REFERENCE_ALIGNED_CAMPAIGN_V91_DOMAIN,
            payload,
        )
        != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v90_verification_id") != V90_VERIFICATION_ID
    ):
        _fail("V91 frozen campaign identity join changed")
    members = document.get("source_members")
    if type(members) is not list or len(members) != 2:
        _fail("V91 source member inventory changed")
    replay_pool = pool_reference_aligned_source_evidence_v65(
        [
            {
                "member_id": row["member_id"],
                "common_partial_acquisition": row["common_partial_acquisition"],
                "source_evidence": row["source_evidence"],
                "action_catalogue": row["action_catalogue"],
            }
            for row in members
        ],
        layout_domain=LAYOUT_DOMAIN,
    )
    if replay_pool != document.get("reference_aligned_source_pool"):
        _fail("V91 reference-aligned source pool reconstruction diverged")
    template = freeze_role_free_relational_template_library_v70().to_document()[
        "compiled_template_library"
    ]
    replay_acquisition = run_relation_covering_compiler_ready_acquisition_v52(
        replay_pool["canonical_source_pool"],
        role_free_template_library=template,
        maximum_exact_instantiations=8,
        confidence_denominator=64,
    )
    if replay_acquisition != document.get(
        "relation_covering_compiler_ready_acquisition"
    ):
        _fail("V91 compiler-ready acquisition reconstruction diverged")
    clean = all(
        row["source_complete_episode"]["predecessor_v30_episode"]["success"]
        is True
        and row["source_complete_episode"]["predecessor_v30_episode"][
            "all_ground_queries_followed_failed_certificates"
        ]
        is True
        and row["source_complete_episode"]["predecessor_v30_episode"][
            "query_local_exact_overlay_exclusively_used_for_safety"
        ]
        is True
        for row in members
    )
    acquisition = replay_acquisition["compiler_ready_acquisition"]
    gate = document.get("registered_gate")
    if (
        clean is not True
        or gate
        != {
            "required_source_member_count": 2,
            "actual_source_member_count": 2,
            "source_certificate_discipline_clean": True,
            "every_source_member_replayed_aligned_and_retained": True,
            "finite_observation_color_mismatch_overcome_by_raw_reference_alignment": True,
            "compiler_ready_heldout_validated": False,
            "joint_successor_model_compiled": False,
            "every_batch_exact_residual_expression_retained": False,
            "multiple_residual_proposals_jointly_compiled": False,
            "fresh_target_outcome_count": 0,
            "passed": False,
        }
        or acquisition.get("status")
        != "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
        or acquisition.get("heldout_exact_prediction") is not False
        or document.get("reusable_joint_successor_version_space_model") is not None
        or document.get("status")
        != "REFERENCE_ALIGNED_ACQUISITION_ABSTAINED_NONCERTIFICATE"
        or document.get("target_execution_performed") is not False
        or document.get("complete_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V91 failure classification or claim boundary changed")
    verification_payload: dict[str, Any] = {
        "schema": "acfqp.reference_aligned_source_independent_verification.v91",
        "campaign_id": CAMPAIGN_ID,
        "campaign_byte_count": CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": CAMPAIGN_SHA256,
        "preregistration_id": PREREGISTRATION_ID,
        "v90_verification_id": V90_VERIFICATION_ID,
        "source_member_ids": [row["member_id"] for row in members],
        "reference_aligned_source_pool_id": replay_pool[
            "reference_aligned_source_pool_id"
        ],
        "compiler_ready_acquisition_id": acquisition[
            "compiler_ready_acquisition_id"
        ],
        "producer_free_pool_reconstruction": True,
        "producer_free_acquisition_reconstruction": True,
        "source_certificate_discipline_verified": True,
        "reference_alignment_success_verified": True,
        "heldout_terminal_failure_verified": True,
        "typed_result": "SOURCE_GATE_FAILURE_NONCERTIFICATE_VERIFIED",
        "fresh_target_outcome_count": 0,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v91(
            domains.CONSTRUCTION_K7_REFERENCE_ALIGNED_VERIFICATION_V91_DOMAIN,
            verification_payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V91 verification changed")
    return result


__all__ = ("verify_reference_aligned_source_campaign_bytes_v91",)
