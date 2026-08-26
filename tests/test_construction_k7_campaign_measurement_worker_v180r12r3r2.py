from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from acfqp import construction_k7_campaign_measurement_worker_v180r12r3r2 as worker
from acfqp import construction_k7_campaign_measurement_ledger_v180r12r3r2 as ledger
from acfqp.phase3e_ids import canonical_json_bytes


def _domain_id(domain: str, payload: dict) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _identified(domain: str, identity_field: str, payload: dict) -> dict:
    return {**payload, identity_field: _domain_id(domain, payload)}


def _synthetic_replay_inputs(mutation: str | None = None):
    protocol_id = "a" * 64
    authorization_id = "b" * 64
    source_rows = []
    for index, source_kind in enumerate(worker.EXPECTED_SOURCE_KINDS):
        source_rows.append(
            _identified(
                worker.V180R12R2_INNER_DOMAINS["source_receipt"],
                "source_receipt_id",
                {"source_kind": source_kind, "synthetic_ordinal": index},
            )
        )
    route_rows = []
    for index, (terminal_code, route_kind) in enumerate(
        worker.EXPECTED_ROUTE_COMPONENTS
    ):
        route_rows.append(
            _identified(
                worker.V180R12R2_INNER_DOMAINS["route_component_chain_receipt"],
                "route_component_chain_receipt_id",
                {
                    "terminal_code": terminal_code,
                    "route_kind": route_kind,
                    "counter_record_count": 269,
                    "counter_record_to_work_vector_to_comparison_vector_replayed": True,
                    "independent_route_component": True,
                    "synthetic_ordinal": index,
                },
            )
        )
    terminal_rows = []
    shared_sets = []
    for terminal_index, terminal_code in enumerate(worker.EXPECTED_TERMINAL_CODES):
        terminal_rows.append(
            _identified(
                worker.V180R12R2_INNER_DOMAINS["terminal_receipt"],
                "terminal_chain_receipt_id",
                {
                    "terminal_code": terminal_code,
                    "synthetic_ordinal": terminal_index,
                },
            )
        )
        receipts = []
        for path_index, path in enumerate(worker._SHARED_RESOURCE_PATHS):
            receipts.append(
                _identified(
                    worker.V180R12R2_INNER_DOMAINS[
                        "terminal_shared_resource_receipt"
                    ],
                    "terminal_shared_resource_receipt_id",
                    {
                        "terminal_code": terminal_code,
                        "path": path,
                        "synthetic_ordinal": 9 * terminal_index + path_index,
                    },
                )
            )
        shared_sets.append(
            _identified(
                worker.V180R12R2_INNER_DOMAINS[
                    "terminal_shared_resource_receipt_set"
                ],
                "terminal_shared_resource_receipt_set_id",
                {
                    "terminal_code": terminal_code,
                    "receipt_count": 9,
                    "all_nine_paths_present": True,
                    "missing_path_inferred_zero": False,
                    "terminal_shared_resource_receipt_ids": [
                        row["terminal_shared_resource_receipt_id"] for row in receipts
                    ],
                    "receipts": receipts,
                    "synthetic_ordinal": terminal_index,
                },
            )
        )
    construction = _identified(
        worker.V180R12R2_INNER_DOMAINS["v180r7r1_construction_axis_receipt"],
        "v180r7r1_construction_axis_receipt_id",
        {
            "one_time_construction_axis": True,
            "construction_axis_replayed_separately": True,
            "charged_to_any_route_component": False,
            "occurrence_route_counter_record_count": 0,
        },
    )
    structural_payload = {
        "structural_declaration_count": 9,
        "actual_counter_record_count": 0,
        "actual_work_vector_present": False,
        "actual_comparison_vector_present": False,
        "actual_projection_proof_present": False,
        "actual_native_zero_attestation_present": False,
        "authoritative_receipt_total": 90,
        "campaign_scope_authoritative_receipt_count": 0,
        "structural_boundary_only": True,
        "scientific_success_claimed": False,
    }
    if mutation == "structural_route_kind":
        structural_payload["route_kind"] = "FORBIDDEN"
    structural = _identified(
        worker.V180R12R2_INNER_DOMAINS["campaign_scope_structural_boundary"],
        "campaign_scope_structural_boundary_id",
        structural_payload,
    )

    terminal = {key: None for key in worker.TERMINAL_KEYSET}
    terminal.update(worker._COMMON_DENOMINATORS)
    terminal.update(
        {
            "schema": worker.TERMINAL_SCHEMA,
            "aggregation_protocol_id": protocol_id,
            "execution_authorization_id": authorization_id,
            "source_verification_receipts": source_rows,
            "route_component_chain_receipts": route_rows,
            "terminal_receipts": terminal_rows,
            "terminal_shared_resource_receipt_sets": shared_sets,
            "v180r7r1_construction_axis_receipt": construction,
            "campaign_scope_structural_boundary": structural,
            "ordered_route_components": [
                {"route_kind": route, "terminal_code": code}
                for code, route in worker.EXPECTED_ROUTE_COMPONENTS
            ],
            "ordered_terminal_codes": list(worker.EXPECTED_TERMINAL_CODES),
            "route_component_counter_closure_status": "PENDING_INDEPENDENT_REPLAY",
            "all_five_source_independent_verifiers_replayed": True,
            "all_ten_occurrence_shared_resource_receipt_sets_present": True,
            "all_twelve_route_component_chains_present": True,
            "producer_bundle_independently_replayed": False,
            "historical_summary_translation_used": False,
            "v180r7r1_construction_work_charged_to_route_components": False,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "SCALAR_CALIBRATION_GATE": "NOT_RUN",
            "BREAK_EVEN_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_BLOCKER": (
                "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
            ),
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
            "fixed_point_iteration": 1,
            "output_bytes_fixed_point": True,
        }
    )
    if mutation == "route_order":
        terminal["ordered_route_components"] = list(
            reversed(terminal["ordered_route_components"])
        )
    if mutation == "historical":
        terminal["historical_summary_translation_used"] = True
    if mutation == "terminal_producer_flag":
        terminal["producer_bundle_independently_replayed"] = True
    terminal_payload = dict(terminal)
    terminal_payload.pop(worker.TERMINAL_ID_FIELD)
    terminal[worker.TERMINAL_ID_FIELD] = _domain_id(
        worker.V180R12R2_TERMINAL_DOMAIN, terminal_payload
    )
    terminal_bytes = canonical_json_bytes(terminal)

    verification = {key: None for key in worker.VERIFICATION_KEYSET}
    verification.update(worker._COMMON_DENOMINATORS)
    verification.update(
        {
            "schema": worker.VERIFICATION_SCHEMA,
            "aggregation_protocol_id": protocol_id,
            "execution_authorization_id": authorization_id,
            "production_aggregation_bundle_id": terminal[worker.TERMINAL_ID_FIELD],
            "aggregation_byte_count": len(terminal_bytes),
            "aggregation_sha256": hashlib.sha256(terminal_bytes).hexdigest(),
            "route_component_counter_closure_status": "PASS",
            "all_five_source_independent_verifiers_replayed": True,
            "all_twelve_route_component_chains_replayed": True,
            "all_ten_terminal_receipts_replayed": True,
            "all_ninety_terminal_shared_resource_receipts_replayed": True,
            "all_route_component_counter_records_replayed": True,
            "all_route_component_work_vectors_replayed": True,
            "all_route_component_comparison_vectors_rederived": True,
            "all_route_component_actual_projection_proofs_replayed": True,
            "all_route_component_native_zero_attestations_replayed": True,
            "terminal_receipt_denominators_replayed": True,
            "campaign_scope_structural_boundary_replayed": True,
            "campaign_scope_has_no_route_kind": True,
            "v180r7r1_construction_axis_replayed_separately": True,
            "producer_aggregate_exact_bytes_reconstructed": True,
            "producer_module_imported": False,
            "v180r12r3_actual_campaign_measurement_ledger_required": True,
            "historical_summary_translation_used": False,
            "v180r7r1_construction_work_charged_to_route_components": False,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "SCALAR_CALIBRATION_GATE": "NOT_RUN",
            "BREAK_EVEN_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_BLOCKER": (
                "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
            ),
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
            "campaign_scope_actual_measurement_ledger_present": False,
        }
    )
    if mutation == "verification_boolean":
        verification["all_route_component_work_vectors_replayed"] = False
    if mutation == "gate":
        verification["official_execution_allowed"] = True
        terminal["official_execution_allowed"] = True
        terminal_payload = dict(terminal)
        terminal_payload.pop(worker.TERMINAL_ID_FIELD)
        terminal[worker.TERMINAL_ID_FIELD] = _domain_id(
            worker.V180R12R2_TERMINAL_DOMAIN, terminal_payload
        )
        terminal_bytes = canonical_json_bytes(terminal)
        verification["production_aggregation_bundle_id"] = terminal[
            worker.TERMINAL_ID_FIELD
        ]
        verification["aggregation_byte_count"] = len(terminal_bytes)
        verification["aggregation_sha256"] = hashlib.sha256(terminal_bytes).hexdigest()
    verification_payload = dict(verification)
    verification_payload.pop(worker.VERIFICATION_ID_FIELD)
    verification[worker.VERIFICATION_ID_FIELD] = _domain_id(
        worker.V180R12R2_VERIFICATION_DOMAIN, verification_payload
    )
    verification_bytes = canonical_json_bytes(verification)

    terminal_fact = worker.StableCampaignInputFactV180R12R3R2(
        worker.CampaignInputRoleV180R12R3R2.TERMINAL,
        "synthetic/terminal.json",
        worker.TERMINAL_SCHEMA,
        worker.TERMINAL_ID_FIELD,
        terminal[worker.TERMINAL_ID_FIELD],
        len(terminal_bytes),
        hashlib.sha256(terminal_bytes).hexdigest(),
    )
    verification_fact = worker.StableCampaignInputFactV180R12R3R2(
        worker.CampaignInputRoleV180R12R3R2.VERIFICATION,
        "synthetic/verification.json",
        worker.VERIFICATION_SCHEMA,
        worker.VERIFICATION_ID_FIELD,
        verification[worker.VERIFICATION_ID_FIELD],
        len(verification_bytes),
        hashlib.sha256(verification_bytes).hexdigest(),
    )
    contract = worker.ProducerFreeReplayContractV180R12R3R2(
        terminal_fact,
        verification_fact,
        protocol_id,
        authorization_id,
        worker.TERMINAL_KEYSET,
        worker.VERIFICATION_KEYSET,
        worker.EXPECTED_SOURCE_KINDS,
        worker.EXPECTED_TERMINAL_CODES,
        worker.EXPECTED_ROUTE_COMPONENTS,
    )
    terminal_snapshot_id, verification_snapshot_id = "1" * 64, "2" * 64
    terminal_stage = worker.MemfdStageReceiptV180R12R3R2(
        terminal_snapshot_id,
        worker.CampaignInputRoleV180R12R3R2.TERMINAL,
        10,
        20,
        30,
        40,
        len(terminal_bytes),
        hashlib.sha256(terminal_bytes).hexdigest(),
        worker.REQUIRED_MEMFD_SEALS,
        True,
        True,
        True,
        0,
        1,
    )
    verification_stage = worker.MemfdStageReceiptV180R12R3R2(
        verification_snapshot_id,
        worker.CampaignInputRoleV180R12R3R2.VERIFICATION,
        11,
        21,
        30,
        41,
        len(verification_bytes),
        hashlib.sha256(verification_bytes).hexdigest(),
        worker.REQUIRED_MEMFD_SEALS,
        True,
        True,
        True,
        0,
        1,
    )
    context = worker.ReplayExecutionContextV180R12R3R2(
        protocol_id="0a" * 32,
        authorization_id="0b" * 32,
        authorization_evidence_id="0f" * 32,
        attempt_id="3" * 64,
        campaign_attempt_record_id="0c" * 32,
        execution_slot_id="4" * 64,
        execution_nonce="5" * 64,
        logical_occurrence_id="6" * 64,
        prelaunch_materialization_terminal_id="a" * 64,
        prelaunch_launch_manifest_sha256="b" * 64,
        prelaunch_launch_rule_id="f" * 64,
        measurement_launch_attempt_id="1a" * 32,
        terminal_snapshot_id=terminal_snapshot_id,
        verification_snapshot_id=verification_snapshot_id,
        open_visibility_receipt_ids=("7" * 64, "8" * 64),
        worker_birth_receipt_id="9" * 64,
        operation_manifest_id="c" * 64,
        native_zero_source_manifest_id="d" * 64,
        native_zero_import_inventory_id="e" * 64,
    )
    return (
        terminal_bytes,
        verification_bytes,
        contract,
        terminal_stage,
        verification_stage,
        context,
    )


