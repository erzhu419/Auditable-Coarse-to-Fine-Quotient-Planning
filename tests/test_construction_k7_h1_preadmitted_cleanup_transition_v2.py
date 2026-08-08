from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import tempfile

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_attempt_execution_phase_owner_v1 as phase_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as output_join_v1
from acfqp import construction_k7_h1_phase_aware_normal_prefix_v1 as normal_v1
from acfqp import construction_k7_h1_preadmitted_cleanup_transition_v2 as cleanup_v2
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_tail_bound_prefix_attestation_v1 as tail_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json

from test_construction_k7_h1_attempt_execution_phase_owner_v1 import (
    _build_case as _build_legacy_phase_case,
    _transition as _legacy_phase_transition,
)
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


@pytest.fixture(scope="module")
def semantic_closure():
    return tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()


@pytest.fixture
def fast_root():
    base = "/dev/shm" if Path("/dev/shm").is_dir() else "/tmp"
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-cleanup-v2-", dir=base))
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


def _preadmit(case, bundle, analysis):
    with _lease(case, bundle) as lease:
        return cleanup_v2.preadmit_h1_normal_prefix_cleanup_envelope_v2(
            lease, cleanup_analysis=analysis
        )


def _success_ordinal_1(case, bundle):
    with _lease(case, bundle) as lease:
        result = normal_v1.execute_next_h1_phase_aware_normal_site_v1(lease)
    assert result.outcome == "SUCCESS"


def _boom():
    raise RuntimeError("registered callback failure")


def test_envelope_is_pre_ordinal_structural_whitelist_only(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="envelope")
    envelope = _preadmit(case, bundle, analysis)
    payload = envelope.payload
    assert payload["failure_branch_action_whitelist_count"] == 112
    assert payload["dispatcher_reachable_failure_branch_count"] == 111
    assert sum(
        row["dispatcher_outcome_reachable"] is False
        for row in payload["failure_branch_action_whitelist"]
    ) == 1
    assert payload["cleanup_actions_are_structural_whitelist_only"] is True
    assert payload["owner_cleanup_continuation_present"] is False
    assert payload["native_resource_receipt_journal_present"] is False
    assert payload["cleanup_budget_admission_present"] is False
    assert payload["cleanup_execution_authority_present"] is False
    assert not {
        "READBACK_OUTPUT_ROLE",
        "FINALIZE_AND_SETTLE_OUTPUT_RESERVATION",
        "CLOSE_OUTPUT_OWNER",
    } & {
        action["action_kind"]
        for row in payload["failure_branch_action_whitelist"]
        for action in row["planned_cleanup_actions"]
    }


def test_integrated_callback_failure_never_returns_bare_event(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="callback")
    envelope = _preadmit(case, bundle, analysis)
    _success_ordinal_1(case, bundle)
    with _lease(case, bundle) as lease:
        result = cleanup_v2.execute_next_h1_normal_site_to_cleanup_boundary_v2(
            lease,
            cleanup_analysis=analysis,
            envelope=envelope,
            callback=_boom,
        )
    assert type(result) is cleanup_v2.H1NormalFailureCleanupBoundaryV2
    assert result.failure_event.outcome == "CALLBACK_FAILED_AFTER_ADMISSION"
    assert result.transition.payload["legacy_dispatch_trace_translation_used"] is False
    with pytest.raises(phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error):
        phase_v1.replay_h1_attempt_execution_phase_owner_v1(
            case.phase, rejection_gate=case.gate
        )
    replay = cleanup_v2.replay_h1_attempt_execution_phase_owner_v2(
        case.phase, rejection_gate=case.gate
    )
    assert replay["state"] == "CLEANUP_ONLY"
    assert replay["transition_schema_version"] == "V2"
    with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
        case.phase,
        rejection_gate=case.gate,
        expected_transition_id=result.transition.transition_id,
    ) as cleanup_lease:
        assert cleanup_lease.transition.transition_id == result.transition.transition_id


