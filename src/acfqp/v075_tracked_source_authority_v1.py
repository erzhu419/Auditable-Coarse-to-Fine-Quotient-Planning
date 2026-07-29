"""Exact tracked-source authority for the final V0-075 preregistration.

The eight source artifacts are immutable public inputs.  This authority reads
their fixed repository paths, replays every available source-only semantic
verifier, and emits one content-addressed bundle verification.  It performs
no target observation and admits no caller-supplied identity or status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import stat
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_frozen_source_proposal_archive_v1 as archive_v1
from acfqp import v075_public_source_work_authority_v1 as public_work
from acfqp import v075_source_offline_work_materializer_v1 as work_v1
from acfqp import v075_source_prior_adapter_v1 as prior_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_tracked_source_authority_v1"

TRACKED_ARTIFACT_PATHS = (
    (
        "SOURCE_ARCHIVE",
        "specs/V075_FROZEN_SOURCE_PROPOSAL_ARCHIVE.json",
    ),
    (
        "SOURCE_ARCHIVE_VERIFICATION",
        "specs/V075_FROZEN_SOURCE_PROPOSAL_ARCHIVE_VERIFICATION.json",
    ),
    (
        "SOURCE_WORK",
        "specs/V075_SOURCE_OFFLINE_WORK_MATERIALIZATION.json",
    ),
    (
        "SOURCE_WORK_VERIFICATION",
        "specs/V075_SOURCE_OFFLINE_WORK_MATERIALIZATION_VERIFICATION.json",
    ),
    (
        "SOURCE_REPLAY_STATUS",
        "specs/V075_SOURCE_REPLAY_MATERIALIZATION_STATUS.json",
    ),
    (
        "PUBLIC_SOURCE_WORK_BUNDLE",
        "specs/V075_VERIFIED_PUBLIC_SOURCE_WORK_BUNDLE.json",
    ),
    (
        "SOURCE_PRIOR_ADAPTER",
        "specs/V075_SOURCE_PRIOR_ADAPTER.json",
    ),
    (
        "SOURCE_PRIOR_ADAPTER_VERIFICATION",
        "specs/V075_SOURCE_PRIOR_ADAPTER_VERIFICATION.json",
    ),
)

DOMAIN_TAGS = {
    "artifact": "acfqp:v075-tracked-source-artifact:v1",
    "bundle": "acfqp:v075-tracked-source-authority-bundle:v1",
    "verification": (
        "acfqp:v075-tracked-source-authority-bundle-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 tracked-source domains must be unique")


class V075TrackedSourceAuthorityInvariantViolation(ValueError):
    """A tracked source byte, identity, role, or semantic replay failed."""


def _fail(message: str) -> None:
    raise V075TrackedSourceAuthorityInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075TrackedSourceAuthorityInvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075TrackedSourceAuthorityInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _read_regular(root: Path, relative: str, cap: int) -> bytes:
    candidate = root.joinpath(*relative.split("/"))
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        if cursor.is_symlink():
            _fail("tracked source path contains a symlink")
    info = candidate.stat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_size <= 0
        or info.st_size > cap
    ):
        _fail("tracked source artifact is absent, empty, or over cap")
    raw = candidate.read_bytes()
    if len(raw) != info.st_size:
        _fail("tracked source artifact changed during read")
    return raw


@dataclass(frozen=True, slots=True)
class V075TrackedSourceArtifactV1:
    role: str
    repository_path: str
    canonical_bytes_sha256: str
    byte_count: int
    semantic_id: str

    def __post_init__(self) -> None:
        expected = dict(TRACKED_ARTIFACT_PATHS).get(self.role)
        if (
            expected != self.repository_path
            or self.canonical_bytes_sha256
            != _cid(
                self.canonical_bytes_sha256,
                "tracked source byte digest",
            )
            or type(self.byte_count) is not int
            or self.byte_count <= 0
        ):
            _fail("tracked source artifact metadata is malformed")
        _cid(self.semantic_id, "tracked source semantic identity")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_tracked_source_artifact.v1",
            "schema_version": SCHEMA_VERSION,
            "role": self.role,
            "repository_path": self.repository_path,
            "canonical_bytes_sha256": self.canonical_bytes_sha256,
            "byte_count": self.byte_count,
            "semantic_id": self.semantic_id,
            "target_accessed": False,
        }

    @property
    def artifact_id(self) -> str:
        return _hash("artifact", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "artifact_id": self.artifact_id}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075TrackedSourceAuthorityBundleV1:
    _issuer: object = field(repr=False, compare=False)
    artifacts: tuple[V075TrackedSourceArtifactV1, ...]
    source_archive_id: str
    source_archive_verification_id: str
    source_work_materialization_id: str
    source_work_verification_id: str
    source_replay_status_id: str
    public_source_work_bundle_id: str
    source_prior_adapter_id: str
    source_prior_verification_id: str
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        identities = (
            self.source_archive_id,
            self.source_archive_verification_id,
            self.source_work_materialization_id,
            self.source_work_verification_id,
            self.source_replay_status_id,
            self.public_source_work_bundle_id,
            self.source_prior_adapter_id,
            self.source_prior_verification_id,
        )
        for value in identities:
            _cid(value, "tracked source authority identity")
        if (
            self._issuer is not _ISSUER
            or type(self.artifacts) is not tuple
            or tuple(
                (item.role, item.repository_path)
                for item in self.artifacts
            )
            != TRACKED_ARTIFACT_PATHS
            or len({item.artifact_id for item in self.artifacts})
            != len(self.artifacts)
            or len(set(identities)) != len(identities)
            or tuple(item.semantic_id for item in self.artifacts)
            != identities
        ):
            _fail("tracked source authority bundle is incomplete or reordered")
        object.__setattr__(
            self,
            "_bundle_id",
            _hash("bundle", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_tracked_source_authority_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "artifact_ids": [item.artifact_id for item in self.artifacts],
            "source_archive_id": self.source_archive_id,
            "source_archive_verification_id": (
                self.source_archive_verification_id
            ),
            "source_work_materialization_id": (
                self.source_work_materialization_id
            ),
            "source_work_verification_id": self.source_work_verification_id,
            "source_replay_status_id": self.source_replay_status_id,
            "public_source_work_bundle_id": (
                self.public_source_work_bundle_id
            ),
            "source_prior_adapter_id": self.source_prior_adapter_id,
            "source_prior_verification_id": (
                self.source_prior_verification_id
            ),
            "source_only": True,
            "proposal_only": True,
            "source_work_charged_once": True,
            "target_accessed": False,
        }

    @property
    def bundle_id(self) -> str:
        return self._bundle_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "artifacts": [item.to_document() for item in self.artifacts],
            "bundle_id": self.bundle_id,
        }


@dataclass(frozen=True, slots=True)
class V075TrackedSourceAuthorityVerificationV1:
    _issuer: object = field(repr=False, compare=False)
    bundle_id: str
    source_prior_adapter_id: str
    source_prior_verification_id: str
    artifact_ids: tuple[str, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.bundle_id,
            self.source_prior_adapter_id,
            self.source_prior_verification_id,
            *self.artifact_ids,
        ):
            _cid(value, "verified tracked source identity")
        if (
            self._issuer is not _ISSUER
            or type(self.artifact_ids) is not tuple
            or len(self.artifact_ids) != len(TRACKED_ARTIFACT_PATHS)
            or len(set(self.artifact_ids)) != len(self.artifact_ids)
        ):
            _fail("tracked source verification was caller-minted or partial")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_tracked_source_authority_bundle_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "bundle_id": self.bundle_id,
            "source_prior_adapter_id": self.source_prior_adapter_id,
            "source_prior_verification_id": (
                self.source_prior_verification_id
            ),
            "artifact_ids": list(self.artifact_ids),
            "tracked_recipe_recompiled": True,
            "source_work_public_authority_replayed": True,
            "source_prior_adapter_recomputed": True,
            "source_prior_verification_recomputed": True,
            "caller_identity_accepted": False,
            "target_accessed": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _load_work_verification(
    raw: bytes,
) -> work_v1.V075SourceOfflineWorkMaterializationVerificationV1:
    value = loads_canonical_json(raw)
    if type(value) is not dict:
        _fail("source-work verification is not one canonical object")
    try:
        result = work_v1.V075SourceOfflineWorkMaterializationVerificationV1(
            value["source_recipe_id"],
            value["source_campaign_id"],
            value["campaign_counters_id"],
            value["materialization_id"],
            value["recomputed_materialization_id"],
            value["materialization_bytes_sha256"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise V075TrackedSourceAuthorityInvariantViolation(
            "source-work verification cannot be reconstructed"
        ) from error
    if canonical_json_bytes(result.to_document()) != raw:
        _fail("source-work verification differs from typed reconstruction")
    return result


def _load_prior_verification(
    raw: bytes,
) -> prior_v1.V075SourcePriorAdapterVerificationV1:
    value = loads_canonical_json(raw)
    if type(value) is not dict:
        _fail("source-prior verification is not one canonical object")
    try:
        result = prior_v1.V075SourcePriorAdapterVerificationV1(
            value["adapter_id"],
            value["recomputed_adapter_id"],
            value["catalogue_id"],
            value["source_archive_id"],
            value["source_archive_verification_id"],
            value["source_work_materialization_id"],
            value["source_work_verification_id"],
            value["adapter_bytes_sha256"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise V075TrackedSourceAuthorityInvariantViolation(
            "source-prior verification cannot be reconstructed"
        ) from error
    if canonical_json_bytes(result.to_document()) != raw:
        _fail("source-prior verification differs from typed reconstruction")
    return result


def verify_tracked_v075_source_authorities_v1(
    repository_root: str | Path,
) -> tuple[
    V075TrackedSourceAuthorityBundleV1,
    V075TrackedSourceAuthorityVerificationV1,
]:
    """Replay all eight exact tracked artifacts without target access."""

    root = Path(repository_root).resolve(strict=True)
    raw = {
        role: _read_regular(root, path, 4 * 1024 * 1024)
        for role, path in TRACKED_ARTIFACT_PATHS
    }
    public_bundle = public_work.verify_v075_public_source_work_artifacts_v1(
        materialization_raw=raw["SOURCE_WORK"],
        verification_raw=raw["SOURCE_WORK_VERIFICATION"],
        controller_status_raw=raw["SOURCE_REPLAY_STATUS"],
    )
    if public_bundle.canonical_bytes != raw["PUBLIC_SOURCE_WORK_BUNDLE"]:
        _fail("tracked public source-work bundle differs from replay")
    archive_verification = (
        archive_v1
        .verify_v075_frozen_source_proposal_archive_bytes_independently_v1(
            repository_root=root,
            raw=raw["SOURCE_ARCHIVE"],
        )
    )
    if (
        canonical_json_bytes(archive_verification.to_document())
        != raw["SOURCE_ARCHIVE_VERIFICATION"]
    ):
        _fail("tracked source archive verification differs from recompilation")
    archive = archive_v1.load_v075_frozen_source_proposal_archive_v1(
        raw["SOURCE_ARCHIVE"],
        expected_archive_id=archive_verification.archive_id,
        expected_source_recipe_id=archive_verification.source_recipe_id,
        expected_offline_work_reference_id=(
            archive_verification.offline_work_reference_id
        ),
    )
    work = work_v1.load_v075_source_offline_work_materialization_v1(
        raw["SOURCE_WORK"],
        expected_materialization_id=public_bundle.materialization_id,
        expected_source_recipe_id=public_bundle.source_recipe_id,
        expected_source_campaign_id=public_bundle.source_campaign_id,
        expected_campaign_counters_id=public_bundle.campaign_counters_id,
    )
    work_verification = _load_work_verification(
        raw["SOURCE_WORK_VERIFICATION"]
    )
    prior = prior_v1.load_v075_source_prior_adapter_v1(
        raw["SOURCE_PRIOR_ADAPTER"],
        source_archive=archive,
        archive_verification=archive_verification,
        source_work=work,
        work_verification=work_verification,
    )
    recomputed_prior_verification = (
        prior_v1.verify_v075_source_prior_adapter_independently_v1(
            source_archive=archive,
            archive_verification=archive_verification,
            source_work=work,
            work_verification=work_verification,
            claimed=prior,
        )
    )
    tracked_prior_verification = _load_prior_verification(
        raw["SOURCE_PRIOR_ADAPTER_VERIFICATION"]
    )
    if tracked_prior_verification != recomputed_prior_verification:
        _fail("tracked source-prior verification differs from exact replay")
    semantic_ids = (
        archive.archive_id,
        archive_verification.verification_id,
        work.materialization_id,
        work_verification.verification_id,
        public_bundle.controller_status_id,
        public_bundle.bundle_id,
        prior.adapter_id,
        recomputed_prior_verification.verification_id,
    )
    artifacts = tuple(
        V075TrackedSourceArtifactV1(
            role,
            path,
            hashlib.sha256(raw[role]).hexdigest(),
            len(raw[role]),
            semantic_id,
        )
        for (role, path), semantic_id in zip(
            TRACKED_ARTIFACT_PATHS,
            semantic_ids,
            strict=True,
        )
    )
    bundle = V075TrackedSourceAuthorityBundleV1(
        _ISSUER,
        artifacts,
        *semantic_ids,
    )
    verification = V075TrackedSourceAuthorityVerificationV1(
        _ISSUER,
        bundle.bundle_id,
        prior.adapter_id,
        recomputed_prior_verification.verification_id,
        tuple(item.artifact_id for item in artifacts),
    )
    return bundle, verification


__all__ = [
    "DOMAIN_TAGS",
    "PROFILE_KEY",
    "TRACKED_ARTIFACT_PATHS",
    "V075TrackedSourceArtifactV1",
    "V075TrackedSourceAuthorityBundleV1",
    "V075TrackedSourceAuthorityInvariantViolation",
    "V075TrackedSourceAuthorityVerificationV1",
    "verify_tracked_v075_source_authorities_v1",
]
