from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import queue
import shutil
import tempfile
import threading

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_attempt_execution_phase_owner_v1 as phase_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as output_join_v1
from acfqp import construction_k7_h1_native_resource_receipt_journal_v1 as receipts_v1
from acfqp import construction_k7_h1_phase_aware_normal_prefix_v1 as normal_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4
from acfqp.phase3e_ids import canonical_json_bytes


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANCHOR_ID = "4a4b0d1888f0ac18123e4163e1a26b0583a64946d2eb219e02d4b77dc0a3e327"


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _NormalCase:
    root: Path
    handle: normal_v1.H1NormalPrefixHandleV1
    gate: rejection_v1.H1AttemptRejectionGateHandleV1
    owner: owner_v4.H1SharedCapOwnerV4WalHandle
    dispatch_profile: dispatch_v1.H1LifecycleDispatchProfileV1
    phase: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1


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
def normal_case(bundle, analysis):
    base = "/dev/shm" if Path("/dev/shm").is_dir() else "/tmp"
    root = Path(tempfile.mkdtemp(prefix="acfqp-h1-native-receipt-normal-", dir=base))
    hard_caps = {path: 100_000 for path in owner_v3.SHARED_RESOURCE_PATHS}
    profile = owner_v3.freeze_h1_shared_cap_profile_core_v3(
        logical_occurrence_id=_id("native-receipt-occurrence"),
        route_attempt_id=_id("native-receipt-attempt"),
        decision_point_id=_id("native-receipt-decision"),
        transaction_id=_id("native-receipt-transaction"),
        caller_pinned_lifecycle_provenance_id=bundle.program.provenance_id,
        lifecycle_program_snapshot_id=bundle.program.snapshot_id,
        lifecycle_program_id=bundle.program.program_id,
        lifecycle_branch_analysis_id=bundle.program.branch_analysis_id,
        hard_caps=hard_caps,
    )
    source = owner_v3.freeze_h1_shared_cap_owner_v3_source_manifest(
        caller_pinned_lifecycle_provenance_id=profile.caller_pinned_lifecycle_provenance_id,
        lifecycle_program_snapshot_id=profile.lifecycle_program_snapshot_id,
        lifecycle_program_id=profile.lifecycle_program_id,
        lifecycle_branch_analysis_id=profile.lifecycle_branch_analysis_id,
    )
    gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=root,
        logical_occurrence_id=profile.logical_occurrence_id,
        route_attempt_id=profile.route_attempt_id,
        caller_pinned_lifecycle_provenance_id=profile.caller_pinned_lifecycle_provenance_id,
    )
    gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(root, gate_spec)
    historical_owner = owner_v3.initialize_h1_shared_cap_owner_v3(
        root, profile=profile, source_manifest=source, rejection_gate=gate
    )
    operands = {
        row["site_key"]: (
            1
            if row["handler_mode"]
            == dispatch_v1.H1LifecycleHandlerModeV1.IMMEDIATE_UNIT.value
            else 10
        )
        for row in bundle.registry.handlers
        if row["reservation_edge"] is True
    }
    dispatch_profile = dispatch_v1.bind_h1_lifecycle_dispatch_profile_v1(
        bundle, historical_owner, site_reservation_uppers=operands
    )
    upgraded = owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(
        historical_owner
    )
    owner = owner_v4.open_h1_shared_cap_owner_v4_wal(
        upgraded.owner_directory,
        expected_runtime_id=upgraded.runtime_id,
        gate_directory=upgraded.gate_directory,
    )
    phase_spec = phase_v1.freeze_h1_attempt_execution_phase_spec_v1(
        root,
        logical_occurrence_id=profile.logical_occurrence_id,
        route_attempt_id=profile.route_attempt_id,
        caller_pinned_lifecycle_provenance_id=profile.caller_pinned_lifecycle_provenance_id,
        rejection_gate=gate,
        anchored_program_id=bundle.program.anchored_program_id,
        handler_registry_id=bundle.registry.registry_id,
        cleanup_analysis=analysis,
    )
    phase = phase_v1.initialize_h1_attempt_execution_phase_owner_v1(
        phase_spec, rejection_gate=gate
    )
    normal_spec = normal_v1.freeze_h1_normal_prefix_spec_v1(
        root,
        phase_handle=phase,
        rejection_gate=gate,
        owner=owner,
        bundle=bundle,
        dispatch_profile=dispatch_profile,
    )
    handle = normal_v1.initialize_h1_normal_prefix_journal_v1(normal_spec)
    try:
        yield _NormalCase(root, handle, gate, owner, dispatch_profile, phase, bundle)
    finally:
        shutil.rmtree(root)


