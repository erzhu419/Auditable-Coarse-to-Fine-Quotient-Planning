"""Observer-owned runtime state machine for V180r12r3r2 campaign measurement.

The module freezes the phase/role grammar, exact operation schedule, cgroup-v2
topology receipts, pidfd birth/reap receipts, event payload envelope, and typed
failure state.  It is intentionally an effect-free orchestration core: there
is no clone, exec, pidfd, memfd, cgroup, filesystem, clock, or commit syscall in
this file.  Production code must inject independently authorized effectors and
submit their receipts to this state machine with externally observed monotonic
timestamps.

The observer owns the append-only ledger for the whole attempt.  A freshly
created empty MEASUREMENT_ROOT has sibling SUPERVISOR and WORKER leaves so the
root may enable memory/pids controllers without violating cgroup-v2's
no-internal-process rule.  Its final memory.peak and pids.peak cover the full
STAGE through COMMIT window; neither value is inferred from a cap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import re
import stat
from types import MappingProxyType
from typing import Any, Callable, Mapping, NoReturn, Protocol, Sequence

from acfqp import construction_k7_campaign_measurement_ledger_v180r12r3r2 as ledger
from acfqp import construction_k7_domain_registry_extension_v180r12r3r2e as domains
from acfqp import construction_k7_campaign_measurement_worker_v180r12r3r2 as worker
from acfqp.phase3e_ids import canonical_json_bytes


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_campaign_measurement_supervisor_v180r12r3r2"

MEMORY_MAX_BYTES = 16 * 1024 * 1024 * 1024
PIDS_MAX = 2
WALL_TIMEOUT_SECONDS = 14_400
SUCCESSFUL_LEDGER_EVENT_COUNT = 625
MAX_EVENT_COUNT = 4_096
MAX_EVENT_BYTE_COUNT = 64 * 1024
MAX_LEDGER_BYTE_COUNT = 64 * 1024 * 1024

EVIDENCE_DOCUMENT_CONTRACT_ROWS = (
    (
        "CAMPAIGN_ATTEMPT_RECORD",
        "acfqp.campaign_attempt_record.v180r12r3r2",
        domains.CONSTRUCTION_K7_CAMPAIGN_ATTEMPT_RECORD_V180R12R3R2E_DOMAIN,
        "campaign_attempt_record_id",
    ),
    (
        "IO_TRANSFER_RECEIPT",
        "acfqp.campaign_io_transfer_receipt.v180r12r3r2",
        domains.CONSTRUCTION_K7_IO_TRANSFER_RECEIPT_V180R12R3R2E_DOMAIN,
        "io_transfer_receipt_id",
    ),
    (
        "PIDFD_BIRTH_RECEIPT",
        "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2",
        domains.CONSTRUCTION_K7_PIDFD_BIRTH_RECEIPT_V180R12R3R2E_DOMAIN,
        "pidfd_birth_receipt_id",
    ),
    (
        "PIDFD_REAP_RECEIPT",
        "acfqp.campaign_pidfd_reap_receipt.v180r12r3r2",
        domains.CONSTRUCTION_K7_PIDFD_REAP_RECEIPT_V180R12R3R2E_DOMAIN,
        "pidfd_reap_receipt_id",
    ),
    (
        "CGROUP_TOPOLOGY_RECEIPT",
        "acfqp.campaign_cgroup_topology_receipt.v180r12r3r2",
        domains.CONSTRUCTION_K7_CGROUP_TOPOLOGY_RECEIPT_V180R12R3R2E_DOMAIN,
        "cgroup_topology_receipt_id",
    ),
    (
        "CGROUP_OBSERVATION_RECEIPT",
        "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2",
        domains.CONSTRUCTION_K7_CGROUP_OBSERVATION_RECEIPT_V180R12R3R2E_DOMAIN,
        "cgroup_observation_receipt_id",
    ),
    (
        "SUBJECT_COMMIT_RECEIPT",
        "acfqp.campaign_subject_commit_receipt.v180r12r3r2",
        domains.CONSTRUCTION_K7_SUBJECT_COMMIT_RECEIPT_V180R12R3R2E_DOMAIN,
        "subject_commit_receipt_id",
    ),
    (
        "WINDOW_CLOSURE_RECEIPT",
        "acfqp.campaign_window_closure_receipt.v180r12r3r2",
        domains.CONSTRUCTION_K7_WINDOW_CLOSURE_RECEIPT_V180R12R3R2E_DOMAIN,
        "window_closure_receipt_id",
    ),
    (
        "CAMPAIGN_EXECUTION_CLOSURE",
        "acfqp.campaign_execution_closure.v180r12r3r2",
        domains.CONSTRUCTION_K7_CAMPAIGN_EXECUTION_CLOSURE_V180R12R3R2E_DOMAIN,
        "campaign_execution_closure_id",
    ),
    (
        "CAMPAIGN_OPERATION_MANIFEST",
        "acfqp.campaign_operation_manifest.v180r12r3r2",
        domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_MANIFEST_V180R12R3R2E_DOMAIN,
        "campaign_operation_manifest_id",
    ),
    (
        "NATIVE_ZERO_SOURCE_MANIFEST",
        "acfqp.campaign_native_zero_source_manifest.v180r12r3r2",
        domains.CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_MANIFEST_V180R12R3R2E_DOMAIN,
        "native_zero_source_manifest_id",
    ),
    (
        "NATIVE_ZERO_IMPORT_INVENTORY",
        "acfqp.campaign_native_zero_import_inventory.v180r12r3r2",
        domains.CONSTRUCTION_K7_NATIVE_ZERO_IMPORT_INVENTORY_V180R12R3R2E_DOMAIN,
        "native_zero_import_inventory_id",
    ),
)

EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS = (
    (
        "PIDFD_BIRTH_RECEIPT",
        "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2",
        "pidfd_birth_receipt_id",
        frozenset(
            {
                "schema", "schema_version", "cgroup_topology_receipt_id",
                "topology_receipt_id", "attempt_id", "operation_id",
                "process_role", "pid", "pidfd", "pidfd_device", "pidfd_inode",
                "clone3_flags", "target_cgroup_fd", "target_cgroup_device",
                "target_cgroup_inode", "target_cgroup_path",
                "proc_starttime_ticks", "pidfd_fdinfo_pid",
                "pidfd_fdinfo_nspid", "cgroup_membership_line",
                "membership_observed_before_work", "pidfd_cloexec",
                "pidfd_birth_receipt_id",
            }
        ),
    ),
    (
        "PIDFD_REAP_RECEIPT",
        "acfqp.campaign_pidfd_reap_receipt.v180r12r3r2",
        "pidfd_reap_receipt_id",
        frozenset(
            {
                "schema", "schema_version", "pidfd_birth_receipt_id",
                "process_birth_receipt_id", "attempt_id", "operation_id",
                "process_role", "pid", "pidfd_device", "pidfd_inode",
                "proc_starttime_ticks", "waitid_idtype", "waitid_pidfd",
                "waitid_code", "waitid_status", "pidfd_readable",
                "leaf_populated_after_reap", "leaf_process_count_after_reap",
                "pidfd_reap_receipt_id",
            }
        ),
    ),
    (
        "CGROUP_TOPOLOGY_RECEIPT",
        "acfqp.campaign_cgroup_topology_receipt.v180r12r3r2",
        "cgroup_topology_receipt_id",
        frozenset(
            {
                "schema", "schema_version", "cgroup_parent_fact",
                "cgroup_parent_fact_sha256", "delegated_parent",
                "measurement_root", "supervisor_leaf", "worker_leaf",
                "filesystem_type", "controllers", "subtree_control",
                "root_memory_max_bytes", "root_pids_max", "memory_max_bytes",
                "pids_max", "supervisor_leaf_pids_max", "worker_leaf_pids_max",
                "root_populated_before_birth", "root_process_count_before_birth",
                "leaf_process_counts_before_birth", "control_files",
                "no_internal_process_rule_satisfied", "sibling_leaf_topology",
                "cgroup_topology_receipt_id",
            }
        ),
    ),
    (
        "CGROUP_OBSERVATION_RECEIPT",
        "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2",
        "cgroup_observation_receipt_id",
        frozenset(
            {
                "schema", "schema_version", "cgroup_topology_receipt_id",
                "topology_receipt_id", "supervisor_reap_receipt_id",
                "worker_reap_receipt_id", "attempt_id", "operation_id",
                "memory_peak_bytes", "pids_peak", "memory_events",
                "pids_events", "populated_by_role", "process_count_by_role",
                "root_populated", "root_process_count",
                "supervisor_leaf_process_count", "worker_leaf_process_count",
                "control_file_readbacks", "observed_after_window_close",
                "memory_peak_is_observed_not_authorization_cap",
                "pids_peak_is_observed_not_authorization_cap",
                "cgroup_observation_receipt_id",
            }
        ),
    ),
)

RUNTIME_EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS = (
    *worker.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS,
    *EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS,
)

_EVIDENCE_CONTRACT_BY_SCHEMA = {
    schema: (evidence_type, domain, identity_field)
    for evidence_type, schema, domain, identity_field in (
        *worker.EVIDENCE_DOCUMENT_CONTRACT_ROWS,
        *EVIDENCE_DOCUMENT_CONTRACT_ROWS,
    )
}
_DIRECT_EVENT_EVIDENCE_SCHEMA = {
    "ATTEMPT_OPEN": "acfqp.campaign_attempt_record.v180r12r3r2",
    "INPUT_READ_OUTCOME": "acfqp.campaign_io_transfer_receipt.v180r12r3r2",
    "STAGE_WRITE_OUTCOME": "acfqp.campaign_io_transfer_receipt.v180r12r3r2",
    "MOUNT_VISIBILITY_OPEN": "acfqp.campaign_fd_visibility_receipt.v180r12r3r2",
    "MOUNT_VISIBILITY_CLOSE": "acfqp.campaign_fd_visibility_receipt.v180r12r3r2",
    "SEMANTIC_HASH_OUTCOME": "acfqp.campaign_semantic_operation_receipt.v180r12r3r2",
    "INTEGRITY_CHECK_OUTCOME": "acfqp.campaign_semantic_operation_receipt.v180r12r3r2",
    "PROTOCOL_CHECK_OUTCOME": "acfqp.campaign_semantic_operation_receipt.v180r12r3r2",
    "PROCESS_BIRTH_OUTCOME": "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2",
    "PROCESS_REAP": "acfqp.campaign_pidfd_reap_receipt.v180r12r3r2",
    "SUBJECT_WRITE_OUTCOME": "acfqp.campaign_io_transfer_receipt.v180r12r3r2",
    "SUBJECT_COMMIT": "acfqp.campaign_subject_commit_receipt.v180r12r3r2",
    "WINDOW_CLOSED": "acfqp.campaign_window_closure_receipt.v180r12r3r2",
    "CGROUP_OBSERVED": "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2",
}

PHASE_ORDER = (
    "ATTEMPT",
    "STAGE",
    "WORKER",
    "COMMIT",
    "WINDOW_CLOSE",
    "OS_OBSERVE",
    "LEDGER_CLOSE",
)
ACTOR_ROLES = ("OBSERVER", "SUPERVISOR", "WORKER")

EVENT_KIND_ROLE_PHASES: Mapping[str, tuple[tuple[str, str], ...]] = {
    "ATTEMPT_OPEN": (("OBSERVER", "ATTEMPT"),),
    "INPUT_READ_INTENT": (
        ("SUPERVISOR", "STAGE"),
        ("WORKER", "WORKER"),
        ("SUPERVISOR", "COMMIT"),
    ),
    "INPUT_READ_OUTCOME": (
        ("SUPERVISOR", "STAGE"),
        ("WORKER", "WORKER"),
        ("SUPERVISOR", "COMMIT"),
    ),
    "STAGE_WRITE_INTENT": (("SUPERVISOR", "STAGE"),),
    "STAGE_WRITE_OUTCOME": (("SUPERVISOR", "STAGE"),),
    "MOUNT_VISIBILITY_OPEN": (("SUPERVISOR", "STAGE"),),
    "MOUNT_VISIBILITY_CLOSE": (("SUPERVISOR", "WINDOW_CLOSE"),),
    "SEMANTIC_HASH_INTENT": (
        ("SUPERVISOR", "STAGE"),
        ("WORKER", "WORKER"),
        ("SUPERVISOR", "COMMIT"),
    ),
    "SEMANTIC_HASH_OUTCOME": (
        ("SUPERVISOR", "STAGE"),
        ("WORKER", "WORKER"),
        ("SUPERVISOR", "COMMIT"),
    ),
    "INTEGRITY_CHECK_INTENT": (
        ("SUPERVISOR", "STAGE"),
        ("WORKER", "WORKER"),
        ("SUPERVISOR", "COMMIT"),
    ),
    "INTEGRITY_CHECK_OUTCOME": (
        ("SUPERVISOR", "STAGE"),
        ("WORKER", "WORKER"),
        ("SUPERVISOR", "COMMIT"),
    ),
    "PROTOCOL_CHECK_INTENT": (("WORKER", "WORKER"),),
    "PROTOCOL_CHECK_OUTCOME": (("WORKER", "WORKER"),),
    "PROCESS_BIRTH_INTENT": (
        ("OBSERVER", "STAGE"),
        ("SUPERVISOR", "WORKER"),
    ),
    "PROCESS_BIRTH_OUTCOME": (
        ("OBSERVER", "STAGE"),
        ("SUPERVISOR", "WORKER"),
    ),
    "PROCESS_REAP": (
        ("SUPERVISOR", "WORKER"),
        ("OBSERVER", "OS_OBSERVE"),
    ),
    "SUBJECT_WRITE_INTENT": (("WORKER", "WORKER"),),
    "SUBJECT_WRITE_OUTCOME": (("WORKER", "WORKER"),),
    "SUBJECT_COMMIT": (("SUPERVISOR", "COMMIT"),),
    "WINDOW_CLOSED": (("SUPERVISOR", "WINDOW_CLOSE"),),
    "CGROUP_OBSERVED": (("OBSERVER", "OS_OBSERVE"),),
    "LEDGER_CLOSED": (("OBSERVER", "LEDGER_CLOSE"),),
}

EXPECTED_OUTCOME_CODE = {
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

COUNTER_EVENT_KINDS = frozenset(
    {
        "INPUT_READ_OUTCOME",
        "STAGE_WRITE_OUTCOME",
        "MOUNT_VISIBILITY_OPEN",
        "SEMANTIC_HASH_OUTCOME",
        "INTEGRITY_CHECK_OUTCOME",
        "PROTOCOL_CHECK_OUTCOME",
        "PROCESS_BIRTH_OUTCOME",
        "SUBJECT_WRITE_OUTCOME",
        "CGROUP_OBSERVED",
    }
)
UNIT_COUNTER_EVENT_KINDS = frozenset(
    {
        "SEMANTIC_HASH_OUTCOME",
        "INTEGRITY_CHECK_OUTCOME",
        "PROTOCOL_CHECK_OUTCOME",
        "PROCESS_BIRTH_OUTCOME",
    }
)

EVIDENCE_REQUIRED_EVENT_KINDS = frozenset(
    {
        "ATTEMPT_OPEN",
        "INPUT_READ_OUTCOME",
        "STAGE_WRITE_OUTCOME",
        "MOUNT_VISIBILITY_OPEN",
        "MOUNT_VISIBILITY_CLOSE",
        "SEMANTIC_HASH_OUTCOME",
        "INTEGRITY_CHECK_OUTCOME",
        "PROTOCOL_CHECK_OUTCOME",
        "PROCESS_BIRTH_OUTCOME",
        "PROCESS_REAP",
        "SUBJECT_WRITE_OUTCOME",
        "SUBJECT_COMMIT",
        "WINDOW_CLOSED",
        "CGROUP_OBSERVED",
    }
)

EVENT_KIND_SLOT = {
    "ATTEMPT_OPEN": "ATTEMPT",
    "INPUT_READ_INTENT": "INPUT_READ",
    "INPUT_READ_OUTCOME": "INPUT_READ",
    "STAGE_WRITE_INTENT": "STAGE_WRITE",
    "STAGE_WRITE_OUTCOME": "STAGE_WRITE",
    "MOUNT_VISIBILITY_OPEN": "MOUNT",
    "MOUNT_VISIBILITY_CLOSE": "MOUNT",
    "SEMANTIC_HASH_INTENT": "SEMANTIC_HASH",
    "SEMANTIC_HASH_OUTCOME": "SEMANTIC_HASH",
    "INTEGRITY_CHECK_INTENT": "INTEGRITY_CHECK",
    "INTEGRITY_CHECK_OUTCOME": "INTEGRITY_CHECK",
    "PROTOCOL_CHECK_INTENT": "PROTOCOL_CHECK",
    "PROTOCOL_CHECK_OUTCOME": "PROTOCOL_CHECK",
    "PROCESS_BIRTH_INTENT": "PROCESS",
    "PROCESS_BIRTH_OUTCOME": "PROCESS",
    "PROCESS_REAP": "PROCESS",
    "SUBJECT_WRITE_INTENT": "SUBJECT_WRITE",
    "SUBJECT_WRITE_OUTCOME": "SUBJECT_WRITE",
    "SUBJECT_COMMIT": "SUBJECT_COMMIT",
    "WINDOW_CLOSED": "WINDOW",
    "CGROUP_OBSERVED": "CGROUP",
    "LEDGER_CLOSED": "LEDGER",
}

INTENT_OUTCOME_PAIRS = {
    "INPUT_READ_INTENT": "INPUT_READ_OUTCOME",
    "STAGE_WRITE_INTENT": "STAGE_WRITE_OUTCOME",
    "SEMANTIC_HASH_INTENT": "SEMANTIC_HASH_OUTCOME",
    "INTEGRITY_CHECK_INTENT": "INTEGRITY_CHECK_OUTCOME",
    "PROTOCOL_CHECK_INTENT": "PROTOCOL_CHECK_OUTCOME",
    "PROCESS_BIRTH_INTENT": "PROCESS_BIRTH_OUTCOME",
    "SUBJECT_WRITE_INTENT": "SUBJECT_WRITE_OUTCOME",
}
OUTCOME_INTENT = {outcome: intent for intent, outcome in INTENT_OUTCOME_PAIRS.items()}

HASH_OPERATION_FAMILIES = (
    ("SOURCE_SHA256", 2, "STAGE", "SUPERVISOR"),
    ("STAGED_SHA256", 2, "WORKER", "WORKER"),
    ("TOP_CONTENT_ID", 2, "WORKER", "WORKER"),
    ("INNER_CONTENT_ID", 129, "WORKER", "WORKER"),
    ("SUBJECT_CONTENT_ID", 1, "WORKER", "WORKER"),
    ("SUBJECT_READBACK_SHA256", 1, "COMMIT", "SUPERVISOR"),
)
INTEGRITY_OPERATION_FAMILIES = (
    ("STAGE_STABLE_INPUT", 2, "STAGE", "SUPERVISOR"),
    ("STAGE_SHA_MATCH", 2, "STAGE", "SUPERVISOR"),
    ("STAGE_SEAL_SET", 2, "STAGE", "SUPERVISOR"),
    ("WORKER_STAGED_SHA", 2, "WORKER", "WORKER"),
    ("WORKER_CANONICAL_JSON", 2, "WORKER", "WORKER"),
    ("WORKER_TOP_ID_MATCH", 2, "WORKER", "WORKER"),
    ("WORKER_INNER_ID_MATCH", 129, "WORKER", "WORKER"),
    ("WORKER_INNER_COUNT_AND_UNIQUENESS", 1, "WORKER", "WORKER"),
    ("WORKER_SUBJECT_CANONICAL_AND_ID", 1, "WORKER", "WORKER"),
    ("COMMIT_READBACK_SIZE_AND_SHA", 1, "COMMIT", "SUPERVISOR"),
    ("COMMIT_STABLE_MODE_AND_NLINK", 1, "COMMIT", "SUPERVISOR"),
)
PROTOCOL_OPERATION_FAMILIES = tuple(
    (family, 1, "WORKER", "WORKER")
    for family in worker.PROTOCOL_CHECK_FAMILIES
)

IO_TRANSFER_GRAPH_ROWS = (
    (
        "INPUT_READ", "FROZEN_SOURCE", 0, "INPUT_READ_OUTCOME",
        "CAMPAIGN_OPERATION_MANIFEST", "TERMINAL_STABLE_INPUT_SNAPSHOT",
    ),
    (
        "INPUT_READ", "FROZEN_SOURCE", 1, "INPUT_READ_OUTCOME",
        "CAMPAIGN_OPERATION_MANIFEST", "VERIFICATION_STABLE_INPUT_SNAPSHOT",
    ),
    (
        "STAGE_WRITE", "SEALED_MEMFD", 0, "STAGE_WRITE_OUTCOME",
        "TERMINAL_STABLE_INPUT_SNAPSHOT", "TERMINAL_MEMFD_STAGE",
    ),
    (
        "STAGE_WRITE", "SEALED_MEMFD", 1, "STAGE_WRITE_OUTCOME",
        "VERIFICATION_STABLE_INPUT_SNAPSHOT", "VERIFICATION_MEMFD_STAGE",
    ),
    (
        "INPUT_READ", "SEALED_STAGE", 0, "INPUT_READ_OUTCOME",
        "TERMINAL_MEMFD_STAGE", "WORKER_PIDFD_BIRTH",
    ),
    (
        "INPUT_READ", "SEALED_STAGE", 1, "INPUT_READ_OUTCOME",
        "VERIFICATION_MEMFD_STAGE", "WORKER_PIDFD_BIRTH",
    ),
    (
        "SUBJECT_WRITE", "SUBJECT_RESULT", 0, "SUBJECT_WRITE_OUTCOME",
        "CAMPAIGN_SUBJECT_RESULT", "WORKER_PIDFD_BIRTH",
    ),
    (
        "INPUT_READ", "SUBJECT_READBACK", 0, "INPUT_READ_OUTCOME",
        "CAMPAIGN_SUBJECT_RESULT", "SUPERVISOR_PIDFD_BIRTH",
    ),
)

_CID = re.compile(r"^[0-9a-f]{64}$")
_AUX_NAME = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
_TOKEN = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_FAILURE_MESSAGE_BYTE_CAP = 4_096
_FAILURE_ARTIFACT_ROW_CAP = 4_112
_FAILURE_ARTIFACT_METADATA_BYTE_CAP = 2 * 1024 * 1024
_FAILURE_DIRECTORY_ENTRY_CAP = 4_096
_FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP = 256 * 1024
_FAILURE_ARTIFACT_STREAM_HASH_BYTE_CAP = MAX_LEDGER_BYTE_COUNT + MAX_EVENT_BYTE_COUNT
FAILURE_ARTIFACT_OBSERVATION_BOUNDARY = "IMMEDIATELY_BEFORE_FAILURE_WRITE"
FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS = tuple(
    sorted(
        (
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement_attempt.json", "FILE"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement", "DIRECTORY"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement/EVENTS", "DIRECTORY"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement_failure.json", "FILE"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement/SUBJECT_RESULT.json.partial", "FILE"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement/SUBJECT_RESULT.json", "FILE"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement/EVIDENCE_INVENTORY.json", "FILE"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement/EXECUTION_CLOSURE.json", "FILE"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement/OS_RECEIPT.json", "FILE"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement/LEDGER_CLOSURE.json", "FILE"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement/TERMINAL.json", "FILE"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement_cas", "DIRECTORY"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement_verification.json", "FILE"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement_verification_failure.json", "FILE"),
            (".tmp/exact-freeze/v180r12r3r2_campaign_measurement_verification_replay.json", "FILE"),
        )
    )
)
FAILURE_ARTIFACT_OBSERVATION_KEYS = frozenset(
    {
        "relative_path", "kind", "state", "mode", "nlink", "byte_count",
        "sha256", "directory_entries", "read_error_type", "read_error_message",
    }
)
FAILURE_CGROUP_OBSERVATION_KEYS = frozenset(
    {
        "root_populated", "supervisor_leaf_populated", "worker_leaf_populated",
        "root_process_count", "supervisor_leaf_process_count",
        "worker_leaf_process_count", "memory_peak_bytes", "pids_peak",
        "memory_events", "pids_events", "kill_outcome", "reap_outcome",
        "close_outcome", "observation_errors", "node_observations",
    }
)
FAILURE_CGROUP_NODE_OBSERVATION_KEYS = frozenset(
    {
        "role", "path", "state", "mode", "nlink", "device", "inode",
        "populated", "process_count", "read_error_type",
        "read_error_message",
    }
)
FAILURE_STATE_FIELD_KEYS = frozenset(
    {
        "schema", "schema_version", "protocol_id", "authorization_id",
        "attempt_id", "failure_code", "phase", "operation_id", "last_event_id",
        "completed_event_count", "message", "message_sha256",
        "process_may_remain", "output_may_exist", "partial_artifact_observations",
        "partial_artifact_observation_boundary",
        "cgroup_failure_observation", "same_identity_rerun_forbidden",
        "successful_ledger_claimed", "counter_records_issued", "failure_state_id",
    }
)


class ConstructionK7CampaignMeasurementSupervisorV180R12R3R2Error(ValueError):
    """The runtime lifecycle, OS receipt, or ledger adapter failed closed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CampaignMeasurementSupervisorV180R12R3R2Error(message)


