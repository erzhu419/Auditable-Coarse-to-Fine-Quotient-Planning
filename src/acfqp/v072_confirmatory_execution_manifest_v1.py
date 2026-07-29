"""Finalization authority for the V0-072 execution manifest.

This module performs a strict, local, read-only audit of the repository tree.
It derives byte digests and a content-addressed nonauthorizing readiness
report.  Once every typed prerequisite is complete, it can internally mint
and idempotently write the final manifest.  It never mints an anchor, accesses
a remote, or opens a registered target observer.

The final manifest has no final-preregistration field.  Its dependency is
one-way: a later final preregistration will bind the manifest ID, and a still
later remote-main anchor verifier will bind that pair to a commit.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_execution_environment_authority_v1 as execution_env
from acfqp import (
    v072_execution_environment_independent_verifier_v1
    as execution_env_independent,
)
from acfqp import observation_support_campaign_v1 as source_campaign_v1
from acfqp import verified_source_acquisition_archive_v2 as source_archive_v2
from acfqp import (
    verified_source_acquisition_archive_independent_verifier_v2
    as source_archive_independent_v2,
)
from acfqp import (
    v072_verified_source_archive_component_v1
    as source_archive_component_v1,
)
from acfqp import (
    v072_source_reconstruction_recipe_v1
    as source_reconstruction_recipe_v1,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_confirmatory_execution_manifest_readiness_v0"
READINESS_STATUS = "NONAUTHORIZING_READINESS"
FINALIZATION_ENABLED = True
TARGET_EXECUTION_ALLOWED = False
SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED_BLOCKER = (
    "CANONICAL_SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED"
)
SOURCE_RECONSTRUCTION_RECIPE_REPLAY_FAILED_BLOCKER = (
    "REAL_SOURCE_RECONSTRUCTION_RECIPE_REPLAY_FAILED"
)
SOURCE_RECONSTRUCTION_RECIPE_NOT_TRACKED_BLOCKER = (
    "SOURCE_RECONSTRUCTION_RECIPE_NOT_TRACKED_IN_GIT"
)
SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH = (
    "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json"
)
FINAL_MANIFEST_REPOSITORY_PATH = (
    "specs/V072_CONFIRMATORY_EXECUTION_MANIFEST.json"
)

REPOSITORY_URL = (
    "git@github.com:erzhu419/"
    "Auditable-Coarse-to-Fine-Quotient-Planning.git"
)
TARGET_BRANCH = "main"
DEVELOPMENT_SYNTHETIC_MODULE_PATH = (
    "src/acfqp/v072_development_synthetic_transition_control_v1.py"
)

EXACT_TEST_COMMAND = execution_env.EXACT_TEST_COMMAND
DETERMINISTIC_ENVIRONMENT_SETTINGS = (
    execution_env.DETERMINISTIC_ENVIRONMENT_SETTINGS
)

COMPONENT_ROLE_ORDER = (
    "normative specification",
    "preregistration authority",
    "verified source-archive builder and independent verifier",
    "portable-feature consensus authority",
    "target preauthorization selector and selector verifier",
    (
        "registered observer, raw-commitment replay, and "
        "support-epoch-chain verifier"
    ),
    "partial-support confidence authority",
    (
        "public legal-action catalogue and novel-child "
        "cardinality authority"
    ),
    "cold H2 closure and relational/ground model builders",
    "incremental materializer and fresh round-2 authority",
    "exact lazy H2 planner and independent proof verifier",
    "matched direct-ground baseline",
    "independent exact ground evaluator",
    "five-arm confirmatory campaign runner",
    "fresh-only durable attempt progress/failure journal",
    "standalone complete-bundle and endpoint verifier",
    "counter/access-log/accepted-draw reconciliation authority",
    "confirmatory tests and the exact test-command manifest",
    "runtime/dependency lock and interpreter build identity",
)

if len(COMPONENT_ROLE_ORDER) != len(set(COMPONENT_ROLE_ORDER)):
    raise RuntimeError("V0-072 component-role order must be unique")


DOMAIN_TAGS = {
    "typed_na": "acfqp:v072-manifest-typed-not-applicable:v1",
    "component_record": "acfqp:v072-manifest-component-record:v1",
    "component_registry": "acfqp:v072-manifest-component-registry:v1",
    "component_tree": "acfqp:v072-manifest-component-tree:v1",
    "dependency_record": "acfqp:v072-execution-dependency-record:v1",
    "dependency_closure": "acfqp:v072-execution-dependency-closure:v1",
    "profile": "acfqp:v072-manifest-bound-profile:v1",
    "readiness": "acfqp:v072-confirmatory-manifest-readiness:v1",
    "final_manifest": "acfqp:v072-confirmatory-execution-manifest:v1",
}

MANIFEST_AUTHORITY_PATH = (
    "src/acfqp/v072_confirmatory_execution_manifest_v1.py"
)
PRODUCTION_ENTRYPOINT_PATHS = (
    "scripts/freeze_v072_source_reconstruction_recipe.py",
    "scripts/run_v072_registered_campaign.py",
)


class V072ConfirmatoryExecutionManifestV1InvariantViolation(ValueError):
    """A role, file, digest, identity, or finalization invariant failed."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(tag + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        canonical = parse_content_id(value)
    except ValueError as error:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error
    if canonical in prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            f"{field} is a permanently retired development identity"
        )
    return canonical


def _token(value: Any, field: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            f"{field} must be one nonempty canonical string"
        )
    return value


def _safe_relative_path(value: Any) -> str:
    if (
        type(value) is not str
        or not value
        or "\\" in value
        or "\x00" in value
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "component path must be a nonempty POSIX repo-relative path"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "component path is absolute, noncanonical, or traverses"
        )
    return value


def _fixed_source_recipe_path_v1(root: Path) -> Path:
    relative = _safe_relative_path(
        SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
    )
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    cursor = root
    for part in PurePosixPath(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "fixed source recipe path contains a symlink"
            )
    return candidate


def _source_recipe_git_status_v1(root: Path) -> tuple[bool, bool]:
    relative = SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
    ignored = subprocess.run(
        ("git", "-C", str(root), "check-ignore", "--quiet", "--", relative),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
        timeout=15,
    )
    if ignored.returncode not in (0, 1):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "cannot verify that the fixed source recipe path is unignored"
        )
    tracked = subprocess.run(
        (
            "git",
            "-C",
            str(root),
            "ls-files",
            "--error-unmatch",
            "--",
            relative,
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
        timeout=15,
    )
    if tracked.returncode not in (0, 1):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "cannot verify fixed source recipe Git tracking"
        )
    return ignored.returncode == 0, tracked.returncode == 0


@dataclass(frozen=True, slots=True)
class TypedNotApplicableV1:
    reason_code: str = "NO_STANDALONE_COMPONENT_CONTENT_ID"

    def __post_init__(self) -> None:
        if self.reason_code != "NO_STANDALONE_COMPONENT_CONTENT_ID":
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "typed N/A reason is not registered"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_manifest_typed_not_applicable.v1",
            "schema_version": SCHEMA_VERSION,
            "kind": "NOT_APPLICABLE",
            "reason_code": self.reason_code,
        }

    @property
    def typed_na_id(self) -> str:
        return _content_id("typed_na", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "typed_na_id": self.typed_na_id}


TYPED_NOT_APPLICABLE = TypedNotApplicableV1()


@dataclass(frozen=True, slots=True)
class ComponentRoleSpecV1:
    component_role: str
    repository_relative_path: str
    schema_or_protocol_id: str
    content_identity: str | TypedNotApplicableV1

    def __post_init__(self) -> None:
        _token(self.component_role, "component role")
        _safe_relative_path(self.repository_relative_path)
        _token(self.schema_or_protocol_id, "schema/protocol ID")
        if self.repository_relative_path == DEVELOPMENT_SYNTHETIC_MODULE_PATH:
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "development synthetic module is excluded from confirmatory roles"
            )
        if type(self.content_identity) is str:
            _cid(self.content_identity, "applicable component content ID")
        elif type(self.content_identity) is not TypedNotApplicableV1:
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "component content identity must be a content ID or typed N/A"
            )


