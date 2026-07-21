"""Independent transport verifier for one H2 model-failure LOCAL closure.

The earlier :mod:`acfqp.phase3e_bundle_v1` bundle deliberately ends at the
failed abstract prefix.  This module extends that transport boundary through
the selected LOCAL route, the sealed factory/delegate accounting merge, the
marginal and occurrence aggregates, and the typed terminal *artifact*.

Transport bytes never recreate runtime semantic authority.  In particular,
the local capability/ground slice and the post-audit ground replay are not
serializable in the current contract.  A successful verification here proves
the complete byte/content/accounting/routing/topology chain, but it does not
mint a plan certificate.  The immutable blocker tuple records that boundary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

from acfqp.access_protocol_v1 import (
    AccessRouteScope,
    AccessEventLogV1,
    ProtocolSequenceProfileV1,
    RouteDecisionFreezeAttestationV1,
    _violation_reason,
)
from acfqp.accounting_v1 import (
    NativeZeroAttestationV1,
    ReconciliationProofV1,
    ReducerEnum,
    SHARED_AXES,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualWorkScope,
    official_actual_projection_profile_v1,
)
from acfqp.campaign_v1 import LogicalOccurrenceV1, RouteAttemptV1
from acfqp.marginal_accounting_v1 import (
    AggregatedMarginalWorkV1,
    MarginalWorkAggregationProofV1,
    verify_marginal_work_aggregate_v1,
)
from acfqp.native_recorder_v1 import RecordedWorkV1
from acfqp.phase3e_bundle_v1 import (
    MANIFEST_CHECKSUM_FILENAME,
    MANIFEST_FILENAME,
    RECORDED_WORK_TRANSPORT_SCHEMA,
    Phase3EBundleV1Error,
    recorded_work_from_dict_v1,
    recorded_work_to_dict_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackCardinalityBoundV1,
    SafeChainFallbackCardinalitySourceV1,
)
from acfqp.phase3e_local_preselection_v1 import (
    SafeChainLocalCardinalityBoundV1,
    SafeChainLocalPreselectionSourceV1,
)
from acfqp.phase3e_local_semantics_v1 import (
    LocalSolverOutcome,
    LocalTransactionResultV1,
    PostAuditCertificateV1,
    PostAuditOutcome,
    TrustedLocalExecutionV1,
)
from acfqp.phase3e_model_failure_consumer_v1 import (
    MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS,
    MODEL_FAILURE_CONSUMER_STATUS,
    official_safe_chain_fallback_cap_profile_v1,
)
from acfqp.phase3e_model_failure_occurrence_v1 import (
    MODEL_FAILURE_OCCURRENCE_STATUS,
    ModelFailureOccurrenceClosureV1,
    require_model_failure_occurrence_closure_v1,
)
from acfqp.phase3e_model_failure_preparation_accounting_v1 import (
    ModelFailurePreparationTraceV1,
    PREPARATION_EXCLUSIONS,
    PREPARATION_OCCURRENCE_CHARGE_STATUS,
    derive_model_failure_preparation_accounting_v1,
)
from acfqp.phase3e_model_only_executor_v1 import (
    EXECUTION_SCHEMA,
    REQUEST_SCHEMA,
    ModelOnlyExecutionRequestV1,
    parse_model_only_execution_request_v1,
    verify_model_only_failed_prefix_artifact_v1,
)
from acfqp.phase3e_model_only_v1 import MODEL_ONLY_RESULT_SCHEMA
from acfqp.phase3e_occurrence_accounting_v1 import (
    OccurrenceRawEvidenceKind,
    OccurrenceWorkComponentKind,
    Phase3EOccurrenceWorkAggregateV1,
)
from acfqp.phase3e_occurrence_runner_v1 import OccurrenceClosureCodeV1
from acfqp.phase3e_rapm_consumer_v1 import (
    LOCAL_QUERY_KEY,
    load_phase3c_model_source_v1,
)
from acfqp.phase3e_sealed_executor_v1 import (
    ExecutorRecipeV1,
    MergedSealedRouteExecutionWorkV1,
    RuntimeFactoryCardinalityV1,
    RuntimeTreeManifestV1,
    SealedExecutorConstructionAccountingV1,
    SealedExecutorConstructionReceiptV1,
    SealedExecutorExecutionMergeProofV1,
    verify_sealed_factory_execution_merge_v1,
)
from acfqp.phase3e_two_stage_accounting_v1 import (
    SealedAccountingCoreV1,
    TwoStageWorkAggregateV1,
    VerificationChargePlanV1,
    VerificationChargeReceiptV1,
)
from acfqp.phase3e_ids import (
    ACCESS_EVENT_LOG_DOMAIN,
    ACCOUNTING_CORE_SEAL_DOMAIN,
    CARDINALITY_EVIDENCE_DOMAIN,
    CAUSAL_EVIDENCE_DOMAIN,
    DECISION_POINT_DOMAIN,
    EXECUTOR_RECIPE_DOMAIN,
    FRONTIER_SNAPSHOT_DOMAIN,
    GROUND_FALLBACK_CARDINALITY_BOUND_DOMAIN,
    GROUND_FALLBACK_CARDINALITY_SOURCE_DOMAIN,
    LOCAL_CARDINALITY_BOUND_DOMAIN,
    LOCAL_PRESELECTION_SOURCE_DOMAIN,
    LOGICAL_OCCURRENCE_DOMAIN,
    MARGINAL_WORK_AGGREGATION_PROOF_DOMAIN,
    MODEL_FAILURE_OCCURRENCE_CLOSURE_DOMAIN,
    MODEL_FAILURE_PREPARATION_ACCOUNTING_DOMAIN,
    MODEL_FAILURE_PREPARATION_TRACE_DOMAIN,
    MODEL_ONLY_FAILED_PREFIX_ACCOUNTING_AUTHORITY_DOMAIN,
    MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN,
    MODEL_ONLY_RESULT_DOMAIN,
    OCCURRENCE_WORK_AGGREGATE_DOMAIN,
    POST_AUDIT_CERTIFICATE_DOMAIN,
    RECORDED_WORK_TRANSPORT_DOMAIN,
    ROUTE_ATTEMPT_DOMAIN,
    ROUTE_CAP_PROFILE_DOMAIN,
    ROUTE_DECISION_CONTEXT_DOMAIN,
    ROUTE_DECISION_DOMAIN,
    ROUTE_DECISION_FREEZE_ATTESTATION_DOMAIN,
    ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN,
    ROUTE_UPPER_FORMULA_DOMAIN,
    RUNTIME_FACTORY_CARDINALITY_DOMAIN,
    RUNTIME_TREE_MANIFEST_DOMAIN,
    SEALED_EXECUTOR_CONSTRUCTION_RECEIPT_DOMAIN,
    SEALED_EXECUTOR_EXECUTION_MERGE_PROOF_DOMAIN,
    SEALED_GROUND_FALLBACK_ROUTE_CAP_PROFILE_DOMAIN,
    SELECTED_ROUTE_BUNDLE_MANIFEST_DOMAIN,
    TERMINAL_ARTIFACT_DOMAIN,
    TRANSACTION_DOMAIN,
    TWO_STAGE_WORK_AGGREGATE_DOMAIN,
    VERIFICATION_CHARGE_PLAN_DOMAIN,
    VERIFICATION_CHARGE_RECEIPT_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
    require_registered_domain_tag,
)
from acfqp.route_upper_formula_v1 import (
    RouteUpperFormulaV1,
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    CausalEvidenceV1,
    DecisionPointV1,
    FrontierSnapshotV1,
    MarginalRouteDecisionV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TransactionV1,
)


SCHEMA_VERSION = "1.0.0"
BUNDLE_ENTRY_SCHEMA = "acfqp.selected_route_bundle_entry.v1"
BUNDLE_MANIFEST_SCHEMA = "acfqp.selected_route_bundle_manifest.v1"
BUNDLE_SCOPE = "H2_MODEL_FAILURE_LOCAL_CLOSURE_TRANSPORT_ONLY"
VERIFICATION_STATUS = "VERIFIED_LOCAL_ROUTE_ACCOUNTING_AND_TOPOLOGY"
SEMANTIC_CERTIFICATE_STATUS = "NOT_MINTED_FROM_TRANSPORT"
REMAINING_BLOCKERS = (
    *MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS,
    "PREPARATION_ACCOUNTING_RETAINED_NOT_YET_OCCURRENCE_CHARGED",
    "LOCAL_GROUND_PROOF_INPUTS_NOT_SERIALIZED",
    "POSTAUDIT_GROUND_REPLAY_INPUTS_NOT_SERIALIZED",
    "TRANSPORT_ATTESTATIONS_CANNOT_MINT_LIVE_SEMANTIC_AUTHORITY",
    "INDEPENDENT_TERMINAL_SEMANTIC_CERTIFICATE_NOT_AVAILABLE",
)
_MAX_DOCUMENT_BYTES = 64 * 1024 * 1024
_DESCRIPTOR_READ_TEST_HOOK_V1: Any | None = None


class Phase3ESelectedRouteBundleV1Error(ValueError):
    """A selected-route bundle byte, role, identity, or replay is invalid."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _cid(value: Any, name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise Phase3ESelectedRouteBundleV1Error(
            f"{name} must be a full lowercase SHA-256"
        ) from error


def _safe_relative_path(value: Any) -> str:
    if type(value) is not str or not value or "\\" in value:
        raise Phase3ESelectedRouteBundleV1Error(
            "bundle path must be a POSIX relative path"
        )
    parts = value.split("/")
    if value.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise Phase3ESelectedRouteBundleV1Error("bundle path traversal is forbidden")
    return value


def _plain_object(raw: bytes, *, source: str) -> dict[str, Any]:
    if len(raw) > _MAX_DOCUMENT_BYTES:
        raise Phase3ESelectedRouteBundleV1Error(f"{source} exceeds size cap")
    try:
        loads_canonical_json(raw)
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise Phase3ESelectedRouteBundleV1Error(
            f"{source} is not canonical JSON: {error}"
        ) from error
    if type(value) is not dict:
        raise Phase3ESelectedRouteBundleV1Error(f"{source} root must be an object")
    return value


class SelectedRouteBundleRoleV1(str, Enum):
    MODEL_ONLY_REQUEST = "MODEL_ONLY_REQUEST"
    MODEL_ONLY_EXECUTION = "MODEL_ONLY_EXECUTION"
    MODEL_ONLY_RESULT = "MODEL_ONLY_RESULT"
    FAILED_PREFIX_AUTHORITY = "FAILED_PREFIX_AUTHORITY"
    FAILED_PREFIX_WORK = "FAILED_PREFIX_WORK"
    PREPARATION_TRACE = "PREPARATION_TRACE"
    PREPARATION_INCREMENTAL_WORK = "PREPARATION_INCREMENTAL_WORK"
    PREPARATION_AGGREGATE_WORK = "PREPARATION_AGGREGATE_WORK"
    PREPARATION_ACCOUNTING = "PREPARATION_ACCOUNTING"
    ROUTE_CONTEXT = "ROUTE_CONTEXT"
    LOGICAL_OCCURRENCE = "LOGICAL_OCCURRENCE"
    ROUTE_ATTEMPT = "ROUTE_ATTEMPT"
    RUNTIME_MANIFEST = "RUNTIME_MANIFEST"
    RUNTIME_CARDINALITY = "RUNTIME_CARDINALITY"
    EXECUTOR_RECIPE = "EXECUTOR_RECIPE"
    FRONTIER = "FRONTIER"
    CAUSAL = "CAUSAL"
    DECISION_POINT = "DECISION_POINT"
    TRANSACTION = "TRANSACTION"
    LOCAL_CAP = "LOCAL_CAP"
    LOCAL_SOURCE = "LOCAL_SOURCE"
    LOCAL_BOUND = "LOCAL_BOUND"
    LOCAL_CARDINALITY = "LOCAL_CARDINALITY"
    LOCAL_FORMULA = "LOCAL_FORMULA"
    LOCAL_UPPER = "LOCAL_UPPER"
    FALLBACK_CAP = "FALLBACK_CAP"
    FALLBACK_SOURCE = "FALLBACK_SOURCE"
    FALLBACK_BOUND = "FALLBACK_BOUND"
    FALLBACK_CARDINALITY = "FALLBACK_CARDINALITY"
    FALLBACK_FORMULA = "FALLBACK_FORMULA"
    FALLBACK_UPPER = "FALLBACK_UPPER"
    ROUTE_DECISION = "ROUTE_DECISION"
    ACCESS_LOG = "ACCESS_LOG"
    FREEZE = "FREEZE"
    COMMON_CORE = "COMMON_CORE"
    COMMON_CORE_WORK = "COMMON_CORE_WORK"
    COMMON_PLAN = "COMMON_PLAN"
    COMMON_SUFFIX_WORK = "COMMON_SUFFIX_WORK"
    COMMON_AGGREGATE_WORK = "COMMON_AGGREGATE_WORK"
    COMMON_AGGREGATE_META = "COMMON_AGGREGATE_META"
    COMMON_RECEIPT = "COMMON_RECEIPT"
    CONSTRUCTION_RECEIPT = "CONSTRUCTION_RECEIPT"
    FACTORY_WORK = "FACTORY_WORK"
    DELEGATE_WORK = "DELEGATE_WORK"
    MERGED_ROUTE_WORK = "MERGED_ROUTE_WORK"
    EXECUTION_MERGE_PROOF = "EXECUTION_MERGE_PROOF"
    LOCAL_RESULT = "LOCAL_RESULT"
    POST_AUDIT = "POST_AUDIT"
    VERIFICATION_SUFFIX_WORK = "VERIFICATION_SUFFIX_WORK"
    MARGINAL_AGGREGATE_WORK = "MARGINAL_AGGREGATE_WORK"
    MARGINAL_AGGREGATION_PROOF = "MARGINAL_AGGREGATION_PROOF"
    OCCURRENCE_WORK_AGGREGATE = "OCCURRENCE_WORK_AGGREGATE"
    TERMINAL = "TERMINAL"
    CLOSURE_SUMMARY = "CLOSURE_SUMMARY"


