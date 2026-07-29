from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp import exact_lazy_h2_robust_planner_v1 as lazy
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import v072_exact_lazy_planner_component_v1 as component
from test_exact_lazy_h2_robust_planner_v1 import _context_shaped_model


@pytest.mark.parametrize(
    "solver_kind",
    (
        robust.RobustSolverKind.GROUND_DIRECT,
        robust.RobustSolverKind.QUOTIENT,
    ),
)
def test_solved_component_requires_independent_prefix_cover(
    solver_kind: robust.RobustSolverKind,
) -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_k6_v0",
        4,
        partial_other=True,
    )
    result = component.solve_and_verify_v072_exact_lazy_h2_v1(
        model=model,
        threshold=threshold,
        solver_kind=solver_kind,
    )
    assert result.solve_result.status is lazy.ExactLazyH2SolveStatus.SOLVED
    assert result.independent_verification is not None
    assert result.independent_proof_replay_complete
    assert result.plan_certificate_authority == (
        result.solve_result.audit is not None
        and result.solve_result.audit.status
        is robust.RobustAuditStatus.CERTIFIED
    )
    assert result.independent_verification.model_id == model.model_id
    assert result.to_document()["ground_kernel_calls"] == 0


def test_resource_exhaustion_is_a_noncertificate() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_k6_v0",
        4,
        partial_other=True,
    )
    result = component.solve_and_verify_v072_exact_lazy_h2_v1(
        model=model,
        threshold=threshold,
        solver_kind=robust.RobustSolverKind.QUOTIENT,
        limits=lazy.ExactLazyH2ResourceLimitsV1(
            max_branch_nodes=1,
            max_complete_policies=1,
            max_root_bound_evaluations=1,
        ),
    )
    assert result.solve_result.status is (
        lazy.ExactLazyH2SolveStatus.EXACT_DP_RESOURCE_EXHAUSTED
    )
    assert result.independent_verification is None
    assert not result.independent_proof_replay_complete
    assert not result.plan_certificate_authority


def test_missing_or_transplanted_verification_is_rejected() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_w5_v0",
        3,
        partial_other=True,
    )
    result = component.solve_and_verify_v072_exact_lazy_h2_v1(
        model=model,
        threshold=threshold,
        solver_kind=robust.RobustSolverKind.GROUND_DIRECT,
    )
    with pytest.raises(
        component.V072ExactLazyPlannerComponentInvariantViolation
    ):
        replace(result, independent_verification=None)
    with pytest.raises(
        component.V072ExactLazyPlannerComponentInvariantViolation
    ):
        replace(result, model_id="0" * 64)


def test_component_api_has_no_caller_supplied_audit_or_status() -> None:
    parameters = set(
        component.solve_and_verify_v072_exact_lazy_h2_v1.__annotations__
    )
    assert not parameters & {
        "audit",
        "audit_status",
        "certificate_status",
        "selected_policy",
        "solve_result",
        "verification",
    }
