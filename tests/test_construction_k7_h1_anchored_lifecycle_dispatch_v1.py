from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
import tempfile

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as output_join_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANCHOR_ID = "4a4b0d1888f0ac18123e4163e1a26b0583a64946d2eb219e02d4b77dc0a3e327"


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def bundle():
    return dispatch_v1.freeze_h1_anchored_lifecycle_dispatch_bundle_v1(
        REPOSITORY_ROOT,
        expected_anchor_id=EXPECTED_ANCHOR_ID,
    )


@pytest.fixture
def fast_root() -> Path:
    base = "/dev/shm" if Path("/dev/shm").is_dir() else "/tmp"
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-dispatch-", dir=base))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _caps(default: int = 100_000) -> dict[str, int]:
    return {path: default for path in owner_v3.SHARED_RESOURCE_PATHS}


def _owner(
    root: Path,
    bundle,
    *,
    suffix: str,
    caps: dict[str, int] | None = None,
):
    profile = owner_v3.freeze_h1_shared_cap_profile_core_v3(
        logical_occurrence_id=_id(f"occurrence-{suffix}"),
        route_attempt_id=_id(f"attempt-{suffix}"),
        decision_point_id=_id(f"decision-{suffix}"),
        transaction_id=_id(f"transaction-{suffix}"),
        caller_pinned_lifecycle_provenance_id=bundle.program.provenance_id,
        lifecycle_program_snapshot_id=bundle.program.snapshot_id,
        lifecycle_program_id=bundle.program.program_id,
        lifecycle_branch_analysis_id=bundle.program.branch_analysis_id,
        hard_caps=_caps() if caps is None else caps,
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
    return owner_v3.initialize_h1_shared_cap_owner_v3(
        root,
        profile=profile,
        source_manifest=source,
        rejection_gate=gate,
    )


def _operands(bundle, *, magnitude: int = 10) -> dict[str, int]:
    return {
        row["site_key"]: (
            1
            if row["handler_mode"]
            == dispatch_v1.H1LifecycleHandlerModeV1.IMMEDIATE_UNIT.value
            else magnitude
        )
        for row in bundle.registry.handlers
        if row["reservation_edge"] is True
    }


def _session(root: Path, bundle, *, suffix: str, caps=None, magnitude: int = 10):
    owner = _owner(root, bundle, suffix=suffix, caps=caps)
    profile = dispatch_v1.bind_h1_lifecycle_dispatch_profile_v1(
        bundle,
        owner,
        site_reservation_uppers=_operands(bundle, magnitude=magnitude),
    )
    session = dispatch_v1.start_h1_lifecycle_construction_dispatch_v1(
        bundle, profile, owner
    )
    return session, profile, owner


def _success_callback(operation: str):
    if operation in {
        "STAGE_INPUT",
        "MOUNT_OPEN",
        "READ_INPUT",
        "READ_BUSINESS_RESULT",
        "OUTPUT_ROLE_READBACK",
        "SAME_OFD_PEAK_READ",
        "OUTPUT_FINALIZE",
    }:
        return lambda: 3
    return lambda: None


def _dispatch_success(session, *, through_ordinal: int) -> None:
    while len(session.events) < through_ordinal:
        row = session.bundle.program.transitions[len(session.events)]
        callback = (
            None
            if row["operation"] in {"MEMORY_BIND", "OUTPUT_RESERVE"}
            else _success_callback(row["operation"])
        )
        event = dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
            session, callback=callback
        )
        assert event.outcome == "SUCCESS"


def _append_exact_owner_tail(owner, *, suffix: str) -> None:
    reservation = owner_v3.reserve_h1_shared_cap_owner_v3(
        owner,
        operation_id=_id(f"prefix-tail-operation-{suffix}"),
        site_key=f"cleanup:prefix-tail:{suffix}",
        path="io.read_bytes",
        reservation_upper=2,
    )
    with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(owner, reservation):
        pass
    owner_v3.settle_h1_shared_cap_owner_v3(
        owner,
        reservation,
        value_basis=owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        native_observed_value=1,
        evidence_source_id=_id(f"prefix-tail-evidence-{suffix}"),
    )


