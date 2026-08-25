"""Structural-only campaign boundary for the V180r12r2 aggregation.

The ten retained terminal occurrences already contain the ninety authoritative
shared-resource receipts.  Aggregation orchestration did not run an
instrumented counter recorder, so its nine declared quantities are structural
obligations and denominators only.  They are deliberately not CounterRecords,
not a WorkVector, not a ComparisonVector, not a projection proof, and not a
native-zero attestation.

The legacy function names remain as narrow compatibility shims for the frozen
finalizer call surface, but they now produce and verify only a strict
``campaign_scope_structural_boundary``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v180r12r2e as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "1.0.0"
CAMPAIGN_SCOPE_KIND = "TEN_TERMINAL_AGGREGATION_ORCHESTRATION"
CAMPAIGN_SOURCE_GROUP_COUNT = 5
CAMPAIGN_STRUCTURAL_DECLARATION_COUNT = 9
CAMPAIGN_ACTUAL_COUNTER_RECORD_COUNT = 0
AUTHORITATIVE_OCCURRENCE_RECEIPT_COUNT = 90
AUTHORITATIVE_RECEIPT_TOTAL = 90
WORKING_BYTES_AUTHORIZATION_CAP = 16 * 1024 * 1024 * 1024

COUNTER_COMPLETENESS_GATE = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE = "NOT_RUN"

CAMPAIGN_STRUCTURAL_PATHS = (
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

# Compatibility names describe the accepted input mapping only.  They do not
# assert that campaign-scope receipts or CounterRecords exist.
CAMPAIGN_COUNTER_PATHS = CAMPAIGN_STRUCTURAL_PATHS
CAMPAIGN_SHARED_RESOURCE_RECEIPT_COUNT = CAMPAIGN_ACTUAL_COUNTER_RECORD_COUNT

_OBLIGATION_QUANTITIES = {
    "common.hash_invocations": 15,
    "common.integrity_checks": 10,
    "common.protocol_checks": 10,
}
_ABSENCE_PATHS = (
    "io.mounted_bytes_peak",
    "io.staged_bytes",
    "process.launches",
)
_ROW_FIELDS = {
    "path",
    "declared_quantity",
    "quantity_semantics",
    "authority_class",
    "actual_measurement_present",
    "counter_gate_eligible",
    "economics_gate_eligible",
}
_BOUNDARY_FIELDS = {
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

_CID = re.compile(r"^[0-9a-f]{64}$")
_ISSUER = object()


class ConstructionK7TenTerminalCampaignAccountingV180R12R2Error(ValueError):
    """The structural campaign boundary is foreign, incomplete, or inflated."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TenTerminalCampaignAccountingV180R12R2Error(message)


def _cid(value: Any, label: str) -> str:
    if type(value) is not str or _CID.fullmatch(value) is None:
        _fail(f"{label} must be one lowercase SHA-256 content ID")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be a nonnegative exact integer")
    return value


def _source_ids(values: Any) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        _fail("source_receipt_ids must be one exact sequence")
    result = tuple(_cid(value, "source receipt ID") for value in values)
    if not (
        len(result) == CAMPAIGN_SOURCE_GROUP_COUNT
        and len(set(result)) == CAMPAIGN_SOURCE_GROUP_COUNT
        and tuple(sorted(result)) == result
    ):
        _fail("source_receipt_ids must be five unique sorted content IDs")
    return result


def _canonical_object(value: Any, label: str) -> tuple[bytes, dict[str, Any]]:
    if type(value) is bytes:
        try:
            document = loads_canonical_json(value)
        except Exception as error:
            raise ConstructionK7TenTerminalCampaignAccountingV180R12R2Error(
                f"{label} is not canonical JSON"
            ) from error
        if type(document) is not dict or canonical_json_bytes(document) != value:
            _fail(f"{label} is not one canonical object")
        return value, document
    if type(value) is not dict:
        _fail(f"{label} must be canonical bytes or one exact dictionary")
    return canonical_json_bytes(value), value