def _cid(value: Any, label: str) -> str:
    if type(value) is not str or _CID.fullmatch(value) is None:
        _fail(f"{label} must be one lowercase SHA-256 content ID")
    return value


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        _fail(f"{label} must be one canonical identifier")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _positive(value: Any, label: str) -> int:
    value = _nonnegative(value, label)
    if value == 0:
        _fail(f"{label} must be positive")
    return value


def _identity(domain: str, payload: Mapping[str, Any]) -> str:
    return domains.extension_content_id_v180r12r3r2e(domain, dict(payload))


def _canonical_evidence_document(value: Any) -> tuple[str, str, dict[str, Any]]:
    to_document = getattr(value, "to_document", None)
    if callable(to_document):
        value = to_document()
    if type(value) is not dict:
        _fail("campaign evidence must be one typed canonical document")
    document = dict(value)
    schema = document.get("schema")
    descriptor = _EVIDENCE_CONTRACT_BY_SCHEMA.get(schema)
    if descriptor is None:
        _fail("campaign evidence schema is outside the exact 18-type inventory")
    _evidence_type, domain, identity_field = descriptor
    identity = _cid(document.get(identity_field), "campaign evidence identity")
    payload = dict(document)
    payload.pop(identity_field)
    if _identity(domain, payload) != identity:
        _fail("campaign evidence identity failed canonical domain replay")
    if canonical_json_bytes(document) != canonical_json_bytes(value):
        _fail("campaign evidence document is not canonically stable")
    return identity, schema, document


def _operation_identity(
    attempt_id: str, slot: str, family: str, ordinal: int
) -> str:
    _cid(attempt_id, "operation attempt ID")
    if (
        type(slot) is not str
        or _TOKEN.fullmatch(slot) is None
        or type(family) is not str
        or _TOKEN.fullmatch(family) is None
    ):
        _fail("operation slot or family is malformed")
    _nonnegative(ordinal, "operation ordinal")
    return _identity(
        domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_V180R12R3R2E_DOMAIN,
        {
            "schema": "acfqp.campaign_operation_identity.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            "attempt_id": attempt_id,
            "slot": slot,
            "family": family,
            "ordinal": ordinal,
        },
    )


class CampaignPhaseV180R12R3R2(str, Enum):
    ATTEMPT = "ATTEMPT"
    STAGE = "STAGE"
    WORKER = "WORKER"
    COMMIT = "COMMIT"
    WINDOW_CLOSE = "WINDOW_CLOSE"
    OS_OBSERVE = "OS_OBSERVE"
    LEDGER_CLOSE = "LEDGER_CLOSE"


class CampaignActorRoleV180R12R3R2(str, Enum):
    OBSERVER = "OBSERVER"
    SUPERVISOR = "SUPERVISOR"
    WORKER = "WORKER"


class ProcessRoleV180R12R3R2(str, Enum):
    SUPERVISOR = "SUPERVISOR"
    WORKER = "WORKER"


class FailureCodeV180R12R3R2(str, Enum):
    INPUT_DRIFT = "INPUT_DRIFT"
    STAGE_FAILURE = "STAGE_FAILURE"
    MEMFD_SEAL_FAILURE = "MEMFD_SEAL_FAILURE"
    FD_VISIBILITY_FAILURE = "FD_VISIBILITY_FAILURE"
    SUPERVISOR_BIRTH_FAILURE = "SUPERVISOR_BIRTH_FAILURE"
    WORKER_BIRTH_FAILURE = "WORKER_BIRTH_FAILURE"
    WORKER_REPLAY_FAILURE = "WORKER_REPLAY_FAILURE"
    PROCESS_REAP_FAILURE = "PROCESS_REAP_FAILURE"
    SUBJECT_WRITE_FAILURE = "SUBJECT_WRITE_FAILURE"
    SUBJECT_COMMIT_FAILURE = "SUBJECT_COMMIT_FAILURE"
    WINDOW_CLOSE_FAILURE = "WINDOW_CLOSE_FAILURE"
    CGROUP_OBSERVATION_FAILURE = "CGROUP_OBSERVATION_FAILURE"
    LEDGER_FAILURE = "LEDGER_FAILURE"
    CAP_VIOLATION = "CAP_VIOLATION"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"


