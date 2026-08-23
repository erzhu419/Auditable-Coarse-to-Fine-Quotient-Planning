import ast
import hashlib
import os
from pathlib import Path

from acfqp.construction_k7_reverse_index_only_invalidation_independent_verifier_v177 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    _verify_sequence,
    verify_reverse_index_only_invalidation_campaign_v177,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v177_verifier_does_not_import_producer_core_or_sequence():
    path = ROOT / (
        "src/acfqp/"
        "construction_k7_reverse_index_only_invalidation_independent_verifier_v177.py"
    )
    tree = ast.parse(path.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden = (
        "reverse_index_only_invalidation_sequence_v177",
        "reverse_index_only_invalidation_campaign_core_v177",
        "construction_k7_reverse_index_only_invalidation_campaign_v177",
    )
    assert not any(any(name.endswith(item) for item in forbidden) for name in imported)


def test_v177_frozen_bytes_reconstruct_reverse_index_and_full_controls():
    campaign = loads_canonical_json(
        (FREEZE / "v177_reverse_index_only_invalidation_campaign.json").read_bytes()
    )
    for occurrence in campaign["target_occurrences"]:
        for key in ("progressive_prior_sequence", "progressive_strict_sequence"):
            sequence = occurrence[key]
            summary = _verify_sequence(sequence, sequence)
            assert summary["issuance"] > 0
            assert summary["joins"] == sequence["execution_step_count"]
            assert summary["production_full_graph_diff_checks"] == 0
            assert summary["production_live_dependency_projection_scan_count"] == 0
            assert summary["verifier_full_graph_diff_checks"] > 0
            assert summary["verifier_full_dependency_projection_checks"] > 0
            assert summary["verified_control_transition_count"] == len(
                sequence["episodes"]
            ) - 1


def test_v177_frozen_verification_summary():
    if VERIFICATION_ID == "0" * 64:
        return
    raw = (
        FREEZE / "v177_reverse_index_only_invalidation_verification.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["verified_production_full_graph_diff_checks"] == 0
    assert document[
        "verified_production_live_dependency_projection_scan_count"
    ] == 0
    assert document[
        "reverse_index_full_dependency_control_equality_independently_verified"
    ] is True


def test_v177_full_producer_free_reexecution_when_requested():
    if os.environ.get("ACFQP_RUN_V177_INDEPENDENT") != "1":
        return
    document = verify_reverse_index_only_invalidation_campaign_v177(
        (
            FREEZE
            / "v177_reverse_index_only_invalidation_preregistration.json"
        ).read_bytes(),
        (FREEZE / "v177_reverse_index_only_invalidation_campaign.json").read_bytes(),
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        (
            FREEZE / "v176_certificate_delta_only_invalidation_campaign.json"
        ).read_bytes(),
        (
            FREEZE
            / "v176_certificate_delta_only_invalidation_verification.json"
        ).read_bytes(),
    )
    assert document["producer_free_target_outcome_reexecution"] is True
    assert document["verified_production_full_graph_diff_checks"] == 0
    assert document[
        "verified_production_live_dependency_projection_scan_count"
    ] == 0
