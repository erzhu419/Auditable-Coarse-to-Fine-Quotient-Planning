from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading

import pytest

from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4
from acfqp.construction_k7_h1_domain_registry_extension_v1 import (
    K7_H1_DOMAIN_TAG_EXTENSION_V1,
)
from acfqp.phase3e_ids import loads_canonical_json


@pytest.fixture
def tmp_path() -> Path:
    path = Path(tempfile.mkdtemp(prefix="acfqp-owner-v4-wal-", dir="/tmp"))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _profile(suffix: str = "") -> owner_v3.H1SharedCapProfileCoreV3:
    return owner_v3.freeze_h1_shared_cap_profile_core_v3(
        logical_occurrence_id=_id(f"occurrence{suffix}"),
        route_attempt_id=_id(f"attempt{suffix}"),
        decision_point_id=_id(f"decision{suffix}"),
        transaction_id=_id(f"transaction{suffix}"),
        caller_pinned_lifecycle_provenance_id=_id(f"provenance{suffix}"),
        lifecycle_program_snapshot_id=_id(f"snapshot{suffix}"),
        lifecycle_program_id=_id(f"program{suffix}"),
        lifecycle_branch_analysis_id=_id(f"analysis{suffix}"),
        hard_caps={path: 10_000 for path in owner_v3.SHARED_RESOURCE_PATHS},
    )


def _source(
    profile: owner_v3.H1SharedCapProfileCoreV3,
) -> owner_v3.H1SharedCapOwnerV3SourceManifest:
    return owner_v3.freeze_h1_shared_cap_owner_v3_source_manifest(
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
        lifecycle_program_snapshot_id=profile.lifecycle_program_snapshot_id,
        lifecycle_program_id=profile.lifecycle_program_id,
        lifecycle_branch_analysis_id=profile.lifecycle_branch_analysis_id,
    )


def _owner(tmp_path: Path, suffix: str = "") -> owner_v4.H1SharedCapOwnerV4WalHandle:
    profile = _profile(suffix)
    gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=tmp_path,
        logical_occurrence_id=profile.logical_occurrence_id,
        route_attempt_id=profile.route_attempt_id,
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
    )
    gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(
        tmp_path, gate_spec
    )
    return owner_v4.initialize_h1_shared_cap_owner_v4_wal(
        tmp_path,
        profile=profile,
        source_manifest=_source(profile),
        rejection_gate=gate,
    )


def _historical_owner(
    tmp_path: Path,
    suffix: str,
) -> owner_v3.H1SharedCapOwnerV3Handle:
    profile = _profile(suffix)
    gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=tmp_path,
        logical_occurrence_id=profile.logical_occurrence_id,
        route_attempt_id=profile.route_attempt_id,
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
    )
    gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(
        tmp_path, gate_spec
    )
    return owner_v3.initialize_h1_shared_cap_owner_v3(
        tmp_path,
        profile=profile,
        source_manifest=_source(profile),
        rejection_gate=gate,
    )


def _two_historical_owners(
    tmp_path: Path,
    suffix: str,
) -> tuple[
    owner_v3.H1SharedCapOwnerV3Handle,
    owner_v3.H1SharedCapOwnerV3Handle,
]:
    occurrence = _id(f"two-occurrence{suffix}")
    attempt = _id(f"two-attempt{suffix}")
    provenance = _id(f"two-provenance{suffix}")

    def profile(index: int) -> owner_v3.H1SharedCapProfileCoreV3:
        return owner_v3.freeze_h1_shared_cap_profile_core_v3(
            logical_occurrence_id=occurrence,
            route_attempt_id=attempt,
            decision_point_id=_id(f"two-decision{suffix}-{index}"),
            transaction_id=_id(f"two-transaction{suffix}-{index}"),
            caller_pinned_lifecycle_provenance_id=provenance,
            lifecycle_program_snapshot_id=_id(f"two-snapshot{suffix}"),
            lifecycle_program_id=_id(f"two-program{suffix}"),
            lifecycle_branch_analysis_id=_id(f"two-analysis{suffix}"),
            hard_caps={path: 10_000 for path in owner_v3.SHARED_RESOURCE_PATHS},
        )

    first_profile = profile(1)
    second_profile = profile(2)
    gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=tmp_path,
        logical_occurrence_id=occurrence,
        route_attempt_id=attempt,
        caller_pinned_lifecycle_provenance_id=provenance,
    )
    gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(
        tmp_path, gate_spec
    )
    return (
        owner_v3.initialize_h1_shared_cap_owner_v3(
            tmp_path,
            profile=first_profile,
            source_manifest=_source(first_profile),
            rejection_gate=gate,
        ),
        owner_v3.initialize_h1_shared_cap_owner_v3(
            tmp_path,
            profile=second_profile,
            source_manifest=_source(second_profile),
            rejection_gate=gate,
        ),
    )


