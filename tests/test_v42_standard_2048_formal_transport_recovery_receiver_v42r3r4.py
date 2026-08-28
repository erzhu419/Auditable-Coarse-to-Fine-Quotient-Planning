from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
RECEIVER_PATH = (
    ROOT
    / "scripts/v42_standard_2048_formal_transport_recovery_receiver_v42r3r4.py"
)
SPEC = importlib.util.spec_from_file_location(
    "_acfqp_test_formal_transport_recovery_receiver_v42r3r4", RECEIVER_PATH
)
assert SPEC is not None and SPEC.loader is not None
receiver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receiver)


def _fact(raw: bytes) -> dict[str, object]:
    return {"byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _tool_fact(path: str, seed: bytes) -> dict[str, object]:
    return {
        "path": path,
        "sha256": hashlib.sha256(seed).hexdigest(),
        "byte_count": len(seed),
        "mode": 0o755,
        "uid": 0,
        "gid": 0,
        "st_nlink": 1,
    }


def _live_tool_fact(path: str) -> dict[str, object]:
    raw = Path(path).read_bytes()
    observed = os.lstat(path)
    return {
        "path": path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "mode": stat.S_IMODE(observed.st_mode),
        "uid": observed.st_uid,
        "gid": observed.st_gid,
        "st_nlink": observed.st_nlink,
    }


def _controller() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": "test.v42r3.controller",
        "schema_version": receiver.RETAINED_PLAN_VERSION,
    }
    return {
        **payload,
        "controller_source_manifest_id": receiver._content_id(  # noqa: SLF001
            receiver.RETAINED_CONTROLLER_MANIFEST_DOMAIN, payload
        ),
    }


def _plan() -> dict[str, object]:
    loader_raw = b"loader\n"
    authority_raw = b"authority\n"
    receiver_raw = b"receiver\n"
    runtime = {
        "hostname": receiver.REMOTE_HOSTNAME,
        "user": receiver.REMOTE_USER,
        "uid": receiver.REMOTE_UID,
        "gid": receiver.REMOTE_GID,
        "python_invocation": receiver.REMOTE_PYTHON_PATH,
        "python_realpath": receiver.REMOTE_PYTHON_REALPATH,
        "python_version": list(receiver.REMOTE_PYTHON_VERSION),
        "python_isolated_flag": 1,
        "python_no_site_flag": 1,
        "python_dont_write_bytecode": True,
    }
    tools = {
        name: _tool_fact(path, (name + "\n").encode())
        for name, path in receiver.REMOTE_TOOL_PATHS.items()
    }
    payload: dict[str, object] = {
        "schema": receiver.RETAINED_PLAN_SCHEMA,
        "schema_version": receiver.RETAINED_PLAN_VERSION,
        "formal_identity": receiver.FORMAL_IDENTITY,
        "global_execution_ordinal": receiver.GLOBAL_EXECUTION_ORDINAL,
        "fixed_remote_root": receiver.FIXED_REMOTE_ROOT,
        "fixed_source_root": receiver.FIXED_SOURCE_ROOT,
        "remote_journal_root": receiver.RETAINED_REMOTE_JOURNAL_ROOT,
        "expected_remote_hostname": receiver.REMOTE_HOSTNAME,
        "observed_remote_hostname": receiver.REMOTE_HOSTNAME,
        "observed_remote_user": receiver.REMOTE_USER,
        "observed_remote_uid": receiver.REMOTE_UID,
        "observed_remote_gid": receiver.REMOTE_GID,
        "host_epoch_receipt": {
            "observed_runtime": runtime,
            "remote_tool_facts": tools,
        },
        "remote_tool_facts": tools,
        "controller_source_manifest_id": _controller()[
            "controller_source_manifest_id"
        ],
        "probe_loader_artifact": _fact(loader_raw),
        "formal_authority_artifact": _fact(authority_raw),
        "probe_receiver_artifact": _fact(receiver_raw),
        "controller_same_effect_dispatch_replay_forbidden_after_marker": True,
        "unit_absence_never_proves_service_never_started": True,
    }
    return {
        **payload,
        "formal_transport_plan_id": receiver._content_id(  # noqa: SLF001
            receiver.RETAINED_PLAN_DOMAIN, payload
        ),
    }