def _run_synthetic(mutation: str | None = None):
    terminal, verification, contract, terminal_stage, verification_stage, context = (
        _synthetic_replay_inputs(mutation)
    )
    stage = worker.measure_campaign_inputs_stage_v180r12r3r2(
        terminal,
        verification,
        terminal_stage_receipt=terminal_stage,
        verification_stage_receipt=verification_stage,
        contract=contract,
    )
    result = worker.replay_campaign_subject_worker_v180r12r3r2(
        stage, execution_context=context
    )
    return stage, result, context


def test_split_replay_is_substantive_and_hash_accounting_is_exact(monkeypatch) -> None:
    inputs = _synthetic_replay_inputs()
    original_sha256 = worker.hashlib.sha256
    calls: list[int] = []

    def counting_sha256(raw=b""):
        calls.append(len(raw))
        return original_sha256(raw)

    monkeypatch.setattr(worker.hashlib, "sha256", counting_sha256)
    terminal, verification, contract, terminal_stage, verification_stage, context = inputs
    stage = worker.measure_campaign_inputs_stage_v180r12r3r2(
        terminal,
        verification,
        terminal_stage_receipt=terminal_stage,
        verification_stage_receipt=verification_stage,
        contract=contract,
    )
    assert len(calls) == 2
    calls.clear()
    replay = worker.replay_campaign_subject_worker_v180r12r3r2(
        stage, execution_context=context
    )
    assert len(calls) == 134
    assert len(replay.hash_results) == 134
    assert len(replay.integrity_results) == 137
    assert len(replay.protocol_results) == 15
    calls.clear()
    commit = worker.measure_subject_commit_v180r12r3r2(
        replay,
        subject_readback=lambda raw: worker.SubjectReadbackObservationV180R12R3R2(
            raw, 0o400, 1
        ),
    )
    assert len(calls) == 1
    joined = worker.join_campaign_replay_measurements_v180r12r3r2(
        stage, replay, commit
    )
    assert len(joined.hash_results) == 137
    assert len(joined.integrity_results) == 145
    assert len(joined.protocol_results) == 15
    subject = worker.loads_canonical_json(joined.subject_bytes)
    assert subject["subject_byte_count"] == len(joined.subject_bytes)
    assert subject["attempt_id"] == context.attempt_id
    assert subject["protocol_id"] == context.protocol_id != contract.aggregation_protocol_id
    assert (
        subject["authorization_id"]
        == context.authorization_id
        != contract.execution_authorization_id
    )


