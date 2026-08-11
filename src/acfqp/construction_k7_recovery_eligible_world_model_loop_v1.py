"""Close one cached-failure -> local evidence -> immutable RAPM loop.

The input request is frozen by the recovery-eligible as-of checkpoint fixture.
Only its six rows with a preregistered next confidence checkpoint are opened in
one fresh private namespace.  Each row receives a signed support-discovery
batch followed by exactly the requested validation delta.  The observer is
then closed before the batches are projected onto the old, frozen support,
compiled into an immutable successor numerical model, and used to replan the
same H=2 query.

This remains a construction fixture.  It does not alter the capped persistent
cache baseline, hide the seventh cap-blocked row, issue a total-lift plan
certificate, or authorize official execution.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_recovery_eligible_checkpoint_fixture_v1 as checkpoint_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_batch_native_statistical_backend_v1 as backend_v1
from acfqp import v075_k7_causal_promotion_construction_fixture_v1 as fixture_v1
from acfqp import v075_observer_signed_batch_control_authority_v2 as control_v2
from acfqp import v075_public_graph_semantics_v1 as graph_v1
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_GROUND_TRANSACTION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_NAMESPACE_BINDING_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ROW_ACQUISITION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_WORLD_MODEL_LOOP_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.111"
PROFILE_KEY = "construction_k7_recovery_eligible_world_model_loop_v1"
ENVIRONMENT_MARKER = "real-reusable-build-epoch"

NAMESPACE_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_NAMESPACE_BINDING_V1_DOMAIN
ROW_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ROW_ACQUISITION_V1_DOMAIN
TRANSACTION_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_GROUND_TRANSACTION_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_WORLD_MODEL_LOOP_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {NAMESPACE_DOMAIN, ROW_DOMAIN, TRANSACTION_DOMAIN, RESULT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("recovery-eligible world-model loop domains are not central")

_PREPARATION_ISSUER = object()
_NAMESPACE_ISSUER = object()
_ROW_ISSUER = object()
_TRANSACTION_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7RecoveryEligibleWorldModelLoopV1Error(ValueError):
    """The frozen request, local acquisition, or immutable overlay changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryEligibleWorldModelLoopV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleWorldModelLoopV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class RecoveryEligibleGroundPreparationV1:
    """Ground-free transaction input frozen before namespace creation."""

    _issuer: InitVar[object]
    request: checkpoint_v1.RecoveryEligibleRecoveryRequestV1 = field(repr=False)
    source_model: planning_v2.V075NumericalModelV2 = field(repr=False)
    source_proof: planning_v2.V075NumericalPlanningProofV2 = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PREPARATION_ISSUER
            or type(self.request)
            is not checkpoint_v1.RecoveryEligibleRecoveryRequestV1
            or type(self.source_model) is not planning_v2.V075NumericalModelV2
            or type(self.source_proof)
            is not planning_v2.V075NumericalPlanningProofV2
        ):
            _fail("recovery-eligible preparation is caller-minted")
        checkpoint_v1.require_recovery_eligible_recovery_request_v1(self.request)
        self.source_model.__post_init__()
        self.source_proof.__post_init__()
        frontier = self.source_proof.failed_frontier
        if (
            self.source_proof.model != self.source_model
            or self.source_model.model_id != self.request.checkpoint.model.model_id
            or self.source_proof.proof_id != self.request.checkpoint.proof.proof_id
            or frontier is None
            or frontier.frontier_id
            != self.request.checkpoint.proof.failed_frontier.frontier_id
        ):
            _fail("recovery-eligible preparation crossed its checkpoint")


