from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.sequential_source_stopping_v1 as stopping


@pytest.fixture(scope="module")
def artifacts():
    catalogue = (
        stopping.raw.registered_g2048_d4_statistical_catalogue_v1()
    )
    preregistration = (
        stopping.preregister_sequential_source_stopping_v1(catalogue)
    )
    source_kernels = stopping.v62.registered_source_kernels_v1()
    source_evidence = stopping.acquire_sequential_source_evidence_v1(
        catalogue, preregistration, source_kernels
    )
    source_prior = stopping.build_sequential_source_prior_v1(
        preregistration, source_evidence
    )
    target_kernels = stopping.raw.registered_raw_context_kernels_v1()
    baseline_evidence = (
        stopping.matched.acquire_matched_end_to_end_evidence_v1(
            catalogue,
            preregistration.base_preregistration.matched_preregistration,
            target_kernels,
        )
    )
    baseline_result = (
        stopping.matched.run_matched_end_to_end_workload_v1(
            catalogue,
            preregistration.base_preregistration.matched_preregistration,
            baseline_evidence,
        )
    )
    target_evidence = stopping.acquire_sequential_target_evidence_v1(
        preregistration, source_prior, baseline_evidence
    )
    result = stopping.run_sequential_sample_tax_campaign_v1(
        catalogue,
        preregistration,
        source_prior,
        target_evidence,
        baseline_result,
    )
    wrong_result = stopping.run_sequential_wrong_prior_control_v1(
        catalogue, preregistration, target_evidence
    )
    verification = stopping.verify_sequential_sample_tax_campaign_v1(
        catalogue,
        preregistration,
        source_evidence,
        source_kernels,
        target_evidence,
        baseline_evidence,
        target_kernels,
        baseline_result,
        result,
        wrong_result,
    )
    return {
        "catalogue": catalogue,
        "preregistration": preregistration,
        "source_kernels": source_kernels,
        "source_evidence": source_evidence,
        "source_prior": source_prior,
        "target_kernels": target_kernels,
        "baseline_evidence": baseline_evidence,
        "baseline_result": baseline_result,
        "target_evidence": target_evidence,
        "result": result,
        "wrong_result": wrong_result,
        "verification": verification,
    }


def test_preregistration_freezes_ordered_disjoint_authorities() -> None:
    catalogue = (
        stopping.raw.registered_g2048_d4_statistical_catalogue_v1()
    )
    preregistration = (
        stopping.preregister_sequential_source_stopping_v1(catalogue)
    )
    assert len(preregistration.ordered_source_contexts) == 3
    assert len(preregistration.target_context_ids) == 3
    assert len(preregistration.target_occurrence_ids) == 6
    assert {
        item.context_id
        for item in preregistration.ordered_source_contexts
    }.isdisjoint(preregistration.target_context_ids)
    assert preregistration.prospective_source_evidence_ids_absent
    assert preregistration.prospective_prior_id_absent
    assert preregistration.prospective_target_evidence_ids_absent
    assert preregistration.prospective_result_ids_absent
    assert preregistration.offline_and_online_lanes_separate
    assert not preregistration.official_execution_allowed


def test_source_stops_only_after_two_complete_contexts(artifacts) -> None:
    evidence = artifacts["source_evidence"]
    assert len(evidence.logs) == 2
    assert [item.decision for item in evidence.checkpoints] == [
        "CONTINUE_MIN_CONTEXTS",
        "STOP_UNIQUE_UNANIMOUS",
    ]
    assert evidence.checkpoints[0].unanimous_prefixes == (
        stopping.PROPOSAL_PREFIX,
    )
    assert evidence.checkpoints[0].frozen_prefix == ()
    assert evidence.checkpoints[1].frozen_prefix == (
        stopping.PROPOSAL_PREFIX
    )
    assert evidence.source_rows == 6
    assert evidence.source_individual_draws == 24_576
    assert evidence.source_exact_kernel_row_queries == 6
    assert len(evidence.unused_source_context_ids) == 1


def test_source_acquisition_never_enumerates_post_stop_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalogue = (
        stopping.raw.registered_g2048_d4_statistical_catalogue_v1()
    )
    preregistration = (
        stopping.preregister_sequential_source_stopping_v1(catalogue)
    )
    kernels = stopping.v62.registered_source_kernels_v1()
    forbidden = preregistration.ordered_source_contexts[2].context_key
    original = stopping.raw._row_outcomes
    visited: list[str] = []

    def guarded(catalogue_value, context, kernel, row):
        visited.append(context.context_key)
        if context.context_key == forbidden:
            raise AssertionError("post-stop source context was accessed")
        return original(catalogue_value, context, kernel, row)

    monkeypatch.setattr(stopping.raw, "_row_outcomes", guarded)
    evidence = stopping.acquire_sequential_source_evidence_v1(
        catalogue, preregistration, kernels
    )
    assert evidence.source_exact_kernel_row_queries == 6
    assert forbidden not in visited


