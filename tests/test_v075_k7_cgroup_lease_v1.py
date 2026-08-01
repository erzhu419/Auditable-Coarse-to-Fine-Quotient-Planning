from __future__ import annotations

import hashlib
import inspect
import os
import pickle
import stat

import pytest

from acfqp import campaign_v1 as campaign
from acfqp import routing_v1 as routing
from acfqp import v075_k7_cgroup_lease_v1 as lease
from acfqp import v075_k7_os_supervisor_admission_v1 as admission
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as accounted
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-cgroup-lease-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


@pytest.fixture(scope="module")
def substrate():
    old_profile = accounted.freeze_v075_k7_root_cap_accounted_sealed_ipc_profile_v1(
        timeout_milliseconds=5_000
    )
    profile = successor.freeze_v075_k7_parent_owned_successor_ipc_profile_v1(
        accounted_profile=old_profile
    )
    registry = public_authority.V075TrustedSignerRegistryV1(
        public_authority.V075RSAPublicVerificationKeyV1(
            "CAMPAIGN_AUTHORITY", (1 << 2047) + 1
        ),
        public_authority.V075RSAPublicVerificationKeyV1(
            "OBSERVER_EVIDENCE", (1 << 2047) + 3
        ),
    )
    return old_profile, profile, registry


def _request(substrate, label: str):
    old_profile, profile, registry = substrate
    occurrence = campaign.LogicalOccurrenceV1(
        _id(f"workload-{label}"),
        _id(f"protocol-{label}"),
        1,
        _id(f"structural-{label}"),
        _id(f"query-{label}"),
        _id(f"selected-plan-{label}"),
        _id(f"threshold-{label}"),
        _id(f"build-epoch-{label}"),
        _id(f"rebuild-{label}"),
    )
    attempt = campaign.RouteAttemptV1.initial(occurrence)
    context = routing.RouteDecisionContextV1(
        _id(f"preregistration-{label}"),
        occurrence.protocol_id,
        old_profile.comparison_profile_id,
        old_profile.counter_registry_id,
        occurrence.structural_id,
        occurrence.query_id,
        occurrence.selected_plan_id,
        occurrence.threshold_profile_id,
        attempt.build_epoch_id,
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
    )
    decision = routing.DecisionPointV1(
        context.route_decision_context_id,
        1,
        _id(f"frontier-{label}"),
        _id(f"causal-{label}"),
        _id(f"common-prefix-{label}"),
    )
    transaction = routing.TransactionV1(
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
        decision.decision_point_id,
        1,
        decision.frontier_snapshot_id,
        _id(f"route-cap-{label}"),
    )
    route = accounted.freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1(
        profile=old_profile,
        logical_occurrence=occurrence,
        route_attempt=attempt,
        route_context=context,
        decision_point=decision,
        transaction=transaction,
    )
    return successor.freeze_v075_k7_parent_owned_successor_request_v1(
        profile=profile,
        route_identity=route,
        signer_registry=registry,
        opaque_environment_commitment_id=_id(f"opaque-{label}"),
        sealed_secret_commitment_id=_id(f"secret-{label}"),
        session_external_id=_id(f"session-{label}"),
        request_nonce=_id(f"nonce-{label}"),
        scientific_occurrence_id=_id(f"science-{label}"),
        schedule_id=_id(f"schedule-{label}"),
    )


def _token(request, result, descriptor):
    return lease.official_v075_k7_cgroup_lease_nonce_service_v1().issue(
        request=request,
        admission_result=result,
        delegated_parent_fd=descriptor,
    )


def test_domains_profile_and_public_acquire_require_parent_nonce() -> None:
    assert lease.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
    document = lease.official_v075_k7_cgroup_lease_profile_v1().to_document()
    assert document["authority_source"] == (
        "CALLER_PREOPENED_DIRECTORY_DESCRIPTOR_ONLY"
    )
    assert document["parent_owned_nonce_consumed_before_cgroup_access"] is True
    assert document["durable_cross_process_replay_verified"] is False
    assert set(lease._formal_locks().values()) == {False}  # noqa: SLF001
    assert "nonce_token" in inspect.signature(
        lease.acquire_v075_k7_cgroup_attempt_lease_v1
    ).parameters


