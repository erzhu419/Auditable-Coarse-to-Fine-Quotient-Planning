"""Later-prefix failure closure for preregistered query-bound campaigns.

V1 closes a failure before the first occurrence commit.  This additive V2
closes the next distinct case: at least one registered occurrence has a fully
verified bundle and durable commit event, while a later registered occurrence
does not commit.  Completed certificates and unresolved noncertificates remain
separate, and every registered occurrence stays in all three denominators.
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
from acfqp import construction_k7_query_bound_complete_bundle_independent_verifier_v1 as bundle_v1
from acfqp import construction_k7_query_bound_preregistered_campaign_runner_v1 as runner_v1
from acfqp import construction_k7_query_bound_supervised_executor_v1 as executor_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_V2_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.104"
PROFILE_KEY = "construction_k7_query_bound_campaign_prefix_failure_closure_v2"
CLOSURE_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_V2_DOMAIN
EVENT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN
EXECUTION_DIRECTORY_NAME = "campaign"
FAILURE_FILENAME = "CAMPAIGN_PREFIX_FAILURE_CLOSURE.json"
PREREGISTRATION_FILENAME = "CAMPAIGN_PREREGISTRATION.json"
EVENT_FILENAME_TEMPLATE = "{index:04d}_COMMIT_EVENT.json"
OCCURRENCE_DIRECTORY_TEMPLATE = "occurrence-{index:04d}"
_ISSUER = object()

_COMPLETED_FIELDS = {
    "occurrence_index",
    "preregistered_occurrence_spec_id",
    "logical_occurrence_id",
    "failure_position",
    "complete_bundle_verification_id",
    "operational_trace_id",
    "shared_measurement_id",
    "shared_resource_receipt_set_id",
    "work_vector_ids",
    "comparison_vector_ids",
    "actual_projection_proof_ids",
    "io.output_bytes",
    "campaign_commit_event_id",
    "terminal_scope",
    "terminal_class",
    "terminal_code",
    "closure_denominator_included",
    "certification_denominator_included",
    "economics_denominator_included",
}
_PENDING_FIELDS = {
    "occurrence_index",
    "preregistered_occurrence_spec_id",
    "logical_occurrence_id",
    "failure_position",
    "complete_bundle_verification_id",
    "occurrence_work_vector_id",
    "terminal_scope",
    "terminal_class",
    "terminal_code",
    "closure_denominator_included",
    "certification_denominator_included",
    "economics_denominator_included",
}


class ConstructionK7QueryBoundCampaignPrefixFailureClosureV2Error(RuntimeError):
    """A committed occurrence prefix or retained denominator changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignPrefixFailureClosureV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignPrefixFailureClosureV2Error(
            f"{label} must be one content ID"
        ) from error


def _private_root(path: str | Path) -> Path:
    root = Path(path)
    if root.exists() or root.is_symlink():
        _fail("prefix-failure wrapper root must be absent")
    parent = root.parent.resolve(strict=True)
    if parent.is_symlink() or not parent.is_dir():
        _fail("prefix-failure wrapper parent is invalid")
    root.mkdir(mode=0o700)
    return root.resolve(strict=True)


