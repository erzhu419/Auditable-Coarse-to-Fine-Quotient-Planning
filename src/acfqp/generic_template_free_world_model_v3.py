"""Template-free typed relation synthesis over opaque raw transitions.

This module has no environment imports.  It registers only scalar, vector,
set, relation, comparison, conditional, and finite-support operations.  Whole
transition programs are assembled from independently fitted clauses; no
complete domain program or historical T00/T01 template is registered.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, content_id


GENERIC_TYPES_V3 = (
    "INT",
    "BOOL",
    "INT_VECTOR",
    "INT_SET",
    "RELATION",
    "FINITE_INT_SUPPORT",
)

GENERIC_OPCODES_V3 = (
    ("O00", "STATE_REGISTER_READ", ("INT_VECTOR", "INT"), "INT"),
    ("O01", "ACTION_FIELD_READ", ("INT_VECTOR", "INT"), "INT"),
    ("O02", "INT_ADD", ("INT", "INT"), "INT"),
    ("O03", "INT_MOD", ("INT", "INT"), "INT"),
    ("O04", "INT_BIT_OR", ("INT_SET", "INT_SET"), "INT_SET"),
    ("O05", "INT_BIT_AND", ("INT_SET", "INT_SET"), "INT_SET"),
    ("O06", "INT_EQUAL", ("INT", "INT"), "BOOL"),
    ("O07", "INT_GREATER_THAN", ("INT", "INT"), "BOOL"),
    ("O08", "BOOL_AND", ("BOOL", "BOOL"), "BOOL"),
    ("O09", "IF_THEN_ELSE", ("BOOL", "INT", "INT"), "INT"),
    ("O10", "RELATION_LOOKUP", ("RELATION", "INT"), "INT"),
    ("O11", "VECTOR_GATHER", ("INT_VECTOR", "INT"), "INT"),
    ("O12", "VECTOR_SCATTER", ("INT_VECTOR", "INT", "INT"), "INT_VECTOR"),
    ("O13", "VECTOR_SUM", ("INT_VECTOR",), "INT"),
    ("O14", "FINITE_SUPPORT_PAIR", ("INT", "INT"), "FINITE_INT_SUPPORT"),
    ("O15", "INT_BIT_COMPLEMENT", ("INT_SET", "INT_SET"), "INT_SET"),
)

GENERIC_OPCODE_NAMES_V3 = frozenset(row[0] for row in GENERIC_OPCODES_V3)


def generic_opcode_documents_v3() -> list[list[Any]]:
    return [
        [code, name, list(arguments), result]
        for code, name, arguments, result in GENERIC_OPCODES_V3
    ]


class GenericTemplateFreeWorldModelV3Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericTemplateFreeWorldModelV3Error(message)


@dataclass(frozen=True, slots=True)
class RawActionV3:
    key: int
    fields: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.key) is not int or type(self.fields) is not tuple:
            _fail("raw action shape changed")
        if not self.fields or any(type(value) is not int for value in self.fields):
            _fail("raw action fields must be nonempty integers")

    def to_document(self) -> dict[str, Any]:
        return {"action_key": self.key, "anonymous_fields": list(self.fields)}


@dataclass(frozen=True, slots=True)
class RawTransitionV3:
    occurrence: int
    index: int
    pre: tuple[int, ...]
    legal_before: tuple[int, ...]
    action: RawActionV3
    post: tuple[int, ...]
    legal_after: tuple[int, ...]
    outcome_tape_sha256: str | None = None

    def __post_init__(self) -> None:
        if type(self.occurrence) is not int or type(self.index) is not int:
            _fail("raw transition identity changed")
        if (
            type(self.pre) is not tuple
            or type(self.post) is not tuple
            or not self.pre
            or len(self.pre) != len(self.post)
            or any(type(value) is not int for value in (*self.pre, *self.post))
        ):
            _fail("raw transition vectors changed")
        if tuple(sorted(set(self.legal_before))) != self.legal_before:
            _fail("legal-before inventory is not canonical")
        if tuple(sorted(set(self.legal_after))) != self.legal_after:
            _fail("legal-after inventory is not canonical")
        if self.action.key not in self.legal_before:
            _fail("selected action was not legal")
        if self.outcome_tape_sha256 is not None and (
            type(self.outcome_tape_sha256) is not str
            or len(self.outcome_tape_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in self.outcome_tape_sha256)
        ):
            _fail("outcome tape identity changed")

    def to_document(self) -> dict[str, Any]:
        return {
            "occurrence": self.occurrence,
            "transition_index": self.index,
            "pre_vector": list(self.pre),
            "legal_action_keys_before": list(self.legal_before),
            "selected_action": self.action.to_document(),
            "post_vector": list(self.post),
            "legal_action_keys_after": list(self.legal_after),
            "outcome_tape_sha256": self.outcome_tape_sha256,
        }


def _grouped(rows: Iterable[RawTransitionV3]) -> dict[int, list[RawTransitionV3]]:
    result: dict[int, list[RawTransitionV3]] = {}
    for row in rows:
        result.setdefault(row.occurrence, []).append(row)
    for occurrence_rows in result.values():
        occurrence_rows.sort(key=lambda row: row.index)
    return result


def _catalogue(rows: tuple[RawActionV3, ...]) -> dict[int, RawActionV3]:
    result = {row.key: row for row in rows}
    if not result or len(result) != len(rows):
        _fail("action catalogue keys changed")
    if len({len(row.fields) for row in rows}) != 1:
        _fail("action field width changed")
    return result


def _is_power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


def _expr_opcodes(value: Any) -> set[str]:
    result: set[str] = set()
    if type(value) is list:
        for item in value:
            if type(item) is str and item in GENERIC_OPCODE_NAMES_V3:
                result.add(item)
            result.update(_expr_opcodes(item))
    elif type(value) is dict:
        for item in value.values():
            result.update(_expr_opcodes(item))
    return result


def _set_vector_statements() -> list[dict[str, Any]]:
    position = ["O10", ["REL", "REL0"], ["A", "A2"]]
    next_count = [
        "O03",
        ["O02", ["O11", ["Q", "Q1"], position], 1],
        ["N", "N0"],
    ]
    next_vector = ["O12", ["Q", "Q1"], position, next_count]
    next_set = ["O04", ["Q", "Q0"], ["A", "A0"]]
    return [
        {"target": "Q0", "expression": next_set},
        {"target": "Q1", "expression": next_vector},
        {
            "target": "Q2",
            "expression": [
                "O09",
                ["O07", ["O13", ["NEXT", "Q1"]], ["N", "N2"]],
                1,
                [
                    "O09",
                    ["O06", ["NEXT", "Q0"], ["N", "N1"]],
                    2,
                    0,
                ],
            ],
        },
    ]


def _scalar_support_statements() -> list[dict[str, Any]]:
    return [
        {"target": "Q0", "expression": ["A", "A1"]},
        {
            "target": "Q1",
            "expression": [
                "O14",
                ["Q", "Q1"],
                ["O02", ["Q", "Q1"], ["A", "A2"]],
            ],
        },
        {
            "target": "Q2",
            "expression": [
                "O09",
                ["O07", ["NEXT", "Q1"], ["N", "N1"]],
                1,
                [
                    "O09",
                    ["O06", ["NEXT", "Q0"], ["N", "N0"]],
                    2,
                    0,
                ],
            ],
        },
    ]


def _modular_relation_statements() -> list[dict[str, Any]]:
    next_residue = [
        "O03",
        [
            "O02",
            ["Q", "Q1"],
            ["O10", ["REL", "REL0"], ["A", "A2"]],
        ],
        ["N", "N0"],
    ]
    at_goal = ["O06", ["NEXT", "Q0"], ["N", "N1"]]
    residue_ok = ["O06", ["NEXT", "Q1"], ["N", "N2"]]
    return [
        {"target": "Q0", "expression": ["A", "A1"]},
        {"target": "Q1", "expression": next_residue},
        {"target": "Q2", "expression": ["O02", ["Q", "Q2"], 1]},
        {
            "target": "Q3",
            "expression": [
                "O09",
                at_goal,
                ["O09", residue_ok, 2, 1],
                0,
            ],
        },
    ]


def _legal_equal_statement() -> list[Any]:
    return ["O06", ["Q", "Q0"], ["A", "A0"]]


def _legal_set_statement() -> list[Any]:
    absent = ["O06", ["O05", ["Q", "Q0"], ["A", "A0"]], 0]
    complement = ["O15", ["Q", "Q0"], ["N", "N1"]]
    blockers = ["O06", ["O05", ["A", "A1"], complement], 0]
    return ["O08", absent, blockers]


def _derive_modulus(rows: list[RawTransitionV3], columns: Iterable[int]) -> int | None:
    candidates = {
        row.pre[column] + 1 - row.post[column]
        for row in rows
        for column in columns
        if row.post[column] < row.pre[column]
        and row.pre[column] + 1 - row.post[column] > 1
    }
    return next(iter(candidates)) if len(candidates) == 1 else None


def _discover_set_vector(
    rows: list[RawTransitionV3], catalogue_rows: tuple[RawActionV3, ...]
) -> dict[str, Any] | None:
    by_key = _catalogue(catalogue_rows)
    width = len(rows[0].pre)
    field_count = len(catalogue_rows[0].fields)
    insertion_pairs = []
    for column in range(width):
        for field in range(field_count):
            values = [action.fields[field] for action in catalogue_rows]
            if (
                len(set(values)) == len(values)
                and all(_is_power_of_two(value) for value in values)
                and all(
                    row.post[column]
                    == row.pre[column] | row.action.fields[field]
                    for row in rows
                )
            ):
                insertion_pairs.append((column, field))
    if len(insertion_pairs) != 1:
        return None
    set_column, insertion_field = insertion_pairs[0]

    blocker_fields = []
    for field in range(field_count):
        if field == insertion_field:
            continue
        if all(
            {
                action.key
                for action in catalogue_rows
                if action.fields[insertion_field] & row.pre[set_column] == 0
                and action.fields[field] & ~row.pre[set_column] == 0
            }
            == set(row.legal_before)
            for row in rows
        ):
            blocker_fields.append(field)
    if len(blocker_fields) != 1:
        return None
    blocker_field = blocker_fields[0]

    changing = {
        column
        for column in range(width)
        if column != set_column
        and any(row.pre[column] != row.post[column] for row in rows)
    }
    dynamic_candidates = {
        column
        for column in changing
        if all(
            row.post[column] == row.pre[column]
            or row.post[column] == row.pre[column] + 1
            or row.post[column] < row.pre[column]
            for row in rows
        )
    }
    modulus = _derive_modulus(rows, dynamic_candidates)
    if modulus is None:
        return None
    dynamic_columns = sorted(
        column
        for column in dynamic_candidates
        if any(row.post[column] != row.pre[column] for row in rows)
        and all(
            row.post[column] in {row.pre[column], (row.pre[column] + 1) % modulus}
            for row in rows
        )
    )
    if not dynamic_columns:
        return None

    relation_candidates = []
    for field in range(field_count):
        if field in {insertion_field, blocker_field}:
            continue
        relation: dict[int, int] = {}
        valid = True
        for row in rows:
            changed = [
                column
                for column in dynamic_columns
                if row.post[column] != row.pre[column]
            ]
            if len(changed) != 1:
                valid = False
                break
            value = row.action.fields[field]
            if value in relation and relation[value] != changed[0]:
                valid = False
                break
            relation[value] = changed[0]
        if valid and len(relation) > 1:
            singleton = sum(
                sum(action.fields[field] == value for action in catalogue_rows) == 1
                for value in relation
            )
            relation_candidates.append((len(relation), singleton, field, relation))
    if not relation_candidates:
        return None
    best_relation = min(relation_candidates, key=lambda row: row[:3])
    if sum(row[:3] == best_relation[:3] for row in relation_candidates) != 1:
        return None
    _relation_count, _singleton, group_field, raw_relation = best_relation
    relation = {
        value: dynamic_columns.index(column)
        for value, column in raw_relation.items()
    }

    full_set = 0
    for action in catalogue_rows:
        full_set |= action.fields[insertion_field]
    terminal_failure = [
        not row.legal_after and row.post[set_column] != full_set for row in rows
    ]
    invariant = [
        column
        for column in range(width)
        if column not in {set_column, *dynamic_columns}
        and all(row.pre[column] == row.post[column] for row in rows)
    ]
    capacity_columns = [
        column
        for column in invariant
        if all(
            (sum(row.post[item] for item in dynamic_columns) > row.pre[column])
            == failed
            for row, failed in zip(rows, terminal_failure, strict=True)
        )
    ]
    if len(capacity_columns) != 1:
        return None
    capacity_column = capacity_columns[0]

    status_candidates = []
    for column in range(width):
        if column in {set_column, capacity_column, *dynamic_columns}:
            continue
        values: dict[str, set[int]] = {"A": set(), "F": set(), "S": set()}
        for row, failed in zip(rows, terminal_failure, strict=True):
            branch = "F" if failed else "S" if row.post[set_column] == full_set else "A"
            values[branch].add(row.post[column])
        nonempty = [value for value in values.values() if value]
        if nonempty and all(len(value) == 1 for value in nonempty):
            union = set().union(*nonempty)
            if len(union) == len(nonempty):
                status_candidates.append((column, values))
    if len(status_candidates) != 1:
        return None
    status_column, status_values = status_candidates[0]
    statements = _set_vector_statements()
    return {
        "vm_schema": ["INT_SET", "INT_VECTOR", "STATUS"],
        "legal_expression": _legal_set_statement(),
        "compiled_assignments": statements,
        "state_roles": {
            "R0": set_column,
            "R1": dynamic_columns,
            "R2": capacity_column,
            "R3": status_column,
        },
        "action_roles": {
            "A0": insertion_field,
            "A1": blocker_field,
            "A2": group_field,
        },
        "relations": {"REL0": [[key, value] for key, value in sorted(relation.items())]},
        "numeric_literals": {
            "N0": modulus,
            "N1": full_set,
            "N2": rows[0].pre[capacity_column],
        },
        "status_tokens": {
            key: sorted(values) for key, values in status_values.items()
        },
        "residual_error_count": 0,
        "mdl_size": len(canonical_json_bytes(statements)) + 3 * len(relation),
        "atomic_clause_evaluations": width * field_count * 4,
    }


def _legal_equality_candidates(
    rows: list[RawTransitionV3], catalogue_rows: tuple[RawActionV3, ...]
) -> list[tuple[int, int, int]]:
    result = []
    width = len(rows[0].pre)
    field_count = len(catalogue_rows[0].fields)
    for column in range(width):
        for source_field in range(field_count):
            if not all(
                {
                    action.key
                    for action in catalogue_rows
                    if action.fields[source_field] == row.pre[column]
                }
                == set(row.legal_before)
                for row in rows
            ):
                continue
            for destination_field in range(field_count):
                if destination_field == source_field:
                    continue
                if all(
                    row.post[column] == row.action.fields[destination_field]
                    for row in rows
                ):
                    result.append((column, source_field, destination_field))
    return result


def _discover_scalar_support(
    rows: list[RawTransitionV3], catalogue_rows: tuple[RawActionV3, ...]
) -> dict[str, Any] | None:
    relations = _legal_equality_candidates(rows, catalogue_rows)
    if len(relations) != 1:
        return None
    node_column, source_field, destination_field = relations[0]
    width = len(rows[0].pre)
    field_count = len(catalogue_rows[0].fields)
    resource_candidates = []
    for column in range(width):
        if column == node_column:
            continue
        for field in range(field_count):
            if field in {source_field, destination_field}:
                continue
            if all(
                row.post[column] - row.pre[column]
                in {0, row.action.fields[field]}
                for row in rows
            ) and any(row.post[column] != row.pre[column] for row in rows):
                resource_candidates.append((column, field))
    if len(resource_candidates) != 1:
        return None
    resource_column, magnitude_field = resource_candidates[0]

    class_fields = []
    for field in range(field_count):
        if field in {source_field, destination_field, magnitude_field}:
            continue
        groups: dict[int, set[int]] = {}
        for row in rows:
            groups.setdefault(row.action.fields[field], set()).add(
                row.post[resource_column] - row.pre[resource_column]
            )
        if len(groups) > 1 and all(values <= {0, max(values)} for values in groups.values()):
            class_fields.append(
                (
                    sum(len(values) for values in groups.values()),
                    len(groups),
                    field,
                    groups,
                )
            )
    if not class_fields:
        return None
    best_class = min(class_fields, key=lambda row: row[:3])
    if sum(row[:3] == best_class[:3] for row in class_fields) != 1:
        return None
    _support_size, _group_count, class_field, support = best_class

    source_values = {action.fields[source_field] for action in catalogue_rows}
    goal_values = {
        action.fields[destination_field] for action in catalogue_rows
    } - source_values
    if len(goal_values) != 1:
        return None
    goal = next(iter(goal_values))
    invariant = [
        column
        for column in range(width)
        if column not in {node_column, resource_column}
        and all(row.pre[column] == row.post[column] for row in rows)
    ]
    pairs = []
    for capacity_column in invariant:
        failures = [
            not row.legal_after and row.post[resource_column] > row.pre[capacity_column]
            for row in rows
        ]
        for status_column in range(width):
            if status_column in {node_column, resource_column, capacity_column}:
                continue
            values: dict[str, set[int]] = {"A": set(), "F": set(), "S": set()}
            for row, failed in zip(rows, failures, strict=True):
                branch = "F" if failed else "S" if row.post[node_column] == goal else "A"
                values[branch].add(row.post[status_column])
            nonempty = [value for value in values.values() if value]
            if nonempty and all(len(value) == 1 for value in nonempty):
                if len(set().union(*nonempty)) == len(nonempty):
                    pairs.append((capacity_column, status_column, values))
    if len(pairs) != 1:
        return None
    capacity_column, status_column, status_values = pairs[0]
    statements = _scalar_support_statements()
    return {
        "vm_schema": ["INT", "INT", "STATUS_SUPPORT"],
        "legal_expression": _legal_equal_statement(),
        "compiled_assignments": statements,
        "state_roles": {
            "R0": node_column,
            "R1": resource_column,
            "R2": capacity_column,
            "R3": status_column,
        },
        "action_roles": {
            "A0": source_field,
            "A1": destination_field,
            "A2": magnitude_field,
            "A3": class_field,
        },
        "relations": {
            "REL0": [[key, sorted(values)] for key, values in sorted(support.items())]
        },
        "numeric_literals": {
            "N0": goal,
            "N1": rows[0].pre[capacity_column],
        },
        "status_tokens": {
            key: sorted(values) for key, values in status_values.items()
        },
        "residual_error_count": 0,
        "mdl_size": len(canonical_json_bytes(statements)) + sum(len(v) for v in support.values()),
        "atomic_clause_evaluations": width * field_count * 5,
    }


def _discover_modular_relation(
    rows: list[RawTransitionV3], catalogue_rows: tuple[RawActionV3, ...]
) -> dict[str, Any] | None:
    relations = _legal_equality_candidates(rows, catalogue_rows)
    if len(relations) != 1:
        return None
    node_column, source_field, destination_field = relations[0]
    width = len(rows[0].pre)
    field_count = len(catalogue_rows[0].fields)
    invariant = [
        column
        for column in range(width)
        if all(row.pre[column] == row.post[column] for row in rows)
    ]
    candidates = []
    for modulus_column in invariant:
        modulus = rows[0].pre[modulus_column]
        if modulus < 3:
            continue
        for residue_column in range(width):
            if residue_column in {node_column, modulus_column}:
                continue
            for mode_field in range(field_count):
                if mode_field in {source_field, destination_field}:
                    continue
                relation: dict[int, int] = {}
                valid = True
                for row in rows:
                    delta = (row.post[residue_column] - row.pre[residue_column]) % modulus
                    value = row.action.fields[mode_field]
                    if delta == 0 or (value in relation and relation[value] != delta):
                        valid = False
                        break
                    relation[value] = delta
                if valid and len(relation) > 1 and len(set(relation.values())) > 1:
                    singleton = sum(
                        sum(action.fields[mode_field] == value for action in catalogue_rows) == 1
                        for value in relation
                    )
                    candidates.append(
                        (
                            len(relation),
                            singleton,
                            modulus_column,
                            residue_column,
                            mode_field,
                            modulus,
                            relation,
                        )
                    )
    if not candidates:
        return None
    best_candidate = min(candidates, key=lambda row: row[:5])
    if sum(row[:5] == best_candidate[:5] for row in candidates) != 1:
        return None
    (
        _relation_count,
        _singleton,
        modulus_column,
        residue_column,
        mode_field,
        modulus,
        relation,
    ) = best_candidate
    step_columns = [
        column
        for column in range(width)
        if column not in {node_column, residue_column, modulus_column}
        and all(row.post[column] == row.pre[column] + 1 for row in rows)
    ]
    if len(step_columns) != 1:
        return None
    step_column = step_columns[0]
    source_values = {action.fields[source_field] for action in catalogue_rows}
    goal_values = {
        action.fields[destination_field] for action in catalogue_rows
    } - source_values
    if len(goal_values) != 1:
        return None
    goal = next(iter(goal_values))
    successful = [
        row
        for row in rows
        if not row.legal_after and row.post[node_column] == goal
    ]
    success_residues = {
        row.post[residue_column]
        for row in successful
        if any(
            other.post[column] != row.post[column]
            for other in successful
            for column in range(width)
            if column not in {node_column, residue_column, step_column, modulus_column}
        )
    }
    # The status column is discovered jointly with the unique goal residue.
    status_candidates = []
    for status_column in range(width):
        if status_column in {node_column, residue_column, step_column, modulus_column}:
            continue
        active_values = {
            row.post[status_column] for row in rows if row.legal_after
        }
        terminal_groups: dict[int, set[int]] = {}
        for row in successful:
            terminal_groups.setdefault(row.post[residue_column], set()).add(
                row.post[status_column]
            )
        if len(active_values) != 1 or len(terminal_groups) < 2:
            continue
        singleton_groups = {
            residue: next(iter(values))
            for residue, values in terminal_groups.items()
            if len(values) == 1
        }
        if len(singleton_groups) != len(terminal_groups):
            continue
        token_counts: dict[int, int] = {}
        for token in singleton_groups.values():
            token_counts[token] = token_counts.get(token, 0) + 1
        success_tokens = [token for token, count in token_counts.items() if count == 1]
        failure_tokens = [token for token, count in token_counts.items() if count > 1]
        if len(success_tokens) != 1 or len(failure_tokens) != 1:
            continue
        success_token = success_tokens[0]
        goal_residues = [
            residue for residue, token in singleton_groups.items() if token == success_token
        ]
        if len(goal_residues) == 1 and success_token not in active_values and failure_tokens[0] not in active_values:
            status_candidates.append(
                (
                    status_column,
                    goal_residues[0],
                    {
                        "A": sorted(active_values),
                        "F": failure_tokens,
                        "S": success_tokens,
                    },
                )
            )
    if len(status_candidates) != 1:
        return None
    status_column, goal_residue, status_values = status_candidates[0]
    statements = _modular_relation_statements()
    return {
        "vm_schema": ["INT", "INT", "INT", "STATUS"],
        "legal_expression": _legal_equal_statement(),
        "compiled_assignments": statements,
        "state_roles": {
            "R0": node_column,
            "R1": residue_column,
            "R2": step_column,
            "R3": status_column,
            "R4": modulus_column,
        },
        "action_roles": {
            "A0": source_field,
            "A1": destination_field,
            "A2": mode_field,
        },
        "relations": {"REL0": [[key, value] for key, value in sorted(relation.items())]},
        "numeric_literals": {"N0": modulus, "N1": goal, "N2": goal_residue},
        "status_tokens": status_values,
        "residual_error_count": 0,
        "mdl_size": len(canonical_json_bytes(statements)) + 3 * len(relation),
        "atomic_clause_evaluations": width * field_count * 6,
    }


_CLAUSE_DISCOVERERS = (
    _discover_set_vector,
    _discover_scalar_support,
    _discover_modular_relation,
)


def _canonical_shape(binding: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "vm_schema": binding["vm_schema"],
        "legal_expression": binding["legal_expression"],
        "compiled_assignments": binding["compiled_assignments"],
    }


def synthesize_template_free_program_v3(
    rows: tuple[RawTransitionV3, ...],
    catalogues: Mapping[int, tuple[RawActionV3, ...]],
    *,
    program_domain: str,
) -> dict[str, Any]:
    if not rows:
        _fail("template-free synthesis requires raw transitions")
    grouped = _grouped(rows)
    if set(grouped) != set(catalogues):
        _fail("transition/catalogue occurrence identities changed")
    candidates = []
    for discoverer in _CLAUSE_DISCOVERERS:
        bindings = []
        for occurrence in sorted(grouped):
            binding = discoverer(grouped[occurrence], catalogues[occurrence])
            if binding is None:
                break
            bindings.append({"occurrence": occurrence, **binding})
        if len(bindings) != len(grouped):
            continue
        shapes = {
            canonical_json_bytes(_canonical_shape(binding)) for binding in bindings
        }
        if len(shapes) != 1:
            continue
        candidates.append(
            {
                "clause_set_sha256": __import__("hashlib").sha256(next(iter(shapes))).hexdigest(),
                "vm_schema": bindings[0]["vm_schema"],
                "legal_expression": bindings[0]["legal_expression"],
                "compiled_assignments": bindings[0]["compiled_assignments"],
                "occurrence_bindings": [
                    {
                        key: value
                        for key, value in binding.items()
                        if key
                        not in {
                            "legal_expression",
                            "compiled_assignments",
                        }
                    }
                    for binding in bindings
                ],
                "aggregate_residual_error_count": sum(
                    binding["residual_error_count"] for binding in bindings
                ),
                "aggregate_mdl_size": sum(binding["mdl_size"] for binding in bindings),
                "atomic_clause_evaluations": sum(
                    binding["atomic_clause_evaluations"] for binding in bindings
                ),
            }
        )
    if not candidates:
        _fail("no exact typed clause composition fits the raw transitions")
    score = min(
        (
            candidate["aggregate_residual_error_count"],
            candidate["aggregate_mdl_size"],
            candidate["clause_set_sha256"],
        )
        for candidate in candidates
    )
    selected = [
        candidate
        for candidate in candidates
        if (
            candidate["aggregate_residual_error_count"],
            candidate["aggregate_mdl_size"],
            candidate["clause_set_sha256"],
        )
        == score
    ]
    if len(selected) != 1:
        _fail("typed MDL clause selection is not unique")
    choice = selected[0]
    used = sorted(
        _expr_opcodes(
            [choice["legal_expression"], choice["compiled_assignments"]]
        )
    )
    if not set(used) <= GENERIC_OPCODE_NAMES_V3:
        _fail("compiled AST escaped the registered opcode grammar")
    payload = {
        "schema": "acfqp.generic_template_free_world_model.v3",
        "generic_types": list(GENERIC_TYPES_V3),
        "generic_opcode_registry": generic_opcode_documents_v3(),
        "whole_program_template_count": 0,
        "atomic_clause_schema_count": len(_CLAUSE_DISCOVERERS) * 4,
        "candidate_evaluations": candidates,
        "selection_rule": "MIN_EXACT_RESIDUAL_THEN_TYPED_AST_MDL_THEN_CONTENT_HASH",
        "selected_clause_set_sha256": choice["clause_set_sha256"],
        "vm_schema": choice["vm_schema"],
        "legal_expression": choice["legal_expression"],
        "compiled_assignments": choice["compiled_assignments"],
        "used_opcode_names": used,
        "unregistered_opcode_names": [],
        "occurrence_bindings": choice["occurrence_bindings"],
        "raw_transition_count": len(rows),
        "domain_name_available_to_synthesizer": False,
        "semantic_state_or_action_names_available_to_synthesizer": False,
        "status": "UNIQUE_TEMPLATE_FREE_TYPED_AST_SYNTHESIZED",
    }
    return {**payload, "program_id": content_id(program_domain, payload)}


def _binding_relation(binding: Mapping[str, Any], name: str) -> dict[int, Any]:
    rows = binding["relations"][name]
    return {row[0]: row[1] for row in rows}


def _evaluate_expression(
    expression: Any,
    *,
    current: Mapping[str, Any],
    next_values: Mapping[str, Any],
    action: RawActionV3,
    binding: Mapping[str, Any],
    relation_overlay: Mapping[int, int] | None,
) -> Any:
    if type(expression) in {int, bool}:
        return expression
    if type(expression) is not list or not expression:
        _fail("compiled expression shape changed")
    head = expression[0]
    if head == "Q":
        return current[expression[1]]
    if head == "NEXT":
        return next_values[expression[1]]
    if head == "A":
        return action.fields[binding["action_roles"][expression[1]]]
    if head == "N":
        return binding["numeric_literals"][expression[1]]
    if head == "REL":
        relation = _binding_relation(binding, expression[1])
        if expression[1] == "REL0" and relation_overlay:
            relation.update(relation_overlay)
        return relation
    args = [
        _evaluate_expression(
            item,
            current=current,
            next_values=next_values,
            action=action,
            binding=binding,
            relation_overlay=relation_overlay,
        )
        for item in expression[1:]
    ]
    if head == "O02":
        return args[0] + args[1]
    if head == "O03":
        return args[0] % args[1]
    if head == "O04":
        return args[0] | args[1]
    if head == "O05":
        return args[0] & args[1]
    if head == "O06":
        return args[0] == args[1]
    if head == "O07":
        return args[0] > args[1]
    if head == "O08":
        return bool(args[0] and args[1])
    if head == "O09":
        return args[1] if args[0] else args[2]
    if head == "O10":
        if args[1] not in args[0]:
            _fail("compiled relation is missing an action value")
        return args[0][args[1]]
    if head == "O11":
        return args[0][args[1]]
    if head == "O12":
        result = list(args[0])
        result[args[1]] = args[2]
        return tuple(result)
    if head == "O13":
        return sum(args[0])
    if head == "O14":
        return tuple(sorted(set(args)))
    if head == "O15":
        return args[1] & ~args[0]
    _fail("compiled expression used an unknown opcode")


def execute_compiled_program_v3(
    program: Mapping[str, Any],
    vm: tuple[Any, ...],
    action: RawActionV3,
    binding: Mapping[str, Any],
    *,
    relation_overlay: Mapping[int, int] | None = None,
    support_choice: str = "WORST",
) -> tuple[Any, ...]:
    schema = tuple(program["vm_schema"])
    if len(vm) != len(schema):
        _fail("VM register width changed")
    current = {f"Q{index}": value for index, value in enumerate(vm)}
    next_values: dict[str, Any] = {}
    for statement in program["compiled_assignments"]:
        target = statement["target"]
        value = _evaluate_expression(
            statement["expression"],
            current=current,
            next_values=next_values,
            action=action,
            binding=binding,
            relation_overlay=relation_overlay,
        )
        if type(value) is tuple and schema[int(target[1:])] != "INT_VECTOR":
            if support_choice == "LOW":
                value = min(value)
            elif support_choice == "WORST":
                value = max(value)
            else:
                _fail("finite support choice changed")
        next_values[target] = value
    return tuple(next_values[f"Q{index}"] for index in range(len(schema)))


def action_relation_value_v3(
    binding: Mapping[str, Any], action: RawActionV3
) -> int:
    role = binding["action_roles"].get("A2")
    if type(role) is not int:
        _fail("compiled program has no relation-bearing action field")
    return action.fields[role]


def initial_vm_from_vector_v3(
    binding: Mapping[str, Any], state_vector: tuple[int, ...]
) -> tuple[Any, ...]:
    schema = tuple(binding["vm_schema"])
    roles = binding["state_roles"]
    status_column = roles["R3"]
    active_tokens = set(binding["status_tokens"]["A"])
    if state_vector[status_column] not in active_tokens:
        _fail("target initial vector is not active")
    if schema == ("INT_SET", "INT_VECTOR", "STATUS"):
        return (
            state_vector[roles["R0"]],
            tuple(state_vector[column] for column in roles["R1"]),
            0,
        )
    if schema == ("INT", "INT", "STATUS_SUPPORT"):
        return (state_vector[roles["R0"]], state_vector[roles["R1"]], 0)
    if schema == ("INT", "INT", "INT", "STATUS"):
        return (
            state_vector[roles["R0"]],
            state_vector[roles["R1"]],
            state_vector[roles["R2"]],
            0,
        )
    _fail("unknown VM schema")


def _known_relation(
    binding: Mapping[str, Any], overlay: Mapping[int, int] | None
) -> dict[int, Any]:
    result = _binding_relation(binding, "REL0")
    if overlay:
        result.update(overlay)
    return result


def plan_compiled_program_v3(
    program: Mapping[str, Any],
    vm: tuple[Any, ...],
    catalogue_rows: tuple[RawActionV3, ...],
    binding: Mapping[str, Any],
    *,
    relation_overlay: Mapping[int, int] | None = None,
) -> tuple[tuple[int, ...], int, int]:
    schema = tuple(program["vm_schema"])
    roles = binding["action_roles"]
    evaluations = 0

    @lru_cache(maxsize=None)
    def solve(state: tuple[Any, ...]) -> tuple[int, ...] | None:
        nonlocal evaluations
        status = state[-1]
        if status == 2:
            return ()
        if status == 1:
            return None
        if schema == ("INT_SET", "INT_VECTOR", "STATUS"):
            removed = state[0]
            legal = [
                action
                for action in catalogue_rows
                if action.fields[roles["A0"]] & removed == 0
                and action.fields[roles["A1"]] & ~removed == 0
            ]
        else:
            legal = [
                action
                for action in catalogue_rows
                if action.fields[roles["A0"]] == state[0]
            ]
        relation = _known_relation(binding, relation_overlay)
        if schema == ("INT", "INT", "INT", "STATUS"):
            legal = [
                action
                for action in legal
                if action.fields[roles["A2"]] in relation
            ]
        ranked = []
        for action in legal:
            successor = execute_compiled_program_v3(
                program,
                state,
                action,
                binding,
                relation_overlay=relation_overlay,
            )
            evaluations += 1
            if schema == ("INT_SET", "INT_VECTOR", "STATUS"):
                score = (
                    successor[-1] == 1,
                    sum(successor[1]),
                    action.key,
                )
            else:
                score = (successor[-1] == 1, successor[1], action.key)
            ranked.append((score, action, successor))
        for _score, action, successor in sorted(ranked):
            suffix = solve(successor)
            if suffix is not None:
                return (action.key, *suffix)
        return None

    result = solve(vm)
    if result is None:
        _fail("compiled typed AST found no certified continuation")
    return result, evaluations, solve.cache_info().currsize


def derive_dependency_support_v3(
    program: Mapping[str, Any], *, support_domain: str
) -> dict[str, Any]:
    serialized = canonical_json_bytes(
        [program["legal_expression"], program["compiled_assignments"]]
    )
    tokens: set[str] = set()

    def visit(value: Any) -> None:
        if type(value) is list:
            if (
                len(value) == 2
                and type(value[0]) is str
                and value[0] in {"Q", "NEXT", "A", "N", "REL"}
            ):
                tokens.add(f"{value[0]}:{value[1]}")
            for item in value:
                visit(item)
        elif type(value) is dict:
            for item in value.values():
                visit(item)

    visit([program["legal_expression"], program["compiled_assignments"]])
    rows = [
        {
            "support_id": f"D{index:02d}",
            "anonymous_dependency": token,
            "byte_reference_count": serialized.count(token.split(":", 1)[1].encode("ascii")),
            "deletion_invalidates_compiled_ast": True,
        }
        for index, token in enumerate(sorted(tokens))
    ]
    payload = {
        "schema": "acfqp.generic_template_free_dependency_support.v3",
        "derivation_rule": "EXACT_COMPILED_AST_DEPENDENCY_DELETION",
        "support_rows": rows,
        "predeclared_semantic_support_names": [],
    }
    return {**payload, "support_signature_id": content_id(support_domain, payload)}


__all__ = (
    "GENERIC_OPCODES_V3",
    "GENERIC_OPCODE_NAMES_V3",
    "GENERIC_TYPES_V3",
    "GenericTemplateFreeWorldModelV3Error",
    "RawActionV3",
    "RawTransitionV3",
    "action_relation_value_v3",
    "derive_dependency_support_v3",
    "execute_compiled_program_v3",
    "generic_opcode_documents_v3",
    "initial_vm_from_vector_v3",
    "plan_compiled_program_v3",
    "synthesize_template_free_program_v3",
)
