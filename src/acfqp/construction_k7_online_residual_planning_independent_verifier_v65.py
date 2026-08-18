"""Producer-free verification of frozen V65 certificate/query evidence."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v65 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


VERIFICATION_ID = "7c33dd9829f58682936f4798e0a6186870c03fcff198765511136dc1739ebea4"
EXPECTED_CANONICAL_BYTE_COUNT = 741
EXPECTED_CANONICAL_SHA256 = "f62da9828100c75e2e0271459272029d0f90355b98cd587582a9a394031d1bf7"
_PREREGISTRATION_ID = "a50a86b6f05d4ec7f027f859936c4921c9a1dce58faf7034bcc6f1c39804f504"
_V64_CAMPAIGN_ID = "b995c21c6e9b6f558d61cac084f9f8dd03eb694ffc0d026ace224e0abb175647"
_V64_VERIFICATION_ID = "fe6b372c86255a7150b5321a394203607e78e1f333d238786a85f6e3b344a2bf"
_TOTAL_DOMAIN = b"acfqp:total-adaptive-residual-acquisition:v20\x00"
_ADAPTIVE_DOMAIN = b"acfqp:adaptive-residual-factor-acquisition:v19\x00"
_EXPECTED_SEEDS = {
    "BALANCED_BATCH_REFINEMENT": set(range(661_101, 661_107)),
    "COUPLED_EXCHANGE": set(range(662_101, 662_107)),
    "MAINTENANCE_CASCADE": set(range(663_101, 663_107)),
}


class ConstructionK7OnlineResidualPlanningIndependentVerifierV65Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OnlineResidualPlanningIndependentVerifierV65Error(message)


def _id(domain: str, document: dict[str, Any], key: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v65(domain, payload) != document.get(key):
        _fail(f"V65 {key} changed")


def _content_hash(document: dict[str, Any], key: str, prefix: bytes) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    expected = hashlib.sha256(prefix + canonical_json_bytes(payload)).hexdigest()
    if document.get(key) != expected:
        _fail(f"V65 embedded {key} changed")


def _verify_total_acquisition(
    acquisition: Any, replay: Any, query_count: int, row_count: int
) -> None:
    if type(acquisition) is not dict or type(replay) is not dict:
        _fail("V65 total acquisition or replay changed")
    _content_hash(acquisition, "total_acquisition_id", _TOTAL_DOMAIN)
    status = acquisition.get("status")
    if status not in (
        "STATISTICAL_PROPOSAL_ISSUED",
        "ABSTAINED_INSUFFICIENT_CALIBRATED_EVIDENCE",
    ):
        _fail("V65 total acquisition status changed")
    predecessor = acquisition.get("predecessor_acquisition")
    if status == "STATISTICAL_PROPOSAL_ISSUED":
        if type(predecessor) is not dict:
            _fail("V65 issued acquisition predecessor changed")
        _content_hash(predecessor, "acquisition_id", _ADAPTIVE_DOMAIN)
    elif predecessor is not None or acquisition.get("candidate") is not None:
        _fail("V65 abstention acquired a candidate")
    labels = acquisition.get("ground_support_labels")
    consumed = acquisition.get("raw_transition_rows_consumed")
    if (
        type(labels) is not int
        or not 0 < labels <= query_count
        or type(consumed) is not int
        or not 0 < consumed <= row_count
        or acquisition.get("proposal_only_not_safety_authority") is not True
        or acquisition.get("complete_residual_world_model_synthesized") is not False
        or replay.get("total_acquisition_id") != acquisition["total_acquisition_id"]
        or replay.get("status") != status
        or replay.get("full_query_stream_label_count") != query_count
        or replay.get("full_query_stream_raw_transition_count") != row_count
        or replay.get("future_transition_prediction_authority_present") is not False
    ):
        _fail("V65 total acquisition accounting changed")


def _verify_episode(
    episode: Any, family: str, seed: int, expected_arm: str
) -> dict[str, int]:
    if type(episode) is not dict:
        _fail("V65 episode changed")
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    raw_rows = episode.get("raw_local_transition_rows")
    if not all(type(value) is list for value in (failures, distinctions, raw_rows)):
        _fail("V65 episode evidence inventory changed")
    if len(failures) != len(distinctions):
        _fail("V65 certificate/distinction cardinality changed")
    flattened = []
    transition_contexts = set()
    legality = 0
    transition = 0
    for index, (failure, distinction) in enumerate(
        zip(failures, distinctions, strict=True)
    ):
        if (
            failure.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("failure_index") != index
            or distinction.get("ground_support_labels") != 1
            or distinction.get("query_after_failed_certificate") is not True
            or distinction.get("raw_state") != failure.get("raw_state")
        ):
            _fail("V65 certificate-before-query ledger changed")
        kind = distinction.get("distinction_kind")
        if kind == "QUERY_LOCAL_LEGAL_ACTION_SET":
            legality += 1
            if failure.get("failure_kind") != "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT":
                _fail("V65 legality certificate kind changed")
        elif kind == "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT":
            transition += 1
            if (
                failure.get("failure_kind")
                != "UNKNOWN_RESIDUAL_PREVENTS_ALL_BRANCH_SAFETY_PROOF"
                or distinction.get("action_key") != failure.get("action_key")
                or type(distinction.get("raw_transition_rows")) is not list
                or not distinction["raw_transition_rows"]
            ):
                _fail("V65 transition certificate kind changed")
            context = (tuple(distinction["raw_state"]), distinction["action_key"])
            if context in transition_contexts:
                _fail("V65 transition support queried twice")
            transition_contexts.add(context)
            for row in distinction["raw_transition_rows"]:
                selected = row.get("selected_action") if type(row) is dict else None
                if (
                    type(selected) is not dict
                    or row.get("pre_vector") != distinction["raw_state"]
                    or selected.get("action_key") != distinction["action_key"]
                ):
                    _fail("V65 local transition row join changed")
            flattened.extend(distinction["raw_transition_rows"])
        else:
            _fail("V65 local distinction kind changed")
    labels = legality + transition
    action_keys = episode.get("action_keys")
    tapes = episode.get("outcome_tape_sha256")
    if (
        episode.get("schema") != "acfqp.generic_online_residual_guided_episode.v21"
        or episode.get("family") != family
        or episode.get("seed") != seed
        or episode.get("episode_index") != 0
        or episode.get("arm") != expected_arm
        or episode.get("local_ground_support_labels") != labels
        or episode.get("queried_state_action_count") != transition
        or flattened != raw_rows
        or type(action_keys) is not list
        or type(tapes) is not list
        or len(action_keys) != episode.get("execution_steps")
        or len(tapes) != episode.get("execution_steps")
        or episode.get("success") is not True
        or episode.get("all_ground_queries_followed_failed_certificates") is not True
        or episode.get("partial_and_residual_models_used_only_for_abstract_action_order")
        is not True
        or episode.get("query_local_exact_overlay_used_for_safety") is not True
        or episode.get("residual_proposal_used_as_safety_authority") is not False
        or episode.get(
            "only_action_conditioned_zero_excess_residual_proposals_guided_ordering"
        )
        is not True
        or episode.get("complete_residual_world_model_synthesized") is not False
    ):
        _fail("V65 episode accounting or claim boundary changed")
    _verify_total_acquisition(
        episode.get("final_total_residual_acquisition"),
        episode.get("final_total_residual_replay"),
        transition,
        len(raw_rows),
    )
    activations = episode.get("residual_proposal_activations")
    if type(activations) is not list:
        _fail("V65 residual activation inventory changed")
    for activation in activations:
        if (
            type(activation) is not dict
            or type(activation.get("local_residual_query_count")) is not int
            or not 0 < activation["local_residual_query_count"] <= transition
            or type(activation.get("candidate_id")) is not str
            or len(activation["candidate_id"]) != 64
            or type(activation.get("acquisition_id")) is not str
            or len(activation["acquisition_id"]) != 64
        ):
            _fail("V65 residual activation fact changed")
    return {
        "labels": labels,
        "legality": legality,
        "transition": transition,
        "steps": episode["execution_steps"],
        "planning": episode["abstract_planning_compute_events"],
        "synthesis": episode["residual_synthesis_attempt_count"],
        "activations": len(activations),
    }


def _verify_occurrence(row: Any) -> dict[str, Any]:
    if type(row) is not dict:
        _fail("V65 occurrence changed")
    _id(
        domains.CONSTRUCTION_K7_ONLINE_RESIDUAL_PLANNING_OCCURRENCE_V65_DOMAIN,
        row,
        "occurrence_id",
    )
    family = row.get("family")
    seed = row.get("seed")
    if family not in _EXPECTED_SEEDS or seed not in _EXPECTED_SEEDS[family]:
        _fail("V65 occurrence identity changed")
    prior = _verify_episode(
        row.get("prior_episode"), family, seed, "RESIDUAL_FACTOR_PRIOR_ON"
    )
    strict = _verify_episode(
        row.get("strict_episode"),
        family,
        seed,
        "STRICT_NO_RESIDUAL_FACTOR_PRIOR",
    )
    if (
        row["prior_episode"]["partial_candidate_id"]
        != row["strict_episode"]["partial_candidate_id"]
        or row.get("common_partial_acquisition_id") is None
        or type(row.get("common_partial_ground_support_labels")) is not int
        or row.get("prior_label_breakdown")
        != {
            "legality_labels": prior["legality"],
            "transition_labels": prior["transition"],
        }
        or row.get("strict_label_breakdown")
        != {
            "legality_labels": strict["legality"],
            "transition_labels": strict["transition"],
        }
        or row.get("matched_environment_seed_and_episode") is not True
        or row.get("same_partial_candidate_and_observations") is not True
        or row.get("proposal_never_discharges_certificate") is not True
        or row.get("only_switched_variable")
        != "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH"
    ):
        _fail("V65 occurrence matched join changed")
    return {
        "family": family,
        "partial": row["common_partial_ground_support_labels"],
        "prior": prior,
        "strict": strict,
    }


def verify_online_residual_planning_campaign_bytes_v65(raw: bytes) -> bytes:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V65 campaign bytes are not canonical")
    _id(
        domains.CONSTRUCTION_K7_ONLINE_RESIDUAL_PLANNING_CAMPAIGN_V65_DOMAIN,
        document,
        "campaign_id",
    )
    if (
        document.get("preregistration_id") != _PREREGISTRATION_ID
        or document.get("v64_campaign_id") != _V64_CAMPAIGN_ID
        or document.get("v64_verification_id") != _V64_VERIFICATION_ID
    ):
        _fail("V65 predecessor identity changed")
    occurrences = document.get("occurrences")
    if type(occurrences) is not list or len(occurrences) != 18:
        _fail("V65 occurrence count changed")
    identities = {(row.get("family"), row.get("seed")) for row in occurrences}
    expected = {
        (family, seed) for family, seeds in _EXPECTED_SEEDS.items() for seed in seeds
    }
    if identities != expected:
        _fail("V65 occurrence inventory changed")
    facts = [_verify_occurrence(row) for row in occurrences]
    prior_labels = sum(row["prior"]["labels"] for row in facts)
    strict_labels = sum(row["strict"]["labels"] for row in facts)
    family_projection = {}
    for family in _EXPECTED_SEEDS:
        selected = [row for row in facts if row["family"] == family]
        family_prior = sum(row["prior"]["labels"] for row in selected)
        family_strict = sum(row["strict"]["labels"] for row in selected)
        family_projection[family] = {
            "occurrence_count": len(selected),
            "prior_certificate_local_labels": family_prior,
            "strict_certificate_local_labels": family_strict,
            "observed_label_difference_strict_minus_prior": family_strict
            - family_prior,
        }
    expected_accounting = {
        "offline_residual_library_labels": 204,
        "common_partial_acquisition_labels": sum(row["partial"] for row in facts),
        "prior_certificate_local_labels": prior_labels,
        "strict_certificate_local_labels": strict_labels,
        "observed_online_label_difference_strict_minus_prior": strict_labels
        - prior_labels,
        "prior_execution_steps": sum(row["prior"]["steps"] for row in facts),
        "strict_execution_steps": sum(row["strict"]["steps"] for row in facts),
        "prior_partial_planning_compute_events": sum(
            row["prior"]["planning"] for row in facts
        ),
        "strict_partial_planning_compute_events": sum(
            row["strict"]["planning"] for row in facts
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
        _fail("V65 campaign accounting changed")
    if document.get("family_projections") != family_projection:
        _fail("V65 family projection changed")
    expected_gate = {
        "relation": "PRIOR_CERTIFICATE_LOCAL_LABELS_LE_STRICT_CERTIFICATE_LOCAL_LABELS",
        "passed": prior_labels <= strict_labels,
        "positive_reduction_required": False,
    }
    if document.get("registered_noninferiority_gate") != expected_gate:
        _fail("V65 registered Gate changed")
    locks = {
        "all_ground_queries_followed_failed_certificates": True,
        "residual_proposals_used_only_for_abstract_action_order": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
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
        _fail("V65 campaign claim locks changed")
    payload = {
        "schema": "acfqp.online_residual_planning_verification.v65",
        "campaign_id": document["campaign_id"],
        "occurrence_count": len(facts),
        "prior_certificate_local_labels": prior_labels,
        "strict_certificate_local_labels": strict_labels,
        "observed_online_label_saving": strict_labels - prior_labels,
        "certificate_before_query_ledgers_replayed": True,
        "query_local_overlay_rows_rejoined": True,
        "adaptive_acquisition_content_ids_recomputed": True,
        "planner_action_order_not_independently_reexecuted": True,
        "producer_imported": False,
        "campaign_core_imported": False,
        "planner_imported": False,
        "official_execution_allowed": False,
        "status": "PRODUCER_FREE_ONLINE_RESIDUAL_CERTIFICATE_LEDGER_VERIFIED",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v65(
            domains.CONSTRUCTION_K7_ONLINE_RESIDUAL_PLANNING_VERIFICATION_V65_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V65 verification changed")
    return result


__all__ = ("verify_online_residual_planning_campaign_bytes_v65",)
