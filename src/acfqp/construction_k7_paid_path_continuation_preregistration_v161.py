"""Outcome-free preregistration for the V161 correction campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v161 as domains
from acfqp.construction_k7_paid_path_prefix_classifier_receipt_freeze_v161 import (
    CLASSIFIER_RECEIPT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as CLASSIFIER_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as CLASSIFIER_SHA256,
    verify_frozen_paid_path_prefix_classifier_receipt_v161,
)
from acfqp.paid_path_continuation_campaign_core_v161 import (
    FALLBACK_FAMILY,
    MODULAR_FAMILY,
    POSITIVE_FAMILY,
    paid_path_continuation_campaign_config_v161,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("160bf28", "3c6a29d", "d5ef273")
TARGET_OCCURRENCES = (
    (POSITIVE_FAMILY, 1_048_301),
    (POSITIVE_FAMILY, 1_048_302),
    (FALLBACK_FAMILY, 1_048_311),
    (FALLBACK_FAMILY, 1_048_312),
    (MODULAR_FAMILY, 1_048_321),
    (MODULAR_FAMILY, 1_048_322),
)
TARGET_EPISODE_INDICES = (861, 862, 863, 864)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
V160_FAILED_CAMPAIGN_ID = "38cbf013db9ceb15605807f5aa83564f7b89fc559d793dcfd7a049d7095771c6"
V160_FAILURE_SHA256 = "1d554b56462031920d3573ed1969997eedd8955426bfd024f8355bfab362d3ab"
PREREGISTRATION_ID = "84bfbf8e9be7de54d0ac95516e5adf18cd5cf7ea08ddb8c22881795c234ee13e"
EXPECTED_CANONICAL_BYTE_COUNT = 387_062
EXPECTED_CANONICAL_SHA256 = "5ceae024494b0d9396a7c4e4eeb480b9db7ac620fbc107e391f427261247bfa3"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/paid_path_continuation_acquisition_operator_v161.py",
        10_416,
        "06b988cf1c22a372ddfdcbd5b15370215396168ddf8e48f33bce05ded3456ee8",
    ),
    (
        "src/acfqp/paid_path_continuation_campaign_core_v161.py",
        11_411,
        "351b09256d612f011bb80b2dac8be64b301865742fd5873cd74f0a96d916dacf",
    ),
    (
        "src/acfqp/construction_k7_paid_path_prefix_classifier_receipt_freeze_v161.py",
        2_850,
        "6750ccf752b114aade4af9185d73d7758de7f9704b824f9babe18742940106ef",
    ),
    (
        "src/acfqp/paid_path_prefix_query_classifier_core_v161.py",
        2_698,
        "33c647f97d13ee5549af2e0c36719dd5150301e72557697516743cfeb3181f5f",
    ),
)


class ConstructionK7PaidPathContinuationPreregistrationV161Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PaidPathContinuationPreregistrationV161Error(message)


def campaign_config_v161():
    config = paid_path_continuation_campaign_config_v161()
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(classifier_receipt_raw: bytes):
    classifier = verify_frozen_paid_path_prefix_classifier_receipt_v161(
        classifier_receipt_raw
    )
    if not (
        len(classifier_receipt_raw) == CLASSIFIER_BYTE_COUNT
        and hashlib.sha256(classifier_receipt_raw).hexdigest() == CLASSIFIER_SHA256
        and classifier["classifier_receipt_id"] == CLASSIFIER_RECEIPT_ID
        and classifier["failed_v160_campaign_id"] == V160_FAILED_CAMPAIGN_ID
        and classifier["failed_v160_record_sha256"] == V160_FAILURE_SHA256
    ):
        _fail("V161 frozen classifier or V160 failure binding changed")
    source_facts = []
    for path, byte_count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V161 target implementation changed before outcomes")
        source_facts.append(
            {"relative_path": path, "byte_count": byte_count, "sha256": digest}
        )
    config = campaign_config_v161()
    payload = {
        "schema": "acfqp.paid_path_continuation_preregistration.v161",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_classifier_receipt": classifier,
        "failed_v160_campaign_id": V160_FAILED_CAMPAIGN_ID,
        "failed_v160_record_sha256": V160_FAILURE_SHA256,
        "target_occurrences": [
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
        "maximum_acquisition_labels_by_family": {
            family: config["families"][family]["maximum_acquisition_labels"]
            for family in (POSITIVE_FAMILY, FALLBACK_FAMILY, MODULAR_FAMILY)
        },
        "registered_gate": {
            "fresh_target_identities_fixed_before_target_outcomes": True,
            "v160_failed_identity_must_remain_failed": True,
            "positive_fallback_and_modular_cohorts_required": True,
            "fallback_must_reuse_exact_path_first_generator": True,
            "fallback_prior_id_labels_and_raw_sha_must_equal_legacy": True,
            "positive_switch_strict_aggregate_sample_reduction_required": True,
            "fallback_and_modular_exact_zero_regression_required": True,
            "factor_prior_noninferior_everywhere_and_positive_in_aggregate": True,
            "no_additional_classifier_only_target_labels": True,
            "both_arm_receding_planning_and_certificate_failure_local_recovery_required": True,
            "all_executed_actions_require_v109_receipts": True,
            "strict_ood_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "paid_path_continuation_transfer_observed": False,
            "v160_failure_reclassified_as_success": False,
            "query_policy_classifier_is_model_planning_or_certificate_authority": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v161(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V161_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PaidPathContinuationPreregistrationV161:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_paid_path_continuation_preregistration_v161(
    classifier_receipt_raw: bytes,
):
    document = _document(classifier_receipt_raw)
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V161 frozen target preregistration changed")
    return PaidPathContinuationPreregistrationV161(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v161",
    "freeze_paid_path_continuation_preregistration_v161",
)
