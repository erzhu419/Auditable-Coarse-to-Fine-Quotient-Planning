from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import time
import types
from types import SimpleNamespace
from typing import Mapping

import pytest

from acfqp import construction_k7_domain_registry_extension_v180r12r4 as domains
from acfqp import construction_k7_campaign_measurement_protocol_v180r12r4 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from scripts import verify_v180r12r4_campaign_measurement as runner
from tests import (
    test_construction_k7_campaign_measurement_finalizer_v180r12r4
    as finalizer_fixture,
)
from tests import (
    test_construction_k7_campaign_measurement_ledger_v180r12r4
    as ledger_fixture,
)
from tests import (
    test_construction_k7_campaign_measurement_supervisor_v180r12r4
    as supervisor_fixture,
)


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = ROOT / "scripts/launch_v180r12r4_campaign_measurement_prelaunch.py"


@pytest.fixture
def tmp_path() -> Path:
    path = Path(tempfile.mkdtemp(prefix="v180r12r4-verify-runner-", dir="/tmp"))
    try:
        yield path
    finally:
        shutil.rmtree(path)


@pytest.fixture(scope="module")
def success_bundle() -> dict[str, object]:
    inputs = finalizer_fixture._closed_inputs()
    terminal = finalizer_fixture._finalize(inputs)
    subject = next(
        row
        for row in terminal.document["campaign_measurement_ledger"]["evidence_documents"]
        if row["schema"] == "acfqp.campaign_measurement_subject_result.v180r12r4"
    )
    return {
        "terminal": terminal,
        "subject": subject,
        "protocol_id": terminal.document["protocol_id"],
        "authorization_id": terminal.document["authorization_id"],
    }


def _write(path: Path, raw: bytes, *, mode: int = 0o400) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(mode)


