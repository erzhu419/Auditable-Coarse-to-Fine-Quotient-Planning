from __future__ import annotations

import fcntl
import inspect
import os
from pathlib import Path
import signal
import socket

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v8 as domains_v8
from acfqp import construction_k7_h1_domain_registry_extension_v9 as domains_v9
from acfqp import construction_k7_h1_domain_registry_extension_v10 as domains_v10
from acfqp import construction_k7_h1_exclusive_native_resource_broker_v1 as broker_v1
from acfqp.phase3e_ids import canonical_json_bytes


def _sources() -> dict[str, bytes]:
    return {
        site: canonical_json_bytes(
            {
                "schema": "acfqp.test.k7_h1_e3_source.v1",
                "site_key": site,
                "index": index,
            }
        )
        for index, site in enumerate(broker_v1.SOURCE_SITE_ORDER)
    }


def _not_prebound_output_context() -> dict[str, str]:
    return {
        "kind": "NOT_APPLICABLE",
        "reason": "OUTPUT_CONTINUATION_NOT_PREBOUND",
    }


def test_v10_domains_are_additive_disjoint_and_canonical() -> None:
    assert not (
        domains_v10.K7_H1_DOMAIN_TAG_EXTENSION_V10
        & domains_v8.K7_H1_DOMAIN_TAG_EXTENSION_V8
    )
    assert not (
        domains_v10.K7_H1_DOMAIN_TAG_EXTENSION_V10
        & domains_v9.K7_H1_DOMAIN_TAG_EXTENSION_V9
    )
    assert len(domains_v10.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V10) == 12
    payload = {"schema": "acfqp.test.k7_h1_v10_domain.v1", "value": 1}
    domain = domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_PROFILE_V1_DOMAIN
    assert domains_v10.extension_content_id_v10(domain, payload) == (
        domains_v10.extension_content_id_v10(domain, payload)
    )
    with pytest.raises(ValueError, match="absent"):
        domains_v10.extension_content_id_v10(
            domains_v8.CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_SPEC_V1_DOMAIN,
            payload,
        )


def test_profile_freezes_new_authority_and_all_downstream_false_flags() -> None:
    document = broker_v1.official_h1_exclusive_broker_profile_v1().to_document()
    assert document["authority_disposition"] == "BROKER_EXCLUSIVE_PRESENT"
    assert document["accepted_upstream_dispositions"] == []
    assert document["v8_present_live_upgradable"] is False
    assert document["target_created_by_source_copy"] is True
    assert document["clone3_pidfd_into_distinct_cgroups_required"] is True
    assert document["pidfd_capability_probe_child_launches_per_reached_admission"] == 1
    assert document["subreaper_opposite_value_restore_probe_required"] is True
    assert document["cgroup_classification_precedes_runtime_admission"] is True
    assert document["execution_cleanup_window_milliseconds"] == 5_000
    assert document["prelaunch_failure_typed_crash_closure_forbidden"] is True
    assert document["optional_output_continuation_prebinding_present"] is True
    assert document["output_continuation_prebinding_authorizes_output"] is False
    assert document["output_ordinals_53_to_62_authorized"] is False
    assert document["formal_counter_records_issued"] is False
    assert document["formal_work_vector_issued"] is False
    assert document["formal_comparison_vector_issued"] is False
    assert document["official_execution_allowed"] is False
    assert broker_v1.V8_PRESENT_LIVE_UPGRADABLE is False
    assert "guardian" not in inspect.signature(
        broker_v1.run_h1_exclusive_native_resource_broker_v1
    ).parameters


def test_exact_ten_slots_map_v6_open_order_to_reverse_cleanup() -> None:
    assert len(broker_v1.PAYLOAD_SLOTS) == 10
    assert broker_v1.SOURCE_SITE_ORDER == tuple(
        row[2] for row in sorted(broker_v1.PAYLOAD_SLOTS, key=lambda row: row[1])
    )
    assert [row[0] for row in sorted(broker_v1.PAYLOAD_SLOTS)] == list(range(43, 53))
    assert broker_v1.ROLE_PAYLOAD_SITES["WORKER"] == (
        "mount-open:WORKER:sealed_runtime_archive",
        "mount-open:WORKER:ipc_binding_candidate",
        "mount-open:WORKER:execution_topology_profile",
    )
    assert len(broker_v1.ROLE_PAYLOAD_SITES["BUSINESS"]) == 7


