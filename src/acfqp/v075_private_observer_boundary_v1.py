"""Private observer boundary for a future production V0-075 campaign.

The public campaign graph deliberately cannot construct a transition kernel.
This module is the narrow boundary at which an independently verified
observer-open authority may be combined, in memory, with a private environment
reveal.  The reveal and its salt are used only to verify the already public
opaque commitment and to construct private exact H=2 kernels.  They are never
included in an observation, capability, journal, or verification artifact.

No production authority, private key, environment reveal, or transition law
is defined here.  A construction-only authority adapter exists so the boundary
can be attacked with synthetic unit-test material.  It is accepted only by a
separate construction entrypoint and can never enter the production one.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    Mapping,
    Protocol,
    runtime_checkable,
)

from acfqp.h2_graph_transition_engine_v1 import (
    DeterministicH2GraphStreamV1,
    H2GraphActionV1,
    H2GraphKernelV1,
    H2GraphSampleV1,
    H2GraphTransitionInvariantViolation,
    verify_deterministic_samples_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as public_graph

if TYPE_CHECKING:
    from acfqp.v075_preopen_target_authorization_v1 import (
        V075ObserverOpenAuthorizationV1,
    )


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v075_private_observer_boundary_v1"
PRODUCTION_ENVIRONMENT_INCLUDED = False
PRODUCTION_PRIVATE_SIGNER_INCLUDED = False
PRODUCTION_OPEN_AUTHORITY_INCLUDED = False

DOMAIN_TAGS = {
    "construction_authority": (
        "acfqp:v075-construction-only-observer-open-authority:v1"
    ),
    "open_binding": "acfqp:v075-observer-open-authority-binding:v1",
    "session": "acfqp:v075-private-observer-session-public-identity:v1",
    "observation": "acfqp:v075-signed-canonical-observation-record:v1",
    "journal_entry": "acfqp:v075-append-only-observer-journal-entry:v1",
    "journal_closure": "acfqp:v075-append-only-observer-journal-closure:v1",
    "capability": "acfqp:v075-public-observation-capability:v1",
    "closure_verification": (
        "acfqp:v075-private-observer-journal-closure-verification:v1"
    ),
}

if (
    len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values()))
    or any(
        not value.startswith("acfqp:v075-")
        for value in DOMAIN_TAGS.values()
    )
):
    raise RuntimeError("V0-075 observer-boundary domains must be unique")


class V075PrivateObserverBoundaryInvariantViolation(ValueError):
    """The private observer boundary or its public evidence was invalid."""


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PrivateObserverBoundaryInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PrivateObserverBoundaryInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V075PrivateObserverBoundaryInvariantViolation(
            "observer arithmetic must remain exact"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


class V075ObserverOpenAuthorityScopeV1(str, Enum):
    PRODUCTION_OPEN = "PRODUCTION_OPEN"
    CONSTRUCTION_ONLY = "CONSTRUCTION_ONLY"


@dataclass(frozen=True, slots=True)
class V075ObserverOpenAuthorityBindingV1:
    """Narrow public binding derived inside an observer entrypoint.

    This class is not an input authority: constructing it directly can never
    open the observer.  The production entrypoint derives it only after exact
    type and semantic checks on the issuer-gated remote-main authority.
    """

    namespace: public_authority.V075PublicTargetTapeNamespaceV1
    upstream_authority_id: str
    verification_attestation_id: str
    scope: V075ObserverOpenAuthorityScopeV1
    independent_final_authority_verified: bool
    observer_open_authorized: bool

    def __post_init__(self) -> None:
        if (
            type(self.namespace)
            is not public_authority.V075PublicTargetTapeNamespaceV1
            or type(self.scope) is not V075ObserverOpenAuthorityScopeV1
            or type(self.independent_final_authority_verified) is not bool
            or type(self.observer_open_authorized) is not bool
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "observer-open authority binding is not strictly typed"
            )
        _cid(self.upstream_authority_id, "upstream observer-open authority")
        _cid(
            self.verification_attestation_id,
            "observer-open verification attestation",
        )
        if self.scope is V075ObserverOpenAuthorityScopeV1.PRODUCTION_OPEN:
            if not (
                self.independent_final_authority_verified
                and self.observer_open_authorized
            ):
                raise V075PrivateObserverBoundaryInvariantViolation(
                    "production observer-open binding is not verified"
                )
        elif (
            self.independent_final_authority_verified
            or self.observer_open_authorized
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "construction authority cannot claim production verification"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_observer_open_authority_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "target_tape_namespace_id": (
                self.namespace.target_tape_namespace_id
            ),
            "environment_commitment_id": (
                self.namespace.environment_commitment.commitment_id
            ),
            "upstream_authority_id": self.upstream_authority_id,
            "verification_attestation_id": (
                self.verification_attestation_id
            ),
            "scope": self.scope.value,
            "independent_final_authority_verified": (
                self.independent_final_authority_verified
            ),
            "observer_open_authorized": self.observer_open_authorized,
            "construction_fixture": (
                self.scope
                is V075ObserverOpenAuthorityScopeV1.CONSTRUCTION_ONLY
            ),
            "public_binding_only": True,
            "private_material_serialized": False,
        }

    @property
    def binding_id(self) -> str:
        return _hash("open_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class V075ConstructionOnlyObserverOpenAuthorityFixtureV1:
    """Synthetic authority accepted only behind an explicit fixture opt-in."""

    namespace: public_authority.V075PublicTargetTapeNamespaceV1
    fixture_registration_id: str

    def __post_init__(self) -> None:
        if (
            type(self.namespace)
            is not public_authority.V075PublicTargetTapeNamespaceV1
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "construction authority requires one public namespace"
            )
        _cid(
            self.fixture_registration_id,
            "construction fixture registration",
        )

    @property
    def fixture_authority_id(self) -> str:
        return _hash(
            "construction_authority",
            {
                "schema": (
                    "acfqp.v075_construction_only_observer_open_authority.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "target_tape_namespace_id": (
                    self.namespace.target_tape_namespace_id
                ),
                "fixture_registration_id": self.fixture_registration_id,
                "scope": "CONSTRUCTION_ONLY",
                "production_claim_allowed": False,
            },
        )

    def verify_for_private_observer_v1(
        self,
        *,
        expected_target_tape_namespace_id: str,
        expected_environment_commitment_id: str,
    ) -> V075ObserverOpenAuthorityBindingV1:
        if (
            _cid(
                expected_target_tape_namespace_id,
                "expected target-tape namespace",
            )
            != self.namespace.target_tape_namespace_id
            or _cid(
                expected_environment_commitment_id,
                "expected environment commitment",
            )
            != self.namespace.environment_commitment.commitment_id
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "construction authority was transplanted"
            )
        return V075ObserverOpenAuthorityBindingV1(
            namespace=self.namespace,
            upstream_authority_id=self.fixture_authority_id,
            verification_attestation_id=self.fixture_registration_id,
            scope=V075ObserverOpenAuthorityScopeV1.CONSTRUCTION_ONLY,
            independent_final_authority_verified=False,
            observer_open_authorized=False,
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_only_observer_open_authority.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "target_tape_namespace_id": (
                self.namespace.target_tape_namespace_id
            ),
            "fixture_registration_id": self.fixture_registration_id,
            "fixture_authority_id": self.fixture_authority_id,
            "scope": "CONSTRUCTION_ONLY",
            "independent_final_authority_verified": False,
            "observer_open_authorized": False,
            "production_claim_allowed": False,
        }


@runtime_checkable
class V075ObserverEvidenceSignerProtocol(Protocol):
    """Private signer interface; an implementation is never serialized."""

    def public_verification_key_v1(
        self,
    ) -> public_authority.V075RSAPublicVerificationKeyV1:
        """Return the matching public observer-evidence key."""

    def sign_observer_evidence_v1(self, message: bytes) -> str:
        """Sign one canonical observer-evidence message."""


def _canonical_private_environment(
    *,
    family: public_authority.V075PublicFamilyGenerationV1,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    try:
        result = tuple(tuple(row) for row in private_environment)
    except TypeError as error:
        raise V075PrivateObserverBoundaryInvariantViolation(
            "private environment must be one concrete exact sequence"
        ) from error
    if len(result) != len(family.replicate_contexts):
        raise V075PrivateObserverBoundaryInvariantViolation(
            "private environment does not cover the public family"
        )
    # Kernel construction is the private arithmetic validator.  Nothing from
    # these kernels is returned to the caller or serialized.
    try:
        for context, row in zip(
            family.replicate_contexts,
            result,
            strict=True,
        ):
            H2GraphKernelV1(
                context.topology,
                context.rank_cap,
                context.horizon,
                row,
            )
    except H2GraphTransitionInvariantViolation as error:
        raise V075PrivateObserverBoundaryInvariantViolation(
            str(error)
        ) from error
    return result


def _require_production_open_binding(
    *,
    authority: "V075ObserverOpenAuthorizationV1",
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
) -> V075ObserverOpenAuthorityBindingV1:
    # Local import keeps the law-free pre-open verifier independent from this
    # private observer boundary in return.
    from acfqp import v075_preopen_target_authorization_v1 as preopen

    if (
        type(authority)
        is not preopen.V075ObserverOpenAuthorizationV1
        or type(namespace)
        is not public_authority.V075PublicTargetTapeNamespaceV1
    ):
        raise V075PrivateObserverBoundaryInvariantViolation(
            "production observer requires the exact independently issued "
            "reveal-attested pre-open authorization and one typed public "
            "namespace"
        )
    anchor = authority.anchor
    reveal = authority.private_reveal_attestation
    if (
        anchor.family_generation_id != namespace.family.generation_id
        or anchor.opaque_environment_commitment_id
        != namespace.environment_commitment.commitment_id
        or anchor.signer_registry != namespace.signer_registry
        or authority.signer_registry != namespace.signer_registry
        or authority.opaque_environment_commitment
        != namespace.environment_commitment
        or reveal.anchor != anchor
        or reveal.anchor.opaque_environment_commitment_id
        != namespace.environment_commitment.commitment_id
        or reveal.anchor.signer_registry != namespace.signer_registry
        or anchor.final_preregistration_id
        != namespace.final_preregistration.external_id
        or anchor.observer_profile_id
        != namespace.observer_profile.external_id
        or anchor.anchor_id
        != namespace.remote_main_anchor.external_id
    ):
        raise V075PrivateObserverBoundaryInvariantViolation(
            "production authority and public namespace do not share one "
            "independently anchored identity graph"
        )
    return V075ObserverOpenAuthorityBindingV1(
        namespace=namespace,
        upstream_authority_id=authority.authorization_id,
        verification_attestation_id=reveal.attestation_id,
        scope=V075ObserverOpenAuthorityScopeV1.PRODUCTION_OPEN,
        independent_final_authority_verified=True,
        observer_open_authorized=True,
    )


def _require_construction_open_binding(
    *,
    authority: V075ConstructionOnlyObserverOpenAuthorityFixtureV1,
) -> V075ObserverOpenAuthorityBindingV1:
    if (
        type(authority)
        is not V075ConstructionOnlyObserverOpenAuthorityFixtureV1
    ):
        raise V075PrivateObserverBoundaryInvariantViolation(
            "construction observer requires its exact domain-separated fixture"
        )
    namespace = authority.namespace
    binding = authority.verify_for_private_observer_v1(
        expected_target_tape_namespace_id=(
            namespace.target_tape_namespace_id
        ),
        expected_environment_commitment_id=(
            namespace.environment_commitment.commitment_id
        ),
    )
    if (
        type(binding) is not V075ObserverOpenAuthorityBindingV1
        or binding.namespace != namespace
        or binding.scope
        is not V075ObserverOpenAuthorityScopeV1.CONSTRUCTION_ONLY
        or binding.independent_final_authority_verified
        or binding.observer_open_authorized
    ):
        raise V075PrivateObserverBoundaryInvariantViolation(
            "construction observer-open fixture returned a foreign binding"
        )
    return binding


def _sign(
    *,
    signer: V075ObserverEvidenceSignerProtocol,
    expected_key: public_authority.V075RSAPublicVerificationKeyV1,
    message: bytes,
) -> str:
    if not isinstance(signer, V075ObserverEvidenceSignerProtocol):
        raise V075PrivateObserverBoundaryInvariantViolation(
            "observer signer does not implement the strict signer protocol"
        )
    public_key = signer.public_verification_key_v1()
    if (
        type(public_key)
        is not public_authority.V075RSAPublicVerificationKeyV1
        or public_key != expected_key
        or public_key.key_role != "OBSERVER_EVIDENCE"
    ):
        raise V075PrivateObserverBoundaryInvariantViolation(
            "private signer does not match the frozen observer-evidence key"
        )
    signature = signer.sign_observer_evidence_v1(message)
    if not public_authority.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=expected_key,
        message=message,
        signature_hex=signature,
    ):
        raise V075PrivateObserverBoundaryInvariantViolation(
            "private observer signer emitted an invalid signature"
        )
    return signature


def _observation_payload(
    *,
    session_public_id: str,
    authority_binding: V075ObserverOpenAuthorityBindingV1,
    stream_identity: public_graph.V075TransitionStreamIdentityV1,
    sample: H2GraphSampleV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_signed_canonical_observation_record.v1",
        "schema_version": SCHEMA_VERSION,
        "observer_session_public_id": _cid(
            session_public_id,
            "observer session",
        ),
        "observer_open_binding_id": authority_binding.binding_id,
        "observer_open_scope": authority_binding.scope.value,
        "target_tape_namespace_id": (
            stream_identity.target_tape_namespace_id
        ),
        "environment_commitment_id": (
            authority_binding.namespace.environment_commitment.commitment_id
        ),
        "observer_signer_key_id": (
            authority_binding.namespace.signer_registry
            .observer_evidence_key.key_id
        ),
        "context_id": stream_identity.context_id,
        "row_binding_id": stream_identity.row_binding_id,
        "catalogue_id": stream_identity.catalogue_id,
        "source_state_id": (
            stream_identity.row_binding.catalogue.state.state_id
        ),
        "remaining_horizon": (
            stream_identity.row_binding.remaining_horizon
        ),
        "action": list(stream_identity.action),
        "pairing_group_id": stream_identity.pairing_group_id,
        "pairing_lineage_id": stream_identity.pairing_lineage_id,
        "support_epoch_id": stream_identity.support_epoch_id,
        "observer_epoch_index": stream_identity.observer_epoch_index,
        "lane": stream_identity.lane.value,
        "arm": stream_identity.arm,
        "stream_id": stream_identity.stream_id,
        "accepted_draw_index": sample.accepted_draw_index,
        "random_word_start_index": sample.random_word_start_index,
        "random_words": list(sample.random_words),
        "next_ranks": list(sample.next_state.ranks),
        "failure": sample.failure,
        "terminal": sample.terminal,
        "spawn_cell": sample.spawn_cell,
        "spawn_rank": sample.spawn_rank,
        "realized_row_reward": _fdoc(sample.realized_row_reward),
        "arm_absent_from_raw_pairing_key": True,
        "private_material_serialized": False,
    }


def observation_record_signing_bytes_v1(
    *,
    session_public_id: str,
    authority_binding: V075ObserverOpenAuthorityBindingV1,
    stream_identity: public_graph.V075TransitionStreamIdentityV1,
    sample: H2GraphSampleV1,
) -> bytes:
    if (
        type(authority_binding)
        is not V075ObserverOpenAuthorityBindingV1
        or type(stream_identity)
        is not public_graph.V075TransitionStreamIdentityV1
        or type(sample) is not H2GraphSampleV1
        or stream_identity.namespace != authority_binding.namespace
    ):
        raise V075PrivateObserverBoundaryInvariantViolation(
            "observation signing graph is stale or untyped"
        )
    return (
        b"acfqp:v075-signed-canonical-observation-record:v1"
        + b"\x00"
        + canonical_json_bytes(
            _observation_payload(
                session_public_id=session_public_id,
                authority_binding=authority_binding,
                stream_identity=stream_identity,
                sample=sample,
            )
        )
    )


@dataclass(frozen=True, slots=True)
class V075SignedObservationRecordV1:
    session_public_id: str
    authority_binding: V075ObserverOpenAuthorityBindingV1
    stream_identity: public_graph.V075TransitionStreamIdentityV1
    sample: H2GraphSampleV1
    observer_signature_hex: str

    def __post_init__(self) -> None:
        if (
            type(self.authority_binding)
            is not V075ObserverOpenAuthorityBindingV1
            or type(self.stream_identity)
            is not public_graph.V075TransitionStreamIdentityV1
            or type(self.sample) is not H2GraphSampleV1
            or self.stream_identity.namespace
            != self.authority_binding.namespace
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "signed observation graph is stale or untyped"
            )
        _cid(self.session_public_id, "observer session")
        message = observation_record_signing_bytes_v1(
            session_public_id=self.session_public_id,
            authority_binding=self.authority_binding,
            stream_identity=self.stream_identity,
            sample=self.sample,
        )
        if not (
            public_authority.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
                public_key=(
                    self.authority_binding.namespace.signer_registry
                    .observer_evidence_key
                ),
                message=message,
                signature_hex=self.observer_signature_hex,
            )
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "observation signature is invalid or transplanted"
            )
        try:
            public_graph.V075SymbolicGraphStateV1(
                self.stream_identity.row_binding.context,
                self.sample.next_state.ranks,
                self.sample.next_state.failure,
            )
        except public_graph.V075PublicGraphSemanticsInvariantViolation as error:
            raise V075PrivateObserverBoundaryInvariantViolation(
                str(error)
            ) from error

    @property
    def record_id(self) -> str:
        return _hash(
            "observation",
            {
                **_observation_payload(
                    session_public_id=self.session_public_id,
                    authority_binding=self.authority_binding,
                    stream_identity=self.stream_identity,
                    sample=self.sample,
                ),
                "observer_signature_hex": self.observer_signature_hex,
                "observer_signature_verified": True,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_observation_payload(
                session_public_id=self.session_public_id,
                authority_binding=self.authority_binding,
                stream_identity=self.stream_identity,
                sample=self.sample,
            ),
            "observer_open_binding": self.authority_binding.to_document(),
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "record_id": self.record_id,
        }


@dataclass(frozen=True, slots=True)
class V075ObservationCapabilityV1:
    """Law-free observation payload safe for a planner or worker."""

    record: V075SignedObservationRecordV1

    def __post_init__(self) -> None:
        if type(self.record) is not V075SignedObservationRecordV1:
            raise V075PrivateObserverBoundaryInvariantViolation(
                "observation capability requires one signed record"
            )

    def _payload(self) -> dict[str, Any]:
        record = self.record
        sample = record.sample
        stream = record.stream_identity
        return {
            "schema": "acfqp.v075_public_observation_capability.v1",
            "schema_version": SCHEMA_VERSION,
            "observation_record_id": record.record_id,
            "target_tape_namespace_id": stream.target_tape_namespace_id,
            "environment_commitment_id": (
                record.authority_binding.namespace.environment_commitment
                .commitment_id
            ),
            "context_id": stream.context_id,
            "row_binding_id": stream.row_binding_id,
            "source_state_id": stream.row_binding.catalogue.state.state_id,
            "remaining_horizon": stream.row_binding.remaining_horizon,
            "action": list(stream.action),
            "stream_id": stream.stream_id,
            "pairing_group_id": stream.pairing_group_id,
            "observer_epoch_index": stream.observer_epoch_index,
            "lane": stream.lane.value,
            "arm": stream.arm,
            "accepted_draw_index": sample.accepted_draw_index,
            "next_ranks": list(sample.next_state.ranks),
            "failure": sample.failure,
            "terminal": sample.terminal,
            "spawn_cell": sample.spawn_cell,
            "spawn_rank": sample.spawn_rank,
            "realized_row_reward": _fdoc(sample.realized_row_reward),
            "observer_signature_hex": record.observer_signature_hex,
            "authority_scope": record.authority_binding.scope.value,
        }

    @property
    def capability_id(self) -> str:
        return _hash("capability", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "capability_id": self.capability_id}


@dataclass(frozen=True, slots=True)
class V075ObserverJournalEntryV1:
    sequence_number: int
    previous_entry_id: str | None
    record: V075SignedObservationRecordV1

    def __post_init__(self) -> None:
        if (
            type(self.sequence_number) is not int
            or self.sequence_number <= 0
            or type(self.record) is not V075SignedObservationRecordV1
            or (self.sequence_number == 1)
            != (self.previous_entry_id is None)
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "observer journal entry is malformed"
            )
        if self.previous_entry_id is not None:
            _cid(self.previous_entry_id, "previous observer journal entry")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_append_only_observer_journal_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "observer_session_public_id": self.record.session_public_id,
            "sequence_number": self.sequence_number,
            "previous_entry_id": self.previous_entry_id,
            "record_id": self.record.record_id,
        }

    @property
    def entry_id(self) -> str:
        return _hash("journal_entry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "record": self.record.to_document(),
            "entry_id": self.entry_id,
        }


def _journal_closure_payload(
    *,
    session_public_id: str,
    authority_binding: V075ObserverOpenAuthorityBindingV1,
    entries: tuple[V075ObserverJournalEntryV1, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_append_only_observer_journal_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "observer_session_public_id": _cid(
            session_public_id,
            "observer session",
        ),
        "observer_open_binding_id": authority_binding.binding_id,
        "target_tape_namespace_id": (
            authority_binding.namespace.target_tape_namespace_id
        ),
        "environment_commitment_id": (
            authority_binding.namespace.environment_commitment.commitment_id
        ),
        "entry_ids": [entry.entry_id for entry in entries],
        "entry_count": len(entries),
        "tail_entry_id": None if not entries else entries[-1].entry_id,
        "append_only_hash_chain_closed": True,
        "private_material_serialized": False,
    }


def observer_journal_closure_signing_bytes_v1(
    *,
    session_public_id: str,
    authority_binding: V075ObserverOpenAuthorityBindingV1,
    entries: tuple[V075ObserverJournalEntryV1, ...],
) -> bytes:
    if (
        type(authority_binding)
        is not V075ObserverOpenAuthorityBindingV1
        or type(entries) is not tuple
        or any(
            type(entry) is not V075ObserverJournalEntryV1
            for entry in entries
        )
    ):
        raise V075PrivateObserverBoundaryInvariantViolation(
            "journal closure signing graph is untyped"
        )
    return (
        b"acfqp:v075-append-only-observer-journal-closure:v1"
        + b"\x00"
        + canonical_json_bytes(
            _journal_closure_payload(
                session_public_id=session_public_id,
                authority_binding=authority_binding,
                entries=entries,
            )
        )
    )


@dataclass(frozen=True, slots=True)
class V075ObserverJournalClosureV1:
    session_public_id: str
    authority_binding: V075ObserverOpenAuthorityBindingV1
    entries: tuple[V075ObserverJournalEntryV1, ...]
    observer_signature_hex: str

    def __post_init__(self) -> None:
        if (
            type(self.authority_binding)
            is not V075ObserverOpenAuthorityBindingV1
            or type(self.entries) is not tuple
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "observer journal closure is untyped"
            )
        _cid(self.session_public_id, "observer session")
        previous: str | None = None
        for index, entry in enumerate(self.entries, start=1):
            if (
                type(entry) is not V075ObserverJournalEntryV1
                or entry.sequence_number != index
                or entry.previous_entry_id != previous
                or entry.record.session_public_id != self.session_public_id
                or entry.record.authority_binding != self.authority_binding
            ):
                raise V075PrivateObserverBoundaryInvariantViolation(
                    "observer journal is gapped, reordered, or transplanted"
                )
            previous = entry.entry_id
        message = observer_journal_closure_signing_bytes_v1(
            session_public_id=self.session_public_id,
            authority_binding=self.authority_binding,
            entries=self.entries,
        )
        if not (
            public_authority.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
                public_key=(
                    self.authority_binding.namespace.signer_registry
                    .observer_evidence_key
                ),
                message=message,
                signature_hex=self.observer_signature_hex,
            )
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "observer journal closure signature is invalid"
            )

    @property
    def closure_id(self) -> str:
        return _hash(
            "journal_closure",
            {
                **_journal_closure_payload(
                    session_public_id=self.session_public_id,
                    authority_binding=self.authority_binding,
                    entries=self.entries,
                ),
                "observer_signature_hex": self.observer_signature_hex,
                "observer_signature_verified": True,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_journal_closure_payload(
                session_public_id=self.session_public_id,
                authority_binding=self.authority_binding,
                entries=self.entries,
            ),
            "observer_open_binding": self.authority_binding.to_document(),
            "entries": [entry.to_document() for entry in self.entries],
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "closure_id": self.closure_id,
        }


class _AppendOnlyObserverJournalV1:
    __slots__ = (
        "_authority_binding",
        "_closed",
        "_entries",
        "_session_public_id",
    )

    def __init__(
        self,
        *,
        session_public_id: str,
        authority_binding: V075ObserverOpenAuthorityBindingV1,
    ) -> None:
        self._session_public_id = _cid(
            session_public_id,
            "observer session",
        )
        self._authority_binding = authority_binding
        self._entries: list[V075ObserverJournalEntryV1] = []
        self._closed = False

    @property
    def entries(self) -> tuple[V075ObserverJournalEntryV1, ...]:
        return tuple(self._entries)

    def append(
        self,
        record: V075SignedObservationRecordV1,
    ) -> V075ObserverJournalEntryV1:
        if self._closed:
            raise V075PrivateObserverBoundaryInvariantViolation(
                "observer journal is already closed"
            )
        if (
            type(record) is not V075SignedObservationRecordV1
            or record.session_public_id != self._session_public_id
            or record.authority_binding != self._authority_binding
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "observer journal rejected a foreign record"
            )
        entry = V075ObserverJournalEntryV1(
            len(self._entries) + 1,
            None if not self._entries else self._entries[-1].entry_id,
            record,
        )
        self._entries.append(entry)
        return entry

    def close(
        self,
        *,
        signer: V075ObserverEvidenceSignerProtocol,
    ) -> V075ObserverJournalClosureV1:
        if self._closed:
            raise V075PrivateObserverBoundaryInvariantViolation(
                "observer journal already emitted its unique closure"
            )
        entries = self.entries
        message = observer_journal_closure_signing_bytes_v1(
            session_public_id=self._session_public_id,
            authority_binding=self._authority_binding,
            entries=entries,
        )
        signature = _sign(
            signer=signer,
            expected_key=(
                self._authority_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=message,
        )
        closure = V075ObserverJournalClosureV1(
            self._session_public_id,
            self._authority_binding,
            entries,
            signature,
        )
        self._closed = True
        return closure


_SESSION_ISSUER = object()


class V075PrivateObserverSessionV1:
    """Private mutable session; only law-free records cross its boundary."""

    __slots__ = (
        "_authority_binding",
        "_closed",
        "_journal",
        "_kernels",
        "_session_public_id",
        "_signer",
        "_streams",
    )

    def __init__(
        self,
        *,
        authority_binding: V075ObserverOpenAuthorityBindingV1,
        kernels: Mapping[str, H2GraphKernelV1],
        signer: V075ObserverEvidenceSignerProtocol,
        session_external_id: str,
        issuer: object,
    ) -> None:
        if issuer is not _SESSION_ISSUER:
            raise V075PrivateObserverBoundaryInvariantViolation(
                "private observer sessions must be opened by the boundary"
            )
        external_id = _cid(session_external_id, "observer session external")
        self._authority_binding = authority_binding
        self._session_public_id = _hash(
            "session",
            {
                "schema": (
                    "acfqp.v075_private_observer_session_public_identity.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "observer_open_binding_id": authority_binding.binding_id,
                "target_tape_namespace_id": (
                    authority_binding.namespace.target_tape_namespace_id
                ),
                "environment_commitment_id": (
                    authority_binding.namespace.environment_commitment
                    .commitment_id
                ),
                "observer_signer_key_id": (
                    authority_binding.namespace.signer_registry
                    .observer_evidence_key.key_id
                ),
                "session_external_id": external_id,
                "private_material_serialized": False,
            },
        )
        self._kernels = dict(kernels)
        self._signer = signer
        self._streams: dict[
            str,
            DeterministicH2GraphStreamV1,
        ] = {}
        self._journal = _AppendOnlyObserverJournalV1(
            session_public_id=self._session_public_id,
            authority_binding=authority_binding,
        )
        self._closed = False

    @property
    def session_public_id(self) -> str:
        return self._session_public_id

    @property
    def authority_binding(
        self,
    ) -> V075ObserverOpenAuthorityBindingV1:
        return self._authority_binding

    @property
    def journal_entries(
        self,
    ) -> tuple[V075ObserverJournalEntryV1, ...]:
        return self._journal.entries

    def public_session_document_v1(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_private_observer_session_public_identity.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "observer_session_public_id": self._session_public_id,
            "observer_open_binding_id": self._authority_binding.binding_id,
            "target_tape_namespace_id": (
                self._authority_binding.namespace.target_tape_namespace_id
            ),
            "environment_commitment_id": (
                self._authority_binding.namespace.environment_commitment
                .commitment_id
            ),
            "observer_signer_key_id": (
                self._authority_binding.namespace.signer_registry
                .observer_evidence_key.key_id
            ),
            "authority_scope": self._authority_binding.scope.value,
            "private_material_serialized": False,
        }

    def observe_v1(
        self,
        stream_identity: public_graph.V075TransitionStreamIdentityV1,
    ) -> V075ObservationCapabilityV1:
        if self._closed:
            raise V075PrivateObserverBoundaryInvariantViolation(
                "private observer session is closed"
            )
        if (
            type(stream_identity)
            is not public_graph.V075TransitionStreamIdentityV1
            or stream_identity.namespace
            != self._authority_binding.namespace
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "observer stream identity is untyped or transplanted"
            )
        context = stream_identity.row_binding.context
        kernel = self._kernels.get(context.context_id)
        if type(kernel) is not H2GraphKernelV1:
            raise V075PrivateObserverBoundaryInvariantViolation(
                "observer lacks the private kernel for this context"
            )
        stream = self._streams.get(stream_identity.stream_id)
        if stream is None:
            try:
                stream = DeterministicH2GraphStreamV1(
                    kernel=kernel,
                    state=(
                        stream_identity.row_binding.catalogue.state
                        .to_kernel_state()
                    ),
                    action=H2GraphActionV1(
                        *stream_identity.row_binding.action
                    ),
                    remaining_horizon=(
                        stream_identity.row_binding.remaining_horizon
                    ),
                    seed=stream_identity.seed,
                )
            except H2GraphTransitionInvariantViolation as error:
                raise V075PrivateObserverBoundaryInvariantViolation(
                    str(error)
                ) from error
            self._streams[stream_identity.stream_id] = stream
        sample = stream.draw()
        signing_bytes = observation_record_signing_bytes_v1(
            session_public_id=self._session_public_id,
            authority_binding=self._authority_binding,
            stream_identity=stream_identity,
            sample=sample,
        )
        signature = _sign(
            signer=self._signer,
            expected_key=(
                self._authority_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=signing_bytes,
        )
        record = V075SignedObservationRecordV1(
            self._session_public_id,
            self._authority_binding,
            stream_identity,
            sample,
            signature,
        )
        self._journal.append(record)
        return V075ObservationCapabilityV1(record)

    def close_v1(self) -> V075ObserverJournalClosureV1:
        if self._closed:
            raise V075PrivateObserverBoundaryInvariantViolation(
                "private observer session already closed"
            )
        closure = self._journal.close(signer=self._signer)
        self._closed = True
        self._streams.clear()
        self._kernels.clear()
        return closure


def _open_private_observer_from_binding_v1(
    *,
    binding: V075ObserverOpenAuthorityBindingV1,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
    observer_signer: V075ObserverEvidenceSignerProtocol,
    session_external_id: str,
) -> V075PrivateObserverSessionV1:
    environment = _canonical_private_environment(
        family=binding.namespace.family,
        private_environment=private_environment,
    )
    try:
        reveal = public_authority.verify_opaque_environment_reveal_v1(
            commitment=binding.namespace.environment_commitment,
            secret_salt=private_salt,
            secret_laws=environment,
        )
    except (
        public_authority.V075PublicCampaignAuthorityInvariantViolation
    ) as error:
        raise V075PrivateObserverBoundaryInvariantViolation(
            str(error)
        ) from error
    if not reveal.matched:
        raise V075PrivateObserverBoundaryInvariantViolation(
            "private environment reveal does not match the opaque commitment"
        )
    signer_key = observer_signer.public_verification_key_v1()
    expected_key = (
        binding.namespace.signer_registry.observer_evidence_key
    )
    if signer_key != expected_key:
        raise V075PrivateObserverBoundaryInvariantViolation(
            "observer signer is not bound to the target namespace"
        )
    kernels = {
        context.context_id: H2GraphKernelV1(
            context.topology,
            context.rank_cap,
            context.horizon,
            law,
        )
        for context, law in zip(
            binding.namespace.family.replicate_contexts,
            environment,
            strict=True,
        )
    }
    return V075PrivateObserverSessionV1(
        authority_binding=binding,
        kernels=kernels,
        signer=observer_signer,
        session_external_id=session_external_id,
        issuer=_SESSION_ISSUER,
    )


def open_private_observer_v1(
    *,
    authority: "V075ObserverOpenAuthorizationV1",
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
    observer_signer: V075ObserverEvidenceSignerProtocol,
    session_external_id: str,
) -> V075PrivateObserverSessionV1:
    """Production constructor; construction authorities are always rejected."""

    binding = _require_production_open_binding(
        authority=authority,
        namespace=namespace,
    )
    return _open_private_observer_from_binding_v1(
        binding=binding,
        private_salt=private_salt,
        private_environment=private_environment,
        observer_signer=observer_signer,
        session_external_id=session_external_id,
    )


def open_construction_private_observer_fixture_v1(
    *,
    authority: V075ConstructionOnlyObserverOpenAuthorityFixtureV1,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
    observer_signer: V075ObserverEvidenceSignerProtocol,
    session_external_id: str,
) -> V075PrivateObserverSessionV1:
    """Construction-only constructor with a disjoint exact authority type."""

    binding = _require_construction_open_binding(authority=authority)
    return _open_private_observer_from_binding_v1(
        binding=binding,
        private_salt=private_salt,
        private_environment=private_environment,
        observer_signer=observer_signer,
        session_external_id=session_external_id,
    )


@dataclass(frozen=True, slots=True)
class V075ObserverClosureVerificationV1:
    closure_id: str
    observer_open_binding_id: str
    replayed_record_count: int
    replayed_stream_count: int

    def __post_init__(self) -> None:
        _cid(self.closure_id, "observer journal closure")
        _cid(self.observer_open_binding_id, "observer-open binding")
        if (
            type(self.replayed_record_count) is not int
            or self.replayed_record_count < 0
            or type(self.replayed_stream_count) is not int
            or self.replayed_stream_count < 0
        ):
            raise V075PrivateObserverBoundaryInvariantViolation(
                "closure replay counts are invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_private_observer_journal_closure_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "closure_id": self.closure_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "verification_result": "EXACT_REPLAY_VERIFIED",
            "replayed_record_count": self.replayed_record_count,
            "replayed_stream_count": self.replayed_stream_count,
            "private_material_serialized": False,
        }

    @property
    def verification_id(self) -> str:
        return _hash("closure_verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _verify_private_observer_journal_closure_from_binding_v1(
    *,
    closure: V075ObserverJournalClosureV1,
    binding: V075ObserverOpenAuthorityBindingV1,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075ObserverClosureVerificationV1:
    """Replay every stream prefix from the arm-free seed at closure."""

    if type(closure) is not V075ObserverJournalClosureV1:
        raise V075PrivateObserverBoundaryInvariantViolation(
            "closure replay requires one typed observer journal"
        )
    if binding != closure.authority_binding:
        raise V075PrivateObserverBoundaryInvariantViolation(
            "closure authority was transplanted"
        )
    environment = _canonical_private_environment(
        family=binding.namespace.family,
        private_environment=private_environment,
    )
    try:
        reveal = public_authority.verify_opaque_environment_reveal_v1(
            commitment=binding.namespace.environment_commitment,
            secret_salt=private_salt,
            secret_laws=environment,
        )
    except (
        public_authority.V075PublicCampaignAuthorityInvariantViolation
    ) as error:
        raise V075PrivateObserverBoundaryInvariantViolation(
            str(error)
        ) from error
    if not reveal.matched:
        raise V075PrivateObserverBoundaryInvariantViolation(
            "closure replay reveal does not match the opaque commitment"
        )
    kernels = {
        context.context_id: H2GraphKernelV1(
            context.topology,
            context.rank_cap,
            context.horizon,
            law,
        )
        for context, law in zip(
            binding.namespace.family.replicate_contexts,
            environment,
            strict=True,
        )
    }
    groups: dict[
        str,
        list[V075SignedObservationRecordV1],
    ] = {}
    stream_identity_by_id: dict[
        str,
        public_graph.V075TransitionStreamIdentityV1,
    ] = {}
    for entry in closure.entries:
        record = entry.record
        stream_id = record.stream_identity.stream_id
        prior = stream_identity_by_id.setdefault(
            stream_id,
            record.stream_identity,
        )
        if prior != record.stream_identity:
            raise V075PrivateObserverBoundaryInvariantViolation(
                "one stream ID was assigned multiple typed identities"
            )
        groups.setdefault(stream_id, []).append(record)
    try:
        for stream_id, records in groups.items():
            stream_identity = stream_identity_by_id[stream_id]
            if tuple(
                record.sample.accepted_draw_index
                for record in records
            ) != tuple(range(1, len(records) + 1)):
                raise V075PrivateObserverBoundaryInvariantViolation(
                    "stream sample prefix is gapped or reordered"
                )
            kernel = kernels[stream_identity.context_id]
            verify_deterministic_samples_v1(
                kernel=kernel,
                state=(
                    stream_identity.row_binding.catalogue.state
                    .to_kernel_state()
                ),
                action=H2GraphActionV1(*stream_identity.action),
                remaining_horizon=(
                    stream_identity.row_binding.remaining_horizon
                ),
                seed=stream_identity.seed,
                samples=tuple(record.sample for record in records),
            )
    except (
        H2GraphTransitionInvariantViolation,
        KeyError,
    ) as error:
        raise V075PrivateObserverBoundaryInvariantViolation(
            str(error)
        ) from error
    return V075ObserverClosureVerificationV1(
        closure.closure_id,
        binding.binding_id,
        len(closure.entries),
        len(groups),
    )


def verify_private_observer_journal_closure_v1(
    *,
    closure: V075ObserverJournalClosureV1,
    authority: "V075ObserverOpenAuthorizationV1",
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075ObserverClosureVerificationV1:
    """Production closure replay; rejects construction authority exactly."""

    binding = _require_production_open_binding(
        authority=authority,
        namespace=namespace,
    )
    return _verify_private_observer_journal_closure_from_binding_v1(
        closure=closure,
        binding=binding,
        private_salt=private_salt,
        private_environment=private_environment,
    )


def verify_construction_private_observer_journal_closure_v1(
    *,
    closure: V075ObserverJournalClosureV1,
    authority: V075ConstructionOnlyObserverOpenAuthorityFixtureV1,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075ObserverClosureVerificationV1:
    """Construction-only closure replay with a disjoint authority type."""

    binding = _require_construction_open_binding(authority=authority)
    return _verify_private_observer_journal_closure_from_binding_v1(
        closure=closure,
        binding=binding,
        private_salt=private_salt,
        private_environment=private_environment,
    )


__all__ = [
    "DOMAIN_TAGS",
    "PROFILE_KEY",
    "PRODUCTION_ENVIRONMENT_INCLUDED",
    "PRODUCTION_OPEN_AUTHORITY_INCLUDED",
    "PRODUCTION_PRIVATE_SIGNER_INCLUDED",
    "SCHEMA_VERSION",
    "V075ConstructionOnlyObserverOpenAuthorityFixtureV1",
    "V075ObservationCapabilityV1",
    "V075ObserverClosureVerificationV1",
    "V075ObserverEvidenceSignerProtocol",
    "V075ObserverJournalClosureV1",
    "V075ObserverJournalEntryV1",
    "V075ObserverOpenAuthorityBindingV1",
    "V075ObserverOpenAuthorityScopeV1",
    "V075PrivateObserverBoundaryInvariantViolation",
    "V075PrivateObserverSessionV1",
    "V075SignedObservationRecordV1",
    "observation_record_signing_bytes_v1",
    "observer_journal_closure_signing_bytes_v1",
    "open_construction_private_observer_fixture_v1",
    "open_private_observer_v1",
    "verify_construction_private_observer_journal_closure_v1",
    "verify_private_observer_journal_closure_v1",
]
