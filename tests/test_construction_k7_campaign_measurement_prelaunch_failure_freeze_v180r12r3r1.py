from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import pytest

from acfqp import (
    construction_k7_campaign_measurement_prelaunch_failure_freeze_v180r12r3r1
    as frozen,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src/acfqp/"
    "construction_k7_campaign_measurement_prelaunch_failure_freeze_v180r12r3r1.py"
)
BASE = ROOT / ".tmp/exact-freeze"


@pytest.fixture
def native_tmp_path() -> Path:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v180r12r3r1-failure-freeze-", dir="/tmp"
    ) as directory:
        yield Path(directory)


def _copy_failure_boundary(destination: Path) -> None:
    destination.mkdir(mode=0o700)
    prelaunch = destination / "v180r12r3r1_campaign_measurement_prelaunch"
    prelaunch.mkdir(mode=0o700)
    for relative, _size, _digest in frozen._RETAINED_FILE_FACTS:
        source = BASE / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o400)
    prelaunch.chmod(0o700)


def test_actual_consumed_prelaunch_failure_is_frozen() -> None:
    value = frozen.load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1()
    attempt = value.launch_attempt_document()
    failure = value.launch_failure_document()
    assert value.launch_attempt_id == frozen.EXPECTED_LAUNCH_ATTEMPT_ID
    assert value.launch_failure_id == frozen.EXPECTED_LAUNCH_FAILURE_ID
    assert len(frozen._RETAINED_FILE_FACTS) == 7
    assert len(frozen._PRELAUNCH_EXACT_ENTRIES) == 5
    assert len(frozen._REQUIRED_ABSENT_PATHS) == 12
    assert attempt["scientific_occurrence_started"] is False
    assert attempt["campaign_actual_measurement"] is False
    assert failure["attempt_lock_preserved"] is True
    assert failure["same_target_identity_rerun_forbidden"] is True
    assert failure["authorized_child_measurement_execution_completed"] is False
    assert failure["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert failure["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert failure["official_execution_allowed"] is False


def test_same_size_resigned_failure_is_rejected(native_tmp_path: Path) -> None:
    base = native_tmp_path / "exact-freeze"
    _copy_failure_boundary(base)
    path = (
        base
        / "v180r12r3r1_campaign_measurement_prelaunch_measurement_launch_failure.json"
    )
    document = json.loads(path.read_bytes())
    document["child_stderr"]["sha256"] = "0" * 64
    raw = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert len(raw) == frozen.EXPECTED_LAUNCH_FAILURE_BYTE_COUNT
    path.chmod(0o600)
    path.write_bytes(raw)
    path.chmod(0o400)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error,
        match="retained file bytes changed",
    ):
        frozen.load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1(base)


def test_resigned_semantic_stream_mutation_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = frozen.load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1()
    failure = value.launch_failure_document()
    failure["child_stderr"]["sha256"] = "0" * 64
    payload = dict(failure)
    del payload["launch_failure_id"]
    failure["launch_failure_id"] = hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
    raw = json.dumps(
        failure, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    monkeypatch.setattr(
        frozen, "EXPECTED_LAUNCH_FAILURE_ID", failure["launch_failure_id"]
    )
    with pytest.raises(
        frozen.FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error,
        match="retained child streams changed",
    ):
        frozen._require_failure_documents(value.launch_attempt_bytes, raw)


def test_resigned_root_cause_traceback_mutation_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = frozen.load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1()
    failure = value.launch_failure_document()
    stderr_raw = bytes.fromhex(failure["child_stderr"]["retained_prefix_hex"])
    original = b"external replay document byte join changed"
    replacement = b"external replay document byte join altered"
    assert len(original) == len(replacement)
    assert stderr_raw.count(original) == 2
    mutated_stderr = stderr_raw.replace(original, replacement)
    mutated_stderr_sha256 = hashlib.sha256(mutated_stderr).hexdigest()
    failure["child_stderr"]["retained_prefix_hex"] = mutated_stderr.hex()
    failure["child_stderr"]["sha256"] = mutated_stderr_sha256
    payload = dict(failure)
    del payload["launch_failure_id"]
    failure["launch_failure_id"] = hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
    raw = json.dumps(
        failure, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    monkeypatch.setattr(
        frozen, "EXPECTED_CHILD_STDERR_SHA256", mutated_stderr_sha256
    )
    monkeypatch.setattr(
        frozen, "EXPECTED_LAUNCH_FAILURE_ID", failure["launch_failure_id"]
    )
    with pytest.raises(
        frozen.FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error,
        match="retained child root-cause traceback changed",
    ):
        frozen._require_failure_documents(value.launch_attempt_bytes, raw)


def test_resigned_progress_mutation_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = frozen.load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1()
    failure = value.launch_failure_document()
    failure["progress_observations"]["output_root"] = {
        "presence": "REGULAR_FILE"
    }
    payload = dict(failure)
    del payload["launch_failure_id"]
    failure["launch_failure_id"] = hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
    raw = json.dumps(
        failure, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    monkeypatch.setattr(
        frozen, "EXPECTED_LAUNCH_FAILURE_ID", failure["launch_failure_id"]
    )
    with pytest.raises(
        frozen.FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error,
        match="retained launch progress observations changed",
    ):
        frozen._require_failure_documents(value.launch_attempt_bytes, raw)


def test_success_or_scientific_progress_coexistence_is_rejected(
    native_tmp_path: Path,
) -> None:
    base = native_tmp_path / "exact-freeze"
    _copy_failure_boundary(base)
    output = base / "v180r12r3r1_campaign_measurement"
    output.mkdir(mode=0o700)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error,
        match="forbidden V180r12r3r1 successor artifact exists",
    ):
        frozen.load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1(base)


def test_scientific_attempt_lock_coexistence_is_rejected(
    native_tmp_path: Path,
) -> None:
    base = native_tmp_path / "exact-freeze"
    _copy_failure_boundary(base)
    attempt = base / "v180r12r3r1_campaign_measurement_attempt.json"
    attempt.write_bytes(b"{}")
    attempt.chmod(0o400)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error,
        match="forbidden V180r12r3r1 successor artifact exists",
    ):
        frozen.load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1(base)


def test_extra_prelaunch_entry_is_bounded_and_rejected(
    native_tmp_path: Path,
) -> None:
    base = native_tmp_path / "exact-freeze"
    _copy_failure_boundary(base)
    extra = base / "v180r12r3r1_campaign_measurement_prelaunch/EXTRA"
    extra.write_bytes(b"")
    with pytest.raises(
        frozen.FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error,
        match="inventory exceeded its cap",
    ):
        frozen.load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1(base)


def test_foreign_frozen_failure_object_is_rejected() -> None:
    value = frozen.load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1()
    with pytest.raises(
        frozen.FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1Error,
        match="foreign",
    ):
        frozen.FrozenCampaignMeasurementPrelaunchFailureV180r12r3r1(
            _issuer=object(),
            launch_attempt_bytes=value.launch_attempt_bytes,
            launch_failure_bytes=value.launch_failure_bytes,
            launch_attempt_id=value.launch_attempt_id,
            launch_failure_id=value.launch_failure_id,
        )


def test_failure_freeze_has_no_execution_module_imports() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            imported.add((node.module or "").split(".", 1)[0])
    assert imported == {
        "dataclasses",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "stat",
        "typing",
    }
