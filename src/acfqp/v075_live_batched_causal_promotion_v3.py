"""Capped validation promotion after the V3 causal child epoch.

The causal child executor materializes only the complete child catalogues named
by the failed proof frontier.  Its first resulting model can still fail solely
because one or more fully materialized rows require the next registered
validation checkpoint.  This module implements that exact successor:

* rank eligible failed-frontier rows by the preregistered V2 rule;
* authorize one +2048 validation extension at a time;
* execute the extension through the owner-controlled signed observer;
* compile one append-only model epoch; and
* require a typed proof barrier before another decision is consumed.

At most two promotion appends are executed.  The semantic intent presented to
the controller is byte-identical to the established V2 promotion schema; the
new V3 decision and barrier bind that semantic projection to the causal child
authorization, execution ledger, and replanning barrier.  This remains a
construction boundary: the observer stays open and no terminal, certificate,
CounterRecord, or campaign claim is issued here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_live_batched_causal_child_authority_v3 as causal
from acfqp import v075_live_batched_causal_child_execution_v3 as child_execution
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "3.0.0"
PROPOSED_CONTRACT_VERSION = "1.63.0"
PROFILE_KEY = "v075_live_batched_causal_promotion_v3"
MAX_CANONICAL_INPUT_BYTES = 128 * 1024 * 1024

PROMOTION_DRAWS = dynamic.PROMOTION_DRAWS
MAXIMUM_PROMOTION_ROUNDS = dynamic.MAXIMUM_PROMOTION_ROUNDS
PROMOTION_SELECTION_RULE = dynamic.PROMOTION_SELECTION_RULE

PRODUCTION_INTEGRATION_READY = False
OBSERVER_CLOSE_PERFORMED = False
TERMINAL_CLASSIFICATION_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
COUNTER_RECORD_ISSUANCE_ALLOWED = False

DOMAIN_TAGS = {
    "decision": "acfqp:v075-live-batched-causal-promotion-decision:v3",
    "decision_verification": (
        "acfqp:v075-live-batched-causal-promotion-decision-verification:v3"
    ),
    "barrier": "acfqp:v075-live-batched-causal-promotion-barrier:v3",
    "barrier_verification": (
        "acfqp:v075-live-batched-causal-promotion-barrier-verification:v3"
    ),
    "bundle": "acfqp:v075-live-batched-causal-promotion-bundle:v3",
    "bundle_verification": (
        "acfqp:v075-live-batched-causal-promotion-bundle-verification:v3"
    ),
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V3 causal promotion domains must be unique")


class V075LiveBatchedCausalPromotionV3InvariantViolation(ValueError):
    """The child lineage, selected row, append, model, or proof changed."""


def _fail(message: str) -> NoReturn:
    raise V075LiveBatchedCausalPromotionV3InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075LiveBatchedCausalPromotionV3InvariantViolation(
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
        raise V075LiveBatchedCausalPromotionV3InvariantViolation(
            str(error)
        ) from error


def _semantic_hash(payload: Mapping[str, Any]) -> str:
    """Use the frozen V2 promotion-intent content domain exactly."""

    return hashlib.sha256(
        dynamic.DOMAIN_TAGS["promotion_intent"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _strict_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_CANONICAL_INPUT_BYTES:
        _fail(f"{label} bytes are absent or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075LiveBatchedCausalPromotionV3InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


def _operational_epoch(
    epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> live_model.V075LiveIncrementalModelEpochV2:
    try:
        return live_model._validate_operational_parent(epoch)  # noqa: SLF001
    except Exception as error:
        raise V075LiveBatchedCausalPromotionV3InvariantViolation(
            "promotion epoch lacks immutable same-process provenance"
        ) from error


def _replay_epoch(
    epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> live_model.V075LiveIncrementalModelEpochV2:
    try:
        replayed = live_model.replay_v075_live_incremental_model_epoch_v2(
            epoch
        )
    except Exception as error:
        raise V075LiveBatchedCausalPromotionV3InvariantViolation(
            "promotion epoch exact replay failed"
        ) from error
    if (
        replayed.model_epoch_id != epoch.model_epoch_id
        or replayed.canonical_bytes != epoch.canonical_bytes
    ):
        _fail("promotion epoch differs from exact replay")
    return replayed


def _exact_child_bundle(
    bundle: child_execution.V075LiveBatchedCausalExecutionBundleV3,
    *,
    portable_replay: bool,
) -> child_execution.V075LiveBatchedCausalExecutionBundleV3:
    """Recompute every causal predecessor consumed by promotion."""

    if type(bundle) is not child_execution.V075LiveBatchedCausalExecutionBundleV3:
        _fail("promotion predecessor is not one causal execution bundle")
    authorization = bundle.authorization
    if not authorization.discovery_intents:
        _fail("promotion predecessor has no authorized child rows")
    namespace = authorization.discovery_intents[0].stream_identity.namespace
    try:
        exact_authorization, exact_authorization_verification = (
            causal.verify_v075_live_batched_causal_child_authorization_bytes_v3(
                source_epoch=authorization.source_closure.source_epoch,
                namespace=namespace,
                claimed_bytes=authorization.canonical_bytes,
            )
        )
        if portable_replay:
            exact_ledger, exact_ledger_verification = (
                child_execution
                .verify_v075_live_batched_causal_execution_ledger_bytes_v3(
                    authorization=exact_authorization,
                    authorization_verification=exact_authorization_verification,
                    open_prefix_verification=(
                        bundle.resulting_epoch.open_prefix_verification
                    ),
                    claimed_bytes=bundle.ledger.canonical_bytes,
                )
            )
            exact_barrier, exact_barrier_verification = (
                child_execution
                .verify_v075_live_batched_causal_replanning_barrier_bytes_v3(
                    authorization=exact_authorization,
                    authorization_verification=exact_authorization_verification,
                    execution_ledger=exact_ledger,
                    execution_verification=exact_ledger_verification,
                    resulting_epoch=bundle.resulting_epoch,
                    claimed_bytes=bundle.barrier.canonical_bytes,
                )
            )
            exact_epoch = _replay_epoch(bundle.resulting_epoch)
        else:
            exact_ledger = (
                child_execution
                .freeze_v075_live_batched_causal_execution_ledger_v3(
                    authorization=exact_authorization,
                    authorization_verification=exact_authorization_verification,
                    open_prefix_verification=(
                        bundle.resulting_epoch.open_prefix_verification
                    ),
                )
            )
            exact_ledger_verification = (
                child_execution._exact_ledger_verification(  # noqa: SLF001
                    exact_ledger
                )
            )
            exact_barrier = (
                child_execution
                .freeze_v075_live_batched_causal_replanning_barrier_v3(
                    authorization=exact_authorization,
                    authorization_verification=exact_authorization_verification,
                    execution_ledger=exact_ledger,
                    execution_verification=exact_ledger_verification,
                    resulting_epoch=bundle.resulting_epoch,
                )
            )
            exact_barrier_verification = (
                child_execution.V075LiveBatchedCausalBarrierVerificationV3(
                    child_execution._BARRIER_VERIFICATION_ISSUER,  # noqa: SLF001
                    exact_barrier.barrier_id,
                    exact_barrier.authorization_id,
                    exact_barrier.execution_ledger_id,
                    exact_barrier.source_model_epoch_id,
                    exact_barrier.resulting_model_epoch_id,
                    exact_barrier.resulting_proof_id,
                )
            )
            exact_epoch = _operational_epoch(bundle.resulting_epoch)
    except Exception as error:
        if type(error) is V075LiveBatchedCausalPromotionV3InvariantViolation:
            raise
        raise V075LiveBatchedCausalPromotionV3InvariantViolation(
            "causal child predecessor exact replay failed"
        ) from error
    if (
        exact_authorization.authorization_id
        != bundle.authorization.authorization_id
        or exact_authorization_verification.verification_id
        != bundle.authorization_verification.verification_id
        or exact_ledger.ledger_id != bundle.ledger.ledger_id
        or exact_ledger_verification.verification_id
        != bundle.ledger_verification.verification_id
        or exact_barrier.barrier_id != bundle.barrier.barrier_id
        or exact_barrier_verification.verification_id
        != bundle.barrier_verification.verification_id
        or exact_epoch.model_epoch_id != bundle.resulting_epoch.model_epoch_id
        or bundle.barrier.resulting_model_epoch_id
        != bundle.resulting_epoch.model_epoch_id
    ):
        _fail("causal child predecessor identities changed")
    return bundle


def _row_source(
    epoch: live_model.V075LiveIncrementalModelEpochV2,
    row_binding_id: str,
) -> live_model.V075LiveModelRowSourceBindingV2:
    try:
        source = epoch.row_source_for_binding_v2(row_binding_id)
    except Exception as error:
        raise V075LiveBatchedCausalPromotionV3InvariantViolation(
            "promotion row lacks exact row-source evidence"
        ) from error
    if (
        type(source) is not live_model.V075LiveModelRowSourceBindingV2
        or source.row_binding_id != row_binding_id
    ):
        _fail("promotion row-source evidence is foreign")
    return source


def _validation_stream(
    *,
    epoch: live_model.V075LiveIncrementalModelEpochV2,
    source: live_model.V075LiveModelRowSourceBindingV2,
) -> graph.V075TransitionStreamIdentityV1:
    streams: dict[str, graph.V075TransitionStreamIdentityV1] = {}
    for receipt_id in source.validation_append_receipt_ids:
        try:
            append = epoch.controlled_append_by_receipt_id_v2(receipt_id)
        except Exception as error:
            raise V075LiveBatchedCausalPromotionV3InvariantViolation(
                "promotion validation append replay failed"
            ) from error
        stream = append.batch.request.stream_identity
        if (
            append.receipt.receipt_id != receipt_id
            or stream.row_binding_id != source.row_binding_id
            or stream.lane is not graph.V075ObservationLaneV1.VALIDATION
            or stream.observer_epoch_index != 1
            or append.batch.request.accepted_draw_cap
            != source.validation_draw_cap
        ):
            _fail("promotion row-source validation stream changed")
        streams[stream.stream_id] = stream
    if (
        len(streams) != 1
        or next(iter(streams)) != source.validation_stream_id
    ):
        _fail("promotion row-source uses multiple validation streams")
    return next(iter(streams.values()))


class V075LiveBatchedCausalPromotionDecisionStatusV3(str, Enum):
    AUTHORIZED = "PROMOTION_AUTHORIZED"
    CANDIDATE_EARLY_STOP = "CANDIDATE_EARLY_STOP"
    NO_ELIGIBLE_FRONTIER_ROW = "NO_ELIGIBLE_FRONTIER_ROW"


_INTENT_ISSUER = object()
_DECISION_ISSUER = object()
_DECISION_VERIFICATION_ISSUER = object()
_BARRIER_ISSUER = object()
_BARRIER_VERIFICATION_ISSUER = object()
_BUNDLE_ISSUER = object()
_BUNDLE_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalPromotionIntentV3:
    """Exact V2 semantic projection selected by the V3 causal lineage."""

    _issuer: object = field(repr=False, compare=False)
    source_model_epoch_id: str
    source_numerical_model_id: str
    source_proof_id: str
    source_frontier_id: str
    source_head_id: str
    occurrence_id: str
    context_id: str
    arm: str
    round_index: int
    previous_decision_id: str | None
    numerical_row_id: str
    row_binding_id: str
    row_source_binding_id: str
    stage: str
    support_freeze_id: str
    stream_identity: graph.V075TransitionStreamIdentityV1
    accepted_draw_start: int
    accepted_draw_count: int
    accepted_draw_cap: int
    _intent_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_model_epoch_id, "promotion source epoch"),
            (self.source_numerical_model_id, "promotion source model"),
            (self.source_proof_id, "promotion source proof"),
            (self.source_frontier_id, "promotion source frontier"),
            (self.source_head_id, "promotion source head"),
            (self.occurrence_id, "promotion occurrence"),
            (self.context_id, "promotion context"),
            (self.numerical_row_id, "promotion numerical row"),
            (self.row_binding_id, "promotion row binding"),
            (self.row_source_binding_id, "promotion row source"),
            (self.support_freeze_id, "promotion support freeze"),
        ):
            _cid(value, label)
        if self.previous_decision_id is not None:
            _cid(self.previous_decision_id, "promotion previous decision")
        if (
            self._issuer is not _INTENT_ISSUER
            or self.arm not in {item.value for item in worker.V075WorkerArmV1}
            or self.round_index not in (1, 2)
            or self.stage not in {"ROOT_VALIDATION", "CHILD_VALIDATION"}
            or type(self.stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or self.stream_identity.context_id != self.context_id
            or self.stream_identity.row_binding_id != self.row_binding_id
            or self.stream_identity.arm != self.arm
            or self.stream_identity.lane
            is not graph.V075ObservationLaneV1.VALIDATION
            or self.stream_identity.observer_epoch_index != 1
            or type(self.accepted_draw_start) is not int
            or self.accepted_draw_start <= 1
            or self.accepted_draw_count != PROMOTION_DRAWS
            or type(self.accepted_draw_cap) is not int
            or self.accepted_draw_end > self.accepted_draw_cap
            or (self.round_index == 1) != (self.previous_decision_id is None)
        ):
            _fail("causal promotion intent is malformed")
        object.__setattr__(
            self,
            "_intent_id",
            _semantic_hash(self._payload()),
        )

    @property
    def accepted_draw_end(self) -> int:
        return self.accepted_draw_start + self.accepted_draw_count - 1

    @property
    def intent_id(self) -> str:
        return self._intent_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": dynamic.LIVE_PROMOTION_SEMANTIC_SCHEMA,
            "schema_version": dynamic.SCHEMA_VERSION,
            "profile_key": dynamic.PROFILE_KEY,
            "semantic_role": dynamic.LIVE_PROMOTION_SEMANTIC_ROLE,
            "stage": self.stage,
            "round_index": self.round_index,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_numerical_model_id": self.source_numerical_model_id,
            "source_proof_id": self.source_proof_id,
            "source_frontier_id": self.source_frontier_id,
            "source_head_id": self.source_head_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "previous_promotion_decision_id": self.previous_decision_id,
            "numerical_row_id": self.numerical_row_id,
            "row_binding_id": self.row_binding_id,
            "row_source_binding_id": self.row_source_binding_id,
            "support_freeze_id": self.support_freeze_id,
            "stream_id": self.stream_identity.stream_id,
            "observer_epoch_index": 1,
            "accepted_draw_start": self.accepted_draw_start,
            "accepted_draw_count": self.accepted_draw_count,
            "accepted_draw_end": self.accepted_draw_end,
            "accepted_draw_cap": self.accepted_draw_cap,
            "selection_rule": PROMOTION_SELECTION_RULE,
            "support_epoch_immutable": True,
            "other_event_remains_other": True,
            "observer_execution_ready": True,
            "official_execution_allowed": False,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "stream_identity": self.stream_identity.to_document(),
            "intent_id": self.intent_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalPromotionDecisionV3:
    _issuer: object = field(repr=False, compare=False)
    source_epoch: live_model.V075LiveIncrementalModelEpochV2 = field(repr=False)
    child_execution_bundle_id: str
    child_authorization_id: str
    child_execution_ledger_id: str
    child_replanning_barrier_id: str
    round_index: int
    previous_decision_id: str | None
    previous_replanning_barrier_id: str | None
    status: V075LiveBatchedCausalPromotionDecisionStatusV3
    intent: V075LiveBatchedCausalPromotionIntentV3 | None
    eligible_row_ids: tuple[str, ...]
    _decision_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.child_execution_bundle_id, "promotion child bundle"),
            (self.child_authorization_id, "promotion child authorization"),
            (self.child_execution_ledger_id, "promotion child ledger"),
            (self.child_replanning_barrier_id, "promotion child barrier"),
        ):
            _cid(value, label)
        for value in (self.previous_decision_id, self.previous_replanning_barrier_id):
            if value is not None:
                _cid(value, "promotion previous lineage")
        if (
            self._issuer is not _DECISION_ISSUER
            or type(self.source_epoch)
            is not live_model.V075LiveIncrementalModelEpochV2
            or self.round_index not in (1, 2)
            or type(self.status)
            is not V075LiveBatchedCausalPromotionDecisionStatusV3
            or type(self.eligible_row_ids) is not tuple
            or self.eligible_row_ids != tuple(sorted(set(self.eligible_row_ids)))
            or (self.round_index == 1)
            != (
                self.previous_decision_id is None
                and self.previous_replanning_barrier_id is None
            )
        ):
            _fail("causal promotion decision is malformed")
        for row_id in self.eligible_row_ids:
            _cid(row_id, "promotion eligible row")
        authorized = (
            self.status
            is V075LiveBatchedCausalPromotionDecisionStatusV3.AUTHORIZED
        )
        if authorized != (
            type(self.intent) is V075LiveBatchedCausalPromotionIntentV3
            and bool(self.eligible_row_ids)
        ):
            _fail("promotion decision status differs from its intent")
        if authorized and (
            self.intent is None
            or self.intent.round_index != self.round_index
            or self.intent.source_model_epoch_id
            != self.source_epoch.model_epoch_id
            or self.intent.source_proof_id != self.source_epoch.proof.proof_id
            or self.intent.source_head_id != self.source_epoch.head_id
            or self.intent.numerical_row_id not in self.eligible_row_ids
        ):
            _fail("promotion intent differs from its source epoch")
        candidate = (
            self.source_epoch.proof.outcome
            is planning.V075NumericalOutcomeV2.CANDIDATE
        )
        if (
            self.status
            is V075LiveBatchedCausalPromotionDecisionStatusV3.CANDIDATE_EARLY_STOP
        ) != candidate:
            _fail("promotion early stop differs from its source proof")
        if not authorized and (self.intent is not None or self.eligible_row_ids):
            _fail("non-authorized promotion decision emitted work")
        object.__setattr__(self, "_decision_id", _hash("decision", self._payload()))

    def _payload(self) -> dict[str, Any]:
        epoch = self.source_epoch
        return {
            "schema": "acfqp.v075_live_batched_causal_promotion_decision.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "status": self.status.value,
            "round_index": self.round_index,
            "child_execution_bundle_id": self.child_execution_bundle_id,
            "child_authorization_id": self.child_authorization_id,
            "child_execution_ledger_id": self.child_execution_ledger_id,
            "child_replanning_barrier_id": self.child_replanning_barrier_id,
            "previous_promotion_decision_id": self.previous_decision_id,
            "previous_promotion_replanning_barrier_id": (
                self.previous_replanning_barrier_id
            ),
            "source_model_epoch_id": epoch.model_epoch_id,
            "source_numerical_model_id": epoch.model.model_id,
            "source_proof_id": epoch.proof.proof_id,
            "source_frontier_id": (
                None
                if epoch.proof.failed_frontier is None
                else epoch.proof.failed_frontier.frontier_id
            ),
            "source_head_id": epoch.head_id,
            "occurrence_id": epoch.occurrence_id,
            "context_id": epoch.context_id,
            "arm": epoch.arm.value,
            "eligible_numerical_row_ids": list(self.eligible_row_ids),
            "selected_semantic_intent_id": (
                None if self.intent is None else self.intent.intent_id
            ),
            "selection_rule": PROMOTION_SELECTION_RULE,
            "maximum_promotion_rounds": MAXIMUM_PROMOTION_ROUNDS,
            "observer_calls": 0,
            "kernel_calls": 0,
            "observer_closed": False,
            "official_execution_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def decision_id(self) -> str:
        return self._decision_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "semantic_intent": (
                None if self.intent is None else self.intent.to_document()
            ),
            "decision_id": self.decision_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalPromotionDecisionVerificationV3:
    _issuer: object = field(repr=False, compare=False)
    decision_id: str
    child_execution_bundle_id: str
    source_model_epoch_id: str
    source_proof_id: str
    round_index: int
    status: V075LiveBatchedCausalPromotionDecisionStatusV3
    semantic_intent_id: str | None
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.decision_id, "promotion verification decision"),
            (self.child_execution_bundle_id, "promotion verification child bundle"),
            (self.source_model_epoch_id, "promotion verification source epoch"),
            (self.source_proof_id, "promotion verification source proof"),
        ):
            _cid(value, label)
        if self.semantic_intent_id is not None:
            _cid(self.semantic_intent_id, "promotion verification intent")
        if (
            self._issuer is not _DECISION_VERIFICATION_ISSUER
            or self.round_index not in (1, 2)
            or type(self.status)
            is not V075LiveBatchedCausalPromotionDecisionStatusV3
            or (
                self.status
                is V075LiveBatchedCausalPromotionDecisionStatusV3.AUTHORIZED
            )
            != (self.semantic_intent_id is not None)
        ):
            _fail("causal promotion decision verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("decision_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_live_batched_causal_promotion_decision_"
                "verification.v3"
            ),
            "schema_version": SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "child_execution_bundle_id": self.child_execution_bundle_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_proof_id": self.source_proof_id,
            "round_index": self.round_index,
            "status": self.status.value,
            "semantic_intent_id": self.semantic_intent_id,
            "semantic_replay_complete": True,
            "observer_execution_performed": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _exact_decision_verification(
    decision: V075LiveBatchedCausalPromotionDecisionV3,
) -> V075LiveBatchedCausalPromotionDecisionVerificationV3:
    return V075LiveBatchedCausalPromotionDecisionVerificationV3(
        _DECISION_VERIFICATION_ISSUER,
        decision.decision_id,
        decision.child_execution_bundle_id,
        decision.source_epoch.model_epoch_id,
        decision.source_epoch.proof.proof_id,
        decision.round_index,
        decision.status,
        None if decision.intent is None else decision.intent.intent_id,
    )


def _eligible_rows(
    epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> tuple[
    tuple[
        planning.V075FrontierObligationV2,
        planning.V075NumericalRowV2,
        live_model.V075LiveModelRowSourceBindingV2,
        graph.V075TransitionStreamIdentityV1,
    ],
    ...,
]:
    proof = epoch.proof
    if (
        proof.outcome is not planning.V075NumericalOutcomeV2.FAILED_FRONTIER
        or proof.failed_frontier is None
    ):
        _fail("promotion eligibility requires one failed proof frontier")
    rows = {item.row_id: item for item in epoch.model.rows}
    eligible = []
    for obligation in proof.failed_frontier.obligations:
        row = rows.get(obligation.row_id)
        if (
            row is None
            or obligation.unmaterialized_successor_ids
            or obligation.next_registered_checkpoint is None
        ):
            continue
        source = _row_source(epoch, row.row_binding_id)
        stream = _validation_stream(epoch=epoch, source=source)
        if (
            source.numerical_row_id != row.row_id
            or source.validation_prefix_end != row.validation_draw_count
            or obligation.current_validation_draw_count
            != row.validation_draw_count
            or obligation.next_registered_checkpoint
            - obligation.current_validation_draw_count
            != PROMOTION_DRAWS
            or obligation.next_registered_checkpoint > source.validation_draw_cap
            or source.support_freeze_id not in epoch.support_freeze_ids
        ):
            _fail("failed frontier and row-source checkpoint disagree")
        eligible.append((obligation, row, source, stream))
    return tuple(
        sorted(
            eligible,
            key=lambda item: (
                -item[0].interval_width_sum,
                -item[0].other_upper,
                item[0].row_id,
            ),
        )
    )


def _validate_previous_round(
    *,
    child_bundle: child_execution.V075LiveBatchedCausalExecutionBundleV3,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    previous_decision: V075LiveBatchedCausalPromotionDecisionV3,
    previous_barrier: "V075LiveBatchedCausalPromotionBarrierV3",
    portable_replay: bool,
    child_prevalidated: bool,
) -> None:
    parent = source_epoch.parent_epoch
    if type(parent) is not live_model.V075LiveIncrementalModelEpochV2:
        _fail("round two lacks its exact round-one parent epoch")
    exact_previous = _freeze_decision(
        child_bundle=child_bundle,
        source_epoch=parent,
        round_index=1,
        previous_decision=None,
        previous_barrier=None,
        portable_replay=portable_replay,
        child_prevalidated=child_prevalidated,
    )
    exact_verification = _exact_decision_verification(exact_previous)
    exact_barrier = _freeze_barrier(
        child_bundle=child_bundle,
        decision=exact_previous,
        decision_verification=exact_verification,
        resulting_epoch=source_epoch,
        previous_barrier=None,
        portable_replay=portable_replay,
        child_prevalidated=child_prevalidated,
    )
    if (
        previous_decision.decision_id != exact_previous.decision_id
        or previous_decision.canonical_bytes != exact_previous.canonical_bytes
        or previous_barrier.barrier_id != exact_barrier.barrier_id
        or previous_barrier.canonical_bytes != exact_barrier.canonical_bytes
    ):
        _fail("round-two promotion predecessor changed")


def _freeze_decision(
    *,
    child_bundle: child_execution.V075LiveBatchedCausalExecutionBundleV3,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    round_index: int,
    previous_decision: V075LiveBatchedCausalPromotionDecisionV3 | None,
    previous_barrier: "V075LiveBatchedCausalPromotionBarrierV3 | None",
    portable_replay: bool,
    child_prevalidated: bool = False,
) -> V075LiveBatchedCausalPromotionDecisionV3:
    if type(round_index) is not int or round_index not in (1, 2):
        _fail("promotion round exceeds the registered two-round cap")
    child = (
        child_bundle
        if child_prevalidated
        else _exact_child_bundle(child_bundle, portable_replay=portable_replay)
    )
    epoch = _replay_epoch(source_epoch) if portable_replay else _operational_epoch(source_epoch)
    if round_index == 1:
        if previous_decision is not None or previous_barrier is not None:
            _fail("promotion round one rejects previous lineage")
        if (
            epoch.model_epoch_id != child.resulting_epoch.model_epoch_id
            or epoch.canonical_bytes != child.resulting_epoch.canonical_bytes
            or (not portable_replay and epoch is not child.resulting_epoch)
        ):
            _fail("promotion round one did not start at the child barrier epoch")
    else:
        if (
            type(previous_decision)
            is not V075LiveBatchedCausalPromotionDecisionV3
            or previous_decision.round_index != 1
            or previous_decision.status
            is not V075LiveBatchedCausalPromotionDecisionStatusV3.AUTHORIZED
            or type(previous_barrier)
            is not V075LiveBatchedCausalPromotionBarrierV3
        ):
            _fail("promotion round two lacks an authorized round-one barrier")
        _validate_previous_round(
            child_bundle=child,
            source_epoch=epoch,
            previous_decision=previous_decision,
            previous_barrier=previous_barrier,
            portable_replay=portable_replay,
            child_prevalidated=child_prevalidated,
        )
    proof = epoch.proof
    previous_decision_id = (
        None if previous_decision is None else previous_decision.decision_id
    )
    previous_barrier_id = (
        None if previous_barrier is None else previous_barrier.barrier_id
    )
    if proof.outcome is planning.V075NumericalOutcomeV2.CANDIDATE:
        return V075LiveBatchedCausalPromotionDecisionV3(
            _DECISION_ISSUER,
            epoch,
            child.bundle_id,
            child.authorization.authorization_id,
            child.ledger.ledger_id,
            child.barrier.barrier_id,
            round_index,
            previous_decision_id,
            previous_barrier_id,
            V075LiveBatchedCausalPromotionDecisionStatusV3.CANDIDATE_EARLY_STOP,
            None,
            (),
        )
    eligible = _eligible_rows(epoch)
    if not eligible:
        return V075LiveBatchedCausalPromotionDecisionV3(
            _DECISION_ISSUER,
            epoch,
            child.bundle_id,
            child.authorization.authorization_id,
            child.ledger.ledger_id,
            child.barrier.barrier_id,
            round_index,
            previous_decision_id,
            previous_barrier_id,
            V075LiveBatchedCausalPromotionDecisionStatusV3.NO_ELIGIBLE_FRONTIER_ROW,
            None,
            (),
        )
    obligation, row, source, stream = eligible[0]
    assert proof.failed_frontier is not None
    intent = V075LiveBatchedCausalPromotionIntentV3(
        _INTENT_ISSUER,
        epoch.model_epoch_id,
        epoch.model.model_id,
        proof.proof_id,
        proof.failed_frontier.frontier_id,
        epoch.head_id,
        epoch.occurrence_id,
        epoch.context_id,
        epoch.arm.value,
        round_index,
        previous_decision_id,
        row.row_id,
        row.row_binding_id,
        source.binding_id,
        "ROOT_VALIDATION" if row.remaining_horizon == 2 else "CHILD_VALIDATION",
        source.support_freeze_id,
        stream,
        obligation.current_validation_draw_count + 1,
        PROMOTION_DRAWS,
        source.validation_draw_cap,
    )
    return V075LiveBatchedCausalPromotionDecisionV3(
        _DECISION_ISSUER,
        epoch,
        child.bundle_id,
        child.authorization.authorization_id,
        child.ledger.ledger_id,
        child.barrier.barrier_id,
        round_index,
        previous_decision_id,
        previous_barrier_id,
        V075LiveBatchedCausalPromotionDecisionStatusV3.AUTHORIZED,
        intent,
        tuple(sorted(item[0].row_id for item in eligible)),
    )


def freeze_v075_live_batched_causal_promotion_decision_v3(
    *,
    child_execution_bundle: child_execution.V075LiveBatchedCausalExecutionBundleV3,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    round_index: int,
    previous_decision: V075LiveBatchedCausalPromotionDecisionV3 | None = None,
    previous_replanning_barrier: "V075LiveBatchedCausalPromotionBarrierV3 | None" = None,
) -> V075LiveBatchedCausalPromotionDecisionV3:
    return _freeze_decision(
        child_bundle=child_execution_bundle,
        source_epoch=source_epoch,
        round_index=round_index,
        previous_decision=previous_decision,
        previous_barrier=previous_replanning_barrier,
        portable_replay=False,
        child_prevalidated=False,
    )


def verify_v075_live_batched_causal_promotion_decision_bytes_v3(
    *,
    child_execution_bundle: child_execution.V075LiveBatchedCausalExecutionBundleV3,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    round_index: int,
    claimed_bytes: bytes,
    previous_decision: V075LiveBatchedCausalPromotionDecisionV3 | None = None,
    previous_replanning_barrier: "V075LiveBatchedCausalPromotionBarrierV3 | None" = None,
) -> tuple[
    V075LiveBatchedCausalPromotionDecisionV3,
    V075LiveBatchedCausalPromotionDecisionVerificationV3,
]:
    document = _strict_document(claimed_bytes, "causal promotion decision")
    expected = _freeze_decision(
        child_bundle=child_execution_bundle,
        source_epoch=source_epoch,
        round_index=round_index,
        previous_decision=previous_decision,
        previous_barrier=previous_replanning_barrier,
        portable_replay=True,
        child_prevalidated=False,
    )
    if set(document) != set(expected.to_document()) or claimed_bytes != (
        expected.canonical_bytes
    ):
        _fail("causal promotion decision differs from exact replay")
    return expected, _exact_decision_verification(expected)


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalPromotionBarrierV3:
    _issuer: object = field(repr=False, compare=False)
    decision_id: str
    decision_verification_id: str
    semantic_intent_id: str
    child_execution_bundle_id: str
    round_index: int
    previous_replanning_barrier_id: str | None
    source_model_epoch_id: str
    source_head_id: str
    resulting_model_epoch_id: str
    resulting_head_id: str
    resulting_open_prefix_verification_id: str
    resulting_numerical_model_id: str
    resulting_proof_id: str
    resulting_outcome: planning.V075NumericalOutcomeV2
    row_binding_id: str
    append_receipt_id: str
    append_batch_id: str
    reused_row_binding_ids: tuple[str, ...]
    _barrier_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.decision_id, "promotion barrier decision"),
            (self.decision_verification_id, "promotion barrier verification"),
            (self.semantic_intent_id, "promotion barrier intent"),
            (self.child_execution_bundle_id, "promotion barrier child bundle"),
            (self.source_model_epoch_id, "promotion barrier source epoch"),
            (self.source_head_id, "promotion barrier source head"),
            (self.resulting_model_epoch_id, "promotion barrier resulting epoch"),
            (self.resulting_head_id, "promotion barrier resulting head"),
            (
                self.resulting_open_prefix_verification_id,
                "promotion barrier resulting prefix",
            ),
            (self.resulting_numerical_model_id, "promotion barrier model"),
            (self.resulting_proof_id, "promotion barrier proof"),
            (self.row_binding_id, "promotion barrier changed row"),
            (self.append_receipt_id, "promotion barrier append receipt"),
            (self.append_batch_id, "promotion barrier append batch"),
        ):
            _cid(value, label)
        for value in self.reused_row_binding_ids:
            _cid(value, "promotion barrier reused row")
        if self.previous_replanning_barrier_id is not None:
            _cid(self.previous_replanning_barrier_id, "promotion previous barrier")
        if (
            self._issuer is not _BARRIER_ISSUER
            or self.round_index not in (1, 2)
            or (self.round_index == 1)
            != (self.previous_replanning_barrier_id is None)
            or self.source_model_epoch_id == self.resulting_model_epoch_id
            or self.source_head_id == self.resulting_head_id
            or type(self.resulting_outcome) is not planning.V075NumericalOutcomeV2
            or type(self.reused_row_binding_ids) is not tuple
            or self.reused_row_binding_ids
            != tuple(sorted(set(self.reused_row_binding_ids)))
            or self.row_binding_id in self.reused_row_binding_ids
        ):
            _fail("causal promotion replanning barrier is malformed")
        object.__setattr__(self, "_barrier_id", _hash("barrier", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_batched_causal_promotion_barrier.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "decision_id": self.decision_id,
            "decision_verification_id": self.decision_verification_id,
            "semantic_intent_id": self.semantic_intent_id,
            "child_execution_bundle_id": self.child_execution_bundle_id,
            "round_index": self.round_index,
            "previous_replanning_barrier_id": self.previous_replanning_barrier_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_head_id": self.source_head_id,
            "resulting_model_epoch_id": self.resulting_model_epoch_id,
            "resulting_head_id": self.resulting_head_id,
            "resulting_open_prefix_verification_id": (
                self.resulting_open_prefix_verification_id
            ),
            "resulting_numerical_model_id": self.resulting_numerical_model_id,
            "resulting_proof_id": self.resulting_proof_id,
            "resulting_outcome": self.resulting_outcome.value,
            "changed_row_binding_ids": [self.row_binding_id],
            "reused_row_binding_ids": list(self.reused_row_binding_ids),
            "append_receipt_id": self.append_receipt_id,
            "append_batch_id": self.append_batch_id,
            "exactly_one_promotion_append": True,
            "semantic_v2_projection_exactly_bound": True,
            "parent_epoch_and_signed_prefix_exactly_bound": True,
            "proof_consumption_allowed": True,
            "observer_closed": False,
            "official_execution_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def barrier_id(self) -> str:
        return self._barrier_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "barrier_id": self.barrier_id}


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalPromotionBarrierVerificationV3:
    _issuer: object = field(repr=False, compare=False)
    barrier_id: str
    decision_id: str
    semantic_intent_id: str
    source_model_epoch_id: str
    resulting_model_epoch_id: str
    resulting_proof_id: str
    round_index: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.barrier_id, "promotion barrier verification barrier"),
            (self.decision_id, "promotion barrier verification decision"),
            (self.semantic_intent_id, "promotion barrier verification intent"),
            (self.source_model_epoch_id, "promotion barrier verification source"),
            (self.resulting_model_epoch_id, "promotion barrier verification result"),
            (self.resulting_proof_id, "promotion barrier verification proof"),
        ):
            _cid(value, label)
        if self._issuer is not _BARRIER_VERIFICATION_ISSUER or self.round_index not in (1, 2):
            _fail("causal promotion barrier verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("barrier_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_live_batched_causal_promotion_barrier_"
                "verification.v3"
            ),
            "schema_version": SCHEMA_VERSION,
            "barrier_id": self.barrier_id,
            "decision_id": self.decision_id,
            "semantic_intent_id": self.semantic_intent_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "resulting_model_epoch_id": self.resulting_model_epoch_id,
            "resulting_proof_id": self.resulting_proof_id,
            "round_index": self.round_index,
            "semantic_replay_complete": True,
            "proof_consumption_allowed": True,
            "observer_closed": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _exact_barrier_verification(
    barrier: V075LiveBatchedCausalPromotionBarrierV3,
) -> V075LiveBatchedCausalPromotionBarrierVerificationV3:
    return V075LiveBatchedCausalPromotionBarrierVerificationV3(
        _BARRIER_VERIFICATION_ISSUER,
        barrier.barrier_id,
        barrier.decision_id,
        barrier.semantic_intent_id,
        barrier.source_model_epoch_id,
        barrier.resulting_model_epoch_id,
        barrier.resulting_proof_id,
        barrier.round_index,
    )


def _freeze_barrier(
    *,
    child_bundle: child_execution.V075LiveBatchedCausalExecutionBundleV3,
    decision: V075LiveBatchedCausalPromotionDecisionV3,
    decision_verification: V075LiveBatchedCausalPromotionDecisionVerificationV3,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
    previous_barrier: V075LiveBatchedCausalPromotionBarrierV3 | None,
    portable_replay: bool,
    child_prevalidated: bool = False,
) -> V075LiveBatchedCausalPromotionBarrierV3:
    if (
        type(decision) is not V075LiveBatchedCausalPromotionDecisionV3
        or decision.status
        is not V075LiveBatchedCausalPromotionDecisionStatusV3.AUTHORIZED
        or decision.intent is None
    ):
        _fail("promotion barrier requires one authorized decision")
    previous_decision = None
    if decision.round_index == 2:
        parent = decision.source_epoch.parent_epoch
        if type(parent) is not live_model.V075LiveIncrementalModelEpochV2:
            _fail("round-two promotion source has no round-one parent")
        previous_decision = _freeze_decision(
            child_bundle=child_bundle,
            source_epoch=parent,
            round_index=1,
            previous_decision=None,
            previous_barrier=None,
            portable_replay=portable_replay,
            child_prevalidated=child_prevalidated,
        )
    exact_decision = _freeze_decision(
        child_bundle=child_bundle,
        source_epoch=decision.source_epoch,
        round_index=decision.round_index,
        previous_decision=previous_decision,
        previous_barrier=previous_barrier,
        portable_replay=portable_replay,
        child_prevalidated=child_prevalidated,
    )
    exact_verification = _exact_decision_verification(exact_decision)
    if (
        exact_decision.decision_id != decision.decision_id
        or exact_decision.canonical_bytes != decision.canonical_bytes
        or decision_verification.verification_id
        != exact_verification.verification_id
        or decision_verification.to_document()
        != exact_verification.to_document()
    ):
        _fail("promotion decision lineage differs from exact replay")
    result = _replay_epoch(resulting_epoch) if portable_replay else _operational_epoch(resulting_epoch)
    source = exact_decision.source_epoch
    parent = result.parent_epoch
    if portable_replay and type(parent) is live_model.V075LiveIncrementalModelEpochV2:
        parent = _replay_epoch(parent)
    intent = exact_decision.intent
    assert intent is not None
    if (
        type(parent) is not live_model.V075LiveIncrementalModelEpochV2
        or parent.model_epoch_id != source.model_epoch_id
        or parent.canonical_bytes != source.canonical_bytes
        or (not portable_replay and parent is not source)
        or result.epoch_index != source.epoch_index + 1
        or result.occurrence_identity != source.occurrence_identity
        or result.route is not source.route
        or result.support_freeze_ids != source.support_freeze_ids
    ):
        _fail("promotion result is not the exact source successor")
    new_receipts = result.append_receipt_ids[len(source.append_receipt_ids) :]
    if (
        result.append_receipt_ids[: len(source.append_receipt_ids)]
        != source.append_receipt_ids
        or len(new_receipts) != 1
    ):
        _fail("promotion result contains partial or extra append work")
    append = result.controlled_append_by_receipt_id_v2(new_receipts[0])
    semantic = append.intent.semantic_authority
    request = append.batch.request
    expected_stage = (
        control.V075ControlledBatchStageV2.ROOT_VALIDATION
        if intent.stage == "ROOT_VALIDATION"
        else control.V075ControlledBatchStageV2.CHILD_VALIDATION
    )
    if (
        semantic.role
        is not control.V075ControlledBatchSemanticAuthorityRoleV2.LIVE_PROMOTION_AUTHORIZATION
        or semantic.schema
        is not control.V075ControlledBatchSemanticAuthoritySchemaV2.LIVE_PROMOTION_AUTHORIZATION
        or semantic.semantic_artifact_id != intent.intent_id
        or semantic.semantic_verification_id
        != exact_verification.verification_id
        or semantic.stage is not expected_stage
        or semantic.round_index != exact_decision.round_index
        or semantic.support_freeze_id != intent.support_freeze_id
        or request.stream_identity != intent.stream_identity
        or request.accepted_draw_start != intent.accepted_draw_start
        or request.accepted_draw_count != intent.accepted_draw_count
        or request.accepted_draw_cap != intent.accepted_draw_cap
    ):
        _fail("promotion append differs from its exact semantic authorization")
    parent_source = _row_source(source, intent.row_binding_id)
    current_source = _row_source(result, intent.row_binding_id)
    parent_stream = _validation_stream(epoch=source, source=parent_source)
    current_stream = _validation_stream(epoch=result, source=current_source)
    new_row_receipts = tuple(
        item
        for item in current_source.validation_append_receipt_ids
        if item not in set(parent_source.validation_append_receipt_ids)
    )
    source_rows = tuple(sorted(item.row_binding_id for item in source.row_sources))
    result_rows = tuple(sorted(item.row_binding_id for item in result.row_sources))
    reused = tuple(item for item in source_rows if item != intent.row_binding_id)
    if (
        current_source.support_freeze_id != parent_source.support_freeze_id
        or current_source.support_freeze_id != intent.support_freeze_id
        or current_source.validation_stream_id != parent_source.validation_stream_id
        or current_stream != parent_stream
        or current_stream != intent.stream_identity
        or current_source.validation_draw_cap != parent_source.validation_draw_cap
        or current_source.validation_prefix_end != intent.accepted_draw_end
        or parent_source.validation_prefix_end != intent.accepted_draw_start - 1
        or new_row_receipts != (append.receipt.receipt_id,)
        or result.changed_row_binding_ids != (intent.row_binding_id,)
        or result.reused_row_binding_ids != reused
        or result_rows != source_rows
    ):
        _fail("promotion row source or changed/reused model rows changed")
    return V075LiveBatchedCausalPromotionBarrierV3(
        _BARRIER_ISSUER,
        exact_decision.decision_id,
        exact_verification.verification_id,
        intent.intent_id,
        child_bundle.bundle_id,
        exact_decision.round_index,
        None if previous_barrier is None else previous_barrier.barrier_id,
        source.model_epoch_id,
        source.head_id,
        result.model_epoch_id,
        result.head_id,
        result.open_prefix_verification.verification_id,
        result.model.model_id,
        result.proof.proof_id,
        result.proof.outcome,
        intent.row_binding_id,
        append.receipt.receipt_id,
        append.batch.batch_id,
        reused,
    )


def freeze_v075_live_batched_causal_promotion_barrier_v3(
    *,
    child_execution_bundle: child_execution.V075LiveBatchedCausalExecutionBundleV3,
    decision: V075LiveBatchedCausalPromotionDecisionV3,
    decision_verification: V075LiveBatchedCausalPromotionDecisionVerificationV3,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
    previous_replanning_barrier: V075LiveBatchedCausalPromotionBarrierV3 | None = None,
) -> V075LiveBatchedCausalPromotionBarrierV3:
    return _freeze_barrier(
        child_bundle=child_execution_bundle,
        decision=decision,
        decision_verification=decision_verification,
        resulting_epoch=resulting_epoch,
        previous_barrier=previous_replanning_barrier,
        portable_replay=False,
        child_prevalidated=False,
    )


def verify_v075_live_batched_causal_promotion_barrier_bytes_v3(
    *,
    child_execution_bundle: child_execution.V075LiveBatchedCausalExecutionBundleV3,
    decision: V075LiveBatchedCausalPromotionDecisionV3,
    decision_verification: V075LiveBatchedCausalPromotionDecisionVerificationV3,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
    claimed_bytes: bytes,
    previous_replanning_barrier: V075LiveBatchedCausalPromotionBarrierV3 | None = None,
) -> tuple[
    V075LiveBatchedCausalPromotionBarrierV3,
    V075LiveBatchedCausalPromotionBarrierVerificationV3,
]:
    document = _strict_document(claimed_bytes, "causal promotion barrier")
    expected = _freeze_barrier(
        child_bundle=child_execution_bundle,
        decision=decision,
        decision_verification=decision_verification,
        resulting_epoch=resulting_epoch,
        previous_barrier=previous_replanning_barrier,
        portable_replay=True,
        child_prevalidated=False,
    )
    if set(document) != set(expected.to_document()) or claimed_bytes != (
        expected.canonical_bytes
    ):
        _fail("causal promotion barrier differs from exact replay")
    return expected, _exact_barrier_verification(expected)


class V075LiveBatchedCausalPromotionOutcomeV3(str, Enum):
    CANDIDATE_READY_FOR_INDEPENDENT_TOTAL_LIFT = (
        "CANDIDATE_READY_FOR_INDEPENDENT_TOTAL_LIFT"
    )
    PROMOTION_BUDGET_EXHAUSTED = "PROMOTION_BUDGET_EXHAUSTED"
    NO_ELIGIBLE_FRONTIER_ROW = "NO_ELIGIBLE_FRONTIER_ROW"


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalPromotionBundleV3:
    _issuer: object = field(repr=False, compare=False)
    child_execution_bundle: child_execution.V075LiveBatchedCausalExecutionBundleV3
    decisions: tuple[V075LiveBatchedCausalPromotionDecisionV3, ...]
    decision_verifications: tuple[
        V075LiveBatchedCausalPromotionDecisionVerificationV3, ...
    ]
    resulting_epochs: tuple[live_model.V075LiveIncrementalModelEpochV2, ...] = field(
        repr=False
    )
    barriers: tuple[V075LiveBatchedCausalPromotionBarrierV3, ...]
    barrier_verifications: tuple[
        V075LiveBatchedCausalPromotionBarrierVerificationV3, ...
    ]
    final_epoch: live_model.V075LiveIncrementalModelEpochV2 = field(repr=False)
    outcome: V075LiveBatchedCausalPromotionOutcomeV3
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _BUNDLE_ISSUER
            or type(self.child_execution_bundle)
            is not child_execution.V075LiveBatchedCausalExecutionBundleV3
            or type(self.decisions) is not tuple
            or not self.decisions
            or len(self.decisions) > MAXIMUM_PROMOTION_ROUNDS
            or type(self.decision_verifications) is not tuple
            or len(self.decision_verifications) != len(self.decisions)
            or type(self.resulting_epochs) is not tuple
            or type(self.barriers) is not tuple
            or type(self.barrier_verifications) is not tuple
            or len(self.resulting_epochs) != len(self.barriers)
            or len(self.barriers) != len(self.barrier_verifications)
            or len(self.barriers) not in {len(self.decisions), len(self.decisions) - 1}
            or type(self.final_epoch)
            is not live_model.V075LiveIncrementalModelEpochV2
            or type(self.outcome) is not V075LiveBatchedCausalPromotionOutcomeV3
        ):
            _fail("causal promotion bundle is malformed")
        for index, decision in enumerate(self.decisions):
            if (
                decision.round_index != index + 1
                or self.decision_verifications[index].decision_id
                != decision.decision_id
            ):
                _fail("promotion bundle decision sequence changed")
        for index, barrier in enumerate(self.barriers):
            if (
                barrier.decision_id != self.decisions[index].decision_id
                or barrier.resulting_model_epoch_id
                != self.resulting_epochs[index].model_epoch_id
                or self.barrier_verifications[index].barrier_id
                != barrier.barrier_id
            ):
                _fail("promotion bundle barrier sequence changed")
        expected_final = (
            self.child_execution_bundle.resulting_epoch
            if not self.resulting_epochs
            else self.resulting_epochs[-1]
        )
        if self.final_epoch is not expected_final:
            _fail("promotion bundle final epoch is not its final exact successor")
        candidate = (
            self.final_epoch.proof.outcome
            is planning.V075NumericalOutcomeV2.CANDIDATE
        )
        if (
            self.outcome
            is V075LiveBatchedCausalPromotionOutcomeV3.CANDIDATE_READY_FOR_INDEPENDENT_TOTAL_LIFT
        ) != candidate:
            _fail("promotion bundle candidate outcome differs from final proof")
        if (
            self.outcome
            is V075LiveBatchedCausalPromotionOutcomeV3.PROMOTION_BUDGET_EXHAUSTED
            and len(self.barriers) != MAXIMUM_PROMOTION_ROUNDS
        ):
            _fail("promotion budget exhaustion occurred before the round cap")
        object.__setattr__(self, "_bundle_id", _hash("bundle", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_batched_causal_promotion_bundle.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "child_execution_bundle_id": self.child_execution_bundle.bundle_id,
            "decision_ids": [item.decision_id for item in self.decisions],
            "decision_verification_ids": [
                item.verification_id for item in self.decision_verifications
            ],
            "resulting_model_epoch_ids": [
                item.model_epoch_id for item in self.resulting_epochs
            ],
            "replanning_barrier_ids": [item.barrier_id for item in self.barriers],
            "replanning_barrier_verification_ids": [
                item.verification_id for item in self.barrier_verifications
            ],
            "final_model_epoch_id": self.final_epoch.model_epoch_id,
            "final_numerical_model_id": self.final_epoch.model.model_id,
            "final_proof_id": self.final_epoch.proof.proof_id,
            "final_numerical_outcome": self.final_epoch.proof.outcome.value,
            "outcome": self.outcome.value,
            "promotion_rounds_executed": len(self.barriers),
            "maximum_promotion_rounds": MAXIMUM_PROMOTION_ROUNDS,
            "observer_closed": False,
            "semantic_terminal_issued": False,
            "counter_records_issued": 0,
            "production_integration_ready": PRODUCTION_INTEGRATION_READY,
            "official_execution_allowed": False,
        }

    @property
    def bundle_id(self) -> str:
        return self._bundle_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "decisions": [item.to_document() for item in self.decisions],
            "decision_verifications": [
                item.to_document() for item in self.decision_verifications
            ],
            "resulting_epochs": [item.to_document() for item in self.resulting_epochs],
            "replanning_barriers": [item.to_document() for item in self.barriers],
            "replanning_barrier_verifications": [
                item.to_document() for item in self.barrier_verifications
            ],
            "bundle_id": self.bundle_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalPromotionBundleVerificationV3:
    _issuer: object = field(repr=False, compare=False)
    bundle_id: str
    child_execution_bundle_id: str
    final_model_epoch_id: str
    final_proof_id: str
    outcome: V075LiveBatchedCausalPromotionOutcomeV3
    executed_round_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.bundle_id, "promotion bundle verification bundle"),
            (
                self.child_execution_bundle_id,
                "promotion bundle verification child bundle",
            ),
            (self.final_model_epoch_id, "promotion bundle verification epoch"),
            (self.final_proof_id, "promotion bundle verification proof"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _BUNDLE_VERIFICATION_ISSUER
            or type(self.outcome) is not V075LiveBatchedCausalPromotionOutcomeV3
            or type(self.executed_round_count) is not int
            or self.executed_round_count not in range(0, MAXIMUM_PROMOTION_ROUNDS + 1)
        ):
            _fail("causal promotion bundle verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("bundle_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_live_batched_causal_promotion_bundle_"
                "verification.v3"
            ),
            "schema_version": SCHEMA_VERSION,
            "bundle_id": self.bundle_id,
            "child_execution_bundle_id": self.child_execution_bundle_id,
            "final_model_epoch_id": self.final_model_epoch_id,
            "final_proof_id": self.final_proof_id,
            "outcome": self.outcome.value,
            "executed_round_count": self.executed_round_count,
            "all_decisions_exactly_replayed": True,
            "all_signed_appends_exactly_replayed": True,
            "all_model_and_proof_barriers_exactly_replayed": True,
            "observer_closed": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _exact_bundle_verification(
    bundle: V075LiveBatchedCausalPromotionBundleV3,
) -> V075LiveBatchedCausalPromotionBundleVerificationV3:
    return V075LiveBatchedCausalPromotionBundleVerificationV3(
        _BUNDLE_VERIFICATION_ISSUER,
        bundle.bundle_id,
        bundle.child_execution_bundle.bundle_id,
        bundle.final_epoch.model_epoch_id,
        bundle.final_epoch.proof.proof_id,
        bundle.outcome,
        len(bundle.barriers),
    )


def _replay_promotion_bundle(
    claimed: V075LiveBatchedCausalPromotionBundleV3,
    *,
    portable_replay: bool,
) -> V075LiveBatchedCausalPromotionBundleV3:
    if type(claimed) is not V075LiveBatchedCausalPromotionBundleV3:
        _fail("promotion bundle replay requires one typed bundle")
    child = _exact_child_bundle(
        claimed.child_execution_bundle,
        portable_replay=portable_replay,
    )
    source = child.resulting_epoch
    previous_decision = None
    previous_barrier = None
    exact_decisions = []
    exact_decision_verifications = []
    exact_epochs = []
    exact_barriers = []
    exact_barrier_verifications = []
    barrier_index = 0
    for index, supplied_decision in enumerate(claimed.decisions, start=1):
        exact_decision = _freeze_decision(
            child_bundle=child,
            source_epoch=source,
            round_index=index,
            previous_decision=previous_decision,
            previous_barrier=previous_barrier,
            portable_replay=portable_replay,
            child_prevalidated=True,
        )
        exact_decision_verification = _exact_decision_verification(
            exact_decision
        )
        if (
            supplied_decision.decision_id != exact_decision.decision_id
            or supplied_decision.canonical_bytes
            != exact_decision.canonical_bytes
            or claimed.decision_verifications[index - 1].to_document()
            != exact_decision_verification.to_document()
        ):
            _fail("promotion bundle decision sequence differs from replay")
        exact_decisions.append(exact_decision)
        exact_decision_verifications.append(exact_decision_verification)
        if (
            exact_decision.status
            is not V075LiveBatchedCausalPromotionDecisionStatusV3.AUTHORIZED
        ):
            if index != len(claimed.decisions):
                _fail("promotion bundle continued after an exact stop decision")
            break
        if barrier_index >= len(claimed.resulting_epochs):
            _fail("promotion bundle omitted an authorized resulting epoch")
        supplied_epoch = claimed.resulting_epochs[barrier_index]
        exact_barrier = _freeze_barrier(
            child_bundle=child,
            decision=exact_decision,
            decision_verification=exact_decision_verification,
            resulting_epoch=supplied_epoch,
            previous_barrier=previous_barrier,
            portable_replay=portable_replay,
            child_prevalidated=True,
        )
        exact_barrier_verification = _exact_barrier_verification(exact_barrier)
        if (
            claimed.barriers[barrier_index].barrier_id
            != exact_barrier.barrier_id
            or claimed.barriers[barrier_index].canonical_bytes
            != exact_barrier.canonical_bytes
            or claimed.barrier_verifications[barrier_index].to_document()
            != exact_barrier_verification.to_document()
        ):
            _fail("promotion bundle replanning barrier differs from replay")
        exact_epoch = (
            _replay_epoch(supplied_epoch)
            if portable_replay
            else _operational_epoch(supplied_epoch)
        )
        exact_epochs.append(exact_epoch)
        exact_barriers.append(exact_barrier)
        exact_barrier_verifications.append(exact_barrier_verification)
        source = exact_epoch
        previous_decision = exact_decision
        previous_barrier = exact_barrier
        barrier_index += 1
    if (
        barrier_index != len(claimed.resulting_epochs)
        or barrier_index != len(claimed.barriers)
        or barrier_index != len(claimed.barrier_verifications)
    ):
        _fail("promotion bundle contains extra resulting epochs or barriers")
    if source.proof.outcome is planning.V075NumericalOutcomeV2.CANDIDATE:
        outcome = (
            V075LiveBatchedCausalPromotionOutcomeV3
            .CANDIDATE_READY_FOR_INDEPENDENT_TOTAL_LIFT
        )
    elif (
        exact_decisions[-1].status
        is V075LiveBatchedCausalPromotionDecisionStatusV3.NO_ELIGIBLE_FRONTIER_ROW
    ):
        outcome = V075LiveBatchedCausalPromotionOutcomeV3.NO_ELIGIBLE_FRONTIER_ROW
    elif barrier_index == MAXIMUM_PROMOTION_ROUNDS:
        outcome = V075LiveBatchedCausalPromotionOutcomeV3.PROMOTION_BUDGET_EXHAUSTED
    else:
        _fail("promotion bundle stopped without candidate, frontier stop, or cap")
    expected = V075LiveBatchedCausalPromotionBundleV3(
        _BUNDLE_ISSUER,
        child,
        tuple(exact_decisions),
        tuple(exact_decision_verifications),
        tuple(exact_epochs),
        tuple(exact_barriers),
        tuple(exact_barrier_verifications),
        source,
        outcome,
    )
    if (
        expected.bundle_id != claimed.bundle_id
        or expected.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("promotion bundle differs from exact replay")
    return expected


def validate_v075_trusted_owned_batched_causal_promotion_bundle_v3(
    claimed: V075LiveBatchedCausalPromotionBundleV3,
) -> tuple[
    V075LiveBatchedCausalPromotionBundleV3,
    V075LiveBatchedCausalPromotionBundleVerificationV3,
]:
    """Exact same-process replay without repeating portable planner replay."""

    expected = _replay_promotion_bundle(claimed, portable_replay=False)
    return expected, _exact_bundle_verification(expected)


def verify_v075_live_batched_causal_promotion_bundle_bytes_v3(
    *,
    claimed: V075LiveBatchedCausalPromotionBundleV3,
    claimed_bytes: bytes,
) -> tuple[
    V075LiveBatchedCausalPromotionBundleV3,
    V075LiveBatchedCausalPromotionBundleVerificationV3,
]:
    document = _strict_document(claimed_bytes, "causal promotion bundle")
    expected = _replay_promotion_bundle(claimed, portable_replay=True)
    if set(document) != set(expected.to_document()) or claimed_bytes != (
        expected.canonical_bytes
    ):
        _fail("causal promotion bundle bytes differ from exact replay")
    return expected, _exact_bundle_verification(expected)


def execute_v075_live_batched_causal_promotions_v3(
    *,
    controller: control.V075ConstructionControlledPrivateObserverV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    child_execution_bundle: child_execution.V075LiveBatchedCausalExecutionBundleV3,
) -> V075LiveBatchedCausalPromotionBundleV3:
    """Execute at most two exact validation promotions and leave owner open."""

    child = _exact_child_bundle(child_execution_bundle, portable_replay=False)
    if (
        type(controller)
        is not control.V075ConstructionControlledPrivateObserverV2
        or type(schedule) is not acquisition.V075InitialAcquisitionScheduleV2
        or schedule.occurrence != child.resulting_epoch.occurrence_identity
    ):
        _fail("promotion controller or schedule was transplanted")
    source_epoch = child.resulting_epoch
    decisions = []
    decision_verifications = []
    resulting_epochs = []
    barriers = []
    barrier_verifications = []
    previous_decision = None
    previous_barrier = None
    stopped_without_append = False
    for round_index in range(1, MAXIMUM_PROMOTION_ROUNDS + 1):
        prefix = controller.freeze_owned_open_prefix_v2()
        if (
            prefix.verification_id
            != source_epoch.open_prefix_verification.verification_id
            or prefix.to_document()
            != source_epoch.open_prefix_verification.to_document()
        ):
            _fail("promotion did not start at its source signed head")
        decision = _freeze_decision(
            child_bundle=child,
            source_epoch=source_epoch,
            round_index=round_index,
            previous_decision=previous_decision,
            previous_barrier=previous_barrier,
            portable_replay=False,
            child_prevalidated=True,
        )
        verification = _exact_decision_verification(decision)
        decisions.append(decision)
        decision_verifications.append(verification)
        if decision.status is not V075LiveBatchedCausalPromotionDecisionStatusV3.AUTHORIZED:
            stopped_without_append = True
            break
        intent = decision.intent
        assert intent is not None
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
            semantic_verification_id=verification.verification_id,
            stage=stage,
            round_index=round_index,
            support_freeze_id=intent.support_freeze_id,
            accepted_draw_start=intent.accepted_draw_start,
            accepted_draw_count=intent.accepted_draw_count,
            accepted_draw_cap=intent.accepted_draw_cap,
        )
        controller.execute_batch_intent_v2(controlled_intent)
        resulting_prefix = controller.freeze_owned_open_prefix_v2()
        result = live_model.freeze_v075_live_incremental_model_epoch_v2(
            occurrence_identity=schedule.occurrence,
            controlled_appends=controller.controlled_appends,
            support_freezes=controller.support_freezes,
            open_prefix_verification=resulting_prefix,
            route=source_epoch.route,
            parent_epoch=source_epoch,
        )
        barrier = _freeze_barrier(
            child_bundle=child,
            decision=decision,
            decision_verification=verification,
            resulting_epoch=result,
            previous_barrier=previous_barrier,
            portable_replay=False,
            child_prevalidated=True,
        )
        barrier_verification = _exact_barrier_verification(barrier)
        resulting_epochs.append(result)
        barriers.append(barrier)
        barrier_verifications.append(barrier_verification)
        source_epoch = result
        previous_decision = decision
        previous_barrier = barrier
        if result.proof.outcome is planning.V075NumericalOutcomeV2.CANDIDATE:
            break
    if source_epoch.proof.outcome is planning.V075NumericalOutcomeV2.CANDIDATE:
        outcome = (
            V075LiveBatchedCausalPromotionOutcomeV3
            .CANDIDATE_READY_FOR_INDEPENDENT_TOTAL_LIFT
        )
    elif stopped_without_append:
        outcome = V075LiveBatchedCausalPromotionOutcomeV3.NO_ELIGIBLE_FRONTIER_ROW
    else:
        outcome = V075LiveBatchedCausalPromotionOutcomeV3.PROMOTION_BUDGET_EXHAUSTED
    return V075LiveBatchedCausalPromotionBundleV3(
        _BUNDLE_ISSUER,
        child,
        tuple(decisions),
        tuple(decision_verifications),
        tuple(resulting_epochs),
        tuple(barriers),
        tuple(barrier_verifications),
        source_epoch,
        outcome,
    )


__all__ = (
    "COUNTER_RECORD_ISSUANCE_ALLOWED",
    "MAXIMUM_PROMOTION_ROUNDS",
    "OBSERVER_CLOSE_PERFORMED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PRODUCTION_INTEGRATION_READY",
    "PROMOTION_DRAWS",
    "PROMOTION_SELECTION_RULE",
    "V075LiveBatchedCausalPromotionBarrierV3",
    "V075LiveBatchedCausalPromotionBarrierVerificationV3",
    "V075LiveBatchedCausalPromotionBundleV3",
    "V075LiveBatchedCausalPromotionBundleVerificationV3",
    "V075LiveBatchedCausalPromotionDecisionStatusV3",
    "V075LiveBatchedCausalPromotionDecisionV3",
    "V075LiveBatchedCausalPromotionDecisionVerificationV3",
    "V075LiveBatchedCausalPromotionIntentV3",
    "V075LiveBatchedCausalPromotionOutcomeV3",
    "V075LiveBatchedCausalPromotionV3InvariantViolation",
    "execute_v075_live_batched_causal_promotions_v3",
    "freeze_v075_live_batched_causal_promotion_barrier_v3",
    "freeze_v075_live_batched_causal_promotion_decision_v3",
    "validate_v075_trusted_owned_batched_causal_promotion_bundle_v3",
    "verify_v075_live_batched_causal_promotion_barrier_bytes_v3",
    "verify_v075_live_batched_causal_promotion_decision_bytes_v3",
    "verify_v075_live_batched_causal_promotion_bundle_bytes_v3",
)