@dataclass(frozen=True, slots=True)
class _RoleSpecV1:
    schema_id: str
    domain_tag: str
    path: str


_ROLE_SPECS: dict[SelectedRouteBundleRoleV1, _RoleSpecV1] = {
    SelectedRouteBundleRoleV1.MODEL_ONLY_REQUEST: _RoleSpecV1(REQUEST_SCHEMA, MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN, "model_only/request.json"),
    SelectedRouteBundleRoleV1.MODEL_ONLY_EXECUTION: _RoleSpecV1(EXECUTION_SCHEMA, MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN, "model_only/execution.json"),
    SelectedRouteBundleRoleV1.MODEL_ONLY_RESULT: _RoleSpecV1(MODEL_ONLY_RESULT_SCHEMA, MODEL_ONLY_RESULT_DOMAIN, "model_only/result.json"),
    SelectedRouteBundleRoleV1.FAILED_PREFIX_AUTHORITY: _RoleSpecV1("acfqp.model_only_failed_prefix_accounting_authority.v1", MODEL_ONLY_FAILED_PREFIX_ACCOUNTING_AUTHORITY_DOMAIN, "model_only/failed_prefix_authority.json"),
    SelectedRouteBundleRoleV1.FAILED_PREFIX_WORK: _RoleSpecV1(RECORDED_WORK_TRANSPORT_SCHEMA, RECORDED_WORK_TRANSPORT_DOMAIN, "accounting/failed_prefix_work.json"),
    SelectedRouteBundleRoleV1.PREPARATION_TRACE: _RoleSpecV1("acfqp.model_failure_preparation_trace.v1", MODEL_FAILURE_PREPARATION_TRACE_DOMAIN, "accounting/preparation_trace.json"),
    SelectedRouteBundleRoleV1.PREPARATION_INCREMENTAL_WORK: _RoleSpecV1(RECORDED_WORK_TRANSPORT_SCHEMA, RECORDED_WORK_TRANSPORT_DOMAIN, "accounting/preparation_incremental_work.json"),
    SelectedRouteBundleRoleV1.PREPARATION_AGGREGATE_WORK: _RoleSpecV1(RECORDED_WORK_TRANSPORT_SCHEMA, RECORDED_WORK_TRANSPORT_DOMAIN, "accounting/preparation_aggregate_work.json"),
    SelectedRouteBundleRoleV1.PREPARATION_ACCOUNTING: _RoleSpecV1("acfqp.model_failure_preparation_accounting.v1", MODEL_FAILURE_PREPARATION_ACCOUNTING_DOMAIN, "accounting/preparation_accounting.json"),
    SelectedRouteBundleRoleV1.ROUTE_CONTEXT: _RoleSpecV1("acfqp.route_decision_context.v1", ROUTE_DECISION_CONTEXT_DOMAIN, "routing/context.json"),
    SelectedRouteBundleRoleV1.LOGICAL_OCCURRENCE: _RoleSpecV1("acfqp.logical_occurrence.v1", LOGICAL_OCCURRENCE_DOMAIN, "campaign/logical_occurrence.json"),
    SelectedRouteBundleRoleV1.ROUTE_ATTEMPT: _RoleSpecV1("acfqp.route_attempt.v1", ROUTE_ATTEMPT_DOMAIN, "campaign/route_attempt.json"),
    SelectedRouteBundleRoleV1.RUNTIME_MANIFEST: _RoleSpecV1("acfqp.runtime_tree_manifest.v1", RUNTIME_TREE_MANIFEST_DOMAIN, "runtime/manifest.json"),
    SelectedRouteBundleRoleV1.RUNTIME_CARDINALITY: _RoleSpecV1("acfqp.runtime_factory_cardinality.v1", RUNTIME_FACTORY_CARDINALITY_DOMAIN, "runtime/cardinality.json"),
    SelectedRouteBundleRoleV1.EXECUTOR_RECIPE: _RoleSpecV1("acfqp.executor_recipe.v1", EXECUTOR_RECIPE_DOMAIN, "runtime/recipe.json"),
    SelectedRouteBundleRoleV1.FRONTIER: _RoleSpecV1("acfqp.frontier_snapshot.v1", FRONTIER_SNAPSHOT_DOMAIN, "routing/frontier.json"),
    SelectedRouteBundleRoleV1.CAUSAL: _RoleSpecV1("acfqp.causal_evidence.v1", CAUSAL_EVIDENCE_DOMAIN, "routing/causal.json"),
    SelectedRouteBundleRoleV1.DECISION_POINT: _RoleSpecV1("acfqp.decision_point.v1", DECISION_POINT_DOMAIN, "routing/decision_point.json"),
    SelectedRouteBundleRoleV1.TRANSACTION: _RoleSpecV1("acfqp.transaction.v1", TRANSACTION_DOMAIN, "routing/transaction.json"),
    SelectedRouteBundleRoleV1.LOCAL_CAP: _RoleSpecV1("acfqp.route_cap_profile.v1", ROUTE_CAP_PROFILE_DOMAIN, "routing/local_cap.json"),
    SelectedRouteBundleRoleV1.LOCAL_SOURCE: _RoleSpecV1("acfqp.safe_chain_local_preselection_source.v1", LOCAL_PRESELECTION_SOURCE_DOMAIN, "routing/local_source.json"),
    SelectedRouteBundleRoleV1.LOCAL_BOUND: _RoleSpecV1("acfqp.safe_chain_local_cardinality_bound.v1", LOCAL_CARDINALITY_BOUND_DOMAIN, "routing/local_bound.json"),
    SelectedRouteBundleRoleV1.LOCAL_CARDINALITY: _RoleSpecV1("acfqp.cardinality_evidence.v1", CARDINALITY_EVIDENCE_DOMAIN, "routing/local_cardinality.json"),
    SelectedRouteBundleRoleV1.LOCAL_FORMULA: _RoleSpecV1("acfqp.route_upper_formula.v1", ROUTE_UPPER_FORMULA_DOMAIN, "routing/local_formula.json"),
    SelectedRouteBundleRoleV1.LOCAL_UPPER: _RoleSpecV1("acfqp.route_upper_bound_envelope.v1", ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN, "routing/local_upper.json"),
    SelectedRouteBundleRoleV1.FALLBACK_CAP: _RoleSpecV1("acfqp.sealed_ground_fallback_route_cap_profile.v1", SEALED_GROUND_FALLBACK_ROUTE_CAP_PROFILE_DOMAIN, "routing/fallback_cap.json"),
    SelectedRouteBundleRoleV1.FALLBACK_SOURCE: _RoleSpecV1("acfqp.safe_chain_fallback_cardinality_source.v1", GROUND_FALLBACK_CARDINALITY_SOURCE_DOMAIN, "routing/fallback_source.json"),
    SelectedRouteBundleRoleV1.FALLBACK_BOUND: _RoleSpecV1("acfqp.ground_fallback_cardinality_bound.v1", GROUND_FALLBACK_CARDINALITY_BOUND_DOMAIN, "routing/fallback_bound.json"),
    SelectedRouteBundleRoleV1.FALLBACK_CARDINALITY: _RoleSpecV1("acfqp.cardinality_evidence.v1", CARDINALITY_EVIDENCE_DOMAIN, "routing/fallback_cardinality.json"),
    SelectedRouteBundleRoleV1.FALLBACK_FORMULA: _RoleSpecV1("acfqp.route_upper_formula.v1", ROUTE_UPPER_FORMULA_DOMAIN, "routing/fallback_formula.json"),
    SelectedRouteBundleRoleV1.FALLBACK_UPPER: _RoleSpecV1("acfqp.route_upper_bound_envelope.v1", ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN, "routing/fallback_upper.json"),
    SelectedRouteBundleRoleV1.ROUTE_DECISION: _RoleSpecV1("acfqp.marginal_route_decision.v1", ROUTE_DECISION_DOMAIN, "routing/decision.json"),
    SelectedRouteBundleRoleV1.ACCESS_LOG: _RoleSpecV1("acfqp.access_event_log.v1", ACCESS_EVENT_LOG_DOMAIN, "execution/access_log.json"),
    SelectedRouteBundleRoleV1.FREEZE: _RoleSpecV1("acfqp.route_decision_freeze_attestation.v1", ROUTE_DECISION_FREEZE_ATTESTATION_DOMAIN, "execution/freeze.json"),
    SelectedRouteBundleRoleV1.COMMON_CORE: _RoleSpecV1("acfqp.accounting_core_seal.v1", ACCOUNTING_CORE_SEAL_DOMAIN, "accounting/common_core.json"),
    SelectedRouteBundleRoleV1.COMMON_CORE_WORK: _RoleSpecV1(RECORDED_WORK_TRANSPORT_SCHEMA, RECORDED_WORK_TRANSPORT_DOMAIN, "accounting/common_core_work.json"),
    SelectedRouteBundleRoleV1.COMMON_PLAN: _RoleSpecV1("acfqp.verification_charge_plan.v1", VERIFICATION_CHARGE_PLAN_DOMAIN, "accounting/common_plan.json"),
    SelectedRouteBundleRoleV1.COMMON_SUFFIX_WORK: _RoleSpecV1(RECORDED_WORK_TRANSPORT_SCHEMA, RECORDED_WORK_TRANSPORT_DOMAIN, "accounting/common_suffix_work.json"),
    SelectedRouteBundleRoleV1.COMMON_AGGREGATE_WORK: _RoleSpecV1(RECORDED_WORK_TRANSPORT_SCHEMA, RECORDED_WORK_TRANSPORT_DOMAIN, "accounting/common_aggregate_work.json"),
    SelectedRouteBundleRoleV1.COMMON_AGGREGATE_META: _RoleSpecV1("acfqp.two_stage_work_aggregate.v1", TWO_STAGE_WORK_AGGREGATE_DOMAIN, "accounting/common_aggregate_meta.json"),
    SelectedRouteBundleRoleV1.COMMON_RECEIPT: _RoleSpecV1("acfqp.verification_charge_receipt.v1", VERIFICATION_CHARGE_RECEIPT_DOMAIN, "accounting/common_receipt.json"),
    SelectedRouteBundleRoleV1.CONSTRUCTION_RECEIPT: _RoleSpecV1("acfqp.sealed_executor_construction_receipt.v1", SEALED_EXECUTOR_CONSTRUCTION_RECEIPT_DOMAIN, "execution/construction_receipt.json"),
    SelectedRouteBundleRoleV1.FACTORY_WORK: _RoleSpecV1(RECORDED_WORK_TRANSPORT_SCHEMA, RECORDED_WORK_TRANSPORT_DOMAIN, "accounting/factory_work.json"),
    SelectedRouteBundleRoleV1.DELEGATE_WORK: _RoleSpecV1(RECORDED_WORK_TRANSPORT_SCHEMA, RECORDED_WORK_TRANSPORT_DOMAIN, "accounting/delegate_work.json"),
    SelectedRouteBundleRoleV1.MERGED_ROUTE_WORK: _RoleSpecV1(RECORDED_WORK_TRANSPORT_SCHEMA, RECORDED_WORK_TRANSPORT_DOMAIN, "accounting/merged_route_work.json"),
    SelectedRouteBundleRoleV1.EXECUTION_MERGE_PROOF: _RoleSpecV1("acfqp.sealed_executor_execution_merge_proof.v1", SEALED_EXECUTOR_EXECUTION_MERGE_PROOF_DOMAIN, "accounting/execution_merge_proof.json"),
    SelectedRouteBundleRoleV1.LOCAL_RESULT: _RoleSpecV1("acfqp.local_transaction_result.v1", "acfqp:local-transaction-result:v1", "execution/local_result.json"),
    SelectedRouteBundleRoleV1.POST_AUDIT: _RoleSpecV1("acfqp.post_audit_certificate.v1", POST_AUDIT_CERTIFICATE_DOMAIN, "execution/post_audit.json"),
    SelectedRouteBundleRoleV1.VERIFICATION_SUFFIX_WORK: _RoleSpecV1(RECORDED_WORK_TRANSPORT_SCHEMA, RECORDED_WORK_TRANSPORT_DOMAIN, "accounting/route_verification_suffix.json"),
    SelectedRouteBundleRoleV1.MARGINAL_AGGREGATE_WORK: _RoleSpecV1(RECORDED_WORK_TRANSPORT_SCHEMA, RECORDED_WORK_TRANSPORT_DOMAIN, "accounting/marginal_aggregate_work.json"),
    SelectedRouteBundleRoleV1.MARGINAL_AGGREGATION_PROOF: _RoleSpecV1("acfqp.marginal_work_aggregation_proof.v1", MARGINAL_WORK_AGGREGATION_PROOF_DOMAIN, "accounting/marginal_aggregation_proof.json"),
    SelectedRouteBundleRoleV1.OCCURRENCE_WORK_AGGREGATE: _RoleSpecV1("acfqp.phase3e_occurrence_work_aggregate.v1", OCCURRENCE_WORK_AGGREGATE_DOMAIN, "accounting/occurrence_work_aggregate.json"),
    SelectedRouteBundleRoleV1.TERMINAL: _RoleSpecV1("acfqp.terminal_artifact.v1", TERMINAL_ARTIFACT_DOMAIN, "terminal/terminal.json"),
    SelectedRouteBundleRoleV1.CLOSURE_SUMMARY: _RoleSpecV1("acfqp.model_failure_occurrence_closure.v1", MODEL_FAILURE_OCCURRENCE_CLOSURE_DOMAIN, "terminal/closure.json"),
}


