from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.cross_graph_relational_support_v1 as cross


@pytest.fixture(scope="module")
def family() -> cross.CrossGraphFamilyV1:
    return cross.registered_cross_graph_family_v1()


@pytest.fixture(scope="module")
def source_bundle() -> cross.CrossGraphSourceObservationBundleV1:
    return cross.acquire_cross_graph_source_observations_v1()


def test_registered_split_contains_six_nonisomorphic_graphs(
    family: cross.CrossGraphFamilyV1,
) -> None:
    assert cross.CONTRACT_VERSION == "1.29.0"
    assert (
        cross.PROFILE_KEY
        == "observation_driven_cross_geometry_relational_rapm_v0"
    )
    assert tuple(item.graph_key for item in family.source_contexts) == (
        "p4",
        "star",
        "paw",
    )
    assert tuple(item.graph_key for item in family.target_contexts) == (
        "c4",
        "diamond",
        "k4",
    )
    assert len(family.nonisomorphism_witnesses) == 9
    assert all(
        item.tested_bijection_count == 24
        and item.isomorphism_mapping_count == 0
        for item in family.nonisomorphism_witnesses
    )
    assert {
        item.structural_id for item in family.source_contexts
    }.isdisjoint(
        {item.structural_id for item in family.target_contexts}
    )
    assert len(family.family_id) == 64
    assert family.official_execution_allowed is False


def test_contexts_freeze_rank_relative_dynamics_and_reject_split_splice(
    family: cross.CrossGraphFamilyV1,
) -> None:
    assert tuple(item.low_rank for item in family.source_contexts) == (1, 2, 3)
    assert tuple(item.low_rank for item in family.target_contexts) == (2, 3, 4)
    assert all(
        item.low_rank_probability == Fraction(99, 100)
        and item.high_rank == item.low_rank + 1
        and item.rank_cap == 6
        and item.horizon == 2
        and item.risk_tolerance == Fraction(1, 20)
        for item in family.source_contexts + family.target_contexts
    )
    with pytest.raises(cross.CrossGraphInvariantViolation):
        replace(
            family.source_contexts[0],
            split=cross.CrossGraphSplit.TARGET,
        )


def test_complete_edge_third_anchor_motif_counts_have_no_graph_cases(
    family: cross.CrossGraphFamilyV1,
) -> None:
    expected = {
        "p4": 6,
        "star": 6,
        "paw": 8,
        "c4": 8,
        "diamond": 10,
        "k4": 12,
    }
    assert {
        item.graph_key: len(cross.motif_states_v1(item))
        for item in family.source_contexts + family.target_contexts
    } == expected
    source = inspect.getsource(cross.motif_states_v1)
    for graph_key in expected:
        assert f'"{graph_key}"' not in source
        assert f"'{graph_key}'" not in source


def test_graph_merge_kernel_exact_and_generative_paths_agree(
    family: cross.CrossGraphFamilyV1,
) -> None:
    context = family.target_contexts[0]
    kernel = cross.GraphMergeKernelV1(context)
    state = cross.motif_states_v1(context)[0]
    action = kernel.actions(state)[0]
    outcomes = kernel.step(state, action)

    assert sum(
        (item.probability for item in outcomes),
        Fraction(0),
    ) == 1
    assert len(outcomes) == 4
    empty_cell_count = len(outcomes) // 2
    for cell_ordinal in range(empty_cell_count):
        for rank_ordinal, rank_fraction in (
            (0, context.low_rank_probability / 2),
            (
                1,
                context.low_rank_probability
                + (1 - context.low_rank_probability) / 2,
            ),
        ):
            uniform = (cell_ordinal + rank_fraction) / empty_cell_count
            sampled = kernel.sample(state, action, uniform)
            expected = outcomes[2 * cell_ordinal + rank_ordinal]
            assert sampled.structural_atom_index == (
                2 * cell_ordinal + rank_ordinal
            )
            assert sampled.next_state == expected.next_state
            assert sampled.normalized_reward == (
                expected.feature("merge") / cross.HORIZON
            )
            assert sampled.failure == expected.failure
            assert sampled.terminal == expected.terminal
            assert sampled.to_document()["exact_probability_exposed"] is False


