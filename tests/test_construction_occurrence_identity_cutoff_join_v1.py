from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_accounting_evidence_closure_v1 as closure_v1
from acfqp import construction_occurrence_identity_cutoff_join_v1 as join_v1
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp import v075_k7_root_cap_owned_partial_runner_v1 as owned_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests import test_v075_observer_signed_multiround_occurrence_runner_v2 as owned_fixture
from tests import test_v075_private_observer_boundary_v2 as observer_fixture


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:construction-identity-cutoff-join-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


_METHOD_KINDS = {
    "common.hash_invocations": (
        receipts_v1.MeasurementMethodKindV1.RECURSION_SAFE_HASH_METER
    ),
    "common.integrity_checks": (
        receipts_v1.MeasurementMethodKindV1.NAMED_OBLIGATION_METER
    ),
    "common.protocol_checks": (
        receipts_v1.MeasurementMethodKindV1.NAMED_OBLIGATION_METER
    ),
    "io.mounted_bytes_peak": (
        receipts_v1.MeasurementMethodKindV1.MOUNT_MANIFEST_PEAK_MONITOR
    ),
    "io.output_bytes": (
        receipts_v1.MeasurementMethodKindV1.EXACT_BYTE_TRANSFER_MONITOR
    ),
    "io.read_bytes": (
        receipts_v1.MeasurementMethodKindV1.EXACT_BYTE_TRANSFER_MONITOR
    ),
    "io.staged_bytes": (
        receipts_v1.MeasurementMethodKindV1.EXACT_BYTE_TRANSFER_MONITOR
    ),
    "memory.working_bytes_peak": (
        receipts_v1.MeasurementMethodKindV1.WORKING_SET_PEAK_MONITOR
    ),
    "process.launches": (
        receipts_v1.MeasurementMethodKindV1.PROCESS_SUPERVISOR
    ),
}


