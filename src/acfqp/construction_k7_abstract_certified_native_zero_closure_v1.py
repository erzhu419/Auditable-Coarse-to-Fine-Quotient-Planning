"""Exact zero-value subset closure for a model-only abstract PASS.

Contract 2.0.41 consumes the Contract-2.0.38 coverage blocker and closes only
the zero values justified by the complete evidence already present there.
It does not reinterpret a V1 CounterRecord as V6 and it never treats an
unobserved event as zero.

For the frozen live PASS, 26 of the 27 legacy zero-valued paths can be proved:

* 23 belong exclusively to LOCAL, FALLBACK, or REBUILD stages forbidden by
  the ``ABSTRACT_CERTIFIED`` recipe and excluded by the source/import window;
* three are exact failure complements of one successful process, route, and
  solver completion.

``io.mounted_bytes_peak`` cannot be zero: the worker sees a runtime tree but
V1 has no mounted-payload meter.  The 160 V6-only construction paths also stay
open: 100 belong to required acquisition/build/closure stages, while 60 are
optional recovery stages whose reachability cannot be inferred from an absent
V1 event without a complete transitive source/import window.

The resulting partition is therefore 23 native-zero proofs, three derived
complement *value* proofs, and 176 typed gaps.  The complement proofs are not
native-zero attestations and do not close the formal derived reconciliation.
Shared-resource receipts, derived reconciliation, formal V6 records,
vectors, terminalization, certification, and all official Gates remain open.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage_v1
from acfqp import construction_k7_all_path_operation_boundary_manifest_v1 as boundary_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_RESIDUAL_GAP_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_EXECUTION_WINDOW_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_PROOF_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_REPLAY_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    parse_content_id,
)
from acfqp.phase3e_model_only_executor_v1 import ModelOnlyQueryExecutionV1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.41"
PROFILE_KEY = "construction_k7_abstract_certified_native_zero_closure_v1"

EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_CLOSED_ZERO_VALUE_COUNT = 26
EXPECTED_NATIVE_ZERO_PROOF_COUNT = 23
EXPECTED_DERIVED_COMPLEMENT_VALUE_PROOF_COUNT = 3
EXPECTED_RESIDUAL_GAP_COUNT = 176
EXPECTED_REQUIRED_STAGE_GAP_COUNT = 100
EXPECTED_OPTIONAL_STAGE_GAP_COUNT = 60
EXPECTED_POSITIVE_BINDING_GAP_COUNT = 15
EXPECTED_MOUNTED_PEAK_GAP_COUNT = 1

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

EXECUTION_WINDOW_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_EXECUTION_WINDOW_V1_DOMAIN
)
ZERO_VALUE_PROOF_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_PROOF_V1_DOMAIN
)
RESIDUAL_GAP_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_RESIDUAL_GAP_V1_DOMAIN
ZERO_VALUE_CLOSURE_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_CLOSURE_V1_DOMAIN
)
REPLAY_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_REPLAY_V1_DOMAIN

LOCAL_DOMAINS = frozenset(
    {
        EXECUTION_WINDOW_DOMAIN,
        ZERO_VALUE_PROOF_DOMAIN,
        RESIDUAL_GAP_DOMAIN,
        ZERO_VALUE_CLOSURE_DOMAIN,
        REPLAY_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 5 or not LOCAL_DOMAINS.issubset(  # pragma: no cover
    PHASE3E_DOMAIN_TAGS
):
    raise RuntimeError("abstract-certified zero-value domains must be central and unique")

_WINDOW_ISSUER = object()
_PROOF_ISSUER = object()
_GAP_ISSUER = object()
_CLOSURE_ISSUER = object()


class ConstructionK7AbstractCertifiedZeroValueClosureV1Error(ValueError):
    """A source window, zero proof, or revised partition changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractCertifiedZeroValueClosureV1Error(message)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("zero-value closure used an unknown local content domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractCertifiedZeroValueClosureV1Error(
            f"{label} must be one exact content ID"
        ) from error


class ZeroValueProofKindV1(str, Enum):
    FORBIDDEN_ROUTE_STAGE_SOURCE_CLOSED = "FORBIDDEN_ROUTE_STAGE_SOURCE_CLOSED"
    SUCCESSFUL_COMPLETION_COMPLEMENT = "SUCCESSFUL_COMPLETION_COMPLEMENT"