@pytest.fixture
def receipt_base():
    base = "/dev/shm" if Path("/dev/shm").is_dir() else "/tmp"
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-native-receipt-", dir=base))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _journal(normal_case: _NormalCase, receipt_base: Path):
    spec = receipts_v1.freeze_h1_native_receipt_journal_spec_v1(
        receipt_base, normal_handle=normal_case.handle
    )
    handle = receipts_v1.initialize_h1_native_receipt_journal_v1(
        spec, normal_handle=normal_case.handle
    )
    return spec, handle


def _callback_for(row):
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


def _execute_normal(normal_case: _NormalCase, *, callback=None, crash_point=None):
    with normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        normal_case.handle,
        phase_handle=normal_case.phase,
        rejection_gate=normal_case.gate,
        owner=normal_case.owner,
        bundle=normal_case.bundle,
        dispatch_profile=normal_case.dispatch_profile,
    ) as lease:
        kwargs = {"callback": callback}
        if crash_point is not None:
            kwargs["crash_point"] = crash_point
        return normal_v1.execute_next_h1_phase_aware_normal_site_v1(lease, **kwargs)


def _advance_to_dangling_intent(normal_case: _NormalCase, ordinal: int) -> str:
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(normal_case.handle)
    while snapshot.document["next_ordinal"] < ordinal:
        row = normal_case.bundle.program.transitions[snapshot.document["next_ordinal"] - 1]
        event = _execute_normal(normal_case, callback=_callback_for(row))
        assert event.outcome == "SUCCESS"
        snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(normal_case.handle)
    row = normal_case.bundle.program.transitions[ordinal - 1]
    with pytest.raises(normal_v1.H1NormalPrefixInjectedCrashV1):
        _execute_normal(
            normal_case,
            callback=_callback_for(row),
            crash_point=normal_v1.H1NormalPrefixCrashPointV1.AFTER_INTENT_FSYNC,
        )
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(normal_case.handle)
    assert snapshot.document["next_ordinal"] == ordinal
    return snapshot.document["dangling_intent_id"]


def _commit_dangling_success(normal_case: _NormalCase):
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(normal_case.handle)
    ordinal = snapshot.document["next_ordinal"]
    row = normal_case.bundle.program.transitions[ordinal - 1]
    return _execute_normal(normal_case, callback=_callback_for(row))


def _commit_dangling_failure(normal_case: _NormalCase):
    def boom():
        raise RuntimeError("registered native-receipt test failure")

    return _execute_normal(normal_case, callback=boom)


def _present(kind):
    return receipts_v1.observe_h1_native_present_v1(987654321, capability_kind=kind)


def _walk_keys(value):
    if type(value) is dict:
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif type(value) is list:
        for child in value:
            yield from _walk_keys(child)


