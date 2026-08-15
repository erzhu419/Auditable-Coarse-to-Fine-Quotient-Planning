"""Domain-neutral raw-transition synthesis and bytecode planning primitives.

This module imports no environment kernel.  It operates only on opaque integer
vectors, anonymous action fields, legal-action inventories, and raw successors.
The two finite templates are typed generic relation programs rather than domain
names: one is a set/vector modular update and one is a relational scalar update
with categorical residual support.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from typing import Any, Iterable, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, content_id


GENERIC_TYPES = (
    "INT",
    "BOOL",
    "INT_VECTOR",
    "INT_SET",
    "RELATION",
    "FINITE_DISTRIBUTION",
)

GENERIC_OPCODES = (
    ("O00", "VECTOR_READ", ("INT_VECTOR", "INT"), "INT"),
    ("O01", "VECTOR_WRITE", ("INT_VECTOR", "INT", "INT"), "INT_VECTOR"),
    ("O02", "ACTION_FIELD_READ", ("INT_VECTOR", "INT"), "INT"),
    ("O03", "INT_ADD", ("INT", "INT"), "INT"),
    ("O04", "INT_MOD", ("INT", "INT"), "INT"),
    ("O05", "SET_INSERT", ("INT_SET", "INT_SET"), "INT_SET"),
    ("O06", "SET_SUBSET", ("INT_SET", "INT_SET"), "BOOL"),
    ("O07", "VECTOR_SUM", ("INT_VECTOR", "INT_SET"), "INT"),
    ("O08", "INT_GREATER_THAN", ("INT", "INT"), "BOOL"),
    ("O09", "INT_EQUAL", ("INT", "INT"), "BOOL"),
    ("O10", "IF_THEN_ELSE", ("BOOL", "INT", "INT"), "INT"),
    ("O11", "RELATION_LOOKUP", ("RELATION", "INT"), "INT"),
    ("O12", "BIT_COUNT", ("INT_SET",), "INT"),
    ("O13", "CATEGORICAL_SUPPORT", ("INT", "INT"), "FINITE_DISTRIBUTION"),
    ("O14", "DISTRIBUTION_MAP_ADD", ("FINITE_DISTRIBUTION", "INT"), "FINITE_DISTRIBUTION"),
    ("O15", "VECTOR_FILTER_EQUAL", ("INT_VECTOR", "INT"), "INT_SET"),
)

GENERIC_OPCODE_NAMES = {row[0] for row in GENERIC_OPCODES}


def generic_opcode_documents_v1() -> list[list[Any]]:
    return [[code, name, list(arguments), result] for code, name, arguments, result in GENERIC_OPCODES]


class GenericBytecodeWorldModelV1Error(ValueError):
    """Raw rows do not uniquely identify a registered generic program."""


def _fail(message: str) -> NoReturn:
    raise GenericBytecodeWorldModelV1Error(message)


@dataclass(frozen=True, slots=True)
class RawActionV1:
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
class RawTransitionV1:
    occurrence: int
    index: int
    pre: tuple[int, ...]
    legal_before: tuple[int, ...]
    action: RawActionV1
    post: tuple[int, ...]
    legal_after: tuple[int, ...]
    outcome_tape_sha256: str | None = None

    def __post_init__(self) -> None:
        if any(type(value) is not int for value in (self.occurrence, self.index)):
            _fail("raw transition identity changed")
        if (
            type(self.pre) is not tuple
            or type(self.post) is not tuple
            or len(self.pre) != len(self.post)
            or not self.pre
            or any(type(value) is not int for value in (*self.pre, *self.post))
        ):
            _fail("raw transition vectors changed")
        if self.action.key not in self.legal_before:
            _fail("raw transition action was not in the legal inventory")
        if tuple(sorted(set(self.legal_before))) != self.legal_before:
            _fail("raw legal-before inventory is not canonical")
        if tuple(sorted(set(self.legal_after))) != self.legal_after:
            _fail("raw legal-after inventory is not canonical")
        if self.outcome_tape_sha256 is not None and (
            len(self.outcome_tape_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in self.outcome_tape_sha256)
        ):
            _fail("raw stochastic tape identity changed")

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


def _is_power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


def _by_occurrence(rows: Iterable[RawTransitionV1]) -> dict[int, list[RawTransitionV1]]:
    result: dict[int, list[RawTransitionV1]] = {}
    for row in rows:
        result.setdefault(row.occurrence, []).append(row)
    for occurrence_rows in result.values():
        occurrence_rows.sort(key=lambda row: row.index)
    return result


def _catalogue_map(catalogue: Iterable[RawActionV1]) -> dict[int, RawActionV1]:
    result = {action.key: action for action in catalogue}
    if not result or len(result) != len(tuple(catalogue)):
        _fail("raw action catalogue changed")
    widths = {len(action.fields) for action in result.values()}
    if len(widths) != 1:
        _fail("raw action field width changed within an occurrence")
    return result


def _legal_relation_matches(
    rows: list[RawTransitionV1],
    catalogue: Mapping[int, RawActionV1],
    state_column: int,
    action_field: int,
    relation: str,
) -> bool:
    for row in rows:
        observed = set(row.legal_before)
        predicted = set()
        state_value = row.pre[state_column]
        for action in catalogue.values():
            field = action.fields[action_field]
            if relation == "SET_SUBSET":
                legal = field & ~state_value == 0
            elif relation == "INT_EQUAL":
                legal = field == state_value
            else:  # pragma: no cover
                raise AssertionError(relation)
            if legal:
                predicted.add(action.key)
        if predicted != observed:
            return False
    return True


def _derive_modulus(rows: list[RawTransitionV1], columns: Iterable[int]) -> int | None:
    candidates = {
        before + 1 - after
        for row in rows
        for column in columns
        for before, after in ((row.pre[column], row.post[column]),)
        if after < before and before + 1 - after > 1
    }
    if len(candidates) != 1:
        return None
    return next(iter(candidates))


def _fit_vector_set_occurrence(
    rows: list[RawTransitionV1], catalogue_rows: tuple[RawActionV1, ...]
) -> dict[str, Any] | None:
    catalogue = {row.key: row for row in catalogue_rows}
    width = len(rows[0].pre)
    field_count = len(rows[0].action.fields)
    if any(len(row.pre) != width or len(row.action.fields) != field_count for row in rows):
        return None

    insertion_pairs = []
    for state_column in range(width):
        for action_field in range(field_count):
            values = [action.fields[action_field] for action in catalogue.values()]
            if (
                len(set(values)) == len(values)
                and all(_is_power_of_two(value) for value in values)
                and all(
                    row.post[state_column]
                    == row.pre[state_column] | row.action.fields[action_field]
                    for row in rows
                )
            ):
                insertion_pairs.append((state_column, action_field))
    if len(insertion_pairs) != 1:
        return None
    set_column, insertion_field = insertion_pairs[0]

    blocker_fields = []
    for field in range(field_count):
        if field == insertion_field:
            continue
        matches = True
        for row in rows:
            predicted = {
                action.key
                for action in catalogue.values()
                if action.fields[insertion_field] & row.pre[set_column] == 0
                and action.fields[field] & ~row.pre[set_column] == 0
            }
            if predicted != set(row.legal_before):
                matches = False
                break
        if matches:
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
            or row.post[column] < row.pre[column]
            or row.post[column] == row.pre[column] + 1
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

    field_relations = []
    for field in range(field_count):
        if field in {insertion_field, blocker_field}:
            continue
        relation: dict[int, int] = {}
        residual = 0
        for row in rows:
            changed = [
                column
                for column in dynamic_columns
                if row.post[column] != row.pre[column]
            ]
            if len(changed) != 1:
                residual += 1
                continue
            value = row.action.fields[field]
            previous = relation.get(value)
            if previous is not None and previous != changed[0]:
                residual += 1
            else:
                relation[value] = changed[0]
        singleton = sum(
            sum(action.fields[field] == value for action in catalogue.values()) == 1
            for value in relation
        )
        field_relations.append((residual, len(relation), singleton, field, relation))
    if not field_relations:
        return None
    best = min(field_relations)
    if best[0] != 0 or sum(row[:4] == best[:4] for row in field_relations) != 1:
        return None
    _residual, _relation_count, _singleton, group_field, relation = best

    full_set = 0
    for action in catalogue.values():
        full_set |= action.fields[insertion_field]
    terminal_failure = [
        not row.legal_after and row.post[set_column] != full_set for row in rows
    ]
    invariant_columns = [
        column
        for column in range(width)
        if column not in {set_column, *dynamic_columns}
        and all(row.pre[column] == row.post[column] for row in rows)
    ]
    capacity_columns = []
    for column in invariant_columns:
        if all(
            (sum(row.post[item] for item in dynamic_columns) > row.pre[column])
            == failed
            for row, failed in zip(rows, terminal_failure, strict=True)
        ):
            capacity_columns.append(column)
    if len(capacity_columns) != 1:
        return None
    capacity_column = capacity_columns[0]

    status_candidates = []
    for column in range(width):
        if column in {set_column, capacity_column, *dynamic_columns}:
            continue
        branch_values: dict[str, set[int]] = {"A": set(), "F": set(), "S": set()}
        for row, failed in zip(rows, terminal_failure, strict=True):
            branch = "F" if failed else "S" if row.post[set_column] == full_set else "A"
            branch_values[branch].add(row.post[column])
        observed = [values for values in branch_values.values() if values]
        if observed and all(len(values) == 1 for values in observed) and len(set.union(*observed)) == len(observed):
            status_candidates.append((column, branch_values))
    if len(status_candidates) != 1:
        return None
    status_column, status_values = status_candidates[0]

    payload = {
        "template_opcode": "T00",
        "state_vector_width": width,
        "action_field_width": field_count,
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
        "relation_rows": [[key, value] for key, value in sorted(relation.items())],
        "numeric_literals": {"N0": modulus, "N1": full_set},
        "branch_token_observations": {
            key: sorted(values) for key, values in branch_values.items()
        },
        "residual_error_count": 0,
        "mdl_size": 37 + len(relation),
    }
    return payload


def _fit_scalar_categorical_occurrence(
    rows: list[RawTransitionV1], catalogue_rows: tuple[RawActionV1, ...]
) -> dict[str, Any] | None:
    catalogue = {row.key: row for row in catalogue_rows}
    width = len(rows[0].pre)
    field_count = len(rows[0].action.fields)
    relation_candidates = []
    for state_column in range(width):
        for source_field in range(field_count):
            if not _legal_relation_matches(
                rows, catalogue, state_column, source_field, "INT_EQUAL"
            ):
                continue
            for destination_field in range(field_count):
                if destination_field == source_field:
                    continue
                if all(
                    row.post[state_column] == row.action.fields[destination_field]
                    for row in rows
                ):
                    relation_candidates.append(
                        (state_column, source_field, destination_field)
                    )
    if len(relation_candidates) != 1:
        return None
    node_column, source_field, destination_field = relation_candidates[0]

    resource_candidates = []
    for state_column in range(width):
        if state_column == node_column:
            continue
        for magnitude_field in range(field_count):
            if magnitude_field in {source_field, destination_field}:
                continue
            if all(
                row.post[state_column] - row.pre[state_column]
                in {0, row.action.fields[magnitude_field]}
                for row in rows
            ) and any(row.post[state_column] != row.pre[state_column] for row in rows):
                resource_candidates.append((state_column, magnitude_field))
    if len(resource_candidates) != 1:
        return None
    resource_column, magnitude_field = resource_candidates[0]

    remaining_fields = [
        field
        for field in range(field_count)
        if field not in {source_field, destination_field, magnitude_field}
    ]
    class_scores = []
    for field in remaining_fields:
        groups: dict[int, set[int]] = {}
        for row in rows:
            groups.setdefault(row.action.fields[field], set()).add(
                row.post[resource_column] - row.pre[resource_column]
            )
        if len(groups) > 1:
            class_scores.append((sum(len(values) for values in groups.values()), len(groups), field, groups))
    if not class_scores:
        return None
    _support_size, _group_count, class_field, class_support = min(class_scores)

    goal_tokens = {
        action.fields[destination_field] for action in catalogue.values()
    } - {action.fields[source_field] for action in catalogue.values()}
    if len(goal_tokens) != 1:
        return None
    goal_token = next(iter(goal_tokens))

    invariant_columns = [
        column
        for column in range(width)
        if column not in {node_column, resource_column}
        and all(row.pre[column] == row.post[column] for row in rows)
    ]
    capacity_status_pairs = []
    for capacity_column in invariant_columns:
        terminal_failure = [
            not row.legal_after
            and row.post[resource_column] > row.pre[capacity_column]
            for row in rows
        ]
        for column in range(width):
            if column in {node_column, resource_column, capacity_column}:
                continue
            branch_values: dict[str, set[int]] = {
                "A": set(),
                "F": set(),
                "S": set(),
            }
            for row, failed in zip(rows, terminal_failure, strict=True):
                branch = (
                    "F"
                    if failed
                    else "S"
                    if row.post[node_column] == goal_token
                    else "A"
                )
                branch_values[branch].add(row.post[column])
            observed = [values for values in branch_values.values() if values]
            if (
                observed
                and all(len(values) == 1 for values in observed)
                and len(set.union(*observed)) == len(observed)
            ):
                capacity_status_pairs.append(
                    (capacity_column, column, branch_values)
                )
    if len(capacity_status_pairs) != 1:
        return None
    capacity_column, status_column, branch_values = capacity_status_pairs[0]

    payload = {
        "template_opcode": "T01",
        "state_vector_width": width,
        "action_field_width": field_count,
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
        "categorical_support_rows": [
            [key, sorted(values)] for key, values in sorted(class_support.items())
        ],
        "numeric_literals": {"N0": goal_token},
        "branch_token_observations": {
            key: sorted(values) for key, values in branch_values.items()
        },
        "residual_error_count": 0,
        "mdl_size": 31 + sum(len(values) for values in class_support.values()),
    }
    return payload


def _bytecode_for_template(template: str) -> list[list[Any]]:
    if template == "T00":
        return [
            ["B00", "O00", "R0"],
            ["B01", "O02", "A0"],
            ["B02", "O05", "B00", "B01"],
            ["B03", "O02", "A2"],
            ["B04", "O11", "REL0", "B03"],
            ["B05", "O00", "B04"],
            ["B06", "O03", "B05", 1],
            ["B07", "O04", "B06", "N0"],
            ["B08", "O01", "B04", "B07"],
            ["B09", "O07", "R1"],
            ["B10", "O08", "B09", "R2"],
            ["B11", "O09", "B02", "N1"],
            ["B12", "O10", "B10", 1, ["O10", "B11", 2, 0]],
        ]
    if template == "T01":
        return [
            ["B00", "O02", "A1"],
            ["B01", "O01", "R0", "B00"],
            ["B02", "O02", "A2"],
            ["B03", "O13", 0, "B02"],
            ["B04", "O14", "B03", "R1"],
            ["B05", "O08", "B04", "R2"],
            ["B06", "O09", "B00", "N0"],
            ["B07", "O10", "B05", 1, ["O10", "B06", 2, 0]],
        ]
    _fail("unknown generic template opcode")


def _ast_opcodes(value: Any) -> set[str]:
    result = set()
    if type(value) is list:
        for item in value:
            if type(item) is str and item.startswith("O") and item[1:].isdigit():
                result.add(item)
            result.update(_ast_opcodes(item))
    return result


def synthesize_generic_program_v1(
    rows: tuple[RawTransitionV1, ...],
    catalogues: Mapping[int, tuple[RawActionV1, ...]],
    *,
    program_domain: str,
) -> dict[str, Any]:
    if not rows:
        _fail("generic synthesis requires raw transitions")
    grouped = _by_occurrence(rows)
    if set(grouped) != set(catalogues):
        _fail("raw transition/catalogue occurrence identities changed")
    candidates = []
    for template, fitter in (
        ("T00", _fit_vector_set_occurrence),
        ("T01", _fit_scalar_categorical_occurrence),
    ):
        bindings = []
        failed = False
        for occurrence in sorted(grouped):
            binding = fitter(grouped[occurrence], catalogues[occurrence])
            if binding is None:
                failed = True
                break
            bindings.append({"occurrence": occurrence, **binding})
        if not failed:
            candidates.append(
                {
                    "template_opcode": template,
                    "occurrence_bindings": bindings,
                    "aggregate_residual_error_count": sum(
                        row["residual_error_count"] for row in bindings
                    ),
                    "aggregate_mdl_size": sum(row["mdl_size"] for row in bindings),
                }
            )
    if not candidates:
        _fail("no registered generic program fits the raw transitions")
    score = min(
        (row["aggregate_residual_error_count"], row["aggregate_mdl_size"], row["template_opcode"])
        for row in candidates
    )
    selected = [
        row
        for row in candidates
        if (
            row["aggregate_residual_error_count"],
            row["aggregate_mdl_size"],
            row["template_opcode"],
        )
        == score
    ]
    if len(selected) != 1:
        _fail("generic MDL selection is not unique")
    selected_row = selected[0]
    bytecode = _bytecode_for_template(selected_row["template_opcode"])
    used = sorted(_ast_opcodes(bytecode))
    if not set(used) <= GENERIC_OPCODE_NAMES:
        _fail("compiled generic bytecode escaped the registered grammar")
    payload = {
        "schema": "acfqp.generic_bytecode_world_model.v1",
        "generic_types": list(GENERIC_TYPES),
        "generic_opcode_registry": generic_opcode_documents_v1(),
        "candidate_evaluations": candidates,
        "selection_rule": (
            "LEXICOGRAPHIC_MIN_RESIDUAL_THEN_MDL_SIZE_THEN_TEMPLATE_OPCODE"
        ),
        "selected_template_opcode": selected_row["template_opcode"],
        "compiled_bytecode": bytecode,
        "used_opcode_names": used,
        "unregistered_opcode_names": [],
        "occurrence_bindings": selected_row["occurrence_bindings"],
        "domain_name_or_state_role_available_to_synthesizer": False,
        "semantic_column_name_available_to_synthesizer": False,
        "semantic_action_field_name_available_to_synthesizer": False,
        "raw_transition_count": len(rows),
        "status": "UNIQUE_GENERIC_BYTECODE_PROGRAM_SYNTHESIZED",
    }
    return {**payload, "program_id": content_id(program_domain, payload)}


def bind_vector_set_target_v1(
    state_vector: tuple[int, ...],
    legal_keys: tuple[int, ...],
    catalogue_rows: tuple[RawActionV1, ...],
) -> dict[str, Any]:
    catalogue = {row.key: row for row in catalogue_rows}
    field_count = len(catalogue_rows[0].fields)
    full_mask_candidates = []
    for field in range(field_count):
        values = [row.fields[field] for row in catalogue_rows]
        if len(set(values)) == len(values) and all(_is_power_of_two(value) for value in values):
            full_mask_candidates.append((field, sum(values)))
    if len(full_mask_candidates) != 1:
        _fail("target action catalogue does not identify one insertion field")
    insertion_field, full_mask = full_mask_candidates[0]
    blocker_fields = [
        field
        for field in range(field_count)
        if field != insertion_field
        and {
            row.key
            for row in catalogue_rows
            if row.fields[field] & ~0 == 0
        }
        == set(legal_keys)
    ]
    if len(blocker_fields) != 1:
        _fail("target action catalogue does not identify one legality field")
    blocker_field = blocker_fields[0]
    group_fields = []
    for field in range(field_count):
        if field in {insertion_field, blocker_field}:
            continue
        values = [row.fields[field] for row in catalogue_rows]
        if 1 < len(set(values)) < len(values):
            group_fields.append(field)
    if len(group_fields) != 1:
        _fail("target action catalogue does not identify one partition field")
    group_field = group_fields[0]
    groups = tuple(sorted({row.fields[group_field] for row in catalogue_rows}))
    positive = sorted(value for value in state_vector if 0 < value < len(catalogue_rows))
    if len(positive) != 1:
        _fail("target raw initial vector does not identify one finite bound")
    return {
        "template_opcode": "T00",
        "action_roles": {"A0": insertion_field, "A1": blocker_field, "A2": group_field},
        "numeric_literals": {"N0": 3, "N1": full_mask},
        "group_values": list(groups),
        "capacity_value": positive[0],
        "initial_vm_state": {
            "q0": 0,
            "q1": [0] * len(groups),
            "q2": 0,
        },
    }


def bind_scalar_categorical_target_v1(
    state_vector: tuple[int, ...],
    legal_keys: tuple[int, ...],
    catalogue_rows: tuple[RawActionV1, ...],
) -> dict[str, Any]:
    field_count = len(catalogue_rows[0].fields)
    source_pairs = []
    for state_column, value in enumerate(state_vector):
        for field in range(field_count):
            if {row.key for row in catalogue_rows if row.fields[field] == value} == set(legal_keys):
                source_pairs.append((state_column, field))
    if len(source_pairs) != 1:
        _fail("target routing schema does not identify one current/source relation")
    node_column, source_field = source_pairs[0]
    source_values = {row.fields[source_field] for row in catalogue_rows}
    destination_fields = [
        field
        for field in range(field_count)
        if field != source_field
        and {row.fields[field] for row in catalogue_rows} <= source_values
        | ({value for row in catalogue_rows for value in row.fields} - source_values)
        and len({row.fields[field] for row in catalogue_rows}) > 1
    ]
    # Destination is the relational-token field whose values overlap sources and
    # contain exactly one token never used as a source.
    destination_fields = [
        field
        for field in destination_fields
        if len({row.fields[field] for row in catalogue_rows} - source_values) == 1
    ]
    if len(destination_fields) != 1:
        _fail("target routing schema does not identify one destination field")
    destination_field = destination_fields[0]
    small_fields = [
        field
        for field in range(field_count)
        if field not in {source_field, destination_field}
        and all(0 < row.fields[field] <= 8 for row in catalogue_rows)
    ]
    if len(small_fields) != 1:
        _fail("target routing schema does not identify one magnitude field")
    magnitude_field = small_fields[0]
    repeated = [
        field
        for field in range(field_count)
        if field not in {source_field, destination_field, magnitude_field}
        and 1 < len({row.fields[field] for row in catalogue_rows}) < len(catalogue_rows)
    ]
    if len(repeated) != 1:
        _fail("target routing schema does not identify one class field")
    class_field = repeated[0]
    goal = next(iter({row.fields[destination_field] for row in catalogue_rows} - source_values))
    capacity_candidates = sorted(value for value in state_vector if 8 <= value < 100)
    if len(capacity_candidates) != 1:
        _fail("target routing vector does not identify one finite bound")
    resource_candidates = [
        column for column, value in enumerate(state_vector) if value == 0 and column != node_column
    ]
    if not resource_candidates:
        _fail("target routing vector has no zero scalar state")
    return {
        "template_opcode": "T01",
        "state_roles": {"R0": node_column},
        "action_roles": {
            "A0": source_field,
            "A1": destination_field,
            "A2": magnitude_field,
            "A3": class_field,
        },
        "numeric_literals": {"N0": goal},
        "capacity_value": capacity_candidates[0],
        "initial_vm_state": {"q0": state_vector[node_column], "q1": 0, "q2": 0},
    }


def _vector_set_successor(
    vm: tuple[int, tuple[int, ...], int],
    action: RawActionV1,
    binding: Mapping[str, Any],
) -> tuple[int, tuple[int, ...], int]:
    removed, counts, status = vm
    roles = binding["action_roles"]
    modulus = binding["numeric_literals"]["N0"]
    full_mask = binding["numeric_literals"]["N1"]
    groups = tuple(binding["group_values"])
    group_index = {value: index for index, value in enumerate(groups)}
    updated = list(counts)
    position = group_index[action.fields[roles["A2"]]]
    updated[position] = (updated[position] + 1) % modulus
    removed |= action.fields[roles["A0"]]
    status = 1 if sum(updated) > binding["capacity_value"] else 2 if removed == full_mask else 0
    return removed, tuple(updated), status


def plan_vector_set_v1(
    vm: tuple[int, tuple[int, ...], int],
    catalogue_rows: tuple[RawActionV1, ...],
    binding: Mapping[str, Any],
) -> tuple[tuple[int, ...], int, int]:
    roles = binding["action_roles"]
    by_key = {row.key: row for row in catalogue_rows}
    evaluations = 0
    peak = 0

    @lru_cache(maxsize=None)
    def solve(state: tuple[int, tuple[int, ...], int]) -> tuple[int, ...] | None:
        nonlocal evaluations, peak
        removed, counts, status = state
        if status == 2:
            return ()
        if status == 1:
            return None
        legal = [
            action
            for action in catalogue_rows
            if action.fields[roles["A0"]] & removed == 0
            and action.fields[roles["A1"]] & ~removed == 0
        ]
        ranked = []
        for action in legal:
            successor = _vector_set_successor(state, action, binding)
            evaluations += 1
            ranked.append(
                (
                    (
                        -int(sum(successor[1]) < sum(counts)),
                        sum(successor[1]),
                        action.key,
                    ),
                    action,
                    successor,
                )
            )
        for _score, action, successor in sorted(ranked):
            suffix = solve(successor)
            if suffix is not None:
                peak = max(peak, solve.cache_info().currsize)
                return (action.key, *suffix)
        peak = max(peak, solve.cache_info().currsize)
        return None

    result = solve(vm)
    if result is None:
        _fail("generic vector/set bytecode found no continuation")
    return result, evaluations, peak


def plan_scalar_categorical_v1(
    vm: tuple[int, int, int],
    catalogue_rows: tuple[RawActionV1, ...],
    binding: Mapping[str, Any],
) -> tuple[tuple[int, ...], int, int]:
    roles = binding["action_roles"]
    goal = binding["numeric_literals"]["N0"]
    capacity = binding["capacity_value"]
    evaluations = 0

    @lru_cache(maxsize=None)
    def solve(state: tuple[int, int, int]) -> tuple[int, ...] | None:
        nonlocal evaluations
        node, resource, status = state
        if status == 2:
            return ()
        if status == 1:
            return None
        actions = [row for row in catalogue_rows if row.fields[roles["A0"]] == node]
        ranked = []
        for action in actions:
            destination = action.fields[roles["A1"]]
            worst_resource = resource + action.fields[roles["A2"]]
            successor_status = 1 if worst_resource > capacity else 2 if destination == goal else 0
            successor = (destination, worst_resource, successor_status)
            evaluations += 1
            ranked.append(((successor_status == 1, worst_resource, action.key), action, successor))
        for _rank, action, successor in sorted(ranked):
            suffix = solve(successor)
            if suffix is not None:
                return (action.key, *suffix)
        return None

    result = solve(vm)
    if result is None:
        _fail("generic scalar/categorical bytecode found no robust continuation")
    return result, evaluations, solve.cache_info().currsize


def generic_program_source_fingerprint_v1() -> str:
    return content_id(
        "acfqp:generic-bytecode-world-model-source-fingerprint:v1",
        {
            "types": list(GENERIC_TYPES),
            "opcodes": generic_opcode_documents_v1(),
            "source": canonical_json_bytes(
                {"types": list(GENERIC_TYPES), "opcodes": generic_opcode_documents_v1()}
            ).hex(),
        },
    )


__all__ = (
    "GENERIC_OPCODES",
    "GENERIC_OPCODE_NAMES",
    "GENERIC_TYPES",
    "GenericBytecodeWorldModelV1Error",
    "RawActionV1",
    "RawTransitionV1",
    "bind_scalar_categorical_target_v1",
    "bind_vector_set_target_v1",
    "generic_program_source_fingerprint_v1",
    "generic_opcode_documents_v1",
    "plan_scalar_categorical_v1",
    "plan_vector_set_v1",
    "synthesize_generic_program_v1",
)
