"""Fail-closed pre-open authorization chain for the V0-075 target.

This module consumes only public Git objects and a signed, law-free private
reveal attestation.  It never receives a reveal salt, transition law, random
tape, kernel, observer session, or observer callback, and it has no operation
that can open an observer.

The production chain is:

    first qualifying origin/main semantic anchor
      -> exact tracked manifest/final blobs
      -> complete component and authority-binding registries
      -> exact public signer registry and opaque commitment
      -> signed private-reveal MATCH attestation
      -> typed ObserverOpenAuthorizationV1

The final type means that all *pre-open* obligations passed.  Minting it does
not open an observer; ``observer_open_performed`` remains false.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import subprocess
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_remote_main_anchor_verifier_v1 as anchor_verifier


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_preopen_target_authorization_v1"

PRIVATE_REVEAL_SIGNING_DOMAIN = (
    b"acfqp:v075-private-reveal-attestation-signing:v1"
)

DOMAIN_TAGS = {
    "private_reveal_attestation": (
        "acfqp:v075-private-reveal-attestation:v1"
    ),
    "tracked_blob_closure": (
        "acfqp:v075-preopen-tracked-blob-closure:v1"
    ),
    "observer_open_authorization": (
        "acfqp:v075-observer-open-authorization:v1"
    ),
    "readiness": "acfqp:v075-preopen-authorization-readiness:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 pre-open content domains must be unique")


class V075PreopenAuthorizationInvariantViolation(ValueError):
    """A public identity, signature, blob, or semantic binding failed."""


class V075PreopenAuthorizationNotReady(RuntimeError):
    """The complete target pre-open chain is not yet authorizing."""


def _fail(message: str) -> None:
    raise V075PreopenAuthorizationInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PreopenAuthorizationInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PreopenAuthorizationInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _git_oid(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field_name} must be one lowercase Git object ID")
    return value


def _strict_document(
    raw: bytes,
    *,
    expected_keys: set[str],
    label: str,
) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > 16 * 1024 * 1024:
        _fail(f"{label} bytes are empty, mistyped, or over cap")
    try:
        value = loads_canonical_json(raw)
    except (Phase3EIdentityError, ValueError) as error:
        raise V075PreopenAuthorizationInvariantViolation(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or set(value) != expected_keys:
        _fail(f"{label} field set changed")
    return value


_REVEAL_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "remote_main_anchor_id",
    "anchor_commit_id",
    "final_preregistration_id",
    "family_generation_id",
    "opaque_environment_commitment_id",
    "observer_profile_id",
    "signer_registry_id",
    "observer_evidence_key_id",
    "private_verification_external_id",
    "verification_result",
    "private_reveal_semantically_verified",
    "secret_salt_serialized",
    "private_environment_serialized",
    "transition_law_serialized",
    "random_tape_serialized",
    "observer_open_performed",
    "observer_session_created",
}


def _private_reveal_payload(
    *,
    anchor: anchor_verifier.V075RemoteMainAnchorAttestationV1,
    private_verification_external_id: str,
) -> dict[str, Any]:
    if type(anchor) is not anchor_verifier.V075RemoteMainAnchorAttestationV1:
        _fail("private reveal attestation requires the exact remote anchor")
    _cid(
        private_verification_external_id,
        "private reveal external verification",
    )
    return {
        "schema": "acfqp.v075_private_reveal_attestation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "remote_main_anchor_id": anchor.anchor_id,
        "anchor_commit_id": anchor.commit_id,
        "final_preregistration_id": anchor.final_preregistration_id,
        "family_generation_id": anchor.family_generation_id,
        "opaque_environment_commitment_id": (
            anchor.opaque_environment_commitment_id
        ),
        "observer_profile_id": anchor.observer_profile_id,
        "signer_registry_id": anchor.signer_registry.registry_id,
        "observer_evidence_key_id": (
            anchor.signer_registry.observer_evidence_key.key_id
        ),
        "private_verification_external_id": (
            private_verification_external_id
        ),
        "verification_result": "MATCH",
        "private_reveal_semantically_verified": True,
        "secret_salt_serialized": False,
        "private_environment_serialized": False,
        "transition_law_serialized": False,
        "random_tape_serialized": False,
        "observer_open_performed": False,
        "observer_session_created": False,
    }


def private_reveal_attestation_signing_bytes_v1(
    *,
    anchor: anchor_verifier.V075RemoteMainAnchorAttestationV1,
    private_verification_external_id: str,
) -> bytes:
    """Return public signing bytes; no reveal material is accepted."""

    return (
        PRIVATE_REVEAL_SIGNING_DOMAIN
        + b"\x00"
        + canonical_json_bytes(
            _private_reveal_payload(
                anchor=anchor,
                private_verification_external_id=(
                    private_verification_external_id
                ),
            )
        )
    )


_REVEAL_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PrivateRevealAttestationV1:
    _issuer: object = field(repr=False, compare=False)
    anchor: anchor_verifier.V075RemoteMainAnchorAttestationV1
    private_verification_external_id: str
    observer_signature_hex: str
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        payload = _private_reveal_payload(
            anchor=self.anchor,
            private_verification_external_id=(
                self.private_verification_external_id
            ),
        )
        if (
            self._issuer is not _REVEAL_ISSUER
            or type(self.observer_signature_hex) is not str
            or not self.observer_signature_hex
            or not public_authority.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
                public_key=(
                    self.anchor.signer_registry.observer_evidence_key
                ),
                message=(
                    PRIVATE_REVEAL_SIGNING_DOMAIN
                    + b"\x00"
                    + canonical_json_bytes(payload)
                ),
                signature_hex=self.observer_signature_hex,
            )
        ):
            _fail("private reveal attestation signature is invalid")
        object.__setattr__(
            self,
            "_attestation_id",
            _hash(
                "private_reveal_attestation",
                {
                    **payload,
                    "observer_signature_hex": self.observer_signature_hex,
                    "observer_signature_verified": True,
                },
            ),
        )

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **_private_reveal_payload(
                anchor=self.anchor,
                private_verification_external_id=(
                    self.private_verification_external_id
                ),
            ),
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "attestation_id": self.attestation_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def verify_and_bind_v075_signed_private_reveal_attestation_v1(
    *,
    anchor: anchor_verifier.V075RemoteMainAnchorAttestationV1,
    private_verification_external_id: str,
    observer_signature_hex: str,
) -> V075PrivateRevealAttestationV1:
    """Bind a private verifier's public signature without receiving secrets."""

    return V075PrivateRevealAttestationV1(
        _REVEAL_ISSUER,
        anchor,
        private_verification_external_id,
        observer_signature_hex,
    )


