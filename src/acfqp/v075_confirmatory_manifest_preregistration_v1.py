"""Law-free V0-075 manifest and final-preregistration authority.

This module freezes only public, pre-target execution inputs.  It never opens
an observer and it never accepts a transition law or environment reveal.

The binding direction is deliberately one way::

    concrete public prerequisites -> execution manifest -> final preregistration

The manifest has no final-preregistration field.  The final preregistration
contains the manifest ID and pins the complete signer-registry public-key
bytes.  Neither artifact is executable until an independent verifier finds
the first qualifying ``origin/main`` commit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_public_campaign_authority_v1 as public_authority


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_confirmatory_manifest_preregistration_v1"

REPOSITORY_URL = (
    "git@github.com:erzhu419/"
    "Auditable-Coarse-to-Fine-Quotient-Planning.git"
)
TARGET_BRANCH = "main"
MANIFEST_REPOSITORY_PATH = (
    "specs/V075_CONFIRMATORY_EXECUTION_MANIFEST.json"
)
FINAL_PREREGISTRATION_REPOSITORY_PATH = (
    "specs/V075_FINAL_PREREGISTRATION.json"
)

EXACT_TEST_COMMAND = (
    "python3",
    "-m",
    "pytest",
    "-q",
    "-s",
    "tests/test_v075_registered_campaign.py",
)
DETERMINISTIC_ENVIRONMENT = (
    ("LC_ALL", "C.UTF-8"),
    ("PYTHONHASHSEED", "0"),
    ("TZ", "UTC"),
)

# These paths are part of the manifest schema, rather than a caller-selected
# list.  Missing future production components are intentional readiness
# blockers in the current construction state.
REQUIRED_COMPONENT_SPECS = (
    (
        "MANIFEST_AND_PREREGISTRATION_AUTHORITY",
        "src/acfqp/v075_confirmatory_manifest_preregistration_v1.py",
    ),
    (
        "INDEPENDENT_REMOTE_MAIN_ANCHOR_VERIFIER",
        "src/acfqp/v075_remote_main_anchor_verifier_v1.py",
    ),
    (
        "LAW_FREE_PUBLIC_CAMPAIGN_AUTHORITY",
        "src/acfqp/v075_public_campaign_authority_v1.py",
    ),
    (
        "PUBLIC_GRAPH_SEMANTICS",
        "src/acfqp/v075_public_graph_semantics_v1.py",
    ),
    (
        "SOURCE_PRIOR_ADAPTER_AUTHORITY",
        "src/acfqp/v075_source_prior_adapter_v1.py",
    ),
    (
        "FROZEN_SOURCE_PROPOSAL_ARCHIVE",
        "src/acfqp/v075_frozen_source_proposal_archive_v1.py",
    ),
    (
        "SOURCE_OFFLINE_WORK_MATERIALIZER",
        "src/acfqp/v075_source_offline_work_materializer_v1.py",
    ),
    (
        "SOURCE_REPLAY_AND_MATERIALIZATION_CONTROLLER",
        "scripts/replay_and_materialize_v075_source_work.py",
    ),
    (
        "EXACT_H2_TRANSITION_ENGINE",
        "src/acfqp/h2_graph_transition_engine_v1.py",
    ),
    (
        "OCCURRENCE_CAS_TRANSPORT",
        "src/acfqp/v075_occurrence_cas_transport_v1.py",
    ),
    (
        "PRIVATE_OBSERVER_BOUNDARY",
        "src/acfqp/v075_private_observer_boundary_v1.py",
    ),
    (
        "TOTAL_LIFT_AUTHORITY",
        "src/acfqp/v075_total_lift_authority_v1.py",
    ),
    (
        "CAMPAIGN_RECONCILIATION_AUTHORITY",
        "src/acfqp/v075_campaign_reconciliation_v1.py",
    ),
    (
        "COMPLETE_BUNDLE_ENDPOINT_VERIFIER",
        "src/acfqp/v075_complete_bundle_endpoint_verifier_v1.py",
    ),
    (
        "PRODUCTION_CAMPAIGN_ENTRYPOINT",
        "scripts/run_v075_registered_campaign.py",
    ),
    (
        "PRODUCTION_CONFIRMATORY_TEST",
        "tests/test_v075_registered_campaign.py",
    ),
    (
        "DEPENDENCY_LOCK",
        "specs/V075_DEPENDENCY_LOCK.json",
    ),
    (
        "PRODUCTION_WORKER_REGISTRY",
        "specs/V075_PRODUCTION_WORKER_REGISTRY.json",
    ),
)

if (
    len(REQUIRED_COMPONENT_SPECS)
    != len({role for role, _path in REQUIRED_COMPONENT_SPECS})
    or len(REQUIRED_COMPONENT_SPECS)
    != len({path for _role, path in REQUIRED_COMPONENT_SPECS})
):
    raise RuntimeError("V0-075 component registry is not one-to-one")


class V075ManifestAuthorityRoleV1(str, Enum):
    OBSERVER_PROFILE = "OBSERVER_PROFILE"
    SOURCE_PRIOR_ADAPTER = "SOURCE_PRIOR_ADAPTER"
    SOURCE_PRIOR_ADAPTER_VERIFICATION = (
        "SOURCE_PRIOR_ADAPTER_VERIFICATION"
    )
    DEPENDENCY_LOCK = "DEPENDENCY_LOCK"
    PRODUCTION_WORKER_REGISTRY = "PRODUCTION_WORKER_REGISTRY"
    OCCURRENCE_CAS_TRANSPORT = "OCCURRENCE_CAS_TRANSPORT"
    EXACT_H2_TRANSITION_ENGINE = "EXACT_H2_TRANSITION_ENGINE"
    TOTAL_LIFT = "TOTAL_LIFT"
    CAMPAIGN_RECONCILIATION = "CAMPAIGN_RECONCILIATION"
    COMPLETE_BUNDLE_ENDPOINT = "COMPLETE_BUNDLE_ENDPOINT"


REQUIRED_AUTHORITY_ROLE_ORDER = tuple(V075ManifestAuthorityRoleV1)

DOMAIN_TAGS = {
    "component_blob": "acfqp:v075-manifest-component-blob:v1",
    "authority_binding": "acfqp:v075-manifest-authority-binding:v1",
    "authority_registry": "acfqp:v075-manifest-authority-registry:v1",
    "component_registry": "acfqp:v075-manifest-component-registry:v1",
    "readiness": "acfqp:v075-confirmatory-manifest-readiness:v1",
    "manifest": "acfqp:v075-confirmatory-execution-manifest:v1",
    "final_preregistration": "acfqp:v075-final-preregistration:v1",
}


class V075ConfirmatoryAuthorityInvariantViolation(ValueError):
    """A V0-075 manifest or preregistration invariant failed."""


class V075ConfirmatoryAuthorityNotReady(RuntimeError):
    """Concrete, public prerequisites are incomplete."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        body = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role].encode("utf-8")
    except (KeyError, TypeError, ValueError) as error:
        raise V075ConfirmatoryAuthorityInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ConfirmatoryAuthorityInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _git_oid(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) not in (40, 64)
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V075ConfirmatoryAuthorityInvariantViolation(
            f"{field_name} must be one full lowercase Git object ID"
        )
    return value


