"""Bounded first-occurrence failure closure for preregistered campaigns.

The existing positive runner intentionally leaves partial artifacts when an
occurrence raises.  This additive wrapper observes that boundary and, only
after the preregistration and its first commit event are durable, closes every
registered logical occurrence as a retained protocol noncertificate.

This first failure slice is deliberately narrow: it accepts failure before the
first occurrence commit only.  Later-prefix failure remains a separate gate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_campaign_preregistration_independent_verifier_v1 as prereg_independent_v1
from acfqp import construction_k7_query_bound_campaign_preregistration_v1 as prereg_v1
from acfqp import construction_k7_query_bound_preregistered_campaign_runner_v1 as runner_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.103"
PROFILE_KEY = "construction_k7_query_bound_campaign_failure_closure_v1"
CLOSURE_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_V1_DOMAIN
EVENT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN
EXECUTION_DIRECTORY_NAME = "campaign"
FAILURE_FILENAME = "CAMPAIGN_FAILURE_CLOSURE.json"
_ISSUER = object()


class ConstructionK7QueryBoundCampaignFailureClosureV1Error(RuntimeError):
    """The durable failure prefix or registered denominator was not exact."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignFailureClosureV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignFailureClosureV1Error(
            f"{label} must be one content ID"
        ) from error


def _private_root(path: str | Path) -> Path:
    root = Path(path)
    if root.exists() or root.is_symlink():
        _fail("campaign failure wrapper root must be absent")
    parent = root.parent.resolve(strict=True)
    if parent.is_symlink() or not parent.is_dir():
        _fail("campaign failure wrapper parent is invalid")
    root.mkdir(mode=0o700)
    return root.resolve(strict=True)


