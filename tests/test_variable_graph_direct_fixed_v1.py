from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

import acfqp.variable_graph_direct_fixed_v1 as fixed
import acfqp.variable_graph_direct_sequential_v1 as sequential
import acfqp.variable_order_graph_rapm_v1 as graph


@pytest.fixture(scope="module")
def results() -> tuple[
    tuple[fixed.DirectFixedResultV1, ...],
    tuple[fixed.DirectFixedVerificationV1, ...],
]:
    """Build operational results while full-row and exact evaluators are banned."""

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("DIRECT_FIXED crossed an operational authority")

    patcher = pytest.MonkeyPatch()
    fixed.run_direct_fixed_context_v1.cache_clear()
    for name in (
        "_acquire_row",
        "acquire_sparse_variable_graph_evidence_v1",
        "verify_sparse_variable_graph_evidence_v1",
        "run_variable_graph_context_v1",
        "_exact_ground_search_v1",
    ):
        patcher.setattr(graph, name, forbidden)
    patcher.setattr(fixed, "_evaluate_exact_policy", forbidden)
    try:
        built = tuple(
            fixed.run_direct_fixed_context_v1(context)
            for context in graph.registered_variable_order_contexts_v1()[:2]
        )
    finally:
        patcher.undo()
    verified = tuple(
        fixed.verify_direct_fixed_result_v1(item) for item in built
    )
    return built, verified


def test_complete_h2_fixed_rows_and_native_draw_counts(results) -> None:
    built, _ = results
    w5, k6 = built
    assert (
        w5.acquired_ground_rows,
        w5.target_generative_draws,
    ) == (30, 30 * 131_072)
    assert (
        k6.acquired_ground_rows,
        k6.target_generative_draws,
    ) == (60, 60 * 131_072)
    assert all(item.complete_h2_closure for item in built)
    assert all(
        item.structural_support_kernel_calls
        == item.operational_exact_kernel_queries
        == item.acquired_ground_rows
        for item in built
    )
    assert all(
        row.draw_count == fixed.FIXED_DRAWS_PER_ROW
        and row.generated_directly_from_draw_zero
        and row.v0066_packed_row_access_count == 0
        and row.operational_exact_probability_reads == 0
        for item in built
        for row in item.rows
    )


def test_fixed_profile_matches_anytime_estimator_at_fixed_horizon(
    results,
) -> None:
    built, _ = results
    assert tuple(
        item.profile.context_aggregate_obligation_count
        for item in built
    ) == (66, 132)
    assert {
        item.profile.family_aggregate_obligation_count for item in built
    } == {198}
    assert all(
        item.profile.target_half_width == Fraction(1, 140)
        and item.profile.per_obligation_tail_upper
        == Fraction(1, 250_000)
        and item.profile.fixed_sample_stopping
        and item.profile.anytime_valid_estimator
        for item in built
    )
    assert sum(
        (
            item.profile.context_tail_upper for item in built
        ),
        Fraction(0),
    ) == fixed.PROVEN_POSITIVE_FAMILY_TAIL_UPPER
    assert (
        fixed.PROVEN_POSITIVE_FAMILY_TAIL_UPPER
        < fixed.REGISTERED_GATE_TAIL_BUDGET
    )


def test_operational_robust_audits_certify_without_exact_reads(
    results,
) -> None:
    built, _ = results
    for result in built:
        assert (
            result.audit.outcome
            is fixed.DirectFixedAuditOutcome.CONDITIONALLY_CERTIFIED
        )
        assert result.audit.root_failure_upper < Fraction(1, 20)
        assert result.audit.root_reward_lower == Fraction(3, 64)
        assert result.audit.normalized_regret_upper == 0
        assert result.audit.exact_probability_reads == 0
        assert result.operational_exact_probability_reads == 0
        assert not result.standalone_evaluation_embedded
        assert not hasattr(result, "evaluation")


def test_standalone_verification_replays_raw_rows_and_exact_policy(
    results,
) -> None:
    built, verified = results
    for result, verification in zip(built, verified):
        assert verification.result_id == result.result_id
        assert verification.replayed_audit_id == result.audit.audit_id
        assert (
            verification.evaluation.audit_id
            == verification.replayed_audit_id
        )
        assert verification.raw_replay_passed
        assert verification.complete_closure_passed
        assert verification.no_v0066_packed_row_access_passed
        assert verification.operational_evaluation_separation_passed
        assert (
            verification.replayed_structural_support_kernel_calls
            == verification.replayed_operational_exact_kernel_queries
            == result.acquired_ground_rows
        )
        assert (
            verification.evaluation.exact_failure_probability
            == Fraction(99, 5_000)
        )
        assert (
            verification.evaluation.exact_normalized_reward
            == Fraction(3, 64)
        )
        assert verification.evaluation.audit_covers_exact_policy
        assert (
            verification.evaluation.evaluation_exact_kernel_calls
            == verification.evaluation.exact_policy_rows_evaluated
            > 0
        )


def test_paired_stream_ids_are_derived_from_typed_row_identity(
    results,
) -> None:
    built, verified = results
    for result, verification in zip(built, verified):
        expected = tuple(
            sorted(
                fixed.paired_stream_identity_v1(
                    row.context_id,
                    row.catalogue.catalogue_id,
                    row.action,
                    row.paired_v0066_seed,
                )
                for row in result.rows
            )
        )
        assert tuple(
            sorted(row.paired_stream_id for row in result.rows)
        ) == expected
        assert verification.replayed_paired_stream_ids == expected


def test_direct_prefix_guard_remains_strict_and_type_distinct(
    results,
) -> None:
    row = results[0][0].rows[0]
    assert type(row) is fixed.DirectFixedRowV1
    assert not isinstance(row, sequential.DirectPrefixRowV1)
    with pytest.raises(
        sequential.VariableGraphDirectSequentialInvariantViolation
    ):
        sequential.DirectPrefixRowV1(
            context_id=row.context_id,
            catalogue=row.catalogue,
            action=row.action,
            atom_descriptors=row.atom_descriptors,
            draw_count=row.draw_count,
            random_word_count=row.random_word_count,
            rejection_count=row.rejection_count,
            ordinal_counts=row.ordinal_counts,
            packed_ordinals=row.packed_ordinals,
            packed_rejection_flags=row.packed_rejection_flags,
            paired_v0066_seed=row.paired_v0066_seed,
            maximum_generated_draw_index=row.draw_count - 1,
        )


def test_negative_context_is_outside_positive_direct_fixed_authority() -> None:
    negative = graph.registered_variable_order_contexts_v1()[2]
    with pytest.raises(fixed.VariableGraphDirectFixedInvariantViolation):
        fixed.run_direct_fixed_context_v1(negative)


def test_raw_transcript_and_operational_lane_tampering_fail_closed(
    results,
) -> None:
    result = results[0][0]
    row = result.rows[0]
    changed = bytes([row.packed_ordinals[0] ^ 1]) + row.packed_ordinals[1:]
    with pytest.raises(fixed.VariableGraphDirectFixedInvariantViolation):
        replace(row, packed_ordinals=changed)
    with pytest.raises(fixed.VariableGraphDirectFixedInvariantViolation):
        replace(result, v0066_packed_row_access_count=1)
    with pytest.raises(fixed.VariableGraphDirectFixedInvariantViolation):
        replace(result, operational_exact_probability_reads=1)
    with pytest.raises(fixed.VariableGraphDirectFixedInvariantViolation):
        replace(result, operational_exact_kernel_queries=0)
    with pytest.raises(fixed.VariableGraphDirectFixedInvariantViolation):
        replace(result, standalone_evaluation_embedded=True)
