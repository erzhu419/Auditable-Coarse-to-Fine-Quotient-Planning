from __future__ import annotations

import errno
import os
from pathlib import Path
import pickle
import select
import shutil
import tempfile

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_cleanup_action_journal_v1 as journal_v1
from acfqp import construction_k7_h1_domain_registry_extension_v1 as domains_v1
from acfqp import construction_k7_h1_domain_registry_extension_v2 as domains_v2
from acfqp import construction_k7_h1_domain_registry_extension_v3 as domains_v3
from acfqp import construction_k7_h1_domain_registry_extension_v4 as domains_v4
from acfqp import construction_k7_h1_domain_registry_extension_v5 as domains_v5
from acfqp import construction_k7_h1_domain_registry_extension_v6 as domains_v6
from acfqp import construction_k7_h1_domain_registry_extension_v7 as domains_v7
from acfqp import construction_k7_h1_domain_registry_extension_v8 as domains_v8
from acfqp import construction_k7_h1_domain_registry_extension_v9 as domains_v9
from acfqp import construction_k7_h1_failed_prefix_cleanup_budget_admission_v1 as admission_v1
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as output_join_v1
from acfqp import construction_k7_h1_native_capability_guardian_v1 as guardian_v1
from acfqp import construction_k7_h1_native_resource_receipt_journal_v1 as receipts_v1
from acfqp import construction_k7_h1_phase_aware_normal_prefix_v1 as normal_v1
from acfqp import construction_k7_h1_preadmitted_cleanup_transition_v2 as cleanup_v2

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
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-cleanup-journal-", dir=base))
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


def _cleanup_lease(case, transition):
    return cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    )


def _setup(root, case, bundle, analysis):
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
    with _lease(case, bundle) as lease:
        admission = admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
            lease,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_spec=spec,
            native_receipt_handle=native,
            available_cleanup_budget=EXACT_BUDGET,
        )
    with _lease(case, bundle) as lease:
        guardian = guardian_v1.initialize_h1_native_capability_guardian_v1(
            lease,
            native_receipt_spec=spec,
            native_receipt_handle=native,
            cleanup_budget_admission=admission,
        )
    return envelope, native, admission, guardian


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


def _execute_integrated(case, bundle, analysis, envelope, *, callback):
    with _lease(case, bundle) as lease:
        return cleanup_v2.execute_next_h1_normal_site_to_cleanup_boundary_v2(
            lease,
            cleanup_analysis=analysis,
            envelope=envelope,
            callback=callback,
        )


def _fail_at(case, bundle, analysis, envelope, ordinal):
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    while snapshot.document["next_ordinal"] < ordinal:
        row = bundle.program.transitions[snapshot.document["next_ordinal"] - 1]
        result = _execute_integrated(
            case,
            bundle,
            analysis,
            envelope,
            callback=_normal_callback(row),
        )
        assert result.outcome == "SUCCESS"
        snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)

    def failure():
        raise RuntimeError("registered failure")

    boundary = _execute_integrated(
        case, bundle, analysis, envelope, callback=failure
    )
    assert type(boundary) is cleanup_v2.H1NormalFailureCleanupBoundaryV2
    return boundary