def test_integrated_cap_rejection_transitions_under_same_outer_lease(
    fast_root, bundle, analysis
):
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        suffix="cap",
        caps={"io.staged_bytes": 10},
    )
    envelope = _preadmit(case, bundle, analysis)
    for row in bundle.program.transitions[:7]:
        with _lease(case, bundle) as lease:
            event = cleanup_v2.execute_next_h1_normal_site_to_cleanup_boundary_v2(
                lease,
                cleanup_analysis=analysis,
                envelope=envelope,
                callback=_callback_for(row),
            )
        assert event.outcome == "SUCCESS"
    with _lease(case, bundle) as lease:
        result = cleanup_v2.execute_next_h1_normal_site_to_cleanup_boundary_v2(
            lease,
            cleanup_analysis=analysis,
            envelope=envelope,
            callback=lambda: 1,
        )
    assert type(result) is cleanup_v2.H1NormalFailureCleanupBoundaryV2
    assert result.failure_event.outcome == "CAP_REJECTED_BEFORE_SIDE_EFFECT"
    assert result.transition.payload["primary_failure_trigger_kind"] == "CAP_REJECTION"


def test_recovery_after_native_cell_never_reexecutes_callback(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="native-cell-recovery")
    envelope = _preadmit(case, bundle, analysis)
    _success_ordinal_1(case, bundle)
    calls = []
    with pytest.raises(normal_v1.H1NormalPrefixInjectedCrashV1):
        with _lease(case, bundle) as lease:
            normal_v1.execute_next_h1_phase_aware_normal_site_v1(
                lease,
                callback=lambda: calls.append(1),
                crash_point=normal_v1.H1NormalPrefixCrashPointV1.AFTER_NATIVE_CELL_FSYNC,
            )
    assert calls == []
    with _lease(case, bundle) as lease:
        result = cleanup_v2.recover_h1_normal_site_to_cleanup_boundary_v2(
            lease, cleanup_analysis=analysis, envelope=envelope
        )
    assert calls == []
    assert type(result) is cleanup_v2.H1NormalFailureCleanupBoundaryV2
    assert result.failure_event.document["callback_invocation_may_have_occurred"] is True
    assert cleanup_v2.replay_h1_attempt_execution_phase_owner_v2(
        case.phase, rejection_gate=case.gate
    )["state"] == "CLEANUP_ONLY"


@pytest.mark.parametrize(
    "crash_point",
    [
        phase_v1.H1AttemptPhaseCrashPointV1.AFTER_INTENT_FSYNC,
        phase_v1.H1AttemptPhaseCrashPointV1.AFTER_INTENT_CURSOR_FSYNC,
        phase_v1.H1AttemptPhaseCrashPointV1.AFTER_COMMIT_LINK_FSYNC,
        phase_v1.H1AttemptPhaseCrashPointV1.AFTER_CLEANUP_CURSOR_FSYNC,
    ],
)
def test_v2_transition_crash_points_replay_to_cleanup_only(
    fast_root, bundle, analysis, crash_point
):
    suffix = "crash-" + hashlib.sha256(crash_point.value.encode()).hexdigest()[:8]
    case = _build_case(fast_root, bundle, analysis, suffix=suffix)
    envelope = _preadmit(case, bundle, analysis)
    _success_ordinal_1(case, bundle)
    with pytest.raises(phase_v1.H1AttemptPhaseInjectedCrashV1):
        with _lease(case, bundle) as lease:
            cleanup_v2.execute_next_h1_normal_site_to_cleanup_boundary_v2(
                lease,
                cleanup_analysis=analysis,
                envelope=envelope,
                callback=_boom,
                transition_crash_point=crash_point,
            )
    replay = cleanup_v2.replay_h1_attempt_execution_phase_owner_v2(
        case.phase, rejection_gate=case.gate
    )
    assert replay["state"] == "CLEANUP_ONLY"
    assert replay["transition_schema_version"] == "V2"


def test_late_mint_and_foreign_envelope_fail_before_transition(
    fast_root, bundle, analysis
):
    late = _build_case(fast_root, bundle, analysis, suffix="late")
    _success_ordinal_1(late, bundle)
    with _lease(late, bundle) as lease:
        with pytest.raises(
            cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error,
            match="after ordinal 1",
        ):
            cleanup_v2.preadmit_h1_normal_prefix_cleanup_envelope_v2(
                lease, cleanup_analysis=analysis
            )

    left = _build_case(fast_root, bundle, analysis, suffix="left")
    right = _build_case(fast_root, bundle, analysis, suffix="right")
    left_envelope = _preadmit(left, bundle, analysis)
    right_envelope = _preadmit(right, bundle, analysis)
    assert left_envelope.envelope_id != right_envelope.envelope_id
    with _lease(left, bundle) as lease:
        with pytest.raises(
            cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error,
            match="durable envelope",
        ):
            cleanup_v2.execute_next_h1_normal_site_to_cleanup_boundary_v2(
                lease,
                cleanup_analysis=analysis,
                envelope=right_envelope,
            )
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(left.normal)
    assert snapshot.document["completed_event_count"] == 0


