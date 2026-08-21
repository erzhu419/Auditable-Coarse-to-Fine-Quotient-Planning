"""Outcome-free preregistration for generic artifact-subprogram binding V121."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_artifact_derived_factor_preregistration_v120 as previous
from acfqp import construction_k7_domain_registry_extension_v121 as domains
from acfqp.construction_k7_artifact_derived_factor_campaign_v120 import (
    CAMPAIGN_ID as V120_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V120_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V120_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_artifact_derived_factor_independent_verifier_v120 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V120_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V120_VERIFICATION_SHA256,
    VERIFICATION_ID as V120_VERIFICATION_ID,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, dual_budget_config_v119
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = (
    "35fc0037fa72aa372c3e45133667970989fd5285",
)
PREREGISTRATION_ID = "3967cb733cd31c1c9afb8596500319634d7b4a6fd57ab402a8014b215b510faa"
EXPECTED_CANONICAL_BYTE_COUNT = 45_956
EXPECTED_CANONICAL_SHA256 = "d15efcf4a85e268ea48e2be6e7cf1fd1b0d953a0153f22fc6d85c00f8f503ef2"
EXPECTED_FACTOR_LIBRARY_ID = previous.EXPECTED_FACTOR_LIBRARY_ID
TARGET_OCCURRENCES = ((FAMILY, 1_033_101), (FAMILY, 1_033_102))
TARGET_EPISODE_INDICES = (275, 276, 277)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v121.py",
        1775,
        "75f226c552a28a6f1a37d15a42850eacaf1ca30375c8a6b9cc737cf023ad2757",
    ),
    (
        "src/acfqp/generic_artifact_subprogram_instantiator_v121.py",
        17117,
        "517c327fffd654e6cefef5469533146d890f9f19ab031c3d63a4be253bcbd994",
    ),
    (
        "src/acfqp/generic_artifact_subprogram_acquisition_v121.py",
        10120,
        "a174c61411dab5794650df71100f601fb89e75a58b9f9f9fcece332f8bcae830",
    ),
    (
        "src/acfqp/generic_artifact_subprogram_campaign_core_v121.py",
        13671,
        "606b5dc400975579a1eaccb1442458f87b2e564089a2425c6f6d50406c347796",
    ),
    (
        "src/acfqp/construction_k7_artifact_derived_factor_preregistration_v120.py",
        14207,
        "0f1a1364d0c7e1154fdb91c2573666af38eba4a350b9c3d2f28fd149d33c70b6",
    ),
    (
        "src/acfqp/construction_k7_artifact_derived_factor_campaign_v120.py",
        5161,
        "3d9e80f9b0204be4edd636e1f1bcec36ff6f5f56e3f2832dcb922aa26d0b7fb5",
    ),
    (
        "src/acfqp/construction_k7_artifact_derived_factor_independent_verifier_v120.py",
        31681,
        "9e0c95d2bbaaccccdcf8f5792347de74d6e038cb44ed9a7e5d798e70685b108c",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7GenericArtifactSubprogramPreregistrationV121Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericArtifactSubprogramPreregistrationV121Error(message)


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


def campaign_config_v121() -> dict[str, Any]:
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
        _fail("V121 artifact factor library identity changed")
    payload = {
        "schema": "acfqp.generic_artifact_subprogram_preregistration.v121",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v120_campaign_id": V120_CAMPAIGN_ID,
            "v120_campaign_byte_count": V120_CAMPAIGN_BYTE_COUNT,
            "v120_campaign_sha256": V120_CAMPAIGN_SHA256,
            "v120_verification_id": V120_VERIFICATION_ID,
            "v120_verification_byte_count": V120_VERIFICATION_BYTE_COUNT,
            "v120_verification_sha256": V120_VERIFICATION_SHA256,
            "v120_registered_gate_passed": True,
            "v120_identity_and_bytes_retained": True,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v121_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V121),
            "frozen_before_any_registered_v121_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v121()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_seed_inventory": [
                1_033_001,
                1_033_002,
                1_033_003,
                1_033_004,
                1_033_005,
                1_033_006,
                1_033_007,
                1_033_008,
                1_033_009,
            ],
            "selected_development_seed": 1_033_002,
            "development_episode_indices": [272, 273, 274],
            "development_identities_excluded_from_registered_gate": True,
        },
        "construction_contract": {
            "artifact_subprograms_bound_by_generic_symbol_inventory": True,
            "typed_opcode_registry_interpreted_recursively": True,
            "hand_written_normalized_expression_shape_cases": 0,
            "arbitrary_action_symbol_count_supported_by_cartesian_binding": True,
            "state_and_action_dependencies_derived_from_bound_expression": True,
            "same_artifact_derived_factor_library_as_v120": True,
            "same_v15_candidate_carrier_for_frozen_downstream_compatibility": True,
            "legacy_shape_specific_planner_execution_adapter_present": True,
            "generic_planner_execution_adapter_verified": False,
            "higher_order_residual_must_remain_explicitly_unknown": True,
            "strict_no_prior_complete_model_attempt_uses_same_raw_prefix_once": True,
            "strict_control_outcome_retained_without_gate_selection": True,
            "all_registered_episodes_must_succeed": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "development_evidence_retained_before_registration": {
            "failed_development_seed_count": 2,
            "failed_development_seeds": [1_033_001, 1_033_003],
            "failure_kind": "NO_STOP_BEFORE_FROZEN_320_LABEL_CAP",
            "selected_partial_acquisition_labels": 33,
            "compiled_factor_assignment_count": 8,
            "unknown_residual_target_column_count": 2,
            "strict_control_outcome": "NO_COMPLETE_CANDIDATE_WITHIN_FROZEN_GRAMMAR",
            "successful_episode_count": 3,
            "certificate_local_labels": 47,
            "actual_planning_compute_events": 18_328,
            "matched_uncached_planning_compute_events": 19_752,
            "planning_compute_events_avoided": 1_424,
            "generic_binding_candidate_evaluations": 36,
            "unfavourable_results_retained": True,
        },
        "sample_tax_contract": {
            "partial_prior_labels_reported": True,
            "strict_control_matched_prefix_labels_reported": True,
            "generic_binding_candidate_evaluations_reported_separately": True,
            "strict_control_is_not_an_adaptive_no_prior_sample_baseline": True,
            "sample_efficiency_sign_not_used_for_gate": True,
            "sample_efficiency_improvement_claimed": False,
            "historical_artifact_labels_not_recharged_to_target": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "generic_symbol_binding_used_in_every_occurrence": True,
            "hand_written_expression_shape_cases_zero": True,
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
            "sample_labels_execution_steps_binding_derivation_planning_dependency_and_library_derivation_separate": True,
            "strict_control_compute_not_charged_to_partial_planning_arm": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v121_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_generic_artifact_subprogram_partial_pipeline_verified": False,
            "legacy_shape_specific_planner_execution_adapter_present": True,
            "generic_planner_execution_adapter_verified": False,
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
        "preregistration_id": domains.extension_content_id_v121(
            domains.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_PREREGISTRATION_V121_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericArtifactSubprogramPreregistrationV121:
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
            or domains.extension_content_id_v121(
                domains.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_PREREGISTRATION_V121_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V121 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: GenericArtifactSubprogramPreregistrationV121 | None = None


def freeze_generic_artifact_subprogram_preregistration_v121(
    source_campaign_bytes: Mapping[str, bytes],
) -> GenericArtifactSubprogramPreregistrationV121:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V121 preregistered source closure changed")
        document = _document(source_campaign_bytes)
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V121 frozen preregistration changed")
        _CACHE = GenericArtifactSubprogramPreregistrationV121(_ISSUER, raw, identity)
    return _CACHE


def verify_generic_artifact_subprogram_preregistration_v121(
    value: Any,
    source_campaign_bytes: Mapping[str, bytes],
) -> GenericArtifactSubprogramPreregistrationV121:
    if type(value) is not GenericArtifactSubprogramPreregistrationV121:
        _fail("V121 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_generic_artifact_subprogram_preregistration_v121(
        source_campaign_bytes
    )
    if value is not expected:
        _fail("V121 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v121",
    "freeze_generic_artifact_subprogram_preregistration_v121",
    "verify_generic_artifact_subprogram_preregistration_v121",
)
