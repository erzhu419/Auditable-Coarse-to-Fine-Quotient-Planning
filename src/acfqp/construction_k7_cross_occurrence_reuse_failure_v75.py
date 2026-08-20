"""Frozen typed record of the preregistered V75 Gate failure."""

from __future__ import annotations

import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v75 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PREREGISTRATION_ID = "7b631cb303116d941b20a3f89e3178df95694eca8822712eb078009ea2478a17"
FAILED_CAMPAIGN_ID = "2879cfb4bb3267d13fc1eef588f9d37c0cbe7a01ee9f5b6bda7385720e256c6c"
FAILED_CAMPAIGN_BYTE_COUNT = 1_682_606
FAILED_CAMPAIGN_SHA256 = "db8ed958b7e36055ab123435e5c3f6a26d345f1b024c6639c6bc1553d5ec8e9a"
FAILURE_ID = "975419a711a99e4c546555b6790dd205cc98f328a2001fc99316b3f712cd2921"
EXPECTED_CANONICAL_BYTE_COUNT = 1_872
EXPECTED_CANONICAL_SHA256 = "818d84de5bd86d1282f007ad72271e31e7ecc5a9a3f8be848c4b7b53b719be19"


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.cross_occurrence_reuse_failure.v75",
        "preregistration_id": PREREGISTRATION_ID,
        "failed_campaign_id": FAILED_CAMPAIGN_ID,
        "failed_campaign_byte_count": FAILED_CAMPAIGN_BYTE_COUNT,
        "failed_campaign_sha256": FAILED_CAMPAIGN_SHA256,
        "failed_registered_relation": (
            "AGGREGATE_DERIVED_TARGET_LABELS_LT_STRICT_AND_AT_LEAST_ONE_"
            "TARGET_OCCURRENCE_STRICTLY_REDUCED"
        ),
        "registered_gate": {
            "compiled_source_count": 2,
            "fresh_target_occurrence_count": 4,
            "target_arm_failure_count": 0,
            "certificate_discipline_clean": True,
            "incompatible_schema_ood_rejection_count": 4,
            "derived_target_certificate_local_labels": 91,
            "strict_target_certificate_local_labels": 91,
            "derived_minus_strict_target_labels": 0,
            "reduced_target_occurrence_count": 0,
            "passed": False,
        },
        "target_rows": [
            {
                "family": "COUPLED_EXCHANGE",
                "source_seed": 752_102,
                "target_seed": 761_201,
                "derived_labels": 15,
                "strict_labels": 15,
            },
            {
                "family": "COUPLED_EXCHANGE",
                "source_seed": 752_102,
                "target_seed": 761_202,
                "derived_labels": 22,
                "strict_labels": 22,
            },
            {
                "family": "MAINTENANCE_CASCADE",
                "source_seed": 753_101,
                "target_seed": 761_301,
                "derived_labels": 32,
                "strict_labels": 32,
            },
            {
                "family": "MAINTENANCE_CASCADE",
                "source_seed": 753_101,
                "target_seed": 761_302,
                "derived_labels": 22,
                "strict_labels": 22,
            },
        ],
        "cross_occurrence_execution_and_certificate_safety_succeeded": True,
        "cross_occurrence_sample_reduction_observed": False,
        "same_identity_rerun_or_gate_relaxation_allowed": False,
        "failure_preserved_before_any_corrective_successor": True,
        "producer_free_verification_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "status": "PREREGISTERED_CROSS_OCCURRENCE_REDUCTION_GATE_FAILED_PRESERVED",
    }
    return {
        **payload,
        "failure_id": domains.extension_content_id_v75(
            domains.CONSTRUCTION_K7_CROSS_OCCURRENCE_REUSE_FAILURE_V75_DOMAIN,
            payload,
        ),
    }


def freeze_cross_occurrence_reuse_failure_v75() -> bytes:
    raw = canonical_json_bytes(_document())
    document = loads_canonical_json(raw)
    if (
        document["failure_id"] != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ) and FAILURE_ID != "0" * 64:
        raise ValueError("frozen V75 failure changed")
    return raw


__all__ = ("FAILURE_ID", "freeze_cross_occurrence_reuse_failure_v75")
