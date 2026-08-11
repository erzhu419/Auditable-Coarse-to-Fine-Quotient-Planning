"""Preregister two fresh queries against one recovered held-out world model.

The query-neutral W5 overlay is verified and both query identities are frozen
before the campaign preregistration reaches disk.  After that durability
boundary, each query executes exactly one owner-accounted H=2 quotient-planner
call.  The resulting stage transcript is passed directly to occurrence
materialization, so accounting does not replay the planner a second time.

This is a bounded construction campaign.  It demonstrates reuse across two
logical occurrences, but it neither charges the historical source-recovery
campaign nor opens any official economics or scalar gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, NoReturn, Sequence

from acfqp.accounting_v1 import RouteKindEnum, SHARED_AXES
from acfqp import construction_k7_heldout_abstract_occurrence_accounting_v1 as occurrence_v1
from acfqp import construction_k7_heldout_abstract_stage_accounting_v1 as stage_v1
from acfqp import construction_k7_heldout_checkpoint_recertification_v1 as source_v1
from acfqp import construction_k7_heldout_overlay_abstract_reuse_v1 as reuse_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.126"
PROFILE_KEY = "construction_k7_heldout_multiquery_campaign_v1"

PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
)
OCCURRENCE_ROW_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
)
CLOSURE_DOMAIN = CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_CLOSURE_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {PREREGISTRATION_DOMAIN, OCCURRENCE_ROW_DOMAIN, CLOSURE_DOMAIN, RESULT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("held-out multiquery campaign domains are not central")

PREREGISTRATION_FILENAME = "0001_PREREGISTRATION.json"
CLOSURE_FILENAME = "0004_CAMPAIGN_CLOSURE.json"
EXPECTED_OCCURRENCE_COUNT = 2


class ConstructionK7HeldoutMultiqueryCampaignV1Error(RuntimeError):
    """The reusable-model campaign identity, accounting, or closure changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutMultiqueryCampaignV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutMultiqueryCampaignV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _row_filename(index: int) -> str:
    return f"{index + 1:04d}_OCCURRENCE_{index:04d}.json"


def _occurrence_directory(index: int) -> str:
    return f"occurrence-{index:04d}"


