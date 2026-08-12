from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp import construction_k7_standard_2048_spawn_observation_v1 as subject
from acfqp.phase3e_ids import canonical_json_bytes


def test_raw_archive_replays_and_interval_is_exact() -> None:
    evidence = subject.build_standard_2048_spawn_observation_evidence_v1()
    subject.verify_standard_2048_spawn_observation_evidence_v1(evidence)
    document = evidence.to_document()
    archive = document["archive"]
    interval = document["interval"]
    packed = bytes.fromhex(archive["packed_rank_two_bits_hex"])
    rows = subject.unpack_observation_bits_v1(packed)
    assert len(rows) == 4096
    assert sum(rows) == archive["rank_two_count"] == 424
    assert archive["rank_one_count"] == 3672
    assert interval["empirical_rank_two_probability"] == Fraction(53, 512)
    assert interval["rank_two_probability_lower"] == Fraction(37, 512)
    assert interval["rank_two_probability_upper"] == Fraction(69, 512)
    assert interval["rank_two_probability_lower"] <= Fraction(1, 10)
    assert Fraction(1, 10) <= interval["rank_two_probability_upper"]


def test_statistical_claim_is_conditional_and_not_an_iid_certificate() -> None:
    document = subject.build_standard_2048_spawn_observation_evidence_v1().to_document()
    assert document["archive"]["deterministic_fixture_replay_not_iid_evidence"] is True
    assert document["interval"]["confidence_is_conditional_on_idealized_iid_source"] is True
    assert document["interval"]["deterministic_replay_does_not_establish_iid"] is True
    assert document["interval"]["conditional_confidence_lower"] == Fraction(999, 1000)


def test_archive_tamper_is_rejected() -> None:
    evidence = subject.build_standard_2048_spawn_observation_evidence_v1()
    original = evidence.canonical_bytes
    attacked = evidence.to_document()
    attacked["archive"]["rank_two_count"] += 1
    object.__setattr__(evidence, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(subject.ConstructionK7Standard2048SpawnObservationV1Error):
        subject.verify_standard_2048_spawn_observation_evidence_v1(evidence)
    object.__setattr__(evidence, "canonical_bytes", original)
    subject.verify_standard_2048_spawn_observation_evidence_v1(evidence)
