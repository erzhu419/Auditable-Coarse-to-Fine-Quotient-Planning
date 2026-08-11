"""Fresh sequential runner for one preregistered query-bound campaign.

The runner durably commits the self-contained preregistration before invoking
the first scientific occurrence.  It then consumes every registered input in
denominator order through the existing source-closed occurrence executor,
independently verifies each eight-role bundle, and materializes the exact
vector-prefix analysis.

This slice proves pre-execution registration and complete positive-path
consumption.  It deliberately does not issue a scientific campaign closure or
charge campaign-orchestration work into the occurrence vectors; those remain
the next accounting/coverage boundary.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, NoReturn, Sequence

from acfqp import construction_k7_query_bound_campaign_analysis_v1 as analysis_v1
from acfqp import construction_k7_query_bound_campaign_analysis_independent_verifier_v1 as analysis_independent_v1
from acfqp import construction_k7_query_bound_campaign_preregistration_v1 as prereg_v1
from acfqp import construction_k7_query_bound_campaign_preregistration_independent_verifier_v1 as prereg_independent_v1
from acfqp import construction_k7_query_bound_complete_bundle_independent_verifier_v1 as bundle_independent_v1
from acfqp import construction_k7_query_bound_occurrence_accounting_v1 as occurrence_v1
from acfqp import construction_k7_query_bound_supervised_executor_v1 as executor_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_OCCURRENCE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_RESULT_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.101"
PROFILE_KEY = "construction_k7_query_bound_preregistered_campaign_runner_v1"
SCALAR_GATE_STATUS = "NOT_RUN"

PREREGISTRATION_FILENAME = "CAMPAIGN_PREREGISTRATION.json"
ANALYSIS_FILENAME = "RETROSPECTIVE_ACCOUNTING_ANALYSIS.json"
RESULT_FILENAME = "PREREGISTERED_CAMPAIGN_RESULT.json"
EVENT_FILENAME_TEMPLATE = "{index:04d}_COMMIT_EVENT.json"
OCCURRENCE_DIRECTORY_TEMPLATE = "occurrence-{index:04d}"

EVENT_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN
)
OCCURRENCE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_OCCURRENCE_V1_DOMAIN
)
RESULT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_RESULT_V1_DOMAIN

EVENT_KINDS = (
    "PREREGISTRATION_COMMITTED",
    "OCCURRENCE_COMMITTED",
    "ACCOUNTING_ANALYSIS_COMMITTED",
)

_EVENT_ISSUER = object()
_OCCURRENCE_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7QueryBoundPreregisteredCampaignRunnerV1Error(RuntimeError):
    """The durable sequence, registered occurrence, or analysis diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundPreregisteredCampaignRunnerV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundPreregisteredCampaignRunnerV1Error(
            f"{label} must be one content ID"
        ) from error


def _private_output_root(path: str | Path) -> Path:
    output = Path(path)
    if output.exists() or output.is_symlink():
        _fail("preregistered campaign output root must be absent")
    parent = output.parent.resolve(strict=True)
    info = parent.stat()
    if parent.is_symlink() or not parent.is_dir() or not stat.S_ISDIR(info.st_mode):
        _fail("preregistered campaign output parent is not one real directory")
    output.mkdir(mode=0o700)
    return output.resolve(strict=True)


