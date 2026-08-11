"""Independent replay of query-bound campaign denominator closures."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_preregistered_campaign_independent_verifier_v1 as campaign_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_VERIFICATION_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_VERIFICATION_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.102"
PRODUCER_PROFILE_KEY = "construction_k7_query_bound_campaign_denominator_closure_v1"
PROFILE_KEY = (
    "construction_k7_query_bound_campaign_denominator_closure_independent_verifier_v1"
)
CLOSURE_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_V1_DOMAIN
VERIFICATION_PROFILE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_VERIFICATION_PROFILE_V1_DOMAIN
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_VERIFICATION_V1_DOMAIN
)
RESULT_FILENAME = "PREREGISTERED_CAMPAIGN_RESULT.json"
ANALYSIS_FILENAME = "RETROSPECTIVE_ACCOUNTING_ANALYSIS.json"
_ISSUER = object()
_TERMINAL_PAIRS = {
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


class ConstructionK7QueryBoundCampaignDenominatorClosureIndependentVerifierV1Error(
    ValueError
):
    """The closure differs from an independent replay of its campaign directory."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignDenominatorClosureIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignDenominatorClosureIndependentVerifierV1Error(
            f"{label} must be one content ID"
        ) from error


def _canonical_bytes(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignDenominatorClosureIndependentVerifierV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _canonical_file(root: Path, name: str, label: str) -> tuple[bytes, dict[str, Any]]:
    path = root / name
    if path.is_symlink() or not path.is_file():
        _fail(f"{label} is absent or not a regular file")
    raw = path.read_bytes()
    return raw, _canonical_bytes(raw, label)


def _terminal_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "occurrence_index": row["occurrence_index"],
        "logical_occurrence_id": row["logical_occurrence_id"],
        "preregistered_campaign_occurrence_id": row[
            "preregistered_campaign_occurrence_id"
        ],
        "complete_bundle_verification_id": row["complete_bundle_verification_id"],
        "terminal_class": row["construction_terminal_class"],
        "terminal_code": row["construction_terminal_code"],
        "closure_denominator_included": True,
        "certification_denominator_included": True,
        "economics_denominator_included": True,
    }


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignDenominatorClosureVerificationV1:
    _issuer: InitVar[object]
    verification_profile_id: str
    closure_id: str
    closure_bytes_sha256: str
    closure_byte_count: int
    campaign_result_id: str
    campaign_verification_id: str
    preregistration_id: str
    workload_spec_id: str
    occurrence_row_ids: tuple[str, ...]
    bundle_verification_ids: tuple[str, ...]
    vector_prefix_ids: tuple[str, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or len(self.occurrence_row_ids) < 2
            or len(self.bundle_verification_ids) != len(self.occurrence_row_ids)
            or not self.vector_prefix_ids
            or type(self.closure_byte_count) is not int
            or self.closure_byte_count <= 0
        ):
            _fail("campaign closure verification is caller-minted or incomplete")
        for value, label in (
            (self.verification_profile_id, "verification profile"),
            (self.closure_id, "denominator closure"),
            (self.closure_bytes_sha256, "closure bytes"),
            (self.campaign_result_id, "campaign result"),
            (self.campaign_verification_id, "campaign verification"),
            (self.preregistration_id, "campaign preregistration"),
            (self.workload_spec_id, "campaign workload"),
            *((value, "occurrence row") for value in self.occurrence_row_ids),
            *((value, "bundle verification") for value in self.bundle_verification_ids),
            *((value, "vector prefix") for value in self.vector_prefix_ids),
        ):
            _cid(value, label)
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_denominator_closure_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile_id": self.verification_profile_id,
            "query_bound_campaign_denominator_closure_id": self.closure_id,
            "closure_bytes_sha256": self.closure_bytes_sha256,
            "closure_byte_count": self.closure_byte_count,
            "preregistered_campaign_result_id": self.campaign_result_id,
            "preregistered_campaign_verification_id": self.campaign_verification_id,
            "query_bound_campaign_preregistration_id": self.preregistration_id,
            "campaign_workload_spec_id": self.workload_spec_id,
            "preregistered_campaign_occurrence_ids": list(self.occurrence_row_ids),
            "complete_bundle_verification_ids": list(self.bundle_verification_ids),
            "campaign_vector_prefix_ids": list(self.vector_prefix_ids),
            "campaign_directory_independently_replayed": True,
            "terminal_counts_recomputed": True,
            "all_denominators_recomputed": True,
            "construction_certificate_coverage_recomputed": True,
            "official_certificate_coverage_gate_status": "NOT_RUN",
            "producer_modules_imported": False,
            "scientific_planner_recomputed_by_this_verifier": False,
            "scientific_campaign_closure_issued": False,
            "campaign_orchestration_work_vector_present": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        expected = content_id(VERIFICATION_DOMAIN, self._payload())
        if expected != self._verification_id:
            _fail("campaign closure verification changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query_bound_campaign_denominator_closure_verification_id": (
                self.verification_id
            ),
        }


