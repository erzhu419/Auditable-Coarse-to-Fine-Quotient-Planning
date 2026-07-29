from __future__ import annotations

from fractions import Fraction
import hashlib

import pytest

from acfqp.h2_graph_transition_engine_v1 import (
    DeterministicH2GraphStreamV1,
    H2GraphActionV1,
    H2GraphKernelV1,
    H2GraphStateV1,
    H2GraphTransitionInvariantViolation,
    derive_splitmix64_seed_v1,
    splitmix64_v1,
    verify_deterministic_samples_v1,
    verify_exact_atoms_v1,
)
from acfqp.relational_graph_core_v1 import GraphTopologyV1


def _kernel() -> H2GraphKernelV1:
    return H2GraphKernelV1(
        topology=GraphTopologyV1(
            4,
            ((0, 1), (0, 2), (1, 3), (2, 3)),
        ),
        rank_cap=6,
        horizon=2,
        spawn_law=(
            (1, Fraction(99, 100)),
            (2, Fraction(1, 100)),
        ),
    )


def test_exact_row_is_normalized_and_uses_postspawn_failure() -> None:
    kernel = _kernel()
    state = H2GraphStateV1((1, 1, 2, 0))
    action = H2GraphActionV1(0, 1, 0)
    atoms = kernel.exact_atoms(
        state,
        action,
        remaining_horizon=2,
    )
    assert sum((atom.probability for atom in atoms), Fraction(0)) == 1
    assert len(atoms) == 4
    assert {atom.spawn_cell for atom in atoms} == {1, 3}
    assert {atom.spawn_rank for atom in atoms} == {1, 2}
    assert all(
        atom.realized_row_reward == Fraction(1, 64)
        for atom in atoms
    )
    assert all(atom.terminal == atom.failure for atom in atoms)


@pytest.mark.parametrize(
    "law",
    (
        ((1, Fraction(99, 100)), (2, Fraction(1, 100))),
        (
            (1, Fraction(991, 1000)),
            (2, Fraction(7, 1000)),
            (3, Fraction(2, 1000)),
        ),
        ((1, Fraction(197, 200)), (2, Fraction(3, 200))),
    ),
)
def test_exact_row_covers_mixed_postspawn_failure_and_uniform_cells(
    law: tuple[tuple[int, Fraction], ...],
) -> None:
    kernel = H2GraphKernelV1(
        topology=GraphTopologyV1(
            4,
            ((0, 1), (0, 2), (1, 3), (2, 3)),
        ),
        rank_cap=6,
        horizon=2,
        spawn_law=law,
    )
    state = H2GraphStateV1((1, 1, 2, 0))
    # Keeping the merged rank-2 at vertex 1 leaves the pre-existing rank-2
    # diagonally separated at vertex 2.  Rank-1 spawns fail, while rank-2
    # spawns restore a merge.  This exercises the actual post-spawn branch.
    atoms = kernel.exact_atoms(
        state,
        H2GraphActionV1(0, 1, 1),
        remaining_horizon=2,
    )
    assert sum((atom.probability for atom in atoms), Fraction(0)) == 1
    rank_probability = dict(law)
    for cell in (0, 3):
        for rank, probability in law:
            atom = next(
                atom
                for atom in atoms
                if atom.spawn_cell == cell and atom.spawn_rank == rank
            )
            assert atom.probability == probability / 2
    assert any(atom.failure for atom in atoms)
    assert any(not atom.failure for atom in atoms)
    assert all(
        atom.failure == (atom.spawn_rank != 2)
        for atom in atoms
    )


def test_horizon_one_is_terminal_before_no_failure_is_inferred() -> None:
    kernel = _kernel()
    atoms = kernel.exact_atoms(
        H2GraphStateV1((1, 1, 2, 0)),
        H2GraphActionV1(0, 1, 0),
        remaining_horizon=1,
    )
    assert all(atom.terminal for atom in atoms)
    assert any(not atom.failure for atom in atoms)


