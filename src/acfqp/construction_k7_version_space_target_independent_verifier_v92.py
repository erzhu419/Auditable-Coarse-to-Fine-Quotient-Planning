"""Producer-free verification of the frozen, failed V92 campaign."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v92 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "97dd235a71f67a79bc9c265f3e45c993773f92d5f6463023c940593a965fb335"
CAMPAIGN_BYTE_COUNT = 86_536
CAMPAIGN_SHA256 = "4e11972eef3d99d7823091aeca36563e949b8fb56ed12bdc40f50530ac29346f"
SOURCE_ACCEPTANCE_ID = "59371553fe2e1a9898f1da41abc2c94d860e6833bdada98bc10ffe699d7d444c"
SOURCE_MODEL_ID = "eb79346ce607c99960670f36aa995033c30be67a9322b4620fff7b29bb4eecd7"
VERIFICATION_ID = (
    "eded5ff6ce0d8b87baebc7d83b77fecec8e511c6dd06e07a4bae85a2c54bc388"
)
EXPECTED_CANONICAL_BYTE_COUNT = 1_239
EXPECTED_CANONICAL_SHA256 = (
    "ae87ec1507cf0a4ce954ab6abe1be6dd51166fa7bcab280ab6a0242fea3b06ee"
)


class ConstructionK7VersionSpaceTargetIndependentVerifierV92Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7VersionSpaceTargetIndependentVerifierV92Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _check_content_id(
    document: Mapping[str, Any], key: str, domain: str
) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v92(domain, payload) != document.get(key):
        _fail(f"V92 {key} content identity changed")


def _check_episode(episode: Any) -> None:
    if type(episode) is not dict:
        _fail("V92 episode type changed")
    payload = {key: value for key, value in episode.items() if key != "episode_id"}
    if (
        _generic_id(
            b"acfqp:generic-version-space-target-episode:v68\x00", payload
        )
        != episode.get("episode_id")
        or episode.get("success") is not True
        or episode.get("all_ground_queries_followed_failed_certificates") is not True
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or episode.get("model_or_alignment_used_as_safety_authority") is not False
        or episode.get("complete_world_model_synthesized") is not False
    ):
        _fail("V92 episode identity or safety boundary changed")
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    if (
        type(failures) is not list
        or type(distinctions) is not list
        or len(failures) != len(distinctions)
        or episode.get("target_certificate_local_ground_support_labels")
        != sum(row.get("ground_support_labels", -1) for row in distinctions)
        or any(
            row.get("ground_query_performed_before_failure") is not False
            for row in failures
        )
        or any(
            row.get("query_after_failed_certificate") is not True
            for row in distinctions
        )
    ):
        _fail("V92 exact certificate/distinction accounting changed")
    receipts = episode.get("abstract_plan_receipts")
    if episode.get("arm") == "JOINT_VERSION_SPACE_WORLD_MODEL":
        if (
            type(receipts) is not list
            or len(receipts) != episode.get("abstract_plan_success_count")
            or any(
                row.get("abstract_plan", {}).get(
                    "all_residual_version_spaces_jointly_propagated"
                )
                is not True
                or row.get("abstract_plan", {}).get(
                    "all_mdl_minimal_terminal_trees_jointly_propagated"
                )
                is not True
                or row.get("abstract_plan", {}).get(
                    "ground_transition_accessed_during_abstract_search"
                )
                is not False
                or row.get("abstract_plan", {}).get(
                    "abstract_plan_used_as_safety_authority"
                )
                is not False
                for row in receipts
            )
        ):
            _fail("V92 abstract-plan receipt inventory changed")
    elif episode.get("arm") == "STRICT_DIRECT_GROUND":
        if receipts != [] or episode.get("abstract_planning_compute_events") != 0:
            _fail("V92 strict arm acquired abstract planning work")
    else:
        _fail("V92 episode arm changed")


def _check_ablation(ablation: Any) -> None:
    if type(ablation) is not dict:
        _fail("V92 ablation type changed")
    payload = {key: value for key, value in ablation.items() if key != "ablation_id"}
    if (
        _generic_id(
            b"acfqp:generic-version-space-target-ablation:v68\x00", payload
        )
        != ablation.get("ablation_id")
        or ablation.get("source_model_id") != SOURCE_MODEL_ID
        or ablation.get("all_ground_queries_followed_failed_certificates") is not True
        or ablation.get("model_or_alignment_used_as_safety_authority") is not False
        or ablation.get("official_execution_allowed") is not False
        or ablation.get("official_scalar_cost") is not None
        or ablation.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V92 ablation identity or claim boundary changed")
    alignment = ablation.get("alignment")
    alignment_payload = {
        key: value for key, value in alignment.items() if key != "alignment_id"
    }
    if (
        type(alignment) is not dict
        or _generic_id(
            b"acfqp:generic-version-space-target-alignment:v68\x00",
            alignment_payload,
        )
        != alignment.get("alignment_id")
        or alignment.get("target_episode_outcomes_used") is not False
        or alignment.get("alignment_used_as_safety_authority") is not False
    ):
        _fail("V92 alignment identity or boundary changed")
    arms = ablation.get("arms")
    if type(arms) is not dict or set(arms) != {
        "JOINT_VERSION_SPACE_WORLD_MODEL",
        "STRICT_DIRECT_GROUND",
    }:
        _fail("V92 matched arm inventory changed")
    for episode in arms.values():
        _check_episode(episode)
    derived = arms["JOINT_VERSION_SPACE_WORLD_MODEL"]
    strict = arms["STRICT_DIRECT_GROUND"]
    if (
        ablation.get("derived_target_certificate_local_ground_support_labels")
        != derived["target_certificate_local_ground_support_labels"]
        or ablation.get("strict_target_certificate_local_ground_support_labels")
        != strict["target_certificate_local_ground_support_labels"]
        or ablation.get("strict_minus_derived_target_labels")
        != strict["target_certificate_local_ground_support_labels"]
        - derived["target_certificate_local_ground_support_labels"]
    ):
        _fail("V92 matched label arithmetic changed")


def verify_version_space_target_campaign_bytes_v92(raw: bytes) -> bytes:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V92 campaign bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V92 campaign is not canonical")
    _check_content_id(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_VERSION_SPACE_TARGET_CAMPAIGN_V92_DOMAIN,
    )
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("source_acceptance_id") != SOURCE_ACCEPTANCE_ID
        or document.get("source_model_id") != SOURCE_MODEL_ID
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
        or document.get("complete_world_model_synthesized") is not False
        or document.get("global_exact_dynamics_claimed") is not False
    ):
        _fail("V92 campaign identity or claim boundary changed")
    occurrences = document.get("target_occurrences")
    if type(occurrences) is not list or len(occurrences) != 2:
        _fail("V92 occurrence inventory changed")
    for occurrence in occurrences:
        _check_content_id(
            occurrence,
            "occurrence_id",
            domains.CONSTRUCTION_K7_VERSION_SPACE_TARGET_OCCURRENCE_V92_DOMAIN,
        )
        if occurrence.get("matched_ablation") is not None:
            _check_ablation(occurrence["matched_ablation"])
    failed = [row for row in occurrences if row.get("matched_ablation") is None]
    completed = [row for row in occurrences if row.get("matched_ablation") is not None]
    if (
        len(failed) != 1
        or failed[0].get("target_seed") != 951101
        or failed[0].get("failure_reason")
        != "V68 retained terminal tree missed the target prefix"
        or len(completed) != 1
        or completed[0].get("target_seed") != 951102
    ):
        _fail("V92 frozen failure/completion split changed")
    accounting = document.get("accounting")
    completed_ablation = completed[0]["matched_ablation"]
    if (
        type(accounting) is not dict
        or accounting.get("derived_target_certificate_local_labels") != 11
        or accounting.get("strict_target_certificate_local_labels") != 11
        or accounting.get("strict_minus_derived_target_certificate_labels") != 0
        or accounting.get("target_common_partial_labels") != 50
        or completed_ablation.get("actual_target_sample_reduction_observed") is not False
    ):
        _fail("V92 failed-campaign accounting changed")
    gate = document.get("registered_gate")
    if (
        type(gate) is not dict
        or gate.get("passed") is not False
        or gate.get("completed_target_occurrence_count") != 1
        or gate.get("aggregate_target_certificate_label_reduction_observed")
        is not False
    ):
        _fail("V92 failed Gate was reinterpreted")
    payload = {
        "schema": "acfqp.version_space_target_verification.v92",
        "campaign_id": CAMPAIGN_ID,
        "source_acceptance_id": SOURCE_ACCEPTANCE_ID,
        "source_model_id": SOURCE_MODEL_ID,
        "campaign_content_identity_verified": True,
        "occurrence_ablation_episode_and_alignment_content_ids_verified": True,
        "certificate_failure_before_query_and_local_distinction_accounting_verified": True,
        "abstract_plan_receipt_claim_boundaries_verified": True,
        "frozen_terminal_transfer_failure_preserved": True,
        "frozen_no_sample_reduction_result_preserved": True,
        "common_partial_raw_transition_rows_embedded_for_independent_replay": False,
        "raw_partial_acquisition_or_alignment_semantics_independently_replayed": False,
        "typed_result": "FAILED_CAMPAIGN_IDENTITY_AND_INTERNAL_ACCOUNTING_VERIFIED_RAW_PARTIAL_REPLAY_UNAVAILABLE",
        "producer_module_imported": False,
        "campaign_builder_imported": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v92(
            domains.CONSTRUCTION_K7_VERSION_SPACE_TARGET_VERIFICATION_V92_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V92 verification changed")
    return result


__all__ = ("VERIFICATION_ID", "verify_version_space_target_campaign_bytes_v92")
