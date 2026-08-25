"""Finalize the corrected V180r12r2 ten-terminal aggregation.

The finalizer consumes five already-retained, independently verified evidence
groups.  It keeps ten terminal receipts distinct from twelve route-component
accounting chains, because the V180r7r1 fallback terminal has three independent
route components.  Its one-time materialization work remains a separate
construction axis and is never charged to an occurrence route.  The nine
aggregation-orchestration quantities are retained only as structural
declarations: no actual campaign measurement ledger exists, so they cannot
become CounterRecords, a WorkVector, or workload-economics evidence.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
import gc
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_domain_registry_extension_v180r12r2 as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r2e as subdomains
from acfqp import (
    construction_k7_cached_exact_infeasibility_production_terminal_independent_verifier_v180r8
    as r8_verifier,
)
from acfqp import (
    construction_k7_full_ground_fallback_production_evidence_freeze_v180r7r1
    as r7r1_evidence,
)
from acfqp import (
    construction_k7_remaining_terminal_evidence_freeze_v180r9
    as r9_evidence,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_campaign_accounting_v180r12r2
    as campaign_accounting,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2
    as authorization,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_protocol_v180r12r2
    as protocol,
)
from acfqp import (
    construction_k7_v34_retained_recovery_evidence_freeze_v180r11
    as r11_evidence,
)
from acfqp import (
    construction_k7_v34_retained_recovery_authorization_v180r11
    as r11_authorization,
)
from acfqp import (
    construction_k7_v34_retained_recovery_independent_verifier_v180r11
    as r11_verifier,
)
from acfqp import (
    construction_k7_v36_retained_recovery_evidence_freeze_v180r10r1
    as r10r1_evidence,
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
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    verify_actual_projection_v1,
)
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
COUNTER_COMPLETENESS_BLOCKER = (
    "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
)
ROUTE_COMPONENT_COUNTER_CLOSURE_STATUS = "PENDING_INDEPENDENT_REPLAY"
TRANSIENT_HEAP_RELEASE_PHASE_COUNT = 7
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

_INPUT_ROLES = (
    (
        "V180R11_RETAINED_V34_FINISH_FORWARD",
        ".tmp/exact-freeze/v180r11_v34_retained_terminal.json",
        ".tmp/exact-freeze/v180r11_v34_retained_verification.json",
    ),
    (
        "V180R10R1_RETAINED_V36_FINISH_FORWARD",
        ".tmp/exact-freeze/v180r10r1_v36_retained_terminal.json",
        ".tmp/exact-freeze/v180r10r1_v36_retained_verification.json",
    ),
    (
        "V180R7R1_FRESH_FULL_GROUND_FALLBACK",
        (
            ".tmp/exact-freeze/"
            "v180r7r1_full_ground_fallback_terminal_bundle.json"
        ),
        ".tmp/exact-freeze/v180r7r1_full_ground_fallback_verification.json",
    ),
    (
        "V180R8_FRESH_CACHED_EXACT",
        ".tmp/v180r8-cached-exact-production/TERMINAL.json",
        ".tmp/v180r8-cached-exact-verification/VERIFICATION.json",
    ),
    (
        "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
        ".tmp/exact-freeze/v180r9_remaining_terminal_production/TERMINAL.json",
        (
            ".tmp/exact-freeze/"
            "v180r9_remaining_terminal_production/VERIFICATION.json"
        ),
    ),
)

EXPECTED_ROUTE_COMPONENTS = (
    (TerminalCode.ABSTRACT_CERTIFIED.value, "ABSTRACT_ONLY_CERTIFICATE"),
    (TerminalCode.LOCAL_GROUND_RECOVERY.value, "LOCAL_ATTEMPT"),
    (TerminalCode.FULL_GROUND_FALLBACK.value, "ABSTRACT_FAILED_PREFIX"),
    (TerminalCode.FULL_GROUND_FALLBACK.value, "LOCAL_ATTEMPT"),
    (TerminalCode.FULL_GROUND_FALLBACK.value, "DIRECT_FALLBACK"),
    (TerminalCode.CACHED_EXACT_INFEASIBLE.value, "ABSTRACT_FAILED_PREFIX"),
    (TerminalCode.FULL_GROUND_EXACT_INFEASIBLE.value, "DIRECT_FALLBACK"),
    (TerminalCode.INTEGRITY_FAILURE.value, "ABSTRACT_FAILED_PREFIX"),
    (TerminalCode.PROTOCOL_FAILURE.value, "ABSTRACT_FAILED_PREFIX"),
    (TerminalCode.REBUILD_REQUIRED.value, "REBUILD"),
    (TerminalCode.FALLBACK_CAP_EXHAUSTED.value, "DIRECT_FALLBACK"),
    (TerminalCode.ATTEMPT_BUDGET_EXHAUSTED.value, "ABSTRACT_FAILED_PREFIX"),
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
    "historical_summary_translation_used",
    "execution_authorization_id",
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
_CAMPAIGN_STRUCTURAL_DECLARATION_FIELDS = {
    "actual_measurement_present",
    "authority_class",
    "counter_gate_eligible",
    "declared_quantity",
    "economics_gate_eligible",
    "path",
    "quantity_semantics",
}
_CAMPAIGN_STRUCTURAL_BOUNDARY_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "actual_comparison_vector_present",
    "actual_counter_record_count",
    "actual_native_zero_attestation_present",
    "actual_projection_proof_present",
    "actual_work_vector_present",
    "aggregation_protocol_id",
    "authoritative_occurrence_receipt_count",
    "authoritative_receipt_total",
    "campaign_scope_authoritative_receipt_count",
    "campaign_scope_structural_boundary_id",
    "construction_axis_record_count",
    "counter_gate_eligible",
    "derived_input_byte_denominator",
    "derived_output_byte_denominator",
    "economics_gate_eligible",
    "execution_authorization_id",
    "hash_invocation_obligation_count",
    "integrity_check_obligation_count",
    "native_zero_claim_count",
    "occurrence_route_record_count",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "protocol_check_obligation_count",
    "schema",
    "schema_version",
    "scientific_success_claimed",
    "scope",
    "source_group_count",
    "source_receipt_ids",
    "structural_boundary_only",
    "structural_declaration_count",
    "structural_declarations",
    "subject_id",
    "working_bytes_authorization_cap",
    "working_bytes_peak_measurement_present",
    "zero_absence_obligation_count",
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


class ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error(
    RuntimeError
):
    """One retained source, accounting chain, or exact output schema changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error(message)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _release_transient_verifier_heap() -> None:
    """Return dead verifier arenas before replaying the next retained group."""

    gc.collect()
    try:
        trim = ctypes.CDLL(None).malloc_trim
    except (AttributeError, OSError) as error:
        raise ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error(
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
        raise ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error(
            f"{label} is not one canonical object"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _read(
    root: Path,
    relative_path: str,
    label: str,
) -> tuple[bytes, dict[str, Any]]:
    try:
        raw = source_runtime_v2._read_regular_symlink_free(  # noqa: SLF001
            root / relative_path
        )
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error(
            f"{label} is absent, linked, or nonregular"
        ) from error
    return raw, _object(raw, label)


def _read_bytes(root: Path, relative_path: str, label: str) -> bytes:
    try:
        return source_runtime_v2._read_regular_symlink_free(  # noqa: SLF001
            root / relative_path
        )
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error(
            f"{label} is absent, linked, or nonregular"
        ) from error


_VERIFICATION_EXPLICIT_NULL_SCALAR_FIELDS_SOURCE_KINDS = frozenset(
    {"V180R9_FRESH_SIX_TERMINAL_CAMPAIGN"}
)
_VERIFICATION_ABSENT_SCALAR_FIELDS_SOURCE_KINDS = frozenset(
    {
        "V180R11_RETAINED_V34_FINISH_FORWARD",
        "V180R10R1_RETAINED_V36_FINISH_FORWARD",
        "V180R7R1_FRESH_FULL_GROUND_FALLBACK",
        "V180R8_FRESH_CACHED_EXACT",
    }
)


def _claim_locks(
    document: Mapping[str, Any],
    label: str,
    *,
    scalar_field_policy: str = "EXPLICIT_NULL",
) -> None:
    if scalar_field_policy == "EXPLICIT_NULL":
        scalar_fields_locked = (
            "official_scalar_cost" in document
            and document["official_scalar_cost"] is None
            and "official_N_break_even" in document
            and document["official_N_break_even"] is None
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
    document: Mapping[str, Any],
    source_kind: str,
) -> None:
    all_source_kinds = (
        _VERIFICATION_EXPLICIT_NULL_SCALAR_FIELDS_SOURCE_KINDS
        | _VERIFICATION_ABSENT_SCALAR_FIELDS_SOURCE_KINDS
    )
    if source_kind not in all_source_kinds:
        _fail("retained verification source kind changed")
    _claim_locks(
        document,
        f"{source_kind} verification",
        scalar_field_policy=(
            "EXPLICIT_NULL"
            if source_kind
            in _VERIFICATION_EXPLICIT_NULL_SCALAR_FIELDS_SOURCE_KINDS
            else "ABSENT"
        ),
    )


def _assert_campaign_scope_structural_boundary(
    document: Mapping[str, Any],
) -> None:
    declarations = document.get("structural_declarations")
    if not (
        type(document) is dict
        and set(document) == _CAMPAIGN_STRUCTURAL_BOUNDARY_FIELDS
        and document.get("schema")
        == "acfqp.campaign_scope_structural_boundary.v180r12r2"
        and type(declarations) is list
        and len(declarations) == CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        and all(
            type(row) is dict
            and set(row) == _CAMPAIGN_STRUCTURAL_DECLARATION_FIELDS
            and row.get("actual_measurement_present") is False
            and row.get("counter_gate_eligible") is False
            and row.get("economics_gate_eligible") is False
            for row in declarations
        )
        and document.get("structural_declaration_count")
        == CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        and document.get("actual_counter_record_count")
        == CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT
        and document.get("campaign_scope_authoritative_receipt_count")
        == CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT
        and document.get("authoritative_occurrence_receipt_count")
        == OCCURRENCE_SHARED_RESOURCE_RECEIPT_COUNT
        and document.get("authoritative_receipt_total")
        == TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT
        and document.get("actual_work_vector_present") is False
        and document.get("actual_comparison_vector_present") is False
        and document.get("actual_projection_proof_present") is False
        and document.get("actual_native_zero_attestation_present") is False
        and document.get("working_bytes_peak_measurement_present") is False
        and document.get("native_zero_claim_count") == 0
        and document.get("counter_gate_eligible") is False
        and document.get("economics_gate_eligible") is False
        and document.get("structural_boundary_only") is True
        and document.get("scientific_success_claimed") is False
        and document.get("occurrence_route_record_count") == 0
        and document.get("construction_axis_record_count") == 0
        and document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and document.get("official_execution_allowed") is False
    ):
        _fail("campaign-scope structural boundary replay changed")


@dataclass(frozen=True, slots=True)
class _VerifiedGroup:
    source_kind: str
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
_R9_PROJECTION_FIELDS = frozenset(
    {"projection_kind", "terminal_rows"}
)
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
    if type(receipt_set) is not dict:
        _fail("retained shared-resource receipt set changed")
    receipts = receipt_set.get("receipts")
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
    """Extract only fields consumed after a complete producer-free replay."""

    if source_kind in {
        "V180R11_RETAINED_V34_FINISH_FORWARD",
        "V180R10R1_RETAINED_V36_FINISH_FORWARD",
        "V180R8_FRESH_CACHED_EXACT",
    }:
        source_ids: list[str]
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
        projected_components: list[dict[str, Any]] = []
        for component in components:
            if type(component) is not dict:
                _fail("V180r7r1 route component changed")
            projected = {
                field: component.get(field)
                for field in _R7R1_COMPONENT_PROJECTION_FIELDS
            }
            if set(projected) != _R7R1_COMPONENT_PROJECTION_FIELDS:
                raise AssertionError("V180r7r1 component projection changed")
            projected_components.append(projected)
        source_ids = source_bundle.get("shared_resource_receipt_ids")
        if not (
            type(source_ids) is list
            and len(source_ids) == len(SHARED_RESOURCE_PATHS)
            and len(source_ids) == len(set(source_ids))
            and all(
                type(value) is str and len(value) == 64
                for value in source_ids
            )
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
        projected_rows: list[dict[str, Any]] = []
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


def _verified_group(
    *,
    source_kind: str,
    terminal_path: str,
    terminal_bytes: bytes,
    terminal: dict[str, Any],
    verification_path: str,
    verification_bytes: bytes,
    verification: dict[str, Any],
    terminal_id_field: str,
) -> _VerifiedGroup:
    terminal_id = terminal.get(terminal_id_field)
    verification_id = verification.get("verification_id")
    if not (
        type(terminal_id) is str
        and len(terminal_id) == 64
        and type(verification_id) is str
        and len(verification_id) == 64
        and canonical_json_bytes(verification) == verification_bytes
    ):
        _fail(f"{source_kind} retained identities changed")
    _claim_locks(terminal, f"{source_kind} terminal")
    _verification_claim_locks(verification, source_kind)
    return _VerifiedGroup(
        source_kind,
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


def _load_verified_groups(repository_root: Path) -> tuple[_VerifiedGroup, ...]:
    base = repository_root / ".tmp" / "exact-freeze"
    groups: list[_VerifiedGroup] = []

    source_kind, terminal_path, verification_path = _INPUT_ROLES[0]
    if (base / "v180r11_v34_retained_failure.json").exists():
        _fail("V180r11 retained output inventory changed")
    terminal_bytes = _read_bytes(repository_root, terminal_path, "V180r11 terminal")
    verification_bytes = _read_bytes(
        repository_root, verification_path, "V180r11 verification"
    )
    if not (
        len(terminal_bytes) == r11_evidence.EXPECTED_TERMINAL_BYTE_COUNT
        and _sha256(terminal_bytes) == r11_evidence.EXPECTED_TERMINAL_SHA256
        and len(verification_bytes)
        == r11_evidence.EXPECTED_VERIFICATION_BYTE_COUNT
        and _sha256(verification_bytes)
        == r11_evidence.EXPECTED_VERIFICATION_SHA256
    ):
        _fail("V180r11 retained terminal or verification bytes changed")
    try:
        replayed = (
            r11_verifier.verify_v34_retained_recovery_bytes_independently_v180r11(
                terminal_bytes,
                base / "v180r5_v34_production_output",
                recovery_authorization_id=(
                    r11_authorization.EXPECTED_AUTHORIZATION_ID
                ),
            )
        )
    except Exception as error:
        raise ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error(
            "V180r11 independent semantic replay failed"
        ) from error
    if not (
        canonical_json_bytes(replayed) == verification_bytes
        and replayed.get("verification_id")
        == r11_evidence.EXPECTED_VERIFICATION_ID
    ):
        _fail("V180r11 retained verification differs from replay")
    _release_transient_verifier_heap()
    terminal = _object(terminal_bytes, "V180r11 terminal")
    retained_verification = _object(
        verification_bytes, "V180r11 verification"
    )
    groups.append(
        _verified_group(
            source_kind=source_kind,
            terminal_path=terminal_path,
            terminal_bytes=terminal_bytes,
            terminal=terminal,
            verification_path=verification_path,
            verification_bytes=verification_bytes,
            verification=replayed,
            terminal_id_field="v34_retained_terminal_id",
        )
    )
    del terminal_bytes, terminal, verification_bytes, retained_verification, replayed
    _release_transient_verifier_heap()

    source_kind, terminal_path, verification_path = _INPUT_ROLES[1]
    if (base / "v180r10r1_v36_retained_failure.json").exists():
        _fail("V180r10r1 retained output inventory changed")
    terminal_bytes = _read_bytes(
        repository_root, terminal_path, "V180r10r1 terminal"
    )
    verification_bytes = _read_bytes(
        repository_root, verification_path, "V180r10r1 verification"
    )
    if not (
        len(terminal_bytes) == r10r1_evidence.EXPECTED_TERMINAL_BYTE_COUNT
        and _sha256(terminal_bytes) == r10r1_evidence.EXPECTED_TERMINAL_SHA256
        and len(verification_bytes)
        == r10r1_evidence.EXPECTED_VERIFICATION_BYTE_COUNT
        and _sha256(verification_bytes)
        == r10r1_evidence.EXPECTED_VERIFICATION_SHA256
    ):
        _fail("V180r10r1 retained terminal or verification bytes changed")
    try:
        replayed = (
            r10r1_verifier.verify_v36_retained_recovery_bytes_independently_v180r10r1(
                terminal_bytes,
                base / "v180r10_v36_resource_successor_output",
                recovery_authorization_id=(
                    r10r1_authorization.EXPECTED_AUTHORIZATION_ID
                ),
            )
        )
    except Exception as error:
        raise ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error(
            "V180r10r1 independent semantic replay failed"
        ) from error
    if not (
        canonical_json_bytes(replayed) == verification_bytes
        and replayed.get("verification_id")
        == r10r1_evidence.EXPECTED_VERIFICATION_ID
    ):
        _fail("V180r10r1 retained verification differs from replay")
    _release_transient_verifier_heap()
    terminal = _object(terminal_bytes, "V180r10r1 terminal")
    retained_verification = _object(
        verification_bytes, "V180r10r1 verification"
    )
    groups.append(
        _verified_group(
            source_kind=source_kind,
            terminal_path=terminal_path,
            terminal_bytes=terminal_bytes,
            terminal=terminal,
            verification_path=verification_path,
            verification_bytes=verification_bytes,
            verification=replayed,
            terminal_id_field="v36_retained_terminal_id",
        )
    )
    del terminal_bytes, terminal, verification_bytes, retained_verification, replayed
    _release_transient_verifier_heap()

    source_kind, terminal_path, verification_path = _INPUT_ROLES[2]
    frozen_r7r1 = (
        r7r1_evidence.load_frozen_full_ground_fallback_production_evidence_v180r7r1(
            base
        )
    )
    groups.append(
        _verified_group(
            source_kind=source_kind,
            terminal_path=terminal_path,
            terminal_bytes=frozen_r7r1.terminal_bytes,
            terminal=frozen_r7r1.terminal_document(),
            verification_path=verification_path,
            verification_bytes=frozen_r7r1.verification_bytes,
            verification=frozen_r7r1.verification_document(),
            terminal_id_field="production_terminal_bundle_id",
        )
    )
    del frozen_r7r1
    _release_transient_verifier_heap()

    source_kind, terminal_path, verification_path = _INPUT_ROLES[3]
    terminal_bytes, terminal = _read(repository_root, terminal_path, "V180r8 terminal")
    verification_bytes, retained_verification = _read(
        repository_root,
        verification_path,
        "V180r8 verification",
    )
    replayed = r8_verifier.verify_cached_exact_terminal_independently_v180r8(
        terminal_bytes
    )
    if retained_verification != replayed:
        _fail("V180r8 retained verification differs from replay")
    groups.append(
        _verified_group(
            source_kind=source_kind,
            terminal_path=terminal_path,
            terminal_bytes=terminal_bytes,
            terminal=terminal,
            verification_path=verification_path,
            verification_bytes=verification_bytes,
            verification=replayed,
            terminal_id_field="production_terminal_bundle_id",
        )
    )
    del terminal_bytes, terminal, verification_bytes, retained_verification, replayed
    _release_transient_verifier_heap()

    source_kind, terminal_path, verification_path = _INPUT_ROLES[4]
    terminal_bytes, terminal = _read(repository_root, terminal_path, "V180r9 terminal")
    verification_bytes, _ = _read(
        repository_root,
        verification_path,
        "V180r9 verification",
    )
    replayed = r9_evidence.verify_frozen_remaining_terminal_evidence_v180r9(
        terminal_bytes,
        verification_bytes,
    )
    groups.append(
        _verified_group(
            source_kind=source_kind,
            terminal_path=terminal_path,
            terminal_bytes=terminal_bytes,
            terminal=terminal,
            verification_path=verification_path,
            verification_bytes=verification_bytes,
            verification=replayed,
            terminal_id_field="production_campaign_bundle_id",
        )
    )
    del terminal_bytes, terminal, verification_bytes, replayed
    _release_transient_verifier_heap()
    if tuple(row.source_kind for row in groups) != tuple(
        row[0] for row in _INPUT_ROLES
    ):
        _fail("five-source evidence ordering changed")
    return tuple(groups)


def _assert_input_contract(
    protocol_document: Mapping[str, Any],
    authorization_document: Mapping[str, Any],
    groups: Sequence[_VerifiedGroup],
) -> None:
    expected_paths = [
        {
            "source_kind": source_kind,
            "terminal_relative_path": terminal_path,
            "verification_relative_path": verification_path,
        }
        for source_kind, terminal_path, verification_path in _INPUT_ROLES
    ]
    protocol_sources = protocol_document.get("retained_source_groups")
    authorization_inputs = authorization_document.get(
        "retained_source_input_facts"
    )
    observed_facts = [
        {
            "source_kind": group.source_kind,
            "terminal_relative_path": group.terminal_path,
            "terminal_content_id": group.terminal_id,
            "terminal_byte_count": group.terminal_byte_count,
            "terminal_sha256": group.terminal_sha256,
            "verification_relative_path": group.verification_path,
            "verification_id": group.verification_id,
            "verification_byte_count": group.verification_byte_count,
            "verification_sha256": group.verification_sha256,
        }
        for group in groups
    ]
    observed_authorization_facts = [
        fact
        for group in groups
        for fact in (
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

    def retained_facts(rows: Any) -> list[dict[str, Any]] | None:
        if type(rows) is not list:
            return None
        result: list[dict[str, Any]] = []
        for row in rows:
            if type(row) is not dict:
                return None
            terminal = row.get("terminal_fact")
            verification = row.get("verification_fact")
            if type(terminal) is not dict or type(verification) is not dict:
                return None
            result.append(
                {
                    "source_kind": row.get("source_kind"),
                    "terminal_relative_path": terminal.get("relative_path"),
                    "terminal_content_id": terminal.get("content_id"),
                    "terminal_byte_count": terminal.get("byte_count"),
                    "terminal_sha256": terminal.get("sha256"),
                    "verification_relative_path": verification.get(
                        "relative_path"
                    ),
                    "verification_id": verification.get("verification_id"),
                    "verification_byte_count": verification.get("byte_count"),
                    "verification_sha256": verification.get("sha256"),
                }
            )
        return result

    bound_protocol_facts = retained_facts(protocol_sources)
    protocol_paths = (
        [
            {
                "source_kind": row["source_kind"],
                "terminal_relative_path": row["terminal_relative_path"],
                "verification_relative_path": row[
                    "verification_relative_path"
                ],
            }
            for row in bound_protocol_facts
        ]
        if bound_protocol_facts is not None
        else None
    )
    protocol_components = protocol_document.get("ordered_route_components")
    if not (
        protocol_paths == expected_paths
        and bound_protocol_facts == observed_facts
        and authorization_inputs == observed_authorization_facts
        and authorization_document.get("retained_source_input_fact_count") == 10
        and authorization_document.get("retained_source_input_total_byte_count")
        == sum(row["byte_count"] for row in observed_authorization_facts)
        and authorization_document.get("retained_source_input_facts_sha256")
        == _sha256(canonical_json_bytes(observed_authorization_facts))
        and protocol_document.get("terminal_code_count") == TERMINAL_RECEIPT_COUNT
        and authorization_document.get("source_group_count") == SOURCE_GROUP_COUNT
        and authorization_document.get("terminal_code_count")
        == TERMINAL_RECEIPT_COUNT
        and type(protocol_components) is list
        and [
            (row.get("terminal_code"), row.get("route_kind"))
            for row in protocol_components
        ]
        == list(EXPECTED_ROUTE_COMPONENTS)
        and [row.get("component_ordinal") for row in protocol_components]
        == list(range(ROUTE_COMPONENT_CHAIN_COUNT))
        and all(
            row.get("counter_record_count") == COUNTER_RECORDS_PER_V9_CHAIN
            for row in protocol_components
        )
    ):
        _fail("V180r12r2 protocol or authorization input contract changed")


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
        raise ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error(
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
                    _fail("V180r9 terminal row compact projection changed")
                code = TerminalCode(row.get("terminal_code"))
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
        code = TerminalCode(document.get("terminal_code"))
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
        "comparison_vector_id": component.comparison_document[
            "comparison_vector_id"
        ],
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
        values = document[
            "source_occurrence_shared_resource_receipt_ids"
        ]
    elif group.source_kind == "V180R8_FRESH_CACHED_EXACT":
        values = document[
            "source_occurrence_shared_resource_receipt_ids"
        ]
    elif group.source_kind == "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN":
        row = next(
            item
            for item in document["terminal_rows"]
            if item["terminal_code"] == terminal_code.value
        )
        values = row["source_occurrence_shared_resource_receipt_ids"]
    else:
        values = document[
            "source_occurrence_shared_resource_receipt_ids"
        ]
    if not (
        len(values) in {0, 9}
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
            row["route_component_chain_receipt_id"]
            for row in component_receipts
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
        "materialized_source_byte_count": reference[
            "materialized_source_byte_count"
        ],
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
            {row["route_component_chain_receipt_id"] for row in component_receipts}
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
            for receipt, vector in zip(
                component_receipts,
                vectors,
                strict=True,
            )
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


def _assemble_ten_terminal_aggregation_bytes_v180r12r2(
    groups: Sequence[_VerifiedGroup],
    *,
    aggregation_protocol_id: str,
    execution_authorization_id: str,
) -> bytes:
    if not (
        type(aggregation_protocol_id) is str
        and len(aggregation_protocol_id) == 64
        and set(aggregation_protocol_id) <= set("0123456789abcdef")
        and type(execution_authorization_id) is str
        and len(execution_authorization_id) == 64
        and set(execution_authorization_id) <= set("0123456789abcdef")
    ):
        _fail("aggregation protocol or execution authorization ID is malformed")
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
        declarations = (
            campaign_accounting.record_campaign_scope_shared_resources_v180r12r2(
                aggregation_protocol_id=aggregation_protocol_id,
                execution_authorization_id=execution_authorization_id,
                subject_id=subject_id,
                source_receipt_ids=sorted(source_receipt_ids),
                values={**structural_quantities, "io.output_bytes": guess},
            )
        )
        structural_boundary = (
            campaign_accounting.derive_campaign_scope_accounting_v180r12r2(
                declarations
            )
        )
        replayed_structural_boundary = (
            campaign_accounting.verify_campaign_scope_accounting_v180r12r2(
                structural_boundary.to_document()
            )
        )
        structural_boundary_document = structural_boundary.to_document()
        if not (
            replayed_structural_boundary.to_document()
            == structural_boundary_document
            and len(declarations) == CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        ):
            _fail("campaign-scope structural boundary replay changed")
        _assert_campaign_scope_structural_boundary(
            structural_boundary_document
        )
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
            "terminal_shared_resource_receipt_sets": (
                terminal_shared_receipt_sets
            ),
            "occurrence_shared_resource_receipt_count": (
                OCCURRENCE_SHARED_RESOURCE_RECEIPT_COUNT
            ),
            "campaign_scope_structural_boundary": (
                structural_boundary_document
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
            "route_component_counter_closure_status": (
                ROUTE_COMPONENT_COUNTER_CLOSURE_STATUS
            ),
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
    _fail("V180r12r2 aggregation output fixed point did not converge")


def reconstruct_ten_terminal_aggregation_core_no_output_v180r12r2(
    repository_root: Path,
    *,
    aggregation_protocol_id: str,
    execution_authorization_id: str,
    protocol_document: Mapping[str, Any],
    authorization_document: Mapping[str, Any],
) -> bytes:
    """Run the complete producer core and return bytes without writing output.

    The IDs may be preregistered development-only dummy IDs.  The retained
    inputs and their protocol/authorization source facts remain exact; the
    helper therefore exercises source verification, the structural boundary,
    complete bundle assembly, the output-length fixed point, and final
    canonical serialization through the same path as production.
    """

    if not isinstance(repository_root, Path) or not repository_root.is_dir():
        _fail("repository root is absent")
    _claim_locks(protocol_document, "V180r12r2 protocol")
    _claim_locks(authorization_document, "V180r12r2 authorization")
    groups = _load_verified_groups(repository_root)
    _assert_input_contract(protocol_document, authorization_document, groups)
    return _assemble_ten_terminal_aggregation_bytes_v180r12r2(
        groups,
        aggregation_protocol_id=aggregation_protocol_id,
        execution_authorization_id=execution_authorization_id,
    )


def materialize_ten_terminal_aggregation_v180r12r2(
    repository_root: Path,
) -> bytes:
    if not isinstance(repository_root, Path) or not repository_root.is_dir():
        _fail("repository root is absent")
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
        and frozen_authorization.authorization_id
        == authorization.EXPECTED_AUTHORIZATION_ID
        and authorization_document.get("aggregation_protocol_id")
        == frozen_protocol.aggregation_protocol_id
    ):
        _fail("V180r12r2 protocol or authorization is not frozen")
    _claim_locks(protocol_document, "V180r12r2 protocol")
    _claim_locks(authorization_document, "V180r12r2 authorization")
    return reconstruct_ten_terminal_aggregation_core_no_output_v180r12r2(
        repository_root,
        aggregation_protocol_id=frozen_protocol.aggregation_protocol_id,
        execution_authorization_id=frozen_authorization.authorization_id,
        protocol_document=protocol_document,
        authorization_document=authorization_document,
    )


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TenTerminalAggregationBundleV180R12R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    bundle_id: str

    def __post_init__(self) -> None:
        document = _object(self.canonical_bytes, "V180r12r2 aggregation")
        payload = dict(document)
        identity = payload.pop("production_aggregation_bundle_id", None)
        if not (
            self._issuer is _ISSUER
            and set(document) == _BUNDLE_FIELDS
            and identity == self.bundle_id
            and identity
            == domains.extension_content_id_v180r12r2(
                domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R2_DOMAIN,
                payload,
            )
            and document["output_bytes_fixed_point"]
            == len(self.canonical_bytes)
            and document["route_component_counter_closure_status"]
            == ROUTE_COMPONENT_COUNTER_CLOSURE_STATUS
            and document["COUNTER_COMPLETENESS_BLOCKER"]
            == COUNTER_COMPLETENESS_BLOCKER
            and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
            and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
            and document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
            and document["BREAK_EVEN_GATE"] == "NOT_RUN"
            and document["campaign_scope_actual_counter_record_count"]
            == CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT
            and document["campaign_scope_actual_shared_resource_receipt_count"]
            == CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT
            and document["campaign_scope_actual_work_vector_count"]
            == CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT
            and document["campaign_scope_actual_comparison_vector_count"]
            == CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT
            and document["campaign_scope_actual_projection_proof_count"]
            == CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT
            and document[
                "campaign_scope_actual_native_zero_attestation_count"
            ]
            == CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT
            and document["campaign_scope_authoritative_receipt_count"]
            == CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT
            and document["official_scalar_cost"] is None
            and document["official_N_break_even"] is None
            and document["official_execution_allowed"] is False
        ):
            _fail("V180r12r2 aggregation object is foreign or malformed")

    def to_document(self) -> dict[str, Any]:
        return _object(self.canonical_bytes, "V180r12r2 aggregation")


def freeze_ten_terminal_aggregation_v180r12r2(
    repository_root: Path,
) -> TenTerminalAggregationBundleV180R12R2:
    raw = materialize_ten_terminal_aggregation_v180r12r2(repository_root)
    document = _object(raw, "V180r12r2 aggregation")
    return TenTerminalAggregationBundleV180R12R2(
        _ISSUER,
        raw,
        document["production_aggregation_bundle_id"],
    )


__all__ = (
    "CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT",
    "CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT",
    "CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT",
    "CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT",
    "CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT",
    "CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT",
    "CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT",
    "CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT",
    "COUNTER_COMPLETENESS_BLOCKER",
    "COUNTER_RECORDS_PER_V9_CHAIN",
    "ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error",
    "EXPECTED_ROUTE_COMPONENTS",
    "MAXIMUM_FIXED_POINT_ITERATIONS",
    "OCCURRENCE_SHARED_RESOURCE_RECEIPT_COUNT",
    "ROUTE_COMPONENT_CHAIN_COUNT",
    "ROUTE_COMPONENT_COUNTER_CLOSURE_STATUS",
    "ROUTE_COMPONENT_COUNTER_RECORD_COUNT",
    "SHARED_RESOURCE_PATHS",
    "SOURCE_GROUP_COUNT",
    "TEN_TERMINAL_REPRESENTATIVE_COUNTER_RECORD_COUNT",
    "TERMINAL_RECEIPT_COUNT",
    "TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT",
    "TenTerminalAggregationBundleV180R12R2",
    "V180R7R1_ADDITIONAL_COUNTER_RECORD_COUNT",
    "WORKING_BYTES_HARD_CAP",
    "freeze_ten_terminal_aggregation_v180r12r2",
    "materialize_ten_terminal_aggregation_v180r12r2",
    "reconstruct_ten_terminal_aggregation_core_no_output_v180r12r2",
)
