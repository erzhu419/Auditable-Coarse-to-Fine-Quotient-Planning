from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp import construction_k7_standard_2048_spawn_support_observation_v2 as subject
from acfqp.phase3e_ids import canonical_json_bytes


@pytest.fixture(scope="module")
def evidence():
    return subject.build_standard_2048_spawn_support_evidence_v2()


def test_source_and_heldout_raw_archives_are_identity_separated(evidence) -> None:
    document = evidence.to_document()
    source = document["source_archive"]
    validation = document["validation_archive"]
    assert source["archive_role"] == "SOURCE_CONSTRUCTION"
    assert validation["archive_role"] == "HELDOUT_VALIDATION"
    assert source["stream_seed"] != validation["stream_seed"]
    assert source["total_record_count"] == 16 * 8192
    assert validation["total_record_count"] == 16 * 1024
    assert source["invalid_support_observation_count"] == 0
    assert validation["invalid_support_observation_count"] == 0
    source_records = subject.unpack_records_v2(
        bytes.fromhex(source["packed_records_hex"])
    )
    validation_records = subject.unpack_records_v2(
        bytes.fromhex(validation["packed_records_hex"])
    )
    assert source_records == subject.source_records_v2()
    assert validation_records == subject.validation_records_v2()


def test_support_rule_is_selected_from_source_then_checked_heldout(evidence) -> None:
    proposal = evidence.to_document()["proposal"]
    selected = [
        row["candidate"]
        for row in proposal["candidate_evaluations"]
        if row["selected_from_source"]
    ]
    assert selected == ["ALL_SORTED_EMPTY_ORDINALS"]
    assert proposal["selected_uniquely_from_source_raw_observations"] is True
    assert proposal["heldout_validation_not_used_for_selection"] is True
    assert proposal["heldout_support_validation_passed"] is True
    assert proposal["fixed_human_meta_grammar"] is True
    assert proposal["open_ended_support_invention_claimed"] is False


def test_position_rank_and_unknown_mass_intervals_are_replayable(evidence) -> None:
    interval = evidence.to_document()["interval"]
    assert interval["rank_two_source_count"] == 13256
    assert interval["rank_two_probability_lower"] == Fraction(1529, 16384)
    assert interval["rank_two_probability_upper"] == Fraction(1785, 16384)
    assert interval["unknown_support_source_count"] == 0
    assert interval["unknown_support_probability_upper"] == Fraction(1, 128)
    assert interval["heldout_position_intervals_passed"] is True
    assert interval["rank_two_heldout_inside_source_interval"] is True
    assert all(
        category["heldout_inside_source_interval"] is True
        for row in interval["position_intervals"]
        for category in row["categories"]
    )
    assert interval["conditional_confidence_lower"] == Fraction(999, 1000)
    assert interval["confidence_is_conditional_on_registered_iid_shared_law"] is True
    assert interval["deterministic_replay_does_not_establish_iid"] is True


def test_support_evidence_tamper_is_rejected(evidence) -> None:
    original = evidence.canonical_bytes
    attacked = evidence.to_document()
    attacked["proposal"]["heldout_validation_not_used_for_selection"] = False
    object.__setattr__(evidence, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048SpawnSupportObservationV2Error
    ):
        subject.verify_standard_2048_spawn_support_evidence_v2(evidence)
    object.__setattr__(evidence, "canonical_bytes", original)
    subject.verify_standard_2048_spawn_support_evidence_v2(evidence)
