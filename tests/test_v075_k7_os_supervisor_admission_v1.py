from __future__ import annotations

from dataclasses import fields
import os

import pytest

from acfqp import v075_k7_os_supervisor_admission_v1 as admission
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def test_admission_domains_are_central_and_profile_is_locked() -> None:
    assert admission.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
    profile = admission.official_v075_k7_os_supervisor_admission_profile_v1()
    document = profile.to_document()
    assert document["runtime_lease_validation_implemented"] is False
    assert document["formal_locks"]["official_execution_allowed"] is False
    assert document["pids_max_required"] == 1
    assert document["cgroup_max_descendants_required"] == 0


def test_current_host_probe_fails_closed_before_launch() -> None:
    result = admission.probe_v075_k7_os_supervisor_admission_v1()
    document = result.to_document()
    assert result.status is admission.K7OSSupervisorAdmissionStatusV1.NOT_AVAILABLE
    assert (
        admission.K7OSSupervisorBlockerV1.DELEGATED_CGROUP_PARENT_FD_NOT_SUPPLIED.value
        in document["blockers"]
    )
    assert document["admission_scope"] == "PRELAUNCH_CAPABILITY_ONLY"
    assert document["attempt_terminal_issued"] is False
    assert document["noncertificate_closure_issued"] is False
    assert document["child_launch_attempted"] is False
    assert document["nine_shared_resource_paths_semantically_closed"] is False
    assert set(document["formal_locks"].values()) == {False}
    assert canonical_json_bytes(document)
    assert admission.verify_v075_k7_os_supervisor_admission_v1(result) is result


def test_directory_fd_is_only_preflight_and_never_execution_authority(
    tmp_path,
) -> None:
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        result = admission.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=descriptor
        )
    finally:
        os.close(descriptor)
    document = result.to_document()
    assert result.status is admission.K7OSSupervisorAdmissionStatusV1.NOT_AVAILABLE
    assert (
        admission.K7OSSupervisorBlockerV1.DELEGATED_PARENT_RUNTIME_LEASE_VALIDATION_NOT_IMPLEMENTED.value
        in document["blockers"]
    )
    assert document["child_launch_attempted"] is False
    assert set(document["formal_locks"].values()) == {False}
    assert document["admission_probe_id"] == result.probe.probe_id


@pytest.mark.parametrize("value", [True, False, -1, "3", 1.0])
def test_delegated_parent_fd_rejects_bool_and_other_invalid_values(value) -> None:
    with pytest.raises(admission.V075K7OSSupervisorAdmissionV1Error):
        admission.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=value
        )


def test_invalid_open_descriptor_is_not_treated_as_directory() -> None:
    descriptor = os.open("/dev/null", os.O_RDONLY)
    try:
        result = admission.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=descriptor
        )
    finally:
        os.close(descriptor)
    assert result.status is admission.K7OSSupervisorAdmissionStatusV1.NOT_AVAILABLE
    assert (
        admission.K7OSSupervisorBlockerV1.DELEGATED_CGROUP_PARENT_FD_INVALID
        in result.probe.blockers
    )


def test_issued_objects_reject_caller_minting() -> None:
    result = admission.probe_v075_k7_os_supervisor_admission_v1()
    read = result.probe.read_evidence[0]
    read_values = [getattr(read, item.name) for item in fields(read) if item.init]
    with pytest.raises(admission.V075K7OSSupervisorAdmissionV1Error):
        admission.K7OSSupervisorReadEvidenceV1(object(), *read_values)
    with pytest.raises(admission.V075K7OSSupervisorAdmissionV1Error):
        admission.K7OSSupervisorAdmissionResultV1(
            object(), result.profile, result.probe, result.status
        )


def test_mutated_nested_read_fails_probe_and_result_freshness() -> None:
    result = admission.probe_v075_k7_os_supervisor_admission_v1()
    read = result.probe.read_evidence[0]
    object.__setattr__(read, "sha256", "0" * 64)
    with pytest.raises(admission.V075K7OSSupervisorAdmissionV1Error):
        _ = result.result_id