def _row_semantics(path: str) -> tuple[str, str]:
    if path in _OBLIGATION_QUANTITIES:
        return (
            "DECLARED_OBLIGATION_CARDINALITY",
            "PRECOMMITTED_ORCHESTRATION_OBLIGATION",
        )
    if path == "io.read_bytes":
        return (
            "DERIVED_INPUT_BYTE_DENOMINATOR",
            "DERIVED_FROM_FROZEN_RETAINED_INPUT_BYTES",
        )
    if path == "io.output_bytes":
        return (
            "DERIVED_OUTPUT_BYTE_DENOMINATOR",
            "DERIVED_FROM_CANONICAL_AGGREGATE_BYTES",
        )
    if path == "memory.working_bytes_peak":
        return (
            "AUTHORIZATION_CAP_NOT_OBSERVED_PEAK",
            "FROZEN_EXECUTION_AUTHORIZATION_CAP",
        )
    if path in _ABSENCE_PATHS:
        return (
            "DECLARED_ABSENCE_OBLIGATION_NOT_NATIVE_ZERO",
            "PRECOMMITTED_ABSENCE_OBLIGATION",
        )
    raise AssertionError("campaign structural path is not classified")


def _declaration_document(path: str, quantity: int) -> dict[str, Any]:
    semantics, authority = _row_semantics(path)
    return {
        "path": path,
        "declared_quantity": quantity,
        "quantity_semantics": semantics,
        "authority_class": authority,
        "actual_measurement_present": False,
        "counter_gate_eligible": False,
        "economics_gate_eligible": False,
    }


def _parse_declaration(document: Any) -> dict[str, Any]:
    if type(document) is not dict or set(document) != _ROW_FIELDS:
        _fail("campaign structural declaration field set mismatch")
    path = document.get("path")
    if type(path) is not str or path not in CAMPAIGN_STRUCTURAL_PATHS:
        _fail("campaign structural declaration path changed")
    quantity = _nonnegative_int(document.get("declared_quantity"), path)
    if document != _declaration_document(path, quantity):
        _fail("campaign structural declaration semantics changed")
    return document


def _validate_declared_quantities(values: Mapping[str, int]) -> dict[str, int]:
    if not isinstance(values, Mapping) or set(values) != set(
        CAMPAIGN_STRUCTURAL_PATHS
    ):
        _fail("campaign values must exactly cover the nine structural paths")
    quantities = {
        path: _nonnegative_int(values[path], path)
        for path in CAMPAIGN_STRUCTURAL_PATHS
    }
    if not (
        all(quantities[path] == value for path, value in _OBLIGATION_QUANTITIES.items())
        and all(quantities[path] == 0 for path in _ABSENCE_PATHS)
        and quantities["memory.working_bytes_peak"]
        == WORKING_BYTES_AUTHORIZATION_CAP
    ):
        _fail("campaign obligation, absence, or authorization-cap quantity changed")
    return quantities


class _UncopyableStructuralArtifact:
    __slots__ = ()

    def __copy__(self) -> NoReturn:
        _fail("campaign structural authority cannot be copied")

    def __deepcopy__(self, memo: dict[int, object]) -> NoReturn:
        del memo
        _fail("campaign structural authority cannot be deep-copied")

    def __reduce__(self) -> NoReturn:
        _fail("campaign structural authority cannot be pickled")


@dataclass(frozen=True, slots=True)
class CampaignScopeStructuralDeclarationV180R12R2(
    _UncopyableStructuralArtifact
):
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    _aggregation_protocol_id: str = field(repr=False)
    _execution_authorization_id: str = field(repr=False)
    _subject_id: str = field(repr=False)
    _source_receipt_ids: tuple[str, ...] = field(repr=False)

    def __post_init__(self) -> None:
        raw, document = _canonical_object(
            self.canonical_bytes,
            "campaign structural declaration",
        )
        if not (
            self._issuer is _ISSUER
            and raw == self.canonical_bytes
            and _parse_declaration(document) == document
            and _cid(self._aggregation_protocol_id, "aggregation protocol ID")
            == self._aggregation_protocol_id
            and _cid(self._execution_authorization_id, "execution authorization ID")
            == self._execution_authorization_id
            and _cid(self._subject_id, "campaign subject ID") == self._subject_id
            and _source_ids(self._source_receipt_ids) == self._source_receipt_ids
        ):
            _fail("campaign structural declaration is foreign")

    def to_document(self) -> dict[str, Any]:
        return _canonical_object(
            self.canonical_bytes,
            "campaign structural declaration",
        )[1]


