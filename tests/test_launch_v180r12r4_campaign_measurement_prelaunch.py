from __future__ import annotations

import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from functools import lru_cache
import shutil
import stat
import tempfile
import time
from types import SimpleNamespace

import pytest

from acfqp import construction_k7_campaign_measurement_protocol_v180r12r4 as protocol
from acfqp import construction_k7_campaign_measurement_finalizer_v180r12r4 as finalizer
from tests import test_construction_k7_campaign_measurement_finalizer_v180r12r4 as finalizer_fixture

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/launch_v180r12r4_campaign_measurement_prelaunch.py"
SPEC = importlib.util.spec_from_file_location("v180r12r4_prelaunch_launcher", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)
ZERO_ID = "0" * 64


@pytest.fixture
def tmp_path() -> Path:
    """Use native Linux mode semantics for O_EXCL/0400 attack tests."""

    path = Path(tempfile.mkdtemp(prefix="v180r12r4-launcher-", dir="/tmp"))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _write_0400(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(0o400)


def _resigned_terminal_bytes(
    terminal_raw: bytes, updates: dict[str, object]
) -> bytes:
    terminal = json.loads(terminal_raw)
    terminal.update(updates)
    terminal.pop("campaign_measurement_terminal_id")
    projected = terminal["output_bytes_fixed_point"]
    for _iteration in range(32):
        terminal["output_bytes_fixed_point"] = projected
        identity = hashlib.sha256(
            launcher.TERMINAL_DOMAIN.encode("utf-8")
            + b"\x00"
            + _canonical(terminal)
        ).hexdigest()
        candidate = {**terminal, "campaign_measurement_terminal_id": identity}
        raw = _canonical(candidate)
        if len(raw) == projected:
            return raw
        projected = len(raw)
    raise AssertionError("test terminal byte-count fixed point did not converge")


@lru_cache(maxsize=1)
def _measurement_success_bytes() -> tuple[bytes, tuple[tuple[str, bytes], ...]]:
    result = finalizer_fixture._finalize(finalizer_fixture._closed_inputs())
    return result.canonical_bytes, tuple(result.success_artifact_bytes.items())


def _write_measurement_success(repository: Path) -> None:
    terminal_raw, artifact_rows = _measurement_success_bytes()
    manifest_raw = (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
    materialization = json.loads(
        (repository / launcher.MATERIALIZATION_TERMINAL_RELATIVE_PATH).read_bytes()
    )
    launch_attempt = json.loads(
        (repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH).read_bytes()
    )
    terminal_raw = _resigned_terminal_bytes(
        terminal_raw,
        {
            "prelaunch_materialization_terminal_id": materialization[
                "materialization_terminal_id"
            ],
            "prelaunch_launch_manifest_sha256": hashlib.sha256(
                manifest_raw
            ).hexdigest(),
            "prelaunch_launch_rule_id": launcher.LAUNCH_RULE_ID,
            "measurement_launch_attempt_id": launch_attempt["launch_attempt_id"],
        },
    )
    relative_by_key = {
        "evidence_inventory": launcher.EVIDENCE_INVENTORY_RELATIVE_PATH,
        "execution_closure": launcher.EXECUTION_CLOSURE_RELATIVE_PATH,
        "os_receipt": launcher.OS_RECEIPT_RELATIVE_PATH,
        "ledger_closure": launcher.LEDGER_CLOSURE_RELATIVE_PATH,
    }
    assert tuple(key for key, _raw in artifact_rows) == launcher.SUCCESS_ARTIFACT_ORDER
    for key, raw in artifact_rows:
        _write_0400(repository / relative_by_key[key], raw)
    _write_0400(repository / launcher.TERMINAL_RELATIVE_PATH, terminal_raw)
    _write_pre_attempt_host_conformance(repository)


def _write_pre_attempt_host_conformance(
    repository: Path,
    *,
    observed_parent_updates: dict[str, object] | None = None,
    observed_socket_updates: dict[str, object] | None = None,
) -> bytes:
    manifest = json.loads(
        (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
    )
    frozen = manifest["frozen_authorization_context"]
    expected_parent = frozen["cgroup_parent_fact"]
    expected_runtime = frozen["runtime_capability_fact"]
    observed_parent = dict(expected_parent)
    observed_parent["self_membership"] = (
        "0::/app.slice/"
        + launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS["measurement"][2]
    )
    if observed_parent_updates is not None:
        observed_parent.update(observed_parent_updates)
    expected_socket = dict(launcher.SOCKET_BUFFER_CAPABILITY_EXPECTED)
    observed_socket = dict(expected_socket)
    if observed_socket_updates is not None:
        observed_socket.update(observed_socket_updates)
    document = {
        "schema": launcher.PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA,
        "phase": "PRE_CAMPAIGN_ATTEMPT_HOST_CONFORMANCE",
        "campaign_attempt_id": frozen["campaign_attempt_id"],
        "expected": {
            "cgroup_parent_fact": expected_parent,
            "runtime_capability_fact": expected_runtime,
            "socket_buffer_capability": expected_socket,
        },
        "observed": {
            "cgroup_parent_fact": observed_parent,
            "runtime_capability_fact": expected_runtime,
            "socket_buffer_capability": observed_socket,
        },
        "cgroup_parent_compared_fields": [
            field
            for field in launcher.CGROUP_PARENT_FACT_FIELD_ORDER
            if field != "self_membership"
        ],
        "cgroup_parent_excluded_fields": ["self_membership"],
        "runtime_capability_compared_fields": list(
            launcher.RUNTIME_CAPABILITY_FACT_FIELD_ORDER
        ),
        "socket_buffer_capability_exact_fields": list(
            launcher.SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS
        ),
        "socket_buffer_capability_at_least_fields": list(
            launcher.SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS
        ),
        "mismatch_rows": [],
        "mismatch_count": 0,
        "cause": None,
        "full_host_conformance": True,
        "working_tree_source_conformance_joined": False,
        "production_unit_ownership_t1_joined": False,
        "campaign_event_or_counter_record_issued": False,
        "campaign_attempt_created": False,
    }
    raw = _canonical(document)
    _write_0400(
        repository / launcher.PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH,
        raw,
    )
    return raw


def _stream(raw: bytes) -> dict[str, object]:
    observation = launcher._StreamObservation()
    observation.add(raw)
    return observation.document()


def _write_inner_launch_receipt(
    repository: Path, digest: str, target: str
) -> tuple[dict[str, object], dict[str, object]]:
    materialization, materialization_raw = launcher._load_materialization(
        repository, digest
    )
    manifest_raw = (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
    invocation = launcher._production_systemd_service_invocation(
        repository, digest, target
    )
    child_argv = [
        *launcher.ISOLATED_ARGV_PREFIX,
        str(repository / launcher.BOOTSTRAP_RELATIVE_PATH),
        target,
        str(repository),
        str(repository / launcher.PRELAUNCH_ROOT_RELATIVE_PATH),
        str(repository / launcher.MANIFEST_RELATIVE_PATH),
    ]
    attempt, attempt_raw = launcher._attempt_document(
        target=target,
        repository_root=repository,
        materialization=materialization,
        materialization_raw=materialization_raw,
        manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
        child_argv=child_argv,
        production_systemd_service_invocation=invocation,
    )
    paths = launcher._state_paths(repository, target)
    _write_0400(paths["attempt"], attempt_raw)
    frozen = json.loads(manifest_raw)["frozen_authorization_context"]
    placement_t1 = None
    if target == "measurement":
        _write_measurement_success(repository)
        descriptors, placement_t1 = (
            launcher._prepare_and_observe_production_runtime_placement_t1(
                target="measurement", frozen_context=frozen
            )
        )
        for descriptor in descriptors:
            os.close(descriptor)
    deadlines = launcher._freeze_launch_deadlines_v180r12r4()
    cgroup_rows = (
        _successful_measurement_cgroup_observations(
            frozen["campaign_attempt_id"]
        )
        if target == "measurement"
        else launcher._initial_measurement_cgroup_observations(
            target, frozen["campaign_attempt_id"]
        )
    )
    receipt, receipt_raw = launcher._terminal_document(
        schema=launcher.LAUNCH_RECEIPT_SCHEMA,
        id_key="launch_receipt_id",
        target=target,
        attempt=attempt,
        return_code=0,
        timed_out=False,
        stdout=launcher._empty_stream_document(),
        stderr=launcher._empty_stream_document(),
        progress=launcher._progress_observations(paths),
        error=None,
        launch_deadlines=deadlines,
        measurement_cgroup_cleanup_observations=cgroup_rows,
        production_systemd_service_invocation=invocation,
        production_runtime_placement_t1=placement_t1,
    )
    _write_0400(paths["receipt"], receipt_raw)
    return attempt, receipt


def _fact(relative_path: str, raw: bytes) -> dict[str, object]:
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _git_fact(relative_path: str, raw: bytes, blob: str) -> dict[str, object]:
    return {
        **_fact(relative_path, raw),
        "git_mode": "100644",
        "git_blob_id": blob,
    }


def _closure(facts: list[dict[str, object]]) -> dict[str, object]:
    return {
        "facts": facts,
        "file_count": len(facts),
        "total_byte_count": sum(int(row["byte_count"]) for row in facts),
        "facts_sha256": hashlib.sha256(_canonical(facts)).hexdigest(),
    }


def _working_tree_source_conformance(
    rows: list[tuple[dict[str, object], bytes]],
) -> dict[str, object]:
    snapshots = []
    for index, (fact, physical_raw) in enumerate(rows):
        relative = str(fact["relative_path"])
        binding_kind = str(
            fact.get("binding_kind", "EXACT_C_PRE_GIT_BLOB")
        )
        effective_raw = (
            b"EXPECTED_AUTHORIZATION_ID = 0\n"
            if binding_kind == launcher.NORMALIZED_WRAPPER_BINDING_KIND
            else physical_raw
        )
        assert len(effective_raw) == fact["byte_count"]
        assert hashlib.sha256(effective_raw).hexdigest() == fact["sha256"]
        effective_blob = hashlib.sha1(
            b"blob "
            + str(len(effective_raw)).encode("ascii")
            + b"\x00"
            + effective_raw
        ).hexdigest()
        physical_blob = hashlib.sha1(
            b"blob "
            + str(len(physical_raw)).encode("ascii")
            + b"\x00"
            + physical_raw
        ).hexdigest()
        observed_stat = {
            "file_type": "REGULAR_FILE",
            "st_dev": 1,
            "st_ino": index + 1,
            "st_mode": stat.S_IFREG | 0o644,
            "mode": 0o644,
            "st_nlink": 1,
            "st_uid": os.getuid(),
            "st_gid": os.getgid(),
            "st_size": len(physical_raw),
            "st_mtime_ns": 1,
            "st_ctime_ns": 1,
        }
        snapshots.append(
            {
                "relative_path": relative,
                "expected": {
                    "file_type": "REGULAR_FILE",
                    "git_mode": "100644",
                    "mode": 0o644,
                    "st_nlink": 1,
                    "binding_kind": binding_kind,
                    "byte_count": len(effective_raw),
                    "sha256": hashlib.sha256(effective_raw).hexdigest(),
                    "git_blob_id": effective_blob,
                },
                "observed_before": observed_stat,
                "observed_after": dict(observed_stat),
                "observed_content": {
                    "binding_kind": binding_kind,
                    "byte_count": len(effective_raw),
                    "sha256": hashlib.sha256(effective_raw).hexdigest(),
                    "git_blob_id": effective_blob,
                    "physical_byte_count": len(physical_raw),
                    "physical_sha256": hashlib.sha256(
                        physical_raw
                    ).hexdigest(),
                    "physical_git_blob_id": physical_blob,
                },
                "mismatch_fields": [],
                "conformant": True,
            }
        )
    return {
        "schema": (
            "acfqp.v180r12r4_working_tree_source_conformance_diagnostic.v1"
        ),
        "phase": "BEFORE_PRELAUNCH_OUTPUT_AND_SCIENTIFIC_CAMPAIGN",
        "source_root_count": len(snapshots),
        "snapshots": snapshots,
        "mismatch_count": 0,
        "per_field_mismatches": [],
        "unit_ownership_evaluated": False,
        "full_source_conformance": True,
        "cause": None,
    }


def _successful_measurement_cgroup_observations(
    campaign_attempt_id: str,
) -> list[dict[str, object]]:
    return [
        launcher._blank_measurement_cgroup_observation(
            phase=phase,
            applicable=True,
            campaign_attempt_id=campaign_attempt_id,
            root_state="ABSENT",
            ownership_acquired=True,
        )
        for phase in launcher.MEASUREMENT_CGROUP_OBSERVATION_PHASES
    ]


def _frozen_authorization_context(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, object]:
    mount = repository / "fake-cgroup2"
    parent = mount / "app.slice"
    parent.mkdir(parents=True)
    mount_stat = os.stat(mount)
    parent_stat = os.stat(parent)
    values = {
        "protocol_id": finalizer_fixture.ledger_fixture.PROTOCOL_ID,
        "authorization_id": finalizer_fixture.ledger_fixture.AUTHORIZATION_ID,
        "authorization_evidence_id": (
            finalizer_fixture.ledger_fixture.AUTHORIZATION_EVIDENCE_ID
        ),
        "campaign_measurement_execution_slot_id": (
            finalizer_fixture.ledger_fixture.EXECUTION_SLOT_ID
        ),
        "logical_occurrence_id": finalizer_fixture.ledger_fixture.LOGICAL_OCCURRENCE_ID,
        "execution_nonce": finalizer_fixture.ledger_fixture.EXECUTION_NONCE,
    }
    attempt_payload = {
        "schema": "acfqp.campaign_measurement_attempt.v180r12r4",
        **values,
    }
    attempt_id = hashlib.sha256(
        b"acfqp:construction-k7-campaign-measurement-attempt:v180r12r4\x00"
        + _canonical(attempt_payload)
    ).hexdigest()
    context = {
        "schema": launcher.FROZEN_AUTHORIZATION_CONTEXT_SCHEMA,
        "protocol_id": values["protocol_id"],
        "protocol_byte_count": 101,
        "protocol_sha256": "7" * 64,
        "authorization_id": values["authorization_id"],
        "authorization_byte_count": 102,
        "authorization_sha256": "8" * 64,
        "authorization_evidence_id": values["authorization_evidence_id"],
        "authorization_evidence_byte_count": 103,
        "authorization_evidence_sha256": "9" * 64,
        "campaign_measurement_execution_slot_id": values[
            "campaign_measurement_execution_slot_id"
        ],
        "logical_occurrence_id": values["logical_occurrence_id"],
        "execution_nonce": values["execution_nonce"],
        "campaign_attempt_id": attempt_id,
        "cgroup_parent_fact": {
            "schema": "acfqp.v180r12r4_cgroup_parent_fact.v1",
            "mount_point": str(mount),
            "mount_fstype": "cgroup2",
            "mount_device": mount_stat.st_dev,
            "mount_inode": mount_stat.st_ino,
            "mount_options": ["rw"],
            "parent_path": str(parent),
            "parent_device": parent_stat.st_dev,
            "parent_inode": parent_stat.st_ino,
            "owner_uid": parent_stat.st_uid,
            "owner_gid": parent_stat.st_gid,
            "mode": stat.S_IMODE(parent_stat.st_mode),
            "controllers": ["cpu", "memory", "pids"],
            "subtree_control": ["cpu", "memory", "pids"],
            "cgroup_type": "domain",
            "cgroup_namespace_inode": 3,
            "cgroup_events_present": True,
            "memory_events_present": True,
            "pids_events_present": True,
            "cgroup_kill_present": True,
            "cgroup_procs_present": True,
            "memory_peak_present": True,
            "pids_peak_present": True,
            "self_membership": (
                "0::/app.slice/"
                "acfqp-v180r12r4r5-freeze-capture-20260829.service"
            ),
        },
        "runtime_capability_fact": {
            "schema": "acfqp.v180r12r4_runtime_capability_fact.v1",
            "machine_architecture": "x86_64",
            "single_threaded": True,
            "clone3_probe_errno": 22,
            "clone3_syscall_recognized": True,
            "pidfd_send_signal_probe_errno": 9,
            "pidfd_send_signal_recognized": True,
            "execveat_probe_errno": 9,
            "execveat_recognized": True,
            "pidfd_wait_present": True,
            "landlock_abi": 7,
            "uid": os.getuid(),
            "gid": os.getgid(),
            "effective_capability_mask": 0,
            "admitted": True,
        },
    }
    capture_raw = _canonical(
        {
            "capture_purpose": launcher.SERVICE_CONTEXT_CAPTURE_PURPOSE,
            "cgroup_parent_fact": context["cgroup_parent_fact"],
            "runtime_capability_fact": context["runtime_capability_fact"],
            "schema": launcher.SERVICE_CONTEXT_CAPTURE_SCHEMA,
        }
    ) + b"\n"
    monkeypatch.setattr(
        launcher,
        "SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT",
        len(capture_raw),
    )
    monkeypatch.setattr(
        launcher,
        "SERVICE_CONTEXT_CAPTURE_CANONICAL_SHA256",
        hashlib.sha256(capture_raw).hexdigest(),
    )
    return context


def _materialized_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, str]:
    source_rule_id = "1" * 64
    materialization_rule_id = "2" * 64
    monkeypatch.setattr(launcher, "SOURCE_CLOSURE_RULE_ID", source_rule_id)
    monkeypatch.setattr(
        launcher, "MATERIALIZATION_RULE_ID", materialization_rule_id
    )
    monkeypatch.setitem(
        launcher.LAUNCH_RULE_DOCUMENT,
        "source_closure_rule_id",
        source_rule_id,
    )
    monkeypatch.setitem(
        launcher.LAUNCH_RULE_DOCUMENT,
        "materialization_rule_id",
        materialization_rule_id,
    )
    launch_rule_id = hashlib.sha256(
        _canonical(launcher.LAUNCH_RULE_DOCUMENT)
    ).hexdigest()
    monkeypatch.setattr(launcher, "LAUNCH_RULE_ID", launch_rule_id)
    repository = tmp_path / "repository"
    repository.mkdir()
    frozen_authorization_context = _frozen_authorization_context(
        repository, monkeypatch
    )

    def fake_placement_t1(
        *, target: str, frozen_context: dict[str, object]
    ) -> tuple[tuple[int, int, int], dict[str, object]]:
        fact = frozen_context["cgroup_parent_fact"]
        assert type(fact) is dict
        parent = Path(str(fact["parent_path"]))
        mount = Path(str(fact["mount_point"]))
        _token_input, token, unit_name = (
            launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
        )
        service = parent / unit_name
        service.mkdir(exist_ok=True)

        def bind(path: Path, destination: int, flags: int) -> None:
            source = os.open(path, flags | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                os.dup2(source, destination, inheritable=True)
            finally:
                if source != destination:
                    os.close(source)

        bind(parent, launcher.DELEGATED_CGROUP_PARENT_FD, os.O_RDONLY)
        bind(mount, launcher.CGROUP2_MOUNT_FD, os.O_PATH)
        bind(service, launcher.SOURCE_SYSTEMD_SERVICE_FD, os.O_RDONLY)
        membership = f"0::/app.slice/{unit_name}"
        return (
            (
                launcher.DELEGATED_CGROUP_PARENT_FD,
                launcher.CGROUP2_MOUNT_FD,
                launcher.SOURCE_SYSTEMD_SERVICE_FD,
            ),
            {
                "schema": launcher.PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA,
                "target": target,
                "token": token,
                "unit_name": unit_name,
                "slice": launcher.PRODUCTION_TRANSIENT_SERVICE_SLICE,
                "source_membership": membership,
                "expected_source_membership": membership,
                "self_pid": os.getpid(),
                "self_pid_in_source_cgroup_procs": True,
                "cgroup_namespace_inode": os.stat("/proc/self/ns/cgroup").st_ino,
                "delegated_parent_fd_fact": launcher._directory_fd_fact(
                    launcher.DELEGATED_CGROUP_PARENT_FD,
                    "DELEGATED_CGROUP_PARENT_DIRECTORY",
                    "O_RDONLY",
                ),
                "cgroup2_mount_fd_fact": launcher._directory_fd_fact(
                    launcher.CGROUP2_MOUNT_FD,
                    "CGROUP2_MOUNT_DIRECTORY",
                    "O_PATH",
                ),
                "source_service_fd_fact": launcher._directory_fd_fact(
                    launcher.SOURCE_SYSTEMD_SERVICE_FD,
                    "SOURCE_SYSTEMD_SERVICE_DIRECTORY",
                    "O_RDONLY",
                ),
                "nearest_common_ancestor_path": str(parent),
                "nearest_common_ancestor_is_app_slice": True,
                "parent_cgroup_procs_o_wronly_openable": True,
                "planned_measurement_root_observation": (
                    launcher._blank_measurement_cgroup_observation(
                        phase="BEFORE_POPEN",
                        applicable=True,
                        campaign_attempt_id=str(
                            frozen_context["campaign_attempt_id"]
                        ),
                        root_state="ABSENT",
                        ownership_acquired=False,
                    )
                ),
                "planned_measurement_root_absent": True,
                "t1_complete_before_child_popen": True,
            },
        )

    monkeypatch.setattr(
        launcher,
        "_prepare_and_observe_production_runtime_placement_t1",
        fake_placement_t1,
    )
    prelaunch = repository / launcher.PRELAUNCH_ROOT_RELATIVE_PATH
    prelaunch.mkdir(parents=True)
    prelaunch.chmod(0o700)

    bootstrap_raw = b"# retained bootstrap\n"
    launcher_raw = SCRIPT.read_bytes()
    wrapper_raw = b"EXPECTED_AUTHORIZATION_ID = 'literal'\n"
    wrapper_normalized_raw = b"EXPECTED_AUTHORIZATION_ID = 0\n"
    wrapper_raw_fact = _fact(
        launcher.AUTHORIZATION_EVIDENCE_RELATIVE_PATH, wrapper_raw
    )
    wrapper_normalized_fact = {
        **_fact(
            launcher.AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
            wrapper_normalized_raw,
        ),
        "binding_kind": launcher.NORMALIZED_WRAPPER_BINDING_KIND,
        "redacted_constant_names": list(
            launcher.WRAPPER_REDACTED_CONSTANT_NAMES
        ),
    }
    authorization_closure = _closure([wrapper_normalized_fact])
    source_conformance = _working_tree_source_conformance(
        [(wrapper_normalized_fact, wrapper_raw)]
    )
    third_party_closure = _closure(
        [
            {
                **_fact("packaging/__init__.py", b"# packaging\n"),
                "module": "packaging",
                "is_package": True,
                "source_root": "/bound/third-party",
            }
        ]
    )
    manifest = {
        "schema": "acfqp.v180r12r4_source_bound_launch_manifest.v1",
        "repository_root": str(repository),
        "c_pre_root": str(prelaunch),
        "manifest_relative_path": "launch_manifest.json",
        "c_pre_commit_id": "a" * 40,
        "bootstrap": _fact("bootstrap.py", bootstrap_raw),
        "runtime": {},
        "git": {},
        "authorization_source_closure_kind": "TEST_BOUND_CLOSURE",
        "authorization_self_module": "acfqp.test_authorization",
        "authorization_raw_source_modules": ["acfqp.test_wrapper"],
        "authorization_source_closure": authorization_closure,
        "working_tree_source_conformance": source_conformance,
        "source_modules": [
            {
                **wrapper_raw_fact,
                "module": "acfqp.test_wrapper",
                "is_package": False,
            }
        ],
        "third_party_source_closure": third_party_closure,
        "targets": {
            "measurement": _fact(
                "scripts/run_v180r12r4_campaign_measurement.py",
                b"# measurement\n",
            ),
            "verification": _fact(
                "scripts/verify_v180r12r4_campaign_measurement.py",
                b"# verification\n",
            ),
            "supervisor": _fact(
                "scripts/supervise_v180r12r4_campaign_measurement.py",
                b"# supervisor\n",
            ),
            "worker": _fact(
                "scripts/work_v180r12r4_campaign_measurement.py",
                b"# worker\n",
            ),
        },
        "internal_target_contract": launcher.INTERNAL_TARGET_CONTRACT,
        "production_systemd_service_contract": (
            launcher._production_systemd_service_contract()
        ),
        "production_systemd_run_argv_templates": {
            target: launcher._production_systemd_run_argv_template(
                repository, target
            )
            for target in ("measurement", "verification")
        },
        "production_service_launch_artifact_paths": (
            launcher.PRODUCTION_SERVICE_LAUNCH_ARTIFACT_PATHS
        ),
        "production_service_launch_modes": (
            launcher.PRODUCTION_SERVICE_LAUNCH_MODES
        ),
        "atomic_cgroup_birth_preflight_receipt_interface": (
            launcher._zero_preflight_receipt_interface()
        ),
        "frozen_authorization_context": frozen_authorization_context,
        "working_tree_mutation_after_snapshot_in_scope": False,
    }
    manifest_raw = _canonical(manifest)
    _write_0400(repository / launcher.BOOTSTRAP_RELATIVE_PATH, bootstrap_raw)
    _write_0400(repository / launcher.LAUNCHER_RELATIVE_PATH, launcher_raw)
    _write_0400(repository / launcher.MANIFEST_RELATIVE_PATH, manifest_raw)
    monkeypatch.setattr(
        launcher,
        "__file__",
        str(repository / launcher.LAUNCHER_RELATIVE_PATH),
    )
    monkeypatch.setattr(
        launcher.sys,
        "argv",
        [str(repository / launcher.LAUNCHER_RELATIVE_PATH)],
    )

    bootstrap_git_fact = _git_fact(
        launcher.SOURCE_BOOTSTRAP_RELATIVE_PATH, bootstrap_raw, "1" * 40
    )
    launcher_git_fact = _git_fact(
        launcher.SOURCE_LAUNCHER_RELATIVE_PATH, launcher_raw, "2" * 40
    )
    materializer_git_fact = _git_fact(
        launcher.SOURCE_MATERIALIZER_RELATIVE_PATH, b"# materializer\n", "3" * 40
    )
    external_root = {
        "schema": "acfqp.v180r12r4_prelaunch_external_root.v1",
        "materialization_rule_id": launcher.MATERIALIZATION_RULE_ID,
        "source_closure_rule_id": launcher.SOURCE_CLOSURE_RULE_ID,
        "repository_root": str(repository),
        "git_directory": str(repository / ".git"),
        "c_pre_commit_id": "a" * 40,
        "c_pre_tree_id": "4" * 40,
        "bootstrap_git_blob": bootstrap_git_fact,
        "launcher_git_blob": launcher_git_fact,
        "materializer_git_blob": materializer_git_fact,
        "third_party_source_roots": {
            "packaging": "/bound/third-party",
            "tomli": "/bound/third-party",
        },
        "frozen_authorization_context": frozen_authorization_context,
        "atomic_cgroup_birth_preflight_receipt_interface": (
            launcher._zero_preflight_receipt_interface()
        ),
        "created_before_v180r12r4_authorized_measurement_execution": True,
        "v180r12r4_outcome_bytes_accessed": False,
    }
    external_raw = _canonical(external_root)
    external_path = repository / launcher.EXTERNAL_ROOT_RELATIVE_PATH
    _write_0400(external_path, external_raw)

    payload = {
        "schema": launcher.MATERIALIZATION_TERMINAL_SCHEMA,
        "materialization_rule_id": launcher.MATERIALIZATION_RULE_ID,
        "source_closure_rule_id": launcher.SOURCE_CLOSURE_RULE_ID,
        "repository_root": str(repository),
        "external_root": {
            "absolute_path": str(external_path),
            "byte_count": len(external_raw),
            "sha256": hashlib.sha256(external_raw).hexdigest(),
            "immutable_mode": "0400",
        },
        "git_topology": {
            "c_pre_commit_id": "a" * 40,
            "c_pre_tree_id": "4" * 40,
            "empty_bridge_commit_id": "b" * 40,
            "empty_bridge_tree_id": "4" * 40,
            "literal_commit_id": "c" * 40,
            "literal_commit_tree_id": "5" * 40,
            "literal_wrapper_prior_blob_id": "6" * 40,
            "literal_wrapper_blob_id": "7" * 40,
        },
        "bootstrap_source_git_blob": bootstrap_git_fact,
        "materializer_source_git_blob": materializer_git_fact,
        "launcher_source_git_blob": launcher_git_fact,
        "retained_bootstrap": _fact(launcher.BOOTSTRAP_RELATIVE_PATH, bootstrap_raw),
        "retained_launcher": _fact(launcher.LAUNCHER_RELATIVE_PATH, launcher_raw),
        "launch_manifest": _fact(launcher.MANIFEST_RELATIVE_PATH, manifest_raw),
        "production_transient_service_rows": [
            {
                "target": target,
                "token": launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS[target][1],
                "unit_name": launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS[target][2],
            }
            for target in ("measurement", "verification")
        ],
        "production_service_launch_artifact_paths": (
            launcher.PRODUCTION_SERVICE_LAUNCH_ARTIFACT_PATHS
        ),
        "production_service_launch_modes": (
            launcher.PRODUCTION_SERVICE_LAUNCH_MODES
        ),
        "atomic_cgroup_birth_preflight_receipt_interface": (
            launcher._zero_preflight_receipt_interface()
        ),
        "materialization_terminal_relative_path": (
            launcher.MATERIALIZATION_TERMINAL_RELATIVE_PATH
        ),
        "materialization_failure_relative_path": (
            launcher.MATERIALIZATION_FAILURE_RELATIVE_PATH
        ),
        "authorization_source_closure_file_count": authorization_closure[
            "file_count"
        ],
        "authorization_source_closure_total_byte_count": authorization_closure[
            "total_byte_count"
        ],
        "authorization_source_closure_facts_sha256": authorization_closure[
            "facts_sha256"
        ],
        "third_party_source_closure_file_count": third_party_closure[
            "file_count"
        ],
        "third_party_source_closure_total_byte_count": third_party_closure[
            "total_byte_count"
        ],
        "third_party_source_closure_facts_sha256": third_party_closure[
            "facts_sha256"
        ],
        "normalized_wrapper_fact": wrapper_normalized_fact,
        "current_literal_wrapper_raw_observation": wrapper_raw_fact,
        "working_tree_source_conformance": source_conformance,
        "launch_manifest_digest_is_runtime_supplied_not_protocol_frozen": True,
        "launch_manifest_has_no_self_digest": True,
        "frozen_authorization_context_sha256": hashlib.sha256(
            _canonical(frozen_authorization_context)
        ).hexdigest(),
        "external_root_created_before_authorized_measurement_execution": True,
        "external_root_required_before_authorization_issuance": False,
        "materialization_terminal_written_last": True,
        "write_once_o_excl": True,
        "write_no_follow": True,
        "close_on_exec": True,
        "output_directory_mode": "0700",
        "output_file_mode": "0400",
        "file_and_directory_fsync_required": True,
        "same_materialization_identity_rerun_forbidden": True,
        "construction_only": True,
        "preauthorization_supervision": True,
        "campaign_actual_measurement": False,
        "scientific_occurrence_executed": False,
        "v180r12r4_outcome_bytes_accessed": False,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_execution_allowed": False,
        "success": True,
    }
    terminal = {
        **payload,
        "materialization_terminal_id": hashlib.sha256(_canonical(payload)).hexdigest(),
    }
    terminal_raw = _canonical(terminal)
    _write_0400(
        repository / launcher.MATERIALIZATION_TERMINAL_RELATIVE_PATH,
        terminal_raw,
    )
    return repository, hashlib.sha256(terminal_raw).hexdigest()


def test_rule_sentinels_caps_and_attempt_first_are_exact() -> None:
    rules = (
        launcher.EXPECTED_SOURCE_CLOSURE_RULE_ID,
        launcher.EXPECTED_MATERIALIZATION_RULE_ID,
        launcher.EXPECTED_LAUNCH_RULE_ID,
    )
    assert launcher.SOURCE_CLOSURE_RULE_ID == rules[0]
    assert launcher.MATERIALIZATION_RULE_ID == rules[1]
    assert launcher.LAUNCH_RULE_ID == rules[2]
    if all(value != ZERO_ID for value in rules):
        assert all(len(value) == 64 for value in rules)
    else:
        assert rules == (ZERO_ID, ZERO_ID, ZERO_ID)
    assert launcher.EXPECTED_SOURCE_CLOSURE_RULE_ID == (
        protocol.EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID
    )
    assert launcher.EXPECTED_MATERIALIZATION_RULE_ID == (
        protocol.EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID
    )
    assert launcher.EXPECTED_LAUNCH_RULE_ID == (
        protocol.EXPECTED_PRELAUNCH_LAUNCH_RULE_ID
    )
    assert launcher.LAUNCH_RULE_DOCUMENT["address_space_hard_cap_bytes"] == (
        16 * 1024 * 1024 * 1024
    )
    assert launcher.LAUNCH_RULE_DOCUMENT["attempt_lock_written_before_child_exec"]
    assert launcher.LAUNCH_RULE_DOCUMENT["campaign_actual_measurement"] is False
    assert launcher.LAUNCH_RULE_DOCUMENT[
        "no_cleanup_syscall_is_started_after_sampled_hard_deadline"
    ] is True
    assert launcher.LAUNCH_RULE_DOCUMENT[
        "individual_cgroupfs_syscall_completion_before_hard_deadline_claimed"
    ] is False
    assert launcher.LAUNCH_RULE_DOCUMENT[
        "cgroupfs_syscall_blocking_is_trusted_runtime_boundary"
    ] is True
    assert launcher.LAUNCH_RULE_DOCUMENT[
        "sock_seqpacket_buffer_request_bytes"
    ] == launcher.SOCK_SEQPACKET_BUFFER_REQUEST_BYTES == 1_048_576
    assert launcher.LAUNCH_RULE_DOCUMENT[
        "sock_seqpacket_effective_min_bytes"
    ] == launcher.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES == 2_097_152
    assert launcher.INTERNAL_TARGET_CONTRACT[
        "sock_seqpacket_so_sndbuf_and_so_rcvbuf_required_on_both_endpoints"
    ] is True
    module_contract = launcher.INTERNAL_TARGET_CONTRACT[
        "precompiled_runner_module_contract"
    ]
    assert module_contract["target_order"] == [
        "measurement",
        "verification",
        "supervisor",
        "worker",
    ]
    assert module_contract["registered_before_runner_exec"] is True
    assert module_contract["preexisting_registration_is_preserved"] is True
    assert module_contract[
        "registration_removed_after_postchecks_on_success_or_failure"
    ] is True
    assert module_contract["runner_module_registration_leak_forbidden"] is True
    assert launcher.CHILD_STREAM_BYTE_CAP == 1024 * 1024
    assert launcher.SCIENTIFIC_ARTIFACT_BYTE_CAP == 16 * 1024 * 1024
    assert launcher.WALL_TIMEOUT_SECONDS == protocol.WALL_TIMEOUT_SECONDS
    assert launcher.ADDRESS_SPACE_HARD_CAP_BYTES == (
        protocol.ADDRESS_SPACE_HARD_CAP_BYTES
    )


def test_success_artifact_contract_is_byte_exact_across_protocol_and_finalizer() -> None:
    assert launcher.SUCCESS_ARTIFACT_ORDER == finalizer.SUCCESS_ARTIFACT_ORDER
    assert launcher.SUCCESS_DURABLE_WRITE_ORDER == (
        "EVIDENCE_INVENTORY",
        "EXECUTION_CLOSURE",
        "OS_RECEIPT",
        "LEDGER_CLOSURE",
        "TERMINAL",
    )
    assert launcher.SUCCESS_DURABLE_WRITE_ORDER == protocol.SUCCESS_DURABLE_WRITE_ORDER
    launcher_schema_rows = tuple(
        (mapping_key, schema, identity_field, terminal_prefix)
        for (
            _artifact_name,
            mapping_key,
            _relative_path,
            schema,
            _domain,
            identity_field,
            terminal_prefix,
            _fields,
            _cap,
        ) in launcher.SUCCESS_ARTIFACT_ROWS
    )
    assert launcher_schema_rows == finalizer.SUCCESS_ARTIFACT_SCHEMA_ROWS
    assert set(launcher.EVIDENCE_INVENTORY_BUNDLE_FIELDS) == set(
        protocol.EVIDENCE_INVENTORY_BUNDLE_FIELDS
    )
    assert set(launcher.EXECUTION_CLOSURE_FIELDS) == set(
        protocol.EXECUTION_CLOSURE_FIELDS
    )
    assert set(launcher.OS_RECEIPT_BUNDLE_FIELDS) == set(
        protocol.OS_RECEIPT_BUNDLE_FIELDS
    )
    assert set(launcher.LEDGER_CLOSURE_FIELDS) == set(
        protocol.LEDGER_CLOSURE_FIELDS
    )
    assert launcher.TERMINAL_FIELDS == finalizer.TERMINAL_FIELDS
    assert tuple(row[8] for row in launcher.SUCCESS_ARTIFACT_ROWS) == (
        protocol.EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP,
        protocol.EXECUTION_CLOSURE_BYTE_CAP,
        protocol.OS_RECEIPT_BUNDLE_BYTE_CAP,
        protocol.LEDGER_CLOSURE_BYTE_CAP,
    )
    assert launcher.LAUNCH_RULE_DOCUMENT["success_durable_write_order"] == list(
        launcher.SUCCESS_DURABLE_WRITE_ORDER
    )
    assert launcher.LAUNCH_RULE_DOCUMENT[
        "verification_predecessor_rejoins_current_exact_four_artifact_bytes"
    ] is True


@pytest.mark.parametrize(
    "rule_name",
    (
        "SOURCE_CLOSURE_RULE_ID",
        "MATERIALIZATION_RULE_ID",
        "LAUNCH_RULE_ID",
    ),
)
def test_zero_rule_sentinels_refuse_before_attempt_or_failure_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule_name: str,
) -> None:
    repository = (tmp_path / "zero-sentinel-repository").absolute()
    repository.mkdir()
    monkeypatch.setattr(launcher, rule_name, ZERO_ID)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="remain zero sentinels",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, ZERO_ID
        )
    assert not (repository / ".tmp").exists()


def test_launch_rule_identity_recomputes_exact_canonical_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_rule_id = "1" * 64
    materialization_rule_id = "2" * 64
    monkeypatch.setattr(launcher, "SOURCE_CLOSURE_RULE_ID", source_rule_id)
    monkeypatch.setattr(
        launcher, "MATERIALIZATION_RULE_ID", materialization_rule_id
    )
    monkeypatch.setitem(
        launcher.LAUNCH_RULE_DOCUMENT, "source_closure_rule_id", source_rule_id
    )
    monkeypatch.setitem(
        launcher.LAUNCH_RULE_DOCUMENT,
        "materialization_rule_id",
        materialization_rule_id,
    )
    monkeypatch.setattr(
        launcher,
        "LAUNCH_RULE_ID",
        hashlib.sha256(_canonical(launcher.LAUNCH_RULE_DOCUMENT)).hexdigest(),
    )
    launcher._require_rule_identities_frozen()
    monkeypatch.setitem(
        launcher.LAUNCH_RULE_DOCUMENT,
        "attempt_lock_written_before_child_exec",
        False,
    )
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="identity binding changed",
    ):
        launcher._require_rule_identities_frozen()


def test_preexec_applies_rlimit_before_exec(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[object] = []
    monkeypatch.setattr(launcher.os, "setsid", lambda: events.append("setsid"))
    monkeypatch.setattr(
        launcher.resource,
        "setrlimit",
        lambda kind, value: events.append((kind, value)),
    )
    launcher._child_preexec()
    assert events == [
        "setsid",
        (
            launcher.resource.RLIMIT_AS,
            (
                launcher.ADDRESS_SPACE_HARD_CAP_BYTES,
                launcher.ADDRESS_SPACE_HARD_CAP_BYTES,
            ),
        ),
    ]


def test_measurement_attempt_precedes_child_and_success_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_run(
        argv: list[str], environment: dict[str, str], pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        assert pass_fds == (249, 250, 251, 252)
        attempt = repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH
        assert attempt.is_file()
        assert environment == {
            launcher.MANIFEST_SHA256_ENV: hashlib.sha256(
                (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
            ).hexdigest(),
            "LC_CTYPE": "C.UTF-8",
        }
        _write_measurement_success(repository)
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_run)
    receipt = launcher.launch_prelaunch_target_v180r12r4(
        "measurement", repository, digest
    )
    assert receipt["schema"] == launcher.LAUNCH_RECEIPT_SCHEMA
    assert receipt["success"] is True
    assert receipt["authorized_child_measurement_execution_attempted"] is True
    assert receipt["authorized_child_measurement_execution_completed"] is True
    assert receipt["producer_free_verification_attempted"] is False
    assert receipt["producer_free_verification_completed"] is False
    rows = receipt["measurement_cgroup_cleanup_observations"]
    assert [row["phase"] for row in rows] == list(
        launcher.MEASUREMENT_CGROUP_OBSERVATION_PHASES
    )
    assert all(row["root_state"] == "ABSENT" for row in rows)
    assert all(row["ownership_acquired"] is True for row in rows)
    attempt_document = json.loads(
        (repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH).read_text(
            encoding="utf-8"
        )
    )
    assert attempt_document["authorized_child_measurement_execution_attempted"] is True
    assert attempt_document["authorized_child_measurement_execution_completed"] is False
    assert (repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH).is_file()
    assert (repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH).is_file()
    assert not os.path.lexists(
        repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
    )
    with pytest.raises(launcher.V180r12r4PrelaunchLaunchReplayForbidden):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )


def test_host_conformance_rejects_bool_for_frozen_integer_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _digest = _materialized_repository(tmp_path, monkeypatch)
    frozen = json.loads(
        (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
    )["frozen_authorization_context"]
    _write_pre_attempt_host_conformance(
        repository,
        observed_parent_updates={"mount_inode": True},
    )
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="success semantics changed",
    ):
        launcher._validate_pre_attempt_host_conformance(
            repository,
            frozen_context=frozen,
            expected_source_membership=(
                "0::/app.slice/"
                + launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS["measurement"][2]
            ),
        )


@pytest.mark.parametrize("value", [True, 2_097_152.0, 2_097_151])
def test_host_conformance_rejects_invalid_socket_minimum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: object
) -> None:
    repository, _digest = _materialized_repository(tmp_path, monkeypatch)
    frozen = json.loads(
        (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
    )["frozen_authorization_context"]
    _write_pre_attempt_host_conformance(
        repository,
        observed_socket_updates={"endpoint_0_so_sndbuf_bytes": value},
    )
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="success semantics changed",
    ):
        launcher._validate_pre_attempt_host_conformance(
            repository,
            frozen_context=frozen,
            expected_source_membership=(
                "0::/app.slice/"
                + launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS["measurement"][2]
            ),
        )


def test_host_conformance_accepts_socket_observations_above_minimum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _digest = _materialized_repository(tmp_path, monkeypatch)
    frozen = json.loads(
        (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
    )["frozen_authorization_context"]
    _write_pre_attempt_host_conformance(
        repository,
        observed_socket_updates={
            field: launcher.SOCKET_BUFFER_CAPABILITY_EXPECTED[field] + 1_048_576
            for field in launcher.SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS
        },
    )
    _raw, document, _fact = launcher._validate_pre_attempt_host_conformance(
        repository,
        frozen_context=frozen,
        expected_source_membership=(
            "0::/app.slice/"
            + launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS["measurement"][2]
        ),
    )
    assert document["full_host_conformance"] is True


@pytest.mark.parametrize(
    "field",
    (
        "authorization_evidence_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
    ),
)
def test_resigned_terminal_cannot_substitute_authorization_or_transport_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_run(
        argv: list[str], environment: dict[str, str], pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        del argv, environment
        assert pass_fds == (249, 250, 251, 252)
        _write_measurement_success(repository)
        terminal_path = repository / launcher.TERMINAL_RELATIVE_PATH
        mutated = _resigned_terminal_bytes(
            terminal_path.read_bytes(), {field: "f" * 64}
        )
        terminal_path.chmod(0o600)
        terminal_path.write_bytes(mutated)
        terminal_path.chmod(0o400)
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_run)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="authorization or transport provenance",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    assert not (repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH).exists()
    assert (repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH).is_file()


@pytest.mark.parametrize(
    "relative_path",
    (
        launcher.EVIDENCE_INVENTORY_RELATIVE_PATH,
        launcher.EXECUTION_CLOSURE_RELATIVE_PATH,
        launcher.OS_RECEIPT_RELATIVE_PATH,
        launcher.LEDGER_CLOSURE_RELATIVE_PATH,
    ),
)
def test_measurement_missing_success_artifact_cannot_receive_launch_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_path: str,
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_run(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        _write_measurement_success(repository)
        (repository / relative_path).unlink()
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_run)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    assert not os.path.lexists(repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH)


def test_bootstrap_failure_preserves_attempt_and_typed_launch_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fail_before_runner(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        assert (repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH).is_file()
        raise ValueError("bootstrap primary")

    monkeypatch.setattr(launcher, "_run_child", fail_before_runner)
    with pytest.raises(ValueError, match="bootstrap primary"):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    failure_path = repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    assert failure["schema"] == launcher.LAUNCH_FAILURE_SCHEMA
    assert failure["failure_type"] == "ValueError"
    assert failure["failure_message"] == "bootstrap primary"
    assert failure["attempt_lock_preserved"] is True
    assert failure["same_target_identity_rerun_forbidden"] is True
    assert failure["authorized_child_measurement_execution_attempted"] is True
    assert failure["authorized_child_measurement_execution_completed"] is False
    assert set(failure) == (
        launcher._TERMINAL_KEYS
        | launcher._LAUNCH_FAILURE_PUBLICATION_KEYS
        | {"launch_failure_id"}
    )
    assert all(
        failure[name] is None
        for name in launcher._LAUNCH_FAILURE_PUBLICATION_KEYS
    )


def test_verification_requires_successful_measurement_and_writes_own_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    prelaunch = repository / launcher.PRELAUNCH_ROOT_RELATIVE_PATH
    materialization, materialization_raw = launcher._load_materialization(
        repository, digest
    )
    attempt, attempt_raw = launcher._attempt_document(
        target="measurement",
        repository_root=repository,
        materialization=materialization,
        materialization_raw=materialization_raw,
        manifest_sha256=hashlib.sha256(
            (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
        ).hexdigest(),
        child_argv=[
            *launcher.ISOLATED_ARGV_PREFIX,
            str(repository / launcher.BOOTSTRAP_RELATIVE_PATH),
            "measurement",
            str(repository),
            str(repository / launcher.PRELAUNCH_ROOT_RELATIVE_PATH),
            str(repository / launcher.MANIFEST_RELATIVE_PATH),
        ],
        production_systemd_service_invocation=(
            launcher._production_systemd_service_invocation(
                repository, digest, "measurement"
            )
        ),
    )
    _write_0400(prelaunch / "MEASUREMENT_LAUNCH_ATTEMPT.json", attempt_raw)
    _write_measurement_success(repository)
    prior_progress = launcher._progress_observations(
        launcher._state_paths(repository, "measurement")
    )
    frozen_context = json.loads(
        (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
    )["frozen_authorization_context"]
    placement_descriptors, measurement_placement_t1 = (
        launcher._prepare_and_observe_production_runtime_placement_t1(
            target="measurement", frozen_context=frozen_context
        )
    )
    for descriptor in placement_descriptors:
        os.close(descriptor)
    empty = launcher._StreamObservation().document()
    prior_receipt, prior_receipt_raw = launcher._terminal_document(
        schema=launcher.LAUNCH_RECEIPT_SCHEMA,
        id_key="launch_receipt_id",
        target="measurement",
        attempt=attempt,
        return_code=0,
        timed_out=False,
        stdout=empty,
        stderr=empty,
        progress=prior_progress,
        error=None,
        launch_deadlines=launcher._freeze_launch_deadlines_v180r12r4(),
        measurement_cgroup_cleanup_observations=(
            _successful_measurement_cgroup_observations(
                finalizer_fixture.ledger_fixture.ATTEMPT_ID
            )
        ),
        production_systemd_service_invocation=(
            launcher._production_systemd_service_invocation(
                repository, digest, "measurement"
            )
        ),
        production_runtime_placement_t1=measurement_placement_t1,
    )
    assert prior_receipt["success"] is True
    _write_0400(prelaunch / "MEASUREMENT_LAUNCH_RECEIPT.json", prior_receipt_raw)

    def fake_verify(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        (repository / launcher.VERIFICATION_RELATIVE_PATH).write_bytes(b"{}")
        (repository / launcher.RETAINED_REPLAY_RELATIVE_PATH).write_bytes(b"{}")
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_verify)
    receipt = launcher.launch_prelaunch_target_v180r12r4(
        "verification", repository, digest
    )
    assert receipt["target"] == "verification"
    assert receipt["success"] is True
    assert receipt["authorized_child_measurement_execution_attempted"] is False
    assert receipt["authorized_child_measurement_execution_completed"] is False
    assert receipt["producer_free_verification_attempted"] is True
    assert receipt["producer_free_verification_completed"] is True
    assert (repository / launcher.VERIFICATION_ATTEMPT_RELATIVE_PATH).is_file()
    assert (repository / launcher.VERIFICATION_RECEIPT_RELATIVE_PATH).is_file()


def test_measurement_success_rejects_nonempty_child_diagnostic_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_measurement(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        _write_measurement_success(repository)
        stdout = launcher._StreamObservation()
        stdout.add(b"unexpected diagnostic")
        return (
            0,
            False,
            stdout.document(),
            launcher._StreamObservation().document(),
        )

    monkeypatch.setattr(launcher, "_run_child", fake_measurement)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    assert not os.path.lexists(repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH)


def test_verification_success_rejects_nonempty_child_diagnostic_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_measurement(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        _write_measurement_success(repository)
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_measurement)
    launcher.launch_prelaunch_target_v180r12r4("measurement", repository, digest)

    def fake_verification(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        _write_0400(repository / launcher.VERIFICATION_RELATIVE_PATH, b"{}")
        _write_0400(repository / launcher.RETAINED_REPLAY_RELATIVE_PATH, b"{}")
        stderr = launcher._StreamObservation()
        stderr.add(b"unexpected warning")
        return (
            0,
            False,
            launcher._StreamObservation().document(),
            stderr.document(),
        )

    monkeypatch.setattr(launcher, "_run_child", fake_verification)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "verification", repository, digest
        )
    assert not os.path.lexists(
        repository / launcher.VERIFICATION_RECEIPT_RELATIVE_PATH
    )


@pytest.mark.parametrize(
    "artifact_row",
    launcher.SUCCESS_ARTIFACT_ROWS,
    ids=lambda row: row[0],
)
def test_verification_rejects_resigned_foreign_success_artifact_before_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact_row: tuple,
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_measurement(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        _write_measurement_success(repository)
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_measurement)
    launcher.launch_prelaunch_target_v180r12r4("measurement", repository, digest)

    (
        _artifact_name,
        _mapping_key,
        relative_path,
        _schema,
        domain,
        identity_field,
        _terminal_prefix,
        _fields,
        _cap,
    ) = artifact_row
    artifact_path = repository / relative_path
    document = json.loads(artifact_path.read_text(encoding="utf-8"))
    document["attempt_id"] = "f" * 64
    payload = dict(document)
    payload.pop(identity_field)
    document[identity_field] = hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + _canonical(payload)
    ).hexdigest()
    artifact_path.chmod(0o600)
    artifact_path.write_bytes(_canonical(document))
    artifact_path.chmod(0o400)

    with pytest.raises(launcher.V180r12r4PrelaunchLaunchError):
        launcher.launch_prelaunch_target_v180r12r4(
            "verification", repository, digest
        )
    assert not os.path.lexists(
        repository / launcher.VERIFICATION_ATTEMPT_RELATIVE_PATH
    )


def test_child_stream_cap_is_constant_memory() -> None:
    observation = launcher._StreamObservation()
    observation.add(b"x" * 8192)
    document = observation.document()
    assert document["byte_count"] == 8192
    assert len(bytes.fromhex(document["retained_prefix_hex"])) == 4096
    assert document["retained_prefix_truncated"] is True


def test_partial_attempt_write_still_freezes_typed_launch_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    original_write_once = launcher._write_once

    def fail_after_attempt_create(
        path: Path,
        raw: bytes,
        *,
        publication_token=None,
        publication_fault_injector=None,
    ) -> None:
        if path == repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH:
            def inject(stage: str) -> None:
                if stage == "AFTER_O_EXCL":
                    raise OSError("injected partial attempt fsync failure")

            original_write_once(
                path,
                raw,
                publication_token=publication_token,
                publication_fault_injector=inject,
            )
            return
        original_write_once(
            path,
            raw,
            publication_token=publication_token,
            publication_fault_injector=publication_fault_injector,
        )

    monkeypatch.setattr(launcher, "_write_once", fail_after_attempt_create)
    with pytest.raises(launcher.V180r12r4DurableWriteError) as captured:
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    failure_path = repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    assert isinstance(captured.value.__cause__, OSError)
    assert "partial attempt" in str(captured.value.__cause__)
    assert failure["failure_type"] == "V180r12r4DurableWriteError"
    assert failure["publication_failure_artifact"] == "LAUNCH_ATTEMPT"
    assert failure["publication_failure_stage"] == "AFTER_O_EXCL"
    assert failure["publication_failure_path_created"] is True
    assert failure["publication_failure_completed"] is False
    assert failure["publication_failure_observed_state"] == (
        "PRESENT_PARTIAL_OR_INVALID"
    )
    assert failure["progress_observations"]["attempt"] == {
        "presence": "REGULAR_FILE",
        "mode": 0o400,
        "byte_count": 0,
        "sha256": hashlib.sha256(
            (repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH).read_bytes()
        ).hexdigest(),
    }


def test_concurrent_attempt_lock_loser_does_not_poison_winner_with_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    original_write_once = launcher._write_once

    def lose_attempt_race(path: Path, raw: bytes, **kwargs: object) -> None:
        if path == repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH:
            original_write_once(path, raw, **kwargs)
            raise FileExistsError("concurrent attempt owner")
        original_write_once(path, raw, **kwargs)

    monkeypatch.setattr(launcher, "_write_once", lose_attempt_race)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchReplayForbidden,
        match="concurrently",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    assert (repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH).is_file()
    assert not os.path.lexists(
        repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
    )
    assert not os.path.lexists(
        repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH
    )


def test_watchdog_kills_a_descendant_that_keeps_diagnostic_pipes_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    monkeypatch.setattr(launcher, "WALL_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(launcher, "TERMINATION_GRACE_SECONDS", 0.05)
    child_code = (
        "import os,time\n"
        "pid=os.fork()\n"
        "if pid == 0:\n"
        "    time.sleep(60)\n"
        "else:\n"
        "    print(pid, flush=True)\n"
        "    os._exit(0)\n"
    )
    argv = [
        launcher.PYTHON_EXECUTABLE,
        "-c",
        child_code,
        "measurement",
        str(repository),
        str(tmp_path / "c-pre"),
        str(tmp_path / "manifest.json"),
    ]
    started = time.monotonic()
    return_code, timed_out, stdout, stderr = launcher._run_child(argv, {})
    elapsed = time.monotonic() - started
    assert return_code == 0
    assert timed_out is True
    assert 0 < stdout["byte_count"] <= launcher.CHILD_STREAM_BYTE_CAP
    assert stderr["byte_count"] == 0
    assert elapsed < 2.0


def test_foreign_preexisting_measurement_cgroup_is_observed_but_never_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    manifest = json.loads(
        (repository / launcher.MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    frozen = manifest["frozen_authorization_context"]
    root = Path(frozen["cgroup_parent_fact"]["parent_path"]) / (
        "v180r12r4-" + frozen["campaign_attempt_id"]
    )
    root.mkdir()

    def forbidden_run(*_args, **_kwargs):  # pragma: no cover - forbidden
        raise AssertionError("Popen boundary was crossed")

    monkeypatch.setattr(launcher, "_run_child", forbidden_run)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="existed before Popen",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    assert root.is_dir()
    failure = json.loads(
        (
            repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
        ).read_text(encoding="utf-8")
    )
    rows = failure["measurement_cgroup_cleanup_observations"]
    assert rows[0]["root_state"] == "READ_ERROR"
    assert all(row["ownership_acquired"] is False for row in rows)
    assert all(row["remove_attempted"] is False for row in rows)


def test_owned_measurement_cgroup_cleanup_is_exact_name_and_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "delegated"
    parent.mkdir()
    campaign_attempt_id = "a" * 64
    root = parent / f"v180r12r4-{campaign_attempt_id}"
    root.mkdir()
    (root / "SUPERVISOR").mkdir()
    (root / "WORKER").mkdir()
    parent_fd = os.open(
        parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    killed: list[int] = []
    monkeypatch.setattr(
        launcher,
        "_read_cgroup_control_at",
        lambda _fd, name: "populated 0\n" if name == "cgroup.events" else "",
    )
    monkeypatch.setattr(
        launcher, "_write_cgroup_kill", lambda descriptor: killed.append(descriptor)
    )
    try:
        cleanup, after, required = launcher._cleanup_owned_measurement_cgroup(
            parent_fd=parent_fd,
            campaign_attempt_id=campaign_attempt_id,
            hard_deadline_ns=(
                time.clock_gettime_ns(time.CLOCK_MONOTONIC)
                + launcher.NANOSECONDS_PER_SECOND
            ),
            ownership_acquired=True,
        )
    finally:
        os.close(parent_fd)
    assert required is True
    assert len(killed) == 1
    assert cleanup["kill_attempted"] is True
    assert cleanup["kill_succeeded"] is True
    assert cleanup["wait_empty_succeeded"] is True
    assert cleanup["remove_succeeded"] is True
    assert cleanup["residual_tree_or_process_possible"] is False
    assert after["root_state"] == "ABSENT"
    assert not root.exists()


def test_launch_failure_coexistence_forbids_success_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_run(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        _write_measurement_success(repository)
        _write_0400(
            repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH,
            b"{}",
        )
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_run)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    assert not os.path.lexists(
        repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH
    )


def test_measurement_child_leaving_runtime_cas_cannot_receive_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_run(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        _write_measurement_success(repository)
        (repository / launcher.RUNTIME_CAS_ROOT_RELATIVE_PATH).mkdir()
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_run)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    assert not os.path.lexists(
        repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH
    )
    assert os.path.lexists(
        repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
    )


def test_launch_failure_write_secondary_never_replaces_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    original_write_once = launcher._write_once

    def fail_child(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        raise ValueError("primary bootstrap failure")

    def fail_failure_write(path: Path, raw: bytes, **kwargs: object) -> None:
        if path == repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH:
            raise OSError("secondary failure write")
        original_write_once(path, raw, **kwargs)

    monkeypatch.setattr(launcher, "_run_child", fail_child)
    monkeypatch.setattr(launcher, "_write_once", fail_failure_write)
    with pytest.raises(ValueError, match="primary bootstrap") as captured:
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    assert isinstance(captured.value.__cause__, OSError)
    assert "secondary failure write" in str(captured.value.__cause__)


def test_hostile_traceback_access_and_with_traceback_cannot_replace_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    original_write_once = launcher._write_once

    class HostilePrimary(ValueError):
        def __getattribute__(self, name: str):
            if name in {"__traceback__", "with_traceback"}:
                raise RuntimeError("hostile traceback accessor")
            return ValueError.__getattribute__(self, name)

        def with_traceback(self, _traceback):
            raise RuntimeError("hostile with_traceback")

    def fail_child(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        raise HostilePrimary("preserve this primary")

    def fail_failure_write(path: Path, raw: bytes, **kwargs: object) -> None:
        if path == repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH:
            raise OSError("typed failure secondary")
        original_write_once(path, raw, **kwargs)

    monkeypatch.setattr(launcher, "_run_child", fail_child)
    monkeypatch.setattr(launcher, "_write_once", fail_failure_write)
    try:
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    except BaseException as captured:
        assert type(captured) is HostilePrimary
        assert str(captured) == "preserve this primary"
        cause = BaseException.__getattribute__(captured, "__cause__")
        assert type(cause) is OSError
        assert str(cause) == "typed failure secondary"
    else:  # pragma: no cover - the test requires one preserved primary
        raise AssertionError("hostile primary was not raised")


def test_resigned_foreign_measurement_receipt_is_rejected_before_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_measurement(
        _argv: list[str], _environment: dict[str, str], _pass_fds=(), *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        _write_measurement_success(repository)
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_measurement)
    launcher.launch_prelaunch_target_v180r12r4("measurement", repository, digest)
    receipt_path = repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt.pop("launch_receipt_id")
    receipt["foreign_resigned_field"] = True
    receipt["launch_receipt_id"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    receipt_path.chmod(0o600)
    receipt_path.write_bytes(_canonical(receipt))
    receipt_path.chmod(0o400)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="schema changed",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "verification", repository, digest
        )
    assert not os.path.lexists(
        repository / launcher.VERIFICATION_ATTEMPT_RELATIVE_PATH
    )


def test_materialization_terminal_resign_cannot_weaken_write_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _digest = _materialized_repository(tmp_path, monkeypatch)
    terminal_path = repository / launcher.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    terminal.pop("materialization_terminal_id")
    terminal["file_and_directory_fsync_required"] = False
    terminal["materialization_terminal_id"] = hashlib.sha256(
        _canonical(terminal)
    ).hexdigest()
    terminal_raw = _canonical(terminal)
    terminal_path.chmod(0o600)
    terminal_path.write_bytes(terminal_raw)
    terminal_path.chmod(0o400)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="boundary changed",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement",
            repository,
            hashlib.sha256(terminal_raw).hexdigest(),
        )


def test_resigned_manifest_cannot_weaken_seqpacket_effective_buffer_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _digest = _materialized_repository(tmp_path, monkeypatch)
    manifest_path = repository / launcher.MANIFEST_RELATIVE_PATH
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["internal_target_contract"][
        "sock_seqpacket_effective_min_bytes"
    ] -= 1
    manifest_raw = _canonical(manifest)
    manifest_path.chmod(0o600)
    manifest_path.write_bytes(manifest_raw)
    manifest_path.chmod(0o400)

    terminal_path = repository / launcher.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    terminal.pop("materialization_terminal_id")
    terminal["launch_manifest"] = _fact(
        launcher.MANIFEST_RELATIVE_PATH,
        manifest_raw,
    )
    terminal["materialization_terminal_id"] = hashlib.sha256(
        _canonical(terminal)
    ).hexdigest()
    terminal_raw = _canonical(terminal)
    terminal_path.chmod(0o600)
    terminal_path.write_bytes(terminal_raw)
    terminal_path.chmod(0o400)

    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="internal target contract changed",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement",
            repository,
            hashlib.sha256(terminal_raw).hexdigest(),
        )
    assert not os.path.lexists(
        repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH
    )


def test_resigned_retained_bootstrap_cannot_disconnect_c_pre_git_blob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _digest = _materialized_repository(tmp_path, monkeypatch)
    terminal_path = repository / launcher.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    terminal.pop("materialization_terminal_id")
    terminal["retained_bootstrap"]["sha256"] = "f" * 64
    terminal["materialization_terminal_id"] = hashlib.sha256(
        _canonical(terminal)
    ).hexdigest()
    terminal_raw = _canonical(terminal)
    terminal_path.chmod(0o600)
    terminal_path.write_bytes(terminal_raw)
    terminal_path.chmod(0o400)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="differs from its C_pre Git blob",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement",
            repository,
            hashlib.sha256(terminal_raw).hexdigest(),
        )


def test_materialization_failure_sibling_forbids_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    failure = repository / launcher.MATERIALIZATION_FAILURE_RELATIVE_PATH
    _write_0400(failure, b"{}")
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchReplayForbidden,
        match="materialization failure",
    ):
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    assert not os.path.lexists(
        repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH
    )


def test_process_group_is_terminated_even_after_leader_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[int, int]] = []

    def fake_killpg(pid: int, sig: int) -> None:
        events.append((pid, sig))
        if sig == 0:
            raise ProcessLookupError

    monkeypatch.setattr(launcher.os, "killpg", fake_killpg)
    launcher._terminate_process_group(
        SimpleNamespace(pid=811, poll=lambda: 0),
        hard_deadline_ns=(
            time.clock_gettime_ns(time.CLOCK_MONOTONIC)
            + launcher.NANOSECONDS_PER_SECOND
        ),
    )
    assert events == [(811, launcher.signal.SIGTERM), (811, 0)]


def test_startup_rejects_wrong_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    retained = repository / launcher.LAUNCHER_RELATIVE_PATH
    retained.parent.mkdir(parents=True)
    retained.write_bytes(SCRIPT.read_bytes())
    monkeypatch.setattr(launcher, "__file__", str(retained))
    monkeypatch.setattr(launcher.sys, "executable", launcher.PYTHON_EXECUTABLE)
    monkeypatch.setattr(launcher.sys, "pycache_prefix", launcher.PYCACHE_PREFIX)
    monkeypatch.setattr(launcher.sys, "dont_write_bytecode", True)
    monkeypatch.setattr(
        launcher.sys,
        "flags",
        SimpleNamespace(
            isolated=1,
            no_site=1,
            no_user_site=1,
            ignore_environment=1,
            dont_write_bytecode=1,
        ),
    )
    expected = [
        *launcher.ISOLATED_ARGV_PREFIX,
        str(retained),
        "service-entry",
        "measurement",
        str(repository),
    ]
    monkeypatch.setattr(launcher.sys, "orig_argv", expected)
    monkeypatch.setattr(
        launcher.sys,
        "argv",
        expected[len(launcher.ISOLATED_ARGV_PREFIX) :],
    )
    monkeypatch.setattr(
        launcher.os,
        "environ",
        {
            launcher.MATERIALIZATION_TERMINAL_SHA256_ENV: "a" * 64,
            "LC_CTYPE": "C.UTF-8",
        },
    )
    monkeypatch.chdir(repository)
    assert launcher._require_launcher_startup(
        "service-entry", "measurement", repository
    ) == "a" * 64
    monkeypatch.chdir(elsewhere)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="working directory",
    ):
        launcher._require_launcher_startup(
            "service-entry", "measurement", repository
        )


def test_dual_target_service_contract_freezes_outer_dispatch_and_inner_entry() -> None:
    contract = launcher._production_systemd_service_contract()
    assert contract == protocol.production_systemd_service_contract_v180r12r4()
    predecessor = {
        "failed_predecessor_freeze_id": (
            "2f71e97fd2133c7983a400b5f536fe87740aa08c551580d62556aae5dcea496b"
        ),
        "failed_inner_launch_failure_id": (
            "46a3d92a70424c296e0137380cdb98f99f11b47b565dce3175baeab8b3546a67"
        ),
        "failed_outer_service_failure_id": (
            "a221f8d37ca354b7e1a753708d99229086ef6128fedd5cbf9879c89871846185"
        ),
        "repair_scope": "SOCKET_BUFFER_CAPABILITY_AND_T3_DIAGNOSTIC_CONFORMANCE",
    }
    assert [row["target"] for row in contract["target_rows"]] == [
        "measurement",
        "verification",
    ]
    assert {
        row["target"]: (row["token"], row["unit_name"])
        for row in contract["target_rows"]
    } == {
        target: (
            launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS[target][1],
            launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS[target][2],
        )
        for target in ("measurement", "verification")
    }
    for row in contract["target_rows"]:
        target = row["target"]
        assert row["token_input"] == {
            **predecessor,
            "purpose": target.upper(),
        }
        outer = row["outer_dispatch_argv_template"]
        inner = row["launcher_command_template"]
        assert row["outer_dispatch_cwd_template"] == "{repository_root}"
        assert row["service_working_directory_template"] == "{repository_root}"
        assert outer[:2] == ["/usr/bin/env", "-i"]
        assert inner[:2] == ["/usr/bin/env", "-i"]
        assert outer[-3:] == ["dispatch", target, "{repository_root}"]
        assert inner[-3:] == ["service-entry", target, "{repository_root}"]
        assert row["systemd_run_argv_template"][-len(inner) :] == inner
        assert "--unit=" + row["unit_name"] in row[
            "systemd_run_argv_template"
        ]
        assert "--working-directory={repository_root}" in row[
            "systemd_run_argv_template"
        ]
        delegate_index = row["systemd_run_argv_template"].index(
            "--property=Delegate=yes"
        )
        assert row["systemd_run_argv_template"][delegate_index + 1] == (
            "--property=UMask=0077"
        )
    assert contract["umask"] == "0077"
    assert contract[
        "outer_dispatch_process_cwd_must_equal_repository_root"
    ] is True
    assert contract[
        "service_working_directory_must_equal_repository_root"
    ] is True
    assert set(launcher.SERVICE_LAUNCH_ATTEMPT_FIELDS) == set(
        protocol.PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_FIELDS
    )
    assert set(launcher.SERVICE_LAUNCH_RECEIPT_FIELDS) == set(
        protocol.PRELAUNCH_SERVICE_LAUNCH_RECEIPT_FIELDS
    )
    assert set(launcher.SERVICE_LAUNCH_FAILURE_FIELDS) == set(
        protocol.PRELAUNCH_SERVICE_LAUNCH_FAILURE_FIELDS
    )
    assert launcher.SERVICE_LAUNCH_PUBLICATION_STAGES == (
        protocol.PRELAUNCH_SERVICE_LAUNCH_PUBLICATION_STAGES
    )
    prelaunch = protocol.prelaunch_contract_v180r12r4()
    assert prelaunch["inner_launch_publication_stages"] == list(
        launcher.SERVICE_LAUNCH_PUBLICATION_STAGES
    )
    assert prelaunch["inner_launch_publication_states"] == list(
        launcher.SERVICE_LAUNCH_PUBLICATION_STATES
    )
    assert set(prelaunch["inner_launch_failure_publication_fields"]) == (
        launcher._LAUNCH_FAILURE_PUBLICATION_KEYS
    )


def test_receipt_publication_claims_are_scoped_to_recovery_outcome() -> None:
    launcher_source = SCRIPT.read_text(encoding="utf-8")
    protocol_source = (
        ROOT
        / "src/acfqp/construction_k7_campaign_measurement_protocol_v180r12r4.py"
    ).read_text(encoding="utf-8")
    combined = launcher_source + protocol_source
    assert (
        "outer_service_launch_receipt_or_failure_is_" + "exactly_one"
    ) not in combined
    assert (
        '"launch_receipt_and_failure_' + 'mutually_exclusive"'
    ) not in combined
    assert (
        "writes exactly one terminal launch " + "receipt or"
    ) not in combined
    assert "normal_or_recovered_success_is_receipt_only" in protocol_source
    assert "ordinary_pre_receipt_failure_is_failure_only" in protocol_source
    assert "unrecoverable_receipt_publication_allows_typed_failure_coexistence_" in (
        protocol_source
    )


@pytest.mark.parametrize("target", ("measurement", "verification"))
def test_t1_producer_selects_exact_direct_service_and_opens_fd252(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    repository = (tmp_path / ("t1-" + target)).absolute()
    repository.mkdir()
    frozen = _frozen_authorization_context(repository, monkeypatch)
    cgroup = frozen["cgroup_parent_fact"]
    parent = Path(cgroup["parent_path"])
    unit_name = launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS[target][2]
    service = parent / unit_name
    service.mkdir()
    (parent / "cgroup.procs").write_text("", encoding="ascii")
    (service / "cgroup.procs").write_text(
        str(os.getpid()) + "\n", encoding="ascii"
    )
    expected_membership = "0::/app.slice/" + unit_name
    monkeypatch.setattr(
        launcher, "_self_cgroup_membership", lambda: expected_membership
    )
    descriptors: tuple[int, int, int] = ()
    try:
        descriptors, t1 = (
            launcher._prepare_and_observe_production_runtime_placement_t1(
                target=target, frozen_context=frozen
            )
        )
        assert descriptors == (
            launcher.DELEGATED_CGROUP_PARENT_FD,
            launcher.CGROUP2_MOUNT_FD,
            launcher.SOURCE_SYSTEMD_SERVICE_FD,
        )
        assert set(t1) == set(protocol.PRODUCTION_RUNTIME_PLACEMENT_T1_FIELDS)
        assert t1["target"] == target
        assert t1["unit_name"] == unit_name
        assert t1["source_membership"] == expected_membership
        assert t1["expected_source_membership"] == expected_membership
        assert t1["source_service_fd_fact"]["fd"] == 252
        assert t1["source_service_fd_fact"]["path"] == str(service)
        assert t1["self_pid"] == os.getpid()
        assert t1["self_pid_in_source_cgroup_procs"] is True
        assert t1["parent_cgroup_procs_o_wronly_openable"] is True
        assert t1["planned_measurement_root_absent"] is True
        assert t1["t1_complete_before_child_popen"] is True
    finally:
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass


def test_outer_service_dispatch_is_injected_bounded_and_exactly_joined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    calls: list[tuple[list[str], dict[str, str], tuple[int, ...], Path]] = []
    inner: dict[str, dict[str, object]] = {}

    def fake_process(
        argv: list[str],
        environment: dict[str, str],
        pass_fds: tuple[int, ...],
        *,
        hard_deadline_ns: int,
        cwd: Path,
    ) -> tuple[int, bool, dict[str, object], dict[str, object]]:
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        calls.append((list(argv), dict(environment), pass_fds, cwd))
        if argv[0] == "/usr/bin/systemd-run":
            attempt, receipt = _write_inner_launch_receipt(
                repository, digest, "measurement"
            )
            inner.update(attempt=attempt, receipt=receipt)
            return (
                0,
                False,
                launcher._empty_stream_document(),
                launcher._empty_stream_document(),
            )
        assert argv == [
            launcher.SYSTEMCTL_EXECUTABLE,
            "--user",
            "show",
            "--property=LoadState",
            "--value",
            launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS["measurement"][2],
        ]
        return 0, False, _stream(b"not-found\n"), _stream(b"")

    receipt = launcher.dispatch_production_service_v180r12r4(
        "measurement", repository, digest, process_runner=fake_process
    )
    attempt_path = repository / launcher.MEASUREMENT_SERVICE_ATTEMPT_RELATIVE_PATH
    receipt_path = repository / launcher.MEASUREMENT_SERVICE_RECEIPT_RELATIVE_PATH
    failure_path = repository / launcher.MEASUREMENT_SERVICE_FAILURE_RELATIVE_PATH
    outer_attempt = json.loads(attempt_path.read_bytes())
    assert len(calls) == 3
    expected_invocation = launcher._production_systemd_service_invocation(
        repository, digest, "measurement"
    )
    assert calls[1] == (
        expected_invocation["systemd_run_argv"],
        launcher._systemd_client_environment_v180r12r4(),
        (),
        repository,
    )
    assert calls[0][0] == calls[2][0] == [
        launcher.SYSTEMCTL_EXECUTABLE,
        "--user",
        "show",
        "--property=LoadState",
        "--value",
        launcher.PRODUCTION_TRANSIENT_SERVICE_ROWS["measurement"][2],
    ]
    assert calls[0][1:] == calls[2][1:] == (
        launcher._systemd_client_environment_v180r12r4(),
        (),
        repository,
    )
    assert set(outer_attempt) == launcher.SERVICE_LAUNCH_ATTEMPT_FIELDS
    assert set(receipt) == launcher.SERVICE_LAUNCH_RECEIPT_FIELDS
    assert outer_attempt["pre_attempt_unit_absence_observation"][
        "unit_absent_after_wait_collect"
    ] is True
    assert receipt["service_launch_attempt_id"] == outer_attempt[
        "service_launch_attempt_id"
    ]
    assert receipt["inner_launch_attempt_id"] == inner["attempt"][
        "launch_attempt_id"
    ]
    assert receipt["inner_launch_terminal_id"] == inner["receipt"][
        "launch_receipt_id"
    ]
    assert receipt["exact_attempt_terminal_join"] is True
    assert receipt["collected_unit_absence_observation"][
        "unit_absent_after_wait_collect"
    ] is True
    assert receipt_path.is_file()
    assert not failure_path.exists()


def test_outer_service_preentry_failure_closes_once_and_replay_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_process(
        argv: list[str],
        _environment: dict[str, str],
        _pass_fds: tuple[int, ...],
        *,
        hard_deadline_ns: int,
        cwd: Path,
    ) -> tuple[int, bool, dict[str, object], dict[str, object]]:
        assert cwd == repository
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        if argv[0] == "/usr/bin/systemd-run":
            return 1, False, _stream(b""), _stream(b"entry failed\n")
        return 0, False, _stream(b"not-found\n"), _stream(b"")

    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="exact inner receipt",
    ):
        launcher.dispatch_production_service_v180r12r4(
            "measurement", repository, digest, process_runner=fake_process
        )
    attempt_path = repository / launcher.MEASUREMENT_SERVICE_ATTEMPT_RELATIVE_PATH
    receipt_path = repository / launcher.MEASUREMENT_SERVICE_RECEIPT_RELATIVE_PATH
    failure_path = repository / launcher.MEASUREMENT_SERVICE_FAILURE_RELATIVE_PATH
    failure = json.loads(failure_path.read_bytes())
    assert attempt_path.is_file()
    assert not receipt_path.exists()
    assert set(failure) == launcher.SERVICE_LAUNCH_FAILURE_FIELDS
    assert failure["systemd_run_return_code"] == 1
    assert failure["systemd_run_stderr"] == _stream(b"entry failed\n")
    assert failure["inner_launch_terminal_kind"] == "ABSENT"
    assert failure["exact_attempt_terminal_join"] is False
    assert all(
        failure[name] is None
        for name in {
            "publication_failure_artifact",
            "publication_failure_stage",
            "publication_failure_path_created",
            "publication_failure_completed",
            "publication_failure_observed_state",
        }
    )
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchReplayForbidden,
        match="triad already exists",
    ):
        launcher.dispatch_production_service_v180r12r4(
            "measurement", repository, digest, process_runner=fake_process
        )


def test_outer_service_foreign_unit_is_no_spend_before_attempt_o_excl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    calls: list[list[str]] = []

    def foreign_unit(
        argv: list[str],
        _environment: dict[str, str],
        _pass_fds: tuple[int, ...],
        *,
        hard_deadline_ns: int,
        cwd: Path,
    ) -> tuple[int, bool, dict[str, object], dict[str, object]]:
        assert cwd == repository
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        calls.append(list(argv))
        return 0, False, _stream(b"loaded\n"), _stream(b"")

    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="already exists before outer ATTEMPT",
    ):
        launcher.dispatch_production_service_v180r12r4(
            "measurement", repository, digest, process_runner=foreign_unit
        )
    assert len(calls) == 1 and calls[0][0] == launcher.SYSTEMCTL_EXECUTABLE
    paths = launcher._service_state_paths(repository, "measurement")
    assert all(
        not os.path.lexists(paths[name])
        for name in ("service_attempt", "service_receipt", "service_failure")
    )


def test_tracked_publication_partial_write_sets_path_created_not_completed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "partial.json"
    raw = b'{"publication":"partial"}\n'
    token = launcher.ServiceLaunchPublicationTokenV180R12R4(
        "SERVICE_LAUNCH_FAILURE"
    )
    token.started = True
    original_write = launcher.os.write
    writes = 0

    def partial_then_fail(descriptor: int, view: object) -> int:
        nonlocal writes
        writes += 1
        if writes == 1:
            prefix = bytes(view)[:5]
            assert original_write(descriptor, prefix) == len(prefix)
            return len(prefix)
        raise OSError(errno.EIO, "injected partial publication")

    monkeypatch.setattr(launcher.os, "write", partial_then_fail)
    with pytest.raises(launcher.V180r12r4DurableWriteError) as captured:
        launcher._write_once(path, raw, publication_token=token)
    assert captured.value.path_created is True
    assert captured.value.completed is False
    assert captured.value.stage == "AFTER_O_EXCL"
    assert token.path_created is True and token.completed is False
    assert path.read_bytes() == raw[:5]


def test_tracked_publication_full_write_then_fsync_error_remains_classifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "full-before-fsync-error.json"
    raw = b'{"publication":"full"}\n'
    token = launcher.ServiceLaunchPublicationTokenV180R12R4(
        "SERVICE_LAUNCH_FAILURE"
    )
    token.started = True
    original_fsync = launcher.os.fsync
    calls = 0

    def fail_first_fsync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError(errno.EIO, "injected post-full-write fsync")
        original_fsync(descriptor)

    monkeypatch.setattr(launcher.os, "fsync", fail_first_fsync)
    with pytest.raises(launcher.V180r12r4DurableWriteError) as captured:
        launcher._write_once(path, raw, publication_token=token)
    assert captured.value.path_created is True
    assert captured.value.completed is False
    assert captured.value.stage == "AFTER_FULL_WRITE"
    assert path.read_bytes() == raw


def test_tracked_publication_readback_error_keeps_exact_bytes_but_not_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "readback-error.json"
    raw = b'{"publication":"readback"}\n'
    token = launcher.ServiceLaunchPublicationTokenV180R12R4(
        "SERVICE_LAUNCH_FAILURE"
    )
    token.started = True
    original_stable_read = launcher._stable_read
    injected = False

    def fail_readback(observed: Path, *args: object, **kwargs: object) -> bytes:
        nonlocal injected
        if observed == path and not injected:
            injected = True
            raise OSError(errno.EIO, "injected exact readback")
        return original_stable_read(observed, *args, **kwargs)

    monkeypatch.setattr(launcher, "_stable_read", fail_readback)
    with pytest.raises(launcher.V180r12r4DurableWriteError) as captured:
        launcher._write_once(path, raw, publication_token=token)
    assert captured.value.path_created is True
    assert captured.value.completed is False
    assert captured.value.stage == "AFTER_PARENT_FSYNC"
    assert path.read_bytes() == raw


def test_attempt_readback_failure_writes_exact_typed_outer_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    attempt_path = (
        repository / launcher.MEASUREMENT_SERVICE_ATTEMPT_RELATIVE_PATH
    )
    original_stable_read = launcher._stable_read
    injected = False

    def fail_attempt_readback(
        observed: Path, *args: object, **kwargs: object
    ) -> bytes:
        nonlocal injected
        if observed == attempt_path and not injected:
            injected = True
            raise OSError(errno.EIO, "injected ATTEMPT readback")
        return original_stable_read(observed, *args, **kwargs)

    def absent_unit(
        _argv: list[str],
        _environment: dict[str, str],
        _pass_fds: tuple[int, ...],
        *,
        hard_deadline_ns: int,
        cwd: Path,
    ) -> tuple[int, bool, dict[str, object], dict[str, object]]:
        assert cwd == repository
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        return 0, False, _stream(b"not-found\n"), _stream(b"")

    monkeypatch.setattr(launcher, "_stable_read", fail_attempt_readback)
    with pytest.raises(launcher.V180r12r4DurableWriteError) as captured:
        launcher.dispatch_production_service_v180r12r4(
            "measurement", repository, digest, process_runner=absent_unit
        )
    failure_path = (
        repository / launcher.MEASUREMENT_SERVICE_FAILURE_RELATIVE_PATH
    )
    failure = json.loads(failure_path.read_bytes())
    assert captured.value.path_created is True
    assert captured.value.completed is False
    assert captured.value.artifact == "SERVICE_LAUNCH_ATTEMPT"
    assert captured.value.stage == "AFTER_PARENT_FSYNC"
    assert failure["publication_failure_artifact"] == (
        "SERVICE_LAUNCH_ATTEMPT"
    )
    assert failure["publication_failure_stage"] == "AFTER_PARENT_FSYNC"
    assert failure["publication_failure_path_created"] is True
    assert failure["publication_failure_completed"] is False
    assert failure["publication_failure_observed_state"] == "PRESENT_EXACT"
    assert launcher._service_launch_publication_observation(
        repository, "measurement"
    ) == {
        "attempt": "PRESENT_EXACT",
        "receipt": "ABSENT",
        "failure": "PRESENT_EXACT",
    }


def test_outer_exact_receipt_readback_failure_is_durably_recovered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    receipt_path = (
        repository / launcher.MEASUREMENT_SERVICE_RECEIPT_RELATIVE_PATH
    )
    original_stable_read = launcher._stable_read
    original_recover = launcher._recover_exact_receipt_publication
    injected = False
    recovered: list[Path] = []

    def fail_receipt_readback(
        observed: Path, *args: object, **kwargs: object
    ) -> bytes:
        nonlocal injected
        if observed == receipt_path and not injected:
            injected = True
            raise OSError(errno.EIO, "injected RECEIPT readback")
        return original_stable_read(observed, *args, **kwargs)

    def successful_service(
        argv: list[str],
        _environment: dict[str, str],
        _pass_fds: tuple[int, ...],
        *,
        hard_deadline_ns: int,
        cwd: Path,
    ) -> tuple[int, bool, dict[str, object], dict[str, object]]:
        assert cwd == repository
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        if argv[0] == "/usr/bin/systemd-run":
            _write_inner_launch_receipt(repository, digest, "measurement")
            return 0, False, _stream(b""), _stream(b"")
        return 0, False, _stream(b"not-found\n"), _stream(b"")

    monkeypatch.setattr(launcher, "_stable_read", fail_receipt_readback)
    def record_recovery(path: Path, raw: bytes) -> None:
        original_recover(path, raw)
        recovered.append(path)

    monkeypatch.setattr(
        launcher, "_recover_exact_receipt_publication", record_recovery
    )
    receipt = launcher.dispatch_production_service_v180r12r4(
        "measurement", repository, digest, process_runner=successful_service
    )
    failure_path = (
        repository / launcher.MEASUREMENT_SERVICE_FAILURE_RELATIVE_PATH
    )
    assert not failure_path.exists()
    assert receipt["success"] is True
    assert receipt_path in recovered
    assert launcher._service_launch_publication_observation(
        repository, "measurement"
    ) == {
        "attempt": "PRESENT_EXACT",
        "receipt": "PRESENT_EXACT",
        "failure": "ABSENT",
    }


def test_partial_failure_publication_is_classified_on_original_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    failure_path = (
        repository / launcher.MEASUREMENT_SERVICE_FAILURE_RELATIVE_PATH
    )
    original_write_once = launcher._write_once

    def partial_failure_write(
        path: Path,
        raw: bytes,
        *,
        publication_token=None,
    ) -> None:
        if path != failure_path:
            original_write_once(
                path, raw, publication_token=publication_token
            )
            return
        assert publication_token is not None and publication_token.started
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o400,
        )
        try:
            publication_token.path_created = True
            publication_token.stage = "AFTER_O_EXCL"
            assert os.write(descriptor, raw[:7]) == 7
            os.fchmod(descriptor, 0o400)
        finally:
            os.close(descriptor)
        durable = launcher.V180r12r4DurableWriteError(
            path, publication_token
        )
        raise durable from OSError(errno.EIO, "injected partial FAILURE")

    def failed_service(
        argv: list[str],
        _environment: dict[str, str],
        _pass_fds: tuple[int, ...],
        *,
        hard_deadline_ns: int,
        cwd: Path,
    ) -> tuple[int, bool, dict[str, object], dict[str, object]]:
        assert cwd == repository
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        if argv[0] == "/usr/bin/systemd-run":
            return 1, False, _stream(b""), _stream(b"entry failed\n")
        return 0, False, _stream(b"not-found\n"), _stream(b"")

    monkeypatch.setattr(launcher, "_write_once", partial_failure_write)
    with pytest.raises(launcher.V180r12r4PrelaunchLaunchError) as captured:
        launcher.dispatch_production_service_v180r12r4(
            "measurement", repository, digest, process_runner=failed_service
        )
    assert captured.value.service_launch_publication_observation == {
        "attempt": "PRESENT_EXACT",
        "receipt": "ABSENT",
        "failure": "PRESENT_PARTIAL_OR_INVALID",
    }
    assert isinstance(
        captured.value.__cause__, launcher.V180r12r4DurableWriteError
    )
    assert captured.value.__cause__.observed_state == (
        "PRESENT_PARTIAL_OR_INVALID"
    )


def test_unrecoverable_exact_outer_receipt_writes_failure_and_consumer_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    receipt_path = repository / launcher.MEASUREMENT_SERVICE_RECEIPT_RELATIVE_PATH
    original_stable_read = launcher._stable_read
    original_recover = launcher._recover_exact_receipt_publication
    injected = False

    def fail_receipt_readback(
        observed: Path, *args: object, **kwargs: object
    ) -> bytes:
        nonlocal injected
        if observed == receipt_path and not injected:
            injected = True
            raise OSError(errno.EIO, "outer receipt publication readback")
        return original_stable_read(observed, *args, **kwargs)

    def reject_outer_recovery(path: Path, raw: bytes) -> None:
        if path == receipt_path:
            raise OSError(errno.EIO, "outer receipt recovery failed")
        original_recover(path, raw)

    def successful_service(
        argv: list[str],
        _environment: dict[str, str],
        _pass_fds: tuple[int, ...],
        *,
        hard_deadline_ns: int,
        cwd: Path,
    ) -> tuple[int, bool, dict[str, object], dict[str, object]]:
        assert cwd == repository
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        if argv[0] == "/usr/bin/systemd-run":
            _write_inner_launch_receipt(repository, digest, "measurement")
            return 0, False, _stream(b""), _stream(b"")
        return 0, False, _stream(b"not-found\n"), _stream(b"")

    monkeypatch.setattr(launcher, "_stable_read", fail_receipt_readback)
    monkeypatch.setattr(
        launcher, "_recover_exact_receipt_publication", reject_outer_recovery
    )
    with pytest.raises(launcher.V180r12r4DurableWriteError) as captured:
        launcher.dispatch_production_service_v180r12r4(
            "measurement", repository, digest, process_runner=successful_service
        )
    failure_path = repository / launcher.MEASUREMENT_SERVICE_FAILURE_RELATIVE_PATH
    assert receipt_path.is_file() and failure_path.is_file()
    failure = json.loads(failure_path.read_bytes())
    assert failure["publication_failure_artifact"] == "SERVICE_LAUNCH_RECEIPT"
    assert failure["publication_failure_stage"] == "AFTER_PARENT_FSYNC"
    assert failure["publication_failure_observed_state"] == "PRESENT_EXACT"
    assert captured.value.publication_recovery_error_type == "OSError"
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchReplayForbidden,
        match="successful measurement service predecessor",
    ):
        launcher._require_successful_measurement_service_launch_v180r12r4(
            repository, digest
        )


@pytest.mark.parametrize(
    "artifact",
    (
        "LAUNCH_ATTEMPT",
        "LAUNCH_RECEIPT",
        "LAUNCH_FAILURE",
        "SERVICE_LAUNCH_ATTEMPT",
        "SERVICE_LAUNCH_RECEIPT",
        "SERVICE_LAUNCH_FAILURE",
    ),
)
@pytest.mark.parametrize("stage", launcher.SERVICE_LAUNCH_PUBLICATION_STAGES)
def test_every_launch_publication_checkpoint_preserves_exact_stage(
    tmp_path: Path, artifact: str, stage: str
) -> None:
    path = tmp_path / f"{artifact}-{stage}.json"
    raw = b'{"publication":"checkpoint"}\n'
    token = launcher.ServiceLaunchPublicationTokenV180R12R4(artifact)
    token.started = True

    def inject(observed_stage: str) -> None:
        if observed_stage == stage:
            raise OSError(errno.EIO, f"injected {artifact} {stage}")

    with pytest.raises(launcher.V180r12r4DurableWriteError) as captured:
        launcher._write_once(
            path,
            raw,
            publication_token=token,
            publication_fault_injector=inject,
        )
    error = captured.value
    assert error.artifact == artifact
    assert error.stage == stage
    assert error.completed is False
    assert error.recovered is False
    assert error.path_created is (
        stage not in {"BEFORE_PARENT_OPEN", "BEFORE_O_EXCL"}
    )
    assert isinstance(error.__cause__, OSError)
    assert error.__cause__.errno == errno.EIO
    assert os.path.lexists(path) is error.path_created
    if stage in {
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_PARENT_FSYNC",
        "AFTER_READBACK",
    }:
        assert path.read_bytes() == raw


def test_receipt_recovery_rejects_exact_byte_inode_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "receipt.json"
    displaced = tmp_path / "displaced-receipt.json"
    raw = b'{"receipt":"exact-bytes"}\n'
    _write_0400(path, raw)
    original_fsync = launcher.os.fsync
    swapped = False

    def swap_after_open(descriptor: int) -> None:
        nonlocal swapped
        if not swapped:
            swapped = True
            path.rename(displaced)
            _write_0400(path, raw)
        original_fsync(descriptor)

    monkeypatch.setattr(launcher.os, "fsync", swap_after_open)
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="inode changed",
    ):
        launcher._recover_exact_receipt_publication(path, raw)
    assert path.read_bytes() == displaced.read_bytes() == raw
    assert path.stat().st_ino != displaced.stat().st_ino