def _ingress(*, plan: dict[str, object] | None = None) -> dict[str, object]:
    retained_plan = _plan() if plan is None else plan
    attempt_id = "a" * 64
    return {
        "schema": receiver.INGRESS_SCHEMA,
        "schema_version": receiver.SCHEMA_VERSION,
        "recovery_plan_id": "b" * 64,
        "retained_launch_occurrence_id": "c" * 64,
        "retained_formal_transport_plan": retained_plan,
        "retained_formal_transport_plan_id": retained_plan[
            "formal_transport_plan_id"
        ],
        "retained_local_launch_attempt_id": attempt_id,
        "retained_remote_journal_root": receiver.RETAINED_REMOTE_JOURNAL_ROOT,
        "retained_systemd_unit_name": (
            receiver.SYSTEMD_UNIT_PREFIX + attempt_id + ".service"
        ),
        "expected_remote_hostname": receiver.REMOTE_HOSTNAME,
        "expected_remote_uid": receiver.REMOTE_UID,
        "expected_remote_gid": receiver.REMOTE_GID,
        "recovery_inspection_ordinal": receiver.RECOVERY_INSPECTION_ORDINAL,
    }


def _unit_values(*, load_state: str = "not-found") -> dict[str, str]:
    attempt_id = "a" * 64
    values = {field: "" for field in receiver.UNIT_SHOW_FIELDS}
    values.update(
        {
            "Id": receiver.SYSTEMD_UNIT_PREFIX + attempt_id + ".service",
            "LoadState": load_state,
            "ActiveState": "inactive",
            "SubState": "dead",
            "MainPID": "0",
            "FragmentPath": "",
            "ExecStart": "",
        }
    )
    return values


def _properties(values: dict[str, str]) -> bytes:
    return ("".join(f"{key}={value}\n" for key, value in values.items())).encode()


def test_unit_parser_accepts_exact_full_inventory_and_exposes_execstart_state() -> None:
    values = _unit_values()
    values["ExecStart"] = "{ path=/usr/bin/python3 ; argv[]=/usr/bin/python3 ; }"
    parsed, state = receiver._parse_unit_properties(_properties(values))  # noqa: SLF001
    assert set(parsed) == set(receiver.UNIT_SHOW_FIELDS) - {"ExecStart"}
    assert "ExecStart" not in parsed
    assert state == "PRESENT_NONEMPTY"


def test_unit_parser_accepts_only_execstart_omission_for_exact_absent_unit() -> None:
    values = _unit_values()
    del values["ExecStart"]
    parsed, state = receiver._parse_unit_properties(_properties(values))  # noqa: SLF001
    assert parsed["LoadState"] == "not-found"
    assert parsed["FragmentPath"] == ""
    assert state == "OMITTED_ONLY_FOR_NOT_FOUND_UNIT"


@pytest.mark.parametrize(
    ("mutation", "expected_message"),
    [
        (lambda values: values.__setitem__("LoadState", "loaded"), "inventory"),
        (lambda values: values.__setitem__("FragmentPath", "/tmp/unit"), "inventory"),
        (lambda values: values.pop("Result"), "inventory"),
        (lambda values: values.__setitem__("Unexpected", "x"), "inventory"),
    ],
)
def test_unit_parser_rejects_every_other_inventory_change(
    mutation, expected_message: str,
) -> None:
    values = _unit_values()
    del values["ExecStart"]
    mutation(values)
    with pytest.raises(receiver.V42R3R4RecoveryReceiverError, match=expected_message):
        receiver._parse_unit_properties(_properties(values))  # noqa: SLF001


def test_unit_parser_rejects_duplicate_property() -> None:
    raw = _properties(_unit_values()) + b"Result=duplicate\n"
    with pytest.raises(receiver.V42R3R4RecoveryReceiverError, match="duplicated"):
        receiver._parse_unit_properties(raw)  # noqa: SLF001