def _filesystem_manifest(root: Path) -> dict[str, tuple[str, int, bytes]]:
    result: dict[str, tuple[str, int, bytes]] = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        metadata = path.lstat()
        if path.is_file():
            result[relative] = ("FILE", metadata.st_mode, path.read_bytes())
        elif path.is_dir():
            result[relative] = ("DIRECTORY", metadata.st_mode, b"")
        else:
            result[relative] = ("OTHER", metadata.st_mode, b"")
    return result


def _reserve(
    handle: owner_v4.H1SharedCapOwnerV4WalHandle,
    label: str,
    upper: int = 8,
) -> owner_v3.H1SharedReservationV3:
    return owner_v4.reserve_h1_shared_cap_owner_v4_wal(
        handle,
        operation_id=_id(label),
        site_key=f"site:{label}",
        path="io.read_bytes",
        reservation_upper=upper,
    )


def _record_documents(handle: owner_v4.H1SharedCapOwnerV4WalHandle) -> list[dict]:
    return [
        loads_canonical_json(path.read_bytes())
        for path in sorted(Path(handle.owner_directory).glob("[0-9]*.json"))
    ]


def test_binding_is_registered_mandatory_reopenable_and_nonpromoting(
    tmp_path: Path,
) -> None:
    handle = _owner(tmp_path, "-binding")
    document = handle.to_document()
    assert handle.owner.pending_payload_wal_directory is not None
    assert Path(handle.owner.pending_payload_wal_directory).is_dir()
    assert document["pending_payload_wal_required"] is True
    assert document["historical_v3_claim_relabelled"] is False
    assert document["no_event_recovery_complete"] is False
    assert document["production_execution_authority_present"] is False
    assert document["formal_counter_record_issued"] is False
    assert document["formal_work_vector_issued"] is False
    assert document["formal_comparison_vector_issued"] is False
    assert document["formal_v7_route_authority_present"] is False
    assert document["official_execution_allowed"] is False
    assert "acfqp:construction-k7-h1-shared-cap-owner-v4-wal-binding:v1" in (
        K7_H1_DOMAIN_TAG_EXTENSION_V1
    )
    reopened = owner_v4.open_h1_shared_cap_owner_v4_wal(
        handle.owner_directory,
        expected_runtime_id=handle.runtime_id,
        gate_directory=handle.gate_directory,
    )
    assert reopened.binding_id == handle.binding_id
    assert owner_v4.replay_h1_shared_cap_owner_v4_wal(reopened)[
        "pending_payload_wal_replay_converged"
    ] is True


def test_wal_required_runtime_rejects_a_stripped_historical_handle(
    tmp_path: Path,
) -> None:
    handle = _owner(tmp_path, "-stripped")
    stripped = replace(
        handle.owner,
        pending_payload_wal_directory=None,
        pending_payload_wal_device=None,
        pending_payload_wal_inode=None,
        pending_payload_wal_binding_id=None,
    )
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="WAL-required Owner runtime",
    ):
        owner_v3.replay_h1_shared_cap_owner_v3(stripped)