class ResidualGapCodeV1(str, Enum):
    REQUIRED_STAGE_OWNER_EVIDENCE_MISSING = "REQUIRED_STAGE_OWNER_EVIDENCE_MISSING"
    OPTIONAL_STAGE_REACHABILITY_AND_TRANSITIVE_SOURCE_CLOSURE_MISSING = (
        "OPTIONAL_STAGE_REACHABILITY_AND_TRANSITIVE_SOURCE_CLOSURE_MISSING"
    )
    POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE = (
        "POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE"
    )
    MOUNTED_PAYLOAD_PEAK_WAS_NOT_MEASURED = "MOUNTED_PAYLOAD_PEAK_WAS_NOT_MEASURED"


class ReplayOutcomeV1(str, Enum):
    ZERO_SUBSET_CLOSED_ACCOUNTING_STILL_BLOCKED = (
        "ZERO_SUBSET_CLOSED_ACCOUNTING_STILL_BLOCKED"
    )
    DOCUMENT_BLOCKED = "DOCUMENT_BLOCKED"


_FORBIDDEN_STAGE_NAMES = frozenset(
    {"LOCAL_ATTEMPT", "DIRECT_FALLBACK", "REBUILD"}
)

_COMPLETION_COMPLEMENTS = {
    "process.exit_failures": (
        "process.launches",
        "process.exit_successes",
    ),
    "route.failures": (
        "route.attempts",
        "route.successes",
    ),
    "solver.failures": (
        "solver.attempts",
        "solver.successes",
    ),
}


@dataclass(frozen=True, slots=True)
class AbstractPassExecutionWindowV1:
    _issuer: InitVar[object]
    coverage_report_id: str
    source_archive_id: str
    operation_boundary_manifest_id: str
    operational_execution_id: str
    request_id: str
    worker_output_id: str
    model_only_result_id: str
    event_trace_id: str
    legacy_work_vector_id: str
    legacy_native_zero_attestation_id: str
    legacy_reconciliation_proof_id: str
    process_values: tuple[tuple[str, int], ...]
    route_values: tuple[tuple[str, int], ...]
    solver_values: tuple[tuple[str, int], ...]
    inactive_route_values: tuple[tuple[str, int], ...]
    _window_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _WINDOW_ISSUER:
            _fail("abstract PASS execution window is caller-minted")
        for value, label in (
            (self.coverage_report_id, "coverage report"),
            (self.source_archive_id, "source archive"),
            (self.operation_boundary_manifest_id, "operation-boundary manifest"),
            (self.operational_execution_id, "operational execution"),
            (self.request_id, "execution request"),
            (self.worker_output_id, "worker output"),
            (self.model_only_result_id, "model-only result"),
            (self.event_trace_id, "native event trace"),
            (self.legacy_work_vector_id, "legacy work vector"),
            (self.legacy_native_zero_attestation_id, "legacy native-zero attestation"),
            (self.legacy_reconciliation_proof_id, "legacy reconciliation proof"),
        ):
            _cid(value, label)
        expected_process = (
            ("process.exit_failures", 0),
            ("process.exit_successes", 1),
            ("process.launches", 1),
        )
        expected_route = (
            ("route.attempts", 1),
            ("route.failures", 0),
            ("route.successes", 1),
        )
        expected_solver = (
            ("solver.attempts", 1),
            ("solver.failures", 0),
            ("solver.successes", 1),
        )
        if (
            self.process_values != expected_process
            or self.route_values != expected_route
            or self.solver_values != expected_solver
            or not self.inactive_route_values
            or tuple(sorted(self.inactive_route_values)) != self.inactive_route_values
            or any(value != 0 for _path, value in self.inactive_route_values)
            or len({path for path, _value in self.inactive_route_values})
            != len(self.inactive_route_values)
        ):
            _fail("abstract PASS execution window values changed")
        object.__setattr__(
            self, "_window_id", _content_id(EXECUTION_WINDOW_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_zero_execution_window.v1",
            "schema_version": SCHEMA_VERSION,
            "coverage_report_id": self.coverage_report_id,
            "source_archive_id": self.source_archive_id,
            "operation_boundary_manifest_id": self.operation_boundary_manifest_id,
            "operational_execution_id": self.operational_execution_id,
            "request_id": self.request_id,
            "worker_output_id": self.worker_output_id,
            "model_only_result_id": self.model_only_result_id,
            "event_trace_id": self.event_trace_id,
            "legacy_work_vector_id": self.legacy_work_vector_id,
            "legacy_native_zero_attestation_id": self.legacy_native_zero_attestation_id,
            "legacy_reconciliation_proof_id": self.legacy_reconciliation_proof_id,
            "process_values": [
                {"path": path, "value": value} for path, value in self.process_values
            ],
            "route_values": [
                {"path": path, "value": value} for path, value in self.route_values
            ],
            "solver_values": [
                {"path": path, "value": value} for path, value in self.solver_values
            ],
            "inactive_route_values": [
                {"path": path, "value": value}
                for path, value in self.inactive_route_values
            ],
            "fresh_process_exit_success": True,
            "model_only_route_success": True,
            "model_only_solver_success": True,
            "ground_local_fallback_rebuild_imports_forbidden": True,
            "complete_selected_source_bytes_replayed": True,
            "complete_transitive_import_manifest_available": False,
            "legacy_records_relabelled_as_v6": False,
        }

    @property
    def window_id(self) -> str:
        if _content_id(EXECUTION_WINDOW_DOMAIN, self._payload()) != self._window_id:
            _fail("abstract PASS execution window changed after issuance")
        return self._window_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "execution_window_id": self.window_id}


