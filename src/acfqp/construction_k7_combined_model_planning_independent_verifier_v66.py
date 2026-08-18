"""Producer-free ledger/accounting verification for frozen V66 bytes."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v66 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


VERIFICATION_ID = "1b42294ccd1785763de545da0b7a159526fc4c23a212a956e341257d1149fc12"
EXPECTED_CANONICAL_BYTE_COUNT = 800
EXPECTED_CANONICAL_SHA256 = "52e57d40f3b168cc4b2da58fa089e32abc6735cfca2ce511405828fc884c51a1"
_PREREGISTRATION_ID = "93602221454dd824a4c8b139a935427b22bc21bd04f56fe6992a977d37a8952e"
_V65_CAMPAIGN_ID = "0754c5575634d075a005d809589dc00198ad4b66be5afcee73c15b3317f9eeda"
_V65_VERIFICATION_ID = "7c33dd9829f58682936f4798e0a6186870c03fcff198765511136dc1739ebea4"
_TOTAL_DOMAIN = b"acfqp:total-adaptive-residual-acquisition:v20\x00"
_ADAPTIVE_DOMAIN = b"acfqp:adaptive-residual-factor-acquisition:v19\x00"
_EXPECTED_SEEDS = {
    "BALANCED_BATCH_REFINEMENT": set(range(671_101, 671_105)),
    "COUPLED_EXCHANGE": set(range(672_101, 672_105)),
    "MAINTENANCE_CASCADE": set(range(673_101, 673_105)),
}


class ConstructionK7CombinedModelPlanningIndependentVerifierV66Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CombinedModelPlanningIndependentVerifierV66Error(message)


def _id(domain: str, document: dict[str, Any], key: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v66(domain, payload) != document.get(key):
        _fail(f"V66 {key} changed")


def _hash(document: dict[str, Any], key: str, prefix: bytes) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != hashlib.sha256(
        prefix + canonical_json_bytes(payload)
    ).hexdigest():
        _fail(f"V66 embedded {key} changed")


def _verify_acquisition(acquisition: Any, replay: Any, queries: int, rows: int) -> None:
    if type(acquisition) is not dict or type(replay) is not dict:
        _fail("V66 final acquisition changed")
    _hash(acquisition, "total_acquisition_id", _TOTAL_DOMAIN)
    status = acquisition.get("status")
    if status not in (
        "STATISTICAL_PROPOSAL_ISSUED",
        "ABSTAINED_INSUFFICIENT_CALIBRATED_EVIDENCE",
    ):
        _fail("V66 final acquisition status changed")
    predecessor = acquisition.get("predecessor_acquisition")
    if status == "STATISTICAL_PROPOSAL_ISSUED":
        if type(predecessor) is not dict:
            _fail("V66 final acquisition predecessor changed")
        _hash(predecessor, "acquisition_id", _ADAPTIVE_DOMAIN)
    elif predecessor is not None or acquisition.get("candidate") is not None:
        _fail("V66 abstention candidate changed")
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
        _fail("V66 final acquisition accounting changed")


def _episode(row: Any, family: str, seed: int, arm: str) -> dict[str, int]:
    if type(row) is not dict:
        _fail("V66 episode changed")
    failures = row.get("failed_certificates")
    distinctions = row.get("local_distinctions")
    raw_rows = row.get("raw_local_transition_rows")
    if not all(type(value) is list for value in (failures, distinctions, raw_rows)):
        _fail("V66 episode evidence inventory changed")
    if len(failures) != len(distinctions):
        _fail("V66 certificate/distinction count changed")
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
            _fail("V66 certificate-before-query ordering changed")
        labels += 1
        if distinction.get("distinction_kind") == "QUERY_LOCAL_LEGAL_ACTION_SET":
            if failure.get("failure_kind") != "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT":
                _fail("V66 legality certificate changed")
        elif distinction.get("distinction_kind") == "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT":
            transitions += 1
            context = (tuple(distinction["raw_state"]), distinction.get("action_key"))
            if (
                context in contexts
                or distinction.get("action_key") != failure.get("action_key")
                or type(distinction.get("raw_transition_rows")) is not list
                or not distinction["raw_transition_rows"]
            ):
                _fail("V66 residual distinction changed")
            contexts.add(context)
            for transition in distinction["raw_transition_rows"]:
                action = transition.get("selected_action") if type(transition) is dict else None
                if (
                    type(action) is not dict
                    or transition.get("pre_vector") != distinction["raw_state"]
                    or action.get("action_key") != distinction.get("action_key")
                ):
                    _fail("V66 local transition join changed")
            flattened.extend(distinction["raw_transition_rows"])
        else:
            _fail("V66 distinction kind changed")
    attempts = row.get("combined_abstract_plan_attempt_count")
    successes = row.get("combined_abstract_plan_success_count")
    robust = row.get("combined_abstract_robust_closure_count")
    truncations = row.get("combined_abstract_robust_resource_truncation_count")
    if (
        row.get("schema") != "acfqp.generic_combined_model_certificate_episode.v23"
        or row.get("family") != family
        or row.get("seed") != seed
        or row.get("episode_index") != 0
        or row.get("arm") != arm
        or row.get("local_ground_support_labels") != labels
        or row.get("queried_state_action_count") != transitions
        or flattened != raw_rows
        or len(row.get("action_keys", [])) != row.get("execution_steps")
        or len(row.get("outcome_tape_sha256", [])) != row.get("execution_steps")
        or not all(type(value) is int for value in (attempts, successes, robust, truncations))
        or not 0 <= successes <= attempts
        or not 0 <= robust <= successes
        or not 0 <= truncations <= successes
        or row.get("success") is not True
        or row.get("combined_partial_residual_model_used_for_multistep_abstract_search")
        is not True
        or row.get("all_ground_queries_followed_failed_certificates") is not True
        or row.get("query_local_exact_overlay_exclusively_used_for_safety") is not True
        or row.get("combined_abstract_plan_used_as_safety_authority") is not False
        or row.get("complete_residual_world_model_synthesized") is not False
    ):
        _fail("V66 episode accounting or claim boundary changed")
    _verify_acquisition(
        row.get("final_total_residual_acquisition"),
        row.get("final_total_residual_replay"),
        transitions,
        len(raw_rows),
    )
    return {
        "labels": labels,
        "steps": row["execution_steps"],
        "partial_compute": row["partial_planning_compute_events"],
        "combined_compute": row["combined_abstract_support_branch_evaluations"],
        "synthesis": row["residual_synthesis_attempt_count"],
        "combined_successes": successes,
    }


def _occurrence(row: Any) -> dict[str, Any]:
    if type(row) is not dict:
        _fail("V66 occurrence changed")
    _id(
        domains.CONSTRUCTION_K7_COMBINED_MODEL_PLANNING_OCCURRENCE_V66_DOMAIN,
        row,
        "occurrence_id",
    )
    family, seed = row.get("family"), row.get("seed")
    if family not in _EXPECTED_SEEDS or seed not in _EXPECTED_SEEDS[family]:
        _fail("V66 occurrence identity changed")
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
        or row.get("combined_model_never_discharges_certificate") is not True
    ):
        _fail("V66 occurrence matched join changed")
    return {
        "family": family,
        "partial": row["common_partial_ground_support_labels"],
        "prior": prior,
        "strict": strict,
    }


def verify_combined_model_planning_campaign_bytes_v66(raw: bytes) -> bytes:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V66 campaign bytes are not canonical")
    _id(
        domains.CONSTRUCTION_K7_COMBINED_MODEL_PLANNING_CAMPAIGN_V66_DOMAIN,
        document,
        "campaign_id",
    )
    if (
        document.get("preregistration_id") != _PREREGISTRATION_ID
        or document.get("v65_campaign_id") != _V65_CAMPAIGN_ID
        or document.get("v65_verification_id") != _V65_VERIFICATION_ID
    ):
        _fail("V66 predecessor identity changed")
    occurrences = document.get("occurrences")
    expected_identities = {
        (family, seed) for family, seeds in _EXPECTED_SEEDS.items() for seed in seeds
    }
    if (
        type(occurrences) is not list
        or len(occurrences) != 12
        or {(row.get("family"), row.get("seed")) for row in occurrences}
        != expected_identities
    ):
        _fail("V66 occurrence inventory changed")
    facts = [_occurrence(row) for row in occurrences]
    prior_successes = sum(row["prior"]["combined_successes"] for row in facts)
    strict_successes = sum(row["strict"]["combined_successes"] for row in facts)
    expected_accounting = {
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
        "prior_combined_abstract_support_branch_evaluations": sum(
            row["prior"]["combined_compute"] for row in facts
        ),
        "strict_combined_abstract_support_branch_evaluations": sum(
            row["strict"]["combined_compute"] for row in facts
        ),
        "prior_residual_synthesis_attempts": sum(
            row["prior"]["synthesis"] for row in facts
        ),
        "strict_residual_synthesis_attempts": sum(
            row["strict"]["synthesis"] for row in facts
        ),
        "all_axes_separate": True,
    }
    if document.get("accounting") != expected_accounting:
        _fail("V66 accounting changed")
    family_rows = {}
    for family in _EXPECTED_SEEDS:
        selected = [row for row in facts if row["family"] == family]
        family_rows[family] = {
            "occurrence_count": len(selected),
            "prior_combined_abstract_plan_success_count": sum(
                row["prior"]["combined_successes"] for row in selected
            ),
            "strict_combined_abstract_plan_success_count": sum(
                row["strict"]["combined_successes"] for row in selected
            ),
            "prior_certificate_local_labels": sum(
                row["prior"]["labels"] for row in selected
            ),
            "strict_certificate_local_labels": sum(
                row["strict"]["labels"] for row in selected
            ),
        }
    if document.get("family_projections") != family_rows:
        _fail("V66 family projections changed")
    expected_gate = {
        "prior_combined_abstract_plan_success_count": prior_successes,
        "strict_combined_abstract_plan_success_count": strict_successes,
        "required_relation": "PRIOR_GT_ZERO_AND_PRIOR_GE_STRICT",
        "passed": prior_successes > 0 and prior_successes >= strict_successes,
        "certificate_local_label_reduction_required": False,
    }
    if document.get("registered_combined_planning_gate") != expected_gate:
        _fail("V66 registered Gate changed")
    locks = {
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "combined_abstract_plan_used_as_safety_authority": False,
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
        _fail("V66 claim locks changed")
    payload = {
        "schema": "acfqp.combined_model_planning_verification.v66",
        "campaign_id": document["campaign_id"],
        "occurrence_count": len(facts),
        "prior_combined_abstract_plan_success_count": prior_successes,
        "strict_combined_abstract_plan_success_count": strict_successes,
        "prior_certificate_local_labels": expected_accounting[
            "prior_certificate_local_labels"
        ],
        "strict_certificate_local_labels": expected_accounting[
            "strict_certificate_local_labels"
        ],
        "certificate_before_query_ledgers_replayed": True,
        "query_local_overlay_rows_rejoined": True,
        "adaptive_acquisition_content_ids_recomputed": True,
        "combined_planner_not_independently_reexecuted": True,
        "producer_imported": False,
        "campaign_core_imported": False,
        "planner_imported": False,
        "official_execution_allowed": False,
        "status": "PRODUCER_FREE_COMBINED_MODEL_CERTIFICATE_LEDGER_VERIFIED",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v66(
            domains.CONSTRUCTION_K7_COMBINED_MODEL_PLANNING_VERIFICATION_V66_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V66 verification changed")
    return result


__all__ = ("verify_combined_model_planning_campaign_bytes_v66",)