def test_source_proposal_guard_has_no_certificate_authority(
    artifacts,
) -> None:
    prior = artifacts["source_prior"]
    assert prior.proposed_prefix == stopping.PROPOSAL_PREFIX
    assert prior.broad_tail == stopping.BROAD_TAIL
    assert not prior.proposal_guard_is_confidence_certificate
    assert not prior.may_narrow_target_envelopes
    assert not prior.may_certify_target_plans
    assert prior.target_context_ids_seen == ()
    assert prior.target_evidence_ids_seen == ()
    assert prior.target_kernel_access == 0


def test_production_interfaces_preserve_source_target_separation() -> None:
    source_parameters = inspect.signature(
        stopping.acquire_sequential_source_evidence_v1
    ).parameters
    prior_parameters = inspect.signature(
        stopping.build_sequential_source_prior_v1
    ).parameters
    target_parameters = inspect.signature(
        stopping.acquire_sequential_target_evidence_v1
    ).parameters
    runner_parameters = inspect.signature(
        stopping.run_sequential_sample_tax_campaign_v1
    ).parameters
    verifier_parameters = inspect.signature(
        stopping.verify_sequential_sample_tax_campaign_v1
    ).parameters
    assert "kernels" in source_parameters
    assert "target" not in source_parameters
    assert "kernel" not in prior_parameters
    assert "target" not in prior_parameters
    assert "kernel" not in target_parameters
    assert "kernel" not in runner_parameters
    assert "baseline_evidence" not in runner_parameters
    assert "source_kernels" in verifier_parameters
    assert "target_kernels" in verifier_parameters


def test_target_plans_remain_target_only_and_reusable(artifacts) -> None:
    target = artifacts["target_evidence"]
    result = artifacts["result"]
    assert target.online_operator_rows == 6
    assert target.online_operator_draws == 98_304
    assert target.online_no_operator_rows == 9
    assert target.online_no_operator_draws == 147_456
    assert len(result.contexts) == 3
    assert len(result.occurrences) == 6
    assert all(
        item.proof.status == stopping.raw.CERTIFIED_STATUS
        for item in result.contexts
    )
    assert sum(item.new_online_draws for item in result.occurrences) == 98_304
    assert sum(
        item.reused_operator_model for item in result.occurrences
    ) == 3
    assert result.target_confidence_lower == Fraction(347, 350)
    assert result.target_only_certificate


def test_registered_offline_plus_online_curve_is_strictly_better(
    artifacts,
) -> None:
    work = artifacts["result"].work
    assert work.v0062_fixed_source_draws == 147_456
    assert work.offline_source_individual_draws == 24_576
    assert work.source_draw_reduction_from_v0062 == 122_880
    assert work.online_operator_individual_draws == 98_304
    assert work.offline_inclusive_operator_draws == 122_880
    assert work.online_no_operator_control_individual_draws == 147_456
    assert work.offline_inclusive_draw_saving == 24_576
    assert work.offline_inclusive_reduction == Fraction(1, 6)
    assert work.diagnostic_context_break_even == 2
    assert work.registered_offline_inclusive_draw_reduction_observed
    assert work.official_scalar_cost is None
    assert work.official_n_break_even is None


def test_wrong_prior_still_fails_before_fallback(artifacts) -> None:
    wrong = artifacts["wrong_result"]
    assert wrong.prefix_failures == 3
    assert wrong.fallback_calls == 3
    assert wrong.final_certificates == 3
    assert wrong.false_certificates == 0
    assert all(
        item.failed_prefix_proof.status == stopping.raw.FAILED_STATUS
        and item.final_proof.status == stopping.raw.CERTIFIED_STATUS
        and not item.false_certificate_emitted
        for item in wrong.contexts
    )


def test_standalone_verifier_replays_source_baseline_and_exact_j0(
    artifacts,
) -> None:
    verification = artifacts["verification"]
    assert verification.verified
    assert verification.failures == ()
    assert verification.source_draws_replayed == 24_576
    assert verification.source_rows_replayed == 6
    assert verification.operator_visible_target_draws == 98_304
    assert (
        verification.unique_target_draws_replayed_by_baseline
        == 147_456
    )
    assert len(verification.comparators) == 6
    assert all(
        item.operator_exact_reward == item.j0_exact_reward
        and item.operator_exact_failure == item.j0_exact_failure
        and item.operator_exact_failure <= item.operator_failure_upper
        for item in verification.comparators
    )


