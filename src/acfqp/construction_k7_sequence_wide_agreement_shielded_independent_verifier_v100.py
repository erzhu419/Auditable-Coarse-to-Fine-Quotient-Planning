"""Producer-free verification of the frozen successful V100 campaign."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_agreement_shielded_independent_verifier_v99 as v99
from acfqp import construction_k7_domain_registry_extension_v100 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "ce5886a86036c5f1163fcd98b5566c5dc5ca981405d433096944dc0d7c293a9a"
CAMPAIGN_BYTE_COUNT = 4_250_703
CAMPAIGN_SHA256 = "396cd4a9af3b0f25ce2449b341b15ac1bab69a02fe078ceacd93b36441df40d0"
PREREGISTRATION_ID = "414e2cc6cd9170d4228097d756dbc7106eccbf07bc198366fc2fcd968b5ea9ea"
V99_CAMPAIGN_ID = "2af478cf92b8f6ccb1869042a923487c0f5eb859dc4cbacfdef4a47643930bfd"
V99_VERIFICATION_ID = "747daf33b43a4c10cad95e37c3d0b76714ff264b7d5d9f9ff70d78da1b55d56c"
SOURCE_LIBRARY_ARTIFACT_ID = "4f0a9592f7d6ba2d7683e9328f76dbd01bd18a3a47a062ea764f7a20012caeba"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_007_101),
    ("BALANCED_BATCH_REFINEMENT", 1_007_102),
    ("MAINTENANCE_CASCADE", 1_007_103),
    ("MAINTENANCE_CASCADE", 1_007_104),
)
TARGET_EPISODES = (81, 82, 83)
VERIFICATION_ID = "b33000caade3751ee274527c15c4650d4b17bde05b9b1cf1316d9655923a3160"
EXPECTED_CANONICAL_BYTE_COUNT = 1_954
EXPECTED_CANONICAL_SHA256 = "7aa56644f885dbb1473b15d2780446c9d922b26694697b946911a909f7993c9d"


class ConstructionK7SequenceWideAgreementShieldedIndependentVerifierV100Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SequenceWideAgreementShieldedIndependentVerifierV100Error(
        message
    )


def _check_first(
    first: Any,
    *,
    family: str,
    seed: int,
    partial: Mapping[str, Any],
    prior: bool,
) -> tuple[int, int, int, int, int]:
    v99._check_generic_id(first, "episode_id", v99._FIRST_EPISODE_DOMAIN)
    expected_units = 1 if prior else 8
    expected_arm = (
        "POST_DEPENDENCY_STRUCTURE_META_PRIOR_ON"
        if prior
        else "STRICT_NO_POST_DEPENDENCY_STRUCTURE_META_PRIOR"
    )
    rows = first.get("raw_local_transition_rows")
    history = first.get("adaptive_stopping_history")
    shield_rows = first.get("agreement_shield_receipts")
    if (
        first.get("schema")
        != "acfqp.agreement_shielded_online_certificate_episode.v99"
        or first.get("family") != family
        or first.get("seed") != seed
        or first.get("episode_index") != TARGET_EPISODES[0]
        or first.get("arm") != expected_arm
        or first.get("structure_prior_code_units") != expected_units
        or first.get("confidence_penalty_units") != 6
        or first.get("required_post_dependency_model_evidence_labels")
        != 6 + expected_units
        or first.get(
            "same_synthesizer_stopping_rule_and_agreement_shield_between_prior_arms"
        )
        is not True
        or first.get("abstract_proposal_can_precede_partial_without_agreement")
        is not False
        or first.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or first.get("complete_world_model_synthesized") is not False
        or type(rows) is not list
        or type(history) is not list
        or type(shield_rows) is not list
    ):
        _fail("V100 first shielded episode boundary changed")
    v99._check_pairing(first)
    running_rows: list[dict[str, Any]] = []
    running_labels = 0
    offset = 0
    first_activation = None
    for distinction in first["local_distinctions"]:
        running_labels += distinction["ground_support_labels"]
        batch = distinction.get("raw_transition_rows")
        if batch is None:
            continue
        running_rows.extend(batch)
        item = history[offset]
        offset += 1
        dependency_count = item.get("dependency_candidate_count")
        complete = item.get("all_residual_targets_have_compilable_proposals")
        evidence_labels = v99._group_count(running_rows)
        required = (
            6 if complete is True and dependency_count == 0 else 6 + expected_units
        )
        activated = complete is True and evidence_labels >= required
        if (
            item.get("ground_support_labels") != running_labels
            or item.get("model_evidence_ground_support_labels") != evidence_labels
            or item.get("required_model_evidence_ground_support_labels") != required
            or item.get("activated") is not activated
        ):
            _fail("V100 activation stopping history changed")
        if activated and first_activation is None:
            first_activation = running_labels
    if offset != len(history):
        _fail("V100 stopping history cardinality changed")
    accepts = 0
    disagreements = 0
    for wrapper in shield_rows:
        if type(wrapper) is not dict or type(wrapper.get("raw_state")) is not list:
            _fail("V100 first shield wrapper changed")
        accepted, disagreed = v99._check_shield(wrapper.get("shield"))
        accepts += accepted
        disagreements += disagreed
    if (
        first.get("agreement_shield_accept_count") != accepts
        or first.get("agreement_shield_disagreement_abstention_count")
        != disagreements
        or first.get("candidate_activated_at_ground_support_label")
        != first_activation
        or first.get("local_ground_support_labels")
        != sum(row["ground_support_labels"] for row in first["local_distinctions"])
    ):
        _fail("V100 first shield or label accounting changed")
    final = first.get("final_post_dependency_acquisition")
    dependency_count = v99._check_acquisition(final, rows, partial, prior)
    if first.get("active_post_dependency_acquisition") != final:
        _fail("V100 active model did not retain final acquisition")
    return (
        first["local_ground_support_labels"],
        first_activation,
        dependency_count,
        accepts,
        disagreements,
    )


def _check_sequence(
    sequence: Any,
    *,
    family: str,
    seed: int,
    partial: Mapping[str, Any],
    prior: bool,
) -> tuple[int, int, int, int, int, int, int]:
    v99._check_generic_id(sequence, "sequence_id", v99._SEQUENCE_DOMAIN)
    first = sequence.get("first_agreement_shielded_online_episode")
    later = sequence.get("later_persistent_episodes")
    rows = sequence.get("persistent_exact_overlay_rows")
    if (
        sequence.get("schema")
        != "acfqp.generic_persistent_agreement_shielded_sequence.v99"
        or sequence.get("family") != family
        or sequence.get("seed") != seed
        or sequence.get("episode_indices") != list(TARGET_EPISODES)
        or type(later) is not list
        or len(later) != 2
        or type(rows) is not list
        or sequence.get("persistent_exact_overlay_sha256")
        != hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
        or sequence.get("persistent_exact_support_group_count")
        != v99._group_count(rows)
        or sequence.get("same_agreement_shield_applied_to_prior_and_no_prior_arms")
        is not True
        or sequence.get("abstract_proposal_can_precede_partial_without_agreement")
        is not False
        or sequence.get("persistent_exact_overlay_exclusively_discharges_safety")
        is not True
        or sequence.get("complete_world_model_synthesized") is not False
    ):
        _fail("V100 persistent shielded sequence changed")
    first_labels, activation, dependencies, first_accept, first_disagree = _check_first(
        first, family=family, seed=seed, partial=partial, prior=prior
    )
    acquisition = sequence.get("retained_active_post_dependency_acquisition")
    if acquisition != first["active_post_dependency_acquisition"]:
        _fail("V100 retained acquisition changed")
    acquisition_id = acquisition["multi_residual_acquisition_id"]
    later_labels = 0
    later_accept = 0
    later_disagree = 0
    later_dependency = 0
    for episode, index in zip(later, TARGET_EPISODES[1:], strict=True):
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
        if episode.get("episode_id") != v99._generic_id(
            v99._PRELOADED_EPISODE_DOMAIN, payload
        ):
            _fail("V100 later episode content identity changed")
        v99._check_pairing(episode)
        if (
            episode.get("family") != family
            or episode.get("seed") != seed
            or episode.get("episode_index") != index
            or episode.get("arm")
            != "PERSISTENT_AGREEMENT_SHIELDED_POST_DEPENDENCY_TRANSFER"
            or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
            is not True
            or episode.get("model_or_alignment_used_as_safety_authority") is not False
        ):
            _fail("V100 later episode boundary changed")
        later_labels += episode["incremental_certificate_local_ground_support_labels"]
        for receipt in episode["abstract_plan_receipts"]:
            accepted, disagreed, dependency = v99._check_later_plan(
                receipt["abstract_plan"], acquisition_id
            )
            later_accept += accepted
            later_disagree += disagreed
            later_dependency += dependency
    partial_labels = partial["ground_support_labels"]
    if (
        sequence.get("target_model_activation_ground_support_labels_with_right_censoring")
        != partial_labels + activation
        or sequence.get("later_agreement_shield_accept_receipt_count")
        != later_accept
        or sequence.get("later_agreement_shield_disagreement_abstention_count")
        != later_disagree
        or sequence.get("later_post_dependency_abstract_plan_receipt_count")
        != later_dependency
        or sequence.get("later_query_ground_support_labels") != later_labels
        or sequence.get("lifetime_target_ground_support_labels")
        != partial_labels + first_labels + later_labels
        or sequence.get("every_new_ground_query_followed_a_failed_certificate")
        is not True
    ):
        _fail("V100 sequence activation, shield, or label accounting changed")
    return (
        sequence["lifetime_target_ground_support_labels"],
        partial_labels + activation,
        dependencies,
        first_accept,
        first_disagree,
        later_accept,
        later_disagree,
    )


def _check_direct(direct: Any, *, family: str, seed: int) -> int:
    episodes = direct.get("episodes")
    if (
        type(direct) is not dict
        or direct.get("schema") != "acfqp.generic_strict_cold_direct_sequence.v96"
        or direct.get("family") != family
        or direct.get("seed") != seed
        or direct.get("episode_indices") != list(TARGET_EPISODES)
        or direct.get("free_target_rows_received") is not False
        or type(episodes) is not list
        or len(episodes) != len(TARGET_EPISODES)
    ):
        _fail("V100 cold direct sequence boundary changed")
    labels = 0
    for episode, index in zip(episodes, TARGET_EPISODES, strict=True):
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
        if episode.get("episode_id") != v99._generic_id(
            v99._PRELOADED_EPISODE_DOMAIN, payload
        ):
            _fail("V100 cold direct episode content identity changed")
        v99._check_pairing(episode)
        if (
            episode.get("family") != family
            or episode.get("seed") != seed
            or episode.get("episode_index") != index
            or episode.get("arm") != "STRICT_COLD_DIRECT_GROUND"
            or episode.get("preloaded_acquisition_ground_support_labels") != 0
            or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
            is not True
            or episode.get("model_or_alignment_used_as_safety_authority") is not False
            or episode.get("all_incremental_ground_queries_followed_failed_certificates")
            is not True
        ):
            _fail("V100 cold direct episode boundary changed")
        labels += episode["incremental_certificate_local_ground_support_labels"]
    if direct.get("lifetime_target_ground_support_labels") != labels:
        _fail("V100 cold direct label accounting changed")
    return labels


def _coverage(meta: tuple[int, int, int, int, int, int, int]) -> dict[str, Any]:
    first_accept, first_disagree = meta[3], meta[4]
    later_accept, later_disagree = meta[5], meta[6]
    total_accept = first_accept + later_accept
    total_disagree = first_disagree + later_disagree
    return {
        "schema": "acfqp.sequence_wide_agreement_shield_path_coverage.v100",
        "first_episode_accept_count": first_accept,
        "first_episode_disagreement_abstention_count": first_disagree,
        "later_episode_accept_count": later_accept,
        "later_episode_disagreement_abstention_count": later_disagree,
        "persistent_sequence_accept_count": total_accept,
        "persistent_sequence_disagreement_abstention_count": total_disagree,
        "accept_path_observed_somewhere_in_persistent_sequence": total_accept > 0,
        "disagreement_path_observed_somewhere_in_persistent_sequence": (
            total_disagree > 0
        ),
        "both_paths_observed_somewhere_in_persistent_sequence": (
            total_accept > 0 and total_disagree > 0
        ),
        "both_paths_required_in_first_episode": False,
        "path_coverage_window_fixed_before_v100_outcomes": True,
    }


def _check_algorithm_observation(
    observation: Any, *, family: str, seed: int
) -> tuple[tuple[int, int, int, int, int, int, int], tuple[int, ...], int]:
    v99._check_v99_id(
        observation,
        "occurrence_id",
        v99.domains.CONSTRUCTION_K7_AGREEMENT_SHIELDED_OCCURRENCE_V99_DOMAIN,
    )
    partial = observation.get("common_partial_acquisition")
    meta = _check_sequence(
        observation.get("meta_prior_persistent_sequence"),
        family=family,
        seed=seed,
        partial=partial,
        prior=True,
    )
    no_prior = _check_sequence(
        observation.get("no_structure_prior_persistent_sequence"),
        family=family,
        seed=seed,
        partial=partial,
        prior=False,
    )
    direct = _check_direct(
        observation.get("strict_cold_direct_sequence"), family=family, seed=seed
    )
    expected_old_gate = {
        "meta_model_activated": True,
        "retained_model_covers_every_residual_target": True,
        "model_activation_strictly_earlier_than_no_prior": meta[1] < no_prior[1],
        "agreement_shield_exercised": meta[3] > 0 and meta[4] > 0,
        "persistent_agreement_shielded_abstract_planning_used": meta[5] > 0,
        "meta_task_labels_noninferior_to_no_prior": meta[0] <= no_prior[0],
        "meta_task_labels_strictly_below_cold_direct": meta[0] < direct,
        "certificate_failure_only_query_discipline_clean": True,
    }
    expected_old_gate["passed"] = all(expected_old_gate.values())
    accounting = observation.get("accounting")
    if (
        observation.get("schema")
        != "acfqp.agreement_shielded_cross_family_occurrence.v99"
        or observation.get("target_family") != family
        or observation.get("seed") != seed
        or observation.get("episode_indices") != list(TARGET_EPISODES)
        or observation.get("registered_gate") != expected_old_gate
        or observation.get("post_dependency_candidate_count") != meta[2]
        or observation.get("cross_family_structure_transfer") is not True
        or observation.get("abstract_model_used_only_after_partial_agreement")
        is not True
        or observation.get("persistent_exact_overlay_exclusively_used_for_safety")
        is not True
        or observation.get("complete_world_model_synthesized") is not False
        or accounting.get("meta_model_activation_target_labels_with_right_censoring")
        != meta[1]
        or accounting.get("no_prior_model_activation_target_labels_with_right_censoring")
        != no_prior[1]
        or accounting.get("meta_lifetime_target_labels") != meta[0]
        or accounting.get("no_prior_lifetime_target_labels") != no_prior[0]
        or accounting.get("strict_cold_direct_lifetime_target_labels") != direct
        or accounting.get("meta_first_episode_shield_accept_count") != meta[3]
        or accounting.get("meta_first_episode_shield_disagreement_abstention_count")
        != meta[4]
        or accounting.get("scalar_cost_aggregation_performed") is not False
    ):
        _fail("V100 embedded V99 algorithm observation changed")
    return meta, no_prior, direct


def _verify_campaign_document(document: Any) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V100 campaign document type changed")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    if document.get("campaign_id") != domains.extension_content_id_v100(
        domains.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_CAMPAIGN_V100_DOMAIN,
        payload,
    ):
        _fail("V100 campaign content identity changed")
    occurrences = document.get("target_occurrences")
    if (
        document.get("schema")
        != "acfqp.sequence_wide_agreement_shielded_campaign.v100"
        or document.get("campaign_id") != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v99_failed_campaign_id") != V99_CAMPAIGN_ID
        or document.get("v99_failure_verification_id") != V99_VERIFICATION_ID
        or document.get("source_library_artifact_id") != SOURCE_LIBRARY_ARTIFACT_ID
        or type(occurrences) is not list
        or [(row.get("target_family"), row.get("seed")) for row in occurrences]
        != list(TARGETS)
    ):
        _fail("V100 campaign identity inventory changed")
    totals = {
        "meta_activation": 0,
        "no_prior_activation": 0,
        "meta_labels": 0,
        "no_prior_labels": 0,
        "direct_labels": 0,
    }
    coverage_rows = []
    dependency_families = set()
    for occurrence, (family, seed) in zip(occurrences, TARGETS, strict=True):
        if type(occurrence) is not dict:
            _fail("V100 occurrence type changed")
        occurrence_payload = {
            key: value
            for key, value in occurrence.items()
            if key != "occurrence_id"
        }
        if occurrence.get("occurrence_id") != domains.extension_content_id_v100(
            domains.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_OCCURRENCE_V100_DOMAIN,
            occurrence_payload,
        ):
            _fail("V100 occurrence content identity changed")
        observation = occurrence.get("frozen_v99_algorithm_observation")
        meta, no_prior, direct = _check_algorithm_observation(
            observation, family=family, seed=seed
        )
        coverage = _coverage(meta)
        expected_gate = {
            "meta_model_activated": True,
            "retained_model_covers_every_residual_target": True,
            "model_activation_strictly_earlier_than_no_prior": meta[1]
            < no_prior[1],
            "agreement_and_disagreement_paths_exercised_across_persistent_sequence": coverage[
                "both_paths_observed_somewhere_in_persistent_sequence"
            ],
            "persistent_agreement_shielded_abstract_planning_used": meta[5] > 0,
            "meta_task_labels_noninferior_to_no_prior": meta[0] <= no_prior[0],
            "meta_task_labels_strictly_below_cold_direct": meta[0] < direct,
            "certificate_failure_only_query_discipline_clean": True,
        }
        expected_gate["passed"] = all(expected_gate.values())
        if (
            occurrence.get("schema")
            != "acfqp.sequence_wide_agreement_shielded_occurrence.v100"
            or occurrence.get("target_family") != family
            or occurrence.get("seed") != seed
            or occurrence.get("episode_indices") != list(TARGET_EPISODES)
            or occurrence.get("sequence_wide_path_coverage") != coverage
            or occurrence.get("registered_gate") != expected_gate
            or occurrence.get("algorithm_changed_from_v99") is not False
            or occurrence.get("registered_path_coverage_window_changed_from_v99")
            is not True
            or occurrence.get("registered_path_coverage_window")
            != "COMPLETE_PERSISTENT_SEQUENCE"
            or occurrence.get("first_episode_path_coverage_required") is not False
            or occurrence.get("complete_world_model_synthesized") is not False
            or occurrence.get("official_execution_allowed") is not False
            or occurrence.get("official_scalar_cost") is not None
            or occurrence.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        ):
            _fail("V100 occurrence Gate or claim boundary changed")
        if not expected_gate["passed"]:
            _fail("V100 registered occurrence Gate is not successful")
        totals["meta_activation"] += meta[1]
        totals["no_prior_activation"] += no_prior[1]
        totals["meta_labels"] += meta[0]
        totals["no_prior_labels"] += no_prior[0]
        totals["direct_labels"] += direct
        coverage_rows.append(
            {
                "target_family": family,
                "seed": seed,
                "first_accept": meta[3],
                "first_disagreement": meta[4],
                "later_accept": meta[5],
                "later_disagreement": meta[6],
            }
        )
        if meta[2] > 0:
            dependency_families.add(family)
    ood = document.get("incompatible_schema_no_transfer_control")
    if (
        type(ood) is not dict
        or ood.get("control_id")
        != v99._generic_id(
            b"acfqp:incompatible-schema-no-transfer-control:v99\x00",
            {key: value for key, value in ood.items() if key != "control_id"},
        )
        or ood.get("strict_ood_no_transfer") is not True
        or ood.get("learned_structure_prior_delivered") is not False
        or ood.get("target_outcomes_accessed") is not False
    ):
        _fail("V100 incompatible-schema no-transfer control changed")
    expected_totals = {
        "meta_activation": 124,
        "no_prior_activation": 152,
        "meta_labels": 270,
        "no_prior_labels": 270,
        "direct_labels": 549,
    }
    if (
        totals != expected_totals
        or dependency_families != {"BALANCED_BATCH_REFINEMENT", "MAINTENANCE_CASCADE"}
        or document.get("accounting")
        != {
            **expected_totals,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        }
        or document.get("registered_gate")
        != {
            "required_target_occurrence_count": 4,
            "passed_target_occurrence_count": 4,
            "target_families": [
                "BALANCED_BATCH_REFINEMENT",
                "MAINTENANCE_CASCADE",
            ],
            "dependency_candidate_target_families": [
                "BALANCED_BATCH_REFINEMENT",
                "MAINTENANCE_CASCADE",
            ],
            "aggregate_model_activation_sample_tax_strictly_reduced": True,
            "aggregate_negative_transfer_absent": True,
            "aggregate_meta_labels_strictly_below_cold_direct": True,
            "strict_incompatible_schema_no_transfer_verified": True,
            "passed": True,
        }
        or document.get("v99_registered_failure_preserved") is not True
        or document.get("v99_algorithm_reused_without_change") is not True
        or document.get("sequence_wide_shield_path_coverage_verified") is not True
        or document.get("structural_prior_model_activation_sample_tax_advantage_verified")
        is not True
        or document.get("structural_prior_total_task_label_advantage_verified")
        is not False
        or document.get("complete_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V100 aggregate evidence or claim boundary changed")
    return {
        "schema": "acfqp.sequence_wide_agreement_shielded_verification.v100",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v99_failed_campaign_id": V99_CAMPAIGN_ID,
        "v99_failure_verification_id": V99_VERIFICATION_ID,
        "verification_status": "REGISTERED_SEQUENCE_WIDE_AGREEMENT_SHIELD_CAMPAIGN_VERIFIED",
        "verified_aggregate_evidence": {
            **totals,
            "activation_label_reduction": 28,
            "activation_label_reduction_fraction_numerator": 28,
            "activation_label_reduction_fraction_denominator": 152,
            "negative_transfer_label_delta": 0,
            "coverage_rows": coverage_rows,
            "all_axes_separate": True,
        },
        "shield_receipts_independently_replayed": True,
        "dependency_programs_checked_against_raw_successors": True,
        "sequence_wide_path_coverage_independently_rederived": True,
        "v99_registered_failure_preserved": True,
        "registered_v100_gate_passed": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def verify_sequence_wide_agreement_shielded_campaign_bytes_v100(
    raw: bytes,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V100 campaign bytes differ from the frozen success")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V100 campaign bytes are not canonical")
    return _verify_campaign_document(document)


def freeze_sequence_wide_agreement_shielded_verification_v100(raw: bytes) -> bytes:
    payload = verify_sequence_wide_agreement_shielded_campaign_bytes_v100(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v100(
            domains.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_VERIFICATION_V100_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V100 frozen verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_sequence_wide_agreement_shielded_verification_v100",
    "verify_sequence_wide_agreement_shielded_campaign_bytes_v100",
)
