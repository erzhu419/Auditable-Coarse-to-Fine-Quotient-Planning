"""Outcome-free preregistration for the V160 three-family campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v160 as domains
from acfqp.construction_k7_progressive_raw_prefix_classifier_receipt_freeze_v160 import (
    CLASSIFIER_RECEIPT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as CLASSIFIER_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as CLASSIFIER_SHA256,
    verify_frozen_progressive_raw_prefix_classifier_receipt_v160,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.progressive_raw_prefix_campaign_core_v160 import (
    FALLBACK_FAMILY,
    MODULAR_FAMILY,
    POSITIVE_FAMILY,
    progressive_raw_prefix_campaign_config_v160,
)


IMPLEMENTATION_COMMITS = ("85cf048", "94c4e5d", "5a13814")
TARGET_OCCURRENCES = (
    (POSITIVE_FAMILY, 1_048_201),
    (POSITIVE_FAMILY, 1_048_202),
    (FALLBACK_FAMILY, 1_048_211),
    (FALLBACK_FAMILY, 1_048_212),
    (MODULAR_FAMILY, 1_048_221),
    (MODULAR_FAMILY, 1_048_222),
)
TARGET_EPISODE_INDICES = (841, 842, 843, 844)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
PREREGISTRATION_ID = "50c290e127e0555fa6b283c90d2ee8bf53f10b59e76d475c64b3c06d5be8cf0c"
EXPECTED_CANONICAL_BYTE_COUNT = 103_196
EXPECTED_CANONICAL_SHA256 = "0e4398e085f228e1bf76199a712aaead674a1a3a6286914410cd2e479892e160"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/progressive_raw_prefix_acquisition_operator_v160.py",
        11_353,
        "bbd5515c48f527362f6b7301359cdfb8530fd736b567e896eb61a696231ea6d6",
    ),
    (
        "src/acfqp/progressive_raw_prefix_campaign_core_v160.py",
        18_461,
        "041d712cf5d985b44b652cfa62b275f3f1973fab7f304d5d0760579065bb3fbc",
    ),
    (
        "src/acfqp/construction_k7_progressive_raw_prefix_classifier_receipt_freeze_v160.py",
        3_015,
        "d7897eea2b1295146cfaa00e4b701aa0f2ef11975b943c48baa1ed3acf8e6cf2",
    ),
    (
        "src/acfqp/progressive_raw_prefix_query_classifier_core_v160.py",
        10_700,
        "439552368965bd2e6b440e30e99e97dd07489c710b05b97399d56ded6faf5f57",
    ),
)


class ConstructionK7ProgressiveRawPrefixPreregistrationV160Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProgressiveRawPrefixPreregistrationV160Error(message)


def campaign_config_v160():
    config = progressive_raw_prefix_campaign_config_v160()
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
    classifier = verify_frozen_progressive_raw_prefix_classifier_receipt_v160(
        classifier_receipt_raw
    )
    if not (
        len(classifier_receipt_raw) == CLASSIFIER_BYTE_COUNT
        and hashlib.sha256(classifier_receipt_raw).hexdigest() == CLASSIFIER_SHA256
        and classifier["classifier_receipt_id"] == CLASSIFIER_RECEIPT_ID
    ):
        _fail("V160 frozen classifier receipt changed")
    source_facts = []
    for path, byte_count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V160 target implementation changed before outcomes")
        source_facts.append(
            {"relative_path": path, "byte_count": byte_count, "sha256": digest}
        )
    config = campaign_config_v160()
    payload = {
        "schema": "acfqp.progressive_raw_prefix_preregistration.v160",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_classifier_receipt": classifier,
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
            "positive_fallback_and_modular_cohorts_required": True,
            "raw_prefix_classifier_decision_must_match_registered_cohort": True,
            "positive_query_policy_strict_aggregate_sample_reduction_required": True,
            "fallback_and_modular_zero_query_policy_regression_required": True,
            "factor_prior_noninferior_everywhere_and_positive_in_aggregate": True,
            "classifier_prefix_labels_must_be_reused_as_acquisition_labels": True,
            "no_additional_classifier_only_target_labels": True,
            "decision_before_full_initial_action_frontier_required": True,
            "both_arm_receding_planning_and_certificate_failure_local_recovery_required": True,
            "all_executed_actions_require_v109_receipts": True,
            "strict_ood_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "progressive_raw_prefix_transfer_observed": False,
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
        "preregistration_id": domains.extension_content_id_v160(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V160_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProgressiveRawPrefixPreregistrationV160:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_progressive_raw_prefix_preregistration_v160(
    classifier_receipt_raw: bytes,
):
    document = _document(classifier_receipt_raw)
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V160 frozen target preregistration changed")
    return ProgressiveRawPrefixPreregistrationV160(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v160",
    "freeze_progressive_raw_prefix_preregistration_v160",
)