def test_payload_wal_recovers_exact_callback_derived_evidence_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle = _owner(tmp_path, "-evidence-recovery")
    reservation = _reserve(handle, "evidence-recovery")
    with owner_v4.hold_h1_shared_cap_owner_v4_wal_side_effect(
        handle, reservation
    ):
        pass

    original_publish = owner_v3._publish_new
    matching_publications = 0

    def crash_on_evidence_journal(directory_fd: int, name: str, raw: bytes):
        nonlocal matching_publications
        try:
            document = loads_canonical_json(raw)
        except (TypeError, ValueError):
            document = {}
        if document.get("schema") == "acfqp.k7_h1_shared_cap_native_evidence.v3":
            matching_publications += 1
            if matching_publications == 2:
                raise RuntimeError("crash after evidence P before journal publication")
        return original_publish(directory_fd, name, raw)

    monkeypatch.setattr(owner_v3, "_publish_new", crash_on_evidence_journal)
    with pytest.raises(RuntimeError, match="evidence P"):
        owner_v4.settle_h1_shared_cap_owner_v4_wal(
            handle,
            reservation,
            value_basis=owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
            native_observed_value=5,
            evidence_source_id=_id("evidence-source"),
        )
    monkeypatch.setattr(owner_v3, "_publish_new", original_publish)

    replay = owner_v4.replay_h1_shared_cap_owner_v4_wal(handle)
    assert replay["pending_cursor"]["kind"] == "NOT_APPLICABLE"
    evidence = [
        row
        for row in _record_documents(handle)
        if (
            row["schema"] == "acfqp.k7_h1_shared_cap_native_evidence.v3"
            and row["h1_shared_cap_owner_v3_reservation_id"]
            == reservation.reservation_id
        )
    ]
    assert len(evidence) == 1
    assert evidence[0]["native_observed_value"] == 5
    assert evidence[0]["value_basis"] == (
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE.value
    )

    result = owner_v4.settle_h1_shared_cap_owner_v4_wal(
        handle,
        reservation,
        value_basis=owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        native_observed_value=5,
        evidence_source_id=_id("evidence-source"),
    )
    assert result.settlement_document["charged_value"] == 5


def test_orphan_payload_before_pending_cursor_is_removed_without_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle = _owner(tmp_path, "-orphan")
    original_link = owner_v3._link_cursor_state
    crashed = False

    def crash_before_pending(root_fd, runtime_id, state_kind, sequence, head_id):
        nonlocal crashed
        if state_kind == "P" and not crashed:
            crashed = True
            raise RuntimeError("crash after WAL before pending cursor")
        return original_link(root_fd, runtime_id, state_kind, sequence, head_id)

    monkeypatch.setattr(owner_v3, "_link_cursor_state", crash_before_pending)
    with pytest.raises(RuntimeError, match="before pending cursor"):
        _reserve(handle, "orphan")
    monkeypatch.setattr(owner_v3, "_link_cursor_state", original_link)
    replay = owner_v4.replay_h1_shared_cap_owner_v4_wal(handle)
    assert replay["journal_sequence"] == 7
    assert list(Path(handle.owner.pending_payload_wal_directory).iterdir()) == []
    assert _reserve(handle, "orphan").reservation_id


def test_committed_record_with_crash_before_wal_unlink_converges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle = _owner(tmp_path, "-committed-unlink")
    original_remove = owner_v3._remove_v4_wal_payload
    crashed = False

    def crash_before_remove(wal_fd: int, name: str) -> None:
        nonlocal crashed
        if not crashed:
            crashed = True
            raise RuntimeError("crash before WAL unlink")
        original_remove(wal_fd, name)

    monkeypatch.setattr(owner_v3, "_remove_v4_wal_payload", crash_before_remove)
    with pytest.raises(RuntimeError, match="before WAL unlink"):
        _reserve(handle, "committed-unlink")
    monkeypatch.setattr(owner_v3, "_remove_v4_wal_payload", original_remove)
    replay = owner_v4.replay_h1_shared_cap_owner_v4_wal(handle)
    assert replay["journal_sequence"] == 8
    assert list(Path(handle.owner.pending_payload_wal_directory).iterdir()) == []
    assert _reserve(handle, "committed-unlink").reservation_id


def test_pending_cursor_without_payload_is_explicitly_unrecoverable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle = _owner(tmp_path, "-missing-payload")
    original_publish = owner_v3._publish_new
    matching_publications = 0

    def delete_payload_then_crash(directory_fd: int, name: str, raw: bytes):
        nonlocal matching_publications
        try:
            document = loads_canonical_json(raw)
        except (TypeError, ValueError):
            document = {}
        if document.get("record_kind") == "RESERVATION_DURABLE":
            matching_publications += 1
            if matching_publications == 2:
                wal_directory = Path(handle.owner.pending_payload_wal_directory)
                for payload in wal_directory.iterdir():
                    payload.unlink()
                raise RuntimeError("crash after payload loss")
        return original_publish(directory_fd, name, raw)

    monkeypatch.setattr(owner_v3, "_publish_new", delete_payload_then_crash)
    with pytest.raises(RuntimeError, match="payload loss"):
        _reserve(handle, "missing-payload")
    monkeypatch.setattr(owner_v3, "_publish_new", original_publish)
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="UNRECOVERABLE_LEGACY_PENDING_APPEND_WITHOUT_PAYLOAD_WAL",
    ):
        owner_v4.replay_h1_shared_cap_owner_v4_wal(handle)