def test_principal_content_ids_are_frozen(artifacts) -> None:
    assert artifacts["preregistration"].preregistration_id == (
        "603294fed3fa937e1a86bcfd119d0280cc61f20c86283119ee7a61f335e1d7b3"
    )
    assert artifacts["source_evidence"].evidence_id == (
        "4e7a5212f1675994a9b91abc108d7a6d7d22b8e30a8edb8b80580b9a3a9a8060"
    )
    assert artifacts["source_prior"].prior_id == (
        "148c5c63d495ee96ce5a9d1cf6c35b76f47150fddcf0d4e575e9876cc663505c"
    )
    assert artifacts["target_evidence"].evidence_id == (
        "0adb0820880a90d4e98ee51f89e50938e15ff94b44be79ad3e8c28d2bb914774"
    )
    assert artifacts["result"].result_id == (
        "d0590a56572514119f0572b6eb73d3416e3dea8f89f017045b0faeb3021a8028"
    )
    assert artifacts["wrong_result"].result_id == (
        "ca0e8e38f7640ab92c20f22f74f54b1d296d2b7e9c6648dad0534bcd253be529"
    )
    assert artifacts["verification"].verification_id == (
        "e2acd49e290d6a002e3eb2f82f148a18a507d3abc1f72b43046dc9a509a3a1a6"
    )
    assert artifacts["result"].work.work_id == (
        "2b3b79cc4e2485cc032735e24a1afc3c77da3b7e6657c262bf20725721679d03"
    )
    assert stopping.IMPLEMENTATION_SHA256 == (
        "03384f204c9f468aa447a1c7046cfaad2bfcad8d45bae89790820f876b6574bc"
    )


def test_one_source_draw_mutation_fails_independent_replay(artifacts) -> None:
    evidence = artifacts["source_evidence"]
    first_log = evidence.logs[0]
    first_block = first_log.blocks[0]
    replacement = (
        "1" if first_block.outcome_nibbles_hex[0] != "1" else "0"
    )
    bad_block = replace(
        first_block,
        outcome_nibbles_hex=(
            replacement + first_block.outcome_nibbles_hex[1:]
        ),
    )
    bad_log = replace(
        first_log,
        blocks=(bad_block, *first_log.blocks[1:]),
    )
    logs = (bad_log, evidence.logs[1])
    checkpoints = (
        stopping._checkpoint_v1(
            evidence.preregistration_id,
            artifacts["catalogue"],
            logs[:1],
        ),
        stopping._checkpoint_v1(
            evidence.preregistration_id,
            artifacts["catalogue"],
            logs,
        ),
    )
    bad_evidence = stopping.SequentialSourceEvidenceV1(
        evidence.preregistration_id,
        logs,
        checkpoints,
        evidence.unused_source_context_ids,
    )
    failures, draws, rows = (
        stopping._independently_replay_sequential_source_v1(
            artifacts["catalogue"],
            bad_evidence,
            artifacts["source_kernels"],
        )
    )
    assert draws == 24_576
    assert rows == 6
    assert any("SOURCE_DRAW_REPLAY_MISMATCH" in item for item in failures)


def test_checkpoint_and_log_identity_attacks_fail_closed(artifacts) -> None:
    first = artifacts["source_evidence"].checkpoints[0]
    with pytest.raises(
        stopping.SequentialSourceStoppingInvariantViolation,
        match="decision",
    ):
        replace(
            first,
            decision="STOP_UNIQUE_UNANIMOUS",
            frozen_prefix=stopping.PROPOSAL_PREFIX,
        )

    evidence = artifacts["source_evidence"]
    tampered_log = replace(
        evidence.logs[0],
        context_sequence_index=1,
    )
    with pytest.raises(
        stopping.SequentialSourceStoppingInvariantViolation,
        match="chronology|totals",
    ):
        stopping.SequentialSourceEvidenceV1(
            evidence.preregistration_id,
            (tampered_log, evidence.logs[1]),
            evidence.checkpoints,
            evidence.unused_source_context_ids,
        )


def test_implementation_pin_and_claim_locks_are_fail_closed(
    artifacts,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = artifacts["result"]
    assert result.registered_offline_inclusive_sample_reduction_claimed
    assert result.sequential_source_stopping_claimed
    assert not result.broad_sample_efficiency_claimed
    assert not result.automatic_coordinate_discovery_claimed
    assert not result.official_execution_allowed
    assert (
        result.sample_efficiency_gate_status
        == (
            "REGISTERED_OFFLINE_INCLUSIVE_INTERVENTION_"
            "PASSED_BROAD_GATE_NOT_RUN"
        )
    )
    monkeypatch.setattr(stopping, "IMPLEMENTATION_SHA256", "0" * 64)
    with pytest.raises(
        stopping.SequentialSourceStoppingInvariantViolation,
        match="implementation",
    ):
        stopping._validate_implementation_authority()
