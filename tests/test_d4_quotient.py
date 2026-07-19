from collections import defaultdict
from fractions import Fraction

import pytest

from acfqp.core import Outcome
from acfqp.domains.g2048 import (
    D4_ELEMENTS as DOMAIN_D4_ELEMENTS,
    D4Transform as DomainD4Transform,
    G2048Status,
    inverse_d4,
    safe_chain_fixture,
    transform_action,
    transform_state,
)
from acfqp.symmetry import (
    D4_ELEMENTS,
    D4Transform,
    ExactD4QuotientInvariantViolation,
    FiniteGroupAction,
    OrbitCellKind,
    build_state_time_d4_quotient,
    build_validate_solve_d4,
    solve_exact_d4_quotient,
    validate_d4_quotient,
)


def _safe_chain_group(kernel):
    return FiniteGroupAction(
        elements=D4_ELEMENTS,
        transform_state=lambda element, state: transform_state(
            state, element, kernel.size
        ),
        transform_action=lambda element, action: transform_action(
            action, element, kernel.size
        ),
        inverse=inverse_d4,
        state_key=lambda state: repr((state.board, state.status.value)),
        action_key=repr,
    )


def test_symmetry_package_reuses_the_single_authoritative_d4_registry() -> None:
    assert D4Transform is DomainD4Transform
    assert D4_ELEMENTS is DOMAIN_D4_ELEMENTS
    assert tuple(element.value for element in D4_ELEMENTS) == (
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "reflect",
        "reflect_rotate_90",
        "reflect_rotate_180",
        "reflect_rotate_270",
    )


def test_exact_state_time_d4_quotient_build_validate_solve_and_lift() -> None:
    kernel, query = safe_chain_fixture()
    group = _safe_chain_group(kernel)

    report = build_validate_solve_d4(
        kernel,
        query,
        group,
        is_failure=lambda state: state.status is G2048Status.FAILURE,
    )

    assert report.validation.exact
    assert report.validation.representative_independent
    assert report.validation.zero_width_exact_model
    assert report.validation.automorphism_exact
    assert report.validation.canonicalizer_choice_independent
    assert report.validation.distinct_uniform_concretizer
    assert report.validation.horizons_separated
    assert report.validation.failure_cells_unified
    assert report.validation.terminal_nonterminal_separated
    assert all(width.zero for width in report.envelope_widths)

    # The exact quotient and its stochastic K_x lift reproduce the J0 optimum.
    assert report.abstract_selected_policy is not None
    assert report.lifted_ground_policy is not None
    assert report.ground_selected_policy is not None
    assert report.abstract_value == report.lifted_value == report.ground_value == Fraction(3, 64)
    assert report.abstract_risk == report.lifted_risk == report.ground_risk == Fraction(
        99, 5000
    )
    assert report.delta_action == 0
    assert report.all_state_time_values_exact
    assert len(report.state_time_value_checks) == len(report.quotient.assignments)
    assert all(check.exact_match for check in report.state_time_value_checks)
    assert all(check.frontier_exact for check in report.state_time_value_checks)
    assert all(
        check.unconstrained_value_exact for check in report.state_time_value_checks
    )
    assert all(
        check.constrained_result_exact for check in report.state_time_value_checks
    )
    assert all(
        check.abstract_unconstrained_value
        == check.lifted_unconstrained_value
        == check.ground_unconstrained_value
        for check in report.state_time_value_checks
    )

    expected_state_checks = len(report.quotient.assignments) * len(D4_ELEMENTS)
    expected_action_checks = sum(
        len(kernel.actions(assignment.state)) * len(D4_ELEMENTS)
        for assignment in report.quotient.assignments
        if assignment.remaining > 0 and not kernel.is_terminal(assignment.state)
    )
    assert len(report.quotient.state_automorphism_checks) == expected_state_checks
    assert len(report.quotient.automorphism_checks) == expected_action_checks
    assert report.validation.automorphism_check_count == (
        expected_state_checks + expected_action_checks
    )
    assert all(check.passed for check in report.quotient.state_automorphism_checks)
    assert all(check.legal_action_set_preserved for check in report.quotient.state_automorphism_checks)
    assert all(check.terminal_semantics_preserved for check in report.quotient.state_automorphism_checks)
    assert all(check.failure_semantics_preserved for check in report.quotient.state_automorphism_checks)
    assert all(check.passed for check in report.quotient.automorphism_checks)

    ground_action_count = sum(
        len(kernel.actions(assignment.state))
        for assignment in report.quotient.assignments
        if assignment.remaining > 0 and not kernel.is_terminal(assignment.state)
    )
    assert report.compression.ground_state_time_count == len(report.quotient.assignments)
    assert report.compression.quotient_state_time_count == len(report.state_time_orbits)
    assert report.compression.ground_legal_action_count == ground_action_count
    assert report.compression.semantic_action_orbit_count == len(report.action_orbits)
    assert report.compression.state_compression_ratio == Fraction(
        len(report.quotient.assignments), len(report.state_time_orbits)
    )
    assert report.compression.action_compression_ratio == Fraction(
        ground_action_count, len(report.action_orbits)
    )
    assert report.compression.ground_state_time_count > (
        report.compression.quotient_state_time_count
    )
    assert report.compression.ground_legal_action_count > (
        report.compression.semantic_action_orbit_count
    )
    assert report.compression.strict_state_compression
    assert report.compression.strict_action_compression

    # h is part of every quotient cell and never silently merged.
    by_state = defaultdict(set)
    for assignment in report.quotient.assignments:
        by_state[assignment.state].add(assignment.cell_id.remaining)
        assert assignment.remaining == assignment.cell_id.remaining
    by_orbit_key = defaultdict(set)
    for orbit in report.state_time_orbits:
        by_orbit_key[
            (orbit.cell_id.kind, orbit.cell_id.representative_key)
        ].add(orbit.cell_id.remaining)
    assert any(len(horizons) > 1 for horizons in by_orbit_key.values())

    # All failure boards reached at one h are intentionally one absorbing F_h.
    failure_cells = [orbit for orbit in report.state_time_orbits if orbit.failure]
    assert failure_cells
    assert len({orbit.cell_id.remaining for orbit in failure_cells}) == len(failure_cells)
    assert all(orbit.terminal for orbit in failure_cells)
    assert all(orbit.cell_id.kind is OrbitCellKind.FAILURE for orbit in failure_cells)
    assert all(
        state.status is G2048Status.FAILURE
        for orbit in failure_cells
        for state in orbit.members
    )
    horizon_terminal_orbits = [
        orbit
        for orbit in report.state_time_orbits
        if orbit.cell_id.remaining == 0 and not orbit.failure
    ]
    assert horizon_terminal_orbits
    assert all(orbit.terminal for orbit in horizon_terminal_orbits)
    assert all(
        orbit.cell_id.kind is OrbitCellKind.TERMINAL
        for orbit in horizon_terminal_orbits
    )