@dataclass(frozen=True, slots=True, order=True)
class AbstractCertifiedZeroValueProofV1:
    _issuer: InitVar[object]
    execution_window_id: str
    coverage_report_id: str
    original_path_gap_id: str
    path: str
    semantics_id: str
    owner: str
    scope: str
    stage_contexts: tuple[tuple[str, str], ...]
    kind: ZeroValueProofKindV1
    source_v1_record_id: str | None
    supporting_record_ids: tuple[str, ...]
    operation_boundary_site_ids: tuple[str, ...]
    _proof_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROOF_ISSUER:
            _fail("abstract-certified zero-value proof is caller-minted")
        for value, label in (
            (self.execution_window_id, "execution window"),
            (self.coverage_report_id, "coverage report"),
            (self.original_path_gap_id, "original path gap"),
            *((value, "source/supporting record") for value in (
                *((self.source_v1_record_id,) if self.source_v1_record_id else ()),
                *self.supporting_record_ids,
            )),
            *((value, "operation-boundary site") for value in self.operation_boundary_site_ids),
        ):
            _cid(value, label)
        try:
            object.__setattr__(self, "kind", ZeroValueProofKindV1(self.kind))
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedZeroValueClosureV1Error(
                "zero proof kind is invalid"
            ) from error
        if (
            not self.path
            or not self.semantics_id
            or not self.owner
            or not self.scope
            or not self.stage_contexts
            or tuple(sorted(self.stage_contexts)) != self.stage_contexts
            or tuple(sorted(self.supporting_record_ids)) != self.supporting_record_ids
            or len(set(self.supporting_record_ids)) != len(self.supporting_record_ids)
            or tuple(sorted(self.operation_boundary_site_ids))
            != self.operation_boundary_site_ids
            or len(set(self.operation_boundary_site_ids))
            != len(self.operation_boundary_site_ids)
        ):
            _fail("abstract-certified zero-value proof is incomplete")
        if self.kind is ZeroValueProofKindV1.FORBIDDEN_ROUTE_STAGE_SOURCE_CLOSED:
            if (
                self.source_v1_record_id is None
                or self.supporting_record_ids
                or not self.operation_boundary_site_ids
                or not all(
                    stage in _FORBIDDEN_STAGE_NAMES and disposition == "FORBIDDEN"
                    for stage, disposition in self.stage_contexts
                )
            ):
                _fail("forbidden-stage zero proof lacks exact source/stage evidence")
        else:
            if (
                self.path not in _COMPLETION_COMPLEMENTS
                or self.source_v1_record_id is None
                or len(self.supporting_record_ids) != 2
                or self.operation_boundary_site_ids
            ):
                _fail("completion-complement zero proof lacks exact records")
        object.__setattr__(
            self, "_proof_id", _content_id(ZERO_VALUE_PROOF_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_zero_value_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "execution_window_id": self.execution_window_id,
            "coverage_report_id": self.coverage_report_id,
            "original_path_gap_id": self.original_path_gap_id,
            "path": self.path,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "scope": self.scope,
            "stage_contexts": [
                {"stage_kind": stage, "disposition": disposition}
                for stage, disposition in self.stage_contexts
            ],
            "proof_kind": self.kind.value,
            "proved_value": 0,
            "source_v1_record_id": self.source_v1_record_id,
            "supporting_record_ids": list(self.supporting_record_ids),
            "operation_boundary_site_ids": list(self.operation_boundary_site_ids),
            "source_v1_record_relabelled_as_v6": False,
            "missing_event_inferred_zero": False,
            "v6_counter_record_issued": False,
        }

    @property
    def proof_id(self) -> str:
        if _content_id(ZERO_VALUE_PROOF_DOMAIN, self._payload()) != self._proof_id:
            _fail("abstract-certified zero-value proof changed after issuance")
        return self._proof_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "zero_value_proof_id": self.proof_id}