def _receipt_set(
    label: str = "receipt",
    *,
    boundary_profile_id: str | None = None,
    execution_profile_id: str | None = None,
    occurrence_id: str | None = None,
) -> receipts_v1.SharedResourceReceiptSetV1:
    counter_registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(counter_registry)
    authority_id = _id(f"{label}-authority")
    methods = tuple(
        receipts_v1.freeze_shared_resource_measurement_method_v1(
            path=path,
            method_kind=_METHOD_KINDS[path],
            primitive=f"test.{path}.primitive",
        )
        for path in receipts_v1.SHARED_RESOURCE_PATHS
    )
    monitors = tuple(
        sorted(
            (
                receipts_v1.SharedResourceMonitorRegistrationV1(
                    registration_authority_id=authority_id,
                    monitor_key=f"test.{method.path}.monitor",
                    monitor_code_id=_id(f"{label}-{method.path}-code"),
                    source_module=(
                        "acfqp.construction_shared_resource_receipts_v1"
                    ),
                    source_symbol="SharedResourceMonitorRegistrationV1",
                    isolation_kind=(
                        receipts_v1.MonitorIsolationKindV1
                        .OUT_OF_PROCESS_SUPERVISOR
                    ),
                    measurement_method_ids=(method.method_id,),
                    zero_attestable_paths=(method.path,),
                    observes_complete_window=True,
                )
                for method in methods
            ),
            key=lambda row: row.monitor_registration_id,
        )
    )
    measurement_registry = receipts_v1.SharedResourceMeasurementRegistryV1(
        counter_registry_id=counter_registry.registry_id,
        registration_authority_id=authority_id,
        methods=methods,
        monitors=monitors,
    )
    identity = receipts_v1.SharedResourceIdentityBindingV1(
        counter_registry_id=counter_registry.registry_id,
        stage_profile_id=stage_profile.stage_profile_id,
        boundary_profile_id=(boundary_profile_id or _id(f"{label}-boundary")),
        execution_profile_id=(execution_profile_id or _id(f"{label}-execution")),
        occurrence_id=(occurrence_id or _id(f"{label}-occurrence")),
        route_attempt_id=_id(f"{label}-route-attempt"),
        decision_point_id=_id(f"{label}-decision-point"),
    )
    window = receipts_v1.SharedResourceMeasurementWindowV1(
        identity_binding_id=identity.identity_binding_id,
        window_key=f"test.{label}.window",
        start_marker_id=_id(f"{label}-window-start"),
        cutoff_marker_id=_id(f"{label}-window-cutoff"),
        start_sequence=10,
        cutoff_sequence=30,
        state=receipts_v1.MeasurementWindowStateV1.CLOSED,
    )
    rows = []
    for path in receipts_v1.SHARED_RESOURCE_PATHS:
        method = measurement_registry.method_by_path[path]
        monitor = measurement_registry.monitor_by_method_id[method.method_id]
        source_schema_id = "acfqp.test.complete_window_zero.v1"
        source_artifact_id = _id(f"{label}-{path}-source")
        source = receipts_v1.SharedResourceSourceEvidenceV1(
            measurement_registry_id=(
                measurement_registry.measurement_registry_id
            ),
            method_id=method.method_id,
            monitor_registration_id=monitor.monitor_registration_id,
            identity_binding_id=identity.identity_binding_id,
            window_id=window.window_id,
            evidence_kind=(
                receipts_v1.SourceEvidenceKindV1
                .COMPLETE_WINDOW_ZERO_ATTESTATION
            ),
            source_schema_id=source_schema_id,
            source_artifact_id=source_artifact_id,
            evidence_bytes_sha256=_id(f"{label}-{path}-bytes"),
            charge_key=receipts_v1.shared_resource_charge_key_v1(
                measurement_registry_id=(
                    measurement_registry.measurement_registry_id
                ),
                method_id=method.method_id,
                monitor_registration_id=monitor.monitor_registration_id,
                identity_binding_id=identity.identity_binding_id,
                window_id=window.window_id,
                source_schema_id=source_schema_id,
                source_artifact_id=source_artifact_id,
                covered_start_sequence=window.start_sequence,
                covered_cutoff_sequence=window.cutoff_sequence,
            ),
            covered_start_sequence=window.start_sequence,
            covered_cutoff_sequence=window.cutoff_sequence,
            reported_value=0,
            observed_event_count=0,
            complete_through_cutoff=True,
            immutable_at_cutoff=True,
        )
        rows.append(
            receipts_v1.SharedResourceReceiptV1(
                registry=measurement_registry,
                identity=identity,
                window=window,
                path=path,
                status=receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED,
                source_claim_present=True,
                value=0,
                method_id=method.method_id,
                monitor_registration_id=monitor.monitor_registration_id,
                source_evidence=source,
            )
        )
    return receipts_v1.SharedResourceReceiptSetV1(
        measurement_registry,
        identity,
        window,
        tuple(rows),
    )


def _schema_join(
    receipt_set: receipts_v1.SharedResourceReceiptSetV1,
) -> join_v1.ConstructionOccurrenceIdentityJoinV1:
    identity = receipt_set.identity
    counter_registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(counter_registry)
    return join_v1.ConstructionOccurrenceIdentityJoinV1(
        _issuer=join_v1._JOIN_ISSUER,  # noqa: SLF001 - schema attack fixture
        owned_partial_result_id=_id("owned-result"),
        original_result_id=_id("original-result"),
        evidence_closure_context_id=_id("closure-context"),
        evidence_closure_id=_id("closure"),
        shared_resource_identity_binding_id=identity.identity_binding_id,
        shared_resource_receipt_set_id=receipt_set.receipt_set_id,
        shared_resource_measurement_window_id=receipt_set.window.window_id,
        counter_registry_id=counter_registry.registry_id,
        stage_profile_id=stage_profile.stage_profile_id,
        boundary_profile_id=identity.boundary_profile_id,
        execution_profile_id=identity.execution_profile_id,
        occurrence_id=identity.occurrence_id,
        route_attempt_id=identity.route_attempt_id,
        decision_point_id=identity.decision_point_id,
        partial_native_transcript_id=_id("transcript"),
        transcript_terminal_id=_id("transcript-terminal"),
        transcript_terminal_kind="COMPLETED",
        execution_terminal_status="CHILD_ACTION_ROW_CAP_EXCEEDED",
        execution_status=(
            join_v1.ConstructionExecutionStatusV1.OWNED_PARTIAL_COMPLETED
        ),
        route_context_authority=(
            join_v1._missing_route_context_authority()  # noqa: SLF001
        ),
        cutoff_authority=join_v1._missing_cutoff_authority(),  # noqa: SLF001
    )


