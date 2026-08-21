"""Producer-free reconstruction of the frozen V90 abstract-primary audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import NoReturn

from acfqp.abstract_planning_primary_audit_core_v90 import (
    build_abstract_planning_primary_audit_document_v90,
)
from acfqp import construction_k7_domain_registry_extension_v90 as domains
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V89_CAMPAIGN_ID = "00e954daeda5823e22a4c489dbf72a207570f36b8ad008488cd38d649d90aaed"
V89_CAMPAIGN_BYTE_COUNT = 2_444_947
V89_CAMPAIGN_SHA256 = "277a28d516d4c73c01f1e5d58441d7d74775a2fe3caac80e885d90dcf578f21d"
V89_VERIFICATION_ID = "6dd9d5c1dab579ef7e0192bc64d486b82468e56a28d1d7a92595505c77dc8f39"
PREREGISTRATION_ID = "848a6858108179348d53176e6113eeae145c3ce4f18c4181268e482cf2384c28"
AUDIT_ID = "1470de5895af6fb5215bfc34c29aa14f14f49af375ba003665ebc008d555e503"
AUDIT_BYTE_COUNT = 113_015
AUDIT_SHA256 = "3607bba575cc24ab41e52181a57a84911a1de85460505102aeb4266c52341d05"
VERIFICATION_ID = "9e98d0c4d4d63b87f5dbad9a21ff61f5509e38f63f08733981dfbe0eb7d5926c"
EXPECTED_CANONICAL_BYTE_COUNT = 2_166
EXPECTED_CANONICAL_SHA256 = "d4f04b6fe73e6a91673e3cb83ea9b6c74a86683b04e853de8218f8cf93cb0ae1"


class ConstructionK7AbstractPlanningPrimaryIndependentVerifierV90Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractPlanningPrimaryIndependentVerifierV90Error(message)


def verify_abstract_planning_primary_audit_bytes_v90(
    v89_campaign_raw: bytes, v90_audit_raw: bytes
) -> bytes:
    if (
        type(v89_campaign_raw) is not bytes
        or len(v89_campaign_raw) != V89_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v89_campaign_raw).hexdigest() != V89_CAMPAIGN_SHA256
        or type(v90_audit_raw) is not bytes
        or len(v90_audit_raw) != AUDIT_BYTE_COUNT
        or hashlib.sha256(v90_audit_raw).hexdigest() != AUDIT_SHA256
    ):
        _fail("V90 input bytes changed")
    campaign = loads_canonical_json(v89_campaign_raw)
    audit = loads_canonical_json(v90_audit_raw)
    if (
        type(campaign) is not dict
        or type(audit) is not dict
        or canonical_json_bytes(campaign) != v89_campaign_raw
        or canonical_json_bytes(audit) != v90_audit_raw
        or campaign.get("campaign_id") != V89_CAMPAIGN_ID
        or audit.get("audit_id") != AUDIT_ID
    ):
        _fail("V90 input canonical identities changed")
    audit_payload = {key: value for key, value in audit.items() if key != "audit_id"}
    if domains.extension_content_id_v90(
        domains.CONSTRUCTION_K7_ABSTRACT_PRIMARY_AUDIT_V90_DOMAIN,
        audit_payload,
    ) != AUDIT_ID:
        _fail("V90 audit content identity changed")
    projected = load_projected_model_artifact_v86()
    applicability = load_action_applicability_model_v87()
    reconstructed = build_abstract_planning_primary_audit_document_v90(
        campaign,
        PREREGISTRATION_ID,
        V89_VERIFICATION_ID,
        projected["projected_disagreement_successor_model"],
        applicability["action_applicability_program"],
        maximum_abstract_depth=12,
        maximum_abstract_support_branch_evaluations=1_000_000,
        abstract_support_feasible_beam_width=32,
    )
    if canonical_json_bytes(reconstructed) != v90_audit_raw:
        _fail("V90 producer-free audit reconstruction diverged")
    gate = audit.get("registered_gate")
    if (
        gate
        != {
            "required_occurrence_audit_count": 6,
            "actual_occurrence_audit_count": 6,
            "every_exactly_certified_action_abstractly_proposed_first": True,
            "non_proposed_ground_action_query_count": 0,
            "proposal_mismatch_count": 0,
            "audited_exact_transition_state_count": 264,
            "replayed_abstract_planning_compute_events": 87372,
            "frozen_v89_accounting_exactly_reproduced": True,
            "passed": True,
        }
        or audit.get("multi_step_planning_primarily_in_abstract_model_verified")
        is not True
        or audit.get("claim_scope")
        != "FROZEN_V89_PERMUTATION_MATCHED_BALANCED_BATCH_WORKLOAD_ONLY"
        or audit.get("ground_queries_used_only_for_exact_policy_certificate")
        is not True
        or audit.get("ground_kernel_accessed_by_v90_audit") is not False
        or audit.get("complete_world_model_synthesized") is not False
        or audit.get("official_execution_allowed") is not False
        or audit.get("official_scalar_cost") is not None
        or audit.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or audit.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V90 claim boundary changed")
    occurrence_ids = []
    proposal_audit_ids = []
    for row in audit["occurrence_audits"]:
        payload = {
            key: value for key, value in row.items() if key != "occurrence_audit_id"
        }
        if row.get("occurrence_audit_id") != domains.extension_content_id_v90(
            domains.CONSTRUCTION_K7_ABSTRACT_PRIMARY_OCCURRENCE_V90_DOMAIN,
            payload,
        ):
            _fail("V90 occurrence audit identity changed")
        proposal = row.get("proposal_primary_audit")
        if (
            type(proposal) is not dict
            or row.get("proposal_primary_audit_id") != proposal.get("audit_id")
            or proposal.get(
                "ground_queries_used_only_to_certify_abstractly_proposed_policy"
            )
            is not True
            or proposal.get("proposal_mismatch_count") != 0
            or proposal.get("non_proposed_alternative_action_query_count") != 0
            or any(
                item.get("first_exactly_certified_action_matches_abstract_proposal")
                is not True
                or item.get("non_proposed_alternative_action_query_count") != 0
                or item.get("exactly_certified_action_keys_in_query_order")
                != [item.get("abstract_proposed_action_key")]
                for item in proposal.get("per_state_audit", [])
            )
        ):
            _fail("V90 per-state proposal audit changed")
        occurrence_ids.append(row["occurrence_audit_id"])
        proposal_audit_ids.append(row["proposal_primary_audit_id"])
    payload = {
        "schema": "acfqp.abstract_planning_primary_independent_verification.v90",
        "v89_campaign_id": V89_CAMPAIGN_ID,
        "v89_campaign_byte_count": V89_CAMPAIGN_BYTE_COUNT,
        "v89_campaign_sha256": V89_CAMPAIGN_SHA256,
        "v89_verification_id": V89_VERIFICATION_ID,
        "v90_preregistration_id": PREREGISTRATION_ID,
        "v90_audit_id": AUDIT_ID,
        "v90_audit_byte_count": AUDIT_BYTE_COUNT,
        "v90_audit_sha256": AUDIT_SHA256,
        "occurrence_audit_ids": occurrence_ids,
        "proposal_primary_audit_ids": proposal_audit_ids,
        "occurrence_audit_count": 6,
        "replayed_abstract_plan_count": 264,
        "proposal_mismatch_count": 0,
        "non_proposed_ground_action_query_count": 0,
        "producer_free_exact_reconstruction": True,
        "multi_step_planning_primarily_in_abstract_model_verified": True,
        "claim_scope": "FROZEN_V89_PERMUTATION_MATCHED_BALANCED_BATCH_WORKLOAD_ONLY",
        "exact_query_local_certificate_remained_only_safety_authority": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v90(
            domains.CONSTRUCTION_K7_ABSTRACT_PRIMARY_VERIFICATION_V90_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V90 verification changed")
    return result


__all__ = ("verify_abstract_planning_primary_audit_bytes_v90",)
