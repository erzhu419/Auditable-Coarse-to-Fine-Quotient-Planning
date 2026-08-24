from __future__ import annotations

import pytest

from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.open_world_ranked_machine_v183 import (
    certify_ranked_termination_v183,
    compile_ranked_machine_world_model_v183,
    execute_ranked_program_v183,
)
from acfqp.open_world_ranked_machine_planner_v183 import (
    RankedMachinePlannerSessionV183,
)
from acfqp.open_world_universal_machine_v182 import (
    CONST,
    DECJZ,
    HALT,
    INC,
    JUMP,
    READ,
)


DOUBLE = (
    (READ, 0, 0),
    (CONST, 1, 0),
    (DECJZ, 0, 6, 3),
    (INC, 1),
    (INC, 1),
    (JUMP, 2),
    (HALT, 1),
)
NONHALTING = (
    (JUMP, 0),
    (HALT, 0),
)
RANK_REWRITTEN = (
    (READ, 0, 0),
    (DECJZ, 0, 4, 2),
    (INC, 0),
    (JUMP, 1),
    (HALT, 0),
)


def test_ranked_loop_proves_unbounded_input_totality_without_carrier_enumeration() -> None:
    certificate = certify_ranked_termination_v183(
        DOUBLE,
        register_count=3,
        input_width=2,
    )
    assert certificate is not None
    document = certificate.to_document()
    assert document["total_for_all_finite_nonnegative_inputs_of_frozen_width"] is True
    assert document["finite_carrier_enumeration_used"] is False
    assert document["general_program_termination_decided"] is False
    assert len(document["loop_proofs"]) == 1
    for value in (0, 1, 7, 100):
        result = execute_ranked_program_v183(
            DOUBLE,
            state=(value,),
            action=(0,),
            register_count=3,
            resource_step_cap=1_000,
        )
        assert result.halted is True
        assert result.output == 2 * value


def test_ranked_checker_rejects_unranked_or_rewritten_cycles() -> None:
    assert certify_ranked_termination_v183(
        NONHALTING,
        register_count=3,
        input_width=2,
    ) is None
    assert certify_ranked_termination_v183(
        RANK_REWRITTEN,
        register_count=3,
        input_width=2,
    ) is None


def test_runtime_cap_is_distinct_from_semantic_nontermination() -> None:
    result = execute_ranked_program_v183(
        DOUBLE,
        state=(100,),
        action=(0,),
        register_count=3,
        resource_step_cap=10,
    )
    assert result.halted is False
    assert result.resource_cap_exhausted is True


def test_raw_rows_compile_to_anonymous_ranked_world_model() -> None:
    observations = []
    query = 0
    # coord0 = 2*s0, coord1 = s1; terminal iff successor coord1 is zero.
    for left in (0, 1, 2, 3):
        for right in (0, 1):
            observations.append(
                RawMachineTransitionV182.observe(
                    occurrence_index=0,
                    query_index=query,
                    state=(left, right),
                    action=(0,),
                    successor=(2 * left, right),
                    terminal=right == 0,
                )
            )
            query += 1
    model = compile_ranked_machine_world_model_v183(
        observations,
        maximum_enumeration_events_per_scalar=10_000,
        resource_step_cap=256,
        maximum_loop_increment_repetitions=3,
        register_count=3,
        maximum_residual_support=1,
        archive=(DOUBLE,),
    )
    assert all(model.covers(row) for row in observations)
    assert model.predict_support((7, 1), (0,)) == ((14, 1),)
    document = model.to_document()
    assert document["all_programs_total_over_unbounded_nonnegative_input_values"] is True
    assert document["finite_carrier_enumeration_used"] is False
    assert document["general_program_termination_decided"] is False
    assert document["named_domain_family_used"] is False
    assert document["named_layout_used"] is False
    assert document["generic_ranked_program_schema_enumerated"] is True
    assert document["current_occurrence_candidate_set_finite"] is True
    assert document["domain_specific_whole_program_template_used"] is False

    planner = RankedMachinePlannerSessionV183(model, horizon=3)
    certificate = planner.certify((0, 1))
    assert certificate.certified is False
    assert certificate.failure_reason == "NO_HORIZON_CERTIFICATE"
    assert certificate.to_document()["local_ground_distinction_permitted"] is True


def test_compiler_rejects_too_few_rows() -> None:
    with pytest.raises(Exception):
        compile_ranked_machine_world_model_v183(
            [],
            maximum_enumeration_events_per_scalar=10,
            resource_step_cap=32,
            maximum_loop_increment_repetitions=1,
        )
