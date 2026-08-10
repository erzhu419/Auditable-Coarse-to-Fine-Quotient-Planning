"""Exact query-owner accounting authority for one retained abstract PASS.

The retained model-only execution already contains an ordered native event
trace.  Contract 2.0.43 intentionally kept its two positive abstract owner
streams as legacy candidates because it had not bound the complete trace
window, the V6 stage, and the operational cutoff.  This additive authority
closes exactly those two blockers and nothing else.

It issues two genuine V6 :class:`~acfqp.accounting_v1.CounterRecordV1`
objects:

* ``common.abstract_audit_obligations``; and
* ``common.abstract_bellman_backups``.

No WorkVector, ComparisonVector, terminal, certificate, campaign closure, or
official Gate is issued here.  The remaining 174 ABSTRACT_CERTIFIED paths
stay open.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage_v1
from acfqp import construction_k7_abstract_certified_native_zero_closure_v1 as zero_v1
from acfqp import construction_k7_abstract_pass_production_native_accounting_v1 as retained_v1
from acfqp import construction_k7_all_path_accounting_profile_v1 as all_path_v1
from acfqp.accounting_v1 import CounterRecordV1
from acfqp.phase3e_abstract_pass_closure_v1 import (
    verify_model_only_operational_execution_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_ENVELOPE_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_RESOLUTION_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_WINDOW_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.phase3e_model_only_executor_v1 import ModelOnlyQueryExecutionV1
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.64"
PROFILE_KEY = "construction_k7_abstract_certified_query_owner_authority_v1"

EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_PRIOR_COMPLETION_COUNT = 26
EXPECTED_NEW_FORMAL_RECORD_COUNT = 2
EXPECTED_COMBINED_COMPLETION_COUNT = 28
EXPECTED_REMAINING_PATH_COUNT = 174

EXPECTED_TOTAL_EVENT_COUNT = 98
EXPECTED_PREFIX_END_SEQUENCE = 4
EXPECTED_OWNER_START_SEQUENCE = 5
EXPECTED_OWNER_END_SEQUENCE = 95
EXPECTED_SUFFIX_START_SEQUENCE = 96

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

WINDOW_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_WINDOW_V1_DOMAIN
RESOLUTION_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_RESOLUTION_V1_DOMAIN
)
ENVELOPE_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_ENVELOPE_V1_DOMAIN
REPLAY_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_REPLAY_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {WINDOW_DOMAIN, RESOLUTION_DOMAIN, ENVELOPE_DOMAIN, REPLAY_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-owner authority domains are not central and unique")

OWNER_PATHS = (
    "common.abstract_audit_obligations",
    "common.abstract_bellman_backups",
)
EXPECTED_OWNER_VALUES = {
    "common.abstract_audit_obligations": 70,
    "common.abstract_bellman_backups": 25,
}
EXPECTED_OWNER_EVENT_COUNTS = {
    "common.abstract_audit_obligations": 66,
    "common.abstract_bellman_backups": 25,
}
OWNER_STAGE = registry_v6.ConstructionStageKindV6.FAILED_ABSTRACT_PREFIX
OWNER_STAGE_DISPOSITION = all_path_v1.StageDispositionV1.OPTIONAL_REPEATABLE

_WINDOW_ISSUER = object()
_RESOLUTION_ISSUER = object()
_ENVELOPE_ISSUER = object()


class ConstructionK7AbstractCertifiedQueryOwnerAuthorityV1Error(ValueError):
    """The retained PASS or one exact query-owner binding changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractCertifiedQueryOwnerAuthorityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractCertifiedQueryOwnerAuthorityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _same_document(left: Any, right: Any, label: str) -> None:
    try:
        same = canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractCertifiedQueryOwnerAuthorityV1Error(
            f"{label} is not canonical"
        ) from error
    if not same:
        _fail(f"{label} crossed its exact retained root")


class QueryOwnerReplayOutcomeV1(str, Enum):
    VERIFIED = "EXACT_QUERY_OWNER_COUNTER_RECORDS_VERIFIED"
    DOCUMENT_BLOCKED = "QUERY_OWNER_AUTHORITY_DOCUMENT_BLOCKED"