def _resign_trace(document: dict) -> bytes:
    payload = copy.deepcopy(document)
    payload.pop("h1_lifecycle_dispatch_trace_id", None)
    payload["h1_lifecycle_dispatch_trace_id"] = content_id(
        dispatch_v1.DISPATCH_TRACE_DOMAIN, payload
    )
    return canonical_json_bytes(payload)


def _resign_event_in_trace(document: dict, index: int) -> bytes:
    payload = copy.deepcopy(document)
    event = payload["consumed_events"][index]
    old_event_id = event["h1_lifecycle_dispatch_event_id"]
    event.pop("h1_lifecycle_dispatch_event_id", None)
    event["h1_lifecycle_dispatch_event_id"] = content_id(
        dispatch_v1.DISPATCH_EVENT_DOMAIN, event
    )
    if payload["first_failure_event_id"] == old_event_id:
        payload["first_failure_event_id"] = event[
            "h1_lifecycle_dispatch_event_id"
        ]
    return _resign_trace(payload)


def test_anchor_registry_partition_and_authority_locks(bundle) -> None:
    registry = bundle.registry.to_document()
    program = bundle.program.to_document()
    assert registry["handler_count"] == 62
    assert registry["reservation_site_count"] == 48
    assert registry["immediate_settlement_site_count"] == 46
    assert registry["deferred_origin_site_count"] == 2
    assert registry["deferred_completion_site_count"] == 2
    assert registry["no_charge_control_site_count"] == 12
    assert registry["handler_mode_counts"] == {
        "IMMEDIATE_UNIT_SETTLEMENT": 5,
        "IMMEDIATE_MAGNITUDE_SETTLEMENT": 41,
        "DEFERRED_ORIGIN_ADMISSION_ONLY": 2,
        "DEFERRED_COMPLETION": 2,
        "NO_CHARGE_LIFECYCLE_CONTROL": 12,
    }
    assert program["transition_count"] == 62
    assert program["operation_family_count"] == 16
    assert program["declared_failure_edge_count"] == 143
    assert program["declared_branch_count"] == 144
    assert program["snapshot_loaded_from_verified_git_blob"] is True
    assert program["source_authority_present"] is False
    assert program["loaded_execution_bytes_verified"] is False
    assert program["cleanup_continuation_complete"] is False
    assert program["output_leaf_join_bound"] is False
    assert all(
        row["legacy_method_used_for_dispatch"] is False
        and row["legacy_owner_v2_method_semantic_identity_bound"] is False
        and row["native_evidence_authority_present"] is False
        and row["production_hook_bound"] is False
        for row in bundle.registry.handlers
    )
    with pytest.raises(ValueError, match="caller-pinned"):
        dispatch_v1.freeze_h1_anchored_lifecycle_dispatch_bundle_v1(
            REPOSITORY_ROOT,
            expected_anchor_id="0" * 64,
        )
    with pytest.raises(ValueError, match="verifier-issued"):
        dispatch_v1.H1AnchoredLifecycleHandlerRegistryV1(
            object(),
            bundle.program.provenance_id,
            bundle.program.snapshot_id,
            bundle.program.program_id,
            (),
        )


def test_candidate_crosscheck_rejects_loaded_source_path_crossing(
    bundle, monkeypatch
) -> None:
    monkeypatch.setattr(dispatch_v1.candidate_v1, "__file__", __file__)
    with pytest.raises(ValueError, match="loaded lifecycle candidate source"):
        dispatch_v1.freeze_h1_anchored_lifecycle_dispatch_bundle_v1(
            REPOSITORY_ROOT,
            expected_anchor_id=EXPECTED_ANCHOR_ID,
        )


