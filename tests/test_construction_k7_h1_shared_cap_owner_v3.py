from __future__ import annotations

import hashlib
import multiprocessing
from pathlib import Path
import shutil
import tempfile
import threading
from typing import Any

import pytest

from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, loads_canonical_json


@pytest.fixture
def tmp_path() -> Path:
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-owner-v3-", dir="/tmp"))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _caps(default: int = 1_000) -> dict[str, int]:
    return {path: default for path in owner_v3.SHARED_RESOURCE_PATHS}


def _profile(*, caps: dict[str, int] | None = None, suffix: str = ""):
    return owner_v3.freeze_h1_shared_cap_profile_core_v3(
        logical_occurrence_id=_id(f"occurrence{suffix}"),
        route_attempt_id=_id(f"attempt{suffix}"),
        decision_point_id=_id(f"decision{suffix}"),
        transaction_id=_id(f"transaction{suffix}"),
        caller_pinned_lifecycle_provenance_id=_id(f"provenance{suffix}"),
        lifecycle_program_snapshot_id=_id(f"program-snapshot{suffix}"),
        lifecycle_program_id=_id(f"program{suffix}"),
        lifecycle_branch_analysis_id=_id(f"branch-analysis{suffix}"),
        hard_caps=_caps() if caps is None else caps,
    )


def _source(profile):
    return owner_v3.freeze_h1_shared_cap_owner_v3_source_manifest(
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
        lifecycle_program_snapshot_id=profile.lifecycle_program_snapshot_id,
        lifecycle_program_id=profile.lifecycle_program_id,
        lifecycle_branch_analysis_id=profile.lifecycle_branch_analysis_id,
    )


def _owner(tmp_path: Path, *, caps: dict[str, int] | None = None, suffix: str = ""):
    profile = _profile(caps=caps, suffix=suffix)
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
    handle = owner_v3.initialize_h1_shared_cap_owner_v3(
        tmp_path,
        profile=profile,
        source_manifest=_source(profile),
        rejection_gate=gate,
    )
    return handle, gate


def _two_transaction_owners(
    tmp_path: Path,
    *,
    suffix: str,
    first_caps: dict[str, int],
    second_caps: dict[str, int],
):
    occurrence_id = _id(f"two-owner-occurrence-{suffix}")
    attempt_id = _id(f"two-owner-attempt-{suffix}")
    provenance_id = _id(f"two-owner-provenance-{suffix}")
    lifecycle_snapshot_id = _id(f"two-owner-snapshot-{suffix}")
    lifecycle_program_id = _id(f"two-owner-program-{suffix}")
    branch_analysis_id = _id(f"two-owner-analysis-{suffix}")

    def profile(index: int, caps: dict[str, int]):
        return owner_v3.freeze_h1_shared_cap_profile_core_v3(
            logical_occurrence_id=occurrence_id,
            route_attempt_id=attempt_id,
            decision_point_id=_id(f"two-owner-decision-{suffix}-{index}"),
            transaction_id=_id(f"two-owner-transaction-{suffix}-{index}"),
            caller_pinned_lifecycle_provenance_id=provenance_id,
            lifecycle_program_snapshot_id=lifecycle_snapshot_id,
            lifecycle_program_id=lifecycle_program_id,
            lifecycle_branch_analysis_id=branch_analysis_id,
            hard_caps=caps,
        )

    profile_one = profile(1, first_caps)
    profile_two = profile(2, second_caps)
    gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=tmp_path,
        logical_occurrence_id=occurrence_id,
        route_attempt_id=attempt_id,
        caller_pinned_lifecycle_provenance_id=provenance_id,
    )
    gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(
        tmp_path, gate_spec
    )
    first = owner_v3.initialize_h1_shared_cap_owner_v3(
        tmp_path,
        profile=profile_one,
        source_manifest=_source(profile_one),
        rejection_gate=gate,
    )
    second = owner_v3.initialize_h1_shared_cap_owner_v3(
        tmp_path,
        profile=profile_two,
        source_manifest=_source(profile_two),
        rejection_gate=gate,
    )
    return first, second, gate


def _reserve(
    handle,
    label: str,
    path: str,
    upper: int,
    *,
    site_key: str | None = None,
):
    return owner_v3.reserve_h1_shared_cap_owner_v3(
        handle,
        operation_id=_id(label),
        site_key=site_key or f"site:{label}",
        path=path,
        reservation_upper=upper,
    )


def _settle(
    handle,
    reservation,
    basis,
    native: int | None,
    *,
    evidence_label: str,
):
    if basis is not owner_v3.H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO:
        reservation_id = reservation.reservation_id
        has_lifecycle_cell = any(
            row.get("h1_shared_cap_owner_v3_reservation_id") == reservation_id
            and row.get("schema") == "acfqp.k7_h1_shared_cap_native_cell.v3"
            for row in _journal_documents(handle)
        )
        if not has_lifecycle_cell:
            try:
                with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(
                    handle, reservation
                ):
                    pass
            except owner_v3.H1SharedCapOwnerV3ProtocolFailure as error:
                if "already started" not in str(error):
                    raise
    return owner_v3.settle_h1_shared_cap_owner_v3(
        handle,
        reservation,
        value_basis=basis,
        native_observed_value=native,
        evidence_source_id=_id(evidence_label),
    )


def _journal_documents(handle) -> list[dict[str, Any]]:
    result = []
    for path in sorted(Path(handle.owner_directory).glob("[0-9]*.json")):
        result.append(loads_canonical_json(path.read_bytes()))
    return result


def _append_rejection_admission(
    handle,
    *,
    operation_label: str,
    site_key: str,
    path: str,
    upper: int,
) -> dict[str, Any]:
    root_fd, directory_fd, state = owner_v3._require_handle_locked(handle)
    try:
        document, candidate = owner_v3._reservation_document_for_request(
            handle,
            state,
            operation_id=_id(operation_label),
            site_key=site_key,
            path=path,
            reservation_upper=upper,
        )
        assert candidate > owner_v3._limit(handle.profile, path).hard_cap
        return owner_v3._append_record(
            root_fd,
            directory_fd,
            handle,
            state,
            schema="acfqp.k7_h1_shared_cap_reservation.v3",
            kind="REJECTION_ADMISSION_DURABLE",
            extra={
                key: value
                for key, value in document.items()
                if key
                in owner_v3._EXTRA_FIELDS[
                    "acfqp.k7_h1_shared_cap_reservation.v3"
                ]
            },
        )
    finally:
        owner_v3.os.close(directory_fd)
        owner_v3.os.close(root_fd)


def _build_rejection_admission_document(
    handle,
    *,
    operation_label: str,
    site_key: str,
    path: str,
    upper: int,
) -> dict[str, Any]:
    root_fd, directory_fd, state = owner_v3._require_handle_locked(handle)
    try:
        document, candidate = owner_v3._reservation_document_for_request(
            handle,
            state,
            operation_id=_id(operation_label),
            site_key=site_key,
            path=path,
            reservation_upper=upper,
        )
        assert candidate > owner_v3._limit(handle.profile, path).hard_cap
        return document
    finally:
        owner_v3.os.close(directory_fd)
        owner_v3.os.close(root_fd)


def _cross_process_same_operation(
    owner_directory: str,
    runtime_id: str,
    gate_directory: str,
    start,
    output,
) -> None:
    try:
        handle = owner_v3.open_h1_shared_cap_owner_v3(
            owner_directory,
            expected_runtime_id=runtime_id,
            gate_directory=gate_directory,
        )
        start.wait(10)
        reservation = _reserve(
            handle,
            "cross-process-one-operation",
            "common.hash_invocations",
            1,
        )
        result = _settle(
            handle,
            reservation,
            owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT,
            1,
            evidence_label="cross-process-source-event",
        )
        output.put(("ok", result.settlement_document[
            "h1_shared_cap_owner_v3_settlement_id"
        ]))
    except BaseException as error:  # pragma: no cover - child diagnostic
        output.put(("error", f"{type(error).__name__}: {error}"))


def _cross_process_distinct_reservation(
    owner_directory: str,
    runtime_id: str,
    gate_directory: str,
    index: int,
    start,
    output,
) -> None:
    try:
        handle = owner_v3.open_h1_shared_cap_owner_v3(
            owner_directory,
            expected_runtime_id=runtime_id,
            gate_directory=gate_directory,
        )
        start.wait(10)
        reservation = _reserve(
            handle,
            f"distinct-cap-{index}",
            "io.read_bytes",
            1,
        )
        output.put(("ADMITTED", reservation.reservation_id))
    except owner_v3.H1SharedCapOwnerV3Rejected as error:
        output.put(("REJECTED", str(error)))
    except BaseException as error:  # pragma: no cover - child diagnostic
        output.put(("ERROR", f"{type(error).__name__}: {error}"))


