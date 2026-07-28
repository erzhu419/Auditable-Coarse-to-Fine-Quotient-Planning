from __future__ import annotations

import copy
from dataclasses import replace
from fractions import Fraction
import hashlib

import pytest

import acfqp.anytime_variable_graph_runner_v1 as anytime
import acfqp.variable_order_graph_rapm_v1 as graph
from acfqp.factorial_sample_efficiency_gate_v1 import (
    NO_PRIOR_SEQUENTIAL,
    REGISTERED_ARMS,
    FactorialSampleEfficiencyPreregistrationV1,
    TerminalClass,
    adapt_anytime_quotient_result_v1,
    build_registered_graph_occurrences_v1,
)


@pytest.fixture(scope="module")
def family() -> tuple[anytime.AnytimeVariableGraphResultV1, ...]:
    """Construct every target while all full-data target paths are disabled."""

    banned = (
        "_acquire_row",
        "acquire_sparse_variable_graph_evidence_v1",
        "verify_sparse_variable_graph_evidence_v1",
        "build_partial_statistical_rapm_v1",
        "target_relational_observation_log_v1",
        "generate_and_test_target_graph_programs_v1",
        "run_variable_graph_context_v1",
    )

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("V0-067 operational path touched full V0-066 data")

    patcher = pytest.MonkeyPatch()
    anytime.run_anytime_variable_graph_context_v1.cache_clear()
    for name in banned:
        patcher.setattr(graph, name, forbidden)
    try:
        skeleton = graph.portable_graph_source_skeleton_v1()
        results = tuple(
            anytime.run_anytime_variable_graph_context_v1(
                context,
                skeleton,
            )
            for context in graph.registered_variable_order_contexts_v1()
        )
    finally:
        patcher.undo()
    return results


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _by_key(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> dict[str, anytime.AnytimeVariableGraphResultV1]:
    return {item.context.context_key: item for item in family}


def test_operational_family_runs_with_every_full_data_path_disabled(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    assert len(family) == 3
    assert all(
        item.counters.full_131072_rows_materialized == 0
        and item.counters.v0066_full_evidence_constructor_calls == 0
        and item.counters.v0066_full_profile_reads == 0
        for item in family
    )
    assert all(
        row.direct_prefix_generation and not row.full_row_materialized
        for result in family
        for row in (
            result.final_evidence.root_rows
            + result.final_evidence.continuation_rows
        )
    )


def test_two_positive_contexts_stop_at_first_plan_certificate(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    results = _by_key(family)
    w5 = results["variable_target_w5_v0"]
    k6 = results["variable_target_k6_v0"]
    assert (
        w5.terminal
        is anytime.AnytimeVariableGraphTerminal.CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE
    )
    assert (
        k6.terminal
        is anytime.AnytimeVariableGraphTerminal.CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE
    )
    assert tuple(
        item.checkpoint_draw_count_per_row for item in w5.checkpoints
    ) == (2_048, 4_096, 8_192)
    assert tuple(
        item.checkpoint_draw_count_per_row for item in k6.checkpoints
    ) == (2_048, 4_096)
    assert not any(item.plan_certified for item in w5.checkpoints[:-1])
    assert not any(item.plan_certified for item in k6.checkpoints[:-1])
    assert w5.checkpoints[-1].plan_certified
    assert k6.checkpoints[-1].plan_certified
    # The source operator score uses a failure-event width proxy.  Target
    # stopping is the first sound plan certificate and does not inherit that
    # proxy as a certification requirement.
    proxy_width = 2 * Fraction(1, 140)
    assert w5.checkpoints[-1].maximum_aggregate_interval_width > proxy_width
    assert k6.checkpoints[-1].maximum_aggregate_interval_width > proxy_width


def test_native_draw_counts_are_16x_and_32x_below_v0066_positive_rows(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    results = _by_key(family)
    w5 = results["variable_target_w5_v0"]
    k6 = results["variable_target_k6_v0"]
    assert w5.final_evidence.ground_row_count == 22
    assert k6.final_evidence.ground_row_count == 60
    assert w5.counters.target_ordinal_draws == 22 * 8_192 == 180_224
    assert k6.counters.target_ordinal_draws == 60 * 4_096 == 245_760
    assert w5.counters.target_ordinal_draws * 16 == 2_883_584
    assert k6.counters.target_ordinal_draws * 32 == 7_864_320
    assert w5.counters.target_random_word_calls >= 180_224
    assert k6.counters.target_random_word_calls >= 245_760


def test_w5_refinement_is_regenerated_from_each_current_prefix_only(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    w5 = _by_key(family)["variable_target_w5_v0"]
    traces = tuple(item.program_trace for item in w5.checkpoints)
    assert all(trace is not None for trace in traces)
    concrete_traces = tuple(trace for trace in traces if trace is not None)
    assert len(
        {
            trace.generation.target_observation_log_id
            for trace in concrete_traces
        }
    ) == len(concrete_traces)
    for checkpoint, trace in zip(w5.checkpoints, concrete_traces):
        assert (
            trace.generation.target_observation_log_id
            == checkpoint.prefix_target_log_id
        )
        assert not checkpoint.full_data_profile_reused
    assert not concrete_traces[0].sound_cover_found
    assert not concrete_traces[1].sound_cover_found
    assert concrete_traces[2].sound_cover_found
    assert (
        concrete_traces[2].selected_program_rendered
        == "active_attribute_degree_signature"
    )
    assert (
        w5.final_profile.generation_id
        == concrete_traces[2].generation.generation_id
    )


def test_k6_certificate_uses_base_profile_at_4096(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    k6 = _by_key(family)["variable_target_k6_v0"]
    assert k6.checkpoints[0].program_trace is not None
    assert not k6.checkpoints[0].program_trace.sound_cover_found
    assert k6.checkpoints[1].program_trace is None
    assert k6.program_trace is None
    assert k6.final_profile.refinement_index == 0
    assert (
        k6.final_audit.outcome
        is graph.PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
    )


def test_negative_control_exhausts_cap_then_charges_exact_fallback_separately(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    negative = _by_key(family)["variable_negative_k6_minus_edge_v0"]
    assert (
        negative.terminal
        is anytime.AnytimeVariableGraphTerminal.FULL_GROUND_FALLBACK_AFTER_SEQUENTIAL_CAP
    )
    assert tuple(
        item.checkpoint_draw_count_per_row
        for item in negative.checkpoints
    ) == anytime.CHECKPOINTS
    assert not any(item.plan_certified for item in negative.checkpoints)
    assert negative.counters.target_ordinal_draws == 60 * 16_384 == 983_040
    assert negative.fallback_proof is not None
    assert negative.counters.fallback_exact_ground_rows == 60
    assert negative.counters.operational_exact_kernel_queries == 120
    assert (
        negative.fallback_proof.exact_failure_probability
        == Fraction(2_277, 16_000)
    )
    assert (
        negative.fallback_proof.failed_audit_id
        == negative.final_audit.audit_id
    )


def test_root_selection_is_frozen_at_first_checkpoint(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    for result in family:
        assert (
            result.final_evidence.root_selection_frozen_at_checkpoint
            == 2_048
        )
        assert result.counters.target_ground_rows == (
            result.final_evidence.ground_row_count
        )
        assert result.counters.structural_support_kernel_calls == (
            result.counters.target_ground_rows
        )
        assert result.counters.operational_exact_kernel_queries == (
            result.counters.structural_support_kernel_calls
            + result.counters.fallback_exact_ground_rows
        )
        assert result.counters.target_ordinal_draws == (
            result.final_evidence.generative_draw_count
        )


def test_all_287_obligations_use_one_alpha_without_checkpoint_multiplier(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    obligation_counts = tuple(
        item.final_evidence.preregistered_aggregate_obligation_count
        for item in family
    )
    assert obligation_counts == (47, 120, 120)
    assert sum(obligation_counts) == 287
    assert sum(
        (
            item.conditional_family_tail_upper for item in family
        ),
        Fraction(0),
    ) == Fraction(287, 250_000)
    assert all(
        item.sequential_profile.confidence_accounting
        == "ONE_ALPHA_VILLE_TIME_UNIFORM_NO_CHECKPOINT_ALPHA_SPENDING"
        for item in family
    )


def test_final_raw_ordinal_transcripts_replay_from_paired_seed(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    for result in family:
        rows = (
            result.final_evidence.root_rows
            + result.final_evidence.continuation_rows
        )
        assert sum(item.sample_count for item in rows) == (
            result.counters.target_ordinal_draws
        )
        assert all(
            anytime.verify_anytime_variable_graph_prefix_row_v1(
                result.context,
                row,
            )
            for row in rows
        )


def test_standalone_verifier_checks_canonical_replay_and_exact_ground_behavior(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    expected = {
        "variable_target_w5_v0": Fraction(1_337, 67_500),
        "variable_target_k6_v0": Fraction(99, 5_000),
        "variable_negative_k6_minus_edge_v0": Fraction(2_277, 16_000),
    }
    for result in family:
        verification = anytime.verify_anytime_variable_graph_result_v1(
            result
        )
        assert verification.result_id == result.result_id
        assert verification.paired_seed_replay_passed
        assert (
            verification.replayed_structural_support_kernel_calls
            == verification.replayed_prefix_rows
        )
        assert (
            verification.verified_operational_exact_kernel_queries
            == result.counters.operational_exact_kernel_queries
        )
        assert verification.actual_verifier_exact_kernel_queries == (
            verification.replayed_structural_support_kernel_calls
            + verification.evaluation_exact_kernel_calls
        )
        assert verification.prefix_generated_refinement_passed
        assert verification.no_full_data_leakage_passed
        assert verification.exact_lift_or_fallback_check_passed
        assert verification.exact_failure_probability == expected[
            result.context.context_key
        ]
        assert verification.exact_normalized_reward == Fraction(3, 64)
        assert verification.exact_policy_rows_evaluated > 0
        assert (
            verification.evaluation_exact_kernel_calls
            == verification.exact_policy_rows_evaluated
        )
    negative = _by_key(family)["variable_negative_k6_minus_edge_v0"]
    negative_verification = (
        anytime.verify_anytime_variable_graph_result_v1(negative)
    )
    assert negative_verification.exact_policy_rows_evaluated == 60
    assert (
        negative_verification.verified_operational_exact_kernel_queries
        == 120
    )
    assert negative_verification.actual_verifier_exact_kernel_queries == 120
    with pytest.raises(anytime.AnytimeVariableGraphInvariantViolation):
        replace(
            negative_verification,
            actual_verifier_exact_kernel_queries=180,
        )
    with pytest.raises(anytime.AnytimeVariableGraphInvariantViolation):
        replace(
            negative_verification,
            verified_operational_exact_kernel_queries=59,
        )


def test_w5_preserves_value_and_constraint_but_does_not_claim_risk_equality(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    w5 = _by_key(family)["variable_target_w5_v0"]
    verification = anytime.verify_anytime_variable_graph_result_v1(w5)
    assert w5.final_audit.normalized_reward_lower == Fraction(3, 64)
    assert verification.exact_failure_probability < Fraction(1, 20)
    assert verification.exact_failure_probability != Fraction(99, 5_000)
    assert not w5.sample_efficiency_claimed


def test_real_anytime_family_has_typed_factorial_gate_adapters(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    query_ids = {
        item.context_key: _id(f"anytime-gate-query:{item.context_key}")
        for item in graph.registered_variable_order_contexts_v1()
    }
    occurrences = build_registered_graph_occurrences_v1(query_ids, 1)
    preregistration = FactorialSampleEfficiencyPreregistrationV1(
        occurrences,
        REGISTERED_ARMS,
        _id("anytime-gate-source-prior"),
        _id("anytime-gate-claim-scope"),
        _id("anytime-gate-confidence-budget"),
    )
    adapted = tuple(
        adapt_anytime_quotient_result_v1(
            preregistration,
            next(
                occurrence
                for occurrence in occurrences
                if occurrence.context_id == result.context.context_id
            ),
            result,
            anytime.verify_anytime_variable_graph_result_v1(result),
        )
        for result in family
    )

    assert all(item.arm == NO_PRIOR_SEQUENTIAL for item in adapted)
    assert all(
        item.terminal_class is TerminalClass.PLAN_CERTIFICATE
        for item in adapted
    )
    assert tuple(item.work.acquisition_draws for item in adapted) == (
        180_224,
        245_760,
        983_040,
    )
    assert tuple(
        item.work.target_acquisition.exact_kernel_queries
        for item in adapted
    ) == (22, 60, 60)
    assert tuple(
        item.work.fallback.exact_kernel_queries for item in adapted
    ) == (0, 0, 60)
    assert all(item.prefix_coupling_verified for item in adapted)


def test_checkpoint_or_transcript_coordinated_tampering_fails_canonical_replay(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    original = _by_key(family)["variable_target_w5_v0"]

    checkpoint_attack = copy.copy(original)
    object.__setattr__(
        checkpoint_attack,
        "checkpoints",
        original.checkpoints[:-1],
    )
    with pytest.raises(anytime.AnytimeVariableGraphInvariantViolation):
        anytime.verify_anytime_variable_graph_result_v1(
            checkpoint_attack
        )

    row = original.final_evidence.root_rows[0]
    row_attack = copy.copy(row)
    changed = bytearray(row.packed_ordinals)
    changed[0] ^= 1
    object.__setattr__(row_attack, "packed_ordinals", bytes(changed))
    evidence_attack = copy.copy(original.final_evidence)
    object.__setattr__(
        evidence_attack,
        "root_rows",
        (row_attack,) + original.final_evidence.root_rows[1:],
    )
    transcript_attack = copy.copy(original)
    object.__setattr__(
        transcript_attack,
        "final_evidence",
        evidence_attack,
    )
    with pytest.raises(anytime.AnytimeVariableGraphInvariantViolation):
        anytime.verify_anytime_variable_graph_result_v1(
            transcript_attack
        )


def test_claim_locks_remain_narrow(
    family: tuple[anytime.AnytimeVariableGraphResultV1, ...],
) -> None:
    assert all(not item.sample_efficiency_claimed for item in family)
    assert all(item.target_local_intervals_only for item in family)
    assert all(item.exact_fallback_separately_charged for item in family)
    assert all(item.first_certificate_stopping for item in family)
