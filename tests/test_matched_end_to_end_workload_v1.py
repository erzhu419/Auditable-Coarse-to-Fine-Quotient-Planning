from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.matched_end_to_end_workload_v1 as matched


@pytest.fixture(scope="module")
def registered_inputs():
    catalogue = (
        matched.raw.registered_g2048_d4_statistical_catalogue_v1()
    )
    preregistration = (
        matched.preregister_matched_end_to_end_workload_v1(catalogue)
    )
    kernels = matched.raw.registered_raw_context_kernels_v1()
    return catalogue, preregistration, kernels


@pytest.fixture(scope="module")
def evidence(registered_inputs):
    catalogue, preregistration, kernels = registered_inputs
    return matched.acquire_matched_end_to_end_evidence_v1(
        catalogue, preregistration, kernels
    )


@pytest.fixture(scope="module")
def result(registered_inputs, evidence):
    catalogue, preregistration, _ = registered_inputs
    return matched.run_matched_end_to_end_workload_v1(
        catalogue, preregistration, evidence
    )


@pytest.fixture(scope="module")
def verification(registered_inputs, evidence, result):
    catalogue, preregistration, kernels = registered_inputs
    return matched.verify_matched_end_to_end_workload_v1(
        catalogue,
        preregistration,
        evidence,
        kernels,
        result,
    )


def test_production_interfaces_exclude_exact_kernels() -> None:
    assert "kernel" not in inspect.signature(
        matched.plan_cold_direct_ground_v1
    ).parameters
    assert "kernel" not in inspect.signature(
        matched.run_matched_end_to_end_workload_v1
    ).parameters
    assert "kernels" in inspect.signature(
        matched.acquire_matched_end_to_end_evidence_v1
    ).parameters
    assert "kernels" in inspect.signature(
        matched.verify_matched_end_to_end_workload_v1
    ).parameters


def test_preregistration_freezes_matched_routes(registered_inputs) -> None:
    _, preregistration, _ = registered_inputs
    assert len(preregistration.source_preregistration.contexts) == 3
    assert len(preregistration.source_preregistration.occurrences) == 6
    assert preregistration.direct_known_finite_support_and_action_catalogue
    assert preregistration.direct_cross_occurrence_model_reuse_forbidden
    assert preregistration.adaptive_context_model_reuse_registered
    assert not preregistration.automatic_coordinate_discovery_claimed
    assert not preregistration.sample_tax_operator_registered
    assert not preregistration.official_execution_allowed


def test_global_calibration_is_exact_and_joint() -> None:
    profile = matched.MatchedAcquisitionProfileV1(
        matched.raw.RawAcquisitionProfileV1().profile_id
    )
    assert profile.direct_exponent == 12
    assert profile.adaptive_obligations == 18
    assert profile.direct_obligations == 252
    assert profile.combined_family_tail_upper == Fraction(783, 43_750)
    assert profile.combined_confidence_lower == Fraction(42_967, 43_750)
    assert profile.combined_confidence_lower > Fraction(49, 50)
    assert (
        profile.direct_counter_uniform_protocol
        == "sha256_counter_uint256_ceil_cdf_v1"
    )


