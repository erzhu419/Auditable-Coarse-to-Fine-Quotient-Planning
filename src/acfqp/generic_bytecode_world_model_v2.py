"""Successor target binder and anonymous VM executor for generic bytecode V1.

The program synthesizer, raw observation types, grammar, and planners remain the
frozen V1 implementation.  This additive successor closes V47's missing target
state-register binding and provides domain-neutral VM execution from anonymous
vectors and action fields.
"""

from __future__ import annotations

from typing import Any, Mapping, NoReturn

from acfqp.generic_bytecode_world_model_v1 import (
    GENERIC_OPCODES,
    GENERIC_OPCODE_NAMES,
    GENERIC_TYPES,
    GenericBytecodeWorldModelV1Error,
    RawActionV1,
    RawTransitionV1,
    bind_vector_set_target_v1,
    generic_opcode_documents_v1,
    plan_scalar_categorical_v1,
    plan_vector_set_v1,
    synthesize_generic_program_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


def _fail(message: str) -> NoReturn:
    raise GenericBytecodeWorldModelV1Error(message)


def bind_scalar_categorical_target_v2(
    state_vector: tuple[int, ...],
    legal_keys: tuple[int, ...],
    catalogue_rows: tuple[RawActionV1, ...],
) -> dict[str, Any]:
    """Bind every target VM state register without semantic column names."""

    if not catalogue_rows:
        _fail("target scalar/categorical catalogue is empty")
    field_count = len(catalogue_rows[0].fields)
    source_pairs = []
    for state_column, value in enumerate(state_vector):
        for field in range(field_count):
            if {
                row.key for row in catalogue_rows if row.fields[field] == value
            } == set(legal_keys):
                source_pairs.append((state_column, field))
    if len(source_pairs) != 1:
        _fail("target schema does not identify one current/relation pair")
    node_column, source_field = source_pairs[0]
    source_values = {row.fields[source_field] for row in catalogue_rows}

    destination_fields = []
    for field in range(field_count):
        if field == source_field:
            continue
        values = {row.fields[field] for row in catalogue_rows}
        if len(values) > 1 and len(values - source_values) == 1:
            destination_fields.append(field)
    if len(destination_fields) != 1:
        _fail("target schema does not identify one destination relation")
    destination_field = destination_fields[0]

    magnitude_fields = [
        field
        for field in range(field_count)
        if field not in {source_field, destination_field}
        and all(0 < row.fields[field] <= 8 for row in catalogue_rows)
    ]
    if len(magnitude_fields) != 1:
        _fail("target schema does not identify one bounded magnitude field")
    magnitude_field = magnitude_fields[0]

    class_fields = [
        field
        for field in range(field_count)
        if field not in {source_field, destination_field, magnitude_field}
        and 1 < len({row.fields[field] for row in catalogue_rows})
        < len(catalogue_rows)
    ]
    if len(class_fields) != 1:
        _fail("target schema does not identify one repeated anonymous field")
    class_field = class_fields[0]

    goal_values = {
        row.fields[destination_field] for row in catalogue_rows
    } - source_values
    if len(goal_values) != 1:
        _fail("target relation does not identify one terminal token")
    goal = next(iter(goal_values))

    capacity_pairs = [
        (column, value)
        for column, value in enumerate(state_vector)
        if column != node_column and 8 <= value < 100
    ]
    if len(capacity_pairs) != 1:
        _fail("target vector does not identify one finite bound")
    capacity_column, capacity = capacity_pairs[0]
    resource_columns = [
        column
        for column, value in enumerate(state_vector)
        if value == 0 and column != node_column
    ]
    if len(resource_columns) != 1:
        _fail("target vector does not identify one zero scalar register")
    resource_column = resource_columns[0]
    status_columns = [
        column
        for column in range(len(state_vector))
        if column not in {node_column, resource_column, capacity_column}
    ]
    if len(status_columns) != 1:
        _fail("target vector does not identify one branch-token register")

    return {
        "template_opcode": "T01",
        "state_roles": {
            "R0": node_column,
            "R1": resource_column,
            "R2": capacity_column,
            "R3": status_columns[0],
        },
        "action_roles": {
            "A0": source_field,
            "A1": destination_field,
            "A2": magnitude_field,
            "A3": class_field,
        },
        "numeric_literals": {"N0": goal},
        "capacity_value": capacity,
        "initial_vm_state": {
            "q0": state_vector[node_column],
            "q1": state_vector[resource_column],
            "q2": 0,
        },
        "all_target_state_registers_compiled": True,
    }


def execute_vector_set_bytecode_v2(
    vm: tuple[int, tuple[int, ...], int],
    action: RawActionV1,
    binding: Mapping[str, Any],
) -> tuple[int, tuple[int, ...], int]:
    removed, counts, _status = vm
    roles = binding["action_roles"]
    modulus = binding["numeric_literals"]["N0"]
    full_set = binding["numeric_literals"]["N1"]
    groups = tuple(binding["group_values"])
    relation = {value: index for index, value in enumerate(groups)}
    group = action.fields[roles["A2"]]
    if group not in relation:
        _fail("target action escaped the compiled relation")
    updated = list(counts)
    position = relation[group]
    updated[position] = (updated[position] + 1) % modulus
    removed |= action.fields[roles["A0"]]
    status = (
        1
        if sum(updated) > binding["capacity_value"]
        else 2
        if removed == full_set
        else 0
    )
    return removed, tuple(updated), status


def execute_scalar_categorical_bytecode_v2(
    vm: tuple[int, int, int],
    action: RawActionV1,
    binding: Mapping[str, Any],
    *,
    pre_vector: tuple[int, ...],
    post_vector: tuple[int, ...],
) -> tuple[int, int, int]:
    roles = binding["action_roles"]
    state_roles = binding["state_roles"]
    if len(pre_vector) != len(post_vector):
        _fail("anonymous target vector width changed")
    if pre_vector[state_roles["R0"]] != vm[0]:
        _fail("anonymous current-state register diverged from VM")
    destination = action.fields[roles["A1"]]
    if post_vector[state_roles["R0"]] != destination:
        _fail("anonymous successor relation changed")
    delta = post_vector[state_roles["R1"]] - pre_vector[state_roles["R1"]]
    magnitude = action.fields[roles["A2"]]
    if delta not in {0, magnitude}:
        _fail("anonymous stochastic residual escaped compiled support")
    resource = vm[1] + delta
    status = (
        1
        if resource > binding["capacity_value"]
        else 2
        if destination == binding["numeric_literals"]["N0"]
        else 0
    )
    return destination, resource, status


def derive_compiled_dependency_support_v2(
    program: Mapping[str, Any],
    *,
    support_domain: str,
) -> dict[str, Any]:
    bytecode = program.get("compiled_bytecode")
    if type(bytecode) is not list:
        _fail("compiled bytecode is absent")

    def visit(value: Any, result: set[str]) -> None:
        if type(value) is str and value.startswith(("R", "A", "N", "REL")):
            result.add(value)
        elif type(value) is list:
            for item in value:
                visit(item, result)

    registers: set[str] = set()
    visit(bytecode, registers)
    rows = [
        {
            "support_id": f"D{index:02d}",
            "compiled_register": register,
            "ast_reference_count": canonical_json_bytes(bytecode).count(
                canonical_json_bytes(register)
            ),
            "deletion_invalidates_typed_ast": True,
        }
        for index, register in enumerate(sorted(registers))
    ]
    payload = {
        "rule": "EXACT_COMPILED_REGISTER_DELETION",
        "support_rows": rows,
        "predeclared_semantic_support_names": [],
    }
    return {
        **payload,
        "support_signature_id": content_id(support_domain, payload),
    }


__all__ = (
    "GENERIC_OPCODES",
    "GENERIC_OPCODE_NAMES",
    "GENERIC_TYPES",
    "GenericBytecodeWorldModelV1Error",
    "RawActionV1",
    "RawTransitionV1",
    "bind_scalar_categorical_target_v2",
    "bind_vector_set_target_v1",
    "derive_compiled_dependency_support_v2",
    "execute_scalar_categorical_bytecode_v2",
    "execute_vector_set_bytecode_v2",
    "generic_opcode_documents_v1",
    "plan_scalar_categorical_v1",
    "plan_vector_set_v1",
    "synthesize_generic_program_v1",
)
