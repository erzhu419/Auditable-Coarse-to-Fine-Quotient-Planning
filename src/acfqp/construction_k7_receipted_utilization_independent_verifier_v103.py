"""Producer-free semantic replay of V103 execution receipts and failed Gate."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v103 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json

CAMPAIGN_ID = "ae93067c6dfacbe158d3db700bc7c1b187e7e2d05d862d8cffcf971e1866d006"
CAMPAIGN_BYTE_COUNT = 4_763_416
CAMPAIGN_SHA256 = "810500096381e789a39bcce5f4e9650d36d2cfc431dbf9513fe20aeefc3c3b16"
PREREGISTRATION_ID = "ac9d7759187a8d97edeeab924210dc066dc47f5dc6eff144954ecc1cf25516c3"
V102_CAMPAIGN_ID = "f0b45ab4a6466988ac6cef39bd2723869d7bb3d4409afc60b9d00e035609d3d7"
V102_VERIFICATION_ID = "21cc3100d7caf82d6802a72899593a78d7fafec0524c285c53cec0cb9f42d00b"
SOURCE_LIBRARY_ARTIFACT_ID = "4f0a9592f7d6ba2d7683e9328f76dbd01bd18a3a47a062ea764f7a20012caeba"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_015_101),
    ("BALANCED_BATCH_REFINEMENT", 1_015_102),
    ("MAINTENANCE_CASCADE", 1_015_103),
    ("MAINTENANCE_CASCADE", 1_015_104),
)
EPISODES = (121, 122, 123)
VERIFICATION_ID = "d9b8504dd7dceef0ad8a5e01f312aaccf61fa8c28e00c376d7bb14de61a448ec"
EXPECTED_CANONICAL_BYTE_COUNT = 3_025
EXPECTED_CANONICAL_SHA256 = "65f33d9d5dfdff6d99ead881d3a37cea96c73d9a92eda78c8c11af67222098ae"

_RECEIPT_DOMAIN = b"acfqp:generic-abstract-execution-receipt:v103\x00"
_SHIELD_DOMAIN = b"acfqp:abstract-partial-agreement-shield:v99\x00"
_FIRST_EPISODE_DOMAIN = b"acfqp:receipted-online-certificate-episode:v103\x00"
_LATER_EPISODE_DOMAIN = b"acfqp:generic-receipted-preloaded-certificate-episode:v103\x00"
_DIRECT_EPISODE_DOMAIN = b"acfqp:generic-preloaded-certificate-receding-episode:v74\x00"
_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-receipted-sequence:v103\x00"


class ConstructionK7ReceiptedUtilizationIndependentVerifierV103Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReceiptedUtilizationIndependentVerifierV103Error(message)


def _hash(prefix: bytes, payload: Any) -> str:
    return hashlib.sha256(prefix + canonical_json_bytes(payload)).hexdigest()


def _content_id(document: Any, key: str, prefix: bytes, omit: set[str] | None = None) -> None:
    if type(document) is not dict:
        _fail(f"V103 {key} document type changed")
    omitted = {key} if omit is None else {key, *omit}
    payload = {name: value for name, value in document.items() if name not in omitted}
    if document.get(key) != _hash(prefix, payload):
        _fail(f"V103 {key} changed")


def _shield(document: Any) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V103 shield type changed")
    abstract = document.get("abstract_proposal")
    partial = document.get("partial_proposal")
    legal = document.get("legal_action_keys")
    if (
        type(abstract) is not list
        or type(partial) is not list
        or type(legal) is not list
        or not legal
        or any(type(key) is not int for key in (*abstract, *partial, *legal))
        or len(set(legal)) != len(legal)
    ):
        _fail("V103 shield inventory changed")
    abstract_key = next((key for key in abstract if key in legal), None)
    partial_key = next((key for key in partial if key in legal), None)
    agreement = (
        abstract_key is not None
        and partial_key is not None
        and abstract_key == partial_key
    )
    order: list[int] = []
    if agreement:
        order.append(abstract_key)
    if partial_key is not None and partial_key not in order:
        order.append(partial_key)
    order.extend(key for key in legal if key not in order)
    payload = {
        "schema": "acfqp.abstract_partial_agreement_shield.v99",
        "abstract_proposal": abstract,
        "partial_proposal": partial,
        "legal_action_keys": legal,
        "abstract_legal_proposal": abstract_key,
        "partial_legal_proposal": partial_key,
        "abstract_partial_agreement": agreement,
        "abstract_proposal_admitted_to_action_order": agreement,
        "abstract_disagreement_abstained": abstract_key is not None and not agreement,
        "shielded_action_order": order,
        "abstract_proposal_can_precede_partial_without_agreement": False,
        "same_shield_applied_to_prior_and_no_prior_arms": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    expected = {**payload, "shield_receipt_id": _hash(_SHIELD_DOMAIN, payload)}
    if document != expected:
        _fail("V103 shield semantics changed")
    return expected


def _receipt(document: Any) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V103 execution receipt type changed")
    shield = _shield(document.get("shield_receipt"))
    raw = document.get("raw_state")
    chosen = document.get("chosen_action_key")
    index = document.get("decision_index")
    if (
        type(raw) is not list
        or any(type(value) is not int for value in raw)
        or type(chosen) is not int
        or type(index) is not int
        or index < 0
        or chosen not in shield["legal_action_keys"]
    ):
        _fail("V103 execution receipt inventory changed")
    agreement = shield["abstract_partial_agreement"]
    abstract_key = shield["abstract_legal_proposal"]
    payload = {
        "schema": "acfqp.generic_abstract_execution_receipt.v103",
        "decision_index": index,
        "raw_state": raw,
        "chosen_action_key": chosen,
        "abstract_proposal": shield["abstract_proposal"],
        "partial_proposal": shield["partial_proposal"],
        "legal_action_keys": shield["legal_action_keys"],
        "shield_receipt": shield,
        "abstract_partial_exact_action_agreement": agreement,
        "chosen_action_matches_admitted_abstract_proposal": (
            agreement and chosen == abstract_key
        ),
        "receipt_is_observation_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    expected = {**payload, "execution_receipt_id": _hash(_RECEIPT_DOMAIN, payload)}
    if document != expected:
        _fail("V103 execution receipt semantics changed")
    return expected


def _episode_receipts(episode: Any, *, first: bool) -> tuple[list[dict[str, Any]], int, int]:
    extras = set() if first else {
        "new_certificate_labels_charged_this_episode",
        "paid_certificate_labels_cumulative",
        "persistent_exact_support_group_count",
    }
    _content_id(
        episode,
        "episode_id",
        _FIRST_EPISODE_DOMAIN if first else _LATER_EPISODE_DOMAIN,
        extras,
    )
    expected_schema = (
        "acfqp.receipted_online_certificate_episode.v103"
        if first
        else "acfqp.generic_receipted_preloaded_certificate_episode.v103"
    )
    receipts = episode.get("abstract_execution_receipts")
    actions = episode.get("action_keys")
    if (
        episode.get("schema") != expected_schema
        or type(receipts) is not list
        or type(actions) is not list
        or episode.get("execution_steps") != len(actions)
        or len(receipts) != len(actions)
        or episode.get("every_execution_action_has_content_addressed_receipt") is not True
    ):
        _fail("V103 episode execution inventory changed")
    verified = [_receipt(row) for row in receipts]
    if [row["decision_index"] for row in verified] != list(range(len(actions))):
        _fail("V103 episode decision sequence changed")
    if [row["chosen_action_key"] for row in verified] != actions:
        _fail("V103 receipt/action join changed")
    matches = [row["chosen_action_matches_admitted_abstract_proposal"] for row in verified]
    if first:
        if episode.get("shielded_joint_execution_action_match_count") != sum(matches):
            _fail("V103 first episode receipt total changed")
    elif (
        episode.get("execution_action_matches_abstract_proposal") != matches
        or episode.get("execution_action_matches_abstract_proposal_count") != sum(matches)
    ):
        _fail("V103 later episode receipt total changed")
    return verified, sum(matches), len(actions)


def _sequence(sequence: Any, family: str, seed: int) -> tuple[dict[str, Any], int, int, int, int]:
    _content_id(sequence, "sequence_id", _SEQUENCE_DOMAIN)
    if (
        sequence.get("schema") != "acfqp.generic_persistent_receipted_sequence.v103"
        or sequence.get("family") != family
        or sequence.get("seed") != seed
        or sequence.get("episode_indices") != list(EPISODES)
        or sequence.get("complete_world_model_synthesized") is not False
        or sequence.get("official_execution_allowed") is not False
        or sequence.get("persistent_exact_overlay_exclusively_discharges_safety") is not True
        or sequence.get("every_new_ground_query_followed_a_failed_certificate") is not True
    ):
        _fail("V103 sequence contract changed")
    first = sequence.get("first_agreement_shielded_online_episode")
    later = sequence.get("later_persistent_episodes")
    if type(later) is not list or len(later) != 2:
        _fail("V103 episode inventory changed")
    all_receipts: list[dict[str, Any]] = []
    first_receipts, matches, steps = _episode_receipts(first, first=True)
    all_receipts.extend(first_receipts)
    for expected_index, episode in zip(EPISODES[1:], later, strict=True):
        if episode.get("episode_index") != expected_index:
            _fail("V103 later episode index changed")
        verified, episode_matches, episode_steps = _episode_receipts(episode, first=False)
        all_receipts.extend(verified)
        matches += episode_matches
        steps += episode_steps
    if (
        sequence.get("all_abstract_execution_receipts") != all_receipts
        or sequence.get("abstract_execution_receipt_count") != len(all_receipts)
        or sequence.get("every_execution_action_has_content_addressed_receipt") is not True
    ):
        _fail("V103 sequence receipt coverage changed")
    utilization = {
        "schema": "acfqp.receipted_abstract_execution_utilization.v103",
        "execution_receipt_count": len(all_receipts),
        "execution_step_count": steps,
        "admitted_abstract_execution_match_count": matches,
        "abstract_execution_match_fraction_numerator": matches,
        "abstract_execution_match_fraction_denominator": len(all_receipts),
        "strict_majority_of_executed_actions_match_admitted_abstract_proposal": (
            2 * matches > len(all_receipts)
        ),
        "every_execution_action_independently_receipted": True,
        "receipt_replay_uses_no_producer_summary_count": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    first_accept = first_disagreement = 0
    for wrapper in first.get("agreement_shield_receipts", []):
        if type(wrapper) is not dict:
            _fail("V103 first shield wrapper changed")
        shield = _shield(wrapper.get("shield"))
        first_accept += shield["abstract_partial_agreement"] is True
        first_disagreement += shield["abstract_disagreement_abstained"] is True
    if (
        first.get("agreement_shield_accept_count") != first_accept
        or first.get("agreement_shield_disagreement_abstention_count") != first_disagreement
    ):
        _fail("V103 first shield accounting changed")
    later_accept = later_disagreement = 0
    for episode in later:
        for wrapper in episode.get("abstract_plan_receipts", []):
            if type(wrapper) is not dict or type(wrapper.get("abstract_plan")) is not dict:
                _fail("V103 later shield wrapper changed")
            shield = _shield(wrapper["abstract_plan"].get("agreement_shield_receipt"))
            later_accept += shield["abstract_partial_agreement"] is True
            later_disagreement += shield["abstract_disagreement_abstained"] is True
    if (
        sequence.get("later_agreement_shield_accept_receipt_count") != later_accept
        or sequence.get("later_agreement_shield_disagreement_abstention_count")
        != later_disagreement
    ):
        _fail("V103 later shield accounting changed")
    labels = sequence.get("lifetime_target_ground_support_labels")
    if (
        type(labels) is not int
        or labels
        != sequence.get("partial_acquisition_ground_support_labels_paid_once")
        + sequence.get("certificate_ground_support_labels_paid_once")
    ):
        _fail("V103 sequence label accounting changed")
    return utilization, first_accept + later_accept, first_disagreement + later_disagreement, labels, sequence["target_model_activation_ground_support_labels_with_right_censoring"]


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
        _fail("V103 direct sequence changed")
    episodes = sequence.get("episodes")
    if type(episodes) is not list or len(episodes) != len(EPISODES):
        _fail("V103 direct episode inventory changed")
    labels = 0
    for index, episode in zip(EPISODES, episodes, strict=True):
        _content_id(episode, "episode_id", _DIRECT_EPISODE_DOMAIN)
        if (
            episode.get("episode_index") != index
            or episode.get("arm") != "STRICT_COLD_DIRECT_GROUND"
            or episode.get("success") is not True
            or episode.get("abstract_model_used_only_for_action_ordering") is not False
            or episode.get("query_local_exact_overlay_exclusively_used_for_safety") is not True
        ):
            _fail("V103 direct episode semantics changed")
        labels += episode.get("total_target_ground_support_labels")
    if sequence.get("lifetime_target_ground_support_labels") != labels:
        _fail("V103 direct label accounting changed")
    return labels


def _occurrence(document: Any, family: str, seed: int) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V103 occurrence type changed")
    payload = {key: value for key, value in document.items() if key != "occurrence_id"}
    if (
        document.get("occurrence_id")
        != domains.extension_content_id_v103(
            domains.CONSTRUCTION_K7_RECEIPTED_UTILIZATION_OCCURRENCE_V103_DOMAIN,
            payload,
        )
        or document.get("schema") != "acfqp.receipted_abstract_utilization_occurrence.v103"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
    ):
        _fail("V103 occurrence identity changed")
    meta, accepts, disagreements, meta_labels, meta_activation = _sequence(
        document.get("meta_prior_persistent_receipted_sequence"), family, seed
    )
    no_prior, _no_accepts, _no_disagreements, no_labels, no_activation = _sequence(
        document.get("no_prior_persistent_receipted_sequence"), family, seed
    )
    direct_labels = _direct(document.get("strict_cold_direct_sequence"), family, seed)
    if (
        document.get("meta_prior_receipted_utilization") != meta
        or document.get("no_prior_receipted_utilization") != no_prior
        or document.get("accept_count_for_family_aggregation") != accepts
        or document.get("disagreement_count_for_family_aggregation") != disagreements
    ):
        _fail("V103 occurrence utilization projection changed")
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
        _fail("V103 occurrence accounting changed")
    gate = {
        "every_execution_action_independently_receipted": meta["every_execution_action_independently_receipted"],
        "abstract_ordering_matches_strict_majority_of_executed_actions": meta["strict_majority_of_executed_actions_match_admitted_abstract_proposal"],
        "abstract_execution_match_rate_noninferior_to_no_prior": meta["abstract_execution_match_fraction_numerator"] * no_prior["abstract_execution_match_fraction_denominator"] >= no_prior["abstract_execution_match_fraction_numerator"] * meta["abstract_execution_match_fraction_denominator"],
        "abstract_accept_path_observed": accepts > 0,
        "model_activation_strictly_earlier_than_no_prior": meta_activation < no_activation,
        "meta_task_labels_noninferior_to_no_prior": meta_labels <= no_labels,
        "meta_task_labels_strictly_below_cold_direct": meta_labels < direct_labels,
        "certificate_failure_only_query_discipline_clean": True,
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("registered_gate") != gate
        or document.get("complete_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V103 occurrence Gate changed")
    return {
        "target_family": family,
        "seed": seed,
        "receipt_match_count": meta["admitted_abstract_execution_match_count"],
        "execution_step_count": meta["execution_step_count"],
        "receipt_strict_majority": meta["strict_majority_of_executed_actions_match_admitted_abstract_proposal"],
        "accept_count": accepts,
        "disagreement_count": disagreements,
        "meta_activation": meta_activation,
        "no_prior_activation": no_activation,
        "meta_labels": meta_labels,
        "no_prior_labels": no_labels,
        "direct_labels": direct_labels,
        "gate_passed": gate["passed"],
    }


def verify_receipted_utilization_campaign_bytes_v103(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V103 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V103 campaign is noncanonical")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("campaign_id")
        != domains.extension_content_id_v103(
            domains.CONSTRUCTION_K7_RECEIPTED_UTILIZATION_CAMPAIGN_V103_DOMAIN,
            payload,
        )
        or document.get("schema") != "acfqp.receipted_abstract_utilization_campaign.v103"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v102_campaign_id") != V102_CAMPAIGN_ID
        or document.get("v102_verification_id") != V102_VERIFICATION_ID
        or document.get("source_library_artifact_id") != SOURCE_LIBRARY_ARTIFACT_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V103 campaign inventory changed")
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
        "meta_receipted_abstract_execution_match_count": sum(row["receipt_match_count"] for row in replay),
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
        _fail("V103 aggregate accounting changed")
    ood = document.get("incompatible_schema_no_transfer_control")
    passed = (
        all(row["gate_passed"] for row in replay)
        and all(row["both_shield_paths_observed_across_family"] for row in coverage)
        and 2 * totals["meta_receipted_abstract_execution_match_count"]
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
        "every_occurrence_abstract_orders_strict_majority_of_executed_actions_from_receipts": all(row["receipt_strict_majority"] for row in replay),
        "every_target_family_exercises_both_shield_paths": all(row["both_shield_paths_observed_across_family"] for row in coverage),
        "aggregate_activation_sample_tax_strictly_reduced": totals["meta_activation"] < totals["no_prior_activation"],
        "aggregate_negative_transfer_absent": totals["meta_labels"] <= totals["no_prior_labels"],
        "aggregate_meta_labels_strictly_below_cold_direct": totals["meta_labels"] < totals["direct_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood.get("strict_ood_no_transfer") is True,
        "passed": passed,
    }
    if (
        document.get("registered_gate") != gate
        or document.get("registered_multistep_execution_primarily_abstract_ordered_verified") is not False
        or document.get("ground_distinctions_acquired_only_after_certificate_failure_verified") is not False
        or document.get("complete_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V103 campaign Gate or claim boundary changed")
    return {
        "schema": "acfqp.receipted_utilization_verification.v103",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V103_RECEIPTED_ABSTRACT_UTILIZATION_GATE_FAILED",
        "producer_free_per_action_receipt_replay": True,
        "producer_summary_counts_not_used": True,
        "verified_occurrences": replay,
        "verified_accounting": totals,
        "verified_family_wide_shield_path_coverage": coverage,
        "registered_gate_independently_verified": False,
        "registered_failure_reason": "NO_OCCURRENCE_REACHED_STRICT_MAJORITY_OF_EXECUTED_ACTIONS_MATCHING_ADMITTED_ABSTRACT_PROPOSALS",
        "sample_tax_reduction_still_observed": totals["meta_activation"] < totals["no_prior_activation"],
        "negative_transfer_absent": totals["meta_labels"] <= totals["no_prior_labels"],
        "ground_query_discipline_independently_verified": True,
        "fresh_successor_required": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_receipted_utilization_verification_v103(raw: bytes) -> bytes:
    payload = verify_receipted_utilization_campaign_bytes_v103(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v103(
            domains.CONSTRUCTION_K7_RECEIPTED_UTILIZATION_VERIFICATION_V103_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V103 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_receipted_utilization_verification_v103",
    "verify_receipted_utilization_campaign_bytes_v103",
)
