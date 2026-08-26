from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_campaign_measurement_finalizer_v180r12r3r2 as finalizer
from acfqp import construction_k7_campaign_measurement_ledger_v180r12r3r2 as ledger
from acfqp import construction_k7_campaign_measurement_supervisor_v180r12r3r2 as supervisor
from acfqp import construction_k7_campaign_measurement_worker_v180r12r3r2 as worker
from acfqp import construction_k7_domain_registry_extension_v180r12r3r2 as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r3r2e as subdomains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from tests import test_construction_k7_campaign_measurement_ledger_v180r12r3r2 as ledger_fixture
from tests import test_construction_k7_campaign_measurement_supervisor_v180r12r3r2 as supervisor_fixture


def _subject_document(
    *,
    protocol_id: str,
    authorization_id: str,
    authorization_evidence_id: str,
    attempt_id: str,
    execution_slot_id: str,
    logical_occurrence_id: str,
    execution_nonce: str,
    prelaunch_materialization_terminal_id: str,
    prelaunch_launch_manifest_sha256: str,
    prelaunch_launch_rule_id: str,
    measurement_launch_attempt_id: str,
    campaign_attempt_record_id: str,
    snapshot_ids: list[str],
    stage_ids: list[str],
    open_visibility_ids: list[str],
    worker_birth_receipt_id: str,
    operation_manifest_id: str,
) -> dict:
    payload = {
        "schema": "acfqp.campaign_measurement_subject_result.v180r12r3r2",
        "schema_version": "1.0.0",
        "scope": "FRESH_PRODUCER_FREE_POST_OUTCOME_EVIDENCE_REPLAY_SUCCESSOR",
        "protocol_id": protocol_id,
        "authorization_id": authorization_id,
        "authorization_evidence_id": authorization_evidence_id,
        "attempt_id": attempt_id,
        "execution_slot_id": execution_slot_id,
        "execution_nonce": execution_nonce,
        "logical_occurrence_id": logical_occurrence_id,
        "prelaunch_materialization_terminal_id": (
            prelaunch_materialization_terminal_id
        ),
        "prelaunch_launch_manifest_sha256": prelaunch_launch_manifest_sha256,
        "prelaunch_launch_rule_id": prelaunch_launch_rule_id,
        "measurement_launch_attempt_id": measurement_launch_attempt_id,
        "campaign_attempt_record_id": campaign_attempt_record_id,
        "terminal_content_id": worker.TERMINAL_CONTENT_ID,
        "terminal_byte_count": worker.TERMINAL_BYTE_COUNT,
        "terminal_sha256": worker.TERMINAL_SHA256,
        "verification_content_id": worker.VERIFICATION_CONTENT_ID,
        "verification_byte_count": worker.VERIFICATION_BYTE_COUNT,
        "verification_sha256": worker.VERIFICATION_SHA256,
        "terminal_snapshot_id": snapshot_ids[0],
        "verification_snapshot_id": snapshot_ids[1],
        "memfd_stage_receipt_ids": stage_ids,
        "open_visibility_receipt_ids": open_visibility_ids,
        "worker_birth_receipt_id": worker_birth_receipt_id,
        "operation_manifest_id": operation_manifest_id,
        "inner_content_ids": [
            {
                "label": label,
                "content_id": ledger_fixture._cid(f"runtime-inner:{label}"),
            }
            for label in worker.INNER_CONTENT_ID_OPERATION_SUFFIXES
        ],
        "inner_content_id_count": 129,
        "semantic_hash_operation_count": 137,
        "integrity_check_operation_count": 145,
        "protocol_check_operation_count": 15,
        "route_component_counter_closure_status": "PASS",
        "exact_v180r12r2_verification_replayed": True,
        "producer_module_imported": False,
        "producer_entrypoint_called": False,
        "v180r12r2_verifier_imported": False,
        "v180r12r2_verifier_called": False,
        "retroactive_v180r12r2_cost_claimed": False,
        "counter_completeness_gate": "PENDING_INDEPENDENT_REPLAY",
        "workload_economics_gate": "NOT_RUN",
        "scalar_calibration_gate": "NOT_RUN",
        "break_even_gate": "NOT_RUN",
        "official_execution_gate": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "subject_byte_count": 0,
    }
    for _iteration in range(8):
        projected = len(
            canonical_json_bytes({**payload, "subject_result_id": "0" * 64})
        )
        if projected == payload["subject_byte_count"]:
            break
        payload["subject_byte_count"] = projected
    document = {
        **payload,
        "subject_result_id": subdomains.extension_content_id_v180r12r3r2e(
            subdomains.CONSTRUCTION_K7_CAMPAIGN_SUBJECT_RESULT_V180R12R3R2E_DOMAIN,
            payload,
        ),
    }
    assert document["subject_byte_count"] == len(canonical_json_bytes(document))
    return document


