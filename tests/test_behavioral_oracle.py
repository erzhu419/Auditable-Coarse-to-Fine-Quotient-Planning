from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction

import pytest

from acfqp.abstraction import build_exact_behavioral_quotient
from acfqp.abstraction.oracle import (
    build_ground_oracle_table,
    oracle_partition,
    oracle_signature_atoms,
    select_oracle_partition,
)
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.core import QuerySpec
from acfqp.domains import (
    D4_ELEMENTS,
    G2048RelativeSurvivorAdapter,
    G2048RelativeSurvivorLabel,
    G2048State,
    SAFE_CHAIN_BASE_STATE,
    canonicalize_state,
    orbit,
    safe_chain_fixture,
    transform_action,
    transform_state,
)
from acfqp.domains.matching_buffer import (
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.symmetry import (
    enumerate_lmb_automorphisms,
    lmb_orbit,
    transform_lmb_action,
    transform_lmb_state,
)
from acfqp.planning import lift_semantic_policy, solve_ground_pareto


@dataclass(frozen=True)
class _G2048OracleControl:
    kernel: object
    query: QuerySpec
    bridge_query: QuerySpec
    coverage: SuiteBuildCoverage
    behavioral: object
    adapter: G2048RelativeSurvivorAdapter
    oracle_table: object
    selection: object


@pytest.fixture(scope="module")
def g2048_oracle_control() -> _G2048OracleControl:
    kernel, query = safe_chain_fixture()
    bridge_safe = orbit(SAFE_CHAIN_BASE_STATE, kernel.size)
    bridge_t = orbit(G2048State((2, 2, 2, 0)), kernel.size)
    bridge_u = orbit(G2048State((2, 2, 4, 0)), kernel.size)
    assert (len(bridge_safe), len(bridge_t), len(bridge_u)) == (8, 4, 8)
    bridge_distribution = tuple(
        sorted(
            (
                *((Fraction(3, 25), state) for state in bridge_safe),
                *((Fraction(1, 200), state) for state in bridge_t),
                *((Fraction(1, 400), state) for state in bridge_u),
            ),
            key=lambda item: (item[1].board, item[1].status.value),
        )
    )
    bridge_query = QuerySpec(
        bridge_distribution,
        horizon=1,
        reward_weights=query.reward_weights,
        goal=query.goal,
        delta=Fraction(1, 20),
        normalizer=Fraction(1),
        normalizer_proof_id=query.normalizer_proof_id,
    )
    coverage = SuiteBuildCoverage.from_queries(
        kernel, (query, bridge_query)
    )
    behavioral = build_exact_behavioral_quotient(
        kernel, coverage.covered_states
    )
    adapter = G2048RelativeSurvivorAdapter()
    table = build_ground_oracle_table(
        kernel,
        coverage.covered_states,
        adapter,
        max_horizon=2,
        reward_weights=query.reward_weights,
        goal=query.goal,
        delta=query.delta,
    )
    selection = select_oracle_partition(
        kernel,
        coverage.covered_states,
        adapter,
        table,
        (query, bridge_query),
        regret_tolerance=Fraction(1, 100),
        minimum_compression=Fraction(5),
        orbit_key=lambda state: canonicalize_state(state, kernel.size)[0],
        require_reachable_mixed_cell=True,
    )
    return _G2048OracleControl(
        kernel,
        query,
        bridge_query,
        coverage,
        behavioral,
        adapter,
        table,
        selection,
    )


@dataclass(frozen=True)
class _LMBBehavioralControl:
    kernel: object
    coverage: SuiteBuildCoverage
    behavioral: object
    automorphisms: tuple[object, ...]


@pytest.fixture(scope="module")
def lmb_behavioral_control() -> _LMBBehavioralControl:
    kernel, _ = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=2,
        seed=0,
    )
    declared_support = (
        (11, (1, 2)),
        (13, (2, 1)),
        (19, (1, 2)),
        (21, (2, 1)),
        (25, (1, 2)),
        (35, (2, 1)),
        (41, (2, 1)),
        (49, (2, 1)),
        (7, (2, 1)),
    )
    rho = tuple(
        (
            Fraction(1, len(declared_support)),
            LMBState(mask, buffer, LMBStatus.ACTIVE),
        )
        for mask, buffer in declared_support
    )
    query = QuerySpec(
        rho,
        horizon=3,
        reward_weights=(
            ("match", Fraction(1)),
            ("terminal_clear", Fraction(1)),
        ),
        goal="default",
        delta=Fraction(1, 20),
        normalizer=Fraction(4),
        normalizer_proof_id=(
            "lmb.canonical.matches_plus_clear_le_2n_over_3.v1"
        ),
    )
    coverage = SuiteBuildCoverage.from_queries(kernel, (query,))
    return _LMBBehavioralControl(
        kernel,
        coverage,
        build_exact_behavioral_quotient(kernel, coverage.covered_states),
        enumerate_lmb_automorphisms(kernel),
    )


