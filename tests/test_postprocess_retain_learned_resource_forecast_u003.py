from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    U002_SOURCE_COMMIT_V1,
    build_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    build_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
POSTPROCESS = (
    REPOSITORY / "scripts/postprocess_retain_learned_resource_forecast_u003.py"
)
U002_PREPARE = REPOSITORY / "scripts/prepare_learned_resource_forecast_campaign_u002.py"
U003_PREPARE = (
    REPOSITORY
    / "scripts/prepare_learned_resource_forecast_evidence_successor_u003.py"
)
U003_SOURCE_COMMIT = "a" * 40


@pytest.fixture
def linux_tmp_path(request) -> Path:
    path = Path(tempfile.mkdtemp(prefix="acfqp-u003-postprocess-", dir="/tmp"))
    request.addfinalizer(lambda: shutil.rmtree(path, ignore_errors=True))
    return path


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical_json_bytes(row) + b"\n" for row in rows))


def _worker_status_rows(worker: int, phase: str, jobs: list[dict]) -> list[dict]:
    rows = [{"event": "WORKER_STARTED", "phase": phase, "worker": worker}]
    for ordinal, job in enumerate(jobs):
        rows.extend(
            (
                {
                    "event": "JOB_STARTED",
                    "phase": phase,
                    "worker": worker,
                    "job_ordinal": ordinal,
                    "execution_id": job["execution_id"],
                    "preexecution_identity_check_only": False,
                },
                {
                    "event": "JOB_COMPLETED",
                    "phase": phase,
                    "worker": worker,
                    "job_ordinal": ordinal,
                    "execution_id": job["execution_id"],
                    "completed_job_count": ordinal + 1,
                    "expected_job_count": len(jobs),
                },
            )
        )
    rows.append(
        {
            "event": "WORKER_COMPLETED",
            "phase": phase,
            "worker": worker,
            "completed_job_count": len(jobs),
        }
    )
    return rows


