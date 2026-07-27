from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.sample_tax_operator_v1 as sample_tax


@pytest.fixture(scope="module")
def artifacts():
    raw = sample_tax.raw
    matched = sample_tax.matched
    catalogue = raw.registered_g2048_d4_statistical_catalogue_v1()
    preregistration = sample_tax.preregister_sample_tax_operator_v1(
        catalogue
    )
    source_kernels = sample_tax.registered_source_kernels_v1()
    source_evidence = sample_tax.acquire_source_evidence_v1(
        catalogue, preregistration, source_kernels
    )
    source_prior = sample_tax.build_source_frozen_prior_v1(
        catalogue, preregistration, source_evidence
    )
    target_kernels = raw.registered_raw_context_kernels_v1()
    baseline_evidence = matched.acquire_matched_end_to_end_evidence_v1(
        catalogue,
        preregistration.matched_preregistration,
        target_kernels,
    )
    baseline_result = matched.run_matched_end_to_end_workload_v1(
        catalogue,
        preregistration.matched_preregistration,
        baseline_evidence,
    )
    target_evidence, wrong_evidence = (
        sample_tax.acquire_target_operator_evidence_v1(
            preregistration, source_prior, baseline_evidence
        )
    )
    result = sample_tax.run_sample_tax_operator_v1(
        catalogue,
        preregistration,
        source_prior,
        target_evidence,
        baseline_result,
    )
    wrong_result = sample_tax.run_wrong_prior_control_v1(
        catalogue, preregistration, wrong_evidence
    )
    verification = sample_tax.verify_sample_tax_operator_v1(
        catalogue,
        preregistration,
        source_evidence,
        source_kernels,
        target_evidence,
        wrong_evidence,
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
        "wrong_evidence": wrong_evidence,
        "result": result,
        "wrong_result": wrong_result,
        "verification": verification,
    }


def test_preregistration_freezes_disjoint_source_target_split() -> None:
    catalogue = (
        sample_tax.raw.registered_g2048_d4_statistical_catalogue_v1()
    )
    preregistration = sample_tax.preregister_sample_tax_operator_v1(
        catalogue
    )
    assert len(preregistration.source_contexts) == 3
    assert len(preregistration.target_context_ids) == 3
    assert len(preregistration.target_occurrence_ids) == 6
    assert {
        item.context_id for item in preregistration.source_contexts
    }.isdisjoint(preregistration.target_context_ids)
    assert preregistration.prospective_source_evidence_ids_absent
    assert preregistration.prospective_target_evidence_ids_absent
    assert preregistration.prospective_prior_id_absent
    assert preregistration.prospective_result_ids_absent
    assert preregistration.offline_and_online_lanes_separate
    assert not preregistration.official_execution_allowed


def test_production_interfaces_exclude_target_kernels() -> None:
    assert "kernels" in inspect.signature(
        sample_tax.acquire_source_evidence_v1
    ).parameters
    assert "kernels" not in inspect.signature(
        sample_tax.build_source_frozen_prior_v1
    ).parameters
    assert "target" not in inspect.signature(
        sample_tax.build_source_frozen_prior_v1
    ).parameters
    assert "kernel" not in inspect.signature(
        sample_tax.build_operator_partial_model_v1
    ).parameters
    assert "kernel" not in inspect.signature(
        sample_tax.solve_operator_partial_model_v1
    ).parameters
    assert "kernel" not in inspect.signature(
        sample_tax.run_sample_tax_operator_v1
    ).parameters
    assert "baseline_evidence" not in inspect.signature(
        sample_tax.run_sample_tax_operator_v1
    ).parameters
    assert "target_kernels" in inspect.signature(
        sample_tax.verify_sample_tax_operator_v1
    ).parameters


