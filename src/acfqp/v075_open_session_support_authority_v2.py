"""Causal complete-support freezing for one open exact V0-075 V2 session.

The historical V2 occurrence adapter can append signed aggregate batches, but
it does not itself prove that validation support was frozen from *all*
discovery outcomes before the validation stream was first used.  This module
adds that missing construction authority:

* one boundary-issued controller owns one unused construction adapter;
* the controller executes and receipts every batch in the open session;
* complete aggregate support is selected deterministically, never by a caller;
* validation is derived from that exact freeze and remains one contiguous
  fixed-cap stream; and
* final reconciliation detects unreceipted direct adapter use under the
  trusted in-process construction control flow.

This remains a construction-only, noncertifying authority.  Python reference
ownership cannot prevent a caller that retained the underlying adapter from
calling it directly or invoking an underscored method.  Receipts are therefore
trusted construction control-flow evidence, not cryptographic execution
causality.  Production requires observer-signed journal heads and intent-bound
append receipts.
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
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_private_observer_boundary_v2 as observer_v2
from acfqp import v075_public_graph_semantics_v1 as graph


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.53.0"
PROFILE_KEY = "v075_open_session_support_authority_v2"
MAX_CANONICAL_INPUT_BYTES = 64 * 1024 * 1024

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
PER_DRAW_REPLAY_ALLOWED = False
PRIVATE_LAW_ACCESS_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_INTERMEDIATE_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
PRODUCTION_BLOCKER = (
    "the V2 complete-support controller is construction-only; production "
    "requires observer-signed heads, intent-bound append receipts, a "
    "byte-gated controller issuer, and an independent final bundle verifier"
)

DOMAIN_TAGS = {
    "controller": "acfqp:v075-open-session-support-controller:v2",
    "execution_receipt": (
        "acfqp:v075-open-session-support-execution-receipt:v2"
    ),
    "support_freeze": "acfqp:v075-open-session-complete-support-freeze:v2",
    "reconciliation": (
        "acfqp:v075-open-session-support-reconciliation:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 open-session support domains must be unique")


class V075OpenSessionSupportV2InvariantViolation(ValueError):
    """The session, support freeze, stream, receipt, or closure was invalid."""


class V075OpenSessionSupportProductionV2NotReady(RuntimeError):
    """Production use is locked until the byte-gated issuer is integrated."""


def _fail(message: str) -> NoReturn:
    raise V075OpenSessionSupportV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075OpenSessionSupportV2InvariantViolation(str(error)) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075OpenSessionSupportV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _strict_document(raw: bytes, label: str) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_CANONICAL_INPUT_BYTES
    ):
        _fail(f"{label} bytes are absent or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075OpenSessionSupportV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


def _replay_identity(
    value: backend.V075BatchNativeOccurrenceIdentityV1,
) -> backend.V075BatchNativeOccurrenceIdentityV1:
    try:
        return backend.replay_v075_batch_native_occurrence_identity_v1(value)
    except Exception as error:
        raise V075OpenSessionSupportV2InvariantViolation(
            "occurrence identity replay failed"
        ) from error


def _controller_content_id(
    *,
    occurrence_id: str,
    target_tape_namespace_id: str,
    context_id: str,
    arm: str,
    observer_session_public_id: str,
    observer_open_binding_id: str,
) -> str:
    for value, label in (
        (occurrence_id, "support controller occurrence"),
        (target_tape_namespace_id, "support controller namespace"),
        (context_id, "support controller context"),
        (observer_session_public_id, "support controller session"),
        (observer_open_binding_id, "support controller binding"),
    ):
        _cid(value, label)
    if type(arm) is not str or not arm:
        _fail("support controller arm is absent")
    return _hash(
        "controller",
        {
            "schema": "acfqp.v075_open_session_support_controller.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": (
                batched_v2.V075BatchOccurrenceAuthorityScopeV2
                .CONSTRUCTION_ONLY.value
            ),
            "occurrence_id": occurrence_id,
            "target_tape_namespace_id": target_tape_namespace_id,
            "context_id": context_id,
            "arm": arm,
            "observer_session_public_id": observer_session_public_id,
            "observer_open_binding_id": observer_open_binding_id,
            "construction_only": True,
            "receipt_complete_final_reconciliation_required": True,
            "official_execution_allowed": False,
        },
    )


def _replay_batch(
    value: observer_v2.V075SignedObservationBatchV2,
) -> observer_v2.V075SignedObservationBatchV2:
    try:
        replayed = observer_v2.replay_signed_observation_batch_object_v2(value)
        batched_v2.verify_v075_signed_observation_batch_v2(replayed)
    except Exception as error:
        raise V075OpenSessionSupportV2InvariantViolation(
            "signed V2 aggregate batch replay failed"
        ) from error
    return replayed


def _replay_support_evidence(
    value: graph.V075BatchAggregateSupportEvidenceV1,
    *,
    namespace: Any,
    row: graph.V075ObservationRowBindingV1,
) -> graph.V075BatchAggregateSupportEvidenceV1:
    if type(value) is not graph.V075BatchAggregateSupportEvidenceV1:
        _fail("complete support contains foreign evidence")
    try:
        observed_state = graph.V075SymbolicGraphStateV1(
            row.context,
            value.observed_state.ranks,
            value.observed_state.failure,
        )
        replayed = graph.V075BatchAggregateSupportEvidenceV1(
            namespace,
            row,
            observed_state,
            value.source_observer_epoch_index,
            value.discovery_request_id,
            value.discovery_batch_id,
            value.discovery_outcome_id,
            value.discovery_outcome_count,
            value.observer_signature_hex,
        )
    except Exception as error:
        raise V075OpenSessionSupportV2InvariantViolation(
            "aggregate support evidence replay failed"
        ) from error
    if (
        replayed != value
        or replayed.to_document() != value.to_document()
        or replayed.evidence_id != value.evidence_id
    ):
        _fail("aggregate support evidence differs from semantic replay")
    return replayed


def _complete_representatives(
    discovery_batch: observer_v2.V075SignedObservationBatchV2,
) -> tuple[
    tuple[
        str,
        graph.V075SymbolicGraphStateV1,
        observer_v2.V075BatchOutcomeAggregateV2,
    ],
    ...,
]:
    """Return every symbolic successor exactly once using the least alias ID."""

    batch = _replay_batch(discovery_batch)
    stream = batch.request.stream_identity
    if (
        stream.lane is not graph.V075ObservationLaneV1.DISCOVERY
        or stream.observer_epoch_index != 0
        or stream.pairing_authority.support_chain.leaf.evidence
    ):
        _fail("complete support requires one epoch-0 DISCOVERY batch")
    by_state: dict[
        str,
        tuple[
            graph.V075SymbolicGraphStateV1,
            observer_v2.V075BatchOutcomeAggregateV2,
        ],
    ] = {}
    for outcome in batch.outcomes:
        state = graph.V075SymbolicGraphStateV1(
            stream.row_binding.context,
            outcome.next_ranks,
            outcome.failure,
        )
        prior = by_state.get(state.state_id)
        if prior is None or outcome.outcome_id < prior[1].outcome_id:
            by_state[state.state_id] = (state, outcome)
    if (
        not by_state
        or len(by_state) > graph.MAX_SUPPORT_MEMBERS_PER_ROW
    ):
        _fail("observed symbolic support is empty or exceeds its hard cap")
    return tuple(
        (state_id, *by_state[state_id]) for state_id in sorted(by_state)
    )


_FREEZE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075CompleteAggregateSupportFreezeV2:
    """All observed symbolic successors frozen before validation."""

    _issuer: object = field(repr=False, compare=False)
    discovery_batch: observer_v2.V075SignedObservationBatchV2 = field(
        repr=False
    )
    evidence: tuple[
        graph.V075BatchAggregateSupportEvidenceV1,
        ...,
    ] = field(repr=False)
    _freeze_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        batch = _replay_batch(self.discovery_batch)
        row = batch.request.stream_identity.row_binding
        namespace = batch.request.authority_binding.namespace
        if (
            self._issuer is not _FREEZE_ISSUER
            or type(self.evidence) is not tuple
            or not self.evidence
            or len(self.evidence) > graph.MAX_SUPPORT_MEMBERS_PER_ROW
        ):
            _fail("complete support freeze is caller-minted or malformed")
        replayed = tuple(
            sorted(
                (
                    _replay_support_evidence(
                        item,
                        namespace=namespace,
                        row=row,
                    )
                    for item in self.evidence
                ),
                key=lambda item: item.evidence_id,
            )
        )
        if replayed != self.evidence:
            _fail("complete support evidence is reordered or duplicated")
        expected = _complete_representatives(batch)
        by_state = {item.observed_state.state_id: item for item in replayed}
        if (
            len(by_state) != len(replayed)
            or set(by_state) != {item[0] for item in expected}
        ):
            _fail("complete support omitted or multiplied an observed state")
        for state_id, state, outcome in expected:
            item = by_state[state_id]
            if (
                item.namespace != namespace
                or item.row_binding != row
                or item.observed_state != state
                or item.source_observer_epoch_index != 0
                or item.discovery_request_id != batch.request.request_id
                or item.discovery_batch_id != batch.batch_id
                or item.discovery_outcome_id != outcome.outcome_id
                or item.discovery_outcome_count != outcome.count
            ):
                _fail(
                    "complete support does not use the canonical observed "
                    "outcome representative"
                )
        object.__setattr__(
            self,
            "_freeze_id",
            _hash("support_freeze", self._payload()),
        )

    @property
    def occurrence_id(self) -> str:
        return self.discovery_batch.request.occurrence_id

    @property
    def observer_session_public_id(self) -> str:
        return self.discovery_batch.request.session_public_id

    @property
    def observer_open_binding_id(self) -> str:
        return self.discovery_batch.request.authority_binding.binding_id

    @property
    def row_binding_id(self) -> str:
        return self.discovery_batch.request.stream_identity.row_binding_id

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(item.evidence_id for item in self.evidence)

    @property
    def observed_state_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(item.observed_state.state_id for item in self.evidence)
        )

    def _payload(self) -> dict[str, Any]:
        request = self.discovery_batch.request
        return {
            "schema": "acfqp.v075_complete_aggregate_support_freeze.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "occurrence_id": request.occurrence_id,
            "observer_session_public_id": request.session_public_id,
            "observer_open_binding_id": (
                request.authority_binding.binding_id
            ),
            "target_tape_namespace_id": (
                request.stream_identity.target_tape_namespace_id
            ),
            "context_id": request.stream_identity.context_id,
            "row_binding_id": request.stream_identity.row_binding_id,
            "discovery_stream_id": request.stream_identity.stream_id,
            "discovery_request_id": request.request_id,
            "discovery_batch_id": self.discovery_batch.batch_id,
            "source_observer_epoch_index": 0,
            "validation_observer_epoch_index": 1,
            "evidence_ids": list(self.evidence_ids),
            "observed_state_ids": list(self.observed_state_ids),
            "support_member_count": len(self.evidence),
            "all_discovery_outcomes_examined": True,
            "complete_symbolic_state_support": True,
            "spawn_aliases_deduplicated": True,
            "spawn_alias_representative_rule": "MIN_OUTCOME_ID",
            "caller_selected_support": False,
            "session_open_when_signed": True,
            "authority_version": "V2",
            "namespace_version": "V2",
            "per_draw_records_read": 0,
            "private_law_access": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "official_execution_allowed": False,
        }

    @property
    def freeze_id(self) -> str:
        return self._freeze_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "evidence": [item.to_document() for item in self.evidence],
            "freeze_id": self.freeze_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _build_complete_support_freeze(
    *,
    discovery_batch: observer_v2.V075SignedObservationBatchV2,
    evidence: tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
) -> V075CompleteAggregateSupportFreezeV2:
    batch = _replay_batch(discovery_batch)
    if type(evidence) is not tuple:
        _fail("complete support evidence must be one exact tuple")
    return V075CompleteAggregateSupportFreezeV2(
        _FREEZE_ISSUER,
        batch,
        evidence,
    )


def verify_v075_complete_aggregate_support_freeze_bytes_v2(
    *,
    discovery_batch: observer_v2.V075SignedObservationBatchV2,
    claimed_evidence: tuple[
        graph.V075BatchAggregateSupportEvidenceV1,
        ...,
    ],
    claimed_bytes: bytes,
) -> V075CompleteAggregateSupportFreezeV2:
    """Rebuild complete support from typed facts without signing new evidence."""

    document = _strict_document(claimed_bytes, "complete support freeze")
    expected = _build_complete_support_freeze(
        discovery_batch=discovery_batch,
        evidence=claimed_evidence,
    )
    if (
        set(document) != set(expected.to_document())
        or claimed_bytes != expected.canonical_bytes
    ):
        _fail("claimed support freeze differs from typed discovery replay")
    return expected


def _replay_freeze(
    value: V075CompleteAggregateSupportFreezeV2,
) -> V075CompleteAggregateSupportFreezeV2:
    if type(value) is not V075CompleteAggregateSupportFreezeV2:
        _fail("validation requires one exact complete-support freeze")
    replayed = _build_complete_support_freeze(
        discovery_batch=value.discovery_batch,
        evidence=value.evidence,
    )
    if (
        replayed.freeze_id != value.freeze_id
        or replayed.canonical_bytes != value.canonical_bytes
    ):
        _fail("complete-support freeze differs from exact replay")
    return replayed


def derive_v075_validation_stream_from_support_freeze_v2(
    *,
    support_freeze: V075CompleteAggregateSupportFreezeV2,
) -> graph.V075TransitionStreamIdentityV1:
    """Derive the only epoch-1 VALIDATION stream admitted by this freeze."""

    support_freeze = _replay_freeze(support_freeze)
    discovery = support_freeze.discovery_batch.request.stream_identity
    bootstrap = discovery.pairing_authority.support_chain.leaf
    if (
        bootstrap.epoch_index != 0
        or bootstrap.required_lane is not graph.V075ObservationLaneV1.DISCOVERY
        or bootstrap.evidence
    ):
        _fail("support freeze lacks one canonical epoch-0 bootstrap")
    try:
        promoted = graph.derive_shared_support_epoch_v1(
            namespace=discovery.namespace,
            row_binding=discovery.row_binding,
            epoch_index=1,
            evidence=support_freeze.evidence,
            parent=bootstrap,
        )
        chain = graph.freeze_shared_support_chain_v1(
            namespace=discovery.namespace,
            row_binding=discovery.row_binding,
            epochs=(bootstrap, promoted),
        )
        pairing = graph.freeze_five_arm_pairing_authority_v1(
            namespace=discovery.namespace,
            row_binding=discovery.row_binding,
            support_chain=chain,
        )
        return graph.derive_transition_stream_identity_v1(
            pairing_authority=pairing,
            arm=discovery.arm,
        )
    except Exception as error:
        raise V075OpenSessionSupportV2InvariantViolation(
            "epoch-1 validation stream derivation failed"
        ) from error


class V075OpenSessionBatchStageV2(str, Enum):
    DISCOVERY = "DISCOVERY"
    VALIDATION = "VALIDATION"


_RECEIPT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075OpenSessionBatchExecutionReceiptV2:
    """Trusted construction record for one batch handled by the controller."""

    _issuer: object = field(repr=False, compare=False)
    controller_id: str
    execution_index: int
    stage: V075OpenSessionBatchStageV2
    batch: observer_v2.V075SignedObservationBatchV2 = field(repr=False)
    support_freeze_id: str | None
    _receipt_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        batch = _replay_batch(self.batch)
        _cid(self.controller_id, "open-session support controller")
        expected_lane = graph.V075ObservationLaneV1(self.stage.value)
        if (
            self._issuer is not _RECEIPT_ISSUER
            or type(self.execution_index) is not int
            or self.execution_index <= 0
            or type(self.stage) is not V075OpenSessionBatchStageV2
            or batch.request.stream_identity.lane is not expected_lane
            or batch.request.stream_identity.observer_epoch_index
            != (0 if self.stage is V075OpenSessionBatchStageV2.DISCOVERY else 1)
        ):
            _fail("open-session execution receipt is caller-minted or stale")
        if self.stage is V075OpenSessionBatchStageV2.DISCOVERY:
            if self.support_freeze_id is not None:
                _fail("DISCOVERY receipt cannot cite a later support freeze")
        else:
            _cid(self.support_freeze_id, "validation support freeze")
        object.__setattr__(
            self,
            "_receipt_id",
            _hash("execution_receipt", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        request = self.batch.request
        return {
            "schema": "acfqp.v075_open_session_batch_execution_receipt.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "controller_id": self.controller_id,
            "execution_index": self.execution_index,
            "stage": self.stage.value,
            "occurrence_id": request.occurrence_id,
            "observer_session_public_id": request.session_public_id,
            "observer_open_binding_id": request.authority_binding.binding_id,
            "row_binding_id": request.stream_identity.row_binding_id,
            "stream_id": request.stream_identity.stream_id,
            "accepted_draw_start": request.accepted_draw_start,
            "accepted_draw_count": request.accepted_draw_count,
            "accepted_draw_end": request.accepted_draw_end,
            "accepted_draw_cap": request.accepted_draw_cap,
            "batch_id": self.batch.batch_id,
            "support_freeze_id": self.support_freeze_id,
            "trusted_in_process_controller_execution_claim": True,
            "observer_signed_control_receipt": False,
            "cryptographic_execution_causality_proven": False,
            "per_draw_records_read": 0,
            "private_law_access": False,
            "official_execution_allowed": False,
        }

    @property
    def receipt_id(self) -> str:
        return self._receipt_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "receipt_id": self.receipt_id}


def _replay_receipt(
    value: V075OpenSessionBatchExecutionReceiptV2,
) -> V075OpenSessionBatchExecutionReceiptV2:
    if (
        type(value) is not V075OpenSessionBatchExecutionReceiptV2
        or value._issuer is not _RECEIPT_ISSUER
    ):
        _fail("reconciliation requires exact controller receipts")
    replayed = V075OpenSessionBatchExecutionReceiptV2(
        _RECEIPT_ISSUER,
        value.controller_id,
        value.execution_index,
        value.stage,
        _replay_batch(value.batch),
        value.support_freeze_id,
    )
    if (
        replayed.receipt_id != value.receipt_id
        or replayed.to_document() != value.to_document()
    ):
        _fail("controller receipt differs from exact replay")
    return replayed


_RECONCILIATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075OpenSessionSupportReconciliationV2:
    """Reconcile a closed journal with trusted construction receipt records."""

    _issuer: object = field(repr=False, compare=False)
    controller_id: str
    support_freeze: V075CompleteAggregateSupportFreezeV2 = field(repr=False)
    receipts: tuple[V075OpenSessionBatchExecutionReceiptV2, ...] = field(
        repr=False
    )
    closure: observer_v2.V075ObserverBatchJournalClosureV2 = field(
        repr=False
    )
    _reconciliation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        support = _replay_freeze(self.support_freeze)
        _cid(self.controller_id, "reconciled support controller")
        if (
            self._issuer is not _RECONCILIATION_ISSUER
            or type(self.receipts) is not tuple
            or len(self.receipts) < 2
            or any(
                type(item) is not V075OpenSessionBatchExecutionReceiptV2
                for item in self.receipts
            )
            or type(self.closure)
            is not observer_v2.V075ObserverBatchJournalClosureV2
        ):
            _fail("open-session support reconciliation is malformed")
        replayed_receipts = tuple(
            _replay_receipt(item) for item in self.receipts
        )
        discovery_request = support.discovery_batch.request
        expected_controller_id = _controller_content_id(
            occurrence_id=discovery_request.occurrence_id,
            target_tape_namespace_id=(
                discovery_request.stream_identity.target_tape_namespace_id
            ),
            context_id=discovery_request.stream_identity.context_id,
            arm=discovery_request.stream_identity.arm,
            observer_session_public_id=discovery_request.session_public_id,
            observer_open_binding_id=(
                discovery_request.authority_binding.binding_id
            ),
        )
        if self.controller_id != expected_controller_id:
            _fail("support controller identity differs from exact replay")
        receipt_batches = tuple(item.batch for item in replayed_receipts)
        streams_by_id = {
            item.request.stream_identity.stream_id: item.request.stream_identity
            for item in receipt_batches
        }
        try:
            replayed_closure = (
                observer_v2.load_observer_batch_journal_closure_bytes_v2(
                    raw=self.closure.canonical_bytes,
                    authority_binding=self.closure.authority_binding,
                    known_stream_identities=tuple(
                        streams_by_id[key] for key in sorted(streams_by_id)
                    ),
                )
            )
        except Exception as error:
            raise V075OpenSessionSupportV2InvariantViolation(
                "closed V2 observer journal replay failed"
            ) from error
        closed_batches = tuple(
            entry.batch for entry in replayed_closure.entries
        )
        if (
            replayed_closure.canonical_bytes != self.closure.canonical_bytes
            or tuple(item.batch_id for item in closed_batches)
            != tuple(item.batch_id for item in receipt_batches)
            or tuple(item.execution_index for item in replayed_receipts)
            != tuple(range(1, len(replayed_receipts) + 1))
            or any(
                item.controller_id != self.controller_id
                for item in replayed_receipts
            )
            or replayed_receipts[0].stage
            is not V075OpenSessionBatchStageV2.DISCOVERY
            or replayed_receipts[0].batch.batch_id
            != support.discovery_batch.batch_id
            or any(
                item.stage is not V075OpenSessionBatchStageV2.VALIDATION
                or item.support_freeze_id != support.freeze_id
                for item in replayed_receipts[1:]
            )
            or replayed_closure.occurrence_id != support.occurrence_id
            or replayed_closure.session_public_id
            != support.observer_session_public_id
        ):
            _fail(
                "closed observer journal and controller receipts are "
                "incomplete, reordered, or transplanted"
            )
        validation = replayed_receipts[1:]
        expected_validation_stream = (
            derive_v075_validation_stream_from_support_freeze_v2(
                support_freeze=support,
            )
        )
        first = validation[0].batch.request
        expected_start = 1
        for receipt in validation:
            request = receipt.batch.request
            if (
                request.stream_identity != expected_validation_stream
                or request.stream_identity != first.stream_identity
                or request.accepted_draw_cap != first.accepted_draw_cap
                or request.accepted_draw_start != expected_start
            ):
                _fail("validation receipt stream is gapped, changed, or rerolled")
            expected_start = request.accepted_draw_end + 1
        object.__setattr__(
            self,
            "_reconciliation_id",
            _hash("reconciliation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_open_session_support_reconciliation.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "controller_id": self.controller_id,
            "support_freeze_id": self.support_freeze.freeze_id,
            "occurrence_id": self.support_freeze.occurrence_id,
            "observer_session_public_id": (
                self.support_freeze.observer_session_public_id
            ),
            "closure_id": self.closure.closure_id,
            "receipt_ids": [item.receipt_id for item in self.receipts],
            "batch_ids": [item.batch.batch_id for item in self.receipts],
            "batch_count": len(self.receipts),
            "accepted_draw_count": sum(
                item.batch.request.accepted_draw_count
                for item in self.receipts
            ),
            "all_batches_have_matching_trusted_receipt_records": True,
            "controller_execution_causality_cryptographically_proven": False,
            "observer_signed_journal_heads_present": False,
            "trusted_in_process_construction_control_flow": True,
            "complete_support_precedes_validation": True,
            "validation_stream_and_cap_frozen": True,
            "validation_prefix_contiguous": True,
            "python_reference_exclusivity_relied_upon": True,
            "independent_private_replay_still_required": True,
            "authority_version": "V2",
            "namespace_version": "V2",
            "per_draw_records_read": 0,
            "private_law_access": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "official_execution_allowed": False,
        }

    @property
    def reconciliation_id(self) -> str:
        return self._reconciliation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "support_freeze": self.support_freeze.to_document(),
            "receipts": [item.to_document() for item in self.receipts],
            "reconciliation_id": self.reconciliation_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


_CONTROLLER_ISSUER = object()
_BOUND_SESSION_PUBLIC_IDS: set[str] = set()


class V075OpenSessionSupportControllerV2:
    """Exclusive construction controller for one exact unused V2 adapter."""

    __slots__ = (
        "_adapter",
        "_closed",
        "_controller_id",
        "_discovery_batch",
        "_failed",
        "_receipts",
        "_support_freeze",
        "_validation_cap",
        "_validation_stream",
    )

    def __init__(
        self,
        *,
        adapter: batched_v2.V075OccurrenceBatchedObserverSessionV2,
        issuer: object,
    ) -> None:
        if (
            issuer is not _CONTROLLER_ISSUER
            or type(adapter)
            is not batched_v2.V075OccurrenceBatchedObserverSessionV2
            or adapter.scope
            is not batched_v2.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
            or adapter._closed  # noqa: SLF001 - exact boundary handoff
            or adapter.batches
            or adapter.session_public_id in _BOUND_SESSION_PUBLIC_IDS
        ):
            _fail(
                "support controller requires one unclaimed, unused, open "
                "construction V2 occurrence adapter"
            )
        identity = _replay_identity(adapter.occurrence_identity)
        session = adapter._session  # noqa: SLF001 - exact boundary handoff
        eligibility = session.batch_open_eligibility_v2
        if (
            session.journal_entries
            or type(eligibility) is not observer_v2.V075BatchOpenEligibilityV2
            or not eligibility.eligible
            or eligibility.status != "ELIGIBLE"
            or eligibility.session_mode != "UNUSED"
            or eligibility.occurrence_id is not None
            or eligibility.existing_batch_count != 0
        ):
            _fail("underlying exact V2 observer session is not unused")
        self._adapter = adapter
        self._controller_id = _controller_content_id(
            occurrence_id=identity.occurrence_id,
            target_tape_namespace_id=identity.target_tape_namespace_id,
            context_id=identity.context_id,
            arm=identity.arm.value,
            observer_session_public_id=adapter.session_public_id,
            observer_open_binding_id=adapter.authority_binding.binding_id,
        )
        self._discovery_batch = None
        self._support_freeze = None
        self._validation_stream = None
        self._validation_cap = None
        self._receipts: list[V075OpenSessionBatchExecutionReceiptV2] = []
        self._closed = False
        self._failed = False
        _BOUND_SESSION_PUBLIC_IDS.add(adapter.session_public_id)

    @property
    def controller_id(self) -> str:
        return self._controller_id

    @property
    def occurrence_identity(
        self,
    ) -> backend.V075BatchNativeOccurrenceIdentityV1:
        return self._adapter.occurrence_identity

    @property
    def receipts(
        self,
    ) -> tuple[V075OpenSessionBatchExecutionReceiptV2, ...]:
        return tuple(self._receipts)

    @property
    def support_freeze(
        self,
    ) -> V075CompleteAggregateSupportFreezeV2 | None:
        return self._support_freeze

    def _ensure_exact_receipted_open_prefix(self) -> None:
        if self._closed or self._failed:
            _fail("open-session support controller is closed or failed")
        session = self._adapter._session  # noqa: SLF001
        eligibility = session.batch_open_eligibility_v2
        batches = self._adapter.batches
        if (
            self._adapter._closed  # noqa: SLF001
            or session.journal_entries
            or type(eligibility) is not observer_v2.V075BatchOpenEligibilityV2
            or not eligibility.eligible
            or eligibility.status != "ELIGIBLE"
            or eligibility.existing_batch_count != len(batches)
            or tuple(item.batch_id for item in batches)
            != tuple(item.batch.batch_id for item in self._receipts)
        ):
            self._failed = True
            _fail(
                "underlying V2 session changed outside the controller or is "
                "not appendable"
            )
        if batches and (
            eligibility.session_mode != "BATCH_NATIVE"
            or eligibility.occurrence_id
            != self.occurrence_identity.occurrence_id
        ):
            self._failed = True
            _fail("underlying V2 batch-native occurrence state changed")

    def _append_receipt(
        self,
        *,
        stage: V075OpenSessionBatchStageV2,
        batch: observer_v2.V075SignedObservationBatchV2,
        support_freeze_id: str | None,
    ) -> V075OpenSessionBatchExecutionReceiptV2:
        receipt = V075OpenSessionBatchExecutionReceiptV2(
            _RECEIPT_ISSUER,
            self.controller_id,
            len(self._receipts) + 1,
            stage,
            _replay_batch(batch),
            support_freeze_id,
        )
        self._receipts.append(receipt)
        return receipt

    def observe_discovery_batch_v2(
        self,
        *,
        stream_identity: graph.V075TransitionStreamIdentityV1,
        accepted_draw_count: int,
        accepted_draw_cap: int,
    ) -> observer_v2.V075SignedObservationBatchV2:
        """Execute the sole epoch-0 DISCOVERY batch through this controller."""

        self._ensure_exact_receipted_open_prefix()
        if (
            self._discovery_batch is not None
            or self._support_freeze is not None
            or self._receipts
            or type(stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or stream_identity.lane
            is not graph.V075ObservationLaneV1.DISCOVERY
            or stream_identity.observer_epoch_index != 0
            or stream_identity.pairing_authority.support_chain.leaf.evidence
        ):
            _fail("controller accepts exactly one canonical DISCOVERY batch")
        try:
            batch = self._adapter.observe_batch_v2(
                stream_identity=stream_identity,
                accepted_draw_start=1,
                accepted_draw_count=accepted_draw_count,
                accepted_draw_cap=accepted_draw_cap,
            )
            self._append_receipt(
                stage=V075OpenSessionBatchStageV2.DISCOVERY,
                batch=batch,
                support_freeze_id=None,
            )
        except Exception:
            self._failed = True
            raise
        self._discovery_batch = batch
        return batch

    def freeze_complete_support_v2(
        self,
    ) -> V075CompleteAggregateSupportFreezeV2:
        """Sign every observed symbolic successor with no caller selection."""

        self._ensure_exact_receipted_open_prefix()
        if (
            self._discovery_batch is None
            or self._support_freeze is not None
            or len(self._receipts) != 1
            or any(
                item.stage is V075OpenSessionBatchStageV2.VALIDATION
                for item in self._receipts
            )
        ):
            _fail("complete support can freeze exactly once before validation")
        batch = _replay_batch(self._discovery_batch)
        namespace = batch.request.authority_binding.namespace
        row = batch.request.stream_identity.row_binding
        session = self._adapter._session  # noqa: SLF001
        signer = session._signer  # noqa: SLF001
        expected_key = namespace.signer_registry.observer_evidence_key
        evidence: list[graph.V075BatchAggregateSupportEvidenceV1] = []
        try:
            for _state_id, state, outcome in _complete_representatives(batch):
                message = (
                    graph.batch_aggregate_support_evidence_signing_bytes_v1(
                        namespace=namespace,
                        row_binding=row,
                        observed_state=state,
                        source_observer_epoch_index=0,
                        discovery_request_id=batch.request.request_id,
                        discovery_batch_id=batch.batch_id,
                        discovery_outcome_id=outcome.outcome_id,
                        discovery_outcome_count=outcome.count,
                    )
                )
                signature = observer_v2._sign(  # noqa: SLF001
                    signer=signer,
                    expected_key=expected_key,
                    message=message,
                )
                evidence.append(
                    graph.bind_batch_aggregate_support_evidence_v1(
                        namespace=namespace,
                        row_binding=row,
                        observed_state=state,
                        source_observer_epoch_index=0,
                        discovery_request_id=batch.request.request_id,
                        discovery_batch_id=batch.batch_id,
                        discovery_outcome_id=outcome.outcome_id,
                        discovery_outcome_count=outcome.count,
                        observer_signature_hex=signature,
                    )
                )
            support = _build_complete_support_freeze(
                discovery_batch=batch,
                evidence=tuple(
                    sorted(evidence, key=lambda item: item.evidence_id)
                ),
            )
        except Exception:
            self._failed = True
            raise
        self._support_freeze = support
        return support

    def observe_validation_batch_v2(
        self,
        *,
        support_freeze: V075CompleteAggregateSupportFreezeV2,
        accepted_draw_count: int,
        accepted_draw_cap: int,
    ) -> observer_v2.V075SignedObservationBatchV2:
        """Append one contiguous batch to the single frozen VALIDATION stream."""

        self._ensure_exact_receipted_open_prefix()
        replayed_support = _replay_freeze(support_freeze)
        if (
            self._support_freeze is None
            or replayed_support.freeze_id != self._support_freeze.freeze_id
            or replayed_support.canonical_bytes
            != self._support_freeze.canonical_bytes
            or replayed_support.observer_session_public_id
            != self._adapter.session_public_id
            or replayed_support.occurrence_id
            != self.occurrence_identity.occurrence_id
        ):
            _fail("validation support is foreign, stale, or not pre-frozen")
        stream = derive_v075_validation_stream_from_support_freeze_v2(
            support_freeze=replayed_support,
        )
        if (
            stream.row_binding_id != replayed_support.row_binding_id
            or stream.arm != self.occurrence_identity.arm.value
        ):
            _fail("validation stream changed row or occurrence arm")
        if self._validation_stream is None:
            self._validation_stream = stream
            self._validation_cap = accepted_draw_cap
            accepted_draw_start = 1
        else:
            if (
                stream != self._validation_stream
                or accepted_draw_cap != self._validation_cap
            ):
                _fail("validation stream or accepted-draw cap cannot change")
            validation_batches = tuple(
                item.batch
                for item in self._receipts
                if item.stage is V075OpenSessionBatchStageV2.VALIDATION
            )
            accepted_draw_start = (
                validation_batches[-1].request.accepted_draw_end + 1
            )
        try:
            batch = self._adapter.observe_batch_v2(
                stream_identity=stream,
                accepted_draw_start=accepted_draw_start,
                accepted_draw_count=accepted_draw_count,
                accepted_draw_cap=accepted_draw_cap,
            )
            self._append_receipt(
                stage=V075OpenSessionBatchStageV2.VALIDATION,
                batch=batch,
                support_freeze_id=replayed_support.freeze_id,
            )
        except Exception:
            self._failed = True
            raise
        return batch

    def close_and_reconcile_v2(
        self,
    ) -> V075OpenSessionSupportReconciliationV2:
        """Close once and require one receipt for every signed journal batch."""

        self._ensure_exact_receipted_open_prefix()
        if (
            self._support_freeze is None
            or len(self._receipts) < 2
            or not any(
                item.stage is V075OpenSessionBatchStageV2.VALIDATION
                for item in self._receipts
            )
        ):
            _fail("final reconciliation requires support and validation")
        try:
            closure = self._adapter.close_v2()
            result = V075OpenSessionSupportReconciliationV2(
                _RECONCILIATION_ISSUER,
                self.controller_id,
                self._support_freeze,
                tuple(self._receipts),
                closure,
            )
        except Exception:
            self._failed = True
            raise
        self._closed = True
        return result


def bind_v075_construction_open_session_support_controller_v2(
    *,
    adapter: batched_v2.V075OccurrenceBatchedObserverSessionV2,
) -> V075OpenSessionSupportControllerV2:
    """Consume one unused construction adapter into the causal controller."""

    return V075OpenSessionSupportControllerV2(
        adapter=adapter,
        issuer=_CONTROLLER_ISSUER,
    )


def open_v075_production_open_session_support_controller_v2(
    **_kwargs: Any,
) -> V075OpenSessionSupportControllerV2:
    """Production is intentionally unavailable until its byte issuer exists."""

    raise V075OpenSessionSupportProductionV2NotReady(PRODUCTION_BLOCKER)


__all__ = [
    "DOMAIN_TAGS",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PER_DRAW_REPLAY_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PRIVATE_LAW_ACCESS_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "PRODUCTION_BLOCKER",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "TERMINAL_CLASS",
    "TERMINAL_SCOPE",
    "V075CompleteAggregateSupportFreezeV2",
    "V075OpenSessionBatchExecutionReceiptV2",
    "V075OpenSessionBatchStageV2",
    "V075OpenSessionSupportControllerV2",
    "V075OpenSessionSupportProductionV2NotReady",
    "V075OpenSessionSupportReconciliationV2",
    "V075OpenSessionSupportV2InvariantViolation",
    "bind_v075_construction_open_session_support_controller_v2",
    "derive_v075_validation_stream_from_support_freeze_v2",
    "open_v075_production_open_session_support_controller_v2",
    "verify_v075_complete_aggregate_support_freeze_bytes_v2",
]
