from __future__ import annotations

import copy
import base64
import errno
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/probe_v180r12r4r3_atomic_cgroup_birth_readiness.py"
SPEC = importlib.util.spec_from_file_location(
    "v180r12r4r3_atomic_birth_probe", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


def _properties(**updates: str) -> dict[str, str]:
    contract = probe.build_target_lifecycle_contract(os.geteuid())
    values = {
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "active",
        "ControlGroup": "/expected/target",
        "BindsTo": probe.SERVICE_UNIT_NAME,
        "After": f"app.slice {probe.SERVICE_UNIT_NAME}",
        "Delegate": "no",
        "CollectMode": "inactive-or-failed",
        "Slice": probe.SERVICE_SLICE,
        "Transient": "yes",
        "FragmentPath": contract["transient_fragment_path"],
        "UnitFileState": "transient",
        "Job": "",
    }
    values.update(updates)
    return values


def _raw(properties: dict[str, str]) -> bytes:
    return (
        "".join(
            f"{key}={properties[key]}\n"
            for key in probe.TARGET_MANAGER_ACTIVE_PROPERTIES
        )
    ).encode("utf-8")


def _result(raw: bytes, argv: tuple[str, ...] = ("/fake/show",)):
    return probe.BoundedProcessResult(argv, 0, raw, b"", False, False)


def _reidentify(
    document: dict[str, object], *, domain: str, identity_field: str
) -> dict[str, object]:
    retained = copy.deepcopy(document)
    retained.pop(identity_field, None)
    retained[identity_field] = probe._domain_id(domain, retained)
    return retained


def _create_result():
    argv = tuple(
        probe.build_target_lifecycle_contract(os.geteuid())["create_argv"]
    )
    return probe.BoundedProcessResult(
        argv,
        0,
        b'o "/org/freedesktop/systemd1/job/123"\n',
        b"",
        False,
        False,
    )


def _absence_properties() -> dict[str, str]:
    return {
        "LoadState": "loaded",
        "ActiveState": "inactive",
        "SubState": "dead",
        "ControlGroup": "",
        "BindsTo": "",
        "After": probe.SERVICE_SLICE,
        "Delegate": "no",
        "CollectMode": "inactive",
        "Slice": probe.SERVICE_SLICE,
        "Transient": "no",
        "FragmentPath": "",
        "UnitFileState": "",
        "Job": "",
    }


def _absence_result() -> probe.BoundedProcessResult:
    contract = probe.build_target_lifecycle_contract(os.geteuid())
    raw = "".join(
        f"{key}={_absence_properties()[key]}\n"
        for key in probe.TARGET_MANAGER_ABSENCE_PROPERTIES
    ).encode("utf-8")
    return probe.BoundedProcessResult(
        tuple(contract["absence_show_argv"]),
        0,
        raw,
        b"",
        False,
        False,
    )


class _CreateProcessAdapter:
    def __init__(
        self,
        *,
        malformed_precreate: bool = False,
        malformed_active: bool = False,
    ) -> None:
        self.malformed_precreate = malformed_precreate
        self.malformed_active = malformed_active
        self.calls: list[tuple[str, ...]] = []
        self.show_calls = 0

    def run(self, argv, **_kwargs):
        retained = tuple(argv)
        self.calls.append(retained)
        contract = probe.build_target_lifecycle_contract(os.geteuid())
        if retained == tuple(contract["absence_show_argv"]):
            self.show_calls += 1
            if self.show_calls == 1:
                raw = (
                    b"LoadState=loaded"
                    if self.malformed_precreate
                    else _absence_result().stdout
                )
            else:
                raw = (
                    b"LoadState=loaded"
                    if self.malformed_active
                    else _raw(_properties())
                )
        elif retained == tuple(contract["create_argv"]):
            raw = _create_result().stdout
        else:
            raise AssertionError(f"unexpected manager argv: {retained!r}")
        return probe.BoundedProcessResult(
            retained, 0, raw, b"", False, False
        )


def _base_create_diagnostic_arguments(
    *,
    trace: probe.TargetManagerPollTrace,
    full: bool,
    device: int | None,
    inode: int | None,
    phase: str | None,
) -> dict[str, object]:
    return {
        "target_membership": "/expected/target",
        "precreate_absence_show_result": _absence_result(),
        "precreate_manager_properties": _absence_properties(),
        "precreate_manager_implicit_absence": True,
        "precreate_target_path_absent": True,
        "precreate_transient_fragment_absent": True,
        "precreate_transient_fragment_path": (
            probe.build_target_lifecycle_contract(os.geteuid())[
                "transient_fragment_path"
            ]
        ),
        "precreate_transient_fragment_stat_errno": errno.ENOENT,
        "precreate_parent_stat_errno": errno.ENOENT,
        "precreate_parent_openat_errno": errno.ENOENT,
        "precreate_parent_inventory": [],
        "manager_create_result": _create_result(),
        "manager_create_job_path": "/org/freedesktop/systemd1/job/123",
        "ownership_acquired": True,
        "trace": trace,
        "full_target_path_ofd_conformance": full,
        "target_device": device,
        "target_inode": inode,
        "exception_phase": phase,
    }


def _success_create_diagnostic(device: int, inode: int) -> dict[str, object]:
    _conformance, trace = probe.poll_target_manager_conformance(
        lambda: _result(_raw(_properties())),
        expected_control_group="/expected/target",
        deadline_ns=10**30,
        sleep=lambda _seconds: None,
    )
    return probe.build_target_create_diagnostic(
        **_base_create_diagnostic_arguments(
            trace=trace,
            full=True,
            device=device,
            inode=inode,
            phase=None,
        ),
        exception_cause=None,
        target_creation_error=None,
    )


def _unit_only_create_diagnostic() -> dict[str, object]:
    try:
        probe.poll_target_manager_conformance(
            lambda: _result(b"LoadState=loaded"),
            expected_control_group="/expected/target",
            deadline_ns=10**30,
            sleep=lambda _seconds: None,
        )
    except probe.TargetManagerPollFailure as failure:
        outer = probe.make_target_creation_error(
            error_number=failure.errno,
            message=(
                "manager target creation stopped before full path/OFD "
                "conformance"
            ),
            target=None,
            cause=failure.cause,
            diagnostic_arguments=_base_create_diagnostic_arguments(
                trace=failure.trace,
                full=False,
                device=None,
                inode=None,
                phase=failure.phase,
            ),
        )
        assert outer.diagnostic is not None
        return outer.diagnostic
    raise AssertionError("malformed manager output unexpectedly parsed")


def test_successor_identity_is_fresh_and_binds_consumed_r4() -> None:
    lineage = probe.preflight_lineage()
    assert probe.PREFLIGHT_ORDINAL == 3
    assert probe.TARGET_ORDINAL == 3
    assert lineage["predecessor_inner_failure_id"] == (
        "b021afb816f3406af885182682cfc2e619035ff7d5fedde0f51a3904e60005d8"
    )
    assert lineage["predecessor_outer_launch_failure_id"] == (
        "4bf2769cc0d5f90b9156e00f4679998fe837d616bfdf6d006661a461026307e0"
    )
    assert lineage["predecessor_frozen_source_commit_id"] == (
        "8359fa2fd93405dacbeaf4428e7c77cce16b2728"
    )
    assert lineage["predecessor_frozen_source_tree_id"] == (
        "38d140913c43fd6bcf61c4396d50547fcf5d995c"
    )
    assert probe.PREFLIGHT_TOKEN not in probe.SERVICE_UNIT_NAME.replace(
        probe.PREFLIGHT_TOKEN, "", 1
    )
    assert "v180r12r4r3" in probe.SERVICE_UNIT_NAME
    assert "v180r12r4_atomic_birth_readiness" not in (
        probe.ARTIFACT_ROOT_RELATIVE_PATH
    )
    replay = dict(lineage)
    replay["ordinal"] = 0
    with pytest.raises(probe.AuthorityError):
        probe.derive_preflight_token(replay)


def test_predecessor_terminal_closure_is_exact_and_tamper_rejected() -> None:
    facts = probe.observe_predecessor_terminal_artifact_facts(ROOT)
    assert [row["byte_count"] for row in facts] == [
        1362,
        1439,
        17723,
        2911,
        1621,
        3733,
        16732,
    ]
    assert [row["sha256"] for row in facts] == [
        "07432f3cdd7d68968f06ef67736ecb42b7a2ca6a18e6ff6f3a23182c8398ef51",
        "60ca7831a1ee8f86bdf780762af2f51635157efe0569f0efae3ead592750ac5f",
        "c31cf9e73c71614352b47556e89184def9846762aa1b5f65d7388b994a1784fb",
        "8363c5203a40392b636bcd8c4e45c58491962d9287cb326534a292cfc39f9bf9",
        "821b1ed994e8c3e9853089ad529cf1ef6aa4f5dd2641157beb61c5ce65c597ff",
        "8cd573a8c47829a9cb1ec3d3a0b9b66995f2178d9bd74ae627bb37e85517517b",
        "33abb2f982ec9bfd49ee6c79ddb2e8834f7bdf9adcd883171d005a5cf93c58cf",
    ]
    assert probe.validate_predecessor_terminal_artifact_facts(facts) == facts
    tampered = copy.deepcopy(facts)
    tampered[5]["sha256"] = "0" * 64
    payload = dict(tampered[5])
    del payload["predecessor_artifact_fact_id"]
    tampered[5]["predecessor_artifact_fact_id"] = probe._domain_id(
        probe.PREDECESSOR_ARTIFACT_FACT_DOMAIN, payload
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_predecessor_terminal_artifact_facts(tampered)


def test_predecessor_probe_source_closure_matches_frozen_blob_bytes() -> None:
    predecessor = ROOT / probe.PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH
    raw = predecessor.read_bytes()
    assert len(raw) == probe.PREDECESSOR_PROBE_SOURCE_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == probe.PREDECESSOR_PROBE_SOURCE_SHA256
    assert probe._git_blob_id(raw) == probe.PREDECESSOR_PROBE_SOURCE_GIT_BLOB_ID


def _host_property_snapshot(
    phase: str, *, override: tuple[str, bytes] | None = None
) -> dict[str, object]:
    raw = {
        "fstatfs_type": f"{probe.CGROUP2_SUPER_MAGIC}\n".encode("ascii"),
        "cgroup.controllers": b"cpu memory pids\n",
        "cgroup.subtree_control": b"memory pids\n",
        "cgroup.type": b"domain\n",
    }
    if override is not None:
        raw[override[0]] = override[1]
    return probe.build_host_parent_property_snapshot(
        phase=phase,
        app_slice_path=(
            "/sys/fs/cgroup/user.slice/user-1000.slice/"
            "user@1000.service/app.slice"
        ),
        raw_properties=raw,
    )


@pytest.mark.parametrize(
    ("field", "changed_raw"),
    (
        (
            "fstatfs_type",
            f"{probe.CGROUP2_SUPER_MAGIC + 1}\n".encode("ascii"),
        ),
        ("cgroup.controllers", b"cpu memory\n"),
        ("cgroup.subtree_control", b"memory\n"),
        ("cgroup.type", b"threaded\n"),
    ),
)
def test_host_parent_single_property_mismatch_is_exact_and_typed(
    field: str, changed_raw: bytes
) -> None:
    expected = _host_property_snapshot("PREPARE")
    observed = _host_property_snapshot(
        "INNER_ACTIVE", override=(field, changed_raw)
    )
    cause = OSError(
        errno.ESTALE, f"host app.slice property mismatch: {field}"
    )
    diagnostic = probe.build_host_parent_conformance_diagnostic(
        phase="INNER_ACTIVE",
        expected_snapshot=expected,
        observed_snapshot=observed,
        cause=cause,
    )
    assert probe.validate_host_parent_conformance_diagnostic(
        diagnostic
    ) == diagnostic
    assert diagnostic["mismatch_rows"] == [
        {
            "field": field,
            "expected": expected["parsed_properties"][field],
            "observed": observed["parsed_properties"][field],
        }
    ]
    assert diagnostic["cause"] == {
        "error_type": "OSError",
        "message": (
            f"[Errno {errno.ESTALE}] host app.slice property mismatch: "
            f"{field}"
        ),
        "errno": errno.ESTALE,
        "errno_name": errno.errorcode[errno.ESTALE],
    }
    assert diagnostic["conformant"] is False


def test_host_parent_property_diagnostic_rejects_tamper_and_reidentification(
) -> None:
    expected = _host_property_snapshot("PREPARE")
    observed = _host_property_snapshot(
        "PRELAUNCH", override=("cgroup.type", b"threaded\n")
    )
    diagnostic = probe.build_host_parent_conformance_diagnostic(
        phase="PRELAUNCH",
        expected_snapshot=expected,
        observed_snapshot=observed,
        cause=OSError(
            errno.ESTALE,
            "host app.slice property mismatch: cgroup.type",
        ),
    )
    tampered = copy.deepcopy(diagnostic)
    tampered["mismatch_rows"][0]["observed"] = "domain"
    with pytest.raises(probe.AuthorityError, match="self-ID"):
        probe.validate_host_parent_conformance_diagnostic(tampered)

    reidentified = copy.deepcopy(diagnostic)
    reidentified["cause"]["message"] = "forged"
    reidentified = _reidentify(
        reidentified,
        domain=probe.HOST_PARENT_CONFORMANCE_DIAGNOSTIC_DOMAIN,
        identity_field="host_parent_conformance_diagnostic_id",
    )
    with pytest.raises(probe.AuthorityError, match="reidentified"):
        probe.validate_host_parent_conformance_diagnostic(reidentified)


def test_host_parent_partial_read_failure_retains_raw_prefix_and_exact_cause(
) -> None:
    raw = {
        "fstatfs_type": f"{probe.CGROUP2_SUPER_MAGIC}\n".encode("ascii"),
        "cgroup.controllers": b"cpu memory pids\n",
    }
    parsed = {
        name: probe._parse_host_parent_property_bytes(name, value)
        for name, value in raw.items()
    }
    diagnostic = probe.build_host_parent_observation_failure(
        phase="INNER_ACTIVE",
        app_slice_path=(
            "/sys/fs/cgroup/user.slice/user-1000.slice/"
            "user@1000.service/app.slice"
        ),
        failed_property="cgroup.subtree_control",
        raw_properties=raw,
        parsed_properties=parsed,
        cause=OSError(errno.EIO, "injected property read failure"),
    )
    assert probe.validate_host_parent_observation_failure(
        diagnostic
    ) == diagnostic
    assert set(diagnostic["raw_properties"]) == {
        "fstatfs_type",
        "cgroup.controllers",
    }
    assert diagnostic["parsed_properties"] == parsed
    assert diagnostic["cause"] == {
        "error_type": "OSError",
        "message": f"[Errno {errno.EIO}] injected property read failure",
        "errno": errno.EIO,
        "errno_name": errno.errorcode[errno.EIO],
    }


@pytest.mark.parametrize(
    "field",
    ("app_slice_inode", "owner_uid"),
)
def test_host_parent_inode_and_ownership_mismatch_have_typed_diagnostic(
    field: str,
) -> None:
    expected = {
        name: index
        for index, name in enumerate(
            probe.HOST_PARENT_IDENTITY_PROPERTY_NAMES, 1
        )
    }
    observed = dict(expected)
    observed[field] += 1000
    diagnostic = probe.build_host_parent_identity_conformance_diagnostic(
        phase="INNER_ACTIVE",
        expected_properties=expected,
        observed_properties=observed,
        cause=OSError(
            errno.ESTALE,
            f"host app.slice identity mismatch: {field}",
        ),
    )
    assert probe.validate_host_parent_identity_conformance_diagnostic(
        diagnostic
    ) == diagnostic
    assert diagnostic["mismatch_rows"] == [
        {
            "field": field,
            "expected": expected[field],
            "observed": observed[field],
        }
    ]
    assert diagnostic["expected_properties_raw"]["byte_count"] > 0
    assert diagnostic["observed_properties_raw"]["sha256"] == (
        hashlib.sha256(probe.canonical_json_bytes(observed)).hexdigest()
    )


def _source_unit_result(
    properties: dict[str, str]
) -> probe.BoundedProcessResult:
    raw = "".join(
        f"{name}={properties[name]}\n"
        for name in probe.SOURCE_MANAGER_ACTIVE_PROPERTIES
    ).encode("utf-8")
    return probe.BoundedProcessResult(
        tuple(probe._source_active_show_argv()),
        0,
        raw,
        b"",
        False,
        False,
    )


@pytest.mark.parametrize(
    ("field", "changed", "enabled", "controllers"),
    (
        ("Delegate", "no", False, []),
        ("DelegateControllers", "cpu", True, ["cpu"]),
    ),
)
def test_source_unit_delegation_single_field_mismatch_is_exact(
    field: str,
    changed: str,
    enabled: bool,
    controllers: list[str],
) -> None:
    uid = os.geteuid()
    source_membership = (
        f"/user.slice/user-{uid}.slice/user@{uid}.service/app.slice/"
        f"{probe.SERVICE_UNIT_NAME}"
    )
    observed = probe._source_expected_properties(
        uid=uid, source_membership=source_membership
    )
    observed[field] = changed
    diagnostic = probe.build_source_unit_conformance_diagnostic(
        uid=uid,
        source_membership=source_membership,
        manager_show_result=_source_unit_result(observed),
        observed_properties=observed,
        cause=OSError(
            errno.EPROTO, f"source unit property mismatch: {field}"
        ),
    )
    assert probe.validate_source_unit_conformance_diagnostic(
        diagnostic
    ) == diagnostic
    assert diagnostic["mismatch_rows"] == [
        {
            "field": field,
            "expected": (
                probe._source_expected_properties(
                    uid=uid, source_membership=source_membership
                )[field]
            ),
            "observed": changed,
        }
    ]
    assert diagnostic["delegation_enabled"] is enabled
    assert diagnostic["delegated_controllers"] == controllers


def test_delegate_empty_contract_and_source_conformance_are_explicit_and_sealed(
    tmp_path: Path,
) -> None:
    invocation = probe.build_systemd_invocation_contract(
        repository_root=tmp_path,
        external_root_path=tmp_path / "external.json",
        artifact_root=tmp_path / "artifacts",
    )
    options = invocation["systemd_options"]
    assert options.count("--property=Delegate=") == 1
    assert not any(
        option.startswith("--property=Delegate=")
        and option != "--property=Delegate="
        for option in options
    )
    assert invocation["delegation_enabled"] is True
    assert invocation["delegated_controllers"] == []

    uid = os.geteuid()
    membership = (
        f"/user.slice/user-{uid}.slice/user@{uid}.service/app.slice/"
        f"{probe.SERVICE_UNIT_NAME}"
    )
    observed = probe._source_expected_properties(
        uid=uid, source_membership=membership
    )
    diagnostic = probe.build_source_unit_conformance_diagnostic(
        uid=uid,
        source_membership=membership,
        manager_show_result=_source_unit_result(observed),
        observed_properties=observed,
        cause=None,
    )
    assert diagnostic["delegation_enabled"] is True
    assert diagnostic["delegated_controllers"] == []
    assert diagnostic["conformant"] is True
    probe.validate_source_unit_conformance_diagnostic(diagnostic)

    reidentified = copy.deepcopy(diagnostic)
    reidentified["delegated_controllers"] = ["cpu"]
    reidentified = _reidentify(
        reidentified,
        domain=probe.SOURCE_UNIT_CONFORMANCE_DIAGNOSTIC_DOMAIN,
        identity_field="source_unit_conformance_diagnostic_id",
    )
    with pytest.raises(probe.AuthorityError, match="replay"):
        probe.validate_source_unit_conformance_diagnostic(reidentified)


def test_typed_conformance_contains_replayable_expected_map() -> None:
    result = probe._target_manager_active(
        _properties(), expected_control_group="/expected/target"
    )
    assert result.conformant is True
    document = result.as_document()
    assert document["expected_properties"]["After"] == (
        f"CONTAINS:{probe.SERVICE_UNIT_NAME}"
    )
    assert probe.validate_target_manager_conformance_document(document) == document
    tampered = copy.deepcopy(document)
    tampered["expected_properties"]["Delegate"] = "yes"
    payload = dict(tampered)
    del payload["target_conformance_id"]
    tampered["target_conformance_id"] = probe._domain_id(
        probe.TARGET_CONFORMANCE_DOMAIN, payload
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_target_manager_conformance_document(tampered)


def test_success_target_create_diagnostic_separately_proves_full_path_ofd() -> None:
    _conformance, trace = probe.poll_target_manager_conformance(
        lambda: _result(_raw(_properties())),
        expected_control_group="/expected/target",
        deadline_ns=10**30,
        sleep=lambda _seconds: None,
    )
    diagnostic = probe.build_target_create_diagnostic(
        **_base_create_diagnostic_arguments(
            trace=trace,
            full=True,
            device=31,
            inode=47,
            phase=None,
        ),
        exception_cause=None,
        target_creation_error=None,
    )
    assert probe.validate_target_create_diagnostic(diagnostic) == diagnostic
    assert diagnostic["manager_unit_ownership_acquired"] is True
    assert diagnostic["full_target_path_ofd_conformance"] is True
    assert diagnostic["conformance_stages"] == {
        name: True for name in probe.TARGET_CREATE_CONFORMANCE_STAGE_NAMES
    }
    assert diagnostic["target_device"] == 31
    assert diagnostic["target_inode"] == 47
    tampered = copy.deepcopy(diagnostic)
    tampered["precreate_transient_fragment_stat_errno"] = errno.EACCES
    tampered = _reidentify(
        tampered,
        domain=probe.TARGET_CREATE_DIAGNOSTIC_DOMAIN,
        identity_field="target_create_diagnostic_id",
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_target_create_diagnostic(tampered)


@pytest.mark.parametrize(
    ("substate", "expected_mismatch_keys"),
    (
        ("active", ["ControlGroup"]),
        ("exited", ["ControlGroup", "SubState"]),
    ),
)
def test_stable_static_mismatch_fails_promptly_with_mismatch_keys(
    substate: str,
    expected_mismatch_keys: list[str],
) -> None:
    bad = _raw(_properties(ControlGroup="", SubState=substate))
    calls = 0

    def observe():
        nonlocal calls
        calls += 1
        return _result(bad)

    with pytest.raises(probe.TargetManagerPollFailure) as caught:
        probe.poll_target_manager_conformance(
            observe,
            expected_control_group="/expected/target",
            deadline_ns=10**30,
            sleep=lambda _seconds: None,
        )
    failure = caught.value
    assert failure.phase == "ACTIVE_CONFORMANCE_STABLE_MISMATCH"
    assert calls == probe.TARGET_MANAGER_STABLE_MISMATCH_POLLS == 2
    assert failure.trace.stable_mismatch is True
    assert (
        failure.trace.last_conformance["mismatch_keys"]
        == expected_mismatch_keys
    )
    create_error = probe.make_target_creation_error(
        error_number=errno.EPROTO,
        message=(
            "manager target creation stopped before full path/OFD conformance"
        ),
        target=None,
        cause=failure.cause,
        diagnostic_arguments=_base_create_diagnostic_arguments(
            trace=failure.trace,
            full=False,
            device=None,
            inode=None,
            phase=failure.phase,
        ),
    )
    assert create_error.diagnostic is not None
    diagnostic = create_error.diagnostic
    assert probe.validate_target_create_diagnostic(diagnostic) == diagnostic
    assert diagnostic["manager_unit_ownership_acquired"] is True
    assert diagnostic["full_target_path_ofd_conformance"] is False
    assert diagnostic["conformance_stages"] == {
        name: False for name in probe.TARGET_CREATE_CONFORMANCE_STAGE_NAMES
    }
    row = probe._substage_record(
        0, "TARGET_CREATE", "FAILED", diagnostic, create_error
    )
    assert probe.validate_substage_record(row, expected_index=0) == row


def test_repeated_transitional_state_is_not_prompt_failed() -> None:
    transitional = _raw(
        _properties(
            ActiveState="activating",
            SubState="start",
            Job="/org/freedesktop/systemd1/job/7",
        )
    )
    final = _raw(_properties())
    results = iter((_result(transitional), _result(transitional), _result(final)))
    conformance, trace = probe.poll_target_manager_conformance(
        lambda: next(results),
        expected_control_group="/expected/target",
        deadline_ns=10**30,
        sleep=lambda _seconds: None,
        max_polls=3,
    )
    assert conformance.conformant is True
    assert trace.poll_count == 3
    assert trace.stable_mismatch is False
    assert trace.stable_mismatch_observation_count == 0


def test_poll_drift_retains_first_last_changed_and_raw_summaries() -> None:
    rows = iter(
        (
            _result(_raw(_properties(ActiveState="activating", SubState="start", Job="/org/freedesktop/systemd1/job/7"))),
            _result(_raw(_properties(ActiveState="reloading", SubState="reload", Job="/org/freedesktop/systemd1/job/8"))),
            _result(_raw(_properties(ActiveState="activating", SubState="start", Job="/org/freedesktop/systemd1/job/7"))),
        )
    )
    with pytest.raises(probe.TargetManagerPollFailure) as caught:
        probe.poll_target_manager_conformance(
            lambda: next(rows),
            expected_control_group="/expected/target",
            deadline_ns=10**30,
            sleep=lambda _seconds: None,
            max_polls=3,
        )
    failure = caught.value
    assert failure.phase == "ACTIVE_CONFORMANCE_POLL_BOUND"
    trace = failure.trace
    assert trace.poll_count == 3
    assert trace.first_properties["ActiveState"] == "activating"
    assert trace.last_properties["ActiveState"] == "activating"
    assert [row["poll_index"] for row in trace.changed_property_maps] == [2, 3]
    assert len(trace.raw_stdout_observations) == 3
    assert all(
        row["byte_count"] > 0 and len(row["sha256"]) == 64
        for row in trace.raw_stdout_observations
    )


def test_poll_changed_map_is_replayed_from_raw_bytes_and_tamper_rejected() -> None:
    active_states = ("activating", "reloading")
    calls = 0

    def observe():
        nonlocal calls
        state = active_states[calls % len(active_states)]
        calls += 1
        substate = "start" if state == "activating" else "reload"
        return _result(
            _raw(
                _properties(
                    ActiveState=state,
                    SubState=substate,
                    Job=f"/org/freedesktop/systemd1/job/{calls}",
                )
            )
        )

    with pytest.raises(probe.TargetManagerPollFailure) as caught:
        probe.poll_target_manager_conformance(
            observe,
            expected_control_group="/expected/target",
            deadline_ns=10**30,
            sleep=lambda _seconds: None,
        )
    failure = caught.value
    assert failure.phase == "ACTIVE_CONFORMANCE_POLL_BOUND"
    outer = probe.make_target_creation_error(
        error_number=failure.errno,
        message=(
            "manager target creation stopped before full path/OFD conformance"
        ),
        target=None,
        cause=failure.cause,
        diagnostic_arguments=_base_create_diagnostic_arguments(
            trace=failure.trace,
            full=False,
            device=None,
            inode=None,
            phase=failure.phase,
        ),
    )
    diagnostic = outer.diagnostic
    assert diagnostic is not None
    assert diagnostic["manager_poll_count"] == probe.TARGET_MANAGER_MAX_POLLS
    assert diagnostic["changed_property_maps"][0]["changed_keys"] == [
        "ActiveState",
        "Job",
        "SubState",
    ]
    assert probe.validate_target_create_diagnostic(diagnostic) == diagnostic
    tampered = copy.deepcopy(diagnostic)
    tampered["changed_property_maps"][0]["changed_keys"] = []
    payload = dict(tampered)
    del payload["target_create_diagnostic_id"]
    tampered["target_create_diagnostic_id"] = probe._domain_id(
        probe.TARGET_CREATE_DIAGNOSTIC_DOMAIN, payload
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_target_create_diagnostic(tampered)


def test_poll_replay_rejects_observations_after_a_terminal_map() -> None:
    diagnostic = _success_create_diagnostic(31, 47)
    extra = copy.deepcopy(diagnostic["raw_stdout_observations"][0])
    extra["poll_index"] = 2
    diagnostic["manager_poll_count"] = 2
    diagnostic["raw_stdout_observations"].append(extra)
    diagnostic["raw_stdout_aggregate"] = probe._poll_raw_aggregate(
        diagnostic["raw_stdout_observations"]
    )
    diagnostic = _reidentify(
        diagnostic,
        domain=probe.TARGET_CREATE_DIAGNOSTIC_DOMAIN,
        identity_field="target_create_diagnostic_id",
    )
    with pytest.raises(
        probe.AuthorityError,
        match="after conformance",
    ):
        probe.validate_target_create_diagnostic(diagnostic)


def test_post_create_parse_error_retains_raw_fact_and_is_replay_tamper_evident() -> None:
    malformed = b"LoadState=loaded"
    with pytest.raises(probe.TargetManagerPollFailure) as caught:
        probe.poll_target_manager_conformance(
            lambda: _result(malformed),
            expected_control_group="/expected/target",
            deadline_ns=10**30,
            sleep=lambda _seconds: None,
        )
    failure = caught.value
    assert failure.phase == "ACTIVE_SHOW_PARSE"
    assert failure.trace.poll_count == 1
    raw_fact = failure.trace.raw_stdout_observations[0]
    assert raw_fact == {
        "poll_index": 1,
        "byte_count": len(malformed),
        "sha256": hashlib.sha256(malformed).hexdigest(),
        "base64": base64.b64encode(malformed).decode("ascii"),
    }
    create_error = probe.make_target_creation_error(
        error_number=errno.EPROTO,
        message=(
            "manager target creation stopped before full path/OFD conformance"
        ),
        target=None,
        cause=failure.cause,
        diagnostic_arguments=_base_create_diagnostic_arguments(
            trace=failure.trace,
            full=False,
            device=None,
            inode=None,
            phase=failure.phase,
        ),
    )
    assert create_error.diagnostic is not None
    diagnostic = create_error.diagnostic
    probe.validate_target_create_diagnostic(diagnostic)
    tampered = copy.deepcopy(diagnostic)
    tampered["raw_stdout_observations"][0]["sha256"] = "f" * 64
    payload = dict(tampered)
    del payload["target_create_diagnostic_id"]
    tampered["target_create_diagnostic_id"] = probe._domain_id(
        probe.TARGET_CREATE_DIAGNOSTIC_DOMAIN, payload
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_target_create_diagnostic(tampered)


@pytest.mark.parametrize(
    ("malformed_manager_show", "app_fd_is_valid"),
    ((True, True), (False, False)),
)
def test_precreate_failure_retains_each_independent_absence_half(
    tmp_path: Path,
    malformed_manager_show: bool,
    app_fd_is_valid: bool,
) -> None:
    valid_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    app_fd = valid_fd if app_fd_is_valid else -1
    process = _CreateProcessAdapter(
        malformed_precreate=malformed_manager_show
    )
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.process_adapter = process
    service = _service(app_fd, tmp_path)
    try:
        with pytest.raises(probe.TargetCreationError) as caught:
            adapter.create_target(service, 10**30)
        error = caught.value
        probe.validate_target_creation_error_join(error)
        diagnostic = error.diagnostic
        assert diagnostic is not None
        assert diagnostic["exception_phase"] == "PRECREATE_ABSENCE"
        assert diagnostic["manager_create_result"] is None
        assert diagnostic["manager_unit_ownership_acquired"] is False
        assert len(process.calls) == 1
        if malformed_manager_show:
            assert diagnostic["precreate_absence_show_result"] is not None
            assert diagnostic["precreate_manager_properties"] is None
            assert diagnostic["precreate_manager_implicit_absence"] is None
            assert diagnostic["precreate_target_path_absent"] is True
        else:
            assert diagnostic["precreate_manager_properties"] == (
                _absence_properties()
            )
            assert diagnostic["precreate_manager_implicit_absence"] is True
            assert diagnostic["precreate_target_path_absent"] is False
            assert diagnostic["precreate_parent_stat_errno"] == errno.EBADF
            assert diagnostic["precreate_parent_openat_errno"] == errno.EBADF
            assert type(diagnostic["precreate_parent_inventory"]) is list
            assert (
                probe.TARGET_CGROUP_NAME
                not in diagnostic["precreate_parent_inventory"]
            )
            assert diagnostic["precreate_transient_fragment_absent"] is True
            assert diagnostic["precreate_transient_fragment_path"] == (
                probe.build_target_lifecycle_contract(os.geteuid())[
                    "transient_fragment_path"
                ]
            )
            assert (
                diagnostic["precreate_transient_fragment_stat_errno"]
                == errno.ENOENT
            )
    finally:
        os.close(valid_fd)


def test_precreate_parent_observer_exception_preserves_unknown_tristates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    process = _CreateProcessAdapter()
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.process_adapter = process
    service = _service(app_fd, tmp_path)

    def fail_parent_observation(*_args, **_kwargs):
        raise OSError(errno.EIO, "injected parent observation failure")

    monkeypatch.setattr(
        probe,
        "_observe_parent_named_path",
        fail_parent_observation,
    )
    try:
        with pytest.raises(probe.TargetCreationError) as caught:
            adapter.create_target(service, 10**30)
        diagnostic = caught.value.diagnostic
        probe.validate_target_creation_error_join(caught.value)
        assert diagnostic["exception_phase"] == "PRECREATE_ABSENCE"
        assert diagnostic["precreate_manager_implicit_absence"] is True
        assert diagnostic["precreate_target_path_absent"] is None
        assert diagnostic["precreate_parent_stat_errno"] is None
        assert diagnostic["precreate_parent_openat_errno"] is None
        assert diagnostic["precreate_parent_inventory"] is None
        assert diagnostic["precreate_transient_fragment_absent"] is None
        assert diagnostic["precreate_transient_fragment_path"] is None
        assert diagnostic["precreate_transient_fragment_stat_errno"] is None
        assert len(process.calls) == 1
    finally:
        os.close(app_fd)


def test_post_create_parse_failure_never_uses_unit_only_name_stop(
    tmp_path: Path,
) -> None:
    app_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    process = _CreateProcessAdapter(malformed_active=True)
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.process_adapter = process
    service = _service(app_fd, tmp_path)
    try:
        with pytest.raises(probe.TargetCreationError) as caught:
            adapter.create_target(service, 10**30)
        error = caught.value
        probe.validate_target_creation_error_join(error)
        target = error.target
        assert target is not None
        assert target.manager_unit_ownership_acquired is True
        assert target.full_target_path_ofd_conformance is False
        diagnostic = error.diagnostic
        assert diagnostic is not None
        assert diagnostic["exception_phase"] == "ACTIVE_SHOW_PARSE"
        assert diagnostic["manager_create_result"] is not None
        assert diagnostic["manager_unit_ownership_acquired"] is True
        assert diagnostic["manager_poll_count"] == 1
        assert diagnostic["raw_stdout_observations"][0]["base64"] == (
            base64.b64encode(b"LoadState=loaded").decode("ascii")
        )
        assert len(process.calls) == 3
        cleanup = _CleanupAdapter(tmp_path)
        with pytest.raises(probe.TargetRemovalError) as cleanup_error:
            cleanup.remove_target(service, target, 10**30)
        probe.validate_target_removal_error_join(cleanup_error.value)
        assert cleanup_error.value.diagnostic["exception_phase"] == (
            "PRESTOP_IDENTITY"
        )
        assert target.stop_requested is False
        assert cleanup.stop_calls == 0
    finally:
        os.close(app_fd)


class _CleanupAdapter(probe.LinuxRuntimeAdapter):
    def __init__(
        self,
        app_path: Path,
        *,
        stop_fails: bool = False,
        stop_behavior: str = "remove",
        absence_fails: bool = False,
    ) -> None:
        self.app_path = app_path
        self.stop_fails = stop_fails
        self.stop_behavior = stop_behavior
        self.absence_fails = absence_fails
        self.stop_calls = 0

    @staticmethod
    def _target_contract(_service):
        return probe.build_target_lifecycle_contract(os.geteuid())

    @staticmethod
    def _fstatfs_type(_descriptor: int) -> int:
        return probe.CGROUP2_SUPER_MAGIC

    def _run_target_manager(
        self,
        service,
        argv_key,
        deadline_ns,
        *,
        require_empty_stdout,
    ):
        assert argv_key == "stop_argv"
        self.stop_calls += 1
        if self.stop_fails:
            raise OSError(errno.EIO, "injected stop failure")
        target_path = self.app_path / probe.TARGET_CGROUP_NAME
        if target_path.exists():
            if self.stop_behavior == "remove":
                os.rmdir(target_path)
            elif self.stop_behavior in {"replacement", "retained_inode"}:
                os.rename(target_path, self.app_path / "retained-target")
                if self.stop_behavior == "replacement":
                    target_path.mkdir()
            else:
                raise AssertionError(
                    f"unexpected stop behavior: {self.stop_behavior}"
                )
        argv = tuple(self._target_contract(service)["stop_argv"])
        return probe.BoundedProcessResult(argv, 0, b"", b"", False, False)

    def _target_manager_absence_properties(self, _service, _deadline_ns):
        if self.absence_fails:
            raise OSError(errno.EIO, "injected absence-show failure")
        return _absence_properties()


def _service(app_fd: int, app_path: Path):
    return probe.ServiceHandle(
        app_slice_fd=app_fd,
        service_fd=-1,
        app_slice_path=str(app_path),
        service_path=str(app_path / "source"),
        source_membership="/source",
        target_membership="/expected/target",
        observation={
            "target_lifecycle_contract": probe.build_target_lifecycle_contract(
                os.geteuid()
            )
        },
    )


def test_unit_only_owned_cleanup_never_stops_by_reusable_unit_name(
    tmp_path: Path,
) -> None:
    app_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        service = _service(app_fd, tmp_path)
        target = probe.TargetHandle(
            -1,
            probe.TARGET_CGROUP_NAME,
            str(tmp_path / probe.TARGET_CGROUP_NAME),
            service.target_membership,
            -1,
            -1,
            owned=True,
            manager_created=True,
            identity_continuous=False,
            residual_possible=True,
            manager_unit_ownership_acquired=True,
            full_target_path_ofd_conformance=False,
            create_diagnostic=_unit_only_create_diagnostic(),
        )
        adapter = _CleanupAdapter(tmp_path)
        with pytest.raises(probe.TargetRemovalError) as caught:
            adapter.remove_target(service, target, 10**30)
        probe.validate_target_removal_error_join(caught.value)
        diagnostic = caught.value.diagnostic
        assert diagnostic["ownership_scope"] == "UNIT_ONLY"
        assert diagnostic["exception_phase"] == "PRESTOP_IDENTITY"
        assert diagnostic["manager_stop_requested"] is False
        assert diagnostic["unconditional_same_uid_replacement_safety_claimed"] is False
        assert diagnostic["manager_stop_identity_binding_contract"] == (
            probe.MANAGER_STOP_IDENTITY_BINDING
        )
        assert diagnostic["requested_manager_stop_identity_binding"] == (
            probe.MANAGER_STOP_NOT_DISPATCHED
        )
        assert target.manager_implicit_absence_proven is False
        assert target.residual_possible is True
        assert adapter.stop_calls == 0
    finally:
        os.close(app_fd)


def test_unit_only_cleanup_rejects_before_even_a_failing_stop(tmp_path: Path) -> None:
    app_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        service = _service(app_fd, tmp_path)
        target = probe.TargetHandle(
            -1,
            probe.TARGET_CGROUP_NAME,
            str(tmp_path / probe.TARGET_CGROUP_NAME),
            service.target_membership,
            -1,
            -1,
            owned=True,
            manager_created=True,
            identity_continuous=False,
            residual_possible=True,
            manager_unit_ownership_acquired=True,
            full_target_path_ofd_conformance=False,
            create_diagnostic=_unit_only_create_diagnostic(),
        )
        adapter = _CleanupAdapter(tmp_path, stop_fails=True)
        with pytest.raises(probe.TargetRemovalError) as caught:
            adapter.remove_target(service, target, 10**30)
        diagnostic = caught.value.diagnostic
        assert probe.validate_target_cleanup_diagnostic(diagnostic) == diagnostic
        row = probe._substage_record(
            0,
            "CLEANUP_TARGET_REMOVE",
            "FAILED",
            diagnostic,
            caught.value,
        )
        assert probe.validate_substage_record(row, expected_index=0) == row
        assert diagnostic["exception_phase"] == "PRESTOP_IDENTITY"
        assert diagnostic["manager_stop_requested"] is False
        assert adapter.stop_calls == 0
        assert diagnostic["manager_implicit_absence_proven"] is False
        tampered = copy.deepcopy(diagnostic)
        tampered["manager_implicit_absence_proven"] = True
        payload = dict(tampered)
        del payload["target_cleanup_diagnostic_id"]
        tampered["target_cleanup_diagnostic_id"] = probe._domain_id(
            probe.TARGET_CLEANUP_DIAGNOSTIC_DOMAIN, payload
        )
        with pytest.raises(probe.AuthorityError):
            probe.validate_target_cleanup_diagnostic(tampered)
        tampered_binding = copy.deepcopy(diagnostic)
        tampered_binding["requested_manager_stop_identity_binding"] = (
            probe.MANAGER_STOP_IDENTITY_BINDING
        )
        tampered_binding = _reidentify(
            tampered_binding,
            domain=probe.TARGET_CLEANUP_DIAGNOSTIC_DOMAIN,
            identity_field="target_cleanup_diagnostic_id",
        )
        with pytest.raises(probe.AuthorityError):
            probe.validate_target_cleanup_diagnostic(tampered_binding)
        assert target.stop_requested is False
        assert target.manager_implicit_absence_proven is False
        assert target.residual_possible is True
        with pytest.raises(OSError, match="residual is possible"):
            adapter.target_absent(service, target, 10**30)
    finally:
        os.close(app_fd)


def test_full_path_ofd_cleanup_proves_kernfs_named_detach_without_unlink_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_path = tmp_path / probe.TARGET_CGROUP_NAME
    target_path.mkdir()
    app_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    target_fd = os.open(target_path, os.O_RDONLY | os.O_DIRECTORY)
    metadata = os.fstat(target_fd)
    try:
        service = _service(app_fd, tmp_path)
        target = probe.TargetHandle(
            target_fd,
            probe.TARGET_CGROUP_NAME,
            str(target_path),
            service.target_membership,
            metadata.st_dev,
            metadata.st_ino,
            owned=True,
            manager_created=True,
            identity_continuous=True,
            residual_possible=False,
            manager_unit_ownership_acquired=True,
            full_target_path_ofd_conformance=True,
            create_diagnostic=_success_create_diagnostic(
                metadata.st_dev, metadata.st_ino
            ),
        )
        retained_fact = {
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "mode": stat.S_IFDIR | 0o755,
            "nlink": 2,
            "fstatfs_type": probe.CGROUP2_SUPER_MAGIC,
            "proc_fd_link": f"{target_path} (deleted)",
            "proc_fd_link_errno": None,
            "deleted_marker": True,
            "cgroup_type_errno": errno.ENOENT,
            "cgroup_events_errno": errno.ENOENT,
            "cgroup_procs_errno": errno.ENOENT,
            "conformant": True,
        }
        monkeypatch.setattr(
            probe,
            "_observe_retained_ofd_detach",
            lambda _target: dict(retained_fact),
        )
        adapter = _CleanupAdapter(tmp_path)
        detail = adapter.remove_target(service, target, 10**30)
        assert detail["ownership_scope"] == "UNIT_PATH_OFD"
        assert detail["named_path_detached_and_manager_implicit_absence"] is True
        assert detail["retained_ofd_detach_fact"] == retained_fact
        assert detail["retained_ofd_detach_fact"]["nlink"] == 2
        assert detail["posix_inode_unlink_claimed"] is False
        cleanup_diagnostic = detail["cleanup_diagnostic"]
        assert cleanup_diagnostic[
            "unconditional_same_uid_replacement_safety_claimed"
        ] is False
        assert cleanup_diagnostic["manager_stop_identity_binding_contract"] == (
            probe.MANAGER_STOP_IDENTITY_BINDING
        )
        assert cleanup_diagnostic["requested_manager_stop_identity_binding"] == (
            probe.MANAGER_STOP_IDENTITY_BINDING
        )
        assert target.named_path_detached_and_manager_implicit_absence is True
        assert target.directory_fd == -1
        assert (
            probe._validated_target_removal_detail(target, detail) == detail
        )

        # Keep the nested diagnostic internally replayable while moving its
        # claimed named path to a foreign parent.  The production consumer
        # must still reject it against the authoritative TargetHandle.
        tampered = copy.deepcopy(detail)
        diagnostic = tampered["cleanup_diagnostic"]
        foreign_path = f"/foreign/app.slice/{probe.TARGET_CGROUP_NAME}"
        diagnostic["target_path"] = foreign_path
        diagnostic["retained_ofd_detach_fact"]["proc_fd_link"] = (
            foreign_path + " (deleted)"
        )
        tampered["cleanup_diagnostic"] = _reidentify(
            diagnostic,
            domain=probe.TARGET_CLEANUP_DIAGNOSTIC_DOMAIN,
            identity_field="target_cleanup_diagnostic_id",
        )
        assert (
            probe.validate_target_cleanup_diagnostic(
                tampered["cleanup_diagnostic"]
            )
            == tampered["cleanup_diagnostic"]
        )
        with pytest.raises(OSError) as caught:
            probe._validated_target_removal_detail(target, tampered)
        assert caught.value.errno == errno.EPROTO

        for mutate in (
            lambda value: value["parent_named_path_observation"].update(
                {"stat_errno": errno.EACCES}
            ),
            lambda value: value["retained_ofd_detach_fact"].update(
                {"deleted_marker": False}
            ),
        ):
            forged = copy.deepcopy(detail["cleanup_diagnostic"])
            mutate(forged)
            forged = _reidentify(
                forged,
                domain=probe.TARGET_CLEANUP_DIAGNOSTIC_DOMAIN,
                identity_field="target_cleanup_diagnostic_id",
            )
            with pytest.raises(probe.AuthorityError):
                probe.validate_target_cleanup_diagnostic(forged)
    finally:
        if target_fd >= 0:
            try:
                os.close(target_fd)
            except OSError:
                pass
        os.close(app_fd)


def test_cleanup_replacement_and_retained_ofd_failures_have_exact_phases(
    tmp_path: Path,
) -> None:
    for stop_behavior, expected_phase in (
        ("replacement", "POSTSTOP_REPLACEMENT"),
        ("retained_inode", "POSTSTOP_RETAINED_OFD_DETACH"),
    ):
        case = tmp_path / stop_behavior
        case.mkdir()
        target_path = case / probe.TARGET_CGROUP_NAME
        target_path.mkdir()
        app_fd = os.open(case, os.O_RDONLY | os.O_DIRECTORY)
        target_fd = os.open(target_path, os.O_RDONLY | os.O_DIRECTORY)
        metadata = os.fstat(target_fd)
        service = _service(app_fd, case)
        target = probe.TargetHandle(
            target_fd,
            probe.TARGET_CGROUP_NAME,
            str(target_path),
            service.target_membership,
            metadata.st_dev,
            metadata.st_ino,
            owned=True,
            manager_created=True,
            identity_continuous=True,
            residual_possible=False,
            manager_unit_ownership_acquired=True,
            full_target_path_ofd_conformance=True,
            create_diagnostic=_success_create_diagnostic(
                metadata.st_dev, metadata.st_ino
            ),
        )
        try:
            with pytest.raises(probe.TargetRemovalError) as caught:
                _CleanupAdapter(
                    case, stop_behavior=stop_behavior
                ).remove_target(service, target, 10**30)
            diagnostic = caught.value.diagnostic
            assert diagnostic["exception_phase"] == expected_phase
            probe.validate_target_cleanup_diagnostic(diagnostic)
            tampered = copy.deepcopy(diagnostic)
            tampered["exception_phase"] = "POSTSTOP_ABSENCE"
            tampered = _reidentify(
                tampered,
                domain=probe.TARGET_CLEANUP_DIAGNOSTIC_DOMAIN,
                identity_field="target_cleanup_diagnostic_id",
            )
            with pytest.raises(probe.AuthorityError):
                probe.validate_target_cleanup_diagnostic(tampered)
        finally:
            try:
                os.close(target_fd)
            except OSError:
                pass
            os.close(app_fd)


def test_cleanup_diagnostic_stop_requested_is_per_attempt_not_historical(
    tmp_path: Path,
) -> None:
    target_path = tmp_path / probe.TARGET_CGROUP_NAME
    target_path.mkdir()
    retained_path = tmp_path / "retained-before-retry"
    app_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    target_fd = os.open(target_path, os.O_RDONLY | os.O_DIRECTORY)
    metadata = os.fstat(target_fd)
    service = _service(app_fd, tmp_path)
    target = probe.TargetHandle(
        target_fd,
        probe.TARGET_CGROUP_NAME,
        str(target_path),
        service.target_membership,
        metadata.st_dev,
        metadata.st_ino,
        owned=True,
        manager_created=True,
        identity_continuous=True,
        stop_requested=True,
        residual_possible=True,
        manager_unit_ownership_acquired=True,
        full_target_path_ofd_conformance=True,
        create_diagnostic=_success_create_diagnostic(
            metadata.st_dev, metadata.st_ino
        ),
    )
    os.rename(target_path, retained_path)
    try:
        with pytest.raises(probe.TargetRemovalError) as caught:
            _CleanupAdapter(tmp_path).remove_target(service, target, 10**30)
        diagnostic = caught.value.diagnostic
        assert diagnostic["exception_phase"] == "PRESTOP_IDENTITY"
        assert diagnostic["manager_stop_requested"] is False
        assert target.stop_requested is True
        probe.validate_target_cleanup_diagnostic(diagnostic)
    finally:
        os.close(target_fd)
        os.close(app_fd)


def test_host_conformance_reidentified_phase_and_path_drift_are_rejected(
) -> None:
    expected = _host_property_snapshot("PREPARE")
    observed = _host_property_snapshot(
        "PRELAUNCH", override=("cgroup.type", b"threaded\n")
    )
    diagnostic = probe.build_host_parent_conformance_diagnostic(
        phase="PRELAUNCH",
        expected_snapshot=expected,
        observed_snapshot=observed,
        cause=OSError(
            errno.ESTALE,
            "host app.slice property mismatch: cgroup.type",
        ),
    )

    wrong_phase = copy.deepcopy(diagnostic)
    wrong_phase["expected_snapshot"]["phase"] = "POSTLAUNCH"
    wrong_phase["expected_snapshot"] = _reidentify(
        wrong_phase["expected_snapshot"],
        domain=probe.HOST_PARENT_PROPERTY_SNAPSHOT_DOMAIN,
        identity_field="host_parent_property_snapshot_id",
    )
    wrong_phase = _reidentify(
        wrong_phase,
        domain=probe.HOST_PARENT_CONFORMANCE_DIAGNOSTIC_DOMAIN,
        identity_field="host_parent_conformance_diagnostic_id",
    )
    with pytest.raises(probe.AuthorityError, match="replay"):
        probe.validate_host_parent_conformance_diagnostic(wrong_phase)

    alien_path = copy.deepcopy(diagnostic)
    alien_path["observed_snapshot"]["app_slice_path"] = "/alien/app.slice"
    alien_path["observed_snapshot"] = _reidentify(
        alien_path["observed_snapshot"],
        domain=probe.HOST_PARENT_PROPERTY_SNAPSHOT_DOMAIN,
        identity_field="host_parent_property_snapshot_id",
    )
    alien_path = _reidentify(
        alien_path,
        domain=probe.HOST_PARENT_CONFORMANCE_DIAGNOSTIC_DOMAIN,
        identity_field="host_parent_conformance_diagnostic_id",
    )
    with pytest.raises(probe.AuthorityError, match="replay"):
        probe.validate_host_parent_conformance_diagnostic(alien_path)


def test_host_observation_failure_replays_prefix_path_kind_and_parse_cause(
) -> None:
    app_path = (
        f"/sys/fs/cgroup/user.slice/user-{os.geteuid()}.slice/"
        f"user@{os.geteuid()}.service/app.slice"
    )
    fstatfs_raw = f"{probe.CGROUP2_SUPER_MAGIC}\n".encode("ascii")
    controllers_raw = b"cpu memory pids\n"
    read_failure = probe.build_host_parent_observation_failure(
        phase="INNER_ACTIVE",
        app_slice_path=app_path,
        failed_property="cgroup.subtree_control",
        raw_properties={
            "fstatfs_type": fstatfs_raw,
            "cgroup.controllers": controllers_raw,
        },
        parsed_properties={
            "fstatfs_type": probe.CGROUP2_SUPER_MAGIC,
            "cgroup.controllers": ["cpu", "memory", "pids"],
        },
        cause=OSError(errno.EIO, "fixture read failure"),
    )
    assert read_failure["failure_kind"] == "READ"

    alien = copy.deepcopy(read_failure)
    alien["app_slice_path"] = "/alien/app.slice"
    alien = _reidentify(
        alien,
        domain=probe.HOST_PARENT_OBSERVATION_FAILURE_DOMAIN,
        identity_field="host_parent_observation_failure_id",
    )
    with pytest.raises(probe.AuthorityError, match="values"):
        probe.validate_host_parent_observation_failure(alien)

    later_property = copy.deepcopy(read_failure)
    later_property["raw_properties"]["cgroup.type"] = probe._output_fact(
        b"domain\n"
    )
    later_property = _reidentify(
        later_property,
        domain=probe.HOST_PARENT_OBSERVATION_FAILURE_DOMAIN,
        identity_field="host_parent_observation_failure_id",
    )
    with pytest.raises(probe.AuthorityError, match="values"):
        probe.validate_host_parent_observation_failure(later_property)

    parseable = copy.deepcopy(read_failure)
    parseable["failure_kind"] = "PARSE"
    parseable["raw_properties"]["cgroup.subtree_control"] = (
        probe._output_fact(b"memory pids\n")
    )
    parseable = _reidentify(
        parseable,
        domain=probe.HOST_PARENT_OBSERVATION_FAILURE_DOMAIN,
        identity_field="host_parent_observation_failure_id",
    )
    with pytest.raises(probe.AuthorityError, match="parseable"):
        probe.validate_host_parent_observation_failure(parseable)

    invalid_raw = b"memory memory\n"
    with pytest.raises(probe.AuthorityError) as parsed_error:
        probe._parse_host_parent_property_bytes(
            "cgroup.subtree_control", invalid_raw
        )
    parse_failure = probe.build_host_parent_observation_failure(
        phase="INNER_ACTIVE",
        app_slice_path=app_path,
        failed_property="cgroup.subtree_control",
        raw_properties={
            "fstatfs_type": fstatfs_raw,
            "cgroup.controllers": controllers_raw,
            "cgroup.subtree_control": invalid_raw,
        },
        parsed_properties={
            "fstatfs_type": probe.CGROUP2_SUPER_MAGIC,
            "cgroup.controllers": ["cpu", "memory", "pids"],
        },
        cause=parsed_error.value,
    )
    forged_cause = copy.deepcopy(parse_failure)
    forged_cause["cause"]["message"] = "forged parse cause"
    forged_cause = _reidentify(
        forged_cause,
        domain=probe.HOST_PARENT_OBSERVATION_FAILURE_DOMAIN,
        identity_field="host_parent_observation_failure_id",
    )
    with pytest.raises(probe.AuthorityError, match="raw-byte replay"):
        probe.validate_host_parent_observation_failure(forged_cause)


def test_substage_exact_error_join_rejects_reidentified_cause_drift() -> None:
    original = OSError(errno.EIO, "fixture ordinary failure")
    row = probe._substage_record(
        0,
        "GIT_AUTHORITY",
        "FAILED",
        probe.build_ordinary_failure_diagnostic(
            substage="GIT_AUTHORITY", error=original
        ),
        original,
    )
    forged = copy.deepcopy(row)
    forged["detail"]["cause"] = probe._error_fact(
        OSError(errno.ENOSPC, "forged ordinary failure")
    )
    forged["detail"] = _reidentify(
        forged["detail"],
        domain=probe.ORDINARY_FAILURE_DIAGNOSTIC_DOMAIN,
        identity_field="ordinary_failure_diagnostic_id",
    )
    forged = _reidentify(
        forged,
        domain=probe.SUBSTAGE_DOMAIN,
        identity_field="substage_record_id",
    )
    with pytest.raises(probe.AuthorityError, match="exact row join"):
        probe.validate_substage_record(forged, expected_index=0)

    app_path = (
        f"/sys/fs/cgroup/user.slice/user-{os.geteuid()}.slice/"
        f"user@{os.geteuid()}.service/app.slice"
    )
    diagnostic = probe.build_host_parent_observation_failure(
        phase="INNER_ACTIVE",
        app_slice_path=app_path,
        failed_property="fstatfs_type",
        raw_properties={},
        parsed_properties={},
        cause=OSError(errno.EIO, "fixture host read failure"),
    )
    wrapper = probe.HostParentObservationError(diagnostic)
    special = probe._substage_record(
        0,
        "SERVICE_PLACEMENT_AND_NCA_PERMISSION",
        "FAILED",
        diagnostic,
        wrapper,
    )
    mutated = copy.deepcopy(special)
    mutated["detail"]["cause"]["message"] = "forged host read cause"
    mutated["detail"] = _reidentify(
        mutated["detail"],
        domain=probe.HOST_PARENT_OBSERVATION_FAILURE_DOMAIN,
        identity_field="host_parent_observation_failure_id",
    )
    mutated = _reidentify(
        mutated,
        domain=probe.SUBSTAGE_DOMAIN,
        identity_field="substage_record_id",
    )
    with pytest.raises(probe.AuthorityError, match="wrapper join"):
        probe.validate_substage_record(mutated, expected_index=0)


def test_source_success_result_cannot_be_reidentified_as_unknown_failure(
) -> None:
    uid = os.geteuid()
    membership = (
        f"/user.slice/user-{uid}.slice/user@{uid}.service/app.slice/"
        f"{probe.SERVICE_UNIT_NAME}"
    )
    observed = probe._source_expected_properties(
        uid=uid, source_membership=membership
    )
    diagnostic = probe.build_source_unit_conformance_diagnostic(
        uid=uid,
        source_membership=membership,
        manager_show_result=_source_unit_result(observed),
        observed_properties=observed,
        cause=None,
    )
    forged = copy.deepcopy(diagnostic)
    forged["observed_properties"] = None
    forged["mismatch_rows"] = [
        {"field": key, "expected": value, "observed": None}
        for key, value in sorted(forged["expected_properties"].items())
    ]
    forged["delegation_enabled"] = None
    forged["delegated_controllers"] = None
    forged["conformant"] = False
    forged["cause"] = probe._error_fact(
        OSError(errno.EIO, "forged source observation failure")
    )
    forged = _reidentify(
        forged,
        domain=probe.SOURCE_UNIT_CONFORMANCE_DIAGNOSTIC_DOMAIN,
        identity_field="source_unit_conformance_diagnostic_id",
    )
    with pytest.raises(probe.AuthorityError, match="successful result"):
        probe.validate_source_unit_conformance_diagnostic(forged)


def test_target_precreate_success_result_cannot_be_reidentified_as_unknown(
) -> None:
    cause = OSError(errno.EBADF, "fixture parent observation failure")
    diagnostic_arguments = {
        "target_membership": "/expected/target",
        "precreate_absence_show_result": _absence_result(),
        "precreate_manager_properties": _absence_properties(),
        "precreate_manager_implicit_absence": True,
        "precreate_target_path_absent": False,
        "precreate_transient_fragment_absent": True,
        "precreate_transient_fragment_path": (
            probe.build_target_lifecycle_contract(os.geteuid())[
                "transient_fragment_path"
            ]
        ),
        "precreate_transient_fragment_stat_errno": errno.ENOENT,
        "precreate_parent_stat_errno": errno.EBADF,
        "precreate_parent_openat_errno": errno.EBADF,
        "precreate_parent_inventory": [],
        "manager_create_result": None,
        "manager_create_job_path": None,
        "ownership_acquired": False,
        "trace": probe.TargetManagerPollTrace(),
        "full_target_path_ofd_conformance": False,
        "target_device": None,
        "target_inode": None,
        "exception_phase": "PRECREATE_ABSENCE",
    }
    outer = probe.make_target_creation_error(
        error_number=errno.EBADF,
        message="target pre-create absence proof failed",
        target=None,
        cause=cause,
        diagnostic_arguments=diagnostic_arguments,
    )
    assert outer.diagnostic is not None
    forged = copy.deepcopy(outer.diagnostic)
    forged["precreate_manager_properties"] = None
    forged["precreate_manager_implicit_absence"] = None
    forged = _reidentify(
        forged,
        domain=probe.TARGET_CREATE_DIAGNOSTIC_DOMAIN,
        identity_field="target_create_diagnostic_id",
    )
    with pytest.raises(probe.AuthorityError, match="retained-result replay"):
        probe.validate_target_create_diagnostic(forged)


def test_successor_source_has_no_r4_formal_invocation() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "probe_v180r12r4_atomic_cgroup_birth_readiness.py --" not in source
    assert "v180r12r4_atomic_birth_readiness/LAUNCH_RECEIPT" not in source
    assert "probe_v180r12r4r2_atomic_cgroup_birth_readiness.py --" not in source
    assert "v180r12r4r2_atomic_birth_readiness/LAUNCH_RECEIPT" not in source
    assert "claimed_inode_unlinked" not in source
