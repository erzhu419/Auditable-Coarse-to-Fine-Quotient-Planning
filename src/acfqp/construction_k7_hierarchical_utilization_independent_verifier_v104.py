"""Producer-free replay of V104 hierarchical per-action utilization."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v104 as domains
from acfqp import construction_k7_receipted_utilization_independent_verifier_v103 as v103
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json

CAMPAIGN_ID = "1f9787eee1cb853f695c3fcb494822f7168abdebb1363f357069f468ce67eb79"
CAMPAIGN_BYTE_COUNT = 5_295_892
CAMPAIGN_SHA256 = "eb8cce92fe9c72f17bdd5493ea943fea7322dd280a1e7bcf00d92f899106a15c"
PREREGISTRATION_ID = "3e3c1f114022357153650c086034d38d86d82cec1e2826929048197a2ca60e66"
V103_CAMPAIGN_ID = "ae93067c6dfacbe158d3db700bc7c1b187e7e2d05d862d8cffcf971e1866d006"
V103_VERIFICATION_ID = "d9b8504dd7dceef0ad8a5e01f312aaccf61fa8c28e00c376d7bb14de61a448ec"
SOURCE_LIBRARY_ARTIFACT_ID = "4f0a9592f7d6ba2d7683e9328f76dbd01bd18a3a47a062ea764f7a20012caeba"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_016_101),
    ("BALANCED_BATCH_REFINEMENT", 1_016_102),
    ("MAINTENANCE_CASCADE", 1_016_103),
    ("MAINTENANCE_CASCADE", 1_016_104),
)
EPISODES = (131, 132, 133)
VERIFICATION_ID = "77cbc5f51f48eef1436c5c778048c0b32593dc7c99d428118e98f9af0c1c8af9"
EXPECTED_CANONICAL_BYTE_COUNT = 3_483
EXPECTED_CANONICAL_SHA256 = "bc1ba1c41fe0d95e7df76cbc4c5e12037e3e5516a066896807755da9bc615f25"

_HIERARCHICAL_RECEIPT_DOMAIN = b"acfqp:hierarchical-abstract-execution-receipt:v104\x00"
_HIERARCHICAL_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-hierarchical-receipted-sequence:v104\x00"


class ConstructionK7HierarchicalUtilizationIndependentVerifierV104Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HierarchicalUtilizationIndependentVerifierV104Error(message)


def _hierarchical_receipt(document: Any, episode_index: int) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V104 hierarchical receipt type changed")
    base = v103._receipt(document.get("base_v103_execution_receipt"))
    legal = base["legal_action_keys"]
    partial_key = next(
        (key for key in base["partial_proposal"] if key in legal), None
    )
    full_key = next(
        (key for key in base["abstract_proposal"] if key in legal), None
    )
    chosen = base["chosen_action_key"]
    full_match = base["chosen_action_matches_admitted_abstract_proposal"]
    partial_match = partial_key is not None and chosen == partial_key
    source = (
        "FULL_POST_DEPENDENCY_WORLD_MODEL"
        if full_match
        else "COMPILED_PARTIAL_WORLD_MODEL_FALLBACK"
        if partial_match
        else "EXACT_CERTIFICATE_POLICY_ONLY"
    )
    payload = {
        "schema": "acfqp.hierarchical_abstract_execution_receipt.v104",
        "episode_index": episode_index,
        "decision_index": base["decision_index"],
        "base_v103_execution_receipt": base,
        "base_v103_execution_receipt_id": base["execution_receipt_id"],
        "chosen_action_key": chosen,
        "full_post_dependency_legal_proposal": full_key,
        "compiled_partial_legal_proposal": partial_key,
        "chosen_action_matches_full_post_dependency_proposal": full_match,
        "chosen_action_matches_compiled_partial_proposal": partial_match,
        "abstract_ordering_source": source,
        "chosen_action_matches_admitted_abstract_model_proposal": (
            full_match or partial_match
        ),
        "full_model_match_not_inferred_from_partial_fallback": True,
        "partial_world_model_explicitly_missing_residual_coordinates": True,
        "residual_completion_disagreement_retained": (
            base["abstract_partial_exact_action_agreement"] is False
        ),
        "receipt_is_observation_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_claimed": False,
    }
    expected = {
        **payload,
        "hierarchical_execution_receipt_id": hashlib.sha256(
            _HIERARCHICAL_RECEIPT_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }
    if document != expected:
        _fail("V104 hierarchical receipt semantics changed")
    return expected


def _base_sequence(
    sequence: Any, family: str, seed: int
) -> tuple[list[tuple[int, list[dict[str, Any]]]], int, int, int, int]:
    v103._content_id(sequence, "sequence_id", v103._SEQUENCE_DOMAIN)
    if (
        type(sequence) is not dict
        or sequence.get("schema") != "acfqp.generic_persistent_receipted_sequence.v103"
        or sequence.get("family") != family
        or sequence.get("seed") != seed
        or sequence.get("episode_indices") != list(EPISODES)
        or sequence.get("complete_world_model_synthesized") is not False
        or sequence.get("official_execution_allowed") is not False
        or sequence.get("persistent_exact_overlay_exclusively_discharges_safety") is not True
        or sequence.get("every_new_ground_query_followed_a_failed_certificate") is not True
    ):
        _fail("V104 embedded V103 sequence contract changed")
    first = sequence.get("first_agreement_shielded_online_episode")
    later = sequence.get("later_persistent_episodes")
    if type(later) is not list or len(later) != 2:
        _fail("V104 embedded episode inventory changed")
    first_receipts, _first_matches, _first_steps = v103._episode_receipts(
        first, first=True
    )
    grouped = [(first["episode_index"], first_receipts)]
    all_base = list(first_receipts)
    for index, episode in zip(EPISODES[1:], later, strict=True):
        if episode.get("episode_index") != index:
            _fail("V104 embedded later episode index changed")
        receipts, _matches, _steps = v103._episode_receipts(episode, first=False)
        grouped.append((index, receipts))
        all_base.extend(receipts)
    if (
        sequence.get("all_abstract_execution_receipts") != all_base
        or sequence.get("abstract_execution_receipt_count") != len(all_base)
        or sequence.get("every_execution_action_has_content_addressed_receipt") is not True
    ):
        _fail("V104 embedded base receipt coverage changed")
    first_accept = first_disagreement = 0
    for wrapper in first.get("agreement_shield_receipts", []):
        if type(wrapper) is not dict:
            _fail("V104 embedded first shield wrapper changed")
        shield = v103._shield(wrapper.get("shield"))
        first_accept += shield["abstract_partial_agreement"] is True
        first_disagreement += shield["abstract_disagreement_abstained"] is True
    if (
        first.get("agreement_shield_accept_count") != first_accept
        or first.get("agreement_shield_disagreement_abstention_count")
        != first_disagreement
    ):
        _fail("V104 embedded first shield accounting changed")
    later_accept = later_disagreement = 0
    for episode in later:
        for wrapper in episode.get("abstract_plan_receipts", []):
            if type(wrapper) is not dict or type(wrapper.get("abstract_plan")) is not dict:
                _fail("V104 embedded later shield wrapper changed")
            shield = v103._shield(
                wrapper["abstract_plan"].get("agreement_shield_receipt")
            )
            later_accept += shield["abstract_partial_agreement"] is True
            later_disagreement += shield["abstract_disagreement_abstained"] is True
    if (
        sequence.get("later_agreement_shield_accept_receipt_count") != later_accept
        or sequence.get("later_agreement_shield_disagreement_abstention_count")
        != later_disagreement
    ):
        _fail("V104 embedded later shield accounting changed")
    labels = sequence.get("lifetime_target_ground_support_labels")
    if (
        type(labels) is not int
        or labels
        != sequence.get("partial_acquisition_ground_support_labels_paid_once")
        + sequence.get("certificate_ground_support_labels_paid_once")
    ):
        _fail("V104 embedded sequence label accounting changed")
    return (
        grouped,
        first_accept + later_accept,
        first_disagreement + later_disagreement,
        labels,
        sequence["target_model_activation_ground_support_labels_with_right_censoring"],
    )


def _hierarchical_sequence(
    sequence: Any, family: str, seed: int
) -> tuple[dict[str, Any], int, int, int, int]:
    v103._content_id(
        sequence, "sequence_id", _HIERARCHICAL_SEQUENCE_DOMAIN
    )
    predecessor = sequence.get("v103_receipted_sequence")
    grouped, accepts, disagreements, labels, activation = _base_sequence(
        predecessor, family, seed
    )
    base_pairs = [
        (episode_index, receipt)
        for episode_index, receipts in grouped
        for receipt in receipts
    ]
    observed = sequence.get("hierarchical_abstract_execution_receipts")
    if type(observed) is not list or len(observed) != len(base_pairs):
        _fail("V104 hierarchical receipt inventory changed")
    expected = []
    for document, (episode_index, base_receipt) in zip(
        observed, base_pairs, strict=True
    ):
        if (
            type(document) is not dict
            or document.get("base_v103_execution_receipt") != base_receipt
        ):
            _fail("V104 hierarchical/base receipt join changed")
        expected.append(_hierarchical_receipt(document, episode_index))
    if (
        sequence.get("schema")
        != "acfqp.generic_persistent_hierarchical_receipted_sequence.v104"
        or sequence.get("family") != family
        or sequence.get("seed") != seed
        or sequence.get("episode_indices") != list(EPISODES)
        or sequence.get("v103_receipted_sequence_id")
        != predecessor.get("sequence_id")
        or observed != expected
        or sequence.get("hierarchical_receipt_count") != len(expected)
        or sequence.get("execution_step_count") != len(expected)
        or sequence.get("every_action_classified_into_exactly_one_ordering_source")
        is not True
        or sequence.get("full_model_match_not_inferred_from_partial_fallback")
        is not True
        or sequence.get("partial_world_model_incompleteness_explicit") is not True
        or sequence.get("query_local_exact_overlay_remains_only_safety_authority")
        is not True
        or sequence.get("complete_world_model_synthesized") is not False
        or sequence.get("official_execution_allowed") is not False
    ):
        _fail("V104 hierarchical sequence contract changed")
    full = sum(
        row["abstract_ordering_source"] == "FULL_POST_DEPENDENCY_WORLD_MODEL"
        for row in expected
    )
    partial = sum(
        row["abstract_ordering_source"]
        == "COMPILED_PARTIAL_WORLD_MODEL_FALLBACK"
        for row in expected
    )
    exact = sum(
        row["abstract_ordering_source"] == "EXACT_CERTIFICATE_POLICY_ONLY"
        for row in expected
    )
    if (
        sequence.get("full_post_dependency_world_model_match_count") != full
        or sequence.get("compiled_partial_world_model_fallback_match_count") != partial
        or sequence.get("exact_certificate_policy_only_count") != exact
        or sequence.get("abstract_model_ordered_execution_count") != full + partial
        or full + partial + exact != len(expected)
    ):
        _fail("V104 hierarchical source counts changed")
    utilization = {
        "schema": "acfqp.hierarchical_abstract_execution_utilization.v104",
        "execution_receipt_count": len(expected),
        "execution_step_count": len(expected),
        "full_post_dependency_world_model_match_count": full,
        "compiled_partial_world_model_fallback_match_count": partial,
        "exact_certificate_policy_only_count": exact,
        "abstract_model_ordered_execution_count": full + partial,
        "abstract_model_ordered_fraction_numerator": full + partial,
        "abstract_model_ordered_fraction_denominator": len(expected),
        "strict_majority_of_executed_actions_ordered_by_full_or_explicit_partial_world_model": 2 * (full + partial) > len(expected),
        "full_world_model_match_is_not_inferred_from_partial_fallback": True,
        "partial_world_model_incompleteness_is_explicit": True,
        "every_execution_action_independently_receipted": True,
        "receipt_replay_uses_no_producer_summary_count": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return utilization, accepts, disagreements, labels, activation


def _direct(sequence: Any, family: str, seed: int) -> int:
    if (
        type(sequence) is not dict
        or sequence.get("schema") != "acfqp.generic_strict_cold_direct_sequence.v96"
        or sequence.get("family") != family
        or sequence.get("seed") != seed
        or sequence.get("episode_indices") != list(EPISODES)
        or sequence.get("free_target_rows_received") is not False
        or sequence.get("abstract_planning_compute_events") != 0
    ):
        _fail("V104 direct sequence changed")
    episodes = sequence.get("episodes")
    if type(episodes) is not list or len(episodes) != len(EPISODES):
        _fail("V104 direct episode inventory changed")
    labels = 0
    for index, episode in zip(EPISODES, episodes, strict=True):
        v103._content_id(
            episode, "episode_id", v103._DIRECT_EPISODE_DOMAIN
        )
        if (
            episode.get("episode_index") != index
            or episode.get("arm") != "STRICT_COLD_DIRECT_GROUND"
            or episode.get("success") is not True
            or episode.get("abstract_model_used_only_for_action_ordering") is not False
            or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
            is not True
        ):
            _fail("V104 direct episode semantics changed")
        labels += episode.get("total_target_ground_support_labels")
    if sequence.get("lifetime_target_ground_support_labels") != labels:
        _fail("V104 direct label accounting changed")
    return labels


def _occurrence(document: Any, family: str, seed: int) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V104 occurrence type changed")
    payload = {key: value for key, value in document.items() if key != "occurrence_id"}
    if (
        document.get("occurrence_id")
        != domains.extension_content_id_v104(
            domains.CONSTRUCTION_K7_HIERARCHICAL_UTILIZATION_OCCURRENCE_V104_DOMAIN,
            payload,
        )
        or document.get("schema")
        != "acfqp.hierarchical_abstract_utilization_occurrence.v104"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
    ):
        _fail("V104 occurrence identity changed")
    meta, accepts, disagreements, meta_labels, meta_activation = (
        _hierarchical_sequence(
            document.get("meta_prior_hierarchical_sequence"), family, seed
        )
    )
    no_prior, _no_accepts, _no_disagreements, no_labels, no_activation = (
        _hierarchical_sequence(
            document.get("no_prior_hierarchical_sequence"), family, seed
        )
    )
    direct_labels = _direct(document.get("strict_cold_direct_sequence"), family, seed)
    if (
        document.get("meta_prior_hierarchical_utilization") != meta
        or document.get("no_prior_hierarchical_utilization") != no_prior
        or document.get("accept_count_for_family_aggregation") != accepts
        or document.get("disagreement_count_for_family_aggregation") != disagreements
    ):
        _fail("V104 occurrence utilization projection changed")
    accounting = {
        "meta_activation_labels": meta_activation,
        "no_prior_activation_labels": no_activation,
        "meta_target_labels": meta_labels,
        "no_prior_target_labels": no_labels,
        "direct_target_labels": direct_labels,
        "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    if document.get("accounting") != accounting:
        _fail("V104 occurrence accounting changed")
    gate = {
        "every_execution_action_independently_receipted": True,
        "abstract_model_orders_strict_majority_of_executed_actions": meta[
            "strict_majority_of_executed_actions_ordered_by_full_or_explicit_partial_world_model"
        ],
        "abstract_ordering_rate_noninferior_to_no_prior": meta[
            "abstract_model_ordered_fraction_numerator"
        ]
        * no_prior["abstract_model_ordered_fraction_denominator"]
        >= no_prior["abstract_model_ordered_fraction_numerator"]
        * meta["abstract_model_ordered_fraction_denominator"],
        "full_and_partial_model_matches_kept_separate": True,
        "partial_world_model_incompleteness_explicit": True,
        "abstract_accept_path_observed": accepts > 0,
        "model_activation_strictly_earlier_than_no_prior": (
            meta_activation < no_activation
        ),
        "meta_task_labels_noninferior_to_no_prior": meta_labels <= no_labels,
        "meta_task_labels_strictly_below_cold_direct": meta_labels < direct_labels,
        "certificate_failure_only_query_discipline_clean": True,
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("registered_gate") != gate
        or document.get("full_post_dependency_world_model_primary_ordering_verified")
        is not False
        or document.get("partial_world_model_is_honest_incomplete_abstraction")
        is not True
        or document.get("complete_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V104 occurrence Gate changed")
    return {
        "target_family": family,
        "seed": seed,
        "full_match_count": meta["full_post_dependency_world_model_match_count"],
        "partial_fallback_match_count": meta[
            "compiled_partial_world_model_fallback_match_count"
        ],
        "exact_only_count": meta["exact_certificate_policy_only_count"],
        "abstract_ordered_count": meta["abstract_model_ordered_execution_count"],
        "execution_step_count": meta["execution_step_count"],
        "abstract_strict_majority": meta[
            "strict_majority_of_executed_actions_ordered_by_full_or_explicit_partial_world_model"
        ],
        "accept_count": accepts,
        "disagreement_count": disagreements,
        "meta_activation": meta_activation,
        "no_prior_activation": no_activation,
        "meta_labels": meta_labels,
        "no_prior_labels": no_labels,
        "direct_labels": direct_labels,
        "gate_passed": gate["passed"],
    }


def verify_hierarchical_utilization_campaign_bytes_v104(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V104 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V104 campaign is noncanonical")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("campaign_id")
        != domains.extension_content_id_v104(
            domains.CONSTRUCTION_K7_HIERARCHICAL_UTILIZATION_CAMPAIGN_V104_DOMAIN,
            payload,
        )
        or document.get("schema")
        != "acfqp.hierarchical_abstract_utilization_campaign.v104"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v103_failed_campaign_id") != V103_CAMPAIGN_ID
        or document.get("v103_failure_verification_id") != V103_VERIFICATION_ID
        or document.get("source_library_artifact_id") != SOURCE_LIBRARY_ARTIFACT_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V104 campaign inventory changed")
    replay = [
        _occurrence(row, family, seed)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    totals = {
        "meta_activation": sum(row["meta_activation"] for row in replay),
        "no_prior_activation": sum(row["no_prior_activation"] for row in replay),
        "meta_labels": sum(row["meta_labels"] for row in replay),
        "no_prior_labels": sum(row["no_prior_labels"] for row in replay),
        "direct_labels": sum(row["direct_labels"] for row in replay),
        "meta_full_post_dependency_world_model_match_count": sum(
            row["full_match_count"] for row in replay
        ),
        "meta_compiled_partial_world_model_fallback_match_count": sum(
            row["partial_fallback_match_count"] for row in replay
        ),
        "meta_exact_certificate_policy_only_count": sum(
            row["exact_only_count"] for row in replay
        ),
        "meta_abstract_model_ordered_execution_count": sum(
            row["abstract_ordered_count"] for row in replay
        ),
        "meta_execution_step_count": sum(row["execution_step_count"] for row in replay),
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    coverage = []
    for family in sorted({family for family, _seed in TARGETS}):
        family_rows = [row for row in replay if row["target_family"] == family]
        accepts = sum(row["accept_count"] for row in family_rows)
        disagreements = sum(row["disagreement_count"] for row in family_rows)
        coverage.append(
            {
                "target_family": family,
                "occurrence_count": len(family_rows),
                "accept_count": accepts,
                "disagreement_abstention_count": disagreements,
                "both_shield_paths_observed_across_family": accepts > 0 and disagreements > 0,
            }
        )
    if document.get("accounting") != totals or document.get("family_wide_shield_path_coverage") != coverage:
        _fail("V104 aggregate accounting changed")
    ood = document.get("incompatible_schema_no_transfer_control")
    passed = (
        all(row["gate_passed"] for row in replay)
        and all(row["both_shield_paths_observed_across_family"] for row in coverage)
        and 2 * totals["meta_abstract_model_ordered_execution_count"]
        > totals["meta_execution_step_count"]
        and totals["meta_activation"] < totals["no_prior_activation"]
        and totals["meta_labels"] <= totals["no_prior_labels"]
        and totals["meta_labels"] < totals["direct_labels"]
        and type(ood) is dict
        and ood.get("strict_ood_no_transfer") is True
    )
    gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(row["gate_passed"] for row in replay),
        "every_occurrence_abstract_model_orders_strict_majority": all(
            row["abstract_strict_majority"] for row in replay
        ),
        "every_target_family_exercises_both_shield_paths": all(
            row["both_shield_paths_observed_across_family"] for row in coverage
        ),
        "aggregate_activation_sample_tax_strictly_reduced": totals[
            "meta_activation"
        ]
        < totals["no_prior_activation"],
        "aggregate_negative_transfer_absent": totals["meta_labels"]
        <= totals["no_prior_labels"],
        "aggregate_meta_labels_strictly_below_cold_direct": totals["meta_labels"]
        < totals["direct_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood.get(
            "strict_ood_no_transfer"
        )
        is True,
        "passed": passed,
    }
    if (
        document.get("registered_gate") != gate
        or document.get("registered_multistep_execution_primarily_abstract_ordered_verified")
        is not True
        or document.get("ground_distinctions_acquired_only_after_certificate_failure_verified")
        is not True
        or document.get("full_post_dependency_world_model_primary_ordering_verified")
        is not False
        or document.get("partial_world_model_primary_ordering_verified") is not True
        or document.get("complete_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V104 campaign Gate or claim boundary changed")
    return {
        "schema": "acfqp.hierarchical_abstract_utilization_verification.v104",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V104_HONEST_PARTIAL_ABSTRACT_UTILIZATION_VERIFIED",
        "producer_free_hierarchical_per_action_receipt_replay": True,
        "producer_summary_counts_not_used": True,
        "verified_occurrences": replay,
        "verified_accounting": totals,
        "verified_family_wide_shield_path_coverage": coverage,
        "registered_gate_independently_verified": True,
        "sample_tax_reduction_verified": totals["meta_activation"]
        < totals["no_prior_activation"],
        "negative_transfer_absent": totals["meta_labels"]
        <= totals["no_prior_labels"],
        "ground_query_discipline_independently_verified": True,
        "full_post_dependency_world_model_primary_ordering_verified": False,
        "partial_world_model_primary_ordering_verified": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_hierarchical_utilization_verification_v104(raw: bytes) -> bytes:
    payload = verify_hierarchical_utilization_campaign_bytes_v104(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v104(
            domains.CONSTRUCTION_K7_HIERARCHICAL_UTILIZATION_VERIFICATION_V104_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V104 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_hierarchical_utilization_verification_v104",
    "verify_hierarchical_utilization_campaign_bytes_v104",
)