def _advance_with_guarded_present_descriptor(
    case,
    bundle,
    analysis,
    envelope,
    native,
    guardian,
    *,
    ordinal,
    raw_descriptor,
    capability_kind,
):
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    while snapshot.document["next_ordinal"] < ordinal:
        row = bundle.program.transitions[snapshot.document["next_ordinal"] - 1]
        result = _execute_integrated(
            case,
            bundle,
            analysis,
            envelope,
            callback=_normal_callback(row),
        )
        assert result.outcome == "SUCCESS"
        snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    row = bundle.program.transitions[ordinal - 1]
    with _lease(case, bundle) as lease:
        with pytest.raises(normal_v1.H1NormalPrefixInjectedCrashV1):
            normal_v1.execute_next_h1_phase_aware_normal_site_v1(
                lease,
                callback=_normal_callback(row),
                crash_point=normal_v1.H1NormalPrefixCrashPointV1.AFTER_INTENT_FSYNC,
            )
    intent = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal).document[
        "dangling_intent_id"
    ]
    slot = next(
        value
        for value in native.spec.payload["predeclared_slots"]
        if value["normal_ordinal"] == ordinal
    )
    pending = guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
        guardian,
        slot_key=slot["slot_key"],
        h1_normal_site_intent_id=intent,
        acquisition=lambda: guardian_v1.observe_h1_guarded_native_present_v1(
            raw_descriptor
        ),
    )
    with _lease(case, bundle) as lease:
        event = normal_v1.execute_next_h1_phase_aware_normal_site_v1(
            lease, callback=_normal_callback(row)
        )
    binding = guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
        guardian, pending_binding=pending, normal_site_event=event
    )
    return slot, binding


def _advance_with_guarded_absent(
    case,
    bundle,
    analysis,
    envelope,
    native,
    guardian,
    *,
    ordinal,
):
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    while snapshot.document["next_ordinal"] < ordinal:
        row = bundle.program.transitions[snapshot.document["next_ordinal"] - 1]
        result = _execute_integrated(
            case,
            bundle,
            analysis,
            envelope,
            callback=_normal_callback(row),
        )
        assert result.outcome == "SUCCESS"
        snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    assert snapshot.document["next_ordinal"] == ordinal
    row = bundle.program.transitions[ordinal - 1]
    with _lease(case, bundle) as lease:
        with pytest.raises(normal_v1.H1NormalPrefixInjectedCrashV1):
            normal_v1.execute_next_h1_phase_aware_normal_site_v1(
                lease,
                callback=_normal_callback(row),
                crash_point=normal_v1.H1NormalPrefixCrashPointV1.AFTER_INTENT_FSYNC,
            )
    intent = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal).document[
        "dangling_intent_id"
    ]
    slot = next(
        value
        for value in native.spec.payload["predeclared_slots"]
        if value["normal_ordinal"] == ordinal
    )
    pending = guardian_v1.execute_h1_guarded_native_acquisition_once_v1(
        guardian,
        slot_key=slot["slot_key"],
        h1_normal_site_intent_id=intent,
        acquisition=lambda: guardian_v1.observe_h1_guarded_native_absent_v1(
            reason="REGISTERED_TEST_ABSENCE"
        ),
    )
    with _lease(case, bundle) as lease:
        event = normal_v1.execute_next_h1_phase_aware_normal_site_v1(
            lease, callback=_normal_callback(row)
        )
    binding = guardian_v1.bind_h1_guarded_native_result_to_normal_event_v1(
        guardian, pending_binding=pending, normal_site_event=event
    )
    return slot, binding


def _manifest_and_handle(
    case, analysis, envelope, native, admission, guardian, boundary
):
    with _cleanup_lease(case, boundary.transition) as lease:
        manifest = journal_v1.freeze_h1_cleanup_action_manifest_v1(
            lease,
            primary_failure_event=boundary.failure_event,
            transition=boundary.transition,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_handle=native,
            guardian=guardian,
            cleanup_budget_admission=admission,
        )
        stale_lease = lease
    with pytest.raises(journal_v1.ConstructionK7H1CleanupActionJournalV1Error):
        journal_v1.initialize_h1_cleanup_action_journal_v1(
            manifest,
            cleanup_lease=stale_lease,
            transition=boundary.transition,
        )
    with _cleanup_lease(case, boundary.transition) as lease:
        handle = journal_v1.initialize_h1_cleanup_action_journal_v1(
            manifest,
            cleanup_lease=lease,
            transition=boundary.transition,
        )
    return manifest, handle