def test_profile_gate_runtime_identity_is_acyclic_and_locked() -> None:
    assert set(owner_v3.REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
    assert len(owner_v3.SHARED_RESOURCE_PATHS) == 9
    profile = _profile()
    document = profile.to_document()
    assert document["identity_graph"] == "PROFILE_CORE_TO_GATE_TO_RUNTIME_BINDING"
    assert document["profile_contains_gate_id"] is False
    assert "h1_attempt_rejection_gate_id" not in document
    assert document["gate_binding_deferred_to_runtime_binding"] is True
    assert document["production_activation_chain_verified"] is False
    assert document["formal_actual_compliance_eligible"] is False
    assert document["production_execution_authorized"] is False
    assert document["official_execution_allowed"] is False


def test_profile_source_and_gate_identity_mismatches_are_rejected(
    tmp_path: Path,
) -> None:
    profile = _profile(suffix="identity-negative")
    mismatched_source = owner_v3.freeze_h1_shared_cap_owner_v3_source_manifest(
        caller_pinned_lifecycle_provenance_id=_id("wrong-provenance"),
        lifecycle_program_snapshot_id=profile.lifecycle_program_snapshot_id,
        lifecycle_program_id=profile.lifecycle_program_id,
        lifecycle_branch_analysis_id=profile.lifecycle_branch_analysis_id,
    )
    matching_gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=tmp_path,
        logical_occurrence_id=profile.logical_occurrence_id,
        route_attempt_id=profile.route_attempt_id,
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
    )
    matching_gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(
        tmp_path, matching_gate_spec
    )
    with pytest.raises(ValueError, match="profile and source"):
        owner_v3.initialize_h1_shared_cap_owner_v3(
            tmp_path,
            profile=profile,
            source_manifest=mismatched_source,
            rejection_gate=matching_gate,
        )

    other_base = tmp_path / "other-gate"
    other_base.mkdir(mode=0o700)
    mismatched_gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=other_base,
        logical_occurrence_id=_id("wrong-occurrence"),
        route_attempt_id=_id("wrong-attempt"),
        caller_pinned_lifecycle_provenance_id=_id("wrong-provenance"),
    )
    mismatched_gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(
        other_base, mismatched_gate_spec
    )
    with pytest.raises(ValueError, match="gate differs"):
        owner_v3.initialize_h1_shared_cap_owner_v3(
            tmp_path,
            profile=profile,
            source_manifest=_source(profile),
            rejection_gate=mismatched_gate,
        )


def test_runtime_binds_profile_core_gate_and_source_without_back_edge(
    tmp_path: Path,
) -> None:
    handle, gate = _owner(tmp_path)
    runtime = loads_canonical_json(
        (Path(handle.owner_directory) / "runtime-binding.json").read_bytes()
    )
    assert runtime["h1_shared_cap_profile_core_v3_id"] == handle.profile.profile_id
    assert runtime["h1_attempt_rejection_gate_id"] == gate.spec.gate_id
    assert runtime["h1_shared_cap_owner_v3_source_manifest_id"] == (
        handle.source_manifest.manifest_id
    )
    assert runtime["gate_shared_owner_profile_id_semantics"] == "PROFILE_CORE_ID"
    assert runtime["identity_graph"] == "PROFILE_CORE_TO_GATE_TO_RUNTIME_BINDING"
    reopened = owner_v3.open_h1_shared_cap_owner_v3(
        handle.owner_directory,
        expected_runtime_id=handle.runtime_id,
        gate_directory=handle.gate_directory,
    )
    assert reopened.runtime_id == handle.runtime_id


def test_partial_first_initialization_consumes_runtime_but_new_transaction_works(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile(suffix="partial-initialize")
    source = _source(profile)
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
    original_initialize_cursor = owner_v3._initialize_owner_cursor

    def interrupt_initialization(*args, **kwargs):
        raise RuntimeError("crash after owner runtime directory allocation")

    monkeypatch.setattr(
        owner_v3,
        "_initialize_owner_cursor",
        interrupt_initialization,
    )
    with pytest.raises(RuntimeError, match="runtime directory allocation"):
        owner_v3.initialize_h1_shared_cap_owner_v3(
            tmp_path,
            profile=profile,
            source_manifest=source,
            rejection_gate=gate,
        )
    monkeypatch.setattr(
        owner_v3,
        "_initialize_owner_cursor",
        original_initialize_cursor,
    )
    with pytest.raises(ValueError, match="cursor|state|token"):
        owner_v3.initialize_h1_shared_cap_owner_v3(
            tmp_path,
            profile=profile,
            source_manifest=source,
            rejection_gate=gate,
        )

    retry_profile = owner_v3.freeze_h1_shared_cap_profile_core_v3(
        logical_occurrence_id=profile.logical_occurrence_id,
        route_attempt_id=profile.route_attempt_id,
        decision_point_id=_id("partial-initialize-retry-decision"),
        transaction_id=_id("partial-initialize-retry-transaction"),
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
        lifecycle_program_snapshot_id=profile.lifecycle_program_snapshot_id,
        lifecycle_program_id=profile.lifecycle_program_id,
        lifecycle_branch_analysis_id=profile.lifecycle_branch_analysis_id,
        hard_caps=_caps(),
    )
    recovered = owner_v3.initialize_h1_shared_cap_owner_v3(
        tmp_path,
        profile=retry_profile,
        source_manifest=_source(retry_profile),
        rejection_gate=gate,
    )
    assert owner_v3.replay_h1_shared_cap_owner_v3(recovered)[
        "journal_replay_complete"
    ] is True


def test_reservation_is_durable_before_guarded_side_effect(tmp_path: Path) -> None:
    handle, _ = _owner(tmp_path)
    reservation = _reserve(handle, "read-one", "io.read_bytes", 9)
    before = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert before["reservation_count"] == 1
    assert before["settlement_count"] == 0
    assert before["outstanding_values"]["io.read_bytes"] == 9
    assert reservation.document["durable_before_side_effect"] is True
    seen = []
    with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(handle, reservation):
        seen.append(owner_v3.replay_h1_shared_cap_owner_v3(handle)[
            "outstanding_values"
        ]["io.read_bytes"])
    assert seen == [9]


def test_oversize_owner_record_is_rejected_before_cursor_or_journal_mutation(
    tmp_path: Path,
) -> None:
    handle, gate = _owner(tmp_path, suffix="oversize-record")
    before = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    before_names = sorted(Path(handle.owner_directory).glob("[0-9]*.json"))
    with pytest.raises(ValueError, match="byte cap"):
        _reserve(
            handle,
            "oversize-operation",
            "io.read_bytes",
            1,
            site_key="s" * (owner_v3._MAX_DOCUMENT_BYTES + 1),
        )
    after = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert after["journal_sequence"] == before["journal_sequence"]
    assert after["journal_head_id"] == before["journal_head_id"]
    assert sorted(Path(handle.owner_directory).glob("[0-9]*.json")) == before_names
    assert rejection_v1.h1_attempt_rejection_gate_snapshot_v1(gate)[
        "state"
    ] == "OPEN"


def test_sum_and_max_reducers_replay_exactly(tmp_path: Path) -> None:
    handle, _ = _owner(tmp_path)
    for index, value in enumerate((3, 5), start=1):
        reservation = _reserve(
            handle, f"sum-{index}", "io.read_bytes", value + 2
        )
        _settle(
            handle,
            reservation,
            owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
            value,
            evidence_label=f"sum-evidence-{index}",
        )
    for index, value in enumerate((80, 60), start=1):
        reservation = _reserve(
            handle, f"max-{index}", "io.mounted_bytes_peak", value
        )
        _settle(
            handle,
            reservation,
            owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
            value,
            evidence_label=f"max-evidence-{index}",
        )
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["charged_values"]["io.read_bytes"] == 8
    assert replay["charged_values"]["io.mounted_bytes_peak"] == 80
    assert replay["outstanding_values"]["io.read_bytes"] == 0
    assert replay["outstanding_values"]["io.mounted_bytes_peak"] == 0
    assert replay["settlement_count"] == 4


def test_all_five_value_bases_keep_observed_and_charged_values_separate(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path)
    cases = (
        (
            "exact-native",
            "io.read_bytes",
            5,
            owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
            3,
            3,
            True,
            False,
        ),
        (
            "exact-source",
            "common.hash_invocations",
            1,
            owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT,
            1,
            1,
            True,
            False,
        ),
        (
            "known-not-started",
            "io.staged_bytes",
            7,
            owner_v3.H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO,
            0,
            0,
            True,
            False,
        ),
        (
            "conservative",
            "io.output_bytes",
            11,
            owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER,
            None,
            11,
            False,
            True,
        ),
    )
    for label, path, upper, basis, native, charged, exact, conservative in cases:
        result = _settle(
            handle,
            _reserve(handle, label, path, upper),
            basis,
            native,
            evidence_label=f"{label}-evidence",
        )
        evidence = result.evidence_document
        assert evidence["charged_value"] == charged
        assert evidence["construction_exact_value_assertion"] is exact
        assert evidence["conservative_charge"] is conservative
        if native is None:
            assert evidence["native_observed_value"]["kind"] == "NOT_APPLICABLE"
        else:
            assert evidence["native_observed_value"] == native

    overrun = _reserve(handle, "overrun", "io.read_bytes", 2)
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="overrun|upper|cap",
    ):
        _settle(
            handle,
            overrun,
            owner_v3.H1SharedValueBasisV3.OBSERVED_OVERRUN,
            4,
            evidence_label="overrun-evidence",
        )
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["charged_values"]["io.read_bytes"] == 7
    assert replay["observed_overrun_count"] == 1
    assert replay["conservative_settlement_count"] == 1
    assert replay["all_settlements_nonconservative"] is False


def test_exact_source_event_is_one_registered_event(tmp_path: Path) -> None:
    handle, _ = _owner(tmp_path)
    reservation = _reserve(
        handle, "source-must-be-one", "common.protocol_checks", 2
    )
    with pytest.raises(ValueError, match="source|one|unit"):
        _settle(
            handle,
            reservation,
            owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT,
            2,
            evidence_label="bad-source-event",
        )
    assert owner_v3.replay_h1_shared_cap_owner_v3(handle)[
        "settlement_count"
    ] == 0


def test_unit_event_overrun_is_preserved_before_protocol_failure(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path, suffix="unit-overrun")
    reservation = _reserve(
        handle, "too-many-launches", "process.launches", 1
    )
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ObservedOverrun) as raised:
        _settle(
            handle,
            reservation,
            owner_v3.H1SharedValueBasisV3.OBSERVED_OVERRUN,
            2,
            evidence_label="two-launches-observed",
        )
    assert raised.value.result.evidence_document["native_observed_value"] == 2
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["charged_values"]["process.launches"] == 2
    assert replay["observed_overrun_count"] == 1


