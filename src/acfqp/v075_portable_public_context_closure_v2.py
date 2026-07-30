"""Portable, byte-complete public-context closure for V0-075 V2.

The construction multiround result carries only derived occurrence evidence.
In particular, its observer-open binding contains identities but not the
canonical namespace, authorization, or reveal-attestation bytes.  This module
therefore has an explicit byte-only constructor for those three public
dependencies.

Every construction or replay independently derives the current remote-main
anchor, strictly replays the three existing byte authorities, and binds the
public replay source-manifest content ID plus the registered repository
identity.  A caller can self-hash a manifest, so that binding is explicitly
opaque until a verified IPC source-snapshot attestation is supplied by a later
authority; this module never upgrades it.  No private key, salt, environment,
law, random tape, observer session, or held-out execution channel is accepted.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_remote_main_anchor_verifier_v2 as remote


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.64.0"
PROFILE_KEY = "v075_portable_public_context_closure_v2"

MAX_DEPENDENCY_BYTES = 32 * 1024 * 1024
MAX_SOURCE_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_CLOSURE_BYTES = 128 * 1024 * 1024

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
PRIVATE_INPUT_CHANNELS_ALLOWED = False
OBSERVER_OPEN_ALLOWED = False
MULTIROUND_RESULT_CONTAINS_CANONICAL_PUBLIC_CONTEXT_BYTES = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_PUBLIC_CONTEXT_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "PUBLIC_CONTEXT_RECORDS_REPLAYED_SOURCE_AUTHORITY_INCOMPLETE"
)

SOURCE_MANIFEST_SCHEMA = "acfqp.v075_public_replay_source_manifest.v2"
SOURCE_MANIFEST_PROFILE_KEY = "v075_public_replay_occurrence_ipc_v2"
SOURCE_MANIFEST_ROOT_MODULE = (
    "acfqp.v075_portable_occurrence_evidence_bundle_v2"
)
SOURCE_MANIFEST_CLOSURE_RULE = "RECURSIVE_STATIC_LOCAL_ACFQP_IMPORTS"
SOURCE_MANIFEST_DOMAIN_TAG = (
    "acfqp:v075-public-replay-source-manifest:v2"
)
SOURCE_MANIFEST_AUTHORITY_STATUS = (
    "OPAQUE_CONTENT_ID_BOUND_UNVERIFIED_BY_THIS_MODULE"
)
SOURCE_AUTHORITY_COMPLETE = False
IPC_SOURCE_SNAPSHOT_ATTESTATION_STATUS = "NOT_SUPPLIED"
_IPC_SOURCE_SNAPSHOT_ATTESTATION_NOT_SUPPLIED = {
    "kind": "NOT_SUPPLIED",
    "reason": (
        "VERIFIED_IPC_SOURCE_SNAPSHOT_ATTESTATION_NOT_PROVIDED_TO_THIS_"
        "CONSTRUCTION_CLOSURE"
    ),
}

DOMAIN_TAGS = {
    "repository_binding": (
        "acfqp:v075-portable-public-context-repository-binding:v2"
    ),
    "dependency_record": (
        "acfqp:v075-portable-public-context-dependency-record:v2"
    ),
    "dependency_attestation": (
        "acfqp:v075-portable-public-context-dependency-attestation:v2"
    ),
    "closure": "acfqp:v075-portable-public-context-closure:v2",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 public-context closure domains overlap")


class V075PortablePublicContextV2InvariantViolation(ValueError):
    """A public dependency, source identity, or closure failed replay."""


class V075PortablePublicContextProductionV2NotReady(RuntimeError):
    """This construction closure cannot authorize production."""


def _fail(message: str) -> NoReturn:
    raise V075PortablePublicContextV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortablePublicContextV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _git_oid(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) not in (40, 64)
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one full lowercase Git object ID")
    return value


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PortablePublicContextV2InvariantViolation(
            str(error)
        ) from error


def _hash_source_manifest(payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            SOURCE_MANIFEST_DOMAIN_TAG.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise V075PortablePublicContextV2InvariantViolation(
            str(error)
        ) from error


def _source_snapshot_attestation_not_supplied() -> dict[str, str]:
    return dict(_IPC_SOURCE_SNAPSHOT_ATTESTATION_NOT_SUPPLIED)


def _strict_document(
    raw: bytes,
    *,
    label: str,
    byte_cap: int,
) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > byte_cap:
        _fail(f"{label} bytes are empty, mistyped, or exceed their cap")

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(f"{label} contains a duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=no_duplicates,
            parse_constant=lambda item: _fail(
                f"{label} contains forbidden numeric constant {item}"
            ),
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
        if type(error) is V075PortablePublicContextV2InvariantViolation:
            raise
        raise V075PortablePublicContextV2InvariantViolation(
            f"{label} is not strict UTF-8 canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


_FORBIDDEN_PRIVATE_KEYS = frozenset(
    {
        "individual_random_words",
        "kernel",
        "private_environment",
        "private_key",
        "private_law",
        "private_salt",
        "random_tape",
        "secret_laws",
        "secret_salt",
        "target_law",
        "target_tape",
    }
)

_PRIVATE_SERIALIZATION_FLAGS = frozenset(
    {
        "individual_random_words_retained",
        "individual_random_words_serialized",
        "private_bytes_accepted",
        "private_environment_serialized",
        "private_key_serialized",
        "private_keys_serialized",
        "private_law_serialized",
        "private_material_serialized",
        "private_salt_serialized",
        "random_tape_serialized",
        "secret_salt_serialized",
        "target_law_serialized",
        "target_tape_serialized",
        "transition_law_serialized",
    }
)


def _assert_public_document(value: Any) -> None:
    if type(value) is list:
        for item in value:
            _assert_public_document(item)
        return
    if type(value) is not dict:
        return
    for key, item in value.items():
        if key in _FORBIDDEN_PRIVATE_KEYS:
            _fail("public-context evidence contains private material")
        if key in _PRIVATE_SERIALIZATION_FLAGS and item is not False:
            _fail("public-context evidence claims private serialization")
        _assert_public_document(item)


@dataclass(frozen=True, slots=True)
class V075PortablePublicContextSourceManifestEntryV2:
    module_name: str
    relative_path: str
    source_sha256: str
    source_byte_count: int

    def __post_init__(self) -> None:
        _cid(self.source_sha256, "source-manifest source digest")
        if self.relative_path.endswith("/__init__.py"):
            derived = self.relative_path[
                : -len("/__init__.py")
            ].replace("/", ".")
        elif self.relative_path.endswith(".py"):
            derived = self.relative_path[:-3].replace("/", ".")
        else:
            derived = ""
        if (
            type(self.module_name) is not str
            or (
                self.module_name != "acfqp"
                and not self.module_name.startswith("acfqp.")
            )
            or type(self.relative_path) is not str
            or self.relative_path.startswith("/")
            or ".." in self.relative_path.split("/")
            or derived != self.module_name
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
        ):
            _fail("source-manifest entry is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "module_name": self.module_name,
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
        }


@dataclass(frozen=True, slots=True)
class V075PortablePublicContextSourceManifestV2:
    entries: tuple[
        V075PortablePublicContextSourceManifestEntryV2,
        ...,
    ]
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        names = tuple(item.module_name for item in self.entries)
        if (
            type(self.entries) is not tuple
            or not self.entries
            or any(
                type(item)
                is not V075PortablePublicContextSourceManifestEntryV2
                for item in self.entries
            )
            or names != tuple(sorted(names))
            or len(set(names)) != len(names)
            or SOURCE_MANIFEST_ROOT_MODULE not in names
            or "acfqp.phase3e_ids" not in names
        ):
            _fail("source manifest is incomplete, unsorted, or duplicated")
        object.__setattr__(
            self,
            "_manifest_id",
            _hash_source_manifest(self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SOURCE_MANIFEST_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "profile_key": SOURCE_MANIFEST_PROFILE_KEY,
            "root_module": SOURCE_MANIFEST_ROOT_MODULE,
            "closure_rule": SOURCE_MANIFEST_CLOSURE_RULE,
            "entries": [item.to_document() for item in self.entries],
            "entry_count": len(self.entries),
        }

    @property
    def manifest_id(self) -> str:
        return self._manifest_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}


_SOURCE_MANIFEST_KEYS = {
    "schema",
    "schema_version",
    "profile_key",
    "root_module",
    "closure_rule",
    "entries",
    "entry_count",
    "manifest_id",
}
_SOURCE_ENTRY_KEYS = {
    "module_name",
    "relative_path",
    "source_sha256",
    "source_byte_count",
}


def replay_v075_portable_public_context_source_manifest_bytes_v2(
    raw: bytes,
) -> V075PortablePublicContextSourceManifestV2:
    document = _strict_document(
        raw,
        label="public replay source manifest",
        byte_cap=MAX_SOURCE_MANIFEST_BYTES,
    )
    if (
        set(document) != _SOURCE_MANIFEST_KEYS
        or document["schema"] != SOURCE_MANIFEST_SCHEMA
        or document["schema_version"] != SCHEMA_VERSION
        or document["profile_key"] != SOURCE_MANIFEST_PROFILE_KEY
        or document["root_module"] != SOURCE_MANIFEST_ROOT_MODULE
        or document["closure_rule"] != SOURCE_MANIFEST_CLOSURE_RULE
        or type(document["entries"]) is not list
        or type(document["entry_count"]) is not int
        or document["entry_count"] != len(document["entries"])
    ):
        _fail("public replay source manifest shape or authority changed")
    entries: list[V075PortablePublicContextSourceManifestEntryV2] = []
    for item in document["entries"]:
        if type(item) is not dict or set(item) != _SOURCE_ENTRY_KEYS:
            _fail("public replay source-manifest entry shape changed")
        entries.append(
            V075PortablePublicContextSourceManifestEntryV2(
                item["module_name"],
                item["relative_path"],
                item["source_sha256"],
                item["source_byte_count"],
            )
        )
    result = V075PortablePublicContextSourceManifestV2(tuple(entries))
    if (
        document["manifest_id"] != result.manifest_id
        or result.canonical_bytes != raw
    ):
        _fail("public replay source manifest differs from content replay")
    return result


_REPOSITORY_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePublicContextRepositoryBindingV2:
    _issuer: InitVar[object]
    remote_main_anchor_id: str
    repository_url: str
    target_branch: str
    remote_tracking_ref: str
    anchor_commit_id: str
    anchor_tree_id: str
    source_manifest_id: str
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.remote_main_anchor_id, "repository-binding anchor")
        _cid(self.source_manifest_id, "repository-binding source manifest")
        _git_oid(self.anchor_commit_id, "repository-binding commit")
        _git_oid(self.anchor_tree_id, "repository-binding tree")
        if (
            _issuer is not _REPOSITORY_BINDING_ISSUER
            or self.repository_url != remote.REPOSITORY_URL
            or self.target_branch != remote.TARGET_BRANCH
            or self.remote_tracking_ref != remote.REMOTE_TRACKING_REF
        ):
            _fail("source repository binding is foreign or caller-minted")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("repository_binding", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_public_context_repository_binding.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "repository_url": self.repository_url,
            "target_branch": self.target_branch,
            "remote_tracking_ref": self.remote_tracking_ref,
            "anchor_commit_id": self.anchor_commit_id,
            "anchor_tree_id": self.anchor_tree_id,
            "source_manifest_id": self.source_manifest_id,
            "remote_main_independently_replayed": True,
            "source_manifest_content_id_replayed": True,
            "source_manifest_authority_status": (
                SOURCE_MANIFEST_AUTHORITY_STATUS
            ),
            "ipc_source_snapshot_attestation": (
                _source_snapshot_attestation_not_supplied()
            ),
            "ipc_source_snapshot_attestation_status": (
                IPC_SOURCE_SNAPSHOT_ATTESTATION_STATUS
            ),
            "source_authority_complete": False,
            "source_archive_bytes_loaded": False,
            "live_source_fallback_allowed": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


class V075PortablePublicContextDependencyRoleV2(str, Enum):
    PUBLIC_TARGET_TAPE_NAMESPACE = "PUBLIC_TARGET_TAPE_NAMESPACE"
    OBSERVER_OPEN_AUTHORIZATION = "OBSERVER_OPEN_AUTHORIZATION"
    PRIVATE_REVEAL_VERIFICATION_ATTESTATION = (
        "PRIVATE_REVEAL_VERIFICATION_ATTESTATION"
    )


_ROLE_ORDER = (
    V075PortablePublicContextDependencyRoleV2
    .PUBLIC_TARGET_TAPE_NAMESPACE,
    V075PortablePublicContextDependencyRoleV2
    .OBSERVER_OPEN_AUTHORIZATION,
    V075PortablePublicContextDependencyRoleV2
    .PRIVATE_REVEAL_VERIFICATION_ATTESTATION,
)

_ROLE_SCHEMA = {
    V075PortablePublicContextDependencyRoleV2
    .PUBLIC_TARGET_TAPE_NAMESPACE: (
        "acfqp.v075_public_target_tape_namespace.v2"
    ),
    V075PortablePublicContextDependencyRoleV2
    .OBSERVER_OPEN_AUTHORIZATION: (
        "acfqp.v075_observer_open_authorization.v2"
    ),
    V075PortablePublicContextDependencyRoleV2
    .PRIVATE_REVEAL_VERIFICATION_ATTESTATION: (
        "acfqp.v075_private_reveal_attestation.v2"
    ),
}

_ROLE_VERIFIER = {
    V075PortablePublicContextDependencyRoleV2
    .PUBLIC_TARGET_TAPE_NAMESPACE: (
        "verify_v075_public_target_tape_namespace_bytes_v2"
    ),
    V075PortablePublicContextDependencyRoleV2
    .OBSERVER_OPEN_AUTHORIZATION: (
        "verify_v075_observer_open_authorization_v2"
    ),
    V075PortablePublicContextDependencyRoleV2
    .PRIVATE_REVEAL_VERIFICATION_ATTESTATION: (
        "load_and_verify_v075_private_reveal_attestation_v2"
    ),
}

_DEPENDENCY_RECORD_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePublicContextDependencyRecordV2:
    _issuer: InitVar[object]
    role: V075PortablePublicContextDependencyRoleV2
    artifact_schema: str
    semantic_artifact_id: str
    artifact_bytes: bytes = field(repr=False)
    canonical_artifact_sha256: str
    canonical_artifact_byte_count: int
    remote_main_anchor_id: str
    repository_binding_id: str
    source_manifest_id: str
    opaque_environment_commitment_id: str
    namespace_public_key_id: str
    _record_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.semantic_artifact_id, "public-context semantic artifact"),
            (
                self.canonical_artifact_sha256,
                "public-context artifact bytes",
            ),
            (self.remote_main_anchor_id, "public-context anchor"),
            (self.repository_binding_id, "public-context repository binding"),
            (self.source_manifest_id, "public-context source manifest"),
            (
                self.opaque_environment_commitment_id,
                "public-context environment commitment",
            ),
            (self.namespace_public_key_id, "namespace public key"),
        ):
            _cid(value, label)
        if (
            _issuer is not _DEPENDENCY_RECORD_ISSUER
            or type(self.role)
            is not V075PortablePublicContextDependencyRoleV2
            or self.artifact_schema != _ROLE_SCHEMA[self.role]
            or type(self.artifact_bytes) is not bytes
            or type(self.canonical_artifact_byte_count) is not int
            or self.canonical_artifact_byte_count <= 0
        ):
            _fail("public-context dependency record is malformed")
        document = _strict_document(
            self.artifact_bytes,
            label=f"{self.role.value} dependency record",
            byte_cap=MAX_DEPENDENCY_BYTES,
        )
        if document.get("schema") != self.artifact_schema:
            _fail("public-context dependency record schema changed")
        _assert_public_document(document)
        if (
            len(self.artifact_bytes) != self.canonical_artifact_byte_count
            or hashlib.sha256(self.artifact_bytes).hexdigest()
            != self.canonical_artifact_sha256
        ):
            _fail("public-context dependency record bytes changed")
        object.__setattr__(
            self,
            "_record_id",
            _hash("dependency_record", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_public_context_dependency_record.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "role": self.role.value,
            "artifact_schema": self.artifact_schema,
            "semantic_artifact_id": self.semantic_artifact_id,
            "artifact_document": self.artifact_document,
            "canonical_artifact_sha256": self.canonical_artifact_sha256,
            "canonical_artifact_byte_count": (
                self.canonical_artifact_byte_count
            ),
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "repository_binding_id": self.repository_binding_id,
            "source_manifest_id": self.source_manifest_id,
            "opaque_environment_commitment_id": (
                self.opaque_environment_commitment_id
            ),
            "namespace_public_key_id": self.namespace_public_key_id,
            "canonical_artifact_bytes_reconstructible": True,
            "source_manifest_authority_status": (
                SOURCE_MANIFEST_AUTHORITY_STATUS
            ),
            "ipc_source_snapshot_attestation": (
                _source_snapshot_attestation_not_supplied()
            ),
            "ipc_source_snapshot_attestation_status": (
                IPC_SOURCE_SNAPSHOT_ATTESTATION_STATUS
            ),
            "source_authority_complete": False,
            "private_material_serialized": False,
        }

    @property
    def record_id(self) -> str:
        return self._record_id

    @property
    def canonical_artifact_bytes(self) -> bytes:
        return self.artifact_bytes

    @property
    def artifact_document(self) -> dict[str, Any]:
        return _strict_document(
            self.artifact_bytes,
            label=f"{self.role.value} dependency record",
            byte_cap=MAX_DEPENDENCY_BYTES,
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "record_id": self.record_id}


_DEPENDENCY_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePublicContextDependencyAttestationV2:
    _issuer: InitVar[object]
    role: V075PortablePublicContextDependencyRoleV2
    record_id: str
    semantic_artifact_id: str
    verifier_authority: str
    canonical_artifact_sha256: str
    remote_main_anchor_id: str
    repository_binding_id: str
    source_manifest_id: str
    opaque_environment_commitment_id: str
    namespace_public_key_id: str
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.record_id, "public-context dependency record"),
            (self.semantic_artifact_id, "public-context semantic artifact"),
            (
                self.canonical_artifact_sha256,
                "public-context artifact digest",
            ),
            (self.remote_main_anchor_id, "public-context anchor"),
            (self.repository_binding_id, "public-context repository binding"),
            (self.source_manifest_id, "public-context source manifest"),
            (
                self.opaque_environment_commitment_id,
                "public-context environment commitment",
            ),
            (self.namespace_public_key_id, "namespace public key"),
        ):
            _cid(value, label)
        if (
            _issuer is not _DEPENDENCY_ATTESTATION_ISSUER
            or type(self.role)
            is not V075PortablePublicContextDependencyRoleV2
            or self.verifier_authority != _ROLE_VERIFIER[self.role]
        ):
            _fail("public-context attestation is foreign or caller-minted")
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("dependency_attestation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_public_context_dependency_"
                "attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "role": self.role.value,
            "record_id": self.record_id,
            "semantic_artifact_id": self.semantic_artifact_id,
            "verifier_authority": self.verifier_authority,
            "canonical_artifact_sha256": (
                self.canonical_artifact_sha256
            ),
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "repository_binding_id": self.repository_binding_id,
            "source_manifest_id": self.source_manifest_id,
            "opaque_environment_commitment_id": (
                self.opaque_environment_commitment_id
            ),
            "namespace_public_key_id": self.namespace_public_key_id,
            "remote_main_independently_replayed": True,
            "role_specific_bytes_verifier_passed": True,
            "canonical_artifact_bytes_replayed": True,
            "dependency_semantic_replay_complete": True,
            "source_manifest_content_id_replayed": True,
            "source_manifest_authority_status": (
                SOURCE_MANIFEST_AUTHORITY_STATUS
            ),
            "ipc_source_snapshot_attestation": (
                _source_snapshot_attestation_not_supplied()
            ),
            "ipc_source_snapshot_attestation_status": (
                IPC_SOURCE_SNAPSHOT_ATTESTATION_STATUS
            ),
            "source_authority_complete": False,
            "source_archive_verified_by_this_attestation": False,
            "observer_opened": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


@dataclass(frozen=True, slots=True)
class V075PortablePublicContextRawResolutionV2:
    """In-memory result of the strict three-record public replay."""

    anchor: remote.V075RemoteMainAnchorAttestationV2
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2
    authorization: preopen.V075ObserverOpenAuthorizationV2
    reveal_attestation: preopen.V075PrivateRevealAttestationV2
    source_manifest: V075PortablePublicContextSourceManifestV2
    repository_binding: V075PortablePublicContextRepositoryBindingV2
    records: tuple[V075PortablePublicContextDependencyRecordV2, ...]
    attestations: tuple[
        V075PortablePublicContextDependencyAttestationV2,
        ...,
    ]

    def __post_init__(self) -> None:
        if (
            type(self.anchor)
            is not remote.V075RemoteMainAnchorAttestationV2
            or type(self.namespace)
            is not namespace_v2.V075PublicTargetTapeNamespaceV2
            or type(self.authorization)
            is not preopen.V075ObserverOpenAuthorizationV2
            or type(self.reveal_attestation)
            is not preopen.V075PrivateRevealAttestationV2
            or type(self.source_manifest)
            is not V075PortablePublicContextSourceManifestV2
            or type(self.repository_binding)
            is not V075PortablePublicContextRepositoryBindingV2
            or tuple(item.role for item in self.records) != _ROLE_ORDER
            or tuple(item.role for item in self.attestations) != _ROLE_ORDER
            or tuple(item.record_id for item in self.records)
            != tuple(item.record_id for item in self.attestations)
        ):
            _fail("public-context raw resolution is incomplete")


def _record(
    *,
    role: V075PortablePublicContextDependencyRoleV2,
    semantic_artifact_id: str,
    raw: bytes,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
    repository_binding: V075PortablePublicContextRepositoryBindingV2,
    commitment_id: str,
    public_key_id: str,
) -> V075PortablePublicContextDependencyRecordV2:
    document = _strict_document(
        raw,
        label=f"{role.value} dependency",
        byte_cap=MAX_DEPENDENCY_BYTES,
    )
    _assert_public_document(document)
    if document.get("schema") != _ROLE_SCHEMA[role]:
        _fail(f"{role.value} dependency schema changed")
    return V075PortablePublicContextDependencyRecordV2(
        _DEPENDENCY_RECORD_ISSUER,
        role,
        _ROLE_SCHEMA[role],
        semantic_artifact_id,
        raw,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
        anchor.anchor_id,
        repository_binding.binding_id,
        repository_binding.source_manifest_id,
        commitment_id,
        public_key_id,
    )


def _attest(
    record: V075PortablePublicContextDependencyRecordV2,
) -> V075PortablePublicContextDependencyAttestationV2:
    return V075PortablePublicContextDependencyAttestationV2(
        _DEPENDENCY_ATTESTATION_ISSUER,
        record.role,
        record.record_id,
        record.semantic_artifact_id,
        _ROLE_VERIFIER[record.role],
        record.canonical_artifact_sha256,
        record.remote_main_anchor_id,
        record.repository_binding_id,
        record.source_manifest_id,
        record.opaque_environment_commitment_id,
        record.namespace_public_key_id,
    )


def resolve_v075_portable_public_context_raw_dependencies_v2(
    *,
    repository_root: str | Path,
    source_manifest_bytes: bytes,
    namespace_bytes: bytes,
    observer_open_authorization_bytes: bytes,
    private_reveal_verification_attestation_bytes: bytes,
) -> V075PortablePublicContextRawResolutionV2:
    """Strictly replay the only three permitted public-context byte roles."""

    try:
        anchor = remote.verify_v075_remote_main_anchor_independently_v2(
            repository_root
        )
        source_manifest = (
            replay_v075_portable_public_context_source_manifest_bytes_v2(
                source_manifest_bytes
            )
        )
        reveal = preopen.load_and_verify_v075_private_reveal_attestation_v2(
            raw=private_reveal_verification_attestation_bytes,
            anchor=anchor,
        )
        authorization = (
            preopen.verify_v075_observer_open_authorization_v2(
                repository_root=repository_root,
                private_reveal_attestation_bytes=(
                    private_reveal_verification_attestation_bytes
                ),
                claimed_authorization_bytes=(
                    observer_open_authorization_bytes
                ),
            )
        )
        namespace, _namespace_verification = (
            namespace_v2.verify_v075_public_target_tape_namespace_bytes_v2(
                repository_root=repository_root,
                anchor=anchor,
                environment_commitment=(
                    authorization.opaque_environment_commitment
                ),
                raw=namespace_bytes,
            )
        )
    except V075PortablePublicContextV2InvariantViolation:
        raise
    except Exception as error:
        raise V075PortablePublicContextV2InvariantViolation(
            "public-context dependency authority replay failed"
        ) from error

    commitment = authorization.opaque_environment_commitment
    public_key = namespace.signer_registry.observer_evidence_key
    if (
        authorization.anchor != anchor
        or namespace.anchor != anchor
        or reveal.anchor != anchor
        or authorization.private_reveal_attestation != reveal
        or authorization.private_reveal_attestation.canonical_bytes
        != private_reveal_verification_attestation_bytes
        or authorization.canonical_bytes
        != observer_open_authorization_bytes
        or namespace.canonical_bytes != namespace_bytes
        or authorization.signer_registry != namespace.signer_registry
        or authorization.signer_registry != anchor.signer_registry
        or commitment != namespace.environment_commitment
        or commitment.commitment_id
        != anchor.opaque_environment_commitment_id
        or public_key != anchor.signer_registry.observer_evidence_key
    ):
        _fail("public-context dependency graph was transplanted")

    repository_binding = V075PortablePublicContextRepositoryBindingV2(
        _REPOSITORY_BINDING_ISSUER,
        anchor.anchor_id,
        remote.REPOSITORY_URL,
        remote.TARGET_BRANCH,
        remote.REMOTE_TRACKING_REF,
        anchor.commit_id,
        anchor.tree_id,
        source_manifest.manifest_id,
    )
    records = (
        _record(
            role=_ROLE_ORDER[0],
            semantic_artifact_id=namespace.target_tape_namespace_id,
            raw=namespace_bytes,
            anchor=anchor,
            repository_binding=repository_binding,
            commitment_id=commitment.commitment_id,
            public_key_id=public_key.key_id,
        ),
        _record(
            role=_ROLE_ORDER[1],
            semantic_artifact_id=authorization.authorization_id,
            raw=observer_open_authorization_bytes,
            anchor=anchor,
            repository_binding=repository_binding,
            commitment_id=commitment.commitment_id,
            public_key_id=public_key.key_id,
        ),
        _record(
            role=_ROLE_ORDER[2],
            semantic_artifact_id=reveal.attestation_id,
            raw=private_reveal_verification_attestation_bytes,
            anchor=anchor,
            repository_binding=repository_binding,
            commitment_id=commitment.commitment_id,
            public_key_id=public_key.key_id,
        ),
    )
    return V075PortablePublicContextRawResolutionV2(
        anchor,
        namespace,
        authorization,
        reveal,
        source_manifest,
        repository_binding,
        records,
        tuple(_attest(item) for item in records),
    )


_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePublicContextEvidenceClosureV2:
    _issuer: InitVar[object]
    repository_binding: V075PortablePublicContextRepositoryBindingV2
    source_manifest: V075PortablePublicContextSourceManifestV2
    remote_main_anchor_id: str
    opaque_environment_commitment_id: str
    namespace_public_key_id: str
    namespace_public_key_bytes: bytes = field(repr=False)
    dependency_records: tuple[
        V075PortablePublicContextDependencyRecordV2,
        ...,
    ]
    dependency_attestations: tuple[
        V075PortablePublicContextDependencyAttestationV2,
        ...,
    ]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.remote_main_anchor_id, "public-context closure anchor"),
            (
                self.opaque_environment_commitment_id,
                "public-context closure commitment",
            ),
            (self.namespace_public_key_id, "namespace public key"),
        ):
            _cid(value, label)
        if (
            _issuer is not _CLOSURE_ISSUER
            or type(self.repository_binding)
            is not V075PortablePublicContextRepositoryBindingV2
            or type(self.source_manifest)
            is not V075PortablePublicContextSourceManifestV2
            or self.repository_binding.source_manifest_id
            != self.source_manifest.manifest_id
            or self.repository_binding.remote_main_anchor_id
            != self.remote_main_anchor_id
            or tuple(item.role for item in self.dependency_records)
            != _ROLE_ORDER
            or tuple(item.role for item in self.dependency_attestations)
            != _ROLE_ORDER
            or tuple(item.record_id for item in self.dependency_records)
            != tuple(
                item.record_id for item in self.dependency_attestations
            )
            or any(
                item.remote_main_anchor_id != self.remote_main_anchor_id
                or item.repository_binding_id
                != self.repository_binding.binding_id
                or item.source_manifest_id
                != self.source_manifest.manifest_id
                or item.opaque_environment_commitment_id
                != self.opaque_environment_commitment_id
                or item.namespace_public_key_id
                != self.namespace_public_key_id
                for item in (
                    *self.dependency_records,
                    *self.dependency_attestations,
                )
            )
            or type(self.namespace_public_key_bytes) is not bytes
            or self.namespace_public_key_document.get("key_id")
            != self.namespace_public_key_id
            or self.namespace_public_key_document.get("key_role")
            != "OBSERVER_EVIDENCE"
            or self.namespace_public_key_document.get(
                "private_key_serialized"
            )
            is not False
        ):
            _fail("public-context closure graph is incomplete or transplanted")
        _assert_public_document(self.namespace_public_key_document)
        object.__setattr__(
            self,
            "_closure_id",
            _hash("closure", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_public_context_evidence_closure.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "repository_binding": self.repository_binding.to_document(),
            "repository_binding_id": self.repository_binding.binding_id,
            "source_manifest": self.source_manifest.to_document(),
            "source_manifest_id": self.source_manifest.manifest_id,
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "opaque_environment_commitment_id": (
                self.opaque_environment_commitment_id
            ),
            "namespace_public_key_id": self.namespace_public_key_id,
            "namespace_public_key": self.namespace_public_key_document,
            "dependency_role_order": [
                item.value for item in _ROLE_ORDER
            ],
            "dependency_records": [
                item.to_document() for item in self.dependency_records
            ],
            "dependency_record_ids": [
                item.record_id for item in self.dependency_records
            ],
            "dependency_attestations": [
                item.to_document()
                for item in self.dependency_attestations
            ],
            "dependency_attestation_ids": [
                item.attestation_id
                for item in self.dependency_attestations
            ],
            "dependency_record_count": len(self.dependency_records),
            "all_three_dependencies_present": True,
            "all_three_dependencies_independently_replayed": True,
            "remote_main_independently_replayed": True,
            "source_manifest_content_id_replayed": True,
            "source_manifest_authority_status": (
                SOURCE_MANIFEST_AUTHORITY_STATUS
            ),
            "ipc_source_snapshot_attestation": (
                _source_snapshot_attestation_not_supplied()
            ),
            "ipc_source_snapshot_attestation_status": (
                IPC_SOURCE_SNAPSHOT_ATTESTATION_STATUS
            ),
            "source_authority_complete": False,
            "source_archive_verified_by_this_closure": False,
            "multiround_result_used_as_dependency_bytes": False,
            "observer_opened": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "private_material_serialized": False,
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    @property
    def namespace_public_key_document(self) -> dict[str, Any]:
        return _strict_document(
            self.namespace_public_key_bytes,
            label="namespace public key",
            byte_cap=256 * 1024,
        )

    @property
    def canonical_bytes(self) -> bytes:
        raw = canonical_json_bytes(self.to_document())
        if len(raw) > MAX_CLOSURE_BYTES:
            _fail("public-context closure exceeds its canonical byte cap")
        return raw

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}


def freeze_v075_portable_public_context_evidence_closure_v2(
    *,
    repository_root: str | Path,
    source_manifest_bytes: bytes,
    namespace_bytes: bytes,
    observer_open_authorization_bytes: bytes,
    private_reveal_verification_attestation_bytes: bytes,
) -> V075PortablePublicContextEvidenceClosureV2:
    resolution = (
        resolve_v075_portable_public_context_raw_dependencies_v2(
            repository_root=repository_root,
            source_manifest_bytes=source_manifest_bytes,
            namespace_bytes=namespace_bytes,
            observer_open_authorization_bytes=(
                observer_open_authorization_bytes
            ),
            private_reveal_verification_attestation_bytes=(
                private_reveal_verification_attestation_bytes
            ),
        )
    )
    key = resolution.namespace.signer_registry.observer_evidence_key
    return V075PortablePublicContextEvidenceClosureV2(
        _CLOSURE_ISSUER,
        resolution.repository_binding,
        resolution.source_manifest,
        resolution.anchor.anchor_id,
        resolution.namespace.environment_commitment.commitment_id,
        key.key_id,
        canonical_json_bytes(key.to_document()),
        resolution.records,
        resolution.attestations,
    )


_CLOSURE_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "terminal_scope",
    "terminal_class",
    "terminal_code",
    "repository_binding",
    "repository_binding_id",
    "source_manifest",
    "source_manifest_id",
    "remote_main_anchor_id",
    "opaque_environment_commitment_id",
    "namespace_public_key_id",
    "namespace_public_key",
    "dependency_role_order",
    "dependency_records",
    "dependency_record_ids",
    "dependency_attestations",
    "dependency_attestation_ids",
    "dependency_record_count",
    "all_three_dependencies_present",
    "all_three_dependencies_independently_replayed",
    "remote_main_independently_replayed",
    "source_manifest_content_id_replayed",
    "source_manifest_authority_status",
    "ipc_source_snapshot_attestation",
    "ipc_source_snapshot_attestation_status",
    "source_authority_complete",
    "source_archive_verified_by_this_closure",
    "multiround_result_used_as_dependency_bytes",
    "observer_opened",
    "fresh_heldout_accessed",
    "official_execution_allowed",
    "production_authorizing",
    "scientific_endpoint_credit_allowed",
    "plan_certificate",
    "infeasibility_certificate",
    "private_material_serialized",
    "closure_id",
}


def verify_v075_portable_public_context_evidence_closure_bytes_v2(
    *,
    repository_root: str | Path,
    raw: bytes,
) -> V075PortablePublicContextEvidenceClosureV2:
    """Replay a closure from its embedded public records and compare bytes."""

    document = _strict_document(
        raw,
        label="portable public-context closure",
        byte_cap=MAX_CLOSURE_BYTES,
    )
    if (
        set(document) != _CLOSURE_KEYS
        or document["schema"]
        != "acfqp.v075_portable_public_context_evidence_closure.v2"
        or document["schema_version"] != SCHEMA_VERSION
        or document["profile_key"] != PROFILE_KEY
        or document["dependency_role_order"]
        != [item.value for item in _ROLE_ORDER]
        or type(document["dependency_records"]) is not list
        or len(document["dependency_records"]) != len(_ROLE_ORDER)
        or document["dependency_record_count"] != len(_ROLE_ORDER)
    ):
        _fail("portable public-context closure shape changed")
    _assert_public_document(document)

    records_by_role: dict[str, dict[str, Any]] = {}
    for item in document["dependency_records"]:
        if type(item) is not dict or type(item.get("role")) is not str:
            _fail("portable public-context dependency record is malformed")
        if item["role"] in records_by_role:
            _fail("portable public-context dependency role is duplicated")
        records_by_role[item["role"]] = item
    if tuple(records_by_role) != tuple(item.value for item in _ROLE_ORDER):
        _fail("portable public-context dependency role order changed")

    def artifact_bytes(
        role: V075PortablePublicContextDependencyRoleV2,
    ) -> bytes:
        item = records_by_role[role.value]
        artifact = item.get("artifact_document")
        if type(artifact) is not dict:
            _fail(f"{role.value} artifact document is missing")
        return canonical_json_bytes(artifact)

    source_manifest = document.get("source_manifest")
    if type(source_manifest) is not dict:
        _fail("portable public-context source manifest is missing")
    expected = freeze_v075_portable_public_context_evidence_closure_v2(
        repository_root=repository_root,
        source_manifest_bytes=canonical_json_bytes(source_manifest),
        namespace_bytes=artifact_bytes(_ROLE_ORDER[0]),
        observer_open_authorization_bytes=artifact_bytes(_ROLE_ORDER[1]),
        private_reveal_verification_attestation_bytes=artifact_bytes(
            _ROLE_ORDER[2]
        ),
    )
    if expected.canonical_bytes != raw:
        _fail(
            "portable public-context closure is stale, transplanted, "
            "or caller-authored"
        )
    return expected


def open_v075_production_from_public_context_closure_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PortablePublicContextProductionV2NotReady(
        "VERIFIED_IPC_SOURCE_SNAPSHOT_ATTESTATION_NOT_SUPPLIED: "
        "source authority is incomplete and production remains locked"
    )


__all__ = [
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "MAX_CLOSURE_BYTES",
    "MAX_DEPENDENCY_BYTES",
    "MAX_SOURCE_MANIFEST_BYTES",
    "MULTIROUND_RESULT_CONTAINS_CANONICAL_PUBLIC_CONTEXT_BYTES",
    "OBSERVER_OPEN_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "IPC_SOURCE_SNAPSHOT_ATTESTATION_STATUS",
    "PRIVATE_INPUT_CHANNELS_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SOURCE_AUTHORITY_COMPLETE",
    "SOURCE_MANIFEST_AUTHORITY_STATUS",
    "SOURCE_MANIFEST_DOMAIN_TAG",
    "V075PortablePublicContextDependencyAttestationV2",
    "V075PortablePublicContextDependencyRecordV2",
    "V075PortablePublicContextDependencyRoleV2",
    "V075PortablePublicContextEvidenceClosureV2",
    "V075PortablePublicContextProductionV2NotReady",
    "V075PortablePublicContextRawResolutionV2",
    "V075PortablePublicContextRepositoryBindingV2",
    "V075PortablePublicContextSourceManifestEntryV2",
    "V075PortablePublicContextSourceManifestV2",
    "V075PortablePublicContextV2InvariantViolation",
    "freeze_v075_portable_public_context_evidence_closure_v2",
    "open_v075_production_from_public_context_closure_v2",
    "replay_v075_portable_public_context_source_manifest_bytes_v2",
    "resolve_v075_portable_public_context_raw_dependencies_v2",
    "verify_v075_portable_public_context_evidence_closure_bytes_v2",
]
