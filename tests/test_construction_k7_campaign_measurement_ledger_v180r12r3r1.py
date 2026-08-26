from __future__ import annotations

import copy
import hashlib
import json

import pytest

from acfqp import construction_k7_campaign_measurement_ledger_v180r12r3r1 as ledger
from acfqp import construction_k7_campaign_measurement_worker_v180r12r3r1 as worker
from acfqp import construction_k7_domain_registry_extension_v180r12r3r1 as identity_domains
from acfqp import construction_k7_domain_registry_extension_v180r12r3r1e as domains
from acfqp.accounting_v1 import KERNEL_TRANSITION_CALLS, SHARED_AXES
from acfqp.phase3e_ids import canonical_json_bytes


PROTOCOL_ID = "a" * 64
AUTHORIZATION_ID = "b" * 64

OUTCOME = {
    "ATTEMPT_OPEN": "OPEN",
    "INPUT_READ_INTENT": "INTENT",
    "INPUT_READ_OUTCOME": "SUCCESS",
    "STAGE_WRITE_INTENT": "INTENT",
    "STAGE_WRITE_OUTCOME": "SUCCESS",
    "MOUNT_VISIBILITY_OPEN": "OPEN",
    "MOUNT_VISIBILITY_CLOSE": "CLOSED",
    "SEMANTIC_HASH_INTENT": "INTENT",
    "SEMANTIC_HASH_OUTCOME": "SUCCESS",
    "INTEGRITY_CHECK_INTENT": "INTENT",
    "INTEGRITY_CHECK_OUTCOME": "PASS",
    "PROTOCOL_CHECK_INTENT": "INTENT",
    "PROTOCOL_CHECK_OUTCOME": "PASS",
    "PROCESS_BIRTH_INTENT": "INTENT",
    "PROCESS_BIRTH_OUTCOME": "SUCCESS",
    "PROCESS_REAP": "SUCCESS",
    "SUBJECT_WRITE_INTENT": "INTENT",
    "SUBJECT_WRITE_OUTCOME": "SUCCESS",
    "SUBJECT_COMMIT": "COMMITTED",
    "WINDOW_CLOSED": "CLOSED",
    "CGROUP_OBSERVED": "OBSERVED",
    "LEDGER_CLOSED": "CLOSED",
}


