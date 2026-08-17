"""Generic atomic-expression composition over opaque flat transitions.

The synthesizer enumerates expressions independently for every output column,
then composes the selected clauses.  It has no environment imports, named
state roles, complete program templates, or family-specific discoverers.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import hashlib
from itertools import combinations
from typing import Any, Iterable, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, content_id


GENERIC_ATOMIC_TYPES_V4 = (
    "INT",
    "BOOL",
    "FINITE_INT_SUPPORT",
    "RELATION_INT_INT",
)

GENERIC_ATOMIC_OPCODES_V4 = (
    ("E00", "STATE_COLUMN", ("INT",), "INT"),
    ("E01", "ACTION_FIELD", ("INT",), "INT"),
    ("E02", "NEXT_COLUMN", ("INT",), "INT"),
    ("E03", "OCCURRENCE_CONSTANT", ("INT",), "INT"),
    ("E04", "RELATION_LOOKUP", ("RELATION_INT_INT", "INT"), "INT"),
    ("E05", "INT_ADD", ("INT", "INT"), "INT"),
    ("E06", "INT_MOD", ("INT", "INT"), "INT"),
    ("E07", "FINITE_SUPPORT_PAIR", ("INT", "INT"), "FINITE_INT_SUPPORT"),
    ("E08", "INT_EQUAL", ("INT", "INT"), "BOOL"),
    ("E09", "INT_GREATER_THAN", ("INT", "INT"), "BOOL"),
    ("E10", "BOOL_AND", ("BOOL", "BOOL"), "BOOL"),
    ("E11", "BOOL_NOT", ("BOOL",), "BOOL"),
    ("E12", "IF_THEN_ELSE", ("BOOL", "INT", "INT"), "INT"),
    ("E13", "INT_BIT_OR", ("INT", "INT"), "INT"),
)

GENERIC_ATOMIC_OPCODE_NAMES_V4 = frozenset(
    row[0] for row in GENERIC_ATOMIC_OPCODES_V4
)

ATOMIC_COMPOSITION_MAX_DEPTH_V4 = 3
ATOMIC_COMPOSITION_BEAM_WIDTH_V4 = 32
TERMINAL_TREE_MAX_DEPTH_V4 = 3
TERMINAL_TREE_BEAM_WIDTH_V4 = 32


class GenericAtomicExpressionWorldModelV4Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericAtomicExpressionWorldModelV4Error(message)


@dataclass(frozen=True, slots=True)
class FlatRawActionV4:
    key: int
    fields: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.key) is not int or type(self.fields) is not tuple:
            _fail("flat raw action shape changed")
        if not self.fields or any(type(value) is not int for value in self.fields):
            _fail("flat raw action fields changed")

    def to_document(self) -> dict[str, Any]:
        return {"action_key": self.key, "anonymous_fields": list(self.fields)}


@dataclass(frozen=True, slots=True)
class FlatRawTransitionV4:
    occurrence: int
    index: int
    pre: tuple[int, ...]
    legal_before: tuple[int, ...]
    action: FlatRawActionV4
    post: tuple[int, ...]
    legal_after: tuple[int, ...]
    terminal_acceptance_after: bool | None
    outcome_tape_sha256: str | None = None

    def __post_init__(self) -> None:
        if type(self.occurrence) is not int or type(self.index) is not int:
            _fail("flat transition identity changed")
        if (
            type(self.pre) is not tuple
            or type(self.post) is not tuple
            or not self.pre
            or len(self.pre) != len(self.post)
            or any(type(value) is not int for value in (*self.pre, *self.post))
        ):
            _fail("flat transition vectors changed")
        if tuple(sorted(set(self.legal_before))) != self.legal_before:
            _fail("flat legal-before inventory changed")
        if tuple(sorted(set(self.legal_after))) != self.legal_after:
            _fail("flat legal-after inventory changed")
        if self.action.key not in self.legal_before:
            _fail("flat selected action was not legal")
        if self.legal_after and self.terminal_acceptance_after is not None:
            _fail("active successor carried a terminal acceptance label")
        if not self.legal_after and type(self.terminal_acceptance_after) is not bool:
            _fail("terminal successor omitted its anonymous acceptance bit")
        if self.outcome_tape_sha256 is not None and (
            type(self.outcome_tape_sha256) is not str
            or len(self.outcome_tape_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in self.outcome_tape_sha256)
        ):
            _fail("flat outcome tape identity changed")

    def to_document(self) -> dict[str, Any]:
        return {
            "occurrence": self.occurrence,
            "transition_index": self.index,
            "pre_vector": list(self.pre),
            "legal_action_keys_before": list(self.legal_before),
            "selected_action": self.action.to_document(),
            "post_vector": list(self.post),
            "legal_action_keys_after": list(self.legal_after),
            "terminal_acceptance_after": self.terminal_acceptance_after,
            "outcome_tape_sha256": self.outcome_tape_sha256,
        }


@dataclass(frozen=True, slots=True)
class _FiniteSupportV4:
    values: tuple[int, ...]


def generic_atomic_opcode_documents_v4() -> list[list[Any]]:
    return [
        [code, name, list(arguments), result]
        for code, name, arguments, result in GENERIC_ATOMIC_OPCODES_V4
    ]


def _grouped(
    rows: Iterable[FlatRawTransitionV4],
) -> dict[int, tuple[FlatRawTransitionV4, ...]]:
    result: dict[int, list[FlatRawTransitionV4]] = {}
    for row in rows:
        result.setdefault(row.occurrence, []).append(row)
    frozen = {}
    for occurrence, occurrence_rows in result.items():
        occurrence_rows.sort(key=lambda row: row.index)
        if [row.index for row in occurrence_rows] != list(range(len(occurrence_rows))):
            _fail("flat transition sequence changed")
        frozen[occurrence] = tuple(occurrence_rows)
    return frozen


def _catalogue(rows: tuple[FlatRawActionV4, ...]) -> dict[int, FlatRawActionV4]:
    result = {row.key: row for row in rows}
    if not result or len(result) != len(rows):
        _fail("flat action catalogue keys changed")
    if len({len(row.fields) for row in rows}) != 1:
        _fail("flat action field width changed")
    return result


def _relation_names(expression: Any) -> set[str]:
    result: set[str] = set()
    if type(expression) is list:
        if len(expression) >= 2 and expression[0] == "E04":
            result.add(expression[1])
        for item in expression:
            result.update(_relation_names(item))
    return result


def _used_opcodes(expression: Any) -> set[str]:
    result: set[str] = set()
    if type(expression) is list:
        if (
            expression
            and type(expression[0]) is str
            and expression[0] in GENERIC_ATOMIC_OPCODE_NAMES_V4
        ):
            result.add(expression[0])
        for item in expression:
            result.update(_used_opcodes(item))
    return result


def _binding_relation(binding: Mapping[str, Any], name: str) -> dict[int, int]:
    return {key: value for key, value in binding["relations"].get(name, [])}


def _evaluate(
    expression: Any,
    *,
    state: tuple[int, ...],
    next_values: Mapping[int, int],
    action: FlatRawActionV4,
    binding: Mapping[str, Any],
    relation_overlay: Mapping[str, Mapping[int, int]] | None = None,
) -> int | bool | _FiniteSupportV4:
    if type(expression) in {int, bool}:
        return expression
    if type(expression) is not list or not expression:
        _fail("atomic expression shape changed")
    head = expression[0]
    if head == "E00":
        return state[expression[1]]
    if head == "E01":
        return action.fields[expression[1]]
    if head == "E02":
        if expression[1] not in next_values:
            _fail("atomic expression referenced an unavailable next column")
        return next_values[expression[1]]
    if head == "E03":
        return binding["constants"][expression[1]]
    if head == "T":
        return binding["terminal_tokens"][expression[1]]
    if head == "E04":
        relation = _binding_relation(binding, expression[1])
        if relation_overlay and expression[1] in relation_overlay:
            relation.update(relation_overlay[expression[1]])
        key = _evaluate(
            expression[2],
            state=state,
            next_values=next_values,
            action=action,
            binding=binding,
            relation_overlay=relation_overlay,
        )
        if type(key) is not int or key not in relation:
            _fail(f"atomic relation {expression[1]} is missing value {key}")
        return relation[key]
    args = [
        _evaluate(
            item,
            state=state,
            next_values=next_values,
            action=action,
            binding=binding,
            relation_overlay=relation_overlay,
        )
        for item in expression[1:]
    ]
    if any(isinstance(value, _FiniteSupportV4) for value in args):
        _fail("finite support escaped its registered expression boundary")
    if head == "E05":
        return int(args[0]) + int(args[1])
    if head == "E06":
        return int(args[0]) % int(args[1])
    if head == "E07":
        return _FiniteSupportV4(tuple(sorted({int(args[0]), int(args[1])})))
    if head == "E08":
        return args[0] == args[1]
    if head == "E09":
        return int(args[0]) > int(args[1])
    if head == "E10":
        return bool(args[0] and args[1])
    if head == "E11":
        return not bool(args[0])
    if head == "E12":
        return int(args[1]) if bool(args[0]) else int(args[2])
    if head == "E13":
        return int(args[0]) | int(args[1])
    _fail("atomic expression used an unregistered opcode")


def _derive_binding(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue_rows: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    width = len(rows[0].pre)
    field_width = len(catalogue_rows[0].fields)
    if any(len(row.pre) != width for row in rows):
        _fail("flat state width changed inside occurrence")
    constants = {
        f"C{column}": rows[0].pre[column]
        for column in range(width)
        if all(
            row.pre[column] == rows[0].pre[column]
            and row.post[column] == rows[0].pre[column]
            for row in rows
        )
    }
    relations: dict[str, list[list[int]]] = {}
    for target_column in range(width):
        for action_field in range(field_width):
            field_values = {
                action.fields[action_field] for action in catalogue_rows
            }
            # A one-value-per-action identifier is a memorization key, not a
            # reusable relation variable.  This generic cardinality rule is
            # independent of every domain and semantic field name.
            if len(field_values) == len(catalogue_rows):
                continue
            for constant_name, modulus in constants.items():
                if modulus < 3:
                    continue
                groups: dict[int, set[int]] = {}
                for row in rows:
                    groups.setdefault(row.action.fields[action_field], set()).add(
                        (row.post[target_column] - row.pre[target_column]) % modulus
                    )
                if (
                    len(groups) >= 2
                    and all(len(values) == 1 for values in groups.values())
                    and len({next(iter(values)) for values in groups.values()}) >= 2
                    and all(next(iter(values)) != 0 for values in groups.values())
                ):
                    name = f"R{target_column}_{action_field}_{constant_name[1:]}"
                    relations[name] = [
                        [key, next(iter(values))]
                        for key, values in sorted(groups.items())
                    ]
    status_candidates = []
    for column in range(width):
        active = {
            row.post[column] for row in rows if row.terminal_acceptance_after is None
        }
        success = {
            row.post[column] for row in rows if row.terminal_acceptance_after is True
        }
        failure = {
            row.post[column] for row in rows if row.terminal_acceptance_after is False
        }
        if all(len(values) == 1 for values in (active, success, failure)):
            tokens = {
                "A": next(iter(active)),
                "S": next(iter(success)),
                "F": next(iter(failure)),
            }
            if len(set(tokens.values())) == 3:
                status_candidates.append((column, tokens))
    if len(status_candidates) != 1:
        _fail("anonymous terminal token column is not unique")
    status_column, terminal_tokens = status_candidates[0]
    return {
        "state_width": width,
        "action_field_width": field_width,
        "constants": constants,
        "relations": relations,
        "status_column": status_column,
        "terminal_tokens": terminal_tokens,
    }


def _atomic_expression_candidates(
    target_column: int,
    *,
    grouped: Mapping[int, tuple[FlatRawTransitionV4, ...]],
    bindings: Mapping[int, Mapping[str, Any]],
    state_width: int,
    action_field_width: int,
    relation_names: Iterable[str],
    constant_names: Iterable[str],
) -> tuple[list[tuple[int, str, Any]], int]:
    """Enumerate typed expressions without a complete-program shape.

    The only search restrictions are the registered atomic grammar, maximum
    composition depth, and a residual/MDL beam.  Relation lookups are crossed
    with every anonymous action field; no relation name is decoded to recover a
    target column or a privileged field.
    """

    observations = tuple(
        (occurrence, row)
        for occurrence, rows in sorted(grouped.items())
        for row in rows
    )
    evaluation_count = 0

    def signature(expression: Any, result_type: str) -> tuple[Any, ...] | None:
        nonlocal evaluation_count
        values: list[Any] = []
        for occurrence, row in observations:
            try:
                value = _evaluate(
                    expression,
                    state=row.pre,
                    next_values={},
                    action=row.action,
                    binding=bindings[occurrence],
                )
            except (GenericAtomicExpressionWorldModelV4Error, ZeroDivisionError):
                return None
            evaluation_count += 1
            if result_type == "INT":
                if type(value) is not int:
                    return None
                values.append(value)
            elif result_type == "FINITE_INT_SUPPORT":
                if not isinstance(value, _FiniteSupportV4):
                    return None
                values.append(value.values)
            else:  # pragma: no cover - internal registration invariant
                raise AssertionError(result_type)
        return tuple(values)

    target_values = tuple(row.post[target_column] for _, row in observations)

    def residual(result_type: str, values: tuple[Any, ...]) -> int:
        if result_type == "INT":
            return sum(value != target for value, target in zip(values, target_values, strict=True))
        return sum(target not in value for value, target in zip(values, target_values, strict=True))

    retained: dict[str, dict[tuple[Any, ...], tuple[int, int, bytes, Any]]] = {
        "INT": {},
        "FINITE_INT_SUPPORT": {},
    }
    frontier: dict[str, list[Any]] = {"INT": [], "FINITE_INT_SUPPORT": []}

    def register(expression: Any, result_type: str, depth: int) -> None:
        values = signature(expression, result_type)
        if values is None:
            return
        encoded = canonical_json_bytes(expression)
        score = (
            residual(result_type, values),
            _expression_mdl(expression, bindings),
            encoded,
            expression,
        )
        incumbent = retained[result_type].get(values)
        if incumbent is None or score[:3] < incumbent[:3]:
            retained[result_type][values] = score
            frontier[result_type].append(expression)

    atoms: list[Any] = [0, 1]
    atoms.extend(["E00", column] for column in range(state_width))
    atoms.extend(["E01", field] for field in range(action_field_width))
    atoms.extend(["E03", name] for name in sorted(constant_names))
    atoms.extend(
        ["E04", name, ["E01", field]]
        for name in sorted(relation_names)
        for field in range(action_field_width)
    )
    for expression in atoms:
        register(expression, "INT", 0)
    atom_pool = tuple(frontier["INT"])

    def exact_rows(depth: int) -> list[tuple[int, str, Any]]:
        rows: list[tuple[int, str, Any]] = []
        for result_type, inventory in retained.items():
            for score in inventory.values():
                if score[0] == 0:
                    rows.append((depth, result_type, score[3]))
        return rows

    exact = exact_rows(0)
    if exact:
        return exact, evaluation_count

    for depth in range(1, ATOMIC_COMPOSITION_MAX_DEPTH_V4 + 1):
        ranked_ints = sorted(
            retained["INT"].values(), key=lambda row: row[:3]
        )[:ATOMIC_COMPOSITION_BEAM_WIDTH_V4]
        int_pool_by_bytes = {
            canonical_json_bytes(expression): expression for expression in atom_pool
        }
        int_pool_by_bytes.update(
            (canonical_json_bytes(row[3]), row[3]) for row in ranked_ints
        )
        int_pool = list(int_pool_by_bytes.values())
        previous_frontier = tuple(frontier["INT"])
        frontier = {"INT": [], "FINITE_INT_SUPPORT": []}
        previous_keys = {canonical_json_bytes(row) for row in previous_frontier}
        for left in int_pool:
            left_key = canonical_json_bytes(left)
            for right in int_pool:
                right_key = canonical_json_bytes(right)
                if left_key not in previous_keys and right_key not in previous_keys:
                    continue
                if left_key <= right_key:
                    register(["E05", left, right], "INT", depth)
                    register(["E13", left, right], "INT", depth)
                    register(["E07", left, right], "FINITE_INT_SUPPORT", depth)
                register(["E06", left, right], "INT", depth)
        exact = exact_rows(depth)
        if exact:
            return exact, evaluation_count
        if not frontier["INT"] and not frontier["FINITE_INT_SUPPORT"]:
            break
    return [], evaluation_count


def _expression_mdl(expression: Any, bindings: Mapping[int, Mapping[str, Any]]) -> int:
    relation_cost = sum(
        len(_binding_relation(binding, name))
        for name in _relation_names(expression)
        for binding in bindings.values()
    )
    return len(canonical_json_bytes(expression)) + relation_cost


def _residual(
    expression: Any,
    target_column: int,
    grouped: Mapping[int, tuple[FlatRawTransitionV4, ...]],
    bindings: Mapping[int, Mapping[str, Any]],
) -> int:
    result = 0
    for occurrence, rows in grouped.items():
        binding = bindings[occurrence]
        for row in rows:
            try:
                predicted = _evaluate(
                    expression,
                    state=row.pre,
                    next_values={},
                    action=row.action,
                    binding=binding,
                )
            except GenericAtomicExpressionWorldModelV4Error:
                result += 1
                continue
            if isinstance(predicted, _FiniteSupportV4):
                result += int(row.post[target_column] not in predicted.values)
            else:
                result += int(predicted != row.post[target_column])
    return result


def _predicate_candidates(state_width: int) -> list[Any]:
    atoms = []
    for next_column in range(state_width):
        for state_column in range(state_width):
            atoms.append(["E08", ["E02", next_column], ["E00", state_column]])
            atoms.append(["E09", ["E02", next_column], ["E00", state_column]])
    unique = {canonical_json_bytes(row): row for row in atoms}
    return [unique[key] for key in sorted(unique)]


def _status_tree(
    status_column: int,
    grouped: Mapping[int, tuple[FlatRawTransitionV4, ...]],
    bindings: Mapping[int, Mapping[str, Any]],
) -> tuple[Any, int, int]:
    observations: list[tuple[int, FlatRawTransitionV4, str]] = []
    for occurrence, rows in sorted(grouped.items()):
        for row in rows:
            label = (
                "A"
                if row.terminal_acceptance_after is None
                else "S"
                if row.terminal_acceptance_after
                else "F"
            )
            observations.append((occurrence, row, label))
    raw_predicates = _predicate_candidates(len(observations[0][1].pre))
    atomic_signatures: dict[tuple[bool, ...], Any] = {}
    evaluations = 0
    for predicate in raw_predicates:
        values = []
        valid = True
        for occurrence, row, _label in observations:
            try:
                value = _evaluate(
                    predicate,
                    state=row.pre,
                    next_values={index: item for index, item in enumerate(row.post)},
                    action=row.action,
                    binding=bindings[occurrence],
                )
            except GenericAtomicExpressionWorldModelV4Error:
                valid = False
                break
            values.append(bool(value))
            evaluations += 1
        if not valid or all(values) or not any(values):
            continue
        signature = tuple(values)
        incumbent = atomic_signatures.get(signature)
        if incumbent is None or (
            len(canonical_json_bytes(predicate)), canonical_json_bytes(predicate)
        ) < (
            len(canonical_json_bytes(incumbent)), canonical_json_bytes(incumbent)
        ):
            atomic_signatures[signature] = predicate
    signatures = dict(atomic_signatures)

    def retain(signature: tuple[bool, ...], expression: Any) -> None:
        if all(signature) or not any(signature):
            return
        incumbent = signatures.get(signature)
        if incumbent is None or (
            len(canonical_json_bytes(expression)), canonical_json_bytes(expression)
        ) < (
            len(canonical_json_bytes(incumbent)), canonical_json_bytes(incumbent)
        ):
            signatures[signature] = expression

    atomic_rows = list(atomic_signatures.items())
    for signature, predicate in atomic_rows:
        retain(tuple(not value for value in signature), ["E11", predicate])
    for (left_signature, left), (right_signature, right) in combinations(
        atomic_rows, 2
    ):
        retain(
            tuple(a and b for a, b in zip(left_signature, right_signature, strict=True)),
            ["E10", left, right],
        )
    predicates = list(signatures.items())
    labels = tuple(row[2] for row in observations)

    @lru_cache(maxsize=None)
    def solve(indices: tuple[int, ...], depth: int) -> Any | None:
        selected_labels = {labels[index] for index in indices}
        if len(selected_labels) == 1:
            return ["T", next(iter(selected_labels))]
        if depth == 0:
            return None
        ranked_splits = []
        for signature, predicate in predicates:
            truth = tuple(index for index in indices if signature[index])
            falsehood = tuple(index for index in indices if not signature[index])
            if not truth or not falsehood:
                continue
            impurity = 0
            for branch in (truth, falsehood):
                counts = Counter(labels[index] for index in branch)
                impurity += len(branch) - max(counts.values())
            encoded = canonical_json_bytes(predicate)
            ranked_splits.append(
                (impurity, abs(len(truth) - len(falsehood)), len(encoded), encoded, predicate, truth, falsehood)
            )
        # This is an explicit generic search cap, not a family pattern: every
        # retained tree must still have zero residual on every observation.
        for _score, _balance, _size, _encoded, predicate, truth, falsehood in sorted(
            ranked_splits
        )[:TERMINAL_TREE_BEAM_WIDTH_V4]:
            left = solve(truth, depth - 1)
            if left is None:
                continue
            right = solve(falsehood, depth - 1)
            if right is None:
                continue
            return ["E12", predicate, left, right]
        return None

    expression = solve(
        tuple(range(len(observations))), TERMINAL_TREE_MAX_DEPTH_V4
    )
    if expression is None:
        _fail("generic depth-three terminal decision tree was not exact")
    for occurrence, row, _label in observations:
        predicted = _evaluate(
            expression,
            state=row.pre,
            next_values={index: item for index, item in enumerate(row.post)},
            action=row.action,
            binding=bindings[occurrence],
        )
        if predicted != row.post[status_column]:
            _fail("generic terminal tree residual changed")
    return expression, len(raw_predicates) + len(signatures), evaluations


def _legal_expression(
    grouped: Mapping[int, tuple[FlatRawTransitionV4, ...]],
    catalogues: Mapping[int, tuple[FlatRawActionV4, ...]],
    bindings: Mapping[int, Mapping[str, Any]],
) -> tuple[Any, int]:
    first_row = next(iter(next(iter(grouped.values()))))
    state_width = len(first_row.pre)
    field_width = len(first_row.action.fields)
    candidates = [
        ["E08", ["E00", column], ["E01", field]]
        for column in range(state_width)
        for field in range(field_width)
    ]
    exact = []
    evaluations = 0
    for expression in candidates:
        residual = 0
        for occurrence, rows in grouped.items():
            binding = bindings[occurrence]
            catalogue = catalogues[occurrence]
            for row in rows:
                predicted = {
                    action.key
                    for action in catalogue
                    if bool(
                        _evaluate(
                            expression,
                            state=row.pre,
                            next_values={},
                            action=action,
                            binding=binding,
                        )
                    )
                }
                residual += len(predicted ^ set(row.legal_before))
                evaluations += len(catalogue)
        if residual == 0:
            exact.append(
                (len(canonical_json_bytes(expression)), canonical_json_bytes(expression), expression)
            )
    if not exact:
        _fail("no exact generic legality expression was found")
    return min(exact)[2], evaluations


def synthesize_generic_atomic_program_v4(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogues: Mapping[int, tuple[FlatRawActionV4, ...]],
    *,
    program_domain: str,
) -> dict[str, Any]:
    if not rows:
        _fail("generic atomic synthesis requires observations")
    grouped = _grouped(rows)
    if set(grouped) != set(catalogues):
        _fail("generic atomic occurrence inventory changed")
    for catalogue in catalogues.values():
        _catalogue(catalogue)
    widths = {len(row.pre) for occurrence in grouped.values() for row in occurrence}
    field_widths = {
        len(action.fields) for catalogue in catalogues.values() for action in catalogue
    }
    if len(widths) != 1 or len(field_widths) != 1:
        _fail("generic atomic layout width changed across occurrences")
    state_width = next(iter(widths))
    action_field_width = next(iter(field_widths))
    bindings = {
        occurrence: _derive_binding(grouped[occurrence], catalogues[occurrence])
        for occurrence in sorted(grouped)
    }
    status_columns = {binding["status_column"] for binding in bindings.values()}
    if len(status_columns) != 1:
        _fail("generic atomic status projection changed across occurrences")
    status_column = next(iter(status_columns))
    common_relations = set.intersection(
        *(set(binding["relations"]) for binding in bindings.values())
    )
    common_constants = set.intersection(
        *(set(binding["constants"]) for binding in bindings.values())
    )
    assignments = []
    candidate_evaluations = []
    atomic_evaluations = 0
    for target_column in range(state_width):
        if target_column == status_column:
            continue
        exact_candidates, evaluations = _atomic_expression_candidates(
            target_column,
            grouped=grouped,
            bindings=bindings,
            state_width=state_width,
            action_field_width=action_field_width,
            relation_names=common_relations,
            constant_names=common_constants,
        )
        scored = []
        for depth, result_type, expression in exact_candidates:
            residual = _residual(expression, target_column, grouped, bindings)
            mdl = _expression_mdl(expression, bindings)
            digest = hashlib.sha256(canonical_json_bytes(expression)).hexdigest()
            scored.append((residual, depth, mdl, digest, result_type, expression))
        atomic_evaluations += evaluations
        if not scored:
            _fail(f"no exact atomic expression fit output column {target_column}")
        score = min((row[0], row[1], row[2], row[3]) for row in scored)
        if score[0] != 0:
            _fail(f"no exact atomic expression fit output column {target_column}")
        selected = next(row for row in scored if row[:4] == score)
        assignments.append(
            {
                "target_column": target_column,
                "result_type": selected[4],
                "composition_depth": selected[1],
                "expression": selected[5],
            }
        )
        candidate_evaluations.append(
            {
                "target_column": target_column,
                "exact_candidate_count": len(exact_candidates),
                "minimum_residual_error_count": score[0],
                "selected_composition_depth": score[1],
                "selected_mdl_size": score[2],
                "selected_expression_sha256": score[3],
            }
        )
    status_expression, predicate_count, status_evaluations = _status_tree(
        status_column, grouped, bindings
    )
    assignments.append(
        {
            "target_column": status_column,
            "result_type": "INT",
            "composition_depth": TERMINAL_TREE_MAX_DEPTH_V4,
            "expression": status_expression,
        }
    )
    assignments.sort(key=lambda row: row["target_column"] == status_column)
    candidate_evaluations.append(
        {
            "target_column": status_column,
            "exact_candidate_count": 1,
            "predicate_candidate_count": predicate_count,
            "minimum_residual_error_count": 0,
            "selected_composition_depth": TERMINAL_TREE_MAX_DEPTH_V4,
            "selected_mdl_size": len(canonical_json_bytes(status_expression)),
            "selected_expression_sha256": hashlib.sha256(
                canonical_json_bytes(status_expression)
            ).hexdigest(),
        }
    )
    legal_expression, legal_evaluations = _legal_expression(
        grouped, catalogues, bindings
    )
    accept_expression = ["E08", ["E00", status_column], ["T", "S"]]
    expressions = [
        legal_expression,
        accept_expression,
        *[row["expression"] for row in assignments],
    ]
    used_opcodes = sorted(_used_opcodes(expressions))
    if not set(used_opcodes) <= GENERIC_ATOMIC_OPCODE_NAMES_V4:
        _fail("generic atomic program escaped its opcode registry")
    normalized_bindings = [
        {"occurrence": occurrence, **bindings[occurrence]}
        for occurrence in sorted(bindings)
    ]
    payload = {
        "schema": "acfqp.generic_atomic_expression_world_model.v4",
        "generic_types": list(GENERIC_ATOMIC_TYPES_V4),
        "generic_opcode_registry": generic_atomic_opcode_documents_v4(),
        "whole_program_template_count": 0,
        "specialized_discovery_pattern_count": 0,
        "selection_rule": "PER_OUTPUT_MIN_EXACT_RESIDUAL_THEN_COMPOSITION_DEPTH_THEN_AST_MDL_THEN_CONTENT_HASH",
        "atomic_composition_max_depth": ATOMIC_COMPOSITION_MAX_DEPTH_V4,
        "atomic_composition_beam_width": ATOMIC_COMPOSITION_BEAM_WIDTH_V4,
        "terminal_tree_max_depth": TERMINAL_TREE_MAX_DEPTH_V4,
        "terminal_tree_beam_width": TERMINAL_TREE_BEAM_WIDTH_V4,
        "state_width": state_width,
        "action_field_width": action_field_width,
        "legal_expression": legal_expression,
        "accept_expression": accept_expression,
        "compiled_assignments": assignments,
        "candidate_evaluations": candidate_evaluations,
        "atomic_expression_evaluations": atomic_evaluations
        + status_evaluations
        + legal_evaluations,
        "used_opcode_names": used_opcodes,
        "unregistered_opcode_names": [],
        "occurrence_bindings": normalized_bindings,
        "raw_transition_count": len(rows),
        "domain_name_available_to_synthesizer": False,
        "semantic_state_or_action_names_available_to_synthesizer": False,
        "status": "GENERIC_ATOMIC_EXPRESSIONS_COMPOSED_WITHOUT_FAMILY_PATTERN",
    }
    return {**payload, "program_id": content_id(program_domain, payload)}


def _dependency_tokens(expression: Any) -> set[tuple[str, int | str]]:
    result: set[tuple[str, int | str]] = set()
    if type(expression) is not list:
        return result
    if len(expression) >= 2 and expression[0] in {"E00", "E01", "E02"}:
        result.add((expression[0], expression[1]))
    elif len(expression) >= 2 and expression[0] in {"E03", "E04", "T"}:
        result.add((expression[0], expression[1]))
    for item in expression:
        result.update(_dependency_tokens(item))
    return result


def _delete_dependency(
    expression: Any, dependency: tuple[str, int | str]
) -> Any:
    if type(expression) is not list:
        return expression
    if len(expression) >= 2 and expression[0] == dependency[0] and expression[1] == dependency[1]:
        return 0
    return [_delete_dependency(item, dependency) for item in expression]


def derive_atomic_dependency_support_v4(
    program: Mapping[str, Any],
    rows: tuple[FlatRawTransitionV4, ...],
    catalogues: Mapping[int, tuple[FlatRawActionV4, ...]],
    *,
    support_domain: str,
) -> dict[str, Any]:
    """Derive a minimal observed support signature by exact leaf deletion."""

    grouped = _grouped(rows)
    bindings = {
        row["occurrence"]: row for row in program["occurrence_bindings"]
    }
    if set(grouped) != set(bindings) or set(grouped) != set(catalogues):
        _fail("dependency-support occurrence inventory changed")
    expressions = [
        program["legal_expression"],
        program["accept_expression"],
        *[row["expression"] for row in program["compiled_assignments"]],
    ]
    dependencies = sorted(
        set().union(*(_dependency_tokens(expression) for expression in expressions))
    )

    def replay(candidate: Mapping[str, Any]) -> bool:
        by_occurrence = {
            occurrence: _catalogue(catalogue)
            for occurrence, catalogue in catalogues.items()
        }
        for occurrence, occurrence_rows in grouped.items():
            binding = bindings[occurrence]
            catalogue = catalogues[occurrence]
            by_key = by_occurrence[occurrence]
            for row in occurrence_rows:
                try:
                    if legal_action_keys_v4(candidate, row.pre, catalogue, binding) != row.legal_before:
                        return False
                    if row.post not in execute_generic_atomic_support_v4(
                        candidate, row.pre, by_key[row.action.key], binding
                    ):
                        return False
                    if is_accepting_state_v4(candidate, row.post, binding) != (
                        row.terminal_acceptance_after is True
                    ):
                        return False
                except (GenericAtomicExpressionWorldModelV4Error, KeyError, TypeError, ZeroDivisionError):
                    return False
        return True

    retained = []
    deletion_rows = []
    for opcode, value in dependencies:
        candidate = {
            **program,
            "legal_expression": _delete_dependency(
                program["legal_expression"], (opcode, value)
            ),
            "accept_expression": _delete_dependency(
                program["accept_expression"], (opcode, value)
            ),
            "compiled_assignments": [
                {
                    **row,
                    "expression": _delete_dependency(
                        row["expression"], (opcode, value)
                    ),
                }
                for row in program["compiled_assignments"]
            ],
        }
        deletion_preserves_replay = replay(candidate)
        deletion_rows.append(
            {
                "anonymous_dependency_opcode": opcode,
                "anonymous_dependency_value": value,
                "deletion_preserves_exact_observed_replay": deletion_preserves_replay,
            }
        )
        if not deletion_preserves_replay:
            retained.append([opcode, value])
    payload = {
        "schema": "acfqp.generic_atomic_dependency_support.v4",
        "program_id": program["program_id"],
        "derivation_rule": "EXACT_COMPILED_LEAF_SINGLE_DELETION_ON_ALL_RAW_TRANSITIONS",
        "predeclared_semantic_support_names": [],
        "candidate_dependency_count": len(dependencies),
        "minimal_observed_dependency_signature": retained,
        "deletion_trials": deletion_rows,
        "all_retained_dependencies_failed_single_deletion": all(
            not row["deletion_preserves_exact_observed_replay"]
            for row in deletion_rows
            if [
                row["anonymous_dependency_opcode"],
                row["anonymous_dependency_value"],
            ]
            in retained
        ),
    }
    return {**payload, "dependency_support_id": content_id(support_domain, payload)}


def target_binding_from_initial_vector_v4(
    program: Mapping[str, Any],
    initial_vector: tuple[int, ...],
    *,
    base_relations: Mapping[str, list[list[int]]],
    terminal_tokens: Mapping[str, int],
) -> dict[str, Any]:
    if len(initial_vector) != program["state_width"]:
        _fail("target initial vector width changed")
    constant_names = {
        name
        for expression in [
            program["legal_expression"],
            program["accept_expression"],
            *[row["expression"] for row in program["compiled_assignments"]],
        ]
        for name in _constant_names(expression)
    }
    constants = {
        name: initial_vector[int(name[1:])]
        for name in sorted(constant_names)
    }
    required_relations = set().union(
        *(
            _relation_names(expression)
            for expression in [
                program["legal_expression"],
                program["accept_expression"],
                *[row["expression"] for row in program["compiled_assignments"]],
            ]
        )
    )
    if set(base_relations) != required_relations:
        _fail("target base relation inventory changed")
    if set(terminal_tokens) != {"A", "F", "S"}:
        _fail("target terminal token inventory changed")
    return {
        "state_width": program["state_width"],
        "action_field_width": program["action_field_width"],
        "constants": constants,
        "relations": {key: value for key, value in sorted(base_relations.items())},
        "status_column": next(
            row["target_column"]
            for row in program["compiled_assignments"]
            if _terminal_names(row["expression"])
        ),
        "terminal_tokens": dict(terminal_tokens),
    }


def _constant_names(expression: Any) -> set[str]:
    result: set[str] = set()
    if type(expression) is list:
        if len(expression) == 2 and expression[0] == "E03":
            result.add(expression[1])
        for item in expression:
            result.update(_constant_names(item))
    return result


def _terminal_names(expression: Any) -> set[str]:
    result: set[str] = set()
    if type(expression) is list:
        if len(expression) == 2 and expression[0] == "T":
            result.add(expression[1])
        for item in expression:
            result.update(_terminal_names(item))
    return result


def execute_generic_atomic_support_v4(
    program: Mapping[str, Any],
    state: tuple[int, ...],
    action: FlatRawActionV4,
    binding: Mapping[str, Any],
    *,
    relation_overlay: Mapping[str, Mapping[int, int]] | None = None,
) -> tuple[tuple[int, ...], ...]:
    if len(state) != program["state_width"]:
        _fail("generic atomic execution state width changed")
    branches: list[dict[int, int]] = [{}]
    for assignment in program["compiled_assignments"]:
        target = assignment["target_column"]
        next_branches = []
        for branch in branches:
            value = _evaluate(
                assignment["expression"],
                state=state,
                next_values=branch,
                action=action,
                binding=binding,
                relation_overlay=relation_overlay,
            )
            values = value.values if isinstance(value, _FiniteSupportV4) else (value,)
            for selected in values:
                if type(selected) is not int:
                    _fail("generic atomic assignment produced a noninteger column")
                next_branch = dict(branch)
                next_branch[target] = selected
                next_branches.append(next_branch)
        branches = next_branches
    if any(set(branch) != set(range(program["state_width"])) for branch in branches):
        _fail("generic atomic program did not assign every state column")
    return tuple(
        sorted(
            {
                tuple(branch[column] for column in range(program["state_width"]))
                for branch in branches
            }
        )
    )


def legal_action_keys_v4(
    program: Mapping[str, Any],
    state: tuple[int, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    binding: Mapping[str, Any],
) -> tuple[int, ...]:
    return tuple(
        action.key
        for action in catalogue
        if bool(
            _evaluate(
                program["legal_expression"],
                state=state,
                next_values={},
                action=action,
                binding=binding,
            )
        )
    )


def is_accepting_state_v4(
    program: Mapping[str, Any],
    state: tuple[int, ...],
    binding: Mapping[str, Any],
) -> bool:
    dummy = FlatRawActionV4(0, tuple(0 for _ in range(program["action_field_width"])))
    return bool(
        _evaluate(
            program["accept_expression"],
            state=state,
            next_values={},
            action=dummy,
            binding=binding,
        )
    )


def missing_relation_values_v4(
    program: Mapping[str, Any],
    action: FlatRawActionV4,
    binding: Mapping[str, Any],
    *,
    relation_overlay: Mapping[str, Mapping[int, int]] | None = None,
) -> tuple[tuple[str, int], ...]:
    result = []
    expressions = [row["expression"] for row in program["compiled_assignments"]]

    def visit(expression: Any) -> None:
        if type(expression) is not list:
            return
        if len(expression) >= 3 and expression[0] == "E04":
            name = expression[1]
            key_expression = expression[2]
            if type(key_expression) == list and key_expression[:1] == ["E01"]:
                value = action.fields[key_expression[1]]
                relation = _binding_relation(binding, name)
                if relation_overlay and name in relation_overlay:
                    relation.update(relation_overlay[name])
                if value not in relation:
                    result.append((name, value))
        for item in expression:
            visit(item)

    for expression in expressions:
        visit(expression)
    return tuple(sorted(set(result)))


def plan_generic_atomic_program_v4(
    program: Mapping[str, Any],
    initial: tuple[int, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    binding: Mapping[str, Any],
    *,
    relation_overlay: Mapping[str, Mapping[int, int]] | None = None,
) -> tuple[tuple[int, ...], int, int]:
    by_key = _catalogue(catalogue)
    evaluations = 0
    choice: dict[tuple[int, ...], tuple[int, tuple[tuple[int, ...], ...]]] = {}

    @lru_cache(maxsize=None)
    def solve(state: tuple[int, ...]) -> bool:
        nonlocal evaluations
        if is_accepting_state_v4(program, state, binding):
            return True
        legal = legal_action_keys_v4(program, state, catalogue, binding)
        if not legal:
            return False
        for key in sorted(legal):
            action = by_key[key]
            if missing_relation_values_v4(
                program,
                action,
                binding,
                relation_overlay=relation_overlay,
            ):
                continue
            successors = execute_generic_atomic_support_v4(
                program,
                state,
                action,
                binding,
                relation_overlay=relation_overlay,
            )
            evaluations += len(successors)
            if successors and all(solve(successor) for successor in successors):
                choice[state] = (key, successors)
                return True
        return False

    if not solve(initial):
        _fail("generic atomic program found no robust continuation")
    plan = []
    state = initial
    while not is_accepting_state_v4(program, state, binding):
        if state not in choice:
            _fail("generic atomic contingent choice was incomplete")
        key, successors = choice[state]
        plan.append(key)
        state = max(successors)
    return tuple(plan), evaluations, solve.cache_info().currsize


__all__ = (
    "ATOMIC_COMPOSITION_BEAM_WIDTH_V4",
    "ATOMIC_COMPOSITION_MAX_DEPTH_V4",
    "FlatRawActionV4",
    "FlatRawTransitionV4",
    "GENERIC_ATOMIC_OPCODES_V4",
    "GENERIC_ATOMIC_TYPES_V4",
    "GenericAtomicExpressionWorldModelV4Error",
    "TERMINAL_TREE_BEAM_WIDTH_V4",
    "TERMINAL_TREE_MAX_DEPTH_V4",
    "derive_atomic_dependency_support_v4",
    "execute_generic_atomic_support_v4",
    "generic_atomic_opcode_documents_v4",
    "is_accepting_state_v4",
    "legal_action_keys_v4",
    "missing_relation_values_v4",
    "plan_generic_atomic_program_v4",
    "synthesize_generic_atomic_program_v4",
    "target_binding_from_initial_vector_v4",
)