def test_durable_overrun_evidence_immediately_poisons_and_only_exact_retry_recovers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle, gate = _owner(tmp_path, suffix="overrun-evidence-poison")
    waiting = _reserve(handle, "overrun-waiting", "io.staged_bytes", 1)
    overrun = _reserve(handle, "overrun-evidence", "io.read_bytes", 2)
    with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(handle, overrun):
        pass
    original_append = owner_v3._append_record
    interrupted = False

    def append_then_crash(*args, **kwargs):
        nonlocal interrupted
        document = original_append(*args, **kwargs)
        if (
            not interrupted
            and kwargs["schema"]
            == "acfqp.k7_h1_shared_cap_native_evidence.v3"
        ):
            interrupted = True
            raise RuntimeError("crash after durable overrun evidence")
        return document

    monkeypatch.setattr(owner_v3, "_append_record", append_then_crash)
    with pytest.raises(RuntimeError, match="overrun evidence"):
        owner_v3.settle_h1_shared_cap_owner_v3(
            handle,
            overrun,
            value_basis=owner_v3.H1SharedValueBasisV3.OBSERVED_OVERRUN,
            native_observed_value=11,
            evidence_source_id=_id("overrun-evidence-source"),
        )
    monkeypatch.setattr(owner_v3, "_append_record", original_append)

    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["protocol_failed"] is True
    assert replay["new_work_allowed"] is False
    assert replay["recovery_required"] is True
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ProtocolFailure):
        _reserve(handle, "work-after-overrun-evidence", "io.output_bytes", 1)
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ProtocolFailure):
        with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(handle, waiting):
            pytest.fail("poisoned owner must not execute another side effect")
    assert rejection_v1.h1_attempt_rejection_gate_snapshot_v1(gate)[
        "state"
    ] == "OPEN"

    with pytest.raises(owner_v3.H1SharedCapOwnerV3ObservedOverrun) as recovered:
        owner_v3.settle_h1_shared_cap_owner_v3(
            handle,
            overrun,
            value_basis=owner_v3.H1SharedValueBasisV3.OBSERVED_OVERRUN,
            native_observed_value=11,
            evidence_source_id=_id("overrun-evidence-source"),
        )
    assert recovered.value.result.settlement_document["charged_value"] == 11
    assert owner_v3.replay_h1_shared_cap_owner_v3(handle)[
        "observed_overrun_count"
    ] == 1


def test_completed_retry_is_read_only_across_another_lifecycle_frontier(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path, suffix="historic-retry-frontier")
    first_reservation = _reserve(handle, "complete-first", "io.read_bytes", 2)
    first_result = _settle(
        handle,
        first_reservation,
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        2,
        evidence_label="complete-first-evidence",
    )
    second_reservation = _reserve(
        handle,
        "incomplete-second",
        "io.staged_bytes",
        1,
    )
    with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(
        handle, second_reservation
    ):
        pass
    frontier = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert frontier["recovery_required"] is True
    assert frontier["new_work_allowed"] is False

    repeated_reservation = _reserve(
        handle,
        "complete-first",
        "io.read_bytes",
        2,
    )
    repeated_result = owner_v3.settle_h1_shared_cap_owner_v3(
        handle,
        repeated_reservation,
        value_basis=owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        native_observed_value=2,
        evidence_source_id=_id("complete-first-evidence"),
    )
    assert repeated_result.receipt_document == first_result.receipt_document
    assert repeated_result.snapshot_document == first_result.snapshot_document

    second_result = owner_v3.settle_h1_shared_cap_owner_v3(
        handle,
        second_reservation,
        value_basis=owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        native_observed_value=1,
        evidence_source_id=_id("incomplete-second-evidence"),
    )
    assert second_result.settlement_document["charged_value"] == 1


@pytest.mark.parametrize(
    "crash_schema",
    (
        "acfqp.k7_h1_shared_cap_native_cell.v3",
        "acfqp.k7_h1_shared_cap_native_evidence.v3",
        "acfqp.k7_h1_shared_cap_settlement.v3",
        "acfqp.k7_h1_shared_cap_receipt.v3",
        "acfqp.k7_h1_shared_cap_event.v3",
        "acfqp.k7_h1_shared_cap_snapshot.v3",
    ),
)
def test_crash_after_each_durable_settlement_record_resumes_idempotently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, crash_schema: str
) -> None:
    handle, _ = _owner(tmp_path)
    reservation = _reserve(handle, f"crash-{crash_schema}", "io.read_bytes", 8)
    original = owner_v3._append_record
    crashed = False

    def append_then_crash(*args, **kwargs):
        nonlocal crashed
        document = original(*args, **kwargs)
        if kwargs["schema"] == crash_schema and not crashed:
            crashed = True
            raise RuntimeError("injected crash after durable append")
        return document

    monkeypatch.setattr(owner_v3, "_append_record", append_then_crash)
    with pytest.raises(RuntimeError, match="injected crash"):
        _settle(
            handle,
            reservation,
            owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
            6,
            evidence_label=f"crash-evidence-{crash_schema}",
        )
    monkeypatch.setattr(owner_v3, "_append_record", original)
    if crash_schema == "acfqp.k7_h1_shared_cap_settlement.v3":
        interrupted = owner_v3.replay_h1_shared_cap_owner_v3(handle)
        assert interrupted["journal_replay_complete"] is False
        assert interrupted["recovery_required"] is True
        assert interrupted["semantic_pair_frontier"]["stage"] == "SETTLEMENT"
        with pytest.raises(
            owner_v3.H1SharedCapOwnerV3ProtocolFailure,
            match="incomplete|settlement",
        ):
            _reserve(handle, "unrelated-after-settlement", "io.read_bytes", 1)
    result = _settle(
        handle,
        reservation,
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        6,
        evidence_label=f"crash-evidence-{crash_schema}",
    )
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert result.settlement_document["charged_value"] == 6
    assert replay["charged_values"]["io.read_bytes"] == 6
    assert replay["reservation_count"] == replay["settlement_count"] == 1


@pytest.mark.parametrize(
    "crash_schema",
    (
        "acfqp.k7_h1_shared_cap_receipt.v3",
        "acfqp.k7_h1_shared_cap_event.v3",
    ),
)
def test_incomplete_pair_blocks_unrelated_append_until_exact_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, crash_schema: str
) -> None:
    handle, _ = _owner(tmp_path)
    first = _reserve(handle, f"pair-frontier-{crash_schema}", "io.read_bytes", 8)
    original = owner_v3._append_record
    crashed = False

    def append_then_crash(*args, **kwargs):
        nonlocal crashed
        document = original(*args, **kwargs)
        if kwargs["schema"] == crash_schema and not crashed:
            crashed = True
            raise RuntimeError("injected incomplete pair")
        return document

    monkeypatch.setattr(owner_v3, "_append_record", append_then_crash)
    with pytest.raises(RuntimeError, match="incomplete pair"):
        _settle(
            handle,
            first,
            owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
            6,
            evidence_label=f"pair-frontier-evidence-{crash_schema}",
        )
    monkeypatch.setattr(owner_v3, "_append_record", original)

    before = owner_v3.replay_h1_shared_cap_owner_v3(handle)["journal_sequence"]
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="incomplete|unrelated",
    ):
        _reserve(handle, f"unrelated-{crash_schema}", "io.staged_bytes", 1)
    assert owner_v3.replay_h1_shared_cap_owner_v3(handle)[
        "journal_sequence"
    ] == before

    _settle(
        handle,
        first,
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        6,
        evidence_label=f"pair-frontier-evidence-{crash_schema}",
    )
    second = _reserve(
        handle, f"after-recovery-{crash_schema}", "io.staged_bytes", 1
    )
    assert second.reservation_id


def test_same_operation_is_idempotent_but_conflicting_reuse_fails(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path)
    first = _reserve(handle, "idempotent", "io.read_bytes", 8)
    second = _reserve(handle, "idempotent", "io.read_bytes", 8)
    assert second.reservation_id == first.reservation_id
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ProtocolFailure):
        _reserve(handle, "idempotent", "io.read_bytes", 9)
    settled = _settle(
        handle,
        first,
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        6,
        evidence_label="idempotent-evidence",
    )
    repeated = _settle(
        handle,
        second,
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        6,
        evidence_label="idempotent-evidence",
    )
    assert repeated.settlement_document == settled.settlement_document
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ProtocolFailure):
        _settle(
            handle,
            second,
            owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
            5,
            evidence_label="idempotent-evidence-conflict",
        )


