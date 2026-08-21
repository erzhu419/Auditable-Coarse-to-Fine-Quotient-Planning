"""Outcome-free preregistration for identity-short-circuited epochs V111."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v111 as domains
from acfqp import construction_k7_epoch_indexed_quotient_preregistration_v110 as previous
from acfqp.construction_k7_epoch_indexed_quotient_campaign_v110 import (
    CAMPAIGN_ID as V110_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V110_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_epoch_indexed_quotient_independent_verifier_v110 import (
    EXPECTED_CANONICAL_SHA256 as V110_VERIFICATION_SHA256,
    VERIFICATION_ID as V110_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("b703255", "24f271c")
PREREGISTRATION_ID = "22642fa7df8eb182748bdb821f8a8d8281f274379565ddf63acc191b175465f7"
EXPECTED_CANONICAL_BYTE_COUNT = 17_725
EXPECTED_CANONICAL_SHA256 = "b90446d6b98b31cd171eaf06d39157e0351ec84049c2e3d61c617eeca4780d54"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_023_101),
    ("BALANCED_BATCH_REFINEMENT", 1_023_102),
    ("MAINTENANCE_CASCADE", 1_023_103),
    ("MAINTENANCE_CASCADE", 1_023_104),
)
TARGET_EPISODE_INDICES = (201, 202, 203)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v111.py",
        1782,
        "8aa49cdd4d3e5cbd8c3c077145104bc76048544b8366a5ac867b239a9f82faa4",
    ),
    (
        "src/acfqp/generic_identity_short_circuited_epoch_sequence_v111.py",
        16363,
        "9de4e66af2d27fb46139354b4616ace29caa33fe442ffebbcb633828be8fd1e4",
    ),
    (
        "src/acfqp/identity_short_circuited_epoch_campaign_core_v111.py",
        16040,
        "6f3dd650a919227b0f47fdb3e217908cd3a4da332cff82cb9e612707b9a7efa9",
    ),
    (
        "src/acfqp/construction_k7_epoch_indexed_quotient_campaign_v110.py",
        4778,
        "cacc6c90ce88d92c6179f864c4243809762b07ae55c0aff00683164940f3244c",
    ),
    (
        "src/acfqp/construction_k7_epoch_indexed_quotient_independent_verifier_v110.py",
        45590,
        "f8f66496d197feeb70d7665fe50caab637b32b11a795404659fcec29734590a8",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7IdentityShortCircuitedEpochPreregistrationV111Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7IdentityShortCircuitedEpochPreregistrationV111Error(
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


def campaign_config_v111() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v110())
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
        "schema": "acfqp.identity_short_circuited_epoch_preregistration.v111",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_failed_predecessor": {
            "v110_campaign_id": V110_CAMPAIGN_ID,
            "v110_campaign_sha256": V110_CAMPAIGN_SHA256,
            "v110_verification_id": V110_VERIFICATION_ID,
            "v110_verification_sha256": V110_VERIFICATION_SHA256,
            "v110_registered_gate_passed": False,
            "v110_passed_target_occurrence_count": 3,
            "v110_failure_reason": "ONE_SMALL_MAINTENANCE_OCCURRENCE_EPOCH_MAINTENANCE_EXCEEDED_PER_HIT_VALIDATION_BY_TWO_EVENTS",
            "v110_failed_occurrence": {
                "family": "MAINTENANCE_CASCADE",
                "seed": 1_022_103,
                "epoch_maintenance_events": 346,
                "per_hit_validation_events": 344,
            },
            "v110_aggregate_maintenance_events_avoided": 2358,
            "v110_actions_receipts_labels_and_steps_equal_baselines": True,
            "v110_failed_identity_retained_without_rerun": True,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v111_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V111),
            "frozen_before_any_registered_v111_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v111()["target_occurrences"],
            "target_seeds_unique": len({seed for _family, seed in TARGET_OCCURRENCES})
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "quotient_graph_id_is_content_address_of_complete_compiled_graph": True,
            "same_graph_identity_skips_full_graph_and_dependency_scan": True,
            "changed_graph_identity_runs_exact_v110_delta_and_reverse_index": True,
            "terminal_rows_are_bound_inside_quotient_graph_identity": True,
            "only_changed_dependency_slices_are_invalidated": True,
            "retained_cache_hits_do_not_rescan_dependency_rows": True,
            "cache_only_orders_actions": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "matched_full_diff_per_hit_and_no_cache_arms_use_same_synthesizer": True,
            "all_matched_execution_actions_receipts_labels_and_steps_must_match": True,
            "identity_diff_reverse_index_per_hit_planning_labels_and_steps_separate": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "ground_transition_accessed_during_epoch_invalidation": False,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_execution_exactly_matches_all_baselines": True,
            "every_occurrence_planning_compute_below_no_cache": True,
            "every_occurrence_maintenance_below_per_hit_validation": True,
            "aggregate_maintenance_below_full_diff": True,
            "at_least_one_identity_short_circuit_observed": True,
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
            "matched_identity_full_diff_per_hit_no_cache_and_direct_sequences_per_occurrence": 5,
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "matched_baseline_labels_not_charged_to_identity_short_arm": True,
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
            "registered_v111_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_identity_short_circuited_epoch_invalidation_verified": False,
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
        "preregistration_id": domains.extension_content_id_v111(
            domains.CONSTRUCTION_K7_IDENTITY_SHORT_CIRCUITED_EPOCH_PREREGISTRATION_V111_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class IdentityShortCircuitedEpochPreregistrationV111:
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
            or domains.extension_content_id_v111(
                domains.CONSTRUCTION_K7_IDENTITY_SHORT_CIRCUITED_EPOCH_PREREGISTRATION_V111_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V111 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: IdentityShortCircuitedEpochPreregistrationV111 | None = None


def freeze_identity_short_circuited_epoch_preregistration_v111() -> IdentityShortCircuitedEpochPreregistrationV111:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V111 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V111 frozen preregistration changed")
        _CACHE = IdentityShortCircuitedEpochPreregistrationV111(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_identity_short_circuited_epoch_preregistration_v111(
    value: Any,
) -> IdentityShortCircuitedEpochPreregistrationV111:
    if type(value) is not IdentityShortCircuitedEpochPreregistrationV111:
        _fail("V111 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_identity_short_circuited_epoch_preregistration_v111()
    if value is not expected:
        _fail("V111 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v111",
    "freeze_identity_short_circuited_epoch_preregistration_v111",
    "verify_identity_short_circuited_epoch_preregistration_v111",
)