def test_receipt_recovery_rejects_same_inode_overwrite_after_first_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "receipt.json"
    raw = b'{"receipt":"exact-bytes"}\n'
    replacement = b'{"receipt":"other-byte!"}\n'
    assert len(replacement) == len(raw)
    _write_0400(path, raw)
    original_fsync = launcher.os.fsync
    calls = 0

    def overwrite_before_parent_fsync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            path.chmod(0o600)
            path.write_bytes(replacement)
            path.chmod(0o400)
        original_fsync(descriptor)

    monkeypatch.setattr(launcher.os, "fsync", overwrite_before_parent_fsync)
    with pytest.raises(launcher.V180r12r4PrelaunchLaunchError):
        launcher._recover_exact_receipt_publication(path, raw)
    assert path.read_bytes() == replacement


def test_inner_exact_receipt_readback_failure_is_durably_recovered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    receipt_path = repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH
    original_stable_read = launcher._stable_read
    original_recover = launcher._recover_exact_receipt_publication
    injected = False
    recovered: list[Path] = []

    def fail_receipt_readback(
        observed: Path, *args: object, **kwargs: object
    ) -> bytes:
        nonlocal injected
        if observed == receipt_path and not injected:
            injected = True
            raise OSError(errno.EIO, "injected inner RECEIPT readback")
        return original_stable_read(observed, *args, **kwargs)

    def fake_run(
        _argv: list[str],
        _environment: dict[str, str],
        _pass_fds=(),
        *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        _write_measurement_success(repository)
        empty = launcher._empty_stream_document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_run)
    monkeypatch.setattr(launcher, "_stable_read", fail_receipt_readback)
    def record_recovery(path: Path, raw: bytes) -> None:
        original_recover(path, raw)
        recovered.append(path)

    monkeypatch.setattr(
        launcher, "_recover_exact_receipt_publication", record_recovery
    )
    receipt = launcher.launch_prelaunch_target_v180r12r4(
        "measurement", repository, digest
    )
    assert receipt["success"] is True
    assert receipt_path in recovered
    assert receipt_path.is_file()
    assert not os.path.lexists(
        repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
    )


