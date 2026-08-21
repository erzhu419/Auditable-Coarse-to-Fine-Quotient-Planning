"""Outcome-free preregistration for dependency-revalidated quotient reuse V109."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v109 as domains
from acfqp import construction_k7_memoized_catalogue_quotient_preregistration_v108 as previous
from acfqp.construction_k7_memoized_catalogue_quotient_campaign_v108 import (
    CAMPAIGN_ID as V108_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V108_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_memoized_catalogue_quotient_independent_verifier_v108 import (
    EXPECTED_CANONICAL_SHA256 as V108_VERIFICATION_SHA256,
    VERIFICATION_ID as V108_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("19d63dd", "34267a1")
PREREGISTRATION_ID = "c1a213ba65426761648c31c6a2f51356509d49d88e0a14244c7428cf42e44df8"
EXPECTED_CANONICAL_BYTE_COUNT = 15_676
EXPECTED_CANONICAL_SHA256 = "a194725d9920ecb23ae674e6400221b5379d0e2f2ca1d39a7a5a774938f0f0f3"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_021_101),
    ("BALANCED_BATCH_REFINEMENT", 1_021_102),
    ("MAINTENANCE_CASCADE", 1_021_103),
    ("MAINTENANCE_CASCADE", 1_021_104),
)
TARGET_EPISODE_INDICES = (181, 182, 183)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v109.py",
        1972,
        "504ceb9cabcea9fba4fb8d8e8aeb1625ab3f597b72068ebe5fdc879ddc36586a",
    ),
    (
        "src/acfqp/generic_quotient_plan_dependency_receipt_v109.py",
        7332,
        "5d89090a1fe35fa72cb2e4dfb0758201c5f981bea9b8bff067fbda37d3972a75",
    ),
    (
        "src/acfqp/generic_dependency_revalidated_execution_receipt_v109.py",
        6096,
        "7383298fdb875523de7db1704abb1fcf9d54ea1019d62df0f7aa6b5c8326b504",
    ),
    (
        "src/acfqp/generic_dependency_revalidated_quotient_sequence_v109.py",
        21002,
        "3d70d49179e2730c08c47cdc7dabf6c762c8984d7a14cff9216d5a48848b4021",
    ),
    (
        "src/acfqp/dependency_revalidated_quotient_campaign_core_v109.py",
        15002,
        "1e4ade9cbed53ff8f573318717451c266f6a9abd4b29d73e8dced9dd0a89f51b",
    ),
    (
        "src/acfqp/construction_k7_memoized_catalogue_quotient_campaign_v108.py",
        5011,
        "f347116f8581e52832879eae4779c572eee5a2c13623e6a3ca67b24baf45c475",
    ),
    (
        "src/acfqp/construction_k7_memoized_catalogue_quotient_independent_verifier_v108.py",
        32359,
        "42af7e0038f6367d59f3145fcc28ba5085287b510639caa141a380402b6084e6",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7DependencyRevalidatedQuotientPreregistrationV109Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DependencyRevalidatedQuotientPreregistrationV109Error(
        message
    )


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


def campaign_config_v109() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v108())
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
        "schema": "acfqp.dependency_revalidated_quotient_preregistration.v109",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_failed_predecessor": {
            "v108_campaign_id": V108_CAMPAIGN_ID,
            "v108_campaign_sha256": V108_CAMPAIGN_SHA256,
            "v108_verification_id": V108_VERIFICATION_ID,
            "v108_verification_sha256": V108_VERIFICATION_SHA256,
            "v108_registered_gate_passed": False,
            "v108_passed_target_occurrence_count": 2,
            "v108_failure_reason": "TWO_BALANCED_OCCURRENCES_HAD_NO_CROSS_EPISODE_IDENTITY_BOUND_CACHE_HIT",
            "v108_actions_receipts_and_labels_equal_no_cache": True,
            "v108_aggregate_planning_compute_events_avoided": 550,
            "v108_failed_identity_retained_without_rerun": True,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v109_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V109),
            "frozen_before_any_registered_v109_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v109()["target_occurrences"],
            "target_seeds_unique": len(
                {seed for _family, seed in TARGET_OCCURRENCES}
            )
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "only_observation_quotient_graph_plans_are_cross_graph_cache_eligible": True,
            "dependency_receipt_contains_exact_bfs_dequeue_prefix_terminal_rule_and_outgoing_edges": True,
            "reuse_requires_exact_dependency_slice_equality": True,
            "unrelated_graph_identity_and_edges_do_not_force_invalidation": True,
            "cached_plan_is_only_an_action_ordering_heuristic": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "matched_no_cache_arm_uses_same_synthesizer_planner_and_stopping_rule": True,
            "revalidated_and_no_cache_actions_base_receipts_labels_and_steps_must_match": True,
            "new_planner_branch_evaluations_and_dependency_validation_checks_separate": True,
            "sample_labels_execution_steps_and_all_compute_axes_separate": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "ground_transition_accessed_during_dependency_validation": False,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_actions_base_receipts_labels_and_steps_equal_no_cache": True,
            "every_occurrence_new_planning_compute_strictly_reduced": True,
            "every_occurrence_dependency_revalidated_hit_observed": True,
            "every_occurrence_quotient_orders_at_least_three_quarters": True,
            "every_occurrence_chosen_action_match_strict_majority": True,
            "every_occurrence_later_zero_label_quotient_reuse": True,
            "aggregate_quotient_labels_below_cold_direct": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "matched_revalidated_and_no_cache_sequences_per_occurrence": 2,
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "matched_no_cache_labels_are_baseline_not_charged_to_reuse_arm": True,
            "initial_acquisition_and_certificate_local_labels_separate": True,
            "new_planning_and_dependency_validation_compute_separate": True,
            "execution_steps_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v109_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_dependency_revalidated_reuse_verified": False,
            "cache_used_as_safety_authority": False,
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
        "preregistration_id": domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_PREREGISTRATION_V109_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class DependencyRevalidatedQuotientPreregistrationV109:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value
            for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v109(
                domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_PREREGISTRATION_V109_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V109 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: DependencyRevalidatedQuotientPreregistrationV109 | None = None


def freeze_dependency_revalidated_quotient_preregistration_v109() -> DependencyRevalidatedQuotientPreregistrationV109:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V109 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V109 frozen preregistration changed")
        _CACHE = DependencyRevalidatedQuotientPreregistrationV109(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_dependency_revalidated_quotient_preregistration_v109(
    value: Any,
) -> DependencyRevalidatedQuotientPreregistrationV109:
    if type(value) is not DependencyRevalidatedQuotientPreregistrationV109:
        _fail("V109 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_dependency_revalidated_quotient_preregistration_v109()
    if value is not expected:
        _fail("V109 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v109",
    "freeze_dependency_revalidated_quotient_preregistration_v109",
    "verify_dependency_revalidated_quotient_preregistration_v109",
)
