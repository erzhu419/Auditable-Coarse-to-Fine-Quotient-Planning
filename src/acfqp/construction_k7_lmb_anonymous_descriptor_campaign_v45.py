"""V45 anonymous-descriptor projection, program, and support synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
import random
from typing import Any, NoReturn

from acfqp import construction_k7_lmb_anonymous_descriptor_preregistration_v45 as pre
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


PROFILE_KEY = "construction_k7_lmb_anonymous_descriptor_campaign_v45"
EXPECTED_CAMPAIGN_ID = "e1b034e577463ea1f91380bb2b85b97c130af89886ce62638762e65a4dab1413"
EXPECTED_CANONICAL_BYTE_COUNT = 856_051
EXPECTED_CANONICAL_SHA256 = "f893d7fada34da53385ab67b08ffe3e30767732d728475bb6fdafb9b64ee31f3"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_lmb_anonymous_descriptor_preregistration_v45.py",
    "src/acfqp/domains/matching_buffer.py",
)


class ConstructionK7LMBAnonymousDescriptorCampaignV45Error(ValueError):
    """The descriptor projection, dependency signature, plan, or evidence changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBAnonymousDescriptorCampaignV45Error(message)


def _state(state: LMBState) -> dict[str, Any]:
    return {
        "removed_mask": state.removed_mask,
        "buffer_counts": list(state.buffer),
        "status": state.status.value,
    }


@dataclass(frozen=True, slots=True)
class _AnonymousLayout:
    occurrence_seed: int
    tokens_by_internal_coordinate: tuple[int, ...]
    observed_coordinate_order: tuple[int, ...]
    coordinate_tokens: tuple[int, ...]
    layout_id: str


def _layout(kernel: LMBKernel, occurrence_seed: int) -> _AnonymousLayout:
    token_permutation = list(range(kernel.type_count))
    random.Random(occurrence_seed ^ pre.DESCRIPTOR_TOKEN_SALT).shuffle(token_permutation)
    token_base = 10_000_000 + occurrence_seed * 100
    tokens = tuple(token_base + token_permutation[index] for index in range(kernel.type_count))
    order = list(range(kernel.type_count))
    random.Random(occurrence_seed ^ pre.COORDINATE_ORDER_SALT).shuffle(order)
    coordinate_tokens = tuple(tokens[index] for index in order)
    payload = {
        "role": "ANONYMOUS_ADAPTER_LAYOUT",
        "occurrence_seed": occurrence_seed,
        "descriptor_field_count": pre.DESCRIPTOR_FIELD_COUNT,
        "coordinate_tokens": list(coordinate_tokens),
        "descriptor_namespace_commitment": content_id(
            pre.FUTURE_DOMAINS["program"],
            {"role": "DESCRIPTOR_NAMESPACE", "tokens": list(tokens)},
        ),
        "coordinate_order_commitment": content_id(
            pre.FUTURE_DOMAINS["program"],
            {"role": "COORDINATE_ORDER", "order": order},
        ),
        "coordinate_order_is_nonidentity": order != list(range(kernel.type_count)),
        "descriptor_semantic_names_exposed": False,
    }
    return _AnonymousLayout(
        occurrence_seed,
        tokens,
        tuple(order),
        coordinate_tokens,
        content_id(pre.FUTURE_DOMAINS["program"], payload),
    )


def _layout_document(layout: _AnonymousLayout) -> dict[str, Any]:
    order = list(layout.observed_coordinate_order)
    tokens = list(layout.tokens_by_internal_coordinate)
    return {
        "layout_id": layout.layout_id,
        "occurrence_seed": layout.occurrence_seed,
        "descriptor_field_count": pre.DESCRIPTOR_FIELD_COUNT,
        "coordinate_tokens": list(layout.coordinate_tokens),
        "descriptor_namespace_commitment": content_id(
            pre.FUTURE_DOMAINS["program"],
            {"role": "DESCRIPTOR_NAMESPACE", "tokens": tokens},
        ),
        "coordinate_order_commitment": content_id(
            pre.FUTURE_DOMAINS["program"],
            {"role": "COORDINATE_ORDER", "order": order},
        ),
        "coordinate_order_is_nonidentity": order != list(range(len(order))),
        "descriptor_semantic_names_exposed": False,
    }


def _action_descriptor(
    kernel: LMBKernel,
    layout: _AnonymousLayout,
    action: LMBAction,
) -> tuple[int, int, int]:
    seed = layout.occurrence_seed
    return (
        20_000_000 + seed * 1_000 + action.tile,
        layout.tokens_by_internal_coordinate[kernel.tile_types[action.tile]],
        30_000_000 + seed * 1_000 + len(kernel.blockers[action.tile]),
    )


def _observed_counts(state: LMBState, layout: _AnonymousLayout) -> tuple[int, ...]:
    return tuple(state.buffer[index] for index in layout.observed_coordinate_order)


def _join_position(
    coordinate_tokens: tuple[int, ...],
    descriptor_fields: tuple[int, ...],
    selected_field_index: int,
) -> int:
    matches = [
        index
        for index, token in enumerate(coordinate_tokens)
        if token == descriptor_fields[selected_field_index]
    ]
    if len(matches) != 1:
        _fail("derived descriptor field does not have one coordinate-token join")
    return matches[0]