def _role_spec(
    role: str,
    path: str,
    protocol: str,
) -> ComponentRoleSpecV1:
    return ComponentRoleSpecV1(
        role,
        path,
        protocol,
        TYPED_NOT_APPLICABLE,
    )


COMPONENT_ROLE_SPECS = (
    _role_spec(
        COMPONENT_ROLE_ORDER[0],
        "specs/TRANSFER_GUIDED_ADAPTIVE_OBSERVATION_ACQUISITION.md",
        "v072-transfer-guided-adaptive-observation-acquisition-spec-v4",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[1],
        "src/acfqp/transfer_guided_acquisition_preregistration_v1.py",
        "acfqp.v072_adaptive_acquisition_preregistration.v2",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[2],
        "src/acfqp/v072_verified_source_archive_component_v1.py",
        "v072-source-archive-builder-independent-verifier-component-v1",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[3],
        "src/acfqp/v072_portable_feature_consensus_authority_v1.py",
        "v072-portable-feature-consensus-authority-v1",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[4],
        "src/acfqp/v072_registered_target_selector_v1.py",
        "v072-registered-proof-frontier-selector-v1",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[5],
        "src/acfqp/heldout_graph_transition_observer_v2.py",
        "v072-heldout-observer-raw-replay-support-chain-v2",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[6],
        "src/acfqp/v072_registered_target_confidence_accumulator_v1.py",
        "v072-registered-target-confidence-accumulator-v1",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[7],
        (
            "src/acfqp/"
            "v072_registered_target_selector_independent_verifier_v1.py"
        ),
        "v072-independent-public-catalogue-cardinality-replay-v1",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[8],
        "src/acfqp/v072_registered_cold_h2_orchestrator_v1.py",
        "v072-registered-cold-h2-observation-model-orchestrator-v2",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[9],
        "src/acfqp/v072_registered_incremental_epoch_materializer_v1.py",
        "v072-registered-immutable-incremental-epoch-materializer-v1",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[10],
        "src/acfqp/v072_exact_lazy_planner_component_v1.py",
        "v072-exact-lazy-planner-independent-verifier-component-v1",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[11],
        "src/acfqp/v072_registered_matched_direct_runtime_v1.py",
        "v072-registered-matched-direct-ground-runtime-v2",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[12],
        "src/acfqp/v072_independent_exact_ground_evaluator_v1.py",
        "v072-independent-exact-ground-fixed-kappa-evaluator-v2",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[13],
        "src/acfqp/v072_registered_campaign_consumer_v1.py",
        "v072-registered-three-context-five-arm-executor-v3",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[14],
        "src/acfqp/v072_registered_campaign_attempt_journal_v1.py",
        "v072-fresh-only-durable-attempt-journal-v1",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[15],
        (
            "src/acfqp/"
            "v072_registered_complete_bundle_endpoint_verifier_v1.py"
        ),
        "v072-registered-complete-bundle-endpoint-verifier-v2",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[16],
        "src/acfqp/v072_registered_campaign_reconciliation_v1.py",
        "v072-registered-four-lane-campaign-reconciliation-v2",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[17],
        "specs/V072_CONFIRMATORY_TEST_COMMAND.json",
        "v072-confirmatory-test-command-manifest-v1",
    ),
    _role_spec(
        COMPONENT_ROLE_ORDER[18],
        "specs/V072_RUNTIME_DEPENDENCY_LOCK.json",
        "v072-runtime-dependency-interpreter-build-v1",
    ),
)

if tuple(item.component_role for item in COMPONENT_ROLE_SPECS) != (
    COMPONENT_ROLE_ORDER
):
    raise RuntimeError("V0-072 component role specifications are misordered")


def _root(value: str | os.PathLike[str]) -> Path:
    root = Path(value)
    if not root.is_dir() or root.is_symlink():
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "repository root must be an existing non-symlink directory"
        )
    return root.resolve(strict=True)


def _safe_component_file(root: Path, relative_path: str) -> Path:
    canonical = _safe_relative_path(relative_path)
    candidate = root.joinpath(*PurePosixPath(canonical).parts)
    cursor = root
    for part in PurePosixPath(canonical).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "component path contains a symlink"
            )
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as error:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "component path does not exist"
        ) from error
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "component path escapes repository root"
        ) from error
    if not resolved.is_file():
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "component path is not one regular file"
        )
    return resolved


def _read_regular_file_without_symlinks(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "component is not a regular file"
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "component changed while its bytes were read"
        )
    data = b"".join(chunks)
    if len(data) != after.st_size:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "component byte count disagrees with file metadata"
        )
    return data


@dataclass(frozen=True, slots=True)
class ComponentRecordV1:
    component_role: str
    repository_relative_path: str
    sha256_file_bytes: str
    file_byte_count: int
    schema_or_protocol_id: str
    content_id_or_typed_not_applicable: str | TypedNotApplicableV1

    def __post_init__(self) -> None:
        _token(self.component_role, "component record role")
        _safe_relative_path(self.repository_relative_path)
        _cid(self.sha256_file_bytes, "component file SHA-256")
        if type(self.file_byte_count) is not int or self.file_byte_count < 0:
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "component byte count is invalid"
            )
        _token(self.schema_or_protocol_id, "component schema/protocol ID")
        identity = self.content_id_or_typed_not_applicable
        if type(identity) is str:
            _cid(identity, "component applicable content ID")
        elif type(identity) is not TypedNotApplicableV1:
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "component content identity is null or untyped"
            )

    def _payload(self) -> dict[str, Any]:
        identity = self.content_id_or_typed_not_applicable
        return {
            "schema": "acfqp.v072_manifest_component_record.v1",
            "schema_version": SCHEMA_VERSION,
            "component_role": self.component_role,
            "repository_relative_path": self.repository_relative_path,
            "sha256_file_bytes": self.sha256_file_bytes,
            "file_byte_count": self.file_byte_count,
            "schema_or_protocol_id": self.schema_or_protocol_id,
            "content_id_or_typed_not_applicable": (
                {
                    "kind": "CONTENT_ID",
                    "content_id": identity,
                }
                if type(identity) is str
                else identity.to_document()
            ),
        }

    @property
    def record_id(self) -> str:
        return _content_id("component_record", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "record_id": self.record_id}


def derive_component_record_v1(
    repository_root: str | os.PathLike[str],
    role_spec: ComponentRoleSpecV1,
) -> ComponentRecordV1:
    """Derive a component record from actual bytes; no hash is accepted."""

    if type(role_spec) is not ComponentRoleSpecV1:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "component derivation requires a typed role specification"
        )
    if role_spec.repository_relative_path == DEVELOPMENT_SYNTHETIC_MODULE_PATH:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "development synthetic module cannot enter confirmatory manifest"
        )
    root = _root(repository_root)
    path = _safe_component_file(root, role_spec.repository_relative_path)
    data = _read_regular_file_without_symlinks(path)
    digest = hashlib.sha256(data).hexdigest()
    return ComponentRecordV1(
        role_spec.component_role,
        role_spec.repository_relative_path,
        digest,
        len(data),
        role_spec.schema_or_protocol_id,
        role_spec.content_identity,
    )


def verify_component_record_v1(
    repository_root: str | os.PathLike[str],
    role_spec: ComponentRoleSpecV1,
    claimed: ComponentRecordV1,
) -> ComponentRecordV1:
    expected = derive_component_record_v1(repository_root, role_spec)
    if (
        type(claimed) is not ComponentRecordV1
        or claimed.to_document() != expected.to_document()
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "component record differs from current repository bytes"
        )
    return expected


@dataclass(frozen=True, slots=True)
class ExecutionDependencyRecordV1:
    repository_relative_path: str
    sha256_file_bytes: str
    file_byte_count: int
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        _safe_relative_path(self.repository_relative_path)
        _cid(self.sha256_file_bytes, "dependency file SHA-256")
        if (
            type(self.file_byte_count) is not int
            or self.file_byte_count < 0
            or type(self.provenance) is not tuple
            or not self.provenance
            or self.provenance
            != tuple(sorted(set(self.provenance)))
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "execution dependency record is malformed"
            )
        for value in self.provenance:
            _token(value, "dependency provenance")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_execution_dependency_record.v1",
            "schema_version": SCHEMA_VERSION,
            "repository_relative_path": self.repository_relative_path,
            "sha256_file_bytes": self.sha256_file_bytes,
            "file_byte_count": self.file_byte_count,
            "provenance": list(self.provenance),
        }

    @property
    def record_id(self) -> str:
        return _content_id("dependency_record", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "record_id": self.record_id}


