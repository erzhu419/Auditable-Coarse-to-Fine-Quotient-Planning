"""Pure, route-free V180r12r4 campaign-measurement ledger.

V180r12r2 froze a structural campaign boundary because its aggregation process
had not emitted actual campaign-scope measurements.  This additive kernel is
the deliberately narrower successor: it validates an append-only lifecycle
event chain and derives exactly nine actual campaign records from successful
observations.  It does not manufacture a :class:`RouteKindEnum` or an
``ActualWorkScope`` merely to reuse route accounting machinery.

Only the nine normative V6 leaf metadata rows and their SUM/MAX projection
semantics are reused.  The resulting route-free work vector is therefore an
input to later weight-agnostic economics, not an official scalar-cost or
break-even result.  Producer output retains a pending-independent-replay gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, NoReturn, Sequence

from acfqp.accounting_v1 import (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    OUTPUT_BYTES,
    PEAK_MOUNTED_BYTES,
    PEAK_WORKING_BYTES,
    PROCESS_LAUNCHES,
    READ_BYTES,
    SHARED_AXES,
    STAGED_BYTES,
)
from acfqp import construction_k7_domain_registry_extension_v180r12r4e as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r4 as identity_domains
from acfqp import construction_accounting_registry_v6 as accounting_registry_v6
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "1.0.0"
CAMPAIGN_SCOPE_KIND = "TEN_TERMINAL_AGGREGATION_MEASURED_REPLAY_SUCCESSOR"
CAMPAIGN_SCOPE_MODEL = "ROUTE_FREE_MEASURED_REPLAY_SUCCESSOR"
COUNTER_REGISTRY_REFERENCE = accounting_registry_v6.COUNTER_REGISTRY_KEY
COUNTER_COMPLETENESS_GATE = "PENDING_INDEPENDENT_REPLAY"
WORKLOAD_ECONOMICS_GATE = "NOT_RUN"
SCALAR_CALIBRATION_GATE = "NOT_RUN"
BREAK_EVEN_GATE = "NOT_RUN"
OFFICIAL_EXECUTION_GATE = "NOT_RUN"

CAMPAIGN_COUNTER_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)
CAMPAIGN_PATH_RECEIPT_COUNT = len(CAMPAIGN_COUNTER_PATHS)
CAMPAIGN_COUNTER_RECORD_COUNT = len(CAMPAIGN_COUNTER_PATHS)
SEMANTIC_HASH_OPERATION_COUNT = 137
INTEGRITY_CHECK_OPERATION_COUNT = 145
PROTOCOL_CHECK_OPERATION_COUNT = 15
SUCCESS_EVENT_COUNT = 625
SUCCESS_EVENT_EVIDENCE_COUNT = 317
SUCCESS_NULL_EVIDENCE_COUNT = 308
CAMPAIGN_EVIDENCE_DOCUMENT_COUNT = 328
PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT = 90
PREDECESSOR_STRUCTURAL_OBLIGATION_COUNT = 9
PREDECESSOR_CAMPAIGN_ACTUAL_RECEIPT_COUNT = 0
PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT = 0
SUCCESSOR_CAMPAIGN_ACTUAL_RECEIPT_COUNT = 9
COMBINED_SUCCESSOR_AUTHORITATIVE_RECEIPT_COUNT = 99
TERMINAL_INPUT_BYTE_COUNT = 199_755
VERIFICATION_INPUT_BYTE_COUNT = 2_752
TOTAL_STAGED_INPUT_BYTE_COUNT = 202_507
SUBJECT_RESULT_RUNTIME_BYTE_CAP = 768 * 1024
FRAME_BYTE_CAP = 1 * 1024 * 1024
MEMORY_MAX_BYTES = 16 * 1024 * 1024 * 1024
PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA = (
    "acfqp.v180r12r4_production_runtime_placement_t1.v1"
)
PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA = (
    "acfqp.v180r12r4_production_runtime_placement_t2.v2"
)
PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA = (
    "acfqp.v180r12r4_production_runtime_placement_t3.v2"
)
PRODUCTION_RUNTIME_PLACEMENT_T1_FIELDS = frozenset(
    "schema target token unit_name slice source_membership "
    "expected_source_membership self_pid self_pid_in_source_cgroup_procs "
    "cgroup_namespace_inode delegated_parent_fd_fact cgroup2_mount_fd_fact "
    "source_service_fd_fact nearest_common_ancestor_path "
    "nearest_common_ancestor_is_app_slice parent_cgroup_procs_o_wronly_openable "
    "planned_measurement_root_observation planned_measurement_root_absent "
    "t1_complete_before_child_popen".split()
)
PRODUCTION_RUNTIME_PLACEMENT_T2_FIELDS = frozenset(
    "schema boundary target token unit_name source_membership "
    "expected_source_membership self_pid self_pid_in_source_cgroup_procs "
    "parent_pid parent_pid_in_source_cgroup_procs "
    "source_service_fd source_service_device source_service_inode "
    "cgroup_namespace_inode nearest_common_ancestor_path "
    "nearest_common_ancestor_is_app_slice parent_cgroup_procs_o_wronly_openable "
    "planned_measurement_root_state scientific_progress_present_paths "
    "scientific_progress_absent".split()
)
PRODUCTION_RUNTIME_PLACEMENT_T3_CHECKPOINT_FIELDS = frozenset(
    (*PRODUCTION_RUNTIME_PLACEMENT_T2_FIELDS,
     "measurement_root_device", "measurement_root_inode",
     "supervisor_leaf_device", "supervisor_leaf_inode",
     "worker_leaf_device", "worker_leaf_inode", "target_cgroup_role",
     "target_cgroup_fd", "target_cgroup_device", "target_cgroup_inode",
     "target_cgroup_path", "target_membership_path",
     "root_empty_before_birth", "supervisor_leaf_empty_before_birth",
     "worker_leaf_empty_before_birth", "programmed_limits_revalidated")
)
PRODUCTION_RUNTIME_PLACEMENT_T3_FIELDS = frozenset(
    "schema target token unit_name before_getrandom "
    "immediately_before_clone3 stable_across_boundaries".split()
)
_PLACEMENT_STABLE_SOURCE_FIELDS = (
    "target", "token", "unit_name", "source_membership",
    "expected_source_membership", "self_pid",
    "self_pid_in_source_cgroup_procs", "parent_pid",
    "parent_pid_in_source_cgroup_procs", "source_service_device",
    "source_service_inode", "cgroup_namespace_inode",
    "nearest_common_ancestor_path", "nearest_common_ancestor_is_app_slice",
    "parent_cgroup_procs_o_wronly_openable",
)

# These labels are part of the evidence grammar, rather than merely producer
# implementation details.  The ledger must be able to validate the typed
# semantic receipts without importing the worker that produced them.
INNER_CONTENT_ID_OPERATION_SUFFIXES = (
    *(f"source_receipt.{index:02d}" for index in range(5)),
    *(f"route_component_chain_receipt.{index:02d}" for index in range(12)),
    *(f"terminal_receipt.{index:02d}" for index in range(10)),
    *(f"terminal_shared_resource_receipt.{index:03d}" for index in range(90)),
    *(f"terminal_shared_resource_receipt_set.{index:02d}" for index in range(10)),
    "v180r7r1_construction_axis_receipt",
    "campaign_scope_structural_boundary",
)
SEMANTIC_HASH_OPERATION_LABELS = (
    "hash.source_file_sha256.terminal",
    "hash.source_file_sha256.verification",
    "hash.staged_file_sha256.terminal",
    "hash.staged_file_sha256.verification",
    "hash.top_content_id.terminal",
    "hash.top_content_id.verification",
    *(f"hash.inner_content_id.{suffix}" for suffix in INNER_CONTENT_ID_OPERATION_SUFFIXES),
    "hash.subject_result_id",
    "hash.subject_readback_sha256",
)
INTEGRITY_CHECK_OPERATION_LABELS = (
    "integrity.stage_source.terminal.stable_read",
    "integrity.stage_source.verification.stable_read",
    "integrity.stage_source.terminal.sha256",
    "integrity.stage_source.verification.sha256",
    "integrity.stage_source.terminal.memfd_seals",
    "integrity.stage_source.verification.memfd_seals",
    "integrity.worker_staged.terminal.sha256",
    "integrity.worker_staged.verification.sha256",
    "integrity.worker_staged.terminal.canonical_json",
    "integrity.worker_staged.verification.canonical_json",
    "integrity.worker_staged.terminal.top_content_id",
    "integrity.worker_staged.verification.top_content_id",
    *(f"integrity.worker_inner_content_id.{suffix}" for suffix in INNER_CONTENT_ID_OPERATION_SUFFIXES),
    "integrity.worker_inner_content_id.denominator_and_uniqueness",
    "integrity.worker_subject.canonical_json_and_content_id",
    "integrity.commit_subject.readback_size_and_sha256",
    "integrity.commit_subject.stable_mode_and_nlink",
)
PROTOCOL_CHECK_OPERATION_LABELS = (
    "protocol.terminal_schema_and_keyset",
    "protocol.verification_schema_and_keyset",
    "protocol.lineage_ids",
    "protocol.source_receipt_order",
    "protocol.route_component_order",
    "protocol.terminal_receipt_order",
    "protocol.shared_set_and_receipt_order",
    "protocol.construction_axis_separation",
    "protocol.structural_nine_zero_route_free",
    "protocol.verification_terminal_bytes_sha_join",
    "protocol.global_denominators",
    "protocol.pending_to_pass_transition",
    "protocol.four_gates_blocker_and_official",
    "protocol.successor_nonretroactivity_and_import_boundary",
    "protocol.subject_schema_and_keyset",
)
SEMANTIC_RECEIPT_AUXILIARY_NAME_BY_KIND = MappingProxyType(
    {
        "SEMANTIC_HASH": "observed_sha256",
        "INTEGRITY_CHECK": "check_passed",
        "PROTOCOL_CHECK": "check_passed",
    }
)

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
PROTOCOL_CHECK_FAMILIES = (
    "TERMINAL_SCHEMA_AND_KEYSET",
    "VERIFICATION_SCHEMA_AND_KEYSET",
    "LINEAGE_IDS",
    "SOURCE_RECEIPT_ORDER",
    "ROUTE_COMPONENT_ORDER",
    "TERMINAL_RECEIPT_ORDER",
    "SHARED_SET_AND_RECEIPT_ORDER",
    "CONSTRUCTION_AXIS_SEPARATION",
    "STRUCTURAL_NINE_ZERO_ROUTE_FREE",
    "VERIFICATION_TERMINAL_BYTES_SHA_JOIN",
    "GLOBAL_DENOMINATORS",
    "PENDING_TO_PASS_TRANSITION",
    "FOUR_GATES_BLOCKER_AND_OFFICIAL",
    "SUCCESSOR_NONRETROACTIVITY_AND_IMPORT_BOUNDARY",
    "SUBJECT_SCHEMA_AND_KEYSET",
)

CAMPAIGN_LEDGER_PHASES = (
    "ATTEMPT",
    "STAGE",
    "WORKER",
    "COMMIT",
    "WINDOW_CLOSE",
    "OS_OBSERVE",
    "LEDGER_CLOSE",
)

EVENT_KIND_ROLE_PHASES = {
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
EVENT_KIND_PHASES = {
    kind: tuple(dict.fromkeys(phase for _role, phase in pairs))
    for kind, pairs in EVENT_KIND_ROLE_PHASES.items()
}
# Compatibility name for protocol grammars: values are allowed phase tuples,
# not a lossy single-phase map.
EVENT_KIND_PHASE = EVENT_KIND_PHASES
REQUIRED_EVENT_KINDS = tuple(EVENT_KIND_ROLE_PHASES)

_EXPECTED_OUTCOME_CODE = {
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
OUTCOME_CODES = frozenset(
    {"INTENT", "SUCCESS", "PASS", "FAIL", "ERROR", "OPEN", "CLOSED", "OBSERVED", "COMMITTED"}
)

_COUNTER_EVENT_PATH = {
    "INPUT_READ_OUTCOME": "io.read_bytes",
    "STAGE_WRITE_OUTCOME": "io.staged_bytes",
    "MOUNT_VISIBILITY_OPEN": "io.mounted_bytes_peak",
    "SEMANTIC_HASH_OUTCOME": "common.hash_invocations",
    "INTEGRITY_CHECK_OUTCOME": "common.integrity_checks",
    "PROTOCOL_CHECK_OUTCOME": "common.protocol_checks",
    "PROCESS_BIRTH_OUTCOME": "process.launches",
    "SUBJECT_WRITE_OUTCOME": "io.output_bytes",
    "CGROUP_OBSERVED": "memory.working_bytes_peak",
}
_UNIT_EVENT_KINDS = frozenset(
    {
        "SEMANTIC_HASH_OUTCOME",
        "INTEGRITY_CHECK_OUTCOME",
        "PROTOCOL_CHECK_OUTCOME",
        "PROCESS_BIRTH_OUTCOME",
    }
)
_EVENT_KINDS_REQUIRING_EVIDENCE = frozenset(
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
_INTENT_OUTCOME_PAIRS = (
    ("INPUT_READ_INTENT", "INPUT_READ_OUTCOME"),
    ("STAGE_WRITE_INTENT", "STAGE_WRITE_OUTCOME"),
    ("SEMANTIC_HASH_INTENT", "SEMANTIC_HASH_OUTCOME"),
    ("INTEGRITY_CHECK_INTENT", "INTEGRITY_CHECK_OUTCOME"),
    ("PROTOCOL_CHECK_INTENT", "PROTOCOL_CHECK_OUTCOME"),
    ("PROCESS_BIRTH_INTENT", "PROCESS_BIRTH_OUTCOME"),
    ("SUBJECT_WRITE_INTENT", "SUBJECT_WRITE_OUTCOME"),
)

_LEAF_METADATA = {
    "common.hash_invocations": (
        "hash-invocation-v1",
        "content_id_layer",
        "invocations",
        "attempt",
        "sum",
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "common.integrity_checks": (
        "integrity-check-v1",
        "artifact_verifier",
        "checks",
        "attempt",
        "sum",
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "common.protocol_checks": (
        "protocol-check-v1",
        "state_machine_verifier",
        "checks",
        "attempt",
        "sum",
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "io.mounted_bytes_peak": (
        "mounted-byte-peak-v1",
        "sandbox_supervisor",
        "bytes",
        "decision_point",
        "max",
        PEAK_MOUNTED_BYTES,
    ),
    "io.output_bytes": (
        "io-output-byte-v1",
        "artifact_writer",
        "bytes",
        "attempt",
        "sum",
        OUTPUT_BYTES,
    ),
    "io.read_bytes": (
        "io-read-byte-v1",
        "io_wrapper",
        "bytes",
        "attempt",
        "sum",
        READ_BYTES,
    ),
    "io.staged_bytes": (
        "io-staged-byte-v1",
        "sandbox_stager",
        "bytes",
        "attempt",
        "sum",
        STAGED_BYTES,
    ),
    "memory.working_bytes_peak": (
        "working-byte-peak-v1",
        "worker_supervisor_or_frozen_cap",
        "bytes",
        "transaction_or_attempt",
        "max",
        PEAK_WORKING_BYTES,
    ),
    "process.launches": (
        "process-launch-v1",
        "process_supervisor",
        "launches",
        "attempt",
        "sum",
        PROCESS_LAUNCHES,
    ),
}
_AXIS_REDUCER = {
    axis: ("max" if axis in {PEAK_MOUNTED_BYTES, PEAK_WORKING_BYTES} else "sum")
    for axis in SHARED_AXES
}

_CID = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_TOKEN = re.compile(r"^[A-Z][A-Z0-9_]*$")
_PAYLOAD_FIELDS = {
    "evidence_id",
    "outcome_code",
    "measured_value",
    "auxiliary_values",
}
_EVENT_FIELDS = {
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
_STATE_ISSUER = object()


class ConstructionK7CampaignMeasurementLedgerV180R12R4Error(ValueError):
    """The campaign measurement stream or derived route-free chain is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CampaignMeasurementLedgerV180R12R4Error(message)