def verify_query_bound_campaign_denominator_closure_bytes_v1(
    closure_bytes: bytes,
    *,
    campaign_directory: str | Path,
) -> QueryBoundCampaignDenominatorClosureVerificationV1:
    """Recompute the complete closure from bytes and its campaign directory."""

    claimed = _canonical_bytes(closure_bytes, "campaign denominator closure")
    root = Path(campaign_directory).resolve(strict=True)
    campaign_verification = (
        campaign_v1.verify_query_bound_preregistered_campaign_directory_v1(root)
    )
    result_raw, result = _canonical_file(root, RESULT_FILENAME, "campaign result")
    _analysis_raw, analysis = _canonical_file(
        root,
        ANALYSIS_FILENAME,
        "campaign accounting analysis",
    )
    rows = [_terminal_row(row) for row in result["executed_occurrences"]]
    count = len(rows)
    if (
        result.get("preregistered_campaign_result_id")
        != campaign_verification.campaign_result_id
        or result.get("query_bound_campaign_preregistration_id")
        != campaign_verification.preregistration_id
        or result.get("campaign_workload_spec_id")
        != campaign_verification.workload_spec_id
        or result.get("accounting_analysis_id")
        != campaign_verification.accounting_analysis_id
        or result.get("accounting_analysis_verification_id")
        != campaign_verification.accounting_analysis_verification_id
        or analysis.get("query_bound_campaign_analysis_id")
        != campaign_verification.accounting_analysis_id
        or tuple(row["preregistered_campaign_occurrence_id"] for row in rows)
        != campaign_verification.occurrence_row_ids
        or tuple(row["complete_bundle_verification_id"] for row in rows)
        != campaign_verification.bundle_verification_ids
        or any(
            (row["terminal_class"], row["terminal_code"]) not in _TERMINAL_PAIRS
            for row in rows
        )
    ):
        _fail("campaign files changed after their independent replay")
    plan_count = sum(row["terminal_class"] == "PLAN_CERTIFICATE" for row in rows)
    infeasible_count = sum(
        row["terminal_class"] == "INFEASIBILITY_CERTIFICATE" for row in rows
    )
    noncertificate_count = sum(
        row["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE" for row in rows
    )
    prefix_ids = tuple(
        row["campaign_vector_prefix_id"] for row in analysis["vector_prefix_totals"]
    )
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_denominator_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "preregistered_campaign_result_id": campaign_verification.campaign_result_id,
        "campaign_result_sha256": hashlib.sha256(result_raw).hexdigest(),
        "campaign_result_byte_count": len(result_raw),
        "preregistered_campaign_verification": campaign_verification.to_document(),
        "preregistered_campaign_verification_id": campaign_verification.verification_id,
        "query_bound_campaign_preregistration_id": campaign_verification.preregistration_id,
        "campaign_workload_spec_id": campaign_verification.workload_spec_id,
        "runtime_preparation_id": result["runtime_preparation_id"],
        "runtime_tree_id": result["runtime_tree_id"],
        "source_closure_id": result["source_closure_id"],
        "accounting_analysis_id": campaign_verification.accounting_analysis_id,
        "accounting_analysis_verification_id": (
            campaign_verification.accounting_analysis_verification_id
        ),
        "campaign_vector_prefix_ids": list(prefix_ids),
        "terminal_rows": rows,
        "logical_occurrence_count": count,
        "closure_denominator": count,
        "certification_coverage_denominator": count,
        "economics_cost_denominator": count,
        "plan_certificate_count": plan_count,
        "infeasibility_certificate_count": infeasible_count,
        "noncertificate_count": noncertificate_count,
        "construction_certificate_coverage_status": (
            "PASS" if noncertificate_count == 0 else "FAIL"
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
    closure_id = content_id(CLOSURE_DOMAIN, payload)
    expected = {
        **payload,
        "query_bound_campaign_denominator_closure_id": closure_id,
    }
    if claimed != expected:
        _fail("campaign denominator closure differs from independent replay")
    profile_payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_denominator_closure_verification_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "producer_import_forbidden": True,
        "complete_campaign_directory_replay_required": True,
        "terminal_count_recomputation_required": True,
        "denominator_recomputation_required": True,
        "scientific_planner_recomputation_required": False,
        "official_execution_allowed": False,
    }
    profile_id = content_id(VERIFICATION_PROFILE_DOMAIN, profile_payload)
    return QueryBoundCampaignDenominatorClosureVerificationV1(
        _ISSUER,
        profile_id,
        closure_id,
        hashlib.sha256(closure_bytes).hexdigest(),
        len(closure_bytes),
        campaign_verification.campaign_result_id,
        campaign_verification.verification_id,
        campaign_verification.preregistration_id,
        campaign_verification.workload_spec_id,
        campaign_verification.occurrence_row_ids,
        campaign_verification.bundle_verification_ids,
        prefix_ids,
    )


__all__ = (
    "ConstructionK7QueryBoundCampaignDenominatorClosureIndependentVerifierV1Error",
    "QueryBoundCampaignDenominatorClosureVerificationV1",
    "verify_query_bound_campaign_denominator_closure_bytes_v1",
)
