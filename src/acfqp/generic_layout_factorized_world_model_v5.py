"""Generic layout discovery followed by anonymous atomic world-model synthesis.

Columns and action fields are represented as vertices in a typed relation
graph.  Their colors are refined only from raw state/action/successor facts;
no domain, state-role, or action-role names are available.  A uniquely colored
graph induces a canonical layout.  The aligned observations are then consumed
by the frozen V4 atomic-expression composer.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from itertools import permutations, product
from typing import Any, Iterable, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
    derive_atomic_dependency_support_v4,
    synthesize_generic_atomic_program_v4,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


LAYOUT_RELATION_META_GRAMMAR_V5 = (
    "ALL_NONE_MIXED",
    "PRE_POST_EQUAL",
    "PRE_POST_UNIT_INCREMENT",
    "PRE_POST_ORDER",
    "POST_SELECTED_FIELD_EQUAL",
    "POST_PRE_PLUS_SELECTED_FIELD",
    "POST_PRE_DELTA_SELECTED_FIELD",
    "LEGAL_SET_IFF_PRE_EQUALS_CATALOGUE_FIELD",
    "TERMINAL_CLASS_CONDITIONAL_EQUALITY_AND_ORDER",
    "SAME_PRE_ACTION_SUCCESSOR_BRANCH_CARDINALITY",
)

LAYOUT_REFINEMENT_MAX_ROUNDS_V5 = 32
META_PRIOR_ALIGNMENT_MAX_CANDIDATES_V5 = 10_000


class GenericLayoutFactorizedWorldModelV5Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericLayoutFactorizedWorldModelV5Error(message)


def _tri(values: Iterable[bool]) -> str:
    rows = tuple(values)
    if not rows:
        return "EMPTY"
    if all(rows):
        return "ALL"
    if any(rows):
        return "MIXED"
    return "NONE"


def _universal(values: Iterable[bool]) -> str:
    rows = tuple(values)
    if not rows:
        return "EMPTY"
    return "ALL" if all(rows) else "OTHER"


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(_jsonable(value))).hexdigest()


def _jsonable(value: Any) -> Any:
    if type(value) is tuple:
        return [_jsonable(item) for item in value]
    if type(value) is list:
        return [_jsonable(item) for item in value]
    if type(value) is dict:
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _canonical_key(value: Any) -> bytes:
    return canonical_json_bytes(_jsonable(value))


def _class_rows(
    rows: tuple[FlatRawTransitionV4, ...], name: str
) -> tuple[FlatRawTransitionV4, ...]:
    if name == "ALL":
        return rows
    if name == "ACTIVE":
        return tuple(row for row in rows if row.terminal_acceptance_after is None)
    if name == "SUCCESS":
        return tuple(row for row in rows if row.terminal_acceptance_after is True)
    if name == "FAILURE":
        return tuple(row for row in rows if row.terminal_acceptance_after is False)
    raise AssertionError(name)


def _validate_occurrence(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[int, int, dict[int, FlatRawActionV4]]:
    if not rows or not catalogue:
        _fail("layout discovery requires raw transitions and an action catalogue")
    occurrences = {row.occurrence for row in rows}
    if len(occurrences) != 1:
        _fail("layout discovery accepts one occurrence at a time")
    state_widths = {len(row.pre) for row in rows} | {len(row.post) for row in rows}
    field_widths = {len(action.fields) for action in catalogue}
    if len(state_widths) != 1 or len(field_widths) != 1:
        _fail("layout discovery width changed")
    by_key = {action.key: action for action in catalogue}
    if len(by_key) != len(catalogue):
        _fail("layout discovery action keys changed")
    if any(row.action != by_key.get(row.action.key) for row in rows):
        _fail("layout discovery selected action descriptor changed")
    return next(iter(state_widths)), next(iter(field_widths)), by_key


def _state_unary(
    rows: tuple[FlatRawTransitionV4, ...], column: int
) -> tuple[Any, ...]:
    grouped: dict[tuple[tuple[int, ...], int], set[int]] = {}
    for row in rows:
        grouped.setdefault((row.pre, row.action.key), set()).add(row.post[column])
    active = {row.post[column] for row in rows if row.terminal_acceptance_after is None}
    success = {row.post[column] for row in rows if row.terminal_acceptance_after is True}
    failure = {row.post[column] for row in rows if row.terminal_acceptance_after is False}
    observed_terminal = [values for values in (success, failure) if values]
    terminal_token = (
        len(active) == 1
        and bool(observed_terminal)
        and all(len(values) == 1 for values in observed_terminal)
        and len(active | set().union(*observed_terminal))
        == 1 + len(observed_terminal)
    )
    values = tuple(row.pre[column] for row in rows) + tuple(row.post[column] for row in rows)
    return (
        "STATE",
        _universal(row.pre[column] == row.post[column] for row in rows),
        _universal(row.post[column] == row.pre[column] + 1 for row in rows),
        (
            "TERMINAL_CLASS_BRANCH"
            if terminal_token
            else "BRANCHED"
            if any(len(found) > 1 for found in grouped.values())
            else "SINGLE"
        ),
        "CONSTANT" if len(set(values)) == 1 else "VARIABLE",
        "TERMINAL_TOKEN" if terminal_token else "NONTERMINAL_TOKEN",
    )


def _action_unary(
    catalogue: tuple[FlatRawActionV4, ...], field: int
) -> tuple[Any, ...]:
    values = tuple(action.fields[field] for action in catalogue)
    return (
        "ACTION",
        "CONSTANT" if len(set(values)) == 1 else "VARIABLE",
        "ONE_PER_ACTION" if len(set(values)) == len(values) else "REPEATED",
    )


def _state_action_edge(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    state_column: int,
    action_field: int,
) -> tuple[Any, ...]:
    legality = []
    for row in rows:
        predicted = {
            action.key
            for action in catalogue
            if action.fields[action_field] == row.pre[state_column]
        }
        legality.append(predicted == set(row.legal_before))
    return (
        "SA",
        _universal(legality),
        _universal(row.pre[state_column] == row.action.fields[action_field] for row in rows),
        _universal(row.post[state_column] == row.action.fields[action_field] for row in rows),
        _universal(
            row.post[state_column] - row.pre[state_column]
            == row.action.fields[action_field]
            for row in rows
        ),
        _universal(
            row.post[state_column]
            == row.pre[state_column] + row.action.fields[action_field]
            for row in rows
        ),
    )


def _state_state_edge(
    rows: tuple[FlatRawTransitionV4, ...],
    post_column: int,
    pre_column: int,
) -> tuple[Any, ...]:
    result: list[Any] = ["SS"]
    for name in ("ALL", "ACTIVE", "SUCCESS", "FAILURE"):
        selected = _class_rows(rows, name)
        result.extend(
            (
                _universal(row.post[post_column] == row.pre[pre_column] for row in selected),
                _universal(row.post[post_column] > row.pre[pre_column] for row in selected),
                _universal(row.post[post_column] < row.pre[pre_column] for row in selected),
            )
        )
    return tuple(result)


def _action_action_edge(
    catalogue: tuple[FlatRawActionV4, ...], left: int, right: int
) -> tuple[Any, ...]:
    return (
        "AA",
        _universal(action.fields[left] == action.fields[right] for action in catalogue),
        _universal(action.fields[left] > action.fields[right] for action in catalogue),
        _universal(action.fields[left] < action.fields[right] for action in catalogue),
    )


@dataclass(frozen=True, slots=True)
class DiscoveredLayoutV5:
    state_canonical_to_raw: tuple[int, ...]
    action_canonical_to_raw: tuple[int, ...]
    state_colors: tuple[str, ...]
    action_colors: tuple[str, ...]
    schema_signature: str
    refinement_rounds: int
    relation_evaluations: int
    layout_id: str
    reference_layout_id: str | None = None
    graph_edit_score: int = 0
    cross_occurrence_value_overlap: int = 0

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.generic_layout_factorization.v5",
            "state_canonical_to_raw": list(self.state_canonical_to_raw),
            "action_canonical_to_raw": list(self.action_canonical_to_raw),
            "state_structural_colors": list(self.state_colors),
            "action_structural_colors": list(self.action_colors),
            "schema_signature": self.schema_signature,
            "refinement_rounds": self.refinement_rounds,
            "relation_evaluations": self.relation_evaluations,
            "reference_layout_id": self.reference_layout_id,
            "graph_edit_score": self.graph_edit_score,
            "cross_occurrence_value_overlap": self.cross_occurrence_value_overlap,
            "semantic_names_available": False,
            "predeclared_layout_or_factor_roles": [],
            "layout_id": self.layout_id,
        }


def discover_generic_layout_v5(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    layout_domain: str,
) -> DiscoveredLayoutV5:
    state_width, action_width, _ = _validate_occurrence(rows, catalogue)
    state_base = [_state_unary(rows, column) for column in range(state_width)]
    action_base = [_action_unary(catalogue, field) for field in range(action_width)]
    sa = {
        (column, field): _state_action_edge(rows, catalogue, column, field)
        for column in range(state_width)
        for field in range(action_width)
    }
    ss = {
        (left, right): _state_state_edge(rows, left, right)
        for left in range(state_width)
        for right in range(state_width)
    }
    aa = {
        (left, right): _action_action_edge(catalogue, left, right)
        for left in range(action_width)
        for right in range(action_width)
    }
    evaluations = state_width * len(rows) + action_width * len(catalogue)
    evaluations += state_width * action_width * (
        len(rows) * (len(catalogue) + 4)
    )
    evaluations += state_width * state_width * len(rows) * 12
    evaluations += action_width * action_width * len(catalogue) * 3
    state_colors = [_digest(row) for row in state_base]
    action_colors = [_digest(row) for row in action_base]
    rounds = 0
    for rounds in range(1, LAYOUT_REFINEMENT_MAX_ROUNDS_V5 + 1):
        next_state = []
        for column in range(state_width):
            incident = [
                ["S_OUT", ss[(column, other)], state_colors[other]]
                for other in range(state_width)
            ] + [
                ["S_IN", ss[(other, column)], state_colors[other]]
                for other in range(state_width)
            ] + [
                ["A", sa[(column, field)], action_colors[field]]
                for field in range(action_width)
            ]
            next_state.append(_digest([state_base[column], sorted(incident, key=_canonical_key)]))
        next_action = []
        for field in range(action_width):
            incident = [
                ["A_OUT", aa[(field, other)], action_colors[other]]
                for other in range(action_width)
            ] + [
                ["A_IN", aa[(other, field)], action_colors[other]]
                for other in range(action_width)
            ] + [
                ["S", sa[(column, field)], state_colors[column]]
                for column in range(state_width)
            ]
            next_action.append(_digest([action_base[field], sorted(incident, key=_canonical_key)]))
        if next_state == state_colors and next_action == action_colors:
            break
        state_colors, action_colors = next_state, next_action
    if len(set(state_colors)) != state_width:
        _fail("raw state relation graph did not induce a unique factorization")
    if len(set(action_colors)) != action_width:
        _fail("raw action relation graph did not induce a unique factorization")
    state_order = tuple(sorted(range(state_width), key=lambda item: state_colors[item]))
    action_order = tuple(sorted(range(action_width), key=lambda item: action_colors[item]))
    ordered_state_colors = tuple(state_colors[item] for item in state_order)
    ordered_action_colors = tuple(action_colors[item] for item in action_order)
    signature_payload = {
        "meta_grammar": list(LAYOUT_RELATION_META_GRAMMAR_V5),
        "state_width": state_width,
        "action_width": action_width,
        "state_unary_inventory": sorted(
            (_jsonable(row) for row in state_base), key=_canonical_key
        ),
        "action_unary_inventory": sorted(
            (_jsonable(row) for row in action_base), key=_canonical_key
        ),
    }
    signature = _digest(signature_payload)
    payload = {
        "state_canonical_to_raw": list(state_order),
        "action_canonical_to_raw": list(action_order),
        "state_structural_colors": list(ordered_state_colors),
        "action_structural_colors": list(ordered_action_colors),
        "schema_signature": signature,
        "refinement_rounds": rounds,
        "relation_evaluations": evaluations,
        "reference_layout_id": None,
        "graph_edit_score": 0,
        "cross_occurrence_value_overlap": 0,
        "semantic_names_available": False,
        "predeclared_layout_or_factor_roles": [],
    }
    return DiscoveredLayoutV5(
        state_order,
        action_order,
        ordered_state_colors,
        ordered_action_colors,
        signature,
        rounds,
        evaluations,
        content_id(layout_domain, payload),
        None,
        0,
        0,
    )


def _group_candidates(
    reference_base: list[tuple[Any, ...]],
    target_base: list[tuple[Any, ...]],
) -> tuple[tuple[int, ...], ...]:
    reference_groups: dict[tuple[Any, ...], list[int]] = {}
    target_groups: dict[tuple[Any, ...], list[int]] = {}
    for index, value in enumerate(reference_base):
        reference_groups.setdefault(value, []).append(index)
    for index, value in enumerate(target_base):
        target_groups.setdefault(value, []).append(index)
    if set(reference_groups) != set(target_groups) or any(
        len(reference_groups[key]) != len(target_groups[key])
        for key in reference_groups
    ):
        _fail("target unary factor inventory is incompatible with the source")
    ordered_groups = sorted(reference_groups, key=_canonical_key)
    group_rows = []
    for key in ordered_groups:
        reference_indices = reference_groups[key]
        target_indices = target_groups[key]
        group_rows.append(
            tuple(
                dict(zip(reference_indices, row, strict=True))
                for row in permutations(target_indices)
            )
        )
    result = []
    for selected in product(*group_rows):
        merged: dict[int, int] = {}
        for row in selected:
            merged.update(row)
        result.append(tuple(merged[index] for index in range(len(reference_base))))
    return tuple(result)


def _edge_mismatch(left: Any, right: Any) -> int:
    return int(left != right)


def _universal_implication_mismatch(left: Any, right: Any) -> int:
    if type(left) is tuple and type(right) is tuple and len(left) == len(right):
        return sum(
            _universal_implication_mismatch(a, b)
            for a, b in zip(left, right, strict=True)
        )
    if left == "ALL":
        return int(right not in {"ALL", "EMPTY"})
    return 0


def _observed_behavior_class(
    rows: tuple[FlatRawTransitionV4, ...], column: int
) -> str:
    grouped: dict[tuple[tuple[int, ...], int], set[int]] = {}
    for row in rows:
        grouped.setdefault((row.pre, row.action.key), set()).add(row.post[column])
    if any(len(values) > 1 for values in grouped.values()):
        return "BRANCHED"
    if all(row.post[column] == row.pre[column] + 1 for row in rows):
        return "UNIT_INCREMENT"
    if any(row.post[column] != row.pre[column] for row in rows):
        return "DYNAMIC"
    return "STABLE"


def _meta_state_candidates(
    reference_rows: tuple[FlatRawTransitionV4, ...],
    target_rows: tuple[FlatRawTransitionV4, ...],
) -> tuple[tuple[int, ...], ...]:
    state_width = len(reference_rows[0].pre)
    reference_status = [
        column
        for column in range(state_width)
        if _state_unary(reference_rows, column)[-1] == "TERMINAL_TOKEN"
    ]
    if len(reference_status) != 1:
        _fail("source relation graph did not expose one anonymous terminal factor")
    status_column = reference_status[0]
    active_values = {
        row.post[status_column]
        for row in reference_rows
        if row.terminal_acceptance_after is None
    }
    if len(active_values) != 1:
        _fail("source anonymous active token changed")
    active_value = next(iter(active_values))
    target_status = [
        column
        for column in range(state_width)
        if all(
            row.pre[column] == active_value
            and (
                row.post[column] == active_value
                or row.terminal_acceptance_after is not None
            )
            for row in target_rows
        )
    ]
    if len(target_status) != 1:
        _fail("structural meta-prior did not identify one target terminal factor")
    fixed = {status_column: target_status[0]}
    reference_groups: dict[str, list[int]] = {}
    target_groups: dict[str, list[int]] = {}
    for column in range(state_width):
        if column != status_column:
            reference_groups.setdefault(
                _observed_behavior_class(reference_rows, column), []
            ).append(column)
        if column != target_status[0]:
            target_groups.setdefault(
                _observed_behavior_class(target_rows, column), []
            ).append(column)
    if set(reference_groups) != set(target_groups) or any(
        len(reference_groups[key]) != len(target_groups[key])
        for key in reference_groups
    ):
        _fail("partial target behavior partition is incompatible with the source")
    rows = []
    ordered = sorted(reference_groups)
    choices = []
    for key in ordered:
        reference_indices = reference_groups[key]
        target_indices = target_groups[key]
        choices.append(
            tuple(
                dict(zip(reference_indices, candidate, strict=True))
                for candidate in permutations(target_indices)
            )
        )
    for selected in product(*choices):
        mapping = dict(fixed)
        for item in selected:
            mapping.update(item)
        rows.append(tuple(mapping[index] for index in range(state_width)))
    return tuple(rows)


def match_generic_layout_meta_prior_v5(
    reference_rows: tuple[FlatRawTransitionV4, ...],
    reference_catalogue: tuple[FlatRawActionV4, ...],
    reference_layout: DiscoveredLayoutV5,
    target_rows: tuple[FlatRawTransitionV4, ...],
    target_catalogue: tuple[FlatRawActionV4, ...],
    *,
    layout_domain: str,
) -> DiscoveredLayoutV5:
    reference_state_width, reference_action_width, _ = _validate_occurrence(
        reference_rows, reference_catalogue
    )
    target_state_width, target_action_width, _ = _validate_occurrence(
        target_rows, target_catalogue
    )
    if (reference_state_width, reference_action_width) != (
        target_state_width,
        target_action_width,
    ):
        _fail("target raw widths are incompatible with the structural meta-prior")
    state_width = reference_state_width
    action_width = reference_action_width
    reference_action_base = [
        _action_unary(reference_catalogue, field) for field in range(action_width)
    ]
    target_action_base = [
        _action_unary(target_catalogue, field) for field in range(action_width)
    ]
    action_candidates = _group_candidates(reference_action_base, target_action_base)
    state_candidates = _meta_state_candidates(reference_rows, target_rows)
    if len(action_candidates) * len(state_candidates) > META_PRIOR_ALIGNMENT_MAX_CANDIDATES_V5:
        _fail("structural-meta-prior alignment exceeded its registered search cap")
    reference_sa = {
        (column, field): _state_action_edge(
            reference_rows, reference_catalogue, column, field
        )
        for column in range(state_width)
        for field in range(action_width)
    }
    target_sa = {
        (column, field): _state_action_edge(
            target_rows, target_catalogue, column, field
        )
        for column in range(state_width)
        for field in range(action_width)
    }
    reference_ss = {
        (left, right): _state_state_edge(reference_rows, left, right)
        for left in range(state_width)
        for right in range(state_width)
    }
    target_ss = {
        (left, right): _state_state_edge(target_rows, left, right)
        for left in range(state_width)
        for right in range(state_width)
    }
    reference_aa = {
        (left, right): _action_action_edge(reference_catalogue, left, right)
        for left in range(action_width)
        for right in range(action_width)
    }
    target_aa = {
        (left, right): _action_action_edge(target_catalogue, left, right)
        for left in range(action_width)
        for right in range(action_width)
    }
    reference_action_values = [
        {action.fields[field] for action in reference_catalogue}
        for field in range(action_width)
    ]
    target_action_values = [
        {action.fields[field] for action in target_catalogue}
        for field in range(action_width)
    ]
    scored = []
    for action_map in action_candidates:
        overlap = sum(
            len(reference_action_values[field] & target_action_values[action_map[field]])
            for field in range(action_width)
        )
        aa_cost = sum(
            _universal_implication_mismatch(
                reference_aa[(left, right)],
                target_aa[(action_map[left], action_map[right])],
            )
            for left in range(action_width)
            for right in range(action_width)
        )
        for state_map in state_candidates:
            cost = aa_cost
            cost += sum(
                _universal_implication_mismatch(
                    reference_sa[(column, field)],
                    target_sa[(state_map[column], action_map[field])],
                )
                for column in range(state_width)
                for field in range(action_width)
            )
            cost += sum(
                _universal_implication_mismatch(
                    reference_ss[(left, right)],
                    target_ss[(state_map[left], state_map[right])],
                )
                for left in range(state_width)
                for right in range(state_width)
            )
            scored.append((cost, -overlap, state_map, action_map))
    minimum = min(row[:2] for row in scored)
    selected = [row for row in scored if row[:2] == minimum]
    if len(selected) != 1:
        _fail(
            "minimum structural-meta-prior alignment was not unique: "
            f"score={minimum}, candidate_count={len(selected)}"
        )
    cost, negative_overlap, state_map, action_map = selected[0]
    state_order = tuple(
        state_map[raw] for raw in reference_layout.state_canonical_to_raw
    )
    action_order = tuple(
        action_map[raw] for raw in reference_layout.action_canonical_to_raw
    )
    payload = {
        "state_canonical_to_raw": list(state_order),
        "action_canonical_to_raw": list(action_order),
        "state_structural_colors": list(reference_layout.state_colors),
        "action_structural_colors": list(reference_layout.action_colors),
        "schema_signature": reference_layout.schema_signature,
        "refinement_rounds": 0,
        "relation_evaluations": len(action_candidates) * len(state_candidates),
        "reference_layout_id": reference_layout.layout_id,
        "graph_edit_score": cost,
        "cross_occurrence_value_overlap": -negative_overlap,
        "semantic_names_available": False,
        "predeclared_layout_or_factor_roles": [],
    }
    return DiscoveredLayoutV5(
        state_order,
        action_order,
        reference_layout.state_colors,
        reference_layout.action_colors,
        reference_layout.schema_signature,
        0,
        len(action_candidates) * len(state_candidates),
        content_id(layout_domain, payload),
        reference_layout.layout_id,
        cost,
        -negative_overlap,
    )


def match_generic_layout_v5(
    reference_rows: tuple[FlatRawTransitionV4, ...],
    reference_catalogue: tuple[FlatRawActionV4, ...],
    reference_layout: DiscoveredLayoutV5,
    target_rows: tuple[FlatRawTransitionV4, ...],
    target_catalogue: tuple[FlatRawActionV4, ...],
    *,
    layout_domain: str,
) -> DiscoveredLayoutV5:
    reference_state_width, reference_action_width, _ = _validate_occurrence(
        reference_rows, reference_catalogue
    )
    target_state_width, target_action_width, _ = _validate_occurrence(
        target_rows, target_catalogue
    )
    if (reference_state_width, reference_action_width) != (
        target_state_width,
        target_action_width,
    ):
        _fail("target raw widths are incompatible with the source relation graph")
    state_width = reference_state_width
    action_width = reference_action_width
    reference_state_base = [
        _state_unary(reference_rows, column) for column in range(state_width)
    ]
    target_state_base = [
        _state_unary(target_rows, column) for column in range(state_width)
    ]
    reference_action_base = [
        _action_unary(reference_catalogue, field) for field in range(action_width)
    ]
    target_action_base = [
        _action_unary(target_catalogue, field) for field in range(action_width)
    ]
    reference_sa = {
        (column, field): _state_action_edge(
            reference_rows, reference_catalogue, column, field
        )
        for column in range(state_width)
        for field in range(action_width)
    }
    target_sa = {
        (column, field): _state_action_edge(
            target_rows, target_catalogue, column, field
        )
        for column in range(state_width)
        for field in range(action_width)
    }
    reference_ss = {
        (left, right): _state_state_edge(reference_rows, left, right)
        for left in range(state_width)
        for right in range(state_width)
    }
    target_ss = {
        (left, right): _state_state_edge(target_rows, left, right)
        for left in range(state_width)
        for right in range(state_width)
    }
    reference_aa = {
        (left, right): _action_action_edge(reference_catalogue, left, right)
        for left in range(action_width)
        for right in range(action_width)
    }
    target_aa = {
        (left, right): _action_action_edge(target_catalogue, left, right)
        for left in range(action_width)
        for right in range(action_width)
    }
    action_candidates = _group_candidates(reference_action_base, target_action_base)
    action_scores = []
    for action_map in action_candidates:
        score = sum(
            _edge_mismatch(
                reference_aa[(left, right)],
                target_aa[(action_map[left], action_map[right])],
            )
            for left in range(action_width)
            for right in range(action_width)
        )
        score += sum(
            _edge_mismatch(
                sorted(
                    (reference_sa[(column, field)] for column in range(state_width)),
                    key=_canonical_key,
                ),
                sorted(
                    (
                        target_sa[(column, action_map[field])]
                        for column in range(state_width)
                    ),
                    key=_canonical_key,
                ),
            )
            for field in range(action_width)
        )
        action_scores.append((score, action_map))
    minimum_action_score = min(row[0] for row in action_scores)
    retained_actions = [
        row[1] for row in action_scores if row[0] == minimum_action_score
    ]
    state_candidates = _group_candidates(reference_state_base, target_state_base)
    scored = []
    for action_map in retained_actions:
        for state_map in state_candidates:
            score = minimum_action_score
            score += sum(
                _edge_mismatch(
                    reference_sa[(column, field)],
                    target_sa[(state_map[column], action_map[field])],
                )
                for column in range(state_width)
                for field in range(action_width)
            )
            score += sum(
                _edge_mismatch(
                    reference_ss[(left, right)],
                    target_ss[(state_map[left], state_map[right])],
                )
                for left in range(state_width)
                for right in range(state_width)
            )
            scored.append((score, state_map, action_map))
    minimum = min(row[0] for row in scored)
    selected = [row for row in scored if row[0] == minimum]
    if len(selected) != 1:
        _fail(
            "minimum relation-graph alignment was not unique: "
            f"score={minimum}, candidate_count={len(selected)}"
        )
    score, state_map, action_map = selected[0]
    state_order = tuple(
        state_map[raw] for raw in reference_layout.state_canonical_to_raw
    )
    action_order = tuple(
        action_map[raw] for raw in reference_layout.action_canonical_to_raw
    )
    signature = reference_layout.schema_signature
    payload = {
        "state_canonical_to_raw": list(state_order),
        "action_canonical_to_raw": list(action_order),
        "state_structural_colors": list(reference_layout.state_colors),
        "action_structural_colors": list(reference_layout.action_colors),
        "schema_signature": signature,
        "refinement_rounds": 0,
        "relation_evaluations": len(action_candidates) + len(scored),
        "reference_layout_id": reference_layout.layout_id,
        "graph_edit_score": score,
        "cross_occurrence_value_overlap": 0,
        "semantic_names_available": False,
        "predeclared_layout_or_factor_roles": [],
    }
    return DiscoveredLayoutV5(
        state_order,
        action_order,
        reference_layout.state_colors,
        reference_layout.action_colors,
        signature,
        0,
        len(action_candidates) + len(scored),
        content_id(layout_domain, payload),
        reference_layout.layout_id,
        score,
        0,
    )


def align_generic_occurrence_v5(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    layout: DiscoveredLayoutV5,
    *,
    canonical_occurrence: int,
) -> tuple[tuple[FlatRawTransitionV4, ...], tuple[FlatRawActionV4, ...]]:
    state_width, action_width, by_key = _validate_occurrence(rows, catalogue)
    if state_width != len(layout.state_canonical_to_raw) or action_width != len(layout.action_canonical_to_raw):
        _fail("layout alignment width changed")
    aligned_catalogue = tuple(
        FlatRawActionV4(
            action.key,
            tuple(action.fields[index] for index in layout.action_canonical_to_raw),
        )
        for action in catalogue
    )
    aligned_by_key = {action.key: action for action in aligned_catalogue}
    aligned_rows = tuple(
        FlatRawTransitionV4(
            canonical_occurrence,
            row.index,
            tuple(row.pre[index] for index in layout.state_canonical_to_raw),
            row.legal_before,
            aligned_by_key[by_key[row.action.key].key],
            tuple(row.post[index] for index in layout.state_canonical_to_raw),
            row.legal_after,
            row.terminal_acceptance_after,
            row.outcome_tape_sha256,
        )
        for row in rows
    )
    return aligned_rows, aligned_catalogue


def synthesize_layout_factorized_world_model_v5(
    rows_by_occurrence: Mapping[int, tuple[FlatRawTransitionV4, ...]],
    catalogues: Mapping[int, tuple[FlatRawActionV4, ...]],
    *,
    layout_domain: str,
    program_domain: str,
    support_domain: str,
) -> dict[str, Any]:
    if set(rows_by_occurrence) != set(catalogues) or not rows_by_occurrence:
        _fail("layout-factorized occurrence inventory changed")
    layouts = {}
    aligned_rows = []
    aligned_catalogues = {}
    ordered_occurrences = sorted(rows_by_occurrence)
    reference_occurrence = ordered_occurrences[0]
    reference_layout = discover_generic_layout_v5(
        rows_by_occurrence[reference_occurrence],
        catalogues[reference_occurrence],
        layout_domain=layout_domain,
    )
    for canonical_occurrence, occurrence in enumerate(ordered_occurrences):
        layout = (
            reference_layout
            if occurrence == reference_occurrence
            else match_generic_layout_v5(
                rows_by_occurrence[reference_occurrence],
                catalogues[reference_occurrence],
                reference_layout,
                rows_by_occurrence[occurrence],
                catalogues[occurrence],
                layout_domain=layout_domain,
            )
        )
        layouts[occurrence] = layout
        rows, catalogue = align_generic_occurrence_v5(
            rows_by_occurrence[occurrence],
            catalogues[occurrence],
            layout,
            canonical_occurrence=canonical_occurrence,
        )
        aligned_rows.extend(rows)
        aligned_catalogues[canonical_occurrence] = catalogue
    signatures = {layout.schema_signature for layout in layouts.values()}
    if len(signatures) != 1:  # pragma: no cover - constructor invariant
        raise AssertionError
    program = synthesize_generic_atomic_program_v4(
        tuple(aligned_rows), aligned_catalogues, program_domain=program_domain
    )
    support = derive_atomic_dependency_support_v4(
        program,
        tuple(aligned_rows),
        aligned_catalogues,
        support_domain=support_domain,
    )
    return {
        "schema": "acfqp.generic_layout_factorized_world_model.v5",
        "relation_meta_grammar": list(LAYOUT_RELATION_META_GRAMMAR_V5),
        "layout_selection": "UNIQUE_ITERATIVE_RELATION_GRAPH_COLOR",
        "layout_factorization_documents": [
            {"occurrence": occurrence, **layouts[occurrence].to_document()}
            for occurrence in sorted(layouts)
        ],
        "shared_schema_signature": next(iter(signatures)),
        "compiled_program": program,
        "dependency_support": support,
        "layout_relation_evaluations": sum(
            layout.relation_evaluations for layout in layouts.values()
        ),
        "domain_name_available_to_layout_discovery": False,
        "semantic_names_available_to_layout_discovery": False,
        "predeclared_layout_or_factor_roles": [],
        "specialized_layout_discovery_pattern_count": 0,
        "status": "LAYOUT_FACTORIZATION_AND_WORLD_MODEL_SYNTHESIZED_FROM_RAW_RELATIONS",
    }


def verify_target_layout_compatibility_v5(
    source_model: Mapping[str, Any], target_layout: DiscoveredLayoutV5
) -> bool:
    return source_model.get("shared_schema_signature") == target_layout.schema_signature


__all__ = (
    "DiscoveredLayoutV5",
    "GenericLayoutFactorizedWorldModelV5Error",
    "LAYOUT_REFINEMENT_MAX_ROUNDS_V5",
    "LAYOUT_RELATION_META_GRAMMAR_V5",
    "META_PRIOR_ALIGNMENT_MAX_CANDIDATES_V5",
    "align_generic_occurrence_v5",
    "discover_generic_layout_v5",
    "match_generic_layout_v5",
    "match_generic_layout_meta_prior_v5",
    "synthesize_layout_factorized_world_model_v5",
    "verify_target_layout_compatibility_v5",
)