def test_exact_twelve_slots_are_predeclared_before_ordinal_one_and_sealed(
    normal_case, receipt_base, monkeypatch
):
    freeze_race_base = receipt_base / "freeze-normal-lock-race"
    freeze_race_base.mkdir()
    original_freeze = receipts_v1._freeze_h1_native_receipt_journal_spec_under_normal_lock
    replay_started = threading.Event()
    replay_finished = threading.Event()

    def replay_contender():
        replay_started.set()
        normal_v1.replay_h1_normal_prefix_journal_v1(normal_case.handle)
        replay_finished.set()

    def interposed_freeze(*args, **kwargs):
        contender = threading.Thread(target=replay_contender)
        contender.start()
        assert replay_started.wait(timeout=2)
        assert replay_finished.wait(timeout=0.1) is False
        result = original_freeze(*args, **kwargs)
        contender_threads_for_freeze.append(contender)
        return result

    contender_threads_for_freeze = []
    monkeypatch.setattr(
        receipts_v1,
        "_freeze_h1_native_receipt_journal_spec_under_normal_lock",
        interposed_freeze,
    )
    receipts_v1.freeze_h1_native_receipt_journal_spec_v1(
        freeze_race_base, normal_handle=normal_case.handle
    )
    contender_threads_for_freeze[0].join(timeout=10)
    assert replay_finished.is_set()
    monkeypatch.setattr(
        receipts_v1,
        "_freeze_h1_native_receipt_journal_spec_under_normal_lock",
        original_freeze,
    )

    for index, crash_point in enumerate(
        (
            "AFTER_ATTEMPT_DIRECTORY",
            "AFTER_CURSOR_FSYNC",
            "AFTER_ALLOCATION_PUBLISH",
            "AFTER_SEALS_FSYNC",
        )
    ):
        crash_base = receipt_base / f"initialization-crash-{index}"
        crash_base.mkdir()
        crash_spec = receipts_v1.freeze_h1_native_receipt_journal_spec_v1(
            crash_base, normal_handle=normal_case.handle
        )
        with pytest.raises(receipts_v1.H1NativeReceiptInjectedCrashV1):
            receipts_v1.initialize_h1_native_receipt_journal_v1(
                crash_spec,
                normal_handle=normal_case.handle,
                crash_point=crash_point,
            )
        recovered = receipts_v1.initialize_h1_native_receipt_journal_v1(
            crash_spec, normal_handle=normal_case.handle
        )
        assert receipts_v1.replay_h1_native_receipt_journal_v1(recovered)[
            "record_count"
        ] == 0
    spec, handle = _journal(normal_case, receipt_base)
    slots = spec.payload["predeclared_slots"]
    assert len(slots) == 12
    assert [row["normal_ordinal"] for row in slots] == [
        7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 26, 30
    ]
    assert sum(row["capability_kind"] == "OFD" for row in slots) == 10
    assert [row["resource_role"] for row in slots[-2:]] == ["WORKER", "BUSINESS"]
    assert all(row["broker_role"] == "BROKER" for row in slots)
    assert all(row["predeclared_before_normal_ordinal_1"] is True for row in slots)
    assert spec.payload["h1_normal_prefix_genesis_snapshot_id"] == (
        normal_v1.replay_h1_normal_prefix_journal_v1(normal_case.handle).snapshot_id
    )
    replay = receipts_v1.replay_h1_native_receipt_journal_v1(handle)
    assert replay["slot_count"] == 12
    assert set(replay["slot_resolutions"].values()) == {"NOT_STARTED"}
    assert replay["real_kernel_credential_authority_present"] is False
    assert replay["native_cleanup_authority_present"] is False
    assert replay["current_access_authority_present"] is False
    assert replay["same_broker_initialization_convergence_present"] is True
    assert replay["cross_process_initialization_recovery_present"] is False
    assert replay["formal_counter_records_issued"] is False
    assert replay["official_execution_allowed"] is False
    reopened = receipts_v1.open_h1_native_receipt_journal_v1(
        spec, normal_handle=normal_case.handle
    )
    assert reopened.allocation_id == handle.allocation_id
    assert receipts_v1.initialize_h1_native_receipt_journal_v1(
        spec, normal_handle=normal_case.handle
    ).allocation_id == handle.allocation_id

    race_base = receipt_base / "normal-lock-race"
    race_base.mkdir()
    race_spec = receipts_v1.freeze_h1_native_receipt_journal_spec_v1(
        race_base, normal_handle=normal_case.handle
    )
    original_complete = receipts_v1._complete_attempt_initialization
    contender_started = threading.Event()
    contender_finished = threading.Event()
    contender_events = []
    contender_threads = []

    def run_contender():
        contender_started.set()
        contender_events.append(_execute_normal(normal_case, callback=None))
        contender_finished.set()

    def interposed_complete(*args, **kwargs):
        contender = threading.Thread(target=run_contender)
        contender_threads.append(contender)
        contender.start()
        assert contender_started.wait(timeout=2)
        assert contender_finished.wait(timeout=0.1) is False
        return original_complete(*args, **kwargs)

    monkeypatch.setattr(
        receipts_v1, "_complete_attempt_initialization", interposed_complete
    )
    race_handle = receipts_v1.initialize_h1_native_receipt_journal_v1(
        race_spec, normal_handle=normal_case.handle
    )
    contender_threads[0].join(timeout=10)
    assert contender_finished.is_set()
    assert contender_events[0].ordinal == 1
    assert contender_events[0].outcome == "SUCCESS"
    assert receipts_v1.replay_h1_native_receipt_journal_v1(race_handle)[
        "record_count"
    ] == 0

    with pytest.raises(TypeError):
        receipts_v1.PREDECLARED_NATIVE_RESOURCE_SLOTS_V1[0]["normal_ordinal"] = 30
    monkeypatch.setattr(receipts_v1, "PREDECLARED_NATIVE_RESOURCE_SLOTS_V1", ())
    monkeypatch.setattr(receipts_v1, "_SLOTS_BY_KEY", {})
    assert receipts_v1.replay_h1_native_receipt_journal_v1(handle)["slot_count"] == 12


