"""Producer-free V70 target-ledger and transferred-program verification."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v70 as domains
from acfqp.generic_relational_terminal_program_independent_replay_v32 import (
    GenericRelationalTerminalProgramIndependentReplayV32Error,
    verify_source_complete_relational_program_v32,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


VERIFICATION_ID = "b55346fd542c47380f5581d065b3a50b1da786f8bb0f42f611dafa05fa897fd7"
EXPECTED_CANONICAL_BYTE_COUNT = 1_085
EXPECTED_CANONICAL_SHA256 = "82bc0e150b826e2e0c166b2a08c7ff81460e4393c5d309af60a42c93aff4a0e7"
_PREREGISTRATION_ID = "394711e2323dff214f3a78241b9549d4a8af4e1877cde6530ab91740982b82e6"
_V69_CAMPAIGN_ID = "3a7655580b14f00a6833599f676c7b03719ae59cb5c48d2677545b47e38ad7a8"
_V69_VERIFICATION_ID = "3c67ad21d01897448aa5a60c7fe4d802f2b1f477761451dc801e1b270c31d3ed"
_LIBRARY_ID = "8657115a19bace2861b3a14ff780a2708b6e76101a2b7468e52e5285a113b2a9"
_SOURCE_DOMAIN = b"acfqp:source-complete-terminal-program-evidence:v31\x00"
_EPISODE_DOMAIN = b"acfqp:generic-source-complete-relational-world-model:v31\x00"
_INSTANTIATION_DOMAIN = b"acfqp:generic-role-free-relational-template-instantiation:v33\x00"
_PLAN_DOMAIN = b"acfqp:generic-role-free-relational-world-model-plan:v34\x00"
_TERMINAL_DOMAIN = b"acfqp:generic-relational-terminal-program:v28\x00"
_EXPECTED_SEEDS = {
    "BALANCED_BATCH_REFINEMENT": {711_101, 711_102},
    "COUPLED_EXCHANGE": {712_101, 712_102},
    "MAINTENANCE_CASCADE": {713_101, 713_102},
}


class ConstructionK7RoleFreeRelationalTransferIndependentVerifierV70Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RoleFreeRelationalTransferIndependentVerifierV70Error(message)


def _id(domain: str, document: dict[str, Any], key: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v70(domain, payload) != document.get(key):
        _fail(f"V70 {key} changed")


def _hash(document: Any, key: str, prefix: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V70 embedded {key} document changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != hashlib.sha256(
        prefix + canonical_json_bytes(payload)
    ).hexdigest():
        _fail(f"V70 embedded {key} changed")


def _relation(opcode: str, left: int, right: int, state: tuple[int, ...]) -> bool:
    if opcode == "EQ":
        return state[left] == state[right]
    if opcode == "LT":
        return state[left] < state[right]
    if opcode == "LE":
        return state[left] <= state[right]
    if opcode == "GT":
        return state[left] > state[right]
    if opcode == "GE":
        return state[left] >= state[right]
    _fail("V70 transferred relation opcode changed")


def _evaluate(node: Any, state: tuple[int, ...]) -> tuple[str, int]:
    while type(node) is dict and node.get("kind") == "RELATION":
        left, right = node.get("left_column"), node.get("right_column")
        if (
            type(left) is not int
            or type(right) is not int
            or not 0 <= left < len(state)
            or not 0 <= right < len(state)
            or left == right
        ):
            _fail("V70 transferred relation columns changed")
        node = node["when_true"] if _relation(
            node.get("opcode"), left, right, state
        ) else node["when_false"]
    if (
        type(node) is not dict
        or node.get("kind") != "LEAF"
        or node.get("terminal_class") not in ("ACTIVE", "ACCEPT", "REJECT")
        or type(node.get("status_token")) is not int
    ):
        _fail("V70 transferred relation leaf changed")
    return node["terminal_class"], node["status_token"]


def _label(row: Mapping[str, Any]) -> str:
    legal = row.get("legal_action_keys_after")
    terminal = row.get("terminal_acceptance_after")
    if type(legal) is not list:
        _fail("V70 target row legal inventory changed")
    if legal:
        if terminal is not None:
            _fail("V70 active row carried terminal label")
        return "ACTIVE"
    if terminal is True:
        return "ACCEPT"
    if terminal is False:
        return "REJECT"
    _fail("V70 terminal row omitted label")


def _certificate_ledger(episode: dict[str, Any]) -> dict[str, int]:
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    raw_rows = episode.get("raw_local_transition_rows")
    if not all(type(value) is list for value in (failures, distinctions, raw_rows)):
        _fail("V70 certificate ledger changed")
    if len(failures) != len(distinctions):
        _fail("V70 certificate/distinction count changed")
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
            _fail("V70 certificate-before-query order changed")
        labels += 1
        if distinction.get("distinction_kind") == "QUERY_LOCAL_LEGAL_ACTION_SET":
            if failure.get("failure_kind") != "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT":
                _fail("V70 legality certificate changed")
        elif distinction.get("distinction_kind") == "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT":
            rows = distinction.get("raw_transition_rows")
            context = (
                tuple(distinction.get("raw_state", ())),
                distinction.get("action_key"),
            )
            if context in contexts or type(rows) is not list or not rows:
                _fail("V70 residual query receipt changed")
            contexts.add(context)
            transitions += 1
            flattened.extend(rows)
        else:
            _fail("V70 distinction kind changed")
    if (
        flattened != raw_rows
        or episode.get("local_ground_support_labels") != labels
        or episode.get("queried_state_action_count") != transitions
    ):
        _fail("V70 target query accounting changed")
    return {"labels": labels, "transitions": transitions}


def _source_episode(envelope: Any, family: str, seed: int) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(envelope) is not dict:
        _fail("V70 source-complete envelope changed")
    _hash(envelope, "source_complete_episode_id", _EPISODE_DOMAIN)
    evidence = envelope.get("terminal_program_source_evidence")
    episode = envelope.get("predecessor_v30_episode")
    if type(evidence) is not dict or type(episode) is not dict:
        _fail("V70 target source evidence changed")
    _hash(evidence, "source_evidence_id", _SOURCE_DOMAIN)
    common = evidence.get("common_partial_raw_transition_rows")
    local = evidence.get("query_local_raw_transition_rows")
    rows = evidence.get("raw_transition_rows")
    if (
        type(common) is not list
        or type(local) is not list
        or type(rows) is not list
        or rows != [*common, *local]
        or local != episode.get("raw_local_transition_rows")
        or evidence.get("common_partial_row_count") != len(common)
        or evidence.get("query_local_row_count") != len(local)
        or evidence.get("all_v28_source_rows_retained") is not True
        or envelope.get("source_evidence_id") != evidence["source_evidence_id"]
        or envelope.get("all_v28_source_rows_retained") is not True
    ):
        _fail("V70 target source union changed")
    source = {
        "layout": evidence.get("layout"),
        "unknown_residual_target_columns": evidence.get(
            "unknown_residual_target_columns"
        ),
        "raw_transition_rows": rows,
    }
    try:
        verify_source_complete_relational_program_v32(
            source, episode.get("final_relational_terminal_program")
        )
    except GenericRelationalTerminalProgramIndependentReplayV32Error as error:
        _fail(f"V70 target exact-context reconstruction failed: {error}")
    ledger = _certificate_ledger(episode)
    if (
        episode.get("schema")
        != "acfqp.generic_relational_world_model_certificate_episode.v30"
        or episode.get("family") != family
        or episode.get("seed") != seed
        or episode.get("success") is not True
        or episode.get("all_ground_queries_followed_failed_certificates") is not True
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or episode.get("relational_abstract_plan_used_as_safety_authority")
        is not False
        or episode.get("complete_world_model_synthesized") is not False
    ):
        _fail("V70 target episode claims changed")
    if ledger["labels"] != episode["local_ground_support_labels"]:
        _fail("V70 target label ledger changed")
    return episode, source


def _verify_abstract_plan(
    plan: Any, batch_id: str, terminal_id: str, *, transferred: bool
) -> int:
    if (
        type(plan) is not dict
        or plan.get("schema") != "acfqp.generic_relational_residual_abstract_plan.v29"
        or plan.get("batch_exact_multi_residual_id") != batch_id
        or plan.get("terminal_program_id") != terminal_id
        or plan.get("support_feasible_receding_plan_found") is not True
        or plan.get("ground_transition_accessed_during_abstract_search") is not False
        or plan.get("abstract_plan_used_as_safety_authority") is not False
        or plan.get("complete_world_model_claimed") is not False
    ):
        _fail("V70 abstract plan receipt changed")
    if transferred and plan.get(
        "terminal_relation_and_transition_program_jointly_selected"
    ) is not True:
        _fail("V70 transferred plan composition changed")
    return plan["abstract_support_branch_evaluations"]


def _verify_transfer(result: Any, episode: dict[str, Any], source: dict[str, Any]) -> dict[str, int]:
    if type(result) is not dict or result.get("status") not in (
        "ROLE_FREE_TRANSFER_PLAN_FOUND",
        "ROLE_FREE_TRANSFER_ABSTAINED",
    ):
        _fail("V70 transfer result changed")
    if result["status"] == "ROLE_FREE_TRANSFER_ABSTAINED":
        if type(result.get("failure")) is not str or result.get("plan") is not None:
            _fail("V70 transfer abstention changed")
        return {"success": 0, "binding": 0, "compute": 0}
    plan = result.get("plan")
    if type(plan) is not dict:
        _fail("V70 transfer plan changed")
    _hash(plan, "role_free_world_model_plan_id", _PLAN_DOMAIN)
    instantiation = plan.get("target_instantiation")
    _hash(instantiation, "instantiation_id", _INSTANTIATION_DOMAIN)
    terminal = instantiation.get("instantiated_terminal_program")
    _hash(terminal, "terminal_program_id", _TERMINAL_DOMAIN)
    internal_library_id = plan.get("template_library_id")
    if (
        type(internal_library_id) is not str
        or len(internal_library_id) != 64
        or plan.get("target_instantiation_id") != instantiation["instantiation_id"]
        or plan.get("instantiated_terminal_program_id")
        != terminal["terminal_program_id"]
        or plan.get("cross_occurrence_role_free_template_reused") is not True
        or plan.get("target_observation_exactness_required_before_planning") is not True
        or plan.get("ground_transition_accessed_during_abstract_search") is not False
        or plan.get("abstract_plan_used_as_safety_authority") is not False
        or plan.get("complete_world_model_claimed") is not False
        or instantiation.get("template_library_id") != internal_library_id
        or instantiation.get("target_observation_exactness_required") is not True
        or instantiation.get("cross_occurrence_proposal_only") is not True
        or instantiation.get("future_target_prediction_authority_present") is not False
        or instantiation.get("abstract_plan_safety_authority_present") is not False
    ):
        _fail("V70 transfer claim or library join changed")
    order = source["layout"]["state_canonical_to_raw"]
    status_target = terminal.get("status_target_column")
    frontier = terminal.get("decision_tree_candidate_frontier")
    if type(frontier) is not list or not frontier or type(status_target) is not int:
        _fail("V70 transferred terminal frontier changed")
    for candidate in frontier:
        tree = candidate.get("decision_tree") if type(candidate) is dict else None
        for row in source["raw_transition_rows"]:
            state = tuple(row["post_vector"][index] for index in order)
            label, token = _evaluate(tree, state)
            if label != _label(row) or token != state[status_target]:
                _fail("V70 transferred tree is not target-observation exact")
    abstract = plan.get("abstract_plan")
    compute = _verify_abstract_plan(
        abstract,
        episode["final_batch_exact_residual_support"][
            "batch_exact_multi_residual_id"
        ],
        terminal["terminal_program_id"],
        transferred=True,
    )
    if plan.get("initial_action_key") != abstract["initial_action_key"]:
        _fail("V70 transferred initial action changed")
    return {
        "success": 1,
        "binding": instantiation["binding_evaluation_count"],
        "compute": compute,
    }


def _verify_strict(result: Any, episode: dict[str, Any]) -> dict[str, int]:
    if type(result) is not dict or result.get("status") not in (
        "EXACT_CONTEXT_PLAN_FOUND",
        "EXACT_CONTEXT_PLAN_ABSTAINED",
    ):
        _fail("V70 strict result changed")
    if result["status"] == "EXACT_CONTEXT_PLAN_ABSTAINED":
        if type(result.get("failure")) is not str or result.get("plan") is not None:
            _fail("V70 strict abstention changed")
        return {"success": 0, "compute": 0}
    plan = result.get("plan")
    compute = _verify_abstract_plan(
        plan,
        episode["final_batch_exact_residual_support"][
            "batch_exact_multi_residual_id"
        ],
        episode["final_relational_terminal_program"]["terminal_program_id"],
        transferred=False,
    )
    return {"success": 1, "compute": compute}


def _occurrence(row: Any) -> dict[str, Any]:
    if type(row) is not dict:
        _fail("V70 occurrence changed")
    _id(
        domains.CONSTRUCTION_K7_ROLE_FREE_RELATIONAL_OCCURRENCE_V70_DOMAIN,
        row,
        "occurrence_id",
    )
    family, seed = row.get("family"), row.get("seed")
    if family not in _EXPECTED_SEEDS or seed not in _EXPECTED_SEEDS[family]:
        _fail("V70 occurrence identity changed")
    episode, source = _source_episode(
        row.get("target_source_complete_episode"), family, seed
    )
    transfer = _verify_transfer(row.get("transferred_role_free_arm"), episode, source)
    strict = _verify_strict(row.get("strict_exact_context_arm"), episode)
    ood = row.get("incompatible_schema_ood_control")
    if (
        type(ood) is not dict
        or ood.get("status") != "INCOMPATIBLE_SCHEMA_REJECTED"
        or row.get("same_target_rows_residual_support_and_planner_caps_between_arms")
        is not True
        or row.get("only_switched_variable")
        != "TERMINAL_PROGRAM_SOURCE_ROLE_FREE_LIBRARY_VS_TARGET_EXACT_CONTEXT"
        or row.get("query_local_overlay_only_safety_authority") is not True
    ):
        _fail("V70 OOD or matched-arm receipt changed")
    return {
        "family": family,
        "partial": row["common_partial_ground_support_labels"],
        "labels": episode["local_ground_support_labels"],
        "steps": episode["execution_steps"],
        "partial_compute": episode["partial_planning_compute_events"],
        "online_compute": episode["relational_abstract_support_branch_evaluations"],
        "transfer": transfer,
        "strict": strict,
        "ood": 1,
    }


def verify_role_free_relational_transfer_campaign_bytes_v70(raw: bytes) -> bytes:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V70 campaign bytes are not canonical")
    _id(
        domains.CONSTRUCTION_K7_ROLE_FREE_RELATIONAL_CAMPAIGN_V70_DOMAIN,
        document,
        "campaign_id",
    )
    if (
        document.get("preregistration_id") != _PREREGISTRATION_ID
        or document.get("v69_campaign_id") != _V69_CAMPAIGN_ID
        or document.get("v69_verification_id") != _V69_VERIFICATION_ID
        or document.get("template_library_artifact_id") != _LIBRARY_ID
    ):
        _fail("V70 predecessor identity changed")
    occurrences = document.get("occurrences")
    expected = {
        (family, seed) for family, seeds in _EXPECTED_SEEDS.items() for seed in seeds
    }
    if (
        type(occurrences) is not list
        or len(occurrences) != 6
        or {(row.get("family"), row.get("seed")) for row in occurrences} != expected
    ):
        _fail("V70 occurrence inventory changed")
    facts = [_occurrence(row) for row in occurrences]
    accounting = {
        "offline_template_source_labels": 401,
        "offline_residual_library_labels": 204,
        "target_common_partial_acquisition_labels": sum(row["partial"] for row in facts),
        "target_certificate_local_labels": sum(row["labels"] for row in facts),
        "target_execution_steps": sum(row["steps"] for row in facts),
        "target_online_partial_planning_compute_events": sum(
            row["partial_compute"] for row in facts
        ),
        "target_online_relational_planning_compute_events": sum(
            row["online_compute"] for row in facts
        ),
        "transfer_template_binding_evaluations": sum(
            row["transfer"]["binding"] for row in facts
        ),
        "transfer_abstract_support_branch_evaluations": sum(
            row["transfer"]["compute"] for row in facts
        ),
        "strict_abstract_support_branch_evaluations": sum(
            row["strict"]["compute"] for row in facts
        ),
        "all_axes_separate": True,
    }
    if document.get("accounting") != accounting:
        _fail("V70 accounting changed")
    families = {}
    for family in _EXPECTED_SEEDS:
        selected = [row for row in facts if row["family"] == family]
        families[family] = {
            "occurrence_count": len(selected),
            "transferred_plan_success_count": sum(
                row["transfer"]["success"] for row in selected
            ),
            "strict_plan_success_count": sum(
                row["strict"]["success"] for row in selected
            ),
            "target_certificate_local_labels": sum(row["labels"] for row in selected),
        }
    if document.get("family_projections") != families:
        _fail("V70 family projections changed")
    transfer_success = sum(row["transfer"]["success"] for row in facts)
    strict_success = sum(row["strict"]["success"] for row in facts)
    ood = sum(row["ood"] for row in facts)
    gate = {
        "transferred_plan_success_count": transfer_success,
        "strict_plan_success_count": strict_success,
        "incompatible_schema_ood_rejection_count": ood,
        "required_ood_rejection_count": 6,
        "required_relation": "TRANSFER_PLAN_GT_ZERO_AND_ALL_INCOMPATIBLE_SCHEMA_OOD_REJECTED",
        "passed": transfer_success > 0 and ood == 6,
        "transfer_outperform_strict_required": False,
        "target_label_reduction_required": False,
    }
    if document.get("registered_role_free_transfer_gate") != gate:
        _fail("V70 registered Gate changed")
    locks = {
        "cross_occurrence_role_free_templates_reused": True,
        "target_observation_exactness_required_before_planning": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "transferred_abstract_plan_used_as_safety_authority": False,
        "producer_free_verification_present": False,
        "online_transfer_planner_integrated": False,
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
        _fail("V70 claim locks changed")
    payload = {
        "schema": "acfqp.role_free_relational_transfer_verification.v70",
        "campaign_id": document["campaign_id"],
        "occurrence_count": 6,
        "transferred_plan_success_count": transfer_success,
        "strict_plan_success_count": strict_success,
        "incompatible_schema_ood_rejection_receipt_count": ood,
        "target_exact_context_terminal_programs_reconstructed": 6,
        "transferred_terminal_programs_target_rows_replayed": transfer_success,
        "target_certificate_local_labels": accounting["target_certificate_local_labels"],
        "certificate_before_query_ledgers_replayed": True,
        "target_relation_programs_independently_reconstructed": True,
        "transferred_relation_trees_independently_evaluated_on_target_rows": True,
        "template_library_membership_not_independently_opened": True,
        "ood_input_not_retained_so_rejection_not_independently_reexecuted": True,
        "abstract_plans_not_independently_reexecuted": True,
        "producer_imported": False,
        "campaign_core_imported": False,
        "v28_imported": False,
        "v29_imported": False,
        "official_execution_allowed": False,
        "status": "PRODUCER_FREE_ROLE_FREE_TRANSFER_TARGET_LEDGER_VERIFIED",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v70(
            domains.CONSTRUCTION_K7_ROLE_FREE_RELATIONAL_VERIFICATION_V70_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V70 verification changed")
    return result


__all__ = ("verify_role_free_relational_transfer_campaign_bytes_v70",)