def _fact(relative: str, raw: bytes) -> dict[str, object]:
    return {
        "relative_path": relative,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _closure(facts: list[dict[str, object]]) -> dict[str, object]:
    return {
        "facts": facts,
        "file_count": len(facts),
        "total_byte_count": sum(int(row["byte_count"]) for row in facts),
        "facts_sha256": hashlib.sha256(canonical_json_bytes(facts)).hexdigest(),
    }


def _working_tree_source_conformance(
    repository: Path,
    closure_facts: list[dict[str, object]],
    sources: Mapping[str, bytes],
    normalized_wrapper: bytes,
) -> dict[str, object]:
    snapshots = []
    for fact in closure_facts:
        relative = str(fact["relative_path"])
        physical_raw = sources[relative]
        effective_raw = (
            normalized_wrapper
            if relative == runner.AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH
            else physical_raw
        )
        metadata = (repository / relative).stat()
        assert stat.S_ISREG(metadata.st_mode)
        assert stat.S_IMODE(metadata.st_mode) == 0o644
        binding_kind = str(
            fact.get("binding_kind", "EXACT_C_PRE_GIT_BLOB")
        )
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
            "st_dev": metadata.st_dev,
            "st_ino": metadata.st_ino,
            "st_mode": metadata.st_mode,
            "mode": stat.S_IMODE(metadata.st_mode),
            "st_nlink": metadata.st_nlink,
            "st_uid": metadata.st_uid,
            "st_gid": metadata.st_gid,
            "st_size": metadata.st_size,
            "st_mtime_ns": metadata.st_mtime_ns,
            "st_ctime_ns": metadata.st_ctime_ns,
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


def _wrapper_source(values: dict[str, object]) -> bytes:
    lines = []
    for name in runner._WRAPPER_REDACTED_NAMES:
        value = values[name]
        lines.append(
            f'{name} = "{value}"' if type(value) is str else f"{name} = {value}"
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _plain_document(payload: dict[str, object], identity_field: str) -> bytes:
    document = {
        **payload,
        identity_field: hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }
    return canonical_json_bytes(document)


def _domain_document(
    payload: dict[str, object], identity_field: str, domain: str
) -> bytes:
    document = {
        **payload,
        identity_field: hashlib.sha256(
            domain.encode("ascii") + b"\x00" + canonical_json_bytes(payload)
        ).hexdigest(),
    }
    return canonical_json_bytes(document)


def _service_launch_documents(
    measurement_attempt_raw: bytes,
    measurement_receipt_raw: bytes,
) -> tuple[bytes, bytes]:
    measurement_attempt = loads_canonical_json(measurement_attempt_raw)
    measurement_receipt = loads_canonical_json(measurement_receipt_raw)
    invocation = measurement_attempt["production_systemd_service_invocation"]
    environment = {
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        "LC_CTYPE": "C.UTF-8",
        "XDG_RUNTIME_DIR": "/run/user/1000",
    }
    origin_ns = 900_000_000_000_000
    hard_deadline_ns = origin_ns + runner.WALL_TIMEOUT_SECONDS * 1_000_000_000
    campaign_deadline_ns = (
        hard_deadline_ns - runner.CAMPAIGN_CLEANUP_GRACE_SECONDS * 1_000_000_000
    )
    empty_stream = {
        "byte_count": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
        "retained_prefix_hex": "",
        "retained_prefix_truncated": False,
    }
    not_found_stream = {
        "byte_count": len(b"not-found\n"),
        "sha256": hashlib.sha256(b"not-found\n").hexdigest(),
        "retained_prefix_hex": b"not-found\n".hex(),
        "retained_prefix_truncated": False,
    }
    unit_absence = {
        "systemctl_argv": [
            "/usr/bin/systemctl", "--user", "show",
            "--property=LoadState", "--value", invocation["unit_name"],
        ],
        "systemctl_environment": environment,
        "return_code": 0,
        "timed_out": False,
        "stdout": not_found_stream,
        "stderr": empty_stream,
        "expected_load_state": "not-found",
        "unit_absent_after_wait_collect": True,
    }
    attempt_payload = {
        "schema": runner.SERVICE_LAUNCH_ATTEMPT_SCHEMA,
        "target": "measurement",
        "token": invocation["token"],
        "unit_name": invocation["unit_name"],
        "materialization_terminal_id": measurement_attempt[
            "materialization_terminal_id"
        ],
        "materialization_terminal_sha256": measurement_attempt[
            "materialization_terminal_sha256"
        ],
        "launch_rule_id": measurement_attempt["launch_rule_id"],
        "production_systemd_service_invocation": invocation,
        "systemd_run_argv": invocation["systemd_run_argv"],
        "systemd_run_environment": environment,
        "pre_attempt_unit_absence_observation": copy.deepcopy(unit_absence),
        "inner_launch_artifact_paths": {
            "attempt": runner.MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
            "receipt": runner.MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH,
            "launch_failure": runner.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH,
        },
        "monotonic_origin_ns": origin_ns,
        "hard_deadline_ns": hard_deadline_ns,
        "campaign_deadline_ns": campaign_deadline_ns,
        "attempt_o_excl_before_systemd_run": True,
        "same_target_identity_rerun_forbidden": True,
        "pre_scientific_outer_dispatch": True,
        "campaign_event_or_evidence_document": False,
    }
    attempt_raw = _domain_document(
        attempt_payload,
        "service_launch_attempt_id",
        runner.SERVICE_LAUNCH_ATTEMPT_DOMAIN,
    )
    attempt = loads_canonical_json(attempt_raw)

    def observation(raw: bytes) -> dict[str, object]:
        return {
            "presence": "REGULAR_FILE",
            "mode": 0o400,
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }

    receipt_payload = {
        "schema": runner.SERVICE_LAUNCH_RECEIPT_SCHEMA,
        "target": "measurement",
        "service_launch_attempt_id": attempt["service_launch_attempt_id"],
        "token": invocation["token"],
        "unit_name": invocation["unit_name"],
        "production_systemd_service_invocation": invocation,
        "systemd_run_return_code": 0,
        "systemd_run_timed_out": False,
        "systemd_run_stdout": empty_stream,
        "systemd_run_stderr": empty_stream,
        "collected_unit_absence_observation": copy.deepcopy(unit_absence),
        "inner_launch_attempt_fact": observation(measurement_attempt_raw),
        "inner_launch_receipt_fact": observation(measurement_receipt_raw),
        "inner_launch_failure_fact": {"presence": "ABSENT"},
        "inner_launch_attempt_id": measurement_attempt["launch_attempt_id"],
        "inner_launch_terminal_kind": "RECEIPT",
        "inner_launch_terminal_id": measurement_receipt["launch_receipt_id"],
        "exact_attempt_terminal_join": True,
        "attempt_lock_preserved": True,
        "same_target_identity_rerun_forbidden": True,
        "pre_scientific_outer_dispatch": True,
        "campaign_event_or_evidence_document": False,
        "success": True,
        "failure_type": None,
        "failure_message": None,
    }
    receipt_raw = _domain_document(
        receipt_payload,
        "service_launch_receipt_id",
        runner.SERVICE_LAUNCH_RECEIPT_DOMAIN,
    )
    return attempt_raw, receipt_raw


def _production_invocation(
    repository: Path, materialization_sha256: str, target: str
) -> dict[str, object]:
    token_input, token, unit_name = protocol.PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
    command = [
        "/usr/bin/env", "-i",
        "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256="
        + materialization_sha256,
        "LC_CTYPE=C.UTF-8", *runner.ISOLATED_ARGV_PREFIX,
        str(repository / runner.LAUNCHER_RELATIVE_PATH),
        "service-entry", target, str(repository),
    ]
    return {
        "schema": protocol.PRODUCTION_SYSTEMD_SERVICE_INVOCATION_SCHEMA,
        "token_domain": protocol.PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN,
        "target": target,
        "token_input": dict(token_input),
        "token": token,
        "unit_name": unit_name,
        "unit_kind": "SERVICE_NOT_SCOPE",
        "slice": "app.slice",
        "service_type": "exec",
        "delegate": True,
        "umask": "0077",
        "launcher_command": command,
        "systemd_run_argv": [
            "/usr/bin/systemd-run", "--user", "--wait", "--collect", "--pipe",
            "--quiet", "--no-ask-password", "--unit=" + unit_name,
            "--slice=app.slice", "--service-type=exec", "--property=Delegate=yes",
            "--property=UMask=0077",
            "--working-directory=" + str(repository),
            *command,
        ],
    }


def _production_t1(target: str, attempt_id: str) -> dict[str, object]:
    placement, _t2, _details = ledger_fixture._placement_facts(attempt_id)
    result = copy.deepcopy(placement)
    _token_input, token, unit_name = protocol.PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
    old_unit_name = result["unit_name"]
    result.update(target=target, token=token, unit_name=unit_name)
    result["source_membership"] = result["source_membership"].replace(
        old_unit_name, unit_name
    )
    result["expected_source_membership"] = result[
        "expected_source_membership"
    ].replace(old_unit_name, unit_name)
    result["source_service_fd_fact"]["path"] = result[
        "source_service_fd_fact"
    ]["path"].replace(old_unit_name, unit_name)
    return result


def _deep_freeze(value):
    if type(value) is dict:
        return types.MappingProxyType(
            {key: _deep_freeze(item) for key, item in value.items()}
        )
    if type(value) is list:
        return tuple(_deep_freeze(item) for item in value)
    return value


def _success_cgroup_rows(campaign_attempt_id: str) -> list[dict[str, object]]:
    return [
        {
            "phase": phase,
            "applicable": True,
            "campaign_attempt_id": campaign_attempt_id,
            "root_name": f"v180r12r4-{campaign_attempt_id}",
            "ownership_acquired": True,
            "root_state": "ABSENT",
            "root_mode": None,
            "root_nlink": None,
            "root_device": None,
            "root_inode": None,
            "root_populated": None,
            "root_process_count": None,
            "supervisor_state": "ABSENT",
            "worker_state": "ABSENT",
            "kill_attempted": False,
            "kill_succeeded": False,
            "wait_empty_attempted": False,
            "wait_empty_succeeded": False,
            "remove_attempted": False,
            "remove_succeeded": False,
            "residual_tree_or_process_possible": False,
            "error_type": None,
            "error_message": None,
        }
        for phase in runner._MEASUREMENT_CGROUP_OBSERVATION_PHASES
    ]


def _source_manifest(
    repository: Path,
    *,
    success_bundle: dict[str, object],
    source_rule: str,
    materialization_rule: str,
    launch_rule: str,
    commit: str,
) -> tuple[dict[str, object], bytes, dict[str, bytes]]:
    terminal = success_bundle["terminal"]
    subject = success_bundle["subject"]
    assert hasattr(terminal, "document") and type(subject) is dict
    protocol_source = (
        f'EXPECTED_PROTOCOL_ID = "{success_bundle["protocol_id"]}"\n'
        "EXPECTED_CANONICAL_BYTE_COUNT = 123\n"
        f'EXPECTED_CANONICAL_SHA256 = "{"a" * 64}"\n'
        f'EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID = "{subject["execution_slot_id"]}"\n'
        f'LOGICAL_OCCURRENCE_ID = "{subject["logical_occurrence_id"]}"\n'
        f'EXECUTION_NONCE = "{subject["execution_nonce"]}"\n'
        f'EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID = "{source_rule}"\n'
        f'EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID = "{materialization_rule}"\n'
        f'EXPECTED_PRELAUNCH_LAUNCH_RULE_ID = "{launch_rule}"\n'
    ).encode("utf-8")
    authorization_source = (
        f'EXPECTED_PROTOCOL_ID = "{success_bundle["protocol_id"]}"\n'
        f'EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID = "{subject["execution_slot_id"]}"\n'
    ).encode("utf-8")
    zero_values = {
        name: ("0" * 64 if name in runner._WRAPPER_STRING_NAMES else 0)
        for name in runner._WRAPPER_REDACTED_NAMES
    }
    normalized_wrapper = _wrapper_source(zero_values)

    sources: dict[str, bytes] = {}
    for index, relative in enumerate(runner.SOURCE_CLOSURE_REQUIRED_ROOTS):
        source_path = ROOT / relative
        raw = source_path.read_bytes() if source_path.is_file() else f"BOUND_{index}=True\n".encode()
        sources[relative] = raw
    sources[runner.PROTOCOL_SOURCE_RELATIVE_PATH] = protocol_source
    sources[runner.AUTHORIZATION_SOURCE_RELATIVE_PATH] = authorization_source
    sources[runner.AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH] = normalized_wrapper

    normalized_facts: list[dict[str, object]] = []
    for relative in runner.SOURCE_CLOSURE_REQUIRED_ROOTS:
        row: dict[str, object] = _fact(relative, sources[relative])
        if relative == runner.AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH:
            row.update(
                {
                    "binding_kind": "POST_PREREG_LITERAL_REDACTED_SOURCE_V1",
                    "redacted_constant_names": list(runner._WRAPPER_REDACTED_NAMES),
                }
            )
        normalized_facts.append(row)
    raw_source_facts = [
        {key: row[key] for key in runner._RAW_FACT_FIELDS}
        for row in normalized_facts
    ]
    source_payload = {
        "schema": "acfqp.v180r12r4_authorization_source_closure.v1",
        "source_facts": raw_source_facts,
        "source_fact_count": len(raw_source_facts),
        "source_total_byte_count": sum(int(row["byte_count"]) for row in raw_source_facts),
        "required_static_roots": list(runner.SOURCE_CLOSURE_REQUIRED_ROOTS),
        "transitive_local_import_closure_required": True,
        "authorization_self_normalized_by_evidence_freeze": True,
    }
    source_raw = canonical_json_bytes(source_payload)
    frozen_values = {
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID": (
            success_bundle["terminal"].document["authorization_evidence_id"]
        ),
        "EXPECTED_CANONICAL_BYTE_COUNT": 321,
        "EXPECTED_CANONICAL_SHA256": "c" * 64,
        "EXPECTED_AUTHORIZATION_ID": success_bundle["authorization_id"],
        "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT": 654,
        "EXPECTED_AUTHORIZATION_CANONICAL_SHA256": "d" * 64,
        "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT": len(authorization_source),
        "EXPECTED_AUTHORIZATION_SOURCE_SHA256": hashlib.sha256(authorization_source).hexdigest(),
        "EXPECTED_SOURCE_CLOSURE_ID": hashlib.sha256(source_raw).hexdigest(),
        "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT": len(source_raw),
        "EXPECTED_SOURCE_CLOSURE_SHA256": hashlib.sha256(source_raw).hexdigest(),
        "EXPECTED_SOURCE_CLOSURE_FILE_COUNT": len(raw_source_facts),
    }
    sources[runner.AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH] = _wrapper_source(
        frozen_values
    )
    for relative, raw in sources.items():
        _write(repository / relative, raw, mode=0o644)
    source_conformance = _working_tree_source_conformance(
        repository, normalized_facts, sources, normalized_wrapper
    )
    service_contract = protocol.production_systemd_service_contract_v180r12r4()
    service_templates = {
        row["target"]: [
            item.replace("{repository_root}", str(repository))
            for item in row["systemd_run_argv_template"]
        ]
        for row in service_contract["target_rows"]
    }

    source_modules = []
    for index, relative in enumerate(runner.SOURCE_CLOSURE_REQUIRED_ROOTS):
        source_modules.append(
            {
                **_fact(relative, sources[relative]),
                "module": f"bound.m{index:03d}",
                "is_package": False,
            }
        )
    third_party = _closure(
        [
            {
                **_fact("packaging/__init__.py", b"# bound packaging\n"),
                "module": "packaging",
                "is_package": True,
                "source_root": str(repository),
            }
        ]
    )
    frozen_context = {
        "schema": runner.FROZEN_AUTHORIZATION_CONTEXT_SCHEMA,
        "protocol_id": success_bundle["protocol_id"],
        "protocol_byte_count": 123,
        "protocol_sha256": "a" * 64,
        "authorization_id": success_bundle["authorization_id"],
        "authorization_byte_count": frozen_values[
            "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT"
        ],
        "authorization_sha256": frozen_values[
            "EXPECTED_AUTHORIZATION_CANONICAL_SHA256"
        ],
        "authorization_evidence_id": frozen_values[
            "EXPECTED_AUTHORIZATION_EVIDENCE_ID"
        ],
        "authorization_evidence_byte_count": frozen_values[
            "EXPECTED_CANONICAL_BYTE_COUNT"
        ],
        "authorization_evidence_sha256": frozen_values[
            "EXPECTED_CANONICAL_SHA256"
        ],
        "campaign_measurement_execution_slot_id": subject["execution_slot_id"],
        "logical_occurrence_id": subject["logical_occurrence_id"],
        "execution_nonce": subject["execution_nonce"],
        "campaign_attempt_id": success_bundle["terminal"].document["attempt_id"],
        "cgroup_parent_fact": {
            "schema": "acfqp.v180r12r4_cgroup_parent_fact.v1",
            "mount_point": "/sys/fs/cgroup",
            "mount_fstype": "cgroup2",
            "mount_device": 25,
            "mount_inode": 1,
            "mount_options": ["rw"],
            "parent_path": "/sys/fs/cgroup/delegated",
            "parent_device": 25,
            "parent_inode": 2,
            "owner_uid": os.getuid(),
            "owner_gid": os.getgid(),
            "mode": 0o700,
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
    assert tuple(frozen_context) == runner.FROZEN_AUTHORIZATION_CONTEXT_FIELDS
    manifest = {
        "schema": runner.PRELAUNCH_MANIFEST_SCHEMA,
        "repository_root": str(repository),
        "c_pre_root": str(repository / runner.PRELAUNCH_ROOT_RELATIVE_PATH),
        "manifest_relative_path": "launch_manifest.json",
        "c_pre_commit_id": commit,
        "bootstrap": _fact(
            "bootstrap.py", sources["scripts/bootstrap_v180r12r4_campaign_measurement.py"]
        ),
        "runtime": {"source_bound": True},
        "git": {"source_bound": True},
        "authorization_source_closure_kind": "EXACT_NORMALIZED_C_PRE_SOURCE_CLOSURE",
        "authorization_self_module": "bound.authorization",
        "authorization_raw_source_modules": ["bound.authorization"],
        "authorization_source_closure": _closure(normalized_facts),
        "working_tree_source_conformance": source_conformance,
        "source_modules": source_modules,
        "third_party_source_closure": third_party,
        "targets": {
            target: _fact(path, sources[path])
            for target, path in runner.TARGET_RUNNER_PATHS.items()
        },
        "internal_target_contract": {"sealed": True},
        "production_systemd_service_contract": service_contract,
        "production_systemd_run_argv_templates": service_templates,
        "production_service_launch_artifact_paths": (
            runner._production_service_artifact_paths()
        ),
        "production_service_launch_modes": {
            "outer_dispatch": "dispatch",
            "retained_service_entry": "service-entry",
        },
        "atomic_cgroup_birth_preflight_receipt_interface": (
            runner._zero_atomic_cgroup_birth_preflight_interface()
        ),
        "frozen_authorization_context": frozen_context,
        "working_tree_mutation_after_snapshot_in_scope": False,
    }
    return manifest, canonical_json_bytes(manifest), sources


def _repository(
    tmp_path: Path, success_bundle: dict[str, object]
) -> tuple[Path, dict[str, str]]:
    repository = (tmp_path / "repository").absolute()
    repository.mkdir()
    (repository / ".git").mkdir()
    prelaunch = repository / runner.PRELAUNCH_ROOT_RELATIVE_PATH
    prelaunch.mkdir(parents=True)
    prelaunch.chmod(0o700)
    output = repository / runner.OUTPUT_ROOT_RELATIVE_PATH
    output.mkdir(parents=True)
    output.chmod(0o700)

    ids = {
        "source_rule": "7" * 64,
        "materialization_rule": "8" * 64,
        "launch_rule": "9" * 64,
        "commit": "a" * 40,
    }
    manifest, manifest_raw, sources = _source_manifest(
        repository,
        success_bundle=success_bundle,
        source_rule=ids["source_rule"],
        materialization_rule=ids["materialization_rule"],
        launch_rule=ids["launch_rule"],
        commit=ids["commit"],
    )
    bootstrap_raw = sources["scripts/bootstrap_v180r12r4_campaign_measurement.py"]
    launcher_raw = sources["scripts/launch_v180r12r4_campaign_measurement_prelaunch.py"]
    _write(repository / runner.BOOTSTRAP_RELATIVE_PATH, bootstrap_raw)
    _write(repository / runner.LAUNCHER_RELATIVE_PATH, launcher_raw)
    _write(repository / runner.MANIFEST_RELATIVE_PATH, manifest_raw)

    def git_fact(relative: str, raw: bytes, digit: str) -> dict[str, object]:
        return {
            **_fact(relative, raw),
            "git_mode": "100644",
            "git_blob_id": digit * 40,
        }

    bootstrap_git = git_fact(
        runner.SOURCE_CLOSURE_REQUIRED_ROOTS[0], bootstrap_raw, "1"
    )
    launcher_git = git_fact(
        runner.SOURCE_CLOSURE_REQUIRED_ROOTS[1], launcher_raw, "2"
    )
    materializer_raw = sources[runner.SOURCE_CLOSURE_REQUIRED_ROOTS[2]]
    materializer_git = git_fact(
        runner.SOURCE_CLOSURE_REQUIRED_ROOTS[2], materializer_raw, "3"
    )
    external = {
        "schema": "acfqp.v180r12r4_prelaunch_external_root.v1",
        "materialization_rule_id": ids["materialization_rule"],
        "source_closure_rule_id": ids["source_rule"],
        "repository_root": str(repository),
        "git_directory": str(repository / ".git"),
        "c_pre_commit_id": ids["commit"],
        "c_pre_tree_id": "4" * 40,
        "bootstrap_git_blob": bootstrap_git,
        "launcher_git_blob": launcher_git,
        "materializer_git_blob": materializer_git,
        "third_party_source_roots": {
            "packaging": str(tmp_path),
            "tomli": str(tmp_path),
        },
        "frozen_authorization_context": manifest[
            "frozen_authorization_context"
        ],
        "atomic_cgroup_birth_preflight_receipt_interface": manifest[
            "atomic_cgroup_birth_preflight_receipt_interface"
        ],
        "created_before_v180r12r4_authorized_measurement_execution": True,
        "v180r12r4_outcome_bytes_accessed": False,
    }
    external_raw = canonical_json_bytes(external)
    _write(repository / runner.EXTERNAL_ROOT_RELATIVE_PATH, external_raw)
    wrapper_normalized = next(
        row
        for row in manifest["authorization_source_closure"]["facts"]
        if row["relative_path"] == runner.AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH
    )
    wrapper_current = next(
        {key: row[key] for key in runner._RAW_FACT_FIELDS}
        for row in manifest["source_modules"]
        if row["relative_path"] == runner.AUTHORIZATION_EVIDENCE_SOURCE_RELATIVE_PATH
    )
    materialization_payload = {
        "schema": runner.MATERIALIZATION_TERMINAL_SCHEMA,
        "materialization_rule_id": ids["materialization_rule"],
        "source_closure_rule_id": ids["source_rule"],
        "repository_root": str(repository),
        "external_root": {
            "absolute_path": str(repository / runner.EXTERNAL_ROOT_RELATIVE_PATH),
            "byte_count": len(external_raw),
            "sha256": hashlib.sha256(external_raw).hexdigest(),
            "immutable_mode": "0400",
        },
        "git_topology": {
            "c_pre_commit_id": ids["commit"],
            "c_pre_tree_id": "4" * 40,
            "empty_bridge_commit_id": "b" * 40,
            "empty_bridge_tree_id": "4" * 40,
            "literal_commit_id": "c" * 40,
            "literal_commit_tree_id": "5" * 40,
            "literal_wrapper_prior_blob_id": "6" * 40,
            "literal_wrapper_blob_id": "7" * 40,
        },
        "bootstrap_source_git_blob": bootstrap_git,
        "materializer_source_git_blob": materializer_git,
        "launcher_source_git_blob": launcher_git,
        "retained_bootstrap": _fact(runner.BOOTSTRAP_RELATIVE_PATH, bootstrap_raw),
        "retained_launcher": _fact(runner.LAUNCHER_RELATIVE_PATH, launcher_raw),
        "launch_manifest": _fact(runner.MANIFEST_RELATIVE_PATH, manifest_raw),
        "production_transient_service_rows": [
            {
                "target": row["target"],
                "token": row["token"],
                "unit_name": row["unit_name"],
            }
            for row in manifest["production_systemd_service_contract"][
                "target_rows"
            ]
        ],
        "production_service_launch_artifact_paths": manifest[
            "production_service_launch_artifact_paths"
        ],
        "production_service_launch_modes": manifest[
            "production_service_launch_modes"
        ],
        "atomic_cgroup_birth_preflight_receipt_interface": manifest[
            "atomic_cgroup_birth_preflight_receipt_interface"
        ],
        "materialization_terminal_relative_path": runner.MATERIALIZATION_TERMINAL_RELATIVE_PATH,
        "materialization_failure_relative_path": runner.MATERIALIZATION_FAILURE_RELATIVE_PATH,
        "authorization_source_closure_file_count": manifest["authorization_source_closure"]["file_count"],
        "authorization_source_closure_total_byte_count": manifest["authorization_source_closure"]["total_byte_count"],
        "authorization_source_closure_facts_sha256": manifest["authorization_source_closure"]["facts_sha256"],
        "third_party_source_closure_file_count": manifest["third_party_source_closure"]["file_count"],
        "third_party_source_closure_total_byte_count": manifest["third_party_source_closure"]["total_byte_count"],
        "third_party_source_closure_facts_sha256": manifest["third_party_source_closure"]["facts_sha256"],
        "normalized_wrapper_fact": wrapper_normalized,
        "current_literal_wrapper_raw_observation": wrapper_current,
        "working_tree_source_conformance": manifest[
            "working_tree_source_conformance"
        ],
        "launch_manifest_digest_is_runtime_supplied_not_protocol_frozen": True,
        "launch_manifest_has_no_self_digest": True,
        "frozen_authorization_context_sha256": hashlib.sha256(
            canonical_json_bytes(manifest["frozen_authorization_context"])
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
    materialization_raw = _plain_document(
        materialization_payload, "materialization_terminal_id"
    )
    _write(repository / runner.MATERIALIZATION_TERMINAL_RELATIVE_PATH, materialization_raw)

    manifest_sha = hashlib.sha256(manifest_raw).hexdigest()

    def attempt(target: str) -> tuple[dict[str, object], bytes]:
        payload = {
            "schema": runner.LAUNCH_ATTEMPT_SCHEMA,
            "launch_rule_id": ids["launch_rule"],
            "target": target,
            "repository_root": str(repository),
            "materialization_terminal_id": loads_canonical_json(materialization_raw)["materialization_terminal_id"],
            "materialization_terminal_byte_count": len(materialization_raw),
            "materialization_terminal_sha256": hashlib.sha256(materialization_raw).hexdigest(),
            "launch_manifest_sha256": manifest_sha,
            "child_argv": [
                *runner.ISOLATED_ARGV_PREFIX,
                str(repository / runner.BOOTSTRAP_RELATIVE_PATH),
                target,
                str(repository),
                str(repository / runner.PRELAUNCH_ROOT_RELATIVE_PATH),
                str(repository / runner.MANIFEST_RELATIVE_PATH),
            ],
            "child_environment": {
                runner.MANIFEST_SHA256_ENV: manifest_sha,
                "LC_CTYPE": "C.UTF-8",
            },
            "production_systemd_service_invocation": _production_invocation(
                repository, hashlib.sha256(materialization_raw).hexdigest(), target
            ),
            "address_space_hard_cap_bytes": runner.ADDRESS_SPACE_HARD_CAP_BYTES,
            "address_space_cap_applied_before_child_exec": True,
            "wall_timeout_seconds": runner.WALL_TIMEOUT_SECONDS,
            "attempt_lock_written_before_child_exec": True,
            "same_target_identity_rerun_forbidden": True,
            "preauthorization_supervision": True,
            "campaign_actual_measurement": False,
            "scientific_occurrence_started": False,
            "authorized_child_measurement_execution_attempted": (
                target == "measurement"
            ),
            "authorized_child_measurement_execution_completed": False,
            "producer_free_verification_attempted": target == "verification",
            "producer_free_verification_completed": False,
        }
        raw = _plain_document(payload, "launch_attempt_id")
        return loads_canonical_json(raw), raw

    measurement_attempt, measurement_attempt_raw = attempt("measurement")
    _write(repository / runner.MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH, measurement_attempt_raw)
    source_terminal = success_bundle["terminal"]
    source_subject = success_bundle["subject"]
    terminal_inputs = finalizer_fixture._closed_inputs(
        authorization_evidence_id=source_terminal.document[
            "authorization_evidence_id"
        ],
        execution_slot_id=source_subject["execution_slot_id"],
        logical_occurrence_id=source_subject["logical_occurrence_id"],
        execution_nonce=source_subject["execution_nonce"],
        prelaunch_materialization_terminal_id=loads_canonical_json(
            materialization_raw
        )["materialization_terminal_id"],
        prelaunch_launch_manifest_sha256=manifest_sha,
        prelaunch_launch_rule_id=ids["launch_rule"],
        measurement_launch_attempt_id=measurement_attempt["launch_attempt_id"],
    )
    terminal = finalizer_fixture._finalize(terminal_inputs)
    subject = next(
        row
        for row in terminal.document["campaign_measurement_ledger"][
            "evidence_documents"
        ]
        if row["schema"]
        == "acfqp.campaign_measurement_subject_result.v180r12r4"
    )
    artifacts = terminal.success_artifact_bytes
    artifact_paths = {
        "evidence_inventory": runner.EVIDENCE_INVENTORY_RELATIVE_PATH,
        "execution_closure": runner.EXECUTION_CLOSURE_RELATIVE_PATH,
        "os_receipt": runner.OS_RECEIPT_RELATIVE_PATH,
        "ledger_closure": runner.LEDGER_CLOSURE_RELATIVE_PATH,
    }
    for key, relative in artifact_paths.items():
        _write(repository / relative, artifacts[key])
    _write(repository / runner.TERMINAL_RELATIVE_PATH, terminal.canonical_bytes)
    store = runner.VerificationDurableStoreV180R12R4(repository)
    try:
        progress = {
            "attempt": store.observe(runner.MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH, runner.LAUNCH_ARTIFACT_BYTE_CAP),
            "receipt": {"presence": "ABSENT"},
            "launch_failure": {"presence": "ABSENT"},
            "runtime_cas": {"presence": "ABSENT"},
            "output_root": {"presence": "DIRECTORY", "mode": 0o700},
            "terminal": store.observe(runner.TERMINAL_RELATIVE_PATH, runner.TERMINAL_BYTE_CAP),
            "evidence_inventory": store.observe(
                runner.EVIDENCE_INVENTORY_RELATIVE_PATH,
                runner.EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP,
            ),
            "execution_closure": store.observe(
                runner.EXECUTION_CLOSURE_RELATIVE_PATH,
                runner.EXECUTION_CLOSURE_BYTE_CAP,
            ),
            "os_receipt": store.observe(
                runner.OS_RECEIPT_RELATIVE_PATH,
                runner.OS_RECEIPT_BUNDLE_BYTE_CAP,
            ),
            "ledger_closure": store.observe(
                runner.LEDGER_CLOSURE_RELATIVE_PATH,
                runner.LEDGER_CLOSURE_BYTE_CAP,
            ),
            "measurement_failure": {"presence": "ABSENT"},
            "verification": {"presence": "ABSENT"},
            "verification_failure": {"presence": "ABSENT"},
            "retained_replay": {"presence": "ABSENT"},
        }
    finally:
        store.close()
    empty_stream = {
        "byte_count": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
        "retained_prefix_hex": "",
        "retained_prefix_truncated": False,
    }
    measurement_origin_ns = 1_000_000_000_000_000
    measurement_hard_deadline_ns = (
        measurement_origin_ns + 14_400 * 1_000_000_000
    )
    measurement_campaign_deadline_ns = (
        measurement_hard_deadline_ns - 600 * 1_000_000_000
    )
    topology = next(
        row
        for row in terminal.document["campaign_measurement_ledger"][
            "evidence_documents"
        ]
        if row.get("schema")
        == "acfqp.campaign_cgroup_topology_receipt.v180r12r4"
    )
    receipt_payload = {
        "schema": runner.LAUNCH_RECEIPT_SCHEMA,
        "launch_rule_id": ids["launch_rule"],
        "launch_attempt_id": measurement_attempt["launch_attempt_id"],
        "target": "measurement",
        "return_code": 0,
        "timed_out": False,
        "child_stdout": empty_stream,
        "child_stderr": empty_stream,
        "progress_observations": progress,
        "same_target_identity_rerun_forbidden": True,
        "attempt_lock_preserved": True,
        "address_space_hard_cap_bytes": runner.ADDRESS_SPACE_HARD_CAP_BYTES,
        "wall_timeout_seconds": runner.WALL_TIMEOUT_SECONDS,
        "monotonic_origin_ns": measurement_origin_ns,
        "hard_deadline_ns": measurement_hard_deadline_ns,
        "campaign_deadline_ns": measurement_campaign_deadline_ns,
        "campaign_cleanup_grace_seconds": 600,
        "termination_grace_seconds": 10,
        "measurement_cgroup_cleanup_observations": _success_cgroup_rows(
            terminal.document["attempt_id"]
        ),
        "production_systemd_service_invocation": measurement_attempt[
            "production_systemd_service_invocation"
        ],
        "production_runtime_placement_t1": topology[
            "production_runtime_placement_t1"
        ],
        "preauthorization_supervision": True,
        "campaign_actual_measurement": False,
        "authorized_child_measurement_execution_attempted": True,
        "authorized_child_measurement_execution_completed": True,
        "producer_free_verification_attempted": False,
        "producer_free_verification_completed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_execution_allowed": False,
        "success": True,
        "failure_type": None,
        "failure_message": None,
    }
    measurement_receipt_raw = _plain_document(
        receipt_payload, "launch_receipt_id"
    )
    measurement_receipt = loads_canonical_json(measurement_receipt_raw)
    _write(
        repository / runner.MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH,
        measurement_receipt_raw,
    )
    measurement_service_attempt_raw, measurement_service_receipt_raw = (
        _service_launch_documents(
            measurement_attempt_raw, measurement_receipt_raw
        )
    )
    _write(
        repository / runner.MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
        measurement_service_attempt_raw,
    )
    _write(
        repository / runner.MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH,
        measurement_service_receipt_raw,
    )
    verification_attempt, verification_attempt_raw = attempt("verification")
    _write(repository / runner.VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH, verification_attempt_raw)
    ids.update(
        {
            "manifest_sha256": manifest_sha,
            "verification_launch_attempt_id": verification_attempt["launch_attempt_id"],
            "success_bundle": {
                "terminal": terminal,
                "subject": subject,
                "measurement_receipt": measurement_receipt,
                "measurement_receipt_raw": measurement_receipt_raw,
                "measurement_service_attempt": loads_canonical_json(
                    measurement_service_attempt_raw
                ),
                "measurement_service_attempt_raw": measurement_service_attempt_raw,
                "measurement_service_receipt": loads_canonical_json(
                    measurement_service_receipt_raw
                ),
                "measurement_service_receipt_raw": measurement_service_receipt_raw,
            },
        }
    )
    return repository, ids


def _fake_result(success_bundle: dict[str, object]) -> SimpleNamespace:
    terminal = success_bundle["terminal"]
    measurement_receipt = success_bundle["measurement_receipt"]
    measurement_receipt_raw = success_bundle["measurement_receipt_raw"]
    measurement_service_attempt = success_bundle["measurement_service_attempt"]
    measurement_service_attempt_raw = success_bundle[
        "measurement_service_attempt_raw"
    ]
    measurement_service_receipt = success_bundle["measurement_service_receipt"]
    measurement_service_receipt_raw = success_bundle[
        "measurement_service_receipt_raw"
    ]
    payload = {
        field_name: None
        for field_name in runner.independent_verifier.VERIFICATION_FIELDS
        if field_name != "campaign_measurement_verification_id"
    }
    payload.update({
        "schema": "acfqp.campaign_measurement_verification.v180r12r4",
        "protocol_id": terminal.document["protocol_id"],
        "authorization_id": terminal.document["authorization_id"],
        "authorization_evidence_id": terminal.document[
            "authorization_evidence_id"
        ],
        "attempt_id": terminal.document["attempt_id"],
        "prelaunch_materialization_terminal_id": terminal.document[
            "prelaunch_materialization_terminal_id"
        ],
        "prelaunch_launch_manifest_sha256": terminal.document[
            "prelaunch_launch_manifest_sha256"
        ],
        "precompiled_source_bundle_sha256": terminal.document[
            "precompiled_source_bundle_sha256"
        ],
        "prelaunch_launch_rule_id": terminal.document[
            "prelaunch_launch_rule_id"
        ],
        "measurement_launch_attempt_id": terminal.document[
            "measurement_launch_attempt_id"
        ],
        "measurement_service_launch_attempt_id": measurement_service_attempt[
            "service_launch_attempt_id"
        ],
        "measurement_service_launch_attempt_byte_count": len(
            measurement_service_attempt_raw
        ),
        "measurement_service_launch_attempt_sha256": hashlib.sha256(
            measurement_service_attempt_raw
        ).hexdigest(),
        "measurement_service_launch_receipt_id": measurement_service_receipt[
            "service_launch_receipt_id"
        ],
        "measurement_service_launch_receipt_byte_count": len(
            measurement_service_receipt_raw
        ),
        "measurement_service_launch_receipt_sha256": hashlib.sha256(
            measurement_service_receipt_raw
        ).hexdigest(),
        "measurement_launch_receipt_id": measurement_receipt[
            "launch_receipt_id"
        ],
        "measurement_launch_receipt_byte_count": len(measurement_receipt_raw),
        "measurement_launch_receipt_sha256": hashlib.sha256(
            measurement_receipt_raw
        ).hexdigest(),
        "runtime_role_exit_origin_guard_status": (
            "PASS_TRANSITIVE_FROZEN_BOOTSTRAP_AND_MEASUREMENT_LAUNCH_RECEIPT"
        ),
        "measurement_launch_receipt_directly_observes_origin_guard": False,
        "frozen_bootstrap_post_dispatch_origin_guard_transitively_supported": True,
        "production_systemd_service_invocation_independently_replayed": True,
        "production_runtime_placement_t1_t2_t3_independently_replayed": True,
        "pre_scientific_outer_service_launch_join_independently_replayed": True,
        "subject_id": terminal.document["subject_id"],
        "campaign_measurement_terminal_id": terminal.document[
            "campaign_measurement_terminal_id"
        ],
        "V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS": "PASS",
        "COUNTER_COMPLETENESS_GATE": "PASS",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "scientific_success_claimed": False,
    })
    document = {
        **payload,
        "campaign_measurement_verification_id": (
            domains.extension_content_id_v180r12r4(
                domains.CONSTRUCTION_K7_VERIFICATION_V180R12R4_DOMAIN,
                payload,
            )
        ),
    }
    return SimpleNamespace(canonical_bytes=canonical_json_bytes(document), document=document)


def _invoke(repository: Path, ids: dict[str, str]) -> dict[str, object]:
    context = runner._validate_verified_external_context_v180r12r4(
        _verified_external_context(repository)
    )
    return runner.verify_retained_campaign_measurement_once_v180r12r4(
        repository,
        expected_manifest_sha256=ids["manifest_sha256"],
        expected_prereg_commit=ids["commit"],
        watchdog_seconds=30,
        verified_external_context=context,
    )


def _verified_external_context(repository: Path) -> types.MappingProxyType:
    manifest_raw = (repository / runner.MANIFEST_RELATIVE_PATH).read_bytes()
    manifest = loads_canonical_json(manifest_raw)
    frozen = manifest["frozen_authorization_context"]
    materialization_raw = (
        repository / runner.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    ).read_bytes()
    materialization = loads_canonical_json(materialization_raw)
    current_raw = (
        repository / runner.VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH
    ).read_bytes()
    current = loads_canonical_json(current_raw)
    measurement_raw = (
        repository / runner.MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH
    ).read_bytes()
    measurement = loads_canonical_json(measurement_raw)
    native_zero_rows = tuple(
        types.MappingProxyType(dict(source_row))
        for source_row in ledger_fixture._precompiled_source_rows()
    )
    verification_origin_ns = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    verification_hard_deadline_ns = (
        verification_origin_ns + 14_400 * 1_000_000_000
    )
    verification_campaign_deadline_ns = (
        verification_hard_deadline_ns - 600 * 1_000_000_000
    )
    values: dict[str, object] = {
        "schema": runner.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA,
        "target": "verification",
        "actor_role": "VERIFIER",
        "repository_root": str(repository),
        "c_pre_root": str(repository / runner.PRELAUNCH_ROOT_RELATIVE_PATH),
        "prereg_commit_id": manifest["c_pre_commit_id"],
        "prelaunch_materialization_terminal_id": materialization[
            "materialization_terminal_id"
        ],
        "prelaunch_materialization_terminal_byte_count": len(materialization_raw),
        "prelaunch_materialization_terminal_sha256": hashlib.sha256(
            materialization_raw
        ).hexdigest(),
        "prelaunch_launch_manifest_sha256": hashlib.sha256(
            manifest_raw
        ).hexdigest(),
        "prelaunch_launch_rule_id": current["launch_rule_id"],
        "current_launch_attempt_id": current["launch_attempt_id"],
        "current_launch_attempt_byte_count": len(current_raw),
        "current_launch_attempt_sha256": hashlib.sha256(current_raw).hexdigest(),
        "measurement_launch_attempt_id": measurement["launch_attempt_id"],
        "measurement_launch_attempt_byte_count": len(measurement_raw),
        "measurement_launch_attempt_sha256": hashlib.sha256(
            measurement_raw
        ).hexdigest(),
        "protocol_id": frozen["protocol_id"],
        "protocol_byte_count": frozen["protocol_byte_count"],
        "protocol_sha256": frozen["protocol_sha256"],
        "authorization_id": frozen["authorization_id"],
        "authorization_byte_count": frozen["authorization_byte_count"],
        "authorization_sha256": frozen["authorization_sha256"],
        "authorization_evidence_id": frozen["authorization_evidence_id"],
        "authorization_evidence_byte_count": frozen[
            "authorization_evidence_byte_count"
        ],
        "authorization_evidence_sha256": frozen[
            "authorization_evidence_sha256"
        ],
        "campaign_measurement_execution_slot_id": frozen[
            "campaign_measurement_execution_slot_id"
        ],
        "logical_occurrence_id": frozen["logical_occurrence_id"],
        "execution_nonce": frozen["execution_nonce"],
        "campaign_attempt_id": frozen["campaign_attempt_id"],
        "monotonic_origin_ns": verification_origin_ns,
        "hard_deadline_ns": verification_hard_deadline_ns,
        "campaign_deadline_ns": verification_campaign_deadline_ns,
        "cgroup_parent_fact": types.MappingProxyType(
            dict(frozen["cgroup_parent_fact"])
        ),
        "runtime_capability_fact": types.MappingProxyType(
            dict(frozen["runtime_capability_fact"])
        ),
        "production_systemd_service_invocation": _deep_freeze(
            current["production_systemd_service_invocation"]
        ),
        "production_runtime_placement_t1": _deep_freeze(
            _production_t1("verification", frozen["campaign_attempt_id"])
        ),
        "inherited_fd_roles": runner.VERIFICATION_EXTERNAL_FD_ROLE_ROWS,
        "target_payload": types.MappingProxyType({}),
        "one_shot": True,
        "precompiled_source_bundle_sha256": (
            ledger_fixture.PRECOMPILED_SOURCE_BUNDLE_SHA256
        ),
        "native_zero_precompiled_source_rows": native_zero_rows,
        "external_launch_context_sha256": "e" * 64,
        "context_consumed_once": True,
    }
    assert tuple(values) == runner.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS
    return types.MappingProxyType(values)


def _campaign_cgroup_topology() -> dict[str, object]:
    return copy.deepcopy(supervisor_fixture._topology().to_document())


def _refresh_cgroup_parent_fact_sha256(topology: dict[str, object]) -> None:
    topology["cgroup_parent_fact_sha256"] = hashlib.sha256(
        canonical_json_bytes(topology["cgroup_parent_fact"])
    ).hexdigest()


def test_independent_cgroup_topology_accepts_extra_parent_cpu_controller(
) -> None:
    topology = _campaign_cgroup_topology()
    parent = topology["cgroup_parent_fact"]
    parent["controllers"] = ["cpu", "memory", "pids"]
    parent["subtree_control"] = ["cpu", "memory", "pids"]
    topology["controllers"] = ["cpu", "memory", "pids"]
    _refresh_cgroup_parent_fact_sha256(topology)

    node_rows, controls = runner.independent_verifier._validate_cgroup_topology(
        topology
    )

    assert set(node_rows) == {
        "DELEGATED_PARENT", "MEASUREMENT_ROOT", "SUPERVISOR", "WORKER"
    }
    assert len(controls) == 14
    assert topology["controllers"] == parent["subtree_control"]
    assert topology["subtree_control"] == ["memory", "pids"]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("controllers", ["pids"]),
        ("controllers", ["memory"]),
        ("subtree_control", ["pids"]),
        ("subtree_control", ["memory"]),
    ),
)
def test_independent_cgroup_topology_requires_parent_memory_and_pids(
    field: str,
    value: list[str],
) -> None:
    topology = _campaign_cgroup_topology()
    topology["cgroup_parent_fact"][field] = value
    _refresh_cgroup_parent_fact_sha256(topology)

    with pytest.raises(
        runner.independent_verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
        match="campaign cgroup topology root fact changed",
    ):
        runner.independent_verifier._validate_cgroup_topology(topology)


@pytest.mark.parametrize(
    ("parent_subtree_control", "root_controllers"),
    (
        (["cpu", "memory", "pids"], ["memory", "pids"]),
        (["memory", "pids"], ["cpu", "memory", "pids"]),
    ),
)
def test_independent_cgroup_topology_joins_root_controllers_to_parent_subtree(
    parent_subtree_control: list[str],
    root_controllers: list[str],
) -> None:
    topology = _campaign_cgroup_topology()
    topology["cgroup_parent_fact"]["subtree_control"] = parent_subtree_control
    topology["controllers"] = root_controllers
    _refresh_cgroup_parent_fact_sha256(topology)

    with pytest.raises(
        runner.independent_verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
        match="campaign cgroup topology root fact changed",
    ):
        runner.independent_verifier._validate_cgroup_topology(topology)


def test_independent_cgroup_topology_keeps_root_subtree_control_exact() -> None:
    topology = _campaign_cgroup_topology()
    topology["subtree_control"] = ["cpu", "memory", "pids"]

    with pytest.raises(
        runner.independent_verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
        match="campaign cgroup topology root fact changed",
    ):
        runner.independent_verifier._validate_cgroup_topology(topology)


def test_independent_cgroup_topology_requires_delegated_parent_subset() -> None:
    topology = _campaign_cgroup_topology()
    topology["cgroup_parent_fact"]["controllers"] = ["memory", "pids"]
    topology["cgroup_parent_fact"]["subtree_control"] = [
        "cpu", "memory", "pids"
    ]
    topology["controllers"] = ["cpu", "memory", "pids"]
    _refresh_cgroup_parent_fact_sha256(topology)

    with pytest.raises(
        runner.independent_verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
        match="campaign cgroup topology root fact changed",
    ):
        runner.independent_verifier._validate_cgroup_topology(topology)


def test_runner_ast_boundary_and_launcher_keysets_are_mechanical() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    forbidden = (
        "campaign_measurement_finalizer_v180r12r4",
        "campaign_measurement_ledger_v180r12r4",
        "campaign_measurement_supervisor_v180r12r4",
        "campaign_measurement_worker_v180r12r4",
        "v180r12r2",
    )
    assert all(fragment not in name for name in imports for fragment in forbidden)
    verifier_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr
        == "verify_campaign_measurement_terminal_independently_v180r12r4"
    ]
    assert len(verifier_calls) == 1
    spec = importlib.util.spec_from_file_location("runner_launcher_contract", LAUNCHER_PATH)
    assert spec is not None and spec.loader is not None
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    assert runner._MANIFEST_FIELDS == launcher._MANIFEST_KEYS
    assert runner._MATERIALIZATION_FIELDS == launcher._MATERIALIZATION_REQUIRED_KEYS
    assert runner._EXTERNAL_ROOT_FIELDS == launcher._EXTERNAL_ROOT_KEYS
    assert runner._ATTEMPT_FIELDS == launcher._ATTEMPT_KEYS
    assert runner._RECEIPT_FIELDS == launcher._TERMINAL_KEYS | {"launch_receipt_id"}
    assert runner._FAILURE_FIELDS == (
        launcher._TERMINAL_KEYS
        | launcher._LAUNCH_FAILURE_PUBLICATION_KEYS
        | {"launch_failure_id"}
    )
    assert tuple(map(len, (
        runner._ATTEMPT_FIELDS, runner._RECEIPT_FIELDS, runner._FAILURE_FIELDS,
    ))) == (24, 36, 41)
    assert runner._LAUNCH_FAILURE_PUBLICATION_FIELDS == frozenset(
        protocol.PRELAUNCH_LAUNCH_FAILURE_PUBLICATION_FIELDS
    ) == launcher._LAUNCH_FAILURE_PUBLICATION_KEYS
    assert runner._LAUNCH_PUBLICATION_STAGES == (
        protocol.PRELAUNCH_LAUNCH_PUBLICATION_STAGES
    ) == launcher.SERVICE_LAUNCH_PUBLICATION_STAGES
    assert runner._LAUNCH_PUBLICATION_STATES == (
        protocol.PRELAUNCH_LAUNCH_PUBLICATION_STATES
    ) == launcher.SERVICE_LAUNCH_PUBLICATION_STATES
    assert runner.PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS == (
        protocol.PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS
    )
    assert runner.independent_verifier.PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS == (
        frozenset(protocol.PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS)
    )
    assert runner.SERVICE_LAUNCH_ATTEMPT_FIELDS == frozenset(
        protocol.PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_FIELDS
    ) == launcher.SERVICE_LAUNCH_ATTEMPT_FIELDS
    assert runner.SERVICE_LAUNCH_ATTEMPT_DOMAIN == (
        protocol.PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_DOMAIN
    )
    assert runner.SERVICE_LAUNCH_RECEIPT_DOMAIN == (
        protocol.PRELAUNCH_SERVICE_LAUNCH_RECEIPT_DOMAIN
    )
    assert runner.SERVICE_LAUNCH_FAILURE_DOMAIN == (
        protocol.PRELAUNCH_SERVICE_LAUNCH_FAILURE_DOMAIN
    )
    assert runner.SERVICE_LAUNCH_RECEIPT_FIELDS == frozenset(
        protocol.PRELAUNCH_SERVICE_LAUNCH_RECEIPT_FIELDS
    ) == launcher.SERVICE_LAUNCH_RECEIPT_FIELDS
    assert runner.SERVICE_LAUNCH_FAILURE_FIELDS == frozenset(
        protocol.PRELAUNCH_SERVICE_LAUNCH_FAILURE_FIELDS
    ) == launcher.SERVICE_LAUNCH_FAILURE_FIELDS
    assert runner.SERVICE_LAUNCH_FAILURE_PUBLICATION_FIELDS == frozenset(
        protocol.PRELAUNCH_LAUNCH_FAILURE_PUBLICATION_FIELDS
    )
    assert runner.SERVICE_LAUNCH_PUBLICATION_STAGES == (
        protocol.PRELAUNCH_SERVICE_LAUNCH_PUBLICATION_STAGES
    ) == launcher.SERVICE_LAUNCH_PUBLICATION_STAGES
    assert runner.SERVICE_LAUNCH_PUBLICATION_STATES == (
        protocol.PRELAUNCH_LAUNCH_PUBLICATION_STATES
    ) == launcher.SERVICE_LAUNCH_PUBLICATION_STATES
    assert runner.SERVICE_LAUNCH_INNER_JOIN_FIELDS == frozenset(
        protocol.PRELAUNCH_SERVICE_LAUNCH_INNER_JOIN_FIELDS
    ) == launcher.SERVICE_LAUNCH_INNER_JOIN_FIELDS
    assert runner.SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS == frozenset(
        protocol.PRELAUNCH_SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS
    ) == launcher.SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS
    assert runner.independent_verifier.MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_FIELDS == (
        frozenset(protocol.PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_FIELDS)
    )
    assert runner.independent_verifier.MEASUREMENT_SERVICE_LAUNCH_RECEIPT_FIELDS == (
        frozenset(protocol.PRELAUNCH_SERVICE_LAUNCH_RECEIPT_FIELDS)
    )
    assert runner.independent_verifier.MEASUREMENT_SERVICE_LAUNCH_FAILURE_FIELDS == (
        frozenset(protocol.PRELAUNCH_SERVICE_LAUNCH_FAILURE_FIELDS)
    )
    assert runner._MEASUREMENT_CGROUP_OBSERVATION_FIELDS == (
        launcher.MEASUREMENT_CGROUP_OBSERVATION_FIELDS
    ) == frozenset(protocol.MEASUREMENT_CGROUP_OBSERVATION_FIELDS)
    assert runner._MEASUREMENT_CGROUP_OBSERVATION_PHASES == (
        launcher.MEASUREMENT_CGROUP_OBSERVATION_PHASES
    ) == protocol.MEASUREMENT_CGROUP_OBSERVATION_PHASES
    assert launcher.TERMINAL_FIELDS == runner.independent_verifier.TERMINAL_FIELDS
    assert frozenset(protocol.TERMINAL_FIELDS) == (
        runner.independent_verifier.TERMINAL_FIELDS
    )
    assert protocol.CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA == (
        domains.CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA
    )
    assert protocol.CAMPAIGN_MEASUREMENT_ATTEMPT_DOMAIN == (
        domains.CONSTRUCTION_K7_CAMPAIGN_MEASUREMENT_ATTEMPT_V180R12R4_DOMAIN
    )
    assert runner.VERIFICATION_FAILURE_FIELDS == frozenset(
        protocol.VERIFICATION_FAILURE_FIELDS
    )
    assert runner.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS == (
        protocol.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
    )
    assert runner.VERIFICATION_FAILURE_OBSERVATION_BOUNDARY == (
        protocol.VERIFICATION_FAILURE_OBSERVATION_BOUNDARY
    )
    assert runner.VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES == (
        protocol.VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES
    )
    assert runner.VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP == (
        protocol.VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP
    )
    assert runner.VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP == (
        protocol.VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP
    )
    assert runner.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROW_COUNT == 9
    assert runner.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA == (
        protocol.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA
    )
    assert runner.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS == (
        protocol.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS
    )
    assert runner.VERIFICATION_EXTERNAL_FD_ROLE_ROWS == (
        protocol.EXTERNAL_FD_ROLE_MAP["verification"]
    ) == ((249, "EXTERNAL_LAUNCH_CONTEXT_MEMFD"),)
    entrypoints = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "bootstrap_entrypoint_v180r12r4"
    ]
    assert len(entrypoints) == 1
    assert tuple(
        row[0] for row in runner.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
    ) == tuple(
        sorted(
            row[0]
            for row in runner.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
        )
    )
    assert {
        row[0] for row in runner.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
    } == {
        runner.EVIDENCE_INVENTORY_RELATIVE_PATH,
        runner.EXECUTION_CLOSURE_RELATIVE_PATH,
        runner.OS_RECEIPT_RELATIVE_PATH,
        runner.LEDGER_CLOSURE_RELATIVE_PATH,
        runner.TERMINAL_RELATIVE_PATH,
        runner.RUNTIME_CAS_ROOT_RELATIVE_PATH,
        runner.VERIFICATION_RELATIVE_PATH,
        runner.VERIFICATION_FAILURE_RELATIVE_PATH,
        runner.RETAINED_REPLAY_RELATIVE_PATH,
    }


def test_bootstrap_entrypoint_consumes_exact_verified_context_once(
    tmp_path: Path,
    success_bundle: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _ids = _repository(tmp_path, success_bundle)
    context = _verified_external_context(repository)
    calls: list[tuple[Path, dict[str, object]]] = []

    def observed(root: Path, **kwargs):
        calls.append((root, kwargs))
        return {"COUNTER_COMPLETENESS_GATE": "PASS"}

    monkeypatch.setattr(
        runner,
        "verify_retained_campaign_measurement_once_v180r12r4",
        observed,
    )
    assert runner.bootstrap_entrypoint_v180r12r4(context) is None
    assert calls == [
        (
            repository,
            {
                "expected_manifest_sha256": context[
                    "prelaunch_launch_manifest_sha256"
                ],
                "expected_prereg_commit": context["prereg_commit_id"],
                "verified_external_context": context,
            },
        )
    ]
    with pytest.raises(
        runner.V180R12R4VerificationRunnerError,
        match="direct verification invocation is forbidden",
    ):
        runner.main()


@pytest.mark.parametrize(
    ("attack", "expected"),
    (
        ("MUTABLE", "exact bootstrap-verified immutable context"),
        ("MISSING", "exact bootstrap-verified immutable context"),
        ("FOREIGN_TARGET", "role/path/FD boundary"),
        ("FOREIGN_FD", "role/path/FD boundary"),
        ("RESIGNED_ATTEMPT", "attempt identity changed"),
    ),
)
def test_bootstrap_entrypoint_rejects_missing_resigned_or_foreign_context(
    tmp_path: Path,
    success_bundle: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
    expected: str,
) -> None:
    repository, _ids = _repository(tmp_path, success_bundle)
    original = _verified_external_context(repository)
    values = {key: original[key] for key in original}
    if attack == "MUTABLE":
        supplied: Mapping[str, object] = values
    else:
        if attack == "MISSING":
            values.pop("external_launch_context_sha256")
        elif attack == "FOREIGN_TARGET":
            values["target"] = "measurement"
        elif attack == "FOREIGN_FD":
            values["inherited_fd_roles"] = (
                (250, "DELEGATED_CGROUP_PARENT_DIRECTORY"),
            )
        elif attack == "RESIGNED_ATTEMPT":
            values["campaign_attempt_id"] = "f" * 64
            values["external_launch_context_sha256"] = "d" * 64
        supplied = types.MappingProxyType(values)
    monkeypatch.setattr(
        runner,
        "verify_retained_campaign_measurement_once_v180r12r4",
        lambda *_args, **_kwargs: pytest.fail("invalid context reached verifier"),
    )
    with pytest.raises(runner.V180R12R4VerificationRunnerError, match=expected):
        runner.bootstrap_entrypoint_v180r12r4(supplied)


def test_verified_external_context_joins_exact_durable_transport_facts(
    tmp_path: Path,
    success_bundle: dict[str, object],
) -> None:
    repository, _ids = _repository(tmp_path, success_bundle)
    context = runner._validate_verified_external_context_v180r12r4(
        _verified_external_context(repository)
    )
    store = runner.VerificationDurableStoreV180R12R4(repository)
    try:
        manifest_raw = store.read_stable(
            runner.MANIFEST_RELATIVE_PATH,
            byte_cap=runner.MANIFEST_BYTE_CAP,
            required_mode=0o400,
        )
        manifest = runner._canonical_object(manifest_raw, "manifest")
        anchors = runner._validate_source_manifest(
            store,
            manifest,
            expected_manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
            expected_prereg_commit=context["prereg_commit_id"],
        )
        materialization, materialization_raw = runner._validate_materialization(
            store, manifest, manifest_raw, anchors
        )
        current = runner._validate_attempt(
            store,
            runner.VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH,
            target="verification",
            anchors=anchors,
            materialization=materialization,
            materialization_raw=materialization_raw,
            manifest_raw=manifest_raw,
        )
        measurement = runner._validate_attempt(
            store,
            runner.MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
            target="measurement",
            anchors=anchors,
            materialization=materialization,
            materialization_raw=materialization_raw,
            manifest_raw=manifest_raw,
        )

        def check(candidate: types.MappingProxyType) -> None:
            runner._validate_verified_external_context_artifact_joins_v180r12r4(
                store,
                candidate,
                manifest=manifest,
                manifest_raw=manifest_raw,
                anchors=anchors,
                materialization=materialization,
                materialization_raw=materialization_raw,
                verification_attempt=current,
                measurement_attempt=measurement,
            )

        check(context)
        for field in (
            "protocol_sha256",
            "prelaunch_materialization_terminal_id",
            "current_launch_attempt_sha256",
            "measurement_launch_attempt_id",
        ):
            values = {key: context[key] for key in context}
            values[field] = "f" * 64
            values["external_launch_context_sha256"] = "d" * 64
            with pytest.raises(
                runner.V180R12R4VerificationRunnerError,
                match="artifact/provenance join changed",
            ):
                check(types.MappingProxyType(values))
    finally:
        store.close()


@pytest.mark.parametrize(
    "attack", ("PRE_ATTEMPT_ABSENCE", "INNER_PATH", "INNER_RECEIPT_FACT")
)
def test_measurement_outer_service_launch_join_rejects_resigned_substitution(
    tmp_path: Path,
    success_bundle: dict[str, object],
    attack: str,
) -> None:
    repository, _ids = _repository(tmp_path, success_bundle)
    materialization = loads_canonical_json(
        (repository / runner.MATERIALIZATION_TERMINAL_RELATIVE_PATH).read_bytes()
    )
    measurement_attempt = loads_canonical_json(
        (repository / runner.MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH).read_bytes()
    )
    measurement_receipt = loads_canonical_json(
        (repository / runner.MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH).read_bytes()
    )
    if attack in {"PRE_ATTEMPT_ABSENCE", "INNER_PATH"}:
        relative = runner.MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH
        document = loads_canonical_json((repository / relative).read_bytes())
        payload = dict(document)
        payload.pop("service_launch_attempt_id")
        if attack == "PRE_ATTEMPT_ABSENCE":
            payload["pre_attempt_unit_absence_observation"] = dict(
                payload["pre_attempt_unit_absence_observation"]
            )
            payload["pre_attempt_unit_absence_observation"][
                "unit_absent_after_wait_collect"
            ] = False
        else:
            payload["inner_launch_artifact_paths"] = dict(
                payload["inner_launch_artifact_paths"]
            )
            payload["inner_launch_artifact_paths"]["receipt"] = (
                "prelaunch/foreign.json"
            )
        raw = _domain_document(
            payload,
            "service_launch_attempt_id",
            runner.SERVICE_LAUNCH_ATTEMPT_DOMAIN,
        )
    else:
        relative = runner.MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH
        document = loads_canonical_json((repository / relative).read_bytes())
        payload = dict(document)
        payload.pop("service_launch_receipt_id")
        payload["inner_launch_receipt_fact"] = dict(
            payload["inner_launch_receipt_fact"]
        )
        payload["inner_launch_receipt_fact"]["sha256"] = "f" * 64
        raw = _domain_document(
            payload,
            "service_launch_receipt_id",
            runner.SERVICE_LAUNCH_RECEIPT_DOMAIN,
        )
    (repository / relative).chmod(0o600)
    _write(repository / relative, raw)
    store = runner.VerificationDurableStoreV180R12R4(repository)
    try:
        with pytest.raises(runner.V180R12R4VerificationRunnerError):
            runner._validate_measurement_service_launch_join(
                store,
                materialization=materialization,
                measurement_attempt=measurement_attempt,
                measurement_receipt=measurement_receipt,
            )
    finally:
        store.close()


@pytest.mark.parametrize(
    "failure_relative",
    (
        runner.MEASUREMENT_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH,
        runner.MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH,
    ),
)
def test_precreate_rejects_receipt_and_failure_namespace_coexistence(
    tmp_path: Path,
    success_bundle: dict[str, object],
    failure_relative: str,
) -> None:
    repository, _ids = _repository(tmp_path, success_bundle)
    _write(repository / failure_relative, b"{}\n")
    store = runner.VerificationDurableStoreV180R12R4(repository)
    try:
        with pytest.raises(
            runner.V180R12R4VerificationRunnerError,
            match="one durable failure",
        ):
            runner._require_current_precreate_matrix(store)
    finally:
        store.close()


def test_source_manifest_rejects_nonconformant_working_tree_snapshot(
    tmp_path: Path, success_bundle: dict[str, object]
) -> None:
    repository, ids = _repository(tmp_path, success_bundle)
    manifest_path = repository / runner.MANIFEST_RELATIVE_PATH
    manifest = loads_canonical_json(manifest_path.read_bytes())
    manifest["working_tree_source_conformance"][
        "full_source_conformance"
    ] = False
    manifest_raw = canonical_json_bytes(manifest)
    manifest_path.chmod(0o600)
    _write(manifest_path, manifest_raw)
    store = runner.VerificationDurableStoreV180R12R4(repository)
    try:
        with pytest.raises(
            runner.V180R12R4VerificationRunnerError,
            match="working-tree source conformance did not pass",
        ):
            runner._validate_source_manifest(
                store,
                manifest,
                expected_manifest_sha256=hashlib.sha256(
                    manifest_raw
                ).hexdigest(),
                expected_prereg_commit=ids["commit"],
            )
    finally:
        store.close()


def test_materialization_rejects_source_conformance_snapshot_substitution(
    tmp_path: Path, success_bundle: dict[str, object]
) -> None:
    repository, ids = _repository(tmp_path, success_bundle)
    store = runner.VerificationDurableStoreV180R12R4(repository)
    try:
        manifest_raw = store.read_stable(
            runner.MANIFEST_RELATIVE_PATH,
            byte_cap=runner.MANIFEST_BYTE_CAP,
            required_mode=0o400,
        )
        manifest = runner._canonical_object(manifest_raw, "manifest")
        anchors = runner._validate_source_manifest(
            store,
            manifest,
            expected_manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
            expected_prereg_commit=ids["commit"],
        )
        terminal_path = repository / runner.MATERIALIZATION_TERMINAL_RELATIVE_PATH
        terminal = loads_canonical_json(terminal_path.read_bytes())
        terminal.pop("materialization_terminal_id")
        diagnostic = copy.deepcopy(terminal["working_tree_source_conformance"])
        diagnostic["snapshots"][0]["observed_before"]["st_ino"] += 1
        diagnostic["snapshots"][0]["observed_after"]["st_ino"] += 1
        terminal["working_tree_source_conformance"] = diagnostic
        terminal_raw = _plain_document(terminal, "materialization_terminal_id")
        terminal_path.chmod(0o600)
        _write(terminal_path, terminal_raw)
        with pytest.raises(
            runner.V180R12R4VerificationRunnerError,
            match="manifest/materialization source conformance join changed",
        ):
            runner._validate_materialization(
                store, manifest, manifest_raw, anchors
            )
    finally:
        store.close()


def test_one_shot_success_writes_exact_verification_and_replay(
    tmp_path: Path, success_bundle: dict[str, object]
) -> None:
    repository, ids = _repository(tmp_path, success_bundle)
    document = _invoke(repository, ids)
    verification = repository / runner.VERIFICATION_RELATIVE_PATH
    replay = repository / runner.RETAINED_REPLAY_RELATIVE_PATH
    assert verification.read_bytes() == replay.read_bytes()
    assert loads_canonical_json(verification.read_bytes()) == document
    assert stat.S_IMODE(verification.stat().st_mode) == 0o400
    assert stat.S_IMODE(replay.stat().st_mode) == 0o400
    assert document["COUNTER_COMPLETENESS_GATE"] == "PASS"
    assert document["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    assert document[
        "production_systemd_service_invocation_independently_replayed"
    ] is True
    assert document[
        "production_runtime_placement_t1_t2_t3_independently_replayed"
    ] is True
    assert document[
        "pre_scientific_outer_service_launch_join_independently_replayed"
    ] is True
    with pytest.raises(runner.V180R12R4VerificationReplayForbidden):
        _invoke(repository, ids)


@pytest.mark.parametrize("partial_target", ("verification", "replay"))
def test_partial_verification_or_replay_consumes_identity_and_freezes_failure(
    tmp_path: Path,
    success_bundle: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    partial_target: str,
) -> None:
    repository, ids = _repository(tmp_path, success_bundle)
    monkeypatch.setattr(
        runner.independent_verifier,
        "verify_campaign_measurement_terminal_independently_v180r12r4",
        lambda *_args, **_kwargs: _fake_result(ids["success_bundle"]),
    )
    original = runner.VerificationDurableStoreV180R12R4.write_once
    target_path = (
        runner.VERIFICATION_RELATIVE_PATH
        if partial_target == "verification"
        else runner.RETAINED_REPLAY_RELATIVE_PATH
    )

    def partial(self, relative_path: str, raw: bytes, *, mode: int = 0o400):
        if relative_path == target_path:
            original(self, relative_path, raw[:17], mode=mode)
            raise runner.V180R12R4VerificationDurableWriteFailure(relative_path, True)
        return original(self, relative_path, raw, mode=mode)

    monkeypatch.setattr(runner.VerificationDurableStoreV180R12R4, "write_once", partial)
    with pytest.raises(runner.V180R12R4VerificationDurableWriteFailure):
        _invoke(repository, ids)
    failure = loads_canonical_json(
        (repository / runner.VERIFICATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    observed = {
        row["relative_path"]: row for row in failure["partial_artifact_observations"]
    }
    assert observed[target_path]["state"] == "PRESENT"
    assert observed[target_path]["byte_count"] == 17
    assert failure["attempt_id"] == success_bundle["terminal"].document["attempt_id"]
    assert failure["verification_launch_attempt_id"] == ids[
        "verification_launch_attempt_id"
    ]
    assert failure["failure_memory_reserve_bytes"] == 4 * 1024 * 1024
    assert failure["failure_memory_reserve_released_before_failure"] is True
    assert failure["partial_artifact_observation_boundary"] == (
        runner.VERIFICATION_FAILURE_OBSERVATION_BOUNDARY
    )
    assert observed[runner.VERIFICATION_FAILURE_RELATIVE_PATH]["state"] == "ABSENT"
    with pytest.raises(runner.V180R12R4VerificationReplayForbidden):
        _invoke(repository, ids)


def test_partial_failure_write_preserves_primary_and_forbids_rerun(
    tmp_path: Path,
    success_bundle: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, ids = _repository(tmp_path, success_bundle)

    def hostile(*_args, **_kwargs):
        raise ValueError("primary independent failure")

    monkeypatch.setattr(
        runner.independent_verifier,
        "verify_campaign_measurement_terminal_independently_v180r12r4",
        hostile,
    )
    original = runner.VerificationDurableStoreV180R12R4.write_once

    class HostileFailureWriteError(OSError):
        def with_traceback(self, _traceback):
            raise AssertionError("hostile secondary with_traceback was called")

    def partial_failure(self, relative_path: str, raw: bytes, *, mode: int = 0o400):
        if relative_path == runner.VERIFICATION_FAILURE_RELATIVE_PATH:
            original(self, relative_path, raw[:17], mode=mode)
            raise HostileFailureWriteError("injected failure fsync loss")
        return original(self, relative_path, raw, mode=mode)

    monkeypatch.setattr(
        runner.VerificationDurableStoreV180R12R4, "write_once", partial_failure
    )
    with pytest.raises(ValueError, match="primary independent") as captured:
        _invoke(repository, ids)
    assert isinstance(captured.value.__cause__, HostileFailureWriteError)
    assert (repository / runner.VERIFICATION_FAILURE_RELATIVE_PATH).stat().st_size == 17
    with pytest.raises(runner.V180R12R4VerificationReplayForbidden):
        _invoke(repository, ids)


def test_runtime_cas_and_symlink_attacks_are_frozen(
    tmp_path: Path,
    success_bundle: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, ids = _repository(tmp_path, success_bundle)
    cas = repository / runner.RUNTIME_CAS_ROOT_RELATIVE_PATH
    cas.mkdir()
    with pytest.raises(runner.V180R12R4VerificationRunnerError, match="runtime CAS"):
        _invoke(repository, ids)
    failure = loads_canonical_json(
        (repository / runner.VERIFICATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    cas_row = next(
        row
        for row in failure["partial_artifact_observations"]
        if row["relative_path"] == runner.RUNTIME_CAS_ROOT_RELATIVE_PATH
    )
    assert cas_row["kind"] == "DIRECTORY" and cas_row["state"] == "PRESENT"

    second_root = tmp_path / "symlink-case"
    second_root.mkdir()
    repository, ids = _repository(second_root, success_bundle)
    terminal = repository / runner.TERMINAL_RELATIVE_PATH
    target = tmp_path / "terminal-target.json"
    target.write_bytes(terminal.read_bytes())
    terminal.unlink()
    terminal.symlink_to(target)
    with pytest.raises(runner.V180R12R4VerificationRunnerError, match="linked"):
        _invoke(repository, ids)
    failure = loads_canonical_json(
        (repository / runner.VERIFICATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    assert failure["attempt_id"] is None


@pytest.mark.parametrize(
    "relative_path",
    (
        runner.EVIDENCE_INVENTORY_RELATIVE_PATH,
        runner.EXECUTION_CLOSURE_RELATIVE_PATH,
        runner.OS_RECEIPT_RELATIVE_PATH,
        runner.LEDGER_CLOSURE_RELATIVE_PATH,
    ),
)
def test_each_separate_success_artifact_drift_is_stream_observed_in_failure(
    tmp_path: Path,
    success_bundle: dict[str, object],
    relative_path: str,
) -> None:
    repository, ids = _repository(tmp_path, success_bundle)
    path = repository / relative_path
    path.chmod(0o600)
    path.write_bytes(path.read_bytes() + b"\n")
    path.chmod(0o400)
    with pytest.raises(runner.V180R12R4VerificationRunnerError):
        _invoke(repository, ids)
    failure = loads_canonical_json(
        (repository / runner.VERIFICATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    row = next(
        item
        for item in failure["partial_artifact_observations"]
        if item["relative_path"] == relative_path
    )
    assert row["state"] == "PRESENT"
    assert row["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert failure["attempt_id"] == success_bundle["terminal"].document["attempt_id"]


def test_hostile_formatter_memory_error_and_watchdog_cleanup_are_typed(
    tmp_path: Path,
    success_bundle: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_allocate_reserve = runner._allocate_failure_memory_reserve
    repository, ids = _repository(tmp_path, success_bundle)

    class HostileError(BaseException):
        def __str__(self):
            raise MemoryError("formatter")

        def with_traceback(self, _traceback):
            raise MemoryError("hostile with_traceback")

    def hostile(*_args, **_kwargs):
        raise HostileError()

    monkeypatch.setattr(
        runner.independent_verifier,
        "verify_campaign_measurement_terminal_independently_v180r12r4",
        hostile,
    )
    with pytest.raises(HostileError):
        _invoke(repository, ids)
    failure = loads_canonical_json(
        (repository / runner.VERIFICATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    assert failure["message"] == "UNFORMATTABLE_EXCEPTION"
    cleanup = failure["watchdog_cleanup_observation"]
    assert cleanup["cancel_attempted"] is True
    assert cleanup["ignore_attempted"] is True
    assert cleanup["handler_restore_attempted"] is True
    assert cleanup["teardown_completed"] is True
    assert failure["traceback_retained"] is False

    second_root = tmp_path / "reserve-case"
    second_root.mkdir()
    repository, ids = _repository(second_root, success_bundle)
    monkeypatch.setattr(
        runner,
        "_allocate_failure_memory_reserve",
        lambda: (_ for _ in ()).throw(MemoryError("reserve allocation")),
    )
    with pytest.raises(MemoryError, match="reserve allocation"):
        _invoke(repository, ids)
    assert not (repository / runner.VERIFICATION_FAILURE_RELATIVE_PATH).exists()
    assert not (repository / runner.VERIFICATION_RELATIVE_PATH).exists()

    third_root = tmp_path / "post-identity-memory-error"
    third_root.mkdir()
    repository, ids = _repository(third_root, success_bundle)
    monkeypatch.setattr(runner, "_allocate_failure_memory_reserve", real_allocate_reserve)
    monkeypatch.setattr(
        runner.independent_verifier,
        "verify_campaign_measurement_terminal_independently_v180r12r4",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(MemoryError("verification")),
    )
    with pytest.raises(MemoryError, match="verification"):
        _invoke(repository, ids)
    failure = loads_canonical_json(
        (repository / runner.VERIFICATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    assert failure["failure_memory_reserve_allocated"] is True
    assert failure["failure_memory_reserve_released_before_failure"] is True


def test_failure_file_observation_is_constant_memory_streaming_and_cap_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "streaming-observation"
    repository.mkdir()
    relative = "large-sparse-artifact.bin"
    path = repository / relative
    with path.open("wb") as handle:
        handle.truncate(runner.MAX_LEDGER_BYTE_COUNT)

    store = runner.VerificationDurableStoreV180R12R4(repository)
    real_read = runner.os.read
    largest_request = 0
    read_calls = 0

    def bounded_read(descriptor: int, count: int) -> bytes:
        nonlocal largest_request, read_calls
        largest_request = max(largest_request, count)
        read_calls += 1
        return real_read(descriptor, count)

    def forbidden_accumulating_read(*_args, **_kwargs):
        raise AssertionError("failure observation called accumulating read_stable")

    monkeypatch.setattr(store, "read_stable", forbidden_accumulating_read)
    monkeypatch.setattr(runner.os, "read", bounded_read)
    try:
        row = runner._failure_observation(
            store,
            relative,
            byte_cap=runner.MAX_LEDGER_BYTE_COUNT,
            kind="FILE",
        )
        assert row["state"] == "PRESENT"
        assert row["byte_count"] == runner.MAX_LEDGER_BYTE_COUNT
        assert largest_request <= (
            runner.VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES
        )
        assert read_calls > 1
        expected = hashlib.sha256()
        zero_chunk = b"\0" * (
            runner.VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES
        )
        for _ in range(
            runner.MAX_LEDGER_BYTE_COUNT
            // runner.VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES
        ):
            expected.update(zero_chunk)
        assert row["sha256"] == expected.hexdigest()

        calls_before_cap_rejection = read_calls
        with path.open("r+b") as handle:
            handle.truncate(runner.MAX_LEDGER_BYTE_COUNT + 1)
        cap_row = runner._failure_observation(
            store,
            relative,
            byte_cap=runner.MAX_LEDGER_BYTE_COUNT,
            kind="FILE",
        )
        assert cap_row["state"] == "READ_ERROR"
        assert cap_row["read_error_type"] == "ARTIFACT_BYTE_CAP_EXCEEDED"
        assert cap_row["byte_count"] == runner.MAX_LEDGER_BYTE_COUNT + 1
        assert read_calls == calls_before_cap_rejection
    finally:
        store.close()


def test_failure_streaming_memory_error_is_a_bounded_typed_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "streaming-memory-error"
    repository.mkdir()
    relative = "artifact.bin"
    (repository / relative).write_bytes(b"bounded-input")
    store = runner.VerificationDurableStoreV180R12R4(repository)

    def memory_error(_descriptor: int, _count: int) -> bytes:
        raise MemoryError("streaming read allocation")

    monkeypatch.setattr(runner.os, "read", memory_error)
    try:
        row = runner._failure_observation(
            store, relative, byte_cap=1024, kind="FILE"
        )
    finally:
        store.close()
    assert row["state"] == "READ_ERROR"
    assert row["byte_count"] == len(b"bounded-input")
    assert row["sha256"] is None
    assert row["read_error_type"] == "MemoryError"
    assert len(row["read_error_message"].encode("utf-8")) <= 512


def test_failure_reserve_precedes_the_first_stable_input_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "reserve-before-input"
    repository.mkdir()
    order: list[str] = []
    allocate = runner._allocate_failure_memory_reserve

    def observed_allocate() -> bytearray:
        order.append("ALLOCATE_RESERVE")
        return allocate()

    def rejected_read(*_args, **_kwargs):
        order.append("FIRST_STABLE_READ")
        raise ValueError("pre-identity input rejected")

    monkeypatch.setattr(runner, "_allocate_failure_memory_reserve", observed_allocate)
    monkeypatch.setattr(
        runner.VerificationDurableStoreV180R12R4,
        "read_stable",
        rejected_read,
    )
    with pytest.raises(ValueError, match="pre-identity input rejected"):
        runner.verify_retained_campaign_measurement_once_v180r12r4(
            repository,
            expected_manifest_sha256="0" * 64,
            expected_prereg_commit="pre-identity",
            watchdog_seconds=30,
        )
    assert order == ["ALLOCATE_RESERVE", "FIRST_STABLE_READ"]


def test_failure_directory_observation_streams_without_unbounded_listdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "streaming-directory"
    observed = repository / "observed"
    observed.mkdir(parents=True)
    for name in ("z", "a", "m"):
        (observed / name).write_bytes(b"")
    store = runner.VerificationDurableStoreV180R12R4(repository)

    def forbidden_listdir(*_args, **_kwargs):
        raise AssertionError("failure observation called unbounded listdir")

    monkeypatch.setattr(runner.os, "listdir", forbidden_listdir)
    try:
        row = runner._failure_observation(
            store, "observed", byte_cap=1, kind="DIRECTORY"
        )
    finally:
        store.close()
    assert row["state"] == "PRESENT"
    assert row["directory_entries"] == ["a", "m", "z"]


def test_oversized_runtime_cas_directory_still_freezes_typed_failure(
    tmp_path: Path,
    success_bundle: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, ids = _repository(tmp_path, success_bundle)

    def hostile(*_args, **_kwargs):
        cas = repository / runner.RUNTIME_CAS_ROOT_RELATIVE_PATH
        cas.mkdir()
        for ordinal in range(
            runner.VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP + 1
        ):
            (cas / f"entry-{ordinal:04d}").touch()
        raise ValueError("primary after oversized CAS")

    monkeypatch.setattr(
        runner.independent_verifier,
        "verify_campaign_measurement_terminal_independently_v180r12r4",
        hostile,
    )
    with pytest.raises(ValueError, match="primary after oversized CAS"):
        _invoke(repository, ids)
    failure = loads_canonical_json(
        (repository / runner.VERIFICATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    cas_row = next(
        row
        for row in failure["partial_artifact_observations"]
        if row["relative_path"] == runner.RUNTIME_CAS_ROOT_RELATIVE_PATH
    )
    assert cas_row["state"] == "READ_ERROR"
    assert cas_row["read_error_type"] == "DIRECTORY_OBSERVATION_CAP_EXCEEDED"
    assert cas_row["directory_entries"] is None


def test_control_character_directory_inventory_fits_the_failure_reserve(
    tmp_path: Path,
    success_bundle: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, ids = _repository(tmp_path, success_bundle)
    entry_count = 1_048
    control_suffix = "\x01" * 245

    def hostile(*_args, **_kwargs):
        cas = repository / runner.RUNTIME_CAS_ROOT_RELATIVE_PATH
        cas.mkdir()
        for ordinal in range(entry_count):
            (cas / f"{ordinal:04d}-{control_suffix}").touch()
        raise ValueError("primary after worst-case JSON escaping")

    monkeypatch.setattr(
        runner.independent_verifier,
        "verify_campaign_measurement_terminal_independently_v180r12r4",
        hostile,
    )
    with pytest.raises(ValueError, match="worst-case JSON escaping"):
        _invoke(repository, ids)
    failure_raw = (
        repository / runner.VERIFICATION_FAILURE_RELATIVE_PATH
    ).read_bytes()
    failure = loads_canonical_json(failure_raw)
    cas_row = next(
        row
        for row in failure["partial_artifact_observations"]
        if row["relative_path"] == runner.RUNTIME_CAS_ROOT_RELATIVE_PATH
    )
    names = cas_row["directory_entries"]
    assert cas_row["state"] == "PRESENT"
    assert len(names) == entry_count
    assert sum(len(name.encode("utf-8")) for name in names) == 262_000
    assert 262_000 <= runner.VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP
    assert b"\\u0001" in failure_raw
    assert len(failure_raw) <= runner.FAILURE_EMERGENCY_RESERVE_BYTES


def test_failure_releases_reserve_between_neutralize_and_restore(
    tmp_path: Path,
    success_bundle: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, ids = _repository(tmp_path, success_bundle)
    monkeypatch.setattr(
        runner.independent_verifier,
        "verify_campaign_measurement_terminal_independently_v180r12r4",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("primary")),
    )
    order: list[str] = []
    real_neutralize = runner._VerificationWatchdog.neutralize
    real_restore = runner._VerificationWatchdog.restore
    real_release = runner._release_failure_memory_reserve

    def observed_neutralize(self):
        order.append("neutralize")
        return real_neutralize(self)

    def observed_release(reserve):
        if reserve is not None:
            order.append("release")
        return real_release(reserve)

    def observed_restore(self):
        order.append("restore")
        assert "release" in order
        return real_restore(self)

    monkeypatch.setattr(runner._VerificationWatchdog, "neutralize", observed_neutralize)
    monkeypatch.setattr(runner, "_release_failure_memory_reserve", observed_release)
    monkeypatch.setattr(runner._VerificationWatchdog, "restore", observed_restore)
    with pytest.raises(ValueError, match="primary"):
        _invoke(repository, ids)
    assert order[:3] == ["neutralize", "release", "restore"]


@pytest.mark.parametrize("injection_point", ("cancel", "ignore"))
def test_second_alarm_during_both_neutralization_edges_still_freezes_failure(
    tmp_path: Path,
    success_bundle: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    injection_point: str,
) -> None:
    repository, ids = _repository(tmp_path, success_bundle)
    monkeypatch.setattr(
        runner.independent_verifier,
        "verify_campaign_measurement_terminal_independently_v180r12r4",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("primary")),
    )
    injected = False
    real_setitimer = runner.signal.setitimer
    real_signal = runner.signal.signal

    def hostile_setitimer(which, seconds, interval=0.0):
        nonlocal injected
        result = real_setitimer(which, seconds, interval)
        if injection_point == "cancel" and seconds == 0.0 and not injected:
            injected = True
            runner._VerificationWatchdog._expired(runner.signal.SIGALRM, None)
        return result

    def hostile_signal(signum, handler):
        nonlocal injected
        result = real_signal(signum, handler)
        if (
            injection_point == "ignore"
            and handler is runner.signal.SIG_IGN
            and not injected
        ):
            injected = True
            runner._VerificationWatchdog._expired(runner.signal.SIGALRM, None)
        return result

    monkeypatch.setattr(runner.signal, "setitimer", hostile_setitimer)
    monkeypatch.setattr(runner.signal, "signal", hostile_signal)
    with pytest.raises(ValueError, match="primary"):
        _invoke(repository, ids)
    failure = loads_canonical_json(
        (repository / runner.VERIFICATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    cleanup = failure["watchdog_cleanup_observation"]
    assert injected is True
    assert cleanup["secondary_observations"]
    assert cleanup["secondary_observations"][0]["failure_type"] == (
        "V180R12R4VerificationTimeout"
    )
    assert failure["failure_type"] == "ValueError"
