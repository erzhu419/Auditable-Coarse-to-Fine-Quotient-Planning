"""Producer-free verification of the preserved V101 registered failure."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_agreement_shielded_independent_verifier_v99 as v99
from acfqp import construction_k7_domain_registry_extension_v100 as domains_v100
from acfqp import construction_k7_domain_registry_extension_v101 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "f6cafbcdb148095f351202764d97550b1fda115e290dd8de3f205f62762ae155"
CAMPAIGN_BYTE_COUNT = 4_931_196
CAMPAIGN_SHA256 = "886392986af01580de4782ef58dea3792c67ea8783b56537f9a20addae208159"
PREREGISTRATION_ID = "336139087db95530d912e3a3b027d14eb0e8aa4cbfc350fd979245107cc9ac9e"
V100_CAMPAIGN_ID = "ce5886a86036c5f1163fcd98b5566c5dc5ca981405d433096944dc0d7c293a9a"
V100_VERIFICATION_ID = "b33000caade3751ee274527c15c4650d4b17bde05b9b1cf1316d9655923a3160"
SOURCE_LIBRARY_ARTIFACT_ID = "4f0a9592f7d6ba2d7683e9328f76dbd01bd18a3a47a062ea764f7a20012caeba"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_011_101),
    ("BALANCED_BATCH_REFINEMENT", 1_011_102),
    ("MAINTENANCE_CASCADE", 1_011_103),
    ("MAINTENANCE_CASCADE", 1_011_104),
)
TARGET_EPISODES = (101, 102, 103)
VERIFICATION_ID = "a367b1c2f73096b7436527767d0f72eec1d605221ceb31618364c86866747e13"
EXPECTED_CANONICAL_BYTE_COUNT = 2_124
EXPECTED_CANONICAL_SHA256 = "91a66c31e4989174e61c1d6771555e59a71692af5f445756308650e35e986ea4"


class ConstructionK7AbstractExecutionUtilizationIndependentVerifierV101Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractExecutionUtilizationIndependentVerifierV101Error(
        message
    )


def _check_content_id(
    document: Any, key: str, domain: str, id_function: Any
) -> None:
    if type(document) is not dict:
        _fail(f"V101 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != id_function(domain, payload):
        _fail(f"V101 {key} content identity changed")


def _shield_counts(sequence: Mapping[str, Any]) -> tuple[int, int]:
    first = sequence.get("first_agreement_shielded_online_episode")
    v99._check_generic_id(first, "episode_id", v99._FIRST_EPISODE_DOMAIN)
    accepts = 0
    disagreements = 0
    for wrapper in first.get("agreement_shield_receipts", []):
        accepted, disagreed = v99._check_shield(wrapper.get("shield"))
        accepts += accepted
        disagreements += disagreed
    if (
        first.get("agreement_shield_accept_count") != accepts
        or first.get("agreement_shield_disagreement_abstention_count")
        != disagreements
    ):
        _fail("V101 first shield counts changed")
    later_accepts = 0
    later_disagreements = 0
    for episode, index in zip(
        sequence.get("later_persistent_episodes", []),
        TARGET_EPISODES[1:],
        strict=True,
    ):
        wrapper_fields = {
            "new_certificate_labels_charged_this_episode",
            "paid_certificate_labels_cumulative",
            "persistent_exact_support_group_count",
        }
        payload = {
            key: value
            for key, value in episode.items()
            if key != "episode_id" and key not in wrapper_fields
        }
        if (
            episode.get("episode_id")
            != v99._generic_id(v99._PRELOADED_EPISODE_DOMAIN, payload)
            or episode.get("episode_index") != index
        ):
            _fail("V101 later episode identity or index changed")
        v99._check_pairing(episode)
        for receipt in episode.get("abstract_plan_receipts", []):
            accepted, disagreed = v99._check_shield(
                receipt.get("abstract_plan", {}).get("agreement_shield_receipt")
            )
            later_accepts += accepted
            later_disagreements += disagreed
    if (
        sequence.get("later_agreement_shield_accept_receipt_count")
        != later_accepts
        or sequence.get("later_agreement_shield_disagreement_abstention_count")
        != later_disagreements
    ):
        _fail("V101 later shield counts changed")
    return accepts + later_accepts, disagreements + later_disagreements


def _execution_utilization(
    sequence: Mapping[str, Any],
) -> tuple[dict[str, Any], int]:
    first = sequence["first_agreement_shielded_online_episode"]
    later = sequence["later_persistent_episodes"]
    first_matches = first["shielded_joint_execution_action_match_count"]
    later_values: list[bool] = []
    later_steps = 0
    for episode in later:
        values = episode.get("execution_action_matches_abstract_proposal")
        if (
            type(values) is not list
            or any(type(value) is not bool for value in values)
            or len(values) != episode.get("execution_steps")
            or sum(values)
            != episode.get("execution_action_matches_abstract_proposal_count")
        ):
            _fail("V101 per-execution abstract-match evidence changed")
        later_values.extend(values)
        later_steps += episode["execution_steps"]
    later_matches = sum(later_values)
    if (
        sequence.get("later_execution_action_matches_abstract_proposal_count")
        != later_matches
    ):
        _fail("V101 persistent execution-match total changed")
    first_steps = first["execution_steps"]
    matches = first_matches + later_matches
    steps = first_steps + later_steps
    document = {
        "schema": "acfqp.abstract_execution_utilization.v101",
        "first_episode_abstract_execution_match_count": first_matches,
        "later_episode_abstract_execution_match_count": later_matches,
        "persistent_sequence_abstract_execution_match_count": matches,
        "first_episode_execution_step_count": first_steps,
        "later_episode_execution_step_count": later_steps,
        "persistent_sequence_execution_step_count": steps,
        "abstract_execution_match_fraction_numerator": matches,
        "abstract_execution_match_fraction_denominator": steps,
        "strict_majority_of_executed_actions_match_abstract_proposal": (
            steps > 0 and 2 * matches > steps
        ),
        "match_requires_abstract_partial_exact_action_agreement": True,
        "abstract_proposal_used_only_for_action_ordering": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return document, later_matches


def _coverage(sequence: Mapping[str, Any]) -> dict[str, Any]:
    first = sequence["first_agreement_shielded_online_episode"]
    total_accept, total_disagreement = _shield_counts(sequence)
    first_accept = first["agreement_shield_accept_count"]
    first_disagreement = first["agreement_shield_disagreement_abstention_count"]
    later_accept = total_accept - first_accept
    later_disagreement = total_disagreement - first_disagreement
    return {
        "schema": "acfqp.sequence_wide_agreement_shield_path_coverage.v100",
        "first_episode_accept_count": first_accept,
        "first_episode_disagreement_abstention_count": first_disagreement,
        "later_episode_accept_count": later_accept,
        "later_episode_disagreement_abstention_count": later_disagreement,
        "persistent_sequence_accept_count": total_accept,
        "persistent_sequence_disagreement_abstention_count": total_disagreement,
        "accept_path_observed_somewhere_in_persistent_sequence": total_accept > 0,
        "disagreement_path_observed_somewhere_in_persistent_sequence": (
            total_disagreement > 0
        ),
        "both_paths_observed_somewhere_in_persistent_sequence": (
            total_accept > 0 and total_disagreement > 0
        ),
        "both_paths_required_in_first_episode": False,
        "path_coverage_window_fixed_before_v100_outcomes": True,
    }


def _verify_campaign_document(document: Any) -> dict[str, Any]:
    _check_content_id(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_ABSTRACT_EXECUTION_UTILIZATION_CAMPAIGN_V101_DOMAIN,
        domains.extension_content_id_v101,
    )
    occurrences = document.get("target_occurrences")
    if (
        document.get("schema")
        != "acfqp.abstract_execution_utilization_campaign.v101"
        or document.get("campaign_id") != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v100_campaign_id") != V100_CAMPAIGN_ID
        or document.get("v100_verification_id") != V100_VERIFICATION_ID
        or document.get("source_library_artifact_id") != SOURCE_LIBRARY_ARTIFACT_ID
        or type(occurrences) is not list
        or [(row.get("target_family"), row.get("seed")) for row in occurrences]
        != list(TARGETS)
    ):
        _fail("V101 campaign identity inventory changed")
    totals = {
        "meta_activation": 0,
        "no_prior_activation": 0,
        "meta_labels": 0,
        "no_prior_labels": 0,
        "direct_labels": 0,
        "meta_abstract_execution_match_count": 0,
        "meta_execution_step_count": 0,
    }
    passed_count = 0
    failed = []
    lower_bound_rows = []
    for occurrence, (family, seed) in zip(occurrences, TARGETS, strict=True):
        _check_content_id(
            occurrence,
            "occurrence_id",
            domains.CONSTRUCTION_K7_ABSTRACT_EXECUTION_UTILIZATION_OCCURRENCE_V101_DOMAIN,
            domains.extension_content_id_v101,
        )
        predecessor = occurrence.get("frozen_v100_sequence_wide_observation")
        _check_content_id(
            predecessor,
            "occurrence_id",
            domains_v100.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_OCCURRENCE_V100_DOMAIN,
            domains_v100.extension_content_id_v100,
        )
        observation = predecessor.get("frozen_v99_algorithm_observation")
        v99._check_v99_id(
            observation,
            "occurrence_id",
            v99.domains.CONSTRUCTION_K7_AGREEMENT_SHIELDED_OCCURRENCE_V99_DOMAIN,
        )
        if (
            occurrence.get("target_family") != family
            or occurrence.get("seed") != seed
            or occurrence.get("episode_indices") != list(TARGET_EPISODES)
            or predecessor.get("target_family") != family
            or predecessor.get("seed") != seed
            or observation.get("target_family") != family
            or observation.get("seed") != seed
        ):
            _fail("V101 occurrence identity join changed")
        meta_sequence = observation["meta_prior_persistent_sequence"]
        no_sequence = observation["no_structure_prior_persistent_sequence"]
        if (
            meta_sequence.get("episode_indices") != list(TARGET_EPISODES)
            or no_sequence.get("episode_indices") != list(TARGET_EPISODES)
            or meta_sequence.get("every_new_ground_query_followed_a_failed_certificate")
            is not True
            or no_sequence.get("every_new_ground_query_followed_a_failed_certificate")
            is not True
            or meta_sequence.get("persistent_exact_overlay_exclusively_discharges_safety")
            is not True
            or no_sequence.get("persistent_exact_overlay_exclusively_discharges_safety")
            is not True
        ):
            _fail("V101 query discipline or safety boundary changed")
        meta_utilization, later_lower_bound = _execution_utilization(meta_sequence)
        no_utilization, _ = _execution_utilization(no_sequence)
        coverage = _coverage(meta_sequence)
        if (
            occurrence.get("meta_prior_abstract_execution_utilization")
            != meta_utilization
            or occurrence.get("no_prior_abstract_execution_utilization")
            != no_utilization
            or predecessor.get("sequence_wide_path_coverage") != coverage
        ):
            _fail("V101 utilization or path coverage changed")
        old_gate = predecessor["registered_gate"]
        expected_gate = {
            "sequence_wide_v100_predecessor_gate_passed": old_gate["passed"],
            "meta_abstract_ordering_matches_strict_majority_of_executed_actions": meta_utilization[
                "strict_majority_of_executed_actions_match_abstract_proposal"
            ],
            "meta_abstract_execution_match_rate_noninferior_to_no_prior": (
                meta_utilization["abstract_execution_match_fraction_numerator"]
                * no_utilization["abstract_execution_match_fraction_denominator"]
                >= no_utilization["abstract_execution_match_fraction_numerator"]
                * meta_utilization["abstract_execution_match_fraction_denominator"]
            ),
            "certificate_failure_only_query_discipline_clean": True,
            "exact_overlay_exclusively_discharges_safety": True,
        }
        expected_gate["passed"] = all(expected_gate.values())
        if (
            occurrence.get("registered_gate") != expected_gate
            or occurrence.get("algorithm_changed_from_v100") is not False
            or occurrence.get("complete_world_model_synthesized") is not False
            or occurrence.get("official_execution_allowed") is not False
        ):
            _fail("V101 occurrence Gate or claim boundary changed")
        accounting = observation["accounting"]
        totals["meta_activation"] += accounting[
            "meta_model_activation_target_labels_with_right_censoring"
        ]
        totals["no_prior_activation"] += accounting[
            "no_prior_model_activation_target_labels_with_right_censoring"
        ]
        totals["meta_labels"] += accounting["meta_lifetime_target_labels"]
        totals["no_prior_labels"] += accounting["no_prior_lifetime_target_labels"]
        totals["direct_labels"] += accounting[
            "strict_cold_direct_lifetime_target_labels"
        ]
        totals["meta_abstract_execution_match_count"] += meta_utilization[
            "persistent_sequence_abstract_execution_match_count"
        ]
        totals["meta_execution_step_count"] += meta_utilization[
            "persistent_sequence_execution_step_count"
        ]
        passed_count += expected_gate["passed"]
        if not expected_gate["passed"]:
            failed.append(
                {
                    "target_family": family,
                    "seed": seed,
                    "persistent_sequence_accept_count": coverage[
                        "persistent_sequence_accept_count"
                    ],
                    "persistent_sequence_disagreement_abstention_count": coverage[
                        "persistent_sequence_disagreement_abstention_count"
                    ],
                }
            )
        steps = meta_utilization["persistent_sequence_execution_step_count"]
        if 2 * later_lower_bound <= steps:
            _fail("V101 independently replayable utilization lower bound is not a majority")
        lower_bound_rows.append(
            {
                "target_family": family,
                "seed": seed,
                "later_episode_independently_replayed_match_count": later_lower_bound,
                "total_sequence_execution_step_count": steps,
            }
        )
    expected_totals = {
        "meta_activation": 170,
        "no_prior_activation": 198,
        "meta_labels": 348,
        "no_prior_labels": 348,
        "direct_labels": 606,
        "meta_abstract_execution_match_count": 50,
        "meta_execution_step_count": 74,
    }
    expected_accounting = {
        **expected_totals,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = document.get("registered_gate")
    if (
        totals != expected_totals
        or document.get("accounting") != expected_accounting
        or passed_count != 3
        or failed
        != [
            {
                "target_family": "BALANCED_BATCH_REFINEMENT",
                "seed": 1_011_102,
                "persistent_sequence_accept_count": 78,
                "persistent_sequence_disagreement_abstention_count": 0,
            }
        ]
        or gate.get("passed") is not False
        or gate.get("passed_target_occurrence_count") != 3
        or gate.get(
            "every_occurrence_abstract_orders_strict_majority_of_executed_actions"
        )
        is not True
        or gate.get(
            "aggregate_abstract_ordering_matches_strict_majority_of_executed_actions"
        )
        is not True
        or gate.get("aggregate_model_activation_sample_tax_strictly_reduced")
        is not True
        or gate.get("aggregate_negative_transfer_absent") is not True
        or document.get(
            "registered_multistep_execution_primarily_abstract_ordered_verified"
        )
        is not False
        or document.get("complete_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V101 registered failure or aggregate evidence changed")
    return {
        "schema": "acfqp.abstract_execution_utilization_verification.v101",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V101_SEQUENCE_PATH_COVERAGE_FAILURE_VERIFIED",
        "verified_aggregate_evidence": {
            **totals,
            "activation_label_reduction": 28,
            "abstract_execution_match_fraction_numerator": 50,
            "abstract_execution_match_fraction_denominator": 74,
            "negative_transfer_label_delta": 0,
            "failed_occurrence": failed[0],
            "producer_free_later_episode_match_lower_bound_rows": lower_bound_rows,
            "all_axes_separate": True,
        },
        "producer_free_later_episode_execution_match_lower_bound_is_majority_for_every_occurrence": True,
        "first_episode_summary_not_needed_for_positive_majority_lower_bound": True,
        "ground_distinctions_only_after_certificate_failure_verified": True,
        "v101_registered_gate_passed": False,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def verify_abstract_execution_utilization_campaign_bytes_v101(
    raw: bytes,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V101 campaign bytes differ from the frozen failure")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V101 campaign bytes are not canonical")
    return _verify_campaign_document(document)


def freeze_abstract_execution_utilization_verification_v101(raw: bytes) -> bytes:
    payload = verify_abstract_execution_utilization_campaign_bytes_v101(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v101(
            domains.CONSTRUCTION_K7_ABSTRACT_EXECUTION_UTILIZATION_VERIFICATION_V101_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V101 frozen verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_abstract_execution_utilization_verification_v101",
    "verify_abstract_execution_utilization_campaign_bytes_v101",
)
