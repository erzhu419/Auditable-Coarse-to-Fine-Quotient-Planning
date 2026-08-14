"""Preserved invalid V46 attempt with out-of-grammar compiled constructors."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
import random
from typing import Any, NoReturn

from acfqp import construction_k7_lmb_opaque_column_preregistration_v46 as pre
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.domains.standard_2048 import ACTION_ORDER as STANDARD_2048_ACTIONS
from acfqp.domains.standard_2048 import CELL_COUNT as STANDARD_2048_CELL_COUNT
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


PROFILE_KEY = "construction_k7_lmb_opaque_column_campaign_v46"
ATTEMPT_VALID = False
EXPECTED_ATTEMPTED_CAMPAIGN_ID = "7eca22a5292256d98898f4dfaeed48efce058a5becec12ad70b44f35f6c59ce2"
EXPECTED_ATTEMPTED_CANONICAL_BYTE_COUNT = 1_023_797
EXPECTED_ATTEMPTED_CANONICAL_SHA256 = "69724c529497d6f6219a4da4fd5491626765e6869ea3552171687d391b105df7"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_lmb_opaque_column_preregistration_v46.py",
    "src/acfqp/domains/matching_buffer.py",
    "src/acfqp/domains/standard_2048.py",
)


class ConstructionK7LMBOpaqueColumnCampaignV46Error(ValueError):
    """The opaque factorization, program, OOD decision, plan, or evidence changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBOpaqueColumnCampaignV46Error(message)


def _semantic_state(state: LMBState) -> dict[str, Any]:
    return {
        "removed_mask": state.removed_mask,
        "buffer_counts": list(state.buffer),
        "status": state.status.value,
    }


@dataclass(frozen=True, slots=True)
class _OpaqueLayout:
    occurrence_seed: int
    observed_to_semantic_column: tuple[int, ...]
    action_group_values_by_internal_type: tuple[int, ...]
    status_values: tuple[int, int, int]
    layout_id: str


def _layout(kernel: LMBKernel, occurrence_seed: int) -> _OpaqueLayout:
    observed_to_semantic = list(range(kernel.type_count + pre.STATE_EXTRA_COLUMN_COUNT))
    random.Random(occurrence_seed ^ pre.FLAT_COLUMN_ORDER_SALT).shuffle(
        observed_to_semantic
    )
    group_permutation = list(range(kernel.type_count))
    random.Random(occurrence_seed ^ pre.ACTION_VALUE_SALT).shuffle(group_permutation)
    group_values = tuple(
        30_000_000 + occurrence_seed * 100 + group_permutation[index]
        for index in range(kernel.type_count)
    )
    status_values = (
        50_000_000 + occurrence_seed * 10 + 1,
        50_000_000 + occurrence_seed * 10 + 2,
        50_000_000 + occurrence_seed * 10 + 3,
    )
    payload = {
        "role": "OPAQUE_FLAT_LAYOUT",
        "occurrence_seed": occurrence_seed,
        "flat_column_count": len(observed_to_semantic),
        "action_metadata_field_count": pre.ACTION_METADATA_FIELD_COUNT,
        "column_order_commitment": content_id(
            pre.FUTURE_DOMAINS["factorization"],
            {"role": "COLUMN_ORDER", "order": observed_to_semantic},
        ),
        "action_value_namespace_commitment": content_id(
            pre.FUTURE_DOMAINS["factorization"],
            {"role": "ACTION_VALUE_NAMESPACE", "values": list(group_values)},
        ),
        "state_column_semantic_names_exposed": False,
        "action_metadata_semantic_names_exposed": False,
        "coordinate_tokens_present": False,
        "direct_cross_interface_equal_values_present": False,
    }
    return _OpaqueLayout(
        occurrence_seed,
        tuple(observed_to_semantic),
        group_values,
        status_values,
        content_id(pre.FUTURE_DOMAINS["factorization"], payload),
    )


def _layout_document(layout: _OpaqueLayout) -> dict[str, Any]:
    return {
        "layout_id": layout.layout_id,
        "occurrence_seed": layout.occurrence_seed,
        "flat_column_count": len(layout.observed_to_semantic_column),
        "action_metadata_field_count": pre.ACTION_METADATA_FIELD_COUNT,
        "column_order_commitment": content_id(
            pre.FUTURE_DOMAINS["factorization"],
            {
                "role": "COLUMN_ORDER",
                "order": list(layout.observed_to_semantic_column),
            },
        ),
        "action_value_namespace_commitment": content_id(
            pre.FUTURE_DOMAINS["factorization"],
            {
                "role": "ACTION_VALUE_NAMESPACE",
                "values": list(layout.action_group_values_by_internal_type),
            },
        ),
        "state_column_semantic_names_exposed": False,
        "action_metadata_semantic_names_exposed": False,
        "coordinate_tokens_present": False,
        "direct_cross_interface_equal_values_present": False,
    }


def _flat_state(kernel: LMBKernel, layout: _OpaqueLayout, state: LMBState) -> tuple[int, ...]:
    status_index = {
        LMBStatus.ACTIVE: 0,
        LMBStatus.FAILURE: 1,
        LMBStatus.SUCCESS: 2,
    }[state.status]
    semantic = (
        state.removed_mask,
        *state.buffer,
        layout.status_values[status_index],
        kernel.capacity,
    )
    return tuple(semantic[index] for index in layout.observed_to_semantic_column)


def _action_metadata(
    kernel: LMBKernel, layout: _OpaqueLayout, action: LMBAction
) -> tuple[int, int, int]:
    seed = layout.occurrence_seed
    return (
        20_000_000 + seed * 1_000 + action.tile,
        layout.action_group_values_by_internal_type[kernel.tile_types[action.tile]],
        40_000_000 + seed * 100 + len(kernel.blockers[action.tile]),
    )