def _dispatch_rows(manifest: dict, phase: str, *, successor: bool) -> list[dict]:
    fixed = manifest["fixed_paths"]
    first = {
        "event": "GLOBAL_PRECHECK_COMPLETED",
        "phase": phase,
        "prechecked_worker_count": 6,
        "filesystem_mutation_before_precheck_completed": False,
    }
    second = {"event": "DISPATCH_STARTED", "phase": phase}
    if successor:
        first["parent_training_closure_all_passed"] = True
        second["u002_failed_evidence_dispatch_eligible"] = False
    rows = [first, second]
    for worker in manifest["workers"]:
        status_name = worker[
            "player_evidence_status_stream"
            if successor
            else "policy_training_status_stream"
        ]
        row = {
            "event": "WORKER_DISPATCHED",
            "phase": phase,
            "worker": worker["worker"],
            "host_alias": worker["host_alias"],
            "expected_hostname": worker["expected_hostname"],
            "device": worker["device"],
            "remote_pid": 10_000 + worker["worker"],
            "worker_results_root": str(
                Path(fixed["results_root"]) / f"worker-{worker['worker']}"
            ),
            "worker_status_stream": str(Path(fixed["status_root"]) / status_name),
            "worker_log": str(
                Path(fixed["log_root"])
                / f"worker-{worker['worker']}-{phase}.log"
            ),
        }
        if successor:
            row["predecessor_snapshot_root"] = worker["predecessor_snapshot_root"]
        rows.append(row)
    rows.append(
        {
            "event": "DISPATCH_COMPLETED",
            "phase": phase,
            "dispatched_worker_count": 6,
            "worker_execution_completed": False,
        }
    )
    return rows


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    subject = _load(POSTPROCESS, "learned_resource_postprocess_u003_subject")
    old_prepare = _load(U002_PREPARE, "learned_resource_postprocess_u003_old_prepare")
    new_prepare = _load(U003_PREPARE, "learned_resource_postprocess_u003_new_prepare")
    predecessor_protocol = build_ratified_learned_resource_forecast_protocol_v1(
        U002_SOURCE_COMMIT_V1
    )
    successor_protocol = (
        build_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            U003_SOURCE_COMMIT
        )
    )
    predecessor_manifest = deepcopy(
        old_prepare.build_launch_manifest_v1(predecessor_protocol)
    )
    successor_manifest = deepcopy(
        new_prepare.build_launch_manifest_v1(successor_protocol)
    )

    launch = tmp_path / "u003-launch"
    old_launch = tmp_path / "u002-launch"
    old_results = tmp_path / "u002-results"
    old_status = tmp_path / "u002-status"
    old_logs = tmp_path / "u002-logs"
    new_results = tmp_path / "u003-results"
    new_status = tmp_path / "u003-status"
    new_logs = tmp_path / "u003-logs"
    analysis = tmp_path / "u003-analysis"
    retained = tmp_path / "u003-retained"
    old_fixed = predecessor_manifest["fixed_paths"]
    old_fixed.update(
        {
            "results_root": str(old_results),
            "status_root": str(old_status),
            "log_root": str(old_logs),
            "protocol": str(old_launch / "protocol.json"),
            "manifest": str(old_launch / "launch-manifest.json"),
            "training_dispatch_status": str(old_launch / "training-dispatch.jsonl"),
            "evidence_dispatch_status": str(old_launch / "evidence-dispatch.jsonl"),
        }
    )
    new_fixed = successor_manifest["fixed_paths"]
    new_fixed.update(
        {
            "source_checkout": str(REPOSITORY),
            "launch_root": str(launch),
            "protocol": str(launch / "protocol.json"),
            "manifest": str(launch / "launch-manifest.json"),
            "history_scan_receipt": str(launch / "history-scan-receipt.json"),
            "gather_transport_marker": str(launch / "gather-transport-marker.json"),
            "gather_receipt": str(launch / "gather-receipt.json"),
            "results_root": str(new_results),
            "status_root": str(new_status),
            "log_root": str(new_logs),
            "analysis_root": str(analysis),
            "retained_root": str(retained),
            "evidence_dispatch_status": str(launch / "evidence-dispatch.jsonl"),
            "postprocess_status": str(launch / "postprocess-status.jsonl"),
            "predecessor_protocol": old_fixed["protocol"],
            "predecessor_manifest": old_fixed["manifest"],
            "predecessor_training_dispatch_status": old_fixed[
                "training_dispatch_status"
            ],
            "ineligible_predecessor_evidence_dispatch_status": old_fixed[
                "evidence_dispatch_status"
            ],
            "predecessor_results_root": str(old_results),
            "predecessor_status_root": str(old_status),
            "predecessor_log_root": str(old_logs),
        }
    )
    for index, worker in enumerate(successor_manifest["workers"]):
        worker["predecessor_snapshot_root"] = str(old_results / f"worker-{index}")
        worker["successor_evidence_output_root"] = str(
            new_results / f"worker-{index}"
        )

    _write_json(Path(old_fixed["protocol"]), predecessor_protocol)
    _write_json(Path(old_fixed["manifest"]), predecessor_manifest)
    _write_json(Path(new_fixed["protocol"]), successor_protocol)
    _write_json(Path(new_fixed["manifest"]), successor_manifest)
    _write_json(Path(new_fixed["history_scan_receipt"]), {"fixture": True})
    _write_json(Path(new_fixed["gather_transport_marker"]), {"fixture": True})
    _write_json(Path(new_fixed["gather_receipt"]), {"fixture": True})
    old_results.mkdir()
    old_status.mkdir()
    old_logs.mkdir()
    new_results.mkdir()
    new_status.mkdir()
    new_logs.mkdir()
    for index in range(6):
        old_worker = predecessor_manifest["workers"][index]
        new_worker = successor_manifest["workers"][index]
        old_root = old_results / f"worker-{index}"
        new_root = new_results / f"worker-{index}"
        old_root.mkdir()
        new_root.mkdir()
        for filename, category in subject._predecessor_artifact_map(old_worker).items():
            if category.endswith("training_json"):
                _write_json(old_root / filename, {})
            else:
                (old_root / filename).write_bytes(b"model")
        for filename, category in subject._successor_artifact_map(new_worker).items():
            if category.endswith("npz"):
                (new_root / filename).write_bytes(b"npz")
            else:
                _write_json(new_root / filename, {})
        old_status_path = old_status / old_worker["policy_training_status_stream"]
        new_status_path = new_status / new_worker["player_evidence_status_stream"]
        _write_jsonl(
            old_status_path,
            _worker_status_rows(index, "training", old_worker["policy_training_jobs"]),
        )
        _write_jsonl(
            new_status_path,
            _worker_status_rows(index, "evidence", new_worker["player_evidence_jobs"]),
        )
        _write_jsonl(
            old_logs / f"worker-{index}-training.log",
            [
                {
                    "success": True,
                    "phase": "training",
                    "worker": index,
                    "completed_job_count": 24,
                    "results_root": str(old_root),
                }
            ],
        )
        _write_jsonl(
            new_logs / f"worker-{index}-evidence.log",
            [
                {
                    "success": True,
                    "phase": "evidence",
                    "worker": index,
                    "completed_job_count": 72,
                    "results_root": str(new_root),
                }
            ],
        )
    _write_jsonl(
        Path(old_fixed["training_dispatch_status"]),
        _dispatch_rows(predecessor_manifest, "training", successor=False),
    )
    _write_jsonl(
        Path(new_fixed["evidence_dispatch_status"]),
        _dispatch_rows(successor_manifest, "evidence", successor=True),
    )
    _write_jsonl(
        Path(new_fixed["ineligible_predecessor_evidence_dispatch_status"]),
        [
            {"event": "GLOBAL_PRECHECK_COMPLETED", "phase": "evidence"},
            {"event": "DISPATCH_STARTED", "phase": "evidence"},
            {
                "event": "WORKER_DISPATCH_FAILED",
                "phase": "evidence",
                "worker": 0,
            },
            {
                "event": "DISPATCH_FAILED",
                "phase": "evidence",
                "dispatched_worker_count": 0,
            },
        ],
    )

    monkeypatch.setattr(
        subject,
        "validate_ratified_learned_resource_forecast_protocol_v1",
        lambda value: value,
    )
    monkeypatch.setattr(
        subject,
        "validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1",
        lambda value: value,
    )
    monkeypatch.setattr(
        subject,
        "_load_predecessor_prepare_module",
        lambda: SimpleNamespace(
            build_launch_manifest_v1=lambda _protocol: predecessor_manifest
        ),
    )
    monkeypatch.setattr(
        subject,
        "_load_successor_prepare_module",
        lambda: SimpleNamespace(build_launch_manifest_v1=lambda _protocol: successor_manifest),
    )
    monkeypatch.setattr(
        subject,
        "_load_history_scan_module",
        lambda: SimpleNamespace(
            validate_history_scan_receipt_v1=lambda receipt, protocol, manifest: receipt
        ),
    )
    def validate_gather(
        receipt, old_protocol, new_protocol, old_manifest, new_manifest
    ):
        assert old_protocol == predecessor_protocol
        assert new_protocol == successor_protocol
        assert old_manifest == predecessor_manifest
        assert new_manifest == successor_manifest
        return receipt

    monkeypatch.setattr(
        subject,
        "_load_gather_module",
        lambda: SimpleNamespace(validate_gather_receipt_v1=validate_gather),
    )
    monkeypatch.setattr(
        subject,
        "bound_clean_source_commit_v1",
        lambda _repository: U003_SOURCE_COMMIT,
    )
    monkeypatch.setattr(
        subject.socket,
        "gethostname",
        lambda: successor_manifest["central_analysis"]["expected_hostname"],
    )
    args = SimpleNamespace(
        predecessor_protocol=Path(new_fixed["predecessor_protocol"]),
        predecessor_manifest=Path(new_fixed["predecessor_manifest"]),
        protocol=Path(new_fixed["protocol"]),
        manifest=Path(new_fixed["manifest"]),
        history_scan_receipt=Path(new_fixed["history_scan_receipt"]),
        gather_receipt=Path(new_fixed["gather_receipt"]),
        analysis_device=successor_manifest["central_analysis"]["device"],
        verifier_device=successor_manifest["central_analysis"]["device"],
    )
    return subject, predecessor_protocol, successor_protocol, predecessor_manifest, successor_manifest, args