@pytest.fixture(scope="module")
def exact_owned_result() -> owned_v1.V075K7RootCapOwnedPartialResultV1:
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture("identity-cutoff-positive-join")  # noqa: SLF001
    )
    schedule, verification = owned_fixture._exact_schedule(
        namespace, context_index=0
    )
    return owned_v1.run_v075_k7_root_cap_owned_partial_v1(
        repository_root=owned_fixture.REPOSITORY_ROOT,
        namespace=namespace,
        schedule=schedule,
        schedule_verification=verification,
        authority=authorization,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id("exact-owned-session"),
    )


def test_exact_owned_result_positive_join_and_terminal_transplant_rejection(
    exact_owned_result: owned_v1.V075K7RootCapOwnedPartialResultV1,
) -> None:
    wrapped = exact_owned_result
    terminal_id = wrapped.transcript.nodes[-1].chain_id
    context = closure_v1.EvidenceClosureContextV1(
        wrapped.counter_registry_id,
        wrapped.stage_profile_id,
        wrapped.boundary_profile_id,
        wrapped.execution_profile_id,
        wrapped.transcript.transcript_id,
        terminal_id,
    )
    closure = closure_v1.initialize_evidence_closure_v1(context)
    receipt_set = _receipt_set(
        "exact-owned",
        boundary_profile_id=wrapped.boundary_profile_id,
        execution_profile_id=wrapped.execution_profile_id,
        occurrence_id=wrapped.transcript.start.occurrence_id,
    )
    joined = join_v1.freeze_construction_occurrence_identity_join_v1(
        owned_result=wrapped,
        evidence_closure=closure,
        receipt_set=receipt_set,
    )
    assert joined.owned_partial_result_id == wrapped.wrapper_id
    assert joined.partial_native_transcript_id == wrapped.transcript.transcript_id
    assert joined.transcript_terminal_id == terminal_id
    assert joined.occurrence_id == wrapped.transcript.start.occurrence_id
    joined_document = joined.to_document()
    assert joined_document["structural_identity_join_only"] is True
    assert joined_document["route_context_semantics_independently_replayed"] is False
    assert joined_document["shared_receipt_semantics_independently_replayed"] is False
    assert joined_document["cutoff_semantics_independently_replayed"] is False

    foreign_context = replace(context, terminal_id=_id("foreign-terminal"))
    foreign_closure = closure_v1.initialize_evidence_closure_v1(foreign_context)
    with pytest.raises(
        join_v1.ConstructionOccurrenceIdentityCutoffJoinV1Error,
        match="do not join exactly",
    ):
        join_v1.freeze_construction_occurrence_identity_join_v1(
            owned_result=wrapped,
            evidence_closure=foreign_closure,
            receipt_set=receipt_set,
        )