def _cid(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


AUTHORIZATION_EVIDENCE_ID = _cid("authorization-evidence")
EXECUTION_SLOT_ID = _cid("execution-slot")
LOGICAL_OCCURRENCE_ID = _cid("logical-occurrence")
EXECUTION_NONCE = _cid("execution-nonce")
PRELAUNCH_MATERIALIZATION_TERMINAL_ID = _cid("materialization-terminal")
PRELAUNCH_MATERIALIZATION_TERMINAL_BYTE_COUNT = 4096
PRELAUNCH_MATERIALIZATION_TERMINAL_SHA256 = _cid("materialization-terminal-bytes")
PRELAUNCH_LAUNCH_MANIFEST_SHA256 = _cid("launch-manifest")
PRECOMPILED_SOURCE_BUNDLE_SHA256 = _cid("precompiled-source-bundle")
PRELAUNCH_LAUNCH_RULE_ID = _cid("launch-rule")
MEASUREMENT_LAUNCH_REPOSITORY_ROOT = "/tmp/v180r12r3r1-test-repository"


def _measurement_launch_attempt_document() -> dict:
    prelaunch_root = (
        f"{MEASUREMENT_LAUNCH_REPOSITORY_ROOT}/.tmp/exact-freeze/"
        "v180r12r3r1_campaign_measurement_prelaunch"
    )
    payload = {
        "schema": "acfqp.v180r12r3r1_prelaunch_launch_attempt.v1",
        "launch_rule_id": PRELAUNCH_LAUNCH_RULE_ID,
        "target": "measurement",
        "repository_root": MEASUREMENT_LAUNCH_REPOSITORY_ROOT,
        "materialization_terminal_id": PRELAUNCH_MATERIALIZATION_TERMINAL_ID,
        "materialization_terminal_byte_count": (
            PRELAUNCH_MATERIALIZATION_TERMINAL_BYTE_COUNT
        ),
        "materialization_terminal_sha256": (
            PRELAUNCH_MATERIALIZATION_TERMINAL_SHA256
        ),
        "launch_manifest_sha256": PRELAUNCH_LAUNCH_MANIFEST_SHA256,
        "child_argv": [
            "/usr/bin/python3", "-I", "-S", "-B", "-X",
            "pycache_prefix=/dev/null/v180r12r3r1",
            f"{prelaunch_root}/bootstrap.py",
            "measurement",
            MEASUREMENT_LAUNCH_REPOSITORY_ROOT,
            prelaunch_root,
            f"{prelaunch_root}/launch_manifest.json",
        ],
        "child_environment": {
            "ACFQP_V180R12R3R1_LAUNCH_MANIFEST_SHA256": (
                PRELAUNCH_LAUNCH_MANIFEST_SHA256
            ),
            "LC_CTYPE": "C.UTF-8",
        },
        "address_space_hard_cap_bytes": 16 * 1024 * 1024 * 1024,
        "address_space_cap_applied_before_child_exec": True,
        "wall_timeout_seconds": 14_400,
        "attempt_lock_written_before_child_exec": True,
        "same_target_identity_rerun_forbidden": True,
        "preauthorization_supervision": True,
        "campaign_actual_measurement": False,
        "scientific_occurrence_started": False,
        "authorized_child_measurement_execution_attempted": True,
        "authorized_child_measurement_execution_completed": False,
        "producer_free_verification_attempted": False,
        "producer_free_verification_completed": False,
    }
    return {
        **payload,
        "launch_attempt_id": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }


MEASUREMENT_LAUNCH_ATTEMPT_ID = _measurement_launch_attempt_document()[
    "launch_attempt_id"
]
ATTEMPT_ID = identity_domains.derive_campaign_measurement_attempt_id_v180r12r3r1(
    protocol_id=PROTOCOL_ID,
    authorization_id=AUTHORIZATION_ID,
    authorization_evidence_id=AUTHORIZATION_EVIDENCE_ID,
    campaign_measurement_execution_slot_id=EXECUTION_SLOT_ID,
    logical_occurrence_id=LOGICAL_OCCURRENCE_ID,
    execution_nonce=EXECUTION_NONCE,
)


def _precompiled_source_rows() -> list[dict]:
    return [
        {
            "source_kind": "MODULE",
            "name": "acfqp.phase3e_ids",
            "source_path": "src/acfqp/phase3e_ids.py",
            "is_package": False,
            "marshal_byte_count": 4096,
            "marshal_sha256": _cid("module:acfqp.phase3e_ids"),
        },
        *[
            {
                "source_kind": "TARGET",
                "name": target,
                "source_path": source_path,
                "is_package": False,
                "marshal_byte_count": 8192 + ordinal,
                "marshal_sha256": _cid(f"target:{target}"),
            }
            for ordinal, (target, source_path) in enumerate(
                sorted(ledger.PRECOMPILED_TARGET_SOURCE_PATHS.items())
            )
        ],
    ]


def _signed(schema: str, identity_field: str, domain: str, **payload):
    body = {"schema": schema, "schema_version": "1.0.0", **payload}
    return {
        **body,
        identity_field: domains.extension_content_id_v180r12r3r1e(domain, body),
    }


def _worker_subject(
    *,
    campaign_attempt_record_id: str,
    snapshot_ids: list[str],
    stage_ids: list[str],
    open_visibility_ids: list[str],
    worker_birth_receipt_id: str,
    operation_manifest_id: str,
) -> dict:
    payload = {
        "schema": "acfqp.campaign_measurement_subject_result.v180r12r3r1",
        "schema_version": "1.0.0",
        "scope": "FRESH_PRODUCER_FREE_POST_OUTCOME_EVIDENCE_REPLAY_SUCCESSOR",
        "protocol_id": PROTOCOL_ID,
        "authorization_id": AUTHORIZATION_ID,
        "authorization_evidence_id": AUTHORIZATION_EVIDENCE_ID,
        "attempt_id": ATTEMPT_ID,
        "execution_slot_id": EXECUTION_SLOT_ID,
        "execution_nonce": EXECUTION_NONCE,
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "prelaunch_materialization_terminal_id": (
            PRELAUNCH_MATERIALIZATION_TERMINAL_ID
        ),
        "prelaunch_launch_manifest_sha256": PRELAUNCH_LAUNCH_MANIFEST_SHA256,
        "prelaunch_launch_rule_id": PRELAUNCH_LAUNCH_RULE_ID,
        "measurement_launch_attempt_id": MEASUREMENT_LAUNCH_ATTEMPT_ID,
        "campaign_attempt_record_id": campaign_attempt_record_id,
        "terminal_content_id": _cid("terminal-content"),
        "terminal_byte_count": 199_755,
        "terminal_sha256": _cid("terminal-sha"),
        "verification_content_id": _cid("verification-content"),
        "verification_byte_count": 2_752,
        "verification_sha256": _cid("verification-sha"),
        "terminal_snapshot_id": snapshot_ids[0],
        "verification_snapshot_id": snapshot_ids[1],
        "memfd_stage_receipt_ids": stage_ids,
        "open_visibility_receipt_ids": open_visibility_ids,
        "worker_birth_receipt_id": worker_birth_receipt_id,
        "operation_manifest_id": operation_manifest_id,
        "inner_content_ids": [
            {"label": f"inner.{index:03d}", "content_id": _cid(f"inner:{index}")}
            for index in range(129)
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
    for _ in range(4):
        projected = len(canonical_json_bytes({**payload, "subject_result_id": "0" * 64}))
        if payload["subject_byte_count"] == projected:
            break
        payload["subject_byte_count"] = projected
    identity = domains.extension_content_id_v180r12r3r1e(
        domains.CONSTRUCTION_K7_CAMPAIGN_SUBJECT_RESULT_V180R12R3R1E_DOMAIN,
        payload,
    )
    document = {**payload, "subject_result_id": identity}
    assert len(canonical_json_bytes(document)) == document["subject_byte_count"]
    return document


def _semantic_observed_value(subject: dict, kind: str, ordinal: int):
    if kind != "SEMANTIC_HASH":
        return True
    if ordinal in {0, 2}:
        return subject["terminal_sha256"]
    if ordinal in {1, 3}:
        return subject["verification_sha256"]
    if ordinal == 4:
        return subject["terminal_content_id"]
    if ordinal == 5:
        return subject["verification_content_id"]
    if 6 <= ordinal < 135:
        return subject["inner_content_ids"][ordinal - 6]["content_id"]
    if ordinal == 135:
        return subject["subject_result_id"]
    if ordinal == 136:
        return hashlib.sha256(canonical_json_bytes(subject)).hexdigest()
    raise AssertionError("semantic hash ordinal escaped fixture")


def _fixture(
    *,
    memory_peak: int = 999,
    frozen_terminal_read: int = 199_755,
    io_endpoint_mutation: tuple[str, str, int, str, str] | None = None,
    subject_provenance_mutation: tuple[str, str] | None = None,
    foreign_semantic_operation: bool = False,
    foreign_semantic_authority: str | None = None,
    semantic_auxiliary_mutation: tuple[str, list[dict]] | None = None,
    foreign_execution_source_manifest: bool = False,
):
    schedule = ledger.build_campaign_operation_schedule_v180r12r3r1(ATTEMPT_ID)
    manifest = ledger.campaign_operation_manifest_v180r12r3r1(ATTEMPT_ID)
    manifest_id = manifest["campaign_operation_manifest_id"]
    docs: dict[str, dict] = {manifest_id: manifest}

    def add_doc(document: dict) -> str:
        schema = document["schema"]
        _domain, identity_field = ledger._EVIDENCE_SCHEMA_DESCRIPTOR[schema]
        identity = document[identity_field]
        assert identity not in docs
        docs[identity] = document
        return identity

    specs = {(row.slot, row.family, row.ordinal): row for row in schedule}
    attempt_spec = specs[("ATTEMPT", "OPEN", 0)]
    attempt = ledger.issue_campaign_attempt_record_v180r12r3r1(
        protocol_id=PROTOCOL_ID,
        authorization_id=AUTHORIZATION_ID,
        authorization_evidence_id=AUTHORIZATION_EVIDENCE_ID,
        campaign_measurement_execution_slot_id=EXECUTION_SLOT_ID,
        logical_occurrence_id=LOGICAL_OCCURRENCE_ID,
        execution_nonce=EXECUTION_NONCE,
        prelaunch_materialization_terminal_id=(
            PRELAUNCH_MATERIALIZATION_TERMINAL_ID
        ),
        prelaunch_launch_manifest_sha256=PRELAUNCH_LAUNCH_MANIFEST_SHA256,
        prelaunch_launch_rule_id=PRELAUNCH_LAUNCH_RULE_ID,
        measurement_launch_attempt_id=MEASUREMENT_LAUNCH_ATTEMPT_ID,
        attempt_id=ATTEMPT_ID,
        operation_id=attempt_spec.operation_id,
        operation_manifest_id=manifest_id,
    )
    attempt_record_id = add_doc(attempt)

    topology = _signed(
        "acfqp.campaign_cgroup_topology_receipt.v180r12r3r1",
        "cgroup_topology_receipt_id",
        domains.CONSTRUCTION_K7_CGROUP_TOPOLOGY_RECEIPT_V180R12R3R1E_DOMAIN,
        memory_max_bytes=ledger.MEMORY_MAX_BYTES,
        pids_max=2,
        root_populated_before_birth=False,
        root_process_count_before_birth=0,
        leaf_process_counts_before_birth=[0, 0],
    )
    topology_id = add_doc(topology)

    source_manifest = ledger.issue_native_zero_source_manifest_v180r12r3r1(
        protocol_id=PROTOCOL_ID,
        authorization_id=AUTHORIZATION_ID,
        attempt_id=ATTEMPT_ID,
        operation_manifest_id=manifest_id,
        prelaunch_launch_manifest_sha256=PRELAUNCH_LAUNCH_MANIFEST_SHA256,
        precompiled_source_bundle_sha256=PRECOMPILED_SOURCE_BUNDLE_SHA256,
        precompiled_source_rows=_precompiled_source_rows(),
    )
    source_manifest_id = add_doc(source_manifest)
    import_inventory = ledger.issue_native_zero_import_inventory_v180r12r3r1(
        protocol_id=PROTOCOL_ID,
        authorization_id=AUTHORIZATION_ID,
        attempt_id=ATTEMPT_ID,
        source_manifest=source_manifest,
    )
    import_inventory_id = add_doc(import_inventory)

    snapshot_ids: list[str] = []
    stage_ids: list[str] = []
    for ordinal, byte_count in enumerate((199_755, 2_752)):
        snapshot = _signed(
            "acfqp.campaign_stable_input_snapshot.v180r12r3r1",
            "stable_input_snapshot_id",
            domains.CONSTRUCTION_K7_STABLE_INPUT_SNAPSHOT_V180R12R3R1E_DOMAIN,
            role=("TERMINAL" if ordinal == 0 else "VERIFICATION"),
            observed_byte_count=byte_count,
            observed_sha256=_cid(f"snapshot-{ordinal}"),
        )
        snapshot_id = add_doc(snapshot)
        snapshot_ids.append(snapshot_id)
        stage = _signed(
            "acfqp.campaign_memfd_stage_receipt.v180r12r3r1",
            "memfd_stage_receipt_id",
            domains.CONSTRUCTION_K7_MEMFD_STAGE_RECEIPT_V180R12R3R1E_DOMAIN,
            input_snapshot_id=snapshot_id,
            role=("TERMINAL" if ordinal == 0 else "VERIFICATION"),
            byte_count=byte_count,
            sha256=snapshot["observed_sha256"],
        )
        stage_ids.append(add_doc(stage))

    birth_by_role: dict[str, str] = {}
    reap_by_role: dict[str, str] = {}
    for role in ("SUPERVISOR", "WORKER"):
        birth = _signed(
            "acfqp.campaign_pidfd_birth_receipt.v180r12r3r1",
            "pidfd_birth_receipt_id",
            domains.CONSTRUCTION_K7_PIDFD_BIRTH_RECEIPT_V180R12R3R1E_DOMAIN,
            topology_receipt_id=topology_id,
            process_role=role,
            pid=10 if role == "SUPERVISOR" else 11,
        )
        birth_id = add_doc(birth)
        birth_by_role[role] = birth_id
        reap = _signed(
            "acfqp.campaign_pidfd_reap_receipt.v180r12r3r1",
            "pidfd_reap_receipt_id",
            domains.CONSTRUCTION_K7_PIDFD_REAP_RECEIPT_V180R12R3R1E_DOMAIN,
            process_birth_receipt_id=birth_id,
            process_role=role,
            waitid_status=0,
        )
        reap_by_role[role] = add_doc(reap)

    mount_evidence: dict[tuple[str, str], str] = {}
    open_visibility_ids: list[str] = []
    close_visibility_ids: list[str] = []
    for ordinal, stage_id in enumerate(stage_ids):
        spec = specs[("MOUNT", "SEALED_MEMFD", ordinal)]
        for state in ("OPEN", "CLOSED"):
            document = _signed(
                "acfqp.campaign_fd_visibility_receipt.v180r12r3r1",
                "fd_visibility_receipt_id",
                domains.CONSTRUCTION_K7_FD_VISIBILITY_RECEIPT_V180R12R3R1E_DOMAIN,
                stage_receipt_id=stage_id,
                holder_process_birth_receipt_id=birth_by_role["SUPERVISOR"],
                holder_role="SUPERVISOR",
                role=("TERMINAL" if ordinal == 0 else "VERIFICATION"),
                state=state,
                visible=state == "OPEN",
            )
            identity = add_doc(document)
            kind = (
                "MOUNT_VISIBILITY_OPEN"
                if state == "OPEN"
                else "MOUNT_VISIBILITY_CLOSE"
            )
            mount_evidence[(kind, spec.operation_id)] = identity
            (open_visibility_ids if state == "OPEN" else close_visibility_ids).append(
                identity
            )

    subject = _worker_subject(
        campaign_attempt_record_id=attempt_record_id,
        snapshot_ids=snapshot_ids,
        stage_ids=stage_ids,
        open_visibility_ids=open_visibility_ids,
        worker_birth_receipt_id=birth_by_role["WORKER"],
        operation_manifest_id=manifest_id,
    )
    if subject_provenance_mutation is not None:
        field_name, foreign_value = subject_provenance_mutation
        subject_payload = dict(subject)
        subject_payload.pop("subject_result_id")
        subject_payload[field_name] = foreign_value
        subject = {
            **subject_payload,
            "subject_result_id": domains.extension_content_id_v180r12r3r1e(
                domains.CONSTRUCTION_K7_CAMPAIGN_SUBJECT_RESULT_V180R12R3R1E_DOMAIN,
                subject_payload,
            ),
        }
        assert len(canonical_json_bytes(subject)) == subject["subject_byte_count"]
    subject_id = add_doc(subject)
    subject_byte_count = subject["subject_byte_count"]

    semantic_by_operation: dict[str, str] = {}
    semantic_ids: list[str] = []
    semantic_ordinal = {"SEMANTIC_HASH": 0, "INTEGRITY_CHECK": 0, "PROTOCOL_CHECK": 0}
    semantic_operation_mutated = False
    semantic_auxiliary_mutated = False
    for spec in schedule:
        if spec.slot not in semantic_ordinal:
            continue
        kind = spec.slot
        ordinal = semantic_ordinal[kind]
        semantic_ordinal[kind] += 1
        outcome = "SUCCESS" if kind == "SEMANTIC_HASH" else "PASS"
        enum_kind = worker.SemanticOperationKindV180R12R3R1(kind)
        label = {
            "SEMANTIC_HASH": worker.SEMANTIC_HASH_OPERATION_LABELS,
            "INTEGRITY_CHECK": worker.INTEGRITY_CHECK_OPERATION_LABELS,
            "PROTOCOL_CHECK": worker.PROTOCOL_CHECK_OPERATION_LABELS,
        }[kind][ordinal]
        result = worker.ReplayOperationResultV180R12R3R1(
            enum_kind,
            label,
            spec.family,
            spec.ordinal,
            ordinal,
            spec.phase,
            spec.actor_role,
            outcome,
            1,
            _semantic_observed_value(subject, kind, ordinal),
        )
        document = worker.semantic_operation_receipt_v180r12r3r1(
            attempt_id=ATTEMPT_ID,
            operation_manifest_id=manifest_id,
            native_zero_source_manifest_id=source_manifest_id,
            native_zero_import_inventory_id=import_inventory_id,
            evidence_subject_id=attempt_record_id,
            result=result,
        ).to_document()
        receipt_operation_id = document["operation_id"]
        if foreign_semantic_operation and not semantic_operation_mutated:
            receipt_operation_id = _cid("foreign-semantic-operation")
            semantic_operation_mutated = True
        receipt_operation_manifest_id = document["operation_manifest_id"]
        receipt_source_manifest_id = document["native_zero_source_manifest_id"]
        receipt_import_inventory_id = document["native_zero_import_inventory_id"]
        if foreign_semantic_authority is not None and not semantic_operation_mutated:
            if foreign_semantic_authority == "operation":
                receipt_operation_manifest_id = _cid("foreign-operation-manifest")
            elif foreign_semantic_authority == "source":
                receipt_source_manifest_id = _cid("foreign-source-manifest")
            elif foreign_semantic_authority == "import":
                receipt_import_inventory_id = _cid("foreign-import-inventory")
            else:
                raise AssertionError("unknown semantic authority mutation")
            semantic_operation_mutated = True
        payload = dict(document)
        payload.pop("semantic_operation_receipt_id")
        payload.update(
            operation_id=receipt_operation_id,
            operation_manifest_id=receipt_operation_manifest_id,
            native_zero_source_manifest_id=receipt_source_manifest_id,
            native_zero_import_inventory_id=receipt_import_inventory_id,
        )
        if (
            semantic_auxiliary_mutation is not None
            and kind == semantic_auxiliary_mutation[0]
            and not semantic_auxiliary_mutated
        ):
            payload["auxiliary_values"] = semantic_auxiliary_mutation[1]
            semantic_auxiliary_mutated = True
        document = {
            **payload,
            "semantic_operation_receipt_id": (
                domains.extension_content_id_v180r12r3r1e(
                    domains.CONSTRUCTION_K7_SEMANTIC_OPERATION_RECEIPT_V180R12R3R1E_DOMAIN,
                    payload,
                )
            ),
        }
        identity = add_doc(document)
        semantic_by_operation[spec.operation_id] = identity
        semantic_ids.append(identity)

    replay_subject = _signed(
        "acfqp.campaign_replay_subject_receipt.v180r12r3r1",
        "replay_subject_receipt_id",
        domains.CONSTRUCTION_K7_REPLAY_SUBJECT_RECEIPT_V180R12R3R1E_DOMAIN,
        operation_manifest_id=manifest_id,
        native_zero_source_manifest_id=source_manifest_id,
        native_zero_import_inventory_id=import_inventory_id,
        terminal_snapshot_id=snapshot_ids[0],
        verification_snapshot_id=snapshot_ids[1],
        open_visibility_receipt_ids=open_visibility_ids,
        campaign_attempt_record_id=attempt_record_id,
        subject_result_id=subject_id,
        semantic_operation_receipt_ids=semantic_ids,
        subject_byte_count=subject_byte_count,
        producer_module_imported=False,
    )
    replay_subject_id = add_doc(replay_subject)

    io_value: dict[str, int] = {}
    io_evidence: dict[tuple[str, str], str] = {}
    for spec in schedule:
        if spec.slot == "INPUT_READ":
            if spec.family == "FROZEN_SOURCE":
                value = (frozen_terminal_read, 2_752)[spec.ordinal]
                source, target = manifest_id, snapshot_ids[spec.ordinal]
            elif spec.family == "SEALED_STAGE":
                value = (199_755, 2_752)[spec.ordinal]
                source, target = stage_ids[spec.ordinal], birth_by_role["WORKER"]
            else:
                value = subject_byte_count
                source, target = subject_id, birth_by_role["SUPERVISOR"]
            event_kind = "INPUT_READ_OUTCOME"
        elif spec.slot == "STAGE_WRITE":
            value = (199_755, 2_752)[spec.ordinal]
            source, target = snapshot_ids[spec.ordinal], stage_ids[spec.ordinal]
            event_kind = "STAGE_WRITE_OUTCOME"
        elif spec.slot == "SUBJECT_WRITE":
            value = subject_byte_count
            source, target = subject_id, birth_by_role["WORKER"]
            event_kind = "SUBJECT_WRITE_OUTCOME"
        else:
            continue
        if io_endpoint_mutation is not None and (
            spec.slot,
            spec.family,
            spec.ordinal,
        ) == io_endpoint_mutation[:3]:
            endpoint, replacement_key = io_endpoint_mutation[3:]
            replacements = {
                "terminal_snapshot": snapshot_ids[0],
                "verification_snapshot": snapshot_ids[1],
                "terminal_stage": stage_ids[0],
                "verification_stage": stage_ids[1],
                "worker_birth": birth_by_role["WORKER"],
                "supervisor_birth": birth_by_role["SUPERVISOR"],
                "subject": subject_id,
                "replay_subject": replay_subject_id,
                "manifest": manifest_id,
            }
            if endpoint == "source":
                source = replacements[replacement_key]
            else:
                target = replacements[replacement_key]
        transfer = ledger.issue_campaign_io_transfer_receipt_v180r12r3r1(
            protocol_id=PROTOCOL_ID,
            authorization_id=AUTHORIZATION_ID,
            attempt_id=ATTEMPT_ID,
            operation_id=spec.operation_id,
            event_kind=event_kind,
            measured_value=value,
            returned_chunk_byte_counts=(value,),
            source_evidence_id=source,
            target_evidence_id=target,
        )
        identity = add_doc(transfer)
        io_value[spec.operation_id] = value
        io_evidence[(event_kind, spec.operation_id)] = identity

    readback_spec = specs[("INPUT_READ", "SUBJECT_READBACK", 0)]
    commit_spec = specs[("SUBJECT_COMMIT", "SUBJECT_RESULT", 0)]
    subject_commit = ledger.issue_subject_commit_receipt_v180r12r3r1(
        protocol_id=PROTOCOL_ID,
        authorization_id=AUTHORIZATION_ID,
        attempt_id=ATTEMPT_ID,
        operation_id=commit_spec.operation_id,
        subject_id=subject_id,
        replay_subject_receipt_id=replay_subject_id,
        readback_transfer_receipt_id=io_evidence[
            ("INPUT_READ_OUTCOME", readback_spec.operation_id)
        ],
        subject_byte_count=subject_byte_count,
    )
    subject_commit_id = add_doc(subject_commit)
    window_spec = specs[("WINDOW", "CLOSE", 0)]
    window_closure = ledger.issue_window_closure_receipt_v180r12r3r1(
        protocol_id=PROTOCOL_ID,
        authorization_id=AUTHORIZATION_ID,
        attempt_id=ATTEMPT_ID,
        operation_id=window_spec.operation_id,
        subject_commit_receipt_id=subject_commit_id,
        close_visibility_receipt_ids=close_visibility_ids,
    )
    window_closure_id = add_doc(window_closure)

    cgroup = _signed(
        "acfqp.campaign_cgroup_observation_receipt.v180r12r3r1",
        "cgroup_observation_receipt_id",
        domains.CONSTRUCTION_K7_CGROUP_OBSERVATION_RECEIPT_V180R12R3R1E_DOMAIN,
        topology_receipt_id=topology_id,
        supervisor_reap_receipt_id=reap_by_role["SUPERVISOR"],
        worker_reap_receipt_id=reap_by_role["WORKER"],
        memory_peak_bytes=memory_peak,
        pids_peak=2,
        root_populated=False,
        root_process_count=0,
        supervisor_leaf_process_count=0,
        worker_leaf_process_count=0,
    )
    cgroup_id = add_doc(cgroup)
    evidence_for_event: dict[tuple[str, str], str] = {
        ("ATTEMPT_OPEN", attempt_spec.operation_id): attempt_record_id,
        ("PROCESS_BIRTH_OUTCOME", specs[("PROCESS", "SUPERVISOR", 0)].operation_id): birth_by_role["SUPERVISOR"],
        ("PROCESS_BIRTH_OUTCOME", specs[("PROCESS", "WORKER", 0)].operation_id): birth_by_role["WORKER"],
        ("PROCESS_REAP", specs[("PROCESS", "SUPERVISOR", 0)].operation_id): reap_by_role["SUPERVISOR"],
        ("PROCESS_REAP", specs[("PROCESS", "WORKER", 0)].operation_id): reap_by_role["WORKER"],
        ("SUBJECT_COMMIT", commit_spec.operation_id): subject_commit_id,
        ("WINDOW_CLOSED", window_spec.operation_id): window_closure_id,
        ("CGROUP_OBSERVED", specs[("CGROUP", "FINAL_OBSERVE", 0)].operation_id): cgroup_id,
        **io_evidence,
        **mount_evidence,
    }
    for spec in schedule:
        if spec.slot in {"SEMANTIC_HASH", "INTEGRITY_CHECK", "PROTOCOL_CHECK"}:
            evidence_for_event[(f"{spec.slot}_OUTCOME", spec.operation_id)] = semantic_by_operation[spec.operation_id]

    state = ledger.open_campaign_ledger_v180r12r3r1(
        protocol_id=PROTOCOL_ID,
        authorization_id=AUTHORIZATION_ID,
        attempt_id=ATTEMPT_ID,
        max_event_count=4_096,
        max_event_byte_count=65_536,
        max_ledger_byte_count=64 * 1024 * 1024,
    )
    clock = 0

    def emit(kind: str, spec, *, role=None, phase=None, measured=None):
        nonlocal state, clock
        clock += 1
        evidence_id = evidence_for_event.get((kind, spec.operation_id))
        state, _event = ledger.append_campaign_event_v180r12r3r1(
            state,
            phase=phase or spec.phase,
            actor_role=role or spec.actor_role,
            operation_id=spec.operation_id,
            event_kind=kind,
            monotonic_ns=clock,
            payload={
                "evidence_id": evidence_id,
                "outcome_code": OUTCOME[kind],
                "measured_value": measured,
                "auxiliary_values": [],
            },
        )

    def pair(stem: str, spec, value: int):
        emit(f"{stem}_INTENT", spec)
        emit(f"{stem}_OUTCOME", spec, measured=value)

    emit("ATTEMPT_OPEN", attempt_spec)
    supervisor_process = specs[("PROCESS", "SUPERVISOR", 0)]
    pair("PROCESS_BIRTH", supervisor_process, 1)
    for spec in schedule:
        if spec.slot == "INPUT_READ" and spec.phase == "STAGE":
            pair("INPUT_READ", spec, io_value[spec.operation_id])
    for spec in schedule:
        if spec.slot == "STAGE_WRITE":
            pair("STAGE_WRITE", spec, io_value[spec.operation_id])
    for spec in schedule:
        if spec.slot == "MOUNT":
            emit(
                "MOUNT_VISIBILITY_OPEN",
                spec,
                measured=sum(
                    docs[stage_ids[index]]["byte_count"]
                    for index in range(spec.ordinal + 1)
                ),
            )
    for slot in ("SEMANTIC_HASH", "INTEGRITY_CHECK"):
        for spec in schedule:
            if spec.slot == slot and spec.phase == "STAGE":
                pair(slot, spec, 1)

    worker_process = specs[("PROCESS", "WORKER", 0)]
    pair("PROCESS_BIRTH", worker_process, 1)
    for spec in schedule:
        if spec.slot == "INPUT_READ" and spec.phase == "WORKER":
            pair("INPUT_READ", spec, io_value[spec.operation_id])
    for slot in ("SEMANTIC_HASH", "INTEGRITY_CHECK", "PROTOCOL_CHECK"):
        for spec in schedule:
            if spec.slot == slot and spec.phase == "WORKER":
                pair(slot, spec, 1)
    subject_write = specs[("SUBJECT_WRITE", "SUBJECT_RESULT", 0)]
    pair("SUBJECT_WRITE", subject_write, io_value[subject_write.operation_id])
    emit("PROCESS_REAP", worker_process, role="SUPERVISOR", phase="WORKER")

    pair("INPUT_READ", readback_spec, io_value[readback_spec.operation_id])
    for slot in ("SEMANTIC_HASH", "INTEGRITY_CHECK"):
        for spec in schedule:
            if spec.slot == slot and spec.phase == "COMMIT":
                pair(slot, spec, 1)
    emit("SUBJECT_COMMIT", commit_spec)
    for spec in schedule:
        if spec.slot == "MOUNT":
            emit("MOUNT_VISIBILITY_CLOSE", spec, role="SUPERVISOR", phase="WINDOW_CLOSE")
    emit("WINDOW_CLOSED", window_spec)
    window_event = state.events[-1]
    assert window_event.event_kind == "WINDOW_CLOSED"
    execution = ledger.issue_campaign_execution_closure_v180r12r3r1(
        protocol_id=PROTOCOL_ID,
        authorization_id=AUTHORIZATION_ID,
        attempt_id=ATTEMPT_ID,
        subject_id=subject_id,
        window_closed_event_id=window_event.event_id,
        window_closure_receipt_id=window_closure_id,
        operation_manifest_id=manifest_id,
        source_manifest_id=(
            _cid("foreign-execution-source-manifest")
            if foreign_execution_source_manifest
            else source_manifest_id
        ),
        import_inventory_id=import_inventory_id,
        precompiled_source_bundle_sha256=PRECOMPILED_SOURCE_BUNDLE_SHA256,
    )
    execution_id = add_doc(execution)
    emit("PROCESS_REAP", supervisor_process, role="OBSERVER", phase="OS_OBSERVE")
    emit("CGROUP_OBSERVED", specs[("CGROUP", "FINAL_OBSERVE", 0)], measured=memory_peak)
    emit("LEDGER_CLOSED", specs[("LEDGER", "CLOSE", 0)])
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
    }


def _artifact(**kwargs):
    fixture = _fixture(**kwargs)
    result = ledger.derive_campaign_measurement_ledger_v180r12r3r1(
        fixture["state"],
        subject_id=fixture["subject_id"],
        evidence_documents_by_id=fixture["docs"],
        expected_native_zero_source_manifest_id=fixture["source_manifest_id"],
        expected_native_zero_import_inventory_id=fixture["import_inventory_id"],
    )
    return fixture, result


def test_exact_operation_manifest_event_chain_and_evidence_denominators() -> None:
    fixture, result = _artifact()
    events = result.state.events
    assert len(ledger.build_campaign_operation_schedule_v180r12r3r1(ATTEMPT_ID)) == 314
    assert len(events) == 625
    assert sum(row.payload["evidence_id"] is not None for row in events) == 317
    assert len(fixture["docs"]) == 328
    assert events[0].previous_event_id is None
    assert all(
        right.previous_event_id == left.event_id
        for left, right in zip(events, events[1:])
    )


def test_attempt_anchor_is_pre_cgroup_and_closes_future_subject_references() -> None:
    fixture = _fixture()
    documents = fixture["docs"]
    attempt = next(
        row
        for row in documents.values()
        if row["schema"] == "acfqp.campaign_attempt_record.v180r12r3r1"
    )
    attempt_id = attempt["campaign_attempt_record_id"]
    subject = documents[fixture["subject_id"]]
    replay = next(
        row
        for row in documents.values()
        if row["schema"] == "acfqp.campaign_replay_subject_receipt.v180r12r3r1"
    )
    semantics = [
        row
        for row in documents.values()
        if row["schema"] == "acfqp.campaign_semantic_operation_receipt.v180r12r3r1"
    ]
    first_event = fixture["state"].events[0]

    assert "cgroup_topology_receipt_id" not in attempt
    assert first_event.event_kind == "ATTEMPT_OPEN"
    assert first_event.payload["evidence_id"] == attempt_id
    assert subject["campaign_attempt_record_id"] == attempt_id
    assert len(semantics) == 297
    assert {row["evidence_subject_id"] for row in semantics} == {attempt_id}
    assert replay["campaign_attempt_record_id"] == attempt_id
    assert replay["subject_result_id"] == fixture["subject_id"]
    assert set(replay["semantic_operation_receipt_ids"]) == {
        row["semantic_operation_receipt_id"] for row in semantics
    }


def test_all_297_semantic_receipts_use_the_real_worker_factory_auxiliary_rows() -> None:
    fixture, _result = _artifact()
    semantics = [
        row
        for row in fixture["docs"].values()
        if row["schema"]
        == "acfqp.campaign_semantic_operation_receipt.v180r12r3r1"
    ]
    assert len(semantics) == 297
    by_kind = {
        kind: [row for row in semantics if row["kind"] == kind]
        for kind in ("SEMANTIC_HASH", "INTEGRITY_CHECK", "PROTOCOL_CHECK")
    }
    assert {kind: len(rows) for kind, rows in by_kind.items()} == {
        "SEMANTIC_HASH": 137,
        "INTEGRITY_CHECK": 145,
        "PROTOCOL_CHECK": 15,
    }
    assert all(
        row["auxiliary_values"]
        == [{"name": "observed_sha256", "value": row["auxiliary_values"][0]["value"]}]
        and len(row["auxiliary_values"][0]["value"]) == 64
        for row in by_kind["SEMANTIC_HASH"]
    )
    assert all(
        row["auxiliary_values"] == [{"name": "check_passed", "value": True}]
        for kind in ("INTEGRITY_CHECK", "PROTOCOL_CHECK")
        for row in by_kind[kind]
    )


@pytest.mark.parametrize(
    ("kind", "auxiliary"),
    (
        ("SEMANTIC_HASH", []),
        ("SEMANTIC_HASH", [{"name": "observed_sha256", "value": "f" * 63}]),
        ("SEMANTIC_HASH", [{"name": "check_passed", "value": True}]),
        ("INTEGRITY_CHECK", [{"name": "check_passed", "value": False}]),
        ("PROTOCOL_CHECK", [{"name": "observed_sha256", "value": "f" * 64}]),
    ),
)
def test_semantic_receipt_auxiliary_mutations_fail_closed(
    kind: str, auxiliary: list[dict]
) -> None:
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="semantic operation receipt semantics",
    ):
        _artifact(semantic_auxiliary_mutation=(kind, auxiliary))


@pytest.mark.parametrize(
    "field_name",
    (
        "authorization_evidence_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
    ),
)
def test_subject_result_rejects_foreign_attempt_provenance(field_name: str) -> None:
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="subject provenance",
    ):
        _artifact(subject_provenance_mutation=(field_name, "f" * 64))


