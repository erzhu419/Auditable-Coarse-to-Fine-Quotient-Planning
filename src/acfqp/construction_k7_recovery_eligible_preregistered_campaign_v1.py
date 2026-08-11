"""Preregistered multi-occurrence campaign for the recovery-eligible loop.

The campaign freezes one source-closed runtime and one immutable three-blob
RAPM/proof-cache input set before launching any occurrence.  Every registered
logical occurrence is then executed exactly once, committed as a complete
occurrence-accounting bundle, and retained in all campaign denominators.

This slice closes the scientific/cost denominator for the registered workload.
It deliberately does not issue campaign-orchestration WorkVectors, an official
scalar, economics claims, or an official execution authorization.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, NoReturn, Sequence

from acfqp.accounting_v1 import SHARED_AXES
from acfqp import construction_k7_recovery_eligible_occurrence_accounting_v1 as occurrence_v1
from acfqp import construction_k7_recovery_eligible_supervised_executor_v1 as executor_v1
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_INPUT_BLOB_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_SPEC_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_WORKLOAD_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.117"
PROFILE_KEY = "construction_k7_recovery_eligible_preregistered_campaign_v1"
INPUT_ROLES = tuple(role for role, _filename in executor_v1.INPUT_ROLES)
MIN_OCCURRENCE_COUNT = 2
MAX_OCCURRENCE_COUNT = 32
PEAK_AXES = frozenset({"peak_mounted_bytes", "peak_working_bytes"})

INPUT_BLOB_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_INPUT_BLOB_V1_DOMAIN
)
OCCURRENCE_SPEC_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_SPEC_V1_DOMAIN
)
WORKLOAD_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_WORKLOAD_V1_DOMAIN
PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
)
COMMIT_EVENT_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN
)
OCCURRENCE_ROW_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
)
CLOSURE_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_CLOSURE_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {
        INPUT_BLOB_DOMAIN,
        OCCURRENCE_SPEC_DOMAIN,
        WORKLOAD_DOMAIN,
        PREREGISTRATION_DOMAIN,
        COMMIT_EVENT_DOMAIN,
        OCCURRENCE_ROW_DOMAIN,
        CLOSURE_DOMAIN,
        RESULT_DOMAIN,
    }
)
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("recovery campaign domains are not centrally registered")

_BLOB_ISSUER = object()
_SPEC_ISSUER = object()
_WORKLOAD_ISSUER = object()
_PREREGISTRATION_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7RecoveryEligiblePreregisteredCampaignV1Error(RuntimeError):
    """The frozen workload, committed bundle, or denominator diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryEligiblePreregisteredCampaignV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligiblePreregisteredCampaignV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are absent")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligiblePreregisteredCampaignV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCampaignInputBlobV1:
    _issuer: InitVar[object]
    role: str
    canonical_bytes: bytes = field(repr=False)
    _blob_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BLOB_ISSUER or self.role not in INPUT_ROLES:
            _fail("campaign input blob is caller-minted or has an unknown role")
        _canonical_object(self.canonical_bytes, f"campaign input {self.role}")
        object.__setattr__(self, "_blob_id", content_id(INPUT_BLOB_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_campaign_input_blob.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "role": self.role,
            "canonical_json_bytes_hex": self.canonical_bytes.hex(),
            "byte_count": len(self.canonical_bytes),
            "sha256": hashlib.sha256(self.canonical_bytes).hexdigest(),
        }

    @property
    def blob_id(self) -> str:
        expected = content_id(INPUT_BLOB_DOMAIN, self._payload())
        if expected != self._blob_id:
            _fail("campaign input blob changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_input_blob_id": self.blob_id}


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCampaignOccurrenceSpecV1:
    _issuer: InitVar[object]
    occurrence_index: int
    logical_occurrence_id: str
    query_ordinal: int
    input_blob_ids: tuple[str, ...]
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _SPEC_ISSUER
            or type(self.occurrence_index) is not int
            or self.occurrence_index <= 0
            or type(self.query_ordinal) is not int
            or self.query_ordinal <= 1
            or type(self.input_blob_ids) is not tuple
            or len(self.input_blob_ids) != len(INPUT_ROLES)
        ):
            _fail("campaign occurrence spec is caller-minted or malformed")
        _cid(self.logical_occurrence_id, "campaign logical occurrence")
        for value in self.input_blob_ids:
            _cid(value, "campaign occurrence input blob")
        object.__setattr__(
            self, "_spec_id", content_id(OCCURRENCE_SPEC_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_campaign_occurrence_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_index": self.occurrence_index,
            "logical_occurrence_id": self.logical_occurrence_id,
            "query_ordinal": self.query_ordinal,
            "input_blob_ids_by_role": [
                {"role": role, "campaign_input_blob_id": blob_id}
                for role, blob_id in zip(INPUT_ROLES, self.input_blob_ids, strict=True)
            ],
            "execution_result_present": False,
            "registered_before_first_worker_launch": True,
            "official_execution_allowed": False,
        }

    @property
    def occurrence_spec_id(self) -> str:
        expected = content_id(OCCURRENCE_SPEC_DOMAIN, self._payload())
        if expected != self._spec_id:
            _fail("campaign occurrence spec changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_occurrence_spec_id": self.occurrence_spec_id}


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCampaignWorkloadV1:
    _issuer: InitVar[object]
    runtime_preparation_id: str
    runtime_tree_id: str
    source_closure_id: str
    input_blob_ids: tuple[str, ...]
    occurrences: tuple[RecoveryEligibleCampaignOccurrenceSpecV1, ...]
    _workload_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        count = len(self.occurrences)
        for value, label in (
            (self.runtime_preparation_id, "campaign runtime preparation"),
            (self.runtime_tree_id, "campaign runtime tree"),
            (self.source_closure_id, "campaign source closure"),
        ):
            _cid(value, label)
        if (
            _issuer is not _WORKLOAD_ISSUER
            or not (MIN_OCCURRENCE_COUNT <= count <= MAX_OCCURRENCE_COUNT)
            or tuple(row.occurrence_index for row in self.occurrences)
            != tuple(range(1, count + 1))
            or len({row.logical_occurrence_id for row in self.occurrences}) != count
            or len({row.query_ordinal for row in self.occurrences}) != count
            or len({row.occurrence_spec_id for row in self.occurrences}) != count
            or any(row.input_blob_ids != self.input_blob_ids for row in self.occurrences)
        ):
            _fail("campaign workload denominator is incomplete or duplicated")
        for value in self.input_blob_ids:
            _cid(value, "campaign workload input blob")
        object.__setattr__(
            self, "_workload_id", content_id(WORKLOAD_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_campaign_workload.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "runtime_preparation_id": self.runtime_preparation_id,
            "runtime_tree_id": self.runtime_tree_id,
            "source_closure_id": self.source_closure_id,
            "shared_input_blob_ids": list(self.input_blob_ids),
            "ordered_occurrence_spec_ids": [row.occurrence_spec_id for row in self.occurrences],
            "ordered_logical_occurrence_ids": [row.logical_occurrence_id for row in self.occurrences],
            "ordered_query_ordinals": [row.query_ordinal for row in self.occurrences],
            "registered_logical_occurrence_count": len(self.occurrences),
            "denominator_frozen_before_execution": True,
            "shared_rapm_and_proof_cache_inputs_required": True,
            "occurrence_deletion_allowed": False,
            "official_execution_allowed": False,
        }

    @property
    def workload_id(self) -> str:
        expected = content_id(WORKLOAD_DOMAIN, self._payload())
        if expected != self._workload_id:
            _fail("campaign workload changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_workload_id": self.workload_id}


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCampaignPreregistrationV1:
    _issuer: InitVar[object]
    runtime_preparation: executor_v1.RecoveryEligibleRuntimePreparationV1 = field(
        repr=False, compare=False
    )
    input_blobs: tuple[RecoveryEligibleCampaignInputBlobV1, ...]
    workload: RecoveryEligibleCampaignWorkloadV1
    _preregistration_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PREREGISTRATION_ISSUER
            or type(self.runtime_preparation)
            is not executor_v1.RecoveryEligibleRuntimePreparationV1
            or tuple(row.role for row in self.input_blobs) != INPUT_ROLES
            or any(type(row) is not RecoveryEligibleCampaignInputBlobV1 for row in self.input_blobs)
            or type(self.workload) is not RecoveryEligibleCampaignWorkloadV1
            or self.workload.runtime_preparation_id != self.runtime_preparation.preparation_id
            or self.workload.runtime_tree_id != self.runtime_preparation.manifest.runtime_tree_id
            or self.workload.source_closure_id != self.runtime_preparation.source_closure.closure_id
            or self.workload.input_blob_ids != tuple(row.blob_id for row in self.input_blobs)
        ):
            _fail("campaign preregistration is caller-minted or crossed")
        object.__setattr__(
            self,
            "_preregistration_id",
            content_id(PREREGISTRATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_campaign_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "runtime_preparation": self.runtime_preparation.to_document(),
            "input_blobs": [row.to_document() for row in self.input_blobs],
            "workload": self.workload.to_document(),
            "registration_stage": "BEFORE_FIRST_OCCURRENCE_WORKER_LAUNCH",
            "campaign_preregistration_present": True,
            "execution_started_by_this_artifact": False,
            "campaign_result_present": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }

    @property
    def preregistration_id(self) -> str:
        expected = content_id(PREREGISTRATION_DOMAIN, self._payload())
        if expected != self._preregistration_id:
            _fail("campaign preregistration changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_preregistration_id": self.preregistration_id}


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCampaignCommitEventV1:
    sequence: int
    event_kind: str
    previous_event_id: str | None
    subject_id: str
    subject_filename: str
    subject_byte_count: int
    subject_sha256: str
    occurrence_index: int | None
    logical_occurrence_id: str | None

    def __post_init__(self) -> None:
        if (
            type(self.sequence) is not int
            or self.sequence < 0
            or self.event_kind not in {"PREREGISTRATION_COMMITTED", "OCCURRENCE_BUNDLE_COMMITTED"}
            or type(self.subject_filename) is not str
            or not self.subject_filename
            or "/" in self.subject_filename
            or type(self.subject_byte_count) is not int
            or self.subject_byte_count <= 0
        ):
            _fail("campaign commit event is malformed")
        _cid(self.subject_id, "campaign commit subject")
        _cid(self.subject_sha256, "campaign commit digest")
        if self.sequence == 0:
            if (
                self.event_kind != "PREREGISTRATION_COMMITTED"
                or self.previous_event_id is not None
                or self.occurrence_index is not None
                or self.logical_occurrence_id is not None
            ):
                _fail("campaign genesis commit event changed")
        else:
            _cid(self.previous_event_id, "campaign previous event")
            if (
                self.event_kind != "OCCURRENCE_BUNDLE_COMMITTED"
                or self.occurrence_index != self.sequence
                or self.logical_occurrence_id is None
            ):
                _fail("campaign occurrence commit event changed")
            _cid(self.logical_occurrence_id, "campaign committed occurrence")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_campaign_commit_event.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence": self.sequence,
            "event_kind": self.event_kind,
            "previous_event": (
                {"kind": "GENESIS", "reason": "PREREGISTRATION_IS_FIRST"}
                if self.previous_event_id is None
                else {"kind": "PREVIOUS_EVENT", "campaign_commit_event_id": self.previous_event_id}
            ),
            "subject_id": self.subject_id,
            "subject_filename": self.subject_filename,
            "subject_byte_count": self.subject_byte_count,
            "subject_sha256": self.subject_sha256,
            "occurrence_index": self.occurrence_index,
            "logical_occurrence_id": self.logical_occurrence_id,
            "file_fsync_completed": True,
            "directory_fsync_completed": True,
            "construction_only": True,
            "official_execution_allowed": False,
        }

    @property
    def event_id(self) -> str:
        return content_id(COMMIT_EVENT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_commit_event_id": self.event_id}


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCampaignOccurrenceRowV1:
    occurrence_spec_id: str
    occurrence_index: int
    logical_occurrence_id: str
    query_ordinal: int
    occurrence_bundle_id: str
    output_commit_id: str
    persistent_proof_cache_id: str
    recovery_eligible_checkpoint_id: str
    occurrence_comparison_values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_spec_id, "campaign row spec"),
            (self.logical_occurrence_id, "campaign row occurrence"),
            (self.occurrence_bundle_id, "campaign row bundle"),
            (self.output_commit_id, "campaign row output commit"),
            (self.persistent_proof_cache_id, "campaign row proof cache"),
            (self.recovery_eligible_checkpoint_id, "campaign row checkpoint"),
        ):
            _cid(value, label)
        if (
            type(self.occurrence_index) is not int
            or self.occurrence_index <= 0
            or type(self.query_ordinal) is not int
            or self.query_ordinal <= 1
            or tuple(axis for axis, _value in self.occurrence_comparison_values) != SHARED_AXES
            or any(type(value) is not int or value < 0 for _axis, value in self.occurrence_comparison_values)
        ):
            _fail("campaign occurrence row is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_campaign_occurrence_row.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_occurrence_spec_id": self.occurrence_spec_id,
            "occurrence_index": self.occurrence_index,
            "logical_occurrence_id": self.logical_occurrence_id,
            "query_ordinal": self.query_ordinal,
            "occurrence_accounting_bundle_id": self.occurrence_bundle_id,
            "output_commit_id": self.output_commit_id,
            "persistent_proof_cache_id": self.persistent_proof_cache_id,
            "recovery_eligible_checkpoint_id": self.recovery_eligible_checkpoint_id,
            "occurrence_comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in self.occurrence_comparison_values
            ],
            "terminal_scope": "LOGICAL_OCCURRENCE",
            "terminal_class": "PLAN_CERTIFICATE",
            "terminal_code": "FULL_GROUND_FALLBACK",
            "closure_denominator_included": True,
            "certification_coverage_denominator_included": True,
            "economics_cost_denominator_included": True,
            "abstract_plan_certificate_issued": False,
            "local_recovery_certificate_issued": False,
            "full_ground_fallback_certificate_issued": True,
            "official_execution_allowed": False,
        }

    @property
    def row_id(self) -> str:
        return content_id(OCCURRENCE_ROW_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_occurrence_row_id": self.row_id}


def _prefix_vectors(
    rows: Sequence[RecoveryEligibleCampaignOccurrenceRowV1],
) -> tuple[tuple[tuple[str, int], ...], ...]:
    running = {axis: 0 for axis in SHARED_AXES}
    prefixes: list[tuple[tuple[str, int], ...]] = []
    for row in rows:
        for axis, value in row.occurrence_comparison_values:
            running[axis] = max(running[axis], value) if axis in PEAK_AXES else running[axis] + value
        prefixes.append(tuple((axis, running[axis]) for axis in SHARED_AXES))
    return tuple(prefixes)


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCampaignClosureV1:
    preregistration_id: str
    workload_id: str
    runtime_preparation_id: str
    occurrence_rows: tuple[RecoveryEligibleCampaignOccurrenceRowV1, ...]
    commit_event_ids: tuple[str, ...]
    vector_prefix_totals: tuple[tuple[tuple[str, int], ...], ...]

    def __post_init__(self) -> None:
        count = len(self.occurrence_rows)
        for value, label in (
            (self.preregistration_id, "campaign closure preregistration"),
            (self.workload_id, "campaign closure workload"),
            (self.runtime_preparation_id, "campaign closure runtime"),
        ):
            _cid(value, label)
        if (
            not (MIN_OCCURRENCE_COUNT <= count <= MAX_OCCURRENCE_COUNT)
            or tuple(row.occurrence_index for row in self.occurrence_rows)
            != tuple(range(1, count + 1))
            or len(self.commit_event_ids) != count + 1
            or len(set(self.commit_event_ids)) != count + 1
            or any(type(row) is not RecoveryEligibleCampaignOccurrenceRowV1 for row in self.occurrence_rows)
            or self.vector_prefix_totals != _prefix_vectors(self.occurrence_rows)
        ):
            _fail("campaign closure denominator or vector prefixes changed")
        for value in self.commit_event_ids:
            _cid(value, "campaign closure commit event")

    def _payload(self) -> dict[str, Any]:
        count = len(self.occurrence_rows)
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_campaign_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "campaign_workload_id": self.workload_id,
            "runtime_preparation_id": self.runtime_preparation_id,
            "ordered_occurrence_row_ids": [row.row_id for row in self.occurrence_rows],
            "ordered_commit_event_ids": list(self.commit_event_ids),
            "registered_logical_occurrence_ids": [row.logical_occurrence_id for row in self.occurrence_rows],
            "logical_occurrence_count": count,
            "closure_denominator": count,
            "certification_coverage_denominator": count,
            "economics_cost_denominator": count,
            "plan_certificate_count": count,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": 0,
            "abstract_plan_certificate_count": 0,
            "local_ground_recovery_certificate_count": 0,
            "full_ground_fallback_certificate_count": count,
            "vector_prefix_totals": [
                [{"axis": axis, "value": value} for axis, value in prefix]
                for prefix in self.vector_prefix_totals
            ],
            "full_registered_denominator_recomputed": True,
            "occurrence_deletion_observed": False,
            "shared_persistent_proof_cache_reused_across_all_occurrences": True,
            "campaign_denominator_closure_issued": True,
            "campaign_orchestration_work_vector_issued": False,
            "cross_occurrence_overlay_persistence_authority": False,
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
class RecoveryEligiblePreregisteredCampaignResultV1:
    _issuer: InitVar[object]
    campaign_directory: Path = field(repr=False, compare=False)
    preregistration: RecoveryEligibleCampaignPreregistrationV1 = field(repr=False)
    preregistration_event: RecoveryEligibleCampaignCommitEventV1
    occurrence_bundles: tuple[occurrence_v1.RecoveryEligibleOccurrenceAccountingBundleV1, ...] = field(repr=False)
    occurrence_rows: tuple[RecoveryEligibleCampaignOccurrenceRowV1, ...]
    occurrence_events: tuple[RecoveryEligibleCampaignCommitEventV1, ...]
    closure: RecoveryEligibleCampaignClosureV1
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        count = len(self.preregistration.workload.occurrences)
        if (
            _issuer is not _RESULT_ISSUER
            or not isinstance(self.campaign_directory, Path)
            or type(self.preregistration) is not RecoveryEligibleCampaignPreregistrationV1
            or type(self.preregistration_event) is not RecoveryEligibleCampaignCommitEventV1
            or self.preregistration_event.sequence != 0
            or len(self.occurrence_bundles) != count
            or len(self.occurrence_rows) != count
            or len(self.occurrence_events) != count
            or self.closure.occurrence_rows != self.occurrence_rows
            or self.closure.commit_event_ids
            != (self.preregistration_event.event_id, *(row.event_id for row in self.occurrence_events))
        ):
            _fail("campaign result is caller-minted or incomplete")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_campaign_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration.preregistration_id,
            "campaign_workload_id": self.preregistration.workload.workload_id,
            "ordered_occurrence_accounting_bundle_ids": [row.bundle_id for row in self.occurrence_bundles],
            "ordered_occurrence_row_ids": [row.row_id for row in self.occurrence_rows],
            "ordered_commit_event_ids": [self.preregistration_event.event_id, *(row.event_id for row in self.occurrence_events)],
            "campaign_closure_id": self.closure.closure_id,
            "registered_occurrences_executed_once": True,
            "complete_occurrence_bundles_committed_once": True,
            "full_registered_denominator_closed_without_deletion": True,
            "scientific_terminal_class": "PLAN_CERTIFICATE",
            "scientific_terminal_code": "FULL_GROUND_FALLBACK",
            "campaign_orchestration_work_vector_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        expected = content_id(RESULT_DOMAIN, self._payload())
        if expected != self._result_id:
            _fail("campaign result changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_result_id": self.result_id}


def preregister_recovery_eligible_campaign_v1(
    *,
    runtime_preparation: executor_v1.RecoveryEligibleRuntimePreparationV1,
    binding_bytes: bytes,
    snapshot_bytes: bytes,
    transition_bytes: bytes,
    occurrence_requests: Sequence[tuple[str, int]],
) -> RecoveryEligibleCampaignPreregistrationV1:
    if type(runtime_preparation) is not executor_v1.RecoveryEligibleRuntimePreparationV1:
        _fail("campaign preregistration requires exact runtime preparation")
    _ = runtime_preparation.preparation_id
    if type(occurrence_requests) not in {tuple, list}:
        _fail("campaign occurrence requests must be one ordered sequence")
    blobs = tuple(
        RecoveryEligibleCampaignInputBlobV1(_BLOB_ISSUER, role, raw)
        for role, raw in zip(
            INPUT_ROLES,
            (binding_bytes, snapshot_bytes, transition_bytes),
            strict=True,
        )
    )
    blob_ids = tuple(row.blob_id for row in blobs)
    specs: list[RecoveryEligibleCampaignOccurrenceSpecV1] = []
    for index, request in enumerate(occurrence_requests, start=1):
        if type(request) is not tuple or len(request) != 2:
            _fail("campaign occurrence request must be (content_id, ordinal)")
        specs.append(
            RecoveryEligibleCampaignOccurrenceSpecV1(
                _SPEC_ISSUER, index, request[0], request[1], blob_ids
            )
        )
    workload = RecoveryEligibleCampaignWorkloadV1(
        _WORKLOAD_ISSUER,
        runtime_preparation.preparation_id,
        runtime_preparation.manifest.runtime_tree_id,
        runtime_preparation.source_closure.closure_id,
        blob_ids,
        tuple(specs),
    )
    return RecoveryEligibleCampaignPreregistrationV1(
        _PREREGISTRATION_ISSUER,
        runtime_preparation,
        blobs,
        workload,
    )


def verify_recovery_eligible_campaign_preregistration_v1(
    registration: RecoveryEligibleCampaignPreregistrationV1,
) -> RecoveryEligibleCampaignPreregistrationV1:
    if type(registration) is not RecoveryEligibleCampaignPreregistrationV1:
        _fail("campaign preregistration verifier received a foreign object")
    registration.__post_init__(_PREREGISTRATION_ISSUER)
    return registration


def _write_committed(path: Path, raw: bytes) -> None:
    if path.exists() or path.parent.is_symlink() or not path.parent.is_dir():
        _fail("campaign commit target must be absent under one real directory")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        offset = 0
        while offset < len(raw):
            count = os.write(descriptor, raw[offset:])
            if count <= 0:
                _fail("campaign commit write made no progress")
            offset += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _commit_event(
    *,
    root: Path,
    sequence: int,
    event_kind: str,
    previous_event_id: str | None,
    subject_id: str,
    subject_filename: str,
    subject_raw: bytes,
    occurrence_index: int | None,
    logical_occurrence_id: str | None,
) -> RecoveryEligibleCampaignCommitEventV1:
    event = RecoveryEligibleCampaignCommitEventV1(
        sequence,
        event_kind,
        previous_event_id,
        subject_id,
        subject_filename,
        len(subject_raw),
        hashlib.sha256(subject_raw).hexdigest(),
        occurrence_index,
        logical_occurrence_id,
    )
    event_name = f"{sequence:04d}_{event_kind}.json"
    _write_committed(root / event_name, canonical_json_bytes(event.to_document()))
    return event


def _occurrence_row(
    spec: RecoveryEligibleCampaignOccurrenceSpecV1,
    bundle: occurrence_v1.RecoveryEligibleOccurrenceAccountingBundleV1,
) -> RecoveryEligibleCampaignOccurrenceRowV1:
    verified = occurrence_v1.verify_recovery_eligible_occurrence_accounting_v1(bundle)
    science = verified.supervised_execution.science_summary
    if (
        science["occurrence_id"] != spec.logical_occurrence_id
        or science["terminal_class"] != "PLAN_CERTIFICATE"
        or science["terminal_code"] != "FULL_GROUND_FALLBACK"
        or science["proof_node_reuse_count"] != 41
        or science["requested_frontier_row_count"] != 6
        or science["local_ground_draw_count"] != 12_672
    ):
        _fail("campaign occurrence scientific terminal changed")
    return RecoveryEligibleCampaignOccurrenceRowV1(
        spec.occurrence_spec_id,
        spec.occurrence_index,
        spec.logical_occurrence_id,
        spec.query_ordinal,
        verified.bundle_id,
        verified.output_commit.output_commit_id,
        science["persistent_proof_cache_id"],
        science["recovery_eligible_checkpoint_id"],
        verified.occurrence_comparison_values,
    )


def run_recovery_eligible_preregistered_campaign_v1(
    *,
    repository_root: str | Path,
    runtime_cas_root: str | Path,
    campaign_directory: str | Path,
    binding_bytes: bytes,
    snapshot_bytes: bytes,
    transition_bytes: bytes,
    occurrence_requests: Sequence[tuple[str, int]],
    timeout_seconds: int = executor_v1.DEFAULT_TIMEOUT_SECONDS,
) -> RecoveryEligiblePreregisteredCampaignResultV1:
    root = Path(campaign_directory)
    if root.exists() or root.parent.is_symlink() or not root.parent.is_dir():
        _fail("campaign output directory must be absent under one real parent")
    preparation = executor_v1.prepare_recovery_eligible_accounted_runtime_v1(
        repository_root=repository_root,
        runtime_cas_root=runtime_cas_root,
    )
    registration = preregister_recovery_eligible_campaign_v1(
        runtime_preparation=preparation,
        binding_bytes=binding_bytes,
        snapshot_bytes=snapshot_bytes,
        transition_bytes=transition_bytes,
        occurrence_requests=occurrence_requests,
    )
    root.mkdir(mode=0o700)
    prereg_name = "CAMPAIGN_PREREGISTRATION.json"
    prereg_raw = canonical_json_bytes(registration.to_document())
    _write_committed(root / prereg_name, prereg_raw)
    prereg_event = _commit_event(
        root=root,
        sequence=0,
        event_kind="PREREGISTRATION_COMMITTED",
        previous_event_id=None,
        subject_id=registration.preregistration_id,
        subject_filename=prereg_name,
        subject_raw=prereg_raw,
        occurrence_index=None,
        logical_occurrence_id=None,
    )

    blobs = {row.role: row.canonical_bytes for row in registration.input_blobs}
    bundles: list[occurrence_v1.RecoveryEligibleOccurrenceAccountingBundleV1] = []
    rows: list[RecoveryEligibleCampaignOccurrenceRowV1] = []
    events: list[RecoveryEligibleCampaignCommitEventV1] = []
    previous_event_id = prereg_event.event_id
    for spec in registration.workload.occurrences:
        occurrence_directory = root / f"occurrence-{spec.occurrence_index:04d}"
        occurrence_directory.mkdir(mode=0o700)
        pending_trace = occurrence_directory / ".OPERATIONAL_TRACE.pending"
        execution = executor_v1.execute_recovery_eligible_accounted_v1(
            preparation,
            binding_bytes=blobs["SOURCE_BUNDLE_BINDING"],
            snapshot_bytes=blobs["REUSABLE_RAPM_SNAPSHOT"],
            transition_bytes=blobs["PROOF_DEPENDENCY_TRANSITION"],
            logical_occurrence_id=spec.logical_occurrence_id,
            query_ordinal=spec.query_ordinal,
            trace_output_path=pending_trace,
            timeout_seconds=timeout_seconds,
        )
        bundle = occurrence_v1.finalize_recovery_eligible_occurrence_accounting_v1(
            supervised_execution=execution,
            output_directory=occurrence_directory,
            pending_trace_path=pending_trace,
        )
        row = _occurrence_row(spec, bundle)
        row_name = f"OCCURRENCE_{spec.occurrence_index:04d}_ROW.json"
        row_raw = canonical_json_bytes(row.to_document())
        _write_committed(root / row_name, row_raw)
        event = _commit_event(
            root=root,
            sequence=spec.occurrence_index,
            event_kind="OCCURRENCE_BUNDLE_COMMITTED",
            previous_event_id=previous_event_id,
            subject_id=row.row_id,
            subject_filename=row_name,
            subject_raw=row_raw,
            occurrence_index=spec.occurrence_index,
            logical_occurrence_id=spec.logical_occurrence_id,
        )
        bundles.append(bundle)
        rows.append(row)
        events.append(event)
        previous_event_id = event.event_id

    if len({row.persistent_proof_cache_id for row in rows}) != 1 or len(
        {row.recovery_eligible_checkpoint_id for row in rows}
    ) != 1:
        _fail("campaign occurrences did not reuse one proof cache/checkpoint")
    closure = RecoveryEligibleCampaignClosureV1(
        registration.preregistration_id,
        registration.workload.workload_id,
        preparation.preparation_id,
        tuple(rows),
        (prereg_event.event_id, *(row.event_id for row in events)),
        _prefix_vectors(rows),
    )
    closure_raw = canonical_json_bytes(closure.to_document())
    _write_committed(root / "CAMPAIGN_CLOSURE.json", closure_raw)
    result = RecoveryEligiblePreregisteredCampaignResultV1(
        _RESULT_ISSUER,
        root.resolve(strict=True),
        registration,
        prereg_event,
        tuple(bundles),
        tuple(rows),
        tuple(events),
        closure,
    )
    return verify_recovery_eligible_preregistered_campaign_v1(result)


def _verify_committed_file(path: Path, expected_raw: bytes) -> None:
    info = path.stat()
    if (
        path.is_symlink()
        or not path.is_file()
        or stat.S_IMODE(info.st_mode) & 0o177
        or path.read_bytes() != expected_raw
    ):
        _fail("campaign committed file changed")


def _require_registered_result_cardinality_v1(result: Any, count: int) -> None:
    if (
        type(count) is not int
        or count < MIN_OCCURRENCE_COUNT
        or len(result.occurrence_bundles) != count
        or len(result.occurrence_rows) != count
        or len(result.occurrence_events) != count
        or len(result.closure.occurrence_rows) != count
    ):
        _fail("campaign result deleted or added a registered occurrence")


def verify_recovery_eligible_preregistered_campaign_v1(
    result: RecoveryEligiblePreregisteredCampaignResultV1,
) -> RecoveryEligiblePreregisteredCampaignResultV1:
    if type(result) is not RecoveryEligiblePreregisteredCampaignResultV1:
        _fail("campaign verifier received a foreign result")
    registration = verify_recovery_eligible_campaign_preregistration_v1(result.preregistration)
    root = result.campaign_directory.resolve(strict=True)
    if root.is_symlink() or not root.is_dir() or stat.S_IMODE(root.stat().st_mode) & 0o077:
        _fail("campaign output directory identity changed")
    _verify_committed_file(
        root / "CAMPAIGN_PREREGISTRATION.json",
        canonical_json_bytes(registration.to_document()),
    )
    _verify_committed_file(
        root / "0000_PREREGISTRATION_COMMITTED.json",
        canonical_json_bytes(result.preregistration_event.to_document()),
    )
    registered_count = len(registration.workload.occurrences)
    _require_registered_result_cardinality_v1(result, registered_count)
    previous = result.preregistration_event.event_id
    cache_ids: set[str] = set()
    checkpoint_ids: set[str] = set()
    for spec, bundle, row, event in zip(
        registration.workload.occurrences,
        result.occurrence_bundles,
        result.occurrence_rows,
        result.occurrence_events,
        strict=True,
    ):
        verified_bundle = occurrence_v1.verify_recovery_eligible_occurrence_accounting_v1(bundle)
        expected_row = _occurrence_row(spec, verified_bundle)
        if row != expected_row or event.previous_event_id != previous:
            _fail("campaign occurrence row or hash chain changed")
        occurrence_directory = root / f"occurrence-{spec.occurrence_index:04d}"
        expected_names = tuple(
            f"{role}.json" for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        )
        if tuple(sorted(path.name for path in occurrence_directory.iterdir())) != tuple(sorted(expected_names)):
            _fail("campaign occurrence output inventory changed")
        for commit in verified_bundle.output_commit.role_commits:
            target = occurrence_directory / commit.filename
            raw = target.read_bytes()
            if len(raw) != commit.byte_count or hashlib.sha256(raw).hexdigest() != commit.bytes_sha256:
                _fail("campaign occurrence output bytes changed")
        row_name = f"OCCURRENCE_{spec.occurrence_index:04d}_ROW.json"
        row_raw = canonical_json_bytes(row.to_document())
        _verify_committed_file(root / row_name, row_raw)
        event_name = f"{spec.occurrence_index:04d}_OCCURRENCE_BUNDLE_COMMITTED.json"
        _verify_committed_file(root / event_name, canonical_json_bytes(event.to_document()))
        if (
            event.sequence != spec.occurrence_index
            or event.subject_id != row.row_id
            or event.subject_filename != row_name
            or event.subject_byte_count != len(row_raw)
            or event.subject_sha256 != hashlib.sha256(row_raw).hexdigest()
            or event.logical_occurrence_id != spec.logical_occurrence_id
        ):
            _fail("campaign occurrence commit evidence changed")
        cache_ids.add(row.persistent_proof_cache_id)
        checkpoint_ids.add(row.recovery_eligible_checkpoint_id)
        previous = event.event_id
    if len(cache_ids) != 1 or len(checkpoint_ids) != 1:
        _fail("campaign proof cache/checkpoint reuse changed")
    expected_closure = RecoveryEligibleCampaignClosureV1(
        registration.preregistration_id,
        registration.workload.workload_id,
        registration.runtime_preparation.preparation_id,
        result.occurrence_rows,
        (result.preregistration_event.event_id, *(row.event_id for row in result.occurrence_events)),
        _prefix_vectors(result.occurrence_rows),
    )
    if result.closure != expected_closure:
        _fail("campaign denominator closure changed")
    _verify_committed_file(
        root / "CAMPAIGN_CLOSURE.json",
        canonical_json_bytes(result.closure.to_document()),
    )
    expected_root_files = {
        "CAMPAIGN_PREREGISTRATION.json",
        "0000_PREREGISTRATION_COMMITTED.json",
        "CAMPAIGN_CLOSURE.json",
        *(f"OCCURRENCE_{row.occurrence_index:04d}_ROW.json" for row in result.occurrence_rows),
        *(f"{row.sequence:04d}_OCCURRENCE_BUNDLE_COMMITTED.json" for row in result.occurrence_events),
    }
    actual_root_files = {path.name for path in root.iterdir() if path.is_file()}
    actual_directories = {path.name for path in root.iterdir() if path.is_dir()}
    if actual_root_files != expected_root_files or actual_directories != {
        f"occurrence-{row.occurrence_index:04d}" for row in result.occurrence_rows
    }:
        _fail("campaign durable output inventory changed")
    if content_id(RESULT_DOMAIN, result._payload()) != result._result_id:
        _fail("campaign result identity changed")
    return result


__all__ = (
    "ConstructionK7RecoveryEligiblePreregisteredCampaignV1Error",
    "LOCAL_DOMAINS",
    "MAX_OCCURRENCE_COUNT",
    "MIN_OCCURRENCE_COUNT",
    "RecoveryEligibleCampaignClosureV1",
    "RecoveryEligibleCampaignCommitEventV1",
    "RecoveryEligibleCampaignInputBlobV1",
    "RecoveryEligibleCampaignOccurrenceRowV1",
    "RecoveryEligibleCampaignOccurrenceSpecV1",
    "RecoveryEligibleCampaignPreregistrationV1",
    "RecoveryEligibleCampaignWorkloadV1",
    "RecoveryEligiblePreregisteredCampaignResultV1",
    "preregister_recovery_eligible_campaign_v1",
    "run_recovery_eligible_preregistered_campaign_v1",
    "verify_recovery_eligible_campaign_preregistration_v1",
    "verify_recovery_eligible_preregistered_campaign_v1",
)
