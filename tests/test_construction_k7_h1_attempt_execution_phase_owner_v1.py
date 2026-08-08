from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import pickle
import shutil
import tempfile
import threading
import time

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_attempt_execution_phase_owner_v1 as phase_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_domain_registry_extension_v2 as domains_v2
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as output_join_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4
from acfqp import construction_k7_h1_tail_bound_prefix_attestation_v1 as tail_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANCHOR_ID = (
    "4a4b0d1888f0ac18123e4163e1a26b0583a64946d2eb219e02d4b77dc0a3e327"
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _raise_runtime_error() -> None:
    raise RuntimeError("registered test failure")


@pytest.fixture(scope="module")
def bundle():
    return dispatch_v1.freeze_h1_anchored_lifecycle_dispatch_bundle_v1(
        REPOSITORY_ROOT,
        expected_anchor_id=EXPECTED_ANCHOR_ID,
    )


@pytest.fixture(scope="module")
def analysis(bundle):
    output_join = output_join_v1.build_h1_lifecycle_output_leaf_join_v1(bundle)
    return cleanup_v1.derive_h1_lifecycle_complete_branch_analysis_v1(
        bundle,
        output_join,
    )


@pytest.fixture(scope="module")
def semantic_closure():
    return tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()


@pytest.fixture
def fast_root() -> Path:
    base = "/dev/shm" if Path("/dev/shm").is_dir() else "/tmp"
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-attempt-phase-", dir=base))
    try:
        yield path
    finally:
        shutil.rmtree(path)


@dataclass(frozen=True)
class _Case:
    profile: owner_v3.H1SharedCapProfileCoreV3
    gate: rejection_v1.H1AttemptRejectionGateHandleV1
    owner: owner_v4.H1SharedCapOwnerV4WalHandle
    dispatch_profile: dispatch_v1.H1LifecycleDispatchProfileV1
    trace_bytes: bytes
    attestation: tail_v1.H1TailBoundPrefixAttestationV1
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1
    phase_spec: phase_v1.H1AttemptExecutionPhaseSpecV1
    phase: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle


def _build_case(
    root: Path,
    bundle,
    analysis,
    semantic_closure,
    *,
    suffix: str,
) -> _Case:
    profile = owner_v3.freeze_h1_shared_cap_profile_core_v3(
        logical_occurrence_id=_id(f"occurrence-{suffix}"),
        route_attempt_id=_id(f"attempt-{suffix}"),
        decision_point_id=_id(f"decision-{suffix}"),
        transaction_id=_id(f"transaction-{suffix}"),
        caller_pinned_lifecycle_provenance_id=bundle.program.provenance_id,
        lifecycle_program_snapshot_id=bundle.program.snapshot_id,
        lifecycle_program_id=bundle.program.program_id,
        lifecycle_branch_analysis_id=bundle.program.branch_analysis_id,
        hard_caps={path: 100_000 for path in owner_v3.SHARED_RESOURCE_PATHS},
    )
    source = owner_v3.freeze_h1_shared_cap_owner_v3_source_manifest(
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
        lifecycle_program_snapshot_id=profile.lifecycle_program_snapshot_id,
        lifecycle_program_id=profile.lifecycle_program_id,
        lifecycle_branch_analysis_id=profile.lifecycle_branch_analysis_id,
    )
    gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=root,
        logical_occurrence_id=profile.logical_occurrence_id,
        route_attempt_id=profile.route_attempt_id,
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
    )
    gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(root, gate_spec)
    historical_owner = owner_v3.initialize_h1_shared_cap_owner_v3(
        root,
        profile=profile,
        source_manifest=source,
        rejection_gate=gate,
    )
    uppers = {
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
        bundle,
        historical_owner,
        site_reservation_uppers=uppers,
    )
    session = dispatch_v1.start_h1_lifecycle_construction_dispatch_v1(
        bundle,
        dispatch_profile,
        historical_owner,
    )
    first = dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
        session,
        callback=None,
    )
    assert first.outcome == "SUCCESS"
    failure = dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
        session,
        callback=_raise_runtime_error,
    )
    assert failure.outcome == "CALLBACK_FAILED_AFTER_ADMISSION"
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    upgraded = owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(
        historical_owner
    )
    owner = owner_v4.open_h1_shared_cap_owner_v4_wal(
        upgraded.owner_directory,
        expected_runtime_id=upgraded.runtime_id,
        gate_directory=upgraded.gate_directory,
    )
    replay = owner_v4.replay_h1_shared_cap_owner_v4_wal(owner)
    attestation = tail_v1.issue_h1_tail_bound_prefix_attestation_v1(
        trace.canonical_bytes,
        bundle=bundle,
        profile=dispatch_profile,
        owner=owner,
        semantic_closure=semantic_closure,
        expected_tail_sequence=replay["journal_sequence"],
        expected_tail_head_id=replay["journal_head_id"],
    )
    cleanup_pass = (
        cleanup_v1.select_h1_lifecycle_cleanup_pass_for_dispatch_trace_bytes_v1(
            analysis,
            trace.canonical_bytes,
            bundle=bundle,
            profile=dispatch_profile,
            owner=owner.owner,
        )
    )
    phase_spec = phase_v1.freeze_h1_attempt_execution_phase_spec_v1(
        root,
        logical_occurrence_id=profile.logical_occurrence_id,
        route_attempt_id=profile.route_attempt_id,
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
        rejection_gate=gate,
        anchored_program_id=bundle.program.anchored_program_id,
        handler_registry_id=bundle.registry.registry_id,
        cleanup_analysis=analysis,
    )
    phase = phase_v1.initialize_h1_attempt_execution_phase_owner_v1(
        phase_spec,
        rejection_gate=gate,
    )
    return _Case(
        profile,
        gate,
        owner,
        dispatch_profile,
        trace.canonical_bytes,
        attestation,
        cleanup_pass,
        phase_spec,
        phase,
    )


