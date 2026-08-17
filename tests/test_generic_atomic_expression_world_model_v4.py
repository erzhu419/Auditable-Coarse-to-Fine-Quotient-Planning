from __future__ import annotations

from collections import deque

import pytest

from acfqp import construction_k7_template_free_preregistration_v48 as v48_pre
from acfqp.domains.stochastic_modular_routing import (
    StochasticModularAction,
    StochasticModularStatus,
    generate_stochastic_modular_routing,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
    GenericAtomicExpressionWorldModelV4Error,
    derive_atomic_dependency_support_v4,
    execute_generic_atomic_support_v4,
    missing_relation_values_v4,
    plan_generic_atomic_program_v4,
    synthesize_generic_atomic_program_v4,
    target_binding_from_initial_vector_v4,
)


MODE_TOKENS = (8001, 8009, 8021, 8039)
CLASS_TOKENS = (8101, 8111, 8117)
STATUS_TOKENS = {"A": 9001, "F": 9007, "S": 9011}
PROGRAM_DOMAIN = v48_pre.FUTURE_DOMAINS["program"]


def _interface(seed, kernel):
    node_tokens = tuple(seed * 100 + index for index in range(kernel.node_count))
    catalogue = tuple(
        FlatRawActionV4(
            index,
            (
                node_tokens[edge.source],
                node_tokens[edge.destination],
                MODE_TOKENS[edge.mode],
                edge.magnitude,
                CLASS_TOKENS[edge.cost_class],
                seed * 10_000 + index,
            ),
        )
        for index, edge in enumerate(kernel.edges)
    )

    def encode(state):
        return (
            node_tokens[state.node],
            state.phase,
            state.resource,
            state.steps,
            STATUS_TOKENS[
                "A"
                if state.status is StochasticModularStatus.ACTIVE
                else "S"
                if state.status is StochasticModularStatus.SUCCESS
                else "F"
            ],
            kernel.modulus,
            kernel.capacity,
            kernel.goal_phase,
            node_tokens[kernel.goal_node],
        )

    return catalogue, encode


def _observations(occurrence, seed):
    kernel, witness = generate_stochastic_modular_routing(
        node_count=6,
        modulus=7,
        capacity=20,
        step_limit=7,
        mode_deltas=(1, 2, 3),
        seed=seed,
    )
    del witness
    catalogue, encode = _interface(seed, kernel)
    initial = kernel.initial_distribution()[0][1]
    queue = deque([initial])
    seen = {initial}
    rows = []
    while queue:
        state = queue.popleft()
        legal = kernel.actions(state)
        for action in legal:
            for outcome in kernel.step(state, action):
                successor = outcome.next_state
                legal_after = kernel.actions(successor)
                rows.append(
                    FlatRawTransitionV4(
                        occurrence,
                        len(rows),
                        encode(state),
                        tuple(item.edge for item in legal),
                        catalogue[action.edge],
                        encode(successor),
                        tuple(item.edge for item in legal_after),
                        None
                        if legal_after
                        else successor.status is StochasticModularStatus.SUCCESS,
                    )
                )
                if successor.status is StochasticModularStatus.ACTIVE and successor not in seen:
                    seen.add(successor)
                    queue.append(successor)
    return kernel, catalogue, encode, tuple(rows)


@pytest.fixture(scope="module")
def learned():
    first = _observations(100, 49011)
    second = _observations(101, 49012)
    rows = (*first[3], *second[3])
    program = synthesize_generic_atomic_program_v4(
        rows,
        {100: first[1], 101: second[1]},
        program_domain=PROGRAM_DOMAIN,
    )
    return program, first, second


