from __future__ import annotations

from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.open_world_total_machine_model_v182r2 import (
    certify_program_totality_v182r2,
    compile_total_machine_world_model_v182r2,
)
from acfqp.open_world_total_machine_planner_v182r2 import (
    TotalMachinePlannerSessionV182R2,
)
from acfqp.open_world_universal_machine_v182 import DECJZ, HALT, READ


def _rows() -> tuple[RawMachineTransitionV182, ...]:
    rows = []
    query = 0
    for countdown in range(5):
        for action in range(2):
            for residual in range(2):
                successor = (max(0, countdown - 1), action + 1, residual)
                rows.append(
                    RawMachineTransitionV182.observe(
                        occurrence_index=182_201,
                        query_index=query,
                        state=(countdown, 0, 0),
                        action=(action,),
                        successor=successor,
                        terminal=successor[0] == 0,
                    )
                )
                query += 1
    return tuple(rows)


def _model():
    return compile_total_machine_world_model_v182r2(
        _rows(),
        state_moduli=(6, 3, 2),
        legal_actions=((0,), (1,)),
        maximum_enumeration_events_per_scalar=5_000,
        maximum_instruction_count=3,
        maximum_execution_steps=16,
        maximum_residual_support=2,
    )


def test_v182r2_rejects_a_program_that_only_halts_on_seen_small_inputs() -> None:
    loops_until_zero = (
        (READ, 0, 0),
        (DECJZ, 0, 2, 1),
        (HALT, 0),
    )
    # It halts for the observed-looking state zero, but not for carrier value 5
    # under the deliberately small registered step budget.
    assert certify_program_totality_v182r2(
        loops_until_zero,
        state_moduli=(6,),
        legal_actions=((0,),),
        register_count=2,
        maximum_execution_steps=4,
    ) is None


def test_v182r2_compiler_certifies_every_program_over_full_carrier() -> None:
    model = _model()
    documents = [
        row.synthesis.totality.to_document() for row in model.coordinates
    ] + [model.terminal_synthesis.totality.to_document()]
    assert all(
        row["total_on_full_registered_finite_carrier"] is True
        for row in documents
    )
    assert all(row["input_count"] > 0 for row in documents)
    assert all(model.covers(row) for row in _rows())
    document = model.to_document()
    assert document["all_programs_total_on_full_registered_finite_carrier"] is True
    assert document["finite_carrier_totality_not_unbounded_totality"] is True


def test_v182r2_total_model_and_planner_cover_every_carrier_input() -> None:
    model = _model()
    for a in range(6):
        for b in range(3):
            for c in range(2):
                state = (a, b, c)
                model.terminal(state)
                for action in model.legal_actions:
                    support = model.predict_support(state, action)
                    assert support
                    assert all(
                        0 <= successor[index] < model.state_moduli[index]
                        for successor in support
                        for index in range(model.state_width)
                    )
    session = TotalMachinePlannerSessionV182R2(model, horizon=5)
    first = session.certify((3, 0, 0))
    second = session.certify((3, 0, 0))
    assert first.certified is True
    assert first.to_document()[
        "planner_consumed_only_totality_checked_compiled_world_model"
    ] is True
    assert second.persistent_cache_hit_count > 0


def test_v182r2_claim_boundary_remains_finite_and_resource_bounded() -> None:
    model = _model()
    document = model.to_document()
    assert document["finite_candidate_program_catalog_used"] is False
    assert document["language_program_length_unbounded"] is True
    assert document["occurrence_search_resource_bounded"] is True
    model_totality_documents = [
        item.synthesis.totality.to_document() for item in model.coordinates
    ]
    for row in model_totality_documents:
        assert row["total_over_unbounded_integer_inputs_claimed"] is False
        assert row["total_over_unregistered_schemas_claimed"] is False