def _observation(
    *,
    stage: str,
    seed: int,
    index: int,
    kernel: LMBKernel,
    layout: _OpaqueLayout,
    state: LMBState,
    action: LMBAction,
    successor: LMBState,
    plan_prefix: list[int] | None,
) -> dict[str, Any]:
    pre_columns = _flat_state(kernel, layout, state)
    post_columns = _flat_state(kernel, layout, successor)
    changed = [
        position
        for position, (left, right) in enumerate(zip(pre_columns, post_columns))
        if left != right
    ]
    payload = {
        "schema": "acfqp.lmb_opaque_column_observation.v46",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "stage": stage,
        "occurrence_seed": seed,
        "decision_index": index,
        "layout_id": layout.layout_id,
        "pre_flat_columns": list(pre_columns),
        "legal_action_ids": [candidate.tile for candidate in kernel.actions(state)],
        "action_id": action.tile,
        "action_metadata_fields": list(_action_metadata(kernel, layout, action)),
        "post_flat_columns": list(post_columns),
        "changed_flat_column_indices": changed,
        "observed_failure": successor.status is LMBStatus.FAILURE,
        "observed_terminal": successor.status is not LMBStatus.ACTIVE,
        "source_plan_prefix_action_ids": plan_prefix,
        "state_column_roles_exposed": False,
        "action_metadata_roles_exposed": False,
        "coordinate_tokens_present": False,
        "source_planning_kernel_step": False,
        "source_generation_witness_accessed": False,
    }
    return {
        **payload,
        "observation_id": content_id(pre.FUTURE_DOMAINS["observation"], payload),
    }


def _derive_cyclic_cardinality(rows: list[dict[str, Any]]) -> int | None:
    equations = {
        before + 1 - after
        for row in rows
        for before, after in zip(row["pre_flat_columns"], row["post_flat_columns"])
        if after < before
    }
    equations = {value for value in equations if value > 1}
    if not equations:
        return None
    if len(equations) != 1:
        _fail("raw flat-column decreases do not derive one cyclic cardinality")
    return next(iter(equations))


def _column_factorization(
    rows: list[dict[str, Any]],
    *,
    tile_count: int,
    cardinality: int,
    expected_capacity: int | None = None,
) -> dict[str, Any]:
    if not rows:
        _fail("opaque factorization requires raw observations")
    width = len(rows[0]["pre_flat_columns"])
    dynamic_columns = []
    for column in range(width):
        transitions = [
            (row["pre_flat_columns"][column], row["post_flat_columns"][column])
            for row in rows
        ]
        if any(left != right for left, right in transitions) and all(
            right == left or right == (left + 1) % cardinality
            for left, right in transitions
        ):
            dynamic_columns.append(column)
    if not dynamic_columns:
        _fail("no cyclic dynamic columns were derived")
    removed_candidates = [
        column
        for column in range(width)
        if all(
            row["post_flat_columns"][column]
            == row["pre_flat_columns"][column] | (1 << row["action_id"])
            for row in rows
        )
    ]
    if len(removed_candidates) != 1:
        _fail("opaque rows do not identify one monotone insertion column")
    removed_column = removed_candidates[0]
    terminal_candidates = [
        column
        for column in range(width)
        if any(
            row["post_flat_columns"][column] != row["pre_flat_columns"][column]
            for row in rows
        )
        and all(
            (
                row["post_flat_columns"][column]
                != row["pre_flat_columns"][column]
            )
            == row["observed_terminal"]
            for row in rows
        )
    ]
    terminal_candidates = [
        column
        for column in terminal_candidates
        if column not in dynamic_columns and column != removed_column
    ]
    if len(terminal_candidates) != 1:
        _fail("opaque rows do not identify one terminal-change column")
    terminal_column = terminal_candidates[0]
    post_loads = [
        sum(row["post_flat_columns"][column] for column in dynamic_columns)
        for row in rows
    ]
    failure_loads = [
        load for row, load in zip(rows, post_loads) if row["observed_failure"]
    ]
    if expected_capacity is None:
        if not failure_loads:
            _fail("source acquisition lacks a capacity-boundary failure")
        capacity = min(failure_loads) - 1
    else:
        capacity = expected_capacity
    if any(
        (load > capacity) != row["observed_failure"]
        for row, load in zip(rows, post_loads)
    ):
        _fail("derived cyclic columns and capacity do not explain failure rows")
    constant_columns = [
        column
        for column in range(width)
        if all(
            row["pre_flat_columns"][column]
            == row["post_flat_columns"][column]
            == rows[0]["pre_flat_columns"][column]
            for row in rows
        )
    ]
    capacity_candidates = [
        column
        for column in constant_columns
        if rows[0]["pre_flat_columns"][column] == capacity
    ]
    if len(capacity_candidates) != 1:
        _fail("opaque constant columns do not identify one capacity column")
    capacity_column = capacity_candidates[0]
    changed_dynamic_by_row = []
    for row in rows:
        changed = [
            column
            for column in dynamic_columns
            if row["pre_flat_columns"][column]
            != row["post_flat_columns"][column]
        ]
        if len(changed) != 1:
            _fail("one action did not change exactly one derived dynamic column")
        changed_dynamic_by_row.append(changed[0])
    field_scores = []
    field_relations = []
    for field_index in range(pre.ACTION_METADATA_FIELD_COUNT):
        groups: dict[int, list[int]] = {}
        for row, changed_column in zip(rows, changed_dynamic_by_row):
            groups.setdefault(row["action_metadata_fields"][field_index], []).append(
                changed_column
            )
        residual = 0
        relation = []
        mapped_columns = []
        for value, columns in sorted(groups.items()):
            counts = {column: columns.count(column) for column in set(columns)}
            selected_column = min(
                counts, key=lambda column: (-counts[column], column)
            )
            residual += len(columns) - counts[selected_column]
            mapped_columns.append(selected_column)
            relation.append(
                {
                    "field_value": value,
                    "changed_dynamic_column_index": selected_column,
                    "supporting_row_count": counts[selected_column],
                }
            )
        collisions = len(mapped_columns) - len(set(mapped_columns))
        singleton_groups = sum(len(columns) == 1 for columns in groups.values())
        score = [
            residual,
            collisions,
            len(groups),
            singleton_groups,
            5,
            field_index,
        ]
        field_scores.append(
            {
                "anonymous_field_index": field_index,
                "mdl_score": score,
                "residual_error_count": residual,
                "semantic_exception_count": collisions,
                "group_to_column_mapping_count": len(groups),
                "singleton_group_count": singleton_groups,
            }
        )
        field_relations.append(relation)
    selected_score = min(row["mdl_score"] for row in field_scores)
    selected_fields = [
        row["anonymous_field_index"]
        for row in field_scores
        if row["mdl_score"] == selected_score
    ]
    if len(selected_fields) != 1:
        _fail("opaque action-field relation has no unique MDL minimum")
    selected_field = selected_fields[0]
    payload = {
        "schema": "acfqp.lmb_column_factorization.v46",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "layout_id": rows[0]["layout_id"],
        "occurrence_seed": rows[0]["occurrence_seed"],
        "tile_count": tile_count,
        "flat_column_count": width,
        "cyclic_cardinality": cardinality,
        "dynamic_column_indices": dynamic_columns,
        "removed_set_column_index": removed_column,
        "terminal_column_index": terminal_column,
        "capacity_column_index": capacity_column,
        "derived_capacity_value": capacity,
        "anonymous_action_field_scores": field_scores,
        "selected_anonymous_action_field_index": selected_field,
        "selected_group_to_changed_column_relation": field_relations[selected_field],
        "predeclared_state_column_roles_used": False,
        "coordinate_token_equality_join_used": False,
        "status": "OPAQUE_COLUMNS_AND_ACTION_RELATION_FACTORIZED",
    }
    return {
        **payload,
        "factorization_id": content_id(
            pre.FUTURE_DOMAINS["factorization"], payload
        ),
    }


