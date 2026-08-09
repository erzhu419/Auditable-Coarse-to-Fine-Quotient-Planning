from __future__ import annotations

import errno
from contextvars import copy_context
import os
from pathlib import Path
import pickle
import queue
import shutil
import tempfile
import threading

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_domain_registry_extension_v1 as domains_v1
from acfqp import construction_k7_h1_domain_registry_extension_v2 as domains_v2
from acfqp import construction_k7_h1_domain_registry_extension_v3 as domains_v3
from acfqp import construction_k7_h1_domain_registry_extension_v4 as domains_v4
from acfqp import construction_k7_h1_domain_registry_extension_v5 as domains_v5
from acfqp import construction_k7_h1_domain_registry_extension_v6 as domains_v6
from acfqp import construction_k7_h1_domain_registry_extension_v7 as domains_v7
from acfqp import construction_k7_h1_domain_registry_extension_v8 as domains_v8
from acfqp import construction_k7_h1_failed_prefix_cleanup_budget_admission_v1 as admission_v1
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as output_join_v1
from acfqp import construction_k7_h1_native_capability_guardian_v1 as guardian_v1
from acfqp import construction_k7_h1_native_resource_receipt_journal_v1 as receipts_v1
from acfqp import construction_k7_h1_phase_aware_normal_prefix_v1 as normal_v1
from acfqp import construction_k7_h1_preadmitted_cleanup_transition_v2 as cleanup_v2
from acfqp.phase3e_ids import canonical_json_bytes

from test_construction_k7_h1_phase_aware_normal_prefix_v1 import _build_case


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANCHOR_ID = (
    "4a4b0d1888f0ac18123e4163e1a26b0583a64946d2eb219e02d4b77dc0a3e327"
)
EXACT_BUDGET = {
    "RESOLVE": 1,
    "REAP": 2,
    "MOUNT_CLOSE": 10,
    "MEMORY_RELEASE": 1,
    "OUTPUT_RELEASE": 1,
}


@pytest.fixture(scope="module")
def bundle():
    return dispatch_v1.freeze_h1_anchored_lifecycle_dispatch_bundle_v1(
        REPOSITORY_ROOT, expected_anchor_id=EXPECTED_ANCHOR_ID
    )


@pytest.fixture(scope="module")
def analysis(bundle):
    return cleanup_v1.derive_h1_lifecycle_complete_branch_analysis_v1(
        bundle, output_join_v1.build_h1_lifecycle_output_leaf_join_v1(bundle)
    )


@pytest.fixture
def fast_root():
    base = "/dev/shm" if Path("/dev/shm").is_dir() else "/tmp"
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-native-guardian-", dir=base))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _lease(case, bundle):
    return normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        case.normal,
        phase_handle=case.phase,
        rejection_gate=case.gate,
        owner=case.owner,
        bundle=bundle,
        dispatch_profile=case.dispatch_profile,
    )


def _prerequisites(root, case, bundle, analysis):
    with _lease(case, bundle) as lease:
        envelope = cleanup_v2.preadmit_h1_normal_prefix_cleanup_envelope_v2(
            lease, cleanup_analysis=analysis
        )
    spec = receipts_v1.freeze_h1_native_receipt_journal_spec_v1(
        root, normal_handle=case.normal
    )
    native = receipts_v1.initialize_h1_native_receipt_journal_v1(
        spec, normal_handle=case.normal
    )
    return envelope, spec, native


def _guardian(root, case, bundle, analysis):
    envelope, spec, native = _prerequisites(root, case, bundle, analysis)
    with _lease(case, bundle) as lease:
        admission = admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
            lease,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_spec=spec,
            native_receipt_handle=native,
            available_cleanup_budget=EXACT_BUDGET,
        )
    # E1 accepts a freshly reopened exact live pristine lease; it does not
    # depend on Python identity of the lease that created C-D.
    with _lease(case, bundle) as lease:
        guardian = guardian_v1.initialize_h1_native_capability_guardian_v1(
            lease,
            native_receipt_spec=spec,
            native_receipt_handle=native,
            cleanup_budget_admission=admission,
        )
    return spec, native, admission, guardian


def _normal_callback(row):
    if row["ordinal"] in {1, 5}:
        return None
    if row["operation"] in {
        "COMMON_HASH",
        "COMMON_INTEGRITY",
        "COMMON_PROTOCOL",
        "LAUNCH_CHILD",
    }:
        return lambda: None
    return lambda: 1


def _execute_normal(case, bundle, *, callback=None, crash_point=None):
    with _lease(case, bundle) as lease:
        kwargs = {"callback": callback}
        if crash_point is not None:
            kwargs["crash_point"] = crash_point
        return normal_v1.execute_next_h1_phase_aware_normal_site_v1(
            lease, **kwargs
        )


def _advance_to_dangling_intent(case, bundle, ordinal):
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    while snapshot.document["next_ordinal"] < ordinal:
        row = bundle.program.transitions[snapshot.document["next_ordinal"] - 1]
        event = _execute_normal(case, bundle, callback=_normal_callback(row))
        assert event.outcome == "SUCCESS"
        snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    row = bundle.program.transitions[ordinal - 1]
    with pytest.raises(normal_v1.H1NormalPrefixInjectedCrashV1):
        _execute_normal(
            case,
            bundle,
            callback=_normal_callback(row),
            crash_point=normal_v1.H1NormalPrefixCrashPointV1.AFTER_INTENT_FSYNC,
        )
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    return snapshot.document["dangling_intent_id"]


def _commit_dangling(case, bundle):
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    row = bundle.program.transitions[snapshot.document["next_ordinal"] - 1]
    return _execute_normal(case, bundle, callback=_normal_callback(row))


def _slot(spec, ordinal):
    return next(
        row for row in spec.payload["predeclared_slots"]
        if row["normal_ordinal"] == ordinal
    )


def _slot_snapshot(snapshot, slot_key):
    return next(row for row in snapshot["slot_states"] if row["slot_key"] == slot_key)


