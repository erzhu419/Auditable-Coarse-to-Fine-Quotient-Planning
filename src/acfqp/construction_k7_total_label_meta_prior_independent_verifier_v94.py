"""Producer-free verification of the frozen successful V94 campaign.

This verifier deliberately does not import the V94 producer, campaign core, or
the V73--V75 acquisition/planning implementation.  It replays the portable
observation projections, stopping arithmetic, content identities, certificate
discipline, and separated accounting directly from the frozen bytes.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v94 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "8fcb91339c02f818ef9ff829e99ab1ac000fbc6940888d700c31c461fafabde8"
CAMPAIGN_BYTE_COUNT = 278_767
CAMPAIGN_SHA256 = "b1419448d18011bec11dfe604573856b6f7e4a56c642a078c0804a1cb410465f"
PREREGISTRATION_ID = (
    "c3b9e3e8b5ea76bb347afdc6d5ebcb07f4c974f4fbbad013ef188e24d5173018"
)
SOURCE_MODEL_ID = "eb79346ce607c99960670f36aa995033c30be67a9322b4620fff7b29bb4eecd7"
SOURCE_ACCEPTANCE_ID = (
    "59371553fe2e1a9898f1da41abc2c94d860e6833bdada98bc10ffe699d7d444c"
)
SOURCE_ACCEPTANCE_VERIFICATION_ID = (
    "bf929def883b2134d32c7bc59cf4b2605b9af7ddb37a3ae37cd0efa3a2d59d7a"
)
V93_FAILED_CAMPAIGN_ID = (
    "1b9b2fb6a1a837428c40d7d4b42546d1bed75fb406f53a5d84af0c69d25b891e"
)
V93_FAILED_VERIFICATION_ID = (
    "841f791d85629fb9317f0a05a02a143ede1df5de340d9495ad6e0c85c213482c"
)

VERIFICATION_ID = "bfd308d496f9e07ea00b2d7f55e0ae2230a4c41f543d704987bfc732cb32be5a"
EXPECTED_CANONICAL_BYTE_COUNT = 1_904
EXPECTED_CANONICAL_SHA256 = (
    "50464d7541a7bc0e5b6eb19afa7928f260eb9c16701b2f1df1386a61be15c2a2"
)

_CANDIDATE_DOMAIN = b"acfqp:generic-low-label-residual-candidate:v73\x00"
_EPISODE_DOMAIN = b"acfqp:generic-preloaded-certificate-receding-episode:v74\x00"
_ABLATION_DOMAIN = b"acfqp:generic-total-label-residual-transfer-ablation:v75\x00"


class ConstructionK7TotalLabelMetaPriorIndependentVerifierV94Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TotalLabelMetaPriorIndependentVerifierV94Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _check_v94_id(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V94 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v94(domain, payload) != document.get(key):
        _fail(f"V94 {key} content identity changed")


def _check_generic_id(document: Any, key: str, domain: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V94 {key} generic document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if _generic_id(domain, payload) != document.get(key):
        _fail(f"V94 {key} generic content identity changed")


def _groups(rows: Any) -> list[list[dict[str, Any]]]:
    if type(rows) is not list:
        _fail("V94 transition inventory type changed")
    grouped: dict[tuple[tuple[int, ...], int], list[dict[str, Any]]] = {}
    order: list[tuple[tuple[int, ...], int]] = []
    for row in rows:
        selected = row.get("selected_action") if type(row) is dict else None
        pre = row.get("pre_vector") if type(row) is dict else None
        key = selected.get("action_key") if type(selected) is dict else None
        fields = selected.get("anonymous_fields") if type(selected) is dict else None
        if (
            type(pre) is not list
            or any(type(value) is not int for value in pre)
            or type(key) is not int
            or type(fields) is not list
            or any(type(value) is not int for value in fields)
        ):
            _fail("V94 transition grouping key changed")
        identity = (tuple(pre), key)
        if identity not in grouped:
            grouped[identity] = []
            order.append(identity)
        elif grouped[identity][0]["selected_action"] != selected:
            _fail("V94 grouped action projection changed")
        grouped[identity].append(row)
    return [grouped[key] for key in order]


def _check_candidate(candidate: Any, aligned_rows: list[dict[str, Any]]) -> None:
    _check_generic_id(candidate, "candidate_id", _CANDIDATE_DOMAIN)
    layout = candidate.get("layout")
    if (
        candidate.get("schema")
        != "acfqp.generic_low_label_residual_candidate.v73"
        or type(layout) is not dict
        or candidate.get("source_model_id") != SOURCE_MODEL_ID
        or candidate.get("transformed_observation_count") != len(aligned_rows)
        or candidate.get("transformed_observation_sha256")
        != hashlib.sha256(canonical_json_bytes(aligned_rows)).hexdigest()
        or candidate.get("source_partial_and_residual_model_refit") is not False
        or candidate.get("source_terminal_program_applicability_claimed") is not False
        or candidate.get("planning_authority_present") is not False
        or candidate.get("complete_world_model_claimed") is not False
    ):
        _fail("V94 projected candidate boundary changed")
    width = candidate.get("state_width")
    action_width = candidate.get("action_field_width")
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    assignments = candidate.get("compiled_factor_assignments")
    residual = candidate.get("unknown_residual_target_columns")
    if (
        type(width) is not int
        or type(action_width) is not int
        or state_order != list(range(width))
        or action_order != list(range(action_width))
        or type(assignments) is not list
        or not assignments
        or type(residual) is not list
        or not residual
        or sorted({row.get("target_column") for row in assignments} | set(residual))
        != list(range(width))
    ):
        _fail("V94 projected candidate coordinate coverage changed")


def _check_stopping(acquisition: Mapping[str, Any]) -> None:
    labels = acquisition.get("ground_support_labels")
    issuance = acquisition.get("candidate_issued_at_ground_support_label")
    crossing = acquisition.get("confidence_crossing_ground_support_label")
    epoch = acquisition.get("candidate_epoch")
    odds = acquisition.get("source_meta_prior_odds")
    confidence = acquisition.get("confidence_denominator")
    successes = acquisition.get("post_issuance_exact_prediction_success_count")
    history = acquisition.get("prequential_history")
    if (
        type(labels) is not int
        or type(issuance) is not int
        or type(crossing) is not int
        or type(epoch) is not int
        or type(odds) is not int
        or type(confidence) is not int
        or type(successes) is not int
        or type(history) is not list
        or not 1 <= issuance <= crossing == labels
        or acquisition.get("target_predictive_confirmation_count") != successes
        or successes != crossing - issuance
    ):
        _fail("V94 prequential stopping coordinates changed")
    issued = [
        row
        for row in history
        if type(row) is dict and row.get("candidate_issued") is True
    ]
    if len(issued) != 1 or issued[0].get("ground_support_label") != issuance:
        _fail("V94 candidate issuance history changed")
    threshold = confidence * (epoch + 1) * (epoch + 2)
    if successes == 0:
        if (
            odds < threshold
            or crossing != issuance
            or acquisition.get("source_meta_prior_only_stop_at_issuance") is not True
            or issued[0].get("source_meta_prior_only_crossing") is not True
        ):
            _fail("V94 prior-only stopping arithmetic changed")
    else:
        expected_successes = None
        for count in range(1, successes + 1):
            if (2 ** (count + 1) - 1) * odds >= (count + 1) * threshold:
                expected_successes = count
                break
        if (
            expected_successes != successes
            or acquisition.get("source_meta_prior_only_stop_at_issuance") is not False
        ):
            _fail("V94 predictive stopping arithmetic changed")


def _check_acquisition(
    acquisition: Any,
    *,
    meta_prior: bool,
    expected_seed: int,
) -> None:
    _check_v94_id(
        acquisition,
        "applicability_id",
        (
            domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_ON_ACQUISITION_V94_DOMAIN
            if meta_prior
            else domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_OFF_ACQUISITION_V94_DOMAIN
        ),
    )
    raw_rows = acquisition.get("raw_transition_rows")
    aligned_rows = acquisition.get("aligned_transition_rows")
    catalogue = acquisition.get("action_catalogue")
    raw_groups = _groups(raw_rows)
    aligned_groups = _groups(aligned_rows)
    if (
        acquisition.get("schema")
        != "acfqp.generic_low_label_residual_applicability.v73"
        or acquisition.get("seed") != expected_seed
        or acquisition.get("source_model_id") != SOURCE_MODEL_ID
        or len(raw_groups) != acquisition.get("ground_support_labels")
        or len(aligned_groups) != len(raw_groups)
        or len(aligned_rows) != len(raw_rows)
        or hashlib.sha256(canonical_json_bytes(raw_rows)).hexdigest()
        != acquisition.get("raw_transition_sha256")
        or hashlib.sha256(canonical_json_bytes(aligned_rows)).hexdigest()
        != acquisition.get("aligned_transition_sha256")
        or type(catalogue) is not list
        or hashlib.sha256(canonical_json_bytes(catalogue)).hexdigest()
        != acquisition.get("action_catalogue_sha256")
    ):
        _fail("V94 acquisition observation inventory changed")
    state_order = acquisition.get("source_state_to_target_raw")
    action_order = acquisition.get("source_action_to_target_raw")
    layout = acquisition.get("matched_target_layout")
    if (
        type(layout) is not dict
        or state_order != layout.get("state_canonical_to_raw")
        or action_order != layout.get("action_canonical_to_raw")
        or type(state_order) is not list
        or type(action_order) is not list
    ):
        _fail("V94 acquisition projection inventory changed")
    for raw, aligned in zip(raw_rows, aligned_rows, strict=True):
        if (
            aligned.get("pre_vector")
            != [raw["pre_vector"][index] for index in state_order]
            or aligned.get("post_vector")
            != [raw["post_vector"][index] for index in state_order]
            or aligned.get("selected_action", {}).get("anonymous_fields")
            != [
                raw["selected_action"]["anonymous_fields"][index]
                for index in action_order
            ]
            or aligned.get("selected_action", {}).get("action_key")
            != raw.get("selected_action", {}).get("action_key")
            or aligned.get("legal_action_keys_before")
            != raw.get("legal_action_keys_before")
            or aligned.get("legal_action_keys_after")
            != raw.get("legal_action_keys_after")
            or aligned.get("terminal_acceptance_after")
            is not raw.get("terminal_acceptance_after")
        ):
            _fail("V94 raw-to-aligned observation replay changed")
    if (
        acquisition.get("source_meta_prior_enabled") is not meta_prior
        or acquisition.get("source_meta_prior_odds") != (16 if meta_prior else 1)
        or acquisition.get("witness_blind_depth_stream_used") is not True
        or acquisition.get("terminal_witness_used_to_schedule_queries") is not False
        or acquisition.get("fixed_label_floor_used") is not False
        or acquisition.get("fixed_confirmation_block_used") is not False
        or acquisition.get("source_terminal_program_used_only_as_fallible_action_ordering_heuristic")
        is not True
        or acquisition.get("empirical_source_meta_prior_strength_preregistered_not_universal")
        is not True
        or acquisition.get("residual_applicability_promoted_to_global_fact") is not False
        or acquisition.get("target_episode_outcomes_used") is not False
        or acquisition.get("source_partial_or_residual_model_refit") is not False
        or acquisition.get("proposal_used_as_safety_authority") is not False
        or acquisition.get("complete_world_model_claimed") is not False
    ):
        _fail("V94 acquisition claim boundary changed")
    _check_stopping(acquisition)
    _check_candidate(acquisition.get("projected_target_candidate"), aligned_rows)


def _check_plan(plan: Any, candidate_id: str) -> None:
    if (
        type(plan) is not dict
        or plan.get("schema")
        != "acfqp.generic_joint_successor_version_space_plan.v42"
        or plan.get("joint_successor_version_space_model_id") != SOURCE_MODEL_ID
        or plan.get("target_partial_candidate_id") != candidate_id
        or type(plan.get("initial_action_key")) is not int
        or plan.get("support_feasible_receding_plan_found") is not True
        or plan.get("all_residual_version_spaces_jointly_propagated") is not True
        or plan.get("all_mdl_minimal_terminal_trees_jointly_propagated") is not True
        or plan.get("ground_transition_accessed_during_abstract_search") is not False
        or plan.get("abstract_plan_used_as_safety_authority") is not False
        or plan.get("empirical_version_space_promoted_to_global_exact_dynamics")
        is not False
        or plan.get("complete_world_model_claimed") is not False
    ):
        _fail("V94 abstract plan propagation boundary changed")


def _check_episode(
    episode: Any,
    *,
    acquisition_labels: int,
    candidate_id: str,
    transfer: bool,
) -> None:
    _check_generic_id(episode, "episode_id", _EPISODE_DOMAIN)
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    receipts = episode.get("abstract_plan_receipts")
    incremental = episode.get("incremental_certificate_local_ground_support_labels")
    steps = episode.get("execution_steps")
    actions = episode.get("action_keys")
    tapes = episode.get("outcome_tape_sha256")
    matches = episode.get("execution_action_matches_abstract_proposal")
    if (
        episode.get("schema")
        != "acfqp.generic_preloaded_certificate_receding_episode.v74"
        or episode.get("source_model_id") is not None
        or episode.get("target_candidate_id") != candidate_id
        or episode.get("success") is not True
        or type(failures) is not list
        or type(distinctions) is not list
        or len(failures) != len(distinctions)
        or type(incremental) is not int
        or incremental
        != sum(row.get("ground_support_labels", -1) for row in distinctions)
        or episode.get("preloaded_acquisition_ground_support_labels")
        != acquisition_labels
        or episode.get("total_target_ground_support_labels")
        != acquisition_labels + incremental
        or type(steps) is not int
        or type(actions) is not list
        or type(tapes) is not list
        or len(actions) != len(tapes) or len(actions) != steps
        or type(matches) is not list
        or len(matches) != steps
        or episode.get("execution_action_matches_abstract_proposal_count")
        != sum(value is True for value in matches)
        or any(
            row.get("ground_query_performed_before_failure") is not False
            for row in failures
        )
        or any(
            row.get("query_after_failed_certificate") is not True
            for row in distinctions
        )
        or episode.get("all_incremental_ground_queries_followed_failed_certificates")
        is not True
        or episode.get("preloaded_exact_rows_reused_without_reacquisition") is not True
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or episode.get("model_or_alignment_used_as_safety_authority") is not False
        or episode.get("target_episode_outcomes_used_to_refit_model_or_alignment")
        is not False
        or episode.get("same_exact_engine_implementation_for_transfer_and_strict_arms")
        is not True
        or episode.get("complete_world_model_synthesized") is not False
    ):
        _fail("V94 exact certificate episode or accounting changed")
    if transfer:
        if (
            episode.get("arm") != "LOW_LABEL_RESIDUAL_TRANSFER"
            or episode.get("abstract_model_used_only_for_action_ordering") is not True
            or type(receipts) is not list
            or not receipts
            or episode.get("abstract_plan_success_count") != len(receipts)
        ):
            _fail("V94 transfer abstract-planning evidence changed")
        for receipt in receipts:
            _check_plan(receipt.get("abstract_plan"), candidate_id)
    elif (
        episode.get("arm") != "STRICT_COLD_DIRECT_GROUND"
        or acquisition_labels != 0
        or receipts != []
        or episode.get("abstract_planning_compute_events") != 0
        or episode.get("abstract_model_used_only_for_action_ordering") is not False
        or episode.get("preloaded_transition_support_hit_count") != 0
    ):
        _fail("V94 strict cold-direct control received transfer work")


def _strict_projection(episode: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in episode.items()
        if key not in {"episode_id", "target_candidate_id"}
    }


def _check_ablation(
    ablation: Any,
    acquisition: Mapping[str, Any],
    *,
    expected_seed: int,
) -> tuple[int, int]:
    _check_generic_id(ablation, "ablation_id", _ABLATION_DOMAIN)
    candidate_id = acquisition["projected_target_candidate"]["candidate_id"]
    arms = ablation.get("arms")
    if type(arms) is not dict or set(arms) != {
        "LOW_LABEL_RESIDUAL_TRANSFER",
        "STRICT_COLD_DIRECT_GROUND",
    }:
        _fail("V94 ablation arm inventory changed")
    transfer = arms["LOW_LABEL_RESIDUAL_TRANSFER"]
    strict = arms["STRICT_COLD_DIRECT_GROUND"]
    labels = acquisition["ground_support_labels"]
    _check_episode(
        transfer,
        acquisition_labels=labels,
        candidate_id=candidate_id,
        transfer=True,
    )
    _check_episode(
        strict,
        acquisition_labels=0,
        candidate_id=candidate_id,
        transfer=False,
    )
    transfer_total = transfer["total_target_ground_support_labels"]
    strict_total = strict["total_target_ground_support_labels"]
    if (
        ablation.get("schema")
        != "acfqp.generic_total_label_residual_transfer_ablation.v75"
        or ablation.get("seed") != expected_seed
        or ablation.get("source_model_id") != SOURCE_MODEL_ID
        or ablation.get("target_candidate_id") != candidate_id
        or ablation.get("transfer_total_target_ground_support_labels")
        != transfer_total
        or ablation.get("strict_total_target_ground_support_labels") != strict_total
        or ablation.get("strict_minus_transfer_total_target_labels")
        != strict_total - transfer_total
        or ablation.get("total_target_sample_reduction_observed")
        is not (transfer_total < strict_total)
        or ablation.get("same_target_kernel_seed_episode_and_exact_engine") is not True
        or ablation.get("transfer_arm_applicability_rows_paid_once_and_reused_as_exact_evidence")
        is not True
        or ablation.get("strict_arm_receives_no_transfer_or_free_target_rows") is not True
        or ablation.get("source_terminal_program_used_only_as_fallible_action_ordering_heuristic")
        is not True
        or ablation.get("source_terminal_applicability_claimed") is not False
        or ablation.get("all_actual_source_residual_and_terminal_candidates_propagated_as_heuristics")
        is not True
        or ablation.get("model_or_alignment_used_as_safety_authority") is not False
        or ablation.get("complete_world_model_synthesized") is not False
        or ablation.get("official_execution_allowed") is not False
        or ablation.get("official_scalar_cost") is not None
        or ablation.get("official_N_break_even") is not None
        or ablation.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or ablation.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V94 total-label ablation boundary changed")
    return transfer_total, strict_total


def verify_total_label_meta_prior_campaign_bytes_v94(raw: bytes) -> bytes:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V94 campaign bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V94 campaign is not canonical")
    _check_v94_id(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_CAMPAIGN_V94_DOMAIN,
    )
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("source_model_id") != SOURCE_MODEL_ID
        or document.get("source_acceptance_id") != SOURCE_ACCEPTANCE_ID
        or document.get("source_acceptance_verification_id")
        != SOURCE_ACCEPTANCE_VERIFICATION_ID
        or document.get("preserved_v93_failed_campaign_id")
        != V93_FAILED_CAMPAIGN_ID
        or document.get("preserved_v93_failed_verification_id")
        != V93_FAILED_VERIFICATION_ID
        or document.get("v93_failure_preserved_without_rerun") is not True
        or document.get("fresh_target_identities_executed_without_selection") is not True
        or document.get("source_meta_prior_odds") != 16
        or document.get("sample_tax_reduction_verified_on_registered_target_workload")
        is not True
        or document.get("sample_tax_reduction_generalized_beyond_registered_workload")
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
        _fail("V94 campaign identity or claim boundary changed")
    occurrences = document.get("target_occurrences")
    if type(occurrences) is not list or [row.get("target_seed") for row in occurrences] != [
        971101,
        971102,
    ]:
        _fail("V94 registered occurrence inventory changed")
    meta_totals: list[int] = []
    no_prior_totals: list[int] = []
    strict_totals: list[int] = []
    meta_acquisition_labels = 0
    no_prior_acquisition_labels = 0
    meta_incremental_labels = 0
    no_prior_incremental_labels = 0
    for occurrence in occurrences:
        _check_v94_id(
            occurrence,
            "occurrence_id",
            domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_OCCURRENCE_V94_DOMAIN,
        )
        seed = occurrence["target_seed"]
        if (
            occurrence.get("status")
            != "TARGET_META_PRIOR_NO_PRIOR_AND_DIRECT_EPISODES_COMPLETED"
            or occurrence.get("failure_reason") is not None
            or occurrence.get("source_model_id") != SOURCE_MODEL_ID
            or occurrence.get("same_synthesizer_stop_rule_target_kernel_seed_episode_and_exact_engine")
            is not True
            or occurrence.get("only_source_meta_prior_odds_differs_between_acquisition_arms")
            is not True
            or occurrence.get("source_meta_prior_strength_used_as_safety_authority")
            is not False
            or occurrence.get("official_execution_allowed") is not False
        ):
            _fail("V94 occurrence boundary changed")
        meta_acquisition = occurrence["meta_prior_acquisition"]
        no_prior_acquisition = occurrence["no_prior_acquisition"]
        _check_acquisition(meta_acquisition, meta_prior=True, expected_seed=seed)
        _check_acquisition(no_prior_acquisition, meta_prior=False, expected_seed=seed)
        meta_total, strict_total = _check_ablation(
            occurrence["meta_prior_total_label_ablation"],
            meta_acquisition,
            expected_seed=seed,
        )
        no_prior_total, repeated_strict_total = _check_ablation(
            occurrence["no_prior_total_label_ablation"],
            no_prior_acquisition,
            expected_seed=seed,
        )
        meta_strict = occurrence["meta_prior_total_label_ablation"]["arms"][
            "STRICT_COLD_DIRECT_GROUND"
        ]
        no_prior_strict = occurrence["no_prior_total_label_ablation"]["arms"][
            "STRICT_COLD_DIRECT_GROUND"
        ]
        if (
            repeated_strict_total != strict_total
            or _strict_projection(meta_strict) != _strict_projection(no_prior_strict)
        ):
            _fail("V94 repeated cold-direct baseline changed across arms")
        ood = occurrence.get("strict_incompatible_model_ood_control")
        if (
            type(ood) is not dict
            or ood.get("status")
            != "INCOMPATIBLE_MODEL_REJECTED_BEFORE_TARGET_OBSERVATION"
            or ood.get("target_ground_support_labels_consumed") != 0
            or ood.get("target_episode_executed") is not False
        ):
            _fail("V94 strict OOD no-transfer control changed")
        meta_totals.append(meta_total)
        no_prior_totals.append(no_prior_total)
        strict_totals.append(strict_total)
        meta_acquisition_labels += meta_acquisition["ground_support_labels"]
        no_prior_acquisition_labels += no_prior_acquisition["ground_support_labels"]
        meta_incremental_labels += (
            occurrence["meta_prior_total_label_ablation"]["arms"][
                "LOW_LABEL_RESIDUAL_TRANSFER"
            ]["incremental_certificate_local_ground_support_labels"]
        )
        no_prior_incremental_labels += (
            occurrence["no_prior_total_label_ablation"]["arms"][
                "LOW_LABEL_RESIDUAL_TRANSFER"
            ]["incremental_certificate_local_ground_support_labels"]
        )
    accounting = document.get("accounting")
    gate = document.get("registered_gate")
    if (
        meta_totals != [7, 11]
        or no_prior_totals != [12, 12]
        or strict_totals != [13, 20]
        or meta_acquisition_labels != 3
        or no_prior_acquisition_labels != 13
        or meta_incremental_labels != 15
        or no_prior_incremental_labels != 11
        or accounting.get("meta_prior_target_acquisition_labels") != 3
        or accounting.get("no_prior_target_acquisition_labels") != 13
        or accounting.get("meta_prior_incremental_certificate_labels") != 15
        or accounting.get("no_prior_incremental_certificate_labels") != 11
        or accounting.get("meta_prior_total_target_labels") != sum(meta_totals) != 18
        or accounting.get("no_prior_total_target_labels") != sum(no_prior_totals) != 24
        or accounting.get("strict_cold_direct_labels") != sum(strict_totals) != 33
        or accounting.get("strict_minus_meta_prior_total_target_labels") != 15
        or accounting.get("no_prior_minus_meta_prior_total_target_labels") != 6
        or accounting.get("source_target_labels_execution_derivation_certificate_and_planning_compute_separate")
        is not True
        or accounting.get("scalar_cost_aggregation_performed") is not False
        or type(gate) is not dict
        or gate.get("passed") is not True
        or gate.get("completed_target_occurrence_count") != 2
        or gate.get("matched_same_synthesizer_prior_on_off_acquisition_clean")
        is not True
        or gate.get("certificate_failure_only_ground_discipline_clean") is not True
        or gate.get("multi_step_abstract_proposal_primary_on_every_target") is not True
        or gate.get("all_source_version_space_candidates_propagated_as_heuristics")
        is not True
        or gate.get("strict_incompatible_model_no_transfer_clean") is not True
        or gate.get("meta_prior_total_labels_noninferior_to_direct_on_every_target")
        is not True
        or gate.get("meta_prior_total_labels_strictly_better_than_direct_in_aggregate")
        is not True
        or gate.get("meta_prior_total_labels_strictly_better_than_no_prior_on_every_target_and_aggregate")
        is not True
    ):
        _fail("V94 registered Gate or separated accounting changed")
    payload = {
        "schema": "acfqp.total_label_meta_prior_verification.v94",
        "campaign_id": CAMPAIGN_ID,
        "source_model_id": SOURCE_MODEL_ID,
        "v93_failed_campaign_id": V93_FAILED_CAMPAIGN_ID,
        "campaign_occurrence_acquisition_candidate_ablation_episode_content_ids_verified": True,
        "raw_to_aligned_target_observations_independently_replayed": True,
        "matched_same_synthesizer_prior_on_off_stopping_arithmetic_independently_replayed": True,
        "source_meta_prior_only_stop_with_zero_target_predictive_confirmations_observed": True,
        "prior_strength_is_preregistered_empirical_hyperparameter_not_universal_authority": True,
        "acquisition_rows_paid_once_and_reused_as_exact_certificate_evidence_verified": True,
        "certificate_failure_before_query_and_local_distinction_accounting_verified": True,
        "all_actual_source_candidates_propagated_only_as_action_ordering_heuristics": True,
        "strict_cold_direct_received_no_free_target_rows_or_abstract_planning": True,
        "strict_incompatible_schema_rejected_before_target_observation": True,
        "meta_prior_total_target_labels": sum(meta_totals),
        "no_prior_total_target_labels": sum(no_prior_totals),
        "strict_cold_direct_target_labels": sum(strict_totals),
        "strict_minus_meta_prior_total_target_labels": 15,
        "no_prior_minus_meta_prior_total_target_labels": 6,
        "sample_tax_reduction_verified_on_registered_target_workload": True,
        "sample_tax_reduction_generalized_beyond_registered_workload": False,
        "typed_result": "REGISTERED_TOTAL_TARGET_SAMPLE_TAX_REDUCTION_VERIFIED_EMPIRICAL_META_PRIOR_NOT_CROSS_DOMAIN_GENERALIZED",
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
        "verification_id": domains.extension_content_id_v94(
            domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_VERIFICATION_V94_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V94 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "verify_total_label_meta_prior_campaign_bytes_v94",
)
