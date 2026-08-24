from pathlib import Path

import pytest

from acfqp import construction_k7_open_world_campaign_failure_verifier_v181r1 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


def _failure_bytes() -> bytes:
    return (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181r1_open_world_campaign_failure.json"
    ).read_bytes()


def test_failure_is_independently_replayed_as_non_success() -> None:
    document = verifier.verify_open_world_campaign_failure_bytes_v181r1(
        _failure_bytes()
    )
    assert document["typed_resource_failure_independently_verified"] is True
    assert document["campaign_success_independently_verified"] is False
    assert document["sample_efficiency_claimed"] is False
    assert document["durable_manifest_and_arm_progress_index_present"] is False


def test_resigned_success_or_message_mutation_is_rejected() -> None:
    for key, value in (
        ("success_claimed", True),
        ("failure_message", "forged"),
    ):
        document = loads_canonical_json(_failure_bytes())
        document[key] = value
        with pytest.raises(ValueError):
            verifier.verify_open_world_campaign_failure_bytes_v181r1(
                canonical_json_bytes(document)
            )


def test_retained_failure_verification_bytes_are_exact() -> None:
    value = verifier.freeze_open_world_campaign_failure_verification_v181r1(
        _failure_bytes()
    )
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181r1_open_world_campaign_failure_verification.json"
    )
    assert path.read_bytes() == value.canonical_bytes
