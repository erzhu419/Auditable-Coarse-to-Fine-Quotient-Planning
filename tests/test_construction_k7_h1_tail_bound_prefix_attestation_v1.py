from __future__ import annotations

import contextlib
import hashlib
from pathlib import Path
import shutil
import tempfile

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4
from acfqp import construction_k7_h1_tail_bound_prefix_attestation_v1 as tail_v1


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANCHOR_ID = (
    "4a4b0d1888f0ac18123e4163e1a26b0583a64946d2eb219e02d4b77dc0a3e327"
)


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
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-tail-attestation-", dir=base))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _session(root: Path, bundle, *, suffix: str):
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
    gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(
        root, gate_spec
    )
    owner = owner_v3.initialize_h1_shared_cap_owner_v3(
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
        owner,
        site_reservation_uppers=uppers,
    )
    session = dispatch_v1.start_h1_lifecycle_construction_dispatch_v1(
        bundle, dispatch_profile, owner
    )
    return session, dispatch_profile, owner


def _upgrade(owner: owner_v3.H1SharedCapOwnerV3Handle):
    upgraded = owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(
        owner
    )
    return owner_v4.open_h1_shared_cap_owner_v4_wal(
        upgraded.owner_directory,
        expected_runtime_id=upgraded.runtime_id,
        gate_directory=upgraded.gate_directory,
    )


def _append_tail(owner: owner_v4.H1SharedCapOwnerV4WalHandle, suffix: str) -> None:
    reservation = owner_v4.reserve_h1_shared_cap_owner_v4_wal(
        owner,
        operation_id=_id(f"tail-operation-{suffix}"),
        site_key=f"cleanup:tail:{suffix}",
        path="io.read_bytes",
        reservation_upper=2,
    )
    with owner_v4.hold_h1_shared_cap_owner_v4_wal_side_effect(
        owner, reservation
    ):
        pass
    owner_v4.settle_h1_shared_cap_owner_v4_wal(
        owner,
        reservation,
        value_basis=owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        native_observed_value=1,
        evidence_source_id=_id(f"tail-evidence-{suffix}"),
    )


def test_semantic_closure_is_self_consistent_and_live_identity_bound() -> None:
    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    repeated = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    assert repeated.closure_id == candidate.closure_id
    frozen = tail_v1.freeze_h1_prefix_verifier_semantic_closure_v1(
        expected_closure_id=candidate.closure_id
    )
    assert tail_v1._require_live_semantic_closure(frozen) is frozen
    document = frozen.to_document()
    assert document["closure_complete_for_registered_python_dependencies"] is True
    assert document["runtime_object_identity_retained"] is True
    assert document["cross_process_source_authority_present"] is False
    assert document["production_execution_authority_present"] is False
    assert document["official_execution_allowed"] is False


def test_semantic_closure_rejects_helper_global_and_sentinel_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    monkeypatch.setattr(dispatch_v1, "_TRACE_ISSUER", object())
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)
    monkeypatch.undo()

    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    monkeypatch.setattr(
        dispatch_v1.H1LifecycleDispatchTraceV1,
        "__init__",
        lambda _self, *_args, **_kwargs: None,
    )
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)
    monkeypatch.undo()

    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    monkeypatch.setattr(
        contextlib._GeneratorContextManager,
        "__enter__",
        lambda _self: None,
    )
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)
    monkeypatch.undo()

    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    monkeypatch.setattr(
        owner_v4,
        "replay_h1_shared_cap_owner_v4_wal",
        lambda _owner: {"gate_state": "FORGED"},
    )
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)
    monkeypatch.undo()

    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    monkeypatch.setattr(tail_v1, "_ordered_owner_records", lambda _index: [])
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)
    monkeypatch.undo()

    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    original_activate = rejection_v1._activate_gate_context

    def replacement_activate(*args, **kwargs):
        return original_activate(*args, **kwargs)

    replacement_activate.__module__ = original_activate.__module__
    replacement_activate.__qualname__ = original_activate.__qualname__
    monkeypatch.setattr(
        rejection_v1,
        "_activate_gate_context",
        replacement_activate,
    )
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)
    monkeypatch.undo()

    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    monkeypatch.setattr(owner_v3, "_record_id", lambda _row: "0" * 64)
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)
    monkeypatch.undo()

    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    monkeypatch.setitem(owner_v3._RECORD_META, "attack.schema", ("x", "y"))
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)
    monkeypatch.undo()

    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    monkeypatch.setattr(owner_v3.fcntl, "flock", lambda *_args: None)
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)
    monkeypatch.undo()

    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    monkeypatch.setattr(owner_v3.Path, "is_absolute", lambda _self: True)
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)
    monkeypatch.undo()

    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    monkeypatch.setattr(
        rejection_v1.H1AttemptRejectionGateReplaySnapshotV1,
        "acknowledgement_id",
        property(lambda _self: "0" * 64),
    )
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)
    monkeypatch.undo()

    candidate = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    original = dispatch_v1._OWNER_ENTRYPOINTS["index"]

    def replacement(*args, **kwargs):
        return original(*args, **kwargs)

    replacement.__module__ = original.__module__
    replacement.__qualname__ = original.__qualname__
    monkeypatch.setitem(dispatch_v1._OWNER_ENTRYPOINTS, "index", replacement)
    with pytest.raises(tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error):
        tail_v1._require_live_semantic_closure(candidate)