def test_profile_freezes_exact_site_operands_and_rejects_identity_crossing(
    fast_root: Path, bundle
) -> None:
    owner = _owner(fast_root, bundle, suffix="profile")
    operands = _operands(bundle)
    missing = dict(operands)
    missing.pop(next(iter(missing)))
    with pytest.raises(ValueError, match="exactly 48"):
        dispatch_v1.bind_h1_lifecycle_dispatch_profile_v1(
            bundle, owner, site_reservation_uppers=missing
        )
    wrong_unit = dict(operands)
    wrong_unit["common:preflight-hash"] = 2
    with pytest.raises(ValueError, match="must equal one"):
        dispatch_v1.bind_h1_lifecycle_dispatch_profile_v1(
            bundle, owner, site_reservation_uppers=wrong_unit
        )
    profile = dispatch_v1.bind_h1_lifecycle_dispatch_profile_v1(
        bundle, owner, site_reservation_uppers=operands
    )
    assert profile.to_document()["site_operand_count"] == 48
    assert profile.to_document()["numeric_operand_authority_present"] is False
    foreign = _owner(fast_root, bundle, suffix="foreign")
    with pytest.raises(ValueError, match="crossed"):
        dispatch_v1.start_h1_lifecycle_construction_dispatch_v1(
            bundle, profile, foreign
        )
    assert owner_v3.replay_h1_shared_cap_owner_v3(foreign)["journal_sequence"] == 0


def test_full_62_site_dispatch_owner_pairing_and_independent_trace_replay(
    fast_root: Path, bundle
) -> None:
    session, profile, owner = _session(
        fast_root, bundle, suffix="full-success"
    )
    _dispatch_success(session, through_ordinal=62)
    assert len(session.events) == 62
    assert all(event.outcome == "SUCCESS" for event in session.events)
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    verified = dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
        trace.canonical_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
    )
    document = verified.to_document()
    assert document["full_declared_success_reached"] is True
    assert document["normal_dispatch_closed"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    replay = owner_v3.replay_h1_shared_cap_owner_v3(owner)
    assert replay["reservation_count"] == 48
    assert replay["settlement_count"] == 48
    assert set(replay["outstanding_values"].values()) == {0}
    owner_index = owner_v3.inspect_h1_shared_cap_owner_v3_record_index(owner)
    assert len(owner_index["record_ids_by_role"]["reservation"]) == 48
    assert owner_index["record_ids_by_role"]["rejection_admission"] == []
    assert len(owner_index["record_ids_by_role"]["settlement"]) == 48
    assert owner_index["gate_owner_join_verified"] is True
    assert owner_index["formal_counter_eligible"] is False
    by_site = {event.site_key: event.document for event in session.events}
    for origin, completion in (
        ("memory:bind-working-hierarchy", "memory:read-retained-same-ofd-peak"),
        ("output:reserve-route-wide", "output:finalize-route-wide"),
    ):
        assert by_site[origin]["callback_invocation_count"] == 0
        assert by_site[origin]["owner_record_refs"]["reservation_id"] == (
            by_site[completion]["owner_record_refs"]["reservation_id"]
        )
    with pytest.raises(ValueError, match="already closed"):
        dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
            session, callback=lambda: None
        )


def test_callback_failure_is_conservative_and_stops_normal_dispatch(
    fast_root: Path, bundle
) -> None:
    session, profile, owner = _session(
        fast_root, bundle, suffix="callback-failure"
    )
    _dispatch_success(session, through_ordinal=5)

    def fail() -> int:
        raise RuntimeError("injected stage failure")

    event = dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
        session, callback=fail
    )
    assert event.site_key == "stage:WORKER:sealed_runtime_archive"
    assert event.outcome == "CALLBACK_FAILED_AFTER_ADMISSION"
    assert event.document["value_basis"] == "CONSERVATIVE_RESERVATION_UPPER"
    assert event.document["callback_exception_type"] == "RuntimeError"
    replay = owner_v3.replay_h1_shared_cap_owner_v3(owner)
    assert replay["charged_values"]["io.staged_bytes"] == 10
    with pytest.raises(ValueError, match="already closed"):
        dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
            session, callback=lambda: 1
        )
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    assert (
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
            trace.canonical_bytes, bundle=bundle, profile=profile, owner=owner
        ).to_document()["declared_first_failure_replay_complete"]
        is True
    )