@dataclass(frozen=True, slots=True)
class CampaignScopeStructuralBoundaryV180R12R2(_UncopyableStructuralArtifact):
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_scope_structural_boundary_id: str
    structural_declarations: tuple[
        CampaignScopeStructuralDeclarationV180R12R2, ...
    ] = field(repr=False)

    def __post_init__(self) -> None:
        _, document = _canonical_object(
            self.canonical_bytes,
            "campaign structural boundary",
        )
        payload = dict(document)
        identity = payload.pop("campaign_scope_structural_boundary_id", None)
        if not (
            self._issuer is _ISSUER
            and type(self.structural_declarations) is tuple
            and len(self.structural_declarations)
            == CAMPAIGN_STRUCTURAL_DECLARATION_COUNT
            and all(
                type(row) is CampaignScopeStructuralDeclarationV180R12R2
                for row in self.structural_declarations
            )
            and document.get("structural_declarations")
            == [row.to_document() for row in self.structural_declarations]
            and identity == self.campaign_scope_structural_boundary_id
            and identity
            == domains.extension_content_id_v180r12r2e(
                domains.CONSTRUCTION_K7_CAMPAIGN_STRUCTURAL_BOUNDARY_V180R12R2E_DOMAIN,
                payload,
            )
        ):
            _fail("campaign structural boundary is foreign")

    def to_document(self) -> dict[str, Any]:
        return _canonical_object(
            self.canonical_bytes,
            "campaign structural boundary",
        )[1]


def record_campaign_scope_structural_declarations_v180r12r2(
    aggregation_protocol_id: str,
    execution_authorization_id: str,
    subject_id: str,
    source_receipt_ids: Sequence[str],
    values: Mapping[str, int],
) -> tuple[CampaignScopeStructuralDeclarationV180R12R2, ...]:
    """Declare nine structural quantities without minting actual records."""

    protocol_id = _cid(aggregation_protocol_id, "aggregation protocol ID")
    authorization_id = _cid(
        execution_authorization_id,
        "execution authorization ID",
    )
    canonical_subject_id = _cid(subject_id, "campaign subject ID")
    sources = _source_ids(tuple(sorted(source_receipt_ids)))
    quantities = _validate_declared_quantities(values)
    return tuple(
        CampaignScopeStructuralDeclarationV180R12R2(
            _ISSUER,
            canonical_json_bytes(_declaration_document(path, quantities[path])),
            protocol_id,
            authorization_id,
            canonical_subject_id,
            sources,
        )
        for path in CAMPAIGN_STRUCTURAL_PATHS
    )


def _declaration_context(
    declarations: Sequence[CampaignScopeStructuralDeclarationV180R12R2],
) -> tuple[
    tuple[CampaignScopeStructuralDeclarationV180R12R2, ...],
    str,
    str,
    str,
    tuple[str, ...],
]:
    if (
        isinstance(declarations, (str, bytes))
        or not isinstance(declarations, Sequence)
        or len(declarations) != CAMPAIGN_STRUCTURAL_DECLARATION_COUNT
        or any(
            type(row) is not CampaignScopeStructuralDeclarationV180R12R2
            for row in declarations
        )
    ):
        _fail("derive requires exactly nine typed structural declarations")
    rows = tuple(declarations)
    documents = tuple(_parse_declaration(row.to_document()) for row in rows)
    if tuple(row["path"] for row in documents) != CAMPAIGN_STRUCTURAL_PATHS:
        _fail("campaign structural declarations changed path order")
    contexts = {
        (
            row._aggregation_protocol_id,
            row._execution_authorization_id,
            row._subject_id,
            row._source_receipt_ids,
        )
        for row in rows
    }
    if len(contexts) != 1:
        _fail("campaign structural declarations do not share one context")
    protocol_id, authorization_id, subject_id, source_ids = next(iter(contexts))
    quantities = {row["path"]: row["declared_quantity"] for row in documents}
    _validate_declared_quantities(quantities)
    return rows, protocol_id, authorization_id, subject_id, source_ids