def test_cross_process_same_operation_has_one_reservation_and_one_spend(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path)
    context = multiprocessing.get_context("fork")
    start = context.Event()
    output = context.Queue()
    processes = [
        context.Process(
            target=_cross_process_same_operation,
            args=(
                handle.owner_directory,
                handle.runtime_id,
                handle.gate_directory,
                start,
                output,
            ),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    start.set()
    rows = [output.get(timeout=15) for _ in processes]
    for process in processes:
        process.join(timeout=15)
        assert process.exitcode == 0
    assert [row[0] for row in rows] == ["ok", "ok"], rows
    assert len({row[1] for row in rows}) == 1
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["reservation_count"] == replay["settlement_count"] == 1
    assert replay["charged_values"]["common.hash_invocations"] == 1


def test_cross_process_distinct_admissions_share_one_cap_and_rejection(
    tmp_path: Path,
) -> None:
    caps = _caps()
    caps["io.read_bytes"] = 3
    handle, gate = _owner(tmp_path, caps=caps, suffix="distinct-cap-race")
    context = multiprocessing.get_context("fork")
    start = context.Event()
    output = context.Queue()
    processes = [
        context.Process(
            target=_cross_process_distinct_reservation,
            args=(
                handle.owner_directory,
                handle.runtime_id,
                handle.gate_directory,
                index,
                start,
                output,
            ),
        )
        for index in range(8)
    ]
    for process in processes:
        process.start()
    start.set()
    rows = [output.get(timeout=20) for _ in processes]
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    assert sum(row[0] == "ADMITTED" for row in rows) == 3, rows
    assert sum(row[0] == "REJECTED" for row in rows) == 5, rows
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["reservation_count"] == 3
    assert replay["outstanding_values"]["io.read_bytes"] == 3
    assert replay["control_cap_rejections"] == 1
    assert rejection_v1.h1_attempt_rejection_gate_snapshot_v1(gate)[
        "control_cap_rejections"
    ] == 1


def test_tamper_gap_unknown_file_and_transplanted_runtime_fail_closed(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path)
    reservation = _reserve(handle, "tamper", "io.read_bytes", 4)
    _settle(
        handle,
        reservation,
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        3,
        evidence_label="tamper-evidence",
    )
    first = sorted(Path(handle.owner_directory).glob("[0-9]*.json"))[0]
    first.write_bytes(first.read_bytes() + b"\n")
    with pytest.raises(owner_v3.ConstructionK7H1SharedCapOwnerV3Error):
        owner_v3.replay_h1_shared_cap_owner_v3(handle)


def test_sequence_gap_unknown_file_and_runtime_transplant_each_fail_closed(
    tmp_path: Path,
) -> None:
    gap, _ = _owner(tmp_path, suffix="sequence-gap")
    _reserve(gap, "gap-first", "io.read_bytes", 1)
    record = next(Path(gap.owner_directory).glob("00000001-*.json"))
    record.rename(record.with_name("00000009-" + record.name.split("-", 1)[1]))
    with pytest.raises(ValueError, match="gap|sequence"):
        owner_v3.replay_h1_shared_cap_owner_v3(gap)

    unknown, _ = _owner(tmp_path, suffix="unknown-file")
    extra = Path(unknown.owner_directory) / "unregistered.bin"
    extra.write_bytes(b"not a registered owner record")
    extra.chmod(0o600)
    with pytest.raises(ValueError, match="unknown record"):
        owner_v3.replay_h1_shared_cap_owner_v3(unknown)

    source, _ = _owner(tmp_path, suffix="transplant-source")
    target, _ = _owner(tmp_path, suffix="transplant-target")
    _reserve(source, "transplant-record", "io.read_bytes", 1)
    source_record = next(Path(source.owner_directory).glob("00000001-*.json"))
    transplanted = Path(target.owner_directory) / source_record.name
    transplanted.write_bytes(source_record.read_bytes())
    transplanted.chmod(0o600)
    with pytest.raises(ValueError, match="context|transplanted|cursor"):
        owner_v3.replay_h1_shared_cap_owner_v3(target)


@pytest.mark.parametrize("mutation", ["basis_path", "evidence_source"])
def test_coherently_reidentified_evidence_still_replays_producer_semantics(
    tmp_path: Path,
    mutation: str,
) -> None:
    handle, _ = _owner(tmp_path, suffix=f"evidence-replay-{mutation}")
    reservation = _reserve(
        handle,
        f"evidence-replay-{mutation}",
        "common.hash_invocations",
        1,
    )
    with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(handle, reservation):
        pass
    root_fd, directory_fd, state = owner_v3._require_handle_locked(handle)
    try:
        cell = state.cells[reservation.reservation_id]
        basis = (
            owner_v3.H1SharedValueBasisV3.EXACT_NATIVE
            if mutation == "basis_path"
            else owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT
        )
        owner_v3._append_record(
            root_fd,
            directory_fd,
            handle,
            state,
            schema="acfqp.k7_h1_shared_cap_native_evidence.v3",
            kind="NATIVE_EVIDENCE_DURABLE",
            extra={
                "h1_shared_cap_owner_v3_reservation_id": reservation.reservation_id,
                "h1_shared_cap_owner_v3_native_cell_id": owner_v3._record_id(cell),
                "operation_id": reservation.document["operation_id"],
                "path": reservation.document["path"],
                "value_basis": basis.value,
                "native_observed_value": 1,
                "charged_value": 1,
                "construction_exact_value_assertion": True,
                "native_authority_verified": False,
                "evidence_source_authority_verified": False,
                "conservative_charge": False,
                "upper_bound_violation": False,
                "evidence_source_id": (
                    "not-a-content-id"
                    if mutation == "evidence_source"
                    else _id("coherent-evidence-source")
                ),
            },
        )
    finally:
        owner_v3.os.close(directory_fd)
        owner_v3.os.close(root_fd)

    with pytest.raises(
        owner_v3.ConstructionK7H1SharedCapOwnerV3Error,
        match="shared path|content ID",
    ):
        owner_v3.replay_h1_shared_cap_owner_v3(handle)


def test_coherently_reidentified_empty_reservation_site_fails_replay(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path, suffix="empty-site-replay")
    root_fd, directory_fd, state = owner_v3._require_handle_locked(handle)
    try:
        document, _ = owner_v3._reservation_document_for_request(
            handle,
            state,
            operation_id=_id("empty-site-operation"),
            site_key="valid-site",
            path="io.read_bytes",
            reservation_upper=1,
        )
        extra = {
            key: value
            for key, value in document.items()
            if key
            in owner_v3._EXTRA_FIELDS[
                "acfqp.k7_h1_shared_cap_reservation.v3"
            ]
        }
        extra["site_key"] = ""
        owner_v3._append_record(
            root_fd,
            directory_fd,
            handle,
            state,
            schema="acfqp.k7_h1_shared_cap_reservation.v3",
            kind="RESERVATION_DURABLE",
            extra=extra,
        )
    finally:
        owner_v3.os.close(directory_fd)
        owner_v3.os.close(root_fd)

    with pytest.raises(ValueError, match="site key"):
        owner_v3.replay_h1_shared_cap_owner_v3(handle)


def test_cap_rejection_commits_owner_pair_snapshot_then_gate_ack(tmp_path: Path) -> None:
    caps = _caps()
    caps["io.output_bytes"] = 5
    handle, gate = _owner(tmp_path, caps=caps)
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        _reserve(handle, "too-large-output", "io.output_bytes", 6)

    gate_snapshot = rejection_v1.h1_attempt_rejection_gate_snapshot_v1(gate)
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert gate_snapshot["state"] == "ACKNOWLEDGED"
    assert gate_snapshot["control_cap_rejections"] == 1
    assert replay["control_cap_rejections"] == 1
    assert replay["reservation_count"] == 0
    receipts = [
        row for row in _journal_documents(handle) if row["record_kind"] == "RECEIPT_DURABLE"
    ]
    events = [
        row for row in _journal_documents(handle) if row["record_kind"] == "EVENT_DURABLE"
    ]
    snapshots = [
        row for row in _journal_documents(handle) if row["record_kind"] == "SNAPSHOT_DURABLE"
    ]
    assert len(receipts) == len(events) == len(snapshots) == 1
    assert receipts[0]["subject_kind"] == "CAP_REJECTION"
    assert events[0]["subject_id"] == receipts[0]["subject_id"]
    assert snapshots[0]["control_cap_rejections"] == 1
    ack = loads_canonical_json((Path(gate.gate_directory) / "ack.json").read_bytes())
    assert ack["shared_owner_receipt_id"] == receipts[0][
        "h1_shared_cap_owner_v3_receipt_id"
    ]
    assert ack["shared_owner_event_id"] == events[0][
        "h1_shared_cap_owner_v3_event_id"
    ]
    assert ack["shared_owner_snapshot_id"] == snapshots[0][
        "h1_shared_cap_owner_v3_snapshot_id"
    ]
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        _reserve(handle, "later-effect", "common.hash_invocations", 1)


def test_owner_rejection_pair_before_ack_is_recoverable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caps = _caps()
    caps["io.output_bytes"] = 1
    handle, _ = _owner(tmp_path, caps=caps, suffix="pair-before-ack")
    original_ack = rejection_v1.acknowledge_h1_attempt_rejection_v1
    interrupted = False

    def interrupt_ack(*args, **kwargs):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise RuntimeError("crash before rejection ACK")
        return original_ack(*args, **kwargs)

    monkeypatch.setattr(
        rejection_v1,
        "acknowledge_h1_attempt_rejection_v1",
        interrupt_ack,
    )
    with pytest.raises(RuntimeError, match="before rejection ACK"):
        _reserve(handle, "pair-before-ack", "io.output_bytes", 2)
    monkeypatch.setattr(
        rejection_v1,
        "acknowledge_h1_attempt_rejection_v1",
        original_ack,
    )

    prefix = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert prefix["gate_owner_join_status"] == "LOCAL_PAIR_AWAITING_ACK"
    assert prefix["recovery_required"] is True
    recovered = owner_v3.synchronize_h1_shared_cap_rejection_v3(handle)
    assert recovered is not None
    assert owner_v3.replay_h1_shared_cap_owner_v3(handle)[
        "gate_owner_join_status"
    ] == "LOCAL_ACK_VERIFIED"


def test_every_artifact_and_replay_keeps_all_production_formal_flags_false(
    tmp_path: Path,
) -> None:
    handle, gate = _owner(tmp_path)
    result = _settle(
        handle,
        _reserve(handle, "flags", "common.integrity_checks", 1),
        owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT,
        1,
        evidence_label="flags-evidence",
    )
    documents = [
        handle.profile.to_document(),
        handle.source_manifest.to_document(),
        result.reservation.document,
        result.native_cell_document,
        result.evidence_document,
        result.settlement_document,
        result.receipt_document,
        result.event_document,
        result.snapshot_document,
        owner_v3.replay_h1_shared_cap_owner_v3(handle),
        rejection_v1.h1_attempt_rejection_gate_snapshot_v1(gate),
    ]
    for document in documents:
        for field in (
            "formal_actual_compliance_eligible",
            "formal_counter_eligible",
            "production_execution_authorized",
            "official_execution_allowed",
        ):
            if field in document:
                assert document[field] is False
    replay = documents[-2]
    assert replay["real_syscall_adapter_bound"] is False
    assert replay["native_zero_eligible"] is False


@pytest.mark.parametrize("delete_mode", ("tail", "all"))
def test_high_water_cursor_rejects_journal_tail_or_total_rollback(
    tmp_path: Path, delete_mode: str
) -> None:
    handle, _ = _owner(tmp_path, suffix=f"rollback-{delete_mode}")
    _settle(
        handle,
        _reserve(handle, "rollback-op", "io.read_bytes", 4),
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        3,
        evidence_label="rollback-evidence",
    )
    records = sorted(Path(handle.owner_directory).glob("[0-9]*.json"))
    targets = records[-1:] if delete_mode == "tail" else records
    for target in targets:
        target.unlink()
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="truncated|cursor",
    ):
        owner_v3.replay_h1_shared_cap_owner_v3(handle)


def test_cursor_deletion_replacement_and_allocation_reset_fail_closed(
    tmp_path: Path,
) -> None:
    handle, gate = _owner(tmp_path, suffix="cursor-attacks")
    root = Path(handle.owner_root_realpath)
    states = list(
        root.glob(f".acfqp-h1-owner-cursor-state-{handle.runtime_id}-*")
    )
    assert len(states) == 1
    states[0].unlink()
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ProtocolFailure, match="cursor"):
        owner_v3.replay_h1_shared_cap_owner_v3(handle)

    # A fresh fixture tests inode replacement and non-recreatable allocation.
    other, other_gate = _owner(tmp_path, suffix="cursor-replacement")
    other_root = Path(other.owner_root_realpath)
    token = other_root / f".acfqp-h1-owner-cursor-token-{other.runtime_id}.bin"
    displaced = other_root / f".displaced-{other.runtime_id}"
    token.rename(displaced)
    token.write_bytes(displaced.read_bytes())
    token.chmod(0o600)
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ProtocolFailure):
        owner_v3.replay_h1_shared_cap_owner_v3(other)

    third, third_gate = _owner(tmp_path, suffix="allocation-delete")
    allocation = Path(third.owner_root_realpath) / (
        f".acfqp-h1-owner-allocation-{third.runtime_id}.json"
    )
    allocation.unlink()
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ProtocolFailure, match="allocation"):
        owner_v3.initialize_h1_shared_cap_owner_v3(
            tmp_path,
            profile=third.profile,
            source_manifest=third.source_manifest,
            rejection_gate=third_gate,
        )
    assert gate.spec.gate_id and other_gate.spec.gate_id


