from __future__ import annotations

import ast
from pathlib import Path
import shutil

import pytest

from acfqp import (
    construction_k7_full_ground_fallback_production_evidence_freeze_v180r7r1
    as freeze,
)


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"
SOURCE = (
    ROOT
    / "src"
    / "acfqp"
    / "construction_k7_full_ground_fallback_production_evidence_freeze_v180r7r1.py"
)


def test_v180r7r1_success_evidence_is_exactly_frozen_and_replayed() -> None:
    frozen = (
        freeze.load_frozen_full_ground_fallback_production_evidence_v180r7r1()
    )
    terminal = frozen.terminal_document()
    verification = frozen.verification_document()
    assert frozen.terminal_bundle_id == freeze.EXPECTED_TERMINAL_BUNDLE_ID
    assert frozen.verification_id == freeze.EXPECTED_VERIFICATION_ID
    assert len(frozen.output_inventory) == 8
    assert terminal["production_terminal_bundle_id"] == frozen.terminal_bundle_id
    assert terminal["production_execution_slot"]["preserved_v180r7_failure_id"] == (
        freeze.EXPECTED_PRESERVED_V180R7_FAILURE_ID
    )
    assert verification["retained_output_file_count"] == 8
    assert verification[
        "retained_source_output_bytes_replayed_without_producer_import"
    ] is True
    assert verification["three_source_v6_route_chains_reconstructed"] is True
    assert verification["registered_v6_to_v9_counter_lift_reconstructed"] is True
    assert verification["fresh_single_path_verified"] is True
    assert verification["all_ten_paths_verified"] is False
    assert verification["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert verification["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert verification["official_execution_allowed"] is False


def test_v180r7r1_eight_role_denominator_is_exact() -> None:
    facts = freeze.EXPECTED_OUTPUT_ROLE_FACTS
    assert tuple(row[0] for row in facts) == (
        "ACTUAL_PROJECTION_PROOF",
        "BUSINESS_RESULT",
        "COMPARISON_VECTOR",
        "COUNTER_RECORD_SET",
        "OPERATIONAL_TRACE",
        "OUTPUT_MANIFEST",
        "TERMINAL_ARTIFACT",
        "WORK_VECTOR",
    )
    assert sum(row[2] for row in facts) == freeze.EXPECTED_SOURCE_OUTPUT_BYTE_COUNT


def test_v180r7r1_freeze_rejects_retained_terminal_byte_mutation(
    tmp_path: Path,
) -> None:
    retained = tmp_path / "retained"
    retained.mkdir()
    shutil.copytree(
        BASE / "v180r7r1_full_ground_fallback_output",
        retained / "v180r7r1_full_ground_fallback_output",
    )
    terminal_name = "v180r7r1_full_ground_fallback_terminal_bundle.json"
    verification_name = "v180r7r1_full_ground_fallback_verification.json"
    terminal = (BASE / terminal_name).read_bytes()
    (retained / terminal_name).write_bytes(terminal + b"\n")
    shutil.copy2(BASE / verification_name, retained / verification_name)
    with pytest.raises(
        freeze.FullGroundFallbackProductionEvidenceFreezeV180r7r1Error
    ):
        freeze.load_frozen_full_ground_fallback_production_evidence_v180r7r1(
            retained
        )


def test_v180r7r1_freeze_rejects_failure_marker_coexistence(
    tmp_path: Path,
) -> None:
    failure = tmp_path / "v180r7r1_full_ground_fallback_failure.json"
    failure.write_bytes(b"{}")
    with pytest.raises(
        freeze.FullGroundFallbackProductionEvidenceFreezeV180r7r1Error,
        match="success and failure evidence coexist",
    ):
        freeze.load_frozen_full_ground_fallback_production_evidence_v180r7r1(
            tmp_path
        )


def test_v180r7r1_freeze_rejects_one_role_byte_mutation(
    tmp_path: Path,
) -> None:
    retained = tmp_path / "retained"
    retained.mkdir()
    output = retained / "v180r7r1_full_ground_fallback_output"
    shutil.copytree(BASE / output.name, output)
    for filename in (
        "v180r7r1_full_ground_fallback_terminal_bundle.json",
        "v180r7r1_full_ground_fallback_verification.json",
    ):
        shutil.copy2(BASE / filename, retained / filename)
    role = output / "BUSINESS_RESULT.json"
    raw = role.read_bytes()
    original = b'"terminal_code":"FULL_GROUND_FALLBACK"'
    forged = b'"terminal_code":"FULL_GROUND_FALLBACX"'
    assert raw.count(original) >= 1 and len(original) == len(forged)
    role.write_bytes(raw.replace(original, forged, 1))
    with pytest.raises(
        freeze.FullGroundFallbackProductionEvidenceFreezeV180r7r1Error,
        match="retained BUSINESS_RESULT exact bytes changed",
    ):
        freeze.load_frozen_full_ground_fallback_production_evidence_v180r7r1(
            retained
        )


def test_v180r7r1_post_outcome_freeze_surface_is_producer_free() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            imports.extend(alias.name for alias in node.names)
    assert not any("production_terminal_finalizer_v180r7r1" in item for item in imports)
    assert not any("run_v180r7r1_full_ground_fallback_occurrence" in item for item in imports)