@dataclass(frozen=True, slots=True, order=True)
class AbstractCertifiedResidualGapV1:
    _issuer: InitVar[object]
    original_path_gap_id: str
    path: str
    semantics_id: str
    stage_contexts: tuple[tuple[str, str], ...]
    code: ResidualGapCodeV1
    source_v1_record_id: str | None
    source_v1_value: int | None
    _gap_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _GAP_ISSUER:
            _fail("abstract-certified residual gap is caller-minted")
        _cid(self.original_path_gap_id, "original path gap")
        if self.source_v1_record_id is not None:
            _cid(self.source_v1_record_id, "source V1 record")
        try:
            object.__setattr__(self, "code", ResidualGapCodeV1(self.code))
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedZeroValueClosureV1Error(
                "residual gap code is invalid"
            ) from error
        if (
            not self.path
            or not self.semantics_id
            or not self.stage_contexts
            or tuple(sorted(self.stage_contexts)) != self.stage_contexts
            or (
                self.source_v1_record_id is None
                and self.source_v1_value is not None
            )
            or (
                self.source_v1_record_id is not None
                and (type(self.source_v1_value) is not int or self.source_v1_value < 0)
            )
        ):
            _fail("abstract-certified residual gap is incomplete")
        if self.code is ResidualGapCodeV1.REQUIRED_STAGE_OWNER_EVIDENCE_MISSING:
            if self.source_v1_record_id is not None or not any(
                disposition in {"REQUIRED_ONCE", "REQUIRED_AT_LEAST_ONCE"}
                for _stage, disposition in self.stage_contexts
            ):
                _fail("required-stage residual gap has inconsistent evidence")
        elif self.code is (
            ResidualGapCodeV1
            .OPTIONAL_STAGE_REACHABILITY_AND_TRANSITIVE_SOURCE_CLOSURE_MISSING
        ):
            if self.source_v1_record_id is not None or not all(
                disposition in {"OPTIONAL_ONCE", "OPTIONAL_REPEATABLE"}
                for _stage, disposition in self.stage_contexts
            ):
                _fail("optional-stage residual gap has inconsistent evidence")
        elif self.code is (
            ResidualGapCodeV1
            .POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE
        ):
            if self.source_v1_record_id is None or not self.source_v1_value:
                _fail("positive binding residual gap lacks positive source record")
        else:
            if (
                self.path != "io.mounted_bytes_peak"
                or self.source_v1_record_id is None
                or self.source_v1_value != 0
            ):
                _fail("mounted-payload residual gap is inconsistent")
        object.__setattr__(
            self, "_gap_id", _content_id(RESIDUAL_GAP_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_residual_gap.v1",
            "schema_version": SCHEMA_VERSION,
            "original_path_gap_id": self.original_path_gap_id,
            "path": self.path,
            "semantics_id": self.semantics_id,
            "stage_contexts": [
                {"stage_kind": stage, "disposition": disposition}
                for stage, disposition in self.stage_contexts
            ],
            "gap_code": self.code.value,
            "source_v1_record_id": self.source_v1_record_id,
            "source_v1_value": self.source_v1_value,
            "missing_event_inferred_zero": False,
            "v6_counter_record_authorized": False,
        }

    @property
    def gap_id(self) -> str:
        if _content_id(RESIDUAL_GAP_DOMAIN, self._payload()) != self._gap_id:
            _fail("abstract-certified residual gap changed after issuance")
        return self._gap_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "residual_gap_id": self.gap_id}