def _model_step(
    kernel: LMBKernel,
    layout: _AnonymousLayout,
    state: LMBState,
    action: LMBAction,
    selected_field_index: int,
    rewrite_cardinality: int,
) -> LMBState:
    descriptor = _action_descriptor(kernel, layout, action)
    observed_position = _join_position(
        layout.coordinate_tokens, descriptor, selected_field_index
    )
    internal_coordinate = layout.observed_coordinate_order[observed_position]
    removed = state.removed_mask | (1 << action.tile)
    counts = list(state.buffer)
    counts[internal_coordinate] = (
        counts[internal_coordinate] + 1
    ) % rewrite_cardinality
    load = sum(counts)
    board_empty = removed == (1 << kernel.tile_count) - 1
    status = (
        LMBStatus.FAILURE
        if load > kernel.capacity
        else LMBStatus.SUCCESS
        if board_empty
        else LMBStatus.ACTIVE
    )
    return LMBState(removed, tuple(counts), status)


def _plan(
    kernel: LMBKernel,
    layout: _AnonymousLayout,
    state: LMBState,
    selected_field_index: int,
    rewrite_cardinality: int,
) -> tuple[tuple[LMBAction, ...], int, int]:
    memo: dict[LMBState, tuple[LMBAction, ...] | None] = {}
    evaluations = 0
    peak = 0

    def solve(current: LMBState) -> tuple[LMBAction, ...] | None:
        nonlocal evaluations, peak
        if current.status is LMBStatus.SUCCESS:
            return ()
        if current.status is LMBStatus.FAILURE:
            return None
        if current in memo:
            return memo[current]
        candidates = []
        for action in kernel.actions(current):
            successor = _model_step(
                kernel,
                layout,
                current,
                action,
                selected_field_index,
                rewrite_cardinality,
            )
            evaluations += 1
            rewrite = sum(successor.buffer) < sum(current.buffer)
            available = sum(
                1
                for tile in range(kernel.tile_count)
                if not successor.removed_mask & (1 << tile)
                and all(
                    successor.removed_mask & (1 << blocker)
                    for blocker in kernel.blockers[tile]
                )
            )
            candidates.append(
                ((-int(rewrite), sum(successor.buffer), -available, action.tile), action, successor)
            )
        for _rank, action, successor in sorted(candidates):
            suffix = solve(successor)
            if suffix is not None:
                memo[current] = (action, *suffix)
                peak = max(peak, len(memo))
                return memo[current]
        memo[current] = None
        peak = max(peak, len(memo))
        return None

    result = solve(state)
    if result is None:
        _fail("anonymous derived program found no successful continuation")
    return result, evaluations, peak


def _observation(
    *,
    stage: str,
    seed: int,
    index: int,
    kernel: LMBKernel,
    layout: _AnonymousLayout,
    state: LMBState,
    action: LMBAction,
    successor: LMBState,
    plan_prefix: list[int] | None,
) -> dict[str, Any]:
    before = _observed_counts(state, layout)
    after = _observed_counts(successor, layout)
    changed = [
        position
        for position, (left, right) in enumerate(zip(before, after))
        if left != right
    ]
    payload = {
        "schema": "acfqp.lmb_anonymous_descriptor_observation.v45",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "stage": stage,
        "source_seed": seed,
        "decision_index": index,
        "layout_id": layout.layout_id,
        "coordinate_tokens": list(layout.coordinate_tokens),
        "pre_removed_mask": state.removed_mask,
        "pre_observed_count_vector": list(before),
        "pre_status": state.status.value,
        "legal_action_ids": [candidate.tile for candidate in kernel.actions(state)],
        "action_id": action.tile,
        "action_descriptor_fields": list(_action_descriptor(kernel, layout, action)),
        "post_removed_mask": successor.removed_mask,
        "post_observed_count_vector": list(after),
        "post_status": successor.status.value,
        "changed_observed_coordinate_positions": changed,
        "pre_load": sum(before),
        "post_load": sum(after),
        "instance_capacity": kernel.capacity,
        "post_board_empty": successor.removed_mask == (1 << kernel.tile_count) - 1,
        "source_plan_prefix": plan_prefix,
        "source_planning_kernel_step": False,
        "source_generation_witness_accessed": False,
        "descriptor_field_semantic_names_exposed": False,
    }
    return {
        **payload,
        "observation_id": content_id(pre.FUTURE_DOMAINS["observation"], payload),
    }


def _candidate_projection_fields(rows: list[dict[str, Any]]) -> list[int]:
    result = []
    for field_index in range(pre.DESCRIPTOR_FIELD_COUNT):
        valid = True
        for row in rows:
            matches = [
                position
                for position, token in enumerate(row["coordinate_tokens"])
                if token == row["action_descriptor_fields"][field_index]
            ]
            if matches != row["changed_observed_coordinate_positions"] or len(matches) != 1:
                valid = False
                break
        if valid:
            result.append(field_index)
    return result