def test_deterministic_stream_samples_only_exact_atoms() -> None:
    kernel = _kernel()
    state = H2GraphStateV1((1, 1, 2, 0))
    action = H2GraphActionV1(0, 1, 0)
    atoms = kernel.exact_atoms(
        state,
        action,
        remaining_horizon=2,
    )
    exact = {
        (
            atom.next_state,
            atom.realized_row_reward,
            atom.failure,
            atom.terminal,
            atom.spawn_cell,
            atom.spawn_rank,
        )
        for atom in atoms
    }
    group = hashlib.sha256(b"fresh-pairing-group").hexdigest()
    seed = derive_splitmix64_seed_v1(
        seed_domain="acfqp:test-h2-seed:v1",
        pairing_group_id=group,
    )
    first = DeterministicH2GraphStreamV1(
        kernel=kernel,
        state=state,
        action=action,
        remaining_horizon=2,
        seed=seed,
    )
    second = DeterministicH2GraphStreamV1(
        kernel=kernel,
        state=state,
        action=action,
        remaining_horizon=2,
        seed=seed,
    )
    first_samples = tuple(first.draw() for _ in range(256))
    second_samples = tuple(second.draw() for _ in range(256))
    assert first_samples == second_samples
    assert all(
        (
            sample.next_state,
            sample.realized_row_reward,
            sample.failure,
            sample.terminal,
            sample.spawn_cell,
            sample.spawn_rank,
        )
        in exact
        for sample in first_samples
    )
    assert first.accepted_draw_count == 256
    assert first.random_word_calls == sum(
        sample.random_word_count for sample in first_samples
    )
    assert (
        verify_exact_atoms_v1(
            kernel=kernel,
            state=state,
            action=action,
            remaining_horizon=2,
            atoms=atoms,
        )
        == atoms
    )
    assert (
        verify_deterministic_samples_v1(
            kernel=kernel,
            state=state,
            action=action,
            remaining_horizon=2,
            seed=seed,
            samples=first_samples,
        )
        == first_samples
    )


def test_serialized_atom_and_sample_forgery_fail_replay() -> None:
    kernel = _kernel()
    state = H2GraphStateV1((1, 1, 2, 0))
    action = H2GraphActionV1(0, 1, 0)
    atoms = kernel.exact_atoms(
        state,
        action,
        remaining_horizon=2,
    )
    forged_atoms = atoms[1:] + atoms[:1]
    with pytest.raises(
        H2GraphTransitionInvariantViolation,
        match="do not replay",
    ):
        verify_exact_atoms_v1(
            kernel=kernel,
            state=state,
            action=action,
            remaining_horizon=2,
            atoms=forged_atoms,
        )

    group = hashlib.sha256(b"replay-bound-group").hexdigest()
    seed = derive_splitmix64_seed_v1(
        seed_domain="acfqp:test-h2-replay-seed:v1",
        pairing_group_id=group,
    )
    stream = DeterministicH2GraphStreamV1(
        kernel=kernel,
        state=state,
        action=action,
        remaining_horizon=2,
        seed=seed,
    )
    samples = tuple(stream.draw() for _ in range(8))
    forged_samples = samples[1:] + samples[:1]
    with pytest.raises(
        H2GraphTransitionInvariantViolation,
        match="do not replay",
    ):
        verify_deterministic_samples_v1(
            kernel=kernel,
            state=state,
            action=action,
            remaining_horizon=2,
            seed=seed,
            samples=forged_samples,
        )


def test_seed_matches_registered_splitmix_construction() -> None:
    group = hashlib.sha256(b"group").hexdigest()
    domain = "acfqp:v075-heldout-discovery-stream-seed:v1"
    expected = int.from_bytes(
        hashlib.sha256(
            domain.encode("utf-8") + b"\x00" + group.encode("ascii")
        ).digest()[:8],
        "big",
    )
    assert (
        derive_splitmix64_seed_v1(
            seed_domain=domain,
            pairing_group_id=group,
        )
        == expected
    )
    assert splitmix64_v1(0) == 0


def test_process_metadata_cannot_enter_the_seed_api() -> None:
    group = hashlib.sha256(b"group").hexdigest()
    with pytest.raises(TypeError):
        derive_splitmix64_seed_v1(
            seed_domain="acfqp:v075-seed:v1",
            pairing_group_id=group,
            worker_id=7,
        )


def test_invalid_state_law_and_action_fail_closed() -> None:
    with pytest.raises(H2GraphTransitionInvariantViolation):
        H2GraphKernelV1(
            topology=GraphTopologyV1(2, ((0, 1),)),
            rank_cap=6,
            horizon=2,
            spawn_law=((1, Fraction(1, 2)),),
        )
    kernel = _kernel()
    with pytest.raises(H2GraphTransitionInvariantViolation):
        kernel.validate_state(H2GraphStateV1((1, 1, 2, 0), True))
    with pytest.raises(H2GraphTransitionInvariantViolation):
        kernel.merge(
            H2GraphStateV1((1, 1, 2, 0)),
            H2GraphActionV1(0, 2, 0),
        )