def test_nine_positive_paths_and_independent_native_zero_projection_are_exact() -> None:
    fixture_data, result = _artifact()
    subject_bytes = fixture_data["subject_byte_count"]
    assert result.work_vector.values == {
        "common.hash_invocations": 137,
        "common.integrity_checks": 145,
        "common.protocol_checks": 15,
        "io.mounted_bytes_peak": 202_507,
        "io.output_bytes": subject_bytes,
        "io.read_bytes": 405_014 + subject_bytes,
        "io.staged_bytes": 202_507,
        "memory.working_bytes_peak": 999,
        "process.launches": 2,
    }
    assert all(not row.path_receipt.native_zero_observed for row in result.records)
    zero = result.native_zero_attestation.to_document()
    assert zero["comparison_axis"] == KERNEL_TRANSITION_CALLS
    assert zero["comparison_axis_value"] == 0
    assert zero["not_an_os_syscall_count"] is True
    assert zero["campaign_path_zero_observation_count"] == 0
    assert result.comparison_vector.value(KERNEL_TRANSITION_CALLS) == 0
    assert tuple(axis for axis, _value in result.comparison_vector.values) == SHARED_AXES
    assert (
        result.comparison_vector.to_document()["campaign_native_zero_attestation_id"]
        == result.native_zero_attestation.campaign_native_zero_attestation_id
    )
    proof = result.projection_proof.to_document()
    assert proof["projection_proof_references_native_zero_attestation"] is True
    assert proof["native_zero_projection_term"]["separate_from_nine_campaign_paths"] is True