def _python_module_index(root: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    for top_level in ("src", "tests", "scripts"):
        base = root / top_level
        if not base.is_dir() or base.is_symlink():
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                f"local Python root is missing or linked: {top_level}"
            )
        for candidate in sorted(base.rglob("*.py")):
            relative = candidate.relative_to(root).as_posix()
            _safe_component_file(root, relative)
            parts = list(PurePosixPath(relative).with_suffix("").parts)
            if parts[0] == "src":
                parts = parts[1:]
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if not parts:
                continue
            module = ".".join(parts)
            existing = index.get(module)
            if existing is not None and existing != relative:
                raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                    f"local Python module aliases two files: {module}"
                )
            index[module] = relative
    return index


def _module_for_path(
    relative_path: str,
    module_index: Mapping[str, str],
) -> str | None:
    matches = [
        module
        for module, path in module_index.items()
        if path == relative_path
    ]
    if len(matches) > 1:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "one local Python file has multiple module identities"
        )
    return matches[0] if matches else None


def _package_initializer_paths(
    module: str,
    module_index: Mapping[str, str],
) -> tuple[str, ...]:
    parts = module.split(".")
    return tuple(
        module_index[prefix]
        for index in range(1, len(parts))
        if (
            (prefix := ".".join(parts[:index])) in module_index
            and PurePosixPath(module_index[prefix]).name == "__init__.py"
        )
    )


def _resolve_import_candidates(
    *,
    node: ast.Import | ast.ImportFrom,
    current_module: str,
    current_is_package: bool,
) -> tuple[tuple[str, bool], ...]:
    if type(node) is ast.Import:
        return tuple((alias.name, True) for alias in node.names)
    package_parts = current_module.split(".")
    if not current_is_package:
        package_parts = package_parts[:-1]
    if node.level:
        trim = node.level - 1
        if trim > len(package_parts):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "relative import escapes its local package"
            )
        package_parts = (
            package_parts[: len(package_parts) - trim]
            if trim
            else package_parts
        )
    elif node.module is not None:
        package_parts = []
    base_parts = [
        *package_parts,
        *([] if node.module is None else node.module.split(".")),
    ]
    base = ".".join(base_parts)
    candidates: list[tuple[str, bool]] = []
    if base:
        candidates.append((base, True))
    for alias in node.names:
        if alias.name == "*":
            continue
        candidates.append(
            (".".join((*base_parts, alias.name)), False)
        )
    return tuple(dict.fromkeys(candidates))


def _resolve_dynamic_import_literal(
    *,
    value: str,
    current_module: str,
    current_is_package: bool,
) -> str:
    if not value.startswith("."):
        return value
    level = len(value) - len(value.lstrip("."))
    suffix = value[level:]
    package_parts = current_module.split(".")
    if not current_is_package:
        package_parts = package_parts[:-1]
    trim = level - 1
    if trim > len(package_parts):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "relative dynamic import escapes its local package"
        )
    if trim:
        package_parts = package_parts[: len(package_parts) - trim]
    if suffix:
        package_parts.extend(suffix.split("."))
    return ".".join(package_parts)


def _local_imports(
    *,
    root: Path,
    relative_path: str,
    module_index: Mapping[str, str],
) -> tuple[str, ...]:
    module = _module_for_path(relative_path, module_index)
    if module is None:
        return ()
    current_is_package = (
        PurePosixPath(relative_path).name == "__init__.py"
    )
    data = _read_regular_file_without_symlinks(
        _safe_component_file(root, relative_path)
    )
    try:
        tree = ast.parse(
            data.decode("utf-8", errors="strict"),
            filename=relative_path,
        )
    except (UnicodeDecodeError, SyntaxError) as error:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            f"local import source is not valid UTF-8 Python: {relative_path}"
        ) from error
    candidates: list[tuple[str, bool]] = []
    for node in ast.walk(tree):
        if type(node) in (ast.Import, ast.ImportFrom):
            candidates.extend(
                _resolve_import_candidates(
                    node=node,
                    current_module=module,
                    current_is_package=current_is_package,
                )
            )
        elif (
            type(node) is ast.Call
            and node.args
            and type(node.args[0]) is ast.Constant
            and type(node.args[0].value) is str
            and (
                (
                    type(node.func) is ast.Name
                    and node.func.id in {"__import__", "import_module"}
                )
                or (
                    type(node.func) is ast.Attribute
                    and node.func.attr == "import_module"
                )
            )
        ):
            candidates.append(
                (
                    _resolve_dynamic_import_literal(
                        value=node.args[0].value,
                        current_module=module,
                        current_is_package=current_is_package,
                    ),
                    True,
                )
            )
    resolved: set[str] = set()
    for candidate, required_module in candidates:
        path = module_index.get(candidate)
        if path is not None:
            resolved.add(path)
            resolved.update(
                _package_initializer_paths(candidate, module_index)
            )
            continue
        root_name = candidate.split(".", 1)[0]
        if root_name in {"acfqp", "tests", "scripts"}:
            if candidate in {"acfqp", "tests", "scripts"}:
                continue
            # ``from package import symbol`` produces a speculative
            # package.symbol candidate.  It is an attribute, not a missing
            # module, when the base package/module itself resolves.
            base = candidate.rsplit(".", 1)[0]
            if not required_module and base in module_index:
                continue
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                f"unresolved local import {candidate} in {relative_path}"
            )
    return tuple(sorted(resolved))


def derive_execution_dependency_closure_v1(
    repository_root: str | os.PathLike[str],
    component_records: tuple[ComponentRecordV1, ...],
) -> tuple[ExecutionDependencyRecordV1, ...]:
    """Hash the complete local Python surface plus explicit import edges.

    Binding every ``src/**/*.py`` file is intentionally conservative.  It
    closes variable/capability-supplied dynamic imports that cannot be
    resolved soundly from AST alone.  Static and literal dynamic imports are
    still traversed to preserve exact provenance and reject missing modules.
    """

    root = _root(repository_root)
    if (
        type(component_records) is not tuple
        or any(type(item) is not ComponentRecordV1 for item in component_records)
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "dependency closure requires typed component records"
        )
    module_index = _python_module_index(root)
    role_paths = {
        record.repository_relative_path for record in component_records
    }
    provenance: dict[str, set[str]] = {}
    queue: list[str] = []

    def seed(path: str, reason: str) -> None:
        _safe_component_file(root, path)
        provenance.setdefault(path, set()).add(reason)
        if path not in queue:
            queue.append(path)

    for record in component_records:
        if record.repository_relative_path.endswith(".py"):
            seed(
                record.repository_relative_path,
                f"COMPONENT_ROLE:{record.component_role}",
            )
    seed(MANIFEST_AUTHORITY_PATH, "MANIFEST_AUTHORITY")
    for path in PRODUCTION_ENTRYPOINT_PATHS:
        seed(path, "REGISTERED_PRODUCTION_ENTRYPOINT")
    for path in execution_env.IMPLEMENTATION_PATHS:
        seed(path, "DECLARED_EXECUTION_ENVIRONMENT_IMPLEMENTATION")
    source_paths = sorted(
        candidate.relative_to(root).as_posix()
        for candidate in (root / "src").rglob("*.py")
    )
    if not source_paths:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "conservative local Python source closure is empty"
        )
    for path in source_paths:
        seed(path, "CONSERVATIVE_LOCAL_PYTHON_CLOSURE")
    test_paths = sorted(
        candidate.relative_to(root).as_posix()
        for candidate in (root / "tests").rglob("*.py")
    )
    if not test_paths:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "exact-command critical test closure is empty"
        )
    for path in test_paths:
        seed(path, "EXACT_TEST_COMMAND_CRITICAL_TEST")

    visited: set[str] = set()
    cursor = 0
    while cursor < len(queue):
        parent = queue[cursor]
        cursor += 1
        if parent in visited:
            continue
        visited.add(parent)
        parent_module = _module_for_path(parent, module_index)
        if parent_module is not None:
            for initializer in _package_initializer_paths(
                parent_module,
                module_index,
            ):
                provenance.setdefault(initializer, set()).add(
                    f"PACKAGE_INITIALIZER:{parent}"
                )
                if initializer not in visited and initializer not in queue:
                    queue.append(initializer)
        for dependency in _local_imports(
            root=root,
            relative_path=parent,
            module_index=module_index,
        ):
            provenance.setdefault(dependency, set()).add(
                f"LOCAL_IMPORT:{parent}"
            )
            if dependency not in visited and dependency not in queue:
                queue.append(dependency)

    records: list[ExecutionDependencyRecordV1] = []
    for path in sorted(set(visited) - role_paths):
        data = _read_regular_file_without_symlinks(
            _safe_component_file(root, path)
        )
        records.append(
            ExecutionDependencyRecordV1(
                path,
                hashlib.sha256(data).hexdigest(),
                len(data),
                tuple(sorted(provenance[path])),
            )
        )
    return tuple(records)