def _admission_paths(admission):
    payload = admission.payload
    base = Path(
        payload["prospective_owner_cleanup_sidecar_baseline"][
            "phase_base_realpath"
        ]
    )
    attempt_id = payload["route_attempt_id"]
    primary = (
        base
        / admission_v1._ROOT_NAME
        / attempt_id
        / admission_v1._ADMISSION_FILE
    )
    seal = base / f"{admission_v1._SEAL_PREFIX}{attempt_id}"
    return base, primary, seal


def _marker_paths(admission):
    base, _primary, _seal = _admission_paths(admission)
    attempt_id = admission.payload["route_attempt_id"]
    primary = (
        base
        / guardian_v1._MARKER_ROOT_NAME
        / attempt_id
        / guardian_v1._MARKER_FILE
    )
    seal = base / f"{guardian_v1._MARKER_SEAL_PREFIX}{attempt_id}"
    return primary, seal


def _walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def test_preordinal_guardian_binds_exact_v6_admission_and_is_not_serializable(
    fast_root, bundle, analysis, monkeypatch
):
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-init")
    spec, native, admission, guardian = _guardian(
        fast_root, case, bundle, analysis
    )
    try:
        payload = guardian.spec.payload
        assert payload["h1_native_receipt_journal_spec_id"] == spec.spec_id
        assert payload["h1_native_receipt_allocation_id"] == native.allocation_id
        assert payload["h1_failed_prefix_cleanup_budget_admission_id"] == admission.admission_id
        assert payload["initialized_before_normal_ordinal_1"] is True
        assert payload["exact_live_pristine_lease_revalidated"] is True
        assert payload["durable_c_d_primary_base_seal_replayed_read_only"] is True
        assert payload["same_c_d_creation_lease_required"] is False
        assert payload["linux_kcmp_file_identity_required"] is True
        assert payload["raw_descriptor_fields_serialized"] is False
        assert payload["generation_secret_serialized"] is False
        assert payload["native_cleanup_effect_authority_present"] is False
        assert payload["current_access_authority_present"] is False
        assert payload["formal_counter_records_issued"] is False
        assert payload["official_execution_allowed"] is False
        marker_primary, marker_seal = _marker_paths(admission)
        primary_metadata = marker_primary.stat()
        seal_metadata = marker_seal.stat()
        assert (
            primary_metadata.st_dev,
            primary_metadata.st_ino,
            primary_metadata.st_nlink,
            primary_metadata.st_mode & 0o777,
        ) == (
            seal_metadata.st_dev,
            seal_metadata.st_ino,
            2,
            0o400,
        )
        assert seal_metadata.st_nlink == 2
        assert seal_metadata.st_mode & 0o777 == 0o400
        assert "sealed" in repr(guardian)
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="not serializable",
        ):
            pickle.dumps(guardian)
        # The durable tombstone, not a mutable Python set, is authoritative.
        with guardian_v1._REGISTRY_LOCK:
            guardian_v1._LIVE_GUARDIANS.pop(guardian._registry_key, None)
            guardian_v1._GUARDED_ALLOCATIONS.discard(guardian._registry_key)
        with _lease(case, bundle) as repeated_lease:
            with pytest.raises(
                guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
                match="marker already burned",
            ):
                guardian_v1.initialize_h1_native_capability_guardian_v1(
                    repeated_lease,
                    native_receipt_spec=spec,
                    native_receipt_handle=native,
                    cleanup_budget_admission=admission,
                )
        actual_start = guardian._broker_process_start_ticks
        monkeypatch.setattr(
            guardian_v1, "_process_start_ticks", lambda process_id=None: actual_start + 1
        )
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="incarnation changed nonrecoverably",
        ):
            guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian)
        monkeypatch.undo()
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="poisoned and nonrecoverable",
        ):
            guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian)
    finally:
        guardian._dispose_for_test_only()


