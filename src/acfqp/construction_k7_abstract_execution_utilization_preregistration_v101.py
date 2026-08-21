"""Outcome-free preregistration for abstract execution utilization V101."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v101 as domains
from acfqp import construction_k7_sequence_wide_agreement_shielded_preregistration_v100 as previous
from acfqp.construction_k7_sequence_wide_agreement_shielded_campaign_v100 import (
    CAMPAIGN_ID as V100_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V100_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_sequence_wide_agreement_shielded_independent_verifier_v100 import (
    EXPECTED_CANONICAL_SHA256 as V100_VERIFICATION_SHA256,
    VERIFICATION_ID as V100_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("5c413d2",)
PREREGISTRATION_ID = "336139087db95530d912e3a3b027d14eb0e8aa4cbfc350fd979245107cc9ac9e"
EXPECTED_CANONICAL_BYTE_COUNT = 7_377
EXPECTED_CANONICAL_SHA256 = "b60a8972774032b4dd036942bb1091fd7c018d35b18a8104b2d5017b93e92e71"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_011_101),
    ("BALANCED_BATCH_REFINEMENT", 1_011_102),
    ("MAINTENANCE_CASCADE", 1_011_103),
    ("MAINTENANCE_CASCADE", 1_011_104),
)
TARGET_EPISODE_INDICES = (101, 102, 103)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v101.py", 1799, "2f67fea97b36e928d8e48a16f470e30c5687a0dd9331156d3c013883ce077774"),
    ("src/acfqp/abstract_execution_utilization_campaign_core_v101.py", 11723, "723190712d36d47e7b85b68c9e963d3c19dc685cbc3452ee08a22394271dc076"),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7AbstractExecutionUtilizationPreregistrationV101Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractExecutionUtilizationPreregistrationV101Error(
        message
    )


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": relative,
            "byte_count": len((SOURCE_ROOT / relative).read_bytes()),
            "sha256": hashlib.sha256(
                (SOURCE_ROOT / relative).read_bytes()
            ).hexdigest(),
        }
        for relative, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v101() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v100())
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
        "schema": "acfqp.abstract_execution_utilization_preregistration.v101",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {
            "v100_campaign_id": V100_CAMPAIGN_ID,
            "v100_campaign_sha256": V100_CAMPAIGN_SHA256,
            "v100_verification_id": V100_VERIFICATION_ID,
            "v100_verification_sha256": V100_VERIFICATION_SHA256,
            "v100_registered_gate_passed": True,
            "v99_registered_failure_remains_retained": True,
            "source_library_artifact_id": previous.SOURCE_LIBRARY_ARTIFACT_ID,
            "v62_residual_library_id": previous.V62_LIBRARY_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v101_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V101),
            "frozen_before_any_registered_v101_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v101()["target_occurrences"],
            "target_seeds_unique": len(
                {seed for _family, seed in TARGET_OCCURRENCES}
            )
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "frozen_v99_planner_and_v100_gate_reused_without_change": True,
            "only_new_measurement": "EXECUTED_ACTION_MATCHES_ABSTRACT_PROPOSAL",
            "execution_match_requires_abstract_partial_exact_action_agreement": True,
            "search_receipts_are_not_counted_as_executed_actions": True,
            "exact_overlay_exclusively_discharges_safety": True,
            "every_new_ground_query_must_follow_failed_certificate": True,
            "same_partial_rows_outcomes_synthesizer_stopping_rule_and_shield_between_arms": True,
            "strict_incompatible_schema_receives_no_transfer": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_meta_abstract_matches_strict_majority_of_executed_actions": True,
            "aggregate_meta_abstract_matches_strict_majority_of_executed_actions": True,
            "meta_execution_match_rate_noninferior_to_matched_no_prior": True,
            "every_occurrence_sequence_wide_v100_gate_must_pass": True,
            "aggregate_activation_sample_tax_must_be_strictly_reduced": True,
            "aggregate_meta_task_labels_must_not_exceed_no_prior": True,
            "aggregate_meta_task_labels_must_be_strictly_below_cold_direct": True,
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
            "meta_no_prior_and_direct_target_labels_separate": True,
            "execution_steps_separate": True,
            "derivation_shield_and_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v101_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_multistep_execution_primarily_abstract_ordered_verified": False,
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
        "preregistration_id": domains.extension_content_id_v101(
            domains.CONSTRUCTION_K7_ABSTRACT_EXECUTION_UTILIZATION_PREREGISTRATION_V101_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AbstractExecutionUtilizationPreregistrationV101:
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
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v101(
                domains.CONSTRUCTION_K7_ABSTRACT_EXECUTION_UTILIZATION_PREREGISTRATION_V101_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V101 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


_CACHE: AbstractExecutionUtilizationPreregistrationV101 | None = None


def freeze_abstract_execution_utilization_preregistration_v101(
) -> AbstractExecutionUtilizationPreregistrationV101:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V101 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V101 frozen preregistration changed")
        _CACHE = AbstractExecutionUtilizationPreregistrationV101(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_abstract_execution_utilization_preregistration_v101(
    value: Any,
) -> AbstractExecutionUtilizationPreregistrationV101:
    if type(value) is not AbstractExecutionUtilizationPreregistrationV101:
        _fail("V101 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_abstract_execution_utilization_preregistration_v101()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V101 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v101",
    "freeze_abstract_execution_utilization_preregistration_v101",
    "verify_abstract_execution_utilization_preregistration_v101",
)
