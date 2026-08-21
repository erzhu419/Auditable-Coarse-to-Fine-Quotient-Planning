"""Outcome-free fourth-family inventory transfer preregistration V118."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v118 as domains
from acfqp import construction_k7_dependency_derived_program_branch_preregistration_v117 as previous
from acfqp.construction_k7_dependency_derived_program_branch_campaign_v117 import (
    CAMPAIGN_ID as V117_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V117_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_dependency_derived_program_branch_independent_verifier_v117 import (
    EXPECTED_CANONICAL_SHA256 as V117_VERIFICATION_SHA256,
    VERIFICATION_ID as V117_VERIFICATION_ID,
)
from acfqp.generic_inventory_assembly_adapter_v118 import (
    FAMILY,
    inventory_assembly_config_v118,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("446efd9", "00a1c3f")
PREREGISTRATION_ID = "6bfe911dc767829058fe00b5887ce6394aeea40baec7cbfbedb3c56ad97affa7"
EXPECTED_CANONICAL_BYTE_COUNT = 24_143
EXPECTED_CANONICAL_SHA256 = "58af74a41d049eaf374be86ff92877341cbda9c2d6b340e96e0f4c2923f028f6"
TARGET_OCCURRENCES = ((FAMILY, 1_030_101), (FAMILY, 1_030_102))
TARGET_EPISODE_INDICES = (257, 258, 259)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v118.py",
        1558,
        "9b11be3852fe969f3e47e02e0c17080d8f1c657ab0ddb5cb9dc8cff6ce370370",
    ),
    (
        "src/acfqp/generic_inventory_assembly_adapter_v118.py",
        4169,
        "26f05732ef1afc064ab64f3a7bfab9ed33610e6a0852a2883adb133560835d74",
    ),
    (
        "src/acfqp/fourth_family_inventory_campaign_core_v118.py",
        11110,
        "354e087ce905a9f96ac19ac6308f9fc626194092835cab6ef7b7a140a886185c",
    ),
    (
        "src/acfqp/domains/stochastic_inventory_assembly.py",
        9160,
        "c531987d511e1e38eb56632084f09aa7c40cef73fed139a5474e052192c7811b",
    ),
    (
        "src/acfqp/construction_k7_dependency_derived_program_branch_preregistration_v117.py",
        11694,
        "a7a4966a1ac3dffd48d97005375e2bcdb4d11c0720f95f0b05c7e18701be0403",
    ),
    (
        "src/acfqp/construction_k7_dependency_derived_program_branch_campaign_v117.py",
        4972,
        "8bb4b67652d77bb8766adf3859143b5f63e68a5370bdc0d576995db23c285fda",
    ),
    (
        "src/acfqp/construction_k7_dependency_derived_program_branch_independent_verifier_v117.py",
        23788,
        "4ee4caa5e7a667d66944d34d1a37c10def49e0381d05fb86553109581e476bde",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7FourthFamilyInventoryPreregistrationV118Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FourthFamilyInventoryPreregistrationV118Error(message)


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path,
            "byte_count": len((SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256((SOURCE_ROOT / path).read_bytes()).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v118() -> dict[str, Any]:
    config = copy.deepcopy(inventory_assembly_config_v118())
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


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.fourth_family_inventory_preregistration.v118",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v117_campaign_id": V117_CAMPAIGN_ID,
            "v117_campaign_sha256": V117_CAMPAIGN_SHA256,
            "v117_verification_id": V117_VERIFICATION_ID,
            "v117_verification_sha256": V117_VERIFICATION_SHA256,
            "v117_registered_gate_passed": True,
            "v117_passed_occurrence_count": 3,
            "v117_target_labels": 166,
            "v117_planning_compute_events": 92_264,
            "v117_planning_compute_events_avoided_against_uncached": 22_512,
            "v117_identity_and_bytes_retained": True,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v118_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V118),
            "frozen_before_any_registered_v118_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v118()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_family_absent_from_v117_three_family_campaign": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "same_v59_observation_derived_partial_candidate_synthesizer": True,
            "same_v117_dependency_derived_cache_retention_and_v113_planner": True,
            "matched_prior_and_no_prior_arms_use_same_witness_blind_query_order": True,
            "prior_on_candidate_drives_receding_abstract_planning": True,
            "matched_v116_sequence_must_be_byte_exact": True,
            "all_registered_episodes_must_succeed": True,
            "compiled_model_cache_and_receipt_only_order_actions": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "sample_tax_contract": {
            "prior_on_and_strict_no_prior_labels_reported_separately": True,
            "prior_minus_no_prior_sign_not_used_for_gate": True,
            "development_seed_prior_minus_no_prior_labels": 1,
            "unfavourable_development_result_retained": True,
            "sample_efficiency_improvement_claimed": False,
            "factor_library_contains_historical_related_schema_sources": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "fresh_inventory_family_present": True,
            "every_occurrence_completes_receding_abstract_planning": True,
            "every_occurrence_matches_dependency_guarded_and_v116_sequences": True,
            "sample_tax_sign_excluded_and_reported_without_selection": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "maximum_acquisition_labels_per_arm": 240,
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_factor_library_labels_not_recharged": True,
            "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
            "matched_no_prior_and_v116_compute_not_charged_to_target_arm": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v118_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_fourth_family_abstract_world_model_pipeline_verified": False,
            "factor_library_contains_historical_related_schema_sources": True,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "compiled_model_cache_or_receipt_used_as_safety_authority": False,
            "global_lumpability_claimed": False,
            "complete_ground_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v118(
            domains.CONSTRUCTION_K7_FOURTH_FAMILY_INVENTORY_PREREGISTRATION_V118_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FourthFamilyInventoryPreregistrationV118:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v118(
                domains.CONSTRUCTION_K7_FOURTH_FAMILY_INVENTORY_PREREGISTRATION_V118_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V118 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: FourthFamilyInventoryPreregistrationV118 | None = None


def freeze_fourth_family_inventory_preregistration_v118() -> FourthFamilyInventoryPreregistrationV118:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V118 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V118 frozen preregistration changed")
        _CACHE = FourthFamilyInventoryPreregistrationV118(_ISSUER, raw, identity)
    return _CACHE


def verify_fourth_family_inventory_preregistration_v118(
    value: Any,
) -> FourthFamilyInventoryPreregistrationV118:
    if type(value) is not FourthFamilyInventoryPreregistrationV118:
        _fail("V118 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_fourth_family_inventory_preregistration_v118()
    if value is not expected:
        _fail("V118 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v118",
    "freeze_fourth_family_inventory_preregistration_v118",
    "verify_fourth_family_inventory_preregistration_v118",
)
