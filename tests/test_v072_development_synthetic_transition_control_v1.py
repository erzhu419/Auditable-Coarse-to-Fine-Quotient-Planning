from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib

import pytest

import acfqp.heldout_graph_transition_observer_v2 as registered
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg
import acfqp.v072_development_synthetic_transition_control_v1 as control


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _stream(
    arm: str,
    lane: control.DevelopmentSyntheticLaneV1 = (
        control.DevelopmentSyntheticLaneV1.DISCOVERY
    ),
    epoch: int = 0,
    lineage: str | None = None,
) -> tuple[
    control.DevelopmentSyntheticAnchorV1,
    control.DevelopmentSyntheticContextV1,
    control.DevelopmentSyntheticCatalogueV1,
    tuple[int, int, int],
    control.DevelopmentSyntheticTransitionStreamV1,
]:
    anchor = control.DevelopmentSyntheticAnchorV1()
    context, _, catalogue = control.development_synthetic_root_catalogue_v1()
    action = catalogue.actions[0]
    stream = control.open_development_synthetic_stream_v1(
        anchor,
        context,
        catalogue,
        action,
        arm,
        lane,
        epoch,
        _id("shared-synthetic-support-lineage")
        if lineage is None
        else lineage,
    )
    return anchor, context, catalogue, action, stream


def test_synthetic_control_is_domain_and_role_separated_from_registered_target(
) -> None:
    context, _, _ = control.development_synthetic_root_catalogue_v1()
    document = context.to_document()
    assert document["role"] == (
        "DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE"
    )
    assert document["registered_target_context"] is False
    assert document["hidden_law_serialized"] is False
    assert "rank_probabilities" not in repr(document)
    assert set(control.DOMAIN_TAGS.values()).isdisjoint(
        registered.DOMAIN_TAGS.values()
    )
    assert context.context_id not in {
        item.context_id
        for item in prereg.registered_heldout_public_contexts_v2()
    }


def test_synthetic_draws_are_exact_raw_committed_and_replayable() -> None:
    anchor, context, catalogue, action, stream = _stream(
        "SOURCE_CONSENSUS_PRIOR"
    )
    observations = tuple(stream.draw() for _ in range(8))
    assert all(
        item.role
        == "DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE"
        and item.to_document()["registered_target_evidence"] is False
        and type(item.reward) is Fraction
        and item.raw_commitment.commitment_id
        for item in observations
    )
    replay = control.verify_development_synthetic_observation_v1(
        anchor,
        context,
        catalogue,
        action,
        "SOURCE_CONSENSUS_PRIOR",
        control.DevelopmentSyntheticLaneV1.DISCOVERY,
        0,
        _id("shared-synthetic-support-lineage"),
        observations[-1],
    )
    assert replay.replayed_draws == 8

    tampered = replace(
        observations[-1],
        reward=observations[-1].reward + Fraction(1, 16),
    )
    with pytest.raises(
        control.SyntheticTransitionControlInvariantViolation,
        match="differs from raw replay",
    ):
        control.verify_development_synthetic_observation_v1(
            anchor,
            context,
            catalogue,
            action,
            "SOURCE_CONSENSUS_PRIOR",
            control.DevelopmentSyntheticLaneV1.DISCOVERY,
            0,
            _id("shared-synthetic-support-lineage"),
            tampered,
        )


def test_synthetic_common_random_numbers_pair_arms_but_not_evidence_ids(
) -> None:
    _, _, _, _, source = _stream("SOURCE_CONSENSUS_PRIOR")
    _, _, _, _, direct = _stream("MATCHED_DIRECT_GROUND")
    source_observations = tuple(source.draw() for _ in range(12))
    direct_observations = tuple(direct.draw() for _ in range(12))
    assert (
        source.raw_word_pairing_group_id
        == direct.raw_word_pairing_group_id
    )
    assert source.stream_id != direct.stream_id
    assert tuple(
        (
            item.next_state,
            item.reward,
            item.failure,
            item.terminal,
        )
        for item in source_observations
    ) == tuple(
        (
            item.next_state,
            item.reward,
            item.failure,
            item.terminal,
        )
        for item in direct_observations
    )
    assert all(
        source_item.observation_id != direct_item.observation_id
        and source_item.raw_commitment.commitment_id
        != direct_item.raw_commitment.commitment_id
        for source_item, direct_item in zip(
            source_observations,
            direct_observations,
            strict=True,
        )
    )


def test_synthetic_lane_epoch_and_support_lineage_separate_raw_groups() -> None:
    _, _, _, _, discovery = _stream("SOURCE_CONSENSUS_PRIOR")
    _, _, _, _, initial_validation = _stream(
        "SOURCE_CONSENSUS_PRIOR",
        control.DevelopmentSyntheticLaneV1.VALIDATION,
        1,
    )
    _, _, _, _, promoted_validation = _stream(
        "SOURCE_CONSENSUS_PRIOR",
        control.DevelopmentSyntheticLaneV1.VALIDATION,
        2,
        _id("changed-promoted-synthetic-lineage"),
    )
    assert len(
        {
            discovery.raw_word_pairing_group_id,
            initial_validation.raw_word_pairing_group_id,
            promoted_validation.raw_word_pairing_group_id,
        }
    ) == 3


def test_synthetic_exact_atoms_are_fractional_and_evaluation_only() -> None:
    anchor = control.DevelopmentSyntheticAnchorV1()
    context, _, catalogue = (
        control.development_synthetic_root_catalogue_v1()
    )
    atoms = control.development_evaluation_only_exact_atoms_v1(
        anchor,
        context,
        catalogue,
        catalogue.actions[0],
    )
    assert len(atoms) == 4
    assert sum((atom.probability for atom in atoms), Fraction(0)) == 1
    assert all(
        type(atom.probability) is Fraction
        and atom.execution_lane == "DEVELOPMENT_EVALUATION_ONLY"
        and atom.role
        == "DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE"
        for atom in atoms
    )
