from collections import Counter
from fractions import Fraction

import pytest

from acfqp.core import QuerySpec
from acfqp.domains.g2048 import (
    D4_ELEMENTS,
    D4Transform,
    G2048Action,
    G2048Kernel,
    G2048State,
    G2048Status,
    SAFE_CHAIN_BASE_STATE,
    canonicalize_state,
    canonicalize_state_action,
    compose_d4,
    inverse_d4,
    orbit,
    safe_chain_fixture,
    safe_chain_query,
    stabilizer,
    transform_action,
    transform_outcome,
    transform_state,
)
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.enumeration import EnumerationStatus, EvaluationTier, enumerate_reachable
from acfqp.planning import solve_ground_pareto


def test_query_spec_is_exact_hashable_and_checks_v0_delta() -> None:
    state = G2048State((1, 1, 0, 0))
    query = QuerySpec.from_state(
        state,
        horizon=2,
        reward_weights=(("merge", Fraction(1)),),
        delta=Fraction(1, 20),
        normalizer=Fraction(2),
    )
    assert hash(query)
    assert query.initial_distribution == ((Fraction(1), state),)
    assert query.normalizer == 2
    assert query.normalizer_value == 2
    assert query.normalizer_proof_id == "kernel.reward_upper_bound.v1"
    with pytest.raises(ValueError, match="delta"):
        QuerySpec.from_state(state, horizon=2, delta=Fraction(1, 50))
    with pytest.raises(ValueError, match="normalizer"):
        QuerySpec.from_state(state, horizon=2, normalizer=0)
    with pytest.raises(ValueError, match="proof ID"):
        QuerySpec.from_state(
            state,
            horizon=2,
            normalizer_proof_id="",
        )

    kernel = G2048Kernel(2)
    with pytest.raises(ValueError, match="unregistered reward"):
        solve_ground_pareto(
            kernel,
            QuerySpec.from_state(
                state,
                horizon=1,
                reward_weights=(("not_registered", Fraction(1)),),
            ),
        )
    with pytest.raises(ValueError, match="unregistered goal"):
        solve_ground_pareto(
            kernel,
            QuerySpec.from_state(state, horizon=1, goal="not_registered"),
        )
    with pytest.raises(ValueError, match="below proved bound"):
        solve_ground_pareto(
            kernel,
            QuerySpec.from_state(
                state,
                horizon=2,
                reward_weights=(("merge", Fraction(1)),),
                normalizer=Fraction(1),
            ),
        )
    with pytest.raises(ValueError, match="nonnegative"):
        solve_ground_pareto(
            kernel,
            QuerySpec.from_state(
                state,
                horizon=1,
                reward_weights=(("merge", Fraction(-1)),),
            ),
        )


def test_g2048_normative_parameters_and_conditioned_initial_law() -> None:
    kernel = G2048Kernel(2)
    initial = kernel.initial_distribution()
    assert kernel.rank_cap == 6
    assert kernel.horizon == 6
    assert kernel.spawn_distribution == (
        (1, Fraction(9, 10)),
        (2, Fraction(1, 10)),
    )
    assert len(initial) == 8  # four grid edges times two equal ranks
    assert sum((probability for probability, _ in initial), Fraction(0)) == 1
    assert all(state.status is G2048Status.ACTIVE for _, state in initial)
    assert all(len(kernel.actions(state)) == 2 for _, state in initial)
    rank_one_probability = sum(
        probability
        for probability, state in initial
        if max(state.board) == 1
    )
    assert rank_one_probability == Fraction(81, 82)

    larger = G2048Kernel(3)
    assert larger.rank_cap == 8
    assert larger.horizon == 8
    assert len(larger.initial_distribution()) == 36  # 12 edges x 3 ranks
    assert sum((p for _, p in larger.spawn_distribution), Fraction(0)) == 1


def test_g2048_transition_order_reward_and_one_time_failure() -> None:
    kernel = G2048Kernel(2)
    state = G2048State((1, 1, 0, 0))
    action = G2048Action(0, 1, 0)
    outcomes = kernel.step(state, action)

    assert len(outcomes) == 6  # three empty positions x two spawn ranks
    assert sum((outcome.probability for outcome in outcomes), Fraction(0)) == 1
    assert all(outcome.feature("merge") == Fraction(1, 32) for outcome in outcomes)
    assert outcomes == kernel.step(state, action)  # deterministic ordering
    assert any(outcome.failure for outcome in outcomes)
    assert any(not outcome.failure for outcome in outcomes)
    for outcome in outcomes:
        assert outcome.failure == (outcome.next_state.status is G2048Status.FAILURE)
        if outcome.failure:
            assert kernel.actions(outcome.next_state) == ()
            assert kernel.is_terminal(outcome.next_state)

    with pytest.raises(ValueError, match="not legal"):
        kernel.step(state, G2048Action(0, 3, 0))


