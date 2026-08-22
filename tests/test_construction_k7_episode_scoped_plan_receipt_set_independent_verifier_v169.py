import ast
import hashlib
from pathlib import Path

import pytest

from acfqp.construction_k7_episode_scoped_plan_receipt_set_independent_verifier_v169 import (
    VERIFICATION_CANONICAL_BYTE_COUNT,
    VERIFICATION_CANONICAL_SHA256,
    VERIFICATION_ID,
    ConstructionK7EpisodeScopedPlanReceiptSetIndependentVerifierV169Error,
    freeze_episode_scoped_plan_receipt_set_verification_v169,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _inputs(audit=None):
    return (
        (FREEZE / "v169_episode_scoped_plan_receipt_set_audit.json").read_bytes()
        if audit is None
        else audit,
        (FREEZE / "v168_fifth_family_total_plan_receipt_set_campaign.json").read_bytes(),
    )


def test_v169_verifier_has_no_audit_producer_import():
    path = (
        ROOT
        / "src/acfqp/construction_k7_episode_scoped_plan_receipt_set_independent_verifier_v169.py"
    )
    tree = ast.parse(path.read_text())
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.episode_scoped_plan_receipt_set_audit_v169" not in imported


def test_v169_frozen_producer_free_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V169 verification not frozen")
    raw = freeze_episode_scoped_plan_receipt_set_verification_v169(*_inputs())
    frozen = (
        FREEZE / "v169_episode_scoped_plan_receipt_set_verification.json"
    ).read_bytes()
    assert raw == frozen
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == VERIFICATION_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == VERIFICATION_CANONICAL_SHA256
    assert document["verified_receipt_set_histogram"]["NONE"] == 12
    assert document["verified_receipt_set_histogram"]["MIXED"] == 2
    assert document["none_still_bound_to_v109_and_query_local_certificate"] is True
    assert document[
        "episode_receipt_set_annotation_is_model_planning_or_certificate_authority"
    ] is False


def test_v169_rejects_resigned_audit_tamper():
    document = loads_canonical_json(_inputs()[0])
    document["receipt_set_rows"][0]["registered_plan_receipt_set_class"] = "NONE"
    payload = {key: value for key, value in document.items() if key != "audit_id"}
    from acfqp import construction_k7_domain_registry_extension_v169 as domains

    document["audit_id"] = domains.extension_content_id_v169(
        domains.CONSTRUCTION_K7_AUDIT_V169_DOMAIN, payload
    )
    with pytest.raises(
        ConstructionK7EpisodeScopedPlanReceiptSetIndependentVerifierV169Error,
        match="frozen audit changed",
    ):
        freeze_episode_scoped_plan_receipt_set_verification_v169(
            *_inputs(canonical_json_bytes(document))
        )
