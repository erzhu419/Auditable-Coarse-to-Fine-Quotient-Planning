"""Outcome-free preregistration for catalogue-closed quotient V107."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v107 as domains
from acfqp import construction_k7_legality_conditioned_quotient_preregistration_v106 as previous
from acfqp.construction_k7_legality_conditioned_quotient_campaign_v106 import (
    CAMPAIGN_ID as V106_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V106_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_legality_conditioned_quotient_independent_verifier_v106 import (
    EXPECTED_CANONICAL_SHA256 as V106_VERIFICATION_SHA256,
    VERIFICATION_ID as V106_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("87838bc", "d4dd0eb")
PREREGISTRATION_ID = "38b7e1adc4392decd5d07e47f4384173a3709c9c14e0f0d8fdec903820126fb8"
EXPECTED_CANONICAL_BYTE_COUNT = 12_874
EXPECTED_CANONICAL_SHA256 = "bd4ab627b88b9874fb754d110c71710b803a658d52075449c144dfbf86000556"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_019_101),
    ("BALANCED_BATCH_REFINEMENT", 1_019_102),
    ("MAINTENANCE_CASCADE", 1_019_103),
    ("MAINTENANCE_CASCADE", 1_019_104),
)
TARGET_EPISODE_INDICES = (161, 162, 163)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v107.py",
        1728,
        "e4a15bae77971551abfb300c2ebd628b791e1d60693c34d3c045af5576a63d3c",
    ),
    (
        "src/acfqp/generic_complete_anonymous_action_catalogue_receipt_v107.py",
        3565,
        "d29620b082e15e09d6c645f1b542d93090c03ae21e99f17b686b273243ac6bfd",
    ),
    (
        "src/acfqp/catalogue_closed_legality_conditioned_quotient_campaign_core_v107.py",
        12096,
        "9860930415d0dd5018bd27ecf5527b249f93d260f8cbd31718b3924119705d34",
    ),
    (
        "src/acfqp/construction_k7_legality_conditioned_quotient_campaign_v106.py",
        5065,
        "837015154463e77733719d423fbe7e14da8f70bc4886d81b27fdcbbd4b8eb2a1",
    ),
    (
        "src/acfqp/construction_k7_legality_conditioned_quotient_independent_verifier_v106.py",
        58185,
        "f56dfe63c79077f9373cc47eb2c55a3a516feea851a0cb5b933808cbd7db65c9",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7CatalogueClosedLegalityQuotientPreregistrationV107Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CatalogueClosedLegalityQuotientPreregistrationV107Error(
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


def campaign_config_v107() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v106())
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
        "schema": "acfqp.catalogue_closed_legality_quotient_preregistration.v107",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_failed_predecessor": {
            "v106_campaign_id": V106_CAMPAIGN_ID,
            "v106_campaign_sha256": V106_CAMPAIGN_SHA256,
            "v106_verification_id": V106_VERIFICATION_ID,
            "v106_verification_sha256": V106_VERIFICATION_SHA256,
            "v106_registered_gate_passed": False,
            "v106_execution_step_count": 65,
            "v106_quotient_proposal_admitted_execution_count": 65,
            "v106_chosen_action_match_count": 53,
            "v106_quotient_lifetime_target_labels": 258,
            "v106_cold_direct_lifetime_target_labels": 588,
            "v106_fallback_plan_receipts_without_catalogue_closure": 128,
            "v106_actual_receipts_using_unreconstructable_fallback": 6,
            "failed_predecessor_retained_without_reclassification": True,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v107_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V107),
            "frozen_before_any_registered_v107_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v107()["target_occurrences"],
            "target_seeds_unique": len(
                {seed for _family, seed in TARGET_OCCURRENCES}
            )
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "complete_anonymous_action_catalogue_is_outcome_free_planner_input": True,
            "catalogue_enumerated_before_target_episode_outcomes": True,
            "catalogue_contains_no_transition_outcomes": True,
            "fallback_search_must_use_receipted_catalogue_order_and_descriptors": True,
            "observation_quotient_graph_remains_primary_transition_program": True,
            "certified_legality_is_initial_action_boundary_only": True,
            "certificate_local_legality_may_be_absent_when_preloaded_support_suffices": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "ground_transition_accessed_during_abstract_search": False,
            "exact_overlay_exclusively_discharges_safety": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_catalogue_closed": True,
            "every_occurrence_quotient_orders_at_least_three_quarters": True,
            "every_occurrence_chosen_action_match_strict_majority": True,
            "aggregate_certificate_local_legality_path_observed": True,
            "no_occurrence_forced_to_manufacture_local_legality_failure": True,
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
            "catalogue_metadata_not_counted_as_ground_transition_labels": True,
            "initial_acquisition_and_certificate_local_labels_separate": True,
            "quotient_and_cold_direct_target_labels_separate": True,
            "execution_steps_separate": True,
            "derivation_and_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v107_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_catalogue_closed_quotient_verified": False,
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
        "preregistration_id": domains.extension_content_id_v107(
            domains.CONSTRUCTION_K7_CATALOGUE_CLOSED_LEGALITY_QUOTIENT_PREREGISTRATION_V107_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CatalogueClosedLegalityQuotientPreregistrationV107:
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
            or domains.extension_content_id_v107(
                domains.CONSTRUCTION_K7_CATALOGUE_CLOSED_LEGALITY_QUOTIENT_PREREGISTRATION_V107_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V107 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: CatalogueClosedLegalityQuotientPreregistrationV107 | None = None


def freeze_catalogue_closed_legality_quotient_preregistration_v107() -> CatalogueClosedLegalityQuotientPreregistrationV107:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V107 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V107 frozen preregistration changed")
        _CACHE = CatalogueClosedLegalityQuotientPreregistrationV107(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_catalogue_closed_legality_quotient_preregistration_v107(
    value: Any,
) -> CatalogueClosedLegalityQuotientPreregistrationV107:
    if type(value) is not CatalogueClosedLegalityQuotientPreregistrationV107:
        _fail("V107 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_catalogue_closed_legality_quotient_preregistration_v107()
    if value is not expected:
        _fail("V107 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v107",
    "freeze_catalogue_closed_legality_quotient_preregistration_v107",
    "verify_catalogue_closed_legality_quotient_preregistration_v107",
)
