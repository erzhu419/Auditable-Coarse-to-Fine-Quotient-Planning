import ast
import hashlib
from pathlib import Path

import pytest

from acfqp.construction_k7_sixth_family_complete_plan_receipt_independent_verifier_v171 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    ConstructionK7SixthFamilyCompletePlanReceiptIndependentVerifierV171Error,
    freeze_sixth_family_complete_plan_receipt_verification_v171,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _inputs(campaign=None):
    return (
        (FREEZE / "v171_sixth_family_complete_plan_receipt_campaign.json").read_bytes()
        if campaign is None
        else campaign,
        (FREEZE / "v171_sixth_family_complete_plan_receipt_preregistration.json").read_bytes(),
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
    )


def test_v171_verifier_has_no_v171_producer_core_or_annotator_import():
    path = ROOT / "src/acfqp/construction_k7_sixth_family_complete_plan_receipt_independent_verifier_v171.py"
    tree = ast.parse(path.read_text())
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.construction_k7_sixth_family_complete_plan_receipt_campaign_v171" not in imported
    assert "acfqp.sixth_family_complete_plan_receipt_campaign_core_v171" not in imported
    assert "acfqp.complete_plan_receipt_taxonomy_sequence_v171" not in imported


def test_v171_frozen_producer_free_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V171 verification not frozen")
    raw = freeze_sixth_family_complete_plan_receipt_verification_v171(*_inputs())
    frozen = (FREEZE / "v171_sixth_family_complete_plan_receipt_verification.json").read_bytes()
    assert raw == frozen
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["verified_factor_prior_labels_avoided"] == 16
    assert document["verified_typed_plan_receipt_count"] == 720
    assert document["verified_execution_join_receipt_count"] == 112
    assert document["producer_free_target_outcome_reexecution"] is True


def test_v171_rejects_resigned_taxonomy_tamper_before_reexecution():
    document = loads_canonical_json(_inputs()[0])
    document["target_occurrences"][0]["typed_plan_source_histogram"][
        "OBSERVATION_DERIVED_QUOTIENT_ORDER"
    ] += 1
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    from acfqp import construction_k7_domain_registry_extension_v171 as domains

    document["campaign_id"] = domains.extension_content_id_v171(
        domains.CONSTRUCTION_K7_CAMPAIGN_V171_DOMAIN, payload
    )
    with pytest.raises(
        ConstructionK7SixthFamilyCompletePlanReceiptIndependentVerifierV171Error,
        match="frozen campaign changed",
    ):
        freeze_sixth_family_complete_plan_receipt_verification_v171(
            *_inputs(canonical_json_bytes(document))
        )
