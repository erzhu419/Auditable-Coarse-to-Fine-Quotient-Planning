"""Outcome-free preregistration for the V162 certified-switch campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v162 as domains
from acfqp.certified_paid_path_switch_campaign_core_v162 import (
    FALLBACK_FAMILY,
    MODULAR_FAMILY,
    POSITIVE_FAMILY,
    certified_paid_path_switch_campaign_config_v162,
)
from acfqp.construction_k7_paid_path_prefix_classifier_receipt_freeze_v161 import (
    CLASSIFIER_RECEIPT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as CLASSIFIER_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as CLASSIFIER_SHA256,
    verify_frozen_paid_path_prefix_classifier_receipt_v161,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("bac9eb4", "de12241")
TARGET_OCCURRENCES = (
    (POSITIVE_FAMILY, 1_048_401),
    (POSITIVE_FAMILY, 1_048_402),
    (FALLBACK_FAMILY, 1_048_411),
    (FALLBACK_FAMILY, 1_048_412),
    (MODULAR_FAMILY, 1_048_421),
    (MODULAR_FAMILY, 1_048_422),
)
TARGET_EPISODE_INDICES = (881, 882, 883, 884)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
V160_FAILED_CAMPAIGN_ID = (
    "38cbf013db9ceb15605807f5aa83564f7b89fc559d793dcfd7a049d7095771c6"
)
V160_FAILURE_BYTE_COUNT = 1_953
V160_FAILURE_SHA256 = (
    "1d554b56462031920d3573ed1969997eedd8955426bfd024f8355bfab362d3ab"
)
V161_FAILED_PREREGISTRATION_ID = (
    "84bfbf8e9be7de54d0ac95516e5adf18cd5cf7ea08ddb8c22881795c234ee13e"
)
V161_FAILURE_BYTE_COUNT = 301
V161_FAILURE_SHA256 = (
    "2a6658caac00c9c4257311e6a1bcc9667afadc13339d36aff4d84d6ea7293cab"
)
PREREGISTRATION_ID = (
    "6bf1cabf3128128e28f98429a7dd15e6e2b3e74e4a38db216c1b03746a5fe9c3"
)
EXPECTED_CANONICAL_BYTE_COUNT = 389_565
EXPECTED_CANONICAL_SHA256 = (
    "72d3cdd65e25b11c40e3a87b636b6682919c7a6751cbe5f9b5fbeb74f1330806"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/certified_paid_path_switch_acquisition_operator_v162.py",
        12_523,
        "da2fb40bd62af0952b87e2e8256b5e3e92c3d7f486751143f6d6fbe7d216e06a",
    ),
    (
        "src/acfqp/certified_paid_path_switch_campaign_core_v162.py",
        13_468,
        "15a5876096fd4f21867e4c9323099679c61e955ec166742f33c75314f790c09e",
    ),
    (
        "src/acfqp/construction_k7_domain_registry_extension_v162.py",
        1_586,
        "dfc293f59fb978e80ee42c78263fb463dba7bbc6a855e79d43b2d83f7a0a34f4",
    ),
)


class ConstructionK7CertifiedPaidPathSwitchPreregistrationV162Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertifiedPaidPathSwitchPreregistrationV162Error(message)


def campaign_config_v162():
    config = certified_paid_path_switch_campaign_config_v162()
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


def _failure_fact(name, expected_count, expected_sha):
    raw = (SOURCE_ROOT / ".tmp/exact-freeze" / name).read_bytes()
    if len(raw) != expected_count or hashlib.sha256(raw).hexdigest() != expected_sha:
        _fail("V162 predecessor failure evidence changed")
    return {
        "relative_path": f".tmp/exact-freeze/{name}",
        "byte_count": expected_count,
        "sha256": expected_sha,
        "document": loads_canonical_json(raw),
    }


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
        _fail("V162 frozen classifier binding changed")
    source_facts = []
    for path, byte_count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V162 target implementation changed before outcomes")
        source_facts.append(
            {"relative_path": path, "byte_count": byte_count, "sha256": digest}
        )
    v160_failure = _failure_fact(
        "v160_progressive_raw_prefix_campaign_failure.json",
        V160_FAILURE_BYTE_COUNT,
        V160_FAILURE_SHA256,
    )
    v161_failure = _failure_fact(
        "v161_paid_path_continuation_campaign_failure.json",
        V161_FAILURE_BYTE_COUNT,
        V161_FAILURE_SHA256,
    )
    if not (
        v160_failure["document"]["failed_campaign_id"] == V160_FAILED_CAMPAIGN_ID
        and v160_failure["document"]["failed_result_not_reclassified_as_success"]
        is True
        and v161_failure["document"]["preregistration_id"]
        == V161_FAILED_PREREGISTRATION_ID
        and v161_failure["document"]["terminal_state"]
        == "FAILED_NO_SAME_IDENTITY_RERUN"
    ):
        _fail("V162 predecessor failure semantics changed")
    config = campaign_config_v162()
    payload = {
        "schema": "acfqp.certified_paid_path_switch_preregistration.v162",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_classifier_receipt": classifier,
        "frozen_v160_failure": v160_failure,
        "frozen_v161_failure": v161_failure,
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
            "v160_and_v161_failures_must_remain_failed": True,
            "positive_fallback_and_modular_cohorts_required": True,
            "switch_requires_classifier_positive_and_paid_relation_witness": True,
            "unwitnessed_classifier_positive_must_exactly_fallback": True,
            "fallback_must_continue_same_exact_path_first_generator": True,
            "fallback_prior_id_labels_and_raw_sha_must_equal_legacy": True,
            "at_least_one_certified_switch_required": True,
            "certified_switch_strict_aggregate_sample_reduction_required": True,
            "all_exact_fallbacks_zero_regression_required": True,
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
            "certified_paid_path_switch_transfer_observed": False,
            "v160_or_v161_failure_reclassified_as_success": False,
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
        "preregistration_id": domains.extension_content_id_v162(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V162_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CertifiedPaidPathSwitchPreregistrationV162:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_certified_paid_path_switch_preregistration_v162(
    classifier_receipt_raw: bytes,
):
    document = _document(classifier_receipt_raw)
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V162 frozen target preregistration changed")
    return CertifiedPaidPathSwitchPreregistrationV162(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v162",
    "freeze_certified_paid_path_switch_preregistration_v162",
)