def test_g2048_exact_behavioral_quotient_has_192_to_10_golden(
    g2048_oracle_control: _G2048OracleControl,
) -> None:
    control = g2048_oracle_control
    quotient = control.behavioral

    assert len(control.coverage.covered_states) == 192
    assert quotient.ground_state_count == 192
    assert quotient.cell_count == 10
    assert tuple(
        step.cell_count for step in quotient.refinement_trace
    ) == (2, 9, 10, 10)
    assert quotient.refinement_trace[-1].partition_signature == (
        quotient.refinement_trace[-2].partition_signature
    )
    assert all(
        len(
            {
                (
                    realization.reward_features,
                    realization.failure_probability,
                    realization.termination_probability,
                    realization.successor_probabilities,
                )
                for realization in entry.realizations
            }
        )
        == 1
        for entry in quotient.quotient_models.envelope.entries
    )


def test_g2048_relative_survivor_adapter_is_exhaustively_d4_equivariant(
    g2048_oracle_control: _G2048OracleControl,
) -> None:
    kernel = g2048_oracle_control.kernel
    adapter = g2048_oracle_control.adapter
    base_labels = {
        action.survivor: adapter.label(kernel, SAFE_CHAIN_BASE_STATE, action)
        for action in kernel.actions(SAFE_CHAIN_BASE_STATE)
    }
    assert base_labels == {
        0: G2048RelativeSurvivorLabel.TOWARD,
        1: G2048RelativeSurvivorLabel.AWAY,
    }

    for state in g2048_oracle_control.coverage.covered_states:
        if kernel.is_terminal(state):
            assert adapter.labels(kernel, state) == ()
            continue
        labels = adapter.labels(kernel, state)
        actions = tuple(kernel.actions(state))
        assert labels
        for label in labels:
            concretization = adapter.concretize(kernel, state, label)
            assert sum(
                (probability for probability, _ in concretization), Fraction(0)
            ) == 1
            assert len({action for _, action in concretization}) == len(
                concretization
            )
            assert all(
                action in actions and adapter.label(kernel, state, action) is label
                for _, action in concretization
            )

        for element in D4_ELEMENTS:
            image = transform_state(state, element, kernel.size)
            assert adapter.labels(kernel, image) == labels
            for action in actions:
                image_action = transform_action(action, element, kernel.size)
                label = adapter.label(kernel, state, action)
                assert adapter.label(kernel, image, image_action) is label
                transported = Counter(
                    {
                        transform_action(ground_action, element, kernel.size): probability
                        for probability, ground_action in adapter.concretize(
                            kernel, state, label
                        )
                    }
                )
                direct = Counter(
                    {
                        ground_action: probability
                        for probability, ground_action in adapter.concretize(
                            kernel, image, label
                        )
                    }
                )
                assert transported == direct


