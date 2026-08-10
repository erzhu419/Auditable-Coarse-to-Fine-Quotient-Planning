"""Lifecycle and derived reconciliation for one retained abstract PASS.

This boundary closes six additional ABSTRACT_CERTIFIED path authorities and
materializes nine formal records: the one model-only worker launch plus all
eight derived reconciliation leaves.  Three derived failure-zero leaves were
already value-proved by the predecessor zero closure; they are materialized
here rather than counted again as newly closed paths.  The boundary also
corrects a legacy V1 classification error:
``solver.attempts`` and ``solver.successes`` counted the abstract planner, but
the V6 catalogue reserves those leaves for LOCAL_ATTEMPT/DIRECT_FALLBACK.
Both stages are forbidden for ABSTRACT_CERTIFIED, so the exact V6 values are
zero rather than the retained V1 value one.

The result contains one shared-resource record and eight derived-only records.
It is still not a WorkVector or ComparisonVector and does not unlock a Gate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import Any, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage_v1
from acfqp import construction_k7_abstract_certified_native_zero_closure_v1 as zero_v1
from acfqp import construction_k7_abstract_certified_query_owner_authority_v1 as owner_v1
from acfqp import construction_k7_abstract_pass_production_native_accounting_v1 as retained_v1
from acfqp import construction_k7_all_path_accounting_profile_v1 as all_path_v1
from acfqp import construction_k7_derived_reconciliation_v1 as derived_v1
from acfqp.accounting_v1 import CounterRecordV1, RouteKindEnum
from acfqp.phase3e_abstract_pass_closure_v1 import (
    verify_model_only_operational_execution_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_ENVELOPE_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_RESOLUTION_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_WINDOW_V1_DOMAIN,
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
PROPOSED_CONTRACT_VERSION = "2.0.65"
PROFILE_KEY = (
    "construction_k7_abstract_certified_lifecycle_reconciliation_authority_v1"
)

EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_PRIOR_COMPLETION_COUNT = 28
EXPECTED_NEW_FORMAL_RECORD_COUNT = 9
EXPECTED_NEW_PATH_AUTHORITY_COUNT = 6
EXPECTED_COMBINED_COMPLETION_COUNT = 34
EXPECTED_REMAINING_PATH_COUNT = 168

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

WINDOW_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_WINDOW_V1_DOMAIN
RESOLUTION_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_RESOLUTION_V1_DOMAIN
)
ENVELOPE_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_ENVELOPE_V1_DOMAIN
REPLAY_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_REPLAY_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {WINDOW_DOMAIN, RESOLUTION_DOMAIN, ENVELOPE_DOMAIN, REPLAY_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("abstract lifecycle domains are not central and unique")

LIFECYCLE_PATHS = (
    "process.launches",
    "process.exit_failures",
    "process.exit_successes",
    "route.attempts",
    "route.failures",
    "route.successes",
    "solver.attempts",
    "solver.failures",
    "solver.successes",
)
RESOLUTION_BUILD_ORDER = (
    "process.launches",
    "process.exit_failures",
    "process.exit_successes",
    "route.failures",
    "route.successes",
    "route.attempts",
    "solver.failures",
    "solver.successes",
    "solver.attempts",
)
if set(RESOLUTION_BUILD_ORDER) != set(LIFECYCLE_PATHS):  # pragma: no cover
    raise RuntimeError("abstract lifecycle dependency order is incomplete")
FORMAL_VALUES = {
    "process.launches": 1,
    "process.exit_failures": 0,
    "process.exit_successes": 1,
    "route.attempts": 1,
    "route.failures": 0,
    "route.successes": 1,
    "solver.attempts": 0,
    "solver.failures": 0,
    "solver.successes": 0,
}
LEGACY_VALUES = {
    "process.launches": 1,
    "process.exit_failures": 0,
    "process.exit_successes": 1,
    "route.attempts": 1,
    "route.failures": 0,
    "route.successes": 1,
    "solver.attempts": 1,
    "solver.failures": 0,
    "solver.successes": 1,
}
FAILURE_PATHS = (
    "process.exit_failures",
    "route.failures",
    "solver.failures",
)
SOURCE_STAGES = {
    "process.launches": registry_v6.ConstructionStageKindV6.PREOPEN_COMMON_PREFIX,
    "process.exit_failures": (
        registry_v6.ConstructionStageKindV6
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
    "process.exit_successes": (
        registry_v6.ConstructionStageKindV6
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
    "route.attempts": (
        registry_v6.ConstructionStageKindV6
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
    "route.failures": (
        registry_v6.ConstructionStageKindV6
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
    "route.successes": (
        registry_v6.ConstructionStageKindV6
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
}
FORBIDDEN_SOLVER_STAGES = (
    registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
    registry_v6.ConstructionStageKindV6.LOCAL_ATTEMPT,
)

_WINDOW_ISSUER = object()
_RESOLUTION_ISSUER = object()
_ENVELOPE_ISSUER = object()


class ConstructionK7AbstractCertifiedLifecycleAuthorityV1Error(ValueError):
    """The lifecycle, source closure, or V6 normalization changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractCertifiedLifecycleAuthorityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractCertifiedLifecycleAuthorityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _same(left: Any, right: Any, label: str) -> None:
    try:
        matched = canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractCertifiedLifecycleAuthorityV1Error(
            f"{label} is not canonical"
        ) from error
    if not matched:
        _fail(f"{label} crossed its exact root")


