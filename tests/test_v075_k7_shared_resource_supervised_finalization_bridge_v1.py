from __future__ import annotations

from functools import cache
import hashlib
import inspect

import pytest

from acfqp import campaign_v1 as campaign
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import construction_shared_resource_global_supervisor_journal_v1 as journal_v1
from acfqp import construction_shared_resource_live_meter_v1 as live_v1
from acfqp import construction_shared_resource_outer_finalization_v1 as outer_v1
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp import routing_v1 as routing
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as ipc_v1
from acfqp import v075_k7_root_cap_shared_resource_identity_v1 as identity_v1
from acfqp import v075_k7_shared_resource_supervised_finalization_bridge_v1 as bridge_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes, content_id


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-supervised-finalization-bridge-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


@cache
def _derivation() -> identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1:
    profile = ipc_v1.freeze_v075_k7_root_cap_accounted_sealed_ipc_profile_v1(
        timeout_milliseconds=5_000
    )
    occurrence = campaign.LogicalOccurrenceV1(
        _id("workload"),
        _id("protocol"),
        1,
        _id("structural"),
        _id("query"),
        _id("plan"),
        _id("threshold"),
        _id("build-epoch"),
        _id("rebuild-policy"),
    )
    attempt = campaign.RouteAttemptV1.initial(occurrence)
    context = routing.RouteDecisionContextV1(
        _id("preregistration"),
        occurrence.protocol_id,
        profile.comparison_profile_id,
        profile.counter_registry_id,
        occurrence.structural_id,
        occurrence.query_id,
        occurrence.selected_plan_id,
        occurrence.threshold_profile_id,
        attempt.build_epoch_id,
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
    )
    decision = routing.DecisionPointV1(
        context.route_decision_context_id,
        1,
        _id("frontier"),
        _id("causal"),
        _id("common-prefix-work"),
    )
    transaction = routing.TransactionV1(
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
        decision.decision_point_id,
        decision.transaction_index,
        decision.frontier_snapshot_id,
        _id("route-cap"),
    )
    route = ipc_v1.freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1(
        profile=profile,
        logical_occurrence=occurrence,
        route_attempt=attempt,
        route_context=context,
        decision_point=decision,
        transaction=transaction,
    )
    return identity_v1.derive_v075_k7_root_cap_shared_resource_identity_v1(route)


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
def _measurement_authorities():
    counter_registry = registry_v6.official_counter_registry_v6()
    authority_id = _id("registration-authority")
    methods = tuple(
        receipts_v1.freeze_shared_resource_measurement_method_v1(
            path=path,
            method_kind=_METHOD_KINDS[path],
            primitive=f"bridge_test.{path}.primitive",
        )
        for path in receipts_v1.SHARED_RESOURCE_PATHS
    )
    monitors = tuple(
        sorted(
            (
                receipts_v1.SharedResourceMonitorRegistrationV1(
                    registration_authority_id=authority_id,
                    monitor_key=f"bridge_test.{method.path}.monitor",
                    monitor_code_id=_id(f"monitor-{method.path}"),
                    source_module=(
                        "acfqp.v075_k7_shared_resource_supervised_finalization_bridge_v1"
                    ),
                    source_symbol="finalize_v075_k7_supervised_shared_resources_v1",
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
    purposes = tuple(
        sorted(
            (
                receipts_v1.HashPurposeRegistrationV1(
                    purpose_key="business_model_digest",
                    disposition=(
                        receipts_v1.HashPurposeDispositionV1.BUSINESS_CHARGEABLE
                    ),
                    source_module=(
                        "acfqp.v075_k7_shared_resource_supervised_finalization_bridge_v1"
                    ),
                    source_symbol="finalize_v075_k7_supervised_shared_resources_v1",
                ),
                *(
                    receipts_v1.HashPurposeRegistrationV1(
                        purpose_key=purpose,
                        disposition=(
                            receipts_v1.HashPurposeDispositionV1.ACCOUNTING_PROVENANCE_EXCLUDED
                        ),
                        source_module=(
                            "acfqp.v075_k7_shared_resource_supervised_finalization_bridge_v1"
                        ),
                        source_symbol=(
                            "V075K7SharedResourceSupervisedFinalizationBridgeV1.bridge_id"
                        ),
                    )
                    for purpose in sorted(
                        receipts_v1.REQUIRED_ACCOUNTING_HASH_EXCLUSION_PURPOSES
                    )
                ),
            ),
            key=lambda item: item.purpose_key,
        )
    )
    hash_method = registry.method_by_path["common.hash_invocations"]
    hash_monitor = registry.monitor_by_method_id[hash_method.method_id]
    hash_profile = receipts_v1.RecursionSafeHashMeterProfileV1(
        registry=registry,
        method_id=hash_method.method_id,
        monitor_registration_id=hash_monitor.monitor_registration_id,
        purposes=purposes,
        suppression_context_key="bridge_test.accounting_hash_suppression",
    )
    obligations = tuple(
        sorted(
            (
                receipts_v1.NamedObligationV1(
                    obligation_key="integrity_bundle_digest_matches",
                    kind=receipts_v1.NamedObligationKindV1.INTEGRITY,
                    source_module=(
                        "acfqp.v075_k7_shared_resource_supervised_finalization_bridge_v1"
                    ),
                    source_symbol="finalize_v075_k7_supervised_shared_resources_v1",
                    stage_kind="PREOPEN_COMMON_PREFIX",
                    counter_path="common.integrity_checks",
                ),
                receipts_v1.NamedObligationV1(
                    obligation_key="protocol_freeze_precedes_execution",
                    kind=receipts_v1.NamedObligationKindV1.PROTOCOL,
                    source_module=(
                        "acfqp.v075_k7_shared_resource_supervised_finalization_bridge_v1"
                    ),
                    source_symbol="finalize_v075_k7_supervised_shared_resources_v1",
                    stage_kind="PREOPEN_COMMON_PREFIX",
                    counter_path="common.protocol_checks",
                ),
            ),
            key=lambda item: item.obligation_key,
        )
    )
    obligation_registry = receipts_v1.NamedObligationRegistryV1(
        registry=registry,
        integrity_method_id=(
            registry.method_by_path["common.integrity_checks"].method_id
        ),
        protocol_method_id=(
            registry.method_by_path["common.protocol_checks"].method_id
        ),
        registration_authority_id=authority_id,
        obligations=obligations,
    )
    return registry, hash_profile, obligation_registry


def _journal(
    *,
    label: str,
    scope: journal_v1.GlobalSupervisorScopeV1,
    final_peak: int,
) -> journal_v1.FrozenGlobalSupervisorEventJournalV1:
    sources = (
        journal_v1.WindowStartSourceDocumentV1(
            scope, f"monitor.registration.{label}"
        ),
        journal_v1.BusinessCutoffSourceDocumentV1(
            scope,
            journal_v1.BusinessCutoffClaimV1.BUSINESS_PAYLOAD_COMPLETE,
            f"business.frame.{label}",
            True,
        ),
        journal_v1.ProcessReapSourceDocumentV1(
            scope, f"process.handle.{label}", 0, True
        ),
        journal_v1.DescendantScanSourceDocumentV1(
            scope, f"process.handle.{label}", 0, True
        ),
        journal_v1.FinalCgroupPeakSourceDocumentV1(
            scope, f"cgroup.scope.{label}", final_peak, True
        ),
        journal_v1.ParentTerminalSourceDocumentV1(
            scope,
            journal_v1.ParentTerminalClaimV1.COMPLETED,
            "STRUCTURAL_TERMINAL",
            True,
        ),
    )
    session = journal_v1.open_global_supervisor_event_journal_v1(sources[0])
    for source in sources[1:]:
        session.append(source)
    return session.freeze()


def _snapshot(
    *,
    label: str,
    derivation: identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1,
    journal: journal_v1.FrozenGlobalSupervisorEventJournalV1,
    live_peak: int = 300,
) -> live_v1.SharedResourceMeasurementSnapshotV1:
    registry, hash_profile, obligations = _measurement_authorities()
    start = journal.events[0]
    cutoff = journal.events[1]
    role = bridge_v1.SupervisedOuterSourceRoleV1
    meter = live_v1.open_trusted_shared_resource_live_meter_v1(
        measurement_registry=registry,
        hash_profile=hash_profile,
        obligation_registry=obligations,
        identity=derivation.identity_binding,
        window_key=journal.scope.window_key,
        start_marker_id=bridge_v1.derive_supervised_outer_source_role_id_v1(
            event=start, role=role.WINDOW_START_MARKER
        ),
        start_sequence=20,
    )
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
        source_kind=(
            live_v1.LiveSourceEvidenceKindV1.SUPERVISOR_MOUNT_MANIFEST
        ),
        source_evidence_id=bridge_v1.derive_supervised_outer_source_role_id_v1(
            event=start, role=role.MOUNT_MANIFEST
        ),
    )
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
        observed_bytes=live_peak,
        source_kind=live_v1.LiveSourceEvidenceKindV1.CGROUP_MEMORY_PEAK,
        source_evidence_id=_id(f"{label}-live-cgroup"),
    )
    meter.record_successful_process_launch(
        source_evidence_id=bridge_v1.derive_supervised_outer_source_role_id_v1(
            event=start, role=role.PROCESS_SUPERVISOR_LAUNCH
        )
    )
    meter.close_operational_window(
        cutoff_marker_id=bridge_v1.derive_supervised_outer_source_role_id_v1(
            event=cutoff, role=role.BUSINESS_CUTOFF_MARKER
        )
    )
    meter.mark_unavailable(
        path="io.output_bytes",
        status=receipts_v1.MeasurementStatusV1.NOT_AVAILABLE,
        reason_code=outer_v1.OUTPUT_UNAVAILABLE_REASON,
    )
    return meter.freeze_snapshot()


def _renderer(candidate: int) -> dict[str, bytes]:
    rendered: dict[str, bytes] = {}
    for index, role in enumerate(fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES):
        document = {"artifact_role": role, "payload": f"role-{index}"}
        if role == fixed_v1.OUTPUT_MANIFEST_ROLE:
            document["io.output_bytes"] = candidate
            document["ordered_artifact_roles"] = list(
                fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            )
        rendered[role] = canonical_json_bytes(document)
    return rendered


@cache
def _fixed_point() -> fixed_v1.OutputBytesFixedPointResultV1:
    route_id = _derivation().route_identity.route_identity_id
    profile = fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=_id("renderer"),
        execution_identity_id=route_id,
        role_byte_caps={
            role: 64 * 1024
            for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        },
        max_total_bytes=256 * 1024,
        max_iterations=16,
    )
    return fixed_v1.solve_output_bytes_fixed_point_v1(
        profile=profile, renderer=_renderer
    )


def _complete_inputs(*, label: str = "base", final_peak: int = 350, live_peak: int = 300):
    derivation = _derivation()
    binding = derivation.identity_binding
    scope = journal_v1.GlobalSupervisorScopeV1(
        binding.identity_binding_id,
        binding.execution_profile_id,
        f"bridge_test.{label}.window",
        f"bridge_test.{label}.supervisor",
    )
    journal = _journal(label=label, scope=scope, final_peak=final_peak)
    snapshot = _snapshot(
        label=label,
        derivation=derivation,
        journal=journal,
        live_peak=live_peak,
    )
    return derivation, snapshot, journal, _fixed_point()


def test_bridge_derives_every_outer_input_and_rebases_after_live_cutoff() -> None:
    derivation, snapshot, journal, fixed_point = _complete_inputs()
    result = bridge_v1.finalize_v075_k7_supervised_shared_resources_v1(
        identity_derivation=derivation,
        snapshot=snapshot,
        journal=journal,
        fixed_point=fixed_point,
    )

    cutoff = snapshot.window.cutoff_sequence
    assert cutoff > journal.events[1].sequence
    assert tuple(item.rebased_global_sequence for item in result.rebased_events) == (
        cutoff + 1,
        cutoff + 2,
        cutoff + 3,
        cutoff + 4,
    )
    assert result.outer_finalization.sources.measurement_identity_binding_id == (
        derivation.identity_binding.identity_binding_id
    )
    assert result.outer_finalization.sources.execution_profile_id == (
        derivation.identity_binding.execution_profile_id
    )
    assert result.outer_finalization.raw_source_values[
        "memory.working_bytes_peak"
    ] == 350
    assert result.outer_finalization.raw_source_values["io.output_bytes"] == (
        fixed_point.output_bytes
    )

    document = result.to_document()
    assert document["outer_source_ids_derived_internally"] is True
    assert document["caller_supplied_outer_source_ids"] == []
    assert document["caller_supplied_post_cutoff_sequences"] == []
    assert document["caller_supplied_lifecycle_bools"] == []
    assert document["caller_supplied_final_peak"] is False
    assert document["final_peak_derived_from_typed_final_cgroup_source"] is True
    assert document["structural_bridge_only"] is True
    assert document["counter_records_issued"] is False
    assert document["work_vector_issued"] is False
    assert document["comparison_vector_issued"] is False
    assert document["actual_projection_proof_issued"] is False
    assert document["certificate_issued"] is False
    assert all(value is False for value in document["formal_locks"].values())

    verification = (
        bridge_v1.verify_v075_k7_supervised_shared_resource_finalization_v1(
            result
        )
    )
    verified = verification.to_document()
    assert verified["verification_result"] == "STRUCTURAL_PASS"
    assert verified["semantic_source_verification_performed"] is False
    assert all(value is False for value in verified["formal_locks"].values())


def test_public_bridge_accepts_no_outer_ids_sequences_bools_or_peak() -> None:
    parameters = inspect.signature(
        bridge_v1.finalize_v075_k7_supervised_shared_resources_v1
    ).parameters
    assert tuple(parameters) == (
        "identity_derivation",
        "snapshot",
        "journal",
        "fixed_point",
    )
    forbidden_fragments = ("source_id", "sequence", "reaped", "descendant", "peak")
    assert not any(
        fragment in name for name in parameters for fragment in forbidden_fragments
    )


def test_bridge_calls_legacy_envelope_and_finalizer_only_after_join(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    derivation, snapshot, journal, fixed_point = _complete_inputs(label="spy")
    original_envelope = outer_v1.issue_post_cutoff_supervisor_envelope_v1
    original_finalizer = outer_v1.finalize_parent_owned_shared_resources_v1
    calls: list[str] = []

    def envelope_spy(**kwargs):
        calls.append("envelope")
        return original_envelope(**kwargs)

    def finalizer_spy(**kwargs):
        calls.append("finalizer")
        return original_finalizer(**kwargs)

    monkeypatch.setattr(
        bridge_v1.outer_v1,
        "issue_post_cutoff_supervisor_envelope_v1",
        envelope_spy,
    )
    monkeypatch.setattr(
        bridge_v1.outer_v1,
        "finalize_parent_owned_shared_resources_v1",
        finalizer_spy,
    )
    bridge_v1.finalize_v075_k7_supervised_shared_resources_v1(
        identity_derivation=derivation,
        snapshot=snapshot,
        journal=journal,
        fixed_point=fixed_point,
    )
    assert calls == ["envelope", "finalizer"]


def test_crossed_scope_and_window_fail_before_outer_finalizer() -> None:
    derivation, snapshot, _journal_ok, fixed_point = _complete_inputs(label="join")
    binding = derivation.identity_binding
    foreign_identity_scope = journal_v1.GlobalSupervisorScopeV1(
        _id("foreign-binding"),
        binding.execution_profile_id,
        snapshot.window.window_key,
        "bridge_test.foreign.identity.supervisor",
    )
    foreign_identity_journal = _journal(
        label="foreign_identity", scope=foreign_identity_scope, final_peak=350
    )
    with pytest.raises(
        bridge_v1.V075K7SharedResourceSupervisedFinalizationBridgeV1Error,
        match="scope crossed",
    ):
        bridge_v1.finalize_v075_k7_supervised_shared_resources_v1(
            identity_derivation=derivation,
            snapshot=snapshot,
            journal=foreign_identity_journal,
            fixed_point=fixed_point,
        )

    foreign_window_scope = journal_v1.GlobalSupervisorScopeV1(
        binding.identity_binding_id,
        binding.execution_profile_id,
        "bridge_test.foreign.window",
        "bridge_test.foreign.window.supervisor",
    )
    foreign_window_journal = _journal(
        label="foreign_window", scope=foreign_window_scope, final_peak=350
    )
    with pytest.raises(
        bridge_v1.V075K7SharedResourceSupervisedFinalizationBridgeV1Error,
        match="binding/window crossed",
    ):
        bridge_v1.finalize_v075_k7_supervised_shared_resources_v1(
            identity_derivation=derivation,
            snapshot=snapshot,
            journal=foreign_window_journal,
            fixed_point=fixed_point,
        )


def test_typed_final_cgroup_peak_must_cover_live_prefix() -> None:
    derivation, snapshot, journal, fixed_point = _complete_inputs(
        label="low_peak", final_peak=299, live_peak=300
    )
    with pytest.raises(
        bridge_v1.V075K7SharedResourceSupervisedFinalizationBridgeV1Error,
        match="below the live prefix",
    ):
        bridge_v1.finalize_v075_k7_supervised_shared_resources_v1(
            identity_derivation=derivation,
            snapshot=snapshot,
            journal=journal,
            fixed_point=fixed_point,
        )


def test_mutated_frozen_journal_fails_without_refreshing_cached_ids() -> None:
    derivation, snapshot, journal, fixed_point = _complete_inputs(
        label="journal_mutation"
    )
    terminal = journal.events[-1].source_document
    assert type(terminal) is journal_v1.ParentTerminalSourceDocumentV1
    original = terminal.terminal_code
    frozen_id = journal._journal_id  # noqa: SLF001 - hostile mutation test
    object.__setattr__(terminal, "terminal_code", "MUTATED_TERMINAL")
    try:
        with pytest.raises(
            bridge_v1.V075K7SharedResourceSupervisedFinalizationBridgeV1Error,
            match="upstream structural replay",
        ):
            bridge_v1.finalize_v075_k7_supervised_shared_resources_v1(
                identity_derivation=derivation,
                snapshot=snapshot,
                journal=journal,
                fixed_point=fixed_point,
            )
        assert journal._journal_id == frozen_id  # noqa: SLF001
    finally:
        object.__setattr__(terminal, "terminal_code", original)
    assert journal.journal_id == frozen_id


def test_domains_are_registered_and_role_separated() -> None:
    assert len(bridge_v1.LOCAL_DOMAIN_TAGS) == 4
    assert bridge_v1.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
    assert len(bridge_v1.REQUESTED_PHASE3E_DOMAIN_CONSTANTS) == 4
    assert len(
        {content_id(domain, {"same": "payload"}) for domain in bridge_v1.LOCAL_DOMAIN_TAGS}
    ) == 4


def test_bridge_and_rebased_event_cannot_be_caller_minted() -> None:
    derivation, snapshot, journal, fixed_point = _complete_inputs(label="mint")
    result = bridge_v1.finalize_v075_k7_supervised_shared_resources_v1(
        identity_derivation=derivation,
        snapshot=snapshot,
        journal=journal,
        fixed_point=fixed_point,
    )
    with pytest.raises(
        bridge_v1.V075K7SharedResourceSupervisedFinalizationBridgeV1Error,
        match="issuer-owned",
    ):
        bridge_v1.V075K7SharedResourceSupervisedFinalizationBridgeV1(
            object(),
            derivation,
            snapshot,
            journal,
            fixed_point,
            result.rebased_events,
            result.outer_finalization,
        )
    first = result.rebased_events[0]
    with pytest.raises(
        bridge_v1.V075K7SharedResourceSupervisedFinalizationBridgeV1Error,
        match="bridge-issued",
    ):
        bridge_v1.RebasedPostCutoffJournalEventV1(
            object(),
            first.journal_id,
            first.live_snapshot_id,
            first.event_id,
            first.source_document_id,
            first.event_kind,
            first.journal_cutoff_sequence,
            first.journal_local_sequence,
            first.live_cutoff_sequence,
            first.rebased_global_sequence,
        )