def load_and_verify_v075_private_reveal_attestation_v1(
    *,
    raw: bytes,
    anchor: anchor_verifier.V075RemoteMainAnchorAttestationV1,
) -> V075PrivateRevealAttestationV1:
    item = _strict_document(
        raw,
        expected_keys={
            *_REVEAL_KEYS,
            "observer_signature_hex",
            "observer_signature_verified",
            "attestation_id",
        },
        label="private reveal attestation",
    )
    if (
        item["observer_signature_verified"] is not True
        or type(item["observer_signature_hex"]) is not str
    ):
        _fail("private reveal attestation signature claim is malformed")
    expected = _private_reveal_payload(
        anchor=anchor,
        private_verification_external_id=_cid(
            item["private_verification_external_id"],
            "private reveal external verification",
        ),
    )
    if any(item[key] != value for key, value in expected.items()):
        _fail("private reveal attestation was transplanted or changed")
    attestation = V075PrivateRevealAttestationV1(
        _REVEAL_ISSUER,
        anchor,
        item["private_verification_external_id"],
        item["observer_signature_hex"],
    )
    if (
        item["attestation_id"] != attestation.attestation_id
        or attestation.canonical_bytes != raw
    ):
        _fail("private reveal attestation identity differs from replay")
    return attestation


_BLOB_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075TrackedPreopenBlobClosureV1:
    _issuer: object = field(repr=False, compare=False)
    anchor: anchor_verifier.V075RemoteMainAnchorAttestationV1
    manifest_bytes_sha256: str
    final_preregistration_bytes_sha256: str
    component_ids: tuple[str, ...]
    authority_binding_ids: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _BLOB_CLOSURE_ISSUER
            or type(self.anchor)
            is not anchor_verifier.V075RemoteMainAnchorAttestationV1
            or type(self.component_ids) is not tuple
            or len(self.component_ids)
            != len(anchor_verifier.REQUIRED_COMPONENT_SPECS)
            or len(set(self.component_ids)) != len(self.component_ids)
            or type(self.authority_binding_ids) is not tuple
            or len(self.authority_binding_ids)
            != len(anchor_verifier.REQUIRED_AUTHORITY_ROLE_ORDER)
            or len(set(self.authority_binding_ids))
            != len(self.authority_binding_ids)
        ):
            _fail("tracked pre-open blob closure is not verifier-issued")
        for value, label in (
            (self.manifest_bytes_sha256, "manifest byte digest"),
            (
                self.final_preregistration_bytes_sha256,
                "final preregistration byte digest",
            ),
            *(
                (item, "component content identity")
                for item in self.component_ids
            ),
            *(
                (item, "authority binding identity")
                for item in self.authority_binding_ids
            ),
        ):
            _cid(value, label)
        all_ids = (
            self.component_ids
            + self.authority_binding_ids
            + (
                self.anchor.manifest_id,
                self.anchor.final_preregistration_id,
                self.anchor.component_registry_id,
                self.anchor.authority_registry_id,
            )
        )
        if len(all_ids) != len(set(all_ids)):
            _fail("tracked pre-open closure aliases incompatible roles")
        object.__setattr__(
            self,
            "_closure_id",
            _hash("tracked_blob_closure", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_preopen_tracked_blob_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "remote_main_anchor_id": self.anchor.anchor_id,
            "anchor_commit_id": self.anchor.commit_id,
            "manifest_blob_id": self.anchor.manifest_blob_id,
            "manifest_id": self.anchor.manifest_id,
            "manifest_bytes_sha256": self.manifest_bytes_sha256,
            "final_preregistration_blob_id": (
                self.anchor.final_preregistration_blob_id
            ),
            "final_preregistration_id": (
                self.anchor.final_preregistration_id
            ),
            "final_preregistration_bytes_sha256": (
                self.final_preregistration_bytes_sha256
            ),
            "components": [
                {
                    "role": role,
                    "repository_path": repository_path,
                    "component_id": component_id,
                }
                for (
                    role,
                    repository_path,
                ), component_id in zip(
                    anchor_verifier.REQUIRED_COMPONENT_SPECS,
                    self.component_ids,
                    strict=True,
                )
            ],
            "component_registry_id": self.anchor.component_registry_id,
            "authority_bindings": [
                {
                    "role": role,
                    "binding_id": binding_id,
                }
                for role, binding_id in zip(
                    anchor_verifier.REQUIRED_AUTHORITY_ROLE_ORDER,
                    self.authority_binding_ids,
                    strict=True,
                )
            ],
            "authority_registry_id": self.anchor.authority_registry_id,
            "every_component_blob_verified_at_anchor_commit": True,
            "every_authority_role_semantically_replayed": True,
            "tracked_final_preregistration_verified": True,
            "target_accessed": False,
            "observer_open_performed": False,
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}


def _git_blob(root: Path, object_id: str) -> bytes:
    _git_oid(object_id, "tracked Git blob")
    process = subprocess.run(
        ("git", "-C", str(root), "cat-file", "blob", object_id),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0 or len(process.stdout) > 16 * 1024 * 1024:
        _fail("tracked Git blob is absent or over cap")
    return process.stdout


def _verify_tracked_blob_closure_v1(
    *,
    repository_root: Path,
    anchor: anchor_verifier.V075RemoteMainAnchorAttestationV1,
) -> tuple[
    V075TrackedPreopenBlobClosureV1,
    public_authority.V075OpaqueEnvironmentCommitmentV1,
]:
    # Re-run the zero-claim independent authority before consuming its blob
    # IDs.  A caller-provided or stale anchor therefore cannot enter.
    replayed = anchor_verifier.verify_v075_remote_main_anchor_independently_v1(
        repository_root
    )
    if replayed != anchor:
        _fail("remote-main anchor changed during pre-open verification")
    manifest_raw = _git_blob(repository_root, anchor.manifest_blob_id)
    final_raw = _git_blob(
        repository_root,
        anchor.final_preregistration_blob_id,
    )
    manifest = _strict_document(
        manifest_raw,
        expected_keys=anchor_verifier._MANIFEST_KEYS,
        label="tracked execution manifest",
    )
    final = _strict_document(
        final_raw,
        expected_keys=anchor_verifier._FINAL_KEYS,
        label="tracked final preregistration",
    )
    if (
        manifest["manifest_id"] != anchor.manifest_id
        or final["final_preregistration_id"]
        != anchor.final_preregistration_id
        or final["confirmatory_execution_manifest_id"]
        != anchor.manifest_id
        or final["confirmatory_execution_manifest_bytes_sha256"]
        != hashlib.sha256(manifest_raw).hexdigest()
        or manifest["component_registry_id"]
        != anchor.component_registry_id
        or manifest["authority_registry_id"]
        != anchor.authority_registry_id
        or manifest["signer_registry_id"]
        != anchor.signer_registry.registry_id
    ):
        _fail("tracked manifest/final chain differs from the remote anchor")
    component_ids = tuple(
        _cid(item["component_id"], "tracked component")
        for item in manifest["component_blobs"]
    )
    authority_binding_ids = tuple(
        _cid(item["binding_id"], "tracked authority binding")
        for item in manifest["authority_bindings"]
    )
    if not all(
        anchor_verifier._ROLE_SEMANTIC_VERIFIER_IMPLEMENTED.values()
    ):
        _fail("not every committed authority role has a semantic verifier")
    family = public_authority.freeze_v075_public_family_generation_v1()
    commitment_document = manifest["opaque_environment_commitment"]
    commitment = public_authority.V075OpaqueEnvironmentCommitmentV1(
        family,
        commitment_document["commitment_digest"],
    )
    if (
        commitment.to_document() != commitment_document
        or commitment.commitment_id
        != anchor.opaque_environment_commitment_id
    ):
        _fail("tracked opaque commitment differs from typed reconstruction")
    return (
        V075TrackedPreopenBlobClosureV1(
            _BLOB_CLOSURE_ISSUER,
            anchor,
            hashlib.sha256(manifest_raw).hexdigest(),
            hashlib.sha256(final_raw).hexdigest(),
            component_ids,
            authority_binding_ids,
        ),
        commitment,
    )


_AUTHORIZATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ObserverOpenAuthorizationV1:
    """Complete pre-open authorization; it does not open an observer."""

    _issuer: object = field(repr=False, compare=False)
    anchor: anchor_verifier.V075RemoteMainAnchorAttestationV1
    tracked_blobs: V075TrackedPreopenBlobClosureV1
    signer_registry: public_authority.V075TrustedSignerRegistryV1
    opaque_environment_commitment: (
        public_authority.V075OpaqueEnvironmentCommitmentV1
    )
    private_reveal_attestation: V075PrivateRevealAttestationV1
    _authorization_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        reveal = self.private_reveal_attestation
        if (
            self._issuer is not _AUTHORIZATION_ISSUER
            or type(self.anchor)
            is not anchor_verifier.V075RemoteMainAnchorAttestationV1
            or type(self.tracked_blobs)
            is not V075TrackedPreopenBlobClosureV1
            or type(self.signer_registry)
            is not public_authority.V075TrustedSignerRegistryV1
            or type(self.opaque_environment_commitment)
            is not public_authority.V075OpaqueEnvironmentCommitmentV1
            or type(reveal) is not V075PrivateRevealAttestationV1
            or self.tracked_blobs.anchor != self.anchor
            or self.signer_registry != self.anchor.signer_registry
            or self.opaque_environment_commitment.commitment_id
            != self.anchor.opaque_environment_commitment_id
            or reveal.anchor != self.anchor
        ):
            _fail("observer-open authorization identity graph is inconsistent")
        object.__setattr__(
            self,
            "_authorization_id",
            _hash("observer_open_authorization", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_observer_open_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "remote_main_anchor_id": self.anchor.anchor_id,
            "anchor_commit_id": self.anchor.commit_id,
            "tracked_blob_closure_id": self.tracked_blobs.closure_id,
            "manifest_id": self.anchor.manifest_id,
            "final_preregistration_id": (
                self.anchor.final_preregistration_id
            ),
            "component_registry_id": self.anchor.component_registry_id,
            "authority_registry_id": self.anchor.authority_registry_id,
            "family_generation_id": self.anchor.family_generation_id,
            "signer_registry_id": self.signer_registry.registry_id,
            "campaign_authority_key_id": (
                self.signer_registry.campaign_authority_key.key_id
            ),
            "observer_evidence_key_id": (
                self.signer_registry.observer_evidence_key.key_id
            ),
            "opaque_environment_commitment_id": (
                self.opaque_environment_commitment.commitment_id
            ),
            "observer_profile_id": self.anchor.observer_profile_id,
            "private_reveal_attestation_id": (
                self.private_reveal_attestation.attestation_id
            ),
            "all_committed_blob_semantic_verifiers_passed": True,
            "private_reveal_match_attested": True,
            "authorization_ready": True,
            "observer_open_performed": False,
            "observer_session_created": False,
            "target_law_read": False,
            "target_tape_read": False,
            "sentinel_created": False,
        }

    @property
    def authorization_id(self) -> str:
        return self._authorization_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "tracked_blob_closure": self.tracked_blobs.to_document(),
            "signer_registry": self.signer_registry.to_document(),
            "opaque_environment_commitment": (
                self.opaque_environment_commitment.to_document()
            ),
            "private_reveal_attestation": (
                self.private_reveal_attestation.to_document()
            ),
            "authorization_id": self.authorization_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


_READINESS_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PreopenAuthorizationReadinessV1:
    _issuer: object = field(repr=False, compare=False)
    blockers: tuple[str, ...]
    authorization: V075ObserverOpenAuthorizationV1 | None
    _readiness_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _READINESS_ISSUER
            or type(self.blockers) is not tuple
            or self.blockers != tuple(sorted(set(self.blockers)))
            or any(
                type(item) is not str or not item for item in self.blockers
            )
            or (
                (not self.blockers)
                != (
                    type(self.authorization)
                    is V075ObserverOpenAuthorizationV1
                )
            )
        ):
            _fail("pre-open authorization readiness is malformed")
        object.__setattr__(
            self,
            "_readiness_id",
            _hash("readiness", self._payload()),
        )

    @property
    def ready(self) -> bool:
        return self.authorization is not None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_preopen_authorization_readiness.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "blockers": list(self.blockers),
            "authorization_id": (
                None
                if self.authorization is None
                else self.authorization.authorization_id
            ),
            "ready": self.ready,
            "registered_target_execution_allowed": False,
            "official_execution_allowed": False,
            "observer_open_performed": False,
            "observer_session_created": False,
            "target_law_read": False,
            "target_tape_read": False,
            "sentinel_created": False,
        }

    @property
    def readiness_id(self) -> str:
        return self._readiness_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "readiness_id": self.readiness_id}


