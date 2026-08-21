"""Producer-free verification of the frozen, failed V93 campaign."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v93 as domains
from acfqp.generic_relational_terminal_program_independent_replay_v32 import (
    reconstruct_relational_terminal_program_v32,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "1b9b2fb6a1a837428c40d7d4b42546d1bed75fb406f53a5d84af0c69d25b891e"
CAMPAIGN_BYTE_COUNT = 222_761
CAMPAIGN_SHA256 = "21e9c700406d0a9bd50650adb2fd5a8f553c2b4566f63a5d5523b911baa4879f"
SOURCE_MODEL_ID = "eb79346ce607c99960670f36aa995033c30be67a9322b4620fff7b29bb4eecd7"
V92_FAILED_CAMPAIGN_ID = "97dd235a71f67a79bc9c265f3e45c993773f92d5f6463023c940593a965fb335"
V92_FAILED_VERIFICATION_ID = "eded5ff6ce0d8b87baebc7d83b77fecec8e511c6dd06e07a4bae85a2c54bc388"
VERIFICATION_ID = (
    "841f791d85629fb9317f0a05a02a143ede1df5de340d9495ad6e0c85c213482c"
)
EXPECTED_CANONICAL_BYTE_COUNT = 1_436
EXPECTED_CANONICAL_SHA256 = (
    "edb59dcd9a09ce6e8f7f00690b97481cc8b057467c7ae67e83d73bbab86c6db9"
)


class ConstructionK7TerminalOverlayTargetIndependentVerifierV93Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TerminalOverlayTargetIndependentVerifierV93Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _check_v93_id(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V93 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v93(domain, payload) != document.get(key):
        _fail(f"V93 {key} content identity changed")


def _check_generic_id(document: Any, key: str, domain: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V93 {key} generic document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if _generic_id(domain, payload) != document.get(key):
        _fail(f"V93 {key} generic content identity changed")


def _groups(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped: dict[tuple[tuple[int, ...], int], list[dict[str, Any]]] = {}
    order = []
    for row in rows:
        if type(row) is not dict:
            _fail("V93 raw transition row type changed")
        pre = row.get("pre_vector")
        selected = row.get("selected_action")
        key = selected.get("action_key") if type(selected) is dict else None
        if type(pre) is not list or type(key) is not int:
            _fail("V93 raw transition grouping key changed")
        group_key = (tuple(pre), key)
        if group_key not in grouped:
            grouped[group_key] = []
            order.append(group_key)
        grouped[group_key].append(row)
    return [grouped[key] for key in order]


def _label(row: Mapping[str, Any]) -> str:
    legal = row.get("legal_action_keys_after")
    terminal = row.get("terminal_acceptance_after")
    if type(legal) is not list:
        _fail("V93 terminal label evidence changed")
    if legal:
        if terminal is not None:
            _fail("V93 active row carried a terminal label")
        return "ACTIVE"
    if terminal is True:
        return "ACCEPT"
    if terminal is False:
        return "REJECT"
    _fail("V93 terminal row omitted its acceptance label")


def _evaluate(tree: Mapping[str, Any], state: list[int]) -> tuple[str, int]:
    cursor = tree
    while cursor.get("kind") == "RELATION":
        opcode = cursor.get("opcode")
        left = cursor.get("left_column")
        right = cursor.get("right_column")
        if (
            opcode not in ("EQ", "LT", "LE", "GT", "GE")
            or type(left) is not int
            or type(right) is not int
            or not 0 <= left < len(state)
            or not 0 <= right < len(state)
        ):
            _fail("V93 terminal decision relation changed")
        if opcode == "EQ":
            result = state[left] == state[right]
        elif opcode == "LT":
            result = state[left] < state[right]
        elif opcode == "LE":
            result = state[left] <= state[right]
        elif opcode == "GT":
            result = state[left] > state[right]
        else:
            result = state[left] >= state[right]
        cursor = cursor.get("when_true" if result else "when_false")
        if type(cursor) is not dict:
            _fail("V93 terminal decision branch changed")
    if (
        cursor.get("kind") != "LEAF"
        or cursor.get("terminal_class") not in ("ACTIVE", "ACCEPT", "REJECT")
        or type(cursor.get("status_token")) is not int
    ):
        _fail("V93 terminal decision leaf changed")
    return cursor["terminal_class"], cursor["status_token"]


def _minimal_frontier(program: Mapping[str, Any]) -> list[dict[str, Any]]:
    frontier = program.get("decision_tree_candidate_frontier")
    if type(frontier) is not list or not frontier:
        _fail("V93 reconstructed terminal frontier changed")
    minimum_nodes = min(row.get("decision_tree_node_count", -1) for row in frontier)
    candidates = [
        row for row in frontier if row.get("decision_tree_node_count") == minimum_nodes
    ]
    minimum_bytes = min(row.get("decision_tree_byte_count", -1) for row in candidates)
    return [
        row for row in candidates if row.get("decision_tree_byte_count") == minimum_bytes
    ]


def _check_terminal_overlay(
    joint: Mapping[str, Any], aligned_groups: list[list[dict[str, Any]]]
) -> None:
    overlay = joint.get("terminal_overlay")
    _check_generic_id(
        overlay,
        "terminal_overlay_id",
        b"acfqp:generic-prequential-terminal-overlay:v69\x00",
    )
    if (
        overlay.get("source_model_id") != SOURCE_MODEL_ID
        or overlay.get("physical_query_group_count") != len(aligned_groups)
        or overlay.get("joint_acquisition_stop_ground_support_labels")
        != len(aligned_groups)
        or overlay.get("prequential_confidence_stop_reached") is not True
        or overlay.get("fixed_confirmation_block_used") is not False
        or overlay.get("heldout_prediction_claimed") is not False
        or overlay.get("target_episode_outcomes_used") is not False
        or overlay.get("target_terminal_overlay_used_as_safety_authority")
        is not False
        or overlay.get("complete_world_model_claimed") is not False
    ):
        _fail("V93 terminal overlay boundary changed")
    issuance = overlay.get("candidate_issued_at_physical_ground_support_label")
    crossing = overlay.get("candidate_confidence_crossing_ground_support_label")
    epoch = overlay.get("candidate_epoch")
    confidence = overlay.get("confidence_denominator")
    if (
        type(issuance) is not int
        or type(crossing) is not int
        or type(epoch) is not int
        or type(confidence) is not int
        or not 1 <= issuance < crossing <= len(aligned_groups)
    ):
        _fail("V93 terminal overlay stopping coordinates changed")
    prefix = [row for group in aligned_groups[:issuance] for row in group]
    width = len(prefix[0]["post_vector"])
    layout = joint["alignment"]["matched_target_layout"]
    evidence = {
        "layout": {
            "state_canonical_to_raw": list(range(width)),
            "state_structural_colors": layout["state_structural_colors"],
        },
        "raw_transition_rows": prefix,
        "unknown_residual_target_columns": [
            overlay["selected_terminal_program"]["status_target_column"]
        ],
    }
    reconstructed = reconstruct_relational_terminal_program_v32(
        evidence,
        maximum_program_candidates=overlay["maximum_program_candidates"],
    )
    if (
        reconstructed != overlay.get("selected_terminal_program")
        or reconstructed.get("terminal_program_id")
        != overlay.get("selected_terminal_program_id")
        or _minimal_frontier(reconstructed)
        != overlay.get("selected_mdl_minimal_terminal_frontier")
    ):
        _fail("V93 terminal program was not independently reconstructed")
    status_column = reconstructed["status_target_column"]
    frontier = _minimal_frontier(reconstructed)
    for group in aligned_groups[issuance:]:
        for row in group:
            expected = (_label(row), row["post_vector"][status_column])
            if any(
                _evaluate(candidate["decision_tree"], row["post_vector"])
                != expected
                for candidate in frontier
            ):
                _fail("V93 selected terminal frontier missed a later prefix row")
    successes = len(aligned_groups) - issuance
    if overlay.get("post_issuance_exact_prediction_success_count") != successes:
        _fail("V93 terminal prequential success count changed")
    threshold = confidence * (epoch + 1) * (epoch + 2)
    expected_crossing = None
    for success_count in range(1, successes + 1):
        if (2 ** (success_count + 1) - 1) >= (success_count + 1) * threshold:
            expected_crossing = issuance + success_count
            break
    if expected_crossing != crossing:
        _fail("V93 terminal confidence crossing was not independently replayed")


def _check_episode(episode: Any, *, derived: bool) -> None:
    _check_generic_id(
        episode,
        "episode_id",
        b"acfqp:generic-certificate-local-receding-episode:v71\x00",
    )
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    if (
        episode.get("success") is not True
        or type(failures) is not list
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
        or episode.get("all_ground_queries_followed_failed_certificates") is not True
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or episode.get(
            "model_alignment_or_terminal_overlay_used_as_safety_authority"
        )
        is not False
    ):
        _fail("V93 certificate-local episode accounting changed")
    receipts = episode.get("abstract_plan_receipts")
    if derived:
        if type(receipts) is not list or not receipts:
            _fail("V93 derived episode omitted abstract plans")
        for receipt in receipts:
            plan = receipt.get("abstract_plan")
            _check_generic_id(
                plan,
                "plan_id",
                b"acfqp:generic-terminal-overlay-version-space-plan:v69\x00",
            )
            if (
                plan.get("all_source_residual_version_spaces_jointly_propagated")
                is not True
                or plan.get(
                    "all_target_mdl_minimal_terminal_trees_jointly_propagated"
                )
                is not True
                or plan.get(
                    "target_episode_ground_transition_accessed_during_abstract_search"
                )
                is not False
                or plan.get("abstract_plan_used_as_safety_authority") is not False
            ):
                _fail("V93 abstract plan boundary changed")
    elif receipts != [] or episode.get("abstract_planning_compute_events") != 0:
        _fail("V93 strict episode acquired abstract planning work")


def _check_joint_acquisition(joint: Any) -> None:
    _check_v93_id(
        joint,
        "joint_acquisition_id",
        domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_JOINT_ACQUISITION_V93_DOMAIN,
    )
    raw_rows = joint.get("raw_transition_rows")
    aligned_rows = joint.get("aligned_transition_rows")
    catalogue = joint.get("action_catalogue")
    if (
        type(raw_rows) is not list
        or not raw_rows
        or type(aligned_rows) is not list
        or len(aligned_rows) != len(raw_rows)
        or type(catalogue) is not list
        or not catalogue
        or joint.get("raw_transition_row_count") != len(raw_rows)
        or joint.get("aligned_transition_row_count") != len(aligned_rows)
        or hashlib.sha256(canonical_json_bytes(raw_rows)).hexdigest()
        != joint.get("raw_transition_sha256")
        or hashlib.sha256(canonical_json_bytes(aligned_rows)).hexdigest()
        != joint.get("aligned_transition_sha256")
        or hashlib.sha256(canonical_json_bytes(catalogue)).hexdigest()
        != joint.get("action_catalogue_sha256")
    ):
        _fail("V93 embedded raw/aligned observation inventory changed")
    raw_groups = _groups(raw_rows)
    aligned_groups = _groups(aligned_rows)
    if (
        len(raw_groups) != len(aligned_groups)
        or len(raw_groups) != joint.get("joint_stop_ground_support_labels")
        or joint.get("partial_factor_stop_ground_support_labels")
        + joint.get("terminal_calibration_incremental_ground_support_labels")
        != len(raw_groups)
    ):
        _fail("V93 physical query-group accounting changed")
    partial = joint.get("partial_acquisition")
    _check_v93_id(
        partial,
        "acquisition_id",
        domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_PARTIAL_ACQUISITION_V93_DOMAIN,
    )
    candidate = partial.get("candidate")
    _check_v93_id(
        candidate,
        "candidate_id",
        domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_PARTIAL_ACQUISITION_V93_DOMAIN,
    )
    partial_groups = raw_groups[: joint["partial_factor_stop_ground_support_labels"]]
    partial_rows = [row for group in partial_groups for row in group]
    if (
        partial.get("ground_support_labels") != len(partial_groups)
        or partial.get("raw_transition_count") != len(partial_rows)
        or hashlib.sha256(canonical_json_bytes(partial_rows)).hexdigest()
        != partial.get("raw_transition_sha256")
        or joint.get("terminal_witness_used_to_schedule_queries") is not False
        or joint.get("fixed_label_floor_used") is not False
        or joint.get("fixed_confirmation_block_used") is not False
        or joint.get("target_episode_outcomes_used") is not False
        or joint.get("proposal_used_as_safety_authority") is not False
    ):
        _fail("V93 partial/joint acquisition boundary changed")
    alignment = joint.get("alignment")
    _check_generic_id(
        alignment,
        "alignment_id",
        b"acfqp:generic-residual-only-target-alignment:v69\x00",
    )
    state_order = alignment.get("source_state_to_target_raw")
    action_order = alignment.get("source_action_to_target_raw")
    if type(state_order) is not list or type(action_order) is not list:
        _fail("V93 coordinate projection changed")
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
            or aligned.get("legal_action_keys_before")
            != raw.get("legal_action_keys_before")
            or aligned.get("legal_action_keys_after")
            != raw.get("legal_action_keys_after")
            or aligned.get("terminal_acceptance_after")
            is not raw.get("terminal_acceptance_after")
        ):
            _fail("V93 raw-to-aligned transition replay changed")
    _check_terminal_overlay(joint, aligned_groups)


def verify_terminal_overlay_target_campaign_bytes_v93(raw: bytes) -> bytes:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V93 campaign bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V93 campaign is not canonical")
    _check_v93_id(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_CAMPAIGN_V93_DOMAIN,
    )
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("source_model_id") != SOURCE_MODEL_ID
        or document.get("preserved_v92_failed_campaign_id")
        != V92_FAILED_CAMPAIGN_ID
        or document.get("preserved_v92_failed_verification_id")
        != V92_FAILED_VERIFICATION_ID
        or document.get("v92_failure_preserved_without_rerun") is not True
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
        or document.get("complete_world_model_synthesized") is not False
    ):
        _fail("V93 campaign identity or claim boundary changed")
    occurrences = document.get("target_occurrences")
    if type(occurrences) is not list or [row.get("target_seed") for row in occurrences] != [
        961101,
        961102,
    ]:
        _fail("V93 fresh occurrence inventory changed")
    ablations = []
    for occurrence in occurrences:
        _check_v93_id(
            occurrence,
            "occurrence_id",
            domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_OCCURRENCE_V93_DOMAIN,
        )
        if occurrence.get("status") != "TARGET_TERMINAL_OVERLAY_EPISODES_COMPLETED":
            _fail("V93 completed occurrence status changed")
        _check_joint_acquisition(occurrence.get("target_joint_acquisition"))
        ablation = occurrence.get("matched_ablation")
        _check_generic_id(
            ablation,
            "ablation_id",
            b"acfqp:generic-terminal-overlay-target-ablation:v72\x00",
        )
        arms = ablation.get("arms")
        if type(arms) is not dict or set(arms) != {
            "SOURCE_RESIDUAL_PLUS_TARGET_TERMINAL_OVERLAY",
            "STRICT_DIRECT_GROUND",
        }:
            _fail("V93 matched arm inventory changed")
        _check_episode(
            arms["SOURCE_RESIDUAL_PLUS_TARGET_TERMINAL_OVERLAY"], derived=True
        )
        _check_episode(arms["STRICT_DIRECT_GROUND"], derived=False)
        ablations.append(ablation)
    derived = [
        row["arms"]["SOURCE_RESIDUAL_PLUS_TARGET_TERMINAL_OVERLAY"]
        for row in ablations
    ]
    strict = [row["arms"]["STRICT_DIRECT_GROUND"] for row in ablations]
    derived_labels = sum(
        row["target_certificate_local_ground_support_labels"] for row in derived
    )
    strict_labels = sum(
        row["target_certificate_local_ground_support_labels"] for row in strict
    )
    accounting = document.get("accounting")
    gate = document.get("registered_gate")
    if (
        derived_labels != 13
        or strict_labels != 14
        or accounting.get("derived_target_certificate_local_labels") != 13
        or accounting.get("strict_target_certificate_local_labels") != 14
        or accounting.get("target_joint_acquisition_labels") != 38
        or gate.get("passed") is not False
        or gate.get("completed_target_occurrence_count") != 2
        or gate.get("every_target_certificate_label_reduction_observed") is not False
        or gate.get("aggregate_target_certificate_label_reduction_observed") is not False
        or [row["actual_target_sample_reduction_observed"] for row in ablations]
        != [True, False]
    ):
        _fail("V93 frozen failed Gate or accounting changed")
    payload = {
        "schema": "acfqp.terminal_overlay_target_verification.v93",
        "campaign_id": CAMPAIGN_ID,
        "source_model_id": SOURCE_MODEL_ID,
        "v92_failed_campaign_id": V92_FAILED_CAMPAIGN_ID,
        "campaign_occurrence_joint_acquisition_ablation_episode_plan_content_ids_verified": True,
        "raw_and_aligned_joint_acquisition_rows_independently_replayed": True,
        "target_terminal_program_independently_reconstructed_from_prequential_prefix": True,
        "terminal_confidence_crossing_independently_replayed": True,
        "certificate_failure_before_query_and_local_distinction_accounting_verified": True,
        "all_actual_residual_and_target_terminal_candidates_propagated": True,
        "frozen_every_target_reduction_failure_preserved": True,
        "aggregate_certificate_only_label_difference": strict_labels - derived_labels,
        "target_joint_acquisition_labels": accounting[
            "target_joint_acquisition_labels"
        ],
        "total_target_label_tax_including_acquisition_beats_strict_direct": (
            accounting["target_joint_acquisition_labels"] + derived_labels
            < strict_labels
        ),
        "sample_tax_problem_resolved": False,
        "typed_result": "FAILED_REGISTERED_EVERY_TARGET_REDUCTION_VERIFIED_TOTAL_TARGET_SAMPLE_TAX_UNRESOLVED",
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
        "verification_id": domains.extension_content_id_v93(
            domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_VERIFICATION_V93_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V93 verification changed")
    return result


__all__ = ("VERIFICATION_ID", "verify_terminal_overlay_target_campaign_bytes_v93")