@dataclass(frozen=True, slots=True)
class FrozenComponentRegistrySnapshotV1:
    records: tuple[ComponentRecordV1, ...]
    execution_dependency_records: tuple[ExecutionDependencyRecordV1, ...]
    missing_roles: tuple[str, ...]
    excluded_development_module_path: str = (
        DEVELOPMENT_SYNTHETIC_MODULE_PATH
    )

    def __post_init__(self) -> None:
        if (
            type(self.records) is not tuple
            or any(type(item) is not ComponentRecordV1 for item in self.records)
            or type(self.execution_dependency_records) is not tuple
            or any(
                type(item) is not ExecutionDependencyRecordV1
                for item in self.execution_dependency_records
            )
            or type(self.missing_roles) is not tuple
            or self.excluded_development_module_path
            != DEVELOPMENT_SYNTHETIC_MODULE_PATH
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "component registry fields are malformed"
            )
        specs = {item.component_role: item for item in COMPONENT_ROLE_SPECS}
        record_roles = tuple(item.component_role for item in self.records)
        if (
            len(record_roles) != len(set(record_roles))
            or tuple(
                role for role in COMPONENT_ROLE_ORDER if role in record_roles
            )
            != record_roles
            or self.missing_roles
            != tuple(
                role
                for role in COMPONENT_ROLE_ORDER
                if role not in set(record_roles)
            )
            or set(record_roles) | set(self.missing_roles)
            != set(COMPONENT_ROLE_ORDER)
            or set(record_roles) & set(self.missing_roles)
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "component roles are reordered, missing, or duplicated"
            )
        for record in self.records:
            spec = specs.get(record.component_role)
            if (
                spec is None
                or record.repository_relative_path
                != spec.repository_relative_path
                or record.schema_or_protocol_id
                != spec.schema_or_protocol_id
                or record.content_id_or_typed_not_applicable
                != spec.content_identity
                or record.repository_relative_path
                == DEVELOPMENT_SYNTHETIC_MODULE_PATH
            ):
                raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                    "component record differs from its frozen role specification"
                )
        dependency_paths = tuple(
            item.repository_relative_path
            for item in self.execution_dependency_records
        )
        record_paths = {
            item.repository_relative_path for item in self.records
        }
        if (
            dependency_paths != tuple(sorted(set(dependency_paths)))
            or set(dependency_paths).intersection(record_paths)
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "execution dependency closure is reordered or duplicated"
            )

    @property
    def record_ids(self) -> tuple[str, ...]:
        return tuple(item.record_id for item in self.records)

    @property
    def component_tree_digest(self) -> str:
        return _content_id(
            "component_tree",
            {
                "schema": "acfqp.v072_manifest_component_tree.v1",
                "schema_version": SCHEMA_VERSION,
                "ordered_component_role_list": list(COMPONENT_ROLE_ORDER),
                "ordered_record_ids": list(self.record_ids),
                "ordered_execution_dependency_record_ids": [
                    item.record_id
                    for item in self.execution_dependency_records
                ],
                "missing_roles": list(self.missing_roles),
            },
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_manifest_component_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "ordered_component_role_list": list(COMPONENT_ROLE_ORDER),
            "record_ids": list(self.record_ids),
            "execution_dependency_record_ids": [
                item.record_id for item in self.execution_dependency_records
            ],
            "execution_dependency_count": len(
                self.execution_dependency_records
            ),
            "execution_dependency_closure_id": _content_id(
                "dependency_closure",
                {
                    "schema": (
                        "acfqp.v072_execution_dependency_closure.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "record_ids": [
                        item.record_id
                        for item in self.execution_dependency_records
                    ],
                },
            ),
            "missing_roles": list(self.missing_roles),
            "component_tree_digest": self.component_tree_digest,
            "excluded_development_module_path": (
                self.excluded_development_module_path
            ),
            "retired_ids_excluded": list(
                prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS
            ),
        }

    @property
    def registry_id(self) -> str:
        return _content_id("component_registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "records": [item.to_document() for item in self.records],
            "execution_dependency_records": [
                item.to_document()
                for item in self.execution_dependency_records
            ],
            "registry_id": self.registry_id,
        }


def freeze_internal_component_registry_v1(
    repository_root: str | os.PathLike[str],
) -> FrozenComponentRegistrySnapshotV1:
    """Freeze every currently present internally registered component."""

    root = _root(repository_root)
    records: list[ComponentRecordV1] = []
    missing: list[str] = []
    for role_spec in COMPONENT_ROLE_SPECS:
        candidate = root.joinpath(
            *PurePosixPath(role_spec.repository_relative_path).parts
        )
        if not candidate.exists() and not candidate.is_symlink():
            missing.append(role_spec.component_role)
            continue
        records.append(derive_component_record_v1(root, role_spec))
    record_tuple = tuple(records)
    return FrozenComponentRegistrySnapshotV1(
        record_tuple,
        derive_execution_dependency_closure_v1(root, record_tuple),
        tuple(missing),
    )


def verify_component_registry_snapshot_v1(
    repository_root: str | os.PathLike[str],
    claimed: FrozenComponentRegistrySnapshotV1,
) -> FrozenComponentRegistrySnapshotV1:
    expected = freeze_internal_component_registry_v1(repository_root)
    if (
        type(claimed) is not FrozenComponentRegistrySnapshotV1
        or claimed.to_document() != expected.to_document()
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "component registry differs from current repository tree"
        )
    return expected


def _profile_id(name: str, payload: Mapping[str, Any]) -> str:
    return _content_id(
        "profile",
        {
            "schema": "acfqp.v072_manifest_bound_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_name": name,
            "payload": dict(payload),
        },
    )