def derive_campaign_scope_structural_boundary_v180r12r2(
    declarations: Sequence[CampaignScopeStructuralDeclarationV180R12R2],
) -> CampaignScopeStructuralBoundaryV180R12R2:
    """Bind the declarations into a strict non-authoritative boundary."""

    rows, protocol_id, authorization_id, subject_id, source_ids = (
        _declaration_context(declarations)
    )
    documents = [row.to_document() for row in rows]
    by_path = {row["path"]: row["declared_quantity"] for row in documents}
    payload = {
        "schema": "acfqp.campaign_scope_structural_boundary.v180r12r2",
        "schema_version": SCHEMA_VERSION,
        "scope": CAMPAIGN_SCOPE_KIND,
        "aggregation_protocol_id": protocol_id,
        "execution_authorization_id": authorization_id,
        "subject_id": subject_id,
        "source_receipt_ids": list(source_ids),
        "source_group_count": CAMPAIGN_SOURCE_GROUP_COUNT,
        "structural_declarations": documents,
        "structural_declaration_count": CAMPAIGN_STRUCTURAL_DECLARATION_COUNT,
        "actual_counter_record_count": CAMPAIGN_ACTUAL_COUNTER_RECORD_COUNT,
        "actual_work_vector_present": False,
        "actual_comparison_vector_present": False,
        "actual_projection_proof_present": False,
        "actual_native_zero_attestation_present": False,
        "occurrence_route_record_count": 0,
        "construction_axis_record_count": 0,
        "campaign_scope_authoritative_receipt_count": 0,
        "authoritative_occurrence_receipt_count": (
            AUTHORITATIVE_OCCURRENCE_RECEIPT_COUNT
        ),
        "authoritative_receipt_total": AUTHORITATIVE_RECEIPT_TOTAL,
        "hash_invocation_obligation_count": by_path["common.hash_invocations"],
        "integrity_check_obligation_count": by_path["common.integrity_checks"],
        "protocol_check_obligation_count": by_path["common.protocol_checks"],
        "derived_input_byte_denominator": by_path["io.read_bytes"],
        "derived_output_byte_denominator": by_path["io.output_bytes"],
        "working_bytes_authorization_cap": by_path["memory.working_bytes_peak"],
        "working_bytes_peak_measurement_present": False,
        "zero_absence_obligation_count": len(_ABSENCE_PATHS),
        "native_zero_claim_count": 0,
        "counter_gate_eligible": False,
        "economics_gate_eligible": False,
        "structural_boundary_only": True,
        "scientific_success_claimed": False,
        "COUNTER_COMPLETENESS_GATE": COUNTER_COMPLETENESS_GATE,
        "WORKLOAD_ECONOMICS_GATE": WORKLOAD_ECONOMICS_GATE,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "campaign_scope_structural_boundary_id": (
            domains.extension_content_id_v180r12r2e(
                domains.CONSTRUCTION_K7_CAMPAIGN_STRUCTURAL_BOUNDARY_V180R12R2E_DOMAIN,
                payload,
            )
        ),
    }
    return CampaignScopeStructuralBoundaryV180R12R2(
        _ISSUER,
        canonical_json_bytes(document),
        document["campaign_scope_structural_boundary_id"],
        rows,
    )