def test_v4_composes_new_modular_and_stochastic_program_without_patterns(learned) -> None:
    program, first, second = learned
    assert program["whole_program_template_count"] == 0
    assert program["specialized_discovery_pattern_count"] == 0
    assert program["status"] == "GENERIC_ATOMIC_EXPRESSIONS_COMPOSED_WITHOUT_FAMILY_PATTERN"
    assert "E06" in program["used_opcode_names"]
    assert "E07" in program["used_opcode_names"]
    assert "E12" in program["used_opcode_names"]
    assert program["raw_transition_count"] == len(first[3]) + len(second[3])
    assert all(row["minimum_residual_error_count"] == 0 for row in program["candidate_evaluations"])
    assert "discover_set_vector" not in repr(program)
    assert "discover_scalar_support" not in repr(program)
    assert "discover_modular_relation" not in repr(program)


def test_v4_replays_every_observed_successor_support(learned) -> None:
    program, first, second = learned
    bindings = {row["occurrence"]: row for row in program["occurrence_bindings"]}
    for occurrence, fixture in ((100, first), (101, second)):
        catalogue = {row.key: row for row in fixture[1]}
        for row in fixture[3]:
            support = execute_generic_atomic_support_v4(
                program,
                row.pre,
                catalogue[row.action.key],
                bindings[occurrence],
            )
            assert row.post in support


def test_v4_derives_anonymous_dependency_support_by_exact_deletion(learned) -> None:
    program, first, second = learned
    support = derive_atomic_dependency_support_v4(
        program,
        (*first[3], *second[3]),
        {100: first[1], 101: second[1]},
        support_domain=v48_pre.FUTURE_DOMAINS["support"],
    )
    assert support["all_retained_dependencies_failed_single_deletion"] is True
    assert support["minimal_observed_dependency_signature"]
    assert support["predeclared_semantic_support_names"] == []
    assert len(support["dependency_support_id"]) == 64


def test_v4_target_missing_relation_requires_local_overlay_then_plans(learned) -> None:
    program, _first, _second = learned
    kernel, witness = generate_stochastic_modular_routing(
        node_count=7,
        modulus=11,
        capacity=24,
        step_limit=8,
        mode_deltas=(1, 2, 4, 5),
        seed=49013,
        require_last_mode=True,
    )
    catalogue, encode = _interface(49013, kernel)
    initial_state = kernel.initial_distribution()[0][1]
    source_binding = program["occurrence_bindings"][0]
    required_relations = {
        name: rows
        for name, rows in source_binding["relations"].items()
        if any(name in repr(row["expression"]) for row in program["compiled_assignments"])
    }
    binding = target_binding_from_initial_vector_v4(
        program,
        encode(initial_state),
        base_relations=required_relations,
        terminal_tokens=STATUS_TOKENS,
    )
    first_action_key = witness.robust_path[0]
    missing = missing_relation_values_v4(
        program,
        catalogue[first_action_key],
        binding,
    )
    assert len(missing) == 1
    relation_name, relation_value = missing[0]
    assert relation_value == MODE_TOKENS[-1]
    overlay = {relation_name: {relation_value: kernel.mode_deltas[-1]}}
    plan, evaluations, peak = plan_generic_atomic_program_v4(
        program,
        encode(initial_state),
        catalogue,
        binding,
        relation_overlay=overlay,
    )
    assert plan
    assert evaluations > 0
    assert peak > 0
    selected = plan[0]
    predicted = execute_generic_atomic_support_v4(
        program,
        encode(initial_state),
        catalogue[selected],
        binding,
        relation_overlay=overlay,
    )
    actual = {
        encode(row.next_state)
        for row in kernel.step(initial_state, StochasticModularAction(selected))
    }
    assert set(predicted) == actual


def test_v4_rejects_missing_terminal_classes() -> None:
    kernel, catalogue, _encode, rows = _observations(200, 49014)
    del kernel
    active_only = tuple(row for row in rows if row.terminal_acceptance_after is None)
    with pytest.raises(GenericAtomicExpressionWorldModelV4Error):
        synthesize_generic_atomic_program_v4(
            active_only,
            {200: catalogue},
            program_domain=PROGRAM_DOMAIN,
        )
