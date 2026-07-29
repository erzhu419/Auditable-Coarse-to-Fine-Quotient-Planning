from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
from itertools import product

import pytest

import acfqp.sequential_bernoulli_acquisition_v1 as seq


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture
def binding() -> seq.TargetLocalBernoulliRowBindingV1:
    return seq.TargetLocalBernoulliRowBindingV1(
        structural_id=_id("structure"),
        target_context_id=_id("target-context"),
        target_row_id=_id("target-row"),
        draw_source_id=_id("target-simulator"),
        outcome_semantics_id=_id("failure-event"),
        row_key="failure-after-selected-semantic-action",
    )


def _small_profile(
    *,
    half_width: Fraction = Fraction(1, 32),
    alpha: Fraction = Fraction(1, 1_000),
    checkpoints: tuple[int, ...] = (
        64,
        128,
        256,
        512,
        1_024,
        2_048,
        4_096,
    ),
) -> seq.SequentialBernoulliProfileV1:
    return seq.SequentialBernoulliProfileV1(
        confidence_alpha=alpha,
        target_half_width=half_width,
        checkpoints=checkpoints,
        boundary_grid_bits=16,
    )


def test_profile_is_one_alpha_time_uniform_and_target_local() -> None:
    profile = seq.v0067_default_sequential_profile_v1()
    assert profile.confidence_alpha == Fraction(1, 250_000)
    assert profile.target_half_width == Fraction(1, 140)
    assert profile.min_draws == 256
    assert profile.max_draws == 131_072
    assert profile.method_id == (
        "uniform_beta_binomial_likelihood_mixture_ville_cs_v1"
    )
    assert profile.confidence_accounting == (
        "ONE_ALPHA_VILLE_TIME_UNIFORM_NO_CHECKPOINT_ALPHA_SPENDING"
    )
    assert profile.interval_evidence_scope == "TARGET_ROW_DRAWS_ONLY"
    assert "SOURCE_OR_META_PRIOR" in profile.reference_mixture


def test_exact_mixture_formula_and_rejection_predicate() -> None:
    # B(3, 3) = 2! 2! / 5! = 1/30 for one particular length-4
    # sequence with two successes.
    assert seq.beta_binomial_sequence_mass_v1(4, 2) == Fraction(1, 30)
    assert seq.bernoulli_likelihood_v1(
        4,
        2,
        Fraction(1, 2),
    ) == Fraction(1, 16)
    assert not seq.bernoulli_mixture_rejects_v1(
        4,
        2,
        Fraction(1, 2),
        Fraction(1, 4),
    )
    assert seq.bernoulli_mixture_rejects_v1(
        4,
        2,
        Fraction(0),
        Fraction(1, 4),
    )


def test_exact_math_memoization_is_byte_neutral_and_clearable() -> None:
    seq.clear_exact_bernoulli_math_cache_v1()
    profile = _small_profile()
    first = seq.build_anytime_bernoulli_checkpoint_v1(2_048, 21, profile)
    before = seq._outer_confidence_bounds.cache_info()
    second = seq.build_anytime_bernoulli_checkpoint_v1(2_048, 21, profile)
    after = seq._outer_confidence_bounds.cache_info()
    assert second == first
    assert second.to_document() == first.to_document()
    assert after.hits > before.hits
    seq.clear_exact_bernoulli_math_cache_v1()
    cleared = seq._outer_confidence_bounds.cache_info()
    assert cleared.currsize == 0
    assert cleared.hits == 0


def test_dyadic_bounds_outer_cover_exact_accepted_grid() -> None:
    alpha = Fraction(1, 1_000)
    denominator = 1 << 8
    for draw_count in range(1, 13):
        for success_count in range(draw_count + 1):
            lower, upper, _, _ = seq._outer_confidence_bounds(
                draw_count,
                success_count,
                alpha,
                8,
            )
            accepted = tuple(
                Fraction(index, denominator)
                for index in range(denominator + 1)
                if not seq.bernoulli_mixture_rejects_v1(
                    draw_count,
                    success_count,
                    Fraction(index, denominator),
                    alpha,
                )
            )
            assert accepted
            assert lower <= min(accepted)
            assert upper >= max(accepted)


