from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from scripts import materialize_v180r12r4_campaign_measurement_prelaunch as materializer


def _inputs(raw: bytes) -> tuple[dict[str, tuple[str, str]], dict[str, bytes]]:
    blob = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
    ).hexdigest()
    return {"sample.py": ("100644", blob)}, {"sample.py": raw}


def test_source_mode_0644_records_complete_conforming_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = b"VALUE = 1\n"
    source = tmp_path / "sample.py"
    source.write_bytes(raw)
    source.chmod(0o644)
    monkeypatch.setattr(
        materializer, "SOURCE_CLOSURE_REQUIRED_ROOTS", ("sample.py",)
    )
    tree, blobs = _inputs(raw)

    diagnostic = materializer._working_tree_source_conformance_v180r12r4(
        tmp_path, tree, blobs
    )

    assert diagnostic["full_source_conformance"] is True
    assert diagnostic["mismatch_count"] == 0
    assert diagnostic["unit_ownership_evaluated"] is False
    assert diagnostic["cause"] is None
    snapshot = diagnostic["snapshots"][0]
    assert snapshot["conformant"] is True
    assert snapshot["mismatch_fields"] == []
    assert snapshot["expected"]["mode"] == 0o644
    assert snapshot["observed_before"] == snapshot["observed_after"]
    assert set(snapshot["observed_before"]) == {
        "file_type",
        "st_dev",
        "st_ino",
        "st_mode",
        "mode",
        "st_nlink",
        "st_uid",
        "st_gid",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    }


def test_source_mode_0664_is_rejected_before_formal_output_with_typed_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = b"VALUE = 1\n"
    source = tmp_path / "sample.py"
    source.write_bytes(raw)
    source.chmod(0o664)
    monkeypatch.setattr(
        materializer, "SOURCE_CLOSURE_REQUIRED_ROOTS", ("sample.py",)
    )
    tree, blobs = _inputs(raw)

    with pytest.raises(
        materializer.V180r12r4WorkingTreeSourceConformanceError
    ) as caught:
        materializer._working_tree_source_conformance_v180r12r4(
            tmp_path, tree, blobs
        )

    diagnostic = caught.value.source_conformance_diagnostic
    assert diagnostic["full_source_conformance"] is False
    assert diagnostic["mismatch_count"] == 1
    assert diagnostic["unit_ownership_evaluated"] is False
    assert diagnostic["snapshots"][0]["mismatch_fields"] == ["mode"]
    assert diagnostic["per_field_mismatches"] == [
        {
            "relative_path": "sample.py",
            "field": "mode",
            "expected": 0o644,
            "observed_before": 0o664,
            "observed_after": 0o664,
        }
    ]
    assert not (tmp_path / ".tmp").exists()

    failure, _raw = materializer.build_materialization_failure_v180r12r4(
        repository_root=tmp_path,
        external_root_path=tmp_path / "external.json",
        expected_external_root_sha256="0" * 64,
        failed_phase="WORKING_TREE_SOURCE_CONFORMANCE",
        error=caught.value,
    )
    assert failure["source_conformance_diagnostic"] == diagnostic
    assert failure["campaign_actual_measurement"] is False
    assert failure["counter_records_issued"] is False
    assert failure["work_vectors_issued"] is False
    assert failure["comparison_vectors_issued"] is False
    assert failure["official_execution_allowed"] is False