def test_callback_contract_preflight_and_invalid_magnitude_are_recoverable(
    fast_root: Path, bundle
) -> None:
    session, _profile, owner = _session(
        fast_root, bundle, suffix="callback-contract"
    )
    with pytest.raises(ValueError, match="forbids a callback"):
        dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
            session, callback=lambda: None
        )
    assert owner_v3.replay_h1_shared_cap_owner_v3(owner)["journal_sequence"] == 0
    dispatch_v1.dispatch_next_h1_lifecycle_site_v1(session)
    with pytest.raises(ValueError, match="requires one callback"):
        dispatch_v1.dispatch_next_h1_lifecycle_site_v1(session)
    assert owner_v3.replay_h1_shared_cap_owner_v3(owner)["journal_sequence"] == 1
    _dispatch_success(session, through_ordinal=5)
    event = dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
        session, callback=lambda: True
    )
    assert event.outcome == "CALLBACK_FAILED_AFTER_ADMISSION"
    assert event.document["callback_exception_type"] == (
        "InvalidNonnegativeMagnitudeResult"
    )
    replay = owner_v3.replay_h1_shared_cap_owner_v3(owner)
    assert replay["settlement_count"] == 4
    assert replay["recovery_required"] is False
    with pytest.raises(ValueError, match="already closed"):
        dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
            session, callback=lambda: 1
        )


def test_aggregate_cap_rejection_never_invokes_rejected_callback(
    fast_root: Path, bundle
) -> None:
    caps = _caps()
    caps["io.staged_bytes"] = 15
    session, profile, owner = _session(
        fast_root,
        bundle,
        suffix="cap-rejection",
        caps=caps,
        magnitude=10,
    )
    callback_count = 0
    while True:
        row = bundle.program.transitions[len(session.events)]

        def callback(operation=row["operation"]):
            nonlocal callback_count
            callback_count += 1
            return 3 if operation in {
                "STAGE_INPUT",
                "MOUNT_OPEN",
                "READ_INPUT",
                "READ_BUSINESS_RESULT",
                "OUTPUT_ROLE_READBACK",
                "SAME_OFD_PEAK_READ",
                "OUTPUT_FINALIZE",
            } else None

        before = callback_count
        event = dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
            session,
            callback=(
                None
                if row["operation"] in {"MEMORY_BIND", "OUTPUT_RESERVE"}
                else callback
            ),
        )
        if event.outcome != "SUCCESS":
            assert event.outcome == "CAP_REJECTED_BEFORE_SIDE_EFFECT"
            assert event.document["callback_invocation_count"] == 0
            assert callback_count == before
            break
    replay = owner_v3.replay_h1_shared_cap_owner_v3(owner)
    assert replay["control_cap_rejections"] == 1
    assert replay["gate_owner_join_verified"] is True
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
        trace.canonical_bytes, bundle=bundle, profile=profile, owner=owner
    )
    document = trace.to_document()
    refs = document["consumed_events"][-1]["owner_record_refs"]
    owner_index = owner_v3.inspect_h1_shared_cap_owner_v3_record_index(owner)
    assert refs["rejection_admission_id"] in (
        owner_index["record_ids_by_role"]["rejection_admission"]
    )
    assert refs["rejection_ack_id"] == owner_index["rejection_ack_id"]

    bad_ack = copy.deepcopy(document)
    bad_ack["consumed_events"][-1]["owner_record_refs"]["rejection_ack_id"] = (
        _id("foreign-rejection-ack")
    )
    with pytest.raises(ValueError, match="gate replay"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
            _resign_event_in_trace(bad_ack, len(bad_ack["consumed_events"]) - 1),
            bundle=bundle,
            profile=profile,
            owner=owner,
        )

    bad_admission = copy.deepcopy(document)
    bad_admission["consumed_events"][-1]["owner_record_refs"][
        "rejection_admission_id"
    ] = _id("foreign-rejection-admission")
    with pytest.raises(ValueError, match="absent Owner-V3 record"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
            _resign_event_in_trace(
                bad_admission, len(bad_admission["consumed_events"]) - 1
            ),
            bundle=bundle,
            profile=profile,
            owner=owner,
        )