@dataclass(frozen=True, slots=True)
class FailureArtifactObservationV180R12R3R2:
    """Bounded read-only observation of one path at terminal failure."""

    relative_path: str
    kind: str
    state: str
    mode: int | None
    nlink: int | None
    byte_count: int | None
    sha256: str | None
    directory_entries: tuple[str, ...] | None
    read_error_type: str | None
    read_error_message: str | None

    def __post_init__(self) -> None:
        path = self.relative_path
        if (
            type(path) is not str
            or not path
            or path.startswith("/")
            or "//" in path
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or self.kind not in {"FILE", "DIRECTORY"}
            or self.state
            not in {"ABSENT", "PRESENT", "LINKED_OR_NONREGULAR", "READ_ERROR"}
        ):
            _fail("failure artifact path/kind/state is malformed")
        for value, label in (
            (self.mode, "failure artifact mode"),
            (self.nlink, "failure artifact nlink"),
            (self.byte_count, "failure artifact byte count"),
        ):
            if value is not None:
                _nonnegative(value, label)
        if self.sha256 is not None:
            _cid(self.sha256, "failure artifact SHA-256")
        if self.directory_entries is not None:
            if (
                type(self.directory_entries) is not tuple
                or len(self.directory_entries) > _FAILURE_DIRECTORY_ENTRY_CAP
                or self.directory_entries
                != tuple(sorted(set(self.directory_entries)))
                or any(
                    type(name) is not str
                    or not name
                    or "/" in name
                    or name in {".", ".."}
                    or len(name.encode("utf-8")) > 255
                    for name in self.directory_entries
                )
                or sum(len(name.encode("utf-8")) for name in self.directory_entries)
                > _FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP
            ):
                _fail("failure directory entry observation exceeds its cap")
        for value, label in (
            (self.read_error_type, "failure read error type"),
            (self.read_error_message, "failure read error message"),
        ):
            if value is not None and (
                type(value) is not str
                or not value
                or len(value.encode("utf-8")) > 512
            ):
                _fail(f"{label} is malformed")
        absent = self.state == "ABSENT"
        present = self.state == "PRESENT"
        failed = self.state == "READ_ERROR"
        if absent and any(
            value is not None
            for value in (
                self.mode, self.nlink, self.byte_count, self.sha256,
                self.directory_entries, self.read_error_type,
                self.read_error_message,
            )
        ):
            _fail("absent failure artifact carries invented metadata")
        if present:
            if (
                self.mode is None
                or self.nlink is None
                or self.read_error_type is not None
                or self.read_error_message is not None
            ):
                _fail("present failure artifact lacks exact metadata")
            if self.kind == "FILE" and (
                not stat.S_ISREG(self.mode)
                or self.byte_count is None
                or self.sha256 is None
                or self.directory_entries is not None
            ):
                _fail("present failure file lacks its streaming digest")
            if self.kind == "DIRECTORY" and (
                not stat.S_ISDIR(self.mode)
                or self.byte_count is not None
                or self.sha256 is not None
                or self.directory_entries is None
            ):
                _fail("present failure directory lacks its bounded entries")
        if failed and (
            self.read_error_type is None
            or self.read_error_message is None
            or self.sha256 is not None
            or self.directory_entries is not None
        ):
            _fail("failure artifact read error is incomplete")
        if self.state == "LINKED_OR_NONREGULAR" and (
            self.mode is None
            or self.nlink is None
            or self.sha256 is not None
            or self.directory_entries is not None
            or self.read_error_type is not None
            or self.read_error_message is not None
        ):
            _fail("linked/nonregular failure artifact observation is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "kind": self.kind,
            "state": self.state,
            "mode": self.mode,
            "nlink": self.nlink,
            "byte_count": self.byte_count,
            "sha256": self.sha256,
            "directory_entries": (
                None
                if self.directory_entries is None
                else list(self.directory_entries)
            ),
            "read_error_type": self.read_error_type,
            "read_error_message": self.read_error_message,
        }


@dataclass(frozen=True, slots=True)
class FailureCgroupNodeObservationV180R12R3R2:
    """Bounded final state of one attempted measurement cgroup directory."""

    role: str
    path: str | None
    state: str
    mode: int | None
    nlink: int | None
    device: int | None
    inode: int | None
    populated: int | None
    process_count: int | None
    read_error_type: str | None
    read_error_message: str | None

    def __post_init__(self) -> None:
        if (
            self.role not in {"MEASUREMENT_ROOT", "SUPERVISOR", "WORKER"}
            or self.state
            not in {"ABSENT", "PRESENT", "LINKED_OR_NONDIR", "READ_ERROR"}
        ):
            _fail("failure cgroup node role/state is malformed")
        if self.path is not None and (
            type(self.path) is not str
            or not self.path.startswith("/")
            or self.path != "/" and self.path.endswith("/")
            or "//" in self.path
            or any(part in {"", ".", ".."} for part in self.path.split("/")[1:])
        ):
            _fail("failure cgroup node path is noncanonical")
        for value in (
            self.mode, self.nlink, self.device, self.inode, self.process_count,
        ):
            if value is not None:
                _nonnegative(value, "failure cgroup node metadata")
        if self.populated is not None and self.populated not in {0, 1}:
            _fail("failure cgroup node populated state is malformed")
        for value in (self.read_error_type, self.read_error_message):
            if value is not None and (
                type(value) is not str
                or not value
                or len(value.encode("utf-8")) > 512
            ):
                _fail("failure cgroup node read error exceeds its cap")
        metadata = (self.mode, self.nlink, self.device, self.inode)
        if self.state == "ABSENT" and (
            self.path is None
            or any(value is not None for value in metadata)
            or self.populated is not None
            or self.process_count is not None
            or self.read_error_type is not None
            or self.read_error_message is not None
        ):
            _fail("absent failure cgroup node carries invented facts")
        if self.state == "PRESENT" and (
            self.path is None
            or any(value is None for value in metadata)
            or not stat.S_ISDIR(self.mode)
            or self.populated not in {0, 1}
            or self.process_count is None
            or self.read_error_type is not None
            or self.read_error_message is not None
        ):
            _fail("present failure cgroup node lacks exact directory facts")
        if self.state == "LINKED_OR_NONDIR" and (
            self.path is None
            or any(value is None for value in metadata)
            or self.populated is not None
            or self.process_count is not None
            or self.read_error_type is not None
            or self.read_error_message is not None
        ):
            _fail("linked/non-directory failure cgroup node is malformed")
        if self.state == "READ_ERROR" and (
            self.read_error_type is None or self.read_error_message is None
        ):
            _fail("failure cgroup node read error is incomplete")

    def to_document(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "path": self.path,
            "state": self.state,
            "mode": self.mode,
            "nlink": self.nlink,
            "device": self.device,
            "inode": self.inode,
            "populated": self.populated,
            "process_count": self.process_count,
            "read_error_type": self.read_error_type,
            "read_error_message": self.read_error_message,
        }


@dataclass(frozen=True, slots=True)
class FailureCgroupObservationV180R12R3R2:
    """Non-success, best-effort observation of an owned cgroup tree."""

    root_populated: int | None
    supervisor_leaf_populated: int | None
    worker_leaf_populated: int | None
    root_process_count: int | None
    supervisor_leaf_process_count: int | None
    worker_leaf_process_count: int | None
    memory_peak_bytes: int | None
    pids_peak: int | None
    memory_events: tuple[tuple[str, int], ...] | None
    pids_events: tuple[tuple[str, int], ...] | None
    kill_outcome: str
    reap_outcome: str
    close_outcome: str
    observation_errors: tuple[str, ...]
    node_observations: tuple[FailureCgroupNodeObservationV180R12R3R2, ...]

    def __post_init__(self) -> None:
        for value in (
            self.root_populated, self.supervisor_leaf_populated,
            self.worker_leaf_populated,
        ):
            if value is not None and value not in {0, 1}:
                _fail("failure cgroup populated value is malformed")
        for value in (
            self.root_process_count, self.supervisor_leaf_process_count,
            self.worker_leaf_process_count, self.memory_peak_bytes,
            self.pids_peak,
        ):
            if value is not None:
                _nonnegative(value, "failure cgroup counter")
        for rows in (self.memory_events, self.pids_events):
            if rows is not None and (
                type(rows) is not tuple
                or rows != tuple(sorted(rows))
                or len({name for name, _value in rows}) != len(rows)
                or any(
                    type(name) is not str
                    or not name
                    or type(value) is not int
                    or value < 0
                    for name, value in rows
                )
            ):
                _fail("failure cgroup event counters are malformed")
        for value in (self.kill_outcome, self.reap_outcome, self.close_outcome):
            if (
                type(value) is not str
                or not value
                or len(value.encode("utf-8")) > 512
            ):
                _fail("failure cgroup cleanup outcome is malformed")
        if (
            type(self.observation_errors) is not tuple
            or len(self.observation_errors) > 32
            or any(
                type(value) is not str
                or not value
                or len(value.encode("utf-8")) > 512
                for value in self.observation_errors
            )
        ):
            _fail("failure cgroup observation errors exceed their cap")
        if (
            type(self.node_observations) is not tuple
            or tuple(row.role for row in self.node_observations)
            != ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER")
            or any(
                type(row) is not FailureCgroupNodeObservationV180R12R3R2
                for row in self.node_observations
            )
        ):
            _fail("failure cgroup observation requires its exact three nodes")
        root, supervisor, worker = self.node_observations
        if root.path is not None and any(
            row.path is not None
            and row.path != root.path + "/" + row.role
            for row in (supervisor, worker)
        ):
            _fail("failure cgroup leaf paths crossed their measurement root")

    def to_document(self) -> dict[str, Any]:
        def rows(value: tuple[tuple[str, int], ...] | None):
            return (
                None
                if value is None
                else [{"name": name, "value": count} for name, count in value]
            )

        return {
            "root_populated": self.root_populated,
            "supervisor_leaf_populated": self.supervisor_leaf_populated,
            "worker_leaf_populated": self.worker_leaf_populated,
            "root_process_count": self.root_process_count,
            "supervisor_leaf_process_count": self.supervisor_leaf_process_count,
            "worker_leaf_process_count": self.worker_leaf_process_count,
            "memory_peak_bytes": self.memory_peak_bytes,
            "pids_peak": self.pids_peak,
            "memory_events": rows(self.memory_events),
            "pids_events": rows(self.pids_events),
            "kill_outcome": self.kill_outcome,
            "reap_outcome": self.reap_outcome,
            "close_outcome": self.close_outcome,
            "observation_errors": list(self.observation_errors),
            "node_observations": [
                row.to_document() for row in self.node_observations
            ],
        }


@dataclass(frozen=True, slots=True)
class CgroupNodeIdentityV180R12R3R2:
    role: str
    path: str
    parent_path: str | None
    membership_path: str
    parent_membership_path: str | None
    directory_fd: int
    device: int
    inode: int
    mode: int
    link_count: int
    cloexec: bool
    symlink_free_resolution: bool

    def __post_init__(self) -> None:
        if type(self.role) is not str or _TOKEN.fullmatch(self.role) is None:
            _fail("cgroup node role is malformed")
        paths = (self.path, self.membership_path)
        parents = (self.parent_path, self.parent_membership_path)
        if any(
            type(path) is not str
            or not path.startswith("/")
            or (path != "/" and path.endswith("/"))
            or "//" in path
            or (
                path != "/"
                and any(part in {"", ".", ".."} for part in path.split("/")[1:])
            )
            for path in paths
        ) or any(
            parent is not None
            and (
                type(parent) is not str
                or not parent.startswith("/")
                or (parent != "/" and parent.endswith("/"))
                or "//" in parent
                or (
                    parent != "/"
                    and any(
                        part in {"", ".", ".."}
                        for part in parent.split("/")[1:]
                    )
                )
            )
            for parent in parents
        ):
            _fail("cgroup node path or parent path is malformed")
        _nonnegative(self.directory_fd, "cgroup directory FD")
        _positive(self.device, "cgroup device")
        _positive(self.inode, "cgroup inode")
        _positive(self.mode, "cgroup directory mode")
        _positive(self.link_count, "cgroup directory link count")
        if (
            stat.S_IFMT(self.mode) != stat.S_IFDIR
            or self.cloexec is not True
            or self.symlink_free_resolution is not True
        ):
            _fail("cgroup node is not one CLOEXEC directory descriptor")

    def to_document(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "path": self.path,
            "parent_path": self.parent_path,
            "membership_path": self.membership_path,
            "parent_membership_path": self.parent_membership_path,
            "directory_fd": self.directory_fd,
            "device": self.device,
            "inode": self.inode,
            "mode": self.mode,
            "link_count": self.link_count,
            "cloexec": self.cloexec,
            "symlink_free_resolution": self.symlink_free_resolution,
        }


@dataclass(frozen=True, slots=True)
class CgroupControlFileOFDV180R12R3R2:
    node_role: str
    name: str
    fd: int
    device: int
    inode: int
    mode: int
    link_count: int
    cloexec: bool
    opened_before_supervisor_birth: bool
    retained_through_os_observe: bool
    control_file_fact_id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.node_role not in {"MEASUREMENT_ROOT", "SUPERVISOR", "WORKER"}:
            _fail("cgroup control-file node role changed")
        allowed_names = {
            "cgroup.events",
            "cgroup.procs",
            "memory.events",
            "memory.max",
            "memory.peak",
            "pids.events",
            "pids.max",
            "pids.peak",
        }
        if self.name not in allowed_names:
            _fail("cgroup control-file name is outside the frozen inventory")
        _nonnegative(self.fd, "cgroup control-file FD")
        _positive(self.device, "cgroup control-file device")
        _positive(self.inode, "cgroup control-file inode")
        _positive(self.mode, "cgroup control-file mode")
        _positive(self.link_count, "cgroup control-file link count")
        if (
            stat.S_IFMT(self.mode) != stat.S_IFREG
            or self.cloexec is not True
            or self.opened_before_supervisor_birth is not True
            or self.retained_through_os_observe is not True
        ):
            _fail("cgroup control file is not one retained CLOEXEC regular-file OFD")
        object.__setattr__(
            self,
            "control_file_fact_id",
            _identity(
                domains.CONSTRUCTION_K7_CGROUP_TOPOLOGY_RECEIPT_V180R12R3R2E_DOMAIN,
                self._identity_payload(),
            ),
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_cgroup_control_file_ofd.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            **self._payload(),
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "node_role": self.node_role,
            "name": self.name,
            "fd": self.fd,
            "device": self.device,
            "inode": self.inode,
            "mode": self.mode,
            "link_count": self.link_count,
            "cloexec": self.cloexec,
            "opened_before_supervisor_birth": self.opened_before_supervisor_birth,
            "retained_through_os_observe": self.retained_through_os_observe,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._identity_payload(),
            "control_file_fact_id": self.control_file_fact_id,
        }


