from __future__ import annotations

import json
from pathlib import Path

from scripts import launch_v42_activation_successor_or_formal as launcher
from scripts import run_v42_activation_successor_finalizer as finalizer


def test_controller_tcb_is_sorted_complete_local_import_closure() -> None:
    assert launcher.TCB_PATHS == tuple(sorted(launcher.TCB_PATHS))
    assert len(launcher.TCB_PATHS) == len(set(launcher.TCB_PATHS)) == 27
    assert {
        "src/acfqp/artifacts.py",
        "src/acfqp/build_coverage.py",
        "src/acfqp/core.py",
        "src/acfqp/enumeration.py",
    } <= set(launcher.TCB_PATHS)


def test_successor_main_writes_one_canonical_result_and_returns_zero(
    tmp_path: Path, monkeypatch, capfd,
) -> None:
    predecessor = tmp_path / ".acfqp-v42-local-activation-evidence-old"
    evidence = tmp_path / (finalizer.SUCCESSOR_ROOT_PREFIX + "e" * 64)
    manifest = {"schema": "test.source"}
    result = {
        "schema": "test.successor.result",
        "activation_successor_final_evidence_index_id": "f" * 64,
    }
    monkeypatch.setattr(
        launcher,
        "build_live_controller_source_manifest_v42r2",
        lambda **_: manifest,
    )
    monkeypatch.setattr(
        finalizer,
        "orchestrate_activation_successor_v42r2",
        lambda **_: result,
    )
    assert launcher.main(
        [
            "successor",
            "--predecessor-activation-evidence-root",
            str(predecessor),
            "--successor-evidence-root",
            str(evidence),
            "--expected-legacy-activation-plan-id",
            "a" * 64,
            "--expected-controller-commit",
            "b" * 40,
            "--expected-controller-tree",
            "c" * 40,
        ]
    ) == 0
    stdout, stderr = capfd.readouterr()
    assert stderr == ""
    assert stdout.encode() == (
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        + b"\n"
    )


def test_formal_parser_requires_source_commit_and_tree() -> None:
    parser = launcher._parser()  # noqa: SLF001
    arguments = parser.parse_args(
        [
            "formal",
            "--predecessor-activation-evidence-root",
            "/tmp/predecessor",
            "--successor-evidence-root",
            "/tmp/successor",
            "--expected-successor-final-evidence-index-id",
            "d" * 64,
            "--expected-controller-commit",
            "e" * 40,
            "--expected-controller-tree",
            "f" * 40,
            "--probe-host-epoch",
        ]
    )
    assert arguments.expected_controller_commit == "e" * 40
    assert arguments.expected_controller_tree == "f" * 40