def assess_v075_preopen_target_authorization_v1(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
) -> V075PreopenAuthorizationReadinessV1:
    """Replay public authority and bind an attestation; never open target."""

    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise V075PreopenAuthorizationInvariantViolation(
            "repository root cannot be resolved"
        ) from error
    try:
        anchor = (
            anchor_verifier.verify_v075_remote_main_anchor_independently_v1(
                root
            )
        )
    except (
        anchor_verifier.V075ProductionOpenAuthorityNotReady,
        anchor_verifier.V075RemoteMainAnchorInvariantViolation,
    ):
        return V075PreopenAuthorizationReadinessV1(
            _READINESS_ISSUER,
            ("REMOTE_MAIN_COMMITTED_SEMANTIC_CHAIN_NOT_READY",),
            None,
        )
    if not all(
        anchor_verifier._ROLE_SEMANTIC_VERIFIER_IMPLEMENTED.values()
    ):
        return V075PreopenAuthorizationReadinessV1(
            _READINESS_ISSUER,
            ("COMMITTED_BLOB_SEMANTIC_VERIFIER_REGISTRY_INCOMPLETE",),
            None,
        )
    try:
        tracked_blobs, commitment = _verify_tracked_blob_closure_v1(
            repository_root=root,
            anchor=anchor,
        )
        reveal = load_and_verify_v075_private_reveal_attestation_v1(
            raw=private_reveal_attestation_bytes,
            anchor=anchor,
        )
        authorization = V075ObserverOpenAuthorizationV1(
            _AUTHORIZATION_ISSUER,
            anchor,
            tracked_blobs,
            anchor.signer_registry,
            commitment,
            reveal,
        )
    except V075PreopenAuthorizationInvariantViolation:
        return V075PreopenAuthorizationReadinessV1(
            _READINESS_ISSUER,
            ("PRIVATE_REVEAL_OR_TRACKED_BLOB_BINDING_INVALID",),
            None,
        )
    return V075PreopenAuthorizationReadinessV1(
        _READINESS_ISSUER,
        (),
        authorization,
    )