def _token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        raise V075ConfirmatoryAuthorityInvariantViolation(
            f"{field_name} must be canonical nonempty text"
        )
    return value


def _safe_path(value: Any) -> str:
    text = _token(value, "repository path")
    if "\\" in text:
        raise V075ConfirmatoryAuthorityInvariantViolation(
            "repository path must use POSIX separators"
        )
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or str(path) != text
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise V075ConfirmatoryAuthorityInvariantViolation(
            "repository path is unsafe or noncanonical"
        )
    return text


def _run_git(root: Path, *arguments: str) -> str:
    process = subprocess.run(
        ("git", "-C", str(root), *arguments),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )
    if process.returncode:
        raise V075ConfirmatoryAuthorityInvariantViolation(
            "Git inspection failed: "
            + process.stderr.decode("utf-8", errors="replace").strip()
        )
    return process.stdout.decode("utf-8").strip()


@dataclass(frozen=True, slots=True)
class V075ComponentBlobV1:
    role: str
    repository_path: str
    git_blob_id: str
    bytes_sha256: str
    byte_count: int
    executable: bool

    def __post_init__(self) -> None:
        expected = dict(REQUIRED_COMPONENT_SPECS).get(self.role)
        if expected is None or _safe_path(self.repository_path) != expected:
            raise V075ConfirmatoryAuthorityInvariantViolation(
                "component role/path is not registered"
            )
        _git_oid(self.git_blob_id, "component Git blob")
        _cid(self.bytes_sha256, "component byte digest")
        if (
            type(self.byte_count) is not int
            or self.byte_count < 1
            or type(self.executable) is not bool
        ):
            raise V075ConfirmatoryAuthorityInvariantViolation(
                "component byte metadata is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_manifest_component_blob.v1",
            "schema_version": SCHEMA_VERSION,
            "role": self.role,
            "repository_path": self.repository_path,
            "git_blob_id": self.git_blob_id,
            "bytes_sha256": self.bytes_sha256,
            "byte_count": self.byte_count,
            "executable": self.executable,
            "worktree_bytes_equal_index_blob": True,
            "target_accessed": False,
        }

    @property
    def component_id(self) -> str:
        return _content_id("component_blob", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "component_id": self.component_id}


