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
SCRIPT = ROOT / "scripts/probe_v180r12r4r2_atomic_cgroup_birth_readiness.py"
SPEC = importlib.util.spec_from_file_location(
    "v180r12r4r2_atomic_birth_probe", SCRIPT
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
    assert probe.PREFLIGHT_ORDINAL == 2
    assert probe.TARGET_ORDINAL == 2
    assert lineage["predecessor_inner_failure_id"] == (
        "5c8c546a33ec18b01f6000407d045c115e85d8cba2ffb8ff512dc238af87c967"
    )
    assert lineage["predecessor_outer_launch_failure_id"] == (
        "8807acbb61b764d1a754423a9be1854c12a1645dc6a935419f696ed4d0351692"
    )
    assert lineage["predecessor_frozen_source_commit_id"] == (
        "349cdb47b9eeaf18906ccad1fb27aec0dca768cd"
    )
    assert lineage["predecessor_frozen_source_tree_id"] == (
        "4815ea8731779b0f259c74f08aaf31d3e93b93b1"
    )
    assert probe.PREFLIGHT_TOKEN not in probe.SERVICE_UNIT_NAME.replace(
        probe.PREFLIGHT_TOKEN, "", 1
    )
    assert "v180r12r4r2" in probe.SERVICE_UNIT_NAME
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
        1394,
        1470,
        14008,
        2625,
        1303,
        27470,
        6588,
    ]
    assert [row["sha256"] for row in facts] == [
        "c73138ab44a531c486301c9e63a7030ed43374cd370ee38c8046bffe09fa348f",
        "c3871bd046f416cd19e6f56b6a736d6ec01e67269b5b87dbcdf400b86b1a7e8f",
        "0ee7e587702872e9926891f69ce821d70a73fcaabe9764b38cff10ab8dea0836",
        "685d4b6fc05994e5452dd81cdbfc2ed20125ce9c6c77bacbeb3312f124016a89",
        "d94d24b05169e3afe5e17bb58b260ef3b53d036916edd4a492c994ddeaf6d80f",
        "376b593c76cf75842a515f80153b5a5c8b8e25d4cc57a0349917caf5dadfec73",
        "aadc5c7f8fcf82cf165c4063942ea29db159ee322836bbb0b416ac3b7ee4f941",
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
    assert diagnostic["unique_manager_unit_ownership_acquired"] is True
    assert diagnostic["full_target_path_ofd_conformance"] is True
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
    assert diagnostic["unique_manager_unit_ownership_acquired"] is True
    assert diagnostic["full_target_path_ofd_conformance"] is False
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
        assert diagnostic["unique_manager_unit_ownership_acquired"] is False
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
        assert diagnostic["unique_manager_unit_ownership_acquired"] is True
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


def test_successor_source_has_no_r4_formal_invocation() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "probe_v180r12r4_atomic_cgroup_birth_readiness.py --" not in source
    assert "v180r12r4_atomic_birth_readiness/LAUNCH_RECEIPT" not in source
    assert "probe_v180r12r4r1_atomic_cgroup_birth_readiness.py --" not in source
    assert "v180r12r4r1_atomic_birth_readiness/LAUNCH_RECEIPT" not in source
    assert "claimed_inode_unlinked" not in source
