"""Outcome-free authorization for one fresh V180r12r2 aggregation."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import io
from pathlib import Path
import tokenize
from typing import Any, NoReturn

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_domain_registry_extension_v180r12r2 as domains
from acfqp import (
    construction_k7_ten_terminal_aggregation_protocol_v180r12r2 as protocol,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AUTHORIZATION_ID = "4a1424a1d27e97139acd10a50cac79ab012b8459be79b884d9adc3fd4b39e3a9"
EXPECTED_CANONICAL_BYTE_COUNT = 64944
EXPECTED_CANONICAL_SHA256 = "f751b8c55985ce056010c7583902a24df244cbcd1473e61419f6435d48b745b2"
EXPECTED_PROTOCOL_ID = "d15ec6d29ffbb4908e20cabfbbc98f3aa53ec4ad38d1d4681930c3306737c965"
EXPECTED_AGGREGATION_EXECUTION_SLOT_ID = "98d5ba0a9b04cd444a2d5c159cd719f8e7803934f7cbb8ee9b0ce8947a41e46e"

LOGICAL_OCCURRENCE_ID = protocol.LOGICAL_OCCURRENCE_ID
EXECUTION_NONCE = protocol.EXECUTION_NONCE
WORKER_PROCESS_COUNT = 1
TIMEOUT_SECONDS = 14_400
ADDRESS_SPACE_HARD_CAP_BYTES = protocol.ADDRESS_SPACE_HARD_CAP_BYTES
OUTPUT_TOTAL_BYTE_CAP = 1024 * 1024 * 1024
FAILURE_EMERGENCY_RESERVE_BYTES = protocol.FAILURE_EMERGENCY_RESERVE_BYTES
FAILURE_MESSAGE_BYTE_CAP = protocol.FAILURE_MESSAGE_BYTE_CAP
FAILURE_TYPE_BYTE_CAP = protocol.FAILURE_TYPE_BYTE_CAP
FAILURE_OBSERVATION_STREAM_BUFFER_BYTES = (
    protocol.FAILURE_OBSERVATION_STREAM_BUFFER_BYTES
)
VERIFICATION_TERMINAL_INPUT_BYTE_CAP = (
    protocol.VERIFICATION_TERMINAL_INPUT_BYTE_CAP
)
SOURCE_CATALOG_MODULE_CAP = 4_096
SOURCE_CATALOG_TOTAL_BYTE_CAP = 128 * 1024 * 1024
MAXIMUM_FIXED_POINT_ITERATIONS = 32
AUTHORIZATION_EVIDENCE_SOURCE_BOUNDARY_GIT_PROCESS_COUNT = 6

RUNTIME_CAS_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation_cas"
)
OUTPUT_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation"
)
TERMINAL_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/TERMINAL.json"
FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation_failure.json"
)
VERIFICATION_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation_verification.json"
)
VERIFICATION_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r2_ten_terminal_aggregation_verification_failure.json"
)
RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r2_ten_terminal_aggregation_verification_replay.json"
)

_ROOT = Path(__file__).resolve().parents[2]
_AUTHORIZATION_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2.py"
)
_AUTHORIZATION_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_ten_terminal_aggregation_execution_"
    "authorization_evidence_freeze_v180r12r2.py"
)
_SOURCE_FACT_EXCLUSIONS = (_AUTHORIZATION_RELATIVE_PATH,)
AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS = (
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
)
_AUTHORIZATION_EVIDENCE_STRING_CONSTANTS = frozenset(
    {
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
        "EXPECTED_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_ID",
        "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
    }
)
_AUTHORIZATION_EVIDENCE_INTEGER_CONSTANTS = frozenset(
    {
        "EXPECTED_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    }
)
_POST_PREREG_REDACTED_STRING_LITERAL = (
    b'"__ACFQP_V180R12R2_POST_PREREG_REDACTED__"'
)
_POST_PREREG_REDACTED_INTEGER_LITERAL = b"0"
_PRODUCTION_SOURCE_ROOTS = (
    "scripts/run_v180r12r2_ten_terminal_aggregation.py",
    (
        "src/acfqp/construction_k7_ten_terminal_aggregation_"
        "finalizer_v180r12r2.py"
    ),
)
_VERIFICATION_SOURCE_ROOTS = (
    "scripts/verify_v180r12r2_ten_terminal_aggregation.py",
    (
        "src/acfqp/construction_k7_ten_terminal_aggregation_"
        "independent_verifier_v180r12r2.py"
    ),
)
_CONTRACT_SOURCE_ROOTS = (
    "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py",
    "scripts/launch_v180r12r2_ten_terminal_aggregation_prelaunch.py",
    "scripts/materialize_v180r12r2_ten_terminal_aggregation_prelaunch.py",
    "src/acfqp/abstraction/behavioral.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r2.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r2e.py",
    (
        "src/acfqp/construction_k7_ten_terminal_aggregation_"
        "stale_predecessor_freeze_v180r12r2.py"
    ),
    "src/acfqp/construction_k7_ten_terminal_aggregation_protocol_v180r12r2.py",
    _AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
    (
        "src/acfqp/construction_k7_ten_terminal_aggregation_"
        "campaign_accounting_v180r12r2.py"
    ),
    "src/acfqp/v075_production_semantic_authority_registry_v2.py",
)


class TenTerminalAggregationExecutionAuthorizationV180R12R2Error(ValueError):
    """The protocol, retained inputs, sources, or finite caps changed."""


def _fail(message: str) -> NoReturn:
    raise TenTerminalAggregationExecutionAuthorizationV180R12R2Error(message)


def _read_regular_symlink_free(path: Path) -> bytes:
    try:
        return source_runtime_v2._read_regular_symlink_free(path)  # noqa: SLF001
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise TenTerminalAggregationExecutionAuthorizationV180R12R2Error(
            "authorization-bound path is absent, linked, or nonregular"
        ) from error


def _module_level_literal_assignments(
    raw: bytes,
) -> dict[str, tuple[int, int, bytes]]:
    """Locate the exact byte spans authorized for post-prereg replacement."""

    try:
        tree = ast.parse(raw, filename=_AUTHORIZATION_EVIDENCE_RELATIVE_PATH)
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise TenTerminalAggregationExecutionAuthorizationV180R12R2Error(
            "authorization-evidence wrapper is not static UTF-8 Python"
        ) from error
    line_offsets = [0]
    for line in raw.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(line))
    assignments: dict[str, tuple[int, int, bytes]] = {}
    wanted = set(AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS)
    for statement in tree.body:
        name: str | None = None
        value: ast.expr | None = None
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        ):
            name = statement.targets[0].id
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target,
            ast.Name,
        ):
            name = statement.target.id
            value = statement.value
        if name not in wanted:
            continue
        if name in assignments or value is None:
            _fail("post-prereg redacted constant is duplicated or valueless")
        if not (
            type(value.lineno) is int
            and type(value.col_offset) is int
            and type(value.end_lineno) is int
            and type(value.end_col_offset) is int
            and 1 <= value.lineno <= value.end_lineno < len(line_offsets)
        ):
            _fail("post-prereg redacted constant has no exact source span")
        literal = value.value if isinstance(value, ast.Constant) else None
        if name in _AUTHORIZATION_EVIDENCE_STRING_CONSTANTS:
            if type(literal) is not str:
                _fail("post-prereg string anchor is not a literal")
            replacement = _POST_PREREG_REDACTED_STRING_LITERAL
        elif name in _AUTHORIZATION_EVIDENCE_INTEGER_CONSTANTS:
            if type(literal) is not int:
                _fail("post-prereg integer anchor is not a literal")
            replacement = _POST_PREREG_REDACTED_INTEGER_LITERAL
        else:  # pragma: no cover - the two frozen sets partition the allowlist
            raise AssertionError
        start = line_offsets[value.lineno - 1] + value.col_offset
        end = line_offsets[value.end_lineno - 1] + value.end_col_offset
        if not (0 <= start < end <= len(raw)):
            _fail("post-prereg redacted constant source span is invalid")
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
            raise TenTerminalAggregationExecutionAuthorizationV180R12R2Error(
                "post-prereg literal tokenization failed"
            ) from error
        expected_token = (
            tokenize.STRING
            if name in _AUTHORIZATION_EVIDENCE_STRING_CONSTANTS
            else tokenize.NUMBER
        )
        if len(tokens) != 1 or tokens[0].type != expected_token:
            _fail("post-prereg anchor must be exactly one lexical literal token")
        assignments[name] = (start, end, replacement)
    if set(assignments) != wanted:
        _fail("post-prereg redacted constant allowlist is incomplete")
    return assignments


def normalize_authorization_evidence_wrapper_source_v180r12r2(
    raw: bytes,
) -> bytes:
    """Redact only frozen post-prereg literal values, never wrapper logic."""

    if type(raw) is not bytes:
        raise TypeError("authorization-evidence wrapper source must be bytes")
    result = raw
    assignments = _module_level_literal_assignments(raw)
    spans = sorted(assignments.values(), key=lambda item: item[0], reverse=True)
    previous_start = len(raw)
    for start, end, replacement in spans:
        if end > previous_start:
            _fail("post-prereg redacted constant source spans overlap")
        result = result[:start] + replacement + result[end:]
        previous_start = start
    return result


def _module_name(relative_path: str) -> str:
    path = Path(relative_path)
    if not (
        relative_path.startswith("src/acfqp/")
        and relative_path.endswith(".py")
    ):
        _fail("authorization catalogue path is outside src/acfqp")
    parts = list(path.relative_to("src").with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    name = ".".join(parts)
    if not source_runtime_v2._valid_module_name(name):  # noqa: SLF001
        _fail("authorization catalogue module name is invalid")
    return name


def _module_catalogue() -> dict[str, tuple[str, Path, bool]]:
    rows: dict[str, tuple[str, Path, bool]] = {}
    for path in sorted((_ROOT / "src" / "acfqp").rglob("*.py")):
        relative_path = path.relative_to(_ROOT).as_posix()
        name = _module_name(relative_path)
        if name in rows:
            _fail("authorization module catalogue is duplicated")
        rows[name] = (relative_path, path, path.name == "__init__.py")
    if not (
        0 < len(rows) <= SOURCE_CATALOG_MODULE_CAP
        and tuple(rows) == tuple(sorted(rows))
    ):
        _fail("authorization module catalogue exceeds its finite cap")
    return rows


def _script_import_roots(
    relative_path: str,
    available_names: frozenset[str],
) -> tuple[str, ...]:
    raw = _read_regular_symlink_free(_ROOT / relative_path)
    try:
        tree = ast.parse(raw, filename=relative_path)
    except (SyntaxError, ValueError) as error:
        raise TenTerminalAggregationExecutionAuthorizationV180R12R2Error(
            "authorization script root is not static Python source"
        ) from error
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in available_names:
                    roots.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            module = node.module
            if type(module) is not str or not module.startswith("acfqp"):
                continue
            if module in available_names:
                roots.add(module)
            for alias in node.names:
                candidate = f"{module}.{alias.name}"
                if candidate in available_names:
                    roots.add(candidate)
    return tuple(sorted(roots))


def _static_source_closure_relative_paths() -> tuple[str, ...]:
    catalogue = _module_catalogue()
    available = frozenset(catalogue)
    all_roots = (
        *_PRODUCTION_SOURCE_ROOTS,
        *_VERIFICATION_SOURCE_ROOTS,
        *_CONTRACT_SOURCE_ROOTS,
    )
    script_roots = tuple(
        relative_path
        for relative_path in all_roots
        if relative_path.startswith("scripts/")
    )
    explicit_modules = {
        _module_name(relative_path)
        for relative_path in all_roots
        if relative_path.startswith("src/acfqp/")
    }
    for relative_path in script_roots:
        explicit_modules.update(_script_import_roots(relative_path, available))
    if not explicit_modules <= available:
        _fail("authorization static-import root is absent")

    pending = list(reversed(tuple(sorted(explicit_modules))))
    included: set[str] = set()
    while pending:
        name = pending.pop()
        if name in included:
            continue
        if len(included) >= SOURCE_CATALOG_MODULE_CAP:
            _fail("authorization static source closure exceeds its module cap")
        included.add(name)
        relative_path, path, is_package = catalogue[name]
        raw = _read_regular_symlink_free(path)
        try:
            imports = source_runtime_v2._local_imports_from_raw(  # noqa: SLF001
                module_name=name,
                is_package=is_package,
                raw=raw,
                available_names=available,
            )
        except (
            source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation
        ) as error:
            raise TenTerminalAggregationExecutionAuthorizationV180R12R2Error(
                f"authorization static-import traversal failed: {relative_path}"
            ) from error
        pending.extend(
            reversed(tuple(item for item in imports if item not in included))
        )
        components = name.split(".")
        for end in range(1, len(components)):
            parent = ".".join(components[:end])
            if parent not in catalogue:
                _fail("authorization static closure omitted a parent package")
            if parent not in included:
                pending.append(parent)

    paths = {
        catalogue[name][0]
        for name in included
        if catalogue[name][0] not in _SOURCE_FACT_EXCLUSIONS
    }
    paths.update(script_roots)
    result = tuple(sorted(paths))
    if (
        set(_SOURCE_FACT_EXCLUSIONS) & set(result)
        or not set(all_roots) <= set(result)
    ):
        _fail("authorization self-exclusion or static roots changed")
    return result


def _source_facts() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total_bytes = 0
    for relative_path in _static_source_closure_relative_paths():
        raw = _read_regular_symlink_free(_ROOT / relative_path)
        if relative_path == _AUTHORIZATION_EVIDENCE_RELATIVE_PATH:
            bound_raw = normalize_authorization_evidence_wrapper_source_v180r12r2(
                raw
            )
            row = {
                "relative_path": relative_path,
                "binding_kind": "POST_PREREG_LITERAL_REDACTED_SOURCE_V1",
                "byte_count": len(bound_raw),
                "sha256": hashlib.sha256(bound_raw).hexdigest(),
                "redacted_constant_names": list(
                    AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS
                ),
            }
        else:
            bound_raw = raw
            row = {
                "relative_path": relative_path,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        total_bytes += len(bound_raw)
        if total_bytes > SOURCE_CATALOG_TOTAL_BYTE_CAP:
            _fail("authorization source closure exceeds its byte cap")
        rows.append(row)
    if [row["relative_path"] for row in rows] != sorted(
        {row["relative_path"] for row in rows}
    ):
        _fail("authorization source facts are unsorted or duplicated")
    return rows


def replay_authorization_source_facts_v180r12r2(
    document: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    observed = _source_facts()
    if not (
        type(document) is dict
        and document.get("source_facts") == observed
        and document.get("source_fact_file_count") == len(observed)
        and document.get("source_fact_byte_count")
        == sum(row["byte_count"] for row in observed)
        and document.get("source_facts_sha256")
        == hashlib.sha256(canonical_json_bytes(observed)).hexdigest()
        and document.get("source_fact_exclusions")
        == list(_SOURCE_FACT_EXCLUSIONS)
    ):
        _fail("authorization-bound static source closure changed")
    return tuple(observed)


def _retained_source_input_facts() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in protocol.RETAINED_SOURCE_GROUP_SPECS:
        source_kind = spec[0]
        for role, relative_path, content_id, byte_count, sha256 in (
            ("TERMINAL", spec[3], spec[5], spec[6], spec[7]),
            ("INDEPENDENT_VERIFICATION", spec[8], spec[9], spec[10], spec[11]),
        ):
            raw = _read_regular_symlink_free(_ROOT / relative_path)
            document = loads_canonical_json(raw)
            if not (
                type(document) is dict
                and canonical_json_bytes(document) == raw
                and len(raw) == byte_count
                and hashlib.sha256(raw).hexdigest() == sha256
            ):
                _fail("authorization-bound retained source bytes changed")
            rows.append(
                {
                    "source_kind": source_kind,
                    "role": role,
                    "relative_path": relative_path,
                    "content_id": content_id,
                    "byte_count": byte_count,
                    "sha256": sha256,
                }
            )
    if not (
        len(rows) == 2 * protocol.SOURCE_GROUP_COUNT
        and sum(row["byte_count"] for row in rows)
        == protocol.RETAINED_SOURCE_TOTAL_BYTE_COUNT
    ):
        _fail("authorization-bound retained source denominator changed")
    return rows


def _resource_caps() -> dict[str, Any]:
    return {
        "applies_to": [
            "PRODUCTION_AGGREGATION",
            "PRODUCER_FREE_VERIFICATION_AND_RETAINED_REPLAY",
        ],
        "worker_process_count": WORKER_PROCESS_COUNT,
        "timeout_seconds": TIMEOUT_SECONDS,
        "wall_timeout_mechanism": "SIGALRM",
        "address_space_hard_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
        "address_space_cap_mechanism": "RLIMIT_AS",
        "glibc_malloc_trim_required_fail_closed": True,
        "glibc_malloc_trim_allowed_return_statuses": list(
            protocol.TRANSIENT_HEAP_RELEASE_ALLOWED_RETURN_STATUSES
        ),
        "linux_proc_self_statm_current_vms_proof_required_before_rlimit_as": (
            True
        ),
        "current_vms_must_not_exceed_address_space_cap_before_rlimit_as": True,
        "finalizer_transient_heap_release_phase_count": (
            protocol.FINALIZER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT
        ),
        "independent_verifier_transient_heap_release_phase_count_per_replay": (
            protocol.INDEPENDENT_VERIFIER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT_PER_REPLAY
        ),
        "producer_runner_precap_heap_release_phase_count": (
            protocol.PRODUCER_RUNNER_PRECAP_HEAP_RELEASE_PHASE_COUNT
        ),
        "producer_total_transient_heap_release_phase_count": (
            protocol.PRODUCER_TOTAL_TRANSIENT_HEAP_RELEASE_PHASE_COUNT
        ),
        "verification_runner_external_heap_release_phase_count": (
            protocol.VERIFICATION_RUNNER_EXTERNAL_HEAP_RELEASE_PHASE_COUNT
        ),
        "verification_replay_count": protocol.VERIFICATION_REPLAY_COUNT,
        "verification_total_transient_heap_release_phase_count": (
            protocol.VERIFICATION_TOTAL_TRANSIENT_HEAP_RELEASE_PHASE_COUNT
        ),
        "transient_heap_release_authority_class": (
            protocol.TRANSIENT_HEAP_RELEASE_AUTHORITY_CLASS
        ),
        "transient_heap_release_is_preauthorization_resource_schedule": True,
        "transient_heap_release_is_campaign_actual_measurement": False,
        "failure_emergency_reserve_bytes": protocol.FAILURE_EMERGENCY_RESERVE_BYTES,
        "failure_emergency_reserve_allocated_before_rlimit_as": True,
        "failure_emergency_reserve_counted_inside_address_space_cap": True,
        "failure_message_byte_cap": protocol.FAILURE_MESSAGE_BYTE_CAP,
        "failure_type_byte_cap": protocol.FAILURE_TYPE_BYTE_CAP,
        "failure_message_utf8_formatting_fail_safe": True,
        "failure_traceback_detach_and_child_frame_clear_required": True,
        "alarm_teardown_inside_protected_terminal_boundary": True,
        "alarm_cancel_or_ignore_before_primary_failure_formatting": True,
        "alarm_neutralization_precedes_failure_reserve_release": True,
        "alarm_previous_handler_restore_after_failure_reserve_release": True,
        "failure_reserve_release_precedes_failure_formatting": True,
        "alarm_teardown_failure_typed_observation_required": True,
        "failure_path_heap_release_best_effort": True,
        "failure_path_heap_release_is_not_fail_closed_phase": True,
        "failure_path_heap_release_is_campaign_actual_measurement": False,
        "failure_progress_observation_streaming_sha256_required": True,
        "failure_observation_stream_buffer_bytes": (
            protocol.FAILURE_OBSERVATION_STREAM_BUFFER_BYTES
        ),
        "producer_progress_path_count": protocol.PRODUCER_PROGRESS_PATH_COUNT,
        "producer_all_progress_paths_absent_before_execution_required": True,
        "verification_runtime_cas_absent_before_execution_required": True,
        "verification_terminal_input_byte_cap": (
            protocol.VERIFICATION_TERMINAL_INPUT_BYTE_CAP
        ),
        "verification_terminal_input_cap_checked_before_and_during_read": True,
        "output_total_byte_cap": OUTPUT_TOTAL_BYTE_CAP,
        "source_catalog_module_cap": SOURCE_CATALOG_MODULE_CAP,
        "source_catalog_total_byte_cap": SOURCE_CATALOG_TOTAL_BYTE_CAP,
        "maximum_fixed_point_iterations": MAXIMUM_FIXED_POINT_ITERATIONS,
        "retained_source_group_count": protocol.SOURCE_GROUP_COUNT,
        "retained_source_file_count": 2 * protocol.SOURCE_GROUP_COUNT,
        "retained_source_total_byte_count": (
            protocol.RETAINED_SOURCE_TOTAL_BYTE_COUNT
        ),
    }


def build_ten_terminal_aggregation_execution_authorization_v180r12r2() -> (
    dict[str, Any]
):
    frozen_protocol = protocol.freeze_ten_terminal_aggregation_protocol_v180r12r2()
    protocol_document = frozen_protocol.to_document()
    prelaunch_contract = protocol.prelaunch_contract_v180r12r2()
    slot = protocol_document["aggregation_execution_slot"]
    if not (
        (EXPECTED_PROTOCOL_ID == "0" * 64 or frozen_protocol.aggregation_protocol_id == EXPECTED_PROTOCOL_ID)
        and (
            EXPECTED_AGGREGATION_EXECUTION_SLOT_ID == "0" * 64
            or frozen_protocol.aggregation_execution_slot_id
            == EXPECTED_AGGREGATION_EXECUTION_SLOT_ID
        )
        and slot["logical_occurrence_id"] == LOGICAL_OCCURRENCE_ID
        and slot["execution_nonce"] == EXECUTION_NONCE
        and slot["predecessor_v180r12r1_authorization_id"]
        == (
            "cf1158297e790cfd5a794adbd2abc98819ff0f7ce736a4859a9795938ef1672f"
        )
        and protocol_document["v180r12r1_status"] == "STALE_UNEXECUTED"
        and protocol_document[
            "v180r12r1_same_authorization_execution_forbidden"
        ]
        is True
        and protocol_document["terminal_shared_resource_receipt_count"] == 90
        and protocol_document["campaign_scope_structural_obligation_count"]
        == 9
        and protocol_document["campaign_scope_actual_counter_record_count"] == 0
        and protocol_document[
            "campaign_scope_actual_shared_resource_receipt_count"
        ]
        == 0
        and protocol_document["campaign_scope_actual_work_vector_count"] == 0
        and protocol_document["campaign_scope_actual_comparison_vector_count"]
        == 0
        and protocol_document["campaign_scope_actual_projection_proof_count"]
        == 0
        and protocol_document[
            "campaign_scope_actual_native_zero_attestation_count"
        ]
        == 0
        and protocol_document["total_authoritative_shared_resource_receipt_count"]
        == 90
        and protocol_document["COUNTER_COMPLETENESS_BLOCKER"]
        == protocol.COUNTER_COMPLETENESS_BLOCKER
        and protocol_document["fresh_v180r12r3_actual_measurement_ledger_required"]
        is True
        and protocol_document[
            "authorization_evidence_source_boundary_commit_required"
        ]
        is True
        and protocol_document["prelaunch_contract"] == prelaunch_contract
        and prelaunch_contract["source_closure_rule_id"]
        == protocol.PRELAUNCH_SOURCE_CLOSURE_RULE_ID
        and prelaunch_contract["materialization_rule_id"]
        == protocol.PRELAUNCH_MATERIALIZATION_RULE_ID
        and prelaunch_contract["launch_rule_id"]
        == protocol.PRELAUNCH_LAUNCH_RULE_ID
        and prelaunch_contract["actual_manifest_digest_preregistered"] is False
        and prelaunch_contract[
            "authorization_evidence_verification_first_action_scope"
        ]
        == (
            "FIRST_ACTION_INSIDE_RUNNER_MAIN_AFTER_PRELAUNCH_DISPATCH_"
            "BEFORE_ANY_SCIENTIFIC_OUTPUT_INSPECTION_OR_CREATION"
        )
        and protocol_document["source_boundary_empty_bridge_commit_required"]
        is True
        and protocol_document[
            "source_boundary_empty_bridge_must_preserve_entire_tree"
        ]
        is True
        and protocol_document[
            "source_boundary_bridge_then_wrapper_eight_literal_commit_sequence_required"
        ]
        is True
        and protocol_document[
            "source_boundary_candidate_build_may_relax_only_literal_commit_presence"
        ]
        is True
        and protocol_document[
            "source_boundary_runtime_freeze_requires_committed_wrapper_literals"
        ]
        is True
        and protocol_document[
            "source_boundary_candidate_and_runtime_payload_identity_must_match"
        ]
        is True
        and protocol_document[
            "source_boundary_post_literal_bound_history_touch_forbidden"
        ]
        is True
        and protocol_document["address_space_hard_cap_bytes"]
        == ADDRESS_SPACE_HARD_CAP_BYTES
        and protocol_document["rejected_preprereg_address_space_cap_bytes"]
        == 6 * 1024 * 1024 * 1024
        and protocol_document["rejected_preprereg_max_rss_kib"] == 6_216_640
        and protocol_document["rejected_preprereg_elapsed_seconds"]
        == "1908.72"
        and protocol_document["rejected_preprereg_failure_stage"]
        == "V180R10R1_TO_V36_TO_V35_PLANNER_FROZENSET_CACHE"
        and protocol_document["rejected_preprereg_failure_type"]
        == "MemoryError"
        and protocol_document["rejected_preprereg_kind"]
        == "PRE_PREREG_NONFROZEN_DEVELOPMENT_RESOURCE_PREFLIGHT"
        and protocol_document["rejected_preprereg_test"]
        == (
            "test_v180r12r2_loads_compact_real_groups_under_explicit_6gib_"
            "rlimit"
        )
        and protocol_document[
            "rejected_preprereg_dummy_aggregation_protocol_id"
        ]
        == "a" * 64
        and protocol_document[
            "rejected_preprereg_dummy_execution_authorization_id"
        ]
        == "b" * 64
        and protocol_document["rejected_preprereg_scientific_output_created"]
        is False
        and protocol_document["rejected_preprereg_production_artifact_written"]
        is False
        and protocol_document["rejected_preprereg_failure_artifact_written"]
        is False
        and protocol_document["rejected_preprereg_runtime_cas_created"] is False
        and protocol_document[
            "rejected_preprereg_authorized_production_aggregation_execution_"
            "attempted"
        ]
        is False
        and protocol_document[
            "rejected_preprereg_development_resource_preflight_computation_"
            "attempted"
        ]
        is True
        and protocol_document[
            "rejected_preprereg_development_resource_preflight_completed"
        ]
        is False
        and protocol_document["rejected_preprereg_scientific_authority"]
        is False
        and protocol_document["rejected_preprereg_official_authority"] is False
        and protocol_document["rejected_preprereg_cap_was_frozen_authorization"]
        is False
        and protocol_document[
            "address_space_cap_selected_before_v180r12r2_authorization"
        ]
        is True
        and protocol_document["glibc_malloc_trim_required_fail_closed"] is True
        and protocol_document["glibc_malloc_trim_allowed_return_statuses"]
        == [0, 1]
        and protocol_document[
            "linux_proc_self_statm_current_vms_proof_required_before_rlimit_as"
        ]
        is True
        and protocol_document[
            "current_vms_must_not_exceed_address_space_cap_before_rlimit_as"
        ]
        is True
        and protocol_document["finalizer_transient_heap_release_phase_count"]
        == 7
        and protocol_document[
            "independent_verifier_transient_heap_release_phase_count_per_replay"
        ]
        == 10
        and protocol_document[
            "producer_runner_precap_heap_release_phase_count"
        ]
        == 1
        and protocol_document["producer_total_transient_heap_release_phase_count"]
        == 8
        and protocol_document[
            "verification_runner_external_heap_release_phase_count"
        ]
        == 2
        and protocol_document["verification_replay_count"] == 2
        and protocol_document[
            "verification_total_transient_heap_release_phase_count"
        ]
        == 22
        and protocol_document["transient_heap_release_authority_class"]
        == "PREAUTHORIZATION_MEMORY_LIFECYCLE_STRUCTURAL_OBLIGATION"
        and protocol_document[
            "transient_heap_release_is_preauthorization_resource_schedule"
        ]
        is True
        and protocol_document[
            "transient_heap_release_is_campaign_actual_measurement"
        ]
        is False
        and protocol_document["failure_emergency_reserve_bytes"]
        == protocol.FAILURE_EMERGENCY_RESERVE_BYTES
        and protocol_document[
            "failure_emergency_reserve_allocated_before_rlimit_as"
        ]
        is True
        and protocol_document[
            "failure_emergency_reserve_counted_inside_address_space_cap"
        ]
        is True
        and protocol_document["failure_message_byte_cap"]
        == protocol.FAILURE_MESSAGE_BYTE_CAP
        and protocol_document["failure_type_byte_cap"]
        == protocol.FAILURE_TYPE_BYTE_CAP
        and protocol_document["failure_message_utf8_formatting_fail_safe"]
        is True
        and protocol_document[
            "failure_traceback_detach_and_child_frame_clear_required"
        ]
        is True
        and protocol_document[
            "alarm_teardown_inside_protected_terminal_boundary"
        ]
        is True
        and protocol_document[
            "alarm_cancel_or_ignore_before_primary_failure_formatting"
        ]
        is True
        and protocol_document[
            "alarm_neutralization_precedes_failure_reserve_release"
        ]
        is True
        and protocol_document[
            "alarm_previous_handler_restore_after_failure_reserve_release"
        ]
        is True
        and protocol_document[
            "failure_reserve_release_precedes_failure_formatting"
        ]
        is True
        and protocol_document[
            "alarm_teardown_failure_typed_observation_required"
        ]
        is True
        and protocol_document["failure_path_heap_release_best_effort"] is True
        and protocol_document[
            "failure_path_heap_release_is_not_fail_closed_phase"
        ]
        is True
        and protocol_document[
            "failure_path_heap_release_is_campaign_actual_measurement"
        ]
        is False
        and protocol_document[
            "failure_progress_observation_streaming_sha256_required"
        ]
        is True
        and protocol_document["failure_observation_stream_buffer_bytes"]
        == protocol.FAILURE_OBSERVATION_STREAM_BUFFER_BYTES
        and protocol_document["producer_progress_path_count"]
        == protocol.PRODUCER_PROGRESS_PATH_COUNT
        and protocol_document[
            "producer_all_progress_paths_absent_before_execution_required"
        ]
        is True
        and protocol_document[
            "verification_runtime_cas_absent_before_execution_required"
        ]
        is True
        and protocol_document["verification_terminal_input_byte_cap"]
        == protocol.VERIFICATION_TERMINAL_INPUT_BYTE_CAP
        and protocol_document[
            "verification_terminal_input_cap_checked_before_and_during_read"
        ]
        is True
        and protocol_document["v180r12r2_outcome_bytes_accessed"] is False
    ):
        _fail("fresh aggregation protocol or slot changed")

    source_facts = _source_facts()
    retained_source_facts = _retained_source_input_facts()
    payload = {
        "schema": "acfqp.ten_terminal_aggregation_execution_authorization.v180r12r2",
        "aggregation_protocol_id": frozen_protocol.aggregation_protocol_id,
        "aggregation_execution_slot": slot,
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "execution_nonce": EXECUTION_NONCE,
        "preserved_stale_v180r12r1_authorization_id": (
            "cf1158297e790cfd5a794adbd2abc98819ff0f7ce736a4859a9795938ef1672f"
        ),
        "stale_v180r12r1_authorization_reused": False,
        "same_stale_authorization_execution_forbidden": True,
        "same_authorization_rerun_after_progress_or_terminal_forbidden": True,
        "retained_source_input_facts": retained_source_facts,
        "retained_source_input_fact_count": len(retained_source_facts),
        "retained_source_input_total_byte_count": sum(
            row["byte_count"] for row in retained_source_facts
        ),
        "retained_source_input_facts_sha256": hashlib.sha256(
            canonical_json_bytes(retained_source_facts)
        ).hexdigest(),
        "source_facts": source_facts,
        "source_fact_file_count": len(source_facts),
        "source_fact_byte_count": sum(row["byte_count"] for row in source_facts),
        "source_facts_sha256": hashlib.sha256(
            canonical_json_bytes(source_facts)
        ).hexdigest(),
        "source_fact_closure_rule": (
            "RECURSIVE_STATIC_LOCAL_ACFQP_IMPORTS_FROM_PRODUCTION_"
            "VERIFICATION_AND_CONTRACT_ROOTS"
        ),
        "production_source_fact_static_import_roots": list(
            _PRODUCTION_SOURCE_ROOTS
        ),
        "verification_source_fact_static_import_roots": list(
            _VERIFICATION_SOURCE_ROOTS
        ),
        "contract_source_fact_static_import_roots": list(_CONTRACT_SOURCE_ROOTS),
        "source_fact_exclusions": list(_SOURCE_FACT_EXCLUSIONS),
        "authorization_self_source_bound_by_post_prereg_freeze": False,
        "authorization_evidence_wrapper_source_bound_in_authorization_closure": (
            True
        ),
        "authorization_evidence_wrapper_binding_kind": (
            "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"
        ),
        "authorization_evidence_wrapper_redacted_constant_names": list(
            AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS
        ),
        "authorization_evidence_wrapper_self_source_excluded": False,
        "self_identity_cycle_avoided": True,
        "identity_cycle_avoidance_rule": (
            "AUTHORIZATION_BINDS_WRAPPER_AFTER_CANONICAL_REDACTION_OF_ONLY_"
            "THE_ALLOWLISTED_POST_PREREG_LITERAL_VALUES_WRAPPER_LITERALS_"
            "THEN_LOCK_AUTHORIZATION_AND_EVIDENCE_IDENTITIES"
        ),
        "post_prereg_authorization_evidence_freeze_required": True,
        "authorization_evidence_source_boundary_commit_required": True,
        "prelaunch_contract": prelaunch_contract,
        "authorization_evidence_empty_bridge_commit_required": True,
        "authorization_evidence_empty_bridge_must_preserve_entire_tree": True,
        "authorization_evidence_bridge_then_wrapper_eight_literal_commit_"
        "sequence_required": True,
        "authorization_evidence_candidate_build_may_relax_only_literal_commit_"
        "presence": True,
        "authorization_evidence_runtime_freeze_requires_committed_wrapper_"
        "literals": True,
        "authorization_evidence_candidate_and_runtime_payload_identity_must_"
        "match": True,
        "authorization_evidence_post_literal_bound_history_touch_forbidden": True,
        "authorization_evidence_source_boundary_git_process_count": (
            AUTHORIZATION_EVIDENCE_SOURCE_BOUNDARY_GIT_PROCESS_COUNT
        ),
        "authorization_evidence_source_boundary_git_processes_are_"
        "preauthorization_not_campaign_actual_measurements": True,
        "resource_caps": _resource_caps(),
        "entrypoint": (
            "acfqp.construction_k7_ten_terminal_aggregation_"
            "finalizer_v180r12r2:freeze_ten_terminal_aggregation_v180r12r2"
        ),
        "runner_relative_path": (
            "scripts/run_v180r12r2_ten_terminal_aggregation.py"
        ),
        "independent_verifier_entrypoint": (
            "acfqp.construction_k7_ten_terminal_aggregation_"
            "independent_verifier_v180r12r2:"
            "verify_ten_terminal_aggregation_independently_v180r12r2"
        ),
        "independent_verifier_runner_relative_path": (
            "scripts/verify_v180r12r2_ten_terminal_aggregation.py"
        ),
        "runtime_cas_root_relative_path": RUNTIME_CAS_ROOT_RELATIVE_PATH,
        "output_root_relative_path": OUTPUT_ROOT_RELATIVE_PATH,
        "terminal_relative_path": TERMINAL_RELATIVE_PATH,
        "failure_relative_path": FAILURE_RELATIVE_PATH,
        "verification_relative_path": VERIFICATION_RELATIVE_PATH,
        "verification_failure_relative_path": VERIFICATION_FAILURE_RELATIVE_PATH,
        "retained_verification_replay_relative_path": (
            RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH
        ),
        "one_worker_process_required": True,
        "one_isolated_worker_no_concurrent_campaign": True,
        "resource_caps_apply_to_producer_and_producer_free_verifier": True,
        "producer_runner_enforces_sigalrm_timeout": True,
        "producer_runner_enforces_rlimit_as": True,
        "producer_free_verifier_runner_enforces_sigalrm_timeout": True,
        "producer_free_verifier_runner_enforces_rlimit_as": True,
        "concurrent_workspace_mutation_during_one_shot_aggregation_out_of_scope": (
            True
        ),
        "timeout_seconds": TIMEOUT_SECONDS,
        "address_space_hard_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
        "rejected_preprereg_address_space_cap_bytes": (
            protocol.REJECTED_PREFLIGHT_ADDRESS_SPACE_CAP_BYTES
        ),
        "rejected_preprereg_max_rss_kib": (
            protocol.REJECTED_PREFLIGHT_MAX_RSS_KIB
        ),
        "rejected_preprereg_elapsed_seconds": (
            protocol.REJECTED_PREFLIGHT_ELAPSED_SECONDS
        ),
        "rejected_preprereg_failure_stage": (
            "V180R10R1_TO_V36_TO_V35_PLANNER_FROZENSET_CACHE"
        ),
        "rejected_preprereg_failure_type": "MemoryError",
        "rejected_preprereg_kind": (
            "PRE_PREREG_NONFROZEN_DEVELOPMENT_RESOURCE_PREFLIGHT"
        ),
        "rejected_preprereg_test": (
            "test_v180r12r2_loads_compact_real_groups_under_explicit_6gib_"
            "rlimit"
        ),
        "rejected_preprereg_dummy_aggregation_protocol_id": "a" * 64,
        "rejected_preprereg_dummy_execution_authorization_id": "b" * 64,
        "rejected_preprereg_scientific_output_created": False,
        "rejected_preprereg_production_artifact_written": False,
        "rejected_preprereg_failure_artifact_written": False,
        "rejected_preprereg_runtime_cas_created": False,
        "rejected_preprereg_authorized_production_aggregation_execution_"
        "attempted": False,
        "rejected_preprereg_development_resource_preflight_computation_"
        "attempted": True,
        "rejected_preprereg_development_resource_preflight_completed": False,
        "rejected_preprereg_scientific_authority": False,
        "rejected_preprereg_official_authority": False,
        "rejected_preprereg_cap_was_frozen_authorization": False,
        "address_space_cap_selected_before_v180r12r2_authorization": True,
        "runtime_cas_root_must_be_absent": True,
        "output_root_must_be_absent": True,
        "terminal_must_be_written_once": True,
        "failure_must_be_written_once": True,
        "verification_must_be_written_once": True,
        "verification_failure_must_be_written_once": True,
        "retained_verification_replay_must_equal_frozen_verification_bytes": True,
        "authorization_evidence_verification_is_first_action_inside_runner_"
        "main_after_prelaunch_dispatch": True,
        "authorization_evidence_verification_precedes_scientific_output_"
        "inspection_or_creation_inside_runner": True,
        "authorization_evidence_verification_is_process_first_action": False,
        "all_source_independent_verifiers_must_replay": True,
        "source_group_count": protocol.SOURCE_GROUP_COUNT,
        "terminal_code_count": protocol.TERMINAL_CODE_COUNT,
        "route_component_chain_count": protocol.ROUTE_COMPONENT_CHAIN_COUNT,
        "logical_terminal_representative_record_count": (
            protocol.LOGICAL_TERMINAL_REPRESENTATIVE_RECORD_COUNT
        ),
        "unique_route_component_record_count": (
            protocol.UNIQUE_ROUTE_COMPONENT_RECORD_COUNT
        ),
        "extra_nonrepresentative_v180r7r1_record_count": (
            protocol.EXTRA_NONREPRESENTATIVE_V180R7R1_RECORD_COUNT
        ),
        "terminal_shared_resource_receipt_count": (
            protocol.TERMINAL_SHARED_RESOURCE_RECEIPT_COUNT
        ),
        "campaign_scope_structural_obligation_count": (
            protocol.CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        ),
        "campaign_scope_actual_counter_record_count": (
            protocol.CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT
        ),
        "campaign_scope_actual_shared_resource_receipt_count": (
            protocol.CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT
        ),
        "campaign_scope_actual_work_vector_count": (
            protocol.CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT
        ),
        "campaign_scope_actual_comparison_vector_count": (
            protocol.CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT
        ),
        "campaign_scope_actual_projection_proof_count": (
            protocol.CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT
        ),
        "campaign_scope_actual_native_zero_attestation_count": (
            protocol.CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT
        ),
        "campaign_scope_authoritative_receipt_count": (
            protocol.CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT
        ),
        "total_authoritative_shared_resource_receipt_count": (
            protocol.TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT
        ),
        "counter_record_work_vector_comparison_vector_chain_required_per_route_component": (
            True
        ),
        "typed_receipt_required_per_logical_terminal": True,
        "typed_campaign_scope_structural_boundary_required": True,
        "typed_campaign_scope_actual_accounting_chain_present": False,
        "campaign_scope_structural_declarations_are_not_counter_records": True,
        "campaign_scope_derived_denominators_are_not_actual_measurements": True,
        "v180r7r1_construction_axis_separate": True,
        "output_bytes_exact_fixed_point_required": True,
        "producer_free_aggregate_reconstruction_required": True,
        "historical_summary_translation_forbidden": True,
        "retained_predecessor_outcome_bytes_accessed": True,
        "v180r12r2_aggregation_execution_started": False,
        "v180r12r2_aggregation_execution_count": 0,
        "v180r12r2_outcome_bytes_accessed": False,
        "authorization_frozen_before_any_v180r12r2_outcome": True,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_BLOCKER": protocol.COUNTER_COMPLETENESS_BLOCKER,
        "fresh_v180r12r3_actual_measurement_ledger_required": True,
        "fresh_v180r12r3_authorization_and_execution_required": True,
        "v180r12r2_counter_completeness_claimed": False,
        "v180r12r2_workload_economics_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "outcome_free": True,
    }
    return {
        **payload,
        "execution_authorization_id": domains.extension_content_id_v180r12r2(
            domains.CONSTRUCTION_K7_EXECUTION_AUTHORIZATION_V180R12R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TenTerminalAggregationExecutionAuthorizationV180R12R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        if not (
            self._issuer is _ISSUER
            and type(document) is dict
            and canonical_json_bytes(document) == self.canonical_bytes
            and document.get("execution_authorization_id") == self.authorization_id
        ):
            _fail("V180r12r2 authorization is foreign or noncanonical")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


@lru_cache(maxsize=1)
def freeze_ten_terminal_aggregation_execution_authorization_v180r12r2() -> (
    TenTerminalAggregationExecutionAuthorizationV180R12R2
):
    document = build_ten_terminal_aggregation_execution_authorization_v180r12r2()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != "0" * 64 and not (
        document["execution_authorization_id"] == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V180r12r2 frozen execution authorization identity changed")
    return TenTerminalAggregationExecutionAuthorizationV180R12R2(
        _ISSUER,
        raw,
        document["execution_authorization_id"],
    )


__all__ = (
    "ADDRESS_SPACE_HARD_CAP_BYTES",
    "AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS",
    "AUTHORIZATION_EVIDENCE_SOURCE_BOUNDARY_GIT_PROCESS_COUNT",
    "EXECUTION_NONCE",
    "EXPECTED_AGGREGATION_EXECUTION_SLOT_ID",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_PROTOCOL_ID",
    "FAILURE_EMERGENCY_RESERVE_BYTES",
    "FAILURE_MESSAGE_BYTE_CAP",
    "FAILURE_OBSERVATION_STREAM_BUFFER_BYTES",
    "FAILURE_TYPE_BYTE_CAP",
    "FAILURE_RELATIVE_PATH",
    "LOGICAL_OCCURRENCE_ID",
    "MAXIMUM_FIXED_POINT_ITERATIONS",
    "OUTPUT_ROOT_RELATIVE_PATH",
    "OUTPUT_TOTAL_BYTE_CAP",
    "RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH",
    "RUNTIME_CAS_ROOT_RELATIVE_PATH",
    "SOURCE_CATALOG_MODULE_CAP",
    "SOURCE_CATALOG_TOTAL_BYTE_CAP",
    "TERMINAL_RELATIVE_PATH",
    "TIMEOUT_SECONDS",
    "TenTerminalAggregationExecutionAuthorizationV180R12R2",
    "TenTerminalAggregationExecutionAuthorizationV180R12R2Error",
    "VERIFICATION_FAILURE_RELATIVE_PATH",
    "VERIFICATION_RELATIVE_PATH",
    "VERIFICATION_TERMINAL_INPUT_BYTE_CAP",
    "WORKER_PROCESS_COUNT",
    "build_ten_terminal_aggregation_execution_authorization_v180r12r2",
    "freeze_ten_terminal_aggregation_execution_authorization_v180r12r2",
    "normalize_authorization_evidence_wrapper_source_v180r12r2",
    "replay_authorization_source_facts_v180r12r2",
)
