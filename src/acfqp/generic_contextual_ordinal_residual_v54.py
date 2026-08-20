"""Generic occurrence-local ordinal residual expressions.

V83 showed a residual coordinate whose update was encoded by an anonymous
categorical action field.  The concrete integer tokens changed between source
occurrences, while their within-occurrence order represented the same update.
This module adds one generic operator: the one-based ordinal of an action-field
value in that occurrence's catalogue support.  The support is derived from
action metadata only; no successor, terminal label, family name, or coordinate
role is used.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp.phase3e_ids import canonical_json_bytes


class GenericContextualOrdinalResidualV54Error(ValueError):
    pass


RESIDUAL_EXPRESSION_OPCODES_V54 = (
    ("R00", "SELF"),
    ("R01", "ACTION_FIELD"),
    ("R02", "ANONYMOUS_INTEGER_CONSTANT"),
    ("R03", "INT_ADD"),
    ("R04", "FINITE_SUPPORT_PAIR"),
    ("R05", "CONTEXT_LOCAL_ACTION_FIELD_ORDINAL_ONE_BASED"),
)


def _fail(message: str) -> NoReturn:
    raise GenericContextualOrdinalResidualV54Error(message)


def attach_contextual_action_supports_v54(
    structural_group: Mapping[str, Any],
    source_members: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Attach outcome-free per-member action-field supports to pooled evidence."""
    if type(structural_group) is not dict or type(source_members) is not dict:
        _fail("V54 structural source inventory changed")
    evidence = structural_group.get("source_evidence")
    member_ids = structural_group.get("source_member_ids")
    if type(evidence) is not dict or type(member_ids) is not list or not member_ids:
        _fail("V54 structural group changed")
    layout = evidence.get("layout")
    rows = evidence.get("raw_transition_rows")
    if type(layout) is not dict or type(rows) is not list or not rows:
        _fail("V54 source evidence changed")
    action_colors = layout.get("action_structural_colors")
    if type(action_colors) is not list or not action_colors:
        _fail("V54 action structure changed")

    contexts = []
    for context_index, member_id in enumerate(member_ids):
        member = source_members.get(member_id)
        member_evidence = member.get("source_evidence") if type(member) is dict else None
        member_layout = (
            member_evidence.get("layout") if type(member_evidence) is dict else None
        )
        catalogue = member.get("action_catalogue") if type(member) is dict else None
        if (
            type(member_id) is not str
            or type(member_layout) is not dict
            or member_layout.get("action_structural_colors") != action_colors
            or type(catalogue) is not list
            or not catalogue
        ):
            _fail("V54 source-member action catalogue changed")
        order = member_layout.get("action_canonical_to_raw")
        if type(order) is not list or sorted(order) != list(range(len(order))):
            _fail("V54 member action projection changed")
        canonical_actions = []
        for action in catalogue:
            key = action.get("action_key") if type(action) is dict else None
            fields = action.get("anonymous_fields") if type(action) is dict else None
            if (
                type(key) is not int
                or type(fields) is not list
                or len(fields) != len(order)
                or any(type(value) is not int for value in fields)
            ):
                _fail("V54 anonymous action metadata changed")
            canonical_actions.append(
                {
                    "action_key": key,
                    "canonical_fields": [fields[index] for index in order],
                }
            )
        canonical_actions.sort(key=lambda row: row["action_key"])
        if len({row["action_key"] for row in canonical_actions}) != len(
            canonical_actions
        ):
            _fail("V54 action keys changed")
        field_supports = [
            sorted({row["canonical_fields"][field] for row in canonical_actions})
            for field in range(len(order))
        ]
        contexts.append(
            {
                "context_index": context_index,
                "source_member_id": member_id,
                "canonical_action_count": len(canonical_actions),
                "canonical_action_sha256": hashlib.sha256(
                    canonical_json_bytes(canonical_actions)
                ).hexdigest(),
                "action_field_supports": field_supports,
            }
        )

    projected = copy.deepcopy(evidence)
    projected_rows = projected["raw_transition_rows"]
    for row in projected_rows:
        context_index = row.get("canonical_source_pool_member_index", 0)
        if type(context_index) is not int or not 0 <= context_index < len(contexts):
            _fail("V54 row-to-context projection changed")
        row["contextual_source_member_index"] = context_index
    projected["contextual_action_field_supports"] = contexts
    projected["contextual_action_supports_derived_from_catalogue_only"] = True
    projected["unacquired_successor_or_terminal_used_for_action_supports"] = False
    payload = {
        "source_evidence_sha256": hashlib.sha256(
            canonical_json_bytes(evidence)
        ).hexdigest(),
        "contextual_action_field_supports": contexts,
        "row_context_projection": [
            row["contextual_source_member_index"] for row in projected_rows
        ],
    }
    projected["contextual_action_support_projection_id"] = hashlib.sha256(
        b"acfqp:generic-contextual-action-support-projection:v54\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return projected


def _supports(evidence: Mapping[str, Any]) -> dict[int, tuple[tuple[int, ...], ...]]:
    contexts = evidence.get("contextual_action_field_supports")
    if type(contexts) is not list or not contexts:
        _fail("V54 contextual action supports changed")
    result = {}
    field_count = None
    for expected_index, row in enumerate(contexts):
        index = row.get("context_index") if type(row) is dict else None
        supports = row.get("action_field_supports") if type(row) is dict else None
        if (
            index != expected_index
            or type(row.get("source_member_id")) is not str
            or type(supports) is not list
            or not supports
        ):
            _fail("V54 context support row changed")
        if field_count is None:
            field_count = len(supports)
        if len(supports) != field_count:
            _fail("V54 contextual action width changed")
        frozen = []
        for support in supports:
            if (
                type(support) is not list
                or not support
                or support != sorted(set(support))
                or any(type(value) is not int for value in support)
            ):
                _fail("V54 action-field support changed")
            frozen.append(tuple(support))
        result[index] = tuple(frozen)
    return result


def _aligned_batches(
    evidence: Mapping[str, Any], groups: list[list[dict[str, Any]]]
) -> list[list[tuple[int, tuple[int, ...], tuple[int, ...], tuple[int, ...]]]]:
    layout = evidence.get("layout")
    if type(layout) is not dict:
        _fail("V54 layout changed")
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    supports = _supports(evidence)
    if type(state_order) is not list or type(action_order) is not list:
        _fail("V54 layout projections changed")
    result = []
    for group in groups:
        batch = []
        for row in group:
            selected = row.get("selected_action") if type(row) is dict else None
            pre = row.get("pre_vector") if type(row) is dict else None
            post = row.get("post_vector") if type(row) is dict else None
            action = selected.get("anonymous_fields") if type(selected) is dict else None
            context = row.get("contextual_source_member_index") if type(row) is dict else None
            if (
                type(pre) is not list
                or type(post) is not list
                or type(action) is not list
                or type(context) is not int
                or context not in supports
                or sorted(state_order) != list(range(len(pre)))
                or len(post) != len(pre)
                or sorted(action_order) != list(range(len(action)))
                or len(action_order) != len(supports[context])
            ):
                _fail("V54 contextual transition alignment changed")
            batch.append(
                (
                    context,
                    tuple(pre[index] for index in state_order),
                    tuple(post[index] for index in state_order),
                    tuple(action[index] for index in action_order),
                )
            )
        result.append(batch)
    return result


def _value(
    expression: Any,
    pre: tuple[int, ...],
    action: tuple[int, ...],
    target: int,
    field: int | None,
    constant: int | None,
    context: int,
    supports: Mapping[int, tuple[tuple[int, ...], ...]],
) -> tuple[int, ...]:
    if expression == ["R00"]:
        return (pre[target],)
    if expression == ["R01"] and field is not None:
        return (action[field],)
    if expression == ["R02"] and constant is not None:
        return (constant,)
    if expression == ["R05"] and field is not None:
        try:
            return (supports[context][field].index(action[field]) + 1,)
        except (KeyError, IndexError, ValueError):
            return ()
    if type(expression) is list and len(expression) == 3 and expression[0] == "R03":
        left = _value(expression[1], pre, action, target, field, constant, context, supports)
        right = _value(expression[2], pre, action, target, field, constant, context, supports)
        if len(left) == len(right) == 1:
            return (left[0] + right[0],)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R04":
        left = _value(expression[1], pre, action, target, field, constant, context, supports)
        right = _value(expression[2], pre, action, target, field, constant, context, supports)
        if len(left) == len(right) == 1:
            return tuple(sorted({left[0], right[0]}))
    return ()


def _templates(
    rows: list[tuple[int, tuple[int, ...], tuple[int, ...], tuple[int, ...]]],
    target: int,
) -> list[tuple[Any, int | None, int | None]]:
    legacy_rows = [(pre, post, action) for _context, pre, post, action in rows]
    result = list(v42._templates(legacy_rows, target))  # noqa: SLF001
    field_count = len(rows[0][3])
    for field in range(field_count):
        result.extend(
            (
                (["R05"], field, None),
                (["R03", ["R00"], ["R05"]], field, None),
                (["R04", ["R00"], ["R03", ["R00"], ["R05"]]], field, None),
            )
        )
    unique = {}
    for expression, field, constant in result:
        unique.setdefault(
            (canonical_json_bytes(expression), field, constant),
            (expression, field, constant),
        )
    return list(unique.values())


def version_space_v54(
    evidence: Mapping[str, Any],
    groups: list[list[dict[str, Any]]],
    target: int,
) -> tuple[list[dict[str, Any]], int]:
    batches = _aligned_batches(evidence, groups)
    rows = [row for batch in batches for row in batch]
    if not rows or type(target) is not int:
        _fail("V54 version-space input changed")
    supports = _supports(evidence)
    frontier = []
    evaluations = 0
    for expression, field, constant in _templates(rows, target):
        exact = True
        for batch in batches:
            predicted = set()
            observed = set()
            for context, pre, post, action in batch:
                predicted.update(
                    _value(
                        expression,
                        pre,
                        action,
                        target,
                        field,
                        constant,
                        context,
                        supports,
                    )
                )
                observed.add(post[target])
            evaluations += 1
            if tuple(sorted(predicted)) != tuple(sorted(observed)):
                exact = False
                break
        if exact:
            frontier.append(
                {
                    "normalized_expression": expression,
                    "action_field_binding": field,
                    "anonymous_integer_constant_binding": constant,
                    "contextual_action_support_operator_used": "R05" in str(expression),
                }
            )
    frontier.sort(key=canonical_json_bytes)
    return frontier, evaluations


def predict_version_space_group_v54(
    evidence: Mapping[str, Any],
    group: list[dict[str, Any]],
    version_spaces: list[dict[str, Any]],
) -> dict[str, Any]:
    batches = _aligned_batches(evidence, [group])
    supports = _supports(evidence)
    rows = []
    all_exact = True
    for space in version_spaces:
        target = space.get("target_column") if type(space) is dict else None
        frontier = space.get("batch_exact_candidate_frontier") if type(space) is dict else None
        if type(target) is not int or type(frontier) is not list or not frontier:
            _fail("V54 frozen residual version space changed")
        candidate_rows = []
        for candidate in frontier:
            predicted = set()
            observed = set()
            for context, pre, post, action in batches[0]:
                predicted.update(
                    _value(
                        candidate.get("normalized_expression"),
                        pre,
                        action,
                        target,
                        candidate.get("action_field_binding"),
                        candidate.get("anonymous_integer_constant_binding"),
                        context,
                        supports,
                    )
                )
                observed.add(post[target])
            exact = tuple(sorted(predicted)) == tuple(sorted(observed))
            all_exact = all_exact and exact
            candidate_rows.append(
                {
                    "candidate_sha256": hashlib.sha256(
                        canonical_json_bytes(candidate)
                    ).hexdigest(),
                    "predicted_support": sorted(predicted),
                    "observed_support": sorted(observed),
                    "exact": exact,
                }
            )
        rows.append(
            {
                "target_column": target,
                "every_retained_candidate_exact": all(
                    row["exact"] for row in candidate_rows
                ),
                "candidate_predictions": candidate_rows,
            }
        )
    return {
        "query_exact": all_exact,
        "per_residual_coordinate": rows,
        "every_retained_residual_candidate_exact": all_exact,
    }


__all__ = (
    "RESIDUAL_EXPRESSION_OPCODES_V54",
    "attach_contextual_action_supports_v54",
    "predict_version_space_group_v54",
    "version_space_v54",
)