@dataclass(frozen=True, slots=True)
class AbstractCertifiedZeroValueClosureV1:
    _issuer: InitVar[object]
    coverage_report_id: str
    execution_window: AbstractPassExecutionWindowV1
    native_zero_proofs: tuple[AbstractCertifiedZeroValueProofV1, ...]
    derived_complement_value_proofs: tuple[AbstractCertifiedZeroValueProofV1, ...]
    residual_gaps: tuple[AbstractCertifiedResidualGapV1, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CLOSURE_ISSUER
            or type(self.execution_window) is not AbstractPassExecutionWindowV1
            or any(type(row) is not AbstractCertifiedZeroValueProofV1 for row in self.native_zero_proofs)
            or any(type(row) is not AbstractCertifiedZeroValueProofV1 for row in self.derived_complement_value_proofs)
            or any(type(row) is not AbstractCertifiedResidualGapV1 for row in self.residual_gaps)
        ):
            _fail("abstract-certified zero-value closure is caller-minted")
        _cid(self.coverage_report_id, "coverage report")
        all_proofs = self.native_zero_proofs + self.derived_complement_value_proofs
        if (
            self.execution_window.coverage_report_id != self.coverage_report_id
            or len(self.native_zero_proofs) != EXPECTED_NATIVE_ZERO_PROOF_COUNT
            or len(self.derived_complement_value_proofs)
            != EXPECTED_DERIVED_COMPLEMENT_VALUE_PROOF_COUNT
            or len(self.residual_gaps) != EXPECTED_RESIDUAL_GAP_COUNT
            or tuple(row.path for row in self.native_zero_proofs)
            != tuple(sorted(row.path for row in self.native_zero_proofs))
            or tuple(row.path for row in self.derived_complement_value_proofs)
            != tuple(sorted(row.path for row in self.derived_complement_value_proofs))
            or tuple(row.path for row in self.residual_gaps)
            != tuple(sorted(row.path for row in self.residual_gaps))
            or any(
                row.kind
                is not ZeroValueProofKindV1.FORBIDDEN_ROUTE_STAGE_SOURCE_CLOSED
                for row in self.native_zero_proofs
            )
            or any(
                row.kind
                is not ZeroValueProofKindV1.SUCCESSFUL_COMPLETION_COMPLEMENT
                for row in self.derived_complement_value_proofs
            )
            or {row.path for row in all_proofs}
            & {row.path for row in self.residual_gaps}
            or len({row.path for row in all_proofs} | {row.path for row in self.residual_gaps})
            != EXPECTED_REQUIRED_PATH_COUNT
        ):
            _fail("revised 26/176 path partition is incomplete or overlapping")
        gap_counts = {code: 0 for code in ResidualGapCodeV1}
        for row in self.residual_gaps:
            gap_counts[row.code] += 1
        if gap_counts != {
            ResidualGapCodeV1.REQUIRED_STAGE_OWNER_EVIDENCE_MISSING: EXPECTED_REQUIRED_STAGE_GAP_COUNT,
            ResidualGapCodeV1.OPTIONAL_STAGE_REACHABILITY_AND_TRANSITIVE_SOURCE_CLOSURE_MISSING: EXPECTED_OPTIONAL_STAGE_GAP_COUNT,
            ResidualGapCodeV1.POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE: EXPECTED_POSITIVE_BINDING_GAP_COUNT,
            ResidualGapCodeV1.MOUNTED_PAYLOAD_PEAK_WAS_NOT_MEASURED: EXPECTED_MOUNTED_PEAK_GAP_COUNT,
        }:
            _fail("revised zero/gap reason cardinalities changed")
        object.__setattr__(
            self, "_closure_id", _content_id(ZERO_VALUE_CLOSURE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_zero_value_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "coverage_report_id": self.coverage_report_id,
            "execution_window": self.execution_window.to_document(),
            "native_zero_proofs": [row.to_document() for row in self.native_zero_proofs],
            "derived_complement_value_proofs": [
                row.to_document() for row in self.derived_complement_value_proofs
            ],
            "residual_gaps": [row.to_document() for row in self.residual_gaps],
            "required_path_count": EXPECTED_REQUIRED_PATH_COUNT,
            "closed_zero_value_count": EXPECTED_CLOSED_ZERO_VALUE_COUNT,
            "native_zero_proof_count": EXPECTED_NATIVE_ZERO_PROOF_COUNT,
            "derived_complement_value_proof_count": EXPECTED_DERIVED_COMPLEMENT_VALUE_PROOF_COUNT,
            "derived_complement_proofs_are_native_zero_attestations": False,
            "residual_gap_count": EXPECTED_RESIDUAL_GAP_COUNT,
            "additional_v6_only_paths_closed_as_zero": 0,
            "optional_stage_paths_retained_without_transitive_source_closure": EXPECTED_OPTIONAL_STAGE_GAP_COUNT,
            "mounted_payload_peak_zero_accepted": False,
            "all_nine_shared_resource_receipts_complete": False,
            "all_eight_derived_reconciliations_complete": False,
            "formal_v6_counter_records_issued": 0,
            "formal_v6_work_vector_issued": False,
            "formal_v6_comparison_vector_issued": False,
            "terminal_artifact_id": None,
            "campaign_occurrence_closure_id": None,
            "certificate_issued": False,
            "missing_event_inferred_zero": False,
            "legacy_v1_records_relabelled_as_v6": False,
            "production_completion_status": "BLOCKED_176_REQUIRED_PATH_GAPS",
            "central_domain_registration_completed": True,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_n_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        }

    @property
    def closure_id(self) -> str:
        if _content_id(ZERO_VALUE_CLOSURE_DOMAIN, self._payload()) != self._closure_id:
            _fail("abstract-certified zero-value closure changed after issuance")
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "zero_value_closure_id": self.closure_id}