def test_inner_failure_partial_publication_preserves_primary_and_classifies_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    failure_path = repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
    original_write_once = launcher._write_once

    def fail_child(*_args: object, **_kwargs: object):
        raise ValueError("primary inner child failure")

    def partial_failure_write(
        path: Path,
        raw: bytes,
        *,
        publication_token=None,
        publication_fault_injector=None,
    ) -> None:
        if path != failure_path:
            original_write_once(
                path,
                raw,
                publication_token=publication_token,
                publication_fault_injector=publication_fault_injector,
            )
            return

        def inject(stage: str) -> None:
            if stage == "AFTER_O_EXCL":
                raise OSError(errno.EIO, "partial inner FAILURE")

        original_write_once(
            path,
            raw,
            publication_token=publication_token,
            publication_fault_injector=inject,
        )

    monkeypatch.setattr(launcher, "_run_child", fail_child)
    monkeypatch.setattr(launcher, "_write_once", partial_failure_write)
    with pytest.raises(ValueError, match="primary inner child") as captured:
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    assert captured.value.launch_publication_observation == {
        "attempt": "PRESENT_EXACT",
        "receipt": "ABSENT",
        "failure": "PRESENT_PARTIAL_OR_INVALID",
    }
    assert isinstance(
        captured.value.__cause__, launcher.V180r12r4DurableWriteError
    )
    assert captured.value.__cause__.artifact == "LAUNCH_FAILURE"
    assert captured.value.__cause__.stage == "AFTER_O_EXCL"
    assert captured.value.__cause__.observed_state == (
        "PRESENT_PARTIAL_OR_INVALID"
    )
    assert failure_path.is_file()


