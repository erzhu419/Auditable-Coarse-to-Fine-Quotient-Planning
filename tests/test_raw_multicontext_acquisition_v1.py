from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.raw_multicontext_acquisition_v1 as raw
from acfqp.domains.g2048 import safe_chain_kernel


@pytest.fixture(scope="module")
def registered_inputs():
    catalogue = raw.registered_g2048_d4_statistical_catalogue_v1()
    preregistration = raw.preregister_raw_multicontext_campaign_v1(catalogue)
    kernels = raw.registered_raw_context_kernels_v1()
    return catalogue, preregistration, kernels


@pytest.fixture(scope="module")
def evidence(registered_inputs):
    catalogue, preregistration, kernels = registered_inputs
    return raw.acquire_raw_multicontext_evidence_v1(
        catalogue, preregistration, kernels
    )


@pytest.fixture(scope="module")
def result(registered_inputs, evidence):
    catalogue, preregistration, _ = registered_inputs
    return raw.run_raw_multicontext_campaign_v1(
        catalogue, preregistration, evidence
    )


@pytest.fixture(scope="module")
def verification(registered_inputs, evidence, result):
    catalogue, preregistration, kernels = registered_inputs
    return raw.verify_raw_multicontext_campaign_v1(
        catalogue,
        preregistration,
        evidence,
        kernels,
        result,
    )


def test_kernel_authority_is_excluded_from_production_interfaces() -> None:
    assert "kernel" not in inspect.signature(
        raw.build_raw_partial_statistical_model_v1
    ).parameters
    assert "kernel" not in inspect.signature(
        raw.run_raw_multicontext_campaign_v1
    ).parameters
    assert "kernels" in inspect.signature(
        raw.acquire_raw_multicontext_evidence_v1
    ).parameters
    assert "kernels" in inspect.signature(
        raw.verify_raw_multicontext_campaign_v1
    ).parameters


def test_preregistration_freezes_three_contexts_and_six_occurrences(
    registered_inputs,
) -> None:
    _, preregistration, _ = registered_inputs
    assert len(preregistration.contexts) == 3
    assert tuple(
        item.rank_one_probability for item in preregistration.contexts
    ) == (
        Fraction(199, 200),
        Fraction(249, 250),
        Fraction(999, 1000),
    )
    assert len(preregistration.occurrences) == 6
    assert tuple(
        item.initial_mode for item in preregistration.occurrences
    ) == ("D4_POINT",) * 3 + ("D4_UNIFORM",) * 3
    assert preregistration.prospective_log_ids_absent
    assert preregistration.prospective_model_ids_absent
    assert preregistration.prospective_plan_ids_absent
    assert safe_chain_kernel().spawn_distribution == (
        (1, Fraction(99, 100)),
        (2, Fraction(1, 100)),
    )


def test_failed_proof_authorizes_only_necessary_rows(evidence) -> None:
    for item in evidence.contexts:
        assert item.failed_proof.status == raw.FAILED_STATUS
        assert (
            item.failed_proof.required_missing_row_keys
            == raw.ADAPTIVE_ROW_KEYS
        )
        assert (
            item.authorization.authorized_row_keys
            == raw.ADAPTIVE_ROW_KEYS
        )
        assert (
            item.adaptive_log.authorization_id
            == item.authorization.authorization_id
        )
        assert item.direct_log.authorization_id is None


def test_packed_logs_embed_every_individual_draw(evidence) -> None:
    adaptive = sum(item.adaptive_log.total_draw_count for item in evidence.contexts)
    direct = sum(item.direct_log.total_draw_count for item in evidence.contexts)
    assert adaptive == raw.ADAPTIVE_TOTAL_DRAWS == 147_456
    assert direct == raw.DIRECT_TOTAL_DRAWS == 294_912
    for item in evidence.contexts:
        for log in (item.adaptive_log, item.direct_log):
            assert log.individual_draw_trace_embedded
            assert not log.aggregate_only_input
            assert not log.exact_probabilities_embedded
            assert all(codebook.exact_probabilities_absent for codebook in log.codebooks)
            assert sum(block.draw_count for block in log.blocks) == log.total_draw_count