def _transition(
    case: _Case,
    semantic_closure,
    lease: phase_v1.H1AttemptExecutionPhaseLeaseV1,
    *,
    crash_point: phase_v1.H1AttemptPhaseCrashPointV1 = (
        phase_v1.H1AttemptPhaseCrashPointV1.NONE
    ),
):
    return phase_v1.transition_h1_attempt_to_cleanup_only_with_phase_lease_v1(
        lease,
        rejection_gate=case.gate,
        trace_bytes=case.trace_bytes,
        tail_attestation=case.attestation,
        semantic_closure=semantic_closure,
        cleanup_pass=case.cleanup_pass,
        owner=case.owner,
        crash_point=crash_point,
    )


def _append_owner_tail(case: _Case, suffix: str) -> None:
    reservation = owner_v4.reserve_h1_shared_cap_owner_v4_wal(
        case.owner,
        operation_id=_id(f"later-tail-operation-{suffix}"),
        site_key=f"later:tail:{suffix}",
        path="io.read_bytes",
        reservation_upper=2,
    )
    with owner_v4.hold_h1_shared_cap_owner_v4_wal_side_effect(
        case.owner,
        reservation,
    ):
        pass
    owner_v4.settle_h1_shared_cap_owner_v4_wal(
        case.owner,
        reservation,
        value_basis=owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        native_observed_value=1,
        evidence_source_id=_id(f"later-tail-evidence-{suffix}"),
    )


def test_callback_failure_transition_is_durable_and_one_way(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="happy",
    )
    initial = phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        case.phase,
        rejection_gate=case.gate,
    )
    assert initial["state"] == "NORMAL"
    assert initial["phase_and_gate_observed_under_ordered_exclusive_locks"] is True
    with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
        case.phase,
        rejection_gate=case.gate,
    ) as lease:
        transition = _transition(case, semantic_closure, lease)
        assert transition.payload["transaction_id"] == case.profile.transaction_id
        assert transition.payload["decision_point_id"] == case.profile.decision_point_id
        assert transition.payload["primary_failure_trigger_kind"] == (
            "LIFECYCLE_FAILURE"
        )
        with pytest.raises(
            phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error
        ):
            _transition(case, semantic_closure, lease)
    replayed = phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        case.phase,
        rejection_gate=case.gate,
    )
    assert replayed["state"] == "CLEANUP_ONLY"
    assert replayed["h1_attempt_cleanup_transition_id"] == transition.transition_id
    reopened = phase_v1.open_h1_attempt_execution_phase_owner_v1(
        case.phase_spec,
        rejection_gate=case.gate,
    )
    repeated = phase_v1.initialize_h1_attempt_execution_phase_owner_v1(
        case.phase_spec,
        rejection_gate=case.gate,
    )
    assert reopened.allocation_id == repeated.allocation_id == case.phase.allocation_id
    with pytest.raises(phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error):
        with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
            reopened,
            rejection_gate=case.gate,
        ):
            pass
    with phase_v1.hold_h1_attempt_cleanup_only_lease_v1(
        reopened,
        rejection_gate=case.gate,
        expected_transition_id=transition.transition_id,
    ) as cleanup_lease:
        assert cleanup_lease.lease_kind is phase_v1.H1AttemptPhaseLeaseKindV1.CLEANUP_PHASE
        assert all(
            not os.get_inheritable(descriptor)
            for descriptor in (
                cleanup_lease._root_fd,
                cleanup_lease._phase_fd,
                cleanup_lease._lock_fd,
                cleanup_lease._cursor_fd,
            )
        )
    with pytest.raises(phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error):
        with phase_v1.hold_h1_attempt_cleanup_only_lease_v1(
            reopened,
            rejection_gate=case.gate,
            expected_transition_id="0" * 64,
        ):
            pass


