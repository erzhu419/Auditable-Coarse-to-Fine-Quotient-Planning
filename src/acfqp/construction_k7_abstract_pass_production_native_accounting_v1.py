"""Retained-V1 evidence inventory for one real model-only abstract PASS.

Contract 2.0.43 inventories what survives a real
``execute_model_only_abstract_pass_v1`` execution.  It is deliberately not a
production-native accounting closure:

* eight shared-resource values are legacy aggregate claims whose source bytes
  can be replayed, but whose operation hooks, measurement-window start,
  stage assignment, and operational cutoff were not observed;
* mounted payload is explicitly unavailable rather than inferred to be zero;
* the two abstract planner/auditor streams are legacy event candidates without
  production hook-semantics/stage/cutoff authority;
* the eight process/route/solver rows are legacy internal reconciliation
  claims without formal V6 dependency records; and
* the 23 Contract-2.0.41 value proofs remain value proofs, never formal
  profile-native-zero attestations.

Every one of the 202 V6 required paths therefore retains one exact formal
blocker.  This module issues no V6 CounterRecord, WorkVector,
ComparisonVector, cap outcome, terminal, certificate, or campaign closure.
All official Gates stay locked.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from functools import lru_cache
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage_v1
from acfqp import construction_k7_abstract_certified_native_zero_closure_v1 as zero_v1
from acfqp import construction_k7_all_path_accounting_profile_v1 as all_path_v1
from acfqp import construction_k7_derived_reconciliation_v1 as derived_v1
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp.phase3e_abstract_pass_closure_v1 import (
    verify_model_only_operational_execution_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_OWNER_EVENT_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_RECONCILIATION_CLAIM_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_SHARED_AGGREGATE_CLAIM_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_EVIDENCE_INVENTORY_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_FORMAL_BLOCKER_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_INVENTORY_CONTEXT_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_INVENTORY_REPLAY_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    parse_content_id,
)
from acfqp.phase3e_model_only_executor_v1 import ModelOnlyQueryExecutionV1
from acfqp.phase3e_model_only_v1 import ModelOnlyOutcome
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.43"
PROFILE_KEY = "construction_k7_abstract_pass_retained_v1_evidence_inventory_v1"

EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_LEGACY_SHARED_AGGREGATE_COUNT = 8
EXPECTED_UNAVAILABLE_SHARED_COUNT = 1
EXPECTED_LEGACY_OWNER_CANDIDATE_COUNT = 2
EXPECTED_LEGACY_RECONCILIATION_CLAIM_COUNT = 8
EXPECTED_FORMAL_BLOCKER_COUNT = 202
EXPECTED_EXTERNAL_GAP_PARTITION_COUNT = 192
EXPECTED_LEGACY_CANDIDATE_BLOCKER_COUNT = 10

EXPECTED_NO_V1_BLOCKER_COUNT = 160
EXPECTED_ZERO_VALUE_BLOCKER_COUNT = 23
EXPECTED_SHARED_AGGREGATE_BLOCKER_COUNT = 8
EXPECTED_MOUNTED_BLOCKER_COUNT = 1
EXPECTED_OWNER_CANDIDATE_BLOCKER_COUNT = 2
EXPECTED_RECONCILIATION_BLOCKER_COUNT = 8

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

CONTEXT_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_INVENTORY_CONTEXT_V1_DOMAIN
)
SHARED_CLAIM_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_SHARED_AGGREGATE_CLAIM_V1_DOMAIN
)
OWNER_CANDIDATE_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_OWNER_EVENT_CANDIDATE_V1_DOMAIN
)
RECONCILIATION_CLAIM_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_RECONCILIATION_CLAIM_V1_DOMAIN
)
BLOCKER_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_FORMAL_BLOCKER_V1_DOMAIN
)
INVENTORY_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_EVIDENCE_INVENTORY_V1_DOMAIN
)
REPLAY_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_INVENTORY_REPLAY_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset(
    {
        CONTEXT_DOMAIN,
        SHARED_CLAIM_DOMAIN,
        OWNER_CANDIDATE_DOMAIN,
        RECONCILIATION_CLAIM_DOMAIN,
        BLOCKER_DOMAIN,
        INVENTORY_DOMAIN,
        REPLAY_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 7 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("retained-V1 inventory domains are not central and unique")

_CONTEXT_ISSUER = object()
_SHARED_ISSUER = object()
_OWNER_ISSUER = object()
_RECONCILIATION_ISSUER = object()
_INVENTORY_ISSUER = object()

_INVENTORY_BYTES_MEMO: dict[tuple[str, str, str], bytes] = {}
_INVENTORY_BYTES_MEMO_MAX = 32

_LEGACY_OWNER_PATHS = (
    "common.abstract_audit_obligations",
    "common.abstract_bellman_backups",
)
_LEGACY_SHARED_PATHS = tuple(
    path for path in shared_v1.SHARED_RESOURCE_PATHS
    if path != "io.mounted_bytes_peak"
)
_DERIVED_PATHS = derived_v1.DERIVED_PATHS


class ConstructionK7AbstractPassRetainedV1InventoryError(ValueError):
    """The retained PASS or one inventory identity/value was crossed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractPassRetainedV1InventoryError(message)


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("retained-V1 inventory used an unknown local domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractPassRetainedV1InventoryError(
            f"{label} must be one exact content ID"
        ) from error