def test_real_memfd_is_adopted_closed_bound_and_reverified(
    fast_root, bundle, analysis, monkeypatch
):
    if not hasattr(os, "memfd_create") or not hasattr(os, "fork"):
        pytest.skip("Linux memfd/fork support is unavailable")
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-memfd")
    spec, _native, _admission, guardian = _guardian(
        fast_root, case, bundle, analysis
    )
    slot = _slot(spec, 7)
    intent = _advance_to_dangling_intent(case, bundle, 7)
    captured = []
    original = os.memfd_create("acfqp-guardian", os.MFD_CLOEXEC)
    original_fingerprint = os.fstat(original)
    reused_original = False
    midfork_reports = []
    real_kcmp = guardian_v1._kcmp_file
    real_v6_execute = receipts_v1.execute_h1_native_resource_callback_once_v1
    real_v6_bind = receipts_v1.bind_h1_native_callback_result_to_normal_event_v1
    real_v6_replay = receipts_v1.replay_h1_native_receipt_journal_v1
    fork_triggered = False

    def assert_capability_mutex_not_held(callable_):
        def checked(*args, **kwargs):
            assert not guardian_v1._REGISTRY_LOCK._is_owned()
            return callable_(*args, **kwargs)

        return checked

    def fork_during_adoption(left_fd, right_fd):
        nonlocal fork_triggered
        if not fork_triggered and guardian_v1._PENDING_FDS:
            fork_triggered = True
            pending_numbers = tuple(guardian_v1._PENDING_FDS)
            read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
            child = os.fork()
            if child == 0:  # pragma: no cover - asserted through parent pipe
                os.close(read_fd)
                closed = True
                for descriptor in pending_numbers:
                    try:
                        os.fstat(descriptor)
                    except OSError as error:
                        closed = closed and error.errno == errno.EBADF
                    else:
                        closed = False
                report = f"{guardian._poisoned}:{closed}:{not guardian_v1._PENDING_FDS}"
                os.write(write_fd, report.encode("ascii"))
                os._exit(0)
            os.close(write_fd)
            midfork_reports.append(os.read(read_fd, 128).decode("ascii"))
            os.close(read_fd)
            _, status = os.waitpid(child, 0)
            assert os.waitstatus_to_exitcode(status) == 0
        return real_kcmp(left_fd, right_fd)

    monkeypatch.setattr(guardian_v1, "_kcmp_file", fork_during_adoption)
    monkeypatch.setattr(
        receipts_v1,
        "execute_h1_native_resource_callback_once_v1",
        assert_capability_mutex_not_held(real_v6_execute),
    )
    monkeypatch.setattr(
        receipts_v1,
        "bind_h1_native_callback_result_to_normal_event_v1",
        assert_capability_mutex_not_held(real_v6_bind),
    )
    monkeypatch.setattr(
        receipts_v1,
        "replay_h1_native_receipt_journal_v1",
        assert_capability_mutex_not_held(real_v6_replay),
    )

    def acquire():
        # Public APIs fail before inspecting any argument while the callback is
        # active; only the two observe APIs are legal here.
        public_calls = (
            lambda: guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian),
            lambda: guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
                guardian,
                slot_key="invalid",
                h1_normal_site_intent_id="invalid",
                acquisition=lambda: None,
            ),
            lambda: guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
                guardian, pending_binding=None, normal_site_event=None
            ),
            lambda: guardian_v1.initialize_h1_native_capability_guardian_v1(
                None,
                native_receipt_spec=None,
                native_receipt_handle=None,
                cleanup_budget_admission=None,
            ),
        )
        for call in public_calls:
            with pytest.raises(
                guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
                match="cannot reenter",
            ):
                call()
        item = guardian_v1.observe_h1_guarded_native_present_v1(original)
        with pytest.raises(OSError) as closed_inside_callback:
            os.fstat(original)
        assert closed_inside_callback.value.errno == errno.EBADF
        replacement = os.memfd_create("acfqp-reused-original-number", os.MFD_CLOEXEC)
        if replacement != original:
            os.dup2(replacement, original, inheritable=False)
            os.close(replacement)
        assert os.fstat(original).st_ino != original_fingerprint.st_ino
        captured.append(item)
        return item

    try:
        pending = guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
            guardian,
            slot_key=slot["slot_key"],
            h1_normal_site_intent_id=intent,
            acquisition=acquire,
        )
        reused_original = True
        assert midfork_reports == ["True:True:True"]
        assert guardian._poisoned is False
        os.fstat(original)
        os.close(original)
        reused_original = False
        assert repr(captured[0]).endswith("sealed>")
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="not serializable",
        ):
            pickle.dumps(captured[0])
        event = _commit_dangling(case, bundle)
        binding = guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
            guardian, pending_binding=pending, normal_site_event=event
        )
        assert binding.status is guardian_v1.H1NativeCapabilityGuardianStatusV1.PRESENT_LIVE
        document = binding.document
        assert document["h1_native_capability_guardian_init_marker_id"] == guardian._marker_id
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="process-local and not serializable",
        ):
            pickle.dumps(binding)
        assert document["h1_native_callback_result_id"] == pending.result_id
        assert document["live_master_witness_same_ofd_verified"] is True
        assert (
            document["live_master_witness_registry_anchor_same_ofd_verified"]
            is True
        )
        assert document["fstat_fdinfo_provenance_verified"] is True
        assert document["descriptor_cloexec_verified"] is True
        assert document["raw_descriptor_fields_serialized"] is False
        assert document["generation_secret_serialized"] is False
        assert document["binding_document_is_durable_capability_authority"] is False
        forbidden = {
            "fd", "raw_fd", "descriptor", "master_fd", "witness_fd",
            "generation_secret",
        }
        assert forbidden.isdisjoint(_walk_keys(document))
        snapshot = guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian)
        assert snapshot["h1_native_capability_guardian_init_marker_id"] == guardian._marker_id
        row = _slot_snapshot(snapshot, slot["slot_key"])
        assert row["guardian_status"] == "PRESENT_LIVE"
        assert row["v6_resolution"] == "KNOWN_PRESENT"
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="process, thread, or use",
        ):
            guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
                guardian, pending_binding=pending, normal_site_event=event
            )
    finally:
        if reused_original:
            os.close(original)
        guardian._dispose_for_test_only()


def test_real_pidfd_is_typed_and_bound_when_supported(fast_root, bundle, analysis):
    if not hasattr(os, "pidfd_open"):
        pytest.skip("Linux pidfd_open is unavailable")
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-pidfd")
    spec, _native, _admission, guardian = _guardian(
        fast_root, case, bundle, analysis
    )
    slot = _slot(spec, 26)
    intent = _advance_to_dangling_intent(case, bundle, 26)
    original = os.pidfd_open(os.getpid(), 0)
    try:
        pending = guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
            guardian,
            slot_key=slot["slot_key"],
            h1_normal_site_intent_id=intent,
            acquisition=lambda: guardian_v1.observe_h1_guarded_native_present_v1(
                original
            ),
        )
        event = _commit_dangling(case, bundle)
        binding = guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
            guardian, pending_binding=pending, normal_site_event=event
        )
        assert binding.status.value == "PRESENT_LIVE"
        assert _slot_snapshot(
            guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian),
            slot["slot_key"],
        )["capability_kind"] == "PIDFD"
    finally:
        guardian._dispose_for_test_only()


