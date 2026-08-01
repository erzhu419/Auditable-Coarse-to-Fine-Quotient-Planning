from __future__ import annotations

from dataclasses import replace
from functools import cache
import hashlib

import pytest

from acfqp import construction_accounting_evidence_closure_v1 as closure_v1
from acfqp import construction_accounting_partial_native_v1 as partial_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp.accounting_v1 import LaneEnum, ReducerEnum


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:construction-accounting-completion-contract-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _context(label: str = "context") -> closure_v1.EvidenceClosureContextV1:
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    return closure_v1.EvidenceClosureContextV1(
        counter_registry_id=registry.registry_id,
        stage_profile_id=stage_profile.stage_profile_id,
        boundary_profile_id=_id(f"{label}-boundary"),
        execution_profile_id=_id(f"{label}-execution"),
        transcript_id=_id(f"{label}-transcript"),
        terminal_id=_id(f"{label}-terminal"),
    )


@cache
def _fresh_closure(
    label: str = "context",
) -> closure_v1.EvidenceClosureV1:
    return closure_v1.initialize_evidence_closure_v1(_context(label))


@cache
def _structurally_closed_but_unverified_closure(
    label: str = "syntactic-closure",
) -> closure_v1.EvidenceClosureV1:
    """Construct coverage refs only; none of their semantics are verified."""

    selected = registry_v6.official_counter_registry_v6()
    context = _context(label)
    rows: list[closure_v1.RequiredPathResolutionV1] = []
    dependency = "acquisition.initial_signed_batches"
    for path in selected.required_paths:
        leaf = selected.by_path[path]
        if leaf.lane is LaneEnum.DERIVED_ONLY:
            row = closure_v1.RequiredPathResolutionV1(
                context_id=context.context_id,
                path=path,
                reducer=leaf.reducer,
                resolution_kind=(
                    closure_v1.RequiredPathResolutionKindV1.DERIVED_RECONCILIATION
                ),
                resolved_value=0,
                source_evidence_ids=(
                    _id(f"{label}-{path}-syntactic-reconciliation-ref"),
                ),
                dependency_paths=(dependency,),
                formula_id=_id(f"{label}-{path}-syntactic-formula-ref"),
            )
        elif path in closure_v1.SHARED_RESOURCE_PATHS_V1:
            row = closure_v1.RequiredPathResolutionV1(
                context_id=context.context_id,
                path=path,
                reducer=leaf.reducer,
                resolution_kind=(
                    closure_v1.RequiredPathResolutionKindV1.SHARED_RESOURCE_RECEIPT
                ),
                resolved_value=0,
                source_evidence_ids=(
                    _id(f"{label}-{path}-syntactic-receipt-ref"),
                ),
            )
        else:
            row = closure_v1.RequiredPathResolutionV1(
                context_id=context.context_id,
                path=path,
                reducer=leaf.reducer,
                resolution_kind=(
                    closure_v1.RequiredPathResolutionKindV1.PROFILE_NATIVE_ZERO
                ),
                resolved_value=0,
                source_evidence_ids=(
                    _id(f"{label}-{path}-syntactic-zero-attestation-ref"),
                ),
            )
        rows.append(row)
    return closure_v1.EvidenceClosureV1(context, tuple(rows))


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


def _receipt_authorities(label: str = "receipts"):
    counter_registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(counter_registry)
    authority_id = _id(f"{label}-registration-authority")
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
                    source_module="acfqp.construction_shared_resource_receipts_v1",
                    source_symbol="SharedResourceMonitorRegistrationV1",
                    isolation_kind=(
                        receipts_v1.MonitorIsolationKindV1.OUT_OF_PROCESS_SUPERVISOR
                    ),
                    measurement_method_ids=(method.method_id,),
                    zero_attestable_paths=(method.path,),
                    observes_complete_window=True,
                )
                for method in methods
            ),
            key=lambda item: item.monitor_registration_id,
        )
    )
    registry = receipts_v1.SharedResourceMeasurementRegistryV1(
        counter_registry_id=counter_registry.registry_id,
        registration_authority_id=authority_id,
        methods=methods,
        monitors=monitors,
    )
    identity = receipts_v1.SharedResourceIdentityBindingV1(
        counter_registry_id=counter_registry.registry_id,
        stage_profile_id=stage_profile.stage_profile_id,
        boundary_profile_id=_id(f"{label}-boundary"),
        execution_profile_id=_id(f"{label}-execution"),
        occurrence_id=_id(f"{label}-occurrence"),
        route_attempt_id=_id(f"{label}-attempt"),
        decision_point_id=_id(f"{label}-decision"),
    )
    window = receipts_v1.SharedResourceMeasurementWindowV1(
        identity_binding_id=identity.identity_binding_id,
        window_key=f"test.{label}.window",
        start_marker_id=_id(f"{label}-start"),
        cutoff_marker_id=_id(f"{label}-cutoff"),
        start_sequence=1,
        cutoff_sequence=9,
        state=receipts_v1.MeasurementWindowStateV1.CLOSED,
    )
    return registry, identity, window


