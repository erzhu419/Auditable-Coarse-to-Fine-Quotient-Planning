"""Outcome-free preregistration for identity-bound plan memoization V108."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v108 as domains
from acfqp import construction_k7_catalogue_closed_legality_quotient_preregistration_v107 as previous
from acfqp.construction_k7_catalogue_closed_legality_quotient_campaign_v107 import (
    CAMPAIGN_ID as V107_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V107_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_catalogue_closed_legality_quotient_independent_verifier_v107 import (
    EXPECTED_CANONICAL_SHA256 as V107_VERIFICATION_SHA256,
    VERIFICATION_ID as V107_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("24fd797", "22f4976")
PREREGISTRATION_ID = "5a423ffdf36b592f12abfc5767e19ecc2af9e3db8e7aeb6e0179b8a634c09ad1"
EXPECTED_CANONICAL_BYTE_COUNT = 13_699
EXPECTED_CANONICAL_SHA256 = "afac699841127e4260a7299c5e08ffd4fe8ff442821e9cffd3d464db7f6929e8"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_020_101),
    ("BALANCED_BATCH_REFINEMENT", 1_020_102),
    ("MAINTENANCE_CASCADE", 1_020_103),
    ("MAINTENANCE_CASCADE", 1_020_104),
)
TARGET_EPISODE_INDICES = (171, 172, 173)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v108.py",
        1671,
        "4f27a2476dbeefc769feb478a156fb32a05dcaa2ef2e0827415e407d93f24708",
    ),
    (
        "src/acfqp/generic_persistent_memoized_catalogue_quotient_sequence_v108.py",
        15270,
        "6d1f2ad10cb0e05099caa7add4669114eb505ffc67965013098890886e8f21f4",
    ),
    (
        "src/acfqp/memoized_catalogue_quotient_campaign_core_v108.py",
        12416,
        "d502b7e5a291440c3ad36fff91588e82c6a6ef332c54c804caafa0d77e33138a",
    ),
    (
        "src/acfqp/construction_k7_catalogue_closed_legality_quotient_campaign_v107.py",
        5194,
        "adaafd7744dace97c6a7d93964625824f2fc37d4417d7aedb7ca98cf1e9fec7e",
    ),
    (
        "src/acfqp/construction_k7_catalogue_closed_legality_quotient_independent_verifier_v107.py",
        29707,
        "b6d3d655c6cef5e076320b9bb33e700dff245362c5356bed8d0cec5a4113dbc4",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7MemoizedCatalogueQuotientPreregistrationV108Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7MemoizedCatalogueQuotientPreregistrationV108Error(message)


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


def campaign_config_v108() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v107())
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
        "schema": "acfqp.memoized_catalogue_quotient_preregistration.v108",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {
            "v107_campaign_id": V107_CAMPAIGN_ID,
            "v107_campaign_sha256": V107_CAMPAIGN_SHA256,
            "v107_verification_id": V107_VERIFICATION_ID,
            "v107_verification_sha256": V107_VERIFICATION_SHA256,
            "v107_registered_gate_passed": True,
            "v107_execution_step_count": 60,
            "v107_quotient_lifetime_target_labels": 306,
            "v107_cold_direct_lifetime_target_labels": 534,
            "v107_abstract_planning_compute_events": 1_836_658,
            "v107_verified_abstract_plan_receipt_count": 417,
            "v107_verified_fallback_plan_receipt_count": 120,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v108_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V108),
            "frozen_before_any_registered_v108_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v108()["target_occurrences"],
            "target_seeds_unique": len(
                {seed for _family, seed in TARGET_OCCURRENCES}
            )
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "memoization_key_includes_model_projection_exact_legality_and_provenance": True,
            "cache_lifetime_is_one_occurrence_and_never_crosses_catalogue_identity": True,
            "cache_hit_returns_identical_content_addressed_plan": True,
            "matched_no_cache_arm_uses_same_synthesizer_planner_and_stopping_rule": True,
            "memoized_and_no_cache_actions_receipts_and_labels_must_match_exactly": True,
            "only_actual_new_planner_evaluations_counted_on_memoized_axis": True,
            "sample_labels_execution_steps_and_planning_compute_remain_separate": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "ground_transition_accessed_during_abstract_search": False,
            "exact_overlay_exclusively_discharges_safety": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_actions_and_receipts_equal_no_cache": True,
            "every_occurrence_labels_equal_no_cache": True,
            "every_occurrence_planning_compute_strictly_reduced": True,
            "every_occurrence_cache_hit_observed": True,
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
            "matched_memoized_and_no_cache_sequences_per_occurrence": 2,
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "matched_no_cache_labels_are_baseline_not_charged_to_memoized_arm": True,
            "initial_acquisition_and_certificate_local_labels_separate": True,
            "memoized_and_no_cache_planning_compute_separate": True,
            "execution_steps_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v108_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_identity_bound_memoization_verified": False,
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
        "preregistration_id": domains.extension_content_id_v108(
            domains.CONSTRUCTION_K7_MEMOIZED_CATALOGUE_QUOTIENT_PREREGISTRATION_V108_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class MemoizedCatalogueQuotientPreregistrationV108:
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
            or domains.extension_content_id_v108(
                domains.CONSTRUCTION_K7_MEMOIZED_CATALOGUE_QUOTIENT_PREREGISTRATION_V108_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V108 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: MemoizedCatalogueQuotientPreregistrationV108 | None = None


def freeze_memoized_catalogue_quotient_preregistration_v108() -> MemoizedCatalogueQuotientPreregistrationV108:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V108 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V108 frozen preregistration changed")
        _CACHE = MemoizedCatalogueQuotientPreregistrationV108(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_memoized_catalogue_quotient_preregistration_v108(
    value: Any,
) -> MemoizedCatalogueQuotientPreregistrationV108:
    if type(value) is not MemoizedCatalogueQuotientPreregistrationV108:
        _fail("V108 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_memoized_catalogue_quotient_preregistration_v108()
    if value is not expected:
        _fail("V108 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v108",
    "freeze_memoized_catalogue_quotient_preregistration_v108",
    "verify_memoized_catalogue_quotient_preregistration_v108",
)
