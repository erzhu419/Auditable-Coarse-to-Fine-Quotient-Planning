"""Parent-owned multi-stage batched-observer lifecycle for V0-075.

The older IPC fixture freezes one lane and closes after one scripted pass.
That cannot represent the production ordering required by a statistical H=2
backend:

    DISCOVERY batches
    -> signed aggregate-support freeze
    -> VALIDATION batches
    -> optional adaptive discovery/freeze/validation rounds
    -> one signed occurrence closure.

This module owns that chronology.  It wraps exactly one private batched
observer session, records every batch and support freeze in an append-only
hash chain, closes the otherwise-empty per-draw observer journal, and issues
one observer-signed aggregate closure.  It never expands a batch into
per-draw capabilities and never serializes a law, salt, kernel, random word,
or accepted-draw index.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_parent_owned_multistage_observer_lifecycle_v1"
PRODUCTION_INTEGRATION_READY = False
PER_DRAW_CAPABILITY_EXPANSION_ALLOWED = False
MAX_ADAPTIVE_ROUNDS = 2
MAX_BATCH_EVENTS = 65_536

_SIGNING_DOMAIN = (
    b"acfqp:v075-multistage-observer-occurrence-closure-signing:v1"
)
_INITIAL_EVENT_ID = hashlib.sha256(
    b"acfqp:v075-multistage-observer-lifecycle-initial:v1"
).hexdigest()

DOMAIN_TAGS = {
    "open_binding": (
        "acfqp:v075-multistage-observer-lifecycle-open-binding:v1"
    ),
    "event": "acfqp:v075-multistage-observer-lifecycle-event:v1",
    "transcript": "acfqp:v075-multistage-observer-lifecycle-transcript:v1",
    "closure": "acfqp:v075-multistage-observer-occurrence-closure:v1",
    "verification": (
        "acfqp:v075-multistage-observer-occurrence-closure-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 multistage lifecycle domains must be unique")


class V075MultistageObserverLifecycleInvariantViolation(ValueError):
    """A phase, support, batch, cap, signature, or closure invariant failed."""


def _fail(message: str) -> None:
    raise V075MultistageObserverLifecycleInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075MultistageObserverLifecycleInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075MultistageObserverLifecycleInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        _fail(f"{field_name} must be canonical nonempty text")
    return value


class V075LifecycleAuthorityScopeV1(str, Enum):
    CONSTRUCTION_ONLY = "CONSTRUCTION_ONLY"
    PRODUCTION = "PRODUCTION"


class V075LifecycleEventKindV1(str, Enum):
    DISCOVERY_BATCH = "DISCOVERY_BATCH"
    SUPPORT_FREEZE = "SUPPORT_FREEZE"
    VALIDATION_BATCH = "VALIDATION_BATCH"
    ADAPTIVE_DISCOVERY_BATCH = "ADAPTIVE_DISCOVERY_BATCH"
    ADAPTIVE_SUPPORT_FREEZE = "ADAPTIVE_SUPPORT_FREEZE"
    ADAPTIVE_VALIDATION_BATCH = "ADAPTIVE_VALIDATION_BATCH"


class V075LifecycleTerminalCodeV1(str, Enum):
    COMPLETE_REGISTERED_CHECKPOINT_CLOSED = (
        "COMPLETE_REGISTERED_CHECKPOINT_CLOSED"
    )
    NONCERTIFICATE_PROTOCOL_CLOSED = "NONCERTIFICATE_PROTOCOL_CLOSED"
    NONCERTIFICATE_CAP_CLOSED = "NONCERTIFICATE_CAP_CLOSED"


@dataclass(frozen=True, slots=True)
class V075OpenMultistageLifecycleBindingV1:
    """Public pre-draw identity of one parent-owned open lifecycle."""

    occurrence_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    route_cap_profile: worker.V075WorkerCapProfileV1
    namespace: public_authority.V075PublicTargetTapeNamespaceV1
    session_public_id: str
    observer_open_binding: observer.V075ObserverOpenAuthorityBindingV1
    authority_scope: V075LifecycleAuthorityScopeV1

    def __post_init__(self) -> None:
        for value, name in (
            (self.occurrence_id, "open lifecycle occurrence"),
            (self.context_id, "open lifecycle context"),
            (self.session_public_id, "open lifecycle session"),
        ):
            _cid(value, name)
        if (
            type(self.arm) is not worker.V075WorkerArmV1
            or type(self.route_cap_profile)
            is not worker.V075WorkerCapProfileV1
            or type(self.namespace)
            is not public_authority.V075PublicTargetTapeNamespaceV1
            or type(self.observer_open_binding)
            is not observer.V075ObserverOpenAuthorityBindingV1
            or self.observer_open_binding.namespace != self.namespace
            or type(self.authority_scope)
            is not V075LifecycleAuthorityScopeV1
            or self.context_id
            not in {
                item.context_id
                for item in self.namespace.family.replicate_contexts
            }
        ):
            _fail("open lifecycle public binding is malformed or transplanted")

    @property
    def route_cap_profile_id(self) -> str:
        return self.route_cap_profile.cap_profile_id

    @property
    def target_tape_namespace_id(self) -> str:
        return self.namespace.target_tape_namespace_id

    @property
    def observer_open_binding_id(self) -> str:
        return self.observer_open_binding.binding_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_multistage_observer_lifecycle_open_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "route_cap_profile_id": self.route_cap_profile_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "session_public_id": self.session_public_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "authority_scope": self.authority_scope.value,
            "frozen_before_observation": True,
            "private_material_serialized": False,
        }

    @property
    def binding_id(self) -> str:
        return _hash("open_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "namespace": self.namespace.to_document(),
            "observer_open_binding": self.observer_open_binding.to_document(),
            "route_cap_profile": self.route_cap_profile.to_document(),
            "binding_id": self.binding_id,
        }


def _scope_from_session(
    value: batched.V075PrivateBatchedObserverSessionV1,
) -> V075LifecycleAuthorityScopeV1:
    if (
        value.authority_scope
        is batched.V075BatchAuthorityScopeV1.CONSTRUCTION_ONLY
    ):
        return V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
    if (
        value.authority_scope
        is batched.V075BatchAuthorityScopeV1.PRODUCTION_OPEN
    ):
        return V075LifecycleAuthorityScopeV1.PRODUCTION
    _fail("batched observer session has an unknown authority scope")
    raise AssertionError("unreachable")


_EVENT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075MultistageLifecycleEventV1:
    _issuer: object = field(repr=False, compare=False)
    sequence_number: int
    previous_event_id: str
    kind: V075LifecycleEventKindV1
    adaptive_round_index: int
    batch_id: str | None
    request_id: str | None
    stream_id: str | None
    row_binding_id: str
    support_epoch_id: str | None
    aggregate_support_evidence_ids: tuple[str, ...]
    source_discovery_batch_ids: tuple[str, ...]
    accepted_draw_count: int
    _event_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.previous_event_id, "previous lifecycle event")
        _cid(self.row_binding_id, "lifecycle event row")
        if self.support_epoch_id is not None:
            _cid(self.support_epoch_id, "lifecycle support epoch")
        for value in (
            *self.aggregate_support_evidence_ids,
            *self.source_discovery_batch_ids,
        ):
            _cid(value, "lifecycle evidence/source batch")
        batch_kind = self.kind in {
            V075LifecycleEventKindV1.DISCOVERY_BATCH,
            V075LifecycleEventKindV1.VALIDATION_BATCH,
            V075LifecycleEventKindV1.ADAPTIVE_DISCOVERY_BATCH,
            V075LifecycleEventKindV1.ADAPTIVE_VALIDATION_BATCH,
        }
        freeze_kind = self.kind in {
            V075LifecycleEventKindV1.SUPPORT_FREEZE,
            V075LifecycleEventKindV1.ADAPTIVE_SUPPORT_FREEZE,
        }
        if (
            self._issuer is not _EVENT_ISSUER
            or type(self.sequence_number) is not int
            or not 1 <= self.sequence_number <= MAX_BATCH_EVENTS * 2
            or type(self.kind) is not V075LifecycleEventKindV1
            or type(self.adaptive_round_index) is not int
            or self.adaptive_round_index not in range(MAX_ADAPTIVE_ROUNDS + 1)
            or type(self.aggregate_support_evidence_ids) is not tuple
            or self.aggregate_support_evidence_ids
            != tuple(sorted(set(self.aggregate_support_evidence_ids)))
            or type(self.source_discovery_batch_ids) is not tuple
            or self.source_discovery_batch_ids
            != tuple(sorted(set(self.source_discovery_batch_ids)))
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count < 0
        ):
            _fail("multistage lifecycle event is malformed")
        if batch_kind:
            for value, name in (
                (self.batch_id, "lifecycle batch"),
                (self.request_id, "lifecycle request"),
                (self.stream_id, "lifecycle stream"),
            ):
                _cid(value, name)
            if (
                self.accepted_draw_count <= 0
                or self.source_discovery_batch_ids
                or (
                    self.kind
                    in {
                        V075LifecycleEventKindV1.DISCOVERY_BATCH,
                        V075LifecycleEventKindV1.ADAPTIVE_DISCOVERY_BATCH,
                    }
                    and (
                        self.support_epoch_id is not None
                        or self.aggregate_support_evidence_ids
                    )
                )
                or (
                    self.kind
                    in {
                        V075LifecycleEventKindV1.VALIDATION_BATCH,
                        V075LifecycleEventKindV1.ADAPTIVE_VALIDATION_BATCH,
                    }
                    and (
                        self.support_epoch_id is None
                        or not self.aggregate_support_evidence_ids
                    )
                )
            ):
                _fail("batch lifecycle event has invalid support/draw fields")
        elif freeze_kind:
            if (
                self.batch_id is not None
                or self.request_id is not None
                or self.stream_id is not None
                or self.support_epoch_id is None
                or not self.aggregate_support_evidence_ids
                or not self.source_discovery_batch_ids
                or self.accepted_draw_count != 0
            ):
                _fail("support-freeze lifecycle event is malformed")
        else:  # pragma: no cover - exhaustive enum
            _fail("unknown lifecycle event kind")
        if (
            self.adaptive_round_index == 0
        ) != (
            self.kind
            in {
                V075LifecycleEventKindV1.DISCOVERY_BATCH,
                V075LifecycleEventKindV1.SUPPORT_FREEZE,
                V075LifecycleEventKindV1.VALIDATION_BATCH,
            }
        ):
            _fail("initial/adaptive lifecycle event round is inconsistent")
        object.__setattr__(
            self,
            "_event_id",
            _hash("event", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_multistage_observer_lifecycle_event.v1",
            "schema_version": SCHEMA_VERSION,
            "sequence_number": self.sequence_number,
            "previous_event_id": self.previous_event_id,
            "kind": self.kind.value,
            "adaptive_round_index": self.adaptive_round_index,
            "batch_id": self.batch_id,
            "request_id": self.request_id,
            "stream_id": self.stream_id,
            "row_binding_id": self.row_binding_id,
            "support_epoch_id": self.support_epoch_id,
            "aggregate_support_evidence_ids": list(
                self.aggregate_support_evidence_ids
            ),
            "source_discovery_batch_ids": list(
                self.source_discovery_batch_ids
            ),
            "accepted_draw_count": self.accepted_draw_count,
            "per_draw_capability_count": 0,
        }

    @property
    def event_id(self) -> str:
        return self._event_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "event_id": self.event_id}


_CLOSURE_ISSUER = object()


def _closure_payload(
    *,
    scope: V075LifecycleAuthorityScopeV1,
    occurrence_id: str,
    context_id: str,
    arm: str,
    target_tape_namespace_id: str,
    session_public_id: str,
    observer_open_binding_id: str,
    route_cap_profile_id: str,
    event_ids: tuple[str, ...],
    lifecycle_transcript_id: str,
    batch_ids: tuple[str, ...],
    request_ids: tuple[str, ...],
    stream_ids: tuple[str, ...],
    sequence_verification_ids: tuple[str, ...],
    public_verification_ids: tuple[str, ...],
    private_replay_verification_ids: tuple[str, ...],
    aggregate_support_evidence_ids: tuple[str, ...],
    accepted_draw_count: int,
    accepted_draw_cap: int,
    process_launches: int,
    child_intent_count: int,
    underlying_session_closure_id: str,
    underlying_closure_verification_id: str,
    terminal_code: V075LifecycleTerminalCodeV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_multistage_observer_occurrence_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "authority_scope": scope.value,
        "occurrence_id": occurrence_id,
        "context_id": context_id,
        "arm": arm,
        "target_tape_namespace_id": target_tape_namespace_id,
        "observer_session_public_id": session_public_id,
        "observer_open_binding_id": observer_open_binding_id,
        "route_cap_profile_id": route_cap_profile_id,
        "event_ids": list(event_ids),
        "event_count": len(event_ids),
        "lifecycle_transcript_id": lifecycle_transcript_id,
        "batch_ids_in_emission_order": list(batch_ids),
        "request_ids_in_emission_order": list(request_ids),
        "stream_ids": list(stream_ids),
        "sequence_verification_ids": list(sequence_verification_ids),
        "public_verification_ids": list(public_verification_ids),
        "private_replay_verification_ids": list(
            private_replay_verification_ids
        ),
        "aggregate_support_evidence_ids": list(
            aggregate_support_evidence_ids
        ),
        "accepted_draw_count": accepted_draw_count,
        "accepted_draw_cap": accepted_draw_cap,
        "process_launches": process_launches,
        "child_intent_count": child_intent_count,
        "per_draw_capability_count": 0,
        "underlying_session_closure_id": underlying_session_closure_id,
        "underlying_closure_verification_id": (
            underlying_closure_verification_id
        ),
        "underlying_per_draw_entry_count": 0,
        "terminal_code": terminal_code.value,
        "complete_registered_checkpoint_claimed": (
            terminal_code
            is V075LifecycleTerminalCodeV1
            .COMPLETE_REGISTERED_CHECKPOINT_CLOSED
        ),
        "private_law_serialized": False,
        "private_salt_serialized": False,
        "private_kernel_serialized": False,
        "random_words_serialized": False,
        "accepted_draw_indices_serialized": False,
    }


def multistage_occurrence_closure_signing_bytes_v1(
    **values: Any,
) -> bytes:
    return (
        _SIGNING_DOMAIN
        + b"\x00"
        + canonical_json_bytes(_closure_payload(**values))
    )


@dataclass(frozen=True, slots=True)
class V075SignedMultistageOccurrenceClosureV1:
    _issuer: object = field(repr=False, compare=False)
    scope: V075LifecycleAuthorityScopeV1
    occurrence_id: str
    context_id: str
    arm: str
    target_tape_namespace_id: str
    session_public_id: str
    observer_open_binding_id: str
    route_cap_profile_id: str
    events: tuple[V075MultistageLifecycleEventV1, ...]
    lifecycle_transcript_id: str
    batch_ids: tuple[str, ...]
    request_ids: tuple[str, ...]
    stream_ids: tuple[str, ...]
    sequence_verification_ids: tuple[str, ...]
    public_verification_ids: tuple[str, ...]
    private_replay_verification_ids: tuple[str, ...]
    aggregate_support_evidence_ids: tuple[str, ...]
    accepted_draw_count: int
    accepted_draw_cap: int
    process_launches: int
    child_intent_count: int
    underlying_session_closure_id: str
    underlying_closure_verification_id: str
    terminal_code: V075LifecycleTerminalCodeV1
    observer_signature_hex: str
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.occurrence_id, "multistage occurrence"),
            (self.context_id, "multistage context"),
            (self.target_tape_namespace_id, "multistage namespace"),
            (self.session_public_id, "multistage session"),
            (self.observer_open_binding_id, "multistage observer binding"),
            (self.route_cap_profile_id, "multistage route cap"),
            (self.lifecycle_transcript_id, "multistage transcript"),
            (
                self.underlying_session_closure_id,
                "underlying observer closure",
            ),
            (
                self.underlying_closure_verification_id,
                "underlying observer closure verification",
            ),
        ):
            _cid(value, name)
        _token(self.arm, "multistage arm")
        for values in (
            self.batch_ids,
            self.request_ids,
            self.stream_ids,
            self.sequence_verification_ids,
            self.public_verification_ids,
            self.private_replay_verification_ids,
            self.aggregate_support_evidence_ids,
        ):
            for value in values:
                _cid(value, "multistage registry entry")
        if (
            self._issuer is not _CLOSURE_ISSUER
            or type(self.scope) is not V075LifecycleAuthorityScopeV1
            or type(self.events) is not tuple
            or not self.events
            or any(
                type(item) is not V075MultistageLifecycleEventV1
                for item in self.events
            )
            or tuple(item.sequence_number for item in self.events)
            != tuple(range(1, len(self.events) + 1))
            or tuple(item.previous_event_id for item in self.events)
            != (
                _INITIAL_EVENT_ID,
                *(item.event_id for item in self.events[:-1]),
            )
            or self.lifecycle_transcript_id
            != _hash(
                "transcript",
                {
                    "schema": (
                        "acfqp.v075_multistage_observer_lifecycle_transcript.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "event_ids": [item.event_id for item in self.events],
                },
            )
            or type(self.batch_ids) is not tuple
            or not self.batch_ids
            or len(set(self.batch_ids)) != len(self.batch_ids)
            or type(self.request_ids) is not tuple
            or len(self.request_ids) != len(self.batch_ids)
            or len(set(self.request_ids)) != len(self.request_ids)
            or self.stream_ids != tuple(sorted(set(self.stream_ids)))
            or self.sequence_verification_ids
            != tuple(sorted(set(self.sequence_verification_ids)))
            or self.public_verification_ids
            != tuple(sorted(set(self.public_verification_ids)))
            or self.private_replay_verification_ids
            != tuple(sorted(set(self.private_replay_verification_ids)))
            or self.aggregate_support_evidence_ids
            != tuple(sorted(set(self.aggregate_support_evidence_ids)))
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count <= 0
            or type(self.accepted_draw_cap) is not int
            or self.accepted_draw_count > self.accepted_draw_cap
            or type(self.process_launches) is not int
            or self.process_launches < 0
            or type(self.child_intent_count) is not int
            or self.child_intent_count < 0
            or type(self.terminal_code) is not V075LifecycleTerminalCodeV1
        ):
            _fail("signed multistage occurrence closure is malformed")
        values = self._signing_values()
        message = multistage_occurrence_closure_signing_bytes_v1(**values)
        first_binding = getattr(self, "_observer_binding_for_validation", None)
        if first_binding is not None:  # pragma: no cover - slots forbid this
            _fail("closure carried an unregistered private binding")
        object.__setattr__(
            self,
            "_closure_id",
            _hash(
                "closure",
                {
                    **_closure_payload(**values),
                    "observer_signature_hex": self.observer_signature_hex,
                    "observer_signature_verified": True,
                },
            ),
        )
        # Signature verification is completed by the issuer and repeated by
        # the independent verifier, which receives the exact public binding.
        if type(message) is not bytes or not message:
            _fail("multistage closure signing payload is invalid")

    def _signing_values(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "session_public_id": self.session_public_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "route_cap_profile_id": self.route_cap_profile_id,
            "event_ids": tuple(item.event_id for item in self.events),
            "lifecycle_transcript_id": self.lifecycle_transcript_id,
            "batch_ids": self.batch_ids,
            "request_ids": self.request_ids,
            "stream_ids": self.stream_ids,
            "sequence_verification_ids": self.sequence_verification_ids,
            "public_verification_ids": self.public_verification_ids,
            "private_replay_verification_ids": (
                self.private_replay_verification_ids
            ),
            "aggregate_support_evidence_ids": (
                self.aggregate_support_evidence_ids
            ),
            "accepted_draw_count": self.accepted_draw_count,
            "accepted_draw_cap": self.accepted_draw_cap,
            "process_launches": self.process_launches,
            "child_intent_count": self.child_intent_count,
            "underlying_session_closure_id": (
                self.underlying_session_closure_id
            ),
            "underlying_closure_verification_id": (
                self.underlying_closure_verification_id
            ),
            "terminal_code": self.terminal_code,
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {
            **_closure_payload(**self._signing_values()),
            "events": [item.to_document() for item in self.events],
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "closure_id": self.closure_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075MultistageOccurrenceClosureVerificationV1:
    _issuer: object = field(repr=False, compare=False)
    closure_id: str
    lifecycle_transcript_id: str
    observer_open_binding_id: str
    batch_count: int
    accepted_draw_count: int
    aggregate_support_evidence_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.closure_id, "verified multistage closure"),
            (self.lifecycle_transcript_id, "verified lifecycle transcript"),
            (
                self.observer_open_binding_id,
                "verified lifecycle observer binding",
            ),
        ):
            _cid(value, name)
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.batch_count) is not int
            or self.batch_count <= 0
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count <= 0
            or type(self.aggregate_support_evidence_count) is not int
            or self.aggregate_support_evidence_count <= 0
        ):
            _fail("multistage closure verification was caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_multistage_observer_occurrence_"
                "closure_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "closure_id": self.closure_id,
            "lifecycle_transcript_id": self.lifecycle_transcript_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "batch_count": self.batch_count,
            "accepted_draw_count": self.accepted_draw_count,
            "aggregate_support_evidence_count": (
                self.aggregate_support_evidence_count
            ),
            "event_hash_chain_replayed": True,
            "phase_causality_replayed": True,
            "support_freeze_precedes_validation": True,
            "batch_registries_replayed": True,
            "public_verifications_replayed": True,
            "sequence_verifications_replayed": True,
            "private_replay_attestations_bound": True,
            "underlying_empty_observer_closure_bound": True,
            "cap_replayed": True,
            "observer_signature_replayed": True,
            "per_draw_capability_count": 0,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


@dataclass(frozen=True, slots=True)
class V075SealedMultistageOccurrenceLifecycleV1:
    closure: V075SignedMultistageOccurrenceClosureV1
    verification: V075MultistageOccurrenceClosureVerificationV1
    batches: tuple[batched.V075SignedBatchedObservationV1, ...]
    public_verifications: tuple[
        batched.V075BatchedObservationPublicVerificationV1, ...
    ]
    sequence_verifications: tuple[
        batched.V075BatchedObservationSequenceVerificationV1, ...
    ]
    private_replay_verifications: tuple[
        batched.V075BatchedObservationPrivateReplayVerificationV1, ...
    ]
    aggregate_support_evidence: tuple[
        graph.V075BatchAggregateSupportEvidenceV1, ...
    ]
    underlying_closure: observer.V075ObserverJournalClosureV1
    underlying_closure_verification: (
        observer.V075ObserverClosureVerificationV1
    )

    def __post_init__(self) -> None:
        if (
            type(self.closure) is not V075SignedMultistageOccurrenceClosureV1
            or type(self.verification)
            is not V075MultistageOccurrenceClosureVerificationV1
            or self.verification.closure_id != self.closure.closure_id
        ):
            _fail("sealed multistage lifecycle is not verifier-issued")


class V075ParentOwnedMultistageObserverLifecycleV1:
    """Mutable parent-only controller; only its sealed output is portable."""

    __slots__ = (
        "_adaptive_round_index",
        "_arm",
        "_batched_session",
        "_batches",
        "_closed",
        "_context_id",
        "_events",
        "_frozen_evidence",
        "_open_binding",
        "_occurrence_id",
        "_phase",
        "_registered_support_epoch_ids",
        "_route_cap_profile",
    )

    def __init__(
        self,
        *,
        batched_session: batched.V075PrivateBatchedObserverSessionV1,
        occurrence_id: str,
        context_id: str,
        arm: worker.V075WorkerArmV1,
        route_cap_profile: worker.V075WorkerCapProfileV1,
    ) -> None:
        if (
            type(batched_session)
            is not batched.V075PrivateBatchedObserverSessionV1
            or type(arm) is not worker.V075WorkerArmV1
            or type(route_cap_profile) is not worker.V075WorkerCapProfileV1
            or batched_session.batches
        ):
            _fail("multistage lifecycle requires one fresh exact batch session")
        self._occurrence_id = _cid(occurrence_id, "lifecycle occurrence")
        self._context_id = _cid(context_id, "lifecycle context")
        self._arm = arm
        self._route_cap_profile = route_cap_profile
        self._batched_session = batched_session
        underlying_session = getattr(batched_session, "_session", None)
        if type(underlying_session) is not observer.V075PrivateObserverSessionV1:
            _fail("multistage lifecycle lacks its exact observer session")
        self._open_binding = V075OpenMultistageLifecycleBindingV1(
            self._occurrence_id,
            self._context_id,
            self._arm,
            self._route_cap_profile,
            underlying_session.authority_binding.namespace,
            batched_session.session_public_id,
            underlying_session.authority_binding,
            _scope_from_session(batched_session),
        )
        self._batches: list[batched.V075SignedBatchedObservationV1] = []
        self._events: list[V075MultistageLifecycleEventV1] = []
        self._frozen_evidence: dict[
            str,
            tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
        ] = {}
        self._registered_support_epoch_ids: set[str] = set()
        self._adaptive_round_index = 0
        self._phase = "DISCOVERY"
        self._closed = False

    @property
    def batches(self) -> tuple[batched.V075SignedBatchedObservationV1, ...]:
        return tuple(self._batches)

    @property
    def open_binding(self) -> V075OpenMultistageLifecycleBindingV1:
        return self._open_binding

    @property
    def events(self) -> tuple[V075MultistageLifecycleEventV1, ...]:
        return tuple(self._events)

    @property
    def aggregate_support_evidence(
        self,
    ) -> tuple[graph.V075BatchAggregateSupportEvidenceV1, ...]:
        return tuple(
            sorted(
                (
                    item
                    for values in self._frozen_evidence.values()
                    for item in values
                ),
                key=lambda item: item.evidence_id,
            )
        )

    def _append_event(
        self,
        *,
        kind: V075LifecycleEventKindV1,
        row_binding_id: str,
        batch_id: str | None = None,
        request_id: str | None = None,
        stream_id: str | None = None,
        support_epoch_id: str | None = None,
        evidence_ids: tuple[str, ...] = (),
        source_batch_ids: tuple[str, ...] = (),
        accepted_draw_count: int = 0,
    ) -> None:
        prior = (
            _INITIAL_EVENT_ID
            if not self._events
            else self._events[-1].event_id
        )
        self._events.append(
            V075MultistageLifecycleEventV1(
                _EVENT_ISSUER,
                len(self._events) + 1,
                prior,
                kind,
                self._adaptive_round_index,
                batch_id,
                request_id,
                stream_id,
                row_binding_id,
                support_epoch_id,
                tuple(sorted(evidence_ids)),
                tuple(sorted(source_batch_ids)),
                accepted_draw_count,
            )
        )

    def execute_batch_v1(
        self,
        *,
        stream_identity: graph.V075TransitionStreamIdentityV1,
        accepted_draw_start: int,
        accepted_draw_count: int,
        accepted_draw_cap: int,
    ) -> batched.V075SignedBatchedObservationV1:
        if (
            self._closed
            or type(stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or stream_identity.context_id != self._context_id
            or stream_identity.arm != self._arm.value
        ):
            _fail("lifecycle batch is closed, foreign, or arm-transplanted")
        lane = stream_identity.lane
        if lane is graph.V075ObservationLaneV1.DISCOVERY:
            if self._phase != "DISCOVERY":
                _fail("DISCOVERY batch occurred after support/validation")
            kind = (
                V075LifecycleEventKindV1.DISCOVERY_BATCH
                if self._adaptive_round_index == 0
                else V075LifecycleEventKindV1.ADAPTIVE_DISCOVERY_BATCH
            )
            evidence_ids: tuple[str, ...] = ()
            support_epoch_id = None
        elif lane is graph.V075ObservationLaneV1.VALIDATION:
            support_epoch = (
                stream_identity.pairing_authority.support_chain.leaf
            )
            evidence = tuple(
                item
                for item in support_epoch.evidence
                if type(item)
                is graph.V075BatchAggregateSupportEvidenceV1
            )
            evidence_ids = tuple(item.evidence_id for item in evidence)
            support_epoch_id = support_epoch.epoch_id
            if (
                not evidence
                or support_epoch_id not in self._registered_support_epoch_ids
            ):
                _fail(
                    "VALIDATION batch lacks a prior lifecycle support freeze"
                )
            self._phase = "VALIDATION"
            kind = (
                V075LifecycleEventKindV1.VALIDATION_BATCH
                if self._adaptive_round_index == 0
                else V075LifecycleEventKindV1.ADAPTIVE_VALIDATION_BATCH
            )
        else:  # pragma: no cover - exhaustive enum
            _fail("unknown observer lane")
        request = self._batched_session.issue_request_v1(
            stream_identity=stream_identity,
            accepted_draw_start=accepted_draw_start,
            accepted_draw_count=accepted_draw_count,
            accepted_draw_cap=accepted_draw_cap,
        )
        result = self._batched_session.execute_request_v1(request)
        self._batches.append(result)
        self._append_event(
            kind=kind,
            row_binding_id=stream_identity.row_binding_id,
            batch_id=result.batch_id,
            request_id=request.request_id,
            stream_id=stream_identity.stream_id,
            support_epoch_id=support_epoch_id,
            evidence_ids=evidence_ids,
            accepted_draw_count=accepted_draw_count,
        )
        return result

    def freeze_aggregate_support_evidence_v1(
        self,
        *,
        discovery_batch: batched.V075SignedBatchedObservationV1,
        selected_outcome_ids: tuple[str, ...],
    ) -> tuple[graph.V075BatchAggregateSupportEvidenceV1, ...]:
        if self._closed or discovery_batch not in self._batches:
            _fail("support freeze uses a foreign or closed discovery batch")
        expected_kind = (
            V075LifecycleEventKindV1.DISCOVERY_BATCH
            if self._adaptive_round_index == 0
            else V075LifecycleEventKindV1.ADAPTIVE_DISCOVERY_BATCH
        )
        event = next(
            (
                item
                for item in self._events
                if item.batch_id == discovery_batch.batch_id
            ),
            None,
        )
        if event is None or event.kind is not expected_kind:
            _fail("support freeze source was not a current-round DISCOVERY")
        if self._phase == "VALIDATION":
            _fail("support cannot freeze retrospectively after validation")
        self._phase = "SUPPORT_FREEZE"
        result = (
            self._batched_session.freeze_aggregate_support_evidence_v1(
                discovery_batch=discovery_batch,
                selected_outcome_ids=selected_outcome_ids,
            )
        )
        if any(
            item.evidence_id in {
                existing.evidence_id
                for values in self._frozen_evidence.values()
                for existing in values
            }
            for item in result
        ):
            _fail("aggregate support evidence was frozen twice")
        self._frozen_evidence[discovery_batch.batch_id] = result
        return result

    def register_validation_support_epoch_v1(
        self,
        *,
        stream_identity: graph.V075TransitionStreamIdentityV1,
    ) -> None:
        if (
            self._closed
            or type(stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or stream_identity.lane
            is not graph.V075ObservationLaneV1.VALIDATION
            or stream_identity.context_id != self._context_id
            or stream_identity.arm != self._arm.value
        ):
            _fail("validation support registration is foreign or mistyped")
        support_epoch = stream_identity.pairing_authority.support_chain.leaf
        evidence = tuple(
            item
            for item in support_epoch.evidence
            if type(item) is graph.V075BatchAggregateSupportEvidenceV1
        )
        if not evidence or len(evidence) != len(support_epoch.evidence):
            _fail("validation support must be entirely batch-aggregate evidence")
        source_batches = tuple(
            sorted({item.discovery_batch_id for item in evidence})
        )
        frozen_by_id = {
            item.evidence_id: item
            for values in self._frozen_evidence.values()
            for item in values
        }
        if any(frozen_by_id.get(item.evidence_id) != item for item in evidence):
            _fail("validation support was not frozen in this lifecycle")
        if support_epoch.epoch_id in self._registered_support_epoch_ids:
            _fail("validation support epoch was registered twice")
        self._registered_support_epoch_ids.add(support_epoch.epoch_id)
        self._append_event(
            kind=(
                V075LifecycleEventKindV1.SUPPORT_FREEZE
                if self._adaptive_round_index == 0
                else V075LifecycleEventKindV1.ADAPTIVE_SUPPORT_FREEZE
            ),
            row_binding_id=stream_identity.row_binding_id,
            support_epoch_id=support_epoch.epoch_id,
            evidence_ids=tuple(item.evidence_id for item in evidence),
            source_batch_ids=source_batches,
        )

    def start_adaptive_round_v1(self, round_index: int) -> None:
        if (
            self._closed
            or type(round_index) is not int
            or round_index != self._adaptive_round_index + 1
            or round_index not in (1, 2)
            or self._phase != "VALIDATION"
        ):
            _fail("adaptive round is gapped, premature, or over cap")
        self._adaptive_round_index = round_index
        self._phase = "DISCOVERY"

    def _seal_common(
        self,
        *,
        scope: V075LifecycleAuthorityScopeV1,
        private_replays: tuple[
            batched.V075BatchedObservationPrivateReplayVerificationV1,
            ...,
        ],
        underlying_closure: observer.V075ObserverJournalClosureV1,
        underlying_verification: observer.V075ObserverClosureVerificationV1,
        process_launches: int,
        child_intent_count: int,
        terminal_code: V075LifecycleTerminalCodeV1,
    ) -> V075SealedMultistageOccurrenceLifecycleV1:
        if (
            self._closed
            or not self._batches
            or not any(
                item.request.stream_identity.lane
                is graph.V075ObservationLaneV1.VALIDATION
                for item in self._batches
            )
            or self._batched_session.batches != tuple(self._batches)
            or type(process_launches) is not int
            or process_launches < 0
            or type(child_intent_count) is not int
            or child_intent_count < 0
            or type(terminal_code) is not V075LifecycleTerminalCodeV1
        ):
            _fail("multistage lifecycle cannot close from its current state")
        underlying_session = getattr(self._batched_session, "_session", None)
        if (
            type(underlying_session)
            is not observer.V075PrivateObserverSessionV1
            or type(underlying_closure)
            is not observer.V075ObserverJournalClosureV1
            or type(underlying_verification)
            is not observer.V075ObserverClosureVerificationV1
            or underlying_closure.entries
            or underlying_closure.session_public_id
            != self._batched_session.session_public_id
            or underlying_closure.authority_binding
            != underlying_session.authority_binding
            or underlying_verification.closure_id
            != underlying_closure.closure_id
            or underlying_verification.observer_open_binding_id
            != underlying_closure.authority_binding.binding_id
            or underlying_verification.replayed_record_count != 0
            or underlying_verification.replayed_stream_count != 0
        ):
            _fail("multistage lifecycle lacks one exact empty observer closure")
        public_verifications = tuple(
            sorted(
                (
                    batched.verify_v075_signed_batched_observation_v1(item)
                    for item in self._batches
                ),
                key=lambda item: item.batch_id,
            )
        )
        groups: dict[
            str,
            list[batched.V075SignedBatchedObservationV1],
        ] = {}
        for item in self._batches:
            groups.setdefault(
                item.request.stream_identity.stream_id,
                [],
            ).append(item)
        sequence_verifications = tuple(
            sorted(
                (
                    batched.verify_v075_batched_observation_sequence_v1(
                        tuple(values)
                    )
                    for values in groups.values()
                ),
                key=lambda item: item.stream_id,
            )
        )
        if (
            type(private_replays) is not tuple
            or len(private_replays) != len(self._batches)
            or any(
                type(item)
                is not batched
                .V075BatchedObservationPrivateReplayVerificationV1
                for item in private_replays
            )
        ):
            _fail("private batch-replay registry is incomplete")
        replay_by_batch = {item.batch_id: item for item in private_replays}
        if set(replay_by_batch) != {item.batch_id for item in self._batches}:
            _fail("private batch-replay IDs differ from observed batches")
        for item in self._batches:
            replay = replay_by_batch[item.batch_id]
            if (
                replay.request_id != item.request.request_id
                or replay.observer_open_binding_id
                != item.request.observer_open_binding.binding_id
                or replay.authority_scope is not item.request.authority_scope
                or replay.replayed_draw_count
                != item.request.accepted_draw_count
            ):
                _fail("private batch replay was transplanted or miscounted")
        event_ids = tuple(item.event_id for item in self._events)
        transcript_id = _hash(
            "transcript",
            {
                "schema": (
                    "acfqp.v075_multistage_observer_lifecycle_transcript.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "event_ids": list(event_ids),
            },
        )
        batches = tuple(self._batches)
        batch_ids = tuple(item.batch_id for item in batches)
        request_ids = tuple(item.request.request_id for item in batches)
        stream_ids = tuple(
            sorted({item.request.stream_identity.stream_id for item in batches})
        )
        evidence = self.aggregate_support_evidence
        evidence_ids = tuple(item.evidence_id for item in evidence)
        accepted_draw_count = sum(
            item.request.accepted_draw_count for item in batches
        )
        cap_by_stream = {
            item.request.stream_identity.stream_id: item.request.accepted_draw_cap
            for item in batches
        }
        if any(
            cap_by_stream[item.request.stream_identity.stream_id]
            != item.request.accepted_draw_cap
            for item in batches
        ):
            _fail("one observed stream changed its accepted-draw cap")
        accepted_draw_cap = sum(cap_by_stream.values())
        binding = underlying_session.authority_binding
        if (
            _scope_from_session(self._batched_session) is not scope
            or binding.namespace.target_tape_namespace_id
            != batches[0].request.stream_identity.target_tape_namespace_id
            or any(
                (
                    item.request.stream_identity.context_id,
                    item.request.stream_identity.arm,
                    item.request.session_public_id,
                    item.request.observer_open_binding,
                )
                != (
                    self._context_id,
                    self._arm.value,
                    self._batched_session.session_public_id,
                    binding,
                )
                for item in batches
            )
        ):
            _fail("multistage lifecycle identity graph is mixed")
        signing_values = {
            "scope": scope,
            "occurrence_id": self._occurrence_id,
            "context_id": self._context_id,
            "arm": self._arm.value,
            "target_tape_namespace_id": (
                binding.namespace.target_tape_namespace_id
            ),
            "session_public_id": self._batched_session.session_public_id,
            "observer_open_binding_id": binding.binding_id,
            "route_cap_profile_id": self._route_cap_profile.cap_profile_id,
            "event_ids": event_ids,
            "lifecycle_transcript_id": transcript_id,
            "batch_ids": batch_ids,
            "request_ids": request_ids,
            "stream_ids": stream_ids,
            "sequence_verification_ids": tuple(
                sorted(
                    item.verification_id
                    for item in sequence_verifications
                )
            ),
            "public_verification_ids": tuple(
                sorted(
                    item.verification_id
                    for item in public_verifications
                )
            ),
            "private_replay_verification_ids": tuple(
                sorted(item.verification_id for item in private_replays)
            ),
            "aggregate_support_evidence_ids": evidence_ids,
            "accepted_draw_count": accepted_draw_count,
            "accepted_draw_cap": accepted_draw_cap,
            "process_launches": process_launches,
            "child_intent_count": child_intent_count,
            "underlying_session_closure_id": underlying_closure.closure_id,
            "underlying_closure_verification_id": (
                underlying_verification.verification_id
            ),
            "terminal_code": terminal_code,
        }
        try:
            signature = observer._sign(
                signer=getattr(underlying_session, "_signer", None),
                expected_key=(
                    binding.namespace.signer_registry.observer_evidence_key
                ),
                message=multistage_occurrence_closure_signing_bytes_v1(
                    **signing_values
                ),
            )
        except observer.V075PrivateObserverBoundaryInvariantViolation as error:
            raise V075MultistageObserverLifecycleInvariantViolation(
                str(error)
            ) from error
        closure = V075SignedMultistageOccurrenceClosureV1(
            _CLOSURE_ISSUER,
            scope,
            self._occurrence_id,
            self._context_id,
            self._arm.value,
            binding.namespace.target_tape_namespace_id,
            self._batched_session.session_public_id,
            binding.binding_id,
            self._route_cap_profile.cap_profile_id,
            tuple(self._events),
            transcript_id,
            batch_ids,
            request_ids,
            stream_ids,
            signing_values["sequence_verification_ids"],
            signing_values["public_verification_ids"],
            signing_values["private_replay_verification_ids"],
            evidence_ids,
            accepted_draw_count,
            accepted_draw_cap,
            process_launches,
            child_intent_count,
            underlying_closure.closure_id,
            underlying_verification.verification_id,
            terminal_code,
            signature,
        )
        self._closed = True
        verification = verify_v075_multistage_occurrence_closure_v1(
            closure=closure,
            batches=batches,
            public_verifications=public_verifications,
            sequence_verifications=sequence_verifications,
            private_replay_verifications=tuple(
                sorted(private_replays, key=lambda item: item.batch_id)
            ),
            aggregate_support_evidence=evidence,
            underlying_closure=underlying_closure,
            underlying_closure_verification=underlying_verification,
            observer_open_binding=binding,
        )
        return V075SealedMultistageOccurrenceLifecycleV1(
            closure,
            verification,
            batches,
            public_verifications,
            sequence_verifications,
            tuple(sorted(private_replays, key=lambda item: item.batch_id)),
            evidence,
            underlying_closure,
            underlying_verification,
        )

    def close_construction_v1(
        self,
        *,
        authority: observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1,
        private_environment: (
            batched.V075ConstructionBatchReplayEnvironmentFixtureV1
        ),
        process_launches: int,
        child_intent_count: int,
        terminal_code: V075LifecycleTerminalCodeV1,
    ) -> V075SealedMultistageOccurrenceLifecycleV1:
        if (
            type(authority)
            is not observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1
            or type(private_environment)
            is not batched.V075ConstructionBatchReplayEnvironmentFixtureV1
            or private_environment.namespace != authority.namespace
            or _scope_from_session(self._batched_session)
            is not V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
        ):
            _fail("construction lifecycle close rejects production/duck inputs")
        replays = tuple(
            batched.verify_v075_construction_batched_observation_private_replay_v1(
                claimed=item,
                authority=authority,
                private_environment=private_environment,
            )
            for item in self._batches
        )
        underlying_session = getattr(self._batched_session, "_session", None)
        if type(underlying_session) is not observer.V075PrivateObserverSessionV1:
            _fail("construction lifecycle lost its underlying session")
        underlying_closure = underlying_session.close_v1()
        underlying_verification = (
            observer.verify_construction_private_observer_journal_closure_v1(
                closure=underlying_closure,
                authority=authority,
                private_salt=private_environment.private_salt,
                private_environment=private_environment.private_environment,
            )
        )
        return self._seal_common(
            scope=V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY,
            private_replays=replays,
            underlying_closure=underlying_closure,
            underlying_verification=underlying_verification,
            process_launches=process_launches,
            child_intent_count=child_intent_count,
            terminal_code=terminal_code,
        )

    def close_production_v1(
        self,
        *,
        authority: Any,
        namespace: Any,
        private_salt: bytes,
        private_environment: private_env.V075PrivateGeneratedEnvironmentV1,
        process_launches: int,
        child_intent_count: int,
        terminal_code: V075LifecycleTerminalCodeV1,
    ) -> V075SealedMultistageOccurrenceLifecycleV1:
        # Exact production authority typing is enforced by both downstream
        # verifier calls; the annotation remains Any to avoid a circular
        # import from the preopen authorization module.
        if (
            type(private_environment)
            is not private_env.V075PrivateGeneratedEnvironmentV1
            or _scope_from_session(self._batched_session)
            is not V075LifecycleAuthorityScopeV1.PRODUCTION
        ):
            _fail("production lifecycle close rejects construction/duck inputs")
        replays = tuple(
            batched.verify_v075_production_batched_observation_private_replay_v1(
                claimed=item,
                authority=authority,
                namespace=namespace,
                private_salt=private_salt,
                private_environment=private_environment,
            )
            for item in self._batches
        )
        underlying_session = getattr(self._batched_session, "_session", None)
        if type(underlying_session) is not observer.V075PrivateObserverSessionV1:
            _fail("production lifecycle lost its underlying session")
        underlying_closure = underlying_session.close_v1()
        underlying_verification = (
            observer.verify_private_observer_journal_closure_v1(
                closure=underlying_closure,
                authority=authority,
                namespace=namespace,
                private_salt=private_salt,
                private_environment=(
                    private_environment.secret_laws_for_commitment()
                ),
            )
        )
        return self._seal_common(
            scope=V075LifecycleAuthorityScopeV1.PRODUCTION,
            private_replays=replays,
            underlying_closure=underlying_closure,
            underlying_verification=underlying_verification,
            process_launches=process_launches,
            child_intent_count=child_intent_count,
            terminal_code=terminal_code,
        )


def open_v075_parent_owned_multistage_lifecycle_v1(
    *,
    batched_session: batched.V075PrivateBatchedObserverSessionV1,
    occurrence_id: str,
    context_id: str,
    arm: worker.V075WorkerArmV1,
    route_cap_profile: worker.V075WorkerCapProfileV1,
) -> V075ParentOwnedMultistageObserverLifecycleV1:
    return V075ParentOwnedMultistageObserverLifecycleV1(
        batched_session=batched_session,
        occurrence_id=occurrence_id,
        context_id=context_id,
        arm=arm,
        route_cap_profile=route_cap_profile,
    )


def _verify_phase_causality(
    events: tuple[V075MultistageLifecycleEventV1, ...],
    evidence_by_id: Mapping[
        str,
        graph.V075BatchAggregateSupportEvidenceV1,
    ],
) -> None:
    phase_by_round: dict[int, int] = {}
    batch_sequence: dict[str, int] = {}
    freeze_sequence_by_epoch: dict[str, int] = {}
    freeze_evidence_by_epoch: dict[str, tuple[str, ...]] = {}
    expected_phase = {
        V075LifecycleEventKindV1.DISCOVERY_BATCH: 0,
        V075LifecycleEventKindV1.SUPPORT_FREEZE: 1,
        V075LifecycleEventKindV1.VALIDATION_BATCH: 2,
        V075LifecycleEventKindV1.ADAPTIVE_DISCOVERY_BATCH: 0,
        V075LifecycleEventKindV1.ADAPTIVE_SUPPORT_FREEZE: 1,
        V075LifecycleEventKindV1.ADAPTIVE_VALIDATION_BATCH: 2,
    }
    seen_rounds: set[int] = set()
    for event in events:
        seen_rounds.add(event.adaptive_round_index)
        phase = expected_phase[event.kind]
        prior = phase_by_round.get(event.adaptive_round_index, 0)
        if phase < prior:
            _fail("lifecycle phase order regressed within one round")
        phase_by_round[event.adaptive_round_index] = phase
        if event.batch_id is not None:
            batch_sequence[event.batch_id] = event.sequence_number
        if event.kind in {
            V075LifecycleEventKindV1.SUPPORT_FREEZE,
            V075LifecycleEventKindV1.ADAPTIVE_SUPPORT_FREEZE,
        }:
            assert event.support_epoch_id is not None
            if event.support_epoch_id in freeze_sequence_by_epoch:
                _fail("one support epoch was frozen twice")
            for evidence_id in event.aggregate_support_evidence_ids:
                evidence = evidence_by_id.get(evidence_id)
                if (
                    evidence is None
                    or evidence.discovery_batch_id
                    not in event.source_discovery_batch_ids
                    or batch_sequence.get(evidence.discovery_batch_id, 10**18)
                    >= event.sequence_number
                ):
                    _fail("support freeze is retrospective or source-transplanted")
            freeze_sequence_by_epoch[event.support_epoch_id] = (
                event.sequence_number
            )
            freeze_evidence_by_epoch[event.support_epoch_id] = (
                event.aggregate_support_evidence_ids
            )
        if event.kind in {
            V075LifecycleEventKindV1.VALIDATION_BATCH,
            V075LifecycleEventKindV1.ADAPTIVE_VALIDATION_BATCH,
        }:
            assert event.support_epoch_id is not None
            if (
                freeze_sequence_by_epoch.get(event.support_epoch_id, 10**18)
                >= event.sequence_number
                or freeze_evidence_by_epoch.get(event.support_epoch_id)
                != event.aggregate_support_evidence_ids
            ):
                _fail("VALIDATION did not follow its exact support freeze")
    if seen_rounds != set(range(max(seen_rounds) + 1)):
        _fail("adaptive lifecycle rounds are gapped")


def verify_v075_multistage_occurrence_closure_v1(
    *,
    closure: V075SignedMultistageOccurrenceClosureV1,
    batches: tuple[batched.V075SignedBatchedObservationV1, ...],
    public_verifications: tuple[
        batched.V075BatchedObservationPublicVerificationV1, ...
    ],
    sequence_verifications: tuple[
        batched.V075BatchedObservationSequenceVerificationV1, ...
    ],
    private_replay_verifications: tuple[
        batched.V075BatchedObservationPrivateReplayVerificationV1, ...
    ],
    aggregate_support_evidence: tuple[
        graph.V075BatchAggregateSupportEvidenceV1, ...
    ],
    underlying_closure: observer.V075ObserverJournalClosureV1,
    underlying_closure_verification: (
        observer.V075ObserverClosureVerificationV1
    ),
    observer_open_binding: observer.V075ObserverOpenAuthorityBindingV1,
) -> V075MultistageOccurrenceClosureVerificationV1:
    """Independently replay the public aggregate lifecycle and signature."""

    if (
        type(closure) is not V075SignedMultistageOccurrenceClosureV1
        or type(batches) is not tuple
        or not batches
        or any(
            type(item) is not batched.V075SignedBatchedObservationV1
            for item in batches
        )
        or type(observer_open_binding)
        is not observer.V075ObserverOpenAuthorityBindingV1
        or observer_open_binding.binding_id
        != closure.observer_open_binding_id
        or observer_open_binding.namespace.target_tape_namespace_id
        != closure.target_tape_namespace_id
    ):
        _fail("multistage closure verification input is untyped or transplanted")
    if (
        closure.batch_ids != tuple(item.batch_id for item in batches)
        or closure.request_ids
        != tuple(item.request.request_id for item in batches)
        or closure.stream_ids
        != tuple(
            sorted(
                {
                    item.request.stream_identity.stream_id
                    for item in batches
                }
            )
        )
        or closure.accepted_draw_count
        != sum(item.request.accepted_draw_count for item in batches)
        or any(
            (
                item.request.session_public_id,
                item.request.observer_open_binding,
                item.request.stream_identity.context_id,
                item.request.stream_identity.arm,
            )
            != (
                closure.session_public_id,
                observer_open_binding,
                closure.context_id,
                closure.arm,
            )
            for item in batches
        )
    ):
        _fail("multistage batch registry differs from closure")
    expected_public = tuple(
        sorted(
            (
                batched.verify_v075_signed_batched_observation_v1(item)
                for item in batches
            ),
            key=lambda item: item.batch_id,
        )
    )
    if (
        public_verifications != expected_public
        or closure.public_verification_ids
        != tuple(
            sorted(item.verification_id for item in expected_public)
        )
    ):
        _fail("multistage public batch verifications differ from replay")
    groups: dict[str, list[batched.V075SignedBatchedObservationV1]] = {}
    for item in batches:
        groups.setdefault(item.request.stream_identity.stream_id, []).append(
            item
        )
    expected_sequences = tuple(
        sorted(
            (
                batched.verify_v075_batched_observation_sequence_v1(
                    tuple(values)
                )
                for values in groups.values()
            ),
            key=lambda item: item.stream_id,
        )
    )
    if (
        sequence_verifications != expected_sequences
        or closure.sequence_verification_ids
        != tuple(
            sorted(item.verification_id for item in expected_sequences)
        )
    ):
        _fail("multistage sequence verifications differ from replay")
    replay_by_batch = {
        item.batch_id: item for item in private_replay_verifications
    }
    if (
        len(replay_by_batch) != len(private_replay_verifications)
        or set(replay_by_batch) != set(closure.batch_ids)
        or closure.private_replay_verification_ids
        != tuple(
            sorted(
                item.verification_id
                for item in private_replay_verifications
            )
        )
    ):
        _fail("multistage private-replay registry is incomplete")
    evidence_by_id = {
        item.evidence_id: item for item in aggregate_support_evidence
    }
    if (
        len(evidence_by_id) != len(aggregate_support_evidence)
        or tuple(sorted(evidence_by_id))
        != closure.aggregate_support_evidence_ids
    ):
        _fail("multistage aggregate-support registry is incomplete")
    _verify_phase_causality(closure.events, evidence_by_id)
    batch_events = tuple(
        item for item in closure.events if item.batch_id is not None
    )
    if (
        tuple(item.batch_id for item in batch_events) != closure.batch_ids
        or tuple(item.request_id for item in batch_events)
        != closure.request_ids
        or sum(item.accepted_draw_count for item in batch_events)
        != closure.accepted_draw_count
    ):
        _fail("multistage event registry differs from batch emission order")
    if (
        type(underlying_closure)
        is not observer.V075ObserverJournalClosureV1
        or type(underlying_closure_verification)
        is not observer.V075ObserverClosureVerificationV1
        or underlying_closure.entries
        or underlying_closure.closure_id
        != closure.underlying_session_closure_id
        or underlying_closure.authority_binding != observer_open_binding
        or underlying_closure.session_public_id != closure.session_public_id
        or underlying_closure_verification.closure_id
        != underlying_closure.closure_id
        or underlying_closure_verification.verification_id
        != closure.underlying_closure_verification_id
        or underlying_closure_verification.replayed_record_count != 0
        or underlying_closure_verification.replayed_stream_count != 0
    ):
        _fail("underlying observer closure is nonempty, stale, or transplanted")
    message = multistage_occurrence_closure_signing_bytes_v1(
        **closure._signing_values()
    )
    if not (
        observer.public_authority
        .verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=(
                observer_open_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=message,
            signature_hex=closure.observer_signature_hex,
        )
    ):
        _fail("multistage occurrence closure signature is invalid")
    reminted_id = _hash(
        "closure",
        {
            **_closure_payload(**closure._signing_values()),
            "observer_signature_hex": closure.observer_signature_hex,
            "observer_signature_verified": True,
        },
    )
    if reminted_id != closure.closure_id:
        _fail("multistage closure content identity differs from replay")
    return V075MultistageOccurrenceClosureVerificationV1(
        _VERIFICATION_ISSUER,
        closure.closure_id,
        closure.lifecycle_transcript_id,
        closure.observer_open_binding_id,
        len(batches),
        closure.accepted_draw_count,
        len(aggregate_support_evidence),
    )


__all__ = [
    "DOMAIN_TAGS",
    "PER_DRAW_CAPABILITY_EXPANSION_ALLOWED",
    "PROFILE_KEY",
    "PRODUCTION_INTEGRATION_READY",
    "V075LifecycleAuthorityScopeV1",
    "V075LifecycleEventKindV1",
    "V075LifecycleTerminalCodeV1",
    "V075MultistageLifecycleEventV1",
    "V075MultistageObserverLifecycleInvariantViolation",
    "V075MultistageOccurrenceClosureVerificationV1",
    "V075OpenMultistageLifecycleBindingV1",
    "V075ParentOwnedMultistageObserverLifecycleV1",
    "V075SealedMultistageOccurrenceLifecycleV1",
    "V075SignedMultistageOccurrenceClosureV1",
    "multistage_occurrence_closure_signing_bytes_v1",
    "open_v075_parent_owned_multistage_lifecycle_v1",
    "verify_v075_multistage_occurrence_closure_v1",
]