def test_adaptive_models_keep_unobserved_rows_vacuous(result) -> None:
    for context_result in result.context_results:
        adaptive = context_result.adaptive_model
        direct = context_result.direct_model
        assert (adaptive.observed_row_count, adaptive.missing_row_count) == (3, 3)
        assert (direct.observed_row_count, direct.missing_row_count) == (6, 0)
        missing = tuple(
            row.catalogue_row.key
            for row in adaptive.rows
            if row.evidence is raw.RowEvidence.MISSING
        )
        assert missing == (
            "ROOT_AWAY",
            "CHAIN_A_TOWARD",
            "CHAIN_B_TOWARD",
        )
        for row in adaptive.rows:
            if row.evidence is raw.RowEvidence.MISSING:
                assert row.raw_log_id is None
                assert row.sample_count == 0
                assert all(
                    interval.lower == 0
                    and interval.upper == 1
                    and interval.empirical_probability is None
                    for interval in row.intervals
                )


def test_calibration_is_global_and_exact() -> None:
    profile = raw.RawAcquisitionProfileV1()
    assert profile.global_coordinate_obligations == 54
    assert profile.global_family_tail_upper == Fraction(27, 700)
    assert profile.global_confidence_lower == Fraction(673, 700)
    assert profile.global_confidence_lower > Fraction(19, 20)


def test_frozen_statistical_risk_bounds(result) -> None:
    assert tuple(
        item.adaptive_proof.selected_policy.failure_upper
        for item in result.context_results
    ) == (
        Fraction(11_153_865, 268_435_456),
        Fraction(2_575_781, 67_108_864),
        Fraction(34_527, 1_048_576),
    )
    assert tuple(
        item.direct_proof.selected_policy.failure_upper
        for item in result.context_results
    ) == (
        Fraction(1_382_201, 33_554_432),
        Fraction(10_511_905, 268_435_456),
        Fraction(8_871_139, 268_435_456),
    )
    assert all(
        item.adaptive_proof.selected_policy.failure_upper
        < Fraction(1, 20)
        and item.direct_proof.selected_policy.failure_upper
        < Fraction(1, 20)
        for item in result.context_results
    )


def test_second_query_per_context_reuses_frozen_models(result) -> None:
    assert tuple(
        (
            item.adaptive_new_draws,
            item.direct_new_draws,
            item.reused_frozen_models,
        )
        for item in result.occurrences
    ) == (
        (49_152, 98_304, False),
        (49_152, 98_304, False),
        (49_152, 98_304, False),
        (0, 0, True),
        (0, 0, True),
        (0, 0, True),
    )
    for first, second in zip(result.occurrences[:3], result.occurrences[3:]):
        assert first.occurrence.context_id == second.occurrence.context_id
        assert first.adaptive_model_id == second.adaptive_model_id
        assert first.direct_model_id == second.direct_model_id
        assert first.result_id != second.result_id


def test_work_preserves_control_semantics_and_claim_locks(result) -> None:
    work = result.work
    assert work.adaptive_individual_draws == 147_456
    assert work.direct_individual_draws == 294_912
    assert work.adaptive_draw_reduction_against_control == 147_456
    assert not work.matched_direct_ground_planning_claimed
    assert not work.sample_efficiency_claimed
    assert not work.sample_tax_operator_claimed
    assert work.official_scalar_cost is None
    assert work.official_n_break_even is None
    assert not result.statistical_exact_sound_claimed
    assert not result.broad_structural_generalization_claimed
    assert not result.official_execution_allowed
    assert not result.workload_economics_gate_run


