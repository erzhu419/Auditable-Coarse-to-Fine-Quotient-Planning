import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_query_local_campaign_v60 as producer
from acfqp import construction_k7_query_local_independent_verifier_v60 as verifier


@pytest.fixture(scope="module")
def verified():
    campaign = producer.run_query_local_campaign_v60()
    result = verifier.verify_query_local_campaign_bytes_v60(campaign.canonical_bytes)
    return campaign, result


def test_v60_independent_verifier_replays_raw_partial_and_query_local_evidence(verified):
    campaign, result = verified
    assert result["campaign_id"] == campaign.campaign_id
    assert result["raw_transition_row_count_replayed"] > 0
    assert result["partial_factor_assignment_count_replayed"] > 0
    assert result["query_local_raw_transition_row_count_replayed"] > 0
    assert result["raw_prefix_semantics_independently_replayed"] is True
    assert result["partial_factor_dynamics_semantics_independently_replayed"] is True
    assert result["certificate_before_query_and_local_raw_evidence_independently_replayed"] is True
    assert result["complete_program_semantic_reexecution_present"] is False
    raw = verifier.canonical_json_bytes(result)
    if verifier.VERIFICATION_ID != "0" * 64:
        assert result["verification_id"] == verifier.VERIFICATION_ID
        assert len(raw) == verifier.EXPECTED_VERIFICATION_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_VERIFICATION_SHA256


def test_v60_independent_verifier_rejects_campaign_byte_mutation(verified):
    campaign, _result = verified
    forged = bytearray(campaign.canonical_bytes)
    forged[len(forged) // 2] ^= 1
    with pytest.raises(verifier.ConstructionK7QueryLocalIndependentVerifierV60Error):
        verifier.verify_query_local_campaign_bytes_v60(bytes(forged))


def test_v60_independent_verifier_source_has_no_producer_core_or_model_import():
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("campaign_v60" in name for name in imported)
    assert not any("campaign_core_v60" in name for name in imported)
    assert not any("planner" in name or "world_model" in name or "synthesizer" in name for name in imported)