def _write_all(fd: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = os.write(fd, raw[offset:])
        if written <= 0:
            _fail("prefix-failure closure write made no progress")
        offset += written


def _commit_file(root: Path, name: str, raw: bytes) -> None:
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
        _fail("prefix-failure closure differs after fsync")


def _canonical_file(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        _fail(f"{label} is absent or not one regular file")
    raw = path.read_bytes()
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignPrefixFailureClosureV2Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return raw, document


def _partial_inventory(directory: Path | None) -> list[dict[str, Any]]:
    if directory is None:
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        info = path.stat()
        if (
            path.is_symlink()
            or not path.is_file()
            or not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            _fail("pending occurrence contains a non-private artifact")
        raw = path.read_bytes()
        rows.append(
            {
                "relative_name": path.name,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "mode": stat.S_IMODE(info.st_mode),
            }
        )
    return rows


def _event_document(
    *,
    index: int,
    previous_event_id: str,
    preregistration_id: str,
    bundle_verification_id: str,
    directory_name: str,
    manifest_raw: bytes,
    occurrence_index: int,
    logical_occurrence_id: str,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_commit_event.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "2.0.101",
        "profile_key": "construction_k7_query_bound_preregistered_campaign_runner_v1",
        "event_index": index,
        "event_kind": "OCCURRENCE_COMMITTED",
        "previous_event_id": previous_event_id,
        "query_bound_campaign_preregistration_id": preregistration_id,
        "subject_id": bundle_verification_id,
        "subject_relative_path": f"{directory_name}/OUTPUT_MANIFEST.json",
        "subject_bytes_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "subject_byte_count": len(manifest_raw),
        "occurrence_index": occurrence_index,
        "logical_occurrence_id": logical_occurrence_id,
        "subject_committed_before_event": True,
        "file_fsync_complete": True,
        "directory_fsync_complete": True,
        "official_execution_allowed": False,
    }
    return {**payload, "campaign_commit_event_id": content_id(EVENT_DOMAIN, payload)}


def _first_event_document(
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
        "subject_relative_path": PREREGISTRATION_FILENAME,
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


def _verify_bundle_registration_join(
    *,
    registered: prereg_v1.QueryBoundCampaignPreregisteredOccurrenceV1,
    registration: prereg_v1.QueryBoundCampaignPreregistrationV1,
    directory: Path,
    verification: bundle_v1.QueryBoundCompleteBundleVerificationV1,
) -> None:
    _business_raw, business = _canonical_file(
        directory / "BUSINESS_RESULT.json",
        "completed occurrence business result",
    )
    preparation = business.get("runtime_preparation")
    request = business.get("supervised_request")
    if type(preparation) is not dict or type(request) is not dict:
        _fail("completed occurrence omitted runtime preparation or request")
    expected_inventory = [
        {
            "role": role,
            "filename": filename,
            "byte_count": len(registered.input_bytes_by_role[role]),
            "sha256": hashlib.sha256(
                registered.input_bytes_by_role[role]
            ).hexdigest(),
        }
        for role, filename in executor_v1.INPUT_ROLES
    ]
    if (
        verification.occurrence_id != registered.logical_occurrence_id
        or business.get("occurrence_id") != registered.logical_occurrence_id
        or preparation.get("query_bound_runtime_preparation_id")
        != registration.runtime_preparation.preparation_id
        or preparation.get("runtime_manifest", {}).get("runtime_tree_id")
        != registration.runtime_preparation.manifest.runtime_tree_id
        or preparation.get("source_closure", {}).get("closure_id")
        != registration.runtime_preparation.source_closure.closure_id
        or request.get("input_inventory") != expected_inventory
    ):
        _fail("completed occurrence differs from preregistered source or inputs")


def _completed_row(
    *,
    registered: prereg_v1.QueryBoundCampaignPreregisteredOccurrenceV1,
    verification: bundle_v1.QueryBoundCompleteBundleVerificationV1,
    event_id: str,
) -> dict[str, Any]:
    return {
        "occurrence_index": registered.occurrence_index,
        "preregistered_occurrence_spec_id": registered.occurrence_spec_id,
        "logical_occurrence_id": registered.logical_occurrence_id,
        "failure_position": "COMPLETED_BEFORE_LATER_CAMPAIGN_FAILURE",
        "complete_bundle_verification_id": verification.verification_id,
        "operational_trace_id": verification.operational_trace_id,
        "shared_measurement_id": verification.shared_measurement_id,
        "shared_resource_receipt_set_id": verification.shared_receipt_set_id,
        "work_vector_ids": list(verification.work_vector_ids),
        "comparison_vector_ids": list(verification.comparison_vector_ids),
        "actual_projection_proof_ids": list(verification.projection_proof_ids),
        "io.output_bytes": verification.output_bytes,
        "campaign_commit_event_id": event_id,
        "terminal_scope": "LOGICAL_OCCURRENCE",
        "terminal_class": "PLAN_CERTIFICATE",
        "terminal_code": "FULL_GROUND_FALLBACK",
        "closure_denominator_included": True,
        "certification_denominator_included": True,
        "economics_denominator_included": True,
    }


def _pending_row(
    registered: prereg_v1.QueryBoundCampaignPreregisteredOccurrenceV1,
    *,
    started: bool,
) -> dict[str, Any]:
    position = (
        "STARTED_WITHOUT_COMMIT"
        if started
        else "NOT_STARTED_AFTER_PREFIX_FAILURE"
    )
    reason = (
        "this occurrence began but no complete bundle event committed"
        if started
        else "campaign protocol failure closed before this occurrence began"
    )
    return {
        "occurrence_index": registered.occurrence_index,
        "preregistered_occurrence_spec_id": registered.occurrence_spec_id,
        "logical_occurrence_id": registered.logical_occurrence_id,
        "failure_position": position,
        "complete_bundle_verification_id": {
            "kind": "NOT_AVAILABLE_DUE_TO_PROTOCOL_FAILURE",
            "reason": reason,
        },
        "occurrence_work_vector_id": {
            "kind": "NOT_AVAILABLE_DUE_TO_PROTOCOL_FAILURE",
            "reason": reason,
        },
        "terminal_scope": "LOGICAL_OCCURRENCE",
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "PROTOCOL_FAILURE",
        "closure_denominator_included": True,
        "certification_denominator_included": True,
        "economics_denominator_included": True,
    }


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignPrefixFailureClosureV2:
    _issuer: InitVar[object]
    preregistration_id: str
    preregistration_verification_id: str
    workload_spec_id: str
    preregistration_bytes: bytes = field(repr=False)
    committed_event_ids: tuple[str, ...]
    occurrence_rows: tuple[dict[str, Any], ...] = field(repr=False)
    completed_occurrence_count: int
    pending_occurrence_directory: str | None
    pending_occurrence_inventory: tuple[dict[str, Any], ...] = field(repr=False)
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        count = len(self.occurrence_rows)
        if (
            _issuer is not _ISSUER
            or count < 2
            or type(self.completed_occurrence_count) is not int
            or not (1 <= self.completed_occurrence_count < count)
            or len(self.committed_event_ids) != self.completed_occurrence_count + 1
            or type(self.preregistration_bytes) is not bytes
            or not self.preregistration_bytes
            or type(self.pending_occurrence_inventory) is not tuple
        ):
            _fail("campaign prefix-failure closure is caller-minted or incomplete")
        for value, label in (
            (self.preregistration_id, "prefix-failure preregistration"),
            (self.preregistration_verification_id, "preregistration verification"),
            (self.workload_spec_id, "prefix-failure workload"),
            *((value, "committed campaign event") for value in self.committed_event_ids),
        ):
            _cid(value, label)
        for index, row in enumerate(self.occurrence_rows, start=1):
            fields = _COMPLETED_FIELDS if index <= self.completed_occurrence_count else _PENDING_FIELDS
            if type(row) is not dict or set(row) != fields or row["occurrence_index"] != index:
                _fail("campaign prefix-failure occurrence row changed")
        expected_pending = f"occurrence-{self.completed_occurrence_count + 1:04d}"
        if self.pending_occurrence_directory not in {None, expected_pending}:
            _fail("pending occurrence directory crossed the committed prefix")
        object.__setattr__(
            self,
            "_closure_id",
            content_id(CLOSURE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        count = len(self.occurrence_rows)
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_prefix_failure_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "query_bound_campaign_preregistration_id": self.preregistration_id,
            "campaign_preregistration_verification_id": self.preregistration_verification_id,
            "campaign_workload_spec_id": self.workload_spec_id,
            "preregistration_bytes_sha256": hashlib.sha256(self.preregistration_bytes).hexdigest(),
            "preregistration_byte_count": len(self.preregistration_bytes),
            "committed_campaign_event_ids": list(self.committed_event_ids),
            "completed_occurrence_count": self.completed_occurrence_count,
            "pending_occurrence_directory": self.pending_occurrence_directory,
            "pending_occurrence_inventory": list(self.pending_occurrence_inventory),
            "occurrence_rows": list(self.occurrence_rows),
            "logical_occurrence_count": count,
            "closure_denominator": count,
            "certification_coverage_denominator": count,
            "economics_cost_denominator": count,
            "plan_certificate_count": self.completed_occurrence_count,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": count - self.completed_occurrence_count,
            "construction_certificate_coverage_status": "FAIL",
            "official_certificate_coverage_gate_status": "NOT_RUN",
            "all_registered_occurrences_retained": True,
            "completed_occurrence_certificates_retained": True,
            "campaign_denominator_closure_issued": True,
            "failure_path_campaign_closure_present": True,
            "scientific_campaign_closure_issued": False,
            "campaign_orchestration_work_vector_present": False,
            "official_run_valid": False,
            "portable_failure_cause_authority": False,
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
            _fail("campaign prefix-failure closure changed after issuance")
        return expected

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query_bound_campaign_prefix_failure_closure_id": self.closure_id,
        }


def _issue_prefix_failure(
    registration: prereg_v1.QueryBoundCampaignPreregistrationV1,
    execution_root: Path,
) -> QueryBoundCampaignPrefixFailureClosureV2:
    prereg_raw, _prereg_doc = _canonical_file(
        execution_root / PREREGISTRATION_FILENAME,
        "campaign preregistration",
    )
    prereg_verification = prereg_independent_v1.verify_query_bound_campaign_preregistration_bytes_v1(
        prereg_raw
    )
    if (
        registration.preregistration_id != prereg_verification.preregistration_id
        or registration.workload_spec.workload_spec_id
        != prereg_verification.workload_spec_id
        or tuple(row.logical_occurrence_id for row in registration.occurrences)
        != prereg_verification.occurrence_ids
    ):
        _fail("live registration crossed the durable preregistration prefix")
    first_event_raw, first_event = _canonical_file(
        execution_root / EVENT_FILENAME_TEMPLATE.format(index=1),
        "campaign preregistration event",
    )
    expected_first = _first_event_document(
        prereg_verification.preregistration_id,
        prereg_raw,
    )
    if first_event != expected_first:
        _fail("campaign prefix changed its preregistration event")
    del first_event_raw
    events = [first_event]
    completed_rows: list[dict[str, Any]] = []
    for registered in registration.occurrences:
        occurrence_index = registered.occurrence_index
        event_index = occurrence_index + 1
        event_path = execution_root / EVENT_FILENAME_TEMPLATE.format(
            index=event_index
        )
        if not event_path.exists():
            break
        directory_name = OCCURRENCE_DIRECTORY_TEMPLATE.format(
            index=occurrence_index
        )
        directory = execution_root / directory_name
        verification = bundle_v1.verify_query_bound_complete_bundle_directory_v1(
            directory
        )
        _verify_bundle_registration_join(
            registered=registered,
            registration=registration,
            directory=directory,
            verification=verification,
        )
        manifest_raw, _manifest = _canonical_file(
            directory / "OUTPUT_MANIFEST.json",
            "completed occurrence manifest",
        )
        _event_raw, event = _canonical_file(event_path, "occurrence commit event")
        expected_event = _event_document(
            index=event_index,
            previous_event_id=events[-1]["campaign_commit_event_id"],
            preregistration_id=prereg_verification.preregistration_id,
            bundle_verification_id=verification.verification_id,
            directory_name=directory_name,
            manifest_raw=manifest_raw,
            occurrence_index=occurrence_index,
            logical_occurrence_id=registered.logical_occurrence_id,
        )
        if event != expected_event:
            _fail("completed occurrence commit event changed")
        events.append(event)
        completed_rows.append(
            _completed_row(
                registered=registered,
                verification=verification,
                event_id=event["campaign_commit_event_id"],
            )
        )
    completed = len(completed_rows)
    total = len(registration.occurrences)
    if not (1 <= completed < total):
        _fail("V2 requires a nonempty but incomplete occurrence prefix")
    pending_name = OCCURRENCE_DIRECTORY_TEMPLATE.format(index=completed + 1)
    pending_path = execution_root / pending_name
    pending_directory = pending_path if pending_path.is_dir() and not pending_path.is_symlink() else None
    rows = list(completed_rows)
    for registered in registration.occurrences[completed:]:
        rows.append(
            _pending_row(
                registered,
                started=(
                    registered.occurrence_index == completed + 1
                    and pending_directory is not None
                ),
            )
        )
    expected_entries = {
        PREREGISTRATION_FILENAME,
        *(EVENT_FILENAME_TEMPLATE.format(index=i) for i in range(1, completed + 2)),
        *(OCCURRENCE_DIRECTORY_TEMPLATE.format(index=i) for i in range(1, completed + 1)),
    }
    if pending_directory is not None:
        expected_entries.add(pending_name)
    if {path.name for path in execution_root.iterdir()} != expected_entries:
        _fail("campaign prefix-failure root inventory changed")
    return QueryBoundCampaignPrefixFailureClosureV2(
        _ISSUER,
        prereg_verification.preregistration_id,
        prereg_verification.verification_id,
        prereg_verification.workload_spec_id,
        prereg_raw,
        tuple(event["campaign_commit_event_id"] for event in events),
        tuple(rows),
        completed,
        pending_name if pending_directory is not None else None,
        tuple(_partial_inventory(pending_directory)),
    )


def run_query_bound_campaign_with_prefix_failure_closure_v2(
    registration: prereg_v1.QueryBoundCampaignPreregistrationV1,
    *,
    output_directory: str | Path,
    timeout_seconds: int = executor_v1.DEFAULT_TIMEOUT_SECONDS,
) -> runner_v1.QueryBoundPreregisteredCampaignResultV1 | QueryBoundCampaignPrefixFailureClosureV2:
    """Run the campaign and close an observed nonempty incomplete prefix."""

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
        if not execution_root.is_dir():
            raise
        closure = _issue_prefix_failure(registration, execution_root)
        _commit_file(root, FAILURE_FILENAME, closure.canonical_bytes)
        return closure


__all__ = (
    "ConstructionK7QueryBoundCampaignPrefixFailureClosureV2Error",
    "FAILURE_FILENAME",
    "QueryBoundCampaignPrefixFailureClosureV2",
    "run_query_bound_campaign_with_prefix_failure_closure_v2",
)