def test_observed_overrun_is_not_clipped_and_poison_is_visible(
    fast_root: Path, bundle
) -> None:
    session, profile, owner = _session(fast_root, bundle, suffix="overrun")
    _dispatch_success(session, through_ordinal=5)
    event = dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
        session, callback=lambda: 11
    )
    assert event.outcome == "OBSERVED_UPPER_BOUND_VIOLATION"
    assert event.document["native_observed_value"] == 11
    assert event.document["value_basis"] == "OBSERVED_OVERRUN"
    replay = owner_v3.replay_h1_shared_cap_owner_v3(owner)
    assert replay["charged_values"]["io.staged_bytes"] == 11
    assert replay["observed_overrun_count"] == 1
    assert replay["new_work_allowed"] is False
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
        trace.canonical_bytes, bundle=bundle, profile=profile, owner=owner
    )


def test_mount_open_overrun_is_preserved_as_supplemental_protocol_abort(
    fast_root: Path, bundle
) -> None:
    session, profile, owner = _session(
        fast_root, bundle, suffix="mount-open-overrun"
    )
    _dispatch_success(session, through_ordinal=6)
    event = dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
        session, callback=lambda: 11
    )
    assert event.outcome == dispatch_v1.ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION
    assert event.document["anchored_transition_semantics_present"] is False
    assert event.document["supplemental_protocol_abort"] is True
    assert event.document["declared_first_failure"] is False
    assert event.document["native_observed_value"] == 11
    assert event.document["value_basis"] == "OBSERVED_OVERRUN"
    replay = owner_v3.replay_h1_shared_cap_owner_v3(owner)
    assert replay["charged_values"]["io.mounted_bytes_peak"] == 11
    assert replay["observed_overrun_count"] == 1
    assert replay["new_work_allowed"] is False
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    verified = dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
        trace.canonical_bytes, bundle=bundle, profile=profile, owner=owner
    )
    verified_document = verified.to_document()
    assert verified_document["declared_first_failure_replay_complete"] is False
    assert verified_document["first_failure_is_provisional_prefix_only"] is True
    assert verified_document["post_admission_protocol_abort_sites"] == [
        "mount-open:WORKER:sealed_runtime_archive"
    ]
    assert verified_document["active_mount_open_sites"] == [
        "mount-open:WORKER:sealed_runtime_archive"
    ]
    output_join = output_join_v1.build_h1_lifecycle_output_leaf_join_v1(bundle)
    analysis = cleanup_v1.derive_h1_lifecycle_complete_branch_analysis_v1(
        bundle, output_join
    )
    cleanup_pass = (
        cleanup_v1.select_h1_lifecycle_cleanup_pass_for_dispatch_trace_bytes_v1(
            analysis,
            trace.canonical_bytes,
            bundle=bundle,
            profile=profile,
            owner=owner,
        )
    )
    assert cleanup_pass.payload["branch_key"] == (
        "SUPPLEMENTAL:mount-open:WORKER:sealed_runtime_archive:"
        "ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION"
    )
    assert cleanup_pass.payload["runtime_trace_bound"] is False
    forged_declared = trace.to_document()
    forged_declared["consumed_events"][-1]["declared_first_failure"] = True
    with pytest.raises(ValueError, match="construction claim boundary"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
            _resign_event_in_trace(
                forged_declared, len(forged_declared["consumed_events"]) - 1
            ),
            bundle=bundle,
            profile=profile,
            owner=owner,
        )


def test_swallowed_dispatch_reentry_cannot_be_reported_as_success(
    fast_root: Path, bundle
) -> None:
    session, _profile, _owner_handle = _session(
        fast_root, bundle, suffix="reentry"
    )
    _dispatch_success(session, through_ordinal=1)

    def swallow_reentry() -> None:
        try:
            dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
                session, callback=lambda: None
            )
        except dispatch_v1.H1LifecycleDispatchProtocolFailureV1:
            pass

    event = dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
        session, callback=swallow_reentry
    )
    assert event.outcome == "CALLBACK_FAILED_AFTER_ADMISSION"
    assert event.document["callback_exception_type"] == (
        "H1LifecycleDispatchReentryViolation"
    )