def _global_binding_document(
    registry: FrozenComponentRegistrySnapshotV1,
    execution_environment: (
        execution_env.V072ExecutionEnvironmentAuthoritiesV1 | None
    ) = None,
    source_reconstruction_recipe: (
        source_reconstruction_recipe_v1.SourceReconstructionRecipeV1
        | None
    ) = None,
    source_archive_component: (
        source_archive_component_v1.V072VerifiedSourceArchiveComponentV1
        | None
    ) = None,
) -> dict[str, Any]:
    contexts = prereg.registered_heldout_public_contexts_v2()
    environment = prereg.frozen_heldout_environment_manifest_v1()
    draft = prereg.freeze_transfer_guided_acquisition_preregistration_v1()
    confidence = draft.to_document()["confidence_allocation"]
    checkpoint_cap = {
        "initial": draft.to_document()["initial_acquisition_schedule"],
        "incremental": draft.to_document()[
            "incremental_acquisition_schedule"
        ],
        "adaptive_audit_checkpoints": list(
            prereg.ADAPTIVE_AUDIT_CHECKPOINTS
        ),
        "exact_lazy_resource_limits": dict(
            prereg.EXACT_LAZY_RESOURCE_LIMITS
        ),
    }
    if execution_environment is None:
        test_command_manifest_id: str | dict[str, str] = {
            "kind": "MISSING_APPLICABLE_ID",
            "reason": "VERIFIED_TEST_COMMAND_AUTHORITY_NOT_SUPPLIED",
        }
        runtime_dependency_lock_id: str | dict[str, str] = {
            "kind": "MISSING_APPLICABLE_ID",
            "reason": "VERIFIED_RUNTIME_LOCK_AUTHORITY_NOT_SUPPLIED",
        }
        interpreter_build_identity_id: str | dict[str, str] = {
            "kind": "MISSING_APPLICABLE_ID",
            "reason": "VERIFIED_INTERPRETER_AUTHORITY_NOT_SUPPLIED",
        }
    elif (
        type(execution_environment)
        is execution_env.V072ExecutionEnvironmentAuthoritiesV1
    ):
        test_command_manifest_id = (
            execution_environment.test_command_manifest
            .test_command_manifest_id
        )
        runtime_dependency_lock_id = (
            execution_environment.runtime_dependency_lock
            .runtime_dependency_lock_id
        )
        interpreter_build_identity_id = (
            execution_environment.interpreter_build_identity
            .interpreter_build_identity_id
        )
    else:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "execution-environment bindings lack exact typed authorities"
        )
    if source_reconstruction_recipe is None:
        source_reconstruction_recipe_id: str | dict[str, str] = {
            "kind": "MISSING_APPLICABLE_ID",
            "reason": (
                "CANONICAL_SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED"
            ),
        }
    elif (
        type(source_reconstruction_recipe)
        is source_reconstruction_recipe_v1.SourceReconstructionRecipeV1
    ):
        source_reconstruction_recipe_id = (
            source_reconstruction_recipe.recipe_id
        )
    else:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "source-recipe binding lacks the exact strictly loaded type"
        )
    if source_archive_component is None:
        source_archive_id: str | dict[str, str] = {
            "kind": "MISSING_APPLICABLE_ID",
            "reason": "VERIFIED_SOURCE_ARCHIVE_NOT_YET_FROZEN_IN_MANIFEST",
        }
        source_archive_attestation_id: str | dict[str, str] = {
            "kind": "MISSING_APPLICABLE_ID",
            "reason": (
                "SOURCE_ARCHIVE_INDEPENDENT_ATTESTATION_NOT_YET_FROZEN"
            ),
        }
    elif (
        type(source_archive_component)
        is source_archive_component_v1.V072VerifiedSourceArchiveComponentV1
    ):
        source_archive_id = source_archive_component.archive.archive_id
        source_archive_attestation_id = (
            source_archive_component.independent_attestation.verification_id
        )
    else:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "source bindings lack the exact replayed component type"
        )
    return {
        "confirmatory_family_generation": (
            prereg.CONFIRMATORY_FAMILY_GENERATION
        ),
        "context_ids": [item.context_id for item in contexts],
        "law_ids": [item.law_id for item in environment.laws],
        "environment_manifest_id": environment.manifest_id,
        "source_reconstruction_recipe_repository_path": (
            SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
        ),
        "source_reconstruction_recipe_id": (
            source_reconstruction_recipe_id
        ),
        "source_archive_id": source_archive_id,
        "source_archive_verification_profile": (
            "verified_source_acquisition_archive_independent_verifier_v2"
        ),
        "source_archive_verification_attestation_id": (
            source_archive_attestation_id
        ),
        "arm_order": list(prereg.ARM_ORDER),
        "terminal_codes": list(prereg.TERMINAL_CODES),
        "confidence_profile_id": _profile_id(
            "V072_CONFIRMATORY_CONFIDENCE",
            confidence,
        ),
        "checkpoint_cap_profile_id": _profile_id(
            "V072_CONFIRMATORY_CHECKPOINT_CAPS",
            checkpoint_cap,
        ),
        "repository_url": REPOSITORY_URL,
        "target_branch": TARGET_BRANCH,
        "component_tree_digest": registry.component_tree_digest,
        "exact_test_command": list(EXACT_TEST_COMMAND),
        "deterministic_environment_settings": [
            {"name": name, "value": value}
            for name, value in DETERMINISTIC_ENVIRONMENT_SETTINGS
        ],
        "test_command_manifest_id": test_command_manifest_id,
        "runtime_dependency_lock_id": runtime_dependency_lock_id,
        "interpreter_build_identity_id": interpreter_build_identity_id,
        "retired_development_ids_excluded": list(
            prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS
        ),
        "development_synthetic_module_excluded": (
            DEVELOPMENT_SYNTHETIC_MODULE_PATH
        ),
        "final_preregistration_id_embedded": False,
        "future_binding_direction": (
            "FINAL_PREREGISTRATION_BINDS_MANIFEST_ID_ONE_WAY"
        ),
    }


_MISSING_GLOBAL_BINDINGS = (
    "source_reconstruction_recipe_id",
    "source_archive_id",
    "source_archive_verification_attestation_id",
)

_EXECUTION_ENVIRONMENT_BINDINGS = (
    "test_command_manifest_id",
    "runtime_dependency_lock_id",
    "interpreter_build_identity_id",
)

_REQUIRED_GLOBAL_BINDING_KEYS = frozenset(
    {
        "confirmatory_family_generation",
        "context_ids",
        "law_ids",
        "environment_manifest_id",
        "source_reconstruction_recipe_repository_path",
        "source_reconstruction_recipe_id",
        "source_archive_id",
        "source_archive_verification_profile",
        "source_archive_verification_attestation_id",
        "arm_order",
        "terminal_codes",
        "confidence_profile_id",
        "checkpoint_cap_profile_id",
        "repository_url",
        "target_branch",
        "component_tree_digest",
        "exact_test_command",
        "deterministic_environment_settings",
        "test_command_manifest_id",
        "runtime_dependency_lock_id",
        "interpreter_build_identity_id",
        "retired_development_ids_excluded",
        "development_synthetic_module_excluded",
        "final_preregistration_id_embedded",
        "future_binding_direction",
    }
)


