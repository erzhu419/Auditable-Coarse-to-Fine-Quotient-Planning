"""Discover reusable residual subprograms from certificate-local raw overlays.

Inputs contain only anonymous layouts, the residual target complement, and raw
state/action/successor rows.  A finite integer/support grammar is enumerated
per target and per occurrence.  Structurally identical expressions are then
joined across independently permuted occurrences and selected by an exact
deterministic cover rule.  No family, state-role, or action-role names enter
the compiler.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


RESIDUAL_FACTOR_TYPES_V18 = ("INT", "FINITE_INT_SUPPORT")
RESIDUAL_FACTOR_OPCODES_V18 = (
    ("R00", "SELF", (), "INT"),
    ("R01", "ACTION_FIELD", (), "INT"),
    ("R02", "ANONYMOUS_INTEGER_CONSTANT", (), "INT"),
    ("R03", "INT_ADD", ("INT", "INT"), "INT"),
    ("R04", "FINITE_SUPPORT_PAIR", ("INT", "INT"), "FINITE_INT_SUPPORT"),
)


class GenericOverlayResidualFactorCompilerV18Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericOverlayResidualFactorCompilerV18Error(message)


def _aligned_rows(document: Mapping[str, Any]) -> list[tuple[list[int], list[int], list[int]]]:
    layout = document.get("layout")
    rows = document.get("raw_transition_rows")
    if type(layout) is not dict or type(rows) is not list or not rows:
        _fail("V18 residual occurrence evidence changed")
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    if type(state_order) is not list or type(action_order) is not list:
        _fail("V18 residual layout projection changed")
    result = []
    for row in rows:
        if type(row) is not dict or type(row.get("selected_action")) is not dict:
            _fail("V18 residual raw row changed")
        pre = row.get("pre_vector")
        post = row.get("post_vector")
        action = row["selected_action"].get("anonymous_fields")
        if (
            type(pre) is not list
            or type(post) is not list
            or type(action) is not list
            or sorted(state_order) != list(range(len(pre)))
            or len(pre) != len(post)
            or sorted(action_order) != list(range(len(action)))
        ):
            _fail("V18 residual row width or permutation changed")
        result.append(
            (
                [pre[index] for index in state_order],
                [post[index] for index in state_order],
                [action[index] for index in action_order],
            )
        )
    return result


def _value(
    expression: Any,
    *,
    pre: list[int],
    action: list[int],
    target: int,
    action_field: int | None,
    constant: int | None,
) -> tuple[int, ...]:
    if expression == ["R00"]:
        return (pre[target],)
    if expression == ["R01"] and action_field is not None:
        return (action[action_field],)
    if expression == ["R02"] and constant is not None:
        return (constant,)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R03":
        left = _value(
            expression[1],
            pre=pre,
            action=action,
            target=target,
            action_field=action_field,
            constant=constant,
        )
        right = _value(
            expression[2],
            pre=pre,
            action=action,
            target=target,
            action_field=action_field,
            constant=constant,
        )
        if len(left) == len(right) == 1:
            return (left[0] + right[0],)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R04":
        left = _value(
            expression[1],
            pre=pre,
            action=action,
            target=target,
            action_field=action_field,
            constant=constant,
        )
        right = _value(
            expression[2],
            pre=pre,
            action=action,
            target=target,
            action_field=action_field,
            constant=constant,
        )
        if len(left) == len(right) == 1:
            return tuple(sorted({left[0], right[0]}))
    _fail("V18 residual expression escaped the registered grammar")


def _candidate_bindings(
    rows: list[tuple[list[int], list[int], list[int]]], target: int
) -> list[dict[str, Any]]:
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
    templates: list[tuple[Any, int | None, int | None]] = [
        (["R00"], None, None),
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
                    (["R03", ["R03", ["R00"], ["R01"]], ["R02"]], field, constant),
                    (["R04", ["R00"], ["R03", ["R03", ["R00"], ["R01"]], ["R02"]]], field, constant),
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
    result = []
    seen = set()
    for expression, field, constant in templates:
        key = (canonical_json_bytes(expression), field, constant)
        if key in seen:
            continue
        seen.add(key)
        if all(
            post[target]
            in _value(
                expression,
                pre=pre,
                action=action,
                target=target,
                action_field=field,
                constant=constant,
            )
            for pre, post, action in rows
        ):
            result.append(
                {
                    "target_column": target,
                    "normalized_expression": expression,
                    "action_field_binding": field,
                    "anonymous_integer_constant_binding": constant,
                }
            )
    return result


def _used_opcodes(expression: Any) -> set[str]:
    if type(expression) is not list:
        return set()
    result = {expression[0]} if expression and type(expression[0]) is str else set()
    for item in expression[1:]:
        result.update(_used_opcodes(item))
    return result


def compile_overlay_residual_factor_library_v18(
    occurrences: Mapping[str, Mapping[str, Any]],
    *,
    minimum_occurrence_support: int = 2,
) -> dict[str, Any]:
    if (
        type(occurrences) is not dict
        or len(occurrences) < 2
        or type(minimum_occurrence_support) is not int
        or minimum_occurrence_support < 2
        or minimum_occurrence_support > len(occurrences)
    ):
        _fail("V18 residual compilation requires multiple occurrences")
    rows_by_occurrence = {
        name: _aligned_rows(document) for name, document in occurrences.items()
    }
    target_inventory: dict[str, set[int]] = {}
    by_expression: dict[bytes, dict[str, list[dict[str, Any]]]] = {}
    expression_values: dict[bytes, Any] = {}
    evaluation_count = 0
    for name, document in occurrences.items():
        unknown = document.get("unknown_residual_target_columns")
        if type(unknown) is not list or not unknown or unknown != sorted(set(unknown)):
            _fail("V18 residual target inventory changed")
        target_inventory[name] = set(unknown)
        for target in unknown:
            bindings = _candidate_bindings(rows_by_occurrence[name], target)
            evaluation_count += len(bindings) * len(rows_by_occurrence[name])
            for binding in bindings:
                encoded = canonical_json_bytes(binding["normalized_expression"])
                expression_values[encoded] = binding["normalized_expression"]
                by_expression.setdefault(encoded, {}).setdefault(name, []).append(binding)
    reusable = [
        encoded
        for encoded, rows in by_expression.items()
        if len(rows) >= minimum_occurrence_support
    ]
    reusable.sort(key=lambda encoded: (len(encoded), encoded))
    universe = {
        (name, target)
        for name, targets in target_inventory.items()
        for target in targets
    }

    def coverage(encoded: bytes) -> set[tuple[str, int]]:
        return {
            (name, binding["target_column"])
            for name, bindings in by_expression[encoded].items()
            for binding in bindings
        }

    selected_list = []
    uncovered = set(universe)
    while True:
        ranked = []
        for encoded in reusable:
            if encoded in selected_list:
                continue
            new_points = coverage(encoded) & uncovered
            if not new_points:
                continue
            excess = 0
            for name, target in new_points:
                options = []
                for binding in by_expression[encoded][name]:
                    if binding["target_column"] != target:
                        continue
                    options.append(
                        sum(
                            len(
                                _value(
                                    expression_values[encoded],
                                    pre=pre,
                                    action=action,
                                    target=target,
                                    action_field=binding["action_field_binding"],
                                    constant=binding["anonymous_integer_constant_binding"],
                                )
                            )
                            - 1
                            for pre, _post, action in rows_by_occurrence[name]
                        )
                    )
                excess += min(options)
            ranked.append(
                (excess, -len(new_points), len(encoded), encoded)
            )
        if not ranked:
            break
        encoded = min(ranked)[3]
        selected_list.append(encoded)
        uncovered -= coverage(encoded)
    selected = tuple(selected_list)
    selected_bindings: dict[tuple[str, int], tuple[bytes, dict[str, Any]]] = {}
    for point in sorted(universe - uncovered):
        name, target = point
        options = []
        for encoded in selected:
            for binding in by_expression[encoded].get(name, []):
                if binding["target_column"] != target:
                    continue
                excess = sum(
                    len(
                        _value(
                            expression_values[encoded],
                            pre=pre,
                            action=action,
                            target=target,
                            action_field=binding["action_field_binding"],
                            constant=binding["anonymous_integer_constant_binding"],
                        )
                    )
                    - 1
                    for pre, _post, action in rows_by_occurrence[name]
                )
                options.append(
                    (excess, len(encoded), encoded, canonical_json_bytes(binding), binding)
                )
        best = min(options)
        selected_bindings[point] = (best[2], best[4])
    subprograms = []
    covered = set()
    for encoded in selected:
        expression = expression_values[encoded]
        selected_target_bindings = []
        for key in sorted(selected_bindings):
            chosen_encoded, binding = selected_bindings[key]
            if chosen_encoded == encoded:
                selected_target_bindings.append({"occurrence": key[0], **binding})
                covered.add(key)
        source_bindings = []
        for name in sorted(by_expression[encoded]):
            ranked = []
            for binding in by_expression[encoded][name]:
                excess = sum(
                    len(
                        _value(
                            expression,
                            pre=pre,
                            action=action,
                            target=binding["target_column"],
                            action_field=binding["action_field_binding"],
                            constant=binding["anonymous_integer_constant_binding"],
                        )
                    )
                    - 1
                    for pre, _post, action in rows_by_occurrence[name]
                )
                ranked.append((excess, canonical_json_bytes(binding), binding))
            source_bindings.append({"occurrence": name, **min(ranked)[2]})
        if selected_target_bindings:
            subprograms.append(
                {
                    "normalized_expression": expression,
                    "expression_sha256": hashlib.sha256(encoded).hexdigest(),
                    "used_opcodes": sorted(_used_opcodes(expression)),
                    "source_occurrence_support_count": len(source_bindings),
                    "occurrence_bindings": source_bindings,
                    "selected_residual_target_bindings": selected_target_bindings,
                }
            )
    if covered != universe - uncovered:
        _fail("V18 residual-factor selection changed its partial coverage")
    payload = {
        "schema": "acfqp.generic_overlay_residual_factor_library.v18",
        "generic_types": list(RESIDUAL_FACTOR_TYPES_V18),
        "generic_opcode_registry": [
            [code, name, list(arguments), result]
            for code, name, arguments, result in RESIDUAL_FACTOR_OPCODES_V18
        ],
        "occurrence_count": len(occurrences),
        "residual_target_count": len(universe),
        "minimum_occurrence_support": minimum_occurrence_support,
        "compiled_subprograms": subprograms,
        "covered_residual_targets": [
            {"occurrence": name, "target_column": target}
            for name, target in sorted(covered)
        ],
        "uncovered_residual_targets": [
            {"occurrence": name, "target_column": target}
            for name, target in sorted(uncovered)
        ],
        "candidate_binding_evaluation_count": evaluation_count,
        "selection_rule": "GREEDY_MIN_PREDICTIVE_SUPPORT_EXCESS_THEN_MAX_NEW_CROSS_OCCURRENCE_COVERAGE_THEN_CANONICAL_BYTES",
        "all_observed_residual_targets_covered": not uncovered,
        "family_names_available_to_compiler": False,
        "semantic_state_or_action_names_available_to_compiler": False,
        "ground_fact_transfer_across_occurrences_claimed": False,
        "future_transition_prediction_authority_present": False,
        "complete_world_model_claimed": False,
    }
    return {
        **payload,
        "residual_factor_library_id": hashlib.sha256(
            b"acfqp:generic-overlay-residual-factor-library:v18\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def replay_overlay_residual_factor_library_v18(
    library: Mapping[str, Any], occurrences: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    expected = compile_overlay_residual_factor_library_v18(
        occurrences,
        minimum_occurrence_support=library.get("minimum_occurrence_support"),
    )
    if library != expected:
        _fail("V18 residual-factor library differs from exact reconstruction")
    rows_by_occurrence = {
        name: _aligned_rows(document) for name, document in occurrences.items()
    }
    checked = 0
    for subprogram in library["compiled_subprograms"]:
        expression = subprogram["normalized_expression"]
        for binding in subprogram["occurrence_bindings"]:
            for pre, post, action in rows_by_occurrence[binding["occurrence"]]:
                if post[binding["target_column"]] not in _value(
                    expression,
                    pre=pre,
                    action=action,
                    target=binding["target_column"],
                    action_field=binding["action_field_binding"],
                    constant=binding["anonymous_integer_constant_binding"],
                ):
                    _fail("V18 residual-factor replay changed")
                checked += 1
    return {
        "residual_factor_library_id": library["residual_factor_library_id"],
        "raw_transition_assignment_checks": checked,
        "exact_on_frozen_overlay_rows": True,
        "future_transition_prediction_authority_present": False,
    }


__all__ = (
    "compile_overlay_residual_factor_library_v18",
    "replay_overlay_residual_factor_library_v18",
)