def test_callable_drift_and_coherently_resigned_trace_tamper_fail_closed(
    fast_root: Path, bundle, monkeypatch
) -> None:
    session, profile, owner = _session(
        fast_root, bundle, suffix="callable-drift"
    )
    monkeypatch.setattr(
        owner_v3,
        "reserve_h1_shared_cap_owner_v3",
        lambda *args, **kwargs: None,
    )
    with pytest.raises(ValueError, match="entrypoint changed"):
        dispatch_v1.dispatch_next_h1_lifecycle_site_v1(session)
    assert owner_v3.replay_h1_shared_cap_owner_v3(owner)["journal_sequence"] == 0
    monkeypatch.undo()
    event = dispatch_v1.dispatch_next_h1_lifecycle_site_v1(session)
    assert event.outcome == "SUCCESS"
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    document = loads_canonical_json(trace.canonical_bytes)
    tampered = copy.deepcopy(document)
    tampered_event = tampered["consumed_events"][0]
    tampered_event["site_key"] = "invented:site"
    event_payload = dict(tampered_event)
    event_payload.pop("h1_lifecycle_dispatch_event_id")
    tampered_event["h1_lifecycle_dispatch_event_id"] = content_id(
        dispatch_v1.DISPATCH_EVENT_DOMAIN, event_payload
    )
    trace_payload = dict(tampered)
    trace_payload.pop("h1_lifecycle_dispatch_trace_id")
    tampered["h1_lifecycle_dispatch_trace_id"] = content_id(
        dispatch_v1.DISPATCH_TRACE_DOMAIN, trace_payload
    )
    with pytest.raises(ValueError, match="skipped, reordered, or rebound"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
            canonical_json_bytes(tampered),
            bundle=bundle,
            profile=profile,
            owner=owner,
        )


def test_trace_rejects_resigned_context_operand_role_swap_and_future_field(
    fast_root: Path, bundle
) -> None:
    session, profile, owner = _session(
        fast_root, bundle, suffix="semantic-tamper"
    )
    _dispatch_success(session, through_ordinal=2)
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    baseline = trace.to_document()

    context = copy.deepcopy(baseline)
    context["consumed_events"][1]["logical_occurrence_id"] = _id("foreign-occurrence")
    with pytest.raises(ValueError, match="skipped, reordered, or rebound"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
            _resign_event_in_trace(context, 1),
            bundle=bundle,
            profile=profile,
            owner=owner,
        )

    operand = copy.deepcopy(baseline)
    operand["consumed_events"][1]["reservation_upper"] = 0
    with pytest.raises(ValueError, match="frozen reservation operand"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
            _resign_event_in_trace(operand, 1),
            bundle=bundle,
            profile=profile,
            owner=owner,
        )

    swapped = copy.deepcopy(baseline)
    swapped["consumed_events"][1]["owner_record_refs"]["reservation_id"] = (
        swapped["consumed_events"][0]["owner_record_refs"]["reservation_id"]
    )
    with pytest.raises(ValueError, match="exact Owner-V3 reservation"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
            _resign_event_in_trace(swapped, 1),
            bundle=bundle,
            profile=profile,
            owner=owner,
        )

    future = copy.deepcopy(baseline)
    future["consumed_events"][1]["future_authority"] = True
    with pytest.raises(ValueError, match="non-object event"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
            _resign_event_in_trace(future, 1),
            bundle=bundle,
            profile=profile,
            owner=owner,
        )


def test_out_of_band_owner_append_is_rejected_before_dispatch_callback(
    fast_root: Path, bundle
) -> None:
    session, _profile, owner = _session(
        fast_root, bundle, suffix="out-of-band"
    )
    owner_v3.reserve_h1_shared_cap_owner_v3(
        owner,
        operation_id=_id("foreign-owner-operation"),
        site_key="foreign:site",
        path="io.read_bytes",
        reservation_upper=1,
    )
    called = 0

    def callback() -> None:
        nonlocal called
        called += 1

    with pytest.raises(ValueError, match="outside the dispatch event chain"):
        dispatch_v1.dispatch_next_h1_lifecycle_site_v1(session, callback=None)
    assert called == 0


