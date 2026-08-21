import ast
import copy
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_quotient_utilization_independent_verifier_v105 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v105_actual_quotient_utilization_campaign.json"
)


def test_v105_verifier_is_producer_free_and_reconstructs_actual_ordering():
    source = Path(verifier.__file__).read_text()
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(
        "campaign_v105" in name
        or "campaign_core_v105" in name
        or "generic_observation_quotient_graph_v105" in name
        or "generic_actual_quotient_execution_receipt_v105" in name
        for name in imported
    )
    result = verifier.verify_quotient_utilization_campaign_bytes_v105(
        CAMPAIGN_PATH.read_bytes()
    )
    assert result["registered_gate_independently_verified"] is True
    assert result["verified_accounting"]["execution_steps"] == 73
    assert result["verified_accounting"]["quotient_proposal_admitted_execution_count"] == 55
    assert result["verified_accounting"][
        "chosen_action_matches_admitted_quotient_proposal_count"
    ] == 51
    assert result["verified_accounting"]["quotient_lifetime_target_labels"] == 230
    assert result["verified_accounting"]["cold_direct_lifetime_target_labels"] == 513
    assert result["verified_accounting"]["target_label_reduction"] == 283
    assert result["complete_ground_world_model_synthesized"] is False


def test_v105_verifier_rejects_rehashed_posthoc_ordering_claim():
    document = loads_canonical_json(CAMPAIGN_PATH.read_bytes())
    receipt = document["target_occurrences"][0]["persistent_quotient_sequence"][
        "all_actual_quotient_execution_receipts"
    ][0]
    receipt["actual_action_ordering_source"] = "EXACT_CERTIFICATE_POLICY_ONLY"
    payload = {
        key: value
        for key, value in receipt.items()
        if key != "actual_quotient_execution_receipt_id"
    }
    receipt["actual_quotient_execution_receipt_id"] = verifier._hash(
        verifier._RECEIPT_DOMAIN, payload
    )
    with pytest.raises(
        verifier.ConstructionK7QuotientUtilizationIndependentVerifierV105Error
    ):
        verifier.verify_quotient_utilization_campaign_bytes_v105(
            canonical_json_bytes(document)
        )


def test_v105_verifier_rejects_residual_imputation_claim():
    document = loads_canonical_json(CAMPAIGN_PATH.read_bytes())
    model = document["target_occurrences"][0]["persistent_quotient_sequence"][
        "quotient_models_before_each_episode"
    ][0]
    model["residual_coordinates_deliberately_quotiented_not_imputed"] = False
    payload = {key: value for key, value in model.items() if key != "quotient_graph_id"}
    model["quotient_graph_id"] = verifier._hash(verifier._MODEL_DOMAIN, payload)
    with pytest.raises(
        verifier.ConstructionK7QuotientUtilizationIndependentVerifierV105Error
    ):
        verifier.verify_quotient_utilization_campaign_bytes_v105(
            canonical_json_bytes(document)
        )


def test_v105_frozen_verification_identity():
    raw = verifier.freeze_quotient_utilization_verification_v105(
        CAMPAIGN_PATH.read_bytes()
    )
    document = loads_canonical_json(raw)
    if verifier.VERIFICATION_ID != "0" * 64:
        assert document["verification_id"] == verifier.VERIFICATION_ID
        assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
