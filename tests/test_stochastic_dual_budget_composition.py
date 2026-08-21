from acfqp.domains.stochastic_dual_budget_composition import (
    DualBudgetAction,
    DualBudgetStatus,
    generate_stochastic_dual_budget_composition,
)


def test_dual_budget_robust_path_and_higher_order_checksum():
    kernel, evidence = generate_stochastic_dual_budget_composition(
        stage_count=7, seed=1_031_001
    )
    state = kernel.initial_distribution()[0][1]
    previous_checksum = state.checksum
    for key in evidence.robust_rule_path:
        rule = kernel.rules[key]
        outcomes = kernel.step(state, DualBudgetAction(key))
        state = max(outcomes, key=lambda row: row.next_state.hazard).next_state
        assert state.checksum == (
            previous_checksum
            + (state.reserve - rule.reserve_increment)
            + rule.primary_increment * rule.checksum_multiplier
        ) % kernel.checksum_modulus
        previous_checksum = state.checksum
    assert state.status is DualBudgetStatus.SUCCESS