def test_unrecoverable_exact_inner_receipt_writes_failure_and_consumers_reject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    receipt_path = repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH
    original_stable_read = launcher._stable_read
    injected = False

    def fail_receipt_readback(
        observed: Path, *args: object, **kwargs: object
    ) -> bytes:
        nonlocal injected
        if observed == receipt_path and not injected:
            injected = True
            raise OSError(errno.EIO, "inner receipt publication readback")
        return original_stable_read(observed, *args, **kwargs)

    def reject_recovery(path: Path, _raw: bytes) -> None:
        if path == receipt_path:
            raise OSError(errno.EIO, "inner receipt recovery failed")
        raise AssertionError("unexpected receipt recovery path")

    def fake_run(
        _argv: list[str],
        _environment: dict[str, str],
        _pass_fds=(),
        *,
        hard_deadline_ns: int,
    ):
        assert hard_deadline_ns > time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        _write_measurement_success(repository)
        empty = launcher._empty_stream_document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_run)
    monkeypatch.setattr(launcher, "_stable_read", fail_receipt_readback)
    monkeypatch.setattr(
        launcher, "_recover_exact_receipt_publication", reject_recovery
    )
    with pytest.raises(launcher.V180r12r4DurableWriteError) as captured:
        launcher.launch_prelaunch_target_v180r12r4(
            "measurement", repository, digest
        )
    failure_path = repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
    assert receipt_path.is_file() and failure_path.is_file()
    failure = json.loads(failure_path.read_bytes())
    assert failure["publication_failure_artifact"] == "LAUNCH_RECEIPT"
    assert failure["publication_failure_stage"] == "AFTER_PARENT_FSYNC"
    assert failure["publication_failure_observed_state"] == "PRESENT_EXACT"
    assert captured.value.publication_recovery_error_type == "OSError"
    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchError,
        match="receipt/failure terminal coexistence",
    ):
        launcher._require_successful_measurement_launch(
            repository,
            json.loads(
                (repository / launcher.MATERIALIZATION_TERMINAL_RELATIVE_PATH)
                .read_bytes()
            )["materialization_terminal_id"],
        )
    assert launcher._inner_launch_join_observation(
        repository, "measurement"
    )["exact_attempt_terminal_join"] is False


