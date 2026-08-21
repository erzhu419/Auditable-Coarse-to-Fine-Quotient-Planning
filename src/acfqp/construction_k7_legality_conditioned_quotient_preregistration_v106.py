"""Outcome-free preregistration for legality-conditioned quotient V106."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v106 as domains
from acfqp import construction_k7_quotient_utilization_preregistration_v105 as previous
from acfqp.construction_k7_quotient_utilization_campaign_v105 import (
    CAMPAIGN_ID as V105_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V105_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_quotient_utilization_independent_verifier_v105 import (
    EXPECTED_CANONICAL_SHA256 as V105_VERIFICATION_SHA256,
    VERIFICATION_ID as V105_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("9521f1e", "ca53d71")
PREREGISTRATION_ID = "c020721354f8257c7d9aa202247c6d03d3fbe955f3d674097f6d29d978c413c5"
EXPECTED_CANONICAL_BYTE_COUNT = 11649
EXPECTED_CANONICAL_SHA256 = "5e2477cf273e21af0261e5509ae304f070ab2b3bdd80dd4cdcbcde1a53475d50"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_018_101),
    ("BALANCED_BATCH_REFINEMENT", 1_018_102),
    ("MAINTENANCE_CASCADE", 1_018_103),
    ("MAINTENANCE_CASCADE", 1_018_104),
)
TARGET_EPISODE_INDICES = (151, 152, 153)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v106.py",
        1599,
        "acad4f64df9affb9eb1ed5526f20d10b44a8d13418408874e47631e19f100594",
    ),
    (
        "src/acfqp/generic_legality_conditioned_quotient_planner_v106.py",
        5944,
        "189e0ebf95c703c9c93b142644ddb0ec5b9ea3f32811107c1c61099bb19ef4c9",
    ),
    (
        "src/acfqp/generic_actual_legality_conditioned_execution_receipt_v106.py",
        5286,
        "4ee1c01bf23649c94fff2679f8d21fa3a0f2c840edc583d997936c5a2c5c44f4",
    ),
    (
        "src/acfqp/generic_legality_conditioned_certificate_engine_v106.py",
        14269,
        "abccda8a738cd7a582059ac137e00e2e29b5c958819b5cd9156baa98d118db09",
    ),
    (
        "src/acfqp/generic_persistent_legality_conditioned_quotient_sequence_v106.py",
        11991,
        "c10a090ca7cebaa56a7ed146febf3d0b57ab7cd0d1b828b80791d6528e8b3945",
    ),
    (
        "src/acfqp/legality_conditioned_quotient_campaign_core_v106.py",
        13962,
        "6f83bd5e8c6a5d61a36b5d5fc6b23532683e836cd948c08e1c4bf20d3a477573",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7LegalityConditionedQuotientPreregistrationV106Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LegalityConditionedQuotientPreregistrationV106Error(message)


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


def campaign_config_v106() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v105())
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
        "schema": "acfqp.legality_conditioned_quotient_preregistration.v106",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {
            "v105_campaign_id": V105_CAMPAIGN_ID,
            "v105_campaign_sha256": V105_CAMPAIGN_SHA256,
            "v105_verification_id": V105_VERIFICATION_ID,
            "v105_verification_sha256": V105_VERIFICATION_SHA256,
            "v105_registered_gate_passed": True,
            "v105_execution_step_count": 73,
            "v105_quotient_proposal_admitted_execution_count": 55,
            "v105_chosen_action_match_count": 51,
            "v105_quotient_lifetime_target_labels": 230,
            "v105_cold_direct_lifetime_target_labels": 513,
            "v105_remaining_no_quotient_order_count": 18,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v106_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V106),
            "frozen_before_any_registered_v106_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v106()["target_occurrences"],
            "target_seeds_unique": len(
                {seed for _family, seed in TARGET_OCCURRENCES}
            )
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "observation_derived_quotient_graph_remains_primary_transition_program": True,
            "certified_legality_visible_to_abstract_planner_as_initial_action_constraint": True,
            "legality_must_be_preloaded_or_acquired_after_a_failed_certificate": True,
            "certificate_local_legality_labels_not_recharged_as_model_labels": True,
            "illegal_initial_actions_forbidden_before_abstract_search": True,
            "ground_transition_accessed_during_abstract_search": False,
            "every_projected_observation_edge_checked_by_compiled_factor_program": True,
            "residual_coordinates_quotiented_out_not_imputed": True,
            "later_graph_updates_only_use_local_rows_acquired_after_certificate_failure": True,
            "exact_overlay_exclusively_discharges_safety": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_action_receipt_replays_independently": True,
            "every_occurrence_quotient_orders_at_least_three_quarters_of_actions": True,
            "every_occurrence_chosen_action_match_strict_majority": True,
            "every_occurrence_uses_certificate_local_legality_in_abstract_planning": True,
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
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "initial_acquisition_and_certificate_local_labels_separate": True,
            "legality_context_reuses_already_charged_exact_support": True,
            "quotient_and_cold_direct_target_labels_separate": True,
            "execution_steps_separate": True,
            "derivation_and_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v106_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_execution_primarily_ordered_by_legality_conditioned_quotient": False,
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
        "preregistration_id": domains.extension_content_id_v106(
            domains.CONSTRUCTION_K7_LEGALITY_CONDITIONED_QUOTIENT_PREREGISTRATION_V106_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LegalityConditionedQuotientPreregistrationV106:
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
            or domains.extension_content_id_v106(
                domains.CONSTRUCTION_K7_LEGALITY_CONDITIONED_QUOTIENT_PREREGISTRATION_V106_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V106 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: LegalityConditionedQuotientPreregistrationV106 | None = None


def freeze_legality_conditioned_quotient_preregistration_v106() -> LegalityConditionedQuotientPreregistrationV106:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V106 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V106 frozen preregistration changed")
        _CACHE = LegalityConditionedQuotientPreregistrationV106(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_legality_conditioned_quotient_preregistration_v106(
    value: Any,
) -> LegalityConditionedQuotientPreregistrationV106:
    if type(value) is not LegalityConditionedQuotientPreregistrationV106:
        _fail("V106 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_legality_conditioned_quotient_preregistration_v106()
    if value is not expected:
        _fail("V106 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v106",
    "freeze_legality_conditioned_quotient_preregistration_v106",
    "verify_legality_conditioned_quotient_preregistration_v106",
)
