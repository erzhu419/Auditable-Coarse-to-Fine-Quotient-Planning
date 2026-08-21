"""Outcome-free preregistration for family-wide opportunity coverage V102."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_abstract_execution_utilization_preregistration_v101 as previous
from acfqp import construction_k7_domain_registry_extension_v102 as domains
from acfqp.construction_k7_abstract_execution_utilization_campaign_v101 import CAMPAIGN_ID as V101_CAMPAIGN_ID, EXPECTED_CANONICAL_SHA256 as V101_CAMPAIGN_SHA256
from acfqp.construction_k7_abstract_execution_utilization_independent_verifier_v101 import VERIFICATION_ID as V101_VERIFICATION_ID, EXPECTED_CANONICAL_SHA256 as V101_VERIFICATION_SHA256
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json

IMPLEMENTATION_COMMITS = ("2352b84",)
PREREGISTRATION_ID = "961025ca99438c31ecedaf33431f8ec95817f1b1d99fe9edda4886a8e1395ba2"
EXPECTED_CANONICAL_BYTE_COUNT = 7_488
EXPECTED_CANONICAL_SHA256 = "8c2b3fc924fef357c479e2726455575e2e2a0d0d5fbcd77e735e704ca184901d"
TARGET_OCCURRENCES = (("BALANCED_BATCH_REFINEMENT", 1_013_101), ("BALANCED_BATCH_REFINEMENT", 1_013_102), ("MAINTENANCE_CASCADE", 1_013_103), ("MAINTENANCE_CASCADE", 1_013_104))
TARGET_EPISODE_INDICES = (111, 112, 113)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = ("BALANCED_BATCH_REFINEMENT", "MAINTENANCE_CASCADE")
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v102.py", 1490, "0cc89fe8250687d37546785d896bea1aceb7b6c765b7cabcee45135c4f175014"),
    ("src/acfqp/family_wide_abstract_utilization_campaign_core_v102.py", 9254, "623b01572f4583c319870e3404d8bf01521c93f5c85f17e20548cec61632b91b"),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7FamilyWideUtilizationPreregistrationV102Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FamilyWideUtilizationPreregistrationV102Error(message)


def _source_facts() -> list[dict[str, Any]]:
    return [{"relative_path": p, "byte_count": len((SOURCE_ROOT / p).read_bytes()), "sha256": hashlib.sha256((SOURCE_ROOT / p).read_bytes()).hexdigest()} for p, _n, _h in FROZEN_SOURCE_FACTS]


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [{"relative_path": p, "byte_count": n, "sha256": h} for p, n, h in FROZEN_SOURCE_FACTS]


def campaign_config_v102() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v101())
    config.update(target_occurrences=[{"family": f, "seed": s} for f, s in TARGET_OCCURRENCES], target_episode_indices=TARGET_EPISODE_INDICES, target_worker_count=TARGET_WORKER_COUNT, required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT, required_target_families=REQUIRED_TARGET_FAMILIES)
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.family_wide_utilization_preregistration.v102",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {"v101_failed_campaign_id": V101_CAMPAIGN_ID, "v101_failed_campaign_sha256": V101_CAMPAIGN_SHA256, "v101_failure_verification_id": V101_VERIFICATION_ID, "v101_failure_verification_sha256": V101_VERIFICATION_SHA256, "v101_registered_gate_passed": False, "v101_failure_retained_without_correction": True, "source_library_artifact_id": previous.previous.SOURCE_LIBRARY_ARTIFACT_ID, "v62_residual_library_id": previous.previous.V62_LIBRARY_ID},
        "source_closure": {"source_facts": _frozen_source_facts(), "v102_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V102), "frozen_before_any_registered_v102_target_outcome": True},
        "identity_contract": {"target_occurrences": campaign_config_v102()["target_occurrences"], "target_seeds_unique": len({s for _f, s in TARGET_OCCURRENCES}) == len(TARGET_OCCURRENCES), "target_seeds_not_previously_exposed": True, "required_target_families": list(REQUIRED_TARGET_FAMILIES), "target_episode_indices": list(TARGET_EPISODE_INDICES)},
        "construction_contract": {"frozen_v101_algorithm_and_measurement_reused_without_change": True, "only_changed_variable": "SHIELD_DISAGREEMENT_OPPORTUNITY_COVERAGE_AGGREGATION", "v101_coverage_unit": "EVERY_OCCURRENCE", "v102_coverage_unit": "EVERY_TARGET_FAMILY", "every_occurrence_still_requires_abstract_execution_strict_majority": True, "every_family_requires_both_accept_and_disagreement_paths": True, "exact_overlay_exclusively_discharges_safety": True, "every_new_ground_query_must_follow_failed_certificate": True},
        "registered_gate": {"required_target_occurrence_count": 4, "every_occurrence_abstract_matches_strict_majority_of_executed_actions": True, "every_target_family_exercises_both_shield_paths": True, "aggregate_activation_sample_tax_strictly_reduced": True, "aggregate_meta_task_labels_not_above_no_prior": True, "aggregate_meta_task_labels_below_cold_direct": True, "strict_incompatible_schema_no_transfer_required": True, "all_unfavourable_results_retained": True},
        "resource_schedule": {"target_worker_count": 2, "maximum_simultaneous_worker_count": 2, "target_occurrence_count": 4, "query_episode_count_per_arm": 3, "maximum_incremental_certificate_labels_per_episode": 100_000},
        "accounting_contract": {"offline_source_labels_not_recharged": True, "activation_labels_use_right_censoring": True, "meta_no_prior_and_direct_target_labels_separate": True, "execution_steps_separate": True, "derivation_shield_and_planning_compute_separate": True, "no_scalar_cost_aggregation": True},
        "claim_boundary": {"registered_v102_target_outcome_observed": False, "producer_free_verification_present": False, "registered_multistep_execution_primarily_abstract_ordered_verified": False, "complete_world_model_synthesized": False, "global_exact_dynamics_claimed": False, "arbitrary_domain_transfer_claimed": False, "official_execution_allowed": False, "official_scalar_cost": None, "official_N_break_even": None, "WORKLOAD_ECONOMICS_GATE": "NOT_RUN", "COUNTER_COMPLETENESS_GATE": "NOT_RUN"},
    }
    return {**payload, "preregistration_id": domains.extension_content_id_v102(domains.CONSTRUCTION_K7_FAMILY_WIDE_UTILIZATION_PREREGISTRATION_V102_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FamilyWideUtilizationPreregistrationV102:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes); payload = {k: v for k, v in document.items() if k != "preregistration_id"}
        if self._issuer is not _ISSUER or canonical_json_bytes(document) != self.canonical_bytes or document.get("preregistration_id") != self.preregistration_id or domains.extension_content_id_v102(domains.CONSTRUCTION_K7_FAMILY_WIDE_UTILIZATION_PREREGISTRATION_V102_DOMAIN, payload) != self.preregistration_id:
            _fail("V102 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: FamilyWideUtilizationPreregistrationV102 | None = None


def freeze_family_wide_utilization_preregistration_v102() -> FamilyWideUtilizationPreregistrationV102:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts(): _fail("V102 preregistered source closure changed")
        document = _document(); raw = canonical_json_bytes(document); identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (identity != PREREGISTRATION_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256): _fail("V102 frozen preregistration changed")
        _CACHE = FamilyWideUtilizationPreregistrationV102(_ISSUER, raw, identity)
    return _CACHE


def verify_family_wide_utilization_preregistration_v102(value: Any) -> FamilyWideUtilizationPreregistrationV102:
    if type(value) is not FamilyWideUtilizationPreregistrationV102: _fail("V102 preregistration rejects foreign values")
    value.__post_init__(); expected = freeze_family_wide_utilization_preregistration_v102()
    if value is not expected: _fail("V102 preregistration differs from frozen output")
    return value


__all__ = ("PREREGISTRATION_ID", "campaign_config_v102", "freeze_family_wide_utilization_preregistration_v102", "verify_family_wide_utilization_preregistration_v102")
