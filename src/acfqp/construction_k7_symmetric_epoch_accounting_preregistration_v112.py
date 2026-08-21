"""Outcome-free preregistration for symmetric epoch accounting V112."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v112 as domains
from acfqp import construction_k7_identity_short_circuited_epoch_preregistration_v111 as previous
from acfqp.construction_k7_identity_short_circuited_epoch_campaign_v111 import (
    CAMPAIGN_ID as V111_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V111_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_identity_short_circuited_epoch_independent_verifier_v111 import (
    EXPECTED_CANONICAL_SHA256 as V111_VERIFICATION_SHA256,
    VERIFICATION_ID as V111_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("11d385a", "a329932")
PREREGISTRATION_ID = "f8e35e43014c8eb6b6d20f5f4101fbcacdd75ba0d263632fa656db9142032eda"
EXPECTED_CANONICAL_BYTE_COUNT = 17_763
EXPECTED_CANONICAL_SHA256 = "8c2ce5d22d931c197d60db7720c82345def42a07fd28cd7cfb777f734a9e4b8f"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_024_101),
    ("BALANCED_BATCH_REFINEMENT", 1_024_102),
    ("MAINTENANCE_CASCADE", 1_024_103),
    ("MAINTENANCE_CASCADE", 1_024_104),
)
TARGET_EPISODE_INDICES = (211, 212, 213)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v112.py",
        1586,
        "53e1e261f58f0062b40de61a3fde314735f48e562e9a1c4146856cbe96a42e55",
    ),
    (
        "src/acfqp/symmetric_epoch_accounting_campaign_core_v112.py",
        9915,
        "8b5b33bbe8087aee51d7e43343023f6f5d12dd1c27839f93567228948e4e25e0",
    ),
    (
        "src/acfqp/construction_k7_identity_short_circuited_epoch_campaign_v111.py",
        4913,
        "d6bfc5427b76af3f1292e5ed9e6bcbd67d85d3f3aa8333ee78f28f4d449030cb",
    ),
    (
        "src/acfqp/construction_k7_identity_short_circuited_epoch_independent_verifier_v111.py",
        42638,
        "58a36219dff796fd8bf5a78bc4fc609df7248bfc3c8475826def0854c61784e1",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7SymmetricEpochAccountingPreregistrationV112Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SymmetricEpochAccountingPreregistrationV112Error(message)


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


def campaign_config_v112() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v111())
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
        "schema": "acfqp.symmetric_epoch_accounting_preregistration.v112",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_failed_predecessor": {
            "v111_campaign_id": V111_CAMPAIGN_ID,
            "v111_campaign_sha256": V111_CAMPAIGN_SHA256,
            "v111_verification_id": V111_VERIFICATION_ID,
            "v111_verification_sha256": V111_VERIFICATION_SHA256,
            "v111_registered_gate_passed": False,
            "v111_passed_target_occurrence_count": 2,
            "v111_failure_reason": "TWO_CHANGED_GRAPH_OCCURRENCES_PAID_TWO_IDENTITY_CHECKS_ABSENT_FROM_THE_OLD_FULL_DIFF_BASELINE_ACCOUNTING",
            "v111_aggregate_maintenance_saved_against_old_full_diff": 666,
            "v111_aggregate_maintenance_saved_against_per_hit": 4242,
            "v111_actions_receipts_labels_and_steps_equal_baselines": True,
            "v111_failed_identity_retained_without_rerun": True,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v112_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V112),
            "frozen_before_any_registered_v112_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v112()["target_occurrences"],
            "target_seeds_unique": len({seed for _family, seed in TARGET_OCCURRENCES})
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "identity_short_algorithm_is_byte_identical_v111_path": True,
            "full_diff_baseline_charged_same_graph_identity_checks": True,
            "no_algorithm_action_outcome_label_or_step_changed_by_accounting_successor": True,
            "same_identity_short_circuits_full_diff": True,
            "changed_identity_matches_fully_accounted_full_diff_cost": True,
            "cache_only_orders_actions": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "matched_full_diff_per_hit_and_no_cache_arms_use_same_synthesizer": True,
            "all_matched_execution_actions_receipts_labels_and_steps_must_match": True,
            "identity_diff_reverse_index_per_hit_planning_labels_and_steps_separate": True,
            "local_ground_distinction_only_after_certificate_failure": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_execution_exactly_matches_all_baselines": True,
            "every_occurrence_planning_compute_below_no_cache": True,
            "every_occurrence_maintenance_below_per_hit_validation": True,
            "every_occurrence_not_above_symmetrically_accounted_full_diff": True,
            "aggregate_maintenance_below_symmetrically_accounted_full_diff": True,
            "at_least_one_identity_short_circuit_observed": True,
            "aggregate_quotient_labels_below_cold_direct": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "matched_identity_full_diff_per_hit_no_cache_and_direct_sequences_per_occurrence": 5,
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "both_identity_and_full_diff_arms_charge_graph_identity_checks": True,
            "initial_acquisition_and_certificate_local_labels_separate": True,
            "new_planning_compute_separate": True,
            "model_epoch_identity_checks_separate": True,
            "full_model_epoch_diff_checks_separate": True,
            "reverse_dependency_index_lookups_separate": True,
            "per_hit_dependency_validation_checks_separate": True,
            "execution_steps_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v112_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_symmetric_epoch_accounting_verified": False,
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
        "preregistration_id": domains.extension_content_id_v112(
            domains.CONSTRUCTION_K7_SYMMETRIC_EPOCH_ACCOUNTING_PREREGISTRATION_V112_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SymmetricEpochAccountingPreregistrationV112:
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
            or domains.extension_content_id_v112(
                domains.CONSTRUCTION_K7_SYMMETRIC_EPOCH_ACCOUNTING_PREREGISTRATION_V112_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V112 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: SymmetricEpochAccountingPreregistrationV112 | None = None


def freeze_symmetric_epoch_accounting_preregistration_v112() -> SymmetricEpochAccountingPreregistrationV112:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V112 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V112 frozen preregistration changed")
        _CACHE = SymmetricEpochAccountingPreregistrationV112(_ISSUER, raw, identity)
    return _CACHE


def verify_symmetric_epoch_accounting_preregistration_v112(
    value: Any,
) -> SymmetricEpochAccountingPreregistrationV112:
    if type(value) is not SymmetricEpochAccountingPreregistrationV112:
        _fail("V112 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_symmetric_epoch_accounting_preregistration_v112()
    if value is not expected:
        _fail("V112 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v112",
    "freeze_symmetric_epoch_accounting_preregistration_v112",
    "verify_symmetric_epoch_accounting_preregistration_v112",
)
