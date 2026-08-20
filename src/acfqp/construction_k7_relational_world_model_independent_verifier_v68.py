"""Producer-free ledger verifier for frozen V68 campaign bytes.

This verifier deliberately does not import the producer, campaign core, or any
V24/V27/V28/V29/V30 constructor.  It recomputes content identities, the exact
certificate-before-query ledger, embedded support-equality receipts, relation
program structural receipts, matched accounting, and claim locks.  The V28
source observations were not all retained by V68, so relation synthesis and
abstract planning are explicitly not independently reexecuted here.
"""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v68 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


VERIFICATION_ID = "6581428db574418a770777f5df03afde2b9299348b3b06fe997d321a909acb87"
EXPECTED_CANONICAL_BYTE_COUNT = 1_038
EXPECTED_CANONICAL_SHA256 = "4341ba4a799b9e5a71c08833926651f18c167a23cbe6a7c826c8557c827e4d47"
_PREREGISTRATION_ID = "5469acca7510f403a62c67d97f80bc764463741c6eee224e056649ab4f33095e"
_V67_CAMPAIGN_ID = "4726d258497299bba1dbaf37339ed5f497e3af7e1e114c602d5b4efe9614708b"
_V67_VERIFICATION_ID = "c7a219fcb73856215082022d1128efbed70aec50678c224533ba48944ebabb19"
_MULTI_DOMAIN = b"acfqp:generic-multi-residual-acquisition:v24\x00"
_TOTAL_DOMAIN = b"acfqp:total-adaptive-residual-acquisition:v20\x00"
_ADAPTIVE_DOMAIN = b"acfqp:adaptive-residual-factor-acquisition:v19\x00"
_BATCH_DOMAIN = b"acfqp:generic-batch-exact-multi-residual-support:v27\x00"
_TERMINAL_DOMAIN = b"acfqp:generic-relational-terminal-program:v28\x00"
_EXPECTED_SEEDS = {
    "BALANCED_BATCH_REFINEMENT": {691_101, 691_102},
    "COUPLED_EXCHANGE": {692_101, 692_102},
    "MAINTENANCE_CASCADE": {693_101, 693_102},
}
_RELATIONS = {"EQ", "LT", "LE", "GT", "GE"}


class ConstructionK7RelationalWorldModelIndependentVerifierV68Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RelationalWorldModelIndependentVerifierV68Error(message)