def _cid(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if type(value) is not str or _CID.fullmatch(value) is None:
        _fail(f"{label} must be one lowercase SHA-256 content ID")
    return value


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        _fail(f"{label} must be one canonical identifier")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be a positive exact integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be a nonnegative exact integer")
    return value


def _canonical_object(value: Any, label: str) -> tuple[bytes, dict[str, Any]]:
    if type(value) is bytes:
        try:
            document = loads_canonical_json(value)
        except Exception as error:
            raise ConstructionK7CampaignMeasurementLedgerV180R12R4Error(
                f"{label} is not canonical JSON"
            ) from error
        if type(document) is not dict or canonical_json_bytes(document) != value:
            _fail(f"{label} is not one canonical object")
        return value, document
    if type(value) is not dict:
        _fail(f"{label} must be canonical bytes or one exact dictionary")
    return canonical_json_bytes(value), value


@dataclass(frozen=True, slots=True)
class CampaignOperationSpecV180R12R4:
    slot: str
    family: str
    ordinal: int
    phase: str
    actor_role: str
    operation_id: str

    def __post_init__(self) -> None:
        if (
            type(self.slot) is not str
            or _TOKEN.fullmatch(self.slot) is None
            or type(self.family) is not str
            or _TOKEN.fullmatch(self.family) is None
        ):
            _fail("campaign operation slot or family changed")
        _nonnegative_int(self.ordinal, "campaign operation ordinal")
        if self.phase not in CAMPAIGN_LEDGER_PHASES:
            _fail("campaign operation phase changed")
        if self.actor_role not in {"OBSERVER", "SUPERVISOR", "WORKER"}:
            _fail("campaign operation actor role changed")
        _cid(self.operation_id, "campaign operation ID")

    def to_document(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "family": self.family,
            "ordinal": self.ordinal,
            "phase": self.phase,
            "actor_role": self.actor_role,
            "operation_id": self.operation_id,
        }


def campaign_operation_id_v180r12r4(
    attempt_id: str, *, slot: str, family: str, ordinal: int
) -> str:
    """Derive one preregistered operation identity from the attempt domain."""

    canonical_attempt_id = _cid(attempt_id, "campaign operation attempt ID")
    if (
        type(slot) is not str
        or _TOKEN.fullmatch(slot) is None
        or type(family) is not str
        or _TOKEN.fullmatch(family) is None
    ):
        _fail("campaign operation slot or family changed")
    _nonnegative_int(ordinal, "campaign operation ordinal")
    return domains.extension_content_id_v180r12r4e(
        domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_V180R12R4E_DOMAIN,
        {
            "schema": "acfqp.campaign_operation_identity.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "attempt_id": canonical_attempt_id,
            "slot": slot,
            "family": family,
            "ordinal": ordinal,
        },
    )


@lru_cache(maxsize=32)
def build_campaign_operation_schedule_v180r12r4(
    attempt_id: str,
) -> tuple[CampaignOperationSpecV180R12R4, ...]:
    """Return the exact 314-operation authority shared by all participants."""

    canonical_attempt_id = _cid(attempt_id, "campaign operation attempt ID")
    specifications: list[tuple[str, str, int, str, str]] = [
        ("ATTEMPT", "OPEN", 0, "ATTEMPT", "OBSERVER"),
        ("PROCESS", "SUPERVISOR", 0, "STAGE", "OBSERVER"),
        ("INPUT_READ", "FROZEN_SOURCE", 0, "STAGE", "SUPERVISOR"),
        ("INPUT_READ", "FROZEN_SOURCE", 1, "STAGE", "SUPERVISOR"),
        ("STAGE_WRITE", "SEALED_MEMFD", 0, "STAGE", "SUPERVISOR"),
        ("STAGE_WRITE", "SEALED_MEMFD", 1, "STAGE", "SUPERVISOR"),
        ("MOUNT", "SEALED_MEMFD", 0, "STAGE", "SUPERVISOR"),
        ("MOUNT", "SEALED_MEMFD", 1, "STAGE", "SUPERVISOR"),
    ]
    family_groups = (
        ("SEMANTIC_HASH", HASH_OPERATION_FAMILIES),
        ("INTEGRITY_CHECK", INTEGRITY_OPERATION_FAMILIES),
    )
    for slot, families in family_groups:
        for family, count, phase, actor_role in families:
            if phase == "STAGE":
                specifications.extend(
                    (slot, family, ordinal, phase, actor_role)
                    for ordinal in range(count)
                )
    specifications.extend(
        (
            ("PROCESS", "WORKER", 0, "WORKER", "SUPERVISOR"),
            ("INPUT_READ", "SEALED_STAGE", 0, "WORKER", "WORKER"),
            ("INPUT_READ", "SEALED_STAGE", 1, "WORKER", "WORKER"),
        )
    )
    for slot, families in family_groups:
        for family, count, phase, actor_role in families:
            if phase == "WORKER":
                specifications.extend(
                    (slot, family, ordinal, phase, actor_role)
                    for ordinal in range(count)
                )
    specifications.extend(
        ("PROTOCOL_CHECK", family, 0, "WORKER", "WORKER")
        for family in PROTOCOL_CHECK_FAMILIES
    )
    specifications.extend(
        (
            ("SUBJECT_WRITE", "SUBJECT_RESULT", 0, "WORKER", "WORKER"),
            ("INPUT_READ", "SUBJECT_READBACK", 0, "COMMIT", "SUPERVISOR"),
        )
    )
    for slot, families in family_groups:
        for family, count, phase, actor_role in families:
            if phase == "COMMIT":
                specifications.extend(
                    (slot, family, ordinal, phase, actor_role)
                    for ordinal in range(count)
                )
    specifications.extend(
        (
            ("SUBJECT_COMMIT", "SUBJECT_RESULT", 0, "COMMIT", "SUPERVISOR"),
            ("WINDOW", "CLOSE", 0, "WINDOW_CLOSE", "SUPERVISOR"),
            ("CGROUP", "FINAL_OBSERVE", 0, "OS_OBSERVE", "OBSERVER"),
            ("LEDGER", "CLOSE", 0, "LEDGER_CLOSE", "OBSERVER"),
        )
    )
    result = tuple(
        CampaignOperationSpecV180R12R4(
            slot,
            family,
            ordinal,
            phase,
            actor_role,
            campaign_operation_id_v180r12r4(
                canonical_attempt_id,
                slot=slot,
                family=family,
                ordinal=ordinal,
            ),
        )
        for slot, family, ordinal, phase, actor_role in specifications
    )
    if len(result) != 314 or len({row.operation_id for row in result}) != 314:
        _fail("campaign exact operation schedule cardinality changed")
    return result


def campaign_operation_manifest_v180r12r4(attempt_id: str) -> dict[str, Any]:
    schedule = build_campaign_operation_schedule_v180r12r4(attempt_id)
    payload = {
        "schema": "acfqp.campaign_operation_manifest.v180r12r4",
        "schema_version": SCHEMA_VERSION,
        "scope": CAMPAIGN_SCOPE_KIND,
        "scope_model": CAMPAIGN_SCOPE_MODEL,
        "attempt_id": attempt_id,
        "operations": [row.to_document() for row in schedule],
        "operation_count": len(schedule),
        "semantic_hash_operation_count": SEMANTIC_HASH_OPERATION_COUNT,
        "integrity_check_operation_count": INTEGRITY_CHECK_OPERATION_COUNT,
        "protocol_check_operation_count": PROTOCOL_CHECK_OPERATION_COUNT,
        "all_event_operation_ids_must_equal_manifest": True,
        "unregistered_operation_ids_forbidden": True,
    }
    return {
        **payload,
        "campaign_operation_manifest_id": domains.extension_content_id_v180r12r4e(
            domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_MANIFEST_V180R12R4E_DOMAIN,
            payload,
        ),
    }


def _operation_specs_by_signature(
    attempt_id: str,
) -> dict[tuple[str, str, str], tuple[str, ...]]:
    buckets: dict[tuple[str, str, str], list[str]] = {}

    def bind(kind: str, role: str, phase: str, spec: CampaignOperationSpecV180R12R4) -> None:
        buckets.setdefault((kind, role, phase), []).append(spec.operation_id)

    for spec in build_campaign_operation_schedule_v180r12r4(attempt_id):
        slot = spec.slot
        if slot == "ATTEMPT":
            bind("ATTEMPT_OPEN", spec.actor_role, spec.phase, spec)
        elif slot == "PROCESS":
            bind("PROCESS_BIRTH_INTENT", spec.actor_role, spec.phase, spec)
            bind("PROCESS_BIRTH_OUTCOME", spec.actor_role, spec.phase, spec)
            reap_role, reap_phase = (
                ("OBSERVER", "OS_OBSERVE")
                if spec.family == "SUPERVISOR"
                else ("SUPERVISOR", "WORKER")
            )
            bind("PROCESS_REAP", reap_role, reap_phase, spec)
        elif slot in {"INPUT_READ", "STAGE_WRITE", "SUBJECT_WRITE"}:
            stem = slot
            bind(f"{stem}_INTENT", spec.actor_role, spec.phase, spec)
            bind(f"{stem}_OUTCOME", spec.actor_role, spec.phase, spec)
        elif slot == "MOUNT":
            bind("MOUNT_VISIBILITY_OPEN", spec.actor_role, spec.phase, spec)
            bind("MOUNT_VISIBILITY_CLOSE", "SUPERVISOR", "WINDOW_CLOSE", spec)
        elif slot in {"SEMANTIC_HASH", "INTEGRITY_CHECK", "PROTOCOL_CHECK"}:
            bind(f"{slot}_INTENT", spec.actor_role, spec.phase, spec)
            bind(f"{slot}_OUTCOME", spec.actor_role, spec.phase, spec)
        else:
            kind = {
                "SUBJECT_COMMIT": "SUBJECT_COMMIT",
                "WINDOW": "WINDOW_CLOSED",
                "CGROUP": "CGROUP_OBSERVED",
                "LEDGER": "LEDGER_CLOSED",
            }[slot]
            bind(kind, spec.actor_role, spec.phase, spec)
    return {key: tuple(value) for key, value in buckets.items()}


@dataclass(frozen=True, slots=True)
class CampaignPlannedEventV180R12R4:
    event_kind: str
    actor_role: str
    phase: str
    operation_id: str


@lru_cache(maxsize=32)
def build_campaign_success_event_schedule_v180r12r4(
    attempt_id: str,
) -> tuple[CampaignPlannedEventV180R12R4, ...]:
    """Expand the exact 314 operations into the exact 625-event success order."""

    schedule = build_campaign_operation_schedule_v180r12r4(attempt_id)
    by_key = {(row.slot, row.family, row.ordinal): row for row in schedule}
    result: list[CampaignPlannedEventV180R12R4] = []

    def emit(
        kind: str,
        spec: CampaignOperationSpecV180R12R4,
        *,
        role: str | None = None,
        phase: str | None = None,
    ) -> None:
        result.append(
            CampaignPlannedEventV180R12R4(
                kind, role or spec.actor_role, phase or spec.phase, spec.operation_id
            )
        )

    def pair(stem: str, spec: CampaignOperationSpecV180R12R4) -> None:
        emit(f"{stem}_INTENT", spec)
        emit(f"{stem}_OUTCOME", spec)

    attempt = by_key[("ATTEMPT", "OPEN", 0)]
    supervisor = by_key[("PROCESS", "SUPERVISOR", 0)]
    worker = by_key[("PROCESS", "WORKER", 0)]
    emit("ATTEMPT_OPEN", attempt)
    pair("PROCESS_BIRTH", supervisor)
    for spec in schedule:
        if spec.slot == "INPUT_READ" and spec.phase == "STAGE":
            pair("INPUT_READ", spec)
    for spec in schedule:
        if spec.slot == "STAGE_WRITE":
            pair("STAGE_WRITE", spec)
    for spec in schedule:
        if spec.slot == "MOUNT":
            emit("MOUNT_VISIBILITY_OPEN", spec)
    for slot in ("SEMANTIC_HASH", "INTEGRITY_CHECK"):
        for spec in schedule:
            if spec.slot == slot and spec.phase == "STAGE":
                pair(slot, spec)
    pair("PROCESS_BIRTH", worker)
    for spec in schedule:
        if spec.slot == "INPUT_READ" and spec.phase == "WORKER":
            pair("INPUT_READ", spec)
    for slot in ("SEMANTIC_HASH", "INTEGRITY_CHECK", "PROTOCOL_CHECK"):
        for spec in schedule:
            if spec.slot == slot and spec.phase == "WORKER":
                pair(slot, spec)
    pair("SUBJECT_WRITE", by_key[("SUBJECT_WRITE", "SUBJECT_RESULT", 0)])
    emit("PROCESS_REAP", worker, role="SUPERVISOR", phase="WORKER")
    pair("INPUT_READ", by_key[("INPUT_READ", "SUBJECT_READBACK", 0)])
    for slot in ("SEMANTIC_HASH", "INTEGRITY_CHECK"):
        for spec in schedule:
            if spec.slot == slot and spec.phase == "COMMIT":
                pair(slot, spec)
    emit("SUBJECT_COMMIT", by_key[("SUBJECT_COMMIT", "SUBJECT_RESULT", 0)])
    for spec in schedule:
        if spec.slot == "MOUNT":
            emit(
                "MOUNT_VISIBILITY_CLOSE",
                spec,
                role="SUPERVISOR",
                phase="WINDOW_CLOSE",
            )
    emit("WINDOW_CLOSED", by_key[("WINDOW", "CLOSE", 0)])
    emit("PROCESS_REAP", supervisor, role="OBSERVER", phase="OS_OBSERVE")
    emit("CGROUP_OBSERVED", by_key[("CGROUP", "FINAL_OBSERVE", 0)])
    emit("LEDGER_CLOSED", by_key[("LEDGER", "CLOSE", 0)])
    if len(result) != SUCCESS_EVENT_COUNT:
        _fail("campaign exact expanded success event count changed")
    return tuple(result)


def _validate_payload(value: Any, event_kind: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PAYLOAD_FIELDS:
        _fail("campaign event payload field set mismatch")
    evidence_id = _cid(value.get("evidence_id"), "event evidence ID", nullable=True)
    outcome_code = value.get("outcome_code")
    if type(outcome_code) is not str or outcome_code not in OUTCOME_CODES:
        _fail("campaign event outcome code changed")
    if outcome_code in {"FAIL", "ERROR"}:
        _fail("failure or error event cannot enter a successful ledger closure")
    if outcome_code != _EXPECTED_OUTCOME_CODE[event_kind]:
        _fail("campaign event kind/outcome semantics changed")
    measured_value = value.get("measured_value")
    if (event_kind in _EVENT_KINDS_REQUIRING_EVIDENCE) != (evidence_id is not None):
        _fail("campaign event evidence nullability changed")
    if event_kind in _COUNTER_EVENT_PATH:
        _positive_int(measured_value, "event measured value")
        if event_kind in _UNIT_EVENT_KINDS and measured_value != 1:
            _fail("successful semantic/process outcome must contribute exactly one")
    elif measured_value is not None:
        _fail("non-counter campaign event cannot carry a measured value")
    rows = value.get("auxiliary_values")
    if rows != []:
        _fail("campaign event auxiliary_values must be the exact empty list")
    return value


@dataclass(frozen=True, slots=True)
class CampaignLedgerEventV180R12R4:
    protocol_id: str
    authorization_id: str
    attempt_id: str
    sequence: int
    phase: str
    actor_role: str
    operation_id: str
    event_kind: str
    previous_event_id: str | None
    monotonic_ns: int
    _payload_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _cid(self.protocol_id, "campaign protocol ID")
        _cid(self.authorization_id, "campaign authorization ID")
        _cid(self.attempt_id, "campaign attempt ID")
        _nonnegative_int(self.sequence, "campaign event sequence")
        if self.phase not in CAMPAIGN_LEDGER_PHASES:
            _fail("campaign event phase changed")
        _identifier(self.actor_role, "campaign event actor role")
        _cid(self.operation_id, "campaign event operation ID")
        if (
            self.event_kind not in EVENT_KIND_ROLE_PHASES
            or (self.actor_role, self.phase)
            not in EVENT_KIND_ROLE_PHASES[self.event_kind]
        ):
            _fail("campaign event kind/actor/phase changed")
        expected_ids = _operation_specs_by_signature(self.attempt_id).get(
            (self.event_kind, self.actor_role, self.phase), ()
        )
        if self.operation_id not in expected_ids:
            _fail("campaign event operation ID is absent from the exact manifest")
        _cid(self.previous_event_id, "previous event ID", nullable=True)
        _nonnegative_int(self.monotonic_ns, "campaign event monotonic time")
        raw, payload = _canonical_object(self._payload_bytes, "campaign event payload")
        if raw != self._payload_bytes:
            _fail("campaign event payload bytes changed")
        _validate_payload(payload, self.event_kind)

    @property
    def payload(self) -> dict[str, Any]:
        return _canonical_object(self._payload_bytes, "campaign event payload")[1]

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_measurement_ledger_event.v180r12r4",
            "protocol_id": self.protocol_id,
            "authorization_id": self.authorization_id,
            "attempt_id": self.attempt_id,
            "sequence": self.sequence,
            "phase": self.phase,
            "actor_role": self.actor_role,
            "operation_id": self.operation_id,
            "event_kind": self.event_kind,
            "previous_event_id": self.previous_event_id,
            "monotonic_ns": self.monotonic_ns,
            "payload": self.payload,
        }

    @property
    def event_id(self) -> str:
        return domains.extension_content_id_v180r12r4e(
            domains.CONSTRUCTION_K7_CAMPAIGN_LEDGER_EVENT_V180R12R4E_DOMAIN,
            self._identity_payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._identity_payload(), "event_id": self.event_id}

    @classmethod
    def from_document(
        cls, value: bytes | dict[str, Any]
    ) -> "CampaignLedgerEventV180R12R4":
        raw, document = _canonical_object(value, "campaign ledger event")
        if set(document) != _EVENT_FIELDS:
            _fail("campaign ledger event field set mismatch")
        if document.get("schema") != "acfqp.campaign_measurement_ledger_event.v180r12r4":
            _fail("campaign ledger event schema changed")
        event = cls(
            document.get("protocol_id"),
            document.get("authorization_id"),
            document.get("attempt_id"),
            document.get("sequence"),
            document.get("phase"),
            document.get("actor_role"),
            document.get("operation_id"),
            document.get("event_kind"),
            document.get("previous_event_id"),
            document.get("monotonic_ns"),
            canonical_json_bytes(document.get("payload")),
        )
        if document.get("event_id") != event.event_id or raw != canonical_json_bytes(
            event.to_document()
        ):
            _fail("campaign ledger event identity or canonical bytes changed")
        return event


@dataclass(frozen=True, slots=True)
class CampaignLedgerStateV180R12R4:
    protocol_id: str
    authorization_id: str
    attempt_id: str
    max_event_count: int
    max_event_byte_count: int
    max_ledger_byte_count: int
    events: tuple[CampaignLedgerEventV180R12R4, ...] = ()
    _event_byte_count: int = field(default=-1, repr=False, compare=False)
    _issuer: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _cid(self.protocol_id, "campaign protocol ID")
        _cid(self.authorization_id, "campaign authorization ID")
        _cid(self.attempt_id, "campaign attempt ID")
        _positive_int(self.max_event_count, "maximum event count")
        _positive_int(self.max_event_byte_count, "maximum event byte count")
        _positive_int(self.max_ledger_byte_count, "maximum ledger byte count")
        if type(self.events) is not tuple or any(
            type(row) is not CampaignLedgerEventV180R12R4 for row in self.events
        ):
            _fail("campaign ledger state events must be one exact typed tuple")
        if len(self.events) > self.max_event_count:
            _fail("campaign ledger event-count cap exceeded")
        if self._issuer is _STATE_ISSUER:
            if (
                type(self._event_byte_count) is not int
                or self._event_byte_count < 0
                or self._event_byte_count > self.max_ledger_byte_count
            ):
                _fail("campaign ledger trusted byte-count state changed")
        else:
            raw_rows = tuple(
                canonical_json_bytes(row.to_document()) for row in self.events
            )
            if any(len(raw) > self.max_event_byte_count for raw in raw_rows):
                _fail("campaign ledger per-event byte cap exceeded")
            byte_count = sum(map(len, raw_rows))
            if byte_count > self.max_ledger_byte_count:
                _fail("campaign ledger total byte cap exceeded")
            object.__setattr__(self, "_event_byte_count", byte_count)

    @property
    def event_byte_count(self) -> int:
        return self._event_byte_count


def open_campaign_ledger_v180r12r4(
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
    max_event_count: int,
    max_event_byte_count: int,
    max_ledger_byte_count: int,
) -> CampaignLedgerStateV180R12R4:
    """Open an empty functional ledger under protocol-supplied positive caps."""

    return CampaignLedgerStateV180R12R4(
        protocol_id,
        authorization_id,
        attempt_id,
        max_event_count,
        max_event_byte_count,
        max_ledger_byte_count,
        (),
        0,
        _STATE_ISSUER,
    )


def append_campaign_event_v180r12r4(
    state: CampaignLedgerStateV180R12R4,
    *,
    phase: str,
    actor_role: str,
    operation_id: str,
    event_kind: str,
    monotonic_ns: int,
    payload: Mapping[str, Any],
) -> tuple[CampaignLedgerStateV180R12R4, CampaignLedgerEventV180R12R4]:
    """Append one immutable canonical event and return the successor state."""

    if type(state) is not CampaignLedgerStateV180R12R4:
        _fail("append requires one V180r12r4 ledger state")
    if state.events and state.events[-1].event_kind == "LEDGER_CLOSED":
        _fail("campaign ledger is already closed")
    event = CampaignLedgerEventV180R12R4(
        state.protocol_id,
        state.authorization_id,
        state.attempt_id,
        len(state.events),
        phase,
        actor_role,
        operation_id,
        event_kind,
        None if not state.events else state.events[-1].event_id,
        monotonic_ns,
        canonical_json_bytes(dict(payload)),
    )
    event_byte_count = len(canonical_json_bytes(event.to_document()))
    if event_byte_count > state.max_event_byte_count:
        _fail("campaign ledger per-event byte cap exceeded")
    successor_byte_count = state.event_byte_count + event_byte_count
    if successor_byte_count > state.max_ledger_byte_count:
        _fail("campaign ledger total byte cap exceeded")
    successor = CampaignLedgerStateV180R12R4(
        state.protocol_id,
        state.authorization_id,
        state.attempt_id,
        state.max_event_count,
        state.max_event_byte_count,
        state.max_ledger_byte_count,
        (*state.events, event),
        successor_byte_count,
        _STATE_ISSUER,
    )
    return successor, event


def close_campaign_ledger_v180r12r4(
    state: CampaignLedgerStateV180R12R4,
    *,
    actor_role: str,
    operation_id: str,
    monotonic_ns: int,
    payload: Mapping[str, Any],
) -> tuple[CampaignLedgerStateV180R12R4, CampaignLedgerEventV180R12R4]:
    return append_campaign_event_v180r12r4(
        state,
        phase="LEDGER_CLOSE",
        actor_role=actor_role,
        operation_id=operation_id,
        event_kind="LEDGER_CLOSED",
        monotonic_ns=monotonic_ns,
        payload=payload,
    )


def _events_by_kind(
    events: Sequence[CampaignLedgerEventV180R12R4], event_kind: str
) -> tuple[CampaignLedgerEventV180R12R4, ...]:
    return tuple(row for row in events if row.event_kind == event_kind)


def _require_exact_operation_pair(
    events: Sequence[CampaignLedgerEventV180R12R4],
    first_kind: str,
    second_kind: str,
) -> None:
    first = _events_by_kind(events, first_kind)
    second = _events_by_kind(events, second_kind)
    first_ids = tuple(row.operation_id for row in first)
    second_ids = tuple(row.operation_id for row in second)
    if (
        not first
        or len(first_ids) != len(set(first_ids))
        or len(second_ids) != len(set(second_ids))
        or set(first_ids) != set(second_ids)
    ):
        _fail(f"campaign operation pairing failed for {first_kind}/{second_kind}")
    position = {row.event_id: row.sequence for row in events}
    by_operation = {row.operation_id: row for row in first}
    for outcome in second:
        intent = by_operation[outcome.operation_id]
        if (
            position[intent.event_id] >= position[outcome.event_id]
            or intent.actor_role != outcome.actor_role
        ):
            _fail(f"campaign operation order/actor changed for {second_kind}")


def _validate_event_stream_v180r12r4(
    state: CampaignLedgerStateV180R12R4,
) -> None:
    events = state.events
    if not events:
        _fail("campaign ledger event chain is empty")
    if len(events) != SUCCESS_EVENT_COUNT:
        _fail("campaign successful ledger must contain exactly 625 events")
    if (
        events[0].event_kind != "ATTEMPT_OPEN"
        or events[-1].event_kind != "LEDGER_CLOSED"
    ):
        _fail("campaign ledger genesis or terminal event changed")
    if len({row.event_id for row in events}) != len(events):
        _fail("campaign ledger repeats an event identity")
    expected_previous: str | None = None
    previous_ns: int | None = None
    phase_indices: list[int] = []
    for sequence, event in enumerate(events):
        if (
            event.protocol_id != state.protocol_id
            or event.authorization_id != state.authorization_id
            or event.attempt_id != state.attempt_id
            or event.sequence != sequence
            or event.previous_event_id != expected_previous
        ):
            _fail("campaign ledger context, sequence, or hash chain changed")
        if previous_ns is not None and event.monotonic_ns <= previous_ns:
            _fail("campaign ledger monotonic time is not strictly increasing")
        phase_indices.append(CAMPAIGN_LEDGER_PHASES.index(event.phase))
        expected_previous = event.event_id
        previous_ns = event.monotonic_ns
    if phase_indices != sorted(phase_indices) or set(phase_indices) != set(
        range(len(CAMPAIGN_LEDGER_PHASES))
    ):
        _fail("campaign ledger phase order or coverage changed")
    evidence_count = sum(row.payload["evidence_id"] is not None for row in events)
    if (
        evidence_count != SUCCESS_EVENT_EVIDENCE_COUNT
        or len(events) - evidence_count != SUCCESS_NULL_EVIDENCE_COUNT
    ):
        _fail("campaign exact 317 non-null/308 null event-evidence split changed")
    actual_expanded_schedule = tuple(
        CampaignPlannedEventV180R12R4(
            event.event_kind,
            event.actor_role,
            event.phase,
            event.operation_id,
        )
        for event in events
    )
    if actual_expanded_schedule != build_campaign_success_event_schedule_v180r12r4(
        state.attempt_id
    ):
        _fail("campaign events changed from the exact expanded 625-event schedule")
    expected_signatures = _operation_specs_by_signature(state.attempt_id)
    actual_signatures: dict[tuple[str, str, str], list[str]] = {}
    for event in events:
        actual_signatures.setdefault(
            (event.event_kind, event.actor_role, event.phase), []
        ).append(event.operation_id)
    if set(actual_signatures) != set(expected_signatures) or any(
        tuple(actual_signatures[key]) != expected_ids
        for key, expected_ids in expected_signatures.items()
    ):
        _fail("campaign event operation IDs changed from the exact manifest")
    missing = sorted(set(REQUIRED_EVENT_KINDS) - {row.event_kind for row in events})
    if missing:
        _fail(f"campaign ledger is missing required event kinds: {missing!r}")
    for kind in (
        "ATTEMPT_OPEN",
        "SUBJECT_COMMIT",
        "WINDOW_CLOSED",
        "CGROUP_OBSERVED",
        "LEDGER_CLOSED",
    ):
        if len(_events_by_kind(events, kind)) != 1:
            _fail(f"campaign ledger requires exactly one {kind} event")
    for first_kind, second_kind in _INTENT_OUTCOME_PAIRS:
        _require_exact_operation_pair(events, first_kind, second_kind)
    _require_exact_operation_pair(
        events, "MOUNT_VISIBILITY_OPEN", "MOUNT_VISIBILITY_CLOSE"
    )
    births = _events_by_kind(events, "PROCESS_BIRTH_OUTCOME")
    reaps = _events_by_kind(events, "PROCESS_REAP")
    if (
        len(births) != 2
        or len(reaps) != 2
        or len({row.operation_id for row in reaps}) != len(reaps)
        or {row.operation_id for row in reaps}
        != {row.operation_id for row in births}
        or {(row.actor_role, row.phase) for row in births}
        != {("OBSERVER", "STAGE"), ("SUPERVISOR", "WORKER")}
        or {(row.actor_role, row.phase) for row in reaps}
        != {("SUPERVISOR", "WORKER"), ("OBSERVER", "OS_OBSERVE")}
    ):
        _fail("campaign exact two-process birth/reap closure changed")
    birth_by_operation = {row.operation_id: row for row in births}
    for reap in reaps:
        birth = birth_by_operation[reap.operation_id]
        if birth.sequence >= reap.sequence or birth.actor_role != reap.actor_role:
            _fail("campaign process was reaped before successful birth")
    reads = _events_by_kind(events, "INPUT_READ_OUTCOME")
    if (
        len(reads) != 5
        or sum(
            row.actor_role == "SUPERVISOR" and row.phase == "STAGE"
            for row in reads
        )
        != 2
        or sum(row.actor_role == "WORKER" and row.phase == "WORKER" for row in reads)
        != 2
        or sum(
            row.actor_role == "SUPERVISOR" and row.phase == "COMMIT"
            for row in reads
        )
        != 1
    ):
        _fail("campaign exact five-read topology changed")
    if len(_events_by_kind(events, "STAGE_WRITE_OUTCOME")) != 2:
        _fail("campaign exact two-stage-write topology changed")
    if len(_events_by_kind(events, "MOUNT_VISIBILITY_OPEN")) != 2:
        _fail("campaign exact two-mount topology changed")
    if len(_events_by_kind(events, "SUBJECT_WRITE_OUTCOME")) != 1:
        _fail("campaign exact one-subject-write topology changed")
    for kind, count in (
        ("SEMANTIC_HASH_OUTCOME", SEMANTIC_HASH_OPERATION_COUNT),
        ("INTEGRITY_CHECK_OUTCOME", INTEGRITY_CHECK_OPERATION_COUNT),
        ("PROTOCOL_CHECK_OUTCOME", PROTOCOL_CHECK_OPERATION_COUNT),
    ):
        if len(_events_by_kind(events, kind)) != count:
            _fail(f"campaign exact {kind} manifest cardinality changed")
    hash_rows = _events_by_kind(events, "SEMANTIC_HASH_OUTCOME")
    integrity_rows = _events_by_kind(events, "INTEGRITY_CHECK_OUTCOME")
    for rows, expected, label in (
        (
            hash_rows,
            {("SUPERVISOR", "STAGE"): 2, ("WORKER", "WORKER"): 134, ("SUPERVISOR", "COMMIT"): 1},
            "semantic hash",
        ),
        (
            integrity_rows,
            {("SUPERVISOR", "STAGE"): 6, ("WORKER", "WORKER"): 137, ("SUPERVISOR", "COMMIT"): 2},
            "integrity check",
        ),
    ):
        actual = {
            pair: sum((row.actor_role, row.phase) == pair for row in rows)
            for pair in expected
        }
        if actual != expected:
            _fail(f"campaign exact {label} role/phase manifest changed")


def replay_campaign_event_chain_v180r12r4(
    event_documents: Sequence[bytes | dict[str, Any]],
    *,
    max_event_count: int,
    max_event_byte_count: int,
    max_ledger_byte_count: int,
) -> CampaignLedgerStateV180R12R4:
    """Producer-free canonical replay of a complete frozen event chain."""

    if isinstance(event_documents, (str, bytes)) or not isinstance(
        event_documents, Sequence
    ):
        _fail("campaign event documents must be one exact sequence")
    events = tuple(CampaignLedgerEventV180R12R4.from_document(row) for row in event_documents)
    if not events:
        _fail("campaign event documents cannot be empty")
    state = CampaignLedgerStateV180R12R4(
        events[0].protocol_id,
        events[0].authorization_id,
        events[0].attempt_id,
        max_event_count,
        max_event_byte_count,
        max_ledger_byte_count,
        events,
    )
    _validate_event_stream_v180r12r4(state)
    return state


_EVIDENCE_SCHEMA_DESCRIPTOR: Mapping[str, tuple[str, str]] = MappingProxyType(
    {
        "acfqp.campaign_attempt_record.v180r12r4": (
            domains.CONSTRUCTION_K7_CAMPAIGN_ATTEMPT_RECORD_V180R12R4E_DOMAIN,
            "campaign_attempt_record_id",
        ),
        "acfqp.campaign_cgroup_topology_receipt.v180r12r4": (
            domains.CONSTRUCTION_K7_CGROUP_TOPOLOGY_RECEIPT_V180R12R4E_DOMAIN,
            "cgroup_topology_receipt_id",
        ),
        "acfqp.campaign_stable_input_snapshot.v180r12r4": (
            domains.CONSTRUCTION_K7_STABLE_INPUT_SNAPSHOT_V180R12R4E_DOMAIN,
            "stable_input_snapshot_id",
        ),
        "acfqp.campaign_io_transfer_receipt.v180r12r4": (
            domains.CONSTRUCTION_K7_IO_TRANSFER_RECEIPT_V180R12R4E_DOMAIN,
            "io_transfer_receipt_id",
        ),
        "acfqp.campaign_memfd_stage_receipt.v180r12r4": (
            domains.CONSTRUCTION_K7_MEMFD_STAGE_RECEIPT_V180R12R4E_DOMAIN,
            "memfd_stage_receipt_id",
        ),
        "acfqp.campaign_fd_visibility_receipt.v180r12r4": (
            domains.CONSTRUCTION_K7_FD_VISIBILITY_RECEIPT_V180R12R4E_DOMAIN,
            "fd_visibility_receipt_id",
        ),
        "acfqp.campaign_semantic_operation_receipt.v180r12r4": (
            domains.CONSTRUCTION_K7_SEMANTIC_OPERATION_RECEIPT_V180R12R4E_DOMAIN,
            "semantic_operation_receipt_id",
        ),
        "acfqp.campaign_pidfd_birth_receipt.v180r12r4": (
            domains.CONSTRUCTION_K7_PIDFD_BIRTH_RECEIPT_V180R12R4E_DOMAIN,
            "pidfd_birth_receipt_id",
        ),
        "acfqp.campaign_pidfd_reap_receipt.v180r12r4": (
            domains.CONSTRUCTION_K7_PIDFD_REAP_RECEIPT_V180R12R4E_DOMAIN,
            "pidfd_reap_receipt_id",
        ),
        "acfqp.campaign_measurement_subject_result.v180r12r4": (
            domains.CONSTRUCTION_K7_CAMPAIGN_SUBJECT_RESULT_V180R12R4E_DOMAIN,
            "subject_result_id",
        ),
        "acfqp.campaign_replay_subject_receipt.v180r12r4": (
            domains.CONSTRUCTION_K7_REPLAY_SUBJECT_RECEIPT_V180R12R4E_DOMAIN,
            "replay_subject_receipt_id",
        ),
        "acfqp.campaign_subject_commit_receipt.v180r12r4": (
            domains.CONSTRUCTION_K7_SUBJECT_COMMIT_RECEIPT_V180R12R4E_DOMAIN,
            "subject_commit_receipt_id",
        ),
        "acfqp.campaign_window_closure_receipt.v180r12r4": (
            domains.CONSTRUCTION_K7_WINDOW_CLOSURE_RECEIPT_V180R12R4E_DOMAIN,
            "window_closure_receipt_id",
        ),
        "acfqp.campaign_cgroup_observation_receipt.v180r12r4": (
            domains.CONSTRUCTION_K7_CGROUP_OBSERVATION_RECEIPT_V180R12R4E_DOMAIN,
            "cgroup_observation_receipt_id",
        ),
        "acfqp.campaign_execution_closure.v180r12r4": (
            domains.CONSTRUCTION_K7_CAMPAIGN_EXECUTION_CLOSURE_V180R12R4E_DOMAIN,
            "campaign_execution_closure_id",
        ),
        "acfqp.campaign_operation_manifest.v180r12r4": (
            domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_MANIFEST_V180R12R4E_DOMAIN,
            "campaign_operation_manifest_id",
        ),
        "acfqp.campaign_native_zero_source_manifest.v180r12r4": (
            domains.CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_MANIFEST_V180R12R4E_DOMAIN,
            "native_zero_source_manifest_id",
        ),
        "acfqp.campaign_native_zero_import_inventory.v180r12r4": (
            domains.CONSTRUCTION_K7_NATIVE_ZERO_IMPORT_INVENTORY_V180R12R4E_DOMAIN,
            "native_zero_import_inventory_id",
        ),
    }
)
EVIDENCE_DOCUMENT_TYPE_COUNTS: Mapping[str, int] = MappingProxyType(
    {
        "acfqp.campaign_attempt_record.v180r12r4": 1,
        "acfqp.campaign_stable_input_snapshot.v180r12r4": 2,
        "acfqp.campaign_io_transfer_receipt.v180r12r4": 8,
        "acfqp.campaign_memfd_stage_receipt.v180r12r4": 2,
        "acfqp.campaign_fd_visibility_receipt.v180r12r4": 4,
        "acfqp.campaign_semantic_operation_receipt.v180r12r4": 297,
        "acfqp.campaign_pidfd_birth_receipt.v180r12r4": 2,
        "acfqp.campaign_pidfd_reap_receipt.v180r12r4": 2,
        "acfqp.campaign_cgroup_topology_receipt.v180r12r4": 1,
        "acfqp.campaign_cgroup_observation_receipt.v180r12r4": 1,
        "acfqp.campaign_replay_subject_receipt.v180r12r4": 1,
        "acfqp.campaign_measurement_subject_result.v180r12r4": 1,
        "acfqp.campaign_subject_commit_receipt.v180r12r4": 1,
        "acfqp.campaign_window_closure_receipt.v180r12r4": 1,
        "acfqp.campaign_execution_closure.v180r12r4": 1,
        "acfqp.campaign_operation_manifest.v180r12r4": 1,
        "acfqp.campaign_native_zero_source_manifest.v180r12r4": 1,
        "acfqp.campaign_native_zero_import_inventory.v180r12r4": 1,
    }
)

# Exact keysets for the eight evidence documents issued by this pure ledger
# kernel.  The worker and supervisor publish the complementary six and four
# rows respectively; the producer-free verifier mechanically joins all 18
# rows so a synthetic fixture cannot silently diverge from runtime bytes.
EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS = (
    (
        "CAMPAIGN_ATTEMPT_RECORD",
        "acfqp.campaign_attempt_record.v180r12r4",
        "campaign_attempt_record_id",
        frozenset(
            "schema schema_version scope protocol_id authorization_id attempt_id "
            "authorization_evidence_id prelaunch_materialization_terminal_id "
            "prelaunch_launch_manifest_sha256 prelaunch_launch_rule_id "
            "measurement_launch_attempt_id operation_id operation_manifest_id "
            "one_shot_attempt_opened "
            "campaign_attempt_record_id".split()
        ),
    ),
    (
        "IO_TRANSFER_RECEIPT",
        "acfqp.campaign_io_transfer_receipt.v180r12r4",
        "io_transfer_receipt_id",
        frozenset(
            "schema schema_version scope protocol_id authorization_id attempt_id "
            "operation_id event_kind measured_value returned_chunk_byte_counts "
            "returned_chunk_count returned_byte_count source_evidence_id "
            "target_evidence_id transfer_identity transfer_complete "
            "io_transfer_receipt_id".split()
        ),
    ),
    (
        "SUBJECT_COMMIT_RECEIPT",
        "acfqp.campaign_subject_commit_receipt.v180r12r4",
        "subject_commit_receipt_id",
        frozenset(
            "schema schema_version scope protocol_id authorization_id attempt_id "
            "operation_id subject_id replay_subject_receipt_id "
            "readback_transfer_receipt_id subject_byte_count stable_readback_verified "
            "subject_committed subject_commit_receipt_id".split()
        ),
    ),
    (
        "WINDOW_CLOSURE_RECEIPT",
        "acfqp.campaign_window_closure_receipt.v180r12r4",
        "window_closure_receipt_id",
        frozenset(
            "schema schema_version scope protocol_id authorization_id attempt_id "
            "operation_id subject_commit_receipt_id close_visibility_receipt_ids "
            "window_closed all_registered_mounts_closed window_closure_receipt_id".split()
        ),
    ),
    (
        "CAMPAIGN_EXECUTION_CLOSURE",
        "acfqp.campaign_execution_closure.v180r12r4",
        "campaign_execution_closure_id",
        frozenset(
            "schema schema_version scope scope_model protocol_id authorization_id "
            "attempt_id subject_id window_closed_event_id window_closure_receipt_id "
            "operation_manifest_id source_manifest_id import_inventory_id "
            "precompiled_source_bundle_sha256 "
            "comparison_axis kernel_transition_calls "
            "registered_planning_operation_site_fact_count "
            "kernel_transition_operation_site_fact_ids "
            "kernel_transition_import_fact_ids unregistered_operation_site_fact_ids "
            "unregistered_import_fact_ids "
            "registered_planning_comparison_ground_kernel_axis_only "
            "prelaunch_sealed_application_import_allowlist_only "
            "runtime_role_exit_origin_guard_required "
            "runtime_role_exit_origin_guard_status "
            "not_an_os_syscall_count unregistered_or_dynamic_sites_forbidden "
            "closed_registered_planning_operation_window_only "
            "open_world_absence_claimed "
            "execution_window_closed campaign_execution_closure_id".split()
        ),
    ),
    (
        "CAMPAIGN_OPERATION_MANIFEST",
        "acfqp.campaign_operation_manifest.v180r12r4",
        "campaign_operation_manifest_id",
        frozenset(
            "schema schema_version scope scope_model attempt_id operations "
            "operation_count semantic_hash_operation_count "
            "integrity_check_operation_count protocol_check_operation_count "
            "all_event_operation_ids_must_equal_manifest "
            "unregistered_operation_ids_forbidden campaign_operation_manifest_id".split()
        ),
    ),
    (
        "NATIVE_ZERO_SOURCE_MANIFEST",
        "acfqp.campaign_native_zero_source_manifest.v180r12r4",
        "native_zero_source_manifest_id",
        frozenset(
            "schema schema_version scope protocol_id authorization_id attempt_id "
            "operation_manifest_id prelaunch_launch_manifest_sha256 "
            "precompiled_source_bundle_sha256 source_fact_rows source_fact_ids "
            "registered_operation_site_fact_rows registered_operation_site_fact_ids "
            "unregistered_operation_site_fact_ids "
            "registered_planning_operation_site_manifest_complete "
            "unregistered_or_dynamic_sites_forbidden "
            "third_party_precompiled_sources_in_trusted_runtime_boundary "
            "open_world_operation_site_absence_claimed "
            "native_zero_source_manifest_id".split()
        ),
    ),
    (
        "NATIVE_ZERO_IMPORT_INVENTORY",
        "acfqp.campaign_native_zero_import_inventory.v180r12r4",
        "native_zero_import_inventory_id",
        frozenset(
            "schema schema_version scope protocol_id authorization_id attempt_id "
            "source_manifest_id precompiled_source_bundle_sha256 "
            "import_fact_rows import_fact_ids unregistered_import_fact_ids "
            "dynamic_import_fact_ids "
            "prelaunch_sealed_application_import_allowlist_complete "
            "runtime_role_exit_origin_guard_required "
            "stdlib_imports_in_trusted_runtime_boundary "
            "third_party_imports_in_trusted_runtime_boundary "
            "trusted_runtime_boundary_namespaces "
            "open_world_import_absence_claimed "
            "native_zero_import_inventory_id".split()
        ),
    ),
)


def _issue_evidence_document(
    *, schema: str, domain: str, identity_field: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    body = {"schema": schema, "schema_version": SCHEMA_VERSION, **dict(payload)}
    if identity_field in body:
        _fail("evidence payload cannot supply its own identity")
    return {
        **body,
        identity_field: domains.extension_content_id_v180r12r4e(domain, body),
    }


def issue_campaign_attempt_record_v180r12r4(
    *,
    protocol_id: str,
    authorization_id: str,
    authorization_evidence_id: str,
    campaign_measurement_execution_slot_id: str,
    logical_occurrence_id: str,
    execution_nonce: str,
    prelaunch_materialization_terminal_id: str,
    prelaunch_launch_manifest_sha256: str,
    prelaunch_launch_rule_id: str,
    measurement_launch_attempt_id: str,
    attempt_id: str,
    operation_id: str,
    operation_manifest_id: str,
) -> dict[str, Any]:
    for value, label in (
        (protocol_id, "attempt protocol ID"),
        (authorization_id, "attempt authorization ID"),
        (authorization_evidence_id, "attempt authorization-evidence ID"),
        (
            campaign_measurement_execution_slot_id,
            "attempt campaign-measurement execution-slot ID",
        ),
        (logical_occurrence_id, "attempt logical-occurrence ID"),
        (execution_nonce, "attempt execution nonce"),
        (
            prelaunch_materialization_terminal_id,
            "attempt prelaunch materialization-terminal ID",
        ),
        (
            prelaunch_launch_manifest_sha256,
            "attempt prelaunch launch-manifest SHA-256",
        ),
        (prelaunch_launch_rule_id, "attempt prelaunch launch-rule ID"),
        (
            measurement_launch_attempt_id,
            "attempt measurement launch-attempt ID",
        ),
        (attempt_id, "attempt ID"),
        (operation_id, "attempt operation ID"),
        (operation_manifest_id, "attempt operation manifest ID"),
    ):
        _cid(value, label)
    expected_attempt_id = (
        identity_domains.derive_campaign_measurement_attempt_id_v180r12r4(
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            authorization_evidence_id=authorization_evidence_id,
            campaign_measurement_execution_slot_id=(
                campaign_measurement_execution_slot_id
            ),
            logical_occurrence_id=logical_occurrence_id,
            execution_nonce=execution_nonce,
        )
    )
    if attempt_id != expected_attempt_id:
        _fail("campaign attempt ID differs from its exact six-input authority")
    return _issue_evidence_document(
        schema="acfqp.campaign_attempt_record.v180r12r4",
        domain=domains.CONSTRUCTION_K7_CAMPAIGN_ATTEMPT_RECORD_V180R12R4E_DOMAIN,
        identity_field="campaign_attempt_record_id",
        payload={
            "scope": CAMPAIGN_SCOPE_KIND,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "authorization_evidence_id": authorization_evidence_id,
            "attempt_id": attempt_id,
            "prelaunch_materialization_terminal_id": (
                prelaunch_materialization_terminal_id
            ),
            "prelaunch_launch_manifest_sha256": (
                prelaunch_launch_manifest_sha256
            ),
            "prelaunch_launch_rule_id": prelaunch_launch_rule_id,
            "measurement_launch_attempt_id": measurement_launch_attempt_id,
            "operation_id": operation_id,
            "operation_manifest_id": operation_manifest_id,
            "one_shot_attempt_opened": True,
        },
    )


def issue_campaign_io_transfer_receipt_v180r12r4(
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
    operation_id: str,
    event_kind: str,
    measured_value: int,
    returned_chunk_byte_counts: Sequence[int],
    source_evidence_id: str,
    target_evidence_id: str,
) -> dict[str, Any]:
    if event_kind not in {
        "INPUT_READ_OUTCOME",
        "STAGE_WRITE_OUTCOME",
        "SUBJECT_WRITE_OUTCOME",
    }:
        _fail("I/O transfer event kind changed")
    _positive_int(measured_value, "I/O transfer measured value")
    if isinstance(returned_chunk_byte_counts, (str, bytes)) or not isinstance(
        returned_chunk_byte_counts, Sequence
    ):
        _fail("I/O returned chunks must be one exact sequence")
    chunks = tuple(returned_chunk_byte_counts)
    if not chunks or any(type(value) is not int or value <= 0 for value in chunks):
        _fail("I/O returned chunks must be nonempty positive exact integers")
    if sum(chunks) != measured_value:
        _fail("I/O returned chunk sum differs from measured value")
    for value, label in (
        (protocol_id, "I/O protocol ID"),
        (authorization_id, "I/O authorization ID"),
        (attempt_id, "I/O attempt ID"),
        (operation_id, "I/O operation ID"),
        (source_evidence_id, "I/O source evidence ID"),
        (target_evidence_id, "I/O target evidence ID"),
    ):
        _cid(value, label)
    return _issue_evidence_document(
        schema="acfqp.campaign_io_transfer_receipt.v180r12r4",
        domain=domains.CONSTRUCTION_K7_IO_TRANSFER_RECEIPT_V180R12R4E_DOMAIN,
        identity_field="io_transfer_receipt_id",
        payload={
            "scope": CAMPAIGN_SCOPE_KIND,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "operation_id": operation_id,
            "event_kind": event_kind,
            "measured_value": measured_value,
            "returned_chunk_byte_counts": list(chunks),
            "returned_chunk_count": len(chunks),
            "returned_byte_count": measured_value,
            "source_evidence_id": source_evidence_id,
            "target_evidence_id": target_evidence_id,
            "transfer_identity": {
                "operation_id": operation_id,
                "event_kind": event_kind,
                "source_evidence_id": source_evidence_id,
                "target_evidence_id": target_evidence_id,
            },
            "transfer_complete": True,
        },
    )


_SUBJECT_RESULT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "scope",
        "protocol_id",
        "authorization_id",
        "authorization_evidence_id",
        "attempt_id",
        "execution_slot_id",
        "execution_nonce",
        "logical_occurrence_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
        "campaign_attempt_record_id",
        "terminal_content_id",
        "terminal_byte_count",
        "terminal_sha256",
        "verification_content_id",
        "verification_byte_count",
        "verification_sha256",
        "terminal_snapshot_id",
        "verification_snapshot_id",
        "memfd_stage_receipt_ids",
        "open_visibility_receipt_ids",
        "worker_birth_receipt_id",
        "operation_manifest_id",
        "inner_content_ids",
        "inner_content_id_count",
        "semantic_hash_operation_count",
        "integrity_check_operation_count",
        "protocol_check_operation_count",
        "route_component_counter_closure_status",
        "exact_v180r12r2_verification_replayed",
        "producer_module_imported",
        "producer_entrypoint_called",
        "v180r12r2_verifier_imported",
        "v180r12r2_verifier_called",
        "retroactive_v180r12r2_cost_claimed",
        "counter_completeness_gate",
        "workload_economics_gate",
        "scalar_calibration_gate",
        "break_even_gate",
        "official_execution_gate",
        "official_scalar_cost",
        "official_N_break_even",
        "official_execution_allowed",
        "subject_byte_count",
        "subject_result_id",
    }
)