def _exact_coverage_report(
    execution: ModelOnlyQueryExecutionV1,
    report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    source_archive: Mapping[str, bytes] | None,
) -> coverage_v1.AbstractCertifiedAccountingCoverageReportV1:
    if type(report) is not coverage_v1.AbstractCertifiedAccountingCoverageReportV1:
        _fail("zero-value closure requires the exact retained coverage report type")
    expected = coverage_v1.audit_abstract_certified_accounting_coverage_v1(
        execution, source_archive=source_archive
    )
    if (
        expected.report_id != report.report_id
        or canonical_json_bytes(expected.to_document())
        != canonical_json_bytes(report.to_document())
    ):
        _fail("coverage report belongs to another execution/source window")
    return expected


def _boundary_sites_by_stage(
    manifest: boundary_v1.ConstructionK7AllPathOperationBoundaryManifestV1,
) -> dict[str, tuple[str, ...]]:
    result: dict[str, list[str]] = {stage: [] for stage in _FORBIDDEN_STAGE_NAMES}
    for site in manifest.sites:
        stage = site.stage_kind.value
        if stage in result:
            result[stage].append(site.site_id)
    frozen = {stage: tuple(sorted(ids)) for stage, ids in result.items()}
    if any(not ids for ids in frozen.values()):
        _fail("forbidden route stage lacks a source-bound operation site")
    return frozen