def collect_v075_component_blob_v1(
    repository_root: str | os.PathLike[str],
    *,
    role: str,
) -> V075ComponentBlobV1:
    """Bind one exact regular worktree file to its stage-zero index blob."""

    expected_path = dict(REQUIRED_COMPONENT_SPECS).get(role)
    if expected_path is None:
        raise V075ConfirmatoryAuthorityInvariantViolation(
            "component role is not registered"
        )
    root = Path(repository_root).resolve(strict=True)
    candidate = root.joinpath(*PurePosixPath(expected_path).parts)
    cursor = root
    for part in PurePosixPath(expected_path).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise V075ConfirmatoryAuthorityInvariantViolation(
                "component path contains a symlink"
            )
    metadata = candidate.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise V075ConfirmatoryAuthorityInvariantViolation(
            "component is not one regular file"
        )
    data = candidate.read_bytes()
    if not data:
        raise V075ConfirmatoryAuthorityInvariantViolation(
            "component file is empty"
        )
    stage = _run_git(root, "ls-files", "--stage", "--", expected_path)
    lines = [line for line in stage.splitlines() if line]
    if len(lines) != 1 or "\t" not in lines[0]:
        raise V075ConfirmatoryAuthorityInvariantViolation(
            "component has no unique stage-zero Git index entry"
        )
    prefix, indexed_path = lines[0].split("\t", 1)
    fields = prefix.split()
    if (
        indexed_path != expected_path
        or len(fields) != 3
        or fields[2] != "0"
        or fields[0] not in {"100644", "100755"}
    ):
        raise V075ConfirmatoryAuthorityInvariantViolation(
            "component Git index entry is malformed"
        )
    blob_id = _git_oid(fields[1], "indexed component blob")
    process = subprocess.run(
        ("git", "-C", str(root), "cat-file", "blob", blob_id),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )
    if process.returncode or process.stdout != data:
        raise V075ConfirmatoryAuthorityInvariantViolation(
            "component worktree bytes differ from the indexed blob"
        )
    return V075ComponentBlobV1(
        role,
        expected_path,
        blob_id,
        hashlib.sha256(data).hexdigest(),
        len(data),
        fields[0] == "100755",
    )