def validate_campaign_subject_result_document_v180r12r4(
    value: bytes | dict[str, Any],
    *,
    expected_protocol_id: str | None = None,
    expected_authorization_id: str | None = None,
    expected_attempt_id: str | None = None,
) -> dict[str, Any]:
    """Register exactly the full worker-produced canonical subject document."""

    raw, document = _canonical_object(value, "campaign subject-result document")
    identity, schema = _document_identity(document)
    if (
        schema != "acfqp.campaign_measurement_subject_result.v180r12r4"
        or set(document) != _SUBJECT_RESULT_FIELDS
        or document.get("subject_result_id") != identity
        or document.get("scope")
        != "FRESH_PRODUCER_FREE_POST_OUTCOME_EVIDENCE_REPLAY_SUCCESSOR"
        or document.get("terminal_byte_count") != TERMINAL_INPUT_BYTE_COUNT
        or document.get("verification_byte_count") != VERIFICATION_INPUT_BYTE_COUNT
        or document.get("inner_content_id_count") != 129
        or document.get("semantic_hash_operation_count")
        != SEMANTIC_HASH_OPERATION_COUNT
        or document.get("integrity_check_operation_count")
        != INTEGRITY_CHECK_OPERATION_COUNT
        or document.get("protocol_check_operation_count")
        != PROTOCOL_CHECK_OPERATION_COUNT
        or document.get("route_component_counter_closure_status") != "PASS"
        or document.get("exact_v180r12r2_verification_replayed") is not True
        or document.get("producer_module_imported") is not False
        or document.get("producer_entrypoint_called") is not False
        or document.get("v180r12r2_verifier_imported") is not False
        or document.get("v180r12r2_verifier_called") is not False
        or document.get("retroactive_v180r12r2_cost_claimed") is not False
        or document.get("counter_completeness_gate") != "PENDING_INDEPENDENT_REPLAY"
        or document.get("workload_economics_gate") != "NOT_RUN"
        or document.get("scalar_calibration_gate") != "NOT_RUN"
        or document.get("break_even_gate") != "NOT_RUN"
        or document.get("official_execution_gate") != "NOT_RUN"
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("official_execution_allowed") is not False
        or document.get("subject_byte_count") != len(raw)
        or len(raw) > SUBJECT_RESULT_RUNTIME_BYTE_CAP
    ):
        _fail("campaign subject-result full worker document changed")
    for field_name in (
        "protocol_id",
        "authorization_id",
        "authorization_evidence_id",
        "attempt_id",
        "execution_slot_id",
        "execution_nonce",
        "logical_occurrence_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
        "campaign_attempt_record_id",
        "terminal_content_id",
        "terminal_sha256",
        "verification_content_id",
        "verification_sha256",
        "terminal_snapshot_id",
        "verification_snapshot_id",
        "worker_birth_receipt_id",
        "operation_manifest_id",
    ):
        _cid(document.get(field_name), f"campaign subject-result {field_name}")
    for field_name in ("memfd_stage_receipt_ids", "open_visibility_receipt_ids"):
        values = document.get(field_name)
        if type(values) is not list or len(values) != 2 or len(set(values)) != 2:
            _fail(f"campaign subject-result {field_name} changed")
        for item in values:
            _cid(item, f"campaign subject-result {field_name}")
    inner = document.get("inner_content_ids")
    if (
        type(inner) is not list
        or len(inner) != 129
        or any(type(row) is not dict or set(row) != {"label", "content_id"} for row in inner)
        or len({row["label"] for row in inner}) != 129
        or len({row["content_id"] for row in inner}) != 129
    ):
        _fail("campaign subject-result inner content-ID inventory changed")
    for row in inner:
        _identifier(row["label"], "campaign subject-result inner label")
        _cid(row["content_id"], "campaign subject-result inner content ID")
    for actual, expected, label in (
        (document.get("protocol_id"), expected_protocol_id, "protocol ID"),
        (
            document.get("authorization_id"),
            expected_authorization_id,
            "authorization ID",
        ),
        (document.get("attempt_id"), expected_attempt_id, "attempt ID"),
    ):
        if expected is not None and actual != expected:
            _fail(f"campaign subject-result expected {label} changed")
    return document


