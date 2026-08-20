"""Producer-free reconstruction of the V72r1 campaign.

This verifier does not import either campaign producer/core, V41, or V39.  It
reuses only the already-independent V71 terminal-program semantic replay,
reconstructs the relation-cover schedule from raw pre-state/action fields, and
independently enumerates every batch-exact R00--R04 successor expression before
replaying the V41 prequential state machine.
"""

from __future__ import annotations

import copy
import hashlib
from itertools import product
import math
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v72r1 as domains
from acfqp import construction_k7_role_free_prequential_independent_verifier_v71 as terminal_replay
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.construction_k7_successor_version_space_failure_v72 import FAILURE_ID
from acfqp.generic_relational_terminal_program_independent_replay_v32 import (
    verify_source_complete_relational_program_v32,
)
from acfqp.generic_role_free_relational_template_v33 import (
    GenericRoleFreeRelationalTemplateV33Error,
    instantiate_role_free_relational_template_v33,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "2d570b3853f574083cb7e93e2f0ca026a985ca6cd5b2b12475eb4ebc5ead1e80"
CAMPAIGN_BYTE_COUNT = 4_445_009
CAMPAIGN_SHA256 = "d4dace957a9173220373022310e1b86b9c3ec609df36eaf8765fbc2c95a4f68b"
PREREGISTRATION_ID = "c1c206669904aa5f7a57a1a8f2a514119e5c6221945105f6808b3a1a7f66c7ca"
V71_CAMPAIGN_ID = "a8a9ebead0bcfeb1587be1a6b21ddb11189ec74e26d871ab5ada0ec279261e17"
V71_VERIFICATION_ID = "faf1e3d0569cacd98514c35874b0c59fb685436a326e899cb7dcc70ed94994fa"
TEMPLATE_LIBRARY_ARTIFACT_ID = "8657115a19bace2861b3a14ff780a2708b6e76101a2b7468e52e5285a113b2a9"
VERIFICATION_ID = "8d2c9459b3e0ccea9d4b00b5ccc6808cd1e03ac6ac34ff8a97c4227c212287a6"
EXPECTED_CANONICAL_BYTE_COUNT = 999
EXPECTED_CANONICAL_SHA256 = "8cc4a38a564d43fbd4cc9b7f9968626562d8a766b8ce528febc7a3ee10ee8b5c"
_SOURCE_EPISODE_DOMAIN = b"acfqp:generic-source-complete-relational-world-model:v31\x00"
_SCHEDULE_DOMAIN = b"acfqp:generic-relation-covering-query-schedule:v39\x00"
_ACQUISITION_DOMAIN = b"acfqp:generic-learned-successor-support-acquisition:v41\x00"


class ConstructionK7SuccessorVersionSpaceIndependentVerifierV72R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SuccessorVersionSpaceIndependentVerifierV72R1Error(message)


def _content(document: Mapping[str, Any], id_key: str, domain: str) -> None:
    if type(document) is not dict or type(document.get(id_key)) is not str:
        _fail(f"V72r1 {id_key} inventory changed")
    payload = {key: value for key, value in document.items() if key != id_key}
    if domains.extension_content_id_v72r1(domain, payload) != document[id_key]:
        _fail(f"V72r1 {id_key} content identity changed")


def _compare(left: int, right: int) -> int:
    return -1 if left < right else (1 if left > right else 0)


def _projection(row: Mapping[str, Any]) -> dict[str, Any]:
    selected = row.get("selected_action")
    pre = row.get("pre_vector")
    if (
        type(pre) is not list
        or type(selected) is not dict
        or type(selected.get("action_key")) is not int
        or type(selected.get("anonymous_fields")) is not list
    ):
        _fail("V72r1 query projection changed")
    return {
        "pre_vector": pre,
        "action_key": selected["action_key"],
        "anonymous_action_fields": selected["anonymous_fields"],
    }


def _groups(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    order = []
    for row in rows:
        projection = _projection(row)
        key = (tuple(projection["pre_vector"]), projection["action_key"])
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)
    return [grouped[key] for key in order]


def _schedule(evidence: Mapping[str, Any]) -> dict[str, Any]:
    layout = evidence.get("layout")
    unknown = evidence.get("unknown_residual_target_columns")
    rows = evidence.get("raw_transition_rows")
    if (
        type(layout) is not dict
        or type(unknown) is not list
        or unknown != sorted(set(unknown))
        or type(rows) is not list
        or not rows
    ):
        _fail("V72r1 schedule source changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V72r1 schedule layout changed")
    known = tuple(index for index in range(len(order)) if index not in unknown)
    groups = _groups(rows)
    strata: dict[bytes, list[tuple[str, int, list[dict[str, Any]], dict[str, Any], dict[str, Any]]]] = {}
    source_projections = []
    for original_index, group in enumerate(groups):
        projection = _projection(group[0])
        source_projections.append(projection)
        canonical_pre = [projection["pre_vector"][raw] for raw in order]
        action = projection["anonymous_action_fields"]
        state_relations = [
            {
                "left_anonymous_coordinate": left,
                "right_anonymous_coordinate": right,
                "three_way_order": _compare(canonical_pre[left], canonical_pre[right]),
            }
            for offset, left in enumerate(known)
            for right in known[offset + 1 :]
        ]
        action_relations = [
            {
                "left_anonymous_action_field": left,
                "right_anonymous_action_field": right,
                "three_way_order": _compare(action[left], action[right]),
            }
            for left in range(len(action))
            for right in range(left + 1, len(action))
        ]
        signature = {
            "modeled_pre_coordinate_relations": state_relations,
            "anonymous_action_field_relations": action_relations,
            "action_field_count": len(action),
        }
        encoded = canonical_json_bytes(signature)
        identity = hashlib.sha256(canonical_json_bytes(projection)).hexdigest()
        strata.setdefault(encoded, []).append(
            (identity, original_index, group, projection, signature)
        )
    for values in strata.values():
        values.sort(key=lambda row: (row[0], row[1]))
    ordered_strata = sorted(
        strata,
        key=lambda encoded: (len(strata[encoded]), hashlib.sha256(encoded).hexdigest()),
    )
    ranked = []
    round_index = 0
    while len(ranked) < len(groups):
        for encoded in ordered_strata:
            values = strata[encoded]
            if round_index < len(values):
                ranked.append((round_index, encoded, values[round_index]))
        round_index += 1
    payload = {
        "schema": "acfqp.generic_relation_covering_query_schedule.v39",
        "query_source_projection_sha256": hashlib.sha256(
            canonical_json_bytes(source_projections)
        ).hexdigest(),
        "query_count": len(groups),
        "raw_transition_row_count": len(rows),
        "relation_signature_stratum_count": len(strata),
        "modeled_coordinate_pair_evaluation_count": (
            len(groups) * (len(known) * (len(known) - 1) // 2)
        ),
        "schedule": [
            {
                "scheduled_query_index": index,
                "coverage_round": row[0],
                "original_query_index": row[2][1],
                "query_projection": row[2][3],
                "relation_signature": row[2][4],
                "relation_signature_sha256": hashlib.sha256(row[1]).hexdigest(),
                "stratum_size": len(strata[row[1]]),
                "raw_transition_row_count": len(row[2][2]),
            }
            for index, row in enumerate(ranked)
        ],
        "scheduled_raw_transition_rows": [item for row in ranked for item in row[2][2]],
        "pre_state_fields_accessed": True,
        "anonymous_action_fields_accessed": True,
        "post_state_fields_accessed": False,
        "legality_after_accessed": False,
        "terminal_acceptance_label_accessed": False,
        "outcome_tape_accessed": False,
        "fixed_label_floor_present": False,
        "coverage_schedule_not_safety_authority": True,
    }
    return {
        **payload,
        "query_schedule_id": hashlib.sha256(
            _SCHEDULE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


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
    _fail("V72r1 successor expression changed")


def _tree_columns(node: Mapping[str, Any]) -> set[int]:
    if node.get("kind") == "LEAF":
        return set()
    if node.get("kind") != "RELATION":
        _fail("V72r1 terminal tree changed")
    left, right = node.get("left_column"), node.get("right_column")
    if type(left) is not int or type(right) is not int:
        _fail("V72r1 terminal relation columns changed")
    return {left, right, *_tree_columns(node["when_true"]), *_tree_columns(node["when_false"])}


def _minimal_program(program: Mapping[str, Any]) -> dict[str, Any]:
    frontier = program.get("decision_tree_candidate_frontier")
    if type(frontier) is not list or not frontier:
        _fail("V72r1 terminal frontier changed")
    nodes = min(row["decision_tree_node_count"] for row in frontier)
    rows = [row for row in frontier if row["decision_tree_node_count"] == nodes]
    byte_count = min(row["decision_tree_byte_count"] for row in rows)
    rows = [row for row in rows if row["decision_tree_byte_count"] == byte_count]
    return {
        **program,
        "decision_tree": rows[0]["decision_tree"],
        "decision_tree_node_count": rows[0]["decision_tree_node_count"],
        "decision_tree_candidate_frontier": rows,
        "decision_tree_candidate_count": len(rows),
    }


def _dependencies(program: Mapping[str, Any]) -> list[int]:
    target = program.get("status_target_column")
    frontier = program.get("decision_tree_candidate_frontier")
    if type(target) is not int or type(frontier) is not list or not frontier:
        _fail("V72r1 terminal dependency inventory changed")
    columns: set[int] = set()
    for row in frontier:
        columns.update(_tree_columns(row["decision_tree"]))
    if target in columns:
        _fail("V72r1 terminal tree read its status output")
    return sorted(columns)


def _aligned_batches(
    layout: Mapping[str, Any], rows: list[dict[str, Any]]
) -> list[list[tuple[list[int], list[int], list[int]]]]:
    state_order = layout["state_canonical_to_raw"]
    action_order = layout["action_canonical_to_raw"]
    grouped = {}
    order = []
    for row in rows:
        selected = row["selected_action"]
        pre_raw, post_raw = row["pre_vector"], row["post_vector"]
        action_raw = selected["anonymous_fields"]
        key = (tuple(pre_raw), selected["action_key"])
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


def _templates(
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
                *(post[target] - pre[target] - action[field] for field in range(field_count)),
            )
        }
    )
    result: list[tuple[Any, int | None, int | None]] = [(["R00"], None, None)]
    for field in range(field_count):
        result.extend(((["R01"], field, None), (["R03", ["R00"], ["R01"]], field, None)))
        for constant in constants:
            result.extend(
                (
                    (["R03", ["R03", ["R00"], ["R01"]], ["R02"]], field, constant),
                    (["R04", ["R00"], ["R03", ["R03", ["R00"], ["R01"]], ["R02"]]], field, constant),
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
        unique.setdefault((canonical_json_bytes(expression), field, constant), (expression, field, constant))
    return list(unique.values())


def _version_space(
    batches: list[list[tuple[list[int], list[int], list[int]]]], target: int
) -> tuple[list[dict[str, Any]], int]:
    rows = [row for batch in batches for row in batch]
    candidates = []
    evaluations = 0
    for expression, field, constant in _templates(rows, target):
        exact = True
        for batch in batches:
            predicted = _value(expression, batch[0][0], batch[0][2], target, field, constant)
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


def _guard(
    layout: Mapping[str, Any],
    acquired: list[dict[str, Any]],
    future_groups: list[list[dict[str, Any]]],
    program: Mapping[str, Any],
    *,
    maximum_states: int = 4_096,
) -> dict[str, Any]:
    state_order = layout["state_canonical_to_raw"]
    action_order = layout["action_canonical_to_raw"]
    minimal = _minimal_program(program)
    dependencies = _dependencies(minimal)
    batches = _aligned_batches(layout, acquired)
    by_target = {}
    evaluations = 0
    for target in dependencies:
        candidates, count = _version_space(batches, target)
        by_target[target] = candidates
        evaluations += count
    counts = [
        {"target_column": target, "candidate_count": len(by_target[target])}
        for target in dependencies
    ]
    if not all(by_target[target] for target in dependencies):
        return {
            "successor_model_present": True,
            "successor_model_source_query_count": len(_groups(acquired)),
            "terminal_dependency_columns": dependencies,
            "per_coordinate_batch_exact_candidate_counts": counts,
            "mdl_minimal_terminal_frontier_count": minimal["decision_tree_candidate_count"],
            "all_terminal_dependency_coordinates_batch_exact_on_acquired_queries": False,
            "learned_successor_frontier_consensus": False,
            "successor_model_selection_compute_events": evaluations,
        }
    support_rows = []
    all_states = set()
    truncated = False
    for query_offset, group in enumerate(future_groups):
        row = group[0]
        selected = row["selected_action"]
        pre_raw, action_raw = row["pre_vector"], selected["anonymous_fields"]
        pre = [pre_raw[index] for index in state_order]
        action = [action_raw[index] for index in action_order]
        coordinate_supports = []
        for target in dependencies:
            values = set()
            for candidate in by_target[target]:
                values.update(
                    _value(
                        candidate["normalized_expression"], pre, action, target,
                        candidate["action_field_binding"],
                        candidate["anonymous_integer_constant_binding"],
                    )
                )
            coordinate_supports.append((target, tuple(sorted(values))))
        if math.prod(len(values) for _target, values in coordinate_supports) > maximum_states:
            truncated = True
            break
        states = []
        for values in product(*(values for _target, values in coordinate_supports)):
            state = list(pre)
            for (target, _support), value in zip(coordinate_supports, values, strict=True):
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
    consensus = (
        not truncated
        and bool(all_states)
        and terminal_replay._consensus(minimal, tuple(sorted(all_states)))  # noqa: SLF001
    )
    return {
        "successor_model_present": True,
        "successor_model_source_query_count": len(_groups(acquired)),
        "terminal_dependency_columns": dependencies,
        "per_coordinate_batch_exact_candidate_counts": counts,
        "mdl_minimal_terminal_frontier_count": minimal["decision_tree_candidate_count"],
        "all_terminal_dependency_coordinates_batch_exact_on_acquired_queries": True,
        "future_query_count": len(future_groups),
        "predicted_successor_support_rows": support_rows,
        "predicted_successor_support_state_count": len(all_states),
        "successor_support_resource_truncated": truncated,
        "learned_successor_frontier_consensus": consensus,
        "successor_model_selection_compute_events": evaluations,
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


def _acquisition(
    evidence: Mapping[str, Any], library: Mapping[str, Any] | None, residual_id: str
) -> dict[str, Any]:
    layout = evidence["layout"]
    unknown = evidence["unknown_residual_target_columns"]
    rows = evidence["raw_transition_rows"]
    order = layout["state_canonical_to_raw"]
    groups = _groups(rows)
    query_pre_states = tuple(
        sorted({tuple(group[0]["pre_vector"][index] for index in order) for group in groups})
    )
    required_classes = ("ACCEPT", "ACTIVE", "REJECT")
    required_bits = 6
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
            prediction = terminal_replay._predict(active["program"], group, order)  # noqa: SLF001
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
        if active is not None and active["evidence_bits"] >= required_bits and count < len(groups):
            selected, stop = active["program"], count
            break
        if active is None and count < len(groups) - 1:
            observed = tuple(sorted({terminal_replay._label(row) for row in acquired}))  # noqa: SLF001
            coverage = set(observed) == set(required_classes)
            constructed = terminal_replay._candidate(  # noqa: SLF001
                layout, unknown, acquired, library=library, maximum=32, denominator=64
            )
            program = constructed.get("candidate_program")
            prestate_consensus = (
                type(program) is dict
                and terminal_replay._consensus(program, query_pre_states)  # noqa: SLF001
            )
            if (
                coverage
                and constructed.get("training_calibrated") is True
                and type(program) is dict
                and prestate_consensus
            ):
                guard = _guard(layout, acquired, groups[count:], program)
            else:
                guard = {
                    "successor_model_present": False,
                    "guard_not_attempted_before_semantic_and_training_calibration": True,
                    "learned_successor_frontier_consensus": False,
                }
            public = {key: value for key, value in constructed.items() if key != "candidate_program"}
            public.update(
                training_query_count=count,
                observed_terminal_classes=list(observed),
                required_terminal_classes=list(required_classes),
                semantic_class_coverage_complete=coverage,
                candidate_frontier_consensus_on_all_query_pre_states=prestate_consensus,
                learned_successor_guard=guard,
                training_calibrated_after_all_guards=(
                    coverage
                    and prestate_consensus
                    and constructed.get("training_calibrated") is True
                    and guard.get("learned_successor_frontier_consensus") is True
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
        heldout, exact = [], False
    else:
        heldout = [row for group in groups[stop:] for row in group]
        exact = all(terminal_replay._predict(selected, group, order)["query_exact"] for group in groups[stop:])  # noqa: SLF001
        status = "PROPOSAL_ISSUED_HELDOUT_VALIDATED" if exact else "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
    query_order = [
        {
            "pre_vector": group[0]["pre_vector"],
            "action_key": group[0]["selected_action"]["action_key"],
            "raw_transition_row_count": len(group),
        }
        for group in groups
    ]
    successor_compute = sum(
        attempt["learned_successor_guard"].get("successor_model_selection_compute_events", 0)
        for attempt in attempts
    )
    payload = {
        "schema": "acfqp.generic_learned_successor_support_acquisition.v41",
        "arm": "ROLE_FREE_FACTOR_PRIOR_ON" if library is not None else "STRICT_NO_ROLE_FREE_FACTOR_PRIOR",
        "role_free_template_library_id": None if library is None else library.get("template_library_id"),
        "successor_prior_library_id": residual_id,
        "successor_point_estimate_confidence_denominator": 64,
        "successor_prior_used_to_prune_batch_exact_version_space": False,
        "required_terminal_classes": list(required_classes),
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
        "heldout_exact_prediction": exact,
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
            _ACQUISITION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _ood(source: Mapping[str, Any], status_target: int) -> dict[str, Any]:
    result = copy.deepcopy(source)
    order = result["layout"]["state_canonical_to_raw"]
    raw_status = order[status_target]
    order.append(len(order))
    colors = result["layout"].get("state_structural_colors")
    if type(colors) is list:
        colors.append("V72_OOD_DUPLICATE_STATUS_ROLE")
    result["unknown_residual_target_columns"].append(len(order) - 1)
    result["unknown_residual_target_columns"].sort()
    for row in result["raw_transition_rows"]:
        row["pre_vector"].append(row["pre_vector"][raw_status])
        row["post_vector"].append(row["post_vector"][raw_status])
    return result


def _consumed(row: Mapping[str, Any]) -> int:
    value = row.get("stopped_physical_ground_support_labels")
    if value is None:
        value = row.get("full_query_stream_ground_support_labels")
    if type(value) is not int:
        _fail("V72r1 label accounting changed")
    return value


def _terminal_compute(row: Mapping[str, Any]) -> int:
    return sum(attempt.get("candidate_constructor_compute", 0) for attempt in row.get("proposal_attempts", []))


def _schedule_compute(schedule: Mapping[str, Any]) -> int:
    return sum(
        len(row["relation_signature"]["modeled_pre_coordinate_relations"])
        + len(row["relation_signature"]["anonymous_action_field_relations"])
        for row in schedule["schedule"]
    )


def verify_successor_version_space_campaign_bytes_v72r1(raw: bytes) -> bytes:
    if type(raw) is not bytes:
        _fail("V72r1 campaign input must be exact bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V72r1 campaign bytes are not canonical")
    if (
        len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
        or document.get("campaign_id") != CAMPAIGN_ID
    ):
        _fail("V72r1 frozen campaign identity changed")
    _content(document, "campaign_id", domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_CAMPAIGN_V72R1_DOMAIN)
    if (
        document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("preserved_v72_failure_id") != FAILURE_ID
        or document.get("v71_campaign_id") != V71_CAMPAIGN_ID
        or document.get("v71_verification_id") != V71_VERIFICATION_ID
        or document.get("template_library_artifact_id") != TEMPLATE_LIBRARY_ARTIFACT_ID
    ):
        _fail("V72r1 predecessor identity changed")
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if template_artifact.library_artifact_id != TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V72r1 template library changed")
    template_document = template_artifact.to_document()
    library = template_document["compiled_template_library"]
    residual_id = residual_artifact.to_document()["compiled_library"]["residual_factor_library_id"]
    occurrences = document.get("occurrences")
    if type(occurrences) is not list or len(occurrences) != 6:
        _fail("V72r1 occurrence inventory changed")
    ood_count = 0
    for occurrence in occurrences:
        _content(occurrence, "occurrence_id", domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_OCCURRENCE_V72R1_DOMAIN)
        if (
            occurrence.get("preserved_v72_failure_id") != FAILURE_ID
            or occurrence.get("frozen_v72_occurrence_constructor_reused_without_semantic_change") is not True
        ):
            _fail("V72r1 occurrence predecessor changed")
        envelope = occurrence.get("target_source_complete_episode")
        source = occurrence.get("retained_target_source")
        if type(envelope) is not dict or type(source) is not dict:
            _fail("V72r1 retained source changed")
        evidence = envelope.get("terminal_program_source_evidence")
        episode = envelope.get("predecessor_v30_episode")
        if source != {
            "layout": evidence.get("layout"),
            "unknown_residual_target_columns": evidence.get("unknown_residual_target_columns"),
            "raw_transition_rows": evidence.get("raw_transition_rows"),
        }:
            _fail("V72r1 source join changed")
        episode_payload = {key: value for key, value in envelope.items() if key != "source_complete_episode_id"}
        if hashlib.sha256(_SOURCE_EPISODE_DOMAIN + canonical_json_bytes(episode_payload)).hexdigest() != envelope.get("source_complete_episode_id"):
            _fail("V72r1 source episode identity changed")
        verify_source_complete_relational_program_v32(source, episode["final_relational_terminal_program"])
        schedule = _schedule(source)
        if schedule != occurrence.get("shared_outcome_blind_query_schedule"):
            _fail("V72r1 relation-cover schedule reconstruction changed")
        ordered = {**source, "raw_transition_rows": schedule["scheduled_raw_transition_rows"]}
        expected_arms = {
            "ROLE_FREE_FACTOR_PRIOR_ON": _acquisition(ordered, library, residual_id),
            "STRICT_NO_ROLE_FREE_FACTOR_PRIOR": _acquisition(ordered, None, residual_id),
        }
        if occurrence.get("acquisition_arms") != expected_arms:
            _fail("V72r1 successor-version-space reconstruction changed")
        expected_ood = _ood(source, episode["final_relational_terminal_program"]["status_target_column"])
        if occurrence.get("retained_incompatible_schema_ood_source") != expected_ood:
            _fail("V72r1 OOD input changed")
        try:
            replay = instantiate_role_free_relational_template_v33(
                library, expected_ood, maximum_exact_instantiations=32
            )
        except GenericRoleFreeRelationalTemplateV33Error:
            pass
        else:
            if replay["exact_target_instantiation_count"] != 0:
                _fail("V72r1 OOD schema received a transfer")
        if occurrence.get("incompatible_schema_ood_control", {}).get("status") != "INCOMPATIBLE_SCHEMA_REJECTED":
            _fail("V72r1 OOD receipt changed")
        ood_count += 1
    names = ("ROLE_FREE_FACTOR_PRIOR_ON", "STRICT_NO_ROLE_FREE_FACTOR_PRIOR")
    summaries = {}
    for name in names:
        rows = [row["acquisition_arms"][name] for row in occurrences]
        summaries[name] = {
            "heldout_validated_occurrence_count": sum(row["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED" for row in rows),
            "heldout_failed_noncertificate_occurrence_count": sum(row["status"] == "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE" for row in rows),
            "abstained_occurrence_count": sum(row["status"].startswith("ABSTAINED") for row in rows),
            "counterfactual_acquisition_consumed_labels": sum(_consumed(row) for row in rows),
            "post_stop_heldout_audit_labels": sum(row["heldout_ground_query_count"] for row in rows),
            "terminal_constructor_compute_events": sum(_terminal_compute(row) for row in rows),
            "successor_model_derivation_compute_events": sum(row["successor_model_derivation_compute_events"] for row in rows),
            "retired_failed_proposal_count": sum(row["retired_failed_proposal_count"] for row in rows),
        }
    comparable = [
        row for row in occurrences
        if all(row["acquisition_arms"][name]["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED" for name in names)
    ]
    prior_labels = sum(_consumed(row["acquisition_arms"][names[0]]) for row in comparable)
    strict_labels = sum(_consumed(row["acquisition_arms"][names[1]]) for row in comparable)
    sample = {
        "jointly_heldout_validated_occurrence_count": len(comparable),
        "prior_consumed_labels_on_comparable_occurrences": prior_labels,
        "strict_consumed_labels_on_comparable_occurrences": strict_labels,
        "prior_minus_strict_labels": prior_labels - strict_labels,
        "fresh_prior_label_reduction_observed": bool(comparable) and prior_labels < strict_labels,
        "sample_reduction_required_by_registered_gate": False,
        "online_actual_sample_reduction_claimed": False,
        "economics_claimed": False,
    }
    if document.get("sample_tax_comparison") != sample:
        _fail("V72r1 sample-tax comparison changed")
    episodes = [row["target_source_complete_episode"]["predecessor_v30_episode"] for row in occurrences]
    accounting = {
        "offline_template_source_labels": template_document["offline_template_source_ground_support_labels"],
        "offline_residual_library_labels": 204,
        "underlying_target_common_partial_labels": sum(row["common_partial_ground_support_labels"] for row in occurrences),
        "underlying_target_certificate_local_labels": sum(row["local_ground_support_labels"] for row in episodes),
        "underlying_target_execution_steps": sum(row["execution_steps"] for row in episodes),
        "underlying_target_partial_planning_compute_events": sum(row["partial_planning_compute_events"] for row in episodes),
        "underlying_target_relational_planning_compute_events": sum(row["relational_abstract_support_branch_evaluations"] for row in episodes),
        "shared_schedule_relation_evaluations": sum(_schedule_compute(row["shared_outcome_blind_query_schedule"]) for row in occurrences),
        "arm_accounting": summaries,
        "all_axes_separate": True,
        "counterfactual_acquisition_labels_not_subtracted_from_actual_source_generation": True,
    }
    if document.get("accounting") != accounting:
        _fail("V72r1 accounting changed")
    gate = document.get("registered_gate")
    expected_gate = {
        "zero_heldout_failed_proposals_in_both_arms": True,
        "prior_heldout_validated_occurrence_count": summaries[names[0]]["heldout_validated_occurrence_count"],
        "strict_heldout_validated_occurrence_count": summaries[names[1]]["heldout_validated_occurrence_count"],
        "jointly_comparable_occurrence_count": len(comparable),
        "incompatible_schema_ood_rejection_count": ood_count,
        "required_ood_rejection_count": len(occurrences),
        "sample_reduction_required": False,
        "passed": True,
    }
    if gate != expected_gate:
        _fail("V72r1 registered Gate changed")
    locks = {
        "same_target_query_pool_in_both_arms": True,
        "same_query_schedule_in_both_arms": True,
        "same_v41_version_space_and_stop_engine_in_both_arms": True,
        "heldout_rows_accessed_before_stop": False,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "producer_free_verification_present": False,
        "online_adaptive_acquisition_integrated": False,
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
        _fail("V72r1 claim locks changed")
    payload = {
        "schema": "acfqp.successor_version_space_verification.v72r1",
        "campaign_id": CAMPAIGN_ID,
        "occurrence_count": len(occurrences),
        "source_complete_terminal_programs_reconstructed": len(occurrences),
        "relation_cover_schedules_reconstructed": len(occurrences),
        "successor_version_space_arm_histories_reconstructed": 2 * len(occurrences),
        "incompatible_schema_ood_controls_reexecuted": ood_count,
        "prior_heldout_validated_occurrence_count": summaries[names[0]]["heldout_validated_occurrence_count"],
        "strict_heldout_validated_occurrence_count": summaries[names[1]]["heldout_validated_occurrence_count"],
        "prior_minus_strict_labels": sample["prior_minus_strict_labels"],
        "fresh_prior_label_reduction_observed": sample["fresh_prior_label_reduction_observed"],
        "all_accounting_axes_recomputed": True,
        "v72r1_producer_imported": False,
        "v72r1_campaign_core_imported": False,
        "v41_acquisition_imported": False,
        "v39_scheduler_imported": False,
        "online_actual_sample_reduction_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "status": "PRODUCER_FREE_SUCCESSOR_VERSION_SPACE_EVIDENCE_VERIFIED",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v72r1(
            domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_VERIFICATION_V72R1_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V72r1 verification changed")
    return result


__all__ = ("verify_successor_version_space_campaign_bytes_v72r1",)
