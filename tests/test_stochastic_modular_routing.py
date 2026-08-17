from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp.domains.stochastic_modular_routing import (
    StochasticModularAction,
    StochasticModularStatus,
    generate_stochastic_modular_routing,
    select_seeded_stochastic_modular_outcome_v1,
)


def test_generated_robust_path_composes_modular_and_stochastic_updates() -> None:
    kernel, evidence = generate_stochastic_modular_routing(
        node_count=6,
        modulus=7,
        capacity=20,
        step_limit=7,
        mode_deltas=(1, 2, 3),
        seed=49001,
    )
    assert evidence.verified is True
    state = kernel.initial_distribution()[0][1]
    for edge_index in evidence.robust_path:
        edge = kernel.edges[edge_index]
        outcomes = kernel.step(state, StochasticModularAction(edge_index))
        assert [row.probability for row in outcomes] == [
            1 - edge.high_cost_probability,
            edge.high_cost_probability,
        ]
        assert {row.next_state.resource - state.resource for row in outcomes} == {
            0,
            edge.magnitude,
        }
        assert {
            (row.next_state.phase - state.phase) % kernel.modulus for row in outcomes
        } == {kernel.mode_deltas[edge.mode]}
        state = max(outcomes, key=lambda row: row.next_state.resource).next_state
    assert state.status is StochasticModularStatus.SUCCESS
    assert state.phase == kernel.goal_phase


def test_seeded_outcome_is_exact_and_repeatable() -> None:
    kernel, _ = generate_stochastic_modular_routing(
        node_count=6,
        modulus=7,
        capacity=20,
        step_limit=7,
        mode_deltas=(1, 2, 3),
        seed=49002,
    )
    state = kernel.initial_distribution()[0][1]
    action = kernel.actions(state)[0]
    outcomes = kernel.step(state, action)
    first, first_tape = select_seeded_stochastic_modular_outcome_v1(
        outcomes,
        seed=49002,
        episode_index=3,
        decision_index=0,
    )
    second, second_tape = select_seeded_stochastic_modular_outcome_v1(
        outcomes,
        seed=49002,
        episode_index=3,
        decision_index=0,
    )
    assert first == second
    assert first_tape == second_tape
    assert len(first_tape) == 64
    assert sum((row.probability for row in outcomes), Fraction()) == 1


def test_last_mode_requirement_changes_private_robust_path_only() -> None:
    kernel, evidence = generate_stochastic_modular_routing(
        node_count=7,
        modulus=11,
        capacity=24,
        step_limit=8,
        mode_deltas=(1, 2, 4, 5),
        seed=49003,
        require_last_mode=True,
    )
    first_edge = kernel.edges[evidence.robust_path[0]]
    assert first_edge.mode == len(kernel.mode_deltas) - 1
    assert not hasattr(kernel, "robust_path")


def test_invalid_or_terminal_action_is_rejected() -> None:
    kernel, evidence = generate_stochastic_modular_routing(
        node_count=6,
        modulus=7,
        capacity=20,
        step_limit=7,
        mode_deltas=(1, 2, 3),
        seed=49004,
    )
    state = kernel.initial_distribution()[0][1]
    illegal = next(
        StochasticModularAction(index)
        for index, edge in enumerate(kernel.edges)
        if edge.source != state.node
    )
    with pytest.raises(ValueError):
        kernel.step(state, illegal)
    for edge_index in evidence.robust_path:
        state = kernel.step(state, StochasticModularAction(edge_index))[0].next_state
    assert state.status is StochasticModularStatus.SUCCESS
    assert kernel.actions(state) == ()
