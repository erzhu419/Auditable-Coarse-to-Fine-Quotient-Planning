from __future__ import annotations

from collections import deque

from acfqp import construction_k7_generic_bytecode_campaign_v47r1 as predecessor
from acfqp.domains.modular_walk import (
    ModularWalkAction,
    ModularWalkStatus,
    generate_modular_walk,
)
from acfqp.generic_template_free_world_model_v3 import (
    RawActionV3,
    RawTransitionV3,
    derive_dependency_support_v3,
    initial_vm_from_vector_v3,
    plan_compiled_program_v3,
    synthesize_template_free_program_v3,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_TEMPLATE_FREE_DEPENDENCY_SUPPORT_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_TYPED_AST_PROGRAM_V48_DOMAIN,
)


def _predecessor_family(family: str):
    rows = []
    catalogues = {}
    for archive in predecessor.freeze_generic_bytecode_campaign_v47r1().to_document()["source_archives"]:
        if archive["anonymous_family"] != family:
            continue
        catalogue = tuple(
            RawActionV3(row["action_key"], tuple(row["anonymous_fields"]))
            for row in archive["anonymous_action_catalogue"]
        )
        occurrence = archive["raw_transitions"][0]["occurrence"]
        catalogues[occurrence] = catalogue
        for row in archive["raw_transitions"]:
            action = row["selected_action"]
            rows.append(
                RawTransitionV3(
                    row["occurrence"],
                    row["transition_index"],
                    tuple(row["pre_vector"]),
                    tuple(row["legal_action_keys_before"]),
                    RawActionV3(action["action_key"], tuple(action["anonymous_fields"])),
                    tuple(row["post_vector"]),
                    tuple(row["legal_action_keys_after"]),
                    row["outcome_tape_sha256"],
                )
            )
    return tuple(rows), catalogues


def test_template_free_engine_reconstructs_both_frozen_predecessor_families() -> None:
    schemas = []
    for family in ("D00", "D01"):
        rows, catalogues = _predecessor_family(family)
        program = synthesize_template_free_program_v3(
            rows,
            catalogues,
            program_domain=CONSTRUCTION_K7_TEMPLATE_FREE_TYPED_AST_PROGRAM_V48_DOMAIN,
        )
        assert program["whole_program_template_count"] == 0
        assert "selected_template_opcode" not in program
        assert "T00" not in repr(program)
        assert "T01" not in repr(program)
        schemas.append(program["vm_schema"])
    assert schemas == [
        ["INT_SET", "INT_VECTOR", "STATUS"],
        ["INT", "INT", "STATUS_SUPPORT"],
    ]


def _modular_fixture():
    kernel, _witness = generate_modular_walk(
        node_count=6,
        modulus=7,
        step_limit=7,
        mode_deltas=(1, 2, 3),
        seed=17,
    )
    nodes = tuple(9_000 + index for index in range(kernel.node_count))
    modes = (7_001, 7_003, 7_009)
    statuses = {
        ModularWalkStatus.ACTIVE: 8_101,
        ModularWalkStatus.FAILURE: 8_102,
        ModularWalkStatus.SUCCESS: 8_103,
    }
    catalogue = tuple(
        RawActionV3(
            index,
            (
                nodes[edge.source],
                nodes[edge.destination],
                modes[edge.mode],
                9_900 + index,
            ),
        )
        for index, edge in enumerate(kernel.edges)
    )

    def encode(state):
        return (
            nodes[state.node],
            state.residue,
            state.steps,
            statuses[state.status],
            kernel.modulus,
        )

    queue = deque([kernel.initial_distribution()[0][1]])
    seen = set(queue)
    rows = []
    while queue:
        state = queue.popleft()
        legal = kernel.actions(state)
        for action in legal:
            successor = kernel.step(state, action)[0].next_state
            rows.append(
                RawTransitionV3(
                    1,
                    len(rows),
                    encode(state),
                    tuple(item.edge for item in legal),
                    catalogue[action.edge],
                    encode(successor),
                    tuple(item.edge for item in kernel.actions(successor)),
                )
            )
            if successor.status is ModularWalkStatus.ACTIVE and successor not in seen:
                seen.add(successor)
                queue.append(successor)
    return kernel, catalogue, encode, tuple(rows)


def test_template_free_engine_composes_a_third_program_and_plans_with_it() -> None:
    kernel, catalogue, encode, rows = _modular_fixture()
    program = synthesize_template_free_program_v3(
        rows,
        {1: catalogue},
        program_domain=CONSTRUCTION_K7_TEMPLATE_FREE_TYPED_AST_PROGRAM_V48_DOMAIN,
    )
    assert program["vm_schema"] == ["INT", "INT", "INT", "STATUS"]
    assert program["whole_program_template_count"] == 0
    binding = program["occurrence_bindings"][0]
    vm = initial_vm_from_vector_v3(
        binding, encode(kernel.initial_distribution()[0][1])
    )
    plan, evaluations, peak = plan_compiled_program_v3(
        program, vm, catalogue, binding
    )
    assert plan
    assert evaluations > 0
    assert peak > 0
    state = kernel.initial_distribution()[0][1]
    for key in plan:
        state = kernel.step(state, ModularWalkAction(key))[0].next_state
    assert state.status is ModularWalkStatus.SUCCESS

    support = derive_dependency_support_v3(
        program,
        support_domain=CONSTRUCTION_K7_TEMPLATE_FREE_DEPENDENCY_SUPPORT_V48_DOMAIN,
    )
    assert support["predeclared_semantic_support_names"] == []
    assert support["support_rows"]