def _projection_acquisition() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    closures = []
    for seed in pre.PROJECTION_ACQUISITION_SEEDS:
        kernel, witness = generate_solvable_lmb(seed=seed, **pre.SOURCE_SPEC)
        del witness
        layout = _layout(kernel, seed)
        state = kernel.initial_distribution()[0][1]
        episode_rows = []
        while state.status is LMBStatus.ACTIVE:
            action = min(kernel.actions(state), key=lambda candidate: candidate.tile)
            outcome = kernel.step(state, action)[0]
            row = _observation(
                stage="PROJECTION_ACQUISITION",
                seed=seed,
                index=len(episode_rows),
                kernel=kernel,
                layout=layout,
                state=state,
                action=action,
                successor=outcome.next_state,
                plan_prefix=None,
            )
            rows.append(row)
            episode_rows.append(row)
            state = outcome.next_state
            if len(rows) > pre.MAX_PROJECTION_ACQUISITION_LABELS:
                _fail("projection acquisition exceeded preregistered label cap")
        candidates = _candidate_projection_fields(rows)
        distinct_tokens = {
            row["coordinate_tokens"][row["changed_observed_coordinate_positions"][0]]
            for row in rows
        }
        complete = (
            len(candidates) == 1
            and len(distinct_tokens) >= pre.MIN_DISTINCT_CHANGED_COORDINATE_TOKENS
        )
        closures.append(
            {
                "source_seed": seed,
                "layout": _layout_document(layout),
                "transition_label_count": len(episode_rows),
                "terminal_status": state.status.value,
                "candidate_projection_fields_after_episode": candidates,
                "distinct_changed_coordinate_token_count": len(distinct_tokens),
                "projection_requirements_satisfied_after_episode": complete,
            }
        )
        if complete:
            break
    if len(_candidate_projection_fields(rows)) != 1:
        _fail("anonymous source rows did not identify one descriptor projection")
    return rows, closures


def _derive_rewrite_cardinality(rows: list[dict[str, Any]]) -> int:
    equations = set()
    for row in rows:
        position = row["changed_observed_coordinate_positions"][0]
        before = row["pre_observed_count_vector"][position]
        after = row["post_observed_count_vector"][position]
        if after < before:
            equations.add(before + 1 - after)
    if len(equations) != 1:
        _fail("anonymous raw differences do not derive one rewrite cardinality")
    return next(iter(equations))


def _source_confirmation(
    selected_field_index: int,
    rewrite_cardinality: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], int, int]:
    seed = pre.SOURCE_CONFIRMATION_SEED
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.SOURCE_SPEC)
    del witness
    layout = _layout(kernel, seed)
    state = kernel.initial_distribution()[0][1]
    plan, evaluations, peak = _plan(
        kernel, layout, state, selected_field_index, rewrite_cardinality
    )
    rows = []
    for plan_index, action in enumerate(plan):
        predicted = _model_step(
            kernel,
            layout,
            state,
            action,
            selected_field_index,
            rewrite_cardinality,
        )
        outcome = kernel.step(state, action)[0]
        if outcome.next_state != predicted:
            _fail("anonymous source confirmation differs from derived program")
        rows.append(
            _observation(
                stage="MODEL_DERIVED_CONFIRMATION",
                seed=seed,
                index=plan_index,
                kernel=kernel,
                layout=layout,
                state=state,
                action=action,
                successor=outcome.next_state,
                plan_prefix=[
                    candidate.tile
                    for candidate in plan[
                        plan_index : plan_index + pre.RECEDING_HORIZON
                    ]
                ],
            )
        )
        state = outcome.next_state
    if state.status is not LMBStatus.SUCCESS or len(rows) != pre.SOURCE_SPEC["tile_count"]:
        _fail("anonymous source confirmation did not reach full-removal success")
    return rows, _layout_document(layout), evaluations, peak


def _expression_node_count(value: Any) -> int:
    if type(value) is list:
        return 1 + sum(_expression_node_count(item) for item in value)
    return 1


def _contains_operator(value: Any, operator: str) -> bool:
    return type(value) is list and (
        (bool(value) and value[0] == operator)
        or any(_contains_operator(item, operator) for item in value[1:])
    )


def _semantic_output(
    feature_values: dict[str, Any], rewrite_cardinality: int
) -> dict[str, Any]:
    selected_count = feature_values["selected_count"]
    next_selected_count = (selected_count + 1) % rewrite_cardinality
    post_capacity_slack = (
        feature_values["capacity_slack"]
        - (next_selected_count - selected_count)
    )
    failure = post_capacity_slack < 0
    status = (
        "failure"
        if failure
        else "success"
        if feature_values["will_remove_last_tile"]
        else "active"
    )
    return {
        "next_selected_count": next_selected_count,
        "failure": failure,
        "post_status": status,
    }