@cache
def _zero_receipt_set(
    label: str = "zero-receipts",
) -> receipts_v1.SharedResourceReceiptSetV1:
    registry, identity, window = _receipt_authorities(label)
    receipt_rows = []
    for path in receipts_v1.SHARED_RESOURCE_PATHS:
        method = registry.method_by_path[path]
        monitor = registry.monitor_by_method_id[method.method_id]
        source_artifact_id = _id(f"{label}-{path}-source")
        source_schema_id = "acfqp.test.complete_window_zero.v1"
        source = receipts_v1.SharedResourceSourceEvidenceV1(
            measurement_registry_id=registry.measurement_registry_id,
            method_id=method.method_id,
            monitor_registration_id=monitor.monitor_registration_id,
            identity_binding_id=identity.identity_binding_id,
            window_id=window.window_id,
            evidence_kind=(
                receipts_v1.SourceEvidenceKindV1.COMPLETE_WINDOW_ZERO_ATTESTATION
            ),
            source_schema_id=source_schema_id,
            source_artifact_id=source_artifact_id,
            evidence_bytes_sha256=_id(f"{label}-{path}-bytes"),
            charge_key=receipts_v1.shared_resource_charge_key_v1(
                measurement_registry_id=registry.measurement_registry_id,
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
        receipt_rows.append(
            receipts_v1.SharedResourceReceiptV1(
                registry=registry,
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
        registry, identity, window, tuple(receipt_rows)
    )


def test_missing_receipts_remain_unresolved_and_block_formal_completion() -> None:
    evidence = _fresh_closure()
    replay = closure_v1.verify_evidence_closure_coverage_v1(evidence)

    assert (
        replay.coverage_state
        is closure_v1.EvidenceClosureCoverageStateV1.INCOMPLETE
    )
    assert replay.completeness is replay.coverage_state
    assert replay.required_path_count == 202
    assert replay.resolved_path_count == 0
    assert set(closure_v1.SHARED_RESOURCE_PATHS_V1).issubset(
        replay.unresolved_paths
    )
    assert evidence.to_document()["missing_paths_inferred_zero"] is False
    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="incomplete",
    ):
        closure_v1.require_complete_structural_coverage_v1(evidence)


def test_complete_row_coverage_remains_explicitly_semantically_unverified() -> None:
    evidence = _structurally_closed_but_unverified_closure()
    replay = closure_v1.require_complete_structural_coverage_v1(evidence)
    document = replay.to_document()
    closure_document = evidence.to_document()

    assert (
        replay.coverage_state
        is closure_v1.EvidenceClosureCoverageStateV1.COMPLETE_UNVERIFIED
    )
    assert replay.completeness is replay.coverage_state
    assert document["coverage_state"] == (
        "STRUCTURAL_COVERAGE_COMPLETE_UNVERIFIED"
    )
    assert document["coverage_only"] is True
    assert document["source_evidence_semantics_verified"] is False
    assert document["numeric_projection_allowed"] is False
    assert document["formal_vector_authorized"] is False
    assert closure_document["coverage_only"] is True
    assert closure_document["source_evidence_semantics_verified"] is False
    assert closure_document["numeric_projection_allowed"] is False
    assert closure_document["formal_vector_authorized"] is False
    assert "COMPLETE_EVIDENCE" not in str(document)


def test_structural_coverage_replay_cannot_be_directly_constructed() -> None:
    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="only be issued",
    ):
        closure_v1.EvidenceClosureCoverageReplayV1()


def test_unknown_or_unresolved_cannot_be_relabelled_as_zero() -> None:
    evidence = _fresh_closure()
    path = "common.hash_invocations"
    unresolved = evidence.by_path[path]

    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="UNRESOLVED cannot carry",
    ):
        replace(unresolved, resolved_value=0)

    forged_zero = closure_v1.RequiredPathResolutionV1(
        context_id=evidence.context.context_id,
        path=path,
        reducer=ReducerEnum.SUM,
        resolution_kind=(
            closure_v1.RequiredPathResolutionKindV1.PROFILE_NATIVE_ZERO
        ),
        resolved_value=0,
        source_evidence_ids=(_id("forged-zero"),),
    )
    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="requires its typed receipt",
    ):
        closure_v1.apply_required_path_resolution_v1(evidence, forged_zero)