class LifecycleResolutionKindV1(str, Enum):
    OBSERVED_PROCESS_LIFECYCLE = "OBSERVED_PROCESS_LIFECYCLE"
    OBSERVED_ROUTE_LIFECYCLE = "OBSERVED_ROUTE_LIFECYCLE"
    SUCCESS_COMPLEMENT_ZERO_MATERIALIZATION = (
        "SUCCESS_COMPLEMENT_ZERO_MATERIALIZATION"
    )
    PROFILE_NATIVE_ZERO_MATERIALIZATION = "PROFILE_NATIVE_ZERO_MATERIALIZATION"


class LifecycleReplayOutcomeV1(str, Enum):
    VERIFIED = "EXACT_ABSTRACT_LIFECYCLE_RECONCILIATION_VERIFIED"
    DOCUMENT_BLOCKED = "ABSTRACT_LIFECYCLE_RECONCILIATION_DOCUMENT_BLOCKED"


@dataclass(frozen=True, slots=True)
class AbstractCertifiedLifecycleWindowV1:
    _issuer: InitVar[object]
    source_lease_id: str
    request_id: str
    worker_output_id: str
    model_only_result_id: str
    operational_execution_id: str
    legacy_work_vector_id: str
    legacy_reconciliation_proof_id: str
    source_archive_id: str
    executor_source_sha256: str
    executor_source_byte_count: int
    zero_value_closure_id: str
    retained_v1_inventory_id: str
    query_owner_envelope_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    route_decision_context_id: str
    legacy_lifecycle_values: tuple[tuple[str, int], ...]
    _window_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _WINDOW_ISSUER:
            _fail("abstract lifecycle window is caller-minted")
        for value, label in (
            (self.source_lease_id, "source lease"),
            (self.request_id, "execution request"),
            (self.worker_output_id, "worker output"),
            (self.model_only_result_id, "model-only result"),
            (self.operational_execution_id, "operational execution"),
            (self.legacy_work_vector_id, "legacy work vector"),
            (self.legacy_reconciliation_proof_id, "legacy reconciliation proof"),
            (self.source_archive_id, "source archive"),
            (self.executor_source_sha256, "executor source digest"),
            (self.zero_value_closure_id, "zero-value closure"),
            (self.retained_v1_inventory_id, "retained-V1 inventory"),
            (self.query_owner_envelope_id, "query-owner envelope"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.route_decision_context_id, "route-decision context"),
        ):
            _cid(value, label)
        if (
            type(self.executor_source_byte_count) is not int
            or self.executor_source_byte_count <= 0
            or self.legacy_lifecycle_values
            != tuple(sorted(LEGACY_VALUES.items()))
        ):
            _fail("abstract lifecycle window facts changed")
        object.__setattr__(
            self, "_window_id", content_id(WINDOW_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_lifecycle_window.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_lease_id": self.source_lease_id,
            "request_id": self.request_id,
            "worker_output_id": self.worker_output_id,
            "model_only_result_id": self.model_only_result_id,
            "operational_execution_id": self.operational_execution_id,
            "legacy_work_vector_id": self.legacy_work_vector_id,
            "legacy_reconciliation_proof_id": self.legacy_reconciliation_proof_id,
            "source_archive_id": self.source_archive_id,
            "executor_source_sha256": self.executor_source_sha256,
            "executor_source_byte_count": self.executor_source_byte_count,
            "zero_value_closure_id": self.zero_value_closure_id,
            "retained_v1_inventory_id": self.retained_v1_inventory_id,
            "query_owner_envelope_id": self.query_owner_envelope_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "route_decision_context_id": self.route_decision_context_id,
            "legacy_lifecycle_values": [
                {"path": path, "value": value}
                for path, value in self.legacy_lifecycle_values
            ],
            "fresh_worker_launch_count": 1,
            "successful_worker_exit_count": 1,
            "abstract_only_route_attempt_count": 1,
            "abstract_only_route_success_count": 1,
            "local_or_fallback_solver_attempt_count": 0,
            "executor_source_and_hook_inventory_replayed": True,
            "fresh_process_returncode_zero_bound": True,
            "abstract_route_pass_terminal_bound": True,
            "lifecycle_complete_through_operational_cutoff": True,
            "legacy_abstract_planner_solver_classification_accepted": False,
            "legacy_retained_decision_point_alias_used_as_authority": False,
            "ground_access_performed": False,
        }

    @property
    def window_id(self) -> str:
        current = content_id(WINDOW_DOMAIN, self._payload())
        if current != self._window_id:
            _fail("abstract lifecycle window changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "abstract_lifecycle_window_id": self.window_id}


@dataclass(frozen=True, slots=True)
class AbstractCertifiedLifecycleResolutionV1:
    _issuer: InitVar[object]
    window_id: str
    path: str
    kind: LifecycleResolutionKindV1
    formal_value: int
    legacy_value: int
    predecessor_evidence_id: str
    predecessor_blocker_id: str
    formula_id: str | None
    supporting_proof_ids: tuple[str, ...]
    stage_kinds: tuple[registry_v6.ConstructionStageKindV6, ...]
    semantics_id: str
    owner: str
    unit: str
    lane: str
    scope: str
    reducer: str
    _resolution_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESOLUTION_ISSUER:
            _fail("abstract lifecycle resolution is caller-minted")
        for value, label in (
            (self.window_id, "lifecycle window"),
            (self.predecessor_evidence_id, "predecessor evidence"),
            (self.predecessor_blocker_id, "predecessor blocker"),
            *((value, "supporting proof") for value in self.supporting_proof_ids),
        ):
            _cid(value, label)
        if self.formula_id is not None:
            _cid(self.formula_id, "reconciliation formula")
        try:
            kind = LifecycleResolutionKindV1(self.kind)
            stages = tuple(
                registry_v6.ConstructionStageKindV6(row) for row in self.stage_kinds
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedLifecycleAuthorityV1Error(
                "lifecycle resolution enum changed"
            ) from error
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "stage_kinds", stages)
        registry = registry_v6.official_counter_registry_v6()
        leaf = registry.by_path.get(self.path)
        expected_kind = (
            LifecycleResolutionKindV1.PROFILE_NATIVE_ZERO_MATERIALIZATION
            if self.path.startswith("solver.")
            else LifecycleResolutionKindV1.SUCCESS_COMPLEMENT_ZERO_MATERIALIZATION
            if self.path in {"process.exit_failures", "route.failures"}
            else LifecycleResolutionKindV1.OBSERVED_PROCESS_LIFECYCLE
            if self.path.startswith("process.")
            else LifecycleResolutionKindV1.OBSERVED_ROUTE_LIFECYCLE
        )
        expected_stages = (
            (SOURCE_STAGES[self.path],)
            if self.path in SOURCE_STAGES
            else FORBIDDEN_SOLVER_STAGES
        )
        if (
            self.path not in LIFECYCLE_PATHS
            or leaf is None
            or kind is not expected_kind
            or self.formal_value != FORMAL_VALUES[self.path]
            or self.legacy_value != LEGACY_VALUES[self.path]
            or stages != expected_stages
            or tuple(sorted(self.supporting_proof_ids)) != self.supporting_proof_ids
            or len(set(self.supporting_proof_ids)) != len(self.supporting_proof_ids)
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
            or (self.path == "process.launches" and self.formula_id is not None)
            or (self.path != "process.launches" and self.formula_id is None)
        ):
            _fail("abstract lifecycle resolution differs from V6 semantics")
        object.__setattr__(
            self,
            "_resolution_id",
            content_id(RESOLUTION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_lifecycle_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "window_id": self.window_id,
            "path": self.path,
            "resolution_kind": self.kind.value,
            "formal_value": self.formal_value,
            "legacy_value": self.legacy_value,
            "predecessor_evidence_id": self.predecessor_evidence_id,
            "predecessor_blocker_id": self.predecessor_blocker_id,
            "reconciliation_formula_id": self.formula_id,
            "supporting_proof_ids": list(self.supporting_proof_ids),
            "stage_kinds": [row.value for row in self.stage_kinds],
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "unit": self.unit,
            "lane": self.lane,
            "scope": self.scope,
            "reducer": self.reducer,
            "source_v1_record_relabelled_as_v6": False,
            "prior_zero_value_proof_materialized": self.path in FAILURE_PATHS,
            "legacy_value_changed_by_v6_normalization": (
                self.legacy_value != self.formal_value
            ),
            "legacy_solver_value_rejected": (
                self.path.startswith("solver.")
                and self.legacy_value != self.formal_value
            ),
            "profile_native_zero_issued": self.path.startswith("solver."),
            "formal_v6_counter_record_authorized": True,
            "ground_access_performed": False,
        }

    @property
    def resolution_id(self) -> str:
        current = content_id(RESOLUTION_DOMAIN, self._payload())
        if current != self._resolution_id:
            _fail("abstract lifecycle resolution changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "abstract_lifecycle_resolution_id": self.resolution_id,
        }


@dataclass(frozen=True, slots=True)
class AbstractCertifiedLifecycleEnvelopeV1:
    _issuer: InitVar[object]
    window: AbstractCertifiedLifecycleWindowV1
    resolutions: tuple[AbstractCertifiedLifecycleResolutionV1, ...]
    counter_records: tuple[CounterRecordV1, ...]
    _envelope_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ENVELOPE_ISSUER
            or type(self.window) is not AbstractCertifiedLifecycleWindowV1
            or any(
                type(row) is not AbstractCertifiedLifecycleResolutionV1
                for row in self.resolutions
            )
            or any(type(row) is not CounterRecordV1 for row in self.counter_records)
        ):
            _fail("abstract lifecycle envelope is caller-minted")
        registry = registry_v6.official_counter_registry_v6()
        if (
            tuple(row.path for row in self.resolutions) != LIFECYCLE_PATHS
            or tuple(row.path for row in self.counter_records) != LIFECYCLE_PATHS
            or any(row.window_id != self.window.window_id for row in self.resolutions)
        ):
            _fail("abstract lifecycle envelope path order changed")
        by_path = {row.path: row for row in self.resolutions}
        for record in self.counter_records:
            resolution = by_path[record.path]
            record.verify_against(registry.by_path[record.path])
            if (
                record.counter_registry_id != registry.registry_id
                or record.value != resolution.formal_value
                or record.recorder_id != resolution.resolution_id
                or record.observed is not True
                or CounterRecordV1.from_dict(record.to_dict()) != record
            ):
                _fail("abstract lifecycle CounterRecord crossed its resolution")
        values = {row.path: row.value for row in self.counter_records}
        if (
            values["process.launches"]
            != values["process.exit_failures"] + values["process.exit_successes"]
            or values["route.attempts"]
            != values["route.failures"] + values["route.successes"]
            or values["solver.attempts"]
            != values["solver.failures"] + values["solver.successes"]
            or any(values[path] != FORMAL_VALUES[path] for path in LIFECYCLE_PATHS)
        ):
            _fail("abstract lifecycle reconciliation equations changed")
        object.__setattr__(
            self, "_envelope_id", content_id(ENVELOPE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_lifecycle_envelope.v1",
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
            "newly_closed_path_authority_count": EXPECTED_NEW_PATH_AUTHORITY_COUNT,
            "combined_completion_progress_count": EXPECTED_COMBINED_COMPLETION_COUNT,
            "remaining_required_path_authority_count": EXPECTED_REMAINING_PATH_COUNT,
            "shared_resource_path_count_closed_here": 1,
            "derived_reconciliation_path_count_closed_here": 5,
            "derived_reconciliation_formal_record_count_materialized_here": 8,
            "prior_zero_proof_materialization_count": 3,
            "remaining_shared_resource_path_count": 8,
            "remaining_derived_reconciliation_path_count": 0,
            "legacy_solver_classification_corrected": True,
            "all_nine_shared_resource_receipts_complete": False,
            "all_eight_derived_reconciliations_complete": True,
            "complete_202_counter_record_chain_present": False,
            "formal_v6_work_vector_id": None,
            "formal_v6_comparison_vector_id": None,
            "terminal_artifact_id": None,
            "campaign_occurrence_closure_id": None,
            "certificate_issued": False,
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
            _fail("abstract lifecycle envelope changed after issuance")
        return current

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "abstract_lifecycle_envelope_id": self.envelope_id,
        }


@dataclass(frozen=True, slots=True)
class AbstractCertifiedLifecycleReplayV1:
    outcome: LifecycleReplayOutcomeV1
    envelope: AbstractCertifiedLifecycleEnvelopeV1 | None
    blocker_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            outcome = LifecycleReplayOutcomeV1(self.outcome)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedLifecycleAuthorityV1Error(
                "lifecycle replay outcome is invalid"
            ) from error
        object.__setattr__(self, "outcome", outcome)
        if outcome is LifecycleReplayOutcomeV1.VERIFIED:
            if type(self.envelope) is not AbstractCertifiedLifecycleEnvelopeV1 or self.blocker_codes:
                _fail("verified lifecycle replay is inconsistent")
        elif self.envelope is not None or not self.blocker_codes:
            _fail("blocked lifecycle replay lacks a typed reason")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_lifecycle_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "outcome": self.outcome.value,
            "abstract_lifecycle_envelope_id": (
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
        return {**self._payload(), "abstract_lifecycle_replay_id": self.replay_id}


def _exact_roots(
    source: ModelOnlyRAPMSourceV1,
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
) -> tuple[
    ModelOnlyRAPMSourceV1,
    ModelOnlyQueryExecutionV1,
    coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
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
    return source, retained, report, zeros, inventory, owner


def _build_from_exact_roots(
    source: ModelOnlyRAPMSourceV1,
    execution: ModelOnlyQueryExecutionV1,
    report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zeros: zero_v1.AbstractCertifiedZeroValueClosureV1,
    inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    owner: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
) -> AbstractCertifiedLifecycleEnvelopeV1:
    result = execution.model_only_result
    work = execution.recorded_work
    vector = work.work_vector
    if (
        result.outcome is not ModelOnlyOutcome.PASS
        or result.ground_binding_required
        or vector.route_kind is not RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
        or vector.subject_id != result.route_attempt.route_attempt_id
    ):
        _fail("lifecycle authority requires one exact abstract-only PASS")

    source_members = {
        row["module_name"]: row for row in report.source_members
    }
    executor_member = source_members.get("acfqp.phase3e_model_only_executor_v1")
    hooks = report.to_document()["existing_selected_hook_sites"]
    required_hooks = {
        "subprocess.run": 1,
        "recorder.record_process_completion": 1,
        "recorder.record_solver_completion": 1,
        "recorder.record_route_completion": 1,
    }
    observed_hooks = {
        row["call_target"]: row["call_count"]
        for row in hooks
        if row["module_name"] == "acfqp.phase3e_model_only_executor_v1"
        and row["symbol_qualname"] == "execute_model_only_query_v1"
        and row["call_target"] in required_hooks
    }
    if executor_member is None or observed_hooks != required_hooks:
        _fail("executor source or lifecycle hook inventory changed")

    legacy_values = tuple(
        sorted(
            (path, vector.value(path))
            for path in LIFECYCLE_PATHS
        )
    )
    expected_legacy = tuple(sorted(LEGACY_VALUES.items()))
    if legacy_values != expected_legacy:
        _fail("retained lifecycle values changed")

    window = AbstractCertifiedLifecycleWindowV1(
        _WINDOW_ISSUER,
        source.lease.source_lease_id,
        execution.request_id,
        execution.worker_output_id,
        result.result_id,
        execution.operational_execution_id,
        vector.work_vector_id,
        work.reconciliation_proof.reconciliation_proof_id,
        report.source_archive_id,
        executor_member["source_sha256"],
        executor_member["source_byte_count"],
        zeros.closure_id,
        inventory.inventory_id,
        owner.envelope_id,
        result.logical_occurrence.logical_occurrence_id,
        result.route_attempt.route_attempt_id,
        result.route_context.route_decision_context_id,
        legacy_values,
    )

    zero_proofs = {
        row.path: row
        for row in zeros.derived_complement_value_proofs
    }
    if set(zero_proofs) != set(FAILURE_PATHS):
        _fail("lifecycle failure-zero proof set changed")
    shared_claims = {row.path: row for row in inventory.shared_claims}
    reconciliation_claims = {
        row.path: row for row in inventory.reconciliation_claims
    }
    blockers = {row.path: row for row in inventory.formal_blockers}
    formulas = {
        row.path: row for row in derived_v1.official_k7_reconciliation_formulas_v1()
    }
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    all_path = all_path_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    dispositions = {
        row.stage_kind: row.disposition
        for row in all_path.terminal_path_rule_by_code[
            TerminalCode.ABSTRACT_CERTIFIED
        ].stage_plan
    }

    resolution_by_path: dict[str, AbstractCertifiedLifecycleResolutionV1] = {}
    for path in RESOLUTION_BUILD_ORDER:
        leaf = registry.by_path[path]
        if path == "process.launches":
            claim = shared_claims[path]
            predecessor_id = claim.claim_id
            expected_code = (
                retained_v1.FormalBlockerCodeV1
                .LEGACY_SHARED_AGGREGATE_LACKS_WINDOW_STAGE_CUTOFF_REPLAY
            )
            formula_id = None
            support_ids = ()
        else:
            claim = reconciliation_claims[path]
            predecessor_id = claim.claim_id
            expected_code = (
                retained_v1.FormalBlockerCodeV1
                .LEGACY_INTERNAL_RECONCILIATION_LACKS_FORMAL_DEPENDENCIES
            )
            formula_id = formulas[path].formula_id
            if path == "process.exit_failures":
                support_ids = (
                    resolution_by_path["process.launches"].resolution_id,
                    zero_proofs["process.exit_failures"].proof_id,
                )
            elif path == "process.exit_successes":
                support_ids = (
                    resolution_by_path["process.exit_failures"].resolution_id,
                    resolution_by_path["process.launches"].resolution_id,
                )
            elif path == "route.failures":
                support_ids = (
                    resolution_by_path["process.exit_failures"].resolution_id,
                    resolution_by_path["process.exit_successes"].resolution_id,
                    zero_proofs["route.failures"].proof_id,
                )
            elif path == "route.successes":
                support_ids = (
                    resolution_by_path["process.exit_failures"].resolution_id,
                    resolution_by_path["process.exit_successes"].resolution_id,
                )
            elif path == "route.attempts":
                support_ids = (
                    resolution_by_path["route.failures"].resolution_id,
                    resolution_by_path["route.successes"].resolution_id,
                )
            elif path == "solver.failures":
                support_ids = (
                    all_path.profile_id,
                    resolution_by_path["route.attempts"].resolution_id,
                    zero_proofs["solver.failures"].proof_id,
                )
            elif path == "solver.successes":
                support_ids = (
                    all_path.profile_id,
                    resolution_by_path["route.attempts"].resolution_id,
                )
            else:
                support_ids = (
                    resolution_by_path["solver.failures"].resolution_id,
                    resolution_by_path["solver.successes"].resolution_id,
                )
        blocker = blockers[path]
        stages = (
            (SOURCE_STAGES[path],)
            if path in SOURCE_STAGES
            else FORBIDDEN_SOLVER_STAGES
        )
        if (
            blocker.code is not expected_code
            or blocker.source_evidence_id != predecessor_id
            or any(
                stage not in stage_profile.by_stage
                or path not in stage_profile.by_stage[stage].allowed_nonzero_paths
                for stage in stages
            )
            or (
                path.startswith("solver.")
                and any(
                    dispositions[stage]
                    is not all_path_v1.StageDispositionV1.FORBIDDEN
                    for stage in stages
                )
            )
            or (
                path in SOURCE_STAGES
                and dispositions[SOURCE_STAGES[path]]
                is not all_path_v1.StageDispositionV1.REQUIRED_ONCE
            )
        ):
            _fail(f"lifecycle predecessor or stage proof changed for {path}")
        resolution = AbstractCertifiedLifecycleResolutionV1(
            _RESOLUTION_ISSUER,
            window.window_id,
            path,
            (
                LifecycleResolutionKindV1.PROFILE_NATIVE_ZERO_MATERIALIZATION
                if path.startswith("solver.")
                else LifecycleResolutionKindV1.SUCCESS_COMPLEMENT_ZERO_MATERIALIZATION
                if path in {"process.exit_failures", "route.failures"}
                else
                LifecycleResolutionKindV1.OBSERVED_PROCESS_LIFECYCLE
                if path.startswith("process.")
                else LifecycleResolutionKindV1.OBSERVED_ROUTE_LIFECYCLE
            ),
            FORMAL_VALUES[path],
            LEGACY_VALUES[path],
            predecessor_id,
            blocker.blocker_id,
            formula_id,
            tuple(sorted(support_ids)),
            stages,
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane.value,
            leaf.scope,
            leaf.reducer.value,
        )
        resolution_by_path[path] = resolution
    resolutions = tuple(resolution_by_path[path] for path in LIFECYCLE_PATHS)
    records = tuple(
        CounterRecordV1.observe(
            registry,
            path,
            FORMAL_VALUES[path],
            recorder_id=resolution_by_path[path].resolution_id,
        )
        for path in LIFECYCLE_PATHS
    )
    return AbstractCertifiedLifecycleEnvelopeV1(
        _ENVELOPE_ISSUER,
        window,
        resolutions,
        records,
    )


def issue_abstract_certified_lifecycle_reconciliation_authority_v1(
    source: ModelOnlyRAPMSourceV1,
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
) -> AbstractCertifiedLifecycleEnvelopeV1:
    roots = _exact_roots(
        source,
        execution,
        coverage_report,
        zero_closure,
        retained_inventory,
        query_owner_envelope,
    )
    return _build_from_exact_roots(*roots)


def verify_abstract_certified_lifecycle_reconciliation_bytes_v1(
    raw: bytes,
    source: ModelOnlyRAPMSourceV1,
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
) -> AbstractCertifiedLifecycleReplayV1:
    try:
        if type(raw) is not bytes:
            _fail("lifecycle replay requires canonical bytes")
        claimed = loads_canonical_json(raw)
        if type(claimed) is not dict or canonical_json_bytes(claimed) != raw:
            _fail("lifecycle envelope bytes are noncanonical")
        roots = _exact_roots(
            source,
            execution,
            coverage_report,
            zero_closure,
            retained_inventory,
            query_owner_envelope,
        )
        expected = _build_from_exact_roots(*roots)
        if raw != expected.canonical_bytes:
            _fail("claimed lifecycle envelope differs from exact replay")
    except Exception:
        return AbstractCertifiedLifecycleReplayV1(
            LifecycleReplayOutcomeV1.DOCUMENT_BLOCKED,
            None,
            ("EXACT_ABSTRACT_LIFECYCLE_REPLAY_FAILED",),
        )
    return AbstractCertifiedLifecycleReplayV1(
        LifecycleReplayOutcomeV1.VERIFIED,
        expected,
        (),
    )


__all__ = [
    "AbstractCertifiedLifecycleEnvelopeV1",
    "AbstractCertifiedLifecycleReplayV1",
    "AbstractCertifiedLifecycleResolutionV1",
    "AbstractCertifiedLifecycleWindowV1",
    "ConstructionK7AbstractCertifiedLifecycleAuthorityV1Error",
    "EXPECTED_COMBINED_COMPLETION_COUNT",
    "EXPECTED_NEW_FORMAL_RECORD_COUNT",
    "EXPECTED_NEW_PATH_AUTHORITY_COUNT",
    "EXPECTED_PRIOR_COMPLETION_COUNT",
    "EXPECTED_REMAINING_PATH_COUNT",
    "EXPECTED_REQUIRED_PATH_COUNT",
    "FORMAL_VALUES",
    "FORBIDDEN_SOLVER_STAGES",
    "LIFECYCLE_PATHS",
    "LOCAL_DOMAINS",
    "LifecycleReplayOutcomeV1",
    "LifecycleResolutionKindV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "issue_abstract_certified_lifecycle_reconciliation_authority_v1",
    "verify_abstract_certified_lifecycle_reconciliation_bytes_v1",
]