def _mount_row(kind, operation, payload, value, byte_count, ordinal):
    return {
        "event_kind": kind,
        "operation_id": _cid(operation),
        "payload_id": _cid(payload),
        "measured_value": value,
        "byte_count": byte_count,
        "event_id": _cid(f"event-{ordinal}"),
        "evidence_id": _cid(f"evidence-{ordinal}"),
    }


def test_mount_interval_replay_sums_overlap_and_handles_nonoverlap() -> None:
    overlap = [
        _mount_row("MOUNT_VISIBILITY_OPEN", "a", "pa", 10, 10, 0),
        _mount_row("MOUNT_VISIBILITY_OPEN", "b", "pb", 30, 20, 1),
        _mount_row("MOUNT_VISIBILITY_CLOSE", "a", "pa", None, 10, 2),
        _mount_row("MOUNT_VISIBILITY_CLOSE", "b", "pb", None, 20, 3),
    ]
    assert ledger.replay_mount_visibility_intervals_v180r12r3r1(overlap).peak_mounted_bytes == 30
    nonoverlap = [
        overlap[0],
        overlap[2],
        _mount_row("MOUNT_VISIBILITY_OPEN", "b", "pb", 20, 20, 1),
        overlap[3],
    ]
    assert ledger.replay_mount_visibility_intervals_v180r12r3r1(nonoverlap).peak_mounted_bytes == 20


