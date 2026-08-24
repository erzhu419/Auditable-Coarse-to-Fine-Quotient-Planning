from __future__ import annotations

import hashlib

from acfqp.open_world_compiled_model_v181r2 import (
    compile_world_model_v181r2,
)
from acfqp.open_world_transition_oracle_v181 import RawTransitionObservationV181


def _rows() -> tuple[RawTransitionObservationV181, ...]:
    rows = []
    index = 0
    for state0 in range(2):
        for state1 in range(3):
            state = (state0, state1, state0 + 1, 0)
            action = (state0,)
            for residual in (0, 1):
                successor = (
                    state[0],
                    (state[1] + residual) % 3,
                    state[2],
                    state[3],
                )
                observation_id = hashlib.sha256(str(index).encode()).hexdigest()
                rows.append(
                    RawTransitionObservationV181(
                        0,
                        index,
                        state,
                        action,
                        successor,
                        successor[3] == 1,
                        observation_id,
                    )
                )
                index += 1
    return tuple(rows)


def test_compiler_retains_two_point_cyclic_support_and_generic_dependencies() -> None:
    model = compile_world_model_v181r2(
        _rows(),
        maximum_enumeration_events_per_expression=200_000,
    )
    document = model.to_document()
    assert document["schema"] == "acfqp.open_world_compiled_program.v181r2"
    assert document["cyclic_residual_carrier_derived_from_observed_coordinate"] is True
    assert document["signed_wraparound_residual_inflation_used"] is False
    assert model.coordinates[1].exact_on_source is False
    assert model.coordinates[1].residual_values == (0, 1)
    assert model.coordinates[1].residual_modulus == 3
    for row in _rows():
        assert row.successor in model.predict_support(row.state, row.action)
        assert model.terminal(row.successor) is row.terminal


def test_compiled_model_rejects_incompatible_opaque_schema() -> None:
    model = compile_world_model_v181r2(
        _rows(),
        maximum_enumeration_events_per_expression=200_000,
    )
    try:
        model.predict_support((0,) * (model.state_width + 1), (0,))
    except Exception as error:
        assert type(error).__name__ == "OpenWorldCompiledModelV181Error"
    else:  # pragma: no cover
        raise AssertionError("incompatible schema was accepted")