def _write_all(fd: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = os.write(fd, raw[offset:])
        if written <= 0:
            _fail("failure closure write made no progress")
        offset += written


def _commit_file(root: Path, name: str, raw: bytes) -> None:
    if Path(name).name != name or type(raw) is not bytes or not raw:
        _fail("failure closure target or bytes are invalid")
    fd = os.open(
        root / name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
        0o400,
    )
    try:
        _write_all(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    directory_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    if (root / name).read_bytes() != raw:
        _fail("failure closure differs after fsync")


def _canonical_file(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        _fail(f"{label} is absent or not one regular file")
    raw = path.read_bytes()
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignFailureClosureV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return raw, document


def _partial_inventory(directory: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        info = path.stat()
        if (
            path.is_symlink()
            or not path.is_file()
            or not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            _fail("partial occurrence contains a non-regular artifact")
        raw = path.read_bytes()
        rows.append(
            {
                "relative_name": path.name,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "mode": stat.S_IMODE(info.st_mode),
            }
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignFailureOccurrenceRowV1:
    occurrence_index: int
    occurrence_spec_id: str
    logical_occurrence_id: str
    failure_position: str

    def __post_init__(self) -> None:
        if (
            type(self.occurrence_index) is not int
            or self.occurrence_index <= 0
            or self.failure_position
            not in {"STARTED_WITHOUT_COMMIT", "NOT_STARTED_AFTER_CAMPAIGN_FAILURE"}
        ):
            _fail("campaign failure occurrence row is invalid")
        _cid(self.occurrence_spec_id, "failure occurrence spec")
        _cid(self.logical_occurrence_id, "failure logical occurrence")

    def to_document(self) -> dict[str, Any]:
        reason = (
            "the first occurrence began but no complete bundle event committed"
            if self.failure_position == "STARTED_WITHOUT_COMMIT"
            else "campaign protocol failure closed before this occurrence began"
        )
        typed_missing = {
            "kind": "NOT_AVAILABLE_DUE_TO_PROTOCOL_FAILURE",
            "reason": reason,
        }
        return {
            "occurrence_index": self.occurrence_index,
            "preregistered_occurrence_spec_id": self.occurrence_spec_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "failure_position": self.failure_position,
            "complete_bundle_verification_id": dict(typed_missing),
            "occurrence_work_vector_id": dict(typed_missing),
            "terminal_scope": "LOGICAL_OCCURRENCE",
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "PROTOCOL_FAILURE",
            "closure_denominator_included": True,
            "certification_denominator_included": True,
            "economics_denominator_included": True,
        }


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignFailureClosureV1:
    _issuer: InitVar[object]
    preregistration_id: str
    preregistration_verification_id: str
    workload_spec_id: str
    preregistration_bytes: bytes = field(repr=False)
    first_event_id: str
    first_event_bytes: bytes = field(repr=False)
    partial_occurrence_inventory: tuple[dict[str, Any], ...] = field(repr=False)
    occurrence_rows: tuple[QueryBoundCampaignFailureOccurrenceRowV1, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or type(self.preregistration_bytes) is not bytes
            or not self.preregistration_bytes
            or type(self.first_event_bytes) is not bytes
            or not self.first_event_bytes
            or type(self.partial_occurrence_inventory) is not tuple
            or len(self.occurrence_rows) < 2
            or tuple(row.occurrence_index for row in self.occurrence_rows)
            != tuple(range(1, len(self.occurrence_rows) + 1))
            or self.occurrence_rows[0].failure_position != "STARTED_WITHOUT_COMMIT"
            or any(
                row.failure_position != "NOT_STARTED_AFTER_CAMPAIGN_FAILURE"
                for row in self.occurrence_rows[1:]
            )
        ):
            _fail("campaign failure closure is caller-minted or incomplete")
        for value, label in (
            (self.preregistration_id, "failure preregistration"),
            (self.preregistration_verification_id, "preregistration verification"),
            (self.workload_spec_id, "failure workload"),
            (self.first_event_id, "first campaign event"),
        ):
            _cid(value, label)
        for row in self.partial_occurrence_inventory:
            if (
                type(row) is not dict
                or set(row) != {"relative_name", "byte_count", "sha256", "mode"}
                or type(row["relative_name"]) is not str
                or Path(row["relative_name"]).name != row["relative_name"]
                or type(row["byte_count"]) is not int
                or row["byte_count"] < 0
                or type(row["mode"]) is not int
            ):
                _fail("partial occurrence inventory is malformed")
            _cid(row["sha256"], "partial artifact bytes")
        object.__setattr__(
            self,
            "_closure_id",
            content_id(CLOSURE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        count = len(self.occurrence_rows)
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_failure_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "query_bound_campaign_preregistration_id": self.preregistration_id,
            "campaign_preregistration_verification_id": self.preregistration_verification_id,
            "campaign_workload_spec_id": self.workload_spec_id,
            "preregistration_bytes_sha256": hashlib.sha256(self.preregistration_bytes).hexdigest(),
            "preregistration_byte_count": len(self.preregistration_bytes),
            "first_commit_event_id": self.first_event_id,
            "first_commit_event_sha256": hashlib.sha256(self.first_event_bytes).hexdigest(),
            "first_commit_event_byte_count": len(self.first_event_bytes),
            "supported_failure_phase": "BEFORE_FIRST_OCCURRENCE_COMMIT",
            "failure_witness_kind": "IN_PROCESS_RUNNER_EXCEPTION_AND_DURABLE_INCOMPLETE_PREFIX",
            "portable_failure_cause_authority": False,
            "partial_occurrence_directory": "occurrence-0001",
            "partial_occurrence_inventory": list(self.partial_occurrence_inventory),
            "occurrence_rows": [row.to_document() for row in self.occurrence_rows],
            "logical_occurrence_count": count,
            "closure_denominator": count,
            "certification_coverage_denominator": count,
            "economics_cost_denominator": count,
            "plan_certificate_count": 0,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": count,
            "construction_certificate_coverage_status": "FAIL",
            "official_certificate_coverage_gate_status": "NOT_RUN",
            "all_registered_occurrences_retained": True,
            "campaign_denominator_closure_issued": True,
            "failure_path_campaign_closure_present": True,
            "scientific_campaign_closure_issued": False,
            "campaign_orchestration_work_vector_present": False,
            "official_run_valid": False,
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
            _fail("campaign failure closure changed after issuance")
        return expected

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query_bound_campaign_failure_closure_id": self.closure_id,
        }


def _first_event_expected(
    preregistration_id: str,
    preregistration_bytes: bytes,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_commit_event.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "2.0.101",
        "profile_key": "construction_k7_query_bound_preregistered_campaign_runner_v1",
        "event_index": 1,
        "event_kind": "PREREGISTRATION_COMMITTED",
        "previous_event_id": None,
        "query_bound_campaign_preregistration_id": preregistration_id,
        "subject_id": preregistration_id,
        "subject_relative_path": runner_v1.PREREGISTRATION_FILENAME,
        "subject_bytes_sha256": hashlib.sha256(preregistration_bytes).hexdigest(),
        "subject_byte_count": len(preregistration_bytes),
        "occurrence_index": None,
        "logical_occurrence_id": None,
        "subject_committed_before_event": True,
        "file_fsync_complete": True,
        "directory_fsync_complete": True,
        "official_execution_allowed": False,
    }
    return {**payload, "campaign_commit_event_id": content_id(EVENT_DOMAIN, payload)}


def _issue_first_occurrence_failure_closure(
    execution_root: Path,
) -> QueryBoundCampaignFailureClosureV1:
    prereg_raw, preregistration = _canonical_file(
        execution_root / runner_v1.PREREGISTRATION_FILENAME,
        "campaign preregistration",
    )
    prereg_verification = (
        prereg_independent_v1.verify_query_bound_campaign_preregistration_bytes_v1(
            prereg_raw
        )
    )
    event_name = runner_v1.EVENT_FILENAME_TEMPLATE.format(index=1)
    event_raw, event = _canonical_file(execution_root / event_name, "first commit event")
    if event != _first_event_expected(prereg_verification.preregistration_id, prereg_raw):
        _fail("campaign failure prefix changed its first commit event")
    occurrence_directory = execution_root / "occurrence-0001"
    if occurrence_directory.is_symlink() or not occurrence_directory.is_dir():
        _fail("campaign failure prefix omitted the first occurrence directory")
    expected_entries = {
        runner_v1.PREREGISTRATION_FILENAME,
        event_name,
        "occurrence-0001",
    }
    if {path.name for path in execution_root.iterdir()} != expected_entries:
        _fail("failure closure supports only the pre-first-commit prefix")
    registered = preregistration["preregistered_occurrences"]
    rows = tuple(
        QueryBoundCampaignFailureOccurrenceRowV1(
            row["occurrence_index"],
            row["preregistered_occurrence_spec_id"],
            row["logical_occurrence_id"],
            (
                "STARTED_WITHOUT_COMMIT"
                if row["occurrence_index"] == 1
                else "NOT_STARTED_AFTER_CAMPAIGN_FAILURE"
            ),
        )
        for row in registered
    )
    return QueryBoundCampaignFailureClosureV1(
        _ISSUER,
        prereg_verification.preregistration_id,
        prereg_verification.verification_id,
        prereg_verification.workload_spec_id,
        prereg_raw,
        event["campaign_commit_event_id"],
        event_raw,
        _partial_inventory(occurrence_directory),
        rows,
    )


def run_query_bound_campaign_with_first_failure_closure_v1(
    registration: prereg_v1.QueryBoundCampaignPreregistrationV1,
    *,
    output_directory: str | Path,
    timeout_seconds: int = runner_v1.executor_v1.DEFAULT_TIMEOUT_SECONDS,
) -> runner_v1.QueryBoundPreregisteredCampaignResultV1 | QueryBoundCampaignFailureClosureV1:
    """Run the campaign; close an observed failure before occurrence commit 1."""

    prereg_v1.verify_query_bound_campaign_preregistration_v1(registration)
    root = _private_root(output_directory)
    execution_root = root / EXECUTION_DIRECTORY_NAME
    try:
        return runner_v1.run_query_bound_preregistered_campaign_v1(
            registration,
            output_directory=execution_root,
            timeout_seconds=timeout_seconds,
        )
    except Exception:
        if (
            not execution_root.is_dir()
            or not (execution_root / runner_v1.PREREGISTRATION_FILENAME).is_file()
            or not (
                execution_root / runner_v1.EVENT_FILENAME_TEMPLATE.format(index=1)
            ).is_file()
            or (
                execution_root / runner_v1.EVENT_FILENAME_TEMPLATE.format(index=2)
            ).exists()
        ):
            raise
        closure = _issue_first_occurrence_failure_closure(execution_root)
        _commit_file(root, FAILURE_FILENAME, closure.canonical_bytes)
        return closure


__all__ = (
    "ConstructionK7QueryBoundCampaignFailureClosureV1Error",
    "FAILURE_FILENAME",
    "QueryBoundCampaignFailureClosureV1",
    "QueryBoundCampaignFailureOccurrenceRowV1",
    "run_query_bound_campaign_with_first_failure_closure_v1",
)
