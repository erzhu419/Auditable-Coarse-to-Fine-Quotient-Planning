"""Portable K7 campaign closure over independently replayed occurrences.

The K7 production accounting pipeline closes one exact logical occurrence.
This successor closes an ordered workload denominator without weakening the
generic Phase-3E campaign contract or treating a process-local pipeline result
as portable evidence.  Each row is recreated from the complete logical-
occurrence bytes and its original production replay inputs before the campaign
summary is issued.

The current root-cap profile contains only typed noncertificate occurrences.
Consequently this module reports campaign coverage failure and keeps counter
completeness, workload economics, scalar cost, break-even, and official
execution locked.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_k7_logical_occurrence_closure_v1 as occurrence_v1
from acfqp import construction_k7_production_accounting_pipeline_v1 as pipeline_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_CAMPAIGN_CLOSURE_SUMMARY_V1_DOMAIN,
    CONSTRUCTION_K7_CAMPAIGN_CLOSURE_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_CAMPAIGN_REGISTRATION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.33"
PROFILE_KEY = "construction_k7_campaign_closure_v1"

TERMINAL_SCOPE = "CAMPAIGN"
TERMINAL_CLASS = occurrence_v1.TERMINAL_CLASS
TERMINAL_CODE = occurrence_v1.TERMINAL_CODE
SOURCE_CAUSE = occurrence_v1.SOURCE_CAUSE

CERTIFICATE_COVERAGE_FAIL = "FAIL"
WORKLOAD_ECONOMICS_GATE_NOT_RUN = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
COUNTER_COMPLETENESS_GATE_NOT_RUN = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
SCALAR_GATE_NOT_RUN = "NOT_RUN"
EXPECTED_COUNTER_RECORD_COUNT = occurrence_v1.EXPECTED_COUNTER_RECORD_COUNT

K7_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN = (
    CONSTRUCTION_K7_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
)
K7_CAMPAIGN_REGISTRATION_V1_DOMAIN = (
    CONSTRUCTION_K7_CAMPAIGN_REGISTRATION_V1_DOMAIN
)
K7_CAMPAIGN_CLOSURE_SUMMARY_V1_DOMAIN = (
    CONSTRUCTION_K7_CAMPAIGN_CLOSURE_SUMMARY_V1_DOMAIN
)
K7_CAMPAIGN_CLOSURE_VERIFICATION_V1_DOMAIN = (
    CONSTRUCTION_K7_CAMPAIGN_CLOSURE_VERIFICATION_V1_DOMAIN
)

LOCAL_DOMAINS = frozenset(
    {
        K7_CAMPAIGN_REGISTRATION_V1_DOMAIN,
        K7_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
        K7_CAMPAIGN_CLOSURE_SUMMARY_V1_DOMAIN,
        K7_CAMPAIGN_CLOSURE_VERIFICATION_V1_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 4:  # pragma: no cover
    raise RuntimeError("K7 campaign domains must be unique")
if not LOCAL_DOMAINS.issubset(PHASE3E_DOMAIN_TAGS):  # pragma: no cover
    raise RuntimeError("K7 campaign domains must be centrally registered")

_REGISTRATION_ISSUER = object()
_ROW_ISSUER = object()
_SUMMARY_ISSUER = object()
_VERIFICATION_ISSUER = object()
_PRODUCTION_CAMPAIGN_ISSUER = object()


class ConstructionK7CampaignClosureV1Error(ValueError):
    """One occurrence, denominator row, or campaign identity failed replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CampaignClosureV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConstructionK7CampaignClosureV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("campaign closure used an unknown local domain")
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7CampaignClosureV1Error(
            f"{label} bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} bytes are noncanonical")
    return document