def test_verification_outer_dispatch_requires_measurement_outer_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    attempt, _early_receipt = _write_inner_launch_receipt(
        repository, digest, "measurement"
    )
    inner_receipt_path = repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH
    inner_receipt_path.unlink()
    manifest = json.loads(
        (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
    )
    invocation = launcher._production_systemd_service_invocation(
        repository, digest, "measurement"
    )
    inner_receipt, inner_receipt_raw = launcher._terminal_document(
        schema=launcher.LAUNCH_RECEIPT_SCHEMA,
        id_key="launch_receipt_id",
        target="measurement",
        attempt=attempt,
        return_code=0,
        timed_out=False,
        stdout=launcher._empty_stream_document(),
        stderr=launcher._empty_stream_document(),
        progress=launcher._progress_observations(
            launcher._state_paths(repository, "measurement")
        ),
        error=None,
        launch_deadlines=launcher._freeze_launch_deadlines_v180r12r4(),
        measurement_cgroup_cleanup_observations=(
            _successful_measurement_cgroup_observations(
                manifest["frozen_authorization_context"]["campaign_attempt_id"]
            )
        ),
        production_systemd_service_invocation=invocation,
        production_runtime_placement_t1=(
            _early_receipt["production_runtime_placement_t1"]
        ),
    )
    assert inner_receipt["success"] is True
    _write_0400(inner_receipt_path, inner_receipt_raw)

    def forbidden_process(*_args, **_kwargs):  # pragma: no cover - forbidden
        raise AssertionError("systemd runner crossed predecessor gate")

    with pytest.raises(
        launcher.V180r12r4PrelaunchLaunchReplayForbidden,
        match="successful measurement service predecessor",
    ):
        launcher.dispatch_production_service_v180r12r4(
            "verification",
            repository,
            digest,
            process_runner=forbidden_process,
        )
    assert not (
        repository / launcher.VERIFICATION_SERVICE_ATTEMPT_RELATIVE_PATH
    ).exists()