@dataclass(frozen=True, slots=True)
class SelectedRouteBundleEntryV1:
    role: SelectedRouteBundleRoleV1
    schema_id: str
    domain_tag: str
    content_id: str
    relative_path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", SelectedRouteBundleRoleV1(self.role))
        try:
            require_registered_domain_tag(self.domain_tag)
        except ValueError as error:
            raise Phase3ESelectedRouteBundleV1Error(str(error)) from error
        _cid(self.content_id, "entry content_id")
        _cid(self.sha256, "entry sha256")
        object.__setattr__(self, "relative_path", _safe_relative_path(self.relative_path))
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise Phase3ESelectedRouteBundleV1Error("entry size must be nonnegative")
        spec = _ROLE_SPECS[self.role]
        if (self.schema_id, self.domain_tag, self.relative_path) != (
            spec.schema_id, spec.domain_tag, spec.path
        ):
            raise Phase3ESelectedRouteBundleV1Error(
                "entry role/schema/domain/path binding mismatch"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": BUNDLE_ENTRY_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "role": self.role.value,
            "schema_id": self.schema_id,
            "domain_tag": self.domain_tag,
            "content_id": self.content_id,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "SelectedRouteBundleEntryV1":
        require_exact_fields(document, {
            "schema", "schema_version", "role", "schema_id", "domain_tag",
            "content_id", "relative_path", "sha256", "size_bytes",
        }, context="selected-route bundle entry")
        if document["schema"] != BUNDLE_ENTRY_SCHEMA or document["schema_version"] != SCHEMA_VERSION:
            raise Phase3ESelectedRouteBundleV1Error("entry schema mismatch")
        return cls(document["role"], document["schema_id"], document["domain_tag"], document["content_id"], document["relative_path"], document["sha256"], document["size_bytes"])


_IDENTITY_NAMES = tuple(sorted((
    "access_event_log_id", "aggregate_marginal_work_vector_id",
    "closure_id", "construction_receipt_id", "decision_point_id",
    "delegate_work_vector_id", "executor_recipe_id",
    "failed_prefix_accounting_authority_id", "fallback_cardinality_id",
    "fallback_upper_id", "freeze_attestation_id", "local_cardinality_id",
    "local_upper_id", "logical_occurrence_id", "merged_route_work_vector_id",
    "model_only_execution_id", "model_only_request_id", "model_only_result_id",
    "occurrence_work_aggregate_id", "route_attempt_id", "route_context_id",
    "route_decision_id", "runtime_factory_cardinality_id", "runtime_tree_id",
    "preparation_accounting_id", "preparation_aggregate_work_vector_id",
    "preparation_incremental_work_vector_id", "preparation_trace_id",
    "terminal_artifact_id", "transaction_id",
)))


@dataclass(frozen=True, slots=True)
class SelectedRouteBundleManifestV1:
    source_bundle_sha256: str
    source_manifest_sha256: str
    source_lease_id: str
    identities: tuple[tuple[str, str], ...]
    entries: tuple[SelectedRouteBundleEntryV1, ...]
    query_key: str = LOCAL_QUERY_KEY
    bundle_scope: str = BUNDLE_SCOPE
    verification_status: str = VERIFICATION_STATUS
    semantic_certificate_status: str = SEMANTIC_CERTIFICATE_STATUS
    remaining_blockers: tuple[str, ...] = REMAINING_BLOCKERS
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    scalar_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        for name in ("source_bundle_sha256", "source_manifest_sha256", "source_lease_id"):
            _cid(getattr(self, name), name)
        if tuple(name for name, _value in self.identities) != _IDENTITY_NAMES:
            raise Phase3ESelectedRouteBundleV1Error("manifest identity chain is incomplete or unordered")
        for name, value in self.identities:
            _cid(value, name)
        if tuple(sorted(self.entries, key=lambda row: row.relative_path)) != self.entries:
            raise Phase3ESelectedRouteBundleV1Error("entries must be path sorted")
        if len(self.entries) != len(_ROLE_SPECS) or {row.role for row in self.entries} != set(_ROLE_SPECS):
            raise Phase3ESelectedRouteBundleV1Error("manifest roles are missing, duplicated, or extra")
        if len({row.relative_path for row in self.entries}) != len(self.entries):
            raise Phase3ESelectedRouteBundleV1Error("manifest repeats an entry path")
        if (
            self.query_key != LOCAL_QUERY_KEY
            or self.bundle_scope != BUNDLE_SCOPE
            or self.verification_status != VERIFICATION_STATUS
            or self.semantic_certificate_status != SEMANTIC_CERTIFICATE_STATUS
            or self.remaining_blockers != REMAINING_BLOCKERS
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.scalar_gate_status != "NOT_RUN"
        ):
            raise Phase3ESelectedRouteBundleV1Error("bundle status, blocker, or Gate lock changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": BUNDLE_MANIFEST_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "source_bundle_sha256": self.source_bundle_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_lease_id": self.source_lease_id,
            "query_key": self.query_key,
            "bundle_scope": self.bundle_scope,
            "verification_status": self.verification_status,
            "semantic_certificate_status": self.semantic_certificate_status,
            "remaining_blockers": list(self.remaining_blockers),
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "scalar_gate_status": self.scalar_gate_status,
            "identities": [{"name": name, "content_id": value} for name, value in self.identities],
            "entries": [row.to_dict() for row in self.entries],
        }

    @property
    def selected_route_bundle_manifest_id(self) -> str:
        return content_id(SELECTED_ROUTE_BUNDLE_MANIFEST_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "selected_route_bundle_manifest_id": self.selected_route_bundle_manifest_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "SelectedRouteBundleManifestV1":
        require_exact_fields(document, {
            "schema", "schema_version", "source_bundle_sha256", "source_manifest_sha256",
            "source_lease_id", "query_key", "bundle_scope", "verification_status",
            "semantic_certificate_status", "remaining_blockers", "official_execution_allowed",
            "official_scalar_cost", "official_N_break_even", "scalar_gate_status",
            "identities", "entries", "selected_route_bundle_manifest_id",
        }, context="selected-route bundle manifest")
        if document["schema"] != BUNDLE_MANIFEST_SCHEMA or document["schema_version"] != SCHEMA_VERSION or type(document["identities"]) is not list or type(document["entries"]) is not list or type(document["remaining_blockers"]) is not list:
            raise Phase3ESelectedRouteBundleV1Error("manifest schema mismatch")
        identities: list[tuple[str, str]] = []
        for row in document["identities"]:
            require_exact_fields(row, {"name", "content_id"}, context="manifest identity")
            identities.append((row["name"], row["content_id"]))
        result = cls(
            document["source_bundle_sha256"], document["source_manifest_sha256"], document["source_lease_id"],
            tuple(identities), tuple(SelectedRouteBundleEntryV1.from_dict(row) for row in document["entries"]),
            document["query_key"], document["bundle_scope"], document["verification_status"],
            document["semantic_certificate_status"], tuple(document["remaining_blockers"]),
            document["official_execution_allowed"], document["official_scalar_cost"],
            document["official_N_break_even"], document["scalar_gate_status"],
        )
        if document["selected_route_bundle_manifest_id"] != result.selected_route_bundle_manifest_id:
            raise Phase3ESelectedRouteBundleV1Error("manifest content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class VerifiedSelectedRouteBundleV1:
    """Pure-data result.  It intentionally carries no execution authority."""

    manifest: SelectedRouteBundleManifestV1
    route_decision: MarginalRouteDecisionV1
    terminal: TerminalArtifactV1
    occurrence_work: Phase3EOccurrenceWorkAggregateV1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verified_selected_route_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "selected_route_bundle_manifest_id": self.manifest.selected_route_bundle_manifest_id,
            "route_decision_id": self.route_decision.route_decision_id,
            "terminal_artifact_id": self.terminal.terminal_artifact_id,
            "occurrence_work_aggregate_id": self.occurrence_work.phase3e_occurrence_work_aggregate_id,
            "verification_status": VERIFICATION_STATUS,
            "semantic_certificate_status": SEMANTIC_CERTIFICATE_STATUS,
            "remaining_blockers": list(REMAINING_BLOCKERS),
            "official_execution_allowed": False,
        }


def _closure_document(closure: ModelFailureOccurrenceClosureV1) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.model_failure_occurrence_closure.v1",
        "status": closure.status,
        "source_accounting_status": closure.source_accounting_status,
        "accounting_blockers": list(closure.accounting_blockers),
        "official_execution_allowed": False,
        "counter_completeness_certified": False,
        "failed_prefix_accounting_authority_id": closure.prepared_consumer.failed_prefix_authority.failed_prefix_accounting_authority_id,
        "route_decision_id": closure.prepared_consumer.route_authorities.decision.route_decision_id,
        "closure_code": closure.occurrence.closure_code.value,
        "occurrence_work_aggregate_id": closure.occurrence.occurrence_work.phase3e_occurrence_work_aggregate_id,
        "component_ref_ids": [row.occurrence_work_component_ref_id for row in closure.occurrence.occurrence_work.component_refs],
        "terminal_id": closure.authoritative_terminal_id,
    }
    return {**payload, "model_failure_occurrence_closure_id": content_id(MODEL_FAILURE_OCCURRENCE_CLOSURE_DOMAIN, payload)}


def _entry(role: SelectedRouteBundleRoleV1, content_identity: str, raw: bytes) -> SelectedRouteBundleEntryV1:
    spec = _ROLE_SPECS[role]
    return SelectedRouteBundleEntryV1(role, spec.schema_id, spec.domain_tag, content_identity, spec.path, _sha256(raw), len(raw))


def _documents_from_closure(
    request: ModelOnlyExecutionRequestV1,
    closure: ModelFailureOccurrenceClosureV1,
) -> tuple[dict[SelectedRouteBundleRoleV1, dict[str, Any]], dict[SelectedRouteBundleRoleV1, str], dict[str, str]]:
    prepared = closure.prepared_consumer
    prefix = prepared.failed_prefix_authority
    artifact = prefix.execution.artifact
    route = prepared.route_authorities
    preparation = prepared.route_preparation_accounting
    run = closure.occurrence.decision_runs[0]
    semantic = run.route_execution.semantic_execution
    if type(semantic) is not TrustedLocalExecutionV1 or semantic.post_audit is None:
        raise Phase3ESelectedRouteBundleV1Error("bundle requires a certified LOCAL execution")
    construction = run.route_execution.sealed_executor_construction_accounting
    delegate = run.route_execution.delegate_execution_work
    merge_proof = run.route_execution.sealed_executor_execution_merge_proof
    common = run.common_two_stage_accounting
    if (
        type(construction) is not SealedExecutorConstructionAccountingV1
        or type(delegate) is not RecordedWorkV1
        or type(merge_proof) is not SealedExecutorExecutionMergeProofV1
        or common is None
        or closure.terminal_artifact is None
    ):
        raise Phase3ESelectedRouteBundleV1Error("closure lacks its sealed accounting or terminal chain")
    local_cap = RouteCapProfileV1()
    fallback_cap = official_safe_chain_fallback_cap_profile_v1()
    if (
        route.transaction.route_cap_profile_id != local_cap.route_cap_profile_id
        or route.local_formula.route_cap_profile_id
        != local_cap.route_cap_profile_id
        or route.fallback_formula.route_cap_profile_id
        != fallback_cap.ground_fallback_cap_profile_id
    ):
        raise Phase3ESelectedRouteBundleV1Error(
            "closure does not retain the exact frozen H2 route-cap bindings"
        )
    occurrence_raw_work_ids = {
        raw.work_vector_id
        for component in closure.occurrence.occurrence_work.component_refs
        for raw in component.raw_work_refs
    }
    if (
        preparation.source_prefix is not prefix.aggregate_work
        or preparation.incremental_work is not preparation.preparation_work
        or preparation.occurrence_charge_status
        != PREPARATION_OCCURRENCE_CHARGE_STATUS
        or preparation.trace.post_decision_point_component is not True
        or run.common_prefix_work is not prefix.aggregate_work
        or common.core.core_work_vector_id
        != prefix.aggregate_work.work_vector.work_vector_id
        or preparation.incremental_work.work_vector.work_vector_id
        in occurrence_raw_work_ids
        or preparation.aggregate_work.work_vector.work_vector_id
        in occurrence_raw_work_ids
    ):
        raise Phase3ESelectedRouteBundleV1Error(
            "preparation work was hidden in the common core or occurrence charge"
        )

    work = lambda value, scope: recorded_work_to_dict_v1(value, expected_scope=scope)
    documents: dict[SelectedRouteBundleRoleV1, dict[str, Any]] = {
        SelectedRouteBundleRoleV1.MODEL_ONLY_REQUEST: request.to_dict(),
        SelectedRouteBundleRoleV1.MODEL_ONLY_EXECUTION: artifact.to_dict(),
        SelectedRouteBundleRoleV1.MODEL_ONLY_RESULT: artifact.model_only_result.to_dict(),
        SelectedRouteBundleRoleV1.FAILED_PREFIX_AUTHORITY: prefix.metadata(),
        SelectedRouteBundleRoleV1.FAILED_PREFIX_WORK: work(prefix.aggregate_work, ActualWorkScope.COMMON_PREFIX),
        SelectedRouteBundleRoleV1.PREPARATION_TRACE: preparation.trace.to_dict(),
        SelectedRouteBundleRoleV1.PREPARATION_INCREMENTAL_WORK: work(preparation.incremental_work, ActualWorkScope.COMMON_PREFIX),
        SelectedRouteBundleRoleV1.PREPARATION_AGGREGATE_WORK: work(preparation.aggregate_work, ActualWorkScope.COMMON_PREFIX),
        SelectedRouteBundleRoleV1.PREPARATION_ACCOUNTING: preparation.metadata(),
        SelectedRouteBundleRoleV1.ROUTE_CONTEXT: prepared.prepared.context.to_dict(),
        SelectedRouteBundleRoleV1.LOGICAL_OCCURRENCE: artifact.model_only_result.logical_occurrence.to_dict(),
        SelectedRouteBundleRoleV1.ROUTE_ATTEMPT: artifact.model_only_result.route_attempt.to_dict(),
        SelectedRouteBundleRoleV1.RUNTIME_MANIFEST: prepared.runtime_manifest.to_dict(),
        SelectedRouteBundleRoleV1.RUNTIME_CARDINALITY: prepared.runtime_cardinality.to_dict(),
        SelectedRouteBundleRoleV1.EXECUTOR_RECIPE: prepared.selected_recipe.to_dict(),
        SelectedRouteBundleRoleV1.FRONTIER: route.frontier.to_dict(),
        SelectedRouteBundleRoleV1.CAUSAL: route.causal.to_dict(),
        SelectedRouteBundleRoleV1.DECISION_POINT: prepared.prepared.decision_point.to_dict(),
        SelectedRouteBundleRoleV1.TRANSACTION: route.transaction.to_dict(),
        SelectedRouteBundleRoleV1.LOCAL_CAP: local_cap.to_dict(),
        SelectedRouteBundleRoleV1.LOCAL_SOURCE: route.local_source.to_dict(),
        SelectedRouteBundleRoleV1.LOCAL_BOUND: route.local_bound.to_dict(),
        SelectedRouteBundleRoleV1.LOCAL_CARDINALITY: route.local_cardinality.to_dict(),
        SelectedRouteBundleRoleV1.LOCAL_FORMULA: route.local_formula.to_dict(),
        SelectedRouteBundleRoleV1.LOCAL_UPPER: route.local_upper.to_dict(),
        SelectedRouteBundleRoleV1.FALLBACK_CAP: fallback_cap.to_dict(),
        SelectedRouteBundleRoleV1.FALLBACK_SOURCE: route.fallback_source.to_dict(),
        SelectedRouteBundleRoleV1.FALLBACK_BOUND: route.fallback_bound.to_dict(),
        SelectedRouteBundleRoleV1.FALLBACK_CARDINALITY: route.fallback_cardinality.to_dict(),
        SelectedRouteBundleRoleV1.FALLBACK_FORMULA: route.fallback_formula.to_dict(),
        SelectedRouteBundleRoleV1.FALLBACK_UPPER: route.fallback_upper.to_dict(),
        SelectedRouteBundleRoleV1.ROUTE_DECISION: route.decision.to_dict(),
        SelectedRouteBundleRoleV1.ACCESS_LOG: run.access_log.to_dict(),
        SelectedRouteBundleRoleV1.FREEZE: run.freeze_attestation.to_dict(),
        SelectedRouteBundleRoleV1.COMMON_CORE: common.core.to_dict(),
        SelectedRouteBundleRoleV1.COMMON_CORE_WORK: work(run.common_prefix_work, ActualWorkScope.COMMON_PREFIX),
        SelectedRouteBundleRoleV1.COMMON_PLAN: common.plan.to_dict(),
        SelectedRouteBundleRoleV1.COMMON_SUFFIX_WORK: work(common.verification_suffix, ActualWorkScope.COMMON_PREFIX),
        SelectedRouteBundleRoleV1.COMMON_AGGREGATE_WORK: work(common.aggregate_work, ActualWorkScope.COMMON_PREFIX),
        SelectedRouteBundleRoleV1.COMMON_AGGREGATE_META: common.aggregate.to_dict(),
        SelectedRouteBundleRoleV1.COMMON_RECEIPT: common.receipt.to_dict(),
        SelectedRouteBundleRoleV1.CONSTRUCTION_RECEIPT: construction.receipt.to_dict(),
        SelectedRouteBundleRoleV1.FACTORY_WORK: work(construction.recorded_work, ActualWorkScope.MARGINAL_ROUTE_EXECUTION),
        SelectedRouteBundleRoleV1.DELEGATE_WORK: work(delegate, ActualWorkScope.MARGINAL_ROUTE_EXECUTION),
        SelectedRouteBundleRoleV1.MERGED_ROUTE_WORK: work(run.selected_route_work, ActualWorkScope.MARGINAL_ROUTE_EXECUTION),
        SelectedRouteBundleRoleV1.EXECUTION_MERGE_PROOF: merge_proof.to_dict(),
        SelectedRouteBundleRoleV1.LOCAL_RESULT: semantic.local_result.to_dict(),
        SelectedRouteBundleRoleV1.POST_AUDIT: semantic.post_audit.to_dict(),
        SelectedRouteBundleRoleV1.VERIFICATION_SUFFIX_WORK: work(run.verification_suffix_work, ActualWorkScope.MARGINAL_ROUTE_VERIFICATION),
        SelectedRouteBundleRoleV1.MARGINAL_AGGREGATE_WORK: {
            **work(RecordedWorkV1(
                run.aggregate_marginal_work.aggregate_work_vector,
                    NativeZeroAttestationV1.derive(run.aggregate_marginal_work.aggregate_work_vector, official_counter_registry_v1()),
                    ReconciliationProofV1.derive(run.aggregate_marginal_work.aggregate_work_vector, official_counter_registry_v1()),
                run.aggregate_marginal_work.aggregate_comparison_vector,
                run.aggregate_marginal_work.aggregate_projection_proof,
            ), ActualWorkScope.MARGINAL_ROUTE_AGGREGATE)
        },
        SelectedRouteBundleRoleV1.MARGINAL_AGGREGATION_PROOF: run.aggregate_marginal_work.aggregation_proof.to_dict(),
        SelectedRouteBundleRoleV1.OCCURRENCE_WORK_AGGREGATE: closure.occurrence.occurrence_work.to_dict(),
        SelectedRouteBundleRoleV1.TERMINAL: closure.terminal_artifact.to_dict(),
        SelectedRouteBundleRoleV1.CLOSURE_SUMMARY: _closure_document(closure),
    }
    identities: dict[SelectedRouteBundleRoleV1, str] = {}
    for role, document in documents.items():
        if role in {
            SelectedRouteBundleRoleV1.FAILED_PREFIX_WORK,
            SelectedRouteBundleRoleV1.PREPARATION_INCREMENTAL_WORK,
            SelectedRouteBundleRoleV1.PREPARATION_AGGREGATE_WORK,
            SelectedRouteBundleRoleV1.COMMON_CORE_WORK, SelectedRouteBundleRoleV1.COMMON_SUFFIX_WORK,
            SelectedRouteBundleRoleV1.COMMON_AGGREGATE_WORK, SelectedRouteBundleRoleV1.FACTORY_WORK,
            SelectedRouteBundleRoleV1.DELEGATE_WORK, SelectedRouteBundleRoleV1.MERGED_ROUTE_WORK,
            SelectedRouteBundleRoleV1.VERIFICATION_SUFFIX_WORK, SelectedRouteBundleRoleV1.MARGINAL_AGGREGATE_WORK,
        }:
            identities[role] = document["recorded_work_transport_id"]
        else:
            candidates = [key for key in document if key.endswith("_id") and key not in {"schema_id"}]
            # Role documents have one authoritative terminal/content identity;
            # choose the registered role-specific final key below where needed.
            key_by_role = {
                SelectedRouteBundleRoleV1.MODEL_ONLY_REQUEST: "request_id",
                SelectedRouteBundleRoleV1.MODEL_ONLY_EXECUTION: "operational_execution_id",
                SelectedRouteBundleRoleV1.MODEL_ONLY_RESULT: "result_id",
                SelectedRouteBundleRoleV1.FAILED_PREFIX_AUTHORITY: "failed_prefix_accounting_authority_id",
                SelectedRouteBundleRoleV1.PREPARATION_TRACE: "model_failure_preparation_trace_id",
                SelectedRouteBundleRoleV1.PREPARATION_ACCOUNTING: "model_failure_preparation_accounting_id",
                SelectedRouteBundleRoleV1.ROUTE_CONTEXT: "route_decision_context_id",
                SelectedRouteBundleRoleV1.LOGICAL_OCCURRENCE: "logical_occurrence_id",
                SelectedRouteBundleRoleV1.ROUTE_ATTEMPT: "route_attempt_id",
                SelectedRouteBundleRoleV1.RUNTIME_MANIFEST: "runtime_tree_id",
                SelectedRouteBundleRoleV1.RUNTIME_CARDINALITY: "runtime_factory_cardinality_id",
                SelectedRouteBundleRoleV1.EXECUTOR_RECIPE: "executor_recipe_id",
                SelectedRouteBundleRoleV1.FRONTIER: "frontier_snapshot_id",
                SelectedRouteBundleRoleV1.CAUSAL: "causal_evidence_id",
                SelectedRouteBundleRoleV1.DECISION_POINT: "decision_point_id",
                SelectedRouteBundleRoleV1.TRANSACTION: "transaction_id",
                SelectedRouteBundleRoleV1.LOCAL_CAP: "route_cap_profile_id",
                SelectedRouteBundleRoleV1.LOCAL_SOURCE: "source_artifact_id",
                SelectedRouteBundleRoleV1.LOCAL_BOUND: "local_cardinality_bound_id",
                SelectedRouteBundleRoleV1.LOCAL_CARDINALITY: "cardinality_evidence_id",
                SelectedRouteBundleRoleV1.LOCAL_FORMULA: "formula_id",
                SelectedRouteBundleRoleV1.LOCAL_UPPER: "route_upper_bound_envelope_id",
                SelectedRouteBundleRoleV1.FALLBACK_CAP: "ground_fallback_cap_profile_id",
                SelectedRouteBundleRoleV1.FALLBACK_SOURCE: "source_artifact_id",
                SelectedRouteBundleRoleV1.FALLBACK_BOUND: "ground_fallback_cardinality_bound_id",
                SelectedRouteBundleRoleV1.FALLBACK_CARDINALITY: "cardinality_evidence_id",
                SelectedRouteBundleRoleV1.FALLBACK_FORMULA: "formula_id",
                SelectedRouteBundleRoleV1.FALLBACK_UPPER: "route_upper_bound_envelope_id",
                SelectedRouteBundleRoleV1.ROUTE_DECISION: "route_decision_id",
                SelectedRouteBundleRoleV1.ACCESS_LOG: "access_event_log_id",
                SelectedRouteBundleRoleV1.FREEZE: "route_decision_freeze_attestation_id",
                SelectedRouteBundleRoleV1.COMMON_CORE: "accounting_core_seal_id",
                SelectedRouteBundleRoleV1.COMMON_PLAN: "verification_charge_plan_id",
                SelectedRouteBundleRoleV1.COMMON_AGGREGATE_META: "two_stage_work_aggregate_id",
                SelectedRouteBundleRoleV1.COMMON_RECEIPT: "verification_charge_receipt_id",
                SelectedRouteBundleRoleV1.CONSTRUCTION_RECEIPT: "sealed_executor_construction_receipt_id",
                SelectedRouteBundleRoleV1.EXECUTION_MERGE_PROOF: "sealed_executor_execution_merge_proof_id",
                SelectedRouteBundleRoleV1.LOCAL_RESULT: "local_transaction_result_id",
                SelectedRouteBundleRoleV1.POST_AUDIT: "post_audit_certificate_id",
                SelectedRouteBundleRoleV1.MARGINAL_AGGREGATION_PROOF: "marginal_work_aggregation_proof_id",
                SelectedRouteBundleRoleV1.OCCURRENCE_WORK_AGGREGATE: "phase3e_occurrence_work_aggregate_id",
                SelectedRouteBundleRoleV1.TERMINAL: "terminal_artifact_id",
                SelectedRouteBundleRoleV1.CLOSURE_SUMMARY: "model_failure_occurrence_closure_id",
            }[role]
            if key_by_role not in document:
                raise Phase3ESelectedRouteBundleV1Error(f"{role.value} lacks {key_by_role}; candidates={candidates}")
            identities[role] = document[key_by_role]

    identity_chain = {
        "access_event_log_id": run.access_log.access_event_log_id,
        "aggregate_marginal_work_vector_id": run.aggregate_marginal_work.aggregate_work_vector.work_vector_id,
        "closure_id": closure.model_failure_occurrence_closure_id,
        "construction_receipt_id": construction.receipt.sealed_executor_construction_receipt_id,
        "decision_point_id": prepared.prepared.decision_point.decision_point_id,
        "delegate_work_vector_id": delegate.work_vector.work_vector_id,
        "executor_recipe_id": prepared.selected_recipe.executor_recipe_id,
        "failed_prefix_accounting_authority_id": prefix.failed_prefix_accounting_authority_id,
        "fallback_cardinality_id": route.fallback_cardinality.cardinality_evidence_id,
        "fallback_upper_id": route.fallback_upper.route_upper_bound_envelope_id,
        "freeze_attestation_id": run.freeze_attestation.route_decision_freeze_attestation_id,
        "local_cardinality_id": route.local_cardinality.cardinality_evidence_id,
        "local_upper_id": route.local_upper.route_upper_bound_envelope_id,
        "logical_occurrence_id": prepared.prepared.context.logical_occurrence_id,
        "merged_route_work_vector_id": run.selected_route_work.work_vector.work_vector_id,
        "model_only_execution_id": artifact.operational_execution_id,
        "model_only_request_id": request.request_id,
        "model_only_result_id": artifact.model_only_result.result_id,
        "occurrence_work_aggregate_id": closure.occurrence.occurrence_work.phase3e_occurrence_work_aggregate_id,
        "preparation_accounting_id": preparation.model_failure_preparation_accounting_id,
        "preparation_aggregate_work_vector_id": preparation.aggregate_work.work_vector.work_vector_id,
        "preparation_incremental_work_vector_id": preparation.incremental_work.work_vector.work_vector_id,
        "preparation_trace_id": preparation.trace.model_failure_preparation_trace_id,
        "route_attempt_id": prepared.prepared.context.route_attempt_id,
        "route_context_id": prepared.prepared.context.route_decision_context_id,
        "route_decision_id": route.decision.route_decision_id,
        "runtime_factory_cardinality_id": prepared.runtime_cardinality.runtime_factory_cardinality_id,
        "runtime_tree_id": prepared.runtime_manifest.runtime_tree_id,
        "terminal_artifact_id": closure.terminal_artifact.terminal_artifact_id,
        "transaction_id": route.transaction.transaction_id,
    }
    return documents, identities, identity_chain


def write_h2_model_failure_local_closure_bundle_v1(
    output_dir: str | Path,
    *,
    source_bundle: str | Path,
    request: ModelOnlyExecutionRequestV1,
    closure: ModelFailureOccurrenceClosureV1,
) -> SelectedRouteBundleManifestV1:
    """Write a complete selected-route transport from one live closure."""

    retained = require_model_failure_occurrence_closure_v1(closure)
    if retained.occurrence.closure_code is not OccurrenceClosureCodeV1.LOCAL_GROUND_RECOVERY:
        raise Phase3ESelectedRouteBundleV1Error("only certified LOCAL closure is supported")
    if type(request) is not ModelOnlyExecutionRequestV1:
        raise Phase3ESelectedRouteBundleV1Error("writer requires a typed model-only request")
    source = load_phase3c_model_source_v1(source_bundle, query_key=LOCAL_QUERY_KEY)
    artifact = verify_model_only_failed_prefix_artifact_v1(
        retained.prepared_consumer.failed_prefix_authority.execution.to_dict(),
        request=request,
        source=source,
    )
    if artifact.request_id != request.request_id:
        raise Phase3ESelectedRouteBundleV1Error("request differs from retained prefix")
    documents, identities, identity_chain = _documents_from_closure(request, retained)
    raw_by_role = {role: canonical_json_bytes(document) for role, document in documents.items()}
    entries = tuple(sorted((_entry(role, identities[role], raw) for role, raw in raw_by_role.items()), key=lambda row: row.relative_path))
    lease = request.source_lease
    manifest = SelectedRouteBundleManifestV1(
        lease.source_bundle_sha256,
        lease.source_manifest_sha256,
        lease.source_lease_id,
        tuple(sorted(identity_chain.items())),
        entries,
    )
    root = Path(output_dir)
    if root.exists():
        if root.is_symlink() or not root.is_dir() or any(root.iterdir()):
            raise Phase3ESelectedRouteBundleV1Error("output directory must be absent or empty and real")
    else:
        root.mkdir(parents=True)
    for entry in entries:
        path = root / entry.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw_by_role[entry.role])
    manifest_raw = canonical_json_bytes(manifest.to_dict())
    (root / MANIFEST_FILENAME).write_bytes(manifest_raw)
    (root / MANIFEST_CHECKSUM_FILENAME).write_text(f"{_sha256(manifest_raw)}  {MANIFEST_FILENAME}\n", encoding="ascii")
    return manifest


