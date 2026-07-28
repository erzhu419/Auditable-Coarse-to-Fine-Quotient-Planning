from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

import acfqp.variable_graph_direct_sequential_v1 as direct
import acfqp.variable_order_graph_rapm_v1 as graph


@pytest.fixture(scope="module")
def results():
    contexts = graph.registered_variable_order_contexts_v1()
    built = tuple(
        direct.run_direct_sequential_context_v1(context)
        for context in contexts[:2]
    )
    verified = tuple(
        direct.verify_direct_sequential_result_v1(item)
        for item in built
    )
    return built, verified


def test_complete_cold_controls_stop_on_prefixes(results) -> None:
    built, _ = results
    w5, k6 = built
    assert (
        w5.acquired_ground_rows,
        w5.final_audit.checkpoint_draws_per_row,
        w5.target_generative_draws,
    ) == (30, 8_192, 245_760)
    assert (
        k6.acquired_ground_rows,
        k6.final_audit.checkpoint_draws_per_row,
        k6.target_generative_draws,
    ) == (60, 8_192, 491_520)
    assert sum(item.target_generative_draws for item in built) == 737_280
    assert all(
        item.final_audit.outcome
        is direct.DirectSequentialAuditOutcome.CONDITIONALLY_CERTIFIED
        for item in built
    )


def test_direct_family_uses_one_matched_confidence_budget(results) -> None:
    built, _ = results
    w5, k6 = built
    assert (
        w5.profile.context_aggregate_obligation_count,
        k6.profile.context_aggregate_obligation_count,
    ) == (66, 132)
    assert {
        item.profile.family_aggregate_obligation_count for item in built
    } == {198}
    assert (
        sum(
            (
                item.profile.context_tail_upper
                for item in built
            ),
            Fraction(0),
        )
        == direct.FAMILY_TAIL_UPPER
        == Fraction(198, 250_000)
    )
    assert all(
        item.profile.per_obligation_alpha == Fraction(1, 250_000)
        for item in built
    )


def test_exact_evaluation_is_standalone_and_covered(results) -> None:
    built, _ = results
    for result in built:
        assert result.evaluation.evaluation_lane == "STANDALONE_EVALUATION"
        assert result.evaluation.exact_failure_probability == Fraction(
            99, 5_000
        )
        assert result.evaluation.exact_normalized_reward == Fraction(3, 64)
        assert result.evaluation.audit_covers_exact_policy
        assert (
            result.evaluation.evaluation_exact_kernel_calls
            == result.evaluation.exact_policy_rows_evaluated
        )
        assert result.operational_exact_probability_reads == 0
        assert (
            result.structural_support_kernel_calls
            == result.operational_exact_kernel_queries
            == result.acquired_ground_rows
        )


def test_raw_prefix_and_first_stop_replay(results) -> None:
    built, verified = results
    for result, verification in zip(built, verified):
        assert verification.result_id == result.result_id
        assert verification.raw_prefix_replay_passed
        assert verification.first_certificate_stopping_passed
        assert verification.no_full_evidence_access_passed
        assert (
            verification.replayed_structural_support_kernel_calls
            == verification.replayed_operational_exact_kernel_queries
            == result.acquired_ground_rows
        )
        assert (
            verification.evaluation_exact_kernel_calls
            == result.evaluation.evaluation_exact_kernel_calls
        )
        assert all(
            row.draw_count < graph.SAMPLE_COUNT_PER_ROW
            and row.maximum_generated_draw_index == row.draw_count - 1
            for row in result.rows
        )


def test_direct_runner_rejects_negative_context() -> None:
    negative = graph.registered_variable_order_contexts_v1()[2]
    with pytest.raises(
        direct.VariableGraphDirectSequentialInvariantViolation
    ):
        direct.run_direct_sequential_context_v1(negative)


def test_full_evidence_or_operational_exact_access_cannot_be_injected(
    results,
) -> None:
    result = results[0][0]
    with pytest.raises(
        direct.VariableGraphDirectSequentialInvariantViolation
    ):
        replace(result, full_v0066_row_access_count=1)
    with pytest.raises(
        direct.VariableGraphDirectSequentialInvariantViolation
    ):
        replace(result, operational_exact_probability_reads=1)
    with pytest.raises(
        direct.VariableGraphDirectSequentialInvariantViolation
    ):
        replace(result, operational_exact_kernel_queries=0)


def test_packed_prefix_tampering_fails_closed(results) -> None:
    row = results[0][0].rows[0]
    changed = bytes([row.packed_ordinals[0] ^ 1]) + row.packed_ordinals[1:]
    with pytest.raises(
        direct.VariableGraphDirectSequentialInvariantViolation
    ):
        replace(row, packed_ordinals=changed)
