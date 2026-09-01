from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    U002_SOURCE_COMMIT_V1,
    build_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    build_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]


def _load_script(filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename.replace(".", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bundle():
    gather = _load_script("gather_learned_resource_forecast_evidence_u003.py")
    old_protocol = build_ratified_learned_resource_forecast_protocol_v1(
        U002_SOURCE_COMMIT_V1
    )
    new_protocol = (
        build_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            "c" * 40
        )
    )
    old_manifest = gather._predecessor_prepare_module().build_launch_manifest_v1(
        old_protocol
    )
    new_manifest = gather._successor_prepare_module().build_launch_manifest_v1(
        new_protocol
    )
    return gather, old_protocol, new_protocol, old_manifest, new_manifest


def test_dual_worker_roster_keeps_u002_training_and_u003_evidence_separate(
    bundle,
) -> None:
    gather, _old_protocol, _new_protocol, old_manifest, new_manifest = bundle
    counts = [
        len(gather._worker_file_paths(old_manifest, new_manifest, index))
        for index in range(6)
    ]
    assert counts == [352, 352, 334, 334, 334, 334]
    for index in range(6):
        paths = gather._worker_file_paths(old_manifest, new_manifest, index)
        assert sum("u002-results" in str(path) for path in paths) == 96
        expected_evidence = 252 if index < 2 else 234
        assert sum("u003-results" in str(path) for path in paths) == expected_evidence
        assert sum("-training" in path.name for path in paths) == 2
        assert sum("-evidence" in path.name for path in paths) == 2


def test_tar_roster_has_both_roots_and_only_registered_status_and_logs(bundle) -> None:
    gather, _old_protocol, _new_protocol, old_manifest, new_manifest = bundle
    members = gather._transport_members(old_manifest, new_manifest, [2, 3])
    assert len(members) == len(set(members)) == 12
    assert sum("u002-results/worker-" in value for value in members) == 2
    assert sum("u003-results/worker-" in value for value in members) == 2
    assert sum("u002-status/worker-" in value for value in members) == 2
    assert sum("u003-status/worker-" in value for value in members) == 2
    assert sum("u002-logs/worker-" in value for value in members) == 2
    assert sum("u003-logs/worker-" in value for value in members) == 2


def _receipt(bundle) -> dict:
    gather, old_protocol, new_protocol, old_manifest, new_manifest = bundle
    common = gather._common_root(old_manifest, new_manifest)
    rows = []
    for host in gather._host_workers(new_manifest):
        files = [
            {
                "relative_path": path.resolve().relative_to(common).as_posix(),
                "size_bytes": 1,
            }
            for index in host["workers"]
            for path in gather._worker_file_paths(old_manifest, new_manifest, index)
        ]
        rows.append(
            {
                "host_alias": host["host_alias"],
                "expected_hostname": host["expected_hostname"],
                "actual_hostname": host["expected_hostname"],
                "workers": host["workers"],
                "files": files,
                "job_reexecution": False,
                "predecessor_training_artifacts_relabelled": False,
                "failed_u002_evidence_dispatch_used": False,
            }
        )
    return {
        "schema": gather.SCHEMA_V1,
        "predecessor_protocol_id": old_protocol["protocol_id"],
        "predecessor_source_commit": old_protocol["source_commit"],
        "predecessor_pilot_execution_identity": old_protocol[
            "pilot_execution_identity"
        ],
        "successor_protocol_id": new_protocol["protocol_id"],
        "successor_source_commit": new_protocol["source_commit"],
        "successor_pilot_execution_identity": new_protocol[
            "pilot_execution_identity"
        ],
        "central_expected_hostname": new_manifest["central_analysis"][
            "expected_hostname"
        ],
        "remote_workers": [2, 3, 4, 5],
        "transport_method": "LOCAL_CONTROLLER_SSH_DUAL_TREE_TAR_TO_SSH_GPU2_TAR",
        "job_reexecution": False,
        "predecessor_training_artifacts_relabelled": False,
        "failed_u002_evidence_dispatch_used": False,
        "source_hosts": rows,
    }


def test_receipt_binds_both_authorities_and_rejects_failed_u002_evidence(bundle) -> None:
    gather, old_protocol, new_protocol, old_manifest, new_manifest = bundle
    receipt = _receipt(bundle)
    assert gather._validate_receipt_structure(
        receipt, old_protocol, new_protocol, old_manifest, new_manifest
    ) == receipt["source_hosts"]
    tampered = json.loads(json.dumps(receipt))
    tampered["failed_u002_evidence_dispatch_used"] = True
    with pytest.raises(
        gather.LearnedResourceForecastGatherU003V1Error,
        match="dual-authority contract",
    ):
        gather._validate_receipt_structure(
            tampered, old_protocol, new_protocol, old_manifest, new_manifest
        )


def test_gather_ssh_inspection_explicitly_disables_existing_mux(
    bundle, monkeypatch: pytest.MonkeyPatch
) -> None:
    gather, _old_protocol, _new_protocol, _old_manifest, _new_manifest = bundle
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        return SimpleNamespace(returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(gather.subprocess, "run", fake_run)
    assert gather._ssh_source_inspector(
        "jtl110gpu",
        {
            "source_pythonpath": "/source/src",
            "python": "/python",
            "predecessor_protocol": "/old/protocol.json",
            "predecessor_manifest": "/old/manifest.json",
            "protocol": "/new/protocol.json",
            "manifest": "/new/manifest.json",
            "workers": [2, 3],
        },
    ) == {}
    command = seen["command"]
    assert command[:2] == ["ssh", "-o"]
    assert "ControlMaster=no" in command
    assert "ControlPath=none" in command
    assert command.count("jtl110gpu") == 1


def test_marker_records_transport_not_execution_or_relabelling(bundle) -> None:
    gather, old_protocol, new_protocol, _old_manifest, new_manifest = bundle
    marker = gather._marker(old_protocol, new_protocol, new_manifest)
    assert marker["predecessor_protocol_id"] == old_protocol["protocol_id"]
    assert marker["successor_protocol_id"] == new_protocol["protocol_id"]
    assert marker["transport_is_not_job_execution"] is True
    assert marker["predecessor_training_artifacts_relabelled"] is False
    assert marker["failed_u002_evidence_dispatch_used"] is False