def test_external_rejection_uses_transition_only_lease_after_gate_closes(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="external-rejection",
    )
    commit = rejection_v1.commit_h1_attempt_rejection_v1(
        case.gate,
        writer_role=rejection_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        decision_point_id=_id("external-decision"),
        transaction_id=_id("external-transaction"),
        shared_owner_profile_core_id=_id("external-owner-profile"),
        rejection_request_id=_id("external-rejection-request"),
        source_kind=rejection_v1.H1RejectionSourceKindV1.BUSINESS_ENGINE,
        site_key="external:business-cap",
        path="io.read_bytes",
        limit_kind=rejection_v1.H1RejectionLimitKindV1.SHARED_PATH,
        reservation_upper=2,
        candidate=2,
        hard_cap=1,
        reason_code="EXTERNAL_BUSINESS_CAP_EXHAUSTED",
    )
    rejection_v1.acknowledge_h1_attempt_rejection_v1(
        case.gate,
        commit,
        writer_role=rejection_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        shared_owner_receipt_id=_id("external-receipt"),
        shared_owner_event_id=_id("external-event"),
        shared_owner_snapshot_id=_id("external-snapshot"),
    )
    replayed = phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        case.phase,
        rejection_gate=case.gate,
    )
    assert replayed["state"] == "NORMAL"
    assert replayed["rejection_durable_while_phase_normal"] is True
    with pytest.raises(phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error):
        with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
            case.phase,
            rejection_gate=case.gate,
        ):
            pass
    with phase_v1.hold_h1_attempt_cleanup_transition_lease_v1(
        case.phase,
        rejection_gate=case.gate,
    ) as lease:
        assert lease.lease_kind is phase_v1.H1AttemptPhaseLeaseKindV1.TRANSITION_ONLY
        with pytest.raises(
            phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
            match="attested exact current",
        ):
            _transition(case, semantic_closure, lease)
    assert phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        case.phase,
        rejection_gate=case.gate,
    )["state"] == "NORMAL"


def test_later_owner_tail_invalidates_transition_before_intent(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="stale-tail",
    )
    _append_owner_tail(case, "stale-tail")
    with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
        case.phase,
        rejection_gate=case.gate,
    ) as lease:
        with pytest.raises(
            phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
            match="attested exact current",
        ):
            _transition(case, semantic_closure, lease)
    assert not (Path(case.phase.phase_directory) / phase_v1._INTENT_FILE).exists()
    assert phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        case.phase,
        rejection_gate=case.gate,
    )["state"] == "NORMAL"