@dataclass(frozen=True, slots=True)
class AbstractCertifiedQueryOwnerWindowV1:
    """Complete trace window and the exact contiguous owner subwindow."""

    _issuer: InitVar[object]
    retained_v1_inventory_id: str
    inventory_context_id: str
    coverage_report_id: str
    zero_value_closure_id: str
    source_archive_id: str
    all_path_accounting_profile_id: str
    operation_boundary_manifest_id: str
    operational_execution_id: str
    event_trace_id: str
    event_trace_sha256: str
    v6_counter_registry_id: str
    v6_stage_profile_id: str
    stage_kind: registry_v6.ConstructionStageKindV6
    ordered_event_rows: tuple[tuple[int, str, int], ...]
    prefix_end_sequence: int
    owner_start_sequence: int
    owner_end_sequence: int
    suffix_start_sequence: int
    _window_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _WINDOW_ISSUER:
            _fail("query-owner window is caller-minted")
        for value, label in (
            (self.retained_v1_inventory_id, "retained-V1 inventory"),
            (self.inventory_context_id, "retained-V1 inventory context"),
            (self.coverage_report_id, "coverage report"),
            (self.zero_value_closure_id, "zero-value closure"),
            (self.source_archive_id, "source archive"),
            (self.all_path_accounting_profile_id, "all-path accounting profile"),
            (self.operation_boundary_manifest_id, "operation boundary manifest"),
            (self.operational_execution_id, "operational execution"),
            (self.event_trace_id, "native event trace"),
            (self.event_trace_sha256, "native event trace digest"),
            (self.v6_counter_registry_id, "V6 counter registry"),
            (self.v6_stage_profile_id, "V6 stage profile"),
        ):
            _cid(value, label)
        try:
            stage = registry_v6.ConstructionStageKindV6(self.stage_kind)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedQueryOwnerAuthorityV1Error(
                "query-owner stage is invalid"
            ) from error
        object.__setattr__(self, "stage_kind", stage)
        rows = tuple(self.ordered_event_rows)
        object.__setattr__(self, "ordered_event_rows", rows)
        sequences = tuple(row[0] for row in rows)
        owner_rows = tuple(row for row in rows if row[1] in OWNER_PATHS)
        owner_sequences = tuple(row[0] for row in owner_rows)
        if (
            stage is not OWNER_STAGE
            or len(rows) != EXPECTED_TOTAL_EVENT_COUNT
            or sequences != tuple(range(1, EXPECTED_TOTAL_EVENT_COUNT + 1))
            or any(
                type(sequence) is not int
                or type(path) is not str
                or type(amount) is not int
                or amount <= 0
                for sequence, path, amount in rows
            )
            or self.prefix_end_sequence != EXPECTED_PREFIX_END_SEQUENCE
            or self.owner_start_sequence != EXPECTED_OWNER_START_SEQUENCE
            or self.owner_end_sequence != EXPECTED_OWNER_END_SEQUENCE
            or self.suffix_start_sequence != EXPECTED_SUFFIX_START_SEQUENCE
            or not owner_sequences
            or owner_sequences[0] != self.owner_start_sequence
            or owner_sequences[-1] != self.owner_end_sequence
            or owner_sequences
            != tuple(range(self.owner_start_sequence, self.owner_end_sequence + 1))
            or any(
                path in OWNER_PATHS
                for _sequence, path, _amount in rows[: self.prefix_end_sequence]
            )
            or any(
                path in OWNER_PATHS
                for _sequence, path, _amount in rows[self.suffix_start_sequence - 1 :]
            )
            or any(
                path not in OWNER_PATHS
                for _sequence, path, _amount in rows[
                    self.owner_start_sequence - 1 : self.owner_end_sequence
                ]
            )
            or {
                path: sum(amount for _sequence, row_path, amount in rows if row_path == path)
                for path in OWNER_PATHS
            }
            != EXPECTED_OWNER_VALUES
            or {
                path: sum(1 for _sequence, row_path, _amount in rows if row_path == path)
                for path in OWNER_PATHS
            }
            != EXPECTED_OWNER_EVENT_COUNTS
        ):
            _fail("query-owner event window or cutoff changed")
        object.__setattr__(self, "_window_id", content_id(WINDOW_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_query_owner_window.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "retained_v1_inventory_id": self.retained_v1_inventory_id,
            "inventory_context_id": self.inventory_context_id,
            "coverage_report_id": self.coverage_report_id,
            "zero_value_closure_id": self.zero_value_closure_id,
            "source_archive_id": self.source_archive_id,
            "all_path_accounting_profile_id": self.all_path_accounting_profile_id,
            "operation_boundary_manifest_id": self.operation_boundary_manifest_id,
            "operational_execution_id": self.operational_execution_id,
            "event_trace_id": self.event_trace_id,
            "event_trace_sha256": self.event_trace_sha256,
            "v6_counter_registry_id": self.v6_counter_registry_id,
            "v6_stage_profile_id": self.v6_stage_profile_id,
            "stage_kind": self.stage_kind.value,
            "ordered_event_rows": [
                {"sequence": sequence, "path": path, "amount": amount}
                for sequence, path, amount in self.ordered_event_rows
            ],
            "measurement_window_start_sequence": 1,
            "operational_cutoff_sequence": EXPECTED_TOTAL_EVENT_COUNT,
            "prefix_end_sequence": self.prefix_end_sequence,
            "owner_start_sequence": self.owner_start_sequence,
            "owner_end_sequence": self.owner_end_sequence,
            "suffix_start_sequence": self.suffix_start_sequence,
            "owner_paths": list(OWNER_PATHS),
            "total_event_count": EXPECTED_TOTAL_EVENT_COUNT,
            "owner_event_count": (
                EXPECTED_OWNER_END_SEQUENCE - EXPECTED_OWNER_START_SEQUENCE + 1
            ),
            "prefix_contains_owner_event": False,
            "owner_window_contains_nonowner_event": False,
            "suffix_contains_owner_event": False,
            "complete_trace_window_bound": True,
            "stage_assignment_bound": True,
            "operational_cutoff_bound": True,
            "ground_access_performed": False,
        }

    @property
    def window_id(self) -> str:
        current = content_id(WINDOW_DOMAIN, self._payload())
        if current != self._window_id:
            _fail("query-owner window changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_owner_window_id": self.window_id}


@dataclass(frozen=True, slots=True, order=True)
class AbstractCertifiedQueryOwnerResolutionV1:
    """One legacy blocker replaced by an exact V6 owner binding."""

    _issuer: InitVar[object]
    path: str
    window_id: str
    inventory_context_id: str
    predecessor_blocker_id: str
    legacy_candidate_id: str
    legacy_v1_record_id: str
    semantics_id: str
    owner: str
    unit: str
    lane: str
    scope: str
    reducer: str
    stage_kind: registry_v6.ConstructionStageKindV6
    stage_disposition: all_path_v1.StageDispositionV1
    ordered_event_rows: tuple[tuple[int, int], ...]
    value: int
    _resolution_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESOLUTION_ISSUER:
            _fail("query-owner resolution is caller-minted")
        for value, label in (
            (self.window_id, "query-owner window"),
            (self.inventory_context_id, "retained-V1 inventory context"),
            (self.predecessor_blocker_id, "predecessor formal blocker"),
            (self.legacy_candidate_id, "legacy owner candidate"),
            (self.legacy_v1_record_id, "legacy V1 record"),
        ):
            _cid(value, label)
        try:
            stage = registry_v6.ConstructionStageKindV6(self.stage_kind)
            disposition = all_path_v1.StageDispositionV1(self.stage_disposition)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedQueryOwnerAuthorityV1Error(
                "query-owner resolution stage metadata is invalid"
            ) from error
        object.__setattr__(self, "stage_kind", stage)
        object.__setattr__(self, "stage_disposition", disposition)
        registry = registry_v6.official_counter_registry_v6()
        leaf = registry.by_path.get(self.path)
        rows = tuple(self.ordered_event_rows)
        object.__setattr__(self, "ordered_event_rows", rows)
        if (
            self.path not in OWNER_PATHS
            or leaf is None
            or (
                self.semantics_id,
                self.owner,
                self.unit,
                self.lane,
                self.scope,
                self.reducer,
            )
            != (
                leaf.semantics_id,
                leaf.owner,
                leaf.unit,
                leaf.lane.value,
                leaf.scope,
                leaf.reducer.value,
            )
            or stage is not OWNER_STAGE
            or disposition is not OWNER_STAGE_DISPOSITION
            or type(self.value) is not int
            or self.value != EXPECTED_OWNER_VALUES[self.path]
            or len(rows) != EXPECTED_OWNER_EVENT_COUNTS[self.path]
            or any(
                type(sequence) is not int
                or sequence < EXPECTED_OWNER_START_SEQUENCE
                or sequence > EXPECTED_OWNER_END_SEQUENCE
                or type(amount) is not int
                or amount <= 0
                for sequence, amount in rows
            )
            or tuple(sequence for sequence, _amount in rows)
            != tuple(sorted(sequence for sequence, _amount in rows))
            or len({sequence for sequence, _amount in rows}) != len(rows)
            or sum(amount for _sequence, amount in rows) != self.value
        ):
            _fail("query-owner resolution differs from exact V6 owner metadata")
        object.__setattr__(
            self,
            "_resolution_id",
            content_id(RESOLUTION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_query_owner_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "path": self.path,
            "window_id": self.window_id,
            "inventory_context_id": self.inventory_context_id,
            "predecessor_blocker_id": self.predecessor_blocker_id,
            "predecessor_blocker_code": (
                retained_v1.FormalBlockerCodeV1
                .LEGACY_OWNER_EVENT_LACKS_HOOK_STAGE_CUTOFF_REPLAY.value
            ),
            "legacy_candidate_id": self.legacy_candidate_id,
            "legacy_v1_record_id": self.legacy_v1_record_id,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "unit": self.unit,
            "lane": self.lane,
            "scope": self.scope,
            "reducer": self.reducer,
            "stage_kind": self.stage_kind.value,
            "stage_disposition": self.stage_disposition.value,
            "ordered_owner_events": [
                {"sequence": sequence, "amount": amount}
                for sequence, amount in self.ordered_event_rows
            ],
            "value": self.value,
            "complete_trace_window_replayed": True,
            "production_hook_semantics_replayed": True,
            "production_stage_assignment_replayed": True,
            "production_occurrence_cutoff_replayed": True,
            "source_v1_record_relabelled_as_v6": False,
            "formal_v6_counter_record_authorized": True,
            "ground_access_performed": False,
        }

    @property
    def resolution_id(self) -> str:
        current = content_id(RESOLUTION_DOMAIN, self._payload())
        if current != self._resolution_id:
            _fail("query-owner resolution changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_owner_resolution_id": self.resolution_id}


@dataclass(frozen=True, slots=True)
class AbstractCertifiedQueryOwnerEnvelopeV1:
    """Exactly two formal records; never a partial WorkVector."""

    _issuer: InitVar[object]
    window: AbstractCertifiedQueryOwnerWindowV1
    resolutions: tuple[AbstractCertifiedQueryOwnerResolutionV1, ...]
    counter_records: tuple[CounterRecordV1, ...]
    _envelope_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ENVELOPE_ISSUER
            or type(self.window) is not AbstractCertifiedQueryOwnerWindowV1
            or any(
                type(row) is not AbstractCertifiedQueryOwnerResolutionV1
                for row in self.resolutions
            )
            or any(type(row) is not CounterRecordV1 for row in self.counter_records)
        ):
            _fail("query-owner envelope is caller-minted")
        resolutions = tuple(self.resolutions)
        records = tuple(self.counter_records)
        object.__setattr__(self, "resolutions", resolutions)
        object.__setattr__(self, "counter_records", records)
        registry = registry_v6.official_counter_registry_v6()
        if (
            len(resolutions) != EXPECTED_NEW_FORMAL_RECORD_COUNT
            or tuple(row.path for row in resolutions) != OWNER_PATHS
            or len(records) != EXPECTED_NEW_FORMAL_RECORD_COUNT
            or tuple(row.path for row in records) != OWNER_PATHS
            or any(row.window_id != self.window.window_id for row in resolutions)
        ):
            _fail("query-owner envelope must contain exactly the two owner paths")
        by_resolution = {row.path: row for row in resolutions}
        for record in records:
            resolution = by_resolution[record.path]
            record.verify_against(registry.by_path[record.path])
            if (
                record.counter_registry_id != registry.registry_id
                or record.value != resolution.value
                or record.observed is not True
                or record.recorder_id != resolution.resolution_id
                or CounterRecordV1.from_dict(record.to_dict()) != record
            ):
                _fail("formal query-owner record is not bound to its resolution")
        object.__setattr__(
            self, "_envelope_id", content_id(ENVELOPE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_query_owner_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_code_assessed": TerminalCode.ABSTRACT_CERTIFIED.value,
            "window": self.window.to_document(),
            "resolutions": [row.to_document() for row in self.resolutions],
            "formal_v6_counter_records": [
                row.to_dict() for row in self.counter_records
            ],
            "required_path_count": EXPECTED_REQUIRED_PATH_COUNT,
            "retained_prior_completion_progress_count": (
                EXPECTED_PRIOR_COMPLETION_COUNT
            ),
            "new_formal_v6_counter_record_count": EXPECTED_NEW_FORMAL_RECORD_COUNT,
            "combined_completion_progress_count": EXPECTED_COMBINED_COMPLETION_COUNT,
            "remaining_required_path_authority_count": EXPECTED_REMAINING_PATH_COUNT,
            "predecessor_owner_blocker_count_resolved": EXPECTED_NEW_FORMAL_RECORD_COUNT,
            "predecessor_owner_blocker_count_remaining": 0,
            "all_nine_shared_resource_receipts_complete": False,
            "all_eight_derived_reconciliations_complete": False,
            "complete_202_counter_record_chain_present": False,
            "formal_v6_work_vector_id": None,
            "formal_v6_comparison_vector_id": None,
            "terminal_artifact_id": None,
            "campaign_occurrence_closure_id": None,
            "certificate_issued": False,
            "ground_access_performed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_n_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        }

    @property
    def envelope_id(self) -> str:
        current = content_id(ENVELOPE_DOMAIN, self._payload())
        if current != self._envelope_id:
            _fail("query-owner envelope changed after issuance")
        return current

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_owner_envelope_id": self.envelope_id}


@dataclass(frozen=True, slots=True)
class AbstractCertifiedQueryOwnerReplayV1:
    outcome: QueryOwnerReplayOutcomeV1
    envelope: AbstractCertifiedQueryOwnerEnvelopeV1 | None
    blocker_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            outcome = QueryOwnerReplayOutcomeV1(self.outcome)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedQueryOwnerAuthorityV1Error(
                "query-owner replay outcome is invalid"
            ) from error
        object.__setattr__(self, "outcome", outcome)
        if outcome is QueryOwnerReplayOutcomeV1.VERIFIED:
            if (
                type(self.envelope) is not AbstractCertifiedQueryOwnerEnvelopeV1
                or self.blocker_codes
            ):
                _fail("verified query-owner replay is inconsistent")
        elif self.envelope is not None or not self.blocker_codes:
            _fail("blocked query-owner replay lacks one typed reason")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_query_owner_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "outcome": self.outcome.value,
            "query_owner_envelope_id": (
                self.envelope.envelope_id if self.envelope is not None else None
            ),
            "blocker_codes": list(self.blocker_codes),
            "exact_root_replay_performed": True,
            "planner_reexecution_performed": False,
            "ground_access_performed": False,
            "formal_v6_work_vector_issued": False,
            "formal_v6_comparison_vector_issued": False,
            "terminal_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def replay_id(self) -> str:
        return content_id(REPLAY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_owner_replay_id": self.replay_id}


def _exact_roots(
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
) -> tuple[
    ModelOnlyQueryExecutionV1,
    coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
]:
    if (
        type(coverage_report)
        is not coverage_v1.AbstractCertifiedAccountingCoverageReportV1
        or type(zero_closure) is not zero_v1.AbstractCertifiedZeroValueClosureV1
        or type(retained_inventory)
        is not retained_v1.AbstractPassRetainedV1EvidenceInventoryV1
    ):
        _fail("query-owner authority requires exact retained root types")
    retained = verify_model_only_operational_execution_v1(execution)
    report = coverage_v1.audit_abstract_certified_accounting_coverage_v1(retained)
    _same_document(report.to_document(), coverage_report.to_document(), "coverage report")
    zeros = zero_v1.close_abstract_certified_zero_value_subset_v1(retained, report)
    _same_document(zeros.to_document(), zero_closure.to_document(), "zero-value closure")
    inventory = retained_v1.inventory_abstract_pass_retained_v1_accounting_v1(
        retained, report, zeros
    )
    _same_document(
        inventory.to_document(), retained_inventory.to_document(), "retained-V1 inventory"
    )
    return retained, report, zeros, inventory


def _build_from_exact_roots(
    execution: ModelOnlyQueryExecutionV1,
    report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zeros: zero_v1.AbstractCertifiedZeroValueClosureV1,
    inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
) -> AbstractCertifiedQueryOwnerEnvelopeV1:
    registry = registry_v6.official_counter_registry_v6()
    registry.validate_official_catalogue()
    stages = registry_v6.official_stage_profile_v6(registry)
    stages.validate(registry)
    all_path = all_path_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    rule = all_path.terminal_path_rule_by_code[TerminalCode.ABSTRACT_CERTIFIED]
    stage_disposition = {
        row.stage_kind: row.disposition for row in rule.stage_plan
    }.get(OWNER_STAGE)
    allowed = stages.by_stage[OWNER_STAGE].allowed_nonzero_paths

    context = inventory.context
    trace = execution.native_event_trace
    trace_rows = tuple(
        (row.sequence, row.path, row.amount) for row in trace.events
    )
    trace_digest = hashlib.sha256(
        canonical_json_bytes(trace.to_dict())
    ).hexdigest()
    if (
        context.coverage_report_id != report.report_id
        or context.zero_value_closure_id != zeros.closure_id
        or context.operational_execution_id != execution.operational_execution_id
        or context.event_trace_id != trace.event_trace_id
        or context.v6_counter_registry_id != registry.registry_id
        or context.v6_stage_profile_id != stages.stage_profile_id
        or context.all_path_accounting_profile_id != all_path.profile_id
        or context.operation_boundary_manifest_id
        != report.operation_boundary_manifest_id
        or report.v6_counter_registry_id != registry.registry_id
        or report.v6_stage_profile_id != stages.stage_profile_id
        or report.all_path_accounting_profile_id != all_path.profile_id
        or stage_disposition is not OWNER_STAGE_DISPOSITION
        or not set(OWNER_PATHS) <= set(allowed)
    ):
        _fail("query-owner registry, stage, profile, or occurrence roots crossed")

    owner_rows = tuple(row for row in trace_rows if row[1] in OWNER_PATHS)
    if not owner_rows:
        _fail("retained trace lacks query-owner events")
    window = AbstractCertifiedQueryOwnerWindowV1(
        _WINDOW_ISSUER,
        inventory.inventory_id,
        context.context_id,
        report.report_id,
        zeros.closure_id,
        report.source_archive_id,
        all_path.profile_id,
        report.operation_boundary_manifest_id,
        execution.operational_execution_id,
        trace.event_trace_id,
        trace_digest,
        registry.registry_id,
        stages.stage_profile_id,
        OWNER_STAGE,
        trace_rows,
        owner_rows[0][0] - 1,
        owner_rows[0][0],
        owner_rows[-1][0],
        owner_rows[-1][0] + 1,
    )

    candidates = {row.path: row for row in inventory.owner_candidates}
    blockers = {
        row.path: row
        for row in inventory.formal_blockers
        if row.code
        is retained_v1.FormalBlockerCodeV1
        .LEGACY_OWNER_EVENT_LACKS_HOOK_STAGE_CUTOFF_REPLAY
    }
    legacy_records = {
        row.path: row for row in execution.recorded_work.work_vector.records
    }
    coverage_gaps = {row.path: row for row in report.path_gaps}
    residual_gaps = {row.path: row for row in zeros.residual_gaps}
    if (
        tuple(candidates) != OWNER_PATHS
        or set(blockers) != set(OWNER_PATHS)
        or not set(OWNER_PATHS) <= set(coverage_gaps)
        or not set(OWNER_PATHS) <= set(residual_gaps)
    ):
        _fail("query-owner predecessor candidates or blockers changed")

    resolutions: list[AbstractCertifiedQueryOwnerResolutionV1] = []
    records: list[CounterRecordV1] = []
    for path in OWNER_PATHS:
        candidate = candidates[path]
        blocker = blockers[path]
        leaf = registry.by_path[path]
        path_rows = tuple(
            (sequence, amount)
            for sequence, row_path, amount in trace_rows
            if row_path == path
        )
        if (
            blocker.context_id != context.context_id
            or blocker.source_evidence_id != candidate.candidate_id
            or candidate.context_id != context.context_id
            or candidate.legacy_event_trace_id != trace.event_trace_id
            or candidate.legacy_event_trace_sha256 != trace_digest
            or candidate.event_rows != path_rows
            or candidate.candidate_value != EXPECTED_OWNER_VALUES[path]
            or candidate.legacy_v1_record_id != legacy_records[path].record_id
            or coverage_gaps[path].code
            is not coverage_v1.PathGapCodeV1
            .POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE
            or coverage_gaps[path].legacy_v1_record_id != candidate.legacy_v1_record_id
            or coverage_gaps[path].legacy_v1_value != candidate.candidate_value
            or residual_gaps[path].code
            is not zero_v1.ResidualGapCodeV1
            .POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE
        ):
            _fail(f"query-owner predecessor evidence changed for {path}")
        resolution = AbstractCertifiedQueryOwnerResolutionV1(
            _RESOLUTION_ISSUER,
            path,
            window.window_id,
            context.context_id,
            blocker.blocker_id,
            candidate.candidate_id,
            candidate.legacy_v1_record_id,
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane.value,
            leaf.scope,
            leaf.reducer.value,
            OWNER_STAGE,
            OWNER_STAGE_DISPOSITION,
            path_rows,
            candidate.candidate_value,
        )
        resolutions.append(resolution)
        records.append(
            CounterRecordV1.observe(
                registry,
                path,
                candidate.candidate_value,
                recorder_id=resolution.resolution_id,
            )
        )
    return AbstractCertifiedQueryOwnerEnvelopeV1(
        _ENVELOPE_ISSUER,
        window,
        tuple(resolutions),
        tuple(records),
    )


def issue_abstract_certified_query_owner_authority_v1(
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
) -> AbstractCertifiedQueryOwnerEnvelopeV1:
    """Issue exactly two formal V6 owner records from one exact retained PASS."""

    roots = _exact_roots(
        execution, coverage_report, zero_closure, retained_inventory
    )
    return _build_from_exact_roots(*roots)


def verify_abstract_certified_query_owner_authority_bytes_v1(
    raw: bytes,
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
) -> AbstractCertifiedQueryOwnerReplayV1:
    """Rebuild the two records from frozen roots without planning or ground access."""

    try:
        if type(raw) is not bytes:
            _fail("query-owner replay requires canonical bytes")
        claimed = loads_canonical_json(raw)
        if type(claimed) is not dict or canonical_json_bytes(claimed) != raw:
            _fail("query-owner envelope bytes are not canonical")
        roots = _exact_roots(
            execution, coverage_report, zero_closure, retained_inventory
        )
        expected = _build_from_exact_roots(*roots)
        if raw != expected.canonical_bytes:
            _fail("claimed query-owner envelope differs from exact replay")
    except Exception:
        return AbstractCertifiedQueryOwnerReplayV1(
            QueryOwnerReplayOutcomeV1.DOCUMENT_BLOCKED,
            None,
            ("EXACT_QUERY_OWNER_AUTHORITY_REPLAY_FAILED",),
        )
    return AbstractCertifiedQueryOwnerReplayV1(
        QueryOwnerReplayOutcomeV1.VERIFIED,
        expected,
        (),
    )


__all__ = [
    "AbstractCertifiedQueryOwnerEnvelopeV1",
    "AbstractCertifiedQueryOwnerReplayV1",
    "AbstractCertifiedQueryOwnerResolutionV1",
    "AbstractCertifiedQueryOwnerWindowV1",
    "ConstructionK7AbstractCertifiedQueryOwnerAuthorityV1Error",
    "EXPECTED_COMBINED_COMPLETION_COUNT",
    "EXPECTED_NEW_FORMAL_RECORD_COUNT",
    "EXPECTED_PRIOR_COMPLETION_COUNT",
    "EXPECTED_REMAINING_PATH_COUNT",
    "EXPECTED_REQUIRED_PATH_COUNT",
    "EXPECTED_TOTAL_EVENT_COUNT",
    "LOCAL_DOMAINS",
    "OWNER_PATHS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "QueryOwnerReplayOutcomeV1",
    "issue_abstract_certified_query_owner_authority_v1",
    "verify_abstract_certified_query_owner_authority_bytes_v1",
]
