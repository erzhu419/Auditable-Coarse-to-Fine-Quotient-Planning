import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_terminal_overlay_target_independent_verifier_v93 as verifier
from acfqp.phase3e_ids import loads_canonical_json


def test_v93_independent_verifier_rejects_foreign_bytes():
    with pytest.raises(
        verifier.ConstructionK7TerminalOverlayTargetIndependentVerifierV93Error
    ):
        verifier.verify_terminal_overlay_target_campaign_bytes_v93(b"{}")


def test_v93_independent_verifier_has_no_campaign_producer_or_core_import():
    source = Path(
        "src/acfqp/construction_k7_terminal_overlay_target_independent_verifier_v93.py"
    ).read_text()
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.construction_k7_terminal_overlay_target_campaign_v93" not in imported
    assert "acfqp.terminal_overlay_target_campaign_core_v93" not in imported
    assert "acfqp.generic_terminal_overlay_version_space_planner_v69" not in imported
    assert "acfqp.generic_joint_partial_terminal_acquisition_v70" not in imported
    assert "acfqp.generic_terminal_overlay_target_ablation_v72" not in imported


def test_v93_frozen_failure_is_independently_reconstructed_and_verified():
    campaign_raw = Path(
        ".tmp/exact-freeze/v93_terminal_overlay_target_campaign.json"
    ).read_bytes()
    result = verifier.verify_terminal_overlay_target_campaign_bytes_v93(
        campaign_raw
    )
    frozen = Path(
        ".tmp/exact-freeze/v93_terminal_overlay_target_verification.json"
    ).read_bytes()
    document = loads_canonical_json(result)
    assert result == frozen
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert len(result) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(result).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert document[
        "target_terminal_program_independently_reconstructed_from_prequential_prefix"
    ] is True
    assert document["total_target_label_tax_including_acquisition_beats_strict_direct"] is False
    assert document["sample_tax_problem_resolved"] is False
    assert document["official_execution_allowed"] is False