def _id(domain: str, document: dict[str, Any], key: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v68(domain, payload) != document.get(key):
        _fail(f"V68 {key} changed")


def _hash(document: Any, key: str, prefix: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V68 embedded {key} document changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != hashlib.sha256(
        prefix + canonical_json_bytes(payload)
    ).hexdigest():
        _fail(f"V68 embedded {key} changed")


def _verify_total(acquisition: Any, replay: Any, queries: int, rows: int) -> None:
    if type(acquisition) is not dict or type(replay) is not dict:
        _fail("V68 per-target acquisition changed")
    _hash(acquisition, "total_acquisition_id", _TOTAL_DOMAIN)
    status = acquisition.get("status")
    predecessor = acquisition.get("predecessor_acquisition")
    if status == "STATISTICAL_PROPOSAL_ISSUED":
        if type(predecessor) is not dict or type(acquisition.get("candidate")) is not dict:
            _fail("V68 statistical proposal changed")
        _hash(predecessor, "acquisition_id", _ADAPTIVE_DOMAIN)
    elif status == "ABSTAINED_INSUFFICIENT_CALIBRATED_EVIDENCE":
        if predecessor is not None or acquisition.get("candidate") is not None:
            _fail("V68 abstention changed")
    else:
        _fail("V68 per-target acquisition status changed")
    if (
        type(acquisition.get("ground_support_labels")) is not int
        or not 0 < acquisition["ground_support_labels"] <= queries
        or type(acquisition.get("raw_transition_rows_consumed")) is not int
        or not 0 < acquisition["raw_transition_rows_consumed"] <= rows
        or acquisition.get("proposal_only_not_safety_authority") is not True
        or replay.get("total_acquisition_id") != acquisition["total_acquisition_id"]
        or replay.get("status") != status
        or replay.get("full_query_stream_label_count") != queries
        or replay.get("full_query_stream_raw_transition_count") != rows
        or replay.get("future_transition_prediction_authority_present") is not False
    ):
        _fail("V68 per-target replay or accounting changed")


def _verify_multi(acquisition: Any, replay: Any, queries: int, rows: int) -> None:
    if type(acquisition) is not dict or type(replay) is not dict:
        _fail("V68 multi acquisition changed")
    _hash(acquisition, "multi_residual_acquisition_id", _MULTI_DOMAIN)
    targets = acquisition.get("unknown_residual_target_columns")
    results = acquisition.get("target_results")
    compilable = acquisition.get("compilable_candidates")
    actionable = acquisition.get("actionable_candidates")
    if (
        acquisition.get("schema") != "acfqp.generic_multi_residual_acquisition.v24"
        or type(targets) is not list
        or not targets
        or targets != sorted(set(targets))
        or type(results) is not list
        or len(results) != len(targets)
        or type(compilable) is not list
        or type(actionable) is not list
        or acquisition.get("shared_physical_ground_support_labels") != queries
        or acquisition.get("shared_raw_transition_row_count") != rows
        or acquisition.get("compilable_candidate_count") != len(compilable)
        or acquisition.get("actionable_candidate_count") != len(actionable)
        or acquisition.get("compilable_target_columns")
        != [item.get("target_column") for item in compilable]
        or acquisition.get("actionable_target_columns")
        != [item.get("target_column") for item in actionable]
        or acquisition.get("same_shared_raw_query_pool_for_every_target") is not True
        or acquisition.get("per_target_label_consumption_summed_as_physical_samples")
        is not False
        or acquisition.get("proposal_only_not_safety_authority") is not True
        or acquisition.get("complete_residual_world_model_synthesized") is not False
        or acquisition.get("global_exact_dynamics_claimed") is not False
    ):
        _fail("V68 multi acquisition inventory or claims changed")
    for target, result in zip(targets, results, strict=True):
        if type(result) is not dict or result.get("target_column") != target:
            _fail("V68 multi target row changed")
        _verify_total(
            result.get("total_acquisition"),
            result.get("full_shared_pool_replay"),
            queries,
            rows,
        )
    if (
        replay.get("multi_residual_acquisition_id")
        != acquisition["multi_residual_acquisition_id"]
        or replay.get("shared_physical_ground_support_labels") != queries
        or replay.get("target_count") != len(targets)
        or replay.get("compilable_candidate_count") != len(compilable)
        or replay.get("actionable_candidate_count") != len(actionable)
        or replay.get("all_target_totalizers_reconstructed") is not True
        or replay.get("future_transition_prediction_authority_present") is not False
    ):
        _fail("V68 multi replay changed")


def _verify_batch(result: Any, replay: Any, multi: dict[str, Any], queries: int) -> None:
    if type(result) is not dict or type(replay) is not dict:
        _fail("V68 batch-exact receipt changed")
    _hash(result, "batch_exact_multi_residual_id", _BATCH_DOMAIN)
    candidates = result.get("joint_batch_exact_candidates")
    refinements = result.get("target_refinements")
    targets = result.get("unknown_residual_target_columns")
    if (
        result.get("schema") != "acfqp.generic_batch_exact_multi_residual_support.v27"
        or result.get("v24_multi_residual_acquisition_id")
        != multi["multi_residual_acquisition_id"]
        or result.get("prior_library_id") != multi.get("prior_library_id")
        or targets != multi["unknown_residual_target_columns"]
        or type(candidates) is not list
        or type(refinements) is not list
        or len(refinements) != len(targets)
        or result.get("joint_batch_exact_candidate_count") != len(candidates)
        or result.get("joint_batch_exact_target_columns")
        != [row.get("target_column") for row in candidates]
        or result.get("shared_physical_ground_support_labels") != queries
        or result.get("empirical_batch_support_equality_only") is not True
        or result.get("future_unseen_support_authority_present") is not False
        or result.get("abstract_plan_safety_authority_present") is not False
        or result.get("global_exact_dynamics_claimed") is not False
        or result.get("complete_residual_world_model_synthesized") is not False
    ):
        _fail("V68 batch-exact inventory or claims changed")
    candidate_ids = {row.get("candidate_id") for row in candidates}
    if None in candidate_ids or len(candidate_ids) != len(candidates):
        _fail("V68 batch-exact candidate identity changed")
    exact_targets = []
    for target, refinement in zip(targets, refinements, strict=True):
        rows = refinement.get("batch_support_rows") if type(refinement) is dict else None
        exact = refinement.get("batch_exact_on_complete_frozen_query_pool")
        if (
            type(refinement) is not dict
            or refinement.get("target_column") != target
            or type(rows) is not list
            or type(exact) is not bool
            or refinement.get("eligible_for_joint_batch_exact_abstract_planning")
            is not exact
        ):
            _fail("V68 batch-exact refinement changed")
        observed_exact = bool(rows) and all(
            type(row) is dict
            and row.get("predicted_support") == row.get("observed_successor_support")
            and row.get("support_equal") is True
            for row in rows
        )
        if exact != observed_exact:
            _fail("V68 batch support equality changed")
        if exact:
            exact_targets.append(target)
    if exact_targets != result["joint_batch_exact_target_columns"]:
        _fail("V68 batch-exact target projection changed")
    if (
        replay.get("batch_exact_multi_residual_id")
        != result["batch_exact_multi_residual_id"]
        or replay.get("raw_state_action_batch_count")
        != result["raw_state_action_batch_count"]
        or replay.get("joint_batch_exact_candidate_count") != len(candidates)
        or replay.get("all_batch_support_equalities_reconstructed") is not True
        or replay.get("future_unseen_support_authority_present") is not False
    ):
        _fail("V68 batch-exact replay changed")


def _tree(node: Any, width: int, classes: set[str]) -> int:
    if type(node) is not dict:
        _fail("V68 terminal tree node changed")
    if node.get("kind") == "LEAF":
        if (
            set(node) != {"kind", "terminal_class", "status_token"}
            or node.get("terminal_class") not in classes
            or type(node.get("status_token")) is not int
        ):
            _fail("V68 terminal leaf changed")
        return 1
    if node.get("kind") != "RELATION" or set(node) != {
        "kind",
        "opcode",
        "left_column",
        "right_column",
        "when_true",
        "when_false",
    }:
        _fail("V68 terminal relation node changed")
    left, right = node.get("left_column"), node.get("right_column")
    if (
        node.get("opcode") not in _RELATIONS
        or type(left) is not int
        or type(right) is not int
        or not 0 <= left < width
        or not 0 <= right < width
        or left == right
    ):
        _fail("V68 terminal relation changed")
    return 1 + _tree(node["when_true"], width, classes) + _tree(
        node["when_false"], width, classes
    )


def _verify_terminal(result: Any, state_width: int) -> None:
    if type(result) is not dict:
        _fail("V68 terminal program changed")
    _hash(result, "terminal_program_id", _TERMINAL_DOMAIN)
    classes = result.get("terminal_classes_observed")
    tokens = result.get("status_token_by_terminal_class")
    frontier = result.get("decision_tree_candidate_frontier")
    if (
        result.get("schema") != "acfqp.generic_relational_terminal_program.v28"
        or type(classes) is not list
        or not {"ACTIVE", "ACCEPT"}.issubset(classes)
        or type(tokens) is not dict
        or set(tokens) != set(classes)
        or type(result.get("status_target_column")) is not int
        or not 0 <= result["status_target_column"] < state_width
        or type(frontier) is not list
        or not frontier
        or result.get("decision_tree_candidate_count") != len(frontier)
        or result.get("relation_opcode_registry") != ["EQ", "LT", "LE", "GT", "GE"]
        or result.get("anonymous_status_coordinate_derived_from_raw_labels") is not True
        or result.get("state_column_roles_preregistered") is not False
        or result.get("domain_specific_terminal_rule_present") is not False
        or result.get("empirical_program_only") is not True
        or result.get("future_unseen_terminal_authority_present") is not False
        or result.get("abstract_plan_safety_authority_present") is not False
        or result.get("global_exact_terminal_dynamics_claimed") is not False
    ):
        _fail("V68 terminal inventory or claims changed")
    if _tree(result.get("decision_tree"), state_width, set(classes)) != result.get(
        "decision_tree_node_count"
    ):
        _fail("V68 selected terminal tree count changed")
    for index, row in enumerate(frontier):
        tree = row.get("decision_tree") if type(row) is dict else None
        encoded = canonical_json_bytes(tree)
        if (
            row.get("candidate_index") != index
            or row.get("decision_tree_node_count")
            != _tree(tree, state_width, set(classes))
            or row.get("decision_tree_byte_count") != len(encoded)
            or row.get("decision_tree_sha256") != hashlib.sha256(encoded).hexdigest()
        ):
            _fail("V68 terminal frontier receipt changed")


def _episode(row: Any, family: str, seed: int, arm: str) -> dict[str, int]:
    if type(row) is not dict:
        _fail("V68 episode changed")
    failures = row.get("failed_certificates")
    distinctions = row.get("local_distinctions")
    raw_rows = row.get("raw_local_transition_rows")
    if not all(type(value) is list for value in (failures, distinctions, raw_rows)):
        _fail("V68 episode ledger inventory changed")
    if len(failures) != len(distinctions):
        _fail("V68 certificate/distinction count changed")
    flattened = []
    labels = 0
    transitions = 0
    contexts = set()
    state_width = None
    for index, (failure, distinction) in enumerate(
        zip(failures, distinctions, strict=True)
    ):
        raw_state = failure.get("raw_state") if type(failure) is dict else None
        if (
            failure.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("failure_index") != index
            or distinction.get("raw_state") != raw_state
            or distinction.get("ground_support_labels") != 1
            or distinction.get("query_after_failed_certificate") is not True
            or type(raw_state) is not list
        ):
            _fail("V68 certificate-before-query ordering changed")
        state_width = len(raw_state) if state_width is None else state_width
        if len(raw_state) != state_width:
            _fail("V68 state width changed")
        labels += 1
        if distinction.get("distinction_kind") == "QUERY_LOCAL_LEGAL_ACTION_SET":
            if failure.get("failure_kind") != "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT":
                _fail("V68 legality certificate changed")
        elif distinction.get("distinction_kind") == "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT":
            transitions += 1
            context = (tuple(raw_state), distinction.get("action_key"))
            rows = distinction.get("raw_transition_rows")
            if (
                context in contexts
                or distinction.get("action_key") != failure.get("action_key")
                or type(rows) is not list
                or not rows
            ):
                _fail("V68 residual distinction changed")
            contexts.add(context)
            for transition in rows:
                action = transition.get("selected_action") if type(transition) is dict else None
                if (
                    type(action) is not dict
                    or transition.get("pre_vector") != raw_state
                    or action.get("action_key") != distinction.get("action_key")
                ):
                    _fail("V68 transition/distinction join changed")
            flattened.extend(rows)
        else:
            _fail("V68 distinction kind changed")
    attempts = row.get("relational_abstract_plan_attempt_count")
    successes = row.get("relational_abstract_plan_success_count")
    activations = row.get("relational_world_model_activations")
    terminal_attempts = row.get("terminal_program_candidate_attempt_count")
    terminal_rejections = row.get("terminal_program_candidate_rejection_count")
    if (
        row.get("schema")
        != "acfqp.generic_relational_world_model_certificate_episode.v30"
        or row.get("family") != family
        or row.get("seed") != seed
        or row.get("episode_index") != 0
        or row.get("arm") != arm
        or row.get("local_ground_support_labels") != labels
        or row.get("queried_state_action_count") != transitions
        or flattened != raw_rows
        or len(row.get("action_keys", [])) != row.get("execution_steps")
        or len(row.get("outcome_tape_sha256", [])) != row.get("execution_steps")
        or not all(
            type(value) is int
            for value in (attempts, successes, terminal_attempts, terminal_rejections)
        )
        or not 0 <= successes <= attempts
        or not 0 <= terminal_rejections <= terminal_attempts
        or type(activations) is not list
        or row.get("success") is not True
        or row.get("terminal_and_transition_programs_jointly_selected_for_abstract_planning")
        is not True
        or row.get("all_ground_queries_followed_failed_certificates") is not True
        or row.get("query_local_exact_overlay_exclusively_used_for_safety") is not True
        or row.get("relational_abstract_plan_used_as_safety_authority") is not False
        or row.get("empirical_support_promoted_to_global_exact_dynamics") is not False
        or row.get("complete_world_model_synthesized") is not False
    ):
        _fail("V68 episode accounting or claims changed")
    multi = row.get("final_multi_residual_acquisition")
    _verify_multi(multi, row.get("final_multi_residual_replay"), transitions, len(raw_rows))
    batch = row.get("final_batch_exact_residual_support")
    _verify_batch(
        batch,
        row.get("final_batch_exact_residual_replay"),
        multi,
        transitions,
    )
    if state_width is None:
        _fail("V68 episode omitted query evidence")
    terminal = row.get("final_relational_terminal_program")
    _verify_terminal(terminal, state_width)
    batch_id = batch["batch_exact_multi_residual_id"]
    terminal_id = terminal["terminal_program_id"]
    for activation in activations:
        if (
            type(activation) is not dict
            or type(activation.get("batch_exact_multi_residual_id")) is not str
            or type(activation.get("terminal_program_id")) is not str
            or activation.get("all_observed_state_coordinates_represented") is not True
        ):
            _fail("V68 activation receipt changed")
    if activations and (
        activations[-1]["batch_exact_multi_residual_id"] != batch_id
        or activations[-1]["terminal_program_id"] != terminal_id
    ):
        _fail("V68 final activation/program join changed")
    return {
        "labels": labels,
        "steps": row["execution_steps"],
        "partial_compute": row["partial_planning_compute_events"],
        "abstract_compute": row["relational_abstract_support_branch_evaluations"],
        "synthesis": row["relational_world_model_synthesis_attempt_count"],
        "terminal_attempts": terminal_attempts,
        "successes": successes,
        "rejections": terminal_rejections,
        "active": int(bool(activations)),
    }


def _occurrence(row: Any) -> dict[str, Any]:
    if type(row) is not dict:
        _fail("V68 occurrence changed")
    _id(
        domains.CONSTRUCTION_K7_RELATIONAL_WORLD_MODEL_OCCURRENCE_V68_DOMAIN,
        row,
        "occurrence_id",
    )
    family, seed = row.get("family"), row.get("seed")
    if family not in _EXPECTED_SEEDS or seed not in _EXPECTED_SEEDS[family]:
        _fail("V68 occurrence identity changed")
    prior = _episode(row.get("prior_episode"), family, seed, "RESIDUAL_FACTOR_PRIOR_ON")
    strict = _episode(
        row.get("strict_episode"), family, seed, "STRICT_NO_RESIDUAL_FACTOR_PRIOR"
    )
    if (
        row["prior_episode"]["partial_candidate_id"]
        != row["strict_episode"]["partial_candidate_id"]
        or type(row.get("common_partial_ground_support_labels")) is not int
        or row.get("matched_environment_seed_episode_partial_candidate_and_observations")
        is not True
        or row.get("only_switched_variable")
        != "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH"
        or row.get("terminal_and_transition_programs_jointly_selected") is not True
        or row.get("query_local_overlay_only_safety_authority") is not True
    ):
        _fail("V68 occurrence matched join changed")
    return {
        "family": family,
        "partial": row["common_partial_ground_support_labels"],
        "prior": prior,
        "strict": strict,
    }


def verify_relational_world_model_campaign_bytes_v68(raw: bytes) -> bytes:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V68 campaign bytes are not canonical")
    _id(
        domains.CONSTRUCTION_K7_RELATIONAL_WORLD_MODEL_CAMPAIGN_V68_DOMAIN,
        document,
        "campaign_id",
    )
    if (
        document.get("preregistration_id") != _PREREGISTRATION_ID
        or document.get("v67_campaign_id") != _V67_CAMPAIGN_ID
        or document.get("v67_verification_id") != _V67_VERIFICATION_ID
    ):
        _fail("V68 predecessor identity changed")
    occurrences = document.get("occurrences")
    expected = {
        (family, seed) for family, seeds in _EXPECTED_SEEDS.items() for seed in seeds
    }
    if (
        type(occurrences) is not list
        or len(occurrences) != 6
        or {(row.get("family"), row.get("seed")) for row in occurrences} != expected
    ):
        _fail("V68 occurrence inventory changed")
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
        "prior_terminal_program_candidate_attempts": sum(
            row["prior"]["terminal_attempts"] for row in facts
        ),
        "strict_terminal_program_candidate_attempts": sum(
            row["strict"]["terminal_attempts"] for row in facts
        ),
        "all_axes_separate": True,
    }
    if document.get("accounting") != accounting:
        _fail("V68 accounting changed")
    family_rows = {}
    for family in _EXPECTED_SEEDS:
        selected = [row for row in facts if row["family"] == family]
        family_rows[family] = {
            "occurrence_count": len(selected),
            "prior_relational_plan_success_count": sum(
                row["prior"]["successes"] for row in selected
            ),
            "strict_relational_plan_success_count": sum(
                row["strict"]["successes"] for row in selected
            ),
            "prior_active_world_model_occurrence_count": sum(
                row["prior"]["active"] for row in selected
            ),
            "strict_active_world_model_occurrence_count": sum(
                row["strict"]["active"] for row in selected
            ),
            "prior_certificate_local_labels": sum(
                row["prior"]["labels"] for row in selected
            ),
            "strict_certificate_local_labels": sum(
                row["strict"]["labels"] for row in selected
            ),
        }
    if document.get("family_projections") != family_rows:
        _fail("V68 family projections changed")
    prior_success = sum(row["prior"]["successes"] for row in facts)
    strict_success = sum(row["strict"]["successes"] for row in facts)
    prior_active = sum(row["prior"]["active"] for row in facts)
    strict_active = sum(row["strict"]["active"] for row in facts)
    prior_rejections = sum(row["prior"]["rejections"] for row in facts)
    gate = {
        "prior_relational_plan_success_count": prior_success,
        "strict_relational_plan_success_count": strict_success,
        "prior_active_world_model_occurrence_count": prior_active,
        "strict_active_world_model_occurrence_count": strict_active,
        "prior_terminal_candidate_rejection_count": prior_rejections,
        "required_relation": "PRIOR_PLAN_GT_ZERO_AND_ACTIVE_GT_ZERO_AND_REJECTION_GT_ZERO",
        "passed": prior_success > 0 and prior_active > 0 and prior_rejections > 0,
        "prior_vs_strict_improvement_required": False,
        "certificate_local_label_reduction_required": False,
    }
    if document.get("registered_relational_world_model_gate") != gate:
        _fail("V68 registered Gate changed")
    locks = {
        "terminal_and_transition_programs_jointly_selected_for_abstract_planning": True,
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
        _fail("V68 claim locks changed")
    payload = {
        "schema": "acfqp.relational_world_model_verification.v68",
        "campaign_id": document["campaign_id"],
        "occurrence_count": len(facts),
        "prior_relational_plan_success_count": prior_success,
        "strict_relational_plan_success_count": strict_success,
        "prior_active_world_model_occurrence_count": prior_active,
        "strict_active_world_model_occurrence_count": strict_active,
        "prior_terminal_candidate_rejection_count": prior_rejections,
        "prior_certificate_local_labels": accounting["prior_certificate_local_labels"],
        "strict_certificate_local_labels": accounting["strict_certificate_local_labels"],
        "certificate_before_query_ledgers_replayed": True,
        "query_local_overlay_rows_rejoined": True,
        "v19_v20_v24_v27_v28_content_ids_recomputed": True,
        "batch_support_and_relation_tree_receipts_replayed": True,
        "v28_source_rows_not_fully_retained_by_v68": True,
        "relational_synthesis_and_planner_not_independently_reexecuted": True,
        "producer_imported": False,
        "campaign_core_imported": False,
        "planner_imported": False,
        "official_execution_allowed": False,
        "status": "PRODUCER_FREE_RELATIONAL_WORLD_MODEL_LEDGER_VERIFIED",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v68(
            domains.CONSTRUCTION_K7_RELATIONAL_WORLD_MODEL_VERIFICATION_V68_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V68 verification changed")
    return result


__all__ = ("verify_relational_world_model_campaign_bytes_v68",)