def test_present_and_absent_resolutions_bind_slot_role_attempt_pid_thread_and_no_fd(
    normal_case, receipt_base
):
    spec, handle = _journal(normal_case, receipt_base)
    reuse_base = receipt_base / "observation-reuse"
    reuse_base.mkdir()
    reuse_spec, reuse_handle = _journal(normal_case, reuse_base)
    ofd = spec.payload["predeclared_slots"][0]
    second_ofd = spec.payload["predeclared_slots"][1]
    with pytest.raises(
        receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
        match="exact current normal intent",
    ):
        receipts_v1.execute_h1_native_resource_callback_once_v1(
            handle,
            slot_key=spec.payload["predeclared_slots"][-1]["slot_key"],
            h1_normal_site_intent_id=_id("out-of-order-intent"),
            callback=lambda: _present("PIDFD"),
        )
    assert receipts_v1.replay_h1_native_receipt_journal_v1(handle)[
        "record_count"
    ] == 0
    intent_7 = _advance_to_dangling_intent(normal_case, 7)
    observations = []

    def capture_observation():
        observation = _present(receipts_v1.H1NativeCapabilityKindV1.OFD)
        observations.append(observation)
        return observation

    pending_ofd = receipts_v1.execute_h1_native_resource_callback_once_v1(
        handle,
        slot_key=ofd["slot_key"],
        h1_normal_site_intent_id=intent_7,
        callback=capture_observation,
    )
    state_lock, state_cursor, native_state = receipts_v1._with_locked(handle)
    try:
        with pytest.raises(
            receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
            match="evidence exists after the claimed exact cutoff",
        ):
            receipts_v1._typed_resolution(ofd, native_state, 6)
    finally:
        receipts_v1._unlock(state_lock, state_cursor)
    event_7 = _commit_dangling_success(normal_case)
    receipt_ofd = receipts_v1.bind_h1_native_callback_result_to_normal_event_v1(
        handle,
        pending_result=pending_ofd,
        normal_site_event=event_7,
    )
    intent_9 = _advance_to_dangling_intent(normal_case, 9)
    with pytest.raises(
        receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
        match="issuer-owned typed observation",
    ):
        receipts_v1.execute_h1_native_resource_callback_once_v1(
            reuse_handle,
            slot_key=reuse_spec.payload["predeclared_slots"][1]["slot_key"],
            h1_normal_site_intent_id=intent_9,
            callback=lambda: observations[0],
        )
    assert observations[0]._consumed is True
    assert observations[0]._raw_descriptor is None
    pending_second = receipts_v1.execute_h1_native_resource_callback_once_v1(
        handle,
        slot_key=second_ofd["slot_key"],
        h1_normal_site_intent_id=intent_9,
        callback=lambda: _present(receipts_v1.H1NativeCapabilityKindV1.OFD),
    )
    with pytest.raises(
        receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
        match="crossed",
    ):
        receipts_v1.bind_h1_native_callback_result_to_normal_event_v1(
            handle,
            pending_result=pending_second,
            normal_site_event=event_7,
        )
    event_9 = _commit_dangling_success(normal_case)
    receipt_second = receipts_v1.bind_h1_native_callback_result_to_normal_event_v1(
        handle,
        pending_result=pending_second,
        normal_site_event=event_9,
    )
    document = receipt_ofd.document
    assert document["route_attempt_id"] == spec.payload["route_attempt_id"]
    assert document["slot_key"] == ofd["slot_key"]
    assert document["normal_site_key"] == ofd["normal_site_key"]
    assert document["resource_role"] == "WORKER"
    assert document["broker_role"] == "BROKER"
    assert document["creating_process_id"] == os.getpid()
    assert document["creating_thread_id"] == threading.get_ident()
    assert document["h1_normal_site_intent_id"] == intent_7
    assert document["h1_normal_site_event_commit_id"] == event_7.event_id
    assert document["opaque_capability_identity"] != (
        receipt_second.document["opaque_capability_identity"]
    )
    assert document["callback_result_was_durable_before_normal_event"] is True
    assert document["receipt_created_after_exact_normal_event_binding"] is True
    assert document["native_receipt_before_normal_event_present"] is False
    assert b"987654321" not in canonical_json_bytes(document)
    assert not {"raw_fd", "fd", "descriptor"} & set(_walk_keys(document))
    assert document["real_kernel_credential_authority_present"] is False
    assert document["native_cleanup_authority_present"] is False


def test_explicit_known_absent_is_bound_to_normal_event(normal_case, receipt_base):
    spec, handle = _journal(normal_case, receipt_base)
    slot = spec.payload["predeclared_slots"][0]
    intent = _advance_to_dangling_intent(normal_case, 7)
    with normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        normal_case.handle,
        phase_handle=normal_case.phase,
        rejection_gate=normal_case.gate,
        owner=normal_case.owner,
        bundle=normal_case.bundle,
        dispatch_profile=normal_case.dispatch_profile,
    ):
        with pytest.raises(
            receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
            match="unintegrated normal lease",
        ):
            receipts_v1.execute_h1_native_resource_callback_once_v1(
                handle,
                slot_key=slot["slot_key"],
                h1_normal_site_intent_id=intent,
                callback=lambda: _present("OFD"),
            )
    pending = receipts_v1.execute_h1_native_resource_callback_once_v1(
        handle,
        slot_key=slot["slot_key"],
        h1_normal_site_intent_id=intent,
        callback=lambda: receipts_v1.observe_h1_native_absent_v1(
            capability_kind="OFD", reason="OPEN_FAILED_BEFORE_DESCRIPTOR_CREATION"
        ),
    )
    event = _commit_dangling_success(normal_case)
    resolution = receipts_v1.bind_h1_native_callback_result_to_normal_event_v1(
        handle,
        pending_result=pending,
        normal_site_event=event,
    )
    assert resolution["resolution_kind"] == "KNOWN_ABSENT"
    assert resolution["absence_reason"] == "OPEN_FAILED_BEFORE_DESCRIPTOR_CREATION"
    assert receipts_v1.replay_h1_native_receipt_journal_v1(handle)[
        "slot_resolutions"
    ][slot["slot_key"]] == "KNOWN_ABSENT"


