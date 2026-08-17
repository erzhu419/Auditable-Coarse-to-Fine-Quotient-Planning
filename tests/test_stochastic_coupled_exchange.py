from __future__ import annotations

from fractions import Fraction

from acfqp.domains.stochastic_coupled_exchange import (
    CoupledExchangeAction,
    CoupledExchangeStatus,
    generate_stochastic_coupled_exchange,
    select_seeded_coupled_exchange_outcome_v1,
)


def test_generated_coupled_exchange_has_higher_order_partial_stochastic_path() -> None:
    kernel, evidence = generate_stochastic_coupled_exchange(
        stage_count=6, primary_base=2, seed=699_101
    )
    assert evidence.verified is True
    state = kernel.initial_distribution()[0][1]
    for decision, key in enumerate(evidence.robust_exchange_path):
        rule = kernel.rules[key]
        outcomes = kernel.step(state, CoupledExchangeAction(key))
        assert len(outcomes) == 2
        assert sum((row.probability for row in outcomes), Fraction()) == 1
        assert {
            row.next_state.primary for row in outcomes
        } == {state.primary + rule.primary_increment + rule.secondary_increment}
        assert len({row.next_state.risk for row in outcomes}) == 2
        state, tape = select_seeded_coupled_exchange_outcome_v1(
            outcomes, seed=699_101, episode_index=0, decision_index=decision
        )
        state = state.next_state
        assert len(tape) == 64
    assert state.status is CoupledExchangeStatus.SUCCESS


def test_changed_primary_base_produces_fresh_relation_support() -> None:
    source, _ = generate_stochastic_coupled_exchange(
        stage_count=6, primary_base=2, seed=699_101
    )
    target, _ = generate_stochastic_coupled_exchange(
        stage_count=7, primary_base=5, seed=699_301
    )
    source_values = {rule.primary_increment for rule in source.rules}
    target_values = {rule.primary_increment for rule in target.rules}
    assert target_values - source_values
    assert max(target_values - source_values) >= 10