@pytest.mark.parametrize("mutation", ["duplicate", "identity_drift", "dangling"])
def test_mount_interval_replay_rejects_identity_mutations(mutation: str) -> None:
    rows = [
        _mount_row("MOUNT_VISIBILITY_OPEN", "a", "pa", 10, 10, 0),
        _mount_row("MOUNT_VISIBILITY_CLOSE", "a", "pa", None, 10, 1),
    ]
    if mutation == "duplicate":
        rows.insert(1, _mount_row("MOUNT_VISIBILITY_OPEN", "b", "pa", 10, 10, 2))
    elif mutation == "identity_drift":
        rows[1]["payload_id"] = _cid("pb")
    else:
        rows.pop()
    with pytest.raises(ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error):
        ledger.replay_mount_visibility_intervals_v180r12r3r1(rows)


def test_closure_is_canonical_replayable_and_distinguishes_90_9_99() -> None:
    fixture, result = _artifact()
    document = result.to_document()
    assert document["scope"] == "TEN_TERMINAL_AGGREGATION_MEASURED_REPLAY_SUCCESSOR"
    assert document["scope_model"] == "ROUTE_FREE_MEASURED_REPLAY_SUCCESSOR"
    assert ledger.COUNTER_REGISTRY_REFERENCE == "acfqp_counter_registry_v6"
    assert document["predecessor_occurrence_authoritative_receipt_count"] == 90
    assert document["predecessor_structural_obligation_count"] == 9
    assert document["predecessor_campaign_actual_receipt_count"] == 0
    assert document["successor_campaign_actual_receipt_count"] == 9
    assert document["combined_successor_authoritative_receipt_count"] == 99
    assert document["COUNTER_COMPLETENESS_GATE"] == "PENDING_INDEPENDENT_REPLAY"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert document["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert document["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    payload = dict(document)
    identity = payload.pop("campaign_ledger_closure_id")
    assert identity == domains.extension_content_id_v180r12r3r1e(
        domains.CONSTRUCTION_K7_CAMPAIGN_LEDGER_CLOSURE_V180R12R3R1E_DOMAIN,
        payload,
    )
    replayed = ledger.verify_campaign_measurement_ledger_v180r12r3r1(
        result.canonical_bytes,
        expected_native_zero_source_manifest_id=fixture["source_manifest_id"],
        expected_native_zero_import_inventory_id=fixture["import_inventory_id"],
        expected_protocol_id=PROTOCOL_ID,
        expected_authorization_id=AUTHORIZATION_ID,
        expected_attempt_id=ATTEMPT_ID,
        expected_subject_id=fixture["subject_id"],
        expected_max_event_count=4_096,
        expected_max_event_byte_count=65_536,
        expected_max_ledger_byte_count=64 * 1024 * 1024,
    )
    assert replayed.canonical_bytes == result.canonical_bytes


def test_same_count_foreign_operation_id_is_rejected_even_when_chain_is_resigned() -> None:
    fixture = _fixture()
    events = [row.to_document() for row in fixture["state"].events]
    target = 100
    events[target]["operation_id"] = _cid("foreign-operation")
    for index in range(target, len(events)):
        events[index]["previous_event_id"] = None if index == 0 else events[index - 1]["event_id"]
        payload = dict(events[index])
        payload.pop("event_id")
        events[index]["event_id"] = domains.extension_content_id_v180r12r3r1e(
            domains.CONSTRUCTION_K7_CAMPAIGN_LEDGER_EVENT_V180R12R3R1E_DOMAIN,
            payload,
        )
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="exact manifest",
    ):
        ledger.replay_campaign_event_chain_v180r12r3r1(
            events,
            max_event_count=4_096,
            max_event_byte_count=65_536,
            max_ledger_byte_count=64 * 1024 * 1024,
        )


