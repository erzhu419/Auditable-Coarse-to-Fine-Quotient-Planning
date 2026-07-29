"""Occurrence-bound, batch-native consumer for the exact V0-075 V2 observer.

The private observer boundary performs every target draw and emits exactly
one signed aggregate plus one append-only journal entry per requested batch.
This module binds those aggregates to a pre-observation occurrence identity,
replays each public signature and stream prefix, and freezes one law-free
occurrence lineage.

Production entry points consume the exact V2 reveal, authorization, namespace,
and closure bytes through the observer boundary's byte authority gate.  The
construction entry point is deliberately typed as ``CONSTRUCTION_ONLY`` and
cannot be promoted to a production lineage.  Neither path projects a V2
authority or namespace into a historical V1 claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.44.0"
PROFILE_KEY = "v075_batched_observer_authority_v2"

PER_DRAW_RECORDS_ALLOWED = False
V1_AUTHORITY_PROJECTION_ALLOWED = False
V1_NAMESPACE_PROJECTION_ALLOWED = False
OFFICIAL_EXECUTION_UNLOCKED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False

DOMAIN_TAGS = {
    "batch_public_verification": (
        "acfqp:v075-batch-public-verification:v2"
    ),
    "batch_sequence_verification": (
        "acfqp:v075-batch-sequence-verification:v2"
    ),
    "occurrence_lineage": (
        "acfqp:v075-batch-occurrence-lineage:v2"
    ),
    "production_lineage_verification": (
        "acfqp:v075-production-batch-occurrence-lineage-verification:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 batched-observer V2 domains must be unique")


class V075BatchedObserverV2InvariantViolation(ValueError):
    """A V2 batch, occurrence, sequence, closure, or byte gate was invalid."""


def _fail(message: str) -> None:
    raise V075BatchedObserverV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075BatchedObserverV2InvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075BatchedObserverV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _bytes_sha256(raw: bytes, field_name: str) -> str:
    if type(raw) is not bytes or not raw:
        _fail(f"{field_name} must be nonempty exact bytes")
    return hashlib.sha256(raw).hexdigest()


def _replay_occurrence_identity(
    claimed: backend.V075BatchNativeOccurrenceIdentityV1,
) -> backend.V075BatchNativeOccurrenceIdentityV1:
    try:
        return backend.replay_v075_batch_native_occurrence_identity_v1(
            claimed
        )
    except backend.V075BatchNativeBackendInvariantViolation as error:
        raise V075BatchedObserverV2InvariantViolation(str(error)) from error


class V075BatchOccurrenceAuthorityScopeV2(str, Enum):
    CONSTRUCTION_ONLY = "CONSTRUCTION_ONLY"
    PRODUCTION_BYTE_REPLAY = "PRODUCTION_BYTE_REPLAY"


_PUBLIC_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchPublicVerificationV2:
    """Deterministic public replay of one exact signed aggregate."""

    _issuer: object = field(repr=False, compare=False)
    batch_id: str
    request_id: str
    occurrence_id: str
    observer_session_public_id: str
    observer_open_binding_id: str
    observer_open_authorization_id: str
    target_tape_namespace_id: str
    context_id: str
    stream_id: str
    accepted_draw_count: int
    outcome_aggregate_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.batch_id, "publicly verified V2 batch"),
            (self.request_id, "publicly verified V2 batch request"),
            (self.occurrence_id, "publicly verified V2 occurrence"),
            (
                self.observer_session_public_id,
                "publicly verified V2 observer session",
            ),
            (
                self.observer_open_binding_id,
                "publicly verified V2 observer binding",
            ),
            (
                self.observer_open_authorization_id,
                "publicly verified V2 observer authorization",
            ),
            (
                self.target_tape_namespace_id,
                "publicly verified V2 target namespace",
            ),
            (self.context_id, "publicly verified V2 context"),
            (self.stream_id, "publicly verified V2 stream"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _PUBLIC_VERIFICATION_ISSUER
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count <= 0
            or type(self.outcome_aggregate_count) is not int
            or self.outcome_aggregate_count <= 0
        ):
            _fail("public V2 batch verification is caller-minted or empty")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("batch_public_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_public_verification.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "batch_id": self.batch_id,
            "request_id": self.request_id,
            "occurrence_id": self.occurrence_id,
            "observer_session_public_id": self.observer_session_public_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "observer_open_authorization_id": (
                self.observer_open_authorization_id
            ),
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "stream_id": self.stream_id,
            "accepted_draw_count": self.accepted_draw_count,
            "outcome_aggregate_count": self.outcome_aggregate_count,
            "observer_signature_verified": True,
            "aggregate_reconciliation_verified": True,
            "rsa_signatures_verified": 1,
            "per_draw_records_verified": 0,
            "authority_version": "V2",
            "namespace_version": "V2",
            "legacy_v1_projection_used": False,
            "private_material_serialized": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_signed_observation_batch_v2(
    batch: observer.V075SignedObservationBatchV2,
) -> V075BatchPublicVerificationV2:
    """Reconstruct the exact batch and recheck its aggregate signature."""

    try:
        replayed = observer.replay_signed_observation_batch_object_v2(
            batch
        )
    except observer.V075PrivateObserverBoundaryV2InvariantViolation as error:
        raise V075BatchedObserverV2InvariantViolation(str(error)) from error
    request = replayed.request
    binding = request.authority_binding
    return V075BatchPublicVerificationV2(
        _PUBLIC_VERIFICATION_ISSUER,
        replayed.batch_id,
        request.request_id,
        request.occurrence_id,
        request.session_public_id,
        binding.binding_id,
        binding.authorization_id,
        request.stream_identity.target_tape_namespace_id,
        request.stream_identity.context_id,
        request.stream_identity.stream_id,
        request.accepted_draw_count,
        len(replayed.outcomes),
    )


_SEQUENCE_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchSequenceVerificationV2:
    """One independently replayed, gap-free stream prefix."""

    _issuer: object = field(repr=False, compare=False)
    occurrence_id: str
    observer_session_public_id: str
    observer_open_binding_id: str
    target_tape_namespace_id: str
    context_id: str
    stream_id: str
    accepted_draw_cap: int
    batch_ids: tuple[str, ...]
    accepted_draw_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "sequence V2 occurrence"),
            (self.observer_session_public_id, "sequence V2 session"),
            (self.observer_open_binding_id, "sequence V2 binding"),
            (self.target_tape_namespace_id, "sequence V2 namespace"),
            (self.context_id, "sequence V2 context"),
            (self.stream_id, "sequence V2 stream"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _SEQUENCE_VERIFICATION_ISSUER
            or type(self.accepted_draw_cap) is not int
            or self.accepted_draw_cap <= 0
            or type(self.batch_ids) is not tuple
            or not self.batch_ids
            or any(
                _cid(item, "sequence V2 batch") != item
                for item in self.batch_ids
            )
            or len(set(self.batch_ids)) != len(self.batch_ids)
            or type(self.accepted_draw_count) is not int
            or not 0 < self.accepted_draw_count <= self.accepted_draw_cap
        ):
            _fail("V2 batch sequence verification is caller-minted or invalid")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("batch_sequence_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_sequence_verification.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "observer_session_public_id": self.observer_session_public_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "stream_id": self.stream_id,
            "accepted_draw_cap": self.accepted_draw_cap,
            "batch_ids": list(self.batch_ids),
            "accepted_draw_count": self.accepted_draw_count,
            "first_accepted_draw_index": 1,
            "last_accepted_draw_index": self.accepted_draw_count,
            "contiguous_prefix_verified": True,
            "gap_count": 0,
            "overlap_count": 0,
            "per_draw_records_replayed": 0,
            "authority_version": "V2",
            "namespace_version": "V2",
            "legacy_v1_projection_used": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_observation_batch_sequence_v2(
    batches: tuple[observer.V075SignedObservationBatchV2, ...],
) -> V075BatchSequenceVerificationV2:
    """Verify one stream's journal-ordered batches as a complete prefix."""

    if (
        type(batches) is not tuple
        or not batches
        or any(
            type(item) is not observer.V075SignedObservationBatchV2
            for item in batches
        )
    ):
        _fail("V2 batch sequence requires one nonempty exact batch tuple")
    try:
        replayed_batches = tuple(
            observer.replay_signed_observation_batch_object_v2(item)
            for item in batches
        )
    except observer.V075PrivateObserverBoundaryV2InvariantViolation as error:
        raise V075BatchedObserverV2InvariantViolation(str(error)) from error
    first = replayed_batches[0].request
    expected_start = 1
    batch_ids: list[str] = []
    for batch in replayed_batches:
        request = batch.request
        if (
            request.occurrence_id != first.occurrence_id
            or request.session_public_id != first.session_public_id
            or request.authority_binding != first.authority_binding
            or request.stream_identity != first.stream_identity
            or request.accepted_draw_cap != first.accepted_draw_cap
            or request.accepted_draw_start != expected_start
            or batch.batch_id in batch_ids
        ):
            _fail(
                "V2 batch stream prefix is mixed, gapped, overlapped, "
                "reordered, or reused"
            )
        verify_v075_signed_observation_batch_v2(batch)
        batch_ids.append(batch.batch_id)
        expected_start = request.accepted_draw_end + 1
    return V075BatchSequenceVerificationV2(
        _SEQUENCE_VERIFICATION_ISSUER,
        first.occurrence_id,
        first.session_public_id,
        first.authority_binding.binding_id,
        first.stream_identity.target_tape_namespace_id,
        first.stream_identity.context_id,
        first.stream_identity.stream_id,
        first.accepted_draw_cap,
        tuple(batch_ids),
        expected_start - 1,
    )


