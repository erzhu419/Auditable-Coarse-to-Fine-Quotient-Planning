"""Execute one fresh-namespace query-local validation transaction.

The transaction consumes a verified PREPARED_NO_ACCESS request, creates a new
construction-only target namespace over the same deterministic private law as
the reusable BuildEpoch, rebinds every selected semantic row, freezes a signed
support discovery before access to each validation stream, executes only the
requested validation deltas, and closes/reconciles the observer.

This is an in-process construction boundary.  It proves the scientific access
ordering and exact signed draw inventory, but it is not process isolation, a
portable bundle, a rebuilt overlay, a plan certificate, or official execution.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_recovery_request_v1 as request_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_batch_native_statistical_backend_v1 as backend_v1
from acfqp import v075_k7_causal_promotion_construction_fixture_v1 as fixture_v1
from acfqp import v075_observer_signed_batch_control_authority_v2 as control_v2
from acfqp import v075_public_graph_semantics_v1 as graph_v1
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_GROUND_TRANSACTION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_NAMESPACE_BINDING_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_ROW_EXECUTION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.88"
PROFILE_KEY = "construction_k7_query_bound_ground_transaction_v1"
ENVIRONMENT_MARKER = "real-reusable-build-epoch"

NAMESPACE_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_NAMESPACE_BINDING_V1_DOMAIN
ROW_EXECUTION_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_ROW_EXECUTION_V1_DOMAIN
TRANSACTION_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_GROUND_TRANSACTION_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {NAMESPACE_DOMAIN, ROW_EXECUTION_DOMAIN, TRANSACTION_DOMAIN}
)
if len(LOCAL_DOMAINS) != 3 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound ground-transaction domains are not central")

_NAMESPACE_ISSUER = object()
_ROW_ISSUER = object()
_TRANSACTION_ISSUER = object()
_PREPARATION_ISSUER = object()


class ConstructionK7QueryBoundGroundTransactionV1Error(ValueError):
    """The query request, namespace join, or signed ground inventory changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundGroundTransactionV1Error(message)