def test_known_absence_is_bound_without_a_live_cell(fast_root, bundle, analysis):
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-absent")
    spec, _native, _admission, guardian = _guardian(
        fast_root, case, bundle, analysis
    )
    slot = _slot(spec, 7)
    intent = _advance_to_dangling_intent(case, bundle, 7)
    copied = []

    def acquire_absence():
        copied.append(copy_context())
        return guardian_v1.observe_h1_guarded_native_absent_v1(
            reason="OPEN_FAILED_BEFORE_DESCRIPTOR_CREATION"
        )

    try:
        pending = guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
            guardian,
            slot_key=slot["slot_key"],
            h1_normal_site_intent_id=intent,
            acquisition=acquire_absence,
        )
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="outside its live callback window",
        ):
            copied[0].run(
                guardian_v1.observe_h1_guarded_native_absent_v1,
                reason="DELAYED_CONTEXT_REPLAY",
            )
        event = _commit_dangling(case, bundle)
        binding = guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
            guardian, pending_binding=pending, normal_site_event=event
        )
        assert binding.status.value == "ABSENT"
        assert binding.document["live_master_witness_same_ofd_verified"] is False
        assert _slot_snapshot(
            guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian),
            slot["slot_key"],
        )["guardian_status"] == "ABSENT"
    finally:
        guardian._dispose_for_test_only()


def test_direct_v6_receipt_without_guardian_stays_unresolved(
    fast_root, bundle, analysis
):
    if not hasattr(os, "memfd_create"):
        pytest.skip("Linux memfd_create is unavailable")
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-bypass")
    spec, native, _admission, guardian = _guardian(
        fast_root, case, bundle, analysis
    )
    slot = _slot(spec, 7)
    intent = _advance_to_dangling_intent(case, bundle, 7)
    original = os.memfd_create("acfqp-direct-v6", os.MFD_CLOEXEC)
    try:
        pending = receipts_v1.execute_h1_native_resource_callback_once_v1(
            native,
            slot_key=slot["slot_key"],
            h1_normal_site_intent_id=intent,
            callback=lambda: receipts_v1.observe_h1_native_present_v1(
                original, capability_kind="OFD"
            ),
        )
        os.close(original)
        original = -1
        event = _commit_dangling(case, bundle)
        receipt = receipts_v1.bind_h1_native_callback_result_to_normal_event_v1(
            native, pending_result=pending, normal_site_event=event
        )
        assert type(receipt) is receipts_v1.H1NativeResourceReceiptV1
        row = _slot_snapshot(
            guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian),
            slot["slot_key"],
        )
        assert row["v6_resolution"] == "KNOWN_PRESENT"
        assert row["guardian_status"] == "UNRESOLVED"
        assert row["unresolved_reason"] == (
            "DIRECT_V6_PRESENT_RECEIPT_WITHOUT_GUARDIAN_BINDING"
        )
    finally:
        if original >= 0:
            os.close(original)
        guardian._dispose_for_test_only()


def test_duplicate_ofd_cross_slot_is_rejected_and_original_alias_closed(
    fast_root, bundle, analysis
):
    if not hasattr(os, "memfd_create"):
        pytest.skip("Linux memfd_create is unavailable")
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-duplicate")
    spec, native, _admission, guardian = _guardian(
        fast_root, case, bundle, analysis
    )
    first = _slot(spec, 7)
    second = _slot(spec, 9)
    intent = _advance_to_dangling_intent(case, bundle, 7)
    original = os.memfd_create("acfqp-duplicate-ofd", os.MFD_CLOEXEC)
    alias = os.dup(original)
    try:
        pending = guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
            guardian,
            slot_key=first["slot_key"],
            h1_normal_site_intent_id=intent,
            acquisition=lambda: guardian_v1.observe_h1_guarded_native_present_v1(
                original
            ),
        )
        event = _commit_dangling(case, bundle)
        binding = guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
            guardian, pending_binding=pending, normal_site_event=event
        )
        intent_9 = _advance_to_dangling_intent(case, bundle, 9)
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="cannot cross native slots",
        ):
            guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
                guardian,
                slot_key=second["slot_key"],
                h1_normal_site_intent_id=intent_9,
                acquisition=lambda: guardian_v1.observe_h1_guarded_native_present_v1(
                    alias
                ),
            )
        with pytest.raises(OSError) as closed:
            os.fstat(alias)
        assert closed.value.errno == errno.EBADF
        replay = receipts_v1.replay_h1_native_receipt_journal_v1(native)
        assert replay["slot_resolutions"][second["slot_key"]] == "UNRESOLVED"
    finally:
        guardian._dispose_for_test_only()


def test_pending_and_duplicate_ofd_cannot_cross_v6_allocations(
    fast_root, bundle, analysis
):
    if not hasattr(os, "memfd_create"):
        pytest.skip("Linux memfd_create is unavailable")
    first_root = fast_root / "allocation-a"
    second_root = fast_root / "allocation-b"
    first_root.mkdir()
    second_root.mkdir()
    first_case = _build_case(first_root, bundle, analysis, suffix="guardian-cross-a")
    second_case = _build_case(second_root, bundle, analysis, suffix="guardian-cross-b")
    first_spec, _first_native, _first_admission, first_guardian = _guardian(
        first_root, first_case, bundle, analysis
    )
    second_spec, _second_native, _second_admission, second_guardian = _guardian(
        second_root, second_case, bundle, analysis
    )
    first_slot = _slot(first_spec, 7)
    second_slot = _slot(second_spec, 7)
    original = os.memfd_create("acfqp-cross-allocation", os.MFD_CLOEXEC)
    alias = os.dup(original)
    try:
        first_intent = _advance_to_dangling_intent(first_case, bundle, 7)
        pending = guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
            first_guardian,
            slot_key=first_slot["slot_key"],
            h1_normal_site_intent_id=first_intent,
            acquisition=lambda: guardian_v1.observe_h1_guarded_native_present_v1(
                original
            ),
        )
        first_event = _commit_dangling(first_case, bundle)
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="crossed guardian",
        ):
            guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
                second_guardian,
                pending_binding=pending,
                normal_site_event=first_event,
            )
        guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
            first_guardian,
            pending_binding=pending,
            normal_site_event=first_event,
        )
        second_intent = _advance_to_dangling_intent(second_case, bundle, 7)
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="cannot cross native slots or V6 allocations",
        ):
            guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
                second_guardian,
                slot_key=second_slot["slot_key"],
                h1_normal_site_intent_id=second_intent,
                acquisition=lambda: guardian_v1.observe_h1_guarded_native_present_v1(
                    alias
                ),
            )
        with pytest.raises(OSError) as closed:
            os.fstat(alias)
        assert closed.value.errno == errno.EBADF
    finally:
        first_guardian._dispose_for_test_only()
        second_guardian._dispose_for_test_only()


