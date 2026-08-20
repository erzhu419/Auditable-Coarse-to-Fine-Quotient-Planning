"""Frozen typed V75r2 failure before campaign issuance."""

from __future__ import annotations

import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v75r2 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PREREGISTRATION_ID = "27391ec9730a7038e78a17bbf95bd83b95fefc2e6a982a67f170f836553b995e"
FAILURE_ID = "1cd0c27a096001dd98a89d8e169642cb1e75fb716f39ff649dec1997858d9b48"
EXPECTED_CANONICAL_BYTE_COUNT = 1_560
EXPECTED_CANONICAL_SHA256 = "e75bdcbdbb8b3155f69da35109ba8c0e2423022ed4fdd76c32eaef02775d1812"


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.normalized_priority_failure.v75r2",
        "preregistration_id": PREREGISTRATION_ID,
        "campaign_issued": False,
        "campaign_id": None,
        "failure_phase": "POST_TARGET_PROCESS_POOL_AGGREGATION",
        "failure_class": "FAILED_TARGET_ARM_AGGREGATED_AS_SUCCESS_SHAPE",
        "exception_type": "KeyError",
        "exception_message": "'portable_priority_ordering_accepted_count'",
        "exception_source": {
            "relative_path": "src/acfqp/normalized_portable_priority_campaign_core_v75r2.py",
            "function": "build_normalized_portable_priority_campaign_document_v75r2",
            "operation": "priority_used aggregation",
        },
        "observed_precondition": (
            "AT_LEAST_ONE_TARGET_ARM_RETURNED_A_TYPED_NONCERTIFICATE_FAILURE_RECORD"
        ),
        "root_cause": (
            "AGGREGATOR_READ_SUCCESS_ONLY_PRIORITY_FIELD_BEFORE_FAIL_CLOSED_ARM_FILTER"
        ),
        "source_stage_completed_before_failure": True,
        "target_process_pool_completed_before_failure": True,
        "partial_target_outcomes_recovered_or_claimed": False,
        "registered_gate_evaluated": False,
        "scientific_success_or_reduction_claimed": False,
        "same_identity_rerun_allowed": False,
        "corrective_successor_requires_fresh_target_identities": True,
        "corrective_successor_must_preserve_typed_arm_failure_reason": True,
        "failure_preserved_before_corrective_successor": True,
        "producer_free_verification_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "status": "PREREGISTERED_EXECUTION_FAILURE_PRESERVED_NO_CAMPAIGN",
    }
    return {
        **payload,
        "failure_id": domains.extension_content_id_v75r2(
            domains.CONSTRUCTION_K7_NORMALIZED_PRIORITY_FAILURE_V75R2_DOMAIN,
            payload,
        ),
    }


def freeze_normalized_priority_failure_v75r2() -> bytes:
    raw = canonical_json_bytes(_document())
    document = loads_canonical_json(raw)
    if FAILURE_ID != "0" * 64 and (
        document["failure_id"] != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("frozen V75r2 failure changed")
    return raw


__all__ = ("FAILURE_ID", "freeze_normalized_priority_failure_v75r2")
