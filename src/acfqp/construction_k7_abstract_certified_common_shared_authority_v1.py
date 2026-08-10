"""Exact common hash/integrity/protocol accounting for an abstract PASS.

The retained model-only runner emits seven runtime common events and, after
the fresh child returns successfully, charges three literal supervisor
aggregates.  This authority binds both halves to the complete executor-owned
PASS, exact source bytes, direct source sites, V6 stages, and the operational
cutoff.  It issues exactly two shared-resource ``CounterRecordV1`` objects for
integrity and protocol obligations.  Selected hash events remain diagnostic:
the retained runner explicitly declares that content-ID hashes are not
globally hooked, so this boundary refuses to issue ``common.hash_invocations``.

It does not authorize I/O or memory values, does not create a partial
WorkVector, and does not unlock either official Gate.
"""

from __future__ import annotations

import ast
from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage_v1
from acfqp import construction_k7_abstract_certified_lifecycle_reconciliation_authority_v1 as lifecycle_v1
from acfqp import construction_k7_abstract_certified_native_zero_closure_v1 as zero_v1
from acfqp import construction_k7_abstract_certified_query_owner_authority_v1 as owner_v1
from acfqp import construction_k7_abstract_pass_production_native_accounting_v1 as retained_v1
from acfqp import construction_k7_all_path_accounting_profile_v1 as all_path_v1
from acfqp.accounting_v1 import CounterRecordV1
from acfqp.phase3e_abstract_pass_closure_v1 import (
    verify_model_only_operational_execution_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_ENVELOPE_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_RESOLUTION_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_WINDOW_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.phase3e_model_only_executor_v1 import (
    ModelOnlyQueryExecutionV1,
    model_only_execution_request_v1,
)
from acfqp.phase3e_model_only_v1 import ModelOnlyOutcome
from acfqp.phase3e_rapm_consumer_v1 import (
    ModelOnlyRAPMSourceV1,
    require_model_only_source_authority_v1,
)
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.67"
PROFILE_KEY = "construction_k7_abstract_certified_common_shared_authority_v1"

EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_PRIOR_COMPLETION_COUNT = 34
EXPECTED_NEW_FORMAL_RECORD_COUNT = 2
EXPECTED_COMBINED_COMPLETION_COUNT = 36
EXPECTED_REMAINING_PATH_COUNT = 166

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

WINDOW_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_WINDOW_V1_DOMAIN
RESOLUTION_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_RESOLUTION_V1_DOMAIN
)
ENVELOPE_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_ENVELOPE_V1_DOMAIN
REPLAY_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_REPLAY_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {WINDOW_DOMAIN, RESOLUTION_DOMAIN, ENVELOPE_DOMAIN, REPLAY_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("abstract common-shared domains are not central and unique")

OBSERVED_COMMON_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
)
COMMON_PATHS = (
    "common.integrity_checks",
    "common.protocol_checks",
)
HASH_PATH = "common.hash_invocations"
HASH_BLOCKER_CODE = "CONTENT_ID_HASH_INVOCATIONS_NOT_GLOBALLY_HOOKED"
PREOPEN_STAGE = registry_v6.ConstructionStageKindV6.PREOPEN_COMMON_PREFIX
CLOSED_STAGE = (
    registry_v6.ConstructionStageKindV6.CLOSED_RECONCILIATION_AND_TERMINALIZATION
)

RUNTIME_MODULE = "acfqp.phase3e_model_only_runtime_v1"
RUNTIME_FILENAME = "phase3e_model_only_runtime_v1.py"
RUNTIME_SYMBOL = "main"
EXECUTOR_MODULE = "acfqp.phase3e_model_only_executor_v1"
EXECUTOR_FILENAME = "phase3e_model_only_executor_v1.py"
EXECUTOR_SYMBOL = "execute_model_only_query_v1"

