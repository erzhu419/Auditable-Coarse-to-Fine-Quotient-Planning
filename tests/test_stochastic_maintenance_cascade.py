from __future__ import annotations

from acfqp.domains.stochastic_maintenance_cascade import (
    MaintenanceCascadeAction,
    MaintenanceCascadeStatus,
    generate_stochastic_maintenance_cascade,
    select_seeded_maintenance_cascade_outcome_v1,
)


def test_generated_maintenance_cascade_has_a_robust_success_path() -> None:
    kernel, evidence = generate_stochastic_maintenance_cascade(
        zone_count=9, repair_base=6, seed=520_011
    )
    state = kernel.initial_distribution()[0][1]
    for task in evidence.robust_task_path:
        outcomes = kernel.step(state, MaintenanceCascadeAction(task))
        assert len(outcomes) == 2
        state = max(outcomes, key=lambda row: row.next_state.hazard).next_state
    assert state.status is MaintenanceCascadeStatus.SUCCESS


def test_seeded_maintenance_tape_is_replayable() -> None:
    kernel, evidence = generate_stochastic_maintenance_cascade(
        zone_count=8, repair_base=5, seed=520_013
    )
    state = kernel.initial_distribution()[0][1]
    outcomes = kernel.step(state, MaintenanceCascadeAction(evidence.robust_task_path[0]))
    first, tape_a = select_seeded_maintenance_cascade_outcome_v1(
        outcomes, seed=520_013, episode_index=2, decision_index=0
    )
    second, tape_b = select_seeded_maintenance_cascade_outcome_v1(
        outcomes, seed=520_013, episode_index=2, decision_index=0
    )
    assert first == second
    assert tape_a == tape_b