def _run_descriptor_read_test_hook_v1(
    stage: str,
    *,
    path: Path,
    relative: str,
    descriptor: int,
) -> None:
    """Provide a deterministic race injection point for security tests only."""

    hook = _DESCRIPTOR_READ_TEST_HOOK_V1
    if hook is not None:
        hook(stage, path, relative, descriptor)


def _descriptor_metadata_v1(metadata: os.stat_result) -> tuple[int, ...]:
    """Return file metadata that must remain stable across a pinned read."""

    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _open_pinned_parent_v1(root: Path, safe: str) -> tuple[int, str]:
    """Open every parent directory without following a symbolic link."""

    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory is None:
        raise Phase3ESelectedRouteBundleV1Error(
            "descriptor-pinned bundle reads require O_NOFOLLOW and O_DIRECTORY"
        )
    flags = os.O_RDONLY | os.O_CLOEXEC | nofollow | directory
    try:
        parent_fd = os.open(root, flags)
    except OSError as error:
        raise Phase3ESelectedRouteBundleV1Error(
            "bundle root could not be securely opened"
        ) from error
    parts = safe.split("/")
    try:
        for part in parts[:-1]:
            child_fd = os.open(part, flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = child_fd
    except OSError as error:
        os.close(parent_fd)
        raise Phase3ESelectedRouteBundleV1Error(
            f"bundle parent is missing, replaced, or not a real directory: {safe}"
        ) from error
    return parent_fd, parts[-1]


def _read_regular(root: Path, relative: str) -> bytes:
    """Read one exact regular file through a pinned, no-follow descriptor."""

    safe = _safe_relative_path(relative)
    path = root / safe
    parent_fd, leaf = _open_pinned_parent_v1(root, safe)
    descriptor = -1
    try:
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
        try:
            descriptor = os.open(leaf, flags, dir_fd=parent_fd)
        except OSError as error:
            raise Phase3ESelectedRouteBundleV1Error(
                f"bundle file is missing, replaced, or not regular: {safe}"
            ) from error

        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink < 1:
            raise Phase3ESelectedRouteBundleV1Error(
                f"bundle file is not a linked regular file: {safe}"
            )
        if before.st_size > _MAX_DOCUMENT_BYTES:
            raise Phase3ESelectedRouteBundleV1Error(
                f"bundle file exceeds cap: {safe}"
            )

        _run_descriptor_read_test_hook_v1(
            "after_initial_fstat",
            path=path,
            relative=safe,
            descriptor=descriptor,
        )
        remaining = before.st_size
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise Phase3ESelectedRouteBundleV1Error(
                    f"bundle file was truncated during pinned read: {safe}"
                )
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise Phase3ESelectedRouteBundleV1Error(
                f"bundle file grew during pinned read: {safe}"
            )
        raw = b"".join(chunks)
        _run_descriptor_read_test_hook_v1(
            "after_exact_read",
            path=path,
            relative=safe,
            descriptor=descriptor,
        )

        after = os.fstat(descriptor)
        try:
            current = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as error:
            raise Phase3ESelectedRouteBundleV1Error(
                f"bundle file was removed or replaced during pinned read: {safe}"
            ) from error
        if (
            _descriptor_metadata_v1(after) != _descriptor_metadata_v1(before)
            or not stat.S_ISREG(current.st_mode)
            or current.st_dev != before.st_dev
            or current.st_ino != before.st_ino
            or current.st_size != before.st_size
        ):
            raise Phase3ESelectedRouteBundleV1Error(
                f"bundle file changed or was replaced during pinned read: {safe}"
            )
        return raw
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_fd)


