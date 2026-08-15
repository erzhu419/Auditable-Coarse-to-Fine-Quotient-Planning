from __future__ import annotations

from acfqp.generic_bytecode_world_model_v2 import (
    RawActionV1,
    bind_scalar_categorical_target_v2,
    derive_compiled_dependency_support_v2,
    execute_scalar_categorical_bytecode_v2,
    execute_vector_set_bytecode_v2,
)
from acfqp.phase3e_ids import CONSTRUCTION_K7_GENERIC_LOCAL_DISTINCTION_V47R1_DOMAIN


def test_v2_binds_all_scalar_state_registers_and_executes_raw_residual() -> None:
    actions = (
        RawActionV1(0, (10, 11, 1, 20, 100)),
        RawActionV1(1, (10, 12, 2, 21, 101)),
        RawActionV1(2, (11, 13, 1, 20, 102)),
        RawActionV1(3, (12, 13, 2, 21, 103)),
    )
    binding = bind_scalar_categorical_target_v2((10, 0, 900, 15), (0, 1), actions)
    assert binding["state_roles"] == {"R0": 0, "R1": 1, "R2": 3, "R3": 2}
    assert binding["all_target_state_registers_compiled"] is True
    successor = execute_scalar_categorical_bytecode_v2(
        (10, 0, 0),
        actions[1],
        binding,
        pre_vector=(10, 0, 900, 15),
        post_vector=(12, 2, 900, 15),
    )
    assert successor == (12, 2, 0)


def test_v2_executes_vector_set_vm_without_typed_adapter_state() -> None:
    action = RawActionV1(0, (1, 0, 10, 1000))
    binding = {
        "action_roles": {"A0": 0, "A1": 1, "A2": 2},
        "numeric_literals": {"N0": 3, "N1": 7},
        "group_values": [10, 20],
        "capacity_value": 2,
    }
    assert execute_vector_set_bytecode_v2((0, (0, 0), 0), action, binding) == (
        1,
        (1, 0),
        0,
    )


def test_v2_support_signature_is_derived_from_compiled_registers() -> None:
    support = derive_compiled_dependency_support_v2(
        {"compiled_bytecode": [["B00", "O02", "A1"], ["B01", "O08", "R1", "N0"]]},
        support_domain=CONSTRUCTION_K7_GENERIC_LOCAL_DISTINCTION_V47R1_DOMAIN,
    )
    assert support["predeclared_semantic_support_names"] == []
    assert [row["compiled_register"] for row in support["support_rows"]] == [
        "A1",
        "N0",
        "R1",
    ]