@pytest.mark.parametrize(
    "crash_point",
    [
        phase_v1.H1AttemptPhaseCrashPointV1.AFTER_INTENT_FSYNC,
        phase_v1.H1AttemptPhaseCrashPointV1.AFTER_INTENT_CURSOR_FSYNC,
        phase_v1.H1AttemptPhaseCrashPointV1.AFTER_COMMIT_LINK_FSYNC,
        phase_v1.H1AttemptPhaseCrashPointV1.AFTER_CLEANUP_CURSOR_FSYNC,
    ],
)
def test_real_process_exit_at_each_durable_boundary_converges(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
    crash_point,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix=f"kill-{crash_point.value}",
    )
    child = os.fork()
    if child == 0:  # pragma: no branch - child exits below
        try:
            phase = phase_v1.open_h1_attempt_execution_phase_owner_v1(
                case.phase_spec,
                rejection_gate=case.gate,
            )
            with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
                phase,
                rejection_gate=case.gate,
            ) as lease:
                try:
                    _transition(
                        case,
                        semantic_closure,
                        lease,
                        crash_point=crash_point,
                    )
                except phase_v1.H1AttemptPhaseInjectedCrashV1:
                    # Exit before either retained context can run ``finally``.
                    os._exit(73)
        except BaseException:
            os._exit(74)
        os._exit(75)
    _, status = os.waitpid(child, 0)
    assert os.WIFEXITED(status)
    assert os.WEXITSTATUS(status) == 73
    reopened = phase_v1.open_h1_attempt_execution_phase_owner_v1(
        case.phase_spec,
        rejection_gate=case.gate,
    )
    replayed = phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        reopened,
        rejection_gate=case.gate,
    )
    assert replayed["state"] == "CLEANUP_ONLY"
    transition_id = replayed["h1_attempt_cleanup_transition_id"]
    phase_directory = Path(reopened.phase_directory)
    root_directory = Path(reopened.root_directory)
    intent = phase_directory / phase_v1._INTENT_FILE
    commit = phase_directory / phase_v1._COMMIT_FILE
    seal = root_directory / phase_v1._root_transition_seal_name(
        reopened.route_attempt_id
    )
    assert intent.read_bytes() == commit.read_bytes() == seal.read_bytes()
    assert intent.stat().st_ino == commit.stat().st_ino == seal.stat().st_ino
    with phase_v1.hold_h1_attempt_cleanup_only_lease_v1(
        reopened,
        rejection_gate=case.gate,
        expected_transition_id=transition_id,
    ):
        pass


@pytest.mark.parametrize("valid_prefix", [True, False])
def test_cursor_repairs_only_the_exact_expected_torn_frame_prefix(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
    valid_prefix,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix=f"torn-{valid_prefix}",
    )
    with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
        case.phase,
        rejection_gate=case.gate,
    ) as lease:
        with pytest.raises(phase_v1.H1AttemptPhaseInjectedCrashV1):
            _transition(
                case,
                semantic_closure,
                lease,
                crash_point=phase_v1.H1AttemptPhaseCrashPointV1.AFTER_INTENT_FSYNC,
            )
        with pytest.raises(phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error):
            phase_v1._require_live_lease(
                lease,
                phase_v1.H1AttemptExecutionPhaseV1.NORMAL,
                (phase_v1.H1AttemptPhaseLeaseKindV1.NORMAL_PHASE,),
            )
    phase_directory = Path(case.phase.phase_directory)
    intent = phase_v1._transition_from_raw(
        (phase_directory / phase_v1._INTENT_FILE).read_bytes()
    )
    cursor = phase_directory / phase_v1._CURSOR_FILE
    records = phase_v1._parse_cursor(cursor.read_bytes(), case.phase.spec_id)
    expected = canonical_json_bytes(
        phase_v1._cursor_record(
            spec_id=case.phase.spec_id,
            sequence=1,
            previous_id=records[0]["h1_attempt_phase_cursor_record_id"],
            state=phase_v1.H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE,
            transition_id=intent.transition_id,
        )
    ) + b"\n"
    with cursor.open("ab") as stream:
        stream.write(expected[: len(expected) // 2] if valid_prefix else b"{evil")
        stream.flush()
        os.fsync(stream.fileno())
    if valid_prefix:
        assert phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase,
            rejection_gate=case.gate,
        )["state"] == "CLEANUP_ONLY"
    else:
        with pytest.raises(
            phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
            match="expected crash-torn",
        ):
            phase_v1.replay_h1_attempt_execution_phase_owner_v1(
                case.phase,
                rejection_gate=case.gate,
            )


@pytest.mark.parametrize("publication_cleanup_fault", ["unlink", "directory-fsync"])
def test_post_intent_publication_cleanup_failure_poison_leases_and_recovers(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
    monkeypatch,
    publication_cleanup_fault,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix=f"post-intent-{publication_cleanup_fault}",
    )
    with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
        case.phase,
        rejection_gate=case.gate,
    ) as lease:
        original_unlink = phase_v1.os.unlink
        original_fsync = phase_v1.os.fsync
        state = {"temp_unlinked": False, "raised": False}

        def injected_unlink(path, *args, **kwargs):
            is_transition_temp = (
                kwargs.get("dir_fd") == lease._phase_fd
                and str(path).startswith(phase_v1._TEMP_PREFIX)
            )
            if (
                publication_cleanup_fault == "unlink"
                and is_transition_temp
                and not state["raised"]
            ):
                state["raised"] = True
                raise OSError("injected temp unlink failure after durable intent")
            result = original_unlink(path, *args, **kwargs)
            if is_transition_temp:
                state["temp_unlinked"] = True
            return result

        def injected_fsync(descriptor):
            if (
                publication_cleanup_fault == "directory-fsync"
                and descriptor == lease._phase_fd
                and state["temp_unlinked"]
                and not state["raised"]
            ):
                state["raised"] = True
                raise OSError("injected directory fsync failure after temp unlink")
            return original_fsync(descriptor)

        class _FaultingPhaseOS:
            def __getattr__(self, name):
                return getattr(os, name)

            unlink = staticmethod(injected_unlink)
            fsync = staticmethod(injected_fsync)

        with monkeypatch.context() as injected:
            injected.setattr(phase_v1, "os", _FaultingPhaseOS())
            with pytest.raises(OSError, match="injected"):
                _transition(case, semantic_closure, lease)
        assert state["raised"] is True
        with pytest.raises(
            phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
            match="stale",
        ):
            phase_v1._require_live_lease(
                lease,
                phase_v1.H1AttemptExecutionPhaseV1.NORMAL,
                (phase_v1.H1AttemptPhaseLeaseKindV1.NORMAL_PHASE,),
            )

    replayed = phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        case.phase,
        rejection_gate=case.gate,
    )
    assert replayed["state"] == "CLEANUP_ONLY"