def _verify_topology(root: Path) -> None:
    expected = {MANIFEST_FILENAME, MANIFEST_CHECKSUM_FILENAME, *(spec.path for spec in _ROLE_SPECS.values())}
    observed: set[str] = set()
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(directory)
        if any((base / name).is_symlink() for name in dirnames):
            raise Phase3ESelectedRouteBundleV1Error("bundle directory symlinks are forbidden")
        for name in filenames:
            path = base / name
            if path.is_symlink() or not path.is_file():
                raise Phase3ESelectedRouteBundleV1Error("bundle contains a non-regular file")
            observed.add(path.relative_to(root).as_posix())
    if observed != expected:
        raise Phase3ESelectedRouteBundleV1Error(f"bundle topology mismatch: missing={sorted(expected-observed)}, unexpected={sorted(observed-expected)}")


def _snapshot(root: Path) -> dict[str, bytes]:
    _verify_topology(root)
    paths = (MANIFEST_FILENAME, MANIFEST_CHECKSUM_FILENAME, *(spec.path for spec in _ROLE_SPECS.values()))
    result = {path: _read_regular(root, path) for path in paths}
    _verify_topology(root)
    if any(_read_regular(root, path) != raw for path, raw in result.items()):
        raise Phase3ESelectedRouteBundleV1Error("bundle changed while acquiring read-set")
    return result


def _recheck(root: Path, snapshot: Mapping[str, bytes]) -> None:
    _verify_topology(root)
    if any(_read_regular(root, path) != raw for path, raw in snapshot.items()):
        raise Phase3ESelectedRouteBundleV1Error("bundle changed during replay")


def _reducer_values(vectors: Sequence[Sequence[tuple[str, int]]]) -> tuple[tuple[str, int], ...]:
    profile = official_comparison_profile_v1(official_counter_registry_v1())
    reducers = {row.name: row.reducer for row in profile.axes}
    values = {axis: 0 for axis in SHARED_AXES}
    for vector in vectors:
        observed = dict(vector)
        if tuple(sorted(observed)) != SHARED_AXES:
            raise Phase3ESelectedRouteBundleV1Error("comparison vector lacks exact shared axes")
        for axis in SHARED_AXES:
            values[axis] = values[axis] + observed[axis] if reducers[axis] is ReducerEnum.SUM else max(values[axis], observed[axis])
    return tuple(sorted(values.items()))


def _verify_common_merge(core: RecordedWorkV1, suffix: RecordedWorkV1, aggregate: RecordedWorkV1) -> None:
    registry = official_counter_registry_v1()
    expected: dict[str, int] = {}
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        left, right = core.work_vector.value(path), suffix.work_vector.value(path)
        expected[path] = left + right if leaf.reducer is ReducerEnum.SUM else max(left, right)
    if aggregate.work_vector.values != expected or aggregate.work_vector.subject_id != core.work_vector.subject_id or suffix.work_vector.subject_id != core.work_vector.subject_id:
        raise Phase3ESelectedRouteBundleV1Error("common-prefix reducer merge does not replay")


def _parse_closure_summary(document: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema", "status", "source_accounting_status", "accounting_blockers",
        "official_execution_allowed", "counter_completeness_certified",
        "failed_prefix_accounting_authority_id", "route_decision_id", "closure_code",
        "occurrence_work_aggregate_id", "component_ref_ids", "terminal_id",
        "model_failure_occurrence_closure_id",
    }
    require_exact_fields(document, fields, context="model-failure occurrence closure transport")
    payload = {key: document[key] for key in fields if key != "model_failure_occurrence_closure_id"}
    if document["schema"] != "acfqp.model_failure_occurrence_closure.v1" or document["status"] != MODEL_FAILURE_OCCURRENCE_STATUS or document["source_accounting_status"] != MODEL_FAILURE_CONSUMER_STATUS or document["official_execution_allowed"] is not False or document["counter_completeness_certified"] is not False or document["closure_code"] != OccurrenceClosureCodeV1.LOCAL_GROUND_RECOVERY.value or document["accounting_blockers"] != list(MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS):
        raise Phase3ESelectedRouteBundleV1Error("closure summary status or blocker lock changed")
    if document["model_failure_occurrence_closure_id"] != content_id(MODEL_FAILURE_OCCURRENCE_CLOSURE_DOMAIN, payload):
        raise Phase3ESelectedRouteBundleV1Error("closure summary content ID mismatch")
    return dict(document)