def test_binding_marker_rollback_cannot_downgrade_to_v3(tmp_path: Path) -> None:
    handle = _owner(tmp_path, "-marker-rollback")
    marker = Path(handle.owner.owner_root_realpath) / (
        owner_v3._v4_wal_binding_name(handle.runtime_id)
    )
    marker.unlink()

    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="activation namespace exists without its durable binding",
    ):
        owner_v3.open_h1_shared_cap_owner_v3(
            handle.owner_directory,
            expected_runtime_id=handle.runtime_id,
            gate_directory=handle.gate_directory,
        )

    repaired = owner_v4.open_h1_shared_cap_owner_v4_wal(
        handle.owner_directory,
        expected_runtime_id=handle.runtime_id,
        gate_directory=handle.gate_directory,
    )
    assert repaired.binding_id == handle.binding_id
    assert marker.is_file()


def test_binding_marker_and_namespace_deletion_still_cannot_downgrade(
    tmp_path: Path,
) -> None:
    handle = _owner(tmp_path, "-marker-and-namespace-rollback")
    root = Path(handle.owner.owner_root_realpath)
    (root / owner_v3._v4_wal_binding_name(handle.runtime_id)).unlink()
    Path(handle.owner.pending_payload_wal_directory).rmdir()

    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="activation intent lost its inode-bound namespace",
    ):
        owner_v3.open_h1_shared_cap_owner_v3(
            handle.owner_directory,
            expected_runtime_id=handle.runtime_id,
            gate_directory=handle.gate_directory,
        )


def test_legacy_pending_tail_refuses_upgrade_without_persistent_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    historical = _historical_owner(tmp_path, "-legacy-pending")
    original_publish = owner_v3._publish_new
    matching_publications = 0

    def crash_after_pending(directory_fd: int, name: str, raw: bytes):
        nonlocal matching_publications
        try:
            document = loads_canonical_json(raw)
        except (TypeError, ValueError):
            document = {}
        if document.get("record_kind") == "RESERVATION_DURABLE":
            matching_publications += 1
            if matching_publications == 1:
                raise RuntimeError("legacy crash after P")
        return original_publish(directory_fd, name, raw)

    monkeypatch.setattr(owner_v3, "_publish_new", crash_after_pending)
    with pytest.raises(RuntimeError, match="legacy crash after P"):
        owner_v3.reserve_h1_shared_cap_owner_v3(
            historical,
            operation_id=_id("legacy-pending"),
            site_key="site:legacy-pending",
            path="io.read_bytes",
            reservation_upper=1,
        )
    monkeypatch.setattr(owner_v3, "_publish_new", original_publish)

    root = Path(historical.owner_root_realpath)
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="fully converged historical V3 tail",
    ):
        owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(historical)
    assert not (root / owner_v3._v4_wal_binding_name(historical.runtime_id)).exists()
    assert not (root / owner_v3._v4_wal_directory_name(historical.runtime_id)).exists()

    recovered = owner_v3.reserve_h1_shared_cap_owner_v3(
        historical,
        operation_id=_id("legacy-pending"),
        site_key="site:legacy-pending",
        path="io.read_bytes",
        reservation_upper=1,
    )
    assert recovered.reservation_id


def test_wal_temporary_file_is_removed_during_replay(tmp_path: Path) -> None:
    handle = _owner(tmp_path, "-wal-temp")
    wal = Path(handle.owner.pending_payload_wal_directory)
    temporary = wal / (".tmp-999-" + "a" * 32)
    temporary.write_bytes(b"partial")
    temporary.chmod(0o600)
    assert temporary.exists()
    owner_v4.replay_h1_shared_cap_owner_v4_wal(handle)
    assert not temporary.exists()