def _derive_dependency_signature(
    expressions: list[list[Any]], rewrite_cardinality: int
) -> dict[str, Any]:
    by_name = {expression[0]: expression[1] for expression in expressions}
    next_count_expression = by_name.get("next_selected_count")
    failure_expression = by_name.get("failure")
    board_empty_expression = by_name.get("board_empty")
    if (
        not _contains_operator(next_count_expression, "MODULO")
        or not _contains_operator(failure_expression, "GREATER_THAN")
        or not _contains_operator(board_empty_expression, "ALL_REGISTERED_TILES_REMOVED")
    ):
        _fail("compiled program lacks a preregistered semantic dependency root")
    selected_feature = next_count_expression[1][1]
    pre_load_features = [
        name
        for name, expression in by_name.items()
        if expression == ["SUM_VECTOR", "PRE_OBSERVED_COUNT_VECTOR"]
    ]
    if len(pre_load_features) != 1 or failure_expression[-1] != "INSTANCE_CAPACITY":
        _fail("compiled comparison dependencies are not uniquely recoverable")
    raw_roots = [
        selected_feature,
        pre_load_features[0],
        failure_expression[-1].lower(),
        "remaining_tile_count_before_action",
    ]
    if pre.DEPENDENCY_MINIMIZATION != {
        "initial_roots": "INPUTS_TO_JOIN_MODULO_COMPARISON_AND_TERMINAL_BRANCH_NODES",
        "comparison_normalization": "REPLACE_CAPACITY_AND_PRE_LOAD_WITH_CAPACITY_MINUS_PRE_LOAD",
        "terminal_normalization": "REPLACE_UPDATED_SET_WITH_WILL_REMOVE_LAST_TILE",
        "deletion_rule": "REMOVE_FEATURE_EXACTLY_DERIVABLE_FROM_RETAINED_FEATURES",
        "tie_break": "LEXICOGRAPHIC_CANONICAL_TYPED_AST_BYTES",
        "support_signature_fields_predeclared": [],
        "expected_support_signature_predeclared": False,
    }:
        _fail("dependency minimization rule changed")
    normalization_steps = [
        {
            "remove": [pre_load_features[0], failure_expression[-1].lower()],
            "insert": "capacity_slack",
            "justification": "GREATER_THAN_TRANSLATION_INVARIANT",
        },
        {
            "remove": ["remaining_tile_count_before_action"],
            "insert": "will_remove_last_tile",
            "justification": "SET_INSERT_TERMINAL_BRANCH_NORMAL_FORM",
        },
    ]
    candidates = [selected_feature, "capacity_slack", "will_remove_last_tile"]
    assignments = [
        {
            "selected_count": selected_count,
            "capacity_slack": capacity_slack,
            "will_remove_last_tile": will_remove_last_tile,
        }
        for selected_count in range(rewrite_cardinality)
        for capacity_slack in range(rewrite_cardinality + 2)
        for will_remove_last_tile in (False, True)
    ]
    deletion_trials = []
    deletion_assignment_evaluations = 0
    for removed_feature in candidates:
        retained = [feature for feature in candidates if feature != removed_feature]
        seen: dict[tuple[Any, ...], tuple[dict[str, Any], dict[str, Any]]] = {}
        counterexample = None
        for values in assignments:
            deletion_assignment_evaluations += 1
            retained_key = tuple(values[feature] for feature in retained)
            output = _semantic_output(values, rewrite_cardinality)
            previous = seen.get(retained_key)
            if previous is not None and previous[1] != output:
                counterexample = {
                    "left_feature_values": previous[0],
                    "left_program_output": previous[1],
                    "right_feature_values": values,
                    "right_program_output": output,
                }
                break
            seen[retained_key] = (values, output)
        deletion_trials.append(
            {
                "removed_feature": removed_feature,
                "counterexample": counterexample,
                "removal_preserves_program_semantics": counterexample is None,
            }
        )
    minimal = [
        trial["removed_feature"]
        for trial in deletion_trials
        if not trial["removal_preserves_program_semantics"]
    ]
    if minimal != candidates or any(
        trial["counterexample"] is None for trial in deletion_trials
    ):
        _fail("dependency deletion did not derive one exact minimal signature")
    return {
        "algorithm": pre.DEPENDENCY_MINIMIZATION,
        "raw_semantic_roots": raw_roots,
        "normalization_steps": normalization_steps,
        "candidate_normalized_features": candidates,
        "deletion_trials": deletion_trials,
        "deletion_assignment_evaluation_count": deletion_assignment_evaluations,
        "minimal_support_signature": minimal,
        "hand_written_structural_support_key_used": False,
        "unique_minimum_under_tie_break": True,
    }


def _ordered_support_key(
    feature_names: list[str], feature_values: dict[str, Any]
) -> tuple[Any, ...]:
    if set(feature_names) != set(feature_values):
        _fail("derived support signature and available semantic values differ")
    return tuple(feature_values[name] for name in feature_names)


def _support_feature_values(
    kernel: LMBKernel,
    layout: _AnonymousLayout,
    state: LMBState,
    action: LMBAction,
    selected_field_index: int,
    feature_names: list[str],
) -> tuple[Any, ...]:
    descriptor = _action_descriptor(kernel, layout, action)
    position = _join_position(layout.coordinate_tokens, descriptor, selected_field_index)
    observed = _observed_counts(state, layout)
    return _ordered_support_key(
        feature_names,
        {
            "selected_count": observed[position],
            "capacity_slack": kernel.capacity - sum(observed),
            "will_remove_last_tile": (
                kernel.tile_count - state.removed_mask.bit_count()
            )
            == 1,
        },
    )


def _row_support_key(
    row: dict[str, Any], selected_field_index: int, feature_names: list[str]
) -> tuple[Any, ...]:
    position = _join_position(
        tuple(row["coordinate_tokens"]),
        tuple(row["action_descriptor_fields"]),
        selected_field_index,
    )
    return _ordered_support_key(
        feature_names,
        {
            "selected_count": row["pre_observed_count_vector"][position],
            "capacity_slack": row["instance_capacity"] - row["pre_load"],
            "will_remove_last_tile": (len(row["legal_action_ids"]) >= 1)
            and (
                row["pre_removed_mask"].bit_count() + 1
                == pre.SOURCE_SPEC["tile_count"]
            ),
        },
    )