def test_optional_gmp_backend_is_bit_exact_with_python_integer_formula() -> None:
    if seq._GMP_EXACT_BACKEND is None:
        pytest.skip("system GMP exact backend is unavailable")
    alpha = Fraction(1, 250_000)
    denominator = 1 << 16
    boundary_cases = (
        (64, 0, 1),
        (64, 1, 2_048),
        (1_024, 10, 512),
        (8_192, 82, 640),
        (8_192, 4_096, 32_768),
        (17, 0, 0),
        (17, 17, denominator),
        (17, 1, denominator - 1),
    )
    deterministic_cases = tuple(
        (
            draw_count,
            (draw_count * 37 + index * 11) % (draw_count + 1),
            (index * 7_919 + draw_count * 101) % (denominator + 1),
        )
        for index, draw_count in enumerate(
            (3, 5, 9, 17, 33, 65, 129, 257, 513, 1_025)
        )
    )
    for draw_count, success_count, grid_index in (
        boundary_cases + deterministic_cases
    ):
        exact = seq._ExactGridRejectionV1(
            draw_count,
            success_count,
            alpha,
            denominator,
        )
        observed = exact.rejects(grid_index)
        likelihood_numerator = (
            grid_index**success_count
            * (denominator - grid_index)
            ** (draw_count - success_count)
        )
        expected = (
            likelihood_numerator * exact.left_coefficient
            <= alpha.numerator * denominator**draw_count
        )
        assert observed is expected


@pytest.mark.parametrize(
    "probability",
    (
        Fraction(1, 10),
        Fraction(1, 3),
        Fraction(1, 2),
        Fraction(9, 10),
    ),
)
def test_exact_finite_horizon_anytime_crossing_probability_is_below_alpha(
    probability: Fraction,
) -> None:
    """Enumerate paths; the event is crossing at *any* prefix, not at n=8."""

    alpha = Fraction(1, 4)
    horizon = 8
    crossing_probability = Fraction(0)
    for path in product((False, True), repeat=horizon):
        crossed = any(
            seq.bernoulli_mixture_rejects_v1(
                draw_count,
                sum(path[:draw_count]),
                probability,
                alpha,
            )
            for draw_count in range(1, horizon + 1)
        )
        if crossed:
            successes = sum(path)
            crossing_probability += (
                probability ** successes
                * (1 - probability) ** (horizon - successes)
            )
    assert crossing_probability <= alpha


def test_low_variance_row_stops_much_earlier_than_balanced_row(
    binding: seq.TargetLocalBernoulliRowBindingV1,
) -> None:
    profile = _small_profile()
    rare = seq.acquire_sequential_bernoulli_row_v1(
        binding,
        profile,
        (index % 100 == 0 for index in range(profile.max_draws)),
    )
    balanced = seq.acquire_sequential_bernoulli_row_v1(
        binding,
        profile,
        (index % 2 == 0 for index in range(profile.max_draws)),
    )
    assert rare.outcome is (
        seq.SequentialBernoulliOutcome.CERTIFIED_TARGET_LOCAL_INTERVAL
    )
    assert rare.draw_count == 512
    assert balanced.outcome is seq.SequentialBernoulliOutcome.CAP_EXHAUSTED
    assert balanced.draw_count == 4_096
    assert rare.draw_count * 8 == balanced.draw_count


def test_v0066_radius_at_probability_point_zero_one_needs_8192_draws(
    binding: seq.TargetLocalBernoulliRowBindingV1,
) -> None:
    profile = seq.v0067_default_sequential_profile_v1()
    result = seq.acquire_sequential_bernoulli_row_v1(
        binding,
        profile,
        (index % 100 == 0 for index in range(profile.max_draws)),
    )
    assert result.certified
    assert result.draw_count == 8_192
    assert result.success_count == 82
    assert result.draw_count * 16 == 131_072
    assert result.final_checkpoint is not None
    assert (
        result.final_checkpoint.interval_width
        <= 2 * Fraction(1, 140)
    )
    assert (
        result.checkpoints[-2].interval_width
        > 2 * Fraction(1, 140)
    )


