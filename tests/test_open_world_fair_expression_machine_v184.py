from itertools import islice

import pytest

from acfqp.open_world_fair_expression_machine_v184 import (
    FairRankedPlannerSessionV184,
    FairSearchResourceExhaustedV184,
    compile_fair_ranked_world_model_v184,
    enumerate_expressions_fairly_v184,
    synthesize_fair_ranked_scalar_program_v184,
)
from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.open_world_universal_machine_v182 import MachineSynthesisRowV182


def test_v184_language_is_fair_size_ordered_and_not_a_finite_catalogue() -> None:
    rows = list(
        islice(
            enumerate_expressions_fairly_v184(input_width=2, constants=(0, 1)),
            300,
        )
    )
    sizes = [size for size, _ in rows]
    assert sizes == sorted(sizes)
    assert sizes[0] == 1
    assert max(sizes) >= 3
    assert len({repr(expression) for _, expression in rows}) == len(rows)


def test_v184_composes_an_exact_program_from_raw_rows() -> None:
    rows = tuple(
        MachineSynthesisRowV182((value,), (value % 2,), value + (value % 2))
        for value in range(8)
    )
    result = synthesize_fair_ranked_scalar_program_v184(
        rows,
        maximum_enumeration_events=20_000,
        resource_step_cap=64,
        register_count=4,
        maximum_residual_support=1,
    )
    document = result.to_document()
    assert result.residual_values == ()
    assert document["expression"] == ["ADD", ["INPUT", 0], ["INPUT", 1]]
    assert document["candidate_language_countably_infinite"] is True
    assert document["finite_candidate_catalog_used"] is False
    assert document["composed_subprogram_invented_from_raw_rows"] is True
    assert document["new_primitive_opcode_invented"] is False
    reused = synthesize_fair_ranked_scalar_program_v184(
        rows,
        maximum_enumeration_events=20_000,
        resource_step_cap=64,
        register_count=4,
        maximum_residual_support=1,
        archive=(result.program,),
    )
    assert reused.program == result.program
    assert reused.archive_reference_used is True
    assert reused.enumeration_events == 1
    assert reused.enumeration_events < result.enumeration_events


def test_v184_cap_exhaustion_is_not_reported_as_infeasibility() -> None:
    rows = tuple(
        MachineSynthesisRowV182((value,), (0,), value * value + 7)
        for value in range(8)
    )
    with pytest.raises(FairSearchResourceExhaustedV184):
        synthesize_fair_ranked_scalar_program_v184(
            rows,
            maximum_enumeration_events=1,
            resource_step_cap=64,
            maximum_residual_support=1,
        )


def test_v184_compiled_model_drives_h3_planning_without_ground_argument() -> None:
    observations = tuple(
        RawMachineTransitionV182.observe(
            occurrence_index=184,
            query_index=index,
            state=(1 + index % 4,),
            action=(index % 2,),
            successor=(index % 2,),
            terminal=index % 2 == 0,
        )
        for index in range(8)
    )
    model = compile_fair_ranked_world_model_v184(
        observations,
        maximum_enumeration_events_per_scalar=2_000,
        resource_step_cap=64,
        register_count=4,
        maximum_residual_support=1,
    )
    assert all(model.covers(row) for row in observations)
    document = model.to_document()
    assert document["layout_supplied"] is False
    assert document["whole_program_templates_supplied"] is False
    assert document["candidate_language_countably_infinite"] is True
    session = FairRankedPlannerSessionV184(model, horizon=3)
    certificate = session.certify((3,))
    assert certificate.certified is True
    assert certificate.to_document()["ground_transition_argument_present"] is False
    assert certificate.to_document()["strict_rank_decrease_proved"] is True
