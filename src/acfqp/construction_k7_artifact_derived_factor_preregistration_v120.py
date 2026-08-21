"""Outcome-free preregistration for artifact-derived factor transfer V120."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v120 as domains
from acfqp import construction_k7_source_unseen_residual_preregistration_v119 as previous
from acfqp.construction_k7_source_unseen_residual_campaign_v119 import (
    CAMPAIGN_ID as V119_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V119_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V119_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_source_unseen_residual_independent_verifier_v119 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V119_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V119_VERIFICATION_SHA256,
    VERIFICATION_ID as V119_VERIFICATION_ID,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    SOURCE_CAMPAIGN_SPECS,
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, dual_budget_config_v119
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = (
    "de9ffd14a93ef515f030bb559d0ecc726ad7650c",
    "7744296ac2f172ac9bb1dba3b505377676a7c63a",
)
PREREGISTRATION_ID = "e381fffe2276be471c7064e8642e7bf583910b4e7ff2d2897e2d3d9bdd3a6596"
EXPECTED_CANONICAL_BYTE_COUNT = 45_262
EXPECTED_CANONICAL_SHA256 = "66c55d3e8fc91d14abc2d1f0815c536f0bdefc28593cc34cd957b11fef5c03fe"
EXPECTED_FACTOR_LIBRARY_ID = (
    "352084adc6c9dec68cb5b63976acb170aa4e02ed5004c89ebe8cd22d08e6b68a"
)
TARGET_OCCURRENCES = ((FAMILY, 1_032_101), (FAMILY, 1_032_102))
TARGET_EPISODE_INDICES = (269, 270, 271)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v120.py",
        1826,
        "2ba6677065041ce28aca79a71dc915e482dee516116b890ac7bfd7f9f5b65f29",
    ),
    (
        "src/acfqp/generic_artifact_derived_factor_projection_v120.py",
        10749,
        "eb56b0f7803554fdffc440de12dd7fecddd970fcc7e8cccfea2556b1d801c49a",
    ),
    (
        "src/acfqp/artifact_derived_partial_acquisition_v120.py",
        10345,
        "7b1c1d729b3a1cc1fe1ae46e605eff77947e8e1ba699223954420aafde31762a",
    ),
    (
        "src/acfqp/artifact_derived_factor_campaign_core_v120.py",
        12882,
        "48cbbb1b260631358b51ec444546eda35663b49db3865f9297e78f26b1b77e2d",
    ),
    (
        "src/acfqp/construction_k7_source_unseen_residual_preregistration_v119.py",
        12701,
        "f2151b6a7af6c97fc762240593fe454b0ba87bb0505012af170350507d652867",
    ),
    (
        "src/acfqp/construction_k7_source_unseen_residual_campaign_v119.py",
        4798,
        "45a35c1ef36c2330f4113a1f894e37b5a4c26f996174be9d6d7907bf87434949",
    ),
    (
        "src/acfqp/construction_k7_source_unseen_residual_independent_verifier_v119.py",
        24908,
        "a9f11c4bce04c2729f057cf4e6650f0a8addf47a304e3a442267bd261dd68c5d",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7ArtifactDerivedFactorPreregistrationV120Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ArtifactDerivedFactorPreregistrationV120Error(message)


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


def campaign_config_v120() -> dict[str, Any]:
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


def _document(source_campaign_bytes: Mapping[str, bytes]) -> dict[str, Any]:
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    if library["factor_library_id"] != EXPECTED_FACTOR_LIBRARY_ID:
        _fail("V120 artifact-derived factor library identity changed")
    payload = {
        "schema": "acfqp.artifact_derived_factor_preregistration.v120",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v119_campaign_id": V119_CAMPAIGN_ID,
            "v119_campaign_byte_count": V119_CAMPAIGN_BYTE_COUNT,
            "v119_campaign_sha256": V119_CAMPAIGN_SHA256,
            "v119_verification_id": V119_VERIFICATION_ID,
            "v119_verification_byte_count": V119_VERIFICATION_BYTE_COUNT,
            "v119_verification_sha256": V119_VERIFICATION_SHA256,
            "v119_registered_gate_passed": True,
            "v119_identity_and_bytes_retained": True,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "artifact_source_campaign_specs": copy.deepcopy(SOURCE_CAMPAIGN_SPECS),
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v120_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V120),
            "frozen_before_any_registered_v120_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v120()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_seed": 1_032_001,
            "development_episode_indices": [266, 267, 268],
            "development_identities_excluded_from_registered_gate": True,
        },
        "construction_contract": {
            "factor_templates_derived_from_frozen_candidate_documents": True,
            "hand_written_factor_template_count": 0,
            "minimum_distinct_schema_pair_support": 2,
            "target_slot_inventory_supplied": False,
            "semantic_family_names_used_for_subprogram_selection": False,
            "same_v15_observation_bound_partial_synthesizer": True,
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
            "artifact_factor_library_id": library["factor_library_id"],
            "derived_subprogram_count": len(library["derived_subprograms"]),
            "historical_candidate_document_count": library[
                "candidate_document_count"
            ],
            "partial_acquisition_labels": 34,
            "compiled_factor_assignment_count": 8,
            "unknown_residual_target_column_count": 2,
            "strict_control_outcome": "NO_COMPLETE_CANDIDATE_WITHIN_FROZEN_GRAMMAR",
            "successful_episode_count": 3,
            "certificate_local_labels": 54,
            "actual_planning_compute_events": 13_476,
            "matched_uncached_planning_compute_events": 14_988,
            "planning_compute_events_avoided": 1_512,
            "same_epoch_genesis_authorized_cache_hits": 1,
            "unfavourable_results_would_remain_visible": True,
        },
        "sample_tax_contract": {
            "historical_candidate_document_count_reported": True,
            "partial_prior_labels_reported": True,
            "strict_control_matched_prefix_labels_reported": True,
            "strict_control_is_not_an_adaptive_no_prior_sample_baseline": True,
            "sample_efficiency_sign_not_used_for_gate": True,
            "sample_efficiency_improvement_claimed": False,
            "historical_artifact_labels_not_recharged_to_target": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "artifact_factor_library_reconstructed_exactly": True,
            "hand_written_factor_template_count_zero": True,
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
            "sample_labels_execution_steps_derivation_planning_dependency_and_library_derivation_separate": True,
            "strict_control_compute_not_charged_to_partial_planning_arm": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v120_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_artifact_derived_partial_world_model_pipeline_verified": False,
            "target_family_present_in_historical_artifact_inventory": True,
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
        "preregistration_id": domains.extension_content_id_v120(
            domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_PREREGISTRATION_V120_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ArtifactDerivedFactorPreregistrationV120:
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
            or domains.extension_content_id_v120(
                domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_PREREGISTRATION_V120_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V120 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: ArtifactDerivedFactorPreregistrationV120 | None = None


def freeze_artifact_derived_factor_preregistration_v120(
    source_campaign_bytes: Mapping[str, bytes],
) -> ArtifactDerivedFactorPreregistrationV120:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V120 preregistered source closure changed")
        document = _document(source_campaign_bytes)
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V120 frozen preregistration changed")
        _CACHE = ArtifactDerivedFactorPreregistrationV120(_ISSUER, raw, identity)
    return _CACHE


def verify_artifact_derived_factor_preregistration_v120(
    value: Any,
    source_campaign_bytes: Mapping[str, bytes],
) -> ArtifactDerivedFactorPreregistrationV120:
    if type(value) is not ArtifactDerivedFactorPreregistrationV120:
        _fail("V120 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_artifact_derived_factor_preregistration_v120(
        source_campaign_bytes
    )
    if value is not expected:
        _fail("V120 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v120",
    "freeze_artifact_derived_factor_preregistration_v120",
    "verify_artifact_derived_factor_preregistration_v120",
)