def _runtime_shaped_fixture(
    *,
    authorization_evidence_id: str = ledger_fixture.AUTHORIZATION_EVIDENCE_ID,
    execution_slot_id: str = ledger_fixture.EXECUTION_SLOT_ID,
    logical_occurrence_id: str = ledger_fixture.LOGICAL_OCCURRENCE_ID,
    execution_nonce: str = ledger_fixture.EXECUTION_NONCE,
    prelaunch_materialization_terminal_id: str = (
        ledger_fixture.PRELAUNCH_MATERIALIZATION_TERMINAL_ID
    ),
    prelaunch_launch_manifest_sha256: str = (
        ledger_fixture.PRELAUNCH_LAUNCH_MANIFEST_SHA256
    ),
    prelaunch_launch_rule_id: str = ledger_fixture.PRELAUNCH_LAUNCH_RULE_ID,
    measurement_launch_attempt_id: str = (
        ledger_fixture.MEASUREMENT_LAUNCH_ATTEMPT_ID
    ),
) -> dict:
    protocol_id = ledger_fixture.PROTOCOL_ID
    authorization_id = ledger_fixture.AUTHORIZATION_ID
    attempt_id = domains.derive_campaign_measurement_attempt_id_v180r12r3r2(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        authorization_evidence_id=authorization_evidence_id,
        campaign_measurement_execution_slot_id=execution_slot_id,
        logical_occurrence_id=logical_occurrence_id,
        execution_nonce=execution_nonce,
    )
    schedule = ledger.build_campaign_operation_schedule_v180r12r3r2(attempt_id)
    specs = {(row.slot, row.family, row.ordinal): row for row in schedule}
    docs: dict[str, dict] = {}

    def add(document: dict) -> str:
        domain, identity_field = ledger._EVIDENCE_SCHEMA_DESCRIPTOR[
            document["schema"]
        ]
        identity = document[identity_field]
        payload = dict(document)
        payload.pop(identity_field)
        assert identity == subdomains.extension_content_id_v180r12r3r2e(
            domain, payload
        )
        assert identity not in docs
        docs[identity] = document
        return identity

    manifest = ledger.campaign_operation_manifest_v180r12r3r2(attempt_id)
    manifest_id = add(manifest)
    attempt_spec = specs[("ATTEMPT", "OPEN", 0)]
    attempt = ledger.issue_campaign_attempt_record_v180r12r3r2(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        authorization_evidence_id=authorization_evidence_id,
        campaign_measurement_execution_slot_id=execution_slot_id,
        logical_occurrence_id=logical_occurrence_id,
        execution_nonce=execution_nonce,
        prelaunch_materialization_terminal_id=(
            prelaunch_materialization_terminal_id
        ),
        prelaunch_launch_manifest_sha256=prelaunch_launch_manifest_sha256,
        prelaunch_launch_rule_id=prelaunch_launch_rule_id,
        measurement_launch_attempt_id=measurement_launch_attempt_id,
        attempt_id=attempt_id,
        operation_id=attempt_spec.operation_id,
        operation_manifest_id=manifest_id,
    )
    attempt_record_id = add(attempt)

    repository_root = Path(__file__).resolve().parents[1]
    snapshot_objects = []
    for fact in worker.FROZEN_INPUT_FACTS_V180R12R3R2:
        raw = (repository_root / fact.relative_path).read_bytes()
        snapshot_objects.append(
            worker.StableInputSnapshotReceiptV180R12R3R2(fact, raw)
        )
    snapshot_ids = [add(row.to_document()) for row in snapshot_objects]

    stage_objects = []
    for ordinal, (snapshot, fact) in enumerate(
        zip(snapshot_objects, worker.FROZEN_INPUT_FACTS_V180R12R3R2)
    ):
        stage_objects.append(
            worker.MemfdStageReceiptV180R12R3R2(
                snapshot.snapshot_receipt_id,
                fact.role,
                20 + ordinal,
                30 + ordinal,
                40,
                50 + ordinal,
                fact.byte_count,
                fact.sha256,
                worker.REQUIRED_MEMFD_SEALS,
                True,
                True,
                True,
                0,
                1,
            )
        )
    stage_ids = [add(row.to_document()) for row in stage_objects]

    topology_object = supervisor_fixture._topology()
    topology_id = add(topology_object.to_document())
    birth_objects = {
        "SUPERVISOR": supervisor_fixture._birth(
            topology_object,
            attempt_id,
            supervisor.ProcessRoleV180R12R3R2.SUPERVISOR,
            601,
            61,
        ),
        "WORKER": supervisor_fixture._birth(
            topology_object,
            attempt_id,
            supervisor.ProcessRoleV180R12R3R2.WORKER,
            602,
            62,
        ),
    }
    birth_ids = {role: add(row.to_document()) for role, row in birth_objects.items()}
    reap_objects = {role: supervisor_fixture._reap(row) for role, row in birth_objects.items()}
    reap_ids = {role: add(row.to_document()) for role, row in reap_objects.items()}

    visibility_ids: dict[tuple[str, str], str] = {}
    open_visibility_ids: list[str] = []
    close_visibility_ids: list[str] = []
    for ordinal, stage in enumerate(stage_objects):
        role = (
            worker.CampaignInputRoleV180R12R3R2.TERMINAL
            if ordinal == 0
            else worker.CampaignInputRoleV180R12R3R2.VERIFICATION
        )
        operation = specs[("MOUNT", "SEALED_MEMFD", ordinal)]
        for state in (
            worker.VisibilityStateV180R12R3R2.OPEN,
            worker.VisibilityStateV180R12R3R2.CLOSED,
        ):
            is_open = state is worker.VisibilityStateV180R12R3R2.OPEN
            receipt = worker.FDVisibilityReceiptV180R12R3R2(
                attempt_id,
                operation.operation_id,
                stage.stage_receipt_id,
                birth_ids["SUPERVISOR"],
                "SUPERVISOR",
                role,
                state,
                stage.worker_fd,
                stage.device,
                stage.inode,
                stage.device if is_open else None,
                stage.inode if is_open else None,
                is_open,
                is_open,
                (),
            )
            identity = add(receipt.to_document())
            event_kind = (
                "MOUNT_VISIBILITY_OPEN" if is_open else "MOUNT_VISIBILITY_CLOSE"
            )
            visibility_ids[(event_kind, operation.operation_id)] = identity
            (open_visibility_ids if is_open else close_visibility_ids).append(identity)

    source_manifest = ledger.issue_native_zero_source_manifest_v180r12r3r2(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        attempt_id=attempt_id,
        operation_manifest_id=manifest_id,
        prelaunch_launch_manifest_sha256=prelaunch_launch_manifest_sha256,
        precompiled_source_bundle_sha256=(
            ledger_fixture.PRECOMPILED_SOURCE_BUNDLE_SHA256
        ),
        precompiled_source_rows=ledger_fixture._precompiled_source_rows(),
    )
    source_manifest_id = add(source_manifest)
    import_inventory = ledger.issue_native_zero_import_inventory_v180r12r3r2(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        attempt_id=attempt_id,
        source_manifest=source_manifest,
    )
    import_inventory_id = add(import_inventory)

    subject = _subject_document(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        authorization_evidence_id=authorization_evidence_id,
        attempt_id=attempt_id,
        execution_slot_id=execution_slot_id,
        logical_occurrence_id=logical_occurrence_id,
        execution_nonce=execution_nonce,
        prelaunch_materialization_terminal_id=(
            prelaunch_materialization_terminal_id
        ),
        prelaunch_launch_manifest_sha256=prelaunch_launch_manifest_sha256,
        prelaunch_launch_rule_id=prelaunch_launch_rule_id,
        measurement_launch_attempt_id=measurement_launch_attempt_id,
        campaign_attempt_record_id=attempt_record_id,
        snapshot_ids=snapshot_ids,
        stage_ids=stage_ids,
        open_visibility_ids=open_visibility_ids,
        worker_birth_receipt_id=birth_ids["WORKER"],
        operation_manifest_id=manifest_id,
    )
    subject_id = add(subject)
    subject_bytes = canonical_json_bytes(subject)
    subject_byte_count = len(subject_bytes)

    semantic_objects = []
    for kind, labels in (
        (
            worker.SemanticOperationKindV180R12R3R2.SEMANTIC_HASH,
            worker.SEMANTIC_HASH_OPERATION_LABELS,
        ),
        (
            worker.SemanticOperationKindV180R12R3R2.INTEGRITY_CHECK,
            worker.INTEGRITY_CHECK_OPERATION_LABELS,
        ),
        (
            worker.SemanticOperationKindV180R12R3R2.PROTOCOL_CHECK,
            worker.PROTOCOL_CHECK_OPERATION_LABELS,
        ),
    ):
        for label in labels:
            family, family_ordinal, global_ordinal, _phase, _actor = (
                worker._operation_coordinates(kind, label)
            )
            operation = specs[(kind.value, family, family_ordinal)]
            outcome = (
                "SUCCESS"
                if kind is worker.SemanticOperationKindV180R12R3R2.SEMANTIC_HASH
                else "PASS"
            )
            result = worker.ReplayOperationResultV180R12R3R2(
                kind,
                label,
                family,
                family_ordinal,
                global_ordinal,
                operation.phase,
                operation.actor_role,
                outcome,
                1,
                ledger_fixture._semantic_observed_value(
                    subject, kind.value, global_ordinal
                ),
            )
            semantic_objects.append(
                worker.semantic_operation_receipt_v180r12r3r2(
                    attempt_id=attempt_id,
                    operation_manifest_id=manifest_id,
                    native_zero_source_manifest_id=source_manifest_id,
                    native_zero_import_inventory_id=import_inventory_id,
                    evidence_subject_id=attempt_record_id,
                    result=result,
                )
            )
    semantic_by_operation = {
        row.operation_id: add(row.to_document()) for row in semantic_objects
    }
    replay_object = worker.ProducerFreeReplaySubjectReceiptV180R12R3R2(
        subject_id,
        attempt_record_id,
        manifest_id,
        source_manifest_id,
        import_inventory_id,
        snapshot_ids[0],
        snapshot_ids[1],
        tuple(open_visibility_ids),
        tuple(semantic_objects),
        subject_bytes,
        False,
        False,
        True,
        "PASS",
    )
    replay_subject_id = add(replay_object.to_document())

    io_values: dict[str, int] = {}
    io_evidence: dict[tuple[str, str], str] = {}
    for operation in schedule:
        if operation.slot == "INPUT_READ":
            event_kind = "INPUT_READ_OUTCOME"
            if operation.family == "FROZEN_SOURCE":
                value = (worker.TERMINAL_BYTE_COUNT, worker.VERIFICATION_BYTE_COUNT)[
                    operation.ordinal
                ]
                source, target = manifest_id, snapshot_ids[operation.ordinal]
            elif operation.family == "SEALED_STAGE":
                value = (worker.TERMINAL_BYTE_COUNT, worker.VERIFICATION_BYTE_COUNT)[
                    operation.ordinal
                ]
                source, target = stage_ids[operation.ordinal], birth_ids["WORKER"]
            else:
                value = subject_byte_count
                source, target = subject_id, birth_ids["SUPERVISOR"]
        elif operation.slot == "STAGE_WRITE":
            event_kind = "STAGE_WRITE_OUTCOME"
            value = (worker.TERMINAL_BYTE_COUNT, worker.VERIFICATION_BYTE_COUNT)[
                operation.ordinal
            ]
            source, target = snapshot_ids[operation.ordinal], stage_ids[operation.ordinal]
        elif operation.slot == "SUBJECT_WRITE":
            event_kind = "SUBJECT_WRITE_OUTCOME"
            value = subject_byte_count
            source, target = subject_id, birth_ids["WORKER"]
        else:
            continue
        io_values[operation.operation_id] = value
        document = ledger.issue_campaign_io_transfer_receipt_v180r12r3r2(
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            attempt_id=attempt_id,
            operation_id=operation.operation_id,
            event_kind=event_kind,
            measured_value=value,
            returned_chunk_byte_counts=(value,),
            source_evidence_id=source,
            target_evidence_id=target,
        )
        io_evidence[(event_kind, operation.operation_id)] = add(document)

    readback = specs[("INPUT_READ", "SUBJECT_READBACK", 0)]
    commit_spec = specs[("SUBJECT_COMMIT", "SUBJECT_RESULT", 0)]
    subject_commit = ledger.issue_subject_commit_receipt_v180r12r3r2(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        attempt_id=attempt_id,
        operation_id=commit_spec.operation_id,
        subject_id=subject_id,
        replay_subject_receipt_id=replay_subject_id,
        readback_transfer_receipt_id=io_evidence[
            ("INPUT_READ_OUTCOME", readback.operation_id)
        ],
        subject_byte_count=subject_byte_count,
    )
    subject_commit_id = add(subject_commit)
    window_spec = specs[("WINDOW", "CLOSE", 0)]
    window_closure = ledger.issue_window_closure_receipt_v180r12r3r2(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        attempt_id=attempt_id,
        operation_id=window_spec.operation_id,
        subject_commit_receipt_id=subject_commit_id,
        close_visibility_receipt_ids=close_visibility_ids,
    )
    window_closure_id = add(window_closure)

    cgroup_operation = specs[("CGROUP", "FINAL_OBSERVE", 0)]
    cgroup_object = supervisor.CgroupV2ObservationReceiptV180R12R3R2(
        topology_object,
        reap_objects["SUPERVISOR"],
        reap_objects["WORKER"],
        cgroup_operation.operation_id,
        999,
        2,
        (
            ("high", 0),
            ("low", 0),
            ("max", 0),
            ("oom", 0),
            ("oom_group_kill", 0),
            ("oom_kill", 0),
        ),
        (("max", 0),),
        (("MEASUREMENT_ROOT", 0), ("SUPERVISOR", 0), ("WORKER", 0)),
        (("MEASUREMENT_ROOT", 0), ("SUPERVISOR", 0), ("WORKER", 0)),
        supervisor_fixture._readbacks(topology_object, 999),
        True,
    )
    cgroup_id = add(cgroup_object.to_document())

    evidence_for_event: dict[tuple[str, str], str] = {
        ("ATTEMPT_OPEN", attempt_spec.operation_id): attempt_record_id,
        (
            "PROCESS_BIRTH_OUTCOME",
            specs[("PROCESS", "SUPERVISOR", 0)].operation_id,
        ): birth_ids["SUPERVISOR"],
        (
            "PROCESS_BIRTH_OUTCOME",
            specs[("PROCESS", "WORKER", 0)].operation_id,
        ): birth_ids["WORKER"],
        (
            "PROCESS_REAP",
            specs[("PROCESS", "SUPERVISOR", 0)].operation_id,
        ): reap_ids["SUPERVISOR"],
        (
            "PROCESS_REAP",
            specs[("PROCESS", "WORKER", 0)].operation_id,
        ): reap_ids["WORKER"],
        ("SUBJECT_COMMIT", commit_spec.operation_id): subject_commit_id,
        ("WINDOW_CLOSED", window_spec.operation_id): window_closure_id,
        ("CGROUP_OBSERVED", cgroup_operation.operation_id): cgroup_id,
        **visibility_ids,
        **io_evidence,
    }
    for operation_id, evidence_id in semantic_by_operation.items():
        slot = next(row.slot for row in schedule if row.operation_id == operation_id)
        evidence_for_event[(f"{slot}_OUTCOME", operation_id)] = evidence_id

    state = ledger.open_campaign_ledger_v180r12r3r2(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        attempt_id=attempt_id,
        max_event_count=4096,
        max_event_byte_count=65_536,
        max_ledger_byte_count=64 * 1024 * 1024,
    )
    execution_id: str | None = None
    for monotonic_ns, plan in enumerate(
        ledger.build_campaign_success_event_schedule_v180r12r3r2(attempt_id),
        start=1,
    ):
        measured = None
        if plan.event_kind in {
            "SEMANTIC_HASH_OUTCOME",
            "INTEGRITY_CHECK_OUTCOME",
            "PROTOCOL_CHECK_OUTCOME",
            "PROCESS_BIRTH_OUTCOME",
        }:
            measured = 1
        elif plan.event_kind in {
            "INPUT_READ_OUTCOME",
            "STAGE_WRITE_OUTCOME",
            "SUBJECT_WRITE_OUTCOME",
        }:
            measured = io_values[plan.operation_id]
        elif plan.event_kind == "MOUNT_VISIBILITY_OPEN":
            measured = (
                worker.TERMINAL_BYTE_COUNT
                if plan.operation_id == specs[("MOUNT", "SEALED_MEMFD", 0)].operation_id
                else worker.EXPECTED_TOTAL_INPUT_BYTES
            )
        elif plan.event_kind == "CGROUP_OBSERVED":
            measured = 999
        evidence_id = evidence_for_event.get((plan.event_kind, plan.operation_id))
        state, _event = ledger.append_campaign_event_v180r12r3r2(
            state,
            phase=plan.phase,
            actor_role=plan.actor_role,
            operation_id=plan.operation_id,
            event_kind=plan.event_kind,
            monotonic_ns=monotonic_ns,
            payload={
                "evidence_id": evidence_id,
                "outcome_code": ledger_fixture.OUTCOME[plan.event_kind],
                "measured_value": measured,
                "auxiliary_values": [],
            },
        )
        if plan.event_kind == "WINDOW_CLOSED":
            assert execution_id is None
            execution = ledger.issue_campaign_execution_closure_v180r12r3r2(
                protocol_id=protocol_id,
                authorization_id=authorization_id,
                attempt_id=attempt_id,
                subject_id=subject_id,
                window_closed_event_id=_event.event_id,
                window_closure_receipt_id=window_closure_id,
                operation_manifest_id=manifest_id,
                source_manifest_id=source_manifest_id,
                import_inventory_id=import_inventory_id,
                precompiled_source_bundle_sha256=(
                    ledger_fixture.PRECOMPILED_SOURCE_BUNDLE_SHA256
                ),
            )
            execution_id = add(execution)
    assert topology_id in docs
    assert execution_id is not None and execution_id in docs
    assert len(state.events) == 625
    assert len(docs) == 328
    return {
        "state": state,
        "docs": docs,
        "subject_id": subject_id,
        "subject_byte_count": subject_byte_count,
        "source_manifest_id": source_manifest_id,
        "import_inventory_id": import_inventory_id,
        "execution_id": execution_id,
        "attempt_record": attempt,
    }