def _derive_program() -> tuple[dict[str, Any], set[tuple[Any, ...]]]:
    acquisition_rows, closures = _projection_acquisition()
    candidates = _candidate_projection_fields(acquisition_rows)
    selected_field_index = candidates[0]
    rewrite_cardinality = _derive_rewrite_cardinality(acquisition_rows)
    confirmation_rows, confirmation_layout, source_compute, source_peak = _source_confirmation(
        selected_field_index, rewrite_cardinality
    )
    rows = [*acquisition_rows, *confirmation_rows]
    if _candidate_projection_fields(rows) != [selected_field_index]:
        _fail("fresh confirmation changed the unique descriptor projection")
    for row in rows:
        position = row["changed_observed_coordinate_positions"][0]
        before = row["pre_observed_count_vector"][position]
        after = row["post_observed_count_vector"][position]
        if after != (before + 1) % rewrite_cardinality:
            _fail("anonymous modular update does not fit every source row")
        expected_status = (
            "failure"
            if row["post_load"] > row["instance_capacity"]
            else "success"
            if row["post_board_empty"]
            else "active"
        )
        if row["post_status"] != expected_status:
            _fail("anonymous terminal rule does not fit every source row")
        if row["post_removed_mask"] != row["pre_removed_mask"] | (1 << row["action_id"]):
            _fail("anonymous removed-set rule changed")
    projection_evaluations = []
    for field_index in range(pre.DESCRIPTOR_FIELD_COUNT):
        satisfied = 0
        counterexamples = []
        for row in rows:
            matches = [
                position
                for position, token in enumerate(row["coordinate_tokens"])
                if token == row["action_descriptor_fields"][field_index]
            ]
            if matches == row["changed_observed_coordinate_positions"] and len(matches) == 1:
                satisfied += 1
            else:
                counterexamples.append(row["observation_id"])
        projection_evaluations.append(
            {
                "anonymous_field_index": field_index,
                "satisfied_row_count": satisfied,
                "counterexample_observation_ids": counterexamples,
                "valid_projection": not counterexamples,
            }
        )
    expressions = [
        [
            "operated_coordinate",
            [
                "UNIQUE_EQUALITY_JOIN_INDEX",
                "COORDINATE_TOKENS",
                ["DESCRIPTOR_FIELD", "ACTION_DESCRIPTOR_FIELDS", selected_field_index],
            ],
        ],
        [
            "selected_count",
            ["VECTOR_AT", "PRE_OBSERVED_COUNT_VECTOR", "operated_coordinate"],
        ],
        [
            "next_selected_count",
            ["MODULO", ["ADD_ONE", "selected_count"], rewrite_cardinality],
        ],
        [
            "post_observed_count_vector",
            [
                "VECTOR_UPDATE",
                "PRE_OBSERVED_COUNT_VECTOR",
                "operated_coordinate",
                "next_selected_count",
            ],
        ],
        ["post_removed_set", ["SET_INSERT", "PRE_REMOVED_SET", "ACTION_ID"]],
        ["pre_load", ["SUM_VECTOR", "PRE_OBSERVED_COUNT_VECTOR"]],
        ["post_load", ["SUM_VECTOR", "post_observed_count_vector"]],
        ["failure", ["GREATER_THAN", "post_load", "INSTANCE_CAPACITY"]],
        ["board_empty", ["ALL_REGISTERED_TILES_REMOVED", "post_removed_set"]],
        [
            "post_status",
            [
                "IF_THEN_ELSE",
                "failure",
                "FAILURE",
                ["IF_THEN_ELSE", "board_empty", "SUCCESS", "ACTIVE"],
            ],
        ],
    ]
    dependency_derivation = _derive_dependency_signature(
        expressions, rewrite_cardinality
    )
    support_signature = dependency_derivation["minimal_support_signature"]
    supports = {
        _row_support_key(row, selected_field_index, support_signature) for row in rows
    }
    derivation_compute = (
        pre.DESCRIPTOR_FIELD_COUNT * len(rows)
        + 6 * len(rows)
        + sum(_expression_node_count(expression) for expression in expressions)
        + len(dependency_derivation["raw_semantic_roots"])
        + len(dependency_derivation["normalization_steps"])
        + len(dependency_derivation["deletion_trials"])
        + dependency_derivation["deletion_assignment_evaluation_count"]
    )
    payload = {
        "schema": "acfqp.lmb_anonymous_descriptor_program.v45",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v44_failure_id": pre.V44_FAILURE_ID,
        "v44r1_campaign_id": pre.V44R1_CAMPAIGN_ID,
        "v44r1_verification_id": pre.V44R1_VERIFICATION_ID,
        "typed_relation_grammar": pre.TYPED_RELATION_GRAMMAR,
        "projection_acquisition_observations": acquisition_rows,
        "projection_acquisition_episode_closures": closures,
        "source_confirmation_observations": confirmation_rows,
        "source_confirmation_layout": confirmation_layout,
        "anonymous_projection_evaluations": projection_evaluations,
        "selected_anonymous_descriptor_field_index": selected_field_index,
        "projection_expression": expressions[0],
        "rewrite_cardinality_derivation": {
            "derived_numeric_literal": rewrite_cardinality,
            "numeric_candidate_grid_used": False,
            "all_rows_satisfy_modular_increment": True,
        },
        "compiled_typed_expressions": expressions,
        "dependency_derived_support_signature": dependency_derivation,
        "source_support_keys_from_derived_signature": [
            list(row) for row in sorted(supports)
        ],
        "source_projection_label_count": len(acquisition_rows),
        "source_confirmation_label_count": len(confirmation_rows),
        "total_source_transition_label_count": len(rows),
        "source_program_abstract_transition_evaluation_count": source_compute,
        "source_program_peak_dynamic_program_cache_entries": source_peak,
        "projection_program_dependency_derivation_compute_event_count": (
            derivation_compute
        ),
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "named_action_class_scaffold_present": False,
        "hand_written_structural_support_key_present": False,
        "status": "ANONYMOUS_PROJECTION_PROGRAM_AND_MINIMAL_SIGNATURE_DERIVED",
    }
    return (
        {**payload, "program_id": content_id(pre.FUTURE_DOMAINS["program"], payload)},
        supports,
    )