def test_unit_observation_normalizes_absent_unit_without_inventing_execstart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = _unit_values()
    del values["ExecStart"]
    monkeypatch.setattr(receiver, "_run_systemctl_show", lambda *_args, **_kw: _properties(values))
    observed = receiver._unit_observation(  # noqa: SLF001
        SimpleNamespace(),
        attempt_id="a" * 64,
        expected_unit=values["Id"],
    )
    assert observed["LoadState"] == "not-found"
    assert observed["MainPID"] == 0
    assert observed["LiveMainPIDArgv"] == []
    assert observed["LiveMainPIDArgvSource"] == "ABSENT_UNIT"
    assert observed["ExecStartPropertyState"] == (
        "OMITTED_ONLY_FOR_NOT_FOUND_UNIT"
    )
    assert "ExecStart" not in observed


def test_ingress_binds_retained_plan_content_root_unit_host_uid_and_gid() -> None:
    document = _ingress()
    raw = receiver._canonical_bytes(document)  # noqa: SLF001
    assert receiver._verify_ingress(raw, "b" * 64) == document  # noqa: SLF001

    for field, value in (
        ("retained_remote_journal_root", "/tmp/not-retained"),
        ("retained_systemd_unit_name", "wrong.service"),
        ("expected_remote_hostname", "wrong-host"),
        ("expected_remote_uid", 1001),
        ("expected_remote_gid", 1001),
    ):
        changed = _ingress()
        changed[field] = value
        with pytest.raises(receiver.V42R3R4RecoveryReceiverError):
            receiver._verify_ingress(  # noqa: SLF001
                receiver._canonical_bytes(changed), "b" * 64  # noqa: SLF001
            )


def test_ingress_rejects_plan_whose_claimed_content_id_does_not_match() -> None:
    document = _ingress()
    document["retained_formal_transport_plan"]["fixed_source_root"] = "/changed"
    with pytest.raises(receiver.V42R3R4RecoveryReceiverError, match="content ID"):
        receiver._verify_ingress(  # noqa: SLF001
            receiver._canonical_bytes(document), "b" * 64  # noqa: SLF001
        )


def test_ingress_rejects_retained_runtime_or_tool_receipt_drift() -> None:
    for mutate in (
        lambda plan: plan["host_epoch_receipt"]["observed_runtime"].__setitem__(
            "python_version", [3, 12, 4]
        ),
        lambda plan: plan["host_epoch_receipt"]["remote_tool_facts"][
            "systemctl"
        ].__setitem__("sha256", "g" * 64),
    ):
        plan = _plan()
        plan.pop("formal_transport_plan_id")
        mutate(plan)
        plan["formal_transport_plan_id"] = receiver._content_id(  # noqa: SLF001
            receiver.RETAINED_PLAN_DOMAIN, plan
        )
        document = _ingress(plan=plan)
        with pytest.raises(receiver.V42R3R4RecoveryReceiverError):
            receiver._verify_ingress(  # noqa: SLF001
                receiver._canonical_bytes(document), "b" * 64  # noqa: SLF001
            )


def test_executable_pin_rejects_digest_different_from_retained_fact() -> None:
    fact = _live_tool_fact(receiver.SYSTEMCTL_PATH)
    fact["sha256"] = "0" * 64
    with pytest.raises(
        receiver.V42R3R4RecoveryReceiverError,
        match="systemctl executable changed while pinned",
    ):
        receiver._ExecutablePin(fact, label="systemctl")  # noqa: SLF001


def test_current_python_runtime_rejects_nonmatching_proc_self_exe_inode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fact = _live_tool_fact(receiver.SYSTEMCTL_PATH)
    pin = receiver._ExecutablePin(fact, label="Python")  # noqa: SLF001
    fake_sys = SimpleNamespace(
        executable=receiver.SYSTEMCTL_PATH,
        version_info=(3, 12, 3),
        flags=SimpleNamespace(isolated=1, no_site=1),
        dont_write_bytecode=True,
    )
    runtime = {
        "python_invocation": receiver.SYSTEMCTL_PATH,
        "python_realpath": receiver.SYSTEMCTL_PATH,
        "python_version": [3, 12, 3],
        "python_isolated_flag": 1,
        "python_no_site_flag": 1,
        "python_dont_write_bytecode": True,
    }
    monkeypatch.setattr(receiver, "sys", fake_sys)
    try:
        with pytest.raises(
            receiver.V42R3R4RecoveryReceiverError,
            match="differs from retained exact evidence",
        ):
            receiver._verify_current_python_runtime(runtime, pin)  # noqa: SLF001
    finally:
        pin.close()