def _closed_inputs(**provenance: str) -> dict:
    fixture = _runtime_shaped_fixture(**provenance)
    event_documents = tuple(
        canonical_json_bytes(row.to_document()) for row in fixture["state"].events
    )
    evidence_documents = tuple(
        canonical_json_bytes(document)
        for _identity, document in sorted(fixture["docs"].items())
    )
    os_schemas = set(finalizer.OS_EVIDENCE_SCHEMA_COUNTS)
    os_receipt_documents = tuple(
        canonical_json_bytes(document)
        for _identity, document in sorted(fixture["docs"].items())
        if document["schema"] in os_schemas
    )
    return {
        "fixture": fixture,
        "event_documents": event_documents,
        "evidence_documents": evidence_documents,
        "os_receipt_documents": os_receipt_documents,
    }


def _finalize(inputs: dict | None = None, **expected_overrides: str):
    values = _closed_inputs() if inputs is None else inputs
    fixture = values["fixture"]
    state = fixture["state"]
    attempt_record = fixture["attempt_record"]
    expected = {
        "expected_protocol_id": state.protocol_id,
        "expected_authorization_id": state.authorization_id,
        "expected_authorization_evidence_id": attempt_record[
            "authorization_evidence_id"
        ],
        "expected_attempt_id": state.attempt_id,
        "expected_prelaunch_materialization_terminal_id": attempt_record[
            "prelaunch_materialization_terminal_id"
        ],
        "expected_prelaunch_launch_manifest_sha256": attempt_record[
            "prelaunch_launch_manifest_sha256"
        ],
        "expected_precompiled_source_bundle_sha256": (
            ledger_fixture.PRECOMPILED_SOURCE_BUNDLE_SHA256
        ),
        "expected_prelaunch_launch_rule_id": attempt_record[
            "prelaunch_launch_rule_id"
        ],
        "expected_measurement_launch_attempt_id": attempt_record[
            "measurement_launch_attempt_id"
        ],
    }
    expected.update(expected_overrides)
    return finalizer.finalize_campaign_measurement_terminal_v180r12r3r2(
        event_documents=values["event_documents"],
        evidence_documents=values["evidence_documents"],
        os_receipt_documents=values["os_receipt_documents"],
        **expected,
        expected_subject_id=fixture["subject_id"],
        expected_native_zero_source_manifest_id=fixture["source_manifest_id"],
        expected_native_zero_import_inventory_id=fixture["import_inventory_id"],
        max_event_count=state.max_event_count,
        max_event_byte_count=state.max_event_byte_count,
        max_ledger_byte_count=state.max_ledger_byte_count,
    )


