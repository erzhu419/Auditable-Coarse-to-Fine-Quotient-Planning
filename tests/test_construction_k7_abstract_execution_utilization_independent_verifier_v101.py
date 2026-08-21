import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_abstract_execution_utilization_independent_verifier_v101 as verifier
from acfqp.phase3e_ids import loads_canonical_json


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v101_abstract_execution_utilization_campaign.json"
)


def test_v101_producer_free_verifier_preserves_failure_and_majority_lower_bound():
    result = verifier.verify_abstract_execution_utilization_campaign_bytes_v101(
        CAMPAIGN_PATH.read_bytes()
    )
    evidence = result["verified_aggregate_evidence"]
    assert result["v101_registered_gate_passed"] is False
    assert evidence["failed_occurrence"]["seed"] == 1_011_102
    assert evidence["failed_occurrence"][
        "persistent_sequence_disagreement_abstention_count"
    ] == 0
    assert evidence["abstract_execution_match_fraction_numerator"] == 50
    assert evidence["abstract_execution_match_fraction_denominator"] == 74
    assert all(
        2 * row["later_episode_independently_replayed_match_count"]
        > row["total_sequence_execution_step_count"]
        for row in evidence["producer_free_later_episode_match_lower_bound_rows"]
    )
    assert result["complete_world_model_synthesized"] is False


def test_v101_verification_artifact_is_content_addressed():
    raw = verifier.freeze_abstract_execution_utilization_verification_v101(
        CAMPAIGN_PATH.read_bytes()
    )
    document = loads_canonical_json(raw)
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256


def test_v101_verifier_rejects_byte_changes_and_has_no_producer_import():
    raw = bytearray(CAMPAIGN_PATH.read_bytes())
    raw[-100] ^= 1
    with pytest.raises(Exception):
        verifier.verify_abstract_execution_utilization_campaign_bytes_v101(
            bytes(raw)
        )
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("campaign_v101" in name for name in imported)
    assert not any("campaign_core_v101" in name for name in imported)
    assert not any("planner_v99" in name for name in imported)
    assert not any("sequence_v99" in name for name in imported)