@dataclass(frozen=True, slots=True)
class V075ConcreteAuthorityBindingV1:
    _issuer: object = field(repr=False, compare=False)
    role: V075ManifestAuthorityRoleV1
    authority_id: str
    independent_verification_id: str
    canonical_artifact_sha256: str

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.role) is not V075ManifestAuthorityRoleV1
        ):
            raise V075ConfirmatoryAuthorityInvariantViolation(
                "authority binding is semantic-verifier-issued only"
            )
        values = (
            _cid(self.authority_id, "bound authority"),
            _cid(
                self.independent_verification_id,
                "authority independent verification",
            ),
            _cid(
                self.canonical_artifact_sha256,
                "authority artifact digest",
            ),
        )
        if len(set(values)) != 3:
            raise V075ConfirmatoryAuthorityInvariantViolation(
                "authority binding aliases incompatible identity roles"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_manifest_authority_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "role": self.role.value,
            "authority_id": self.authority_id,
            "independent_verification_id": (
                self.independent_verification_id
            ),
            "canonical_artifact_sha256": (
                self.canonical_artifact_sha256
            ),
            "binding_status": "CONCRETE_AND_INDEPENDENTLY_VERIFIED",
            "placeholder": False,
            "target_accessed": False,
        }

    @property
    def binding_id(self) -> str:
        return _content_id("authority_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class V075AuthorityPlaceholderV1:
    role: V075ManifestAuthorityRoleV1
    blocker_code: str

    def __post_init__(self) -> None:
        if type(self.role) is not V075ManifestAuthorityRoleV1:
            raise V075ConfirmatoryAuthorityInvariantViolation(
                "authority placeholder role is not typed"
            )
        _token(self.blocker_code, "authority blocker")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConfirmatoryExecutionManifestV1:
    _issuer: object = field(repr=False, compare=False)
    signer_registry: public_authority.V075TrustedSignerRegistryV1
    opaque_environment_commitment: (
        public_authority.V075OpaqueEnvironmentCommitmentV1
    )
    component_blobs: tuple[V075ComponentBlobV1, ...]
    authority_bindings: tuple[V075ConcreteAuthorityBindingV1, ...]
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        family = public_authority.freeze_v075_public_family_generation_v1()
        if (
            self._issuer is not _ISSUER
            or type(self.signer_registry)
            is not public_authority.V075TrustedSignerRegistryV1
            or type(self.opaque_environment_commitment)
            is not public_authority.V075OpaqueEnvironmentCommitmentV1
            or self.opaque_environment_commitment.family != family
            or type(self.component_blobs) is not tuple
            or tuple(type(item) for item in self.component_blobs)
            != (V075ComponentBlobV1,) * len(REQUIRED_COMPONENT_SPECS)
            or tuple(
                (item.role, item.repository_path)
                for item in self.component_blobs
            )
            != REQUIRED_COMPONENT_SPECS
            or type(self.authority_bindings) is not tuple
            or tuple(type(item) for item in self.authority_bindings)
            != (V075ConcreteAuthorityBindingV1,)
            * len(REQUIRED_AUTHORITY_ROLE_ORDER)
            or tuple(item.role for item in self.authority_bindings)
            != REQUIRED_AUTHORITY_ROLE_ORDER
        ):
            raise V075ConfirmatoryAuthorityInvariantViolation(
                "manifest is not exact, complete, ordered, and factory-issued"
            )
        all_role_ids = (
            [item.component_id for item in self.component_blobs]
            + [item.binding_id for item in self.authority_bindings]
            + [
                self.signer_registry.registry_id,
                self.opaque_environment_commitment.commitment_id,
            ]
        )
        if len(all_role_ids) != len(set(all_role_ids)):
            raise V075ConfirmatoryAuthorityInvariantViolation(
                "manifest aliases incompatible component/authority roles"
            )
        object.__setattr__(
            self,
            "_manifest_id",
            _content_id("manifest", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        family = public_authority.freeze_v075_public_family_generation_v1()
        component_documents = [
            item.to_document() for item in self.component_blobs
        ]
        binding_documents = [
            item.to_document() for item in self.authority_bindings
        ]
        return {
            "schema": "acfqp.v075_confirmatory_execution_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "repository_url": REPOSITORY_URL,
            "target_branch": TARGET_BRANCH,
            "family_generation_id": family.generation_id,
            "replicate_context_ids": [
                item.context_id for item in family.replicate_contexts
            ],
            "signer_registry_id": self.signer_registry.registry_id,
            "opaque_environment_commitment": (
                self.opaque_environment_commitment.to_document()
            ),
            "opaque_environment_commitment_id": (
                self.opaque_environment_commitment.commitment_id
            ),
            "component_blobs": component_documents,
            "component_registry_id": _content_id(
                "component_registry",
                {"components": component_documents},
            ),
            "authority_bindings": binding_documents,
            "authority_registry_id": _content_id(
                "authority_registry",
                {"bindings": binding_documents},
            ),
            "exact_test_command": list(EXACT_TEST_COMMAND),
            "deterministic_environment": [
                {"name": name, "value": value}
                for name, value in DETERMINISTIC_ENVIRONMENT
            ],
            "dependency_lock_bound": True,
            "production_worker_registry_bound": True,
            "transport_engine_total_lift_reconciliation_endpoint_bound": True,
            "source_adapter_authority_bound": True,
            "law_free_public_dependency_graph": True,
            "private_environment_reveal_serialized": False,
            "target_accessed": False,
            "final_preregistration_id_embedded": False,
            "future_binding_direction": (
                "MANIFEST_THEN_FINAL_PREREGISTRATION_THEN_REMOTE_MAIN"
            ),
            "target_execution_allowed": False,
        }

    @property
    def manifest_id(self) -> str:
        return self._manifest_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


@dataclass(frozen=True, slots=True)
class V075ManifestReadinessV1:
    _issuer: object = field(repr=False, compare=False)
    blockers: tuple[str, ...]
    component_ids: tuple[str, ...]
    authority_binding_ids: tuple[str, ...]
    manifest: V075ConfirmatoryExecutionManifestV1 | None
    _readiness_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.blockers) is not tuple
            or self.blockers != tuple(sorted(set(self.blockers)))
            or any(type(item) is not str or not item for item in self.blockers)
            or type(self.component_ids) is not tuple
            or type(self.authority_binding_ids) is not tuple
            or (
                self.manifest is not None
                and type(self.manifest)
                is not V075ConfirmatoryExecutionManifestV1
            )
            or ((not self.blockers) != (self.manifest is not None))
        ):
            raise V075ConfirmatoryAuthorityInvariantViolation(
                "manifest readiness report is malformed"
            )
        for item in self.component_ids:
            _cid(item, "readiness component")
        for item in self.authority_binding_ids:
            _cid(item, "readiness authority binding")
        object.__setattr__(
            self,
            "_readiness_id",
            _content_id("readiness", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_confirmatory_manifest_readiness.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "blockers": list(self.blockers),
            "component_ids": list(self.component_ids),
            "authority_binding_ids": list(self.authority_binding_ids),
            "ready": not self.blockers,
            "manifest_id": (
                None if self.manifest is None else self.manifest.manifest_id
            ),
            "registered_target_execution_allowed": False,
            "official_execution_allowed": False,
            "registered_observer_calls": 0,
            "target_accessed": False,
        }

    @property
    def readiness_id(self) -> str:
        return self._readiness_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "readiness_id": self.readiness_id}


def assess_v075_manifest_readiness_v1(
    repository_root: str | os.PathLike[str],
    *,
    signer_registry: Any = None,
    opaque_environment_commitment: Any = None,
    authority_inputs: tuple[
        V075ConcreteAuthorityBindingV1 | V075AuthorityPlaceholderV1, ...
    ] = (),
) -> V075ManifestReadinessV1:
    """Audit public prerequisites without touching a target observer."""

    blockers: list[str] = []
    components: list[V075ComponentBlobV1] = []
    root = Path(repository_root)
    for role, _path in REQUIRED_COMPONENT_SPECS:
        try:
            components.append(
                collect_v075_component_blob_v1(root, role=role)
            )
        except (
            OSError,
            subprocess.SubprocessError,
            V075ConfirmatoryAuthorityInvariantViolation,
        ):
            blockers.append(f"COMPONENT_NOT_CONCRETE:{role}")

    if (
        type(signer_registry)
        is not public_authority.V075TrustedSignerRegistryV1
    ):
        blockers.append("TRACKED_SIGNER_REGISTRY_NOT_CONCRETE")
    if (
        type(opaque_environment_commitment)
        is not public_authority.V075OpaqueEnvironmentCommitmentV1
    ):
        blockers.append("OPAQUE_ENVIRONMENT_COMMITMENT_NOT_CONCRETE")

    bindings: list[V075ConcreteAuthorityBindingV1] = []
    if type(authority_inputs) is not tuple:
        blockers.append("AUTHORITY_INPUTS_NOT_TYPED_TUPLE")
    else:
        seen: set[V075ManifestAuthorityRoleV1] = set()
        for item in authority_inputs:
            if type(item) is V075ConcreteAuthorityBindingV1:
                if item.role in seen:
                    blockers.append(
                        f"DUPLICATE_AUTHORITY_ROLE:{item.role.value}"
                    )
                else:
                    seen.add(item.role)
                    bindings.append(item)
            elif type(item) is V075AuthorityPlaceholderV1:
                if item.role in seen:
                    blockers.append(
                        f"DUPLICATE_AUTHORITY_ROLE:{item.role.value}"
                    )
                else:
                    seen.add(item.role)
                    blockers.append(item.blocker_code)
            else:
                blockers.append("AUTHORITY_INPUT_DUCK_TYPE_REJECTED")
        for role in REQUIRED_AUTHORITY_ROLE_ORDER:
            if role not in seen:
                blockers.append(f"AUTHORITY_NOT_CONCRETE:{role.value}")

    manifest: V075ConfirmatoryExecutionManifestV1 | None = None
    if not blockers:
        assert (
            type(signer_registry)
            is public_authority.V075TrustedSignerRegistryV1
        )
        assert (
            type(opaque_environment_commitment)
            is public_authority.V075OpaqueEnvironmentCommitmentV1
        )
        manifest = V075ConfirmatoryExecutionManifestV1(
            _ISSUER,
            signer_registry,
            opaque_environment_commitment,
            tuple(components),
            tuple(
                sorted(
                    bindings,
                    key=lambda item: REQUIRED_AUTHORITY_ROLE_ORDER.index(
                        item.role
                    ),
                )
            ),
        )
    return V075ManifestReadinessV1(
        _ISSUER,
        tuple(sorted(set(blockers))),
        tuple(item.component_id for item in components),
        tuple(item.binding_id for item in bindings),
        manifest,
    )


def require_ready_v075_manifest_v1(
    readiness: V075ManifestReadinessV1,
) -> V075ConfirmatoryExecutionManifestV1:
    if (
        type(readiness) is not V075ManifestReadinessV1
        or readiness.manifest is None
        or readiness.blockers
    ):
        raise V075ConfirmatoryAuthorityNotReady(
            "V0-075 confirmatory manifest prerequisites are incomplete"
        )
    return readiness.manifest


@dataclass(frozen=True, slots=True)
class V075FinalPreregistrationV1:
    _issuer: object = field(repr=False, compare=False)
    manifest: V075ConfirmatoryExecutionManifestV1
    _final_preregistration_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.manifest)
            is not V075ConfirmatoryExecutionManifestV1
        ):
            raise V075ConfirmatoryAuthorityInvariantViolation(
                "final preregistration is factory-issued from one exact manifest"
            )
        object.__setattr__(
            self,
            "_final_preregistration_id",
            _content_id("final_preregistration", self._payload()),
        )
        final_id = self._final_preregistration_id
        if (
            final_id.encode("ascii") in self.manifest.canonical_bytes
            or b"final_preregistration_id" in self.manifest.canonical_bytes
        ):
            raise V075ConfirmatoryAuthorityInvariantViolation(
                "manifest circularly embeds final-preregistration authority"
            )

    def _payload(self) -> dict[str, Any]:
        family = public_authority.freeze_v075_public_family_generation_v1()
        registry = self.manifest.signer_registry
        return {
            "schema": "acfqp.v075_final_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "repository_url": REPOSITORY_URL,
            "target_branch": TARGET_BRANCH,
            "confirmatory_execution_manifest_id": self.manifest.manifest_id,
            "confirmatory_execution_manifest_bytes_sha256": (
                hashlib.sha256(self.manifest.canonical_bytes).hexdigest()
            ),
            "family_generation_id": family.generation_id,
            "replicate_context_ids": [
                item.context_id for item in family.replicate_contexts
            ],
            "opaque_environment_commitment_id": (
                self.manifest.opaque_environment_commitment.commitment_id
            ),
            "signer_registry_id": registry.registry_id,
            "signer_registry": registry.to_document(),
            "campaign_authority_public_key_bytes": (
                canonical_json_bytes(
                    registry.campaign_authority_key.to_document()
                ).hex()
            ),
            "observer_evidence_public_key_bytes": (
                canonical_json_bytes(
                    registry.observer_evidence_key.to_document()
                ).hex()
            ),
            "component_registry_id": self.manifest.to_document()[
                "component_registry_id"
            ],
            "authority_registry_id": self.manifest.to_document()[
                "authority_registry_id"
            ],
            "exact_test_command": list(EXACT_TEST_COMMAND),
            "manifest_precedes_final_preregistration": True,
            "manifest_contains_final_preregistration_id": False,
            "remote_main_anchor_id": None,
            "observer_open_allowed": False,
            "registered_target_execution_allowed": False,
            "official_execution_allowed": False,
            "target_accessed": False,
        }

    @property
    def final_preregistration_id(self) -> str:
        return self._final_preregistration_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "final_preregistration_id": self.final_preregistration_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def finalize_v075_preregistration_v1(
    readiness: V075ManifestReadinessV1,
) -> V075FinalPreregistrationV1:
    manifest = require_ready_v075_manifest_v1(readiness)
    return V075FinalPreregistrationV1(_ISSUER, manifest)