def test_cursor_scan_ignores_disappearing_unrelated_runtime_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    handle, _ = _owner(tmp_path, suffix="unrelated-cursor-churn")
    unrelated_name = ".unrelated-runtime-churn"
    unrelated = Path(handle.owner_root_realpath) / unrelated_name
    unrelated.write_bytes(b"transient")
    unrelated.chmod(0o600)
    original_stat = owner_v3.os.stat

    def disappearing_stat(path, *args, **kwargs):
        if path == unrelated_name:
            raise FileNotFoundError(path)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(owner_v3.os, "stat", disappearing_stat)
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["journal_replay_complete"] is True


def test_open_holds_owner_lock_across_cursor_and_static_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    handle, _ = _owner(tmp_path, suffix="open-cursor-lock")
    opener_inside = threading.Event()
    release_opener = threading.Event()
    writer_started = threading.Event()
    writer_done = threading.Event()
    errors: list[BaseException] = []
    original_initialize = owner_v3._initialize_owner_cursor

    def paused_initialize(*args, **kwargs):
        if (
            threading.current_thread().name == "owner-opener"
            and kwargs.get("allow_create") is False
        ):
            opener_inside.set()
            assert release_opener.wait(5)
        return original_initialize(*args, **kwargs)

    monkeypatch.setattr(owner_v3, "_initialize_owner_cursor", paused_initialize)

    def open_owner() -> None:
        try:
            owner_v3.open_h1_shared_cap_owner_v3(
                handle.owner_directory,
                expected_runtime_id=handle.runtime_id,
                gate_directory=handle.gate_directory,
            )
        except BaseException as error:  # pragma: no cover - thread diagnostic
            errors.append(error)

    def write_owner() -> None:
        writer_started.set()
        try:
            _reserve(handle, "writer-during-open", "io.read_bytes", 1)
        except BaseException as error:  # pragma: no cover - thread diagnostic
            errors.append(error)
        finally:
            writer_done.set()

    opener = threading.Thread(target=open_owner, name="owner-opener")
    opener.start()
    assert opener_inside.wait(5)
    writer = threading.Thread(target=write_owner, name="owner-writer")
    writer.start()
    assert writer_started.wait(5)
    assert writer_done.wait(0.2) is False
    release_opener.set()
    opener.join(10)
    writer.join(10)
    assert not opener.is_alive() and not writer.is_alive()
    assert errors == []


def test_strict_orphan_temp_is_cleaned_after_final_publication(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path, suffix="orphan-temp")
    _reserve(handle, "temp-op", "io.read_bytes", 2)
    orphan = Path(handle.owner_directory) / (
        ".tmp-12345-0123456789abcdef0123456789abcdef"
    )
    orphan.write_bytes(b"already-published-temp-link")
    orphan.chmod(0o600)
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["reservation_count"] == 1
    assert not orphan.exists()


def test_stale_gate_handle_cannot_initialize_owner(tmp_path: Path) -> None:
    profile = _profile(suffix="stale-gate")
    gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=tmp_path,
        logical_occurrence_id=profile.logical_occurrence_id,
        route_attempt_id=profile.route_attempt_id,
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
    )
    gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(tmp_path, gate_spec)
    original = Path(gate.gate_directory)
    original.rename(tmp_path / "displaced-stale-gate")
    original.mkdir(mode=0o700)
    with pytest.raises(
        ValueError,
        match="spec|allocation|physical|coordination lock",
    ):
        owner_v3.initialize_h1_shared_cap_owner_v3(
            tmp_path,
            profile=profile,
            source_manifest=_source(profile),
            rejection_gate=gate,
        )


def test_durable_start_prevents_known_not_started_zero_bypass(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path, suffix="start-token")
    reservation = _reserve(handle, "started-op", "io.read_bytes", 4)
    with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(handle, reservation):
        with pytest.raises(
            owner_v3.H1SharedCapOwnerV3ProtocolFailure,
            match="lifecycle",
        ):
            owner_v3.settle_h1_shared_cap_owner_v3(
                handle,
                reservation,
                value_basis=(
                    owner_v3.H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO
                ),
                native_observed_value=0,
                evidence_source_id=_id("false-zero"),
            )
    result = owner_v3.settle_h1_shared_cap_owner_v3(
        handle,
        reservation,
        value_basis=owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        native_observed_value=3,
        evidence_source_id=_id("real-observation"),
    )
    assert result.settlement_document["charged_value"] == 3


def test_observed_overrun_durably_poisons_new_owner_work(tmp_path: Path) -> None:
    handle, _ = _owner(tmp_path, suffix="overrun-poison")
    waiting = _reserve(handle, "waiting", "io.staged_bytes", 1)
    overrun = _reserve(handle, "poison", "io.read_bytes", 2)
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ObservedOverrun):
        _settle(
            handle,
            overrun,
            owner_v3.H1SharedValueBasisV3.OBSERVED_OVERRUN,
            4,
            evidence_label="poison-evidence",
        )
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["protocol_failed"] is True
    assert replay["new_work_allowed"] is False
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ProtocolFailure, match="poison"):
        _reserve(handle, "after-poison", "common.hash_invocations", 1)
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ProtocolFailure, match="poison"):
        with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(handle, waiting):
            pass


def test_completed_settlement_retry_survives_later_cap_rejection(
    tmp_path: Path,
) -> None:
    caps = _caps()
    caps["io.output_bytes"] = 1
    handle, _ = _owner(tmp_path, caps=caps, suffix="historic-pair")
    reservation = _reserve(handle, "historic", "io.read_bytes", 2)
    first = _settle(
        handle,
        reservation,
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        2,
        evidence_label="historic-evidence",
    )
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        _reserve(handle, "later-rejection", "io.output_bytes", 2)
    repeated = _settle(
        handle,
        reservation,
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        2,
        evidence_label="historic-evidence",
    )
    assert repeated.receipt_document == first.receipt_document
    assert repeated.snapshot_document == first.snapshot_document


def test_source_event_basis_is_restricted_to_registered_unit_paths(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path, suffix="basis-registry")
    reservation = _reserve(handle, "wrong-basis", "io.read_bytes", 1)
    with pytest.raises(ValueError, match="source-event basis"):
        owner_v3.settle_h1_shared_cap_owner_v3(
            handle,
            reservation,
            value_basis=owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT,
            native_observed_value=1,
            evidence_source_id=_id("wrong-basis-evidence"),
        )