def test_unreachable_branch_and_output_authority_are_rejected(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="negative")
    envelope = _preadmit(case, bundle, analysis)
    with pytest.raises(
        cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error
    ):
        cleanup_v2._selected_whitelist_entry(
            envelope,
            {
                "ordinal": 1,
                "site_key": "memory:bind-working-hierarchy",
                "outcome": "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION",
            },
        )
    with pytest.raises(
        cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error,
        match="authoritative action",
    ):
        cleanup_v2._validate_cleanup_actions(
            [
                {
                    "cleanup_ordinal": 1,
                    "action_kind": "FINALIZE_AND_SETTLE_OUTPUT_RESERVATION",
                    "target": "output:reserve-route-wide",
                    "primary_failure_preserved": True,
                    "secondary_failure_is_append_only": True,
                    "continue_with_later_safe_cleanup_after_secondary_failure": True,
                    "new_business_work_allowed": False,
                    "normal_route_reservation_allowed": False,
                    "execution_authority_present": False,
                }
            ],
            branch_key="negative-control",
        )


def test_historical_phase_and_normal_sources_remain_byte_exact():
    assert hashlib.sha256(Path(phase_v1.__file__).read_bytes()).hexdigest() == (
        "db3c577ddd67ff8e3c1090c1d288a7bcade36c5e6bfd86906acb934b8d029a50"
    )
    assert hashlib.sha256(Path(normal_v1.__file__).read_bytes()).hexdigest() == (
        "541d21b966ea6aac37fe8633ba3f44a8319bbd17dadc5a059dbacd3874dd43b3"
    )


def _failed_boundary(case, bundle, analysis, envelope):
    _success_ordinal_1(case, bundle)
    with _lease(case, bundle) as lease:
        result = cleanup_v2.execute_next_h1_normal_site_to_cleanup_boundary_v2(
            lease,
            cleanup_analysis=analysis,
            envelope=envelope,
            callback=_boom,
        )
    assert type(result) is cleanup_v2.H1NormalFailureCleanupBoundaryV2
    return result


@pytest.mark.parametrize("replacement", ["missing", "separate-inode"])
def test_cleanup_only_replay_requires_immutable_commit(
    fast_root, bundle, analysis, replacement
):
    case = _build_case(fast_root, bundle, analysis, suffix=f"commit-{replacement}")
    envelope = _preadmit(case, bundle, analysis)
    _failed_boundary(case, bundle, analysis, envelope)
    commit = Path(case.phase.phase_directory) / phase_v1._COMMIT_FILE
    raw = commit.read_bytes()
    commit.unlink()
    if replacement == "separate-inode":
        commit.write_bytes(raw)
        commit.chmod(0o400)
    with pytest.raises(
        cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error,
        match="commit",
    ):
        cleanup_v2.replay_h1_attempt_execution_phase_owner_v2(
            case.phase, rejection_gate=case.gate
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("normal_prefix_last_ordinal", 39),
        ("formal_counter_records_issued", True),
        ("branch_selection_must_follow_unique_failed_tail_event", False),
        ("forbidden_output_authority_action_kinds", []),
        ("gate_state_at_preadmission", "ACKNOWLEDGED"),
        ("gate_owner_join_status_at_preadmission", "LOCAL_ACK_VERIFIED"),
    ],
)
def test_persisted_envelope_rejects_rehashed_claim_changes(
    fast_root, bundle, analysis, field, replacement
):
    case = _build_case(fast_root, bundle, analysis, suffix=f"envelope-{field}")
    envelope = _preadmit(case, bundle, analysis)
    payload = envelope.payload
    payload[field] = replacement
    document = {
        **payload,
        "h1_preadmitted_cleanup_envelope_id": cleanup_v2._content_id(
            cleanup_v2.ENVELOPE_DOMAIN, payload
        ),
    }
    with pytest.raises(
        cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error,
        match="claims",
    ):
        cleanup_v2._envelope_from_raw(canonical_json_bytes(document))


