"""Compile V49 acquisition evidence into the verified V42 model format."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.generic_relational_terminal_program_v28 import (
    evaluate_relational_terminal_program_v28,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericSuccessorProjectedModelCompilerV49Error(ValueError):
    pass


_ACQUISITION_DOMAIN = b"acfqp:generic-successor-projected-acquisition:v49\x00"
_BUNDLE_DOMAIN = b"acfqp:relation-covering-successor-projected-acquisition:v49\x00"
_MODEL_DOMAIN = b"acfqp:generic-joint-successor-version-space-model:v42\x00"


def _fail(message: str) -> NoReturn:
    raise GenericSuccessorProjectedModelCompilerV49Error(message)


def _content_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def compile_successor_projected_model_v49(
    candidate: PartialFactorCandidateV15,
    source_complete_evidence: Mapping[str, Any],
    relation_covering_acquisition: Mapping[str, Any],
) -> dict[str, Any]:
    if type(candidate) is not PartialFactorCandidateV15:
        _fail("V49 partial candidate type changed")
    if (
        type(source_complete_evidence) is not dict
        or type(relation_covering_acquisition) is not dict
    ):
        _fail("V49 source artifact type changed")
    document = candidate.public_document
    layout = source_complete_evidence.get("layout")
    unknown = source_complete_evidence.get("unknown_residual_target_columns")
    source_rows = source_complete_evidence.get("raw_transition_rows")
    if (
        type(layout) is not dict
        or layout != document.get("layout")
        or type(unknown) is not list
        or unknown != document.get("unknown_residual_target_columns")
        or unknown != sorted(set(unknown))
        or type(source_rows) is not list
        or not source_rows
    ):
        _fail("V49 source/candidate identity join changed")
    expected_schedule = schedule_relation_covering_queries_v39(
        source_complete_evidence
    )
    schedule = relation_covering_acquisition.get("query_schedule")
    acquisition = relation_covering_acquisition.get(
        "successor_projected_acquisition"
    )
    if (
        type(schedule) is not dict
        or canonical_json_bytes(schedule) != canonical_json_bytes(expected_schedule)
        or type(acquisition) is not dict
        or relation_covering_acquisition.get("schema")
        != "acfqp.relation_covering_successor_projected_acquisition.v49"
        or relation_covering_acquisition.get("query_schedule_id")
        != schedule.get("query_schedule_id")
        or relation_covering_acquisition.get(
            "successor_projected_acquisition_id"
        )
        != acquisition.get("successor_projected_acquisition_id")
    ):
        _fail("V49 acquisition bundle join changed")
    acquisition_payload = {
        key: value
        for key, value in acquisition.items()
        if key != "successor_projected_acquisition_id"
    }
    bundle_payload = {
        key: value
        for key, value in relation_covering_acquisition.items()
        if key != "relation_covering_successor_projected_acquisition_id"
    }
    if (
        _content_id(_ACQUISITION_DOMAIN, acquisition_payload)
        != acquisition.get("successor_projected_acquisition_id")
        or _content_id(_BUNDLE_DOMAIN, bundle_payload)
        != relation_covering_acquisition.get(
            "relation_covering_successor_projected_acquisition_id"
        )
        or acquisition.get("status") != "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        or acquisition.get("heldout_exact_prediction") is not True
        or acquisition.get("heldout_rows_accessed_before_stop") is not False
        or acquisition.get("terminal_frontier_evaluated_on_query_prestates")
        is not False
        or acquisition.get("projected_future_successor_support_consensus_required")
        is not True
        or acquisition.get("proposal_only_not_safety_authority") is not True
    ):
        _fail("V49 requires a content-bound heldout-validated proposal")
    groups = v42._groups(schedule["scheduled_raw_transition_rows"])  # noqa: SLF001
    stop = acquisition.get("stopped_physical_ground_support_labels")
    if type(stop) is not int or not 1 <= stop < len(groups):
        _fail("V49 acquisition stop changed")
    acquired_groups = groups[:stop]
    acquired_rows = [
        copy.deepcopy(row) for group in acquired_groups for row in group
    ]
    batches = v42._aligned_batches(layout, acquired_groups)  # noqa: SLF001
    terminal = acquisition.get("selected_terminal_program")
    if (
        type(terminal) is not dict
        or terminal.get("schema") != "acfqp.generic_relational_terminal_program.v28"
        or terminal.get("future_unseen_terminal_authority_present") is not False
        or terminal.get("terminal_program_id")
        != acquisition.get("selected_terminal_program_id")
    ):
        _fail("V49 selected terminal program changed")
    status_target = terminal.get("status_target_column")
    if type(status_target) is not int or status_target not in unknown:
        _fail("V49 status target changed")
    terminal_frontier = v42._minimal_terminal_frontier(terminal)  # noqa: SLF001
    state_order = layout["state_canonical_to_raw"]
    for row in acquired_rows:
        post = row.get("post_vector")
        if type(post) is not list or sorted(state_order) != list(range(len(post))):
            _fail("V49 acquired successor row changed")
        canonical_post = tuple(post[index] for index in state_order)
        label = v42._terminal_label(row)  # noqa: SLF001
        for terminal_row in terminal_frontier:
            prediction = evaluate_relational_terminal_program_v28(
                {
                    "schema": "acfqp.generic_relational_terminal_program.v28",
                    "decision_tree": terminal_row["decision_tree"],
                },
                canonical_post,
            )
            if (
                prediction["terminal_class"] != label
                or prediction["status_token"] != canonical_post[status_target]
            ):
                _fail("V49 terminal frontier is not exact on acquired successors")
    residual_targets = [target for target in unknown if target != status_target]
    if not residual_targets:
        _fail("V49 requires a non-status residual coordinate")
    spaces = []
    selection_compute = 0
    for target in residual_targets:
        frontier, evaluations = v42._version_space(batches, target)  # noqa: SLF001
        selection_compute += evaluations
        if not frontier:
            _fail("V49 acquired rows identify no residual expression")
        spaces.append(
            {
                "target_column": target,
                "batch_exact_candidate_count": len(frontier),
                "batch_exact_candidate_frontier": frontier,
            }
        )
    known_assignments = copy.deepcopy(list(candidate.assignments))
    modeled = {
        *(row["target_column"] for row in known_assignments),
        *residual_targets,
        status_target,
    }
    width = document.get("state_width")
    if type(width) is not int or modeled != set(range(width)):
        _fail("V49 compiled components do not cover the canonical state")
    accepting = []
    for row in acquired_rows:
        if row.get("terminal_acceptance_after") is True:
            accepting.append([row["post_vector"][index] for index in state_order])
    payload = {
        "schema": "acfqp.generic_joint_successor_version_space_model.v42",
        "partial_candidate_id": document["candidate_id"],
        "source_relation_covering_acquisition_id": relation_covering_acquisition[
            "relation_covering_successor_projected_acquisition_id"
        ],
        "source_query_schedule_id": schedule["query_schedule_id"],
        "source_learned_successor_acquisition_id": acquisition[
            "successor_projected_acquisition_id"
        ],
        "source_complete_evidence_sha256": hashlib.sha256(
            canonical_json_bytes(source_complete_evidence)
        ).hexdigest(),
        "source_layout": copy.deepcopy(layout),
        "state_width": width,
        "action_field_width": document["action_field_width"],
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
        "source_acquisition_protocol": "SUCCESSOR_PROJECTED_V49",
        "terminal_frontier_evaluated_on_query_prestates": False,
        "every_batch_exact_residual_expression_retained": True,
        "multiple_residual_proposals_jointly_compiled": any(
            row["batch_exact_candidate_count"] > 1 for row in spaces
        ),
        "all_state_coordinates_represented": True,
        "only_acquisition_prefix_outcomes_used_to_fit_successor_expressions": True,
        "post_stop_heldout_rows_used_as_successor_expression_inputs": False,
        "post_stop_heldout_validation_and_provenance_identity_present": True,
        "heldout_validation_used_only_as_scientific_gate": True,
        "empirical_version_space_promoted_to_global_exact_dynamics": False,
        "complete_world_model_claimed": False,
        "abstract_plan_safety_authority_present": False,
    }
    model = {
        **payload,
        "joint_successor_version_space_model_id": _content_id(
            _MODEL_DOMAIN, payload
        ),
    }
    v42.verify_joint_successor_version_space_model_v42(model)
    return model


__all__ = ("compile_successor_projected_model_v49",)