def test_real_source_copy_creates_new_inode_new_target_ofd_and_closes_rw() -> None:
    raw = b"source remains a distinct provisioning OFD"
    source_fd = broker_v1._create_sealed_memfd(raw, "acfqp-e3-test-source")  # noqa: SLF001
    target = None
    try:
        source_stat = os.fstat(source_fd)
        target = broker_v1._create_exclusive_target_from_source_fd(  # noqa: SLF001
            source_fd,
            expected_sha256=broker_v1._sha(raw),  # noqa: SLF001
            expected_size=len(raw),
            name="acfqp-e3-test-target",
        )
        assert (target["source_device"], target["source_inode"]) == (
            source_stat.st_dev,
            source_stat.st_ino,
        )
        assert (target["target_device"], target["target_inode"]) != (
            source_stat.st_dev,
            source_stat.st_ino,
        )
        assert target["creator_rw_ofd_closed"] is True
        assert target["seals"] & broker_v1.REQUIRED_MEMFD_SEALS == (
            broker_v1.REQUIRED_MEMFD_SEALS
        )
        assert broker_v1._kcmp_file(  # noqa: SLF001
            target["master_fd"], target["anchor_fd"]
        )
        assert not broker_v1._kcmp_file(source_fd, target["master_fd"])  # noqa: SLF001
        assert broker_v1._same_ofd_inventory(target["master_fd"]) == tuple(  # noqa: SLF001
            sorted((target["master_fd"], target["anchor_fd"]))
        )
        assert os.pread(source_fd, len(raw), 0) == raw
    finally:
        os.close(source_fd)
        if target is not None:
            for key in ("master_fd", "anchor_fd"):
                try:
                    os.close(target[key])
                except OSError:
                    pass


def test_unledgered_same_ofd_alias_is_detected_before_close() -> None:
    raw = b"alias attack"
    source_fd = broker_v1._create_sealed_memfd(raw, "acfqp-e3-alias-source")  # noqa: SLF001
    target = broker_v1._create_exclusive_target_from_source_fd(  # noqa: SLF001
        source_fd,
        expected_sha256=broker_v1._sha(raw),  # noqa: SLF001
        expected_size=len(raw),
        name="acfqp-e3-alias-target",
    )
    attacker_fd = fcntl.fcntl(
        target["master_fd"], broker_v1._F_DUPFD_CLOEXEC, 3  # noqa: SLF001
    )
    try:
        assert broker_v1._same_ofd_inventory(target["master_fd"]) == tuple(  # noqa: SLF001
            sorted((target["master_fd"], target["anchor_fd"], attacker_fd))
        )
        assert broker_v1._same_ofd_inventory(target["master_fd"]) != tuple(  # noqa: SLF001
            sorted((target["master_fd"], target["anchor_fd"]))
        )
    finally:
        for descriptor in (
            attacker_fd,
            target["master_fd"],
            target["anchor_fd"],
            source_fd,
        ):
            os.close(descriptor)


def test_unexpected_scm_right_is_closed_before_packet_rejection() -> None:
    receiver, sender = socket.socketpair(
        socket.AF_UNIX,
        socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC,
    )
    receiver.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    raw_fd = broker_v1._create_sealed_memfd(b"right", "acfqp-e3-right")  # noqa: SLF001
    before = broker_v1._open_fd_numbers()  # noqa: SLF001
    try:
        broker_v1._send_packet(sender, {"kind": "ATTACK"}, (raw_fd,))  # noqa: SLF001
        with pytest.raises(RuntimeError, match="credentials, rights or extent"):
            broker_v1._recv_packet(  # noqa: SLF001
                receiver,
                deadline=broker_v1.time.monotonic() + 2,
                expected_pid=os.getpid(),
                expected_rights=0,
            )
        assert broker_v1._open_fd_numbers() == before  # noqa: SLF001
    finally:
        os.close(raw_fd)
        receiver.close()
        sender.close()


def test_missing_real_cgroup_authority_cannot_launch_or_mint_barrier() -> None:
    result = broker_v1.run_h1_exclusive_native_resource_broker_v1(
        source_payloads=_sources()
    )
    assert type(result) is broker_v1.H1ExclusiveBrokerUnavailableV1
    document = result.to_document()
    assert document["reason"] == "CGROUP_AUTHORITY_REQUIRED"
    assert document["broker_launched"] is False
    assert document["broker_exclusive_present"] is False
    assert document["normal_ordinal_41_to_52_success_events_issued"] is False
    assert document["native_cleanup_barrier_issued"] is False
    assert document["output_ordinals_53_to_62_authorized"] is False
    assert document["formal_counter_records_issued"] is False
    assert document["official_execution_allowed"] is False