def test_actual_split_phase_trace_consumes_exact_expanded_625_positions() -> None:
    terminal, verification, contract, terminal_stage, verification_stage, context = (
        _synthetic_replay_inputs()
    )
    expected = ledger.build_campaign_success_event_schedule_v180r12r3r2(
        context.attempt_id
    )
    operations = {
        (row.slot, row.family, row.ordinal): row.operation_id
        for row in ledger.build_campaign_operation_schedule_v180r12r3r2(
            context.attempt_id
        )
    }
    actual: list[tuple[str, str, str, str]] = []

    def observer(state, label, result):
        kind = (
            worker.SemanticOperationKindV180R12R3R2.SEMANTIC_HASH
            if label.startswith("hash.")
            else worker.SemanticOperationKindV180R12R3R2.INTEGRITY_CHECK
            if label.startswith("integrity.")
            else worker.SemanticOperationKindV180R12R3R2.PROTOCOL_CHECK
        )
        family, family_ordinal, _global, phase, actor = worker._operation_coordinates(
            kind, label
        )
        actual.append(
            (
                f"{kind.value}_{state}",
                actor,
                phase,
                operations[(kind.value, family, family_ordinal)],
            )
        )

    def signature(row):
        return (row.event_kind, row.actor_role, row.phase, row.operation_id)

    stage_start = next(
        index
        for index, row in enumerate(expected)
        if row.phase == "STAGE" and row.event_kind == "SEMANTIC_HASH_INTENT"
    )
    worker_start = next(
        index
        for index, row in enumerate(expected)
        if row.phase == "WORKER" and row.event_kind == "SEMANTIC_HASH_INTENT"
    )
    commit_start = next(
        index
        for index, row in enumerate(expected)
        if row.phase == "COMMIT" and row.event_kind == "SEMANTIC_HASH_INTENT"
    )
    actual.extend(signature(row) for row in expected[:stage_start])
    stage = worker.measure_campaign_inputs_stage_v180r12r3r2(
        terminal,
        verification,
        terminal_stage_receipt=terminal_stage,
        verification_stage_receipt=verification_stage,
        contract=contract,
        operation_observer=observer,
    )
    stage_end = stage_start + 2 * (2 + 6)
    actual.extend(signature(row) for row in expected[stage_end:worker_start])
    replay = worker.replay_campaign_subject_worker_v180r12r3r2(
        stage,
        execution_context=context,
        operation_observer=observer,
    )
    worker_end = worker_start + 2 * (134 + 137 + 15)
    actual.extend(signature(row) for row in expected[worker_end:commit_start])
    worker.measure_subject_commit_v180r12r3r2(
        replay,
        subject_readback=lambda raw: worker.SubjectReadbackObservationV180R12R3R2(
            raw, 0o400, 1
        ),
        operation_observer=observer,
    )
    commit_end = commit_start + 2 * (1 + 2)
    actual.extend(signature(row) for row in expected[commit_end:])
    assert len(actual) == 625
    assert tuple(actual) == tuple(signature(row) for row in expected)


