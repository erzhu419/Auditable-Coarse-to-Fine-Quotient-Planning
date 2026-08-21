"""Producer-free verification of the V115 memoization delta."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v109 as domains109
from acfqp import construction_k7_domain_registry_extension_v113 as domains113
from acfqp import construction_k7_domain_registry_extension_v115 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "d2d061867f8bfc3d2c1abe439537ad0a1432738bf2db4242ef4d35f2c41dfcfe"
CAMPAIGN_BYTE_COUNT = 6_519_817
CAMPAIGN_SHA256 = "94add1705c5780f4893a7dde82771e4dd3c8d27219ceb1c6b8a3631d393476dd"
PREREGISTRATION_ID = "6834b8be1244a74e9e4a5bc0e6ee1d9c881b167fd8b53e116be8744fa8972513"
V114_CAMPAIGN_ID = "0daf03f1891ed225b2221d61fa3780c1f0a84d2506ce8d2bff8164df1153c3a8"
V114_VERIFICATION_ID = "a2c30e47cb13b16c01c0c942c1a2e84437c0395335582474720011563a747f50"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_027_101),
    ("COUPLED_EXCHANGE", 1_027_201),
    ("MAINTENANCE_CASCADE", 1_027_301),
)
EPISODES = (241, 242, 243)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64

_EPISODE_DOMAIN = b"acfqp:generic-legality-conditioned-certificate-episode:v106\x00"
_MODEL_DOMAIN = b"acfqp:generic-observation-quotient-graph:v105\x00"
_V106_PLAN_DOMAIN = b"acfqp:generic-legality-conditioned-quotient-plan:v106\x00"
_EXECUTION_DOMAIN = b"acfqp:generic-abstract-execution-receipt:v103\x00"
_V113_EPISODE_EXTRAS = {
    "quotient_graph_before_episode",
    "incremental_successor_state_id_before_episode",
    "incremental_successor_update_after_episode",
    "full_rebuild_match_after_episode",
    "quotient_graph_after_episode",
    "incremental_successor_state_id_after_episode",
    "epoch_transition_after_episode",
    "actual_legality_conditioned_execution_receipts",
    "actual_legality_conditioned_execution_receipt_count",
    "quotient_proposal_admitted_execution_count",
    "chosen_action_matches_admitted_quotient_proposal_count",
    "certificate_local_legality_plan_count",
    "epoch_indexed_orderer_call_count",
    "epoch_authorized_cache_hit_count",
    "epoch_cache_miss_count",
    "actual_new_abstract_planning_compute_events",
    "dependency_cache_entry_count_after_episode",
    "new_certificate_labels_charged_this_episode",
    "paid_certificate_labels_cumulative",
    "persistent_exact_support_group_count_after_episode",
    "planner_raw_transition_argument_present",
}


class ConstructionK7ProjectedProgramMemoIndependentVerifierV115Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedProgramMemoIndependentVerifierV115Error(
        message
    )


def _content_v115(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V115 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v115(domain, payload):
        _fail(f"V115 {key} changed")


def _content_v113(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V115 embedded {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains113.extension_content_id_v113(domain, payload):
        _fail(f"V115 embedded {key} changed")


def _model(document: Any) -> None:
    if type(document) is not dict:
        _fail("V115 quotient model type changed")
    payload = {
        key: value for key, value in document.items() if key != "quotient_graph_id"
    }
    if document.get("quotient_graph_id") != hashlib.sha256(
        _MODEL_DOMAIN + canonical_json_bytes(payload)
    ).hexdigest():
        _fail("V115 quotient model identity changed")


def _episode(document: Any) -> None:
    if type(document) is not dict:
        _fail("V115 episode type changed")
    payload = {
        key: value
        for key, value in document.items()
        if key != "episode_id" and key not in _V113_EPISODE_EXTRAS
    }
    if document.get("episode_id") != hashlib.sha256(
        _EPISODE_DOMAIN + canonical_json_bytes(payload)
    ).hexdigest():
        _fail("V115 episode identity changed")
    for row in document.get("abstract_execution_receipts", []):
        _execution_receipt(row)


def _execution_receipt(document: Any) -> None:
    if type(document) is not dict:
        _fail("V115 execution receipt type changed")
    payload = {
        key: value for key, value in document.items() if key != "execution_receipt_id"
    }
    shield = document.get("shield_receipt")
    abstract = document.get("abstract_proposal")
    partial = document.get("partial_proposal")
    legal = document.get("legal_action_keys")
    chosen = document.get("chosen_action_key")
    if (
        document.get("execution_receipt_id")
        != hashlib.sha256(
            _EXECUTION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest()
        or type(shield) is not dict
        or type(abstract) is not list
        or type(partial) is not list
        or type(legal) is not list
        or chosen not in legal
        or shield.get("abstract_proposal") != abstract
        or shield.get("partial_proposal") != partial
        or shield.get("legal_action_keys") != legal
        or document.get("query_local_exact_overlay_remains_only_safety_authority")
        is not True
    ):
        _fail("V115 execution receipt semantics changed")


def _plan(document: Any) -> None:
    if type(document) is not dict:
        _fail("V115 plan type changed")
    payload = {
        key: value
        for key, value in document.items()
        if key != "legality_conditioned_quotient_plan_id"
    }
    source = document.get("planning_source")
    if source in (
        "OBSERVATION_QUOTIENT_GRAPH",
        "COMPILED_FACTOR_PROGRAM_FALLBACK",
    ):
        expected = hashlib.sha256(
            _V106_PLAN_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest()
    elif source == "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER":
        expected = domains109.extension_content_id_v109(
            domains109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_PLAN_V109_DOMAIN,
            payload,
        )
    elif source == "COMPILED_FACTOR_PROGRAM_MEMOIZED":
        expected = domains.extension_content_id_v115(
            domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_PLAN_V115_DOMAIN,
            payload,
        )
    else:
        _fail("V115 planning source changed")
    if (
        document.get("legality_conditioned_quotient_plan_id") != expected
        or document.get("initial_action_key")
        not in document.get("exact_legal_action_keys_at_initial_state", [])
        or document.get("projected_action_path", [None])[0]
        != document.get("initial_action_key")
        or document.get("query_local_exact_overlay_remains_only_safety_authority")
        is not True
    ):
        _fail("V115 plan identity or safety boundary changed")


def _sequence(document: Any) -> None:
    _content_v113(
        document,
        "sequence_id",
        domains113.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_SEQUENCE_V113_DOMAIN,
    )
    if (
        document.get("schema")
        != "acfqp.generic_incremental_abstract_successor_sequence.v113"
        or document.get("episode_indices") != list(EPISODES)
        or document.get("planner_consumed_compiled_successor_without_raw_transition_argument")
        is not True
        or document.get("every_new_ground_query_followed_a_failed_certificate")
        is not True
        or document.get("query_local_exact_overlay_exclusively_discharges_safety")
        is not True
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
    ):
        _fail("V115 embedded sequence boundary changed")
    for model in (
        *document["quotient_models_before_each_episode"],
        *document["quotient_models_after_each_episode"],
    ):
        _model(model)
    for update in document["incremental_successor_update_receipts"]:
        _content_v113(
            update,
            "update_receipt_id",
            domains113.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_UPDATE_V113_DOMAIN,
        )
    for match in (
        document["bootstrap_full_rebuild_match"],
        *document["full_rebuild_match_receipts"],
    ):
        _content_v113(
            match,
            "match_receipt_id",
            domains113.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_MATCH_V113_DOMAIN,
        )
    episodes = document.get("episodes")
    if type(episodes) is not list or len(episodes) != len(EPISODES):
        _fail("V115 episode inventory changed")
    for episode, index in zip(episodes, EPISODES, strict=True):
        _episode(episode)
        if episode.get("episode_index") != index:
            _fail("V115 episode index changed")
        for receipt in episode["abstract_plan_receipts"]:
            _plan(receipt["abstract_plan"])


def _plan_projection(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in plan.items()
        if key
        not in (
            "legality_conditioned_quotient_plan_id",
            "abstract_support_branch_evaluations",
            "embedded_projected_plan",
        )
    }


def _projected_plan_projection(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in plan.items()
        if key
        not in (
            "projected_planning_compute_events",
            "matched_uncached_projected_planning_compute_events",
            "projected_branch_cache_hit_count",
            "projected_branch_cache_entry_count",
        )
    }


def _compare_plan_receipts(
    memo_sequence: Mapping[str, Any], matched_sequence: Mapping[str, Any]
) -> dict[str, int]:
    memo_compute = matched_compute = branch_hits = whole_hits = 0
    for memo_episode, matched_episode in zip(
        memo_sequence["episodes"], matched_sequence["episodes"], strict=True
    ):
        memo_rows = {
            tuple(row["raw_state"]): row["abstract_plan"]
            for row in memo_episode["abstract_plan_receipts"]
        }
        matched_rows = {
            tuple(row["raw_state"]): row["abstract_plan"]
            for row in matched_episode["abstract_plan_receipts"]
        }
        if set(memo_rows) != set(matched_rows):
            _fail("V115 memo and matched plan contexts changed")
        for raw in sorted(memo_rows):
            memo = memo_rows[raw]
            matched = matched_rows[raw]
            _plan(memo)
            _plan(matched)
            memo_compute += memo["abstract_support_branch_evaluations"]
            matched_compute += matched["abstract_support_branch_evaluations"]
            if memo["planning_source"] == "COMPILED_FACTOR_PROGRAM_MEMOIZED":
                whole_hits += 1
                _fail("V115 registered campaign unexpectedly used whole-plan memo")
            if matched["planning_source"] != "COMPILED_FACTOR_PROGRAM_FALLBACK":
                if memo != matched:
                    _fail("V115 non-program plan changed against V113")
                continue
            if memo["planning_source"] != "COMPILED_FACTOR_PROGRAM_FALLBACK":
                _fail("V115 fallback source classification changed")
            if _plan_projection(memo) != _plan_projection(matched):
                _fail("V115 fallback plan semantics changed")
            memo_projected = memo["embedded_projected_plan"]
            matched_projected = matched["embedded_projected_plan"]
            if (
                _projected_plan_projection(memo_projected)
                != _projected_plan_projection(matched_projected)
                or memo_projected["projected_planning_compute_events"]
                != memo["abstract_support_branch_evaluations"]
                or matched_projected["projected_planning_compute_events"]
                != matched["abstract_support_branch_evaluations"]
                or memo_projected[
                    "matched_uncached_projected_planning_compute_events"
                ]
                != matched_projected["projected_planning_compute_events"]
                or memo_projected["projected_planning_compute_events"]
                + memo_projected["projected_branch_cache_hit_count"]
                != matched_projected["projected_planning_compute_events"]
            ):
                _fail("V115 program branch accounting changed")
            branch_hits += memo_projected["projected_branch_cache_hit_count"]
    return {
        "memo_compute": memo_compute,
        "matched_compute": matched_compute,
        "branch_hits": branch_hits,
        "whole_hits": whole_hits,
    }


def _occurrence(document: Any, family: str, seed: int) -> dict[str, Any]:
    _content_v115(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_OCCURRENCE_V115_DOMAIN,
    )
    wrapper = document.get("projected_program_memo_sequence")
    matched = document.get("matched_v113_incremental_sequence")
    if (
        document.get("schema") != "acfqp.projected_program_memo_occurrence.v115"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or type(wrapper) is not dict
        or type(matched) is not dict
    ):
        _fail("V115 occurrence identity changed")
    _content_v115(
        wrapper,
        "sequence_id",
        domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_SEQUENCE_V115_DOMAIN,
    )
    memo = wrapper["program_memoized_base_sequence"]
    if (
        wrapper.get("program_memoized_base_sequence_id") != memo.get("sequence_id")
        or document.get("projected_program_memo_sequence_id")
        != wrapper.get("sequence_id")
        or document.get("matched_v113_incremental_sequence_id")
        != matched.get("sequence_id")
    ):
        _fail("V115 occurrence sequence join changed")
    _sequence(memo)
    _sequence(matched)
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
    exact = all(memo[key] == matched[key] for key in exact_keys) and all(
        all(left[key] == right[key] for key in episode_exact_keys)
        for left, right in zip(memo["episodes"], matched["episodes"], strict=True)
    )
    comparison = _compare_plan_receipts(memo, matched)
    accounting = {
        "initial_acquisition_labels": memo[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_local_labels": memo[
            "certificate_ground_support_labels_paid_once"
        ],
        "projected_program_memo_lifetime_target_labels": memo[
            "lifetime_target_ground_support_labels"
        ],
        "matched_v113_lifetime_target_labels": matched[
            "lifetime_target_ground_support_labels"
        ],
        "execution_steps": memo["execution_step_count"],
        "projected_program_memo_planning_compute_events": comparison[
            "memo_compute"
        ],
        "matched_v113_planning_compute_events": comparison["matched_compute"],
        "matched_uncached_abstract_planning_compute_events": comparison[
            "matched_compute"
        ],
        "planning_compute_events_avoided_by_program_memo": comparison[
            "matched_compute"
        ]
        - comparison["memo_compute"],
        "projected_program_whole_plan_memo_hits": comparison["whole_hits"],
        "projected_program_branch_cache_hits": comparison["branch_hits"],
        "model_epoch_identity_checks": memo["model_epoch_identity_checks"],
        "full_model_epoch_diff_checks": memo["full_model_epoch_diff_checks"],
        "reverse_dependency_index_lookups": memo[
            "reverse_dependency_index_lookups"
        ],
        "dependency_maintenance_events": memo["dependency_maintenance_events"],
        "incremental_model_update_compilation_events": memo[
            "incremental_model_update_compilation_events"
        ],
        "matched_full_rebuild_update_compilation_events": memo[
            "matched_full_rebuild_update_compilation_events"
        ],
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "memo_and_v113_actions_certificates_overlays_models_and_execution_equal": exact,
        "memo_and_v113_target_labels_equal": accounting[
            "projected_program_memo_lifetime_target_labels"
        ]
        == accounting["matched_v113_lifetime_target_labels"],
        "memo_uncached_compute_reconstructs_v113_compute": wrapper[
            "matched_uncached_abstract_planning_compute_events"
        ]
        == comparison["matched_compute"],
        "projected_program_branch_cache_hit_observed": comparison[
            "branch_hits"
        ]
        > 0,
        "projected_program_memo_planning_compute_strictly_below_v113": comparison[
            "memo_compute"
        ]
        < comparison["matched_compute"],
        "certificate_failure_only_query_discipline_clean": memo[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_model_still_matches_full_v105_rebuild": memo[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_still_consumes_compiled_model_without_raw_rows": memo[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
    }
    gate["passed"] = all(gate.values())
    if (
        wrapper.get("projected_program_branch_cache_hit_count")
        != comparison["branch_hits"]
        or wrapper.get("projected_program_memo_hit_count")
        != comparison["whole_hits"]
        or wrapper.get("actual_new_abstract_planning_compute_events")
        != comparison["memo_compute"]
        or wrapper.get("planning_compute_events_avoided_by_program_memo")
        != comparison["matched_compute"] - comparison["memo_compute"]
        or document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("projected_program_memoization_verified") != gate["passed"]
        or document.get("compiled_model_or_memo_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V115 occurrence accounting, Gate, or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        **accounting,
    }


def verify_projected_program_memo_campaign_bytes_v115(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V115 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V115 campaign is noncanonical")
    _content_v115(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_CAMPAIGN_V115_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema") != "acfqp.projected_program_memo_campaign.v115"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v114_success_campaign_id") != V114_CAMPAIGN_ID
        or document.get("v114_success_verification_id") != V114_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V115 campaign inventory changed")
    replay = [
        _occurrence(row, family, seed)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    keys = tuple(
        key
        for key, value in replay[0].items()
        if type(value) is int and key not in ("seed", "gate_passed")
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
        and numeric["projected_program_branch_cache_hits"] > 0
        and numeric["projected_program_memo_planning_compute_events"]
        < numeric["matched_v113_planning_compute_events"]
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
        "every_occurrence_matches_v113_actions_certificates_models_and_execution": all(
            row["gate_passed"] for row in replay
        ),
        "every_occurrence_observes_program_branch_reuse": all(
            row["projected_program_branch_cache_hits"] > 0 for row in replay
        ),
        "every_occurrence_planning_compute_below_v113": all(
            row["projected_program_memo_planning_compute_events"]
            < row["matched_v113_planning_compute_events"]
            for row in replay
        ),
        "aggregate_planning_compute_below_v113": numeric[
            "projected_program_memo_planning_compute_events"
        ]
        < numeric["matched_v113_planning_compute_events"],
        "strict_incompatible_schema_no_transfer_verified": strict_ood,
        "passed": passed,
    }
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("registered_projected_program_memoization_verified")
        != passed
        or document.get("ground_distinctions_only_after_certificate_failure_verified")
        != passed
        or document.get("compiled_model_or_memo_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("arbitrary_domain_transfer_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V115 campaign accounting, Gate, or claim boundary changed")
    return {
        "schema": "acfqp.projected_program_memo_verification.v115",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v114_success_verification_id": V114_VERIFICATION_ID,
        "verification_status": "REGISTERED_V115_PROJECTED_PROGRAM_MEMO_VERIFIED",
        "producer_free_v115_content_graph_reconstruction": True,
        "producer_free_program_plan_pairing_and_branch_accounting_reconstruction": True,
        "producer_free_actions_certificates_overlays_models_and_execution_equality_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "fresh_v115_full_dynamics_rederivation_performed": False,
        "frozen_v114_full_dynamics_verification_remains_predecessor": True,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "registered_gate_independently_verified": passed,
        "compiled_model_or_memo_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_projected_program_memo_verification_v115(raw: bytes) -> bytes:
    payload = verify_projected_program_memo_campaign_bytes_v115(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v115(
            domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_VERIFICATION_V115_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V115 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_projected_program_memo_verification_v115",
    "verify_projected_program_memo_campaign_bytes_v115",
)