def close_abstract_certified_zero_value_subset_v1(
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    *,
    source_archive: Mapping[str, bytes] | None = None,
) -> AbstractCertifiedZeroValueClosureV1:
    """Close exactly 26 sound zeros and retain all remaining typed gaps."""

    report = _exact_coverage_report(execution, coverage_report, source_archive)
    retained = coverage_v1.verify_model_only_operational_execution_v1(execution)
    vector = retained.recorded_work.work_vector
    records = {row.path: row for row in vector.records}
    manifest = boundary_v1.freeze_construction_k7_all_path_operation_boundary_manifest_v1()
    if manifest.manifest_id != report.operation_boundary_manifest_id:
        _fail("operation-boundary manifest changed after coverage report")

    zero_source_paths = tuple(
        sorted(
            row.path
            for row in report.path_gaps
            if row.code
            is coverage_v1.PathGapCodeV1.ZERO_V1_RECORD_LACKS_V6_PROFILE_NATIVE_ZERO_EVIDENCE
            and row.path != "io.mounted_bytes_peak"
        )
    )
    inactive_paths = tuple(
        sorted(
            path
            for path in zero_source_paths
            if path not in _COMPLETION_COMPLEMENTS
        )
    )
    if len(inactive_paths) != EXPECTED_NATIVE_ZERO_PROOF_COUNT:
        _fail("forbidden-route legacy zero set changed")
    window = AbstractPassExecutionWindowV1(
        _WINDOW_ISSUER,
        report.report_id,
        report.source_archive_id,
        report.operation_boundary_manifest_id,
        retained.operational_execution_id,
        retained.request_id,
        retained.worker_output_id,
        retained.model_only_result.result_id,
        retained.native_event_trace.event_trace_id,
        vector.work_vector_id,
        retained.recorded_work.native_zero_attestation.native_zero_attestation_id,
        retained.recorded_work.reconciliation_proof.reconciliation_proof_id,
        tuple((path, vector.value(path)) for path in (
            "process.exit_failures", "process.exit_successes", "process.launches"
        )),
        tuple((path, vector.value(path)) for path in (
            "route.attempts", "route.failures", "route.successes"
        )),
        tuple((path, vector.value(path)) for path in (
            "solver.attempts", "solver.failures", "solver.successes"
        )),
        tuple((path, vector.value(path)) for path in inactive_paths),
    )
    boundary_by_stage = _boundary_sites_by_stage(manifest)
    native_zero_rows: list[AbstractCertifiedZeroValueProofV1] = []
    derived_complement_rows: list[AbstractCertifiedZeroValueProofV1] = []
    residual_rows: list[AbstractCertifiedResidualGapV1] = []
    for original in report.path_gaps:
        if original.path in zero_source_paths:
            if original.legacy_v1_record_id is None or original.legacy_v1_value != 0:
                _fail("zero source path lacks its exact zero-valued V1 record")
            if original.path in _COMPLETION_COMPLEMENTS:
                supports = tuple(
                    sorted(records[path].record_id for path in _COMPLETION_COMPLEMENTS[original.path])
                )
                derived_complement_rows.append(
                    AbstractCertifiedZeroValueProofV1(
                        _PROOF_ISSUER,
                        window.window_id,
                        report.report_id,
                        original.gap_id,
                        original.path,
                        original.semantics_id,
                        original.owner,
                        original.scope,
                        original.stage_contexts,
                        ZeroValueProofKindV1.SUCCESSFUL_COMPLETION_COMPLEMENT,
                        original.legacy_v1_record_id,
                        supports,
                        (),
                    )
                )
            else:
                stage_names = {stage for stage, _disposition in original.stage_contexts}
                if not stage_names or not stage_names <= _FORBIDDEN_STAGE_NAMES:
                    _fail("zero-valued forbidden-stage path has a non-forbidden stage")
                site_ids = tuple(
                    sorted(
                        {
                            site_id
                            for stage in stage_names
                            for site_id in boundary_by_stage[stage]
                        }
                    )
                )
                native_zero_rows.append(
                    AbstractCertifiedZeroValueProofV1(
                        _PROOF_ISSUER,
                        window.window_id,
                        report.report_id,
                        original.gap_id,
                        original.path,
                        original.semantics_id,
                        original.owner,
                        original.scope,
                        original.stage_contexts,
                        ZeroValueProofKindV1.FORBIDDEN_ROUTE_STAGE_SOURCE_CLOSED,
                        original.legacy_v1_record_id,
                        (),
                        site_ids,
                    )
                )
            continue

        if original.path == "io.mounted_bytes_peak":
            code = ResidualGapCodeV1.MOUNTED_PAYLOAD_PEAK_WAS_NOT_MEASURED
        elif original.code is (
            coverage_v1.PathGapCodeV1
            .POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE
        ):
            code = (
                ResidualGapCodeV1
                .POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE
            )
        elif original.code is coverage_v1.PathGapCodeV1.NO_V1_COUNTER_LEAF_OR_EMISSION:
            dispositions = {value for _stage, value in original.stage_contexts}
            if dispositions <= {"OPTIONAL_ONCE", "OPTIONAL_REPEATABLE"}:
                code = (
                    ResidualGapCodeV1
                    .OPTIONAL_STAGE_REACHABILITY_AND_TRANSITIVE_SOURCE_CLOSURE_MISSING
                )
            elif dispositions & {"REQUIRED_ONCE", "REQUIRED_AT_LEAST_ONCE"}:
                code = ResidualGapCodeV1.REQUIRED_STAGE_OWNER_EVIDENCE_MISSING
            else:
                _fail("V6-only path has no sound residual stage disposition")
        else:
            _fail("unrecognized residual gap after exact zero subset closure")
        residual_rows.append(
            AbstractCertifiedResidualGapV1(
                _GAP_ISSUER,
                original.gap_id,
                original.path,
                original.semantics_id,
                original.stage_contexts,
                code,
                original.legacy_v1_record_id,
                original.legacy_v1_value,
            )
        )

    return AbstractCertifiedZeroValueClosureV1(
        _CLOSURE_ISSUER,
        report.report_id,
        window,
        tuple(sorted(native_zero_rows, key=lambda row: row.path)),
        tuple(sorted(derived_complement_rows, key=lambda row: row.path)),
        tuple(sorted(residual_rows, key=lambda row: row.path)),
    )


