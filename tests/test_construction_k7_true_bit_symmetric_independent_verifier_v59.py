import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_true_bit_symmetric_campaign_v59 as producer
from acfqp import construction_k7_true_bit_symmetric_independent_verifier_v59 as verifier


def test_v59_independent_verifier_replays_frozen_bytes_without_producer_import():
    campaign = producer.run_true_bit_symmetric_campaign_v59()
    result = verifier.verify_true_bit_symmetric_campaign_bytes_v59(
        campaign.canonical_bytes
    )
    assert result["campaign_id"] == campaign.campaign_id
    assert result["producer_or_campaign_core_imported"] is False
    assert result["raw_transition_semantic_reexecution_present"] is False
    assert result["outcome"] == (
        "PRODUCER_FREE_IDENTITY_AND_INTERNAL_ACCOUNTING_VERIFIED"
    )
    raw = verifier.canonical_json_bytes(result)
    assert result["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_VERIFICATION_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_VERIFICATION_SHA256


def test_v59_verifier_source_has_no_producer_or_core_import():
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("campaign_v59" in name for name in imported)
    assert not any("campaign_core_v59" in name for name in imported)
