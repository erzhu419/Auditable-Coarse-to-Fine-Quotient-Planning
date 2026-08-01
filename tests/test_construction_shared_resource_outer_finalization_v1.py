from __future__ import annotations

from functools import cache
import hashlib

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import construction_shared_resource_live_meter_v1 as live_v1
from acfqp import construction_shared_resource_outer_finalization_v1 as outer_v1
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:construction-shared-resource-outer-finalization-test:v1\x00"
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
    "io.read_bytes": receipts_v1.MeasurementMethodKindV1.EXACT_BYTE_TRANSFER_MONITOR,
    "io.staged_bytes": (
        receipts_v1.MeasurementMethodKindV1.EXACT_BYTE_TRANSFER_MONITOR
    ),
    "memory.working_bytes_peak": (
        receipts_v1.MeasurementMethodKindV1.WORKING_SET_PEAK_MONITOR
    ),
    "process.launches": receipts_v1.MeasurementMethodKindV1.PROCESS_SUPERVISOR,
}


@cache
def _authorities():
    counter_registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(counter_registry)
    authority_id = _id("registration-authority")
    methods = tuple(
        receipts_v1.freeze_shared_resource_measurement_method_v1(
            path=path,
            method_kind=_METHOD_KINDS[path],
            primitive=f"outer_test.{path}.primitive",
        )
        for path in receipts_v1.SHARED_RESOURCE_PATHS
    )
    monitors = tuple(
        sorted(
            (
                receipts_v1.SharedResourceMonitorRegistrationV1(
                    registration_authority_id=authority_id,
                    monitor_key=f"outer_test.{method.path}.monitor",
                    monitor_code_id=_id(f"{method.path}-monitor"),
                    source_module=(
                        "acfqp.construction_shared_resource_outer_finalization_v1"
                    ),
                    source_symbol="finalize_parent_owned_shared_resources_v1",
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
                    disposition=receipts_v1.HashPurposeDispositionV1.BUSINESS_CHARGEABLE,
                    source_module=(
                        "acfqp.construction_shared_resource_outer_finalization_v1"
                    ),
                    source_symbol="finalize_parent_owned_shared_resources_v1",
                ),
                *(
                    receipts_v1.HashPurposeRegistrationV1(
                        purpose_key=purpose,
                        disposition=(
                            receipts_v1.HashPurposeDispositionV1.ACCOUNTING_PROVENANCE_EXCLUDED
                        ),
                        source_module=(
                            "acfqp.construction_shared_resource_outer_finalization_v1"
                        ),
                        source_symbol="ParentOwnedSharedResourceFinalizationV1.finalization_id",
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
        suppression_context_key="outer_test.accounting_hash_suppression",
    )
    obligations = tuple(
        sorted(
            (
                receipts_v1.NamedObligationV1(
                    obligation_key="integrity_bundle_digest_matches",
                    kind=receipts_v1.NamedObligationKindV1.INTEGRITY,
                    source_module=(
                        "acfqp.construction_shared_resource_outer_finalization_v1"
                    ),
                    source_symbol="finalize_parent_owned_shared_resources_v1",
                    stage_kind="PREOPEN_COMMON_PREFIX",
                    counter_path="common.integrity_checks",
                ),
                receipts_v1.NamedObligationV1(
                    obligation_key="protocol_freeze_precedes_execution",
                    kind=receipts_v1.NamedObligationKindV1.PROTOCOL,
                    source_module=(
                        "acfqp.construction_shared_resource_outer_finalization_v1"
                    ),
                    source_symbol="finalize_parent_owned_shared_resources_v1",
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
            measurement_registry.method_by_path["common.integrity_checks"].method_id
        ),
        protocol_method_id=(
            measurement_registry.method_by_path["common.protocol_checks"].method_id
        ),
        registration_authority_id=authority_id,
        obligations=obligations,
    )
    return measurement_registry, hash_profile, obligation_registry, (
        counter_registry.registry_id
    ), stage.stage_profile_id


def _snapshot(
    label: str,
    *,
    output_prefix: int = 0,
    process_launch_count: int = 1,
    output_status: receipts_v1.MeasurementStatusV1 = (
        receipts_v1.MeasurementStatusV1.NOT_AVAILABLE
    ),
    output_reason: str = outer_v1.OUTPUT_UNAVAILABLE_REASON,
    unavailable_extra_path: str | None = None,
):
    registry, hash_profile, obligations, registry_id, stage_id = _authorities()
    identity = receipts_v1.SharedResourceIdentityBindingV1(
        counter_registry_id=registry_id,
        stage_profile_id=stage_id,
        boundary_profile_id=_id(f"{label}-boundary"),
        execution_profile_id=_id(f"{label}-execution-profile"),
        occurrence_id=_id(f"{label}-occurrence"),
        route_attempt_id=_id(f"{label}-attempt"),
        decision_point_id=_id(f"{label}-decision"),
    )
    meter = live_v1.open_trusted_shared_resource_live_meter_v1(
        measurement_registry=registry,
        hash_profile=hash_profile,
        obligation_registry=obligations,
        identity=identity,
        window_key=f"outer_test.{label}.window",
        start_marker_id=_id(f"{label}-start"),
    )
    sources = {
        "business": _id(f"{label}-business"),
        "process": _id(f"{label}-process"),
        "cgroup": _id(f"{label}-cgroup"),
        "final_cgroup": _id(f"{label}-final-cgroup"),
        "mount": _id(f"{label}-mount"),
        "cutoff": _id(f"{label}-cutoff"),
        "terminal": _id(f"{label}-terminal"),
        "reap": _id(f"{label}-reap"),
        "descendant_scan": _id(f"{label}-descendant-scan"),
    }
    meter.record_hash_invocation(
        purpose_key="business_model_digest",
        source_evidence_id=_id(f"{label}-hash"),
    )
    meter.record_named_obligation(
        obligation_key="integrity_bundle_digest_matches",
        outcome=live_v1.ObligationOutcomeV1.PASS,
        source_evidence_id=_id(f"{label}-integrity"),
    )
    meter.record_named_obligation(
        obligation_key="protocol_freeze_precedes_execution",
        outcome=live_v1.ObligationOutcomeV1.PASS,
        source_evidence_id=_id(f"{label}-protocol"),
    )
    meter.record_peak_observation(
        path="io.mounted_bytes_peak",
        observed_bytes=200,
        source_kind=live_v1.LiveSourceEvidenceKindV1.SUPERVISOR_MOUNT_MANIFEST,
        source_evidence_id=sources["mount"],
    )
    if output_prefix:
        meter.record_byte_transfer(
            path="io.output_bytes",
            byte_count=output_prefix,
            source_evidence_id=_id(f"{label}-output-prefix"),
        )
    if unavailable_extra_path != "io.read_bytes":
        meter.record_byte_transfer(
            path="io.read_bytes",
            byte_count=13,
            source_evidence_id=_id(f"{label}-read"),
        )
    meter.record_byte_transfer(
        path="io.staged_bytes",
        byte_count=17,
        source_evidence_id=_id(f"{label}-staged"),
    )
    meter.record_peak_observation(
        path="memory.working_bytes_peak",
        observed_bytes=300,
        source_kind=live_v1.LiveSourceEvidenceKindV1.CGROUP_MEMORY_PEAK,
        source_evidence_id=sources["cgroup"],
    )
    for launch_index in range(process_launch_count):
        meter.record_successful_process_launch(
            source_evidence_id=(
                sources["process"]
                if launch_index == 0
                else _id(f"{label}-process-{launch_index}")
            )
        )
    meter.close_operational_window(cutoff_marker_id=sources["cutoff"])
    meter.mark_unavailable(
        path="io.output_bytes",
        status=output_status,
        reason_code=output_reason,
    )
    if unavailable_extra_path is not None:
        meter.mark_unavailable(
            path=unavailable_extra_path,
            status=receipts_v1.MeasurementStatusV1.UNKNOWN,
            reason_code="SOURCE_NOT_INSTRUMENTED",
        )
    snapshot = meter.freeze_snapshot()
    return snapshot, identity, sources


def _renderer(candidate: int) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for index, role in enumerate(fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES):
        document = {"artifact_role": role, "payload": f"role-{index}"}
        if role == fixed_v1.OUTPUT_MANIFEST_ROLE:
            document["io.output_bytes"] = candidate
            document["ordered_artifact_roles"] = list(
                fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            )
        result[role] = canonical_json_bytes(document)
    return result


def _fixed_point(route_identity_id: str):
    profile = fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=_id("renderer"),
        execution_identity_id=route_identity_id,
        role_byte_caps={
            role: 64 * 1024
            for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        },
        max_total_bytes=256 * 1024,
        max_iterations=16,
    )
    return fixed_v1.solve_output_bytes_fixed_point_v1(
        profile=profile,
        renderer=_renderer,
    )


def _post_cutoff_envelope(
    label: str,
    snapshot,
    identity,
    sources,
    route_identity_id: str,
    **overrides,
):
    cutoff = snapshot.window.cutoff_sequence
    values = {
        "snapshot": snapshot,
        "identity_binding": identity,
        "route_identity_id": route_identity_id,
        "parent_global_terminal_source_id": sources["terminal"],
        "child_reap_source_id": sources["reap"],
        "descendant_scan_source_id": sources["descendant_scan"],
        "final_cgroup_peak_source_id": sources["final_cgroup"],
        "child_reap_sequence": cutoff + 1,
        "descendant_scan_sequence": cutoff + 2,
        "final_cgroup_peak_sequence": cutoff + 3,
        "parent_global_terminal_sequence": cutoff + 4,
        "final_working_bytes_peak": 350,
        "child_reaped": True,
        "no_descendants": True,
    }
    values.update(overrides)
    return outer_v1.issue_post_cutoff_supervisor_envelope_v1(**values)


def _finalize(label: str, snapshot, identity, sources, fixed_point, **overrides):
    default_route_identity_id = (
        fixed_point.profile.execution_identity_id
        if type(fixed_point) is fixed_v1.OutputBytesFixedPointResultV1
        else _id(f"{label}-fallback-route-identity")
    )
    envelope = overrides.pop("post_cutoff_envelope", None)
    if envelope is None:
        envelope = _post_cutoff_envelope(
            label,
            snapshot,
            identity,
            sources,
            default_route_identity_id,
        )
    values = {
        "snapshot": snapshot,
        "identity_binding": identity,
        "fixed_point": fixed_point,
        "route_identity_id": default_route_identity_id,
        "business_source_id": sources["business"],
        "cutoff_source_id": sources["cutoff"],
        "process_supervisor_source_id": sources["process"],
        "mount_manifest_source_id": sources["mount"],
        "post_cutoff_envelope": envelope,
    }
    values.update(overrides)
    return outer_v1.finalize_parent_owned_shared_resources_v1(**values)


def test_parent_finalization_yields_nine_unverified_rows_without_double_output() -> None:
    snapshot, identity, sources = _snapshot("success")
    route_identity_id = _id("success-route-identity")
    fixed_point = _fixed_point(route_identity_id)

    result = _finalize("success", snapshot, identity, sources, fixed_point)

    assert tuple(row.path for row in result.rows) == receipts_v1.SHARED_RESOURCE_PATHS
    assert len(result.rows) == 9
    assert all(
        row.status is receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED
        for row in result.rows
    )
    prefix = snapshot.observed_prefix_values.get("io.output_bytes", 0)
    output = next(row for row in result.rows if row.path == "io.output_bytes")
    assert prefix == 0
    assert output.value == fixed_point.output_bytes
    assert output.output_prefix_bytes == prefix
    assert output.prefix_added_to_final_value is False
    assert output.complete_fixed_point_total_selected_once_structurally is True
    assert result.raw_source_values["io.output_bytes"] == fixed_point.output_bytes
    working = next(
        row for row in result.rows if row.path == "memory.working_bytes_peak"
    )
    assert working.value == 350
    assert working.source_kind is (
        outer_v1.OuterRawSourceKindV1.POST_CUTOFF_SUPERVISOR_ENVELOPE
    )
    assert working.source_row_id == sources["final_cgroup"]
    assert sources["cgroup"] not in working.source_evidence_ids
    assert outer_v1.replay_parent_owned_shared_resource_finalization_v1(result) is result

    document = result.to_document()
    assert document["output_commit_before_fixed_point"] is False
    assert document["output_prefix_added_to_complete_total"] is False
    assert (
        document[
            "complete_output_fixed_point_total_selected_once_structurally"
        ]
        is True
    )
    assert document["artifact_bytes_committed"] is False
    assert document["fixed_point_covers_outer_wrapper_bytes"] is False
    assert document["operational_output_semantics_verified"] is False
    assert document["operational_artifact_write_authorized"] is False
    assert document["parent_global_terminal_order_bound_structurally"] is True
    assert document["child_reaped"] is True
    assert document["no_descendants"] is True
    assert document["post_cutoff_supervisor_envelope_bound"] is True
    assert document["post_cutoff_lifecycle_semantics_verified"] is False
    assert document["post_reap_working_peak_comes_from_live_snapshot"] is False
    assert document["pre_cutoff_peak_accepted_as_final_peak"] is False
    assert document["final_working_bytes_peak"] == 350
    assert document["source_evidence_semantics_verified"] is False
    assert document["formal_counter_records_issued"] is False
    assert document["formal_work_vector_authorized"] is False
    assert document["formal_comparison_vector_authorized"] is False
    assert document["numeric_projection_authorized"] is False
    assert document["official_execution_allowed"] is False
    envelope_document = result.sources.post_cutoff_envelope.to_document()
    assert envelope_document["issued_after_live_cutoff_claimed_structurally"] is True
    assert (
        envelope_document[
            "reap_and_descendant_scan_order_claimed_structurally"
        ]
        is True
    )
    assert envelope_document["supervisor_provenance_verified"] is False
    assert envelope_document["global_sequence_semantics_verified"] is False
    assert envelope_document["pre_cutoff_peak_accepted_as_final_peak"] is False
    assert envelope_document["source_evidence_semantics_verified"] is False
    assert envelope_document["numeric_projection_authorized"] is False
    assert envelope_document["official_execution_allowed"] is False


def test_exact_output_unavailability_and_all_other_numeric_rows_are_required() -> None:
    route_identity_id = _id("unavailable-route")
    fixed_point = _fixed_point(route_identity_id)

    unknown, unknown_identity, unknown_sources = _snapshot(
        "unknown-output",
        output_status=receipts_v1.MeasurementStatusV1.UNKNOWN,
    )
    with pytest.raises(
        outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
        match="exact post-cutoff typed unavailability",
    ):
        _finalize(
            "unknown", unknown, unknown_identity, unknown_sources, fixed_point
        )

    wrong_reason, wrong_reason_identity, wrong_reason_sources = _snapshot(
        "wrong-reason",
        output_reason="OTHER_SUFFIX_REASON",
    )
    with pytest.raises(
        outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
        match="exact post-cutoff typed unavailability",
    ):
        _finalize(
            "reason",
            wrong_reason,
            wrong_reason_identity,
            wrong_reason_sources,
            fixed_point,
        )

    missing_read, missing_read_identity, missing_read_sources = _snapshot(
        "missing-read",
        unavailable_extra_path="io.read_bytes",
    )
    with pytest.raises(
        outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
        match="eight pre-output",
    ):
        _finalize(
            "missing",
            missing_read,
            missing_read_identity,
            missing_read_sources,
            fixed_point,
        )


def test_route_execution_cutoff_and_parent_source_roles_cannot_cross() -> None:
    snapshot, identity, sources = _snapshot("identity")
    route_identity_id = _id("identity-route")
    fixed_point = _fixed_point(route_identity_id)

    cases = (
        ({"route_identity_id": _id("wrong-route")}, "source-set identity"),
        ({"identity_binding": object()}, "measurement identity binding"),
        ({"cutoff_source_id": _id("wrong-cutoff")}, "source-set identity"),
        (
            {"process_supervisor_source_id": _id("wrong-process")},
            "process.launches",
        ),
        ({"mount_manifest_source_id": _id("wrong-mount")}, "mounted_bytes_peak"),
    )
    for overrides, message in cases:
        with pytest.raises(
            outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
            match=message,
        ):
            _finalize(
                "identity", snapshot, identity, sources, fixed_point, **overrides
            )

    with pytest.raises(
        outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
        match="reused a pre-cutoff live source",
    ):
        _post_cutoff_envelope(
            "precutoff-cgroup",
            snapshot,
            identity,
            sources,
            route_identity_id,
            final_cgroup_peak_source_id=sources["cgroup"],
        )

    # A business/child role cannot be relabelled as a parent peak source.
    with pytest.raises(
        outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
        match="roles must be distinct",
    ):
        _finalize(
            "self-report",
            snapshot,
            identity,
            sources,
            fixed_point,
            mount_manifest_source_id=sources["business"],
        )


def test_terminal_lifecycle_exact_types_and_precommit_output_are_fail_closed() -> None:
    snapshot, identity, sources = _snapshot("lifecycle")
    route_identity_id = _id("lifecycle-route")
    fixed_point = _fixed_point(route_identity_id)

    for overrides, message in (
        (
            {"parent_global_terminal_sequence": snapshot.window.cutoff_sequence},
            "strictly ordered",
        ),
        ({"parent_global_terminal_sequence": True}, "positive exact integer"),
        ({"child_reaped": 1}, "child_reaped must be exact true"),
        ({"child_reaped": False}, "child_reaped must be exact true"),
        ({"no_descendants": False}, "no_descendants must be exact true"),
    ):
        with pytest.raises(
            outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
            match=message,
        ):
            _post_cutoff_envelope(
                "lifecycle",
                snapshot,
                identity,
                sources,
                route_identity_id,
                **overrides,
            )

    with pytest.raises(
        outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
        match="cannot be below",
    ):
        _post_cutoff_envelope(
            "lower-peak",
            snapshot,
            identity,
            sources,
            route_identity_id,
            final_working_bytes_peak=299,
        )

    committed_prefix, committed_identity, committed_sources = _snapshot(
        "committed-prefix", output_prefix=1
    )
    with pytest.raises(
        outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
        match="committed before",
    ):
        _finalize(
            "committed",
            committed_prefix,
            committed_identity,
            committed_sources,
            fixed_point,
        )

    with pytest.raises(
        outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
        match="issued output-byte fixed point",
    ):
        _finalize(
            "not-fixed",
            snapshot,
            identity,
            sources,
            fixed_point.profile,
            route_identity_id=route_identity_id,
            post_cutoff_envelope=_post_cutoff_envelope(
                "not-fixed",
                snapshot,
                identity,
                sources,
                route_identity_id,
            ),
        )

    extra_launch, extra_identity, extra_sources = _snapshot(
        "extra-launch", process_launch_count=2
    )
    with pytest.raises(
        outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
        match="exactly one child launch",
    ):
        _finalize(
            "extra-launch",
            extra_launch,
            extra_identity,
            extra_sources,
            fixed_point,
        )


def test_outer_domains_are_central_and_result_rows_are_not_caller_mintable() -> None:
    assert outer_v1.REQUESTED_PHASE3E_DOMAIN_TAGS == tuple(
        sorted(outer_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)
    )
    assert len(outer_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) == 3
    assert set(outer_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS

    with pytest.raises(
        outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
        match="finalizer-issued only",
    ):
        outer_v1.PostCutoffSupervisorEnvelopeV1(
            object(),
            _id("route"),
            _id("identity"),
            _id("execution"),
            _id("snapshot"),
            _id("cutoff"),
            _id("terminal"),
            _id("reap"),
            _id("scan"),
            _id("cgroup-final"),
            10,
            11,
            12,
            13,
            14,
            1,
            True,
            True,
        )

    with pytest.raises(
        outer_v1.ConstructionSharedResourceOuterFinalizationV1Error,
        match="finalizer-issued only",
    ):
        outer_v1.OuterFinalizedRawSourceRowV1(
            object(),
            _id("source-set"),
            _id("snapshot"),
            _id("fixed"),
            "io.read_bytes",
            "sum",
            receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED,
            1,
            outer_v1.OuterRawSourceKindV1.LIVE_MEASUREMENT_ROW,
            _id("source-row"),
            (_id("evidence"),),
            None,
            None,
            False,
            False,
        )
