"""Outcome-free preregistration for the V163 safe sample-tax campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v163 as domains
from acfqp.construction_k7_paid_path_prefix_classifier_receipt_freeze_v161 import (
    CLASSIFIER_RECEIPT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as CLASSIFIER_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as CLASSIFIER_SHA256,
    verify_frozen_paid_path_prefix_classifier_receipt_v161,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.safe_paid_path_sample_tax_campaign_core_v163 import (
    FALLBACK_FAMILY,
    MODULAR_FAMILY,
    POSITIVE_FAMILY,
    safe_paid_path_sample_tax_campaign_config_v163,
)


IMPLEMENTATION_COMMITS = ("de12241", "f307b3c")
TARGET_OCCURRENCES = (
    (POSITIVE_FAMILY, 1_048_501),
    (POSITIVE_FAMILY, 1_048_502),
    (POSITIVE_FAMILY, 1_048_503),
    (POSITIVE_FAMILY, 1_048_504),
    (FALLBACK_FAMILY, 1_048_511),
    (FALLBACK_FAMILY, 1_048_512),
    (MODULAR_FAMILY, 1_048_521),
    (MODULAR_FAMILY, 1_048_522),
)
TARGET_EPISODE_INDICES = (901, 902, 903, 904)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 8
V162_FAILED_CAMPAIGN_ID = (
    "84250a94f22de611e57987c88bedbf5d44cc2bfa8f92cdec942ef625daa6b69a"
)
V162_FAILURE_BYTE_COUNT = 2_561
V162_FAILURE_SHA256 = (
    "3f69c16b089ce2bb95a458b1e046dd19c3d262b953397bd79d8579e1f9f96c7a"
)
PREREGISTRATION_ID = (
    "214233cd0d3af6c319fc872a03813890e1920d4e6e3049158c25caf2454ce9fe"
)
EXPECTED_CANONICAL_BYTE_COUNT = 389_728
EXPECTED_CANONICAL_SHA256 = (
    "0f328858df6f19a90cd15ec3c1ab95744e99112d505a8b9f97ccfab64ffd2d56"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/certified_paid_path_switch_acquisition_operator_v162.py",
        12_523,
        "da2fb40bd62af0952b87e2e8256b5e3e92c3d7f486751143f6d6fbe7d216e06a",
    ),
    (
        "src/acfqp/safe_paid_path_sample_tax_campaign_core_v163.py",
        9_834,
        "7e9665607c6da2d29b11f409f580e04bed4d67ce72a2a741e43760c5352dd9a3",
    ),
    (
        "src/acfqp/construction_k7_domain_registry_extension_v163.py",
        1_413,
        "ba7e6ae04e91724a1aaa904b2092951eb79e6dbe8af5b8f31aedf276f07c251f",
    ),
)


class ConstructionK7SafePaidPathSampleTaxPreregistrationV163Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SafePaidPathSampleTaxPreregistrationV163Error(message)


def campaign_config_v163():
    config = safe_paid_path_sample_tax_campaign_config_v163()
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
        and classifier["fresh_v161_target_outcomes_accessed"] is False
    ):
        _fail("V163 frozen classifier binding changed")
    source_facts = []
    for path, byte_count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V163 implementation changed before outcomes")
        source_facts.append(
            {"relative_path": path, "byte_count": byte_count, "sha256": digest}
        )
    failure_raw = (
        SOURCE_ROOT
        / ".tmp/exact-freeze/v162_certified_paid_path_switch_campaign_failure.json"
    ).read_bytes()
    if not (
        len(failure_raw) == V162_FAILURE_BYTE_COUNT
        and hashlib.sha256(failure_raw).hexdigest() == V162_FAILURE_SHA256
    ):
        _fail("V162 failure evidence changed")
    failure = loads_canonical_json(failure_raw)
    if not (
        failure["failed_campaign_id"] == V162_FAILED_CAMPAIGN_ID
        and failure["failed_result_not_reclassified_as_success"] is True
        and failure["same_identity_rerun_forbidden"] is True
    ):
        _fail("V162 failure semantics changed")
    config = campaign_config_v163()
    payload = {
        "schema": "acfqp.safe_paid_path_sample_tax_preregistration.v163",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_classifier_receipt": classifier,
        "frozen_v162_failure": {
            "relative_path": ".tmp/exact-freeze/v162_certified_paid_path_switch_campaign_failure.json",
            "byte_count": V162_FAILURE_BYTE_COUNT,
            "sha256": V162_FAILURE_SHA256,
            "document": failure,
        },
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
            "v162_failed_identity_must_remain_failed": True,
            "positive_fallback_and_modular_cohorts_required": True,
            "at_least_one_certified_switch_required": True,
            "query_policy_noninferior_everywhere_required": True,
            "every_exact_fallback_zero_regression_required": True,
            "strict_query_policy_reduction_not_required": True,
            "factor_prior_noninferior_everywhere_required": True,
            "factor_prior_strict_aggregate_sample_reduction_required": True,
            "no_additional_classifier_only_target_labels": True,
            "both_arm_receding_planning_and_certificate_failure_local_recovery_required": True,
            "all_executed_actions_require_v109_receipts": True,
            "strict_ood_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "safe_query_and_factor_prior_sample_tax_reduction_observed": False,
            "strict_query_policy_sample_reduction_claimed": False,
            "v162_failure_reclassified_as_success": False,
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
        "preregistration_id": domains.extension_content_id_v163(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V163_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SafePaidPathSampleTaxPreregistrationV163:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_safe_paid_path_sample_tax_preregistration_v163(
    classifier_receipt_raw: bytes,
):
    document = _document(classifier_receipt_raw)
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V163 frozen target preregistration changed")
    return SafePaidPathSampleTaxPreregistrationV163(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v163",
    "freeze_safe_paid_path_sample_tax_preregistration_v163",
)
