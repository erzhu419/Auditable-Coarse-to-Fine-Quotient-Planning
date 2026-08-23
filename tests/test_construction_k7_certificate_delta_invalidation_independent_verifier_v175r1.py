import ast
import hashlib
import os
from pathlib import Path

from acfqp.construction_k7_certificate_delta_invalidation_independent_verifier_v175r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    _verify_sequence,
    verify_certificate_delta_invalidation_campaign_v175r1,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v175r1_verifier_does_not_import_producer_core_or_sequence():
    path = ROOT / (
        "src/acfqp/"
        "construction_k7_certificate_delta_invalidation_independent_verifier_v175r1.py"
    )
    tree = ast.parse(path.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden = (
        "certificate_delta_driven_invalidation_sequence_v175",
        "certificate_delta_invalidation_campaign_core_v175",
        "certificate_delta_invalidation_campaign_core_v175r1",
        "construction_k7_certificate_delta_invalidation_campaign_v175",
        "construction_k7_certificate_delta_invalidation_campaign_v175r1",
    )
    assert not any(any(name.endswith(item) for item in forbidden) for name in imported)


def test_v175r1_frozen_bytes_reconstruct_delta_and_receipt_lifecycle():
    campaign = loads_canonical_json(
        (FREEZE / "v175r1_certificate_delta_invalidation_campaign.json").read_bytes()
    )
    for occurrence in campaign["target_occurrences"]:
        for key in ("progressive_prior_sequence", "progressive_strict_sequence"):
            sequence = occurrence[key]
            summary = _verify_sequence(sequence, sequence)
            assert summary["issuance"] > 0
            assert summary["joins"] == sequence["execution_step_count"]
            assert summary["delta_receipts"] == len(sequence["episodes"])
            assert summary["delta_transition_joins"] == len(sequence["episodes"]) - 1
            assert summary["full_graph_diff_checks_avoided"] > 0


def test_v175r1_frozen_verification_summary():
    raw = (
        FREEZE / "v175r1_certificate_delta_invalidation_verification.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["producer_free_certificate_delta_reconstruction"] is True
    assert document["producer_free_minimal_invalidation_reconstruction"] is True
    assert document[
        "zero_serialized_full_graph_scan_on_decision_path_independently_verified"
    ] is True


def test_v175r1_full_producer_free_reexecution_when_requested():
    if os.environ.get("ACFQP_RUN_V175R1_INDEPENDENT") != "1":
        return
    document = verify_certificate_delta_invalidation_campaign_v175r1(
        (
            FREEZE
            / "v175r1_certificate_delta_invalidation_preregistration.json"
        ).read_bytes(),
        (FREEZE / "v175r1_certificate_delta_invalidation_campaign.json").read_bytes(),
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        (FREEZE / "v175_certificate_delta_invalidation_failure.json").read_bytes(),
    )
    assert document["producer_free_target_outcome_reexecution"] is True
    assert document["verified_certificate_local_delta_receipts"] > 0
    assert document["verified_graph_dependency_retentions"] > 0
