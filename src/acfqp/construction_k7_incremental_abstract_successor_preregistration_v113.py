"""Outcome-free preregistration for incremental abstract successors V113."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v113 as domains
from acfqp import construction_k7_symmetric_epoch_accounting_preregistration_v112 as previous
from acfqp.construction_k7_symmetric_epoch_accounting_campaign_v112 import (
    CAMPAIGN_ID as V112_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V112_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_symmetric_epoch_accounting_independent_verifier_v112 import (
    EXPECTED_CANONICAL_SHA256 as V112_VERIFICATION_SHA256,
    VERIFICATION_ID as V112_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("1bef68a", "66023b6", "797a478")
PREREGISTRATION_ID = "26e52284ee6c7bb0a3a101b9c12f4517af64ab5323b6fd1449ae051bb032f9d9"
EXPECTED_CANONICAL_BYTE_COUNT = 19_656
EXPECTED_CANONICAL_SHA256 = "0788260e0888461ea4c96e7582ffb889bc12c1f027a37465d66ad314f65773ea"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_025_101),
    ("BALANCED_BATCH_REFINEMENT", 1_025_102),
    ("MAINTENANCE_CASCADE", 1_025_103),
    ("MAINTENANCE_CASCADE", 1_025_104),
)
TARGET_EPISODE_INDICES = (221, 222, 223)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v113.py",
        1955,
        "b72778facd571c434370b7a408d89b8b197693e1e5ed7241e29279ce5e47e343",
    ),
    (
        "src/acfqp/generic_incremental_abstract_successor_v113.py",
        33566,
        "2e1d281bf1fef638da083bf2463d01600c15a5491fb565268e891ad42d9b4885",
    ),
    (
        "src/acfqp/generic_incremental_abstract_successor_sequence_v113.py",
        18474,
        "24e4100594ee63578bb73bc5a50227d914e073671234653dbabd1e350ec35340",
    ),
    (
        "src/acfqp/incremental_abstract_successor_campaign_core_v113.py",
        13959,
        "0cae2d6ccab32d58237f6656e68c758fd04fd29dfd960ae84f5e88d9f6ff6a03",
    ),
    (
        "src/acfqp/construction_k7_symmetric_epoch_accounting_preregistration_v112.py",
        11678,
        "78f1e9304efed0aff75004d6d8ed5e2543d1e0f4aa7518d773aec613b76bf0ab",
    ),
    (
        "src/acfqp/construction_k7_symmetric_epoch_accounting_campaign_v112.py",
        4875,
        "579df6bb7b9e3f76c0aecfbd41abf70231bc823e82ef11e65f6374bf4be206db",
    ),
    (
        "src/acfqp/construction_k7_symmetric_epoch_accounting_independent_verifier_v112.py",
        16794,
        "3e6a904fd72a00433326447fa0d3e785a459e202f07d450ee17226093301bb98",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7IncrementalAbstractSuccessorPreregistrationV113Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7IncrementalAbstractSuccessorPreregistrationV113Error(
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


def campaign_config_v113() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v112())
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
        "schema": "acfqp.incremental_abstract_successor_preregistration.v113",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v112_campaign_id": V112_CAMPAIGN_ID,
            "v112_campaign_sha256": V112_CAMPAIGN_SHA256,
            "v112_verification_id": V112_VERIFICATION_ID,
            "v112_verification_sha256": V112_VERIFICATION_SHA256,
            "v112_registered_gate_passed": True,
            "v112_target_labels": 269,
            "v112_cold_direct_labels": 555,
            "v112_identity_short_maintenance_events": 1829,
            "v112_fully_accounted_full_diff_events": 2303,
            "v112_per_hit_validation_events": 5301,
            "v112_predecessor_bytes_and_identity_retained": True,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v113_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V113),
            "frozen_before_any_registered_v113_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v113()["target_occurrences"],
            "target_seeds_unique": len({seed for _family, seed in TARGET_OCCURRENCES})
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "initial_observations_compile_one_full_v105_bootstrap": True,
            "certificate_local_delta_rows_are_the_only_incremental_model_inputs": True,
            "only_novel_raw_rows_are_projected_after_bootstrap": True,
            "incremental_edges_terminal_classes_contexts_and_acceptance_values_are_union_updated": True,
            "every_incremental_model_and_terminal_rule_must_equal_fresh_full_rebuild": True,
            "abstract_planner_consumes_compiled_model_without_raw_transition_argument": True,
            "matched_full_rebuild_planner_uses_same_candidate_actions_and_queries": True,
            "all_actions_plans_receipts_labels_steps_and_dependency_maintenance_must_match": True,
            "compiled_model_only_orders_actions": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_execution_exactly_matches_full_rebuild": True,
            "every_occurrence_model_bytes_equal_full_v105_rebuild": True,
            "every_occurrence_planner_has_no_raw_transition_argument": True,
            "every_occurrence_incremental_update_compilation_below_full_rebuild": True,
            "aggregate_incremental_update_compilation_below_full_rebuild": True,
            "every_occurrence_certificate_failure_only_query_discipline_clean": True,
            "aggregate_quotient_labels_below_cold_direct": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "matched_incremental_full_rebuild_cache_baselines_and_direct_sequences_per_occurrence": 6,
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "initial_acquisition_and_certificate_local_labels_separate": True,
            "execution_steps_separate": True,
            "derivation_compute_separate": True,
            "abstract_planning_compute_separate": True,
            "dependency_maintenance_separate": True,
            "bootstrap_compilation_separate": True,
            "incremental_model_update_compilation_separate": True,
            "matched_full_rebuild_compilation_separate": True,
            "matched_control_compute_not_charged_to_incremental_arm": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v113_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_incremental_abstract_successor_verified": False,
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
        "preregistration_id": domains.extension_content_id_v113(
            domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_PREREGISTRATION_V113_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class IncrementalAbstractSuccessorPreregistrationV113:
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
            or domains.extension_content_id_v113(
                domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_PREREGISTRATION_V113_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V113 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: IncrementalAbstractSuccessorPreregistrationV113 | None = None


def freeze_incremental_abstract_successor_preregistration_v113() -> IncrementalAbstractSuccessorPreregistrationV113:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V113 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V113 frozen preregistration changed")
        _CACHE = IncrementalAbstractSuccessorPreregistrationV113(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_incremental_abstract_successor_preregistration_v113(
    value: Any,
) -> IncrementalAbstractSuccessorPreregistrationV113:
    if type(value) is not IncrementalAbstractSuccessorPreregistrationV113:
        _fail("V113 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_incremental_abstract_successor_preregistration_v113()
    if value is not expected:
        _fail("V113 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v113",
    "freeze_incremental_abstract_successor_preregistration_v113",
    "verify_incremental_abstract_successor_preregistration_v113",
)
