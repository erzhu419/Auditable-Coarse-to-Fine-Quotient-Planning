import ast
from pathlib import Path
import hashlib

from acfqp.construction_k7_cross_family_branch_complete_independent_verifier_v173r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v173r1_verifier_does_not_import_campaign_producer_or_core():
    path = ROOT / "src/acfqp/construction_k7_cross_family_branch_complete_independent_verifier_v173r1.py"
    tree = ast.parse(path.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(
        name.endswith("cross_family_branch_complete_online_receipt_core_v173r1")
        or name.endswith("cross_family_branch_complete_campaign_v173r1")
        for name in imported
    )


def test_v173r1_frozen_verification_summary():
    if VERIFICATION_ID == "0" * 64:
        return
    raw = (
        FREEZE / "v173r1_cross_family_branch_complete_verification.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["producer_free_all_four_online_sources_reconstructed"] is True
    assert all(
        count > 0
        for count in document["verified_online_typed_plan_source_histogram"].values()
    )