def test_local_rejection_refuses_activation_without_any_owner_mutation(
    tmp_path: Path,
) -> None:
    historical = _historical_owner(tmp_path, "-closed-local")
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        owner_v3.reserve_h1_shared_cap_owner_v3(
            historical,
            operation_id=_id("closed-local-rejection"),
            site_key="site:closed-local-rejection",
            path="io.read_bytes",
            reservation_upper=10_001,
        )
    root = Path(historical.owner_root_realpath)
    before = _filesystem_manifest(root)
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="attempt gate to remain OPEN",
    ):
        owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(historical)
    assert _filesystem_manifest(root) == before


def test_external_same_gate_rejection_refuses_activation_without_mutation(
    tmp_path: Path,
) -> None:
    rejecting, candidate = _two_historical_owners(tmp_path, "-closed-external")
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        owner_v3.reserve_h1_shared_cap_owner_v3(
            rejecting,
            operation_id=_id("closed-external-rejection"),
            site_key="site:closed-external-rejection",
            path="io.read_bytes",
            reservation_upper=10_001,
        )
    root = Path(candidate.owner_root_realpath)
    before = _filesystem_manifest(root)
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="attempt gate to remain OPEN",
    ):
        owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(candidate)
    assert _filesystem_manifest(root) == before


def test_observed_overrun_refuses_activation_without_mutation(
    tmp_path: Path,
) -> None:
    historical = _historical_owner(tmp_path, "-overrun-poison")
    reservation = owner_v3.reserve_h1_shared_cap_owner_v3(
        historical,
        operation_id=_id("overrun-poison"),
        site_key="site:overrun-poison",
        path="io.read_bytes",
        reservation_upper=1,
    )
    with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(
        historical, reservation
    ):
        pass
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ObservedOverrun):
        owner_v3.settle_h1_shared_cap_owner_v3(
            historical,
            reservation,
            value_basis=owner_v3.H1SharedValueBasisV3.OBSERVED_OVERRUN,
            native_observed_value=2,
            evidence_source_id=_id("overrun-poison-evidence"),
        )
    root = Path(historical.owner_root_realpath)
    before = _filesystem_manifest(root)
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="poisoned by overrun",
    ):
        owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(historical)
    assert _filesystem_manifest(root) == before


def test_settled_intent_recovers_marker_after_later_external_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rejecting, candidate = _two_historical_owners(
        tmp_path, "-recover-after-rejection"
    )
    original_publish = owner_v3._publish_v4_wal_binding

    def crash_at_binding(directory_fd: int, runtime_id: str, raw: bytes):
        if runtime_id == candidate.runtime_id:
            raise RuntimeError("crash before binding marker")
        return original_publish(directory_fd, runtime_id, raw)

    monkeypatch.setattr(owner_v3, "_publish_v4_wal_binding", crash_at_binding)
    with pytest.raises(RuntimeError, match="before binding marker"):
        owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(candidate)
    monkeypatch.setattr(owner_v3, "_publish_v4_wal_binding", original_publish)

    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        owner_v3.reserve_h1_shared_cap_owner_v3(
            rejecting,
            operation_id=_id("later-external-rejection"),
            site_key="site:later-external-rejection",
            path="io.read_bytes",
            reservation_upper=10_001,
        )
    recovered = owner_v4.open_h1_shared_cap_owner_v4_wal(
        candidate.owner_directory,
        expected_runtime_id=candidate.runtime_id,
        gate_directory=candidate.gate_directory,
    )
    assert recovered.binding_id
    assert owner_v4.replay_h1_shared_cap_owner_v4_wal(recovered)[
        "journal_sequence"
    ] == 7