def test_intent_only_gate_synchronizes_to_owner_pair_and_ack(tmp_path: Path) -> None:
    caps = _caps()
    caps["io.read_bytes"] = 1
    handle, gate = _owner(tmp_path, caps=caps, suffix="intent-sync")
    admission = _build_rejection_admission_document(
        handle,
        operation_label="intent-sync-operation",
        site_key="site:intent-sync",
        path="io.read_bytes",
        upper=2,
    )
    with pytest.raises(rejection_v1.H1AttemptRejectionInjectedCrashV1):
        rejection_v1.commit_h1_attempt_rejection_v1(
            gate,
            writer_role=rejection_v1.H1AttemptRejectionWriterRoleV1.BROKER,
            decision_point_id=handle.profile.decision_point_id,
            transaction_id=handle.profile.transaction_id,
            shared_owner_profile_core_id=handle.profile.profile_id,
            rejection_request_id=admission["rejection_request_id"],
            source_kind=rejection_v1.H1RejectionSourceKindV1.SHARED_OWNER,
            site_key="site:intent-sync",
            path="io.read_bytes",
            limit_kind=rejection_v1.H1RejectionLimitKindV1.SHARED_PATH,
            reservation_upper=2,
            candidate=2,
            hard_cap=1,
            reason_code="SHARED_CAP_EXHAUSTED",
            crash_point=(
                rejection_v1.H1AttemptRejectionCrashPointV1.AFTER_INTENT_FSYNC
            ),
        )
    assert owner_v3.synchronize_h1_shared_cap_rejection_v3(handle) is None
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected) as rejected:
        _reserve(
            handle,
            "intent-sync-operation",
            "io.read_bytes",
            2,
            site_key="site:intent-sync",
        )
    assert rejected.value.result is not None
    result = rejected.value.result
    assert result.acknowledgement.commit_id == result.rejection_commit.commit_id
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["gate_state"] == "ACKNOWLEDGED"
    assert replay["gate_owner_join_verified"] is True
    assert replay["control_cap_rejections"] == 1


def test_gate_commit_without_owner_admission_recovers_only_exact_request(
    tmp_path: Path,
) -> None:
    caps = _caps()
    caps["io.read_bytes"] = 1
    handle, gate = _owner(tmp_path, caps=caps, suffix="admission-recovery")
    admission = _build_rejection_admission_document(
        handle,
        operation_label="admission-recovery-operation",
        site_key="site:admission-recovery",
        path="io.read_bytes",
        upper=2,
    )
    rejection_v1.commit_h1_attempt_rejection_v1(
        gate,
        writer_role=rejection_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        decision_point_id=handle.profile.decision_point_id,
        transaction_id=handle.profile.transaction_id,
        shared_owner_profile_core_id=handle.profile.profile_id,
        rejection_request_id=admission["rejection_request_id"],
        source_kind=rejection_v1.H1RejectionSourceKindV1.SHARED_OWNER,
        site_key="site:admission-recovery",
        path="io.read_bytes",
        limit_kind=rejection_v1.H1RejectionLimitKindV1.SHARED_PATH,
        reservation_upper=2,
        candidate=2,
        hard_cap=1,
        reason_code="SHARED_CAP_EXHAUSTED",
    )
    interrupted = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert interrupted["gate_owner_join_status"] == (
        "LOCAL_COMMIT_AWAITING_ADMISSION"
    )
    assert interrupted["attempt_control_cap_rejections"] == 1
    assert interrupted["recovery_required"] is True
    assert interrupted["new_work_allowed"] is False
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="exact rejection recovery request",
    ):
        _reserve(handle, "other-after-admission", "io.read_bytes", 2)
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        _reserve(
            handle,
            "admission-recovery-operation",
            "io.read_bytes",
            2,
            site_key="site:admission-recovery",
        )
    completed = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert completed["gate_owner_join_status"] == "LOCAL_ACK_VERIFIED"
    assert completed["attempt_control_cap_rejections"] == 1


def test_gate_first_crash_blocks_other_transaction_until_exact_owner_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    occurrence_id = _id("gate-first-crash-occurrence")
    attempt_id = _id("gate-first-crash-attempt")
    provenance_id = _id("gate-first-crash-provenance")

    def profile(label: str, read_cap: int):
        caps = _caps()
        caps["io.read_bytes"] = read_cap
        return owner_v3.freeze_h1_shared_cap_profile_core_v3(
            logical_occurrence_id=occurrence_id,
            route_attempt_id=attempt_id,
            decision_point_id=_id(f"gate-first-decision-{label}"),
            transaction_id=_id(f"gate-first-transaction-{label}"),
            caller_pinned_lifecycle_provenance_id=provenance_id,
            lifecycle_program_snapshot_id=_id("gate-first-lifecycle-snapshot"),
            lifecycle_program_id=_id("gate-first-lifecycle-program"),
            lifecycle_branch_analysis_id=_id("gate-first-branch-analysis"),
            hard_caps=caps,
        )

    first_profile = profile("first", 1)
    second_profile = profile("second", 100)
    gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=tmp_path,
        logical_occurrence_id=occurrence_id,
        route_attempt_id=attempt_id,
        caller_pinned_lifecycle_provenance_id=provenance_id,
    )
    gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(
        tmp_path, gate_spec
    )
    first = owner_v3.initialize_h1_shared_cap_owner_v3(
        tmp_path,
        profile=first_profile,
        source_manifest=_source(first_profile),
        rejection_gate=gate,
    )
    second = owner_v3.initialize_h1_shared_cap_owner_v3(
        tmp_path,
        profile=second_profile,
        source_manifest=_source(second_profile),
        rejection_gate=gate,
    )
    waiting = _reserve(first, "gate-first-waiting", "io.staged_bytes", 1)
    original_append = owner_v3._append_record
    interrupted = False

    def crash_before_owner_admission(*args, **kwargs):
        nonlocal interrupted
        if kwargs["kind"] == "REJECTION_ADMISSION_DURABLE" and not interrupted:
            interrupted = True
            raise RuntimeError("crash after gate commit before owner admission")
        return original_append(*args, **kwargs)

    monkeypatch.setattr(owner_v3, "_append_record", crash_before_owner_admission)
    with pytest.raises(RuntimeError, match="after gate commit"):
        _reserve(first, "gate-first-reject", "io.read_bytes", 2)
    monkeypatch.setattr(owner_v3, "_append_record", original_append)

    prefix = owner_v3.replay_h1_shared_cap_owner_v3(first)
    assert prefix["gate_state"] == "COMMITTED_UNACKNOWLEDGED"
    assert prefix["gate_owner_join_status"] == "LOCAL_COMMIT_AWAITING_ADMISSION"
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        _reserve(second, "must-not-enter", "io.staged_bytes", 1)
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="must recover.*local settlement",
    ):
        owner_v3.settle_h1_shared_cap_owner_v3(
            first,
            waiting,
            value_basis=owner_v3.H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO,
            native_observed_value=0,
            evidence_source_id=_id("blocked-cleanup-before-recovery"),
        )
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected) as recovered:
        _reserve(first, "gate-first-reject", "io.read_bytes", 2)
    assert recovered.value.result is not None
    assert owner_v3.replay_h1_shared_cap_owner_v3(first)[
        "gate_owner_join_status"
    ] == "LOCAL_ACK_VERIFIED"
    cleaned = owner_v3.settle_h1_shared_cap_owner_v3(
        first,
        waiting,
        value_basis=owner_v3.H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO,
        native_observed_value=0,
        evidence_source_id=_id("cleanup-after-rejection-recovery"),
    )
    assert cleaned.settlement_document["charged_value"] == 0
    assert owner_v3.replay_h1_shared_cap_owner_v3(first)[
        "gate_owner_join_status"
    ] == "LOCAL_ACK_VERIFIED"


def test_pending_reservation_blocks_different_overcap_before_gate_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caps = _caps()
    caps["io.read_bytes"] = 1
    handle, gate = _owner(tmp_path, caps=caps, suffix="pending-preflight")
    original_publish = owner_v3._publish_new
    interrupted = False

    def interrupt_reservation(directory_fd, name, raw):
        nonlocal interrupted
        try:
            document = loads_canonical_json(raw)
        except (TypeError, ValueError):
            document = {}
        if (
            not interrupted
            and document.get("record_kind") == "RESERVATION_DURABLE"
        ):
            interrupted = True
            raise RuntimeError("crash after pending reservation cursor")
        return original_publish(directory_fd, name, raw)

    monkeypatch.setattr(owner_v3, "_publish_new", interrupt_reservation)
    with pytest.raises(RuntimeError, match="pending reservation"):
        _reserve(handle, "pending-admitted", "io.staged_bytes", 1)
    monkeypatch.setattr(owner_v3, "_publish_new", original_publish)
    assert owner_v3.replay_h1_shared_cap_owner_v3(handle)["pending_cursor"]
    assert owner_v3.replay_h1_shared_cap_owner_v3(handle)[
        "new_work_allowed"
    ] is False

    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="pending append",
    ):
        _reserve(handle, "different-overcap", "io.read_bytes", 2)
    assert rejection_v1.h1_attempt_rejection_gate_snapshot_v1(gate)[
        "state"
    ] == "OPEN"

    recovered = _reserve(handle, "pending-admitted", "io.staged_bytes", 1)
    cleaned = owner_v3.settle_h1_shared_cap_owner_v3(
        handle,
        recovered,
        value_basis=owner_v3.H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO,
        native_observed_value=0,
        evidence_source_id=_id("pending-admitted-zero"),
    )
    assert cleaned.settlement_document["charged_value"] == 0