def test_start_without_result_and_callback_return_without_receipt_never_replay(
    normal_case, receipt_base
):
    bases = [receipt_base / f"journal-{index}" for index in range(3)]
    for base in bases:
        base.mkdir()
    journals = [_journal(normal_case, base) for base in bases]
    spec, start_only_handle = journals[0]
    _, callback_only_handle = journals[1]
    _, pending_handle = journals[2]
    first = spec.payload["predeclared_slots"][0]
    intent = _advance_to_dangling_intent(normal_case, 7)
    calls = []
    with pytest.raises(receipts_v1.H1NativeReceiptInjectedCrashV1):
        receipts_v1.execute_h1_native_resource_callback_once_v1(
            start_only_handle,
            slot_key=first["slot_key"],
            h1_normal_site_intent_id=intent,
            callback=lambda: calls.append("forbidden") or _present("OFD"),
            crash_point="AFTER_START_FSYNC",
        )
    assert calls == []
    with pytest.raises(
        receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
        match="replay is forbidden",
    ):
        receipts_v1.execute_h1_native_resource_callback_once_v1(
            start_only_handle,
            slot_key=first["slot_key"],
            h1_normal_site_intent_id=intent,
            callback=lambda: calls.append("replayed") or _present("OFD"),
        )
    with pytest.raises(receipts_v1.H1NativeReceiptInjectedCrashV1):
        receipts_v1.execute_h1_native_resource_callback_once_v1(
            callback_only_handle,
            slot_key=first["slot_key"],
            h1_normal_site_intent_id=intent,
            callback=lambda: _present("OFD"),
            crash_point="AFTER_CALLBACK_BEFORE_RESULT_FSYNC",
        )
    pending = receipts_v1.execute_h1_native_resource_callback_once_v1(
        pending_handle,
        slot_key=first["slot_key"],
        h1_normal_site_intent_id=intent,
        callback=lambda: _present("OFD"),
    )
    assert pending.document["normal_event_binding_status"] == "PENDING"
    failure_event = _commit_dangling_failure(normal_case)
    cutoffs = [
        receipts_v1.freeze_h1_native_cutoff_snapshot_for_v2_transition_v1(
            handle, primary_failure_event=failure_event
        )
        for handle in (start_only_handle, callback_only_handle, pending_handle)
    ]
    for cutoff in cutoffs:
        rows = {
            row["slot_key"]: row for row in cutoff.document["typed_resolutions"]
        }
        assert rows[first["slot_key"]]["resolution_kind"] == "UNRESOLVED"
        assert rows[first["slot_key"]]["native_callback_replay_forbidden"] is True
        assert cutoff.document["known_absent_count"] == 11
        assert cutoff.document["unresolved_count"] == 1
        assert cutoff.document["exact_cutoff_for_v2_transition"] is True
    pending_rows = {
        row["slot_key"]: row for row in cutoffs[-1].document["typed_resolutions"]
    }
    assert pending_rows[first["slot_key"]]["callback_result_id"] == pending.result_id
    assert cutoffs[-1].document["cutoff_exactness_scope"] == (
        "NATIVE_RECEIPT_JOURNAL_PREFIX_ONLY"
    )
    assert cutoffs[-1].document["normal_failure_event_semantic_verification_present"] is False
    assert cutoffs[-1].document["v2_transition_integration_present"] is False
    post_lock, post_cursor, post_state = receipts_v1._with_locked(pending_handle)
    try:
        receipts_v1._append_record_locked(
            pending_handle,
            post_cursor,
            post_state,
            dict(post_state.records[0]),
        )
    finally:
        receipts_v1._unlock(post_lock, post_cursor)
    with pytest.raises(
        receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
        match="continued after its terminal cutoff",
    ):
        receipts_v1.replay_h1_native_receipt_journal_v1(pending_handle)


