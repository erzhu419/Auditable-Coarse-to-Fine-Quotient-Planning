import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_agreement_shielded_independent_verifier_v99 as verifier
from acfqp.phase3e_ids import loads_canonical_json


CAMPAIGN_PATH = Path(".tmp/exact-freeze/v99_agreement_shielded_campaign.json")


def test_v99_producer_free_verifier_preserves_the_registered_failure():
    result = verifier.verify_agreement_shielded_campaign_bytes_v99(
        CAMPAIGN_PATH.read_bytes()
    )
    assert result["verification_status"] == (
        "REGISTERED_AGREEMENT_SHIELDED_PATH_COVERAGE_FAILURE_VERIFIED"
    )
    evidence = result["verified_aggregate_evidence"]
    assert evidence["activation_label_reduction"] == 24
    assert evidence["negative_transfer_label_delta"] == 0
    assert evidence["failed_occurrence"]["seed"] == 1_005_101
    assert evidence["failed_occurrence"]["first_episode_agreement_accept_count"] == 0
    assert evidence["failed_occurrence"]["later_agreement_accept_count"] == 2
    assert result["failure_is_preregistered_first_episode_path_coverage_only"] is True
    assert result["registered_v99_gate_passed"] is False
    assert result["complete_world_model_synthesized"] is False


def test_v99_verification_artifact_is_content_addressed():
    raw = verifier.freeze_agreement_shielded_verification_v99(
        CAMPAIGN_PATH.read_bytes()
    )
    document = loads_canonical_json(raw)
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256


def test_v99_verifier_rejects_byte_changes_and_has_no_producer_import():
    raw = bytearray(CAMPAIGN_PATH.read_bytes())
    raw[-100] ^= 1
    with pytest.raises(Exception):
        verifier.verify_agreement_shielded_campaign_bytes_v99(bytes(raw))
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("campaign_v99" in name for name in imported)
    assert not any("planner_v99" in name for name in imported)
    assert not any("sequence_v99" in name for name in imported)