@pytest.mark.parametrize("field", ["sequence", "head"])
def test_envelope_binding_rejects_rehashed_preadmission_cutoff(
    fast_root, bundle, analysis, field
):
    case = _build_case(fast_root, bundle, analysis, suffix=f"cutoff-{field}")
    envelope = _preadmit(case, bundle, analysis)
    payload = envelope.payload
    if field == "sequence":
        payload["owner_tail_sequence_at_preadmission"] += 1
    else:
        payload["owner_tail_head_id_at_preadmission"] = hashlib.sha256(
            b"crossed-owner-head"
        ).hexdigest()
    crossed = cleanup_v2.H1PreadmittedCleanupEnvelopeV1(
        cleanup_v2._ENVELOPE_ISSUER, canonical_json_bytes(payload)
    )
    with _lease(case, bundle) as lease:
        with pytest.raises(
            cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error,
            match="cutoff",
        ):
            cleanup_v2._validate_envelope_bindings(crossed, lease, analysis)


def test_recovered_transition_rebinds_envelope_and_live_gate(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="transition-rebind")
    envelope = _preadmit(case, bundle, analysis)
    boundary = _failed_boundary(case, bundle, analysis, envelope)

    crossed_payload = boundary.transition.payload
    crossed_payload["transaction_id"] = hashlib.sha256(
        b"crossed-transaction"
    ).hexdigest()
    crossed = cleanup_v2.H1AttemptCleanupTransitionV2(
        cleanup_v2._TRANSITION_ISSUER, canonical_json_bytes(crossed_payload)
    )
    with pytest.raises(
        cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error,
        match="envelope",
    ):
        cleanup_v2._validate_transition_v2_against_envelope(crossed, envelope)

    gate_payload = boundary.transition.payload
    gate_payload["gate_state_at_transition"] = "ACKNOWLEDGED"
    crossed_gate = cleanup_v2.H1AttemptCleanupTransitionV2(
        cleanup_v2._TRANSITION_ISSUER, canonical_json_bytes(gate_payload)
    )
    with rejection_v1.hold_h1_attempt_rejection_gate_for_replay_v1(
        case.gate
    ) as snapshot:
        with pytest.raises(
            cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error,
            match="retained gate",
        ):
            cleanup_v2._validate_transition_v2_gate_snapshot(
                crossed_gate, snapshot
            )


def test_gate_inconsistent_intent_is_rejected_before_phase_repair(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="gate-preflight-order")
    envelope = _preadmit(case, bundle, analysis)
    _success_ordinal_1(case, bundle)
    with pytest.raises(phase_v1.H1AttemptPhaseInjectedCrashV1):
        with _lease(case, bundle) as lease:
            cleanup_v2.execute_next_h1_normal_site_to_cleanup_boundary_v2(
                lease,
                cleanup_analysis=analysis,
                envelope=envelope,
                callback=_boom,
                transition_crash_point=(
                    phase_v1.H1AttemptPhaseCrashPointV1.AFTER_INTENT_FSYNC
                ),
            )

    phase_directory = Path(case.phase.phase_directory)
    root_directory = Path(case.phase.root_directory)
    intent = phase_directory / phase_v1._INTENT_FILE
    commit = phase_directory / phase_v1._COMMIT_FILE
    seal = root_directory / phase_v1._root_transition_seal_name(
        case.phase.route_attempt_id
    )
    document = loads_canonical_json(intent.read_bytes())
    document.pop("h1_attempt_cleanup_transition_id")
    document["gate_state_at_transition"] = "ACKNOWLEDGED"
    rewritten = {
        **document,
        "h1_attempt_cleanup_transition_id": cleanup_v2._content_id(
            cleanup_v2.TRANSITION_DOMAIN, document
        ),
    }
    intent.unlink()
    intent.write_bytes(canonical_json_bytes(rewritten))
    intent.chmod(0o400)

    with pytest.raises(
        cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error,
        match="retained gate",
    ):
        cleanup_v2.replay_h1_attempt_execution_phase_owner_v2(
            case.phase, rejection_gate=case.gate
        )
    assert not commit.exists()
    assert not seal.exists()
    cursor = phase_directory / phase_v1._CURSOR_FILE
    rows = [loads_canonical_json(line) for line in cursor.read_bytes().splitlines()]
    assert rows[-1]["state"] == "NORMAL"