def test_external_transaction_gate_closure_invalidates_dispatch_prefix(
    fast_root: Path, bundle
) -> None:
    session, _profile, first_owner = _session(
        fast_root, bundle, suffix="external-gate-close"
    )
    dispatch_v1.dispatch_next_h1_lifecycle_site_v1(session)

    caps = _caps()
    caps["common.hash_invocations"] = 0
    second_profile = owner_v3.freeze_h1_shared_cap_profile_core_v3(
        logical_occurrence_id=first_owner.profile.logical_occurrence_id,
        route_attempt_id=first_owner.profile.route_attempt_id,
        decision_point_id=_id("external-gate-close-second-decision"),
        transaction_id=_id("external-gate-close-second-transaction"),
        caller_pinned_lifecycle_provenance_id=bundle.program.provenance_id,
        lifecycle_program_snapshot_id=bundle.program.snapshot_id,
        lifecycle_program_id=bundle.program.program_id,
        lifecycle_branch_analysis_id=bundle.program.branch_analysis_id,
        hard_caps=caps,
    )
    second_source = owner_v3.freeze_h1_shared_cap_owner_v3_source_manifest(
        caller_pinned_lifecycle_provenance_id=bundle.program.provenance_id,
        lifecycle_program_snapshot_id=bundle.program.snapshot_id,
        lifecycle_program_id=bundle.program.program_id,
        lifecycle_branch_analysis_id=bundle.program.branch_analysis_id,
    )
    gate = rejection_v1.open_h1_attempt_rejection_gate_v1(
        first_owner.gate_directory,
        expected_gate_id=Path(first_owner.gate_directory).name,
    )
    second_owner = owner_v3.initialize_h1_shared_cap_owner_v3(
        fast_root,
        profile=second_profile,
        source_manifest=second_source,
        rejection_gate=gate,
    )
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        owner_v3.reserve_h1_shared_cap_owner_v3(
            second_owner,
            operation_id=_id("external-gate-close-operation"),
            site_key="external:cap-close",
            path="common.hash_invocations",
            reservation_upper=1,
        )
    first_index = owner_v3.inspect_h1_shared_cap_owner_v3_record_index(first_owner)
    assert first_index["gate_owner_join_status"] == (
        "EXTERNAL_ATTEMPT_REJECTION_ACKNOWLEDGED"
    )
    with pytest.raises(ValueError, match="attempt gate changed"):
        dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    with pytest.raises(ValueError, match="attempt gate changed"):
        dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
            session, callback=lambda: None
        )