def _expected_semantic_receipt_auxiliary_values_v180r12r4(
    *, kind: str, ordinal: int, subject: Mapping[str, Any]
) -> list[dict[str, str | bool]]:
    """Reconstruct the exact worker-factory auxiliary evidence row.

    Event-envelope ``auxiliary_values`` remain empty.  This helper validates
    the independently content-addressed semantic receipt, whose single row is
    required to carry the observed hash value or successful check result.
    """

    if kind == "SEMANTIC_HASH":
        if ordinal in {0, 2}:
            observed = subject.get("terminal_sha256")
        elif ordinal in {1, 3}:
            observed = subject.get("verification_sha256")
        elif ordinal == 4:
            observed = subject.get("terminal_content_id")
        elif ordinal == 5:
            observed = subject.get("verification_content_id")
        elif 6 <= ordinal < 135:
            inner = subject.get("inner_content_ids")
            if type(inner) is not list or len(inner) != 129:
                _fail("campaign semantic hash inner-content authority changed")
            observed = inner[ordinal - 6].get("content_id")
        elif ordinal == 135:
            observed = subject.get("subject_result_id")
        elif ordinal == 136:
            observed = hashlib.sha256(canonical_json_bytes(subject)).hexdigest()
        else:  # pragma: no cover - caller freezes the exact denominator
            _fail("campaign semantic hash ordinal escaped its manifest")
        _cid(observed, "campaign semantic observed SHA256")
        return [{"name": "observed_sha256", "value": observed}]
    if kind in {"INTEGRITY_CHECK", "PROTOCOL_CHECK"}:
        return [{"name": "check_passed", "value": True}]
    _fail("campaign semantic receipt kind escaped its auxiliary grammar")


def issue_subject_commit_receipt_v180r12r4(
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
    operation_id: str,
    subject_id: str,
    replay_subject_receipt_id: str,
    readback_transfer_receipt_id: str,
    subject_byte_count: int,
) -> dict[str, Any]:
    for value, label in (
        (protocol_id, "commit protocol ID"),
        (authorization_id, "commit authorization ID"),
        (attempt_id, "commit attempt ID"),
        (operation_id, "commit operation ID"),
        (subject_id, "commit subject ID"),
        (replay_subject_receipt_id, "commit replay receipt ID"),
        (readback_transfer_receipt_id, "commit readback transfer receipt ID"),
    ):
        _cid(value, label)
    _positive_int(subject_byte_count, "commit subject byte count")
    return _issue_evidence_document(
        schema="acfqp.campaign_subject_commit_receipt.v180r12r4",
        domain=domains.CONSTRUCTION_K7_SUBJECT_COMMIT_RECEIPT_V180R12R4E_DOMAIN,
        identity_field="subject_commit_receipt_id",
        payload={
            "scope": CAMPAIGN_SCOPE_KIND,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "operation_id": operation_id,
            "subject_id": subject_id,
            "replay_subject_receipt_id": replay_subject_receipt_id,
            "readback_transfer_receipt_id": readback_transfer_receipt_id,
            "subject_byte_count": subject_byte_count,
            "stable_readback_verified": True,
            "subject_committed": True,
        },
    )


def issue_window_closure_receipt_v180r12r4(
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
    operation_id: str,
    subject_commit_receipt_id: str,
    close_visibility_receipt_ids: Sequence[str],
) -> dict[str, Any]:
    close_ids = tuple(close_visibility_receipt_ids)
    for value, label in (
        (protocol_id, "window protocol ID"),
        (authorization_id, "window authorization ID"),
        (attempt_id, "window attempt ID"),
        (operation_id, "window operation ID"),
        (subject_commit_receipt_id, "window subject commit receipt ID"),
    ):
        _cid(value, label)
    if len(close_ids) != 2 or len(set(close_ids)) != 2:
        _fail("window closure requires two distinct visibility-close receipts")
    for value in close_ids:
        _cid(value, "window visibility-close receipt ID")
    return _issue_evidence_document(
        schema="acfqp.campaign_window_closure_receipt.v180r12r4",
        domain=domains.CONSTRUCTION_K7_WINDOW_CLOSURE_RECEIPT_V180R12R4E_DOMAIN,
        identity_field="window_closure_receipt_id",
        payload={
            "scope": CAMPAIGN_SCOPE_KIND,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "operation_id": operation_id,
            "subject_commit_receipt_id": subject_commit_receipt_id,
            "close_visibility_receipt_ids": list(close_ids),
            "window_closed": True,
            "all_registered_mounts_closed": True,
        },
    )


