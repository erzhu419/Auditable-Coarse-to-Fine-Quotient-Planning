"""Typed denominator closure for one complete query-bound campaign.

This consumer starts from a fully replayed preregistered campaign directory.
It closes the registered denominator and classifies every retained construction
terminal.  It does not recompute the scientific planner, charge campaign-level
orchestration, run economics, or authorize official execution.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_preregistered_campaign_independent_verifier_v1 as campaign_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.102"
PROFILE_KEY = "construction_k7_query_bound_campaign_denominator_closure_v1"
CLOSURE_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_V1_DOMAIN
RESULT_FILENAME = "PREREGISTERED_CAMPAIGN_RESULT.json"
ANALYSIS_FILENAME = "RETROSPECTIVE_ACCOUNTING_ANALYSIS.json"
_ISSUER = object()


class ConstructionK7QueryBoundCampaignDenominatorClosureV1Error(ValueError):
    """The registered denominator, terminal classification, or identity crossed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignDenominatorClosureV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignDenominatorClosureV1Error(
            f"{label} must be one content ID"
        ) from error


def _canonical_object(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignDenominatorClosureV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return raw, document


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignTerminalRowV1:
    occurrence_index: int
    logical_occurrence_id: str
    occurrence_row_id: str
    bundle_verification_id: str
    terminal_class: str
    terminal_code: str

    def __post_init__(self) -> None:
        if type(self.occurrence_index) is not int or self.occurrence_index <= 0:
            _fail("campaign terminal occurrence index is invalid")
        for value, label in (
            (self.logical_occurrence_id, "terminal logical occurrence"),
            (self.occurrence_row_id, "terminal occurrence row"),
            (self.bundle_verification_id, "terminal bundle verification"),
        ):
            _cid(value, label)
        allowed = {
            ("PLAN_CERTIFICATE", "ABSTRACT_CERTIFIED"),
            ("PLAN_CERTIFICATE", "LOCAL_GROUND_RECOVERY"),
            ("PLAN_CERTIFICATE", "FULL_GROUND_FALLBACK"),
            ("INFEASIBILITY_CERTIFICATE", "CACHED_EXACT_INFEASIBLE"),
            ("INFEASIBILITY_CERTIFICATE", "FULL_GROUND_EXACT_INFEASIBLE"),
            ("ATTEMPT_CLOSURE_NONCERTIFICATE", "INTEGRITY_FAILURE"),
            ("ATTEMPT_CLOSURE_NONCERTIFICATE", "PROTOCOL_FAILURE"),
            ("ATTEMPT_CLOSURE_NONCERTIFICATE", "REBUILD_REQUIRED"),
            ("ATTEMPT_CLOSURE_NONCERTIFICATE", "FALLBACK_CAP_EXHAUSTED"),
            ("ATTEMPT_CLOSURE_NONCERTIFICATE", "ATTEMPT_BUDGET_EXHAUSTED"),
        }
        if (self.terminal_class, self.terminal_code) not in allowed:
            _fail("campaign terminal class/code pair is invalid")

    def to_document(self) -> dict[str, Any]:
        return {
            "occurrence_index": self.occurrence_index,
            "logical_occurrence_id": self.logical_occurrence_id,
            "preregistered_campaign_occurrence_id": self.occurrence_row_id,
            "complete_bundle_verification_id": self.bundle_verification_id,
            "terminal_class": self.terminal_class,
            "terminal_code": self.terminal_code,
            "closure_denominator_included": True,
            "certification_denominator_included": True,
            "economics_denominator_included": True,
        }


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignDenominatorClosureV1:
    _issuer: InitVar[object]
    campaign_result_id: str
    campaign_result_bytes: bytes = field(repr=False)
    campaign_verification_id: str
    campaign_verification_document: dict[str, Any] = field(repr=False)
    preregistration_id: str
    workload_spec_id: str
    runtime_preparation_id: str
    runtime_tree_id: str
    source_closure_id: str
    accounting_analysis_id: str
    accounting_analysis_verification_id: str
    vector_prefix_ids: tuple[str, ...]
    terminal_rows: tuple[QueryBoundCampaignTerminalRowV1, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or type(self.campaign_result_bytes) is not bytes
            or not self.campaign_result_bytes
            or type(self.campaign_verification_document) is not dict
            or len(self.terminal_rows) < 2
            or tuple(row.occurrence_index for row in self.terminal_rows)
            != tuple(range(1, len(self.terminal_rows) + 1))
            or not self.vector_prefix_ids
        ):
            _fail("campaign denominator closure is caller-minted or incomplete")
        for value, label in (
            (self.campaign_result_id, "campaign result"),
            (self.campaign_verification_id, "campaign verification"),
            (self.preregistration_id, "campaign preregistration"),
            (self.workload_spec_id, "campaign workload"),
            (self.runtime_preparation_id, "runtime preparation"),
            (self.runtime_tree_id, "runtime tree"),
            (self.source_closure_id, "source closure"),
            (self.accounting_analysis_id, "accounting analysis"),
            (self.accounting_analysis_verification_id, "analysis verification"),
            *((value, "vector prefix") for value in self.vector_prefix_ids),
        ):
            _cid(value, label)
        if (
            self.campaign_verification_document.get(
                "preregistered_campaign_verification_id"
            )
            != self.campaign_verification_id
        ):
            _fail("campaign verification document crossed its ID")
        object.__setattr__(
            self,
            "_closure_id",
            content_id(CLOSURE_DOMAIN, self._payload()),
        )

    @property
    def plan_certificate_count(self) -> int:
        return sum(row.terminal_class == "PLAN_CERTIFICATE" for row in self.terminal_rows)

    @property
    def infeasibility_certificate_count(self) -> int:
        return sum(
            row.terminal_class == "INFEASIBILITY_CERTIFICATE"
            for row in self.terminal_rows
        )

    @property
    def noncertificate_count(self) -> int:
        return sum(
            row.terminal_class == "ATTEMPT_CLOSURE_NONCERTIFICATE"
            for row in self.terminal_rows
        )

    def _payload(self) -> dict[str, Any]:
        count = len(self.terminal_rows)
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_denominator_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistered_campaign_result_id": self.campaign_result_id,
            "campaign_result_sha256": hashlib.sha256(self.campaign_result_bytes).hexdigest(),
            "campaign_result_byte_count": len(self.campaign_result_bytes),
            "preregistered_campaign_verification": self.campaign_verification_document,
            "preregistered_campaign_verification_id": self.campaign_verification_id,
            "query_bound_campaign_preregistration_id": self.preregistration_id,
            "campaign_workload_spec_id": self.workload_spec_id,
            "runtime_preparation_id": self.runtime_preparation_id,
            "runtime_tree_id": self.runtime_tree_id,
            "source_closure_id": self.source_closure_id,
            "accounting_analysis_id": self.accounting_analysis_id,
            "accounting_analysis_verification_id": self.accounting_analysis_verification_id,
            "campaign_vector_prefix_ids": list(self.vector_prefix_ids),
            "terminal_rows": [row.to_document() for row in self.terminal_rows],
            "logical_occurrence_count": count,
            "closure_denominator": count,
            "certification_coverage_denominator": count,
            "economics_cost_denominator": count,
            "plan_certificate_count": self.plan_certificate_count,
            "infeasibility_certificate_count": self.infeasibility_certificate_count,
            "noncertificate_count": self.noncertificate_count,
            "construction_certificate_coverage_status": (
                "PASS" if self.noncertificate_count == 0 else "FAIL"
            ),
            "official_certificate_coverage_gate_status": "NOT_RUN",
            "all_registered_occurrences_retained": True,
            "all_occurrence_accounting_bundles_independently_replayed": True,
            "campaign_denominator_closure_issued": True,
            "scientific_planner_recomputed_by_closure": False,
            "scientific_campaign_closure_issued": False,
            "failure_path_campaign_closure_present": False,
            "campaign_orchestration_work_vector_present": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "scalar_gate_status": "NOT_RUN",
            "official_execution_allowed": False,
        }

    @property
    def closure_id(self) -> str:
        expected = content_id(CLOSURE_DOMAIN, self._payload())
        if expected != self._closure_id:
            _fail("campaign denominator closure changed after issuance")
        return expected

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query_bound_campaign_denominator_closure_id": self.closure_id,
        }