def test_wrong_reducer_and_foreign_identity_fail_closed() -> None:
    evidence = _fresh_closure()
    mounted_path = "io.mounted_bytes_peak"
    wrong_reducer = closure_v1.RequiredPathResolutionV1(
        context_id=evidence.context.context_id,
        path=mounted_path,
        reducer=ReducerEnum.SUM,
        resolution_kind=(
            closure_v1.RequiredPathResolutionKindV1.SHARED_RESOURCE_RECEIPT
        ),
        resolved_value=17,
        source_evidence_ids=(_id("mounted-receipt"),),
    )
    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="metadata differs",
    ):
        closure_v1.apply_required_path_resolution_v1(
            evidence, wrong_reducer
        )

    foreign_context = _context("foreign")
    foreign_resolution = closure_v1.RequiredPathResolutionV1(
        context_id=foreign_context.context_id,
        path="common.hash_invocations",
        reducer=ReducerEnum.SUM,
        resolution_kind=(
            closure_v1.RequiredPathResolutionKindV1.SHARED_RESOURCE_RECEIPT
        ),
        resolved_value=1,
        source_evidence_ids=(_id("foreign-receipt"),),
    )
    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="another closure context",
    ):
        closure_v1.apply_required_path_resolution_v1(
            evidence, foreign_resolution
        )


def test_duplicate_path_and_duplicate_evidence_charge_are_rejected() -> None:
    evidence = _fresh_closure()
    first = evidence.resolutions[0]
    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="unique",
    ):
        closure_v1.EvidenceClosureV1(
            evidence.context,
            (first, first, *evidence.resolutions[1:]),
        )

    shared_evidence_id = _id("one-charge-key")
    evidence = closure_v1.resolve_profile_native_zero_v1(
        evidence,
        path="acquisition.initial_signed_batches",
        zero_attestation_id=shared_evidence_id,
    )
    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="evidence|consumed|charge",
    ):
        closure_v1.resolve_profile_native_zero_v1(
            evidence,
            path="acquisition.initial_support_freezes",
            zero_attestation_id=shared_evidence_id,
        )


def test_sum_and_max_resolution_families_cannot_be_substituted() -> None:
    evidence = _fresh_closure()
    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="positive SUM events only",
    ):
        closure_v1.RequiredPathResolutionV1(
            context_id=evidence.context.context_id,
            path="io.mounted_bytes_peak",
            reducer=ReducerEnum.MAX,
            resolution_kind=(
                closure_v1.RequiredPathResolutionKindV1.POSITIVE_EVENT_STREAM
            ),
            resolved_value=9,
            source_evidence_ids=(_id("peak-event"),),
        )

    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="shared path",
    ):
        closure_v1.resolve_positive_event_stream_v1(
            evidence,
            path="common.protocol_checks",
            resolved_value=1,
            event_ids=(_id("protocol-event"),),
        )


def test_receipt_set_requires_all_nine_paths_once() -> None:
    complete = _zero_receipt_set()
    assert complete.all_receipts_structurally_recorded is True
    assert complete.unverified_reported_values == {
        path: 0 for path in receipts_v1.SHARED_RESOURCE_PATHS
    }
    document = complete.to_document()
    assert document["coverage_state"] == (
        "ALL_SOURCE_CLAIMS_STRUCTURALLY_RECORDED_UNVERIFIED"
    )
    assert document["source_evidence_semantics_verified"] is False
    assert document["numeric_projection_allowed"] is False
    assert document["formal_vector_authorized"] is False
    first_receipt = complete.receipts[0]
    assert type(first_receipt.source_evidence) is (
        receipts_v1.SharedResourceSourceEvidenceV1
    )
    source_document = first_receipt.source_evidence.to_document()
    assert source_document["source_claim_only"] is True
    assert source_document["source_evidence_semantics_verified"] is False
    assert source_document["numeric_value_authorized"] is False
    receipt_document = first_receipt.to_document()
    assert receipt_document["source_evidence_semantics_verified"] is False
    assert receipt_document["numeric_value_authorized"] is False
    receipts_v1.replay_shared_resource_receipt_set_structure_v1(
        complete, require_all_structurally_recorded=True
    )

    with pytest.raises(
        receipts_v1.ConstructionSharedResourceReceiptsV1Error,
        match="exactly the nine",
    ):
        receipts_v1.SharedResourceReceiptSetV1(
            complete.registry,
            complete.identity,
            complete.window,
            complete.receipts[:-1],
        )
    with pytest.raises(
        receipts_v1.ConstructionSharedResourceReceiptsV1Error,
        match="exactly the nine",
    ):
        receipts_v1.SharedResourceReceiptSetV1(
            complete.registry,
            complete.identity,
            complete.window,
            (complete.receipts[0], *complete.receipts[:-1]),
        )


