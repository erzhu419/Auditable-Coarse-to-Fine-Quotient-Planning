import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_persistent_overlay_campaign_v61 as producer
from acfqp import construction_k7_persistent_overlay_independent_verifier_v61 as verifier


@pytest.fixture(scope="module")
def verified():
    campaign = producer.run_persistent_overlay_campaign_v61()
    return campaign, verifier.verify_persistent_overlay_campaign_bytes_v61(
        campaign.canonical_bytes
    )


def test_v61_independent_verifier_replays_persistent_and_cold_evidence(verified):
    campaign, result = verified
    assert result["campaign_id"] == campaign.campaign_id
    assert result["raw_transition_row_count_replayed"] > 0
    assert result["persistent_overlay_raw_transition_row_count_replayed"] > 0
    assert result["cold_restart_local_labels"] > result["persistent_overlay_local_labels"]
    assert result["raw_prefix_partial_factor_and_overlay_semantics_independently_replayed"] is True
    assert result["certificate_before_query_order_independently_replayed"] is True
    assert result["producer_campaign_core_or_planner_imported"] is False
    raw = verifier.canonical_json_bytes(result)
    if verifier.VERIFICATION_ID != "0" * 64:
        assert result["verification_id"] == verifier.VERIFICATION_ID
        assert len(raw) == verifier.EXPECTED_VERIFICATION_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_VERIFICATION_SHA256


def test_v61_independent_verifier_rejects_mutated_campaign_bytes(verified):
    campaign, _ = verified
    forged = bytearray(campaign.canonical_bytes)
    forged[len(forged) // 3] ^= 1
    with pytest.raises(verifier.ConstructionK7PersistentOverlayIndependentVerifierV61Error):
        verifier.verify_persistent_overlay_campaign_bytes_v61(bytes(forged))


def test_v61_independent_verifier_import_surface_is_producer_free():
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    modules = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("campaign_v61" in module for module in modules)
    assert not any("campaign_core_v61" in module for module in modules)
    assert not any("planner" in module or "synthesizer" in module for module in modules)
