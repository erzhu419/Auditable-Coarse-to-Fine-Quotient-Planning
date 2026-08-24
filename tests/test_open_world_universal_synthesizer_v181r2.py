from __future__ import annotations

import pytest

from acfqp.open_world_universal_synthesizer_v181 import (
    SynthesisRowV181,
    evaluate_expression_v181,
)
from acfqp.open_world_universal_synthesizer_v181r2 import (
    OpenWorldUniversalSynthesizerV181R2Error,
    synthesize_expression_v181r2,
)


def test_wraparound_three_point_support_stays_three_not_five() -> None:
    rows = []
    for state_value in range(3):
        state = (state_value, 0)
        action = (0,)
        for residual in range(3):
            rows.append(
                SynthesisRowV181(
                    state,
                    action,
                    (state_value + residual) % 3,
                )
            )
    result = synthesize_expression_v181r2(
        tuple(rows),
        maximum_enumeration_events=1_000,
        maximum_token_length=7,
        maximum_residual_support=3,
        residual_modulus=3,
    )
    assert result.exact_on_all_rows is False
    assert result.residual_values == (0, 1, 2)
    assert result.residual_modulus == 3
    assert result.enumeration_events < 100


def test_two_point_cyclic_support_recovers_opaque_state_base() -> None:
    rows = []
    for state_value in range(5):
        for action_value in range(3):
            state = (9 - state_value, state_value)
            action = (action_value,)
            for residual in (0, 2):
                rows.append(
                    SynthesisRowV181(
                        state,
                        action,
                        (state_value + residual) % 5,
                    )
                )
    result = synthesize_expression_v181r2(
        tuple(rows),
        maximum_enumeration_events=5_000,
        residual_modulus=5,
    )
    assert result.expression == ("S", 1)
    assert result.residual_values == (0, 2)
    assert result.dependencies == (("S", 1),)


def test_deterministic_expression_delegates_without_semantic_change() -> None:
    expression = ("MOD", ("ADD", ("S", 0), ("A", 0)), ("K", 5))
    rows = tuple(
        SynthesisRowV181(
            (seed % 5, (seed * 2) % 7),
            (seed % 3,),
            evaluate_expression_v181(
                expression,
                (seed % 5, (seed * 2) % 7),
                (seed % 3,),
            ),
        )
        for seed in range(18)
    )
    result = synthesize_expression_v181r2(
        rows,
        maximum_enumeration_events=1_000_000,
        maximum_token_length=9,
    )
    assert result.exact_on_all_rows is True
    assert all(
        evaluate_expression_v181(result.expression, row.state, row.action)
        == row.target
        for row in rows
    )


def test_stochastic_modulus_and_resource_caps_fail_closed() -> None:
    rows = (
        SynthesisRowV181((0,), (0,), 0),
        SynthesisRowV181((0,), (0,), 1),
    )
    with pytest.raises(OpenWorldUniversalSynthesizerV181R2Error, match="modulus"):
        synthesize_expression_v181r2(
            rows,
            maximum_enumeration_events=100,
        )
    with pytest.raises(OpenWorldUniversalSynthesizerV181R2Error, match="resource cap"):
        synthesize_expression_v181r2(
            rows,
            maximum_enumeration_events=1,
            residual_modulus=2,
        )