def test_profile_or_probe_replacement_is_rejected() -> None:
    first = admission.probe_v075_k7_os_supervisor_admission_v1()
    second = admission.probe_v075_k7_os_supervisor_admission_v1()
    object.__setattr__(first, "probe", second.probe)
    with pytest.raises(admission.V075K7OSSupervisorAdmissionV1Error):
        _ = first.to_document()


def test_unknown_blocker_cannot_enter_an_issued_probe() -> None:
    result = admission.probe_v075_k7_os_supervisor_admission_v1()
    probe = result.probe
    values = [getattr(probe, item.name) for item in fields(probe) if item.init]
    values[-1] = ("UNKNOWN_BLOCKER",)
    with pytest.raises(admission.V075K7OSSupervisorAdmissionV1Error):
        admission.K7OSSupervisorAdmissionProbeV1(
            admission._PROBE_ISSUER,  # noqa: SLF001
            *values,
        )


def test_read_artifacts_retain_only_digest_and_byte_count() -> None:
    result = admission.probe_v075_k7_os_supervisor_admission_v1()
    for row in result.probe.to_document()["read_evidence"]:
        assert "content_hex" not in row
        assert "content" not in row
        assert row["source_bytes_retained"] is False
        assert type(row["byte_count"]) is int
        assert len(row["sha256"]) == 64


def test_mount_root_mapping_selects_longest_covering_mount() -> None:
    mountinfo = (
        "1 0 0:1 / /root rw - tmpfs tmpfs rw\n"
        "2 1 0:2 /slice /cg-a rw - cgroup2 cgroup2 rw\n"
        "3 1 0:3 /slice/deeper /cg-b rw - cgroup2 cgroup2 rw\n"
    )
    root, mountpoint = admission._cgroup2_mount(  # noqa: SLF001
        mountinfo, "/slice/deeper/attempt"
    )
    assert (root, mountpoint) == ("/slice/deeper", "/cg-b")
    assert admission._current_cgroup_directory(  # noqa: SLF001
        membership="/slice/deeper/attempt",
        mount_root=root,
        mountpoint=mountpoint,
    ) == admission.Path("/cg-b/attempt")


def test_probe_never_opens_for_write_or_mutates_or_launches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_open = admission.os.open

    def guarded_open(path, flags, *args, **kwargs):
        forbidden = admission.os.O_WRONLY | admission.os.O_RDWR | admission.os.O_CREAT
        assert flags & forbidden == 0
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(admission.os, "open", guarded_open)
    for name in ("fork", "posix_spawn"):
        if hasattr(admission.os, name):
            monkeypatch.setattr(
                admission.os,
                name,
                lambda *_args, _name=name, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(f"probe called {_name}")
                ),
            )
    result = admission.probe_v075_k7_os_supervisor_admission_v1()
    assert result.status is admission.K7OSSupervisorAdmissionStatusV1.NOT_AVAILABLE


def test_bounded_reader_rejects_source_over_cap(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "oversized"
    source.write_bytes(b"1234")
    monkeypatch.setattr(admission, "MAX_SOURCE_BYTES", 3)
    with pytest.raises(admission.V075K7OSSupervisorAdmissionV1Error):
        admission._read_bounded(  # noqa: SLF001
            source,
            admission.K7OSSupervisorReadRoleV1.PROC_SELF_CGROUP,
        )


def test_descriptor_facts_prevent_directory_transplant(tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    descriptors = [
        os.open(first, os.O_RDONLY | os.O_DIRECTORY),
        os.open(second, os.O_RDONLY | os.O_DIRECTORY),
    ]
    try:
        results = [
            admission.probe_v075_k7_os_supervisor_admission_v1(
                delegated_parent_fd=value
            )
            for value in descriptors
        ]
    finally:
        for value in descriptors:
            os.close(value)
    assert results[0].result_id != results[1].result_id


def test_unknown_blocker_mutation_fails_with_typed_error() -> None:
    result = admission.probe_v075_k7_os_supervisor_admission_v1()
    object.__setattr__(result.probe, "blockers", ("UNKNOWN_BLOCKER",))
    with pytest.raises(admission.V075K7OSSupervisorAdmissionV1Error):
        result.to_document()