def test_public_initialize_recovers_crash_before_binding_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    historical = _historical_owner(tmp_path, "-public-initialize-recovery")
    gate = rejection_v1.open_h1_attempt_rejection_gate_v1(
        historical.gate_directory,
        expected_gate_id=Path(historical.gate_directory).name,
    )
    original_publish = owner_v3._publish_v4_wal_binding

    def crash_at_binding(directory_fd: int, runtime_id: str, raw: bytes):
        if runtime_id == historical.runtime_id:
            raise RuntimeError("public initialize crash before binding marker")
        return original_publish(directory_fd, runtime_id, raw)

    monkeypatch.setattr(owner_v3, "_publish_v4_wal_binding", crash_at_binding)
    with pytest.raises(RuntimeError, match="before binding marker"):
        owner_v4.initialize_h1_shared_cap_owner_v4_wal(
            tmp_path,
            profile=historical.profile,
            source_manifest=historical.source_manifest,
            rejection_gate=gate,
        )
    monkeypatch.setattr(owner_v3, "_publish_v4_wal_binding", original_publish)

    recovered = owner_v4.initialize_h1_shared_cap_owner_v4_wal(
        tmp_path,
        profile=historical.profile,
        source_manifest=historical.source_manifest,
        rejection_gate=gate,
    )
    replay = owner_v4.replay_h1_shared_cap_owner_v4_wal(recovered)
    assert recovered.binding_id
    assert replay["journal_sequence"] == 7
    assert replay["pending_cursor"]["kind"] == "NOT_APPLICABLE"


def test_preintent_namespace_crash_rolls_back_even_after_external_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rejecting, candidate = _two_historical_owners(
        tmp_path, "-preintent-rollback-after-rejection"
    )
    gate = rejection_v1.open_h1_attempt_rejection_gate_v1(
        candidate.gate_directory,
        expected_gate_id=Path(candidate.gate_directory).name,
    )
    original_reservation_document = owner_v3._reservation_document_for_request

    def crash_before_intent(*args, **kwargs):
        if kwargs.get("site_key") == owner_v3._V4_WAL_BINDING_SITE_KEY:
            raise RuntimeError("crash after WAL namespace before activation intent")
        return original_reservation_document(*args, **kwargs)

    monkeypatch.setattr(
        owner_v3,
        "_reservation_document_for_request",
        crash_before_intent,
    )
    with pytest.raises(RuntimeError, match="before activation intent"):
        owner_v4.initialize_h1_shared_cap_owner_v4_wal(
            tmp_path,
            profile=candidate.profile,
            source_manifest=candidate.source_manifest,
            rejection_gate=gate,
        )
    wal_path = Path(candidate.owner_root_realpath) / (
        owner_v3._v4_wal_directory_name(candidate.runtime_id)
    )
    assert wal_path.is_dir()
    monkeypatch.setattr(
        owner_v3,
        "_reservation_document_for_request",
        original_reservation_document,
    )

    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        owner_v3.reserve_h1_shared_cap_owner_v3(
            rejecting,
            operation_id=_id("preintent-later-external-rejection"),
            site_key="site:preintent-later-external-rejection",
            path="io.read_bytes",
            reservation_upper=10_001,
        )
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="attempt gate to remain OPEN",
    ):
        owner_v4.initialize_h1_shared_cap_owner_v4_wal(
            tmp_path,
            profile=candidate.profile,
            source_manifest=candidate.source_manifest,
            rejection_gate=gate,
        )
    assert not wal_path.exists()
    historical = owner_v3.open_h1_shared_cap_owner_v3(
        candidate.owner_directory,
        expected_runtime_id=candidate.runtime_id,
        gate_directory=candidate.gate_directory,
    )
    assert historical.pending_payload_wal_binding_id is None


def test_stale_historical_handle_hydrates_completed_activation(
    tmp_path: Path,
) -> None:
    historical = _historical_owner(tmp_path, "-stale-handle")
    stale = owner_v3.open_h1_shared_cap_owner_v3(
        historical.owner_directory,
        expected_runtime_id=historical.runtime_id,
        gate_directory=historical.gate_directory,
    )
    first = owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(
        historical
    )
    second = owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(stale)
    assert second.pending_payload_wal_binding_id == (
        first.pending_payload_wal_binding_id
    )