def test_g2048_train_only_oracle_selection_has_192_to_8_cross_d4_golden(
    g2048_oracle_control: _G2048OracleControl,
) -> None:
    control = g2048_oracle_control
    selection = control.selection

    assert len(control.coverage.covered_states) == 192
    assert len(selection.partition.cell_ids) == 8
    assert Fraction(192, 8) == 24
    active_states = tuple(
        state
        for state in control.coverage.covered_states
        if not control.kernel.is_terminal(state)
    )
    active_cells = tuple(
        cell
        for cell in selection.partition.cell_ids
        if not all(
            control.kernel.is_terminal(state)
            for state in selection.partition.members(cell)
        )
    )
    assert (len(active_states), len(active_cells)) == (68, 7)
    assert Fraction(len(active_states), len(active_cells)) == Fraction(68, 7)
    assert tuple(
        sorted(atom.atom_id for atom in selection.selected_atoms)
    ) == (
        "h1:maximum_normalized_reward",
        "h1:selected_semantic_action@delta",
    )
    assert len(selection.training_evaluations) == 2
    assert all(
        evaluation.audit.certified
        for evaluation in selection.training_evaluations
    )

    orbit_key = lambda state: canonicalize_state(state, control.kernel.size)[0]
    cross_d4_cells = tuple(
        cell
        for cell in selection.partition.cell_ids
        if len(
            {
                orbit_key(state)
                for state in selection.partition.members(cell)
            }
        )
        > 1
    )
    assert cross_d4_cells
    assert selection.reachable_mixed_cells
    assert set(selection.reachable_mixed_cells) <= set(cross_d4_cells)

    reward_atom = next(
        atom
        for atom in oracle_signature_atoms(control.oracle_table)
        if atom.atom_id == "h2:maximum_normalized_reward"
    )
    reward_partition = oracle_partition(
        control.kernel,
        control.coverage.covered_states,
        control.adapter,
        control.oracle_table,
        (reward_atom,),
    )
    for state in control.coverage.covered_states:
        if control.kernel.is_terminal(state):
            continue
        record = control.oracle_table.record(state, 2)
        cell = reward_partition.cell_of(state)
        assert dict(cell[2])[reward_atom.atom_id] == (
            record.maximum_reward / record.normalizer
        )

    bridge_evaluation = next(
        evaluation
        for evaluation in selection.training_evaluations
        if evaluation.query == control.bridge_query
    )
    bridge_lift = lift_semantic_policy(
        control.kernel,
        control.bridge_query,
        selection.partition,
        bridge_evaluation.abstract_policy,
        control.adapter,
    )
    left = G2048State((0, 2, 2, 2))
    right = G2048State((0, 2, 4, 2))
    initial_masses = dict(
        (state, mass)
        for mass, state in control.bridge_query.initial_distribution
    )
    assert initial_masses[left] == Fraction(1, 200)
    assert initial_masses[right] == Fraction(1, 400)
    lifted_states = {
        decision.state
        for decision in bridge_lift.lifted_semantic_policy.decisions
    }
    assert {left, right} <= lifted_states
    witness_cell = selection.partition.cell_of(left)
    assert selection.partition.cell_of(right) == witness_cell
    assert witness_cell in selection.reachable_mixed_cells
    assert canonicalize_state(left, control.kernel.size)[0] != (
        canonicalize_state(right, control.kernel.size)[0]
    )
    assert right not in orbit(left, control.kernel.size)
    assert bridge_lift.lifted_semantic_policy.action(left, 1) is (
        G2048RelativeSurvivorLabel.AWAY
    )
    assert bridge_lift.lifted_semantic_policy.action(right, 1) is (
        G2048RelativeSurvivorLabel.AWAY
    )

    ground = solve_ground_pareto(control.kernel, control.bridge_query)
    assert ground.selected is not None
    assert ground.selected.expected_reward == Fraction(13, 400)
    assert ground.selected.failure_probability == Fraction(199, 5000)
    assert bridge_lift.evaluation.expected_reward == Fraction(13, 400)
    assert bridge_lift.evaluation.failure_probability == Fraction(199, 5000)
    assert bridge_evaluation.audit.unrestricted_reward_upper == Fraction(13, 400)
    assert bridge_evaluation.audit.lifted_reward_lower == Fraction(13, 400)
    assert bridge_evaluation.audit.regret_upper == 0
    assert bridge_evaluation.audit.lifted_failure_upper == Fraction(1, 25)
    assert bridge_evaluation.audit.certified


def test_lmb_behavioral_quotient_is_25_to_5_and_merges_a_nonorbit_pair(
    lmb_behavioral_control: _LMBBehavioralControl,
) -> None:
    control = lmb_behavioral_control
    kernel = control.kernel
    quotient = control.behavioral
    automorphisms = control.automorphisms

    assert len(control.coverage.covered_states) == 25
    assert quotient.ground_state_count == 25
    assert quotient.cell_count == 5
    assert tuple(
        step.cell_count for step in quotient.refinement_trace
    ) == (3, 5, 5)
    assert len(automorphisms) == 4

    left = LMBState(11, (1, 2), LMBStatus.ACTIVE)
    right = LMBState(13, (2, 1), LMBStatus.ACTIVE)
    assert left in control.coverage.covered_states
    assert right in control.coverage.covered_states
    assert right not in lmb_orbit(kernel, left, automorphisms)
    assert quotient.partition.cell_of(left) == quotient.partition.cell_of(right)

    covered = set(control.coverage.covered_states)
    for state in control.coverage.covered_states:
        for automorphism in automorphisms:
            image = transform_lmb_state(kernel, state, automorphism)
            assert image in covered
            assert tuple(
                sorted(
                    transform_lmb_action(kernel, action, automorphism)
                    for action in kernel.actions(state)
                )
            ) == tuple(sorted(kernel.actions(image)))
            for action in kernel.actions(state):
                image_action = transform_lmb_action(
                    kernel, action, automorphism
                )
                transported = kernel.step(state, action)[0]
                direct = kernel.step(image, image_action)[0]
                assert direct.next_state == transform_lmb_state(
                    kernel, transported.next_state, automorphism
                )
                assert direct.reward_features == transported.reward_features
                assert direct.failure == transported.failure
                assert direct.terminal == transported.terminal