def test_dup2_replacement_invalidates_live_binding(fast_root, bundle, analysis):
    if not hasattr(os, "memfd_create"):
        pytest.skip("Linux memfd_create is unavailable")
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-dup2")
    spec, _native, _admission, guardian = _guardian(
        fast_root, case, bundle, analysis
    )
    slot = _slot(spec, 7)
    intent = _advance_to_dangling_intent(case, bundle, 7)
    original = os.memfd_create("acfqp-before-dup2", os.MFD_CLOEXEC)
    try:
        pending = guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
            guardian,
            slot_key=slot["slot_key"],
            h1_normal_site_intent_id=intent,
            acquisition=lambda: guardian_v1.observe_h1_guarded_native_present_v1(
                original
            ),
        )
        event = _commit_dangling(case, bundle)
        binding = guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
            guardian, pending_binding=pending, normal_site_event=event
        )
        cell = guardian._slot_states[slot["slot_key"]].cell
        assert cell is not None
        anchor = guardian_v1._ANCHOR_FDS[
            (guardian._registry_key, slot["slot_key"])
        ]
        replacement = os.memfd_create("acfqp-after-dup2", os.MFD_CLOEXEC)
        try:
            os.dup2(replacement, cell._master_fd, inheritable=False)
            os.dup2(replacement, cell._witness_fd, inheritable=False)
            assert guardian_v1._kcmp_file(cell._master_fd, cell._witness_fd)
            assert not guardian_v1._kcmp_file(cell._master_fd, anchor)
        finally:
            os.close(replacement)
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="CLOEXEC|provenance|reused|replaced",
        ):
            guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian)
        assert guardian._slot_states[slot["slot_key"]].status.value == "UNRESOLVED"
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="descriptor|live",
        ):
            _ = binding.binding_id
        guardian._dispose_for_test_only()
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="poisoned",
        ):
            _ = binding.document
    finally:
        guardian._dispose_for_test_only()


def test_cross_thread_and_forked_child_fail_while_parent_remains_live(
    fast_root, bundle, analysis
):
    if not hasattr(os, "memfd_create") or not hasattr(os, "fork"):
        pytest.skip("Linux memfd/fork support is unavailable")
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-fork")
    spec, _native, _admission, guardian = _guardian(
        fast_root, case, bundle, analysis
    )
    slot = _slot(spec, 7)
    intent = _advance_to_dangling_intent(case, bundle, 7)
    original = os.memfd_create("acfqp-parent-live", os.MFD_CLOEXEC)
    try:
        pending = guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
            guardian,
            slot_key=slot["slot_key"],
            h1_normal_site_intent_id=intent,
            acquisition=lambda: guardian_v1.observe_h1_guarded_native_present_v1(
                original
            ),
        )
        event = _commit_dangling(case, bundle)
        binding = guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
            guardian, pending_binding=pending, normal_site_event=event
        )
        outcomes = queue.Queue()

        def foreign_thread():
            try:
                guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian)
            except BaseException as error:
                outcomes.put(type(error))
            try:
                _ = binding.binding_id
            except BaseException as error:
                outcomes.put(type(error))

        worker = threading.Thread(target=foreign_thread)
        worker.start()
        worker.join(timeout=10)
        assert outcomes.get_nowait() is guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error
        assert outcomes.get_nowait() is guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error

        cell = guardian._slot_states[slot["slot_key"]].cell
        assert cell is not None
        master_number = cell._master_fd
        read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        child = os.fork()
        if child == 0:  # pragma: no cover - asserted through parent pipe
            os.close(read_fd)
            try:
                poisoned = False
                closed = False
                try:
                    guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian)
                except guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error:
                    poisoned = True
                token_rejected = False
                try:
                    _ = binding.document
                except guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error:
                    token_rejected = True
                try:
                    os.fstat(master_number)
                except OSError as error:
                    closed = error.errno == errno.EBADF
                os.write(
                    write_fd,
                    f"{poisoned}:{closed}:{token_rejected}".encode("ascii"),
                )
            finally:
                os._exit(0)
        os.close(write_fd)
        child_report = os.read(read_fd, 128).decode("ascii")
        os.close(read_fd)
        _, status = os.waitpid(child, 0)
        assert os.waitstatus_to_exitcode(status) == 0
        assert child_report == "True:True:True"
        assert _slot_snapshot(
            guardian_v1.snapshot_h1_native_capability_guardian_v1(guardian),
            slot["slot_key"],
        )["guardian_status"] == "PRESENT_LIVE"
        assert binding.status.value == "PRESENT_LIVE"
    finally:
        guardian._dispose_for_test_only()