@pytest.mark.parametrize(
    "phase",
    (
        "WAL_TEMP_BEFORE_LINK",
        "WAL_LINK_BEFORE_PENDING",
        "PENDING_BEFORE_JOURNAL",
        "JOURNAL_BEFORE_COMMITTED",
        "COMMITTED_BEFORE_CURSOR_CLEANUP",
        "COMMITTED_BEFORE_WAL_UNLINK",
    ),
)
def test_sigkill_reservation_phase_replay_converges(
    tmp_path: Path,
    phase: str,
) -> None:
    handle = _owner(tmp_path, f"-sigkill-{phase}")
    label = f"sigkill-{phase}"
    child = r'''
import os
import re
import signal
import sys
from acfqp import construction_k7_h1_shared_cap_owner_v3 as v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as v4

owner_directory, runtime_id, gate_directory, phase, operation_id, site_key = sys.argv[1:]
handle = v4.open_h1_shared_cap_owner_v4_wal(
    owner_directory,
    expected_runtime_id=runtime_id,
    gate_directory=gate_directory,
)
kill = lambda: os.kill(os.getpid(), signal.SIGKILL)
if phase == "WAL_TEMP_BEFORE_LINK":
    original = v3.os.link
    def link(src, dst, *args, **kwargs):
        if str(src).startswith(".tmp-") and str(dst).startswith("pending-"):
            kill()
        return original(src, dst, *args, **kwargs)
    v3.os.link = link
elif phase == "WAL_LINK_BEFORE_PENDING":
    original = v3._link_cursor_state
    def link_cursor(root_fd, runtime, kind, sequence, head):
        if kind == "P" and sequence > 7:
            kill()
        return original(root_fd, runtime, kind, sequence, head)
    v3._link_cursor_state = link_cursor
elif phase == "PENDING_BEFORE_JOURNAL":
    original = v3._publish_new
    def publish(directory_fd, name, raw):
        if re.fullmatch(r"[0-9]{8}-[0-9a-f]{64}[.]json", name):
            kill()
        return original(directory_fd, name, raw)
    v3._publish_new = publish
elif phase == "JOURNAL_BEFORE_COMMITTED":
    original = v3._link_cursor_state
    def link_cursor(root_fd, runtime, kind, sequence, head):
        if kind == "C" and sequence > 7:
            kill()
        return original(root_fd, runtime, kind, sequence, head)
    v3._link_cursor_state = link_cursor
elif phase == "COMMITTED_BEFORE_CURSOR_CLEANUP":
    original = v3._unlink_cursor_state
    def unlink_cursor(root_fd, name):
        if "-P-00000008-" in name:
            kill()
        return original(root_fd, name)
    v3._unlink_cursor_state = unlink_cursor
elif phase == "COMMITTED_BEFORE_WAL_UNLINK":
    original = v3._remove_v4_wal_payload
    def remove(wal_fd, name):
        kill()
    v3._remove_v4_wal_payload = remove
else:
    raise AssertionError(phase)
v4.reserve_h1_shared_cap_owner_v4_wal(
    handle,
    operation_id=operation_id,
    site_key=site_key,
    path="io.read_bytes",
    reservation_upper=1,
)
raise AssertionError("kill point not reached")
'''
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            child,
            handle.owner_directory,
            handle.runtime_id,
            handle.gate_directory,
            phase,
            _id(label),
            f"site:{label}",
        ],
        check=False,
    )
    assert completed.returncode == -signal.SIGKILL

    reopened = owner_v4.open_h1_shared_cap_owner_v4_wal(
        handle.owner_directory,
        expected_runtime_id=handle.runtime_id,
        gate_directory=handle.gate_directory,
    )
    replay = owner_v4.replay_h1_shared_cap_owner_v4_wal(reopened)
    assert replay["pending_cursor"]["kind"] == "NOT_APPLICABLE"
    assert list(Path(reopened.owner.pending_payload_wal_directory).iterdir()) == []
    reservation = owner_v4.reserve_h1_shared_cap_owner_v4_wal(
        reopened,
        operation_id=_id(label),
        site_key=f"site:{label}",
        path="io.read_bytes",
        reservation_upper=1,
    )
    assert reservation.reservation_id
    assert owner_v4.replay_h1_shared_cap_owner_v4_wal(reopened)[
        "journal_sequence"
    ] == 8


