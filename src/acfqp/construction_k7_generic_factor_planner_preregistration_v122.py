"""Outcome-free preregistration for the V122 generic planner campaign."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v122 as domains
from acfqp import construction_k7_generic_subprogram_preregistration_v121r1 as previous
from acfqp.construction_k7_generic_subprogram_campaign_v121r1 import (
    CAMPAIGN_ID as V121R1_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V121R1_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V121R1_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_generic_subprogram_independent_verifier_v121r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V121R1_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V121R1_VERIFICATION_SHA256,
    VERIFICATION_ID as V121R1_VERIFICATION_ID,
    freeze_generic_subprogram_verification_v121r1,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, dual_budget_config_v119
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = (
    "2d0ad207a936fd6d45aa2ae298feae0ddcad4ad9",
    "c6ee7d16d686dc7cd83f697eac23210152ebc6c7",
)
V121R1_VERIFICATION_COMMIT = "62230bd8f0b5351c3275b56eb0d62e0786db506b"
PREREGISTRATION_ID = "37ad2738275cad9469c815c383f9951337697f619128581b6403424208fa5c88"
EXPECTED_CANONICAL_BYTE_COUNT = 47_551
EXPECTED_CANONICAL_SHA256 = "47bcc9ab044b6bf072df0be1a86c75d5f1e63b7654e3cf6b740c645a81adfb8f"
TARGET_OCCURRENCES = ((FAMILY, 1_035_101), (FAMILY, 1_035_102))
TARGET_EPISODE_INDICES = (281, 282, 283)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v122.py",
        1_638,
        "8e96a03bb52599b30a0309a04b244f75db86ad6e2983e4179ef53ad9aaede62e",
    ),
    (
        "src/acfqp/generic_compiled_factor_planner_v122.py",
        18_498,
        "bb94cc4fa211a114de404b1cf83a5d84329882875ded27b16b214194be89d36f",
    ),
    (
        "src/acfqp/generic_factor_planner_sequence_v122.py",
        14_369,
        "51347f062b38570182b2b287017109203ceeb0c3dccddd3a937f5a47ea67ecdf",
    ),
    (
        "src/acfqp/generic_factor_planner_campaign_core_v122.py",
        13_836,
        "f81688759610ccf3fe13ead34615dbf085164b6044b2de110f3ebaf58dfccee1",
    ),
    (
        "src/acfqp/construction_k7_generic_subprogram_campaign_v121r1.py",
        4_291,
        "7957b83e98aa90fbaf3db9f5b57f506872a3b106f37b73303d70659abc02913b",
    ),
    (
        "src/acfqp/construction_k7_generic_subprogram_independent_verifier_v121r1.py",
        31_087,
        "2ea0060a9b39bd2c466220d34c53f6060bf92c6354727dadac477c990bccf5df",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7GenericFactorPlannerPreregistrationV122Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericFactorPlannerPreregistrationV122Error(message)


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path,
            "byte_count": len((SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256((SOURCE_ROOT / path).read_bytes()).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v122() -> dict[str, Any]:
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


def _document(
    source_campaign_bytes: Mapping[str, bytes],
    v121r1_campaign_raw: bytes,
    v121r1_verification_raw: bytes,
) -> dict[str, Any]:
    campaign = loads_canonical_json(v121r1_campaign_raw)
    verification = loads_canonical_json(v121r1_verification_raw)
    if (
        canonical_json_bytes(campaign) != v121r1_campaign_raw
        or len(v121r1_campaign_raw) != V121R1_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v121r1_campaign_raw).hexdigest() != V121R1_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V121R1_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or canonical_json_bytes(verification) != v121r1_verification_raw
        or len(v121r1_verification_raw) != V121R1_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v121r1_verification_raw).hexdigest()
        != V121R1_VERIFICATION_SHA256
        or verification.get("verification_id") != V121R1_VERIFICATION_ID
        or verification.get("registered_gate_independently_verified") is not True
        or freeze_generic_subprogram_verification_v121r1(
            v121r1_campaign_raw,
            (SOURCE_ROOT / ".tmp/exact-freeze/v121_generic_artifact_subprogram_campaign.json").read_bytes(),
            dict(source_campaign_bytes),
        )
        != v121r1_verification_raw
    ):
        _fail("V122 frozen V121r1 predecessor changed")
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    payload = {
        "schema": "acfqp.generic_factor_planner_preregistration.v122",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v121r1_campaign_id": V121R1_CAMPAIGN_ID,
            "v121r1_campaign_byte_count": V121R1_CAMPAIGN_BYTE_COUNT,
            "v121r1_campaign_sha256": V121R1_CAMPAIGN_SHA256,
            "v121r1_verification_id": V121R1_VERIFICATION_ID,
            "v121r1_verification_byte_count": V121R1_VERIFICATION_BYTE_COUNT,
            "v121r1_verification_sha256": V121R1_VERIFICATION_SHA256,
            "v121r1_verification_commit": V121R1_VERIFICATION_COMMIT,
            "v121r1_identity_and_bytes_retained": True,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v122_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V122),
            "frozen_before_any_registered_v122_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v122()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_seed": 1_033_002,
            "development_episode_indices": [272, 273, 274],
            "development_identity_excluded_from_registered_gate": True,
        },
        "construction_contract": {
            "generic_typed_opcode_interpreter_executes_every_new_program_successor": True,
            "terminal_rules_derived_from_anonymous_dependencies_and_projected_deltas": True,
            "affine_translation_lower_bound_derived_by_generic_abstract_interpretation": True,
            "unsupported_expression_fragments_receive_zero_lower_bound": True,
            "legacy_shape_specific_planner_execution_adapter_present": False,
            "legacy_shape_specific_model_builder_retained_only_as_matched_control": True,
            "unseen_nested_expression_outside_v15_shape_dispatch_must_execute": True,
            "generic_planner_fallback_must_be_exercised": True,
            "every_compiled_projected_edge_must_replay_through_generic_interpreter": True,
            "same_epoch_cache_hit_is_diagnostic_not_gate": True,
            "higher_order_residual_must_remain_explicitly_unknown": True,
            "all_registered_episodes_must_succeed": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "development_evidence_retained_before_registration": {
            "partial_acquisition_labels": 33,
            "certificate_local_labels": 47,
            "lifetime_target_labels": 80,
            "execution_steps": 18,
            "generic_planning_compute_events": 18_328,
            "matched_uncached_planning_compute_events": 19_752,
            "planning_compute_events_avoided": 1_424,
            "generic_projected_edge_support_checks": 2_944,
            "generic_terminal_rule_checks": 24,
            "direct_generic_factor_program_plan_count": 32,
            "memoized_generic_planner_source_count": 1,
            "strict_control_outcome": "NO_COMPLETE_CANDIDATE_WITHIN_FROZEN_GRAMMAR",
            "all_three_episodes_succeeded": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "generic_planner_used_in_every_occurrence": True,
            "legacy_shape_specific_planner_adapter_absent_in_every_occurrence": True,
            "all_receding_episodes_succeed": True,
            "every_occurrence_retains_unknown_residual": True,
            "strict_control_outcomes_retained_without_gate_selection": True,
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
            "sample_labels_execution_steps_binding_derivation_planning_dependency_and_generic_execution_checks_separate": True,
            "same_epoch_cache_hits_are_diagnostic_not_gate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v122_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_generic_factor_planner_pipeline_verified": False,
            "legacy_shape_specific_planner_execution_adapter_present": False,
            "generic_planner_execution_adapter_verified": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "sample_efficiency_improvement_claimed": False,
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
        "preregistration_id": domains.extension_content_id_v122(
            domains.CONSTRUCTION_K7_GENERIC_FACTOR_PLANNER_PREREGISTRATION_V122_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericFactorPlannerPreregistrationV122:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v122(
                domains.CONSTRUCTION_K7_GENERIC_FACTOR_PLANNER_PREREGISTRATION_V122_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V122 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: GenericFactorPlannerPreregistrationV122 | None = None


def freeze_generic_factor_planner_preregistration_v122(
    source_campaign_bytes: Mapping[str, bytes],
    v121r1_campaign_raw: bytes,
    v121r1_verification_raw: bytes,
) -> GenericFactorPlannerPreregistrationV122:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V122 preregistered source closure changed")
        document = _document(
            source_campaign_bytes, v121r1_campaign_raw, v121r1_verification_raw
        )
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V122 frozen preregistration changed")
        _CACHE = GenericFactorPlannerPreregistrationV122(_ISSUER, raw, identity)
    return _CACHE


def verify_generic_factor_planner_preregistration_v122(
    value: Any,
    source_campaign_bytes: Mapping[str, bytes],
    v121r1_campaign_raw: bytes,
    v121r1_verification_raw: bytes,
) -> GenericFactorPlannerPreregistrationV122:
    if type(value) is not GenericFactorPlannerPreregistrationV122:
        _fail("V122 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_generic_factor_planner_preregistration_v122(
        source_campaign_bytes, v121r1_campaign_raw, v121r1_verification_raw
    )
    if value is not expected:
        _fail("V122 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v122",
    "freeze_generic_factor_planner_preregistration_v122",
    "verify_generic_factor_planner_preregistration_v122",
)