def test_source_integer_sampler_matches_exact_rational_protocol() -> None:
    probabilities = (
        Fraction(1, 200),
        Fraction(99, 200),
        Fraction(1, 200),
        Fraction(99, 200),
    )
    thresholds = sample_tax._integer_thresholds_v1(probabilities)
    cumulative = tuple(
        sum(probabilities[: index + 1], Fraction(0))
        for index in range(len(probabilities))
    )
    uniforms = (
        0,
        1,
        thresholds[0] - 1,
        thresholds[0],
        thresholds[1] - 1,
        thresholds[1],
        (1 << 256) - 1,
        *(
            sample_tax._source_uniform_v1(
                "source-equivalence",
                "0" * 64,
                "1" * 64,
                index,
            )
            for index in range(32)
        ),
    )
    for uniform in uniforms:
        rational = Fraction(uniform, 1 << 256)
        expected = next(
            index
            for index, threshold in enumerate(cumulative)
            if rational < threshold
        )
        assert sample_tax._sample_index_v1(thresholds, uniform) == expected


def test_source_prior_is_unanimous_proposal_only(artifacts) -> None:
    evidence = artifacts["source_evidence"]
    prior = artifacts["source_prior"]
    assert evidence.source_rows == 9
    assert evidence.source_individual_draws == 147_456
    assert evidence.target_evidence_ids_used == ()
    assert evidence.target_kernel_access == 0
    assert prior.proposed_prefix == (
        "ROOT_TOWARD",
        "CHAIN_A_AWAY",
    )
    assert prior.broad_tail == ("CHAIN_B_AWAY",)
    assert prior.target_context_ids_seen == ()
    assert prior.target_evidence_ids_seen == ()
    assert not prior.may_narrow_target_envelopes
    assert not prior.may_certify_target_plans
    by_context = {}
    for assessment in prior.assessments:
        by_context.setdefault(assessment.source_context_id, []).append(
            assessment
        )
    assert len(by_context) == 3
    for rows in by_context.values():
        certifying = tuple(
            item.observed_row_keys for item in rows if item.certifies
        )
        assert certifying == (
            ("ROOT_TOWARD", "CHAIN_A_AWAY"),
        )


def test_operator_uses_two_target_rows_and_certifies_all_occurrences(
    artifacts,
) -> None:
    evidence = artifacts["target_evidence"]
    result = artifacts["result"]
    assert evidence.observed_rows == 6
    assert evidence.individual_draws == 98_304
    assert evidence.broad_tail_rows_accessed == 0
    assert all(
        item.prefix_log.row_keys
        == ("ROOT_TOWARD", "CHAIN_A_AWAY")
        for item in evidence.contexts
    )
    assert tuple(
        item.proof.selected_policy.failure_upper
        for item in result.contexts
    ) == (
        Fraction(11_153_865, 268_435_456),
        Fraction(2_575_781, 67_108_864),
        Fraction(34_527, 1_048_576),
    )
    assert all(
        item.proof.status == sample_tax.raw.CERTIFIED_STATUS
        and item.model.observed_row_keys
        == ("ROOT_TOWARD", "CHAIN_A_AWAY")
        and item.fallback_rows == 0
        for item in result.contexts
    )
    assert len(result.occurrences) == 6
    assert tuple(
        (item.new_online_draws, item.reused_operator_model)
        for item in result.occurrences
    ) == (
        (32_768, False),
        (32_768, False),
        (32_768, False),
        (0, True),
        (0, True),
        (0, True),
    )


def test_unchanged_no_operator_and_cold_direct_controls_are_bound(
    artifacts,
) -> None:
    result = artifacts["result"]
    baseline = artifacts["baseline_result"]
    assert result.baseline_result_id == baseline.result_id
    assert baseline.work.adaptive_individual_draws == 147_456
    assert baseline.work.direct_individual_draws == 4_866_048
    assert baseline.work.registered_direct_to_adaptive_draw_ratio == 33
    for item, control in zip(result.occurrences, baseline.occurrences):
        assert (
            item.baseline_adaptive_proof_id
            == control.adaptive.adaptive_proof_id
        )
        assert item.baseline_direct_proof_id == control.direct.proof_id


