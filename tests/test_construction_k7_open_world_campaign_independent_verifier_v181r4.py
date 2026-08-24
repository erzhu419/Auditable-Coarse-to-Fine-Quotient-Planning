from pathlib import Path

import pytest

from acfqp import construction_k7_open_world_campaign_independent_verifier_v181r4 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"


def _campaign() -> bytes:
    return (BASE / "v181r4_open_world_campaign.json").read_bytes()


def _checkpoints() -> tuple[bytes, ...]:
    return tuple(
        path.read_bytes()
        for path in sorted((BASE / "v181r4_open_world_progress").glob("checkpoint-*.json"))
    )


def test_retained_rank_decreasing_result_is_independently_replayed() -> None:
    document = verifier.verify_open_world_campaign_bundle_v181r4(
        _campaign(),
        _checkpoints(),
    )
    assert document["episode_denominator"] == 72
    assert document["terminal_episode_count"] == 72
    assert document["prior_labels_avoided"] == -32
    assert document["covered_recompilation_skip_count"] == 19
    assert document["mismatch_only_recompilation_independently_verified"] is True
    assert document["strict_rank_decrease_fields_independently_verified"] is True
    assert document["registered_gate_projection_independently_verified"] is True
    assert document["bounded_rank_decreasing_campaign_succeeded"] is True
    assert document["negative_prior_transfer_independently_observed"] is True
    assert document["broad_open_world_success_claimed"] is False


def test_missing_checkpoint_or_resigned_gate_is_rejected() -> None:
    with pytest.raises(ValueError):
        verifier.verify_open_world_campaign_bundle_v181r4(
            _campaign(),
            _checkpoints()[:-1],
        )
    document = loads_canonical_json(_campaign())
    document["registered_gate_passed"] = False
    with pytest.raises(ValueError):
        verifier.verify_open_world_campaign_bundle_v181r4(
            canonical_json_bytes(document),
            _checkpoints(),
        )


def test_rank_certificate_claim_mutation_is_rejected() -> None:
    document = loads_canonical_json(_campaign())
    certificate = document["distribution_results"][0]["episodes"][
        "REUSED_SUBPROGRAM_PRIOR"
    ][0]["steps"][0]["certificate"]
    certificate["strict_rank_decrease_proved"] = False
    with pytest.raises(ValueError):
        verifier.verify_open_world_campaign_bundle_v181r4(
            canonical_json_bytes(document),
            _checkpoints(),
        )


def test_checkpoint_stage_or_official_claim_mutation_is_rejected() -> None:
    checkpoints = list(_checkpoints())
    document = loads_canonical_json(checkpoints[0])
    document["official_execution_allowed"] = True
    checkpoints[0] = canonical_json_bytes(document)
    with pytest.raises(ValueError):
        verifier.verify_open_world_campaign_bundle_v181r4(
            _campaign(),
            checkpoints,
        )


def test_retained_verification_bytes_are_exact() -> None:
    value = verifier.freeze_open_world_campaign_verification_v181r4(
        _campaign(),
        _checkpoints(),
    )
    path = BASE / "v181r4_open_world_campaign_verification.json"
    assert path.read_bytes() == value.canonical_bytes