def _parse_preparation_accounting_metadata(
    document: Mapping[str, Any],
) -> dict[str, Any]:
    fields = {
        "schema",
        "trace_id",
        "source_prefix_work_vector_id",
        "preparation_work_vector_id",
        "aggregate_work_vector_id",
        "excluded_work",
        "occurrence_charge_status",
        "model_failure_preparation_accounting_id",
    }
    require_exact_fields(
        document, fields, context="model-failure preparation accounting transport"
    )
    if (
        document["schema"]
        != "acfqp.model_failure_preparation_accounting.v1"
        or type(document["excluded_work"]) is not list
        or document["excluded_work"] != list(PREPARATION_EXCLUSIONS)
        or document["occurrence_charge_status"]
        != PREPARATION_OCCURRENCE_CHARGE_STATUS
    ):
        raise Phase3ESelectedRouteBundleV1Error(
            "preparation accounting status or exclusion boundary changed"
        )
    for key in (
        "trace_id",
        "source_prefix_work_vector_id",
        "preparation_work_vector_id",
        "aggregate_work_vector_id",
        "model_failure_preparation_accounting_id",
    ):
        _cid(document[key], key)
    payload = {
        key: document[key]
        for key in fields
        if key != "model_failure_preparation_accounting_id"
    }
    if document["model_failure_preparation_accounting_id"] != content_id(
        MODEL_FAILURE_PREPARATION_ACCOUNTING_DOMAIN, payload
    ):
        raise Phase3ESelectedRouteBundleV1Error(
            "preparation accounting metadata content ID mismatch"
        )
    return dict(document)