def test_cross_allocation_pending_result_and_wrong_capability_kind_fail_closed(
    normal_case, receipt_base
):
    other_base = Path(tempfile.mkdtemp(prefix="acfqp-h1-native-receipt-cross-", dir=receipt_base.parent))
    attack_base = Path(tempfile.mkdtemp(prefix="acfqp-h1-native-receipt-attack-", dir=receipt_base.parent))
    resolution_base = Path(tempfile.mkdtemp(prefix="acfqp-h1-native-receipt-resolution-", dir=receipt_base.parent))
    try:
        spec_a, handle_a = _journal(normal_case, receipt_base)
        spec_b, handle_b = _journal(normal_case, other_base)
        _, attack_handle = _journal(normal_case, attack_base)
        _, resolution_handle = _journal(normal_case, resolution_base)
        slot_a = spec_a.payload["predeclared_slots"][0]
        intent = _advance_to_dangling_intent(normal_case, 7)
        pending = receipts_v1.execute_h1_native_resource_callback_once_v1(
            handle_a,
            slot_key=slot_a["slot_key"],
            h1_normal_site_intent_id=intent,
            callback=lambda: _present("OFD"),
        )
        pending_resolution = receipts_v1.execute_h1_native_resource_callback_once_v1(
            resolution_handle,
            slot_key=slot_a["slot_key"],
            h1_normal_site_intent_id=intent,
            callback=lambda: _present("OFD"),
        )
        source_lock, source_cursor, source_state = receipts_v1._with_locked(handle_a)
        try:
            crossed_start = dict(source_state.records[0])
        finally:
            receipts_v1._unlock(source_lock, source_cursor)
        attack_lock, attack_cursor, attack_state = receipts_v1._with_locked(
            attack_handle
        )
        try:
            receipts_v1._append_record_locked(
                attack_handle, attack_cursor, attack_state, crossed_start
            )
        finally:
            receipts_v1._unlock(attack_lock, attack_cursor)
        with pytest.raises(
            receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
            match="frozen context",
        ):
            receipts_v1.replay_h1_native_receipt_journal_v1(attack_handle)
        slot_b = spec_b.payload["predeclared_slots"][0]
        with pytest.raises(
            receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
            match="capability kind crossed",
        ):
            receipts_v1.execute_h1_native_resource_callback_once_v1(
                handle_b,
                slot_key=slot_b["slot_key"],
                h1_normal_site_intent_id=intent,
                callback=lambda: _present("PIDFD"),
            )
        event = _commit_dangling_success(normal_case)
        with pytest.raises(
            receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
            match="crossed",
        ):
            receipts_v1.bind_h1_native_callback_result_to_normal_event_v1(
                handle_b,
                pending_result=pending,
                normal_site_event=event,
            )
        valid_receipt = receipts_v1.bind_h1_native_callback_result_to_normal_event_v1(
            handle_a,
            pending_result=pending,
            normal_site_event=event,
        )
        forged_receipt = dict(valid_receipt.document)
        forged_receipt.update(
            {
                "h1_native_receipt_journal_spec_id": resolution_handle.spec.spec_id,
                "h1_native_receipt_allocation_id": resolution_handle.allocation_id,
                "h1_normal_site_event_commit_id": _id("forged-normal-event"),
                "h1_native_callback_start_id": pending_resolution.document[
                    "h1_native_callback_start_id"
                ],
                "h1_native_callback_result_id": pending_resolution.result_id,
                "opaque_capability_identity": pending_resolution.document[
                    "opaque_capability_identity"
                ],
            }
        )
        forged_receipt.pop("h1_native_resource_receipt_id")
        forged_receipt["h1_native_resource_receipt_id"] = receipts_v1._content_id(
            receipts_v1.RECEIPT_DOMAIN, forged_receipt
        )
        resolution_lock, resolution_cursor, resolution_state = (
            receipts_v1._with_locked(resolution_handle)
        )
        try:
            receipts_v1._append_record_locked(
                resolution_handle,
                resolution_cursor,
                resolution_state,
                forged_receipt,
            )
        finally:
            receipts_v1._unlock(resolution_lock, resolution_cursor)
        with pytest.raises(
            receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
            match="exact normal event",
        ):
            receipts_v1.replay_h1_native_receipt_journal_v1(resolution_handle)
        forge_lock, forge_cursor, forge_state = receipts_v1._with_locked(handle_b)
        try:
            start_b = forge_state.starts[slot_b["slot_key"]]
            forged_result = dict(pending.document)
            forged_result.update(
                {
                    "h1_native_receipt_journal_spec_id": handle_b.spec.spec_id,
                    "h1_native_receipt_allocation_id": handle_b.allocation_id,
                    "h1_native_callback_start_id": start_b[
                        "h1_native_callback_start_id"
                    ],
                    "callback_cell_nonce_commitment": start_b[
                        "callback_cell_nonce_commitment"
                    ],
                    "resolution_kind": "KNOWN_ABSENT",
                }
            )
            forged_result.pop("h1_native_callback_result_id")
            forged_result["h1_native_callback_result_id"] = receipts_v1._content_id(
                receipts_v1.RESULT_DOMAIN, forged_result
            )
            receipts_v1._append_record_locked(
                handle_b, forge_cursor, forge_state, forged_result
            )
        finally:
            receipts_v1._unlock(forge_lock, forge_cursor)
        with pytest.raises(
            receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
            match="absent native callback result",
        ):
            receipts_v1.replay_h1_native_receipt_journal_v1(handle_b)
    finally:
        shutil.rmtree(other_base)
        shutil.rmtree(attack_base)
        shutil.rmtree(resolution_base)


