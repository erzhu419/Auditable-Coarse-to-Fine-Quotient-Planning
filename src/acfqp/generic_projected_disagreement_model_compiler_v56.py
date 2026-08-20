"""Compile V56 adaptively ordered evidence into a contextual world model."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import generic_contextual_ordinal_model_compiler_v54 as v54_model
from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp.generic_contextual_ordinal_residual_v54 import version_space_v54
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


class GenericProjectedDisagreementModelCompilerV56Error(ValueError):
    pass


_ACQUISITION_DOMAIN = b"acfqp:generic-projected-disagreement-acquisition:v56\x00"
_BUNDLE_DOMAIN = b"acfqp:projected-disagreement-contextual-acquisition:v56\x00"
_MODEL_DOMAIN = b"acfqp:generic-projected-disagreement-successor-model:v56\x00"
_V54_MODEL_DOMAIN = b"acfqp:generic-contextual-ordinal-successor-model:v54\x00"


def _fail(message: str) -> NoReturn:
    raise GenericProjectedDisagreementModelCompilerV56Error(message)


def _content_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def compile_projected_disagreement_model_v56(
    candidate: PartialFactorCandidateV15,
    source_complete_evidence: Mapping[str, Any],
    acquisition_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    if type(candidate) is not PartialFactorCandidateV15:
        _fail("V56 partial candidate type changed")
    if type(source_complete_evidence) is not dict or type(acquisition_bundle) is not dict:
        _fail("V56 source artifact type changed")
    document = candidate.public_document
    layout = source_complete_evidence.get("layout")
    unknown = source_complete_evidence.get("unknown_residual_target_columns")
    supports = source_complete_evidence.get("contextual_action_field_supports")
    if (
        type(layout) is not dict
        or layout != document.get("layout")
        or type(unknown) is not list
        or unknown != document.get("unknown_residual_target_columns")
        or type(supports) is not list
        or not supports
        or source_complete_evidence.get("known_partial_factor_assignments")
        != document.get("compiled_factor_assignments")
    ):
        _fail("V56 source/candidate identity join changed")
    acquisition = acquisition_bundle.get("projected_disagreement_acquisition")
    if (
        type(acquisition) is not dict
        or acquisition_bundle.get("schema")
        != "acfqp.projected_disagreement_contextual_acquisition.v56"
        or acquisition_bundle.get("projected_disagreement_acquisition_id")
        != acquisition.get("projected_disagreement_acquisition_id")
    ):
        _fail("V56 acquisition bundle join changed")
    acquisition_payload = {
        key: value for key, value in acquisition.items()
        if key != "projected_disagreement_acquisition_id"
    }
    bundle_payload = {
        key: value for key, value in acquisition_bundle.items()
        if key != "projected_disagreement_contextual_acquisition_id"
    }
    if (
        _content_id(_ACQUISITION_DOMAIN, acquisition_payload)
        != acquisition.get("projected_disagreement_acquisition_id")
        or _content_id(_BUNDLE_DOMAIN, bundle_payload)
        != acquisition_bundle.get("projected_disagreement_contextual_acquisition_id")
        or acquisition.get("status") != "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        or acquisition.get("heldout_exact_prediction") is not True
        or acquisition.get("heldout_rows_accessed_before_stop") is not False
        or acquisition.get("candidate_disagreement_scheduling_uses_only_abstract_successor_support") is not True
        or acquisition.get("unacquired_post_state_or_label_accessed_by_query_selection") is not False
        or acquisition.get("every_retained_terminal_frontier_candidate_prequentially_checked") is not True
        or acquisition.get("every_retained_residual_frontier_candidate_prequentially_checked") is not True
        or acquisition.get("proposal_only_not_safety_authority") is not True
    ):
        _fail("V56 requires a content-bound heldout-validated adaptive proposal")
    rows = acquisition.get("executed_raw_transition_rows")
    ledger = acquisition.get("adaptive_query_selection_ledger")
    stop = acquisition.get("stopped_physical_ground_support_labels")
    if type(rows) is not list or not rows or type(ledger) is not list or type(stop) is not int:
        _fail("V56 executed acquisition prefix changed")
    groups = v42._groups(rows)  # noqa: SLF001
    if len(groups) != stop or len(ledger) != stop:
        _fail("V56 adaptive-prefix accounting changed")
    terminal = acquisition.get("selected_terminal_program")
    status_target = terminal.get("status_target_column") if type(terminal) is dict else None
    if (
        type(terminal) is not dict
        or terminal.get("schema") != "acfqp.generic_relational_terminal_program.v28"
        or terminal.get("future_unseen_terminal_authority_present") is not False
        or terminal.get("terminal_program_id") != acquisition.get("selected_terminal_program_id")
        or type(status_target) is not int
        or status_target not in unknown
    ):
        _fail("V56 selected terminal program changed")
    terminal_frontier = v42._minimal_terminal_frontier(terminal)  # noqa: SLF001
    v54_model._terminal_frontier_exact(  # noqa: SLF001
        rows, layout, terminal_frontier, status_target
    )
    spaces = []
    selection_compute = 0
    for target in unknown:
        if target == status_target:
            continue
        frontier, evaluations = version_space_v54(source_complete_evidence, groups, target)
        selection_compute += evaluations
        if not frontier:
            _fail("V56 acquired rows identify no residual expression")
        spaces.append(
            {
                "target_column": target,
                "batch_exact_candidate_count": len(frontier),
                "batch_exact_candidate_frontier": frontier,
            }
        )
    if not spaces or spaces != acquisition.get("selected_residual_version_spaces"):
        _fail("V56 frozen residual frontier changed before compilation")
    assignments = copy.deepcopy(list(candidate.assignments))
    width = document.get("state_width")
    modeled = {
        *(row["target_column"] for row in assignments),
        *(row["target_column"] for row in spaces),
        status_target,
    }
    if type(width) is not int or modeled != set(range(width)):
        _fail("V56 compiled components do not cover the canonical state")
    state_order = layout["state_canonical_to_raw"]
    accepting = [
        [row["post_vector"][index] for index in state_order]
        for row in rows
        if row.get("terminal_acceptance_after") is True
    ]
    payload = {
        "schema": "acfqp.generic_projected_disagreement_successor_model.v56",
        "partial_candidate_id": document["candidate_id"],
        "source_projected_disagreement_acquisition_id": acquisition_bundle[
            "projected_disagreement_contextual_acquisition_id"
        ],
        "source_query_schedule_id": acquisition[
            "source_context_stratified_query_schedule_id"
        ],
        "source_contextual_ordinal_acquisition_id": acquisition[
            "projected_disagreement_acquisition_id"
        ],
        "source_complete_evidence_sha256": hashlib.sha256(
            canonical_json_bytes(source_complete_evidence)
        ).hexdigest(),
        "source_layout": copy.deepcopy(layout),
        "source_contextual_action_field_supports": copy.deepcopy(supports),
        "contextual_action_support_projection_id": source_complete_evidence[
            "contextual_action_support_projection_id"
        ],
        "state_width": width,
        "action_field_width": document["action_field_width"],
        "unknown_residual_target_columns": copy.deepcopy(unknown),
        "acquisition_prefix_ground_support_labels": stop,
        "acquired_raw_transition_rows": copy.deepcopy(rows),
        "acquired_raw_transition_row_count": len(rows),
        "acquired_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes(rows)
        ).hexdigest(),
        "known_partial_factor_assignments": assignments,
        "residual_version_spaces": spaces,
        "status_target_column": status_target,
        "mdl_minimal_terminal_candidate_frontier": terminal_frontier,
        "mdl_minimal_terminal_candidate_count": len(terminal_frontier),
        "canonical_accepting_state_prototypes": [
            list(row) for row in sorted(set(map(tuple, accepting)))
        ],
        "version_space_selection_compute_events": selection_compute,
        "source_acquisition_protocol": "PROJECTED_DISAGREEMENT_V56",
        "projected_candidate_disagreement_schedule_used": True,
        "query_selection_projection_compute_events": acquisition[
            "query_selection_projection_compute_events"
        ],
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
        "projected_disagreement_successor_model_id": _content_id(
            _MODEL_DOMAIN, payload
        ),
    }


def _v54_view(model: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        key: copy.deepcopy(value)
        for key, value in model.items()
        if key != "projected_disagreement_successor_model_id"
    }
    payload["schema"] = "acfqp.generic_contextual_ordinal_successor_model.v54"
    payload["source_relation_covering_acquisition_id"] = payload.pop(
        "source_projected_disagreement_acquisition_id"
    )
    payload.pop("projected_candidate_disagreement_schedule_used")
    payload.pop("query_selection_projection_compute_events")
    return {
        **payload,
        "contextual_ordinal_successor_model_id": _content_id(
            _V54_MODEL_DOMAIN, payload
        ),
    }


def verify_projected_disagreement_model_v56(model: Mapping[str, Any]) -> dict[str, Any]:
    if type(model) is not dict:
        _fail("V56 model type changed")
    payload = {
        key: value for key, value in model.items()
        if key != "projected_disagreement_successor_model_id"
    }
    if (
        model.get("schema") != "acfqp.generic_projected_disagreement_successor_model.v56"
        or _content_id(_MODEL_DOMAIN, payload)
        != model.get("projected_disagreement_successor_model_id")
        or model.get("projected_candidate_disagreement_schedule_used") is not True
        or model.get("contextual_ordinal_action_support_operator_present") is not True
        or model.get("complete_world_model_claimed") is not False
        or model.get("abstract_plan_safety_authority_present") is not False
    ):
        _fail("V56 model identity or claim boundary changed")
    v54_model.verify_contextual_ordinal_model_v54(_v54_view(model))
    return copy.deepcopy(model)


__all__ = (
    "compile_projected_disagreement_model_v56",
    "verify_projected_disagreement_model_v56",
)