def test_globally_reordered_adjacent_operations_fail_exact_625_position_schedule() -> None:
    fixture = _fixture()
    events = [row.to_document() for row in fixture["state"].events]
    start = next(
        index
        for index in range(len(events) - 3)
        if [events[index + offset]["event_kind"] for offset in range(4)]
        == [
            "SEMANTIC_HASH_INTENT",
            "SEMANTIC_HASH_OUTCOME",
            "SEMANTIC_HASH_INTENT",
            "SEMANTIC_HASH_OUTCOME",
        ]
    )
    events[start : start + 4] = [
        events[start],
        events[start + 2],
        events[start + 1],
        events[start + 3],
    ]
    for index, event in enumerate(events):
        event["sequence"] = index
        event["monotonic_ns"] = index + 1
        event["previous_event_id"] = None if index == 0 else events[index - 1]["event_id"]
        payload = dict(event)
        payload.pop("event_id")
        event["event_id"] = domains.extension_content_id_v180r12r3r1e(
            domains.CONSTRUCTION_K7_CAMPAIGN_LEDGER_EVENT_V180R12R3R1E_DOMAIN,
            payload,
        )
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="expanded 625-event schedule",
    ):
        ledger.replay_campaign_event_chain_v180r12r3r1(
            events,
            max_event_count=4_096,
            max_event_byte_count=65_536,
            max_ledger_byte_count=64 * 1024 * 1024,
        )