def require_ready_v075_preopen_target_authorization_v1(
    readiness: V075PreopenAuthorizationReadinessV1,
) -> V075ObserverOpenAuthorizationV1:
    if (
        type(readiness) is not V075PreopenAuthorizationReadinessV1
        or not readiness.ready
        or readiness.authorization is None
    ):
        raise V075PreopenAuthorizationNotReady(
            "V0-075 pre-open target authorization is not ready"
        )
    return readiness.authorization


def verify_v075_observer_open_authorization_v1(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
) -> V075ObserverOpenAuthorizationV1:
    readiness = assess_v075_preopen_target_authorization_v1(
        repository_root=repository_root,
        private_reveal_attestation_bytes=(
            private_reveal_attestation_bytes
        ),
    )
    authorization = require_ready_v075_preopen_target_authorization_v1(
        readiness
    )
    if (
        type(claimed_authorization_bytes) is not bytes
        or authorization.canonical_bytes != claimed_authorization_bytes
    ):
        _fail("claimed observer-open authorization differs from full replay")
    return authorization


__all__ = [
    "DOMAIN_TAGS",
    "PRIVATE_REVEAL_SIGNING_DOMAIN",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075ObserverOpenAuthorizationV1",
    "V075PreopenAuthorizationInvariantViolation",
    "V075PreopenAuthorizationNotReady",
    "V075PreopenAuthorizationReadinessV1",
    "V075PrivateRevealAttestationV1",
    "V075TrackedPreopenBlobClosureV1",
    "assess_v075_preopen_target_authorization_v1",
    "load_and_verify_v075_private_reveal_attestation_v1",
    "private_reveal_attestation_signing_bytes_v1",
    "require_ready_v075_preopen_target_authorization_v1",
    "verify_and_bind_v075_signed_private_reveal_attestation_v1",
    "verify_v075_observer_open_authorization_v1",
]