def test_count_only_checkpoint_reuses_one_multinomial_transcript() -> None:
    profile = seq.v0067_default_sequential_profile_v1()
    # One authoritative ordinal transcript; three preregistered aggregate
    # events reuse its counts without serializing three boolean transcripts.
    ordinals = tuple(index % 100 for index in range(16_384))
    event_sets = (
        frozenset((0,)),
        frozenset(range(10)),
        frozenset(range(50)),
    )
    checkpoints = tuple(
        seq.build_anytime_bernoulli_checkpoint_v1(
            len(ordinals),
            sum(ordinal in event for ordinal in ordinals),
            profile,
        )
        for event in event_sets
    )
    assert tuple(item.success_count for item in checkpoints) == (
        164,
        1_640,
        8_200,
    )
    assert all(
        item.draw_count == len(ordinals) for item in checkpoints
    )
    assert all(
        type(item.lower_probability) is Fraction
        and type(item.upper_probability) is Fraction
        for item in checkpoints
    )


def test_count_only_point_zero_one_radius_beats_v0066_fixed_radius_at_16384() -> None:
    checkpoint = seq.build_anytime_bernoulli_checkpoint_v1(
        16_384,
        164,
        seq.v0067_default_sequential_profile_v1(),
    )
    adaptive_half_width = checkpoint.interval_width / 2
    assert adaptive_half_width < Fraction(1, 140)
    assert adaptive_half_width < Fraction(3, 4) * Fraction(1, 140)
    assert 0.0047 < float(adaptive_half_width) < 0.0049


def test_acquisition_is_content_addressed_and_exactly_replayable(
    binding: seq.TargetLocalBernoulliRowBindingV1,
) -> None:
    profile = _small_profile(half_width=Fraction(1, 16))
    draws = tuple(index % 100 == 0 for index in range(profile.max_draws))
    first = seq.acquire_sequential_bernoulli_row_v1(
        binding,
        profile,
        draws,
    )
    second = seq.acquire_sequential_bernoulli_row_v1(
        binding,
        profile,
        draws,
    )
    assert first == second
    assert first.acquisition_id == second.acquisition_id
    verification = seq.verify_sequential_bernoulli_acquisition_v1(first)
    assert verification.acquisition_id == first.acquisition_id
    assert verification.exact_transcript_replay_passed
    assert verification.exact_boundary_replay_passed
    assert verification.target_local_scope_passed
    assert verification.cap_and_stopping_rule_passed


def test_full_draw_transcript_and_native_counters_are_exposed(
    binding: seq.TargetLocalBernoulliRowBindingV1,
) -> None:
    profile = _small_profile(half_width=Fraction(1, 16))
    result = seq.acquire_sequential_bernoulli_row_v1(
        binding,
        profile,
        (index % 100 == 0 for index in range(profile.max_draws)),
    )
    document = result.to_document()
    assert bytes.fromhex(document["packed_draws_hex"]) == result.packed_draws
    assert document["packed_draws_sha256"] == hashlib.sha256(
        result.packed_draws
    ).hexdigest()
    assert result.counters.target_draw_calls == result.draw_count
    assert result.counters.source_poll_calls == result.draw_count
    assert result.counters.checkpoint_evaluations == len(result.checkpoints)
    assert result.counters.cap_checks == len(result.checkpoints)
    assert result.counters.transcript_bits_recorded == result.draw_count
    assert result.counters.source_observation_rows_imported == 0
    assert result.counters.offline_draws_used_for_interval == 0
    assert result.counters.cross_target_rows_imported == 0


def test_cap_exhaustion_is_a_noncertificate(
    binding: seq.TargetLocalBernoulliRowBindingV1,
) -> None:
    profile = _small_profile(
        half_width=Fraction(1, 128),
        checkpoints=(8, 16),
    )
    result = seq.acquire_sequential_bernoulli_row_v1(
        binding,
        profile,
        (index % 2 == 0 for index in range(profile.max_draws)),
    )
    assert result.outcome is seq.SequentialBernoulliOutcome.CAP_EXHAUSTED
    assert not result.certified
    assert result.draw_count == profile.max_draws
    assert result.final_checkpoint is not None
    assert (
        result.final_checkpoint.interval_width
        > 2 * profile.target_half_width
    )


def test_source_exhaustion_is_fail_closed_and_charged(
    binding: seq.TargetLocalBernoulliRowBindingV1,
) -> None:
    profile = _small_profile(checkpoints=(8, 16))
    result = seq.acquire_sequential_bernoulli_row_v1(
        binding,
        profile,
        (False, False, True, False, False),
    )
    assert result.outcome is seq.SequentialBernoulliOutcome.SOURCE_EXHAUSTED
    assert not result.certified
    assert result.draw_count == 5
    assert result.counters.target_draw_calls == 5
    assert result.counters.source_poll_calls == 6
    assert tuple(item.draw_count for item in result.checkpoints) == (5,)
    seq.verify_sequential_bernoulli_acquisition_v1(result)


