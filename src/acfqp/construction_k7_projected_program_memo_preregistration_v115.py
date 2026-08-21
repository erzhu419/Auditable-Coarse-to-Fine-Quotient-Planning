"""Outcome-free preregistration for projected program memoization V115."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v115 as domains
from acfqp import construction_k7_three_family_incremental_successor_preregistration_v114 as previous
from acfqp.construction_k7_three_family_incremental_successor_campaign_v114 import (
    CAMPAIGN_ID as V114_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V114_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_three_family_incremental_successor_independent_verifier_v114 import (
    EXPECTED_CANONICAL_SHA256 as V114_VERIFICATION_SHA256,
    VERIFICATION_ID as V114_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("440f8e5", "ab9820d")
PREREGISTRATION_ID = "6834b8be1244a74e9e4a5bc0e6ee1d9c881b167fd8b53e116be8744fa8972513"
EXPECTED_CANONICAL_BYTE_COUNT = 20_912
EXPECTED_CANONICAL_SHA256 = (
    "37b7ee1160d37a7ae49fb7df9a82a975be441415edce16a653e4e1641ced7dab"
)
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_027_101),
    ("COUPLED_EXCHANGE", 1_027_201),
    ("MAINTENANCE_CASCADE", 1_027_301),
)
TARGET_EPISODE_INDICES = (241, 242, 243)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 3
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "COUPLED_EXCHANGE",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v115.py",
        1699,
        "c20d8acc183a4fe20d95c067f829338c9247c62a0211e960f610199ce51b8f3b",
    ),
    (
        "src/acfqp/generic_projected_program_memo_sequence_v115.py",
        23771,
        "4c7d0c25a585f121d7e17fffd5ca6804e59371e094435a1460fd3114152d84ae",
    ),
    (
        "src/acfqp/projected_program_memo_campaign_core_v115.py",
        12626,
        "6a9a08e29cabbfde29823ad8ff2da892741bbb731688ecafdbedbc0e82903bc8",
    ),
    (
        "src/acfqp/construction_k7_three_family_incremental_successor_preregistration_v114.py",
        11813,
        "06a8751959858b7852c2d11e74a5eda5c8afb0e99c0e06cf02e7ebf05324739a",
    ),
    (
        "src/acfqp/construction_k7_three_family_incremental_successor_campaign_v114.py",
        4939,
        "1427b58ffdebb54f71468e492d520b0f14a4ddd5f96a1b0cc73016b90a106f61",
    ),
    (
        "src/acfqp/construction_k7_three_family_incremental_successor_independent_verifier_v114.py",
        14974,
        "b6da1cc648889b1ddc0b4659f29fbd06b632ccc8767bfba2a82b14b3fb8eac46",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7ProjectedProgramMemoPreregistrationV115Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedProgramMemoPreregistrationV115Error(message)


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


def campaign_config_v115() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v114())
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        required_target_families=REQUIRED_TARGET_FAMILIES,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.projected_program_memo_preregistration.v115",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v114_campaign_id": V114_CAMPAIGN_ID,
            "v114_campaign_sha256": V114_CAMPAIGN_SHA256,
            "v114_verification_id": V114_VERIFICATION_ID,
            "v114_verification_sha256": V114_VERIFICATION_SHA256,
            "v114_registered_gate_passed": True,
            "v114_passed_occurrence_count": 6,
            "v114_three_family_counts": {
                "BALANCED_BATCH_REFINEMENT": 2,
                "COUPLED_EXCHANGE": 2,
                "MAINTENANCE_CASCADE": 2,
            },
            "v114_target_labels": 368,
            "v114_cold_direct_labels": 681,
            "v114_incremental_compilation_events": 4495,
            "v114_full_rebuild_compilation_events": 31524,
            "v114_identity_and_bytes_retained": True,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v115_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V115),
            "frozen_before_any_registered_v115_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v115()["target_occurrences"],
            "target_seeds_unique": len({seed for _family, seed in TARGET_OCCURRENCES})
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "one_occurrence_per_family": all(
                sum(row[0] == family for row in TARGET_OCCURRENCES) == 1
                for family in REQUIRED_TARGET_FAMILIES
            ),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "v113_incremental_compiler_and_planner_semantics_retained": True,
            "same_acquisition_exact_engine_and_outcome_tape_for_memo_and_control": True,
            "program_successor_projection_cache_keyed_by_compiled_state_state_and_action": True,
            "whole_plan_cache_keyed_by_projected_state_and_exact_legal_set": True,
            "memo_invalidated_on_compiled_successor_state_change": True,
            "every_action_certificate_overlay_model_and_execution_must_match_v113": True,
            "uncached_equivalent_branch_count_must_reconstruct_v113_compute": True,
            "every_occurrence_requires_positive_branch_reuse": True,
            "every_occurrence_requires_strict_planning_compute_reduction": True,
            "compiled_model_and_memo_only_order_actions": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "all_three_registered_structural_families_present": True,
            "every_occurrence_matches_v113_actions_certificates_models_and_execution": True,
            "every_occurrence_observes_program_branch_reuse": True,
            "every_occurrence_planning_compute_below_v113": True,
            "aggregate_planning_compute_below_v113": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
            "matched_v113_compute_not_charged_to_memo_arm": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v115_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_projected_program_memoization_verified": False,
            "compiled_model_or_memo_used_as_safety_authority": False,
            "global_lumpability_claimed": False,
            "complete_ground_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v115(
            domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_PREREGISTRATION_V115_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProjectedProgramMemoPreregistrationV115:
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
            or domains.extension_content_id_v115(
                domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_PREREGISTRATION_V115_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V115 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: ProjectedProgramMemoPreregistrationV115 | None = None


def freeze_projected_program_memo_preregistration_v115() -> ProjectedProgramMemoPreregistrationV115:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V115 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V115 frozen preregistration changed")
        _CACHE = ProjectedProgramMemoPreregistrationV115(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_projected_program_memo_preregistration_v115(
    value: Any,
) -> ProjectedProgramMemoPreregistrationV115:
    if type(value) is not ProjectedProgramMemoPreregistrationV115:
        _fail("V115 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_projected_program_memo_preregistration_v115()
    if value is not expected:
        _fail("V115 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v115",
    "freeze_projected_program_memo_preregistration_v115",
    "verify_projected_program_memo_preregistration_v115",
)