def test_kcmp_unavailable_and_late_initialization_fail_closed(
    fast_root, bundle, analysis, monkeypatch
):
    unavailable_root = fast_root / "unavailable"
    unavailable_root.mkdir()
    case = _build_case(unavailable_root, bundle, analysis, suffix="guardian-kcmp")
    envelope, spec, native = _prerequisites(
        unavailable_root, case, bundle, analysis
    )

    def unavailable(_left, _right):
        raise guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error(
            "Linux kcmp(KCMP_FILE) failed closed: EPERM"
        )

    with _lease(case, bundle) as lease:
        admission = admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
            lease,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_spec=spec,
            native_receipt_handle=native,
            available_cleanup_budget=EXACT_BUDGET,
        )
        monkeypatch.setattr(guardian_v1, "_kcmp_file", unavailable)
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="failed closed",
        ):
            guardian_v1.initialize_h1_native_capability_guardian_v1(
                lease,
                native_receipt_spec=spec,
                native_receipt_handle=native,
                cleanup_budget_admission=admission,
            )
    assert receipts_v1.replay_h1_native_receipt_journal_v1(native)["record_count"] == 0
    monkeypatch.undo()

    late_root = fast_root / "late"
    late_root.mkdir()
    late_case = _build_case(late_root, bundle, analysis, suffix="guardian-late")
    late_envelope, late_spec, late_native = _prerequisites(
        late_root, late_case, bundle, analysis
    )
    with _lease(late_case, bundle) as admission_lease:
        late_admission = admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
            admission_lease,
            envelope=late_envelope,
            cleanup_analysis=analysis,
            native_receipt_spec=late_spec,
            native_receipt_handle=late_native,
            available_cleanup_budget=EXACT_BUDGET,
        )
    first = bundle.program.transitions[0]
    assert _execute_normal(
        late_case, bundle, callback=_normal_callback(first)
    ).outcome == "SUCCESS"
    with _lease(late_case, bundle) as late_lease:
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="before normal ordinal 1",
        ):
            guardian_v1.initialize_h1_native_capability_guardian_v1(
                late_lease,
                native_receipt_spec=late_spec,
                native_receipt_handle=late_native,
                cleanup_budget_admission=late_admission,
            )


def test_durable_c_d_replay_and_all_post_pin_exception_windows_fail_closed(
    fast_root, bundle, analysis, monkeypatch
):
    if not hasattr(os, "memfd_create"):
        pytest.skip("Linux memfd_create is unavailable")
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-durable-cd")
    envelope, spec, native = _prerequisites(fast_root, case, bundle, analysis)
    with _lease(case, bundle) as admission_lease:
        admission = admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
            admission_lease,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_spec=spec,
            native_receipt_handle=native,
            available_cleanup_budget=EXACT_BUDGET,
        )

    base, primary, seal = _admission_paths(admission)

    def initialize():
        with _lease(case, bundle) as reopened:
            return guardian_v1.initialize_h1_native_capability_guardian_v1(
                reopened,
                native_receipt_spec=spec,
                native_receipt_handle=native,
                cleanup_budget_admission=admission,
            )

    seal.unlink()
    with pytest.raises(
        guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
        match="base seal",
    ):
        initialize()
    os.link(primary, seal)

    foreign_link = base / "injected-foreign-c-d-hardlink"
    os.link(primary, foreign_link)
    with pytest.raises(
        guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
        match="topology",
    ):
        initialize()
    foreign_link.unlink()

    repair_entry = primary.parent / ".injected-repair"
    descriptor = os.open(
        repair_entry,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    os.close(descriptor)
    with pytest.raises(
        guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
        match="temp, repair, or foreign",
    ):
        initialize()
    repair_entry.unlink()

    guardian = initialize()
    try:
        # Failure after immediate pin but before the acquisition object is
        # registered must close master, witness, and registry anchor.
        slot_7 = _slot(spec, 7)
        intent_7 = _advance_to_dangling_intent(case, bundle, 7)
        raw_7 = os.memfd_create("guardian-constructor-failure", os.MFD_CLOEXEC)
        constructor_triple = []

        def fail_constructor(*args, **kwargs):
            cell = kwargs["cell"]
            constructor_triple.extend(
                (
                    cell._master_fd,
                    cell._witness_fd,
                    guardian_v1._ANCHOR_FDS[
                        (guardian._registry_key, slot_7["slot_key"])
                    ],
                )
            )
            raise RuntimeError("injected acquisition construction failure")

        with monkeypatch.context() as patcher:
            patcher.setattr(
                guardian_v1,
                "H1NativeCapabilityAcquisitionV1",
                fail_constructor,
            )
            with pytest.raises(RuntimeError, match="construction failure"):
                guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
                    guardian,
                    slot_key=slot_7["slot_key"],
                    h1_normal_site_intent_id=intent_7,
                    acquisition=lambda: guardian_v1.observe_h1_guarded_native_present_v1(
                        raw_7
                    ),
                )
        assert guardian._slot_states[slot_7["slot_key"]].cell is None
        assert (guardian._registry_key, slot_7["slot_key"]) not in guardian_v1._ANCHOR_FDS
        for descriptor in constructor_triple:
            with pytest.raises(OSError) as closed:
                os.fstat(descriptor)
            assert closed.value.errno == errno.EBADF

    finally:
        guardian._dispose_for_test_only()


def test_pending_document_validation_exception_revokes_the_pinned_triple(
    fast_root, bundle, analysis, monkeypatch
):
    if not hasattr(os, "memfd_create"):
        pytest.skip("Linux memfd_create is unavailable")
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-bad-pending")
    spec, _native, _admission, guardian = _guardian(
        fast_root, case, bundle, analysis
    )
    slot = _slot(spec, 7)
    intent = _advance_to_dangling_intent(case, bundle, 7)
    raw = os.memfd_create("guardian-pending-validation", os.MFD_CLOEXEC)
    triple = []
    real_execute = receipts_v1.execute_h1_native_resource_callback_once_v1

    class BadPending:
        @property
        def document(self):
            raise RuntimeError("injected pending document failure")

    def return_bad_pending(*args, **kwargs):
        real_execute(*args, **kwargs)
        cell = guardian._slot_states[slot["slot_key"]].cell
        assert cell is not None
        triple.extend(
            (
                cell._master_fd,
                cell._witness_fd,
                guardian_v1._ANCHOR_FDS[
                    (guardian._registry_key, slot["slot_key"])
                ],
            )
        )
        return BadPending()

    try:
        monkeypatch.setattr(
            receipts_v1,
            "execute_h1_native_resource_callback_once_v1",
            return_bad_pending,
        )
        with pytest.raises(RuntimeError, match="pending document failure"):
            guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
                guardian,
                slot_key=slot["slot_key"],
                h1_normal_site_intent_id=intent,
                acquisition=lambda: guardian_v1.observe_h1_guarded_native_present_v1(
                    raw
                ),
            )
        assert guardian._slot_states[slot["slot_key"]].cell is None
        assert (guardian._registry_key, slot["slot_key"]) not in guardian_v1._ANCHOR_FDS
        for descriptor in triple:
            with pytest.raises(OSError) as closed:
                os.fstat(descriptor)
            assert closed.value.errno == errno.EBADF
    finally:
        guardian._dispose_for_test_only()