def test_operation_hooks_ack_intent_before_compute_and_outcome_after(
    monkeypatch,
) -> None:
    trace: list[tuple] = []
    original_sha256 = worker.hashlib.sha256

    class Hooks:
        def before_operation(self, kind, label, phase, actor):
            trace.append(("before", kind.value, label, phase, actor))

        def after_operation(self, result):
            trace.append(("after", result.kind.value, result.label))

    def counted_sha256(raw):
        trace.append(("compute", bytes(raw)))
        return original_sha256(raw)

    monkeypatch.setattr(worker.hashlib, "sha256", counted_sha256)
    recorder = worker._ReplayOperationRecorderV180R12R3R2(Hooks())
    recorder.hash_bytes(worker.SEMANTIC_HASH_OPERATION_LABELS[0], b"payload")
    assert trace == [
        (
            "before",
            "SEMANTIC_HASH",
            worker.SEMANTIC_HASH_OPERATION_LABELS[0],
            "STAGE",
            "SUPERVISOR",
        ),
        ("compute", b"payload"),
        ("after", "SEMANTIC_HASH", worker.SEMANTIC_HASH_OPERATION_LABELS[0]),
    ]

    class AmbiguousHooks(Hooks):
        def __call__(self, *args):
            raise AssertionError(args)

    with pytest.raises(
        worker.ConstructionK7CampaignMeasurementWorkerV180R12R3R2Error,
        match="observer hooks are malformed",
    ):
        worker._ReplayOperationRecorderV180R12R3R2(AmbiguousHooks())