def _mock_runners(manifest: dict, calls: list[str]):
    analysis_root = Path(manifest["fixed_paths"]["analysis_root"])
    old_results = Path(manifest["fixed_paths"]["predecessor_results_root"])
    new_results = Path(manifest["fixed_paths"]["results_root"])

    def analysis_runner(args: SimpleNamespace) -> dict:
        calls.append(args.operation)
        if args.operation == "fit-encoders":
            assert all(str(path).startswith(str(new_results)) for path in args.trajectory_dir)
            for name in (
                "aligned-resource-forecast.encoder.pt",
                "player-shuffled-resource-forecast.encoder.pt",
                "aligned-resource-forecast.receipt.json",
                "player-shuffled-resource-forecast.receipt.json",
            ):
                (analysis_root / name).write_bytes(b"fit")
        elif args.operation == "encode-probes":
            assert all(str(path).startswith(str(new_results)) for path in args.probe_dir)
            (analysis_root / "probe-representation-matrices.npz").write_bytes(b"matrix")
            _write_json(analysis_root / "probe-representation-matrices.metadata.json", {})
        elif args.operation == "evaluate":
            assert all(
                str(path).startswith(str(old_results))
                for path in args.predecessor_training_result_dir
            )
            assert all(
                str(path).startswith(str(new_results))
                for path in args.worker_result_dir
            )
            _write_json(
                analysis_root / "pilot-result.json",
                {"PROVISIONAL_DESIGN_SIGNAL_GATE": "PASS"},
            )
        return {"success": True}

    def verifier_runner(args: SimpleNamespace) -> dict:
        calls.append("independent-verifier")
        assert all(
            str(path).startswith(str(old_results))
            for path in args.predecessor_training_result_dir
        )
        assert all(
            str(path).startswith(str(new_results)) for path in args.worker_result_dir
        )
        _write_json(analysis_root / "independent-verification.json", {"valid": True})
        return {"success": True, "valid": True}

    return analysis_runner, verifier_runner


