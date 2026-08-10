"""Formal V6 authority for eight sealed abstract shared-resource paths.

The historical V1 aggregate values are retained only as predecessor blockers.
This module rebuilds the exact 34-path query-owner/lifecycle prefix, requires
one live accounted V2 PASS, binds its immutable runtime preparation and
measurement window, and issues fresh V6 CounterRecords for the seven shared
resource paths that are neither the already-authorized ``process.launches``
nor the pending ``io.output_bytes``.  The measured launch is joined exactly to
the lifecycle record instead of being issued a second time.  Output remains
pending because it must be solved with the final operational artifact set in
one fixed point.

No partial WorkVector is materialized and no terminal, campaign, official
execution, scalar, break-even, or Gate claim is made.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage_v1
from acfqp import construction_k7_abstract_certified_lifecycle_reconciliation_authority_v1 as lifecycle_v1
from acfqp import construction_k7_abstract_certified_native_zero_closure_v1 as zero_v1
from acfqp import construction_k7_abstract_certified_query_owner_authority_v1 as owner_v1
from acfqp import construction_k7_abstract_pass_production_native_accounting_v1 as retained_v1
from acfqp.accounting_v1 import CounterRecordV1, ReducerEnum
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_ENVELOPE_V2_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_REPLAY_V2_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_RESOLUTION_V2_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.phase3e_model_only_accounted_executor_v2 import (
    FORMAL_SHARED_PATHS,
    PENDING_SHARED_PATH,
    AccountedModelOnlyExecutionV2,
    require_accounted_model_only_execution_v2,
)
from acfqp.phase3e_model_only_executor_v1 import model_only_execution_request_v1
from acfqp.phase3e_rapm_consumer_v1 import (
    ModelOnlyRAPMSourceV1,
    require_model_only_source_authority_v1,
)
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.69"
PROFILE_KEY = "construction_k7_abstract_accounted_shared_authority_v2"

EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_PRIOR_COMPLETION_COUNT = 34
EXPECTED_NEW_FORMAL_RECORD_COUNT = 7
EXPECTED_COMBINED_COMPLETION_COUNT = 41
EXPECTED_REMAINING_PATH_COUNT = 161
EXPECTED_SHARED_PATH_COUNT = 9
EXPECTED_REMAINING_SHARED_PATH_COUNT = 1

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

RESOLUTION_DOMAIN = CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_RESOLUTION_V2_DOMAIN
ENVELOPE_DOMAIN = CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_ENVELOPE_V2_DOMAIN
REPLAY_DOMAIN = CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_REPLAY_V2_DOMAIN
LOCAL_DOMAINS = frozenset({RESOLUTION_DOMAIN, ENVELOPE_DOMAIN, REPLAY_DOMAIN})
if len(LOCAL_DOMAINS) != 3 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("abstract accounted shared domains are not central")

AGGREGATE_STAGES = (
    registry_v6.ConstructionStageKindV6.PREOPEN_COMMON_PREFIX,
    registry_v6.ConstructionStageKindV6.FAILED_ABSTRACT_PREFIX,
    registry_v6.ConstructionStageKindV6.CLOSED_RECONCILIATION_AND_TERMINALIZATION,
)
PREVIOUSLY_AUTHORIZED_SHARED_PATH = "process.launches"
NEW_FORMAL_SHARED_PATHS = tuple(
    path for path in FORMAL_SHARED_PATHS if path != PREVIOUSLY_AUTHORIZED_SHARED_PATH
)

MEASUREMENT_METHODS = {
    "common.hash_invocations": "GLOBAL_RECURSION_SAFE_SHA256_CONSTRUCTOR_METER",
    "common.integrity_checks": "NAMED_INTEGRITY_OBLIGATION_TRANSCRIPT",
    "common.protocol_checks": "NAMED_PROTOCOL_OBLIGATION_TRANSCRIPT",
    "io.mounted_bytes_peak": "IMMUTABLE_RUNTIME_AND_SANDBOX_PAYLOAD_PEAK",
    "io.read_bytes": "SEALED_RUNTIME_AND_TRANSFER_VERIFIED_UPPER_BOUND",
    "io.staged_bytes": "PRIVATE_RUNTIME_LEASE_AND_REQUEST_EXACT_BYTES",
    "memory.working_bytes_peak": "PARENT_WAIT4_RUSAGE_PEAK",
    "process.launches": "SINGLE_FRESH_PROCESS_SUPERVISOR_OBSERVATION",
}
VALUE_KINDS = {
    path: (
        "VERIFIED_UPPER_BOUND" if path == "io.read_bytes" else "EXACT"
    )
    for path in FORMAL_SHARED_PATHS
}

_RESOLUTION_ISSUER = object()
_ENVELOPE_ISSUER = object()


class ConstructionK7AbstractAccountedSharedAuthorityV2Error(ValueError):
    """The predecessor, V2 measurement, V6 leaf, or document changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractAccountedSharedAuthorityV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractAccountedSharedAuthorityV2Error(
            f"{label} must be one exact content ID"
        ) from error