def test_prelink_publication_failure_consumes_only_current_lease(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
    monkeypatch,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="prelink-publication-failure",
    )
    with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
        case.phase,
        rejection_gate=case.gate,
    ) as lease:
        def fail_before_link(directory_fd, name, raw, *, mode=0o400):
            assert directory_fd == lease._phase_fd
            assert name == phase_v1._INTENT_FILE
            assert raw
            assert mode == 0o400
            raise OSError("injected failure before intent link")

        with monkeypatch.context() as injected:
            injected.setattr(phase_v1, "_publish_new", fail_before_link)
            with pytest.raises(OSError, match="before intent link"):
                _transition(case, semantic_closure, lease)
        with pytest.raises(
            phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
            match="stale",
        ):
            phase_v1._require_live_lease(
                lease,
                phase_v1.H1AttemptExecutionPhaseV1.NORMAL,
                (phase_v1.H1AttemptPhaseLeaseKindV1.NORMAL_PHASE,),
            )
        assert not (
            Path(case.phase.phase_directory) / phase_v1._INTENT_FILE
        ).exists()

    assert phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        case.phase,
        rejection_gate=case.gate,
    )["state"] == "NORMAL"


def test_root_seal_recovers_phase_local_rollback_and_allocation_is_strict(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="seal-recovery",
    )
    with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
        case.phase,
        rejection_gate=case.gate,
    ) as lease:
        transition = _transition(case, semantic_closure, lease)
    phase_directory = Path(case.phase.phase_directory)
    cursor = phase_directory / phase_v1._CURSOR_FILE
    genesis = cursor.read_bytes().splitlines(keepends=True)[0]
    (phase_directory / phase_v1._INTENT_FILE).unlink()
    (phase_directory / phase_v1._COMMIT_FILE).unlink()
    cursor.write_bytes(genesis)
    replayed = phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        case.phase,
        rejection_gate=case.gate,
    )
    assert replayed["state"] == "CLEANUP_ONLY"
    assert replayed["h1_attempt_cleanup_transition_id"] == transition.transition_id

    allocation = Path(case.phase.root_directory) / phase_v1._allocation_name(
        case.phase.route_attempt_id
    )
    document = json.loads(allocation.read_text(encoding="utf-8"))
    document["unknown_attack_field"] = True
    allocation.chmod(0o600)
    allocation.write_bytes(canonical_json_bytes(document))
    allocation.chmod(0o400)
    with pytest.raises(
        phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error
    ):
        phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase,
            rejection_gate=case.gate,
        )