def test_absent_retained_journal_is_observed_twice_without_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "retained-absent"
    monkeypatch.setattr(receiver, "RETAINED_REMOTE_JOURNAL_ROOT", str(root))
    state, inventory, states, recovered = receiver._journal_observation(  # noqa: SLF001
        retained_plan=_plan(),
        plan_id=_plan()["formal_transport_plan_id"],
        attempt_id="a" * 64,
        expected_unit=receiver.SYSTEMD_UNIT_PREFIX + "a" * 64 + ".service",
    )
    assert (state, inventory, recovered) == ("ABSENT", [], {})
    assert states == {
        "launch_transport_attempt": "ABSENT",
        "launch_admission_receipt": "ABSENT",
        "service_wrapper_attestation": "ABSENT",
    }
    assert not root.exists()


def test_present_retained_journal_reads_exact_inventory_and_canonical_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "retained"
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    monkeypatch.setattr(receiver, "RETAINED_REMOTE_JOURNAL_ROOT", str(root))
    monkeypatch.setattr(receiver, "REMOTE_UID", os.getuid())
    monkeypatch.setattr(receiver, "REMOTE_GID", os.getgid())
    plan = _plan()
    loader_raw = b"loader\n"
    authority_raw = b"authority\n"
    receiver_raw = b"receiver\n"
    controller = _controller()
    attempt_payload = {
        "schema": (
            "acfqp.v42_formal_transport_successor_launch_transport_attempt.v42r3"
        ),
        "schema_version": receiver.RETAINED_PLAN_VERSION,
        "formal_transport_plan_id": plan["formal_transport_plan_id"],
        "local_launch_attempt_id": "a" * 64,
        "unit_name": receiver.SYSTEMD_UNIT_PREFIX + "a" * 64 + ".service",
        "operation": "LAUNCH",
        "network_effect_started": False,
        "systemd_admission_effect_started": False,
        "formal_execution_performed": False,
        "controller_same_effect_dispatch_replay_forbidden_after_network_marker": True,
    }
    attempt = {
        **attempt_payload,
        "formal_launch_transport_attempt_id": receiver._content_id(  # noqa: SLF001
            receiver.RETAINED_LAUNCH_TRANSPORT_ATTEMPT_DOMAIN,
            attempt_payload,
        ),
    }
    raw_by_name = {
        receiver.REMOTE_CONTROLLER_NAME: receiver._canonical_bytes(controller),  # noqa: SLF001
        receiver.REMOTE_LOADER_NAME: loader_raw,
        receiver.REMOTE_AUTHORITY_NAME: authority_raw,
        receiver.REMOTE_RECEIVER_NAME: receiver_raw,
        receiver.REMOTE_PLAN_NAME: receiver._canonical_bytes(plan),  # noqa: SLF001
        receiver.REMOTE_TRANSPORT_ATTEMPT_NAME: receiver._canonical_bytes(attempt),  # noqa: SLF001
    }
    for name, raw in raw_by_name.items():
        path = root / name
        path.write_bytes(raw)
        path.chmod(0o400)

    state, inventory, states, recovered = receiver._journal_observation(  # noqa: SLF001
        retained_plan=plan,
        plan_id=plan["formal_transport_plan_id"],
        attempt_id="a" * 64,
        expected_unit=receiver.SYSTEMD_UNIT_PREFIX + "a" * 64 + ".service",
    )
    assert state == "DIRECTORY"
    assert inventory == sorted(receiver.REMOTE_INITIAL_INVENTORY)
    assert states == {
        "launch_transport_attempt": "REGULAR_FILE",
        "launch_admission_receipt": "ABSENT",
        "service_wrapper_attestation": "ABSENT",
    }
    assert recovered == {"launch_transport_attempt": attempt}