@lru_cache(maxsize=1)
def _v6_leaf_blueprint() -> tuple[tuple[str, str, str, str], ...]:
    """Cache primitive leaf metadata, never a registry authority object."""

    registry = registry_v6.official_counter_registry_v6()
    return tuple(
        (
            path,
            registry.by_path[path].semantics_id,
            registry.by_path[path].owner,
            registry.by_path[path].scope,
        )
        for path in registry.required_paths
    )


def _leaf_metadata(path: str) -> tuple[str, str, str]:
    try:
        _path, semantics_id, owner, scope = next(
            row for row in _v6_leaf_blueprint() if row[0] == path
        )
    except StopIteration as error:
        raise ConstructionK7AbstractPassRetainedV1InventoryError(
            f"unknown required V6 path {path!r}"
        ) from error
    return semantics_id, owner, scope


@lru_cache(maxsize=1)
def _formula_blueprint() -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    return tuple(
        (row.path, row.formula_id, row.closure_dependency_paths)
        for row in derived_v1.official_k7_reconciliation_formulas_v1()
    )


class LegacyClaimStatusV1(str, Enum):
    LEGACY_AGGREGATE_NOT_VERIFIED = "LEGACY_AGGREGATE_NOT_VERIFIED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class FormalBlockerCodeV1(str, Enum):
    NO_V1_COUNTER_OR_EVENT = "NO_V1_COUNTER_OR_EVENT"
    ZERO_VALUE_IS_NOT_PROFILE_NATIVE_ZERO = "ZERO_VALUE_IS_NOT_PROFILE_NATIVE_ZERO"
    LEGACY_SHARED_AGGREGATE_LACKS_WINDOW_STAGE_CUTOFF_REPLAY = (
        "LEGACY_SHARED_AGGREGATE_LACKS_WINDOW_STAGE_CUTOFF_REPLAY"
    )
    MOUNTED_PAYLOAD_NOT_MEASURED_FROM_WINDOW_START = (
        "MOUNTED_PAYLOAD_NOT_MEASURED_FROM_WINDOW_START"
    )
    LEGACY_OWNER_EVENT_LACKS_HOOK_STAGE_CUTOFF_REPLAY = (
        "LEGACY_OWNER_EVENT_LACKS_HOOK_STAGE_CUTOFF_REPLAY"
    )
    LEGACY_INTERNAL_RECONCILIATION_LACKS_FORMAL_DEPENDENCIES = (
        "LEGACY_INTERNAL_RECONCILIATION_LACKS_FORMAL_DEPENDENCIES"
    )


class ReplayOutcomeV1(str, Enum):
    RETAINED_V1_INVENTORY_VERIFIED_FORMAL_ACCOUNTING_BLOCKED = (
        "RETAINED_V1_INVENTORY_VERIFIED_FORMAL_ACCOUNTING_BLOCKED"
    )
    DOCUMENT_BLOCKED = "DOCUMENT_BLOCKED"


