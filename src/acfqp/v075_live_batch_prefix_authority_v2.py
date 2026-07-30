"""Publicly verifiable checkpoints over one still-open V0-075 V2 batch session.

Dynamic acquisition cannot be implemented by closing an occurrence lineage
after every planning decision: closing destroys the only state that can append
the next contiguous prefix of an existing transition stream.  This authority
therefore freezes content-addressed checkpoints from already signed aggregate
batches while the parent-owned session remains open.  It never reads a
per-draw record or private law.

Every checkpoint is provisional and noncertifying.  After the session is
closed exactly once, the complete checkpoint chain must be reconstructed from
the signed final lineage.  That reconciliation proves that the claimed bytes
are exact journal prefixes and that no checkpoint reordered, removed, or
invented observer work.  It does *not* prove that a checkpoint existed before
the next draw: production causality still requires an observer-signed journal
head plus a subsequent request bound to that head and its frozen intent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.52.0"
PROFILE_KEY = "v075_live_batch_prefix_authority_v2"
MAX_CHECKPOINTS = 64
MAX_BATCHES = 256
MAX_CANONICAL_INPUT_BYTES = 64 * 1024 * 1024

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
PER_DRAW_REPLAY_ALLOWED = False
PRIVATE_LAW_ACCESS_ALLOWED = False

TERMINAL_SCOPE = "INTERMEDIATE_PREFIX_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
PRODUCTION_BLOCKER = (
    "live-prefix checkpoints are only an intermediate authority; the V2 "
    "observer-signed head and intent-bound append protocol, dynamic runner, "
    "independent total lift, and production bundle verifier are not integrated"
)

DOMAIN_TAGS = {
    "checkpoint": "acfqp:v075-live-batch-prefix-checkpoint:v2",
    "reconciliation": "acfqp:v075-live-batch-prefix-reconciliation:v2",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 live-prefix domains must be unique")


class V075LiveBatchPrefixV2InvariantViolation(ValueError):
    """A session prefix, checkpoint chain, or final lineage was invalid."""


class V075LiveBatchPrefixProductionV2NotReady(RuntimeError):
    """The intermediate prefix authority cannot authorize production."""


def _fail(message: str) -> NoReturn:
    raise V075LiveBatchPrefixV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075LiveBatchPrefixV2InvariantViolation(str(error)) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075LiveBatchPrefixV2InvariantViolation(
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
        raise V075LiveBatchPrefixV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


def _replay_identity(
    claimed: backend.V075BatchNativeOccurrenceIdentityV1,
) -> backend.V075BatchNativeOccurrenceIdentityV1:
    try:
        return backend.replay_v075_batch_native_occurrence_identity_v1(
            claimed
        )
    except Exception as error:
        raise V075LiveBatchPrefixV2InvariantViolation(
            "live-prefix occurrence identity replay failed"
        ) from error


def _group_by_stream(
    batches: tuple[observer_v2.V075SignedObservationBatchV2, ...],
) -> dict[str, tuple[observer_v2.V075SignedObservationBatchV2, ...]]:
    grouped: dict[
        str,
        list[observer_v2.V075SignedObservationBatchV2],
    ] = {}
    for batch in batches:
        grouped.setdefault(
            batch.request.stream_identity.stream_id,
            [],
        ).append(batch)
    return {key: tuple(values) for key, values in grouped.items()}


_CHECKPOINT_ISSUER = object()
_RECONCILIATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075LiveBatchPrefixCheckpointV2:
    """One monotone checkpoint of signed aggregates in journal order."""

    _issuer: object = field(repr=False, compare=False)
    scope: batched_v2.V075BatchOccurrenceAuthorityScopeV2
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1 = field(
        repr=False
    )
    batches: tuple[observer_v2.V075SignedObservationBatchV2, ...] = field(
        repr=False
    )
    public_verifications: tuple[
        batched_v2.V075BatchPublicVerificationV2,
        ...,
    ]
    sequence_verifications: tuple[
        batched_v2.V075BatchSequenceVerificationV2,
        ...,
    ]
    checkpoint_index: int
    parent_checkpoint_id: str | None
    parent_batch_count: int
    appended_batch_ids: tuple[str, ...]
    _checkpoint_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        identity = _replay_identity(self.occurrence_identity)
        if (
            self._issuer is not _CHECKPOINT_ISSUER
            or type(self.scope)
            is not batched_v2.V075BatchOccurrenceAuthorityScopeV2
            or type(self.occurrence_identity)
            is not backend.V075BatchNativeOccurrenceIdentityV1
            or type(self.batches) is not tuple
            or not self.batches
            or len(self.batches) > MAX_BATCHES
            or any(
                type(item)
                is not observer_v2.V075SignedObservationBatchV2
                for item in self.batches
            )
            or type(self.public_verifications) is not tuple
            or type(self.sequence_verifications) is not tuple
            or type(self.checkpoint_index) is not int
            or self.checkpoint_index not in range(1, MAX_CHECKPOINTS + 1)
            or type(self.parent_batch_count) is not int
            or not 0 <= self.parent_batch_count < len(self.batches)
            or type(self.appended_batch_ids) is not tuple
            or not self.appended_batch_ids
        ):
            _fail("live-prefix checkpoint is malformed or caller-minted")

        replayed_batches: list[
            observer_v2.V075SignedObservationBatchV2
        ] = []
        expected_public: list[
            batched_v2.V075BatchPublicVerificationV2
        ] = []
        for batch in self.batches:
            try:
                replayed = observer_v2.replay_signed_observation_batch_object_v2(
                    batch
                )
                public = batched_v2.verify_v075_signed_observation_batch_v2(
                    replayed
                )
            except Exception as error:
                raise V075LiveBatchPrefixV2InvariantViolation(
                    "signed live-prefix batch replay failed"
                ) from error
            replayed_batches.append(replayed)
            expected_public.append(public)

        replayed_tuple = tuple(replayed_batches)
        batch_ids = tuple(item.batch_id for item in replayed_tuple)
        if len(set(batch_ids)) != len(batch_ids):
            _fail("live-prefix checkpoint reuses one signed batch")
        first_request = replayed_tuple[0].request
        if any(
            batch.request.occurrence_id != identity.occurrence_id
            or batch.request.stream_identity.target_tape_namespace_id
            != identity.target_tape_namespace_id
            or batch.request.stream_identity.context_id != identity.context_id
            or batch.request.stream_identity.arm != identity.arm.value
            or batch.request.session_public_id
            != first_request.session_public_id
            or batch.request.authority_binding.binding_id
            != first_request.authority_binding.binding_id
            for batch in replayed_tuple
        ):
            _fail("live-prefix batches are mixed across one occurrence session")
        grouped = _group_by_stream(replayed_tuple)
        try:
            expected_sequences = tuple(
                batched_v2.verify_v075_observation_batch_sequence_v2(
                    grouped[stream_id]
                )
                for stream_id in sorted(grouped)
            )
        except Exception as error:
            raise V075LiveBatchPrefixV2InvariantViolation(
                "live-prefix stream sequence replay failed"
            ) from error
        if (
            tuple(expected_public) != self.public_verifications
            or expected_sequences != self.sequence_verifications
            or self.appended_batch_ids != batch_ids[self.parent_batch_count :]
        ):
            _fail("live-prefix verification or appended suffix changed")
        if self.checkpoint_index == 1:
            if (
                self.parent_checkpoint_id is not None
                or self.parent_batch_count != 0
            ):
                _fail("first live-prefix checkpoint cannot have a parent")
        else:
            if self.parent_checkpoint_id is None:
                _fail("later live-prefix checkpoint lacks its exact parent")
            _cid(self.parent_checkpoint_id, "parent live-prefix checkpoint")
        object.__setattr__(
            self,
            "_checkpoint_id",
            _hash("checkpoint", self._payload()),
        )

    @property
    def occurrence_id(self) -> str:
        return self.occurrence_identity.occurrence_id

    @property
    def batch_ids(self) -> tuple[str, ...]:
        return tuple(item.batch_id for item in self.batches)

    @property
    def observer_session_public_id(self) -> str:
        return self.batches[0].request.session_public_id

    @property
    def observer_open_binding_id(self) -> str:
        return self.batches[0].request.authority_binding.binding_id

    def _payload(self) -> dict[str, Any]:
        identity = self.occurrence_identity
        return {
            "schema": "acfqp.v075_live_batch_prefix_checkpoint.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "scope": self.scope.value,
            "occurrence_id": identity.occurrence_id,
            "target_tape_namespace_id": identity.target_tape_namespace_id,
            "context_id": identity.context_id,
            "arm": identity.arm.value,
            "observer_session_public_id": self.observer_session_public_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "checkpoint_index": self.checkpoint_index,
            "parent_checkpoint_id": self.parent_checkpoint_id,
            "parent_batch_count": self.parent_batch_count,
            "batch_ids": list(self.batch_ids),
            "appended_batch_ids": list(self.appended_batch_ids),
            "public_verification_ids": [
                item.verification_id for item in self.public_verifications
            ],
            "sequence_verification_ids": [
                item.verification_id for item in self.sequence_verifications
            ],
            "batch_count": len(self.batches),
            "accepted_draw_count": sum(
                item.request.accepted_draw_count for item in self.batches
            ),
            "stream_count": len(self.sequence_verifications),
            "signed_aggregate_prefix_only": True,
            "session_open_when_frozen": True,
            "final_lineage_reconciliation_required": True,
            "observer_signed_checkpoint_head": False,
            "next_batch_request_binds_checkpoint": False,
            "production_causality_proven": False,
            "trusted_construction_generation_only": True,
            "per_draw_records_read": 0,
            "private_law_access": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "official_execution_allowed": False,
        }

    @property
    def checkpoint_id(self) -> str:
        return self._checkpoint_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "public_verifications": [
                item.to_document() for item in self.public_verifications
            ],
            "sequence_verifications": [
                item.to_document() for item in self.sequence_verifications
            ],
            "checkpoint_id": self.checkpoint_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _freeze_from_batches(
    *,
    scope: batched_v2.V075BatchOccurrenceAuthorityScopeV2,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    batches: tuple[observer_v2.V075SignedObservationBatchV2, ...],
    parent: V075LiveBatchPrefixCheckpointV2 | None,
) -> V075LiveBatchPrefixCheckpointV2:
    identity = _replay_identity(occurrence_identity)
    if not batches:
        _fail("cannot freeze an empty live-prefix checkpoint")
    if parent is None:
        checkpoint_index = 1
        parent_id = None
        parent_count = 0
    else:
        if (
            type(parent) is not V075LiveBatchPrefixCheckpointV2
            or parent.scope is not scope
            or parent.occurrence_identity != identity
            or len(parent.batches) >= len(batches)
            or parent.batch_ids
            != tuple(item.batch_id for item in batches[: len(parent.batches)])
            or parent.observer_session_public_id
            != batches[0].request.session_public_id
            or parent.observer_open_binding_id
            != batches[0].request.authority_binding.binding_id
        ):
            _fail("live-prefix checkpoint does not strictly extend its parent")
        checkpoint_index = parent.checkpoint_index + 1
        parent_id = parent.checkpoint_id
        parent_count = len(parent.batches)
    public_verifications = tuple(
        batched_v2.verify_v075_signed_observation_batch_v2(item)
        for item in batches
    )
    grouped = _group_by_stream(batches)
    sequences = tuple(
        batched_v2.verify_v075_observation_batch_sequence_v2(
            grouped[stream_id]
        )
        for stream_id in sorted(grouped)
    )
    return V075LiveBatchPrefixCheckpointV2(
        _CHECKPOINT_ISSUER,
        scope,
        identity,
        batches,
        public_verifications,
        sequences,
        checkpoint_index,
        parent_id,
        parent_count,
        tuple(item.batch_id for item in batches[parent_count:]),
    )


def freeze_v075_live_batch_prefix_checkpoint_v2(
    *,
    adapter: batched_v2.V075OccurrenceBatchedObserverSessionV2,
    parent: V075LiveBatchPrefixCheckpointV2 | None = None,
) -> V075LiveBatchPrefixCheckpointV2:
    """Freeze the exact signed journal prefix without closing the session."""

    if type(adapter) is not batched_v2.V075OccurrenceBatchedObserverSessionV2:
        _fail("live-prefix freeze requires one exact V2 occurrence adapter")
    if (
        adapter.scope
        is batched_v2.V075BatchOccurrenceAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
    ):
        _fail(
            "production live-prefix freeze awaits observer-signed causal heads"
        )
    if adapter._closed:  # noqa: SLF001 - same-package authority boundary
        _fail("live-prefix checkpoint must be frozen before session close")
    session = adapter._session  # noqa: SLF001 - same-package authority boundary
    eligibility = session.batch_open_eligibility_v2
    if (
        type(eligibility) is not observer_v2.V075BatchOpenEligibilityV2
        or not eligibility.eligible
        or eligibility.status != "ELIGIBLE"
        or eligibility.session_mode != "BATCH_NATIVE"
        or eligibility.occurrence_id
        != adapter.occurrence_identity.occurrence_id
        or eligibility.session_public_id != adapter.session_public_id
        or eligibility.observer_open_binding_id
        != adapter.authority_binding.binding_id
        or eligibility.existing_batch_count != len(adapter.batches)
    ):
        _fail("underlying V2 observer session is not one appendable prefix")
    return _freeze_from_batches(
        scope=adapter.scope,
        occurrence_identity=adapter.occurrence_identity,
        batches=adapter.batches,
        parent=parent,
    )


def verify_v075_live_batch_prefix_checkpoint_bytes_v2(
    *,
    scope: batched_v2.V075BatchOccurrenceAuthorityScopeV2,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    batches: tuple[observer_v2.V075SignedObservationBatchV2, ...],
    parent: V075LiveBatchPrefixCheckpointV2 | None,
    claimed_bytes: bytes,
) -> V075LiveBatchPrefixCheckpointV2:
    """Rebuild one checkpoint from typed batch references and exact bytes."""

    if (
        scope
        is batched_v2.V075BatchOccurrenceAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
    ):
        _fail(
            "production checkpoint bytes require the future signed-head "
            "authority"
        )
    document = _strict_document(
        claimed_bytes,
        "live-prefix checkpoint",
    )
    expected = _freeze_from_batches(
        scope=scope,
        occurrence_identity=occurrence_identity,
        batches=batches,
        parent=parent,
    )
    if (
        set(document) != set(expected.to_document())
        or claimed_bytes != expected.canonical_bytes
    ):
        _fail("live-prefix checkpoint differs from exact typed-batch replay")
    return expected


@dataclass(frozen=True, slots=True)
class V075LiveBatchPrefixReconciliationV2:
    """Exact reconstruction of a checkpoint chain from the final lineage."""

    _issuer: object = field(repr=False, compare=False)
    lineage_id: str
    occurrence_id: str
    checkpoint_ids: tuple[str, ...]
    final_batch_count: int
    final_accepted_draw_count: int
    _reconciliation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.lineage_id, "reconciled final lineage")
        _cid(self.occurrence_id, "reconciled occurrence")
        if (
            self._issuer is not _RECONCILIATION_ISSUER
            or type(self.checkpoint_ids) is not tuple
            or not self.checkpoint_ids
            or len(self.checkpoint_ids) > MAX_CHECKPOINTS
            or any(
                _cid(item, "reconciled live-prefix checkpoint") != item
                for item in self.checkpoint_ids
            )
            or len(set(self.checkpoint_ids)) != len(self.checkpoint_ids)
            or type(self.final_batch_count) is not int
            or self.final_batch_count <= 0
            or type(self.final_accepted_draw_count) is not int
            or self.final_accepted_draw_count <= 0
        ):
            _fail("live-prefix final reconciliation is malformed")
        object.__setattr__(
            self,
            "_reconciliation_id",
            _hash("reconciliation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_batch_prefix_reconciliation.v2",
            "schema_version": SCHEMA_VERSION,
            "lineage_id": self.lineage_id,
            "occurrence_id": self.occurrence_id,
            "checkpoint_ids": list(self.checkpoint_ids),
            "final_batch_count": self.final_batch_count,
            "final_accepted_draw_count": self.final_accepted_draw_count,
            "strict_checkpoint_indices_replayed": True,
            "strict_parent_chain_replayed": True,
            "strict_journal_prefixes_replayed": True,
            "last_checkpoint_equals_final_lineage": True,
            "observer_batch_signatures_replayed": True,
            "observer_signed_checkpoint_heads_replayed": False,
            "intent_bound_append_causality_proven": False,
            "production_causality_authority_still_required": True,
            "per_draw_records_replayed": 0,
            "private_law_access": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def reconciliation_id(self) -> str:
        return self._reconciliation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "reconciliation_id": self.reconciliation_id,
        }


def reconcile_v075_live_batch_prefix_chain_v2(
    *,
    final_lineage: batched_v2.V075BatchOccurrenceLineageV2,
    checkpoints: tuple[V075LiveBatchPrefixCheckpointV2, ...],
) -> V075LiveBatchPrefixReconciliationV2:
    """Rebuild every checkpoint as a strict prefix of the signed closure."""

    if (
        type(final_lineage) is not batched_v2.V075BatchOccurrenceLineageV2
        or type(checkpoints) is not tuple
        or not checkpoints
        or len(checkpoints) > MAX_CHECKPOINTS
        or any(
            type(item) is not V075LiveBatchPrefixCheckpointV2
            for item in checkpoints
        )
    ):
        _fail("final live-prefix reconciliation inputs are untyped")
    try:
        lineage = batched_v2.replay_v075_signed_batch_occurrence_lineage_v2(
            final_lineage
        )
    except Exception as error:
        raise V075LiveBatchPrefixV2InvariantViolation(
            "final signed V2 lineage replay failed"
        ) from error
    if (
        lineage.scope
        is batched_v2.V075BatchOccurrenceAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
    ):
        _fail(
            "production prefix reconciliation requires the future independent "
            "private-replay verification chain"
        )
    batches = tuple(entry.batch for entry in lineage.closure.entries)
    if not batches:
        _fail("final lineage cannot reconcile an empty checkpoint chain")
    parent: V075LiveBatchPrefixCheckpointV2 | None = None
    rebuilt: list[V075LiveBatchPrefixCheckpointV2] = []
    prior_count = 0
    for index, claimed in enumerate(checkpoints, start=1):
        count = len(claimed.batches)
        if (
            claimed.checkpoint_index != index
            or count <= prior_count
            or count > len(batches)
        ):
            _fail("checkpoint indices or prefix lengths are not monotone")
        expected = _freeze_from_batches(
            scope=lineage.scope,
            occurrence_identity=lineage.occurrence_identity,
            batches=batches[:count],
            parent=parent,
        )
        if (
            expected.checkpoint_id != claimed.checkpoint_id
            or expected.canonical_bytes != claimed.canonical_bytes
        ):
            _fail("checkpoint differs from exact final-lineage prefix replay")
        rebuilt.append(expected)
        parent = expected
        prior_count = count
    if prior_count != len(batches):
        _fail("last live-prefix checkpoint does not equal final lineage")
    return V075LiveBatchPrefixReconciliationV2(
        _RECONCILIATION_ISSUER,
        lineage.lineage_id,
        lineage.occurrence_identity.occurrence_id,
        tuple(item.checkpoint_id for item in rebuilt),
        len(batches),
        sum(item.request.accepted_draw_count for item in batches),
    )


def open_v075_production_live_batch_prefix_authority_v2(
    *_args: Any,
    **_kwargs: Any,
) -> NoReturn:
    """Remain structurally locked until the complete production runner exists."""

    raise V075LiveBatchPrefixProductionV2NotReady(PRODUCTION_BLOCKER)


__all__ = [
    "DOMAIN_TAGS",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "MAX_BATCHES",
    "MAX_CANONICAL_INPUT_BYTES",
    "MAX_CHECKPOINTS",
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
    "V075LiveBatchPrefixCheckpointV2",
    "V075LiveBatchPrefixProductionV2NotReady",
    "V075LiveBatchPrefixReconciliationV2",
    "V075LiveBatchPrefixV2InvariantViolation",
    "freeze_v075_live_batch_prefix_checkpoint_v2",
    "open_v075_production_live_batch_prefix_authority_v2",
    "reconcile_v075_live_batch_prefix_chain_v2",
    "verify_v075_live_batch_prefix_checkpoint_bytes_v2",
]
