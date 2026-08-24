from pathlib import Path

import pytest

from acfqp import construction_k7_open_world_campaign_failure_verifier_v181r2 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


_ROOT = Path(__file__).resolve().parents[1]
_BASE = _ROOT / ".tmp" / "exact-freeze"


def _failure_bytes() -> bytes:
    return (_BASE / "v181r2_open_world_campaign_failure.json").read_bytes()


def _checkpoint_bytes() -> tuple[bytes, ...]:
    directory = _BASE / "v181r2_open_world_progress"
    return tuple(path.read_bytes() for path in sorted(directory.glob("checkpoint-*.json")))


def test_exact_interrupted_campaign_chain_is_independently_replayed() -> None:
    document = verifier.verify_open_world_campaign_failure_bundle_v181r2(
        _failure_bytes(),
        _checkpoint_bytes(),
    )
    assert document["checkpoint_count"] == 14
    assert document["typed_operator_interruption_independently_verified"] is True
    assert document["resource_cap_violation_observed"] is False
    assert document["scientific_campaign_success_independently_verified"] is False
    assert document["scientific_campaign_failure_independently_verified"] is False
    assert document["performance_successor_requires_fresh_identity"] is True


def test_missing_reordered_or_resigned_progress_is_rejected() -> None:
    checkpoints = list(_checkpoint_bytes())
    with pytest.raises(ValueError):
        verifier.verify_open_world_campaign_failure_bundle_v181r2(
            _failure_bytes(), checkpoints[:-1]
        )
    checkpoints[0], checkpoints[1] = checkpoints[1], checkpoints[0]
    with pytest.raises(ValueError):
        verifier.verify_open_world_campaign_failure_bundle_v181r2(
            _failure_bytes(), checkpoints
        )
    checkpoints = list(_checkpoint_bytes())
    document = loads_canonical_json(checkpoints[-1])
    document["official_execution_allowed"] = True
    checkpoints[-1] = canonical_json_bytes(document)
    with pytest.raises(ValueError):
        verifier.verify_open_world_campaign_failure_bundle_v181r2(
            _failure_bytes(), checkpoints
        )


def test_resigned_failure_success_claim_is_rejected() -> None:
    document = loads_canonical_json(_failure_bytes())
    document["success_claimed"] = True
    with pytest.raises(ValueError):
        verifier.verify_open_world_campaign_failure_bundle_v181r2(
            canonical_json_bytes(document), _checkpoint_bytes()
        )


def test_retained_failure_verification_bytes_are_exact() -> None:
    value = verifier.freeze_open_world_campaign_failure_verification_v181r2(
        _failure_bytes(),
        _checkpoint_bytes(),
    )
    path = _BASE / "v181r2_open_world_campaign_failure_verification.json"
    assert path.read_bytes() == value.canonical_bytes