@dataclass(frozen=True, slots=True)
class K7CampaignRegistrationV1:
    """Immutable ordered denominator registered before campaign closure."""

    _issuer: InitVar[object]
    workload_spec_id: str
    logical_occurrence_ids: tuple[str, ...]
    _registration_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _REGISTRATION_ISSUER
            or type(self.logical_occurrence_ids) is not tuple
            or not self.logical_occurrence_ids
            or len(set(self.logical_occurrence_ids))
            != len(self.logical_occurrence_ids)
        ):
            _fail("K7 campaign registration is caller-minted, empty, or duplicated")
        _cid(self.workload_spec_id, "workload specification")
        for occurrence_id in self.logical_occurrence_ids:
            _cid(occurrence_id, "registered logical occurrence")
        object.__setattr__(
            self,
            "_registration_id",
            _local_id(K7_CAMPAIGN_REGISTRATION_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_campaign_registration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "workload_spec_id": self.workload_spec_id,
            "registered_logical_occurrence_ids": list(
                self.logical_occurrence_ids
            ),
            "registered_logical_occurrence_count": len(
                self.logical_occurrence_ids
            ),
            "registration_order_is_denominator_order": True,
            "posthoc_occurrence_deletion_allowed": False,
            "posthoc_occurrence_insertion_allowed": False,
            "official_execution_allowed": False,
        }

    @property
    def registration_id(self) -> str:
        expected = _local_id(
            K7_CAMPAIGN_REGISTRATION_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._registration_id:
            _fail("K7 campaign registration changed after issuance")
        return self._registration_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_registration_id": self.registration_id,
        }


@dataclass(frozen=True, slots=True)
class K7CampaignOccurrenceReplayInputV1:
    """Full production roots needed to replay one portable occurrence row."""

    logical_occurrence_closure_raw: bytes = field(repr=False)
    complete_bundle_verification_raw: bytes = field(repr=False)
    semantic_closure_raw: bytes = field(repr=False)
    formal_materialization_raw: bytes = field(repr=False)
    terminal_accounting_bundle_raw: bytes = field(repr=False)
    closure_replay_inputs: Mapping[str, Any] = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if any(
            type(value) is not bytes or not value
            for value in (
                self.logical_occurrence_closure_raw,
                self.complete_bundle_verification_raw,
                self.semantic_closure_raw,
                self.formal_materialization_raw,
                self.terminal_accounting_bundle_raw,
            )
        ) or type(self.closure_replay_inputs) is not dict:
            _fail("campaign occurrence replay input is incomplete")

    @classmethod
    def from_pipeline_result(
        cls,
        result: pipeline_v1.K7ProductionAccountingPipelineResultV1,
    ) -> "K7CampaignOccurrenceReplayInputV1":
        if type(result) is not pipeline_v1.K7ProductionAccountingPipelineResultV1:
            _fail("campaign replay input requires one exact pipeline result")
        return cls(
            result.logical_occurrence_closure.canonical_bytes,
            result.complete_verification.canonical_bytes,
            result.semantic_closure.canonical_bytes,
            result.formal_materialization.canonical_bytes,
            result.terminal_accounting.canonical_bytes,
            result.closure_replay_inputs,
        )


@dataclass(frozen=True, slots=True)
class K7ProductionAccountingCampaignOccurrenceInputV1:
    """One exact production-root input consumed after registration."""

    replay_roots: Mapping[str, Any] = field(repr=False, compare=False)
    source_archive_raw: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.replay_roots) is not dict
            or type(self.source_archive_raw) is not bytes
            or not self.source_archive_raw
        ):
            _fail("production campaign occurrence input is incomplete")


