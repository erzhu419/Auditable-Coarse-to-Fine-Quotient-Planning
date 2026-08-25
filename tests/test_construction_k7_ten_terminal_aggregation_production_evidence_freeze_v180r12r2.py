from __future__ import annotations

import ast
from pathlib import Path
import shutil

import pytest

from acfqp import (
    construction_k7_ten_terminal_aggregation_production_evidence_freeze_v180r12r2
    as freeze,
)


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"
SOURCE = (
    ROOT
    / "src"
    / "acfqp"
    / "construction_k7_ten_terminal_aggregation_production_evidence_freeze_v180r12r2.py"
)


def _copy_retained_success(destination: Path) -> Path:
    destination.mkdir()
    for _role, relative_path, _field, _identity, _count, _sha256 in (
        freeze.EXPECTED_RETAINED_FILE_FACTS
    ):
        source = BASE / relative_path
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(freeze.EXPECTED_RETAINED_FILE_MODE)
    for relative_path, mode in freeze.EXPECTED_RETAINED_DIRECTORY_MODES:
        (destination / relative_path).chmod(mode)
    return destination


def test_v180r12r2_production_evidence_is_exactly_frozen_statically() -> None:
    frozen = (
        freeze.load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2()
    )
    terminal = frozen.terminal_document()
    verification = frozen.verification_document()
    assert frozen.production_aggregation_bundle_id == (
        freeze.EXPECTED_PRODUCTION_AGGREGATION_BUNDLE_ID
    )
    assert frozen.verification_id == freeze.EXPECTED_VERIFICATION_ID
    assert frozen.verification_bytes == frozen.replay_bytes
    assert len(frozen.retained_file_facts) == 10
    assert terminal["source_group_count"] == 5
    assert terminal["terminal_receipt_count"] == 10
    assert terminal["route_component_chain_receipt_count"] == 12
    assert terminal["occurrence_shared_resource_receipt_count"] == 90
    assert terminal["route_component_counter_record_count"] == 3_228
    assert terminal["ten_terminal_representative_counter_record_count"] == 2_690
    assert terminal["v180r7r1_additional_counter_record_count"] == 538
    assert terminal["campaign_scope_structural_obligation_count"] == 9
    assert verification["route_component_counter_closure_status"] == "PASS"
    assert verification["campaign_scope_actual_measurement_ledger_present"] is False
    assert verification["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert verification["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert verification["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert verification["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert verification["official_execution_allowed"] is False


def test_v180r12r2_freeze_rejects_same_size_terminal_mutation(
    tmp_path: Path,
) -> None:
    retained = _copy_retained_success(tmp_path / "retained")
    path = retained / freeze.EXPECTED_RETAINED_FILE_FACTS[0][1]
    raw = path.read_bytes()
    original = freeze.EXPECTED_PRODUCTION_AGGREGATION_BUNDLE_ID.encode("ascii")
    forged = b"b" + original[1:]
    assert len(original) == len(forged) and raw.count(original) == 1
    path.chmod(0o600)
    path.write_bytes(raw.replace(original, forged, 1))
    path.chmod(freeze.EXPECTED_RETAINED_FILE_MODE)
    with pytest.raises(
        freeze.TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error,
        match="retained TERMINAL exact bytes changed",
    ):
        freeze.load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2(
            retained
        )


def test_v180r12r2_freeze_rejects_verification_replay_mutation(
    tmp_path: Path,
) -> None:
    retained = _copy_retained_success(tmp_path / "retained")
    replay_fact = next(
        row for row in freeze.EXPECTED_RETAINED_FILE_FACTS if row[0] == "REPLAY"
    )
    path = retained / replay_fact[1]
    raw = path.read_bytes()
    original = freeze.EXPECTED_VERIFICATION_ID.encode("ascii")
    forged = b"6" + original[1:]
    assert len(original) == len(forged) and raw.count(original) == 1
    path.chmod(0o600)
    path.write_bytes(raw.replace(original, forged, 1))
    path.chmod(freeze.EXPECTED_RETAINED_FILE_MODE)
    with pytest.raises(
        freeze.TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error,
        match="retained REPLAY exact bytes changed",
    ):
        freeze.load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2(
            retained
        )


def test_v180r12r2_freeze_rejects_success_failure_coexistence(
    tmp_path: Path,
) -> None:
    retained = _copy_retained_success(tmp_path / "retained")
    failure = retained / freeze.EXPECTED_ABSENT_RELATIVE_PATHS[3]
    failure.write_bytes(b"{}")
    with pytest.raises(
        freeze.TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error,
        match="success and failure or runtime-CAS evidence coexist",
    ):
        freeze.load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2(
            retained
        )


def test_v180r12r2_freeze_rejects_runtime_cas_coexistence(
    tmp_path: Path,
) -> None:
    retained = _copy_retained_success(tmp_path / "retained")
    runtime_cas = retained / freeze.EXPECTED_ABSENT_RELATIVE_PATHS[-1]
    runtime_cas.mkdir()
    with pytest.raises(
        freeze.TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error,
        match="success and failure or runtime-CAS evidence coexist",
    ):
        freeze.load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2(
            retained
        )


def test_v180r12r2_freeze_rejects_linked_retained_file(tmp_path: Path) -> None:
    retained = _copy_retained_success(tmp_path / "retained")
    terminal_fact = freeze.EXPECTED_RETAINED_FILE_FACTS[0]
    path = retained / terminal_fact[1]
    path.unlink()
    path.symlink_to(BASE / terminal_fact[1])
    with pytest.raises(
        freeze.TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error,
        match="absent, linked, or unreadable",
    ):
        freeze.load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2(
            retained
        )


def test_v180r12r2_freeze_rejects_linked_base(tmp_path: Path) -> None:
    retained = _copy_retained_success(tmp_path / "retained")
    linked = tmp_path / "linked"
    linked.symlink_to(retained, target_is_directory=True)
    with pytest.raises(
        freeze.TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error,
        match="absent, linked, or unreadable component",
    ):
        freeze.load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2(
            linked
        )


def test_v180r12r2_freeze_rejects_retained_mode_drift(tmp_path: Path) -> None:
    retained = _copy_retained_success(tmp_path / "retained")
    terminal_fact = freeze.EXPECTED_RETAINED_FILE_FACTS[0]
    (retained / terminal_fact[1]).chmod(0o600)
    with pytest.raises(
        freeze.TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error,
        match="type, mode, link count, or size changed",
    ):
        freeze.load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2(
            retained
        )


def test_v180r12r2_freeze_rejects_retained_directory_mode_drift(
    tmp_path: Path,
) -> None:
    retained = _copy_retained_success(tmp_path / "retained")
    relative_path, _mode = freeze.EXPECTED_RETAINED_DIRECTORY_MODES[0]
    (retained / relative_path).chmod(0o755)
    with pytest.raises(
        freeze.TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error,
        match="directory mode changed",
    ):
        freeze.load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2(
            retained
        )


def test_v180r12r2_freeze_rederives_all_129_inner_content_ids() -> None:
    frozen = freeze.load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2()
    terminal = frozen.terminal_document()
    assert freeze.EXPECTED_INNER_CONTENT_ID_COUNT == 129
    freeze._assert_all_inner_content_ids(terminal)
    terminal["route_component_chain_receipts"][0]["counter_record_count"] = 268
    with pytest.raises(
        freeze.TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error,
        match="route_component_chain_receipt_id is not the registered content ID",
    ):
        freeze._assert_all_inner_content_ids(terminal)


def test_v180r12r2_freeze_rechecks_failure_absence_after_retained_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    retained = _copy_retained_success(tmp_path / "retained")
    original = freeze._read_regular_stable
    last_path = freeze.EXPECTED_RETAINED_FILE_FACTS[-1][1]

    def read_then_publish_failure(
        base_fd: int, relative_path: str, byte_count: int
    ) -> bytes:
        raw = original(base_fd, relative_path, byte_count)
        if relative_path == last_path:
            (retained / freeze.EXPECTED_ABSENT_RELATIVE_PATHS[3]).write_bytes(b"{}")
        return raw

    monkeypatch.setattr(freeze, "_read_regular_stable", read_then_publish_failure)
    with pytest.raises(
        freeze.TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error,
        match="success and failure or runtime-CAS evidence coexist",
    ):
        freeze.load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2(
            retained
        )


def test_v180r12r2_launch_stdout_joins_authorization_evidence_and_outputs() -> None:
    for target in ("PRODUCTION", "VERIFICATION"):
        role = f"{target}_LAUNCH_RECEIPT"
        fact = next(row for row in freeze.EXPECTED_RETAINED_FILE_FACTS if row[0] == role)
        receipt = freeze._document((BASE / fact[1]).read_bytes(), role)
        stdout = freeze._launch_stdout_document(receipt, role)
        assert stdout["execution_authorization_id"] == (
            freeze.EXPECTED_EXECUTION_AUTHORIZATION_ID
        )
        if target == "PRODUCTION":
            assert stdout["authorization_evidence_id"] == (
                freeze.EXPECTED_AUTHORIZATION_EVIDENCE_ID
            )
            assert stdout["production_aggregation_bundle_id"] == (
                freeze.EXPECTED_PRODUCTION_AGGREGATION_BUNDLE_ID
            )
        else:
            assert stdout["verification_id"] == freeze.EXPECTED_VERIFICATION_ID
            assert stdout["retained_replay_exact"] is True


def test_v180r12r2_post_outcome_freeze_surface_has_no_execution_imports() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            imports.extend(alias.name for alias in node.names)
    forbidden = (
        "finalizer_v180r12r2",
        "independent_verifier_v180r12r2",
        "run_v180r12r2",
        "launch_v180r12r2",
        "materialize_v180r12r2",
    )
    assert not any(marker in imported for marker in forbidden for imported in imports)