_ADAPTER_ISSUER = object()


class V075OccurrenceBatchedObserverSessionV2:
    """Exclusive occurrence adapter over one exact V2 private session."""

    __slots__ = ("_closed", "_identity", "_scope", "_session")

    def __init__(
        self,
        *,
        session: observer.V075PrivateObserverSessionV2,
        occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
        scope: V075BatchOccurrenceAuthorityScopeV2,
        issuer: object,
    ) -> None:
        occurrence_identity = _replay_occurrence_identity(
            occurrence_identity
        )
        eligibility = session.batch_open_eligibility_v2
        if (
            issuer is not _ADAPTER_ISSUER
            or type(session) is not observer.V075PrivateObserverSessionV2
            or type(scope) is not V075BatchOccurrenceAuthorityScopeV2
            or session.journal_entries
            or session.batch_journal_entries
            or type(eligibility) is not observer.V075BatchOpenEligibilityV2
            or not eligibility.eligible
            or eligibility.status != "ELIGIBLE"
            or eligibility.session_mode != "UNUSED"
            or eligibility.occurrence_id is not None
            or eligibility.existing_batch_count != 0
            or eligibility.session_public_id != session.session_public_id
            or eligibility.observer_open_binding_id
            != session.authority_binding.binding_id
            or session.authority_binding.namespace.target_tape_namespace_id
            != occurrence_identity.target_tape_namespace_id
        ):
            _fail(
                "V2 occurrence adapter requires one unused exact session "
                "and its pre-observation identity"
            )
        self._session = session
        self._identity = occurrence_identity
        self._scope = scope
        self._closed = False

    @property
    def occurrence_identity(
        self,
    ) -> backend.V075BatchNativeOccurrenceIdentityV1:
        return self._identity

    @property
    def scope(self) -> V075BatchOccurrenceAuthorityScopeV2:
        return self._scope

    @property
    def session_public_id(self) -> str:
        return self._session.session_public_id

    @property
    def authority_binding(self) -> observer.V075ObserverOpenAuthorityBindingV2:
        return self._session.authority_binding

    @property
    def batches(self) -> tuple[observer.V075SignedObservationBatchV2, ...]:
        return tuple(
            entry.batch for entry in self._session.batch_journal_entries
        )

    def observe_batch_v2(
        self,
        *,
        stream_identity: graph.V075TransitionStreamIdentityV1,
        accepted_draw_start: int,
        accepted_draw_count: int,
        accepted_draw_cap: int,
    ) -> observer.V075SignedObservationBatchV2:
        if self._closed:
            _fail("V2 occurrence batch adapter is closed")
        identity = self._identity
        if (
            type(stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or stream_identity.target_tape_namespace_id
            != identity.target_tape_namespace_id
            or stream_identity.context_id != identity.context_id
            or stream_identity.arm != identity.arm.value
        ):
            _fail("V2 batch stream was transplanted across occurrence identity")
        return self._session.observe_batch_v2(
            occurrence_id=identity.occurrence_id,
            stream_identity=stream_identity,
            accepted_draw_start=accepted_draw_start,
            accepted_draw_count=accepted_draw_count,
            accepted_draw_cap=accepted_draw_cap,
        )

    def close_v2(self) -> observer.V075ObserverBatchJournalClosureV2:
        if self._closed:
            _fail("V2 occurrence batch adapter is already closed")
        closure = self._session.close_batch_v2()
        self._closed = True
        if closure.occurrence_id != self._identity.occurrence_id:
            _fail("closed V2 batch journal carries a foreign occurrence")
        return closure


def bind_v075_construction_occurrence_batched_observer_v2(
    *,
    session: observer.V075PrivateObserverSessionV2,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
) -> V075OccurrenceBatchedObserverSessionV2:
    """Bind a synthetic exact-V2 session without granting production scope."""

    return V075OccurrenceBatchedObserverSessionV2(
        session=session,
        occurrence_identity=occurrence_identity,
        scope=V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY,
        issuer=_ADAPTER_ISSUER,
    )


def open_v075_production_occurrence_batched_observer_v2(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    private_salt: bytes,
    private_environment: Iterable[Any],
    observer_signer: observer.V075ObserverEvidenceSignerProtocolV2,
    session_external_id: str,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
) -> V075OccurrenceBatchedObserverSessionV2:
    """Open only through the production V2 byte gate, then bind occurrence."""

    if (
        type(occurrence_identity)
        is not backend.V075BatchNativeOccurrenceIdentityV1
    ):
        _fail("production V2 batch open requires one exact occurrence identity")
    occurrence_identity = _replay_occurrence_identity(occurrence_identity)
    session = observer.open_private_observer_v2(
        repository_root=repository_root,
        private_reveal_attestation_bytes=private_reveal_attestation_bytes,
        claimed_authorization_bytes=claimed_authorization_bytes,
        namespace_bytes=namespace_bytes,
        private_salt=private_salt,
        private_environment=private_environment,
        observer_signer=observer_signer,
        session_external_id=session_external_id,
    )
    return V075OccurrenceBatchedObserverSessionV2(
        session=session,
        occurrence_identity=occurrence_identity,
        scope=V075BatchOccurrenceAuthorityScopeV2.PRODUCTION_BYTE_REPLAY,
        issuer=_ADAPTER_ISSUER,
    )


_CONSTRUCTION_LINEAGE_ISSUER = object()
_PRODUCTION_LINEAGE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchOccurrenceLineageV2:
    """Complete batch journal lineage for one pre-frozen occurrence."""

    _issuer: object = field(repr=False, compare=False)
    scope: V075BatchOccurrenceAuthorityScopeV2
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1
    closure: observer.V075ObserverBatchJournalClosureV2 = field(repr=False)
    closure_verification: (
        observer.V075ObserverBatchClosureVerificationV2
    )
    public_verifications: tuple[V075BatchPublicVerificationV2, ...]
    sequence_verifications: tuple[V075BatchSequenceVerificationV2, ...]
    private_reveal_attestation_bytes_sha256: str
    authorization_bytes_sha256: str
    namespace_bytes_sha256: str
    closure_bytes_sha256: str
    _lineage_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        replayed_identity = _replay_occurrence_identity(
            self.occurrence_identity
        )
        production = (
            self.scope
            is V075BatchOccurrenceAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
        )
        if (
            type(self.scope) is not V075BatchOccurrenceAuthorityScopeV2
            or self._issuer
            is not (
                _PRODUCTION_LINEAGE_ISSUER
                if production
                else _CONSTRUCTION_LINEAGE_ISSUER
            )
            or type(self.occurrence_identity)
            is not backend.V075BatchNativeOccurrenceIdentityV1
            or type(self.closure)
            is not observer.V075ObserverBatchJournalClosureV2
            or type(self.closure_verification)
            is not observer.V075ObserverBatchClosureVerificationV2
            or type(self.public_verifications) is not tuple
            or any(
                type(item) is not V075BatchPublicVerificationV2
                for item in self.public_verifications
            )
            or type(self.sequence_verifications) is not tuple
            or any(
                type(item) is not V075BatchSequenceVerificationV2
                for item in self.sequence_verifications
            )
            or self.sequence_verifications
            != tuple(
                sorted(
                    self.sequence_verifications,
                    key=lambda item: item.stream_id,
                )
            )
        ):
            _fail("V2 batch occurrence lineage is caller-minted or untyped")
        for value, label in (
            (
                self.private_reveal_attestation_bytes_sha256,
                "V2 reveal bytes digest",
            ),
            (self.authorization_bytes_sha256, "V2 authorization bytes digest"),
            (self.namespace_bytes_sha256, "V2 namespace bytes digest"),
            (self.closure_bytes_sha256, "V2 batch closure bytes digest"),
        ):
            _cid(value, label)

        closure = self.closure
        identity = replayed_identity
        batches = tuple(entry.batch for entry in closure.entries)
        batch_ids = tuple(item.batch_id for item in batches)
        public_by_batch = {
            item.batch_id: item for item in self.public_verifications
        }
        if (
            len(public_by_batch) != len(self.public_verifications)
            or tuple(item.batch_id for item in self.public_verifications)
            != batch_ids
        ):
            _fail("V2 public verification registry does not match journal order")
        for batch in batches:
            if (
                public_by_batch.get(batch.batch_id)
                != verify_v075_signed_observation_batch_v2(batch)
            ):
                _fail("V2 batch public verification changed on replay")

        groups = _group_batches_by_stream(batches)
        sequence_by_stream = {
            item.stream_id: item for item in self.sequence_verifications
        }
        if (
            len(sequence_by_stream) != len(self.sequence_verifications)
            or set(sequence_by_stream) != set(groups)
        ):
            _fail("V2 stream sequence registry is incomplete")
        for stream_id, stream_batches in groups.items():
            if sequence_by_stream[stream_id] != (
                verify_v075_observation_batch_sequence_v2(stream_batches)
            ):
                _fail("V2 stream sequence verification changed on replay")

        binding = closure.authority_binding
        verification = self.closure_verification
        accepted_draw_count = sum(
            item.request.accepted_draw_count for item in batches
        )
        if (
            closure.occurrence_id != identity.occurrence_id
            or binding.namespace.target_tape_namespace_id
            != identity.target_tape_namespace_id
            or any(
                item.request.occurrence_id != identity.occurrence_id
                or item.request.stream_identity.target_tape_namespace_id
                != identity.target_tape_namespace_id
                or item.request.stream_identity.context_id
                != identity.context_id
                or item.request.stream_identity.arm != identity.arm.value
                for item in batches
            )
            or verification.closure_id != closure.closure_id
            or verification.occurrence_id != closure.occurrence_id
            or verification.batch_ids != batch_ids
            or verification.observer_open_binding_id != binding.binding_id
            or verification.observer_open_authorization_id
            != binding.authorization_id
            or verification.private_reveal_attestation_id
            != binding.private_reveal_attestation_id
            or verification.remote_main_anchor_id
            != binding.remote_main_anchor_id
            or verification.target_tape_namespace_id
            != identity.target_tape_namespace_id
            or verification.replayed_batch_count != len(batches)
            or verification.replayed_draw_count != accepted_draw_count
            or verification.replayed_stream_count != len(groups)
            or self.closure_bytes_sha256
            != hashlib.sha256(closure.canonical_bytes).hexdigest()
        ):
            _fail(
                "V2 closure, occurrence, batch, stream, or private replay "
                "identity was transplanted"
            )
        object.__setattr__(
            self,
            "_lineage_id",
            _hash("occurrence_lineage", self._payload()),
        )

    @property
    def batches(self) -> tuple[observer.V075SignedObservationBatchV2, ...]:
        return tuple(entry.batch for entry in self.closure.entries)

    @property
    def accepted_draw_count(self) -> int:
        return self.closure_verification.replayed_draw_count

    def _payload(self) -> dict[str, Any]:
        closure = self.closure
        return {
            "schema": "acfqp.v075_batch_occurrence_lineage.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "occurrence_identity": (
                self.occurrence_identity.to_document()
            ),
            "occurrence_id": self.occurrence_identity.occurrence_id,
            "target_tape_namespace_id": (
                self.occurrence_identity.target_tape_namespace_id
            ),
            "context_id": self.occurrence_identity.context_id,
            "arm": self.occurrence_identity.arm.value,
            "observer_session_public_id": closure.session_public_id,
            "observer_open_binding_id": closure.authority_binding.binding_id,
            "observer_open_authorization_id": (
                closure.authority_binding.authorization_id
            ),
            "private_reveal_attestation_id": (
                closure.authority_binding.private_reveal_attestation_id
            ),
            "remote_main_anchor_id": (
                closure.authority_binding.remote_main_anchor_id
            ),
            "closure_id": closure.closure_id,
            "closure_verification_id": (
                self.closure_verification.verification_id
            ),
            "journal_entry_ids": [
                item.entry_id for item in closure.entries
            ],
            "batch_ids": [item.batch.batch_id for item in closure.entries],
            "batch_public_verification_ids": [
                item.verification_id for item in self.public_verifications
            ],
            "batch_sequence_verification_ids": [
                item.verification_id for item in self.sequence_verifications
            ],
            "accepted_draw_count": self.accepted_draw_count,
            "batch_count": len(closure.entries),
            "stream_count": len(self.sequence_verifications),
            "rsa_batch_signature_count": len(closure.entries),
            "rsa_closure_signature_count": 1,
            "per_draw_record_count": 0,
            "per_draw_signature_count": 0,
            "private_reveal_attestation_bytes_sha256": (
                self.private_reveal_attestation_bytes_sha256
            ),
            "authorization_bytes_sha256": (
                self.authorization_bytes_sha256
            ),
            "namespace_bytes_sha256": self.namespace_bytes_sha256,
            "closure_bytes_sha256": self.closure_bytes_sha256,
            "production_authority_bytes_replayed": (
                self.scope
                is V075BatchOccurrenceAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
            ),
            "authority_version": "V2",
            "namespace_version": "V2",
            "legacy_v1_authority_projection_used": False,
            "legacy_v1_namespace_projection_used": False,
            "private_material_serialized": False,
            "official_execution_unlocked": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def lineage_id(self) -> str:
        return self._lineage_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "lineage_id": self.lineage_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _group_batches_by_stream(
    batches: tuple[observer.V075SignedObservationBatchV2, ...],
) -> dict[str, tuple[observer.V075SignedObservationBatchV2, ...]]:
    grouped: dict[str, list[observer.V075SignedObservationBatchV2]] = {}
    for batch in batches:
        grouped.setdefault(
            batch.request.stream_identity.stream_id,
            [],
        ).append(batch)
    return {key: tuple(values) for key, values in grouped.items()}


def _freeze_lineage(
    *,
    issuer: object,
    scope: V075BatchOccurrenceAuthorityScopeV2,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    closure: observer.V075ObserverBatchJournalClosureV2,
    closure_verification: observer.V075ObserverBatchClosureVerificationV2,
    private_reveal_attestation_bytes: bytes,
    authorization_bytes: bytes,
    namespace_bytes: bytes,
) -> V075BatchOccurrenceLineageV2:
    occurrence_identity = _replay_occurrence_identity(occurrence_identity)
    batches = tuple(entry.batch for entry in closure.entries)
    public_verifications = tuple(
        verify_v075_signed_observation_batch_v2(item) for item in batches
    )
    grouped = _group_batches_by_stream(batches)
    sequence_verifications = tuple(
        verify_v075_observation_batch_sequence_v2(grouped[stream_id])
        for stream_id in sorted(grouped)
    )
    return V075BatchOccurrenceLineageV2(
        issuer,
        scope,
        occurrence_identity,
        closure,
        closure_verification,
        public_verifications,
        sequence_verifications,
        _bytes_sha256(
            private_reveal_attestation_bytes,
            "private reveal attestation",
        ),
        _bytes_sha256(authorization_bytes, "observer authorization"),
        _bytes_sha256(namespace_bytes, "target namespace"),
        hashlib.sha256(closure.canonical_bytes).hexdigest(),
    )


def freeze_v075_construction_batch_occurrence_lineage_v2(
    *,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    closure: observer.V075ObserverBatchJournalClosureV2,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    known_stream_identities: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    private_salt: bytes,
    private_environment: Iterable[Any],
) -> V075BatchOccurrenceLineageV2:
    """Replay a synthetic exact-V2 graph without granting production scope."""

    if (
        type(occurrence_identity)
        is not backend.V075BatchNativeOccurrenceIdentityV1
        or type(closure)
        is not observer.V075ObserverBatchJournalClosureV2
        or type(authority) is not preopen.V075ObserverOpenAuthorizationV2
        or type(namespace)
        is not namespace_v2.V075PublicTargetTapeNamespaceV2
    ):
        _fail("construction V2 lineage inputs are untyped")
    occurrence_identity = _replay_occurrence_identity(occurrence_identity)
    binding = closure.authority_binding
    if (
        type(binding) is not observer.V075ObserverOpenAuthorityBindingV2
        or binding.namespace != namespace
    ):
        _fail("construction V2 closure carries a foreign authority binding")
    replayed_closure = (
        observer.load_observer_batch_journal_closure_bytes_v2(
            raw=closure.canonical_bytes,
            authority_binding=binding,
            known_stream_identities=known_stream_identities,
        )
    )
    verification = observer.verify_loaded_private_observer_batch_closure_v2(
        closure=replayed_closure,
        authority=authority,
        namespace=namespace,
        authority_binding=binding,
        private_salt=private_salt,
        private_environment=private_environment,
    )
    return _freeze_lineage(
        issuer=_CONSTRUCTION_LINEAGE_ISSUER,
        scope=V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY,
        occurrence_identity=occurrence_identity,
        closure=replayed_closure,
        closure_verification=verification,
        private_reveal_attestation_bytes=(
            authority.private_reveal_attestation.canonical_bytes
        ),
        authorization_bytes=authority.canonical_bytes,
        namespace_bytes=namespace.canonical_bytes,
    )


_PRODUCTION_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionBatchOccurrenceLineageVerificationV2:
    """Independent production byte-gate replay of one claimed lineage."""

    _issuer: object = field(repr=False, compare=False)
    lineage_id: str
    occurrence_id: str
    closure_id: str
    closure_verification_id: str
    private_reveal_attestation_bytes_sha256: str
    authorization_bytes_sha256: str
    namespace_bytes_sha256: str
    closure_bytes_sha256: str
    batch_count: int
    accepted_draw_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.lineage_id, "production V2 occurrence lineage"),
            (self.occurrence_id, "production V2 occurrence"),
            (self.closure_id, "production V2 batch closure"),
            (
                self.closure_verification_id,
                "production V2 closure verification",
            ),
            (
                self.private_reveal_attestation_bytes_sha256,
                "production V2 reveal bytes",
            ),
            (
                self.authorization_bytes_sha256,
                "production V2 authorization bytes",
            ),
            (self.namespace_bytes_sha256, "production V2 namespace bytes"),
            (self.closure_bytes_sha256, "production V2 closure bytes"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _PRODUCTION_VERIFICATION_ISSUER
            or type(self.batch_count) is not int
            or self.batch_count <= 0
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count <= 0
        ):
            _fail("production V2 lineage verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("production_lineage_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_batch_occurrence_"
                "lineage_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "lineage_id": self.lineage_id,
            "occurrence_id": self.occurrence_id,
            "closure_id": self.closure_id,
            "closure_verification_id": self.closure_verification_id,
            "private_reveal_attestation_bytes_sha256": (
                self.private_reveal_attestation_bytes_sha256
            ),
            "authorization_bytes_sha256": (
                self.authorization_bytes_sha256
            ),
            "namespace_bytes_sha256": self.namespace_bytes_sha256,
            "closure_bytes_sha256": self.closure_bytes_sha256,
            "batch_count": self.batch_count,
            "accepted_draw_count": self.accepted_draw_count,
            "verification_result": (
                "EXACT_V2_PRODUCTION_BATCH_LINEAGE_REPLAY_VERIFIED"
            ),
            "production_authority_bytes_replayed": True,
            "closure_bytes_replayed": True,
            "batch_public_signatures_replayed": True,
            "stream_sequences_replayed": True,
            "private_batch_aggregates_replayed": True,
            "legacy_v1_projection_used": False,
            "private_material_serialized": False,
            "official_execution_unlocked": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def freeze_v075_production_batch_occurrence_lineage_v2(
    *,
    repository_root: str | Path,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    batch_closure_bytes: bytes,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    known_stream_identities: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    private_salt: bytes,
    private_environment: Iterable[Any],
) -> tuple[
    V075BatchOccurrenceLineageV2,
    V075ProductionBatchOccurrenceLineageVerificationV2,
]:
    """Freeze only after exact production authority and private batch replay."""

    if (
        type(occurrence_identity)
        is not backend.V075BatchNativeOccurrenceIdentityV1
        or type(batch_closure_bytes) is not bytes
        or not batch_closure_bytes
    ):
        _fail(
            "production V2 lineage requires exact occurrence and nonempty "
            "canonical closure bytes"
        )
    occurrence_identity = _replay_occurrence_identity(occurrence_identity)
    replayed_closure, verification = (
        observer.replay_and_verify_private_observer_batch_journal_closure_v2(
            repository_root=repository_root,
            private_reveal_attestation_bytes=(
                private_reveal_attestation_bytes
            ),
            claimed_authorization_bytes=claimed_authorization_bytes,
            namespace_bytes=namespace_bytes,
            batch_closure_bytes=batch_closure_bytes,
            known_stream_identities=known_stream_identities,
            private_salt=private_salt,
            private_environment=private_environment,
        )
    )
    lineage = _freeze_lineage(
        issuer=_PRODUCTION_LINEAGE_ISSUER,
        scope=V075BatchOccurrenceAuthorityScopeV2.PRODUCTION_BYTE_REPLAY,
        occurrence_identity=occurrence_identity,
        closure=replayed_closure,
        closure_verification=verification,
        private_reveal_attestation_bytes=private_reveal_attestation_bytes,
        authorization_bytes=claimed_authorization_bytes,
        namespace_bytes=namespace_bytes,
    )
    attestation = V075ProductionBatchOccurrenceLineageVerificationV2(
        _PRODUCTION_VERIFICATION_ISSUER,
        lineage.lineage_id,
        occurrence_identity.occurrence_id,
        replayed_closure.closure_id,
        verification.verification_id,
        lineage.private_reveal_attestation_bytes_sha256,
        lineage.authorization_bytes_sha256,
        lineage.namespace_bytes_sha256,
        lineage.closure_bytes_sha256,
        len(replayed_closure.entries),
        lineage.accepted_draw_count,
    )
    return lineage, attestation


def verify_v075_production_batch_occurrence_lineage_v2(
    *,
    claimed_lineage: V075BatchOccurrenceLineageV2,
    claimed_verification: (
        V075ProductionBatchOccurrenceLineageVerificationV2
    ),
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    batch_closure_bytes: bytes,
    known_stream_identities: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    private_salt: bytes,
    private_environment: Iterable[Any],
) -> tuple[
    V075BatchOccurrenceLineageV2,
    V075ProductionBatchOccurrenceLineageVerificationV2,
]:
    """Independently recreate the production lineage and byte-compare IDs."""

    if (
        type(claimed_lineage) is not V075BatchOccurrenceLineageV2
        or claimed_lineage.scope
        is not V075BatchOccurrenceAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
        or type(claimed_verification)
        is not V075ProductionBatchOccurrenceLineageVerificationV2
    ):
        _fail("production V2 lineage verifier rejects construction or ducks")
    replayed, verification = (
        freeze_v075_production_batch_occurrence_lineage_v2(
            repository_root=repository_root,
            occurrence_identity=claimed_lineage.occurrence_identity,
            batch_closure_bytes=batch_closure_bytes,
            private_reveal_attestation_bytes=(
                private_reveal_attestation_bytes
            ),
            claimed_authorization_bytes=claimed_authorization_bytes,
            namespace_bytes=namespace_bytes,
            known_stream_identities=known_stream_identities,
            private_salt=private_salt,
            private_environment=private_environment,
        )
    )
    if (
        replayed != claimed_lineage
        or replayed.canonical_bytes != claimed_lineage.canonical_bytes
        or verification != claimed_verification
    ):
        _fail("claimed production V2 batch lineage differs from replay")
    return replayed, verification


__all__ = [
    "DOMAIN_TAGS",
    "OFFICIAL_EXECUTION_UNLOCKED",
    "PER_DRAW_RECORDS_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "V1_AUTHORITY_PROJECTION_ALLOWED",
    "V1_NAMESPACE_PROJECTION_ALLOWED",
    "V075BatchOccurrenceAuthorityScopeV2",
    "V075BatchOccurrenceLineageV2",
    "V075BatchPublicVerificationV2",
    "V075BatchSequenceVerificationV2",
    "V075BatchedObserverV2InvariantViolation",
    "V075OccurrenceBatchedObserverSessionV2",
    "V075ProductionBatchOccurrenceLineageVerificationV2",
    "bind_v075_construction_occurrence_batched_observer_v2",
    "freeze_v075_construction_batch_occurrence_lineage_v2",
    "freeze_v075_production_batch_occurrence_lineage_v2",
    "open_v075_production_occurrence_batched_observer_v2",
    "verify_v075_observation_batch_sequence_v2",
    "verify_v075_production_batch_occurrence_lineage_v2",
    "verify_v075_signed_observation_batch_v2",
]