@dataclass(frozen=True, slots=True)
class ConfirmatoryExecutionManifestReadinessV1:
    component_registry: FrozenComponentRegistrySnapshotV1
    global_bindings: Mapping[str, Any]
    _execution_environment: (
        execution_env.V072ExecutionEnvironmentAuthoritiesV1
    ) = field(repr=False)
    _execution_environment_attestation: (
        execution_env_independent
        .IndependentExecutionEnvironmentAttestationV1
    ) = field(repr=False)
    _source_archive_component: (
        source_archive_component_v1.V072VerifiedSourceArchiveComponentV1
        | None
    ) = field(repr=False)
    _source_reconstruction_recipe: (
        source_reconstruction_recipe_v1.SourceReconstructionRecipeV1
        | None
    ) = field(repr=False)
    _source_reconstruction_replay: (
        source_reconstruction_recipe_v1.SourceReconstructionReplayV1
        | None
    ) = field(repr=False)
    _source_recipe_blockers: tuple[str, ...] = field(repr=False)
    missing_component_roles: tuple[str, ...]
    missing_applicable_bindings: tuple[str, ...]
    finalization_blockers: tuple[str, ...]
    status: str = READINESS_STATUS
    target_execution_allowed: bool = False
    anchor_id: None = None

    def __post_init__(self) -> None:
        if (
            type(self.component_registry)
            is not FrozenComponentRegistrySnapshotV1
            or type(self.global_bindings) is not dict
            or type(self._execution_environment)
            is not execution_env.V072ExecutionEnvironmentAuthoritiesV1
            or type(self._execution_environment_attestation)
            is not (
                execution_env_independent
                .IndependentExecutionEnvironmentAttestationV1
            )
            or (
                self._source_archive_component is not None
                and type(self._source_archive_component)
                is not (
                    source_archive_component_v1
                    .V072VerifiedSourceArchiveComponentV1
                )
            )
            or (
                self._source_reconstruction_recipe is not None
                and type(self._source_reconstruction_recipe)
                is not (
                    source_reconstruction_recipe_v1
                    .SourceReconstructionRecipeV1
                )
            )
            or (
                self._source_reconstruction_replay is not None
                and type(self._source_reconstruction_replay)
                is not (
                    source_reconstruction_recipe_v1
                    .SourceReconstructionReplayV1
                )
            )
            or type(self._source_recipe_blockers) is not tuple
            or any(
                type(item) is not str or not item
                for item in self._source_recipe_blockers
            )
            or self.missing_component_roles
            != self.component_registry.missing_roles
            or self.missing_applicable_bindings
            != tuple(
                name
                for name in _MISSING_GLOBAL_BINDINGS
                if type(self.global_bindings.get(name)) is not str
            )
            or type(self.finalization_blockers) is not tuple
            or self.status != READINESS_STATUS
            or self.target_execution_allowed is not False
            or self.anchor_id is not None
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "manifest readiness is malformed or authorizing"
            )
        expected_blockers = tuple(
            [
                *(
                    f"MISSING_COMPONENT_ROLE:{role}"
                    for role in self.component_registry.missing_roles
                ),
                *(
                    f"MISSING_APPLICABLE_BINDING:{name}"
                    for name in self.missing_applicable_bindings
                ),
                *self._source_recipe_blockers,
                *(
                    (
                        "FINALIZATION_DISABLED_"
                        "NONAUTHORIZING_READINESS_ONLY",
                    )
                    if FINALIZATION_ENABLED is not True
                    else ()
                ),
            ]
        )
        if self.finalization_blockers != expected_blockers:
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "manifest readiness blockers do not match its exact "
                "prerequisites"
            )
        if set(self.global_bindings) != _REQUIRED_GLOBAL_BINDING_KEYS:
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "readiness global-binding schema changed"
            )
        if self.global_bindings != _global_binding_document(
            self.component_registry,
            self._execution_environment,
            self._source_reconstruction_recipe,
            self._source_archive_component,
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "readiness global bindings differ from frozen authorities"
            )
        if (
            self._execution_environment_attestation
            .test_command_manifest_id
            != self.global_bindings["test_command_manifest_id"]
            or self._execution_environment_attestation
            .runtime_dependency_lock_id
            != self.global_bindings["runtime_dependency_lock_id"]
            or self._execution_environment_attestation
            .interpreter_build_identity_id
            != self.global_bindings["interpreter_build_identity_id"]
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "independent environment replay does not bind readiness IDs"
            )
        for field in (
            "context_ids",
            "law_ids",
        ):
            values = self.global_bindings[field]
            if (
                type(values) is not list
                or not values
                or any(type(item) is not str for item in values)
            ):
                raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                    f"{field} contains a null applicable ID"
                )
            for item in values:
                _cid(item, field)
        for field in (
            "environment_manifest_id",
            "confidence_profile_id",
            "checkpoint_cap_profile_id",
            "component_tree_digest",
            *_EXECUTION_ENVIRONMENT_BINDINGS,
        ):
            _cid(self.global_bindings[field], field)
        if self._source_archive_component is not None:
            for field in (
                "source_archive_id",
                "source_archive_verification_attestation_id",
            ):
                _cid(self.global_bindings[field], field)
            if (
                self.global_bindings["source_archive_id"]
                != self._source_archive_component.archive.archive_id
                or self.global_bindings[
                    "source_archive_verification_attestation_id"
                ]
                != (
                    self._source_archive_component
                    .independent_attestation.verification_id
                )
            ):
                raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                    "source readiness IDs differ from independently "
                    "replayed archive evidence"
                )
        if self._source_reconstruction_recipe is not None:
            _cid(
                self.global_bindings["source_reconstruction_recipe_id"],
                "source reconstruction recipe",
            )
            if (
                self.global_bindings["source_reconstruction_recipe_id"]
                != self._source_reconstruction_recipe.recipe_id
            ):
                raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                    "source recipe ID differs from the strictly loaded recipe"
                )
        if self._source_reconstruction_replay is not None:
            replay = self._source_reconstruction_replay
            component = self._source_archive_component
            if (
                self._source_reconstruction_recipe is None
                or component is None
                or not self._source_reconstruction_recipe.replay_ready
                or replay.recipe_id
                != self._source_reconstruction_recipe.recipe_id
                or replay.component != component
                or replay.archive != component.archive
                or replay.production_verification
                != component.production_verification
                or replay.independent_attestation
                != component.independent_attestation
            ):
                raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                    "source recipe replay does not close the production, "
                    "independent, and typed-component identity graph"
                )
        if (
            self.global_bindings["confirmatory_family_generation"]
            != prereg.CONFIRMATORY_FAMILY_GENERATION
            or tuple(self.global_bindings["arm_order"])
            != prereg.ARM_ORDER
            or tuple(self.global_bindings["terminal_codes"])
            != prereg.TERMINAL_CODES
            or self.global_bindings["repository_url"] != REPOSITORY_URL
            or self.global_bindings["target_branch"] != TARGET_BRANCH
            or self.global_bindings[
                "source_reconstruction_recipe_repository_path"
            ]
            != SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
            or self.global_bindings["component_tree_digest"]
            != self.component_registry.component_tree_digest
            or self.global_bindings[
                "retired_development_ids_excluded"
            ]
            != list(prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS)
            or self.global_bindings[
                "development_synthetic_module_excluded"
            ]
            != DEVELOPMENT_SYNTHETIC_MODULE_PATH
            or self.global_bindings[
                "final_preregistration_id_embedded"
            ]
            is not False
            or self.global_bindings["future_binding_direction"]
            != "FINAL_PREREGISTRATION_BINDS_MANIFEST_ID_ONE_WAY"
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "readiness global profile differs from preregistration"
            )
        for field in self.missing_applicable_bindings:
            value = self.global_bindings[field]
            if (
                type(value) is not dict
                or value.get("kind") != "MISSING_APPLICABLE_ID"
                or type(value.get("reason")) is not str
                or not value["reason"]
            ):
                raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                    "missing applicable identity is null or untyped"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_confirmatory_execution_manifest_readiness.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "status": READINESS_STATUS,
            "component_registry_id": self.component_registry.registry_id,
            "global_bindings": dict(self.global_bindings),
            "missing_component_roles": list(
                self.missing_component_roles
            ),
            "missing_applicable_bindings": list(
                self.missing_applicable_bindings
            ),
            "finalization_blockers": list(self.finalization_blockers),
            "final_manifest_id": None,
            "anchor_id": None,
            "target_execution_allowed": False,
            "registered_observations_generated": 0,
        }

    @property
    def readiness_id(self) -> str:
        return _content_id("readiness", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "component_registry": self.component_registry.to_document(),
            "readiness_id": self.readiness_id,
        }


def _freeze_source_archive_component_from_campaign_v1(
    *,
    source_campaign: source_campaign_v1.ObservationSupportCampaignV1,
    source_verification: (
        source_campaign_v1.ObservationSupportCampaignVerificationV1
    ),
) -> source_archive_component_v1.V072VerifiedSourceArchiveComponentV1:
    """Run both archive verifiers; no archive, component, or ID is accepted."""

    if (
        type(source_campaign)
        is not source_campaign_v1.ObservationSupportCampaignV1
        or type(source_verification)
        is not source_campaign_v1.ObservationSupportCampaignVerificationV1
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "source readiness requires exact campaign and verification types"
        )
    try:
        archive = (
            source_archive_v2
            .freeze_verified_source_acquisition_archive_v2(
                source_campaign=source_campaign,
                source_verification=source_verification,
            )
        )
        production_verification = (
            source_archive_v2.verify_verified_source_acquisition_archive_v2(
                source_campaign=source_campaign,
                source_verification=source_verification,
                claimed=archive,
            )
        )
        independent_attestation = (
            source_archive_independent_v2
            .verify_source_acquisition_archive_independently_v2(
                source_campaign=source_campaign,
                source_verification=source_verification,
                claimed=archive,
            )
        )
        return (
            source_archive_component_v1
            .bind_v072_verified_source_archive_component_v1(
                archive=archive,
                production_verification=production_verification,
                independent_attestation=independent_attestation,
            )
        )
    except (
        source_archive_v2
        .VerifiedSourceAcquisitionArchiveInvariantViolation,
        source_archive_independent_v2
        .IndependentSourceArchiveVerificationViolation,
        source_archive_component_v1
        .V072VerifiedSourceArchiveComponentInvariantViolation,
    ) as error:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "source archive dual replay or typed binding failed"
        ) from error