def test_ordinary_directories_cannot_substitute_for_cgroup_kernel_fixture(
    tmp_path: Path,
) -> None:
    worker = tmp_path / "worker"
    business = tmp_path / "business"
    worker.mkdir()
    business.mkdir()
    worker_fd = os.open(worker, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    business_fd = os.open(business, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        result = broker_v1.run_h1_exclusive_native_resource_broker_v1(
            source_payloads=_sources(),
            worker_cgroup_fd=worker_fd,
            business_cgroup_fd=business_fd,
        )
    finally:
        os.close(worker_fd)
        os.close(business_fd)
    assert type(result) is broker_v1.H1ExclusiveBrokerUnavailableV1
    assert result.reason is broker_v1.H1ExclusiveBrokerUnavailableReasonV1.CGROUP_AUTHORITY_INVALID
    assert result.to_document()["broker_exclusive_present"] is False


def test_cgroup_missing_and_invalid_reasons_precede_all_runtime_probes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_probe(*_args: object, **_kwargs: object) -> bool:
        raise AssertionError("runtime probe ran before cgroup classification")

    for name in (
        "_thread_count",
        "_probe_memfd_sealing",
        "_probe_kcmp",
        "_probe_clone3",
        "_probe_pidfd_wait",
        "_probe_subreaper",
    ):
        monkeypatch.setattr(broker_v1, name, forbidden_probe)
    missing = broker_v1.run_h1_exclusive_native_resource_broker_v1(
        source_payloads=_sources()
    )
    assert missing.reason is (
        broker_v1.H1ExclusiveBrokerUnavailableReasonV1.CGROUP_AUTHORITY_REQUIRED
    )

    worker = tmp_path / "worker-invalid"
    business = tmp_path / "business-invalid"
    worker.mkdir()
    business.mkdir()
    worker_fd = os.open(worker, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    business_fd = os.open(business, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        invalid = broker_v1.run_h1_exclusive_native_resource_broker_v1(
            source_payloads=_sources(),
            worker_cgroup_fd=worker_fd,
            business_cgroup_fd=business_fd,
        )
    finally:
        os.close(worker_fd)
        os.close(business_fd)
    assert invalid.reason is (
        broker_v1.H1ExclusiveBrokerUnavailableReasonV1.CGROUP_AUTHORITY_INVALID
    )


@pytest.mark.parametrize(
    ("failed_probe", "expected_reason"),
    (
        (
            "_probe_pidfd_wait",
            broker_v1.H1ExclusiveBrokerUnavailableReasonV1.PIDFD_WAIT_UNAVAILABLE,
        ),
        (
            "_probe_subreaper",
            broker_v1.H1ExclusiveBrokerUnavailableReasonV1.SUBREAPER_UNAVAILABLE,
        ),
    ),
)
def test_real_capability_probe_failure_is_unavailable_before_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_probe: str,
    expected_reason: broker_v1.H1ExclusiveBrokerUnavailableReasonV1,
) -> None:
    worker = tmp_path / f"worker-{failed_probe}"
    business = tmp_path / f"business-{failed_probe}"
    worker.mkdir()
    business.mkdir()
    worker_fd = os.open(worker, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    business_fd = os.open(business, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    monkeypatch.setattr(broker_v1, "_require_empty_role_cgroup", lambda _fd: None)
    monkeypatch.setattr(broker_v1, "_thread_count", lambda: 1)
    monkeypatch.setattr(broker_v1.signal, "getsignal", lambda _signal: signal.SIG_DFL)
    monkeypatch.setattr(broker_v1, "_probe_memfd_sealing", lambda: True)
    monkeypatch.setattr(broker_v1, "_probe_kcmp", lambda: True)
    monkeypatch.setattr(broker_v1, "_probe_clone3", lambda: True)
    monkeypatch.setattr(broker_v1, "_probe_pidfd_wait", lambda: True)
    monkeypatch.setattr(broker_v1, "_probe_subreaper", lambda: True)
    monkeypatch.setattr(broker_v1, failed_probe, lambda: False)

    def forbidden_launch(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("broker launched after a failed capability probe")

    monkeypatch.setattr(broker_v1.subprocess, "Popen", forbidden_launch)
    try:
        result = broker_v1.run_h1_exclusive_native_resource_broker_v1(
            source_payloads=_sources(),
            worker_cgroup_fd=worker_fd,
            business_cgroup_fd=business_fd,
        )
    finally:
        os.close(worker_fd)
        os.close(business_fd)
    assert type(result) is broker_v1.H1ExclusiveBrokerUnavailableV1
    assert result.reason is expected_reason
    assert result.to_document()["broker_launched"] is False


def test_prelaunch_popen_failure_is_not_a_postlaunch_crash_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = tmp_path / "worker-prelaunch"
    business = tmp_path / "business-prelaunch"
    worker.mkdir()
    business.mkdir()
    worker_fd = os.open(worker, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    business_fd = os.open(business, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    before_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    before_subreaper = broker_v1._get_subreaper()  # noqa: SLF001
    monkeypatch.setattr(broker_v1, "_probe_prerequisites", lambda _w, _b: ({}, None))

    def fail_launch(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected Popen failure")

    monkeypatch.setattr(broker_v1.subprocess, "Popen", fail_launch)
    try:
        with pytest.raises(
            broker_v1.ConstructionK7H1ExclusiveNativeResourceBrokerV1Error,
            match="before process launch",
        ):
            broker_v1.run_h1_exclusive_native_resource_broker_v1(
                source_payloads=_sources(),
                worker_cgroup_fd=worker_fd,
                business_cgroup_fd=business_fd,
            )
    finally:
        os.close(worker_fd)
        os.close(business_fd)
    assert signal.pthread_sigmask(signal.SIG_BLOCK, set()) == before_mask
    assert broker_v1._get_subreaper() == before_subreaper  # noqa: SLF001


def test_source_order_and_caller_minted_results_fail_closed() -> None:
    reversed_sources = dict(reversed(tuple(_sources().items())))
    with pytest.raises(
        broker_v1.ConstructionK7H1ExclusiveNativeResourceBrokerV1Error,
        match="exact V6 site order",
    ):
        broker_v1.run_h1_exclusive_native_resource_broker_v1(
            source_payloads=reversed_sources
        )
    with pytest.raises(
        broker_v1.ConstructionK7H1ExclusiveNativeResourceBrokerV1Error,
        match="caller-minted",
    ):
        broker_v1.H1ExclusiveBrokerCompletionV1(
            object(), canonical_json_bytes({"schema": "forged"})
        )


@pytest.mark.parametrize(
    "invalid_value",
    (
        "a" * 63,
        "A" * 64,
        "g" * 64,
        "",
        7,
        _not_prebound_output_context(),
    ),
)
def test_invalid_public_output_continuation_prebinding_fails_closed(
    invalid_value: object,
) -> None:
    with pytest.raises(
        broker_v1.ConstructionK7H1ExclusiveNativeResourceBrokerV1Error,
        match="lowercase 64-hex or None",
    ):
        broker_v1.run_h1_exclusive_native_resource_broker_v1(
            source_payloads=_sources(),
            prebound_output_continuation_context_id=invalid_value,  # type: ignore[arg-type]
        )


def test_prebound_context_echo_rejects_wrong_or_crossed_identity() -> None:
    expected = "ab" * 32
    broker_v1._verify_prebound_output_continuation_echo(  # noqa: SLF001
        expected, expected
    )
    with pytest.raises(RuntimeError, match="echo crossed launch input"):
        broker_v1._verify_prebound_output_continuation_echo(  # noqa: SLF001
            "cd" * 32, expected
        )
    with pytest.raises(RuntimeError, match="echo crossed launch input"):
        broker_v1._verify_prebound_output_continuation_echo(  # noqa: SLF001
            _not_prebound_output_context(), expected
        )


def test_absent_prebinding_normalizes_to_one_durable_typed_null() -> None:
    first = broker_v1._normalize_prebound_output_continuation_context_id(None)  # noqa: SLF001
    second = broker_v1._normalize_prebound_output_continuation_context_id(None)  # noqa: SLF001
    assert first == _not_prebound_output_context()
    assert second == _not_prebound_output_context()
    assert first is not second


def test_source_manifest_binds_the_current_full_fresh_exec_source() -> None:
    document = broker_v1.official_h1_exclusive_broker_source_manifest_v1().to_document()
    raw = Path(broker_v1.__file__).read_bytes()
    assert document["source_sha256"] == broker_v1._sha(raw)  # noqa: SLF001
    assert document["source_byte_count"] == len(raw)
    assert document["source_staged_as_sealed_memfd"] is True
    assert document["interpreter_path_display"] == "/proc/self/exe"
    assert document["interpreter_manifest_read_from_one_fd"] is True
    assert document["fresh_exec_flags"] == ["-I", "-S", "-B"]


def test_running_image_hash_and_role_execveat_share_one_pinned_fd() -> None:
    manifest = broker_v1.official_h1_exclusive_broker_source_manifest_v1().to_document()
    descriptor, identity = broker_v1._open_verified_current_executable(  # noqa: SLF001
        manifest["interpreter_sha256"]
    )
    try:
        metadata = os.fstat(descriptor)
        assert identity == {
            "proc_path": "/proc/self/exe",
            "fd": descriptor,
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "byte_count": metadata.st_size,
            "sha256": manifest["interpreter_sha256"],
            "hash_and_execveat_use_same_fd": True,
        }
        raw = broker_v1._read_all_fd(  # noqa: SLF001
            descriptor, broker_v1.MAX_INTERPRETER_BYTES
        )
        assert broker_v1._sha(raw) == manifest["interpreter_sha256"]  # noqa: SLF001
    finally:
        os.close(descriptor)


def test_raw_syscall_fallback_table_and_real_memfd_seal_probe_are_complete() -> None:
    required = {
        "clone3",
        "execveat",
        "kcmp",
        "memfd_create",
        "pidfd_open",
        "pidfd_send_signal",
    }
    assert all(required <= set(row) for row in broker_v1._SYSCALLS.values())  # noqa: SLF001
    assert broker_v1._probe_memfd_sealing() is True  # noqa: SLF001


def test_crash_cleanup_cannot_be_complete_before_broker_pidfd_reap() -> None:
    complete_roles = {role: True for role in broker_v1.ROLE_ORDER}
    assert broker_v1._crash_cleanup_is_complete(  # noqa: SLF001
        broker_launched=True,
        broker_pidfd_reap_confirmed=False,
        role_cleanup=complete_roles,
        cgroup_empty=complete_roles,
    ) is False
    assert broker_v1._crash_cleanup_is_complete(  # noqa: SLF001
        broker_launched=True,
        broker_pidfd_reap_confirmed=True,
        role_cleanup=complete_roles,
        cgroup_empty=complete_roles,
    ) is True
    assert broker_v1._crash_cleanup_is_complete(  # noqa: SLF001
        broker_launched=True,
        broker_pidfd_reap_confirmed=True,
        role_cleanup={"WORKER": True, "BUSINESS": False},
        cgroup_empty=complete_roles,
    ) is False
    assert broker_v1._crash_cleanup_is_complete(  # noqa: SLF001
        broker_launched=True,
        broker_pidfd_reap_confirmed=True,
        role_cleanup=complete_roles,
        cgroup_empty={"WORKER": False, "BUSINESS": True},
    ) is False


def test_supervisor_control_restoration_helpers_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_mask(_how: int, _mask: object) -> object:
        raise OSError("injected signal-mask restoration failure")

    monkeypatch.setattr(broker_v1.signal, "pthread_sigmask", fail_mask)
    with pytest.raises(OSError, match="signal-mask restoration failure"):
        broker_v1._restore_signal_mask(set())  # noqa: SLF001


def test_subreaper_restoration_helper_does_not_swallow_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_subreaper(_enabled: int) -> int:
        raise OSError("injected subreaper restoration failure")

    monkeypatch.setattr(broker_v1, "_set_subreaper", fail_subreaper)
    with pytest.raises(OSError, match="subreaper restoration failure"):
        broker_v1._restore_subreaper(0)  # noqa: SLF001


@pytest.mark.skipif(not broker_v1.sys.platform.startswith("linux"), reason="Linux prctl required")
def test_real_subreaper_probe_preserves_the_exact_prior_state() -> None:
    before = broker_v1._get_subreaper()  # noqa: SLF001
    assert broker_v1._probe_subreaper() is True  # noqa: SLF001
    assert broker_v1._get_subreaper() == before  # noqa: SLF001


def test_subreaper_probe_restoration_failure_is_fatal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_values = iter((0, 1))
    set_calls: list[int] = []

    def fake_get() -> int:
        return next(observed_values)

    def fake_set(value: int) -> int:
        set_calls.append(value)
        if len(set_calls) == 2:
            raise OSError("injected probe restoration failure")
        return 0

    monkeypatch.setattr(broker_v1, "_get_subreaper", fake_get)
    monkeypatch.setattr(broker_v1, "_set_subreaper", fake_set)
    with pytest.raises(RuntimeError, match="could not restore prior state"):
        broker_v1._probe_subreaper()  # noqa: SLF001
    assert set_calls == [1, 0]


@pytest.mark.skipif(not broker_v1.sys.platform.startswith("linux"), reason="Linux pidfd required")
def test_real_pidfd_wait_probe_runs_fresh_and_leaves_no_child() -> None:
    source = """
import os
from acfqp import construction_k7_h1_exclusive_native_resource_broker_v1 as broker
assert broker._thread_count() == 1
assert broker._probe_pidfd_wait() is True
try:
    os.waitpid(-1, os.WNOHANG)
except ChildProcessError:
    raise SystemExit(0)
raise SystemExit(3)
"""
    completed = broker_v1.subprocess.run(
        [broker_v1.sys.executable, "-c", source],
        stdin=broker_v1.subprocess.DEVNULL,
        stdout=broker_v1.subprocess.PIPE,
        stderr=broker_v1.subprocess.PIPE,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")


@pytest.mark.skipif(
    not (
        os.environ.get("ACFQP_E3_WORKER_CGROUP")
        and os.environ.get("ACFQP_E3_BUSINESS_CGROUP")
    ),
    reason="two preconfigured delegated cgroup-v2 leaves were not registered",
)
def test_real_fresh_exec_clone3_pidfd_exclusive_cleanup_vertical_slice() -> None:
    worker_path = os.environ["ACFQP_E3_WORKER_CGROUP"]
    business_path = os.environ["ACFQP_E3_BUSINESS_CGROUP"]
    worker_fd = os.open(worker_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    business_fd = os.open(business_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    before_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    before_subreaper = broker_v1._get_subreaper()  # noqa: SLF001
    try:
        probe = broker_v1.probe_h1_exclusive_native_resource_broker_v1(
            worker_cgroup_fd=worker_fd,
            business_cgroup_fd=business_fd,
        )
        if not probe["admitted"]:
            pytest.skip(f"real E3 kernel fixture unavailable: {probe['blocker']}")
        result = broker_v1.run_h1_exclusive_native_resource_broker_v1(
            source_payloads=_sources(),
            worker_cgroup_fd=worker_fd,
            business_cgroup_fd=business_fd,
            deadline_milliseconds=30_000,
        )
    finally:
        os.close(worker_fd)
        os.close(business_fd)
    assert signal.pthread_sigmask(signal.SIG_BLOCK, set()) == before_mask
    assert broker_v1._get_subreaper() == before_subreaper  # noqa: SLF001
    assert type(result) is broker_v1.H1ExclusiveBrokerCompletionV1
    document = result.to_document()
    typed_null = _not_prebound_output_context()
    assert document["prebound_output_continuation_context_id"] == typed_null
    assert document["broker_session_genesis"][
        "prebound_output_continuation_context_id"
    ] == typed_null
    assert document["native_cleanup_barrier"][
        "prebound_output_continuation_context_id"
    ] == typed_null
    assert document["h1_exclusive_broker_profile_id"] == (
        broker_v1.official_h1_exclusive_broker_profile_v1().profile_id
    )
    assert document["h1_exclusive_broker_source_manifest_id"] == (
        broker_v1.official_h1_exclusive_broker_source_manifest_v1().manifest_id
    )
    assert document["broker_session_genesis"]["interpreter_execution_identity"][
        "hash_and_execveat_use_same_fd"
    ] is True
    assert all(
        row["postexec_dumpable_zero"] is True
        and row["postexec_no_new_privs"] is True
        for row in document["child_credentials"]
    )
    assert document["authority_disposition"] == "BROKER_EXCLUSIVE_PRESENT"
    assert document["v8_present_live_used"] is False
    assert document["source_ofd_adopted"] is False
    assert document["normal_ordinal_41_to_52_success_events_issued"] is True
    assert document["native_cleanup_barrier"]["completed_normal_ordinals"] == list(
        range(41, 53)
    )
    assert [
        row["normal_ordinal"]
        for row in document["last_legal_reference_closures"]
    ] == list(range(43, 53))
    assert all(
        row["last_legal_reference_closed"] is True
        for row in document["last_legal_reference_closures"]
    )
    assert document["output_ordinals_53_to_62_authorized"] is False
    assert document["formal_counter_records_issued"] is False
    assert document["official_execution_allowed"] is False
    forged = dict(document)
    forged["prebound_output_continuation_context_id"] = "ab" * 32
    with pytest.raises(
        broker_v1.ConstructionK7H1ExclusiveNativeResourceBrokerV1Error,
        match="completion content ID changed",
    ):
        broker_v1.H1ExclusiveBrokerCompletionV1(
            broker_v1._RESULT_ISSUER,  # noqa: SLF001
            canonical_json_bytes(forged),
        )
    crossed = dict(forged)
    crossed_payload = dict(crossed)
    crossed_payload.pop("h1_exclusive_broker_completion_id")
    crossed["h1_exclusive_broker_completion_id"] = broker_v1._domain_id(  # noqa: SLF001
        domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_COMPLETION_V1_DOMAIN,
        crossed_payload,
    )
    with pytest.raises(
        broker_v1.ConstructionK7H1ExclusiveNativeResourceBrokerV1Error,
        match="completion topology changed",
    ):
        broker_v1.H1ExclusiveBrokerCompletionV1(
            broker_v1._RESULT_ISSUER,  # noqa: SLF001
            canonical_json_bytes(crossed),
        )


@pytest.mark.skipif(
    not (
        os.environ.get("ACFQP_E3_WORKER_CGROUP")
        and os.environ.get("ACFQP_E3_BUSINESS_CGROUP")
    ),
    reason="two preconfigured delegated cgroup-v2 leaves were not registered",
)
def test_bound_output_continuation_context_propagates_without_authorizing_output() -> None:
    context_id = "ab" * 32
    worker_fd = os.open(
        os.environ["ACFQP_E3_WORKER_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    business_fd = os.open(
        os.environ["ACFQP_E3_BUSINESS_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        result = broker_v1.run_h1_exclusive_native_resource_broker_v1(
            source_payloads=_sources(),
            worker_cgroup_fd=worker_fd,
            business_cgroup_fd=business_fd,
            prebound_output_continuation_context_id=context_id,
            deadline_milliseconds=30_000,
        )
    finally:
        os.close(worker_fd)
        os.close(business_fd)
    assert type(result) is broker_v1.H1ExclusiveBrokerCompletionV1
    document = result.to_document()
    assert document["prebound_output_continuation_context_id"] == context_id
    assert document["broker_session_genesis"][
        "prebound_output_continuation_context_id"
    ] == context_id
    assert document["native_cleanup_barrier"][
        "prebound_output_continuation_context_id"
    ] == context_id
    assert document["output_ordinals_53_to_62_authorized"] is False
    assert document["native_cleanup_barrier"][
        "output_ordinals_53_to_62_authorized"
    ] is False
    assert document["production_output_leaf_authority_present"] is False
    assert document["formal_counter_records_issued"] is False
    assert document["official_execution_allowed"] is False


@pytest.mark.skipif(
    not (
        os.environ.get("ACFQP_E3_WORKER_CGROUP")
        and os.environ.get("ACFQP_E3_BUSINESS_CGROUP")
    ),
    reason="two preconfigured delegated cgroup-v2 leaves were not registered",
)
def test_persistent_supervisor_restoration_failure_is_untyped_fatal_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker_fd = os.open(
        os.environ["ACFQP_E3_WORKER_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    business_fd = os.open(
        os.environ["ACFQP_E3_BUSINESS_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    before_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())

    def fail_restore(_expected: set[signal.Signals]) -> None:
        raise OSError("injected persistent restoration failure")

    monkeypatch.setattr(broker_v1, "_restore_signal_mask", fail_restore)
    try:
        with pytest.raises(
            RuntimeError,
            match="could not restore supervisor controls",
        ):
            broker_v1.run_h1_exclusive_native_resource_broker_v1(
                source_payloads=_sources(),
                worker_cgroup_fd=worker_fd,
                business_cgroup_fd=business_fd,
                deadline_milliseconds=30_000,
            )
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, before_mask)
        os.close(worker_fd)
        os.close(business_fd)


@pytest.mark.skipif(
    not (
        os.environ.get("ACFQP_E3_WORKER_CGROUP")
        and os.environ.get("ACFQP_E3_BUSINESS_CGROUP")
    ),
    reason="two preconfigured delegated cgroup-v2 leaves were not registered",
)
def test_transient_supervisor_restoration_failure_converts_success_to_noncertificate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker_fd = os.open(
        os.environ["ACFQP_E3_WORKER_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    business_fd = os.open(
        os.environ["ACFQP_E3_BUSINESS_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    original = broker_v1._restore_signal_mask  # noqa: SLF001
    calls = 0

    def fail_once(expected: set[signal.Signals]) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected transient restoration failure")
        original(expected)

    monkeypatch.setattr(broker_v1, "_restore_signal_mask", fail_once)
    try:
        result = broker_v1.run_h1_exclusive_native_resource_broker_v1(
            source_payloads=_sources(),
            worker_cgroup_fd=worker_fd,
            business_cgroup_fd=business_fd,
            deadline_milliseconds=30_000,
        )
    finally:
        os.close(worker_fd)
        os.close(business_fd)
    assert calls == 2
    assert type(result) is broker_v1.H1ExclusiveBrokerCrashClosureV1
    document = result.to_document()
    assert document["broker_exit_status"] == 0
    assert document["broker_pidfd_reap_confirmed"] is True
    assert document["crash_cleanup_complete"] is True
    assert document["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert document["broker_exclusive_present"] is False
    assert document["native_cleanup_barrier_issued"] is False


@pytest.mark.skipif(
    not (
        os.environ.get("ACFQP_E3_WORKER_CGROUP")
        and os.environ.get("ACFQP_E3_BUSINESS_CGROUP")
    ),
    reason="two preconfigured delegated cgroup-v2 leaves were not registered",
)
def test_expired_execution_deadline_gets_a_distinct_bounded_cleanup_window() -> None:
    worker_fd = os.open(
        os.environ["ACFQP_E3_WORKER_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    business_fd = os.open(
        os.environ["ACFQP_E3_BUSINESS_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        result = broker_v1.run_h1_exclusive_native_resource_broker_v1(
            source_payloads=_sources(),
            worker_cgroup_fd=worker_fd,
            business_cgroup_fd=business_fd,
            deadline_milliseconds=1,
        )
    finally:
        os.close(worker_fd)
        os.close(business_fd)
    assert type(result) is broker_v1.H1ExclusiveBrokerCrashClosureV1
    document = result.to_document()
    assert document["execution_deadline_expired"] is True
    assert document["cleanup_window_milliseconds"] == (
        broker_v1.CLEANUP_TIMEOUT_MILLISECONDS
    )
    assert document["cleanup_window_independent_of_execution_deadline"] is True
    assert document["broker_pidfd_reap_confirmed"] is True
    assert document["role_cleanup_complete"] == {"WORKER": True, "BUSINESS": True}
    assert document["role_cgroups_empty"] == {"WORKER": True, "BUSINESS": True}
    assert document["crash_cleanup_complete"] is True
    assert document["broker_exclusive_present"] is False
    assert document["native_cleanup_barrier_issued"] is False


@pytest.mark.skipif(
    not (
        os.environ.get("ACFQP_E3_WORKER_CGROUP")
        and os.environ.get("ACFQP_E3_BUSINESS_CGROUP")
    ),
    reason="two preconfigured delegated cgroup-v2 leaves were not registered",
)
@pytest.mark.parametrize(
    "crash_point",
    (
        broker_v1.H1ExclusiveBrokerCrashPointV1.AFTER_TARGET_CREATION,
        broker_v1.H1ExclusiveBrokerCrashPointV1.AFTER_WORKER_ESCROW,
        broker_v1.H1ExclusiveBrokerCrashPointV1.AFTER_ROLE_REAPS,
        broker_v1.H1ExclusiveBrokerCrashPointV1.DURING_CLOSE_47,
    ),
)
def test_real_broker_crash_is_cleanup_complete_but_never_a_barrier(
    crash_point: broker_v1.H1ExclusiveBrokerCrashPointV1,
) -> None:
    prebound_context_id = (
        "cd" * 32
        if crash_point
        is broker_v1.H1ExclusiveBrokerCrashPointV1.AFTER_TARGET_CREATION
        else None
    )
    worker_fd = os.open(
        os.environ["ACFQP_E3_WORKER_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    business_fd = os.open(
        os.environ["ACFQP_E3_BUSINESS_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        result = broker_v1.run_h1_exclusive_native_resource_broker_v1(
            source_payloads=_sources(),
            worker_cgroup_fd=worker_fd,
            business_cgroup_fd=business_fd,
            prebound_output_continuation_context_id=prebound_context_id,
            deadline_milliseconds=30_000,
            crash_point=crash_point,
        )
    finally:
        os.close(worker_fd)
        os.close(business_fd)
    assert type(result) is broker_v1.H1ExclusiveBrokerCrashClosureV1
    document = result.to_document()
    assert document["prebound_output_continuation_context_id"] == (
        prebound_context_id
        if prebound_context_id is not None
        else _not_prebound_output_context()
    )
    assert document["broker_exit_status"] == 97, document
    assert document["broker_pidfd_reap_confirmed"] is True
    assert document["crash_cleanup_complete"] is True
    assert document["supervisor_signal_mask_restored"] is True
    assert document["supervisor_subreaper_restored"] is True
    assert document["role_cgroups_empty"] == {"WORKER": True, "BUSINESS": True}
    assert document["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert document["broker_exclusive_present"] is False
    assert document["normal_ordinal_41_to_52_success_events_issued"] is False
    assert document["native_cleanup_barrier_issued"] is False
    assert document["output_ordinals_53_to_62_authorized"] is False
    assert document["official_execution_allowed"] is False
