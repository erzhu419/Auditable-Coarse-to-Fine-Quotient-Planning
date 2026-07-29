"""Exact V2 pre-open authorization for the V0-075 held-out target.

This authority consumes only the exact
``V075RemoteMainAnchorAttestationV2`` and a signed, law-free reveal
attestation.  It does not accept V1 anchors, projections, adapters, mappings,
or caller-supplied status claims.  The production assessor independently
replays ``origin/main`` before binding any authorization.

Minting ``V075ObserverOpenAuthorizationV2`` completes pre-open identity
checking only.  This module has no observer-open operation and never receives
target laws, target tapes, kernels, observer sessions, or private keys.
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
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_remote_main_anchor_verifier_v2 as remote


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.44.0"
PROFILE_KEY = "v075_preopen_target_authorization_v2"

PRIVATE_REVEAL_SIGNING_DOMAIN = (
    b"acfqp:v075-private-reveal-attestation-signing:v2"
)

DOMAIN_TAGS = {
    "private_reveal_attestation": (
        "acfqp:v075-private-reveal-attestation:v2"
    ),
    "tracked_blob_closure": (
        "acfqp:v075-preopen-tracked-blob-closure:v2"
    ),
    "observer_open_authorization": (
        "acfqp:v075-observer-open-authorization:v2"
    ),
    "readiness": "acfqp:v075-preopen-authorization-readiness:v2",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 V2 pre-open content domains must be unique")

# The authorization is a capability for a later boundary.  This module never
# exercises that capability.
TARGET_EXECUTION_OPENED = False


class V075PreopenAuthorizationV2InvariantViolation(ValueError):
    """A V2 public identity, signature, blob, or binding failed closed."""


class V075PreopenAuthorizationV2NotReady(RuntimeError):
    """The exact V2 pre-open chain is not yet authorizing."""


def _fail(message: str) -> None:
    raise V075PreopenAuthorizationV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PreopenAuthorizationV2InvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PreopenAuthorizationV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _git_oid(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) not in (40, 64)
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field_name} must be one full lowercase Git object ID")
    return value


def _strict_document(
    raw: bytes,
    *,
    expected_keys: set[str],
    label: str,
) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > 32 * 1024 * 1024:
        _fail(f"{label} bytes are empty, mistyped, or over cap")
    try:
        value = loads_canonical_json(raw)
    except (Phase3EIdentityError, ValueError) as error:
        raise V075PreopenAuthorizationV2InvariantViolation(
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
    "anchor_tree_id",
    "manifest_id",
    "final_preregistration_id",
    "component_registry_id",
    "semantic_registry_binding_id",
    "semantic_artifact_replay_id",
    "workload_id",
    "family_generation_id",
    "opaque_environment_commitment_id",
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
    "target_accessed",
}


def _private_reveal_payload(
    *,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
    private_verification_external_id: str,
) -> dict[str, Any]:
    if type(anchor) is not remote.V075RemoteMainAnchorAttestationV2:
        _fail("V2 reveal attestation requires the exact V2 remote anchor")
    _cid(
        private_verification_external_id,
        "private reveal external verification",
    )
    return {
        "schema": "acfqp.v075_private_reveal_attestation.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "remote_main_anchor_id": anchor.anchor_id,
        "anchor_commit_id": anchor.commit_id,
        "anchor_tree_id": anchor.tree_id,
        "manifest_id": anchor.manifest_id,
        "final_preregistration_id": anchor.final_preregistration_id,
        "component_registry_id": anchor.component_registry_id,
        "semantic_registry_binding_id": (
            anchor.semantic_registry_binding_id
        ),
        "semantic_artifact_replay_id": (
            anchor.semantic_artifact_replay_id
        ),
        "workload_id": anchor.workload_id,
        "family_generation_id": anchor.family_generation_id,
        "opaque_environment_commitment_id": (
            anchor.opaque_environment_commitment_id
        ),
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
        "target_accessed": False,
    }


def private_reveal_attestation_signing_bytes_v2(
    *,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
    private_verification_external_id: str,
) -> bytes:
    """Return V2 role-separated signing bytes without receiving secrets."""

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
class V075PrivateRevealAttestationV2:
    _issuer: object = field(repr=False, compare=False)
    anchor: remote.V075RemoteMainAnchorAttestationV2
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
            or not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
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
            _fail("V2 private reveal attestation signature is invalid")
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


def verify_and_bind_v075_signed_private_reveal_attestation_v2(
    *,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
    private_verification_external_id: str,
    observer_signature_hex: str,
) -> V075PrivateRevealAttestationV2:
    """Bind exactly one observer signature to an exact V2 anchor."""

    return V075PrivateRevealAttestationV2(
        _REVEAL_ISSUER,
        anchor,
        private_verification_external_id,
        observer_signature_hex,
    )


def load_and_verify_v075_private_reveal_attestation_v2(
    *,
    raw: bytes,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
) -> V075PrivateRevealAttestationV2:
    item = _strict_document(
        raw,
        expected_keys={
            *_REVEAL_KEYS,
            "observer_signature_hex",
            "observer_signature_verified",
            "attestation_id",
        },
        label="V2 private reveal attestation",
    )
    if (
        type(anchor) is not remote.V075RemoteMainAnchorAttestationV2
        or item["observer_signature_verified"] is not True
        or type(item["observer_signature_hex"]) is not str
    ):
        _fail("V2 private reveal role or signature claim is malformed")
    expected = _private_reveal_payload(
        anchor=anchor,
        private_verification_external_id=_cid(
            item["private_verification_external_id"],
            "private reveal external verification",
        ),
    )
    if any(item[key] != value for key, value in expected.items()):
        _fail("V2 private reveal attestation was transplanted or changed")
    attestation = V075PrivateRevealAttestationV2(
        _REVEAL_ISSUER,
        anchor,
        item["private_verification_external_id"],
        item["observer_signature_hex"],
    )
    if (
        item["attestation_id"] != attestation.attestation_id
        or attestation.canonical_bytes != raw
    ):
        _fail("V2 private reveal identity differs from replay")
    return attestation


_BLOB_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075TrackedPreopenBlobClosureV2:
    _issuer: object = field(repr=False, compare=False)
    anchor: remote.V075RemoteMainAnchorAttestationV2
    manifest_bytes_sha256: str
    final_preregistration_bytes_sha256: str
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _BLOB_CLOSURE_ISSUER
            or type(self.anchor)
            is not remote.V075RemoteMainAnchorAttestationV2
        ):
            _fail("V2 tracked pre-open blob closure is verifier-issued only")
        _cid(self.manifest_bytes_sha256, "manifest byte digest")
        _cid(
            self.final_preregistration_bytes_sha256,
            "final preregistration byte digest",
        )
        object.__setattr__(
            self,
            "_closure_id",
            _hash("tracked_blob_closure", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_preopen_tracked_blob_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "remote_main_anchor_id": self.anchor.anchor_id,
            "anchor_commit_id": self.anchor.commit_id,
            "anchor_tree_id": self.anchor.tree_id,
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
            "component_registry_id": self.anchor.component_registry_id,
            "semantic_registry_binding_id": (
                self.anchor.semantic_registry_binding_id
            ),
            "semantic_artifact_replay_id": (
                self.anchor.semantic_artifact_replay_id
            ),
            "workload_id": self.anchor.workload_id,
            "every_component_blob_verified_at_anchor_commit": True,
            "code_only_static_surfaces_verified": True,
            "every_serialized_artifact_semantically_replayed": True,
            "tracked_final_preregistration_verified": True,
            "legacy_v1_projection_issued": False,
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
        timeout=30,
    )
    if (
        process.returncode != 0
        or not process.stdout
        or len(process.stdout) > 32 * 1024 * 1024
    ):
        _fail("tracked V2 Git blob is absent, empty, or over cap")
    return process.stdout


def _commitment_from_manifest(
    raw: bytes,
    *,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
) -> public.V075OpaqueEnvironmentCommitmentV1:
    try:
        item = loads_canonical_json(raw)
        opaque = item["opaque_environment_commitment"]
        digest = opaque["commitment_digest"]
        commitment = public.V075OpaqueEnvironmentCommitmentV1(
            public.freeze_v075_public_family_generation_v1(),
            digest,
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        Phase3EIdentityError,
    ) as error:
        raise V075PreopenAuthorizationV2InvariantViolation(
            "tracked V2 opaque commitment cannot be reconstructed"
        ) from error
    if (
        type(item) is not dict
        or commitment.to_document() != opaque
        or commitment.family.generation_id != anchor.family_generation_id
        or commitment.commitment_id
        != anchor.opaque_environment_commitment_id
    ):
        _fail("tracked V2 opaque commitment differs from the anchor")
    return commitment


def _verify_tracked_blob_closure_v2(
    *,
    repository_root: Path,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
) -> tuple[
    V075TrackedPreopenBlobClosureV2,
    public.V075OpaqueEnvironmentCommitmentV1,
]:
    if type(anchor) is not remote.V075RemoteMainAnchorAttestationV2:
        _fail("tracked closure requires the exact V2 remote anchor")
    try:
        replayed = remote.verify_v075_remote_main_anchor_independently_v2(
            repository_root
        )
    except (
        remote.V075RemoteMainAnchorV2InvariantViolation,
        remote.V075RemoteMainAnchorV2NotReady,
    ) as error:
        raise V075PreopenAuthorizationV2InvariantViolation(
            "V2 remote-main replay failed during pre-open closure"
        ) from error
    if type(replayed) is not remote.V075RemoteMainAnchorAttestationV2:
        _fail("V2 remote-main replay returned a foreign authority role")
    if replayed != anchor:
        _fail("origin/main V2 anchor is stale or changed during pre-open")
    anchor_document = anchor.to_document()
    if (
        anchor_document["preopen_v2_migration_status"] != "READY"
        or anchor_document["target_accessed"] is not False
        or anchor_document["target_execution_allowed"] is not False
    ):
        _fail("signed V2 anchor has not declared the migration ready")
    manifest_raw = _git_blob(repository_root, anchor.manifest_blob_id)
    final_raw = _git_blob(
        repository_root,
        anchor.final_preregistration_blob_id,
    )
    commitment = _commitment_from_manifest(
        manifest_raw,
        anchor=anchor,
    )
    return (
        V075TrackedPreopenBlobClosureV2(
            _BLOB_CLOSURE_ISSUER,
            anchor,
            hashlib.sha256(manifest_raw).hexdigest(),
            hashlib.sha256(final_raw).hexdigest(),
        ),
        commitment,
    )


_AUTHORIZATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ObserverOpenAuthorizationV2:
    """Complete exact-V2 pre-open authorization; no observer is opened."""

    _issuer: object = field(repr=False, compare=False)
    anchor: remote.V075RemoteMainAnchorAttestationV2
    tracked_blobs: V075TrackedPreopenBlobClosureV2
    signer_registry: public.V075TrustedSignerRegistryV1
    opaque_environment_commitment: (
        public.V075OpaqueEnvironmentCommitmentV1
    )
    private_reveal_attestation: V075PrivateRevealAttestationV2
    _authorization_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        reveal = self.private_reveal_attestation
        if (
            self._issuer is not _AUTHORIZATION_ISSUER
            or type(self.anchor)
            is not remote.V075RemoteMainAnchorAttestationV2
            or type(self.tracked_blobs)
            is not V075TrackedPreopenBlobClosureV2
            or type(self.signer_registry)
            is not public.V075TrustedSignerRegistryV1
            or type(self.opaque_environment_commitment)
            is not public.V075OpaqueEnvironmentCommitmentV1
            or type(reveal) is not V075PrivateRevealAttestationV2
            or self.tracked_blobs.anchor != self.anchor
            or self.signer_registry != self.anchor.signer_registry
            or self.opaque_environment_commitment.family.generation_id
            != self.anchor.family_generation_id
            or self.opaque_environment_commitment.commitment_id
            != self.anchor.opaque_environment_commitment_id
            or reveal.anchor != self.anchor
        ):
            _fail("V2 observer-open authorization graph is inconsistent")
        object.__setattr__(
            self,
            "_authorization_id",
            _hash("observer_open_authorization", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_observer_open_authorization.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "remote_main_anchor_id": self.anchor.anchor_id,
            "anchor_commit_id": self.anchor.commit_id,
            "anchor_tree_id": self.anchor.tree_id,
            "tracked_blob_closure_id": self.tracked_blobs.closure_id,
            "manifest_id": self.anchor.manifest_id,
            "final_preregistration_id": (
                self.anchor.final_preregistration_id
            ),
            "component_registry_id": self.anchor.component_registry_id,
            "semantic_registry_binding_id": (
                self.anchor.semantic_registry_binding_id
            ),
            "semantic_artifact_replay_id": (
                self.anchor.semantic_artifact_replay_id
            ),
            "workload_id": self.anchor.workload_id,
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
            "private_reveal_attestation_id": (
                self.private_reveal_attestation.attestation_id
            ),
            "all_committed_blob_semantic_verifiers_passed": True,
            "private_reveal_match_attested": True,
            "legacy_v1_projection_issued": False,
            "authorization_ready": True,
            "observer_open_performed": False,
            "observer_session_created": False,
            "target_law_read": False,
            "target_tape_read": False,
            "target_accessed": False,
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
class V075PreopenAuthorizationReadinessV2:
    _issuer: object = field(repr=False, compare=False)
    blockers: tuple[str, ...]
    authorization: V075ObserverOpenAuthorizationV2 | None
    _readiness_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _READINESS_ISSUER
            or type(self.blockers) is not tuple
            or self.blockers != tuple(sorted(set(self.blockers)))
            or any(type(item) is not str or not item for item in self.blockers)
            or (
                (not self.blockers)
                != (
                    type(self.authorization)
                    is V075ObserverOpenAuthorizationV2
                )
            )
        ):
            _fail("V2 pre-open authorization readiness is malformed")
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
            "schema": "acfqp.v075_preopen_authorization_readiness.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "blockers": list(self.blockers),
            "authorization_id": (
                None
                if self.authorization is None
                else self.authorization.authorization_id
            ),
            "ready": self.ready,
            "legacy_v1_projection_issued": False,
            "registered_target_execution_allowed": False,
            "official_execution_allowed": False,
            "observer_open_performed": False,
            "observer_session_created": False,
            "target_law_read": False,
            "target_tape_read": False,
            "target_accessed": False,
            "sentinel_created": False,
        }

    @property
    def readiness_id(self) -> str:
        return self._readiness_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "readiness_id": self.readiness_id}


def _blocked(code: str) -> V075PreopenAuthorizationReadinessV2:
    return V075PreopenAuthorizationReadinessV2(
        _READINESS_ISSUER,
        (code,),
        None,
    )


def assess_v075_preopen_target_authorization_v2(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
) -> V075PreopenAuthorizationReadinessV2:
    """Replay exact V2 public authority; never read or open the target."""

    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError):
        return _blocked("REPOSITORY_ROOT_NOT_READY")
    try:
        anchor = remote.verify_v075_remote_main_anchor_independently_v2(
            root
        )
    except (
        remote.V075RemoteMainAnchorV2InvariantViolation,
        remote.V075RemoteMainAnchorV2NotReady,
    ):
        return _blocked("REMOTE_MAIN_V2_SEMANTIC_CHAIN_NOT_READY")
    if type(anchor) is not remote.V075RemoteMainAnchorAttestationV2:
        return _blocked("REMOTE_MAIN_V2_AUTHORITY_ROLE_INVALID")
    if anchor.to_document()["preopen_v2_migration_status"] != "READY":
        return _blocked("PREOPEN_V2_SIGNED_DECLARATION_NOT_READY")
    try:
        tracked_blobs, commitment = _verify_tracked_blob_closure_v2(
            repository_root=root,
            anchor=anchor,
        )
        reveal = load_and_verify_v075_private_reveal_attestation_v2(
            raw=private_reveal_attestation_bytes,
            anchor=anchor,
        )
        authorization = V075ObserverOpenAuthorizationV2(
            _AUTHORIZATION_ISSUER,
            anchor,
            tracked_blobs,
            anchor.signer_registry,
            commitment,
            reveal,
        )
    except V075PreopenAuthorizationV2InvariantViolation:
        return _blocked("V2_REVEAL_OR_TRACKED_BLOB_BINDING_INVALID")
    return V075PreopenAuthorizationReadinessV2(
        _READINESS_ISSUER,
        (),
        authorization,
    )


def require_ready_v075_preopen_target_authorization_v2(
    readiness: V075PreopenAuthorizationReadinessV2,
) -> V075ObserverOpenAuthorizationV2:
    if (
        type(readiness) is not V075PreopenAuthorizationReadinessV2
        or not readiness.ready
        or type(readiness.authorization)
        is not V075ObserverOpenAuthorizationV2
    ):
        raise V075PreopenAuthorizationV2NotReady(
            "exact V0-075 V2 pre-open authorization is not ready"
        )
    return readiness.authorization


def verify_v075_observer_open_authorization_v2(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
) -> V075ObserverOpenAuthorizationV2:
    readiness = assess_v075_preopen_target_authorization_v2(
        repository_root=repository_root,
        private_reveal_attestation_bytes=(
            private_reveal_attestation_bytes
        ),
    )
    authorization = require_ready_v075_preopen_target_authorization_v2(
        readiness
    )
    if (
        type(claimed_authorization_bytes) is not bytes
        or authorization.canonical_bytes != claimed_authorization_bytes
    ):
        _fail("claimed V2 observer-open authorization differs from replay")
    return authorization


__all__ = [
    "DOMAIN_TAGS",
    "PRIVATE_REVEAL_SIGNING_DOMAIN",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "TARGET_EXECUTION_OPENED",
    "V075ObserverOpenAuthorizationV2",
    "V075PreopenAuthorizationReadinessV2",
    "V075PreopenAuthorizationV2InvariantViolation",
    "V075PreopenAuthorizationV2NotReady",
    "V075PrivateRevealAttestationV2",
    "V075TrackedPreopenBlobClosureV2",
    "assess_v075_preopen_target_authorization_v2",
    "load_and_verify_v075_private_reveal_attestation_v2",
    "private_reveal_attestation_signing_bytes_v2",
    "require_ready_v075_preopen_target_authorization_v2",
    "verify_and_bind_v075_signed_private_reveal_attestation_v2",
    "verify_v075_observer_open_authorization_v2",
]