def _write_all(fd: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = os.write(fd, raw[offset:])
        if written <= 0:
            _fail("campaign durable artifact write made no progress")
        offset += written


def _commit_file(root: Path, relative_name: str, raw: bytes) -> Path:
    if (
        type(relative_name) is not str
        or not relative_name
        or Path(relative_name).name != relative_name
        or type(raw) is not bytes
        or not raw
    ):
        _fail("campaign durable artifact target or bytes are invalid")
    target = root / relative_name
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(target, flags, 0o400)
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
    if target.read_bytes() != raw:
        _fail("campaign durable artifact differs after fsync")
    return target


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignCommitEventV1:
    _issuer: InitVar[object]
    event_index: int
    event_kind: str
    previous_event_id: str | None
    preregistration_id: str
    subject_id: str
    subject_relative_path: str
    subject_bytes_sha256: str
    subject_byte_count: int
    occurrence_index: int | None
    logical_occurrence_id: str | None
    _event_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _EVENT_ISSUER
            or type(self.event_index) is not int
            or self.event_index <= 0
            or self.event_kind not in EVENT_KINDS
            or type(self.subject_relative_path) is not str
            or not self.subject_relative_path
            or Path(self.subject_relative_path).is_absolute()
            or ".." in Path(self.subject_relative_path).parts
            or type(self.subject_byte_count) is not int
            or self.subject_byte_count <= 0
        ):
            _fail("campaign commit event is caller-minted or malformed")
        for value, label in (
            (self.preregistration_id, "event preregistration"),
            (self.subject_id, "event subject"),
            (self.subject_bytes_sha256, "event subject bytes"),
        ):
            _cid(value, label)
        if self.event_index == 1:
            if self.previous_event_id is not None or self.event_kind != EVENT_KINDS[0]:
                _fail("campaign first event is not the preregistration commit")
        else:
            _cid(self.previous_event_id, "previous campaign event")
        is_occurrence = self.event_kind == "OCCURRENCE_COMMITTED"
        if (
            is_occurrence
            != (
                type(self.occurrence_index) is int
                and self.occurrence_index > 0
                and self.logical_occurrence_id is not None
            )
        ):
            _fail("campaign event occurrence binding changed")
        if self.logical_occurrence_id is not None:
            _cid(self.logical_occurrence_id, "event logical occurrence")
        object.__setattr__(self, "_event_id", content_id(EVENT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_commit_event.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "event_index": self.event_index,
            "event_kind": self.event_kind,
            "previous_event_id": self.previous_event_id,
            "query_bound_campaign_preregistration_id": self.preregistration_id,
            "subject_id": self.subject_id,
            "subject_relative_path": self.subject_relative_path,
            "subject_bytes_sha256": self.subject_bytes_sha256,
            "subject_byte_count": self.subject_byte_count,
            "occurrence_index": self.occurrence_index,
            "logical_occurrence_id": self.logical_occurrence_id,
            "subject_committed_before_event": True,
            "file_fsync_complete": True,
            "directory_fsync_complete": True,
            "official_execution_allowed": False,
        }

    @property
    def event_id(self) -> str:
        expected = content_id(EVENT_DOMAIN, self._payload())
        if expected != self._event_id:
            _fail("campaign commit event changed after issuance")
        return expected

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_commit_event_id": self.event_id}


@dataclass(frozen=True, slots=True)
class QueryBoundPreregisteredCampaignOccurrenceV1:
    _issuer: InitVar[object]
    preregistration_id: str
    workload_spec_id: str
    occurrence_index: int
    occurrence_spec_id: str
    logical_occurrence_id: str
    output_directory_name: str
    bundle_verification_id: str
    operational_trace_id: str
    shared_measurement_id: str
    shared_receipt_set_id: str
    work_vector_ids: tuple[str, ...]
    comparison_vector_ids: tuple[str, ...]
    projection_proof_ids: tuple[str, ...]
    output_bytes: int
    output_manifest_sha256: str
    output_manifest_byte_count: int
    commit_event_id: str
    _row_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _OCCURRENCE_ISSUER
            or type(self.occurrence_index) is not int
            or self.occurrence_index <= 0
            or self.output_directory_name
            != OCCURRENCE_DIRECTORY_TEMPLATE.format(index=self.occurrence_index)
            or len(self.work_vector_ids) != 3
            or len(self.comparison_vector_ids) != 3
            or len(self.projection_proof_ids) != 3
            or type(self.output_bytes) is not int
            or self.output_bytes <= 0
            or type(self.output_manifest_byte_count) is not int
            or self.output_manifest_byte_count <= 0
        ):
            _fail("executed campaign occurrence is caller-minted or malformed")
        for value, label in (
            (self.preregistration_id, "occurrence preregistration"),
            (self.workload_spec_id, "occurrence workload"),
            (self.occurrence_spec_id, "occurrence spec"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.bundle_verification_id, "bundle verification"),
            (self.operational_trace_id, "operational trace"),
            (self.shared_measurement_id, "shared measurement"),
            (self.shared_receipt_set_id, "shared receipt set"),
            (self.output_manifest_sha256, "output manifest bytes"),
            (self.commit_event_id, "occurrence commit event"),
            *((value, "work vector") for value in self.work_vector_ids),
            *((value, "comparison vector") for value in self.comparison_vector_ids),
            *((value, "projection proof") for value in self.projection_proof_ids),
        ):
            _cid(value, label)
        object.__setattr__(self, "_row_id", content_id(OCCURRENCE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_preregistered_campaign_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "query_bound_campaign_preregistration_id": self.preregistration_id,
            "campaign_workload_spec_id": self.workload_spec_id,
            "occurrence_index": self.occurrence_index,
            "preregistered_occurrence_spec_id": self.occurrence_spec_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "output_directory_name": self.output_directory_name,
            "complete_bundle_verification_id": self.bundle_verification_id,
            "operational_trace_id": self.operational_trace_id,
            "shared_measurement_id": self.shared_measurement_id,
            "shared_resource_receipt_set_id": self.shared_receipt_set_id,
            "work_vector_ids": list(self.work_vector_ids),
            "comparison_vector_ids": list(self.comparison_vector_ids),
            "actual_projection_proof_ids": list(self.projection_proof_ids),
            "io.output_bytes": self.output_bytes,
            "output_manifest_sha256": self.output_manifest_sha256,
            "output_manifest_byte_count": self.output_manifest_byte_count,
            "campaign_commit_event_id": self.commit_event_id,
            "registered_inputs_consumed_exactly_once": True,
            "construction_terminal_class": "PLAN_CERTIFICATE",
            "construction_terminal_code": "FULL_GROUND_FALLBACK",
            "scientific_planner_recomputed_by_campaign_verifier": False,
            "official_execution_allowed": False,
        }

    @property
    def row_id(self) -> str:
        expected = content_id(OCCURRENCE_DOMAIN, self._payload())
        if expected != self._row_id:
            _fail("executed campaign occurrence changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "preregistered_campaign_occurrence_id": self.row_id}


@dataclass(frozen=True, slots=True)
class QueryBoundPreregisteredCampaignResultV1:
    _issuer: InitVar[object]
    preregistration_id: str
    preregistration_verification_id: str
    workload_spec_id: str
    runtime_preparation_id: str
    runtime_tree_id: str
    source_closure_id: str
    preregistration_bytes_sha256: str
    preregistration_byte_count: int
    events: tuple[QueryBoundCampaignCommitEventV1, ...]
    occurrences: tuple[QueryBoundPreregisteredCampaignOccurrenceV1, ...]
    accounting_analysis_id: str
    accounting_analysis_verification_id: str
    accounting_analysis_bytes: bytes = field(repr=False)
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        count = len(self.occurrences)
        if (
            _issuer is not _RESULT_ISSUER
            or count < 2
            or len(self.events) != count + 2
            or tuple(row.event_index for row in self.events)
            != tuple(range(1, len(self.events) + 1))
            or self.events[0].event_kind != "PREREGISTRATION_COMMITTED"
            or self.events[-1].event_kind != "ACCOUNTING_ANALYSIS_COMMITTED"
            or any(
                row.previous_event_id != self.events[index - 1].event_id
                for index, row in enumerate(self.events[1:], start=1)
            )
            or tuple(row.occurrence_index for row in self.occurrences)
            != tuple(range(1, count + 1))
            or tuple(row.commit_event_id for row in self.occurrences)
            != tuple(row.event_id for row in self.events[1:-1])
            or type(self.accounting_analysis_bytes) is not bytes
            or not self.accounting_analysis_bytes
            or type(self.preregistration_byte_count) is not int
            or self.preregistration_byte_count <= 0
        ):
            _fail("preregistered campaign result is caller-minted or incomplete")
        for value, label in (
            (self.preregistration_id, "result preregistration"),
            (self.preregistration_verification_id, "preregistration verification"),
            (self.workload_spec_id, "result workload"),
            (self.runtime_preparation_id, "result runtime preparation"),
            (self.runtime_tree_id, "result runtime tree"),
            (self.source_closure_id, "result source closure"),
            (self.preregistration_bytes_sha256, "result preregistration bytes"),
            (self.accounting_analysis_id, "accounting analysis"),
            (self.accounting_analysis_verification_id, "accounting analysis verification"),
        ):
            _cid(value, label)
        if hashlib.sha256(self.accounting_analysis_bytes).hexdigest() != self.events[-1].subject_bytes_sha256:
            _fail("campaign analysis bytes crossed the final commit event")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        count = len(self.occurrences)
        return {
            "schema": "acfqp.construction_k7_query_bound_preregistered_campaign_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "query_bound_campaign_preregistration_id": self.preregistration_id,
            "campaign_preregistration_verification_id": self.preregistration_verification_id,
            "campaign_workload_spec_id": self.workload_spec_id,
            "runtime_preparation_id": self.runtime_preparation_id,
            "runtime_tree_id": self.runtime_tree_id,
            "source_closure_id": self.source_closure_id,
            "preregistration_bytes_sha256": self.preregistration_bytes_sha256,
            "preregistration_byte_count": self.preregistration_byte_count,
            "commit_events": [row.to_document() for row in self.events],
            "executed_occurrences": [row.to_document() for row in self.occurrences],
            "accounting_analysis_id": self.accounting_analysis_id,
            "accounting_analysis_verification_id": self.accounting_analysis_verification_id,
            "accounting_analysis_bytes_hex": self.accounting_analysis_bytes.hex(),
            "logical_occurrence_count": count,
            "closure_denominator": count,
            "certification_coverage_denominator": count,
            "economics_cost_denominator": count,
            "campaign_preregistration_present": True,
            "preregistration_committed_before_first_occurrence": True,
            "all_registered_occurrences_executed_exactly_once": True,
            "posthoc_occurrence_deletion_observed": False,
            "posthoc_occurrence_insertion_observed": False,
            "registered_scientific_inputs_consumed": True,
            "embedded_source_archive_bound_to_runtime": True,
            "scientific_planner_executed_for_every_occurrence": True,
            "all_occurrence_accounting_bundles_independently_replayed": True,
            "scientific_planner_recomputed_by_campaign_verifier": False,
            "accounting_campaign_execution_evidence": True,
            "scientific_campaign_closure_issued": False,
            "failure_path_campaign_closure_present": False,
            "campaign_orchestration_work_vector_present": False,
            "certificate_coverage_gate_status": "NOT_RUN",
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "scalar_gate_status": SCALAR_GATE_STATUS,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        expected = content_id(RESULT_DOMAIN, self._payload())
        if expected != self._result_id:
            _fail("preregistered campaign result changed after issuance")
        return expected

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "preregistered_campaign_result_id": self.result_id}


def _commit_event(
    *,
    root: Path,
    index: int,
    kind: str,
    previous: QueryBoundCampaignCommitEventV1 | None,
    preregistration_id: str,
    subject_id: str,
    subject_relative_path: str,
    subject_bytes: bytes,
    occurrence_index: int | None = None,
    logical_occurrence_id: str | None = None,
) -> QueryBoundCampaignCommitEventV1:
    event = QueryBoundCampaignCommitEventV1(
        _EVENT_ISSUER,
        index,
        kind,
        None if previous is None else previous.event_id,
        preregistration_id,
        subject_id,
        subject_relative_path,
        hashlib.sha256(subject_bytes).hexdigest(),
        len(subject_bytes),
        occurrence_index,
        logical_occurrence_id,
    )
    _commit_file(
        root,
        EVENT_FILENAME_TEMPLATE.format(index=index),
        event.canonical_bytes,
    )
    return event


def _require_bundle_matches_registration(
    *,
    registered: prereg_v1.QueryBoundCampaignPreregisteredOccurrenceV1,
    registration: prereg_v1.QueryBoundCampaignPreregistrationV1,
    output: Path,
    verification: bundle_independent_v1.QueryBoundCompleteBundleVerificationV1,
) -> None:
    business_path = output / "BUSINESS_RESULT.json"
    business_raw = business_path.read_bytes()
    try:
        business = loads_canonical_json(business_raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundPreregisteredCampaignRunnerV1Error(
            "campaign business result is not canonical JSON"
        ) from error
    preparation = business.get("runtime_preparation")
    request = business.get("supervised_request")
    if type(preparation) is not dict or type(request) is not dict:
        _fail("campaign business result omitted runtime preparation or request")
    inventory = request.get("input_inventory")
    if type(inventory) is not list:
        _fail("campaign business result omitted input inventory")
    expected_bytes = registered.input_bytes_by_role
    expected_inventory = [
        {
            "role": role,
            "filename": filename,
            "byte_count": len(expected_bytes[role]),
            "sha256": hashlib.sha256(expected_bytes[role]).hexdigest(),
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
        or inventory != expected_inventory
    ):
        _fail("executed occurrence differs from preregistered source or inputs")


def run_query_bound_preregistered_campaign_v1(
    registration: prereg_v1.QueryBoundCampaignPreregistrationV1,
    *,
    output_directory: str | Path,
    timeout_seconds: int = executor_v1.DEFAULT_TIMEOUT_SECONDS,
) -> QueryBoundPreregisteredCampaignResultV1:
    """Commit registration, then execute every registered occurrence in order."""

    try:
        prereg_v1.verify_query_bound_campaign_preregistration_v1(registration)
        prereg_verification = (
            prereg_independent_v1.verify_query_bound_campaign_preregistration_bytes_v1(
                registration.canonical_bytes
            )
        )
    except Exception as error:
        raise ConstructionK7QueryBoundPreregisteredCampaignRunnerV1Error(
            "campaign runner rejected its preregistration before output creation"
        ) from error
    if (
        type(timeout_seconds) is not int
        or not (0 < timeout_seconds <= 7_200)
    ):
        _fail("campaign occurrence timeout is outside its finite profile")
    root = _private_output_root(output_directory)
    registration_raw = registration.canonical_bytes
    _commit_file(root, PREREGISTRATION_FILENAME, registration_raw)
    events: list[QueryBoundCampaignCommitEventV1] = []
    events.append(
        _commit_event(
            root=root,
            index=1,
            kind="PREREGISTRATION_COMMITTED",
            previous=None,
            preregistration_id=registration.preregistration_id,
            subject_id=registration.preregistration_id,
            subject_relative_path=PREREGISTRATION_FILENAME,
            subject_bytes=registration_raw,
        )
    )
    rows: list[QueryBoundPreregisteredCampaignOccurrenceV1] = []
    bundle_directories: list[Path] = []
    for registered in registration.occurrences:
        index = registered.occurrence_index
        directory_name = OCCURRENCE_DIRECTORY_TEMPLATE.format(index=index)
        occurrence_root = root / directory_name
        occurrence_root.mkdir(mode=0o700)
        pending_trace = occurrence_root / ".OPERATIONAL_TRACE.pending"
        inputs = registered.input_bytes_by_role
        execution = executor_v1.execute_query_bound_accounted_v1(
            registration.runtime_preparation,
            source_trace_bytes=inputs["SOURCE_TRACE"],
            build_epoch_envelope_bytes=inputs["BUILD_EPOCH_ENVELOPE"],
            root_query_result_bytes=inputs["ROOT_QUERY_RESULT"],
            overlay_bytes=inputs["RECOVERY_OVERLAY"],
            request_bytes=inputs["RECOVERY_REQUEST"],
            trace_output_path=pending_trace,
            timeout_seconds=timeout_seconds,
        )
        occurrence_v1.finalize_query_bound_occurrence_accounting_v1(
            supervised_execution=execution,
            output_directory=occurrence_root,
            pending_trace_path=pending_trace,
        )
        verification = (
            bundle_independent_v1.verify_query_bound_complete_bundle_directory_v1(
                occurrence_root
            )
        )
        _require_bundle_matches_registration(
            registered=registered,
            registration=registration,
            output=occurrence_root,
            verification=verification,
        )
        manifest_raw = (occurrence_root / "OUTPUT_MANIFEST.json").read_bytes()
        event = _commit_event(
            root=root,
            index=len(events) + 1,
            kind="OCCURRENCE_COMMITTED",
            previous=events[-1],
            preregistration_id=registration.preregistration_id,
            subject_id=verification.verification_id,
            subject_relative_path=f"{directory_name}/OUTPUT_MANIFEST.json",
            subject_bytes=manifest_raw,
            occurrence_index=index,
            logical_occurrence_id=registered.logical_occurrence_id,
        )
        events.append(event)
        rows.append(
            QueryBoundPreregisteredCampaignOccurrenceV1(
                _OCCURRENCE_ISSUER,
                registration.preregistration_id,
                registration.workload_spec.workload_spec_id,
                index,
                registered.occurrence_spec_id,
                registered.logical_occurrence_id,
                directory_name,
                verification.verification_id,
                verification.operational_trace_id,
                verification.shared_measurement_id,
                verification.shared_receipt_set_id,
                verification.work_vector_ids,
                verification.comparison_vector_ids,
                verification.projection_proof_ids,
                verification.output_bytes,
                hashlib.sha256(manifest_raw).hexdigest(),
                len(manifest_raw),
                event.event_id,
            )
        )
        bundle_directories.append(occurrence_root)
    analysis_spec = analysis_v1.freeze_query_bound_campaign_analysis_spec_v1(
        ordered_occurrence_ids=tuple(
            row.logical_occurrence_id for row in registration.occurrences
        ),
        permutation_cap=registration.workload_spec.permutation_cap,
    )
    analysis = analysis_v1.analyze_query_bound_campaign_bundles_v1(
        analysis_spec,
        bundle_directories=bundle_directories,
    )
    analysis_verification = (
        analysis_independent_v1.verify_query_bound_campaign_analysis_bytes_v1(
            analysis.canonical_bytes,
            bundle_directories=bundle_directories,
        )
    )
    _commit_file(root, ANALYSIS_FILENAME, analysis.canonical_bytes)
    events.append(
        _commit_event(
            root=root,
            index=len(events) + 1,
            kind="ACCOUNTING_ANALYSIS_COMMITTED",
            previous=events[-1],
            preregistration_id=registration.preregistration_id,
            subject_id=analysis.analysis_id,
            subject_relative_path=ANALYSIS_FILENAME,
            subject_bytes=analysis.canonical_bytes,
        )
    )
    result = QueryBoundPreregisteredCampaignResultV1(
        _RESULT_ISSUER,
        registration.preregistration_id,
        prereg_verification.verification_id,
        registration.workload_spec.workload_spec_id,
        registration.runtime_preparation.preparation_id,
        registration.runtime_preparation.manifest.runtime_tree_id,
        registration.runtime_preparation.source_closure.closure_id,
        hashlib.sha256(registration_raw).hexdigest(),
        len(registration_raw),
        tuple(events),
        tuple(rows),
        analysis.analysis_id,
        analysis_verification.verification_id,
        analysis.canonical_bytes,
    )
    _commit_file(root, RESULT_FILENAME, result.canonical_bytes)
    return verify_query_bound_preregistered_campaign_result_v1(
        result,
        registration=registration,
    )


def verify_query_bound_preregistered_campaign_result_v1(
    claimed: QueryBoundPreregisteredCampaignResultV1,
    *,
    registration: prereg_v1.QueryBoundCampaignPreregistrationV1,
) -> QueryBoundPreregisteredCampaignResultV1:
    """Verify the issued in-process positive-path result and identity joins."""

    if (
        type(claimed) is not QueryBoundPreregisteredCampaignResultV1
        or type(registration) is not prereg_v1.QueryBoundCampaignPreregistrationV1
    ):
        _fail("campaign result verifier received a foreign result or registration")
    _ = claimed.result_id
    if (
        claimed.preregistration_id != registration.preregistration_id
        or claimed.workload_spec_id != registration.workload_spec.workload_spec_id
        or tuple(row.logical_occurrence_id for row in claimed.occurrences)
        != tuple(row.logical_occurrence_id for row in registration.occurrences)
        or tuple(row.occurrence_spec_id for row in claimed.occurrences)
        != tuple(row.occurrence_spec_id for row in registration.occurrences)
    ):
        _fail("campaign result crossed its preregistered denominator")
    return claimed


__all__ = (
    "ANALYSIS_FILENAME",
    "ConstructionK7QueryBoundPreregisteredCampaignRunnerV1Error",
    "PREREGISTRATION_FILENAME",
    "QueryBoundCampaignCommitEventV1",
    "QueryBoundPreregisteredCampaignOccurrenceV1",
    "QueryBoundPreregisteredCampaignResultV1",
    "RESULT_FILENAME",
    "run_query_bound_preregistered_campaign_v1",
    "verify_query_bound_preregistered_campaign_result_v1",
)