def test_rehashed_envelope_and_intent_cannot_change_normal_spec_cutoff(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="normal-cutoff-preflight")
    envelope = _preadmit(case, bundle, analysis)
    _success_ordinal_1(case, bundle)
    with pytest.raises(phase_v1.H1AttemptPhaseInjectedCrashV1):
        with _lease(case, bundle) as lease:
            cleanup_v2.execute_next_h1_normal_site_to_cleanup_boundary_v2(
                lease,
                cleanup_analysis=analysis,
                envelope=envelope,
                callback=_boom,
                transition_crash_point=(
                    phase_v1.H1AttemptPhaseCrashPointV1.AFTER_INTENT_FSYNC
                ),
            )

    envelope_root = (
        Path(case.normal.spec.payload["normal_prefix_base_realpath"])
        / cleanup_v2._ENVELOPE_ROOT_NAME
    )
    envelope_file = (
        envelope_root / case.normal.route_attempt_id / cleanup_v2._ENVELOPE_FILE
    )
    envelope_seal = envelope_root / cleanup_v2._envelope_seal_name(
        case.normal.route_attempt_id
    )
    envelope_document = loads_canonical_json(envelope_file.read_bytes())
    envelope_document.pop("h1_preadmitted_cleanup_envelope_id")
    envelope_document["owner_tail_sequence_at_preadmission"] += 1
    rewritten_envelope = {
        **envelope_document,
        "h1_preadmitted_cleanup_envelope_id": cleanup_v2._content_id(
            cleanup_v2.ENVELOPE_DOMAIN, envelope_document
        ),
    }
    envelope_file.unlink()
    envelope_seal.unlink()
    envelope_file.write_bytes(canonical_json_bytes(rewritten_envelope))
    envelope_file.chmod(0o400)
    os.link(envelope_file, envelope_seal)

    phase_directory = Path(case.phase.phase_directory)
    root_directory = Path(case.phase.root_directory)
    intent = phase_directory / phase_v1._INTENT_FILE
    intent_document = loads_canonical_json(intent.read_bytes())
    intent_document.pop("h1_attempt_cleanup_transition_id")
    intent_document["h1_preadmitted_cleanup_envelope_id"] = rewritten_envelope[
        "h1_preadmitted_cleanup_envelope_id"
    ]
    rewritten_intent = {
        **intent_document,
        "h1_attempt_cleanup_transition_id": cleanup_v2._content_id(
            cleanup_v2.TRANSITION_DOMAIN, intent_document
        ),
    }
    intent.unlink()
    intent.write_bytes(canonical_json_bytes(rewritten_intent))
    intent.chmod(0o400)

    with pytest.raises(
        cleanup_v2.ConstructionK7H1PreadmittedCleanupTransitionV2Error,
        match="immutable normal-prefix cutoff",
    ):
        cleanup_v2.replay_h1_attempt_execution_phase_owner_v2(
            case.phase, rejection_gate=case.gate
        )
    assert not (phase_directory / phase_v1._COMMIT_FILE).exists()
    assert not (
        root_directory
        / phase_v1._root_transition_seal_name(case.phase.route_attempt_id)
    ).exists()
    cursor = phase_directory / phase_v1._CURSOR_FILE
    rows = [loads_canonical_json(line) for line in cursor.read_bytes().splitlines()]
    assert rows[-1]["state"] == "NORMAL"


def test_failed_nested_phase_activation_does_not_leak_v2_context(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="nested-context")
    envelope = _preadmit(case, bundle, analysis)
    boundary = _failed_boundary(case, bundle, analysis, envelope)
    token = phase_v1._ACTIVE_PHASE_LEASES.set((case.phase.spec_id,))
    try:
        with pytest.raises(
            phase_v1.ConstructionK7H1AttemptExecutionPhaseOwnerV1Error,
            match="cannot nest",
        ):
            with cleanup_v2.hold_h1_attempt_cleanup_only_lease_v2(
                case.phase,
                rejection_gate=case.gate,
                expected_transition_id=boundary.transition.transition_id,
            ):
                pass
        assert cleanup_v2._ACTIVE_V2_PHASE_LEASES.get() == ()
    finally:
        phase_v1._ACTIVE_PHASE_LEASES.reset(token)


def test_successor_replay_delegates_actual_historical_v1_transition(
    fast_root, bundle, analysis, semantic_closure
):
    case = _build_legacy_phase_case(
        fast_root,
        bundle,
        analysis,
        semantic_closure,
        suffix="legacy-v1-delegation",
    )
    with phase_v1.hold_h1_attempt_normal_execution_lease_v1(
        case.phase, rejection_gate=case.gate
    ) as lease:
        transition = _legacy_phase_transition(case, semantic_closure, lease)
    replay = cleanup_v2.replay_h1_attempt_execution_phase_owner_v2(
        case.phase, rejection_gate=case.gate
    )
    assert replay["state"] == "CLEANUP_ONLY"
    assert replay["h1_attempt_cleanup_transition_id"] == transition.transition_id
    assert replay["transition_schema_version"] == "V1"
    assert replay["v1_transition_parser_delegated_exactly"] is True