def test_build_remote_inspection_is_canonical_id_bound_and_never_claims_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = _ingress()
    manager = {
        "kernel_boot_id": "91139880-050f-4104-89de-6666cce9d5a8",
        "linger_enabled": True,
        "linger_path": "/var/lib/systemd/linger/erzhu419",
        "user_manager_invocation_id": "ffbac9d8-6675-4a11-a8ec-6dab87dc2f72",
        "user_manager_main_pid": 2000,
        "user_manager_control_group": "/user.slice/user-1000.slice/user@1000.service",
    }
    unit = {
        "Id": document["retained_systemd_unit_name"],
        "LoadState": "not-found",
        "FragmentPath": "",
        "MainPID": 0,
        "LiveMainPIDArgv": [],
        "LiveMainPIDArgvSource": "ABSENT_UNIT",
        "ExecStartPropertyState": "OMITTED_ONLY_FOR_NOT_FOUND_UNIT",
    }

    pins: list[tuple[str, dict[str, object]]] = []

    class Pin:
        def __init__(self, fact, *, label: str) -> None:
            pins.append((label, fact))

        def close(self) -> None:
            pass

        def verify(self) -> None:
            pass

    monkeypatch.setattr(receiver.socket, "gethostname", lambda: receiver.REMOTE_HOSTNAME)
    monkeypatch.setattr(receiver.os, "getuid", lambda: receiver.REMOTE_UID)
    monkeypatch.setattr(receiver.os, "getgid", lambda: receiver.REMOTE_GID)
    monkeypatch.setattr(receiver, "_ExecutablePin", Pin)
    monkeypatch.setattr(receiver, "_verify_current_python_runtime", lambda *_args: None)
    monkeypatch.setattr(receiver, "_manager_binding", lambda _pin: manager)
    monkeypatch.setattr(receiver, "_unit_observation", lambda *_args, **_kw: unit)
    monkeypatch.setattr(
        receiver,
        "_journal_observation",
        lambda **_kw: (
            "ABSENT",
            [],
            {
                "launch_transport_attempt": "ABSENT",
                "launch_admission_receipt": "ABSENT",
                "service_wrapper_attestation": "ABSENT",
            },
            {},
        ),
    )
    inspection = receiver.build_remote_inspection(
        ingress_raw=receiver._canonical_bytes(document),  # noqa: SLF001
        expected_recovery_plan_id="b" * 64,
    )
    payload = {key: value for key, value in inspection.items() if key != "remote_inspection_id"}
    assert inspection["remote_inspection_id"] == receiver._content_id(  # noqa: SLF001
        receiver.REMOTE_INSPECTION_DOMAIN, payload
    )
    assert inspection["unit_observation"]["ExecStartPropertyState"] == (
        "OMITTED_ONLY_FOR_NOT_FOUND_UNIT"
    )
    assert inspection["authenticated_body_remote_filesystem_mutation_performed"] is False
    assert inspection["systemd_lifecycle_mutation_performed"] is False
    assert inspection["same_effect_reissued"] is False
    assert inspection["end_to_end_absence_claimed"] is False
    assert [label for label, _fact_value in pins] == ["Python", "systemctl"]
    assert pins[0][1]["path"] == receiver.REMOTE_PYTHON_REALPATH
    assert pins[1][1]["path"] == receiver.SYSTEMCTL_PATH
    assert receiver._canonical_bytes(inspection) == receiver._canonical_bytes(  # noqa: SLF001
        json.loads(receiver._canonical_bytes(inspection))  # noqa: SLF001
    )


def test_receiver_source_has_no_remote_write_lifecycle_or_runner_entry_path() -> None:
    source = RECEIVER_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "systemd-run",
        "mkdir(",
        ".mkdir(",
        ".write_text(",
        ".write_bytes(",
        ".unlink(",
        "os.replace(",
        "os.rename(",
        "os.execv",
        "scientific_runner",
    ):
        assert forbidden not in source
    assert "--user" in source
    assert '"show"' in source
    assert "authenticated_body_remote_filesystem_mutation_performed" in source
    assert "end_to_end_absence_claimed" in source