def test_g2048_rank_is_capped_but_emits_full_normalized_merge_reward() -> None:
    kernel = G2048Kernel(2)
    state = G2048State((6, 6, 0, 0))
    outcomes = kernel.step(state, G2048Action(0, 1, 0))
    assert all(outcome.next_state.board[0] == 6 for outcome in outcomes)
    assert all(outcome.feature("merge") == 1 for outcome in outcomes)


def test_lmb_eligibility_match_before_capacity_and_terminal_clear_bonus() -> None:
    kernel = LMBKernel(
        tile_types=(0, 0, 0),
        blockers=(frozenset(), frozenset({0}), frozenset({1})),
        type_count=1,
        capacity=2,
        max_layers=3,
    )
    state = kernel.initial_distribution()[0][1]
    assert kernel.actions(state) == (LMBAction(0),)

    state = kernel.step(state, LMBAction(0))[0].next_state
    assert state.buffer == (1,)
    assert kernel.actions(state) == (LMBAction(1),)
    state = kernel.step(state, LMBAction(1))[0].next_state
    assert state.buffer == (2,)

    final = kernel.step(state, LMBAction(2))[0]
    assert final.next_state.status is LMBStatus.SUCCESS
    assert final.next_state.buffer == (0,)  # triple clears before occupancy check
    assert not final.failure
    assert final.feature("match") == 1
    assert final.feature("terminal_clear") == 1
    assert kernel.actions(final.next_state) == ()


def test_lmb_overflow_is_absorbing_one_time_failure() -> None:
    kernel = LMBKernel(
        tile_types=(0, 0, 0, 1, 1, 1),
        blockers=(frozenset(),) * 6,
        type_count=2,
        capacity=1,
        max_layers=1,
    )
    state = kernel.initial_distribution()[0][1]
    state = kernel.step(state, LMBAction(0))[0].next_state
    failed = kernel.step(state, LMBAction(3))[0]
    assert failed.failure
    assert failed.next_state.status is LMBStatus.FAILURE
    assert failed.terminal
    assert kernel.actions(failed.next_state) == ()


def test_reverse_constructor_is_seed_deterministic_and_verified() -> None:
    arguments = dict(
        tile_count=9, type_count=3, capacity=3, max_layers=3, seed=1719
    )
    kernel, evidence = generate_solvable_lmb(**arguments)
    repeated_kernel, repeated_evidence = generate_solvable_lmb(**arguments)
    assert kernel == repeated_kernel
    assert evidence == repeated_evidence
    assert evidence.verified
    assert len(evidence.target_sequence) == kernel.tile_count
    counts = Counter(kernel.tile_types)
    assert all(count % 3 == 0 for count in counts.values())

    state = kernel.initial_distribution()[0][1]
    for tile in evidence.target_sequence:
        assert LMBAction(tile) in kernel.actions(state)
        state = kernel.step(state, LMBAction(tile))[0].next_state
    assert state.status is LMBStatus.SUCCESS
    assert not any(state.buffer)


def test_enumeration_is_exact_deterministic_and_checks_probability_mass() -> None:
    kernel = G2048Kernel(2)
    first = enumerate_reachable(kernel, horizon=1)
    second = enumerate_reachable(kernel, horizon=1)
    assert first == second
    assert first.status is EnumerationStatus.EXACT
    assert first.evaluation_tier is EvaluationTier.EXACT_SOUND
    assert first.complete
    assert len(first.layers) == 2
    assert first.transitions
    assert all(
        sum((outcome.probability for outcome in record.outcomes), Fraction(0)) == 1
        for record in first.transitions
    )


def test_state_cap_is_explicit_stress_only_and_never_exact_sound() -> None:
    result = enumerate_reachable(G2048Kernel(2), horizon=0, state_cap=7)
    assert result.status is EnumerationStatus.STATE_CAP_EXCEEDED
    assert result.evaluation_tier is EvaluationTier.STRESS_ONLY
    assert not result.complete
    assert result.state_count == 7
    assert result.state_count_lower_bound == 8