def test_foreign_thread_and_fork_cannot_issue_broker_receipts(normal_case, receipt_base):
    dead_broker_base = receipt_base / "dead-broker"
    dead_broker_base.mkdir()
    dead_broker_spec = receipts_v1.freeze_h1_native_receipt_journal_spec_v1(
        dead_broker_base, normal_handle=normal_case.handle
    )
    dead_read, dead_write = os.pipe()
    dead_child = os.fork()
    if dead_child == 0:  # pragma: no cover - asserted through parent pipe
        os.close(dead_read)
        try:
            receipts_v1.initialize_h1_native_receipt_journal_v1(
                dead_broker_spec,
                normal_handle=normal_case.handle,
                crash_point="AFTER_ALLOCATION_PUBLISH",
            )
        except BaseException as error:
            os.write(dead_write, type(error).__name__.encode("ascii"))
        finally:
            os.close(dead_write)
        os._exit(0)
    os.close(dead_write)
    dead_result = os.read(dead_read, 4096).decode("ascii")
    os.close(dead_read)
    os.waitpid(dead_child, 0)
    assert dead_result == "H1NativeReceiptInjectedCrashV1"
    with pytest.raises(
        receipts_v1.H1NativeForkedCallbackContinuationV1,
        match="cannot write recovery state",
    ):
        receipts_v1.initialize_h1_native_receipt_journal_v1(
            dead_broker_spec, normal_handle=normal_case.handle
        )
    dead_root = dead_broker_base / receipts_v1._ROOT_NAME
    dead_attempt = dead_root / receipts_v1._attempt_name(
        dead_broker_spec.payload["route_attempt_id"]
    )
    assert not (dead_attempt / receipts_v1._INITIALIZATION_COMPLETE_FILE).exists()
    assert not (
        dead_root
        / f"{receipts_v1._ROOT_SEAL_PREFIX}{dead_broker_spec.payload['route_attempt_id']}"
    ).exists()
    assert not (
        dead_root
        / f"{receipts_v1._ALLOCATION_SEAL_PREFIX}{dead_broker_spec.payload['route_attempt_id']}"
    ).exists()
    assert not (
        dead_root
        / f"{receipts_v1._CURSOR_SEAL_PREFIX}{dead_broker_spec.payload['route_attempt_id']}"
    ).exists()

    spec, handle = _journal(normal_case, receipt_base)
    slot = spec.payload["predeclared_slots"][0]
    intent = _advance_to_dangling_intent(normal_case, 7)
    outcomes: queue.Queue[BaseException | None] = queue.Queue()

    def foreign_thread():
        try:
            receipts_v1.execute_h1_native_resource_callback_once_v1(
                handle,
                slot_key=slot["slot_key"],
                h1_normal_site_intent_id=intent,
                callback=lambda: _present("OFD"),
            )
        except BaseException as error:
            outcomes.put(error)
        else:  # pragma: no cover - fail-closed assertion
            outcomes.put(None)

    thread = threading.Thread(target=foreign_thread)
    thread.start()
    thread.join()
    assert isinstance(
        outcomes.get_nowait(), receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error
    )

    read_fd, write_fd = os.pipe()
    child = os.fork()
    if child == 0:  # pragma: no cover - asserted through parent pipe
        os.close(read_fd)
        try:
            receipts_v1.execute_h1_native_resource_callback_once_v1(
                handle,
                slot_key=slot["slot_key"],
                h1_normal_site_intent_id=intent,
                callback=lambda: _present("OFD"),
            )
        except BaseException as error:
            os.write(write_fd, type(error).__name__.encode("ascii"))
        finally:
            os.close(write_fd)
        os._exit(0)
    os.close(write_fd)
    child_result = os.read(read_fd, 4096).decode("ascii")
    os.close(read_fd)
    os.waitpid(child, 0)
    assert child_result == "H1NativeForkedCallbackContinuationV1"
    assert receipts_v1.replay_h1_native_receipt_journal_v1(handle)["record_count"] == 0

    fork_observation = []

    def callback_that_forks():
        child_read, child_write = os.pipe()
        callback_child = os.fork()
        if callback_child == 0:  # pragma: no cover - asserted through parent pipe
            os.close(child_read)
            try:
                receipts_v1.observe_h1_native_absent_v1(
                    capability_kind="OFD", reason="FORKED_CALLBACK"
                )
            except BaseException as error:
                os.write(child_write, type(error).__name__.encode("ascii"))
            finally:
                os.close(child_write)
            os._exit(0)
        os.close(child_write)
        fork_observation.append(os.read(child_read, 4096).decode("ascii"))
        os.close(child_read)
        os.waitpid(callback_child, 0)
        return _present("OFD")

    pending = receipts_v1.execute_h1_native_resource_callback_once_v1(
        handle,
        slot_key=slot["slot_key"],
        h1_normal_site_intent_id=intent,
        callback=callback_that_forks,
    )
    assert pending.document["normal_event_binding_status"] == "PENDING"
    assert fork_observation == ["H1NativeForkedCallbackContinuationV1"]
    assert receipts_v1.replay_h1_native_receipt_journal_v1(handle)["record_count"] == 2