def _execute_one(
    handle,
    case,
    analysis,
    envelope,
    native,
    guardian,
    boundary,
    *,
    ordinal,
    crash=journal_v1.H1CleanupActionCrashPointV1.NONE,
):
    with _cleanup_lease(case, boundary.transition) as lease:
        return journal_v1.execute_next_h1_cleanup_action_v1(
            handle,
            cleanup_lease=lease,
            transition=boundary.transition,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_handle=native,
            guardian=guardian,
            owner=case.owner,
            expected_cleanup_ordinal=ordinal,
            crash_point=crash,
        )


def test_exact_join_component_budget_and_conservative_release_are_crash_idempotent(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="e2-owner-release")
    envelope, native, admission, guardian = _setup(
        fast_root, case, bundle, analysis
    )
    boundary = _fail_at(case, bundle, analysis, envelope, 2)
    # The public marker ID is insufficient if either durable prerequisite
    # primary disappears.  E2 must independently replay C-D and E1.
    route = admission.payload["route_attempt_id"]
    prerequisite_primaries = (
        fast_root
        / ".acfqp-k7-h1-failed-prefix-cleanup-budget-admissions-v1"
        / route
        / "cleanup-budget-admission.json",
        fast_root
        / ".acfqp-k7-h1-native-capability-guardian-v1"
        / route
        / "guardian-init-marker.json",
    )
    for primary in prerequisite_primaries:
        parked = primary.with_suffix(".parked")
        os.rename(primary, parked)
        try:
            with _cleanup_lease(case, boundary.transition) as lease:
                with pytest.raises(
                    journal_v1.ConstructionK7H1CleanupActionJournalV1Error
                ):
                    journal_v1.freeze_h1_cleanup_action_manifest_v1(
                        lease,
                        primary_failure_event=boundary.failure_event,
                        transition=boundary.transition,
                        envelope=envelope,
                        cleanup_analysis=analysis,
                        native_receipt_handle=native,
                        guardian=guardian,
                        cleanup_budget_admission=admission,
                    )
        finally:
            os.rename(parked, primary)
    manifest, handle = _manifest_and_handle(
        case, analysis, envelope, native, admission, guardian, boundary
    )
    assert manifest.payload["action_count"] == 1
    assert {
        row["e2_join_disposition"]
        for row in manifest.payload["cleanup_cutoff_join"]["slot_joins"]
    } == {"ABSENT_CONTROL_FLOW"}
    assert manifest.payload["actions"][0]["budget_category"] == "MEMORY_RELEASE"
    with pytest.raises(journal_v1.H1CleanupActionJournalInjectedCrashV1):
        _execute_one(
            handle,
            case,
            analysis,
            envelope,
            native,
            guardian,
            boundary,
            ordinal=1,
            crash=journal_v1.H1CleanupActionCrashPointV1.AFTER_INTENT_FILE_FSYNC,
        )
    with pytest.raises(journal_v1.H1CleanupActionJournalInjectedCrashV1):
        _execute_one(
            handle,
            case,
            analysis,
            envelope,
            native,
            guardian,
            boundary,
            ordinal=1,
            crash=journal_v1.H1CleanupActionCrashPointV1.AFTER_EFFECT_BEFORE_RESULT,
        )
    with pytest.raises(journal_v1.H1CleanupActionJournalInjectedCrashV1):
        _execute_one(
            handle,
            case,
            analysis,
            envelope,
            native,
            guardian,
            boundary,
            ordinal=1,
            crash=journal_v1.H1CleanupActionCrashPointV1.AFTER_RESULT_FILE_FSYNC,
        )
    # Simulate an actual partial cursor write after the immutable result is one
    # row ahead.  Only this unique strict prefix is repairable.
    attempt_fd, lock_fd, cursor_fd = journal_v1._open_locked(handle)
    try:
        records = journal_v1._scan_records(attempt_fd)
        cursor_raw = journal_v1._read_descriptor(cursor_fd)
        cursor_rows = [
            journal_v1._parse(line, "test cursor")
            for line in cursor_raw.splitlines()
        ]
        result_id = journal_v1._record_identity(records[-1])[2]
        next_row = journal_v1._cursor_row(
            journal_v1._cursor_payload(
                len(cursor_rows),
                cursor_rows[-1]["h1_cleanup_journal_cursor_id"],
                "RESULT",
                result_id,
            )
        )
        next_raw = journal_v1.canonical_json_bytes(next_row) + b"\n"
        os.lseek(cursor_fd, 0, os.SEEK_END)
        journal_v1._write_all(cursor_fd, next_raw[: len(next_raw) // 2])
        os.fsync(cursor_fd)
    finally:
        journal_v1._unlock(lock_fd, cursor_fd, attempt_fd)
    result = _execute_one(
        handle,
        case,
        analysis,
        envelope,
        native,
        guardian,
        boundary,
        ordinal=1,
    )
    assert result["outcome"] == "OWNER_CONSERVATIVE_RELEASED"
    assert _execute_one(
        handle,
        case,
        analysis,
        envelope,
        native,
        guardian,
        boundary,
        ordinal=1,
    )["h1_cleanup_action_result_id"] == result["h1_cleanup_action_result_id"]
    replay = journal_v1.replay_h1_cleanup_action_journal_v1(handle)
    assert replay["budget_consumed"] == {
        "RESOLVE": 0,
        "REAP": 0,
        "MOUNT_CLOSE": 0,
        "MEMORY_RELEASE": 1,
        "OUTPUT_RELEASE": 0,
    }
    assert replay["drained"] is True
    assert replay["normal_ordinal_41_to_52_success_events_issued"] is False
    # A coherently rehashed but semantically impossible result must fail the
    # action-kind verifier, not merely its content hash.
    attempt_fd, lock_fd, cursor_fd = journal_v1._open_locked(handle)
    try:
        durable_records, _ = journal_v1._load_state_locked(
            handle, attempt_fd, cursor_fd, repair=False
        )
    finally:
        journal_v1._unlock(lock_fd, cursor_fd, attempt_fd)
    fake = dict(durable_records[-1])
    fake.pop("h1_cleanup_action_result_id")
    fake["outcome"] = "PIDFD_REAPED"
    fake["effect_evidence"] = {
        "pidfd_waitid_reap_performed": True,
        "pidfd_close_alone_counted_as_reap": False,
        "business_or_worker_role_identity_proven": False,
    }
    fake["h1_cleanup_action_result_id"] = journal_v1._content_id(
        journal_v1.RESULT_DOMAIN, fake
    )
    with pytest.raises(journal_v1.ConstructionK7H1CleanupActionJournalV1Error):
        journal_v1._validate_record_semantics(handle, [durable_records[0], fake])
    forged_cid = dict(durable_records[-1])
    forged_cid.pop("h1_cleanup_action_result_id")
    forged_cid["effect_evidence"] = {
        **forged_cid["effect_evidence"],
        "h1_owner_cleanup_sidecar_allocation_id": manifest.manifest_id,
    }
    forged_cid["h1_cleanup_action_result_id"] = journal_v1._content_id(
        journal_v1.RESULT_DOMAIN, forged_cid
    )
    with pytest.raises(journal_v1.ConstructionK7H1CleanupActionJournalV1Error):
        journal_v1._validate_record_semantics(
            handle, [durable_records[0], forged_cid]
        )

    if hasattr(os, "fork"):
        reservation_key = (handle.allocation_id, 999)
        with journal_v1._EFFECT_RESERVATION_LOCK:
            journal_v1._ACTIVE_EFFECT_RESERVATIONS[reservation_key] = object()
        child = os.fork()
        if child == 0:  # pragma: no cover - child side
            ok = (
                reservation_key in journal_v1._BURNED_EFFECT_RESERVATIONS
                and reservation_key not in journal_v1._ACTIVE_EFFECT_RESERVATIONS
                and handle._closed
            )
            try:
                journal_v1.replay_h1_cleanup_action_journal_v1(handle)
            except journal_v1.ConstructionK7H1CleanupActionJournalV1Error:
                pass
            else:
                ok = False
            os._exit(0 if ok else 1)
        _, status = os.waitpid(child, 0)
        with journal_v1._EFFECT_RESERVATION_LOCK:
            journal_v1._ACTIVE_EFFECT_RESERVATIONS.pop(reservation_key, None)
        assert os.waitstatus_to_exitcode(status) == 0

    # Replacing the allocation-root lock with a valid-looking symlink must be
    # rejected; restoring the original pinned inode restores replay.
    root_lock = Path(handle.root_directory) / journal_v1._ROOT_LOCK_FILE
    parked_lock = root_lock.with_suffix(".parked")
    os.rename(root_lock, parked_lock)
    os.symlink("/dev/null", root_lock)
    try:
        with pytest.raises(journal_v1.ConstructionK7H1CleanupActionJournalV1Error):
            journal_v1.replay_h1_cleanup_action_journal_v1(handle)
    finally:
        root_lock.unlink()
        os.rename(parked_lock, root_lock)
    assert journal_v1.replay_h1_cleanup_action_journal_v1(handle)["drained"] is True
    record = next(Path(handle.attempt_directory).glob("record-*-result-*.json"))
    attack = Path(handle.attempt_directory) / "extra-hardlink"
    os.link(record, attack)
    with pytest.raises(journal_v1.ConstructionK7H1CleanupActionJournalV1Error):
        journal_v1.replay_h1_cleanup_action_journal_v1(handle)
    journal_v1.close_h1_cleanup_action_journal_v1(handle)
    with pytest.raises(journal_v1.ConstructionK7H1CleanupActionJournalV1Error):
        journal_v1.replay_h1_cleanup_action_journal_v1(handle)


def test_v9_domains_and_objects_are_disjoint_nonmintable_and_non_authoritative():
    prior = set().union(
        domains_v1.K7_H1_DOMAIN_TAG_EXTENSION_V1,
        domains_v2.K7_H1_DOMAIN_TAG_EXTENSION_V2,
        domains_v3.K7_H1_DOMAIN_TAG_EXTENSION_V3,
        domains_v4.K7_H1_DOMAIN_TAG_EXTENSION_V4,
        domains_v5.K7_H1_DOMAIN_TAG_EXTENSION_V5,
        domains_v6.K7_H1_DOMAIN_TAG_EXTENSION_V6,
        domains_v7.K7_H1_DOMAIN_TAG_EXTENSION_V7,
        domains_v8.K7_H1_DOMAIN_TAG_EXTENSION_V8,
    )
    assert len(domains_v9.K7_H1_DOMAIN_TAG_EXTENSION_V9) == 9
    assert prior.isdisjoint(domains_v9.K7_H1_DOMAIN_TAG_EXTENSION_V9)
    with pytest.raises(journal_v1.ConstructionK7H1CleanupActionJournalV1Error):
        journal_v1.H1CleanupActionManifestV1(object(), b"{}")
    assert journal_v1.UNDERLYING_OFD_LAST_REFERENCE_RELEASE_PROVEN is False
    assert journal_v1.MOUNT_RESOURCE_RELEASE_PROVEN is False
    assert journal_v1.CURRENT_ACCESS_AUTHORITY_PRESENT is False
    assert journal_v1.FORMAL_COUNTER_RECORDS_ISSUED is False
    assert journal_v1.FORMAL_WORK_VECTOR_ISSUED is False
    assert journal_v1.FORMAL_COMPARISON_VECTOR_ISSUED is False
    assert journal_v1.FORMAL_V7_ROUTE_AUTHORITY_PRESENT is False
    assert journal_v1.OFFICIAL_EXECUTION_ALLOWED is False


def test_mount_cleanup_closes_only_guardian_aliases_and_external_same_ofd_survives(
    fast_root, bundle, analysis
):
    if not hasattr(os, "memfd_create"):
        pytest.skip("memfd is required for exact same-OFD alias test")
    case = _build_case(fast_root, bundle, analysis, suffix="e2-ofd-alias")
    envelope, native, admission, guardian = _setup(
        fast_root, case, bundle, analysis
    )
    original = os.memfd_create("acfqp-e2-ofd", os.MFD_CLOEXEC)
    external_alias = os.dup(original)
    try:
        _slot, binding = _advance_with_guarded_present_descriptor(
            case,
            bundle,
            analysis,
            envelope,
            native,
            guardian,
            ordinal=7,
            raw_descriptor=original,
            capability_kind="OFD",
        )
        _absent_slot, absent_binding = _advance_with_guarded_absent(
            case,
            bundle,
            analysis,
            envelope,
            native,
            guardian,
            ordinal=9,
        )
        boundary = _fail_at(case, bundle, analysis, envelope, 10)
        manifest, handle = _manifest_and_handle(
            case, analysis, envelope, native, admission, guardian, boundary
        )
        results = [
            _execute_one(
                handle,
                case,
                analysis,
                envelope,
                native,
                guardian,
                boundary,
                ordinal=ordinal,
            )
            for ordinal in range(1, manifest.payload["action_count"] + 1)
        ]
        close = next(
            row
            for row in results
            if row["action_kind"] == "CLOSE_MOUNT"
            and row["outcome"] == "GUARDIAN_ALIAS_SET_CLOSED"
        )
        assert close["outcome"] == "GUARDIAN_ALIAS_SET_CLOSED"
        assert close["effect_evidence"]["guardian_alias_set_closed"] is True
        assert close["underlying_ofd_last_reference_release_proven"] is False
        assert close["mount_resource_release_proven"] is False
        assert any(
            row["outcome"] == "SKIPPED_KNOWN_ABSENT"
            and row["effect_evidence"]["cutoff_join_disposition"]
            == "ABSENT_EXPLICIT"
            for row in results
        )
        assert {
            row["e2_join_disposition"]
            for row in manifest.payload["cleanup_cutoff_join"]["slot_joins"]
        } >= {"PRESENT_LIVE", "ABSENT_EXPLICIT", "ABSENT_CONTROL_FLOW"}
        # This is the essential anti-overclaim regression: another alias of
        # the same OFD remains usable after all Guardian aliases are closed.
        assert os.fstat(external_alias).st_ino >= 0
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error
        ):
            _ = binding.status
        assert absent_binding.status.value == "ABSENT"
        replay = journal_v1.replay_h1_cleanup_action_journal_v1(handle)
        selected_mount_close_count = sum(
            row["action_kind"] == "CLOSE_MOUNT" for row in results
        )
        assert selected_mount_close_count == 2
        assert (
            replay["budget_consumed"]["MOUNT_CLOSE"]
            == selected_mount_close_count
        )
        assert replay["drained_with_unresolved_or_partial_effect"] is True
        journal_v1.close_h1_cleanup_action_journal_v1(handle)
    finally:
        try:
            os.close(original)
        except OSError as error:
            assert error.errno == errno.EBADF
        os.close(external_alias)


def test_pidfd_reap_uses_waitid_and_unresolved_mounts_do_not_stop_later_cleanup(
    fast_root, bundle, analysis, monkeypatch
):
    if not all(
        (
            hasattr(os, "fork"),
            hasattr(os, "pidfd_open"),
            hasattr(os, "P_PIDFD"),
            hasattr(os, "waitid"),
        )
    ):
        pytest.skip("Linux pidfd/waitid support is required")
    case = _build_case(fast_root, bundle, analysis, suffix="e2-pidfd-reap")
    envelope, native, admission, guardian = _setup(
        fast_root, case, bundle, analysis
    )
    child = os.fork()
    if child == 0:  # pragma: no cover - child side
        os._exit(0)
    pidfd = os.pidfd_open(child, 0)
    try:
        _slot, binding = _advance_with_guarded_present_descriptor(
            case,
            bundle,
            analysis,
            envelope,
            native,
            guardian,
            ordinal=26,
            raw_descriptor=pidfd,
            capability_kind="PIDFD",
        )
        poller = select.poll()
        # The original pidfd is closed by adoption.  The test observes child
        # exit with a temporary independent pidfd, then closes it before E2.
        readiness_fd = os.pidfd_open(child, 0)
        try:
            poller.register(readiness_fd, select.POLLIN)
            assert poller.poll(5_000)
        finally:
            os.close(readiness_fd)
        boundary = _fail_at(case, bundle, analysis, envelope, 27)
        manifest, handle = _manifest_and_handle(
            case, analysis, envelope, native, admission, guardian, boundary
        )
        assert "UNRESOLVED_V6_CUTOFF" in {
            row["e2_join_disposition"]
            for row in manifest.payload["cleanup_cutoff_join"]["slot_joins"]
        }

        def reject_generic_ofd_close_for_pidfd(*_args, **_kwargs):
            raise AssertionError(
                "PIDFD reap must close its prevalidated cell without OFD revalidation"
            )

        monkeypatch.setattr(
            journal_v1,
            "_close_guardian_alias_set",
            reject_generic_ofd_close_for_pidfd,
        )
        results = [
            _execute_one(
                handle,
                case,
                analysis,
                envelope,
                native,
                guardian,
                boundary,
                ordinal=ordinal,
            )
            for ordinal in range(1, manifest.payload["action_count"] + 1)
        ]
        reap = next(row for row in results if row["action_kind"] == "REAP_DESCENDANT")
        assert reap["outcome"] == "PIDFD_REAPED"
        assert reap["effect_evidence"]["pidfd_waitid_reap_performed"] is True
        assert reap["effect_evidence"]["pidfd_close_alone_counted_as_reap"] is False
        with pytest.raises(ChildProcessError):
            os.waitpid(child, os.WNOHANG)
        blocked_mounts = [
            row
            for row in results
            if row["action_kind"] == "CLOSE_MOUNT"
            and row["outcome"] == "BLOCKED_UNRESOLVED"
        ]
        assert len(blocked_mounts) == 10
        assert results[-1]["outcome"] == "OWNER_CONSERVATIVE_RELEASED"
        replay = journal_v1.replay_h1_cleanup_action_journal_v1(handle)
        assert replay["drained"] is True
        assert replay["drained_with_unresolved_or_partial_effect"] is True
        assert replay["budget_consumed"]["REAP"] == 1
        assert replay["budget_consumed"]["MOUNT_CLOSE"] == 10
        attempt_fd, lock_fd, cursor_fd = journal_v1._open_locked(handle)
        try:
            records, _ = journal_v1._load_state_locked(
                handle, attempt_fd, cursor_fd, repair=False
            )
        finally:
            journal_v1._unlock(lock_fd, cursor_fd, attempt_fd)
        preobs_index = next(
            index
            for index, row in enumerate(records)
            if row["schema"]
            == "acfqp.k7_h1_cleanup_pidfd_preobservation.v1"
        )
        fake_preobs = dict(records[preobs_index])
        fake_preobs.pop("h1_cleanup_pidfd_preobservation_id")
        fake_preobs["preobservation"] = {
            **fake_preobs["preobservation"],
            "child_exit_observed": False,
        }
        fake_preobs["h1_cleanup_pidfd_preobservation_id"] = (
            journal_v1._content_id(journal_v1.PREOBS_DOMAIN, fake_preobs)
        )
        forged_records = list(records)
        forged_records[preobs_index] = fake_preobs
        with pytest.raises(
            journal_v1.ConstructionK7H1CleanupActionJournalV1Error
        ):
            journal_v1._validate_record_semantics(handle, forged_records)
        with pytest.raises(
            guardian_v1.ConstructionK7H1NativeCapabilityGuardianV1Error
        ):
            _ = binding.status
        journal_v1.close_h1_cleanup_action_journal_v1(handle)
    finally:
        try:
            os.close(pidfd)
        except OSError as error:
            assert error.errno == errno.EBADF
        try:
            os.waitpid(child, 0)
        except ChildProcessError:
            pass