def test_production_runner_cannot_call_context_kernel(
    monkeypatch, registered_inputs, evidence
) -> None:
    catalogue, preregistration, _ = registered_inputs

    def forbidden_step(*_args, **_kwargs):
        raise AssertionError("production attempted exact kernel access")

    monkeypatch.setattr(raw.RawSafeChainContextKernelV1, "step", forbidden_step)
    replay = raw.run_raw_multicontext_campaign_v1(
        catalogue, preregistration, evidence
    )
    assert replay.status == raw.SUCCESS_STATUS


def test_standalone_verifier_replays_raw_draws_and_exact_j0(
    result, verification
) -> None:
    assert verification.verified
    assert verification.failures == ()
    assert verification.raw_individual_draws_replayed == 442_368
    assert verification.production_kernel_access == 0
    assert verification.exact_ground_composed_candidates == 16_320
    assert tuple(
        item.selected_failure for item in verification.exact_comparators
    ) == (
        Fraction(199, 20_000),
        Fraction(249, 31_250),
        Fraction(999, 500_000),
    )
    by_context = {
        item.context.context_id: item for item in result.context_results
    }
    for comparator in verification.exact_comparators:
        context_result = by_context[comparator.context_id]
        for proof in (
            context_result.adaptive_proof,
            context_result.direct_proof,
        ):
            selected = proof.selected_policy
            assert selected.failure_lower <= comparator.selected_failure
            assert comparator.selected_failure <= selected.failure_upper


def test_single_draw_tamper_is_detected_by_independent_replay(
    registered_inputs, evidence
) -> None:
    catalogue, _, kernels = registered_inputs
    context_evidence = evidence.contexts[0]
    original = context_evidence.adaptive_log
    target_row_id = original.codebooks[0].catalogue_row_id
    changed_blocks = []
    previous = None
    for block in original.blocks:
        if block.catalogue_row_id != target_row_id:
            changed_blocks.append(block)
            continue
        nibbles = block.outcome_nibbles_hex
        if block.block_index == 0:
            replacement = "1" if nibbles[0] != "1" else "0"
            nibbles = replacement + nibbles[1:]
        rebuilt = replace(
            block,
            outcome_nibbles_hex=nibbles,
            previous_block_id=previous,
        )
        changed_blocks.append(rebuilt)
        previous = rebuilt.block_id
    tampered = replace(original, blocks=tuple(changed_blocks))
    failures, replayed = raw._independently_replay_raw_log_v1(
        catalogue,
        context_evidence.context,
        kernels[0],
        tampered,
    )
    assert replayed == 49_152
    assert any(item.startswith("RAW_DRAW_REPLAY_MISMATCH") for item in failures)


def test_aggregate_only_and_unregistered_contexts_are_rejected(
    registered_inputs, evidence
) -> None:
    catalogue, preregistration, kernels = registered_inputs
    with pytest.raises(raw.RawMultiContextInvariantViolation):
        replace(evidence.contexts[0].adaptive_log, aggregate_only_input=True)
    bad_kernel = raw.RawSafeChainContextKernelV1(
        size=2,
        context_key=kernels[0].context_key,
        rank_one_probability=Fraction(9, 10),
    )
    with pytest.raises(
        raw.RawMultiContextInvariantViolation,
        match="out-of-support",
    ):
        raw.acquire_raw_multicontext_evidence_v1(
            catalogue,
            preregistration,
            (bad_kernel, kernels[1], kernels[2]),
        )


def test_content_ids_replay_and_implementation_authority_are_frozen(
    registered_inputs, evidence, result
) -> None:
    catalogue, preregistration, _ = registered_inputs
    replay = raw.run_raw_multicontext_campaign_v1(
        catalogue, preregistration, evidence
    )
    assert replay.to_document() == result.to_document()
    assert replay.result_id == result.result_id
    assert raw._observed_implementation_sha256() == raw.IMPLEMENTATION_SHA256