def test_unknown_and_resigned_evidence_documents_are_rejected() -> None:
    fixture = _fixture()
    missing = dict(fixture["docs"])
    missing.pop(next(iter(missing)))
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="328",
    ):
        ledger.derive_campaign_measurement_ledger_v180r12r3r1(
            fixture["state"],
            subject_id=fixture["subject_id"],
            evidence_documents_by_id=missing,
            expected_native_zero_source_manifest_id=fixture["source_manifest_id"],
            expected_native_zero_import_inventory_id=fixture["import_inventory_id"],
        )
    resigned = copy.deepcopy(fixture["docs"])
    target_id = next(
        identity
        for identity, document in resigned.items()
        if document["schema"] == "acfqp.campaign_io_transfer_receipt.v180r12r3r1"
    )
    resigned[target_id]["measured_value"] += 1
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="identity changed",
    ):
        ledger.derive_campaign_measurement_ledger_v180r12r3r1(
            fixture["state"],
            subject_id=fixture["subject_id"],
            evidence_documents_by_id=resigned,
            expected_native_zero_source_manifest_id=fixture["source_manifest_id"],
            expected_native_zero_import_inventory_id=fixture["import_inventory_id"],
        )


def test_full_worker_subject_is_the_only_registered_subject_and_chunks_are_exact() -> None:
    fixture = _fixture()
    subject = fixture["docs"][fixture["subject_id"]]
    assert (
        ledger.validate_campaign_subject_result_document_v180r12r3r1(
            subject,
            expected_protocol_id=PROTOCOL_ID,
            expected_authorization_id=AUTHORIZATION_ID,
            expected_attempt_id=ATTEMPT_ID,
        )["subject_result_id"]
        == fixture["subject_id"]
    )
    competing = _signed(
        "acfqp.campaign_measurement_subject_result.v180r12r3r1",
        "subject_result_id",
        domains.CONSTRUCTION_K7_CAMPAIGN_SUBJECT_RESULT_V180R12R3R1E_DOMAIN,
        protocol_id=PROTOCOL_ID,
        authorization_id=AUTHORIZATION_ID,
        attempt_id=ATTEMPT_ID,
        subject_byte_count=1,
    )
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="full worker document",
    ):
        ledger.validate_campaign_subject_result_document_v180r12r3r1(competing)
    spec = next(
        row
        for row in ledger.build_campaign_operation_schedule_v180r12r3r1(ATTEMPT_ID)
        if row.slot == "INPUT_READ"
    )
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="chunk sum",
    ):
        ledger.issue_campaign_io_transfer_receipt_v180r12r3r1(
            protocol_id=PROTOCOL_ID,
            authorization_id=AUTHORIZATION_ID,
            attempt_id=ATTEMPT_ID,
            operation_id=spec.operation_id,
            event_kind="INPUT_READ_OUTCOME",
            measured_value=10,
            returned_chunk_byte_counts=(4, 5),
            source_evidence_id=fixture["subject_id"],
            target_evidence_id=fixture["subject_id"],
        )