def test_online_saving_and_offline_cost_are_not_conflated(
    artifacts,
) -> None:
    result = artifacts["result"]
    work = result.work
    assert work.offline_source_individual_draws == 147_456
    assert work.offline_source_environment_interactions == 0
    assert work.offline_source_generative_oracle_samples == 147_456
    assert work.offline_source_exact_kernel_queries == 9
    assert work.offline_source_logged_observations == 0
    assert work.offline_source_synthetic_model_rollouts == 0
    assert work.online_operator_individual_draws == 98_304
    assert work.online_operator_environment_interactions == 0
    assert work.online_operator_generative_oracle_samples == 98_304
    assert work.online_operator_exact_kernel_queries == 6
    assert work.online_operator_logged_observations == 0
    assert work.online_operator_synthetic_model_rollouts == 0
    assert work.online_no_operator_control_individual_draws == 147_456
    assert work.no_operator_control_generative_oracle_samples == 147_456
    assert work.no_operator_control_exact_kernel_queries == 9
    assert work.cold_direct_ground_generative_oracle_samples == 4_866_048
    assert work.cold_direct_ground_exact_kernel_queries == 198
    assert work.operator_online_draw_saving == 49_152
    assert work.operator_online_reduction == Fraction(1, 3)
    assert work.offline_inclusive_operator_draws == 245_760
    assert not work.offline_inclusive_draw_saving_observed
    assert work.diagnostic_source_amortization_contexts == 9
    assert work.evidence_event_taxonomy_complete
    assert work.official_scalar_cost is None
    assert work.official_n_break_even is None
    assert result.registered_sample_tax_operator_claimed
    assert not result.offline_inclusive_sample_reduction_claimed
    assert not result.broad_sample_efficiency_claimed
    assert (
        result.sample_efficiency_gate_status
        == "REGISTERED_INTERVENTION_GATE_PASSED_BROAD_GATE_NOT_RUN"
    )


def test_wrong_prior_fails_closed_then_uses_broad_tail(
    artifacts,
) -> None:
    result = artifacts["wrong_result"]
    assert result.status == sample_tax.WRONG_PRIOR_STATUS
    assert result.prefix_failures == 3
    assert result.fallback_calls == 3
    assert result.final_certificates == 3
    assert result.total_individual_draws == 147_456
    assert result.false_certificates == 0
    for item in result.contexts:
        assert item.prefix_model.observed_row_keys == (
            "ROOT_TOWARD",
            "CHAIN_B_AWAY",
        )
        assert item.failed_prefix_proof.status == sample_tax.raw.FAILED_STATUS
        assert item.failed_prefix_proof.required_tail_row_keys == (
            "CHAIN_A_AWAY",
        )
        assert item.final_model.observed_row_keys == sample_tax.SOURCE_ROW_KEYS
        assert item.final_proof.status == sample_tax.raw.CERTIFIED_STATUS
        assert not item.false_certificate_emitted


def test_production_runner_cannot_call_exact_kernel(
    monkeypatch, artifacts
) -> None:
    def forbidden_step(*_args, **_kwargs):
        raise AssertionError("production attempted exact kernel access")

    monkeypatch.setattr(
        sample_tax.raw.RawSafeChainContextKernelV1,
        "step",
        forbidden_step,
    )
    replay = sample_tax.run_sample_tax_operator_v1(
        artifacts["catalogue"],
        artifacts["preregistration"],
        artifacts["source_prior"],
        artifacts["target_evidence"],
        artifacts["baseline_result"],
    )
    wrong = sample_tax.run_wrong_prior_control_v1(
        artifacts["catalogue"],
        artifacts["preregistration"],
        artifacts["wrong_evidence"],
    )
    assert replay.result_id == artifacts["result"].result_id
    assert wrong.result_id == artifacts["wrong_result"].result_id


def test_standalone_verifier_replays_source_targets_and_exact_j0(
    artifacts,
) -> None:
    verification = artifacts["verification"]
    assert verification.verified
    assert verification.failures == ()
    assert verification.source_draws_replayed == 147_456
    assert verification.operator_visible_target_draws == 98_304
    assert verification.unique_target_draws_replayed_by_baseline == 147_456
    assert verification.wrong_control_visible_target_draws == 147_456
    assert tuple(
        item.j0_exact_failure for item in verification.comparators
    ) == (
        Fraction(199, 20_000),
        Fraction(249, 31_250),
        Fraction(999, 500_000),
        Fraction(199, 20_000),
        Fraction(249, 31_250),
        Fraction(999, 500_000),
    )
    assert all(
        item.operator_exact_reward
        == item.j0_exact_reward
        == Fraction(3, 64)
        and item.operator_exact_failure == item.j0_exact_failure
        <= item.operator_failure_upper
        <= Fraction(1, 20)
        for item in verification.comparators
    )


