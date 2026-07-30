"""Observer-signed atomic private-replay attestation for V0-075 V2.

An issuer token on ``V075ObserverBatchClosureVerificationV2`` is only an
in-process construction guard: code with access to that token can mint an
exact-shaped object without performing private replay.  Consequently this
primitive never accepts a caller-supplied verification object.  Its trusted
freeze performs the private replay itself and, without returning control to
the caller, signs the exact replay result and complete public closure/stream
projection.

The trusted freeze necessarily accepts the private salt and environment.
Neither is serialized.  The public verifier accepts only canonical
attestation bytes plus an already-public reconstructed closure, binding, and
stream graph.  It can verify the observer signature and every public field,
but cannot independently prove that replay preceded signing.  The temporal
claim is therefore explicitly limited to
``TRUSTED_ATOMIC_FREEZE_EXECUTION``.

The primitive creates a new artifact and exposes no path for upgrading a
legacy or exact-cloned verification object.  It is not integrated into the
portable role registry, occurrence runner, or production campaign.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from fractions import Fraction
import hashlib
from types import MappingProxyType
from typing import Any, Iterable, Mapping, NoReturn

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.68.0"
PROFILE_KEY = "v075_observer_signed_private_replay_attestation_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
OBSERVER_OPEN_ALLOWED = False
TRUSTED_ATOMIC_FREEZE_PRIVATE_INPUTS_REQUIRED = True
PUBLIC_VERIFIER_PRIVATE_INPUTS_ALLOWED = False
RAW_SOURCE_VERIFICATION_ACCEPTED = False
LEGACY_PRIVATE_REPLAY_VERIFICATION_UPGRADE_ALLOWED = False
CALLER_SUPPLIED_PRIVATE_REPLAY_VERIFICATION_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_M1_B3_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "B3_PRIVATE_REPLAY_OBSERVER_ATTESTED_PORTABLE_REGISTRY_INCOMPLETE"
)

MAX_ATTESTATION_BYTES = 2 * 1024 * 1024
PRIVATE_REPLAY_STATUS = "EXACT_BATCH_NATIVE_V2_REPLAY_VERIFIED"
PRIVATE_REPLAY_ORDER_CLAIM_SCOPE = "TRUSTED_ATOMIC_FREEZE_EXECUTION"
SOURCE_PRIVATE_REPLAY_SCHEMA = (
    "acfqp.v075_observer_batch_journal_closure_verification.v2"
)
ATTESTATION_ROLE = "OBSERVER_SIGNED_PRIVATE_REPLAY_ATTESTATION"

DOMAIN_TAGS = MappingProxyType(
    {
        "profile": (
            "acfqp:v075-observer-signed-private-replay-profile:v2"
        ),
        "stream_graph": (
            "acfqp:v075-observer-signed-private-replay-stream-graph:v2"
        ),
        "signature": (
            "acfqp:v075-observer-signed-private-replay-attestation-"
            "signature:v2"
        ),
        "attestation": (
            "acfqp:v075-observer-signed-private-replay-attestation:v2"
        ),
    }
)

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 private-replay attestation domains overlap")


class V075ObserverSignedPrivateReplayAttestationV2InvariantViolation(
    ValueError
):
    """The source replay, public graph, signature, or identity was invalid."""


class V075ObserverSignedPrivateReplayAttestationProductionV2NotReady(
    RuntimeError
):
    """The construction-only B3 primitive cannot authorize production."""


def _fail(message: str) -> NoReturn:
    raise V075ObserverSignedPrivateReplayAttestationV2InvariantViolation(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise (
            V075ObserverSignedPrivateReplayAttestationV2InvariantViolation(
                f"{label} must be one lowercase SHA-256 content ID"
            )
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise (
            V075ObserverSignedPrivateReplayAttestationV2InvariantViolation(
                str(error)
            )
        ) from error


def _hash_external_domain(
    domain: str,
    payload: Mapping[str, Any],
) -> str:
    if type(domain) is not str or not domain.startswith("acfqp:"):
        _fail("source private-replay content domain is malformed")
    try:
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise (
            V075ObserverSignedPrivateReplayAttestationV2InvariantViolation(
                str(error)
            )
        ) from error


def _private_replay_profile_payload() -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v075_observer_signed_private_replay_profile.v2"
        ),
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "source_private_replay_schema": SOURCE_PRIVATE_REPLAY_SCHEMA,
        "required_private_replay_status": PRIVATE_REPLAY_STATUS,
        "replay_algorithm": (
            "DETERMINISTIC_H2_GRAPH_STREAM_V1_FULL_BATCH_AGGREGATE_"
            "AND_TRANSCRIPT_REPLAY"
        ),
        "source_verification_must_be_issuer_minted": True,
        "caller_supplied_source_verification_accepted": False,
        "private_verifier_invoked_inside_atomic_freeze": True,
        "raw_source_verification_accepted": False,
        "legacy_source_verification_upgrade_allowed": False,
        "complete_signed_closure_required": True,
        "complete_used_stream_graph_required": True,
        "ordered_entry_and_batch_ids_required": True,
        "observer_signature_after_private_replay_required": True,
        "observer_signature_after_private_replay_scope": (
            PRIVATE_REPLAY_ORDER_CLAIM_SCOPE
        ),
        "public_verifier_proves_private_replay_execution_order": False,
        "execution_order_is_trusted_api_discipline_not_cryptographic_proof": (
            True
        ),
        "production_requires_signer_owning_sealed_observer_boundary": True,
        "private_replay_claim_observer_signed": True,
        "private_replay_independently_recomputed": False,
        "trusted_atomic_freeze_private_inputs_required": True,
        "private_inputs_serialized": False,
        "salt_or_environment_accepted_by_public_verifier": False,
        "production_authorizing": False,
    }


PRIVATE_REPLAY_PROFILE_ID = _hash(
    "profile",
    _private_replay_profile_payload(),
)


_SOURCE_VERIFICATION_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "closure_id",
        "occurrence_id",
        "batch_ids",
        "observer_open_binding_id",
        "observer_open_authorization_id",
        "private_reveal_attestation_id",
        "remote_main_anchor_id",
        "target_tape_namespace_id",
        "verification_result",
        "replayed_batch_count",
        "replayed_draw_count",
        "replayed_stream_count",
        "per_draw_records_replayed",
        "authority_version",
        "namespace_version",
        "legacy_v1_projection_used",
        "private_material_serialized",
        "verification_id",
    }
)


def _source_verification_payload(
    *,
    closure_id: str,
    occurrence_id: str,
    ordered_batch_ids: tuple[str, ...],
    binding_id: str,
    authorization_id: str,
    reveal_attestation_id: str,
    anchor_id: str,
    namespace_id: str,
    batch_count: int,
    draw_count: int,
    stream_count: int,
) -> dict[str, Any]:
    return {
        "schema": SOURCE_PRIVATE_REPLAY_SCHEMA,
        "schema_version": observer.SCHEMA_VERSION,
        "closure_id": closure_id,
        "occurrence_id": occurrence_id,
        "batch_ids": list(ordered_batch_ids),
        "observer_open_binding_id": binding_id,
        "observer_open_authorization_id": authorization_id,
        "private_reveal_attestation_id": reveal_attestation_id,
        "remote_main_anchor_id": anchor_id,
        "target_tape_namespace_id": namespace_id,
        "verification_result": PRIVATE_REPLAY_STATUS,
        "replayed_batch_count": batch_count,
        "replayed_draw_count": draw_count,
        "replayed_stream_count": stream_count,
        "per_draw_records_replayed": 0,
        "authority_version": "V2",
        "namespace_version": "V2",
        "legacy_v1_projection_used": False,
        "private_material_serialized": False,
    }


def _strict_document(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_ATTESTATION_BYTES
    ):
        _fail(
            "private-replay attestation bytes are empty, mistyped, or "
            "over cap"
        )
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise (
            V075ObserverSignedPrivateReplayAttestationV2InvariantViolation(
                "private-replay attestation is not strict canonical JSON"
            )
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("private-replay attestation is not one canonical JSON object")
    return document


def _reconstruct_binding(
    value: observer.V075ObserverOpenAuthorityBindingV2,
) -> observer.V075ObserverOpenAuthorityBindingV2:
    if (
        type(value) is not observer.V075ObserverOpenAuthorityBindingV2
        or value._issuer is not observer._BINDING_ISSUER  # noqa: SLF001
    ):
        _fail("private-replay attestation binding is not issuer-minted")
    try:
        replayed = observer.V075ObserverOpenAuthorityBindingV2(
            observer._BINDING_ISSUER,  # noqa: SLF001
            value.namespace,
            value.authorization_id,
            value.private_reveal_attestation_id,
            value.remote_main_anchor_id,
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
    ) as error:
        raise (
            V075ObserverSignedPrivateReplayAttestationV2InvariantViolation(
                "private-replay attestation binding replay failed"
            )
        ) from error
    if (
        replayed != value
        or replayed.to_document() != value.to_document()
        or replayed.binding_id != value.binding_id
    ):
        _fail("private-replay attestation binding differs from exact replay")
    return replayed


def _public_projection(
    *,
    closure: observer.V075ObserverBatchJournalClosureV2,
    authority_binding: observer.V075ObserverOpenAuthorityBindingV2,
    used_stream_identities: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ],
) -> dict[str, Any]:
    binding = _reconstruct_binding(authority_binding)
    if (
        type(closure)
        is not observer.V075ObserverBatchJournalClosureV2
        or type(used_stream_identities) is not tuple
        or not used_stream_identities
        or any(
            type(item) is not graph.V075TransitionStreamIdentityV1
            for item in used_stream_identities
        )
    ):
        _fail("private-replay closure or used-stream graph is untyped")
    stream_ids = tuple(item.stream_id for item in used_stream_identities)
    if len(set(stream_ids)) != len(stream_ids):
        _fail("private-replay used-stream graph contains duplicate streams")
    try:
        replayed_closure = (
            observer.load_observer_batch_journal_closure_bytes_v2(
                raw=closure.canonical_bytes,
                authority_binding=binding,
                known_stream_identities=tuple(
                    sorted(
                        used_stream_identities,
                        key=lambda item: item.stream_id,
                    )
                ),
            )
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
    ) as error:
        raise (
            V075ObserverSignedPrivateReplayAttestationV2InvariantViolation(
                "signed closure or exact used-stream graph failed replay"
            )
        ) from error
    if (
        replayed_closure != closure
        or replayed_closure.canonical_bytes != closure.canonical_bytes
        or replayed_closure.authority_binding != binding
    ):
        _fail("signed closure, binding, or stream graph was transplanted")

    streams_by_id: dict[
        str,
        graph.V075TransitionStreamIdentityV1,
    ] = {}
    for entry in replayed_closure.entries:
        stream = entry.batch.request.stream_identity
        prior = streams_by_id.setdefault(stream.stream_id, stream)
        if prior != stream or prior.to_document() != stream.to_document():
            _fail("one used stream ID carries multiple public graphs")
    ordered_streams = tuple(
        streams_by_id[key] for key in sorted(streams_by_id)
    )
    if set(stream_ids) != set(streams_by_id):
        _fail("caller stream graph is not the exact closure stream set")

    stream_graph_payload = {
        "schema": (
            "acfqp.v075_observer_signed_private_replay_stream_graph.v2"
        ),
        "schema_version": SCHEMA_VERSION,
        "closure_id": replayed_closure.closure_id,
        "occurrence_id": replayed_closure.occurrence_id,
        "observer_session_public_id": replayed_closure.session_public_id,
        "observer_open_binding_id": binding.binding_id,
        "target_tape_namespace_id": (
            binding.namespace.target_tape_namespace_id
        ),
        "ordered_stream_ids": [
            item.stream_id for item in ordered_streams
        ],
        "streams": [item.to_document() for item in ordered_streams],
        "ordering_rule": "LEXICOGRAPHIC_STREAM_ID",
        "complete_exact_used_stream_set": True,
    }
    entries = replayed_closure.entries
    return {
        "closure_id": replayed_closure.closure_id,
        "occurrence_id": replayed_closure.occurrence_id,
        "observer_session_public_id": replayed_closure.session_public_id,
        "observer_open_binding_id": binding.binding_id,
        "observer_open_authorization_id": binding.authorization_id,
        "private_reveal_attestation_id": (
            binding.private_reveal_attestation_id
        ),
        "remote_main_anchor_id": binding.remote_main_anchor_id,
        "target_tape_namespace_id": (
            binding.namespace.target_tape_namespace_id
        ),
        "opaque_environment_commitment_id": (
            binding.namespace.environment_commitment.commitment_id
        ),
        "signer_registry_id": binding.namespace.signer_registry.registry_id,
        "observer_evidence_key_id": (
            binding.namespace.signer_registry.observer_evidence_key.key_id
        ),
        "ordered_entry_ids": [item.entry_id for item in entries],
        "ordered_batch_ids": [
            item.batch.batch_id for item in entries
        ],
        "ordered_stream_ids": [
            item.stream_id for item in ordered_streams
        ],
        "used_stream_graph_digest": _hash(
            "stream_graph",
            stream_graph_payload,
        ),
        "replayed_batch_count": len(entries),
        "replayed_draw_count": sum(
            item.batch.request.accepted_draw_count for item in entries
        ),
        "replayed_stream_count": len(ordered_streams),
    }


def _expected_source_private_replay(
    projection: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    expected_payload = _source_verification_payload(
        closure_id=projection["closure_id"],
        occurrence_id=projection["occurrence_id"],
        ordered_batch_ids=tuple(projection["ordered_batch_ids"]),
        binding_id=projection["observer_open_binding_id"],
        authorization_id=projection["observer_open_authorization_id"],
        reveal_attestation_id=projection[
            "private_reveal_attestation_id"
        ],
        anchor_id=projection["remote_main_anchor_id"],
        namespace_id=projection["target_tape_namespace_id"],
        batch_count=projection["replayed_batch_count"],
        draw_count=projection["replayed_draw_count"],
        stream_count=projection["replayed_stream_count"],
    )
    expected_id = _hash_external_domain(
        observer.DOMAIN_TAGS["batch_closure_verification"],
        expected_payload,
    )
    expected_document = {
        **expected_payload,
        "verification_id": expected_id,
    }
    return expected_id, expected_document


def _verify_source_private_replay(
    *,
    verification: observer.V075ObserverBatchClosureVerificationV2,
    projection: Mapping[str, Any],
) -> str:
    if (
        type(verification)
        is not observer.V075ObserverBatchClosureVerificationV2
        or verification._issuer  # noqa: SLF001
        is not observer._BATCH_CLOSURE_VERIFICATION_ISSUER  # noqa: SLF001
    ):
        _fail("source private-replay verification is not issuer-minted")
    expected_id, expected_document = _expected_source_private_replay(
        projection
    )
    try:
        claimed = verification.to_document()
    except (AttributeError, TypeError, ValueError) as error:
        raise (
            V075ObserverSignedPrivateReplayAttestationV2InvariantViolation(
                "source private-replay verification is unreadable"
            )
        ) from error
    if (
        type(claimed) is not dict
        or set(claimed) != _SOURCE_VERIFICATION_KEYS
        or claimed != expected_document
        or verification.verification_id != expected_id
        or canonical_json_bytes(claimed)
        != canonical_json_bytes(expected_document)
    ):
        _fail(
            "source private-replay verification, closure, stream counts, "
            "profile, or status differ"
        )
    return expected_id


def _attestation_payload(
    *,
    source_private_replay_verification_id: str,
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v075_observer_signed_private_replay_attestation.v2"
        ),
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "attestation_role": ATTESTATION_ROLE,
        "source_private_replay_schema": SOURCE_PRIVATE_REPLAY_SCHEMA,
        "source_private_replay_verification_id": (
            source_private_replay_verification_id
        ),
        "private_replay_profile_id": PRIVATE_REPLAY_PROFILE_ID,
        "private_replay_status": PRIVATE_REPLAY_STATUS,
        **dict(projection),
        "observer_signature_algorithm": "RSASSA-PKCS1-v1_5-SHA256",
        "private_replay_claim_observer_signed": True,
        "private_replay_independently_recomputed": False,
        "public_closure_and_stream_graph_recomputed": True,
        "private_verifier_invoked_inside_atomic_freeze": True,
        "caller_supplied_source_verification_accepted": False,
        "source_verification_issuer_checked_inside_atomic_freeze": True,
        "observer_signature_created_after_private_replay": True,
        "observer_signature_after_private_replay_scope": (
            PRIVATE_REPLAY_ORDER_CLAIM_SCOPE
        ),
        "public_verifier_proves_private_replay_execution_order": False,
        "execution_order_is_trusted_api_discipline_not_cryptographic_proof": (
            True
        ),
        "production_requires_signer_owning_sealed_observer_boundary": True,
        "raw_source_verification_accepted": False,
        "legacy_source_verification_upgrade_allowed": False,
        "trusted_atomic_freeze_private_inputs_required": True,
        "public_verifier_private_inputs_allowed": False,
        "private_salt_serialized": False,
        "private_environment_serialized": False,
        "transition_law_serialized": False,
        "random_tape_serialized": False,
        "target_access_performed_by_attestation": False,
        "official_execution_allowed": False,
        "production_authorizing": False,
        "scientific_endpoint_credit_allowed": False,
        "source_authority_complete": False,
        "code_provenance_complete": False,
        "portable_semantic_registry_complete": False,
        "fresh_heldout_access_allowed": False,
        "plan_certificate_issuance_allowed": False,
        "infeasibility_certificate_issuance_allowed": False,
    }


def _signing_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        DOMAIN_TAGS["signature"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    )


_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ObserverSignedPrivateReplayAttestationV2:
    """One public observer attestation of an upstream exact private replay."""

    _issuer: InitVar[object]
    source_private_replay_verification_id: str
    closure_id: str
    occurrence_id: str
    observer_session_public_id: str
    observer_open_binding_id: str
    observer_open_authorization_id: str
    private_reveal_attestation_id: str
    remote_main_anchor_id: str
    target_tape_namespace_id: str
    opaque_environment_commitment_id: str
    signer_registry_id: str
    observer_evidence_key_id: str
    ordered_entry_ids: tuple[str, ...]
    ordered_batch_ids: tuple[str, ...]
    ordered_stream_ids: tuple[str, ...]
    used_stream_graph_digest: str
    replayed_batch_count: int
    replayed_draw_count: int
    replayed_stream_count: int
    observer_signature_hex: str
    observer_evidence_key: public.V075RSAPublicVerificationKeyV1 = field(
        repr=False,
        compare=False,
    )
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (
                self.source_private_replay_verification_id,
                "source private-replay verification",
            ),
            (self.closure_id, "private-replay closure"),
            (self.occurrence_id, "private-replay occurrence"),
            (
                self.observer_session_public_id,
                "private-replay observer session",
            ),
            (
                self.observer_open_binding_id,
                "private-replay observer-open binding",
            ),
            (
                self.observer_open_authorization_id,
                "private-replay observer-open authorization",
            ),
            (
                self.private_reveal_attestation_id,
                "private-replay reveal attestation",
            ),
            (self.remote_main_anchor_id, "private-replay anchor"),
            (
                self.target_tape_namespace_id,
                "private-replay namespace",
            ),
            (
                self.opaque_environment_commitment_id,
                "private-replay environment commitment",
            ),
            (self.signer_registry_id, "private-replay signer registry"),
            (
                self.observer_evidence_key_id,
                "private-replay observer key",
            ),
            (
                self.used_stream_graph_digest,
                "private-replay used-stream graph",
            ),
        ):
            _cid(value, label)
        id_groups = (
            self.ordered_entry_ids,
            self.ordered_batch_ids,
            self.ordered_stream_ids,
        )
        if (
            _issuer is not _ATTESTATION_ISSUER
            or any(type(group) is not tuple or not group for group in id_groups)
            or any(
                _cid(value, "private-replay ordered identity") != value
                for group in id_groups
                for value in group
            )
            or len(set(self.ordered_entry_ids))
            != len(self.ordered_entry_ids)
            or len(set(self.ordered_batch_ids))
            != len(self.ordered_batch_ids)
            or tuple(sorted(self.ordered_stream_ids))
            != self.ordered_stream_ids
            or len(set(self.ordered_stream_ids))
            != len(self.ordered_stream_ids)
            or type(self.replayed_batch_count) is not int
            or self.replayed_batch_count != len(self.ordered_entry_ids)
            or self.replayed_batch_count != len(self.ordered_batch_ids)
            or type(self.replayed_draw_count) is not int
            or self.replayed_draw_count <= 0
            or type(self.replayed_stream_count) is not int
            or self.replayed_stream_count != len(self.ordered_stream_ids)
            or type(self.observer_signature_hex) is not str
            or not self.observer_signature_hex
            or type(self.observer_evidence_key)
            is not public.V075RSAPublicVerificationKeyV1
            or self.observer_evidence_key.key_role != "OBSERVER_EVIDENCE"
            or self.observer_evidence_key.key_id
            != self.observer_evidence_key_id
        ):
            _fail("observer-signed private-replay attestation is malformed")
        payload = self._payload()
        if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=self.observer_evidence_key,
            message=_signing_bytes(payload),
            signature_hex=self.observer_signature_hex,
        ):
            _fail("observer-signed private-replay signature is invalid")
        object.__setattr__(
            self,
            "_attestation_id",
            _hash(
                "attestation",
                {
                    **payload,
                    "observer_signature_hex": self.observer_signature_hex,
                    "observer_signature_verified": True,
                },
            ),
        )

    def _projection(self) -> dict[str, Any]:
        return {
            "closure_id": self.closure_id,
            "occurrence_id": self.occurrence_id,
            "observer_session_public_id": self.observer_session_public_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "observer_open_authorization_id": (
                self.observer_open_authorization_id
            ),
            "private_reveal_attestation_id": (
                self.private_reveal_attestation_id
            ),
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "opaque_environment_commitment_id": (
                self.opaque_environment_commitment_id
            ),
            "signer_registry_id": self.signer_registry_id,
            "observer_evidence_key_id": self.observer_evidence_key_id,
            "ordered_entry_ids": list(self.ordered_entry_ids),
            "ordered_batch_ids": list(self.ordered_batch_ids),
            "ordered_stream_ids": list(self.ordered_stream_ids),
            "used_stream_graph_digest": self.used_stream_graph_digest,
            "replayed_batch_count": self.replayed_batch_count,
            "replayed_draw_count": self.replayed_draw_count,
            "replayed_stream_count": self.replayed_stream_count,
        }

    def _payload(self) -> dict[str, Any]:
        return _attestation_payload(
            source_private_replay_verification_id=(
                self.source_private_replay_verification_id
            ),
            projection=self._projection(),
        )

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "attestation_id": self.attestation_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


_ATTESTATION_DOCUMENT_KEYS = frozenset(
    {
        *_attestation_payload(
            source_private_replay_verification_id="0" * 64,
            projection={
                "closure_id": "0" * 64,
                "occurrence_id": "0" * 64,
                "observer_session_public_id": "0" * 64,
                "observer_open_binding_id": "0" * 64,
                "observer_open_authorization_id": "0" * 64,
                "private_reveal_attestation_id": "0" * 64,
                "remote_main_anchor_id": "0" * 64,
                "target_tape_namespace_id": "0" * 64,
                "opaque_environment_commitment_id": "0" * 64,
                "signer_registry_id": "0" * 64,
                "observer_evidence_key_id": "0" * 64,
                "ordered_entry_ids": ["0" * 64],
                "ordered_batch_ids": ["0" * 64],
                "ordered_stream_ids": ["0" * 64],
                "used_stream_graph_digest": "0" * 64,
                "replayed_batch_count": 1,
                "replayed_draw_count": 1,
                "replayed_stream_count": 1,
            },
        ),
        "observer_signature_hex",
        "observer_signature_verified",
        "attestation_id",
    }
)


def freeze_v075_observer_signed_private_replay_attestation_v2(
    *,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    closure: observer.V075ObserverBatchJournalClosureV2,
    authority_binding: observer.V075ObserverOpenAuthorityBindingV2,
    used_stream_identities: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    private_salt: bytes,
    private_environment: Iterable[
        Iterable[tuple[int, Fraction]]
    ],
    observer_signer: observer.V075ObserverEvidenceSignerProtocolV2,
) -> V075ObserverSignedPrivateReplayAttestationV2:
    """Privately replay and then sign within one trusted atomic call.

    The caller supplies private material and a trusted observer signer but
    cannot supply or substitute the replay-verification result.  This is a
    construction API discipline, not public cryptographic proof of execution
    order.  A production revision still needs a signer-owning sealed observer
    boundary.
    """

    projection = _public_projection(
        closure=closure,
        authority_binding=authority_binding,
        used_stream_identities=used_stream_identities,
    )
    if not isinstance(
        observer_signer,
        observer.V075ObserverEvidenceSignerProtocolV2,
    ):
        _fail("private-replay observer signer lacks the strict V2 protocol")
    expected_key = (
        authority_binding.namespace.signer_registry.observer_evidence_key
    )
    key = observer_signer.public_verification_key_v1()
    if (
        type(key) is not public.V075RSAPublicVerificationKeyV1
        or key != expected_key
        or key.key_role != "OBSERVER_EVIDENCE"
    ):
        _fail("private-replay observer signer is foreign")

    # The only admitted verification is minted by the real private verifier
    # during this call.  No legacy, exact-cloned, or caller-created
    # V075ObserverBatchClosureVerificationV2 has an input channel.
    try:
        verification = observer.verify_loaded_private_observer_batch_closure_v2(
            closure=closure,
            authority=authority,
            namespace=namespace,
            authority_binding=authority_binding,
            private_salt=private_salt,
            private_environment=private_environment,
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
    ) as error:
        raise (
            V075ObserverSignedPrivateReplayAttestationV2InvariantViolation(
                "trusted atomic freeze private replay failed"
            )
        ) from error
    verification_id = _verify_source_private_replay(
        verification=verification,
        projection=projection,
    )
    payload = _attestation_payload(
        source_private_replay_verification_id=verification_id,
        projection=projection,
    )
    signature = observer_signer.sign_observer_evidence_v1(
        _signing_bytes(payload)
    )
    if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=expected_key,
        message=_signing_bytes(payload),
        signature_hex=signature,
    ):
        _fail("private-replay observer signer emitted an invalid signature")
    return V075ObserverSignedPrivateReplayAttestationV2(
        _ATTESTATION_ISSUER,
        verification_id,
        projection["closure_id"],
        projection["occurrence_id"],
        projection["observer_session_public_id"],
        projection["observer_open_binding_id"],
        projection["observer_open_authorization_id"],
        projection["private_reveal_attestation_id"],
        projection["remote_main_anchor_id"],
        projection["target_tape_namespace_id"],
        projection["opaque_environment_commitment_id"],
        projection["signer_registry_id"],
        projection["observer_evidence_key_id"],
        tuple(projection["ordered_entry_ids"]),
        tuple(projection["ordered_batch_ids"]),
        tuple(projection["ordered_stream_ids"]),
        projection["used_stream_graph_digest"],
        projection["replayed_batch_count"],
        projection["replayed_draw_count"],
        projection["replayed_stream_count"],
        signature,
        expected_key,
    )


def verify_v075_observer_signed_private_replay_attestation_bytes_v2(
    *,
    raw: bytes,
    closure: observer.V075ObserverBatchJournalClosureV2,
    authority_binding: observer.V075ObserverOpenAuthorityBindingV2,
    used_stream_identities: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ],
) -> V075ObserverSignedPrivateReplayAttestationV2:
    """Verify the signed claim and recompute every publicly knowable field."""

    document = _strict_document(raw)
    if (
        set(document) != _ATTESTATION_DOCUMENT_KEYS
        or document["observer_signature_verified"] is not True
        or type(document["observer_signature_hex"]) is not str
    ):
        _fail("private-replay attestation keyset or signature claim changed")
    projection = _public_projection(
        closure=closure,
        authority_binding=authority_binding,
        used_stream_identities=used_stream_identities,
    )
    verification_id, _ = _expected_source_private_replay(projection)
    if (
        _cid(
            document["source_private_replay_verification_id"],
            "signed source private-replay verification",
        )
        != verification_id
    ):
        _fail(
            "signed source private-replay verification identity differs "
            "from the exact public closure projection"
        )
    expected_payload = _attestation_payload(
        source_private_replay_verification_id=verification_id,
        projection=projection,
    )
    if any(
        document[key] != value
        for key, value in expected_payload.items()
    ):
        _fail(
            "private-replay attestation public fields, profile, status, "
            "counts, or locks differ from exact replay"
        )
    attestation = V075ObserverSignedPrivateReplayAttestationV2(
        _ATTESTATION_ISSUER,
        verification_id,
        projection["closure_id"],
        projection["occurrence_id"],
        projection["observer_session_public_id"],
        projection["observer_open_binding_id"],
        projection["observer_open_authorization_id"],
        projection["private_reveal_attestation_id"],
        projection["remote_main_anchor_id"],
        projection["target_tape_namespace_id"],
        projection["opaque_environment_commitment_id"],
        projection["signer_registry_id"],
        projection["observer_evidence_key_id"],
        tuple(projection["ordered_entry_ids"]),
        tuple(projection["ordered_batch_ids"]),
        tuple(projection["ordered_stream_ids"]),
        projection["used_stream_graph_digest"],
        projection["replayed_batch_count"],
        projection["replayed_draw_count"],
        projection["replayed_stream_count"],
        document["observer_signature_hex"],
        authority_binding.namespace.signer_registry.observer_evidence_key,
    )
    if (
        document["attestation_id"] != attestation.attestation_id
        or attestation.canonical_bytes != raw
    ):
        _fail("private-replay attestation content identity differs")
    return attestation


def open_v075_observer_signed_private_replay_production_v2() -> NoReturn:
    """Fail closed until the new role is integrated into production replay."""

    raise V075ObserverSignedPrivateReplayAttestationProductionV2NotReady(
        "B3 is a trusted construction API, not public cryptographic proof "
        "of replay/sign order; production additionally requires a "
        "signer-owning sealed observer boundary and portable registry, "
        "occurrence-runner, and bundle-verifier integration"
    )


__all__ = [
    "ATTESTATION_ROLE",
    "CALLER_SUPPLIED_PRIVATE_REPLAY_VERIFICATION_ALLOWED",
    "CODE_PROVENANCE_COMPLETE",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "LEGACY_PRIVATE_REPLAY_VERIFICATION_UPGRADE_ALLOWED",
    "MAX_ATTESTATION_BYTES",
    "OBSERVER_OPEN_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRIVATE_REPLAY_ORDER_CLAIM_SCOPE",
    "PRIVATE_REPLAY_PROFILE_ID",
    "PRIVATE_REPLAY_STATUS",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "PUBLIC_VERIFIER_PRIVATE_INPUTS_ALLOWED",
    "RAW_SOURCE_VERIFICATION_ACCEPTED",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "SOURCE_PRIVATE_REPLAY_SCHEMA",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "TRUSTED_ATOMIC_FREEZE_PRIVATE_INPUTS_REQUIRED",
    "V075ObserverSignedPrivateReplayAttestationProductionV2NotReady",
    "V075ObserverSignedPrivateReplayAttestationV2",
    "V075ObserverSignedPrivateReplayAttestationV2InvariantViolation",
    "freeze_v075_observer_signed_private_replay_attestation_v2",
    "open_v075_observer_signed_private_replay_production_v2",
    "verify_v075_observer_signed_private_replay_attestation_bytes_v2",
]
