from dataclasses import replace

import pytest

from acfqp.planning import (
    ExactJ0InfeasibilityProof,
    PlanningIdentity,
    ProductionPrecheckStatus,
    resolve_known_infeasibility,
)


def _identity() -> PlanningIdentity:
    return PlanningIdentity(
        structural_id="fixture-structural",
        build_id="build-content",
        kernel_hash="kernel-content",
        query_hash="query-content",
    )


def _proof(identity: PlanningIdentity) -> ExactJ0InfeasibilityProof:
    return ExactJ0InfeasibilityProof(
        proof_id="j0-proof",
        identity=identity,
        frontier_hash="frontier-content",
        establishment_candidate_count=17,
        establishment_elapsed_ns=23,
    )


def test_exact_known_infeasibility_shortcuts_and_preserves_accounting() -> None:
    identity = _identity()
    result = resolve_known_infeasibility(
        identity,
        _proof(identity),
        validation_elapsed_ns=5,
    )
    assert result is not None
    assert result.status is ProductionPrecheckStatus.INFEASIBLE_QUERY
    assert result.establishment_candidate_count == 17
    assert result.establishment_elapsed_ns == 23
    assert result.validation_elapsed_ns == 5


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("structural_id", "other-structural"),
        ("build_id", "other-build"),
        ("kernel_hash", "other-kernel"),
        ("query_hash", "other-query"),
    ),
)
def test_any_identity_mismatch_disables_shortcut(field: str, value: str) -> None:
    current = _identity()
    mismatched = replace(current, **{field: value})
    assert resolve_known_infeasibility(current, _proof(mismatched)) is None


def test_nonexact_or_nonoracle_proof_cannot_be_constructed() -> None:
    with pytest.raises(ValueError, match="exact oracle-truth"):
        ExactJ0InfeasibilityProof(
            proof_id="bad-proof",
            identity=_identity(),
            frontier_hash="frontier-content",
            establishment_candidate_count=0,
            establishment_elapsed_ns=0,
            exact=False,
        )