def test_pending_reservation_converges_after_external_attempt_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_caps = _caps()
    second_caps = _caps()
    second_caps["io.read_bytes"] = 1
    first, second, _ = _two_transaction_owners(
        tmp_path,
        suffix="pending-reservation-external",
        first_caps=first_caps,
        second_caps=second_caps,
    )
    original_publish = owner_v3._publish_new
    interrupted = False

    def interrupt_reservation(directory_fd, name, raw):
        nonlocal interrupted
        try:
            document = loads_canonical_json(raw)
        except (TypeError, ValueError):
            document = {}
        if (
            not interrupted
            and document.get("record_kind") == "RESERVATION_DURABLE"
        ):
            interrupted = True
            raise RuntimeError("crash before reservation publication")
        return original_publish(directory_fd, name, raw)

    monkeypatch.setattr(owner_v3, "_publish_new", interrupt_reservation)
    with pytest.raises(RuntimeError, match="reservation publication"):
        _reserve(first, "pending-before-external", "io.staged_bytes", 1)
    monkeypatch.setattr(owner_v3, "_publish_new", original_publish)

    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        _reserve(second, "external-rejection", "io.read_bytes", 2)
    recovered = _reserve(
        first,
        "pending-before-external",
        "io.staged_bytes",
        1,
    )
    cleaned = owner_v3.settle_h1_shared_cap_owner_v3(
        first,
        recovered,
        value_basis=owner_v3.H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO,
        native_observed_value=0,
        evidence_source_id=_id("pending-external-zero"),
    )
    assert cleaned.settlement_document["charged_value"] == 0
    replay = owner_v3.replay_h1_shared_cap_owner_v3(first)
    assert replay["pending_cursor"]["kind"] == "NOT_APPLICABLE"
    assert replay["gate_owner_join_status"] == (
        "EXTERNAL_ATTEMPT_REJECTION_ACKNOWLEDGED"
    )


def test_pending_start_after_external_rejection_requires_conservative_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_caps = _caps()
    second_caps = _caps()
    second_caps["io.read_bytes"] = 1
    first, second, _ = _two_transaction_owners(
        tmp_path,
        suffix="pending-start-external",
        first_caps=first_caps,
        second_caps=second_caps,
    )
    reservation = _reserve(first, "pending-start", "io.staged_bytes", 3)
    original_publish = owner_v3._publish_new
    interrupted = False

    def interrupt_start(directory_fd, name, raw):
        nonlocal interrupted
        try:
            document = loads_canonical_json(raw)
        except (TypeError, ValueError):
            document = {}
        if (
            not interrupted
            and document.get("record_kind") == "NATIVE_CELL_DURABLE"
        ):
            interrupted = True
            raise RuntimeError("crash before start publication")
        return original_publish(directory_fd, name, raw)

    monkeypatch.setattr(owner_v3, "_publish_new", interrupt_start)
    with pytest.raises(RuntimeError, match="start publication"):
        with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(
            first, reservation
        ):
            pytest.fail("the side effect must not be reached")
    monkeypatch.setattr(owner_v3, "_publish_new", original_publish)

    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        _reserve(second, "external-start-rejection", "io.read_bytes", 2)
    with pytest.raises(rejection_v1.H1AttemptRejectedV1):
        with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(
            first, reservation
        ):
            pytest.fail("closed attempt must not execute the side effect")
    for basis, native in (
        (owner_v3.H1SharedValueBasisV3.EXACT_NATIVE, 1),
        (owner_v3.H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO, 0),
    ):
        with pytest.raises(
            owner_v3.H1SharedCapOwnerV3ProtocolFailure,
            match="requires conservative",
        ):
            owner_v3.settle_h1_shared_cap_owner_v3(
                first,
                reservation,
                value_basis=basis,
                native_observed_value=native,
                evidence_source_id=_id(f"pending-start-{basis.value}"),
            )

    cleaned = owner_v3.settle_h1_shared_cap_owner_v3(
        first,
        reservation,
        value_basis=(
            owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER
        ),
        native_observed_value=None,
        evidence_source_id=_id("pending-start-conservative"),
    )
    assert cleaned.settlement_document["charged_value"] == 3
    replay = owner_v3.replay_h1_shared_cap_owner_v3(first)
    assert replay["pending_cursor"]["kind"] == "NOT_APPLICABLE"
    assert replay["conservative_settlement_count"] == 1


def test_attempt_wide_rejection_from_later_transaction_is_external_to_prior_owner(
    tmp_path: Path,
) -> None:
    occurrence_id = _id("two-transaction-occurrence")
    attempt_id = _id("two-transaction-attempt")
    provenance_id = _id("two-transaction-provenance")
    lifecycle_snapshot_id = _id("two-transaction-lifecycle-snapshot")
    lifecycle_program_id = _id("two-transaction-lifecycle-program")
    branch_analysis_id = _id("two-transaction-branch-analysis")

    def profile(transaction: int, *, read_cap: int):
        caps = _caps()
        caps["io.read_bytes"] = read_cap
        return owner_v3.freeze_h1_shared_cap_profile_core_v3(
            logical_occurrence_id=occurrence_id,
            route_attempt_id=attempt_id,
            decision_point_id=_id(f"two-transaction-decision-{transaction}"),
            transaction_id=_id(f"two-transaction-id-{transaction}"),
            caller_pinned_lifecycle_provenance_id=provenance_id,
            lifecycle_program_snapshot_id=lifecycle_snapshot_id,
            lifecycle_program_id=lifecycle_program_id,
            lifecycle_branch_analysis_id=branch_analysis_id,
            hard_caps=caps,
        )

    profile_one = profile(1, read_cap=10)
    profile_two = profile(2, read_cap=1)
    gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=tmp_path,
        logical_occurrence_id=occurrence_id,
        route_attempt_id=attempt_id,
        caller_pinned_lifecycle_provenance_id=provenance_id,
    )
    gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(
        tmp_path, gate_spec
    )
    owner_one = owner_v3.initialize_h1_shared_cap_owner_v3(
        tmp_path,
        profile=profile_one,
        source_manifest=_source(profile_one),
        rejection_gate=gate,
    )
    owner_two = owner_v3.initialize_h1_shared_cap_owner_v3(
        tmp_path,
        profile=profile_two,
        source_manifest=_source(profile_two),
        rejection_gate=gate,
    )

    reservation = _reserve(owner_one, "transaction-one-read", "io.read_bytes", 2)
    _reserve(
        owner_one,
        "recover-wrapper-after-close",
        "io.staged_bytes",
        1,
    )
    with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(
        owner_one, reservation
    ):
        for blocked in (
            lambda: _reserve(
                owner_two,
                "cross-transaction-during-guard",
                "io.staged_bytes",
                1,
            ),
            lambda: owner_v3.replay_h1_shared_cap_owner_v3(owner_two),
            lambda: owner_v3.synchronize_h1_shared_cap_rejection_v3(owner_two),
        ):
            with pytest.raises(
                owner_v3.H1SharedCapOwnerV3ProtocolFailure,
                match="guard|guarded",
            ):
                blocked()
    first = _settle(
        owner_one,
        reservation,
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        2,
        evidence_label="transaction-one-read-evidence",
    )
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        _reserve(owner_two, "transaction-two-rejection", "io.read_bytes", 2)

    earlier = owner_v3.replay_h1_shared_cap_owner_v3(owner_one)
    rejecting = owner_v3.replay_h1_shared_cap_owner_v3(owner_two)
    assert earlier["gate_owner_join_status"] == (
        "EXTERNAL_ATTEMPT_REJECTION_ACKNOWLEDGED"
    )
    assert earlier["external_attempt_rejection"] is True
    assert earlier["local_gate_owner_pair_verified"] is False
    assert earlier["gate_owner_join_verified"] is False
    assert earlier["journal_replay_complete"] is True
    assert earlier["control_cap_rejections"] == 0
    assert earlier["attempt_control_cap_rejections"] == 1
    assert earlier["new_work_allowed"] is False
    assert rejecting["gate_owner_join_status"] == "LOCAL_ACK_VERIFIED"
    assert rejecting["local_gate_owner_pair_verified"] is True
    assert rejecting["gate_owner_join_verified"] is True
    assert rejecting["control_cap_rejections"] == 1
    assert owner_v3.synchronize_h1_shared_cap_rejection_v3(owner_one) is None

    reopened_one = owner_v3.open_h1_shared_cap_owner_v3(
        owner_one.owner_directory,
        expected_runtime_id=owner_one.runtime_id,
        gate_directory=owner_one.gate_directory,
    )
    recovered_waiting = _reserve(
        reopened_one,
        "recover-wrapper-after-close",
        "io.staged_bytes",
        1,
    )
    cleaned = owner_v3.settle_h1_shared_cap_owner_v3(
        reopened_one,
        recovered_waiting,
        value_basis=owner_v3.H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO,
        native_observed_value=0,
        evidence_source_id=_id("closed-attempt-known-zero"),
    )
    assert cleaned.settlement_document["charged_value"] == 0

    repeated = _settle(
        owner_one,
        reservation,
        owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        2,
        evidence_label="transaction-one-read-evidence",
    )
    assert repeated.receipt_document == first.receipt_document
    with pytest.raises(owner_v3.H1SharedCapOwnerV3Rejected):
        _reserve(owner_one, "transaction-one-late-work", "io.read_bytes", 1)


def test_recursive_reservation_inside_side_effect_guard_fails_without_deadlock(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path, suffix="recursive-reservation")
    reservation = _reserve(handle, "outer-operation", "io.read_bytes", 1)
    with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(handle, reservation):
        with pytest.raises(
            owner_v3.H1SharedCapOwnerV3ProtocolFailure,
            match="cannot reserve recursively",
        ):
            _reserve(handle, "inner-operation", "io.read_bytes", 1)


def test_nested_side_effect_guard_fails_before_inner_lifecycle_mutation(
    tmp_path: Path,
) -> None:
    handle, _ = _owner(tmp_path, suffix="nested-side-effect")
    outer = _reserve(handle, "nested-outer", "io.read_bytes", 1)
    inner = _reserve(handle, "nested-inner", "io.read_bytes", 1)
    with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(handle, outer):
        with pytest.raises(
            owner_v3.H1SharedCapOwnerV3ProtocolFailure,
            match="cannot be nested",
        ):
            with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(handle, inner):
                pass
        with pytest.raises(
            owner_v3.H1SharedCapOwnerV3ProtocolFailure,
            match="cannot synchronize",
        ):
            owner_v3.synchronize_h1_shared_cap_rejection_v3(handle)
    inner_cells = [
        document
        for document in _journal_documents(handle)
        if document.get("schema") == "acfqp.k7_h1_shared_cap_native_cell.v3"
        and document.get("h1_shared_cap_owner_v3_reservation_id")
        == inner.reservation_id
    ]
    assert inner_cells == []


