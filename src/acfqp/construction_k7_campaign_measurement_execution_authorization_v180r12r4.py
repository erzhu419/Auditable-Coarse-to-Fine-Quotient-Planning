"""Outcome-free authorization scaffold for one V180r12r4 measurement attempt."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import stat
import tokenize
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v180r12r4 as domains
from acfqp import construction_k7_campaign_measurement_protocol_v180r12r4 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ZERO_ID = protocol.ZERO_ID
EXPECTED_AUTHORIZATION_ID = ZERO_ID
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = ZERO_ID
EXPECTED_PROTOCOL_ID = "39ac13c2dde86d2d4d1a97475e227def0f2d1cf79be7d7998564ca99cd5afe9e"
EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID = (
    "57f9877f10e8cfa85cd13cc9ae1dd92d5a0faf9f9f8ffacc9856904f6b5b9504"
)
EXPECTED_SOURCE_CLOSURE_ID = ZERO_ID
EXPECTED_SOURCE_CLOSURE_BYTE_COUNT = 0
EXPECTED_SOURCE_CLOSURE_SHA256 = ZERO_ID
EXPECTED_SOURCE_CLOSURE_FILE_COUNT = 0

LOGICAL_OCCURRENCE_ID = protocol.LOGICAL_OCCURRENCE_ID
EXECUTION_NONCE = protocol.EXECUTION_NONCE
WALL_TIMEOUT_SECONDS = protocol.WALL_TIMEOUT_SECONDS
CAMPAIGN_CLEANUP_GRACE_SECONDS = protocol.CAMPAIGN_CLEANUP_GRACE_SECONDS
TERMINATION_GRACE_SECONDS = protocol.TERMINATION_GRACE_SECONDS
MEMORY_MAX_BYTES = protocol.MEMORY_MAX_BYTES
ADDRESS_SPACE_HARD_CAP_BYTES = protocol.ADDRESS_SPACE_HARD_CAP_BYTES
PIDS_MAX = protocol.PIDS_MAX
INPUT_FILE_BYTE_CAP = protocol.INPUT_FILE_BYTE_CAP
INPUT_TOTAL_BYTE_CAP = protocol.INPUT_TOTAL_BYTE_CAP
SUBJECT_RESULT_BYTE_CAP = protocol.SUBJECT_RESULT_BYTE_CAP
SUBJECT_RESULT_RUNTIME_BYTE_CAP = protocol.SUBJECT_RESULT_RUNTIME_BYTE_CAP
FRAME_BYTE_CAP = protocol.FRAME_BYTE_CAP
SOCK_SEQPACKET_BUFFER_REQUEST_BYTES = (
    protocol.SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
)
SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES = (
    protocol.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
)
TERMINAL_BYTE_CAP = protocol.TERMINAL_BYTE_CAP
VERIFICATION_BYTE_CAP = protocol.VERIFICATION_BYTE_CAP
EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP = (
    protocol.EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP
)
EXECUTION_CLOSURE_BYTE_CAP = protocol.EXECUTION_CLOSURE_BYTE_CAP
OS_RECEIPT_BUNDLE_BYTE_CAP = protocol.OS_RECEIPT_BUNDLE_BYTE_CAP
LEDGER_CLOSURE_BYTE_CAP = protocol.LEDGER_CLOSURE_BYTE_CAP
STDOUT_BYTE_CAP = protocol.STDOUT_BYTE_CAP
STDERR_BYTE_CAP = protocol.STDERR_BYTE_CAP
FAILURE_EMERGENCY_RESERVE_BYTES = protocol.FAILURE_EMERGENCY_RESERVE_BYTES
FAILURE_MESSAGE_BYTE_CAP = protocol.FAILURE_MESSAGE_BYTE_CAP
FAILURE_ARTIFACT_OBSERVATION_ROW_CAP = (
    protocol.FAILURE_ARTIFACT_OBSERVATION_ROW_CAP
)
FAILURE_ARTIFACT_METADATA_BYTE_CAP = protocol.FAILURE_ARTIFACT_METADATA_BYTE_CAP
FAILURE_DIRECTORY_ENTRY_CAP = protocol.FAILURE_DIRECTORY_ENTRY_CAP
FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP = (
    protocol.FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP
)
FAILURE_ARTIFACT_HASH_BYTE_CAP = protocol.FAILURE_ARTIFACT_HASH_BYTE_CAP
FAILURE_CGROUP_OBSERVATION_FIELDS = protocol.FAILURE_CGROUP_OBSERVATION_FIELDS
FAILURE_CGROUP_NODE_OBSERVATION_FIELDS = (
    protocol.FAILURE_CGROUP_NODE_OBSERVATION_FIELDS
)
FAILURE_CGROUP_NODE_ROLES = protocol.FAILURE_CGROUP_NODE_ROLES
FAILURE_CGROUP_NODE_STATES = protocol.FAILURE_CGROUP_NODE_STATES
VERIFICATION_FAILURE_SCHEMA = protocol.VERIFICATION_FAILURE_SCHEMA
VERIFICATION_FAILURE_FIELDS = protocol.VERIFICATION_FAILURE_FIELDS
VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS = (
    protocol.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
)
VERIFICATION_FAILURE_OBSERVATION_BOUNDARY = (
    protocol.VERIFICATION_FAILURE_OBSERVATION_BOUNDARY
)
VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES = (
    protocol.VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES
)
VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP = (
    protocol.VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP
)
VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP = (
    protocol.VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP
)
MAX_EVENT_COUNT = protocol.MAX_EVENT_COUNT
MAX_EVENT_BYTE_COUNT = protocol.MAX_EVENT_BYTE_COUNT
MAX_LEDGER_BYTE_COUNT = protocol.MAX_LEDGER_BYTE_COUNT

OUTPUT_ROOT_RELATIVE_PATH = protocol.OUTPUT_ROOT_RELATIVE_PATH
ATTEMPT_RELATIVE_PATH = protocol.ATTEMPT_RELATIVE_PATH
TERMINAL_RELATIVE_PATH = protocol.TERMINAL_RELATIVE_PATH
FAILURE_RELATIVE_PATH = protocol.FAILURE_RELATIVE_PATH
VERIFICATION_RELATIVE_PATH = protocol.VERIFICATION_RELATIVE_PATH
VERIFICATION_FAILURE_RELATIVE_PATH = protocol.VERIFICATION_FAILURE_RELATIVE_PATH
RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH = (
    protocol.RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH
)
RUNTIME_CAS_ROOT_RELATIVE_PATH = protocol.RUNTIME_CAS_ROOT_RELATIVE_PATH
EVENTS_RELATIVE_PATH = protocol.EVENTS_RELATIVE_PATH
SUBJECT_TEMP_RELATIVE_PATH = protocol.SUBJECT_TEMP_RELATIVE_PATH
SUBJECT_RESULT_RELATIVE_PATH = protocol.SUBJECT_RESULT_RELATIVE_PATH
EVIDENCE_INVENTORY_RELATIVE_PATH = protocol.EVIDENCE_INVENTORY_RELATIVE_PATH
EXECUTION_CLOSURE_RELATIVE_PATH = protocol.EXECUTION_CLOSURE_RELATIVE_PATH
OS_RECEIPT_RELATIVE_PATH = protocol.OS_RECEIPT_RELATIVE_PATH
LEDGER_CLOSURE_RELATIVE_PATH = protocol.LEDGER_CLOSURE_RELATIVE_PATH
SUCCESS_ARTIFACT_ORDER = protocol.SUCCESS_ARTIFACT_ORDER
SUCCESS_ARTIFACT_SCHEMA_ROWS = protocol.SUCCESS_ARTIFACT_SCHEMA_ROWS
SUCCESS_DURABLE_ARTIFACT_ROWS = protocol.SUCCESS_DURABLE_ARTIFACT_ROWS
SUCCESS_DURABLE_WRITE_ORDER = protocol.SUCCESS_DURABLE_WRITE_ORDER

SOURCE_CLOSURE_REQUIRED_ROOTS = protocol.SOURCE_CLOSURE_REQUIRED_ROOTS
SOURCE_CATALOG_MODULE_CAP = 4_096
SOURCE_CATALOG_TOTAL_BYTE_CAP = 128 * 1024 * 1024
AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS = (
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
    "EXPECTED_SOURCE_CLOSURE_ID",
    "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT",
    "EXPECTED_SOURCE_CLOSURE_SHA256",
    "EXPECTED_SOURCE_CLOSURE_FILE_COUNT",
)
_AUTHORIZATION_EVIDENCE_STRING_CONSTANTS = frozenset(
    {
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
        "EXPECTED_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_ID",
        "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
        "EXPECTED_SOURCE_CLOSURE_ID",
        "EXPECTED_SOURCE_CLOSURE_SHA256",
    }
)
_AUTHORIZATION_EVIDENCE_INTEGER_CONSTANTS = frozenset(
    {
        "EXPECTED_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
        "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT",
        "EXPECTED_SOURCE_CLOSURE_FILE_COUNT",
    }
)
_POST_PREREG_REDACTED_STRING_LITERAL = (
    b'"0000000000000000000000000000000000000000000000000000000000000000"'
)
_POST_PREREG_REDACTED_INTEGER_LITERAL = b"0"

_ROOT = Path(__file__).resolve().parents[2]
_AUTHORIZATION_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_authorization_evidence_freeze_"
    "v180r12r4.py"
)


class CampaignMeasurementExecutionAuthorizationV180R12R4Error(ValueError):
    """The protocol, capability facts, source contract, or caps changed."""


def _fail(message: str) -> NoReturn:
    raise CampaignMeasurementExecutionAuthorizationV180R12R4Error(message)


def _normalized_relative_path(value: Any, label: str) -> str:
    if type(value) is not str:
        _fail(f"{label} must be a relative path")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or candidate.as_posix() != value
    ):
        _fail(f"{label} must be one normalized relative path")
    return value


def _read_regular_stable(relative_path: str) -> bytes:
    path = _ROOT / _normalized_relative_path(relative_path, "source path")
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _fail(f"authorization source is linked or nonregular: {relative_path}")
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as error:
        raise CampaignMeasurementExecutionAuthorizationV180R12R4Error(
            f"authorization source is absent or unreadable: {relative_path}"
        ) from error
    try:
        opened = os.fstat(descriptor)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, SOURCE_CATALOG_TOTAL_BYTE_CAP + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > SOURCE_CATALOG_TOTAL_BYTE_CAP:
                _fail("one authorization source exceeds the total source cap")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fact = lambda row: (  # noqa: E731
        row.st_dev,
        row.st_ino,
        row.st_mode,
        row.st_nlink,
        row.st_size,
        row.st_mtime_ns,
        row.st_ctime_ns,
    )
    raw = b"".join(chunks)
    if not (
        fact(before) == fact(opened) == fact(after)
        and len(raw) == before.st_size
        and len(raw) <= SOURCE_CATALOG_TOTAL_BYTE_CAP
    ):
        _fail(f"authorization source changed during read: {relative_path}")
    return raw


def _authorization_evidence_literal_spans(
    raw: bytes,
) -> dict[str, tuple[int, int, bytes]]:
    """Locate the exact independent twelve-literal mutation surface."""

    if type(raw) is not bytes:
        raise TypeError("authorization-evidence wrapper source must be bytes")
    try:
        tree = ast.parse(raw, filename=_AUTHORIZATION_EVIDENCE_RELATIVE_PATH)
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise CampaignMeasurementExecutionAuthorizationV180R12R4Error(
            "authorization-evidence wrapper is not static UTF-8 Python"
        ) from error
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    wanted = set(AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS)
    if not (
        len(wanted) == 12
        and not (
            _AUTHORIZATION_EVIDENCE_STRING_CONSTANTS
            & _AUTHORIZATION_EVIDENCE_INTEGER_CONSTANTS
        )
        and (
            _AUTHORIZATION_EVIDENCE_STRING_CONSTANTS
            | _AUTHORIZATION_EVIDENCE_INTEGER_CONSTANTS
        )
        == wanted
    ):
        raise AssertionError("authorization-evidence literal partition changed")
    spans: dict[str, tuple[int, int, bytes]] = {}
    literal_values: dict[str, str | int] = {}
    for statement in tree.body:
        exact_assignment = (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        )
        if exact_assignment:
            name = statement.targets[0].id
            value = statement.value
        else:
            bound_names = {
                node.id
                for node in ast.walk(statement)
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
            }
            bound_names.update(
                node.name
                for node in ast.walk(statement)
                if isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef))
            )
            for node in ast.walk(statement):
                if isinstance(node, ast.Import):
                    bound_names.update(
                        alias.asname or alias.name.partition(".")[0]
                        for alias in node.names
                    )
                elif isinstance(node, ast.ImportFrom):
                    bound_names.update(alias.asname or alias.name for alias in node.names)
            if bound_names & wanted:
                _fail(
                    "post-prereg anchor must be one direct top-level "
                    "Assign(Constant)"
                )
            continue
        if name not in wanted:
            continue
        if name in spans:
            _fail("post-prereg redacted constant is duplicated or valueless")
        literal = value.value if isinstance(value, ast.Constant) else None
        if name in _AUTHORIZATION_EVIDENCE_STRING_CONSTANTS:
            if type(literal) is not str:
                _fail("post-prereg string anchor is not one literal")
            replacement = _POST_PREREG_REDACTED_STRING_LITERAL
            expected_token = tokenize.STRING
        elif name in _AUTHORIZATION_EVIDENCE_INTEGER_CONSTANTS:
            if type(literal) is not int:
                _fail("post-prereg integer anchor is not one literal")
            replacement = _POST_PREREG_REDACTED_INTEGER_LITERAL
            expected_token = tokenize.NUMBER
        else:  # pragma: no cover - the two sets partition the allowlist
            raise AssertionError
        if not all(
            type(row) is int
            for row in (
                value.lineno,
                value.col_offset,
                value.end_lineno,
                value.end_col_offset,
            )
        ):
            _fail("post-prereg literal lacks one exact source span")
        start = offsets[value.lineno - 1] + value.col_offset
        end = offsets[value.end_lineno - 1] + value.end_col_offset
        if not (0 <= start < end <= len(raw)):
            _fail("post-prereg literal source span is invalid")
        try:
            tokens = tuple(
                token
                for token in tokenize.tokenize(
                    io.BytesIO(raw[start:end]).readline
                )
                if token.type
                not in {
                    tokenize.ENCODING,
                    tokenize.ENDMARKER,
                    tokenize.NEWLINE,
                    tokenize.NL,
                }
            )
        except (IndentationError, SyntaxError, tokenize.TokenError) as error:
            raise CampaignMeasurementExecutionAuthorizationV180R12R4Error(
                "post-prereg literal tokenization failed"
            ) from error
        if len(tokens) != 1 or tokens[0].type != expected_token:
            _fail("post-prereg anchor must be exactly one lexical literal token")
        spans[name] = (start, end, replacement)
        literal_values[name] = literal
    if set(spans) != wanted:
        _fail("post-prereg redacted constant allowlist is incomplete")
    all_sentinels = all(
        value == (ZERO_ID if name in _AUTHORIZATION_EVIDENCE_STRING_CONSTANTS else 0)
        for name, value in literal_values.items()
    )
    all_frozen = all(
        (
            type(value) is str
            and value != ZERO_ID
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )
        if name in _AUTHORIZATION_EVIDENCE_STRING_CONSTANTS
        else type(value) is int and value > 0
        for name, value in literal_values.items()
    )
    if not (all_sentinels or all_frozen):
        _fail("post-prereg anchors mix sentinel, frozen, or invalid phases")
    return spans


def normalize_authorization_evidence_wrapper_source_v180r12r4(
    raw: bytes,
) -> bytes:
    """Restore only the evidence wrapper's twelve C_pre sentinel literals."""

    result = raw
    previous_start = len(raw)
    for start, end, replacement in sorted(
        _authorization_evidence_literal_spans(raw).values(), reverse=True
    ):
        if end > previous_start:
            _fail("post-prereg literal source spans overlap")
        result = result[:start] + replacement + result[end:]
        previous_start = start
    return result