@dataclass(frozen=True, slots=True)
class HeldoutMultiqueryCampaignPreregistrationV1:
    source_result_id: str
    source_overlay_id: str
    quotient_model_id: str
    threshold_profile_id: str
    queries: tuple[reuse_v1.HeldoutOverlayQueryV1, ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_result_id, "campaign source result"),
            (self.source_overlay_id, "campaign source overlay"),
            (self.quotient_model_id, "campaign quotient model"),
            (self.threshold_profile_id, "campaign threshold"),
        ):
            _cid(value, label)
        queries = tuple(self.queries)
        object.__setattr__(self, "queries", queries)
        if (
            len(queries) != EXPECTED_OCCURRENCE_COUNT
            or any(type(row) is not reuse_v1.HeldoutOverlayQueryV1 for row in queries)
            or len({row.logical_occurrence_id for row in queries}) != len(queries)
            or len({row.query_id for row in queries}) != len(queries)
            or tuple(row.occurrence_ordinal for row in queries)
            != tuple(sorted(row.occurrence_ordinal for row in queries))
            or any(
                row.source_result_id != self.source_result_id
                or row.source_overlay_id != self.source_overlay_id
                or row.quotient_model_id != self.quotient_model_id
                or row.threshold_profile_id != self.threshold_profile_id
                for row in queries
            )
        ):
            _fail("multiquery preregistration inventory changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_multiquery_campaign_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_result_id": self.source_result_id,
            "source_overlay_id": self.source_overlay_id,
            "quotient_model_id": self.quotient_model_id,
            "threshold_profile_id": self.threshold_profile_id,
            "ordered_occurrence_specs": [
                {
                    "occurrence_index": index,
                    "logical_occurrence_id": query.logical_occurrence_id,
                    "occurrence_ordinal": query.occurrence_ordinal,
                    "frozen_query_id": query.query_id,
                    "expected_route_kind": RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE.value,
                    "expected_terminal_class": "PLAN_CERTIFICATE",
                    "expected_terminal_code": "ABSTRACT_CERTIFIED",
                }
                for index, query in enumerate(self.queries, start=1)
            ],
            "registered_logical_occurrence_count": len(self.queries),
            "source_verified_before_preregistration": True,
            "all_query_specs_frozen_before_preregistration": True,
            "fresh_query_planner_invocations_before_preregistration": 0,
            "one_owner_accounted_planner_call_required_per_occurrence": True,
            "denominator_row_deletion_allowed": False,
            "official_execution_allowed": False,
        }

    @property
    def preregistration_id(self) -> str:
        return content_id(PREREGISTRATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_preregistration_id": self.preregistration_id}


@dataclass(frozen=True, slots=True)
class HeldoutMultiqueryCampaignOccurrenceRowV1:
    preregistration_id: str
    occurrence_index: int
    reuse_result: reuse_v1.HeldoutOverlayAbstractReuseResultV1 = field(
        repr=False, compare=False
    )
    occurrence_bundle: occurrence_v1.HeldoutAbstractOccurrenceAccountingBundleV1 = field(
        repr=False, compare=False
    )

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "row preregistration")
        if (
            type(self.occurrence_index) is not int
            or not 1 <= self.occurrence_index <= EXPECTED_OCCURRENCE_COUNT
            or type(self.reuse_result)
            is not reuse_v1.HeldoutOverlayAbstractReuseResultV1
            or type(self.occurrence_bundle)
            is not occurrence_v1.HeldoutAbstractOccurrenceAccountingBundleV1
            or self.occurrence_bundle.reuse_result is not self.reuse_result
            or self.occurrence_bundle.work_vector.route_kind
            is not RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
        ):
            _fail("multiquery occurrence row is malformed")

    def _payload(self) -> dict[str, Any]:
        bundle = self.occurrence_bundle
        return {
            "schema": "acfqp.construction_k7_heldout_multiquery_campaign_occurrence_row.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "occurrence_index": self.occurrence_index,
            "occurrence_id": self.reuse_result.query.logical_occurrence_id,
            "occurrence_ordinal": self.reuse_result.query.occurrence_ordinal,
            "frozen_query_id": self.reuse_result.query.query_id,
            "reuse_result_id": self.reuse_result.result_id,
            "fresh_plan_id": self.reuse_result.plan.plan_id,
            "quotient_model_id": self.reuse_result.query.quotient_model_id,
            "source_overlay_id": self.reuse_result.query.source_overlay_id,
            "occurrence_accounting_bundle_id": bundle.bundle_id,
            "work_vector_id": bundle.work_vector.work_vector_id,
            "comparison_vector_id": bundle.comparison_vector.comparison_vector_id,
            "actual_projection_proof_id": bundle.actual_projection_proof.actual_projection_proof_id,
            "output_commit_id": bundle.output_commit.output_commit_id,
            "reuse_result": self.reuse_result.to_document(),
            "occurrence_accounting_bundle": bundle.to_document(),
            "output_bytes_fixed_point_result": bundle.fixed_point.to_document(),
            "output_commit": bundle.output_commit.to_document(),
            "comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in bundle.comparison_vector.values
            ],
            "route_kind": RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE.value,
            "terminal_class": "PLAN_CERTIFICATE",
            "terminal_code": "ABSTRACT_CERTIFIED",
            "fresh_planner_invocations": 1,
            "accounting_planner_replay_invocations": 0,
            "fresh_ground_or_observer_event_count": 0,
            "portable_occurrence_evidence_embedded": True,
            "closure_denominator_contribution": 1,
            "certificate_coverage_denominator_contribution": 1,
            "future_economics_denominator_contribution": 1,
            "plan_certificate_count_contribution": 1,
            "noncertificate_count_contribution": 0,
            "official_execution_allowed": False,
        }

    @property
    def row_id(self) -> str:
        return content_id(OCCURRENCE_ROW_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_occurrence_row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class HeldoutMultiqueryCampaignClosureV1:
    preregistration_id: str
    rows: tuple[HeldoutMultiqueryCampaignOccurrenceRowV1, ...]
    cumulative_comparison_values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "closure preregistration")
        rows = tuple(self.rows)
        object.__setattr__(self, "rows", rows)
        if (
            len(rows) != EXPECTED_OCCURRENCE_COUNT
            or tuple(row.occurrence_index for row in rows) != (1, 2)
            or any(row.preregistration_id != self.preregistration_id for row in rows)
            or tuple(axis for axis, _value in self.cumulative_comparison_values)
            != SHARED_AXES
            or any(
                type(value) is not int or value < 0
                for _axis, value in self.cumulative_comparison_values
            )
        ):
            _fail("multiquery campaign closure changed")

    def _payload(self) -> dict[str, Any]:
        count = len(self.rows)
        return {
            "schema": "acfqp.construction_k7_heldout_multiquery_campaign_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "ordered_occurrence_row_ids": [row.row_id for row in self.rows],
            "registered_logical_occurrence_count": count,
            "closed_logical_occurrence_count": count,
            "closure_denominator": count,
            "certificate_coverage_denominator": count,
            "future_economics_cost_denominator": count,
            "plan_certificate_count": count,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": 0,
            "cumulative_comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in self.cumulative_comparison_values
            ],
            "shared_source_overlay_count": 1,
            "shared_quotient_model_count": 1,
            "fresh_query_count": count,
            "fresh_plan_count": count,
            "fresh_owner_accounted_planner_invocation_count": count,
            "accounting_planner_replay_invocation_count": 0,
            "fresh_ground_or_observer_event_count": 0,
            "all_registered_occurrences_retained": True,
            "campaign_construction_closed": True,
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
class HeldoutMultiqueryCampaignFileCommitV1:
    filename: str
    byte_count: int
    bytes_sha256: str

    def __post_init__(self) -> None:
        if (
            type(self.filename) is not str
            or not self.filename.endswith(".json")
            or "/" in self.filename
            or type(self.byte_count) is not int
            or self.byte_count <= 0
        ):
            _fail("multiquery campaign file commit changed")
        _cid(self.bytes_sha256, "campaign file digest")

    def to_document(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "byte_count": self.byte_count,
            "bytes_sha256": self.bytes_sha256,
            "regular_file": True,
            "file_fsync_completed": True,
        }


