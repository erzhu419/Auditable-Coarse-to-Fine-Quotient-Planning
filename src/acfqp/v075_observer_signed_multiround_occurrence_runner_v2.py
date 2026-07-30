"""Construction-only observer-signed V0-075 multiround occurrence runner.

This module owns the execution order from one exact preregistered initial
schedule through observer-signed aggregate acquisition, live numerical model
epochs, and final closed-lineage reconciliation.  It deliberately stops
before any production or scientific claim: every result remains a
noncertificate construction artifact.

The authorized-child path crosses an exact child-model/replanning barrier
binding the global child closure, closure verification, all-or-none execution
ledger, ledger verification, and resulting live model epoch.  Every promotion
crosses a second exact execution/model barrier.  A raw post-execution epoch is
never accepted as permission to inspect its proof or continue planning.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, NoReturn

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    parse_content_id,
)
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import (
    v075_batch_occurrence_lifecycle_authority_v2 as lifecycle_module,
)
from acfqp import v075_batched_observer_authority_v2 as lineage_authority
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.60.0"
PROFILE_KEY = "v075_observer_signed_multiround_occurrence_runner_v2"
MAXIMUM_PROMOTION_ROUNDS = 2
MAX_CANONICAL_RESULT_BYTES = 16 * 1024 * 1024

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
FRESH_HELDOUT_ACCESS_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_OCCURRENCE_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
PRODUCTION_BLOCKER = (
    "the observer-signed multiround runner is construction-only; production "
    "IPC, semantic-registry replay, canonical bundle loading, independent "
    "verification, and a fresh preregistered held-out campaign are absent"
)

DOMAIN_TAGS = {
    "root_execution": (
        "acfqp:v075-observer-signed-root-execution:v2"
    ),
    "closed_reconciliation": (
        "acfqp:v075-observer-signed-closed-reconciliation:v2"
    ),
    "result": (
        "acfqp:v075-observer-signed-multiround-result:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 multiround runner domains must be unique")
if MAXIMUM_PROMOTION_ROUNDS != dynamic.MAXIMUM_PROMOTION_ROUNDS:
    raise RuntimeError(
        "V0-075 multiround runner/dynamic promotion caps differ"
    )


class V075ObserverSignedMultiroundV2InvariantViolation(ValueError):
    """The construction state machine or one exact binding was invalid."""


class V075ObserverSignedMultiroundProductionV2NotReady(RuntimeError):
    """The construction runner cannot authorize production execution."""


def _fail(message: str) -> NoReturn:
    raise V075ObserverSignedMultiroundV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ObserverSignedMultiroundV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ObserverSignedMultiroundV2InvariantViolation(
            str(error)
        ) from error


def _canonical_private_environment(
    value: Iterable[Iterable[tuple[int, Any]]],
) -> tuple[tuple[tuple[int, Any], ...], ...]:
    """Materialize once so observer execution and closed replay see one law."""

    try:
        result = tuple(tuple(row) for row in value)
    except (TypeError, ValueError) as error:
        raise V075ObserverSignedMultiroundV2InvariantViolation(
            "construction private environment is not a finite iterable"
        ) from error
    if not result:
        _fail("construction private environment is empty")
    return result


def _snapshot_construction_evidence_roots(
    roots: Mapping[str, Any],
) -> bytes:
    """Seal public and private/cached fields around the post-closure sink."""

    return canonical_json_bytes(
        {
            key: control.same_process_structural_fingerprint_v2(value)
            for key, value in sorted(roots.items())
        }
    )


def _exact_initial_authority(
    *,
    repository_root: str | Path,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    verification: acquisition.V075InitialAcquisitionVerificationV2,
) -> tuple[
    acquisition.V075InitialAcquisitionScheduleV2,
    acquisition.V075InitialAcquisitionVerificationV2,
]:
    """Replay schedule and its verifier-issued identity before target access."""

    if (
        type(namespace) is not namespace_v2.V075PublicTargetTapeNamespaceV2
        or type(schedule) is not acquisition.V075InitialAcquisitionScheduleV2
        or type(verification)
        is not acquisition.V075InitialAcquisitionVerificationV2
    ):
        _fail("initial schedule boundary requires exact V2 typed artifacts")
    try:
        exact_schedule = acquisition.replay_v075_initial_acquisition_schedule_v2(
            repository_root=repository_root,
            namespace=namespace,
            claimed=schedule,
        )
        expected_slot = exact_schedule.profile.occurrence_slot_for(
            context_id=exact_schedule.occurrence.context_id,
            arm=exact_schedule.occurrence.arm,
        )
        exact_verification = (
            acquisition.verify_v075_initial_acquisition_verification_bytes_v2(
                schedule=exact_schedule,
                expected_slot=expected_slot,
                raw=verification.canonical_bytes,
            )
        )
    except Exception as error:
        raise V075ObserverSignedMultiroundV2InvariantViolation(
            "initial schedule or verification exact replay failed"
        ) from error
    if (
        exact_schedule.schedule_id != schedule.schedule_id
        or exact_schedule.canonical_bytes != schedule.canonical_bytes
        or exact_verification.verification_id != verification.verification_id
        or exact_verification.canonical_bytes != verification.canonical_bytes
        or exact_schedule.occurrence.arm
        is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    ):
        _fail("multiround runner requires one exact adaptive schedule")
    return exact_schedule, exact_verification


def _root_discovery_stream(
    *,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    row_binding: graph.V075ObservationRowBindingV1,
    arm: worker.V075WorkerArmV1,
) -> graph.V075TransitionStreamIdentityV1:
    epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row_binding,
        epoch_index=0,
        evidence=(),
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row_binding,
        epochs=(epoch,),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row_binding,
        support_chain=chain,
    )
    stream = graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=arm.value,
    )
    if (
        stream.row_binding != row_binding
        or stream.lane is not graph.V075ObservationLaneV1.DISCOVERY
        or stream.observer_epoch_index != 0
    ):
        _fail("initial root discovery stream derivation changed")
    return stream


_ROOT_EXECUTION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ObserverSignedRootExecutionV2:
    """One exact schedule-to-signed-root-prefix execution mapping."""

    _issuer: InitVar[object]
    schedule_id: str
    schedule_verification_id: str
    occurrence_id: str
    resulting_head_id: str
    open_prefix_verification_id: str
    discovery_intent_ids: tuple[str, ...]
    discovery_receipt_ids: tuple[str, ...]
    support_promotion_template_ids: tuple[str, ...]
    support_freeze_ids: tuple[str, ...]
    support_promotion_freeze_bindings: tuple[tuple[str, str], ...]
    validation_intent_ids: tuple[str, ...]
    validation_receipt_ids: tuple[str, ...]
    root_row_binding_ids: tuple[str, ...]
    _execution_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.schedule_id, "root execution schedule"),
            (
                self.schedule_verification_id,
                "root execution schedule verification",
            ),
            (self.occurrence_id, "root execution occurrence"),
            (self.resulting_head_id, "root execution resulting head"),
            (
                self.open_prefix_verification_id,
                "root execution prefix verification",
            ),
            *(
                (value, "root execution artifact")
                for value in (
                    *self.discovery_intent_ids,
                    *self.discovery_receipt_ids,
                    *self.support_promotion_template_ids,
                    *self.support_freeze_ids,
                    *(
                        value
                        for binding in self.support_promotion_freeze_bindings
                        for value in binding
                    ),
                    *self.validation_intent_ids,
                    *self.validation_receipt_ids,
                    *self.root_row_binding_ids,
                )
            ),
        ):
            _cid(value, label)
        width = len(self.root_row_binding_ids)
        if (
            _issuer is not _ROOT_EXECUTION_ISSUER
            or width <= 0
            or any(
                len(values) != width
                for values in (
                    self.discovery_intent_ids,
                    self.discovery_receipt_ids,
                    self.support_promotion_template_ids,
                    self.support_freeze_ids,
                    self.support_promotion_freeze_bindings,
                    self.validation_intent_ids,
                    self.validation_receipt_ids,
                )
            )
            or len(set(self.root_row_binding_ids)) != width
            or len(set(self.discovery_intent_ids))
            != len(self.discovery_intent_ids)
            or len(set(self.support_promotion_template_ids))
            != len(self.support_promotion_template_ids)
            or len(set(self.validation_intent_ids))
            != len(self.validation_intent_ids)
            or any(
                len(set(values)) != width
                for values in (
                    self.discovery_receipt_ids,
                    self.support_freeze_ids,
                    self.validation_receipt_ids,
                )
            )
            or any(
                type(binding) is not tuple or len(binding) != 2
                for binding in self.support_promotion_freeze_bindings
            )
            or self.support_promotion_freeze_bindings
            != tuple(
                zip(
                    self.support_promotion_template_ids,
                    self.support_freeze_ids,
                    strict=True,
                )
            )
        ):
            _fail("signed root execution is partial, duplicated, or caller-minted")
        object.__setattr__(
            self,
            "_execution_id",
            _hash("root_execution", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_observer_signed_root_execution.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "schedule_id": self.schedule_id,
            "schedule_verification_id": self.schedule_verification_id,
            "occurrence_id": self.occurrence_id,
            "resulting_head_id": self.resulting_head_id,
            "open_prefix_verification_id": (
                self.open_prefix_verification_id
            ),
            "discovery_intent_ids": list(self.discovery_intent_ids),
            "discovery_receipt_ids": list(self.discovery_receipt_ids),
            "support_promotion_template_ids": list(
                self.support_promotion_template_ids
            ),
            "support_freeze_ids": list(self.support_freeze_ids),
            "support_promotion_freeze_bindings": [
                {
                    "support_promotion_template_id": template_id,
                    "support_freeze_id": freeze_id,
                }
                for template_id, freeze_id in (
                    self.support_promotion_freeze_bindings
                )
            ],
            "validation_intent_ids": list(self.validation_intent_ids),
            "validation_receipt_ids": list(self.validation_receipt_ids),
            "root_row_binding_ids": list(self.root_row_binding_ids),
            "all_preregistered_root_rows_executed_exactly_once": True,
            "all_support_promotion_templates_matched_exactly_once": True,
            "support_promotion_dependency_chain_exactly_replayed": True,
            "support_frozen_before_same_row_validation": True,
            "observer_signed_prefix_exactly_replayed": True,
            "official_execution_allowed": False,
        }

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "execution_id": self.execution_id}


def _execute_initial_root_schedule(
    *,
    controller: control.V075ConstructionControlledPrivateObserverV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    verification: acquisition.V075InitialAcquisitionVerificationV2,
) -> V075ObserverSignedRootExecutionV2:
    """Execute every exact D64/freeze/V2048 root row once."""

    discoveries = tuple(
        item
        for item in schedule.intents
        if item.kind is acquisition.V075InitialIntentKindV2.ROOT_DISCOVERY
    )
    promotions = tuple(
        item
        for item in schedule.intents
        if item.kind
        is acquisition.V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE
    )
    validations = tuple(
        item
        for item in schedule.intents
        if item.kind is acquisition.V075InitialIntentKindV2.ROOT_VALIDATION
    )
    if (
        not discoveries
        or len(discoveries) != len(promotions)
        or len(discoveries) != len(validations)
        or tuple(item.row_binding for item in discoveries)
        != tuple(item.row_binding for item in promotions)
        or tuple(item.row_binding for item in discoveries)
        != tuple(item.row_binding for item in validations)
        or tuple(item.dependency_intent_ids for item in promotions)
        != tuple((item.intent_id,) for item in discoveries)
        or tuple(item.dependency_intent_ids for item in validations)
        != tuple((item.intent_id,) for item in promotions)
        or controller.occurrence_identity != schedule.occurrence
        or controller.controlled_appends
        or controller.support_freezes
    ):
        _fail("initial root execution boundary is stale or incomplete")
    discovery_receipts = []
    support_by_row: dict[
        str,
        control.V075ControlledCompleteSupportFreezeV2,
    ] = {}
    for item in discoveries:
        intent = controller.prepare_batch_intent_v2(
            stream_identity=_root_discovery_stream(
                namespace=namespace,
                row_binding=item.row_binding,
                arm=schedule.occurrence.arm,
            ),
            semantic_authority_role=(
                control.V075ControlledBatchSemanticAuthorityRoleV2
                .INITIAL_SCHEDULE_ROW_INTENT
            ),
            semantic_authority_schema=(
                control.V075ControlledBatchSemanticAuthoritySchemaV2
                .INITIAL_SCHEDULE_ROW_INTENT
            ),
            semantic_artifact_id=item.intent_id,
            semantic_verification_id=verification.verification_id,
            stage=control.V075ControlledBatchStageV2.ROOT_DISCOVERY,
            round_index=0,
            support_freeze_id=None,
            accepted_draw_start=item.accepted_draw_start,
            accepted_draw_count=item.accepted_draw_count,
            accepted_draw_cap=item.accepted_draw_cap,
        )
        append = controller.execute_batch_intent_v2(intent)
        support = controller.freeze_complete_support_v2(
            discovery_append=append,
        )
        if support.row_binding_id in support_by_row:
            _fail("initial root support freeze repeated one row")
        support_by_row[support.row_binding_id] = support
        discovery_receipts.append(append.receipt.receipt_id)
    validation_receipts = []
    for item in validations:
        support = support_by_row.get(item.row_binding.row_binding_id)
        if support is None:
            _fail("initial root validation lacks its same-row support freeze")
        validation_stream = (
            control.derive_v075_controlled_validation_stream_v2(
                support_freeze=support,
            )
        )
        intent = controller.prepare_batch_intent_v2(
            stream_identity=validation_stream,
            semantic_authority_role=(
                control.V075ControlledBatchSemanticAuthorityRoleV2
                .INITIAL_SCHEDULE_ROW_INTENT
            ),
            semantic_authority_schema=(
                control.V075ControlledBatchSemanticAuthoritySchemaV2
                .INITIAL_SCHEDULE_ROW_INTENT
            ),
            semantic_artifact_id=item.intent_id,
            semantic_verification_id=verification.verification_id,
            stage=control.V075ControlledBatchStageV2.ROOT_VALIDATION,
            round_index=0,
            support_freeze_id=support.freeze_id,
            accepted_draw_start=item.accepted_draw_start,
            accepted_draw_count=item.accepted_draw_count,
            accepted_draw_cap=item.accepted_draw_cap,
        )
        append = controller.execute_batch_intent_v2(intent)
        validation_receipts.append(append.receipt.receipt_id)
    prefix = controller.freeze_owned_open_prefix_v2()
    expected_artifacts = tuple(
        (*[item.intent_id for item in discoveries],
         *[item.intent_id for item in validations])
    )
    actual_artifacts = tuple(
        item.intent.semantic_authority.semantic_artifact_id
        for item in controller.controlled_appends
    )
    if actual_artifacts != expected_artifacts:
        _fail("initial root controlled append order differs from schedule")
    supports = tuple(
        support_by_row[item.row_binding.row_binding_id]
        for item in discoveries
    )
    return V075ObserverSignedRootExecutionV2(
        _issuer=_ROOT_EXECUTION_ISSUER,
        schedule_id=schedule.schedule_id,
        schedule_verification_id=verification.verification_id,
        occurrence_id=schedule.occurrence.occurrence_id,
        resulting_head_id=prefix.current_head_id,
        open_prefix_verification_id=prefix.verification_id,
        discovery_intent_ids=tuple(
            item.intent_id for item in discoveries
        ),
        discovery_receipt_ids=tuple(discovery_receipts),
        support_promotion_template_ids=tuple(
            item.intent_id for item in promotions
        ),
        support_freeze_ids=tuple(item.freeze_id for item in supports),
        support_promotion_freeze_bindings=tuple(
            (promotion.intent_id, support.freeze_id)
            for promotion, support in zip(
                promotions,
                supports,
                strict=True,
            )
        ),
        validation_intent_ids=tuple(
            item.intent_id for item in validations
        ),
        validation_receipt_ids=tuple(validation_receipts),
        root_row_binding_ids=tuple(
            item.row_binding.row_binding_id for item in discoveries
        ),
    )


class V075ObserverSignedMultiroundTerminalStatusV2(str, Enum):
    CANDIDATE_EARLY_STOP = "CANDIDATE_EARLY_STOP"
    CHILD_ACTION_ROW_CAP_EXCEEDED = "CHILD_ACTION_ROW_CAP_EXCEEDED"
    CANDIDATE_AFTER_CHILD_CLOSURE = "CANDIDATE_AFTER_CHILD_CLOSURE"
    CANDIDATE_AFTER_PROMOTION_ONE = "CANDIDATE_AFTER_PROMOTION_ONE"
    CANDIDATE_AFTER_PROMOTION_TWO = "CANDIDATE_AFTER_PROMOTION_TWO"
    NO_ELIGIBLE_PROMOTION_ROW = "NO_ELIGIBLE_PROMOTION_ROW"
    PROMOTION_BUDGET_EXHAUSTED = "PROMOTION_BUDGET_EXHAUSTED"


_CLOSED_RECONCILIATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ObserverSignedClosedReconciliationV2:
    """Final live epoch exactly equal to full closed recompilation."""

    _issuer: InitVar[object]
    final_epoch: live_model.V075LiveIncrementalModelEpochV2 = field(
        repr=False
    )
    controlled_closure: control.V075ControlledBatchJournalClosureV2 = field(
        repr=False
    )
    lineage: lineage_authority.V075BatchOccurrenceLineageV2 = field(
        repr=False
    )
    lifecycle: lifecycle_module.V075BatchOccurrenceLifecycleClosureV2 = field(
        repr=False
    )
    planning_input: planning.V075ConstructionPlanningInputV2 = field(
        repr=False
    )
    closed_proof: planning.V075NumericalPlanningProofV2 = field(
        repr=False
    )
    _reconciliation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        epoch = self.final_epoch
        if (
            _issuer is not _CLOSED_RECONCILIATION_ISSUER
            or type(epoch) is not live_model.V075LiveIncrementalModelEpochV2
            or type(self.controlled_closure)
            is not control.V075ControlledBatchJournalClosureV2
            or type(self.lineage)
            is not lineage_authority.V075BatchOccurrenceLineageV2
            or type(self.lifecycle)
            is not lifecycle_module.V075BatchOccurrenceLifecycleClosureV2
            or type(self.planning_input)
            is not planning.V075ConstructionPlanningInputV2
            or type(self.closed_proof)
            is not planning.V075NumericalPlanningProofV2
            or self.controlled_closure.control_closure.final_head_id
            != epoch.head_id
            or self.lineage.occurrence_identity
            != epoch.occurrence_identity
            or self.lifecycle.occurrence_id
            != epoch.occurrence_identity.occurrence_id
            or self.planning_input.occurrence_id
            != epoch.occurrence_identity.occurrence_id
            or self.planning_input.route is not epoch.route
            or self.planning_input.model.model_id != epoch.model.model_id
            or canonical_json_bytes(self.planning_input.model.to_document())
            != canonical_json_bytes(epoch.model.to_document())
            or self.closed_proof.proof_id != epoch.proof.proof_id
            or self.closed_proof.canonical_bytes != epoch.proof.canonical_bytes
        ):
            _fail("closed compiler/planner differs from final live epoch")
        object.__setattr__(
            self,
            "_reconciliation_id",
            _hash("closed_reconciliation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_observer_signed_closed_reconciliation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "final_model_epoch_id": self.final_epoch.model_epoch_id,
            "final_numerical_model_id": self.final_epoch.model.model_id,
            "final_proof_id": self.final_epoch.proof.proof_id,
            "controlled_journal_closure_id": (
                self.controlled_closure.control_closure.control_closure_id
            ),
            "batch_closure_id": (
                self.controlled_closure.batch_closure.closure_id
            ),
            "lineage_id": self.lineage.lineage_id,
            "lifecycle_closure_id": self.lifecycle.closure_id,
            "closed_planning_input_id": self.planning_input.input_id,
            "closed_proof_id": self.closed_proof.proof_id,
            "live_and_closed_model_bytes_equal": True,
            "live_and_closed_proof_bytes_equal": True,
            "closed_lineage_exactly_replayed": True,
            "official_execution_allowed": False,
        }

    @property
    def reconciliation_id(self) -> str:
        return self._reconciliation_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "reconciliation_id": self.reconciliation_id,
        }


def freeze_v075_construction_closed_reconciliation_v2(
    *,
    repository_root: str | Path,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    final_epoch: live_model.V075LiveIncrementalModelEpochV2,
    controlled_closure: control.V075ControlledBatchJournalClosureV2,
    lineage: lineage_authority.V075BatchOccurrenceLineageV2,
    lifecycle: lifecycle_module.V075BatchOccurrenceLifecycleClosureV2,
) -> V075ObserverSignedClosedReconciliationV2:
    """Replay and reconcile one already-closed construction occurrence.

    The public producer accepts only upstream evidence roots.  In particular,
    it never accepts a caller-claimed planning input or proof: both are
    deterministically rebuilt after the control, lineage, lifecycle, and live
    epoch graphs have been reconciled.
    """

    try:
        if (
            type(schedule)
            is not acquisition.V075InitialAcquisitionScheduleV2
            or type(final_epoch)
            is not live_model.V075LiveIncrementalModelEpochV2
            or type(controlled_closure)
            is not control.V075ControlledBatchJournalClosureV2
            or type(lineage)
            is not lineage_authority.V075BatchOccurrenceLineageV2
            or type(lifecycle)
            is not lifecycle_module.V075BatchOccurrenceLifecycleClosureV2
        ):
            _fail(
                "closed reconciliation requires exact construction evidence "
                "root types"
            )
        if (
            lineage.scope
            is not (
                lineage_authority
                .V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
            )
            or lifecycle.scope
            is not (
                lifecycle_module
                .V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY
            )
        ):
            _fail("closed reconciliation accepts construction scope only")

        exact_final_epoch = (
            live_model.replay_v075_live_incremental_model_epoch_v2(
                final_epoch
            )
        )
        if (
            type(exact_final_epoch)
            is not live_model.V075LiveIncrementalModelEpochV2
            or exact_final_epoch.model_epoch_id != final_epoch.model_epoch_id
            or exact_final_epoch.canonical_bytes
            != final_epoch.canonical_bytes
        ):
            _fail("final live epoch differs from public exact replay")
        final_epoch = exact_final_epoch

        replayed_control = (
            control.verify_v075_controlled_batch_journal_closure_v2(
                batch_closure=controlled_closure.batch_closure,
                heads=controlled_closure.heads,
                appends=controlled_closure.appends,
                control_closure=controlled_closure.control_closure,
                support_freezes=controlled_closure.support_freezes,
            )
        )
        if (
            type(replayed_control)
            is not control.V075SignedBatchControlReconciliationV2
            or replayed_control.to_document()
            != controlled_closure.reconciliation.to_document()
        ):
            _fail(
                "controlled closure differs from public exact graph replay"
            )

        exact_lineage = (
            lineage_authority
            .replay_v075_signed_batch_occurrence_lineage_v2(lineage)
        )
        if (
            exact_lineage.scope
            is not (
                lineage_authority
                .V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
            )
            or exact_lineage.canonical_bytes != lineage.canonical_bytes
            or exact_lineage.closure.canonical_bytes
            != controlled_closure.batch_closure.canonical_bytes
        ):
            _fail(
                "lineage is not the exact construction replay of the "
                "controlled batch closure"
            )

        streams = tuple(
            sorted(
                {
                    batch.request.stream_identity.stream_id: (
                        batch.request.stream_identity
                    )
                    for batch in exact_lineage.batches
                }.values(),
                key=lambda item: item.stream_id,
            )
        )
        exact_lifecycle, lifecycle_verification = (
            lifecycle_module
            .verify_v075_batch_occurrence_lifecycle_bytes_v2(
                lifecycle_bytes=lifecycle.canonical_bytes,
                lineage_bytes=exact_lineage.canonical_bytes,
                batch_closure_bytes=(
                    controlled_closure.batch_closure.canonical_bytes
                ),
                known_stream_identities=streams,
            )
        )
        if (
            type(exact_lifecycle)
            is not lifecycle_module.V075BatchOccurrenceLifecycleClosureV2
            or type(lifecycle_verification)
            is not lifecycle_module.V075BatchOccurrenceLifecycleVerificationV2
            or exact_lifecycle.scope
            is not (
                lifecycle_module
                .V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY
            )
            or exact_lifecycle.canonical_bytes != lifecycle.canonical_bytes
            or exact_lifecycle.lineage_id != exact_lineage.lineage_id
            or exact_lifecycle.batch_closure_id
            != controlled_closure.batch_closure.closure_id
        ):
            _fail(
                "lifecycle is not the exact construction replay of lineage "
                "and controlled closure"
            )

        occurrence = schedule.occurrence
        occurrence_id = occurrence.occurrence_id
        namespace_id = occurrence.target_tape_namespace_id
        arm = occurrence.arm
        expected_route = (
            planning.V075PlanningRouteV2.MATCHED_DIRECT_GROUND
            if arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            else planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
        )
        controlled_namespace_id = (
            controlled_closure.batch_closure.authority_binding.namespace
            .target_tape_namespace_id
        )
        lineage_namespace_id = (
            exact_lineage.closure.authority_binding.namespace
            .target_tape_namespace_id
        )
        if (
            final_epoch.occurrence_identity != occurrence
            or exact_lineage.occurrence_identity != occurrence
            or controlled_closure.batch_closure.occurrence_id != occurrence_id
            or controlled_closure.control_closure.occurrence_id != occurrence_id
            or exact_lifecycle.occurrence_id != occurrence_id
            or final_epoch.context_id != occurrence.context_id
            or exact_lifecycle.context_id != occurrence.context_id
            or final_epoch.arm is not arm
            or exact_lifecycle.arm != arm.value
            or final_epoch.route is not expected_route
            or final_epoch.occurrence_identity.target_tape_namespace_id
            != namespace_id
            or exact_lineage.occurrence_identity.target_tape_namespace_id
            != namespace_id
            or controlled_namespace_id != namespace_id
            or lineage_namespace_id != namespace_id
            or exact_lifecycle.target_tape_namespace_id != namespace_id
        ):
            _fail(
                "closed evidence crossed occurrence, namespace, context, "
                "arm, or route"
            )

        append_receipt_ids = tuple(
            item.receipt.receipt_id for item in controlled_closure.appends
        )
        support_freeze_ids = tuple(
            item.freeze_id for item in controlled_closure.support_freezes
        )
        head_ids = tuple(item.head_id for item in controlled_closure.heads)
        prefix = final_epoch.open_prefix_verification
        if (
            final_epoch.controlled_appends != controlled_closure.appends
            or final_epoch.support_freezes
            != controlled_closure.support_freezes
            or prefix.heads != controlled_closure.heads
            or prefix.appends != controlled_closure.appends
            or prefix.support_freezes != controlled_closure.support_freezes
            or prefix.head_ids != head_ids
            or prefix.receipt_ids != append_receipt_ids
            or prefix.support_freeze_ids != support_freeze_ids
            or final_epoch.head_id
            != controlled_closure.control_closure.final_head_id
            or prefix.current_head_id != final_epoch.head_id
        ):
            _fail(
                "final live epoch is not the complete controlled "
                "append/freeze prefix"
            )

        planning_input = (
            planning.compile_v075_construction_planning_input_v2(
                repository_root=repository_root,
                schedule=schedule,
                lineage=exact_lineage,
                lifecycle=exact_lifecycle,
            )
        )
        if (
            type(planning_input)
            is not planning.V075ConstructionPlanningInputV2
            or planning_input.schedule_id != schedule.schedule_id
            or planning_input.lineage_id != exact_lineage.lineage_id
            or planning_input.lifecycle_closure_id
            != exact_lifecycle.closure_id
            or planning_input.lifecycle_verification_id
            != lifecycle_verification.verification_id
            or planning_input.occurrence_id != occurrence_id
            or planning_input.target_tape_namespace_id != namespace_id
            or planning_input.arm is not arm
            or planning_input.route is not expected_route
            or planning_input.model.model_id != final_epoch.model.model_id
            or canonical_json_bytes(planning_input.model.to_document())
            != canonical_json_bytes(final_epoch.model.to_document())
        ):
            _fail(
                "closed planning input differs from the reconciled evidence "
                "or final live model"
            )
        proof = planning.plan_v075_construction_numerical_model_v2(
            model=planning_input.model,
            route=planning_input.route,
        )
        if (
            type(proof) is not planning.V075NumericalPlanningProofV2
            or proof.proof_id != final_epoch.proof.proof_id
            or proof.canonical_bytes != final_epoch.proof.canonical_bytes
        ):
            _fail("closed replanning proof differs from final live proof")
        return V075ObserverSignedClosedReconciliationV2(
            _CLOSED_RECONCILIATION_ISSUER,
            final_epoch,
            controlled_closure,
            exact_lineage,
            exact_lifecycle,
            planning_input,
            proof,
        )
    except V075ObserverSignedMultiroundV2InvariantViolation:
        raise
    except Exception as error:
        raise V075ObserverSignedMultiroundV2InvariantViolation(
            "construction closed reconciliation exact replay failed"
        ) from error


def _close_and_reconcile(
    *,
    repository_root: str | Path,
    controller: control.V075ConstructionControlledPrivateObserverV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    final_epoch: live_model.V075LiveIncrementalModelEpochV2,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    private_salt: bytes,
    private_environment: tuple[tuple[tuple[int, Any], ...], ...],
) -> V075ObserverSignedClosedReconciliationV2:
    closed = controller.close_and_reconcile_v2()
    streams = tuple(
        sorted(
            {
                item.batch.request.stream_identity.stream_id: (
                    item.batch.request.stream_identity
                )
                for item in closed.appends
            }.values(),
            key=lambda item: item.stream_id,
        )
    )
    try:
        exact_lineage = (
            lineage_authority
            .freeze_v075_construction_batch_occurrence_lineage_v2(
                occurrence_identity=schedule.occurrence,
                closure=closed.batch_closure,
                authority=authority,
                namespace=namespace,
                known_stream_identities=streams,
                private_salt=private_salt,
                private_environment=private_environment,
            )
        )
        exact_lifecycle = (
            lifecycle_module.freeze_v075_construction_batch_occurrence_lifecycle_v2(
                lineage=exact_lineage,
                lineage_bytes=exact_lineage.canonical_bytes,
                batch_closure_bytes=closed.batch_closure.canonical_bytes,
            )
        )
        planning_input = planning.compile_v075_construction_planning_input_v2(
            repository_root=repository_root,
            schedule=schedule,
            lineage=exact_lineage,
            lifecycle=exact_lifecycle,
        )
        proof = planning.plan_v075_construction_numerical_model_v2(
            model=planning_input.model,
            route=planning_input.route,
        )
    except Exception as error:
        raise V075ObserverSignedMultiroundV2InvariantViolation(
            "closed lineage/compiler/planner exact replay failed"
        ) from error
    return V075ObserverSignedClosedReconciliationV2(
        _CLOSED_RECONCILIATION_ISSUER,
        final_epoch,
        closed,
        exact_lineage,
        exact_lifecycle,
        planning_input,
        proof,
    )


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ObserverSignedMultiroundResultV2:
    """Construction-only terminal state; never a plan certificate."""

    _issuer: InitVar[object]
    status: V075ObserverSignedMultiroundTerminalStatusV2
    schedule_id: str
    schedule_verification_id: str
    root_execution_id: str
    root_model_epoch_id: str
    child_closure_id: str
    child_closure_verification_id: str
    child_closure_status: dynamic.V075LiveDynamicChildClosureStatusV2
    child_execution_ledger_id: str | None
    child_execution_verification_id: str | None
    child_replanning_barrier_id: str | None
    child_replanning_barrier_verification_id: str | None
    promotion_decision_ids: tuple[str, ...]
    promotion_decision_verification_ids: tuple[str, ...]
    promotion_replanning_barrier_ids: tuple[str, ...]
    promotion_replanning_barrier_verification_ids: tuple[str, ...]
    final_model_epoch_id: str
    final_numerical_model_id: str
    final_proof_id: str
    closed_reconciliation_id: str
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.schedule_id, "multiround schedule"),
            (
                self.schedule_verification_id,
                "multiround schedule verification",
            ),
            (self.root_execution_id, "multiround root execution"),
            (self.root_model_epoch_id, "multiround root epoch"),
            (self.child_closure_id, "multiround child closure"),
            (
                self.child_closure_verification_id,
                "multiround child closure verification",
            ),
            (self.final_model_epoch_id, "multiround final epoch"),
            (self.final_numerical_model_id, "multiround final model"),
            (self.final_proof_id, "multiround final proof"),
            (
                self.closed_reconciliation_id,
                "multiround closed reconciliation",
            ),
            *(
                (value, "multiround promotion decision")
                for value in self.promotion_decision_ids
            ),
        ):
            _cid(value, label)
        for value, label in (
            (
                self.child_execution_ledger_id,
                "multiround child execution ledger",
            ),
            (
                self.child_replanning_barrier_id,
                "multiround child replanning barrier",
            ),
            (
                self.child_execution_verification_id,
                "multiround child execution verification",
            ),
            (
                self.child_replanning_barrier_verification_id,
                "multiround child replanning barrier verification",
            ),
        ):
            if value is not None:
                _cid(value, label)
        for values, label in (
            (
                self.promotion_decision_verification_ids,
                "multiround promotion decision verification",
            ),
            (
                self.promotion_replanning_barrier_ids,
                "multiround promotion replanning barrier",
            ),
            (
                self.promotion_replanning_barrier_verification_ids,
                "multiround promotion replanning barrier verification",
            ),
        ):
            for value in values:
                _cid(value, label)
        no_child_execution = self.child_closure_status is not (
            dynamic.V075LiveDynamicChildClosureStatusV2.AUTHORIZED
        )
        fixed_no_execution_status = self.child_closure_status in {
            dynamic.V075LiveDynamicChildClosureStatusV2.CANDIDATE_EARLY_STOP,
            (
                dynamic.V075LiveDynamicChildClosureStatusV2
                .CHILD_ACTION_ROW_CAP_EXCEEDED
            ),
        }
        child_optionals = (
            self.child_execution_ledger_id,
            self.child_execution_verification_id,
            self.child_replanning_barrier_id,
            self.child_replanning_barrier_verification_id,
        )
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.status)
            is not V075ObserverSignedMultiroundTerminalStatusV2
            or type(self.child_closure_status)
            is not dynamic.V075LiveDynamicChildClosureStatusV2
            or type(self.promotion_decision_ids) is not tuple
            or type(self.promotion_decision_verification_ids) is not tuple
            or type(self.promotion_replanning_barrier_ids) is not tuple
            or type(self.promotion_replanning_barrier_verification_ids)
            is not tuple
            or len(self.promotion_decision_ids) > MAXIMUM_PROMOTION_ROUNDS
            or len(set(self.promotion_decision_ids))
            != len(self.promotion_decision_ids)
            or len(self.promotion_decision_verification_ids)
            != len(self.promotion_decision_ids)
            or len(self.promotion_replanning_barrier_ids)
            > len(self.promotion_decision_ids)
            or len(self.promotion_replanning_barrier_verification_ids)
            != len(self.promotion_replanning_barrier_ids)
            or any(
                len(set(values)) != len(values)
                for values in (
                    self.promotion_decision_verification_ids,
                    self.promotion_replanning_barrier_ids,
                    self.promotion_replanning_barrier_verification_ids,
                )
            )
            or no_child_execution
            != all(item is None for item in child_optionals)
            or (
                not no_child_execution
                and any(item is None for item in child_optionals)
            )
        ):
            _fail("multiround terminal result is malformed or caller-minted")
        exact_status = {
            (
                dynamic.V075LiveDynamicChildClosureStatusV2
                .CANDIDATE_EARLY_STOP
            ): V075ObserverSignedMultiroundTerminalStatusV2.CANDIDATE_EARLY_STOP,
            (
                dynamic.V075LiveDynamicChildClosureStatusV2
                .CHILD_ACTION_ROW_CAP_EXCEEDED
            ): (
                V075ObserverSignedMultiroundTerminalStatusV2
                .CHILD_ACTION_ROW_CAP_EXCEEDED
            ),
        }.get(self.child_closure_status)
        if fixed_no_execution_status and self.status is not exact_status:
            _fail("multiround terminal status differs from child closure")
        if fixed_no_execution_status and self.promotion_decision_ids:
            _fail("candidate/cap child closure cannot emit promotion work")
        if (
            self.status
            is V075ObserverSignedMultiroundTerminalStatusV2
            .CANDIDATE_AFTER_CHILD_CLOSURE
            and self.child_closure_status
            is not dynamic.V075LiveDynamicChildClosureStatusV2.AUTHORIZED
        ):
            _fail("post-child candidate lacks its authorized child barrier")
        decision_count = len(self.promotion_decision_ids)
        barrier_count = len(self.promotion_replanning_barrier_ids)
        expected_counts = {
            (
                V075ObserverSignedMultiroundTerminalStatusV2
                .CANDIDATE_EARLY_STOP
            ): (0, 0),
            (
                V075ObserverSignedMultiroundTerminalStatusV2
                .CHILD_ACTION_ROW_CAP_EXCEEDED
            ): (0, 0),
            (
                V075ObserverSignedMultiroundTerminalStatusV2
                .CANDIDATE_AFTER_CHILD_CLOSURE
            ): (0, 0),
            (
                V075ObserverSignedMultiroundTerminalStatusV2
                .CANDIDATE_AFTER_PROMOTION_ONE
            ): (1, 1),
            (
                V075ObserverSignedMultiroundTerminalStatusV2
                .CANDIDATE_AFTER_PROMOTION_TWO
            ): (2, 2),
            (
                V075ObserverSignedMultiroundTerminalStatusV2
                .PROMOTION_BUDGET_EXHAUSTED
            ): (2, 2),
        }.get(self.status)
        if expected_counts is not None and (
            decision_count,
            barrier_count,
        ) != expected_counts:
            _fail("multiround terminal status differs from promotion lineage")
        if (
            self.status
            is V075ObserverSignedMultiroundTerminalStatusV2
            .NO_ELIGIBLE_PROMOTION_ROW
            and (
                decision_count not in (1, 2)
                or barrier_count != decision_count - 1
            )
        ):
            _fail("empty promotion frontier has an invalid decision lineage")
        object.__setattr__(
            self,
            "_result_id",
            _hash("result", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_observer_signed_multiround_occurrence_result.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "status": self.status.value,
            "schedule_id": self.schedule_id,
            "schedule_verification_id": self.schedule_verification_id,
            "root_execution_id": self.root_execution_id,
            "root_model_epoch_id": self.root_model_epoch_id,
            "child_closure_id": self.child_closure_id,
            "child_closure_verification_id": (
                self.child_closure_verification_id
            ),
            "child_closure_status": self.child_closure_status.value,
            "child_execution_ledger_id": self.child_execution_ledger_id,
            "child_execution_verification_id": (
                self.child_execution_verification_id
            ),
            "child_replanning_barrier_id": (
                self.child_replanning_barrier_id
            ),
            "child_replanning_barrier_verification_id": (
                self.child_replanning_barrier_verification_id
            ),
            "promotion_decision_ids": list(self.promotion_decision_ids),
            "promotion_decision_verification_ids": list(
                self.promotion_decision_verification_ids
            ),
            "promotion_replanning_barrier_ids": list(
                self.promotion_replanning_barrier_ids
            ),
            "promotion_replanning_barrier_verification_ids": list(
                self.promotion_replanning_barrier_verification_ids
            ),
            "maximum_promotion_rounds": MAXIMUM_PROMOTION_ROUNDS,
            "final_model_epoch_id": self.final_model_epoch_id,
            "final_numerical_model_id": self.final_numerical_model_id,
            "final_proof_id": self.final_proof_id,
            "closed_reconciliation_id": self.closed_reconciliation_id,
            "closed_lineage_recompiled": True,
            "partial_child_closure_permitted": False,
            "raw_post_child_epoch_consumable_without_barrier": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    @property
    def canonical_bytes(self) -> bytes:
        raw = canonical_json_bytes(self.to_document())
        if len(raw) > MAX_CANONICAL_RESULT_BYTES:  # pragma: no cover
            _fail("multiround result exceeds its canonical byte cap")
        return raw

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _freeze_root_epoch(
    *,
    controller: control.V075ConstructionControlledPrivateObserverV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
) -> live_model.V075LiveIncrementalModelEpochV2:
    return live_model.freeze_v075_live_incremental_model_epoch_v2(
        occurrence_identity=schedule.occurrence,
        controlled_appends=controller.controlled_appends,
        support_freezes=controller.support_freezes,
        open_prefix_verification=controller.freeze_owned_open_prefix_v2(),
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
        parent_epoch=None,
    )


def _freeze_child_epoch_without_consuming_proof(
    *,
    controller: control.V075ConstructionControlledPrivateObserverV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    parent_epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> live_model.V075LiveIncrementalModelEpochV2:
    """Construct a child epoch that remains opaque until a dynamic barrier."""

    return live_model.freeze_v075_live_incremental_model_epoch_v2(
        occurrence_identity=schedule.occurrence,
        controlled_appends=controller.controlled_appends,
        support_freezes=controller.support_freezes,
        open_prefix_verification=controller.freeze_owned_open_prefix_v2(),
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
        parent_epoch=parent_epoch,
    )


def _execute_authorized_child_closure(
    *,
    controller: control.V075ConstructionControlledPrivateObserverV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    closure: dynamic.V075LiveDynamicChildClosureV2,
    closure_verification: dynamic.V075LiveDynamicChildClosureVerificationV2,
) -> tuple[
    live_model.V075LiveIncrementalModelEpochV2,
    dynamic.V075LiveDynamicChildExecutionLedgerV2,
    dynamic.V075LiveDynamicChildExecutionVerificationV2,
    dynamic.V075LiveDynamicChildReplanningBarrierV2,
    dynamic.V075LiveDynamicChildReplanningBarrierVerificationV2,
]:
    """Execute the whole authorized child closure and cross its hard barrier."""

    if (
        closure.status
        is not dynamic.V075LiveDynamicChildClosureStatusV2.AUTHORIZED
        or not closure.discovery_intents
        or len(closure.discovery_intents)
        != len(closure.validation_templates)
    ):
        _fail("child executor requires one nonempty authorized closure")
    templates = {
        item.row_binding_id: item
        for item in closure.validation_templates
    }
    if len(templates) != len(closure.validation_templates):
        _fail("child validation templates alias one row")
    source_append_count = len(controller.controlled_appends)
    source_freeze_count = len(controller.support_freezes)
    for discovery in closure.discovery_intents:
        row_id = discovery.row_binding.row_binding_id
        template = templates.get(row_id)
        if template is None:
            _fail("authorized child discovery lacks its validation template")
        intent = controller.prepare_batch_intent_v2(
            stream_identity=discovery.stream_identity,
            semantic_authority_role=(
                control.V075ControlledBatchSemanticAuthorityRoleV2
                .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
            ),
            semantic_authority_schema=(
                control.V075ControlledBatchSemanticAuthoritySchemaV2
                .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
            ),
            semantic_artifact_id=discovery.intent_id,
            semantic_verification_id=closure_verification.verification_id,
            stage=control.V075ControlledBatchStageV2.CHILD_DISCOVERY,
            round_index=0,
            support_freeze_id=None,
            accepted_draw_start=1,
            accepted_draw_count=dynamic.CHILD_DISCOVERY_DRAWS,
            accepted_draw_cap=dynamic.CHILD_DISCOVERY_DRAWS,
        )
        discovery_append = controller.execute_batch_intent_v2(intent)
        support = controller.freeze_complete_support_v2(
            discovery_append=discovery_append,
        )
        validation_stream = (
            control.derive_v075_controlled_validation_stream_v2(
                support_freeze=support,
            )
        )
        validation_intent = controller.prepare_batch_intent_v2(
            stream_identity=validation_stream,
            semantic_authority_role=(
                control.V075ControlledBatchSemanticAuthorityRoleV2
                .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
            ),
            semantic_authority_schema=(
                control.V075ControlledBatchSemanticAuthoritySchemaV2
                .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
            ),
            semantic_artifact_id=template.template_id,
            semantic_verification_id=closure_verification.verification_id,
            stage=control.V075ControlledBatchStageV2.CHILD_VALIDATION,
            round_index=0,
            support_freeze_id=support.freeze_id,
            accepted_draw_start=1,
            accepted_draw_count=dynamic.CHILD_VALIDATION_DRAWS,
            accepted_draw_cap=(
                dynamic.CHILD_VALIDATION_DRAWS
                + dynamic.MAXIMUM_PROMOTION_ROUNDS
                * dynamic.PROMOTION_DRAWS
            ),
        )
        controller.execute_batch_intent_v2(validation_intent)
    expected_count = len(closure.discovery_intents)
    if (
        len(controller.controlled_appends) - source_append_count
        != 2 * expected_count
        or len(controller.support_freezes) - source_freeze_count
        != expected_count
    ):
        _fail("authorized child closure executed partially or with extra work")
    prefix = controller.freeze_owned_open_prefix_v2()
    ledger = dynamic.freeze_v075_live_dynamic_child_execution_ledger_v2(
        closure=closure,
        closure_verification=closure_verification,
        open_prefix_verification=prefix,
    )
    ledger, ledger_verification = (
        dynamic.verify_v075_live_dynamic_child_execution_ledger_bytes_v2(
            closure=closure,
            closure_verification=closure_verification,
            open_prefix_verification=prefix,
            claimed_bytes=ledger.canonical_bytes,
        )
    )
    # Do not inspect the resulting proof here.  Only the dynamic barrier may
    # expose its verified outcome to the state machine.
    resulting_epoch = _freeze_child_epoch_without_consuming_proof(
        controller=controller,
        schedule=schedule,
        parent_epoch=closure.source_epoch,
    )
    barrier = dynamic.freeze_v075_live_dynamic_child_replanning_barrier_v2(
        closure=closure,
        closure_verification=closure_verification,
        execution_ledger=ledger,
        execution_verification=ledger_verification,
        resulting_epoch=resulting_epoch,
    )
    barrier, barrier_verification = (
        dynamic.verify_v075_live_dynamic_child_replanning_barrier_bytes_v2(
            closure=closure,
            closure_verification=closure_verification,
            execution_ledger=ledger,
            execution_verification=ledger_verification,
            resulting_epoch=resulting_epoch,
            claimed_bytes=barrier.canonical_bytes,
        )
    )
    return (
        resulting_epoch,
        ledger,
        ledger_verification,
        barrier,
        barrier_verification,
    )


def _freeze_exact_promotion_decision(
    *,
    epoch: live_model.V075LiveIncrementalModelEpochV2,
    round_index: int,
    child_closure: dynamic.V075LiveDynamicChildClosureV2,
    child_closure_verification: (
        dynamic.V075LiveDynamicChildClosureVerificationV2
    ),
    child_ledger: dynamic.V075LiveDynamicChildExecutionLedgerV2 | None,
    child_ledger_verification: (
        dynamic.V075LiveDynamicChildExecutionVerificationV2 | None
    ),
    child_barrier: (
        dynamic.V075LiveDynamicChildReplanningBarrierV2 | None
    ),
    child_barrier_verification: (
        dynamic.V075LiveDynamicChildReplanningBarrierVerificationV2 | None
    ),
    previous_decision: dynamic.V075LivePromotionDecisionV2 | None,
    previous_barrier: dynamic.V075LivePromotionReplanningBarrierV2 | None,
) -> tuple[
    dynamic.V075LivePromotionDecisionV2,
    dynamic.V075LivePromotionDecisionVerificationV2,
]:
    decision = dynamic.freeze_v075_live_promotion_decision_v2(
        source_epoch=epoch,
        round_index=round_index,
        child_closure=child_closure,
        child_closure_verification=child_closure_verification,
        child_execution_ledger=child_ledger,
        child_execution_verification=child_ledger_verification,
        child_replanning_barrier=child_barrier,
        child_replanning_barrier_verification=child_barrier_verification,
        previous_decision=previous_decision,
        previous_replanning_barrier=previous_barrier,
    )
    return dynamic.verify_v075_live_promotion_decision_bytes_v2(
        source_epoch=epoch,
        round_index=round_index,
        child_closure=child_closure,
        child_closure_verification=child_closure_verification,
        child_execution_ledger=child_ledger,
        child_execution_verification=child_ledger_verification,
        child_replanning_barrier=child_barrier,
        child_replanning_barrier_verification=child_barrier_verification,
        previous_decision=previous_decision,
        previous_replanning_barrier=previous_barrier,
        claimed_bytes=decision.canonical_bytes,
    )


def _execute_authorized_promotion(
    *,
    controller: control.V075ConstructionControlledPrivateObserverV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    decision: dynamic.V075LivePromotionDecisionV2,
    decision_verification: dynamic.V075LivePromotionDecisionVerificationV2,
    child_closure: dynamic.V075LiveDynamicChildClosureV2,
    child_closure_verification: (
        dynamic.V075LiveDynamicChildClosureVerificationV2
    ),
    child_ledger: dynamic.V075LiveDynamicChildExecutionLedgerV2 | None,
    child_ledger_verification: (
        dynamic.V075LiveDynamicChildExecutionVerificationV2 | None
    ),
    child_barrier: (
        dynamic.V075LiveDynamicChildReplanningBarrierV2 | None
    ),
    child_barrier_verification: (
        dynamic.V075LiveDynamicChildReplanningBarrierVerificationV2 | None
    ),
    previous_barrier: dynamic.V075LivePromotionReplanningBarrierV2 | None,
) -> tuple[
    live_model.V075LiveIncrementalModelEpochV2,
    dynamic.V075LivePromotionReplanningBarrierV2,
    dynamic.V075LivePromotionReplanningBarrierVerificationV2,
]:
    """Execute one +2048 append; consume proof only after its hard barrier."""

    intent = decision.intent
    if (
        decision.status
        is not dynamic.V075LivePromotionDecisionStatusV2.AUTHORIZED
        or intent is None
    ):
        _fail("promotion executor requires one authorized exact decision")
    stage = (
        control.V075ControlledBatchStageV2.ROOT_VALIDATION
        if intent.stage == "ROOT_VALIDATION"
        else control.V075ControlledBatchStageV2.CHILD_VALIDATION
    )
    controlled_intent = controller.prepare_batch_intent_v2(
        stream_identity=intent.stream_identity,
        semantic_authority_role=(
            control.V075ControlledBatchSemanticAuthorityRoleV2
            .LIVE_PROMOTION_AUTHORIZATION
        ),
        semantic_authority_schema=(
            control.V075ControlledBatchSemanticAuthoritySchemaV2
            .LIVE_PROMOTION_AUTHORIZATION
        ),
        semantic_artifact_id=intent.intent_id,
        semantic_verification_id=decision_verification.verification_id,
        stage=stage,
        round_index=decision.round_index,
        support_freeze_id=intent.support_freeze_id,
        accepted_draw_start=intent.accepted_draw_start,
        accepted_draw_count=intent.accepted_draw_count,
        accepted_draw_cap=intent.accepted_draw_cap,
    )
    controller.execute_batch_intent_v2(controlled_intent)
    resulting_epoch = _freeze_child_epoch_without_consuming_proof(
        controller=controller,
        schedule=schedule,
        parent_epoch=decision.source_epoch,
    )
    barrier = dynamic.freeze_v075_live_promotion_replanning_barrier_v2(
        decision=decision,
        decision_verification=decision_verification,
        resulting_epoch=resulting_epoch,
        child_closure=child_closure,
        child_closure_verification=child_closure_verification,
        child_execution_ledger=child_ledger,
        child_execution_verification=child_ledger_verification,
        child_replanning_barrier=child_barrier,
        child_replanning_barrier_verification=child_barrier_verification,
        previous_replanning_barrier=previous_barrier,
    )
    barrier, barrier_verification = (
        dynamic.verify_v075_live_promotion_replanning_barrier_bytes_v2(
            decision=decision,
            decision_verification=decision_verification,
            resulting_epoch=resulting_epoch,
            child_closure=child_closure,
            child_closure_verification=child_closure_verification,
            child_execution_ledger=child_ledger,
            child_execution_verification=child_ledger_verification,
            child_replanning_barrier=child_barrier,
            child_replanning_barrier_verification=(
                child_barrier_verification
            ),
            previous_replanning_barrier=previous_barrier,
            claimed_bytes=barrier.canonical_bytes,
        )
    )
    return resulting_epoch, barrier, barrier_verification


def _closed_result(
    *,
    status: V075ObserverSignedMultiroundTerminalStatusV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    verification: acquisition.V075InitialAcquisitionVerificationV2,
    root_execution: V075ObserverSignedRootExecutionV2,
    root_epoch: live_model.V075LiveIncrementalModelEpochV2,
    child_closure: dynamic.V075LiveDynamicChildClosureV2,
    child_closure_verification: (
        dynamic.V075LiveDynamicChildClosureVerificationV2
    ),
    child_ledger: (
        dynamic.V075LiveDynamicChildExecutionLedgerV2 | None
    ),
    child_ledger_verification: (
        dynamic.V075LiveDynamicChildExecutionVerificationV2 | None
    ),
    child_barrier: (
        dynamic.V075LiveDynamicChildReplanningBarrierV2 | None
    ),
    child_barrier_verification: (
        dynamic.V075LiveDynamicChildReplanningBarrierVerificationV2 | None
    ),
    promotion_decisions: tuple[
        dynamic.V075LivePromotionDecisionV2,
        ...,
    ],
    promotion_decision_verifications: tuple[
        dynamic.V075LivePromotionDecisionVerificationV2,
        ...,
    ],
    promotion_barriers: tuple[
        dynamic.V075LivePromotionReplanningBarrierV2,
        ...,
    ],
    promotion_barrier_verifications: tuple[
        dynamic.V075LivePromotionReplanningBarrierVerificationV2,
        ...,
    ],
    final_epoch: live_model.V075LiveIncrementalModelEpochV2,
    reconciliation: V075ObserverSignedClosedReconciliationV2,
) -> V075ObserverSignedMultiroundResultV2:
    if (
        type(child_closure_verification)
        is not dynamic.V075LiveDynamicChildClosureVerificationV2
        or child_closure_verification.closure_id
        != child_closure.closure_id
        or child_closure_verification.source_model_epoch_id
        != child_closure.source_epoch.model_epoch_id
        or child_closure_verification.source_proof_id
        != child_closure.source_epoch.proof.proof_id
        or child_closure_verification.source_head_id
        != child_closure.source_epoch.head_id
        or child_closure_verification.status is not child_closure.status
        or child_closure_verification.discovery_intent_ids
        != tuple(
            item.intent_id for item in child_closure.discovery_intents
        )
        or child_closure_verification.validation_template_ids
        != tuple(
            item.template_id
            for item in child_closure.validation_templates
        )
    ):
        _fail("multiround child closure verification is stale or foreign")
    return V075ObserverSignedMultiroundResultV2(
        _issuer=_RESULT_ISSUER,
        status=status,
        schedule_id=schedule.schedule_id,
        schedule_verification_id=verification.verification_id,
        root_execution_id=root_execution.execution_id,
        root_model_epoch_id=root_epoch.model_epoch_id,
        child_closure_id=child_closure.closure_id,
        child_closure_verification_id=(
            child_closure_verification.verification_id
        ),
        child_closure_status=child_closure.status,
        child_execution_ledger_id=(
            None if child_ledger is None else child_ledger.ledger_id
        ),
        child_execution_verification_id=(
            None
            if child_ledger_verification is None
            else child_ledger_verification.verification_id
        ),
        child_replanning_barrier_id=(
            None if child_barrier is None else child_barrier.barrier_id
        ),
        child_replanning_barrier_verification_id=(
            None
            if child_barrier_verification is None
            else child_barrier_verification.verification_id
        ),
        promotion_decision_ids=tuple(
            item.decision_id for item in promotion_decisions
        ),
        promotion_decision_verification_ids=tuple(
            item.verification_id
            for item in promotion_decision_verifications
        ),
        promotion_replanning_barrier_ids=tuple(
            item.barrier_id for item in promotion_barriers
        ),
        promotion_replanning_barrier_verification_ids=tuple(
            item.verification_id
            for item in promotion_barrier_verifications
        ),
        final_model_epoch_id=final_epoch.model_epoch_id,
        final_numerical_model_id=final_epoch.model.model_id,
        final_proof_id=final_epoch.proof.proof_id,
        closed_reconciliation_id=reconciliation.reconciliation_id,
    )


def run_v075_construction_observer_signed_multiround_occurrence_v2(
    *,
    repository_root: str | Path,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    schedule_verification: acquisition.V075InitialAcquisitionVerificationV2,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Any]]],
    observer_signer: observer.V075ObserverEvidenceSignerProtocolV2,
    session_external_id: str,
    evidence_sink: (
        Callable[[Mapping[str, Any]], Any] | None
    ) = None,
) -> V075ObserverSignedMultiroundResultV2:
    """Run one exact construction occurrence through at most two promotions."""

    if evidence_sink is not None and not callable(evidence_sink):
        _fail("construction evidence sink must be callable or absent")
    exact_schedule, exact_verification = _exact_initial_authority(
        repository_root=repository_root,
        namespace=namespace,
        schedule=schedule,
        verification=schedule_verification,
    )
    environment = _canonical_private_environment(private_environment)
    try:
        controller = (
            control.open_v075_construction_controlled_private_observer_v2(
                authority=authority,
                namespace=namespace,
                private_salt=private_salt,
                private_environment=environment,
                observer_signer=observer_signer,
                session_external_id=session_external_id,
                occurrence_identity=exact_schedule.occurrence,
            )
        )
        root_execution = _execute_initial_root_schedule(
            controller=controller,
            namespace=namespace,
            schedule=exact_schedule,
            verification=exact_verification,
        )
        root_epoch = _freeze_root_epoch(
            controller=controller,
            schedule=exact_schedule,
        )
        child_closure, child_verification = (
            dynamic.verify_v075_live_dynamic_child_closure_bytes_v2(
                source_epoch=root_epoch,
                namespace=namespace,
                claimed_bytes=(
                    dynamic.freeze_v075_live_dynamic_child_closure_v2(
                        source_epoch=root_epoch,
                        namespace=namespace,
                    ).canonical_bytes
                ),
            )
        )
    except Exception as error:
        if type(error) in {
            V075ObserverSignedMultiroundV2InvariantViolation,
        }:
            raise
        raise V075ObserverSignedMultiroundV2InvariantViolation(
            "observer-signed root construction failed"
        ) from error
    current_epoch = root_epoch
    child_ledger = None
    child_ledger_verification = None
    child_barrier = None
    child_barrier_verification = None
    promotion_decisions: list[dynamic.V075LivePromotionDecisionV2] = []
    promotion_decision_verifications: list[
        dynamic.V075LivePromotionDecisionVerificationV2
    ] = []
    promotion_barriers: list[
        dynamic.V075LivePromotionReplanningBarrierV2
    ] = []
    promotion_barrier_verifications: list[
        dynamic.V075LivePromotionReplanningBarrierVerificationV2
    ] = []
    terminal = None
    if (
        child_closure.status
        is dynamic.V075LiveDynamicChildClosureStatusV2.CANDIDATE_EARLY_STOP
    ):
        terminal = (
            V075ObserverSignedMultiroundTerminalStatusV2.CANDIDATE_EARLY_STOP
        )
    elif child_closure.status is (
        dynamic.V075LiveDynamicChildClosureStatusV2
        .CHILD_ACTION_ROW_CAP_EXCEEDED
    ):
        terminal = (
            V075ObserverSignedMultiroundTerminalStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        )
    elif (
        child_closure.status
        is dynamic.V075LiveDynamicChildClosureStatusV2.AUTHORIZED
    ):
        (
            current_epoch,
            child_ledger,
            child_ledger_verification,
            child_barrier,
            child_barrier_verification,
        ) = _execute_authorized_child_closure(
            controller=controller,
            schedule=exact_schedule,
            closure=child_closure,
            closure_verification=child_verification,
        )
        # This outcome is consumed only from the independently replayed hard
        # barrier; the raw resulting epoch proof was opaque until this point.
        if (
            child_barrier.resulting_outcome
            is planning.V075NumericalOutcomeV2.CANDIDATE
        ):
            terminal = (
                V075ObserverSignedMultiroundTerminalStatusV2
                .CANDIDATE_AFTER_CHILD_CLOSURE
            )
        elif child_barrier.resulting_outcome is not (
            planning.V075NumericalOutcomeV2.FAILED_FRONTIER
        ):
            _fail("child barrier exposed an unknown numerical outcome")
    elif child_closure.status is not (
        dynamic.V075LiveDynamicChildClosureStatusV2.ALREADY_COMPLETE
    ):
        _fail("dynamic child closure returned an unknown state")

    previous_decision = None
    previous_promotion_barrier = None
    for round_index in range(1, MAXIMUM_PROMOTION_ROUNDS + 1):
        if terminal is not None:
            break
        decision, decision_verification = _freeze_exact_promotion_decision(
            epoch=current_epoch,
            round_index=round_index,
            child_closure=child_closure,
            child_closure_verification=child_verification,
            child_ledger=child_ledger,
            child_ledger_verification=child_ledger_verification,
            child_barrier=child_barrier,
            child_barrier_verification=child_barrier_verification,
            previous_decision=previous_decision,
            previous_barrier=previous_promotion_barrier,
        )
        promotion_decisions.append(decision)
        promotion_decision_verifications.append(decision_verification)
        if decision.status is (
            dynamic.V075LivePromotionDecisionStatusV2.CANDIDATE_EARLY_STOP
        ):
            _fail(
                "promotion decision candidate contradicted the preceding "
                "verified failed outcome"
            )
        if decision.status is (
            dynamic.V075LivePromotionDecisionStatusV2
            .NO_ELIGIBLE_FRONTIER_ROW
        ):
            terminal = (
                V075ObserverSignedMultiroundTerminalStatusV2
                .NO_ELIGIBLE_PROMOTION_ROW
            )
            break
        if decision.status is not (
            dynamic.V075LivePromotionDecisionStatusV2.AUTHORIZED
        ):
            _fail("promotion decision returned an unknown state")
        (
            current_epoch,
            promotion_barrier,
            promotion_barrier_verification,
        ) = _execute_authorized_promotion(
            controller=controller,
            schedule=exact_schedule,
            decision=decision,
            decision_verification=decision_verification,
            child_closure=child_closure,
            child_closure_verification=child_verification,
            child_ledger=child_ledger,
            child_ledger_verification=child_ledger_verification,
            child_barrier=child_barrier,
            child_barrier_verification=child_barrier_verification,
            previous_barrier=previous_promotion_barrier,
        )
        promotion_barriers.append(promotion_barrier)
        promotion_barrier_verifications.append(
            promotion_barrier_verification
        )
        # As above, consume only the barrier's replayed outcome.
        if (
            promotion_barrier.resulting_outcome
            is planning.V075NumericalOutcomeV2.CANDIDATE
        ):
            terminal = (
                V075ObserverSignedMultiroundTerminalStatusV2
                .CANDIDATE_AFTER_PROMOTION_ONE
                if round_index == 1
                else (
                    V075ObserverSignedMultiroundTerminalStatusV2
                    .CANDIDATE_AFTER_PROMOTION_TWO
                )
            )
            break
        if promotion_barrier.resulting_outcome is not (
            planning.V075NumericalOutcomeV2.FAILED_FRONTIER
        ):
            _fail("promotion barrier exposed an unknown numerical outcome")
        if round_index == MAXIMUM_PROMOTION_ROUNDS:
            terminal = (
                V075ObserverSignedMultiroundTerminalStatusV2
                .PROMOTION_BUDGET_EXHAUSTED
            )
            break
        previous_decision = decision
        previous_promotion_barrier = promotion_barrier
    if terminal is None:  # pragma: no cover - state-machine exhaustiveness
        _fail("multiround state machine reached no terminal construction state")
    reconciliation = _close_and_reconcile(
        repository_root=repository_root,
        controller=controller,
        schedule=exact_schedule,
        final_epoch=current_epoch,
        authority=authority,
        namespace=namespace,
        private_salt=private_salt,
        private_environment=environment,
    )
    result = _closed_result(
        status=terminal,
        schedule=exact_schedule,
        verification=exact_verification,
        root_execution=root_execution,
        root_epoch=root_epoch,
        child_closure=child_closure,
        child_closure_verification=child_verification,
        child_ledger=child_ledger,
        child_ledger_verification=child_ledger_verification,
        child_barrier=child_barrier,
        child_barrier_verification=child_barrier_verification,
        promotion_decisions=tuple(promotion_decisions),
        promotion_decision_verifications=tuple(
            promotion_decision_verifications
        ),
        promotion_barriers=tuple(promotion_barriers),
        promotion_barrier_verifications=tuple(
            promotion_barrier_verifications
        ),
        final_epoch=current_epoch,
        reconciliation=reconciliation,
    )
    if evidence_sink is not None:
        roots = MappingProxyType(
            {
                "initial_schedule": exact_schedule,
                "initial_schedule_verification": exact_verification,
                "root_execution": root_execution,
                "root_model_epoch": root_epoch,
                "child_closure": child_closure,
                "child_closure_verification": child_verification,
                "child_execution_ledger": child_ledger,
                "child_execution_verification": (
                    child_ledger_verification
                ),
                "child_replanning_barrier": child_barrier,
                "child_replanning_barrier_verification": (
                    child_barrier_verification
                ),
                "promotion_decisions": tuple(promotion_decisions),
                "promotion_decision_verifications": tuple(
                    promotion_decision_verifications
                ),
                "promotion_replanning_barriers": tuple(
                    promotion_barriers
                ),
                "promotion_replanning_barrier_verifications": tuple(
                    promotion_barrier_verifications
                ),
                "final_model_epoch": current_epoch,
                "controlled_journal_closure": (
                    reconciliation.controlled_closure
                ),
                "construction_lineage": reconciliation.lineage,
                "construction_lifecycle": reconciliation.lifecycle,
                "closed_planning_input": reconciliation.planning_input,
                "closed_planning_proof": reconciliation.closed_proof,
                "closed_reconciliation": reconciliation,
                "multiround_result": result,
            }
        )
        before = _snapshot_construction_evidence_roots(roots)
        try:
            evidence_sink(roots)
        except Exception as error:
            raise V075ObserverSignedMultiroundV2InvariantViolation(
                "construction evidence sink failed after exact closure"
            ) from error
        if _snapshot_construction_evidence_roots(roots) != before:
            _fail("construction evidence sink mutated immutable typed roots")
    return result


def open_v075_production_observer_signed_multiround_occurrence_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075ObserverSignedMultiroundProductionV2NotReady(
        PRODUCTION_BLOCKER
    )


__all__ = [
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "MAXIMUM_PROMOTION_ROUNDS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PROFILE_KEY",
    "PRODUCTION_AUTHORIZING",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "TERMINAL_CLASS",
    "TERMINAL_SCOPE",
    "V075ObserverSignedClosedReconciliationV2",
    "V075ObserverSignedMultiroundProductionV2NotReady",
    "V075ObserverSignedMultiroundResultV2",
    "V075ObserverSignedMultiroundTerminalStatusV2",
    "V075ObserverSignedMultiroundV2InvariantViolation",
    "V075ObserverSignedRootExecutionV2",
    "freeze_v075_construction_closed_reconciliation_v2",
    "open_v075_production_observer_signed_multiround_occurrence_v2",
    "run_v075_construction_observer_signed_multiround_occurrence_v2",
]
