from pathlib import Path

import pytest

from acfqp import construction_k7_open_world_campaign_independent_verifier_v181r3 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"


def _campaign() -> bytes:
    return (BASE / "v181r3_open_world_campaign.json").read_bytes()


def _checkpoints() -> tuple[bytes, ...]:
    return tuple(
        path.read_bytes()
        for path in sorted((BASE / "v181r3_open_world_progress").glob("checkpoint-*.json"))
    )


def test_retained_mixed_result_is_independently_replayed() -> None:
    document = verifier.verify_open_world_campaign_bundle_v181r3(
        _campaign(),
        _checkpoints(),
    )
    assert document["episode_denominator"] == 72
    assert document["terminal_episode_count"] == 32
    assert document["prior_labels_avoided"] == 8
    assert document["covered_recompilation_skip_count"] == 39
    assert document["mismatch_only_recompilation_independently_verified"] is True
    assert document["registered_gate_passed_independently_verified"] is False
    assert document["scientific_success_claimed"] is False


def test_missing_checkpoint_or_resigned_gate_is_rejected() -> None:
    with pytest.raises(ValueError):
        verifier.verify_open_world_campaign_bundle_v181r3(
            _campaign(),
            _checkpoints()[:-1],
        )
    document = loads_canonical_json(_campaign())
    document["registered_gate_passed"] = True
    with pytest.raises(ValueError):
        verifier.verify_open_world_campaign_bundle_v181r3(
            canonical_json_bytes(document),
            _checkpoints(),
        )


def test_checkpoint_stage_or_official_claim_mutation_is_rejected() -> None:
    checkpoints = list(_checkpoints())
    document = loads_canonical_json(checkpoints[0])
    document["official_execution_allowed"] = True
    checkpoints[0] = canonical_json_bytes(document)
    with pytest.raises(ValueError):
        verifier.verify_open_world_campaign_bundle_v181r3(
            _campaign(),
            checkpoints,
        )


def test_retained_verification_bytes_are_exact() -> None:
    value = verifier.freeze_open_world_campaign_verification_v181r3(
        _campaign(),
        _checkpoints(),
    )
    path = BASE / "v181r3_open_world_campaign_verification.json"
    assert path.read_bytes() == value.canonical_bytes
