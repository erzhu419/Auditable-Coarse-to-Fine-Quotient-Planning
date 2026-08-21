import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_catalogue_closed_legality_quotient_independent_verifier_v107 as verifier
from acfqp.phase3e_ids import loads_canonical_json


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v107_catalogue_closed_legality_quotient_campaign.json"
)


def test_v107_verifier_is_producer_free_and_reconstructs_all_plans():
    source = Path(verifier.__file__).read_text()
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(
        "catalogue_closed_legality_quotient_campaign_v107" in name
        or "catalogue_closed_legality_conditioned_quotient_campaign_core_v107" in name
        or "generic_complete_anonymous_action_catalogue_receipt_v107" in name
        for name in imported
    )
    result = verifier.verify_catalogue_closed_legality_quotient_campaign_bytes_v107(
        CAMPAIGN_PATH.read_bytes()
    )
    assert result["registered_gate_independently_verified"] is True
    assert result["producer_free_observation_and_fallback_plan_reconstruction"] is True
    assert result["verified_accounting"]["execution_steps"] == 60
    assert result["verified_accounting"][
        "quotient_proposal_admitted_execution_count"
    ] == 60
    assert result["verified_accounting"][
        "chosen_action_matches_admitted_quotient_proposal_count"
    ] == 49
    assert result["verified_accounting"]["quotient_lifetime_target_labels"] == 306
    assert result["verified_accounting"]["cold_direct_lifetime_target_labels"] == 534
    assert result["verified_abstract_plan_receipt_count"] == 417
    assert result["verified_fallback_plan_receipt_count"] == 120
    assert result["verified_actual_execution_receipt_count_using_fallback"] == 12
    assert result["complete_ground_world_model_synthesized"] is False


def test_v107_full_replay_rejects_rehashed_catalogue_descriptor_change():
    document = loads_canonical_json(CAMPAIGN_PATH.read_bytes())
    occurrence = document["target_occurrences"][0]
    receipt = occurrence["complete_anonymous_action_catalogue_receipt"]
    receipt["action_descriptor_rows"][0]["anonymous_fields"][0] += 1
    payload = {
        key: value for key, value in receipt.items() if key != "catalogue_receipt_id"
    }
    receipt["catalogue_receipt_id"] = verifier.domains.extension_content_id_v107(
        verifier.domains.CONSTRUCTION_K7_COMPLETE_ANONYMOUS_ACTION_CATALOGUE_RECEIPT_V107_DOMAIN,
        payload,
    )
    occurrence_payload = {
        key: value for key, value in occurrence.items() if key != "occurrence_id"
    }
    occurrence["occurrence_id"] = verifier.domains.extension_content_id_v107(
        verifier.domains.CONSTRUCTION_K7_CATALOGUE_CLOSED_LEGALITY_QUOTIENT_OCCURRENCE_V107_DOMAIN,
        occurrence_payload,
    )
    with pytest.raises(
        verifier.ConstructionK7CatalogueClosedLegalityQuotientIndependentVerifierV107Error
    ):
        verifier._occurrence(
            occurrence, "BALANCED_BATCH_REFINEMENT", 1_019_101
        )


def test_v107_frozen_verification_identity():
    raw = verifier.freeze_catalogue_closed_legality_quotient_verification_v107(
        CAMPAIGN_PATH.read_bytes()
    )
    document = loads_canonical_json(raw)
    if verifier.VERIFICATION_ID != "0" * 64:
        assert document["verification_id"] == verifier.VERIFICATION_ID
        assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