def test_integer_threshold_sampler_exactly_matches_rational_protocol() -> None:
    probabilities = (
        Fraction(1, 100),
        Fraction(33, 100),
        Fraction(33, 100),
        Fraction(33, 100),
    )
    thresholds = matched._integer_cumulative_thresholds_v1(probabilities)
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
            matched._direct_uniform_v1(
                "equivalence-test",
                "0" * 64,
                "1" * 64,
                "2" * 64,
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
        assert (
            matched._sample_outcome_index(thresholds, uniform)
            == expected
        )
    expected_block = "".join(
        format(
            matched._sample_outcome_index(
                thresholds,
                matched._direct_uniform_v1(
                    "equivalence-test",
                    "0" * 64,
                    "1" * 64,
                    "2" * 64,
                    index,
                ),
            ),
            "x",
        )
        for index in range(32)
    )
    assert (
        matched._direct_draw_block_nibbles_v1(
            "equivalence-test",
            "0" * 64,
            "1" * 64,
            "2" * 64,
            thresholds,
            0,
            32,
        )
        == expected_block
    )
    assert (
        matched._independent_direct_draw_block_nibbles_v1(
            "equivalence-test",
            "0" * 64,
            "1" * 64,
            "2" * 64,
            thresholds,
            0,
            32,
        )
        == expected_block
    )


def test_adaptive_evidence_is_failed_proof_directed(evidence) -> None:
    assert evidence.adaptive_total_draws == 147_456
    for item in evidence.adaptive_contexts:
        assert item.failed_proof.status == matched.raw.FAILED_STATUS
        assert (
            item.failed_proof.required_missing_row_keys
            == matched.raw.ADAPTIVE_ROW_KEYS
        )
        assert (
            item.authorization.authorized_row_keys
            == matched.raw.ADAPTIVE_ROW_KEYS
        )
        assert item.adaptive_log.total_draw_count == 49_152


def test_direct_ground_evidence_is_cold_complete_and_raw(evidence) -> None:
    assert evidence.direct_total_draws == 4_866_048
    assert tuple(
        (
            item.reachable_state_time_pairs,
            item.action_rows,
            item.h1_action_rows,
            item.root_action_rows,
            item.statistical_obligations,
        )
        for item in evidence.direct_occurrences
    ) == (
        (6, 18, 16, 2, 20),
        (6, 18, 16, 2, 20),
        (6, 18, 16, 2, 20),
        (20, 48, 32, 16, 64),
        (20, 48, 32, 16, 64),
        (20, 48, 32, 16, 64),
    )
    all_row_ids = []
    for item in evidence.direct_occurrences:
        assert item.occurrence_local_cold_model
        assert not item.cross_occurrence_reuse
        assert item.state_action_catalogue_calls == (
            item.reachable_state_time_pairs
        )
        assert item.transition_row_enumerations == item.action_rows
        for row in item.rows:
            assert row.individual_draw_trace_embedded
            assert not row.exact_probabilities_embedded
            assert row.codebook.exact_probabilities_absent
            assert row.sample_count == 24_576
            all_row_ids.append(row.codebook.row_id)
    assert len(all_row_ids) == len(set(all_row_ids)) == 198


def test_both_routes_certify_every_occurrence(result) -> None:
    assert result.status == matched.SUCCESS_STATUS
    assert result.combined_confidence_lower == Fraction(42_967, 43_750)
    assert len(result.occurrences) == 6
    assert all(
        item.adaptive.failure_upper < Fraction(1, 20)
        and item.direct.selected_policy.failure_upper < Fraction(1, 20)
        for item in result.occurrences
    )
    assert all(
        item.direct.normalized_regret_upper <= Fraction(1, 20)
        and item.direct.status == matched.DIRECT_CERTIFIED_STATUS
        for item in result.occurrences
    )


def test_frozen_direct_statistical_risk_bounds(result) -> None:
    assert tuple(
        item.direct.selected_policy.failure_upper
        for item in result.occurrences
    ) == (
        Fraction(12_533_567, 301_989_888),
        Fraction(3_968_317, 100_663_296),
        Fraction(20_009_551, 603_979_776),
        Fraction(197_945_945, 4_831_838_208),
        Fraction(31_379_491, 805_306_368),
        Fraction(40_027_739, 1_207_959_552),
    )
    assert tuple(
        len(item.direct.root_candidates) for item in result.occurrences
    ) == (2, 2, 2, 256, 256, 256)


def test_only_adaptive_arm_reuses_context_models(result) -> None:
    assert tuple(
        (
            item.adaptive.new_individual_draws,
            item.adaptive.reused_frozen_context_model,
            item.direct_model_reused,
        )
        for item in result.occurrences
    ) == (
        (49_152, False, False),
        (49_152, False, False),
        (49_152, False, False),
        (0, True, False),
        (0, True, False),
        (0, True, False),
    )
    for first, second in zip(
        result.occurrences[:3], result.occurrences[3:]
    ):
        assert first.occurrence.context_id == second.occurrence.context_id
        assert (
            first.adaptive.adaptive_model_id
            == second.adaptive.adaptive_model_id
        )
        assert first.direct.evidence_id != second.direct.evidence_id


def test_work_records_registered_33x_difference_without_overclaim(
    result,
) -> None:
    work = result.work
    assert work.adaptive_individual_draws == 147_456
    assert work.direct_individual_draws == 4_866_048
    assert work.registered_direct_to_adaptive_draw_ratio == 33
    assert work.adaptive_fallback_calls == 0
    assert work.direct_fallback_calls == 0
    assert work.noncertificate_occurrence_closures == 0
    assert work.matched_direct_ground_planning_control
    assert work.registered_workload_draw_advantage_observed
    assert not work.broad_sample_efficiency_claimed
    assert not work.sample_tax_operator_claimed
    assert work.official_scalar_cost is None
    assert work.official_n_break_even is None
    assert not result.automatic_coordinate_discovery_claimed
    assert not result.broad_structural_generalization_claimed
    assert not result.official_execution_allowed
    assert not result.workload_economics_gate_run


def test_production_runner_cannot_call_exact_kernel(
    monkeypatch, registered_inputs, evidence
) -> None:
    catalogue, preregistration, _ = registered_inputs

    def forbidden_step(*_args, **_kwargs):
        raise AssertionError("production attempted exact kernel access")

    monkeypatch.setattr(
        matched.raw.RawSafeChainContextKernelV1,
        "step",
        forbidden_step,
    )
    replay = matched.run_matched_end_to_end_workload_v1(
        catalogue, preregistration, evidence
    )
    assert replay.status == matched.SUCCESS_STATUS


def test_standalone_verifier_replays_both_arms_and_exact_j0(
    verification,
) -> None:
    assert verification.verified
    assert verification.failures == ()
    assert verification.adaptive_individual_draws_replayed == 147_456
    assert verification.direct_individual_draws_replayed == 4_866_048
    assert verification.direct_transition_rows_replayed == 198
    assert verification.exact_ground_composed_candidates == 16_386
    assert tuple(
        item.j0_exact_failure for item in verification.exact_comparators
    ) == (
        Fraction(199, 20_000),
        Fraction(249, 31_250),
        Fraction(999, 500_000),
        Fraction(199, 20_000),
        Fraction(249, 31_250),
        Fraction(999, 500_000),
    )
    assert all(
        item.adaptive_exact_reward
        == item.direct_exact_reward
        == item.j0_exact_reward
        == Fraction(3, 64)
        and item.adaptive_exact_failure
        == item.j0_exact_failure
        and item.j0_exact_failure
        <= item.direct_exact_failure
        < Fraction(1, 20)
        and item.direct_failure_gap_from_j0 <= Fraction(1, 1000)
        for item in verification.exact_comparators
    )


def test_single_direct_draw_tamper_is_detected(
    registered_inputs, evidence
) -> None:
    _, _, kernels = registered_inputs
    original_occurrence = evidence.direct_occurrences[0]
    original_row = original_occurrence.rows[0]
    changed_blocks = []
    previous = None
    for block in original_row.blocks:
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
    changed_row = replace(
        original_row, blocks=tuple(changed_blocks)
    )
    changed_occurrence = replace(
        original_occurrence,
        rows=(changed_row,) + original_occurrence.rows[1:],
    )
    failures, replayed, rows = (
        matched._independently_replay_direct_occurrence_v1(
            changed_occurrence, kernels[0]
        )
    )
    assert replayed == 442_368
    assert rows == 18
    assert any(
        item.startswith("DIRECT_DRAW_REPLAY_MISMATCH")
        for item in failures
    )


def test_missing_ground_row_and_cross_occurrence_reuse_are_rejected(
    evidence,
) -> None:
    with pytest.raises(matched.MatchedEndToEndInvariantViolation):
        replace(
            evidence.direct_occurrences[0],
            rows=evidence.direct_occurrences[0].rows[:-1],
            action_rows=17,
            transition_row_enumerations=17,
            total_draw_count=17 * 24_576,
        )
    with pytest.raises(matched.MatchedEndToEndInvariantViolation):
        replace(
            evidence.direct_occurrences[0],
            cross_occurrence_reuse=True,
        )


def test_content_ids_and_implementation_authority_are_frozen(
    registered_inputs, evidence, result, verification
) -> None:
    catalogue, preregistration, _ = registered_inputs
    replay = matched.run_matched_end_to_end_workload_v1(
        catalogue, preregistration, evidence
    )
    assert replay.to_document() == result.to_document()
    assert replay.result_id == result.result_id
    assert (
        matched._observed_implementation_sha256()
        == matched.IMPLEMENTATION_SHA256
    )
    assert catalogue.catalogue_id == (
        "1c97e476c25b0a1f0f37ce2796ae4cf9bb138bf29dbd80271792e2ef988dbcb1"
    )
    assert preregistration.preregistration_id == (
        "004d647e84f22d6a566b61d107188e2c65925637cee1f919e6a7522e0e4b9223"
    )
    assert evidence.bundle_id == (
        "c0cdae3f2aa81289a95222ce18c63a1973663839ed39f805c1933a6a48804356"
    )
    assert result.result_id == (
        "c120b86d4d5ed3c3aec9ea33ffd5ca9545ec5d71465165a67d9379ebcd01c26d"
    )
    assert verification.verification_id == (
        "1916f243008fd428c76d47eb29d8d44a35957dfc1e43819de33796e1ef77fe4b"
    )
