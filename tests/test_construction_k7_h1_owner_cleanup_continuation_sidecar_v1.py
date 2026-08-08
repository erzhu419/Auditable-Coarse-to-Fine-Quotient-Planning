from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import tempfile

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as output_join_v1
from acfqp import construction_k7_h1_owner_cleanup_continuation_sidecar_v1 as sidecar_v1
from acfqp import construction_k7_h1_phase_aware_normal_prefix_v1 as normal_v1
from acfqp import construction_k7_h1_preadmitted_cleanup_transition_v2 as cleanup_v2
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4

from test_construction_k7_h1_phase_aware_normal_prefix_v1 import (
    _build_case,
    _callback_for,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANCHOR_ID = (
    "4a4b0d1888f0ac18123e4163e1a26b0583a64946d2eb219e02d4b77dc0a3e327"
)


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
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-owner-cleanup-", dir=base))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _normal_lease(case, bundle):
    return normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        case.normal,
        phase_handle=case.phase,
        rejection_gate=case.gate,
        owner=case.owner,
        bundle=bundle,
        dispatch_profile=case.dispatch_profile,
    )


def _boom():
    raise RuntimeError("registered cleanup-sidecar failure")


def _prepare(case, bundle, analysis, *, failed_ordinal: int):
    with _normal_lease(case, bundle) as lease:
        envelope = cleanup_v2.preadmit_h1_normal_prefix_cleanup_envelope_v2(
            lease, cleanup_analysis=analysis
        )
    for row in bundle.program.transitions[: failed_ordinal - 1]:
        with _normal_lease(case, bundle) as lease:
            event = normal_v1.execute_next_h1_phase_aware_normal_site_v1(
                lease, callback=_callback_for(row)
            )
        assert event.outcome == "SUCCESS"
    with _normal_lease(case, bundle) as lease:
        boundary = cleanup_v2.execute_next_h1_normal_site_to_cleanup_boundary_v2(
            lease,
            cleanup_analysis=analysis,
            envelope=envelope,
            callback=_boom,
        )
    assert type(boundary) is cleanup_v2.H1NormalFailureCleanupBoundaryV2
    cleanup_pass = cleanup_v1.bind_h1_lifecycle_cleanup_pass_v1(
        analysis, branch_key=boundary.transition.payload["branch_key"]
    )
    return envelope, boundary.transition, cleanup_pass


def _action(cleanup_pass, kind):
    rows = [
        row
        for row in cleanup_pass.payload["planned_cleanup_actions"]
        if row["action_kind"] == kind
    ]
    assert len(rows) == 1
    return rows[0]


def _reservation(case, site_key):
    index = owner_v3.inspect_h1_shared_cap_owner_v3_record_index(case.owner.owner)
    rows = [
        row
        for row in index["records_by_role"]["reservation"]
        if row["site_key"] == site_key
    ]
    assert len(rows) == 1
    return rows[0]