def test_target_draw_tamper_is_detected(artifacts) -> None:
    target = artifacts["target_evidence"]
    original_context = target.contexts[0]
    original_log = original_context.prefix_log
    first_codebook = original_log.codebooks[0]
    changed_blocks = []
    previous = None
    for block in original_log.blocks:
        nibbles = block.outcome_nibbles_hex
        if (
            block.catalogue_row_id == first_codebook.catalogue_row_id
            and block.block_index == 0
        ):
            replacement = "1" if nibbles[0] != "1" else "0"
            nibbles = replacement + nibbles[1:]
        if block.catalogue_row_id != first_codebook.catalogue_row_id:
            previous_for_block = block.previous_block_id
        else:
            previous_for_block = previous
        rebuilt = replace(
            block,
            outcome_nibbles_hex=nibbles,
            previous_block_id=previous_for_block,
        )
        changed_blocks.append(rebuilt)
        if block.catalogue_row_id == first_codebook.catalogue_row_id:
            previous = rebuilt.block_id
    changed_log = replace(
        original_log, blocks=tuple(changed_blocks)
    )
    changed_context = replace(
        original_context, prefix_log=changed_log
    )
    changed_target = replace(
        target,
        contexts=(changed_context,) + target.contexts[1:],
    )
    verification = sample_tax.verify_sample_tax_operator_v1(
        artifacts["catalogue"],
        artifacts["preregistration"],
        artifacts["source_evidence"],
        artifacts["source_kernels"],
        changed_target,
        artifacts["wrong_evidence"],
        artifacts["baseline_evidence"],
        artifacts["target_kernels"],
        artifacts["baseline_result"],
        artifacts["result"],
        artifacts["wrong_result"],
    )
    assert not verification.verified
    assert "TARGET_EVIDENCE_RECONSTRUCTION_MISMATCH" in verification.failures


def test_target_leakage_and_implementation_mutation_fail_closed(
    monkeypatch, artifacts
) -> None:
    with pytest.raises(sample_tax.SampleTaxOperatorInvariantViolation):
        replace(
            artifacts["source_prior"],
            target_context_ids_seen=(
                artifacts["preregistration"].target_context_ids[0],
            ),
        )
    monkeypatch.setattr(
        sample_tax,
        "IMPLEMENTATION_SHA256",
        "f" * 64,
    )
    with pytest.raises(
        sample_tax.SampleTaxOperatorInvariantViolation,
        match="frozen authority",
    ):
        sample_tax.run_sample_tax_operator_v1(
            artifacts["catalogue"],
            artifacts["preregistration"],
            artifacts["source_prior"],
            artifacts["target_evidence"],
            artifacts["baseline_result"],
        )


def test_frozen_content_ids_and_implementation_digest(artifacts) -> None:
    assert (
        sample_tax._observed_implementation_sha256()
        == sample_tax.IMPLEMENTATION_SHA256
        == "decc1f2f34d08cdec9eefe72d5c645ef8a50af5c8692ec9beecd82d48b21b2da"
    )
    assert (
        artifacts["preregistration"].preregistration_id
        == "f6b9e5e689123e91c04192117af39ea58a7d8985525e9b87391c966df956ddda"
    )
    assert (
        artifacts["source_evidence"].evidence_id
        == "5f071a9991783edfcd24f146fbebaf3817165bdbb59189c499ebef7791c030d0"
    )
    assert (
        artifacts["source_prior"].prior_id
        == "f65f5baa7ffc85df63ddc585077d896d01db8c134443ff4012be6c5fc30a9d2d"
    )
    assert (
        artifacts["target_evidence"].evidence_id
        == "e5f02b06f116b1c3e44c34d17e9e8e5823331cd761badac9613c2ad51ea93550"
    )
    assert (
        artifacts["result"].result_id
        == "1ba8e353322d9833d893ab0526f4254ebe979968d9a23ac81065db4fbf941037"
    )
    assert (
        artifacts["verification"].verification_id
        == "ded946c44d7052b014419d5b7a196a70db7ef25ec2903df0bd87167ec10f791a"
    )
