"""Independent bytes-oriented replay of the V60 coordinate alignment."""

from __future__ import annotations

import hashlib
from itertools import permutations, product
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


_ALIGNMENT_DOMAIN = b"acfqp:generic-coordinate-alignment:v60\x00"


class GenericCoordinateAlignmentIndependentReplayV61Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericCoordinateAlignmentIndependentReplayV61Error(message)


def _predicate(opcode: str, left: int, right: int) -> bool:
    operations = {
        "EQ": left == right,
        "NE": left != right,
        "LT": left < right,
        "LE": left <= right,
        "GT": left > right,
        "GE": left >= right,
    }
    if opcode not in operations:
        _fail("V61 relation opcode changed")
    return operations[opcode]


def _canonical_inputs(
    candidate: Mapping[str, Any],
    raw_rows: list[dict[str, Any]],
    raw_catalogue: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    layout = candidate.get("layout")
    state_order = layout.get("state_canonical_to_raw") if type(layout) is dict else None
    action_order = layout.get("action_canonical_to_raw") if type(layout) is dict else None
    if (
        type(state_order) is not list
        or type(action_order) is not list
        or sorted(state_order) != list(range(len(state_order)))
        or sorted(action_order) != list(range(len(action_order)))
        or type(raw_rows) is not list
        or not raw_rows
        or type(raw_catalogue) is not list
        or not raw_catalogue
    ):
        _fail("V61 raw alignment inventory changed")
    catalogue = []
    action_by_key = {}
    for raw in raw_catalogue:
        key = raw.get("action_key") if type(raw) is dict else None
        fields = raw.get("anonymous_fields") if type(raw) is dict else None
        if (
            type(key) is not int
            or type(fields) is not list
            or len(fields) != len(action_order)
            or any(type(value) is not int for value in fields)
        ):
            _fail("V61 raw action catalogue changed")
        row = {
            "key": key,
            "fields": [fields[index] for index in action_order],
        }
        catalogue.append(row)
        action_by_key[key] = row
    if len(action_by_key) != len(catalogue):
        _fail("V61 duplicate action key")
    rows = []
    for raw in raw_rows:
        action = raw.get("selected_action") if type(raw) is dict else None
        fields = action.get("anonymous_fields") if type(action) is dict else None
        pre = raw.get("pre_vector") if type(raw) is dict else None
        post = raw.get("post_vector") if type(raw) is dict else None
        before = raw.get("legal_action_keys_before") if type(raw) is dict else None
        after = raw.get("legal_action_keys_after") if type(raw) is dict else None
        terminal = raw.get("terminal_acceptance_after") if type(raw) is dict else None
        if (
            type(pre) is not list
            or type(post) is not list
            or len(pre) != len(state_order)
            or len(post) != len(pre)
            or type(fields) is not list
            or len(fields) != len(action_order)
            or type(before) is not list
            or type(after) is not list
            or (after and terminal is not None)
            or (not after and type(terminal) is not bool)
        ):
            _fail("V61 raw transition row changed")
        rows.append(
            {
                "pre": [pre[index] for index in state_order],
                "post": [post[index] for index in state_order],
                "action": [fields[index] for index in action_order],
                "legal_before": before,
                "legal_after": after,
                "terminal": terminal,
            }
        )
    return rows, catalogue


def _examples(
    rows: list[dict[str, Any]], catalogue: list[dict[str, Any]]
) -> list[tuple[list[int], list[int], bool]]:
    states: dict[tuple[int, ...], tuple[int, ...]] = {}
    for row in rows:
        for state, legal in (
            (row["pre"], row["legal_before"]),
            (row["post"], row["legal_after"]),
        ):
            key = tuple(state)
            previous = states.setdefault(key, tuple(legal))
            if previous != tuple(legal):
                _fail("V61 state legality changed")
    result = []
    for state in sorted(states):
        legal = set(states[state])
        for action in sorted(catalogue, key=lambda row: row["key"]):
            result.append((list(state), action["fields"], action["key"] in legal))
    return result


def _state_mappings(
    model: Mapping[str, Any], candidate: Mapping[str, Any]
) -> list[tuple[int, ...]]:
    width = model["state_width"]
    source = {row["target_column"]: row for row in model["known_partial_factor_assignments"]}
    target = {row["target_column"]: row for row in candidate["compiled_factor_assignments"]}

    def descriptor(rows: Mapping[int, Mapping[str, Any]], column: int):
        row = rows.get(column)
        return (
            ("UNKNOWN",)
            if row is None
            else ("KNOWN", row["result_type"], row["signature_sha256"])
        )

    source_groups = {}
    target_groups = {}
    for column in range(width):
        source_groups.setdefault(descriptor(source, column), []).append(column)
        target_groups.setdefault(descriptor(target, column), []).append(column)
    if set(source_groups) != set(target_groups) or any(
        len(source_groups[key]) != len(target_groups[key]) for key in source_groups
    ):
        return []
    groups = sorted(source_groups, key=lambda row: canonical_json_bytes(list(row)))
    result = []
    for choices in product(*(permutations(target_groups[key]) for key in groups)):
        mapping = [-1] * width
        for key, targets in zip(groups, choices, strict=True):
            for source_column, target_column in zip(source_groups[key], targets, strict=True):
                mapping[source_column] = target_column
        result.append(tuple(mapping))
    return result


def _action_mappings(
    model: Mapping[str, Any],
    candidate: Mapping[str, Any],
    state_mapping: tuple[int, ...],
    source_applicability: tuple[int, int],
    target_applicability: tuple[int, int],
) -> list[tuple[int, ...]]:
    width = model["action_field_width"]
    source = {row["target_column"]: row for row in model["known_partial_factor_assignments"]}
    target = {row["target_column"]: row for row in candidate["compiled_factor_assignments"]}
    bindings = {source_applicability[1]: target_applicability[1]}
    for source_column, source_row in source.items():
        target_row = target[state_mapping[source_column]]
        left = source_row["action_dependencies"]
        right = target_row["action_dependencies"]
        if len(left) != len(right):
            return []
        for source_field, target_field in zip(left, right, strict=True):
            if source_field in bindings and bindings[source_field] != target_field:
                return []
            bindings[source_field] = target_field
    if len(bindings) != len(set(bindings.values())):
        return []
    source_remaining = [row for row in range(width) if row not in bindings]
    target_remaining = [row for row in range(width) if row not in bindings.values()]
    result = []
    for choice in permutations(target_remaining):
        mapping = [-1] * width
        for source_field, target_field in bindings.items():
            mapping[source_field] = target_field
        for source_field, target_field in zip(source_remaining, choice, strict=True):
            mapping[source_field] = target_field
        result.append(tuple(mapping))
    return result


def _partial_support(
    assignment: Mapping[str, Any], state: list[int], action: list[int]
) -> tuple[int, ...]:
    expression = assignment["expression"]
    if expression[0] == "E00":
        return (state[expression[1]],)
    if expression[0] == "E07":
        column = expression[1][1]
        field = expression[2][2][1]
        return tuple(sorted({state[column], state[column] + action[field]}))
    _fail("V61 partial expression changed")


def _residual_value(
    expression: Any,
    state: list[int],
    action: list[int],
    target: int,
    field: int | None,
    constant: int | None,
    supports: list[tuple[int, ...]],
) -> tuple[int, ...]:
    if expression == ["R00"]:
        return (state[target],)
    if expression == ["R01"] and field is not None:
        return (action[field],)
    if expression == ["R02"] and constant is not None:
        return (constant,)
    if expression == ["R05"] and field is not None:
        try:
            return (supports[field].index(action[field]) + 1,)
        except ValueError:
            return ()
    if type(expression) is list and len(expression) == 3:
        left = _residual_value(expression[1], state, action, target, field, constant, supports)
        right = _residual_value(expression[2], state, action, target, field, constant, supports)
        if len(left) == len(right) == 1:
            if expression[0] == "R03":
                return (left[0] + right[0],)
            if expression[0] == "R04":
                return tuple(sorted({left[0], right[0]}))
    return ()


def _terminal(tree: Mapping[str, Any], state: list[int]) -> tuple[str, int]:
    cursor = tree
    while cursor.get("kind") == "RELATION":
        outcome = _predicate(
            cursor["opcode"],
            state[cursor["left_column"]],
            state[cursor["right_column"]],
        )
        cursor = cursor["when_true" if outcome else "when_false"]
    if cursor.get("kind") != "LEAF":
        _fail("V61 terminal tree changed")
    return cursor["terminal_class"], cursor["status_token"]


def _replays(
    model: Mapping[str, Any],
    rows: list[dict[str, Any]],
    catalogue: list[dict[str, Any]],
    state_mapping: tuple[int, ...],
    action_mapping: tuple[int, ...],
) -> bool:
    supports = [
        tuple(sorted({row["fields"][action_mapping[field]] for row in catalogue}))
        for field in range(model["action_field_width"])
    ]
    for target_row in rows:
        pre = [target_row["pre"][target] for target in state_mapping]
        post = [target_row["post"][target] for target in state_mapping]
        action = [target_row["action"][target] for target in action_mapping]
        if any(
            post[row["target_column"]] not in _partial_support(row, pre, action)
            for row in model["known_partial_factor_assignments"]
        ):
            return False
        for space in model["residual_version_spaces"]:
            target = space["target_column"]
            for expression in space["batch_exact_candidate_frontier"]:
                if post[target] not in _residual_value(
                    expression["normalized_expression"],
                    pre,
                    action,
                    target,
                    expression.get("action_field_binding"),
                    expression.get("anonymous_integer_constant_binding"),
                    supports,
                ):
                    return False
        expected = (
            "ACTIVE"
            if target_row["legal_after"]
            else "ACCEPT"
            if target_row["terminal"] is True
            else "REJECT"
        )
        for terminal in model["mdl_minimal_terminal_candidate_frontier"]:
            classification, token = _terminal(terminal["decision_tree"], post)
            if classification != expected or token != post[model["status_target_column"]]:
                return False
    return True


def rederive_coordinate_alignment_v61(
    model: Mapping[str, Any],
    applicability_program: Mapping[str, Any],
    target_candidate: Mapping[str, Any],
    raw_transition_rows: list[dict[str, Any]],
    raw_action_catalogue: list[dict[str, Any]],
) -> dict[str, Any]:
    if (
        type(model) is not dict
        or type(applicability_program) is not dict
        or type(target_candidate) is not dict
        or target_candidate.get("state_width") != model.get("state_width")
        or target_candidate.get("action_field_width") != model.get("action_field_width")
        or target_candidate.get("layout", {}).get("schema_signature")
        != model.get("source_layout", {}).get("schema_signature")
    ):
        _fail("V61 structural schema family changed")
    rows, catalogue = _canonical_inputs(
        target_candidate, raw_transition_rows, raw_action_catalogue
    )
    examples = _examples(rows, catalogue)
    relation = applicability_program["selected_program"]
    target_bindings = []
    relation_evaluations = 0
    for state_column in range(model["state_width"]):
        for action_field in range(model["action_field_width"]):
            relation_evaluations += len(examples)
            if all(
                _predicate(relation["opcode"], state[state_column], action[action_field])
                == expected
                for state, action, expected in examples
            ):
                target_bindings.append((state_column, action_field))
    source_applicability = (relation["state_column"], relation["action_field"])
    state_candidates = _state_mappings(model, target_candidate)
    action_candidate_count = 0
    replay_evaluations = 0
    retained = []
    for state_mapping in state_candidates:
        for target_applicability in target_bindings:
            if state_mapping[source_applicability[0]] != target_applicability[0]:
                continue
            action_candidates = _action_mappings(
                model,
                target_candidate,
                state_mapping,
                source_applicability,
                target_applicability,
            )
            action_candidate_count += len(action_candidates)
            for action_mapping in action_candidates:
                replay_evaluations += len(rows)
                if _replays(model, rows, catalogue, state_mapping, action_mapping):
                    retained.append(
                        {
                            "source_state_to_target_canonical": list(state_mapping),
                            "source_action_to_target_canonical": list(action_mapping),
                            "target_applicability_state_column": target_applicability[0],
                            "target_applicability_action_field": target_applicability[1],
                        }
                    )
    retained = list({canonical_json_bytes(row): row for row in retained}.values())
    retained.sort(key=canonical_json_bytes)
    if len(retained) != 1:
        _fail(f"V61 retained alignment count changed: {len(retained)}")
    payload = {
        "schema": "acfqp.generic_coordinate_alignment.v60",
        "source_model_id": model["projected_disagreement_successor_model_id"],
        "source_applicability_program_id": applicability_program[
            "action_applicability_program_id"
        ],
        "target_partial_candidate_id": target_candidate["candidate_id"],
        "target_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes(raw_transition_rows)
        ).hexdigest(),
        "target_raw_transition_count": len(raw_transition_rows),
        "state_width": model["state_width"],
        "action_field_width": model["action_field_width"],
        "source_applicability_relation_opcode": relation["opcode"],
        "target_exact_applicability_binding_count": len(target_bindings),
        "target_applicability_relation_evaluations": relation_evaluations,
        "type_compatible_state_mapping_candidate_count": len(state_candidates),
        "type_compatible_action_mapping_candidate_count": action_candidate_count,
        "full_model_replay_row_evaluations": replay_evaluations,
        "exact_full_model_projection_count": 1,
        **retained[0],
        "alignment_derived_only_from_target_common_partial_observations": True,
        "target_episode_outcomes_used": False,
        "source_model_or_applicability_refit": False,
        "semantic_names_used": False,
        "alignment_used_as_safety_authority": False,
        "complete_world_model_claimed": False,
    }
    return {
        **payload,
        "coordinate_alignment_id": hashlib.sha256(
            _ALIGNMENT_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("rederive_coordinate_alignment_v61",)
