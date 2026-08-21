import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_sequence_wide_agreement_shielded_independent_verifier_v100 as verifier
from acfqp.phase3e_ids import loads_canonical_json


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v100_sequence_wide_agreement_shielded_campaign.json"
)


def test_v100_producer_free_verifier_rederives_success_and_sample_tax():
    result = verifier.verify_sequence_wide_agreement_shielded_campaign_bytes_v100(
        CAMPAIGN_PATH.read_bytes()
    )
    evidence = result["verified_aggregate_evidence"]
    assert result["registered_v100_gate_passed"] is True
    assert evidence["meta_activation"] == 124
    assert evidence["no_prior_activation"] == 152
    assert evidence["activation_label_reduction"] == 28
    assert evidence["meta_labels"] == evidence["no_prior_labels"] == 270
    assert evidence["direct_labels"] == 549
    assert len(evidence["coverage_rows"]) == 4
    assert all(
        row["first_accept"] + row["later_accept"] > 0
        and row["first_disagreement"] + row["later_disagreement"] > 0
        for row in evidence["coverage_rows"]
    )
    assert result["complete_world_model_synthesized"] is False


def test_v100_verification_artifact_is_content_addressed():
    raw = verifier.freeze_sequence_wide_agreement_shielded_verification_v100(
        CAMPAIGN_PATH.read_bytes()
    )
    document = loads_canonical_json(raw)
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256


def test_v100_verifier_rejects_byte_changes_and_has_no_producer_import():
    raw = bytearray(CAMPAIGN_PATH.read_bytes())
    raw[-100] ^= 1
    with pytest.raises(Exception):
        verifier.verify_sequence_wide_agreement_shielded_campaign_bytes_v100(
            bytes(raw)
        )
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("campaign_v100" in name for name in imported)
    assert not any("campaign_core_v100" in name for name in imported)
    assert not any("planner_v99" in name for name in imported)
    assert not any("sequence_v99" in name for name in imported)