@dataclass(frozen=True, slots=True)
class HeldoutMultiqueryCampaignResultV1:
    source: source_v1.HeldoutCheckpointRecertificationResultV1 = field(
        repr=False, compare=False
    )
    preregistration: HeldoutMultiqueryCampaignPreregistrationV1
    rows: tuple[HeldoutMultiqueryCampaignOccurrenceRowV1, ...]
    closure: HeldoutMultiqueryCampaignClosureV1
    file_commits: tuple[HeldoutMultiqueryCampaignFileCommitV1, ...]

    def __post_init__(self) -> None:
        rows = tuple(self.rows)
        commits = tuple(self.file_commits)
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "file_commits", commits)
        if (
            type(self.source) is not source_v1.HeldoutCheckpointRecertificationResultV1
            or type(self.preregistration)
            is not HeldoutMultiqueryCampaignPreregistrationV1
            or len(rows) != EXPECTED_OCCURRENCE_COUNT
            or type(self.closure) is not HeldoutMultiqueryCampaignClosureV1
            or self.closure.rows != rows
            or len(commits) != EXPECTED_OCCURRENCE_COUNT + 2
            or tuple(row.filename for row in commits)
            != (
                PREREGISTRATION_FILENAME,
                _row_filename(1),
                _row_filename(2),
                CLOSURE_FILENAME,
            )
            or self.preregistration.source_result_id != self.source.result_id
            or tuple(row.reuse_result.query for row in rows)
            != self.preregistration.queries
        ):
            _fail("multiquery campaign result is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_multiquery_campaign_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration.preregistration_id,
            "ordered_occurrence_row_ids": [row.row_id for row in self.rows],
            "campaign_closure_id": self.closure.closure_id,
            "campaign_file_commits": [row.to_document() for row in self.file_commits],
            "registered_logical_occurrence_count": len(self.rows),
            "plan_certificate_count": len(self.rows),
            "noncertificate_count": 0,
            "single_query_neutral_overlay_reused": True,
            "fresh_planner_execution_accounted_without_replay": True,
            "campaign_construction_closed": True,
            "producer_free_campaign_verification_present": False,
            "campaign_orchestration_work_vector_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        return content_id(RESULT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "heldout_multiquery_campaign_result_id": self.result_id}


def _write_file(
    directory: Path, filename: str, document: dict[str, Any]
) -> HeldoutMultiqueryCampaignFileCommitV1:
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
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                _fail("multiquery campaign file write made no progress")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    info = target.stat()
    if (
        target.is_symlink()
        or not target.is_file()
        or stat.S_IMODE(info.st_mode) & 0o177
        or info.st_size != len(raw)
    ):
        _fail("multiquery campaign file identity changed")
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return HeldoutMultiqueryCampaignFileCommitV1(
        filename, len(raw), hashlib.sha256(raw).hexdigest()
    )


def _preregister(
    source: source_v1.HeldoutCheckpointRecertificationResultV1,
    queries: tuple[reuse_v1.HeldoutOverlayQueryV1, ...],
) -> HeldoutMultiqueryCampaignPreregistrationV1:
    return HeldoutMultiqueryCampaignPreregistrationV1(
        source.result_id,
        source.final_overlay.overlay_id,
        source.final_overlay.bridge.quotient_model.model_id,
        source.threshold.threshold_profile_id,
        queries,
    )


def _cumulative(
    rows: tuple[HeldoutMultiqueryCampaignOccurrenceRowV1, ...],
) -> tuple[tuple[str, int], ...]:
    return tuple(
        (
            axis,
            sum(
                dict(row.occurrence_bundle.comparison_vector.values)[axis]
                for row in rows
            ),
        )
        for axis in SHARED_AXES
    )


def run_heldout_multiquery_campaign_v1(
    source: source_v1.HeldoutCheckpointRecertificationResultV1,
    *,
    occurrence_specs: Sequence[tuple[str, int]],
    campaign_directory: str | Path,
) -> HeldoutMultiqueryCampaignResultV1:
    """Preregister, execute and close two fresh zero-ground occurrences."""

    if type(source) is not source_v1.HeldoutCheckpointRecertificationResultV1:
        _fail("multiquery campaign requires one exact held-out source")
    specs = tuple(occurrence_specs)
    if (
        len(specs) != EXPECTED_OCCURRENCE_COUNT
        or any(
            type(row) is not tuple
            or len(row) != 2
            or type(row[0]) is not str
            or type(row[1]) is not int
            for row in specs
        )
    ):
        _fail("multiquery campaign requires exactly two typed occurrence specs")
    # All source semantic replay and query freezing occurs before the durable
    # preregistration.  No fresh query planner has run at this point.
    queries = tuple(
        reuse_v1.freeze_heldout_overlay_query_v1(
            source,
            logical_occurrence_id=occurrence_id,
            occurrence_ordinal=ordinal,
        )
        for occurrence_id, ordinal in specs
    )
    preregistration = _preregister(source, queries)
    directory = Path(campaign_directory)
    if directory.exists():
        _fail("multiquery campaign directory must be absent")
    directory.mkdir(mode=0o700, parents=False)
    commits = [
        _write_file(
            directory,
            PREREGISTRATION_FILENAME,
            preregistration.to_document(),
        )
    ]
    rows: list[HeldoutMultiqueryCampaignOccurrenceRowV1] = []
    for index, query in enumerate(queries, start=1):
        stage = stage_v1.run_and_record_heldout_abstract_route_v1(source, query)
        bundle = occurrence_v1.run_preaccounted_heldout_abstract_occurrence_v1(
            stage,
            output_directory=directory / _occurrence_directory(index),
        )
        row = HeldoutMultiqueryCampaignOccurrenceRowV1(
            preregistration.preregistration_id,
            index,
            stage.reuse_result,
            bundle,
        )
        rows.append(row)
        commits.append(_write_file(directory, _row_filename(index), row.to_document()))
    frozen_rows = tuple(rows)
    closure = HeldoutMultiqueryCampaignClosureV1(
        preregistration.preregistration_id,
        frozen_rows,
        _cumulative(frozen_rows),
    )
    commits.append(_write_file(directory, CLOSURE_FILENAME, closure.to_document()))
    return verify_heldout_multiquery_campaign_v1(
        HeldoutMultiqueryCampaignResultV1(
            source,
            preregistration,
            frozen_rows,
            closure,
            tuple(commits),
        )
    )


def verify_heldout_multiquery_campaign_v1(
    result: HeldoutMultiqueryCampaignResultV1,
) -> HeldoutMultiqueryCampaignResultV1:
    if type(result) is not HeldoutMultiqueryCampaignResultV1:
        _fail("multiquery campaign verifier rejects foreign values")
    expected_preregistration = _preregister(
        result.source, result.preregistration.queries
    )
    expected_closure = HeldoutMultiqueryCampaignClosureV1(
        expected_preregistration.preregistration_id,
        result.rows,
        _cumulative(result.rows),
    )
    if (
        result.preregistration != expected_preregistration
        or result.closure != expected_closure
    ):
        _fail("multiquery campaign differs from exact identity/closure replay")
    for row in result.rows:
        occurrence_v1.verify_heldout_abstract_occurrence_accounting_v1(
            row.occurrence_bundle
        )
    documents = (
        expected_preregistration.to_document(),
        *(row.to_document() for row in result.rows),
        expected_closure.to_document(),
    )
    filenames = (
        PREREGISTRATION_FILENAME,
        _row_filename(1),
        _row_filename(2),
        CLOSURE_FILENAME,
    )
    expected_commits = tuple(
        HeldoutMultiqueryCampaignFileCommitV1(
            filename,
            len(raw := canonical_json_bytes(document)),
            hashlib.sha256(raw).hexdigest(),
        )
        for filename, document in zip(filenames, documents, strict=True)
    )
    if (
        result.file_commits != expected_commits
    ):
        _fail("multiquery campaign differs from exact identity/closure replay")
    result.__post_init__()
    return result


__all__ = (
    "ConstructionK7HeldoutMultiqueryCampaignV1Error",
    "EXPECTED_OCCURRENCE_COUNT",
    "HeldoutMultiqueryCampaignClosureV1",
    "HeldoutMultiqueryCampaignFileCommitV1",
    "HeldoutMultiqueryCampaignOccurrenceRowV1",
    "HeldoutMultiqueryCampaignPreregistrationV1",
    "HeldoutMultiqueryCampaignResultV1",
    "LOCAL_DOMAINS",
    "run_heldout_multiquery_campaign_v1",
    "verify_heldout_multiquery_campaign_v1",
)