def _source_acquisition() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], int, int
]:
    all_rows: list[dict[str, Any]] = []
    episode_rows: list[list[dict[str, Any]]] = []
    layouts: list[_OpaqueLayout] = []
    terminals: list[str] = []
    cardinality = None
    for seed in pre.SOURCE_ACQUISITION_SEEDS:
        kernel, witness = generate_solvable_lmb(seed=seed, **pre.SOURCE_SPEC)
        del witness
        layout = _layout(kernel, seed)
        state = kernel.initial_distribution()[0][1]
        rows = []
        while state.status is LMBStatus.ACTIVE:
            action = min(kernel.actions(state), key=lambda candidate: candidate.tile)
            outcome = kernel.step(state, action)[0]
            row = _observation(
                stage="OPAQUE_SOURCE_ACQUISITION",
                seed=seed,
                index=len(rows),
                kernel=kernel,
                layout=layout,
                state=state,
                action=action,
                successor=outcome.next_state,
                plan_prefix=None,
            )
            rows.append(row)
            all_rows.append(row)
            state = outcome.next_state
            if len(all_rows) > pre.MAX_SOURCE_ACQUISITION_LABELS:
                _fail("opaque source acquisition exceeded preregistered label cap")
        episode_rows.append(rows)
        layouts.append(layout)
        terminals.append(state.status.value)
        cardinality = _derive_cyclic_cardinality(all_rows)
        if cardinality is not None:
            factorizations = [
                _column_factorization(
                    occurrence_rows,
                    tile_count=pre.SOURCE_SPEC["tile_count"],
                    cardinality=cardinality,
                )
                for occurrence_rows in episode_rows
            ]
            selected = {
                factorization["selected_anonymous_action_field_index"]
                for factorization in factorizations
            }
            if (
                len(selected) == 1
                and max(
                    len(factorization["dynamic_column_indices"])
                    for factorization in factorizations
                )
                >= pre.MIN_DYNAMIC_COLUMN_COUNT
            ):
                break
    if cardinality is None:
        _fail("source rows did not derive a cyclic cardinality")
    factorizations = [
        _column_factorization(
            rows,
            tile_count=pre.SOURCE_SPEC["tile_count"],
            cardinality=cardinality,
        )
        for rows in episode_rows
    ]
    aggregate_scores = []
    for field_index in range(pre.ACTION_METADATA_FIELD_COUNT):
        component_rows = [
            factorization["anonymous_action_field_scores"][field_index]
            for factorization in factorizations
        ]
        score = [
            sum(row["residual_error_count"] for row in component_rows),
            sum(row["semantic_exception_count"] for row in component_rows),
            sum(row["group_to_column_mapping_count"] for row in component_rows),
            sum(row["singleton_group_count"] for row in component_rows),
            5,
            field_index,
        ]
        aggregate_scores.append(
            {"anonymous_field_index": field_index, "aggregate_mdl_score": score}
        )
    selected_score = min(row["aggregate_mdl_score"] for row in aggregate_scores)
    selected_fields = [
        row["anonymous_field_index"]
        for row in aggregate_scores
        if row["aggregate_mdl_score"] == selected_score
    ]
    if len(selected_fields) != 1:
        _fail("source occurrences do not select one global action field")
    selected_field = selected_fields[0]
    closures = [
        {
            "occurrence_seed": layout.occurrence_seed,
            "opaque_layout": _layout_document(layout),
            "transition_label_count": len(rows),
            "terminal_status": terminal,
            "factorization_id": factorization["factorization_id"],
            "dynamic_column_count": len(factorization["dynamic_column_indices"]),
            "selected_anonymous_action_field_index": factorization[
                "selected_anonymous_action_field_index"
            ],
            "global_stop_requirements_satisfied_after_episode": index
            == len(episode_rows) - 1,
        }
        for index, (layout, rows, terminal, factorization) in enumerate(
            zip(layouts, episode_rows, terminals, factorizations)
        )
    ]
    return all_rows, closures, factorizations, cardinality, selected_field


@dataclass(frozen=True, slots=True)
class _AbstractState:
    removed_mask: int
    group_counts: tuple[int, ...]
    status: LMBStatus


def _group_values(kernel: LMBKernel, layout: _OpaqueLayout, field_index: int) -> tuple[int, ...]:
    return tuple(
        sorted(
            {
                _action_metadata(kernel, layout, LMBAction(tile))[field_index]
                for tile in range(kernel.tile_count)
            }
        )
    )


def _abstract_from_lmb(
    kernel: LMBKernel,
    layout: _OpaqueLayout,
    state: LMBState,
    selected_field_index: int,
) -> _AbstractState:
    groups = _group_values(kernel, layout, selected_field_index)
    counts_by_group = {group: 0 for group in groups}
    for internal_type, count in enumerate(state.buffer):
        group = layout.action_group_values_by_internal_type[internal_type]
        counts_by_group[group] = count
    return _AbstractState(
        state.removed_mask,
        tuple(counts_by_group[group] for group in groups),
        state.status,
    )


def _abstract_step(
    kernel: LMBKernel,
    layout: _OpaqueLayout,
    state: _AbstractState,
    action: LMBAction,
    selected_field_index: int,
    rewrite_cardinality: int,
    capacity: int,
) -> _AbstractState:
    groups = _group_values(kernel, layout, selected_field_index)
    group_index = {group: index for index, group in enumerate(groups)}
    action_group = _action_metadata(kernel, layout, action)[selected_field_index]
    counts = list(state.group_counts)
    index = group_index[action_group]
    counts[index] = (counts[index] + 1) % rewrite_cardinality
    removed = state.removed_mask | (1 << action.tile)
    load = sum(counts)
    board_empty = removed == (1 << kernel.tile_count) - 1
    status = (
        LMBStatus.FAILURE
        if load > capacity
        else LMBStatus.SUCCESS
        if board_empty
        else LMBStatus.ACTIVE
    )
    return _AbstractState(removed, tuple(counts), status)