def test_rejected_intent_hook_prevents_operation_computation(monkeypatch) -> None:
    calls = 0

    class RejectingHooks:
        def before_operation(self, kind, label, phase, actor):
            del kind, label, phase, actor
            raise RuntimeError("durable intent ACK rejected")

        def after_operation(self, result):  # pragma: no cover - must not run
            raise AssertionError(result)

    def forbidden_sha256(raw):  # pragma: no cover - must not run
        nonlocal calls
        calls += 1
        raise AssertionError(raw)

    monkeypatch.setattr(worker.hashlib, "sha256", forbidden_sha256)
    recorder = worker._ReplayOperationRecorderV180R12R3R2(RejectingHooks())
    with pytest.raises(RuntimeError, match="intent ACK rejected"):
        recorder.hash_bytes(worker.SEMANTIC_HASH_OPERATION_LABELS[0], b"payload")
    assert calls == 0
    assert recorder.hash_results == []


@pytest.mark.parametrize(
    "mutation",
    [
        "verification_boolean",
        "route_order",
        "structural_route_kind",
        "historical",
        "terminal_producer_flag",
        "gate",
    ],
)
def test_replay_mutations_fail_closed_without_caller_supplied_pass(mutation) -> None:
    with pytest.raises(
        worker.ConstructionK7CampaignMeasurementWorkerV180R12R3R2Error,
        match="replay check failed at protocol",
    ):
        _run_synthetic(mutation)


