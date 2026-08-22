import ast
from pathlib import Path
import hashlib

from acfqp.construction_k7_online_typed_plan_receipt_independent_verifier_v172r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    verify_online_typed_plan_receipt_campaign_v172r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _inputs():
    return (
        (
            FREEZE / "v172r1_online_typed_plan_receipt_preregistration.json"
        ).read_bytes(),
        (FREEZE / "v172r1_online_typed_plan_receipt_campaign.json").read_bytes(),
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
    )


def test_v172r1_independent_verifier_has_no_producer_or_v172_runtime_import():
    path = ROOT / "src/acfqp/construction_k7_online_typed_plan_receipt_independent_verifier_v172r1.py"
    tree = ast.parse(path.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(
        name.endswith("online_typed_plan_receipt_sequence_v172")
        or name.endswith("online_typed_plan_receipt_campaign_core_v172")
        or name.endswith("online_typed_plan_receipt_campaign_v172r1")
        for name in imported
    )


def test_v172r1_frozen_independent_verification_bytes():
    if VERIFICATION_ID == "0" * 64:
        return
    document = verify_online_typed_plan_receipt_campaign_v172r1(*_inputs())
    raw = canonical_json_bytes(document)
    frozen = (
        FREEZE / "v172r1_online_typed_plan_receipt_verification.json"
    ).read_bytes()
    assert raw == frozen
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["producer_free_online_issuance_reconstruction"] is True
    assert document["verified_factor_prior_labels_avoided"] > 0


def test_v172r1_independent_verifier_rejects_resigned_campaign_change():
    prereg, campaign_raw, *rest = _inputs()
    campaign = loads_canonical_json(campaign_raw)
    campaign["official_execution_allowed"] = True
    payload = {key: value for key, value in campaign.items() if key != "campaign_id"}
    from acfqp import construction_k7_domain_registry_extension_v172 as domains

    campaign["campaign_id"] = domains.extension_content_id_v172(
        domains.CONSTRUCTION_K7_CAMPAIGN_V172_DOMAIN, payload
    )
    try:
        verify_online_typed_plan_receipt_campaign_v172r1(
            prereg, canonical_json_bytes(campaign), *rest
        )
    except ValueError:
        pass
    else:
        raise AssertionError("V172r1 verifier accepted a resigned campaign change")
