"""Producer-free verification of the V180r12r2 ten-terminal aggregate.

The verifier never imports the aggregation producer.  It captures the ten
retained terminal/verification files through one symlink-free stable-read
epoch, replays each retained verifier, and independently reconstructs every
source, route-component, terminal, authoritative occurrence receipt, and
construction-axis receipt plus the non-authoritative campaign structural
boundary before comparing the exact aggregate bytes.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import gc
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import (
    construction_k7_cached_exact_infeasibility_production_terminal_independent_verifier_v180r8
    as r8_verifier,
)
from acfqp import construction_k7_domain_registry_extension_v180r12r2 as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r2e as subdomains
from acfqp import (
    construction_k7_full_ground_fallback_production_terminal_independent_verifier_v180r7r1
    as r7r1_verifier,
)
from acfqp import construction_k7_remaining_terminal_evidence_freeze_v180r9 as r9_evidence
from acfqp import (
    construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2
    as authorization,
)
from acfqp import construction_k7_ten_terminal_aggregation_protocol_v180r12r2 as protocol
from acfqp import (
    construction_k7_v34_retained_recovery_authorization_v180r11
    as r11_authorization,
)
from acfqp import (
    construction_k7_v34_retained_recovery_independent_verifier_v180r11
    as r11_verifier,
)
from acfqp import (
    construction_k7_v36_retained_recovery_authorization_v180r10r1
    as r10r1_authorization,
)
from acfqp import (
    construction_k7_v36_retained_recovery_independent_verifier_v180r10r1
    as r10r1_verifier,
)
from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    NativeZeroAttestationV1,
    ReducerEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import ActualProjectionProofV1, verify_actual_projection_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


MAXIMUM_FIXED_POINT_ITERATIONS = 32
WORKING_BYTES_HARD_CAP = 16 * 1024 * 1024 * 1024
SOURCE_GROUP_COUNT = 5
TERMINAL_RECEIPT_COUNT = 10
ROUTE_COMPONENT_CHAIN_COUNT = 12
COUNTER_RECORDS_PER_V9_CHAIN = 269
TEN_TERMINAL_REPRESENTATIVE_COUNTER_RECORD_COUNT = 2_690
ROUTE_COMPONENT_COUNTER_RECORD_COUNT = 3_228
V180R7R1_ADDITIONAL_COUNTER_RECORD_COUNT = 538
OCCURRENCE_SHARED_RESOURCE_RECEIPT_COUNT = 90
CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT = 9
CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT = 0
CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT = 0
CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT = 0
CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT = 0
CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT = 0
CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT = 0
CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT = 0
TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT = 90
COUNTER_COMPLETENESS_BLOCKER = "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
TRANSIENT_HEAP_RELEASE_PHASE_COUNT = 2 * SOURCE_GROUP_COUNT
TRANSIENT_HEAP_RELEASE_AUTHORITY_CLASS = (
    "PREAUTHORIZATION_MEMORY_LIFECYCLE_STRUCTURAL_OBLIGATION"
)

SHARED_RESOURCE_PATHS = (
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
_CAMPAIGN_SCHEMA_VERSION = "1.0.0"
_CAMPAIGN_SCOPE_KIND = "TEN_TERMINAL_AGGREGATION_ORCHESTRATION"
_CAMPAIGN_OBLIGATION_QUANTITIES = {
    "common.hash_invocations": 15,
    "common.integrity_checks": 10,
    "common.protocol_checks": 10,
}
_CAMPAIGN_ABSENCE_PATHS = (
    "io.mounted_bytes_peak",
    "io.staged_bytes",
    "process.launches",
)
_CAMPAIGN_STRUCTURAL_ROW_FIELDS = {
    "path",
    "declared_quantity",
    "quantity_semantics",
    "authority_class",
    "actual_measurement_present",
    "counter_gate_eligible",
    "economics_gate_eligible",
}
_CAMPAIGN_STRUCTURAL_BOUNDARY_FIELDS = {
    "schema",
    "schema_version",
    "scope",
    "aggregation_protocol_id",
    "execution_authorization_id",
    "subject_id",
    "source_receipt_ids",
    "source_group_count",
    "structural_declarations",
    "structural_declaration_count",
    "actual_counter_record_count",
    "actual_work_vector_present",
    "actual_comparison_vector_present",
    "actual_projection_proof_present",
    "actual_native_zero_attestation_present",
    "occurrence_route_record_count",
    "construction_axis_record_count",
    "campaign_scope_authoritative_receipt_count",
    "authoritative_occurrence_receipt_count",
    "authoritative_receipt_total",
    "hash_invocation_obligation_count",
    "integrity_check_obligation_count",
    "protocol_check_obligation_count",
    "derived_input_byte_denominator",
    "derived_output_byte_denominator",
    "working_bytes_authorization_cap",
    "working_bytes_peak_measurement_present",
    "zero_absence_obligation_count",
    "native_zero_claim_count",
    "counter_gate_eligible",
    "economics_gate_eligible",
    "structural_boundary_only",
    "scientific_success_claimed",
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "official_scalar_cost",
    "official_N_break_even",
    "official_execution_allowed",
    "campaign_scope_structural_boundary_id",
}
EXPECTED_ROUTE_COMPONENTS = tuple(
    (terminal_code, route_kind)
    for terminal_code, route_kind, _source_kind, _representative
    in protocol.ORDERED_ROUTE_COMPONENT_SPECS
)
_PATH_FAMILY = {
    TerminalCode.ABSTRACT_CERTIFIED: "SUCCESS",
    TerminalCode.CACHED_EXACT_INFEASIBLE: "SUCCESS",
    TerminalCode.LOCAL_GROUND_RECOVERY: "FALLBACK",
    TerminalCode.FULL_GROUND_FALLBACK: "FALLBACK",
    TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: "FALLBACK",
    TerminalCode.FALLBACK_CAP_EXHAUSTED: "FALLBACK",
    TerminalCode.REBUILD_REQUIRED: "OOD",
    TerminalCode.INTEGRITY_FAILURE: "FAILURE",
    TerminalCode.PROTOCOL_FAILURE: "FAILURE",
    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: "FAILURE",
}

_WORK_VECTOR_FIELDS = {
    "counter_record_ids",
    "counter_registry_id",
    "records",
    "route_kind",
    "schema",
    "subject_id",
    "work_vector_id",
}
_COMPARISON_VECTOR_FIELDS = {
    "comparison_profile_id",
    "comparison_vector_id",
    "route_kind",
    "schema",
    "subject_id",
    "values",
    "work_vector_id",
}
_PROJECTION_PROOF_FIELDS = {
    "actual_projection_profile_id",
    "actual_projection_proof_id",
    "comparison_profile_id",
    "comparison_vector_id",
    "counter_registry_id",
    "projection_term_count",
    "schema",
    "schema_version",
    "source_lane",
    "work_scope",
    "work_vector_id",
}
_NATIVE_ZERO_FIELDS = {
    "native_zero_attestation_id",
    "recorder_ids",
    "schema",
    "work_vector_id",
    "zero_paths",
}
_SOURCE_RECEIPT_FIELDS = {
    "aggregation_protocol_id",
    "execution_authorization_id",
    "independent_verifier_replayed_before_aggregation",
    "schema",
    "source_kind",
    "source_receipt_id",
    "terminal_byte_count",
    "terminal_content_id",
    "terminal_relative_path",
    "terminal_sha256",
    "verification_byte_count",
    "verification_bytes_equal_replay",
    "verification_id",
    "verification_relative_path",
    "verification_sha256",
}
_ROUTE_COMPONENT_RECEIPT_FIELDS = {
    "actual_projection_proof_id",
    "aggregation_protocol_id",
    "comparison_vector_id",
    "component_ordinal",
    "counter_record_count",
    "counter_record_to_work_vector_to_comparison_vector_replayed",
    "execution_authorization_id",
    "historical_summary_translation_used",
    "independent_route_component",
    "native_zero_attestation_id",
    "path_family",
    "route_component_chain_receipt_id",
    "route_component_count_for_terminal",
    "route_kind",
    "schema",
    "source_receipt_id",
    "source_terminal_bundle_id",
    "source_verification_id",
    "terminal_code",
    "terminal_component_ordinal",
    "work_vector_id",
}
_TERMINAL_SHARED_RECEIPT_FIELDS = {
    "aggregation_protocol_id",
    "campaign_scope_resource_receipt",
    "construction_axis_receipt",
    "execution_authorization_id",
    "independent_source_verifier_replayed_nine_receipts",
    "native_zero_observed",
    "occurrence_shared_resource_receipt",
    "path",
    "reducer",
    "schema",
    "source_occurrence_shared_resource_receipt_ids",
    "source_occurrence_shared_resource_receipt_ids_embedded",
    "source_occurrence_shared_resource_receipt_count",
    "source_receipt_id",
    "source_route_component_values",
    "terminal_code",
    "terminal_shared_resource_receipt_id",
    "value",
}
_TERMINAL_RECEIPT_SET_FIELDS = {
    "aggregation_protocol_id",
    "all_nine_paths_present",
    "execution_authorization_id",
    "missing_path_inferred_zero",
    "ordered_paths",
    "receipt_count",
    "receipts",
    "schema",
    "source_receipt_id",
    "terminal_code",
    "terminal_shared_resource_receipt_ids",
    "terminal_shared_resource_receipt_set_id",
}
_TERMINAL_RECEIPT_FIELDS = {
    "aggregation_protocol_id",
    "all_route_component_counter_record_count",
    "execution_authorization_id",
    "historical_summary_translation_used",
    "independent_source_verifier_replayed_before_aggregation",
    "occurrence_shared_resource_receipt_count",
    "path_family",
    "representative_route_component_chain_receipt_id",
    "route_component_chain_receipt_ids",
    "route_component_count",
    "schema",
    "source_receipt_id",
    "source_terminal_bundle_id",
    "source_terminal_byte_count",
    "source_terminal_sha256",
    "source_verification_id",
    "ten_terminal_representative_counter_record_count",
    "terminal_chain_receipt_id",
    "terminal_code",
    "terminal_shared_resource_receipt_set_id",
}
_CONSTRUCTION_AXIS_RECEIPT_FIELDS = {
    "aggregation_protocol_id",
    "charged_to_any_route_component",
    "construction_axis_replayed_separately",
    "construction_work",
    "construction_work_sha256",
    "execution_authorization_id",
    "historical_summary_translation_used",
    "materialization_manifest_id",
    "materialized_source_byte_count",
    "materialized_source_module_count",
    "materialized_source_tree_id",
    "occurrence_route_counter_record_count",
    "one_time_construction_axis",
    "schema",
    "source_catalog_manifest_id",
    "source_closure_id",
    "source_closure_repair_id",
    "source_receipt_id",
    "source_terminal_bundle_id",
    "source_verification_id",
    "v180r7r1_construction_axis_receipt_id",
}
_MATERIALIZED_SOURCE_REFERENCE_FIELDS = {
    "charged_to_any_route_component",
    "construction_work",
    "materialization_manifest_canonical_byte_count",
    "materialization_manifest_canonical_sha256",
    "materialization_manifest_id",
    "materialized_source_byte_count",
    "materialized_source_module_count",
    "materialized_source_relative_path",
    "materialized_source_tree_id",
    "one_time_construction_axis",
    "schema",
    "scientific_occurrence_execution_work",
    "source_catalog_manifest_id",
    "source_closure_id",
    "source_closure_repair_id",
}
_BUNDLE_FIELDS = {
    "BREAK_EVEN_GATE",
    "COUNTER_COMPLETENESS_BLOCKER",
    "COUNTER_COMPLETENESS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "all_five_source_independent_verifiers_replayed",
    "all_ten_occurrence_shared_resource_receipt_sets_present",
    "all_twelve_route_component_chains_present",
    "aggregation_protocol_id",
    "campaign_scope_actual_comparison_vector_count",
    "campaign_scope_actual_counter_record_count",
    "campaign_scope_actual_native_zero_attestation_count",
    "campaign_scope_actual_projection_proof_count",
    "campaign_scope_actual_shared_resource_receipt_count",
    "campaign_scope_actual_work_vector_count",
    "campaign_scope_authoritative_receipt_count",
    "campaign_scope_structural_boundary",
    "campaign_scope_structural_obligation_count",
    "execution_authorization_id",
    "fixed_point_iteration",
    "historical_summary_translation_used",
    "occurrence_shared_resource_receipt_count",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "ordered_route_components",
    "ordered_terminal_codes",
    "output_bytes_fixed_point",
    "producer_bundle_independently_replayed",
    "production_aggregation_bundle_id",
    "route_component_chain_receipt_count",
    "route_component_chain_receipts",
    "route_component_counter_closure_status",
    "route_component_counter_record_count",
    "schema",
    "source_group_count",
    "source_verification_receipt_count",
    "source_verification_receipts",
    "ten_terminal_representative_counter_record_count",
    "terminal_code_count",
    "terminal_receipt_count",
    "terminal_receipts",
    "terminal_shared_resource_receipt_sets",
    "total_authoritative_shared_resource_receipt_count",
    "v180r7r1_additional_counter_record_count",
    "v180r7r1_construction_axis_receipt",
    "v180r7r1_construction_axis_receipt_count",
    "v180r7r1_construction_work_charged_to_route_components",
}


class ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error(
    RuntimeError
):
    """A retained byte, accounting chain, schema, or claim lock changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error(
        message
    )


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _release_transient_verifier_heap() -> None:
    gc.collect()
    try:
        trim = ctypes.CDLL(None).malloc_trim
    except (AttributeError, OSError) as error:
        raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error(
            "required glibc malloc_trim lifecycle primitive is unavailable"
        ) from error
    trim.argtypes = (ctypes.c_size_t,)
    trim.restype = ctypes.c_int
    result = trim(0)
    if type(result) is not int or result not in {0, 1}:
        _fail("glibc malloc_trim returned a foreign status")


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError, UnicodeError) as error:
        raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error(
            f"{label} is not one canonical object"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _stat_identity(info: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _absolute_parts(path: Path) -> tuple[str, ...]:
    absolute = Path(os.path.abspath(os.fspath(path)))
    if absolute.anchor != "/" or not absolute.parts[1:]:
        _fail("stable-read root must name one absolute child")
    return absolute.parts[1:]


def _open_directory_symlink_free(path: Path) -> int:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open("/", flags)
    try:
        for part in _absolute_parts(path):
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        info = os.fstat(descriptor)
        if not stat.S_ISDIR(info.st_mode):
            _fail("stable-read root is not one directory")
        return descriptor
    except (OSError, ValueError) as error:
        os.close(descriptor)
        raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error(
            "stable-read root contains a link or nondirectory"
        ) from error


def _relative_parts(relative_path: str) -> tuple[str, ...]:
    if type(relative_path) is not str or "\\" in relative_path:
        _fail("retained relative path is malformed")
    pure = PurePosixPath(relative_path)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != relative_path
    ):
        _fail("retained relative path is malformed")
    return pure.parts


def _read_regular_at(root_descriptor: int, relative_path: str) -> tuple[bytes, tuple[int, ...]]:
    parts = _relative_parts(relative_path)
    directory = os.dup(root_descriptor)
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        for part in parts[:-1]:
            next_directory = os.open(part, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = next_directory
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory,
        )
    except OSError as error:
        os.close(directory)
        raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error(
            f"retained input is absent, linked, or nonregular: {relative_path}"
        ) from error
    finally:
        if "descriptor" in locals():
            os.close(directory)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _fail("retained input is not one singly linked regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        identity = _stat_identity(after)
        if _stat_identity(before) != identity or len(raw) != after.st_size:
            _fail("retained input changed during stable read")
        return raw, identity
    finally:
        os.close(descriptor)


def _capture_retained_epoch(repository_root: Path) -> dict[str, bytes]:
    if not isinstance(repository_root, Path) or not repository_root.is_dir():
        _fail("repository root is absent")
    ordered_paths = tuple(
        path
        for spec in protocol.RETAINED_SOURCE_GROUP_SPECS
        for path in (spec[3], spec[8])
    )
    if len(ordered_paths) != 10 or len(set(ordered_paths)) != 10:
        _fail("retained input path denominator changed")
    root_descriptor = _open_directory_symlink_free(repository_root)
    try:
        first = {
            path: _read_regular_at(root_descriptor, path)
            for path in ordered_paths
        }
        second = {
            path: _read_regular_at(root_descriptor, path)
            for path in ordered_paths
        }
    finally:
        os.close(root_descriptor)
    for path in ordered_paths:
        if first[path] != second[path]:
            _fail("retained input changed across the stable-read epoch")
    return {path: first[path][0] for path in ordered_paths}


def _claim_locks(
    document: Mapping[str, Any],
    label: str,
    *,
    scalar_field_policy: str = "EXPLICIT_NULL",
) -> None:
    if scalar_field_policy == "EXPLICIT_NULL":
        scalar_fields_locked = (
            document.get("official_scalar_cost") is None
            and "official_scalar_cost" in document
            and document.get("official_N_break_even") is None
            and "official_N_break_even" in document
        )
    elif scalar_field_policy == "ABSENT":
        scalar_fields_locked = (
            "official_scalar_cost" not in document
            and "official_N_break_even" not in document
        )
    else:
        _fail(f"{label} scalar-field policy is unknown")
    if not (
        type(document) is dict
        and document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and scalar_fields_locked
        and document.get("official_execution_allowed") is False
    ):
        _fail(f"{label} accounting or official gate changed")


def _verification_claim_locks(
    document: Mapping[str, Any], source_kind: str
) -> None:
    _claim_locks(
        document,
        f"{source_kind} verification",
        scalar_field_policy=(
            "EXPLICIT_NULL"
            if source_kind == "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN"
            else "ABSENT"
        ),
    )


@dataclass(frozen=True, slots=True)
class _VerifiedGroup:
    source_kind: str
    source_authorization_id: str
    covered_terminal_codes: tuple[str, ...]
    terminal_path: str
    terminal_byte_count: int
    terminal_sha256: str
    terminal: dict[str, Any]
    verification_path: str
    verification_byte_count: int
    verification_sha256: str
    verification: dict[str, Any]
    terminal_id: str
    verification_id: str


@dataclass(frozen=True, slots=True)
class _EpochGroup:
    source_kind: str
    terminal_bytes: bytes
    verification_bytes: bytes


_SINGLE_CHAIN_PROJECTION_FIELDS = frozenset(
    {
        "projection_kind",
        "terminal_code",
        "terminal_work_vector",
        "terminal_comparison_vector",
        "terminal_actual_projection_proof",
        "terminal_native_zero_attestation",
        "source_occurrence_shared_resource_receipt_ids",
    }
)
_R7R1_PROJECTION_FIELDS = frozenset(
    {
        "projection_kind",
        "terminal_code",
        "v9_lifted_route_components",
        "source_occurrence_shared_resource_receipt_ids",
        "materialized_source_reference",
    }
)
_R7R1_COMPONENT_PROJECTION_FIELDS = frozenset(
    {
        "independent_route_component",
        "materialized_source_construction_work_charged_to_component",
        "v9_work_vector",
        "v9_comparison_vector",
        "v9_actual_projection_proof",
        "v9_native_zero_attestation",
    }
)
_R9_PROJECTION_FIELDS = frozenset({"projection_kind", "terminal_rows"})
_R9_ROW_PROJECTION_FIELDS = frozenset(
    {
        "terminal_code",
        "production_terminal_bundle_id",
        "canonical_byte_count",
        "canonical_sha256",
        "terminal_work_vector",
        "terminal_comparison_vector",
        "terminal_actual_projection_proof",
        "terminal_native_zero_attestation",
        "source_occurrence_shared_resource_receipt_ids",
    }
)
_VERIFICATION_PROJECTION_FIELDS = frozenset(
    {
        "construction_axis_replayed_separately",
        "construction_work_charged_to_any_route_component",
    }
)


def _shared_receipt_ids(document: Mapping[str, Any]) -> list[str]:
    receipt_set = document.get("shared_resource_receipt_set")
    receipts = receipt_set.get("receipts") if type(receipt_set) is dict else None
    if type(receipts) is not list:
        _fail("retained shared-resource receipts changed")
    values = [
        row.get("receipt_id") if type(row) is dict else None
        for row in receipts
    ]
    if not (
        len(values) == len(SHARED_RESOURCE_PATHS)
        and len(values) == len(set(values))
        and all(type(value) is str and len(value) == 64 for value in values)
    ):
        _fail("retained shared-resource receipt identities changed")
    return values  # type: ignore[return-value]


def _compact_terminal_projection(
    source_kind: str,
    terminal: Mapping[str, Any],
) -> dict[str, Any]:
    if source_kind in {
        "V180R11_RETAINED_V34_FINISH_FORWARD",
        "V180R10R1_RETAINED_V36_FINISH_FORWARD",
        "V180R8_FRESH_CACHED_EXACT",
    }:
        if source_kind == "V180R8_FRESH_CACHED_EXACT":
            source_ids = _shared_receipt_ids(terminal)
        else:
            source_replay = terminal.get("source_independent_verification")
            if not (
                type(source_replay) is dict
                and source_replay.get(
                    "all_nine_shared_resource_receipts_replayed"
                )
                is True
            ):
                _fail("retained finish-forward lost nine-path source replay")
            source_ids = []
        projection = {
            "projection_kind": "SINGLE_CHAIN",
            "terminal_code": terminal.get("terminal_code"),
            "terminal_work_vector": terminal.get("terminal_work_vector"),
            "terminal_comparison_vector": terminal.get(
                "terminal_comparison_vector"
            ),
            "terminal_actual_projection_proof": terminal.get(
                "terminal_actual_projection_proof"
            ),
            "terminal_native_zero_attestation": terminal.get(
                "terminal_native_zero_attestation"
            ),
            "source_occurrence_shared_resource_receipt_ids": source_ids,
        }
        if set(projection) != _SINGLE_CHAIN_PROJECTION_FIELDS:
            raise AssertionError("single-chain compact projection changed")
        return projection
    if source_kind == "V180R7R1_FRESH_FULL_GROUND_FALLBACK":
        components = terminal.get("v9_lifted_route_components")
        source_bundle = terminal.get("source_occurrence_accounting_bundle")
        reference = terminal.get("materialized_source_reference")
        if not (
            type(components) is list
            and len(components) == 3
            and type(source_bundle) is dict
            and type(reference) is dict
        ):
            _fail("V180r7r1 compact projection source changed")
        projected_components = []
        for component in components:
            if type(component) is not dict:
                _fail("V180r7r1 route component changed")
            projected = {
                field: component.get(field)
                for field in _R7R1_COMPONENT_PROJECTION_FIELDS
            }
            projected_components.append(projected)
        source_ids = source_bundle.get("shared_resource_receipt_ids")
        if not (
            type(source_ids) is list
            and len(source_ids) == len(SHARED_RESOURCE_PATHS)
            and len(source_ids) == len(set(source_ids))
            and all(type(value) is str and len(value) == 64 for value in source_ids)
        ):
            _fail("V180r7r1 shared-resource receipt identities changed")
        projection = {
            "projection_kind": "THREE_CHAIN_WITH_CONSTRUCTION_AXIS",
            "terminal_code": terminal.get("terminal_code"),
            "v9_lifted_route_components": projected_components,
            "source_occurrence_shared_resource_receipt_ids": list(source_ids),
            "materialized_source_reference": reference,
        }
        if set(projection) != _R7R1_PROJECTION_FIELDS:
            raise AssertionError("V180r7r1 compact projection changed")
        return projection
    if source_kind == "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN":
        rows = terminal.get("terminal_rows")
        if type(rows) is not list or len(rows) != 6:
            _fail("V180r9 six-terminal rows changed")
        projected_rows = []
        for row in rows:
            if type(row) is not dict or type(row.get("bundle")) is not dict:
                _fail("V180r9 terminal bundle changed")
            bundle = row["bundle"]
            bundle_bytes = canonical_json_bytes(bundle)
            if not (
                row.get("canonical_byte_count") == len(bundle_bytes)
                and row.get("canonical_sha256") == _sha256(bundle_bytes)
                and row.get("production_terminal_bundle_id")
                == bundle.get("production_terminal_bundle_id")
                and row.get("terminal_code") == bundle.get("terminal_code")
            ):
                _fail("V180r9 terminal row exact byte fact changed")
            projected = {
                "terminal_code": row["terminal_code"],
                "production_terminal_bundle_id": row[
                    "production_terminal_bundle_id"
                ],
                "canonical_byte_count": len(bundle_bytes),
                "canonical_sha256": _sha256(bundle_bytes),
                "terminal_work_vector": bundle.get("terminal_work_vector"),
                "terminal_comparison_vector": bundle.get(
                    "terminal_comparison_vector"
                ),
                "terminal_actual_projection_proof": bundle.get(
                    "terminal_actual_projection_proof"
                ),
                "terminal_native_zero_attestation": bundle.get(
                    "terminal_native_zero_attestation"
                ),
                "source_occurrence_shared_resource_receipt_ids": (
                    _shared_receipt_ids(bundle)
                ),
            }
            if set(projected) != _R9_ROW_PROJECTION_FIELDS:
                raise AssertionError("V180r9 row compact projection changed")
            projected_rows.append(projected)
        projection = {
            "projection_kind": "SIX_TERMINAL_CAMPAIGN",
            "terminal_rows": projected_rows,
        }
        if set(projection) != _R9_PROJECTION_FIELDS:
            raise AssertionError("V180r9 compact projection changed")
        return projection
    _fail("retained source kind has no compact projection")


def _compact_verification_projection(
    source_kind: str,
    verification: Mapping[str, Any],
) -> dict[str, Any]:
    projection = {
        "construction_axis_replayed_separately": (
            verification.get("construction_axis_replayed_separately")
            if source_kind == "V180R7R1_FRESH_FULL_GROUND_FALLBACK"
            else None
        ),
        "construction_work_charged_to_any_route_component": (
            verification.get(
                "construction_work_charged_to_any_route_component"
            )
            if source_kind == "V180R7R1_FRESH_FULL_GROUND_FALLBACK"
            else None
        ),
    }
    if set(projection) != _VERIFICATION_PROJECTION_FIELDS:
        raise AssertionError("compact verification projection changed")
    return projection


def _replay_group_semantics(group: _EpochGroup, repository_root: Path) -> dict[str, Any]:
    base = repository_root / ".tmp" / "exact-freeze"
    try:
        if group.source_kind == "V180R11_RETAINED_V34_FINISH_FORWARD":
            replay = r11_verifier.verify_v34_retained_recovery_bytes_independently_v180r11(
                group.terminal_bytes,
                base / "v180r5_v34_production_output",
                recovery_authorization_id=r11_authorization.EXPECTED_AUTHORIZATION_ID,
            )
        elif group.source_kind == "V180R10R1_RETAINED_V36_FINISH_FORWARD":
            replay = r10r1_verifier.verify_v36_retained_recovery_bytes_independently_v180r10r1(
                group.terminal_bytes,
                base / "v180r10_v36_resource_successor_output",
                recovery_authorization_id=r10r1_authorization.EXPECTED_AUTHORIZATION_ID,
            )
        elif group.source_kind == "V180R7R1_FRESH_FULL_GROUND_FALLBACK":
            replay = r7r1_verifier.verify_full_ground_fallback_terminal_independently_v180r7r1(
                group.terminal_bytes,
                base / "v180r7r1_full_ground_fallback_output",
            )
        elif group.source_kind == "V180R8_FRESH_CACHED_EXACT":
            replay = r8_verifier.verify_cached_exact_terminal_independently_v180r8(
                group.terminal_bytes
            )
        elif group.source_kind == "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN":
            replay = r9_evidence.verify_frozen_remaining_terminal_evidence_v180r9(
                group.terminal_bytes,
                group.verification_bytes,
            )
        else:  # pragma: no cover - protocol exhaustiveness
            _fail("unknown retained source group")
    except Exception as error:
        raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error(
            f"{group.source_kind} independent semantic replay failed"
        ) from error
    if type(replay) is not dict or canonical_json_bytes(replay) != group.verification_bytes:
        _fail(f"{group.source_kind} verification bytes changed under replay")
    return replay


def _capture_verified_groups(
    repository_root: Path,
    *,
    replay_semantics: bool = True,
) -> tuple[_VerifiedGroup, ...]:
    epoch = _capture_retained_epoch(repository_root)
    groups: list[_VerifiedGroup] = []
    for spec in protocol.RETAINED_SOURCE_GROUP_SPECS:
        (
            source_kind,
            source_authorization_id,
            covered_codes,
            terminal_path,
            terminal_id_key,
            terminal_id,
            terminal_byte_count,
            terminal_sha256,
            verification_path,
            verification_id,
            verification_byte_count,
            verification_sha256,
        ) = spec
        terminal_bytes = epoch.pop(terminal_path)
        verification_bytes = epoch.pop(verification_path)
        if not (
            len(terminal_bytes) == terminal_byte_count
            and _sha256(terminal_bytes) == terminal_sha256
            and len(verification_bytes) == verification_byte_count
            and _sha256(verification_bytes) == verification_sha256
        ):
            _fail(f"{source_kind} retained source bytes or identity changed")
        epoch_group = _EpochGroup(
            source_kind,
            terminal_bytes,
            verification_bytes,
        )
        if replay_semantics:
            _replay_group_semantics(epoch_group, repository_root)
        _release_transient_verifier_heap()
        terminal = _object(terminal_bytes, f"{source_kind} terminal")
        verification = _object(verification_bytes, f"{source_kind} verification")
        if not (
            terminal.get(terminal_id_key) == terminal_id
            and verification.get("verification_id") == verification_id
        ):
            _fail(f"{source_kind} retained source bytes or identity changed")
        _claim_locks(terminal, f"{source_kind} terminal")
        _verification_claim_locks(verification, source_kind)
        group = _VerifiedGroup(
            source_kind,
            source_authorization_id,
            tuple(covered_codes),
            terminal_path,
            len(terminal_bytes),
            _sha256(terminal_bytes),
            _compact_terminal_projection(source_kind, terminal),
            verification_path,
            len(verification_bytes),
            _sha256(verification_bytes),
            _compact_verification_projection(source_kind, verification),
            terminal_id,
            verification_id,
        )
        groups.append(group)
        del terminal_bytes, verification_bytes, terminal, verification, epoch_group
        _release_transient_verifier_heap()
    if epoch:
        _fail("stable-read epoch retained unexpected bytes")
    if tuple(group.source_kind for group in groups) != tuple(
        spec[0] for spec in protocol.RETAINED_SOURCE_GROUP_SPECS
    ):
        _fail("five-source ordering changed")
    return tuple(groups)


def _protocol_source_rows(groups: Sequence[_VerifiedGroup]) -> list[dict[str, Any]]:
    return [
        {
            "source_kind": group.source_kind,
            "source_authorization_id": group.source_authorization_id,
            "covered_terminal_codes": list(group.covered_terminal_codes),
            "terminal_fact": {
                "relative_path": group.terminal_path,
                "content_id_key": next(
                    spec[4]
                    for spec in protocol.RETAINED_SOURCE_GROUP_SPECS
                    if spec[0] == group.source_kind
                ),
                "content_id": group.terminal_id,
                "byte_count": group.terminal_byte_count,
                "sha256": group.terminal_sha256,
            },
            "verification_fact": {
                "relative_path": group.verification_path,
                "verification_id": group.verification_id,
                "byte_count": group.verification_byte_count,
                "sha256": group.verification_sha256,
            },
            "status_at_successor_freeze": "COMPLETED_AND_INDEPENDENTLY_VERIFIED",
        }
        for group in groups
    ]


def _authorization_input_rows(groups: Sequence[_VerifiedGroup]) -> list[dict[str, Any]]:
    return [
        row
        for group in groups
        for row in (
            {
                "source_kind": group.source_kind,
                "role": "TERMINAL",
                "relative_path": group.terminal_path,
                "content_id": group.terminal_id,
                "byte_count": group.terminal_byte_count,
                "sha256": group.terminal_sha256,
            },
            {
                "source_kind": group.source_kind,
                "role": "INDEPENDENT_VERIFICATION",
                "relative_path": group.verification_path,
                "content_id": group.verification_id,
                "byte_count": group.verification_byte_count,
                "sha256": group.verification_sha256,
            },
        )
    ]


def _frozen_contract() -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    frozen_protocol = protocol.freeze_ten_terminal_aggregation_protocol_v180r12r2()
    frozen_authorization = (
        authorization.freeze_ten_terminal_aggregation_execution_authorization_v180r12r2()
    )
    protocol_document = frozen_protocol.to_document()
    authorization_document = frozen_authorization.to_document()
    if not (
        protocol.EXPECTED_PROTOCOL_ID != "0" * 64
        and authorization.EXPECTED_AUTHORIZATION_ID != "0" * 64
        and frozen_protocol.aggregation_protocol_id == protocol.EXPECTED_PROTOCOL_ID
        and frozen_authorization.authorization_id == authorization.EXPECTED_AUTHORIZATION_ID
        and authorization_document.get("aggregation_protocol_id")
        == frozen_protocol.aggregation_protocol_id
    ):
        _fail("V180r12r2 protocol or authorization is not frozen")
    _claim_locks(protocol_document, "V180r12r2 protocol")
    _claim_locks(authorization_document, "V180r12r2 authorization")
    try:
        authorization.replay_authorization_source_facts_v180r12r2(
            authorization_document
        )
    except Exception as error:
        raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error(
            "authorized verifier source closure changed"
        ) from error
    return (
        frozen_protocol.aggregation_protocol_id,
        frozen_authorization.authorization_id,
        protocol_document,
        authorization_document,
    )


def _assert_input_contract(
    protocol_document: Mapping[str, Any],
    authorization_document: Mapping[str, Any],
    groups: Sequence[_VerifiedGroup],
) -> None:
    protocol_rows = _protocol_source_rows(groups)
    authorization_rows = _authorization_input_rows(groups)
    components = protocol_document.get("ordered_route_components")
    if not (
        protocol_document.get("retained_source_groups") == protocol_rows
        and protocol_document.get("retained_source_total_byte_count")
        == sum(
            group.terminal_byte_count + group.verification_byte_count
            for group in groups
        )
        and protocol_document.get("source_group_count") == SOURCE_GROUP_COUNT
        and protocol_document.get("terminal_code_count") == TERMINAL_RECEIPT_COUNT
        and protocol_document.get("route_component_chain_count")
        == ROUTE_COMPONENT_CHAIN_COUNT
        and type(components) is list
        and [(row.get("terminal_code"), row.get("route_kind")) for row in components]
        == list(EXPECTED_ROUTE_COMPONENTS)
        and [row.get("component_ordinal") for row in components]
        == list(range(ROUTE_COMPONENT_CHAIN_COUNT))
        and all(row.get("counter_record_count") == COUNTER_RECORDS_PER_V9_CHAIN for row in components)
        and authorization_document.get("retained_source_input_facts")
        == authorization_rows
        and authorization_document.get("retained_source_input_fact_count") == 10
        and authorization_document.get("retained_source_input_total_byte_count")
        == sum(row["byte_count"] for row in authorization_rows)
        and authorization_document.get("retained_source_input_facts_sha256")
        == _sha256(canonical_json_bytes(authorization_rows))
        and authorization_document.get("source_group_count") == SOURCE_GROUP_COUNT
        and authorization_document.get("terminal_code_count") == TERMINAL_RECEIPT_COUNT
        and authorization_document.get("route_component_chain_count")
        == ROUTE_COMPONENT_CHAIN_COUNT
    ):
        _fail("V180r12r2 protocol, authorization, or retained source facts changed")


def _source_receipt(
    group: _VerifiedGroup,
    *,
    aggregation_protocol_id: str,
    execution_authorization_id: str,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.ten_terminal_source_verification_receipt.v180r12r2",
        "aggregation_protocol_id": aggregation_protocol_id,
        "execution_authorization_id": execution_authorization_id,
        "source_kind": group.source_kind,
        "terminal_relative_path": group.terminal_path,
        "terminal_content_id": group.terminal_id,
        "terminal_byte_count": group.terminal_byte_count,
        "terminal_sha256": group.terminal_sha256,
        "verification_relative_path": group.verification_path,
        "verification_id": group.verification_id,
        "verification_byte_count": group.verification_byte_count,
        "verification_sha256": group.verification_sha256,
        "independent_verifier_replayed_before_aggregation": True,
        "verification_bytes_equal_replay": True,
    }
    document = {
        **payload,
        "source_receipt_id": subdomains.extension_content_id_v180r12r2e(
            subdomains.CONSTRUCTION_K7_SOURCE_RECEIPT_V180R12R2E_DOMAIN,
            payload,
        ),
    }
    if set(document) != _SOURCE_RECEIPT_FIELDS:
        raise AssertionError("V180r12r2 source receipt schema changed")
    return document


def _verify_chain(
    *,
    vector_document: Mapping[str, Any],
    comparison_document: Mapping[str, Any],
    proof_document: Mapping[str, Any],
    zero_document: Mapping[str, Any],
    expected_route_kind: str,
) -> WorkVectorV1:
    if not (
        type(vector_document) is dict
        and set(vector_document) == _WORK_VECTOR_FIELDS
        and type(comparison_document) is dict
        and set(comparison_document) == _COMPARISON_VECTOR_FIELDS
        and type(proof_document) is dict
        and set(proof_document) == _PROJECTION_PROOF_FIELDS
        and type(zero_document) is dict
        and set(zero_document) == _NATIVE_ZERO_FIELDS
    ):
        _fail("route-component accounting document schema changed")
    registry = registry_v9.official_counter_registry_v9()
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry,
        comparison_profile,
    )
    try:
        vector = WorkVectorV1.from_dict(vector_document, registry)
        comparison = ComparisonVectorV1.from_dict(comparison_document)
        proof = ActualProjectionProofV1.from_dict(proof_document)
        zero = NativeZeroAttestationV1.from_dict(zero_document)
        recomputed = verify_actual_projection_v1(
            proof,
            vector,
            comparison,
            registry,
            comparison_profile,
            actual_profile,
        )
    except Exception as error:
        raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error(
            "route-component accounting chain failed replay"
        ) from error
    if not (
        len(vector.records) == COUNTER_RECORDS_PER_V9_CHAIN
        and vector.route_kind.value == expected_route_kind
        and recomputed == comparison
        and zero == NativeZeroAttestationV1.derive(vector, registry)
    ):
        _fail("route-component accounting chain changed")
    return vector


@dataclass(frozen=True, slots=True)
class _ComponentInput:
    terminal_code: TerminalCode
    source_receipt_id: str
    source_verification_id: str
    source_terminal_id: str
    terminal_byte_count: int
    terminal_sha256: str
    vector_document: dict[str, Any]
    comparison_document: dict[str, Any]
    proof_document: dict[str, Any]
    zero_document: dict[str, Any]
    component_ordinal: int
    component_count: int


def _component_inputs(
    groups: Sequence[_VerifiedGroup],
    source_receipts: Sequence[Mapping[str, Any]],
) -> tuple[_ComponentInput, ...]:
    source_ids = {
        group.source_kind: receipt["source_receipt_id"]
        for group, receipt in zip(groups, source_receipts, strict=True)
    }
    result: list[_ComponentInput] = []
    for group in groups:
        document = group.terminal
        if group.source_kind == "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN":
            rows = document.get("terminal_rows")
            if type(rows) is not list or len(rows) != 6:
                _fail("V180r9 six-terminal rows changed")
            for row in rows:
                if type(row) is not dict or set(row) != _R9_ROW_PROJECTION_FIELDS:
                    _fail("V180r9 terminal row changed")
                try:
                    code = TerminalCode(row.get("terminal_code"))
                except (TypeError, ValueError) as error:
                    raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error(
                        "V180r9 terminal code changed"
                    ) from error
                result.append(
                    _ComponentInput(
                        code,
                        source_ids[group.source_kind],
                        group.verification_id,
                        row["production_terminal_bundle_id"],
                        row["canonical_byte_count"],
                        row["canonical_sha256"],
                        row["terminal_work_vector"],
                        row["terminal_comparison_vector"],
                        row["terminal_actual_projection_proof"],
                        row["terminal_native_zero_attestation"],
                        0,
                        1,
                    )
                )
            continue
        try:
            code = TerminalCode(document.get("terminal_code"))
        except (TypeError, ValueError) as error:
            raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error(
                f"{group.source_kind} terminal code changed"
            ) from error
        if code is TerminalCode.FULL_GROUND_FALLBACK:
            components = document.get("v9_lifted_route_components")
            if type(components) is not list or len(components) != 3:
                _fail("V180r7r1 three route components changed")
            for ordinal, component in enumerate(components):
                if not (
                    type(component) is dict
                    and component.get("independent_route_component") is True
                    and component.get(
                        "materialized_source_construction_work_charged_to_component"
                    )
                    is False
                ):
                    _fail("V180r7r1 route-component separation changed")
                result.append(
                    _ComponentInput(
                        code,
                        source_ids[group.source_kind],
                        group.verification_id,
                        group.terminal_id,
                        group.terminal_byte_count,
                        group.terminal_sha256,
                        component["v9_work_vector"],
                        component["v9_comparison_vector"],
                        component["v9_actual_projection_proof"],
                        component["v9_native_zero_attestation"],
                        ordinal,
                        len(components),
                    )
                )
            continue
        result.append(
            _ComponentInput(
                code,
                source_ids[group.source_kind],
                group.verification_id,
                group.terminal_id,
                group.terminal_byte_count,
                group.terminal_sha256,
                document["terminal_work_vector"],
                document["terminal_comparison_vector"],
                document["terminal_actual_projection_proof"],
                document["terminal_native_zero_attestation"],
                0,
                1,
            )
        )
    return tuple(result)


def _route_component_receipt(
    component: _ComponentInput,
    *,
    aggregation_protocol_id: str,
    execution_authorization_id: str,
    global_component_ordinal: int,
) -> tuple[dict[str, Any], WorkVectorV1]:
    route_kind = component.vector_document.get("route_kind")
    if type(route_kind) is not str:
        _fail("route-component route kind is absent")
    vector = _verify_chain(
        vector_document=component.vector_document,
        comparison_document=component.comparison_document,
        proof_document=component.proof_document,
        zero_document=component.zero_document,
        expected_route_kind=route_kind,
    )
    payload = {
        "schema": "acfqp.route_component_chain_receipt.v180r12r2",
        "aggregation_protocol_id": aggregation_protocol_id,
        "execution_authorization_id": execution_authorization_id,
        "terminal_code": component.terminal_code.value,
        "path_family": _PATH_FAMILY[component.terminal_code],
        "source_receipt_id": component.source_receipt_id,
        "source_verification_id": component.source_verification_id,
        "source_terminal_bundle_id": component.source_terminal_id,
        "component_ordinal": global_component_ordinal,
        "terminal_component_ordinal": component.component_ordinal,
        "route_component_count_for_terminal": component.component_count,
        "route_kind": vector.route_kind.value,
        "work_vector_id": vector.work_vector_id,
        "comparison_vector_id": component.comparison_document["comparison_vector_id"],
        "actual_projection_proof_id": component.proof_document[
            "actual_projection_proof_id"
        ],
        "native_zero_attestation_id": component.zero_document[
            "native_zero_attestation_id"
        ],
        "counter_record_count": len(vector.records),
        "counter_record_to_work_vector_to_comparison_vector_replayed": True,
        "independent_route_component": True,
        "historical_summary_translation_used": False,
    }
    document = {
        **payload,
        "route_component_chain_receipt_id": (
            subdomains.extension_content_id_v180r12r2e(
                subdomains.CONSTRUCTION_K7_ROUTE_COMPONENT_CHAIN_RECEIPT_V180R12R2E_DOMAIN,
                payload,
            )
        ),
    }
    if set(document) != _ROUTE_COMPONENT_RECEIPT_FIELDS:
        raise AssertionError("V180r12r2 route-component receipt schema changed")
    return document, vector


def _assert_global_counter_record_uniqueness(
    vectors: Sequence[WorkVectorV1],
) -> None:
    record_ids = [
        record.record_id
        for vector in vectors
        for record in vector.records
    ]
    if not (
        len(record_ids) == ROUTE_COMPONENT_COUNTER_RECORD_COUNT
        and len(set(record_ids)) == ROUTE_COMPONENT_COUNTER_RECORD_COUNT
    ):
        _fail("twelve route components do not contain 3228 unique CounterRecords")


def _original_shared_receipt_ids(
    group: _VerifiedGroup,
    terminal_code: TerminalCode,
) -> tuple[str, ...]:
    document = group.terminal
    if terminal_code is TerminalCode.FULL_GROUND_FALLBACK:
        values = document["source_occurrence_shared_resource_receipt_ids"]
    elif group.source_kind == "V180R8_FRESH_CACHED_EXACT":
        values = document["source_occurrence_shared_resource_receipt_ids"]
    elif group.source_kind == "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN":
        row = next(
            item
            for item in document["terminal_rows"]
            if item["terminal_code"] == terminal_code.value
        )
        values = row["source_occurrence_shared_resource_receipt_ids"]
    else:
        values = document["source_occurrence_shared_resource_receipt_ids"]
    if not (
        type(values) is list
        and len(values) in {0, 9}
        and len(values) == len(set(values))
        and all(type(value) is str and len(value) == 64 for value in values)
    ):
        _fail("source occurrence shared-resource identities changed")
    return tuple(values)


def _terminal_shared_receipt_set(
    *,
    terminal_code: TerminalCode,
    source_receipt_id: str,
    source_receipt_ids: Sequence[str],
    vectors: Sequence[WorkVectorV1],
    aggregation_protocol_id: str,
    execution_authorization_id: str,
) -> dict[str, Any]:
    registry = registry_v9.official_counter_registry_v9()
    receipts: list[dict[str, Any]] = []
    for path in SHARED_RESOURCE_PATHS:
        values = [vector.values[path] for vector in vectors]
        reducer = registry.by_path[path].reducer
        value = max(values) if reducer is ReducerEnum.MAX else sum(values)
        payload = {
            "schema": "acfqp.terminal_shared_resource_receipt.v180r12r2",
            "aggregation_protocol_id": aggregation_protocol_id,
            "execution_authorization_id": execution_authorization_id,
            "terminal_code": terminal_code.value,
            "source_receipt_id": source_receipt_id,
            "path": path,
            "reducer": reducer.value,
            "value": value,
            "source_route_component_values": [
                {
                    "work_vector_id": vector.work_vector_id,
                    "value": vector.values[path],
                }
                for vector in vectors
            ],
            "source_occurrence_shared_resource_receipt_ids": list(
                source_receipt_ids
            ),
            "source_occurrence_shared_resource_receipt_count": len(
                SHARED_RESOURCE_PATHS
            ),
            "source_occurrence_shared_resource_receipt_ids_embedded": (
                len(source_receipt_ids) == len(SHARED_RESOURCE_PATHS)
            ),
            "independent_source_verifier_replayed_nine_receipts": True,
            "native_zero_observed": value == 0,
            "occurrence_shared_resource_receipt": True,
            "campaign_scope_resource_receipt": False,
            "construction_axis_receipt": False,
        }
        receipt = {
            **payload,
            "terminal_shared_resource_receipt_id": (
                subdomains.extension_content_id_v180r12r2e(
                    subdomains.CONSTRUCTION_K7_TERMINAL_SHARED_RECEIPT_V180R12R2E_DOMAIN,
                    payload,
                )
            ),
        }
        if set(receipt) != _TERMINAL_SHARED_RECEIPT_FIELDS:
            raise AssertionError("V180r12r2 terminal shared receipt changed")
        receipts.append(receipt)
    payload = {
        "schema": "acfqp.terminal_shared_resource_receipt_set.v180r12r2",
        "aggregation_protocol_id": aggregation_protocol_id,
        "execution_authorization_id": execution_authorization_id,
        "terminal_code": terminal_code.value,
        "source_receipt_id": source_receipt_id,
        "ordered_paths": list(SHARED_RESOURCE_PATHS),
        "receipts": receipts,
        "terminal_shared_resource_receipt_ids": [
            row["terminal_shared_resource_receipt_id"] for row in receipts
        ],
        "receipt_count": len(receipts),
        "all_nine_paths_present": True,
        "missing_path_inferred_zero": False,
    }
    document = {
        **payload,
        "terminal_shared_resource_receipt_set_id": (
            subdomains.extension_content_id_v180r12r2e(
                subdomains.CONSTRUCTION_K7_TERMINAL_RECEIPT_SET_V180R12R2E_DOMAIN,
                payload,
            )
        ),
    }
    if set(document) != _TERMINAL_RECEIPT_SET_FIELDS:
        raise AssertionError("V180r12r2 terminal receipt set schema changed")
    return document


def _terminal_receipt(
    *,
    component_receipts: Sequence[Mapping[str, Any]],
    group: _VerifiedGroup,
    source_receipt_id: str,
    terminal_code: TerminalCode,
    terminal_id: str,
    terminal_byte_count: int,
    terminal_sha256: str,
    shared_receipt_set_id: str,
    aggregation_protocol_id: str,
    execution_authorization_id: str,
) -> dict[str, Any]:
    representative = next(
        (
            row
            for row in component_receipts
            if row["route_kind"] == "DIRECT_FALLBACK"
        ),
        component_receipts[0],
    )
    payload = {
        "schema": "acfqp.ten_terminal_chain_receipt.v180r12r2",
        "aggregation_protocol_id": aggregation_protocol_id,
        "execution_authorization_id": execution_authorization_id,
        "terminal_code": terminal_code.value,
        "path_family": _PATH_FAMILY[terminal_code],
        "source_receipt_id": source_receipt_id,
        "source_verification_id": group.verification_id,
        "source_terminal_bundle_id": terminal_id,
        "source_terminal_byte_count": terminal_byte_count,
        "source_terminal_sha256": terminal_sha256,
        "route_component_chain_receipt_ids": [
            row["route_component_chain_receipt_id"] for row in component_receipts
        ],
        "route_component_count": len(component_receipts),
        "representative_route_component_chain_receipt_id": representative[
            "route_component_chain_receipt_id"
        ],
        "ten_terminal_representative_counter_record_count": (
            COUNTER_RECORDS_PER_V9_CHAIN
        ),
        "all_route_component_counter_record_count": sum(
            row["counter_record_count"] for row in component_receipts
        ),
        "terminal_shared_resource_receipt_set_id": shared_receipt_set_id,
        "occurrence_shared_resource_receipt_count": len(SHARED_RESOURCE_PATHS),
        "independent_source_verifier_replayed_before_aggregation": True,
        "historical_summary_translation_used": False,
    }
    document = {
        **payload,
        "terminal_chain_receipt_id": subdomains.extension_content_id_v180r12r2e(
            subdomains.CONSTRUCTION_K7_TERMINAL_RECEIPT_V180R12R2E_DOMAIN,
            payload,
        ),
    }
    if set(document) != _TERMINAL_RECEIPT_FIELDS:
        raise AssertionError("V180r12r2 terminal receipt schema changed")
    return document


def _construction_axis_receipt(
    *,
    group: _VerifiedGroup,
    source_receipt_id: str,
    aggregation_protocol_id: str,
    execution_authorization_id: str,
) -> dict[str, Any]:
    reference = group.terminal.get("materialized_source_reference")
    if not (
        type(reference) is dict
        and set(reference) == _MATERIALIZED_SOURCE_REFERENCE_FIELDS
        and reference.get("one_time_construction_axis") is True
        and reference.get("charged_to_any_route_component") is False
        and type(reference.get("construction_work")) is dict
        and group.verification.get("construction_axis_replayed_separately") is True
        and group.verification.get(
            "construction_work_charged_to_any_route_component"
        )
        is False
    ):
        _fail("V180r7r1 construction-axis separation changed")
    work = reference["construction_work"]
    payload = {
        "schema": "acfqp.v180r7r1_construction_axis_receipt.v180r12r2",
        "aggregation_protocol_id": aggregation_protocol_id,
        "execution_authorization_id": execution_authorization_id,
        "source_receipt_id": source_receipt_id,
        "source_verification_id": group.verification_id,
        "source_terminal_bundle_id": group.terminal_id,
        "materialization_manifest_id": reference["materialization_manifest_id"],
        "materialized_source_tree_id": reference["materialized_source_tree_id"],
        "source_catalog_manifest_id": reference["source_catalog_manifest_id"],
        "source_closure_repair_id": reference["source_closure_repair_id"],
        "source_closure_id": reference["source_closure_id"],
        "materialized_source_module_count": reference[
            "materialized_source_module_count"
        ],
        "materialized_source_byte_count": reference["materialized_source_byte_count"],
        "construction_work": work,
        "construction_work_sha256": _sha256(canonical_json_bytes(work)),
        "one_time_construction_axis": True,
        "charged_to_any_route_component": False,
        "occurrence_route_counter_record_count": 0,
        "construction_axis_replayed_separately": True,
        "historical_summary_translation_used": False,
    }
    document = {
        **payload,
        "v180r7r1_construction_axis_receipt_id": (
            subdomains.extension_content_id_v180r12r2e(
                subdomains.CONSTRUCTION_K7_V180R7R1_CONSTRUCTION_AXIS_RECEIPT_V180R12R2E_DOMAIN,
                payload,
            )
        ),
    }
    if set(document) != _CONSTRUCTION_AXIS_RECEIPT_FIELDS:
        raise AssertionError("V180r12r2 construction-axis receipt schema changed")
    return document


def _all_receipts(
    groups: Sequence[_VerifiedGroup],
    *,
    aggregation_protocol_id: str,
    execution_authorization_id: str,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    source_receipts = [
        _source_receipt(
            group,
            aggregation_protocol_id=aggregation_protocol_id,
            execution_authorization_id=execution_authorization_id,
        )
        for group in groups
    ]
    components = _component_inputs(groups, source_receipts)
    component_pairs = [
        _route_component_receipt(
            component,
            aggregation_protocol_id=aggregation_protocol_id,
            execution_authorization_id=execution_authorization_id,
            global_component_ordinal=ordinal,
        )
        for ordinal, component in enumerate(components)
    ]
    component_receipts = [row[0] for row in component_pairs]
    vectors = [row[1] for row in component_pairs]
    _assert_global_counter_record_uniqueness(vectors)
    observed_components = tuple(
        (row["terminal_code"], row["route_kind"])
        for row in component_receipts
    )
    if not (
        observed_components == EXPECTED_ROUTE_COMPONENTS
        and len(component_receipts) == ROUTE_COMPONENT_CHAIN_COUNT
        and len(
            {
                row["route_component_chain_receipt_id"]
                for row in component_receipts
            }
        )
        == ROUTE_COMPONENT_CHAIN_COUNT
        and len({vector.work_vector_id for vector in vectors})
        == ROUTE_COMPONENT_CHAIN_COUNT
    ):
        _fail("twelve unique route-component chains changed")

    groups_by_code: dict[TerminalCode, _VerifiedGroup] = {}
    terminal_metadata: dict[TerminalCode, tuple[str, int, str]] = {}
    for group in groups:
        if group.source_kind == "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN":
            for row in group.terminal["terminal_rows"]:
                code = TerminalCode(row["terminal_code"])
                groups_by_code[code] = group
                terminal_metadata[code] = (
                    row["production_terminal_bundle_id"],
                    row["canonical_byte_count"],
                    row["canonical_sha256"],
                )
        else:
            code = TerminalCode(group.terminal["terminal_code"])
            groups_by_code[code] = group
            terminal_metadata[code] = (
                group.terminal_id,
                group.terminal_byte_count,
                group.terminal_sha256,
            )
    if set(groups_by_code) != set(TerminalCode):
        _fail("ten terminal source coverage changed")

    shared_receipt_sets: list[dict[str, Any]] = []
    terminal_receipts: list[dict[str, Any]] = []
    for code in TerminalCode:
        group = groups_by_code[code]
        source_receipt = next(
            row
            for row in source_receipts
            if row["source_kind"] == group.source_kind
        )
        selected = [
            (receipt, vector)
            for receipt, vector in zip(component_receipts, vectors, strict=True)
            if receipt["terminal_code"] == code.value
        ]
        original_ids = _original_shared_receipt_ids(group, code)
        shared_set = _terminal_shared_receipt_set(
            terminal_code=code,
            source_receipt_id=source_receipt["source_receipt_id"],
            source_receipt_ids=original_ids,
            vectors=[row[1] for row in selected],
            aggregation_protocol_id=aggregation_protocol_id,
            execution_authorization_id=execution_authorization_id,
        )
        shared_receipt_sets.append(shared_set)
        terminal_id, terminal_byte_count, terminal_sha256 = terminal_metadata[
            code
        ]
        terminal_receipts.append(
            _terminal_receipt(
                component_receipts=[row[0] for row in selected],
                group=group,
                source_receipt_id=source_receipt["source_receipt_id"],
                terminal_code=code,
                terminal_id=terminal_id,
                terminal_byte_count=terminal_byte_count,
                terminal_sha256=terminal_sha256,
                shared_receipt_set_id=shared_set[
                    "terminal_shared_resource_receipt_set_id"
                ],
                aggregation_protocol_id=aggregation_protocol_id,
                execution_authorization_id=execution_authorization_id,
            )
        )

    r7_group = next(
        row
        for row in groups
        if row.source_kind == "V180R7R1_FRESH_FULL_GROUND_FALLBACK"
    )
    r7_source_receipt = next(
        row
        for row in source_receipts
        if row["source_kind"] == r7_group.source_kind
    )
    construction_receipt = _construction_axis_receipt(
        group=r7_group,
        source_receipt_id=r7_source_receipt["source_receipt_id"],
        aggregation_protocol_id=aggregation_protocol_id,
        execution_authorization_id=execution_authorization_id,
    )
    if not (
        len(source_receipts) == SOURCE_GROUP_COUNT
        and len(terminal_receipts) == TERMINAL_RECEIPT_COUNT
        and len(shared_receipt_sets) == TERMINAL_RECEIPT_COUNT
        and sum(row["receipt_count"] for row in shared_receipt_sets)
        == OCCURRENCE_SHARED_RESOURCE_RECEIPT_COUNT
        and sum(
            row["ten_terminal_representative_counter_record_count"]
            for row in terminal_receipts
        )
        == TEN_TERMINAL_REPRESENTATIVE_COUNTER_RECORD_COUNT
        and sum(
            row["all_route_component_counter_record_count"]
            for row in terminal_receipts
        )
        == ROUTE_COMPONENT_COUNTER_RECORD_COUNT
    ):
        _fail("corrected receipt denominator changed")
    return (
        source_receipts,
        terminal_receipts,
        component_receipts,
        shared_receipt_sets,
        construction_receipt,
    )


def _subject_id(
    *,
    aggregation_protocol_id: str,
    execution_authorization_id: str,
    route_component_receipts: Sequence[Mapping[str, Any]],
) -> str:
    return _sha256(
        b"acfqp:v180r12r2:ten-terminal-aggregation\x00"
        + aggregation_protocol_id.encode("ascii")
        + b"\x00"
        + execution_authorization_id.encode("ascii")
        + b"\x00"
        + canonical_json_bytes(
            [
                row["route_component_chain_receipt_id"]
                for row in route_component_receipts
            ]
        )
    )


def _campaign_structural_row(path: str, quantity: int) -> dict[str, Any]:
    if path in _CAMPAIGN_OBLIGATION_QUANTITIES:
        semantics = "DECLARED_OBLIGATION_CARDINALITY"
        authority = "PRECOMMITTED_ORCHESTRATION_OBLIGATION"
    elif path == "io.read_bytes":
        semantics = "DERIVED_INPUT_BYTE_DENOMINATOR"
        authority = "DERIVED_FROM_FROZEN_RETAINED_INPUT_BYTES"
    elif path == "io.output_bytes":
        semantics = "DERIVED_OUTPUT_BYTE_DENOMINATOR"
        authority = "DERIVED_FROM_CANONICAL_AGGREGATE_BYTES"
    elif path == "memory.working_bytes_peak":
        semantics = "AUTHORIZATION_CAP_NOT_OBSERVED_PEAK"
        authority = "FROZEN_EXECUTION_AUTHORIZATION_CAP"
    elif path in _CAMPAIGN_ABSENCE_PATHS:
        semantics = "DECLARED_ABSENCE_OBLIGATION_NOT_NATIVE_ZERO"
        authority = "PRECOMMITTED_ABSENCE_OBLIGATION"
    else:  # pragma: no cover - local structural grammar exhaustiveness
        raise AssertionError("campaign structural path is not classified")
    return {
        "path": path,
        "declared_quantity": quantity,
        "quantity_semantics": semantics,
        "authority_class": authority,
        "actual_measurement_present": False,
        "counter_gate_eligible": False,
        "economics_gate_eligible": False,
    }


def _validate_campaign_structural_quantities(
    values: Mapping[str, int],
) -> dict[str, int]:
    if not (
        isinstance(values, Mapping)
        and set(values) == set(SHARED_RESOURCE_PATHS)
        and all(type(values[path]) is int and values[path] >= 0 for path in values)
    ):
        _fail("campaign structural quantities changed type or path denominator")
    quantities = {path: values[path] for path in SHARED_RESOURCE_PATHS}
    if not (
        all(
            quantities[path] == value
            for path, value in _CAMPAIGN_OBLIGATION_QUANTITIES.items()
        )
        and all(quantities[path] == 0 for path in _CAMPAIGN_ABSENCE_PATHS)
        and quantities["memory.working_bytes_peak"] == WORKING_BYTES_HARD_CAP
    ):
        _fail("campaign obligation, absence, or authorization cap changed")
    return quantities


def _independent_campaign_scope_structural_boundary_document(
    *,
    aggregation_protocol_id: str,
    execution_authorization_id: str,
    subject_id: str,
    source_receipt_ids: Sequence[str],
    values: Mapping[str, int],
) -> dict[str, Any]:
    """Rebuild nine non-authoritative obligations without producer helpers."""

    source_ids = tuple(sorted(source_receipt_ids))
    if not (
        type(aggregation_protocol_id) is str
        and len(aggregation_protocol_id) == 64
        and type(execution_authorization_id) is str
        and len(execution_authorization_id) == 64
        and type(subject_id) is str
        and len(subject_id) == 64
        and len(source_ids) == SOURCE_GROUP_COUNT
        and len(set(source_ids)) == SOURCE_GROUP_COUNT
        and all(type(value) is str and len(value) == 64 for value in source_ids)
    ):
        _fail("independent campaign structural context changed")
    quantities = _validate_campaign_structural_quantities(values)
    declarations = [
        _campaign_structural_row(path, quantities[path])
        for path in SHARED_RESOURCE_PATHS
    ]
    by_path = {row["path"]: row["declared_quantity"] for row in declarations}
    payload = {
        "schema": "acfqp.campaign_scope_structural_boundary.v180r12r2",
        "schema_version": _CAMPAIGN_SCHEMA_VERSION,
        "scope": _CAMPAIGN_SCOPE_KIND,
        "aggregation_protocol_id": aggregation_protocol_id,
        "execution_authorization_id": execution_authorization_id,
        "subject_id": subject_id,
        "source_receipt_ids": list(source_ids),
        "source_group_count": SOURCE_GROUP_COUNT,
        "structural_declarations": declarations,
        "structural_declaration_count": CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT,
        "actual_counter_record_count": CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT,
        "actual_work_vector_present": False,
        "actual_comparison_vector_present": False,
        "actual_projection_proof_present": False,
        "actual_native_zero_attestation_present": False,
        "occurrence_route_record_count": 0,
        "construction_axis_record_count": 0,
        "campaign_scope_authoritative_receipt_count": (
            CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT
        ),
        "authoritative_occurrence_receipt_count": (
            TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT
        ),
        "authoritative_receipt_total": (
            TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT
        ),
        "hash_invocation_obligation_count": by_path["common.hash_invocations"],
        "integrity_check_obligation_count": by_path["common.integrity_checks"],
        "protocol_check_obligation_count": by_path["common.protocol_checks"],
        "derived_input_byte_denominator": by_path["io.read_bytes"],
        "derived_output_byte_denominator": by_path["io.output_bytes"],
        "working_bytes_authorization_cap": by_path["memory.working_bytes_peak"],
        "working_bytes_peak_measurement_present": False,
        "zero_absence_obligation_count": len(_CAMPAIGN_ABSENCE_PATHS),
        "native_zero_claim_count": 0,
        "counter_gate_eligible": False,
        "economics_gate_eligible": False,
        "structural_boundary_only": True,
        "scientific_success_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "campaign_scope_structural_boundary_id": (
            subdomains.extension_content_id_v180r12r2e(
                subdomains.CONSTRUCTION_K7_CAMPAIGN_STRUCTURAL_BOUNDARY_V180R12R2E_DOMAIN,
                payload,
            )
        ),
    }


def _independently_verify_campaign_scope_structural_boundary_document(
    document: Mapping[str, Any],
) -> dict[str, Any]:
    if type(document) is not dict or set(document) != (
        _CAMPAIGN_STRUCTURAL_BOUNDARY_FIELDS
    ):
        _fail("campaign structural boundary field set changed")
    declarations = document.get("structural_declarations")
    if not (
        type(declarations) is list
        and len(declarations) == CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        and all(
            type(row) is dict and set(row) == _CAMPAIGN_STRUCTURAL_ROW_FIELDS
            for row in declarations
        )
        and [row["path"] for row in declarations] == list(SHARED_RESOURCE_PATHS)
        and all(
            type(row["declared_quantity"]) is int
            and row["declared_quantity"] >= 0
            for row in declarations
        )
    ):
        _fail("campaign structural obligation rows or denominator changed")
    expected = _independent_campaign_scope_structural_boundary_document(
        aggregation_protocol_id=document.get("aggregation_protocol_id"),
        execution_authorization_id=document.get("execution_authorization_id"),
        subject_id=document.get("subject_id"),
        source_receipt_ids=document.get("source_receipt_ids", ()),
        values={
            row["path"]: row["declared_quantity"] for row in declarations
        },
    )
    if document != expected or canonical_json_bytes(document) != canonical_json_bytes(
        expected
    ):
        _fail("campaign structural boundary changed under independent exact replay")
    return expected
def _reconstruct_aggregation_bytes(
    groups: Sequence[_VerifiedGroup],
    aggregation_protocol_id: str,
    execution_authorization_id: str,
) -> bytes:
    (
        source_receipts,
        terminal_receipts,
        route_component_receipts,
        terminal_shared_receipt_sets,
        construction_axis_receipt,
    ) = _all_receipts(
        groups,
        aggregation_protocol_id=aggregation_protocol_id,
        execution_authorization_id=execution_authorization_id,
    )
    source_receipt_ids = [row["source_receipt_id"] for row in source_receipts]
    subject_id = _subject_id(
        aggregation_protocol_id=aggregation_protocol_id,
        execution_authorization_id=execution_authorization_id,
        route_component_receipts=route_component_receipts,
    )
    structural_quantities = {
        "common.hash_invocations": 15,
        "common.integrity_checks": 10,
        "common.protocol_checks": 10,
        "io.mounted_bytes_peak": 0,
        "io.read_bytes": sum(
            group.terminal_byte_count + group.verification_byte_count
            for group in groups
        ),
        "io.staged_bytes": 0,
        "memory.working_bytes_peak": WORKING_BYTES_HARD_CAP,
        "process.launches": 0,
    }
    if set(structural_quantities) | {"io.output_bytes"} != set(
        SHARED_RESOURCE_PATHS
    ):
        raise AssertionError("V180r12r2 campaign structural paths changed")
    guess = 0
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        structural_boundary = (
            _independent_campaign_scope_structural_boundary_document(
                aggregation_protocol_id=aggregation_protocol_id,
                execution_authorization_id=execution_authorization_id,
                subject_id=subject_id,
                source_receipt_ids=sorted(source_receipt_ids),
                values={**structural_quantities, "io.output_bytes": guess},
            )
        )
        replayed_structural_boundary = (
            _independently_verify_campaign_scope_structural_boundary_document(
                structural_boundary
            )
        )
        if not (
            replayed_structural_boundary == structural_boundary
            and structural_boundary["structural_declaration_count"]
            == CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
            and structural_boundary["actual_counter_record_count"]
            == CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT
            and structural_boundary["actual_work_vector_present"] is False
            and structural_boundary["authoritative_receipt_total"]
            == TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT
            and structural_boundary["occurrence_route_record_count"] == 0
        ):
            _fail("campaign-scope structural boundary replay changed")
        payload = {
            "schema": "acfqp.ten_terminal_production_aggregation.v180r12r2",
            "aggregation_protocol_id": aggregation_protocol_id,
            "execution_authorization_id": execution_authorization_id,
            "ordered_terminal_codes": [code.value for code in TerminalCode],
            "terminal_code_count": TERMINAL_RECEIPT_COUNT,
            "ordered_route_components": [
                {"terminal_code": code, "route_kind": route_kind}
                for code, route_kind in EXPECTED_ROUTE_COMPONENTS
            ],
            "source_group_count": SOURCE_GROUP_COUNT,
            "source_verification_receipt_count": SOURCE_GROUP_COUNT,
            "source_verification_receipts": source_receipts,
            "terminal_receipt_count": TERMINAL_RECEIPT_COUNT,
            "terminal_receipts": terminal_receipts,
            "route_component_chain_receipt_count": ROUTE_COMPONENT_CHAIN_COUNT,
            "route_component_chain_receipts": route_component_receipts,
            "ten_terminal_representative_counter_record_count": (
                TEN_TERMINAL_REPRESENTATIVE_COUNTER_RECORD_COUNT
            ),
            "route_component_counter_record_count": (
                ROUTE_COMPONENT_COUNTER_RECORD_COUNT
            ),
            "v180r7r1_additional_counter_record_count": (
                V180R7R1_ADDITIONAL_COUNTER_RECORD_COUNT
            ),
            "terminal_shared_resource_receipt_sets": terminal_shared_receipt_sets,
            "occurrence_shared_resource_receipt_count": (
                OCCURRENCE_SHARED_RESOURCE_RECEIPT_COUNT
            ),
            "campaign_scope_structural_boundary": structural_boundary,
            "campaign_scope_structural_obligation_count": (
                CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
            ),
            "campaign_scope_actual_counter_record_count": (
                CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT
            ),
            "campaign_scope_actual_shared_resource_receipt_count": (
                CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT
            ),
            "campaign_scope_actual_work_vector_count": (
                CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT
            ),
            "campaign_scope_actual_comparison_vector_count": (
                CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT
            ),
            "campaign_scope_actual_projection_proof_count": (
                CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT
            ),
            "campaign_scope_actual_native_zero_attestation_count": (
                CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT
            ),
            "campaign_scope_authoritative_receipt_count": (
                CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT
            ),
            "total_authoritative_shared_resource_receipt_count": (
                TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT
            ),
            "v180r7r1_construction_axis_receipt": construction_axis_receipt,
            "v180r7r1_construction_axis_receipt_count": 1,
            "v180r7r1_construction_work_charged_to_route_components": False,
            "output_bytes_fixed_point": guess,
            "fixed_point_iteration": iteration,
            "all_five_source_independent_verifiers_replayed": True,
            "all_twelve_route_component_chains_present": True,
            "all_ten_occurrence_shared_resource_receipt_sets_present": True,
            "historical_summary_translation_used": False,
            "producer_bundle_independently_replayed": False,
            "route_component_counter_closure_status": "PENDING_INDEPENDENT_REPLAY",
            "COUNTER_COMPLETENESS_BLOCKER": COUNTER_COMPLETENESS_BLOCKER,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "SCALAR_CALIBRATION_GATE": "NOT_RUN",
            "BREAK_EVEN_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }
        document = {
            **payload,
            "production_aggregation_bundle_id": (
                domains.extension_content_id_v180r12r2(
                    domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R2_DOMAIN,
                    payload,
                )
            ),
        }
        if set(document) != _BUNDLE_FIELDS:
            raise AssertionError("V180r12r2 aggregation bundle schema changed")
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("V180r12r2 producer-free aggregate fixed point did not converge")


def _content_id_matches(
    document: Mapping[str, Any],
    identity_field: str,
    domain: str,
    *,
    subregistry: bool,
) -> bool:
    if type(document) is not dict:
        return False
    payload = dict(document)
    identity = payload.pop(identity_field, None)
    if subregistry:
        expected = subdomains.extension_content_id_v180r12r2e(domain, payload)
    else:
        expected = domains.extension_content_id_v180r12r2(domain, payload)
    return type(identity) is str and identity == expected


def _contains_key(value: Any, key: str) -> bool:
    if type(value) is dict:
        return key in value or any(_contains_key(item, key) for item in value.values())
    if type(value) is list:
        return any(_contains_key(item, key) for item in value)
    return False


def _assert_exact_aggregate_schema(
    document: Mapping[str, Any],
    *,
    aggregation_bytes: bytes,
    aggregation_protocol_id: str,
    execution_authorization_id: str,
    groups: Sequence[_VerifiedGroup],
) -> None:
    sources = document.get("source_verification_receipts")
    components = document.get("route_component_chain_receipts")
    terminals = document.get("terminal_receipts")
    shared_sets = document.get("terminal_shared_resource_receipt_sets")
    construction = document.get("v180r7r1_construction_axis_receipt")
    structural_boundary = document.get("campaign_scope_structural_boundary")
    if not (
        type(document) is dict
        and set(document) == _BUNDLE_FIELDS
        and document.get("schema")
        == "acfqp.ten_terminal_production_aggregation.v180r12r2"
        and document.get("aggregation_protocol_id") == aggregation_protocol_id
        and document.get("execution_authorization_id")
        == execution_authorization_id
        and _content_id_matches(
            document,
            "production_aggregation_bundle_id",
            domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R2_DOMAIN,
            subregistry=False,
        )
        and document.get("output_bytes_fixed_point") == len(aggregation_bytes)
        and type(document.get("fixed_point_iteration")) is int
        and 0 <= document["fixed_point_iteration"] < MAXIMUM_FIXED_POINT_ITERATIONS
        and document.get("ordered_terminal_codes")
        == [code.value for code in TerminalCode]
        and document.get("ordered_route_components")
        == [
            {"terminal_code": code, "route_kind": route_kind}
            for code, route_kind in EXPECTED_ROUTE_COMPONENTS
        ]
        and type(sources) is list
        and len(sources) == SOURCE_GROUP_COUNT
        and type(components) is list
        and len(components) == ROUTE_COMPONENT_CHAIN_COUNT
        and type(terminals) is list
        and len(terminals) == TERMINAL_RECEIPT_COUNT
        and type(shared_sets) is list
        and len(shared_sets) == TERMINAL_RECEIPT_COUNT
        and type(construction) is dict
        and type(structural_boundary) is dict
    ):
        _fail("aggregate top-level schema, identity, or ordering changed")

    expected_source_rows = {
        group.source_kind: group for group in groups
    }
    if not all(
        set(row) == _SOURCE_RECEIPT_FIELDS
        and row.get("source_kind") in expected_source_rows
        and row.get("aggregation_protocol_id") == aggregation_protocol_id
        and row.get("execution_authorization_id") == execution_authorization_id
        and _content_id_matches(
            row,
            "source_receipt_id",
            subdomains.CONSTRUCTION_K7_SOURCE_RECEIPT_V180R12R2E_DOMAIN,
            subregistry=True,
        )
        for row in sources
    ):
        _fail("source receipt schema or identity changed")

    if not all(
        set(row) == _ROUTE_COMPONENT_RECEIPT_FIELDS
        and row.get("aggregation_protocol_id") == aggregation_protocol_id
        and row.get("execution_authorization_id") == execution_authorization_id
        and row.get("component_ordinal") == ordinal
        and row.get("counter_record_count") == COUNTER_RECORDS_PER_V9_CHAIN
        and row.get("independent_route_component") is True
        and row.get("historical_summary_translation_used") is False
        and _content_id_matches(
            row,
            "route_component_chain_receipt_id",
            subdomains.CONSTRUCTION_K7_ROUTE_COMPONENT_CHAIN_RECEIPT_V180R12R2E_DOMAIN,
            subregistry=True,
        )
        for ordinal, row in enumerate(components)
    ):
        _fail("route-component receipt schema, ordering, or identity changed")
    if [
        (row["terminal_code"], row["route_kind"]) for row in components
    ] != list(EXPECTED_ROUTE_COMPONENTS):
        _fail("route-component terminal or route ordering changed")

    terminal_ids = {
        row["terminal_code"]: row["terminal_chain_receipt_id"] for row in terminals
    }
    if not (
        len(terminal_ids) == TERMINAL_RECEIPT_COUNT
        and set(terminal_ids) == {code.value for code in TerminalCode}
        and all(
            set(row) == _TERMINAL_RECEIPT_FIELDS
            and row.get("aggregation_protocol_id") == aggregation_protocol_id
            and row.get("execution_authorization_id") == execution_authorization_id
            and row.get("occurrence_shared_resource_receipt_count") == 9
            and row.get("ten_terminal_representative_counter_record_count")
            == COUNTER_RECORDS_PER_V9_CHAIN
            and row.get("historical_summary_translation_used") is False
            and _content_id_matches(
                row,
                "terminal_chain_receipt_id",
                subdomains.CONSTRUCTION_K7_TERMINAL_RECEIPT_V180R12R2E_DOMAIN,
                subregistry=True,
            )
            for row in terminals
        )
    ):
        _fail("terminal receipt schema, denominator, or identity changed")

    terminal_shared_rows = 0
    for receipt_set in shared_sets:
        receipts = receipt_set.get("receipts") if type(receipt_set) is dict else None
        if not (
            type(receipt_set) is dict
            and set(receipt_set) == _TERMINAL_RECEIPT_SET_FIELDS
            and receipt_set.get("aggregation_protocol_id") == aggregation_protocol_id
            and receipt_set.get("execution_authorization_id")
            == execution_authorization_id
            and receipt_set.get("ordered_paths") == list(SHARED_RESOURCE_PATHS)
            and receipt_set.get("receipt_count") == 9
            and receipt_set.get("all_nine_paths_present") is True
            and receipt_set.get("missing_path_inferred_zero") is False
            and type(receipts) is list
            and len(receipts) == 9
            and receipt_set.get("terminal_shared_resource_receipt_ids")
            == [row.get("terminal_shared_resource_receipt_id") for row in receipts]
            and _content_id_matches(
                receipt_set,
                "terminal_shared_resource_receipt_set_id",
                subdomains.CONSTRUCTION_K7_TERMINAL_RECEIPT_SET_V180R12R2E_DOMAIN,
                subregistry=True,
            )
        ):
            _fail("terminal shared-resource receipt-set schema changed")
        for row in receipts:
            if not (
                type(row) is dict
                and set(row) == _TERMINAL_SHARED_RECEIPT_FIELDS
                and row.get("aggregation_protocol_id") == aggregation_protocol_id
                and row.get("execution_authorization_id")
                == execution_authorization_id
                and row.get("source_occurrence_shared_resource_receipt_count")
                == 9
                and row.get("occurrence_shared_resource_receipt") is True
                and row.get("campaign_scope_resource_receipt") is False
                and row.get("construction_axis_receipt") is False
                and _content_id_matches(
                    row,
                    "terminal_shared_resource_receipt_id",
                    subdomains.CONSTRUCTION_K7_TERMINAL_SHARED_RECEIPT_V180R12R2E_DOMAIN,
                    subregistry=True,
                )
            ):
                _fail("terminal shared-resource receipt schema changed")
        terminal_shared_rows += len(receipts)
    if terminal_shared_rows != OCCURRENCE_SHARED_RESOURCE_RECEIPT_COUNT:
        _fail("terminal shared-resource receipt denominator changed")

    if not (
        set(construction) == _CONSTRUCTION_AXIS_RECEIPT_FIELDS
        and construction.get("aggregation_protocol_id") == aggregation_protocol_id
        and construction.get("execution_authorization_id")
        == execution_authorization_id
        and construction.get("one_time_construction_axis") is True
        and construction.get("charged_to_any_route_component") is False
        and construction.get("occurrence_route_counter_record_count") == 0
        and construction.get("construction_axis_replayed_separately") is True
        and construction.get("historical_summary_translation_used") is False
        and _content_id_matches(
            construction,
            "v180r7r1_construction_axis_receipt_id",
            subdomains.CONSTRUCTION_K7_V180R7R1_CONSTRUCTION_AXIS_RECEIPT_V180R12R2E_DOMAIN,
            subregistry=True,
        )
    ):
        _fail("V180r7r1 construction-axis receipt changed")
    replayed_structural_boundary = (
        _independently_verify_campaign_scope_structural_boundary_document(
            structural_boundary
        )
    )
    if not (
        replayed_structural_boundary == structural_boundary
        and structural_boundary.get("structural_declaration_count") == 9
        and structural_boundary.get("actual_counter_record_count")
        == CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT
        and structural_boundary.get("actual_work_vector_present") is False
        and structural_boundary.get("actual_comparison_vector_present") is False
        and structural_boundary.get("actual_projection_proof_present") is False
        and structural_boundary.get("actual_native_zero_attestation_present")
        is False
        and structural_boundary.get("authoritative_receipt_total") == 90
        and structural_boundary.get("native_zero_claim_count") == 0
        and structural_boundary.get("working_bytes_peak_measurement_present")
        is False
        and not _contains_key(structural_boundary, "route_kind")
    ):
        _fail("campaign structural boundary gained actual authority")

    if not (
        document.get("source_group_count") == SOURCE_GROUP_COUNT
        and document.get("source_verification_receipt_count") == SOURCE_GROUP_COUNT
        and document.get("terminal_code_count") == TERMINAL_RECEIPT_COUNT
        and document.get("terminal_receipt_count") == TERMINAL_RECEIPT_COUNT
        and document.get("route_component_chain_receipt_count")
        == ROUTE_COMPONENT_CHAIN_COUNT
        and document.get("ten_terminal_representative_counter_record_count")
        == TEN_TERMINAL_REPRESENTATIVE_COUNTER_RECORD_COUNT
        and document.get("route_component_counter_record_count")
        == ROUTE_COMPONENT_COUNTER_RECORD_COUNT
        and document.get("v180r7r1_additional_counter_record_count")
        == V180R7R1_ADDITIONAL_COUNTER_RECORD_COUNT
        and document.get("occurrence_shared_resource_receipt_count")
        == OCCURRENCE_SHARED_RESOURCE_RECEIPT_COUNT
        and document.get("campaign_scope_structural_obligation_count")
        == CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        and document.get("campaign_scope_actual_counter_record_count")
        == CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT
        and document.get("campaign_scope_actual_shared_resource_receipt_count")
        == CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT
        and document.get("campaign_scope_actual_work_vector_count")
        == CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT
        and document.get("campaign_scope_actual_comparison_vector_count")
        == CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT
        and document.get("campaign_scope_actual_projection_proof_count")
        == CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT
        and document.get("campaign_scope_actual_native_zero_attestation_count")
        == CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT
        and document.get("campaign_scope_authoritative_receipt_count")
        == CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT
        and document.get("total_authoritative_shared_resource_receipt_count")
        == TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT
        and document.get("v180r7r1_construction_axis_receipt_count") == 1
        and document.get("v180r7r1_construction_work_charged_to_route_components")
        is False
        and document.get("all_five_source_independent_verifiers_replayed") is True
        and document.get("all_twelve_route_component_chains_present") is True
        and document.get("all_ten_occurrence_shared_resource_receipt_sets_present")
        is True
        and document.get("historical_summary_translation_used") is False
        and document.get("producer_bundle_independently_replayed") is False
        and document.get("route_component_counter_closure_status")
        == "PENDING_INDEPENDENT_REPLAY"
        and document.get("COUNTER_COMPLETENESS_BLOCKER")
        == COUNTER_COMPLETENESS_BLOCKER
        and document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and document.get("SCALAR_CALIBRATION_GATE") == "NOT_RUN"
        and document.get("BREAK_EVEN_GATE") == "NOT_RUN"
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and document.get("official_execution_allowed") is False
    ):
        _fail("aggregate accounting denominator or claim lock changed")


def verify_ten_terminal_aggregation_core_no_output_v180r12r2(
    aggregation_bytes: bytes,
    repository_root: Path,
    *,
    aggregation_protocol_id: str,
    execution_authorization_id: str,
    protocol_document: Mapping[str, Any],
    authorization_document: Mapping[str, Any],
) -> dict[str, Any]:
    """Run the full producer-free verifier lifecycle without writing output."""

    if type(aggregation_bytes) is not bytes:
        _fail("V180r12r2 aggregation must be canonical bytes")
    groups = _capture_verified_groups(repository_root, replay_semantics=True)
    _assert_input_contract(protocol_document, authorization_document, groups)
    expected = _reconstruct_aggregation_bytes(
        groups,
        aggregation_protocol_id,
        execution_authorization_id,
    )
    if expected != aggregation_bytes:
        _fail("ten-terminal aggregate did not reproduce without producer import")
    # Do not retain a parsed candidate while the producer-free reconstruction
    # is live.  The exact byte comparison is intentionally the first join.
    del expected
    candidate = _object(aggregation_bytes, "V180r12r2 aggregation")
    _assert_exact_aggregate_schema(
        candidate,
        aggregation_bytes=aggregation_bytes,
        aggregation_protocol_id=aggregation_protocol_id,
        execution_authorization_id=execution_authorization_id,
        groups=groups,
    )
    payload = {
        "schema": "acfqp.ten_terminal_aggregation_verification.v180r12r2",
        "aggregation_protocol_id": aggregation_protocol_id,
        "execution_authorization_id": execution_authorization_id,
        "production_aggregation_bundle_id": candidate[
            "production_aggregation_bundle_id"
        ],
        "aggregation_byte_count": len(aggregation_bytes),
        "aggregation_sha256": _sha256(aggregation_bytes),
        "source_group_count": SOURCE_GROUP_COUNT,
        "source_verification_receipt_count": SOURCE_GROUP_COUNT,
        "terminal_code_count": TERMINAL_RECEIPT_COUNT,
        "terminal_receipt_count": TERMINAL_RECEIPT_COUNT,
        "route_component_chain_receipt_count": ROUTE_COMPONENT_CHAIN_COUNT,
        "ten_terminal_representative_counter_record_count": (
            TEN_TERMINAL_REPRESENTATIVE_COUNTER_RECORD_COUNT
        ),
        "route_component_counter_record_count": ROUTE_COMPONENT_COUNTER_RECORD_COUNT,
        "v180r7r1_additional_counter_record_count": (
            V180R7R1_ADDITIONAL_COUNTER_RECORD_COUNT
        ),
        "occurrence_shared_resource_receipt_count": (
            OCCURRENCE_SHARED_RESOURCE_RECEIPT_COUNT
        ),
        "campaign_scope_structural_obligation_count": (
            CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        ),
        "campaign_scope_actual_counter_record_count": (
            CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT
        ),
        "campaign_scope_actual_shared_resource_receipt_count": (
            CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT
        ),
        "campaign_scope_actual_work_vector_count": (
            CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT
        ),
        "campaign_scope_actual_comparison_vector_count": (
            CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT
        ),
        "campaign_scope_actual_projection_proof_count": (
            CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT
        ),
        "campaign_scope_actual_native_zero_attestation_count": (
            CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT
        ),
        "campaign_scope_authoritative_receipt_count": (
            CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT
        ),
        "total_authoritative_shared_resource_receipt_count": (
            TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT
        ),
        "v180r7r1_construction_axis_receipt_count": 1,
        "all_five_source_independent_verifiers_replayed": True,
        "all_twelve_route_component_chains_replayed": True,
        "all_ten_terminal_receipts_replayed": True,
        "all_ninety_terminal_shared_resource_receipts_replayed": True,
        "campaign_scope_structural_boundary_replayed": True,
        "all_route_component_counter_records_replayed": True,
        "all_route_component_work_vectors_replayed": True,
        "all_route_component_comparison_vectors_rederived": True,
        "all_route_component_actual_projection_proofs_replayed": True,
        "all_route_component_native_zero_attestations_replayed": True,
        "terminal_receipt_denominators_replayed": True,
        "campaign_scope_actual_measurement_ledger_present": False,
        "campaign_scope_has_no_route_kind": True,
        "v180r7r1_construction_axis_replayed_separately": True,
        "v180r7r1_construction_work_charged_to_route_components": False,
        "producer_aggregate_exact_bytes_reconstructed": True,
        "producer_module_imported": False,
        "historical_summary_translation_used": False,
        "route_component_counter_closure_status": "PASS",
        "COUNTER_COMPLETENESS_BLOCKER": COUNTER_COMPLETENESS_BLOCKER,
        "v180r12r3_actual_campaign_measurement_ledger_required": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "verification_id": domains.extension_content_id_v180r12r2(
            domains.CONSTRUCTION_K7_VERIFICATION_V180R12R2_DOMAIN,
            payload,
        ),
    }


def verify_ten_terminal_aggregation_independently_v180r12r2(
    aggregation_bytes: bytes,
    repository_root: Path,
) -> dict[str, Any]:
    """Reconstruct and verify the aggregate without importing its producer."""

    (
        aggregation_protocol_id,
        execution_authorization_id,
        protocol_document,
        authorization_document,
    ) = _frozen_contract()
    return verify_ten_terminal_aggregation_core_no_output_v180r12r2(
        aggregation_bytes,
        repository_root,
        aggregation_protocol_id=aggregation_protocol_id,
        execution_authorization_id=execution_authorization_id,
        protocol_document=protocol_document,
        authorization_document=authorization_document,
    )


__all__ = (
    "ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error",
    "verify_ten_terminal_aggregation_core_no_output_v180r12r2",
    "verify_ten_terminal_aggregation_independently_v180r12r2",
)