def test_g2048_d4_group_canonicalization_and_kernel_automorphism() -> None:
    kernel, _ = safe_chain_fixture()
    state = SAFE_CHAIN_BASE_STATE
    safe_action = G2048Action(0, 1, 0)

    assert D4_ELEMENTS[0] is D4Transform.IDENTITY
    assert len(D4_ELEMENTS) == 8
    for transform in D4_ELEMENTS:
        inverse = inverse_d4(transform)
        assert compose_d4(inverse, transform) is D4Transform.IDENTITY
        assert compose_d4(transform, inverse) is D4Transform.IDENTITY

        transformed_state = transform_state(state, transform)
        transformed_action = transform_action(safe_action, transform)
        assert transformed_action in kernel.actions(transformed_state)
        transported = Counter(
            transform_outcome(outcome, transform)
            for outcome in kernel.step(state, safe_action)
        )
        direct = Counter(kernel.step(transformed_state, transformed_action))
        assert transported == direct

    representative, to_representative = canonicalize_state(state)
    assert transform_state(state, to_representative) == representative
    assert stabilizer(state) == (D4Transform.IDENTITY,)
    assert len(stabilizer(G2048State((1, 1, 1, 1)))) == 8
    canonical_pair = canonicalize_state_action(state, safe_action)[:2]
    for transform in D4_ELEMENTS:
        image = transform_state(state, transform)
        image_action = transform_action(safe_action, transform)
        assert canonicalize_state(image)[:1] == (representative,)
        assert canonicalize_state_action(image, image_action)[:2] == canonical_pair


def test_safe_chain_query_has_canonical_eight_state_d4_orbit() -> None:
    kernel, query = safe_chain_fixture()
    expected_orbit = orbit(SAFE_CHAIN_BASE_STATE)
    assert len(expected_orbit) == 8
    assert query.initial_distribution == tuple(
        (Fraction(1, 8), state) for state in expected_orbit
    )
    assert sum((mass for mass, _ in query.initial_distribution), Fraction(0)) == 1
    assert query.horizon == 2
    assert query.delta == Fraction(1, 20)
    assert query.normalizer == 2
    assert query.normalizer_proof_id == (
        "g2048.canonical.merge_le_1_per_step.total_le_h.v1"
    )
    assert query.reward_weights == (("merge", Fraction(1)),)

    # Input order is a query concern and is canonicalized before QuerySpec
    # construction; it cannot perturb the structural key or query value object.
    reversed_query = safe_chain_query(
        kernel, initial_distribution=reversed(query.initial_distribution)
    )
    assert reversed_query == query
    structural = kernel.structural_key()
    assert structural["fixture_key"] == "g2048_select_safe_chain_2x2_v0"
    assert structural["spawn_distribution"] == (
        (1, Fraction(99, 100)),
        (2, Fraction(1, 100)),
    )
    assert "rho0" not in structural
    assert "delta" not in structural
    assert "reward_weights" not in structural


def _survival_after_fixed_first_action(
    kernel: G2048Kernel,
    state: G2048State,
    first_action: G2048Action,
) -> Fraction:
    survival = Fraction(0)
    for first_outcome in kernel.step(state, first_action):
        if first_outcome.failure:
            continue
        second_state = first_outcome.next_state
        second_survival = max(
            (
                sum(
                    (
                        outcome.probability
                        for outcome in kernel.step(second_state, action)
                        if not outcome.failure
                    ),
                    Fraction(0),
                )
                for action in kernel.actions(second_state)
            ),
            default=Fraction(0),
        )
        survival += first_outcome.probability * second_survival
    return survival


def test_safe_chain_j0_exact_golden_and_wrong_survivor() -> None:
    kernel, query = safe_chain_fixture()
    result = solve_ground_pareto(kernel, query)
    assert result.feasible
    assert result.selected is not None
    assert result.selected.failure_probability == Fraction(99, 5000)
    assert 1 - result.selected.failure_probability == Fraction(4901, 5000)
    assert result.selected.expected_reward == Fraction(3, 64)

    base_safe = G2048Action(0, 1, 0)
    base_wrong = G2048Action(0, 1, 1)
    weighted_wrong_survival = Fraction(0)
    for initial_mass, state in query.initial_distribution:
        matching_transform = next(
            transform
            for transform in D4_ELEMENTS
            if transform_state(SAFE_CHAIN_BASE_STATE, transform) == state
        )
        safe_action = transform_action(base_safe, matching_transform)
        wrong_action = transform_action(base_wrong, matching_transform)
        assert result.selected.policy.action(state, 2) == safe_action
        assert _survival_after_fixed_first_action(kernel, state, safe_action) == Fraction(
            4901, 5000
        )
        wrong_survival = _survival_after_fixed_first_action(kernel, state, wrong_action)
        assert wrong_survival == Fraction(1, 10000)
        weighted_wrong_survival += initial_mass * wrong_survival
    assert weighted_wrong_survival == Fraction(1, 10000)
