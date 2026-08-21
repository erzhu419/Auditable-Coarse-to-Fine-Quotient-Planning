import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_legality_conditioned_quotient_independent_verifier_v106 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v106_legality_conditioned_quotient_campaign.json"
)


def test_v106_verifier_is_producer_free_and_reconstructs_failed_gate():
    source = Path(verifier.__file__).read_text()
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(
        "legality_conditioned_quotient_campaign_v106" in name
        or "legality_conditioned_quotient_campaign_core_v106" in name
        or "generic_legality_conditioned" in name
        or "generic_actual_legality_conditioned" in name
        for name in imported
    )
    result = verifier.verify_legality_conditioned_quotient_campaign_bytes_v106(
        CAMPAIGN_PATH.read_bytes()
    )
    assert result["registered_gate_independently_verified"] is False
    assert result["verified_accounting"]["execution_steps"] == 65
    assert result["verified_accounting"][
        "quotient_proposal_admitted_execution_count"
    ] == 65
    assert result["verified_accounting"][
        "chosen_action_matches_admitted_quotient_proposal_count"
    ] == 53
    assert result["verified_accounting"]["certificate_local_legality_plan_count"] == 4
    assert result["verified_accounting"]["quotient_lifetime_target_labels"] == 258
    assert result["verified_accounting"]["cold_direct_lifetime_target_labels"] == 588
    assert result["all_execution_steps_still_ordered_by_legality_conditioned_quotient"] is True
    assert result["fallback_plan_receipt_count_without_complete_catalogue_closure"] == 128
    assert result["actual_execution_receipt_count_using_unreconstructable_fallback"] == 6
    assert result["producer_free_fallback_plan_reconstruction"] is False
    assert result["complete_ground_world_model_synthesized"] is False


def test_v106_verifier_rejects_rehashed_gate_upgrade():
    document = loads_canonical_json(CAMPAIGN_PATH.read_bytes())
    document["registered_gate"]["passed"] = True
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = verifier.domains.extension_content_id_v106(
        verifier.domains.CONSTRUCTION_K7_LEGALITY_CONDITIONED_QUOTIENT_CAMPAIGN_V106_DOMAIN,
        payload,
    )
    with pytest.raises(
        verifier.ConstructionK7LegalityConditionedQuotientIndependentVerifierV106Error
    ):
        verifier.verify_legality_conditioned_quotient_campaign_bytes_v106(
            canonical_json_bytes(document)
        )


def test_v106_frozen_verification_identity():
    raw = verifier.freeze_legality_conditioned_quotient_verification_v106(
        CAMPAIGN_PATH.read_bytes()
    )
    document = loads_canonical_json(raw)
    if verifier.VERIFICATION_ID != "0" * 64:
        assert document["verification_id"] == verifier.VERIFICATION_ID
        assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
