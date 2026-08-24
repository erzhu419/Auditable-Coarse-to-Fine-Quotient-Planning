from acfqp.open_world_universal_synthesizer_v181 import SynthesisRowV181
from acfqp.open_world_universal_synthesizer_v181r3 import (
    synthesize_expression_v181r3,
)


def test_deterministic_wrapped_update_uses_one_point_cyclic_support() -> None:
    rows = tuple(
        SynthesisRowV181((state, 0), (action,), (state + action) % 5)
        for state in range(5)
        for action in range(3)
    )
    result = synthesize_expression_v181r3(
        rows,
        maximum_enumeration_events=200_000,
        residual_modulus=5,
    )
    assert result.expression == (
        "MOD",
        ("ADD", ("A", 0), ("S", 0)),
        ("K", 5),
    )
    assert result.exact_on_all_rows is True
    assert result.residual_values == (0,)
    assert result.residual_modulus is None
    assert result.token_length == 5


def test_shorter_three_point_scaffold_does_not_hide_tighter_length_three_model() -> None:
    rows = tuple(
        SynthesisRowV181((state, 0), (action,), (state + action + noise) % 5)
        for state in range(5)
        for action in range(3)
        for noise in (0, 1)
    )
    result = synthesize_expression_v181r3(
        rows,
        maximum_enumeration_events=200_000,
        residual_modulus=5,
    )
    assert result.expression == ("ADD", ("A", 0), ("S", 0))
    assert result.residual_values == (0, 1)
    assert result.residual_modulus == 5


def test_boolean_expression_remains_exact_and_has_no_residual() -> None:
    rows = tuple(
        SynthesisRowV181((state, 0), (0,), state == 0)
        for state in range(5)
    )
    result = synthesize_expression_v181r3(
        rows,
        maximum_enumeration_events=200_000,
    )
    assert result.exact_on_all_rows is True
    assert result.residual_values == ()
    assert result.residual_modulus is None
