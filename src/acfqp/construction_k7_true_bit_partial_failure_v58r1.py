"""Frozen failed V58r1 predecessor; same-identity execution is forbidden."""

from __future__ import annotations

import hashlib

from acfqp import construction_k7_domain_registry_extension_v58r1 as domains
from acfqp.phase3e_ids import canonical_json_bytes


FAILURE_ID = "62786c619f6ea7354929c23e25fbd5ea4c9e24fee9cedb5917c0edb207186cf6"
EXPECTED_CANONICAL_BYTE_COUNT = 1_361
EXPECTED_CANONICAL_SHA256 = "625719621356d4b66a0199ced4d11c4640a342012af2ebb6bb552eb40d0b9eb7"


def freeze_true_bit_partial_failure_v58r1() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": "acfqp.true_bit_partial_registered_failure.v58r1",
        "preregistration_id": (
            "9677242df0fb8c27190b00a5190e38b4cb33efd2541c8caafb65d10167368579"
        ),
        "implementation_commit": "36c32fc",
        "preregistration_commit": "8232d5c",
        "registered_execution_started": True,
        "campaign_artifact_returned": False,
        "failure_stage": "MATCHED_ACQUISITION_PREFIX_POST_AUDIT",
        "failed_occurrence_identity": None,
        "failed_occurrence_identity_unavailable_reason": (
            "PROCESS_POOL_EXCEPTION_DID_NOT_SERIALIZE_ARGUMENT_IDENTITY"
        ),
        "failure_condition": "ASYMMETRIC_PREFIX_COMPARISON_ASSUMED_PRIOR_STOPPED_FIRST",
        "exception_type": "TrueBitPartialThreeDomainCampaignCoreV58R1Error",
        "exception_message": "V58r1 matched acquisition prefix changed",
        "trace_leaf": {
            "relative_path": (
                "src/acfqp/true_bit_partial_three_domain_campaign_core_v58r1.py"
            ),
            "line": 335,
            "function": "acquire_matched_true_bit_models_v58r1",
        },
        "registered_worker_count": 4,
        "partial_scientific_artifacts_persisted": False,
        "failed_worker_partial_state_reused": False,
        "same_identity_rerun_forbidden": True,
        "fresh_successor_identity_required": True,
        "successor_correction": (
            "COMPARE_BOTH_ARMS_OVER_SYMMETRIC_MINIMUM_COMMON_PREFIX"
        ),
        "successor_must_preserve_true_bit_and_no_frontier_contract": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    raw = canonical_json_bytes(payload)
    identity = domains.extension_content_id_v58r1(
        domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_CAMPAIGN_V58R1_DOMAIN,
        payload,
    )
    if FAILURE_ID != "0" * 64 and (
        identity != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("frozen V58r1 registered failure changed")
    return {**payload, "failure_id": identity}


__all__ = ("FAILURE_ID", "freeze_true_bit_partial_failure_v58r1")