def test_finalizer_materializes_only_the_exact_pending_terminal() -> None:
    inputs = _closed_inputs()
    result = _finalize(inputs)
    document = result.document
    fixture = inputs["fixture"]

    assert document["event_count"] == 625
    assert document["evidence_document_count"] == 328
    assert document["os_receipt_document_count"] == 12
    assert document["os_receipt_schema_counts"] == dict(
        finalizer.OS_EVIDENCE_SCHEMA_COUNTS
    )
    assert document["os_receipt_ids"] == sorted(document["os_receipt_ids"])
    assert document["subject_id"] == fixture["subject_id"]
    for field_name in (
        "authorization_evidence_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
    ):
        assert document[field_name] == fixture["attempt_record"][field_name]
    assert document["precompiled_source_bundle_sha256"] == (
        ledger_fixture.PRECOMPILED_SOURCE_BUNDLE_SHA256
    )
    assert document["campaign_measurement_ledger"][
        "combined_successor_authoritative_receipt_count"
    ] == 99
    assert document["V180R12R3R2_CAMPAIGN_COUNTER_CLOSURE_STATUS"] == (
        "PENDING_INDEPENDENT_REPLAY"
    )
    assert document["COUNTER_COMPLETENESS_GATE"] == "PENDING_INDEPENDENT_REPLAY"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert document["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert document["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    assert document["independent_verification_present"] is False
    assert document["output_bytes_fixed_point"] == len(result.canonical_bytes)

    payload = dict(document)
    terminal_id = payload.pop("campaign_measurement_terminal_id")
    assert terminal_id == domains.extension_content_id_v180r12r3r2(
        domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R3R2_DOMAIN,
        payload,
    )
    closure_bytes = canonical_json_bytes(document["campaign_measurement_ledger"])
    assert document["campaign_ledger_closure_byte_count"] == len(closure_bytes)
    assert document["campaign_ledger_closure_sha256"] == hashlib.sha256(
        closure_bytes
    ).hexdigest()
    artifacts = result.success_artifact_bytes
    assert tuple(artifacts) == finalizer.SUCCESS_ARTIFACT_ORDER
    assert tuple(row[0] for row in finalizer.SUCCESS_ARTIFACT_SCHEMA_ROWS) == (
        finalizer.SUCCESS_ARTIFACT_ORDER
    )
    inventory = loads_canonical_json(artifacts["evidence_inventory"])
    os_bundle = loads_canonical_json(artifacts["os_receipt"])
    for key, schema, identity_field, terminal_prefix in (
        finalizer.SUCCESS_ARTIFACT_SCHEMA_ROWS
    ):
        artifact_document = loads_canonical_json(artifacts[key])
        assert artifact_document["schema"] == schema
        assert document[f"{terminal_prefix}_id"] == artifact_document[
            identity_field
        ]
    assert frozenset(document) == finalizer.TERMINAL_FIELDS
    assert frozenset(inventory) == finalizer.EVIDENCE_INVENTORY_BUNDLE_FIELDS
    assert frozenset(os_bundle) == finalizer.OS_RECEIPT_BUNDLE_FIELDS
    assert inventory["schema"] == finalizer.EVIDENCE_INVENTORY_BUNDLE_SCHEMA
    assert inventory["evidence_document_count"] == 328
    assert inventory["ordered_evidence_document_ids"] == sorted(
        inventory["ordered_evidence_document_ids"]
    )
    assert os_bundle["schema"] == finalizer.OS_RECEIPT_BUNDLE_SCHEMA
    assert os_bundle["campaign_evidence_inventory_bundle_id"] == inventory[
        "campaign_evidence_inventory_bundle_id"
    ]
    assert os_bundle["os_receipt_document_count"] == 12
    assert document["campaign_evidence_inventory_bundle_id"] == inventory[
        "campaign_evidence_inventory_bundle_id"
    ]
    assert document["campaign_os_receipt_bundle_id"] == os_bundle[
        "campaign_os_receipt_bundle_id"
    ]
    for prefix, raw in (
        ("campaign_evidence_inventory_bundle", artifacts["evidence_inventory"]),
        ("campaign_execution_closure", artifacts["execution_closure"]),
        ("campaign_os_receipt_bundle", artifacts["os_receipt"]),
        ("campaign_ledger_closure", artifacts["ledger_closure"]),
    ):
        assert document[f"{prefix}_byte_count"] == len(raw)
        assert document[f"{prefix}_sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize(
    "expected_field",
    (
        "expected_authorization_evidence_id",
        "expected_prelaunch_materialization_terminal_id",
        "expected_prelaunch_launch_manifest_sha256",
        "expected_prelaunch_launch_rule_id",
        "expected_measurement_launch_attempt_id",
    ),
)
def test_finalizer_rejects_foreign_authorization_or_transport_provenance(
    expected_field: str,
) -> None:
    with pytest.raises(
        finalizer.ConstructionK7CampaignMeasurementFinalizerV180R12R3R2Error,
        match="provenance changed",
    ):
        _finalize(_closed_inputs(), **{expected_field: "f" * 64})


@pytest.mark.parametrize(
    ("field", "foreign_value"),
    (
        *(
            (f"{prefix}_{suffix}", "0" * 64)
            for prefix in (
                "campaign_evidence_inventory_bundle",
                "campaign_execution_closure",
                "campaign_os_receipt_bundle",
                "campaign_ledger_closure",
            )
            for suffix in ("id", "sha256")
        ),
        *(
            (f"{prefix}_byte_count", None)
            for prefix in (
                "campaign_evidence_inventory_bundle",
                "campaign_execution_closure",
                "campaign_os_receipt_bundle",
                "campaign_ledger_closure",
            )
        ),
    ),
)
def test_pending_terminal_rejects_resigned_success_artifact_fact(
    field: str, foreign_value: str | None
) -> None:
    result = _finalize(_closed_inputs())
    document = result.document
    document[field] = (
        document[field] + 1 if foreign_value is None else foreign_value
    )
    payload = dict(document)
    payload.pop("campaign_measurement_terminal_id")
    document["campaign_measurement_terminal_id"] = (
        domains.extension_content_id_v180r12r3r2(
            domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R3R2_DOMAIN,
            payload,
        )
    )
    with pytest.raises(
        finalizer.ConstructionK7CampaignMeasurementFinalizerV180R12R3R2Error,
        match="success artifact facts changed",
    ):
        finalizer.PendingCampaignMeasurementTerminalV180R12R3R2(
            canonical_json_bytes(document)
        )


def test_pending_terminal_rejects_resigned_extra_field() -> None:
    result = _finalize(_closed_inputs())
    document = result.document
    document["foreign_claim"] = False
    payload = dict(document)
    payload.pop("campaign_measurement_terminal_id")
    document["campaign_measurement_terminal_id"] = (
        domains.extension_content_id_v180r12r3r2(
            domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R3R2_DOMAIN,
            payload,
        )
    )
    with pytest.raises(
        finalizer.ConstructionK7CampaignMeasurementFinalizerV180R12R3R2Error,
        match="identity or gate changed",
    ):
        finalizer.PendingCampaignMeasurementTerminalV180R12R3R2(
            canonical_json_bytes(document)
        )


@pytest.mark.parametrize("mutation", ("event_order", "evidence_count", "os_order"))
def test_finalizer_rejects_population_denominator_or_order_mutation(
    mutation: str,
) -> None:
    inputs = _closed_inputs()
    if mutation == "event_order":
        rows = list(inputs["event_documents"])
        rows[1], rows[2] = rows[2], rows[1]
        inputs["event_documents"] = tuple(rows)
    elif mutation == "evidence_count":
        inputs["evidence_documents"] = inputs["evidence_documents"][:-1]
    else:
        rows = list(inputs["os_receipt_documents"])
        rows[0], rows[1] = rows[1], rows[0]
        inputs["os_receipt_documents"] = tuple(rows)
    with pytest.raises(
        finalizer.ConstructionK7CampaignMeasurementFinalizerV180R12R3R2Error
    ):
        _finalize(inputs)


def test_finalizer_rejects_unknown_or_resigned_os_receipt() -> None:
    inputs = _closed_inputs()
    rows = list(inputs["os_receipt_documents"])
    candidate = copy.deepcopy(
        next(
            document
            for document in inputs["fixture"]["docs"].values()
            if document["schema"]
            == "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2"
        )
    )
    candidate["memory_peak_bytes"] += 1
    rows[-1] = canonical_json_bytes(candidate)
    inputs["os_receipt_documents"] = tuple(rows)
    with pytest.raises(
        finalizer.ConstructionK7CampaignMeasurementFinalizerV180R12R3R2Error
    ):
        _finalize(inputs)


def test_finalizer_rejects_noncanonical_raw_event_bytes() -> None:
    inputs = _closed_inputs()
    rows = list(inputs["event_documents"])
    rows[0] += b"\n"
    inputs["event_documents"] = tuple(rows)
    with pytest.raises(
        finalizer.ConstructionK7CampaignMeasurementFinalizerV180R12R3R2Error,
        match="canonical",
    ):
        _finalize(inputs)


def test_finalizer_source_has_no_effectful_boundary() -> None:
    source_path = Path(finalizer.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert not imported.intersection(
        {"os", "pathlib", "shutil", "subprocess", "tempfile"}
    )
    assert all(
        not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"open", "exec", "eval", "compile", "__import__"}
        )
        for node in ast.walk(tree)
    )
