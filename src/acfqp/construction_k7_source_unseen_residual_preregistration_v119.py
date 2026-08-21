"""Outcome-free source-unseen higher-order residual preregistration V119."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v119 as domains
from acfqp import construction_k7_fourth_family_inventory_preregistration_v118 as previous
from acfqp.construction_k7_fourth_family_inventory_campaign_v118 import (
    CAMPAIGN_ID as V118_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V118_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_fourth_family_inventory_independent_verifier_v118 import (
    EXPECTED_CANONICAL_SHA256 as V118_VERIFICATION_SHA256,
    VERIFICATION_ID as V118_VERIFICATION_ID,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, dual_budget_config_v119
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("85f3519", "0023b74")
PREREGISTRATION_ID = "4f29a2060a9eaecd4f072d245b7f0dd1af8168b4ae005b268ec3c52510fac929"
EXPECTED_CANONICAL_BYTE_COUNT = 26_779
EXPECTED_CANONICAL_SHA256 = "252330621f8ba9a70903882f83b54cd60238bc3c9f210645d680bb2ba5426e01"
TARGET_OCCURRENCES = ((FAMILY, 1_031_101), (FAMILY, 1_031_102))
TARGET_EPISODE_INDICES = (263, 264, 265)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v119.py",
        1848,
        "d29e57e7b5a2006e01456a00539923fd370a07ac416d527f61c0c6cb645a86bb",
    ),
    (
        "src/acfqp/domains/stochastic_dual_budget_composition.py",
        9736,
        "3c2b51beefa7e5a8692c4e2ca0f378a85b1ede773ad8fc844a6a52e9f252547c",
    ),
    (
        "src/acfqp/generic_dual_budget_adapter_v119.py",
        4178,
        "86034b2ee197ed88693932d5def890403cfb44017ec0e0fa4e76125dfead3345",
    ),
    (
        "src/acfqp/source_unseen_partial_acquisition_v119.py",
        8970,
        "d7226410341dc147355f32a183285ca284ad918d250d2cd3d81998a04bd62c22",
    ),
    (
        "src/acfqp/generic_genesis_authorized_program_branch_sequence_v119.py",
        13790,
        "77c21fe81f7e316ebf80862d948741215b80406fd4fe39606ef282307950f772",
    ),
    (
        "src/acfqp/source_unseen_residual_campaign_core_v119.py",
        11487,
        "3c5a60bff8b885dd605556cebeb2df3de64fdcdf123721693a25f7cf71e5d2cf",
    ),
    (
        "src/acfqp/construction_k7_fourth_family_inventory_preregistration_v118.py",
        11600,
        "8fcb542b1db4c5495a877b714f576d8fc0859c9a0555302d5f8aa50140d642e7",
    ),
    (
        "src/acfqp/construction_k7_fourth_family_inventory_campaign_v118.py",
        4872,
        "f74d45dfaa891e0770d7ad119322fd672ad388935dc3c1ad1c4bb41b6ab4a40b",
    ),
    (
        "src/acfqp/construction_k7_fourth_family_inventory_independent_verifier_v118.py",
        18125,
        "f6ffea83097cd06c6e2fee6ba5bdc97a339eb564b8b89de3cc566b6f7b1e9c61",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7SourceUnseenResidualPreregistrationV119Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SourceUnseenResidualPreregistrationV119Error(message)


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


def campaign_config_v119() -> dict[str, Any]:
    config = copy.deepcopy(dual_budget_config_v119())
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
        "schema": "acfqp.source_unseen_residual_preregistration.v119",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v118_campaign_id": V118_CAMPAIGN_ID,
            "v118_campaign_sha256": V118_CAMPAIGN_SHA256,
            "v118_verification_id": V118_VERIFICATION_ID,
            "v118_verification_sha256": V118_VERIFICATION_SHA256,
            "v118_registered_gate_passed": True,
            "v118_identity_and_bytes_retained": True,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v119_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V119),
            "frozen_before_any_registered_v119_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v119()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_seed": 1_031_001,
            "development_episode_indices": [260, 261, 262],
            "development_identities_excluded_from_registered_gate": True,
        },
        "construction_contract": {
            "same_observation_derived_layout_and_partial_factor_synthesizer": True,
            "target_domain_source_unavailable_to_synthesizer": True,
            "target_domain_source_absent_from_factor_library_source_closure": True,
            "higher_order_residual_must_remain_explicitly_unknown": True,
            "strict_no_prior_complete_model_attempt_uses_same_raw_prefix_once": True,
            "strict_control_outcome_retained_without_gate_selection": True,
            "same_v113_incremental_model_and_certificate_engine": True,
            "same_epoch_zero_transition_cache_reuse_requires_exact_genesis_identity": True,
            "cross_epoch_cache_reuse_requires_epoch_authorization_chain": True,
            "all_registered_episodes_must_succeed": True,
            "compiled_partial_model_only_orders_actions": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "development_evidence_retained_before_registration": {
            "partial_acquisition_labels": 73,
            "compiled_factor_assignment_count": 8,
            "unknown_residual_target_column_count": 2,
            "strict_control_outcome": "NO_COMPLETE_CANDIDATE_WITHIN_FROZEN_GRAMMAR",
            "successful_episode_count": 3,
            "certificate_local_labels": 48,
            "actual_planning_compute_events": 18_988,
            "matched_uncached_planning_compute_events": 21_828,
            "planning_compute_events_avoided": 2_840,
            "same_epoch_genesis_authorized_cache_hits": 3,
            "unfavourable_results_would_remain_visible": True,
        },
        "sample_tax_contract": {
            "partial_prior_labels_reported": True,
            "strict_control_matched_prefix_labels_reported": True,
            "strict_control_is_not_an_adaptive_no_prior_sample_baseline": True,
            "sample_efficiency_sign_not_used_for_gate": True,
            "sample_efficiency_improvement_claimed": False,
            "offline_factor_library_labels_not_recharged": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "source_unseen_higher_order_residual_family_present": True,
            "every_occurrence_retains_unknown_residual_and_completes_planning": True,
            "same_epoch_genesis_authorization_observed": True,
            "strict_control_outcomes_retained_without_selection": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "maximum_acquisition_labels": 320,
            "strict_complete_model_attempts_per_occurrence": 1,
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
            "strict_control_compute_not_charged_to_partial_planning_arm": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v119_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_source_unseen_partial_world_model_pipeline_verified": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "strict_complete_model_required_for_planning": False,
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
        "preregistration_id": domains.extension_content_id_v119(
            domains.CONSTRUCTION_K7_SOURCE_UNSEEN_RESIDUAL_PREREGISTRATION_V119_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SourceUnseenResidualPreregistrationV119:
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
            or domains.extension_content_id_v119(
                domains.CONSTRUCTION_K7_SOURCE_UNSEEN_RESIDUAL_PREREGISTRATION_V119_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V119 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: SourceUnseenResidualPreregistrationV119 | None = None


def freeze_source_unseen_residual_preregistration_v119() -> SourceUnseenResidualPreregistrationV119:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V119 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V119 frozen preregistration changed")
        _CACHE = SourceUnseenResidualPreregistrationV119(_ISSUER, raw, identity)
    return _CACHE


def verify_source_unseen_residual_preregistration_v119(
    value: Any,
) -> SourceUnseenResidualPreregistrationV119:
    if type(value) is not SourceUnseenResidualPreregistrationV119:
        _fail("V119 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_source_unseen_residual_preregistration_v119()
    if value is not expected:
        _fail("V119 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v119",
    "freeze_source_unseen_residual_preregistration_v119",
    "verify_source_unseen_residual_preregistration_v119",
)