def test_temp_directory_fails_before_mutation_with_typed_blocker(
    substrate, tmp_path
) -> None:
    request = _request(substrate, "tmp-not-cgroup2")
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        result = admission.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=descriptor
        )
        token = _token(request, result, descriptor)
        before = tuple(tmp_path.iterdir())
        blocked = lease.acquire_v075_k7_cgroup_attempt_lease_v1(
            request=request,
            admission_result=result,
            delegated_parent_fd=descriptor,
            nonce_token=token,
        )
        after = tuple(tmp_path.iterdir())
    finally:
        os.close(descriptor)
    assert type(blocked) is lease.K7CgroupLeasePrelaunchBlockedResultV1
    assert blocked.blocker is lease.K7CgroupLeaseBlockerV1.NOT_CGROUP2_FILESYSTEM
    assert before == after == ()
    document = blocked.to_document()
    assert document["leaf_was_created"] is False
    assert document["cleanup_complete"] is True
    assert document["child_launch_attempted"] is False
    assert document["attempt_terminal_issued"] is False
    assert document["counter_record_issued"] is False
    assert set(
        document[name] for name in lease._formal_locks()  # noqa: SLF001
    ) == {False}
    assert canonical_json_bytes(document)


def test_nonce_is_single_use_and_consumed_before_filesystem_probe(
    substrate, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(substrate, "single-use")
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        result = admission.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=descriptor
        )
        token = _token(request, result, descriptor)
        calls = 0

        def fake_magic(_descriptor):
            nonlocal calls
            calls += 1
            return -1

        monkeypatch.setattr(lease, "_fstatfs_magic", fake_magic)
        first = lease.acquire_v075_k7_cgroup_attempt_lease_v1(
            request=request,
            admission_result=result,
            delegated_parent_fd=descriptor,
            nonce_token=token,
        )
        assert type(first) is lease.K7CgroupLeasePrelaunchBlockedResultV1
        assert calls == 1
        with pytest.raises(
            lease.V075K7CgroupLeaseV1Error, match="already consumed"
        ):
            lease.acquire_v075_k7_cgroup_attempt_lease_v1(
                request=request,
                admission_result=result,
                delegated_parent_fd=descriptor,
                nonce_token=token,
            )
        assert calls == 1
    finally:
        os.close(descriptor)


def test_failure_after_unique_leaf_creation_removes_its_leaf(
    substrate, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(substrate, "cleanup-after-create")
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    original_read = lease._read_control  # noqa: SLF001
    try:
        result = admission.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=descriptor
        )
        token = _token(request, result, descriptor)

        def read_control(directory_fd, name):
            if name in {"cgroup.controllers", "cgroup.subtree_control"}:
                return b"memory pids\n"
            return original_read(directory_fd, name)

        monkeypatch.setattr(
            lease, "_fstatfs_magic", lambda _descriptor: lease.CGROUP2_SUPER_MAGIC
        )
        monkeypatch.setattr(lease, "_read_control", read_control)
        blocked = lease.acquire_v075_k7_cgroup_attempt_lease_v1(
            request=request,
            admission_result=result,
            delegated_parent_fd=descriptor,
            nonce_token=token,
        )
    finally:
        os.close(descriptor)
    assert blocked.blocker is lease.K7CgroupLeaseBlockerV1.REQUIRED_LEAF_FILE_MISSING
    assert blocked.leaf_was_created is True
    assert blocked.leaf_was_removed is True
    assert tuple(tmp_path.iterdir()) == ()


def test_descriptor_target_and_identity_transplant_are_rejected_at_preparation(
    substrate, tmp_path
) -> None:
    request = _request(substrate, "transplant")
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    first_fd = os.open(first, os.O_RDONLY | os.O_DIRECTORY)
    second_fd = os.open(second, os.O_RDONLY | os.O_DIRECTORY)
    try:
        result = admission.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=first_fd
        )
        os.dup2(second_fd, first_fd)
        with pytest.raises(
            lease.V075K7CgroupLeaseV1Error,
            match="does not match admission evidence",
        ):
            _token(request, result, first_fd)
    finally:
        os.close(first_fd)
        os.close(second_fd)
    assert tuple(first.iterdir()) == ()
    assert tuple(second.iterdir()) == ()


