"""Outcome-free preregistration for hierarchical abstract utilization V104."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v104 as domains
from acfqp import construction_k7_receipted_utilization_preregistration_v103 as previous
from acfqp.construction_k7_receipted_utilization_campaign_v103 import (
    CAMPAIGN_ID as V103_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V103_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_receipted_utilization_independent_verifier_v103 import (
    EXPECTED_CANONICAL_SHA256 as V103_VERIFICATION_SHA256,
    VERIFICATION_ID as V103_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json

IMPLEMENTATION_COMMITS = ("4b981be",)
PREREGISTRATION_ID = "3e3c1f114022357153650c086034d38d86d82cec1e2826929048197a2ca60e66"
EXPECTED_CANONICAL_BYTE_COUNT = 9_868
EXPECTED_CANONICAL_SHA256 = "0febee4024b93913a49675ff6dcb37e38b1b0450ddf4e98cc108575aaf5f0016"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_016_101),
    ("BALANCED_BATCH_REFINEMENT", 1_016_102),
    ("MAINTENANCE_CASCADE", 1_016_103),
    ("MAINTENANCE_CASCADE", 1_016_104),
)
TARGET_EPISODE_INDICES = (131, 132, 133)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v104.py",
        1574,
        "bca1789c0e83164ed13aa2d43a3f9b79e688ce76471a4fb80ad779aa6d313bd9",
    ),
    (
        "src/acfqp/generic_hierarchical_abstract_execution_receipt_v104.py",
        3644,
        "ec91b07065c6c5362abd0fc4644ef83fbc1721d5eaabe0443a6b4a58e6f6317f",
    ),
    (
        "src/acfqp/generic_persistent_hierarchical_receipted_sequence_v104.py",
        4197,
        "79a2168a8adbadd7898932baca159fd9e1b6a0ec8c9c4e5eb63d9d8298b5565d",
    ),
    (
        "src/acfqp/hierarchical_abstract_utilization_campaign_core_v104.py",
        16355,
        "ede3541626bb05365e86f78e4e359b78b8c021ee851a4ced7de4d54193363ab4",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7HierarchicalUtilizationPreregistrationV104Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HierarchicalUtilizationPreregistrationV104Error(message)


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


def campaign_config_v104() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v103())
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
        "schema": "acfqp.hierarchical_abstract_utilization_preregistration.v104",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {
            "v103_failed_campaign_id": V103_CAMPAIGN_ID,
            "v103_failed_campaign_sha256": V103_CAMPAIGN_SHA256,
            "v103_failure_verification_id": V103_VERIFICATION_ID,
            "v103_failure_verification_sha256": V103_VERIFICATION_SHA256,
            "v103_registered_gate_passed": False,
            "v103_failure_retained_without_reclassification": True,
            "v103_full_post_dependency_match_count": 13,
            "v103_execution_step_count": 71,
            "source_library_artifact_id": previous.previous.previous.previous.SOURCE_LIBRARY_ARTIFACT_ID,
            "v62_residual_library_id": previous.previous.previous.previous.V62_LIBRARY_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v104_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V104),
            "frozen_before_any_registered_v104_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v104()["target_occurrences"],
            "target_seeds_unique": len({seed for _family, seed in TARGET_OCCURRENCES})
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "v103_planning_policy_and_safety_engine_reused_without_change": True,
            "every_action_receipt_classifies_exactly_one_ordering_source": True,
            "full_post_dependency_match_requires_full_partial_and_chosen_agreement": True,
            "compiled_partial_fallback_match_requires_partial_and_chosen_agreement": True,
            "exact_policy_only_actions_not_counted_as_abstract_ordered": True,
            "full_model_match_never_inferred_from_partial_fallback": True,
            "partial_world_model_incompleteness_always_explicit": True,
            "every_occurrence_requires_full_or_partial_abstract_strict_majority": True,
            "every_family_requires_both_accept_and_disagreement_paths": True,
            "exact_overlay_exclusively_discharges_safety": True,
            "every_new_ground_query_must_follow_failed_certificate": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_action_hierarchical_receipt_replays_independently": True,
            "every_occurrence_full_or_explicit_partial_abstract_strict_majority": True,
            "every_target_family_exercises_both_shield_paths": True,
            "aggregate_activation_sample_tax_strictly_reduced": True,
            "aggregate_meta_task_labels_not_above_no_prior": True,
            "aggregate_meta_task_labels_below_cold_direct": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count_per_arm": len(TARGET_EPISODE_INDICES),
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "activation_labels_use_right_censoring": True,
            "full_partial_and_exact_ordering_counts_separate": True,
            "meta_no_prior_and_direct_target_labels_separate": True,
            "execution_steps_separate": True,
            "derivation_shield_and_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v104_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_multistep_execution_primarily_abstract_ordered_verified": False,
            "full_post_dependency_world_model_primary_ordering_verified": False,
            "partial_world_model_primary_ordering_verified": False,
            "complete_world_model_synthesized": False,
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
        "preregistration_id": domains.extension_content_id_v104(
            domains.CONSTRUCTION_K7_HIERARCHICAL_UTILIZATION_PREREGISTRATION_V104_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class HierarchicalUtilizationPreregistrationV104:
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
            or domains.extension_content_id_v104(
                domains.CONSTRUCTION_K7_HIERARCHICAL_UTILIZATION_PREREGISTRATION_V104_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V104 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: HierarchicalUtilizationPreregistrationV104 | None = None


def freeze_hierarchical_utilization_preregistration_v104() -> HierarchicalUtilizationPreregistrationV104:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V104 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V104 frozen preregistration changed")
        _CACHE = HierarchicalUtilizationPreregistrationV104(_ISSUER, raw, identity)
    return _CACHE


def verify_hierarchical_utilization_preregistration_v104(
    value: Any,
) -> HierarchicalUtilizationPreregistrationV104:
    if type(value) is not HierarchicalUtilizationPreregistrationV104:
        _fail("V104 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_hierarchical_utilization_preregistration_v104()
    if value is not expected:
        _fail("V104 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v104",
    "freeze_hierarchical_utilization_preregistration_v104",
    "verify_hierarchical_utilization_preregistration_v104",
)
