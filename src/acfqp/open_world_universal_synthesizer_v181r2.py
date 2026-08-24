"""V181r2 generic synthesis with cyclic finite-residual semantics.

V181 computed stochastic residuals in the ordinary integers even when the
compiled successor coordinate lived in a finite cyclic carrier.  Wraparound
therefore inflated a true three-point support to five signed differences and
caused the retained V181r1 resource failure.  This additive successor keeps
the same typed expression grammar and MDL search, but derives residuals in the
observed coordinate carrier.  It also checks the lowest-length residual
candidate immediately instead of scanning a longer deterministic frontier.
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
    synthesize_expression_v181,
)


class OpenWorldUniversalSynthesizerV181R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldUniversalSynthesizerV181R2Error(message)


@dataclass(frozen=True, slots=True)
class _CandidateV181R2:
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
) -> _CandidateV181R2 | None:
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
    return _CandidateV181R2(
        expression,
        outputs,
        value_type,
        discounted_length
        if discounted_length is not None
        else expression_token_length_v181(expression),
        archive_reference_used,
    )


def _distance(
    outputs: Sequence[int | bool], targets: Sequence[int | bool]
) -> int:
    if type(targets[0]) is bool:
        return sum(left is not right for left, right in zip(outputs, targets))
    return sum(abs(int(left) - int(right)) for left, right in zip(outputs, targets))


def synthesize_expression_v181r2(
    rows: Sequence[SynthesisRowV181],
    *,
    maximum_enumeration_events: int,
    maximum_token_length: int = 11,
    beam_width: int = 96,
    maximum_residual_support: int = 3,
    residual_modulus: int | None = None,
    archive: Iterable[ExpressionV181] = (),
) -> SynthesizedExpressionV181:
    """Synthesize one expression, using cyclic residuals when stochastic.

    Deterministic and boolean rows retain the frozen V181 enumerator exactly.
    Stochastic integer rows require a caller-supplied, observation-derived
    carrier modulus and search the same generic expression grammar for a base
    whose modular residual support is bounded.
    """

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
        or maximum_residual_support < 2
    ):
        _fail("V181r2 synthesis configuration changed")
    state_width = len(rows[0].state)
    action_width = len(rows[0].action)
    target_type = type(rows[0].target)
    if any(
        len(row.state) != state_width
        or len(row.action) != action_width
        or type(row.target) is not target_type
        for row in rows
    ):
        _fail("V181r2 rows cross opaque schemas or target types")
    targets = tuple(row.target for row in rows)
    targets_by_input: dict[
        tuple[tuple[int, ...], tuple[int, ...]], set[int | bool]
    ] = {}
    for row in rows:
        targets_by_input.setdefault((row.state, row.action), set()).add(row.target)
    stochastic = target_type is int and any(
        len(values) > 1 for values in targets_by_input.values()
    )
    if not stochastic:
        try:
            return synthesize_expression_v181(
                rows,
                maximum_enumeration_events=maximum_enumeration_events,
                maximum_token_length=maximum_token_length,
                beam_width=beam_width,
                maximum_residual_support=maximum_residual_support,
                archive=archive,
            )
        except OpenWorldUniversalSynthesizerV181Error as error:
            raise OpenWorldUniversalSynthesizerV181R2Error(str(error)) from error
    if (
        type(residual_modulus) is not int
        or residual_modulus < 2
        or any(type(value) is not int or not 0 <= value < residual_modulus for value in targets)
    ):
        _fail("stochastic rows lack one valid observation-derived carrier modulus")

    by_semantics: dict[tuple[type, tuple[int | bool, ...]], _CandidateV181R2] = {}
    by_length: dict[int, list[_CandidateV181R2]] = {}
    events = 0

    def admit(candidate: _CandidateV181R2 | None) -> None:
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

    def rebuild_lengths() -> None:
        by_length.clear()
        for candidate in by_semantics.values():
            by_length.setdefault(candidate.token_length, []).append(candidate)
        for candidates in by_length.values():
            candidates.sort(
                key=lambda item: (
                    _distance(item.outputs, targets),
                    expression_bytes_v181(item.expression),
                )
            )
            del candidates[beam_width:]

    def best_residual() -> SynthesizedExpressionV181 | None:
        candidates = []
        for candidate in by_semantics.values():
            if candidate.value_type is not int:
                continue
            residuals = tuple(
                sorted(
                    {
                        (int(target) - int(output)) % residual_modulus
                        for output, target in zip(candidate.outputs, targets)
                    }
                )
            )
            if 1 < len(residuals) <= maximum_residual_support:
                candidates.append(
                    (
                        candidate.token_length + len(residuals),
                        len(residuals),
                        candidate.token_length,
                        expression_bytes_v181(candidate.expression),
                        candidate,
                        residuals,
                    )
                )
        if not candidates:
            return None
        *_, selected, residuals = min(candidates)
        return SynthesizedExpressionV181(
            selected.expression,
            selected.token_length,
            events,
            False,
            residuals,
            residual_modulus,
            expression_dependencies_v181(selected.expression),
            selected.archive_reference_used,
        )

    maximum_constant = max(9, residual_modulus)
    for index in range(state_width):
        admit(_candidate(("S", index), rows))
    for index in range(action_width):
        admit(_candidate(("A", index), rows))
    for value in range(maximum_constant + 1):
        admit(_candidate(("K", value), rows))
    for expression in tuple(archive):
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
    rebuild_lengths()
    found = best_residual()
    if found is not None:
        return found

    int_binary = ("ADD", "SUB", "MIN", "MAX", "XOR")
    comparisons = ("EQ", "LT")
    for total_length in range(3, maximum_token_length + 1, 2):
        rebuild_lengths()
        snapshot = {length: tuple(values) for length, values in by_length.items()}
        for left_length, left_rows in snapshot.items():
            right_rows = snapshot.get(total_length - 1 - left_length, ())
            for left in left_rows:
                for right in right_rows:
                    archived = (
                        left.archive_reference_used or right.archive_reference_used
                    )
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
                    total_length - 1 - predicate_length - true_length, ()
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
        found = best_residual()
        if found is not None:
            return found
    _fail("no bounded cyclic residual support found within the run budget")


__all__ = (
    "OpenWorldUniversalSynthesizerV181R2Error",
    "synthesize_expression_v181r2",
)
