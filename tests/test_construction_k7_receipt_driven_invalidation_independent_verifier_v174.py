import ast
import hashlib
import os
from pathlib import Path

from acfqp.construction_k7_receipt_driven_invalidation_independent_verifier_v174 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    _verify_sequence,
    verify_receipt_driven_invalidation_campaign_v174,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v174_verifier_does_not_import_v174_producer_core_or_sequence():
    path = (
        ROOT
        / "src/acfqp/construction_k7_receipt_driven_invalidation_independent_verifier_v174.py"
    )
    tree = ast.parse(path.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden = (
        "receipt_driven_minimal_invalidation_sequence_v174",
        "receipt_driven_invalidation_campaign_core_v174",
        "construction_k7_receipt_driven_invalidation_campaign_v174",
    )
    assert not any(any(name.endswith(item) for item in forbidden) for name in imported)


def test_v174_frozen_bytes_reconstruct_dependency_lifecycle_without_producer():
    campaign = loads_canonical_json(
        (FREEZE / "v174_receipt_driven_invalidation_campaign.json").read_bytes()
    )
    for occurrence in campaign["target_occurrences"]:
        for key in ("progressive_prior_sequence", "progressive_strict_sequence"):
            sequence = occurrence[key]
            summary = _verify_sequence(sequence, sequence)
            assert summary["issuance"] > 0
            assert summary["joins"] == sequence["execution_step_count"]
            assert summary["graph_retentions"] > 0
            assert summary["incremental"] > 0


def test_v174_frozen_verification_summary():
    if VERIFICATION_ID == "0" * 64:
        return
    raw = (
        FREEZE / "v174_receipt_driven_invalidation_verification.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["producer_free_minimal_invalidation_reconstruction"] is True
    assert document[
        "producer_free_incremental_revalidation_chain_reconstruction"
    ] is True


def test_v174_full_producer_free_reexecution_when_requested():
    if os.environ.get("ACFQP_RUN_V174_INDEPENDENT") != "1":
        return
    document = verify_receipt_driven_invalidation_campaign_v174(
        (FREEZE / "v174_receipt_driven_invalidation_preregistration.json").read_bytes(),
        (FREEZE / "v174_receipt_driven_invalidation_campaign.json").read_bytes(),
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
    )
    assert document["producer_free_target_outcome_reexecution"] is True
    assert document["verified_graph_dependency_invalidations"] > 0
    assert document["verified_graph_dependency_retentions"] > 0