@pytest.mark.parametrize(
    "mutation",
    [
        ("INPUT_READ", "FROZEN_SOURCE", 0, "target", "verification_snapshot"),
        ("STAGE_WRITE", "SEALED_MEMFD", 0, "source", "verification_snapshot"),
        ("INPUT_READ", "SEALED_STAGE", 0, "source", "verification_stage"),
        ("SUBJECT_WRITE", "SUBJECT_RESULT", 0, "source", "replay_subject"),
        ("INPUT_READ", "SUBJECT_READBACK", 0, "target", "worker_birth"),
    ],
)
def test_exact_eight_io_transfer_graph_rejects_role_swaps_and_self_edges(
    mutation: tuple[str, str, int, str, str],
) -> None:
    fixture = _fixture(io_endpoint_mutation=mutation)
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="I/O transfer evidence graph",
    ):
        ledger.derive_campaign_measurement_ledger_v180r12r3r1(
            fixture["state"],
            subject_id=fixture["subject_id"],
            evidence_documents_by_id=fixture["docs"],
            expected_native_zero_source_manifest_id=fixture["source_manifest_id"],
            expected_native_zero_import_inventory_id=fixture["import_inventory_id"],
        )


@pytest.mark.parametrize("authority", ["operation", "source", "import"])
def test_semantic_receipts_directly_bind_all_three_registered_authorities(
    authority: str,
) -> None:
    fixture = _fixture(foreign_semantic_authority=authority)
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="semantic operation receipt",
    ):
        ledger.derive_campaign_measurement_ledger_v180r12r3r1(
            fixture["state"],
            subject_id=fixture["subject_id"],
            evidence_documents_by_id=fixture["docs"],
            expected_native_zero_source_manifest_id=fixture["source_manifest_id"],
            expected_native_zero_import_inventory_id=fixture["import_inventory_id"],
        )


def test_preregistered_native_zero_manifest_id_and_arithmetic_drift_are_rejected() -> None:
    fixture = _fixture()
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="source/import",
    ):
        ledger.derive_campaign_measurement_ledger_v180r12r3r1(
            fixture["state"],
            subject_id=fixture["subject_id"],
            evidence_documents_by_id=fixture["docs"],
            expected_native_zero_source_manifest_id=_cid("foreign-source-manifest"),
            expected_native_zero_import_inventory_id=fixture["import_inventory_id"],
        )
    drift = _fixture(frozen_terminal_read=199_754)
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="read/stage/output byte arithmetic",
    ):
        ledger.derive_campaign_measurement_ledger_v180r12r3r1(
            drift["state"],
            subject_id=drift["subject_id"],
            evidence_documents_by_id=drift["docs"],
            expected_native_zero_source_manifest_id=drift["source_manifest_id"],
            expected_native_zero_import_inventory_id=drift["import_inventory_id"],
        )
    over_cap = _fixture(memory_peak=ledger.MEMORY_MAX_BYTES + 1)
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="cgroup observation",
    ):
        ledger.derive_campaign_measurement_ledger_v180r12r3r1(
            over_cap["state"],
            subject_id=over_cap["subject_id"],
            evidence_documents_by_id=over_cap["docs"],
            expected_native_zero_source_manifest_id=over_cap["source_manifest_id"],
            expected_native_zero_import_inventory_id=over_cap["import_inventory_id"],
        )


def test_nonempty_auxiliary_boolean_measurement_and_noncanonical_bytes_fail_closed() -> None:
    spec = ledger.build_campaign_operation_schedule_v180r12r3r1(ATTEMPT_ID)[0]
    state = ledger.open_campaign_ledger_v180r12r3r1(
        protocol_id=PROTOCOL_ID,
        authorization_id=AUTHORIZATION_ID,
        attempt_id=ATTEMPT_ID,
        max_event_count=10,
        max_event_byte_count=65_536,
        max_ledger_byte_count=1_000_000,
    )
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="exact empty list",
    ):
        ledger.append_campaign_event_v180r12r3r1(
            state,
            phase=spec.phase,
            actor_role=spec.actor_role,
            operation_id=spec.operation_id,
            event_kind="ATTEMPT_OPEN",
            monotonic_ns=1,
            payload={
                "evidence_id": _cid("attempt-evidence"),
                "outcome_code": "OPEN",
                "measured_value": None,
                "auxiliary_values": [{"name": "x", "value": 1}],
            },
        )
    fixture, result = _artifact()
    event_bytes = json.dumps(result.state.events[0].to_document()).encode("utf-8")
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="canonical",
    ):
        ledger.CampaignLedgerEventV180R12R3R1.from_document(event_bytes)
    with pytest.raises(
        ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error,
        match="canonical",
    ):
        ledger.verify_campaign_measurement_ledger_v180r12r3r1(
            result.canonical_bytes + b"\n",
            expected_native_zero_source_manifest_id=fixture["source_manifest_id"],
            expected_native_zero_import_inventory_id=fixture["import_inventory_id"],
        )
