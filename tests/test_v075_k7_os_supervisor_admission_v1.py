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
    assert document["prelaunch_terminal"] is True
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
    assert result.status is admission.K7OSSupervisorAdmissionStatusV1.PREFLIGHT_ONLY
    assert (
        admission.K7OSSupervisorBlockerV1.DELEGATED_PARENT_RUNTIME_LEASE_VALIDATION_NOT_IMPLEMENTED.value
        in document["blockers"]
    )
    assert document["child_launch_attempted"] is False
    assert set(document["formal_locks"].values()) == {False}


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
        admission.K7OSSupervisorAdmissionProbeV1(object(), *values)
