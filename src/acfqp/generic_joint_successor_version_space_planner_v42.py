"""Compile and plan with a conservative joint successor version space.

V41 retained every batch-exact R00--R04 successor expression but used the
version space only as a one-step terminal-proposal guard.  This additive slice
reconstructs those frontiers from the acquisition prefix, combines every
unknown non-status coordinate with the observation-derived V15 partial
factors, and performs multi-step receding abstract search.  Every consistent
expression and every MDL-minimal terminal tree remains live during search.

The result is deliberately proposal-only.  It orders actions but cannot prove
an unseen ground transition, legality fact, or terminal outcome.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
from itertools import product
import math
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.generic_relational_terminal_program_v28 import (
    evaluate_relational_terminal_program_v28,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericJointSuccessorVersionSpacePlannerV42Error(ValueError):
    pass


_MODEL_DOMAIN = b"acfqp:generic-joint-successor-version-space-model:v42\x00"
_ACQUISITION_DOMAIN = b"acfqp:generic-learned-successor-support-acquisition:v41\x00"
_BUNDLE_DOMAIN = b"acfqp:relation-covering-learned-successor-acquisition:v41\x00"


def _fail(message: str) -> NoReturn:
    raise GenericJointSuccessorVersionSpacePlannerV42Error(message)


def _content_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _groups(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped: dict[tuple[tuple[int, ...], int], list[dict[str, Any]]] = {}
    order = []
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
            _fail("V42 raw query group changed")
        identity = (tuple(pre), key)
        if identity not in grouped:
            grouped[identity] = []
            order.append(identity)
        elif grouped[identity][0]["selected_action"] != selected:
            _fail("V42 grouped action projection changed")
        grouped[identity].append(row)
    return [grouped[key] for key in order]


def _value(
    expression: Any,
    pre: tuple[int, ...] | list[int],
    action: tuple[int, ...] | list[int],
    target: int,
    field: int | None,
    constant: int | None,
) -> tuple[int, ...]:
    if expression == ["R00"]:
        return (pre[target],)
    if expression == ["R01"] and field is not None:
        return (action[field],)
    if expression == ["R02"] and constant is not None:
        return (constant,)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R03":
        left = _value(expression[1], pre, action, target, field, constant)
        right = _value(expression[2], pre, action, target, field, constant)
        if len(left) == len(right) == 1:
            return (left[0] + right[0],)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R04":
        left = _value(expression[1], pre, action, target, field, constant)
        right = _value(expression[2], pre, action, target, field, constant)
        if len(left) == len(right) == 1:
            return tuple(sorted({left[0], right[0]}))
    _fail("V42 residual expression escaped R00--R04")


def _templates(
    rows: list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]],
    target: int,
) -> list[tuple[Any, int | None, int | None]]:
    if not rows:
        _fail("V42 version-space template source is empty")
    field_count = len(rows[0][2])
    constants = sorted(
        {
            value
            for pre, post, action in rows
            for value in (
                post[target],
                post[target] - pre[target],
                *(
                    post[target] - pre[target] - action[field]
                    for field in range(field_count)
                ),
            )
        }
    )
    result: list[tuple[Any, int | None, int | None]] = [(["R00"], None, None)]
    for field in range(field_count):
        result.extend(
            (
                (["R01"], field, None),
                (["R03", ["R00"], ["R01"]], field, None),
            )
        )
        for constant in constants:
            result.extend(
                (
                    (
                        ["R03", ["R03", ["R00"], ["R01"]], ["R02"]],
                        field,
                        constant,
                    ),
                    (
                        [
                            "R04",
                            ["R00"],
                            ["R03", ["R03", ["R00"], ["R01"]], ["R02"]],
                        ],
                        field,
                        constant,
                    ),
                )
            )
    for constant in constants:
        result.extend(
            (
                (["R02"], None, constant),
                (["R03", ["R00"], ["R02"]], None, constant),
                (["R04", ["R00"], ["R03", ["R00"], ["R02"]]], None, constant),
            )
        )
    unique = {}
    for expression, field, constant in result:
        unique.setdefault(
            (canonical_json_bytes(expression), field, constant),
            (expression, field, constant),
        )
    return list(unique.values())


def _aligned_batches(
    layout: Mapping[str, Any], groups: list[list[dict[str, Any]]]
) -> list[list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]]]:
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    if type(state_order) is not list or type(action_order) is not list:
        _fail("V42 layout projection changed")
    result = []
    for group in groups:
        batch = []
        for row in group:
            selected = row.get("selected_action")
            pre = row.get("pre_vector")
            post = row.get("post_vector")
            action = selected.get("anonymous_fields") if type(selected) is dict else None
            if (
                type(pre) is not list
                or type(post) is not list
                or type(action) is not list
                or sorted(state_order) != list(range(len(pre)))
                or len(post) != len(pre)
                or sorted(action_order) != list(range(len(action)))
            ):
                _fail("V42 acquired transition alignment changed")
            batch.append(
                (
                    tuple(pre[index] for index in state_order),
                    tuple(post[index] for index in state_order),
                    tuple(action[index] for index in action_order),
                )
            )
        result.append(batch)
    return result


def _version_space(
    batches: list[list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]]],
    target: int,
) -> tuple[list[dict[str, Any]], int]:
    rows = [row for batch in batches for row in batch]
    frontier = []
    evaluations = 0
    for expression, field, constant in _templates(rows, target):
        exact = True
        for batch in batches:
            predicted = _value(
                expression, batch[0][0], batch[0][2], target, field, constant
            )
            observed = tuple(sorted({post[target] for _pre, post, _action in batch}))
            evaluations += 1
            if predicted != observed:
                exact = False
                break
        if exact:
            frontier.append(
                {
                    "normalized_expression": expression,
                    "action_field_binding": field,
                    "anonymous_integer_constant_binding": constant,
                }
            )
    frontier.sort(key=canonical_json_bytes)
    return frontier, evaluations


def _minimal_terminal_frontier(program: Mapping[str, Any]) -> list[dict[str, Any]]:
    frontier = program.get("decision_tree_candidate_frontier")
    if type(frontier) is not list or not frontier:
        _fail("V42 terminal frontier changed")
    nodes = [row.get("decision_tree_node_count") for row in frontier]
    sizes = [row.get("decision_tree_byte_count") for row in frontier]
    if any(type(value) is not int or value <= 0 for value in (*nodes, *sizes)):
        _fail("V42 terminal MDL inventory changed")
    minimum_nodes = min(nodes)
    candidates = [row for row in frontier if row["decision_tree_node_count"] == minimum_nodes]
    minimum_bytes = min(row["decision_tree_byte_count"] for row in candidates)
    result = [copy.deepcopy(row) for row in candidates if row["decision_tree_byte_count"] == minimum_bytes]
    if not result or any(type(row.get("decision_tree")) is not dict for row in result):
        _fail("V42 MDL-minimal terminal frontier changed")
    return result


def _terminal_label(row: Mapping[str, Any]) -> str:
    legal = row.get("legal_action_keys_after")
    terminal = row.get("terminal_acceptance_after")
    if type(legal) is not list:
        _fail("V42 terminal label evidence changed")
    if legal:
        if terminal is not None:
            _fail("V42 active row carried a terminal label")
        return "ACTIVE"
    if terminal is True:
        return "ACCEPT"
    if terminal is False:
        return "REJECT"
    _fail("V42 terminal row omitted its label")


def compile_joint_successor_version_space_model_v42(
    candidate: PartialFactorCandidateV15,
    source_complete_evidence: Mapping[str, Any],
    relation_covering_acquisition: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze a reusable model using only the V41 acquisition prefix."""
    if type(candidate) is not PartialFactorCandidateV15:
        _fail("V42 partial candidate type changed")
    if type(source_complete_evidence) is not dict or type(relation_covering_acquisition) is not dict:
        _fail("V42 source artifact type changed")
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
        _fail("V42 source/candidate identity join changed")
    expected_schedule = schedule_relation_covering_queries_v39(source_complete_evidence)
    schedule = relation_covering_acquisition.get("query_schedule")
    acquisition = relation_covering_acquisition.get("learned_successor_acquisition")
    if (
        type(schedule) is not dict
        or canonical_json_bytes(schedule) != canonical_json_bytes(expected_schedule)
        or type(acquisition) is not dict
        or relation_covering_acquisition.get("schema")
        != "acfqp.relation_covering_learned_successor_acquisition.v41"
        or relation_covering_acquisition.get("query_schedule_id")
        != schedule.get("query_schedule_id")
        or relation_covering_acquisition.get("learned_successor_acquisition_id")
        != acquisition.get("learned_successor_acquisition_id")
    ):
        _fail("V42 V41 bundle join changed")
    acquisition_payload = {
        key: value for key, value in acquisition.items() if key != "learned_successor_acquisition_id"
    }
    bundle_payload = {
        key: value for key, value in relation_covering_acquisition.items()
        if key != "relation_covering_acquisition_id"
    }
    if (
        _content_id(_ACQUISITION_DOMAIN, acquisition_payload)
        != acquisition.get("learned_successor_acquisition_id")
        or _content_id(_BUNDLE_DOMAIN, bundle_payload)
        != relation_covering_acquisition.get("relation_covering_acquisition_id")
        or acquisition.get("status") != "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        or acquisition.get("heldout_exact_prediction") is not True
        or acquisition.get("heldout_rows_accessed_before_stop") is not False
        or acquisition.get("proposal_only_not_safety_authority") is not True
    ):
        _fail("V42 requires a content-bound held-out-validated V41 proposal")
    groups = _groups(schedule["scheduled_raw_transition_rows"])
    stop = acquisition.get("stopped_physical_ground_support_labels")
    if type(stop) is not int or not 1 <= stop < len(groups):
        _fail("V42 acquisition stop changed")
    acquired_groups = groups[:stop]
    acquired_rows = [copy.deepcopy(row) for group in acquired_groups for row in group]
    batches = _aligned_batches(layout, acquired_groups)
    terminal = acquisition.get("selected_terminal_program")
    if (
        type(terminal) is not dict
        or terminal.get("schema") != "acfqp.generic_relational_terminal_program.v28"
        or terminal.get("future_unseen_terminal_authority_present") is not False
        or terminal.get("terminal_program_id")
        != acquisition.get("selected_terminal_program_id")
    ):
        _fail("V42 selected terminal program changed")
    status_target = terminal.get("status_target_column")
    if type(status_target) is not int or status_target not in unknown:
        _fail("V42 status target changed")
    terminal_frontier = _minimal_terminal_frontier(terminal)
    state_order = layout["state_canonical_to_raw"]
    for row in acquired_rows:
        post = row.get("post_vector")
        if type(post) is not list or sorted(state_order) != list(range(len(post))):
            _fail("V42 acquired successor row changed")
        canonical_post = tuple(post[index] for index in state_order)
        label = _terminal_label(row)
        for terminal_row in terminal_frontier:
            view = {
                "schema": "acfqp.generic_relational_terminal_program.v28",
                "decision_tree": terminal_row["decision_tree"],
            }
            prediction = evaluate_relational_terminal_program_v28(view, canonical_post)
            if (
                prediction["terminal_class"] != label
                or prediction["status_token"] != canonical_post[status_target]
            ):
                _fail("V42 terminal frontier is not exact on the acquisition prefix")
    residual_targets = [target for target in unknown if target != status_target]
    if not residual_targets:
        _fail("V42 requires at least one non-status residual coordinate")
    spaces = []
    selection_compute = 0
    for target in residual_targets:
        frontier, evaluations = _version_space(batches, target)
        selection_compute += evaluations
        if not frontier:
            _fail("V42 acquired rows identify no batch-exact residual expression")
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
        _fail("V42 compiled components do not cover the canonical state")
    accepting = []
    for row in acquired_rows:
        if row.get("terminal_acceptance_after") is True:
            accepting.append([row["post_vector"][index] for index in state_order])
    payload = {
        "schema": "acfqp.generic_joint_successor_version_space_model.v42",
        "partial_candidate_id": document["candidate_id"],
        "source_relation_covering_acquisition_id": relation_covering_acquisition[
            "relation_covering_acquisition_id"
        ],
        "source_query_schedule_id": schedule["query_schedule_id"],
        "source_learned_successor_acquisition_id": acquisition[
            "learned_successor_acquisition_id"
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
        "canonical_accepting_state_prototypes": sorted(set(map(tuple, accepting))),
        "version_space_selection_compute_events": selection_compute,
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
    payload["canonical_accepting_state_prototypes"] = [
        list(row) for row in payload["canonical_accepting_state_prototypes"]
    ]
    return {
        **payload,
        "joint_successor_version_space_model_id": _content_id(_MODEL_DOMAIN, payload),
    }


def verify_joint_successor_version_space_model_v42(
    model: Mapping[str, Any],
) -> dict[str, Any]:
    if type(model) is not dict:
        _fail("V42 model type changed")
    payload = {
        key: value for key, value in model.items()
        if key != "joint_successor_version_space_model_id"
    }
    if (
        model.get("schema") != "acfqp.generic_joint_successor_version_space_model.v42"
        or _content_id(_MODEL_DOMAIN, payload)
        != model.get("joint_successor_version_space_model_id")
        or model.get("all_state_coordinates_represented") is not True
        or model.get("post_stop_heldout_rows_used_as_successor_expression_inputs")
        is not False
        or model.get("empirical_version_space_promoted_to_global_exact_dynamics") is not False
        or model.get("complete_world_model_claimed") is not False
        or model.get("abstract_plan_safety_authority_present") is not False
    ):
        _fail("V42 model identity or claim boundary changed")
    rows = model.get("acquired_raw_transition_rows")
    layout = model.get("source_layout")
    spaces = model.get("residual_version_spaces")
    assignments = model.get("known_partial_factor_assignments")
    terminal_frontier = model.get("mdl_minimal_terminal_candidate_frontier")
    status_target = model.get("status_target_column")
    width = model.get("state_width")
    if (
        type(rows) is not list
        or not rows
        or len(rows) != model.get("acquired_raw_transition_row_count")
        or hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
        != model.get("acquired_raw_transition_sha256")
        or type(layout) is not dict
        or type(spaces) is not list
        or not spaces
        or type(assignments) is not list
        or type(terminal_frontier) is not list
        or not terminal_frontier
        or type(status_target) is not int
        or type(width) is not int
    ):
        _fail("V42 retained model inventory changed")
    groups = _groups(rows)
    if len(groups) != model.get("acquisition_prefix_ground_support_labels"):
        _fail("V42 acquisition-prefix label accounting changed")
    batches = _aligned_batches(layout, groups)
    recomputed_spaces = []
    recomputed_compute = 0
    for space in spaces:
        target = space.get("target_column") if type(space) is dict else None
        if type(target) is not int:
            _fail("V42 residual target inventory changed")
        frontier, evaluations = _version_space(batches, target)
        recomputed_compute += evaluations
        recomputed_spaces.append(
            {
                "target_column": target,
                "batch_exact_candidate_count": len(frontier),
                "batch_exact_candidate_frontier": frontier,
            }
        )
    if (
        recomputed_spaces != spaces
        or recomputed_compute != model.get("version_space_selection_compute_events")
        or model.get("multiple_residual_proposals_jointly_compiled")
        is not any(row["batch_exact_candidate_count"] > 1 for row in spaces)
    ):
        _fail("V42 retained residual version space was not exactly reconstructed")
    state_order = layout.get("state_canonical_to_raw")
    if type(state_order) is not list:
        _fail("V42 retained state projection changed")
    for row in rows:
        post = row.get("post_vector") if type(row) is dict else None
        if type(post) is not list or sorted(state_order) != list(range(len(post))):
            _fail("V42 retained terminal row changed")
        canonical_post = tuple(post[index] for index in state_order)
        label = _terminal_label(row)
        for terminal_row in terminal_frontier:
            view = {
                "schema": "acfqp.generic_relational_terminal_program.v28",
                "decision_tree": terminal_row.get("decision_tree"),
            }
            prediction = evaluate_relational_terminal_program_v28(view, canonical_post)
            if (
                prediction.get("terminal_class") != label
                or prediction.get("status_token") != canonical_post[status_target]
            ):
                _fail("V42 retained terminal frontier replay changed")
    targets = {
        *(row.get("target_column") for row in assignments),
        *(row["target_column"] for row in spaces),
        status_target,
    }
    if targets != set(range(width)):
        _fail("V42 retained state-coordinate coverage changed")
    return copy.deepcopy(model)


def _partial_support(
    assignment: Mapping[str, Any], state: tuple[int, ...], action: tuple[int, ...]
) -> tuple[int, ...]:
    expression = assignment.get("expression")
    if type(expression) is not list or not expression:
        _fail("V42 partial expression changed")
    if expression[0] == "E00":
        return (state[expression[1]],)
    if expression[0] == "E01":
        return (action[expression[1]],)
    if expression[0] == "E07":
        target = expression[1][1]
        field = expression[2][2][1]
        return tuple(sorted({state[target], state[target] + action[field]}))
    _fail("V42 partial expression escaped the retained V15 grammar")


def plan_joint_successor_version_space_v42(
    model: Mapping[str, Any],
    target_candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    *,
    maximum_depth: int,
    maximum_robust_state_depth_evaluations: int = 4096,
    maximum_support_branch_evaluations: int = 1_000_000,
    support_feasible_beam_width: int = 64,
) -> dict[str, Any]:
    """Plan while preserving every residual expression and terminal tree."""
    verified = verify_joint_successor_version_space_model_v42(model)
    if (
        type(target_candidate) is not PartialFactorCandidateV15
        or type(catalogue) is not tuple
        or not catalogue
        or type(initial_raw_state) is not tuple
        or maximum_depth <= 0
        or maximum_robust_state_depth_evaluations <= 0
        or maximum_support_branch_evaluations <= 0
        or support_feasible_beam_width <= 0
    ):
        _fail("V42 planning inventory changed")
    target = target_candidate.public_document
    source_layout = verified["source_layout"]
    target_layout = target.get("layout")
    if (
        type(target_layout) is not dict
        or target.get("state_width") != verified["state_width"]
        or target.get("action_field_width") != verified["action_field_width"]
        or target.get("unknown_residual_target_columns")
        != sorted(
            [
                *[
                    row["target_column"]
                    for row in verified["residual_version_spaces"]
                ],
                verified["status_target_column"],
            ]
        )
        or target.get("compiled_factor_assignments")
        != verified["known_partial_factor_assignments"]
        or target_layout.get("state_structural_colors")
        != source_layout.get("state_structural_colors")
        or target_layout.get("action_structural_colors")
        != source_layout.get("action_structural_colors")
    ):
        _fail("V42 target occurrence is not structurally compatible with the model")
    state_order = target_layout.get("state_canonical_to_raw")
    action_order = target_layout.get("action_canonical_to_raw")
    if (
        type(state_order) is not list
        or sorted(state_order) != list(range(len(initial_raw_state)))
        or type(action_order) is not list
    ):
        _fail("V42 target layout projection changed")
    initial = tuple(initial_raw_state[index] for index in state_order)
    actions = tuple(
        FlatRawActionV4(
            action.key,
            tuple(action.fields[index] for index in action_order),
        )
        for action in catalogue
    )
    if len({action.key for action in actions}) != len(actions):
        _fail("V42 target action catalogue changed")
    partial = {
        row["target_column"]: row
        for row in verified["known_partial_factor_assignments"]
    }
    residual = {
        row["target_column"]: row["batch_exact_candidate_frontier"]
        for row in verified["residual_version_spaces"]
    }
    status_target = verified["status_target_column"]
    frontier = verified["mdl_minimal_terminal_candidate_frontier"]

    def terminal_predictions(state: tuple[int, ...]) -> tuple[tuple[str, int], ...]:
        values = set()
        for row in frontier:
            view = {
                "schema": "acfqp.generic_relational_terminal_program.v28",
                "decision_tree": row["decision_tree"],
            }
            result = evaluate_relational_terminal_program_v28(view, state)
            classification = result.get("terminal_class")
            token = result.get("status_token")
            if classification not in ("ACTIVE", "ACCEPT", "REJECT") or type(token) is not int:
                _fail("V42 terminal frontier prediction changed")
            values.add((classification, token))
        return tuple(sorted(values))

    branch_evaluations = 0
    maximum_branch_width = 0

    def successors(
        state: tuple[int, ...], action: FlatRawActionV4
    ) -> tuple[tuple[int, ...], ...]:
        nonlocal maximum_branch_width
        supports = []
        targets = sorted((*partial, *residual))
        for column in targets:
            if column in partial:
                values = _partial_support(partial[column], state, action.fields)
            else:
                values_set = set()
                for expression in residual[column]:
                    values_set.update(
                        _value(
                            expression["normalized_expression"],
                            state,
                            action.fields,
                            column,
                            expression.get("action_field_binding"),
                            expression.get("anonymous_integer_constant_binding"),
                        )
                    )
                values = tuple(sorted(values_set))
            if not values:
                _fail("V42 compiled coordinate support became empty")
            supports.append(values)
        width = math.prod(len(values) for values in supports)
        if width > maximum_support_branch_evaluations:
            _fail("V42 one-step support crossed its frozen compute cap")
        result = set()
        for values in product(*supports):
            projected = list(state)
            for column, value in zip(targets, values, strict=True):
                projected[column] = value
            for _classification, token in terminal_predictions(tuple(projected)):
                row = list(projected)
                row[status_target] = token
                result.add(tuple(row))
        maximum_branch_width = max(maximum_branch_width, len(result))
        return tuple(sorted(result))

    def consensus_class(state: tuple[int, ...]) -> str | None:
        classes = {classification for classification, _token in terminal_predictions(state)}
        return next(iter(classes)) if len(classes) == 1 else None

    robust_calls = 0
    robust_truncated = False
    visiting: set[tuple[tuple[int, ...], int]] = set()
    policy: dict[tuple[int, ...], int] = {}

    @lru_cache(maxsize=None)
    def robust(state: tuple[int, ...], depth: int) -> bool:
        nonlocal branch_evaluations, robust_calls, robust_truncated
        robust_calls += 1
        classification = consensus_class(state)
        if classification == "ACCEPT":
            return True
        if classification in (None, "REJECT"):
            return False
        if (
            depth == 0
            or (state, depth) in visiting
            or robust_calls > maximum_robust_state_depth_evaluations
            or branch_evaluations >= maximum_support_branch_evaluations
        ):
            robust_truncated = (
                robust_calls > maximum_robust_state_depth_evaluations
                or branch_evaluations >= maximum_support_branch_evaluations
            )
            return False
        visiting.add((state, depth))
        for action in actions:
            branch = successors(state, action)
            branch_evaluations += len(branch)
            if branch_evaluations > maximum_support_branch_evaluations:
                robust_truncated = True
                visiting.remove((state, depth))
                return False
            progressing = tuple(value for value in branch if value != state)
            if progressing and all(robust(value, depth - 1) for value in progressing):
                policy[state] = action.key
                visiting.remove((state, depth))
                return True
        visiting.remove((state, depth))
        return False

    closed = robust(initial, maximum_depth)
    support_path: list[int] = []
    if not closed:
        predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
            initial: None
        }
        goal = None
        frontier_states = (initial,)
        prototypes = tuple(tuple(row) for row in verified["canonical_accepting_state_prototypes"])

        def distance(state: tuple[int, ...]) -> int:
            if not prototypes:
                return 0
            return min(
                sum(abs(left - right) for left, right in zip(state, prototype, strict=True))
                for prototype in prototypes
            )

        for _depth in range(maximum_depth):
            next_rows: dict[tuple[int, ...], tuple[tuple[int, ...], int]] = {}
            for state in frontier_states:
                if consensus_class(state) != "ACTIVE":
                    continue
                for action in actions:
                    branch = successors(state, action)
                    branch_evaluations += len(branch)
                    if branch_evaluations > maximum_support_branch_evaluations:
                        _fail("V42 support-feasible search crossed its compute cap")
                    for successor in branch:
                        classification = consensus_class(successor)
                        if successor == state or classification in (None, "REJECT") or successor in predecessor:
                            continue
                        edge = (state, action.key)
                        previous = next_rows.get(successor)
                        if previous is None or edge < previous:
                            next_rows[successor] = edge
            ranked = sorted(next_rows, key=lambda row: (distance(row), row))
            frontier_states = tuple(ranked[:support_feasible_beam_width])
            for successor in frontier_states:
                predecessor[successor] = next_rows[successor]
                if consensus_class(successor) == "ACCEPT":
                    goal = successor
                    break
            if goal is not None or not frontier_states:
                break
        if goal is None:
            _fail("V42 joint version space found no conservative abstract continuation")
        cursor = goal
        reversed_actions = []
        while predecessor[cursor] is not None:
            parent, key = predecessor[cursor]
            reversed_actions.append(key)
            cursor = parent
        support_path = list(reversed(reversed_actions))
    first = policy.get(initial) if closed else support_path[0] if support_path else None
    if type(first) is not int:
        _fail("V42 joint version-space policy omitted its initial action")
    return {
        "schema": "acfqp.generic_joint_successor_version_space_plan.v42",
        "joint_successor_version_space_model_id": verified[
            "joint_successor_version_space_model_id"
        ],
        "target_partial_candidate_id": target["candidate_id"],
        "initial_action_key": first,
        "support_feasible_action_keys": support_path,
        "maximum_depth": maximum_depth,
        "residual_target_count": len(residual),
        "retained_residual_expression_count": sum(len(rows) for rows in residual.values()),
        "retained_terminal_tree_count": len(frontier),
        "abstract_state_depth_cache_count": robust.cache_info().currsize,
        "abstract_support_branch_evaluations": branch_evaluations,
        "maximum_joint_successor_support_width": maximum_branch_width,
        "robust_all_version_space_branches_closed": closed,
        "robust_search_resource_cap_reached": robust_truncated,
        "support_feasible_receding_plan_found": True,
        "all_residual_version_spaces_jointly_propagated": True,
        "all_mdl_minimal_terminal_trees_jointly_propagated": True,
        "ground_transition_accessed_during_abstract_search": False,
        "abstract_plan_used_as_safety_authority": False,
        "empirical_version_space_promoted_to_global_exact_dynamics": False,
        "complete_world_model_claimed": False,
    }


__all__ = (
    "GenericJointSuccessorVersionSpacePlannerV42Error",
    "compile_joint_successor_version_space_model_v42",
    "plan_joint_successor_version_space_v42",
    "verify_joint_successor_version_space_model_v42",
)