@dataclass(frozen=True, slots=True)
class RecoveryEligibleNamespaceBindingV1:
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
            _fail("recovery-eligible namespace binding is caller-minted")
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
            _fail("recovery-eligible namespace arm changed")
        object.__setattr__(
            self, "_binding_id", content_id(NAMESPACE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_namespace_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "recovery_eligible_recovery_request_id": self.recovery_request_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "native_occurrence_id": self.native_occurrence_id,
            "private_environment_generation_id": self.private_environment_generation_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "request_verified_before_namespace_creation": True,
            "namespace_ground_access_count_at_binding": 0,
            "construction_only": True,
            "production_authorizing": False,
            "official_execution_allowed": False,
        }

    @property
    def binding_id(self) -> str:
        current = content_id(NAMESPACE_DOMAIN, self._payload())
        if current != self._binding_id:
            _fail("recovery-eligible namespace binding changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "namespace_binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class RecoveryEligibleRowAcquisitionV1:
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
    _acquisition_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROW_ISSUER:
            _fail("recovery-eligible row acquisition is caller-minted")
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
            or self.requested_validation_draw_count != 2_048
        ):
            _fail("recovery-eligible row draw counts changed")
        object.__setattr__(
            self, "_acquisition_id", content_id(ROW_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_row_acquisition.v1",
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
            "selected_from_cached_failed_proof_frontier": True,
            "ground_access_performed": True,
        }

    @property
    def acquisition_id(self) -> str:
        current = content_id(ROW_DOMAIN, self._payload())
        if current != self._acquisition_id:
            _fail("recovery-eligible row acquisition changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_acquisition_id": self.acquisition_id}


@dataclass(frozen=True, slots=True)
class RecoveryEligibleGroundTransactionV1:
    _issuer: InitVar[object]
    request: checkpoint_v1.RecoveryEligibleRecoveryRequestV1 = field(repr=False)
    namespace_binding: RecoveryEligibleNamespaceBindingV1
    native_occurrence: backend_v1.V075BatchNativeOccurrenceIdentityV1 = field(
        repr=False
    )
    observer_closure: control_v2.V075ControlledBatchJournalClosureV2 = field(
        repr=False
    )
    row_acquisitions: tuple[RecoveryEligibleRowAcquisitionV1, ...]
    _transaction_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _TRANSACTION_ISSUER
            or type(self.request)
            is not checkpoint_v1.RecoveryEligibleRecoveryRequestV1
            or type(self.namespace_binding) is not RecoveryEligibleNamespaceBindingV1
            or type(self.native_occurrence)
            is not backend_v1.V075BatchNativeOccurrenceIdentityV1
            or type(self.observer_closure)
            is not control_v2.V075ControlledBatchJournalClosureV2
            or type(self.row_acquisitions) is not tuple
            or any(
                type(item) is not RecoveryEligibleRowAcquisitionV1
                for item in self.row_acquisitions
            )
        ):
            _fail("recovery-eligible ground transaction is caller-minted")
        checkpoint_v1.require_recovery_eligible_recovery_request_v1(self.request)
        self.namespace_binding.__post_init__(_NAMESPACE_ISSUER)
        for item in self.row_acquisitions:
            item.__post_init__(_ROW_ISSUER)
        requested = self.request.requested_rows
        if (
            self.namespace_binding.recovery_request_id != self.request.request_id
            or self.namespace_binding.logical_occurrence_id
            != self.request.consumption.query.logical_occurrence_id
            or self.namespace_binding.native_occurrence_id
            != self.native_occurrence.occurrence_id
            or self.namespace_binding.target_tape_namespace_id
            != self.native_occurrence.target_tape_namespace_id
            or tuple(item.validation_request_id for item in self.row_acquisitions)
            != tuple(item.request_id for item in requested)
            or tuple(item.numerical_row_id for item in self.row_acquisitions)
            != tuple(item.numerical_row_id for item in requested)
            or len(self.observer_closure.appends) != 2 * len(requested)
            or len(self.observer_closure.support_freezes) != len(requested)
            or self.observer_closure.reconciliation.total_accepted_draw_count
            != self.total_ground_draw_count
        ):
            _fail("recovery-eligible ground inventory crossed its request")
        replayed = control_v2.verify_v075_controlled_batch_journal_closure_v2(
            batch_closure=self.observer_closure.batch_closure,
            heads=self.observer_closure.heads,
            appends=self.observer_closure.appends,
            control_closure=self.observer_closure.control_closure,
            support_freezes=self.observer_closure.support_freezes,
        )
        if replayed != self.observer_closure.reconciliation:
            _fail("recovery-eligible observer closure differs from exact replay")
        object.__setattr__(
            self,
            "_transaction_id",
            content_id(TRANSACTION_DOMAIN, self._payload()),
        )

    @property
    def support_discovery_draw_count(self) -> int:
        return sum(item.support_discovery_draw_count for item in self.row_acquisitions)

    @property
    def requested_validation_draw_count(self) -> int:
        return sum(
            item.requested_validation_draw_count for item in self.row_acquisitions
        )

    @property
    def total_ground_draw_count(self) -> int:
        return self.support_discovery_draw_count + self.requested_validation_draw_count

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_ground_transaction.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "recovery_eligible_recovery_request_id": self.request.request_id,
            "logical_occurrence_id": self.request.consumption.query.logical_occurrence_id,
            "namespace_binding_id": self.namespace_binding.binding_id,
            "target_tape_namespace_id": self.native_occurrence.target_tape_namespace_id,
            "native_occurrence_id": self.native_occurrence.occurrence_id,
            "observer_control_closure_id": self.observer_closure.control_closure.control_closure_id,
            "observer_reconciliation_id": self.observer_closure.reconciliation.reconciliation_id,
            "row_acquisition_ids": [
                item.acquisition_id for item in self.row_acquisitions
            ],
            "requested_row_count": len(self.row_acquisitions),
            "cap_blocked_row_count": len(self.request.cap_blocked_rows),
            "support_discovery_draw_count": self.support_discovery_draw_count,
            "requested_validation_draw_count": self.requested_validation_draw_count,
            "total_ground_draw_count": self.total_ground_draw_count,
            "request_verified_before_namespace_creation": True,
            "namespace_bound_before_ground_access": True,
            "only_requested_rows_executed": True,
            "cap_blocked_rows_not_accessed": True,
            "observer_closed_and_exactly_reconciled": True,
            "fresh_query_ground_recovery_executed": True,
            "ground_access_after_observer_closure": 0,
            "immutable_overlay_compiled": False,
            "post_transaction_replanning_performed": False,
            "next_required_action": "COMPILE_SIGNED_BATCH_DELTAS_INTO_IMMUTABLE_OVERLAY",
            "construction_only": True,
            "plan_certificate_issued": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def transaction_id(self) -> str:
        current = content_id(TRANSACTION_DOMAIN, self._payload())
        if current != self._transaction_id:
            _fail("recovery-eligible ground transaction changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "request": self.request.to_document(),
            "namespace_binding": self.namespace_binding.to_document(),
            "native_occurrence": self.native_occurrence.to_document(),
            "row_acquisitions": [
                item.to_document() for item in self.row_acquisitions
            ],
            "observer_closure": self.observer_closure.to_document(),
            "recovery_eligible_ground_transaction_id": self.transaction_id,
        }


def _row_binding(
    model: planning_v2.V075NumericalModelV2,
    row: planning_v2.V075NumericalRowV2,
) -> graph_v1.V075ObservationRowBindingV1:
    state = graph_v1.V075SymbolicGraphStateV1(
        model.context, row.source_ranks, False
    )
    catalogue = graph_v1.V075LegalActionCatalogueV1(
        model.context,
        state,
        row.remaining_horizon,
        graph_v1.legal_action_triples_v1(
            model.context, state.ranks, state.failure
        ),
    )
    binding = graph_v1.observation_row_binding_v1(
        model.context, catalogue, row.action
    )
    if binding.row_binding_id != row.row_binding_id:
        _fail("recovery-eligible row changed its semantic binding")
    return binding


def prepare_recovery_eligible_ground_transaction_v1(
    request: checkpoint_v1.RecoveryEligibleRecoveryRequestV1,
) -> RecoveryEligibleGroundPreparationV1:
    request = checkpoint_v1.require_recovery_eligible_recovery_request_v1(request)
    return RecoveryEligibleGroundPreparationV1(
        _PREPARATION_ISSUER,
        request,
        request.checkpoint.model,
        request.checkpoint.proof,
    )


def execute_prepared_recovery_eligible_ground_transaction_v1(
    preparation: RecoveryEligibleGroundPreparationV1,
) -> RecoveryEligibleGroundTransactionV1:
    if type(preparation) is not RecoveryEligibleGroundPreparationV1:
        _fail("recovery-eligible preparation has a foreign type")
    preparation.__post_init__(_PREPARATION_ISSUER)
    request = preparation.request
    model = preparation.source_model
    logical_occurrence_id = request.consumption.query.logical_occurrence_id
    prepared = fixture_v1.prepare_v075_k7_construction_environment_v1(
        environment_marker=ENVIRONMENT_MARKER,
        identity_marker=logical_occurrence_id,
    )
    contexts = tuple(
        item
        for item in prepared.namespace.family.replicate_contexts
        if item.context_id == model.context.context_id
    )
    if len(contexts) != 1 or contexts[0] != model.context:
        _fail("fresh namespace does not share the cached model context")
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
    namespace_binding = RecoveryEligibleNamespaceBindingV1(
        _NAMESPACE_ISSUER,
        request.request_id,
        logical_occurrence_id,
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
    acquisitions: list[RecoveryEligibleRowAcquisitionV1] = []
    for item in request.requested_rows:
        row = rows_by_id.get(item.numerical_row_id)
        if row is None or row.row_binding_id != item.semantic_row_binding_id:
            _fail("requested recovery row is absent from the cached model")
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
        support = controller.freeze_complete_support_v2(discovery_append=discovery)
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
        acquisitions.append(
            RecoveryEligibleRowAcquisitionV1(
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
    return RecoveryEligibleGroundTransactionV1(
        _TRANSACTION_ISSUER,
        request,
        namespace_binding,
        occurrence,
        closure,
        tuple(acquisitions),
    )


def verify_recovery_eligible_ground_transaction_v1(
    claimed: RecoveryEligibleGroundTransactionV1,
) -> RecoveryEligibleGroundTransactionV1:
    if type(claimed) is not RecoveryEligibleGroundTransactionV1:
        _fail("recovery-eligible ground transaction has a foreign type")
    claimed.__post_init__(_TRANSACTION_ISSUER)
    return claimed


@dataclass(frozen=True, slots=True)
class RecoveryEligibleWorldModelLoopV1:
    _issuer: InitVar[object]
    transaction: RecoveryEligibleGroundTransactionV1 = field(repr=False)
    source_model: planning_v2.V075NumericalModelV2 = field(repr=False)
    source_proof: planning_v2.V075NumericalPlanningProofV2 = field(repr=False)
    deltas: tuple[planning_v2.V075QueryBoundValidationDeltaV2, ...] = field(
        repr=False
    )
    successor_model: planning_v2.V075NumericalModelV2 = field(repr=False)
    successor_proof: planning_v2.V075NumericalPlanningProofV2 = field(repr=False)
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.transaction) is not RecoveryEligibleGroundTransactionV1
            or type(self.source_model) is not planning_v2.V075NumericalModelV2
            or type(self.source_proof)
            is not planning_v2.V075NumericalPlanningProofV2
            or type(self.deltas) is not tuple
            or len(self.deltas) != 6
            or any(
                type(item) is not planning_v2.V075QueryBoundValidationDeltaV2
                for item in self.deltas
            )
            or type(self.successor_model) is not planning_v2.V075NumericalModelV2
            or type(self.successor_proof)
            is not planning_v2.V075NumericalPlanningProofV2
        ):
            _fail("recovery-eligible world-model loop is caller-minted")
        verify_recovery_eligible_ground_transaction_v1(self.transaction)
        if (
            self.source_model != self.transaction.request.checkpoint.model
            or self.source_proof != self.transaction.request.checkpoint.proof
            or self.source_proof.model != self.source_model
            or self.source_proof.failed_frontier is None
            or self.successor_proof.model != self.successor_model
            or self.successor_proof.route
            is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
            or tuple(item.source_row_id for item in self.deltas)
            != tuple(sorted({item.source_row_id for item in self.deltas}))
            or {item.source_model_id for item in self.deltas}
            != {self.source_model.model_id}
            or self.added_validation_draw_count != 12_288
        ):
            _fail("recovery-eligible overlay identity graph crossed")
        source_by_binding = {
            item.row_binding_id: item for item in self.source_model.rows
        }
        successor_by_binding = {
            item.row_binding_id: item for item in self.successor_model.rows
        }
        if (
            len(source_by_binding) != len(self.source_model.rows)
            or len(successor_by_binding) != len(self.successor_model.rows)
            or set(source_by_binding) != set(successor_by_binding)
            or self.source_model.context != self.successor_model.context
            or self.source_model.evidence_kind != self.successor_model.evidence_kind
        ):
            _fail("recovery-eligible overlay changed the reusable model closure")
        delta_by_binding = {item.row_binding_id: item for item in self.deltas}
        if set(delta_by_binding) != set(self.changed_row_binding_ids):
            _fail("recovery-eligible overlay changed rows outside signed deltas")
        for binding_id, source_row in source_by_binding.items():
            successor_row = successor_by_binding[binding_id]
            delta = delta_by_binding.get(binding_id)
            if delta is None:
                if source_row.to_document() != successor_row.to_document():
                    _fail("recovery-eligible overlay changed an unrequested row")
            elif (
                delta.source_row_id != source_row.row_id
                or delta.source_validation_draw_count
                != source_row.validation_draw_count
                or delta.target_validation_draw_count
                != successor_row.validation_draw_count
                or tuple(item.to_document() for item in source_row.support)
                != tuple(item.to_document() for item in successor_row.support)
            ):
                _fail("recovery-eligible overlay changed support semantics")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    @property
    def changed_row_binding_ids(self) -> tuple[str, ...]:
        source = {item.row_binding_id: item.row_id for item in self.source_model.rows}
        successor = {
            item.row_binding_id: item.row_id for item in self.successor_model.rows
        }
        return tuple(
            sorted(
                binding_id
                for binding_id in source
                if successor.get(binding_id) != source[binding_id]
            )
        )

    @property
    def preserved_row_binding_ids(self) -> tuple[str, ...]:
        changed = set(self.changed_row_binding_ids)
        return tuple(
            sorted(
                item.row_binding_id
                for item in self.source_model.rows
                if item.row_binding_id not in changed
            )
        )

    @property
    def added_validation_draw_count(self) -> int:
        return sum(item.additional_validation_draw_count for item in self.deltas)

    def _payload(self) -> dict[str, Any]:
        frontier = self.successor_proof.failed_frontier
        failed = frontier is not None
        query = self.transaction.request.consumption.query
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_world_model_loop.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": query.logical_occurrence_id,
            "recovery_eligible_checkpoint_id": self.transaction.request.checkpoint.checkpoint_id,
            "recovery_eligible_query_id": query.query_id,
            "recovery_eligible_recovery_request_id": self.transaction.request.request_id,
            "ground_transaction_id": self.transaction.transaction_id,
            "source_numerical_model_id": self.source_model.model_id,
            "source_numerical_proof_id": self.source_proof.proof_id,
            "source_frontier_id": self.source_proof.failed_frontier.frontier_id,
            "validation_delta_ids": [item.delta_id for item in self.deltas],
            "successor_numerical_model_id": self.successor_model.model_id,
            "successor_numerical_proof_id": self.successor_proof.proof_id,
            "successor_outcome": self.successor_proof.outcome.value,
            "successor_frontier_id": None if frontier is None else frontier.frontier_id,
            "requested_row_count": len(self.deltas),
            "cap_blocked_row_count": len(self.transaction.request.cap_blocked_rows),
            "changed_row_count": len(self.changed_row_binding_ids),
            "preserved_row_count": len(self.preserved_row_binding_ids),
            "changed_semantic_row_binding_ids": list(self.changed_row_binding_ids),
            "preserved_semantic_row_binding_ids": list(self.preserved_row_binding_ids),
            "support_discovery_draw_count": self.transaction.support_discovery_draw_count,
            "added_signed_validation_draw_count": self.added_validation_draw_count,
            "total_local_ground_draw_count": self.transaction.total_ground_draw_count,
            "cached_proof_reused_before_failure": True,
            "failed_proof_frontier_selected_before_ground_access": True,
            "only_preregistered_requestable_rows_acquired": True,
            "cap_blocked_row_remained_unaccessed": True,
            "signed_batch_deltas_exactly_replayed": True,
            "old_support_frozen_and_reused": True,
            "unseen_delta_outcomes_projected_to_other": True,
            "unrequested_rows_byte_identical": True,
            "immutable_query_local_model_compiled": True,
            "same_multistep_query_replanned": True,
            "horizon": self.successor_model.context.horizon,
            "ground_access_after_closed_transaction": 0,
            "fresh_query_recovery_loop_closed_through_replanning": True,
            "proof_still_failed": failed,
            "next_required_action": (
                "ROUTE_TO_DIRECT_GROUND_FALLBACK"
                if failed
                else "INDEPENDENT_TOTAL_LIFT_AND_PLAN_CERTIFICATE_AUDIT"
            ),
            "plan_certificate_issued": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("recovery-eligible world-model loop changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "validation_deltas": [item.to_document() for item in self.deltas],
            "successor_model": self.successor_model.to_document(),
            "successor_proof": self.successor_proof.to_document(),
            "recovery_eligible_world_model_loop_id": self.result_id,
        }


def compile_recovery_eligible_world_model_loop_v1(
    transaction: RecoveryEligibleGroundTransactionV1,
) -> RecoveryEligibleWorldModelLoopV1:
    transaction = verify_recovery_eligible_ground_transaction_v1(transaction)
    source_model = transaction.request.checkpoint.model
    source_proof = transaction.request.checkpoint.proof
    appends_by_batch = {
        item.batch.batch_id: item for item in transaction.observer_closure.appends
    }
    request_by_id = {
        item.request_id: item for item in transaction.request.requested_rows
    }
    deltas = []
    for acquisition in transaction.row_acquisitions:
        request = request_by_id.get(acquisition.validation_request_id)
        append = appends_by_batch.get(acquisition.validation_batch_id)
        if (
            request is None
            or append is None
            or append.receipt.receipt_id
            != acquisition.validation_append_receipt_id
            or append.batch.request.stream_identity.row_binding_id
            != acquisition.semantic_row_binding_id
            or append.batch.request.accepted_draw_count
            != request.requested_additional_draw_count
            or request.next_registered_checkpoint is None
        ):
            _fail("recovery-eligible validation crossed its signed request")
        deltas.append(
            planning_v2.freeze_v075_query_bound_validation_delta_v2(
                source_model=source_model,
                source_row_id=acquisition.numerical_row_id,
                signed_validation_batch=append.batch,
                target_validation_draw_count=request.next_registered_checkpoint,
            )
        )
    canonical_deltas = tuple(sorted(deltas, key=lambda item: item.source_row_id))
    successor_model = planning_v2.compile_v075_query_bound_validation_overlay_v2(
        source_model=source_model,
        deltas=canonical_deltas,
    )
    successor_proof = planning_v2.plan_v075_construction_numerical_model_v2(
        model=successor_model,
        route=planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    return RecoveryEligibleWorldModelLoopV1(
        _RESULT_ISSUER,
        transaction,
        source_model,
        source_proof,
        canonical_deltas,
        successor_model,
        successor_proof,
    )


def verify_recovery_eligible_world_model_loop_v1(
    claimed: RecoveryEligibleWorldModelLoopV1,
) -> RecoveryEligibleWorldModelLoopV1:
    if type(claimed) is not RecoveryEligibleWorldModelLoopV1:
        _fail("recovery-eligible world-model loop has a foreign type")
    expected = compile_recovery_eligible_world_model_loop_v1(claimed.transaction)
    if canonical_json_bytes(expected.to_document()) != canonical_json_bytes(
        claimed.to_document()
    ):
        _fail("recovery-eligible world-model loop differs from exact replay")
    return expected


def verify_recovery_eligible_world_model_loop_bytes_v1(
    *,
    transaction: RecoveryEligibleGroundTransactionV1,
    result_bytes: bytes,
) -> RecoveryEligibleWorldModelLoopV1:
    expected = compile_recovery_eligible_world_model_loop_v1(transaction)
    if (
        type(result_bytes) is not bytes
        or canonical_json_bytes(loads_canonical_json(result_bytes)) != result_bytes
        or canonical_json_bytes(expected.to_document()) != result_bytes
    ):
        _fail("recovery-eligible world-model loop bytes differ from exact replay")
    return expected


__all__ = [
    "ConstructionK7RecoveryEligibleWorldModelLoopV1Error",
    "ENVIRONMENT_MARKER",
    "LOCAL_DOMAINS",
    "RecoveryEligibleGroundPreparationV1",
    "RecoveryEligibleGroundTransactionV1",
    "RecoveryEligibleNamespaceBindingV1",
    "RecoveryEligibleRowAcquisitionV1",
    "RecoveryEligibleWorldModelLoopV1",
    "compile_recovery_eligible_world_model_loop_v1",
    "execute_prepared_recovery_eligible_ground_transaction_v1",
    "prepare_recovery_eligible_ground_transaction_v1",
    "verify_recovery_eligible_ground_transaction_v1",
    "verify_recovery_eligible_world_model_loop_bytes_v1",
    "verify_recovery_eligible_world_model_loop_v1",
]