def test_prefix_verifier_preserves_cutoff_across_exact_append_only_owner_tail(
    fast_root: Path, bundle
) -> None:
    assert dispatch_v1.PREFIX_VERIFICATION_ATTESTATION_ISSUED is False
    session, profile, owner = _session(
        fast_root, bundle, suffix="prefix-tail-valid"
    )
    _dispatch_success(session, through_ordinal=2)
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    cutoff = trace.to_document()

    dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
        trace.canonical_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
    )
    dispatch_v1.verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1(
        trace.canonical_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
    )

    _append_exact_owner_tail(owner, suffix="valid")
    current = owner_v3.inspect_h1_shared_cap_owner_v3_record_index(owner)
    assert current["journal_sequence"] == (
        cutoff["owner_journal_sequence_at_snapshot"] + 7
    )
    with pytest.raises(ValueError, match="terminal snapshot|record set"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_bytes_v1(
            trace.canonical_bytes,
            bundle=bundle,
            profile=profile,
            owner=owner,
        )
    verified = dispatch_v1.verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1(
        trace.canonical_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
    )
    assert verified.trace_id == trace.trace_id
    prefix = owner_v3.inspect_h1_shared_cap_owner_v3_record_prefix(
        owner,
        journal_sequence=cutoff["owner_journal_sequence_at_snapshot"],
        journal_head_id=cutoff["owner_journal_head_id_at_snapshot"],
    )
    assert prefix["append_only_tail_record_count"] == 7
    assert prefix["charged_values"] == cutoff["owner_charged_values_at_snapshot"]
    assert prefix["outstanding_values"] == cutoff[
        "owner_outstanding_values_at_snapshot"
    ]
    assert prefix["record_ids_by_role"] == cutoff[
        "owner_record_ids_at_snapshot"
    ]


def test_prefix_verifier_rejects_resigned_cutoff_and_runtime_crossing(
    fast_root: Path, bundle
) -> None:
    session, profile, owner = _session(
        fast_root, bundle, suffix="prefix-cutoff-tamper"
    )
    _dispatch_success(session, through_ordinal=2)
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    _append_exact_owner_tail(owner, suffix="tamper")

    tampered = trace.to_document()
    tampered["owner_charged_values_at_snapshot"]["io.read_bytes"] = 1
    with pytest.raises(ValueError, match="terminal snapshot"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1(
            _resign_trace(tampered),
            bundle=bundle,
            profile=profile,
            owner=owner,
        )

    foreign_session, _foreign_profile, foreign_owner = _session(
        fast_root, bundle, suffix="prefix-foreign-runtime"
    )
    _dispatch_success(foreign_session, through_ordinal=2)
    with pytest.raises(ValueError, match="cutoff head"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1(
            trace.canonical_bytes,
            bundle=bundle,
            profile=profile,
            owner=foreign_owner,
        )


def test_prefix_verifier_rejects_inserted_and_replaced_owner_records(
    fast_root: Path, bundle
) -> None:
    inserted_session, inserted_profile, inserted_owner = _session(
        fast_root, bundle, suffix="prefix-record-insertion"
    )
    _dispatch_success(inserted_session, through_ordinal=2)
    inserted_trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(
        inserted_session
    )
    _append_exact_owner_tail(inserted_owner, suffix="insertion")
    record_files = sorted(
        path
        for path in Path(inserted_owner.owner_directory).iterdir()
        if path.name[:8].isdigit() and path.suffix == ".json"
    )
    inserted = Path(inserted_owner.owner_directory) / (
        "00000001-" + "0" * 64 + ".json"
    )
    inserted.write_bytes(record_files[-1].read_bytes())
    inserted.chmod(0o600)
    with pytest.raises(ValueError, match="journal|filename|gap|duplicate"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1(
            inserted_trace.canonical_bytes,
            bundle=bundle,
            profile=inserted_profile,
            owner=inserted_owner,
        )

    replaced_session, replaced_profile, replaced_owner = _session(
        fast_root, bundle, suffix="prefix-record-replacement"
    )
    _dispatch_success(replaced_session, through_ordinal=2)
    replaced_trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(
        replaced_session
    )
    _append_exact_owner_tail(replaced_owner, suffix="replacement")
    replacement_files = sorted(
        path
        for path in Path(replaced_owner.owner_directory).iterdir()
        if path.name[:8].isdigit() and path.suffix == ".json"
    )
    replacement_files[0].chmod(0o600)
    replacement_files[0].write_bytes(replacement_files[-1].read_bytes())
    with pytest.raises(ValueError, match="journal|filename|identity|context"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1(
            replaced_trace.canonical_bytes,
            bundle=bundle,
            profile=replaced_profile,
            owner=replaced_owner,
        )


def test_prefix_verifier_rejects_transitive_owner_helper_drift(
    fast_root: Path, bundle, monkeypatch
) -> None:
    session, profile, owner = _session(
        fast_root, bundle, suffix="prefix-helper-drift"
    )
    _dispatch_success(session, through_ordinal=2)
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    monkeypatch.setattr(owner_v3, "_replay_records_fd", lambda *args, **kwargs: None)
    with pytest.raises(ValueError, match="prefix dependency"):
        dispatch_v1.verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1(
            trace.canonical_bytes,
            bundle=bundle,
            profile=profile,
            owner=owner,
        )