def _context(
    layout: _AnonymousLayout,
    state: LMBState,
    action: LMBAction,
    descriptor: tuple[int, ...],
) -> str:
    return content_id(
        pre.FUTURE_DOMAINS["distinction"],
        {
            "role": "EXACT_CONTEXT",
            "layout_id": layout.layout_id,
            "state": _state(state),
            "action_id": action.tile,
            "action_descriptor_fields": list(descriptor),
        },
    )


def _certificate(
    *,
    program_id: str,
    arm: str,
    seed: int,
    index: int,
    layout_id: str,
    state: LMBState,
    action: LMBAction,
    descriptor: tuple[int, ...],
    support_key: list[Any],
    status: str,
    failed_id: str | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_anonymous_descriptor_certificate.v45",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "program_id": program_id,
        "arm": arm,
        "episode_seed": seed,
        "decision_index": index,
        "layout_id": layout_id,
        "state": _state(state),
        "action_id": action.tile,
        "action_descriptor_fields": list(descriptor),
        "support_key": support_key,
        "status": status,
        "failed_certificate_id": failed_id,
        "kernel_step_during_planning": False,
    }
    return {
        **payload,
        "certificate_id": content_id(pre.FUTURE_DOMAINS["distinction"], payload),
    }


def _episode(
    *,
    seed: int,
    arm: str,
    program_id: str,
    selected_field_index: int,
    rewrite_cardinality: int,
    support_signature: list[str],
    source_supports: set[tuple[Any, ...]],
) -> dict[str, Any]:
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.TARGET_SPEC)
    del witness
    layout = _layout(kernel, seed)
    state = kernel.initial_distribution()[0][1]
    derived_overlay: set[tuple[int, int, bool]] = set()
    context_overlay: set[str] = set()
    decisions = []
    labels = 0
    abstract_compute = 0
    certificate_compute = 0
    peak = 0
    while state.status is LMBStatus.ACTIVE:
        index = len(decisions)
        plan, evaluations, plan_peak = _plan(
            kernel,
            layout,
            state,
            selected_field_index,
            rewrite_cardinality,
        )
        abstract_compute += evaluations
        peak = max(peak, plan_peak)
        action = plan[0]
        descriptor = _action_descriptor(kernel, layout, action)
        predicted = _model_step(
            kernel,
            layout,
            state,
            action,
            selected_field_index,
            rewrite_cardinality,
        )
        derived_key = _support_feature_values(
            kernel,
            layout,
            state,
            action,
            selected_field_index,
            support_signature,
        )
        context_key = _context(layout, state, action, descriptor)
        support_key = list(derived_key) if arm == pre.ARMS[0] else [context_key]
        supported = (
            derived_key in source_supports or derived_key in derived_overlay
            if arm == pre.ARMS[0]
            else context_key in context_overlay
        )
        initial = _certificate(
            program_id=program_id,
            arm=arm,
            seed=seed,
            index=index,
            layout_id=layout.layout_id,
            state=state,
            action=action,
            descriptor=descriptor,
            support_key=support_key,
            status="CERTIFIED_MODEL_SUPPORT" if supported else "FAILED_MISSING_SUPPORT",
            failed_id=None,
        )
        certificate_compute += 1
        distinction = None
        exact = None
        final = initial
        replanned = False
        if not supported:
            exact = kernel.step(state, action)[0]
            labels += 1
            distinction_payload = {
                "schema": "acfqp.lmb_dependency_derived_local_distinction.v45",
                "schema_version": pre.SCHEMA_VERSION,
                "preregistration_id": pre.PREREGISTRATION_ID,
                "program_id": program_id,
                "failed_certificate_id": initial["certificate_id"],
                "arm": arm,
                "episode_seed": seed,
                "decision_index": index,
                "layout_id": layout.layout_id,
                "coordinate_tokens": list(layout.coordinate_tokens),
                "pre_observed_count_vector": list(_observed_counts(state, layout)),
                "action_id": action.tile,
                "action_descriptor_fields": list(descriptor),
                "support_key": support_key,
                "observed_successor": _state(exact.next_state),
                "observed_successor_count_vector": list(
                    _observed_counts(exact.next_state, layout)
                ),
                "observed_failure": exact.failure,
                "observed_terminal": exact.terminal,
                "acquired_after_failed_certificate": True,
            }
            distinction = {
                **distinction_payload,
                "distinction_id": content_id(
                    pre.FUTURE_DOMAINS["distinction"], distinction_payload
                ),
            }
            if arm == pre.ARMS[0]:
                derived_overlay.add(derived_key)
            else:
                context_overlay.add(context_key)
            repeated, repeated_evaluations, repeated_peak = _plan(
                kernel,
                layout,
                state,
                selected_field_index,
                rewrite_cardinality,
            )
            abstract_compute += repeated_evaluations
            peak = max(peak, repeated_peak)
            if repeated[0] != action:
                _fail("local distinction changed anonymous derived-program action")
            replanned = True
            final = _certificate(
                program_id=program_id,
                arm=arm,
                seed=seed,
                index=index,
                layout_id=layout.layout_id,
                state=state,
                action=action,
                descriptor=descriptor,
                support_key=support_key,
                status="CERTIFIED_AFTER_LOCAL_DISTINCTION",
                failed_id=initial["certificate_id"],
            )
            certificate_compute += 1
        outcome = exact or kernel.step(state, action)[0]
        if outcome.next_state != predicted:
            _fail("held-out execution differs from anonymous derived program")
        decisions.append(
            {
                "decision_index": index,
                "source_state": _state(state),
                "observed_source_count_vector": list(_observed_counts(state, layout)),
                "coordinate_tokens": list(layout.coordinate_tokens),
                "plan_prefix_action_ids": [candidate.tile for candidate in plan[: pre.RECEDING_HORIZON]],
                "selected_action_id": action.tile,
                "selected_action_descriptor_fields": list(descriptor),
                "derived_operated_coordinate_position": _join_position(
                    layout.coordinate_tokens, descriptor, selected_field_index
                ),
                "predicted_successor": _state(predicted),
                "predicted_successor_count_vector": list(_observed_counts(predicted, layout)),
                "initial_certificate": initial,
                "local_distinction": distinction,
                "replanned_after_local_distinction": replanned,
                "final_certificate": final,
                "executed_successor": _state(outcome.next_state),
                "executed_successor_count_vector": list(
                    _observed_counts(outcome.next_state, layout)
                ),
                "model_matches_execution": True,
            }
        )
        state = outcome.next_state
    if (
        state.status is not LMBStatus.SUCCESS
        or len(decisions) != pre.TARGET_SPEC["tile_count"]
        or labels > pre.MAX_TARGET_LOCAL_LABELS_PER_EPISODE
    ):
        _fail("V45 held-out episode did not close within preregistered bounds")
    payload = {
        "schema": "acfqp.lmb_anonymous_descriptor_episode.v45",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "program_id": program_id,
        "arm": arm,
        "episode_seed": seed,
        "instance_specification": pre.TARGET_SPEC,
        "anonymous_layout": _layout_document(layout),
        "decisions": decisions,
        "terminal_state": _state(state),
        "full_board_cleared": True,
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "target_local_distinction_label_count": labels,
        "execution_environment_step_count": len(decisions),
        "abstract_transition_evaluation_count": abstract_compute,
        "certificate_evaluation_count": certificate_compute,
        "peak_dynamic_program_cache_entries": peak,
        "labels_steps_and_compute_separate": True,
    }
    return {**payload, "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload)}


def _source_binding() -> dict[str, Any]:
    facts = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        facts.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return {
        "schema": "acfqp.lmb_anonymous_descriptor_source_binding.v45",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v44r1_campaign_id": pre.V44R1_CAMPAIGN_ID,
        "v44r1_verification_id": pre.V44R1_VERIFICATION_ID,
        "source_facts": facts,
        "full_producer_source_closure_claimed": False,
        "producer_free_verification_required": True,
    }


def build_lmb_anonymous_descriptor_campaign_document_v45() -> dict[str, Any]:
    registration = pre.freeze_lmb_anonymous_descriptor_preregistration_v45()
    pre.verify_lmb_anonymous_descriptor_preregistration_v45(registration)
    program, supports = _derive_program()
    selected_field_index = program["selected_anonymous_descriptor_field_index"]
    rewrite_cardinality = program["rewrite_cardinality_derivation"]["derived_numeric_literal"]
    support_signature = program["dependency_derived_support_signature"][
        "minimal_support_signature"
    ]
    episodes = [
        _episode(
            seed=seed,
            arm=arm,
            program_id=program["program_id"],
            selected_field_index=selected_field_index,
            rewrite_cardinality=rewrite_cardinality,
            support_signature=support_signature,
            source_supports=supports,
        )
        for arm in pre.ARMS
        for seed in pre.HELDOUT_SEEDS
    ]
    structural = episodes[: len(pre.HELDOUT_SEEDS)]
    control = episodes[len(pre.HELDOUT_SEEDS) :]
    structural_labels = sum(row["target_local_distinction_label_count"] for row in structural)
    control_labels = sum(row["target_local_distinction_label_count"] for row in control)
    if not structural_labels < control_labels:
        _fail("dependency-derived signature did not reduce target labels")
    source_layout_ids = {
        row["layout_id"] for row in program["projection_acquisition_observations"]
    } | {program["source_confirmation_layout"]["layout_id"]}
    target_layout_ids = {episode["anonymous_layout"]["layout_id"] for episode in episodes}
    if source_layout_ids & target_layout_ids:
        _fail("source and target anonymous layout identities overlap")
    source_coordinate_tokens = {
        token
        for row in program["projection_acquisition_observations"]
        for token in row["coordinate_tokens"]
    } | set(program["source_confirmation_layout"]["coordinate_tokens"])
    target_coordinate_tokens = {
        token
        for episode in episodes
        for token in episode["anonymous_layout"]["coordinate_tokens"]
    }
    if source_coordinate_tokens & target_coordinate_tokens:
        _fail("source and target anonymous descriptor namespaces overlap")
    source_descriptor_values = {
        value
        for row in [
            *program["projection_acquisition_observations"],
            *program["source_confirmation_observations"],
        ]
        for value in row["action_descriptor_fields"]
    }
    target_descriptor_values = {
        value
        for episode in episodes
        for decision in episode["decisions"]
        for value in decision["selected_action_descriptor_fields"]
    }
    if source_descriptor_values & target_descriptor_values:
        _fail("source and target anonymous action-descriptor values overlap")
    payload = {
        "schema": "acfqp.lmb_anonymous_descriptor_campaign.v45",
        "schema_version": pre.SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v41_campaign_id": pre.V41_CAMPAIGN_ID,
        "v41_verification_id": pre.V41_VERIFICATION_ID,
        "v42_campaign_id": pre.V42_CAMPAIGN_ID,
        "v42_verification_id": pre.V42_VERIFICATION_ID,
        "v43_campaign_id": pre.V43_CAMPAIGN_ID,
        "v43_verification_id": pre.V43_VERIFICATION_ID,
        "v44_preregistration_id": pre.V44_PREREGISTRATION_ID,
        "v44_failure_id": pre.V44_FAILURE_ID,
        "v44r1_preregistration_id": pre.V44R1_PREREGISTRATION_ID,
        "v44r1_campaign_id": pre.V44R1_CAMPAIGN_ID,
        "v44r1_verification_id": pre.V44R1_VERIFICATION_ID,
        "source_binding": _source_binding(),
        "derived_program": program,
        "episodes": episodes,
        "summary": {
            "source_projection_label_count": program["source_projection_label_count"],
            "source_confirmation_label_count": program["source_confirmation_label_count"],
            "total_source_transition_label_count": program[
                "total_source_transition_label_count"
            ],
            "structural_meta_prior_target_label_count": structural_labels,
            "strict_no_prior_target_label_count": control_labels,
            "target_label_fraction": Fraction(structural_labels, control_labels),
            "heldout_episode_count_per_arm": len(pre.HELDOUT_SEEDS),
            "execution_environment_step_count_per_arm": sum(
                row["execution_environment_step_count"] for row in structural
            ),
            "source_abstract_compute_events": program[
                "source_program_abstract_transition_evaluation_count"
            ],
            "projection_program_dependency_derivation_compute_events": program[
                "projection_program_dependency_derivation_compute_event_count"
            ],
            "structural_abstract_compute_events": sum(
                row["abstract_transition_evaluation_count"]
                + row["certificate_evaluation_count"]
                for row in structural
            ),
            "control_abstract_compute_events": sum(
                row["abstract_transition_evaluation_count"]
                + row["certificate_evaluation_count"]
                for row in control
            ),
            "all_episodes_completed": all(row["full_board_cleared"] for row in episodes),
            "all_local_labels_follow_failed_certificates": all(
                decision["local_distinction"] is None
                or decision["local_distinction"]["failed_certificate_id"]
                == decision["initial_certificate"]["certificate_id"]
                for episode in episodes
                for decision in episode["decisions"]
            ),
            "source_target_layout_id_sets_disjoint": True,
            "source_target_descriptor_value_namespaces_disjoint": True,
            "source_target_coordinate_token_namespaces_disjoint": True,
            "descriptor_values_and_coordinate_order_permuted_on_target": True,
            "all_target_coordinate_orders_nonidentity": all(
                episode["anonymous_layout"]["coordinate_order_is_nonidentity"]
                for episode in episodes
            ),
            "source_generation_witness_access_count": 0,
            "target_generation_witness_access_count": 0,
            "planning_kernel_step_count": 0,
            "labels_steps_and_compute_separate": True,
        },
        "verified_scope_candidate": (
            "REGISTERED_ANONYMOUS_DESCRIPTOR_PERMUTED_LMB_WORKLOAD_V45"
        ),
        "named_action_class_scaffold_present": False,
        "hand_written_structural_support_key_present": False,
        "open_ended_descriptor_or_grammar_invention_claimed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {**payload, "campaign_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBAnonymousDescriptorCampaignV45:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V45 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V45 campaign bytes changed")
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            document.get("campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("V45 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V45 campaign is not an object")
        return value


def run_lmb_anonymous_descriptor_campaign_v45(
    output_path: str | Path | None = None,
) -> LMBAnonymousDescriptorCampaignV45:
    document = build_lmb_anonymous_descriptor_campaign_document_v45()
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        identity != EXPECTED_CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V45 campaign changed")
    if output_path is not None:
        Path(output_path).write_bytes(raw)
    return LMBAnonymousDescriptorCampaignV45(_ISSUER, raw, identity)


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "LMBAnonymousDescriptorCampaignV45",
    "build_lmb_anonymous_descriptor_campaign_document_v45",
    "run_lmb_anonymous_descriptor_campaign_v45",
)
