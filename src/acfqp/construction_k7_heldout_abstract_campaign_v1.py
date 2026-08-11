"""Preregister and close one held-out abstract-model campaign occurrence.

The campaign spec is durably committed before the owner-accounted planner
replay starts.  Its only occurrence then contributes exactly one row to the
closure, certificate-coverage, and future-economics denominators.  The row
references the formal abstract-only WorkVector chain; no failed or expensive
occurrence can be removed from a denominator by this module.

This is a construction campaign.  It does not run either official Gate and it
does not define a scalar cost or break-even point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, NoReturn

from acfqp.accounting_v1 import RouteKindEnum, SHARED_AXES
from acfqp import construction_k7_heldout_abstract_occurrence_accounting_v1 as occurrence_v1
from acfqp import construction_k7_heldout_overlay_abstract_reuse_v1 as reuse_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.124"
PROFILE_KEY = "construction_k7_heldout_abstract_campaign_v1"
PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
)
OCCURRENCE_ROW_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
)
CLOSURE_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_CLOSURE_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {PREREGISTRATION_DOMAIN, OCCURRENCE_ROW_DOMAIN, CLOSURE_DOMAIN, RESULT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("held-out campaign domains are not central")

PREREGISTRATION_FILENAME = "0001_PREREGISTRATION.json"
OCCURRENCE_ROW_FILENAME = "0002_OCCURRENCE_ROW.json"
CLOSURE_FILENAME = "0003_CAMPAIGN_CLOSURE.json"
OCCURRENCE_OUTPUT_DIRECTORY = "occurrence-0001"


class ConstructionK7HeldoutAbstractCampaignV1Error(RuntimeError):
    """Campaign preregistration, execution, denominator, or commit failed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutAbstractCampaignV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutAbstractCampaignV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class HeldoutAbstractCampaignPreregistrationV1:
    occurrence_id: str
    occurrence_ordinal: int
    threshold_profile_id: str
    reuse_result_id: str
    source_overlay_id: str
    quotient_model_id: str
    fresh_query_id: str
    fresh_plan_id: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "preregistered occurrence"),
            (self.threshold_profile_id, "preregistered threshold"),
            (self.reuse_result_id, "preregistered held-out result"),
            (self.source_overlay_id, "preregistered epoch"),
            (self.quotient_model_id, "preregistered model"),
            (self.fresh_query_id, "preregistered query"),
            (self.fresh_plan_id, "preregistered plan"),
        ):
            _cid(value, label)
        if type(self.occurrence_ordinal) is not int or self.occurrence_ordinal <= 0:
            _fail("campaign query ordinal must be positive")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_campaign_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_specs": [
                {
                    "occurrence_id": self.occurrence_id,
                    "occurrence_ordinal": self.occurrence_ordinal,
                    "threshold_profile_id": self.threshold_profile_id,
                    "heldout_abstract_reuse_result_id": self.reuse_result_id,
                    "source_overlay_id": self.source_overlay_id,
                    "quotient_model_id": self.quotient_model_id,
                    "fresh_query_id": self.fresh_query_id,
                    "fresh_plan_id": self.fresh_plan_id,
                    "expected_route_kind": RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE.value,
                    "expected_terminal_class": "PLAN_CERTIFICATE",
                    "expected_terminal_code": "ABSTRACT_CERTIFIED",
                }
            ],
            "registered_logical_occurrence_count": 1,
            "preregistration_committed_before_accounting_execution": True,
            "denominator_row_deletion_allowed": False,
            "rebuild_allowed": False,
            "max_route_attempts_per_logical_occurrence": 1,
            "official_execution_allowed": False,
        }

    @property
    def preregistration_id(self) -> str:
        return content_id(PREREGISTRATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_preregistration_id": self.preregistration_id}


@dataclass(frozen=True, slots=True)
class HeldoutAbstractCampaignOccurrenceRowV1:
    preregistration_id: str
    occurrence_id: str
    occurrence_accounting_bundle_id: str
    output_commit_id: str
    work_vector_id: str
    comparison_vector_id: str
    actual_projection_proof_id: str
    occurrence_bundle_bytes: bytes = field(repr=False)
    fixed_point_result_bytes: bytes = field(repr=False)
    output_commit_bytes: bytes = field(repr=False)
    comparison_values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.preregistration_id, "row preregistration"),
            (self.occurrence_id, "row occurrence"),
            (self.occurrence_accounting_bundle_id, "row bundle"),
            (self.output_commit_id, "row output commit"),
            (self.work_vector_id, "row WorkVector"),
            (self.comparison_vector_id, "row ComparisonVector"),
            (self.actual_projection_proof_id, "row projection proof"),
        ):
            _cid(value, label)
        if (
            tuple(axis for axis, _value in self.comparison_values) != SHARED_AXES
            or any(type(value) is not int or value < 0 for _axis, value in self.comparison_values)
        ):
            _fail("campaign occurrence comparison vector changed")
        embedded = []
        for raw, label in (
            (self.occurrence_bundle_bytes, "occurrence bundle"),
            (self.fixed_point_result_bytes, "fixed-point result"),
            (self.output_commit_bytes, "output commit"),
        ):
            if type(raw) is not bytes:
                _fail(f"embedded {label} must be canonical bytes")
            document = loads_canonical_json(raw)
            if canonical_json_bytes(document) != raw or type(document) is not dict:
                _fail(f"embedded {label} is not canonical")
            embedded.append(document)
        bundle_document, fixed_document, commit_document = embedded
        if (
            bundle_document.get("occurrence_accounting_bundle_id")
            != self.occurrence_accounting_bundle_id
            or bundle_document.get("output_bytes_fixed_point_result_id")
            != fixed_document.get("output_bytes_fixed_point_result_id")
            or bundle_document.get("output_commit_id")
            != commit_document.get("output_commit_id")
            or commit_document.get("output_commit_id") != self.output_commit_id
        ):
            _fail("embedded occurrence evidence identity chain changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_campaign_occurrence_row.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "occurrence_id": self.occurrence_id,
            "occurrence_accounting_bundle_id": self.occurrence_accounting_bundle_id,
            "output_commit_id": self.output_commit_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "actual_projection_proof_id": self.actual_projection_proof_id,
            "occurrence_accounting_bundle": loads_canonical_json(
                self.occurrence_bundle_bytes
            ),
            "output_bytes_fixed_point_result": loads_canonical_json(
                self.fixed_point_result_bytes
            ),
            "output_commit": loads_canonical_json(self.output_commit_bytes),
            "comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in self.comparison_values
            ],
            "route_kind": RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE.value,
            "terminal_class": "PLAN_CERTIFICATE",
            "terminal_code": "ABSTRACT_CERTIFIED",
            "closure_denominator_contribution": 1,
            "certificate_coverage_denominator_contribution": 1,
            "future_economics_denominator_contribution": 1,
            "plan_certificate_count_contribution": 1,
            "infeasibility_certificate_count_contribution": 0,
            "noncertificate_count_contribution": 0,
            "official_execution_allowed": False,
        }

    @property
    def row_id(self) -> str:
        return content_id(OCCURRENCE_ROW_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_occurrence_row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class HeldoutAbstractCampaignClosureV1:
    preregistration_id: str
    occurrence_row_id: str
    cumulative_comparison_values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "closure preregistration")
        _cid(self.occurrence_row_id, "closure occurrence row")
        if (
            tuple(axis for axis, _value in self.cumulative_comparison_values)
            != SHARED_AXES
            or any(
                type(value) is not int or value < 0
                for _axis, value in self.cumulative_comparison_values
            )
        ):
            _fail("campaign cumulative comparison vector changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_campaign_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "ordered_occurrence_row_ids": [self.occurrence_row_id],
            "registered_logical_occurrence_count": 1,
            "closed_logical_occurrence_count": 1,
            "closure_denominator": 1,
            "certificate_coverage_denominator": 1,
            "future_economics_cost_denominator": 1,
            "plan_certificate_count": 1,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": 0,
            "cumulative_comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in self.cumulative_comparison_values
            ],
            "all_registered_occurrences_retained": True,
            "campaign_construction_closed": True,
            "official_certificate_coverage_authority": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }

    @property
    def closure_id(self) -> str:
        return content_id(CLOSURE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_closure_id": self.closure_id}


@dataclass(frozen=True, slots=True)
class HeldoutAbstractCampaignFileCommitV1:
    filename: str
    byte_count: int
    bytes_sha256: str

    def __post_init__(self) -> None:
        if (
            self.filename not in {
                PREREGISTRATION_FILENAME,
                OCCURRENCE_ROW_FILENAME,
                CLOSURE_FILENAME,
            }
            or type(self.byte_count) is not int
            or self.byte_count <= 0
        ):
            _fail("campaign file commit changed")
        _cid(self.bytes_sha256, "campaign file digest")

    def to_document(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "byte_count": self.byte_count,
            "bytes_sha256": self.bytes_sha256,
            "regular_file": True,
            "file_fsync_completed": True,
        }


def _write_campaign_file(
    directory: Path,
    filename: str,
    document: dict[str, Any],
) -> HeldoutAbstractCampaignFileCommitV1:
    raw = canonical_json_bytes(document)
    target = directory / filename
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    try:
        offset = 0
        while offset < len(raw):
            count = os.write(descriptor, raw[offset:])
            if count <= 0:
                _fail("campaign file write made no progress")
            offset += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    info = target.stat()
    if (
        target.is_symlink()
        or not target.is_file()
        or info.st_size != len(raw)
        or stat.S_IMODE(info.st_mode) & 0o177
    ):
        _fail("campaign committed file identity changed")
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return HeldoutAbstractCampaignFileCommitV1(
        filename, len(raw), hashlib.sha256(raw).hexdigest()
    )


@dataclass(frozen=True, slots=True)
class HeldoutAbstractCampaignResultV1:
    reuse_result: reuse_v1.HeldoutOverlayAbstractReuseResultV1 = field(
        repr=False, compare=False
    )
    preregistration: HeldoutAbstractCampaignPreregistrationV1
    occurrence_bundle: occurrence_v1.HeldoutAbstractOccurrenceAccountingBundleV1 = field(
        repr=False, compare=False
    )
    occurrence_row: HeldoutAbstractCampaignOccurrenceRowV1
    closure: HeldoutAbstractCampaignClosureV1
    file_commits: tuple[HeldoutAbstractCampaignFileCommitV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.reuse_result) is not reuse_v1.HeldoutOverlayAbstractReuseResultV1
            or type(self.preregistration) is not HeldoutAbstractCampaignPreregistrationV1
            or type(self.occurrence_bundle)
            is not occurrence_v1.HeldoutAbstractOccurrenceAccountingBundleV1
            or type(self.occurrence_row) is not HeldoutAbstractCampaignOccurrenceRowV1
            or type(self.closure) is not HeldoutAbstractCampaignClosureV1
            or tuple(row.filename for row in self.file_commits)
            != (
                PREREGISTRATION_FILENAME,
                OCCURRENCE_ROW_FILENAME,
                CLOSURE_FILENAME,
            )
            or self.preregistration.reuse_result_id != self.reuse_result.result_id
            or self.occurrence_bundle.reuse_result != self.reuse_result
            or self.occurrence_row.preregistration_id
            != self.preregistration.preregistration_id
            or self.occurrence_row.occurrence_accounting_bundle_id
            != self.occurrence_bundle.bundle_id
            or self.closure.preregistration_id
            != self.preregistration.preregistration_id
            or self.closure.occurrence_row_id != self.occurrence_row.row_id
            or self.closure.cumulative_comparison_values
            != self.occurrence_row.comparison_values
        ):
            _fail("held-out campaign result is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_campaign_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration.preregistration_id,
            "occurrence_accounting_bundle_id": self.occurrence_bundle.bundle_id,
            "campaign_occurrence_row_id": self.occurrence_row.row_id,
            "campaign_closure_id": self.closure.closure_id,
            "campaign_file_commits": [row.to_document() for row in self.file_commits],
            "registered_logical_occurrence_count": 1,
            "plan_certificate_count": 1,
            "noncertificate_count": 0,
            "campaign_construction_closed": True,
            "producer_free_campaign_verification_present": False,
            "campaign_orchestration_work_vector_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        return content_id(RESULT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "heldout_abstract_campaign_result_id": self.result_id}


def _preregister(
    result: reuse_v1.HeldoutOverlayAbstractReuseResultV1,
) -> HeldoutAbstractCampaignPreregistrationV1:
    return HeldoutAbstractCampaignPreregistrationV1(
        result.query.logical_occurrence_id,
        result.query.occurrence_ordinal,
        result.query.threshold_profile_id,
        result.result_id,
        result.source.final_overlay.overlay_id,
        result.source.final_overlay.bridge.quotient_model.model_id,
        result.query.query_id,
        result.plan.plan_id,
    )


def _occurrence_row(
    preregistration: HeldoutAbstractCampaignPreregistrationV1,
    bundle: occurrence_v1.HeldoutAbstractOccurrenceAccountingBundleV1,
) -> HeldoutAbstractCampaignOccurrenceRowV1:
    return HeldoutAbstractCampaignOccurrenceRowV1(
        preregistration.preregistration_id,
        bundle.work_vector.subject_id,
        bundle.bundle_id,
        bundle.output_commit.output_commit_id,
        bundle.work_vector.work_vector_id,
        bundle.comparison_vector.comparison_vector_id,
        bundle.actual_projection_proof.actual_projection_proof_id,
        canonical_json_bytes(bundle.to_document()),
        canonical_json_bytes(bundle.fixed_point.to_document()),
        canonical_json_bytes(bundle.output_commit.to_document()),
        bundle.comparison_vector.values,
    )


def run_heldout_abstract_campaign_v1(
    result: reuse_v1.HeldoutOverlayAbstractReuseResultV1,
    *,
    campaign_directory: str | Path,
) -> HeldoutAbstractCampaignResultV1:
    if type(result) is not reuse_v1.HeldoutOverlayAbstractReuseResultV1:
        _fail("held-out campaign requires one exact reuse result")
    directory = Path(campaign_directory)
    if directory.exists():
        _fail("held-out campaign directory must be absent")
    directory.mkdir(mode=0o700, parents=False)
    preregistration = _preregister(result)
    commits = [
        _write_campaign_file(
            directory, PREREGISTRATION_FILENAME, preregistration.to_document()
        )
    ]
    bundle = occurrence_v1.run_heldout_abstract_occurrence_accounting_v1(
        result,
        output_directory=directory / OCCURRENCE_OUTPUT_DIRECTORY,
    )
    row = _occurrence_row(preregistration, bundle)
    commits.append(
        _write_campaign_file(directory, OCCURRENCE_ROW_FILENAME, row.to_document())
    )
    closure = HeldoutAbstractCampaignClosureV1(
        preregistration.preregistration_id,
        row.row_id,
        row.comparison_values,
    )
    commits.append(
        _write_campaign_file(directory, CLOSURE_FILENAME, closure.to_document())
    )
    result_bundle = HeldoutAbstractCampaignResultV1(
        result,
        preregistration,
        bundle,
        row,
        closure,
        tuple(commits),
    )
    return verify_heldout_abstract_campaign_v1(result_bundle)


def verify_heldout_abstract_campaign_v1(
    result: HeldoutAbstractCampaignResultV1,
) -> HeldoutAbstractCampaignResultV1:
    if type(result) is not HeldoutAbstractCampaignResultV1:
        _fail("held-out campaign verifier rejects foreign values")
    result.reuse_result.result_id
    result.occurrence_bundle.bundle_id
    expected_preregistration = _preregister(result.reuse_result)
    expected_row = _occurrence_row(expected_preregistration, result.occurrence_bundle)
    expected_closure = HeldoutAbstractCampaignClosureV1(
        expected_preregistration.preregistration_id,
        expected_row.row_id,
        expected_row.comparison_values,
    )
    documents = (
        expected_preregistration.to_document(),
        expected_row.to_document(),
        expected_closure.to_document(),
    )
    expected_commits = tuple(
        HeldoutAbstractCampaignFileCommitV1(
            filename,
            len(raw := canonical_json_bytes(document)),
            hashlib.sha256(raw).hexdigest(),
        )
        for filename, document in zip(
            (PREREGISTRATION_FILENAME, OCCURRENCE_ROW_FILENAME, CLOSURE_FILENAME),
            documents,
        )
    )
    if (
        result.preregistration != expected_preregistration
        or result.occurrence_row != expected_row
        or result.closure != expected_closure
        or result.file_commits != expected_commits
    ):
        _fail("held-out campaign differs from exact identity/denominator replay")
    result.__post_init__()
    return result


__all__ = (
    "ConstructionK7HeldoutAbstractCampaignV1Error",
    "LOCAL_DOMAINS",
    "HeldoutAbstractCampaignClosureV1",
    "HeldoutAbstractCampaignFileCommitV1",
    "HeldoutAbstractCampaignOccurrenceRowV1",
    "HeldoutAbstractCampaignPreregistrationV1",
    "HeldoutAbstractCampaignResultV1",
    "run_heldout_abstract_campaign_v1",
    "verify_heldout_abstract_campaign_v1",
)
