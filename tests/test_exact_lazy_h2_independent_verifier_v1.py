from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

import acfqp.exact_lazy_h2_independent_verifier_v1 as independent
import acfqp.exact_lazy_h2_robust_planner_v1 as lazy
import acfqp.partial_support_robust_planner_v1 as robust
from test_exact_lazy_h2_robust_planner_v1 import (
    _context_shaped_model,
    _id,
)


def _replace_original_proof(
    result: lazy.ExactLazyH2SolveResultV1,
    proof: lazy.ExactLazyH2SearchProofV1,
) -> lazy.ExactLazyH2SolveResultV1:
    assert result.trace is not None
    return replace(
        result,
        trace=replace(result.trace, original_proof=proof),
    )


def _quotient_above_legacy_cap_model() -> tuple[
    robust.PartialSupportIntervalModelV1,
    robust.RobustThresholdProfileV1,
]:
    model, threshold = _context_shaped_model(
        "opaque_graph_k6_v0",
        17,
    )
    cell_by_state = {
        catalogue.state_id: (
            catalogue.state_coordinate_key
            if catalogue.state_id == model.root_state_id
            else _id(f"independent-quotient-cell:{catalogue.state_id}")
        )
        for catalogue in model.catalogues
    }
    return (
        robust.build_partial_support_model_v1(
            context_id=model.context_id,
            root_state_id=model.root_state_id,
            catalogues=(
                replace(
                    catalogue,
                    state_coordinate_key=cell_by_state[catalogue.state_id],
                )
                for catalogue in model.catalogues
            ),
            destinations=model.destinations,
            rows=model.rows,
            concretizer_entries=(
                replace(
                    entry,
                    state_coordinate_key=cell_by_state[entry.state_id],
                )
                for entry in model.concretizer_entries
            ),
        ),
        threshold,
    )


def test_small_model_gets_prefix_replay_and_legacy_byte_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_w5_v0",
        4,
    )
    result = lazy.solve_exact_lazy_ground_direct_h2_v1(model, threshold)
    assert result.trace is not None

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("production lazy traversal was called")

    monkeypatch.setattr(lazy, "solve_exact_lazy_robust_h2_v1", forbidden)
    monkeypatch.setattr(lazy, "_solve_core_lazy", forbidden)
    monkeypatch.setattr(lazy, "_can_prune", forbidden)
    monkeypatch.setattr(lazy, "_optimistic_child_values", forbidden)

    verified = independent.verify_exact_lazy_h2_solve_result_v1(
        model,
        threshold,
        result,
    )

    assert verified.legacy_exhaustive_bytes_compared
    assert verified.complete_prefix_cover_verified
    assert verified.exact_fraction_replay_verified
    assert verified.selected_audit_rebuilt_independently
    assert verified.independent_implementation_claimed
    assert not verified.production_lazy_solver_called
    assert verified.original_proof_id == result.trace.original_proof.proof_id


def test_above_legacy_cap_uses_complete_independent_prefix_proof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_k6_v0",
        17,
    )
    result = lazy.solve_exact_lazy_ground_direct_h2_v1(model, threshold)

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("legacy exhaustive solver was called above cap")

    monkeypatch.setattr(
        robust,
        "solve_ground_direct_robust_h2_v1",
        forbidden,
    )
    monkeypatch.setattr(
        robust,
        "solve_quotient_robust_h2_v1",
        forbidden,
    )

    verified = independent.verify_exact_lazy_h2_solve_result_v1(
        model,
        threshold,
        result,
    )

    assert not verified.legacy_exhaustive_bytes_compared
    assert verified.verified_pruned_nodes > 0
    assert verified.verified_complete_nodes > 0
    assert verified.verified_branch_nodes == (
        result.trace.original.branch_nodes  # type: ignore[union-attr]
    )


def test_quotient_above_legacy_cap_replays_proof_and_exact_counters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, threshold = _quotient_above_legacy_cap_model()
    with pytest.raises(
        robust.PartialSupportRobustPlannerInvariantViolation,
        match="quotient robust policy enumeration exceeds the frozen cap",
    ):
        robust.solve_quotient_robust_h2_v1(model, threshold)
    result = lazy.solve_exact_lazy_quotient_h2_v1(model, threshold)
    assert result.trace is not None

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("legacy exhaustive solver was called above cap")

    monkeypatch.setattr(
        robust,
        "solve_quotient_robust_h2_v1",
        forbidden,
    )
    verified = independent.verify_exact_lazy_h2_solve_result_v1(
        model,
        threshold,
        result,
    )

    assert not verified.legacy_exhaustive_bytes_compared
    assert verified.verified_branch_nodes == result.trace.original.branch_nodes
    assert verified.verified_complete_nodes == (
        result.trace.original.complete_policies
    )
    assert verified.verified_pruned_nodes == (
        result.trace.original.pruned_branches
    )

    forged_counters = replace(
        result.trace.original,
        branch_nodes=result.trace.original.branch_nodes + 1,
    )
    forged = replace(
        result,
        trace=replace(result.trace, original=forged_counters),
    )
    with pytest.raises(
        independent.ExactLazyH2IndependentVerificationError,
        match="counters",
    ):
        independent.verify_exact_lazy_h2_solve_result_v1(
            model,
            threshold,
            forged,
        )


def test_removed_pruned_prefix_fails_closed_after_coherent_reconstruction() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_k6_v0",
        17,
    )
    result = lazy.solve_exact_lazy_ground_direct_h2_v1(model, threshold)
    assert result.trace is not None
    proof = result.trace.original_proof
    assert proof.pruned_nodes
    forged = replace(proof, pruned_nodes=proof.pruned_nodes[1:])
    claimed = _replace_original_proof(result, forged)

    with pytest.raises(
        independent.ExactLazyH2IndependentVerificationError,
        match="cover|counters",
    ):
        independent.verify_exact_lazy_h2_solve_result_v1(
            model,
            threshold,
            claimed,
        )