_REQUIRED_CGROUP_CONTROL_FILES = (
    ("MEASUREMENT_ROOT", "cgroup.events"),
    ("MEASUREMENT_ROOT", "cgroup.procs"),
    ("MEASUREMENT_ROOT", "memory.events"),
    ("MEASUREMENT_ROOT", "memory.max"),
    ("MEASUREMENT_ROOT", "memory.peak"),
    ("MEASUREMENT_ROOT", "pids.events"),
    ("MEASUREMENT_ROOT", "pids.max"),
    ("MEASUREMENT_ROOT", "pids.peak"),
    ("SUPERVISOR", "cgroup.events"),
    ("SUPERVISOR", "cgroup.procs"),
    ("SUPERVISOR", "pids.max"),
    ("WORKER", "cgroup.events"),
    ("WORKER", "cgroup.procs"),
    ("WORKER", "pids.max"),
)


@dataclass(frozen=True, slots=True)
class MeasurementCgroupTopologyReceiptV180R12R3R2:
    cgroup_parent_fact: Mapping[str, Any] = field(repr=False, compare=False)
    delegated_parent: CgroupNodeIdentityV180R12R3R2
    measurement_root: CgroupNodeIdentityV180R12R3R2
    supervisor_leaf: CgroupNodeIdentityV180R12R3R2
    worker_leaf: CgroupNodeIdentityV180R12R3R2
    filesystem_type: str
    controllers: tuple[str, ...]
    subtree_control: tuple[str, ...]
    root_memory_max_bytes: int
    root_pids_max: int
    supervisor_leaf_pids_max: int
    worker_leaf_pids_max: int
    root_populated_before_birth: bool
    root_process_count_before_birth: int
    leaf_process_counts_before_birth: tuple[int, int]
    control_files: tuple[CgroupControlFileOFDV180R12R3R2, ...]
    cgroup_topology_receipt_id: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.cgroup_parent_fact) is not dict:
            _fail("cgroup parent fact must be one canonical mapping")
        parent_fact = dict(self.cgroup_parent_fact)
        if canonical_json_bytes(parent_fact) != canonical_json_bytes(
            self.cgroup_parent_fact
        ):
            _fail("cgroup parent fact is not canonical")
        object.__setattr__(self, "cgroup_parent_fact", MappingProxyType(parent_fact))
        nodes = (
            self.delegated_parent,
            self.measurement_root,
            self.supervisor_leaf,
            self.worker_leaf,
        )
        if any(type(node) is not CgroupNodeIdentityV180R12R3R2 for node in nodes):
            _fail("cgroup topology node is mistyped")
        identities = {(node.device, node.inode) for node in nodes}
        if len(identities) != len(nodes):
            _fail("cgroup topology nodes must be inode-distinct")
        if (
            self.filesystem_type != "cgroup2"
            or self.controllers != ("memory", "pids")
            or self.subtree_control != ("memory", "pids")
            or self.root_memory_max_bytes != MEMORY_MAX_BYTES
            or self.root_pids_max != PIDS_MAX
            or self.supervisor_leaf_pids_max != 1
            or self.worker_leaf_pids_max != 1
            or self.root_populated_before_birth is not False
            or self.root_process_count_before_birth != 0
            or self.leaf_process_counts_before_birth != (0, 0)
            or self.measurement_root.role != "MEASUREMENT_ROOT"
            or self.supervisor_leaf.role != "SUPERVISOR"
            or self.worker_leaf.role != "WORKER"
            or len({node.device for node in nodes}) != 1
            or parent_fact.get("schema") != "acfqp.v180r12r3r2_cgroup_parent_fact.v1"
            or parent_fact.get("mount_fstype") != "cgroup2"
            or parent_fact.get("parent_path") != self.delegated_parent.path
            or parent_fact.get("parent_device") != self.delegated_parent.device
            or parent_fact.get("parent_inode") != self.delegated_parent.inode
            or parent_fact.get("mode") != stat.S_IMODE(self.delegated_parent.mode)
            or parent_fact.get("controllers") != ["memory", "pids"]
            or parent_fact.get("subtree_control") != ["memory", "pids"]
            or self.measurement_root.parent_path != self.delegated_parent.path
            or self.measurement_root.parent_membership_path
            != self.delegated_parent.membership_path
            or self.supervisor_leaf.parent_path != self.measurement_root.path
            or self.supervisor_leaf.parent_membership_path
            != self.measurement_root.membership_path
            or self.worker_leaf.parent_path != self.measurement_root.path
            or self.worker_leaf.parent_membership_path
            != self.measurement_root.membership_path
            or self.measurement_root.path.rsplit("/", 1)[0]
            != self.delegated_parent.path
            or self.supervisor_leaf.path.rsplit("/", 1)[0]
            != self.measurement_root.path
            or self.worker_leaf.path.rsplit("/", 1)[0]
            != self.measurement_root.path
            or self.measurement_root.membership_path.rsplit("/", 1)[0]
            != self.delegated_parent.membership_path.rstrip("/")
            or self.supervisor_leaf.membership_path.rsplit("/", 1)[0]
            != self.measurement_root.membership_path
            or self.worker_leaf.membership_path.rsplit("/", 1)[0]
            != self.measurement_root.membership_path
            or self.measurement_root.path
            in {self.supervisor_leaf.path, self.worker_leaf.path}
            or self.supervisor_leaf.path == self.worker_leaf.path
        ):
            _fail("cgroup-v2 sibling-leaf topology or limits changed")
        if (
            type(self.control_files) is not tuple
            or any(type(row) is not CgroupControlFileOFDV180R12R3R2 for row in self.control_files)
            or tuple((row.node_role, row.name) for row in self.control_files)
            != _REQUIRED_CGROUP_CONTROL_FILES
            or len({row.fd for row in self.control_files}) != len(self.control_files)
            or len({(row.device, row.inode) for row in self.control_files})
            != len(self.control_files)
        ):
            _fail("cgroup retained control-file OFD inventory changed")
        node_by_role = {
            "MEASUREMENT_ROOT": self.measurement_root,
            "SUPERVISOR": self.supervisor_leaf,
            "WORKER": self.worker_leaf,
        }
        if any(row.device != node_by_role[row.node_role].device for row in self.control_files):
            _fail("cgroup control file crossed its cgroup filesystem device")
        object.__setattr__(
            self,
            "cgroup_topology_receipt_id",
            _identity(
                domains.CONSTRUCTION_K7_CGROUP_TOPOLOGY_RECEIPT_V180R12R3R2E_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_cgroup_topology_receipt.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            "cgroup_parent_fact": dict(self.cgroup_parent_fact),
            "cgroup_parent_fact_sha256": hashlib.sha256(
                canonical_json_bytes(dict(self.cgroup_parent_fact))
            ).hexdigest(),
            "delegated_parent": self.delegated_parent.to_document(),
            "measurement_root": self.measurement_root.to_document(),
            "supervisor_leaf": self.supervisor_leaf.to_document(),
            "worker_leaf": self.worker_leaf.to_document(),
            "filesystem_type": self.filesystem_type,
            "controllers": list(self.controllers),
            "subtree_control": list(self.subtree_control),
            "root_memory_max_bytes": self.root_memory_max_bytes,
            "root_pids_max": self.root_pids_max,
            "memory_max_bytes": self.root_memory_max_bytes,
            "pids_max": self.root_pids_max,
            "supervisor_leaf_pids_max": self.supervisor_leaf_pids_max,
            "worker_leaf_pids_max": self.worker_leaf_pids_max,
            "root_populated_before_birth": self.root_populated_before_birth,
            "root_process_count_before_birth": self.root_process_count_before_birth,
            "leaf_process_counts_before_birth": list(
                self.leaf_process_counts_before_birth
            ),
            "control_files": [row.to_document() for row in self.control_files],
            "no_internal_process_rule_satisfied": True,
            "sibling_leaf_topology": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "cgroup_topology_receipt_id": self.cgroup_topology_receipt_id,
        }

    @property
    def topology_receipt_id(self) -> str:
        return self.cgroup_topology_receipt_id


@dataclass(frozen=True, slots=True)
class PidfdBirthReceiptV180R12R3R2:
    topology_receipt: MeasurementCgroupTopologyReceiptV180R12R3R2 = field(repr=False)
    attempt_id: str
    operation_id: str
    process_role: ProcessRoleV180R12R3R2
    pid: int
    pidfd: int
    pidfd_device: int
    pidfd_inode: int
    clone3_flags: tuple[str, ...]
    target_cgroup_fd: int
    target_cgroup_device: int
    target_cgroup_inode: int
    target_cgroup_path: str
    proc_starttime_ticks: int
    pidfd_fdinfo_pid: int
    pidfd_fdinfo_nspid: tuple[int, ...]
    cgroup_membership_line: str
    membership_observed_before_work: bool
    pidfd_cloexec: bool
    pidfd_birth_receipt_id: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.topology_receipt) is not MeasurementCgroupTopologyReceiptV180R12R3R2:
            _fail("pidfd birth topology receipt is mistyped")
        _cid(self.attempt_id, "birth attempt ID")
        _cid(self.operation_id, "birth operation ID")
        if type(self.process_role) is not ProcessRoleV180R12R3R2:
            _fail("process birth role is mistyped")
        for value, label in (
            (self.pid, "birth PID"),
            (self.pidfd, "birth pidfd"),
            (self.pidfd_device, "birth pidfd device"),
            (self.pidfd_inode, "birth pidfd inode"),
            (self.target_cgroup_fd, "birth cgroup FD"),
            (self.target_cgroup_device, "birth cgroup device"),
            (self.target_cgroup_inode, "birth cgroup inode"),
            (self.proc_starttime_ticks, "birth /proc starttime"),
            (self.pidfd_fdinfo_pid, "birth pidfd fdinfo PID"),
        ):
            _positive(value, label)
        target = (
            self.topology_receipt.supervisor_leaf
            if self.process_role is ProcessRoleV180R12R3R2.SUPERVISOR
            else self.topology_receipt.worker_leaf
        )
        expected_operation_id = _operation_identity(
            self.attempt_id, "PROCESS", self.process_role.value, 0
        )
        if not (
            self.operation_id == expected_operation_id
            and self.clone3_flags == ("CLONE_INTO_CGROUP", "CLONE_PIDFD")
            and self.target_cgroup_fd == target.directory_fd
            and self.target_cgroup_device == target.device
            and self.target_cgroup_inode == target.inode
            and self.target_cgroup_path == target.path
            and self.pidfd_fdinfo_pid == self.pid
            and type(self.pidfd_fdinfo_nspid) is tuple
            and bool(self.pidfd_fdinfo_nspid)
            and self.pidfd_fdinfo_nspid[0] == self.pid
            and all(type(value) is int and value > 0 for value in self.pidfd_fdinfo_nspid)
            and self.cgroup_membership_line == f"0::{target.membership_path}"
            and self.membership_observed_before_work is True
            and self.pidfd_cloexec is True
        ):
            _fail("pidfd birth lacks exact clone3/cgroup/starttime/fdinfo binding")
        object.__setattr__(
            self,
            "pidfd_birth_receipt_id",
            _identity(
                domains.CONSTRUCTION_K7_PIDFD_BIRTH_RECEIPT_V180R12R3R2E_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            "cgroup_topology_receipt_id": self.topology_receipt.cgroup_topology_receipt_id,
            "topology_receipt_id": self.topology_receipt.cgroup_topology_receipt_id,
            "attempt_id": self.attempt_id,
            "operation_id": self.operation_id,
            "process_role": self.process_role.value,
            "pid": self.pid,
            "pidfd": self.pidfd,
            "pidfd_device": self.pidfd_device,
            "pidfd_inode": self.pidfd_inode,
            "clone3_flags": list(self.clone3_flags),
            "target_cgroup_fd": self.target_cgroup_fd,
            "target_cgroup_device": self.target_cgroup_device,
            "target_cgroup_inode": self.target_cgroup_inode,
            "target_cgroup_path": self.target_cgroup_path,
            "proc_starttime_ticks": self.proc_starttime_ticks,
            "pidfd_fdinfo_pid": self.pidfd_fdinfo_pid,
            "pidfd_fdinfo_nspid": list(self.pidfd_fdinfo_nspid),
            "cgroup_membership_line": self.cgroup_membership_line,
            "membership_observed_before_work": self.membership_observed_before_work,
            "pidfd_cloexec": self.pidfd_cloexec,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "pidfd_birth_receipt_id": self.pidfd_birth_receipt_id,
        }

    @property
    def process_birth_receipt_id(self) -> str:
        return self.pidfd_birth_receipt_id


@dataclass(frozen=True, slots=True)
class PidfdReapReceiptV180R12R3R2:
    birth_receipt: PidfdBirthReceiptV180R12R3R2 = field(repr=False)
    operation_id: str
    pidfd_device: int
    pidfd_inode: int
    proc_starttime_ticks: int
    waitid_idtype: str
    waitid_pidfd: int
    waitid_code: str
    waitid_status: int
    pidfd_readable: bool
    leaf_populated_after_reap: bool
    leaf_process_count_after_reap: int
    pidfd_reap_receipt_id: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.birth_receipt) is not PidfdBirthReceiptV180R12R3R2:
            _fail("pidfd reap birth receipt is mistyped")
        _cid(self.operation_id, "reap operation ID")
        for value, label in (
            (self.pidfd_device, "reap pidfd device"),
            (self.pidfd_inode, "reap pidfd inode"),
            (self.proc_starttime_ticks, "reap /proc starttime"),
            (self.waitid_pidfd, "reap waitid pidfd"),
        ):
            _positive(value, label)
        if (
            self.operation_id != self.birth_receipt.operation_id
            or self.pidfd_device != self.birth_receipt.pidfd_device
            or self.pidfd_inode != self.birth_receipt.pidfd_inode
            or self.proc_starttime_ticks != self.birth_receipt.proc_starttime_ticks
            or self.waitid_idtype != "P_PIDFD"
            or self.waitid_pidfd != self.birth_receipt.pidfd
            or self.waitid_code != "CLD_EXITED"
            or self.waitid_status != 0
            or self.pidfd_readable is not True
            or self.leaf_populated_after_reap is not False
            or self.leaf_process_count_after_reap != 0
        ):
            _fail("pidfd reap did not prove terminal empty-leaf state")
        object.__setattr__(
            self,
            "pidfd_reap_receipt_id",
            _identity(
                domains.CONSTRUCTION_K7_PIDFD_REAP_RECEIPT_V180R12R3R2E_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_pidfd_reap_receipt.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            "pidfd_birth_receipt_id": self.birth_receipt.pidfd_birth_receipt_id,
            "process_birth_receipt_id": self.birth_receipt.pidfd_birth_receipt_id,
            "attempt_id": self.birth_receipt.attempt_id,
            "operation_id": self.operation_id,
            "process_role": self.birth_receipt.process_role.value,
            "pid": self.birth_receipt.pid,
            "pidfd_device": self.pidfd_device,
            "pidfd_inode": self.pidfd_inode,
            "proc_starttime_ticks": self.proc_starttime_ticks,
            "waitid_idtype": self.waitid_idtype,
            "waitid_pidfd": self.waitid_pidfd,
            "waitid_code": self.waitid_code,
            "waitid_status": self.waitid_status,
            "pidfd_readable": self.pidfd_readable,
            "leaf_populated_after_reap": self.leaf_populated_after_reap,
            "leaf_process_count_after_reap": self.leaf_process_count_after_reap,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "pidfd_reap_receipt_id": self.pidfd_reap_receipt_id,
        }

    @property
    def process_reap_receipt_id(self) -> str:
        return self.pidfd_reap_receipt_id


@dataclass(frozen=True, slots=True)
class CgroupControlFileReadbackV180R12R3R2:
    control_file: CgroupControlFileOFDV180R12R3R2
    raw_value: str
    same_open_file_description: bool
    read_after_both_reaps: bool
    read_before_cgroup_remove: bool

    def __post_init__(self) -> None:
        if (
            type(self.control_file) is not CgroupControlFileOFDV180R12R3R2
            or type(self.raw_value) is not str
            or (not self.raw_value and self.control_file.name != "cgroup.procs")
            or self.same_open_file_description is not True
            or self.read_after_both_reaps is not True
            or self.read_before_cgroup_remove is not True
        ):
            _fail("cgroup control-file readback did not preserve its retained OFD")

    def to_document(self) -> dict[str, Any]:
        return {
            "control_file_fact_id": self.control_file.control_file_fact_id,
            "node_role": self.control_file.node_role,
            "name": self.control_file.name,
            "fd": self.control_file.fd,
            "device": self.control_file.device,
            "inode": self.control_file.inode,
            "mode": self.control_file.mode,
            "link_count": self.control_file.link_count,
            "raw_value": self.raw_value,
            "same_open_file_description": self.same_open_file_description,
            "read_after_both_reaps": self.read_after_both_reaps,
            "read_before_cgroup_remove": self.read_before_cgroup_remove,
        }


@dataclass(frozen=True, slots=True)
class CgroupV2ObservationReceiptV180R12R3R2:
    topology_receipt: MeasurementCgroupTopologyReceiptV180R12R3R2 = field(repr=False)
    supervisor_reap_receipt: PidfdReapReceiptV180R12R3R2 = field(repr=False)
    worker_reap_receipt: PidfdReapReceiptV180R12R3R2 = field(repr=False)
    operation_id: str
    memory_peak_bytes: int
    pids_peak: int
    memory_events: tuple[tuple[str, int], ...]
    pids_events: tuple[tuple[str, int], ...]
    populated_by_role: tuple[tuple[str, int], ...]
    process_count_by_role: tuple[tuple[str, int], ...]
    control_file_readbacks: tuple[CgroupControlFileReadbackV180R12R3R2, ...]
    observed_after_window_close: bool
    cgroup_observation_receipt_id: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.topology_receipt) is not MeasurementCgroupTopologyReceiptV180R12R3R2
            or type(self.supervisor_reap_receipt) is not PidfdReapReceiptV180R12R3R2
            or type(self.worker_reap_receipt) is not PidfdReapReceiptV180R12R3R2
            or self.supervisor_reap_receipt.birth_receipt.process_role
            is not ProcessRoleV180R12R3R2.SUPERVISOR
            or self.worker_reap_receipt.birth_receipt.process_role
            is not ProcessRoleV180R12R3R2.WORKER
        ):
            _fail("cgroup observation process/topology joins changed")
        _cid(self.operation_id, "cgroup observation operation ID")
        expected_operation_id = _operation_identity(
            self.supervisor_reap_receipt.birth_receipt.attempt_id,
            "CGROUP", "FINAL_OBSERVE", 0,
        )
        _positive(self.memory_peak_bytes, "memory.peak observation")
        if (
            self.operation_id != expected_operation_id
            or self.memory_peak_bytes > MEMORY_MAX_BYTES
            or self.pids_peak != 2
            or self.memory_events
            != (("high", 0), ("low", 0), ("max", 0), ("oom", 0),
                ("oom_group_kill", 0), ("oom_kill", 0))
            or self.pids_events != (("max", 0),)
            or self.populated_by_role
            != (("MEASUREMENT_ROOT", 0), ("SUPERVISOR", 0), ("WORKER", 0))
            or self.process_count_by_role
            != (("MEASUREMENT_ROOT", 0), ("SUPERVISOR", 0), ("WORKER", 0))
            or self.observed_after_window_close is not True
        ):
            _fail("final cgroup-v2 observation is nonempty, early, or over cap")
        if (
            type(self.control_file_readbacks) is not tuple
            or tuple(row.control_file for row in self.control_file_readbacks)
            != self.topology_receipt.control_files
            or any(type(row) is not CgroupControlFileReadbackV180R12R3R2 for row in self.control_file_readbacks)
        ):
            _fail("final cgroup observation did not read every retained OFD once")
        raw_by_key = {
            (row.control_file.node_role, row.control_file.name): row.raw_value
            for row in self.control_file_readbacks
        }

        def parse_counter_file(raw: str, label: str) -> tuple[tuple[str, int], ...]:
            parsed: list[tuple[str, int]] = []
            for line in raw.splitlines():
                parts = line.split(" ")
                if len(parts) != 2 or not parts[0] or not parts[1].isdigit():
                    _fail(f"{label} raw counter line is malformed")
                parsed.append((parts[0], int(parts[1])))
            result = tuple(sorted(parsed))
            if len(result) != len(set(name for name, _value in result)):
                _fail(f"{label} raw counter names repeat")
            return result

        if (
            parse_counter_file(
                raw_by_key[("MEASUREMENT_ROOT", "memory.events")],
                "memory.events",
            )
            != self.memory_events
            or parse_counter_file(
                raw_by_key[("MEASUREMENT_ROOT", "pids.events")],
                "pids.events",
            )
            != self.pids_events
            or raw_by_key[("MEASUREMENT_ROOT", "memory.max")]
            != f"{MEMORY_MAX_BYTES}\n"
            or raw_by_key[("MEASUREMENT_ROOT", "pids.max")] != "2\n"
            or raw_by_key[("SUPERVISOR", "pids.max")] != "1\n"
            or raw_by_key[("WORKER", "pids.max")] != "1\n"
            or raw_by_key[("MEASUREMENT_ROOT", "memory.peak")]
            != f"{self.memory_peak_bytes}\n"
            or raw_by_key[("MEASUREMENT_ROOT", "pids.peak")] != "2\n"
            or any(
                raw_by_key[(role, "cgroup.procs")] != ""
                for role in ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER")
            )
            or any(
                parse_counter_file(raw_by_key[(role, "cgroup.events")], "cgroup.events")
                != (("frozen", 0), ("populated", 0))
                for role in ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER")
            )
        ):
            _fail("cgroup raw control-file readbacks contradict observed values")
        object.__setattr__(
            self,
            "cgroup_observation_receipt_id",
            _identity(
                domains.CONSTRUCTION_K7_CGROUP_OBSERVATION_RECEIPT_V180R12R3R2E_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            "cgroup_topology_receipt_id": self.topology_receipt.cgroup_topology_receipt_id,
            "topology_receipt_id": self.topology_receipt.cgroup_topology_receipt_id,
            "supervisor_reap_receipt_id": self.supervisor_reap_receipt.pidfd_reap_receipt_id,
            "worker_reap_receipt_id": self.worker_reap_receipt.pidfd_reap_receipt_id,
            "attempt_id": self.supervisor_reap_receipt.birth_receipt.attempt_id,
            "operation_id": self.operation_id,
            "memory_peak_bytes": self.memory_peak_bytes,
            "pids_peak": self.pids_peak,
            "memory_events": [
                {"name": name, "value": value} for name, value in self.memory_events
            ],
            "pids_events": [
                {"name": name, "value": value} for name, value in self.pids_events
            ],
            "populated_by_role": [
                {"role": role, "value": value} for role, value in self.populated_by_role
            ],
            "process_count_by_role": [
                {"role": role, "value": value}
                for role, value in self.process_count_by_role
            ],
            "root_populated": False,
            "root_process_count": 0,
            "supervisor_leaf_process_count": 0,
            "worker_leaf_process_count": 0,
            "control_file_readbacks": [
                row.to_document() for row in self.control_file_readbacks
            ],
            "observed_after_window_close": self.observed_after_window_close,
            "memory_peak_is_observed_not_authorization_cap": True,
            "pids_peak_is_observed_not_authorization_cap": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "cgroup_observation_receipt_id": self.cgroup_observation_receipt_id,
        }


@dataclass(frozen=True, slots=True)
class CampaignFailureStateV180R12R3R2:
    protocol_id: str
    authorization_id: str
    attempt_id: str
    failure_code: FailureCodeV180R12R3R2
    phase: CampaignPhaseV180R12R3R2
    operation_id: str | None
    last_event_id: str | None
    completed_event_count: int
    message: str
    process_may_remain: bool
    output_may_exist: bool
    partial_artifact_observations: tuple[
        FailureArtifactObservationV180R12R3R2, ...
    ]
    cgroup_failure_observation: FailureCgroupObservationV180R12R3R2 | None
    same_identity_rerun_forbidden: bool = True
    failure_state_id: str = field(init=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.protocol_id, "failure protocol ID"),
            (self.authorization_id, "failure authorization ID"),
            (self.attempt_id, "failure attempt ID"),
        ):
            _cid(value, label)
        if type(self.failure_code) is not FailureCodeV180R12R3R2:
            _fail("failure code is mistyped")
        if type(self.phase) is not CampaignPhaseV180R12R3R2:
            _fail("failure phase is mistyped")
        if self.operation_id is not None:
            _identifier(self.operation_id, "failure operation ID")
        if self.last_event_id is not None:
            _cid(self.last_event_id, "failure last event ID")
        _nonnegative(self.completed_event_count, "completed event count")
        if (
            type(self.message) is not str
            or not self.message
            or len(self.message.encode("utf-8")) > _FAILURE_MESSAGE_BYTE_CAP
            or type(self.process_may_remain) is not bool
            or type(self.output_may_exist) is not bool
            or self.same_identity_rerun_forbidden is not True
        ):
            _fail("typed failure state is malformed or rerunnable")
        if (
            type(self.partial_artifact_observations) is not tuple
            or not self.partial_artifact_observations
            or len(self.partial_artifact_observations) > _FAILURE_ARTIFACT_ROW_CAP
            or any(
                type(row) is not FailureArtifactObservationV180R12R3R2
                for row in self.partial_artifact_observations
            )
            or tuple(row.relative_path for row in self.partial_artifact_observations)
            != tuple(
                sorted(
                    set(
                        row.relative_path
                        for row in self.partial_artifact_observations
                    )
                )
            )
            or self.cgroup_failure_observation is not None
            and type(self.cgroup_failure_observation)
            is not FailureCgroupObservationV180R12R3R2
        ):
            _fail("failure artifact/cgroup observation closure is malformed")
        observations_by_path = {
            row.relative_path: row for row in self.partial_artifact_observations
        }
        if any(
            observations_by_path.get(path) is None
            or observations_by_path[path].kind != kind
            for path, kind in FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS
        ):
            _fail("failure artifact closure lacks its exact fixed path inventory")
        events_path = ".tmp/exact-freeze/v180r12r3r2_campaign_measurement/EVENTS"
        events_row = observations_by_path[events_path]
        expected_event_paths = (
            set()
            if events_row.state != "PRESENT"
            else {f"{events_path}/{name}" for name in events_row.directory_entries or ()}
        )
        fixed_paths = {path for path, _kind in FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS}
        actual_event_paths = set(observations_by_path).difference(fixed_paths)
        if (
            actual_event_paths != expected_event_paths
            or any(observations_by_path[path].kind != "FILE" for path in actual_event_paths)
        ):
            _fail("failure artifact closure does not cover every exact EVENTS entry")
        nested_raw = canonical_json_bytes(
            {
                "partial_artifact_observations": [
                    row.to_document() for row in self.partial_artifact_observations
                ],
                "cgroup_failure_observation": (
                    None
                    if self.cgroup_failure_observation is None
                    else self.cgroup_failure_observation.to_document()
                ),
            }
        )
        if len(nested_raw) > _FAILURE_ARTIFACT_METADATA_BYTE_CAP:
            _fail("failure observation metadata exceeds its exact 2MiB cap")
        object.__setattr__(
            self,
            "failure_state_id",
            _identity(
                domains.CONSTRUCTION_K7_FAILURE_STATE_RECEIPT_V180R12R3R2E_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_failure_state.v180r12r3r2",
            "schema_version": SCHEMA_VERSION,
            "protocol_id": self.protocol_id,
            "authorization_id": self.authorization_id,
            "attempt_id": self.attempt_id,
            "failure_code": self.failure_code.value,
            "phase": self.phase.value,
            "operation_id": self.operation_id,
            "last_event_id": self.last_event_id,
            "completed_event_count": self.completed_event_count,
            "message": self.message,
            "message_sha256": hashlib.sha256(self.message.encode("utf-8")).hexdigest(),
            "process_may_remain": self.process_may_remain,
            "output_may_exist": self.output_may_exist,
            "partial_artifact_observation_boundary": (
                FAILURE_ARTIFACT_OBSERVATION_BOUNDARY
            ),
            "partial_artifact_observations": [
                row.to_document() for row in self.partial_artifact_observations
            ],
            "cgroup_failure_observation": (
                None
                if self.cgroup_failure_observation is None
                else self.cgroup_failure_observation.to_document()
            ),
            "same_identity_rerun_forbidden": self.same_identity_rerun_forbidden,
            "successful_ledger_claimed": False,
            "counter_records_issued": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "failure_state_id": self.failure_state_id}


def _auxiliary_document(
    values: Sequence[tuple[str, str | int | bool | None]],
) -> list[dict[str, Any]]:
    if type(values) not in {tuple, list}:
        _fail("auxiliary values must be one exact sequence")
    names: list[str] = []
    rows: list[dict[str, Any]] = []
    for item in values:
        if type(item) is not tuple or len(item) != 2:
            _fail("auxiliary value must be one exact pair")
        name, value = item
        if type(name) is not str or _AUX_NAME.fullmatch(name) is None:
            _fail("auxiliary value name is malformed")
        if value is not None and type(value) not in {str, int, bool}:
            _fail("auxiliary value must be one canonical scalar")
        if type(value) is int and value < 0:
            _fail("auxiliary integer cannot be negative")
        names.append(name)
        rows.append({"name": name, "value": value})
    if names != sorted(set(names)):
        _fail("auxiliary values must be name-sorted and unique")
    return rows


def campaign_event_payload_v180r12r3r2(
    *,
    event_kind: str,
    evidence_id: str | None,
    measured_value: int | None,
    auxiliary_values: Sequence[tuple[str, str | int | bool | None]],
) -> dict[str, Any]:
    """Build the only accepted four-field successful-event envelope."""

    if event_kind not in EXPECTED_OUTCOME_CODE:
        _fail("campaign event kind is unknown")
    if event_kind in EVIDENCE_REQUIRED_EVENT_KINDS:
        _cid(evidence_id, "required event evidence ID")
    elif evidence_id is not None:
        _fail("intent or ledger-close event cannot carry evidence")
    if event_kind in COUNTER_EVENT_KINDS:
        if evidence_id is None:
            _fail("counter event requires an evidence ID")
        _nonnegative(measured_value, "event measured value")
        if event_kind in UNIT_COUNTER_EVENT_KINDS and measured_value != 1:
            _fail("unit counter event must measure exactly one")
    elif measured_value is not None:
        _fail("non-counter event cannot carry a measured value")
    if type(auxiliary_values) not in {tuple, list} or len(auxiliary_values) != 0:
        _fail("campaign successful event auxiliary_values must be exactly empty")
    return {
        "evidence_id": evidence_id,
        "outcome_code": EXPECTED_OUTCOME_CODE[event_kind],
        "measured_value": measured_value,
        "auxiliary_values": [],
    }


@dataclass(frozen=True, slots=True)
class CampaignOperationPlanV180R12R3R2:
    operation_id: str
    slot: str
    family: str
    ordinal: int
    phase: str
    actor_role: str

    def __post_init__(self) -> None:
        _identifier(self.operation_id, "planned operation ID")
        if (
            type(self.slot) is not str
            or _TOKEN.fullmatch(self.slot) is None
            or type(self.family) is not str
            or _IDENTIFIER.fullmatch(self.family) is None
            or type(self.ordinal) is not int
            or self.ordinal < 0
            or self.phase not in PHASE_ORDER
            or self.actor_role not in ACTOR_ROLES
        ):
            _fail("campaign operation plan is malformed")


@dataclass(frozen=True, slots=True)
class CampaignSuccessEventPlanV180R12R3R2:
    phase: str
    actor_role: str
    operation_id: str
    event_kind: str

    def __post_init__(self) -> None:
        _cid(self.operation_id, "planned event operation ID")
        if (
            self.event_kind not in EVENT_KIND_ROLE_PHASES
            or (self.actor_role, self.phase)
            not in EVENT_KIND_ROLE_PHASES[self.event_kind]
        ):
            _fail("planned event role/phase signature changed")


def build_campaign_operation_schedule_v180r12r3r2(
    attempt_id: str,
) -> tuple[CampaignOperationPlanV180R12R3R2, ...]:
    """Consume the kernel's sole exact 314-operation authority."""

    authority = ledger.build_campaign_operation_schedule_v180r12r3r2(attempt_id)
    result = tuple(
        CampaignOperationPlanV180R12R3R2(
            row.operation_id,
            row.slot,
            row.family,
            row.ordinal,
            row.phase,
            row.actor_role,
        )
        for row in authority
    )
    if len(result) != 314 or len({row.operation_id for row in result}) != len(result):
        _fail("kernel campaign operation authority changed")
    return result


def build_campaign_success_event_plan_v180r12r3r2(
    attempt_id: str,
) -> tuple[CampaignSuccessEventPlanV180R12R3R2, ...]:
    """Consume the kernel's sole expanded 625-position event authority."""

    authority = ledger.build_campaign_success_event_schedule_v180r12r3r2(attempt_id)
    result = tuple(
        CampaignSuccessEventPlanV180R12R3R2(
            row.phase,
            row.actor_role,
            row.operation_id,
            row.event_kind,
        )
        for row in authority
    )
    if len(result) != SUCCESSFUL_LEDGER_EVENT_COUNT:
        _fail("kernel expanded campaign success authority changed")
    return result


def _one_registered_evidence_v180r12r3r2(
    documents_by_id: Mapping[str, Mapping[str, Any]],
    schema: str,
    *,
    field_name: str | None = None,
    field_value: Any = None,
) -> tuple[str, Mapping[str, Any]]:
    matches = tuple(
        (identity, document)
        for identity, document in documents_by_id.items()
        if isinstance(document, Mapping)
        and document.get("schema") == schema
        and (field_name is None or document.get(field_name) == field_value)
    )
    if len(matches) != 1:
        _fail("I/O graph endpoint is absent, repeated, or role-crossed")
    identity, document = matches[0]
    contract = _EVIDENCE_CONTRACT_BY_SCHEMA.get(schema)
    if contract is None or document.get(contract[2]) != identity:
        _fail("I/O graph endpoint does not bind its canonical evidence identity")
    return identity, document


def validate_campaign_io_transfer_edge_v180r12r3r2(
    *,
    plan: CampaignOperationPlanV180R12R3R2,
    event_kind: str,
    measured_value: int | None,
    receipt_document: Mapping[str, Any],
    evidence_documents_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str]:
    """Validate one of the eight exact acyclic measured-transfer edges."""

    if type(plan) is not CampaignOperationPlanV180R12R3R2:
        _fail("I/O graph operation plan is mistyped")
    expected_event_kind = {
        "INPUT_READ": "INPUT_READ_OUTCOME",
        "STAGE_WRITE": "STAGE_WRITE_OUTCOME",
        "SUBJECT_WRITE": "SUBJECT_WRITE_OUTCOME",
    }.get(plan.slot)
    graph_rows = tuple(
        row
        for row in IO_TRANSFER_GRAPH_ROWS
        if row[:3] == (plan.slot, plan.family, plan.ordinal)
    )
    if (
        expected_event_kind != event_kind
        or len(graph_rows) != 1
        or graph_rows[0][3] != event_kind
    ):
        _fail("I/O graph event kind crossed its exact operation slot")
    if not isinstance(receipt_document, Mapping) or receipt_document.get(
        "schema"
    ) != "acfqp.campaign_io_transfer_receipt.v180r12r3r2":
        _fail("I/O graph receipt type changed")
    chunks = receipt_document.get("returned_chunk_byte_counts")
    if (
        receipt_document.get("operation_id") != plan.operation_id
        or receipt_document.get("event_kind") != event_kind
        or receipt_document.get("measured_value") != measured_value
        or type(chunks) is not list
        or not chunks
        or any(type(value) is not int or value <= 0 for value in chunks)
        or sum(chunks) != measured_value
        or receipt_document.get("returned_chunk_count") != len(chunks)
        or receipt_document.get("returned_byte_count") != measured_value
        or receipt_document.get("transfer_complete") is not True
    ):
        _fail("I/O graph receipt does not bind exact returned syscall chunks")
    source_id = _cid(
        receipt_document.get("source_evidence_id"), "I/O graph source evidence ID"
    )
    target_id = _cid(
        receipt_document.get("target_evidence_id"), "I/O graph target evidence ID"
    )
    if (
        source_id == target_id
        or source_id not in evidence_documents_by_id
        or target_id not in evidence_documents_by_id
        or receipt_document.get("transfer_identity")
        != {
            "operation_id": plan.operation_id,
            "event_kind": event_kind,
            "source_evidence_id": source_id,
            "target_evidence_id": target_id,
        }
    ):
        _fail("I/O graph transfer identity or endpoint registration changed")

    if plan.slot in {"INPUT_READ", "STAGE_WRITE"} and plan.family in {
        "FROZEN_SOURCE",
        "SEALED_STAGE",
        "SEALED_MEMFD",
    }:
        if plan.ordinal not in {0, 1}:
            _fail("I/O predecessor transfer ordinal changed")
        role = "TERMINAL" if plan.ordinal == 0 else "VERIFICATION"
        expected_bytes = (
            worker.TERMINAL_BYTE_COUNT
            if plan.ordinal == 0
            else worker.VERIFICATION_BYTE_COUNT
        )
        snapshot_id, snapshot = _one_registered_evidence_v180r12r3r2(
            evidence_documents_by_id,
            "acfqp.campaign_stable_input_snapshot.v180r12r3r2",
            field_name="role",
            field_value=role,
        )
        if snapshot.get("observed_byte_count") != expected_bytes:
            _fail("I/O source snapshot byte denominator changed")
        if plan.slot == "INPUT_READ" and plan.family == "FROZEN_SOURCE":
            manifest_id, _manifest = _one_registered_evidence_v180r12r3r2(
                evidence_documents_by_id,
                "acfqp.campaign_operation_manifest.v180r12r3r2",
            )
            expected_endpoints = (manifest_id, snapshot_id)
        else:
            stage_id, stage = _one_registered_evidence_v180r12r3r2(
                evidence_documents_by_id,
                "acfqp.campaign_memfd_stage_receipt.v180r12r3r2",
                field_name="role",
                field_value=role,
            )
            if (
                stage.get("input_snapshot_id") != snapshot_id
                or stage.get("byte_count") != expected_bytes
            ):
                _fail("I/O staged payload crossed its exact source snapshot")
            if plan.slot == "STAGE_WRITE" and plan.family == "SEALED_MEMFD":
                expected_endpoints = (snapshot_id, stage_id)
            elif plan.slot == "INPUT_READ" and plan.family == "SEALED_STAGE":
                worker_birth_id, _birth = _one_registered_evidence_v180r12r3r2(
                    evidence_documents_by_id,
                    "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2",
                    field_name="process_role",
                    field_value="WORKER",
                )
                expected_endpoints = (stage_id, worker_birth_id)
            else:
                _fail("I/O predecessor transfer escaped its exact graph")
    elif plan.slot == "SUBJECT_WRITE" and plan.family == "SUBJECT_RESULT":
        subject_id, subject = _one_registered_evidence_v180r12r3r2(
            evidence_documents_by_id,
            "acfqp.campaign_measurement_subject_result.v180r12r3r2",
        )
        worker_birth_id, _birth = _one_registered_evidence_v180r12r3r2(
            evidence_documents_by_id,
            "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2",
            field_name="process_role",
            field_value="WORKER",
        )
        if (
            subject.get("subject_byte_count") != measured_value
        ):
            _fail("subject write did not join subject-result to worker birth")
        expected_endpoints = (subject_id, worker_birth_id)
    elif plan.slot == "INPUT_READ" and plan.family == "SUBJECT_READBACK":
        subject_id, subject = _one_registered_evidence_v180r12r3r2(
            evidence_documents_by_id,
            "acfqp.campaign_measurement_subject_result.v180r12r3r2",
        )
        supervisor_birth_id, _birth = _one_registered_evidence_v180r12r3r2(
            evidence_documents_by_id,
            "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2",
            field_name="process_role",
            field_value="SUPERVISOR",
        )
        if subject.get("subject_byte_count") != measured_value:
            _fail("subject readback byte denominator changed")
        expected_endpoints = (subject_id, supervisor_birth_id)
    else:
        _fail("I/O operation escaped the frozen eight-edge graph")

    if (source_id, target_id) != expected_endpoints:
        _fail("I/O transfer source/target evidence roles changed")
    return source_id, target_id


class CampaignLedgerAdapterV180R12R3R2(Protocol):
    def open(
        self,
        *,
        protocol_id: str,
        authorization_id: str,
        attempt_id: str,
        max_event_count: int,
        max_event_byte_count: int,
        max_ledger_byte_count: int,
    ) -> Any: ...

    def append(
        self,
        state: Any,
        *,
        phase: str,
        actor_role: str,
        operation_id: str,
        event_kind: str,
        monotonic_ns: int,
        payload: Mapping[str, Any],
    ) -> tuple[Any, Any]: ...

    def close(
        self,
        state: Any,
        *,
        actor_role: str,
        operation_id: str,
        monotonic_ns: int,
        payload: Mapping[str, Any],
    ) -> tuple[Any, Any]: ...


@dataclass(frozen=True, slots=True)
class FunctionalLedgerAdapterV180R12R3R2:
    open_function: Callable[..., Any] = ledger.open_campaign_ledger_v180r12r3r2
    append_function: Callable[..., tuple[Any, Any]] = (
        ledger.append_campaign_event_v180r12r3r2
    )
    close_function: Callable[..., tuple[Any, Any]] = (
        ledger.close_campaign_ledger_v180r12r3r2
    )

    def __post_init__(self) -> None:
        if not all(
            callable(function)
            for function in (
                self.open_function,
                self.append_function,
                self.close_function,
            )
        ):
            _fail("campaign ledger adapter functions must be callable")

    def open(self, **kwargs: Any) -> Any:
        return self.open_function(**kwargs)

    def append(self, state: Any, **kwargs: Any) -> tuple[Any, Any]:
        return self.append_function(state, **kwargs)

    def close(self, state: Any, **kwargs: Any) -> tuple[Any, Any]:
        return self.close_function(state, **kwargs)


class CampaignMeasurementSupervisorV180R12R3R2:
    """Effect-free mutable facade over the functional observer ledger."""

    __slots__ = (
        "protocol_id",
        "authorization_id",
        "attempt_id",
        "operation_schedule",
        "success_event_plan",
        "_operation_plan_by_id",
        "_adapter",
        "_ledger_state",
        "_events",
        "_current_phase_index",
        "_last_monotonic_ns",
        "_intent_kind_by_operation",
        "_completed_operation_ids",
        "_kind_counts",
        "_evidence_documents_by_id",
        "_used_direct_evidence_ids",
        "_active_mounts_by_operation",
        "_failed",
        "_closed",
    )

    def __init__(
        self,
        *,
        protocol_id: str,
        authorization_id: str,
        attempt_id: str,
        adapter: CampaignLedgerAdapterV180R12R3R2 | None = None,
        max_event_count: int = MAX_EVENT_COUNT,
        max_event_byte_count: int = MAX_EVENT_BYTE_COUNT,
        max_ledger_byte_count: int = MAX_LEDGER_BYTE_COUNT,
    ) -> None:
        for value, label in (
            (protocol_id, "supervisor protocol ID"),
            (authorization_id, "supervisor authorization ID"),
            (attempt_id, "supervisor attempt ID"),
        ):
            _cid(value, label)
        if (
            max_event_count != MAX_EVENT_COUNT
            or max_event_byte_count != MAX_EVENT_BYTE_COUNT
            or max_ledger_byte_count != MAX_LEDGER_BYTE_COUNT
        ):
            _fail("runtime ledger caps changed from the frozen 4096/64KiB/64MiB")
        selected = FunctionalLedgerAdapterV180R12R3R2() if adapter is None else adapter
        if not all(callable(getattr(selected, name, None)) for name in ("open", "append", "close")):
            _fail("runtime ledger adapter is malformed")
        self.protocol_id = protocol_id
        self.authorization_id = authorization_id
        self.attempt_id = attempt_id
        self.operation_schedule = build_campaign_operation_schedule_v180r12r3r2(
            attempt_id
        )
        self.success_event_plan = build_campaign_success_event_plan_v180r12r3r2(
            attempt_id
        )
        self._operation_plan_by_id = {
            row.operation_id: row for row in self.operation_schedule
        }
        self._adapter = selected
        self._ledger_state = selected.open(
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            attempt_id=attempt_id,
            max_event_count=max_event_count,
            max_event_byte_count=max_event_byte_count,
            max_ledger_byte_count=max_ledger_byte_count,
        )
        self._events: list[Any] = []
        self._current_phase_index = -1
        self._last_monotonic_ns: int | None = None
        self._intent_kind_by_operation: dict[str, str] = {}
        self._completed_operation_ids: set[str] = set()
        self._kind_counts = {kind: 0 for kind in EVENT_KIND_ROLE_PHASES}
        self._evidence_documents_by_id: dict[str, dict[str, Any]] = {}
        self._used_direct_evidence_ids: set[str] = set()
        self._active_mounts_by_operation: dict[str, tuple[str, int]] = {}
        self._failed = False
        self._closed = False

    @property
    def ledger_state(self) -> Any:
        return self._ledger_state

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def last_event_id(self) -> str | None:
        if not self._events:
            return None
        value = getattr(self._events[-1], "event_id", None)
        return _cid(value, "adapter event ID")

    def register_evidence_document(self, value: Any) -> str:
        """Register one canonical typed document before any event references it."""

        if self._failed or self._closed:
            _fail("failed or closed campaign supervisor cannot register evidence")
        original_value = value
        identity, schema, document = _canonical_evidence_document(value)
        required_runtime_type = {
            "acfqp.campaign_stable_input_snapshot.v180r12r3r2": (
                worker.StableInputSnapshotReceiptV180R12R3R2
            ),
            "acfqp.campaign_memfd_stage_receipt.v180r12r3r2": (
                worker.MemfdStageReceiptV180R12R3R2
            ),
            "acfqp.campaign_fd_visibility_receipt.v180r12r3r2": (
                worker.FDVisibilityReceiptV180R12R3R2
            ),
            "acfqp.campaign_semantic_operation_receipt.v180r12r3r2": (
                worker.SemanticOperationReceiptV180R12R3R2
            ),
            "acfqp.campaign_replay_subject_receipt.v180r12r3r2": (
                worker.ProducerFreeReplaySubjectReceiptV180R12R3R2
            ),
            "acfqp.campaign_pidfd_birth_receipt.v180r12r3r2": (
                PidfdBirthReceiptV180R12R3R2
            ),
            "acfqp.campaign_pidfd_reap_receipt.v180r12r3r2": (
                PidfdReapReceiptV180R12R3R2
            ),
            "acfqp.campaign_cgroup_topology_receipt.v180r12r3r2": (
                MeasurementCgroupTopologyReceiptV180R12R3R2
            ),
            "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2": (
                CgroupV2ObservationReceiptV180R12R3R2
            ),
        }.get(schema)
        if required_runtime_type is not None and type(original_value) is not required_runtime_type:
            _fail("runtime-owned evidence must originate from its exact typed receipt")
        if schema == "acfqp.campaign_measurement_subject_result.v180r12r3r2":
            validator = getattr(
                ledger, "validate_campaign_subject_result_document_v180r12r3r2", None
            )
            if not callable(validator) or validator(
                document,
                expected_protocol_id=self.protocol_id,
                expected_authorization_id=self.authorization_id,
                expected_attempt_id=self.attempt_id,
            ) != document:
                _fail("worker subject-result document failed kernel validation")
        prior = self._evidence_documents_by_id.get(identity)
        if prior is not None and prior != document:
            _fail("campaign evidence identity aliases two documents")
        self._evidence_documents_by_id[identity] = document
        return identity

    def _resolve_direct_evidence(
        self,
        *,
        event_kind: str,
        operation_id: str,
        evidence_id: str | None,
        evidence_document: Any | None,
        measured_value: int | None,
    ) -> str | None:
        expected_schema = _DIRECT_EVENT_EVIDENCE_SCHEMA.get(event_kind)
        if expected_schema is None:
            if evidence_document is not None or evidence_id is not None:
                _fail("intent or ledger-close event cannot carry evidence")
            return None
        if evidence_document is not None:
            registered_id = self.register_evidence_document(evidence_document)
            if evidence_id is not None and evidence_id != registered_id:
                _fail("campaign event supplied mismatching evidence ID/document")
            evidence_id = registered_id
        if evidence_id is None or evidence_id not in self._evidence_documents_by_id:
            _fail("campaign event evidence must be canonically registered first")
        document = self._evidence_documents_by_id[evidence_id]
        if document.get("schema") != expected_schema:
            _fail("campaign event referenced the wrong registered evidence type")
        if document.get("operation_id") != operation_id:
            _fail("campaign event evidence did not bind its exact planned operation")
        for field_name, expected in (
            ("protocol_id", self.protocol_id),
            ("authorization_id", self.authorization_id),
            ("attempt_id", self.attempt_id),
        ):
            if field_name in document and document[field_name] != expected:
                _fail("campaign event evidence crossed its execution context")
        if "measured_value" in document and document["measured_value"] != measured_value:
            _fail("campaign event/evidence measured value changed")
        plan = self._operation_plan_by_id[operation_id]
        if event_kind in {
            "INPUT_READ_OUTCOME",
            "STAGE_WRITE_OUTCOME",
            "SUBJECT_WRITE_OUTCOME",
        }:
            validate_campaign_io_transfer_edge_v180r12r3r2(
                plan=plan,
                event_kind=event_kind,
                measured_value=measured_value,
                receipt_document=document,
                evidence_documents_by_id=self._evidence_documents_by_id,
            )
        if event_kind in {"INPUT_READ_OUTCOME", "STAGE_WRITE_OUTCOME"} and plan.family in {
            "FROZEN_SOURCE",
            "SEALED_STAGE",
            "SEALED_MEMFD",
        }:
            expected_input_bytes = (
                worker.TERMINAL_BYTE_COUNT
                if plan.ordinal == 0
                else worker.VERIFICATION_BYTE_COUNT
            )
            if measured_value != expected_input_bytes:
                _fail("exact predecessor input transfer byte count changed")
        if event_kind == "CGROUP_OBSERVED" and document.get(
            "memory_peak_bytes"
        ) != measured_value:
            _fail("cgroup event did not bind the observed root memory.peak")
        if event_kind in {"MOUNT_VISIBILITY_OPEN", "MOUNT_VISIBILITY_CLOSE"}:
            stage_id = _cid(document.get("stage_receipt_id"), "mount stage receipt ID")
            stage_document = self._evidence_documents_by_id.get(stage_id)
            if (
                stage_document is None
                or stage_document.get("schema")
                != "acfqp.campaign_memfd_stage_receipt.v180r12r3r2"
            ):
                _fail("mount evidence lacks its registered memfd stage receipt")
            stage_bytes = _positive(stage_document.get("byte_count"), "mount payload bytes")
            expected_stage_bytes = (
                worker.TERMINAL_BYTE_COUNT
                if plan.ordinal == 0
                else worker.VERIFICATION_BYTE_COUNT
            )
            expected_stage_role = "TERMINAL" if plan.ordinal == 0 else "VERIFICATION"
            if (
                stage_bytes != expected_stage_bytes
                or stage_document.get("role") != expected_stage_role
            ):
                _fail("mount operation crossed its exact predecessor payload")
            if event_kind == "MOUNT_VISIBILITY_OPEN":
                if operation_id in self._active_mounts_by_operation:
                    _fail("mount operation is already active")
                expected_aggregate = sum(
                    byte_count
                    for _stage_id, byte_count in self._active_mounts_by_operation.values()
                ) + stage_bytes
                if measured_value != expected_aggregate:
                    _fail("mount OPEN must measure current aggregate visible bytes")
            elif (
                measured_value is not None
                or self._active_mounts_by_operation.get(operation_id)
                != (stage_id, stage_bytes)
            ):
                _fail("mount CLOSE did not match its exact active payload interval")
        if event_kind in {
            "SEMANTIC_HASH_OUTCOME",
            "INTEGRITY_CHECK_OUTCOME",
            "PROTOCOL_CHECK_OUTCOME",
            "PROCESS_BIRTH_OUTCOME",
        } and measured_value != 1:
            _fail("unit evidence event changed its exact measured value")
        if evidence_id in self._used_direct_evidence_ids:
            _fail("campaign direct evidence identity was reused")
        return evidence_id

    def _precheck(
        self,
        *,
        phase: str,
        actor_role: str,
        operation_id: str,
        event_kind: str,
        monotonic_ns: int,
    ) -> None:
        if self._failed or self._closed:
            _fail("failed or closed campaign supervisor cannot append")
        if len(self._events) >= len(self.success_event_plan):
            _fail("campaign event exceeds the exact successful plan")
        expected_next = self.success_event_plan[len(self._events)]
        if (
            phase,
            actor_role,
            operation_id,
            event_kind,
        ) != (
            expected_next.phase,
            expected_next.actor_role,
            expected_next.operation_id,
            expected_next.event_kind,
        ):
            _fail("campaign event is not the next exact registered lifecycle event")
        _identifier(operation_id, "campaign operation ID")
        plan = self._operation_plan_by_id.get(operation_id)
        if plan is None or EVENT_KIND_SLOT.get(event_kind) != plan.slot:
            _fail("campaign event operation ID is unplanned or slot-crossed")
        if (
            event_kind not in EVENT_KIND_ROLE_PHASES
            or (actor_role, phase) not in EVENT_KIND_ROLE_PHASES[event_kind]
        ):
            _fail("campaign event actor/phase grammar changed")
        phase_index = PHASE_ORDER.index(phase)
        if phase_index < self._current_phase_index:
            _fail("campaign event phase regressed")
        if type(monotonic_ns) is not int or monotonic_ns < 0:
            _fail("campaign monotonic time is malformed")
        if self._last_monotonic_ns is not None and monotonic_ns <= self._last_monotonic_ns:
            _fail("campaign monotonic time must strictly increase")
        if plan.slot not in {"MOUNT", "PROCESS"} and (
            plan.phase != phase or plan.actor_role != actor_role
        ):
            _fail("campaign event operation role/phase crossed its exact plan")
        if plan.slot == "MOUNT" and not (
            actor_role == "SUPERVISOR"
            and phase
            == (
                "STAGE"
                if event_kind == "MOUNT_VISIBILITY_OPEN"
                else "WINDOW_CLOSE"
            )
        ):
            _fail("campaign mount operation crossed its open/close plan")
        if plan.slot == "PROCESS":
            expected_pair = {
                ("SUPERVISOR", "PROCESS_BIRTH_INTENT"): ("OBSERVER", "STAGE"),
                ("SUPERVISOR", "PROCESS_BIRTH_OUTCOME"): ("OBSERVER", "STAGE"),
                ("SUPERVISOR", "PROCESS_REAP"): ("OBSERVER", "OS_OBSERVE"),
                ("WORKER", "PROCESS_BIRTH_INTENT"): ("SUPERVISOR", "WORKER"),
                ("WORKER", "PROCESS_BIRTH_OUTCOME"): ("SUPERVISOR", "WORKER"),
                ("WORKER", "PROCESS_REAP"): ("SUPERVISOR", "WORKER"),
            }.get((plan.family, event_kind))
            if expected_pair != (actor_role, phase):
                _fail("campaign process operation crossed its exact role chain")
        if event_kind in INTENT_OUTCOME_PAIRS:
            if operation_id in self._intent_kind_by_operation or operation_id in self._completed_operation_ids:
                _fail("campaign operation intent ID was reused")
        elif event_kind in OUTCOME_INTENT:
            expected_intent = OUTCOME_INTENT[event_kind]
            if self._intent_kind_by_operation.get(operation_id) != expected_intent:
                _fail("campaign outcome lacks its exact prior intent operation ID")
        elif event_kind == "MOUNT_VISIBILITY_OPEN":
            if operation_id in self._intent_kind_by_operation or operation_id in self._completed_operation_ids:
                _fail("mount visibility operation ID was reused")
        elif event_kind == "MOUNT_VISIBILITY_CLOSE":
            if self._intent_kind_by_operation.get(operation_id) != "MOUNT_VISIBILITY_OPEN":
                _fail("mount close lacks its exact open operation ID")
        elif event_kind == "PROCESS_REAP":
            if self._intent_kind_by_operation.get(operation_id) != "PROCESS_BIRTH_OUTCOME":
                _fail("process reap lacks its exact successful birth operation ID")
        elif operation_id in self._completed_operation_ids:
            _fail("campaign singleton operation ID was reused")

    def append_event(
        self,
        *,
        phase: str,
        actor_role: str,
        operation_id: str,
        event_kind: str,
        monotonic_ns: int,
        evidence_id: str | None = None,
        evidence_document: Any | None = None,
        measured_value: int | None = None,
        auxiliary_values: Sequence[tuple[str, str | int | bool | None]] = (),
    ) -> Any:
        """Append one successful event after local phase and pairing checks."""

        self._precheck(
            phase=phase,
            actor_role=actor_role,
            operation_id=operation_id,
            event_kind=event_kind,
            monotonic_ns=monotonic_ns,
        )
        evidence_id = self._resolve_direct_evidence(
            event_kind=event_kind,
            operation_id=operation_id,
            evidence_id=evidence_id,
            evidence_document=evidence_document,
            measured_value=measured_value,
        )
        payload = campaign_event_payload_v180r12r3r2(
            event_kind=event_kind,
            evidence_id=evidence_id,
            measured_value=measured_value,
            auxiliary_values=auxiliary_values,
        )
        if event_kind == "LEDGER_CLOSED":
            successor, event = self._adapter.close(
                self._ledger_state,
                actor_role=actor_role,
                operation_id=operation_id,
                monotonic_ns=monotonic_ns,
                payload=payload,
            )
        else:
            successor, event = self._adapter.append(
                self._ledger_state,
                phase=phase,
                actor_role=actor_role,
                operation_id=operation_id,
                event_kind=event_kind,
                monotonic_ns=monotonic_ns,
                payload=payload,
            )
        document = getattr(event, "to_document", None)
        if not callable(document):
            _fail("ledger adapter returned an untyped event")
        event_document = document()
        expected_fields = {
            "schema",
            "protocol_id",
            "authorization_id",
            "attempt_id",
            "sequence",
            "phase",
            "actor_role",
            "operation_id",
            "event_kind",
            "previous_event_id",
            "monotonic_ns",
            "payload",
            "event_id",
        }
        if (
            type(event_document) is not dict
            or set(event_document) != expected_fields
            or event_document["protocol_id"] != self.protocol_id
            or event_document["authorization_id"] != self.authorization_id
            or event_document["attempt_id"] != self.attempt_id
            or event_document["sequence"] != len(self._events)
            or event_document["phase"] != phase
            or event_document["actor_role"] != actor_role
            or event_document["operation_id"] != operation_id
            or event_document["event_kind"] != event_kind
            or event_document["monotonic_ns"] != monotonic_ns
            or event_document["payload"] != payload
            or event_document["previous_event_id"] != self.last_event_id
        ):
            _fail("ledger adapter returned a context-drifting event")
        self._ledger_state = successor
        self._events.append(event)
        self._current_phase_index = PHASE_ORDER.index(phase)
        self._last_monotonic_ns = monotonic_ns
        self._kind_counts[event_kind] += 1
        if evidence_id is not None:
            self._used_direct_evidence_ids.add(evidence_id)
        if event_kind == "MOUNT_VISIBILITY_OPEN":
            visibility = self._evidence_documents_by_id[evidence_id]
            stage_id = visibility["stage_receipt_id"]
            self._active_mounts_by_operation[operation_id] = (
                stage_id,
                self._evidence_documents_by_id[stage_id]["byte_count"],
            )
        elif event_kind == "MOUNT_VISIBILITY_CLOSE":
            self._active_mounts_by_operation.pop(operation_id)
        if event_kind in INTENT_OUTCOME_PAIRS:
            self._intent_kind_by_operation[operation_id] = event_kind
        elif event_kind in OUTCOME_INTENT:
            self._intent_kind_by_operation.pop(operation_id)
            self._completed_operation_ids.add(operation_id)
            if event_kind == "PROCESS_BIRTH_OUTCOME":
                self._intent_kind_by_operation[operation_id] = event_kind
                self._completed_operation_ids.discard(operation_id)
        elif event_kind == "MOUNT_VISIBILITY_OPEN":
            self._intent_kind_by_operation[operation_id] = event_kind
        elif event_kind in {"MOUNT_VISIBILITY_CLOSE", "PROCESS_REAP"}:
            self._intent_kind_by_operation.pop(operation_id)
            self._completed_operation_ids.add(operation_id)
        else:
            self._completed_operation_ids.add(operation_id)
        if event_kind == "LEDGER_CLOSED":
            self._closed = True
        return event

    def validate_registered_evidence_bundle(self) -> Any:
        """Return the kernel's canonical 328-document inventory after closure."""

        if not self._closed or self._failed:
            _fail("campaign evidence bundle can only close after the ledger")
        inventory_type = getattr(ledger, "CampaignEvidenceInventoryV180R12R3R2", None)
        if inventory_type is None or not callable(
            getattr(inventory_type, "from_documents", None)
        ):
            _fail("campaign kernel evidence inventory API is unavailable")
        inventory = inventory_type.from_documents(
            tuple(self._evidence_documents_by_id.values())
        )
        direct_ids = {
            identity
            for identity, document in self._evidence_documents_by_id.items()
            if document.get("schema") in set(_DIRECT_EVENT_EVIDENCE_SCHEMA.values())
        }
        if (
            self._used_direct_evidence_ids != direct_ids
            or len(direct_ids) != 317
            or len(self._evidence_documents_by_id) != 328
        ):
            _fail("campaign 317-direct/328-total evidence closure changed")
        return inventory

    def assert_success_schedule_complete(self) -> None:
        """Check the exact 625-event multiset and phase/role distribution."""

        if not self._closed or self._failed or self.event_count != SUCCESSFUL_LEDGER_EVENT_COUNT:
            _fail("campaign supervisor does not hold one complete success ledger")
        expected = {
            "ATTEMPT_OPEN": 1,
            "INPUT_READ_INTENT": 5,
            "INPUT_READ_OUTCOME": 5,
            "STAGE_WRITE_INTENT": 2,
            "STAGE_WRITE_OUTCOME": 2,
            "MOUNT_VISIBILITY_OPEN": 2,
            "MOUNT_VISIBILITY_CLOSE": 2,
            "SEMANTIC_HASH_INTENT": worker.SEMANTIC_HASH_OPERATION_COUNT,
            "SEMANTIC_HASH_OUTCOME": worker.SEMANTIC_HASH_OPERATION_COUNT,
            "INTEGRITY_CHECK_INTENT": worker.INTEGRITY_CHECK_OPERATION_COUNT,
            "INTEGRITY_CHECK_OUTCOME": worker.INTEGRITY_CHECK_OPERATION_COUNT,
            "PROTOCOL_CHECK_INTENT": worker.PROTOCOL_CHECK_OPERATION_COUNT,
            "PROTOCOL_CHECK_OUTCOME": worker.PROTOCOL_CHECK_OPERATION_COUNT,
            "PROCESS_BIRTH_INTENT": 2,
            "PROCESS_BIRTH_OUTCOME": 2,
            "PROCESS_REAP": 2,
            "SUBJECT_WRITE_INTENT": 1,
            "SUBJECT_WRITE_OUTCOME": 1,
            "SUBJECT_COMMIT": 1,
            "WINDOW_CLOSED": 1,
            "CGROUP_OBSERVED": 1,
            "LEDGER_CLOSED": 1,
        }
        if self._kind_counts != expected:
            _fail("campaign successful event multiset changed")
        if self._intent_kind_by_operation:
            _fail("campaign successful ledger retains an open operation")
        if self._active_mounts_by_operation:
            _fail("campaign successful ledger retains an open mount interval")
        scheduled_ids = {row.operation_id for row in self.operation_schedule}
        if self._completed_operation_ids != scheduled_ids:
            _fail("campaign successful ledger did not complete its exact operation plan")

    def freeze_failure(
        self,
        *,
        failure_code: FailureCodeV180R12R3R2,
        phase: CampaignPhaseV180R12R3R2,
        operation_id: str | None,
        message: str,
        process_may_remain: bool,
        output_may_exist: bool,
        partial_artifact_observations: tuple[
            FailureArtifactObservationV180R12R3R2, ...
        ],
        cgroup_failure_observation: FailureCgroupObservationV180R12R3R2 | None,
    ) -> CampaignFailureStateV180R12R3R2:
        """Freeze the current prefix; this attempt identity becomes non-rerunnable."""

        if self._failed or self._closed:
            _fail("failed or closed campaign supervisor cannot fail again")
        receipt = CampaignFailureStateV180R12R3R2(
            self.protocol_id,
            self.authorization_id,
            self.attempt_id,
            failure_code,
            phase,
            operation_id,
            self.last_event_id,
            self.event_count,
            message,
            process_may_remain,
            output_may_exist,
            partial_artifact_observations,
            cgroup_failure_observation,
        )
        self._failed = True
        return receipt


def supervisor_contract_v180r12r3r2() -> dict[str, Any]:
    """Return the outcome-free runtime grammar for protocol preregistration."""

    return {
        "schema": "acfqp.campaign_measurement_supervisor_contract.v180r12r3r2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "phase_order": list(PHASE_ORDER),
        "actor_roles": list(ACTOR_ROLES),
        "event_kind_role_phases": {
            kind: [list(pair) for pair in pairs]
            for kind, pairs in EVENT_KIND_ROLE_PHASES.items()
        },
        "successful_ledger_event_count": SUCCESSFUL_LEDGER_EVENT_COUNT,
        "successful_direct_evidence_event_count": 317,
        "successful_null_evidence_event_count": 308,
        "maximum_event_count": MAX_EVENT_COUNT,
        "maximum_event_byte_count": MAX_EVENT_BYTE_COUNT,
        "maximum_ledger_byte_count": MAX_LEDGER_BYTE_COUNT,
        "memory_max_bytes": MEMORY_MAX_BYTES,
        "pids_max": PIDS_MAX,
        "wall_timeout_seconds": WALL_TIMEOUT_SECONDS,
        "input_read_pair_count": 5,
        "stage_write_pair_count": 2,
        "mount_open_close_pair_count": 2,
        "process_birth_reap_chain_count": 2,
        "semantic_hash_pair_count": worker.SEMANTIC_HASH_OPERATION_COUNT,
        "integrity_check_pair_count": worker.INTEGRITY_CHECK_OPERATION_COUNT,
        "protocol_check_pair_count": worker.PROTOCOL_CHECK_OPERATION_COUNT,
        "subject_write_pair_count": 1,
        "io_transfer_receipt_count": len(IO_TRANSFER_GRAPH_ROWS),
        "io_transfer_graph_rows": [list(row) for row in IO_TRANSFER_GRAPH_ROWS],
        "io_transfer_returned_syscall_chunks_required": True,
        "cgroup_topology": "EMPTY_ROOT_WITH_SUPERVISOR_AND_WORKER_SIBLING_LEAVES",
        "cgroup_controllers": ["memory", "pids"],
        "observer_owns_append_only_ledger": True,
        "intent_outcome_share_operation_id": True,
        "failure_preserves_exact_prefix": True,
        "same_failure_identity_rerun_allowed": False,
        "failure_artifact_observation_row_cap": _FAILURE_ARTIFACT_ROW_CAP,
        "failure_artifact_fixed_path_kind_rows": [
            list(row) for row in FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS
        ],
        "failure_artifact_observation_boundary": (
            FAILURE_ARTIFACT_OBSERVATION_BOUNDARY
        ),
        "failure_artifact_metadata_byte_cap": (
            _FAILURE_ARTIFACT_METADATA_BYTE_CAP
        ),
        "failure_directory_entry_cap": _FAILURE_DIRECTORY_ENTRY_CAP,
        "failure_directory_entry_name_total_byte_cap": (
            _FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP
        ),
        "failure_artifact_stream_hash_byte_cap": (
            _FAILURE_ARTIFACT_STREAM_HASH_BYTE_CAP
        ),
        "failure_artifact_states": [
            "ABSENT", "LINKED_OR_NONREGULAR", "PRESENT", "READ_ERROR"
        ],
        "failure_artifact_kinds": ["DIRECTORY", "FILE"],
        "failure_cgroup_observation_is_not_success_receipt": True,
        "failure_cgroup_node_roles": [
            "MEASUREMENT_ROOT", "SUPERVISOR", "WORKER"
        ],
        "failure_cgroup_node_states": [
            "ABSENT", "LINKED_OR_NONDIR", "PRESENT", "READ_ERROR"
        ],
        "failure_cgroup_node_observation_keys": sorted(
            FAILURE_CGROUP_NODE_OBSERVATION_KEYS
        ),
        "instrumentation_ledger_hashing_counted": False,
        "prelaunch_source_loading_counted": False,
        "child_memory_overhead_in_cgroup_peak": True,
        "real_effects_present_in_this_module": False,
    }


__all__ = (
    "ACTOR_ROLES",
    "CampaignActorRoleV180R12R3R2",
    "CampaignFailureStateV180R12R3R2",
    "CampaignLedgerAdapterV180R12R3R2",
    "CampaignMeasurementSupervisorV180R12R3R2",
    "CampaignOperationPlanV180R12R3R2",
    "CampaignPhaseV180R12R3R2",
    "CampaignSuccessEventPlanV180R12R3R2",
    "CgroupControlFileOFDV180R12R3R2",
    "CgroupControlFileReadbackV180R12R3R2",
    "CgroupNodeIdentityV180R12R3R2",
    "CgroupV2ObservationReceiptV180R12R3R2",
    "ConstructionK7CampaignMeasurementSupervisorV180R12R3R2Error",
    "EVENT_KIND_ROLE_PHASES",
    "EVIDENCE_DOCUMENT_CONTRACT_ROWS",
    "EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS",
    "FailureCodeV180R12R3R2",
    "FailureArtifactObservationV180R12R3R2",
    "FailureCgroupObservationV180R12R3R2",
    "FailureCgroupNodeObservationV180R12R3R2",
    "FAILURE_ARTIFACT_OBSERVATION_KEYS",
    "FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS",
    "FAILURE_ARTIFACT_OBSERVATION_BOUNDARY",
    "FAILURE_CGROUP_OBSERVATION_KEYS",
    "FAILURE_CGROUP_NODE_OBSERVATION_KEYS",
    "FAILURE_STATE_FIELD_KEYS",
    "FunctionalLedgerAdapterV180R12R3R2",
    "HASH_OPERATION_FAMILIES",
    "INTEGRITY_OPERATION_FAMILIES",
    "IO_TRANSFER_GRAPH_ROWS",
    "MAX_EVENT_BYTE_COUNT",
    "MAX_EVENT_COUNT",
    "MAX_LEDGER_BYTE_COUNT",
    "MEMORY_MAX_BYTES",
    "MeasurementCgroupTopologyReceiptV180R12R3R2",
    "PHASE_ORDER",
    "PIDS_MAX",
    "PROTOCOL_OPERATION_FAMILIES",
    "PidfdBirthReceiptV180R12R3R2",
    "PidfdReapReceiptV180R12R3R2",
    "ProcessRoleV180R12R3R2",
    "RUNTIME_EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS",
    "SUCCESSFUL_LEDGER_EVENT_COUNT",
    "WALL_TIMEOUT_SECONDS",
    "build_campaign_operation_schedule_v180r12r3r2",
    "build_campaign_success_event_plan_v180r12r3r2",
    "campaign_event_payload_v180r12r3r2",
    "supervisor_contract_v180r12r3r2",
    "validate_campaign_io_transfer_edge_v180r12r3r2",
)