def test_inode_mode_unknown_entry_and_lease_attacks_fail_closed(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="attacks",
    )
    with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
        case.phase,
        rejection_gate=case.gate,
    ) as lease:
        with pytest.raises(phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error):
            with phase_v1.hold_h1_attempt_cleanup_transition_lease_v1(
                case.phase,
                rejection_gate=case.gate,
            ):
                pass
        with pytest.raises(phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error):
            pickle.dumps(lease)

        errors: list[BaseException] = []

        def crossed_thread() -> None:
            try:
                phase_v1._require_live_lease(
                    lease,
                    phase_v1.H1AttemptExecutionPhaseV1.NORMAL,
                    (phase_v1.H1AttemptPhaseLeaseKindV1.NORMAL_PHASE,),
                )
            except BaseException as error:
                errors.append(error)

        thread = threading.Thread(target=crossed_thread)
        thread.start()
        thread.join(timeout=5)
        assert len(errors) == 1
    with pytest.raises(phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error):
        phase_v1._require_live_lease(
            lease,
            phase_v1.H1AttemptExecutionPhaseV1.NORMAL,
            (phase_v1.H1AttemptPhaseLeaseKindV1.NORMAL_PHASE,),
        )

    phase_directory = Path(case.phase.phase_directory)
    unknown = phase_directory / "unknown-entry"
    unknown.write_text("attack", encoding="utf-8")
    with pytest.raises(
        phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
        match="unknown entry",
    ):
        phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase,
            rejection_gate=case.gate,
        )
    unknown.unlink()
    lock = phase_directory / phase_v1._LOCK_FILE
    old = phase_directory / "old-phase-lock"
    lock.rename(old)
    old.unlink()
    lock.touch(mode=0o600)
    with pytest.raises(
        phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
        match="lock inode changed",
    ):
        phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase,
            rejection_gate=case.gate,
        )


def test_root_attempt_directory_symlink_mode_and_missing_field_attacks_fail_closed(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="physical-layout-attacks",
    )
    root = Path(case.phase.root_directory)
    phase_directory = Path(case.phase.phase_directory)

    phase_directory.chmod(0o755)
    with pytest.raises(
        phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
        match="attempt directory mode changed",
    ):
        phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase,
            rejection_gate=case.gate,
        )
    phase_directory.chmod(0o700)

    retired_phase = root / "retired-attempt-directory"
    phase_directory.rename(retired_phase)
    phase_directory.mkdir(mode=0o700)
    with pytest.raises(
        phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
        match="attempt directory inode changed",
    ):
        phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase,
            rejection_gate=case.gate,
        )
    phase_directory.rmdir()
    retired_phase.rename(phase_directory)

    spec_path = phase_directory / phase_v1._SPEC_FILE
    retired_spec = fast_root / "retired-phase-spec"
    spec_path.rename(retired_spec)
    spec_path.symlink_to(retired_spec)
    with pytest.raises(
        phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
        match="cannot be opened safely",
    ):
        phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase,
            rejection_gate=case.gate,
        )
    spec_path.unlink()
    retired_spec.rename(spec_path)

    allocation = root / phase_v1._allocation_name(case.phase.route_attempt_id)
    original_allocation = allocation.read_bytes()
    missing = loads_canonical_json(original_allocation)
    missing.pop("phase_cursor_inode")
    allocation.chmod(0o600)
    allocation.write_bytes(canonical_json_bytes(missing))
    allocation.chmod(0o400)
    with pytest.raises(
        phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
        match="canonical",
    ):
        phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase,
            rejection_gate=case.gate,
        )
    allocation.chmod(0o600)
    allocation.write_bytes(original_allocation)
    allocation.chmod(0o400)

    retired_root = root.with_name(f"{root.name}-retired")
    root.rename(retired_root)
    root.mkdir(mode=0o700)
    with pytest.raises(
        phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
        match="root inode changed",
    ):
        phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase,
            rejection_gate=case.gate,
        )
    root.rmdir()
    retired_root.rename(root)

    assert phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        case.phase,
        rejection_gate=case.gate,
    )["state"] == "NORMAL"


