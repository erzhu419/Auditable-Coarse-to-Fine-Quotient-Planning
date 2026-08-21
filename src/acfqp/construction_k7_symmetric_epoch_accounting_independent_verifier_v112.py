"""Producer-free V112 replay with episode-bound frozen V111 verifier code."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v112 as domains
from acfqp import construction_k7_identity_short_circuited_epoch_independent_verifier_v111 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "9c77611e946310fb08ba1d22afe11326b975f0087c3b2712d39fc2899e09b2a4"
CAMPAIGN_BYTE_COUNT = 18_417_315
CAMPAIGN_SHA256 = "9c299ce8ed67ba6a8201d2b780b7a76a5cfef888733c5560c160a0d272e1c899"
PREREGISTRATION_ID = "f8e35e43014c8eb6b6d20f5f4101fbcacdd75ba0d263632fa656db9142032eda"
V111_CAMPAIGN_ID = "378f333008191bdb338182c787547aeb80f4fa27b612f499043b20163a6327f5"
V111_VERIFICATION_ID = "e648b69d758ba92816777d5a7f1ea9eee1663c6a6bed1a2585f7e0d8f5814184"
V111_VERIFIER_SOURCE_SHA256 = "58a36219dff796fd8bf5a78bc4fc609df7248bfc3c8475826def0854c61784e1"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_024_101),
    ("BALANCED_BATCH_REFINEMENT", 1_024_102),
    ("MAINTENANCE_CASCADE", 1_024_103),
    ("MAINTENANCE_CASCADE", 1_024_104),
)
EPISODES = (211, 212, 213)
VERIFICATION_ID = "b96f2b0ba6a77ecc61b3f632c7104ac89b564b149466cc570cfeb13d247b8312"
EXPECTED_CANONICAL_BYTE_COUNT = 8_476
EXPECTED_CANONICAL_SHA256 = "e3f09a37e1d661baa7101c3677ae14ea818f7564e1806a135d2bbee6d11b48ef"


class ConstructionK7SymmetricEpochAccountingIndependentVerifierV112Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SymmetricEpochAccountingIndependentVerifierV112Error(
        message
    )


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V112 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v112(domain, payload):
        _fail(f"V112 {key} changed")


def _episode_bound_v111_occurrence_verifier():
    source = Path(previous.__file__).read_bytes()
    if (
        hashlib.sha256(source).hexdigest() != V111_VERIFIER_SOURCE_SHA256
        or previous.EPISODES != (201, 202, 203)
        or previous.VERIFICATION_ID != V111_VERIFICATION_ID
    ):
        _fail("V112 frozen V111 verifier source or constants changed")
    namespace = dict(previous.__dict__)
    namespace["EPISODES"] = EPISODES
    originals = {
        name: value
        for name, value in previous.__dict__.items()
        if type(value) is FunctionType and value.__module__ == previous.__name__
    }
    for name, value in originals.items():
        clone = FunctionType(
            value.__code__,
            namespace,
            name=value.__name__,
            argdefs=value.__defaults__,
            closure=value.__closure__,
        )
        clone.__kwdefaults__ = value.__kwdefaults__
        namespace[name] = clone
    return namespace["_occurrence"]


def _occurrence(
    document: Any,
    family: str,
    seed: int,
    replay_v111_occurrence,
) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_SYMMETRIC_EPOCH_ACCOUNTING_OCCURRENCE_V112_DOMAIN,
    )
    raw = document.get("v111_raw_occurrence")
    if (
        document.get("schema") != "acfqp.symmetric_epoch_accounting_occurrence.v112"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or type(raw) is not dict
        or document.get("v111_raw_occurrence_id") != raw.get("occurrence_id")
    ):
        _fail("V112 occurrence identity changed")
    replay = replay_v111_occurrence(raw, family, seed)
    base_keys = (
        "initial_acquisition_labels",
        "certificate_local_labels",
        "identity_short_quotient_lifetime_target_labels",
        "full_diff_quotient_lifetime_target_labels",
        "per_hit_quotient_lifetime_target_labels",
        "no_cache_quotient_lifetime_target_labels",
        "cold_direct_lifetime_target_labels",
        "target_label_reduction_against_cold_direct",
        "execution_steps",
        "identity_short_new_planning_compute_events",
        "full_diff_new_planning_compute_events",
        "per_hit_new_planning_compute_events",
        "no_cache_planning_compute_events",
        "planning_compute_events_avoided_against_no_cache",
        "model_epoch_identity_checks",
        "full_model_epoch_diff_checks",
        "reverse_dependency_index_lookups",
        "identity_short_dependency_maintenance_events",
        "full_diff_dependency_maintenance_events",
        "per_hit_dependency_validation_checks",
        "maintenance_events_avoided_against_full_diff",
        "maintenance_events_avoided_against_per_hit",
        "identity_short_circuit_count",
    )
    accounting = {key: replay[key] for key in base_keys}
    accounting.update(
        sample_labels_execution_steps_planning_and_all_maintenance_axes_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    symmetric_full_diff = (
        accounting["full_diff_dependency_maintenance_events"]
        + accounting["model_epoch_identity_checks"]
    )
    accounting.update(
        fully_accounted_full_diff_identity_checks=accounting[
            "model_epoch_identity_checks"
        ],
        fully_accounted_full_diff_dependency_maintenance_events=symmetric_full_diff,
        maintenance_events_avoided_against_fully_accounted_full_diff=(
            symmetric_full_diff
            - accounting["identity_short_dependency_maintenance_events"]
        ),
        v110_full_diff_baseline_omitted_identity_checks=True,
        symmetric_matched_accounting_applied=True,
    )
    old_gate = raw["registered_gate"]
    gate = {
        "identity_short_full_diff_per_hit_and_no_cache_execution_equal": old_gate[
            "identity_short_full_diff_per_hit_and_no_cache_execution_equal"
        ],
        "all_reuse_arms_new_planning_compute_equal": old_gate[
            "all_reuse_arms_new_planning_compute_equal"
        ],
        "identity_short_new_planning_compute_strictly_below_no_cache": old_gate[
            "identity_short_new_planning_compute_strictly_below_no_cache"
        ],
        "identity_short_dependency_maintenance_strictly_below_per_hit_validation": old_gate[
            "identity_short_dependency_maintenance_strictly_below_per_hit_validation"
        ],
        "identity_short_dependency_maintenance_not_above_symmetrically_accounted_full_diff": accounting[
            "identity_short_dependency_maintenance_events"
        ]
        <= symmetric_full_diff,
        "epoch_authorized_cache_hit_observed": old_gate[
            "epoch_authorized_cache_hit_observed"
        ],
        "per_hit_dependency_rescan_count_is_zero": old_gate[
            "per_hit_dependency_rescan_count_is_zero"
        ],
        "quotient_model_orders_at_least_three_quarters": old_gate[
            "quotient_model_orders_at_least_three_quarters"
        ],
        "chosen_action_matches_quotient_strict_majority": old_gate[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_failure_only_query_discipline_clean": old_gate[
            "certificate_failure_only_query_discipline_clean"
        ],
        "later_zero_label_quotient_reuse_observed": old_gate[
            "later_zero_label_quotient_reuse_observed"
        ],
        "quotient_lifetime_labels_strictly_below_cold_direct": old_gate[
            "quotient_lifetime_labels_strictly_below_cold_direct"
        ],
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get(
            "symmetric_accounting_preserves_actions_labels_steps_and_algorithm"
        )
        != gate["passed"]
        or document.get("algorithm_or_outcome_changed_from_embedded_v111_occurrence")
        is not False
        or document.get("cached_heuristic_used_as_safety_authority") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V112 occurrence accounting or Gate changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        **accounting,
        "cache_hits": replay["cache_hits"],
        "cache_misses": replay["cache_misses"],
        "invalidations": replay["invalidations"],
    }


def verify_symmetric_epoch_accounting_campaign_bytes_v112(
    raw: bytes,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V112 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V112 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_SYMMETRIC_EPOCH_ACCOUNTING_CAMPAIGN_V112_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema") != "acfqp.symmetric_epoch_accounting_campaign.v112"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v111_failed_campaign_id") != V111_CAMPAIGN_ID
        or document.get("v111_failed_verification_id") != V111_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V112 campaign inventory changed")
    occurrence_verifier = _episode_bound_v111_occurrence_verifier()
    replay = [
        _occurrence(row, family, seed, occurrence_verifier)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    keys = (
        "initial_acquisition_labels",
        "certificate_local_labels",
        "identity_short_quotient_lifetime_target_labels",
        "full_diff_quotient_lifetime_target_labels",
        "per_hit_quotient_lifetime_target_labels",
        "no_cache_quotient_lifetime_target_labels",
        "cold_direct_lifetime_target_labels",
        "target_label_reduction_against_cold_direct",
        "execution_steps",
        "identity_short_new_planning_compute_events",
        "full_diff_new_planning_compute_events",
        "per_hit_new_planning_compute_events",
        "no_cache_planning_compute_events",
        "planning_compute_events_avoided_against_no_cache",
        "model_epoch_identity_checks",
        "full_model_epoch_diff_checks",
        "reverse_dependency_index_lookups",
        "identity_short_dependency_maintenance_events",
        "full_diff_dependency_maintenance_events",
        "per_hit_dependency_validation_checks",
        "maintenance_events_avoided_against_full_diff",
        "maintenance_events_avoided_against_per_hit",
        "identity_short_circuit_count",
        "fully_accounted_full_diff_identity_checks",
        "fully_accounted_full_diff_dependency_maintenance_events",
        "maintenance_events_avoided_against_fully_accounted_full_diff",
    )
    totals = {key: sum(row[key] for row in replay) for key in keys}
    accounting = {
        **totals,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_planning_and_all_maintenance_axes_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    ood = previous.v106.v105._ood(  # noqa: SLF001
        document["incompatible_schema_no_transfer_control"]
    )
    passed = (
        all(row["gate_passed"] for row in replay)
        and totals["identity_short_dependency_maintenance_events"]
        < totals["fully_accounted_full_diff_dependency_maintenance_events"]
        and totals["identity_short_dependency_maintenance_events"]
        < totals["per_hit_dependency_validation_checks"]
        and totals["identity_short_circuit_count"] > 0
        and totals["identity_short_quotient_lifetime_target_labels"]
        < totals["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(row["gate_passed"] for row in replay),
        "every_occurrence_exactly_matches_all_baselines": all(
            row["identity_short_quotient_lifetime_target_labels"]
            == row["full_diff_quotient_lifetime_target_labels"]
            == row["per_hit_quotient_lifetime_target_labels"]
            == row["no_cache_quotient_lifetime_target_labels"]
            for row in replay
        ),
        "every_occurrence_maintenance_below_per_hit_validation": all(
            row["identity_short_dependency_maintenance_events"]
            < row["per_hit_dependency_validation_checks"]
            for row in replay
        ),
        "every_occurrence_not_above_symmetrically_accounted_full_diff": all(
            row["identity_short_dependency_maintenance_events"]
            <= row["fully_accounted_full_diff_dependency_maintenance_events"]
            for row in replay
        ),
        "aggregate_maintenance_strictly_below_symmetrically_accounted_full_diff": totals[
            "identity_short_dependency_maintenance_events"
        ]
        < totals["fully_accounted_full_diff_dependency_maintenance_events"],
        "identity_short_circuit_observed": totals["identity_short_circuit_count"]
        > 0,
        "aggregate_quotient_labels_strictly_below_cold_direct": totals[
            "identity_short_quotient_lifetime_target_labels"
        ]
        < totals["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("registered_symmetric_epoch_accounting_verified")
        != passed
        or document.get("algorithm_or_outcome_changed_by_v112_accounting_successor")
        is not False
        or document.get("cached_heuristic_used_as_safety_authority") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V112 campaign accounting or Gate changed")
    return {
        "schema": "acfqp.symmetric_epoch_accounting_verification.v112",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V112_SYMMETRIC_EPOCH_ACCOUNTING_VERIFIED",
        "producer_free_fresh_v111_plan_and_receipt_reconstruction": True,
        "producer_free_identity_short_and_full_diff_reconstruction": True,
        "producer_free_symmetric_accounting_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "verified_cache_hit_count": sum(row["cache_hits"] for row in replay),
        "verified_cache_miss_count": sum(row["cache_misses"] for row in replay),
        "verified_dependency_invalidations": sum(
            row["invalidations"] for row in replay
        ),
        "registered_gate_independently_verified": passed,
        "cached_heuristic_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_symmetric_epoch_accounting_verification_v112(raw: bytes) -> bytes:
    payload = verify_symmetric_epoch_accounting_campaign_bytes_v112(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v112(
            domains.CONSTRUCTION_K7_SYMMETRIC_EPOCH_ACCOUNTING_VERIFICATION_V112_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V112 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_symmetric_epoch_accounting_verification_v112",
    "verify_symmetric_epoch_accounting_campaign_bytes_v112",
)
