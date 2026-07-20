from __future__ import annotations

from dataclasses import replace

import pytest

from test_phase3e_predecision_acceptance import _scenario

from acfqp.phase3e_predecision_acceptance import (
    Phase3EPredecisionAcceptanceError,
    accept_phase3e_predecision_mechanics,
)
from acfqp.phase3e_terminal_shape import (
    PLAN_TERMINAL_SHAPE_ONLY,
    evaluate_phase3e_terminal_shape,
)
from acfqp.route_comparison import DIRECT_FALLBACK
from acfqp.route_protocol_guard import ProjectionTerm


def _accept_with(*, cap_profile=None, local_projection=None):
    fixture, catalog, commitment, envelope, semantic_results = _scenario()
    return accept_phase3e_predecision_mechanics(
        envelope=envelope,
        context=fixture.context,
        registry=fixture.registry,
        catalog=catalog,
        cap_profile=cap_profile or fixture.cap_profile,
        decision_points=(),
        local_projection=local_projection or fixture.local_projection,
        fallback_projection=fixture.fallback_projection,
        guard_commitment=commitment,
        semantic_results=semantic_results,
    )


def test_no_causal_route_rejects_cap_profile_from_another_context() -> None:
    fixture, _, _, _, _ = _scenario()
    forged = replace(fixture.cap_profile, context_id="another-context")
    with pytest.raises(Phase3EPredecisionAcceptanceError, match="different route context"):
        _accept_with(cap_profile=forged)


def test_no_causal_route_rejects_local_projection_labeled_fallback() -> None:
    fixture, _, _, _, _ = _scenario()
    forged = replace(
        fixture.local_projection,
        route_candidate=DIRECT_FALLBACK,
        projection_key="forged-fallback-labeled-local",
    )
    with pytest.raises(Phase3EPredecisionAcceptanceError, match="wrong route candidate"):
        _accept_with(local_projection=forged)


def test_no_causal_route_rejects_incomplete_shared_axis_coverage() -> None:
    fixture, _, _, _, _ = _scenario()
    forged = replace(
        fixture.local_projection,
        projection_key="forged-missing-axis",
        terms=(
            ProjectionTerm("resource.bytes", "work.bytes", 1),
            ProjectionTerm("resource.bytes", "work.operations", 1),
        ),
    )
    with pytest.raises(Phase3EPredecisionAcceptanceError, match="shared axes"):
        _accept_with(local_projection=forged)


def test_authoritative_terminal_entry_replays_abstract_shape_end_to_end() -> None:
    fixture, catalog, commitment, envelope, semantic_results = _scenario()
    result = evaluate_phase3e_terminal_shape(
        envelope=envelope,
        context=fixture.context,
        registry=fixture.registry,
        catalog=catalog,
        cap_profile=fixture.cap_profile,
        decision_points=(),
        local_projection=fixture.local_projection,
        fallback_projection=fixture.fallback_projection,
        guard_commitment=commitment,
        semantic_results=semantic_results,
    )

    assert result.classification == PLAN_TERMINAL_SHAPE_ONLY
    assert result.source_predecision_outcome_id
    assert result.official is False