def test_crossed_transition_evidence_cannot_publish_intent(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="evidence-primary",
    )
    foreign = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="evidence-foreign",
    )

    closure_payload = semantic_closure.payload
    closure_payload["profile_key"] = "crossed-semantic-closure"
    crossed_closure = tail_v1.H1PrefixVerifierSemanticClosureV1(
        tail_v1._CLOSURE_ISSUER,
        canonical_json_bytes(closure_payload),
        semantic_closure.function_refs,
        semantic_closure.global_refs,
        semantic_closure.module_refs,
    )
    registry_payload = case.attestation.payload
    registry_payload["h1_anchored_lifecycle_handler_registry_id"] = _id(
        "crossed-registry"
    )
    crossed_registry = tail_v1.H1TailBoundPrefixAttestationV1(
        tail_v1._ATTESTATION_ISSUER,
        canonical_json_bytes(registry_payload),
    )
    cleanup_payload = case.cleanup_pass.payload
    cleanup_payload["branch_key"] = "FAIL:crossed:CALLBACK_FAILED_AFTER_ADMISSION"
    crossed_cleanup = cleanup_v1.H1LifecycleCleanupPassV1(
        cleanup_v1._PASS_ISSUER,
        canonical_json_bytes(cleanup_payload),
    )

    with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
        case.phase,
        rejection_gate=case.gate,
    ) as lease:
        defaults = {
            "rejection_gate": case.gate,
            "trace_bytes": case.trace_bytes,
            "tail_attestation": case.attestation,
            "semantic_closure": semantic_closure,
            "cleanup_pass": case.cleanup_pass,
            "owner": case.owner,
        }
        attacks = (
            {"rejection_gate": foreign.gate},
            {"owner": foreign.owner},
            {"trace_bytes": foreign.trace_bytes},
            {"tail_attestation": foreign.attestation},
            {"tail_attestation": crossed_registry},
            {"semantic_closure": crossed_closure},
            {"cleanup_pass": crossed_cleanup},
        )
        for attack in attacks:
            arguments = {**defaults, **attack}
            with pytest.raises(ValueError):
                phase_v1.transition_h1_attempt_to_cleanup_only_with_phase_lease_v1(
                    lease,
                    **arguments,
                )
            assert not (
                Path(case.phase.phase_directory) / phase_v1._INTENT_FILE
            ).exists()
            phase_v1._require_live_lease(
                lease,
                phase_v1.H1AttemptExecutionPhaseV1.NORMAL,
                (phase_v1.H1AttemptPhaseLeaseKindV1.NORMAL_PHASE,),
            )


@pytest.mark.parametrize(
    ("target_kind", "message"),
    [
        ("root_lock", "allocation"),
        ("cursor", "cursor inode changed"),
    ],
)
def test_root_lock_and_cursor_inode_replacement_fail_closed(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
    target_kind,
    message,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix=f"inode-{target_kind}",
    )
    if target_kind == "root_lock":
        target = Path(case.phase.root_directory) / phase_v1._ROOT_LOCK
    else:
        target = Path(case.phase.phase_directory) / phase_v1._CURSOR_FILE
    retired = target.with_name(f"retired-{target.name}")
    target.rename(retired)
    retired.unlink()
    target.touch(mode=0o600)
    with pytest.raises(
        phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
        match=message,
    ):
        phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase,
            rejection_gate=case.gate,
        )


