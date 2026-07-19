from fractions import Fraction

import pytest

from acfqp.domains.g2048 import G2048Kernel, G2048State, G2048Status
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBStatus,
)
from acfqp.domains.semantic import (
    BoundaryActionLabel,
    G2048SemanticAdapter,
    LMBSemanticAdapter,
    restriction_diagnostic,
)


def as_dict(features: tuple[tuple[str, Fraction], ...]) -> dict[str, Fraction]:
    return dict(features)


def test_g2048_boundary_labels_concretize_exact_first_and_last_actions() -> None:
    kernel = G2048Kernel(2)
    state = G2048State((1, 1, 1, 1))
    adapter = G2048SemanticAdapter()
    primitive = kernel.actions(state)

    assert adapter.labels(kernel, state) == (
        BoundaryActionLabel.FIRST,
        BoundaryActionLabel.LAST,
    )
    assert adapter.concretize(kernel, state, BoundaryActionLabel.FIRST) == (
        (Fraction(1), primitive[0]),
    )
    assert adapter.concretize(kernel, state, BoundaryActionLabel.LAST) == (
        (Fraction(1), primitive[-1]),
    )

    diagnostic = restriction_diagnostic(adapter, kernel, state)
    assert diagnostic.evidence_level == "diagnostic_only"
    assert diagnostic.represented_actions == (primitive[0], primitive[-1])
    assert diagnostic.omitted_actions == primitive[1:-1]
    assert diagnostic.restriction_active


def test_terminal_state_has_no_semantic_labels() -> None:
    kernel = G2048Kernel(2)
    state = G2048State((1, 2, 0, 0), G2048Status.FAILURE)
    adapter = G2048SemanticAdapter()
    assert adapter.labels(kernel, state) == ()
    assert not restriction_diagnostic(adapter, kernel, state).restriction_active
    with pytest.raises(ValueError, match="unavailable"):
        adapter.concretize(kernel, state, BoundaryActionLabel.FIRST)


def test_g2048_features_are_exact_current_state_atoms() -> None:
    kernel = G2048Kernel(2)
    state = G2048State((1, 1, 2, 0))
    features = as_dict(G2048SemanticAdapter().features(kernel, state))
    assert features == {
        "action_count": Fraction(2),
        "branching_count": Fraction(8),  # 2 actions x 2 empties x 2 ranks
        "capacity_slack": Fraction(1, 4),
        "empty_count": Fraction(1),
        "immediate_release_liquidity": Fraction(1, 4),
        "match_debt_mean": Fraction(1, 12),
        "match_debt_min": Fraction(0),
        "match_debt_nonzero_types": Fraction(1),
        "max_rank": Fraction(2),
        "min_rank": Fraction(1),
        "occupied_count": Fraction(3),
        "rank_sum": Fraction(4),
        "spatial_match_debt": Fraction(1),
    }


def test_lmb_single_action_deduplicates_last_label() -> None:
    kernel = LMBKernel(
        tile_types=(0, 0, 0),
        blockers=(frozenset(), frozenset({0}), frozenset({1})),
        type_count=1,
        capacity=2,
        max_layers=3,
    )
    state = kernel.initial_distribution()[0][1]
    adapter = LMBSemanticAdapter()
    assert adapter.labels(kernel, state) == (BoundaryActionLabel.FIRST,)
    assert adapter.concretize(kernel, state, BoundaryActionLabel.FIRST) == (
        (Fraction(1), LMBAction(0)),
    )
    with pytest.raises(ValueError, match="unavailable"):
        adapter.concretize(kernel, state, BoundaryActionLabel.LAST)
    assert not restriction_diagnostic(adapter, kernel, state).restriction_active


def test_lmb_features_capture_capacity_liquidity_and_match_debt() -> None:
    kernel = LMBKernel(
        tile_types=(0, 0, 0),
        blockers=(frozenset(), frozenset({0}), frozenset({1})),
        type_count=1,
        capacity=2,
        max_layers=3,
    )
    adapter = LMBSemanticAdapter()
    state = kernel.initial_distribution()[0][1]
    state = kernel.step(state, LMBAction(0))[0].next_state
    first = as_dict(adapter.features(kernel, state))
    assert first["capacity_slack"] == Fraction(1, 2)
    assert first["immediate_release_liquidity"] == 0
    assert first["match_debt_mean"] == Fraction(2, 3)
    assert first["match_debt_nonzero_types"] == 1

    state = kernel.step(state, LMBAction(1))[0].next_state
    second = as_dict(adapter.features(kernel, state))
    assert second["capacity_slack"] == 0
    assert second["immediate_release_liquidity"] == 1
    assert second["match_debt_mean"] == Fraction(1, 3)
    assert second["max_match_debt"] == Fraction(1, 3)
    assert second["branching_count"] == 1


def test_lmb_diagnostic_lists_interior_eligible_actions_as_omitted() -> None:
    kernel = LMBKernel(
        tile_types=(0, 0, 0, 1, 1, 1),
        blockers=(frozenset(),) * 6,
        type_count=2,
        capacity=3,
        max_layers=1,
    )
    state = kernel.initial_distribution()[0][1]
    diagnostic = restriction_diagnostic(LMBSemanticAdapter(), kernel, state)
    assert diagnostic.primitive_actions == tuple(LMBAction(tile) for tile in range(6))
    assert diagnostic.represented_actions == (LMBAction(0), LMBAction(5))
    assert diagnostic.omitted_actions == tuple(LMBAction(tile) for tile in range(1, 5))
