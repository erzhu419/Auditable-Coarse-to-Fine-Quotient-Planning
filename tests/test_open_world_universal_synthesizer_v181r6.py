from acfqp.open_world_universal_synthesizer_v181 import SynthesisRowV181
from acfqp.open_world_universal_synthesizer_v181r6 import (
    synthesize_expression_v181r6,
)


def test_deterministic_wrapped_update_uses_one_point_cyclic_support() -> None:
    rows = tuple(
        SynthesisRowV181((state, 0), (action,), (state + action) % 5)
        for state in range(5)
        for action in range(3)
    )
    result = synthesize_expression_v181r6(
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
    result = synthesize_expression_v181r6(
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
    result = synthesize_expression_v181r6(
        rows,
        maximum_enumeration_events=200_000,
    )
    assert result.exact_on_all_rows is True
    assert result.residual_values == ()
    assert result.residual_modulus is None


def test_archive_proposal_receives_no_mdl_discount() -> None:
    rows = tuple(
        SynthesisRowV181((state,), (action,), state + action)
        for state in range(4)
        for action in range(3)
    )
    result = synthesize_expression_v181r6(
        rows,
        maximum_enumeration_events=200_000,
        residual_modulus=8,
        archive=(("ADD", ("ADD", ("S", 0), ("A", 0)), ("K", 0)),),
    )
    assert result.expression == ("ADD", ("A", 0), ("S", 0))
    assert result.token_length == 3
    assert result.archive_reference_used is False


def test_exact_archive_reference_is_revalidated_at_its_real_length() -> None:
    expression = ("MOD", ("ADD", ("A", 0), ("S", 0)), ("K", 5))
    rows = tuple(
        SynthesisRowV181((state,), (action,), (state + action) % 5)
        for state in range(5)
        for action in range(3)
    )
    result = synthesize_expression_v181r6(
        rows,
        maximum_enumeration_events=200_000,
        residual_modulus=5,
        archive=(expression,),
    )
    assert result.expression == expression
    assert result.token_length == 5
    assert result.archive_reference_used is True
