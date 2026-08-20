"""Learned successor-support guard for role-free terminal acquisition.

The remaining V40 failure cannot be resolved from pre-state geometry alone.
V41 learns a coordinate-wise partial successor-support version space from
*acquired* raw transitions using the generic R00--R04 expression grammar.  It
projects the union of every batch-exact expression over the still-unacquired
query pre-states/actions and permits a terminal proposal only when its exact
candidate frontier agrees on every predicted successor support state.  No
unacquired successor or label is read.

Both the successor model and terminal program remain empirical proposals.  The
guard is calibration evidence only and never discharges a safety certificate.
"""

from __future__ import annotations

import copy
import hashlib
from itertools import product
import math
from typing import Any, Mapping, NoReturn

from acfqp import generic_adaptive_role_free_terminal_acquisition_v35 as v35
from acfqp import generic_prequential_role_free_acquisition_v37 as v37
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.generic_semantic_coverage_acquisition_v38 import (
    TERMINAL_CLASS_UNIVERSE_V38,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericLearnedSuccessorSupportAcquisitionV41Error(ValueError):
    pass


RETAINED_V71_DEVELOPMENT_DIAGNOSTIC_V41 = {
    "predecessor_campaign_id": "a8a9ebead0bcfeb1587be1a6b21ddb11189ec74e26d871ab5ada0ec279261e17",
    "occurrence_count": 6,
    "role_free_factor_prior_on": {
        "heldout_validated_occurrence_count": 4,
        "heldout_failed_noncertificate_occurrence_count": 0,
        "abstained_occurrence_count": 2,
        "counterfactual_consumed_labels": 213,
        "post_stop_heldout_audit_labels": 156,
    },
    "strict_no_role_free_factor_prior": {
        "heldout_validated_occurrence_count": 3,
        "heldout_failed_noncertificate_occurrence_count": 0,
        "abstained_occurrence_count": 3,
        "counterfactual_consumed_labels": 250,
        "post_stop_heldout_audit_labels": 119,
    },
    "jointly_heldout_validated_occurrence_count": 3,
    "jointly_comparable_prior_labels": 61,
    "jointly_comparable_strict_labels": 95,
    "jointly_comparable_label_reduction": 34,
    "development_only_not_preregistered": True,
    "fresh_confirmatory_sample_tax_claim_present": False,
}


def _fail(message: str) -> NoReturn:
    raise GenericLearnedSuccessorSupportAcquisitionV41Error(message)


def _value(
    expression: Any,
    pre: list[int],
    action: list[int],
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
    _fail("V41 successor expression escaped the finite grammar")


def _tree_columns(node: Mapping[str, Any]) -> set[int]:
    if node.get("kind") == "LEAF":
        return set()
    if node.get("kind") != "RELATION":
        _fail("V41 terminal dependency tree changed")
    left, right = node.get("left_column"), node.get("right_column")
    if type(left) is not int or type(right) is not int:
        _fail("V41 terminal dependency columns changed")
    return {
        left,
        right,
        *_tree_columns(node["when_true"]),
        *_tree_columns(node["when_false"]),
    }


def _program_dependency_columns(program: Mapping[str, Any]) -> list[int]:
    target = program.get("status_target_column")
    frontier = program.get("decision_tree_candidate_frontier")
    if type(target) is not int or type(frontier) is not list or not frontier:
        _fail("V41 terminal dependency inventory changed")
    # The decision tree returns the status token; it never reads the status
    # coordinate.  Modeling that coordinate as an input dependency would be a
    # circular requirement and would incorrectly demand that the successor
    # model already know the terminal answer the tree is meant to derive.
    columns: set[int] = set()
    for row in frontier:
        tree = row.get("decision_tree") if type(row) is dict else None
        if type(tree) is not dict:
            _fail("V41 terminal frontier tree changed")
        columns.update(_tree_columns(tree))
    if target in columns:
        _fail("V41 terminal decision tree read its own status target")
    return sorted(columns)


def _mdl_minimal_program_view(program: Mapping[str, Any]) -> dict[str, Any]:
    frontier = program.get("decision_tree_candidate_frontier")
    if type(frontier) is not list or not frontier:
        _fail("V41 MDL frontier changed")
    minimum_nodes = min(row.get("decision_tree_node_count") for row in frontier)
    node_minimal = [
        row for row in frontier if row.get("decision_tree_node_count") == minimum_nodes
    ]
    minimum_bytes = min(row.get("decision_tree_byte_count") for row in node_minimal)
    minimal = [
        row for row in node_minimal if row.get("decision_tree_byte_count") == minimum_bytes
    ]
    if not minimal:
        raise AssertionError  # pragma: no cover
    return {
        **program,
        "decision_tree": minimal[0]["decision_tree"],
        "decision_tree_node_count": minimal[0]["decision_tree_node_count"],
        "decision_tree_candidate_frontier": minimal,
        "decision_tree_candidate_count": len(minimal),
    }


def _aligned_batches(
    layout: Mapping[str, Any], rows: list[dict[str, Any]]
) -> list[list[tuple[list[int], list[int], list[int]]]]:
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    if type(state_order) is not list or type(action_order) is not list:
        _fail("V41 anonymous layout changed")
    grouped: dict[tuple[Any, ...], list[tuple[list[int], list[int], list[int]]]] = {}
    order = []
    for row in rows:
        selected = row.get("selected_action") if type(row) is dict else None
        pre_raw = row.get("pre_vector") if type(row) is dict else None
        post_raw = row.get("post_vector") if type(row) is dict else None
        action_raw = selected.get("anonymous_fields") if type(selected) is dict else None
        key = (
            tuple(pre_raw or ()),
            selected.get("action_key") if type(selected) is dict else None,
        )
        if (
            type(pre_raw) is not list
            or type(post_raw) is not list
            or type(action_raw) is not list
            or len(pre_raw) != len(post_raw)
            or sorted(state_order) != list(range(len(pre_raw)))
            or sorted(action_order) != list(range(len(action_raw)))
            or type(key[1]) is not int
        ):
            _fail("V41 acquired transition row changed")
        aligned = (
            [pre_raw[index] for index in state_order],
            [post_raw[index] for index in state_order],
            [action_raw[index] for index in action_order],
        )
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(aligned)
    return [grouped[key] for key in order]


def _residual_templates(
    rows: list[tuple[list[int], list[int], list[int]]], target: int
) -> list[tuple[Any, int | None, int | None]]:
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
    templates: list[tuple[Any, int | None, int | None]] = [
        (["R00"], None, None)
    ]
    for field in range(field_count):
        templates.extend(
            (
                (["R01"], field, None),
                (["R03", ["R00"], ["R01"]], field, None),
            )
        )
        for constant in constants:
            templates.extend(
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
        templates.extend(
            (
                (["R02"], None, constant),
                (["R03", ["R00"], ["R02"]], None, constant),
                (["R04", ["R00"], ["R03", ["R00"], ["R02"]]], None, constant),
            )
        )
    unique = {}
    for expression, field, constant in templates:
        unique.setdefault(
            (canonical_json_bytes(expression), field, constant),
            (expression, field, constant),
        )
    return list(unique.values())


def _batch_exact_version_space(
    batches: list[list[tuple[list[int], list[int], list[int]]]],
    target: int,
) -> tuple[list[dict[str, Any]], int]:
    rows = [row for batch in batches for row in batch]
    candidates = []
    evaluations = 0
    for expression, field, constant in _residual_templates(rows, target):
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
            candidates.append(
                {
                    "normalized_expression": expression,
                    "action_field_binding": field,
                    "anonymous_integer_constant_binding": constant,
                }
            )
    candidates.sort(key=canonical_json_bytes)
    return candidates, evaluations


def _learned_successor_guard(
    layout: Mapping[str, Any],
    acquired: list[dict[str, Any]],
    future_groups: list[list[dict[str, Any]]],
    program: Mapping[str, Any],
    *,
    successor_prior_library: Mapping[str, Any] | None,
    successor_confidence_denominator: int,
    maximum_successor_support_states: int,
) -> dict[str, Any]:
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    if (
        type(state_order) is not list
        or type(action_order) is not list
        or not future_groups
    ):
        _fail("V41 successor layout or future query inventory changed")
    minimal_program = _mdl_minimal_program_view(program)
    dependency_columns = _program_dependency_columns(minimal_program)
    batches = _aligned_batches(layout, acquired)
    candidate_by_target = {}
    evaluation_count = 0
    for target in dependency_columns:
        frontier, evaluations = _batch_exact_version_space(batches, target)
        evaluation_count += evaluations
        candidate_by_target[target] = frontier
    complete = all(candidate_by_target[target] for target in dependency_columns)
    if not complete:
        return {
            "successor_model_present": True,
            "successor_model_source_query_count": len(v35._groups(acquired)),  # noqa: SLF001
            "terminal_dependency_columns": dependency_columns,
            "per_coordinate_batch_exact_candidate_counts": [
                {"target_column": target, "candidate_count": len(candidate_by_target[target])}
                for target in dependency_columns
            ],
            "mdl_minimal_terminal_frontier_count": minimal_program[
                "decision_tree_candidate_count"
            ],
            "all_terminal_dependency_coordinates_batch_exact_on_acquired_queries": False,
            "learned_successor_frontier_consensus": False,
            "successor_model_selection_compute_events": evaluation_count,
        }
    support_rows = []
    all_states = set()
    truncated = False
    for query_offset, group in enumerate(future_groups):
        row = group[0]
        selected = row.get("selected_action")
        pre_raw = row.get("pre_vector")
        action_raw = selected.get("anonymous_fields") if type(selected) is dict else None
        if type(pre_raw) is not list or type(action_raw) is not list:
            _fail("V41 future query projection changed")
        pre = [pre_raw[index] for index in state_order]
        action = [action_raw[index] for index in action_order]
        coordinate_supports = []
        for target in dependency_columns:
            values = set()
            for candidate in candidate_by_target[target]:
                values.update(
                    _value(
                        candidate["normalized_expression"],
                        pre,
                        action,
                        target,
                        candidate.get("action_field_binding"),
                        candidate.get("anonymous_integer_constant_binding"),
                    )
                )
            coordinate_supports.append(
                (
                    target,
                    tuple(sorted(values)),
                )
            )
        count = math.prod(len(values) for _target, values in coordinate_supports)
        if count > maximum_successor_support_states:
            truncated = True
            break
        states = []
        for values in product(*(values for _target, values in coordinate_supports)):
            state = list(pre)
            for (target, _support), value in zip(
                coordinate_supports, values, strict=True
            ):
                state[target] = value
            states.append(tuple(state))
        states = tuple(sorted(states))
        all_states.update(states)
        support_rows.append(
            {
                "future_query_offset": query_offset,
                "query_projection_sha256": hashlib.sha256(
                    canonical_json_bytes(
                        {
                            "pre_vector": pre_raw,
                            "action_key": selected["action_key"],
                            "anonymous_action_fields": action_raw,
                        }
                    )
                ).hexdigest(),
                "terminal_dependency_coordinate_supports": [
                    {"target_column": target, "predicted_support": list(values)}
                    for target, values in coordinate_supports
                ],
                "successor_support_states": [list(state) for state in states],
                "successor_support_state_count": len(states),
            }
        )
    frontier_consensus = (
        not truncated
        and bool(all_states)
        and v35._consensus(minimal_program, tuple(sorted(all_states)))  # noqa: SLF001
    )
    return {
        "successor_model_present": True,
        "successor_model_source_query_count": len(v35._groups(acquired)),  # noqa: SLF001
        "terminal_dependency_columns": dependency_columns,
        "per_coordinate_batch_exact_candidate_counts": [
            {"target_column": target, "candidate_count": len(candidate_by_target[target])}
            for target in dependency_columns
        ],
        "mdl_minimal_terminal_frontier_count": minimal_program[
            "decision_tree_candidate_count"
        ],
        "all_terminal_dependency_coordinates_batch_exact_on_acquired_queries": True,
        "future_query_count": len(future_groups),
        "predicted_successor_support_rows": support_rows,
        "predicted_successor_support_state_count": len(all_states),
        "successor_support_resource_truncated": truncated,
        "learned_successor_frontier_consensus": frontier_consensus,
        "successor_model_selection_compute_events": evaluation_count,
        "only_acquired_transition_outcomes_used_to_fit_successor_model": True,
        "unacquired_query_prestate_and_action_only_used_for_projection": True,
        "unacquired_successor_or_label_accessed": False,
        "empirical_successor_support_only": True,
        "all_batch_exact_candidate_expressions_retained_for_projection": True,
        "single_point_successor_model_selected_before_projection": False,
        "nonterminal_dependency_state_coordinates_not_modeled_by_guard": True,
        "terminal_dependency_columns_derived_from_mdl_minimal_frontier": True,
        "successor_support_safety_authority_present": False,
    }


def acquire_learned_successor_support_terminal_program_v41(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    successor_prior_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
    successor_confidence_denominator: int = 64,
    maximum_successor_support_states: int = 4096,
) -> dict[str, Any]:
    if (
        type(source_complete_evidence) is not dict
        or type(required_terminal_classes) is not tuple
        or tuple(sorted(set(required_terminal_classes))) != required_terminal_classes
        or not required_terminal_classes
        or any(value not in TERMINAL_CLASS_UNIVERSE_V38 for value in required_terminal_classes)
        or type(successor_confidence_denominator) is not int
        or successor_confidence_denominator < 2
        or type(maximum_successor_support_states) is not int
        or maximum_successor_support_states < 1
    ):
        _fail("V41 acquisition inventory changed")
    layout = source_complete_evidence.get("layout")
    unknown = source_complete_evidence.get("unknown_residual_target_columns")
    rows = source_complete_evidence.get("raw_transition_rows")
    if (
        type(layout) is not dict
        or type(unknown) is not list
        or unknown != sorted(set(unknown))
        or type(rows) is not list
        or not rows
    ):
        _fail("V41 source evidence changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V41 state layout changed")
    groups = v35._groups(rows)  # noqa: SLF001
    if len(groups) < 3:
        _fail("V41 needs training, prequential, and held-out queries")
    query_pre_states = tuple(
        sorted(
            {
                tuple(group[0]["pre_vector"][index] for index in order)
                for group in groups
            }
        )
    )
    required_bits = math.ceil(math.log2(confidence_denominator))
    required_set = set(required_terminal_classes)
    acquired: list[dict[str, Any]] = []
    attempts = []
    ledger = []
    active = None
    selected = None
    stop = None
    retired = 0
    for offset, group in enumerate(groups):
        count = offset + 1
        if active is not None:
            prediction = v37._predict_group(active["program"], group, order)  # noqa: SLF001
            ledger.append(
                {
                    "query_index": offset,
                    "candidate_program_id_before_outcome": active["program_id"],
                    "candidate_training_query_count": active["training_query_count"],
                    "prediction": prediction,
                    "prediction_frozen_before_query_outcome": True,
                }
            )
            if prediction["query_exact"]:
                active["evidence_bits"] += 1
                active["confirmed_query_count"] += 1
            else:
                active = None
                retired += 1
        acquired.extend(group)
        if (
            active is not None
            and active["evidence_bits"] >= required_bits
            and count < len(groups)
        ):
            selected, stop = active["program"], count
            break
        if active is None and count < len(groups) - 1:
            observed_classes = tuple(sorted({v35._label(row) for row in acquired}))  # noqa: SLF001
            class_coverage = set(observed_classes) == required_set
            constructed = v37._candidate(  # noqa: SLF001
                layout,
                unknown,
                acquired,
                role_free_template_library=role_free_template_library,
                maximum_exact_instantiations=maximum_exact_instantiations,
                confidence_denominator=confidence_denominator,
            )
            program = constructed.get("candidate_program")
            prestate_consensus = (
                type(program) is dict
                and v35._consensus(program, query_pre_states)  # noqa: SLF001
            )
            if (
                class_coverage
                and constructed.get("training_calibrated") is True
                and type(program) is dict
                and prestate_consensus
            ):
                successor_guard = _learned_successor_guard(
                    layout,
                    acquired,
                    groups[count:],
                    program,
                    successor_prior_library=successor_prior_library,
                    successor_confidence_denominator=successor_confidence_denominator,
                    maximum_successor_support_states=maximum_successor_support_states,
                )
            else:
                successor_guard = {
                    "successor_model_present": False,
                    "guard_not_attempted_before_semantic_and_training_calibration": True,
                    "learned_successor_frontier_consensus": False,
                }
            public = {
                key: value
                for key, value in constructed.items()
                if key != "candidate_program"
            }
            public.update(
                training_query_count=count,
                observed_terminal_classes=list(observed_classes),
                required_terminal_classes=list(required_terminal_classes),
                semantic_class_coverage_complete=class_coverage,
                candidate_frontier_consensus_on_all_query_pre_states=(
                    prestate_consensus
                ),
                learned_successor_guard=successor_guard,
                training_calibrated_after_all_guards=(
                    class_coverage
                    and prestate_consensus
                    and constructed.get("training_calibrated") is True
                    and successor_guard.get("learned_successor_frontier_consensus") is True
                ),
            )
            attempts.append(public)
            if public["training_calibrated_after_all_guards"]:
                active = {
                    "program": program,
                    "program_id": constructed["candidate_program_id"],
                    "training_query_count": count,
                    "evidence_bits": 0,
                    "confirmed_query_count": 0,
                }
    if selected is None or stop is None:
        status = "ABSTAINED_NO_LEARNED_SUCCESSOR_SUPPORT_CONSENSUS_PROPOSAL"
        heldout, heldout_exact = [], False
    else:
        heldout = [row for group in groups[stop:] for row in group]
        heldout_exact = all(
            v37._predict_group(selected, group, order)["query_exact"]  # noqa: SLF001
            for group in groups[stop:]
        )
        status = (
            "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
            if heldout_exact
            else "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
        )
    query_order = [
        {
            "pre_vector": group[0]["pre_vector"],
            "action_key": group[0]["selected_action"]["action_key"],
            "raw_transition_row_count": len(group),
        }
        for group in groups
    ]
    successor_compute = sum(
        attempt["learned_successor_guard"].get(
            "successor_model_selection_compute_events", 0
        )
        + attempt["learned_successor_guard"].get(
            "batch_exact_binding_evaluation_count", 0
        )
        for attempt in attempts
    )
    payload = {
        "schema": "acfqp.generic_learned_successor_support_acquisition.v41",
        "arm": (
            "ROLE_FREE_FACTOR_PRIOR_ON"
            if role_free_template_library is not None
            else "STRICT_NO_ROLE_FREE_FACTOR_PRIOR"
        ),
        "role_free_template_library_id": (
            None if role_free_template_library is None else role_free_template_library.get("template_library_id")
        ),
        "successor_prior_library_id": (
            None if successor_prior_library is None else successor_prior_library.get("residual_factor_library_id")
        ),
        "successor_point_estimate_confidence_denominator": successor_confidence_denominator,
        "successor_prior_used_to_prune_batch_exact_version_space": False,
        "required_terminal_classes": list(required_terminal_classes),
        "witness_blind_query_order": query_order,
        "witness_blind_query_order_sha256": hashlib.sha256(canonical_json_bytes(query_order)).hexdigest(),
        "full_query_stream_ground_support_labels": len(groups),
        "proposal_attempts": attempts,
        "prequential_prediction_ledger": ledger,
        "retired_failed_proposal_count": retired,
        "required_prequential_evidence_bits": required_bits,
        "prequential_evidence_bits_per_exact_query": 1,
        "stopped_physical_ground_support_labels": stop,
        "selected_terminal_program": selected,
        "selected_terminal_program_id": None if selected is None else selected["terminal_program_id"],
        "heldout_ground_query_count": len(groups) - (stop or len(groups)),
        "heldout_raw_transition_row_count": len(heldout),
        "heldout_exact_prediction": heldout_exact,
        "status": status,
        "successor_model_derivation_compute_events": successor_compute,
        "same_successor_guard_and_prequential_engine_in_both_arms": True,
        "status_output_coordinate_used_as_successor_guard_input": False,
        "batch_exact_successor_version_space_not_point_estimate": True,
        "only_acquired_transition_outcomes_used_to_fit_successor_models": True,
        "unacquired_successor_or_label_accessed_by_guard": False,
        "heldout_rows_accessed_before_stop": False,
        "fixed_label_floor_present": False,
        "fixed_confirmation_block_present": False,
        "statistical_coverage_claimed": False,
        "empirical_successor_support_promoted_to_global_dynamics": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "learned_successor_acquisition_id": hashlib.sha256(
            b"acfqp:generic-learned-successor-support-acquisition:v41\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_relation_covering_learned_successor_acquisition_v41(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    successor_prior_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
    successor_confidence_denominator: int = 64,
    maximum_successor_support_states: int = 4096,
) -> dict[str, Any]:
    schedule = schedule_relation_covering_queries_v39(source_complete_evidence)
    ordered = copy.deepcopy(source_complete_evidence)
    ordered["raw_transition_rows"] = schedule["scheduled_raw_transition_rows"]
    acquisition = acquire_learned_successor_support_terminal_program_v41(
        ordered,
        role_free_template_library=role_free_template_library,
        successor_prior_library=successor_prior_library,
        required_terminal_classes=required_terminal_classes,
        maximum_exact_instantiations=maximum_exact_instantiations,
        confidence_denominator=confidence_denominator,
        successor_confidence_denominator=successor_confidence_denominator,
        maximum_successor_support_states=maximum_successor_support_states,
    )
    payload = {
        "schema": "acfqp.relation_covering_learned_successor_acquisition.v41",
        "query_schedule": schedule,
        "learned_successor_acquisition": acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "learned_successor_acquisition_id": acquisition[
            "learned_successor_acquisition_id"
        ],
        "outcome_witness_used_for_scheduling_or_unacquired_guard": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "relation_covering_acquisition_id": hashlib.sha256(
            b"acfqp:relation-covering-learned-successor-acquisition:v41\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "RETAINED_V71_DEVELOPMENT_DIAGNOSTIC_V41",
    "acquire_learned_successor_support_terminal_program_v41",
    "run_relation_covering_learned_successor_acquisition_v41",
)
