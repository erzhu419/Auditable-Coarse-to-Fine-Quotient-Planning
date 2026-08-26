from __future__ import annotations

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

from acfqp import construction_k7_campaign_measurement_protocol_v180r12r3r1 as protocol
from acfqp import construction_k7_campaign_measurement_finalizer_v180r12r3r1 as finalizer
from tests import test_construction_k7_campaign_measurement_finalizer_v180r12r3r1 as finalizer_fixture

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/launch_v180r12r3r1_campaign_measurement_prelaunch.py"
SPEC = importlib.util.spec_from_file_location("v180r12r3r1_prelaunch_launcher", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)
ZERO_ID = "0" * 64


@pytest.fixture
def tmp_path() -> Path:
    """Use native Linux mode semantics for O_EXCL/0400 attack tests."""

    path = Path(tempfile.mkdtemp(prefix="v180r12r3r1-launcher-", dir="/tmp"))
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


def _frozen_authorization_context(repository: Path) -> dict[str, object]:
    mount = repository / "fake-cgroup2"
    parent = mount / "delegated"
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
        "schema": "acfqp.campaign_measurement_attempt.v180r12r3r1",
        **values,
    }
    attempt_id = hashlib.sha256(
        b"acfqp:construction-k7-campaign-measurement-attempt:v180r12r3r1\x00"
        + _canonical(attempt_payload)
    ).hexdigest()
    return {
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
            "schema": "acfqp.v180r12r3r1_cgroup_parent_fact.v1",
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
            "controllers": ["memory", "pids"],
            "subtree_control": ["memory", "pids"],
            "cgroup_type": "domain",
            "cgroup_namespace_inode": 3,
            "cgroup_events_present": True,
            "memory_events_present": True,
            "pids_events_present": True,
            "cgroup_kill_present": True,
            "cgroup_procs_present": True,
            "memory_peak_present": True,
            "pids_peak_present": True,
            "self_membership": "0::/",
        },
        "runtime_capability_fact": {
            "schema": "acfqp.v180r12r3r1_runtime_capability_fact.v1",
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
    frozen_authorization_context = _frozen_authorization_context(repository)
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
        "schema": "acfqp.v180r12r3r1_source_bound_launch_manifest.v1",
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
                "scripts/run_v180r12r3r1_campaign_measurement.py",
                b"# measurement\n",
            ),
            "verification": _fact(
                "scripts/verify_v180r12r3r1_campaign_measurement.py",
                b"# verification\n",
            ),
            "supervisor": _fact(
                "scripts/supervise_v180r12r3r1_campaign_measurement.py",
                b"# supervisor\n",
            ),
            "worker": _fact(
                "scripts/work_v180r12r3r1_campaign_measurement.py",
                b"# worker\n",
            ),
        },
        "internal_target_contract": launcher.INTERNAL_TARGET_CONTRACT,
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
        "schema": "acfqp.v180r12r3r1_prelaunch_external_root.v1",
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
        "created_before_v180r12r3r1_authorized_measurement_execution": True,
        "v180r12r3r1_outcome_bytes_accessed": False,
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
        "v180r12r3r1_outcome_bytes_accessed": False,
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
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="remain zero sentinels",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
        launcher.V180r12r3r1PrelaunchLaunchError,
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
        assert pass_fds == (249, 250, 251)
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
    receipt = launcher.launch_prelaunch_target_v180r12r3r1(
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
    with pytest.raises(launcher.V180r12r3r1PrelaunchLaunchReplayForbidden):
        launcher.launch_prelaunch_target_v180r12r3r1(
            "measurement", repository, digest
        )


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
        assert pass_fds == (249, 250, 251)
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
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="authorization or transport provenance",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
        launcher.launch_prelaunch_target_v180r12r3r1(
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
    )
    _write_0400(prelaunch / "MEASUREMENT_LAUNCH_ATTEMPT.json", attempt_raw)
    _write_measurement_success(repository)
    prior_progress = launcher._progress_observations(
        launcher._state_paths(repository, "measurement")
    )
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
        launch_deadlines=launcher._freeze_launch_deadlines_v180r12r3r1(),
        measurement_cgroup_cleanup_observations=(
            _successful_measurement_cgroup_observations(
                finalizer_fixture.ledger_fixture.ATTEMPT_ID
            )
        ),
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
    receipt = launcher.launch_prelaunch_target_v180r12r3r1(
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
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
    launcher.launch_prelaunch_target_v180r12r3r1("measurement", repository, digest)

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
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
    launcher.launch_prelaunch_target_v180r12r3r1("measurement", repository, digest)

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

    with pytest.raises(launcher.V180r12r3r1PrelaunchLaunchError):
        launcher.launch_prelaunch_target_v180r12r3r1(
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

    def fail_after_attempt_create(path: Path, raw: bytes) -> None:
        if path == repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH:
            _write_0400(path, raw[:17])
            raise OSError("injected partial attempt fsync failure")
        original_write_once(path, raw)

    monkeypatch.setattr(launcher, "_write_once", fail_after_attempt_create)
    with pytest.raises(OSError, match="partial attempt"):
        launcher.launch_prelaunch_target_v180r12r3r1(
            "measurement", repository, digest
        )
    failure_path = repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    assert failure["failure_type"] == "OSError"
    assert failure["progress_observations"]["attempt"] == {
        "presence": "REGULAR_FILE",
        "mode": 0o400,
        "byte_count": 17,
        "sha256": hashlib.sha256(
            (repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH).read_bytes()
        ).hexdigest(),
    }


def test_concurrent_attempt_lock_loser_does_not_poison_winner_with_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    original_write_once = launcher._write_once

    def lose_attempt_race(path: Path, raw: bytes) -> None:
        if path == repository / launcher.MEASUREMENT_ATTEMPT_RELATIVE_PATH:
            original_write_once(path, raw)
            raise FileExistsError("concurrent attempt owner")
        original_write_once(path, raw)

    monkeypatch.setattr(launcher, "_write_once", lose_attempt_race)
    with pytest.raises(
        launcher.V180r12r3r1PrelaunchLaunchReplayForbidden,
        match="concurrently",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
        "v180r12r3r1-" + frozen["campaign_attempt_id"]
    )
    root.mkdir()

    def forbidden_run(*_args, **_kwargs):  # pragma: no cover - forbidden
        raise AssertionError("Popen boundary was crossed")

    monkeypatch.setattr(launcher, "_run_child", forbidden_run)
    with pytest.raises(
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="existed before Popen",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
    root = parent / f"v180r12r3r1-{campaign_attempt_id}"
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
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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

    def fail_failure_write(path: Path, raw: bytes) -> None:
        if path == repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH:
            raise OSError("secondary failure write")
        original_write_once(path, raw)

    monkeypatch.setattr(launcher, "_run_child", fail_child)
    monkeypatch.setattr(launcher, "_write_once", fail_failure_write)
    with pytest.raises(ValueError, match="primary bootstrap") as captured:
        launcher.launch_prelaunch_target_v180r12r3r1(
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

    def fail_failure_write(path: Path, raw: bytes) -> None:
        if path == repository / launcher.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH:
            raise OSError("typed failure secondary")
        original_write_once(path, raw)

    monkeypatch.setattr(launcher, "_run_child", fail_child)
    monkeypatch.setattr(launcher, "_write_once", fail_failure_write)
    try:
        launcher.launch_prelaunch_target_v180r12r3r1(
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
    launcher.launch_prelaunch_target_v180r12r3r1("measurement", repository, digest)
    receipt_path = repository / launcher.MEASUREMENT_RECEIPT_RELATIVE_PATH
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt.pop("launch_receipt_id")
    receipt["foreign_resigned_field"] = True
    receipt["launch_receipt_id"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    receipt_path.chmod(0o600)
    receipt_path.write_bytes(_canonical(receipt))
    receipt_path.chmod(0o400)
    with pytest.raises(
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="schema changed",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="boundary changed",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="internal target contract changed",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="differs from its C_pre Git blob",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
        launcher.V180r12r3r1PrelaunchLaunchReplayForbidden,
        match="materialization failure",
    ):
        launcher.launch_prelaunch_target_v180r12r3r1(
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
    monkeypatch.chdir(elsewhere)
    with pytest.raises(
        launcher.V180r12r3r1PrelaunchLaunchError,
        match="working directory",
    ):
        launcher._require_launcher_startup("measurement", repository)