def _owner_tree_digest(case):
    root = Path(case.owner.owner.owner_root_realpath)
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append(
                (
                    str(path.relative_to(root)),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
            )
    return rows


@pytest.mark.parametrize(
    "failed_ordinal,action_kind,site_key,path,reducer",
    [
        (
            2,
            "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ",
            "memory:bind-working-hierarchy",
            "memory.working_bytes_peak",
            "MAX",
        ),
        (
            6,
            "SETTLE_OUTPUT_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_FINALIZE",
            "output:reserve-route-wide",
            "io.output_bytes",
            "SUM",
        ),
    ],
)
def test_memory_and_output_release_are_sidecar_only_single_spends(
    fast_root,
    bundle,
    analysis,
    failed_ordinal,
    action_kind,
    site_key,
    path,
    reducer,
):
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        suffix=f"release-{failed_ordinal}",
    )
    envelope, transition, cleanup_pass = _prepare(
        case, bundle, analysis, failed_ordinal=failed_ordinal
    )
    action = _action(cleanup_pass, action_kind)
    reservation = _reservation(case, site_key)
    owner_before = _owner_tree_digest(case)
    replay_before = owner_v4.replay_h1_shared_cap_owner_v4_wal(case.owner)
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        context = sidecar_v1.validate_h1_owner_cleanup_context_with_retained_lease_v1(
            cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
            reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
        )
        handle = sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
            fast_root,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
            reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
        )
        release = sidecar_v1.conservatively_release_h1_owner_cleanup_reservation_v1(
            handle,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
        combined = sidecar_v1.verify_h1_owner_cleanup_combined_state_v1(
            handle,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
    assert context["retained_phase_gate_owner_validation_complete"] is True
    assert release.payload["sidecar_operation"] == (
        "CONSERVATIVE_RELEASE_WITHOUT_NATIVE_START"
    )
    assert release.payload["native_observed_value"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "NATIVE_EFFECT_NOT_STARTED",
    }
    assert release.payload["charged_value"] == reservation["reservation_upper"]
    assert release.payload["reducer"] == reducer
    assert release.payload["charged_after"] == (
        release.payload["charged_before"] + reservation["reservation_upper"]
        if reducer == "SUM"
        else max(
            release.payload["charged_before"], reservation["reservation_upper"]
        )
    )
    assert release.payload["native_effect_started"] is False
    assert release.payload["memory_read_performed"] is False
    assert release.payload["output_finalize_performed"] is False
    assert combined["sidecar_release_count"] == 1
    assert combined["sidecar_single_spend_verified"] is True
    assert combined["combined_outstanding_values"][path] == (
        combined["v3_outstanding_values"][path] - reservation["reservation_upper"]
    )
    assert owner_before == _owner_tree_digest(case)
    assert replay_before == owner_v4.replay_h1_shared_cap_owner_v4_wal(case.owner)
    assert combined["formal_counter_records_issued"] is False
    assert combined["production_execution_authority_present"] is False
    assert combined["official_execution_allowed"] is False


def test_phase_base_is_the_only_storage_root_for_one_reservation(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="unique-base")
    envelope, transition, cleanup_pass = _prepare(
        case, bundle, analysis, failed_ordinal=2
    )
    action = _action(
        cleanup_pass,
        "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ",
    )
    reservation = _reservation(case, "memory:bind-working-hierarchy")
    alternate = fast_root / "cross-root"
    alternate.mkdir(mode=0o700)
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        with pytest.raises(
            sidecar_v1.ConstructionK7H1OwnerCleanupContinuationSidecarV1Error,
            match="unique phase-spec base",
        ):
            sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
                alternate,
                cleanup_lease=cleanup_lease,
                owner=case.owner,
                transition=transition,
                envelope=envelope,
                cleanup_pass=cleanup_pass,
                action=action,
                reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
            )
        assert not (alternate / sidecar_v1._ROOT_NAME).exists()
        handle = sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
            fast_root,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
            reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
        )
    assert Path(handle.root_directory).parent == fast_root.resolve()


def test_repairable_v4_payload_is_rejected_without_preflight_mutation(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="pending-preflight")
    envelope, transition, cleanup_pass = _prepare(
        case, bundle, analysis, failed_ordinal=2
    )
    action = _action(
        cleanup_pass,
        "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ",
    )
    reservation = _reservation(case, "memory:bind-working-hierarchy")
    sequence = transition.payload["owner_tail_sequence_at_transition"]
    head = transition.payload["owner_tail_head_id_at_transition"]
    source = Path(case.owner.owner_directory) / f"{sequence:08d}-{head}.json"
    pending = Path(case.owner.owner.pending_payload_wal_directory) / (
        f"pending-{sequence:08d}-{head}.json"
    )
    pending.write_bytes(source.read_bytes())
    pending.chmod(0o600)
    before = _owner_tree_digest(case)
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        with pytest.raises(
            sidecar_v1.ConstructionK7H1OwnerCleanupContinuationSidecarV1Error,
            match="repairable V4 WAL payload",
        ):
            sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
                fast_root,
                cleanup_lease=cleanup_lease,
                owner=case.owner,
                transition=transition,
                envelope=envelope,
                cleanup_pass=cleanup_pass,
                action=action,
                reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
            )
    assert pending.exists()
    assert _owner_tree_digest(case) == before