@dataclass(frozen=True, slots=True)
class K7CampaignOccurrenceRowV1:
    _issuer: InitVar[object]
    occurrence_index: int
    logical_occurrence_id: str
    logical_occurrence_closure_bundle_id: str
    logical_occurrence_closure_id: str
    logical_occurrence_closure_verification_id: str
    logical_occurrence_work_sum_id: str
    route_attempt_id: str
    work_vector_id: str
    comparison_vector_id: str
    counter_record_count: int
    _row_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ROW_ISSUER
            or type(self.occurrence_index) is not int
            or self.occurrence_index <= 0
            or type(self.counter_record_count) is not int
            or self.counter_record_count != EXPECTED_COUNTER_RECORD_COUNT
        ):
            _fail("K7 campaign occurrence row is caller-minted or incomplete")
        for value, label in (
            (self.logical_occurrence_id, "logical occurrence"),
            (self.logical_occurrence_closure_bundle_id, "occurrence bundle"),
            (self.logical_occurrence_closure_id, "occurrence closure"),
            (
                self.logical_occurrence_closure_verification_id,
                "occurrence verification",
            ),
            (self.logical_occurrence_work_sum_id, "occurrence work sum"),
            (self.route_attempt_id, "route attempt"),
            (self.work_vector_id, "work vector"),
            (self.comparison_vector_id, "comparison vector"),
        ):
            _cid(value, label)
        object.__setattr__(
            self,
            "_row_id",
            _local_id(K7_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_campaign_occurrence_row.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_index": self.occurrence_index,
            "logical_occurrence_id": self.logical_occurrence_id,
            "logical_occurrence_closure_bundle_id": (
                self.logical_occurrence_closure_bundle_id
            ),
            "logical_occurrence_closure_id": self.logical_occurrence_closure_id,
            "logical_occurrence_closure_verification_id": (
                self.logical_occurrence_closure_verification_id
            ),
            "logical_occurrence_work_sum_id": self.logical_occurrence_work_sum_id,
            "route_attempt_id": self.route_attempt_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "counter_record_count": self.counter_record_count,
            "route_attempt_count": 1,
            "rebuild_count": 0,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "specific_cause": SOURCE_CAUSE,
            "certificate_covered": False,
            "closure_denominator_included": True,
            "certification_denominator_included": True,
            "economics_denominator_included": True,
        }

    @property
    def row_id(self) -> str:
        expected = _local_id(
            K7_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._row_id:
            _fail("K7 campaign occurrence row changed after issuance")
        return self._row_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_occurrence_row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class K7CampaignClosureSummaryV1:
    _issuer: InitVar[object]
    registration: K7CampaignRegistrationV1 = field(
        repr=False,
        compare=False,
    )
    rows: tuple[K7CampaignOccurrenceRowV1, ...]
    _summary_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _SUMMARY_ISSUER
            or type(self.registration) is not K7CampaignRegistrationV1
            or type(self.rows) is not tuple
            or not self.rows
            or any(type(row) is not K7CampaignOccurrenceRowV1 for row in self.rows)
            or tuple(row.occurrence_index for row in self.rows)
            != tuple(range(1, len(self.rows) + 1))
            or tuple(row.logical_occurrence_id for row in self.rows)
            != self.registration.logical_occurrence_ids
        ):
            _fail("K7 campaign summary is caller-minted, empty, or noncanonical")
        self.registration.registration_id
        for values, label in (
            (
                tuple(row.logical_occurrence_id for row in self.rows),
                "logical occurrence",
            ),
            (
                tuple(
                    row.logical_occurrence_closure_bundle_id for row in self.rows
                ),
                "occurrence bundle",
            ),
            (
                tuple(
                    row.logical_occurrence_closure_verification_id
                    for row in self.rows
                ),
                "occurrence verification",
            ),
            (tuple(row.work_vector_id for row in self.rows), "work vector"),
            (tuple(row.row_id for row in self.rows), "campaign row"),
        ):
            if len(set(values)) != len(values):
                _fail(f"K7 campaign repeats one {label}")
        object.__setattr__(
            self,
            "_summary_id",
            _local_id(K7_CAMPAIGN_CLOSURE_SUMMARY_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        count = len(self.rows)
        return {
            "schema": "acfqp.construction_k7_campaign_closure_summary.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_registration": self.registration.to_document(),
            "campaign_registration_id": self.registration.registration_id,
            "workload_spec_id": self.registration.workload_spec_id,
            "rows": [row.to_document() for row in self.rows],
            "logical_occurrence_count": count,
            "closure_denominator": count,
            "certification_coverage_denominator": count,
            "economics_cost_denominator": count,
            "total_route_attempt_count": count,
            "plan_certificate_count": 0,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": count,
            "official_run_valid": True,
            "certificate_coverage_gate": CERTIFICATE_COVERAGE_FAIL,
            "all_registered_occurrences_retained": True,
            "campaign_closure_issued": True,
            "official_execution_allowed": False,
            "counter_completeness_gate_status": (
                COUNTER_COMPLETENESS_GATE_NOT_RUN
            ),
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_NOT_RUN,
            "scalar_gate_status": SCALAR_GATE_NOT_RUN,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def summary_id(self) -> str:
        expected = _local_id(
            K7_CAMPAIGN_CLOSURE_SUMMARY_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._summary_id:
            _fail("K7 campaign summary changed after issuance")
        return self._summary_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_closure_summary_id": self.summary_id}


@dataclass(frozen=True, slots=True)
class K7CampaignClosureVerificationV1:
    _issuer: InitVar[object]
    verified_summary: K7CampaignClosureSummaryV1 = field(
        repr=False,
        compare=False,
    )
    occurrence_verification_ids: tuple[str, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.verified_summary) is not K7CampaignClosureSummaryV1
            or type(self.occurrence_verification_ids) is not tuple
            or self.occurrence_verification_ids
            != tuple(
                row.logical_occurrence_closure_verification_id
                for row in self.verified_summary.rows
            )
        ):
            _fail("K7 campaign verification is caller-minted or crossed")
        object.__setattr__(
            self,
            "_verification_id",
            _local_id(
                K7_CAMPAIGN_CLOSURE_VERIFICATION_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        summary_raw = self.verified_summary.canonical_bytes
        return {
            "schema": "acfqp.construction_k7_campaign_closure_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_registration_id": (
                self.verified_summary.registration.registration_id
            ),
            "campaign_closure_summary_id": self.verified_summary.summary_id,
            "campaign_closure_summary_sha256": hashlib.sha256(
                summary_raw
            ).hexdigest(),
            "campaign_closure_summary_byte_count": len(summary_raw),
            "logical_occurrence_closure_verification_ids": list(
                self.occurrence_verification_ids
            ),
            "logical_occurrence_count": len(self.occurrence_verification_ids),
            "all_occurrences_independently_replayed": True,
            "campaign_denominators_replayed": True,
            "certificate_coverage_replayed": True,
            "official_execution_allowed": False,
            "counter_completeness_gate_status": (
                COUNTER_COMPLETENESS_GATE_NOT_RUN
            ),
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_NOT_RUN,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def verification_id(self) -> str:
        expected = _local_id(
            K7_CAMPAIGN_CLOSURE_VERIFICATION_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._verification_id:
            _fail("K7 campaign verification changed after issuance")
        return self._verification_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_closure_verification_id": self.verification_id,
        }


@dataclass(frozen=True, slots=True)
class K7ProductionAccountingCampaignResultV1:
    """Process-local all-or-nothing result for an ordered K7 campaign."""

    _issuer: InitVar[object]
    registration: K7CampaignRegistrationV1 = field(repr=False)
    occurrence_results: tuple[
        pipeline_v1.K7ProductionAccountingPipelineResultV1,
        ...,
    ] = field(repr=False, compare=False)
    campaign_summary: K7CampaignClosureSummaryV1
    campaign_verification: K7CampaignClosureVerificationV1

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PRODUCTION_CAMPAIGN_ISSUER
            or type(self.registration) is not K7CampaignRegistrationV1
            or type(self.occurrence_results) is not tuple
            or not self.occurrence_results
            or any(
                type(row)
                is not pipeline_v1.K7ProductionAccountingPipelineResultV1
                for row in self.occurrence_results
            )
            or type(self.campaign_summary) is not K7CampaignClosureSummaryV1
            or type(self.campaign_verification)
            is not K7CampaignClosureVerificationV1
        ):
            _fail("production K7 campaign result is caller-minted or incomplete")
        occurrence_ids = tuple(
            row.logical_occurrence_closure.occurrence_closure.logical_occurrence_id
            for row in self.occurrence_results
        )
        if (
            occurrence_ids != self.registration.logical_occurrence_ids
            or self.campaign_summary.registration.registration_id
            != self.registration.registration_id
            or self.campaign_verification.verified_summary.to_document()
            != self.campaign_summary.to_document()
            or tuple(
                row.logical_occurrence_closure_verification_id
                for row in self.campaign_summary.rows
            )
            != tuple(
                row.logical_occurrence_verification.verification_id
                for row in self.occurrence_results
            )
        ):
            _fail("production K7 campaign identities or denominator crossed")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_production_accounting_campaign_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_registration_id": self.registration.registration_id,
            "occurrence_pipeline_results": [
                row.to_document() for row in self.occurrence_results
            ],
            "campaign_closure_summary_id": self.campaign_summary.summary_id,
            "campaign_closure_verification_id": (
                self.campaign_verification.verification_id
            ),
            "logical_occurrence_count": len(self.occurrence_results),
            "all_registered_occurrences_executed": True,
            "all_occurrences_independently_replayed": True,
            "campaign_denominator_closed": True,
            "certificate_coverage_gate": CERTIFICATE_COVERAGE_FAIL,
            "counter_completeness_gate_status": (
                COUNTER_COMPLETENESS_GATE_NOT_RUN
            ),
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_NOT_RUN,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }


def _row_from_verification(
    *,
    occurrence_index: int,
    verification: occurrence_v1.K7LogicalOccurrenceClosureVerificationV1,
) -> K7CampaignOccurrenceRowV1:
    if type(verification) is not (
        occurrence_v1.K7LogicalOccurrenceClosureVerificationV1
    ):
        _fail("campaign row requires exact logical-occurrence verification")
    verification.verification_id
    bundle = verification.verified_bundle
    closure = bundle.occurrence_closure
    work_sum = bundle.occurrence_work_sum
    return K7CampaignOccurrenceRowV1(
        _ROW_ISSUER,
        occurrence_index,
        closure.logical_occurrence_id,
        bundle.bundle_id,
        closure.closure_id,
        verification.verification_id,
        work_sum.occurrence_work_sum_id,
        closure.route_attempt_id,
        work_sum.work_vector.work_vector_id,
        work_sum.comparison_vector.comparison_vector_id,
        len(work_sum.counter_record_ids),
    )


def preregister_k7_campaign_v1(
    *,
    workload_spec_id: str,
    logical_occurrence_ids: Sequence[str],
) -> K7CampaignRegistrationV1:
    """Freeze the complete ordered occurrence denominator."""

    return K7CampaignRegistrationV1(
        _REGISTRATION_ISSUER,
        workload_spec_id,
        tuple(logical_occurrence_ids),
    )


def verify_k7_campaign_registration_bytes_v1(
    raw: bytes,
) -> K7CampaignRegistrationV1:
    """Replay portable campaign registration bytes."""

    document = _canonical_object(raw, "K7 campaign registration")
    expected_fields = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "workload_spec_id",
        "registered_logical_occurrence_ids",
        "registered_logical_occurrence_count",
        "registration_order_is_denominator_order",
        "posthoc_occurrence_deletion_allowed",
        "posthoc_occurrence_insertion_allowed",
        "official_execution_allowed",
        "campaign_registration_id",
    }
    if (
        set(document) != expected_fields
        or type(document.get("registered_logical_occurrence_ids")) is not list
    ):
        _fail("K7 campaign registration schema changed")
    expected = preregister_k7_campaign_v1(
        workload_spec_id=document.get("workload_spec_id"),
        logical_occurrence_ids=document["registered_logical_occurrence_ids"],
    )
    if document != expected.to_document():
        _fail("K7 campaign registration differs from exact replay")
    return expected


def issue_k7_campaign_closure_summary_v1(
    *,
    registration: K7CampaignRegistrationV1,
    occurrence_verifications: Sequence[
        occurrence_v1.K7LogicalOccurrenceClosureVerificationV1
    ],
) -> K7CampaignClosureSummaryV1:
    """Issue one ordered campaign denominator from verified occurrences."""

    if type(registration) is not K7CampaignRegistrationV1:
        _fail("campaign summary requires exact registration authority")
    registration.registration_id
    rows = tuple(occurrence_verifications)
    if not rows:
        _fail("K7 campaign cannot omit every registered occurrence")
    return K7CampaignClosureSummaryV1(
        _SUMMARY_ISSUER,
        registration,
        tuple(
            _row_from_verification(
                occurrence_index=index,
                verification=verification,
            )
            for index, verification in enumerate(rows, start=1)
        ),
    )


def issue_k7_campaign_closure_from_pipeline_results_v1(
    *,
    registration: K7CampaignRegistrationV1,
    pipeline_results: Sequence[
        pipeline_v1.K7ProductionAccountingPipelineResultV1
    ],
) -> K7CampaignClosureSummaryV1:
    """Bind the one-shot accounting outputs directly into campaign rows."""

    results = tuple(pipeline_results)
    if not results or any(
        type(row) is not pipeline_v1.K7ProductionAccountingPipelineResultV1
        for row in results
    ):
        _fail("campaign requires exact one-shot accounting results")
    return issue_k7_campaign_closure_summary_v1(
        registration=registration,
        occurrence_verifications=tuple(
            row.logical_occurrence_verification for row in results
        ),
    )


def verify_k7_campaign_closure_summary_bytes_v1(
    *,
    raw: bytes,
    campaign_registration_raw: bytes,
    occurrence_replay_inputs: Sequence[K7CampaignOccurrenceReplayInputV1],
) -> K7CampaignClosureVerificationV1:
    """Replay every occurrence from complete roots and verify campaign bytes."""

    claimed = _canonical_object(raw, "K7 campaign closure summary")
    registration = verify_k7_campaign_registration_bytes_v1(
        campaign_registration_raw
    )
    inputs = tuple(occurrence_replay_inputs)
    if not inputs or any(
        type(row) is not K7CampaignOccurrenceReplayInputV1 for row in inputs
    ):
        _fail("campaign verification requires typed complete occurrence inputs")
    try:
        occurrence_verifications = tuple(
            occurrence_v1.verify_k7_logical_occurrence_closure_bundle_bytes_v1(
                raw=row.logical_occurrence_closure_raw,
                complete_bundle_verification_raw=(
                    row.complete_bundle_verification_raw
                ),
                semantic_closure_raw=row.semantic_closure_raw,
                formal_materialization_raw=row.formal_materialization_raw,
                terminal_accounting_bundle_raw=(
                    row.terminal_accounting_bundle_raw
                ),
                closure_replay_inputs=row.closure_replay_inputs,
            )
            for row in inputs
        )
    except Exception as error:
        raise ConstructionK7CampaignClosureV1Error(
            "one campaign occurrence failed complete independent replay"
        ) from error
    expected = issue_k7_campaign_closure_summary_v1(
        registration=registration,
        occurrence_verifications=occurrence_verifications,
    )
    if claimed != expected.to_document():
        _fail("K7 campaign closure summary differs from replayed occurrences")
    return K7CampaignClosureVerificationV1(
        _VERIFICATION_ISSUER,
        expected,
        tuple(row.verification_id for row in occurrence_verifications),
    )


def verify_k7_campaign_closure_verification_bytes_v1(
    *,
    raw: bytes,
    campaign_summary_raw: bytes,
    campaign_registration_raw: bytes,
    occurrence_replay_inputs: Sequence[K7CampaignOccurrenceReplayInputV1],
) -> K7CampaignClosureVerificationV1:
    """Replay a transported campaign verification from the same complete roots."""

    claimed = _canonical_object(raw, "K7 campaign closure verification")
    expected = verify_k7_campaign_closure_summary_bytes_v1(
        raw=campaign_summary_raw,
        campaign_registration_raw=campaign_registration_raw,
        occurrence_replay_inputs=occurrence_replay_inputs,
    )
    if claimed != expected.to_document():
        _fail("K7 campaign verification differs from complete occurrence replay")
    return expected


def run_k7_production_accounting_campaign_v1(
    *,
    registration: K7CampaignRegistrationV1,
    occurrence_inputs: Sequence[
        K7ProductionAccountingCampaignOccurrenceInputV1
    ],
) -> K7ProductionAccountingCampaignResultV1:
    """Execute and independently replay every preregistered occurrence."""

    if type(registration) is not K7CampaignRegistrationV1:
        _fail("production campaign requires exact registration authority")
    registration.registration_id
    inputs = tuple(occurrence_inputs)
    if (
        len(inputs) != len(registration.logical_occurrence_ids)
        or not inputs
        or any(
            type(row) is not K7ProductionAccountingCampaignOccurrenceInputV1
            for row in inputs
        )
    ):
        _fail("production campaign inputs differ from registered denominator")
    try:
        occurrence_results = tuple(
            pipeline_v1.run_k7_production_accounting_pipeline_v1(
                replay_roots=dict(row.replay_roots),
                source_archive_raw=row.source_archive_raw,
            )
            for row in inputs
        )
        actual_occurrence_ids = tuple(
            row.logical_occurrence_closure.occurrence_closure
            .logical_occurrence_id
            for row in occurrence_results
        )
        if actual_occurrence_ids != registration.logical_occurrence_ids:
            _fail("executed occurrence identities differ from registration")
        summary = issue_k7_campaign_closure_from_pipeline_results_v1(
            registration=registration,
            pipeline_results=occurrence_results,
        )
        replay_inputs = tuple(
            K7CampaignOccurrenceReplayInputV1.from_pipeline_result(row)
            for row in occurrence_results
        )
        verification = verify_k7_campaign_closure_summary_bytes_v1(
            raw=summary.canonical_bytes,
            campaign_registration_raw=registration.canonical_bytes,
            occurrence_replay_inputs=replay_inputs,
        )
    except ConstructionK7CampaignClosureV1Error:
        raise
    except Exception as error:
        raise ConstructionK7CampaignClosureV1Error(
            "production campaign failed complete accounting replay"
        ) from error
    return K7ProductionAccountingCampaignResultV1(
        _PRODUCTION_CAMPAIGN_ISSUER,
        registration,
        occurrence_results,
        summary,
        verification,
    )


def replay_k7_production_accounting_campaign_v1(
    claimed: Any,
    *,
    registration: K7CampaignRegistrationV1,
    occurrence_inputs: Sequence[
        K7ProductionAccountingCampaignOccurrenceInputV1
    ],
) -> K7ProductionAccountingCampaignResultV1:
    """Re-execute a process-local campaign claim from preregistered roots."""

    if type(claimed) is not K7ProductionAccountingCampaignResultV1:
        _fail("production campaign replay requires one exact issued result")
    expected = run_k7_production_accounting_campaign_v1(
        registration=registration,
        occurrence_inputs=occurrence_inputs,
    )
    if claimed.to_document() != expected.to_document():
        _fail("production campaign result differs from full replay")
    return expected


__all__ = (
    "CERTIFICATE_COVERAGE_FAIL",
    "COUNTER_COMPLETENESS_GATE_NOT_RUN",
    "ConstructionK7CampaignClosureV1Error",
    "EXPECTED_COUNTER_RECORD_COUNT",
    "K7CampaignClosureSummaryV1",
    "K7CampaignClosureVerificationV1",
    "K7CampaignOccurrenceReplayInputV1",
    "K7CampaignOccurrenceRowV1",
    "K7CampaignRegistrationV1",
    "K7ProductionAccountingCampaignOccurrenceInputV1",
    "K7ProductionAccountingCampaignResultV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCALAR_GATE_NOT_RUN",
    "SCHEMA_VERSION",
    "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
    "issue_k7_campaign_closure_from_pipeline_results_v1",
    "issue_k7_campaign_closure_summary_v1",
    "preregister_k7_campaign_v1",
    "replay_k7_production_accounting_campaign_v1",
    "run_k7_production_accounting_campaign_v1",
    "verify_k7_campaign_closure_summary_bytes_v1",
    "verify_k7_campaign_closure_verification_bytes_v1",
    "verify_k7_campaign_registration_bytes_v1",
)