def replay_authorization_source_facts_v180r12r4(
    relative_paths: Sequence[str] = SOURCE_CLOSURE_REQUIRED_ROOTS,
) -> list[dict[str, Any]]:
    """Read an explicit completed closure; never discover or execute imports."""

    if isinstance(relative_paths, (str, bytes)) or not isinstance(
        relative_paths, Sequence
    ):
        _fail("source closure paths must be one exact sequence")
    paths = tuple(
        _normalized_relative_path(value, "source closure path")
        for value in relative_paths
    )
    if not (
        paths
        and len(paths) <= SOURCE_CATALOG_MODULE_CAP
        and tuple(sorted(set(paths))) == paths
    ):
        _fail("source closure paths must be sorted, unique, and capped")
    rows = []
    total = 0
    for relative_path in paths:
        raw = _read_regular_stable(relative_path)
        bound_raw = (
            normalize_authorization_evidence_wrapper_source_v180r12r4(raw)
            if relative_path == _AUTHORIZATION_EVIDENCE_RELATIVE_PATH
            else raw
        )
        total += len(bound_raw)
        if total > SOURCE_CATALOG_TOTAL_BYTE_CAP:
            _fail("authorization source closure exceeds its total byte cap")
        rows.append(
            {
                "relative_path": relative_path,
                "byte_count": len(bound_raw),
                "sha256": hashlib.sha256(bound_raw).hexdigest(),
            }
        )
    return rows


