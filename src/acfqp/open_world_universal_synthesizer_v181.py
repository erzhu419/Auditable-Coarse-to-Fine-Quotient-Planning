"""Generic length-ordered expression synthesis for opaque transition rows.

The synthesizer has no domain-family switch and no whole-program templates.
It enumerates self-delimiting typed prefix expressions, deduplicates them by
their behavior on the supplied rows, and uses one exact MDL tie break.  A run
is finite because callers supply a compute budget, not because the module
contains a finite catalogue of candidate programs.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable, NoReturn, Sequence


ExpressionV181 = tuple[Any, ...]
_INT_BINARY = ("ADD", "SUB", "MIN", "MAX", "XOR")
_COMPARISONS = ("EQ", "LT")


class OpenWorldUniversalSynthesizerV181Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldUniversalSynthesizerV181Error(message)


def expression_bytes_v181(expression: ExpressionV181) -> bytes:
    return json.dumps(expression, separators=(",", ":"), ensure_ascii=True).encode()


def expression_token_length_v181(expression: ExpressionV181) -> int:
    opcode = expression[0]
    if opcode in {"S", "A", "K"}:
        return 1
    return 1 + sum(
        expression_token_length_v181(item)
        for item in expression[1:]
        if type(item) is tuple
    )


def expression_dependencies_v181(
    expression: ExpressionV181,
) -> tuple[tuple[str, int], ...]:
    rows: set[tuple[str, int]] = set()

    def visit(item: ExpressionV181) -> None:
        if item[0] in {"S", "A"}:
            rows.add((item[0], item[1]))
        for child in item[1:]:
            if type(child) is tuple:
                visit(child)

    visit(expression)
    return tuple(sorted(rows))


def evaluate_expression_v181(
    expression: ExpressionV181,
    state: Sequence[int],
    action: Sequence[int],
) -> int | bool:
    if type(expression) is not tuple or not expression or type(expression[0]) is not str:
        _fail("expression is not one canonical prefix tuple")
    opcode = expression[0]
    if opcode in {"S", "A", "K"}:
        if len(expression) != 2 or type(expression[1]) is not int:
            _fail("atomic expression is malformed")
        if opcode == "K":
            return expression[1]
        source = state if opcode == "S" else action
        if not 0 <= expression[1] < len(source):
            _fail("opaque input coordinate is outside the row")
        value = source[expression[1]]
        if type(value) is not int:
            _fail("opaque input coordinate is not an exact integer")
        return value
    expected_arity = {
        "ADD": 2,
        "SUB": 2,
        "MOD": 2,
        "MIN": 2,
        "MAX": 2,
        "XOR": 2,
        "EQ": 2,
        "LT": 2,
        "AND": 2,
        "SELECT": 3,
    }
    if opcode not in expected_arity or len(expression) != expected_arity[opcode] + 1:
        _fail("expression opcode or arity is outside the universal protocol")
    values = [evaluate_expression_v181(item, state, action) for item in expression[1:]]
    if opcode in _INT_BINARY or opcode == "MOD":
        if any(type(value) is not int for value in values):
            _fail("integer expression received a non-integer child")
        left, right = values
        if opcode == "ADD":
            return left + right
        if opcode == "SUB":
            return left - right
        if opcode == "MOD":
            if right <= 0:
                _fail("modulus is not positive")
            return left % right
        if opcode == "MIN":
            return min(left, right)
        if opcode == "MAX":
            return max(left, right)
        return left ^ right
    if opcode in _COMPARISONS:
        if any(type(value) is not int for value in values):
            _fail("comparison received a non-integer child")
        return values[0] == values[1] if opcode == "EQ" else values[0] < values[1]
    if opcode == "AND":
        if any(type(value) is not bool for value in values):
            _fail("boolean conjunction received a non-boolean child")
        return values[0] and values[1]
    condition, when_true, when_false = values
    if type(condition) is not bool or type(when_true) is not int or type(when_false) is not int:
        _fail("conditional expression types changed")
    return when_true if condition else when_false


@dataclass(frozen=True, slots=True)
class SynthesisRowV181:
    state: tuple[int, ...]
    action: tuple[int, ...]
    target: int | bool

    def __post_init__(self) -> None:
        if (
            type(self.state) is not tuple
            or not self.state
            or any(type(value) is not int for value in self.state)
            or type(self.action) is not tuple
            or not self.action
            or any(type(value) is not int for value in self.action)
            or type(self.target) not in {int, bool}
        ):
            _fail("synthesis row is not one opaque integer observation")


@dataclass(frozen=True, slots=True)
class SynthesizedExpressionV181:
    expression: ExpressionV181
    token_length: int
    enumeration_events: int
    exact_on_all_rows: bool
    residual_values: tuple[int, ...]
    residual_modulus: int | None
    dependencies: tuple[tuple[str, int], ...]
    archive_reference_used: bool


@dataclass(frozen=True, slots=True)
class _CandidateV181:
    expression: ExpressionV181
    outputs: tuple[int | bool, ...]
    value_type: type
    token_length: int
    archive_reference_used: bool


def _candidate(
    expression: ExpressionV181,
    rows: Sequence[SynthesisRowV181],
    *,
    archive_reference_used: bool = False,
    discounted_length: int | None = None,
) -> _CandidateV181 | None:
    try:
        outputs = tuple(
            evaluate_expression_v181(expression, row.state, row.action) for row in rows
        )
    except OpenWorldUniversalSynthesizerV181Error:
        return None
    value_type = type(outputs[0])
    if value_type not in {int, bool} or any(type(value) is not value_type for value in outputs):
        return None
    if value_type is int and any(abs(value) > 1_000_000 for value in outputs):
        return None
    return _CandidateV181(
        expression,
        outputs,
        value_type,
        discounted_length
        if discounted_length is not None
        else expression_token_length_v181(expression),
        archive_reference_used,
    )


def _distance(outputs: Sequence[int | bool], targets: Sequence[int | bool]) -> int:
    if type(targets[0]) is bool:
        return sum(left is not right for left, right in zip(outputs, targets))
    return sum(abs(int(left) - int(right)) for left, right in zip(outputs, targets))


def _residual_signature(
    outputs: Sequence[int | bool], targets: Sequence[int | bool]
) -> tuple[int, ...] | None:
    if type(targets[0]) is not int or any(type(value) is not int for value in outputs):
        return None
    return tuple(sorted({int(target) - int(output) for output, target in zip(outputs, targets)}))


def synthesize_expression_v181(
    rows: Sequence[SynthesisRowV181],
    *,
    maximum_enumeration_events: int,
    maximum_token_length: int = 11,
    beam_width: int = 96,
    maximum_residual_support: int = 3,
    archive: Iterable[ExpressionV181] = (),
) -> SynthesizedExpressionV181:
    if (
        type(rows) not in {tuple, list}
        or not rows
        or any(type(row) is not SynthesisRowV181 for row in rows)
        or type(maximum_enumeration_events) is not int
        or maximum_enumeration_events <= 0
        or type(maximum_token_length) is not int
        or maximum_token_length < 1
        or type(beam_width) is not int
        or beam_width < 16
    ):
        _fail("synthesis configuration or observation rows are invalid")
    state_width = len(rows[0].state)
    action_width = len(rows[0].action)
    target_type = type(rows[0].target)
    if any(
        len(row.state) != state_width
        or len(row.action) != action_width
        or type(row.target) is not target_type
        for row in rows
    ):
        _fail("synthesis rows cross opaque schemas or target types")
    targets = tuple(row.target for row in rows)
    by_semantics: dict[tuple[type, tuple[int | bool, ...]], _CandidateV181] = {}
    by_length: dict[int, list[_CandidateV181]] = {}
    events = 0

    def admit(candidate: _CandidateV181 | None) -> None:
        nonlocal events
        events += 1
        if events > maximum_enumeration_events:
            _fail("program enumeration resource cap exhausted")
        if candidate is None or candidate.token_length > maximum_token_length:
            return
        key = (candidate.value_type, candidate.outputs)
        previous = by_semantics.get(key)
        if previous is not None and (
            previous.token_length,
            expression_bytes_v181(previous.expression),
        ) <= (
            candidate.token_length,
            expression_bytes_v181(candidate.expression),
        ):
            return
        by_semantics[key] = candidate

    for index in range(state_width):
        admit(_candidate(("S", index), rows))
    for index in range(action_width):
        admit(_candidate(("A", index), rows))
    for value in range(10):
        admit(_candidate(("K", value), rows))
    for expression in archive:
        if type(expression) is not tuple:
            _fail("archive contains a non-expression value")
        admit(
            _candidate(
                expression,
                rows,
                archive_reference_used=True,
                discounted_length=1,
            )
        )

    def rebuild_lengths() -> None:
        by_length.clear()
        for candidate in by_semantics.values():
            by_length.setdefault(candidate.token_length, []).append(candidate)
        for length, candidates in tuple(by_length.items()):
            candidates.sort(
                key=lambda item: (
                    _distance(item.outputs, targets),
                    expression_bytes_v181(item.expression),
                )
            )
            del candidates[beam_width:]

    def best_result() -> SynthesizedExpressionV181 | None:
        exact = [
            candidate
            for candidate in by_semantics.values()
            if candidate.value_type is target_type and candidate.outputs == targets
        ]
        if exact:
            selected = min(
                exact,
                key=lambda item: (
                    item.token_length,
                    expression_bytes_v181(item.expression),
                ),
            )
            return SynthesizedExpressionV181(
                selected.expression,
                selected.token_length,
                events,
                True,
                (0,) if target_type is int else (),
                None,
                expression_dependencies_v181(selected.expression),
                selected.archive_reference_used,
            )
        return None

    rebuild_lengths()
    found = best_result()
    if found is not None:
        return found
    for total_length in range(3, maximum_token_length + 1, 2):
        rebuild_lengths()
        snapshot = {length: tuple(values) for length, values in by_length.items()}
        for left_length, left_rows in snapshot.items():
            right_length = total_length - 1 - left_length
            right_rows = snapshot.get(right_length, ())
            for left in left_rows:
                for right in right_rows:
                    if left.value_type is int and right.value_type is int:
                        for opcode in _INT_BINARY:
                            admit(
                                _candidate(
                                    (opcode, left.expression, right.expression), rows,
                                    archive_reference_used=(
                                        left.archive_reference_used
                                        or right.archive_reference_used
                                    ),
                                )
                            )
                        for opcode in _COMPARISONS:
                            admit(
                                _candidate(
                                    (opcode, left.expression, right.expression), rows,
                                    archive_reference_used=(
                                        left.archive_reference_used
                                        or right.archive_reference_used
                                    ),
                                )
                            )
                    if left.value_type is bool and right.value_type is bool:
                        admit(
                            _candidate(
                                ("AND", left.expression, right.expression), rows,
                                archive_reference_used=(
                                    left.archive_reference_used
                                    or right.archive_reference_used
                                ),
                            )
                        )
        for child_length, child_rows in snapshot.items():
            constant_length = total_length - 1 - child_length
            if constant_length != 1:
                continue
            for child in child_rows:
                if child.value_type is not int:
                    continue
                for modulus in range(2, 10):
                    admit(
                        _candidate(
                            ("MOD", child.expression, ("K", modulus)), rows,
                            archive_reference_used=child.archive_reference_used,
                        )
                    )
        for predicate_length, predicates in snapshot.items():
            for true_length, true_rows in snapshot.items():
                false_length = total_length - 1 - predicate_length - true_length
                false_rows = snapshot.get(false_length, ())
                for predicate in predicates:
                    if predicate.value_type is not bool:
                        continue
                    for when_true in true_rows:
                        if when_true.value_type is not int:
                            continue
                        for when_false in false_rows:
                            if when_false.value_type is not int:
                                continue
                            admit(
                                _candidate(
                                    (
                                        "SELECT",
                                        predicate.expression,
                                        when_true.expression,
                                        when_false.expression,
                                    ),
                                    rows,
                                    archive_reference_used=(
                                        predicate.archive_reference_used
                                        or when_true.archive_reference_used
                                        or when_false.archive_reference_used
                                    ),
                                )
                            )
        rebuild_lengths()
        found = best_result()
        if found is not None:
            return found

    if target_type is bool:
        _fail("no exact boolean expression found within the run budget")
    residual_candidates = []
    inferred_modulus = max(
        max(max(row.state) for row in rows),
        max(int(row.target) for row in rows),
    ) + 1
    for candidate in by_semantics.values():
        if candidate.value_type is not int:
            continue
        residuals = _residual_signature(candidate.outputs, targets)
        if residuals is not None and len(residuals) <= maximum_residual_support:
            residual_candidates.append(
                (
                    len(residuals),
                    candidate.token_length,
                    expression_bytes_v181(candidate.expression),
                    candidate,
                    residuals,
                )
            )
    if not residual_candidates:
        _fail("no bounded finite residual support found within the run budget")
    _, _, _, selected, residuals = min(residual_candidates)
    return SynthesizedExpressionV181(
        selected.expression,
        selected.token_length,
        events,
        False,
        residuals,
        inferred_modulus,
        expression_dependencies_v181(selected.expression),
        selected.archive_reference_used,
    )


__all__ = (
    "ExpressionV181",
    "OpenWorldUniversalSynthesizerV181Error",
    "SynthesisRowV181",
    "SynthesizedExpressionV181",
    "evaluate_expression_v181",
    "expression_bytes_v181",
    "expression_dependencies_v181",
    "expression_token_length_v181",
    "synthesize_expression_v181",
)
