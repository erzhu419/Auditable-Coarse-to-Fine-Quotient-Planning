"""Outcome-free preregistration for cross-epoch branch reuse V116."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v116 as domains
from acfqp import construction_k7_projected_program_memo_preregistration_v115 as previous
from acfqp.construction_k7_projected_program_memo_campaign_v115 import (
    CAMPAIGN_ID as V115_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V115_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_projected_program_memo_independent_verifier_v115 import (
    EXPECTED_CANONICAL_SHA256 as V115_VERIFICATION_SHA256,
    VERIFICATION_ID as V115_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("4617db3", "de45f46")
PREREGISTRATION_ID = "0110bd988c146dcb5d93f67081e4ce603f0106ca1df2d93e0e2dc74a3c0d6012"
EXPECTED_CANONICAL_BYTE_COUNT = 21_767
EXPECTED_CANONICAL_SHA256 = (
    "239f7c5d22fb969fdc215482da64b40a69f1e53309b984e6ca49393d9fe2d63c"
)
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_028_101),
    ("COUPLED_EXCHANGE", 1_028_201),
    ("MAINTENANCE_CASCADE", 1_028_301),
)
TARGET_EPISODE_INDICES = (251, 252, 253)
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
        "src/acfqp/construction_k7_domain_registry_extension_v116.py",
        1651,
        "6d420d07993325d721be50fae220da361ff8399b00482bbe5f324e6680aff1a0",
    ),
    (
        "src/acfqp/generic_cross_epoch_program_branch_sequence_v116.py",
        5941,
        "8b47071ebd77ab3da634cbf0fe9358769fc012a17898dba07586e231caa14242",
    ),
    (
        "src/acfqp/cross_epoch_program_branch_campaign_core_v116.py",
        13287,
        "6ffd7519aad384951e72643eed0ebe43791a0e5fd1fd965376a85a4f9c43380a",
    ),
    (
        "src/acfqp/construction_k7_projected_program_memo_preregistration_v115.py",
        11819,
        "7271136c8d291145fedfa169ca744f0ebb07a9180fa53500de044b55e8183445",
    ),
    (
        "src/acfqp/construction_k7_projected_program_memo_campaign_v115.py",
        4877,
        "40f2aea35811f59344f5df69ec88ecd59ba8b1828fe6b924872fc6a52d8ee3fd",
    ),
    (
        "src/acfqp/construction_k7_projected_program_memo_independent_verifier_v115.py",
        26587,
        "c00a56add0fd915420d8f18ec92b79a4d4fa8420647719c522e51cd4eacfa6f2",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7CrossEpochProgramBranchPreregistrationV116Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossEpochProgramBranchPreregistrationV116Error(message)


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


def campaign_config_v116() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v115())
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
        "schema": "acfqp.cross_epoch_program_branch_preregistration.v116",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v115_campaign_id": V115_CAMPAIGN_ID,
            "v115_campaign_sha256": V115_CAMPAIGN_SHA256,
            "v115_verification_id": V115_VERIFICATION_ID,
            "v115_verification_sha256": V115_VERIFICATION_SHA256,
            "v115_registered_gate_passed": True,
            "v115_passed_occurrence_count": 3,
            "v115_target_labels": 145,
            "v115_planning_compute_events": 101_300,
            "v115_uncached_v113_planning_compute_events": 123_716,
            "v115_planning_compute_events_avoided": 22_416,
            "v115_identity_and_bytes_retained": True,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v116_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V116),
            "frozen_before_any_registered_v116_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v116()["target_occurrences"],
            "target_seeds_unique": len({seed for _family, seed in TARGET_OCCURRENCES})
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "one_occurrence_per_family": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "v115_branch_cache_and_v113_planner_semantics_retained": True,
            "factor_successor_projection_depends_only_on_candidate_catalogue_state_and_action": True,
            "factor_successor_projection_cache_retained_across_model_epochs": True,
            "whole_program_plan_cache_still_invalidated_on_model_epoch_change": True,
            "every_action_certificate_overlay_model_and_execution_must_match_v115": True,
            "every_occurrence_planning_compute_must_not_exceed_v115": True,
            "at_least_one_occurrence_and_aggregate_must_strictly_improve_v115": True,
            "compiled_model_and_cache_only_order_actions": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "all_three_registered_structural_families_present": True,
            "every_occurrence_matches_v115_actions_certificates_models_and_execution": True,
            "every_occurrence_planning_compute_not_above_v115": True,
            "at_least_one_occurrence_observes_additional_cross_epoch_branch_reuse": True,
            "aggregate_planning_compute_below_v115": True,
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
            "matched_v115_compute_not_charged_to_cross_epoch_arm": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v116_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_cross_epoch_program_branch_reuse_verified": False,
            "compiled_model_or_cache_used_as_safety_authority": False,
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
        "preregistration_id": domains.extension_content_id_v116(
            domains.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_PREREGISTRATION_V116_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CrossEpochProgramBranchPreregistrationV116:
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
            or domains.extension_content_id_v116(
                domains.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_PREREGISTRATION_V116_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V116 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: CrossEpochProgramBranchPreregistrationV116 | None = None


def freeze_cross_epoch_program_branch_preregistration_v116() -> CrossEpochProgramBranchPreregistrationV116:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V116 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V116 frozen preregistration changed")
        _CACHE = CrossEpochProgramBranchPreregistrationV116(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_cross_epoch_program_branch_preregistration_v116(
    value: Any,
) -> CrossEpochProgramBranchPreregistrationV116:
    if type(value) is not CrossEpochProgramBranchPreregistrationV116:
        _fail("V116 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_cross_epoch_program_branch_preregistration_v116()
    if value is not expected:
        _fail("V116 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v116",
    "freeze_cross_epoch_program_branch_preregistration_v116",
    "verify_cross_epoch_program_branch_preregistration_v116",
)
