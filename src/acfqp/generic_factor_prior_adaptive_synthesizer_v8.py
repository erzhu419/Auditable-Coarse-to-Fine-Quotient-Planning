"""Generic finite-grammar adaptive synthesis with one optional factor prior.

Both arms use the same candidates, exact likelihood, query order, posterior
threshold, and two-observation confirmation rule.  ``factor_prior_enabled``
changes only the initial weight assigned to signatures already present in an
anonymous cross-schema factor library.  The module does not inspect semantic
column or action names.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any, Iterable, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


class GenericFactorPriorAdaptiveSynthesizerV8Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericFactorPriorAdaptiveSynthesizerV8Error(message)


def _depth(expression: Any) -> int:
    if type(expression) is not list or not expression:
        return 0
    children = [_depth(value) for value in expression[1:]]
    return 0 if not children else 1 + max(children)


def _node_count(expression: Any) -> int:
    if type(expression) is not list or not expression:
        return 1
    if expression[0] in {"E00", "E01"}:
        return 1
    return 1 + sum(_node_count(value) for value in expression[1:])


def _action_dependencies(expression: Any) -> tuple[int, ...]:
    result: set[int] = set()

    def visit(value: Any) -> None:
        if type(value) is not list or not value:
            return
        if value[0] == "E01":
            result.add(value[1])
        for child in value[1:]:
            visit(child)

    visit(expression)
    return tuple(sorted(result))


def _contains_noncanonical_constant_action(
    expression: Any, constant_fields: Mapping[int, int]
) -> bool:
    if type(expression) is not list or not expression:
        return False
    if expression[0] in {"E05", "E13"}:
        for child in expression[1:]:
            if (
                type(child) is list
                and child[:1] == ["E01"]
                and child[1] in constant_fields
                and constant_fields[child[1]] in {-1, 0, 1}
            ):
                return True
    return any(
        _contains_noncanonical_constant_action(child, constant_fields)
        for child in expression[1:]
    )


def _normalize(expression: Any, target_column: int) -> Any:
    state_map: dict[int, int] = {}
    action_map: dict[int, int] = {}

    def state_symbol(value: int) -> list[Any]:
        if value == target_column:
            return ["S", "SELF"]
        if value not in state_map:
            state_map[value] = len(state_map)
        return ["S", state_map[value]]

    def action_symbol(value: int) -> list[Any]:
        if value not in action_map:
            action_map[value] = len(action_map)
        return ["A", action_map[value]]

    def visit(value: Any) -> Any:
        if type(value) is not list or not value:
            return value
        if value[0] == "E00":
            return state_symbol(value[1])
        if value[0] == "E01":
            return action_symbol(value[1])
        return [value[0], *(visit(item) for item in value[1:])]

    return visit(expression)


def _signature(expression: Any, result_type: str, target_column: int) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            {
                "result_type": result_type,
                "normalized_expression": _normalize(expression, target_column),
            }
        )
    ).hexdigest()


def enumerate_anonymous_factor_candidates_v8(
    state_width: int,
    action_field_width: int,
    *,
    literal_atoms: tuple[int, ...] = (-1, 1),
) -> tuple[dict[str, Any], ...]:
    """Enumerate the registered finite grammar without semantic hints."""

    if state_width <= 0 or action_field_width <= 0:
        _fail("candidate grammar requires positive anonymous widths")
    expressions: list[tuple[str, Any]] = []
    for state_column in range(state_width):
        state = ["E00", state_column]
        expressions.append(("INT", state))
        for literal in literal_atoms:
            expressions.append(("INT", ["E05", literal, state]))
        for action_field in range(action_field_width):
            action = ["E01", action_field]
            addition = ["E05", state, action]
            expressions.append(("INT", addition))
            expressions.append(
                ("FINITE_INT_SUPPORT", ["E07", state, addition])
            )
    for action_field in range(action_field_width):
        expressions.append(("INT", ["E01", action_field]))
    unique: dict[bytes, tuple[str, Any]] = {}
    for result_type, expression in expressions:
        key = canonical_json_bytes([result_type, expression])
        unique[key] = (result_type, expression)
    return tuple(
        {
            "candidate_id": hashlib.sha256(key).hexdigest(),
            "result_type": result_type,
            "expression": expression,
        }
        for key, (result_type, expression) in sorted(unique.items())
    )


def _scalar(expression: Any, state: tuple[int, ...], action: tuple[int, ...]) -> Any:
    if type(expression) is int:
        return expression
    if type(expression) is not list or not expression:
        _fail("candidate expression shape changed")
    head = expression[0]
    if head == "E00":
        return state[expression[1]]
    if head == "E01":
        return action[expression[1]]
    left = _scalar(expression[1], state, action)
    right = _scalar(expression[2], state, action)
    if head == "E05":
        return int(left) + int(right)
    if head == "E07":
        return frozenset((int(left), int(right)))
    if head == "E13":
        return int(left) | int(right)
    _fail("candidate used an opcode outside the registered finite grammar")


def _group_supports(
    rows: Iterable[FlatRawTransitionV4],
) -> tuple[tuple[tuple[int, ...], tuple[int, ...], tuple[frozenset[int], ...]], ...]:
    grouped: dict[tuple[tuple[int, ...], tuple[int, ...]], list[tuple[int, ...]]] = (
        defaultdict(list)
    )
    for row in rows:
        grouped[(row.pre, row.action.fields)].append(row.post)
    result = []
    for (state, action), posts in sorted(grouped.items()):
        width = len(state)
        if any(len(post) != width for post in posts):
            _fail("successor width changed inside adaptive evidence")
        result.append(
            (
                state,
                action,
                tuple(frozenset(post[column] for post in posts) for column in range(width)),
            )
        )
    return tuple(result)


def infer_factor_slots_v8(
    rows: Iterable[FlatRawTransitionV4],
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    factor_slots: Mapping[int, str],
    prior_signature_sha256: frozenset[str],
    factor_prior_enabled: bool,
    prior_weight: int,
    posterior_numerator: int,
    posterior_denominator: int,
) -> dict[str, Any]:
    """Apply one exact-likelihood posterior update to all factor slots."""

    frozen_rows = tuple(rows)
    if not frozen_rows or not catalogue:
        _fail("adaptive synthesis requires nonempty anonymous observations")
    if prior_weight <= 1 or not (0 < posterior_numerator < posterior_denominator):
        _fail("adaptive posterior contract changed")
    state_width = len(frozen_rows[0].pre)
    action_width = len(catalogue[0].fields)
    candidates = enumerate_anonymous_factor_candidates_v8(state_width, action_width)
    action_column_values = {
        field: tuple(action.fields[field] for action in catalogue)
        for field in range(action_width)
    }
    action_representative = {
        field: min(
            candidate
            for candidate, values in action_column_values.items()
            if values == action_column_values[field]
        )
        for field in range(action_width)
    }
    constant_action_fields = {
        field: values[0]
        for field, values in action_column_values.items()
        if len(set(values)) == 1
    }
    supports = _group_supports(frozen_rows)
    selections = []
    all_stopped = True
    for target, expected_type in sorted(factor_slots.items()):
        survivors = []
        for candidate in candidates:
            if candidate["result_type"] != expected_type:
                continue
            dependencies = _action_dependencies(candidate["expression"])
            if any(action_representative[field] != field for field in dependencies):
                continue
            if _contains_noncanonical_constant_action(
                candidate["expression"], constant_action_fields
            ):
                continue
            matches = True
            for state, action, actual in supports:
                predicted = _scalar(candidate["expression"], state, action)
                if expected_type == "FINITE_INT_SUPPORT":
                    matches = predicted == actual[target]
                else:
                    matches = actual[target] == frozenset((predicted,))
                if not matches:
                    break
            if not matches:
                continue
            signature = _signature(candidate["expression"], expected_type, target)
            factor_multiplier = (
                prior_weight
                if factor_prior_enabled and signature in prior_signature_sha256
                else 1
            )
            node_count = _node_count(candidate["expression"])
            mdl_base_weight = 1
            weight = factor_multiplier
            survivors.append(
                {
                    **candidate,
                    "signature_sha256": signature,
                    "node_count": node_count,
                    "mdl_base_weight": mdl_base_weight,
                    "factor_prior_multiplier": factor_multiplier,
                    "weight": weight,
                }
            )
        if not survivors:
            _fail("anonymous finite grammar has no surviving factor candidate")
        survivors.sort(key=lambda row: (-row["weight"], row["candidate_id"]))
        top_weight = survivors[0]["weight"]
        top = [row for row in survivors if row["weight"] == top_weight]
        total_weight = sum(row["weight"] for row in survivors)
        stopped = (
            len(top) == 1
            and top_weight * posterior_denominator
            >= total_weight * posterior_numerator
        )
        all_stopped = all_stopped and stopped
        selections.append(
            {
                "target_column": target,
                "expected_result_type": expected_type,
                "survivor_count": len(survivors),
                "top_candidate_count": len(top),
                "top_weight": top_weight,
                "total_weight": total_weight,
                "posterior_threshold": {
                    "numerator": posterior_numerator,
                    "denominator": posterior_denominator,
                },
                "stopped": stopped,
                "selected_candidate": top[0] if stopped else None,
            }
        )
    return {
        "schema": "acfqp.generic_factor_prior_adaptive_update.v8",
        "factor_prior_enabled": factor_prior_enabled,
        "candidate_grammar": "FINITE_ANONYMOUS_INTEGER_VECTOR_ACTION_EXPRESSION_GRAMMAR_V8",
        "candidate_count": len(candidates),
        "exact_zero_one_likelihood": True,
        "factor_prior_weight": prior_weight if factor_prior_enabled else 1,
        "shared_base_weight": 1,
        "uniform_nonprior_factor_multiplier": 1,
        "catalogue_identical_action_columns_quotiented": True,
        "catalogue_constant_action_subexpressions_canonicalized": True,
        "observed_support_count": len(supports),
        "selections": selections,
        "all_factor_slots_stopped": all_stopped,
    }


def compile_factor_slot_program_v8(
    scaffold_program: Mapping[str, Any],
    update: Mapping[str, Any],
    *,
    program_domain: str,
) -> dict[str, Any]:
    if update.get("all_factor_slots_stopped") is not True:
        _fail("cannot compile before all factor slots satisfy the stopping rule")
    selected = {
        row["target_column"]: row["selected_candidate"]
        for row in update["selections"]
    }
    assignments = []
    for assignment in scaffold_program["compiled_assignments"]:
        target = assignment["target_column"]
        if target in selected:
            candidate = selected[target]
            assignments.append(
                {
                    "target_column": target,
                    "result_type": candidate["result_type"],
                    "expression": candidate["expression"],
                    "composition_depth": _depth(candidate["expression"]),
                }
            )
        else:
            assignments.append(dict(assignment))
    assignments.sort(key=lambda row: row["target_column"])
    payload = {
        **{
            key: value
            for key, value in scaffold_program.items()
            if key not in {"program_id", "compiled_assignments", "schema"}
        },
        "schema": "acfqp.generic_factor_prior_single_switch_program.v8",
        "compiled_assignments": assignments,
        "shared_residual_scaffold_program_id": scaffold_program["program_id"],
        "factor_prior_enabled_during_acquisition": update["factor_prior_enabled"],
        "all_factor_slots_rederived_from_raw_observations": True,
    }
    return {**payload, "program_id": content_id(program_domain, payload)}


__all__ = (
    "GenericFactorPriorAdaptiveSynthesizerV8Error",
    "compile_factor_slot_program_v8",
    "enumerate_anonymous_factor_candidates_v8",
    "infer_factor_slots_v8",
)
