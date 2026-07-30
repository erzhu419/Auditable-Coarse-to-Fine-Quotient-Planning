"""Target-free raw authority for the portable observer-open binding.

This adapter accepts only canonical public-context closure bytes and canonical
observer-open binding bytes.  It first replays the complete public-context
closure, then passes the closure's three canonical dependency artifacts to the
issuer-owning observer boundary.  No caller-created typed authorization,
namespace, reveal attestation, or binding can enter this surface.

The observer-open binding is namespace scoped.  Session and occurrence-context
identities first appear in later signed request/control records, so this B1
authority deliberately does not invent either identity.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_portable_public_context_closure_v2 as public_context
from acfqp import v075_private_observer_boundary_v2 as observer


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.66.0"
PROFILE_KEY = "v075_portable_observer_open_binding_authority_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
M1_ROLE_SEMANTICS_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
OBSERVER_OPEN_ALLOWED = False
PRIVATE_INPUT_CHANNELS_ALLOWED = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_M1_B1_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = "B1_OBSERVER_OPEN_BINDING_REPLAYED_M1_INCOMPLETE"
MAX_OUTPUT_BYTES = 1024 * 1024

DOMAIN_TAGS = MappingProxyType(
    {
        "result": (
            "acfqp:v075-portable-observer-open-binding-authority:v2"
        ),
    }
)


class V075PortableObserverOpenBindingV2InvariantViolation(ValueError):
    """The public closure or observer-open binding failed raw replay."""


class V075PortableObserverOpenBindingProductionV2NotReady(RuntimeError):
    """B1 cannot authorize production or the incomplete M1 registry."""


def _fail(message: str) -> NoReturn:
    raise V075PortableObserverOpenBindingV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableObserverOpenBindingV2InvariantViolation(
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
        raise V075PortableObserverOpenBindingV2InvariantViolation(
            str(error)
        ) from error


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableObserverOpenBindingReplayV2:
    """Issuer-backed B1 result retaining the reconstructed typed binding."""

    _issuer: InitVar[object]
    public_context_closure_id: str
    repository_binding_id: str
    source_manifest_id: str
    remote_main_anchor_id: str
    target_tape_namespace_id: str
    namespace_public_key_id: str
    observer_open_authorization_id: str
    private_reveal_attestation_id: str
    observer_open_binding: observer.V075ObserverOpenAuthorityBindingV2 = field(
        repr=False
    )
    canonical_binding_sha256: str
    canonical_binding_bytes: int
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.public_context_closure_id, "B1 public-context closure"),
            (self.repository_binding_id, "B1 repository binding"),
            (self.source_manifest_id, "B1 source manifest"),
            (self.remote_main_anchor_id, "B1 remote-main anchor"),
            (self.target_tape_namespace_id, "B1 target namespace"),
            (self.namespace_public_key_id, "B1 namespace public key"),
            (
                self.observer_open_authorization_id,
                "B1 observer-open authorization",
            ),
            (
                self.private_reveal_attestation_id,
                "B1 private reveal attestation",
            ),
            (self.canonical_binding_sha256, "B1 binding bytes"),
        ):
            _cid(value, label)
        binding = self.observer_open_binding
        if (
            _issuer is not _RESULT_ISSUER
            or type(binding)
            is not observer.V075ObserverOpenAuthorityBindingV2
            or binding.binding_id
            != _cid(binding.binding_id, "B1 observer-open binding")
            or binding.authorization_id
            != self.observer_open_authorization_id
            or binding.private_reveal_attestation_id
            != self.private_reveal_attestation_id
            or binding.remote_main_anchor_id != self.remote_main_anchor_id
            or binding.namespace.target_tape_namespace_id
            != self.target_tape_namespace_id
            or (
                binding.namespace.signer_registry.observer_evidence_key.key_id
                != self.namespace_public_key_id
            )
            or type(self.canonical_binding_bytes) is not int
            or not 0
            < self.canonical_binding_bytes
            <= observer.MAX_OBSERVER_OPEN_BINDING_BYTES
            or hashlib.sha256(
                canonical_json_bytes(binding.to_document())
            ).hexdigest()
            != self.canonical_binding_sha256
            or len(canonical_json_bytes(binding.to_document()))
            != self.canonical_binding_bytes
        ):
            _fail("B1 replay result is mistyped, stale, or transplanted")
        object.__setattr__(
            self,
            "_result_id",
            _hash("result", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        binding = self.observer_open_binding
        return {
            "schema": (
                "acfqp.v075_portable_observer_open_binding_replay.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "public_context_closure_id": self.public_context_closure_id,
            "repository_binding_id": self.repository_binding_id,
            "source_manifest_id": self.source_manifest_id,
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "namespace_public_key_id": self.namespace_public_key_id,
            "observer_open_authorization_id": (
                self.observer_open_authorization_id
            ),
            "private_reveal_attestation_id": (
                self.private_reveal_attestation_id
            ),
            "observer_open_binding_id": binding.binding_id,
            "canonical_binding_sha256": self.canonical_binding_sha256,
            "canonical_binding_bytes": self.canonical_binding_bytes,
            "public_context_closure_raw_replayed": True,
            "authorization_signature_graph_replayed": True,
            "namespace_public_key_replayed": True,
            "observer_open_binding_raw_replayed": True,
            "observer_open_binding_semantics_complete": True,
            "session_identity": {
                "kind": "NOT_APPLICABLE",
                "reason": (
                    "OBSERVER_OPEN_BINDING_IS_NAMESPACE_SCOPED_AND_PRECEDES_"
                    "SESSION_CREATION"
                ),
            },
            "occurrence_context_identity": {
                "kind": "NOT_APPLICABLE",
                "reason": (
                    "OBSERVER_OPEN_BINDING_IS_NAMESPACE_SCOPED_AND_SHARED_"
                    "ACROSS_PREREGISTERED_CONTEXTS"
                ),
            },
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "m1_role_semantics_complete": False,
            "portable_semantic_registry_complete": False,
            "observer_opened": False,
            "private_input_channels_allowed": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "private_material_serialized": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    @property
    def canonical_bytes(self) -> bytes:
        raw = canonical_json_bytes(self.to_document())
        if len(raw) > MAX_OUTPUT_BYTES:
            _fail("B1 replay result exceeds its output byte cap")
        return raw

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def replay_v075_portable_observer_open_binding_v2(
    *,
    repository_root: str | Path,
    public_context_closure_bytes: bytes,
    observer_open_binding_bytes: bytes,
) -> V075PortableObserverOpenBindingReplayV2:
    """Replay B1 from raw bytes only; caller-created typed inputs are invalid."""

    if (
        type(public_context_closure_bytes) is not bytes
        or type(observer_open_binding_bytes) is not bytes
    ):
        _fail("B1 accepts canonical bytes only")
    try:
        closure = (
            public_context
            .verify_v075_portable_public_context_evidence_closure_bytes_v2(
                repository_root=repository_root,
                raw=public_context_closure_bytes,
            )
        )
    except Exception as error:
        raise V075PortableObserverOpenBindingV2InvariantViolation(
            "B1 public-context closure failed raw replay"
        ) from error
    records = {item.role: item for item in closure.dependency_records}
    roles = tuple(public_context.V075PortablePublicContextDependencyRoleV2)
    if set(records) != set(roles):
        _fail("B1 public-context closure omits one exact dependency role")
    try:
        binding = (
            observer
            .replay_v075_observer_open_authority_binding_bytes_v2(
                repository_root=repository_root,
                namespace_bytes=records[roles[0]].canonical_artifact_bytes,
                claimed_authorization_bytes=(
                    records[roles[1]].canonical_artifact_bytes
                ),
                private_reveal_attestation_bytes=(
                    records[roles[2]].canonical_artifact_bytes
                ),
                observer_open_binding_bytes=observer_open_binding_bytes,
            )
        )
    except Exception as error:
        raise V075PortableObserverOpenBindingV2InvariantViolation(
            "B1 observer-open binding failed issuer-backed raw replay"
        ) from error
    key = binding.namespace.signer_registry.observer_evidence_key
    if (
        closure.remote_main_anchor_id != binding.remote_main_anchor_id
        or closure.namespace_public_key_id != key.key_id
        or closure.opaque_environment_commitment_id
        != binding.namespace.environment_commitment.commitment_id
    ):
        _fail("B1 binding and public-context closure were transplanted")
    return V075PortableObserverOpenBindingReplayV2(
        _RESULT_ISSUER,
        closure.closure_id,
        closure.repository_binding.binding_id,
        closure.source_manifest.manifest_id,
        closure.remote_main_anchor_id,
        binding.namespace.target_tape_namespace_id,
        key.key_id,
        binding.authorization_id,
        binding.private_reveal_attestation_id,
        binding,
        hashlib.sha256(observer_open_binding_bytes).hexdigest(),
        len(observer_open_binding_bytes),
    )


def open_v075_production_from_portable_observer_open_binding_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PortableObserverOpenBindingProductionV2NotReady(
        "B1 observer-open binding replay is complete, but source authority, "
        "code provenance, the remaining M1 roles, and the aggregate portable "
        "semantic registry remain incomplete"
    )


__all__ = [
    "CODE_PROVENANCE_COMPLETE",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "M1_ROLE_SEMANTICS_COMPLETE",
    "OBSERVER_OPEN_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRIVATE_INPUT_CHANNELS_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "V075PortableObserverOpenBindingProductionV2NotReady",
    "V075PortableObserverOpenBindingReplayV2",
    "V075PortableObserverOpenBindingV2InvariantViolation",
    "open_v075_production_from_portable_observer_open_binding_v2",
    "replay_v075_portable_observer_open_binding_v2",
]
