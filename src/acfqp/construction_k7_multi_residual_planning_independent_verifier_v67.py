"""Producer-free ledger verification for frozen V67 campaign bytes."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v67 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


VERIFICATION_ID = "c7a219fcb73856215082022d1128efbed70aec50678c224533ba48944ebabb19"
EXPECTED_CANONICAL_BYTE_COUNT = 909
EXPECTED_CANONICAL_SHA256 = "14e8b492a30db521646565ceb239c7a343b7209d0f599903c785313bb6ba61ba"
_PREREGISTRATION_ID = "49a2faf3b37abaaf3960678a12cc0450f91b6054ffc67206756e5307eb7bb239"
_V66_CAMPAIGN_ID = "b4c8e705ebe76b63c3a67831feedcff948a2b0e09ab928b9aaa03363f3d3a1a8"
_V66_VERIFICATION_ID = "1b42294ccd1785763de545da0b7a159526fc4c23a212a956e341257d1149fc12"
_MULTI_DOMAIN = b"acfqp:generic-multi-residual-acquisition:v24\x00"
_TOTAL_DOMAIN = b"acfqp:total-adaptive-residual-acquisition:v20\x00"
_ADAPTIVE_DOMAIN = b"acfqp:adaptive-residual-factor-acquisition:v19\x00"
_EXPECTED_SEEDS = {
    "BALANCED_BATCH_REFINEMENT": set(range(681_101, 681_105)),
    "COUPLED_EXCHANGE": set(range(682_101, 682_105)),
    "MAINTENANCE_CASCADE": set(range(683_101, 683_105)),
}


class ConstructionK7MultiResidualPlanningIndependentVerifierV67Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7MultiResidualPlanningIndependentVerifierV67Error(message)


def _id(domain: str, document: dict[str, Any], key: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v67(domain, payload) != document.get(key):
        _fail(f"V67 {key} changed")


def _hash(document: dict[str, Any], key: str, prefix: bytes) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != hashlib.sha256(
        prefix + canonical_json_bytes(payload)
    ).hexdigest():
        _fail(f"V67 embedded {key} changed")


def _verify_total(acquisition: Any, replay: Any, queries: int, rows: int) -> None:
    if type(acquisition) is not dict or type(replay) is not dict:
        _fail("V67 per-target acquisition changed")
    _hash(acquisition, "total_acquisition_id", _TOTAL_DOMAIN)
    status = acquisition.get("status")
    if status not in (
        "STATISTICAL_PROPOSAL_ISSUED",
        "ABSTAINED_INSUFFICIENT_CALIBRATED_EVIDENCE",
    ):
        _fail("V67 per-target acquisition status changed")
    predecessor = acquisition.get("predecessor_acquisition")
    if status == "STATISTICAL_PROPOSAL_ISSUED":
        if type(predecessor) is not dict or type(acquisition.get("candidate")) is not dict:
            _fail("V67 statistical proposal changed")
        _hash(predecessor, "acquisition_id", _ADAPTIVE_DOMAIN)
    elif predecessor is not None or acquisition.get("candidate") is not None:
        _fail("V67 abstention changed")
    if (
        type(acquisition.get("ground_support_labels")) is not int
        or not 0 < acquisition["ground_support_labels"] <= queries
        or type(acquisition.get("raw_transition_rows_consumed")) is not int
        or not 0 < acquisition["raw_transition_rows_consumed"] <= rows
        or acquisition.get("proposal_only_not_safety_authority") is not True
        or replay.get("total_acquisition_id") != acquisition["total_acquisition_id"]
        or replay.get("status") != status
        or replay.get("full_query_stream_label_count") != queries
        or replay.get("full_query_stream_raw_transition_count") != rows
        or replay.get("future_transition_prediction_authority_present") is not False
    ):
        _fail("V67 per-target acquisition accounting changed")


def _verify_multi(acquisition: Any, replay: Any, queries: int, rows: int) -> None:
    if type(acquisition) is not dict or type(replay) is not dict:
        _fail("V67 multi acquisition changed")
    _hash(acquisition, "multi_residual_acquisition_id", _MULTI_DOMAIN)
    targets = acquisition.get("unknown_residual_target_columns")
    target_results = acquisition.get("target_results")
    compilable = acquisition.get("compilable_candidates")
    actionable = acquisition.get("actionable_candidates")
    if (
        acquisition.get("schema") != "acfqp.generic_multi_residual_acquisition.v24"
        or type(targets) is not list
        or not targets
        or targets != sorted(set(targets))
        or type(target_results) is not list
        or len(target_results) != len(targets)
        or type(compilable) is not list
        or type(actionable) is not list
        or acquisition.get("shared_physical_ground_support_labels") != queries
        or acquisition.get("shared_raw_transition_row_count") != rows
        or acquisition.get("compilable_candidate_count") != len(compilable)
        or acquisition.get("actionable_candidate_count") != len(actionable)
        or acquisition.get("compilable_target_columns")
        != [row.get("target_column") for row in compilable]
        or acquisition.get("actionable_target_columns")
        != [row.get("target_column") for row in actionable]
        or acquisition.get("per_target_label_consumption_summed_as_physical_samples")
        is not False
        or acquisition.get("same_shared_raw_query_pool_for_every_target") is not True
        or acquisition.get("proposal_only_not_safety_authority") is not True
        or acquisition.get("positive_excess_supports_may_only_overapproximate_successors")
        is not True
        or acquisition.get("complete_residual_world_model_synthesized") is not False
        or acquisition.get("global_exact_dynamics_claimed") is not False
    ):
        _fail("V67 multi acquisition inventory or claims changed")
    if len({row.get("target_column") for row in compilable}) != len(compilable):
        _fail("V67 compilable target uniqueness changed")
    if len({row.get("target_column") for row in actionable}) != len(actionable):
        _fail("V67 actionable target uniqueness changed")
    for target, result in zip(targets, target_results, strict=True):
        if (
            type(result) is not dict
            or result.get("target_column") != target
            or type(result.get("compilable_for_proposal_only_abstract_planning"))
            is not bool
            or type(result.get("actionable_for_abstract_planning")) is not bool
        ):
            _fail("V67 per-target result changed")
        _verify_total(
            result.get("total_acquisition"),
            result.get("full_shared_pool_replay"),
            queries,
            rows,
        )
    if (
        replay.get("multi_residual_acquisition_id")
        != acquisition["multi_residual_acquisition_id"]
        or replay.get("shared_physical_ground_support_labels") != queries
        or replay.get("target_count") != len(targets)
        or replay.get("compilable_candidate_count") != len(compilable)
        or replay.get("actionable_candidate_count") != len(actionable)
        or replay.get("all_target_totalizers_reconstructed") is not True
        or replay.get("future_transition_prediction_authority_present") is not False
    ):
        _fail("V67 multi replay changed")


def _episode(row: Any, family: str, seed: int, arm: str) -> dict[str, int]:
    if type(row) is not dict:
        _fail("V67 episode changed")
    failures = row.get("failed_certificates")
    distinctions = row.get("local_distinctions")
    raw_rows = row.get("raw_local_transition_rows")
    if not all(type(value) is list for value in (failures, distinctions, raw_rows)):
        _fail("V67 episode evidence inventory changed")
    if len(failures) != len(distinctions):
        _fail("V67 certificate/distinction count changed")
    flattened = []
    transitions = 0
    labels = 0
    contexts = set()
    for index, (failure, distinction) in enumerate(
        zip(failures, distinctions, strict=True)
    ):
        if (
            failure.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("failure_index") != index
            or distinction.get("raw_state") != failure.get("raw_state")
            or distinction.get("ground_support_labels") != 1
            or distinction.get("query_after_failed_certificate") is not True
        ):
            _fail("V67 certificate-before-query ordering changed")
        labels += 1
        if distinction.get("distinction_kind") == "QUERY_LOCAL_LEGAL_ACTION_SET":
            if failure.get("failure_kind") != "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT":
                _fail("V67 legality certificate changed")
        elif distinction.get("distinction_kind") == "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT":
            transitions += 1
            context = (tuple(distinction["raw_state"]), distinction.get("action_key"))
            if (
                context in contexts
                or distinction.get("action_key") != failure.get("action_key")
                or type(distinction.get("raw_transition_rows")) is not list
                or not distinction["raw_transition_rows"]
            ):
                _fail("V67 residual distinction changed")
            contexts.add(context)
            for transition in distinction["raw_transition_rows"]:
                action = transition.get("selected_action") if type(transition) is dict else None
                if (
                    type(action) is not dict
                    or transition.get("pre_vector") != distinction["raw_state"]
                    or action.get("action_key") != distinction.get("action_key")
                ):
                    _fail("V67 local transition join changed")
            flattened.extend(distinction["raw_transition_rows"])
        else:
            _fail("V67 distinction kind changed")
    attempts = row.get("joint_abstract_plan_attempt_count")
    successes = row.get("joint_abstract_plan_success_count")
    robust = row.get("joint_abstract_robust_closure_count")
    truncations = row.get("joint_abstract_robust_resource_truncation_count")
    maximum = row.get("maximum_simultaneously_compilable_residual_proposal_count")
    if (
        row.get("schema") != "acfqp.generic_multi_residual_certificate_episode.v26"
        or row.get("family") != family
        or row.get("seed") != seed
        or row.get("episode_index") != 0
        or row.get("arm") != arm
        or row.get("local_ground_support_labels") != labels
        or row.get("queried_state_action_count") != transitions
        or flattened != raw_rows
        or len(row.get("action_keys", [])) != row.get("execution_steps")
        or len(row.get("outcome_tape_sha256", [])) != row.get("execution_steps")
        or not all(
            type(value) is int
            for value in (attempts, successes, robust, truncations, maximum)
        )
        or not 0 <= successes <= attempts
        or not 0 <= robust <= successes
        or not 0 <= truncations <= successes
        or not 0 <= maximum <= len(row["final_multi_residual_acquisition"][
            "unknown_residual_target_columns"
        ])
        or row.get("success") is not True
        or row.get("shared_query_pool_reused_across_residual_targets") is not True
        or row.get("multiple_residual_proposals_jointly_compiled_when_available")
        is not True
        or row.get("all_ground_queries_followed_failed_certificates") is not True
        or row.get("query_local_exact_overlay_exclusively_used_for_safety") is not True
        or row.get("joint_abstract_plan_used_as_safety_authority") is not False
        or row.get("complete_residual_world_model_synthesized") is not False
    ):
        _fail("V67 episode accounting or claim boundary changed")
    _verify_multi(
        row.get("final_multi_residual_acquisition"),
        row.get("final_multi_residual_replay"),
        transitions,
        len(raw_rows),
    )
    return {
        "labels": labels,
        "steps": row["execution_steps"],
        "partial_compute": row["partial_planning_compute_events"],
        "joint_compute": row["joint_abstract_support_branch_evaluations"],
        "synthesis": row["multi_residual_synthesis_attempt_count"],
        "joint_successes": successes,
        "multi": int(maximum >= 2),
    }


def _occurrence(row: Any) -> dict[str, Any]:
    if type(row) is not dict:
        _fail("V67 occurrence changed")
    _id(
        domains.CONSTRUCTION_K7_MULTI_RESIDUAL_PLANNING_OCCURRENCE_V67_DOMAIN,
        row,
        "occurrence_id",
    )
    family, seed = row.get("family"), row.get("seed")
    if family not in _EXPECTED_SEEDS or seed not in _EXPECTED_SEEDS[family]:
        _fail("V67 occurrence identity changed")
    prior = _episode(row.get("prior_episode"), family, seed, "RESIDUAL_FACTOR_PRIOR_ON")
    strict = _episode(
        row.get("strict_episode"), family, seed, "STRICT_NO_RESIDUAL_FACTOR_PRIOR"
    )
    if (
        row["prior_episode"]["partial_candidate_id"]
        != row["strict_episode"]["partial_candidate_id"]
        or type(row.get("common_partial_ground_support_labels")) is not int
        or row.get("matched_environment_seed_episode_partial_candidate_and_observations")
        is not True
        or row.get("shared_physical_query_pool_not_multiplied_by_residual_target_count")
        is not True
        or row.get("joint_residual_model_never_discharges_certificate") is not True
    ):
        _fail("V67 occurrence matched join changed")
    return {
        "family": family,
        "partial": row["common_partial_ground_support_labels"],
        "prior": prior,
        "strict": strict,
    }


def verify_multi_residual_planning_campaign_bytes_v67(raw: bytes) -> bytes:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V67 campaign bytes are not canonical")
    _id(
        domains.CONSTRUCTION_K7_MULTI_RESIDUAL_PLANNING_CAMPAIGN_V67_DOMAIN,
        document,
        "campaign_id",
    )
    if (
        document.get("preregistration_id") != _PREREGISTRATION_ID
        or document.get("v66_campaign_id") != _V66_CAMPAIGN_ID
        or document.get("v66_verification_id") != _V66_VERIFICATION_ID
    ):
        _fail("V67 predecessor identity changed")
    occurrences = document.get("occurrences")
    expected = {
        (family, seed) for family, seeds in _EXPECTED_SEEDS.items() for seed in seeds
    }
    if (
        type(occurrences) is not list
        or len(occurrences) != 12
        or {(row.get("family"), row.get("seed")) for row in occurrences} != expected
    ):
        _fail("V67 occurrence inventory changed")
    facts = [_occurrence(row) for row in occurrences]
    prior_joint = sum(row["prior"]["joint_successes"] for row in facts)
    strict_joint = sum(row["strict"]["joint_successes"] for row in facts)
    prior_multi = sum(row["prior"]["multi"] for row in facts)
    strict_multi = sum(row["strict"]["multi"] for row in facts)
    accounting = {
        "offline_residual_library_labels": 204,
        "common_partial_acquisition_labels": sum(row["partial"] for row in facts),
        "prior_certificate_local_labels": sum(row["prior"]["labels"] for row in facts),
        "strict_certificate_local_labels": sum(row["strict"]["labels"] for row in facts),
        "prior_execution_steps": sum(row["prior"]["steps"] for row in facts),
        "strict_execution_steps": sum(row["strict"]["steps"] for row in facts),
        "prior_partial_planning_compute_events": sum(
            row["prior"]["partial_compute"] for row in facts
        ),
        "strict_partial_planning_compute_events": sum(
            row["strict"]["partial_compute"] for row in facts
        ),
        "prior_joint_abstract_support_branch_evaluations": sum(
            row["prior"]["joint_compute"] for row in facts
        ),
        "strict_joint_abstract_support_branch_evaluations": sum(
            row["strict"]["joint_compute"] for row in facts
        ),
        "prior_multi_residual_synthesis_attempts": sum(
            row["prior"]["synthesis"] for row in facts
        ),
        "strict_multi_residual_synthesis_attempts": sum(
            row["strict"]["synthesis"] for row in facts
        ),
        "all_axes_separate": True,
    }
    if document.get("accounting") != accounting:
        _fail("V67 accounting changed")
    family_rows = {}
    for family in _EXPECTED_SEEDS:
        selected = [row for row in facts if row["family"] == family]
        family_rows[family] = {
            "occurrence_count": len(selected),
            "prior_joint_abstract_plan_success_count": sum(
                row["prior"]["joint_successes"] for row in selected
            ),
            "strict_joint_abstract_plan_success_count": sum(
                row["strict"]["joint_successes"] for row in selected
            ),
            "prior_multi_proposal_occurrence_count": sum(
                row["prior"]["multi"] for row in selected
            ),
            "strict_multi_proposal_occurrence_count": sum(
                row["strict"]["multi"] for row in selected
            ),
            "prior_certificate_local_labels": sum(
                row["prior"]["labels"] for row in selected
            ),
            "strict_certificate_local_labels": sum(
                row["strict"]["labels"] for row in selected
            ),
        }
    if document.get("family_projections") != family_rows:
        _fail("V67 family projections changed")
    gate = {
        "prior_joint_abstract_plan_success_count": prior_joint,
        "strict_joint_abstract_plan_success_count": strict_joint,
        "prior_multi_proposal_occurrence_count": prior_multi,
        "strict_multi_proposal_occurrence_count": strict_multi,
        "required_relation": "PRIOR_JOINT_GT_ZERO_AND_PRIOR_MULTI_OCCURRENCES_GT_ZERO",
        "passed": prior_joint > 0 and prior_multi > 0,
        "prior_vs_strict_improvement_required": False,
        "certificate_local_label_reduction_required": False,
    }
    if document.get("registered_joint_planning_gate") != gate:
        _fail("V67 registered Gate changed")
    locks = {
        "multiple_residual_proposals_jointly_compiled_when_available": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "joint_abstract_plan_used_as_safety_authority": False,
        "producer_free_verification_present": False,
        "complete_residual_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    if any(document.get(key) != value for key, value in locks.items()):
        _fail("V67 claim locks changed")
    payload = {
        "schema": "acfqp.multi_residual_planning_verification.v67",
        "campaign_id": document["campaign_id"],
        "occurrence_count": len(facts),
        "prior_joint_abstract_plan_success_count": prior_joint,
        "strict_joint_abstract_plan_success_count": strict_joint,
        "prior_multi_proposal_occurrence_count": prior_multi,
        "strict_multi_proposal_occurrence_count": strict_multi,
        "prior_certificate_local_labels": accounting["prior_certificate_local_labels"],
        "strict_certificate_local_labels": accounting["strict_certificate_local_labels"],
        "certificate_before_query_ledgers_replayed": True,
        "query_local_overlay_rows_rejoined": True,
        "multi_and_per_target_acquisition_content_ids_recomputed": True,
        "residual_synthesis_and_joint_planner_not_independently_reexecuted": True,
        "producer_imported": False,
        "campaign_core_imported": False,
        "planner_imported": False,
        "official_execution_allowed": False,
        "status": "PRODUCER_FREE_MULTI_RESIDUAL_CERTIFICATE_LEDGER_VERIFIED",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v67(
            domains.CONSTRUCTION_K7_MULTI_RESIDUAL_PLANNING_VERIFICATION_V67_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V67 verification changed")
    return result


__all__ = ("verify_multi_residual_planning_campaign_bytes_v67",)