def _inspect_confirmatory_execution_manifest_readiness_v1(
    repository_root: str | os.PathLike[str],
    *,
    source_reconstruction_recipe: (
        source_reconstruction_recipe_v1.SourceReconstructionRecipeV1
        | None
    ),
    source_reconstruction_replay: (
        source_reconstruction_recipe_v1.SourceReconstructionReplayV1
        | None
    ),
    source_archive_component: (
        source_archive_component_v1.V072VerifiedSourceArchiveComponentV1
        | None
    ),
    source_recipe_blockers: tuple[str, ...],
) -> ConfirmatoryExecutionManifestReadinessV1:
    root = _root(repository_root)
    if (
        type(source_recipe_blockers) is not tuple
        or any(
            type(item) is not str or not item
            for item in source_recipe_blockers
        )
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "source recipe blockers are malformed"
        )
    registry = freeze_internal_component_registry_v1(root)
    execution_environment = (
        execution_env.freeze_v072_execution_environment_authorities_v1(
            root
        )
    )
    execution_environment_attestation = (
        execution_env_independent
        .verify_execution_environment_authorities_independently_v1(
            root,
            execution_environment,
        )
    )
    bindings = _global_binding_document(
        registry,
        execution_environment,
        source_reconstruction_recipe,
        source_archive_component,
    )
    missing_bindings = tuple(
        name
        for name in _MISSING_GLOBAL_BINDINGS
        if type(bindings[name]) is not str
    )
    blockers = tuple(
        [
            *(
                f"MISSING_COMPONENT_ROLE:{role}"
                for role in registry.missing_roles
            ),
            *(
                f"MISSING_APPLICABLE_BINDING:{name}"
                for name in missing_bindings
            ),
            *source_recipe_blockers,
            *(
                (
                    "FINALIZATION_DISABLED_"
                    "NONAUTHORIZING_READINESS_ONLY",
                )
                if FINALIZATION_ENABLED is not True
                else ()
            ),
        ]
    )
    return ConfirmatoryExecutionManifestReadinessV1(
        component_registry=registry,
        global_bindings=bindings,
        _execution_environment=execution_environment,
        _execution_environment_attestation=(
            execution_environment_attestation
        ),
        _source_archive_component=source_archive_component,
        _source_reconstruction_recipe=source_reconstruction_recipe,
        _source_reconstruction_replay=source_reconstruction_replay,
        _source_recipe_blockers=source_recipe_blockers,
        missing_component_roles=registry.missing_roles,
        missing_applicable_bindings=missing_bindings,
        finalization_blockers=blockers,
    )


def inspect_confirmatory_execution_manifest_readiness_v1(
    repository_root: str | os.PathLike[str],
) -> ConfirmatoryExecutionManifestReadinessV1:
    """Inspect without source objects and report typed missing bindings."""

    return _inspect_confirmatory_execution_manifest_readiness_v1(
        repository_root,
        source_reconstruction_recipe=None,
        source_reconstruction_replay=None,
        source_archive_component=None,
        source_recipe_blockers=(
            SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED_BLOCKER,
        ),
    )


def inspect_confirmatory_execution_manifest_readiness_with_source_v1(
    repository_root: str | os.PathLike[str],
    *,
    source_campaign: source_campaign_v1.ObservationSupportCampaignV1,
    source_verification: (
        source_campaign_v1.ObservationSupportCampaignVerificationV1
    ),
) -> ConfirmatoryExecutionManifestReadinessV1:
    """Recompute source archive proofs before populating both source IDs."""

    component = _freeze_source_archive_component_from_campaign_v1(
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    return _inspect_confirmatory_execution_manifest_readiness_v1(
        repository_root,
        source_reconstruction_recipe=None,
        source_reconstruction_replay=None,
        source_archive_component=component,
        source_recipe_blockers=(
            SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED_BLOCKER,
        ),
    )


def inspect_confirmatory_execution_manifest_readiness_with_source_recipe_v1(
    repository_root: str | os.PathLike[str],
) -> ConfirmatoryExecutionManifestReadinessV1:
    """Strictly load and replay the compact production source recipe.

    The recipe is read only from the frozen repository-relative path.
    Expected identities, runners, paths, campaign objects, archive objects,
    and attestations cannot be supplied by the caller.
    """

    root = _root(repository_root)
    source_recipe_path = _fixed_source_recipe_path_v1(root)
    ignored, tracked = _source_recipe_git_status_v1(root)
    if ignored:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "fixed source reconstruction recipe path is ignored"
        )
    if not source_recipe_path.exists():
        return _inspect_confirmatory_execution_manifest_readiness_v1(
            root,
            source_reconstruction_recipe=None,
            source_reconstruction_replay=None,
            source_archive_component=None,
            source_recipe_blockers=(
                SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED_BLOCKER,
            ),
        )
    try:
        recipe = (
            source_reconstruction_recipe_v1
            .load_source_reconstruction_recipe_v1(source_recipe_path)
        )
    except (
        source_reconstruction_recipe_v1
        .V072SourceReconstructionRecipeInvariantViolation
    ) as error:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "source reconstruction recipe is not strict canonical evidence"
        ) from error
    if not recipe.replay_ready:
        return _inspect_confirmatory_execution_manifest_readiness_v1(
            root,
            source_reconstruction_recipe=recipe,
            source_reconstruction_replay=None,
            source_archive_component=None,
            source_recipe_blockers=(
                source_reconstruction_recipe_v1.INCOMPLETE_BLOCKER,
                *(
                    (SOURCE_RECONSTRUCTION_RECIPE_NOT_TRACKED_BLOCKER,)
                    if not tracked
                    else ()
                ),
            ),
        )
    try:
        replay = (
            source_reconstruction_recipe_v1
            .replay_source_reconstruction_recipe_v1(
                root,
                recipe,
            )
        )
    except (
        source_reconstruction_recipe_v1
        .V072SourceReconstructionRecipeInvariantViolation
    ):
        return _inspect_confirmatory_execution_manifest_readiness_v1(
            root,
            source_reconstruction_recipe=recipe,
            source_reconstruction_replay=None,
            source_archive_component=None,
            source_recipe_blockers=(
                SOURCE_RECONSTRUCTION_RECIPE_REPLAY_FAILED_BLOCKER,
                *(
                    (SOURCE_RECONSTRUCTION_RECIPE_NOT_TRACKED_BLOCKER,)
                    if not tracked
                    else ()
                ),
            ),
        )
    return _inspect_confirmatory_execution_manifest_readiness_v1(
        root,
        source_reconstruction_recipe=recipe,
        source_reconstruction_replay=replay,
        source_archive_component=replay.component,
        source_recipe_blockers=(
            (SOURCE_RECONSTRUCTION_RECIPE_NOT_TRACKED_BLOCKER,)
            if not tracked
            else ()
        ),
    )


def verify_confirmatory_execution_manifest_readiness_v1(
    repository_root: str | os.PathLike[str],
    claimed: ConfirmatoryExecutionManifestReadinessV1,
) -> ConfirmatoryExecutionManifestReadinessV1:
    expected = inspect_confirmatory_execution_manifest_readiness_v1(
        repository_root
    )
    if (
        type(claimed) is not ConfirmatoryExecutionManifestReadinessV1
        or claimed != expected
        or claimed.to_document() != expected.to_document()
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "manifest readiness differs from current authorities or tree"
        )
    return expected


def verify_confirmatory_execution_manifest_readiness_with_source_v1(
    repository_root: str | os.PathLike[str],
    *,
    source_campaign: source_campaign_v1.ObservationSupportCampaignV1,
    source_verification: (
        source_campaign_v1.ObservationSupportCampaignVerificationV1
    ),
    claimed: ConfirmatoryExecutionManifestReadinessV1,
) -> ConfirmatoryExecutionManifestReadinessV1:
    expected = (
        inspect_confirmatory_execution_manifest_readiness_with_source_v1(
            repository_root,
            source_campaign=source_campaign,
            source_verification=source_verification,
        )
    )
    if (
        type(claimed) is not ConfirmatoryExecutionManifestReadinessV1
        or claimed != expected
        or claimed.to_document() != expected.to_document()
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "source-complete readiness differs from fresh dual replay"
        )
    return expected