def _same(left: Any, right: Any, label: str) -> None:
    try:
        matched = canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractAccountedSharedAuthorityV2Error(
            f"{label} is not canonical"
        ) from error
    if not matched:
        _fail(f"{label} crossed its exact root")


@dataclass(frozen=True, slots=True)
class AbstractAccountedSharedResolutionV2:
    _issuer: InitVar[object]
    measurement_id: str
    lifecycle_envelope_id: str
    query_owner_envelope_id: str
    retained_inventory_id: str
    predecessor_claim_id: str
    predecessor_blocker_id: str
    path: str
    value: int
    reducer: ReducerEnum
    measurement_method: str
    value_kind: str
    aggregate_stage_kinds: tuple[registry_v6.ConstructionStageKindV6, ...]
    _resolution_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESOLUTION_ISSUER:
            _fail("abstract accounted shared resolution is caller-minted")
        for value, label in (
            (self.measurement_id, "measurement"),
            (self.lifecycle_envelope_id, "lifecycle envelope"),
            (self.query_owner_envelope_id, "query-owner envelope"),
            (self.retained_inventory_id, "retained inventory"),
            (self.predecessor_claim_id, "predecessor claim"),
            (self.predecessor_blocker_id, "predecessor blocker"),
        ):
            _cid(value, label)
        try:
            reducer = ReducerEnum(self.reducer)
            stages = tuple(
                registry_v6.ConstructionStageKindV6(value)
                for value in self.aggregate_stage_kinds
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractAccountedSharedAuthorityV2Error(
                "shared resolution enum changed"
            ) from error
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(self, "aggregate_stage_kinds", stages)
        registry = registry_v6.official_counter_registry_v6()
        if (
            self.path not in NEW_FORMAL_SHARED_PATHS
            or type(self.value) is not int
            or self.value <= 0
            or reducer is not registry.by_path[self.path].reducer
            or self.measurement_method != MEASUREMENT_METHODS[self.path]
            or self.value_kind != VALUE_KINDS[self.path]
            or stages != AGGREGATE_STAGES
        ):
            _fail("shared resolution differs from its frozen measurement method")
        object.__setattr__(
            self,
            "_resolution_id",
            content_id(RESOLUTION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_accounted_shared_resolution.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "measurement_id": self.measurement_id,
            "lifecycle_envelope_id": self.lifecycle_envelope_id,
            "query_owner_envelope_id": self.query_owner_envelope_id,
            "retained_inventory_id": self.retained_inventory_id,
            "predecessor_claim_id": self.predecessor_claim_id,
            "predecessor_blocker_id": self.predecessor_blocker_id,
            "path": self.path,
            "value": self.value,
            "reducer": self.reducer.value,
            "measurement_method": self.measurement_method,
            "value_kind": self.value_kind,
            "aggregate_stage_kinds": [stage.value for stage in self.aggregate_stage_kinds],
            "occurrence_total_only": True,
            "per_stage_numeric_split_claimed": False,
            "measurement_window_start_observed": True,
            "complete_through_operational_cutoff": True,
            "aggregate_stage_reachability_replayed": True,
            "source_v1_record_relabelled_as_v6": False,
            "numeric_projection_authorized": True,
        }

    @property
    def resolution_id(self) -> str:
        expected = content_id(RESOLUTION_DOMAIN, self._payload())
        if expected != self._resolution_id:
            _fail("shared resolution changed after issuance")
        return self._resolution_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "abstract_accounted_shared_resolution_id": self.resolution_id,
        }


@dataclass(frozen=True, slots=True)
class AbstractAccountedSharedEnvelopeV2:
    _issuer: InitVar[object]
    source_lease_id: str
    operational_execution_id: str
    result_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    route_decision_context_id: str
    coverage_report_id: str
    zero_closure_id: str
    retained_inventory_id: str
    query_owner_envelope_id: str
    lifecycle_envelope_id: str
    lifecycle_process_launch_record_id: str
    runtime_preparation_id: str
    measurement_id: str
    resolutions: tuple[AbstractAccountedSharedResolutionV2, ...]
    counter_records: tuple[CounterRecordV1, ...]
    _envelope_id: str = field(init=False, repr=False)
    _canonical_bytes: bytes = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ENVELOPE_ISSUER:
            _fail("abstract accounted shared envelope is caller-minted")
        for value, label in (
            (self.source_lease_id, "source lease"),
            (self.operational_execution_id, "operational execution"),
            (self.result_id, "result"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.route_decision_context_id, "route context"),
            (self.coverage_report_id, "coverage report"),
            (self.zero_closure_id, "zero closure"),
            (self.retained_inventory_id, "retained inventory"),
            (self.query_owner_envelope_id, "query-owner envelope"),
            (self.lifecycle_envelope_id, "lifecycle envelope"),
            (self.lifecycle_process_launch_record_id, "lifecycle process-launch record"),
            (self.runtime_preparation_id, "runtime preparation"),
            (self.measurement_id, "measurement"),
        ):
            _cid(value, label)
        if (
            type(self.resolutions) is not tuple
            or len(self.resolutions) != EXPECTED_NEW_FORMAL_RECORD_COUNT
            or tuple(row.path for row in self.resolutions) != NEW_FORMAL_SHARED_PATHS
            or type(self.counter_records) is not tuple
            or len(self.counter_records) != EXPECTED_NEW_FORMAL_RECORD_COUNT
            or tuple(row.path for row in self.counter_records) != NEW_FORMAL_SHARED_PATHS
        ):
            _fail("abstract accounted shared envelope cardinality changed")
        registry = registry_v6.official_counter_registry_v6()
        for resolution, record in zip(
            self.resolutions, self.counter_records, strict=True
        ):
            if (
                resolution.measurement_id != self.measurement_id
                or resolution.lifecycle_envelope_id != self.lifecycle_envelope_id
                or resolution.query_owner_envelope_id != self.query_owner_envelope_id
                or resolution.retained_inventory_id != self.retained_inventory_id
                or record.recorder_id != resolution.resolution_id
                or record.value != resolution.value
                or record.counter_registry_id != registry.registry_id
            ):
                _fail("shared resolution/record roots crossed")
            record.verify_against(registry.by_path[record.path])
        object.__setattr__(self, "_envelope_id", content_id(ENVELOPE_DOMAIN, self._payload()))
        object.__setattr__(self, "_canonical_bytes", canonical_json_bytes(self.to_document()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_accounted_shared_envelope.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_code_assessed": TerminalCode.ABSTRACT_CERTIFIED.value,
            "source_lease_id": self.source_lease_id,
            "operational_execution_id": self.operational_execution_id,
            "result_id": self.result_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "route_decision_context_id": self.route_decision_context_id,
            "coverage_report_id": self.coverage_report_id,
            "zero_closure_id": self.zero_closure_id,
            "retained_inventory_id": self.retained_inventory_id,
            "query_owner_envelope_id": self.query_owner_envelope_id,
            "lifecycle_envelope_id": self.lifecycle_envelope_id,
            "lifecycle_process_launch_record_id": (
                self.lifecycle_process_launch_record_id
            ),
            "runtime_preparation_id": self.runtime_preparation_id,
            "measurement_id": self.measurement_id,
            "resolutions": [row.to_document() for row in self.resolutions],
            "formal_v6_counter_records": [
                row.to_dict() for row in self.counter_records
            ],
            "required_path_count": EXPECTED_REQUIRED_PATH_COUNT,
            "retained_prior_completion_progress_count": EXPECTED_PRIOR_COMPLETION_COUNT,
            "new_formal_v6_counter_record_count": EXPECTED_NEW_FORMAL_RECORD_COUNT,
            "combined_completion_progress_count": EXPECTED_COMBINED_COMPLETION_COUNT,
            "remaining_required_path_authority_count": EXPECTED_REMAINING_PATH_COUNT,
            "shared_resource_path_count": EXPECTED_SHARED_PATH_COUNT,
            "shared_resource_path_count_closed_before_here": 1,
            "shared_resource_path_count_closed_here": EXPECTED_NEW_FORMAL_RECORD_COUNT,
            "remaining_shared_resource_path_count": EXPECTED_REMAINING_SHARED_PATH_COUNT,
            "pending_shared_resource_path": PENDING_SHARED_PATH,
            "all_nine_shared_resource_receipts_complete": False,
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
        expected = content_id(ENVELOPE_DOMAIN, self._payload())
        if expected != self._envelope_id:
            _fail("abstract accounted shared envelope changed after issuance")
        return self._envelope_id

    @property
    def canonical_bytes(self) -> bytes:
        current = canonical_json_bytes(self.to_document())
        if current != self._canonical_bytes:
            _fail("abstract accounted shared bytes changed after issuance")
        return self._canonical_bytes

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "abstract_accounted_shared_envelope_id": self.envelope_id,
        }


def _exact_roots(
    source: ModelOnlyRAPMSourceV1,
    accounted_execution: AccountedModelOnlyExecutionV2,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_envelope: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
) -> tuple[
    AccountedModelOnlyExecutionV2,
    coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
]:
    require_model_only_source_authority_v1(source)
    accounted = require_accounted_model_only_execution_v2(accounted_execution)
    execution = accounted.execution
    request = model_only_execution_request_v1(
        source,
        regret_tolerance=execution.model_only_result.audit.regret_tolerance,
    )
    if request.request_id != execution.request_id:
        _fail("source authority belongs to another accounted execution")
    report = coverage_v1.audit_abstract_certified_accounting_coverage_v1(execution)
    _same(report.to_document(), coverage_report.to_document(), "coverage report")
    zeros = zero_v1.close_abstract_certified_zero_value_subset_v1(execution, report)
    _same(zeros.to_document(), zero_closure.to_document(), "zero closure")
    inventory = retained_v1.inventory_abstract_pass_retained_v1_accounting_v1(
        execution, report, zeros
    )
    _same(inventory.to_document(), retained_inventory.to_document(), "retained inventory")
    owner = owner_v1.issue_abstract_certified_query_owner_authority_v1(
        execution, report, zeros, inventory
    )
    _same(owner.to_document(), query_owner_envelope.to_document(), "query-owner envelope")
    lifecycle = (
        lifecycle_v1
        .issue_abstract_certified_lifecycle_reconciliation_authority_v1(
            source,
            execution,
            report,
            zeros,
            inventory,
            owner,
        )
    )
    _same(
        lifecycle.to_document(),
        lifecycle_envelope.to_document(),
        "lifecycle envelope",
    )
    return accounted, report, zeros, inventory, owner, lifecycle


def _build_from_exact_roots(
    source: ModelOnlyRAPMSourceV1,
    accounted: AccountedModelOnlyExecutionV2,
    report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zeros: zero_v1.AbstractCertifiedZeroValueClosureV1,
    inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    owner: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
) -> AbstractAccountedSharedEnvelopeV2:
    execution = accounted.execution
    result = execution.model_only_result
    measurement = accounted.measurement
    if (
        result.outcome.value != "PASS"
        or result.ground_binding_required
        or measurement.operational_execution_id != execution.operational_execution_id
        or measurement.result_id != result.result_id
        or measurement.route_attempt_id != result.route_attempt.route_attempt_id
        or measurement.route_decision_context_id
        != result.route_context.route_decision_context_id
    ):
        _fail("accounted measurement belongs to another abstract PASS")

    claims = {row.path: row for row in inventory.shared_claims}
    blockers = {row.path: row for row in inventory.formal_blockers}
    if set(claims) != set(FORMAL_SHARED_PATHS) | {PENDING_SHARED_PATH}:
        _fail("retained shared predecessor inventory changed")
    registry = registry_v6.official_counter_registry_v6()
    lifecycle_records = {row.path: row for row in lifecycle.counter_records}
    lifecycle_process = lifecycle_records.get(PREVIOUSLY_AUTHORIZED_SHARED_PATH)
    if (
        set(lifecycle_records) != set(lifecycle_v1.LIFECYCLE_PATHS)
        or lifecycle_process is None
        or lifecycle_process.value
        != measurement.values[PREVIOUSLY_AUTHORIZED_SHARED_PATH]
        or lifecycle_process.value != 1
    ):
        _fail("accounted process launch differs from lifecycle authority")
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    rules = tuple(stage_profile.by_stage[stage] for stage in AGGREGATE_STAGES)
    values = measurement.values
    resolutions: list[AbstractAccountedSharedResolutionV2] = []
    records: list[CounterRecordV1] = []
    for path in NEW_FORMAL_SHARED_PATHS:
        claim = claims[path]
        blocker = blockers[path]
        if (
            blocker.path != path
            or blocker.source_evidence_id != claim.claim_id
            or any(path not in rule.allowed_nonzero_paths for rule in rules)
            or values[path] <= 0
        ):
            _fail(f"shared predecessor or stage changed for {path}")
        resolution = AbstractAccountedSharedResolutionV2(
            _RESOLUTION_ISSUER,
            measurement.measurement_id,
            lifecycle.envelope_id,
            owner.envelope_id,
            inventory.inventory_id,
            claim.claim_id,
            blocker.blocker_id,
            path,
            values[path],
            registry.by_path[path].reducer,
            MEASUREMENT_METHODS[path],
            VALUE_KINDS[path],
            AGGREGATE_STAGES,
        )
        resolutions.append(resolution)
        records.append(
            CounterRecordV1.observe(
                registry,
                path,
                values[path],
                recorder_id=resolution.resolution_id,
            )
        )
    return AbstractAccountedSharedEnvelopeV2(
        _ENVELOPE_ISSUER,
        source.lease.source_lease_id,
        execution.operational_execution_id,
        result.result_id,
        result.logical_occurrence.logical_occurrence_id,
        result.route_attempt.route_attempt_id,
        result.route_context.route_decision_context_id,
        report.source_archive_id,
        zeros.closure_id,
        inventory.inventory_id,
        owner.envelope_id,
        lifecycle.envelope_id,
        lifecycle_process.record_id,
        accounted.preparation.preparation_id,
        measurement.measurement_id,
        tuple(resolutions),
        tuple(records),
    )


def issue_abstract_accounted_shared_authority_v2(
    source: ModelOnlyRAPMSourceV1,
    accounted_execution: AccountedModelOnlyExecutionV2,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_envelope: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
) -> AbstractAccountedSharedEnvelopeV2:
    roots = _exact_roots(
        source,
        accounted_execution,
        coverage_report,
        zero_closure,
        retained_inventory,
        query_owner_envelope,
        lifecycle_envelope,
    )
    return _build_from_exact_roots(source, *roots)


class AccountedSharedReplayOutcomeV2(str, Enum):
    VERIFIED = "VERIFIED"
    DOCUMENT_BLOCKED = "DOCUMENT_BLOCKED"
    SOURCE_BLOCKED = "SOURCE_BLOCKED"


@dataclass(frozen=True, slots=True)
class AbstractAccountedSharedReplayV2:
    outcome: AccountedSharedReplayOutcomeV2
    envelope: AbstractAccountedSharedEnvelopeV2 | None
    blocker_codes: tuple[str, ...]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_accounted_shared_replay.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "outcome": self.outcome.value,
            "abstract_accounted_shared_envelope_id": (
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
        return {**self._payload(), "abstract_accounted_shared_replay_id": self.replay_id}


def verify_abstract_accounted_shared_authority_bytes_v2(
    raw: bytes,
    source: ModelOnlyRAPMSourceV1,
    accounted_execution: AccountedModelOnlyExecutionV2,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_envelope: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
) -> AbstractAccountedSharedReplayV2:
    try:
        expected = issue_abstract_accounted_shared_authority_v2(
            source,
            accounted_execution,
            coverage_report,
            zero_closure,
            retained_inventory,
            query_owner_envelope,
            lifecycle_envelope,
        )
    except (TypeError, ValueError):
        return AbstractAccountedSharedReplayV2(
            AccountedSharedReplayOutcomeV2.SOURCE_BLOCKED,
            None,
            ("EXACT_ACCOUNTED_SOURCE_REPLAY_FAILED",),
        )
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError):
        return AbstractAccountedSharedReplayV2(
            AccountedSharedReplayOutcomeV2.DOCUMENT_BLOCKED,
            None,
            ("NONCANONICAL_ACCOUNTED_SHARED_DOCUMENT",),
        )
    if type(document) is not dict or raw != expected.canonical_bytes:
        return AbstractAccountedSharedReplayV2(
            AccountedSharedReplayOutcomeV2.DOCUMENT_BLOCKED,
            None,
            ("ACCOUNTED_SHARED_DOCUMENT_DIFFERS_FROM_EXACT_REPLAY",),
        )
    return AbstractAccountedSharedReplayV2(
        AccountedSharedReplayOutcomeV2.VERIFIED,
        expected,
        (),
    )


__all__ = (
    "AbstractAccountedSharedEnvelopeV2",
    "AbstractAccountedSharedReplayV2",
    "AbstractAccountedSharedResolutionV2",
    "AccountedSharedReplayOutcomeV2",
    "ConstructionK7AbstractAccountedSharedAuthorityV2Error",
    "FORMAL_SHARED_PATHS",
    "AGGREGATE_STAGES",
    "NEW_FORMAL_SHARED_PATHS",
    "issue_abstract_accounted_shared_authority_v2",
    "verify_abstract_accounted_shared_authority_bytes_v2",
)