def test_two_processes_serialize_and_loser_cannot_reopen_normal(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="process-race",
    )
    ready_read, ready_write = os.pipe()
    release_read, release_write = os.pipe()
    child = os.fork()
    if child == 0:  # pragma: no branch - child exits below
        os.close(ready_read)
        os.close(release_write)
        try:
            phase = phase_v1.open_h1_attempt_execution_phase_owner_v1(
                case.phase_spec,
                rejection_gate=case.gate,
            )
            with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
                phase,
                rejection_gate=case.gate,
            ) as lease:
                os.write(ready_write, b"1")
                os.read(release_read, 1)
                _transition(case, semantic_closure, lease)
        except BaseException:
            os._exit(81)
        os._exit(0)
    os.close(ready_write)
    os.close(release_read)
    assert os.read(ready_read, 1) == b"1"
    entered = threading.Event()
    failed: list[BaseException] = []

    def contender() -> None:
        try:
            with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
                case.phase,
                rejection_gate=case.gate,
            ):
                entered.set()
        except BaseException as error:
            failed.append(error)

    contender_thread = threading.Thread(target=contender)
    contender_thread.start()
    time.sleep(0.1)
    assert not entered.is_set()
    os.write(release_write, b"1")
    _, status = os.waitpid(child, 0)
    contender_thread.join(timeout=10)
    assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
    assert not entered.is_set()
    assert len(failed) == 1
    assert phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        case.phase,
        rejection_gate=case.gate,
    )["state"] == "CLEANUP_ONLY"


def test_fork_child_context_exit_cannot_unlock_parent_phase_or_gate(
    fast_root,
    bundle,
    analysis,
    semantic_closure,
) -> None:
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="fork-inside-lease",
    )

    class _LeaveInheritedContext(Exception):
        pass

    try:
        with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
            case.phase,
            rejection_gate=case.gate,
        ) as lease:
            child = os.fork()
            if child == 0:  # pragma: no branch - child exits in outer handler
                raise _LeaveInheritedContext
            _, status = os.waitpid(child, 0)
            assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0

            entered = threading.Event()
            failed: list[BaseException] = []

            def contender() -> None:
                try:
                    with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
                        case.phase,
                        rejection_gate=case.gate,
                    ):
                        entered.set()
                except BaseException as error:
                    failed.append(error)

            contender_thread = threading.Thread(target=contender)
            contender_thread.start()
            time.sleep(0.1)
            assert not entered.is_set()
            transition = _transition(case, semantic_closure, lease)
        contender_thread.join(timeout=10)
        assert not contender_thread.is_alive()
        assert not entered.is_set()
        assert len(failed) == 1
        assert phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase,
            rejection_gate=case.gate,
        )["h1_attempt_cleanup_transition_id"] == transition.transition_id
    except _LeaveInheritedContext:
        # Unwinding the inherited ``with`` executes both fork-aware finalizers.
        os._exit(0)


def test_frozen_claim_boundary_remains_closed() -> None:
    payload = {"same": "payload"}
    ids = {
        domains_v2.extension_content_id_v2(domain, payload)
        for domain in domains_v2.K7_H1_DOMAIN_TAG_EXTENSION_V2
    }
    assert len(ids) == 3
    with pytest.raises(ValueError):
        domains_v2.extension_content_id_v2("acfqp:unregistered:v1", payload)
    assert phase_v1.PHASE_AUTHORITY_PRESENT is True
    assert phase_v1.NORMAL_PHASE_LEASE_PRESENT is True
    assert phase_v1.NORMAL_EXECUTION_LEASE_PRESENT is False
    assert phase_v1.LEASE_AWARE_NORMAL_DISPATCH_PRESENT is False
    assert phase_v1.HISTORICAL_CAP_REJECTION_TRANSITION_REACHABLE is False
    assert (
        phase_v1.HISTORICAL_POST_REJECTION_PREFIX_ATTESTATION_REACHABLE is False
    )
    assert phase_v1.CLEANUP_EXECUTION_AUTHORITY_PRESENT is False
    assert phase_v1.PRODUCTION_EXECUTION_AUTHORITY_PRESENT is False
    assert phase_v1.FORMAL_COUNTER_RECORD_ISSUED is False
    assert phase_v1.FORMAL_WORK_VECTOR_ISSUED is False
    assert phase_v1.FORMAL_COMPARISON_VECTOR_ISSUED is False
    assert phase_v1.FORMAL_V7_ROUTE_AUTHORITY_PRESENT is False
    assert phase_v1.NO_EVENT_RECOVERY_COMPLETE is False
    assert phase_v1.CLEANUP_ENVELOPE_PREADMITTED is False
    assert phase_v1.COUNTER_COMPLETENESS_GATE_STATUS == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert phase_v1.WORKLOAD_ECONOMICS_GATE_STATUS == (
        "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )
    assert phase_v1.SAMPLE_EFFICIENCY_GATE_STATUS == (
        "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
    )
    assert phase_v1.OFFICIAL_EXECUTION_ALLOWED is False
