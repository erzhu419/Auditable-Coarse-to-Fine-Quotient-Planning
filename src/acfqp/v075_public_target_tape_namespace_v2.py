"""Public, law-free target namespace derived from the exact V0-075 V2 anchor.

The namespace is a public identity junction only.  It independently replays
the supplied remote-main anchor, freezes the registered workload, family, and
campaign-runner profile, and binds one typed opaque commitment.  It never
opens an observer and accepts no V1 external-claim projection, private reveal,
salt, law, random tape, callback, or caller-selected workload/profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_confirmatory_manifest_preregistration_v2 as manifest
from acfqp import v075_production_campaign_profile_v2 as campaign_profile
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_remote_main_anchor_verifier_v2 as remote


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.43.0"
PROFILE_KEY = "v075_public_target_tape_namespace_v2"
MAX_NAMESPACE_BYTES = 16 * 1024 * 1024
REQUIRED_ANCHOR_RUNNER_PROFILE_FIELD = "runner_profile_id"

TARGET_EXECUTION_OPENED = False
TARGET_LAW_ACCESSED = False
TARGET_TAPE_ACCESSED = False
PRIVATE_BYTES_ACCEPTED = False
V1_EXTERNAL_CLAIM_PROJECTION_ALLOWED = False

DOMAIN_TAGS = {
    "namespace": "acfqp:v075-public-target-tape-namespace:v2",
    "verification": (
        "acfqp:v075-public-target-tape-namespace-verification:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 public namespace V2 domains overlap")


class V075PublicTargetTapeNamespaceV2InvariantViolation(ValueError):
    """An anchor, workload, profile, commitment, or replay was invalid."""


class V075PublicTargetTapeNamespaceV2NotReady(RuntimeError):
    """The independently anchored public identity graph is incomplete."""


def _fail(message: str) -> None:
    raise V075PublicTargetTapeNamespaceV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PublicTargetTapeNamespaceV2InvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PublicTargetTapeNamespaceV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _anchor_runner_profile_id(
    anchor: remote.V075RemoteMainAnchorAttestationV2,
) -> str:
    value = getattr(anchor, REQUIRED_ANCHOR_RUNNER_PROFILE_FIELD, None)
    if value is None:
        raise V075PublicTargetTapeNamespaceV2NotReady(
            "V075RemoteMainAnchorAttestationV2 must explicitly carry "
            "runner_profile_id replayed from the signed workload"
        )
    return _cid(value, "V2 anchor runner profile")


def _workload_runner_profile_id(
    workload: manifest.V075ConfirmatoryPublicWorkloadV2,
) -> str:
    profile = getattr(workload, "runner_profile", None)
    if (
        type(profile)
        is not campaign_profile.V075ProductionCampaignProfileV2
    ):
        raise V075PublicTargetTapeNamespaceV2NotReady(
            "V075ConfirmatoryPublicWorkloadV2 must explicitly carry "
            "one exact typed runner_profile"
        )
    return _cid(profile.profile_id, "V2 workload runner profile")


_NAMESPACE_ISSUER = object()
_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PublicTargetTapeNamespaceV2:
    """Verifier-derived public namespace with no V1 claim compatibility."""

    _issuer: object = field(repr=False, compare=False)
    anchor: remote.V075RemoteMainAnchorAttestationV2
    workload: manifest.V075ConfirmatoryPublicWorkloadV2
    family: public.V075PublicFamilyGenerationV1
    runner_profile: campaign_profile.V075ProductionCampaignProfileV2
    environment_commitment: public.V075OpaqueEnvironmentCommitmentV1
    signer_registry: public.V075TrustedSignerRegistryV1
    _namespace_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _NAMESPACE_ISSUER
            or type(self.anchor)
            is not remote.V075RemoteMainAnchorAttestationV2
            or type(self.workload)
            is not manifest.V075ConfirmatoryPublicWorkloadV2
            or type(self.family) is not public.V075PublicFamilyGenerationV1
            or type(self.runner_profile)
            is not campaign_profile.V075ProductionCampaignProfileV2
            or type(self.environment_commitment)
            is not public.V075OpaqueEnvironmentCommitmentV1
            or type(self.signer_registry)
            is not public.V075TrustedSignerRegistryV1
        ):
            _fail("public namespace V2 is untyped or caller-minted")
        anchor_runner = _anchor_runner_profile_id(self.anchor)
        workload_runner = _workload_runner_profile_id(self.workload)
        exact_family = public.freeze_v075_public_family_generation_v1()
        exact_runner = (
            campaign_profile.freeze_v075_production_campaign_profile_v2()
        )
        exact_workload = manifest.freeze_v075_confirmatory_public_workload_v2()
        if (
            self.family != exact_family
            or self.runner_profile != exact_runner
            or self.workload != exact_workload
            or self.anchor.workload_id != self.workload.workload_id
            or self.anchor.family_generation_id != self.family.generation_id
            or anchor_runner != self.runner_profile.profile_id
            or workload_runner != self.runner_profile.profile_id
            or self.environment_commitment.family != self.family
            or self.anchor.opaque_environment_commitment_id
            != self.environment_commitment.commitment_id
            or self.signer_registry != self.anchor.signer_registry
        ):
            _fail(
                "public namespace V2 identity graph is stale or transplanted"
            )
        role_ids = (
            self.anchor.anchor_id,
            self.anchor.manifest_id,
            self.anchor.final_preregistration_id,
            self.anchor.component_registry_id,
            self.anchor.semantic_registry_binding_id,
            self.anchor.semantic_artifact_replay_id,
            self.workload.workload_id,
            self.family.generation_id,
            self.runner_profile.profile_id,
            self.environment_commitment.commitment_id,
            self.signer_registry.registry_id,
        )
        for value in role_ids:
            _cid(value, "public namespace V2 role")
        if len(role_ids) != len(set(role_ids)):
            _fail("public namespace V2 aliases incompatible identity roles")
        object.__setattr__(
            self,
            "_namespace_id",
            _hash("namespace", self._payload()),
        )

    @property
    def target_tape_namespace_id(self) -> str:
        return self._namespace_id

    @property
    def remote_main_anchor_id(self) -> str:
        return self.anchor.anchor_id

    @property
    def final_preregistration_id(self) -> str:
        return self.anchor.final_preregistration_id

    @property
    def workload_id(self) -> str:
        return self.workload.workload_id

    @property
    def runner_profile_id(self) -> str:
        return self.runner_profile.profile_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_target_tape_namespace.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "remote_main_anchor_id": self.anchor.anchor_id,
            "anchor_commit_id": self.anchor.commit_id,
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
            "workload_id": self.workload.workload_id,
            "family_generation_id": self.family.generation_id,
            "runner_profile_id": self.runner_profile.profile_id,
            "opaque_environment_commitment_id": (
                self.environment_commitment.commitment_id
            ),
            "signer_registry_id": self.signer_registry.registry_id,
            "campaign_authority_key_id": (
                self.signer_registry.campaign_authority_key.key_id
            ),
            "observer_evidence_key_id": (
                self.signer_registry.observer_evidence_key.key_id
            ),
            "anchor_independently_replayed": True,
            "workload_frozen_locally": True,
            "family_frozen_locally": True,
            "runner_profile_frozen_locally": True,
            "v1_external_claim_projection_present": False,
            "v1_external_claim_projection_accepted": False,
            "caller_workload_accepted": False,
            "caller_family_accepted": False,
            "caller_runner_profile_accepted": False,
            "caller_signer_registry_accepted": False,
            "observer_open_authority": False,
            "observer_opened": False,
            "target_execution_allowed": False,
            "target_accessed": False,
            "target_law_serialized": False,
            "target_tape_serialized": False,
            "private_bytes_accepted": False,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "anchor": self.anchor.to_document(),
            "workload": self.workload.to_document(),
            "family": self.family.to_document(),
            "runner_profile": self.runner_profile.to_document(),
            "opaque_environment_commitment": (
                self.environment_commitment.to_document()
            ),
            "signer_registry": self.signer_registry.to_document(),
            "target_tape_namespace_id": self.target_tape_namespace_id,
        }


def freeze_v075_public_target_tape_namespace_v2(
    *,
    repository_root: str | Path,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
    environment_commitment: public.V075OpaqueEnvironmentCommitmentV1,
) -> V075PublicTargetTapeNamespaceV2:
    """Recompute all public identities and freeze one V2 namespace."""

    if (
        type(anchor) is not remote.V075RemoteMainAnchorAttestationV2
        or type(environment_commitment)
        is not public.V075OpaqueEnvironmentCommitmentV1
    ):
        _fail("namespace V2 requires exact anchor and commitment types")
    try:
        replayed_anchor = (
            remote.verify_v075_remote_main_anchor_independently_v2(
                repository_root
            )
        )
    except remote.V075RemoteMainAnchorV2NotReady as error:
        raise V075PublicTargetTapeNamespaceV2NotReady(
            "remote-main V2 authority is not ready"
        ) from error
    except remote.V075RemoteMainAnchorV2InvariantViolation as error:
        raise V075PublicTargetTapeNamespaceV2InvariantViolation(
            "remote-main V2 replay failed"
        ) from error
    if replayed_anchor != anchor:
        _fail("caller anchor differs from independent remote-main replay")
    workload = manifest.freeze_v075_confirmatory_public_workload_v2()
    family = public.freeze_v075_public_family_generation_v1()
    runner_profile = (
        campaign_profile.freeze_v075_production_campaign_profile_v2()
    )
    return V075PublicTargetTapeNamespaceV2(
        _NAMESPACE_ISSUER,
        replayed_anchor,
        workload,
        family,
        runner_profile,
        environment_commitment,
        replayed_anchor.signer_registry,
    )


@dataclass(frozen=True, slots=True)
class V075PublicTargetTapeNamespaceVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    namespace_id: str
    replayed_namespace_id: str
    namespace_bytes_sha256: str
    anchor_id: str
    workload_id: str
    runner_profile_id: str
    commitment_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.namespace_id, "verified namespace"),
            (self.replayed_namespace_id, "replayed namespace"),
            (self.namespace_bytes_sha256, "namespace byte digest"),
            (self.anchor_id, "namespace anchor"),
            (self.workload_id, "namespace workload"),
            (self.runner_profile_id, "namespace runner profile"),
            (self.commitment_id, "namespace commitment"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or self.namespace_id != self.replayed_namespace_id
        ):
            _fail("namespace V2 verification is caller-minted or partial")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_public_target_tape_namespace_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "target_tape_namespace_id": self.namespace_id,
            "replayed_target_tape_namespace_id": (
                self.replayed_namespace_id
            ),
            "namespace_bytes_sha256": self.namespace_bytes_sha256,
            "remote_main_anchor_id": self.anchor_id,
            "workload_id": self.workload_id,
            "runner_profile_id": self.runner_profile_id,
            "opaque_environment_commitment_id": self.commitment_id,
            "anchor_replayed": True,
            "workload_recomputed": True,
            "runner_profile_recomputed": True,
            "v1_external_claim_projection_accepted": False,
            "target_accessed": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_public_target_tape_namespace_bytes_v2(
    *,
    repository_root: str | Path,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
    environment_commitment: public.V075OpaqueEnvironmentCommitmentV1,
    raw: bytes,
) -> tuple[
    V075PublicTargetTapeNamespaceV2,
    V075PublicTargetTapeNamespaceVerificationV2,
]:
    """Strictly byte-replay one public namespace without target access."""

    if type(raw) is not bytes or not raw or len(raw) > MAX_NAMESPACE_BYTES:
        _fail("namespace V2 bytes are empty, mistyped, or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075PublicTargetTapeNamespaceV2InvariantViolation(
            "namespace V2 is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("namespace V2 is not one canonical object")
    expected = freeze_v075_public_target_tape_namespace_v2(
        repository_root=repository_root,
        anchor=anchor,
        environment_commitment=environment_commitment,
    )
    if expected.canonical_bytes != raw:
        _fail("namespace V2 bytes are stale, altered, or transplanted")
    return (
        expected,
        V075PublicTargetTapeNamespaceVerificationV2(
            _VERIFICATION_ISSUER,
            expected.target_tape_namespace_id,
            expected.target_tape_namespace_id,
            hashlib.sha256(raw).hexdigest(),
            expected.anchor.anchor_id,
            expected.workload.workload_id,
            expected.runner_profile.profile_id,
            expected.environment_commitment.commitment_id,
        ),
    )


__all__ = [
    "DOMAIN_TAGS",
    "MAX_NAMESPACE_BYTES",
    "PRIVATE_BYTES_ACCEPTED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUIRED_ANCHOR_RUNNER_PROFILE_FIELD",
    "SCHEMA_VERSION",
    "TARGET_EXECUTION_OPENED",
    "TARGET_LAW_ACCESSED",
    "TARGET_TAPE_ACCESSED",
    "V1_EXTERNAL_CLAIM_PROJECTION_ALLOWED",
    "V075PublicTargetTapeNamespaceV2",
    "V075PublicTargetTapeNamespaceV2InvariantViolation",
    "V075PublicTargetTapeNamespaceV2NotReady",
    "V075PublicTargetTapeNamespaceVerificationV2",
    "freeze_v075_public_target_tape_namespace_v2",
    "verify_v075_public_target_tape_namespace_bytes_v2",
]
