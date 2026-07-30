"""Observer-owned, signed batch-control construction authority for V0-075.

This module closes the causal gap left by post-hoc batch-prefix wrappers.  It
opens and owns one exact V2 private observer session behind its public API,
signs the zero/current journal head, freezes a public head-bound intent before
every draw, and emits an observer-signed append receipt after the signed batch
has entered the observer journal.

The implementation is deliberately construction-only.  Python object
encapsulation is not process isolation, so no artifact from this module
authorizes official execution or earns a scientific endpoint claim.  A future
production boundary must put the same protocol behind an isolated observer
process and tracked byte gate.  The caller still retains its signer reference;
therefore this wrapper proves trusted in-process ordering, not exclusive signer
ownership or single-private-boundary atomicity.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.54.0"
PROFILE_KEY = "v075_observer_signed_batch_control_authority_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PROCESS_ISOLATION_PROVIDED = False
PUBLIC_PRIVATE_SESSION_API_EXPOSED = False
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"

DOMAIN_TAGS = {
    "journal_head_signature": (
        "acfqp:v075-observer-signed-batch-journal-head-signature:v2"
    ),
    "journal_head": "acfqp:v075-observer-signed-batch-journal-head:v2",
    "batch_intent": "acfqp:v075-head-bound-exact-batch-intent:v2",
    "semantic_authority": (
        "acfqp:v075-controlled-batch-semantic-authority-binding:v2"
    ),
    "support_freeze_signature": (
        "acfqp:v075-controlled-complete-support-freeze-signature:v2"
    ),
    "support_freeze": (
        "acfqp:v075-controlled-complete-support-freeze:v2"
    ),
    "open_prefix_verification": (
        "acfqp:v075-open-controlled-batch-prefix-verification:v2"
    ),
    "append_receipt_signature": (
        "acfqp:v075-observer-signed-batch-append-receipt-signature:v2"
    ),
    "append_receipt": (
        "acfqp:v075-observer-signed-batch-append-receipt:v2"
    ),
    "control_closure_signature": (
        "acfqp:v075-observer-signed-batch-control-closure-signature:v2"
    ),
    "control_closure": (
        "acfqp:v075-observer-signed-batch-control-closure:v2"
    ),
    "reconciliation": (
        "acfqp:v075-observer-signed-batch-control-reconciliation:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 signed batch-control domains must be unique")


class V075ObserverSignedBatchControlV2InvariantViolation(ValueError):
    """The controlled observer, signed chain, or reconciliation was invalid."""


class V075ObserverSignedBatchControlProductionV2NotReady(RuntimeError):
    """Production use remains locked until an isolated byte-gated boundary."""


def _fail(message: str) -> None:
    raise V075ObserverSignedBatchControlV2InvariantViolation(message)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            str(error)
        ) from error


def _signing_bytes(role: str, payload: Mapping[str, Any]) -> bytes:
    try:
        return (
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        )
    except (KeyError, TypeError, ValueError) as error:
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            str(error)
        ) from error


def _sign(
    *,
    signer: observer.V075ObserverEvidenceSignerProtocolV2,
    binding: observer.V075ObserverOpenAuthorityBindingV2,
    message: bytes,
) -> str:
    if (
        not isinstance(
            signer,
            observer.V075ObserverEvidenceSignerProtocolV2,
        )
        or type(binding)
        is not observer.V075ObserverOpenAuthorityBindingV2
    ):
        _fail("signed batch-control signer or binding is untyped")
    expected_key = binding.namespace.signer_registry.observer_evidence_key
    if signer.public_verification_key_v1() != expected_key:
        _fail("signed batch-control signer is foreign")
    signature = signer.sign_observer_evidence_v1(message)
    if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=expected_key,
        message=message,
        signature_hex=signature,
    ):
        _fail("signed batch-control signer emitted an invalid signature")
    return signature


def _verify_signature(
    *,
    binding: observer.V075ObserverOpenAuthorityBindingV2,
    message: bytes,
    signature_hex: str,
) -> None:
    if (
        type(binding)
        is not observer.V075ObserverOpenAuthorityBindingV2
        or not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=(
                binding.namespace.signer_registry.observer_evidence_key
            ),
            message=message,
            signature_hex=signature_hex,
        )
    ):
        _fail("observer-signed batch-control signature is invalid")


@dataclass(frozen=True, slots=True)
class V075BatchStreamFrontierV2:
    """Exact next-draw frontier for one stream in a signed journal head."""

    stream_id: str
    row_binding_id: str
    accepted_draw_cap: int
    accepted_draw_end: int
    batch_count: int
    last_request_id: str
    last_batch_id: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.stream_id, "controlled stream"),
            (self.row_binding_id, "controlled row binding"),
            (self.last_request_id, "controlled last request"),
            (self.last_batch_id, "controlled last batch"),
        ):
            _cid(value, label)
        if (
            type(self.accepted_draw_cap) is not int
            or self.accepted_draw_cap <= 0
            or type(self.accepted_draw_end) is not int
            or not 0 < self.accepted_draw_end <= self.accepted_draw_cap
            or type(self.batch_count) is not int
            or self.batch_count <= 0
        ):
            _fail("controlled stream frontier is empty or malformed")

    @property
    def next_accepted_draw_index(self) -> int:
        return self.accepted_draw_end + 1

    def to_document(self) -> dict[str, Any]:
        return {
            "stream_id": self.stream_id,
            "row_binding_id": self.row_binding_id,
            "accepted_draw_cap": self.accepted_draw_cap,
            "accepted_draw_end": self.accepted_draw_end,
            "next_accepted_draw_index": self.next_accepted_draw_index,
            "batch_count": self.batch_count,
            "last_request_id": self.last_request_id,
            "last_batch_id": self.last_batch_id,
        }


def _journal_head_payload(
    *,
    occurrence_id: str,
    session_public_id: str,
    authority_binding: observer.V075ObserverOpenAuthorityBindingV2,
    entry_count: int,
    tail_entry_id: str | None,
    total_accepted_draw_count: int,
    stream_frontiers: tuple[V075BatchStreamFrontierV2, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_observer_signed_batch_journal_head.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "occurrence_id": occurrence_id,
        "observer_session_public_id": session_public_id,
        "observer_open_binding_id": authority_binding.binding_id,
        "observer_open_authorization_id": authority_binding.authorization_id,
        "target_tape_namespace_id": (
            authority_binding.namespace.target_tape_namespace_id
        ),
        "observer_signer_key_id": (
            authority_binding.namespace.signer_registry.observer_evidence_key
            .key_id
        ),
        "entry_count": entry_count,
        "tail_entry_id": tail_entry_id,
        "total_accepted_draw_count": total_accepted_draw_count,
        "stream_frontiers": [
            item.to_document() for item in stream_frontiers
        ],
        "stream_count": len(stream_frontiers),
        "zero_head": entry_count == 0,
        "observer_owned_state": True,
        "observer_signature_required": True,
        "authority_version": "V2",
        "namespace_version": "V2",
        "private_material_serialized": False,
    }


@dataclass(frozen=True, slots=True)
class V075SignedBatchJournalHeadV2:
    """Observer-signed exact journal state, including the empty zero head."""

    occurrence_id: str
    session_public_id: str
    authority_binding: observer.V075ObserverOpenAuthorityBindingV2 = field(
        repr=False
    )
    entry_count: int
    tail_entry_id: str | None
    total_accepted_draw_count: int
    stream_frontiers: tuple[V075BatchStreamFrontierV2, ...]
    observer_signature_hex: str

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "signed-head occurrence")
        _cid(self.session_public_id, "signed-head session")
        if (
            type(self.authority_binding)
            is not observer.V075ObserverOpenAuthorityBindingV2
            or type(self.entry_count) is not int
            or self.entry_count < 0
            or type(self.total_accepted_draw_count) is not int
            or self.total_accepted_draw_count < 0
            or type(self.stream_frontiers) is not tuple
            or any(
                type(item) is not V075BatchStreamFrontierV2
                for item in self.stream_frontiers
            )
            or self.stream_frontiers
            != tuple(
                sorted(self.stream_frontiers, key=lambda item: item.stream_id)
            )
            or len({item.stream_id for item in self.stream_frontiers})
            != len(self.stream_frontiers)
        ):
            _fail("observer-signed journal head is malformed")
        if self.entry_count == 0:
            if (
                self.tail_entry_id is not None
                or self.total_accepted_draw_count != 0
                or self.stream_frontiers
            ):
                _fail("zero journal head contains nonzero state")
        else:
            if self.tail_entry_id is None:
                _fail("nonzero journal head lacks its exact tail")
            _cid(self.tail_entry_id, "signed-head tail")
            if (
                not self.stream_frontiers
                or sum(
                    item.batch_count for item in self.stream_frontiers
                )
                != self.entry_count
                or sum(
                    item.accepted_draw_end
                    for item in self.stream_frontiers
                )
                != self.total_accepted_draw_count
            ):
                _fail("nonzero journal head frontiers do not reconcile")
        _verify_signature(
            binding=self.authority_binding,
            message=_signing_bytes(
                "journal_head_signature",
                self._unsigned_payload(),
            ),
            signature_hex=self.observer_signature_hex,
        )

    def _unsigned_payload(self) -> dict[str, Any]:
        return _journal_head_payload(
            occurrence_id=self.occurrence_id,
            session_public_id=self.session_public_id,
            authority_binding=self.authority_binding,
            entry_count=self.entry_count,
            tail_entry_id=self.tail_entry_id,
            total_accepted_draw_count=self.total_accepted_draw_count,
            stream_frontiers=self.stream_frontiers,
        )

    @property
    def head_id(self) -> str:
        return _hash(
            "journal_head",
            {
                **self._unsigned_payload(),
                "observer_signature_hex": self.observer_signature_hex,
                "observer_signature_verified": True,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._unsigned_payload(),
            "observer_open_binding": self.authority_binding.to_document(),
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "head_id": self.head_id,
        }


_INTENT_ISSUER = object()
_SEMANTIC_AUTHORITY_ISSUER = object()


class V075ControlledBatchSemanticAuthorityRoleV2(str, Enum):
    INITIAL_SCHEDULE_ROW_INTENT = "INITIAL_SCHEDULE_ROW_INTENT"
    DYNAMIC_CHILD_DISCOVERY_INTENT = "DYNAMIC_CHILD_DISCOVERY_INTENT"


class V075ControlledBatchSemanticAuthoritySchemaV2(str, Enum):
    INITIAL_SCHEDULE_ROW_INTENT = (
        "acfqp.v075_five_arm_initial_row_intent.v2"
    )
    DYNAMIC_CHILD_DISCOVERY_INTENT = (
        "acfqp.v075_dynamic_child_discovery_intent.v2"
    )


class V075ControlledBatchStageV2(str, Enum):
    ROOT_DISCOVERY = "ROOT_DISCOVERY"
    ROOT_VALIDATION = "ROOT_VALIDATION"
    CHILD_DISCOVERY = "CHILD_DISCOVERY"
    CHILD_VALIDATION = "CHILD_VALIDATION"


_ROLE_SCHEMA = {
    V075ControlledBatchSemanticAuthorityRoleV2
    .INITIAL_SCHEDULE_ROW_INTENT: (
        V075ControlledBatchSemanticAuthoritySchemaV2
        .INITIAL_SCHEDULE_ROW_INTENT
    ),
    V075ControlledBatchSemanticAuthorityRoleV2
    .DYNAMIC_CHILD_DISCOVERY_INTENT: (
        V075ControlledBatchSemanticAuthoritySchemaV2
        .DYNAMIC_CHILD_DISCOVERY_INTENT
    ),
}


@dataclass(frozen=True, slots=True)
class V075ControlledBatchSemanticAuthorityBindingV2:
    """Typed opaque link awaiting upstream semantic-authority replay."""

    _issuer: object = field(repr=False, compare=False)
    role: V075ControlledBatchSemanticAuthorityRoleV2
    schema: V075ControlledBatchSemanticAuthoritySchemaV2
    semantic_artifact_id: str
    semantic_verification_id: str
    stage: V075ControlledBatchStageV2
    round_index: int
    support_freeze_id: str | None
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.semantic_artifact_id, "semantic authority artifact")
        _cid(self.semantic_verification_id, "semantic authority verification")
        if self.support_freeze_id is not None:
            _cid(self.support_freeze_id, "semantic authority support freeze")
        discovery = self.stage in {
            V075ControlledBatchStageV2.ROOT_DISCOVERY,
            V075ControlledBatchStageV2.CHILD_DISCOVERY,
        }
        validation = self.stage in {
            V075ControlledBatchStageV2.ROOT_VALIDATION,
            V075ControlledBatchStageV2.CHILD_VALIDATION,
        }
        role_stage_valid = (
            self.role
            is (
                V075ControlledBatchSemanticAuthorityRoleV2
                .INITIAL_SCHEDULE_ROW_INTENT
            )
            and self.stage
            in {
                V075ControlledBatchStageV2.ROOT_DISCOVERY,
                V075ControlledBatchStageV2.ROOT_VALIDATION,
            }
            and self.round_index == 0
        ) or (
            self.role
            is (
                V075ControlledBatchSemanticAuthorityRoleV2
                .DYNAMIC_CHILD_DISCOVERY_INTENT
            )
            and self.stage
            in {
                V075ControlledBatchStageV2.CHILD_DISCOVERY,
                V075ControlledBatchStageV2.CHILD_VALIDATION,
            }
            and self.round_index > 0
        )
        if (
            self._issuer is not _SEMANTIC_AUTHORITY_ISSUER
            or type(self.role)
            is not V075ControlledBatchSemanticAuthorityRoleV2
            or type(self.schema)
            is not V075ControlledBatchSemanticAuthoritySchemaV2
            or _ROLE_SCHEMA.get(self.role) is not self.schema
            or type(self.stage) is not V075ControlledBatchStageV2
            or type(self.round_index) is not int
            or self.round_index < 0
            or not role_stage_valid
            or not (discovery or validation)
            or discovery != (self.support_freeze_id is None)
        ):
            _fail(
                "controlled batch semantic authority role, schema, stage, "
                "round, or support-freeze requiredness is invalid"
            )
        object.__setattr__(
            self,
            "_binding_id",
            _hash("semantic_authority", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_controlled_batch_semantic_authority_binding.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "semantic_authority_role": self.role.value,
            "semantic_authority_schema": self.schema.value,
            "semantic_artifact_id": self.semantic_artifact_id,
            "semantic_verification_id": self.semantic_verification_id,
            "stage": self.stage.value,
            "round_index": self.round_index,
            "support_freeze_id": self.support_freeze_id,
            "typed_support_freeze_optionality": True,
            "semantic_authority_reference_status": "OPAQUE_DEFERRED",
            "semantic_authority_exact_replay_performed": False,
            "semantic_artifact_bytes_verified_by_this_boundary": False,
            "production_registry_replay_required": True,
            "child_validation_discovery_authority_and_support_freeze_relation_"
            "replay_performed": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


def freeze_v075_controlled_batch_semantic_authority_v2(
    *,
    role: V075ControlledBatchSemanticAuthorityRoleV2,
    schema: V075ControlledBatchSemanticAuthoritySchemaV2,
    semantic_artifact_id: str,
    semantic_verification_id: str,
    stage: V075ControlledBatchStageV2,
    round_index: int,
    support_freeze_id: str | None,
) -> V075ControlledBatchSemanticAuthorityBindingV2:
    return V075ControlledBatchSemanticAuthorityBindingV2(
        _SEMANTIC_AUTHORITY_ISSUER,
        role,
        schema,
        semantic_artifact_id,
        semantic_verification_id,
        stage,
        round_index,
        support_freeze_id,
    )


@dataclass(frozen=True, slots=True)
class V075HeadBoundExactBatchIntentV2:
    """Public exact batch intent frozen against one signed prior head."""

    _issuer: object = field(repr=False, compare=False)
    prior_head_id: str
    occurrence_id: str
    session_public_id: str
    observer_open_binding_id: str
    semantic_authority: V075ControlledBatchSemanticAuthorityBindingV2
    stream_identity: graph.V075TransitionStreamIdentityV1 = field(repr=False)
    accepted_draw_start: int
    accepted_draw_count: int
    accepted_draw_cap: int
    _intent_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.prior_head_id, "intent prior head"),
            (self.occurrence_id, "intent occurrence"),
            (self.session_public_id, "intent session"),
            (self.observer_open_binding_id, "intent observer binding"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _INTENT_ISSUER
            or type(self.semantic_authority)
            is not V075ControlledBatchSemanticAuthorityBindingV2
            or type(self.stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or type(self.accepted_draw_start) is not int
            or self.accepted_draw_start <= 0
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count <= 0
            or type(self.accepted_draw_cap) is not int
            or self.accepted_draw_cap <= 0
            or self.accepted_draw_end > self.accepted_draw_cap
        ):
            _fail("head-bound exact batch intent is caller-minted or invalid")
        expected_lane = (
            "DISCOVERY"
            if self.semantic_authority.stage
            in {
                V075ControlledBatchStageV2.ROOT_DISCOVERY,
                V075ControlledBatchStageV2.CHILD_DISCOVERY,
            }
            else "VALIDATION"
        )
        if self.stream_identity.lane.value != expected_lane:
            _fail("head-bound exact batch intent stage and lane disagree")
        object.__setattr__(
            self,
            "_intent_id",
            _hash("batch_intent", self._payload()),
        )

    @property
    def accepted_draw_end(self) -> int:
        return self.accepted_draw_start + self.accepted_draw_count - 1

    def _payload(self) -> dict[str, Any]:
        stream = self.stream_identity
        return {
            "schema": "acfqp.v075_head_bound_exact_batch_intent.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "prior_head_id": self.prior_head_id,
            "occurrence_id": self.occurrence_id,
            "observer_session_public_id": self.session_public_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "semantic_authority_binding_id": (
                self.semantic_authority.binding_id
            ),
            "semantic_authority_role": self.semantic_authority.role.value,
            "semantic_authority_schema": (
                self.semantic_authority.schema.value
            ),
            "semantic_artifact_id": (
                self.semantic_authority.semantic_artifact_id
            ),
            "semantic_verification_id": (
                self.semantic_authority.semantic_verification_id
            ),
            "stage": self.semantic_authority.stage.value,
            "round_index": self.semantic_authority.round_index,
            "support_freeze_id": (
                self.semantic_authority.support_freeze_id
            ),
            "target_tape_namespace_id": (
                stream.target_tape_namespace_id
            ),
            "context_id": stream.context_id,
            "stream_id": stream.stream_id,
            "row_binding_id": stream.row_binding_id,
            "catalogue_id": stream.catalogue_id,
            "support_epoch_id": stream.support_epoch_id,
            "observer_epoch_index": stream.observer_epoch_index,
            "lane": stream.lane.value,
            "arm": stream.arm,
            "stream_identity_sha256": hashlib.sha256(
                canonical_json_bytes(stream.to_document())
            ).hexdigest(),
            "accepted_draw_start": self.accepted_draw_start,
            "accepted_draw_count": self.accepted_draw_count,
            "accepted_draw_end": self.accepted_draw_end,
            "accepted_draw_cap": self.accepted_draw_cap,
            "head_bound_before_draw": True,
            "public_law_free_intent": True,
            "private_material_serialized": False,
        }

    @property
    def intent_id(self) -> str:
        return self._intent_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "semantic_authority": self.semantic_authority.to_document(),
            "stream_identity": self.stream_identity.to_document(),
            "intent_id": self.intent_id,
        }


def freeze_v075_head_bound_exact_batch_intent_v2(
    *,
    prior_head: V075SignedBatchJournalHeadV2,
    stream_identity: graph.V075TransitionStreamIdentityV1,
    semantic_authority: V075ControlledBatchSemanticAuthorityBindingV2,
    accepted_draw_start: int,
    accepted_draw_count: int,
    accepted_draw_cap: int,
) -> V075HeadBoundExactBatchIntentV2:
    """Freeze one public law-free intent; this performs no target draw."""

    if (
        type(prior_head) is not V075SignedBatchJournalHeadV2
        or type(stream_identity)
        is not graph.V075TransitionStreamIdentityV1
        or type(semantic_authority)
        is not V075ControlledBatchSemanticAuthorityBindingV2
    ):
        _fail("exact batch intent requires one signed head and exact stream")
    try:
        replayed_stream = observer._validate_v2_stream(  # noqa: SLF001
            binding=prior_head.authority_binding,
            stream_identity=stream_identity,
        )
    except observer.V075PrivateObserverBoundaryV2InvariantViolation as error:
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            str(error)
        ) from error
    expected_start = _expected_next_from_head(
        head=prior_head,
        stream_id=replayed_stream.stream_id,
        requested_cap=accepted_draw_cap,
    )
    if accepted_draw_start != expected_start:
        _fail("head-bound exact batch intent is gapped or overlaps its prefix")
    return V075HeadBoundExactBatchIntentV2(
        _INTENT_ISSUER,
        prior_head.head_id,
        prior_head.occurrence_id,
        prior_head.session_public_id,
        prior_head.authority_binding.binding_id,
        semantic_authority,
        replayed_stream,
        accepted_draw_start,
        accepted_draw_count,
        accepted_draw_cap,
    )


def _append_receipt_payload(
    *,
    occurrence_id: str,
    session_public_id: str,
    authority_binding: observer.V075ObserverOpenAuthorityBindingV2,
    prior_head_id: str,
    intent_id: str,
    semantic_authority_binding_id: str,
    batch_id: str,
    batch_request_id: str,
    journal_entry_id: str,
    journal_sequence_number: int,
    resulting_head_id: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_observer_signed_batch_append_receipt.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "occurrence_id": occurrence_id,
        "observer_session_public_id": session_public_id,
        "observer_open_binding_id": authority_binding.binding_id,
        "observer_open_authorization_id": authority_binding.authorization_id,
        "target_tape_namespace_id": (
            authority_binding.namespace.target_tape_namespace_id
        ),
        "prior_head_id": prior_head_id,
        "intent_id": intent_id,
        "semantic_authority_binding_id": semantic_authority_binding_id,
        "signed_batch_id": batch_id,
        "signed_batch_request_id": batch_request_id,
        "journal_entry_id": journal_entry_id,
        "journal_sequence_number": journal_sequence_number,
        "resulting_head_id": resulting_head_id,
        "intent_validated_before_draw": True,
        "batch_appended_before_receipt": True,
        "trusted_in_process_sequential_control_path": True,
        "single_private_boundary_atomicity_proven": False,
        "exclusive_signer_ownership_proven": False,
        "private_material_serialized": False,
    }


@dataclass(frozen=True, slots=True)
class V075ObserverSignedBatchAppendReceiptV2:
    """Observer signature over prior head, intent, batch, entry, and new head."""

    occurrence_id: str
    session_public_id: str
    authority_binding: observer.V075ObserverOpenAuthorityBindingV2 = field(
        repr=False
    )
    prior_head_id: str
    intent_id: str
    semantic_authority_binding_id: str
    batch_id: str
    batch_request_id: str
    journal_entry_id: str
    journal_sequence_number: int
    resulting_head_id: str
    observer_signature_hex: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "receipt occurrence"),
            (self.session_public_id, "receipt session"),
            (self.prior_head_id, "receipt prior head"),
            (self.intent_id, "receipt intent"),
            (
                self.semantic_authority_binding_id,
                "receipt semantic authority",
            ),
            (self.batch_id, "receipt signed batch"),
            (self.batch_request_id, "receipt batch request"),
            (self.journal_entry_id, "receipt journal entry"),
            (self.resulting_head_id, "receipt resulting head"),
        ):
            _cid(value, label)
        if (
            type(self.authority_binding)
            is not observer.V075ObserverOpenAuthorityBindingV2
            or type(self.journal_sequence_number) is not int
            or self.journal_sequence_number <= 0
        ):
            _fail("observer-signed append receipt is malformed")
        _verify_signature(
            binding=self.authority_binding,
            message=_signing_bytes(
                "append_receipt_signature",
                self._unsigned_payload(),
            ),
            signature_hex=self.observer_signature_hex,
        )

    def _unsigned_payload(self) -> dict[str, Any]:
        return _append_receipt_payload(
            occurrence_id=self.occurrence_id,
            session_public_id=self.session_public_id,
            authority_binding=self.authority_binding,
            prior_head_id=self.prior_head_id,
            intent_id=self.intent_id,
            semantic_authority_binding_id=(
                self.semantic_authority_binding_id
            ),
            batch_id=self.batch_id,
            batch_request_id=self.batch_request_id,
            journal_entry_id=self.journal_entry_id,
            journal_sequence_number=self.journal_sequence_number,
            resulting_head_id=self.resulting_head_id,
        )

    @property
    def receipt_id(self) -> str:
        return _hash(
            "append_receipt",
            {
                **self._unsigned_payload(),
                "observer_signature_hex": self.observer_signature_hex,
                "observer_signature_verified": True,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._unsigned_payload(),
            "observer_open_binding": self.authority_binding.to_document(),
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "receipt_id": self.receipt_id,
        }


_OWNED_APPEND_ISSUER = object()
_REPLAYED_APPEND_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ControlledBatchAppendV2:
    """Public artifacts emitted by one fail-closed in-process control step."""

    prior_head: V075SignedBatchJournalHeadV2
    intent: V075HeadBoundExactBatchIntentV2
    batch: observer.V075SignedObservationBatchV2 = field(repr=False)
    resulting_head: V075SignedBatchJournalHeadV2
    receipt: V075ObserverSignedBatchAppendReceiptV2
    _exact_batch_issuer: InitVar[object | None] = None

    def __post_init__(self, _exact_batch_issuer: object | None) -> None:
        if (
            type(self.prior_head) is not V075SignedBatchJournalHeadV2
            or type(self.intent) is not V075HeadBoundExactBatchIntentV2
            or type(self.batch) is not observer.V075SignedObservationBatchV2
            or type(self.resulting_head) is not V075SignedBatchJournalHeadV2
            or type(self.receipt)
            is not V075ObserverSignedBatchAppendReceiptV2
        ):
            _fail("controlled batch append graph is untyped")
        if _exact_batch_issuer in {
            _OWNED_APPEND_ISSUER,
            _REPLAYED_APPEND_ISSUER,
        }:
            batch = self.batch
        else:
            try:
                batch = observer.replay_signed_observation_batch_object_v2(
                    self.batch
                )
            except (
                observer.V075PrivateObserverBoundaryV2InvariantViolation
            ) as error:
                raise V075ObserverSignedBatchControlV2InvariantViolation(
                    str(error)
                ) from error
        request = batch.request
        receipt = self.receipt
        intent = self.intent
        if (
            intent.prior_head_id != self.prior_head.head_id
            or intent.occurrence_id != request.occurrence_id
            or intent.session_public_id != request.session_public_id
            or intent.observer_open_binding_id
            != request.authority_binding.binding_id
            or intent.stream_identity != request.stream_identity
            or intent.accepted_draw_start != request.accepted_draw_start
            or intent.accepted_draw_count != request.accepted_draw_count
            or intent.accepted_draw_cap != request.accepted_draw_cap
            or receipt.occurrence_id != request.occurrence_id
            or receipt.session_public_id != request.session_public_id
            or receipt.authority_binding != request.authority_binding
            or receipt.prior_head_id != self.prior_head.head_id
            or receipt.intent_id != intent.intent_id
            or receipt.semantic_authority_binding_id
            != intent.semantic_authority.binding_id
            or receipt.batch_id != batch.batch_id
            or receipt.batch_request_id != request.request_id
            or receipt.resulting_head_id != self.resulting_head.head_id
            or self.resulting_head.entry_count
            != self.prior_head.entry_count + 1
            or receipt.journal_sequence_number
            != self.resulting_head.entry_count
            or self.prior_head.occurrence_id
            != self.resulting_head.occurrence_id
            or self.prior_head.session_public_id
            != self.resulting_head.session_public_id
            or self.prior_head.authority_binding
            != self.resulting_head.authority_binding
        ):
            _fail("controlled batch append was stale, mixed, or transplanted")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_controlled_batch_append.v2",
            "schema_version": SCHEMA_VERSION,
            "prior_head_id": self.prior_head.head_id,
            "intent_id": self.intent.intent_id,
            "signed_batch_id": self.batch.batch_id,
            "resulting_head_id": self.resulting_head.head_id,
            "append_receipt_id": self.receipt.receipt_id,
            "observer_signatures_verified": 4,
            "private_material_serialized": False,
        }


def _complete_support_representatives(
    batch: observer.V075SignedObservationBatchV2,
) -> tuple[
    tuple[
        str,
        graph.V075SymbolicGraphStateV1,
        observer.V075BatchOutcomeAggregateV2,
    ],
    ...,
]:
    try:
        batch = observer.replay_signed_observation_batch_object_v2(batch)
        return _complete_support_representatives_from_exact_batch(batch)
    except (
        AttributeError,
        TypeError,
        ValueError,
        graph.V075PublicGraphSemanticsInvariantViolation,
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
    ) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "complete support representative reconstruction failed"
        ) from error


def _complete_support_representatives_from_exact_batch(
    batch: observer.V075SignedObservationBatchV2,
) -> tuple[
    tuple[
        str,
        graph.V075SymbolicGraphStateV1,
        observer.V075BatchOutcomeAggregateV2,
    ],
    ...,
]:
    try:
        if type(batch) is not observer.V075SignedObservationBatchV2:
            _fail("complete support requires one exact signed batch")
        stream = batch.request.stream_identity
        if (
            stream.lane is not graph.V075ObservationLaneV1.DISCOVERY
            or stream.pairing_authority.support_chain.leaf.evidence
        ):
            _fail("complete support requires one bootstrap DISCOVERY batch")
        by_state: dict[
            str,
            tuple[
                graph.V075SymbolicGraphStateV1,
                observer.V075BatchOutcomeAggregateV2,
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
            _fail("complete support is empty or exceeds its hard cap")
        return tuple(
            (state_id, *by_state[state_id])
            for state_id in sorted(by_state)
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
        graph.V075PublicGraphSemanticsInvariantViolation,
    ) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "complete support representative reconstruction failed"
        ) from error


def _replay_aggregate_support_evidence(
    claimed: graph.V075BatchAggregateSupportEvidenceV1,
    *,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    row_binding: graph.V075ObservationRowBindingV1,
) -> graph.V075BatchAggregateSupportEvidenceV1:
    if type(claimed) is not graph.V075BatchAggregateSupportEvidenceV1:
        _fail("support freeze evidence has a foreign concrete type")
    try:
        state = graph.V075SymbolicGraphStateV1(
            row_binding.context,
            claimed.observed_state.ranks,
            claimed.observed_state.failure,
        )
        replayed = graph.V075BatchAggregateSupportEvidenceV1(
            namespace,
            row_binding,
            state,
            claimed.source_observer_epoch_index,
            claimed.discovery_request_id,
            claimed.discovery_batch_id,
            claimed.discovery_outcome_id,
            claimed.discovery_outcome_count,
            claimed.observer_signature_hex,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("support evidence differs from exact reconstruction")
        return replayed
    except (
        AttributeError,
        TypeError,
        ValueError,
        graph.V075PublicGraphSemanticsInvariantViolation,
    ) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "support evidence reconstruction failed"
        ) from error


def _support_freeze_payload(
    *,
    discovery_append: V075ControlledBatchAppendV2,
    frozen_at_head: V075SignedBatchJournalHeadV2,
    evidence: tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
) -> dict[str, Any]:
    batch = discovery_append.batch
    request = batch.request
    stream = request.stream_identity
    return {
        "schema": "acfqp.v075_controlled_complete_support_freeze.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "occurrence_id": request.occurrence_id,
        "observer_session_public_id": request.session_public_id,
        "observer_open_binding_id": request.authority_binding.binding_id,
        "target_tape_namespace_id": stream.target_tape_namespace_id,
        "context_id": stream.context_id,
        "row_binding_id": stream.row_binding_id,
        "discovery_stream_id": stream.stream_id,
        "discovery_intent_id": discovery_append.intent.intent_id,
        "discovery_append_receipt_id": (
            discovery_append.receipt.receipt_id
        ),
        "discovery_resulting_head_id": (
            discovery_append.resulting_head.head_id
        ),
        "discovery_request_id": request.request_id,
        "discovery_batch_id": batch.batch_id,
        "frozen_at_head_id": frozen_at_head.head_id,
        "frozen_after_append_count": frozen_at_head.entry_count,
        "source_observer_epoch_index": stream.observer_epoch_index,
        "validation_observer_epoch_index": stream.observer_epoch_index + 1,
        "evidence_ids": [item.evidence_id for item in evidence],
        "observed_state_ids": [
            item.observed_state.state_id for item in evidence
        ],
        "support_member_count": len(evidence),
        "all_discovery_outcomes_examined": True,
        "complete_symbolic_state_support": True,
        "spawn_aliases_deduplicated": True,
        "spawn_alias_representative_rule": "MIN_OUTCOME_ID",
        "caller_selected_support": False,
        "observer_owned_freeze_path": True,
        "same_open_controlled_session": True,
        "freeze_precedes_same_row_validation": True,
        "observer_signature_required": True,
        "official_execution_allowed": False,
        "process_isolation_provided": False,
        "private_material_serialized": False,
    }


_OWNED_SUPPORT_FREEZE_ISSUER = object()
_REPLAYED_SUPPORT_FREEZE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ControlledCompleteSupportFreezeV2:
    """Observer-signed complete symbolic support from one DISCOVERY append."""

    _issuer: object = field(repr=False, compare=False)
    discovery_append: V075ControlledBatchAppendV2 = field(repr=False)
    frozen_at_head: V075SignedBatchJournalHeadV2
    evidence: tuple[
        graph.V075BatchAggregateSupportEvidenceV1,
        ...,
    ] = field(repr=False)
    observer_signature_hex: str

    def __post_init__(self) -> None:
        append = self.discovery_append
        head = self.frozen_at_head
        if (
            self._issuer
            not in {
                _OWNED_SUPPORT_FREEZE_ISSUER,
                _REPLAYED_SUPPORT_FREEZE_ISSUER,
            }
            or type(append) is not V075ControlledBatchAppendV2
            or type(head) is not V075SignedBatchJournalHeadV2
        ):
            _fail("controlled complete support freeze is caller-minted")
        batch = append.batch
        request = batch.request
        stream = request.stream_identity
        if (
            append.resulting_head.entry_count > head.entry_count
            or append.resulting_head.occurrence_id != head.occurrence_id
            or append.resulting_head.session_public_id
            != head.session_public_id
            or append.resulting_head.authority_binding
            != head.authority_binding
            or type(self.evidence) is not tuple
            or not self.evidence
            or len(self.evidence) > graph.MAX_SUPPORT_MEMBERS_PER_ROW
            or stream.lane is not graph.V075ObservationLaneV1.DISCOVERY
            or append.intent.semantic_authority.stage
            not in {
                V075ControlledBatchStageV2.ROOT_DISCOVERY,
                V075ControlledBatchStageV2.CHILD_DISCOVERY,
            }
        ):
            _fail("controlled complete support freeze is malformed or late")
        replayed_evidence = tuple(
            sorted(
                self.evidence,
                key=lambda item: item.evidence_id,
            )
        )
        if (
            any(
                type(item)
                is not graph.V075BatchAggregateSupportEvidenceV1
                for item in self.evidence
            )
            or replayed_evidence != self.evidence
        ):
            _fail("complete support evidence is reordered or duplicated")
        expected = _complete_support_representatives_from_exact_batch(batch)
        by_state = {
            item.observed_state.state_id: item
            for item in replayed_evidence
        }
        if (
            len(by_state) != len(replayed_evidence)
            or set(by_state) != {item[0] for item in expected}
        ):
            _fail("complete support omitted or multiplied an observed state")
        for state_id, state, outcome in expected:
            item = by_state[state_id]
            if (
                item.namespace != request.authority_binding.namespace
                or item.row_binding != stream.row_binding
                or item.observed_state != state
                or item.source_observer_epoch_index
                != stream.observer_epoch_index
                or item.discovery_request_id != request.request_id
                or item.discovery_batch_id != batch.batch_id
                or item.discovery_outcome_id != outcome.outcome_id
                or item.discovery_outcome_count != outcome.count
            ):
                _fail("complete support uses a noncanonical representative")
        _verify_signature(
            binding=request.authority_binding,
            message=_signing_bytes(
                "support_freeze_signature",
                self._unsigned_payload(),
            ),
            signature_hex=self.observer_signature_hex,
        )

    def _unsigned_payload(self) -> dict[str, Any]:
        return _support_freeze_payload(
            discovery_append=self.discovery_append,
            frozen_at_head=self.frozen_at_head,
            evidence=self.evidence,
        )

    @property
    def freeze_id(self) -> str:
        return _hash(
            "support_freeze",
            {
                **self._unsigned_payload(),
                "observer_signature_hex": self.observer_signature_hex,
                "observer_signature_verified": True,
            },
        )

    @property
    def row_binding_id(self) -> str:
        return self.discovery_append.batch.request.stream_identity.row_binding_id

    @property
    def discovery_append_receipt_id(self) -> str:
        return self.discovery_append.receipt.receipt_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._unsigned_payload(),
            "evidence": [item.to_document() for item in self.evidence],
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "freeze_id": self.freeze_id,
        }


def _replay_support_freeze(
    claimed: V075ControlledCompleteSupportFreezeV2,
) -> V075ControlledCompleteSupportFreezeV2:
    if type(claimed) is not V075ControlledCompleteSupportFreezeV2:
        _fail("support freeze replay requires one exact concrete type")
    try:
        append = _replay_append(claimed.discovery_append)
        head = _replay_signed_head(claimed.frozen_at_head)
        stream = append.batch.request.stream_identity
        evidence = tuple(
            _replay_aggregate_support_evidence(
                item,
                namespace=append.batch.request.authority_binding.namespace,
                row_binding=stream.row_binding,
            )
            for item in claimed.evidence
        )
        replayed = V075ControlledCompleteSupportFreezeV2(
            _REPLAYED_SUPPORT_FREEZE_ISSUER,
            append,
            head,
            evidence,
            claimed.observer_signature_hex,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("support freeze differs from exact reconstruction")
        return replayed
    except (AttributeError, TypeError, ValueError) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "support freeze reconstruction failed"
        ) from error


def _replay_support_freeze_against_prefix(
    claimed: V075ControlledCompleteSupportFreezeV2,
    *,
    discovery_append: V075ControlledBatchAppendV2,
    frozen_at_head: V075SignedBatchJournalHeadV2,
) -> V075ControlledCompleteSupportFreezeV2:
    """Replay a freeze while reusing exact append/head prefix objects."""

    if type(claimed) is not V075ControlledCompleteSupportFreezeV2:
        _fail("support freeze replay requires one exact concrete type")
    try:
        if (
            claimed.discovery_append != discovery_append
            or claimed.discovery_append.to_document()
            != discovery_append.to_document()
            or claimed.frozen_at_head != frozen_at_head
            or claimed.frozen_at_head.to_document()
            != frozen_at_head.to_document()
        ):
            _fail("support freeze embeds a foreign append or head")
        stream = discovery_append.batch.request.stream_identity
        evidence = tuple(
            _replay_aggregate_support_evidence(
                item,
                namespace=(
                    discovery_append.batch.request.authority_binding.namespace
                ),
                row_binding=stream.row_binding,
            )
            for item in claimed.evidence
        )
        replayed = V075ControlledCompleteSupportFreezeV2(
            _REPLAYED_SUPPORT_FREEZE_ISSUER,
            discovery_append,
            frozen_at_head,
            evidence,
            claimed.observer_signature_hex,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("support freeze differs from exact reconstruction")
        return replayed
    except (AttributeError, TypeError, ValueError) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "support freeze reconstruction failed"
        ) from error


def derive_v075_controlled_validation_stream_v2(
    *,
    support_freeze: V075ControlledCompleteSupportFreezeV2,
) -> graph.V075TransitionStreamIdentityV1:
    """Derive the sole next-epoch VALIDATION stream admitted by a freeze."""

    support = _replay_support_freeze(support_freeze)
    return _derive_validation_stream_from_owned_support_freeze(support)


def _derive_validation_stream_from_owned_support_freeze(
    support: V075ControlledCompleteSupportFreezeV2,
) -> graph.V075TransitionStreamIdentityV1:
    if type(support) is not V075ControlledCompleteSupportFreezeV2:
        _fail("owned validation derivation requires one exact support freeze")
    discovery = support.discovery_append.batch.request.stream_identity
    chain = discovery.pairing_authority.support_chain
    source = chain.leaf
    if (
        source.epoch_index != discovery.observer_epoch_index
        or source.required_lane is not graph.V075ObservationLaneV1.DISCOVERY
        or source.evidence
    ):
        _fail("support freeze discovery stream lacks an empty bootstrap leaf")
    try:
        promoted = graph.derive_shared_support_epoch_v1(
            namespace=discovery.namespace,
            row_binding=discovery.row_binding,
            epoch_index=source.epoch_index + 1,
            evidence=support.evidence,
            parent=source,
        )
        promoted_chain = graph.freeze_shared_support_chain_v1(
            namespace=discovery.namespace,
            row_binding=discovery.row_binding,
            epochs=(*chain.epochs, promoted),
        )
        pairing = graph.freeze_five_arm_pairing_authority_v1(
            namespace=discovery.namespace,
            row_binding=discovery.row_binding,
            support_chain=promoted_chain,
        )
        return graph.derive_transition_stream_identity_v1(
            pairing_authority=pairing,
            arm=discovery.arm,
        )
    except graph.V075PublicGraphSemanticsInvariantViolation as error:
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "controlled validation stream derivation failed"
        ) from error


def _control_closure_payload(
    *,
    occurrence_id: str,
    session_public_id: str,
    authority_binding: observer.V075ObserverOpenAuthorityBindingV2,
    zero_head_id: str,
    final_head_id: str,
    head_ids: tuple[str, ...],
    intent_ids: tuple[str, ...],
    semantic_authority_binding_ids: tuple[str, ...],
    support_freeze_ids: tuple[str, ...],
    receipt_ids: tuple[str, ...],
    batch_closure_id: str,
    batch_ids: tuple[str, ...],
    journal_entry_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_observer_signed_batch_control_closure.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "occurrence_id": occurrence_id,
        "observer_session_public_id": session_public_id,
        "observer_open_binding_id": authority_binding.binding_id,
        "observer_open_authorization_id": authority_binding.authorization_id,
        "target_tape_namespace_id": (
            authority_binding.namespace.target_tape_namespace_id
        ),
        "zero_head_id": zero_head_id,
        "final_head_id": final_head_id,
        "head_ids": list(head_ids),
        "intent_ids": list(intent_ids),
        "semantic_authority_binding_ids": list(
            semantic_authority_binding_ids
        ),
        "support_freeze_ids": list(support_freeze_ids),
        "support_freeze_count": len(support_freeze_ids),
        "append_receipt_ids": list(receipt_ids),
        "batch_journal_closure_id": batch_closure_id,
        "signed_batch_ids": list(batch_ids),
        "journal_entry_ids": list(journal_entry_ids),
        "append_count": len(receipt_ids),
        "signed_head_count": len(head_ids),
        "control_chain_closed": True,
        "batch_closure_reconciliation_required": True,
        "construction_wrapper_retains_signer_reference_until_both_closures": (
            True
        ),
        "caller_also_retains_signer_reference": True,
        "exclusive_signer_ownership_proven": False,
        "single_private_boundary_atomicity_proven": False,
        "private_material_serialized": False,
    }


@dataclass(frozen=True, slots=True)
class V075ObserverSignedBatchControlClosureV2:
    """Observer signature binding the whole control chain to batch closure."""

    occurrence_id: str
    session_public_id: str
    authority_binding: observer.V075ObserverOpenAuthorityBindingV2 = field(
        repr=False
    )
    zero_head_id: str
    final_head_id: str
    head_ids: tuple[str, ...]
    intent_ids: tuple[str, ...]
    semantic_authority_binding_ids: tuple[str, ...]
    support_freeze_ids: tuple[str, ...]
    receipt_ids: tuple[str, ...]
    batch_closure_id: str
    batch_ids: tuple[str, ...]
    journal_entry_ids: tuple[str, ...]
    observer_signature_hex: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "control-closure occurrence"),
            (self.session_public_id, "control-closure session"),
            (self.zero_head_id, "control-closure zero head"),
            (self.final_head_id, "control-closure final head"),
            (self.batch_closure_id, "control-closure batch closure"),
        ):
            _cid(value, label)
        if (
            type(self.authority_binding)
            is not observer.V075ObserverOpenAuthorityBindingV2
            or type(self.head_ids) is not tuple
            or type(self.intent_ids) is not tuple
            or type(self.receipt_ids) is not tuple
            or type(self.semantic_authority_binding_ids) is not tuple
            or type(self.support_freeze_ids) is not tuple
            or type(self.batch_ids) is not tuple
            or type(self.journal_entry_ids) is not tuple
            or not self.receipt_ids
            or len(self.head_ids) != len(self.receipt_ids) + 1
            or len(self.intent_ids) != len(self.receipt_ids)
            or len(self.semantic_authority_binding_ids)
            != len(self.receipt_ids)
            or len(self.batch_ids) != len(self.receipt_ids)
            or len(self.journal_entry_ids) != len(self.receipt_ids)
            or self.head_ids[0] != self.zero_head_id
            or self.head_ids[-1] != self.final_head_id
            or any(
                _cid(item, "control-closure chain member") != item
                for collection in (
                    self.head_ids,
                    self.intent_ids,
                    self.semantic_authority_binding_ids,
                    self.support_freeze_ids,
                    self.receipt_ids,
                    self.batch_ids,
                    self.journal_entry_ids,
                )
                for item in collection
            )
            or any(
                len(set(collection)) != len(collection)
                for collection in (
                    self.head_ids,
                    self.intent_ids,
                    self.support_freeze_ids,
                    self.receipt_ids,
                    self.batch_ids,
                    self.journal_entry_ids,
                )
            )
        ):
            _fail("observer-signed control closure is malformed")
        _verify_signature(
            binding=self.authority_binding,
            message=_signing_bytes(
                "control_closure_signature",
                self._unsigned_payload(),
            ),
            signature_hex=self.observer_signature_hex,
        )

    def _unsigned_payload(self) -> dict[str, Any]:
        return _control_closure_payload(
            occurrence_id=self.occurrence_id,
            session_public_id=self.session_public_id,
            authority_binding=self.authority_binding,
            zero_head_id=self.zero_head_id,
            final_head_id=self.final_head_id,
            head_ids=self.head_ids,
            intent_ids=self.intent_ids,
            semantic_authority_binding_ids=(
                self.semantic_authority_binding_ids
            ),
            support_freeze_ids=self.support_freeze_ids,
            receipt_ids=self.receipt_ids,
            batch_closure_id=self.batch_closure_id,
            batch_ids=self.batch_ids,
            journal_entry_ids=self.journal_entry_ids,
        )

    @property
    def control_closure_id(self) -> str:
        return _hash(
            "control_closure",
            {
                **self._unsigned_payload(),
                "observer_signature_hex": self.observer_signature_hex,
                "observer_signature_verified": True,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._unsigned_payload(),
            "observer_open_binding": self.authority_binding.to_document(),
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "control_closure_id": self.control_closure_id,
        }


_RECONCILIATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075SignedBatchControlReconciliationV2:
    """Verifier-issued complete chain/closure reconciliation."""

    _issuer: object = field(repr=False, compare=False)
    occurrence_id: str
    session_public_id: str
    control_closure_id: str
    batch_closure_id: str
    zero_head_id: str
    final_head_id: str
    append_count: int
    total_accepted_draw_count: int
    _reconciliation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "reconciled occurrence"),
            (self.session_public_id, "reconciled session"),
            (self.control_closure_id, "reconciled control closure"),
            (self.batch_closure_id, "reconciled batch closure"),
            (self.zero_head_id, "reconciled zero head"),
            (self.final_head_id, "reconciled final head"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _RECONCILIATION_ISSUER
            or type(self.append_count) is not int
            or self.append_count <= 0
            or type(self.total_accepted_draw_count) is not int
            or self.total_accepted_draw_count <= 0
        ):
            _fail("batch-control reconciliation is caller-minted or empty")
        object.__setattr__(
            self,
            "_reconciliation_id",
            _hash("reconciliation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_observer_signed_batch_control_reconciliation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "observer_session_public_id": self.session_public_id,
            "control_closure_id": self.control_closure_id,
            "batch_journal_closure_id": self.batch_closure_id,
            "zero_head_id": self.zero_head_id,
            "final_head_id": self.final_head_id,
            "append_count": self.append_count,
            "total_accepted_draw_count": (
                self.total_accepted_draw_count
            ),
            "zero_head_signature_verified": True,
            "all_head_signatures_verified": True,
            "all_batch_signatures_verified": True,
            "all_append_receipt_signatures_verified": True,
            "batch_closure_signature_verified": True,
            "control_closure_signature_verified": True,
            "head_intent_append_order_reconciled": True,
            "batch_journal_exactly_reconciled": True,
            "accepted_chain_raw_out_of_band_append_count": 0,
            "accepted_chain_stale_or_reused_intent_count": 0,
            "accepted_chain_gap_or_cap_change_count": 0,
            "production_authorizing": False,
            "official_execution_allowed": False,
            "process_isolation_provided": False,
            "python_wrapper_is_not_process_isolation": True,
            "trusted_in_process_wrapper_order_replayed": True,
            "single_private_boundary_atomicity_proven": False,
            "exclusive_signer_ownership_proven": False,
            "wrapper_signer_reference_cleared_after_both_closures": True,
            "semantic_authority_reference_status": "OPAQUE_DEFERRED",
            "terminal_class": TERMINAL_CLASS,
        }

    @property
    def reconciliation_id(self) -> str:
        return self._reconciliation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "reconciliation_id": self.reconciliation_id,
        }


_OWNED_CLOSED_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ControlledBatchJournalClosureV2:
    """Exact normal batch closure plus independently checked control chain."""

    batch_closure: observer.V075ObserverBatchJournalClosureV2 = field(
        repr=False
    )
    heads: tuple[V075SignedBatchJournalHeadV2, ...]
    appends: tuple[V075ControlledBatchAppendV2, ...] = field(repr=False)
    control_closure: V075ObserverSignedBatchControlClosureV2
    reconciliation: V075SignedBatchControlReconciliationV2
    support_freezes: tuple[
        V075ControlledCompleteSupportFreezeV2,
        ...,
    ] = field(default=(), repr=False)
    _exact_reconciliation_issuer: InitVar[object | None] = None

    def __post_init__(
        self,
        _exact_reconciliation_issuer: object | None,
    ) -> None:
        if (
            type(self.batch_closure)
            is not observer.V075ObserverBatchJournalClosureV2
            or type(self.heads) is not tuple
            or any(
                type(item) is not V075SignedBatchJournalHeadV2
                for item in self.heads
            )
            or type(self.appends) is not tuple
            or any(
                type(item) is not V075ControlledBatchAppendV2
                for item in self.appends
            )
            or type(self.control_closure)
            is not V075ObserverSignedBatchControlClosureV2
            or type(self.reconciliation)
            is not V075SignedBatchControlReconciliationV2
            or type(self.support_freezes) is not tuple
            or any(
                type(item) is not V075ControlledCompleteSupportFreezeV2
                for item in self.support_freezes
            )
        ):
            _fail("controlled batch journal closure graph is untyped")
        if _exact_reconciliation_issuer is _OWNED_CLOSED_RESULT_ISSUER:
            replayed = self.reconciliation
            if (
                replayed.occurrence_id != self.batch_closure.occurrence_id
                or replayed.session_public_id
                != self.batch_closure.session_public_id
                or replayed.batch_closure_id != self.batch_closure.closure_id
                or replayed.control_closure_id
                != self.control_closure.control_closure_id
                or replayed.zero_head_id != self.heads[0].head_id
                or replayed.final_head_id != self.heads[-1].head_id
                or replayed.append_count != len(self.appends)
                or replayed.total_accepted_draw_count
                != self.heads[-1].total_accepted_draw_count
                or self.control_closure.support_freeze_ids
                != tuple(item.freeze_id for item in self.support_freezes)
            ):
                _fail("owned closed result differs from exact reconciliation")
        else:
            replayed = _verify_controlled_closure_graph(
                batch_closure=self.batch_closure,
                heads=self.heads,
                appends=self.appends,
                control_closure=self.control_closure,
                support_freezes=self.support_freezes,
            )
        if replayed != self.reconciliation:
            _fail("claimed batch-control reconciliation differs from replay")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_controlled_batch_journal_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "batch_journal_closure_id": self.batch_closure.closure_id,
            "control_closure_id": self.control_closure.control_closure_id,
            "reconciliation_id": self.reconciliation.reconciliation_id,
            "head_ids": [item.head_id for item in self.heads],
            "intent_ids": [
                item.intent.intent_id for item in self.appends
            ],
            "append_receipt_ids": [
                item.receipt.receipt_id for item in self.appends
            ],
            "support_freeze_ids": [
                item.freeze_id for item in self.support_freezes
            ],
            "support_freeze_count": len(self.support_freezes),
            "official_execution_allowed": False,
            "production_authorizing": False,
            "process_isolation_provided": False,
            "python_wrapper_is_not_process_isolation": True,
            "trusted_in_process_wrapper_order_replayed": True,
            "single_private_boundary_atomicity_proven": False,
            "exclusive_signer_ownership_proven": False,
            "wrapper_signer_reference_cleared_after_both_closures": True,
            "terminal_class": TERMINAL_CLASS,
        }


def _derive_frontiers(
    entries: tuple[observer.V075ObserverBatchJournalEntryV2, ...],
) -> tuple[V075BatchStreamFrontierV2, ...]:
    state: dict[str, V075BatchStreamFrontierV2] = {}
    expected_previous: str | None = None
    for sequence_number, entry in enumerate(entries, start=1):
        if (
            type(entry) is not observer.V075ObserverBatchJournalEntryV2
            or entry.sequence_number != sequence_number
            or entry.previous_entry_id != expected_previous
        ):
            _fail("controlled observer journal is reordered or gapped")
        try:
            batch = observer.replay_signed_observation_batch_object_v2(
                entry.batch
            )
        except observer.V075PrivateObserverBoundaryV2InvariantViolation as error:
            raise V075ObserverSignedBatchControlV2InvariantViolation(
                str(error)
            ) from error
        _advance_frontier_state_from_exact_batch(state=state, batch=batch)
        expected_previous = entry.entry_id
    return tuple(sorted(state.values(), key=lambda item: item.stream_id))


def _advance_frontier_state_from_exact_batch(
    *,
    state: dict[str, V075BatchStreamFrontierV2],
    batch: observer.V075SignedObservationBatchV2,
) -> tuple[V075BatchStreamFrontierV2, ...]:
    if (
        type(state) is not dict
        or type(batch) is not observer.V075SignedObservationBatchV2
    ):
        _fail("exact frontier advance received a foreign object")
    request = batch.request
    stream_id = request.stream_identity.stream_id
    prior = state.get(stream_id)
    if (
        request.accepted_draw_start
        != (1 if prior is None else prior.accepted_draw_end + 1)
        or (
            prior is not None
            and request.accepted_draw_cap != prior.accepted_draw_cap
        )
        or (
            prior is not None
            and request.stream_identity.row_binding_id != prior.row_binding_id
        )
    ):
        _fail("controlled observer stream changed cap, row, or prefix")
    state[stream_id] = V075BatchStreamFrontierV2(
        stream_id,
        request.stream_identity.row_binding_id,
        request.accepted_draw_cap,
        request.accepted_draw_end,
        1 if prior is None else prior.batch_count + 1,
        request.request_id,
        batch.batch_id,
    )
    return tuple(sorted(state.values(), key=lambda item: item.stream_id))


def _derive_frontiers_from_owned_entries(
    entries: tuple[observer.V075ObserverBatchJournalEntryV2, ...],
) -> tuple[V075BatchStreamFrontierV2, ...]:
    state: dict[str, V075BatchStreamFrontierV2] = {}
    expected_previous: str | None = None
    for sequence_number, entry in enumerate(entries, start=1):
        if (
            type(entry) is not observer.V075ObserverBatchJournalEntryV2
            or entry.sequence_number != sequence_number
            or entry.previous_entry_id != expected_previous
        ):
            _fail("owned observer journal is reordered or gapped")
        _advance_frontier_state_from_exact_batch(
            state=state,
            batch=entry.batch,
        )
        expected_previous = entry.entry_id
    return tuple(sorted(state.values(), key=lambda item: item.stream_id))


def _expected_next_from_head(
    *,
    head: V075SignedBatchJournalHeadV2,
    stream_id: str,
    requested_cap: int,
) -> int:
    by_stream = {item.stream_id: item for item in head.stream_frontiers}
    prior = by_stream.get(stream_id)
    if prior is None:
        return 1
    if prior.accepted_draw_cap != requested_cap:
        _fail("controlled exact batch intent changes a frozen stream cap")
    return prior.next_accepted_draw_index


def _replay_signed_head(
    claimed: V075SignedBatchJournalHeadV2,
) -> V075SignedBatchJournalHeadV2:
    if type(claimed) is not V075SignedBatchJournalHeadV2:
        _fail("signed journal head replay requires one exact concrete type")
    try:
        frontiers = tuple(
            V075BatchStreamFrontierV2(
                item.stream_id,
                item.row_binding_id,
                item.accepted_draw_cap,
                item.accepted_draw_end,
                item.batch_count,
                item.last_request_id,
                item.last_batch_id,
            )
            for item in claimed.stream_frontiers
        )
        replayed = V075SignedBatchJournalHeadV2(
            claimed.occurrence_id,
            claimed.session_public_id,
            claimed.authority_binding,
            claimed.entry_count,
            claimed.tail_entry_id,
            claimed.total_accepted_draw_count,
            frontiers,
            claimed.observer_signature_hex,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("signed journal head differs from exact reconstruction")
        return replayed
    except (AttributeError, TypeError, ValueError) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "signed journal head reconstruction failed"
        ) from error


def _replay_semantic_authority(
    claimed: V075ControlledBatchSemanticAuthorityBindingV2,
) -> V075ControlledBatchSemanticAuthorityBindingV2:
    if (
        type(claimed)
        is not V075ControlledBatchSemanticAuthorityBindingV2
    ):
        _fail("semantic authority replay requires one exact concrete type")
    try:
        replayed = V075ControlledBatchSemanticAuthorityBindingV2(
            _SEMANTIC_AUTHORITY_ISSUER,
            claimed.role,
            claimed.schema,
            claimed.semantic_artifact_id,
            claimed.semantic_verification_id,
            claimed.stage,
            claimed.round_index,
            claimed.support_freeze_id,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("semantic authority differs from exact reconstruction")
        return replayed
    except (AttributeError, TypeError, ValueError) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "semantic authority reconstruction failed"
        ) from error


def _replay_intent(
    claimed: V075HeadBoundExactBatchIntentV2,
) -> V075HeadBoundExactBatchIntentV2:
    if type(claimed) is not V075HeadBoundExactBatchIntentV2:
        _fail("batch intent replay requires one exact concrete type")
    try:
        semantic_authority = _replay_semantic_authority(
            claimed.semantic_authority
        )
        stream = observer._replay_v2_stream_identity(  # noqa: SLF001
            claimed.stream_identity
        )
        replayed = V075HeadBoundExactBatchIntentV2(
            _INTENT_ISSUER,
            claimed.prior_head_id,
            claimed.occurrence_id,
            claimed.session_public_id,
            claimed.observer_open_binding_id,
            semantic_authority,
            stream,
            claimed.accepted_draw_start,
            claimed.accepted_draw_count,
            claimed.accepted_draw_cap,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("batch intent differs from exact reconstruction")
        return replayed
    except (
        AttributeError,
        TypeError,
        ValueError,
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
    ) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "batch intent reconstruction failed"
        ) from error


def _replay_intent_against_stream(
    claimed: V075HeadBoundExactBatchIntentV2,
    *,
    stream: graph.V075TransitionStreamIdentityV1,
) -> V075HeadBoundExactBatchIntentV2:
    """Replay an intent while reusing an exact batch-reconstructed stream."""

    if (
        type(claimed) is not V075HeadBoundExactBatchIntentV2
        or type(stream) is not graph.V075TransitionStreamIdentityV1
    ):
        _fail("batch intent/stream replay requires exact concrete types")
    try:
        if (
            claimed.stream_identity != stream
            or claimed.stream_identity.to_document() != stream.to_document()
        ):
            _fail("batch intent embeds a foreign stream")
        semantic_authority = _replay_semantic_authority(
            claimed.semantic_authority
        )
        replayed = V075HeadBoundExactBatchIntentV2(
            _INTENT_ISSUER,
            claimed.prior_head_id,
            claimed.occurrence_id,
            claimed.session_public_id,
            claimed.observer_open_binding_id,
            semantic_authority,
            stream,
            claimed.accepted_draw_start,
            claimed.accepted_draw_count,
            claimed.accepted_draw_cap,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("batch intent differs from exact reconstruction")
        return replayed
    except (AttributeError, TypeError, ValueError) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "batch intent reconstruction failed"
        ) from error


def _replay_receipt(
    claimed: V075ObserverSignedBatchAppendReceiptV2,
) -> V075ObserverSignedBatchAppendReceiptV2:
    if type(claimed) is not V075ObserverSignedBatchAppendReceiptV2:
        _fail("append receipt replay requires one exact concrete type")
    try:
        replayed = V075ObserverSignedBatchAppendReceiptV2(
            claimed.occurrence_id,
            claimed.session_public_id,
            claimed.authority_binding,
            claimed.prior_head_id,
            claimed.intent_id,
            claimed.semantic_authority_binding_id,
            claimed.batch_id,
            claimed.batch_request_id,
            claimed.journal_entry_id,
            claimed.journal_sequence_number,
            claimed.resulting_head_id,
            claimed.observer_signature_hex,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("append receipt differs from exact reconstruction")
        return replayed
    except (AttributeError, TypeError, ValueError) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "append receipt reconstruction failed"
        ) from error


def _replay_append(
    claimed: V075ControlledBatchAppendV2,
) -> V075ControlledBatchAppendV2:
    if type(claimed) is not V075ControlledBatchAppendV2:
        _fail("controlled append replay requires one exact concrete type")
    try:
        replayed_batch = (
            observer.replay_signed_observation_batch_object_v2(
                claimed.batch
            )
        )
        replayed = V075ControlledBatchAppendV2(
            _replay_signed_head(claimed.prior_head),
            _replay_intent_against_stream(
                claimed.intent,
                stream=replayed_batch.request.stream_identity,
            ),
            replayed_batch,
            _replay_signed_head(claimed.resulting_head),
            _replay_receipt(claimed.receipt),
            _REPLAYED_APPEND_ISSUER,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("controlled append differs from exact reconstruction")
        return replayed
    except (
        AttributeError,
        TypeError,
        ValueError,
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
    ) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "controlled append reconstruction failed"
        ) from error


def _replay_append_against_heads(
    claimed: V075ControlledBatchAppendV2,
    *,
    prior_head: V075SignedBatchJournalHeadV2,
    resulting_head: V075SignedBatchJournalHeadV2,
) -> V075ControlledBatchAppendV2:
    """Replay one append while reusing already reconstructed chain heads."""

    if type(claimed) is not V075ControlledBatchAppendV2:
        _fail("controlled append replay requires one exact concrete type")
    try:
        if (
            claimed.prior_head != prior_head
            or claimed.prior_head.to_document()
            != prior_head.to_document()
            or claimed.resulting_head != resulting_head
            or claimed.resulting_head.to_document()
            != resulting_head.to_document()
        ):
            _fail("controlled append embeds a foreign head")
        replayed_batch = (
            observer.replay_signed_observation_batch_object_v2(
                claimed.batch
            )
        )
        replayed = V075ControlledBatchAppendV2(
            prior_head,
            _replay_intent_against_stream(
                claimed.intent,
                stream=replayed_batch.request.stream_identity,
            ),
            replayed_batch,
            resulting_head,
            _replay_receipt(claimed.receipt),
            _REPLAYED_APPEND_ISSUER,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("controlled append differs from exact reconstruction")
        return replayed
    except (
        AttributeError,
        TypeError,
        ValueError,
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
    ) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "controlled append reconstruction failed"
        ) from error


def _replay_batch_closure(
    claimed: observer.V075ObserverBatchJournalClosureV2,
) -> observer.V075ObserverBatchJournalClosureV2:
    if (
        type(claimed)
        is not observer.V075ObserverBatchJournalClosureV2
    ):
        _fail("batch closure replay requires one exact concrete type")
    try:
        entries: list[observer.V075ObserverBatchJournalEntryV2] = []
        for claimed_entry in claimed.entries:
            if (
                type(claimed_entry)
                is not observer.V075ObserverBatchJournalEntryV2
            ):
                _fail("batch closure contains a foreign entry type")
            replayed_batch = (
                observer.replay_signed_observation_batch_object_v2(
                    claimed_entry.batch
                )
            )
            replayed_entry = observer.V075ObserverBatchJournalEntryV2(
                claimed_entry.sequence_number,
                claimed_entry.previous_entry_id,
                replayed_batch,
            )
            if (
                replayed_entry != claimed_entry
                or replayed_entry.to_document()
                != claimed_entry.to_document()
            ):
                _fail("batch journal entry differs from exact reconstruction")
            entries.append(replayed_entry)
        if not entries:
            _fail("controlled batch closure cannot be empty")
        first_request = entries[0].batch.request
        replayed = observer.V075ObserverBatchJournalClosureV2(
            first_request.occurrence_id,
            first_request.session_public_id,
            first_request.authority_binding,
            tuple(entries),
            claimed.observer_signature_hex,
        )
        if (
            replayed != claimed
            or replayed.canonical_bytes != claimed.canonical_bytes
        ):
            _fail("batch closure differs from exact reconstruction")
        return replayed
    except (
        AttributeError,
        TypeError,
        ValueError,
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
    ) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "batch closure reconstruction failed"
        ) from error


def _replay_batch_closure_against_appends(
    claimed: observer.V075ObserverBatchJournalClosureV2,
    *,
    appends: tuple[V075ControlledBatchAppendV2, ...],
) -> observer.V075ObserverBatchJournalClosureV2:
    """Replay closure structure/signature using exact prefix-replayed batches."""

    if (
        type(claimed)
        is not observer.V075ObserverBatchJournalClosureV2
        or type(appends) is not tuple
        or not appends
        or len(claimed.entries) != len(appends)
    ):
        _fail("batch closure/append replay graph is malformed")
    try:
        entries: list[observer.V075ObserverBatchJournalEntryV2] = []
        for index, (claimed_entry, append) in enumerate(
            zip(claimed.entries, appends, strict=True),
            start=1,
        ):
            if (
                type(claimed_entry)
                is not observer.V075ObserverBatchJournalEntryV2
                or claimed_entry.batch.batch_id != append.batch.batch_id
                or claimed_entry.batch.request.request_id
                != append.batch.request.request_id
                or claimed_entry.batch.observer_signature_hex
                != append.batch.observer_signature_hex
                or claimed_entry.batch.outcomes != append.batch.outcomes
            ):
                _fail("batch closure entry differs from replayed prefix batch")
            entry = observer.V075ObserverBatchJournalEntryV2(
                index,
                None if not entries else entries[-1].entry_id,
                append.batch,
            )
            if (
                entry.sequence_number != claimed_entry.sequence_number
                or entry.previous_entry_id != claimed_entry.previous_entry_id
                or entry.entry_id != claimed_entry.entry_id
            ):
                _fail("batch closure entry chain differs from replayed prefix")
            entries.append(entry)
        first_request = appends[0].batch.request
        replayed = observer.V075ObserverBatchJournalClosureV2(
            first_request.occurrence_id,
            first_request.session_public_id,
            first_request.authority_binding,
            tuple(entries),
            claimed.observer_signature_hex,
        )
        if replayed.closure_id != claimed.closure_id:
            _fail("batch closure differs from exact prefix reconstruction")
        return replayed
    except (
        AttributeError,
        TypeError,
        ValueError,
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
    ) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "batch closure reconstruction failed"
        ) from error


def _replay_control_closure(
    claimed: V075ObserverSignedBatchControlClosureV2,
) -> V075ObserverSignedBatchControlClosureV2:
    if (
        type(claimed)
        is not V075ObserverSignedBatchControlClosureV2
    ):
        _fail("control closure replay requires one exact concrete type")
    try:
        replayed = V075ObserverSignedBatchControlClosureV2(
            claimed.occurrence_id,
            claimed.session_public_id,
            claimed.authority_binding,
            claimed.zero_head_id,
            claimed.final_head_id,
            tuple(claimed.head_ids),
            tuple(claimed.intent_ids),
            tuple(claimed.semantic_authority_binding_ids),
            tuple(claimed.support_freeze_ids),
            tuple(claimed.receipt_ids),
            claimed.batch_closure_id,
            tuple(claimed.batch_ids),
            tuple(claimed.journal_entry_ids),
            claimed.observer_signature_hex,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("control closure differs from exact reconstruction")
        return replayed
    except (AttributeError, TypeError, ValueError) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "control closure reconstruction failed"
        ) from error


def _exact_open_prefix_components(
    *,
    heads: tuple[V075SignedBatchJournalHeadV2, ...],
    appends: tuple[V075ControlledBatchAppendV2, ...],
    support_freezes: tuple[
        V075ControlledCompleteSupportFreezeV2,
        ...,
    ],
) -> tuple[
    tuple[V075SignedBatchJournalHeadV2, ...],
    tuple[V075ControlledBatchAppendV2, ...],
    tuple[V075ControlledCompleteSupportFreezeV2, ...],
]:
    if (
        type(heads) is not tuple
        or type(appends) is not tuple
        or type(support_freezes) is not tuple
        or len(heads) != len(appends) + 1
        or not heads
    ):
        _fail("open controlled prefix has noncanonical container lengths")
    replayed_heads = tuple(_replay_signed_head(item) for item in heads)
    replayed_appends = tuple(
        _replay_append_against_heads(
            item,
            prior_head=replayed_heads[index],
            resulting_head=replayed_heads[index + 1],
        )
        for index, item in enumerate(appends)
    )
    append_by_receipt = {
        item.receipt.receipt_id: item for item in replayed_appends
    }
    head_by_id = {item.head_id: item for item in replayed_heads}
    try:
        replayed_freezes = tuple(
            _replay_support_freeze_against_prefix(
                item,
                discovery_append=append_by_receipt[
                    item.discovery_append.receipt.receipt_id
                ],
                frozen_at_head=head_by_id[item.frozen_at_head.head_id],
            )
            for item in support_freezes
        )
    except (AttributeError, KeyError) as error:
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "open-prefix support freeze cites a foreign append or head"
        ) from error
    if (
        replayed_heads[0].entry_count != 0
        or replayed_heads[0].tail_entry_id is not None
        or replayed_heads[0].stream_frontiers
        or replayed_freezes
        != tuple(
            sorted(
                replayed_freezes,
                key=lambda item: (
                    item.frozen_at_head.entry_count,
                    item.row_binding_id,
                    item.freeze_id,
                ),
            )
        )
    ):
        _fail("open controlled prefix lacks H0 or canonical freeze order")

    occurrence_id = replayed_heads[0].occurrence_id
    session_public_id = replayed_heads[0].session_public_id
    binding = replayed_heads[0].authority_binding
    entries: list[observer.V075ObserverBatchJournalEntryV2] = []
    previous_entry_id: str | None = None
    frontier_state: dict[str, V075BatchStreamFrontierV2] = {}
    for index, append in enumerate(replayed_appends, start=1):
        entry = observer.V075ObserverBatchJournalEntryV2(
            index,
            previous_entry_id,
            append.batch,
        )
        entries.append(entry)
        expected_frontiers = _advance_frontier_state_from_exact_batch(
            state=frontier_state,
            batch=append.batch,
        )
        prior = replayed_heads[index - 1]
        resulting = replayed_heads[index]
        if (
            append.prior_head != prior
            or append.resulting_head != resulting
            or append.receipt.journal_entry_id != entry.entry_id
            or append.receipt.journal_sequence_number != index
            or prior.occurrence_id != occurrence_id
            or prior.session_public_id != session_public_id
            or prior.authority_binding != binding
            or resulting.occurrence_id != occurrence_id
            or resulting.session_public_id != session_public_id
            or resulting.authority_binding != binding
            or resulting.entry_count != index
            or resulting.tail_entry_id != entry.entry_id
            or resulting.stream_frontiers != expected_frontiers
            or resulting.total_accepted_draw_count
            != sum(
                item.batch.request.accepted_draw_count for item in entries
            )
        ):
            _fail("open controlled prefix head/append chain is inconsistent")
        previous_entry_id = entry.entry_id

    freeze_ids: set[str] = set()
    freeze_rows: set[str] = set()
    freeze_receipts: set[str] = set()
    append_index_by_receipt = {
        item.receipt.receipt_id: index
        for index, item in enumerate(replayed_appends, start=1)
    }
    for support in replayed_freezes:
        receipt_id = support.discovery_append_receipt_id
        discovery_index = append_index_by_receipt.get(receipt_id)
        row_id = support.row_binding_id
        if (
            support.freeze_id in freeze_ids
            or row_id in freeze_rows
            or receipt_id in freeze_receipts
            or discovery_index is None
            or replayed_appends[discovery_index - 1]
            != support.discovery_append
            or support.frozen_at_head.entry_count >= len(replayed_heads)
            or support.frozen_at_head
            != replayed_heads[support.frozen_at_head.entry_count]
            or discovery_index > support.frozen_at_head.entry_count
            or support.frozen_at_head.occurrence_id != occurrence_id
            or support.frozen_at_head.session_public_id != session_public_id
            or support.frozen_at_head.authority_binding != binding
        ):
            _fail("open prefix support freeze is duplicated or transplanted")
        freeze_ids.add(support.freeze_id)
        freeze_rows.add(row_id)
        freeze_receipts.add(receipt_id)

    freeze_by_row = {
        item.row_binding_id: item for item in replayed_freezes
    }
    for index, append in enumerate(replayed_appends, start=1):
        stream = append.batch.request.stream_identity
        row_id = stream.row_binding_id
        support = freeze_by_row.get(row_id)
        if stream.lane is graph.V075ObservationLaneV1.VALIDATION:
            if (
                support is None
                or index <= support.frozen_at_head.entry_count
                or append.intent.semantic_authority.support_freeze_id
                != support.freeze_id
                or stream
                != _derive_validation_stream_from_owned_support_freeze(
                    support
                )
            ):
                _fail(
                    "validation append is not exactly downstream of its "
                    "same-row support freeze"
                )
        elif (
            support is not None
            and index > support.frozen_at_head.entry_count
            and stream.lane is graph.V075ObservationLaneV1.DISCOVERY
        ):
            _fail("same-row discovery continued after complete support freeze")
    discovery_rows = tuple(
        item.batch.request.stream_identity.row_binding_id
        for item in replayed_appends
        if item.batch.request.stream_identity.lane
        is graph.V075ObservationLaneV1.DISCOVERY
    )
    if len(discovery_rows) != len(set(discovery_rows)):
        _fail("open prefix repeats a same-row discovery append")
    return replayed_heads, replayed_appends, replayed_freezes


_OPEN_PREFIX_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075OpenControlledBatchPrefixVerificationV2:
    """Exact typed H0-to-Hn replay that neither closes nor re-signs."""

    _issuer: InitVar[object]
    heads: tuple[V075SignedBatchJournalHeadV2, ...] = field(repr=False)
    appends: tuple[V075ControlledBatchAppendV2, ...] = field(repr=False)
    support_freezes: tuple[
        V075ControlledCompleteSupportFreezeV2,
        ...,
    ] = field(repr=False)
    occurrence_id: str
    session_public_id: str
    observer_open_binding_id: str
    zero_head_id: str
    current_head_id: str
    head_ids: tuple[str, ...]
    intent_ids: tuple[str, ...]
    batch_ids: tuple[str, ...]
    receipt_ids: tuple[str, ...]
    support_freeze_ids: tuple[str, ...]
    append_count: int
    total_accepted_draw_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.occurrence_id, "open-prefix occurrence"),
            (self.session_public_id, "open-prefix session"),
            (self.observer_open_binding_id, "open-prefix binding"),
            (self.zero_head_id, "open-prefix zero head"),
            (self.current_head_id, "open-prefix current head"),
        ):
            _cid(value, label)
        if (
            _issuer is not _OPEN_PREFIX_VERIFICATION_ISSUER
            or type(self.heads) is not tuple
            or type(self.appends) is not tuple
            or type(self.support_freezes) is not tuple
            or type(self.head_ids) is not tuple
            or type(self.intent_ids) is not tuple
            or type(self.batch_ids) is not tuple
            or type(self.receipt_ids) is not tuple
            or type(self.support_freeze_ids) is not tuple
            or type(self.append_count) is not int
            or self.append_count < 0
            or type(self.total_accepted_draw_count) is not int
            or self.total_accepted_draw_count < 0
            or len(self.heads) != self.append_count + 1
            or len(self.appends) != self.append_count
            or self.head_ids != tuple(item.head_id for item in self.heads)
            or self.intent_ids
            != tuple(item.intent.intent_id for item in self.appends)
            or self.batch_ids
            != tuple(item.batch.batch_id for item in self.appends)
            or self.receipt_ids
            != tuple(item.receipt.receipt_id for item in self.appends)
            or self.support_freeze_ids
            != tuple(item.freeze_id for item in self.support_freezes)
            or self.zero_head_id != self.heads[0].head_id
            or self.current_head_id != self.heads[-1].head_id
            or self.occurrence_id != self.heads[0].occurrence_id
            or self.session_public_id != self.heads[0].session_public_id
            or self.observer_open_binding_id
            != self.heads[0].authority_binding.binding_id
            or self.total_accepted_draw_count
            != self.heads[-1].total_accepted_draw_count
        ):
            _fail("open controlled prefix verification is caller-minted")
        for collection in (
            self.head_ids,
            self.intent_ids,
            self.batch_ids,
            self.receipt_ids,
            self.support_freeze_ids,
        ):
            if any(_cid(item, "open-prefix member") != item for item in collection):
                _fail("open controlled prefix contains a malformed ID")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("open_prefix_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_open_controlled_batch_prefix_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "observer_session_public_id": self.session_public_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "zero_head_id": self.zero_head_id,
            "current_head_id": self.current_head_id,
            "head_ids": list(self.head_ids),
            "intent_ids": list(self.intent_ids),
            "signed_batch_ids": list(self.batch_ids),
            "append_receipt_ids": list(self.receipt_ids),
            "support_freeze_ids": list(self.support_freeze_ids),
            "append_count": self.append_count,
            "support_freeze_count": len(self.support_freeze_ids),
            "total_accepted_draw_count": (
                self.total_accepted_draw_count
            ),
            "zero_to_current_head_chain_exactly_reconstructed": True,
            "ordered_intents_batches_receipts_replayed": True,
            "support_freezes_exactly_replayed": True,
            "verifier_closed_session": False,
            "verifier_resigned_artifacts": False,
            "session_open_state_verified": False,
            "typed_open_prefix_only": True,
            "semantic_authority_reference_status": "OPAQUE_DEFERRED",
            "official_execution_allowed": False,
            "process_isolation_provided": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_open_controlled_batch_prefix_v2(
    *,
    heads: tuple[V075SignedBatchJournalHeadV2, ...],
    appends: tuple[V075ControlledBatchAppendV2, ...],
    support_freezes: tuple[
        V075ControlledCompleteSupportFreezeV2,
        ...,
    ] = (),
) -> V075OpenControlledBatchPrefixVerificationV2:
    """Reconstruct an open typed prefix without closing or signing anything."""

    heads, appends, support_freezes = _exact_open_prefix_components(
        heads=heads,
        appends=appends,
        support_freezes=support_freezes,
    )
    first = heads[0]
    return V075OpenControlledBatchPrefixVerificationV2(
        _OPEN_PREFIX_VERIFICATION_ISSUER,
        heads,
        appends,
        support_freezes,
        first.occurrence_id,
        first.session_public_id,
        first.authority_binding.binding_id,
        first.head_id,
        heads[-1].head_id,
        tuple(item.head_id for item in heads),
        tuple(item.intent.intent_id for item in appends),
        tuple(item.batch.batch_id for item in appends),
        tuple(item.receipt.receipt_id for item in appends),
        tuple(item.freeze_id for item in support_freezes),
        len(appends),
        heads[-1].total_accepted_draw_count,
    )


def replay_v075_open_controlled_batch_prefix_verification_v2(
    claimed: V075OpenControlledBatchPrefixVerificationV2,
) -> V075OpenControlledBatchPrefixVerificationV2:
    if type(claimed) is not V075OpenControlledBatchPrefixVerificationV2:
        _fail("open-prefix replay requires one exact verification artifact")
    try:
        replayed = verify_v075_open_controlled_batch_prefix_v2(
            heads=claimed.heads,
            appends=claimed.appends,
            support_freezes=claimed.support_freezes,
        )
        if (
            replayed != claimed
            or replayed.to_document() != claimed.to_document()
        ):
            _fail("open-prefix verification differs from exact replay")
        return replayed
    except (AttributeError, TypeError, ValueError) as error:
        if type(error) is V075ObserverSignedBatchControlV2InvariantViolation:
            raise
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            "open-prefix verification reconstruction failed"
        ) from error


def _verify_controlled_closure_graph(
    *,
    batch_closure: observer.V075ObserverBatchJournalClosureV2,
    heads: tuple[V075SignedBatchJournalHeadV2, ...],
    appends: tuple[V075ControlledBatchAppendV2, ...],
    control_closure: V075ObserverSignedBatchControlClosureV2,
    support_freezes: tuple[
        V075ControlledCompleteSupportFreezeV2,
        ...,
    ] = (),
) -> V075SignedBatchControlReconciliationV2:
    prefix = verify_v075_open_controlled_batch_prefix_v2(
        heads=heads,
        appends=appends,
        support_freezes=support_freezes,
    )
    heads = prefix.heads
    appends = prefix.appends
    support_freezes = prefix.support_freezes
    batch_closure = _replay_batch_closure_against_appends(
        batch_closure,
        appends=appends,
    )
    control_closure = _replay_control_closure(control_closure)
    if (
        type(batch_closure)
        is not observer.V075ObserverBatchJournalClosureV2
        or not appends
        or len(heads) != len(appends) + 1
        or heads[0].entry_count != 0
    ):
        _fail("controlled closure cannot reconcile an empty or partial chain")
    entries = batch_closure.entries
    if len(entries) != len(appends):
        _fail("raw or missing batch append exists outside the control chain")
    binding = batch_closure.authority_binding
    occurrence_id = batch_closure.occurrence_id
    session_public_id = batch_closure.session_public_id
    for index, (append, entry) in enumerate(
        zip(appends, entries, strict=True),
        start=1,
    ):
        request = entry.batch.request
        if (
            append.batch != entry.batch
            or append.receipt.journal_entry_id != entry.entry_id
            or append.receipt.journal_sequence_number != index
            or append.intent.stream_identity != request.stream_identity
        ):
            _fail("controlled head/intent/append chain differs from journal")
    head_ids = tuple(item.head_id for item in heads)
    intent_ids = tuple(item.intent.intent_id for item in appends)
    semantic_authority_binding_ids = tuple(
        item.intent.semantic_authority.binding_id for item in appends
    )
    support_freeze_ids = tuple(
        item.freeze_id for item in support_freezes
    )
    receipt_ids = tuple(item.receipt.receipt_id for item in appends)
    batch_ids = tuple(item.batch.batch_id for item in appends)
    entry_ids = tuple(item.entry_id for item in entries)
    if (
        control_closure.occurrence_id != occurrence_id
        or control_closure.session_public_id != session_public_id
        or control_closure.authority_binding != binding
        or control_closure.zero_head_id != heads[0].head_id
        or control_closure.final_head_id != heads[-1].head_id
        or control_closure.head_ids != head_ids
        or control_closure.intent_ids != intent_ids
        or control_closure.semantic_authority_binding_ids
        != semantic_authority_binding_ids
        or control_closure.support_freeze_ids != support_freeze_ids
        or control_closure.receipt_ids != receipt_ids
        or control_closure.batch_closure_id != batch_closure.closure_id
        or control_closure.batch_ids != batch_ids
        or control_closure.journal_entry_ids != entry_ids
    ):
        _fail("signed control closure differs from exact batch closure")
    return V075SignedBatchControlReconciliationV2(
        _RECONCILIATION_ISSUER,
        occurrence_id,
        session_public_id,
        control_closure.control_closure_id,
        batch_closure.closure_id,
        heads[0].head_id,
        heads[-1].head_id,
        len(appends),
        heads[-1].total_accepted_draw_count,
    )


def verify_v075_controlled_batch_journal_closure_v2(
    *,
    batch_closure: observer.V075ObserverBatchJournalClosureV2,
    heads: tuple[V075SignedBatchJournalHeadV2, ...],
    appends: tuple[V075ControlledBatchAppendV2, ...],
    control_closure: V075ObserverSignedBatchControlClosureV2,
    support_freezes: tuple[
        V075ControlledCompleteSupportFreezeV2,
        ...,
    ] = (),
) -> V075SignedBatchControlReconciliationV2:
    """Exact same-implementation typed replay without re-signing.

    This construction verifier receives already-instantiated typed artifacts;
    it is not the future production canonical-byte loader or an independent
    verifier implementation.
    """

    return _verify_controlled_closure_graph(
        batch_closure=batch_closure,
        heads=heads,
        appends=appends,
        control_closure=control_closure,
        support_freezes=support_freezes,
    )


_CONTROLLER_ISSUER = object()


class V075ConstructionControlledPrivateObserverV2:
    """Exclusive construction wrapper; its exact session never escapes."""

    __slots__ = (
        "__adapter",
        "__appends",
        "__closed",
        "__heads",
        "__identity",
        "__pending_intent",
        "__poisoned",
        "__session",
        "__signer",
        "__support_freezes",
        "__used_intent_ids",
    )

    def __init__(
        self,
        *,
        session: observer.V075PrivateObserverSessionV2,
        adapter: batched_v2.V075OccurrenceBatchedObserverSessionV2,
        signer: observer.V075ObserverEvidenceSignerProtocolV2,
        identity: backend.V075BatchNativeOccurrenceIdentityV1,
        issuer: object,
    ) -> None:
        if (
            issuer is not _CONTROLLER_ISSUER
            or type(session) is not observer.V075PrivateObserverSessionV2
            or type(adapter)
            is not batched_v2.V075OccurrenceBatchedObserverSessionV2
            or adapter.session_public_id != session.session_public_id
            or adapter.authority_binding != session.authority_binding
            or adapter.occurrence_identity != identity
            or adapter.scope
            is not (
                batched_v2.V075BatchOccurrenceAuthorityScopeV2
                .CONSTRUCTION_ONLY
            )
            or adapter.batches
            or session.batch_journal_entries
        ):
            _fail("controlled private observer requires one unused owned session")
        self.__session = session
        self.__adapter = adapter
        self.__signer = signer
        self.__identity = identity
        self.__appends: list[V075ControlledBatchAppendV2] = []
        self.__pending_intent: V075HeadBoundExactBatchIntentV2 | None = None
        self.__used_intent_ids: set[str] = set()
        self.__support_freezes: list[
            V075ControlledCompleteSupportFreezeV2
        ] = []
        self.__closed = False
        self.__poisoned = False
        self.__heads = [self.__mint_current_head()]

    @property
    def occurrence_identity(
        self,
    ) -> backend.V075BatchNativeOccurrenceIdentityV1:
        return self.__identity

    @property
    def current_signed_head(self) -> V075SignedBatchJournalHeadV2:
        return self.__heads[-1]

    @property
    def controlled_appends(self) -> tuple[V075ControlledBatchAppendV2, ...]:
        return tuple(self.__appends)

    @property
    def signed_heads(self) -> tuple[V075SignedBatchJournalHeadV2, ...]:
        return tuple(self.__heads)

    @property
    def support_freezes(
        self,
    ) -> tuple[V075ControlledCompleteSupportFreezeV2, ...]:
        return tuple(
            sorted(
                self.__support_freezes,
                key=lambda item: (
                    item.frozen_at_head.entry_count,
                    item.row_binding_id,
                    item.freeze_id,
                ),
            )
        )

    def verify_open_prefix_v2(
        self,
    ) -> V075OpenControlledBatchPrefixVerificationV2:
        self.__require_open()
        self.__assert_exact_controlled_journal()
        return verify_v075_open_controlled_batch_prefix_v2(
            heads=self.signed_heads,
            appends=self.controlled_appends,
            support_freezes=self.support_freezes,
        )

    def derive_validation_stream_v2(
        self,
        *,
        support_freeze: V075ControlledCompleteSupportFreezeV2,
    ) -> graph.V075TransitionStreamIdentityV1:
        self.__require_open()
        self.__assert_exact_controlled_journal()
        if not any(
            item is support_freeze for item in self.__support_freezes
        ):
            _fail("validation derivation requires this controller's freeze")
        return _derive_validation_stream_from_owned_support_freeze(
            support_freeze
        )

    def __require_open(self) -> None:
        if self.__closed or self.__poisoned:
            _fail("controlled private observer is closed or poisoned")

    def __entries(
        self,
    ) -> tuple[observer.V075ObserverBatchJournalEntryV2, ...]:
        return self.__session.batch_journal_entries

    def __mint_current_head(self) -> V075SignedBatchJournalHeadV2:
        entries = self.__entries()
        frontiers = _derive_frontiers_from_owned_entries(entries)
        unsigned = _journal_head_payload(
            occurrence_id=self.__identity.occurrence_id,
            session_public_id=self.__session.session_public_id,
            authority_binding=self.__session.authority_binding,
            entry_count=len(entries),
            tail_entry_id=None if not entries else entries[-1].entry_id,
            total_accepted_draw_count=sum(
                entry.batch.request.accepted_draw_count for entry in entries
            ),
            stream_frontiers=frontiers,
        )
        signature = _sign(
            signer=self.__signer,
            binding=self.__session.authority_binding,
            message=_signing_bytes("journal_head_signature", unsigned),
        )
        return V075SignedBatchJournalHeadV2(
            self.__identity.occurrence_id,
            self.__session.session_public_id,
            self.__session.authority_binding,
            len(entries),
            None if not entries else entries[-1].entry_id,
            sum(
                entry.batch.request.accepted_draw_count for entry in entries
            ),
            frontiers,
            signature,
        )

    def __assert_exact_controlled_journal(self) -> None:
        entries = self.__entries()
        if (
            len(entries) != len(self.__appends)
            or tuple(entry.batch.batch_id for entry in entries)
            != tuple(item.batch.batch_id for item in self.__appends)
            or tuple(entry.entry_id for entry in entries)
            != tuple(item.receipt.journal_entry_id for item in self.__appends)
            or len(self.__heads) != len(entries) + 1
            or self.__heads[-1].entry_count != len(entries)
            or (
                entries
                and self.__heads[-1].tail_entry_id != entries[-1].entry_id
            )
        ):
            self.__poisoned = True
            _fail("raw or out-of-band adapter change violated control chain")

    def prepare_batch_intent_v2(
        self,
        *,
        stream_identity: graph.V075TransitionStreamIdentityV1,
        semantic_authority_role: (
            V075ControlledBatchSemanticAuthorityRoleV2
        ),
        semantic_authority_schema: (
            V075ControlledBatchSemanticAuthoritySchemaV2
        ),
        semantic_artifact_id: str,
        semantic_verification_id: str,
        stage: V075ControlledBatchStageV2,
        round_index: int,
        support_freeze_id: str | None,
        accepted_draw_start: int,
        accepted_draw_count: int,
        accepted_draw_cap: int,
    ) -> V075HeadBoundExactBatchIntentV2:
        """Freeze the sole pending intent without performing any draw."""

        self.__require_open()
        self.__assert_exact_controlled_journal()
        if self.__pending_intent is not None:
            _fail("controlled private observer already has a pending intent")
        identity = self.__identity
        if (
            type(stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or stream_identity.target_tape_namespace_id
            != identity.target_tape_namespace_id
            or stream_identity.context_id != identity.context_id
            or stream_identity.arm != identity.arm.value
        ):
            _fail("controlled batch stream was transplanted")
        semantic_authority = (
            freeze_v075_controlled_batch_semantic_authority_v2(
                role=semantic_authority_role,
                schema=semantic_authority_schema,
                semantic_artifact_id=semantic_artifact_id,
                semantic_verification_id=semantic_verification_id,
                stage=stage,
                round_index=round_index,
                support_freeze_id=support_freeze_id,
            )
        )
        expected_lane = (
            "DISCOVERY"
            if stage
            in {
                V075ControlledBatchStageV2.ROOT_DISCOVERY,
                V075ControlledBatchStageV2.CHILD_DISCOVERY,
            }
            else "VALIDATION"
        )
        if stream_identity.lane.value != expected_lane:
            _fail("controlled batch stage and stream lane disagree")
        support_by_row = {
            item.row_binding_id: item for item in self.support_freezes
        }
        row_support = support_by_row.get(stream_identity.row_binding_id)
        if expected_lane == "VALIDATION":
            if (
                row_support is None
                or support_freeze_id != row_support.freeze_id
                or stream_identity
                != _derive_validation_stream_from_owned_support_freeze(
                    row_support
                )
            ):
                _fail(
                    "controlled validation intent lacks its exact same-row "
                    "support freeze"
                )
        elif row_support is not None:
            _fail("controlled discovery cannot continue after row freeze")
        elif any(
            item.batch.request.stream_identity.row_binding_id
            == stream_identity.row_binding_id
            and item.batch.request.stream_identity.lane
            is graph.V075ObservationLaneV1.DISCOVERY
            for item in self.__appends
        ):
            _fail("controlled row already has its sole discovery append")
        expected_start = _expected_next_from_head(
            head=self.current_signed_head,
            stream_id=stream_identity.stream_id,
            requested_cap=accepted_draw_cap,
        )
        if accepted_draw_start != expected_start:
            _fail("controlled batch intent is gapped or overlaps its prefix")
        intent = freeze_v075_head_bound_exact_batch_intent_v2(
            prior_head=self.current_signed_head,
            stream_identity=stream_identity,
            semantic_authority=semantic_authority,
            accepted_draw_start=accepted_draw_start,
            accepted_draw_count=accepted_draw_count,
            accepted_draw_cap=accepted_draw_cap,
        )
        if intent.intent_id in self.__used_intent_ids:
            _fail("controlled batch intent was already consumed")
        self.__pending_intent = intent
        return intent

    def freeze_complete_support_v2(
        self,
        *,
        discovery_append: V075ControlledBatchAppendV2,
    ) -> V075ControlledCompleteSupportFreezeV2:
        """Freeze every symbolic outcome before same-row validation."""

        self.__require_open()
        self.__assert_exact_controlled_journal()
        if self.__pending_intent is not None:
            _fail("support cannot freeze while another intent is pending")
        matching = tuple(
            item
            for item in self.__appends
            if item is discovery_append
        )
        if len(matching) != 1:
            _fail(
                "support freeze is duplicate, foreign, non-discovery, or "
                "after validation"
            )
        append = matching[0]
        stream = append.batch.request.stream_identity
        same_row_discoveries = tuple(
            item
            for item in self.__appends
            if item.batch.request.stream_identity.row_binding_id
            == stream.row_binding_id
            and item.batch.request.stream_identity.lane
            is graph.V075ObservationLaneV1.DISCOVERY
        )
        if (
            stream.lane is not graph.V075ObservationLaneV1.DISCOVERY
            or append.intent.semantic_authority.stage
            not in {
                V075ControlledBatchStageV2.ROOT_DISCOVERY,
                V075ControlledBatchStageV2.CHILD_DISCOVERY,
            }
            or any(
                item.discovery_append_receipt_id
                == append.receipt.receipt_id
                or item.row_binding_id == stream.row_binding_id
                for item in self.__support_freezes
            )
            or any(
                item.batch.request.stream_identity.row_binding_id
                == stream.row_binding_id
                and item.batch.request.stream_identity.lane
                is graph.V075ObservationLaneV1.VALIDATION
                for item in self.__appends
            )
            or same_row_discoveries != (append,)
        ):
            _fail(
                "support freeze is duplicate, foreign, non-discovery, or "
                "after validation"
            )
        batch = append.batch
        request = batch.request
        namespace = request.authority_binding.namespace
        row = stream.row_binding
        evidence: list[graph.V075BatchAggregateSupportEvidenceV1] = []
        self.__poisoned = True
        try:
            for _state_id, state, outcome in (
                _complete_support_representatives(batch)
            ):
                message = (
                    graph.batch_aggregate_support_evidence_signing_bytes_v1(
                        namespace=namespace,
                        row_binding=row,
                        observed_state=state,
                        source_observer_epoch_index=(
                            stream.observer_epoch_index
                        ),
                        discovery_request_id=request.request_id,
                        discovery_batch_id=batch.batch_id,
                        discovery_outcome_id=outcome.outcome_id,
                        discovery_outcome_count=outcome.count,
                    )
                )
                signature = _sign(
                    signer=self.__signer,
                    binding=request.authority_binding,
                    message=message,
                )
                evidence.append(
                    graph.bind_batch_aggregate_support_evidence_v1(
                        namespace=namespace,
                        row_binding=row,
                        observed_state=state,
                        source_observer_epoch_index=(
                            stream.observer_epoch_index
                        ),
                        discovery_request_id=request.request_id,
                        discovery_batch_id=batch.batch_id,
                        discovery_outcome_id=outcome.outcome_id,
                        discovery_outcome_count=outcome.count,
                        observer_signature_hex=signature,
                    )
                )
            evidence_tuple = tuple(
                sorted(evidence, key=lambda item: item.evidence_id)
            )
            frozen_at_head = self.current_signed_head
            unsigned = _support_freeze_payload(
                discovery_append=append,
                frozen_at_head=frozen_at_head,
                evidence=evidence_tuple,
            )
            support = V075ControlledCompleteSupportFreezeV2(
                _OWNED_SUPPORT_FREEZE_ISSUER,
                append,
                frozen_at_head,
                evidence_tuple,
                _sign(
                    signer=self.__signer,
                    binding=request.authority_binding,
                    message=_signing_bytes(
                        "support_freeze_signature",
                        unsigned,
                    ),
                ),
            )
        except Exception:
            self.__closed = True
            raise
        self.__support_freezes.append(support)
        self.__poisoned = False
        return support

    def execute_batch_intent_v2(
        self,
        intent: V075HeadBoundExactBatchIntentV2,
    ) -> V075ControlledBatchAppendV2:
        """Validate first, then fail closed across draw, append, and signing."""

        self.__require_open()
        self.__assert_exact_controlled_journal()
        if (
            type(intent) is not V075HeadBoundExactBatchIntentV2
            or self.__pending_intent is None
            or intent != self.__pending_intent
            or intent.intent_id in self.__used_intent_ids
            or intent.prior_head_id != self.current_signed_head.head_id
        ):
            _fail("controlled batch intent is stale, reused, or unregistered")
        prior_head = self.current_signed_head
        self.__poisoned = True
        try:
            batch = self.__adapter.observe_batch_v2(
                stream_identity=intent.stream_identity,
                accepted_draw_start=intent.accepted_draw_start,
                accepted_draw_count=intent.accepted_draw_count,
                accepted_draw_cap=intent.accepted_draw_cap,
            )
            entries = self.__entries()
            request = batch.request
            if (
                len(entries) != len(self.__appends) + 1
                or entries[-1].batch != batch
                or request.occurrence_id != intent.occurrence_id
                or request.session_public_id != intent.session_public_id
                or request.authority_binding != prior_head.authority_binding
                or request.stream_identity != intent.stream_identity
                or request.accepted_draw_start
                != intent.accepted_draw_start
                or request.accepted_draw_count
                != intent.accepted_draw_count
                or request.accepted_draw_cap != intent.accepted_draw_cap
            ):
                _fail("controlled batch append differs from frozen intent")
            resulting_head = self.__mint_current_head()
            entry = entries[-1]
            unsigned_receipt = _append_receipt_payload(
                occurrence_id=intent.occurrence_id,
                session_public_id=intent.session_public_id,
                authority_binding=prior_head.authority_binding,
                prior_head_id=prior_head.head_id,
                intent_id=intent.intent_id,
                semantic_authority_binding_id=(
                    intent.semantic_authority.binding_id
                ),
                batch_id=batch.batch_id,
                batch_request_id=batch.request.request_id,
                journal_entry_id=entry.entry_id,
                journal_sequence_number=entry.sequence_number,
                resulting_head_id=resulting_head.head_id,
            )
            receipt = V075ObserverSignedBatchAppendReceiptV2(
                intent.occurrence_id,
                intent.session_public_id,
                prior_head.authority_binding,
                prior_head.head_id,
                intent.intent_id,
                intent.semantic_authority.binding_id,
                batch.batch_id,
                batch.request.request_id,
                entry.entry_id,
                entry.sequence_number,
                resulting_head.head_id,
                _sign(
                    signer=self.__signer,
                    binding=prior_head.authority_binding,
                    message=_signing_bytes(
                        "append_receipt_signature",
                        unsigned_receipt,
                    ),
                ),
            )
            append = V075ControlledBatchAppendV2(
                prior_head,
                intent,
                batch,
                resulting_head,
                receipt,
                _OWNED_APPEND_ISSUER,
            )
        except Exception:
            self.__closed = True
            raise
        self.__heads.append(resulting_head)
        self.__appends.append(append)
        self.__used_intent_ids.add(intent.intent_id)
        self.__pending_intent = None
        self.__poisoned = False
        return append

    def close_and_reconcile_v2(
        self,
    ) -> V075ControlledBatchJournalClosureV2:
        """Close both signed chains and exact-reconcile them once."""

        self.__require_open()
        self.__assert_exact_controlled_journal()
        if self.__pending_intent is not None:
            _fail("controlled private observer cannot close a pending intent")
        if not self.__appends:
            _fail("controlled private observer cannot close an empty journal")
        self.__poisoned = True
        try:
            batch_closure = self.__adapter.close_v2()
            heads = tuple(self.__heads)
            appends = tuple(self.__appends)
            support_freezes = self.support_freezes
            batch_ids = tuple(item.batch.batch_id for item in appends)
            entry_ids = tuple(
                item.entry_id for item in batch_closure.entries
            )
            unsigned_control = _control_closure_payload(
                occurrence_id=self.__identity.occurrence_id,
                session_public_id=batch_closure.session_public_id,
                authority_binding=batch_closure.authority_binding,
                zero_head_id=heads[0].head_id,
                final_head_id=heads[-1].head_id,
                head_ids=tuple(item.head_id for item in heads),
                intent_ids=tuple(
                    item.intent.intent_id for item in appends
                ),
                semantic_authority_binding_ids=tuple(
                    item.intent.semantic_authority.binding_id
                    for item in appends
                ),
                support_freeze_ids=tuple(
                    item.freeze_id for item in support_freezes
                ),
                receipt_ids=tuple(
                    item.receipt.receipt_id for item in appends
                ),
                batch_closure_id=batch_closure.closure_id,
                batch_ids=batch_ids,
                journal_entry_ids=entry_ids,
            )
            control_closure = V075ObserverSignedBatchControlClosureV2(
                self.__identity.occurrence_id,
                batch_closure.session_public_id,
                batch_closure.authority_binding,
                heads[0].head_id,
                heads[-1].head_id,
                tuple(item.head_id for item in heads),
                tuple(item.intent.intent_id for item in appends),
                tuple(
                    item.intent.semantic_authority.binding_id
                    for item in appends
                ),
                tuple(item.freeze_id for item in support_freezes),
                tuple(item.receipt.receipt_id for item in appends),
                batch_closure.closure_id,
                batch_ids,
                entry_ids,
                _sign(
                    signer=self.__signer,
                    binding=batch_closure.authority_binding,
                    message=_signing_bytes(
                        "control_closure_signature",
                        unsigned_control,
                    ),
                ),
            )
            reconciliation = _verify_controlled_closure_graph(
                batch_closure=batch_closure,
                heads=heads,
                appends=appends,
                control_closure=control_closure,
                support_freezes=support_freezes,
            )
            result = V075ControlledBatchJournalClosureV2(
                batch_closure,
                heads,
                appends,
                control_closure,
                reconciliation,
                support_freezes,
                _OWNED_CLOSED_RESULT_ISSUER,
            )
        except Exception:
            self.__closed = True
            raise
        self.__closed = True
        self.__poisoned = False
        self.__signer = None
        return result


def open_v075_construction_controlled_private_observer_v2(
    *,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
    observer_signer: observer.V075ObserverEvidenceSignerProtocolV2,
    session_external_id: str,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
) -> V075ConstructionControlledPrivateObserverV2:
    """Open and hide one exact unused session behind the controlled surface."""

    try:
        occurrence_identity = (
            backend.replay_v075_batch_native_occurrence_identity_v1(
                occurrence_identity
            )
        )
        binding = observer._require_exact_v2_binding(  # noqa: SLF001
            authority=authority,
            namespace=namespace,
        )
        session = observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
            authority=authority,
            namespace=namespace,
            binding=binding,
            private_salt=private_salt,
            private_environment=private_environment,
            observer_signer=observer_signer,
            session_external_id=session_external_id,
        )
        adapter = (
            batched_v2.bind_v075_construction_occurrence_batched_observer_v2(
                session=session,
                occurrence_identity=occurrence_identity,
            )
        )
    except (
        backend.V075BatchNativeBackendInvariantViolation,
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        batched_v2.V075BatchedObserverV2InvariantViolation,
    ) as error:
        raise V075ObserverSignedBatchControlV2InvariantViolation(
            str(error)
        ) from error
    return V075ConstructionControlledPrivateObserverV2(
        session=session,
        adapter=adapter,
        signer=observer_signer,
        identity=occurrence_identity,
        issuer=_CONTROLLER_ISSUER,
    )


def open_v075_production_controlled_private_observer_v2(
    **_unused: Any,
) -> None:
    raise V075ObserverSignedBatchControlProductionV2NotReady(
        "production signed batch control requires process isolation, tracked "
        "byte replay, and an official contract revision"
    )


__all__ = [
    "DOMAIN_TAGS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PROCESS_ISOLATION_PROVIDED",
    "PRODUCTION_AUTHORIZING",
    "PUBLIC_PRIVATE_SESSION_API_EXPOSED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "TERMINAL_CLASS",
    "V075BatchStreamFrontierV2",
    "V075ConstructionControlledPrivateObserverV2",
    "V075ControlledCompleteSupportFreezeV2",
    "V075ControlledBatchSemanticAuthorityBindingV2",
    "V075ControlledBatchSemanticAuthorityRoleV2",
    "V075ControlledBatchSemanticAuthoritySchemaV2",
    "V075ControlledBatchStageV2",
    "V075ControlledBatchAppendV2",
    "V075ControlledBatchJournalClosureV2",
    "V075HeadBoundExactBatchIntentV2",
    "V075ObserverSignedBatchAppendReceiptV2",
    "V075ObserverSignedBatchControlClosureV2",
    "V075ObserverSignedBatchControlProductionV2NotReady",
    "V075ObserverSignedBatchControlV2InvariantViolation",
    "V075OpenControlledBatchPrefixVerificationV2",
    "V075SignedBatchControlReconciliationV2",
    "V075SignedBatchJournalHeadV2",
    "derive_v075_controlled_validation_stream_v2",
    "freeze_v075_controlled_batch_semantic_authority_v2",
    "freeze_v075_head_bound_exact_batch_intent_v2",
    "open_v075_construction_controlled_private_observer_v2",
    "open_v075_production_controlled_private_observer_v2",
    "replay_v075_open_controlled_batch_prefix_verification_v2",
    "verify_v075_controlled_batch_journal_closure_v2",
    "verify_v075_open_controlled_batch_prefix_v2",
]