@pytest.mark.parametrize(
    "crash_point",
    [
        sidecar_v1.H1OwnerCleanupSidecarCrashPointV1.AFTER_RELEASE_FSYNC,
        sidecar_v1.H1OwnerCleanupSidecarCrashPointV1.AFTER_ROOT_SEAL_FSYNC,
        sidecar_v1.H1OwnerCleanupSidecarCrashPointV1.AFTER_CURSOR_FSYNC,
    ],
)
def test_release_crash_boundaries_recover_without_owner_mutation(
    fast_root, bundle, analysis, crash_point
):
    suffix = "crash-" + hashlib.sha256(crash_point.value.encode()).hexdigest()[:8]
    case = _build_case(fast_root, bundle, analysis, suffix=suffix)
    envelope, transition, cleanup_pass = _prepare(
        case, bundle, analysis, failed_ordinal=2
    )
    action = _action(
        cleanup_pass,
        "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ",
    )
    reservation = _reservation(case, "memory:bind-working-hierarchy")
    owner_before = _owner_tree_digest(case)
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        handle = sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
            fast_root,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
            reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
        )
        with pytest.raises(sidecar_v1.H1OwnerCleanupSidecarInjectedCrashV1):
            sidecar_v1.conservatively_release_h1_owner_cleanup_reservation_v1(
                handle,
                cleanup_lease=cleanup_lease,
                owner=case.owner,
                transition=transition,
                envelope=envelope,
                cleanup_pass=cleanup_pass,
                action=action,
                crash_point=crash_point,
            )
        allocation_id = handle.allocation_id
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        reopened = sidecar_v1.open_h1_owner_cleanup_continuation_sidecar_v1(
            fast_root,
            expected_allocation_id=allocation_id,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
            reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
        )
        recovered = (
            sidecar_v1.conservatively_release_h1_owner_cleanup_reservation_v1(
                reopened,
                cleanup_lease=cleanup_lease,
                owner=case.owner,
                transition=transition,
                envelope=envelope,
                cleanup_pass=cleanup_pass,
                action=action,
            )
        )
        combined = sidecar_v1.verify_h1_owner_cleanup_combined_state_v1(
            reopened,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
    assert recovered.release_id == combined["h1_owner_cleanup_release_id"]
    assert combined["sidecar_release_count"] == 1
    assert owner_before == _owner_tree_digest(case)


def test_torn_cursor_repairs_only_the_unique_verified_commit_prefix(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="torn-cursor")
    envelope, transition, cleanup_pass = _prepare(
        case, bundle, analysis, failed_ordinal=2
    )
    action = _action(
        cleanup_pass,
        "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ",
    )
    reservation = _reservation(case, "memory:bind-working-hierarchy")
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        handle = sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
            fast_root,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
            reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
        )
        with pytest.raises(sidecar_v1.H1OwnerCleanupSidecarInjectedCrashV1):
            sidecar_v1.conservatively_release_h1_owner_cleanup_reservation_v1(
                handle,
                cleanup_lease=cleanup_lease,
                owner=case.owner,
                transition=transition,
                envelope=envelope,
                cleanup_pass=cleanup_pass,
                action=action,
                crash_point=(
                    sidecar_v1.H1OwnerCleanupSidecarCrashPointV1.AFTER_RELEASE_FSYNC
                ),
            )
        allocation_id = handle.allocation_id
    cursor_path = Path(handle.sidecar_directory, "cursor.jsonl")
    genesis = cursor_path.read_bytes()
    with cursor_path.open("ab") as stream:
        stream.write(b'{"crossed":')
        stream.flush()
        os.fsync(stream.fileno())
    crossed = cursor_path.read_bytes()
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        with pytest.raises(
            sidecar_v1.ConstructionK7H1OwnerCleanupContinuationSidecarV1Error,
            match="unique expected commit",
        ):
            sidecar_v1.open_h1_owner_cleanup_continuation_sidecar_v1(
                fast_root,
                expected_allocation_id=allocation_id,
                cleanup_lease=cleanup_lease,
                owner=case.owner,
                transition=transition,
                envelope=envelope,
                cleanup_pass=cleanup_pass,
                action=action,
                reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
            )
    assert cursor_path.read_bytes() == crossed
    cursor_path.write_bytes(genesis)
    release = sidecar_v1._release_from_raw(
        Path(handle.sidecar_directory, "release.json").read_bytes()
    )
    genesis_document = sidecar_v1.loads_canonical_json(genesis.splitlines()[0])
    commit = sidecar_v1._cursor_document(
        sidecar_v1._cursor_payload(
            allocation_id,
            sequence=1,
            previous_cursor_id=genesis_document[
                "h1_owner_cleanup_cursor_record_id"
            ],
            state="RELEASE_COMMITTED",
            release_id=release.release_id,
        )
    )
    commit_line = sidecar_v1.canonical_json_bytes(commit) + b"\n"
    prefix = commit_line[: len(commit_line) // 2]
    with cursor_path.open("ab") as stream:
        stream.write(prefix)
        stream.flush()
        os.fsync(stream.fileno())
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        reopened = sidecar_v1.open_h1_owner_cleanup_continuation_sidecar_v1(
            fast_root,
            expected_allocation_id=allocation_id,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
            reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
        )
    assert reopened.allocation_id == allocation_id
    assert len(cursor_path.read_bytes().splitlines()) == 2


def test_duplicate_release_is_idempotent_and_crossed_reservation_is_rejected(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="duplicate")
    envelope, transition, cleanup_pass = _prepare(
        case, bundle, analysis, failed_ordinal=6
    )
    action = _action(
        cleanup_pass,
        "SETTLE_OUTPUT_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_FINALIZE",
    )
    reservation = _reservation(case, "output:reserve-route-wide")
    memory = _reservation(case, "memory:bind-working-hierarchy")
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        with pytest.raises(
            sidecar_v1.ConstructionK7H1OwnerCleanupContinuationSidecarV1Error,
            match="deferred-origin reservation",
        ):
            sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
                fast_root,
                cleanup_lease=cleanup_lease,
                owner=case.owner,
                transition=transition,
                envelope=envelope,
                cleanup_pass=cleanup_pass,
                action=action,
                reservation_id=memory["h1_shared_cap_owner_v3_reservation_id"],
            )
        handle = sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
            fast_root,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
            reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
        )
        first = sidecar_v1.conservatively_release_h1_owner_cleanup_reservation_v1(
            handle,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
        second = sidecar_v1.conservatively_release_h1_owner_cleanup_reservation_v1(
            handle,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
        combined = sidecar_v1.verify_h1_owner_cleanup_combined_state_v1(
            handle,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
    assert first.release_id == second.release_id
    assert combined["sidecar_release_count"] == 1
    cursor = Path(handle.sidecar_directory, "cursor.jsonl").read_bytes()
    assert len(cursor.splitlines()) == 2


def test_allocation_and_release_root_seals_recover_but_cursor_inode_is_immutable(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="seal-recovery")
    envelope, transition, cleanup_pass = _prepare(
        case, bundle, analysis, failed_ordinal=2
    )
    action = _action(
        cleanup_pass,
        "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ",
    )
    reservation = _reservation(case, "memory:bind-working-hierarchy")
    owner_before = _owner_tree_digest(case)
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        handle = sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
            fast_root,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
            reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
        )
        sidecar_v1.conservatively_release_h1_owner_cleanup_reservation_v1(
            handle,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
        allocation_id = handle.allocation_id
    Path(handle.sidecar_directory, "allocation.json").unlink()
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        reopened = sidecar_v1.open_h1_owner_cleanup_continuation_sidecar_v1(
            fast_root,
            expected_allocation_id=allocation_id,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
            reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
        )
        assert Path(reopened.sidecar_directory, "allocation.json").exists()
        Path(reopened.sidecar_directory, "release.json").unlink()
        combined = sidecar_v1.verify_h1_owner_cleanup_combined_state_v1(
            reopened,
            cleanup_lease=cleanup_lease,
            owner=case.owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
        assert combined["sidecar_release_count"] == 1

        def replace_and_restore(path: Path, expected_match: str) -> None:
            backup = path.with_name(path.name + ".attack-backup")
            raw = path.read_bytes()
            path.rename(backup)
            path.write_bytes(raw)
            path.chmod(backup.stat().st_mode & 0o777)
            try:
                with pytest.raises(
                    sidecar_v1.ConstructionK7H1OwnerCleanupContinuationSidecarV1Error,
                    match=expected_match,
                ):
                    sidecar_v1.verify_h1_owner_cleanup_combined_state_v1(
                        reopened,
                        cleanup_lease=cleanup_lease,
                        owner=case.owner,
                        transition=transition,
                        envelope=envelope,
                        cleanup_pass=cleanup_pass,
                        action=action,
                    )
            finally:
                path.unlink()
                backup.rename(path)

        replace_and_restore(
            Path(reopened.sidecar_directory, "sidecar.lock"), "sidecar lock inode"
        )
        replace_and_restore(
            Path(reopened.root_directory, "allocation.lock"),
            "root allocation lock inode",
        )
        replace_and_restore(
            Path(reopened.root_directory)
            / sidecar_v1._allocation_seal_name(reopened.spec),
            "allocation/root seal",
        )
        replace_and_restore(
            Path(reopened.root_directory)
            / sidecar_v1._release_seal_name(reopened.spec),
            "release/root seal",
        )
        cursor_path = Path(reopened.sidecar_directory, "cursor.jsonl")
        cursor_raw = cursor_path.read_bytes()
        cursor_path.unlink()
        cursor_path.write_bytes(cursor_raw)
        cursor_path.chmod(0o600)
        with pytest.raises(
            sidecar_v1.ConstructionK7H1OwnerCleanupContinuationSidecarV1Error,
            match="cursor inode",
        ):
            sidecar_v1.verify_h1_owner_cleanup_combined_state_v1(
                reopened,
                cleanup_lease=cleanup_lease,
                owner=case.owner,
                transition=transition,
                envelope=envelope,
                cleanup_pass=cleanup_pass,
                action=action,
            )
        root_path = Path(reopened.root_directory)
        root_backup = root_path.with_name(root_path.name + ".inode-attack")
        root_path.rename(root_backup)
        root_path.mkdir(mode=0o700)
        try:
            with pytest.raises(
                sidecar_v1.ConstructionK7H1OwnerCleanupContinuationSidecarV1Error,
                match="root inode",
            ):
                sidecar_v1.verify_h1_owner_cleanup_combined_state_v1(
                    reopened,
                    cleanup_lease=cleanup_lease,
                    owner=case.owner,
                    transition=transition,
                    envelope=envelope,
                    cleanup_pass=cleanup_pass,
                    action=action,
                )
        finally:
            root_path.rmdir()
            root_backup.rename(root_path)
    assert owner_before == _owner_tree_digest(case)


def test_foreign_transition_and_owner_gate_context_fail_closed(
    fast_root, bundle, analysis
):
    left = _build_case(fast_root, bundle, analysis, suffix="context-left")
    right = _build_case(fast_root, bundle, analysis, suffix="context-right")
    left_env, left_transition, left_pass = _prepare(
        left, bundle, analysis, failed_ordinal=2
    )
    right_env, right_transition, _right_pass = _prepare(
        right, bundle, analysis, failed_ordinal=2
    )
    action = _action(
        left_pass,
        "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ",
    )
    reservation = _reservation(left, "memory:bind-working-hierarchy")
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        left.phase,
        rejection_gate=left.gate,
        expected_transition_id=left_transition.transition_id,
    ) as cleanup_lease:
        with pytest.raises(
            cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error
        ):
            sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
                fast_root,
                cleanup_lease=cleanup_lease,
                owner=left.owner,
                transition=right_transition,
                envelope=right_env,
                cleanup_pass=left_pass,
                action=action,
                reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
            )
        with pytest.raises(
            sidecar_v1.ConstructionK7H1OwnerCleanupContinuationSidecarV1Error,
            match="identities crossed",
        ):
            sidecar_v1.initialize_h1_owner_cleanup_continuation_sidecar_v1(
                fast_root,
                cleanup_lease=cleanup_lease,
                owner=right.owner,
                transition=left_transition,
                envelope=left_env,
                cleanup_pass=left_pass,
                action=action,
                reservation_id=reservation["h1_shared_cap_owner_v3_reservation_id"],
            )


def test_ensure_regular_file_closes_descriptor_on_initial_write_failure(
    fast_root, monkeypatch
):
    directory = fast_root / "fd-close"
    directory.mkdir(mode=0o700)
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    before = len(os.listdir("/proc/self/fd"))

    def fail_write(_descriptor, _raw):
        raise RuntimeError("injected initial write failure")

    monkeypatch.setattr(sidecar_v1, "_write_all", fail_write)
    try:
        with pytest.raises(RuntimeError, match="initial write failure"):
            sidecar_v1._ensure_regular_file(
                directory_fd, "mutable.bin", initial=b"one byte"
            )
        assert len(os.listdir("/proc/self/fd")) == before
    finally:
        os.close(directory_fd)