def test_stabilizer_action_orbits_use_distinct_uniform_inverse_actions() -> None:
    kernel, query = safe_chain_fixture()
    group = _safe_chain_group(kernel)
    quotient = build_state_time_d4_quotient(
        kernel,
        query,
        group,
        is_failure=lambda state: state.status is G2048Status.FAILURE,
    )

    for action_orbit in quotient.action_orbits:
        expected = {
            transform_action(action_orbit.canonical_action, element, kernel.size)
            for element in action_orbit.stabilizer
        }
        assert set(action_orbit.representative_actions) == expected
    assert quotient.canonicalizer_choice_checks
    assert all(check.passed for check in quotient.canonicalizer_choice_checks)
    assert all(
        check.transporter_choices_checked > 0
        for check in quotient.canonicalizer_choice_checks
    )

    nontrivial = [
        record for record in quotient.concretizations if len(record.action_distribution) > 1
    ]
    assert nontrivial, "safe-chain closure must exercise a nontrivial stabilizer K_x"
    for record in nontrivial:
        actions = [action for _, action in record.action_distribution]
        probabilities = [probability for probability, _ in record.action_distribution]
        assert len(actions) == len(set(actions))
        assert probabilities == [Fraction(1, len(actions))] * len(actions)
        assert sum(probabilities, Fraction(0)) == 1
        assert set(actions) <= set(kernel.actions(record.state))
        assert len(record.transporters_to_representative) >= len(actions)


class _OrientationBiasedKernel:
    """Deliberately violates D4 reward equivariance without changing its bound."""

    def __init__(self, base):
        self.base = base

    @property
    def horizon(self):
        return self.base.horizon

    @property
    def registered_reward_features(self):
        return self.base.registered_reward_features

    @property
    def registered_goals(self):
        return self.base.registered_goals

    def reward_upper_bound(self, horizon, raw_weights, goal):
        return self.base.reward_upper_bound(horizon, raw_weights, goal)

    def initial_distribution(self):
        return self.base.initial_distribution()

    def actions(self, state):
        return self.base.actions(state)

    def is_terminal(self, state):
        return self.base.is_terminal(state)

    def step(self, state, action):
        outcomes = self.base.step(state, action)
        if action.survivor != 0:
            return outcomes
        return tuple(
            Outcome(
                outcome.probability,
                outcome.next_state,
                (("merge", Fraction(0)),),
                failure=outcome.failure,
                terminal=outcome.terminal,
            )
            for outcome in outcomes
        )


def test_representative_independence_detects_orientation_biased_kernel() -> None:
    base, query = safe_chain_fixture()
    kernel = _OrientationBiasedKernel(base)
    quotient = build_state_time_d4_quotient(
        kernel,
        query,
        _safe_chain_group(base),
        is_failure=lambda state: state.status is G2048Status.FAILURE,
    )
    validation = validate_d4_quotient(quotient)

    assert not validation.representative_independent
    assert not validation.zero_width_exact_model
    assert any(not width.zero for width in validation.envelope_widths)
    with pytest.raises(ExactD4QuotientInvariantViolation) as captured:
        solve_exact_d4_quotient(kernel, query, quotient)
    assert captured.value.status == "EXACT_D4_QUOTIENT_INVARIANT_VIOLATION"