def verify_campaign_scope_structural_boundary_v180r12r2(
    value: bytes | dict[str, Any],
) -> CampaignScopeStructuralBoundaryV180R12R2:
    """Rebuild a boundary and reject actual/economics authority inflation."""

    raw, document = _canonical_object(value, "campaign structural boundary")
    if set(document) != _BOUNDARY_FIELDS:
        _fail("campaign structural boundary field set mismatch")
    rows = document.get("structural_declarations")
    if not (
        type(rows) is list
        and len(rows) == CAMPAIGN_STRUCTURAL_DECLARATION_COUNT
        and all(type(row) is dict for row in rows)
    ):
        _fail("campaign structural declaration denominator changed")
    protocol_id = _cid(document.get("aggregation_protocol_id"), "aggregation protocol ID")
    authorization_id = _cid(
        document.get("execution_authorization_id"),
        "execution authorization ID",
    )
    subject_id = _cid(document.get("subject_id"), "campaign subject ID")
    source_ids = _source_ids(document.get("source_receipt_ids"))
    declarations = tuple(
        CampaignScopeStructuralDeclarationV180R12R2(
            _ISSUER,
            canonical_json_bytes(_parse_declaration(row)),
            protocol_id,
            authorization_id,
            subject_id,
            source_ids,
        )
        for row in rows
    )
    expected = derive_campaign_scope_structural_boundary_v180r12r2(declarations)
    if document != expected.to_document() or raw != expected.canonical_bytes:
        _fail("campaign structural boundary changed under exact replay")
    return expected


# Frozen finalizer compatibility shims.  Despite their historical names these
# functions mint no receipt, CounterRecord, WorkVector, comparison, or proof.
def record_campaign_scope_shared_resources_v180r12r2(
    aggregation_protocol_id: str,
    execution_authorization_id: str,
    subject_id: str,
    source_receipt_ids: Sequence[str],
    values: Mapping[str, int],
) -> tuple[CampaignScopeStructuralDeclarationV180R12R2, ...]:
    return record_campaign_scope_structural_declarations_v180r12r2(
        aggregation_protocol_id,
        execution_authorization_id,
        subject_id,
        source_receipt_ids,
        values,
    )


def derive_campaign_scope_accounting_v180r12r2(
    declarations: Sequence[CampaignScopeStructuralDeclarationV180R12R2],
) -> CampaignScopeStructuralBoundaryV180R12R2:
    return derive_campaign_scope_structural_boundary_v180r12r2(declarations)


def verify_campaign_scope_accounting_v180r12r2(
    value: bytes | dict[str, Any],
) -> CampaignScopeStructuralBoundaryV180R12R2:
    return verify_campaign_scope_structural_boundary_v180r12r2(value)


__all__ = (
    "AUTHORITATIVE_OCCURRENCE_RECEIPT_COUNT",
    "AUTHORITATIVE_RECEIPT_TOTAL",
    "CAMPAIGN_ACTUAL_COUNTER_RECORD_COUNT",
    "CAMPAIGN_COUNTER_PATHS",
    "CAMPAIGN_SCOPE_KIND",
    "CAMPAIGN_SHARED_RESOURCE_RECEIPT_COUNT",
    "CAMPAIGN_SOURCE_GROUP_COUNT",
    "CAMPAIGN_STRUCTURAL_DECLARATION_COUNT",
    "CAMPAIGN_STRUCTURAL_PATHS",
    "COUNTER_COMPLETENESS_GATE",
    "WORKING_BYTES_AUTHORIZATION_CAP",
    "WORKLOAD_ECONOMICS_GATE",
    "CampaignScopeStructuralBoundaryV180R12R2",
    "CampaignScopeStructuralDeclarationV180R12R2",
    "ConstructionK7TenTerminalCampaignAccountingV180R12R2Error",
    "derive_campaign_scope_accounting_v180r12r2",
    "derive_campaign_scope_structural_boundary_v180r12r2",
    "record_campaign_scope_shared_resources_v180r12r2",
    "record_campaign_scope_structural_declarations_v180r12r2",
    "verify_campaign_scope_accounting_v180r12r2",
    "verify_campaign_scope_structural_boundary_v180r12r2",
)