def test_multiple_observations_revoke_the_immediately_pinned_triple(
    fast_root, bundle, analysis
):
    if not hasattr(os, "memfd_create"):
        pytest.skip("Linux memfd_create is unavailable")
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-multiple")
    spec, _native, _admission, guardian = _guardian(
        fast_root, case, bundle, analysis
    )
    slot = _slot(spec, 7)
    intent = _advance_to_dangling_intent(case, bundle, 7)
    raw = os.memfd_create("guardian-multiple-observation", os.MFD_CLOEXEC)
    triple = []

    def multiple_observations():
        first = guardian_v1.observe_h1_guarded_native_present_v1(raw)
        cell = guardian._slot_states[slot["slot_key"]].cell
        assert cell is not None
        triple.extend(
            (
                cell._master_fd,
                cell._witness_fd,
                guardian_v1._ANCHOR_FDS[
                    (guardian._registry_key, slot["slot_key"])
                ],
            )
        )
        guardian_v1.observe_h1_guarded_native_absent_v1(
            reason="INJECTED_SECOND_OBSERVATION"
        )
        return first

    try:
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="no unique sealed guardian observation",
        ):
            guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
                guardian,
                slot_key=slot["slot_key"],
                h1_normal_site_intent_id=intent,
                acquisition=multiple_observations,
            )
        assert guardian._slot_states[slot["slot_key"]].cell is None
        assert (guardian._registry_key, slot["slot_key"]) not in guardian_v1._ANCHOR_FDS
        for descriptor in triple:
            with pytest.raises(OSError) as closed:
                os.fstat(descriptor)
            assert closed.value.errno == errno.EBADF
    finally:
        guardian._dispose_for_test_only()


def test_irreversible_marker_primary_crash_burns_retry_permanently(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-marker-crash")
    envelope, spec, native = _prerequisites(fast_root, case, bundle, analysis)
    with _lease(case, bundle) as admission_lease:
        admission = admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
            admission_lease,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_spec=spec,
            native_receipt_handle=native,
            available_cleanup_budget=EXACT_BUDGET,
        )
    with _lease(case, bundle) as reopened:
        with pytest.raises(
            guardian_v1.H1NativeCapabilityGuardianInjectedCrashV1,
            match="after irreversible guardian marker primary",
        ):
            guardian_v1.initialize_h1_native_capability_guardian_v1(
                reopened,
                native_receipt_spec=spec,
                native_receipt_handle=native,
                cleanup_budget_admission=admission,
                crash_point=(
                    guardian_v1.H1NativeCapabilityGuardianInitializationCrashPointV1.AFTER_PRIMARY_FSYNC_BEFORE_SEAL
                ),
            )
    marker_primary, marker_seal = _marker_paths(admission)
    metadata = marker_primary.stat()
    assert metadata.st_nlink == 1
    assert metadata.st_mode & 0o777 == 0o400
    assert not marker_seal.exists()
    with _lease(case, bundle) as retry:
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="marker already burned",
        ):
            guardian_v1.initialize_h1_native_capability_guardian_v1(
                retry,
                native_receipt_spec=spec,
                native_receipt_handle=native,
                cleanup_budget_admission=admission,
            )
    key = (native.allocation_id, os.getpid(), guardian_v1._process_start_ticks())
    assert key not in guardian_v1._GUARDED_ALLOCATIONS
    assert key not in guardian_v1._LIVE_GUARDIANS


def test_marker_publication_rechecks_pinned_c_d_namespace_before_guardian(
    fast_root, bundle, analysis, monkeypatch
):
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-cd-toctou")
    envelope, spec, native = _prerequisites(fast_root, case, bundle, analysis)
    with _lease(case, bundle) as admission_lease:
        admission = admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
            admission_lease,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_spec=spec,
            native_receipt_handle=native,
            available_cleanup_budget=EXACT_BUDGET,
        )
    _base, _primary, c_d_seal = _admission_paths(admission)
    real_publish = guardian_v1._publish_irreversible_guardian_marker

    def publish_then_unlink_c_d(*args, **kwargs):
        marker_id = real_publish(*args, **kwargs)
        c_d_seal.unlink()
        return marker_id

    monkeypatch.setattr(
        guardian_v1,
        "_publish_irreversible_guardian_marker",
        publish_then_unlink_c_d,
    )
    with _lease(case, bundle) as reopened:
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="namespace mapping disappeared|topology changed",
        ):
            guardian_v1.initialize_h1_native_capability_guardian_v1(
                reopened,
                native_receipt_spec=spec,
                native_receipt_handle=native,
                cleanup_budget_admission=admission,
            )
    marker_primary, marker_seal = _marker_paths(admission)
    assert marker_primary.exists() and marker_seal.exists()
    key = (native.allocation_id, os.getpid(), guardian_v1._process_start_ticks())
    assert key not in guardian_v1._GUARDED_ALLOCATIONS