def test_shared_owner_gate_commit_without_prior_admission_is_rejected(
    tmp_path: Path,
) -> None:
    caps = _caps()
    caps["io.read_bytes"] = 1
    handle, gate = _owner(tmp_path, caps=caps, suffix="missing-admission")
    rejection_v1.commit_h1_attempt_rejection_v1(
        gate,
        writer_role=rejection_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        decision_point_id=handle.profile.decision_point_id,
        transaction_id=handle.profile.transaction_id,
        shared_owner_profile_core_id=handle.profile.profile_id,
        rejection_request_id=_id("unproven-rejection-request"),
        source_kind=rejection_v1.H1RejectionSourceKindV1.SHARED_OWNER,
        site_key="site:unproven-rejection",
        path="io.read_bytes",
        limit_kind=rejection_v1.H1RejectionLimitKindV1.SHARED_PATH,
        reservation_upper=2,
        candidate=2,
        hard_cap=1,
        reason_code="SHARED_CAP_EXHAUSTED",
    )
    assert owner_v3.synchronize_h1_shared_cap_rejection_v3(handle) is None
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["gate_owner_join_status"] == "LOCAL_COMMIT_AWAITING_ADMISSION"
    assert replay["gate_owner_join_verified"] is False
    assert replay["recovery_required"] is True
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="exact rejection recovery request",
    ):
        _reserve(
            handle,
            "unknown-forged-operation",
            "io.read_bytes",
            2,
            site_key="site:unproven-rejection",
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "wrong_transaction",
        "wrong_cap",
        "wrong_candidate",
        "control_limit",
        "wrong_reason",
    ),
)
def test_missing_admission_prefix_still_validates_rejection_gate_shape(
    tmp_path: Path, mutation: str
) -> None:
    caps = _caps()
    caps["io.read_bytes"] = 1
    handle, gate = _owner(
        tmp_path,
        caps=caps,
        suffix=f"invalid-rejection-shape-{mutation}",
    )
    transaction_id = handle.profile.transaction_id
    limit_kind = rejection_v1.H1RejectionLimitKindV1.SHARED_PATH
    candidate: int | None = 2
    hard_cap = 1
    reason = "SHARED_CAP_EXHAUSTED"
    reservation_upper = 2
    if mutation == "wrong_transaction":
        transaction_id = _id("wrong-rejection-transaction")
    elif mutation == "wrong_cap":
        candidate, hard_cap = 3, 2
    elif mutation == "wrong_candidate":
        reservation_upper = 1
    elif mutation == "control_limit":
        candidate = None
        limit_kind = rejection_v1.H1RejectionLimitKindV1.CONTROL_CAP_CHECKS
    elif mutation == "wrong_reason":
        reason = "WRONG_REASON"
    rejection_v1.commit_h1_attempt_rejection_v1(
        gate,
        writer_role=rejection_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        decision_point_id=handle.profile.decision_point_id,
        transaction_id=transaction_id,
        shared_owner_profile_core_id=handle.profile.profile_id,
        rejection_request_id=_id(f"invalid-shape-request-{mutation}"),
        source_kind=rejection_v1.H1RejectionSourceKindV1.SHARED_OWNER,
        site_key=f"site:invalid-shape:{mutation}",
        path="io.read_bytes",
        limit_kind=limit_kind,
        reservation_upper=reservation_upper,
        candidate=candidate,
        hard_cap=hard_cap,
        reason_code=reason,
    )
    with pytest.raises(owner_v3.H1SharedCapOwnerV3ProtocolFailure):
        owner_v3.replay_h1_shared_cap_owner_v3(handle)


def test_independent_replay_rejects_forged_owner_rejection_without_gate_commit(
    tmp_path: Path,
) -> None:
    caps = _caps()
    caps["io.read_bytes"] = 1
    handle, gate = _owner(
        tmp_path, caps=caps, suffix="forged-owner-rejection"
    )
    admission = _append_rejection_admission(
        handle,
        operation_label="forged-owner-rejection-operation",
        site_key="site:forged-owner-rejection",
        path="io.read_bytes",
        upper=2,
    )
    forged = rejection_v1._build_commit(
        gate.spec,
        decision_point_id=handle.profile.decision_point_id,
        transaction_id=handle.profile.transaction_id,
        shared_owner_profile_core_id=handle.profile.profile_id,
        rejection_request_id=admission["rejection_request_id"],
        source_kind=rejection_v1.H1RejectionSourceKindV1.SHARED_OWNER,
        site_key="site:forged-owner-rejection",
        path="io.read_bytes",
        limit_kind=rejection_v1.H1RejectionLimitKindV1.SHARED_PATH,
        reservation_upper=2,
        candidate=2,
        hard_cap=1,
        reason_code="SHARED_CAP_EXHAUSTED",
    )
    root_fd, directory_fd, state = owner_v3._require_handle_locked(handle)
    try:
        owner_v3._append_rejection_pair_locked(
            root_fd,
            directory_fd,
            handle,
            state,
            forged,
        )
    finally:
        owner_v3.os.close(directory_fd)
        owner_v3.os.close(root_fd)
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="committed gate rejection",
    ):
        owner_v3.replay_h1_shared_cap_owner_v3(handle)


def test_joint_replay_rejects_owner_pair_semantics_forged_around_real_commit(
    tmp_path: Path,
) -> None:
    caps = _caps()
    caps["io.read_bytes"] = 1
    handle, gate = _owner(tmp_path, caps=caps, suffix="forged-pair-semantics")
    admission = _append_rejection_admission(
        handle,
        operation_label="forged-pair-operation",
        site_key="site:forged-pair",
        path="io.read_bytes",
        upper=2,
    )
    commit = rejection_v1.commit_h1_attempt_rejection_v1(
        gate,
        writer_role=rejection_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        decision_point_id=handle.profile.decision_point_id,
        transaction_id=handle.profile.transaction_id,
        shared_owner_profile_core_id=handle.profile.profile_id,
        rejection_request_id=admission["rejection_request_id"],
        source_kind=rejection_v1.H1RejectionSourceKindV1.SHARED_OWNER,
        site_key="site:forged-pair",
        path="io.read_bytes",
        limit_kind=rejection_v1.H1RejectionLimitKindV1.SHARED_PATH,
        reservation_upper=2,
        candidate=2,
        hard_cap=1,
        reason_code="SHARED_CAP_EXHAUSTED",
    )
    root_fd, directory_fd, state = owner_v3._require_handle_locked(handle)
    try:
        wrong = dict(owner_v3._rejection_pair_extra(commit))
        wrong["path"] = "io.output_bytes"
        wrong["reservation_upper"] = 999
        pair = owner_v3._append_receipt_event_snapshot(
            root_fd,
            directory_fd,
            handle,
            state,
            pair_extra=wrong,
        )
    finally:
        owner_v3.os.close(directory_fd)
        owner_v3.os.close(root_fd)
    rejection_v1.acknowledge_h1_attempt_rejection_v1(
        gate,
        commit,
        writer_role=rejection_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        shared_owner_receipt_id=owner_v3._record_id(pair[0]),
        shared_owner_event_id=owner_v3._record_id(pair[1]),
        shared_owner_snapshot_id=owner_v3._record_id(pair[2]),
    )
    with pytest.raises(
        owner_v3.H1SharedCapOwnerV3ProtocolFailure,
        match="exact gate commit",
    ):
        owner_v3.replay_h1_shared_cap_owner_v3(handle)


def test_append_preflight_prevents_burying_a_partial_semantic_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    handle, _ = _owner(tmp_path, suffix="buried-pair")
    first = _reserve(handle, "buried-first", "io.read_bytes", 2)
    original = owner_v3._append_record
    crashed = False

    def append_then_crash(*args, **kwargs):
        nonlocal crashed
        document = original(*args, **kwargs)
        if (
            kwargs["schema"] == "acfqp.k7_h1_shared_cap_receipt.v3"
            and not crashed
        ):
            crashed = True
            raise RuntimeError("leave receipt head")
        return document

    monkeypatch.setattr(owner_v3, "_append_record", append_then_crash)
    with pytest.raises(RuntimeError, match="receipt head"):
        _settle(
            handle,
            first,
            owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
            2,
            evidence_label="buried-first-evidence",
        )
    monkeypatch.setattr(owner_v3, "_append_record", original)

    root_fd, directory_fd, state = owner_v3._require_handle_locked(handle)
    try:
        document, _ = owner_v3._reservation_document_for_request(
            handle,
            state,
            operation_id=_id("forged-unrelated-reservation"),
            site_key="site:forged-unrelated",
            path="io.staged_bytes",
            reservation_upper=1,
        )
        before_names = sorted(Path(handle.owner_directory).glob("[0-9]*.json"))
        with pytest.raises(
            owner_v3.H1SharedCapOwnerV3ProtocolFailure,
            match="immediately followed",
        ):
            owner_v3._append_record(
                root_fd,
                directory_fd,
                handle,
                state,
                schema="acfqp.k7_h1_shared_cap_reservation.v3",
                kind="RESERVATION_DURABLE",
                extra={
                    key: value
                    for key, value in document.items()
                    if key
                    in owner_v3._EXTRA_FIELDS[
                        "acfqp.k7_h1_shared_cap_reservation.v3"
                    ]
                },
            )
        assert sorted(Path(handle.owner_directory).glob("[0-9]*.json")) == (
            before_names
        )
    finally:
        owner_v3.os.close(directory_fd)
        owner_v3.os.close(root_fd)
    replay = owner_v3.replay_h1_shared_cap_owner_v3(handle)
    assert replay["recovery_required"] is True
    assert replay["semantic_pair_frontier"]["stage"] == "RECEIPT"