def current_v075_pretarget_readiness_v1(
    repository_root: str | os.PathLike[str],
) -> V075ManifestReadinessV1:
    """Return the honest construction-state report with no secret inputs."""

    placeholders = tuple(
        V075AuthorityPlaceholderV1(
            role,
            f"{role.value}_PRODUCTION_AUTHORITY_NOT_CONCRETE",
        )
        for role in REQUIRED_AUTHORITY_ROLE_ORDER
    )
    return assess_v075_manifest_readiness_v1(
        repository_root,
        authority_inputs=placeholders,
    )


__all__ = [
    "DETERMINISTIC_ENVIRONMENT",
    "DOMAIN_TAGS",
    "EXACT_TEST_COMMAND",
    "FINAL_PREREGISTRATION_REPOSITORY_PATH",
    "MANIFEST_REPOSITORY_PATH",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REPOSITORY_URL",
    "REQUIRED_AUTHORITY_ROLE_ORDER",
    "REQUIRED_COMPONENT_SPECS",
    "SCHEMA_VERSION",
    "TARGET_BRANCH",
    "V075AuthorityPlaceholderV1",
    "V075ComponentBlobV1",
    "V075ConcreteAuthorityBindingV1",
    "V075ConfirmatoryAuthorityInvariantViolation",
    "V075ConfirmatoryAuthorityNotReady",
    "V075ConfirmatoryExecutionManifestV1",
    "V075FinalPreregistrationV1",
    "V075ManifestAuthorityRoleV1",
    "V075ManifestReadinessV1",
    "assess_v075_manifest_readiness_v1",
    "collect_v075_component_blob_v1",
    "current_v075_pretarget_readiness_v1",
    "finalize_v075_preregistration_v1",
    "require_ready_v075_manifest_v1",
]