def close_query_bound_preregistered_campaign_directory_v1(
    campaign_directory: str | Path,
) -> QueryBoundCampaignDenominatorClosureV1:
    """Replay one complete directory and close its exact registered denominator."""

    root = Path(campaign_directory).resolve(strict=True)
    verification = campaign_v1.verify_query_bound_preregistered_campaign_directory_v1(
        root
    )
    result_raw, result = _canonical_object(root / RESULT_FILENAME, "campaign result")
    _analysis_raw, analysis = _canonical_object(
        root / ANALYSIS_FILENAME,
        "campaign accounting analysis",
    )
    executed = result.get("executed_occurrences")
    prefixes = analysis.get("vector_prefix_totals")
    if type(executed) is not list or type(prefixes) is not list:
        _fail("campaign result or analysis omitted closure rows")
    rows = tuple(
        QueryBoundCampaignTerminalRowV1(
            row["occurrence_index"],
            row["logical_occurrence_id"],
            row["preregistered_campaign_occurrence_id"],
            row["complete_bundle_verification_id"],
            row["construction_terminal_class"],
            row["construction_terminal_code"],
        )
        for row in executed
    )
    prefix_ids = tuple(row["campaign_vector_prefix_id"] for row in prefixes)
    if (
        tuple(row.occurrence_row_id for row in rows)
        != verification.occurrence_row_ids
        or tuple(row.bundle_verification_id for row in rows)
        != verification.bundle_verification_ids
        or result["preregistered_campaign_result_id"]
        != verification.campaign_result_id
        or result["accounting_analysis_id"] != verification.accounting_analysis_id
        or result["accounting_analysis_verification_id"]
        != verification.accounting_analysis_verification_id
    ):
        _fail("campaign closure crossed its independently replayed identities")
    return QueryBoundCampaignDenominatorClosureV1(
        _ISSUER,
        verification.campaign_result_id,
        result_raw,
        verification.verification_id,
        verification.to_document(),
        verification.preregistration_id,
        verification.workload_spec_id,
        result["runtime_preparation_id"],
        result["runtime_tree_id"],
        result["source_closure_id"],
        verification.accounting_analysis_id,
        verification.accounting_analysis_verification_id,
        prefix_ids,
        rows,
    )


__all__ = (
    "ConstructionK7QueryBoundCampaignDenominatorClosureV1Error",
    "QueryBoundCampaignDenominatorClosureV1",
    "QueryBoundCampaignTerminalRowV1",
    "close_query_bound_preregistered_campaign_directory_v1",
)