@dataclass(frozen=True, slots=True)
class QueryBoundGroundTransactionPreparationV1:
    """Issuer-bound ground-free input frozen before acquisition begins."""

    _issuer: InitVar[object]
    request: request_v1.QueryBoundRecoveryRequestV1 = field(repr=False)
    source_model: planning_v2.V075NumericalModelV2 = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PREPARATION_ISSUER
            or type(self.request) is not request_v1.QueryBoundRecoveryRequestV1
            or type(self.source_model) is not planning_v2.V075NumericalModelV2
        ):
            _fail("query-bound transaction preparation is caller-minted")
        request_v1.require_query_bound_recovery_request_v1(self.request)
        self.source_model.__post_init__()
        if self.source_model.model_id != self.request.overlay_model_id:
            _fail("query-bound transaction preparation crossed its request")


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundGroundTransactionV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class QueryBoundNamespaceBindingV1:
    _issuer: InitVar[object]
    recovery_request_id: str
    logical_occurrence_id: str
    target_tape_namespace_id: str
    native_occurrence_id: str
    private_environment_generation_id: str
    context_id: str
    arm: str
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _NAMESPACE_ISSUER:
            _fail("query-bound namespace binding is caller-minted")
        for value, label in (
            (self.recovery_request_id, "recovery request"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.target_tape_namespace_id, "target namespace"),
            (self.native_occurrence_id, "native occurrence"),
            (self.private_environment_generation_id, "environment generation"),
            (self.context_id, "context"),
        ):
            _cid(value, label)
        if self.arm != worker_v1.V075WorkerArmV1.NO_PRIOR.value:
            _fail("query-bound namespace arm changed")
        object.__setattr__(
            self,
            "_binding_id",
            content_id(NAMESPACE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_namespace_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "recovery_request_id": self.recovery_request_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "native_occurrence_id": self.native_occurrence_id,
            "private_environment_generation_id": self.private_environment_generation_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "fresh_namespace_created_after_request_freeze": True,
            "namespace_ground_access_count_at_binding": 0,
            "construction_only": True,
            "production_authorizing": False,
            "official_execution_allowed": False,
        }

    @property
    def binding_id(self) -> str:
        current = content_id(NAMESPACE_DOMAIN, self._payload())
        if current != self._binding_id:
            _fail("query-bound namespace binding changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "namespace_binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class QueryBoundRowExecutionV1:
    _issuer: InitVar[object]
    validation_request_id: str
    numerical_row_id: str
    semantic_row_binding_id: str
    discovery_intent_id: str
    discovery_batch_id: str
    discovery_append_receipt_id: str
    support_freeze_id: str
    validation_intent_id: str
    validation_batch_id: str
    validation_append_receipt_id: str
    support_discovery_draw_count: int
    requested_validation_draw_count: int
    _execution_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROW_ISSUER:
            _fail("query-bound row execution is caller-minted")
        for value, label in (
            (self.validation_request_id, "validation request"),
            (self.numerical_row_id, "numerical row"),
            (self.semantic_row_binding_id, "semantic row binding"),
            (self.discovery_intent_id, "discovery intent"),
            (self.discovery_batch_id, "discovery batch"),
            (self.discovery_append_receipt_id, "discovery receipt"),
            (self.support_freeze_id, "support freeze"),
            (self.validation_intent_id, "validation intent"),
            (self.validation_batch_id, "validation batch"),
            (self.validation_append_receipt_id, "validation receipt"),
        ):
            _cid(value, label)
        caps = worker_v1.V075WorkerCapProfileV1()
        if (
            self.support_discovery_draw_count
            != caps.new_child_discovery_draws_per_row
            or self.requested_validation_draw_count <= 0
        ):
            _fail("query-bound row execution draw counts changed")
        object.__setattr__(
            self,
            "_execution_id",
            content_id(ROW_EXECUTION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_row_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "validation_request_id": self.validation_request_id,
            "numerical_row_id": self.numerical_row_id,
            "semantic_row_binding_id": self.semantic_row_binding_id,
            "discovery_intent_id": self.discovery_intent_id,
            "discovery_batch_id": self.discovery_batch_id,
            "discovery_append_receipt_id": self.discovery_append_receipt_id,
            "support_freeze_id": self.support_freeze_id,
            "validation_intent_id": self.validation_intent_id,
            "validation_batch_id": self.validation_batch_id,
            "validation_append_receipt_id": self.validation_append_receipt_id,
            "support_discovery_draw_count": self.support_discovery_draw_count,
            "requested_validation_draw_count": self.requested_validation_draw_count,
            "support_frozen_before_validation": True,
            "observer_signed_discovery_and_validation": True,
            "ground_access_performed": True,
        }

    @property
    def execution_id(self) -> str:
        current = content_id(ROW_EXECUTION_DOMAIN, self._payload())
        if current != self._execution_id:
            _fail("query-bound row execution changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_execution_id": self.execution_id}


@dataclass(frozen=True, slots=True)
class QueryBoundGroundTransactionV1:
    _issuer: InitVar[object]
    request: request_v1.QueryBoundRecoveryRequestV1 = field(repr=False)
    namespace_binding: QueryBoundNamespaceBindingV1
    native_occurrence: backend_v1.V075BatchNativeOccurrenceIdentityV1 = field(
        repr=False
    )
    observer_closure: control_v2.V075ControlledBatchJournalClosureV2 = field(
        repr=False
    )
    row_executions: tuple[QueryBoundRowExecutionV1, ...]
    _transaction_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _TRANSACTION_ISSUER
            or type(self.request) is not request_v1.QueryBoundRecoveryRequestV1
            or type(self.namespace_binding) is not QueryBoundNamespaceBindingV1
            or type(self.native_occurrence)
            is not backend_v1.V075BatchNativeOccurrenceIdentityV1
            or type(self.observer_closure)
            is not control_v2.V075ControlledBatchJournalClosureV2
            or type(self.row_executions) is not tuple
            or any(type(item) is not QueryBoundRowExecutionV1 for item in self.row_executions)
        ):
            _fail("query-bound ground transaction is caller-minted")
        request_v1.require_query_bound_recovery_request_v1(self.request)
        self.namespace_binding.__post_init__(_NAMESPACE_ISSUER)
        for item in self.row_executions:
            item.__post_init__(_ROW_ISSUER)
        requested = self.request.requested_rows
        if (
            self.namespace_binding.recovery_request_id != self.request.request_id
            or self.namespace_binding.logical_occurrence_id
            != self.request.logical_occurrence_id
            or self.namespace_binding.native_occurrence_id
            != self.native_occurrence.occurrence_id
            or self.namespace_binding.target_tape_namespace_id
            != self.native_occurrence.target_tape_namespace_id
            or tuple(item.validation_request_id for item in self.row_executions)
            != tuple(item.request_id for item in requested)
            or tuple(item.numerical_row_id for item in self.row_executions)
            != tuple(item.numerical_row_id for item in requested)
            or len(self.observer_closure.appends) != 2 * len(requested)
            or len(self.observer_closure.support_freezes) != len(requested)
            or self.observer_closure.reconciliation.total_accepted_draw_count
            != self.total_ground_draw_count
        ):
            _fail("query-bound transaction identity or ground inventory crossed")
        replayed = control_v2.verify_v075_controlled_batch_journal_closure_v2(
            batch_closure=self.observer_closure.batch_closure,
            heads=self.observer_closure.heads,
            appends=self.observer_closure.appends,
            control_closure=self.observer_closure.control_closure,
            support_freezes=self.observer_closure.support_freezes,
        )
        if replayed != self.observer_closure.reconciliation:
            _fail("query-bound observer closure differs from exact replay")
        object.__setattr__(
            self,
            "_transaction_id",
            content_id(TRANSACTION_DOMAIN, self._payload()),
        )

    @property
    def support_discovery_draw_count(self) -> int:
        return sum(item.support_discovery_draw_count for item in self.row_executions)

    @property
    def requested_validation_draw_count(self) -> int:
        return sum(item.requested_validation_draw_count for item in self.row_executions)

    @property
    def total_ground_draw_count(self) -> int:
        return self.support_discovery_draw_count + self.requested_validation_draw_count

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_ground_transaction.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "query_bound_recovery_request_id": self.request.request_id,
            "logical_occurrence_id": self.request.logical_occurrence_id,
            "namespace_binding_id": self.namespace_binding.binding_id,
            "target_tape_namespace_id": self.native_occurrence.target_tape_namespace_id,
            "native_occurrence_id": self.native_occurrence.occurrence_id,
            "observer_control_closure_id": self.observer_closure.control_closure.control_closure_id,
            "observer_reconciliation_id": self.observer_closure.reconciliation.reconciliation_id,
            "row_execution_ids": [item.execution_id for item in self.row_executions],
            "requested_row_count": len(self.row_executions),
            "cap_blocked_row_count": len(self.request.cap_blocked_rows),
            "support_discovery_draw_count": self.support_discovery_draw_count,
            "requested_validation_draw_count": self.requested_validation_draw_count,
            "total_ground_draw_count": self.total_ground_draw_count,
            "request_verified_before_namespace_creation": True,
            "namespace_bound_before_ground_access": True,
            "only_requested_rows_executed": True,
            "observer_closed_and_exactly_reconciled": True,
            "fresh_query_observer_namespace_handoff_present": True,
            "fresh_query_ground_recovery_executed": True,
            "portable_bundle_present": False,
            "immutable_overlay_compiled": False,
            "post_transaction_replanning_performed": False,
            "next_required_action": "COMPILE_SIGNED_BATCH_DELTAS_INTO_IMMUTABLE_OVERLAY",
            "process_isolation_provided": False,
            "construction_only": True,
            "plan_certificate_issued": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def transaction_id(self) -> str:
        current = content_id(TRANSACTION_DOMAIN, self._payload())
        if current != self._transaction_id:
            _fail("query-bound ground transaction changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "request": self.request.to_document(),
            "namespace_binding": self.namespace_binding.to_document(),
            "native_occurrence": self.native_occurrence.to_document(),
            "row_executions": [item.to_document() for item in self.row_executions],
            "observer_closure": self.observer_closure.to_document(),
            "query_bound_ground_transaction_id": self.transaction_id,
        }


def _row_binding(
    model: planning_v2.V075NumericalModelV2,
    row: planning_v2.V075NumericalRowV2,
) -> graph_v1.V075ObservationRowBindingV1:
    state = graph_v1.V075SymbolicGraphStateV1(
        model.context,
        row.source_ranks,
        False,
    )
    catalogue = graph_v1.V075LegalActionCatalogueV1(
        model.context,
        state,
        row.remaining_horizon,
        graph_v1.legal_action_triples_v1(model.context, state.ranks, state.failure),
    )
    binding = graph_v1.observation_row_binding_v1(
        model.context,
        catalogue,
        row.action,
    )
    if binding.row_binding_id != row.row_binding_id:
        _fail("query-bound numerical row changed its semantic binding")
    return binding


def prepare_query_bound_ground_transaction_v1(
    *,
    source_trace_bytes: bytes,
    request: request_v1.QueryBoundRecoveryRequestV1,
) -> QueryBoundGroundTransactionPreparationV1:
    """Replay the cached model without opening a ground namespace."""

    request = request_v1.require_query_bound_recovery_request_v1(request)
    trace = loads_canonical_json(source_trace_bytes)
    try:
        model = planning_v2.replay_v075_numerical_model_bytes_v2(
            canonical_json_bytes(
                trace["causal_recovery_chain"]["final_model_epoch"]["model"]
            )
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundGroundTransactionV1Error(
            "query-bound transaction lacks its exact cached model"
        ) from error
    if model.model_id != request.overlay_model_id:
        _fail("query-bound transaction model crossed its request")
    return QueryBoundGroundTransactionPreparationV1(
        _PREPARATION_ISSUER,
        request,
        model,
    )


def execute_prepared_query_bound_ground_transaction_v1(
    preparation: QueryBoundGroundTransactionPreparationV1,
) -> QueryBoundGroundTransactionV1:
    """Execute only the acquisition half of one frozen transaction."""

    if type(preparation) is not QueryBoundGroundTransactionPreparationV1:
        _fail("query-bound transaction preparation has a foreign type")
    preparation.__post_init__(_PREPARATION_ISSUER)
    request = preparation.request
    model = preparation.source_model
    prepared = fixture_v1.prepare_v075_k7_construction_environment_v1(
        environment_marker=ENVIRONMENT_MARKER,
        identity_marker=request.logical_occurrence_id,
    )
    contexts = tuple(
        item
        for item in prepared.namespace.family.replicate_contexts
        if item.context_id == model.context.context_id
    )
    if len(contexts) != 1 or contexts[0] != model.context:
        _fail("fresh namespace does not share the reusable model context")
    context = contexts[0]
    arm = worker_v1.V075WorkerArmV1.NO_PRIOR
    occurrence = backend_v1.freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
        namespace=prepared.namespace,
        context=context,
        arm=arm,
        occurrence_ordinal=0,
        threshold_profile=prepared.namespace.workload.threshold_profile,
        cap_profile=prepared.namespace.workload.cap_profile,
        source_prior_transport=None,
    )
    namespace_binding = QueryBoundNamespaceBindingV1(
        _NAMESPACE_ISSUER,
        request.request_id,
        request.logical_occurrence_id,
        prepared.namespace.target_tape_namespace_id,
        occurrence.occurrence_id,
        prepared.namespace.family.generation_id,
        context.context_id,
        arm.value,
    )
    controller = control_v2.open_v075_construction_controlled_private_observer_v2(
        authority=prepared.observer_open_authorization,
        namespace=prepared.namespace,
        private_salt=prepared.private_salt,
        private_environment=prepared.generated_environment.secret_laws_for_commitment(),
        observer_signer=prepared.observer_signer,
        session_external_id=request.request_id,
        occurrence_identity=occurrence,
    )
    rows_by_id = {item.row_id: item for item in model.rows}
    caps = worker_v1.V075WorkerCapProfileV1()
    executions: list[QueryBoundRowExecutionV1] = []
    for item in request.requested_rows:
        row = rows_by_id.get(item.numerical_row_id)
        if row is None or row.row_binding_id != item.semantic_row_binding_id:
            _fail("query-bound requested row is absent from cached model")
        binding = _row_binding(model, row)
        epoch = graph_v1.derive_shared_support_epoch_v1(
            namespace=prepared.namespace,
            row_binding=binding,
            epoch_index=0,
            evidence=(),
        )
        chain = graph_v1.freeze_shared_support_chain_v1(
            namespace=prepared.namespace,
            row_binding=binding,
            epochs=(epoch,),
        )
        pairing = graph_v1.freeze_five_arm_pairing_authority_v1(
            namespace=prepared.namespace,
            row_binding=binding,
            support_chain=chain,
        )
        discovery_stream = graph_v1.derive_transition_stream_identity_v1(
            pairing_authority=pairing,
            arm=arm.value,
        )
        discovery_intent = controller.prepare_batch_intent_v2(
            stream_identity=discovery_stream,
            semantic_authority_role=(
                control_v2.V075ControlledBatchSemanticAuthorityRoleV2
                .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
            ),
            semantic_authority_schema=(
                control_v2.V075ControlledBatchSemanticAuthoritySchemaV2
                .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
            ),
            semantic_artifact_id=item.request_id,
            semantic_verification_id=namespace_binding.binding_id,
            stage=control_v2.V075ControlledBatchStageV2.CHILD_DISCOVERY,
            round_index=0,
            support_freeze_id=None,
            accepted_draw_start=1,
            accepted_draw_count=caps.new_child_discovery_draws_per_row,
            accepted_draw_cap=caps.new_child_discovery_draws_per_row,
        )
        discovery = controller.execute_batch_intent_v2(discovery_intent)
        support = controller.freeze_complete_support_v2(
            discovery_append=discovery
        )
        validation_stream = controller.derive_validation_stream_v2(
            support_freeze=support
        )
        validation_intent = controller.prepare_batch_intent_v2(
            stream_identity=validation_stream,
            semantic_authority_role=(
                control_v2.V075ControlledBatchSemanticAuthorityRoleV2
                .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
            ),
            semantic_authority_schema=(
                control_v2.V075ControlledBatchSemanticAuthoritySchemaV2
                .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
            ),
            semantic_artifact_id=item.request_id,
            semantic_verification_id=namespace_binding.binding_id,
            stage=control_v2.V075ControlledBatchStageV2.CHILD_VALIDATION,
            round_index=0,
            support_freeze_id=support.freeze_id,
            accepted_draw_start=1,
            accepted_draw_count=item.requested_additional_draw_count,
            accepted_draw_cap=item.requested_additional_draw_count,
        )
        validation = controller.execute_batch_intent_v2(validation_intent)
        executions.append(
            QueryBoundRowExecutionV1(
                _ROW_ISSUER,
                item.request_id,
                item.numerical_row_id,
                item.semantic_row_binding_id,
                discovery_intent.intent_id,
                discovery.batch.batch_id,
                discovery.receipt.receipt_id,
                support.freeze_id,
                validation_intent.intent_id,
                validation.batch.batch_id,
                validation.receipt.receipt_id,
                caps.new_child_discovery_draws_per_row,
                item.requested_additional_draw_count,
            )
        )
    closure = controller.close_and_reconcile_v2()
    return QueryBoundGroundTransactionV1(
        _TRANSACTION_ISSUER,
        request,
        namespace_binding,
        occurrence,
        closure,
        tuple(executions),
    )


def execute_query_bound_ground_transaction_v1(
    *,
    source_trace_bytes: bytes,
    build_epoch_envelope_bytes: bytes,
    root_query_result_bytes: bytes,
    overlay_bytes: bytes,
    request_bytes: bytes,
) -> QueryBoundGroundTransactionV1:
    """Compatibility wrapper: verify, prepare, then execute one transaction."""

    request = request_v1.verify_query_bound_recovery_request_bytes_v1(
        source_trace_bytes=source_trace_bytes,
        build_epoch_envelope_bytes=build_epoch_envelope_bytes,
        root_query_result_bytes=root_query_result_bytes,
        overlay_bytes=overlay_bytes,
        request_bytes=request_bytes,
    )
    preparation = prepare_query_bound_ground_transaction_v1(
        source_trace_bytes=source_trace_bytes,
        request=request,
    )
    return execute_prepared_query_bound_ground_transaction_v1(preparation)


def verify_query_bound_ground_transaction_v1(
    claimed: QueryBoundGroundTransactionV1,
) -> QueryBoundGroundTransactionV1:
    if type(claimed) is not QueryBoundGroundTransactionV1:
        _fail("query-bound ground transaction has a foreign type")
    claimed.__post_init__(_TRANSACTION_ISSUER)
    return claimed


__all__ = [
    "ConstructionK7QueryBoundGroundTransactionV1Error",
    "ENVIRONMENT_MARKER",
    "LOCAL_DOMAINS",
    "QueryBoundGroundTransactionV1",
    "QueryBoundGroundTransactionPreparationV1",
    "QueryBoundNamespaceBindingV1",
    "QueryBoundRowExecutionV1",
    "execute_query_bound_ground_transaction_v1",
    "execute_prepared_query_bound_ground_transaction_v1",
    "prepare_query_bound_ground_transaction_v1",
    "verify_query_bound_ground_transaction_v1",
]
