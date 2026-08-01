from __future__ import annotations

from dataclasses import replace
from functools import cache
import hashlib

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_live_meter_v1 as live_v1
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp.accounting_v1 import ReducerEnum
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:construction-shared-resource-live-meter-test:v1\x00"
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
    "process.launches": receipts_v1.MeasurementMethodKindV1.PROCESS_SUPERVISOR,
}


@cache
def _base_authorities():
    counter_registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(counter_registry)
    authority_id = _id("shared-registration-authority")
    methods = tuple(
        receipts_v1.freeze_shared_resource_measurement_method_v1(
            path=path,
            method_kind=_METHOD_KINDS[path],
            primitive=f"live_test.{path}.primitive",
        )
        for path in live_v1.SHARED_RESOURCE_PATHS
    )
    monitors = tuple(
        sorted(
            (
                receipts_v1.SharedResourceMonitorRegistrationV1(
                    registration_authority_id=authority_id,
                    monitor_key=f"live_test.{method.path}.monitor",
                    monitor_code_id=_id(f"shared-{method.path}-monitor-code"),
                    source_module=(
                        "acfqp.construction_shared_resource_live_meter_v1"
                    ),
                    source_symbol="TrustedSharedResourceLiveMeterV1",
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
    measurement_registry = receipts_v1.SharedResourceMeasurementRegistryV1(
        counter_registry_id=counter_registry.registry_id,
        registration_authority_id=authority_id,
        methods=methods,
        monitors=monitors,
    )

    purposes = tuple(
        sorted(
            (
                receipts_v1.HashPurposeRegistrationV1(
                    purpose_key="business_model_digest",
                    disposition=(
                        receipts_v1.HashPurposeDispositionV1.BUSINESS_CHARGEABLE
                    ),
                    source_module=(
                        "acfqp.construction_shared_resource_live_meter_v1"
                    ),
                    source_symbol="TrustedSharedResourceLiveMeterV1.record_hash_invocation",
                ),
                *(
                    receipts_v1.HashPurposeRegistrationV1(
                        purpose_key=purpose,
                        disposition=(
                            receipts_v1.HashPurposeDispositionV1.ACCOUNTING_PROVENANCE_EXCLUDED
                        ),
                        source_module=(
                            "acfqp.construction_shared_resource_live_meter_v1"
                        ),
                        source_symbol="SharedResourceMeasurementSnapshotV1.snapshot_id",
                    )
                    for purpose in sorted(
                        receipts_v1.REQUIRED_ACCOUNTING_HASH_EXCLUSION_PURPOSES
                    )
                ),
            ),
            key=lambda item: item.purpose_key,
        )
    )
    hash_method = measurement_registry.method_by_path["common.hash_invocations"]
    hash_monitor = measurement_registry.monitor_by_method_id[hash_method.method_id]
    hash_profile = receipts_v1.RecursionSafeHashMeterProfileV1(
        registry=measurement_registry,
        method_id=hash_method.method_id,
        monitor_registration_id=hash_monitor.monitor_registration_id,
        purposes=purposes,
        suppression_context_key="live_test.accounting_hash_suppression",
    )

    obligations = tuple(
        sorted(
            (
                receipts_v1.NamedObligationV1(
                    obligation_key="integrity_bundle_digest_matches",
                    kind=receipts_v1.NamedObligationKindV1.INTEGRITY,
                    source_module=(
                        "acfqp.construction_shared_resource_live_meter_v1"
                    ),
                    source_symbol="TrustedSharedResourceLiveMeterV1.record_named_obligation",
                    stage_kind="PREOPEN_COMMON_PREFIX",
                    counter_path="common.integrity_checks",
                ),
                receipts_v1.NamedObligationV1(
                    obligation_key="protocol_freeze_precedes_execution",
                    kind=receipts_v1.NamedObligationKindV1.PROTOCOL,
                    source_module=(
                        "acfqp.construction_shared_resource_live_meter_v1"
                    ),
                    source_symbol="TrustedSharedResourceLiveMeterV1.record_named_obligation",
                    stage_kind="PREOPEN_COMMON_PREFIX",
                    counter_path="common.protocol_checks",
                ),
            ),
            key=lambda item: item.obligation_key,
        )
    )
    obligation_registry = receipts_v1.NamedObligationRegistryV1(
        registry=measurement_registry,
        integrity_method_id=(
            measurement_registry.method_by_path[
                "common.integrity_checks"
            ].method_id
        ),
        protocol_method_id=(
            measurement_registry.method_by_path[
                "common.protocol_checks"
            ].method_id
        ),
        registration_authority_id=authority_id,
        obligations=obligations,
    )
    return (
        measurement_registry,
        hash_profile,
        obligation_registry,
        counter_registry.registry_id,
        stage_profile.stage_profile_id,
    )


def _authorities(label: str = "authority"):
    (
        measurement_registry,
        hash_profile,
        obligation_registry,
        counter_registry_id,
        stage_profile_id,
    ) = _base_authorities()
    identity = receipts_v1.SharedResourceIdentityBindingV1(
        counter_registry_id=counter_registry_id,
        stage_profile_id=stage_profile_id,
        boundary_profile_id=_id(f"{label}-boundary"),
        execution_profile_id=_id(f"{label}-execution"),
        occurrence_id=_id(f"{label}-occurrence"),
        route_attempt_id=_id(f"{label}-attempt"),
        decision_point_id=_id(f"{label}-decision"),
    )
    return measurement_registry, hash_profile, obligation_registry, identity


def _meter(label: str = "meter") -> live_v1.TrustedSharedResourceLiveMeterV1:
    registry, hash_profile, obligations, identity = _authorities(label)
    return live_v1.open_trusted_shared_resource_live_meter_v1(
        measurement_registry=registry,
        hash_profile=hash_profile,
        obligation_registry=obligations,
        identity=identity,
        window_key=f"live_test.{label}.window",
        start_marker_id=_id(f"{label}-start"),
    )


def _close_and_mark_unavailable(
    meter: live_v1.TrustedSharedResourceLiveMeterV1,
    label: str,
) -> live_v1.SharedResourceMeasurementSnapshotV1:
    meter.close_operational_window(cutoff_marker_id=_id(f"{label}-cutoff"))
    for path in meter.unresolved_paths:
        meter.mark_unavailable(
            path=path,
            status=receipts_v1.MeasurementStatusV1.UNKNOWN,
            reason_code="SOURCE_NOT_INSTRUMENTED",
        )
    return meter.freeze_snapshot()


def test_live_meter_reduces_all_nine_paths_without_formal_claims() -> None:
    meter = _meter("all-nine")

    meter.record_hash_invocation(
        purpose_key="business_model_digest",
        source_evidence_id=_id("hash-business-1"),
    )
    meter.record_hash_invocation(
        purpose_key="business_model_digest",
        source_evidence_id=_id("hash-business-2"),
    )
    meter.record_hash_invocation(
        purpose_key="accounting_event_content_id",
        source_evidence_id=_id("hash-accounting-excluded"),
    )
    meter.record_named_obligation(
        obligation_key="integrity_bundle_digest_matches",
        outcome=live_v1.ObligationOutcomeV1.PASS,
        source_evidence_id=_id("integrity-pass"),
    )
    meter.record_named_obligation(
        obligation_key="integrity_bundle_digest_matches",
        outcome=live_v1.ObligationOutcomeV1.FAIL,
        source_evidence_id=_id("integrity-fail"),
    )
    meter.record_named_obligation(
        obligation_key="protocol_freeze_precedes_execution",
        outcome=live_v1.ObligationOutcomeV1.PASS,
        source_evidence_id=_id("protocol-pass"),
    )
    meter.record_byte_transfer(
        path="io.read_bytes",
        byte_count=3,
        source_evidence_id=_id("read-3"),
    )
    meter.record_byte_transfer(
        path="io.read_bytes",
        byte_count=5,
        source_evidence_id=_id("read-5"),
    )
    meter.record_byte_transfer(
        path="io.staged_bytes",
        byte_count=7,
        source_evidence_id=_id("staged-7"),
    )
    meter.record_byte_transfer(
        path="io.output_bytes",
        byte_count=11,
        source_evidence_id=_id("output-11"),
    )
    meter.record_successful_process_launch(source_evidence_id=_id("launch-1"))
    meter.record_successful_process_launch(source_evidence_id=_id("launch-2"))
    for value in (10, 20, 15):
        meter.record_peak_observation(
            path="io.mounted_bytes_peak",
            observed_bytes=value,
            source_kind=(
                live_v1.LiveSourceEvidenceKindV1.SUPERVISOR_MOUNT_MANIFEST
            ),
            source_evidence_id=_id(f"mounted-{value}"),
        )
    for index, value in enumerate((100, 90)):
        meter.record_peak_observation(
            path="memory.working_bytes_peak",
            observed_bytes=value,
            source_kind=live_v1.LiveSourceEvidenceKindV1.CGROUP_MEMORY_PEAK,
            source_evidence_id=_id(f"working-{index}-{value}"),
        )

    meter.close_operational_window(cutoff_marker_id=_id("all-nine-cutoff"))
    # The snapshot/result/counter/manifest suffix is written after this
    # collector's cutoff.  Prefix output events are preserved, but V1 must not
    # call them a complete output-byte total.
    assert meter.unresolved_paths == ("io.output_bytes",)
    meter.mark_unavailable(
        path="io.output_bytes",
        status=receipts_v1.MeasurementStatusV1.UNKNOWN,
        reason_code="POST_CUTOFF_ACCOUNTING_SUFFIX_UNMEASURED",
    )
    snapshot = meter.freeze_snapshot()

    assert meter.state is live_v1.LiveMeterStateV1.FROZEN
    assert tuple(row.path for row in snapshot.rows) == live_v1.SHARED_RESOURCE_PATHS
    assert not snapshot.all_paths_structurally_recorded
    assert snapshot.observed_prefix_values == {
        "common.hash_invocations": 2,
        "common.integrity_checks": 2,
        "common.protocol_checks": 1,
        "io.mounted_bytes_peak": 20,
        "io.output_bytes": 11,
        "io.read_bytes": 8,
        "io.staged_bytes": 7,
        "memory.working_bytes_peak": 100,
        "process.launches": 2,
    }
    with pytest.raises(live_v1.ConstructionSharedResourceLiveMeterV1Error):
        _ = snapshot.unverified_reported_values
    document = snapshot.to_document()
    assert document["sum_and_max_reducers_replayed_separately"] is True
    assert document["absence_inferred_as_zero"] is False
    assert document["source_evidence_semantics_verified"] is False
    assert document["numeric_projection_allowed"] is False
    assert document["formal_counter_records_issued"] is False
    assert document["formal_work_vector_authorized"] is False
    assert document["formal_comparison_vector_authorized"] is False
    assert document["output_prefix_observations_preserved"] is True
    assert document["output_suffix_coverage_complete"] is False
    assert document["accounting_suffix_io_and_obligations_blanket_excluded"] is False
    assert len(snapshot.events) == 17
    excluded = [event for event in snapshot.events if not event.charged]
    assert len(excluded) == 1
    assert excluded[0].purpose_key == "accounting_event_content_id"
    assert live_v1.replay_live_measurement_snapshot_structure_v1(snapshot) == snapshot


def test_sum_and_max_apis_are_not_interchangeable() -> None:
    meter = _meter("reducers")

    with pytest.raises(live_v1.ConstructionSharedResourceLiveMeterV1Error):
        meter.record_byte_transfer(
            path="io.mounted_bytes_peak",
            byte_count=1,
            source_evidence_id=_id("bad-sum-peak"),
        )
    with pytest.raises(live_v1.ConstructionSharedResourceLiveMeterV1Error):
        meter.record_peak_observation(
            path="io.read_bytes",
            observed_bytes=1,
            source_kind=live_v1.LiveSourceEvidenceKindV1.CGROUP_MEMORY_PEAK,
            source_evidence_id=_id("bad-peak-sum"),
        )
    with pytest.raises(live_v1.ConstructionSharedResourceLiveMeterV1Error):
        meter.record_byte_transfer(
            path="io.read_bytes",
            byte_count=0,
            source_evidence_id=_id("implicit-zero"),
        )


def test_missing_is_not_zero_and_typed_unavailable_stays_nonnumeric() -> None:
    meter = _meter("missing")
    meter.record_byte_transfer(
        path="io.read_bytes",
        byte_count=4,
        source_evidence_id=_id("missing-read"),
    )
    meter.close_operational_window(cutoff_marker_id=_id("missing-cutoff"))

    with pytest.raises(
        live_v1.ConstructionSharedResourceLiveMeterV1Error,
        match="cannot freeze unresolved",
    ):
        meter.freeze_snapshot()

    for path in meter.unresolved_paths:
        meter.mark_unavailable(
            path=path,
            status=receipts_v1.MeasurementStatusV1.NOT_AVAILABLE,
            reason_code="TRUSTED_SOURCE_UNAVAILABLE",
        )
    snapshot = meter.freeze_snapshot()
    read_row = next(row for row in snapshot.rows if row.path == "io.read_bytes")
    missing_row = next(
        row for row in snapshot.rows if row.path == "io.output_bytes"
    )
    assert read_row.value == 4
    assert missing_row.value is None
    assert missing_row.status is receipts_v1.MeasurementStatusV1.NOT_AVAILABLE
    assert not snapshot.all_paths_structurally_recorded
    with pytest.raises(live_v1.ConstructionSharedResourceLiveMeterV1Error):
        _ = snapshot.unverified_reported_values


def test_zero_requires_post_cutoff_complete_window_attestation() -> None:
    meter = _meter("zeros")
    meter.close_operational_window(cutoff_marker_id=_id("zeros-cutoff"))
    for path in meter.unresolved_paths:
        if path == "io.output_bytes":
            with pytest.raises(
                live_v1.ConstructionSharedResourceLiveMeterV1Error,
                match="self-referential output suffix",
            ):
                meter.attest_complete_window_zero(
                    path=path,
                    source_evidence_id=_id(f"forbidden-zero-{path}"),
                )
            meter.mark_unavailable(
                path=path,
                status=receipts_v1.MeasurementStatusV1.UNKNOWN,
                reason_code="POST_CUTOFF_ACCOUNTING_SUFFIX_UNMEASURED",
            )
        else:
            meter.attest_complete_window_zero(
                path=path,
                source_evidence_id=_id(f"zero-{path}"),
            )
    snapshot = meter.freeze_snapshot()

    assert not snapshot.all_paths_structurally_recorded
    assert snapshot.observed_prefix_values == {}
    assert all(row.observed_event_count == 0 for row in snapshot.rows)
    assert all(
        row.zero_claim_id is not None
        for row in snapshot.rows
        if row.path != "io.output_bytes"
    )
    output_row = next(
        row for row in snapshot.rows if row.path == "io.output_bytes"
    )
    assert output_row.value is None


def test_hash_purpose_and_named_obligation_registries_are_enforced() -> None:
    meter = _meter("registrations")
    with pytest.raises(live_v1.ConstructionSharedResourceLiveMeterV1Error):
        meter.record_hash_invocation(
            purpose_key="unregistered_hash_role",
            source_evidence_id=_id("unknown-hash"),
        )
    with pytest.raises(live_v1.ConstructionSharedResourceLiveMeterV1Error):
        meter.record_named_obligation(
            obligation_key="unregistered_predicate",
            outcome=live_v1.ObligationOutcomeV1.PASS,
            source_evidence_id=_id("unknown-obligation"),
        )

    meter.record_named_obligation(
        obligation_key="protocol_freeze_precedes_execution",
        outcome=live_v1.ObligationOutcomeV1.FAIL,
        source_evidence_id=_id("registered-fail"),
    )
    snapshot = _close_and_mark_unavailable(meter, "registrations")
    protocol = next(
        row for row in snapshot.rows if row.path == "common.protocol_checks"
    )
    assert protocol.value == 1


def test_duplicate_evidence_post_cutoff_events_and_proc_self_report_fail() -> None:
    meter = _meter("fail-closed")
    evidence_id = _id("duplicate-source")
    meter.record_successful_process_launch(source_evidence_id=evidence_id)
    with pytest.raises(live_v1.ConstructionSharedResourceLiveMeterV1Error):
        meter.record_successful_process_launch(source_evidence_id=evidence_id)
    with pytest.raises(
        live_v1.ConstructionSharedResourceLiveMeterV1Error,
        match="unknown peak source kind",
    ):
        meter.record_peak_observation(
            path="memory.working_bytes_peak",
            observed_bytes=12,
            source_kind="PROC_STATUS_SELF_REPORT",  # type: ignore[arg-type]
            source_evidence_id=_id("proc-self-report"),
        )
    with pytest.raises(
        live_v1.ConstructionSharedResourceLiveMeterV1Error,
        match="unknown peak source kind",
    ):
        meter.record_peak_observation(
            path="memory.working_bytes_peak",
            observed_bytes=12,
            source_kind="ENFORCED_FROZEN_WORKING_CAP",  # type: ignore[arg-type]
            source_evidence_id=_id("frozen-cap-is-not-exact"),
        )

    meter.close_operational_window(cutoff_marker_id=_id("fail-closed-cutoff"))
    with pytest.raises(
        live_v1.ConstructionSharedResourceLiveMeterV1Error,
        match="after the measurement cutoff",
    ):
        meter.record_successful_process_launch(
            source_evidence_id=_id("late-launch")
        )
    for path in meter.unresolved_paths:
        meter.mark_unavailable(
            path=path,
            status=receipts_v1.MeasurementStatusV1.UNKNOWN,
            reason_code="SOURCE_NOT_INSTRUMENTED",
        )
    snapshot = meter.freeze_snapshot()
    with pytest.raises(live_v1.ConstructionSharedResourceLiveMeterV1Error):
        meter.freeze_snapshot()
    assert snapshot.to_document()["proc_self_report_accepted_as_peak_proof"] is False


def test_domains_are_registered_and_snapshot_rows_keep_v6_reducers() -> None:
    assert live_v1.REQUESTED_PHASE3E_DOMAIN_TAGS == tuple(
        sorted(live_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)
    )
    assert len(live_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) == 5
    assert all(
        tag.startswith("acfqp:construction-shared-resource-live-")
        for tag in live_v1.REQUESTED_PHASE3E_DOMAIN_TAGS
    )
    assert set(live_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS

    snapshot = _close_and_mark_unavailable(_meter("domains"), "domains")
    reducers = {row.path: row.reducer for row in snapshot.rows}
    assert all(
        reducers[path] is ReducerEnum.SUM
        for path in live_v1.SUM_SHARED_RESOURCE_PATHS
    )
    assert all(
        reducers[path] is ReducerEnum.MAX
        for path in live_v1.MAX_SHARED_RESOURCE_PATHS
    )
    with pytest.raises(live_v1.ConstructionSharedResourceLiveMeterV1Error):
        replace(
            snapshot.rows[0],
            reducer=(
                ReducerEnum.MAX
                if snapshot.rows[0].reducer is ReducerEnum.SUM
                else ReducerEnum.SUM
            ),
        )