def test_dual_authority_postprocess_orders_lanes_and_retains_exact_provenance(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _old_protocol, _new_protocol, _old_manifest, new_manifest, args = _fixture(
        linux_tmp_path, monkeypatch
    )
    calls: list[str] = []
    analysis_runner, verifier_runner = _mock_runners(new_manifest, calls)

    summary = subject._run(
        args,
        analysis_runner=analysis_runner,
        verifier_runner=verifier_runner,
        runtime_validator=lambda *_args: None,
    )

    assert calls == [
        "fit-encoders",
        "encode-probes",
        "evaluate",
        "independent-verifier",
    ]
    assert summary["success"] is True
    assert summary["PROVISIONAL_DESIGN_SIGNAL_GATE"] == "PASS"
    assert summary["independent_verification"] is True
    assert summary["failed_u002_evidence_dispatch_used"] is False
    assert summary["retained_artifact_count_excluding_inventory"] == 2059
    assert summary["physical_file_count_including_inventory"] == 2060
    retained = Path(new_manifest["fixed_paths"]["retained_root"])
    inventory = json.loads(
        (retained / "retention-inventory.json").read_text(encoding="utf-8")
    )
    assert inventory["category_counts"] == subject.EXPECTED_CATEGORY_COUNTS_V1
    assert inventory["provenance_counts"] == subject.EXPECTED_PROVENANCE_COUNTS_V1
    assert inventory["failed_u002_evidence_dispatch_used"] is False
    assert (retained / "predecessor-u002/training/workers/worker-0").is_dir()
    assert (retained / "successor-u003/evidence/workers/worker-0").is_dir()
    failed = [
        row
        for row in inventory["entries"]
        if row["category"] == "ineligible_predecessor_failed_evidence_dispatch"
    ]
    assert len(failed) == 1
    assert failed[0]["provenance"] == subject.PROVENANCE_FAILED_U002_EVIDENCE_V1


def test_failed_u002_dispatch_is_history_only_and_must_show_zero_dispatched_workers(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _old_protocol, _new_protocol, _old_manifest, new_manifest, args = _fixture(
        linux_tmp_path, monkeypatch
    )
    path = Path(
        new_manifest["fixed_paths"]["ineligible_predecessor_evidence_dispatch_status"]
    )
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[-1]["dispatched_worker_count"] = 1
    _write_jsonl(path, rows)
    calls: list[str] = []

    with pytest.raises(
        subject.LearnedResourceForecastPostprocessU003V1Error,
        match="zero-worker failure history",
    ):
        subject._run(
            args,
            analysis_runner=lambda stage: calls.append(stage.operation),
            runtime_validator=lambda *_args: None,
        )
    assert calls == []
    assert not Path(new_manifest["fixed_paths"]["analysis_root"]).exists()
    assert not Path(new_manifest["fixed_paths"]["postprocess_status"]).exists()


def test_parent_artifact_in_successor_root_fails_before_analysis(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _old_protocol, _new_protocol, old_manifest, new_manifest, args = _fixture(
        linux_tmp_path, monkeypatch
    )
    parent_name = old_manifest["workers"][0]["policy_training_jobs"][0][
        "result_filename"
    ]
    foreign = Path(new_manifest["fixed_paths"]["results_root"]) / "worker-0" / parent_name
    foreign.write_text("{}", encoding="utf-8")
    calls: list[str] = []

    with pytest.raises(
        subject.LearnedResourceForecastPostprocessU003V1Error,
        match="missing, duplicate, foreign",
    ):
        subject._run(
            args,
            analysis_runner=lambda stage: calls.append(stage.operation),
            runtime_validator=lambda *_args: None,
        )
    assert calls == []
    assert not Path(new_manifest["fixed_paths"]["analysis_root"]).exists()