def test_typed_unknown_cannot_masquerade_as_observed_zero() -> None:
    complete = _zero_receipt_set()
    original = complete.receipts[0]
    unavailable = receipts_v1.TypedUnavailableMeasurementV1(
        receipts_v1.MeasurementStatusV1.UNKNOWN,
        "MONITOR_NOT_INSTALLED",
    )
    unknown = replace(
        original,
        status=receipts_v1.MeasurementStatusV1.UNKNOWN,
        source_claim_present=False,
        value=unavailable,
        source_evidence=unavailable,
    )
    incomplete = receipts_v1.SharedResourceReceiptSetV1(
        complete.registry,
        complete.identity,
        complete.window,
        (unknown, *complete.receipts[1:]),
    )
    assert incomplete.all_receipts_structurally_recorded is False
    with pytest.raises(
        receipts_v1.ConstructionSharedResourceReceiptsV1Error,
        match="cannot expose all source claims",
    ):
        _ = incomplete.unverified_reported_values
    with pytest.raises(
        receipts_v1.ConstructionSharedResourceReceiptsV1Error,
        match="UNKNOWN/NOT_AVAILABLE",
    ):
        receipts_v1.replay_shared_resource_receipt_set_structure_v1(
            incomplete, require_all_structurally_recorded=True
        )
    with pytest.raises(
        receipts_v1.ConstructionSharedResourceReceiptsV1Error,
        match="must remain typed",
    ):
        replace(unknown, value=0)


def test_receipt_wrong_owner_reducer_method_and_identity_are_rejected() -> None:
    complete = _zero_receipt_set()
    read_method = complete.registry.method_by_path["io.read_bytes"]
    with pytest.raises(
        receipts_v1.ConstructionSharedResourceReceiptsV1Error,
        match="metadata differs from V6",
    ):
        replace(read_method, owner="caller_supplied_fake_owner")
    with pytest.raises(
        receipts_v1.ConstructionSharedResourceReceiptsV1Error,
        match="metadata differs from V6",
    ):
        replace(read_method, reducer=ReducerEnum.MAX)

    mounted_method = complete.registry.method_by_path[
        "io.mounted_bytes_peak"
    ]
    with pytest.raises(
        receipts_v1.ConstructionSharedResourceReceiptsV1Error,
        match="metadata differs from V6",
    ):
        replace(mounted_method, reducer=ReducerEnum.SUM)

    foreign_identity = replace(
        complete.identity, occurrence_id=_id("foreign-occurrence")
    )
    with pytest.raises(
        receipts_v1.ConstructionSharedResourceReceiptsV1Error,
        match="binding changed",
    ):
        replace(complete.receipts[0], identity=foreign_identity)

    foreign_method = complete.registry.method_by_path["io.output_bytes"]
    foreign_monitor = complete.registry.monitor_by_method_id[
        foreign_method.method_id
    ]
    with pytest.raises(
        receipts_v1.ConstructionSharedResourceReceiptsV1Error,
        match="method or monitor",
    ):
        replace(
            complete.receipts[
                receipts_v1.SHARED_RESOURCE_PATHS.index("io.read_bytes")
            ],
            method_id=foreign_method.method_id,
            monitor_registration_id=foreign_monitor.monitor_registration_id,
        )


def test_receipt_set_rejects_duplicate_source_charge_key() -> None:
    complete = _zero_receipt_set()
    first = complete.receipts[0]
    second = complete.receipts[1]
    assert type(first.source_evidence) is receipts_v1.SharedResourceSourceEvidenceV1
    assert type(second.source_evidence) is receipts_v1.SharedResourceSourceEvidenceV1
    with pytest.raises(
        receipts_v1.ConstructionSharedResourceReceiptsV1Error,
        match="content-bound",
    ):
        replace(
            second.source_evidence,
            charge_key=first.source_evidence.charge_key,
        )


def test_partial_native_transcript_is_not_a_formal_completion_input() -> None:
    # The legacy object is deliberately not duck-typed into the successor.
    unavailable = partial_v1.IncompleteSiteCoverageRefV1()
    assert unavailable.kind == "NOT_AVAILABLE_INCOMPLETE_SITE_COVERAGE"
    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="exact closure artifact",
    ):
        closure_v1.verify_evidence_closure_coverage_v1(  # type: ignore[arg-type]
            unavailable
        )
    with pytest.raises(
        closure_v1.ConstructionAccountingEvidenceClosureV1Error,
        match="exact closure artifact",
    ):
        closure_v1.require_complete_structural_coverage_v1(  # type: ignore[arg-type]
            unavailable
        )
