"""Length-ordered MDL synthesis with non-discounted archive proposals.

V181r5 preserves the carrier-aware V181r3 semantics, but removes the archive's
artificial one-token MDL discount.  Archive expressions are evaluated on the
current raw rows and enter the same length order as newly enumerated programs.
They may accelerate discovery and later earn evidence-based acquisition credit,
but can no longer win merely because they came from another domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, NoReturn, Sequence

from acfqp.open_world_universal_synthesizer_v181 import (
    ExpressionV181,
    OpenWorldUniversalSynthesizerV181Error,
    SynthesisRowV181,
    SynthesizedExpressionV181,
    evaluate_expression_v181,
    expression_bytes_v181,
    expression_dependencies_v181,
    expression_token_length_v181,
)


class OpenWorldUniversalSynthesizerV181R5Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldUniversalSynthesizerV181R5Error(message)


@dataclass(frozen=True, slots=True)
class _CandidateV181R5:
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
) -> _CandidateV181R5 | None:
    try:
        outputs = tuple(
            evaluate_expression_v181(expression, row.state, row.action)
            for row in rows
        )
    except OpenWorldUniversalSynthesizerV181Error:
        return None
    value_type = type(outputs[0])
    if value_type not in {int, bool} or any(
        type(value) is not value_type for value in outputs
    ):
        return None
    if value_type is int and any(abs(value) > 1_000_000 for value in outputs):
        return None
    return _CandidateV181R5(
        expression,
        outputs,
        value_type,
        expression_token_length_v181(expression),
        archive_reference_used,
    )


def _inside_current_grammar(
    expression: ExpressionV181,
    *,
    state_width: int,
    action_width: int,
    maximum_constant: int,
) -> bool:
    if type(expression) is not tuple or not expression:
        return False
    opcode = expression[0]
    if opcode == "S":
        return (
            len(expression) == 2
            and type(expression[1]) is int
            and 0 <= expression[1] < state_width
        )
    if opcode == "A":
        return (
            len(expression) == 2
            and type(expression[1]) is int
            and 0 <= expression[1] < action_width
        )
    if opcode == "K":
        return (
            len(expression) == 2
            and type(expression[1]) is int
            and 0 <= expression[1] <= maximum_constant
        )
    if opcode in {"ADD", "SUB", "MIN", "MAX", "XOR", "EQ", "LT", "AND"}:
        return len(expression) == 3 and all(
            _inside_current_grammar(
                child,
                state_width=state_width,
                action_width=action_width,
                maximum_constant=maximum_constant,
            )
            for child in expression[1:]
        )
    if opcode == "MOD":
        return (
            len(expression) == 3
            and _inside_current_grammar(
                expression[1],
                state_width=state_width,
                action_width=action_width,
                maximum_constant=maximum_constant,
            )
            and type(expression[2]) is tuple
            and expression[2][0:1] == ("K",)
            and len(expression[2]) == 2
            and type(expression[2][1]) is int
            and 2 <= expression[2][1] <= maximum_constant
        )
    if opcode == "SELECT":
        return len(expression) == 4 and all(
            _inside_current_grammar(
                child,
                state_width=state_width,
                action_width=action_width,
                maximum_constant=maximum_constant,
            )
            for child in expression[1:]
        )
    return False


def _distance(
    outputs: Sequence[int | bool],
    targets: Sequence[int | bool],
    residual_modulus: int | None,
) -> int:
    if type(targets[0]) is bool:
        return sum(left is not right for left, right in zip(outputs, targets))
    if residual_modulus is None:
        return sum(abs(int(left) - int(right)) for left, right in zip(outputs, targets))
    return sum(
        min(
            (int(left) - int(right)) % residual_modulus,
            (int(right) - int(left)) % residual_modulus,
        )
        for left, right in zip(outputs, targets)
    )


def synthesize_expression_v181r5(
    rows: Sequence[SynthesisRowV181],
    *,
    maximum_enumeration_events: int,
    maximum_token_length: int = 11,
    beam_width: int = 96,
    maximum_residual_support: int = 3,
    residual_modulus: int | None = None,
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
        or type(maximum_residual_support) is not int
        or maximum_residual_support < 1
    ):
        _fail("V181r5 synthesis configuration changed")
    state_width = len(rows[0].state)
    action_width = len(rows[0].action)
    target_type = type(rows[0].target)
    if any(
        len(row.state) != state_width
        or len(row.action) != action_width
        or type(row.target) is not target_type
        for row in rows
    ):
        _fail("V181r5 rows cross opaque schemas or target types")
    targets = tuple(row.target for row in rows)
    if target_type is int and (
        type(residual_modulus) is not int
        or residual_modulus < 2
        or any(not 0 <= int(value) < residual_modulus for value in targets)
    ):
        _fail("integer rows lack one observation-derived finite carrier")
    if target_type is bool and residual_modulus is not None:
        _fail("boolean rows cannot carry a residual modulus")
    targets_by_input: dict[
        tuple[tuple[int, ...], tuple[int, ...]],
        set[int | bool],
    ] = {}
    for row in rows:
        targets_by_input.setdefault((row.state, row.action), set()).add(row.target)
    minimum_required_residual_support = max(
        len(values) for values in targets_by_input.values()
    )
    exact_program_logically_possible = minimum_required_residual_support == 1
    residual_value_code_units = (
        max(1, (residual_modulus - 1).bit_length())
        if residual_modulus is not None
        else 0
    )

    by_semantics: dict[tuple[type, tuple[int | bool, ...]], _CandidateV181R5] = {}
    by_length: dict[int, list[_CandidateV181R5]] = {}
    events = 0

    def admit(candidate: _CandidateV181R5 | None) -> None:
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
            if (
                previous.expression == candidate.expression
                and not previous.archive_reference_used
                and candidate.archive_reference_used
            ):
                by_semantics[key] = candidate
            return
        by_semantics[key] = candidate

    def rebuild_lengths() -> None:
        by_length.clear()
        for candidate in by_semantics.values():
            by_length.setdefault(candidate.token_length, []).append(candidate)
        for candidates in by_length.values():
            candidates.sort(
                key=lambda item: (
                    _distance(item.outputs, targets, residual_modulus),
                    expression_bytes_v181(item.expression),
                )
            )
            del candidates[beam_width:]

    def best_result() -> tuple[tuple[object, ...], SynthesizedExpressionV181] | None:
        ranked: list[tuple[tuple[object, ...], SynthesizedExpressionV181]] = []
        for candidate in by_semantics.values():
            if candidate.value_type is not target_type:
                continue
            exact = candidate.outputs == targets
            if exact:
                result = SynthesizedExpressionV181(
                    candidate.expression,
                    candidate.token_length,
                    events,
                    True,
                    (0,) if target_type is int else (),
                    None,
                    expression_dependencies_v181(candidate.expression),
                    candidate.archive_reference_used,
                )
                rank: tuple[object, ...] = (
                    candidate.token_length,
                    0,
                    0,
                    candidate.token_length,
                    expression_bytes_v181(candidate.expression),
                )
                ranked.append((rank, result))
                continue
            if target_type is not int:
                continue
            assert residual_modulus is not None
            residuals = tuple(
                sorted(
                    {
                        (int(target) - int(output)) % residual_modulus
                        for output, target in zip(candidate.outputs, targets)
                    }
                )
            )
            if not 1 <= len(residuals) <= maximum_residual_support:
                continue
            result = SynthesizedExpressionV181(
                candidate.expression,
                candidate.token_length,
                events,
                False,
                residuals,
                residual_modulus,
                expression_dependencies_v181(candidate.expression),
                candidate.archive_reference_used,
            )
            rank = (
                candidate.token_length
                + residual_value_code_units * len(residuals),
                1,
                len(residuals),
                candidate.token_length,
                expression_bytes_v181(candidate.expression),
            )
            ranked.append((rank, result))
        return min(ranked, key=lambda item: item[0]) if ranked else None

    maximum_constant = max(
        9,
        residual_modulus if residual_modulus is not None else 0,
    )
    for index in range(state_width):
        admit(_candidate(("S", index), rows))
    for index in range(action_width):
        admit(_candidate(("A", index), rows))
    for value in range(maximum_constant + 1):
        admit(_candidate(("K", value), rows))
    for expression in tuple(archive):
        if not _inside_current_grammar(
            expression,
            state_width=state_width,
            action_width=action_width,
            maximum_constant=maximum_constant,
        ):
            _fail("archive expression is outside the current typed grammar")
        admit(
            _candidate(
                expression,
                rows,
                archive_reference_used=True,
            )
        )
    rebuild_lengths()
    found = best_result()
    first_unseen_lower_bound = (
        3
        if exact_program_logically_possible
        else 3
        + residual_value_code_units * minimum_required_residual_support
    )
    if found is not None and int(found[0][0]) < first_unseen_lower_bound:
        return found[1]

    int_binary = ("ADD", "SUB", "MIN", "MAX", "XOR")
    comparisons = ("EQ", "LT")
    for total_length in range(3, maximum_token_length + 1, 2):
        rebuild_lengths()
        snapshot = {length: tuple(values) for length, values in by_length.items()}
        for left_length, left_rows in snapshot.items():
            right_rows = snapshot.get(total_length - 1 - left_length, ())
            for left in left_rows:
                for right in right_rows:
                    archived = left.archive_reference_used or right.archive_reference_used
                    if left.value_type is int and right.value_type is int:
                        for opcode in (*int_binary, *comparisons):
                            admit(
                                _candidate(
                                    (opcode, left.expression, right.expression),
                                    rows,
                                    archive_reference_used=archived,
                                )
                            )
                    elif left.value_type is bool and right.value_type is bool:
                        admit(
                            _candidate(
                                ("AND", left.expression, right.expression),
                                rows,
                                archive_reference_used=archived,
                            )
                        )
        for child_length, child_rows in snapshot.items():
            if total_length - 1 - child_length != 1:
                continue
            for child in child_rows:
                if child.value_type is not int:
                    continue
                for modulus in range(2, maximum_constant + 1):
                    admit(
                        _candidate(
                            ("MOD", child.expression, ("K", modulus)),
                            rows,
                            archive_reference_used=child.archive_reference_used,
                        )
                    )
        for predicate_length, predicates in snapshot.items():
            for true_length, true_rows in snapshot.items():
                false_rows = snapshot.get(
                    total_length - 1 - predicate_length - true_length,
                    (),
                )
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
        if found is None:
            continue
        rank, result = found
        next_unseen_length = total_length + 2
        next_unseen_lower_bound = (
            next_unseen_length
            if exact_program_logically_possible
            else next_unseen_length
            + residual_value_code_units * minimum_required_residual_support
        )
        if result.exact_on_all_rows or int(rank[0]) < next_unseen_lower_bound:
            return result
    found = best_result()
    if found is None:
        _fail("no exact or bounded cyclic model found within the run budget")
    return found[1]


__all__ = (
    "OpenWorldUniversalSynthesizerV181R5Error",
    "synthesize_expression_v181r5",
)
