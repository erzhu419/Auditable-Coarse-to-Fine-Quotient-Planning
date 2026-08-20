"""Producer-free reconstruction of every V69 relational terminal program."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v69 as domains
from acfqp.generic_relational_terminal_program_independent_replay_v32 import (
    GenericRelationalTerminalProgramIndependentReplayV32Error,
    verify_source_complete_relational_program_v32,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


VERIFICATION_ID = "3c67ad21d01897448aa5a60c7fe4d802f2b1f477761451dc801e1b270c31d3ed"
EXPECTED_CANONICAL_BYTE_COUNT = 979
EXPECTED_CANONICAL_SHA256 = "bd06095afebe4f678a2dfbf127bbfd10eddd5f53ee903bec3f04ba425c4c5a03"
_PREREGISTRATION_ID = "056f3a4caf03c2bba595af958b67e2f1d124766c767eabea24e9c3ac4ff916a5"
_V68_CAMPAIGN_ID = "607e55ff4f745dee3f1ddf8fd8cccb76ffc1bf4f25f6df143a9b61a08c50a944"
_V68_VERIFICATION_ID = "6581428db574418a770777f5df03afde2b9299348b3b06fe997d321a909acb87"
_SOURCE_DOMAIN = b"acfqp:source-complete-terminal-program-evidence:v31\x00"
_EPISODE_DOMAIN = b"acfqp:generic-source-complete-relational-world-model:v31\x00"
_MULTI_DOMAIN = b"acfqp:generic-multi-residual-acquisition:v24\x00"
_BATCH_DOMAIN = b"acfqp:generic-batch-exact-multi-residual-support:v27\x00"
_EXPECTED_SEEDS = {
    "BALANCED_BATCH_REFINEMENT": {701_101, 701_102},
    "COUPLED_EXCHANGE": {702_101, 702_102},
    "MAINTENANCE_CASCADE": {703_101, 703_102},
}


class ConstructionK7SourceCompleteRelationalIndependentVerifierV69Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SourceCompleteRelationalIndependentVerifierV69Error(message)


def _id(domain: str, document: dict[str, Any], key: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v69(domain, payload) != document.get(key):
        _fail(f"V69 {key} changed")


def _hash(document: Any, key: str, prefix: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V69 embedded {key} document changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != hashlib.sha256(
        prefix + canonical_json_bytes(payload)
    ).hexdigest():
        _fail(f"V69 embedded {key} changed")


def _certificate_ledger(episode: dict[str, Any]) -> dict[str, int]:
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    raw_rows = episode.get("raw_local_transition_rows")
    if not all(type(value) is list for value in (failures, distinctions, raw_rows)):
        _fail("V69 V30 ledger inventory changed")
    if len(failures) != len(distinctions):
        _fail("V69 certificate/distinction count changed")
    labels = 0
    transitions = 0
    flattened = []
    contexts = set()
    for index, (failure, distinction) in enumerate(
        zip(failures, distinctions, strict=True)
    ):
        if (
            type(failure) is not dict
            or type(distinction) is not dict
            or failure.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("failure_index") != index
            or distinction.get("raw_state") != failure.get("raw_state")
            or distinction.get("ground_support_labels") != 1
            or distinction.get("query_after_failed_certificate") is not True
        ):
            _fail("V69 certificate-before-query order changed")
        labels += 1
        if distinction.get("distinction_kind") == "QUERY_LOCAL_LEGAL_ACTION_SET":
            if failure.get("failure_kind") != "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT":
                _fail("V69 legality certificate changed")
        elif distinction.get("distinction_kind") == "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT":
            rows = distinction.get("raw_transition_rows")
            context = (
                tuple(distinction.get("raw_state", ())),
                distinction.get("action_key"),
            )
            if (
                context in contexts
                or type(rows) is not list
                or not rows
                or distinction.get("action_key") != failure.get("action_key")
            ):
                _fail("V69 residual query receipt changed")
            contexts.add(context)
            transitions += 1
            for row in rows:
                action = row.get("selected_action") if type(row) is dict else None
                if (
                    type(action) is not dict
                    or row.get("pre_vector") != distinction.get("raw_state")
                    or action.get("action_key") != distinction.get("action_key")
                ):
                    _fail("V69 transition/query join changed")
            flattened.extend(rows)
        else:
            _fail("V69 distinction kind changed")
    if (
        flattened != raw_rows
        or episode.get("local_ground_support_labels") != labels
        or episode.get("queried_state_action_count") != transitions
    ):
        _fail("V69 query-local accounting changed")
    return {"labels": labels, "transitions": transitions, "rows": len(raw_rows)}


def _source_complete_episode(
    envelope: Any, family: str, seed: int, arm: str
) -> dict[str, int]:
    if type(envelope) is not dict:
        _fail("V69 source-complete envelope changed")
    _hash(envelope, "source_complete_episode_id", _EPISODE_DOMAIN)
    episode = envelope.get("predecessor_v30_episode")
    evidence = envelope.get("terminal_program_source_evidence")
    if type(episode) is not dict or type(evidence) is not dict:
        _fail("V69 envelope content changed")
    _hash(evidence, "source_evidence_id", _SOURCE_DOMAIN)
    common = evidence.get("common_partial_raw_transition_rows")
    local = evidence.get("query_local_raw_transition_rows")
    all_rows = evidence.get("raw_transition_rows")
    if (
        evidence.get("schema")
        != "acfqp.source_complete_terminal_program_evidence.v31"
        or type(common) is not list
        or not common
        or type(local) is not list
        or type(all_rows) is not list
        or all_rows != [*common, *local]
        or evidence.get("common_partial_row_count") != len(common)
        or evidence.get("query_local_row_count") != len(local)
        or evidence.get("all_v28_source_rows_retained") is not True
        or envelope.get("source_evidence_id") != evidence["source_evidence_id"]
        or envelope.get("terminal_program_id")
        != episode.get("final_relational_terminal_program", {}).get(
            "terminal_program_id"
        )
        or envelope.get("all_v28_source_rows_retained") is not True
        or envelope.get("producer_free_terminal_program_reconstruction_enabled")
        is not True
        or envelope.get("planning_behavior_changed_from_v30") is not False
        or envelope.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or envelope.get("relational_abstract_plan_used_as_safety_authority")
        is not False
        or envelope.get("complete_world_model_synthesized") is not False
    ):
        _fail("V69 source-complete evidence join changed")
    source = {
        "layout": evidence.get("layout"),
        "unknown_residual_target_columns": evidence.get(
            "unknown_residual_target_columns"
        ),
        "raw_transition_rows": all_rows,
    }
    try:
        replay = verify_source_complete_relational_program_v32(
            source, episode.get("final_relational_terminal_program")
        )
    except GenericRelationalTerminalProgramIndependentReplayV32Error as error:
        _fail(f"V69 independent terminal reconstruction rejected evidence: {error}")
    if (
        replay.get("terminal_program_id") != envelope["terminal_program_id"]
        or replay.get("raw_transition_row_count") != len(all_rows)
        or replay.get("decision_tree_frontier_rederived") is not True
        or replay.get("producer_imported") is not False
        or replay.get("v28_imported") is not False
        or replay.get("v30_imported") is not False
    ):
        _fail("V69 independent terminal reconstruction changed")
    ledger = _certificate_ledger(episode)
    if local != episode["raw_local_transition_rows"]:
        _fail("V69 retained query-local rows changed")
    multi = episode.get("final_multi_residual_acquisition")
    batch = episode.get("final_batch_exact_residual_support")
    _hash(multi, "multi_residual_acquisition_id", _MULTI_DOMAIN)
    _hash(batch, "batch_exact_multi_residual_id", _BATCH_DOMAIN)
    activations = episode.get("relational_world_model_activations")
    if (
        episode.get("schema")
        != "acfqp.generic_relational_world_model_certificate_episode.v30"
        or episode.get("family") != family
        or episode.get("seed") != seed
        or episode.get("episode_index") != 0
        or episode.get("arm") != arm
        or type(activations) is not list
        or episode.get("success") is not True
        or episode.get("all_ground_queries_followed_failed_certificates") is not True
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or episode.get("relational_abstract_plan_used_as_safety_authority")
        is not False
        or episode.get("complete_world_model_synthesized") is not False
        or len(episode.get("action_keys", [])) != episode.get("execution_steps")
        or len(episode.get("outcome_tape_sha256", []))
        != episode.get("execution_steps")
    ):
        _fail("V69 predecessor episode claims changed")
    return {
        "labels": ledger["labels"],
        "steps": episode["execution_steps"],
        "partial_compute": episode["partial_planning_compute_events"],
        "abstract_compute": episode[
            "relational_abstract_support_branch_evaluations"
        ],
        "synthesis": episode["relational_world_model_synthesis_attempt_count"],
        "successes": episode["relational_abstract_plan_success_count"],
        "active": int(bool(activations)),
        "retained_rows": len(all_rows),
    }


def _occurrence(row: Any) -> dict[str, Any]:
    if type(row) is not dict:
        _fail("V69 occurrence changed")
    _id(
        domains.CONSTRUCTION_K7_SOURCE_COMPLETE_RELATIONAL_OCCURRENCE_V69_DOMAIN,
        row,
        "occurrence_id",
    )
    family, seed = row.get("family"), row.get("seed")
    if family not in _EXPECTED_SEEDS or seed not in _EXPECTED_SEEDS[family]:
        _fail("V69 occurrence identity changed")
    prior = _source_complete_episode(
        row.get("prior_episode"), family, seed, "RESIDUAL_FACTOR_PRIOR_ON"
    )
    strict = _source_complete_episode(
        row.get("strict_episode"), family, seed, "STRICT_NO_RESIDUAL_FACTOR_PRIOR"
    )
    if (
        row["prior_episode"]["predecessor_v30_episode"]["partial_candidate_id"]
        != row["strict_episode"]["predecessor_v30_episode"]["partial_candidate_id"]
        or type(row.get("common_partial_ground_support_labels")) is not int
        or row.get("matched_environment_seed_episode_partial_candidate_and_observations")
        is not True
        or row.get("only_switched_variable")
        != "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH"
        or row.get("all_terminal_program_source_rows_retained") is not True
        or row.get("query_local_overlay_only_safety_authority") is not True
    ):
        _fail("V69 matched occurrence join changed")
    return {
        "family": family,
        "partial": row["common_partial_ground_support_labels"],
        "prior": prior,
        "strict": strict,
    }


def verify_source_complete_relational_campaign_bytes_v69(raw: bytes) -> bytes:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V69 campaign bytes are not canonical")
    _id(
        domains.CONSTRUCTION_K7_SOURCE_COMPLETE_RELATIONAL_CAMPAIGN_V69_DOMAIN,
        document,
        "campaign_id",
    )
    if (
        document.get("preregistration_id") != _PREREGISTRATION_ID
        or document.get("v68_campaign_id") != _V68_CAMPAIGN_ID
        or document.get("v68_verification_id") != _V68_VERIFICATION_ID
    ):
        _fail("V69 predecessor identity changed")
    occurrences = document.get("occurrences")
    expected = {
        (family, seed) for family, seeds in _EXPECTED_SEEDS.items() for seed in seeds
    }
    if (
        type(occurrences) is not list
        or len(occurrences) != 6
        or {(row.get("family"), row.get("seed")) for row in occurrences} != expected
    ):
        _fail("V69 occurrence inventory changed")
    facts = [_occurrence(row) for row in occurrences]
    accounting = {
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
        "prior_relational_abstract_support_branch_evaluations": sum(
            row["prior"]["abstract_compute"] for row in facts
        ),
        "strict_relational_abstract_support_branch_evaluations": sum(
            row["strict"]["abstract_compute"] for row in facts
        ),
        "prior_relational_world_model_synthesis_attempts": sum(
            row["prior"]["synthesis"] for row in facts
        ),
        "strict_relational_world_model_synthesis_attempts": sum(
            row["strict"]["synthesis"] for row in facts
        ),
        "retained_terminal_source_rows": sum(
            row[arm]["retained_rows"] for row in facts for arm in ("prior", "strict")
        ),
        "all_axes_separate": True,
    }
    if document.get("accounting") != accounting:
        _fail("V69 accounting changed")
    families = {}
    for family in _EXPECTED_SEEDS:
        selected = [row for row in facts if row["family"] == family]
        families[family] = {
            "occurrence_count": len(selected),
            "prior_relational_plan_success_count": sum(
                row["prior"]["successes"] for row in selected
            ),
            "strict_relational_plan_success_count": sum(
                row["strict"]["successes"] for row in selected
            ),
            "prior_certificate_local_labels": sum(
                row["prior"]["labels"] for row in selected
            ),
            "strict_certificate_local_labels": sum(
                row["strict"]["labels"] for row in selected
            ),
        }
    if document.get("family_projections") != families:
        _fail("V69 family projections changed")
    prior_success = sum(row["prior"]["successes"] for row in facts)
    strict_success = sum(row["strict"]["successes"] for row in facts)
    prior_active = sum(row["prior"]["active"] for row in facts)
    strict_active = sum(row["strict"]["active"] for row in facts)
    gate = {
        "prior_relational_plan_success_count": prior_success,
        "strict_relational_plan_success_count": strict_success,
        "prior_active_world_model_occurrence_count": prior_active,
        "strict_active_world_model_occurrence_count": strict_active,
        "source_complete_episode_count": 12,
        "required_source_complete_episode_count": 12,
        "required_relation": "PRIOR_PLAN_GT_ZERO_AND_ACTIVE_GT_ZERO_AND_ALL_SOURCE_COMPLETE",
        "passed": prior_success > 0 and prior_active > 0,
        "prior_vs_strict_improvement_required": False,
        "certificate_local_label_reduction_required": False,
    }
    if document.get("registered_source_complete_gate") != gate:
        _fail("V69 registered Gate changed")
    locks = {
        "all_v28_source_rows_retained": True,
        "producer_free_terminal_program_reconstruction_enabled": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "relational_abstract_plan_used_as_safety_authority": False,
        "producer_free_verification_present": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    if any(document.get(key) != value for key, value in locks.items()):
        _fail("V69 claim locks changed")
    payload = {
        "schema": "acfqp.source_complete_relational_verification.v69",
        "campaign_id": document["campaign_id"],
        "occurrence_count": len(facts),
        "source_complete_episode_count": 12,
        "independently_reconstructed_terminal_program_count": 12,
        "prior_relational_plan_success_count": prior_success,
        "strict_relational_plan_success_count": strict_success,
        "prior_certificate_local_labels": accounting["prior_certificate_local_labels"],
        "strict_certificate_local_labels": accounting["strict_certificate_local_labels"],
        "retained_terminal_source_rows": accounting["retained_terminal_source_rows"],
        "certificate_before_query_ledgers_replayed": True,
        "anonymous_status_coordinates_rederived": True,
        "relation_feature_inventories_rederived": True,
        "decision_tree_frontiers_rederived": True,
        "v28_imported": False,
        "v30_imported": False,
        "producer_imported": False,
        "campaign_core_imported": False,
        "abstract_planner_not_independently_reexecuted": True,
        "official_execution_allowed": False,
        "status": "PRODUCER_FREE_SOURCE_COMPLETE_RELATIONAL_PROGRAMS_RECONSTRUCTED",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v69(
            domains.CONSTRUCTION_K7_SOURCE_COMPLETE_RELATIONAL_VERIFICATION_V69_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V69 verification changed")
    return result


__all__ = ("verify_source_complete_relational_campaign_bytes_v69",)
