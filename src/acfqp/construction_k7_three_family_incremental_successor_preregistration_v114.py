"""Outcome-free three-family incremental-successor preregistration V114."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v114 as domains
from acfqp import construction_k7_incremental_abstract_successor_preregistration_v113 as previous
from acfqp.construction_k7_incremental_abstract_successor_campaign_v113 import (
    CAMPAIGN_ID as V113_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V113_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_incremental_abstract_successor_independent_verifier_v113 import (
    EXPECTED_CANONICAL_SHA256 as V113_VERIFICATION_SHA256,
    VERIFICATION_ID as V113_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("ad925c5", "3f71509")
PREREGISTRATION_ID = "a638782c5108b33039f48a23c0f2dfbc32bc1ebb158d4e19afbdf1f982398433"
EXPECTED_CANONICAL_BYTE_COUNT = 19_757
EXPECTED_CANONICAL_SHA256 = "b2446bb8bc739f2e5143e23d76990bad9fcdf43ba461fbdb56afe41bb5cfee3d"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_026_101),
    ("BALANCED_BATCH_REFINEMENT", 1_026_102),
    ("COUPLED_EXCHANGE", 1_026_201),
    ("COUPLED_EXCHANGE", 1_026_202),
    ("MAINTENANCE_CASCADE", 1_026_301),
    ("MAINTENANCE_CASCADE", 1_026_302),
)
TARGET_EPISODE_INDICES = (231, 232, 233)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "COUPLED_EXCHANGE",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v114.py",
        1626,
        "440fb83dab002abea5f900ca9cb15bd0e1f72f2033965ed9b75425742f338127",
    ),
    (
        "src/acfqp/three_family_incremental_successor_campaign_core_v114.py",
        8824,
        "29f11b185b625e9ed0eae8eafa5b16b3edd20fc670d06091d1de0df04f58dbf0",
    ),
    (
        "src/acfqp/construction_k7_incremental_abstract_successor_preregistration_v113.py",
        12394,
        "51989dff0af674398b45b309f20fa49f1da587bd9ec3e6b194be60fb549bbea5",
    ),
    (
        "src/acfqp/construction_k7_incremental_abstract_successor_campaign_v113.py",
        4916,
        "e1d42d772465a551ba560d1fce786ba328c836a9328a841605ce58457a7b2075",
    ),
    (
        "src/acfqp/construction_k7_incremental_abstract_successor_independent_verifier_v113.py",
        31874,
        "e263d896a02984c3377c9dc2106e04e2e86ddefea060e6ff9dcead488feb02c2",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7ThreeFamilyIncrementalSuccessorPreregistrationV114Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ThreeFamilyIncrementalSuccessorPreregistrationV114Error(
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


def campaign_config_v114() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v113())
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
        "schema": "acfqp.three_family_incremental_successor_preregistration.v114",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v113_campaign_id": V113_CAMPAIGN_ID,
            "v113_campaign_sha256": V113_CAMPAIGN_SHA256,
            "v113_verification_id": V113_VERIFICATION_ID,
            "v113_verification_sha256": V113_VERIFICATION_SHA256,
            "v113_registered_gate_passed": True,
            "v113_passed_occurrence_count": 4,
            "v113_incremental_compilation_events": 3305,
            "v113_full_rebuild_compilation_events": 22089,
            "v113_compilation_events_avoided": 18784,
            "v113_target_labels": 295,
            "v113_cold_direct_labels": 588,
            "v113_identity_and_bytes_retained": True,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v114_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V114),
            "frozen_before_any_registered_v114_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v114()["target_occurrences"],
            "target_seeds_unique": len({seed for _family, seed in TARGET_OCCURRENCES})
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "two_occurrences_per_family": all(
                sum(row[0] == family for row in TARGET_OCCURRENCES) == 2
                for family in REQUIRED_TARGET_FAMILIES
            ),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "v113_compiler_planner_and_stop_rules_unchanged": True,
            "coupled_exchange_was_absent_from_v113_registered_targets": True,
            "all_three_existing_structural_families_are_now_fresh_targets": True,
            "same_incremental_compiler_and_full_rebuild_control_for_every_family": True,
            "every_model_and_terminal_rule_must_equal_fresh_full_rebuild": True,
            "every_action_plan_receipt_label_step_and_dependency_axis_must_match": True,
            "compiled_model_only_orders_actions": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "all_three_registered_structural_families_present": True,
            "every_occurrence_unchanged_v113_gate_passed": True,
            "every_occurrence_execution_exactly_matches_full_rebuild": True,
            "every_occurrence_incremental_model_equals_full_v105_rebuild": True,
            "every_occurrence_planner_uses_compiled_model_without_raw_rows": True,
            "every_occurrence_incremental_compilation_below_full_rebuild": True,
            "aggregate_incremental_compilation_below_full_rebuild": True,
            "aggregate_quotient_labels_below_cold_direct": True,
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
            "matched_control_compute_not_charged_to_incremental_arm": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v114_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_three_family_incremental_successor_transfer_verified": False,
            "compiled_model_used_as_safety_authority": False,
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
        "preregistration_id": domains.extension_content_id_v114(
            domains.CONSTRUCTION_K7_THREE_FAMILY_INCREMENTAL_SUCCESSOR_PREREGISTRATION_V114_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ThreeFamilyIncrementalSuccessorPreregistrationV114:
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
            or domains.extension_content_id_v114(
                domains.CONSTRUCTION_K7_THREE_FAMILY_INCREMENTAL_SUCCESSOR_PREREGISTRATION_V114_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V114 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: ThreeFamilyIncrementalSuccessorPreregistrationV114 | None = None


def freeze_three_family_incremental_successor_preregistration_v114() -> ThreeFamilyIncrementalSuccessorPreregistrationV114:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V114 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V114 frozen preregistration changed")
        _CACHE = ThreeFamilyIncrementalSuccessorPreregistrationV114(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_three_family_incremental_successor_preregistration_v114(
    value: Any,
) -> ThreeFamilyIncrementalSuccessorPreregistrationV114:
    if type(value) is not ThreeFamilyIncrementalSuccessorPreregistrationV114:
        _fail("V114 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_three_family_incremental_successor_preregistration_v114()
    if value is not expected:
        _fail("V114 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v114",
    "freeze_three_family_incremental_successor_preregistration_v114",
    "verify_three_family_incremental_successor_preregistration_v114",
)