def test_semantic_receipts_bind_exact_operation_manifest_and_subject() -> None:
    stage, replay, context = _run_synthetic()
    commit = worker.measure_subject_commit_v180r12r3r2(
        replay,
        subject_readback=lambda raw: worker.SubjectReadbackObservationV180R12R3R2(
            raw, 0o400, 1
        ),
    )
    computation = worker.join_campaign_replay_measurements_v180r12r3r2(
        stage, replay, commit
    )
    subject_by_label = {
        result.label: context.campaign_attempt_record_id
        for result in (
            computation.hash_results
            + computation.integrity_results
            + computation.protocol_results
        )
    }
    receipts = worker.materialize_semantic_operation_receipts_v180r12r3r2(
        computation,
        execution_context=context,
        evidence_subject_id_by_label=subject_by_label,
    )
    assert len(receipts) == 297
    assert len({row.operation_id for row in receipts}) == 297
    replay_receipt = worker.ProducerFreeReplaySubjectReceiptV180R12R3R2(
        replay.subject_id,
        context.campaign_attempt_record_id,
        context.operation_manifest_id,
        context.native_zero_source_manifest_id,
        context.native_zero_import_inventory_id,
        context.terminal_snapshot_id,
        context.verification_snapshot_id,
        context.open_visibility_receipt_ids,
        receipts,
        replay.subject_bytes,
        False,
        False,
        True,
        "PASS",
    )
    assert replay_receipt.to_document()["subject_result_id"] == replay.subject_id
    assert replay_receipt.to_document()["campaign_attempt_record_id"] == (
        context.campaign_attempt_record_id
    )
    assert replay_receipt.replay_subject_receipt_id != replay.subject_id
    terminal_snapshot = worker.StableInputSnapshotReceiptV180R12R3R2(
        stage.contract.terminal_fact, stage.terminal_bytes
    )
    mount_operation_id = worker._identity(
        worker.domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_V180R12R3R2E_DOMAIN,
        {
            "schema": "acfqp.campaign_operation_identity.v180r12r3r2",
            "schema_version": worker.SCHEMA_VERSION,
            "attempt_id": context.attempt_id,
            "slot": "MOUNT",
            "family": "SEALED_MEMFD",
            "ordinal": 0,
        },
    )
    visibility = worker.FDVisibilityReceiptV180R12R3R2(
        context.attempt_id,
        mount_operation_id,
        stage.terminal_stage_receipt.stage_receipt_id,
        "a" * 64,
        "SUPERVISOR",
        worker.CampaignInputRoleV180R12R3R2.TERMINAL,
        worker.VisibilityStateV180R12R3R2.OPEN,
        stage.terminal_stage_receipt.worker_fd,
        stage.terminal_stage_receipt.device,
        stage.terminal_stage_receipt.inode,
        stage.terminal_stage_receipt.device,
        stage.terminal_stage_receipt.inode,
        True,
        True,
        (),
    )
    actual_documents = {
        "STABLE_INPUT_SNAPSHOT": terminal_snapshot.to_document(),
        "MEMFD_STAGE_RECEIPT": stage.terminal_stage_receipt.to_document(),
        "FD_VISIBILITY_RECEIPT": visibility.to_document(),
        "SEMANTIC_OPERATION_RECEIPT": receipts[0].to_document(),
        "REPLAY_SUBJECT_RECEIPT": replay_receipt.to_document(),
        "CAMPAIGN_SUBJECT_RESULT": worker.loads_canonical_json(replay.subject_bytes),
    }
    for evidence_type, schema, identity_field, fields in (
        worker.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS
    ):
        document = actual_documents[evidence_type]
        assert document["schema"] == schema
        assert identity_field in document
        assert set(document) == fields
    foreign_receipt = replace(receipts[0], evidence_subject_id="f" * 64)
    with pytest.raises(
        worker.ConstructionK7CampaignMeasurementWorkerV180R12R3R2Error,
        match="attempt/manifest closure",
    ):
        worker.ProducerFreeReplaySubjectReceiptV180R12R3R2(
            replay.subject_id,
            context.campaign_attempt_record_id,
            context.operation_manifest_id,
            context.native_zero_source_manifest_id,
            context.native_zero_import_inventory_id,
            context.terminal_snapshot_id,
            context.verification_snapshot_id,
            context.open_visibility_receipt_ids,
            (foreign_receipt, *receipts[1:]),
            replay.subject_bytes,
            False,
            False,
            True,
            "PASS",
        )
    row = receipts[0]
    with pytest.raises(worker.ConstructionK7CampaignMeasurementWorkerV180R12R3R2Error):
        worker.SemanticOperationReceiptV180R12R3R2(
            row.attempt_id,
            receipts[1].operation_id,
            row.kind,
            row.label,
            row.family,
            row.family_ordinal,
            row.ordinal,
            row.operation_manifest_id,
            row.native_zero_source_manifest_id,
            row.native_zero_import_inventory_id,
            row.evidence_subject_id,
            row.outcome_code,
            row.measured_value,
            row.auxiliary_values,
        )


