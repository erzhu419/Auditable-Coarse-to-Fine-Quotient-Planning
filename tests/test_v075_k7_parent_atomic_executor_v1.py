from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json
from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime
from acfqp import v075_k7_atomic_shared_resource_authority_v1 as shared_authority
from acfqp import v075_k7_child_business_bundle_v1 as business
from acfqp import v075_k7_parent_atomic_executor_v1 as parent
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor
from acfqp import v075_signer_owning_complete_observer_lifecycle_ipc_v1 as lifecycle
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _id, _successor_request
from tests.test_v075_production_private_signer_runtime_v1 import (
    REPOSITORY_ROOT,
    _key_document,
    _registry,
    _write_private_key,
)


def _sealed(raw: bytes, name: str) -> int:
    return runtime.create_v075_k7_sealed_memfd_from_bytes_v1(raw=raw, name=name)


def _prepare(tmp_path: Path):
    request = _successor_request("parent-static")
    private_root = tmp_path / ".acfqp-private"
    private_root.mkdir(mode=0o700)
    key_path = private_root / "observer-key.json"
    key_path.write_bytes(b"not-used-by-static-preparation")
    key_path.chmod(0o600)
    secret_fd = _sealed(b"sealed-static-secret", "acfqp-parent-static-secret")
    try:
        spec, bootstrap = parent._prepare_bootstrap(  # noqa: SLF001
            request=request,
            sealed_secret_fd=secret_fd,
            repository_root=REPOSITORY_ROOT.resolve(),
            signer_private_root=private_root.resolve(),
            signer_private_key_path=key_path.resolve(),
        )
    finally:
        os.close(secret_fd)
    return request, spec, bootstrap


def _runtime_result(
    raw: bytes,
    *,
    deadline_milliseconds: int = parent.FIXED_DEADLINE_MILLISECONDS,
    output_cap_bytes: int = parent.FIXED_CHILD_OUTPUT_CAP_BYTES,
    memory_max_bytes: int = parent.FIXED_MEMORY_MAX_BYTES,
) -> runtime.K7AtomicPidfdRunResultV1:
    counters = runtime.K7AtomicPidfdCountersV1(
        1,
        1,
        0,
        1,
        len(raw),
        len(raw),
        runtime.SUCCESS_PATH_CGROUP_CONTROL_READS,
    )
    evidence = runtime.K7AtomicSupervisorResourceEvidenceV1(
        runtime._SUPERVISOR_EVIDENCE_ISSUER,  # noqa: SLF001
        _id("parent-result-lease"),
        1234,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        1,
        4096,
        memory_max_bytes,
        True,
        True,
        True,
    )
    return runtime.K7AtomicPidfdRunResultV1(
        runtime._RESULT_ISSUER,  # noqa: SLF001
        lease_id=_id("parent-result-lease"),
        child_pid=1234,
        outcome=runtime.K7AtomicPidfdOutcomeV1.EXITED,
        exit_code=0,
        terminating_signal=None,
        setup_succeeded=True,
        setup_failure_stage=None,
        setup_errno=None,
        output=raw,
        output_truncated=False,
        output_eof_before_reap=True,
        deadline_milliseconds=deadline_milliseconds,
        output_cap_bytes=output_cap_bytes,
        memory_max_bytes=memory_max_bytes,
        memory_peak_bytes=4096,
        cgroup_empty_verified=True,
        no_descendants_verified=True,
        supervisor_resource_evidence=evidence,
        elapsed_nanoseconds=100,
        counters=counters,
    )