def _markers(
    identity_join: join_v1.ConstructionOccurrenceIdentityJoinV1,
    receipt_set: receipts_v1.SharedResourceReceiptSetV1,
) -> tuple[join_v1.OperationalSequenceMarkerV1, ...]:
    window = receipt_set.window
    return (
        join_v1.OperationalSequenceMarkerV1(
            window.start_sequence,
            join_v1.OperationalSequenceKindV1.WINDOW_START,
            "measurement.window.start",
            window.start_marker_id,
        ),
        join_v1.OperationalSequenceMarkerV1(
            15,
            join_v1.OperationalSequenceKindV1.BUSINESS_WORK,
            "owned.partial.business.work",
            _id("business-work"),
        ),
        join_v1.OperationalSequenceMarkerV1(
            20,
            join_v1.OperationalSequenceKindV1.TRANSCRIPT_TERMINAL,
            "partial.native.transcript.terminal",
            identity_join.transcript_terminal_id,
        ),
        join_v1.OperationalSequenceMarkerV1(
            window.cutoff_sequence,
            join_v1.OperationalSequenceKindV1.OPERATIONAL_CUTOFF,
            "operational.measurement.cutoff",
            window.cutoff_marker_id,
        ),
        join_v1.OperationalSequenceMarkerV1(
            31,
            join_v1.OperationalSequenceKindV1.ACCOUNTING_TAIL,
            "accounting.receipts.tail",
            _id("accounting-tail"),
        ),
        join_v1.OperationalSequenceMarkerV1(
            32,
            join_v1.OperationalSequenceKindV1.PROVENANCE_TAIL,
            "provenance.identity.tail",
            _id("provenance-tail"),
        ),
    )


def test_cutoff_order_replays_but_never_authorizes_formal_vectors() -> None:
    receipt_set = _receipt_set()
    identity_join = _schema_join(receipt_set)
    cutoff = join_v1.freeze_operational_cutoff_attestation_v1(
        identity_join=identity_join,
        receipt_set=receipt_set,
        markers=_markers(identity_join, receipt_set),
    )
    replay = join_v1.verify_operational_cutoff_attestation_v1(
        cutoff,
        identity_join=identity_join,
        receipt_set=receipt_set,
    )

    assert replay.last_business_sequence == 15
    assert replay.cutoff_sequence == 30
    assert replay.accounting_tail_count == 1
    assert replay.provenance_tail_count == 1
    replay_document = replay.to_document()
    cutoff_document = cutoff.to_document()
    assert replay_document["ordered_marker_structure_replayed"] is True
    assert replay_document["marker_structure_contains_business_work_after_cutoff"] is False
    assert replay_document["source_event_bytes_independently_replayed"] is False
    assert replay_document["source_event_business_work_after_cutoff"] == {
        "kind": "UNKNOWN",
        "reason": "SOURCE_EVENT_BYTES_NOT_INDEPENDENTLY_REPLAYED",
    }
    assert replay_document["post_cutoff_tail_output_byte_exclusion_verified"] == {
        "kind": "UNKNOWN",
        "reason": "OUTPUT_BYTE_RECEIPT_NOT_SEMANTICALLY_REPLAYED",
    }
    assert replay_document["formal_vector_authorized"] is False
    assert cutoff_document[
        "marker_policy_declares_business_work_forbidden_after_cutoff"
    ] is True
    assert cutoff_document["post_cutoff_business_work_absence_verified"][
        "kind"
    ] == "UNKNOWN"
    assert cutoff_document[
        "post_cutoff_tail_output_byte_exclusion_verified"
    ]["kind"] == "UNKNOWN"


def test_business_work_after_operational_cutoff_is_rejected() -> None:
    receipt_set = _receipt_set("post-cutoff")
    identity_join = _schema_join(receipt_set)
    rows = list(_markers(identity_join, receipt_set))
    rows[1] = replace(rows[1], sequence=33)

    with pytest.raises(
        join_v1.ConstructionOccurrenceIdentityCutoffJoinV1Error,
        match="operational cutoff",
    ):
        join_v1.freeze_operational_cutoff_attestation_v1(
            identity_join=identity_join,
            receipt_set=receipt_set,
            markers=tuple(sorted(rows, key=lambda row: row.sequence)),
        )