def test_first_semantic_outcome_receipt_needs_no_future_subject_id() -> None:
    terminal, verification, contract, terminal_stage, verification_stage, context = (
        _synthetic_replay_inputs()
    )
    stage = worker.measure_campaign_inputs_stage_v180r12r3r2(
        terminal,
        verification,
        terminal_stage_receipt=terminal_stage,
        verification_stage_receipt=verification_stage,
        contract=contract,
    )
    first = worker.semantic_operation_receipt_v180r12r3r2(
        attempt_id=context.attempt_id,
        operation_manifest_id=context.operation_manifest_id,
        native_zero_source_manifest_id=context.native_zero_source_manifest_id,
        native_zero_import_inventory_id=context.native_zero_import_inventory_id,
        evidence_subject_id=context.campaign_attempt_record_id,
        result=stage.hash_results[0],
    )
    assert first.evidence_subject_id == context.campaign_attempt_record_id
    assert first.to_document()["evidence_subject_id"] != "0" * 64


def test_worker_has_no_v180r12r2_producer_or_verifier_import() -> None:
    source = open(worker.__file__, "r", encoding="utf-8").read()
    assert "import construction_k7_ten_terminal" not in source
    assert "from acfqp import construction_k7_ten_terminal" not in source
    assert "from hashlib import sha256" not in source
    with pytest.raises(worker.ConstructionK7CampaignMeasurementWorkerV180R12R3R2Error):
        worker.replay_exact_v180r12r2_evidence_successor_v180r12r3r2(
            b"{}",
            b"{}",
            terminal_stage_receipt=object(),
            verification_stage_receipt=object(),
            subject_readback=lambda raw: raw,
        )


def test_measured_import_closure_rejects_late_and_predecessor_executor_imports() -> None:
    modules = tuple(
        sorted(
            {
                "acfqp.construction_k7_campaign_measurement_worker_v180r12r3r2",
                "hashlib",
                "json",
            }
        )
    )
    closure = worker.MeasuredImportClosureV180R12R3R2(modules, modules, modules)
    assert closure.window_close_module_names == modules
    with pytest.raises(worker.ConstructionK7CampaignMeasurementWorkerV180R12R3R2Error):
        worker.MeasuredImportClosureV180R12R3R2(
            modules,
            modules,
            tuple(sorted((*modules, "decimal"))),
        )
    forbidden = tuple(
        sorted(
            (
                *modules,
                "acfqp.construction_k7_ten_terminal_aggregation_"
                "independent_verifier_v180r12r2",
            )
        )
    )
    with pytest.raises(worker.ConstructionK7CampaignMeasurementWorkerV180R12R3R2Error):
        worker.MeasuredImportClosureV180R12R3R2(forbidden, forbidden, forbidden)