def verify_confirmatory_execution_manifest_readiness_with_source_recipe_v1(
    repository_root: str | os.PathLike[str],
    *,
    claimed: ConfirmatoryExecutionManifestReadinessV1,
) -> ConfirmatoryExecutionManifestReadinessV1:
    expected = (
        inspect_confirmatory_execution_manifest_readiness_with_source_recipe_v1(
            repository_root,
        )
    )
    if (
        type(claimed) is not ConfirmatoryExecutionManifestReadinessV1
        or claimed != expected
        or claimed.to_document() != expected.to_document()
    ):
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "recipe-backed readiness differs from strict load and real replay"
        )
    return expected


@dataclass(frozen=True, slots=True)
class ConfirmatoryExecutionManifestV1:
    """Strict one-way manifest minted only from complete typed readiness."""

    _finalization_capability: object
    _readiness: ConfirmatoryExecutionManifestReadinessV1

    def __post_init__(self) -> None:
        readiness = self._readiness
        bindings_are_complete = (
            type(readiness) is ConfirmatoryExecutionManifestReadinessV1
            and type(readiness.global_bindings) is dict
            and set(readiness.global_bindings)
            == _REQUIRED_GLOBAL_BINDING_KEYS
            and all(
                type(readiness.global_bindings.get(name)) is str
                for name in (
                    *_MISSING_GLOBAL_BINDINGS,
                    *_EXECUTION_ENVIRONMENT_BINDINGS,
                )
            )
        )
        if (
            self._finalization_capability is not _FINALIZATION_SENTINEL
            or FINALIZATION_ENABLED is not True
            or type(readiness)
            is not ConfirmatoryExecutionManifestReadinessV1
            or readiness.finalization_blockers
            or readiness.missing_component_roles
            or readiness.missing_applicable_bindings
            or readiness._source_reconstruction_recipe is None
            or readiness._source_reconstruction_replay is None
            or readiness._source_archive_component is None
            or not readiness._source_reconstruction_recipe.replay_ready
            or not bindings_are_complete
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "final manifest lacks an internally minted complete typed "
                "readiness capability"
            )
        expected = _global_binding_document(
            readiness.component_registry,
            readiness._execution_environment,
            readiness._source_reconstruction_recipe,
            readiness._source_archive_component,
        )
        if readiness.global_bindings != expected:
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "final manifest differs from frozen global authorities"
            )
        for name in (
            *_MISSING_GLOBAL_BINDINGS,
            *_EXECUTION_ENVIRONMENT_BINDINGS,
        ):
            _cid(readiness.global_bindings[name], name)
        if (
            "final_preregistration_id" in readiness.global_bindings
            or "preregistration_id" in readiness.global_bindings
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "execution manifest must not embed the future preregistration ID"
            )

    @property
    def component_registry(self) -> FrozenComponentRegistrySnapshotV1:
        return self._readiness.component_registry

    @property
    def global_bindings(self) -> Mapping[str, Any]:
        return self._readiness.global_bindings

    @property
    def source_reconstruction_replay(
        self,
    ) -> source_reconstruction_recipe_v1.SourceReconstructionReplayV1:
        """Expose the one replay already paid by finalization."""

        replay = self._readiness._source_reconstruction_replay
        if (
            type(replay)
            is not source_reconstruction_recipe_v1.SourceReconstructionReplayV1
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "final manifest lost its typed source reconstruction replay"
            )
        return replay

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_confirmatory_execution_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "component_registry_id": self.component_registry.registry_id,
            "global_bindings": dict(self.global_bindings),
            "final_preregistration_id_embedded": False,
        }

    @property
    def manifest_id(self) -> str:
        return _content_id("final_manifest", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}


_FINALIZATION_SENTINEL = object()


def finalize_confirmatory_execution_manifest_v1(
    repository_root: str | os.PathLike[str],
) -> ConfirmatoryExecutionManifestV1:
    """Mint from the fixed recipe path; accepts no IDs, status, or source."""

    readiness = (
        inspect_confirmatory_execution_manifest_readiness_with_source_recipe_v1(
            repository_root,
        )
    )
    if readiness.finalization_blockers:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "confirmatory manifest prerequisites are incomplete; blockers="
            + ",".join(readiness.finalization_blockers)
        )
    verify_component_registry_snapshot_v1(
        repository_root,
        readiness.component_registry,
    )
    return ConfirmatoryExecutionManifestV1(
        _FINALIZATION_SENTINEL,
        readiness,
    )


def _artifact_path_v1(
    root: Path,
    repository_relative_path: str,
) -> Path:
    relative = _safe_relative_path(repository_relative_path)
    cursor = root
    for part in PurePosixPath(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "final artifact path contains a symlink"
            )
    parent = cursor.parent
    if not parent.is_dir() or parent.is_symlink():
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "final artifact parent is absent, linked, or not a directory"
        )
    return cursor


def _write_canonical_artifact_v1(
    root: Path,
    repository_relative_path: str,
    document: Mapping[str, Any],
) -> Path:
    path = _artifact_path_v1(root, repository_relative_path)
    data = canonical_json_bytes(dict(document))
    if path.exists():
        if (
            not path.is_file()
            or path.is_symlink()
            or _read_regular_file_without_symlinks(path) != data
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "existing final artifact differs from internally minted bytes"
            )
        return path
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o644)
    except FileExistsError:
        if (
            path.is_symlink()
            or not path.is_file()
            or _read_regular_file_without_symlinks(path) != data
        ):
            raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
                "racing final artifact differs from minted bytes"
            )
        return path
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("zero-byte final artifact write")
            view = view[written:]
        os.fsync(descriptor)
    except OSError as error:
        raise V072ConfirmatoryExecutionManifestV1InvariantViolation(
            "final artifact write did not complete"
        ) from error
    finally:
        os.close(descriptor)
    return path


def write_confirmatory_execution_manifest_v1(
    repository_root: str | os.PathLike[str],
) -> ConfirmatoryExecutionManifestV1:
    """Mint and idempotently write only the fixed final-manifest path."""

    root = _root(repository_root)
    manifest = finalize_confirmatory_execution_manifest_v1(root)
    _write_canonical_artifact_v1(
        root,
        FINAL_MANIFEST_REPOSITORY_PATH,
        manifest.to_document(),
    )
    return manifest


__all__ = [
    "COMPONENT_ROLE_ORDER",
    "COMPONENT_ROLE_SPECS",
    "ComponentRecordV1",
    "ComponentRoleSpecV1",
    "ConfirmatoryExecutionManifestReadinessV1",
    "ConfirmatoryExecutionManifestV1",
    "DETERMINISTIC_ENVIRONMENT_SETTINGS",
    "DEVELOPMENT_SYNTHETIC_MODULE_PATH",
    "EXACT_TEST_COMMAND",
    "ExecutionDependencyRecordV1",
    "FINALIZATION_ENABLED",
    "FINAL_MANIFEST_REPOSITORY_PATH",
    "FrozenComponentRegistrySnapshotV1",
    "MANIFEST_AUTHORITY_PATH",
    "PROFILE_KEY",
    "PRODUCTION_ENTRYPOINT_PATHS",
    "READINESS_STATUS",
    "REPOSITORY_URL",
    "SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED_BLOCKER",
    "SOURCE_RECONSTRUCTION_RECIPE_NOT_TRACKED_BLOCKER",
    "SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH",
    "SOURCE_RECONSTRUCTION_RECIPE_REPLAY_FAILED_BLOCKER",
    "TARGET_BRANCH",
    "TARGET_EXECUTION_ALLOWED",
    "TYPED_NOT_APPLICABLE",
    "TypedNotApplicableV1",
    "V072ConfirmatoryExecutionManifestV1InvariantViolation",
    "derive_component_record_v1",
    "derive_execution_dependency_closure_v1",
    "finalize_confirmatory_execution_manifest_v1",
    "freeze_internal_component_registry_v1",
    "inspect_confirmatory_execution_manifest_readiness_v1",
    "inspect_confirmatory_execution_manifest_readiness_with_source_recipe_v1",
    "inspect_confirmatory_execution_manifest_readiness_with_source_v1",
    "verify_component_record_v1",
    "verify_component_registry_snapshot_v1",
    "verify_confirmatory_execution_manifest_readiness_v1",
    "verify_confirmatory_execution_manifest_readiness_with_source_recipe_v1",
    "verify_confirmatory_execution_manifest_readiness_with_source_v1",
    "write_confirmatory_execution_manifest_v1",
]