def _validate_source_facts(value: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _fail("source facts must be one sequence")
    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            _fail("source fact must be one mapping")
        row = dict(item)
        if set(row) != {"relative_path", "byte_count", "sha256"}:
            _fail("source fact field set changed")
        _normalized_relative_path(row["relative_path"], "source fact path")
        if not (
            type(row["byte_count"]) is int
            and row["byte_count"] >= 0
            and type(row["sha256"]) is str
            and len(row["sha256"]) == 64
            and all(character in "0123456789abcdef" for character in row["sha256"])
        ):
            _fail("source fact size or digest changed")
        rows.append(row)
    paths = tuple(row["relative_path"] for row in rows)
    if not (
        len(rows) <= SOURCE_CATALOG_MODULE_CAP
        and tuple(sorted(set(paths))) == paths
        and sum(row["byte_count"] for row in rows) <= SOURCE_CATALOG_TOTAL_BYTE_CAP
    ):
        _fail("source facts are not sorted, unique, or capped")
    return rows


def source_closure_candidate_v180r12r4(
    source_facts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = _validate_source_facts(source_facts)
    payload = {
        "schema": "acfqp.v180r12r4_authorization_source_closure.v1",
        "source_facts": rows,
        "source_fact_count": len(rows),
        "source_total_byte_count": sum(row["byte_count"] for row in rows),
        "required_static_roots": list(SOURCE_CLOSURE_REQUIRED_ROOTS),
        "transitive_local_import_closure_required": True,
        "authorization_self_normalized_by_evidence_freeze": True,
    }
    raw = canonical_json_bytes(payload)
    return {
        **payload,
        "source_closure_id": hashlib.sha256(raw).hexdigest(),
        "source_closure_byte_count": len(raw),
        "source_closure_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _resource_caps() -> dict[str, Any]:
    return {
        "applies_to": [
            "FRESH_PRODUCER_FREE_CAMPAIGN_MEASUREMENT_SUCCESSOR",
            "PRODUCER_FREE_INDEPENDENT_VERIFICATION_AND_RETAINED_REPLAY",
        ],
        "wall_timeout_seconds": WALL_TIMEOUT_SECONDS,
        "campaign_cleanup_grace_seconds": CAMPAIGN_CLEANUP_GRACE_SECONDS,
        "termination_grace_seconds": TERMINATION_GRACE_SECONDS,
        "absolute_deadline_origin_and_formula": (
            "POST_ATTEMPT_MONOTONIC_ORIGIN_HARD_14400_CAMPAIGN_HARD_MINUS_600"
        ),
        "memory_max_bytes": MEMORY_MAX_BYTES,
        "address_space_hard_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
        "pids_max": PIDS_MAX,
        "input_file_byte_cap": INPUT_FILE_BYTE_CAP,
        "input_total_byte_cap": INPUT_TOTAL_BYTE_CAP,
        "subject_result_byte_cap": SUBJECT_RESULT_BYTE_CAP,
        "subject_result_runtime_byte_cap": SUBJECT_RESULT_RUNTIME_BYTE_CAP,
        "runtime_ipc_frame_byte_cap": FRAME_BYTE_CAP,
        "sock_seqpacket_buffer_request_bytes": (
            SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
        ),
        "sock_seqpacket_effective_min_bytes": (
            SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        ),
        "sock_seqpacket_buffer_applies_to_both_endpoints_of_both_pairs": True,
        "sock_seqpacket_buffers_configured_and_read_back_before_clone_or_send": True,
        "sock_seqpacket_insufficient_effective_buffer_fails_before_child_creation": True,
        "terminal_byte_cap": TERMINAL_BYTE_CAP,
        "verification_byte_cap": VERIFICATION_BYTE_CAP,
        "evidence_inventory_bundle_byte_cap": (
            EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP
        ),
        "execution_closure_byte_cap": EXECUTION_CLOSURE_BYTE_CAP,
        "os_receipt_bundle_byte_cap": OS_RECEIPT_BUNDLE_BYTE_CAP,
        "ledger_closure_byte_cap": LEDGER_CLOSURE_BYTE_CAP,
        "stdout_byte_cap": STDOUT_BYTE_CAP,
        "stderr_byte_cap": STDERR_BYTE_CAP,
        "failure_emergency_reserve_bytes": FAILURE_EMERGENCY_RESERVE_BYTES,
        "failure_message_byte_cap": FAILURE_MESSAGE_BYTE_CAP,
        "failure_artifact_observation_row_cap": (
            FAILURE_ARTIFACT_OBSERVATION_ROW_CAP
        ),
        "failure_artifact_metadata_byte_cap": FAILURE_ARTIFACT_METADATA_BYTE_CAP,
        "failure_directory_entry_cap": FAILURE_DIRECTORY_ENTRY_CAP,
        "failure_directory_entry_name_total_byte_cap": (
            FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP
        ),
        "failure_artifact_streaming_hash_byte_cap": (
            FAILURE_ARTIFACT_HASH_BYTE_CAP
        ),
        "max_event_count": MAX_EVENT_COUNT,
        "max_event_byte_count": MAX_EVENT_BYTE_COUNT,
        "max_ledger_byte_count": MAX_LEDGER_BYTE_COUNT,
        "source_catalog_module_cap": SOURCE_CATALOG_MODULE_CAP,
        "source_catalog_total_byte_cap": SOURCE_CATALOG_TOTAL_BYTE_CAP,
        "whole_process_tree_caps_required": True,
        "rlimit_as_required_for_supervisor_and_worker": True,
        "monotonic_parent_deadline_required": True,
        "clone3_clone_into_cgroup_required": True,
        "clone3_leaf_directory_fd_required": True,
        "pidfd_required_for_both_births": True,
        "pidfd_wait_and_reap_required_for_both_births": True,
        "measurement_root_memory_max_written_before_first_birth": True,
        "measurement_root_pids_max_written_before_first_birth": True,
        "measurement_root_pids_max_exact": 2,
        "measurement_root_is_process_empty": True,
        "supervisor_and_worker_sibling_leaves_required": True,
        "root_and_leaf_populated_zero_before_peak_observation": True,
        "same_root_memory_peak_and_pids_peak_observation_required": True,
        "cgroup_kill_on_failure_required": True,
        "cap_violation_consumes_attempt_identity": True,
        "caps_may_not_be_raised_under_frozen_authorization": True,
        "ledger_observer_overhead_is_campaign_actual_measurement": False,
    }


def build_campaign_measurement_execution_authorization_v180r12r4(
    *,
    cgroup_parent_fact: Mapping[str, Any],
    runtime_capability_fact: Mapping[str, Any],
    source_facts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    frozen_protocol = protocol.freeze_campaign_measurement_protocol_v180r12r4(
        cgroup_parent_fact=cgroup_parent_fact,
        runtime_capability_fact=runtime_capability_fact,
    )
    protocol_document = frozen_protocol.to_document()
    prelaunch_contract = protocol.prelaunch_contract_v180r12r4()
    evidence_inventory_contract = protocol.evidence_inventory_contract_v180r12r4()
    durable_artifact_contract = protocol.durable_artifact_contract_v180r12r4()
    success_artifact_contract = (
        protocol.success_durable_artifact_contract_v180r12r4()
    )
    failure_observation_contract = protocol.failure_observation_contract_v180r12r4()
    event_grammar = protocol.event_grammar_v180r12r4()
    attempt_identity_contract = (
        protocol.campaign_measurement_attempt_identity_contract_v180r12r4()
    )
    semantic_hash_scope = protocol.semantic_hash_counter_scope_contract_v180r12r4()
    repair_lineage = (
        protocol.failed_dispatch_repair_lineage_contract_v180r12r4()
    )
    failed_external_replay = (
        protocol.failed_external_replay_repair_lineage_contract_v180r12r4()
    )
    failed_scientific_birth = (
        protocol.failed_scientific_birth_repair_lineage_contract_v180r12r4()
    )
    failed_ordinal8 = (
        protocol.failed_ordinal8_repair_lineage_contract_v180r12r4()
    )
    failed_ordinal9 = (
        protocol.failed_ordinal9_repair_lineage_contract_v180r12r4()
    )
    failed_ordinal10 = (
        protocol.failed_ordinal10_repair_lineage_contract_v180r12r4()
    )
    failed_ordinal11 = (
        protocol.failed_ordinal11_repair_lineage_contract_v180r12r4()
    )
    service_context_capture = (
        protocol.service_context_capture_contract_v180r12r4()
    )
    runner_execution_envelope = (
        protocol.source_bound_runner_execution_envelope_contract_v180r12r4()
    )
    supplied_source_facts = (
        [] if source_facts is None else _validate_source_facts(source_facts)
    )
    if source_facts is not None and not set(SOURCE_CLOSURE_REQUIRED_ROOTS) <= {
        row["relative_path"] for row in supplied_source_facts
    }:
        _fail("supplied source closure omits a preregistered static root")
    closure = source_closure_candidate_v180r12r4(supplied_source_facts)
    closure_frozen = source_facts is not None and EXPECTED_SOURCE_CLOSURE_ID != ZERO_ID
    if not (
        (
            EXPECTED_PROTOCOL_ID == ZERO_ID
            or frozen_protocol.campaign_measurement_protocol_id
            == EXPECTED_PROTOCOL_ID
        )
        and (
            EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID == ZERO_ID
            or frozen_protocol.campaign_measurement_execution_slot_id
            == EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID
        )
        and protocol_document["cgroup_parent_fact"]
        == protocol.validate_cgroup_parent_fact_v180r12r4(cgroup_parent_fact)
        and protocol_document["runtime_capability_fact"]
        == protocol.validate_runtime_capability_fact_v180r12r4(runtime_capability_fact)
        and protocol_document["cgroup_parent_fact"]["owner_uid"]
        == protocol_document["runtime_capability_fact"]["uid"]
        and protocol_document["cgroup_parent_fact"]["owner_gid"]
        == protocol_document["runtime_capability_fact"]["gid"]
        and protocol_document["campaign_measurement_attempt_identity_contract"]
        == attempt_identity_contract
        and attempt_identity_contract["attempt_schema"]
        == protocol.CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA
        and attempt_identity_contract["attempt_domain"]
        == protocol.CAMPAIGN_MEASUREMENT_ATTEMPT_DOMAIN
        and tuple(attempt_identity_contract["payload_fields"])
        == protocol.CAMPAIGN_MEASUREMENT_ATTEMPT_PAYLOAD_FIELDS
        and attempt_identity_contract["identity_input_count"] == 6
        and protocol_document["semantic_hash_counter_scope_contract"]
        == semantic_hash_scope
        and semantic_hash_scope["counted_operation_count"] == 137
        and protocol_document["campaign_path_count"] == 9
        and protocol_document["campaign_actual_counter_record_count"] == 0
        and protocol_document["prelaunch_contract"] == prelaunch_contract
        and protocol_document["failed_dispatch_repair_lineage"]
        == repair_lineage
        and protocol_document["failed_external_replay_repair_lineage"]
        == failed_external_replay
        and protocol_document["failed_scientific_birth_repair_lineage"]
        == failed_scientific_birth
        and protocol_document["failed_ordinal8_repair_lineage"]
        == failed_ordinal8
        and protocol_document["failed_ordinal9_repair_lineage"]
        == failed_ordinal9
        and protocol_document["failed_ordinal10_repair_lineage"]
        == failed_ordinal10
        and protocol_document["failed_ordinal11_repair_lineage"]
        == failed_ordinal11
        and protocol_document["failed_v180r12r3_identity_rerun_forbidden"]
        is True
        and protocol_document["failed_v180r12r3r1_identity_rerun_forbidden"]
        is True
        and protocol_document["failed_v180r12r3r2_identity_rerun_forbidden"]
        is True
        and protocol_document[
            "failed_v180r12r4r2_ordinal8_identity_rerun_forbidden"
        ]
        is True
        and protocol_document[
            "failed_v180r12r4r4_ordinal9_identity_rerun_forbidden"
        ]
        is True
        and protocol_document[
            "failed_v180r12r4r5_ordinal10_identity_rerun_forbidden"
        ]
        is True
        and protocol_document[
            "failed_v180r12r4r6_ordinal11_identity_rerun_forbidden"
        ]
        is True
        and protocol_document["repair_scope"]
        == failed_ordinal11["repair_scope"]
        == protocol.V180R12R4_REPAIR_SCOPE
        and failed_ordinal10["repair_scope"]
        == protocol.V180R12R4R5_REPAIR_SCOPE
        and failed_ordinal9["repair_scope"]
        == protocol.V180R12R4R4_REPAIR_SCOPE
        and failed_ordinal8["repair_scope"]
        == protocol.V180R12R4R3_REPAIR_SCOPE
        and failed_external_replay["repair_scope"]
        == "AUTHORIZATION_EVIDENCE_WRAPPER_SOURCE_FACT_NORMALIZATION_ONLY"
        and protocol_document["source_bound_runner_execution_envelope_contract"]
        == runner_execution_envelope
        and prelaunch_contract["precompiled_runner_module_contract"]
        == runner_execution_envelope
        and len(SOURCE_CLOSURE_REQUIRED_ROOTS) == 26
        and protocol.V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and protocol.V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and protocol.V180R12R3R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and protocol.V180R12R4R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and protocol.V180R12R4R4_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and protocol.V180R12R4R5_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and protocol.V180R12R4R6_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and repair_lineage["scientific_attempt_record_present"] is False
        and repair_lineage["scientific_occurrence_started"] is False
        and repair_lineage["campaign_actual_measurement"] is False
        and repair_lineage["measurement_cgroup_created"] is False
        and repair_lineage[
            "all_required_successor_paths_absent_at_failure_freeze"
        ]
        is True
        and repair_lineage["fresh_successor_identity_required"] is True
        and repair_lineage[
            "runtime_replay_is_pre_scientific_prereg_authority"
        ]
        is True
        and repair_lineage[
            "retained_artifact_absence_and_cgroup_reads_are_campaign_actual_"
            "measurement"
        ]
        is False
        and failed_external_replay["scientific_attempt_record_present"] is False
        and failed_external_replay["scientific_occurrence_started"] is False
        and failed_external_replay["campaign_actual_measurement"] is False
        and failed_external_replay["measurement_cgroup_created"] is False
        and failed_external_replay["same_campaign_attempt_rerun_forbidden"]
        is True
        and failed_external_replay["same_launch_attempt_rerun_forbidden"] is True
        and failed_external_replay[
            "inherited_v180r12r3_dispatch_repair_preserved"
        ]
        is True
        and failed_external_replay[
            "source_bound_authorization_replay_must_use_c_pre_normalized_sources"
        ]
        is True
        and failed_external_replay[
            "raw_post_literal_wrapper_authorization_replay_forbidden"
        ]
        is True
        and failed_external_replay["fresh_successor_identity_required"] is True
        and failed_external_replay[
            "repair_changes_scientific_scope_or_denominators"
        ]
        is False
        and failed_scientific_birth["scientific_attempt_record_present"] is True
        and failed_scientific_birth["scientific_occurrence_started"] is True
        and failed_scientific_birth["durable_scientific_event_prefix_present"]
        is True
        and failed_scientific_birth["campaign_counter_records_issued"] is False
        and failed_scientific_birth["successful_ledger_claimed"] is False
        and failed_scientific_birth["producer_free_verification_attempted"]
        is False
        and failed_scientific_birth["same_campaign_attempt_rerun_forbidden"]
        is True
        and failed_scientific_birth["same_launch_attempt_rerun_forbidden"]
        is True
        and failed_scientific_birth["fresh_successor_identity_required"] is True
        and failed_scientific_birth[
            "repair_changes_campaign_path_roles_event_schedule_evidence_"
            "cardinality_or_reducers"
        ]
        is False
        and failed_ordinal8["historical_failure_code_misclassified"] is True
        and failed_ordinal8["outer_service_unit_ownership_acquired"] is True
        and failed_ordinal8["full_cgroup_conformance"] is False
        and failed_ordinal8["full_property_diagnostic_recorded"] is False
        and failed_ordinal8["counter_records_issued"] is False
        and failed_ordinal8["work_vectors_issued"] is False
        and failed_ordinal8["comparison_vectors_issued"] is False
        and failed_ordinal8["same_identity_rerun_forbidden"] is True
        and failed_ordinal9["campaign_attempt_artifact_present"] is False
        and failed_ordinal9["campaign_started"] is False
        and failed_ordinal9["outer_service_unit_ownership_acquired"] is True
        and failed_ordinal9["full_source_conformance"] is False
        and failed_ordinal9["postmortem_full_property_diagnostic_recorded"]
        is True
        and failed_ordinal9["counter_records_issued"] is False
        and failed_ordinal9["work_vectors_issued"] is False
        and failed_ordinal9["comparison_vectors_issued"] is False
        and failed_ordinal9["same_identity_rerun_forbidden"] is True
        and failed_ordinal9["fresh_successor_identity_required"] is True
        and failed_ordinal10["campaign_attempt_artifact_present"] is False
        and failed_ordinal10["campaign_started"] is False
        and failed_ordinal10["outer_service_unit_ownership_acquired"] is True
        and failed_ordinal10["full_source_conformance"] is True
        and failed_ordinal10["runtime_failure_generic_cause_recorded"] is True
        and failed_ordinal10["runtime_failure_property_snapshots_recorded"]
        is False
        and failed_ordinal10["runtime_failure_per_field_mismatch_recorded"]
        is False
        and failed_ordinal10["runtime_failure_exact_cause_dimension_recorded"]
        is False
        and failed_ordinal10["counter_records_issued"] is False
        and failed_ordinal10["work_vectors_issued"] is False
        and failed_ordinal10["comparison_vectors_issued"] is False
        and failed_ordinal10["same_identity_rerun_forbidden"] is True
        and failed_ordinal10["fresh_successor_identity_required"] is True
        and failed_ordinal11["scientific_attempt_opened"] is True
        and failed_ordinal11["completed_event_count"] == 1
        and failed_ordinal11["full_source_conformance"] is True
        and failed_ordinal11["full_host_conformance"] is True
        and failed_ordinal11["host_conformance_mismatch_count"] == 0
        and failed_ordinal11["host_conformance_cause"] is None
        and failed_ordinal11["full_t1_t2_conformance"] is False
        and failed_ordinal11["t1_t2_same_formal_service"] is True
        and failed_ordinal11["t1_t2_same_source_membership"] is True
        and failed_ordinal11["t1_t2_same_service_directory"] is True
        and failed_ordinal11["only_mismatch"]["field"] == "t2.pid"
        and failed_ordinal11["exact_failure_cause"]
        == "T1_T2_PID_ROLE_CONFLATION"
        and failed_ordinal11["distinct_process_roles"] is True
        and failed_ordinal11["cleanup_complete"] is True
        and failed_ordinal11["counter_records_issued"] is False
        and failed_ordinal11["work_vectors_issued"] is False
        and failed_ordinal11["comparison_vectors_issued"] is False
        and failed_ordinal11["same_identity_rerun_forbidden"] is True
        and failed_ordinal11["fresh_successor_identity_required"] is True
        and protocol_document["service_context_capture_contract"]
        == service_context_capture
        and protocol_document["terminal_evidence_inventory_contract"]
        == evidence_inventory_contract
        and protocol_document["durable_artifact_contract"]
        == durable_artifact_contract
        and durable_artifact_contract["success_artifact_contract"]
        == success_artifact_contract
        and success_artifact_contract["producer_write_order"]
        == list(SUCCESS_DURABLE_WRITE_ORDER)
        and success_artifact_contract["evidence_inventory_document_count"]
        == 328
        and success_artifact_contract["os_receipt_document_count"] == 12
        and protocol_document["failure_observation_contract"]
        == failure_observation_contract
        and failure_observation_contract[
            "success_evidence_inventory_document_count"
        ]
        == 328
        and failure_observation_contract[
            "failure_observations_in_success_evidence_inventory"
        ]
        is False
        and failure_observation_contract[
            "failure_cgroup_observation_is_campaign_success_receipt"
        ]
        is False
        and protocol_document["event_grammar"] == event_grammar
        and event_grammar["fallible_paired_operation_count"] == 307
        and event_grammar[
            "every_fallible_paired_operation_emits_exact_intent_then_outcome"
        ]
        is True
        and event_grammar["process_birth_operations_emit_intent_outcome_then_reap"]
        is True
        and event_grammar["mount_interval_operations_emit_open_then_close"] is True
        and event_grammar["singleton_operation_count"] == 5
        and event_grammar["unqualified_every_operation_intent_outcome_claim"]
        is False
        and evidence_inventory_contract["typed_document_count"] == 328
        and evidence_inventory_contract["nonnull_event_evidence_count"] == 317
        and evidence_inventory_contract["null_event_evidence_count"] == 308
        and evidence_inventory_contract["causal_join_rules"]
        == list(protocol.EVIDENCE_CAUSAL_JOIN_RULES)
        and evidence_inventory_contract[
            "semantic_receipt_count_bound_to_attempt_record"
        ]
        == 297
        and evidence_inventory_contract[
            "successful_event_may_reference_not_yet_issued_evidence"
        ]
        is False
        and event_grammar[
            "successful_event_evidence_id_must_be_issued_before_event_append"
        ]
        is True
        and protocol_document["predecessor_occurrence_authoritative_receipt_count"]
        == 90
        and protocol_document["successful_campaign_authoritative_receipt_count"]
        == 9
        and protocol_document["successful_combined_authoritative_receipt_count"]
        == 99
        and protocol_document["V180R12R2_COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and protocol_document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and protocol_document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and protocol_document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
        and protocol_document["BREAK_EVEN_GATE"] == "NOT_RUN"
        and protocol_document["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
        and protocol_document["official_scalar_cost"] is None
        and protocol_document["official_N_break_even"] is None
        and protocol_document["official_execution_allowed"] is False
        and protocol_document["measured_scope_is_retroactive_v180r12r2_aggregation_cost"] is False
        and protocol_document["v180r12r2_producer_or_verifier_execution_permitted"] is False
        and protocol_document["outcome_free"] is True
    ):
        _fail("V180r12r4 protocol or frozen capability binding changed")
    if EXPECTED_SOURCE_CLOSURE_ID != ZERO_ID and not (
        closure_frozen
        and closure["source_closure_id"] == EXPECTED_SOURCE_CLOSURE_ID
        and closure["source_closure_byte_count"] == EXPECTED_SOURCE_CLOSURE_BYTE_COUNT
        and closure["source_closure_sha256"] == EXPECTED_SOURCE_CLOSURE_SHA256
        and closure["source_fact_count"] == EXPECTED_SOURCE_CLOSURE_FILE_COUNT
    ):
        _fail("V180r12r4 authorization source closure identity changed")

    payload = {
        "schema": "acfqp.campaign_measurement_execution_authorization.v180r12r4",
        "identity_literals_frozen": EXPECTED_AUTHORIZATION_ID != ZERO_ID,
        "campaign_measurement_protocol_id": frozen_protocol.campaign_measurement_protocol_id,
        "campaign_measurement_execution_slot_id": (
            frozen_protocol.campaign_measurement_execution_slot_id
        ),
        "campaign_measurement_attempt_identity_contract": (
            attempt_identity_contract
        ),
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "execution_nonce": EXECUTION_NONCE,
        "predecessor_production_aggregation_bundle_id": (
            protocol.V180R12R2_PRODUCTION_AGGREGATION_BUNDLE_ID
        ),
        "predecessor_verification_id": protocol.V180R12R2_VERIFICATION_ID,
        "authorized_subject": (
            protocol.CAMPAIGN_SCOPE_KIND
        ),
        "campaign_scope_kind": protocol.CAMPAIGN_SCOPE_KIND,
        "work_scope_kind": protocol.WORK_SCOPE_KIND,
        "counter_registry_reference": protocol.COUNTER_REGISTRY_REFERENCE,
        "authorized_attempt_count": 1,
        "planned_authorized_attempt_count": 1,
        "execution_authorization_effective": False,
        "zero_sentinel_draft_is_executable_authorization": False,
        "execution_forbidden_until_all_protocol_authorization_source_closure_"
        "prelaunch_rule_and_evidence_identities_are_frozen": True,
        "old_v180r12r2_authorization_reused": False,
        "v180r12r2_producer_or_verifier_rerun_authorized": False,
        "cgroup_parent_fact": protocol_document["cgroup_parent_fact"],
        "runtime_capability_fact": protocol_document["runtime_capability_fact"],
        "service_context_capture_contract": service_context_capture,
        "cgroup_parent_and_runtime_facts_exact_join_same_source_bound_capture": (
            True
        ),
        "cgroup_parent_and_capability_facts_must_replay_exactly_before_attempt": True,
        "cgroup_parent_owner_uid_equals_runtime_uid": True,
        "cgroup_parent_owner_gid_equals_runtime_gid": True,
        "cgroup_parent_owner_write_and_execute_required": True,
        "source_closure_contract": protocol.source_closure_contract_v180r12r4(),
        "prelaunch_contract": prelaunch_contract,
        "failed_dispatch_repair_lineage": repair_lineage,
        "failed_external_replay_repair_lineage": failed_external_replay,
        "failed_scientific_birth_repair_lineage": failed_scientific_birth,
        "failed_ordinal8_repair_lineage": failed_ordinal8,
        "failed_ordinal9_repair_lineage": failed_ordinal9,
        "failed_ordinal10_repair_lineage": failed_ordinal10,
        "failed_ordinal11_repair_lineage": failed_ordinal11,
        "failed_v180r12r3_identity_rerun_forbidden": True,
        "failed_v180r12r3r1_identity_rerun_forbidden": True,
        "failed_v180r12r3r2_identity_rerun_forbidden": True,
        "failed_v180r12r4r2_ordinal8_identity_rerun_forbidden": True,
        "failed_v180r12r4r4_ordinal9_identity_rerun_forbidden": True,
        "failed_v180r12r4r5_ordinal10_identity_rerun_forbidden": True,
        "failed_v180r12r4r6_ordinal11_identity_rerun_forbidden": True,
        "fresh_v180r12r4_physical_paths_and_identities_required": True,
        "repair_scope": protocol.V180R12R4_REPAIR_SCOPE,
        "repair_changes_campaign_path_roles_event_schedule_evidence_"
        "cardinality_or_reducers": False,
        "source_bound_runner_execution_envelope_contract": (
            runner_execution_envelope
        ),
        "terminal_evidence_inventory_contract": evidence_inventory_contract,
        "campaign_subject_result_fields": protocol_document[
            "campaign_subject_result_fields"
        ],
        "campaign_subject_result_echoes_authorization_evidence_and_transport_"
        "provenance": True,
        "durable_artifact_contract": durable_artifact_contract,
        "success_durable_artifact_contract": success_artifact_contract,
        "source_closure_candidate": closure,
        "source_closure_facts_supplied": source_facts is not None,
        "source_closure_identity_frozen": closure_frozen,
        "source_closure_placeholder_only": not closure_frozen,
        "authorization_evidence_freeze_required_before_execution": True,
        "source_bound_prelaunch_required_before_real_outcome_execution": True,
        "authorization_self_source_bound_by_post_prereg_freeze": False,
        "resource_caps": _resource_caps(),
        "event_grammar": event_grammar,
        "semantic_hash_counter_scope_contract": semantic_hash_scope,
        "fallible_paired_operation_count": event_grammar[
            "fallible_paired_operation_count"
        ],
        "fallible_paired_operation_scope": event_grammar[
            "fallible_paired_operation_scope"
        ],
        "all_307_fallible_paired_operation_sites_require_durable_intent_ack_"
        "before_listed_operation": event_grammar[
            "all_307_fallible_paired_operation_sites_require_durable_intent_ack_"
            "before_listed_operation"
        ],
        "every_fallible_paired_operation_emits_exact_intent_then_outcome": (
            event_grammar[
                "every_fallible_paired_operation_emits_exact_intent_then_outcome"
            ]
        ),
        "process_birth_operations_emit_intent_outcome_then_reap": event_grammar[
            "process_birth_operations_emit_intent_outcome_then_reap"
        ],
        "mount_interval_operations_emit_open_then_close": event_grammar[
            "mount_interval_operations_emit_open_then_close"
        ],
        "mount_interval_operations_use_open_close_not_intent_outcome": (
            event_grammar[
                "mount_interval_operations_use_open_close_not_intent_outcome"
            ]
        ),
        "singleton_operation_count": event_grammar["singleton_operation_count"],
        "singleton_operations_are_post_effect_atomic_observations_without_"
        "intent_claim": event_grammar[
            "singleton_operations_are_post_effect_atomic_observations_without_"
            "intent_claim"
        ],
        "unqualified_every_operation_intent_outcome_claim": event_grammar[
            "unqualified_every_operation_intent_outcome_claim"
        ],
        "deterministic_local_parse_shape_and_subject_computation_emits_"
        "separate_ledger_event": False,
        "failure_between_registered_hooks_preserves_current_phase_typed_"
        "failure_and_exact_durable_prefix": True,
        "trusted_observer_owns_all_durable_event_files_and_acks": True,
        "supervisor_and_worker_submit_observations_only": True,
        "supervisor_forwards_worker_observations_to_observer": True,
        "measured_children_append_durable_event_files": False,
        "measurement_derivation_contract": (
            protocol.measurement_derivation_contract_v180r12r4()
        ),
        "successful_measurement_arithmetic": protocol_document[
            "successful_measurement_arithmetic"
        ],
        "actual_operation_manifest": protocol.operation_manifest_v180r12r4(),
        "campaign_paths": list(protocol.CAMPAIGN_PATHS),
        "campaign_path_count": protocol.CAMPAIGN_PATH_COUNT,
        "route_kind": None,
        "route_free_campaign_scope_required": True,
        "exactly_two_predecessor_inputs_authorized": True,
        "predecessor_terminal_and_verification_only": True,
        "predecessor_source_receipt_count_replayed": 5,
        "predecessor_route_component_chain_receipt_count_replayed": 12,
        "predecessor_terminal_receipt_count_replayed": 10,
        "predecessor_terminal_shared_resource_receipt_count_replayed": 90,
        "predecessor_terminal_shared_resource_receipt_set_count_replayed": 10,
        "v180r7r1_construction_axis_replayed_as_independent_predecessor_"
        "evidence": True,
        "v180r7r1_construction_axis_charged_as_successor_campaign_"
        "authoritative_receipt": False,
        "v180r7r1_construction_axis_identity_replay_check_overhead_is_successor_"
        "campaign_measurement": True,
        "retained_verification_replay_is_bound_evidence_not_third_worker_input": True,
        "trusted_launcher_precompiles_repo_and_runtime_sources_before_attempt": True,
        "measured_children_lazy_repo_imports_forbidden": True,
        "worker_forbidden_imports": protocol_document["worker_forbidden_imports"],
        "worker_import_contract": protocol.worker_import_contract_v180r12r4(),
        "attempt_record_relative_path": ATTEMPT_RELATIVE_PATH,
        "output_root_relative_path": OUTPUT_ROOT_RELATIVE_PATH,
        "terminal_relative_path": TERMINAL_RELATIVE_PATH,
        "failure_relative_path": FAILURE_RELATIVE_PATH,
        "verification_relative_path": VERIFICATION_RELATIVE_PATH,
        "verification_failure_relative_path": VERIFICATION_FAILURE_RELATIVE_PATH,
        "retained_verification_replay_relative_path": (
            RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH
        ),
        "runtime_cas_root_relative_path": RUNTIME_CAS_ROOT_RELATIVE_PATH,
        "events_directory_relative_path": EVENTS_RELATIVE_PATH,
        "subject_temp_relative_path": SUBJECT_TEMP_RELATIVE_PATH,
        "subject_result_relative_path": SUBJECT_RESULT_RELATIVE_PATH,
        "evidence_inventory_relative_path": EVIDENCE_INVENTORY_RELATIVE_PATH,
        "execution_closure_relative_path": EXECUTION_CLOSURE_RELATIVE_PATH,
        "os_receipt_relative_path": OS_RECEIPT_RELATIVE_PATH,
        "ledger_closure_relative_path": LEDGER_CLOSURE_RELATIVE_PATH,
        "all_output_progress_paths_absent_before_attempt_required": True,
        "attempt_record_o_excl_and_fsync_before_cgroup_creation_or_authorized_"
        "measured_subject_input_read": True,
        "attempt_record_excludes_cgroup_topology_receipt_id": True,
        "terminal_evidence_causal_join_rules": list(
            protocol.EVIDENCE_CAUSAL_JOIN_RULES
        ),
        "failure_observation_contract": failure_observation_contract,
        "failure_observations_in_success_evidence_inventory": False,
        "failure_artifact_observations_are_campaign_success_authority": False,
        "failure_cgroup_observation_is_campaign_success_receipt": False,
        "final_subject_references_campaign_attempt_record_not_semantic_receipts": True,
        "semantic_receipt_evidence_subject_is_campaign_attempt_record": True,
        "semantic_receipt_evidence_subject_is_future_final_subject": False,
        "semantic_receipt_count_bound_to_attempt_record": 297,
        "replay_subject_binds_attempt_final_subject_and_exact_297_semantic_"
        "receipts": True,
        "subject_write_io_receipt_source_evidence_type": (
            "CAMPAIGN_SUBJECT_RESULT"
        ),
        "subject_write_io_receipt_target_evidence_type": (
            "WORKER_PIDFD_BIRTH_RECEIPT"
        ),
        "subject_write_io_receipt_references_future_replay_subject": False,
        "replay_subject_first_consumer_event_kind": "SUBJECT_COMMIT",
        "subject_readback_io_receipt_source_evidence_type": (
            "CAMPAIGN_SUBJECT_RESULT"
        ),
        "subject_readback_io_receipt_target_evidence_type": (
            "SUPERVISOR_PIDFD_BIRTH_RECEIPT"
        ),
        "successful_event_evidence_id_issued_before_event_append_required": True,
        "successful_event_future_evidence_reference_forbidden": True,
        "preauthorization_predecessor_and_source_validation_reads_are_trusted_"
        "excluded_overhead": True,
        "preauthorization_validation_reads_are_campaign_actual_measurement": False,
        "supervisor_first_measured_source_reads_occur_after_attempt_open": True,
        "attempt_identity_input_fields": [
            "protocol_id",
            "authorization_id",
            "authorization_evidence_id",
            "campaign_measurement_execution_slot_id",
            "logical_occurrence_id",
            "execution_nonce",
        ],
        "attempt_id_derived_from_exact_six_authorities": True,
        "attempt_identity_includes_fresh_authorization_evidence_id": True,
        "attempt_identity_excludes_cgroup_runtime_and_transport_facts": True,
        "attempt_record_and_terminal_echo_authorization_evidence_id": True,
        "attempt_record_and_terminal_transport_provenance_fields": [
            "prelaunch_materialization_terminal_id",
            "prelaunch_launch_manifest_sha256",
            "prelaunch_launch_rule_id",
            "measurement_launch_attempt_id",
        ],
        "measurement_launch_receipt_excluded_from_terminal_fixed_point": True,
        "verification_launcher_joins_post_outcome_measurement_launch_receipt": True,
        "attempt_identity_is_concurrency_and_replay_lock": True,
        "success_failure_timeout_cap_violation_or_crash_consumes_attempt_identity": True,
        "same_attempt_identity_rerun_forbidden": True,
        "terminal_failure_and_runtime_cas_mutually_exclusive": True,
        "campaign_failure_forbidden_at_terminal_publication_attempt_entry": True,
        "terminal_publication_attempt_entry_precedes_open_parent_and_o_excl": True,
        "post_terminal_child_or_bootstrap_error_is_outer_launch_failure": True,
        "pending_terminal_requires_measurement_launch_receipt_for_acceptance": True,
        "failure_prefix_event_chain_must_be_retained": True,
        "failure_written_o_excl_fsync_once": True,
        "terminal_written_o_excl_fsync_once": True,
        "verification_written_o_excl_fsync_once": True,
        "verification_failure_written_o_excl_fsync_once": True,
        "retained_verification_replay_must_equal_verification_exact_bytes": True,
        "measurement_root_created_empty_under_bound_parent": True,
        "measurement_root_memory_max_bytes": MEMORY_MAX_BYTES,
        "measurement_root_pids_max": PIDS_MAX,
        "measurement_root_child_roles": ["SUPERVISOR", "WORKER"],
        "measurement_root_and_leaf_role_fact_count": 3,
        "measurement_root_and_leaf_dev_inode_receipts_required": True,
        "no_internal_process_rule_required": True,
        "supervisor_birth_phase": "STAGE",
        "worker_birth_phase": "WORKER",
        "worker_reap_phase": "WORKER",
        "supervisor_reap_phase": "OS_OBSERVE",
        "process_birth_reap_chain_count": 2,
        "successful_semantic_hash_pair_count": (
            protocol.SEMANTIC_HASH_OPERATION_COUNT
        ),
        "successful_integrity_check_pair_count": (
            protocol.INTEGRITY_CHECK_OPERATION_COUNT
        ),
        "successful_protocol_check_pair_count": (
            protocol.PROTOCOL_CHECK_OPERATION_COUNT
        ),
        "successful_exact_event_count": protocol.SUCCESS_EXACT_EVENT_COUNT,
        "successful_extra_events_forbidden": True,
        "source_input_read_chain_count": 2,
        "staged_worker_input_read_chain_count": 2,
        "subject_readback_chain_count": 1,
        "total_input_read_chain_count": 5,
        "stage_write_mount_chain_count": 2,
        "mount_close_count": 2,
        "subject_result_preopened_o_excl_by_supervisor": True,
        "subject_write_phase": "WORKER",
        "subject_write_actor_role": "WORKER",
        "subject_commit_phase": "COMMIT",
        "subject_commit_actor_role": "SUPERVISOR",
        "subject_commit_requires_supervisor_readback_fsync_chmod_and_dir_fsync": True,
        "subject_result_is_separate_from_ledger_and_outer_terminal": True,
        "journal_ipc_ledger_hashing_storage_is_instrumentation_overhead": True,
        "instrumentation_overhead_is_campaign_actual_measurement": False,
        "instrumentation_memory_inside_children_remains_in_cgroup_peak": True,
        "root_and_both_leaf_populated_zero_before_cgroup_observed": True,
        "campaign_counter_record_count_before_execution": 0,
        "campaign_work_vector_count_before_execution": 0,
        "campaign_comparison_vector_count_before_execution": 0,
        "campaign_projection_proof_count_before_execution": 0,
        "campaign_native_zero_attestation_count_before_execution": 0,
        "successful_campaign_counter_record_count": 9,
        "successful_campaign_work_vector_count": 1,
        "successful_campaign_comparison_vector_count": 1,
        "successful_campaign_projection_proof_count": 1,
        "successful_campaign_native_zero_attestation_count": 1,
        "predecessor_occurrence_authoritative_receipt_count": 90,
        "predecessor_campaign_authoritative_receipt_count": 0,
        "predecessor_campaign_scope_structural_obligation_count": 9,
        "successful_campaign_authoritative_receipt_count": 9,
        "successful_combined_authoritative_receipt_count": 99,
        "terminal_pending_authoritative_receipt_join": protocol_document[
            "terminal_pending_authoritative_receipt_join"
        ],
        "independent_verifier_pass_authoritative_receipt_join": protocol_document[
            "independent_verifier_pass_authoritative_receipt_join"
        ],
        "predecessor_structural_nine_are_successor_actual_receipts": False,
        "successful_campaign_path_values_strictly_positive": True,
        "successful_zero_valued_campaign_path_receipt_count": 0,
        "successful_campaign_path_native_zero_observed_count": 0,
        "native_zero_observed_false_for_all_nine_campaign_paths": True,
        "native_zero_required_for_each_zero_valued_path": False,
        "zero_valued_campaign_path_receipts_if_present_are_observations": True,
        "zero_valued_campaign_path_receipts_permitted_on_success": False,
        "zero_valued_campaign_path_receipts_are_kernel_axis_zero_authority": False,
        "independent_native_zero_authority_required": True,
        "native_zero_comparison_axis": protocol.NATIVE_ZERO_COMPARISON_AXIS,
        "native_zero_comparison_axis_value": 0,
        "kernel_transition_calls_is_linux_syscall_count": False,
        "kernel_transition_calls_semantics": (
            "REGISTERED_PLANNING_GROUND_KERNEL_TRANSITION_OPERATION_SITES"
        ),
        "native_zero_registered_planning_operation_site_fact_count": 314,
        "native_zero_runtime_role_exit_origin_guard_status_at_terminal": (
            "PENDING_INDEPENDENT_MEASUREMENT_LAUNCH_RECEIPT"
        ),
        "native_zero_bound_campaign_operation_schedule_count": 314,
        "native_zero_bound_semantic_operation_receipt_count": 297,
        "native_zero_is_open_world_no_kernel_call_claim": False,
        "unregistered_or_dynamic_ground_kernel_operation_sites_forbidden": True,
        "post_attempt_unregistered_imports_or_code_loading_in_native_zero_"
        "authority_scope_forbidden": True,
        "native_zero_binds_closed_window_event": True,
        "native_zero_binds_exact_operation_manifest": True,
        "native_zero_binds_exact_source_and_import_manifest_facts": True,
        "native_zero_references_campaign_operation_manifest": True,
        "native_zero_references_native_zero_source_manifest": True,
        "native_zero_references_native_zero_import_inventory": True,
        "native_zero_references_window_closure_receipt": True,
        "native_zero_references_campaign_execution_closure": True,
        "projection_proof_references_native_zero_attestation": True,
        "campaign_measurement_execution_started": False,
        "campaign_measurement_execution_count": 0,
        "campaign_measurement_authorization_issued": False,
        "V180R12R2_COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "terminal_counter_closure_status_on_success": "PENDING_INDEPENDENT_REPLAY",
        "terminal_counter_completeness_gate_on_success": "PENDING_INDEPENDENT_REPLAY",
        "independent_verifier_is_only_counter_pass_authority": True,
        "independent_verifier_counter_completeness_gate_on_success": "PASS",
        "independent_verifier_campaign_counter_closure_status_on_success": "PASS",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "measured_scope_is_fresh_replay_successor_overhead": True,
        "measured_scope_is_retroactive_v180r12r2_aggregation_cost": False,
        "future_v180r13_must_carry_fresh_replay_successor_scope": True,
        "outcome_free": True,
    }
    return {
        **payload,
        "execution_authorization_id": domains.extension_content_id_v180r12r4(
            domains.CONSTRUCTION_K7_EXECUTION_AUTHORIZATION_V180R12R4_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CampaignMeasurementExecutionAuthorizationV180R12R4:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    execution_authorization_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        if not (
            self._issuer is _ISSUER
            and type(document) is dict
            and canonical_json_bytes(document) == self.canonical_bytes
            and document.get("execution_authorization_id")
            == self.execution_authorization_id
        ):
            _fail("V180r12r4 execution authorization is foreign or noncanonical")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document

    def __reduce__(self) -> NoReturn:
        raise TypeError("V180r12r4 execution authorization is not picklable")


def freeze_campaign_measurement_execution_authorization_v180r12r4(
    *,
    cgroup_parent_fact: Mapping[str, Any],
    runtime_capability_fact: Mapping[str, Any],
    source_facts: Sequence[Mapping[str, Any]] | None = None,
) -> CampaignMeasurementExecutionAuthorizationV180R12R4:
    document = build_campaign_measurement_execution_authorization_v180r12r4(
        cgroup_parent_fact=cgroup_parent_fact,
        runtime_capability_fact=runtime_capability_fact,
        source_facts=source_facts,
    )
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != ZERO_ID and not (
        document["execution_authorization_id"] == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V180r12r4 frozen execution authorization identity changed")
    return CampaignMeasurementExecutionAuthorizationV180R12R4(
        _ISSUER,
        raw,
        document["execution_authorization_id"],
    )


__all__ = (
    "ADDRESS_SPACE_HARD_CAP_BYTES",
    "ATTEMPT_RELATIVE_PATH",
    "AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS",
    "CampaignMeasurementExecutionAuthorizationV180R12R4",
    "CampaignMeasurementExecutionAuthorizationV180R12R4Error",
    "CAMPAIGN_CLEANUP_GRACE_SECONDS",
    "EXECUTION_NONCE",
    "EVENTS_RELATIVE_PATH",
    "EVIDENCE_INVENTORY_RELATIVE_PATH",
    "EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP",
    "EXECUTION_CLOSURE_RELATIVE_PATH",
    "EXECUTION_CLOSURE_BYTE_CAP",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_PROTOCOL_ID",
    "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT",
    "EXPECTED_SOURCE_CLOSURE_FILE_COUNT",
    "EXPECTED_SOURCE_CLOSURE_ID",
    "EXPECTED_SOURCE_CLOSURE_SHA256",
    "FAILURE_ARTIFACT_HASH_BYTE_CAP",
    "FAILURE_ARTIFACT_METADATA_BYTE_CAP",
    "FAILURE_ARTIFACT_OBSERVATION_ROW_CAP",
    "FAILURE_CGROUP_OBSERVATION_FIELDS",
    "FAILURE_CGROUP_NODE_OBSERVATION_FIELDS",
    "FAILURE_CGROUP_NODE_ROLES",
    "FAILURE_CGROUP_NODE_STATES",
    "FAILURE_DIRECTORY_ENTRY_CAP",
    "FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP",
    "FAILURE_EMERGENCY_RESERVE_BYTES",
    "FAILURE_MESSAGE_BYTE_CAP",
    "FRAME_BYTE_CAP",
    "SOCK_SEQPACKET_BUFFER_REQUEST_BYTES",
    "SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES",
    "FAILURE_RELATIVE_PATH",
    "LOGICAL_OCCURRENCE_ID",
    "LEDGER_CLOSURE_RELATIVE_PATH",
    "LEDGER_CLOSURE_BYTE_CAP",
    "MAX_EVENT_BYTE_COUNT",
    "MAX_EVENT_COUNT",
    "MAX_LEDGER_BYTE_COUNT",
    "MEMORY_MAX_BYTES",
    "OUTPUT_ROOT_RELATIVE_PATH",
    "OS_RECEIPT_RELATIVE_PATH",
    "OS_RECEIPT_BUNDLE_BYTE_CAP",
    "PIDS_MAX",
    "RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH",
    "RUNTIME_CAS_ROOT_RELATIVE_PATH",
    "SOURCE_CATALOG_MODULE_CAP",
    "SOURCE_CATALOG_TOTAL_BYTE_CAP",
    "SOURCE_CLOSURE_REQUIRED_ROOTS",
    "SUBJECT_RESULT_RELATIVE_PATH",
    "SUBJECT_RESULT_BYTE_CAP",
    "SUBJECT_RESULT_RUNTIME_BYTE_CAP",
    "SUBJECT_TEMP_RELATIVE_PATH",
    "SUCCESS_ARTIFACT_ORDER",
    "SUCCESS_ARTIFACT_SCHEMA_ROWS",
    "SUCCESS_DURABLE_ARTIFACT_ROWS",
    "SUCCESS_DURABLE_WRITE_ORDER",
    "TERMINAL_RELATIVE_PATH",
    "TERMINATION_GRACE_SECONDS",
    "VERIFICATION_FAILURE_RELATIVE_PATH",
    "VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS",
    "VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP",
    "VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP",
    "VERIFICATION_FAILURE_FIELDS",
    "VERIFICATION_FAILURE_OBSERVATION_BOUNDARY",
    "VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES",
    "VERIFICATION_FAILURE_SCHEMA",
    "VERIFICATION_RELATIVE_PATH",
    "WALL_TIMEOUT_SECONDS",
    "build_campaign_measurement_execution_authorization_v180r12r4",
    "freeze_campaign_measurement_execution_authorization_v180r12r4",
    "normalize_authorization_evidence_wrapper_source_v180r12r4",
    "replay_authorization_source_facts_v180r12r4",
    "source_closure_candidate_v180r12r4",
)