def test_terminalization_work_between_transcript_terminal_and_cutoff_is_allowed() -> None:
    receipt_set = _receipt_set("terminalization-window")
    identity_join = _schema_join(receipt_set)
    rows = list(_markers(identity_join, receipt_set))
    rows[1] = replace(rows[1], sequence=25)
    cutoff = join_v1.freeze_operational_cutoff_attestation_v1(
        identity_join=identity_join,
        receipt_set=receipt_set,
        markers=tuple(sorted(rows, key=lambda row: row.sequence)),
    )
    replay = join_v1.verify_operational_cutoff_attestation_v1(
        cutoff,
        identity_join=identity_join,
        receipt_set=receipt_set,
    )
    assert replay.last_business_sequence == 25
    assert replay.cutoff_sequence == 30
    assert replay.to_document()["source_event_business_work_after_cutoff"][
        "kind"
    ] == "UNKNOWN"


def test_accounting_and_provenance_tails_are_both_mandatory() -> None:
    receipt_set = _receipt_set("tails")
    identity_join = _schema_join(receipt_set)
    rows = tuple(
        row
        for row in _markers(identity_join, receipt_set)
        if row.kind is not join_v1.OperationalSequenceKindV1.PROVENANCE_TAIL
    )
    with pytest.raises(
        join_v1.ConstructionOccurrenceIdentityCutoffJoinV1Error,
        match="tails must both be explicit",
    ):
        join_v1.freeze_operational_cutoff_attestation_v1(
            identity_join=identity_join,
            receipt_set=receipt_set,
            markers=rows,
        )


def test_cutoff_rejects_crossed_route_identity() -> None:
    receipt_set = _receipt_set("crossed")
    identity_join = _schema_join(receipt_set)
    foreign = replace(
        identity_join,
        _issuer=join_v1._JOIN_ISSUER,  # noqa: SLF001 - attack
        route_attempt_id=_id("foreign-route-attempt"),
    )
    with pytest.raises(
        join_v1.ConstructionOccurrenceIdentityCutoffJoinV1Error,
        match="receipt identity differs",
    ):
        join_v1.freeze_operational_cutoff_attestation_v1(
            identity_join=foreign,
            receipt_set=receipt_set,
            markers=_markers(foreign, receipt_set),
        )


def test_join_and_cutoff_cannot_be_caller_minted() -> None:
    receipt_set = _receipt_set("mint")
    identity_join = _schema_join(receipt_set)
    with pytest.raises(
        join_v1.ConstructionOccurrenceIdentityCutoffJoinV1Error,
        match="caller-minted",
    ):
        replace(identity_join, _issuer=object())

    cutoff = join_v1.freeze_operational_cutoff_attestation_v1(
        identity_join=identity_join,
        receipt_set=receipt_set,
        markers=_markers(identity_join, receipt_set),
    )
    with pytest.raises(
        join_v1.ConstructionOccurrenceIdentityCutoffJoinV1Error,
        match="caller-minted",
    ):
        replace(cutoff, _issuer=object())


def test_schema_join_does_not_accept_fake_owned_or_closure_roots() -> None:
    receipt_set = _receipt_set("fake-roots")
    with pytest.raises(
        join_v1.ConstructionOccurrenceIdentityCutoffJoinV1Error,
        match="exact typed",
    ):
        join_v1.freeze_construction_occurrence_identity_join_v1(
            owned_result=object(),  # type: ignore[arg-type]
            evidence_closure=object(),  # type: ignore[arg-type]
            receipt_set=receipt_set,
        )
    with pytest.raises(
        join_v1.ConstructionOccurrenceIdentityCutoffJoinV1Error,
        match="exact owned",
    ):
        join_v1.assess_current_identity_join_readiness_v1(
            owned_result=object(),  # type: ignore[arg-type]
            evidence_closure=object(),  # type: ignore[arg-type]
        )


def test_requested_domains_are_explicit_and_distinct() -> None:
    assert len(join_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) == 6
    assert all(
        value.startswith("acfqp:construction-")
        for value in join_v1.REQUESTED_PHASE3E_DOMAIN_TAGS
    )
    assert join_v1.REQUESTED_PHASE3E_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