def test_observed_tail_attestation_invalidates_then_extends(
    fast_root: Path,
    bundle,
) -> None:
    session, profile, historical = _session(
        fast_root, bundle, suffix="extension"
    )
    first_event = dispatch_v1.dispatch_next_h1_lifecycle_site_v1(
        session, callback=None
    )
    assert first_event.outcome == "SUCCESS"
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    owner = _upgrade(historical)
    closure = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    first_tail = owner_v4.replay_h1_shared_cap_owner_v4_wal(owner)
    first = tail_v1.issue_h1_tail_bound_prefix_attestation_v1(
        trace.canonical_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
        semantic_closure=closure,
        expected_tail_sequence=first_tail["journal_sequence"],
        expected_tail_head_id=first_tail["journal_head_id"],
    )
    assert first.payload["prefix_last_event_id"] == first_event.event_id
    assert first.payload["prefix_first_failure_event_id"]["kind"] == (
        "NOT_APPLICABLE"
    )
    assert first.payload["verification_scope"] == (
        "EXACT_TAIL_OBSERVED_DURING_ISSUANCE"
    )
    assert first.payload["atomic_future_consumer_lease_present"] is False
    assert first.payload["future_append_validity"] is False
    tail_v1.verify_h1_tail_bound_prefix_attestation_exact_current_bytes_v1(
        first.canonical_bytes,
        trace.canonical_bytes,
        expected_attestation_id=first.attestation_id,
        bundle=bundle,
        profile=profile,
        owner=owner,
        semantic_closure=closure,
        expected_tail_sequence=first_tail["journal_sequence"],
        expected_tail_head_id=first_tail["journal_head_id"],
    )

    _append_tail(owner, "extension")
    second_tail = owner_v4.replay_h1_shared_cap_owner_v4_wal(owner)
    with pytest.raises(
        tail_v1.ConstructionK7H1TailBoundPrefixAttestationV1Error,
        match="current tail differs",
    ):
        tail_v1.verify_h1_tail_bound_prefix_attestation_exact_current_bytes_v1(
            first.canonical_bytes,
            trace.canonical_bytes,
            expected_attestation_id=first.attestation_id,
            bundle=bundle,
            profile=profile,
            owner=owner,
            semantic_closure=closure,
            expected_tail_sequence=first_tail["journal_sequence"],
            expected_tail_head_id=first_tail["journal_head_id"],
        )

    second = tail_v1.extend_h1_tail_bound_prefix_attestation_v1(
        first,
        trace.canonical_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
        semantic_closure=closure,
        expected_tail_sequence=second_tail["journal_sequence"],
        expected_tail_head_id=second_tail["journal_head_id"],
    )
    assert second.payload[
        "predecessor_h1_tail_bound_prefix_attestation_id"
    ] == first.attestation_id
    assert second.payload["current_tail_ordered_record_ids"][: first_tail[
        "journal_sequence"
    ]] == first.payload["current_tail_ordered_record_ids"]
    tail_v1.verify_h1_tail_bound_prefix_attestation_extension_observed_current_bytes_v1(
        second.canonical_bytes,
        first,
        trace.canonical_bytes,
        expected_attestation_id=second.attestation_id,
        bundle=bundle,
        profile=profile,
        owner=owner,
        semantic_closure=closure,
        expected_tail_sequence=second_tail["journal_sequence"],
        expected_tail_head_id=second_tail["journal_head_id"],
    )


def test_empty_prefix_uses_typed_null_last_event(fast_root: Path, bundle) -> None:
    session, profile, historical = _session(
        fast_root, bundle, suffix="empty-prefix"
    )
    trace = dispatch_v1.snapshot_h1_lifecycle_dispatch_trace_v1(session)
    owner = _upgrade(historical)
    closure = tail_v1.inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    replay = owner_v4.replay_h1_shared_cap_owner_v4_wal(owner)
    attestation = tail_v1.issue_h1_tail_bound_prefix_attestation_v1(
        trace.canonical_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
        semantic_closure=closure,
        expected_tail_sequence=replay["journal_sequence"],
        expected_tail_head_id=replay["journal_head_id"],
    )
    assert attestation.payload["prefix_last_event_id"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "DISPATCH_PREFIX_HAS_NO_EVENTS",
    }