def test_cursor_strict_prefix_recovers_but_record_rollback_and_seal_attack_fail(
    normal_case, receipt_base
):
    spec, handle = _journal(normal_case, receipt_base)
    slot = spec.payload["predeclared_slots"][0]
    intent = _advance_to_dangling_intent(normal_case, 7)
    receipts_v1.execute_h1_native_resource_callback_once_v1(
        handle,
        slot_key=slot["slot_key"],
        h1_normal_site_intent_id=intent,
        callback=lambda: _present("OFD"),
    )
    cursor = handle.attempt_directory / "journal.cursor"
    lines = cursor.read_bytes().splitlines(keepends=True)
    cursor.write_bytes(b"".join(lines[:-1]))
    assert receipts_v1.replay_h1_native_receipt_journal_v1(handle)["record_count"] == 2
    assert len(cursor.read_bytes().splitlines()) == 3
    complete_cursor = cursor.read_bytes()
    cursor.write_bytes(complete_cursor[:-7])
    assert receipts_v1.replay_h1_native_receipt_journal_v1(handle)["record_count"] == 2
    assert cursor.read_bytes() == complete_cursor

    journal_lock = handle.attempt_directory / "journal.lock"
    lock_backup = receipt_base / "journal-lock-backup"
    os.link(journal_lock, lock_backup)
    journal_lock.unlink()
    replacement_fd = os.open(journal_lock, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(replacement_fd)
    with pytest.raises(
        receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
        match="lock identity changed",
    ):
        receipts_v1.replay_h1_native_receipt_journal_v1(handle)
    journal_lock.unlink()
    lock_backup.rename(journal_lock)
    assert receipts_v1.replay_h1_native_receipt_journal_v1(handle)["record_count"] == 2

    extra_link = receipt_base / "foreign-hardlink"
    os.link(handle.attempt_directory / "root-anchor.json", extra_link)
    with pytest.raises(
        receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
        match="seal changed",
    ):
        receipts_v1.replay_h1_native_receipt_journal_v1(handle)
    extra_link.unlink()
    assert receipts_v1.replay_h1_native_receipt_journal_v1(handle)["record_count"] == 2

    records = sorted(handle.attempt_directory.glob("record-*.json"))
    record_link = receipt_base / "foreign-record-hardlink"
    os.link(records[0], record_link)
    with pytest.raises(
        receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
        match="record type, mode, or link count changed",
    ):
        receipts_v1.replay_h1_native_receipt_journal_v1(handle)
    record_link.unlink()
    assert receipts_v1.replay_h1_native_receipt_journal_v1(handle)["record_count"] == 2

    records[-1].unlink()
    cursor.write_bytes(lines[0])
    with pytest.raises(
        receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
        match="high-water",
    ):
        receipts_v1.replay_h1_native_receipt_journal_v1(handle)


def test_registry_and_public_claim_boundary_are_exact():
    slots = receipts_v1.PREDECLARED_NATIVE_RESOURCE_SLOTS_V1
    assert len({row["h1_native_resource_slot_id"] for row in slots}) == 12
    assert receipts_v1.REAL_KERNEL_CREDENTIAL_AUTHORITY_PRESENT is False
    assert receipts_v1.NATIVE_CLEANUP_AUTHORITY_PRESENT is False
    assert receipts_v1.NATIVE_CALLBACK_RESULT_BEFORE_NORMAL_EVENT_PRESENT is True
    assert receipts_v1.NATIVE_RECEIPT_BEFORE_NORMAL_EVENT_PRESENT is False
    assert receipts_v1.SAME_BROKER_INITIALIZATION_CONVERGENCE_PRESENT is True
    assert receipts_v1.CROSS_PROCESS_INITIALIZATION_RECOVERY_PRESENT is False
    assert receipts_v1.CURRENT_ACCESS_AUTHORITY_PRESENT is False
    assert receipts_v1.PRODUCTION_EXECUTION_AUTHORITY_PRESENT is False
    assert receipts_v1.NORMAL_FAILURE_EVENT_SEMANTIC_VERIFICATION_PRESENT is False
    assert receipts_v1.V2_TRANSITION_INTEGRATION_PRESENT is False
    assert receipts_v1.FORMAL_COUNTER_RECORDS_ISSUED is False
    assert receipts_v1.FORMAL_WORK_VECTOR_ISSUED is False
    assert receipts_v1.FORMAL_COMPARISON_VECTOR_ISSUED is False
    assert receipts_v1.FORMAL_V7_ROUTE_AUTHORITY_PRESENT is False
    assert receipts_v1.OFFICIAL_EXECUTION_ALLOWED is False
