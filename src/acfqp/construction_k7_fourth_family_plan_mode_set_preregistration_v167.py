"""Outcome-free preregistration for the fresh V167 successor."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v167 as domains
from acfqp.fourth_family_plan_mode_set_campaign_core_v167 import (
    FALLBACK_FAMILY,
    MAINTENANCE_FAMILY,
    MODULAR_FAMILY,
    POSITIVE_FAMILY,
    TARGET_FAMILIES,
    V166_FAILURE_ID,
    fourth_family_plan_mode_set_campaign_config_v167,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("24490f6",)
TARGET_OCCURRENCES = (
    (POSITIVE_FAMILY, 1_048_811),
    (POSITIVE_FAMILY, 1_048_812),
    (FALLBACK_FAMILY, 1_048_821),
    (FALLBACK_FAMILY, 1_048_822),
    (MODULAR_FAMILY, 1_048_831),
    (MODULAR_FAMILY, 1_048_832),
    (MAINTENANCE_FAMILY, 1_048_841),
    (MAINTENANCE_FAMILY, 1_048_842),
)
TARGET_EPISODE_INDICES = (947, 948, 949, 950)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 8
V166_PREREGISTRATION_ID = (
    "043a502c5f6f7da983ce1859edace7a74aca28645b688362bcdb2760620337c8"
)
V166_PREREGISTRATION_BYTE_COUNT = 4_681
V166_PREREGISTRATION_SHA256 = (
    "7ef9a7141c6b181d5cbc14a6174a5d273b04f8260a586d3c9e63f35728d3da6e"
)
V166_FAILURE_BYTE_COUNT = 1_800
V166_FAILURE_SHA256 = (
    "22333a80c08c1915da8659b25651ee8b49850a7fea132d0acb6df0540dabc51c"
)
PREREGISTRATION_ID = (
    "1f42238f1162e441986b88a43aad2cbf097a8d93280e9e181cab116c5d003c57"
)
EXPECTED_CANONICAL_BYTE_COUNT = 4_179
EXPECTED_CANONICAL_SHA256 = (
    "18b072b134665a6e1d262eabbe26a76819c4c5d5b3fdff6bc50839f66281e5ee"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/fourth_family_plan_mode_set_campaign_core_v167.py",
        10_833,
        "443ff2ff146c70c35b8a55a6c9fd372a12854719d7c05b72a1d99160d42c3326",
    ),
    (
        "src/acfqp/applicable_plan_mode_set_sequence_v167.py",
        5_653,
        "1fe7fbc649e4a6254c8c699a1b27ec8136cfcf61ef37d35cf3164b4477af5925",
    ),
    (
        "src/acfqp/construction_k7_domain_registry_extension_v167.py",
        1_647,
        "bfb6c1dcbe5b76dadb0d26deab6515f6b7bb5572c5a76890e07af205fc7b41af",
    ),
    (
        "src/acfqp/construction_k7_fourth_family_sample_tax_failure_v166.py",
        4_440,
        "2029b512fa54cdb78cbd88118568e6f5b9aea0307d5d05d672ac8d8c374a6fff",
    ),
)


class ConstructionK7FourthFamilyPlanModeSetPreregistrationV167Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FourthFamilyPlanModeSetPreregistrationV167Error(message)


def campaign_config_v167():
    config = fourth_family_plan_mode_set_campaign_config_v167()
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


def _frozen(name: str, *, count: int, digest: str, identity_key: str, identity: str):
    raw = (SOURCE_ROOT / ".tmp/exact-freeze" / name).read_bytes()
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail("V167 frozen V166 predecessor changed")
    return document


def _document():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V167 implementation changed before target outcomes")
        source_facts.append(
            {"relative_path": path, "byte_count": count, "sha256": digest}
        )
    registration = _frozen(
        "v166_fourth_family_sample_tax_preregistration.json",
        count=V166_PREREGISTRATION_BYTE_COUNT,
        digest=V166_PREREGISTRATION_SHA256,
        identity_key="preregistration_id",
        identity=V166_PREREGISTRATION_ID,
    )
    failure = _frozen(
        "v166_fourth_family_sample_tax_failure.json",
        count=V166_FAILURE_BYTE_COUNT,
        digest=V166_FAILURE_SHA256,
        identity_key="failure_id",
        identity=V166_FAILURE_ID,
    )
    if not (
        failure["failed_preregistration_id"] == V166_PREREGISTRATION_ID
        and failure["same_identity_rerun_forbidden"] is True
        and failure["fresh_successor_identity_required"] is True
        and failure["query_or_factor_sample_tax_result_claimed"] is False
        and registration["claim_boundary"]["target_outcomes_accessed"] is False
    ):
        _fail("V167 V166 failure boundary changed")
    config = campaign_config_v167()
    payload = {
        "schema": "acfqp.fourth_family_plan_mode_set_preregistration.v167",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v166_preregistration": {
            "preregistration_id": V166_PREREGISTRATION_ID,
            "byte_count": V166_PREREGISTRATION_BYTE_COUNT,
            "sha256": V166_PREREGISTRATION_SHA256,
        },
        "frozen_v166_failure": {
            "failure_id": V166_FAILURE_ID,
            "byte_count": V166_FAILURE_BYTE_COUNT,
            "sha256": V166_FAILURE_SHA256,
            "same_identity_rerun_forbidden": True,
            "failed_result_not_reclassified_as_success": True,
        },
        "correction": {
            "failed_gate": "OCCURRENCE_WIDE_EXACTLY_ONE_PLAN_RECEIPT_MODE",
            "replacement_gate": "EXACT_REGISTERED_PLAN_RECEIPT_MODE_SET",
            "mixed_mode_interpretation": "TEMPORALLY_DISTINCT_RECEIPTS_NOT_COMPETING_ACTIONS",
            "planner_dynamics_changed": False,
            "execution_policy_changed": False,
            "v109_and_certificate_safety_boundary_changed": False,
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
            for family in TARGET_FAMILIES
        },
        "registered_gate": {
            "fresh_target_identities_fixed_before_target_outcomes": True,
            "v166_failed_identity_preserved_and_not_rerun": True,
            "exactly_two_occurrences_from_each_of_four_families_required": True,
            "single_and_mixed_registered_plan_receipt_sets_admissible": True,
            "all_executed_actions_require_v109_receipts": True,
            "plan_mode_set_is_not_model_planning_or_certificate_authority": True,
            "query_policy_noninferior_everywhere_required": True,
            "every_exact_fallback_zero_regression_required": True,
            "factor_prior_noninferior_everywhere_required": True,
            "factor_prior_strict_aggregate_and_new_family_reduction_required": True,
            "both_arm_receding_planning_and_certificate_local_recovery_required": True,
            "sample_execution_derivation_and_planning_axes_separate": True,
            "strict_ood_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "v167_fourth_family_transfer_observed": False,
            "v166_failed_result_reclassified": False,
            "profitability_classifier_issued": False,
            "query_policy_or_plan_mode_annotation_is_safety_authority": False,
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
        "preregistration_id": domains.extension_content_id_v167(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V167_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FourthFamilyPlanModeSetPreregistrationV167:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_fourth_family_plan_mode_set_preregistration_v167():
    document = _document()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V167 frozen target preregistration changed")
    return FourthFamilyPlanModeSetPreregistrationV167(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v167",
    "freeze_fourth_family_plan_mode_set_preregistration_v167",
)