def test_marker_publisher_return_must_equal_the_published_document_identity(
    fast_root, bundle, analysis, monkeypatch
):
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-marker-id")
    envelope, spec, native = _prerequisites(fast_root, case, bundle, analysis)
    with _lease(case, bundle) as admission_lease:
        admission = admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
            admission_lease,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_spec=spec,
            native_receipt_handle=native,
            available_cleanup_budget=EXACT_BUDGET,
        )
    real_publish = guardian_v1._publish_irreversible_guardian_marker

    def publish_then_lie(*args, **kwargs):
        published = real_publish(*args, **kwargs)
        forged = "0" * 64
        assert forged != published
        return forged

    monkeypatch.setattr(
        guardian_v1,
        "_publish_irreversible_guardian_marker",
        publish_then_lie,
    )
    with _lease(case, bundle) as reopened:
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="wrong durable identity",
        ):
            guardian_v1.initialize_h1_native_capability_guardian_v1(
                reopened,
                native_receipt_spec=spec,
                native_receipt_handle=native,
                cleanup_budget_admission=admission,
            )
    marker_primary, marker_seal = _marker_paths(admission)
    assert marker_primary.exists() and marker_seal.exists()
    key = (native.allocation_id, os.getpid(), guardian_v1._process_start_ticks())
    assert key not in guardian_v1._GUARDED_ALLOCATIONS


def test_marker_publisher_cannot_skip_write_and_return_the_expected_id(
    fast_root, bundle, analysis, monkeypatch
):
    case = _build_case(fast_root, bundle, analysis, suffix="guardian-marker-skip")
    envelope, spec, native = _prerequisites(fast_root, case, bundle, analysis)
    with _lease(case, bundle) as admission_lease:
        admission = admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
            admission_lease,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_spec=spec,
            native_receipt_handle=native,
            available_cleanup_budget=EXACT_BUDGET,
        )

    def skip_write(_pins, *, marker_document, crash_point):
        del crash_point
        return marker_document[
            "h1_native_capability_guardian_init_marker_id"
        ]

    monkeypatch.setattr(
        guardian_v1,
        "_publish_irreversible_guardian_marker",
        skip_write,
    )
    with _lease(case, bundle) as reopened:
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
            match="marker root replay|independent read-only replay",
        ):
            guardian_v1.initialize_h1_native_capability_guardian_v1(
                reopened,
                native_receipt_spec=spec,
                native_receipt_handle=native,
                cleanup_budget_admission=admission,
            )
    marker_primary, marker_seal = _marker_paths(admission)
    assert not marker_primary.exists() and not marker_seal.exists()
    key = (native.allocation_id, os.getpid(), guardian_v1._process_start_ticks())
    assert key not in guardian_v1._GUARDED_ALLOCATIONS


def test_concurrent_cross_allocation_same_ofd_has_exactly_one_winner(
    fast_root, bundle, analysis
):
    if not hasattr(os, "memfd_create"):
        pytest.skip("Linux memfd_create is unavailable")
    roots = (fast_root / "race-a", fast_root / "race-b")
    for root in roots:
        root.mkdir()
    original = os.memfd_create("guardian-concurrent-ofd", os.MFD_CLOEXEC)
    aliases = (os.dup(original), os.dup(original))
    os.close(original)
    ready = threading.Barrier(2)
    finished = threading.Barrier(2)
    outcomes = queue.Queue()

    def worker(index, alias):
        guardian = None
        try:
            case = _build_case(
                roots[index], bundle, analysis, suffix=f"guardian-race-{index}"
            )
            spec, _native, _admission, guardian = _guardian(
                roots[index], case, bundle, analysis
            )
            slot = _slot(spec, 7)
            intent = _advance_to_dangling_intent(case, bundle, 7)
            ready.wait(timeout=600)
            try:
                guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
                    guardian,
                    slot_key=slot["slot_key"],
                    h1_normal_site_intent_id=intent,
                    acquisition=lambda: guardian_v1.observe_h1_guarded_native_present_v1(
                        alias
                    ),
                )
            except guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error as error:
                outcomes.put(("rejected", str(error)))
            else:
                outcomes.put(("winner", index))
            finished.wait(timeout=600)
        except BaseException as error:
            outcomes.put(("unexpected", repr(error)))
            try:
                ready.abort()
            except BaseException:
                pass
            try:
                finished.abort()
            except BaseException:
                pass
        finally:
            try:
                os.close(alias)
            except OSError:
                pass
            if guardian is not None:
                guardian._dispose_for_test_only()

    workers = [
        threading.Thread(target=worker, args=(index, alias), daemon=True)
        for index, alias in enumerate(aliases)
    ]
    for worker_thread in workers:
        worker_thread.start()
    for worker_thread in workers:
        worker_thread.join(timeout=900)
        assert not worker_thread.is_alive()
    results = [outcomes.get_nowait(), outcomes.get_nowait()]
    assert sum(result[0] == "winner" for result in results) == 1
    rejected = next(result for result in results if result[0] == "rejected")
    assert "cannot cross native slots or V6 allocations" in rejected[1]


def test_v8_domains_are_disjoint_and_guardian_objects_are_not_caller_mintable():
    registries = (
        domains_v1.K7_H1_DOMAIN_TAG_EXTENSION_V1,
        domains_v2.K7_H1_DOMAIN_TAG_EXTENSION_V2,
        domains_v3.K7_H1_DOMAIN_TAG_EXTENSION_V3,
        domains_v4.K7_H1_DOMAIN_TAG_EXTENSION_V4,
        domains_v5.K7_H1_DOMAIN_TAG_EXTENSION_V5,
        domains_v6.K7_H1_DOMAIN_TAG_EXTENSION_V6,
        domains_v7.K7_H1_DOMAIN_TAG_EXTENSION_V7,
        domains_v8.K7_H1_DOMAIN_TAG_EXTENSION_V8,
    )
    combined = set().union(*registries)
    assert len(combined) == sum(len(registry) for registry in registries)
    with pytest.raises(
        guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error,
        match="caller-minted",
    ):
        guardian_v1.H1NativeCapabilityGuardianSpecV1(object(), b"{}")
    with pytest.raises(ValueError, match="absent from the K7 H1 V8 registry"):
        domains_v8.extension_content_id_v8(
            domains_v6.CONSTRUCTION_K7_H1_NATIVE_RECEIPT_SPEC_V1_DOMAIN,
            {"cross_role": True},
        )
    assert canonical_json_bytes(
        {"domains": sorted(domains_v8.K7_H1_DOMAIN_TAG_EXTENSION_V8)}
    )
