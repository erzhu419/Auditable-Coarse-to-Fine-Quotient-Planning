"""Compile a contextual-ordinal residual version space with terminal frontiers."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp.generic_contextual_ordinal_residual_v54 import version_space_v54
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.generic_relational_terminal_program_v28 import (
    evaluate_relational_terminal_program_v28,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericContextualOrdinalModelCompilerV54Error(ValueError):
    pass


_ACQUISITION_DOMAIN = b"acfqp:generic-contextual-ordinal-frontier-acquisition:v54\x00"
_BUNDLE_DOMAIN = b"acfqp:relation-covering-contextual-ordinal-frontier-acquisition:v54\x00"
_MODEL_DOMAIN = b"acfqp:generic-contextual-ordinal-successor-model:v54\x00"


def _fail(message: str) -> NoReturn:
    raise GenericContextualOrdinalModelCompilerV54Error(message)


def _content_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _terminal_frontier_exact(
    rows: list[dict[str, Any]],
    layout: Mapping[str, Any],
    terminal_frontier: list[dict[str, Any]],
    status_target: int,
) -> None:
    state_order = layout.get("state_canonical_to_raw")
    if type(state_order) is not list:
        _fail("V54 terminal state projection changed")
    for row in rows:
        post = row.get("post_vector") if type(row) is dict else None
        if type(post) is not list or sorted(state_order) != list(range(len(post))):
            _fail("V54 retained terminal row changed")
        canonical_post = tuple(post[index] for index in state_order)
        label = v42._terminal_label(row)  # noqa: SLF001
        for terminal_row in terminal_frontier:
            prediction = evaluate_relational_terminal_program_v28(
                {
                    "schema": "acfqp.generic_relational_terminal_program.v28",
                    "decision_tree": terminal_row.get("decision_tree"),
                },
                canonical_post,
            )
            if (
                prediction.get("terminal_class") != label
                or prediction.get("status_token") != canonical_post[status_target]
            ):
                _fail("V54 terminal frontier is not exact on acquired successors")


def compile_contextual_ordinal_model_v54(
    candidate: PartialFactorCandidateV15,
    source_complete_evidence: Mapping[str, Any],
    relation_covering_acquisition: Mapping[str, Any],
) -> dict[str, Any]:
    if type(candidate) is not PartialFactorCandidateV15:
        _fail("V54 partial candidate type changed")
    if type(source_complete_evidence) is not dict or type(relation_covering_acquisition) is not dict:
        _fail("V54 source artifact type changed")
    document = candidate.public_document
    layout = source_complete_evidence.get("layout")
    unknown = source_complete_evidence.get("unknown_residual_target_columns")
    source_rows = source_complete_evidence.get("raw_transition_rows")
    contextual_supports = source_complete_evidence.get("contextual_action_field_supports")
    if (
        type(layout) is not dict
        or layout != document.get("layout")
        or type(unknown) is not list
        or unknown != document.get("unknown_residual_target_columns")
        or unknown != sorted(set(unknown))
        or type(source_rows) is not list
        or not source_rows
        or type(contextual_supports) is not list
        or not contextual_supports
        or source_complete_evidence.get("contextual_action_supports_derived_from_catalogue_only") is not True
    ):
        _fail("V54 source/candidate identity join changed")
    schedule = relation_covering_acquisition.get("query_schedule")
    acquisition = relation_covering_acquisition.get("contextual_ordinal_frontier_acquisition")
    expected_schedule = schedule_relation_covering_queries_v39(source_complete_evidence)
    if (
        type(schedule) is not dict
        or canonical_json_bytes(schedule) != canonical_json_bytes(expected_schedule)
        or type(acquisition) is not dict
        or relation_covering_acquisition.get("schema")
        != "acfqp.relation_covering_contextual_ordinal_frontier_acquisition.v54"
        or relation_covering_acquisition.get("query_schedule_id") != schedule.get("query_schedule_id")
        or relation_covering_acquisition.get("contextual_ordinal_frontier_acquisition_id")
        != acquisition.get("contextual_ordinal_frontier_acquisition_id")
    ):
        _fail("V54 acquisition bundle join changed")
    acquisition_payload = {
        key: value for key, value in acquisition.items()
        if key != "contextual_ordinal_frontier_acquisition_id"
    }
    bundle_payload = {
        key: value for key, value in relation_covering_acquisition.items()
        if key != "relation_covering_contextual_ordinal_acquisition_id"
    }
    if (
        _content_id(_ACQUISITION_DOMAIN, acquisition_payload)
        != acquisition.get("contextual_ordinal_frontier_acquisition_id")
        or _content_id(_BUNDLE_DOMAIN, bundle_payload)
        != relation_covering_acquisition.get("relation_covering_contextual_ordinal_acquisition_id")
        or acquisition.get("status") != "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        or acquisition.get("heldout_exact_prediction") is not True
        or acquisition.get("heldout_rows_accessed_before_stop") is not False
        or acquisition.get("every_retained_terminal_frontier_candidate_prequentially_checked") is not True
        or acquisition.get("every_retained_residual_frontier_candidate_prequentially_checked") is not True
        or acquisition.get("every_retained_terminal_frontier_candidate_heldout_checked") is not True
        or acquisition.get("every_retained_residual_frontier_candidate_heldout_checked") is not True
        or acquisition.get("proposal_only_not_safety_authority") is not True
    ):
        _fail("V54 requires a content-bound heldout-validated joint proposal")
    groups = v42._groups(schedule["scheduled_raw_transition_rows"])  # noqa: SLF001
    stop = acquisition.get("stopped_physical_ground_support_labels")
    if type(stop) is not int or not 1 <= stop < len(groups):
        _fail("V54 acquisition stop changed")
    acquired_groups = groups[:stop]
    acquired_rows = [copy.deepcopy(row) for group in acquired_groups for row in group]
    terminal = acquisition.get("selected_terminal_program")
    if (
        type(terminal) is not dict
        or terminal.get("schema") != "acfqp.generic_relational_terminal_program.v28"
        or terminal.get("future_unseen_terminal_authority_present") is not False
        or terminal.get("terminal_program_id") != acquisition.get("selected_terminal_program_id")
    ):
        _fail("V54 selected terminal program changed")
    status_target = terminal.get("status_target_column")
    if type(status_target) is not int or status_target not in unknown:
        _fail("V54 status target changed")
    terminal_frontier = v42._minimal_terminal_frontier(terminal)  # noqa: SLF001
    _terminal_frontier_exact(acquired_rows, layout, terminal_frontier, status_target)

    residual_targets = [target for target in unknown if target != status_target]
    if not residual_targets:
        _fail("V54 requires a non-status residual coordinate")
    spaces = []
    selection_compute = 0
    for target in residual_targets:
        frontier, evaluations = version_space_v54(
            source_complete_evidence, acquired_groups, target
        )
        selection_compute += evaluations
        if not frontier:
            _fail("V54 acquired rows identify no residual expression")
        spaces.append(
            {
                "target_column": target,
                "batch_exact_candidate_count": len(frontier),
                "batch_exact_candidate_frontier": frontier,
            }
        )
    if spaces != acquisition.get("selected_residual_version_spaces"):
        _fail("V54 frozen residual frontier changed before compilation")
    known_assignments = copy.deepcopy(list(candidate.assignments))
    width = document.get("state_width")
    modeled = {
        *(row["target_column"] for row in known_assignments),
        *residual_targets,
        status_target,
    }
    if type(width) is not int or modeled != set(range(width)):
        _fail("V54 compiled components do not cover the canonical state")
    state_order = layout["state_canonical_to_raw"]
    accepting = [
        [row["post_vector"][index] for index in state_order]
        for row in acquired_rows
        if row.get("terminal_acceptance_after") is True
    ]
    payload = {
        "schema": "acfqp.generic_contextual_ordinal_successor_model.v54",
        "partial_candidate_id": document["candidate_id"],
        "source_relation_covering_acquisition_id": relation_covering_acquisition[
            "relation_covering_contextual_ordinal_acquisition_id"
        ],
        "source_query_schedule_id": schedule["query_schedule_id"],
        "source_contextual_ordinal_acquisition_id": acquisition[
            "contextual_ordinal_frontier_acquisition_id"
        ],
        "source_complete_evidence_sha256": hashlib.sha256(
            canonical_json_bytes(source_complete_evidence)
        ).hexdigest(),
        "source_layout": copy.deepcopy(layout),
        "source_contextual_action_field_supports": copy.deepcopy(contextual_supports),
        "contextual_action_support_projection_id": source_complete_evidence[
            "contextual_action_support_projection_id"
        ],
        "state_width": width,
        "action_field_width": document["action_field_width"],
        "unknown_residual_target_columns": copy.deepcopy(unknown),
        "acquisition_prefix_ground_support_labels": stop,
        "acquired_raw_transition_rows": acquired_rows,
        "acquired_raw_transition_row_count": len(acquired_rows),
        "acquired_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes(acquired_rows)
        ).hexdigest(),
        "known_partial_factor_assignments": known_assignments,
        "residual_version_spaces": spaces,
        "status_target_column": status_target,
        "mdl_minimal_terminal_candidate_frontier": terminal_frontier,
        "mdl_minimal_terminal_candidate_count": len(terminal_frontier),
        "canonical_accepting_state_prototypes": [
            list(row) for row in sorted(set(map(tuple, accepting)))
        ],
        "version_space_selection_compute_events": selection_compute,
        "source_acquisition_protocol": "CONTEXTUAL_ORDINAL_ALL_FRONTIER_V54",
        "contextual_ordinal_action_support_operator_present": any(
            candidate_row["contextual_action_support_operator_used"] is True
            for space in spaces
            for candidate_row in space["batch_exact_candidate_frontier"]
        ),
        "every_terminal_and_residual_frontier_candidate_prequentially_checked": True,
        "every_terminal_and_residual_frontier_candidate_heldout_checked": True,
        "every_batch_exact_residual_expression_retained": True,
        "multiple_residual_proposals_jointly_compiled": any(
            row["batch_exact_candidate_count"] > 1 for row in spaces
        ),
        "all_state_coordinates_represented": True,
        "only_acquisition_prefix_outcomes_used_to_fit_successor_expressions": True,
        "post_stop_heldout_rows_used_as_successor_expression_inputs": False,
        "heldout_validation_used_only_as_scientific_gate": True,
        "empirical_version_space_promoted_to_global_exact_dynamics": False,
        "complete_world_model_claimed": False,
        "abstract_plan_safety_authority_present": False,
    }
    return {
        **payload,
        "contextual_ordinal_successor_model_id": _content_id(_MODEL_DOMAIN, payload),
    }


def verify_contextual_ordinal_model_v54(model: Mapping[str, Any]) -> dict[str, Any]:
    if type(model) is not dict:
        _fail("V54 model type changed")
    payload = {
        key: value for key, value in model.items()
        if key != "contextual_ordinal_successor_model_id"
    }
    if (
        model.get("schema") != "acfqp.generic_contextual_ordinal_successor_model.v54"
        or _content_id(_MODEL_DOMAIN, payload) != model.get("contextual_ordinal_successor_model_id")
        or model.get("contextual_ordinal_action_support_operator_present") is not True
        or model.get("every_terminal_and_residual_frontier_candidate_prequentially_checked") is not True
        or model.get("post_stop_heldout_rows_used_as_successor_expression_inputs") is not False
        or model.get("empirical_version_space_promoted_to_global_exact_dynamics") is not False
        or model.get("complete_world_model_claimed") is not False
        or model.get("abstract_plan_safety_authority_present") is not False
    ):
        _fail("V54 model identity or claim boundary changed")
    rows = model.get("acquired_raw_transition_rows")
    layout = model.get("source_layout")
    supports = model.get("source_contextual_action_field_supports")
    spaces = model.get("residual_version_spaces")
    assignments = model.get("known_partial_factor_assignments")
    terminal_frontier = model.get("mdl_minimal_terminal_candidate_frontier")
    status_target = model.get("status_target_column")
    width = model.get("state_width")
    if (
        type(rows) is not list
        or not rows
        or len(rows) != model.get("acquired_raw_transition_row_count")
        or hashlib.sha256(canonical_json_bytes(rows)).hexdigest() != model.get("acquired_raw_transition_sha256")
        or type(layout) is not dict
        or type(supports) is not list
        or not supports
        or type(spaces) is not list
        or not spaces
        or type(assignments) is not list
        or type(terminal_frontier) is not list
        or not terminal_frontier
        or type(status_target) is not int
        or type(width) is not int
    ):
        _fail("V54 retained model inventory changed")
    groups = v42._groups(rows)  # noqa: SLF001
    if len(groups) != model.get("acquisition_prefix_ground_support_labels"):
        _fail("V54 acquisition-prefix label accounting changed")
    evidence = {
        "layout": copy.deepcopy(layout),
        "raw_transition_rows": copy.deepcopy(rows),
        "contextual_action_field_supports": copy.deepcopy(supports),
    }
    recomputed_spaces = []
    compute = 0
    for space in spaces:
        target = space.get("target_column") if type(space) is dict else None
        if type(target) is not int:
            _fail("V54 residual target inventory changed")
        frontier, evaluations = version_space_v54(evidence, groups, target)
        compute += evaluations
        recomputed_spaces.append(
            {
                "target_column": target,
                "batch_exact_candidate_count": len(frontier),
                "batch_exact_candidate_frontier": frontier,
            }
        )
    if (
        recomputed_spaces != spaces
        or compute != model.get("version_space_selection_compute_events")
        or model.get("multiple_residual_proposals_jointly_compiled")
        is not any(row["batch_exact_candidate_count"] > 1 for row in spaces)
    ):
        _fail("V54 retained residual version space was not exactly reconstructed")
    _terminal_frontier_exact(rows, layout, terminal_frontier, status_target)
    targets = {
        *(row.get("target_column") for row in assignments),
        *(row["target_column"] for row in spaces),
        status_target,
    }
    if targets != set(range(width)):
        _fail("V54 retained state-coordinate coverage changed")
    return copy.deepcopy(model)


__all__ = (
    "compile_contextual_ordinal_model_v54",
    "verify_contextual_ordinal_model_v54",
)