def verify_h2_model_failure_local_closure_bundle_v1(
    bundle_dir: str | Path,
    *,
    source_bundle: str | Path,
) -> VerifiedSelectedRouteBundleV1:
    """Replay all serializable selected-route evidence without planner/J0."""

    root = Path(bundle_dir)
    if root.is_symlink() or not root.is_dir():
        raise Phase3ESelectedRouteBundleV1Error("bundle root must be a real directory")
    root = root.resolve(strict=True)
    snapshot = _snapshot(root)
    manifest_raw = snapshot[MANIFEST_FILENAME]
    if snapshot[MANIFEST_CHECKSUM_FILENAME] != f"{_sha256(manifest_raw)}  {MANIFEST_FILENAME}\n".encode("ascii"):
        raise Phase3ESelectedRouteBundleV1Error("manifest checksum mismatch")
    manifest = SelectedRouteBundleManifestV1.from_dict(_plain_object(manifest_raw, source=MANIFEST_FILENAME))
    documents: dict[SelectedRouteBundleRoleV1, dict[str, Any]] = {}
    entry_ids: dict[SelectedRouteBundleRoleV1, str] = {}
    for entry in manifest.entries:
        raw = snapshot[entry.relative_path]
        if len(raw) != entry.size_bytes or _sha256(raw) != entry.sha256:
            raise Phase3ESelectedRouteBundleV1Error(f"entry digest mismatch: {entry.relative_path}")
        document = _plain_object(raw, source=entry.relative_path)
        if document.get("schema") != entry.schema_id:
            raise Phase3ESelectedRouteBundleV1Error(f"entry schema mismatch: {entry.relative_path}")
        documents[entry.role] = document
        entry_ids[entry.role] = entry.content_id
    get = documents.__getitem__
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual_profile = official_actual_projection_profile_v1(registry, profile)
    try:
        request = parse_model_only_execution_request_v1(get(SelectedRouteBundleRoleV1.MODEL_ONLY_REQUEST))
        source = load_phase3c_model_source_v1(source_bundle, query_key=LOCAL_QUERY_KEY)
        artifact = verify_model_only_failed_prefix_artifact_v1(get(SelectedRouteBundleRoleV1.MODEL_ONLY_EXECUTION), request=request, source=source)
        preparation_trace = ModelFailurePreparationTraceV1.from_dict(
            get(SelectedRouteBundleRoleV1.PREPARATION_TRACE)
        )
        preparation_metadata = _parse_preparation_accounting_metadata(
            get(SelectedRouteBundleRoleV1.PREPARATION_ACCOUNTING)
        )
        context = RouteDecisionContextV1.from_dict(get(SelectedRouteBundleRoleV1.ROUTE_CONTEXT))
        occurrence = LogicalOccurrenceV1.from_dict(get(SelectedRouteBundleRoleV1.LOGICAL_OCCURRENCE))
        attempt = RouteAttemptV1.from_dict(get(SelectedRouteBundleRoleV1.ROUTE_ATTEMPT))
        runtime_manifest = RuntimeTreeManifestV1.from_dict(get(SelectedRouteBundleRoleV1.RUNTIME_MANIFEST))
        runtime_cardinality = RuntimeFactoryCardinalityV1.from_dict(get(SelectedRouteBundleRoleV1.RUNTIME_CARDINALITY))
        recipe = ExecutorRecipeV1.from_dict(get(SelectedRouteBundleRoleV1.EXECUTOR_RECIPE))
        frontier = FrontierSnapshotV1.from_dict(get(SelectedRouteBundleRoleV1.FRONTIER))
        causal = CausalEvidenceV1.from_dict(get(SelectedRouteBundleRoleV1.CAUSAL))
        point = DecisionPointV1.from_dict(get(SelectedRouteBundleRoleV1.DECISION_POINT))
        transaction = TransactionV1.from_dict(get(SelectedRouteBundleRoleV1.TRANSACTION))
        local_cap = RouteCapProfileV1.from_dict(get(SelectedRouteBundleRoleV1.LOCAL_CAP))
        local_source = SafeChainLocalPreselectionSourceV1.from_dict(get(SelectedRouteBundleRoleV1.LOCAL_SOURCE))
        local_bound = SafeChainLocalCardinalityBoundV1.from_dict(get(SelectedRouteBundleRoleV1.LOCAL_BOUND))
        local_cardinality = CardinalityEvidenceV1.from_dict(get(SelectedRouteBundleRoleV1.LOCAL_CARDINALITY))
        local_formula = RouteUpperFormulaV1.from_dict(get(SelectedRouteBundleRoleV1.LOCAL_FORMULA))
        local_upper = RouteUpperBoundEnvelopeV1.from_dict(get(SelectedRouteBundleRoleV1.LOCAL_UPPER))
        fallback_cap = GroundFallbackCapProfileV1.from_dict(get(SelectedRouteBundleRoleV1.FALLBACK_CAP))
        fallback_source = SafeChainFallbackCardinalitySourceV1.from_dict(get(SelectedRouteBundleRoleV1.FALLBACK_SOURCE))
        fallback_bound = GroundFallbackCardinalityBoundV1.from_dict(get(SelectedRouteBundleRoleV1.FALLBACK_BOUND))
        fallback_cardinality = CardinalityEvidenceV1.from_dict(get(SelectedRouteBundleRoleV1.FALLBACK_CARDINALITY))
        fallback_formula = RouteUpperFormulaV1.from_dict(get(SelectedRouteBundleRoleV1.FALLBACK_FORMULA))
        fallback_upper = RouteUpperBoundEnvelopeV1.from_dict(get(SelectedRouteBundleRoleV1.FALLBACK_UPPER))
        decision = MarginalRouteDecisionV1.from_dict(get(SelectedRouteBundleRoleV1.ROUTE_DECISION))
        access_log = AccessEventLogV1.from_dict(get(SelectedRouteBundleRoleV1.ACCESS_LOG))
        freeze = RouteDecisionFreezeAttestationV1.from_dict(get(SelectedRouteBundleRoleV1.FREEZE))
        common_core = SealedAccountingCoreV1.from_dict(get(SelectedRouteBundleRoleV1.COMMON_CORE))
        common_plan = VerificationChargePlanV1.from_dict(get(SelectedRouteBundleRoleV1.COMMON_PLAN))
        common_meta = TwoStageWorkAggregateV1.from_dict(get(SelectedRouteBundleRoleV1.COMMON_AGGREGATE_META))
        common_receipt = VerificationChargeReceiptV1.from_dict(get(SelectedRouteBundleRoleV1.COMMON_RECEIPT))
        construction_receipt = SealedExecutorConstructionReceiptV1.from_dict(get(SelectedRouteBundleRoleV1.CONSTRUCTION_RECEIPT))
        merge_proof = SealedExecutorExecutionMergeProofV1.from_dict(get(SelectedRouteBundleRoleV1.EXECUTION_MERGE_PROOF))
        local_result = LocalTransactionResultV1.from_dict(get(SelectedRouteBundleRoleV1.LOCAL_RESULT))
        post_audit = PostAuditCertificateV1.from_dict(get(SelectedRouteBundleRoleV1.POST_AUDIT))
        marginal_proof = MarginalWorkAggregationProofV1.from_dict(get(SelectedRouteBundleRoleV1.MARGINAL_AGGREGATION_PROOF))
        occurrence_work = Phase3EOccurrenceWorkAggregateV1.from_dict(get(SelectedRouteBundleRoleV1.OCCURRENCE_WORK_AGGREGATE))
        terminal = TerminalArtifactV1.from_dict(get(SelectedRouteBundleRoleV1.TERMINAL))
        closure_summary = _parse_closure_summary(get(SelectedRouteBundleRoleV1.CLOSURE_SUMMARY))
        failed_prefix_work = recorded_work_from_dict_v1(get(SelectedRouteBundleRoleV1.FAILED_PREFIX_WORK), expected_scope=ActualWorkScope.COMMON_PREFIX)
        preparation_incremental_work = recorded_work_from_dict_v1(
            get(SelectedRouteBundleRoleV1.PREPARATION_INCREMENTAL_WORK),
            expected_scope=ActualWorkScope.COMMON_PREFIX,
        )
        preparation_aggregate_work = recorded_work_from_dict_v1(
            get(SelectedRouteBundleRoleV1.PREPARATION_AGGREGATE_WORK),
            expected_scope=ActualWorkScope.COMMON_PREFIX,
        )
        common_core_work = recorded_work_from_dict_v1(get(SelectedRouteBundleRoleV1.COMMON_CORE_WORK), expected_scope=ActualWorkScope.COMMON_PREFIX)
        common_suffix = recorded_work_from_dict_v1(get(SelectedRouteBundleRoleV1.COMMON_SUFFIX_WORK), expected_scope=ActualWorkScope.COMMON_PREFIX)
        common_aggregate = recorded_work_from_dict_v1(get(SelectedRouteBundleRoleV1.COMMON_AGGREGATE_WORK), expected_scope=ActualWorkScope.COMMON_PREFIX)
        factory_work = recorded_work_from_dict_v1(get(SelectedRouteBundleRoleV1.FACTORY_WORK), expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION)
        delegate_work = recorded_work_from_dict_v1(get(SelectedRouteBundleRoleV1.DELEGATE_WORK), expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION)
        merged_work = recorded_work_from_dict_v1(get(SelectedRouteBundleRoleV1.MERGED_ROUTE_WORK), expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION)
        verification_suffix = recorded_work_from_dict_v1(get(SelectedRouteBundleRoleV1.VERIFICATION_SUFFIX_WORK), expected_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION)
        marginal_work = recorded_work_from_dict_v1(get(SelectedRouteBundleRoleV1.MARGINAL_AGGREGATE_WORK), expected_scope=ActualWorkScope.MARGINAL_ROUTE_AGGREGATE)
    except (KeyError, TypeError, ValueError, Phase3EBundleV1Error) as error:
        if isinstance(error, Phase3ESelectedRouteBundleV1Error):
            raise
        raise Phase3ESelectedRouteBundleV1Error(f"bundle typed replay failed: {error}") from error

    result = artifact.model_only_result
    if get(SelectedRouteBundleRoleV1.MODEL_ONLY_RESULT) != result.to_dict() or context != result.route_context or occurrence != result.logical_occurrence or attempt != result.route_attempt:
        raise Phase3ESelectedRouteBundleV1Error("model-only source/context chain was spliced")
    lease = request.source_lease
    if (manifest.source_bundle_sha256, manifest.source_manifest_sha256, manifest.source_lease_id) != (lease.source_bundle_sha256, lease.source_manifest_sha256, lease.source_lease_id):
        raise Phase3ESelectedRouteBundleV1Error("external source lease differs from manifest")
    prefix_metadata = get(SelectedRouteBundleRoleV1.FAILED_PREFIX_AUTHORITY)
    if prefix_metadata.get("operational_execution_id") != artifact.operational_execution_id or prefix_metadata.get("model_only_result_id") != result.result_id or prefix_metadata.get("route_decision_context_id") != context.route_decision_context_id or prefix_metadata.get("aggregate_work_vector_id") != failed_prefix_work.work_vector.work_vector_id:
        raise Phase3ESelectedRouteBundleV1Error("failed-prefix identity chain was spliced")
    prefix_payload = dict(prefix_metadata)
    claimed_prefix_id = prefix_payload.pop("failed_prefix_accounting_authority_id", None)
    if claimed_prefix_id != content_id(MODEL_ONLY_FAILED_PREFIX_ACCOUNTING_AUTHORITY_DOMAIN, prefix_payload):
        raise Phase3ESelectedRouteBundleV1Error("failed-prefix authority metadata ID mismatch")

    if runtime_cardinality != RuntimeFactoryCardinalityV1.from_manifest(runtime_manifest) or recipe.runtime_tree_id != runtime_manifest.runtime_tree_id or recipe.selected_route is not RouteSelection.LOCAL:
        raise Phase3ESelectedRouteBundleV1Error("runtime manifest/cardinality/recipe chain was spliced")
    if context.route_decision_context_id != point.route_decision_context_id or point.frontier_snapshot_id != frontier.frontier_snapshot_id or point.causal_evidence_id != causal.causal_evidence_id or transaction.decision_point_id != point.decision_point_id or transaction.frontier_snapshot_id != frontier.frontier_snapshot_id:
        raise Phase3ESelectedRouteBundleV1Error("frontier/causal/decision/transaction chain was spliced")
    if local_cap != RouteCapProfileV1() or fallback_cap != official_safe_chain_fallback_cap_profile_v1():
        raise Phase3ESelectedRouteBundleV1Error("route cap profile is not the frozen H2 profile")
    if local_formula != official_route_upper_formula_v1(RouteKind.LOCAL_ATTEMPT, registry=registry, profile=profile, cap_profile=local_cap) or fallback_formula != official_route_upper_formula_v1(RouteKind.DIRECT_FALLBACK, registry=registry, profile=profile, cap_profile=fallback_cap):
        raise Phase3ESelectedRouteBundleV1Error("route upper formula is not official")
    if (
        local_source.route_decision_context_id
        != context.route_decision_context_id
        or local_source.source_artifact_id not in local_bound.source_artifact_ids
        or local_cardinality.source_artifact_ids
        != tuple(
            sorted(
                set(local_bound.source_artifact_ids)
                | {local_bound.local_cardinality_bound_id}
            )
        )
        or fallback_source.route_decision_context_id
        != context.route_decision_context_id
        or fallback_source.source_artifact_id
        not in fallback_bound.source_artifact_ids
        or fallback_cardinality.source_artifact_ids
        != tuple(
            sorted(
                set(fallback_bound.source_artifact_ids)
                | {fallback_bound.ground_fallback_cardinality_bound_id}
            )
        )
    ):
        raise Phase3ESelectedRouteBundleV1Error("cardinality source/bound/evidence chain was spliced")
    replayed_local, _ = derive_route_upper_v1(context=context, decision_point=point, cardinality=local_cardinality, cap_profile=local_cap, registry=registry, profile=profile, formula=local_formula, transaction=transaction, causal=causal)
    replayed_fallback, _ = derive_route_upper_v1(context=context, decision_point=point, cardinality=fallback_cardinality, cap_profile=fallback_cap, registry=registry, profile=profile, formula=fallback_formula)
    if local_upper != replayed_local or fallback_upper != replayed_fallback or decision != MarginalRouteDecisionV1.select(point, fallback_upper, causal=causal, local_upper=local_upper) or decision.selected_route is not RouteSelection.LOCAL:
        raise Phase3ESelectedRouteBundleV1Error("upper arithmetic or route decision does not replay")

    replayed_preparation = derive_model_failure_preparation_accounting_v1(
        trace=preparation_trace,
        source_prefix=failed_prefix_work,
        registry=registry,
        comparison_profile=profile,
    )
    if (
        replayed_preparation.preparation_work != preparation_incremental_work
        or replayed_preparation.aggregate_work != preparation_aggregate_work
        or replayed_preparation.metadata() != preparation_metadata
        or preparation_trace.route_decision_context_id
        != context.route_decision_context_id
        or preparation_trace.route_attempt_id != context.route_attempt_id
        or preparation_trace.causal_evidence_id != causal.causal_evidence_id
        or preparation_trace.causal_candidate_count
        != causal.evaluated_candidate_count
    ):
        raise Phase3ESelectedRouteBundleV1Error(
            "preparation trace, work, metadata, or route identity does not replay"
        )
    preparation_evidence = {
        row.operation_id: row.evidence_id for row in preparation_trace.events
    }
    expected_preparation_evidence = {
        "official-accounting-profiles-validated": profile.comparison_profile_id,
        "failed-prefix-authority-validated": claimed_prefix_id,
        "runtime-input-types-validated": runtime_manifest.runtime_tree_id,
        "runtime-manifest-roundtrip-validated": runtime_manifest.runtime_tree_id,
        "runtime-cardinality-roundtrip-validated": runtime_cardinality.runtime_factory_cardinality_id,
        "runtime-manifest-cardinality-binding-validated": runtime_cardinality.runtime_factory_cardinality_id,
        "failed-query-chain-validated": result.result_id,
        "route-cap-profile-types-validated": local_cap.route_cap_profile_id,
        "protocol-step-order-validated": context.route_decision_context_id,
        "causal-frontier-derived": frontier.frontier_snapshot_id,
        "causal-evaluation-cap-checked": causal.causal_evidence_id,
        "decision-point-transaction-bound": transaction.transaction_id,
        "local-cardinality-source-derived": local_source.source_artifact_id,
        "local-cardinality-bound-cap-checked": local_bound.local_cardinality_bound_id,
        "local-cardinality-evidence-cap-checked": local_cardinality.cardinality_evidence_id,
        "local-upper-formula-bound": local_formula.formula_id,
        "local-upper-derived": local_upper.route_upper_bound_envelope_id,
        "fallback-cardinality-source-derived": fallback_source.source_artifact_id,
        "fallback-cardinality-bound-cap-checked": fallback_bound.ground_fallback_cardinality_bound_id,
        "fallback-cardinality-evidence-cap-checked": fallback_cardinality.cardinality_evidence_id,
        "fallback-upper-formula-bound": fallback_formula.formula_id,
        "fallback-upper-derived": fallback_upper.route_upper_bound_envelope_id,
        "marginal-route-decision-derived": decision.route_decision_id,
    }
    if any(
        preparation_evidence.get(operation_id) != evidence_id
        for operation_id, evidence_id in expected_preparation_evidence.items()
    ):
        raise Phase3ESelectedRouteBundleV1Error(
            "preparation event evidence was spliced from its typed artifact"
        )
    ground_binding_evidence = {
        preparation_evidence["ground-binding-authority-validated"],
        preparation_evidence["prepared-estimate-derived-from-failed-authority"],
        preparation_evidence["verified-model-estimate-binding-replayed"],
    }
    if len(ground_binding_evidence) != 1:
        raise Phase3ESelectedRouteBundleV1Error(
            "preparation ground-binding evidence is internally inconsistent"
        )

    profile_sequence = ProtocolSequenceProfileV1()
    boundary = access_log.freeze_after_sequence
    if not access_log.is_frozen or boundary is None or access_log.route_attempt_id != context.route_attempt_id or access_log.decision_point_id != point.decision_point_id or access_log.route_decision_id != decision.route_decision_id or access_log.route_decision_freeze_attestation_id != freeze.route_decision_freeze_attestation_id or freeze.route_decision_id != decision.route_decision_id or freeze.selected_route is not RouteSelection.LOCAL or freeze.protocol_sequence_profile_id != profile_sequence.protocol_sequence_profile_id or freeze.last_preselection_sequence != boundary or access_log.prefreeze_prefix().access_event_log_id != freeze.prefreeze_access_event_log_id:
        raise Phase3ESelectedRouteBundleV1Error("access/freeze topology does not replay")
    if any((event.route_scope is not AccessRouteScope.COMMON if event.sequence_number <= boundary else event.route_scope is AccessRouteScope.FALLBACK) for event in access_log.events):
        raise Phase3ESelectedRouteBundleV1Error("access log violates selected LOCAL route scope")
    for event in access_log.events:
        selected = None if event.sequence_number <= boundary else RouteSelection.LOCAL
        if _violation_reason(event, selected) is not None:
            raise Phase3ESelectedRouteBundleV1Error(
                "access log fails pure selected-route protocol replay"
            )

    _verify_common_merge(common_core_work, common_suffix, common_aggregate)
    if (
        failed_prefix_work != common_core_work
        or common_core.core_work_vector_id
        != common_core_work.work_vector.work_vector_id
        or common_plan.accounting_core_seal_id != common_core.accounting_core_seal_id
        or common_meta.core_work_vector_id
        != common_core_work.work_vector.work_vector_id
        or common_meta.verification_suffix_work_vector_id
        != common_suffix.work_vector.work_vector_id
        or common_meta.aggregate_work_vector_id
        != common_aggregate.work_vector.work_vector_id
        or common_receipt.verification_charge_plan_id
        != common_plan.verification_charge_plan_id
        or common_receipt.two_stage_work_aggregate_id
        != common_meta.two_stage_work_aggregate_id
        or common_receipt.destination_aggregate_work_vector_id
        != common_aggregate.work_vector.work_vector_id
    ):
        raise Phase3ESelectedRouteBundleV1Error("common-prefix two-stage accounting chain was spliced")

    construction = SealedExecutorConstructionAccountingV1(construction_receipt, factory_work)
    merged = MergedSealedRouteExecutionWorkV1(merged_work, merge_proof)
    verify_sealed_factory_execution_merge_v1(merged, factory_accounting=construction, delegate_work=delegate_work, registry=registry, comparison_profile=profile)
    if local_result.outcome is not LocalSolverOutcome.CANDIDATE_FOUND or post_audit.outcome is not PostAuditOutcome.CERTIFIED or local_result.work_vector_id != delegate_work.work_vector.work_vector_id or post_audit.local_transaction_result_id != local_result.local_transaction_result_id or local_result.selected_upper_id != local_upper.route_upper_bound_envelope_id or local_result.transaction_id != transaction.transaction_id or post_audit.transaction_id != transaction.transaction_id:
        raise Phase3ESelectedRouteBundleV1Error("local-result/post-audit transport chain was spliced")
    claimed_marginal = AggregatedMarginalWorkV1(marginal_work.work_vector, marginal_work.comparison_vector, marginal_work.actual_projection_proof, marginal_proof)
    verify_marginal_work_aggregate_v1(claimed_marginal, subject_id=transaction.transaction_id, route_kind=merged_work.work_vector.route_kind, execution=(merged_work.work_vector, merged_work.comparison_vector, merged_work.actual_projection_proof), verification_suffix=(verification_suffix.work_vector, verification_suffix.comparison_vector, verification_suffix.actual_projection_proof), registry=registry, comparison_profile=profile, actual_profile=actual_profile)
    if any(marginal_work.comparison_vector.value(axis) > dict(local_upper.upper_bounds)[axis] for axis in SHARED_AXES):
        raise Phase3ESelectedRouteBundleV1Error("selected route exceeds its frozen upper")

    if len(occurrence_work.component_refs) != 2 or tuple(row.component_kind for row in occurrence_work.component_refs) != (OccurrenceWorkComponentKind.COMMON_PREFIX, OccurrenceWorkComponentKind.LOCAL_TRANSACTION):
        raise Phase3ESelectedRouteBundleV1Error("occurrence component topology is not one common plus one LOCAL")
    common_ref, local_ref = occurrence_work.component_refs
    if common_ref.component_values != common_aggregate.comparison_vector.values or local_ref.component_values != marginal_work.comparison_vector.values or occurrence_work.aggregate_values != _reducer_values((common_ref.component_values, local_ref.component_values)):
        raise Phase3ESelectedRouteBundleV1Error("occurrence vector aggregation does not replay")
    if len(common_ref.raw_work_refs) != 1 or common_ref.raw_work_refs[0].evidence_kind is not OccurrenceRawEvidenceKind.TWO_STAGE_ACCOUNTED_COMMON or common_ref.raw_work_refs[0].work_vector_id != common_aggregate.work_vector.work_vector_id or common_ref.raw_work_refs[0].marginal_work_aggregation_proof_id != common_receipt.verification_charge_receipt_id or len(local_ref.raw_work_refs) != 1 or local_ref.raw_work_refs[0].evidence_kind is not OccurrenceRawEvidenceKind.AGGREGATED_MARGINAL_WORK or local_ref.raw_work_refs[0].work_vector_id != marginal_work.work_vector.work_vector_id or local_ref.raw_work_refs[0].marginal_work_aggregation_proof_id != marginal_proof.marginal_work_aggregation_proof_id:
        raise Phase3ESelectedRouteBundleV1Error("occurrence raw-work references were spliced")
    occurrence_raw_work_ids = {
        raw.work_vector_id
        for component in occurrence_work.component_refs
        for raw in component.raw_work_refs
    }
    if (
        preparation_metadata["occurrence_charge_status"]
        != PREPARATION_OCCURRENCE_CHARGE_STATUS
        or preparation_incremental_work.work_vector.work_vector_id
        in occurrence_raw_work_ids
        or preparation_aggregate_work.work_vector.work_vector_id
        in occurrence_raw_work_ids
    ):
        raise Phase3ESelectedRouteBundleV1Error(
            "retained post-core preparation was masqueraded as occurrence-charged"
        )

    if terminal.terminal_scope != "LOGICAL_OCCURRENCE" or terminal.terminal_class is not TerminalClass.PLAN_CERTIFICATE or terminal.terminal_code is not TerminalCode.LOCAL_GROUND_RECOVERY or terminal.route_decision_context_id != context.route_decision_context_id or terminal.logical_occurrence_id != context.logical_occurrence_id or terminal.route_attempt_id != context.route_attempt_id or terminal.decision_point_id != point.decision_point_id or terminal.transaction_id != transaction.transaction_id or terminal.actual_work_vector_id != marginal_work.work_vector.work_vector_id or terminal.actual_comparison_vector_id != marginal_work.comparison_vector.comparison_vector_id or terminal.actual_projection_proof_id != marginal_work.actual_projection_proof.actual_projection_proof_id or terminal.marginal_work_aggregation_proof_id != marginal_proof.marginal_work_aggregation_proof_id or terminal.route_decision_freeze_attestation_id != freeze.route_decision_freeze_attestation_id or terminal.access_event_log_id != access_log.access_event_log_id:
        raise Phase3ESelectedRouteBundleV1Error("terminal artifact topology was spliced")
    if closure_summary["source_accounting_status"] != MODEL_FAILURE_CONSUMER_STATUS or closure_summary["failed_prefix_accounting_authority_id"] != claimed_prefix_id or closure_summary["route_decision_id"] != decision.route_decision_id or closure_summary["occurrence_work_aggregate_id"] != occurrence_work.phase3e_occurrence_work_aggregate_id or closure_summary["component_ref_ids"] != [row.occurrence_work_component_ref_id for row in occurrence_work.component_refs] or closure_summary["terminal_id"] != terminal.terminal_artifact_id:
        raise Phase3ESelectedRouteBundleV1Error("closure summary topology was spliced")

    # Every typed parser above replayed its content ID.  The entry identity is
    # additionally tied to the exact authoritative key selected by the writer.
    _unused_documents, expected_ids, identity_chain = _documents_from_parsed_values(
        request=request, artifact=artifact, context=context, occurrence=occurrence,
        attempt=attempt, runtime_manifest=runtime_manifest,
        runtime_cardinality=runtime_cardinality, recipe=recipe, frontier=frontier,
        causal=causal, point=point, transaction=transaction, local_cap=local_cap,
        local_source=local_source, local_bound=local_bound,
        local_cardinality=local_cardinality, local_formula=local_formula,
        local_upper=local_upper, fallback_cap=fallback_cap,
        fallback_source=fallback_source, fallback_bound=fallback_bound,
        fallback_cardinality=fallback_cardinality, fallback_formula=fallback_formula,
        fallback_upper=fallback_upper, decision=decision, access_log=access_log,
        freeze=freeze, common_core=common_core, common_plan=common_plan,
        common_suffix=common_suffix, common_aggregate=common_aggregate,
        common_core_work=common_core_work,
        common_meta=common_meta, common_receipt=common_receipt,
        construction_receipt=construction_receipt, factory_work=factory_work,
        delegate_work=delegate_work, merged_work=merged_work,
        merge_proof=merge_proof, local_result=local_result, post_audit=post_audit,
        verification_suffix=verification_suffix, marginal_work=marginal_work,
        marginal_proof=marginal_proof, occurrence_work=occurrence_work,
        terminal=terminal, prefix_metadata=prefix_metadata,
        failed_prefix_work=failed_prefix_work,
        preparation_trace=preparation_trace,
        preparation_incremental_work=preparation_incremental_work,
        preparation_aggregate_work=preparation_aggregate_work,
        preparation_metadata=preparation_metadata,
        closure_summary=closure_summary,
    )
    if any(entry_ids[role] != expected_ids[role] for role in expected_ids):
        raise Phase3ESelectedRouteBundleV1Error("entry content identity differs from replay")
    if dict(manifest.identities) != identity_chain:
        raise Phase3ESelectedRouteBundleV1Error("manifest identity chain differs from replay")
    _recheck(root, snapshot)
    return VerifiedSelectedRouteBundleV1(manifest, decision, terminal, occurrence_work)


