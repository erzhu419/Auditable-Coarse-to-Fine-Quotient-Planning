import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_hierarchical_utilization_independent_verifier_v104 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_PATH = Path(".tmp/exact-freeze/v104_hierarchical_utilization_campaign.json")


def test_v104_verifier_is_producer_free_and_replays_hierarchical_receipts():
    source = Path(verifier.__file__).read_text()
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any("campaign_v104" in name or "generic_hierarchical_abstract_execution_receipt" in name for name in imported)
    result = verifier.verify_hierarchical_utilization_campaign_bytes_v104(
        CAMPAIGN_PATH.read_bytes()
    )
    assert result["registered_gate_independently_verified"] is True
    assert result["verified_accounting"]["meta_abstract_model_ordered_execution_count"] == 67
    assert result["verified_accounting"]["meta_full_post_dependency_world_model_match_count"] == 12
    assert result["verified_accounting"]["meta_compiled_partial_world_model_fallback_match_count"] == 55
    assert result["verified_accounting"]["meta_exact_certificate_policy_only_count"] == 0
    assert result["partial_world_model_primary_ordering_verified"] is True
    assert result["full_post_dependency_world_model_primary_ordering_verified"] is False
    assert result["complete_world_model_synthesized"] is False


def test_v104_verifier_rejects_rehashed_partial_fallback_as_full_match():
    document = loads_canonical_json(CAMPAIGN_PATH.read_bytes())
    receipt = document["target_occurrences"][0]["meta_prior_hierarchical_sequence"]["hierarchical_abstract_execution_receipts"][1]
    assert receipt["abstract_ordering_source"] == "COMPILED_PARTIAL_WORLD_MODEL_FALLBACK"
    receipt["abstract_ordering_source"] = "FULL_POST_DEPENDENCY_WORLD_MODEL"
    payload = {key: value for key, value in receipt.items() if key != "hierarchical_execution_receipt_id"}
    receipt["hierarchical_execution_receipt_id"] = hashlib.sha256(
        verifier._HIERARCHICAL_RECEIPT_DOMAIN + canonical_json_bytes(payload)
    ).hexdigest()
    with pytest.raises(verifier.ConstructionK7HierarchicalUtilizationIndependentVerifierV104Error):
        verifier.verify_hierarchical_utilization_campaign_bytes_v104(
            canonical_json_bytes(document)
        )


def test_v104_frozen_verification_identity():
    raw = verifier.freeze_hierarchical_utilization_verification_v104(
        CAMPAIGN_PATH.read_bytes()
    )
    document = loads_canonical_json(raw)
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
