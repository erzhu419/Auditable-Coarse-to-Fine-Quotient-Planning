from __future__ import annotations

import copy
import base64
import errno
import hashlib
import importlib.util
import os
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/probe_v180r12r4r1_atomic_cgroup_birth_readiness.py"
SPEC = importlib.util.spec_from_file_location(
    "v180r12r4r1_atomic_birth_probe", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


def _properties(**updates: str) -> dict[str, str]:
    values = {
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "exited",
        "ControlGroup": "/expected/target",
        "BindsTo": probe.SERVICE_UNIT_NAME,
        "After": f"basic.target {probe.SERVICE_UNIT_NAME}",
        "KillMode": "control-group",
        "Type": probe.TARGET_SERVICE_TYPE,
        "RemainAfterExit": "yes",
        "Delegate": "yes",
        "CollectMode": "inactive-or-failed",
        "Slice": probe.SERVICE_SLICE,
        "TimeoutStopUSec": f"{probe.TARGET_UNIT_STOP_TIMEOUT_SECONDS}s",
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


def _create_result():
    argv = tuple(
        probe.build_target_lifecycle_contract(os.geteuid())["create_argv"]
    )
    return probe.BoundedProcessResult(argv, 0, b"", b"", False, False)


def _absence_properties() -> dict[str, str]:
    return {
        "LoadState": "not-found",
        "ActiveState": "inactive",
        "SubState": "dead",
        "ControlGroup": "",
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

    def run(self, argv, **_kwargs):
        retained = tuple(argv)
        self.calls.append(retained)
        contract = probe.build_target_lifecycle_contract(os.geteuid())
        if retained == tuple(contract["absence_show_argv"]):
            raw = (
                b"LoadState=not-found"
                if self.malformed_precreate
                else _absence_result().stdout
            )
        elif retained == tuple(contract["create_argv"]):
            raw = b""
        elif retained == tuple(contract["active_show_argv"]):
            raw = b"LoadState=loaded" if self.malformed_active else _raw(_properties())
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
        "precreate_manager_not_found": True,
        "precreate_target_path_absent": True,
        "manager_create_result": _create_result(),
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
    assert probe.PREFLIGHT_ORDINAL == 1
    assert probe.TARGET_ORDINAL == 1
    assert lineage["predecessor_inner_failure_id"] == (
        "78a406bdde5d79b2dee79011ed731b392da301c67cebcc27456855af394bc695"
    )
    assert lineage["predecessor_outer_launch_failure_id"] == (
        "4bf05b7989cb24d350436c3c433827ee0019af44637017cb0f3f0c83dd185ff5"
    )
    assert lineage["predecessor_frozen_source_commit_id"] == (
        "69afc2791151328dff952942f869e1010047ae28"
    )
    assert probe.PREFLIGHT_TOKEN not in probe.SERVICE_UNIT_NAME.replace(
        probe.PREFLIGHT_TOKEN, "", 1
    )
    assert "v180r12r4r1" in probe.SERVICE_UNIT_NAME
    assert "v180r12r4_atomic_birth_readiness" not in (
        probe.ARTIFACT_ROOT_RELATIVE_PATH
    )
    replay = dict(lineage)
    replay["ordinal"] = 0
    with pytest.raises(probe.AuthorityError):
        probe.derive_preflight_token(replay)


def test_predecessor_terminal_closure_is_exact_and_tamper_rejected() -> None:
    facts = probe.observe_predecessor_terminal_artifact_facts(ROOT)
    assert [row["byte_count"] for row in facts] == [2603, 1292, 9476, 6561]
    assert [row["sha256"] for row in facts] == [
        "581a66571360a7a58832b240dd86adbff9ed1f7df71d156c974a56d012a810e8",
        "0b844b1f2f6ea13fc8909ee6c7cf942d0348285c0a7d5daf11fb6a60be39fd32",
        "9b59d3d7dc7e804271782d9e1a37545c268e717050296052168693ea35e6b53c",
        "aa5b82f25b66979217a987ae8eef45501ae0ab6a49dac080d0e88206573077d4",
    ]
    assert probe.validate_predecessor_terminal_artifact_facts(facts) == facts
    tampered = copy.deepcopy(facts)
    tampered[2]["sha256"] = "0" * 64
    payload = dict(tampered[2])
    del payload["predecessor_artifact_fact_id"]
    tampered[2]["predecessor_artifact_fact_id"] = probe._domain_id(
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
    tampered["expected_properties"]["Delegate"] = "no"
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


def test_stable_static_mismatch_fails_promptly_with_mismatch_keys() -> None:
    bad = _raw(_properties(Delegate="no"))
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
    assert failure.trace.last_conformance["mismatch_keys"] == ["Delegate"]
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
        _properties(ActiveState="activating", SubState="start")
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
            _result(_raw(_properties(ActiveState="activating", SubState="start"))),
            _result(_raw(_properties(ActiveState="reloading", SubState="reload"))),
            _result(_raw(_properties(ActiveState="activating", SubState="start"))),
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
        return _result(_raw(_properties(ActiveState=state, SubState=substate)))

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
            assert diagnostic["precreate_manager_not_found"] is None
            assert diagnostic["precreate_target_path_absent"] is True
        else:
            assert diagnostic["precreate_manager_properties"] == (
                _absence_properties()
            )
            assert diagnostic["precreate_manager_not_found"] is True
            assert diagnostic["precreate_target_path_absent"] is None
    finally:
        os.close(valid_fd)


def test_post_create_parse_failure_owns_exact_unit_and_can_clean_it(
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
        detail = cleanup.remove_target(service, target, 10**30)
        assert detail["ownership_scope"] == "UNIT_ONLY"
        assert detail["manager_absence_proven"] is True
        assert target.stop_requested is True
        assert cleanup.stop_calls == 1
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
        return {
            "LoadState": "not-found",
            "ActiveState": "inactive",
            "SubState": "dead",
            "ControlGroup": "",
        }


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


def test_unit_only_owned_cleanup_stops_and_proves_manager_and_path_absence(
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
        detail = adapter.remove_target(service, target, 10**30)
        assert detail["ownership_scope"] == "UNIT_ONLY"
        assert detail["manager_absence_proven"] is True
        assert detail["target_path_absent"] is True
        assert detail["claimed_inode_unlinked"] is None
        assert target.manager_absence_proven is True
        assert target.residual_possible is False
        assert adapter.target_absent(service, target, 10**30)["target_absent"] is True
    finally:
        os.close(app_fd)


def test_unit_only_cleanup_stop_failure_is_fail_closed(tmp_path: Path) -> None:
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
        assert diagnostic["exception_phase"] == "STOP_SUBPROCESS"
        assert diagnostic["manager_absence_proven"] is False
        tampered = copy.deepcopy(diagnostic)
        tampered["manager_absence_proven"] = True
        payload = dict(tampered)
        del payload["target_cleanup_diagnostic_id"]
        tampered["target_cleanup_diagnostic_id"] = probe._domain_id(
            probe.TARGET_CLEANUP_DIAGNOSTIC_DOMAIN, payload
        )
        with pytest.raises(probe.AuthorityError):
            probe.validate_target_cleanup_diagnostic(tampered)
        assert target.stop_requested is True
        assert target.manager_absence_proven is False
        assert target.residual_possible is True
        with pytest.raises(OSError, match="residual is possible"):
            adapter.target_absent(service, target, 10**30)
    finally:
        os.close(app_fd)


def test_full_path_ofd_cleanup_additionally_proves_inode_unlink(
    tmp_path: Path,
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
        adapter = _CleanupAdapter(tmp_path)
        detail = adapter.remove_target(service, target, 10**30)
        assert detail["ownership_scope"] == "UNIT_PATH_OFD"
        assert detail["claimed_inode_unlinked"] is True
        assert target.claimed_inode_unlinked is True
        assert target.directory_fd == -1
    finally:
        if target_fd >= 0:
            try:
                os.close(target_fd)
            except OSError:
                pass
        os.close(app_fd)


def test_successor_source_has_no_r4_formal_invocation() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "probe_v180r12r4_atomic_cgroup_birth_readiness.py --" not in source
    assert "v180r12r4_atomic_birth_readiness/LAUNCH_RECEIPT" not in source