def test_zero_draw_source_exhaustion_remains_a_replayable_noncertificate(
    binding: seq.TargetLocalBernoulliRowBindingV1,
) -> None:
    result = seq.acquire_sequential_bernoulli_row_v1(
        binding,
        _small_profile(checkpoints=(8, 16)),
        (),
    )
    assert result.outcome is seq.SequentialBernoulliOutcome.SOURCE_EXHAUSTED
    assert result.draw_count == 0
    assert result.checkpoints == ()
    assert result.counters.source_poll_calls == 1
    seq.verify_sequential_bernoulli_acquisition_v1(result)


def test_nonboolean_draw_is_rejected_not_coerced(
    binding: seq.TargetLocalBernoulliRowBindingV1,
) -> None:
    with pytest.raises(seq.SequentialBernoulliInvariantViolation):
        seq.acquire_sequential_bernoulli_row_v1(
            binding,
            _small_profile(checkpoints=(8, 16)),
            (False, False, 1, False),
        )


def test_transcript_checkpoint_and_counter_tampering_fail_replay(
    binding: seq.TargetLocalBernoulliRowBindingV1,
) -> None:
    result = seq.acquire_sequential_bernoulli_row_v1(
        binding,
        _small_profile(half_width=Fraction(1, 16)),
        (index % 100 == 0 for index in range(4_096)),
    )

    transcript_attack = copy.copy(result)
    changed = bytearray(result.packed_draws)
    changed[0] ^= 1
    object.__setattr__(transcript_attack, "packed_draws", bytes(changed))
    with pytest.raises(seq.SequentialBernoulliInvariantViolation):
        seq.verify_sequential_bernoulli_acquisition_v1(transcript_attack)

    checkpoint_attack = copy.copy(result)
    object.__setattr__(
        checkpoint_attack,
        "checkpoints",
        result.checkpoints[:-1],
    )
    with pytest.raises(seq.SequentialBernoulliInvariantViolation):
        seq.verify_sequential_bernoulli_acquisition_v1(checkpoint_attack)

    counter_attack = copy.copy(result)
    changed_counters = copy.copy(result.counters)
    object.__setattr__(
        changed_counters,
        "exact_likelihood_comparisons",
        result.counters.exact_likelihood_comparisons + 1,
    )
    object.__setattr__(counter_attack, "counters", changed_counters)
    with pytest.raises(seq.SequentialBernoulliInvariantViolation):
        seq.verify_sequential_bernoulli_acquisition_v1(counter_attack)


def test_binding_forbids_source_or_cross_target_interval_rows() -> None:
    with pytest.raises(seq.SequentialBernoulliInvariantViolation):
        seq.TargetLocalBernoulliRowBindingV1(
            structural_id=_id("structure"),
            target_context_id=_id("target-context"),
            target_row_id=_id("target-row"),
            draw_source_id=_id("target-simulator"),
            outcome_semantics_id=_id("failure-event"),
            row_key="attack",
            source_observation_rows_used=1,
        )
    with pytest.raises(seq.SequentialBernoulliInvariantViolation):
        seq.TargetLocalBernoulliRowBindingV1(
            structural_id=_id("structure"),
            target_context_id=_id("target-context"),
            target_row_id=_id("target-row"),
            draw_source_id=_id("target-simulator"),
            outcome_semantics_id=_id("failure-event"),
            row_key="attack",
            cross_target_rows_used=1,
        )


def test_outer_grid_resolution_and_exact_fraction_contract() -> None:
    with pytest.raises(seq.SequentialBernoulliInvariantViolation):
        seq.SequentialBernoulliProfileV1(
            confidence_alpha=Fraction(1, 1_000),
            target_half_width=Fraction(1, 10_000),
            checkpoints=(64, 128),
            boundary_grid_bits=8,
        )
    with pytest.raises(seq.SequentialBernoulliInvariantViolation):
        seq.SequentialBernoulliProfileV1(
            confidence_alpha=0.001,  # type: ignore[arg-type]
            target_half_width=Fraction(1, 32),
            checkpoints=(64, 128),
            boundary_grid_bits=16,
        )
