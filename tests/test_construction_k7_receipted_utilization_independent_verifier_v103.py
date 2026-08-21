import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_receipted_utilization_independent_verifier_v103 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_PATH = Path(".tmp/exact-freeze/v103_receipted_utilization_campaign.json")


def test_v103_verifier_is_producer_free_and_replays_every_execution_receipt():
    source = Path(verifier.__file__).read_text()
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any("campaign_v103" in name or "generic_abstract_execution_receipt_v103" in name for name in imported)
    raw = CAMPAIGN_PATH.read_bytes()
    result = verifier.verify_receipted_utilization_campaign_bytes_v103(raw)
    assert result["verification_status"].endswith("GATE_FAILED")
    assert result["producer_free_per_action_receipt_replay"] is True
    assert result["verified_accounting"]["meta_receipted_abstract_execution_match_count"] == 13
    assert result["verified_accounting"]["meta_execution_step_count"] == 71
    assert all(row["receipt_strict_majority"] is False for row in result["verified_occurrences"])
    assert result["sample_tax_reduction_still_observed"] is True
    assert result["complete_world_model_synthesized"] is False


def test_v103_verifier_rejects_a_fully_rehashed_receipt_semantic_change():
    document = loads_canonical_json(CAMPAIGN_PATH.read_bytes())
    receipt = document["target_occurrences"][0]["meta_prior_persistent_receipted_sequence"]["all_abstract_execution_receipts"][0]
    receipt["chosen_action_matches_admitted_abstract_proposal"] = False
    payload = {key: value for key, value in receipt.items() if key != "execution_receipt_id"}
    receipt["execution_receipt_id"] = verifier._hash(verifier._RECEIPT_DOMAIN, payload)
    with pytest.raises(verifier.ConstructionK7ReceiptedUtilizationIndependentVerifierV103Error):
        verifier.verify_receipted_utilization_campaign_bytes_v103(canonical_json_bytes(document))


def test_v103_frozen_verification_identity():
    raw = verifier.freeze_receipted_utilization_verification_v103(CAMPAIGN_PATH.read_bytes())
    document = loads_canonical_json(raw)
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