def test_execution_spec_binds_exact_bootstrap_inputs_and_private_locators(
    tmp_path: Path,
) -> None:
    request, spec, bootstrap = _prepare(tmp_path)
    try:
        document = spec.to_document()
        record = runtime.K7SealedBootstrapExecV1._record(bootstrap)  # noqa: SLF001
        assert [row["role"] for row in document["input_manifest"]] == list(
            parent.INPUT_ROLES
        )
        assert document["input_manifest"][-1]["content_digest_serialized"] is False
        assert "sha256" not in document["input_manifest"][-1]
        assert document["deadline_milliseconds"] == parent.FIXED_DEADLINE_MILLISECONDS
        assert document["memory_max_bytes"] == parent.FIXED_MEMORY_MAX_BYTES
        assert document["child_output_cap_bytes"] == parent.FIXED_CHILD_OUTPUT_CAP_BYTES
        assert document["python_hash_seed_fixed"] is False
        assert dict(record.environment) == {"LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
        assert record.argv[-3] == spec.spec_id
        assert record.argv[1:5] == ("-I", "-S", "-B", "-c")
        assert request.request_id == document["request_id"]

        with pytest.raises(parent.V075K7ParentAtomicExecutorV1Error):
            replace(
                spec,
                _issuer=parent._SPEC_ISSUER,  # noqa: SLF001
                input_manifest_rows=tuple(reversed(spec.input_manifest_rows)),
            )
    finally:
        bootstrap.close()


def test_two_frame_result_rejects_crossed_caps_bytes_and_framing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, spec, bootstrap = _prepare(tmp_path)
    bootstrap.close()
    child_raw = canonical_json_bytes({"schema": "acfqp.test_child_frame.v1"})
    child_document = {
        "atomic_child_business_frame_id": _id("child-frame"),
        "child_business_bundle_id": _id("child-bundle"),
    }
    monkeypatch.setattr(parent, "_portable_replay", lambda _request: object())
    monkeypatch.setattr(
        parent.child_v1,
        "verify_v075_k7_atomic_child_business_frame_bytes_v1",
        lambda **_kwargs: dict(child_document),
    )
    observed = _runtime_result(child_raw)
    suffix_raw, two_frame = parent._solve_two_frame_fixed_point(  # noqa: SLF001
        child_raw=child_raw,
        request=request,
        spec=spec,
        child_document=child_document,
        runtime_result=observed,
    )
    result = parent.V075K7ParentAtomicExecutionResultV1(
        parent._RESULT_ISSUER,  # noqa: SLF001
        request,
        spec,
        observed,
        child_raw,
        suffix_raw,
        two_frame,
    )
    assert result.child_frame_bytes == child_raw
    assert result.suffix_frame_bytes == suffix_raw

    with pytest.raises(parent.V075K7ParentAtomicExecutorV1Error):
        parent.verify_v075_k7_parent_atomic_two_frame_output_v1(
            raw=two_frame,
            request=request,
            spec=spec,
            runtime_result=_runtime_result(child_raw, deadline_milliseconds=1),
        )
    with pytest.raises(parent.V075K7ParentAtomicExecutorV1Error):
        parent.V075K7ParentAtomicExecutionResultV1(
            parent._RESULT_ISSUER,  # noqa: SLF001
            request,
            spec,
            observed,
            b"crossed",
            suffix_raw,
            two_frame,
        )
    for attacked in (two_frame[:-1], two_frame + b"trailing", parent._frame(suffix_raw) + parent._frame(child_raw)):  # noqa: SLF001
        with pytest.raises(parent.V075K7ParentAtomicExecutorV1Error):
            parent.verify_v075_k7_parent_atomic_two_frame_output_v1(
                raw=attacked,
                request=request,
                spec=spec,
                runtime_result=observed,
            )


def test_failure_retains_child_bytes_privately_and_domains_do_not_cross() -> None:
    raw = b"private-child-output"
    failure = parent.V075K7ParentAtomicFailureV1(
        parent._FAILURE_ISSUER,  # noqa: SLF001
        _id("failure-request"),
        _id("failure-spec"),
        "CHILD_EXECUTION",
        canonical_json_bytes({"schema": "acfqp.test_runtime_failure.v1"}),
        raw,
    )
    document = failure.to_document()
    assert raw not in canonical_json_bytes(document)
    assert document["raw_child_output_sha256"] == hashlib.sha256(raw).hexdigest()
    assert document["raw_child_output_byte_count"] == len(raw)
    payload = {"same": "payload"}
    assert content_id(
        parent.V075_K7_ATOMIC_PARENT_EXECUTION_RESULT_V1_DOMAIN, payload
    ) != content_id(parent.V075_K7_ATOMIC_PARENT_EXECUTION_FAILURE_V1_DOMAIN, payload)


def test_bootstrap_source_freezes_exact_process_boundary() -> None:
    source = parent._BOOTSTRAP_SOURCE  # noqa: SLF001
    for required in (
        "len(sys.argv) != 11",
        "sys.flags.isolated != 1",
        "sys.flags.no_site != 1",
        "sys.flags.ignore_environment != 1",
        "sys.flags.dont_write_bytecode != 1",
        "set(os.environ) !=",
        "os.close(executable_fds[0])",
        "atomic_parent_execution_spec_id=atomic_parent_execution_spec_id",
        "os._exit(code)",
    ):
        assert required in source


def test_fatal_lease_and_runtime_cleanup_errors_are_never_typed_away(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _successor_request("fatal-cleanup")
    paths = (tmp_path.resolve(), tmp_path.resolve(), tmp_path.resolve())
    admission_result = object()
    monkeypatch.setattr(
        parent.admission_v1,
        "probe_v075_k7_os_supervisor_admission_v1",
        lambda **_kwargs: admission_result,
    )

    class FatalNonceService:
        def issue(self, **_kwargs):
            raise parent.lease_v1.V075K7CgroupLeaseCleanupV1Error("fatal lease cleanup")

    monkeypatch.setattr(
        parent.lease_v1,
        "official_v075_k7_cgroup_lease_nonce_service_v1",
        lambda: FatalNonceService(),
    )
    with pytest.raises(parent.lease_v1.V075K7CgroupLeaseCleanupV1Error):
        parent.execute_v075_k7_parent_atomic_attempt_v1(
            request=request,
            delegated_parent_fd=0,
            sealed_lifecycle_secret_fd=0,
            repository_root=paths[0],
            signer_private_root=paths[1],
            signer_private_key_path=paths[2],
        )

    class FakeLease:
        closed = True

        def close(self) -> None:
            raise AssertionError("already closed fake lease must not be closed")

    class FakeBootstrap:
        closed = True

        def close(self) -> None:
            raise AssertionError("already closed fake bootstrap must not be closed")

    monkeypatch.setattr(parent.lease_v1, "K7CgroupAttemptLeaseV1", FakeLease)
    monkeypatch.setattr(
        parent.lease_v1,
        "official_v075_k7_cgroup_lease_nonce_service_v1",
        lambda: SimpleNamespace(issue=lambda **_kwargs: object()),
    )
    monkeypatch.setattr(
        parent.lease_v1,
        "acquire_v075_k7_cgroup_attempt_lease_v1",
        lambda **_kwargs: FakeLease(),
    )
    monkeypatch.setattr(
        parent,
        "_prepare_bootstrap",
        lambda **_kwargs: (SimpleNamespace(spec_id=_id("fake-spec")), FakeBootstrap()),
    )
    monkeypatch.setattr(
        parent.runtime_v1,
        "run_v075_k7_atomic_pidfd_runtime_v1",
        lambda **_kwargs: (_ for _ in ()).throw(
            parent.runtime_v1.V075K7AtomicPidfdCleanupV1Error("fatal runtime cleanup")
        ),
    )
    with pytest.raises(parent.runtime_v1.V075K7AtomicPidfdCleanupV1Error):
        parent.execute_v075_k7_parent_atomic_attempt_v1(
            request=request,
            delegated_parent_fd=0,
            sealed_lifecycle_secret_fd=0,
            repository_root=paths[0],
            signer_private_root=paths[1],
            signer_private_key_path=paths[2],
        )


def _production_request(marker: str, secret_raw: bytes):
    generated, _salt, commitment = lifecycle._load_secret(secret_raw)  # noqa: SLF001
    del generated
    registry = _registry()
    base = lifecycle._fixture_base(  # noqa: SLF001
        commitment=commitment,
        signer_registry=registry,
    )
    schedule, _verification = business._derive_exact_no_prior_schedule(  # noqa: SLF001
        repository_root=REPOSITORY_ROOT.resolve(),
        namespace=base.namespace,
    )
    structural = _successor_request(marker)
    secret_document = loads_canonical_json(secret_raw)
    return successor.freeze_v075_k7_parent_owned_successor_request_v1(
        profile=structural.profile,
        route_identity=structural.route_identity,
        signer_registry=registry,
        opaque_environment_commitment_id=commitment.commitment_id,
        sealed_secret_commitment_id=secret_document["secret_material_id"],
        session_external_id=_id(f"{marker}-session"),
        request_nonce=_id(f"{marker}-nonce"),
        scientific_occurrence_id=schedule.occurrence.occurrence_id,
        schedule_id=schedule.schedule_id,
    )


@contextmanager
def _delegated_scope_parent_fd():
    relative = next(
        row.removeprefix("0::").strip()
        for row in Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
        if row.startswith("0::")
    )
    parent_path = Path(
        os.environ.get(
            "ACFQP_K7_DELEGATED_PARENT",
            str(Path("/sys/fs/cgroup") / relative.lstrip("/")),
        )
    )
    supervisor_name = f"acfqp-parent-executor-{os.getpid()}"
    supervisor_path = parent_path / supervisor_name
    parent_fd = os.open(parent_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    moved = False
    enabled = False
    try:
        os.mkdir(supervisor_name, mode=0o700, dir_fd=parent_fd)
        (supervisor_path / "cgroup.procs").write_text(f"{os.getpid()}\n", encoding="ascii")
        moved = True
        (parent_path / "cgroup.subtree_control").write_text(
            "+memory +pids\n", encoding="ascii"
        )
        enabled = True
        yield parent_fd
    finally:
        if enabled:
            (parent_path / "cgroup.subtree_control").write_text(
                "-memory -pids\n", encoding="ascii"
            )
        if moved:
            (parent_path / "cgroup.procs").write_text(f"{os.getpid()}\n", encoding="ascii")
        try:
            os.rmdir(supervisor_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_CGROUP_INTEGRATION") != "1",
    reason="requires an externally prepared delegated systemd user scope",
)
def test_real_parent_executor_runs_one_business_and_publishes_two_frames(
    tmp_path: Path,
) -> None:
    if runtime._thread_count() != 1:  # noqa: SLF001
        pytest.skip("positive clone3 path requires an exact single-thread parent")
    seed = hashlib.sha512(b"atomic-parent-real-generation").digest()
    salt = hashlib.sha512(b"atomic-parent-real-salt").digest()
    secret_raw = lifecycle._secret_raw_for_testing(  # noqa: SLF001
        generation_seed=seed,
        private_salt=salt,
    )
    request = _production_request("parent-real", secret_raw)
    private_root, key_path = _write_private_key(
        tmp_path,
        _key_document(_registry()),
    )
    secret_fd = lifecycle._stage_secret_for_testing(secret_raw)  # noqa: SLF001
    try:
        with _delegated_scope_parent_fd() as parent_fd:
            result = parent.execute_v075_k7_parent_atomic_attempt_v1(
                request=request,
                delegated_parent_fd=parent_fd,
                sealed_lifecycle_secret_fd=secret_fd,
                repository_root=REPOSITORY_ROOT.resolve(),
                signer_private_root=private_root,
                signer_private_key_path=key_path,
            )
    finally:
        os.close(secret_fd)
    if type(result) is not parent.V075K7ParentAtomicExecutionResultV1:
        pytest.fail(
            repr(
                (
                    result.to_document()["underlying_result"],
                    result.raw_child_output,
                )
            )
        )
    resource_verification = (
        shared_authority.verify_v075_k7_atomic_shared_resource_evidence_v1(
            request=request,
            parent_result=result,
        )
    )
    child, suffix = result.child_frame, result.suffix_frame
    assert child["atomic_parent_execution_spec_id"] == result.spec.spec_id
    assert suffix["wrapper_complete_two_frame_output_bytes"] == len(
        result.two_frame_output
    )
    assert resource_verification.child_runtime_resolution.value == (
        result.runtime_result.memory_peak_bytes
    )
    assert resource_verification.to_document()["exact_connected_paths"] == []
    assert resource_verification.to_document()[
        "child_runtime_window_scope_incomplete_paths"
    ] == [
        "memory.working_bytes_peak"
    ]
    assert result.runtime_result.output_eof_before_reap is True
    assert all(value is False for value in parent._locks().values())  # noqa: SLF001