def _sorted_unique_cids(values: Sequence[str], label: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        _fail(f"{label} must be one exact sequence")
    result = tuple(values)
    for value in result:
        _cid(value, label)
    if not result or result != tuple(sorted(set(result))):
        _fail(f"{label} must be nonempty, sorted, and unique")
    return result


PRECOMPILED_SOURCE_ROW_FIELDS = frozenset(
    {"source_kind", "name", "source_path", "is_package", "marshal_byte_count", "marshal_sha256"}
)
NATIVE_ZERO_SOURCE_FACT_FIELDS = frozenset(
    {
        "schema", "schema_version", "prelaunch_launch_manifest_sha256",
        "precompiled_source_bundle_sha256", *PRECOMPILED_SOURCE_ROW_FIELDS,
        "native_zero_source_fact_id",
    }
)
NATIVE_ZERO_OPERATION_SITE_FACT_FIELDS = frozenset(
    {
        "schema", "schema_version", "attempt_id", "operation_id", "slot",
        "family", "ordinal", "phase", "actor_role", "instrumentation_site",
        "bound_source_fact_id", "comparison_axis_scope",
        "kernel_transition_calls", "not_an_os_syscall_count",
        "native_zero_operation_site_fact_id",
    }
)
NATIVE_ZERO_IMPORT_FACT_FIELDS = frozenset(
    {
        "schema", "schema_version", "precompiled_source_bundle_sha256",
        "module", "source_path", "source_fact_id", "allowed_actor_roles",
        "application_precompiled_loader_only", "stdlib_runtime_boundary_excluded",
        "native_zero_import_fact_id",
    }
)
PRECOMPILED_TARGET_SOURCE_PATHS = MappingProxyType(
    {
        "measurement": "scripts/run_v180r12r4_campaign_measurement.py",
        "supervisor": "scripts/supervise_v180r12r4_campaign_measurement.py",
        "worker": "scripts/work_v180r12r4_campaign_measurement.py",
    }
)
_OPERATION_SITE_TARGET_BY_ACTOR = MappingProxyType(
    {"OBSERVER": "measurement", "SUPERVISOR": "supervisor", "WORKER": "worker"}
)


def _native_zero_source_facts_v180r12r4(
    *,
    prelaunch_launch_manifest_sha256: str,
    precompiled_source_bundle_sha256: str,
    precompiled_source_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    manifest_sha = _cid(
        prelaunch_launch_manifest_sha256,
        "native-zero prelaunch launch-manifest SHA256",
    )
    bundle_sha = _cid(
        precompiled_source_bundle_sha256,
        "native-zero precompiled source-bundle SHA256",
    )
    if isinstance(precompiled_source_rows, (str, bytes)) or not isinstance(
        precompiled_source_rows, Sequence
    ):
        _fail("precompiled source rows must be one exact sequence")
    normalized: list[dict[str, Any]] = []
    coordinates: list[tuple[str, str]] = []
    for supplied in precompiled_source_rows:
        if type(supplied) is not dict or set(supplied) != PRECOMPILED_SOURCE_ROW_FIELDS:
            _fail("precompiled source row field set changed")
        row = dict(supplied)
        source_kind = row.get("source_kind")
        name = row.get("name")
        source_path = row.get("source_path")
        is_package = row.get("is_package")
        if (
            source_kind not in {"MODULE", "TARGET"}
            or type(name) is not str
            or not name
            or type(source_path) is not str
            or not source_path
            or source_path.startswith("/")
            or ".." in source_path.split("/")
            or type(row.get("marshal_byte_count")) is not int
            or row["marshal_byte_count"] <= 0
        ):
            _fail("precompiled source row value changed")
        _cid(row.get("marshal_sha256"), "precompiled source marshal SHA256")
        if source_kind == "MODULE":
            if (
                type(is_package) is not bool
                or any(not component.isidentifier() for component in name.split("."))
                or not (name == "acfqp" or name.startswith("acfqp."))
                or not source_path.startswith("src/acfqp/")
            ):
                _fail("precompiled module source row changed")
        elif (
            is_package is not False
            or name not in PRECOMPILED_TARGET_SOURCE_PATHS
            or source_path != PRECOMPILED_TARGET_SOURCE_PATHS[name]
        ):
            _fail("precompiled target source row changed")
        coordinates.append((source_kind, name))
        payload = {
            "schema": "acfqp.campaign_native_zero_source_fact.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "prelaunch_launch_manifest_sha256": manifest_sha,
            "precompiled_source_bundle_sha256": bundle_sha,
            **row,
        }
        normalized.append(
            {
                **payload,
                "native_zero_source_fact_id": domains.extension_content_id_v180r12r4e(
                    domains.CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_FACT_V180R12R4E_DOMAIN,
                    payload,
                ),
            }
        )
    if (
        not normalized
        or coordinates != sorted(set(coordinates))
        or {name for kind, name in coordinates if kind == "TARGET"}
        != set(PRECOMPILED_TARGET_SOURCE_PATHS)
        or not any(kind == "MODULE" for kind, _name in coordinates)
    ):
        _fail("precompiled source rows are incomplete, duplicated, or out of order")
    return tuple(normalized)


def _native_zero_operation_site_facts_v180r12r4(
    *,
    attempt_id: str,
    source_facts: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    target_source_ids = {
        row["name"]: row["native_zero_source_fact_id"]
        for row in source_facts
        if row["source_kind"] == "TARGET"
    }
    result: list[dict[str, Any]] = []
    for spec in build_campaign_operation_schedule_v180r12r4(attempt_id):
        target = _OPERATION_SITE_TARGET_BY_ACTOR[spec.actor_role]
        payload = {
            "schema": "acfqp.campaign_native_zero_operation_site_fact.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "attempt_id": attempt_id,
            "operation_id": spec.operation_id,
            "slot": spec.slot,
            "family": spec.family,
            "ordinal": spec.ordinal,
            "phase": spec.phase,
            "actor_role": spec.actor_role,
            "instrumentation_site": (
                f"{target}:{spec.phase}:{spec.slot}:{spec.family}:{spec.ordinal}"
            ),
            "bound_source_fact_id": target_source_ids[target],
            "comparison_axis_scope": (
                "REGISTERED_PLANNING_COMPARISON_GROUND_KERNEL_TRANSITION_AXIS"
            ),
            "kernel_transition_calls": 0,
            "not_an_os_syscall_count": True,
        }
        result.append(
            {
                **payload,
                "native_zero_operation_site_fact_id": (
                    domains.extension_content_id_v180r12r4e(
                        domains.CONSTRUCTION_K7_NATIVE_ZERO_OPERATION_SITE_FACT_V180R12R4E_DOMAIN,
                        payload,
                    )
                ),
            }
        )
    if len(result) != 314 or len(
        {row["native_zero_operation_site_fact_id"] for row in result}
    ) != 314:
        _fail("native-zero operation-site fact denominator changed")
    return tuple(result)


def issue_native_zero_source_manifest_v180r12r4(
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
    operation_manifest_id: str,
    prelaunch_launch_manifest_sha256: str,
    precompiled_source_bundle_sha256: str,
    precompiled_source_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    for value, label in (
        (protocol_id, "source-manifest protocol ID"),
        (authorization_id, "source-manifest authorization ID"),
        (attempt_id, "source-manifest attempt ID"),
        (operation_manifest_id, "source-manifest operation manifest ID"),
    ):
        _cid(value, label)
    exact_operation_manifest = campaign_operation_manifest_v180r12r4(attempt_id)
    if operation_manifest_id != exact_operation_manifest[
        "campaign_operation_manifest_id"
    ]:
        _fail("native-zero source manifest operation authority changed")
    source_facts = _native_zero_source_facts_v180r12r4(
        prelaunch_launch_manifest_sha256=prelaunch_launch_manifest_sha256,
        precompiled_source_bundle_sha256=precompiled_source_bundle_sha256,
        precompiled_source_rows=precompiled_source_rows,
    )
    site_facts = _native_zero_operation_site_facts_v180r12r4(
        attempt_id=attempt_id,
        source_facts=source_facts,
    )
    return _issue_evidence_document(
        schema="acfqp.campaign_native_zero_source_manifest.v180r12r4",
        domain=domains.CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_MANIFEST_V180R12R4E_DOMAIN,
        identity_field="native_zero_source_manifest_id",
        payload={
            "scope": CAMPAIGN_SCOPE_KIND,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "operation_manifest_id": operation_manifest_id,
            "prelaunch_launch_manifest_sha256": prelaunch_launch_manifest_sha256,
            "precompiled_source_bundle_sha256": precompiled_source_bundle_sha256,
            "source_fact_rows": list(source_facts),
            "source_fact_ids": [
                row["native_zero_source_fact_id"] for row in source_facts
            ],
            "registered_operation_site_fact_rows": list(site_facts),
            "registered_operation_site_fact_ids": [
                row["native_zero_operation_site_fact_id"] for row in site_facts
            ],
            "unregistered_operation_site_fact_ids": [],
            "registered_planning_operation_site_manifest_complete": True,
            "unregistered_or_dynamic_sites_forbidden": True,
            "third_party_precompiled_sources_in_trusted_runtime_boundary": True,
            "open_world_operation_site_absence_claimed": False,
        },
    )


def issue_native_zero_import_inventory_v180r12r4(
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if type(source_manifest) is not dict:
        _fail("native-zero import inventory requires the exact source manifest")
    source_manifest_id = _cid(
        source_manifest.get("native_zero_source_manifest_id"),
        "import-inventory source manifest ID",
    )
    payload_for_id = dict(source_manifest)
    payload_for_id.pop("native_zero_source_manifest_id", None)
    if source_manifest_id != domains.extension_content_id_v180r12r4e(
        domains.CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_MANIFEST_V180R12R4E_DOMAIN,
        payload_for_id,
    ):
        _fail("native-zero import inventory source manifest is re-signed")
    for value, label in (
        (protocol_id, "import-inventory protocol ID"),
        (authorization_id, "import-inventory authorization ID"),
        (attempt_id, "import-inventory attempt ID"),
    ):
        _cid(value, label)
    if (
        source_manifest.get("protocol_id") != protocol_id
        or source_manifest.get("authorization_id") != authorization_id
        or source_manifest.get("attempt_id") != attempt_id
    ):
        _fail("native-zero import/source context changed")
    source_rows = source_manifest.get("source_fact_rows")
    if type(source_rows) is not list:
        _fail("native-zero import source rows changed")
    normalized_source_rows: list[dict[str, Any]] = []
    for source in source_rows:
        if type(source) is not dict or set(source) != NATIVE_ZERO_SOURCE_FACT_FIELDS:
            _fail("native-zero import source fact schema changed")
        normalized_source_rows.append(
            {key: source[key] for key in PRECOMPILED_SOURCE_ROW_FIELDS}
        )
    exact_source_manifest = issue_native_zero_source_manifest_v180r12r4(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        attempt_id=attempt_id,
        operation_manifest_id=source_manifest.get("operation_manifest_id"),
        prelaunch_launch_manifest_sha256=source_manifest.get(
            "prelaunch_launch_manifest_sha256"
        ),
        precompiled_source_bundle_sha256=source_manifest.get(
            "precompiled_source_bundle_sha256"
        ),
        precompiled_source_rows=normalized_source_rows,
    )
    if source_manifest != exact_source_manifest:
        _fail("native-zero import source manifest facts changed")
    import_facts: list[dict[str, Any]] = []
    for source in source_rows:
        if type(source) is not dict or source.get("source_kind") != "MODULE":
            continue
        payload = {
            "schema": "acfqp.campaign_native_zero_import_fact.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "precompiled_source_bundle_sha256": source_manifest[
                "precompiled_source_bundle_sha256"
            ],
            "module": source["name"],
            "source_path": source["source_path"],
            "source_fact_id": source["native_zero_source_fact_id"],
            "allowed_actor_roles": ["OBSERVER", "SUPERVISOR", "WORKER"],
            "application_precompiled_loader_only": True,
            "stdlib_runtime_boundary_excluded": True,
        }
        import_facts.append(
            {
                **payload,
                "native_zero_import_fact_id": domains.extension_content_id_v180r12r4e(
                    domains.CONSTRUCTION_K7_NATIVE_ZERO_IMPORT_FACT_V180R12R4E_DOMAIN,
                    payload,
                ),
            }
        )
    if not import_facts or [row["module"] for row in import_facts] != sorted(
        {row["module"] for row in import_facts}
    ):
        _fail("native-zero import fact rows are incomplete or duplicated")
    return _issue_evidence_document(
        schema="acfqp.campaign_native_zero_import_inventory.v180r12r4",
        domain=domains.CONSTRUCTION_K7_NATIVE_ZERO_IMPORT_INVENTORY_V180R12R4E_DOMAIN,
        identity_field="native_zero_import_inventory_id",
        payload={
            "scope": CAMPAIGN_SCOPE_KIND,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "source_manifest_id": source_manifest_id,
            "precompiled_source_bundle_sha256": source_manifest[
                "precompiled_source_bundle_sha256"
            ],
            "import_fact_rows": import_facts,
            "import_fact_ids": [
                row["native_zero_import_fact_id"] for row in import_facts
            ],
            "unregistered_import_fact_ids": [],
            "dynamic_import_fact_ids": [],
            "prelaunch_sealed_application_import_allowlist_complete": True,
            "runtime_role_exit_origin_guard_required": True,
            "stdlib_imports_in_trusted_runtime_boundary": True,
            "third_party_imports_in_trusted_runtime_boundary": True,
            "trusted_runtime_boundary_namespaces": [
                "packaging",
                "stdlib",
                "tomli",
            ],
            "open_world_import_absence_claimed": False,
        },
    )


def issue_campaign_execution_closure_v180r12r4(
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
    subject_id: str,
    window_closed_event_id: str,
    window_closure_receipt_id: str,
    operation_manifest_id: str,
    source_manifest_id: str,
    import_inventory_id: str,
    precompiled_source_bundle_sha256: str,
) -> dict[str, Any]:
    for value, label in (
        (protocol_id, "execution-closure protocol ID"),
        (authorization_id, "execution-closure authorization ID"),
        (attempt_id, "execution-closure attempt ID"),
        (subject_id, "execution-closure subject ID"),
        (window_closed_event_id, "execution-closure window event ID"),
        (window_closure_receipt_id, "execution-closure window receipt ID"),
        (operation_manifest_id, "execution-closure operation manifest ID"),
        (source_manifest_id, "execution-closure source manifest ID"),
        (import_inventory_id, "execution-closure import inventory ID"),
        (
            precompiled_source_bundle_sha256,
            "execution-closure precompiled source-bundle SHA256",
        ),
    ):
        _cid(value, label)
    return _issue_evidence_document(
        schema="acfqp.campaign_execution_closure.v180r12r4",
        domain=domains.CONSTRUCTION_K7_CAMPAIGN_EXECUTION_CLOSURE_V180R12R4E_DOMAIN,
        identity_field="campaign_execution_closure_id",
        payload={
            "scope": CAMPAIGN_SCOPE_KIND,
            "scope_model": CAMPAIGN_SCOPE_MODEL,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "subject_id": subject_id,
            "window_closed_event_id": window_closed_event_id,
            "window_closure_receipt_id": window_closure_receipt_id,
            "operation_manifest_id": operation_manifest_id,
            "source_manifest_id": source_manifest_id,
            "import_inventory_id": import_inventory_id,
            "precompiled_source_bundle_sha256": precompiled_source_bundle_sha256,
            "comparison_axis": KERNEL_TRANSITION_CALLS,
            "kernel_transition_calls": 0,
            "registered_planning_operation_site_fact_count": 314,
            "kernel_transition_operation_site_fact_ids": [],
            "kernel_transition_import_fact_ids": [],
            "unregistered_operation_site_fact_ids": [],
            "unregistered_import_fact_ids": [],
            "registered_planning_comparison_ground_kernel_axis_only": True,
            "prelaunch_sealed_application_import_allowlist_only": True,
            "runtime_role_exit_origin_guard_required": True,
            "runtime_role_exit_origin_guard_status": (
                "PENDING_INDEPENDENT_MEASUREMENT_LAUNCH_RECEIPT"
            ),
            "not_an_os_syscall_count": True,
            "unregistered_or_dynamic_sites_forbidden": True,
            "closed_registered_planning_operation_window_only": True,
            "open_world_absence_claimed": False,
            "execution_window_closed": True,
        },
    )


def _document_identity(document: Mapping[str, Any]) -> tuple[str, str]:
    schema = document.get("schema")
    if type(schema) is not str or schema not in _EVIDENCE_SCHEMA_DESCRIPTOR:
        _fail("campaign evidence document schema is unregistered")
    domain, identity_field = _EVIDENCE_SCHEMA_DESCRIPTOR[schema]
    identity = _cid(document.get(identity_field), f"{schema} identity")
    payload = dict(document)
    payload.pop(identity_field, None)
    expected = domains.extension_content_id_v180r12r4e(domain, payload)
    if identity != expected:
        _fail("campaign evidence document identity changed under canonical replay")
    return identity, schema


@dataclass(frozen=True, slots=True)
class CampaignEvidenceInventoryV180R12R4:
    rows: tuple[tuple[str, bytes], ...]

    def __post_init__(self) -> None:
        if type(self.rows) is not tuple or len(self.rows) != CAMPAIGN_EVIDENCE_DOCUMENT_COUNT:
            _fail("campaign evidence inventory must contain exactly 328 documents")
        ids: list[str] = []
        schemas: list[str] = []
        for supplied_id, raw in self.rows:
            _cid(supplied_id, "campaign evidence inventory key")
            canonical, document = _canonical_object(raw, "campaign evidence document")
            if canonical != raw:
                _fail("campaign evidence document bytes changed")
            actual_id, schema = _document_identity(document)
            if supplied_id != actual_id:
                _fail("campaign evidence inventory key/document identity mismatch")
            ids.append(actual_id)
            schemas.append(schema)
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            _fail("campaign evidence inventory IDs must be sorted and unique")
        actual_counts = {schema: schemas.count(schema) for schema in set(schemas)}
        if actual_counts != dict(EVIDENCE_DOCUMENT_TYPE_COUNTS):
            _fail("campaign evidence inventory exact typed denominator changed")

    @classmethod
    def from_mapping(
        cls, documents_by_id: Mapping[str, bytes | dict[str, Any]]
    ) -> "CampaignEvidenceInventoryV180R12R4":
        if not isinstance(documents_by_id, Mapping):
            _fail("campaign evidence documents must be one exact ID mapping")
        rows = tuple(
            (key, _canonical_object(value, "campaign evidence document")[0])
            for key, value in sorted(documents_by_id.items())
        )
        return cls(rows)

    @classmethod
    def from_documents(
        cls, documents: Sequence[bytes | dict[str, Any]]
    ) -> "CampaignEvidenceInventoryV180R12R4":
        if isinstance(documents, (str, bytes)) or not isinstance(documents, Sequence):
            _fail("campaign embedded evidence documents must be one exact sequence")
        mapping: dict[str, bytes | dict[str, Any]] = {}
        for value in documents:
            _raw, document = _canonical_object(value, "campaign evidence document")
            identity, _schema = _document_identity(document)
            if identity in mapping:
                _fail("campaign embedded evidence document identity repeats")
            mapping[identity] = value
        return cls.from_mapping(mapping)

    @property
    def documents_by_id(self) -> dict[str, dict[str, Any]]:
        return {
            identity: _canonical_object(raw, "campaign evidence document")[1]
            for identity, raw in self.rows
        }

    @property
    def documents(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            _canonical_object(raw, "campaign evidence document")[1]
            for _identity, raw in self.rows
        )

    def one(self, schema: str) -> dict[str, Any]:
        rows = [row for row in self.documents if row.get("schema") == schema]
        if len(rows) != 1:
            _fail(f"campaign evidence inventory requires exactly one {schema}")
        return rows[0]


@dataclass(frozen=True, slots=True)
class MountVisibilityReplayV180R12R4:
    peak_mounted_bytes: int
    open_event_ids: tuple[str, ...]
    open_evidence_ids: tuple[str, ...]
    close_event_ids: tuple[str, ...]
    close_evidence_ids: tuple[str, ...]
    payload_ids: tuple[str, ...]


def replay_mount_visibility_intervals_v180r12r4(
    rows: Sequence[Mapping[str, Any]],
) -> MountVisibilityReplayV180R12R4:
    """Replay unique payload OPEN/CLOSE intervals and sum simultaneous bytes."""

    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        _fail("mount visibility interval rows must be one exact sequence")
    active_by_payload: dict[str, tuple[str, int]] = {}
    payload_by_operation: dict[str, str] = {}
    seen_payloads: set[str] = set()
    peak = 0
    open_event_ids: list[str] = []
    open_evidence_ids: list[str] = []
    close_event_ids: list[str] = []
    close_evidence_ids: list[str] = []
    payload_ids: list[str] = []
    for index, row in enumerate(rows):
        if type(row) is not dict or set(row) != {
            "event_kind",
            "operation_id",
            "payload_id",
            "measured_value",
            "byte_count",
            "event_id",
            "evidence_id",
        }:
            _fail("mount visibility interval row field set changed")
        operation_id = _cid(row.get("operation_id"), "mount operation ID")
        payload_id = _cid(row.get("payload_id"), "mount payload ID")
        event_id = _cid(row.get("event_id"), "mount event ID")
        evidence_id = _cid(row.get("evidence_id"), "mount evidence ID")
        byte_count = _positive_int(row.get("byte_count"), "mount payload byte count")
        kind = row.get("event_kind")
        if kind == "MOUNT_VISIBILITY_OPEN":
            if (
                payload_id in seen_payloads
                or payload_id in active_by_payload
                or operation_id in payload_by_operation
            ):
                _fail("mount visibility repeats an opened payload identity")
            active_by_payload[payload_id] = (operation_id, byte_count)
            payload_by_operation[operation_id] = payload_id
            seen_payloads.add(payload_id)
            payload_ids.append(payload_id)
            open_event_ids.append(event_id)
            open_evidence_ids.append(evidence_id)
            aggregate_visible_bytes = sum(
                value for _operation, value in active_by_payload.values()
            )
            if row.get("measured_value") != aggregate_visible_bytes:
                _fail("mount OPEN measured bytes differ from aggregate active visibility")
            peak = max(peak, aggregate_visible_bytes)
        elif kind == "MOUNT_VISIBILITY_CLOSE":
            if row.get("measured_value") is not None:
                _fail("mount CLOSE cannot carry measured bytes")
            expected_payload = payload_by_operation.get(operation_id)
            if expected_payload is None:
                _fail("mount visibility CLOSE has no matching OPEN")
            if expected_payload != payload_id:
                _fail("mount visibility CLOSE payload identity drifted")
            _active_operation, active_bytes = active_by_payload.get(
                payload_id, (None, None)
            )
            if active_bytes != byte_count:
                _fail("mount visibility CLOSE payload bytes drifted")
            del active_by_payload[payload_id]
            del payload_by_operation[operation_id]
            close_event_ids.append(event_id)
            close_evidence_ids.append(evidence_id)
        else:
            _fail(f"mount visibility interval row {index} has an unknown kind")
    if active_by_payload or payload_by_operation:
        _fail("mount visibility has an OPEN without a matching CLOSE")
    if not seen_payloads:
        _fail("mount visibility interval replay is empty")
    return MountVisibilityReplayV180R12R4(
        peak,
        tuple(open_event_ids),
        tuple(open_evidence_ids),
        tuple(close_event_ids),
        tuple(close_evidence_ids),
        tuple(payload_ids),
    )


_DIRECT_EVENT_SCHEMA = {
    "ATTEMPT_OPEN": "acfqp.campaign_attempt_record.v180r12r4",
    "INPUT_READ_OUTCOME": "acfqp.campaign_io_transfer_receipt.v180r12r4",
    "STAGE_WRITE_OUTCOME": "acfqp.campaign_io_transfer_receipt.v180r12r4",
    "MOUNT_VISIBILITY_OPEN": "acfqp.campaign_fd_visibility_receipt.v180r12r4",
    "MOUNT_VISIBILITY_CLOSE": "acfqp.campaign_fd_visibility_receipt.v180r12r4",
    "SEMANTIC_HASH_OUTCOME": (
        "acfqp.campaign_semantic_operation_receipt.v180r12r4"
    ),
    "INTEGRITY_CHECK_OUTCOME": (
        "acfqp.campaign_semantic_operation_receipt.v180r12r4"
    ),
    "PROTOCOL_CHECK_OUTCOME": (
        "acfqp.campaign_semantic_operation_receipt.v180r12r4"
    ),
    "PROCESS_BIRTH_OUTCOME": "acfqp.campaign_pidfd_birth_receipt.v180r12r4",
    "PROCESS_REAP": "acfqp.campaign_pidfd_reap_receipt.v180r12r4",
    "SUBJECT_WRITE_OUTCOME": "acfqp.campaign_io_transfer_receipt.v180r12r4",
    "SUBJECT_COMMIT": "acfqp.campaign_subject_commit_receipt.v180r12r4",
    "WINDOW_CLOSED": "acfqp.campaign_window_closure_receipt.v180r12r4",
    "CGROUP_OBSERVED": "acfqp.campaign_cgroup_observation_receipt.v180r12r4",
}
_DIRECT_EVIDENCE_SCHEMAS = frozenset(_DIRECT_EVENT_SCHEMA.values())


@dataclass(frozen=True, slots=True)
class CampaignEvidenceFactsV180R12R4:
    inventory: CampaignEvidenceInventoryV180R12R4
    mount_replay: MountVisibilityReplayV180R12R4
    subject_byte_count: int
    operation_manifest_id: str
    source_manifest_id: str
    import_inventory_id: str
    execution_closure_id: str


def _validate_production_runtime_placement_chain_v180r12r4(
    *,
    topology: Mapping[str, Any],
    supervisor_birth: Mapping[str, Any],
    worker_birth: Mapping[str, Any],
) -> None:
    """Replay the exact T1 -> T2 -> supervisor-T3 placement chain."""

    t1 = topology.get("production_runtime_placement_t1")
    t2 = topology.get("production_runtime_placement_t2")
    t3 = supervisor_birth.get("production_runtime_placement_t3")
    if not (
        type(t1) is dict
        and frozenset(t1) == PRODUCTION_RUNTIME_PLACEMENT_T1_FIELDS
        and type(t2) is dict
        and frozenset(t2) == PRODUCTION_RUNTIME_PLACEMENT_T2_FIELDS
        and type(t3) is dict
        and frozenset(t3) == PRODUCTION_RUNTIME_PLACEMENT_T3_FIELDS
        and worker_birth.get("production_runtime_placement_t3") is None
    ):
        _fail("campaign runtime placement receipt keysets or observer ownership changed")
    token = _cid(t1.get("token"), "production placement token")
    expected_unit = f"acfqp-v180r12r4-measurement-{token}.service"
    service = t1.get("source_service_fd_fact")
    parent = t1.get("delegated_parent_fd_fact")
    mount = t1.get("cgroup2_mount_fd_fact")
    fd_fields = {
        "fd", "role", "access", "path", "device", "inode", "mode",
        "owner_uid", "owner_gid", "nlink",
    }
    if not (
        t1.get("schema") == PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA
        and t1.get("target") == "measurement"
        and t1.get("unit_name") == expected_unit
        and t1.get("slice") == "app.slice"
        and t1.get("source_membership") == t1.get("expected_source_membership")
        and type(t1.get("self_pid")) is int
        and t1["self_pid"] > 0
        and t1.get("self_pid_in_source_cgroup_procs") is True
        and t1.get("nearest_common_ancestor_is_app_slice") is True
        and t1.get("parent_cgroup_procs_o_wronly_openable") is True
        and t1.get("planned_measurement_root_absent") is True
        and t1.get("t1_complete_before_child_popen") is True
        and all(type(row) is dict and set(row) == fd_fields for row in (parent, mount, service))
        and (parent.get("fd"), parent.get("role"), parent.get("access"))
        == (250, "DELEGATED_CGROUP_PARENT_DIRECTORY", "O_RDONLY")
        and (mount.get("fd"), mount.get("role"), mount.get("access"))
        == (251, "CGROUP2_MOUNT_DIRECTORY", "O_PATH")
        and (service.get("fd"), service.get("role"), service.get("access"))
        == (252, "SOURCE_SYSTEMD_SERVICE_DIRECTORY", "O_RDONLY")
        and t2.get("schema") == PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA
        and t2.get("boundary") == "T2_BEFORE_SCIENTIFIC_ATTEMPT_O_EXCL"
        and t2.get("target") == "measurement"
        and t2.get("token") == token
        and t2.get("unit_name") == expected_unit
        and t2.get("source_membership") == t1.get("source_membership")
        and t2.get("expected_source_membership")
        == t1.get("expected_source_membership")
        and type(t2.get("self_pid")) is int
        and t2["self_pid"] > 0
        and t2["self_pid"] != t1.get("self_pid")
        and t2.get("self_pid_in_source_cgroup_procs") is True
        and type(t2.get("parent_pid")) is int
        and t2["parent_pid"] > 0
        and t2.get("parent_pid") == t1.get("self_pid")
        and t2.get("parent_pid_in_source_cgroup_procs") is True
        and t2.get("source_service_fd") == 252
        and t2.get("source_service_device") == service.get("device")
        and t2.get("source_service_inode") == service.get("inode")
        and t2.get("cgroup_namespace_inode") == t1.get("cgroup_namespace_inode")
        and t2.get("nearest_common_ancestor_path")
        == t1.get("nearest_common_ancestor_path")
        and t2.get("nearest_common_ancestor_is_app_slice") is True
        and t2.get("parent_cgroup_procs_o_wronly_openable") is True
        and t2.get("planned_measurement_root_state") == "ABSENT"
        and t2.get("scientific_progress_present_paths") == []
        and t2.get("scientific_progress_absent") is True
    ):
        _fail("campaign T1/T2 production placement chain changed")

    before = t3.get("before_getrandom")
    preclone = t3.get("immediately_before_clone3")
    root = topology.get("measurement_root")
    supervisor = topology.get("supervisor_leaf")
    worker = topology.get("worker_leaf")
    if not (
        t3.get("schema") == PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA
        and t3.get("target") == "measurement"
        and t3.get("token") == token
        and t3.get("unit_name") == expected_unit
        and t3.get("stable_across_boundaries") is True
        and type(before) is dict
        and frozenset(before) == PRODUCTION_RUNTIME_PLACEMENT_T3_CHECKPOINT_FIELDS
        and type(preclone) is dict
        and frozenset(preclone) == PRODUCTION_RUNTIME_PLACEMENT_T3_CHECKPOINT_FIELDS
        and before.get("schema") == PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA
        and preclone.get("schema") == PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA
        and before.get("boundary") == "T3_BEFORE_GETRANDOM"
        and preclone.get("boundary") == "T3_IMMEDIATELY_BEFORE_CLONE3"
        and canonical_json_bytes(before)
        == canonical_json_bytes({**preclone, "boundary": "T3_BEFORE_GETRANDOM"})
        and all(
            canonical_json_bytes(before.get(field_name))
            == canonical_json_bytes(t2.get(field_name))
            and canonical_json_bytes(preclone.get(field_name))
            == canonical_json_bytes(t2.get(field_name))
            for field_name in _PLACEMENT_STABLE_SOURCE_FIELDS
        )
        and before.get("source_service_fd") == 252
        and before.get("planned_measurement_root_state") == "PRESENT"
        and type(root) is dict
        and type(supervisor) is dict
        and type(worker) is dict
        and before.get("measurement_root_device") == root.get("device")
        and before.get("measurement_root_inode") == root.get("inode")
        and before.get("supervisor_leaf_device") == supervisor.get("device")
        and before.get("supervisor_leaf_inode") == supervisor.get("inode")
        and before.get("worker_leaf_device") == worker.get("device")
        and before.get("worker_leaf_inode") == worker.get("inode")
        and before.get("target_cgroup_role") == "SUPERVISOR"
        and before.get("target_cgroup_fd") == supervisor.get("directory_fd")
        and before.get("target_cgroup_device") == supervisor.get("device")
        and before.get("target_cgroup_inode") == supervisor.get("inode")
        and before.get("target_cgroup_path") == supervisor.get("path")
        and before.get("target_membership_path") == supervisor.get("membership_path")
        and before.get("root_empty_before_birth") is True
        and before.get("supervisor_leaf_empty_before_birth") is True
        and before.get("worker_leaf_empty_before_birth") is True
        and before.get("programmed_limits_revalidated") is True
        and supervisor_birth.get("target_cgroup_fd") == supervisor.get("directory_fd")
        and supervisor_birth.get("target_cgroup_device") == supervisor.get("device")
        and supervisor_birth.get("target_cgroup_inode") == supervisor.get("inode")
        and supervisor_birth.get("target_cgroup_path") == supervisor.get("path")
    ):
        _fail("campaign T2/T3 production placement/topology chain changed")


def _validate_evidence_inventory_v180r12r4(
    state: CampaignLedgerStateV180R12R4,
    subject_id: str,
    inventory: CampaignEvidenceInventoryV180R12R4,
    *,
    expected_source_manifest_id: str,
    expected_import_inventory_id: str,
) -> CampaignEvidenceFactsV180R12R4:
    docs = inventory.documents_by_id
    source_id = _cid(expected_source_manifest_id, "expected native-zero source manifest ID")
    import_id = _cid(expected_import_inventory_id, "expected native-zero import inventory ID")
    operation_manifest = inventory.one("acfqp.campaign_operation_manifest.v180r12r4")
    exact_manifest = campaign_operation_manifest_v180r12r4(state.attempt_id)
    if operation_manifest != exact_manifest:
        _fail("campaign operation manifest differs from the attempt-derived authority")
    operation_manifest_id = exact_manifest["campaign_operation_manifest_id"]
    attempt_record = inventory.one("acfqp.campaign_attempt_record.v180r12r4")
    attempt_record_id = _cid(
        attempt_record.get("campaign_attempt_record_id"),
        "campaign attempt record ID",
    )
    authorization_evidence_id = _cid(
        attempt_record.get("authorization_evidence_id"),
        "campaign attempt authorization-evidence ID",
    )
    for field_name in (
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
    ):
        _cid(
            attempt_record.get(field_name),
            f"campaign attempt {field_name}",
        )
    if (
        attempt_record.get("protocol_id") != state.protocol_id
        or attempt_record.get("authorization_id") != state.authorization_id
        or attempt_record.get("attempt_id") != state.attempt_id
        or attempt_record.get("operation_manifest_id") != operation_manifest_id
        or attempt_record.get("one_shot_attempt_opened") is not True
        or "cgroup_topology_receipt_id" in attempt_record
    ):
        _fail("campaign attempt record pre-cgroup authority changed")

    subject = validate_campaign_subject_result_document_v180r12r4(
        inventory.one("acfqp.campaign_measurement_subject_result.v180r12r4"),
        expected_protocol_id=state.protocol_id,
        expected_authorization_id=state.authorization_id,
        expected_attempt_id=state.attempt_id,
    )
    if (
        subject.get("subject_result_id") != subject_id
        or subject.get("campaign_attempt_record_id") != attempt_record_id
        or subject.get("authorization_evidence_id")
        != authorization_evidence_id
        or subject.get("prelaunch_materialization_terminal_id")
        != attempt_record.get("prelaunch_materialization_terminal_id")
        or subject.get("prelaunch_launch_manifest_sha256")
        != attempt_record.get("prelaunch_launch_manifest_sha256")
        or subject.get("prelaunch_launch_rule_id")
        != attempt_record.get("prelaunch_launch_rule_id")
        or subject.get("measurement_launch_attempt_id")
        != attempt_record.get("measurement_launch_attempt_id")
    ):
        _fail("campaign subject provenance differs from the pre-cgroup attempt")
    expected_attempt_id = (
        identity_domains.derive_campaign_measurement_attempt_id_v180r12r4(
            protocol_id=state.protocol_id,
            authorization_id=state.authorization_id,
            authorization_evidence_id=authorization_evidence_id,
            campaign_measurement_execution_slot_id=subject["execution_slot_id"],
            logical_occurrence_id=subject["logical_occurrence_id"],
            execution_nonce=subject["execution_nonce"],
        )
    )
    if state.attempt_id != expected_attempt_id:
        _fail("campaign attempt ID differs from its six-input provenance")
    subject_byte_count = _positive_int(
        subject.get("subject_byte_count"), "campaign subject byte count"
    )
    replay_subject = inventory.one("acfqp.campaign_replay_subject_receipt.v180r12r4")
    if (
        replay_subject.get("subject_result_id") != subject_id
        or replay_subject.get("subject_byte_count") != subject_byte_count
        or replay_subject.get("campaign_attempt_record_id") != attempt_record_id
    ):
        _fail("campaign subject-result/replay-receipt byte join changed")

    source_manifest = inventory.one(
        "acfqp.campaign_native_zero_source_manifest.v180r12r4"
    )
    import_inventory = inventory.one(
        "acfqp.campaign_native_zero_import_inventory.v180r12r4"
    )
    source_fact_rows = source_manifest.get("source_fact_rows")
    if type(source_fact_rows) is not list:
        _fail("native-zero source fact population changed")
    normalized_source_rows: list[dict[str, Any]] = []
    for source_fact in source_fact_rows:
        if (
            type(source_fact) is not dict
            or set(source_fact) != NATIVE_ZERO_SOURCE_FACT_FIELDS
        ):
            _fail("native-zero source fact schema changed")
        normalized_source_rows.append(
            {key: source_fact[key] for key in PRECOMPILED_SOURCE_ROW_FIELDS}
        )
    exact_source_manifest = issue_native_zero_source_manifest_v180r12r4(
        protocol_id=state.protocol_id,
        authorization_id=state.authorization_id,
        attempt_id=state.attempt_id,
        operation_manifest_id=operation_manifest_id,
        prelaunch_launch_manifest_sha256=attempt_record[
            "prelaunch_launch_manifest_sha256"
        ],
        precompiled_source_bundle_sha256=source_manifest.get(
            "precompiled_source_bundle_sha256"
        ),
        precompiled_source_rows=normalized_source_rows,
    )
    exact_import_inventory = issue_native_zero_import_inventory_v180r12r4(
        protocol_id=state.protocol_id,
        authorization_id=state.authorization_id,
        attempt_id=state.attempt_id,
        source_manifest=exact_source_manifest,
    )
    if (
        source_manifest.get("native_zero_source_manifest_id") != source_id
        or import_inventory.get("native_zero_import_inventory_id") != import_id
        or source_manifest != exact_source_manifest
        or import_inventory != exact_import_inventory
        or source_manifest.get("operation_manifest_id") != operation_manifest_id
        or import_inventory.get("source_manifest_id") != source_id
        or source_manifest.get("unregistered_operation_site_fact_ids") != []
        or source_manifest.get(
            "registered_planning_operation_site_manifest_complete"
        )
        is not True
        or source_manifest.get("unregistered_or_dynamic_sites_forbidden") is not True
        or source_manifest.get(
            "third_party_precompiled_sources_in_trusted_runtime_boundary"
        )
        is not True
        or source_manifest.get("open_world_operation_site_absence_claimed") is not False
        or import_inventory.get("unregistered_import_fact_ids") != []
        or import_inventory.get("dynamic_import_fact_ids") != []
        or import_inventory.get(
            "prelaunch_sealed_application_import_allowlist_complete"
        )
        is not True
        or import_inventory.get("runtime_role_exit_origin_guard_required") is not True
        or import_inventory.get("stdlib_imports_in_trusted_runtime_boundary") is not True
        or import_inventory.get("third_party_imports_in_trusted_runtime_boundary")
        is not True
        or import_inventory.get("trusted_runtime_boundary_namespaces")
        != ["packaging", "stdlib", "tomli"]
        or import_inventory.get("open_world_import_absence_claimed") is not False
    ):
        _fail("native-zero source/import preregistration closure changed")

    direct_events = tuple(
        row for row in state.events if row.payload["evidence_id"] is not None
    )
    direct_ids = tuple(row.payload["evidence_id"] for row in direct_events)
    if len(direct_ids) != SUCCESS_EVENT_EVIDENCE_COUNT or len(set(direct_ids)) != len(
        direct_ids
    ):
        _fail("campaign direct event evidence IDs must be exactly 317 and unique")
    direct_inventory_ids = {
        identity
        for identity, document in docs.items()
        if document.get("schema") in _DIRECT_EVIDENCE_SCHEMAS
    }
    if set(direct_ids) != direct_inventory_ids:
        _fail("campaign event evidence does not bijectively cover direct typed receipts")

    semantic_ids: list[str] = []
    semantic_ordinals = {
        "SEMANTIC_HASH": 0,
        "INTEGRITY_CHECK": 0,
        "PROTOCOL_CHECK": 0,
    }
    operation_specs_by_id = {
        row["operation_id"]: row for row in exact_manifest["operations"]
    }
    io_receipts_by_operation: dict[str, dict[str, Any]] = {}
    mount_rows: list[dict[str, Any]] = []
    birth_ids_by_role: dict[str, str] = {}
    reap_ids_by_role: dict[str, str] = {}
    for event in direct_events:
        evidence_id = event.payload["evidence_id"]
        assert evidence_id is not None
        document = docs.get(evidence_id)
        if document is None:
            _fail("campaign event references an unknown evidence document")
        expected_schema = _DIRECT_EVENT_SCHEMA[event.event_kind]
        if document.get("schema") != expected_schema:
            _fail("campaign event evidence type changed")
        if "operation_id" in document and document.get("operation_id") != event.operation_id:
            _fail("campaign event/evidence operation join changed")
        if "measured_value" in document and document.get("measured_value") != event.payload[
            "measured_value"
        ]:
            _fail("campaign event/evidence measured-value join changed")
        for field_name, expected_value in (
            ("protocol_id", state.protocol_id),
            ("authorization_id", state.authorization_id),
            ("attempt_id", state.attempt_id),
        ):
            if field_name in document and document.get(field_name) != expected_value:
                _fail("campaign event/evidence context join changed")
        if event.event_kind == "ATTEMPT_OPEN":
            if (
                document.get("operation_manifest_id") != operation_manifest_id
                or document.get("one_shot_attempt_opened") is not True
            ):
                _fail("campaign attempt record authority changed")
        elif event.event_kind in {
            "INPUT_READ_OUTCOME",
            "STAGE_WRITE_OUTCOME",
            "SUBJECT_WRITE_OUTCOME",
        }:
            chunks = document.get("returned_chunk_byte_counts")
            measured = event.payload["measured_value"]
            if (
                document.get("event_kind") != event.event_kind
                or type(chunks) is not list
                or not chunks
                or any(type(value) is not int or value <= 0 for value in chunks)
                or sum(chunks) != measured
                or document.get("returned_chunk_count") != len(chunks)
                or document.get("returned_byte_count") != measured
                or document.get("transfer_complete") is not True
                or document.get("source_evidence_id") not in docs
                or document.get("target_evidence_id") not in docs
                or document.get("transfer_identity")
                != {
                    "operation_id": event.operation_id,
                    "event_kind": event.event_kind,
                    "source_evidence_id": document.get("source_evidence_id"),
                    "target_evidence_id": document.get("target_evidence_id"),
                }
            ):
                _fail("campaign I/O transfer receipt semantics changed")
            io_receipts_by_operation[event.operation_id] = document
        elif event.event_kind in {
            "SEMANTIC_HASH_OUTCOME",
            "INTEGRITY_CHECK_OUTCOME",
            "PROTOCOL_CHECK_OUTCOME",
        }:
            expected_kind = {
                "SEMANTIC_HASH_OUTCOME": "SEMANTIC_HASH",
                "INTEGRITY_CHECK_OUTCOME": "INTEGRITY_CHECK",
                "PROTOCOL_CHECK_OUTCOME": "PROTOCOL_CHECK",
            }[event.event_kind]
            ordinal = semantic_ordinals[expected_kind]
            labels = {
                "SEMANTIC_HASH": SEMANTIC_HASH_OPERATION_LABELS,
                "INTEGRITY_CHECK": INTEGRITY_CHECK_OPERATION_LABELS,
                "PROTOCOL_CHECK": PROTOCOL_CHECK_OPERATION_LABELS,
            }[expected_kind]
            spec = operation_specs_by_id[event.operation_id]
            expected_auxiliary = (
                _expected_semantic_receipt_auxiliary_values_v180r12r4(
                    kind=expected_kind,
                    ordinal=ordinal,
                    subject=subject,
                )
            )
            if (
                document.get("attempt_id") != state.attempt_id
                or document.get("kind") != expected_kind
                or document.get("label") != labels[ordinal]
                or document.get("family") != spec["family"]
                or document.get("family_ordinal") != spec["ordinal"]
                or document.get("ordinal") != ordinal
                or document.get("operation_manifest_id") != operation_manifest_id
                or document.get("native_zero_source_manifest_id") != source_id
                or document.get("native_zero_import_inventory_id") != import_id
                or document.get("evidence_subject_id") != attempt_record_id
                or document.get("outcome_code") != event.payload["outcome_code"]
                or document.get("measured_value") != 1
                or document.get("auxiliary_values") != expected_auxiliary
            ):
                _fail("campaign semantic operation receipt semantics changed")
            semantic_ordinals[expected_kind] += 1
            semantic_ids.append(evidence_id)
        elif event.event_kind in {
            "MOUNT_VISIBILITY_OPEN",
            "MOUNT_VISIBILITY_CLOSE",
        }:
            expected_state = (
                "OPEN" if event.event_kind == "MOUNT_VISIBILITY_OPEN" else "CLOSED"
            )
            stage_id = _cid(document.get("stage_receipt_id"), "mount stage receipt ID")
            stage = docs.get(stage_id)
            if (
                stage is None
                or stage.get("schema")
                != "acfqp.campaign_memfd_stage_receipt.v180r12r4"
                or document.get("state") != expected_state
            ):
                _fail("campaign mount visibility/stage evidence join changed")
            mount_rows.append(
                {
                    "event_kind": event.event_kind,
                    "operation_id": event.operation_id,
                    "payload_id": stage_id,
                    "measured_value": event.payload["measured_value"],
                    "byte_count": stage.get("byte_count"),
                    "event_id": event.event_id,
                    "evidence_id": evidence_id,
                }
            )
        elif event.event_kind == "PROCESS_BIRTH_OUTCOME":
            expected_role = (
                "SUPERVISOR"
                if (event.actor_role, event.phase) == ("OBSERVER", "STAGE")
                else "WORKER"
            )
            if document.get("process_role") != expected_role:
                _fail("campaign process-birth evidence role changed")
            birth_ids_by_role[expected_role] = evidence_id
        elif event.event_kind == "PROCESS_REAP":
            expected_role = (
                "SUPERVISOR"
                if (event.actor_role, event.phase) == ("OBSERVER", "OS_OBSERVE")
                else "WORKER"
            )
            if document.get("process_role") != expected_role:
                _fail("campaign process-reap evidence role changed")
            reap_ids_by_role[expected_role] = evidence_id
        elif event.event_kind == "SUBJECT_COMMIT":
            if (
                document.get("subject_id") != subject_id
                or document.get("replay_subject_receipt_id")
                != replay_subject.get("replay_subject_receipt_id")
                or document.get("subject_byte_count") != subject_byte_count
                or document.get("subject_committed") is not True
            ):
                _fail("campaign subject-commit evidence join changed")
        elif event.event_kind == "CGROUP_OBSERVED":
            memory_peak = _positive_int(
                document.get("memory_peak_bytes"), "observed memory.peak"
            )
            if (
                memory_peak != event.payload["measured_value"]
                or memory_peak > MEMORY_MAX_BYTES
                or document.get("pids_peak") != 2
                or document.get("root_populated") is not False
                or document.get("root_process_count") != 0
                or document.get("supervisor_leaf_process_count") != 0
                or document.get("worker_leaf_process_count") != 0
            ):
                _fail("campaign cgroup observation arithmetic/topology changed")

    if (
        set(replay_subject.get("semantic_operation_receipt_ids", []))
        != set(semantic_ids)
        or len(semantic_ids)
        != (
            SEMANTIC_HASH_OPERATION_COUNT
            + INTEGRITY_CHECK_OPERATION_COUNT
            + PROTOCOL_CHECK_OPERATION_COUNT
        )
        or semantic_ordinals
        != {
            "SEMANTIC_HASH": SEMANTIC_HASH_OPERATION_COUNT,
            "INTEGRITY_CHECK": INTEGRITY_CHECK_OPERATION_COUNT,
            "PROTOCOL_CHECK": PROTOCOL_CHECK_OPERATION_COUNT,
        }
        or replay_subject.get("operation_manifest_id") != operation_manifest_id
        or replay_subject.get("native_zero_source_manifest_id") != source_id
        or replay_subject.get("native_zero_import_inventory_id") != import_id
        or replay_subject.get("campaign_attempt_record_id") != attempt_record_id
    ):
        _fail("campaign replay subject does not bind the exact semantic receipts")

    topology = inventory.one("acfqp.campaign_cgroup_topology_receipt.v180r12r4")
    topology_id = topology.get("cgroup_topology_receipt_id")
    if (
        topology.get("memory_max_bytes") != MEMORY_MAX_BYTES
        or topology.get("pids_max") != 2
        or topology.get("root_populated_before_birth") is not False
        or topology.get("root_process_count_before_birth") != 0
        or topology.get("leaf_process_counts_before_birth") != [0, 0]
    ):
        _fail("campaign cgroup topology receipt changed")
    if set(birth_ids_by_role) != {"SUPERVISOR", "WORKER"}:
        _fail("campaign exact supervisor/worker birth population changed")
    _validate_production_runtime_placement_chain_v180r12r4(
        topology=topology,
        supervisor_birth=docs[birth_ids_by_role["SUPERVISOR"]],
        worker_birth=docs[birth_ids_by_role["WORKER"]],
    )
    for role, birth_id in birth_ids_by_role.items():
        if docs[birth_id].get("topology_receipt_id") != topology_id:
            _fail("campaign process birth/topology receipt join changed")
        reap = docs[reap_ids_by_role[role]]
        if reap.get("process_birth_receipt_id") != birth_id:
            _fail("campaign process reap/birth receipt join changed")

    snapshots = tuple(
        document
        for document in inventory.documents
        if document.get("schema")
        == "acfqp.campaign_stable_input_snapshot.v180r12r4"
    )
    snapshot_by_role = {document.get("role"): document for document in snapshots}
    if (
        set(snapshot_by_role) != {"TERMINAL", "VERIFICATION"}
        or len(snapshot_by_role) != len(snapshots)
        or snapshot_by_role["TERMINAL"].get("observed_byte_count")
        != TERMINAL_INPUT_BYTE_COUNT
        or snapshot_by_role["VERIFICATION"].get("observed_byte_count")
        != VERIFICATION_INPUT_BYTE_COUNT
    ):
        _fail("campaign exact two source snapshot byte counts changed")
    snapshot_ids = {row["stable_input_snapshot_id"] for row in snapshots}
    stages = tuple(
        document
        for document in inventory.documents
        if document.get("schema")
        == "acfqp.campaign_memfd_stage_receipt.v180r12r4"
    )
    stage_by_role = {document.get("role"): document for document in stages}
    if (
        set(stage_by_role) != {"TERMINAL", "VERIFICATION"}
        or len(stage_by_role) != len(stages)
        or stage_by_role["TERMINAL"].get("byte_count")
        != TERMINAL_INPUT_BYTE_COUNT
        or stage_by_role["VERIFICATION"].get("byte_count")
        != VERIFICATION_INPUT_BYTE_COUNT
        or any(
            stage_by_role[role].get("input_snapshot_id")
            != snapshot_by_role[role].get("stable_input_snapshot_id")
            for role in ("TERMINAL", "VERIFICATION")
        )
    ):
        _fail("campaign exact two staged payload byte/snapshot joins changed")

    io_events = {
        (row.event_kind, row.actor_role, row.phase, row.operation_id): row
        for row in direct_events
        if row.event_kind
        in {"INPUT_READ_OUTCOME", "STAGE_WRITE_OUTCOME", "SUBJECT_WRITE_OUTCOME"}
    }
    schedule = build_campaign_operation_schedule_v180r12r4(state.attempt_id)
    # Freeze the exact acyclic evidence graph for all eight measured transfers.
    # No successful transfer in this campaign is a self-edge: each operation's
    # source/target types and input role are fixed by its manifest family/ordinal.
    for spec in schedule:
        if spec.operation_id not in io_receipts_by_operation:
            continue
        receipt = io_receipts_by_operation[spec.operation_id]
        role = "TERMINAL" if spec.ordinal == 0 else "VERIFICATION"
        if spec.slot == "INPUT_READ" and spec.family == "FROZEN_SOURCE":
            expected_endpoints = (
                operation_manifest_id,
                snapshot_by_role[role]["stable_input_snapshot_id"],
            )
        elif spec.slot == "STAGE_WRITE" and spec.family == "SEALED_MEMFD":
            expected_endpoints = (
                snapshot_by_role[role]["stable_input_snapshot_id"],
                stage_by_role[role]["memfd_stage_receipt_id"],
            )
        elif spec.slot == "INPUT_READ" and spec.family == "SEALED_STAGE":
            expected_endpoints = (
                stage_by_role[role]["memfd_stage_receipt_id"],
                birth_ids_by_role["WORKER"],
            )
        elif spec.slot == "SUBJECT_WRITE" and spec.family == "SUBJECT_RESULT":
            expected_endpoints = (subject_id, birth_ids_by_role["WORKER"])
        elif spec.slot == "INPUT_READ" and spec.family == "SUBJECT_READBACK":
            expected_endpoints = (subject_id, birth_ids_by_role["SUPERVISOR"])
        else:
            _fail("campaign I/O transfer operation escaped its exact graph")
        actual_endpoints = (
            receipt.get("source_evidence_id"),
            receipt.get("target_evidence_id"),
        )
        if (
            actual_endpoints != expected_endpoints
            or actual_endpoints[0] == actual_endpoints[1]
        ):
            _fail("campaign I/O transfer evidence graph changed")
    if len(io_receipts_by_operation) != 8:
        _fail("campaign I/O transfer evidence graph denominator changed")

    def values_for(slot: str, family: str) -> list[int]:
        result: list[int] = []
        event_kind = f"{slot}_OUTCOME"
        for spec in schedule:
            if spec.slot == slot and spec.family == family:
                result.append(
                    io_events[
                        (event_kind, spec.actor_role, spec.phase, spec.operation_id)
                    ].payload["measured_value"]
                )
        return result

    if (
        values_for("INPUT_READ", "FROZEN_SOURCE")
        != [TERMINAL_INPUT_BYTE_COUNT, VERIFICATION_INPUT_BYTE_COUNT]
        or values_for("INPUT_READ", "SEALED_STAGE")
        != [TERMINAL_INPUT_BYTE_COUNT, VERIFICATION_INPUT_BYTE_COUNT]
        or values_for("INPUT_READ", "SUBJECT_READBACK") != [subject_byte_count]
        or values_for("STAGE_WRITE", "SEALED_MEMFD")
        != [TERMINAL_INPUT_BYTE_COUNT, VERIFICATION_INPUT_BYTE_COUNT]
        or values_for("SUBJECT_WRITE", "SUBJECT_RESULT") != [subject_byte_count]
    ):
        _fail("campaign exact read/stage/output byte arithmetic changed")

    mount_replay = replay_mount_visibility_intervals_v180r12r4(mount_rows)
    if (
        len(mount_replay.open_event_ids) != 2
        or len(mount_replay.close_event_ids) != 2
        or mount_replay.peak_mounted_bytes != TOTAL_STAGED_INPUT_BYTE_COUNT
    ):
        _fail("campaign overlapping mounted-byte peak changed")
    if (
        set(replay_subject.get("open_visibility_receipt_ids", []))
        != set(mount_replay.open_evidence_ids)
        or {
            replay_subject.get("terminal_snapshot_id"),
            replay_subject.get("verification_snapshot_id"),
        }
        != snapshot_ids
    ):
        _fail("campaign replay-subject input/visibility evidence joins changed")
    if (
        subject.get("operation_manifest_id") != operation_manifest_id
        or set(subject.get("memfd_stage_receipt_ids", []))
        != {row["memfd_stage_receipt_id"] for row in stages}
        or set(subject.get("open_visibility_receipt_ids", []))
        != set(mount_replay.open_evidence_ids)
        or {
            subject.get("terminal_snapshot_id"),
            subject.get("verification_snapshot_id"),
        }
        != snapshot_ids
        or subject.get("worker_birth_receipt_id")
        != birth_ids_by_role.get("WORKER")
    ):
        _fail("campaign full subject-result evidence cross-joins changed")

    subject_commit = inventory.one("acfqp.campaign_subject_commit_receipt.v180r12r4")
    window_closure = inventory.one("acfqp.campaign_window_closure_receipt.v180r12r4")
    window_event = _events_by_kind(state.events, "WINDOW_CLOSED")[0]
    if (
        window_closure.get("subject_commit_receipt_id")
        != subject_commit.get("subject_commit_receipt_id")
        or set(window_closure.get("close_visibility_receipt_ids", []))
        != set(mount_replay.close_evidence_ids)
        or window_closure.get("window_closed") is not True
        or window_closure.get("all_registered_mounts_closed") is not True
    ):
        _fail("campaign window-closure evidence join changed")
    readback_spec = next(
        row
        for row in schedule
        if row.slot == "INPUT_READ" and row.family == "SUBJECT_READBACK"
    )
    readback_event = io_events[
        (
            "INPUT_READ_OUTCOME",
            readback_spec.actor_role,
            readback_spec.phase,
            readback_spec.operation_id,
        )
    ]
    if (
        subject_commit.get("readback_transfer_receipt_id")
        != readback_event.payload["evidence_id"]
        or subject_commit.get("subject_id") != subject_id
    ):
        _fail("campaign subject commit/readback receipt join changed")

    cgroup_observation = inventory.one(
        "acfqp.campaign_cgroup_observation_receipt.v180r12r4"
    )
    if (
        cgroup_observation.get("topology_receipt_id") != topology_id
        or cgroup_observation.get("supervisor_reap_receipt_id")
        != reap_ids_by_role.get("SUPERVISOR")
        or cgroup_observation.get("worker_reap_receipt_id")
        != reap_ids_by_role.get("WORKER")
    ):
        _fail("campaign cgroup observation/topology/reap join changed")

    execution = inventory.one("acfqp.campaign_execution_closure.v180r12r4")
    execution_id = execution.get("campaign_execution_closure_id")
    if (
        execution.get("protocol_id") != state.protocol_id
        or execution.get("authorization_id") != state.authorization_id
        or execution.get("attempt_id") != state.attempt_id
        or execution.get("subject_id") != subject_id
        or execution.get("window_closed_event_id") != window_event.event_id
        or execution.get("window_closure_receipt_id")
        != window_closure.get("window_closure_receipt_id")
        or execution.get("operation_manifest_id") != operation_manifest_id
        or execution.get("source_manifest_id") != source_id
        or execution.get("import_inventory_id") != import_id
        or execution.get("precompiled_source_bundle_sha256")
        != source_manifest.get("precompiled_source_bundle_sha256")
        or execution.get("comparison_axis") != KERNEL_TRANSITION_CALLS
        or execution.get("kernel_transition_calls") != 0
        or execution.get("registered_planning_operation_site_fact_count") != 314
        or execution.get("kernel_transition_operation_site_fact_ids") != []
        or execution.get("kernel_transition_import_fact_ids") != []
        or execution.get("unregistered_operation_site_fact_ids") != []
        or execution.get("unregistered_import_fact_ids") != []
        or execution.get("registered_planning_comparison_ground_kernel_axis_only")
        is not True
        or execution.get("prelaunch_sealed_application_import_allowlist_only")
        is not True
        or execution.get("runtime_role_exit_origin_guard_required") is not True
        or execution.get("runtime_role_exit_origin_guard_status")
        != "PENDING_INDEPENDENT_MEASUREMENT_LAUNCH_RECEIPT"
        or execution.get("not_an_os_syscall_count") is not True
        or execution.get("unregistered_or_dynamic_sites_forbidden") is not True
        or execution.get("closed_registered_planning_operation_window_only")
        is not True
        or execution.get("open_world_absence_claimed") is not False
        or execution.get("execution_window_closed") is not True
    ):
        _fail("campaign execution closure/native-zero authority changed")
    assert type(execution_id) is str
    return CampaignEvidenceFactsV180R12R4(
        inventory,
        mount_replay,
        subject_byte_count,
        operation_manifest_id,
        source_id,
        import_id,
        execution_id,
    )


def _leaf_document(path: str) -> dict[str, Any]:
    if path not in _LEAF_METADATA:
        _fail("campaign counter path is absent from the nine-leaf extract")
    semantics_id, owner, unit, scope, reducer, axis = _LEAF_METADATA[path]
    return {
        "path": path,
        "semantics_id": semantics_id,
        "owner": owner,
        "unit": unit,
        "lane": "operational",
        "scope": scope,
        "reducer": reducer,
        "comparison_axis": axis,
        "required": True,
        "source_registry_key": COUNTER_REGISTRY_REFERENCE,
        "metadata_authority": "EXACT_V6_LEAF_METADATA_EXTRACT",
    }


@dataclass(frozen=True, slots=True)
class CampaignPathReceiptV180R12R4:
    protocol_id: str
    authorization_id: str
    attempt_id: str
    subject_id: str
    path: str
    value: int
    counter_event_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    closure_event_ids: tuple[str, ...]
    closure_evidence_ids: tuple[str, ...]
    window_closed_event_id: str
    native_zero_observed: bool

    def __post_init__(self) -> None:
        for value, label in (
            (self.protocol_id, "campaign protocol ID"),
            (self.authorization_id, "campaign authorization ID"),
            (self.attempt_id, "campaign attempt ID"),
            (self.subject_id, "campaign subject ID"),
            (self.window_closed_event_id, "campaign window-closed event ID"),
        ):
            _cid(value, label)
        _leaf_document(self.path)
        _positive_int(self.value, self.path)
        if (
            type(self.counter_event_ids) is not tuple
            or not self.counter_event_ids
            or type(self.evidence_ids) is not tuple
            or len(self.evidence_ids) != len(self.counter_event_ids)
        ):
            _fail("campaign path receipt event/evidence alignment changed")
        for value in self.counter_event_ids:
            _cid(value, "campaign counter event ID")
        for value in self.evidence_ids:
            _cid(value, "campaign counter evidence ID")
        if (
            type(self.closure_event_ids) is not tuple
            or type(self.closure_evidence_ids) is not tuple
            or len(self.closure_event_ids) != len(self.closure_evidence_ids)
        ):
            _fail("campaign path closure event/evidence alignment changed")
        for value in self.closure_event_ids:
            _cid(value, "campaign closure event ID")
        for value in self.closure_evidence_ids:
            _cid(value, "campaign closure evidence ID")
        if self.path == "io.mounted_bytes_peak":
            if len(self.counter_event_ids) != 2 or len(self.closure_event_ids) != 2:
                _fail("mounted-byte path must bind two OPEN and two CLOSE receipts")
        elif self.closure_event_ids or self.closure_evidence_ids:
            _fail("non-mounted path cannot bind visibility-close receipts")
        if self.native_zero_observed is not False:
            _fail("successful campaign paths are all strictly positive")

    def _payload(self) -> dict[str, Any]:
        leaf = _leaf_document(self.path)
        return {
            "schema": "acfqp.campaign_path_receipt.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "scope": CAMPAIGN_SCOPE_KIND,
            "protocol_id": self.protocol_id,
            "authorization_id": self.authorization_id,
            "attempt_id": self.attempt_id,
            "subject_id": self.subject_id,
            **leaf,
            "value": self.value,
            "observed": True,
            "actual_measurement_present": True,
            "counter_event_ids": list(self.counter_event_ids),
            "evidence_ids": list(self.evidence_ids),
            "closure_event_ids": list(self.closure_event_ids),
            "closure_evidence_ids": list(self.closure_evidence_ids),
            "window_closed_event_id": self.window_closed_event_id,
            "native_zero_observed": self.native_zero_observed,
        }

    @property
    def campaign_path_receipt_id(self) -> str:
        return domains.extension_content_id_v180r12r4e(
            domains.CONSTRUCTION_K7_CAMPAIGN_PATH_RECEIPT_V180R12R4E_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_path_receipt_id": self.campaign_path_receipt_id,
        }


@dataclass(frozen=True, slots=True)
class CampaignCounterRecordV180R12R4:
    path_receipt: CampaignPathReceiptV180R12R4

    def __post_init__(self) -> None:
        if type(self.path_receipt) is not CampaignPathReceiptV180R12R4:
            _fail("campaign counter record requires one typed path receipt")

    @property
    def path(self) -> str:
        return self.path_receipt.path

    @property
    def value(self) -> int:
        return self.path_receipt.value

    def _payload(self) -> dict[str, Any]:
        receipt = self.path_receipt
        return {
            "schema": "acfqp.campaign_counter_record.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "scope": CAMPAIGN_SCOPE_KIND,
            "protocol_id": receipt.protocol_id,
            "authorization_id": receipt.authorization_id,
            "attempt_id": receipt.attempt_id,
            "subject_id": receipt.subject_id,
            **_leaf_document(receipt.path),
            "value": receipt.value,
            "observed": True,
            "campaign_path_receipt_id": receipt.campaign_path_receipt_id,
            "native_zero_observed": receipt.native_zero_observed,
        }

    @property
    def counter_record_id(self) -> str:
        return domains.extension_content_id_v180r12r4e(
            domains.CONSTRUCTION_K7_CAMPAIGN_COUNTER_RECORD_V180R12R4E_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_record_id": self.counter_record_id}


@dataclass(frozen=True, slots=True)
class CampaignReceiptSetV180R12R4:
    receipts: tuple[CampaignPathReceiptV180R12R4, ...]

    def __post_init__(self) -> None:
        if (
            type(self.receipts) is not tuple
            or tuple(row.path for row in self.receipts) != CAMPAIGN_COUNTER_PATHS
            or any(type(row) is not CampaignPathReceiptV180R12R4 for row in self.receipts)
        ):
            _fail("campaign receipt set must contain the exact nine paths in order")
        contexts = {
            (row.protocol_id, row.authorization_id, row.attempt_id, row.subject_id)
            for row in self.receipts
        }
        if len(contexts) != 1:
            _fail("campaign receipt set context changed")

    def _payload(self) -> dict[str, Any]:
        first = self.receipts[0]
        return {
            "schema": "acfqp.campaign_receipt_set.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "scope": CAMPAIGN_SCOPE_KIND,
            "protocol_id": first.protocol_id,
            "authorization_id": first.authorization_id,
            "attempt_id": first.attempt_id,
            "subject_id": first.subject_id,
            "ordered_paths": list(CAMPAIGN_COUNTER_PATHS),
            "ordered_campaign_path_receipt_ids": [
                row.campaign_path_receipt_id for row in self.receipts
            ],
            "campaign_path_receipt_count": CAMPAIGN_PATH_RECEIPT_COUNT,
        }

    @property
    def campaign_receipt_set_id(self) -> str:
        return domains.extension_content_id_v180r12r4e(
            domains.CONSTRUCTION_K7_CAMPAIGN_RECEIPT_SET_V180R12R4E_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_receipt_set_id": self.campaign_receipt_set_id}


@dataclass(frozen=True, slots=True)
class CampaignWorkVectorV180R12R4:
    receipt_set: CampaignReceiptSetV180R12R4
    records: tuple[CampaignCounterRecordV180R12R4, ...]

    def __post_init__(self) -> None:
        if (
            type(self.receipt_set) is not CampaignReceiptSetV180R12R4
            or type(self.records) is not tuple
            or tuple(row.path for row in self.records) != CAMPAIGN_COUNTER_PATHS
            or any(type(row) is not CampaignCounterRecordV180R12R4 for row in self.records)
            or tuple(row.path_receipt for row in self.records) != self.receipt_set.receipts
        ):
            _fail("campaign work vector is not the exact nine-record receipt lift")

    @property
    def values(self) -> dict[str, int]:
        return {row.path: row.value for row in self.records}

    def _payload(self) -> dict[str, Any]:
        first = self.receipt_set.receipts[0]
        return {
            "schema": "acfqp.campaign_work_vector.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "scope": CAMPAIGN_SCOPE_KIND,
            "scope_model": CAMPAIGN_SCOPE_MODEL,
            "protocol_id": first.protocol_id,
            "authorization_id": first.authorization_id,
            "attempt_id": first.attempt_id,
            "subject_id": first.subject_id,
            "campaign_receipt_set_id": self.receipt_set.campaign_receipt_set_id,
            "ordered_counter_record_ids": [row.counter_record_id for row in self.records],
            "counter_record_count": CAMPAIGN_COUNTER_RECORD_COUNT,
            "ordered_paths": list(CAMPAIGN_COUNTER_PATHS),
        }

    @property
    def campaign_work_vector_id(self) -> str:
        return domains.extension_content_id_v180r12r4e(
            domains.CONSTRUCTION_K7_CAMPAIGN_WORK_VECTOR_V180R12R4E_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_work_vector_id": self.campaign_work_vector_id}


@dataclass(frozen=True, slots=True)
class CampaignComparisonVectorV180R12R4:
    work_vector: CampaignWorkVectorV180R12R4
    native_zero_attestation: "CampaignNativeZeroAttestationV180R12R4"
    values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if type(self.work_vector) is not CampaignWorkVectorV180R12R4:
            _fail("campaign comparison vector requires one route-free work vector")
        if (
            type(self.native_zero_attestation)
            is not CampaignNativeZeroAttestationV180R12R4
            or self.native_zero_attestation.work_vector != self.work_vector
        ):
            _fail("campaign comparison vector lacks its independent native-zero authority")
        if (
            type(self.values) is not tuple
            or tuple(axis for axis, _value in self.values) != SHARED_AXES
            or any(type(value) is not int or value < 0 for _axis, value in self.values)
        ):
            _fail("campaign comparison vector must contain the exact eight axes")

    def _payload(self) -> dict[str, Any]:
        first = self.work_vector.receipt_set.receipts[0]
        return {
            "schema": "acfqp.campaign_comparison_vector.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "scope": CAMPAIGN_SCOPE_KIND,
            "scope_model": CAMPAIGN_SCOPE_MODEL,
            "protocol_id": first.protocol_id,
            "authorization_id": first.authorization_id,
            "attempt_id": first.attempt_id,
            "subject_id": first.subject_id,
            "campaign_work_vector_id": self.work_vector.campaign_work_vector_id,
            "campaign_native_zero_attestation_id": (
                self.native_zero_attestation.campaign_native_zero_attestation_id
            ),
            "values": [
                {
                    "axis": axis,
                    "value": value,
                    "reducer": _AXIS_REDUCER[axis],
                }
                for axis, value in self.values
            ],
        }

    @property
    def campaign_comparison_vector_id(self) -> str:
        return domains.extension_content_id_v180r12r4e(
            domains.CONSTRUCTION_K7_CAMPAIGN_COMPARISON_VECTOR_V180R12R4E_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_comparison_vector_id": self.campaign_comparison_vector_id,
        }

    def value(self, axis: str) -> int:
        try:
            return dict(self.values)[axis]
        except KeyError as error:
            raise ConstructionK7CampaignMeasurementLedgerV180R12R4Error(
                f"campaign comparison vector has no axis {axis!r}"
            ) from error


def _projection_terms(
    records: Sequence[CampaignCounterRecordV180R12R4],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "source_path": row.path,
            "source_counter_record_id": row.counter_record_id,
            "source_campaign_path_receipt_id": row.path_receipt.campaign_path_receipt_id,
            "source_semantics_id": _LEAF_METADATA[row.path][0],
            "source_lane": "operational",
            "target_axis": _LEAF_METADATA[row.path][5],
            "coefficient": 1,
            "reducer": _LEAF_METADATA[row.path][4],
        }
        for row in records
    )


@dataclass(frozen=True, slots=True)
class CampaignProjectionProofV180R12R4:
    work_vector: CampaignWorkVectorV180R12R4
    comparison_vector: CampaignComparisonVectorV180R12R4
    native_zero_attestation: "CampaignNativeZeroAttestationV180R12R4"

    def __post_init__(self) -> None:
        if (
            type(self.work_vector) is not CampaignWorkVectorV180R12R4
            or type(self.comparison_vector) is not CampaignComparisonVectorV180R12R4
            or self.comparison_vector.work_vector != self.work_vector
            or type(self.native_zero_attestation)
            is not CampaignNativeZeroAttestationV180R12R4
            or self.comparison_vector.native_zero_attestation
            != self.native_zero_attestation
        ):
            _fail("campaign projection proof vector references changed")
        expected = _derive_comparison_values(
            self.work_vector.records, self.native_zero_attestation
        )
        if self.comparison_vector.values != expected:
            _fail("campaign projection proof does not replay the exact reducers")

    def _payload(self) -> dict[str, Any]:
        first = self.work_vector.receipt_set.receipts[0]
        return {
            "schema": "acfqp.campaign_projection_proof.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "scope": CAMPAIGN_SCOPE_KIND,
            "scope_model": CAMPAIGN_SCOPE_MODEL,
            "protocol_id": first.protocol_id,
            "authorization_id": first.authorization_id,
            "attempt_id": first.attempt_id,
            "subject_id": first.subject_id,
            "campaign_work_vector_id": self.work_vector.campaign_work_vector_id,
            "campaign_comparison_vector_id": (
                self.comparison_vector.campaign_comparison_vector_id
            ),
            "campaign_native_zero_attestation_id": (
                self.native_zero_attestation.campaign_native_zero_attestation_id
            ),
            "projection_terms": list(_projection_terms(self.work_vector.records)),
            "projection_term_count": CAMPAIGN_COUNTER_RECORD_COUNT,
            "native_zero_projection_term": {
                "source_campaign_native_zero_attestation_id": (
                    self.native_zero_attestation.campaign_native_zero_attestation_id
                ),
                "target_axis": KERNEL_TRANSITION_CALLS,
                "value": 0,
                "separate_from_nine_campaign_paths": True,
            },
            "native_zero_projection_term_count": 1,
            "projection_proof_references_native_zero_attestation": True,
            "all_operational_leaves_projected_once": True,
            "sum_and_max_reducers_replayed": True,
        }

    @property
    def campaign_projection_proof_id(self) -> str:
        return domains.extension_content_id_v180r12r4e(
            domains.CONSTRUCTION_K7_CAMPAIGN_PROJECTION_PROOF_V180R12R4E_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_projection_proof_id": self.campaign_projection_proof_id,
        }


@dataclass(frozen=True, slots=True)
class CampaignNativeZeroAttestationV180R12R4:
    work_vector: CampaignWorkVectorV180R12R4
    window_closed_event_id: str
    _execution_closure_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.work_vector) is not CampaignWorkVectorV180R12R4:
            _fail("campaign native-zero attestation requires one work vector")
        _cid(self.window_closed_event_id, "campaign zero window-closed event ID")
        if any(
            row.value <= 0
            or row.path_receipt.native_zero_observed is not False
            or row.path_receipt.window_closed_event_id != self.window_closed_event_id
            for row in self.work_vector.records
        ):
            _fail("campaign successful nine-path positivity changed")
        raw, execution = _canonical_object(
            self._execution_closure_bytes, "campaign execution closure evidence"
        )
        if raw != self._execution_closure_bytes:
            _fail("campaign execution closure evidence bytes changed")
        identity, schema = _document_identity(execution)
        first = self.work_vector.receipt_set.receipts[0]
        if (
            schema != "acfqp.campaign_execution_closure.v180r12r4"
            or execution.get("campaign_execution_closure_id") != identity
            or execution.get("protocol_id") != first.protocol_id
            or execution.get("authorization_id") != first.authorization_id
            or execution.get("attempt_id") != first.attempt_id
            or execution.get("subject_id") != first.subject_id
            or execution.get("window_closed_event_id") != self.window_closed_event_id
            or execution.get("comparison_axis") != KERNEL_TRANSITION_CALLS
            or execution.get("kernel_transition_calls") != 0
            or execution.get("registered_planning_comparison_ground_kernel_axis_only")
            is not True
            or execution.get("not_an_os_syscall_count") is not True
            or execution.get("unregistered_or_dynamic_sites_forbidden") is not True
            or execution.get("registered_planning_operation_site_fact_count") != 314
            or execution.get("prelaunch_sealed_application_import_allowlist_only")
            is not True
            or execution.get("runtime_role_exit_origin_guard_required") is not True
            or execution.get("runtime_role_exit_origin_guard_status")
            != "PENDING_INDEPENDENT_MEASUREMENT_LAUNCH_RECEIPT"
            or execution.get("closed_registered_planning_operation_window_only")
            is not True
            or execution.get("open_world_absence_claimed") is not False
        ):
            _fail("campaign native-zero execution closure changed")

    @property
    def execution_closure(self) -> dict[str, Any]:
        return _canonical_object(
            self._execution_closure_bytes, "campaign execution closure evidence"
        )[1]

    def _payload(self) -> dict[str, Any]:
        first = self.work_vector.receipt_set.receipts[0]
        return {
            "schema": "acfqp.campaign_native_zero_attestation.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "scope": CAMPAIGN_SCOPE_KIND,
            "scope_model": CAMPAIGN_SCOPE_MODEL,
            "protocol_id": first.protocol_id,
            "authorization_id": first.authorization_id,
            "attempt_id": first.attempt_id,
            "subject_id": first.subject_id,
            "campaign_work_vector_id": self.work_vector.campaign_work_vector_id,
            "window_closed_event_id": self.window_closed_event_id,
            "campaign_execution_closure_id": self.execution_closure[
                "campaign_execution_closure_id"
            ],
            "registered_operation_manifest_id": self.execution_closure[
                "operation_manifest_id"
            ],
            "native_zero_source_manifest_id": self.execution_closure[
                "source_manifest_id"
            ],
            "native_zero_import_inventory_id": self.execution_closure[
                "import_inventory_id"
            ],
            "comparison_axis": KERNEL_TRANSITION_CALLS,
            "comparison_axis_value": 0,
            "axis_definition": (
                "REGISTERED_PLANNING_COMPARISON_GROUND_KERNEL_TRANSITION_AXIS"
            ),
            "not_an_os_syscall_count": True,
            "unregistered_or_dynamic_sites_forbidden": True,
            "registered_planning_operation_site_fact_count": 314,
            "prelaunch_sealed_application_import_allowlist_only": True,
            "runtime_role_exit_origin_guard_required": True,
            "runtime_role_exit_origin_guard_status": (
                "PENDING_INDEPENDENT_MEASUREMENT_LAUNCH_RECEIPT"
            ),
            "closed_registered_planning_operation_window_only": True,
            "open_world_absence_claimed": False,
            "campaign_path_zero_observation_count": 0,
            "all_nine_campaign_paths_strictly_positive": True,
            "separate_from_nine_campaign_paths": True,
        }

    @property
    def campaign_native_zero_attestation_id(self) -> str:
        return domains.extension_content_id_v180r12r4e(
            domains.CONSTRUCTION_K7_CAMPAIGN_NATIVE_ZERO_ATTESTATION_V180R12R4E_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_native_zero_attestation_id": (
                self.campaign_native_zero_attestation_id
            ),
        }


def _derive_comparison_values(
    records: Sequence[CampaignCounterRecordV180R12R4],
    native_zero_attestation: CampaignNativeZeroAttestationV180R12R4,
) -> tuple[tuple[str, int], ...]:
    if type(native_zero_attestation) is not CampaignNativeZeroAttestationV180R12R4:
        _fail("comparison derivation requires independent native-zero authority")
    axes: dict[str, int | None] = {axis: None for axis in SHARED_AXES}
    for record in records:
        _semantics_id, _owner, _unit, _scope, reducer, axis = _LEAF_METADATA[
            record.path
        ]
        if reducer == "sum":
            axes[axis] = (axes[axis] or 0) + record.value
        else:
            axes[axis] = record.value if axes[axis] is None else max(
                axes[axis], record.value
            )
    if axes[KERNEL_TRANSITION_CALLS] is not None:
        _fail("nine campaign paths cannot populate kernel_transition_calls")
    axes[KERNEL_TRANSITION_CALLS] = 0
    if any(value is None for value in axes.values()):
        _fail("comparison derivation left an axis unproved")
    return tuple((axis, int(axes[axis])) for axis in SHARED_AXES)


def _derive_path_receipts(
    state: CampaignLedgerStateV180R12R4,
    subject_id: str,
    evidence_facts: CampaignEvidenceFactsV180R12R4,
) -> tuple[CampaignPathReceiptV180R12R4, ...]:
    _validate_event_stream_v180r12r4(state)
    canonical_subject_id = _cid(subject_id, "campaign subject ID")
    assert canonical_subject_id is not None
    window = _events_by_kind(state.events, "WINDOW_CLOSED")[0]
    receipts: list[CampaignPathReceiptV180R12R4] = []
    for path in CAMPAIGN_COUNTER_PATHS:
        rows = tuple(
            row
            for row in state.events
            if _COUNTER_EVENT_PATH.get(row.event_kind) == path
        )
        if not rows:
            _fail(f"campaign path {path!r} has no actual observation")
        values = tuple(row.payload["measured_value"] for row in rows)
        reducer = _LEAF_METADATA[path][4]
        if path == "io.mounted_bytes_peak":
            replay = evidence_facts.mount_replay
            value = replay.peak_mounted_bytes
            counter_event_ids = replay.open_event_ids
            evidence_ids = replay.open_evidence_ids
            closure_event_ids = replay.close_event_ids
            closure_evidence_ids = replay.close_evidence_ids
        else:
            value = sum(values) if reducer == "sum" else max(values)
            counter_event_ids = tuple(row.event_id for row in rows)
            evidence_ids = tuple(row.payload["evidence_id"] for row in rows)
            closure_event_ids = ()
            closure_evidence_ids = ()
        if any(evidence_id is None for evidence_id in evidence_ids):
            _fail("campaign actual observation lost its evidence ID")
        receipts.append(
            CampaignPathReceiptV180R12R4(
                state.protocol_id,
                state.authorization_id,
                state.attempt_id,
                canonical_subject_id,
                path,
                value,
                counter_event_ids,
                evidence_ids,  # type: ignore[arg-type]
                closure_event_ids,
                closure_evidence_ids,
                window.event_id,
                False,
            )
        )
    result = tuple(receipts)
    actual = {row.path: row.value for row in result}
    expected = {
        "common.hash_invocations": SEMANTIC_HASH_OPERATION_COUNT,
        "common.integrity_checks": INTEGRITY_CHECK_OPERATION_COUNT,
        "common.protocol_checks": PROTOCOL_CHECK_OPERATION_COUNT,
        "io.mounted_bytes_peak": TOTAL_STAGED_INPUT_BYTE_COUNT,
        "io.output_bytes": evidence_facts.subject_byte_count,
        "io.read_bytes": 2 * TOTAL_STAGED_INPUT_BYTE_COUNT
        + evidence_facts.subject_byte_count,
        "io.staged_bytes": TOTAL_STAGED_INPUT_BYTE_COUNT,
        "memory.working_bytes_peak": actual["memory.working_bytes_peak"],
        "process.launches": 2,
    }
    if actual != expected or not (0 < actual["memory.working_bytes_peak"] <= MEMORY_MAX_BYTES):
        _fail("campaign exact nine-path arithmetic closure changed")
    return result


@dataclass(frozen=True, slots=True)
class CampaignMeasurementLedgerV180R12R4:
    state: CampaignLedgerStateV180R12R4
    subject_id: str
    evidence_inventory: CampaignEvidenceInventoryV180R12R4
    native_zero_source_manifest_id: str
    native_zero_import_inventory_id: str
    receipt_set: CampaignReceiptSetV180R12R4
    records: tuple[CampaignCounterRecordV180R12R4, ...]
    work_vector: CampaignWorkVectorV180R12R4
    comparison_vector: CampaignComparisonVectorV180R12R4
    projection_proof: CampaignProjectionProofV180R12R4
    native_zero_attestation: CampaignNativeZeroAttestationV180R12R4

    def __post_init__(self) -> None:
        _validate_event_stream_v180r12r4(self.state)
        _cid(self.subject_id, "campaign subject ID")
        if type(self.evidence_inventory) is not CampaignEvidenceInventoryV180R12R4:
            _fail("campaign measurement ledger requires one typed evidence inventory")
        evidence_facts = _validate_evidence_inventory_v180r12r4(
            self.state,
            self.subject_id,
            self.evidence_inventory,
            expected_source_manifest_id=self.native_zero_source_manifest_id,
            expected_import_inventory_id=self.native_zero_import_inventory_id,
        )
        expected_receipts = _derive_path_receipts(
            self.state, self.subject_id, evidence_facts
        )
        expected_records = tuple(CampaignCounterRecordV180R12R4(row) for row in expected_receipts)
        expected_receipt_set = CampaignReceiptSetV180R12R4(expected_receipts)
        expected_work = CampaignWorkVectorV180R12R4(
            expected_receipt_set, expected_records
        )
        window = _events_by_kind(self.state.events, "WINDOW_CLOSED")[0]
        expected_zero = CampaignNativeZeroAttestationV180R12R4(
            expected_work,
            window.event_id,
            canonical_json_bytes(
                self.evidence_inventory.documents_by_id[
                    evidence_facts.execution_closure_id
                ]
            ),
        )
        expected_comparison = CampaignComparisonVectorV180R12R4(
            expected_work,
            expected_zero,
            _derive_comparison_values(expected_records, expected_zero),
        )
        if (
            self.receipt_set != expected_receipt_set
            or self.records != expected_records
            or self.work_vector != expected_work
            or self.native_zero_attestation != expected_zero
            or self.comparison_vector != expected_comparison
            or self.projection_proof
            != CampaignProjectionProofV180R12R4(
                expected_work, expected_comparison, expected_zero
            )
        ):
            _fail("campaign measurement ledger derived accounting chain changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_measurement_ledger_closure.v180r12r4",
            "schema_version": SCHEMA_VERSION,
            "scope": CAMPAIGN_SCOPE_KIND,
            "scope_model": CAMPAIGN_SCOPE_MODEL,
            "protocol_id": self.state.protocol_id,
            "authorization_id": self.state.authorization_id,
            "attempt_id": self.state.attempt_id,
            "subject_id": self.subject_id,
            "campaign_operation_manifest_id": (
                self.native_zero_attestation.execution_closure[
                    "operation_manifest_id"
                ]
            ),
            "native_zero_source_manifest_id": self.native_zero_source_manifest_id,
            "native_zero_import_inventory_id": self.native_zero_import_inventory_id,
            "campaign_execution_closure_id": (
                self.native_zero_attestation.execution_closure[
                    "campaign_execution_closure_id"
                ]
            ),
            "max_event_count": self.state.max_event_count,
            "max_event_byte_count": self.state.max_event_byte_count,
            "max_ledger_byte_count": self.state.max_ledger_byte_count,
            "events": [row.to_document() for row in self.state.events],
            "ordered_event_ids": [row.event_id for row in self.state.events],
            "event_count": len(self.state.events),
            "ledger_event_byte_count": self.state.event_byte_count,
            "first_event_id": self.state.events[0].event_id,
            "last_event_id": self.state.events[-1].event_id,
            "evidence_documents": list(self.evidence_inventory.documents),
            "campaign_evidence_document_count": CAMPAIGN_EVIDENCE_DOCUMENT_COUNT,
            "direct_event_evidence_document_count": SUCCESS_EVENT_EVIDENCE_COUNT,
            "support_evidence_document_count": (
                CAMPAIGN_EVIDENCE_DOCUMENT_COUNT - SUCCESS_EVENT_EVIDENCE_COUNT
            ),
            "campaign_evidence_document_type_counts": dict(
                EVIDENCE_DOCUMENT_TYPE_COUNTS
            ),
            "event_evidence_nonnull_count": SUCCESS_EVENT_EVIDENCE_COUNT,
            "event_evidence_null_count": SUCCESS_NULL_EVIDENCE_COUNT,
            "path_receipts": [row.to_document() for row in self.receipt_set.receipts],
            "campaign_receipt_set": self.receipt_set.to_document(),
            "counter_records": [row.to_document() for row in self.records],
            "campaign_work_vector": self.work_vector.to_document(),
            "campaign_comparison_vector": self.comparison_vector.to_document(),
            "campaign_projection_proof": self.projection_proof.to_document(),
            "campaign_native_zero_attestation": (
                self.native_zero_attestation.to_document()
            ),
            "campaign_path_receipt_count": CAMPAIGN_PATH_RECEIPT_COUNT,
            "campaign_counter_record_count": CAMPAIGN_COUNTER_RECORD_COUNT,
            "campaign_work_vector_count": 1,
            "campaign_comparison_vector_count": 1,
            "campaign_projection_proof_count": 1,
            "campaign_native_zero_attestation_count": 1,
            "predecessor_occurrence_authoritative_receipt_count": (
                PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
            ),
            "predecessor_structural_obligation_count": (
                PREDECESSOR_STRUCTURAL_OBLIGATION_COUNT
            ),
            "predecessor_campaign_scope_structural_obligation_count": (
                PREDECESSOR_STRUCTURAL_OBLIGATION_COUNT
            ),
            "predecessor_campaign_actual_receipt_count": (
                PREDECESSOR_CAMPAIGN_ACTUAL_RECEIPT_COUNT
            ),
            "predecessor_campaign_authoritative_receipt_count": (
                PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
            ),
            "successor_campaign_actual_receipt_count": (
                SUCCESSOR_CAMPAIGN_ACTUAL_RECEIPT_COUNT
            ),
            "successor_campaign_counter_record_count": (
                CAMPAIGN_COUNTER_RECORD_COUNT
            ),
            "combined_successor_authoritative_receipt_count": (
                COMBINED_SUCCESSOR_AUTHORITATIVE_RECEIPT_COUNT
            ),
            "successful_campaign_authoritative_receipt_count": (
                SUCCESSOR_CAMPAIGN_ACTUAL_RECEIPT_COUNT
            ),
            "successful_combined_authoritative_receipt_count": (
                COMBINED_SUCCESSOR_AUTHORITATIVE_RECEIPT_COUNT
            ),
            "terminal_pending_authoritative_receipt_join": {
                "counter_status": "PENDING_INDEPENDENT_REPLAY",
                "predecessor_occurrence_receipt_count": (
                    PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
                ),
                "campaign_actual_receipt_count": (
                    SUCCESSOR_CAMPAIGN_ACTUAL_RECEIPT_COUNT
                ),
                "combined_authoritative_receipt_count": (
                    COMBINED_SUCCESSOR_AUTHORITATIVE_RECEIPT_COUNT
                ),
            },
            "independent_verifier_pass_authoritative_receipt_join": {
                "counter_status": "PASS",
                "predecessor_occurrence_receipt_count": (
                    PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
                ),
                "campaign_actual_receipt_count": (
                    SUCCESSOR_CAMPAIGN_ACTUAL_RECEIPT_COUNT
                ),
                "combined_authoritative_receipt_count": (
                    COMBINED_SUCCESSOR_AUTHORITATIVE_RECEIPT_COUNT
                ),
            },
            "predecessor_structural_nine_are_successor_actual_receipts": False,
            "predecessor_structural_obligations_are_not_current_measurements": True,
            "authoritative_receipt_arithmetic_90_plus_9_equals_99": True,
            "hash_chain_complete": True,
            "lifecycle_phase_order_complete": True,
            "actual_measurements_present": True,
            "all_nine_campaign_paths_strictly_positive": True,
            "independent_comparison_axis_native_zero_complete": True,
            "route_free_campaign_accounting": True,
            "independent_verification_present": False,
            "COUNTER_COMPLETENESS_GATE": COUNTER_COMPLETENESS_GATE,
            "WORKLOAD_ECONOMICS_GATE": WORKLOAD_ECONOMICS_GATE,
            "SCALAR_CALIBRATION_GATE": SCALAR_CALIBRATION_GATE,
            "BREAK_EVEN_GATE": BREAK_EVEN_GATE,
            "OFFICIAL_EXECUTION_GATE": OFFICIAL_EXECUTION_GATE,
            "v180r13_weight_agnostic_economics_input_ready": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
            "scientific_success_claimed": False,
        }

    @property
    def campaign_ledger_closure_id(self) -> str:
        return domains.extension_content_id_v180r12r4e(
            domains.CONSTRUCTION_K7_CAMPAIGN_LEDGER_CLOSURE_V180R12R4E_DOMAIN,
            self._payload(),
        )

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_ledger_closure_id": self.campaign_ledger_closure_id,
        }


def derive_campaign_measurement_ledger_v180r12r4(
    state: CampaignLedgerStateV180R12R4,
    *,
    subject_id: str,
    evidence_documents_by_id: Mapping[str, bytes | dict[str, Any]],
    expected_native_zero_source_manifest_id: str,
    expected_native_zero_import_inventory_id: str,
) -> CampaignMeasurementLedgerV180R12R4:
    """Derive the exact nine-receipt route-free accounting chain."""

    if type(state) is not CampaignLedgerStateV180R12R4:
        _fail("campaign ledger derivation requires one typed state")
    inventory = CampaignEvidenceInventoryV180R12R4.from_mapping(
        evidence_documents_by_id
    )
    facts = _validate_evidence_inventory_v180r12r4(
        state,
        subject_id,
        inventory,
        expected_source_manifest_id=expected_native_zero_source_manifest_id,
        expected_import_inventory_id=expected_native_zero_import_inventory_id,
    )
    receipts = _derive_path_receipts(state, subject_id, facts)
    receipt_set = CampaignReceiptSetV180R12R4(receipts)
    records = tuple(CampaignCounterRecordV180R12R4(row) for row in receipts)
    work = CampaignWorkVectorV180R12R4(receipt_set, records)
    window = _events_by_kind(state.events, "WINDOW_CLOSED")[0]
    zero = CampaignNativeZeroAttestationV180R12R4(
        work,
        window.event_id,
        canonical_json_bytes(inventory.documents_by_id[facts.execution_closure_id]),
    )
    comparison = CampaignComparisonVectorV180R12R4(
        work, zero, _derive_comparison_values(records, zero)
    )
    projection = CampaignProjectionProofV180R12R4(work, comparison, zero)
    return CampaignMeasurementLedgerV180R12R4(
        state,
        subject_id,
        inventory,
        facts.source_manifest_id,
        facts.import_inventory_id,
        receipt_set,
        records,
        work,
        comparison,
        projection,
        zero,
    )


def verify_campaign_measurement_ledger_v180r12r4(
    value: bytes | dict[str, Any],
    *,
    expected_native_zero_source_manifest_id: str,
    expected_native_zero_import_inventory_id: str,
    expected_protocol_id: str | None = None,
    expected_authorization_id: str | None = None,
    expected_attempt_id: str | None = None,
    expected_subject_id: str | None = None,
    expected_max_event_count: int | None = None,
    expected_max_event_byte_count: int | None = None,
    expected_max_ledger_byte_count: int | None = None,
) -> CampaignMeasurementLedgerV180R12R4:
    """Recompute every identity, reducer, zero, and closure field from events."""

    raw, document = _canonical_object(value, "campaign measurement ledger closure")
    if document.get("schema") != "acfqp.campaign_measurement_ledger_closure.v180r12r4":
        _fail("campaign measurement ledger closure schema changed")
    for actual, expected, label in (
        (document.get("protocol_id"), expected_protocol_id, "protocol ID"),
        (document.get("authorization_id"), expected_authorization_id, "authorization ID"),
        (document.get("attempt_id"), expected_attempt_id, "attempt ID"),
        (document.get("subject_id"), expected_subject_id, "subject ID"),
        (
            document.get("native_zero_source_manifest_id"),
            expected_native_zero_source_manifest_id,
            "native-zero source manifest ID",
        ),
        (
            document.get("native_zero_import_inventory_id"),
            expected_native_zero_import_inventory_id,
            "native-zero import inventory ID",
        ),
        (document.get("max_event_count"), expected_max_event_count, "event-count cap"),
        (
            document.get("max_event_byte_count"),
            expected_max_event_byte_count,
            "per-event byte cap",
        ),
        (
            document.get("max_ledger_byte_count"),
            expected_max_ledger_byte_count,
            "ledger byte cap",
        ),
    ):
        if expected is not None and actual != expected:
            _fail(f"campaign measurement ledger expected {label} changed")
    events = document.get("events")
    if type(events) is not list:
        _fail("campaign measurement ledger events must be one list")
    state = replay_campaign_event_chain_v180r12r4(
        events,
        max_event_count=document.get("max_event_count"),
        max_event_byte_count=document.get("max_event_byte_count"),
        max_ledger_byte_count=document.get("max_ledger_byte_count"),
    )
    evidence_documents = document.get("evidence_documents")
    if type(evidence_documents) is not list:
        _fail("campaign measurement ledger evidence documents must be one list")
    inventory = CampaignEvidenceInventoryV180R12R4.from_documents(evidence_documents)
    expected = derive_campaign_measurement_ledger_v180r12r4(
        state,
        subject_id=document.get("subject_id"),
        evidence_documents_by_id=inventory.documents_by_id,
        expected_native_zero_source_manifest_id=(
            expected_native_zero_source_manifest_id
        ),
        expected_native_zero_import_inventory_id=(
            expected_native_zero_import_inventory_id
        ),
    )
    if document != expected.to_document() or raw != expected.canonical_bytes:
        _fail("campaign measurement ledger changed under exact producer-free replay")
    return expected


__all__ = (
    "CAMPAIGN_COUNTER_PATHS",
    "CAMPAIGN_COUNTER_RECORD_COUNT",
    "CAMPAIGN_LEDGER_PHASES",
    "CAMPAIGN_PATH_RECEIPT_COUNT",
    "CAMPAIGN_EVIDENCE_DOCUMENT_COUNT",
    "CAMPAIGN_SCOPE_KIND",
    "CAMPAIGN_SCOPE_MODEL",
    "COMBINED_SUCCESSOR_AUTHORITATIVE_RECEIPT_COUNT",
    "COUNTER_COMPLETENESS_GATE",
    "BREAK_EVEN_GATE",
    "COUNTER_REGISTRY_REFERENCE",
    "FRAME_BYTE_CAP",
    "EVENT_KIND_PHASE",
    "EVENT_KIND_PHASES",
    "EVENT_KIND_ROLE_PHASES",
    "EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS",
    "EVIDENCE_DOCUMENT_TYPE_COUNTS",
    "HASH_OPERATION_FAMILIES",
    "INTEGRITY_OPERATION_FAMILIES",
    "INNER_CONTENT_ID_OPERATION_SUFFIXES",
    "OUTCOME_CODES",
    "INTEGRITY_CHECK_OPERATION_COUNT",
    "PROTOCOL_CHECK_OPERATION_COUNT",
    "PROTOCOL_CHECK_FAMILIES",
    "PROTOCOL_CHECK_OPERATION_LABELS",
    "PRECOMPILED_SOURCE_ROW_FIELDS",
    "PRECOMPILED_TARGET_SOURCE_PATHS",
    "NATIVE_ZERO_SOURCE_FACT_FIELDS",
    "NATIVE_ZERO_OPERATION_SITE_FACT_FIELDS",
    "NATIVE_ZERO_IMPORT_FACT_FIELDS",
    "PREDECESSOR_CAMPAIGN_ACTUAL_RECEIPT_COUNT",
    "PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT",
    "PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT",
    "PREDECESSOR_STRUCTURAL_OBLIGATION_COUNT",
    "REQUIRED_EVENT_KINDS",
    "SCHEMA_VERSION",
    "SEMANTIC_HASH_OPERATION_COUNT",
    "SEMANTIC_HASH_OPERATION_LABELS",
    "INTEGRITY_CHECK_OPERATION_LABELS",
    "SEMANTIC_RECEIPT_AUXILIARY_NAME_BY_KIND",
    "SUCCESS_EVENT_COUNT",
    "SUCCESS_EVENT_EVIDENCE_COUNT",
    "SUCCESS_NULL_EVIDENCE_COUNT",
    "SUCCESSOR_CAMPAIGN_ACTUAL_RECEIPT_COUNT",
    "SUBJECT_RESULT_RUNTIME_BYTE_CAP",
    "TERMINAL_INPUT_BYTE_COUNT",
    "TOTAL_STAGED_INPUT_BYTE_COUNT",
    "VERIFICATION_INPUT_BYTE_COUNT",
    "WORKLOAD_ECONOMICS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "OFFICIAL_EXECUTION_GATE",
    "CampaignComparisonVectorV180R12R4",
    "CampaignCounterRecordV180R12R4",
    "CampaignEvidenceFactsV180R12R4",
    "CampaignEvidenceInventoryV180R12R4",
    "CampaignLedgerEventV180R12R4",
    "CampaignLedgerStateV180R12R4",
    "CampaignMeasurementLedgerV180R12R4",
    "CampaignNativeZeroAttestationV180R12R4",
    "CampaignOperationSpecV180R12R4",
    "CampaignPathReceiptV180R12R4",
    "CampaignPlannedEventV180R12R4",
    "CampaignProjectionProofV180R12R4",
    "CampaignReceiptSetV180R12R4",
    "CampaignWorkVectorV180R12R4",
    "MountVisibilityReplayV180R12R4",
    "ConstructionK7CampaignMeasurementLedgerV180R12R4Error",
    "append_campaign_event_v180r12r4",
    "build_campaign_operation_schedule_v180r12r4",
    "build_campaign_success_event_schedule_v180r12r4",
    "campaign_operation_id_v180r12r4",
    "campaign_operation_manifest_v180r12r4",
    "close_campaign_ledger_v180r12r4",
    "derive_campaign_measurement_ledger_v180r12r4",
    "issue_campaign_attempt_record_v180r12r4",
    "issue_campaign_execution_closure_v180r12r4",
    "issue_campaign_io_transfer_receipt_v180r12r4",
    "issue_native_zero_import_inventory_v180r12r4",
    "issue_native_zero_source_manifest_v180r12r4",
    "issue_subject_commit_receipt_v180r12r4",
    "issue_window_closure_receipt_v180r12r4",
    "open_campaign_ledger_v180r12r4",
    "replay_campaign_event_chain_v180r12r4",
    "replay_mount_visibility_intervals_v180r12r4",
    "validate_campaign_subject_result_document_v180r12r4",
    "verify_campaign_measurement_ledger_v180r12r4",
)