def test_forged_fraction_rectangle_is_recomputed_not_trusted() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_k6_v0",
        17,
    )
    result = lazy.solve_exact_lazy_ground_direct_h2_v1(model, threshold)
    assert result.trace is not None
    proof = result.trace.original_proof
    target = proof.pruned_nodes[0]
    changed = replace(
        target,
        reward_lower_upper_bound=(
            target.reward_lower_upper_bound + Fraction(1, 10_000)
        ),
    )
    nodes = tuple(
        sorted(
            (changed, *proof.pruned_nodes[1:]),
            key=lambda item: item.witness_id,
        )
    )
    claimed = _replace_original_proof(
        result,
        replace(proof, pruned_nodes=nodes),
    )

    with pytest.raises(
        independent.ExactLazyH2IndependentVerificationError,
        match="rectangle",
    ):
        independent.verify_exact_lazy_h2_solve_result_v1(
            model,
            threshold,
            claimed,
        )


def test_forged_policy_tie_witness_is_recomputed_not_trusted() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_k6_v0",
        17,
    )
    result = lazy.solve_exact_lazy_ground_direct_h2_v1(model, threshold)
    assert result.trace is not None
    proof = result.trace.original_proof
    target = proof.pruned_nodes[0]
    changed_key = tuple(
        sorted(
            (
                *target.minimum_policy_key[:-1],
                _id("forged-independent-tie-assignment"),
            )
        )
    )
    changed = replace(target, minimum_policy_key=changed_key)
    nodes = tuple(
        sorted(
            (changed, *proof.pruned_nodes[1:]),
            key=lambda item: item.witness_id,
        )
    )
    claimed = _replace_original_proof(
        result,
        replace(proof, pruned_nodes=nodes),
    )

    with pytest.raises(
        independent.ExactLazyH2IndependentVerificationError,
        match="rectangle",
    ):
        independent.verify_exact_lazy_h2_solve_result_v1(
            model,
            threshold,
            claimed,
        )


@pytest.mark.parametrize("field", ("dominating_policy_key", "dominating_reward_lower"))
def test_forged_dominating_policy_claim_is_rejected(field: str) -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_k6_v0",
        17,
    )
    result = lazy.solve_exact_lazy_ground_direct_h2_v1(model, threshold)
    assert result.trace is not None
    proof = result.trace.original_proof
    target = proof.pruned_nodes[0]
    if field == "dominating_policy_key":
        value: object = tuple(
            sorted(
                (
                    *target.dominating_policy_key[:-1],
                    _id("forged-independent-dominating-assignment"),
                )
            )
        )
    else:
        value = target.dominating_reward_lower + Fraction(1, 10_000)
    changed = replace(target, **{field: value})
    nodes = tuple(
        sorted(
            (changed, *proof.pruned_nodes[1:]),
            key=lambda item: item.witness_id,
        )
    )
    claimed = _replace_original_proof(
        result,
        replace(proof, pruned_nodes=nodes),
    )

    with pytest.raises(
        independent.ExactLazyH2IndependentVerificationError,
        match="rectangle",
    ):
        independent.verify_exact_lazy_h2_solve_result_v1(
            model,
            threshold,
            claimed,
        )


def test_forged_complete_node_exact_value_is_rejected() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_w5_v0",
        4,
    )
    result = lazy.solve_exact_lazy_ground_direct_h2_v1(model, threshold)
    assert result.trace is not None
    proof = result.trace.original_proof
    target = proof.complete_nodes[0]
    changed = replace(
        target,
        reward_upper=target.reward_upper + Fraction(1, 10_000),
    )
    nodes = tuple(
        sorted(
            (changed, *proof.complete_nodes[1:]),
            key=lambda item: item.witness_id,
        )
    )
    claimed = _replace_original_proof(
        result,
        replace(proof, complete_nodes=nodes),
    )

    with pytest.raises(
        independent.ExactLazyH2IndependentVerificationError,
        match="exact evaluation",
    ):
        independent.verify_exact_lazy_h2_solve_result_v1(
            model,
            threshold,
            claimed,
        )


def test_zero_other_phase_has_a_separate_independent_prefix_proof() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_w5_v0",
        3,
        partial_other=True,
    )
    result = lazy.solve_exact_lazy_ground_direct_h2_v1(model, threshold)
    assert result.trace is not None
    assert result.trace.zero_other_counterfactual_proof is not None

    verified = independent.verify_exact_lazy_h2_solve_result_v1(
        model,
        threshold,
        result,
    )

    assert verified.zero_other_proof_id == (
        result.trace.zero_other_counterfactual_proof.proof_id
    )
    assert verified.verified_branch_nodes > result.trace.original.branch_nodes


def test_resource_exhaustion_cannot_be_verified_as_an_exact_audit() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_w5_v0",
        3,
    )
    result = lazy.solve_exact_lazy_ground_direct_h2_v1(
        model,
        threshold,
        limits=lazy.ExactLazyH2ResourceLimitsV1(
            max_branch_nodes=1,
            max_complete_policies=10,
            max_root_bound_evaluations=10,
        ),
    )
    assert (
        result.status
        is lazy.ExactLazyH2SolveStatus.EXACT_DP_RESOURCE_EXHAUSTED
    )
    assert result.audit is None
    assert result.trace is None

    with pytest.raises(
        independent.ExactLazyH2IndependentVerificationError,
        match="claimed lazy result",
    ):
        independent.verify_exact_lazy_h2_solve_result_v1(
            model,
            threshold,
            result,
        )
