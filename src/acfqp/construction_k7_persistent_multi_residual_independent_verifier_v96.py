"""Producer-free verification of the preserved V96 registered failure."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v96 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "93d3ae84f1a1f2e1a6cb7dac3f72d5e5ef24646b2e9f864657fee3a242443551"
CAMPAIGN_BYTE_COUNT = 1_115_065
CAMPAIGN_SHA256 = "7d34c7d96689536937a3e157a74aad597da7a707054326322cf6a19bcbbca4c5"
PREREGISTRATION_ID = "535c2020329e2dc0d6d2c9742dd2be0ddd1b5ec447d9e891b8468d7cc16d0d85"
TARGET_SEEDS = (997_101, 997_102)
TARGET_EPISODES = (21, 22, 23)
VERIFICATION_ID = "ce1a04b45959e2d34d2ad31b8e84630796dc377c24b7190e74f72e8faed20fca"
EXPECTED_CANONICAL_BYTE_COUNT = 1_127
EXPECTED_CANONICAL_SHA256 = "c4aaf1a8ec47d82d1486f00965e7960a06fe46654f8562a1ce730954c43ee722"

_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-multi-residual-sequence:v96\x00"
_MULTI_ACQUISITION_DOMAIN = b"acfqp:generic-multi-residual-acquisition:v24\x00"


class ConstructionK7PersistentMultiResidualIndependentVerifierV96Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PersistentMultiResidualIndependentVerifierV96Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _check_generic_id(document: Any, key: str, domain: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V96 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != _generic_id(domain, payload):
        _fail(f"V96 {key} content identity changed")


def _check_v96_id(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V96 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v96(domain, payload):
        _fail(f"V96 {key} content identity changed")


def _group_count(rows: Any) -> int:
    if type(rows) is not list:
        _fail("V96 overlay row inventory changed")
    groups = set()
    for row in rows:
        action = row.get("selected_action") if type(row) is dict else None
        if (
            type(row) is not dict
            or type(row.get("pre_vector")) is not list
            or type(action) is not dict
            or type(action.get("action_key")) is not int
        ):
            _fail("V96 overlay row schema changed")
        groups.add((tuple(row["pre_vector"]), action["action_key"]))
    return len(groups)


def _check_failure_query_pairing(sequence: Mapping[str, Any]) -> None:
    failures = sequence.get("all_failed_certificates")
    distinctions = sequence.get("all_local_distinctions")
    if (
        type(failures) is not list
        or type(distinctions) is not list
        or len(failures) != len(distinctions)
        or [row.get("failure_index") for row in failures]
        != list(range(len(failures)))
        or [row.get("failure_index") for row in distinctions]
        != list(range(len(distinctions)))
        or any(
            row.get("ground_query_performed_before_failure") is not False
            for row in failures
        )
        or any(
            row.get("query_after_failed_certificate") is not True
            for row in distinctions
        )
        or sequence.get("every_new_ground_query_followed_a_failed_certificate")
        is not True
    ):
        _fail("V96 certificate-failure-only query discipline changed")


def _check_sequence(
    sequence: Any,
    *,
    seed: int,
    arm: str,
) -> tuple[int, int, int]:
    _check_generic_id(sequence, "sequence_id", _SEQUENCE_DOMAIN)
    rows = sequence.get("persistent_exact_overlay_rows")
    first = sequence.get("first_online_multi_residual_episode")
    later = sequence.get("later_persistent_episodes")
    retained = sequence.get("retained_joint_multi_residual_acquisition")
    if (
        sequence.get("schema")
        != "acfqp.generic_persistent_multi_residual_sequence.v96"
        or sequence.get("family") != "COUPLED_EXCHANGE"
        or sequence.get("seed") != seed
        or sequence.get("episode_indices") != list(TARGET_EPISODES)
        or sequence.get("arm") != arm
        or type(first) is not dict
        or type(later) is not list
        or len(later) != len(TARGET_EPISODES) - 1
        or retained is not None
        or sequence.get("retained_joint_activation") is not None
        or sequence.get("retained_joint_proposal_count") != 0
        or sequence.get("later_joint_abstract_plan_receipt_count") != 0
        or sequence.get(
            "multiple_residual_proposals_jointly_compiled_into_one_abstract_successor"
        )
        is not False
        or sequence.get("later_query_ground_support_labels") != 0
        or sequence.get(
            "retained_joint_model_is_fallible_action_ordering_heuristic"
        )
        is not True
        or sequence.get("persistent_exact_overlay_exclusively_discharges_safety")
        is not True
        or sequence.get("complete_world_model_synthesized") is not False
        or sequence.get("official_execution_allowed") is not False
        or type(rows) is not list
        or sequence.get("persistent_exact_overlay_sha256")
        != hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
        or sequence.get("persistent_exact_support_group_count")
        != _group_count(rows)
    ):
        _fail("V96 preserved failed sequence boundary changed")
    acquisition = first.get("final_multi_residual_acquisition")
    _check_generic_id(
        acquisition, "multi_residual_acquisition_id", _MULTI_ACQUISITION_DOMAIN
    )
    if (
        acquisition.get("schema") != "acfqp.generic_multi_residual_acquisition.v24"
        or acquisition.get("compilable_candidate_count") != 1
        or acquisition.get("actionable_candidate_count") != 1
        or acquisition.get("abstention_count") != 1
        or first.get("multi_residual_proposal_activations") != []
        or first.get("maximum_simultaneously_compilable_residual_proposal_count")
        != 1
        or any(
            episode.get("new_certificate_labels_charged_this_episode") != 0
            for episode in later
        )
    ):
        _fail("V96 fresh target exposed a different residual failure")
    _check_failure_query_pairing(sequence)
    return (
        sequence["lifetime_target_ground_support_labels"],
        sequence["later_execution_action_matches_any_abstract_proposal_count"],
        sequence["later_query_ground_support_labels"],
    )


def _verify_campaign_document(document: Any) -> dict[str, Any]:
    _check_v96_id(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_PERSISTENT_MULTI_RESIDUAL_CAMPAIGN_V96_DOMAIN,
    )
    occurrences = document.get("target_occurrences")
    if (
        document.get("schema") != "acfqp.persistent_multi_residual_campaign.v96"
        or document.get("campaign_id") != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or type(occurrences) is not list
        or len(occurrences) != len(TARGET_SEEDS)
        or [row.get("seed") for row in occurrences] != list(TARGET_SEEDS)
    ):
        _fail("V96 campaign identity inventory changed")
    meta_total = 0
    no_prior_total = 0
    direct_total = 0
    matches = 0
    for occurrence, seed in zip(occurrences, TARGET_SEEDS, strict=True):
        _check_v96_id(
            occurrence,
            "occurrence_id",
            domains.CONSTRUCTION_K7_PERSISTENT_MULTI_RESIDUAL_OCCURRENCE_V96_DOMAIN,
        )
        if (
            occurrence.get("family") != "COUPLED_EXCHANGE"
            or occurrence.get("episode_indices") != list(TARGET_EPISODES)
            or occurrence.get(
                "same_partial_candidate_and_observations_between_residual_prior_arms"
            )
            is not True
            or occurrence.get("meta_prior_partial_acquisition")
            != occurrence.get("no_prior_partial_acquisition")
            or occurrence.get("registered_gate", {}).get("passed") is not False
            or occurrence.get("registered_gate", {}).get(
                "meta_retained_joint_proposal_count_at_least_two"
            )
            is not False
            or occurrence.get("registered_gate", {}).get(
                "meta_later_joint_abstract_plan_used"
            )
            is not False
        ):
            _fail("V96 matched failed occurrence changed")
        meta, meta_matches, later_meta = _check_sequence(
            occurrence.get("meta_prior_persistent_sequence"),
            seed=seed,
            arm="RESIDUAL_FACTOR_META_PRIOR_ON",
        )
        no_prior, _no_prior_matches, later_no_prior = _check_sequence(
            occurrence.get("no_prior_persistent_sequence"),
            seed=seed,
            arm="STRICT_NO_RESIDUAL_FACTOR_META_PRIOR",
        )
        direct = occurrence.get("strict_cold_direct_sequence", {}).get(
            "lifetime_target_ground_support_labels"
        )
        if (
            type(direct) is not int
            or meta != no_prior
            or not meta < direct
            or later_meta != 0
            or later_no_prior != 0
        ):
            _fail("V96 occurrence accounting changed")
        meta_total += meta
        no_prior_total += no_prior
        direct_total += direct
        matches += meta_matches
    accounting = document.get("accounting")
    if (
        type(accounting) is not dict
        or accounting.get("meta_prior_lifetime_target_labels") != meta_total
        or accounting.get("no_residual_prior_lifetime_target_labels")
        != no_prior_total
        or accounting.get("strict_cold_direct_lifetime_target_labels")
        != direct_total
        or accounting.get("strict_minus_meta_prior_lifetime_target_labels")
        != direct_total - meta_total
        or accounting.get("later_joint_abstract_plan_receipt_count") != 0
        or accounting.get(
            "later_execution_action_matches_abstract_proposal_count"
        )
        != matches
        or accounting.get(
            "sample_labels_execution_steps_synthesis_and_planning_compute_separate"
        )
        is not True
        or accounting.get("scalar_cost_aggregation_performed") is not False
        or (meta_total, no_prior_total, direct_total) != (96, 96, 174)
    ):
        _fail("V96 aggregate accounting changed")
    gate = document.get("registered_gate")
    if (
        type(gate) is not dict
        or gate.get("completed_passing_target_occurrence_count") != 0
        or gate.get(
            "every_target_retained_at_least_two_joint_residual_proposals"
        )
        is not False
        or gate.get("every_target_later_queries_ground_label_free") is not True
        or gate.get("aggregate_meta_labels_noninferior_to_no_residual_prior")
        is not True
        or gate.get("aggregate_meta_labels_strictly_below_cold_direct") is not True
        or gate.get("joint_abstract_planning_and_execution_match_observed")
        is not False
        or gate.get("passed") is not False
        or document.get("multiple_residual_proposals_jointly_compiled_and_persisted")
        is not False
        or document.get("persistent_exact_overlay_reduced_repeated_query_sample_tax")
        is not False
        or document.get("producer_free_verification_present") is not False
        or document.get("complete_world_model_synthesized") is not False
        or document.get("global_exact_dynamics_claimed") is not False
        or document.get("arbitrary_domain_transfer_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V96 registered failure or claim locks changed")
    return {
        "schema": "acfqp.persistent_multi_residual_verification.v96",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_PERSISTENT_MULTI_RESIDUAL_GATE_FAILURE_VERIFIED",
        "verified_failure": {
            "fresh_target_count": len(occurrences),
            "fresh_target_seeds": list(TARGET_SEEDS),
            "meta_prior_lifetime_target_labels": meta_total,
            "no_residual_prior_lifetime_target_labels": no_prior_total,
            "strict_cold_direct_lifetime_target_labels": direct_total,
            "later_query_ground_support_labels": 0,
            "retained_joint_proposal_count_per_target": [0, 0],
            "failure_is_joint_residual_availability_not_sample_reuse": True,
        },
        "campaign_bytes_replayed_without_producer": True,
        "unfavourable_result_preserved_without_selection": True,
        "persistent_joint_residual_integration_verified": False,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def verify_persistent_multi_residual_campaign_bytes_v96(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V96 campaign bytes differ from the frozen failure")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V96 campaign bytes are not canonical")
    return _verify_campaign_document(document)


def freeze_persistent_multi_residual_verification_v96(raw: bytes) -> bytes:
    payload = _verify_campaign_document(loads_canonical_json(raw))
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v96(
            domains.CONSTRUCTION_K7_PERSISTENT_MULTI_RESIDUAL_VERIFICATION_V96_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V96 frozen verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_persistent_multi_residual_verification_v96",
    "verify_persistent_multi_residual_campaign_bytes_v96",
)
