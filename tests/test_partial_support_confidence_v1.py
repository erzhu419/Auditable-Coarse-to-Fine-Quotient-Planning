from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib

import pytest

import acfqp.partial_support_confidence_v1 as partial
from acfqp.sequential_bernoulli_acquisition_v1 import (
    SequentialBernoulliProfileV1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _outcome(label: str) -> partial.OpaqueObservedJointOutcomeV1:
    return partial.OpaqueObservedJointOutcomeV1(
        _id(f"outcome:{label}"),
        {"label": label, "opaque_payload": [len(label), label.upper()]},
    )


def _observations(
    stream_label: str,
    outcomes: tuple[partial.OpaqueObservedJointOutcomeV1, ...],
    *,
    sample_prefix: str | None = None,
) -> tuple[partial.SplitSupportObservationV1, ...]:
    stream_id = _id(f"stream:{stream_label}")
    prefix = stream_label if sample_prefix is None else sample_prefix
    return tuple(
        partial.SplitSupportObservationV1(
            stream_domain_id=stream_id,
            sample_id=_id(f"sample:{prefix}:{index}"),
            sequence_index=index,
            outcome=outcome,
        )
        for index, outcome in enumerate(outcomes)
    )


def _epoch(
    discovery_outcomes: tuple[partial.OpaqueObservedJointOutcomeV1, ...],
    *,
    validation_label: str = "validation-1",
) -> partial.FrozenSupportEpochV1:
    discovery = _observations("discovery-1", discovery_outcomes)
    return partial.freeze_support_epoch_v1(
        row_id=_id("row"),
        support_epoch_index=1,
        discovery_stream_domain_id=_id("stream:discovery-1"),
        validation_stream_domain_id=_id(f"stream:{validation_label}"),
        discovery_observations=discovery,
    )


def test_contract_profile_and_exact_alpha_allocation_are_frozen() -> None:
    safe = _outcome("safe")
    epoch = _epoch((safe,) * 4)
    profile = partial.v0068_partial_support_confidence_profile_v1()

    assert partial.CONTRACT_VERSION == "1.32.0"
    assert partial.PROFILE_KEY == "split_support_confidence_v0"
    assert profile.row_epoch_beta == Fraction(1, 64_000)
    assert epoch.support_outcome_ids == (safe.outcome_id,)
    assert epoch.event_count == 2
    assert epoch.per_event_alpha == Fraction(1, 128_000)
    assert (
        profile.sequential_profile(epoch.event_count).confidence_alpha
        * epoch.event_count
        == profile.row_epoch_beta
    )
    assert len(epoch.support_epoch_id) == 64


def test_rare_catastrophe_is_one_other_coordinate_and_a_novel_identity() -> None:
    safe = _outcome("safe")
    catastrophe = _outcome("rare-catastrophe")
    epoch = _epoch((safe,) * 8)
    validation_outcomes = (safe,) * 63 + (catastrophe,)
    authority = partial.build_partial_support_confidence_v1(
        epoch,
        _observations("validation-1", validation_outcomes),
    )

    assert tuple(
        (item.event_kind, item.success_count)
        for item in authority.event_intervals
    ) == (
        (partial.PartialSupportEventKind.DISCOVERED, 63),
        (partial.PartialSupportEventKind.OTHER, 1),
    )
    assert authority.novel_outcome_ids == (catastrophe.outcome_id,)
    assert authority.other_event_count == 1
    assert authority.joint_simplex.other_coordinate_count == 1
    assert (
        authority.joint_simplex.lower_probabilities[1]
        <= Fraction(1, 64)
        <= authority.joint_simplex.upper_probabilities[1]
    )
    assert sum(
        (item.success_count for item in authority.event_intervals),
        0,
    ) == 64
    verification = partial.verify_partial_support_confidence_v1(authority)
    assert verification.authority_id == authority.authority_id


def test_all_missed_discovery_atoms_collapse_into_exactly_one_other() -> None:
    safe = _outcome("safe")
    novel_left = _outcome("novel-left")
    novel_right = _outcome("novel-right")
    epoch = _epoch((safe,) * 3)
    outcomes = (safe,) * 60 + (novel_left,) * 2 + (novel_right,) * 2
    authority = partial.build_partial_support_confidence_v1(
        epoch,
        _observations("validation-1", outcomes),
    )

    assert authority.novel_outcome_ids == tuple(
        sorted((novel_left.outcome_id, novel_right.outcome_id))
    )
    others = tuple(
        item
        for item in authority.event_intervals
        if item.event_kind is partial.PartialSupportEventKind.OTHER
    )
    assert len(others) == 1
    assert others[0].success_count == 4
    assert len(authority.joint_simplex.event_interval_ids) == 2


def test_optional_stopping_uses_one_alpha_across_registered_checkpoints() -> None:
    safe = _outcome("safe")
    catastrophe = _outcome("rare")
    epoch = _epoch((safe,) * 4)
    first_outcomes = (safe,) * 63 + (catastrophe,)
    full_outcomes = first_outcomes + (safe,) * 63 + (catastrophe,)
    first = partial.build_partial_support_confidence_v1(
        epoch,
        _observations("validation-1", first_outcomes),
    )
    full = partial.build_partial_support_confidence_v1(
        epoch,
        _observations("validation-1", full_outcomes),
    )

    assert (
        first.sequential_profile.confidence_alpha
        == full.sequential_profile.confidence_alpha
        == epoch.per_event_alpha
    )
    assert first.sequential_profile.confidence_accounting == (
        "ONE_ALPHA_VILLE_TIME_UNIFORM_NO_CHECKPOINT_ALPHA_SPENDING"
    )
    assert first.event_intervals[-1].checkpoint.draw_count == 64
    assert full.event_intervals[-1].checkpoint.draw_count == 128
    assert (
        full.event_intervals[-1].checkpoint.interval_width
        < first.event_intervals[-1].checkpoint.interval_width
    )
    partial.verify_partial_support_confidence_v1(first)
    partial.verify_partial_support_confidence_v1(full)


def test_distinct_stream_domains_and_sample_no_reuse_are_mandatory() -> None:
    safe = _outcome("safe")
    discovery = _observations("discovery-1", (safe,) * 4)
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        partial.freeze_support_epoch_v1(
            row_id=_id("row"),
            support_epoch_index=1,
            discovery_stream_domain_id=_id("stream:discovery-1"),
            validation_stream_domain_id=_id("stream:discovery-1"),
            discovery_observations=discovery,
        )

    epoch = _epoch((safe,) * 4)
    reused = _observations(
        "validation-1",
        (safe,) * 64,
        sample_prefix="discovery-1",
    )
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        partial.build_partial_support_confidence_v1(epoch, reused)


def test_support_change_stale_epoch_and_alpha_transplant_are_rejected() -> None:
    safe = _outcome("safe")
    other = _outcome("other")
    epoch = _epoch((safe,) * 4)
    observations = _observations("validation-1", (safe,) * 64)
    authority = partial.build_partial_support_confidence_v1(epoch, observations)

    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        replace(epoch, support_outcomes=(safe, other))

    fresh_epoch = _epoch((safe,) * 4, validation_label="validation-fresh")
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        replace(authority, support_epoch=fresh_epoch)

    transplanted_profile = SequentialBernoulliProfileV1(
        confidence_alpha=Fraction(1, 99_999),
        target_half_width=authority.sequential_profile.target_half_width,
        checkpoints=authority.sequential_profile.checkpoints,
        boundary_grid_bits=authority.sequential_profile.boundary_grid_bits,
    )
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        replace(authority, sequential_profile=transplanted_profile)


def test_duplicate_other_and_infeasible_simplex_attacks_fail_closed() -> None:
    safe = _outcome("safe")
    epoch = _epoch((safe,) * 4)
    authority = partial.build_partial_support_confidence_v1(
        epoch,
        _observations("validation-1", (safe,) * 64),
    )
    duplicate_other = replace(
        authority.event_intervals[-1],
        event_ordinal=2,
    )
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        replace(
            authority,
            event_intervals=authority.event_intervals + (duplicate_other,),
        )
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        replace(
            authority.joint_simplex,
            lower_probabilities=(Fraction(3, 4), Fraction(3, 4)),
        )


def test_more_than_sixteen_discovered_atoms_is_rejected() -> None:
    outcomes = tuple(_outcome(f"atom-{index}") for index in range(17))
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        _epoch(outcomes)


def test_same_outcome_id_cannot_change_opaque_document() -> None:
    first = _outcome("stable")
    changed = partial.OpaqueObservedJointOutcomeV1(
        first.outcome_id,
        {"label": "silently-changed"},
    )
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        _epoch((first, changed))


def test_cached_opaque_document_never_exposes_mutable_internal_state() -> None:
    outcome = _outcome("immutable")
    original = outcome.to_document()
    attacked = outcome.to_document()
    attacked["document"]["opaque_payload"][0] = -1
    attacked["document"]["new_field"] = True
    assert outcome.to_document() == original
    assert outcome.document == original["document"]


def test_epoch_two_promotion_is_proposal_only_and_requires_fresh_draws() -> None:
    safe = _outcome("safe")
    novel = _outcome("novel")
    epoch_one = _epoch((safe,) * 4)
    old_validation = _observations(
        "validation-1",
        (safe,) * 63 + (novel,),
    )
    authority_one = partial.build_partial_support_confidence_v1(
        epoch_one,
        old_validation,
    )
    epoch_two = partial.promote_support_epoch_v1(
        authority_one,
        next_validation_stream_domain_id=_id("stream:validation-2"),
    )

    assert epoch_two.support_epoch_index == 2
    assert set(epoch_two.support_outcome_ids) == {
        safe.outcome_id,
        novel.outcome_id,
    }
    assert epoch_two.promotion_evidence.proposal_only is True
    assert epoch_two.promotion_evidence.probability_evidence_draw_count == 0
    assert set(old_validation[index].sample_id for index in range(64)).issubset(
        epoch_two.excluded_probability_sample_ids
    )
    assert set(epoch_one.excluded_probability_sample_ids).issubset(
        epoch_two.excluded_probability_sample_ids
    )
    assert epoch_two.per_event_alpha == Fraction(1, 192_000)
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        replace(
            epoch_two.promotion_evidence,
            excluded_probability_sample_ids=tuple(
                sorted(item.sample_id for item in old_validation)
            ),
        )

    relabeled_reuse = tuple(
        replace(
            item,
            stream_domain_id=_id("stream:validation-2"),
        )
        for item in old_validation
    )
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        partial.build_partial_support_confidence_v1(
            epoch_two,
            relabeled_reuse,
        )

    fresh = _observations(
        "validation-2",
        (safe,) * 62 + (novel,) * 2,
    )
    authority_two = partial.build_partial_support_confidence_v1(epoch_two, fresh)
    assert authority_two.novel_outcome_ids == ()
    assert authority_two.event_intervals[-1].success_count == 0
    partial.verify_partial_support_confidence_v1(authority_two)


def test_promotion_rejects_nonparent_or_nonnovel_proposals_and_old_domain() -> None:
    safe = _outcome("safe")
    novel = _outcome("novel")
    authority = partial.build_partial_support_confidence_v1(
        _epoch((safe,) * 4),
        _observations("validation-1", (safe,) * 63 + (novel,)),
    )
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        partial.promote_support_epoch_v1(
            authority,
            next_validation_stream_domain_id=_id("stream:validation-1"),
        )
    with pytest.raises(partial.PartialSupportConfidenceInvariantViolation):
        partial.promote_support_epoch_v1(
            authority,
            next_validation_stream_domain_id=_id("stream:validation-2"),
            novel_proposal_observations=(
                _observations("unrelated", (novel,))[0],
            ),
        )


def test_content_ids_are_deterministic_and_bind_epoch_and_transcript() -> None:
    safe = _outcome("safe")
    epoch = _epoch((safe,) * 4)
    observations = _observations("validation-1", (safe,) * 64)
    left = partial.build_partial_support_confidence_v1(epoch, observations)
    right = partial.build_partial_support_confidence_v1(epoch, observations)
    assert left.authority_id == right.authority_id
    assert left.to_document() == right.to_document()

    changed = list(observations)
    changed[-1] = replace(
        changed[-1],
        sample_id=_id("sample:changed-last"),
    )
    replacement = partial.build_partial_support_confidence_v1(
        epoch,
        tuple(changed),
    )
    assert replacement.validation_evidence.validation_evidence_id != (
        left.validation_evidence.validation_evidence_id
    )
    assert replacement.authority_id != left.authority_id
