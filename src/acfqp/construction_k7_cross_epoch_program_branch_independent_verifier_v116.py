"""Producer-free verification of the V116 cross-epoch reuse delta."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v115 as domains115
from acfqp import construction_k7_domain_registry_extension_v116 as domains
from acfqp import construction_k7_projected_program_memo_independent_verifier_v115 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "2ffeebf8f989a944afce3144aeed8aeba4eda529bce3f3bfe7be19cea4a8e406"
CAMPAIGN_BYTE_COUNT = 6_768_106
CAMPAIGN_SHA256 = "755a92500fcf5f4e88bf6f1b0990ced8b4660a35cfd92ad92e535112363b0be2"
PREREGISTRATION_ID = "0110bd988c146dcb5d93f67081e4ce603f0106ca1df2d93e0e2dc74a3c0d6012"
V115_CAMPAIGN_ID = "d2d061867f8bfc3d2c1abe439537ad0a1432738bf2db4242ef4d35f2c41dfcfe"
V115_VERIFICATION_ID = "3cf6f79e13fdfa3a83f7e837106f2247659e5f1c6cb0e2b9d67fd2023e25d8f9"
V115_VERIFIER_SOURCE_SHA256 = "c00a56add0fd915420d8f18ec92b79a4d4fa8420647719c522e51cd4eacfa6f2"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_028_101),
    ("COUPLED_EXCHANGE", 1_028_201),
    ("MAINTENANCE_CASCADE", 1_028_301),
)
EPISODES = (251, 252, 253)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7CrossEpochProgramBranchIndependentVerifierV116Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossEpochProgramBranchIndependentVerifierV116Error(
        message
    )


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V116 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v116(domain, payload):
        _fail(f"V116 {key} changed")


def _v115_namespace() -> dict[str, Any]:
    if (
        hashlib.sha256(Path(previous.__file__).read_bytes()).hexdigest()
        != V115_VERIFIER_SOURCE_SHA256
        or previous.EPISODES != (241, 242, 243)
        or previous.CAMPAIGN_ID != V115_CAMPAIGN_ID
        or previous.VERIFICATION_ID != V115_VERIFICATION_ID
    ):
        _fail("V116 frozen producer-free V115 verifier changed")
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
    return namespace


def _compare(
    cross: Mapping[str, Any], matched: Mapping[str, Any], verifier: Mapping[str, Any]
) -> dict[str, int]:
    cross_compute = matched_compute = cross_hits = matched_hits = 0
    for cross_episode, matched_episode in zip(
        cross["episodes"], matched["episodes"], strict=True
    ):
        cross_rows = {
            tuple(row["raw_state"]): row["abstract_plan"]
            for row in cross_episode["abstract_plan_receipts"]
        }
        matched_rows = {
            tuple(row["raw_state"]): row["abstract_plan"]
            for row in matched_episode["abstract_plan_receipts"]
        }
        if set(cross_rows) != set(matched_rows):
            _fail("V116 cross-epoch and V115 plan contexts changed")
        for raw in sorted(cross_rows):
            left = cross_rows[raw]
            right = matched_rows[raw]
            verifier["_plan"](left)
            verifier["_plan"](right)
            cross_compute += left["abstract_support_branch_evaluations"]
            matched_compute += right["abstract_support_branch_evaluations"]
            if right["planning_source"] != "COMPILED_FACTOR_PROGRAM_FALLBACK":
                if left != right:
                    _fail("V116 non-program plan changed against V115")
                continue
            if left["planning_source"] != "COMPILED_FACTOR_PROGRAM_FALLBACK":
                _fail("V116 program source classification changed")
            if verifier["_plan_projection"](left) != verifier[
                "_plan_projection"
            ](right):
                _fail("V116 program plan semantics changed")
            left_projected = left["embedded_projected_plan"]
            right_projected = right["embedded_projected_plan"]
            if verifier["_projected_plan_projection"](
                left_projected
            ) != verifier["_projected_plan_projection"](right_projected):
                _fail("V116 projected program path changed")
            left_new = left_projected["projected_planning_compute_events"]
            right_new = right_projected["projected_planning_compute_events"]
            left_hit = left_projected["projected_branch_cache_hit_count"]
            right_hit = right_projected["projected_branch_cache_hit_count"]
            left_total = left_projected[
                "matched_uncached_projected_planning_compute_events"
            ]
            right_total = right_projected[
                "matched_uncached_projected_planning_compute_events"
            ]
            if (
                left_new != left["abstract_support_branch_evaluations"]
                or right_new != right["abstract_support_branch_evaluations"]
                or left_new + left_hit != left_total
                or right_new + right_hit != right_total
                or left_total != right_total
                or left_new > right_new
            ):
                _fail("V116 cross-epoch branch accounting changed")
            cross_hits += left_hit
            matched_hits += right_hit
    return {
        "cross_compute": cross_compute,
        "matched_compute": matched_compute,
        "cross_hits": cross_hits,
        "matched_hits": matched_hits,
    }


def _occurrence(
    document: Any,
    family: str,
    seed: int,
    verifier: Mapping[str, Any],
) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_OCCURRENCE_V116_DOMAIN,
    )
    cross_wrapper = document.get("cross_epoch_program_branch_sequence")
    matched_wrapper = document.get("matched_v115_program_memo_sequence")
    if (
        document.get("schema") != "acfqp.cross_epoch_program_branch_occurrence.v116"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or type(cross_wrapper) is not dict
        or type(matched_wrapper) is not dict
    ):
        _fail("V116 occurrence identity changed")
    _content(
        cross_wrapper,
        "sequence_id",
        domains.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_SEQUENCE_V116_DOMAIN,
    )
    matched_payload = {
        key: value for key, value in matched_wrapper.items() if key != "sequence_id"
    }
    if matched_wrapper.get("sequence_id") != domains115.extension_content_id_v115(
        domains115.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_SEQUENCE_V115_DOMAIN,
        matched_payload,
    ):
        _fail("V116 embedded V115 wrapper changed")
    cross = cross_wrapper["cross_epoch_program_branch_base_sequence"]
    matched = matched_wrapper["program_memoized_base_sequence"]
    if (
        cross_wrapper.get("cross_epoch_program_branch_base_sequence_id")
        != cross.get("sequence_id")
        or matched_wrapper.get("program_memoized_base_sequence_id")
        != matched.get("sequence_id")
        or document.get("cross_epoch_program_branch_sequence_id")
        != cross_wrapper.get("sequence_id")
        or document.get("matched_v115_program_memo_sequence_id")
        != matched_wrapper.get("sequence_id")
    ):
        _fail("V116 sequence join changed")
    try:
        verifier["_sequence"](cross)
        verifier["_sequence"](matched)
    except previous.ConstructionK7ProjectedProgramMemoIndependentVerifierV115Error as exc:
        _fail(f"V116 embedded sequence reconstruction failed: {exc}")
    exact_keys = (
        "all_failed_certificates",
        "all_local_distinctions",
        "persistent_exact_overlay_rows",
        "persistent_exact_overlay_sha256",
        "quotient_models_before_each_episode",
        "quotient_models_after_each_episode",
        "incremental_successor_update_receipts",
        "full_rebuild_match_receipts",
        "model_epoch_transition_receipts",
        "lifetime_target_ground_support_labels",
        "execution_step_count",
    )
    episode_exact_keys = (
        "action_keys",
        "abstract_execution_receipts",
        "raw_incremental_transition_rows",
        "failed_certificates",
        "local_distinctions",
        "incremental_certificate_local_ground_support_labels",
        "execution_steps",
        "success",
    )
    exact = all(cross[key] == matched[key] for key in exact_keys) and all(
        all(left[key] == right[key] for key in episode_exact_keys)
        for left, right in zip(cross["episodes"], matched["episodes"], strict=True)
    )
    comparison = _compare(cross, matched, verifier)
    accounting = {
        "initial_acquisition_labels": cross[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_local_labels": cross[
            "certificate_ground_support_labels_paid_once"
        ],
        "cross_epoch_lifetime_target_labels": cross[
            "lifetime_target_ground_support_labels"
        ],
        "matched_v115_lifetime_target_labels": matched[
            "lifetime_target_ground_support_labels"
        ],
        "execution_steps": cross["execution_step_count"],
        "cross_epoch_planning_compute_events": comparison["cross_compute"],
        "matched_v115_planning_compute_events": comparison["matched_compute"],
        "matched_uncached_v113_planning_compute_events": cross_wrapper[
            "matched_uncached_abstract_planning_compute_events"
        ],
        "planning_compute_events_avoided_against_v115": comparison[
            "matched_compute"
        ]
        - comparison["cross_compute"],
        "planning_compute_events_avoided_against_uncached_v113": cross_wrapper[
            "matched_uncached_abstract_planning_compute_events"
        ]
        - comparison["cross_compute"],
        "cross_epoch_program_branch_cache_hits": comparison["cross_hits"],
        "matched_v115_program_branch_cache_hits": comparison["matched_hits"],
        "additional_cross_epoch_program_branch_cache_hits": comparison[
            "cross_hits"
        ]
        - comparison["matched_hits"],
        "model_epoch_identity_checks": cross["model_epoch_identity_checks"],
        "full_model_epoch_diff_checks": cross["full_model_epoch_diff_checks"],
        "reverse_dependency_index_lookups": cross[
            "reverse_dependency_index_lookups"
        ],
        "dependency_maintenance_events": cross["dependency_maintenance_events"],
        "incremental_model_update_compilation_events": cross[
            "incremental_model_update_compilation_events"
        ],
        "matched_full_rebuild_update_compilation_events": cross[
            "matched_full_rebuild_update_compilation_events"
        ],
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "cross_epoch_and_v115_actions_certificates_overlays_models_and_execution_equal": exact,
        "cross_epoch_and_v115_target_labels_equal": accounting[
            "cross_epoch_lifetime_target_labels"
        ]
        == accounting["matched_v115_lifetime_target_labels"],
        "cross_epoch_uncached_compute_reconstructs_v115_uncached_compute": cross_wrapper[
            "matched_uncached_abstract_planning_compute_events"
        ]
        == matched_wrapper["matched_uncached_abstract_planning_compute_events"],
        "additional_cross_epoch_branch_reuse_observed": accounting[
            "additional_cross_epoch_program_branch_cache_hits"
        ]
        > 0,
        "cross_epoch_planning_compute_not_above_v115": comparison[
            "cross_compute"
        ]
        <= comparison["matched_compute"],
        "certificate_failure_only_query_discipline_clean": cross[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_model_still_matches_full_v105_rebuild": cross[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_still_consumes_compiled_model_without_raw_rows": cross[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
    }
    gate["passed"] = all(
        value
        for key, value in gate.items()
        if key != "additional_cross_epoch_branch_reuse_observed"
    )
    if (
        cross_wrapper.get("cross_epoch_program_branch_cache_hit_count")
        != comparison["cross_hits"]
        or matched_wrapper.get("projected_program_branch_cache_hit_count")
        != comparison["matched_hits"]
        or cross_wrapper.get("actual_new_abstract_planning_compute_events")
        != comparison["cross_compute"]
        or matched_wrapper.get("actual_new_abstract_planning_compute_events")
        != comparison["matched_compute"]
        or document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("cross_epoch_program_branch_reuse_verified")
        != gate["passed"]
        or document.get("compiled_model_or_cache_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V116 occurrence accounting, Gate, or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        "additional_reuse_observed": gate[
            "additional_cross_epoch_branch_reuse_observed"
        ],
        **accounting,
    }


def verify_cross_epoch_program_branch_campaign_bytes_v116(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V116 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V116 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_CAMPAIGN_V116_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema") != "acfqp.cross_epoch_program_branch_campaign.v116"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v115_success_campaign_id") != V115_CAMPAIGN_ID
        or document.get("v115_success_verification_id") != V115_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V116 campaign inventory changed")
    verifier = _v115_namespace()
    replay = [
        _occurrence(row, family, seed, verifier)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    keys = tuple(
        key
        for key, value in replay[0].items()
        if type(value) is int
        and key not in ("seed", "gate_passed", "additional_reuse_observed")
    )
    numeric = {key: sum(row[key] for row in replay) for key in keys}
    accounting = {
        **numeric,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    family_counts = {
        family: sum(row["target_family"] == family for row in replay)
        for family, _seed in TARGETS
    }
    ood = document.get("incompatible_schema_no_transfer_control")
    strict_ood = (
        type(ood) is dict
        and ood.get("exact_interface_match") is False
        and ood.get("learned_structure_prior_delivered") is False
        and ood.get("strict_ood_no_transfer") is True
    )
    passed = (
        all(row["gate_passed"] for row in replay)
        and all(family_counts.values())
        and numeric["additional_cross_epoch_program_branch_cache_hits"] > 0
        and numeric["cross_epoch_planning_compute_events"]
        < numeric["matched_v115_planning_compute_events"]
        and strict_ood
    )
    gate = {
        "required_target_occurrence_count": len(TARGETS),
        "passed_target_occurrence_count": sum(
            row["gate_passed"] for row in replay
        ),
        "required_target_family_counts": family_counts,
        "all_three_registered_structural_families_present": all(
            family_counts.values()
        ),
        "every_occurrence_matches_v115_actions_certificates_models_and_execution": all(
            row["gate_passed"] for row in replay
        ),
        "at_least_one_occurrence_observes_additional_cross_epoch_branch_reuse": any(
            row["additional_reuse_observed"] for row in replay
        ),
        "every_occurrence_planning_compute_not_above_v115": all(
            row["cross_epoch_planning_compute_events"]
            <= row["matched_v115_planning_compute_events"]
            for row in replay
        ),
        "aggregate_planning_compute_below_v115": numeric[
            "cross_epoch_planning_compute_events"
        ]
        < numeric["matched_v115_planning_compute_events"],
        "strict_incompatible_schema_no_transfer_verified": strict_ood,
        "passed": passed,
    }
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("registered_cross_epoch_program_branch_reuse_verified")
        != passed
        or document.get("ground_distinctions_only_after_certificate_failure_verified")
        != passed
        or document.get("compiled_model_or_cache_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("arbitrary_domain_transfer_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V116 campaign accounting, Gate, or claim boundary changed")
    return {
        "schema": "acfqp.cross_epoch_program_branch_verification.v116",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v115_success_verification_id": V115_VERIFICATION_ID,
        "verification_status": "REGISTERED_V116_CROSS_EPOCH_PROGRAM_BRANCH_VERIFIED",
        "producer_free_v116_content_graph_reconstruction": True,
        "producer_free_cross_epoch_and_v115_plan_pairing_reconstruction": True,
        "producer_free_branch_accounting_and_execution_equality_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "fresh_v116_full_dynamics_rederivation_performed": False,
        "frozen_v115_delta_verification_remains_predecessor": True,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "registered_gate_independently_verified": passed,
        "compiled_model_or_cache_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_cross_epoch_program_branch_verification_v116(raw: bytes) -> bytes:
    payload = verify_cross_epoch_program_branch_campaign_bytes_v116(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v116(
            domains.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_VERIFICATION_V116_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V116 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_cross_epoch_program_branch_verification_v116",
    "verify_cross_epoch_program_branch_campaign_bytes_v116",
)
