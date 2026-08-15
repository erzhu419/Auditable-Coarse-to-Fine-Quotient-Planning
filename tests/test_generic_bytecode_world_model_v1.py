from __future__ import annotations

from acfqp.generic_bytecode_world_model_v1 import (
    RawActionV1,
    RawTransitionV1,
    synthesize_generic_program_v1,
)
from acfqp.phase3e_ids import CONSTRUCTION_K7_GENERIC_BYTECODE_PROGRAM_V47_DOMAIN


def test_generic_synthesizer_selects_vector_set_program_without_domain_names() -> None:
    actions = tuple(
        RawActionV1(index, (1 << index, 0, 10 if index < 3 else 20, 1000 + index))
        for index in range(6)
    )
    rows = (
        RawTransitionV1(1, 0, (0, 0, 0, 1, 100), tuple(range(6)), actions[0], (1, 1, 0, 1, 100), tuple(range(1, 6))),
        RawTransitionV1(1, 1, (1, 1, 0, 1, 100), tuple(range(1, 6)), actions[1], (3, 2, 0, 1, 101), ()),
        RawTransitionV1(1, 2, (3, 2, 0, 1, 100), tuple(range(2, 6)), actions[2], (7, 0, 0, 1, 100), tuple(range(3, 6))),
        RawTransitionV1(1, 3, (31, 0, 2, 1, 100), (5,), actions[5], (63, 0, 0, 1, 102), ()),
    )
    program = synthesize_generic_program_v1(
        rows,
        {1: actions},
        program_domain=CONSTRUCTION_K7_GENERIC_BYTECODE_PROGRAM_V47_DOMAIN,
    )
    assert program["selected_template_opcode"] == "T00"
    assert program["unregistered_opcode_names"] == []
    assert "lmb" not in repr(program).lower()


def test_generic_synthesizer_selects_partial_categorical_program() -> None:
    actions = (
        RawActionV1(0, (10, 11, 1, 20, 100)),
        RawActionV1(1, (10, 12, 2, 21, 101)),
        RawActionV1(2, (11, 13, 1, 20, 102)),
        RawActionV1(3, (12, 13, 2, 21, 103)),
    )
    rows = (
        RawTransitionV1(2, 0, (10, 0, 200, 3), (0, 1), actions[0], (11, 0, 200, 3), (2,)),
        RawTransitionV1(2, 1, (10, 0, 200, 3), (0, 1), actions[1], (12, 2, 200, 3), (3,)),
        RawTransitionV1(2, 2, (11, 3, 200, 3), (2,), actions[2], (13, 4, 500, 3), ()),
        RawTransitionV1(2, 3, (12, 0, 200, 3), (3,), actions[3], (13, 0, 600, 3), ()),
    )
    program = synthesize_generic_program_v1(
        rows,
        {2: actions},
        program_domain=CONSTRUCTION_K7_GENERIC_BYTECODE_PROGRAM_V47_DOMAIN,
    )
    assert program["selected_template_opcode"] == "T01"
    binding = program["occurrence_bindings"][0]
    assert binding["categorical_support_rows"] == [[20, [0, 1]], [21, [0, 2]]]
    assert "routing" not in repr(program).lower()