def _plan(
    kernel: LMBKernel,
    layout: _OpaqueLayout,
    state: _AbstractState,
    selected_field_index: int,
    rewrite_cardinality: int,
    capacity: int,
) -> tuple[tuple[LMBAction, ...], int, int]:
    memo: dict[_AbstractState, tuple[LMBAction, ...] | None] = {}
    evaluations = 0
    peak = 0

    def legal_actions(current: _AbstractState) -> tuple[LMBAction, ...]:
        return kernel.actions(
            LMBState(
                current.removed_mask,
                (0,) * kernel.type_count,
                current.status,
            )
        )

    def solve(current: _AbstractState) -> tuple[LMBAction, ...] | None:
        nonlocal evaluations, peak
        if current.status is LMBStatus.SUCCESS:
            return ()
        if current.status is LMBStatus.FAILURE:
            return None
        if current in memo:
            return memo[current]
        candidates = []
        for action in legal_actions(current):
            successor = _abstract_step(
                kernel,
                layout,
                current,
                action,
                selected_field_index,
                rewrite_cardinality,
                capacity,
            )
            evaluations += 1
            rewrite = sum(successor.group_counts) < sum(current.group_counts)
            available = (
                len(legal_actions(successor))
                if successor.status is LMBStatus.ACTIVE
                else 0
            )
            candidates.append(
                (
                    (-int(rewrite), sum(successor.group_counts), -available, action.tile),
                    action,
                    successor,
                )
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
        _fail("opaque-column abstract program found no successful continuation")
    return result, evaluations, peak


def _source_confirmation(
    selected_field_index: int, rewrite_cardinality: int
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], int, int]:
    seed = pre.SOURCE_CONFIRMATION_SEED
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.SOURCE_SPEC)
    del witness
    layout = _layout(kernel, seed)
    state = kernel.initial_distribution()[0][1]
    abstract = _abstract_from_lmb(kernel, layout, state, selected_field_index)
    plan, evaluations, peak = _plan(
        kernel,
        layout,
        abstract,
        selected_field_index,
        rewrite_cardinality,
        kernel.capacity,
    )
    rows = []
    for plan_index, action in enumerate(plan):
        predicted = _abstract_step(
            kernel,
            layout,
            abstract,
            action,
            selected_field_index,
            rewrite_cardinality,
            kernel.capacity,
        )
        outcome = kernel.step(state, action)[0]
        actual_abstract = _abstract_from_lmb(
            kernel, layout, outcome.next_state, selected_field_index
        )
        if actual_abstract != predicted:
            _fail("fresh source confirmation differs from opaque derived program")
        rows.append(
            _observation(
                stage="OPAQUE_MODEL_DERIVED_CONFIRMATION",
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
        abstract = actual_abstract
    if state.status is not LMBStatus.SUCCESS or len(rows) != pre.SOURCE_SPEC["tile_count"]:
        _fail("opaque source confirmation did not reach full-removal success")
    factorization = _column_factorization(
        rows,
        tile_count=pre.SOURCE_SPEC["tile_count"],
        cardinality=rewrite_cardinality,
        expected_capacity=pre.SOURCE_SPEC["capacity"],
    )
    if factorization["selected_anonymous_action_field_index"] != selected_field_index:
        _fail("confirmation changed the selected anonymous action field")
    return rows, _layout_document(layout), factorization, evaluations, peak


def _contains_operator(value: Any, operator: str) -> bool:
    return type(value) is list and (
        (bool(value) and value[0] == operator)
        or any(_contains_operator(item, operator) for item in value[1:])
    )


def _expression_node_count(value: Any) -> int:
    if type(value) is list:
        return 1 + sum(_expression_node_count(item) for item in value)
    return 1


def _semantic_output(values: dict[str, Any], cardinality: int) -> dict[str, Any]:
    selected = values["selected_count"]
    next_selected = (selected + 1) % cardinality
    post_slack = values["capacity_slack"] - (next_selected - selected)
    failure = post_slack < 0
    status = (
        "failure"
        if failure
        else "success"
        if values["will_remove_last_action"]
        else "active"
    )
    return {
        "next_selected_count": next_selected,
        "failure": failure,
        "post_status": status,
    }


def _derive_support_signature(
    expressions: list[list[Any]], cardinality: int
) -> dict[str, Any]:
    by_name = {row[0]: row[1] for row in expressions}
    if (
        not _contains_operator(by_name.get("next_selected_count"), "MODULO")
        or not _contains_operator(by_name.get("failure"), "GREATER_THAN")
        or not _contains_operator(by_name.get("post_status"), "IF_THEN_ELSE")
    ):
        _fail("compiled opaque program lacks support dependency roots")
    candidates = ["selected_count", "capacity_slack", "will_remove_last_action"]
    assignments = [
        {
            "selected_count": selected,
            "capacity_slack": slack,
            "will_remove_last_action": last,
        }
        for selected in range(cardinality)
        for slack in range(cardinality + 2)
        for last in (False, True)
    ]
    deletion_trials = []
    evaluation_count = 0
    for removed in candidates:
        retained = [feature for feature in candidates if feature != removed]
        seen: dict[tuple[Any, ...], tuple[dict[str, Any], dict[str, Any]]] = {}
        counterexample = None
        for values in assignments:
            evaluation_count += 1
            key = tuple(values[feature] for feature in retained)
            output = _semantic_output(values, cardinality)
            previous = seen.get(key)
            if previous is not None and previous[1] != output:
                counterexample = {
                    "left_feature_values": previous[0],
                    "left_program_output": previous[1],
                    "right_feature_values": values,
                    "right_program_output": output,
                }
                break
            seen[key] = (values, output)
        deletion_trials.append(
            {
                "removed_feature": removed,
                "counterexample": counterexample,
                "removal_preserves_program_semantics": counterexample is None,
            }
        )
    minimal = [
        row["removed_feature"]
        for row in deletion_trials
        if row["counterexample"] is not None
    ]
    if minimal != candidates:
        _fail("opaque program dependencies do not derive the unique finite minimum")
    return {
        "raw_dependency_roots_derived_from_compiled_ast": [
            "selected_count",
            "pre_load",
            "capacity_value",
            "remaining_action_count",
        ],
        "normalization_steps": [
            {
                "remove": ["pre_load", "capacity_value"],
                "insert": "capacity_slack",
                "justification": "GREATER_THAN_TRANSLATION_INVARIANT",
            },
            {
                "remove": ["remaining_action_count"],
                "insert": "will_remove_last_action",
                "justification": "SINGLE_BIT_INSERTION_TERMINAL_NORMAL_FORM",
            },
        ],
        "candidate_normalized_features": candidates,
        "deletion_trials": deletion_trials,
        "deletion_assignment_evaluation_count": evaluation_count,
        "minimal_support_signature": minimal,
        "support_signature_fields_predeclared": [],
        "unique_minimum_under_tie_break": True,
    }


def _factorization_map(factorization: dict[str, Any]) -> dict[int, int]:
    return {
        row["field_value"]: row["changed_dynamic_column_index"]
        for row in factorization["selected_group_to_changed_column_relation"]
    }


def _source_support_key(
    row: dict[str, Any],
    factorization: dict[str, Any],
    signature: list[str],
) -> tuple[Any, ...]:
    selected_field = factorization["selected_anonymous_action_field_index"]
    group = row["action_metadata_fields"][selected_field]
    mapping = _factorization_map(factorization)
    selected_count = row["pre_flat_columns"][mapping[group]]
    pre_load = sum(
        row["pre_flat_columns"][column]
        for column in factorization["dynamic_column_indices"]
    )
    capacity = row["pre_flat_columns"][factorization["capacity_column_index"]]
    removed = row["pre_flat_columns"][factorization["removed_set_column_index"]]
    values = {
        "selected_count": selected_count,
        "capacity_slack": capacity - pre_load,
        "will_remove_last_action": removed.bit_count() + 1
        == factorization["tile_count"],
    }
    return tuple(values[feature] for feature in signature)


def _derive_program() -> tuple[dict[str, Any], set[tuple[Any, ...]]]:
    (
        acquisition_rows,
        closures,
        acquisition_factorizations,
        cardinality,
        selected_field,
    ) = _source_acquisition()
    (
        confirmation_rows,
        confirmation_layout,
        confirmation_factorization,
        source_compute,
        source_peak,
    ) = _source_confirmation(selected_field, cardinality)
    expressions = [
        ["dynamic_columns", ["MDL_SELECT", "COLUMN_TRANSITION_TRACES"]],
        ["action_groups", ["FIELD_VALUE_PARTITION", "ACTION_METADATA", selected_field]],
        [
            "action_to_dynamic_column",
            ["PARTITION_TO_CHANGED_COLUMN_RELATION", "action_groups", "dynamic_columns"],
        ],
        ["selected_count", ["RELATION_VECTOR_AT", "PRE_COLUMNS", "action_to_dynamic_column"]],
        ["next_selected_count", ["MODULO", ["ADD_ONE", "selected_count"], cardinality]],
        ["post_dynamic_columns", ["RELATION_VECTOR_UPDATE", "PRE_COLUMNS", "action_to_dynamic_column", "next_selected_count"]],
        ["post_removed_set", ["MONOTONE_SINGLE_BIT_INSERTION", "PRE_REMOVED_SET", "ACTION_ID"]],
        ["pre_load", ["SUM_PARTITION", "PRE_COLUMNS", "dynamic_columns"]],
        ["post_load", ["SUM_PARTITION", "post_dynamic_columns", "dynamic_columns"]],
        ["failure", ["GREATER_THAN", "post_load", "FACTORIZED_CAPACITY_COLUMN"]],
        ["board_empty", ["ALL_ACTION_IDS_INSERTED", "post_removed_set"]],
        ["post_status", ["IF_THEN_ELSE", "failure", "FAILURE", ["IF_THEN_ELSE", "board_empty", "SUCCESS", "ACTIVE"]]],
    ]
    support = _derive_support_signature(expressions, cardinality)
    signature = support["minimal_support_signature"]
    supports: set[tuple[Any, ...]] = set()
    by_layout = {
        factorization["layout_id"]: factorization
        for factorization in [
            *acquisition_factorizations,
            confirmation_factorization,
        ]
    }
    for row in [*acquisition_rows, *confirmation_rows]:
        supports.add(_source_support_key(row, by_layout[row["layout_id"]], signature))
    factorization_payload = {
        "schema": "acfqp.lmb_cross_occurrence_factorization.v46",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "source_occurrence_factorizations": acquisition_factorizations,
        "source_confirmation_factorization": confirmation_factorization,
        "selected_anonymous_action_field_index": selected_field,
        "cyclic_cardinality": cardinality,
        "state_column_roles_predeclared": False,
        "coordinate_token_equality_join_used": False,
        "status": "CROSS_OCCURRENCE_OPAQUE_FACTORIZATION_DERIVED",
    }
    cross_factorization = {
        **factorization_payload,
        "cross_occurrence_factorization_id": content_id(
            pre.FUTURE_DOMAINS["factorization"], factorization_payload
        ),
    }
    derivation_compute = (
        len(acquisition_rows) * pre.ACTION_METADATA_FIELD_COUNT
        + len(confirmation_rows) * pre.ACTION_METADATA_FIELD_COUNT
        + sum(_expression_node_count(row) for row in expressions)
        + support["deletion_assignment_evaluation_count"]
        + sum(
            len(factorization["dynamic_column_indices"])
            * len(
                next(
                    rows
                    for rows in (
                        [
                            row
                            for row in acquisition_rows
                            if row["layout_id"] == factorization["layout_id"]
                        ],
                        confirmation_rows,
                    )
                    if rows and rows[0]["layout_id"] == factorization["layout_id"]
                )
            )
            for factorization in [
                *acquisition_factorizations,
                confirmation_factorization,
            ]
        )
    )
    payload = {
        "schema": "acfqp.lmb_opaque_relation_program.v46",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v45_campaign_id": pre.V45_CAMPAIGN_ID,
        "v45_verification_id": pre.V45_VERIFICATION_ID,
        "generic_relation_meta_grammar": pre.GENERIC_RELATION_META_GRAMMAR,
        "mdl_and_dependency_rule": pre.MDL_AND_DEPENDENCY_RULE,
        "source_acquisition_observations": acquisition_rows,
        "source_acquisition_episode_closures": closures,
        "cross_occurrence_factorization": cross_factorization,
        "source_confirmation_observations": confirmation_rows,
        "source_confirmation_layout": confirmation_layout,
        "compiled_typed_expressions": expressions,
        "dependency_derived_support_signature": support,
        "source_support_keys_from_derived_signature": [
            list(row) for row in sorted(supports)
        ],
        "source_acquisition_label_count": len(acquisition_rows),
        "source_confirmation_label_count": len(confirmation_rows),
        "total_source_transition_label_count": len(acquisition_rows)
        + len(confirmation_rows),
        "source_program_abstract_transition_evaluation_count": source_compute,
        "source_program_peak_dynamic_program_cache_entries": source_peak,
        "factorization_relation_program_dependency_compute_event_count": derivation_compute,
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "state_column_roles_predeclared": False,
        "coordinate_token_equality_scaffold_present": False,
        "status": "OPAQUE_FACTORIZATION_RELATION_PROGRAM_DERIVED",
    }
    return {
        **payload,
        "program_id": content_id(pre.FUTURE_DOMAINS["program"], payload),
    }, supports


def _context(
    layout_id: str,
    state: _AbstractState,
    action: LMBAction,
    metadata: tuple[int, ...],
) -> str:
    return content_id(
        pre.FUTURE_DOMAINS["distinction"],
        {
            "role": "EXACT_OPAQUE_CONTEXT",
            "layout_id": layout_id,
            "abstract_removed_mask": state.removed_mask,
            "abstract_group_counts": list(state.group_counts),
            "action_id": action.tile,
            "action_metadata_fields": list(metadata),
        },
    )


def _certificate(
    *,
    program_id: str,
    arm: str,
    seed: int,
    index: int,
    layout_id: str,
    state: _AbstractState,
    action: LMBAction,
    metadata: tuple[int, ...],
    support_key: list[Any],
    relation_mapping_present: bool,
    status: str,
    failed_id: str | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_opaque_factorized_certificate.v46",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "program_id": program_id,
        "arm": arm,
        "episode_seed": seed,
        "decision_index": index,
        "layout_id": layout_id,
        "abstract_removed_mask": state.removed_mask,
        "abstract_group_counts": list(state.group_counts),
        "action_id": action.tile,
        "action_metadata_fields": list(metadata),
        "support_key": support_key,
        "target_relation_mapping_present": relation_mapping_present,
        "status": status,
        "failed_certificate_id": failed_id,
        "kernel_step_during_planning": False,
    }
    return {
        **payload,
        "certificate_id": content_id(pre.FUTURE_DOMAINS["distinction"], payload),
    }


def _support_key_from_abstract(
    state: _AbstractState,
    group_index: int,
    capacity: int,
    tile_count: int,
    signature: list[str],
) -> tuple[Any, ...]:
    values = {
        "selected_count": state.group_counts[group_index],
        "capacity_slack": capacity - sum(state.group_counts),
        "will_remove_last_action": state.removed_mask.bit_count() + 1 == tile_count,
    }
    return tuple(values[feature] for feature in signature)


def _episode(
    *,
    seed: int,
    arm: str,
    program: dict[str, Any],
    source_supports: set[tuple[Any, ...]],
) -> dict[str, Any]:
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.TARGET_SPEC)
    del witness
    layout = _layout(kernel, seed)
    selected_field = program["cross_occurrence_factorization"][
        "selected_anonymous_action_field_index"
    ]
    cardinality = program["cross_occurrence_factorization"]["cyclic_cardinality"]
    signature = program["dependency_derived_support_signature"][
        "minimal_support_signature"
    ]
    groups = _group_values(kernel, layout, selected_field)
    group_index = {group: index for index, group in enumerate(groups)}
    state = kernel.initial_distribution()[0][1]
    abstract = _abstract_from_lmb(kernel, layout, state, selected_field)
    relation_overlay: dict[int, int] = {}
    support_overlay: set[tuple[Any, ...]] = set()
    context_overlay: set[str] = set()
    decisions = []
    labels = 0
    abstract_compute = 0
    certificate_compute = 0
    factorization_compute = 0
    peak = 0
    while state.status is LMBStatus.ACTIVE:
        index = len(decisions)
        plan, evaluations, plan_peak = _plan(
            kernel,
            layout,
            abstract,
            selected_field,
            cardinality,
            kernel.capacity,
        )
        abstract_compute += evaluations
        peak = max(peak, plan_peak)
        action = plan[0]
        metadata = _action_metadata(kernel, layout, action)
        action_group = metadata[selected_field]
        group_position = group_index[action_group]
        predicted = _abstract_step(
            kernel,
            layout,
            abstract,
            action,
            selected_field,
            cardinality,
            kernel.capacity,
        )
        derived_key = _support_key_from_abstract(
            abstract,
            group_position,
            kernel.capacity,
            kernel.tile_count,
            signature,
        )
        context_key = _context(layout.layout_id, abstract, action, metadata)
        relation_supported = action_group in relation_overlay
        if arm == pre.ARMS[0]:
            support_key = list(derived_key)
            supported = relation_supported and (
                derived_key in source_supports or derived_key in support_overlay
            )
        else:
            support_key = [context_key]
            supported = context_key in context_overlay
        initial = _certificate(
            program_id=program["program_id"],
            arm=arm,
            seed=seed,
            index=index,
            layout_id=layout.layout_id,
            state=abstract,
            action=action,
            metadata=metadata,
            support_key=support_key,
            relation_mapping_present=relation_supported,
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
            pre_columns = _flat_state(kernel, layout, state)
            post_columns = _flat_state(kernel, layout, exact.next_state)
            dynamic_candidates = [
                column
                for column, (left, right) in enumerate(zip(pre_columns, post_columns))
                if right == (left + 1) % cardinality
            ]
            if len(dynamic_candidates) != 1:
                _fail("failed certificate did not reveal one cyclic target column")
            changed_dynamic_column = dynamic_candidates[0]
            factorization_compute += len(pre_columns)
            if arm == pre.ARMS[0]:
                prior = relation_overlay.get(action_group)
                if prior is not None and prior != changed_dynamic_column:
                    _fail("target relation overlay changed its mapped column")
                relation_overlay[action_group] = changed_dynamic_column
                support_overlay.add(derived_key)
            else:
                context_overlay.add(context_key)
            distinction_payload = {
                "schema": "acfqp.lmb_factorized_local_distinction.v46",
                "schema_version": pre.SCHEMA_VERSION,
                "preregistration_id": pre.PREREGISTRATION_ID,
                "program_id": program["program_id"],
                "failed_certificate_id": initial["certificate_id"],
                "arm": arm,
                "episode_seed": seed,
                "decision_index": index,
                "layout_id": layout.layout_id,
                "pre_flat_columns": list(pre_columns),
                "action_id": action.tile,
                "action_metadata_fields": list(metadata),
                "post_flat_columns": list(post_columns),
                "changed_flat_column_indices": [
                    column
                    for column, (left, right) in enumerate(
                        zip(pre_columns, post_columns)
                    )
                    if left != right
                ],
                "derived_changed_dynamic_column_index": changed_dynamic_column,
                "support_key": support_key,
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
            repeated, repeated_evaluations, repeated_peak = _plan(
                kernel,
                layout,
                abstract,
                selected_field,
                cardinality,
                kernel.capacity,
            )
            abstract_compute += repeated_evaluations
            peak = max(peak, repeated_peak)
            if repeated[0] != action:
                _fail("local factorization changed the derived-program action")
            replanned = True
            final = _certificate(
                program_id=program["program_id"],
                arm=arm,
                seed=seed,
                index=index,
                layout_id=layout.layout_id,
                state=abstract,
                action=action,
                metadata=metadata,
                support_key=support_key,
                relation_mapping_present=(
                    action_group in relation_overlay if arm == pre.ARMS[0] else False
                ),
                status="CERTIFIED_AFTER_LOCAL_DISTINCTION",
                failed_id=initial["certificate_id"],
            )
            certificate_compute += 1
        outcome = exact or kernel.step(state, action)[0]
        actual_abstract = _abstract_from_lmb(
            kernel, layout, outcome.next_state, selected_field
        )
        if actual_abstract != predicted:
            _fail("held-out execution differs from opaque derived program")
        decisions.append(
            {
                "decision_index": index,
                "source_abstract_state": {
                    "removed_mask": abstract.removed_mask,
                    "group_counts": list(abstract.group_counts),
                    "status": abstract.status.value,
                },
                "observed_source_flat_columns": list(
                    _flat_state(kernel, layout, state)
                ),
                "plan_prefix_action_ids": [
                    candidate.tile for candidate in plan[: pre.RECEDING_HORIZON]
                ],
                "selected_action_id": action.tile,
                "selected_action_metadata_fields": list(metadata),
                "selected_anonymous_action_field_index": selected_field,
                "predicted_successor_abstract_state": {
                    "removed_mask": predicted.removed_mask,
                    "group_counts": list(predicted.group_counts),
                    "status": predicted.status.value,
                },
                "initial_certificate": initial,
                "local_distinction": distinction,
                "replanned_after_local_distinction": replanned,
                "final_certificate": final,
                "executed_successor": _semantic_state(outcome.next_state),
                "executed_successor_flat_columns": list(
                    _flat_state(kernel, layout, outcome.next_state)
                ),
                "model_matches_execution": True,
                "successful_execution_retained_as_ground_distinction": False,
            }
        )
        state = outcome.next_state
        abstract = actual_abstract
    if (
        state.status is not LMBStatus.SUCCESS
        or len(decisions) != pre.TARGET_SPEC["tile_count"]
        or labels > pre.MAX_TARGET_LOCAL_LABELS_PER_EPISODE
    ):
        _fail("V46 held-out episode did not close within preregistered bounds")
    if arm == pre.ARMS[0] and len(relation_overlay) != pre.TARGET_SPEC["type_count"]:
        _fail("derived arm did not locally close every fresh action group")
    payload = {
        "schema": "acfqp.lmb_factorized_episode.v46",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "program_id": program["program_id"],
        "arm": arm,
        "episode_seed": seed,
        "instance_specification": pre.TARGET_SPEC,
        "opaque_layout": _layout_document(layout),
        "decisions": decisions,
        "terminal_state": _semantic_state(state),
        "full_board_cleared": True,
        "derived_relation_mapping_count": len(relation_overlay),
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "target_local_distinction_label_count": labels,
        "execution_environment_step_count": len(decisions),
        "abstract_transition_evaluation_count": abstract_compute,
        "certificate_evaluation_count": certificate_compute,
        "target_factorization_compute_event_count": factorization_compute,
        "peak_dynamic_program_cache_entries": peak,
        "labels_steps_and_compute_separate": True,
    }
    return {
        **payload,
        "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


def _ood_rejection(program: dict[str, Any]) -> dict[str, Any]:
    selected_field = program["cross_occurrence_factorization"][
        "selected_anonymous_action_field_index"
    ]
    control = pre.OOD_CONTROL
    if (
        control["flat_state_column_count"] != STANDARD_2048_CELL_COUNT
        or len(STANDARD_2048_ACTIONS) != 4
    ):
        _fail("registered 2048 OOD schema disagrees with the bound domain source")
    schema_compatible = (
        control["action_metadata_field_count"] > selected_field
        and control["registered_lmb_relation_assumptions_present"]
    )
    if schema_compatible:
        _fail("registered cross-domain OOD control unexpectedly accepts the prior")
    payload = {
        "schema": "acfqp.lmb_opaque_schema_ood_rejection.v46",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "program_id": program["program_id"],
        "control": control,
        "selected_action_field_index_required_by_program": selected_field,
        "bound_standard_2048_cell_count": STANDARD_2048_CELL_COUNT,
        "bound_standard_2048_action_count": len(STANDARD_2048_ACTIONS),
        "schema_compatible": False,
        "decision": "OOD_SCHEMA_REJECTED_NO_TRANSFER",
        "prior_access_count": 0,
        "overlay_access_count": 0,
        "transition_outcome_access_count": 0,
        "target_label_count": 0,
        "environment_step_count": 0,
        "schema_evaluation_compute_event_count": 4,
        "status": "TYPED_OOD_NO_TRANSFER_VERIFIED",
    }
    return {**payload, "ood_rejection_id": content_id(pre.FUTURE_DOMAINS["ood"], payload)}


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
        "schema": "acfqp.lmb_opaque_column_source_binding.v46",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v45_campaign_id": pre.V45_CAMPAIGN_ID,
        "v45_verification_id": pre.V45_VERIFICATION_ID,
        "source_facts": facts,
        "full_producer_source_closure_claimed": False,
        "producer_free_verification_required": True,
    }


def build_lmb_opaque_column_campaign_document_v46() -> dict[str, Any]:
    registration = pre.freeze_lmb_opaque_column_preregistration_v46()
    pre.verify_lmb_opaque_column_preregistration_v46(registration)
    program, supports = _derive_program()
    episodes = [
        _episode(seed=seed, arm=arm, program=program, source_supports=supports)
        for arm in pre.ARMS
        for seed in pre.HELDOUT_SEEDS
    ]
    structural = episodes[: len(pre.HELDOUT_SEEDS)]
    control = episodes[len(pre.HELDOUT_SEEDS) :]
    structural_labels = sum(row["target_local_distinction_label_count"] for row in structural)
    control_labels = sum(row["target_local_distinction_label_count"] for row in control)
    if not structural_labels < control_labels:
        _fail("opaque factorized relation did not reduce target labels")
    source_layout_ids = {
        row["layout_id"] for row in program["source_acquisition_observations"]
    } | {program["source_confirmation_layout"]["layout_id"]}
    target_layout_ids = {episode["opaque_layout"]["layout_id"] for episode in episodes}
    if source_layout_ids & target_layout_ids:
        _fail("source and target opaque layout identities overlap")
    source_action_values = {
        value
        for row in [
            *program["source_acquisition_observations"],
            *program["source_confirmation_observations"],
        ]
        for value in row["action_metadata_fields"]
    }
    target_action_values = {
        value
        for episode in episodes
        for decision in episode["decisions"]
        for value in decision["selected_action_metadata_fields"]
    }
    if source_action_values & target_action_values:
        _fail("source and target opaque action-value namespaces overlap")
    ood = _ood_rejection(program)
    payload = {
        "schema": "acfqp.lmb_opaque_column_campaign.v46",
        "schema_version": pre.SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v41_campaign_id": pre.V41_CAMPAIGN_ID,
        "v41_verification_id": pre.V41_VERIFICATION_ID,
        "v42_campaign_id": pre.V42_CAMPAIGN_ID,
        "v42_verification_id": pre.V42_VERIFICATION_ID,
        "v43_campaign_id": pre.V43_CAMPAIGN_ID,
        "v43_verification_id": pre.V43_VERIFICATION_ID,
        "v44_failure_id": pre.V44_FAILURE_ID,
        "v44r1_campaign_id": pre.V44R1_CAMPAIGN_ID,
        "v44r1_verification_id": pre.V44R1_VERIFICATION_ID,
        "v45_preregistration_id": pre.V45_PREREGISTRATION_ID,
        "v45_campaign_id": pre.V45_CAMPAIGN_ID,
        "v45_verification_id": pre.V45_VERIFICATION_ID,
        "source_binding": _source_binding(),
        "derived_program": program,
        "episodes": episodes,
        "ood_no_transfer": ood,
        "summary": {
            "source_acquisition_label_count": program["source_acquisition_label_count"],
            "source_confirmation_label_count": program["source_confirmation_label_count"],
            "total_source_transition_label_count": program["total_source_transition_label_count"],
            "structural_target_label_count": structural_labels,
            "strict_no_prior_target_label_count": control_labels,
            "target_label_fraction": Fraction(structural_labels, control_labels),
            "heldout_episode_count_per_arm": len(pre.HELDOUT_SEEDS),
            "execution_environment_step_count_per_arm": sum(
                row["execution_environment_step_count"] for row in structural
            ),
            "source_abstract_compute_events": program[
                "source_program_abstract_transition_evaluation_count"
            ],
            "factorization_relation_program_dependency_compute_events": program[
                "factorization_relation_program_dependency_compute_event_count"
            ],
            "structural_abstract_compute_events": sum(
                row["abstract_transition_evaluation_count"]
                + row["certificate_evaluation_count"]
                + row["target_factorization_compute_event_count"]
                for row in structural
            ),
            "control_abstract_compute_events": sum(
                row["abstract_transition_evaluation_count"]
                + row["certificate_evaluation_count"]
                + row["target_factorization_compute_event_count"]
                for row in control
            ),
            "ood_target_label_count": ood["target_label_count"],
            "ood_environment_step_count": ood["environment_step_count"],
            "ood_schema_evaluation_compute_events": ood[
                "schema_evaluation_compute_event_count"
            ],
            "all_episodes_completed": all(row["full_board_cleared"] for row in episodes),
            "all_local_labels_follow_failed_certificates": all(
                decision["local_distinction"] is None
                or decision["local_distinction"]["failed_certificate_id"]
                == decision["initial_certificate"]["certificate_id"]
                for episode in episodes
                for decision in episode["decisions"]
            ),
            "source_target_layout_id_sets_disjoint": True,
            "source_target_action_value_namespaces_disjoint": True,
            "ood_prior_access_count": 0,
            "source_generation_witness_access_count": 0,
            "target_generation_witness_access_count": 0,
            "planning_kernel_step_count": 0,
            "labels_steps_and_compute_separate": True,
        },
        "verified_scope_candidate": "REGISTERED_OPAQUE_COLUMN_LMB_AND_TYPED_2048_OOD_V46",
        "state_column_roles_predeclared": False,
        "coordinate_token_equality_scaffold_present": False,
        "open_ended_relation_grammar_invention_claimed": False,
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
class LMBOpaqueColumnFailedAttemptV46:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    attempted_campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V46 failed attempt is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V46 failed-attempt bytes changed")
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            document.get("campaign_id") != self.attempted_campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload)
            != self.attempted_campaign_id
        ):
            _fail("V46 failed-attempt identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V46 failed attempt is not an object")
        return value


def freeze_lmb_opaque_column_failed_attempt_v46(
    output_path: str | Path | None = None,
) -> LMBOpaqueColumnFailedAttemptV46:
    document = build_lmb_opaque_column_campaign_document_v46()
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if (
        identity != EXPECTED_ATTEMPTED_CAMPAIGN_ID
        or len(raw) != EXPECTED_ATTEMPTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_ATTEMPTED_CANONICAL_SHA256
    ):
        _fail("frozen V46 failed attempt changed")
    if output_path is not None:
        Path(output_path).write_bytes(raw)
    return LMBOpaqueColumnFailedAttemptV46(_ISSUER, raw, identity)


__all__ = (
    "ATTEMPT_VALID",
    "EXPECTED_ATTEMPTED_CAMPAIGN_ID",
    "EXPECTED_ATTEMPTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_ATTEMPTED_CANONICAL_SHA256",
    "LMBOpaqueColumnFailedAttemptV46",
    "build_lmb_opaque_column_campaign_document_v46",
    "freeze_lmb_opaque_column_failed_attempt_v46",
)