def test_token_and_service_are_process_local_unpickleable(substrate, tmp_path) -> None:
    request = _request(substrate, "unpickleable")
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        result = admission.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=descriptor
        )
        token = _token(request, result, descriptor)
        with pytest.raises(TypeError, match="unpickleable"):
            pickle.dumps(token)
        with pytest.raises(TypeError, match="unpickleable"):
            pickle.dumps(
                lease.official_v075_k7_cgroup_lease_nonce_service_v1()
            )
    finally:
        os.close(descriptor)


def test_directly_constructed_token_cannot_enter_production_acquire(
    substrate, tmp_path
) -> None:
    request = _request(substrate, "unregistered-token")
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        result = admission.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=descriptor
        )
        status = os.fstat(descriptor)
        target = os.readlink(f"/proc/self/fd/{descriptor}")
        forged = lease.K7CgroupLeaseNonceTokenV1(
            lease._NONCE_TOKEN_ISSUER,  # noqa: SLF001
            request,
            result,
            descriptor,
            (
                status.st_dev,
                status.st_ino,
                stat.S_IMODE(status.st_mode),
                status.st_uid,
                status.st_gid,
            ),
            hashlib.sha256(target.encode("utf-8")).hexdigest(),
        )
        with pytest.raises(lease.V075K7CgroupLeaseV1Error, match="not issued"):
            lease.acquire_v075_k7_cgroup_attempt_lease_v1(
                request=request,
                admission_result=result,
                delegated_parent_fd=descriptor,
                nonce_token=forged,
            )
    finally:
        os.close(descriptor)
    assert tuple(tmp_path.iterdir()) == ()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b"memory pids cpu\n", ("cpu", "memory", "pids")),
        (b"pids memory memory", ("memory", "pids")),
        (b"", ()),
    ],
)
def test_controller_parser_is_canonical(raw, expected) -> None:
    assert (
        lease._parse_controller_tokens(raw, "controllers")  # noqa: SLF001
        == expected
    )


def test_events_empty_and_readback_parsers_are_strict() -> None:
    assert lease._parse_cgroup_events(b"populated 0\nfrozen 0\n") == {  # noqa: SLF001
        "populated": 0,
        "frozen": 0,
    }
    assert lease._readback_matches(b"1\n", "1", "pids.max") is True  # noqa: SLF001
    assert lease._readback_matches(b"0\n", "1", "pids.max") is False  # noqa: SLF001
    with pytest.raises(lease.V075K7CgroupLeaseV1Error, match="duplicated"):
        lease._parse_cgroup_events(b"populated 0\npopulated 1\n")  # noqa: SLF001
    with pytest.raises(lease.V075K7CgroupLeaseV1Error, match="lacks populated"):
        lease._parse_cgroup_events(b"frozen 0\n")  # noqa: SLF001


@pytest.mark.parametrize(
    ("cgroup_type", "memory_peak", "expected"),
    [
        (b"domain\n", b"0\n", None),
        (
            b"threaded\n",
            b"0\n",
            lease.K7CgroupLeaseBlockerV1.LEAF_TYPE_NOT_DOMAIN,
        ),
        (
            b"domain\n",
            b"1\n",
            lease.K7CgroupLeaseBlockerV1.MEMORY_PEAK_NOT_ZERO,
        ),
    ],
)
def test_initial_leaf_requires_domain_type_and_exact_zero_peak(
    monkeypatch: pytest.MonkeyPatch, cgroup_type, memory_peak, expected
) -> None:
    rows = {
        "cgroup.procs": b"",
        "cgroup.threads": b"",
        "pids.current": b"0\n",
        "cgroup.events": b"populated 0\nfrozen 0\n",
        "cgroup.type": cgroup_type,
        "memory.peak": memory_peak,
    }
    monkeypatch.setattr(
        lease, "_read_control", lambda _descriptor, name: rows[name]
    )
    assert lease._validate_initial_leaf(101) is expected  # noqa: SLF001


@pytest.mark.parametrize("value", [True, False, -1, "3", 1.0])
def test_acquire_rejects_mistyped_descriptor_before_any_os_access(
    substrate, value
) -> None:
    request = _request(substrate, f"bad-fd-{value!r}")
    result = admission.probe_v075_k7_os_supervisor_admission_v1()
    with pytest.raises(lease.V075K7CgroupLeaseV1Error):
        lease.acquire_v075_k7_cgroup_attempt_lease_v1(
            request=request,
            admission_result=result,
            delegated_parent_fd=value,
            nonce_token=object(),
        )