# Source-order direct calls.  The stage is the time at which the registered
# event is emitted, not a retrospective guess about a nested sub-check.
EXPECTED_RUNTIME_CALLS = (
    ("common.protocol_checks", 1, PREOPEN_STAGE),
    ("common.hash_invocations", 1, PREOPEN_STAGE),
    ("common.hash_invocations", 2, PREOPEN_STAGE),
    ("common.integrity_checks", 5, PREOPEN_STAGE),
    ("common.integrity_checks", 1, CLOSED_STAGE),
    ("common.protocol_checks", 1, CLOSED_STAGE),
    ("common.hash_invocations", 1, CLOSED_STAGE),
)
EXPECTED_SUPERVISOR_CALLS = (
    ("common.integrity_checks", 6, CLOSED_STAGE),
    ("common.protocol_checks", 5, CLOSED_STAGE),
    ("common.hash_invocations", 2, CLOSED_STAGE),
)
EXPECTED_RUNTIME_TRACE_ROWS = (
    (1, "common.protocol_checks", 1),
    (2, "common.hash_invocations", 1),
    (3, "common.hash_invocations", 2),
    (4, "common.integrity_checks", 5),
    (96, "common.integrity_checks", 1),
    (97, "common.protocol_checks", 1),
    (98, "common.hash_invocations", 1),
)


def _stage_totals(path: str) -> tuple[tuple[str, int], ...]:
    rows = (*EXPECTED_RUNTIME_CALLS, *EXPECTED_SUPERVISOR_CALLS)
    totals = {
        stage.value: sum(
            amount
            for row_path, amount, row_stage in rows
            if row_path == path and row_stage is stage
        )
        for stage in (PREOPEN_STAGE, CLOSED_STAGE)
    }
    return tuple((stage.value, totals[stage.value]) for stage in (PREOPEN_STAGE, CLOSED_STAGE))


EXPECTED_STAGE_TOTALS = {path: _stage_totals(path) for path in OBSERVED_COMMON_PATHS}
EXPECTED_VALUES = {
    path: sum(value for _stage, value in EXPECTED_STAGE_TOTALS[path])
    for path in OBSERVED_COMMON_PATHS
}
if EXPECTED_VALUES != {  # pragma: no cover - literal contract lock
    "common.hash_invocations": 6,
    "common.integrity_checks": 12,
    "common.protocol_checks": 7,
}:
    raise RuntimeError("abstract common-shared literal totals changed")

_WINDOW_ISSUER = object()
_RESOLUTION_ISSUER = object()
_ENVELOPE_ISSUER = object()


