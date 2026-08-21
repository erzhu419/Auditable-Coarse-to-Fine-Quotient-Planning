"""Outcome-free preregistration for epoch-indexed dependency reuse V110."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v110 as domains
from acfqp import construction_k7_dependency_revalidated_quotient_preregistration_v109 as previous
from acfqp.construction_k7_dependency_revalidated_quotient_campaign_v109 import (
    CAMPAIGN_ID as V109_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V109_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_dependency_revalidated_quotient_independent_verifier_v109 import (
    EXPECTED_CANONICAL_SHA256 as V109_VERIFICATION_SHA256,
    VERIFICATION_ID as V109_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("fd3d3fa", "4cae3dc")
PREREGISTRATION_ID = "ce41eb77cb6f1270fde8f6121ade5a73a937bbdb4dd912d95a0313891b04b2be"
EXPECTED_CANONICAL_BYTE_COUNT = 16_375
EXPECTED_CANONICAL_SHA256 = "663ee3d98171f0536f2284021edc09bb061772f274ffa47d66226e8eee9d47b2"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_022_101),
    ("BALANCED_BATCH_REFINEMENT", 1_022_102),
    ("MAINTENANCE_CASCADE", 1_022_103),
    ("MAINTENANCE_CASCADE", 1_022_104),
)
TARGET_EPISODE_INDICES = (191, 192, 193)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v110.py",
        1729,
        "733fdd53737555cf8b2a7de61945c813d7cf46ca7633b61929bc30679b5c1e51",
    ),
    (
        "src/acfqp/generic_epoch_indexed_quotient_sequence_v110.py",
        19746,
        "f7abc47b56795f364091a2eb857870f36673950c9c25ac2977bfcd188a010c1c",
    ),
    (
        "src/acfqp/epoch_indexed_quotient_campaign_core_v110.py",
        13682,
        "0a30ea4e75d1716ee7adfc6e9ff51243724dd39f5f799cbfde5bf77e17d09fdd",
    ),
    (
        "src/acfqp/construction_k7_dependency_revalidated_quotient_campaign_v109.py",
        5066,
        "6346cd41767f991275acfe1a4d6377441575bb6aa5058b7b76619e338fee8288",
    ),
    (
        "src/acfqp/construction_k7_dependency_revalidated_quotient_independent_verifier_v109.py",
        42869,
        "0c76567ddd3c9a08b41cbdac33d5f95a908b1bc619a2b0884b8d72a9116d5e83",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7EpochIndexedQuotientPreregistrationV110Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7EpochIndexedQuotientPreregistrationV110Error(message)


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


def campaign_config_v110() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v109())
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
        "schema": "acfqp.epoch_indexed_quotient_preregistration.v110",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_successful_predecessor": {
            "v109_campaign_id": V109_CAMPAIGN_ID,
            "v109_campaign_sha256": V109_CAMPAIGN_SHA256,
            "v109_verification_id": V109_VERIFICATION_ID,
            "v109_verification_sha256": V109_VERIFICATION_SHA256,
            "v109_registered_gate_passed": True,
            "v109_actions_receipts_labels_and_steps_equal_no_cache": True,
            "v109_target_labels": 277,
            "v109_cold_direct_labels": 516,
            "v109_planning_compute_events_avoided": 1740,
            "v109_per_hit_dependency_validation_checks": 4477,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v110_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V110),
            "frozen_before_any_registered_v110_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v110()["target_occurrences"],
            "target_seeds_unique": len({seed for _family, seed in TARGET_OCCURRENCES})
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "dependency_receipt_is_exact_minimal_bfs_slice": True,
            "reverse_index_maps_projected_state_to_dependency_receipts": True,
            "each_model_epoch_computes_exact_outgoing_edge_delta": True,
            "terminal_rule_delta_invalidates_all_prior_receipts": True,
            "only_changed_dependency_slices_are_invalidated": True,
            "retained_cache_hits_do_not_rescan_dependency_rows": True,
            "cache_only_orders_actions": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "matched_per_hit_and_no_cache_arms_use_same_synthesizer_and_stopping_rule": True,
            "indexed_per_hit_and_no_cache_actions_receipts_labels_and_steps_must_match": True,
            "new_planning_model_epoch_diff_reverse_index_and_per_hit_compute_are_separate": True,
            "sample_labels_execution_steps_and_all_compute_axes_separate": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "ground_transition_accessed_during_epoch_invalidation": False,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_execution_exactly_matches_per_hit_and_no_cache": True,
            "every_occurrence_new_planning_compute_below_no_cache": True,
            "every_occurrence_epoch_maintenance_below_per_hit_validation": True,
            "every_occurrence_epoch_authorized_hit_observed": True,
            "every_occurrence_per_hit_dependency_rescan_zero": True,
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
            "matched_indexed_per_hit_no_cache_and_direct_sequences_per_occurrence": 4,
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "matched_baseline_labels_not_charged_to_indexed_arm": True,
            "initial_acquisition_and_certificate_local_labels_separate": True,
            "new_planning_compute_separate": True,
            "model_epoch_diff_checks_separate": True,
            "reverse_dependency_index_lookups_separate": True,
            "per_hit_dependency_validation_checks_separate": True,
            "execution_steps_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v110_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_epoch_indexed_dependency_invalidation_verified": False,
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
        "preregistration_id": domains.extension_content_id_v110(
            domains.CONSTRUCTION_K7_EPOCH_INDEXED_QUOTIENT_PREREGISTRATION_V110_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class EpochIndexedQuotientPreregistrationV110:
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
            or domains.extension_content_id_v110(
                domains.CONSTRUCTION_K7_EPOCH_INDEXED_QUOTIENT_PREREGISTRATION_V110_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V110 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: EpochIndexedQuotientPreregistrationV110 | None = None


def freeze_epoch_indexed_quotient_preregistration_v110() -> EpochIndexedQuotientPreregistrationV110:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V110 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V110 frozen preregistration changed")
        _CACHE = EpochIndexedQuotientPreregistrationV110(_ISSUER, raw, identity)
    return _CACHE


def verify_epoch_indexed_quotient_preregistration_v110(
    value: Any,
) -> EpochIndexedQuotientPreregistrationV110:
    if type(value) is not EpochIndexedQuotientPreregistrationV110:
        _fail("V110 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_epoch_indexed_quotient_preregistration_v110()
    if value is not expected:
        _fail("V110 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v110",
    "freeze_epoch_indexed_quotient_preregistration_v110",
    "verify_epoch_indexed_quotient_preregistration_v110",
)
