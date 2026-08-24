from __future__ import annotations

from pathlib import Path

import pytest

from acfqp import construction_k7_domain_registry_extension_v180r7r1 as domains
from acfqp.phase3e_ids import canonical_json_bytes
from scripts import run_v180r7r1_full_ground_fallback_occurrence as runner


def test_runner_write_once_fsyncs_file_and_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "terminal.json"
    descriptors: list[int] = []
    monkeypatch.setattr(runner.os, "fsync", descriptors.append)
    runner._write_once(target, b"{}")
    assert target.read_bytes() == b"{}"
    assert len(descriptors) == 2
    with pytest.raises(FileExistsError):
        runner._write_once(target, b"{}")


def test_runner_typed_failure_binds_exact_partial_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cas_root = tmp_path / "cas"
    output_root = tmp_path / "output"
    success = tmp_path / "terminal.json"
    verification = tmp_path / "verification.json"
    cas_root.mkdir()
    output_root.mkdir()
    (output_root / "partial.json").write_bytes(b"partial")
    monkeypatch.setattr(runner, "CAS_ROOT", cas_root)
    monkeypatch.setattr(runner, "OUTPUT_ROOT", output_root)
    monkeypatch.setattr(runner, "SUCCESS", success)
    monkeypatch.setattr(runner, "VERIFICATION", verification)
    document, raw = runner._failure_document(
        RuntimeError("injected"),
        authorization_id="a" * 64,
        protocol_id="b" * 64,
        slot_id="c" * 64,
        failed_phase="FRESH_PRODUCTION_OCCURRENCE",
    )
    payload = dict(document)
    failure_id = payload.pop("failure_id")
    assert failure_id == domains.extension_content_id_v180r7r1(
        domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_FAILURE_V180R7R1_DOMAIN,
        payload,
    )
    assert canonical_json_bytes(document) == raw
    assert document["runtime_cas_state"]["presence"] == "DIRECTORY"
    assert document["output_progress_inventory"]["regular_file_count"] == 1
    assert document["output_progress_inventory"]["regular_file_byte_count"] == 7
    assert document["same_authorization_rerun_forbidden"] is True
    assert document["scientific_success_claimed"] is False
    assert document["official_execution_allowed"] is False


def test_exact_completed_success_is_recognized_without_new_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cas_root = tmp_path / "cas"
    output_root = tmp_path / "output"
    success = tmp_path / "terminal.json"
    failure = tmp_path / "failure.json"
    cas_root.mkdir()
    output_root.mkdir()
    slot = {"production_execution_slot_id": "c" * 64}
    authorization_document = {
        "fallback_execution_protocol_id": "b" * 64,
        "production_execution_slot": slot,
    }
    payload = {
        "schema": "acfqp.full_ground_fallback_production_terminal_bundle.v180r7r1",
        "fallback_execution_protocol_id": "b" * 64,
        "production_execution_slot": slot,
        "terminal_code": "FULL_GROUND_FALLBACK",
    }
    document = {
        **payload,
        "production_terminal_bundle_id": domains.extension_content_id_v180r7r1(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_TERMINAL_V180R7R1_DOMAIN,
            payload,
        ),
    }
    success.write_bytes(canonical_json_bytes(document))
    monkeypatch.setattr(runner, "CAS_ROOT", cas_root)
    monkeypatch.setattr(runner, "OUTPUT_ROOT", output_root)
    monkeypatch.setattr(runner, "SUCCESS", success)
    monkeypatch.setattr(runner, "FAILURE", failure)
    assert runner._exact_completed_success_present(authorization_document) is True
    assert not failure.exists()


def test_runner_is_fixed_to_fresh_paths_caps_and_one_shot_finalizer() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "v180r7r1_full_ground_fallback_cas" in source
    assert "v180r7r1_full_ground_fallback_output" in source
    assert "v180r7r1_full_ground_fallback_terminal_bundle.json" in source
    assert "v180r7r1_full_ground_fallback_failure.json" in source
    assert "run_full_ground_fallback_production_occurrence_v180r7r1" in source
    assert "authorization.ADDRESS_SPACE_HARD_CAP_BYTES" in source
    assert "resource.setrlimit(resource.RLIMIT_AS, (cap, cap))" in source
    assert "os.O_EXCL" in source
    assert "os.fsync(descriptor)" in source
    assert "except BaseException as error:" in source
    assert "run_full_ground_fallback_production_occurrence_v180r7(" not in source
    assert not runner.CAS_ROOT.exists()
    assert not runner.OUTPUT_ROOT.exists()
    assert not runner.SUCCESS.exists()
    assert not runner.FAILURE.exists()