class ConstructionK7AbstractCertifiedCommonSharedAuthorityV1Error(ValueError):
    """The execution, source sites, stages, or common values changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractCertifiedCommonSharedAuthorityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractCertifiedCommonSharedAuthorityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _same(left: Any, right: Any, label: str) -> None:
    try:
        matched = canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractCertifiedCommonSharedAuthorityV1Error(
            f"{label} is not canonical"
        ) from error
    if not matched:
        _fail(f"{label} crossed its exact root")


def _call_target(call: ast.Call) -> str | None:
    target = call.func
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
        return f"{target.value.id}.{target.attr}"
    return None


def _literal_common_call(call: ast.Call) -> tuple[str, int] | None:
    if not call.args or not isinstance(call.args[0], ast.Constant):
        return None
    path = call.args[0].value
    if path not in OBSERVED_COMMON_PATHS:
        return None
    if len(call.args) == 1:
        amount = 1
    elif len(call.args) == 2 and isinstance(call.args[1], ast.Constant):
        amount = call.args[1].value
    else:
        _fail("common source call lacks one literal amount")
    if type(amount) is not int or amount <= 0:
        _fail("common source call amount is not positive")
    return path, amount


def _direct_source_calls(
    raw: bytes,
    *,
    filename: str,
    symbol: str,
    target: str,
) -> tuple[tuple[str, int], ...]:
    try:
        tree = ast.parse(raw.decode("utf-8", errors="strict"), filename=filename)
    except (UnicodeDecodeError, SyntaxError) as error:
        raise ConstructionK7AbstractCertifiedCommonSharedAuthorityV1Error(
            f"{filename} is not exact UTF-8 Python"
        ) from error
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == symbol
    ]
    if len(functions) != 1:
        _fail(f"{filename} lacks one exact {symbol} function")
    function = functions[0]
    direct: list[tuple[str, int]] = []
    for statement in function.body:
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            continue
        call = statement.value
        if _call_target(call) != target:
            continue
        row = _literal_common_call(call)
        if row is not None:
            direct.append(row)
    nested_with_locations = [
        (call.lineno, call.col_offset, row)
        for call in ast.walk(function)
        if isinstance(call, ast.Call) and _call_target(call) == target
        if (row := _literal_common_call(call)) is not None
    ]
    nested = tuple(
        row for _line, _column, row in sorted(nested_with_locations)
    )
    if tuple(direct) != nested:
        _fail(f"{filename} has a nested or hidden common charge site")
    return tuple(direct)


class CommonSharedReplayOutcomeV1(str, Enum):
    VERIFIED = "EXACT_ABSTRACT_COMMON_SHARED_COUNTER_RECORDS_VERIFIED"
    DOCUMENT_BLOCKED = "ABSTRACT_COMMON_SHARED_DOCUMENT_BLOCKED"


@dataclass(frozen=True, slots=True)
class AbstractCertifiedCommonSharedWindowV1:
    _issuer: InitVar[object]
    source_lease_id: str
    operational_execution_id: str
    coverage_report_id: str
    source_archive_id: str
    lifecycle_envelope_id: str
    event_trace_id: str
    event_trace_sha256: str
    runtime_source_sha256: str
    runtime_source_byte_count: int
    executor_source_sha256: str
    executor_source_byte_count: int
    runtime_trace_rows: tuple[tuple[int, str, int], ...]
    source_site_rows: tuple[tuple[str, str, int, str, int, str], ...]
    _window_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _WINDOW_ISSUER:
            _fail("abstract common-shared window is caller-minted")
        for value, label in (
            (self.source_lease_id, "source lease"),
            (self.operational_execution_id, "operational execution"),
            (self.coverage_report_id, "coverage report"),
            (self.source_archive_id, "source archive"),
            (self.lifecycle_envelope_id, "lifecycle envelope"),
            (self.event_trace_id, "native event trace"),
            (self.event_trace_sha256, "native event trace digest"),
            (self.runtime_source_sha256, "runtime source digest"),
            (self.executor_source_sha256, "executor source digest"),
        ):
            _cid(value, label)
        expected_sites = tuple(
            (
                RUNTIME_MODULE,
                RUNTIME_SYMBOL,
                index,
                path,
                amount,
                stage.value,
            )
            for index, (path, amount, stage) in enumerate(
                EXPECTED_RUNTIME_CALLS, start=1
            )
        ) + tuple(
            (
                EXECUTOR_MODULE,
                EXECUTOR_SYMBOL,
                index,
                path,
                amount,
                stage.value,
            )
            for index, (path, amount, stage) in enumerate(
                EXPECTED_SUPERVISOR_CALLS, start=1
            )
        )
        if (
            type(self.runtime_source_byte_count) is not int
            or self.runtime_source_byte_count <= 0
            or type(self.executor_source_byte_count) is not int
            or self.executor_source_byte_count <= 0
            or self.runtime_trace_rows != EXPECTED_RUNTIME_TRACE_ROWS
            or self.source_site_rows != expected_sites
        ):
            _fail("abstract common-shared measurement window changed")
        object.__setattr__(self, "_window_id", content_id(WINDOW_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_common_shared_window.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_lease_id": self.source_lease_id,
            "operational_execution_id": self.operational_execution_id,
            "coverage_report_id": self.coverage_report_id,
            "source_archive_id": self.source_archive_id,
            "lifecycle_envelope_id": self.lifecycle_envelope_id,
            "event_trace_id": self.event_trace_id,
            "event_trace_sha256": self.event_trace_sha256,
            "runtime_source_sha256": self.runtime_source_sha256,
            "runtime_source_byte_count": self.runtime_source_byte_count,
            "executor_source_sha256": self.executor_source_sha256,
            "executor_source_byte_count": self.executor_source_byte_count,
            "runtime_trace_rows": [
                {"sequence": sequence, "path": path, "amount": amount}
                for sequence, path, amount in self.runtime_trace_rows
            ],
            "source_site_rows": [
                {
                    "module_name": module,
                    "symbol_qualname": symbol,
                    "site_ordinal": ordinal,
                    "path": path,
                    "amount": amount,
                    "stage_kind": stage,
                }
                for module, symbol, ordinal, path, amount, stage in self.source_site_rows
            ],
            "complete_runtime_trace_bound": True,
            "direct_literal_supervisor_sites_bound": True,
            "measurement_window_start_observed": True,
            "complete_through_operational_cutoff": True,
            "stage_assignment_replayed": True,
            "selected_hash_event_value": EXPECTED_VALUES[HASH_PATH],
            "global_content_id_hash_meter_present": False,
            "hash_counter_record_issued": False,
            "hash_blocker_code": HASH_BLOCKER_CODE,
            "ground_access_performed": False,
        }

    @property
    def window_id(self) -> str:
        current = content_id(WINDOW_DOMAIN, self._payload())
        if current != self._window_id:
            _fail("abstract common-shared window changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "abstract_common_shared_window_id": self.window_id}


@dataclass(frozen=True, slots=True)
class AbstractCertifiedCommonSharedResolutionV1:
    _issuer: InitVar[object]
    window_id: str
    path: str
    value: int
    runtime_value: int
    supervisor_value: int
    stage_values: tuple[tuple[str, int], ...]
    predecessor_claim_id: str
    predecessor_blocker_id: str
    semantics_id: str
    owner: str
    unit: str
    lane: str
    scope: str
    reducer: str
    _resolution_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESOLUTION_ISSUER:
            _fail("abstract common-shared resolution is caller-minted")
        _cid(self.window_id, "common-shared window")
        _cid(self.predecessor_claim_id, "legacy shared claim")
        _cid(self.predecessor_blocker_id, "legacy shared blocker")
        registry = registry_v6.official_counter_registry_v6()
        leaf = registry.by_path.get(self.path)
        runtime_value = sum(
            amount for path, amount, _stage in EXPECTED_RUNTIME_CALLS if path == self.path
        )
        supervisor_value = sum(
            amount for path, amount, _stage in EXPECTED_SUPERVISOR_CALLS if path == self.path
        )
        if (
            self.path not in COMMON_PATHS
            or leaf is None
            or type(self.value) is not int
            or self.value != EXPECTED_VALUES[self.path]
            or self.runtime_value != runtime_value
            or self.supervisor_value != supervisor_value
            or self.value != self.runtime_value + self.supervisor_value
            or self.stage_values != EXPECTED_STAGE_TOTALS[self.path]
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
        ):
            _fail("abstract common-shared resolution differs from V6 semantics")
        object.__setattr__(
            self, "_resolution_id", content_id(RESOLUTION_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_common_shared_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "window_id": self.window_id,
            "path": self.path,
            "value": self.value,
            "runtime_value": self.runtime_value,
            "supervisor_value": self.supervisor_value,
            "stage_values": [
                {"stage_kind": stage, "value": value}
                for stage, value in self.stage_values
            ],
            "predecessor_claim_id": self.predecessor_claim_id,
            "predecessor_blocker_id": self.predecessor_blocker_id,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "unit": self.unit,
            "lane": self.lane,
            "scope": self.scope,
            "reducer": self.reducer,
            "source_v1_record_relabelled_as_v6": False,
            "runtime_events_replayed": True,
            "supervisor_source_sites_replayed": True,
            "formal_v6_counter_record_authorized": True,
            "ground_access_performed": False,
        }

    @property
    def resolution_id(self) -> str:
        current = content_id(RESOLUTION_DOMAIN, self._payload())
        if current != self._resolution_id:
            _fail("abstract common-shared resolution changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "abstract_common_shared_resolution_id": self.resolution_id,
        }


@dataclass(frozen=True, slots=True)
class AbstractCertifiedCommonSharedEnvelopeV1:
    _issuer: InitVar[object]
    window: AbstractCertifiedCommonSharedWindowV1
    resolutions: tuple[AbstractCertifiedCommonSharedResolutionV1, ...]
    counter_records: tuple[CounterRecordV1, ...]
    _envelope_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ENVELOPE_ISSUER
            or type(self.window) is not AbstractCertifiedCommonSharedWindowV1
            or any(type(row) is not AbstractCertifiedCommonSharedResolutionV1 for row in self.resolutions)
            or any(type(row) is not CounterRecordV1 for row in self.counter_records)
            or tuple(row.path for row in self.resolutions) != COMMON_PATHS
            or tuple(row.path for row in self.counter_records) != COMMON_PATHS
            or any(row.window_id != self.window.window_id for row in self.resolutions)
        ):
            _fail("abstract common-shared envelope is caller-minted or reordered")
        registry = registry_v6.official_counter_registry_v6()
        resolutions = {row.path: row for row in self.resolutions}
        for record in self.counter_records:
            resolution = resolutions[record.path]
            record.verify_against(registry.by_path[record.path])
            if (
                record.counter_registry_id != registry.registry_id
                or record.value != resolution.value
                or record.recorder_id != resolution.resolution_id
                or record.observed is not True
                or CounterRecordV1.from_dict(record.to_dict()) != record
            ):
                _fail("common-shared CounterRecord crossed its resolution")
        object.__setattr__(
            self, "_envelope_id", content_id(ENVELOPE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_common_shared_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_code_assessed": TerminalCode.ABSTRACT_CERTIFIED.value,
            "window": self.window.to_document(),
            "resolutions": [row.to_document() for row in self.resolutions],
            "formal_v6_counter_records": [row.to_dict() for row in self.counter_records],
            "required_path_count": EXPECTED_REQUIRED_PATH_COUNT,
            "retained_prior_completion_progress_count": EXPECTED_PRIOR_COMPLETION_COUNT,
            "new_formal_v6_counter_record_count": EXPECTED_NEW_FORMAL_RECORD_COUNT,
            "newly_closed_path_authority_count": EXPECTED_NEW_FORMAL_RECORD_COUNT,
            "combined_completion_progress_count": EXPECTED_COMBINED_COMPLETION_COUNT,
            "remaining_required_path_authority_count": EXPECTED_REMAINING_PATH_COUNT,
            "shared_resource_path_count_closed_here": 2,
            "remaining_shared_resource_path_count": 6,
            "remaining_derived_reconciliation_path_count": 0,
            "all_nine_shared_resource_receipts_complete": False,
            "all_eight_derived_reconciliations_complete": True,
            "complete_202_counter_record_chain_present": False,
            "formal_v6_work_vector_id": None,
            "formal_v6_comparison_vector_id": None,
            "terminal_artifact_id": None,
            "campaign_occurrence_closure_id": None,
            "certificate_issued": False,
            "common_hash_invocations_counter_record_id": None,
            "common_hash_invocations_blocker_code": HASH_BLOCKER_CODE,
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
            _fail("abstract common-shared envelope changed after issuance")
        return current

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "abstract_common_shared_envelope_id": self.envelope_id,
        }


@dataclass(frozen=True, slots=True)
class AbstractCertifiedCommonSharedReplayV1:
    outcome: CommonSharedReplayOutcomeV1
    envelope: AbstractCertifiedCommonSharedEnvelopeV1 | None
    blocker_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            outcome = CommonSharedReplayOutcomeV1(self.outcome)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedCommonSharedAuthorityV1Error(
                "common-shared replay outcome is invalid"
            ) from error
        object.__setattr__(self, "outcome", outcome)
        if outcome is CommonSharedReplayOutcomeV1.VERIFIED:
            if type(self.envelope) is not AbstractCertifiedCommonSharedEnvelopeV1 or self.blocker_codes:
                _fail("verified common-shared replay is inconsistent")
        elif self.envelope is not None or not self.blocker_codes:
            _fail("blocked common-shared replay lacks a typed reason")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_common_shared_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "outcome": self.outcome.value,
            "abstract_common_shared_envelope_id": (
                self.envelope.envelope_id if self.envelope is not None else None
            ),
            "blocker_codes": list(self.blocker_codes),
            "planner_reexecution_performed": False,
            "ground_access_performed": False,
            "formal_v6_work_vector_issued": False,
            "terminal_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def replay_id(self) -> str:
        return content_id(REPLAY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "abstract_common_shared_replay_id": self.replay_id}


def _source_bytes_and_facts(
    report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
) -> tuple[bytes, dict[str, Any], bytes, dict[str, Any]]:
    base = Path(__file__).resolve().parent
    members = {row["module_name"]: row for row in report.source_members}
    runtime_member = members.get(RUNTIME_MODULE)
    executor_member = members.get(EXECUTOR_MODULE)
    if runtime_member is None or executor_member is None:
        _fail("common-shared source archive lacks runtime or executor")
    runtime_raw = (base / RUNTIME_FILENAME).read_bytes()
    executor_raw = (base / EXECUTOR_FILENAME).read_bytes()
    for raw, member, label in (
        (runtime_raw, runtime_member, "runtime"),
        (executor_raw, executor_member, "executor"),
    ):
        if (
            len(raw) != member["source_byte_count"]
            or hashlib.sha256(raw).hexdigest() != member["source_sha256"]
        ):
            _fail(f"{label} source differs from the frozen coverage archive")
    return runtime_raw, runtime_member, executor_raw, executor_member


def _exact_roots(
    source: ModelOnlyRAPMSourceV1,
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_envelope: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
) -> tuple[
    ModelOnlyRAPMSourceV1,
    ModelOnlyQueryExecutionV1,
    coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
]:
    require_model_only_source_authority_v1(source)
    retained = verify_model_only_operational_execution_v1(execution)
    request = model_only_execution_request_v1(
        source,
        regret_tolerance=retained.model_only_result.audit.regret_tolerance,
    )
    if request.request_id != retained.request_id:
        _fail("source authority belongs to another execution request")
    report = coverage_v1.audit_abstract_certified_accounting_coverage_v1(retained)
    _same(report.to_document(), coverage_report.to_document(), "coverage report")
    zeros = zero_v1.close_abstract_certified_zero_value_subset_v1(retained, report)
    _same(zeros.to_document(), zero_closure.to_document(), "zero-value closure")
    inventory = retained_v1.inventory_abstract_pass_retained_v1_accounting_v1(
        retained, report, zeros
    )
    _same(inventory.to_document(), retained_inventory.to_document(), "retained inventory")
    owner = owner_v1.issue_abstract_certified_query_owner_authority_v1(
        retained, report, zeros, inventory
    )
    _same(owner.to_document(), query_owner_envelope.to_document(), "query-owner envelope")
    lifecycle = lifecycle_v1.issue_abstract_certified_lifecycle_reconciliation_authority_v1(
        source, retained, report, zeros, inventory, owner
    )
    _same(lifecycle.to_document(), lifecycle_envelope.to_document(), "lifecycle envelope")
    return source, retained, report, zeros, inventory, owner, lifecycle


def _build_from_exact_roots(
    source: ModelOnlyRAPMSourceV1,
    execution: ModelOnlyQueryExecutionV1,
    report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zeros: zero_v1.AbstractCertifiedZeroValueClosureV1,
    inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    owner: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
) -> AbstractCertifiedCommonSharedEnvelopeV1:
    del zeros, owner
    result = execution.model_only_result
    if result.outcome is not ModelOnlyOutcome.PASS or result.ground_binding_required:
        _fail("common-shared authority requires one exact abstract PASS")
    runtime_raw, runtime_member, executor_raw, executor_member = _source_bytes_and_facts(report)
    runtime_calls = _direct_source_calls(
        runtime_raw,
        filename=RUNTIME_FILENAME,
        symbol=RUNTIME_SYMBOL,
        target="count",
    )
    supervisor_calls = _direct_source_calls(
        executor_raw,
        filename=EXECUTOR_FILENAME,
        symbol=EXECUTOR_SYMBOL,
        target="recorder.add",
    )
    if runtime_calls != tuple((path, amount) for path, amount, _stage in EXPECTED_RUNTIME_CALLS):
        _fail("runtime common call inventory changed")
    if supervisor_calls != tuple((path, amount) for path, amount, _stage in EXPECTED_SUPERVISOR_CALLS):
        _fail("supervisor common call inventory changed")

    trace_rows = tuple(
        (event.sequence, event.path, event.amount)
        for event in execution.native_event_trace.events
        if event.path in OBSERVED_COMMON_PATHS
    )
    if trace_rows != EXPECTED_RUNTIME_TRACE_ROWS:
        _fail("runtime common event trace changed")
    trace_sha = hashlib.sha256(
        canonical_json_bytes(execution.native_event_trace.to_dict())
    ).hexdigest()
    source_sites = tuple(
        (
            RUNTIME_MODULE,
            RUNTIME_SYMBOL,
            index,
            path,
            amount,
            stage.value,
        )
        for index, (path, amount, stage) in enumerate(EXPECTED_RUNTIME_CALLS, start=1)
    ) + tuple(
        (
            EXECUTOR_MODULE,
            EXECUTOR_SYMBOL,
            index,
            path,
            amount,
            stage.value,
        )
        for index, (path, amount, stage) in enumerate(EXPECTED_SUPERVISOR_CALLS, start=1)
    )
    window = AbstractCertifiedCommonSharedWindowV1(
        _WINDOW_ISSUER,
        source.lease.source_lease_id,
        execution.operational_execution_id,
        report.report_id,
        report.source_archive_id,
        lifecycle.envelope_id,
        execution.native_event_trace.event_trace_id,
        trace_sha,
        runtime_member["source_sha256"],
        runtime_member["source_byte_count"],
        executor_member["source_sha256"],
        executor_member["source_byte_count"],
        trace_rows,
        source_sites,
    )

    claims = {row.path: row for row in inventory.shared_claims}
    blockers = {row.path: row for row in inventory.formal_blockers}
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    all_path = all_path_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    dispositions = {
        row.stage_kind: row.disposition
        for row in all_path.terminal_path_rule_by_code[
            TerminalCode.ABSTRACT_CERTIFIED
        ].stage_plan
    }
    for stage in (PREOPEN_STAGE, CLOSED_STAGE):
        if dispositions[stage] is not all_path_v1.StageDispositionV1.REQUIRED_ONCE:
            _fail("common-shared stage is no longer required once")

    resolutions: list[AbstractCertifiedCommonSharedResolutionV1] = []
    records: list[CounterRecordV1] = []
    for path in COMMON_PATHS:
        claim = claims[path]
        blocker = blockers[path]
        leaf = registry.by_path[path]
        if (
            claim.reported_value != EXPECTED_VALUES[path]
            or blocker.code
            is not retained_v1.FormalBlockerCodeV1.LEGACY_SHARED_AGGREGATE_LACKS_WINDOW_STAGE_CUTOFF_REPLAY
            or blocker.source_evidence_id != claim.claim_id
            or any(
                path not in stage_profile.by_stage[stage].allowed_nonzero_paths
                for stage in (PREOPEN_STAGE, CLOSED_STAGE)
            )
        ):
            _fail(f"common-shared predecessor changed for {path}")
        runtime_value = sum(
            amount for _sequence, row_path, amount in trace_rows if row_path == path
        )
        supervisor_value = sum(
            amount
            for row_path, amount, _stage in EXPECTED_SUPERVISOR_CALLS
            if row_path == path
        )
        resolution = AbstractCertifiedCommonSharedResolutionV1(
            _RESOLUTION_ISSUER,
            window.window_id,
            path,
            EXPECTED_VALUES[path],
            runtime_value,
            supervisor_value,
            EXPECTED_STAGE_TOTALS[path],
            claim.claim_id,
            blocker.blocker_id,
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane.value,
            leaf.scope,
            leaf.reducer.value,
        )
        resolutions.append(resolution)
        records.append(
            CounterRecordV1.observe(
                registry,
                path,
                resolution.value,
                recorder_id=resolution.resolution_id,
            )
        )
    return AbstractCertifiedCommonSharedEnvelopeV1(
        _ENVELOPE_ISSUER,
        window,
        tuple(resolutions),
        tuple(records),
    )


def issue_abstract_certified_common_shared_authority_v1(
    source: ModelOnlyRAPMSourceV1,
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_envelope: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
) -> AbstractCertifiedCommonSharedEnvelopeV1:
    roots = _exact_roots(
        source,
        execution,
        coverage_report,
        zero_closure,
        retained_inventory,
        query_owner_envelope,
        lifecycle_envelope,
    )
    return _build_from_exact_roots(*roots)


def verify_abstract_certified_common_shared_authority_bytes_v1(
    raw: bytes,
    source: ModelOnlyRAPMSourceV1,
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_envelope: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
) -> AbstractCertifiedCommonSharedReplayV1:
    try:
        if type(raw) is not bytes:
            _fail("common-shared replay requires canonical bytes")
        claimed = loads_canonical_json(raw)
        if type(claimed) is not dict or canonical_json_bytes(claimed) != raw:
            _fail("common-shared envelope bytes are noncanonical")
        roots = _exact_roots(
            source,
            execution,
            coverage_report,
            zero_closure,
            retained_inventory,
            query_owner_envelope,
            lifecycle_envelope,
        )
        expected = _build_from_exact_roots(*roots)
        if raw != expected.canonical_bytes:
            _fail("claimed common-shared envelope differs from exact replay")
    except Exception:
        return AbstractCertifiedCommonSharedReplayV1(
            CommonSharedReplayOutcomeV1.DOCUMENT_BLOCKED,
            None,
            ("EXACT_ABSTRACT_COMMON_SHARED_REPLAY_FAILED",),
        )
    return AbstractCertifiedCommonSharedReplayV1(
        CommonSharedReplayOutcomeV1.VERIFIED,
        expected,
        (),
    )


__all__ = [
    "AbstractCertifiedCommonSharedEnvelopeV1",
    "AbstractCertifiedCommonSharedReplayV1",
    "AbstractCertifiedCommonSharedResolutionV1",
    "AbstractCertifiedCommonSharedWindowV1",
    "COMMON_PATHS",
    "CommonSharedReplayOutcomeV1",
    "ConstructionK7AbstractCertifiedCommonSharedAuthorityV1Error",
    "EXPECTED_COMBINED_COMPLETION_COUNT",
    "EXPECTED_NEW_FORMAL_RECORD_COUNT",
    "EXPECTED_REMAINING_PATH_COUNT",
    "EXPECTED_VALUES",
    "LOCAL_DOMAINS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "issue_abstract_certified_common_shared_authority_v1",
    "verify_abstract_certified_common_shared_authority_bytes_v1",
]