@dataclass(frozen=True, slots=True)
class AbstractCertifiedZeroValueReplayV1:
    outcome: ReplayOutcomeV1
    operational_execution_id: str
    closure: AbstractCertifiedZeroValueClosureV1 | None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "outcome", ReplayOutcomeV1(self.outcome))
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedZeroValueClosureV1Error(
                "zero-value replay outcome is invalid"
            ) from error
        _cid(self.operational_execution_id, "operational execution")
        if (
            (self.outcome is ReplayOutcomeV1.ZERO_SUBSET_CLOSED_ACCOUNTING_STILL_BLOCKED)
            != (self.closure is not None)
            or (self.outcome is ReplayOutcomeV1.DOCUMENT_BLOCKED)
            != (self.closure is None)
        ):
            _fail("zero-value replay outcome is inconsistent")

    @property
    def replay_id(self) -> str:
        return _content_id(
            REPLAY_DOMAIN,
            {
                "schema": "acfqp.construction_k7_abstract_certified_zero_value_replay.v1",
                "schema_version": SCHEMA_VERSION,
                "outcome": self.outcome.value,
                "operational_execution_id": self.operational_execution_id,
                "zero_value_closure_id": None if self.closure is None else self.closure.closure_id,
                "terminal_issued": False,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_zero_value_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "outcome": self.outcome.value,
            "operational_execution_id": self.operational_execution_id,
            "zero_value_closure_id": None if self.closure is None else self.closure.closure_id,
            "terminal_issued": False,
            "replay_id": self.replay_id,
        }


def verify_abstract_certified_zero_value_closure_document_v1(
    document: Mapping[str, Any],
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    *,
    source_archive: Mapping[str, bytes] | None = None,
) -> AbstractCertifiedZeroValueReplayV1:
    """Independently reconstruct and compare the entire revised partition."""

    expected = close_abstract_certified_zero_value_subset_v1(
        execution, coverage_report, source_archive=source_archive
    )
    if type(document) is not dict or canonical_json_bytes(document) != canonical_json_bytes(
        expected.to_document()
    ):
        return AbstractCertifiedZeroValueReplayV1(
            ReplayOutcomeV1.DOCUMENT_BLOCKED,
            expected.execution_window.operational_execution_id,
            None,
        )
    return AbstractCertifiedZeroValueReplayV1(
        ReplayOutcomeV1.ZERO_SUBSET_CLOSED_ACCOUNTING_STILL_BLOCKED,
        expected.execution_window.operational_execution_id,
        expected,
    )


__all__ = [
    "AbstractCertifiedZeroValueClosureV1",
    "AbstractCertifiedZeroValueProofV1",
    "AbstractCertifiedZeroValueReplayV1",
    "AbstractCertifiedResidualGapV1",
    "AbstractPassExecutionWindowV1",
    "ConstructionK7AbstractCertifiedZeroValueClosureV1Error",
    "ReplayOutcomeV1",
    "ResidualGapCodeV1",
    "ZeroValueProofKindV1",
    "close_abstract_certified_zero_value_subset_v1",
    "verify_abstract_certified_zero_value_closure_document_v1",
]
