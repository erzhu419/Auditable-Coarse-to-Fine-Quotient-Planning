from __future__ import annotations

import pytest

from acfqp.open_world_universal_synthesizer_v181 import (
    OpenWorldUniversalSynthesizerV181Error,
    SynthesisRowV181,
    evaluate_expression_v181,
    expression_dependencies_v181,
    synthesize_expression_v181,
)


def _rows(expression, *, width=3, action_width=2):
    rows = []
    for seed in range(18):
        state = tuple((seed * (index + 2) + index) % 7 for index in range(width))
        action = tuple((seed + 2 * index) % 4 for index in range(action_width))
        rows.append(
            SynthesisRowV181(
                state,
                action,
                evaluate_expression_v181(expression, state, action),
            )
        )
    return tuple(rows)


@pytest.mark.parametrize(
    "expression",
    (
        ("MOD", ("ADD", ("S", 0), ("A", 0)), ("K", 5)),
        ("XOR", ("S", 2), ("MOD", ("A", 1), ("K", 2))),
        ("MAX", ("K", 0), ("SUB", ("S", 1), ("K", 1))),
        (
            "AND",
            ("EQ", ("S", 0), ("K", 0)),
            ("LT", ("S", 1), ("K", 3)),
        ),
    ),
)
def test_bottom_up_search_recovers_development_expressions(expression) -> None:
    result = synthesize_expression_v181(
        _rows(expression),
        maximum_enumeration_events=1_000_000,
        maximum_token_length=9,
    )
    assert result.exact_on_all_rows is True
    assert all(
        evaluate_expression_v181(result.expression, row.state, row.action)
        == row.target
        for row in _rows(expression)
    )
    assert result.dependencies == expression_dependencies_v181(result.expression)


def test_archive_is_only_a_discounted_generic_subprogram() -> None:
    expression = ("MOD", ("ADD", ("S", 0), ("A", 0)), ("K", 5))
    result = synthesize_expression_v181(
        _rows(expression),
        maximum_enumeration_events=50_000,
        archive=(expression,),
    )
    assert result.exact_on_all_rows is True
    assert result.archive_reference_used is True
    assert result.token_length == 1


def test_stochastic_residual_is_retained_instead_of_fabricated_exactness() -> None:
    rows = []
    for seed in range(18):
        state = (seed % 5, (seed * 2) % 7)
        action = (seed % 3,)
        target = state[0] + (seed % 2)
        rows.append(SynthesisRowV181(state, action, target))
    result = synthesize_expression_v181(
        tuple(rows),
        maximum_enumeration_events=100_000,
        maximum_token_length=3,
        maximum_residual_support=3,
    )
    assert result.exact_on_all_rows is False
    assert len(result.residual_values) in {2, 3}
    assert result.residual_modulus is not None


def test_schema_crossing_and_resource_exhaustion_fail_closed() -> None:
    with pytest.raises(OpenWorldUniversalSynthesizerV181Error):
        synthesize_expression_v181(
            (
                SynthesisRowV181((0, 1), (0,), 0),
                SynthesisRowV181((0, 1, 2), (0,), 1),
            ),
            maximum_enumeration_events=100,
        )
    with pytest.raises(OpenWorldUniversalSynthesizerV181Error, match="resource cap"):
        synthesize_expression_v181(
            _rows(("MOD", ("ADD", ("S", 0), ("A", 0)), ("K", 5))),
            maximum_enumeration_events=1,
        )