def _documents_from_parsed_values(**values: Any) -> tuple[dict[SelectedRouteBundleRoleV1, dict[str, Any]], dict[SelectedRouteBundleRoleV1, str], dict[str, str]]:
    """Recover role IDs after pure parsing without recreating live authorities."""

    role_values = {
        SelectedRouteBundleRoleV1.MODEL_ONLY_REQUEST: values["request"].request_id,
        SelectedRouteBundleRoleV1.MODEL_ONLY_EXECUTION: values["artifact"].operational_execution_id,
        SelectedRouteBundleRoleV1.MODEL_ONLY_RESULT: values["artifact"].model_only_result.result_id,
        SelectedRouteBundleRoleV1.FAILED_PREFIX_AUTHORITY: values["prefix_metadata"]["failed_prefix_accounting_authority_id"],
        SelectedRouteBundleRoleV1.FAILED_PREFIX_WORK: recorded_work_to_dict_v1(values["failed_prefix_work"])["recorded_work_transport_id"],
        SelectedRouteBundleRoleV1.PREPARATION_TRACE: values["preparation_trace"].model_failure_preparation_trace_id,
        SelectedRouteBundleRoleV1.PREPARATION_INCREMENTAL_WORK: recorded_work_to_dict_v1(values["preparation_incremental_work"])["recorded_work_transport_id"],
        SelectedRouteBundleRoleV1.PREPARATION_AGGREGATE_WORK: recorded_work_to_dict_v1(values["preparation_aggregate_work"])["recorded_work_transport_id"],
        SelectedRouteBundleRoleV1.PREPARATION_ACCOUNTING: values["preparation_metadata"]["model_failure_preparation_accounting_id"],
        SelectedRouteBundleRoleV1.ROUTE_CONTEXT: values["context"].route_decision_context_id,
        SelectedRouteBundleRoleV1.LOGICAL_OCCURRENCE: values["occurrence"].logical_occurrence_id,
        SelectedRouteBundleRoleV1.ROUTE_ATTEMPT: values["attempt"].route_attempt_id,
        SelectedRouteBundleRoleV1.RUNTIME_MANIFEST: values["runtime_manifest"].runtime_tree_id,
        SelectedRouteBundleRoleV1.RUNTIME_CARDINALITY: values["runtime_cardinality"].runtime_factory_cardinality_id,
        SelectedRouteBundleRoleV1.EXECUTOR_RECIPE: values["recipe"].executor_recipe_id,
        SelectedRouteBundleRoleV1.FRONTIER: values["frontier"].frontier_snapshot_id,
        SelectedRouteBundleRoleV1.CAUSAL: values["causal"].causal_evidence_id,
        SelectedRouteBundleRoleV1.DECISION_POINT: values["point"].decision_point_id,
        SelectedRouteBundleRoleV1.TRANSACTION: values["transaction"].transaction_id,
        SelectedRouteBundleRoleV1.LOCAL_CAP: values["local_cap"].route_cap_profile_id,
        SelectedRouteBundleRoleV1.LOCAL_SOURCE: values["local_source"].source_artifact_id,
        SelectedRouteBundleRoleV1.LOCAL_BOUND: values["local_bound"].local_cardinality_bound_id,
        SelectedRouteBundleRoleV1.LOCAL_CARDINALITY: values["local_cardinality"].cardinality_evidence_id,
        SelectedRouteBundleRoleV1.LOCAL_FORMULA: values["local_formula"].formula_id,
        SelectedRouteBundleRoleV1.LOCAL_UPPER: values["local_upper"].route_upper_bound_envelope_id,
        SelectedRouteBundleRoleV1.FALLBACK_CAP: values["fallback_cap"].ground_fallback_cap_profile_id,
        SelectedRouteBundleRoleV1.FALLBACK_SOURCE: values["fallback_source"].source_artifact_id,
        SelectedRouteBundleRoleV1.FALLBACK_BOUND: values["fallback_bound"].ground_fallback_cardinality_bound_id,
        SelectedRouteBundleRoleV1.FALLBACK_CARDINALITY: values["fallback_cardinality"].cardinality_evidence_id,
        SelectedRouteBundleRoleV1.FALLBACK_FORMULA: values["fallback_formula"].formula_id,
        SelectedRouteBundleRoleV1.FALLBACK_UPPER: values["fallback_upper"].route_upper_bound_envelope_id,
        SelectedRouteBundleRoleV1.ROUTE_DECISION: values["decision"].route_decision_id,
        SelectedRouteBundleRoleV1.ACCESS_LOG: values["access_log"].access_event_log_id,
        SelectedRouteBundleRoleV1.FREEZE: values["freeze"].route_decision_freeze_attestation_id,
        SelectedRouteBundleRoleV1.COMMON_CORE: values["common_core"].accounting_core_seal_id,
        SelectedRouteBundleRoleV1.COMMON_CORE_WORK: recorded_work_to_dict_v1(values["common_core_work"])["recorded_work_transport_id"],
        SelectedRouteBundleRoleV1.COMMON_PLAN: values["common_plan"].verification_charge_plan_id,
        SelectedRouteBundleRoleV1.COMMON_SUFFIX_WORK: recorded_work_to_dict_v1(values["common_suffix"])["recorded_work_transport_id"],
        SelectedRouteBundleRoleV1.COMMON_AGGREGATE_WORK: recorded_work_to_dict_v1(values["common_aggregate"])["recorded_work_transport_id"],
        SelectedRouteBundleRoleV1.COMMON_AGGREGATE_META: values["common_meta"].two_stage_work_aggregate_id,
        SelectedRouteBundleRoleV1.COMMON_RECEIPT: values["common_receipt"].verification_charge_receipt_id,
        SelectedRouteBundleRoleV1.CONSTRUCTION_RECEIPT: values["construction_receipt"].sealed_executor_construction_receipt_id,
        SelectedRouteBundleRoleV1.FACTORY_WORK: recorded_work_to_dict_v1(values["factory_work"])["recorded_work_transport_id"],
        SelectedRouteBundleRoleV1.DELEGATE_WORK: recorded_work_to_dict_v1(values["delegate_work"])["recorded_work_transport_id"],
        SelectedRouteBundleRoleV1.MERGED_ROUTE_WORK: recorded_work_to_dict_v1(values["merged_work"])["recorded_work_transport_id"],
        SelectedRouteBundleRoleV1.EXECUTION_MERGE_PROOF: values["merge_proof"].sealed_executor_execution_merge_proof_id,
        SelectedRouteBundleRoleV1.LOCAL_RESULT: values["local_result"].local_transaction_result_id,
        SelectedRouteBundleRoleV1.POST_AUDIT: values["post_audit"].post_audit_certificate_id,
        SelectedRouteBundleRoleV1.VERIFICATION_SUFFIX_WORK: recorded_work_to_dict_v1(values["verification_suffix"])["recorded_work_transport_id"],
        SelectedRouteBundleRoleV1.MARGINAL_AGGREGATE_WORK: recorded_work_to_dict_v1(values["marginal_work"])["recorded_work_transport_id"],
        SelectedRouteBundleRoleV1.MARGINAL_AGGREGATION_PROOF: values["marginal_proof"].marginal_work_aggregation_proof_id,
        SelectedRouteBundleRoleV1.OCCURRENCE_WORK_AGGREGATE: values["occurrence_work"].phase3e_occurrence_work_aggregate_id,
        SelectedRouteBundleRoleV1.TERMINAL: values["terminal"].terminal_artifact_id,
        SelectedRouteBundleRoleV1.CLOSURE_SUMMARY: values["closure_summary"]["model_failure_occurrence_closure_id"],
    }
    chain = {
        "access_event_log_id": values["access_log"].access_event_log_id,
        "aggregate_marginal_work_vector_id": values["marginal_work"].work_vector.work_vector_id,
        "closure_id": values["closure_summary"]["model_failure_occurrence_closure_id"],
        "construction_receipt_id": values["construction_receipt"].sealed_executor_construction_receipt_id,
        "decision_point_id": values["point"].decision_point_id,
        "delegate_work_vector_id": values["delegate_work"].work_vector.work_vector_id,
        "executor_recipe_id": values["recipe"].executor_recipe_id,
        "failed_prefix_accounting_authority_id": values["prefix_metadata"]["failed_prefix_accounting_authority_id"],
        "fallback_cardinality_id": values["fallback_cardinality"].cardinality_evidence_id,
        "fallback_upper_id": values["fallback_upper"].route_upper_bound_envelope_id,
        "freeze_attestation_id": values["freeze"].route_decision_freeze_attestation_id,
        "local_cardinality_id": values["local_cardinality"].cardinality_evidence_id,
        "local_upper_id": values["local_upper"].route_upper_bound_envelope_id,
        "logical_occurrence_id": values["context"].logical_occurrence_id,
        "merged_route_work_vector_id": values["merged_work"].work_vector.work_vector_id,
        "model_only_execution_id": values["artifact"].operational_execution_id,
        "model_only_request_id": values["request"].request_id,
        "model_only_result_id": values["artifact"].model_only_result.result_id,
        "occurrence_work_aggregate_id": values["occurrence_work"].phase3e_occurrence_work_aggregate_id,
        "preparation_accounting_id": values["preparation_metadata"]["model_failure_preparation_accounting_id"],
        "preparation_aggregate_work_vector_id": values["preparation_aggregate_work"].work_vector.work_vector_id,
        "preparation_incremental_work_vector_id": values["preparation_incremental_work"].work_vector.work_vector_id,
        "preparation_trace_id": values["preparation_trace"].model_failure_preparation_trace_id,
        "route_attempt_id": values["context"].route_attempt_id,
        "route_context_id": values["context"].route_decision_context_id,
        "route_decision_id": values["decision"].route_decision_id,
        "runtime_factory_cardinality_id": values["runtime_cardinality"].runtime_factory_cardinality_id,
        "runtime_tree_id": values["runtime_manifest"].runtime_tree_id,
        "terminal_artifact_id": values["terminal"].terminal_artifact_id,
        "transaction_id": values["transaction"].transaction_id,
    }
    return {}, role_values, chain


__all__ = [
    "BUNDLE_SCOPE",
    "REMAINING_BLOCKERS",
    "SEMANTIC_CERTIFICATE_STATUS",
    "VERIFICATION_STATUS",
    "Phase3ESelectedRouteBundleV1Error",
    "SelectedRouteBundleEntryV1",
    "SelectedRouteBundleManifestV1",
    "SelectedRouteBundleRoleV1",
    "VerifiedSelectedRouteBundleV1",
    "verify_h2_model_failure_local_closure_bundle_v1",
    "write_h2_model_failure_local_closure_bundle_v1",
]
