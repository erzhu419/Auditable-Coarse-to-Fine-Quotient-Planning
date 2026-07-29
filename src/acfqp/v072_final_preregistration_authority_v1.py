"""Fail-closed V0-072 final-preregistration and anchor authority.

Production source persistence is a compact deterministic reconstruction
recipe, not the historical full-object snapshot.  Before finalization this
authority requires the manifest authority to strictly load that recipe,
reconstruct the real source graph, and close the production, independent, and
typed-component identity graph.  It then writes the one-way manifest and
final preregistration.  Only an independently verified production-scope
origin/main claim can mint the executable anchor.

    source recipe -> final manifest -> final preregistration
                  -> remote-main anchor

The execution manifest never contains the final preregistration ID.  A strict
logical verifier is provided so that this dependency can be tested now without
creating a fake executable anchor or opening a registered target tape.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_confirmatory_execution_manifest_v1 as manifest_v1
from acfqp import v072_source_reconstruction_recipe_v1 as recipe_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_final_preregistration_remote_main_anchor_v1"

FINAL_PREREGISTRATION_ENABLED = True
REMOTE_MAIN_ANCHOR_AUTHORITY_ENABLED = True
TARGET_EXECUTION_ALLOWED = True

FINAL_MANIFEST_SCHEMA = "acfqp.v072_confirmatory_execution_manifest.v1"
FINAL_PREREGISTRATION_SCHEMA = (
    "acfqp.v072_adaptive_acquisition_preregistration.v2"
)
FINAL_MANIFEST_DOMAIN = (
    "acfqp:v072-confirmatory-execution-manifest:v1"
)
FINAL_PREREGISTRATION_DOMAIN = (
    "acfqp:v072-adaptive-acquisition-preregistration:v2"
)
FINAL_PREREGISTRATION_ATTESTATION_DOMAIN = (
    "acfqp:v072-final-preregistration-logical-attestation:v1"
)
FINAL_PREREGISTRATION_READINESS_DOMAIN = (
    "acfqp:v072-final-preregistration-readiness:v1"
)
REMOTE_MAIN_ANCHOR_CLAIM_DOMAIN = (
    "acfqp:v072-remote-main-anchor-claim:v1"
)
REMOTE_MAIN_ANCHOR_DOMAIN = "acfqp:v072-remote-main-anchor:v1"

FINAL_MANIFEST_REPOSITORY_PATH = (
    manifest_v1.FINAL_MANIFEST_REPOSITORY_PATH
)
FINAL_PREREGISTRATION_REPOSITORY_PATH = (
    "specs/V072_FINAL_PREREGISTRATION.json"
)
SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH = (
    manifest_v1.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
)

_REQUIRED_MANIFEST_GLOBAL_BINDINGS = frozenset(
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


class V072FinalPreregistrationInvariantViolation(ValueError):
    """A final-preregistration or anchor schema invariant failed."""


class V072FinalPreregistrationLockedV1(RuntimeError):
    """The required source/manifest/push authority chain is incomplete."""


class RemoteMainAnchorVerificationScopeV1(str, Enum):
    REGISTERED_PRODUCTION_CANDIDATE = "REGISTERED_PRODUCTION_CANDIDATE"
    DEVELOPMENT_LOCAL_BARE_REMOTE_NONAUTHORIZING = (
        "DEVELOPMENT_LOCAL_BARE_REMOTE_NONAUTHORIZING"
    )


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
    except (TypeError, ValueError) as error:
        raise V072FinalPreregistrationInvariantViolation(str(error)) from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + encoded
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072FinalPreregistrationInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        raise V072FinalPreregistrationInvariantViolation(
            f"{field_name} must be canonical nonempty text"
        )
    return value


def _git_object_id(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) not in (40, 64)
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V072FinalPreregistrationInvariantViolation(
            f"{field_name} must be one full lowercase Git object ID"
        )
    return value


def _safe_repository_path(value: Any) -> str:
    path = PurePosixPath(_token(value, "repository-relative path"))
    if (
        path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or str(path) != value
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "repository-relative path is unsafe or noncanonical"
        )
    return value


def _strict_document(
    value: Any,
    *,
    expected_keys: frozenset[str],
    label: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected_keys:
        raise V072FinalPreregistrationInvariantViolation(
            f"{label} schema keys changed"
        )
    try:
        canonical_json_bytes(value)
    except (TypeError, ValueError) as error:
        raise V072FinalPreregistrationInvariantViolation(
            f"{label} is not canonical-JSON compatible"
        ) from error
    return value


def _draft_preregistration_payload_v1() -> dict[str, Any]:
    document = (
        prereg.freeze_transfer_guided_acquisition_preregistration_v1()
        .to_document()
    )
    if document.pop("preregistration_id") != prereg.DRAFT_PREREGISTRATION_ID:
        raise V072FinalPreregistrationInvariantViolation(
            "draft preregistration authority changed"
        )
    return document


def _expected_final_preregistration_payload_v1(
    manifest_id: str,
) -> dict[str, Any]:
    manifest_id = _cid(manifest_id, "final execution manifest")
    payload = _draft_preregistration_payload_v1()
    payload["confirmatory_execution_manifest_id"] = manifest_id
    payload["confirmatory_profile_finalized"] = True
    # The anchor is later and cannot be included without a circular identity.
    payload["anchor_commit_id"] = None
    payload["target_execution_allowed"] = False
    return payload


def _verify_final_manifest_document_v1(
    document: Any,
) -> tuple[dict[str, Any], str]:
    expected_keys = frozenset(
        {
            "schema",
            "schema_version",
            "component_registry_id",
            "global_bindings",
            "final_preregistration_id_embedded",
            "manifest_id",
        }
    )
    document = _strict_document(
        document,
        expected_keys=expected_keys,
        label="final execution manifest",
    )
    bindings = document["global_bindings"]
    if (
        document["schema"] != FINAL_MANIFEST_SCHEMA
        or document["schema_version"] != manifest_v1.SCHEMA_VERSION
        or document["final_preregistration_id_embedded"] is not False
        or type(bindings) is not dict
        or set(bindings) != _REQUIRED_MANIFEST_GLOBAL_BINDINGS
        or bindings.get("final_preregistration_id_embedded") is not False
        or bindings.get("future_binding_direction")
        != "FINAL_PREREGISTRATION_BINDS_MANIFEST_ID_ONE_WAY"
        or "final_preregistration_id" in bindings
        or "preregistration_id" in bindings
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "final execution manifest is not the frozen one-way schema"
        )
    _cid(document["component_registry_id"], "component registry")
    for field_name in (
        "source_reconstruction_recipe_id",
        "source_archive_id",
        "source_archive_verification_attestation_id",
        "environment_manifest_id",
        "confidence_profile_id",
        "checkpoint_cap_profile_id",
        "component_tree_digest",
        "test_command_manifest_id",
        "runtime_dependency_lock_id",
        "interpreter_build_identity_id",
    ):
        _cid(bindings.get(field_name), field_name)
    if (
        bindings.get("repository_url") != manifest_v1.REPOSITORY_URL
        or bindings.get("target_branch") != manifest_v1.TARGET_BRANCH
        or bindings.get(
            "source_reconstruction_recipe_repository_path"
        )
        != manifest_v1.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
        or bindings.get("confirmatory_family_generation")
        != prereg.CONFIRMATORY_FAMILY_GENERATION
        or bindings.get("context_ids")
        != list(
            item.context_id
            for item in prereg.registered_heldout_public_contexts_v2()
        )
        or bindings.get("law_ids")
        != list(
            item.law_id
            for item in prereg.frozen_heldout_environment_manifest_v1().laws
        )
        or bindings.get("arm_order") != list(prereg.ARM_ORDER)
        or bindings.get("terminal_codes") != list(prereg.TERMINAL_CODES)
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "final manifest global authorities differ from the frozen profile"
        )
    payload = {key: value for key, value in document.items() if key != "manifest_id"}
    manifest_id = _content_id(FINAL_MANIFEST_DOMAIN, payload)
    if document["manifest_id"] != manifest_id:
        raise V072FinalPreregistrationInvariantViolation(
            "final execution manifest ID differs from its payload"
        )
    return document, manifest_id


@dataclass(frozen=True, slots=True)
class V072FinalPreregistrationLogicalAttestationV1:
    manifest_id: str
    final_preregistration_id: str
    one_way_binding_verified: bool = True
    circular_identity_absent: bool = True
    target_execution_allowed: bool = False
    registered_observer_calls: int = 0
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.manifest_id, "logical-attestation manifest")
        _cid(
            self.final_preregistration_id,
            "logical-attestation final preregistration",
        )
        if (
            self.one_way_binding_verified is not True
            or self.circular_identity_absent is not True
            or self.target_execution_allowed is not False
            or self.registered_observer_calls != 0
        ):
            raise V072FinalPreregistrationInvariantViolation(
                "logical attestation is malformed or authorizing"
            )
        object.__setattr__(
            self,
            "_attestation_id",
            _content_id(
                FINAL_PREREGISTRATION_ATTESTATION_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_final_preregistration_logical_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "manifest_id": self.manifest_id,
            "final_preregistration_id": self.final_preregistration_id,
            "one_way_binding_verified": True,
            "circular_identity_absent": True,
            "target_execution_allowed": False,
            "registered_observer_calls": 0,
        }

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


def verify_v072_final_preregistration_documents_v1(
    *,
    manifest_document: Mapping[str, Any],
    final_preregistration_document: Mapping[str, Any],
) -> V072FinalPreregistrationLogicalAttestationV1:
    """Verify the one-way content dependency without minting authority."""

    manifest_document, manifest_id = _verify_final_manifest_document_v1(
        manifest_document
    )
    expected_payload = _expected_final_preregistration_payload_v1(
        manifest_id
    )
    expected_keys = frozenset(
        {*expected_payload, "preregistration_id"}
    )
    final_document = _strict_document(
        final_preregistration_document,
        expected_keys=expected_keys,
        label="final preregistration",
    )
    if (
        final_document["schema"] != FINAL_PREREGISTRATION_SCHEMA
        or {
            key: value
            for key, value in final_document.items()
            if key != "preregistration_id"
        }
        != expected_payload
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "final preregistration changed a frozen law, seed, schedule, "
            "threshold, cap, endpoint, or manifest binding"
        )
    final_id = _content_id(
        FINAL_PREREGISTRATION_DOMAIN,
        expected_payload,
    )
    if final_document["preregistration_id"] != final_id:
        raise V072FinalPreregistrationInvariantViolation(
            "final preregistration ID differs from its payload"
        )
    if final_id.encode("ascii") in canonical_json_bytes(manifest_document):
        raise V072FinalPreregistrationInvariantViolation(
            "execution manifest circularly embeds the final preregistration ID"
        )
    bindings = manifest_document["global_bindings"]
    if (
        bindings["context_ids"] != final_document["context_ids"]
        or bindings["environment_manifest_id"]
        != final_document["environment_manifest_id"]
        or bindings["arm_order"] != final_document["arm_order"]
        or bindings["terminal_codes"] != final_document["terminal_codes"]
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "manifest and final preregistration authorities do not agree"
        )
    return V072FinalPreregistrationLogicalAttestationV1(
        manifest_id,
        final_id,
    )


@dataclass(frozen=True, slots=True)
class V072FinalPreregistrationReadinessV1:
    manifest_readiness_id: str | None
    source_reconstruction_recipe_id: str | None
    finalization_blockers: tuple[str, ...]
    final_manifest_id: None = None
    final_preregistration_id: None = None
    remote_main_anchor_id: None = None
    target_execution_allowed: bool = False
    registered_observer_calls: int = 0
    _readiness_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.manifest_readiness_id is not None:
            _cid(self.manifest_readiness_id, "manifest readiness")
        if self.source_reconstruction_recipe_id is not None:
            _cid(
                self.source_reconstruction_recipe_id,
                "source reconstruction recipe",
            )
        if (
            type(self.finalization_blockers) is not tuple
            or any(
                type(item) is not str or not item
                for item in self.finalization_blockers
            )
            or self.final_manifest_id is not None
            or self.final_preregistration_id is not None
            or self.remote_main_anchor_id is not None
            or self.target_execution_allowed is not False
            or self.registered_observer_calls != 0
        ):
            raise V072FinalPreregistrationInvariantViolation(
                "final-preregistration readiness is malformed or authorizing"
            )
        object.__setattr__(
            self,
            "_readiness_id",
            _content_id(
                FINAL_PREREGISTRATION_READINESS_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_final_preregistration_readiness.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "manifest_readiness_id": (
                self.manifest_readiness_id
                if self.manifest_readiness_id is not None
                else {
                    "kind": "MISSING_APPLICABLE_ARTIFACT",
                    "reason": "FINAL_MANIFEST_READINESS_REPLAY_FAILED",
                }
            ),
            "source_reconstruction_recipe_id": (
                self.source_reconstruction_recipe_id
                if self.source_reconstruction_recipe_id is not None
                else {
                    "kind": "MISSING_APPLICABLE_ARTIFACT",
                    "reason": (
                        "CANONICAL_SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED"
                    ),
                }
            ),
            "finalization_blockers": list(self.finalization_blockers),
            "final_manifest_id": None,
            "final_preregistration_id": None,
            "remote_main_anchor_id": None,
            "target_execution_allowed": False,
            "registered_observer_calls": 0,
        }

    @property
    def readiness_id(self) -> str:
        return self._readiness_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "readiness_id": self.readiness_id}


def inspect_v072_final_preregistration_readiness_v1(
    repository_root: str | os.PathLike[str],
) -> V072FinalPreregistrationReadinessV1:
    """Inspect manifest prerequisites without writing final artifacts."""

    manifest_readiness = None
    manifest_blockers: tuple[str, ...]
    try:
        manifest_readiness = (
            manifest_v1
            .inspect_confirmatory_execution_manifest_readiness_with_source_recipe_v1(
                repository_root,
            )
        )
    except ValueError as error:
        manifest_blockers = (
            "FINAL_MANIFEST_READINESS_REPLAY_FAILED:"
            + type(error).__name__,
        )
    else:
        manifest_blockers = manifest_readiness.finalization_blockers
    source_reconstruction_recipe_id: str | None = None
    if manifest_readiness is not None:
        candidate = manifest_readiness.global_bindings[
            "source_reconstruction_recipe_id"
        ]
        if type(candidate) is str:
            source_reconstruction_recipe_id = candidate
    blockers = tuple(
        dict.fromkeys(
            (
                *(
                    (
                        manifest_v1
                        .SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED_BLOCKER,
                    )
                    if source_reconstruction_recipe_id is None
                    else ()
                ),
                *manifest_blockers,
                *(
                    ("FINAL_PREREGISTRATION_FINALIZATION_DISABLED",)
                    if FINAL_PREREGISTRATION_ENABLED is not True
                    else ()
                ),
            )
        )
    )
    return V072FinalPreregistrationReadinessV1(
        (
            manifest_readiness.readiness_id
            if manifest_readiness is not None
            else None
        ),
        source_reconstruction_recipe_id,
        blockers,
    )


@dataclass(frozen=True, slots=True)
class V072FinalPreregistrationV1:
    """One-way final preregistration bound to an internally minted manifest."""

    _finalization_capability: object
    manifest: manifest_v1.ConfirmatoryExecutionManifestV1
    frozen_payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if (
            self._finalization_capability is not _FINAL_PREREGISTRATION_SENTINEL
            or FINAL_PREREGISTRATION_ENABLED is not True
            or type(self.manifest)
            is not manifest_v1.ConfirmatoryExecutionManifestV1
            or type(self.frozen_payload) is not dict
            or self.frozen_payload
            != _expected_final_preregistration_payload_v1(
                self.manifest.manifest_id
            )
        ):
            raise V072FinalPreregistrationInvariantViolation(
                "final preregistration lacks the internally minted complete "
                "source-and-manifest capability"
            )

    @property
    def manifest_id(self) -> str:
        return self.manifest.manifest_id

    @property
    def final_preregistration_id(self) -> str:
        return _content_id(
            FINAL_PREREGISTRATION_DOMAIN,
            self.frozen_payload,
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **dict(self.frozen_payload),
            "preregistration_id": self.final_preregistration_id,
        }


_FINAL_PREREGISTRATION_SENTINEL = object()


def finalize_v072_final_preregistration_v1(
    repository_root: str | os.PathLike[str],
) -> V072FinalPreregistrationV1:
    """Write manifest first, then mint/write its one-way preregistration."""

    if FINAL_PREREGISTRATION_ENABLED is not True:
        raise V072FinalPreregistrationLockedV1(
            "final preregistration authority is disabled"
        )
    try:
        manifest = (
            manifest_v1.write_confirmatory_execution_manifest_v1(
                repository_root
            )
        )
    except (
        manifest_v1.V072ConfirmatoryExecutionManifestV1InvariantViolation
    ) as error:
        raise V072FinalPreregistrationLockedV1(
            "final preregistration lacks a complete internally written "
            "manifest"
        ) from error
    final = V072FinalPreregistrationV1(
        _FINAL_PREREGISTRATION_SENTINEL,
        manifest,
        _expected_final_preregistration_payload_v1(manifest.manifest_id),
    )
    attestation = verify_v072_final_preregistration_documents_v1(
        manifest_document=manifest.to_document(),
        final_preregistration_document=final.to_document(),
    )
    if (
        attestation.manifest_id != manifest.manifest_id
        or attestation.final_preregistration_id
        != final.final_preregistration_id
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "internal one-way preregistration replay changed identities"
        )
    try:
        root = manifest_v1._root(repository_root)
        manifest_v1._write_canonical_artifact_v1(
            root,
            FINAL_PREREGISTRATION_REPOSITORY_PATH,
            final.to_document(),
        )
    except (
        manifest_v1.V072ConfirmatoryExecutionManifestV1InvariantViolation
    ) as error:
        raise V072FinalPreregistrationInvariantViolation(
            "final preregistration artifact write failed closed"
        ) from error
    return final


def _production_repository_root_v1(
    value: str | os.PathLike[str],
) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        raise V072FinalPreregistrationInvariantViolation(
            "production anchor repository root must be absolute"
        )
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise V072FinalPreregistrationInvariantViolation(
            "production anchor repository root does not exist"
        ) from error
    if (
        resolved != candidate
        or candidate.is_symlink()
        or not resolved.is_dir()
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "production anchor repository root is linked or noncanonical"
        )
    return resolved


def _run_git_for_claim_v1(
    root: Path,
    *arguments: str,
    accepted_return_codes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            ("git", "-C", os.fspath(root), *arguments),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise V072FinalPreregistrationInvariantViolation(
            "production Git claim derivation could not complete"
        ) from error
    if result.returncode not in accepted_return_codes:
        raise V072FinalPreregistrationInvariantViolation(
            "production Git claim derivation failed for "
            + " ".join(arguments)
        )
    return result


def _git_text_for_claim_v1(root: Path, *arguments: str) -> str:
    data = _run_git_for_claim_v1(root, *arguments).stdout
    try:
        return data.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as error:
        raise V072FinalPreregistrationInvariantViolation(
            "production Git metadata is not canonical UTF-8"
        ) from error


def _unique_json_object_for_claim_v1(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise V072FinalPreregistrationInvariantViolation(
                f"duplicate committed JSON key: {key}"
            )
        result[key] = value
    return result


def _reject_json_constant_for_claim_v1(value: str) -> Any:
    raise V072FinalPreregistrationInvariantViolation(
        f"non-finite committed JSON token: {value}"
    )


def _parse_canonical_blob_for_claim_v1(
    data: bytes,
    *,
    label: str,
) -> dict[str, Any]:
    try:
        document = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_json_object_for_claim_v1,
            parse_constant=_reject_json_constant_for_claim_v1,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        V072FinalPreregistrationInvariantViolation,
    ) as error:
        raise V072FinalPreregistrationInvariantViolation(
            f"{label} is not strict JSON"
        ) from error
    if type(document) is not dict:
        raise V072FinalPreregistrationInvariantViolation(
            f"{label} bytes are not canonical JSON"
        )
    try:
        canonical = canonical_json_bytes(document)
    except (TypeError, ValueError) as error:
        raise V072FinalPreregistrationInvariantViolation(
            f"{label} is not canonical-JSON compatible"
        ) from error
    if canonical != data:
        raise V072FinalPreregistrationInvariantViolation(
            f"{label} bytes are not canonical JSON"
        )
    return document


@dataclass(frozen=True, slots=True)
class V072RemoteMainAnchorClaimV1:
    """Untrusted, nonauthorizing claim consumed by the independent verifier."""

    verification_scope: RemoteMainAnchorVerificationScopeV1
    repository_url: str
    target_branch: str
    commit_id: str
    tree_id: str
    parent_commit_id: str
    source_reconstruction_recipe_blob_id: str
    manifest_blob_id: str
    final_preregistration_blob_id: str
    source_reconstruction_recipe_id: str
    manifest_id: str
    final_preregistration_id: str
    source_reconstruction_recipe_repository_path: str = (
        SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
    )
    manifest_repository_path: str = FINAL_MANIFEST_REPOSITORY_PATH
    final_preregistration_repository_path: str = (
        FINAL_PREREGISTRATION_REPOSITORY_PATH
    )
    target_execution_allowed: bool = False
    registered_observer_calls: int = 0
    _claim_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.verification_scope) is not RemoteMainAnchorVerificationScopeV1:
            raise V072FinalPreregistrationInvariantViolation(
                "remote-main verification scope is not typed"
            )
        _token(self.repository_url, "repository URL")
        if self.target_branch != "main":
            raise V072FinalPreregistrationInvariantViolation(
                "remote-main claim must bind branch main"
            )
        for value, name in (
            (self.commit_id, "anchor commit"),
            (self.tree_id, "anchor tree"),
            (self.parent_commit_id, "anchor parent"),
            (
                self.source_reconstruction_recipe_blob_id,
                "source-reconstruction-recipe blob",
            ),
            (self.manifest_blob_id, "manifest blob"),
            (
                self.final_preregistration_blob_id,
                "final-preregistration blob",
            ),
        ):
            _git_object_id(value, name)
        _cid(
            self.source_reconstruction_recipe_id,
            "anchor source reconstruction recipe",
        )
        _cid(self.manifest_id, "anchor manifest")
        _cid(
            self.final_preregistration_id,
            "anchor final preregistration",
        )
        paths = (
            _safe_repository_path(
                self.source_reconstruction_recipe_repository_path
            ),
            _safe_repository_path(self.manifest_repository_path),
            _safe_repository_path(
                self.final_preregistration_repository_path
            ),
        )
        if (
            len(set(paths)) != 3
            or self.source_reconstruction_recipe_repository_path
            != SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
            or self.target_execution_allowed is not False
            or self.registered_observer_calls != 0
        ):
            raise V072FinalPreregistrationInvariantViolation(
                "remote-main claim is malformed or authorizing"
            )
        object.__setattr__(
            self,
            "_claim_id",
            _content_id(REMOTE_MAIN_ANCHOR_CLAIM_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_remote_main_anchor_claim.v1",
            "schema_version": SCHEMA_VERSION,
            "verification_scope": self.verification_scope.value,
            "repository_url": self.repository_url,
            "target_branch": self.target_branch,
            "remote_tracking_ref": "refs/remotes/origin/main",
            "local_branch_ref": "refs/heads/main",
            "commit_id": self.commit_id,
            "tree_id": self.tree_id,
            "parent_commit_id": self.parent_commit_id,
            "source_reconstruction_recipe_repository_path": (
                self.source_reconstruction_recipe_repository_path
            ),
            "manifest_repository_path": self.manifest_repository_path,
            "final_preregistration_repository_path": (
                self.final_preregistration_repository_path
            ),
            "source_reconstruction_recipe_blob_id": (
                self.source_reconstruction_recipe_blob_id
            ),
            "manifest_blob_id": self.manifest_blob_id,
            "final_preregistration_blob_id": (
                self.final_preregistration_blob_id
            ),
            "source_reconstruction_recipe_id": (
                self.source_reconstruction_recipe_id
            ),
            "manifest_id": self.manifest_id,
            "final_preregistration_id": self.final_preregistration_id,
            "first_qualifying_origin_main_commit_required": True,
            "parent_and_all_ancestors_must_lack_anchored_identity_ids": [
                "source_reconstruction_recipe_id",
                "final_preregistration_id",
            ],
            "target_execution_allowed": False,
            "registered_observer_calls": 0,
        }

    @property
    def claim_id(self) -> str:
        return self._claim_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "claim_id": self.claim_id}


def derive_v072_remote_main_anchor_claim_v1(
    repository_root: str | os.PathLike[str],
) -> V072RemoteMainAnchorClaimV1:
    """Derive every production claim field from the clean committed tree."""

    root = _production_repository_root_v1(repository_root)
    if (
        Path(
            _git_text_for_claim_v1(
                root,
                "rev-parse",
                "--show-toplevel",
            )
        )
        != root
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "production claim path is not the Git worktree root"
        )
    if _run_git_for_claim_v1(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ).stdout:
        raise V072FinalPreregistrationInvariantViolation(
            "production claim requires a clean worktree"
        )
    if (
        _git_text_for_claim_v1(
            root,
            "symbolic-ref",
            "--quiet",
            "HEAD",
        )
        != "refs/heads/main"
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "production claim requires attached branch main"
        )
    origin_fetch_url = _git_text_for_claim_v1(
        root,
        "remote",
        "get-url",
        "origin",
    )
    origin_push_url = _git_text_for_claim_v1(
        root,
        "remote",
        "get-url",
        "--push",
        "origin",
    )
    if (
        origin_fetch_url != manifest_v1.REPOSITORY_URL
        or origin_push_url != manifest_v1.REPOSITORY_URL
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "production claim origin fetch/push URL is not frozen"
        )
    refs = tuple(
        _git_text_for_claim_v1(
            root,
            "rev-parse",
            "--verify",
            f"{name}^{{commit}}",
        )
        for name in (
            "HEAD",
            "refs/heads/main",
            "refs/remotes/origin/main",
        )
    )
    if len(set(refs)) != 1:
        raise V072FinalPreregistrationInvariantViolation(
            "production claim is local-only or origin/main is stale"
        )
    commit_id = refs[0]
    _git_object_id(commit_id, "derived production commit")
    if (
        _git_text_for_claim_v1(
            root,
            "cat-file",
            "-t",
            commit_id,
        )
        != "commit"
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "derived production commit object is missing"
        )
    tree_id = _git_text_for_claim_v1(
        root,
        "show",
        "-s",
        "--format=%T",
        commit_id,
    )
    _git_object_id(tree_id, "derived production tree")
    if (
        _git_text_for_claim_v1(root, "cat-file", "-t", tree_id)
        != "tree"
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "derived production tree object is missing"
        )
    parents = _git_text_for_claim_v1(
        root,
        "show",
        "-s",
        "--format=%P",
        commit_id,
    ).split()
    if len(parents) != 1:
        raise V072FinalPreregistrationInvariantViolation(
            "production anchor commit must have exactly one parent"
        )
    parent_commit_id = parents[0]
    _git_object_id(parent_commit_id, "derived production parent")
    if (
        _git_text_for_claim_v1(
            root,
            "cat-file",
            "-t",
            parent_commit_id,
        )
        != "commit"
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "derived production parent object is missing"
        )

    paths = (
        SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH,
        FINAL_MANIFEST_REPOSITORY_PATH,
        FINAL_PREREGISTRATION_REPOSITORY_PATH,
    )
    blob_ids = tuple(
        _git_text_for_claim_v1(
            root,
            "rev-parse",
            f"{commit_id}:{path}",
        )
        for path in paths
    )
    for blob_id, path in zip(blob_ids, paths, strict=True):
        _git_object_id(blob_id, f"derived blob for {path}")
        if (
            _git_text_for_claim_v1(root, "cat-file", "-t", blob_id)
            != "blob"
        ):
            raise V072FinalPreregistrationInvariantViolation(
                f"committed production artifact is not a blob: {path}"
            )
    recipe_bytes, manifest_bytes, final_bytes = tuple(
        _run_git_for_claim_v1(
            root,
            "cat-file",
            "blob",
            blob_id,
        ).stdout
        for blob_id in blob_ids
    )
    if len(recipe_bytes) > recipe_v1.MAX_CANONICAL_RECIPE_BYTES:
        raise V072FinalPreregistrationInvariantViolation(
            "committed source reconstruction recipe exceeds its byte cap"
        )
    recipe_document = _parse_canonical_blob_for_claim_v1(
        recipe_bytes,
        label="source reconstruction recipe",
    )
    manifest_document = _parse_canonical_blob_for_claim_v1(
        manifest_bytes,
        label="confirmatory execution manifest",
    )
    final_document = _parse_canonical_blob_for_claim_v1(
        final_bytes,
        label="final preregistration",
    )
    if "recipe_id" not in recipe_document:
        raise V072FinalPreregistrationInvariantViolation(
            "committed source reconstruction recipe has no recipe ID"
        )
    recipe_id = _cid(
        recipe_document["recipe_id"],
        "committed source reconstruction recipe",
    )
    recipe_payload = {
        key: value
        for key, value in recipe_document.items()
        if key != "recipe_id"
    }
    if recipe_id != _content_id(recipe_v1.RECIPE_DOMAIN, recipe_payload):
        raise V072FinalPreregistrationInvariantViolation(
            "committed source reconstruction recipe ID differs from bytes"
        )
    _, manifest_id = _verify_final_manifest_document_v1(
        manifest_document
    )
    logical_attestation = verify_v072_final_preregistration_documents_v1(
        manifest_document=manifest_document,
        final_preregistration_document=final_document,
    )
    bindings = manifest_document["global_bindings"]
    if (
        bindings["source_reconstruction_recipe_id"] != recipe_id
        or bindings["source_reconstruction_recipe_repository_path"]
        != SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
        or logical_attestation.manifest_id != manifest_id
    ):
        raise V072FinalPreregistrationInvariantViolation(
            "committed recipe, manifest, and preregistration do not form "
            "the frozen one-way identity chain"
        )
    return V072RemoteMainAnchorClaimV1(
        (
            RemoteMainAnchorVerificationScopeV1
            .REGISTERED_PRODUCTION_CANDIDATE
        ),
        manifest_v1.REPOSITORY_URL,
        manifest_v1.TARGET_BRANCH,
        commit_id,
        tree_id,
        parent_commit_id,
        blob_ids[0],
        blob_ids[1],
        blob_ids[2],
        recipe_id,
        manifest_id,
        logical_attestation.final_preregistration_id,
    )


@dataclass(frozen=True, slots=True)
class V072RemoteMainAnchorV1:
    """Executable authority minted from one production-scope replay."""

    _anchor_capability: object
    claim: V072RemoteMainAnchorClaimV1
    independent_semantic_attestation: Any = field(repr=False)
    target_execution_allowed: bool = True
    _anchor_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from acfqp import (
            v072_remote_main_anchor_independent_verifier_v1 as independent,
        )

        attestation = self.independent_semantic_attestation
        if (
            self._anchor_capability is not _REMOTE_MAIN_ANCHOR_SENTINEL
            or REMOTE_MAIN_ANCHOR_AUTHORITY_ENABLED is not True
            or type(self.claim) is not V072RemoteMainAnchorClaimV1
            or type(attestation)
            is not independent.IndependentRemoteMainAnchorAttestationV1
            or self.claim.verification_scope
            is not RemoteMainAnchorVerificationScopeV1.REGISTERED_PRODUCTION_CANDIDATE
            or attestation.verification_scope
            is not RemoteMainAnchorVerificationScopeV1.REGISTERED_PRODUCTION_CANDIDATE
            or self.claim.repository_url != manifest_v1.REPOSITORY_URL
            or self.claim.target_branch != manifest_v1.TARGET_BRANCH
            or attestation.claim_id != self.claim.claim_id
            or attestation.repository_url != self.claim.repository_url
            or attestation.commit_id != self.claim.commit_id
            or attestation.tree_id != self.claim.tree_id
            or attestation.parent_commit_id != self.claim.parent_commit_id
            or attestation.source_reconstruction_recipe_blob_id
            != self.claim.source_reconstruction_recipe_blob_id
            or attestation.manifest_blob_id != self.claim.manifest_blob_id
            or attestation.final_preregistration_blob_id
            != self.claim.final_preregistration_blob_id
            or attestation.source_reconstruction_recipe_id
            != self.claim.source_reconstruction_recipe_id
            or attestation.manifest_id != self.claim.manifest_id
            or attestation.final_preregistration_id
            != self.claim.final_preregistration_id
            or attestation.executable_anchor_minted is not False
            or attestation.target_execution_allowed is not False
            or attestation.registered_observer_calls != 0
            or self.target_execution_allowed is not True
        ):
            raise V072FinalPreregistrationInvariantViolation(
                "remote-main anchor lacks the internal final-artifact and "
                "semantic-push capability"
            )
        _cid(
            attestation.verification_id,
            "independent anchor attestation",
        )
        object.__setattr__(
            self,
            "_anchor_id",
            _content_id(REMOTE_MAIN_ANCHOR_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_remote_main_anchor.v1",
            "schema_version": SCHEMA_VERSION,
            "claim_id": self.claim.claim_id,
            "source_reconstruction_recipe_id": (
                self.claim.source_reconstruction_recipe_id
            ),
            "source_reconstruction_recipe_blob_id": (
                self.claim.source_reconstruction_recipe_blob_id
            ),
            "source_reconstruction_recipe_repository_path": (
                self.claim.source_reconstruction_recipe_repository_path
            ),
            "manifest_id": self.claim.manifest_id,
            "final_preregistration_id": (
                self.claim.final_preregistration_id
            ),
            "repository_url": self.claim.repository_url,
            "target_branch": self.claim.target_branch,
            "commit_id": self.claim.commit_id,
            "tree_id": self.claim.tree_id,
            "parent_commit_id": self.claim.parent_commit_id,
            "independent_semantic_attestation_id": (
                self.independent_semantic_attestation.verification_id
            ),
            "target_execution_allowed": True,
        }

    @property
    def anchor_id(self) -> str:
        return self._anchor_id

    @property
    def independent_semantic_attestation_id(self) -> str:
        return self.independent_semantic_attestation.verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "anchor_id": self.anchor_id}


_REMOTE_MAIN_ANCHOR_SENTINEL = object()


def mint_v072_remote_main_anchor_v1(
    *,
    repository_root: str | os.PathLike[str],
) -> V072RemoteMainAnchorV1:
    """Derive, independently replay, and privately mint one anchor."""

    if REMOTE_MAIN_ANCHOR_AUTHORITY_ENABLED is not True:
        raise V072FinalPreregistrationLockedV1(
            "remote-main anchor authority is disabled"
        )
    try:
        claim = derive_v072_remote_main_anchor_claim_v1(repository_root)
    except V072FinalPreregistrationInvariantViolation as error:
        raise V072FinalPreregistrationLockedV1(
            "remote-main production claim derivation failed"
        ) from error
    from acfqp import (
        v072_remote_main_anchor_independent_verifier_v1 as independent,
    )

    try:
        attestation = (
            independent.verify_remote_main_anchor_claim_independently_v1(
                repository_root,
                claim,
            )
        )
    except (
        independent.IndependentRemoteMainAnchorVerificationViolation
    ) as error:
        raise V072FinalPreregistrationLockedV1(
            "remote-main claim failed independent production replay"
        ) from error
    return V072RemoteMainAnchorV1(
        _REMOTE_MAIN_ANCHOR_SENTINEL,
        claim,
        attestation,
    )


__all__ = [
    "FINAL_MANIFEST_DOMAIN",
    "FINAL_MANIFEST_REPOSITORY_PATH",
    "FINAL_PREREGISTRATION_DOMAIN",
    "FINAL_PREREGISTRATION_ENABLED",
    "FINAL_PREREGISTRATION_REPOSITORY_PATH",
    "PROFILE_KEY",
    "REMOTE_MAIN_ANCHOR_AUTHORITY_ENABLED",
    "RemoteMainAnchorVerificationScopeV1",
    "SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH",
    "TARGET_EXECUTION_ALLOWED",
    "V072FinalPreregistrationInvariantViolation",
    "V072FinalPreregistrationLockedV1",
    "V072FinalPreregistrationLogicalAttestationV1",
    "V072FinalPreregistrationReadinessV1",
    "V072FinalPreregistrationV1",
    "V072RemoteMainAnchorClaimV1",
    "V072RemoteMainAnchorV1",
    "derive_v072_remote_main_anchor_claim_v1",
    "finalize_v072_final_preregistration_v1",
    "inspect_v072_final_preregistration_readiness_v1",
    "mint_v072_remote_main_anchor_v1",
    "verify_v072_final_preregistration_documents_v1",
]
