from __future__ import annotations

import ast
from pathlib import Path

from acfqp.open_world_universal_machine_v182 import (
    DECJZ,
    HALT,
    INC,
    JUMP,
    MachineSynthesisRowV182,
    READ,
    execute_program_v182,
    synthesize_scalar_program_v182,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "acfqp" / "open_world_universal_machine_v182.py"


def test_v182_counter_machine_executes_branching_and_bounded_divergence() -> None:
    decrement = ((READ, 0, 0), (DECJZ, 0, 2, 2), (HALT, 0))
    positive = execute_program_v182(
        decrement,
        state=(3,),
        action=(0,),
        register_count=2,
        maximum_steps=8,
    )
    zero = execute_program_v182(
        decrement,
        state=(0,),
        action=(0,),
        register_count=2,
        maximum_steps=8,
    )
    divergent = execute_program_v182(
        ((JUMP, 0),),
        state=(0,),
        action=(0,),
        register_count=2,
        maximum_steps=5,
    )
    assert (positive.halted, positive.output, positive.read_dependencies) == (
        True,
        2,
        (0,),
    )
    assert (zero.halted, zero.output) == (True, 0)
    assert (divergent.halted, divergent.output, divergent.steps) == (False, None, 5)


def test_v182_length_order_discovers_a_program_without_a_named_template() -> None:
    rows = tuple(
        MachineSynthesisRowV182((value,), (value % 2,), value + 1)
        for value in range(5)
    )
    result = synthesize_scalar_program_v182(
        rows,
        maximum_enumeration_events=2_000,
        maximum_instruction_count=3,
        maximum_execution_steps=12,
    )
    assert result.exact_on_all_rows is True
    assert result.instruction_count == 3
    assert result.program == ((READ, 0, 0), (INC, 0), (HALT, 0))
    assert result.read_dependencies == (("S", 0),)
    document = result.to_document()
    assert document["domain_specific_primitive_used"] is False
    assert document["whole_program_template_used"] is False
    assert document["named_layout_used"] is False
    assert document["language_program_length_unbounded"] is True
    assert document["occurrence_search_resource_bounded"] is True


def test_v182_learns_finite_partial_support_separately_from_program() -> None:
    rows = tuple(
        MachineSynthesisRowV182((state,), (0,), state + residual)
        for state in (1, 3, 5)
        for residual in (0, 2)
    )
    result = synthesize_scalar_program_v182(
        rows,
        maximum_enumeration_events=2_000,
        maximum_instruction_count=2,
        maximum_execution_steps=8,
        maximum_residual_support=2,
    )
    assert result.exact_on_all_rows is False
    assert result.program == ((READ, 0, 0), (HALT, 0))
    assert result.residual_values == (0, 2)
    assert result.read_dependencies == (("S", 0),)


def test_v182_source_has_no_domain_family_or_whole_program_catalog() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    ast.parse(source)
    forbidden = (
        "LMB",
        "2048",
        "ROUTING_DOMAIN",
        "MANIFEST_DOCUMENTS",
        "WHOLE_PROGRAM_CANDIDATES",
    )
    assert not any(token in source for token in forbidden)