@dataclass(frozen=True, slots=True)
class AbstractPassRetainedV1InventoryContextV1:
    _issuer: InitVar[object]
    coverage_report_id: str
    zero_value_closure_id: str
    operational_execution_id: str
    request_id: str
    worker_output_id: str
    model_only_result_id: str
    event_trace_id: str
    legacy_work_vector_id: str
    legacy_reconciliation_proof_id: str
    v6_counter_registry_id: str
    v6_stage_profile_id: str
    all_path_accounting_profile_id: str
    operation_boundary_manifest_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    _context_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CONTEXT_ISSUER:
            _fail("retained-V1 inventory context is caller-minted")
        for name in (
            "coverage_report_id",
            "zero_value_closure_id",
            "operational_execution_id",
            "request_id",
            "worker_output_id",
            "model_only_result_id",
            "event_trace_id",
            "legacy_work_vector_id",
            "legacy_reconciliation_proof_id",
            "v6_counter_registry_id",
            "v6_stage_profile_id",
            "all_path_accounting_profile_id",
            "operation_boundary_manifest_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
        ):
            _cid(getattr(self, name), name)
        object.__setattr__(self, "_context_id", _local_id(CONTEXT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_pass_retained_v1_inventory_context.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                name: getattr(self, name)
                for name in (
                    "coverage_report_id",
                    "zero_value_closure_id",
                    "operational_execution_id",
                    "request_id",
                    "worker_output_id",
                    "model_only_result_id",
                    "event_trace_id",
                    "legacy_work_vector_id",
                    "legacy_reconciliation_proof_id",
                    "v6_counter_registry_id",
                    "v6_stage_profile_id",
                    "all_path_accounting_profile_id",
                    "operation_boundary_manifest_id",
                    "logical_occurrence_id",
                    "route_attempt_id",
                    "decision_point_id",
                )
            },
            "production_occurrence_authority_id": None,
            "production_stage_assignment_id": None,
            "production_measurement_window_id": None,
            "production_operational_cutoff_id": None,
            "legacy_identity_values_retained_only": True,
            "production_identity_stage_cutoff_authority_complete": False,
            "legacy_v1_records_relabelled_as_v6": False,
            "ground_access_performed": False,
        }

    @property
    def context_id(self) -> str:
        current = _local_id(CONTEXT_DOMAIN, self._payload())
        if current != self._context_id:
            _fail("retained-V1 inventory context changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "retained_v1_inventory_context_id": self.context_id}


@dataclass(frozen=True, slots=True)
class LegacySharedAggregateClaimV1:
    _issuer: InitVar[object]
    context_id: str
    path: str
    status: LegacyClaimStatusV1
    legacy_v1_record_id: str
    legacy_placeholder_value: int
    reported_value: int | None
    source_artifact_id: str | None
    source_bytes_sha256: str | None
    _claim_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SHARED_ISSUER:
            _fail("legacy shared aggregate claim is caller-minted")
        _cid(self.context_id, "retained-V1 inventory context")
        _cid(self.legacy_v1_record_id, "legacy V1 record")
        try:
            status = LegacyClaimStatusV1(self.status)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractPassRetainedV1InventoryError(
                "legacy shared claim status is invalid"
            ) from error
        object.__setattr__(self, "status", status)
        if type(self.legacy_placeholder_value) is not int or self.legacy_placeholder_value < 0:
            _fail("legacy shared placeholder value is invalid")
        if status is LegacyClaimStatusV1.LEGACY_AGGREGATE_NOT_VERIFIED:
            if (
                self.path not in _LEGACY_SHARED_PATHS
                or type(self.reported_value) is not int
                or self.reported_value <= 0
                or self.reported_value != self.legacy_placeholder_value
                or self.source_artifact_id is None
                or self.source_bytes_sha256 is None
            ):
                _fail("legacy shared aggregate claim is incomplete")
            _cid(self.source_artifact_id, "legacy aggregate source artifact")
            _cid(self.source_bytes_sha256, "legacy aggregate source digest")
        elif (
            self.path != "io.mounted_bytes_peak"
            or self.legacy_placeholder_value != 0
            or self.reported_value is not None
            or self.source_artifact_id is not None
            or self.source_bytes_sha256 is not None
        ):
            _fail("mounted-payload unavailability was converted into a value")
        object.__setattr__(self, "_claim_id", _local_id(SHARED_CLAIM_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_pass_legacy_shared_aggregate_claim.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "path": self.path,
            "status": self.status.value,
            "legacy_v1_record_id": self.legacy_v1_record_id,
            "legacy_placeholder_value": self.legacy_placeholder_value,
            "reported_value": self.reported_value,
            "source_artifact_id": self.source_artifact_id,
            "source_bytes_sha256": self.source_bytes_sha256,
            "measurement_window_start_observed": False,
            "complete_through_operational_cutoff": False,
            "stage_assignment_replayed": False,
            "source_semantics_verified": False,
            "numeric_projection_authorized": False,
            "v6_counter_record_issued": False,
        }

    @property
    def claim_id(self) -> str:
        current = _local_id(SHARED_CLAIM_DOMAIN, self._payload())
        if current != self._claim_id:
            _fail("legacy shared aggregate claim changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "legacy_shared_aggregate_claim_id": self.claim_id}


@dataclass(frozen=True, slots=True)
class LegacyOwnerEventCandidateV1:
    _issuer: InitVar[object]
    context_id: str
    path: str
    semantics_id: str
    owner: str
    scope: str
    legacy_v1_record_id: str
    legacy_event_trace_id: str
    legacy_event_trace_sha256: str
    candidate_value: int
    event_rows: tuple[tuple[int, int], ...]
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _OWNER_ISSUER:
            _fail("legacy owner-event candidate is caller-minted")
        for value, label in (
            (self.context_id, "retained-V1 inventory context"),
            (self.legacy_v1_record_id, "legacy V1 record"),
            (self.legacy_event_trace_id, "legacy event trace"),
            (self.legacy_event_trace_sha256, "legacy event trace digest"),
        ):
            _cid(value, label)
        semantics_id, owner, scope = _leaf_metadata(self.path)
        if (
            self.path not in _LEGACY_OWNER_PATHS
            or self.semantics_id != semantics_id
            or self.owner != owner
            or self.scope != scope
            or type(self.candidate_value) is not int
            or self.candidate_value <= 0
            or type(self.event_rows) is not tuple
            or not self.event_rows
            or tuple(sequence for sequence, _amount in self.event_rows)
            != tuple(sorted(sequence for sequence, _amount in self.event_rows))
            or len({sequence for sequence, _amount in self.event_rows}) != len(self.event_rows)
            or any(
                type(sequence) is not int or sequence <= 0
                or type(amount) is not int or amount <= 0
                for sequence, amount in self.event_rows
            )
            or sum(amount for _sequence, amount in self.event_rows) != self.candidate_value
        ):
            _fail("legacy owner-event candidate differs from retained trace metadata")
        object.__setattr__(self, "_candidate_id", _local_id(OWNER_CANDIDATE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_pass_legacy_owner_event_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "path": self.path,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "scope": self.scope,
            "legacy_v1_record_id": self.legacy_v1_record_id,
            "legacy_event_trace_id": self.legacy_event_trace_id,
            "legacy_event_trace_sha256": self.legacy_event_trace_sha256,
            "candidate_value": self.candidate_value,
            "ordered_legacy_events": [
                {"sequence": sequence, "amount": amount}
                for sequence, amount in self.event_rows
            ],
            "production_hook_semantics_replayed": False,
            "production_stage_assignment_replayed": False,
            "production_occurrence_cutoff_replayed": False,
            "formal_owner_event_authority": False,
            "source_v1_record_relabelled_as_v6": False,
            "v6_counter_record_issued": False,
        }

    @property
    def candidate_id(self) -> str:
        current = _local_id(OWNER_CANDIDATE_DOMAIN, self._payload())
        if current != self._candidate_id:
            _fail("legacy owner-event candidate changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "legacy_owner_event_candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class LegacyInternalReconciliationClaimV1:
    _issuer: InitVar[object]
    context_id: str
    path: str
    claimed_value: int
    formula_id: str
    dependency_paths: tuple[str, ...]
    legacy_path_record_id: str
    supporting_record_ids: tuple[str, ...]
    legacy_reconciliation_proof_id: str
    legacy_reconciliation_proof_sha256: str
    _claim_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RECONCILIATION_ISSUER:
            _fail("legacy internal reconciliation claim is caller-minted")
        for value, label in (
            (self.context_id, "retained-V1 inventory context"),
            (self.formula_id, "frozen formula"),
            (self.legacy_path_record_id, "legacy path record"),
            (self.legacy_reconciliation_proof_id, "legacy reconciliation proof"),
            (self.legacy_reconciliation_proof_sha256, "legacy reconciliation proof digest"),
            *((value, "supporting legacy record") for value in self.supporting_record_ids),
        ):
            _cid(value, label)
        formulas = {
            path: (formula_id, dependencies)
            for path, formula_id, dependencies in _formula_blueprint()
        }
        formula = formulas.get(self.path)
        if (
            formula is None
            or self.path not in _DERIVED_PATHS
            or self.formula_id != formula[0]
            or self.dependency_paths != formula[1]
            or type(self.claimed_value) is not int
            or self.claimed_value < 0
            or type(self.supporting_record_ids) is not tuple
            or tuple(sorted(self.supporting_record_ids)) != self.supporting_record_ids
            or not self.supporting_record_ids
            or len(set(self.supporting_record_ids)) != len(self.supporting_record_ids)
        ):
            _fail("legacy reconciliation claim differs from retained V1 arithmetic")
        object.__setattr__(
            self, "_claim_id", _local_id(RECONCILIATION_CLAIM_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_pass_legacy_internal_reconciliation_claim.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "path": self.path,
            "claimed_value": self.claimed_value,
            "formula_id": self.formula_id,
            "dependency_paths": list(self.dependency_paths),
            "legacy_path_record_id": self.legacy_path_record_id,
            "supporting_legacy_record_ids": list(self.supporting_record_ids),
            "legacy_reconciliation_proof_id": self.legacy_reconciliation_proof_id,
            "legacy_reconciliation_proof_sha256": self.legacy_reconciliation_proof_sha256,
            "legacy_internal_arithmetic_replayed": True,
            "production_semantic_dependencies_replayed": False,
            "source_level_reconciliation_complete": False,
            "formal_v6_dependency_records_complete": False,
            "formal_reconciliation_authority": False,
            "source_v1_record_relabelled_as_v6": False,
            "v6_counter_record_issued": False,
        }

    @property
    def claim_id(self) -> str:
        current = _local_id(RECONCILIATION_CLAIM_DOMAIN, self._payload())
        if current != self._claim_id:
            _fail("legacy internal reconciliation claim changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "legacy_internal_reconciliation_claim_id": self.claim_id}


@dataclass(frozen=True, slots=True, order=True)
class AbstractPassRetainedV1FormalBlockerV1:
    context_id: str
    path: str
    code: FormalBlockerCodeV1
    source_evidence_id: str
    detail: str

    def __post_init__(self) -> None:
        _cid(self.context_id, "retained-V1 inventory context")
        _cid(self.source_evidence_id, "formal blocker source evidence")
        try:
            object.__setattr__(self, "code", FormalBlockerCodeV1(self.code))
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractPassRetainedV1InventoryError(
                "formal blocker code is invalid"
            ) from error
        if self.path not in {row[0] for row in _v6_leaf_blueprint()} or not self.detail:
            _fail("formal blocker path/detail is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_pass_retained_v1_formal_blocker.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "path": self.path,
            "blocker_code": self.code.value,
            "source_evidence_id": self.source_evidence_id,
            "detail": self.detail,
            "missing_inferred_zero": False,
            "counter_record_issued": False,
        }

    @property
    def blocker_id(self) -> str:
        return _local_id(BLOCKER_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "formal_blocker_id": self.blocker_id}


@dataclass(frozen=True, slots=True)
class AbstractPassRetainedV1EvidenceInventoryV1:
    _issuer: InitVar[object]
    context: AbstractPassRetainedV1InventoryContextV1
    shared_claims: tuple[LegacySharedAggregateClaimV1, ...]
    owner_candidates: tuple[LegacyOwnerEventCandidateV1, ...]
    reconciliation_claims: tuple[LegacyInternalReconciliationClaimV1, ...]
    retained_zero_value_proof_ids: tuple[str, ...]
    formal_blockers: tuple[AbstractPassRetainedV1FormalBlockerV1, ...]
    _inventory_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _INVENTORY_ISSUER
            or type(self.context) is not AbstractPassRetainedV1InventoryContextV1
            or any(type(row) is not LegacySharedAggregateClaimV1 for row in self.shared_claims)
            or any(type(row) is not LegacyOwnerEventCandidateV1 for row in self.owner_candidates)
            or any(
                type(row) is not LegacyInternalReconciliationClaimV1
                for row in self.reconciliation_claims
            )
            or any(type(row) is not AbstractPassRetainedV1FormalBlockerV1 for row in self.formal_blockers)
        ):
            _fail("retained-V1 evidence inventory is caller-minted")
        shared_paths = tuple(row.path for row in self.shared_claims)
        owner_paths = tuple(row.path for row in self.owner_candidates)
        reconciliation_paths = tuple(row.path for row in self.reconciliation_claims)
        blocker_paths = tuple(row.path for row in self.formal_blockers)
        if (
            shared_paths != shared_v1.SHARED_RESOURCE_PATHS
            or owner_paths != _LEGACY_OWNER_PATHS
            or reconciliation_paths != _DERIVED_PATHS
            or type(self.retained_zero_value_proof_ids) is not tuple
            or tuple(sorted(self.retained_zero_value_proof_ids)) != self.retained_zero_value_proof_ids
            or len(self.retained_zero_value_proof_ids) != EXPECTED_ZERO_VALUE_BLOCKER_COUNT
            or len(set(self.retained_zero_value_proof_ids)) != len(self.retained_zero_value_proof_ids)
            or blocker_paths != tuple(sorted(blocker_paths))
            or len(blocker_paths) != EXPECTED_FORMAL_BLOCKER_COUNT
            or len(set(blocker_paths)) != len(blocker_paths)
            or any(row.context_id != self.context.context_id for row in self.shared_claims)
            or any(row.context_id != self.context.context_id for row in self.owner_candidates)
            or any(row.context_id != self.context.context_id for row in self.reconciliation_claims)
            or any(row.context_id != self.context.context_id for row in self.formal_blockers)
        ):
            _fail("retained-V1 inventory cardinality/identity changed")
        counts = {code: 0 for code in FormalBlockerCodeV1}
        sets = {code: set() for code in FormalBlockerCodeV1}
        for row in self.formal_blockers:
            counts[row.code] += 1
            sets[row.code].add(row.path)
        expected_counts = {
            FormalBlockerCodeV1.NO_V1_COUNTER_OR_EVENT: EXPECTED_NO_V1_BLOCKER_COUNT,
            FormalBlockerCodeV1.ZERO_VALUE_IS_NOT_PROFILE_NATIVE_ZERO: EXPECTED_ZERO_VALUE_BLOCKER_COUNT,
            FormalBlockerCodeV1.LEGACY_SHARED_AGGREGATE_LACKS_WINDOW_STAGE_CUTOFF_REPLAY: EXPECTED_SHARED_AGGREGATE_BLOCKER_COUNT,
            FormalBlockerCodeV1.MOUNTED_PAYLOAD_NOT_MEASURED_FROM_WINDOW_START: EXPECTED_MOUNTED_BLOCKER_COUNT,
            FormalBlockerCodeV1.LEGACY_OWNER_EVENT_LACKS_HOOK_STAGE_CUTOFF_REPLAY: EXPECTED_OWNER_CANDIDATE_BLOCKER_COUNT,
            FormalBlockerCodeV1.LEGACY_INTERNAL_RECONCILIATION_LACKS_FORMAL_DEPENDENCIES: EXPECTED_RECONCILIATION_BLOCKER_COUNT,
        }
        official = {row[0] for row in _v6_leaf_blueprint()}
        if (
            counts != expected_counts
            or sum(len(paths) for paths in sets.values()) != len(set().union(*sets.values()))
            or set().union(*sets.values()) != official
        ):
            _fail("six blocker sets must be disjoint and union to official 202")
        object.__setattr__(self, "_inventory_id", _local_id(INVENTORY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_pass_retained_v1_evidence_inventory.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context": self.context.to_document(),
            "legacy_shared_resource_claims": [row.to_document() for row in self.shared_claims],
            "legacy_owner_event_candidates": [row.to_document() for row in self.owner_candidates],
            "legacy_internal_reconciliation_claims": [
                row.to_document() for row in self.reconciliation_claims
            ],
            "retained_zero_value_proof_ids": list(self.retained_zero_value_proof_ids),
            "formal_blockers": [row.to_document() for row in self.formal_blockers],
            "required_path_count": EXPECTED_REQUIRED_PATH_COUNT,
            "legacy_shared_aggregate_count": EXPECTED_LEGACY_SHARED_AGGREGATE_COUNT,
            "unavailable_shared_count": EXPECTED_UNAVAILABLE_SHARED_COUNT,
            "legacy_owner_candidate_count": EXPECTED_LEGACY_OWNER_CANDIDATE_COUNT,
            "legacy_internal_reconciliation_claim_count": EXPECTED_LEGACY_RECONCILIATION_CLAIM_COUNT,
            "formal_blocker_count": EXPECTED_FORMAL_BLOCKER_COUNT,
            "external_gap_partition_count": EXPECTED_EXTERNAL_GAP_PARTITION_COUNT,
            "legacy_candidate_formal_blocker_count": EXPECTED_LEGACY_CANDIDATE_BLOCKER_COUNT,
            "six_blocker_sets_pairwise_disjoint": True,
            "six_blocker_sets_union_official_202": True,
            "legacy_evidence_inventory_only": True,
            "production_native_accounting_closed": False,
            "shared_measurement_window_and_cutoff_complete": False,
            "owner_hook_stage_cutoff_replay_complete": False,
            "source_level_derived_reconciliation_complete": False,
            "formal_v6_reconciliation_complete": False,
            "retained_23_value_proofs_promoted_to_profile_native_zero": False,
            "legacy_v1_records_relabelled_as_v6": False,
            "missing_event_inferred_zero": False,
            "root_cap_materializer_invoked": False,
            "formal_materialization_allowed": False,
            "formal_v6_counter_records_issued": 0,
            "formal_v6_work_vector_id": None,
            "formal_v6_comparison_vector_id": None,
            "cap_outcome": None,
            "cap_authority_id": None,
            "terminal_candidate_code": TerminalCode.ABSTRACT_CERTIFIED.value,
            "terminal_artifact_id": None,
            "campaign_occurrence_closure_id": None,
            "certificate_issued": False,
            "ground_access_performed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_n_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "central_domain_registration_pending": False,
        }

    @property
    def inventory_id(self) -> str:
        current = _local_id(INVENTORY_DOMAIN, self._payload())
        if current != self._inventory_id:
            _fail("retained-V1 evidence inventory changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "retained_v1_evidence_inventory_id": self.inventory_id}


@dataclass(frozen=True, slots=True)
class AbstractPassRetainedV1InventoryReplayV1:
    outcome: ReplayOutcomeV1
    inventory: AbstractPassRetainedV1EvidenceInventoryV1 | None
    blocker_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "outcome", ReplayOutcomeV1(self.outcome))
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractPassRetainedV1InventoryError(
                "retained-V1 inventory replay outcome is invalid"
            ) from error
        if self.outcome is ReplayOutcomeV1.RETAINED_V1_INVENTORY_VERIFIED_FORMAL_ACCOUNTING_BLOCKED:
            if type(self.inventory) is not AbstractPassRetainedV1EvidenceInventoryV1 or self.blocker_codes:
                _fail("accepted retained-V1 replay is inconsistent")
        elif self.inventory is not None or not self.blocker_codes:
            _fail("blocked retained-V1 replay lacks a typed reason")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_pass_retained_v1_inventory_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "outcome": self.outcome.value,
            "retained_v1_evidence_inventory_id": (
                self.inventory.inventory_id if self.inventory is not None else None
            ),
            "blocker_codes": list(self.blocker_codes),
            "legacy_evidence_inventory_only": True,
            "production_native_accounting_closed": False,
            "formal_materialization_allowed": False,
            "terminal_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def replay_id(self) -> str:
        return _local_id(REPLAY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "retained_v1_inventory_replay_id": self.replay_id}


def _exact_roots(
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
) -> tuple[
    ModelOnlyQueryExecutionV1,
    coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_v1.AbstractCertifiedZeroValueClosureV1,
]:
    retained = verify_model_only_operational_execution_v1(execution)
    if retained.model_only_result.outcome is not ModelOnlyOutcome.PASS:
        _fail("retained-V1 inventory requires one executor-owned abstract PASS")
    if (
        type(coverage_report) is not coverage_v1.AbstractCertifiedAccountingCoverageReportV1
        or coverage_report.operational_execution_id != retained.operational_execution_id
        or coverage_report.model_only_result_id != retained.model_only_result.result_id
        or coverage_report.legacy_v1_work_vector_id
        != retained.recorded_work.work_vector.work_vector_id
    ):
        _fail("coverage report belongs to another retained execution")
    if (
        type(zero_closure) is not zero_v1.AbstractCertifiedZeroValueClosureV1
        or zero_closure.coverage_report_id != coverage_report.report_id
        or zero_closure.execution_window.operational_execution_id
        != retained.operational_execution_id
        or zero_closure.execution_window.legacy_work_vector_id
        != retained.recorded_work.work_vector.work_vector_id
    ):
        _fail("zero-value closure belongs to another retained execution")
    _cid(coverage_report.report_id, "coverage report")
    _cid(zero_closure.closure_id, "zero-value closure")
    return retained, coverage_report, zero_closure


def _context(
    retained: ModelOnlyQueryExecutionV1,
    report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zeros: zero_v1.AbstractCertifiedZeroValueClosureV1,
) -> AbstractPassRetainedV1InventoryContextV1:
    result = retained.model_only_result
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    all_path = all_path_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    return AbstractPassRetainedV1InventoryContextV1(
        _CONTEXT_ISSUER,
        report.report_id,
        zeros.closure_id,
        retained.operational_execution_id,
        retained.request_id,
        retained.worker_output_id,
        result.result_id,
        retained.native_event_trace.event_trace_id,
        retained.recorded_work.work_vector.work_vector_id,
        retained.recorded_work.reconciliation_proof.reconciliation_proof_id,
        registry.registry_id,
        stage.stage_profile_id,
        all_path.profile_id,
        report.operation_boundary_manifest_id,
        result.logical_occurrence.logical_occurrence_id,
        result.route_attempt.route_attempt_id,
        result.route_context.route_decision_context_id,
    )


def _shared_claims(
    retained: ModelOnlyQueryExecutionV1,
    context: AbstractPassRetainedV1InventoryContextV1,
) -> tuple[LegacySharedAggregateClaimV1, ...]:
    vector = retained.recorded_work.work_vector
    records = {row.path: row for row in vector.records}
    raw = canonical_json_bytes(vector.to_dict())
    digest = hashlib.sha256(raw).hexdigest()
    rows = []
    for path in shared_v1.SHARED_RESOURCE_PATHS:
        record = records[path]
        if path == "io.mounted_bytes_peak":
            if record.value != 0:
                _fail("legacy mounted placeholder changed")
            rows.append(
                LegacySharedAggregateClaimV1(
                    _SHARED_ISSUER,
                    context.context_id,
                    path,
                    LegacyClaimStatusV1.NOT_AVAILABLE,
                    record.record_id,
                    record.value,
                    None,
                    None,
                    None,
                )
            )
        else:
            if record.value <= 0:
                _fail("expected legacy shared aggregate is not positive")
            rows.append(
                LegacySharedAggregateClaimV1(
                    _SHARED_ISSUER,
                    context.context_id,
                    path,
                    LegacyClaimStatusV1.LEGACY_AGGREGATE_NOT_VERIFIED,
                    record.record_id,
                    record.value,
                    record.value,
                    vector.work_vector_id,
                    digest,
                )
            )
    return tuple(rows)


def _owner_candidates(
    retained: ModelOnlyQueryExecutionV1,
    context: AbstractPassRetainedV1InventoryContextV1,
) -> tuple[LegacyOwnerEventCandidateV1, ...]:
    vector = retained.recorded_work.work_vector
    records = {row.path: row for row in vector.records}
    trace_raw = canonical_json_bytes(retained.native_event_trace.to_dict())
    trace_digest = hashlib.sha256(trace_raw).hexdigest()
    rows = []
    for path in _LEGACY_OWNER_PATHS:
        semantics_id, owner, scope = _leaf_metadata(path)
        events = tuple(
            (event.sequence, event.amount)
            for event in retained.native_event_trace.events
            if event.path == path
        )
        record = records[path]
        if record.value != sum(amount for _sequence, amount in events):
            _fail("legacy owner aggregate differs from its retained event trace")
        rows.append(
            LegacyOwnerEventCandidateV1(
                _OWNER_ISSUER,
                context.context_id,
                path,
                semantics_id,
                owner,
                scope,
                record.record_id,
                retained.native_event_trace.event_trace_id,
                trace_digest,
                record.value,
                events,
            )
        )
    return tuple(rows)


def _reconciliation_claims(
    retained: ModelOnlyQueryExecutionV1,
    context: AbstractPassRetainedV1InventoryContextV1,
) -> tuple[LegacyInternalReconciliationClaimV1, ...]:
    vector = retained.recorded_work.work_vector
    records = {row.path: row for row in vector.records}
    formulas = {
        path: (formula_id, dependencies)
        for path, formula_id, dependencies in _formula_blueprint()
    }
    values = {path: vector.value(path) for path in _DERIVED_PATHS}
    if (
        values
        != {
            "process.exit_failures": 0,
            "process.exit_successes": 1,
            "route.attempts": 1,
            "route.failures": 0,
            "route.successes": 1,
            "solver.attempts": 1,
            "solver.failures": 0,
            "solver.successes": 1,
        }
        or values["route.attempts"]
        != values["route.failures"] + values["route.successes"]
        or values["solver.attempts"]
        != values["solver.failures"] + values["solver.successes"]
        or vector.value("process.launches")
        != values["process.exit_failures"] + values["process.exit_successes"]
    ):
        _fail("legacy internal reconciliation values changed")
    legacy_proof = retained.recorded_work.reconciliation_proof
    proof_digest = hashlib.sha256(
        canonical_json_bytes(legacy_proof.to_dict())
    ).hexdigest()
    rows = []
    for path in _DERIVED_PATHS:
        formula_id, dependencies = formulas[path]
        supporting_paths = set(dependencies) | {path}
        rows.append(
            LegacyInternalReconciliationClaimV1(
                _RECONCILIATION_ISSUER,
                context.context_id,
                path,
                values[path],
                formula_id,
                dependencies,
                records[path].record_id,
                tuple(sorted(records[name].record_id for name in supporting_paths)),
                legacy_proof.reconciliation_proof_id,
                proof_digest,
            )
        )
    return tuple(rows)


def _formal_blockers(
    report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zeros: zero_v1.AbstractCertifiedZeroValueClosureV1,
    context: AbstractPassRetainedV1InventoryContextV1,
    shared_claims: tuple[LegacySharedAggregateClaimV1, ...],
    owner_candidates: tuple[LegacyOwnerEventCandidateV1, ...],
    reconciliation_claims: tuple[LegacyInternalReconciliationClaimV1, ...],
) -> tuple[AbstractPassRetainedV1FormalBlockerV1, ...]:
    rows: list[AbstractPassRetainedV1FormalBlockerV1] = []
    for gap in report.path_gaps:
        if gap.code is coverage_v1.PathGapCodeV1.NO_V1_COUNTER_LEAF_OR_EMISSION:
            rows.append(
                AbstractPassRetainedV1FormalBlockerV1(
                    context.context_id,
                    gap.path,
                    FormalBlockerCodeV1.NO_V1_COUNTER_OR_EVENT,
                    gap.gap_id,
                    "the retained V1 execution emitted no counter or event for this required V6 path",
                )
            )
    for proof in zeros.native_zero_proofs:
        rows.append(
            AbstractPassRetainedV1FormalBlockerV1(
                context.context_id,
                proof.path,
                FormalBlockerCodeV1.ZERO_VALUE_IS_NOT_PROFILE_NATIVE_ZERO,
                proof.proof_id,
                "the zero is a retained value proof, not a formal route-profile native-zero attestation",
            )
        )
    for claim in shared_claims:
        code = (
            FormalBlockerCodeV1.MOUNTED_PAYLOAD_NOT_MEASURED_FROM_WINDOW_START
            if claim.path == "io.mounted_bytes_peak"
            else FormalBlockerCodeV1.LEGACY_SHARED_AGGREGATE_LACKS_WINDOW_STAGE_CUTOFF_REPLAY
        )
        detail = (
            "mounted payload was not measured from the start of the execution window"
            if claim.path == "io.mounted_bytes_peak"
            else "the legacy aggregate lacks a complete measurement window, stage assignment, and cutoff replay"
        )
        rows.append(
            AbstractPassRetainedV1FormalBlockerV1(
                context.context_id, claim.path, code, claim.claim_id, detail
            )
        )
    for candidate in owner_candidates:
        rows.append(
            AbstractPassRetainedV1FormalBlockerV1(
                context.context_id,
                candidate.path,
                FormalBlockerCodeV1.LEGACY_OWNER_EVENT_LACKS_HOOK_STAGE_CUTOFF_REPLAY,
                candidate.candidate_id,
                "the legacy event candidate lacks production hook semantics, stage assignment, and cutoff replay",
            )
        )
    for claim in reconciliation_claims:
        rows.append(
            AbstractPassRetainedV1FormalBlockerV1(
                context.context_id,
                claim.path,
                FormalBlockerCodeV1.LEGACY_INTERNAL_RECONCILIATION_LACKS_FORMAL_DEPENDENCIES,
                claim.claim_id,
                "the legacy internal arithmetic lacks formal V6 semantic dependency records",
            )
        )
    return tuple(sorted(rows, key=lambda row: row.path))


def _build_from_exact_roots(
    retained: ModelOnlyQueryExecutionV1,
    report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zeros: zero_v1.AbstractCertifiedZeroValueClosureV1,
) -> AbstractPassRetainedV1EvidenceInventoryV1:
    context = _context(retained, report, zeros)
    shared_claims = _shared_claims(retained, context)
    owner_candidates = _owner_candidates(retained, context)
    reconciliation_claims = _reconciliation_claims(retained, context)
    zero_ids = tuple(sorted(row.proof_id for row in zeros.native_zero_proofs))
    blockers = _formal_blockers(
        report,
        zeros,
        context,
        shared_claims,
        owner_candidates,
        reconciliation_claims,
    )
    return AbstractPassRetainedV1EvidenceInventoryV1(
        _INVENTORY_ISSUER,
        context,
        shared_claims,
        owner_candidates,
        reconciliation_claims,
        zero_ids,
        blockers,
    )


def _memo_key(
    retained: ModelOnlyQueryExecutionV1,
    report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zeros: zero_v1.AbstractCertifiedZeroValueClosureV1,
) -> tuple[str, str, str]:
    return retained.operational_execution_id, report.report_id, zeros.closure_id


def _memo_bytes(
    key: tuple[str, str, str], inventory: AbstractPassRetainedV1EvidenceInventoryV1
) -> bytes:
    raw = canonical_json_bytes(inventory.to_document())
    if len(_INVENTORY_BYTES_MEMO) >= _INVENTORY_BYTES_MEMO_MAX and key not in _INVENTORY_BYTES_MEMO:
        _INVENTORY_BYTES_MEMO.pop(next(iter(_INVENTORY_BYTES_MEMO)))
    _INVENTORY_BYTES_MEMO[key] = raw
    return raw


def inventory_abstract_pass_retained_v1_accounting_v1(
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
) -> AbstractPassRetainedV1EvidenceInventoryV1:
    """Issue only the maximal honest retained-V1 evidence inventory."""

    retained, report, zeros = _exact_roots(execution, coverage_report, zero_closure)
    inventory = _build_from_exact_roots(retained, report, zeros)
    _memo_bytes(_memo_key(retained, report, zeros), inventory)
    return inventory


def verify_abstract_pass_retained_v1_inventory_document_v1(
    claimed_document: Any,
    execution: ModelOnlyQueryExecutionV1,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
) -> AbstractPassRetainedV1InventoryReplayV1:
    """Replay roots and reject any promotion beyond the retained inventory."""

    try:
        retained, report, zeros = _exact_roots(
            execution, coverage_report, zero_closure
        )
        key = _memo_key(retained, report, zeros)
        expected_raw = _INVENTORY_BYTES_MEMO.get(key)
        if expected_raw is None:
            generated = _build_from_exact_roots(retained, report, zeros)
            expected_raw = _memo_bytes(key, generated)
        if (
            type(claimed_document) is not dict
            or canonical_json_bytes(claimed_document) != expected_raw
        ):
            raise ConstructionK7AbstractPassRetainedV1InventoryError(
                "claimed retained-V1 inventory changed"
            )
    except Exception:
        return AbstractPassRetainedV1InventoryReplayV1(
            ReplayOutcomeV1.DOCUMENT_BLOCKED,
            None,
            ("EXACT_RETAINED_V1_INVENTORY_REPLAY_FAILED",),
        )
    expected = _build_from_exact_roots(retained, report, zeros)
    if canonical_json_bytes(expected.to_document()) != expected_raw:
        _fail("primitive retained-V1 memo differs from fresh authority replay")
    return AbstractPassRetainedV1InventoryReplayV1(
        ReplayOutcomeV1.RETAINED_V1_INVENTORY_VERIFIED_FORMAL_ACCOUNTING_BLOCKED,
        expected,
        (),
    )


__all__ = [
    "AbstractPassRetainedV1EvidenceInventoryV1",
    "AbstractPassRetainedV1FormalBlockerV1",
    "AbstractPassRetainedV1InventoryContextV1",
    "AbstractPassRetainedV1InventoryReplayV1",
    "ConstructionK7AbstractPassRetainedV1InventoryError",
    "FormalBlockerCodeV1",
    "LegacyClaimStatusV1",
    "LegacyInternalReconciliationClaimV1",
    "LegacyOwnerEventCandidateV1",
    "LegacySharedAggregateClaimV1",
    "LOCAL_DOMAINS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "ReplayOutcomeV1",
    "inventory_abstract_pass_retained_v1_accounting_v1",
    "verify_abstract_pass_retained_v1_inventory_document_v1",
]
