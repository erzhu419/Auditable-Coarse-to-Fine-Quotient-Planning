from __future__ import annotations

from acfqp.domains.modular_walk import ModularWalkAction, ModularWalkStatus, generate_modular_walk


def test_generated_modular_walk_has_a_verified_successful_path() -> None:
    kernel, evidence = generate_modular_walk(
        node_count=7,
        modulus=7,
        step_limit=8,
        mode_deltas=(1, 2, 3, 4),
        seed=19,
        require_last_mode=True,
    )
    assert evidence.verified is True
    assert kernel.edges[evidence.successful_path[0]].mode == 3
    state = kernel.initial_distribution()[0][1]
    for edge in evidence.successful_path:
        state = kernel.step(state, ModularWalkAction(edge))[0].next_state
    assert state.status is ModularWalkStatus.SUCCESS