def test_sigkill_root_binding_temp_is_scoped_cleaned_and_recovered(
    tmp_path: Path,
) -> None:
    historical = _historical_owner(tmp_path, "-root-binding-sigkill")
    child = r'''
import os
import signal
import sys
from acfqp import construction_k7_h1_shared_cap_owner_v3 as v3

owner_directory, runtime_id, gate_directory = sys.argv[1:]
handle = v3.open_h1_shared_cap_owner_v3(
    owner_directory,
    expected_runtime_id=runtime_id,
    gate_directory=gate_directory,
)
original = v3.os.link
def link(src, dst, *args, **kwargs):
    if str(src).startswith(".tmp-v4-wal-binding-"):
        os.kill(os.getpid(), signal.SIGKILL)
    return original(src, dst, *args, **kwargs)
v3.os.link = link
v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(handle)
raise AssertionError("kill point not reached")
'''
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            child,
            historical.owner_directory,
            historical.runtime_id,
            historical.gate_directory,
        ],
        check=False,
    )
    assert completed.returncode == -signal.SIGKILL
    root = Path(historical.owner_root_realpath)
    prefix = owner_v3._v4_wal_binding_temp_prefix(historical.runtime_id)
    assert any(path.name.startswith(prefix) for path in root.iterdir())

    recovered = owner_v4.open_h1_shared_cap_owner_v4_wal(
        historical.owner_directory,
        expected_runtime_id=historical.runtime_id,
        gate_directory=historical.gate_directory,
    )
    assert owner_v4.replay_h1_shared_cap_owner_v4_wal(recovered)[
        "journal_sequence"
    ] == 7
    assert not any(path.name.startswith(prefix) for path in root.iterdir())


def test_concurrent_initializers_converge_to_one_binding(tmp_path: Path) -> None:
    historical = _historical_owner(tmp_path, "-concurrent-initializers")
    barrier = tmp_path / "start-concurrent-initializers"
    child = r'''
import sys
import time
from pathlib import Path
from acfqp import construction_k7_h1_shared_cap_owner_v3 as v3

owner_directory, runtime_id, gate_directory, barrier = sys.argv[1:]
while not Path(barrier).exists():
    time.sleep(0.001)
handle = v3.open_h1_shared_cap_owner_v3(
    owner_directory,
    expected_runtime_id=runtime_id,
    gate_directory=gate_directory,
    _allow_v4_activation_recovery=True,
)
upgraded = v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(handle)
print(upgraded.pending_payload_wal_binding_id, flush=True)
'''
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                child,
                historical.owner_directory,
                historical.runtime_id,
                historical.gate_directory,
                str(barrier),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(4)
    ]
    barrier.touch()
    results = [process.communicate(timeout=30) for process in processes]
    assert [process.returncode for process in processes] == [0, 0, 0, 0], results
    binding_ids = {stdout.strip() for stdout, _stderr in results}
    assert len(binding_ids) == 1
    assert next(iter(binding_ids))
    reopened = owner_v4.open_h1_shared_cap_owner_v4_wal(
        historical.owner_directory,
        expected_runtime_id=historical.runtime_id,
        gate_directory=historical.gate_directory,
    )
    assert reopened.binding_id == next(iter(binding_ids))


def test_concurrent_public_initializers_converge_to_one_binding(
    tmp_path: Path,
) -> None:
    historical = _historical_owner(tmp_path, "-concurrent-public-initializers")
    gate = rejection_v1.open_h1_attempt_rejection_gate_v1(
        historical.gate_directory,
        expected_gate_id=Path(historical.gate_directory).name,
    )
    barrier = threading.Barrier(4)

    def initialize() -> owner_v4.H1SharedCapOwnerV4WalHandle:
        barrier.wait(timeout=10)
        return owner_v4.initialize_h1_shared_cap_owner_v4_wal(
            tmp_path,
            profile=historical.profile,
            source_manifest=historical.source_manifest,
            rejection_gate=gate,
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        handles = list(executor.map(lambda _index: initialize(), range(4)))

    assert len({handle.binding_id for handle in handles}) == 1
    assert all(
        owner_v4.replay_h1_shared_cap_owner_v4_wal(handle)[
            "journal_sequence"
        ]
        == 7
        for handle in handles
    )


def test_historical_v3_runtime_remains_without_v4_claim(tmp_path: Path) -> None:
    historical = _historical_owner(tmp_path, "-historical")
    assert historical.pending_payload_wal_directory is None
    assert owner_v3.replay_h1_shared_cap_owner_v3(historical)[
        "journal_sequence"
    ] == 0
    with pytest.raises(owner_v4.ConstructionK7H1SharedCapOwnerV4WalError):
        owner_v4.open_h1_shared_cap_owner_v4_wal(
            historical.owner_directory,
            expected_runtime_id=historical.runtime_id,
            gate_directory=historical.gate_directory,
        )