def test_source_acquisition_closes_every_h2_state_action_row(
    source_bundle: cross.CrossGraphSourceObservationBundleV1,
) -> None:
    assert tuple(
        (context.graph_key, count)
        for context, (_, count) in zip(
            source_bundle.contexts,
            source_bundle.row_counts_by_context,
        )
    ) == (("p4", 36), ("star", 36), ("paw", 48))
    assert source_bundle.ground_row_count == 120
    assert len(source_bundle.observation_log.topologies) == 3
    assert source_bundle.query_inputs_used == 0
    assert source_bundle.target_inputs_used == 0
    assert source_bundle.graph_group_prior_used is False
    assert source_bundle.graph_identity_branches_used is False
    assert len(source_bundle.bundle_id) == 64

    rows_by_state: dict[str, list[object]] = {}
    for row in source_bundle.observation_log.rows:
        rows_by_state.setdefault(row.state.state_id, []).append(row)
    assert all(
        len(rows)
        == len(rows[0].legal_actions)
        == len({row.action.action_id for row in rows})
        for rows in rows_by_state.values()
    )


def test_target_root_and_continuation_catalogues_are_complete(
    family: cross.CrossGraphFamilyV1,
) -> None:
    expected = {
        "c4": (8, 12),
        "diamond": (10, 14),
        "k4": (12, 16),
    }
    for context in family.target_contexts:
        roots = cross.target_root_catalogues_v1(context)
        continuations = cross.target_continuation_catalogues_v1(context)
        assert (len(roots), len(continuations)) == expected[context.graph_key]
        assert all(
            item.context_id == context.context_id
            and item.state.remaining_horizon == 2
            and len(item.legal_actions) == 2
            for item in roots
        )
        assert all(
            item.context_id == context.context_id
            and item.state.remaining_horizon == 1
            and item.legal_actions
            for item in continuations
        )


def test_every_target_point_has_exact_safe_h2_ground_control(
    family: cross.CrossGraphFamilyV1,
) -> None:
    expected_risk = Fraction(99, 5000)
    expected_root_counts = {"c4": 8, "diamond": 10, "k4": 12}
    expected_row_counts = {
        "c4": {18},
        "diamond": {20, 24, 26},
        "k4": {28},
    }
    for context in family.target_contexts:
        controls = cross.cold_exact_h2_family_v1(context)
        assert len(controls) == expected_root_counts[context.graph_key]
        assert {
            item.minimum_failure_probability for item in controls
        } == {expected_risk}
        assert all(
            item.feasible
            and item.selected_failure_probability == expected_risk
            and item.selected_normalized_reward is not None
            and item.model_reuse_count == 0
            and item.exact_ground_oracle_used
            for item in controls
        )
        assert {
            item.reachable_state_action_row_count for item in controls
        } == expected_row_counts[context.graph_key]
        assert len({item.query_id for item in controls}) == len(controls)


def test_target_oracle_rejects_source_context(
    family: cross.CrossGraphFamilyV1,
) -> None:
    with pytest.raises(cross.CrossGraphInvariantViolation):
        cross.cold_exact_h2_oracle_v1(family.source_contexts[0])
    with pytest.raises(cross.CrossGraphInvariantViolation):
        cross.target_root_catalogues_v1(family.source_contexts[0])


def test_foundation_implementation_authority_is_frozen() -> None:
    assert len(cross.FOUNDATION_IMPLEMENTATION_SHA256) == 64
    cross.validate_cross_graph_foundation_authority_v1()
    for function in (
        cross.GraphMergeKernelV1.actions,
        cross.GraphMergeKernelV1.step,
        cross.GraphMergeKernelV1.sample,
        cross.motif_states_v1,
    ):
        source = inspect.getsource(function)
        for graph_key in ("p4", "star", "paw", "c4", "diamond", "k4"):
            assert f'"{graph_key}"' not in source
            assert f"'{graph_key}'" not in source
