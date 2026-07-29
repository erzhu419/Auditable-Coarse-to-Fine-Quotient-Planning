"""Independent Git-object verifier for the V0-075 production-open boundary.

The public API accepts only a repository root.  It accepts no caller-supplied
manifest ID, final-preregistration ID, registry, signature claim, commit,
status, or expected value.  All authority is recomputed from committed Git
objects under ``refs/remotes/origin/main``.

This verifier does not import the manifest/preregistration implementation.
Its schema and content-ID replay are intentionally independent.  It pins the
complete public-key bytes carried by the tracked final preregistration,
verifies every component blob against the qualifying commit, proves that no
ancestor contained either sentinel, and only then issues the exact typed
``V075ProductionOpenAuthorityV1`` consumed by a future private observer.

No function in this module accesses a target observer or an environment
reveal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import os
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_public_campaign_authority_v1 as public_authority


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_independent_remote_main_anchor_verifier_v1"

REPOSITORY_URL = (
    "git@github.com:erzhu419/"
    "Auditable-Coarse-to-Fine-Quotient-Planning.git"
)
TARGET_BRANCH = "main"
REMOTE_TRACKING_REF = "refs/remotes/origin/main"
LOCAL_BRANCH_REF = "refs/heads/main"
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
    {"name": "LC_ALL", "value": "C.UTF-8"},
    {"name": "PYTHONHASHSEED", "value": "0"},
    {"name": "TZ", "value": "UTC"},
)

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
REQUIRED_AUTHORITY_ROLE_ORDER = (
    "OBSERVER_PROFILE",
    "SOURCE_PRIOR_ADAPTER",
    "SOURCE_PRIOR_ADAPTER_VERIFICATION",
    "DEPENDENCY_LOCK",
    "PRODUCTION_WORKER_REGISTRY",
    "OCCURRENCE_CAS_TRANSPORT",
    "EXACT_H2_TRANSITION_ENGINE",
    "TOTAL_LIFT",
    "CAMPAIGN_RECONCILIATION",
    "COMPLETE_BUNDLE_ENDPOINT",
)

# No generic caller-supplied ``(authority_id, verification_id, digest)`` tuple
# is semantic evidence.  A role flips to concrete only when this independent
# module contains a strict parser/replayer for the exact authority artifact
# and its exact attestation bytes.  The current pre-target slice intentionally
# leaves every entry unavailable.
_ROLE_SEMANTIC_VERIFIER_IMPLEMENTED = {
    role: False for role in REQUIRED_AUTHORITY_ROLE_ORDER
}

_DOMAINS = {
    "component_blob": "acfqp:v075-manifest-component-blob:v1",
    "authority_binding": "acfqp:v075-manifest-authority-binding:v1",
    "authority_registry": "acfqp:v075-manifest-authority-registry:v1",
    "component_registry": "acfqp:v075-manifest-component-registry:v1",
    "manifest": "acfqp:v075-confirmatory-execution-manifest:v1",
    "final_preregistration": "acfqp:v075-final-preregistration:v1",
    "rsa_public_key": "acfqp:v075-rsa-public-verification-key:v1",
    "signer_registry": "acfqp:v075-trusted-signer-registry:v1",
    "opaque_commitment": (
        "acfqp:v075-salted-opaque-environment-commitment:v1"
    ),
    "anchor_attestation": (
        "acfqp:v075-independent-remote-main-anchor-attestation:v1"
    ),
    "production_open": "acfqp:v075-production-open-authority:v1",
}

_MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
_MAX_SENTINEL_SCAN_BLOB_BYTES = 32 * 1024 * 1024
_MAX_SENTINEL_SCAN_TOTAL_BYTES = 512 * 1024 * 1024


class V075RemoteMainAnchorInvariantViolation(ValueError):
    """Committed identity, schema, ancestry, or blob closure failed."""


class V075ProductionOpenAuthorityNotReady(RuntimeError):
    """No complete first-qualifying remote-main authority exists."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        body = canonical_json_bytes(dict(payload))
        domain = _DOMAINS[role].encode("utf-8")
    except (KeyError, TypeError, ValueError) as error:
        raise V075RemoteMainAnchorInvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except (Phase3EIdentityError, ValueError) as error:
        raise V075RemoteMainAnchorInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _git_oid(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) not in (40, 64)
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            f"{field_name} must be one full lowercase Git object ID"
        )
    return value


def _strict(
    value: Any,
    *,
    keys: set[str] | frozenset[str],
    label: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(keys):
        raise V075RemoteMainAnchorInvariantViolation(
            f"{label} schema keys changed"
        )
    try:
        canonical_json_bytes(value)
    except (TypeError, ValueError) as error:
        raise V075RemoteMainAnchorInvariantViolation(
            f"{label} is not canonical-JSON compatible"
        ) from error
    return value


def _safe_path(value: Any) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\\" in value
        or "\x00" in value
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "repository path is malformed"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "repository path is unsafe or noncanonical"
        )
    return value


def _git(
    root: Path,
    *arguments: str,
    binary: bool = False,
    allow_missing: bool = False,
) -> bytes | str | None:
    process = subprocess.run(
        ("git", "-C", str(root), *arguments),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if process.returncode:
        if allow_missing:
            return None
        raise V075RemoteMainAnchorInvariantViolation(
            "Git object verification failed: "
            + process.stderr.decode("utf-8", errors="replace").strip()
        )
    if len(process.stdout) > _MAX_ARTIFACT_BYTES and (
        arguments[:1] == ("show",)
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "tracked authority artifact exceeds byte cap"
        )
    if binary:
        return process.stdout
    return process.stdout.decode("utf-8", errors="strict").strip()


def _read_blob_at(
    root: Path,
    commit_id: str,
    repository_path: str,
) -> bytes | None:
    _git_oid(commit_id, "commit")
    path = _safe_path(repository_path)
    result = _git(
        root,
        "show",
        f"{commit_id}:{path}",
        binary=True,
        allow_missing=True,
    )
    if result is None:
        return None
    assert type(result) is bytes
    if len(result) > _MAX_ARTIFACT_BYTES:
        raise V075RemoteMainAnchorInvariantViolation(
            "tracked authority artifact exceeds byte cap"
        )
    return result


def _tree_blob_record(
    root: Path,
    commit_id: str,
    repository_path: str,
) -> tuple[str, bool]:
    output = _git(
        root,
        "ls-tree",
        commit_id,
        "--",
        _safe_path(repository_path),
    )
    assert type(output) is str
    lines = [line for line in output.splitlines() if line]
    if len(lines) != 1 or "\t" not in lines[0]:
        raise V075RemoteMainAnchorInvariantViolation(
            "committed component path lacks one exact tree entry"
        )
    prefix, actual_path = lines[0].split("\t", 1)
    fields = prefix.split()
    if (
        actual_path != repository_path
        or len(fields) != 3
        or fields[1] != "blob"
        or fields[0] not in {"100644", "100755"}
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "committed component tree entry is malformed"
        )
    return _git_oid(fields[2], "component tree blob"), fields[0] == "100755"


_COMPONENT_KEYS = {
    "schema",
    "schema_version",
    "role",
    "repository_path",
    "git_blob_id",
    "bytes_sha256",
    "byte_count",
    "executable",
    "worktree_bytes_equal_index_blob",
    "target_accessed",
    "component_id",
}
_BINDING_KEYS = {
    "schema",
    "schema_version",
    "role",
    "authority_id",
    "independent_verification_id",
    "canonical_artifact_sha256",
    "binding_status",
    "placeholder",
    "target_accessed",
    "binding_id",
}
_COMMITMENT_KEYS = {
    "schema",
    "schema_version",
    "family_generation_id",
    "context_ids",
    "commitment_digest",
    "commitment_scheme",
    "minimum_secret_salt_bytes",
    "secret_salt_serialized",
    "secret_environment_serialized",
    "production_law_serialized",
    "commitment_id",
}
_MANIFEST_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "repository_url",
    "target_branch",
    "family_generation_id",
    "replicate_context_ids",
    "signer_registry_id",
    "opaque_environment_commitment",
    "opaque_environment_commitment_id",
    "component_blobs",
    "component_registry_id",
    "authority_bindings",
    "authority_registry_id",
    "exact_test_command",
    "deterministic_environment",
    "dependency_lock_bound",
    "production_worker_registry_bound",
    "transport_engine_total_lift_reconciliation_endpoint_bound",
    "source_adapter_authority_bound",
    "law_free_public_dependency_graph",
    "private_environment_reveal_serialized",
    "target_accessed",
    "final_preregistration_id_embedded",
    "future_binding_direction",
    "target_execution_allowed",
    "manifest_id",
}
_KEY_KEYS = {
    "schema",
    "schema_version",
    "key_role",
    "algorithm",
    "modulus_hex",
    "public_exponent",
    "minimum_modulus_bits",
    "private_key_serialized",
    "key_id",
}
_REGISTRY_KEYS = {
    "schema",
    "schema_version",
    "campaign_authority_key_id",
    "observer_evidence_key_id",
    "private_keys_serialized",
    "registry_precedes_final_preregistration",
    "final_preregistration_must_bind_registry_id",
    "registry_contains_final_preregistration_id",
    "campaign_authority_key",
    "observer_evidence_key",
    "registry_id",
}
_FINAL_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "repository_url",
    "target_branch",
    "confirmatory_execution_manifest_id",
    "confirmatory_execution_manifest_bytes_sha256",
    "family_generation_id",
    "replicate_context_ids",
    "opaque_environment_commitment_id",
    "signer_registry_id",
    "signer_registry",
    "campaign_authority_public_key_bytes",
    "observer_evidence_public_key_bytes",
    "component_registry_id",
    "authority_registry_id",
    "exact_test_command",
    "manifest_precedes_final_preregistration",
    "manifest_contains_final_preregistration_id",
    "remote_main_anchor_id",
    "observer_open_allowed",
    "registered_target_execution_allowed",
    "official_execution_allowed",
    "target_accessed",
    "final_preregistration_id",
}


def _verify_component_document(
    root: Path,
    commit_id: str,
    value: Any,
    expected_role: str,
    expected_path: str,
) -> dict[str, Any]:
    item = _strict(value, keys=_COMPONENT_KEYS, label="component")
    payload = dict(item)
    claimed_id = _cid(payload.pop("component_id"), "component")
    if (
        item["schema"] != "acfqp.v075_manifest_component_blob.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["role"] != expected_role
        or item["repository_path"] != expected_path
        or item["worktree_bytes_equal_index_blob"] is not True
        or item["target_accessed"] is not False
        or type(item["byte_count"]) is not int
        or item["byte_count"] < 1
        or type(item["executable"]) is not bool
        or _content_id("component_blob", payload) != claimed_id
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "component document is stale or malformed"
        )
    expected_blob, executable = _tree_blob_record(
        root, commit_id, expected_path
    )
    data = _read_blob_at(root, commit_id, expected_path)
    if data is None:
        raise V075RemoteMainAnchorInvariantViolation(
            "component blob is absent"
        )
    if (
        _git_oid(item["git_blob_id"], "component Git blob")
        != expected_blob
        or _cid(item["bytes_sha256"], "component byte digest")
        != hashlib.sha256(data).hexdigest()
        or item["byte_count"] != len(data)
        or item["executable"] is not executable
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "component blob closure differs from the manifest"
        )
    return item


def _verify_binding_document(
    value: Any,
    expected_role: str,
) -> dict[str, Any]:
    item = _strict(value, keys=_BINDING_KEYS, label="authority binding")
    payload = dict(item)
    claimed_id = _cid(payload.pop("binding_id"), "authority binding")
    values = (
        _cid(item["authority_id"], "bound authority"),
        _cid(
            item["independent_verification_id"],
            "authority independent verification",
        ),
        _cid(item["canonical_artifact_sha256"], "authority digest"),
    )
    if (
        item["schema"] != "acfqp.v075_manifest_authority_binding.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["role"] != expected_role
        or item["binding_status"]
        != "CONCRETE_AND_INDEPENDENTLY_VERIFIED"
        or item["placeholder"] is not False
        or item["target_accessed"] is not False
        or len(set(values)) != 3
        or _content_id("authority_binding", payload) != claimed_id
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "authority binding is stale, placeholder, or malformed"
        )
    if not _ROLE_SEMANTIC_VERIFIER_IMPLEMENTED[expected_role]:
        raise V075RemoteMainAnchorInvariantViolation(
            f"{expected_role} per-role semantic verifier is not implemented"
        )
    return item


def _verify_commitment_document(
    value: Any,
    family_generation_id: str,
    context_ids: list[str],
) -> dict[str, Any]:
    item = _strict(
        value,
        keys=_COMMITMENT_KEYS,
        label="opaque environment commitment",
    )
    payload = dict(item)
    claimed_id = _cid(
        payload.pop("commitment_id"),
        "opaque environment commitment",
    )
    if (
        item["schema"]
        != "acfqp.v075_salted_opaque_environment_commitment.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["family_generation_id"] != family_generation_id
        or item["context_ids"] != context_ids
        or _cid(item["commitment_digest"], "opaque commitment digest")
        != item["commitment_digest"]
        or item["commitment_scheme"]
        != (
            "SHA256(domain || NUL || secret_salt || NUL || "
            "canonical_private_reveal)"
        )
        or item["minimum_secret_salt_bytes"] != 32
        or item["secret_salt_serialized"] is not False
        or item["secret_environment_serialized"] is not False
        or item["production_law_serialized"] is not False
        or _content_id("opaque_commitment", payload) != claimed_id
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "opaque environment commitment is malformed or revealing"
        )
    return item


def _verify_manifest(
    root: Path,
    commit_id: str,
    raw: bytes,
) -> dict[str, Any]:
    try:
        parsed = loads_canonical_json(raw)
    except (Phase3EIdentityError, ValueError) as error:
        raise V075RemoteMainAnchorInvariantViolation(
            "manifest bytes are not canonical JSON"
        ) from error
    item = _strict(parsed, keys=_MANIFEST_KEYS, label="execution manifest")
    payload = dict(item)
    manifest_id = _cid(payload.pop("manifest_id"), "execution manifest")
    context_ids = item["replicate_context_ids"]
    if (
        item["schema"]
        != "acfqp.v075_confirmatory_execution_manifest.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"]
        != PROPOSED_CONTRACT_VERSION
        or item["profile_key"]
        != "v075_confirmatory_manifest_preregistration_v1"
        or item["repository_url"] != REPOSITORY_URL
        or item["target_branch"] != TARGET_BRANCH
        or _cid(item["family_generation_id"], "family generation")
        != item["family_generation_id"]
        or type(context_ids) is not list
        or len(context_ids) != 3
        or len(set(context_ids)) != 3
        or any(_cid(value, "replicate context") != value for value in context_ids)
        or _cid(item["signer_registry_id"], "signer registry")
        != item["signer_registry_id"]
        or item["exact_test_command"] != list(EXACT_TEST_COMMAND)
        or item["deterministic_environment"]
        != list(DETERMINISTIC_ENVIRONMENT)
        or item["dependency_lock_bound"] is not True
        or item["production_worker_registry_bound"] is not True
        or item[
            "transport_engine_total_lift_reconciliation_endpoint_bound"
        ]
        is not True
        or item["source_adapter_authority_bound"] is not True
        or item["law_free_public_dependency_graph"] is not True
        or item["private_environment_reveal_serialized"] is not False
        or item["target_accessed"] is not False
        or item["final_preregistration_id_embedded"] is not False
        or item["future_binding_direction"]
        != "MANIFEST_THEN_FINAL_PREREGISTRATION_THEN_REMOTE_MAIN"
        or item["target_execution_allowed"] is not False
        or _content_id("manifest", payload) != manifest_id
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "execution manifest contract or identity changed"
        )
    commitment = _verify_commitment_document(
        item["opaque_environment_commitment"],
        item["family_generation_id"],
        context_ids,
    )
    if (
        item["opaque_environment_commitment_id"]
        != commitment["commitment_id"]
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "manifest commitment reference changed"
        )
    components = item["component_blobs"]
    if (
        type(components) is not list
        or len(components) != len(REQUIRED_COMPONENT_SPECS)
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "manifest component closure is incomplete"
        )
    verified_components = [
        _verify_component_document(root, commit_id, value, role, path)
        for value, (role, path) in zip(
            components, REQUIRED_COMPONENT_SPECS, strict=True
        )
    ]
    if item["component_registry_id"] != _content_id(
        "component_registry",
        {"components": verified_components},
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "component registry ID changed"
        )
    bindings = item["authority_bindings"]
    if (
        type(bindings) is not list
        or len(bindings) != len(REQUIRED_AUTHORITY_ROLE_ORDER)
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "manifest authority registry is incomplete"
        )
    verified_bindings = [
        _verify_binding_document(value, role)
        for value, role in zip(
            bindings, REQUIRED_AUTHORITY_ROLE_ORDER, strict=True
        )
    ]
    if item["authority_registry_id"] != _content_id(
        "authority_registry",
        {"bindings": verified_bindings},
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "authority registry ID changed"
        )
    return item


def _verify_key(
    value: Any,
    expected_role: str,
) -> tuple[dict[str, Any], public_authority.V075RSAPublicVerificationKeyV1]:
    item = _strict(value, keys=_KEY_KEYS, label="RSA public key")
    payload = dict(item)
    key_id = _cid(payload.pop("key_id"), "RSA public key")
    modulus_hex = item["modulus_hex"]
    if (
        item["schema"] != "acfqp.v075_rsa_public_verification_key.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["key_role"] != expected_role
        or item["algorithm"] != "RSASSA-PKCS1-v1_5-SHA256"
        or type(modulus_hex) is not str
        or not modulus_hex
        or modulus_hex.lower() != modulus_hex
        or any(character not in "0123456789abcdef" for character in modulus_hex)
        or modulus_hex.startswith("0")
        or int(modulus_hex, 16).bit_length() < 2_048
        or type(item["public_exponent"]) is not int
        or item["public_exponent"] < 3
        or item["public_exponent"] % 2 == 0
        or item["minimum_modulus_bits"] != 2_048
        or item["private_key_serialized"] is not False
        or _content_id("rsa_public_key", payload) != key_id
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "tracked RSA public key is malformed"
        )
    key = public_authority.V075RSAPublicVerificationKeyV1(
        expected_role,
        int(modulus_hex, 16),
        item["public_exponent"],
    )
    if key.to_document() != item:
        raise V075RemoteMainAnchorInvariantViolation(
            "tracked RSA public key differs from independent reconstruction"
        )
    return item, key


def _verify_registry(
    value: Any,
    campaign_key_bytes_hex: Any,
    observer_key_bytes_hex: Any,
) -> tuple[
    dict[str, Any],
    public_authority.V075TrustedSignerRegistryV1,
]:
    item = _strict(value, keys=_REGISTRY_KEYS, label="signer registry")
    campaign_doc, campaign_key = _verify_key(
        item["campaign_authority_key"], "CAMPAIGN_AUTHORITY"
    )
    observer_doc, observer_key = _verify_key(
        item["observer_evidence_key"], "OBSERVER_EVIDENCE"
    )
    payload = {
        key: item[key]
        for key in (
            "schema",
            "schema_version",
            "campaign_authority_key_id",
            "observer_evidence_key_id",
            "private_keys_serialized",
            "registry_precedes_final_preregistration",
            "final_preregistration_must_bind_registry_id",
            "registry_contains_final_preregistration_id",
        )
    }
    registry_id = _cid(item["registry_id"], "signer registry")
    try:
        campaign_bytes = bytes.fromhex(campaign_key_bytes_hex)
        observer_bytes = bytes.fromhex(observer_key_bytes_hex)
    except (TypeError, ValueError) as error:
        raise V075RemoteMainAnchorInvariantViolation(
            "pinned public-key bytes are malformed"
        ) from error
    if (
        item["schema"] != "acfqp.v075_trusted_signer_registry.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["campaign_authority_key_id"] != campaign_doc["key_id"]
        or item["observer_evidence_key_id"] != observer_doc["key_id"]
        or item["private_keys_serialized"] is not False
        or item["registry_precedes_final_preregistration"] is not True
        or item["final_preregistration_must_bind_registry_id"] is not True
        or item["registry_contains_final_preregistration_id"] is not False
        or campaign_bytes != canonical_json_bytes(campaign_doc)
        or observer_bytes != canonical_json_bytes(observer_doc)
        or _content_id("signer_registry", payload) != registry_id
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "tracked signer registry or pinned key bytes changed"
        )
    registry = public_authority.V075TrustedSignerRegistryV1(
        campaign_key,
        observer_key,
    )
    if registry.to_document() != item:
        raise V075RemoteMainAnchorInvariantViolation(
            "tracked signer registry differs from independent reconstruction"
        )
    return item, registry


def _verify_final(
    raw: bytes,
    manifest: dict[str, Any],
    manifest_raw: bytes,
) -> tuple[
    dict[str, Any],
    public_authority.V075TrustedSignerRegistryV1,
]:
    try:
        parsed = loads_canonical_json(raw)
    except (Phase3EIdentityError, ValueError) as error:
        raise V075RemoteMainAnchorInvariantViolation(
            "final preregistration bytes are not canonical JSON"
        ) from error
    item = _strict(
        parsed,
        keys=_FINAL_KEYS,
        label="final preregistration",
    )
    payload = dict(item)
    final_id = _cid(
        payload.pop("final_preregistration_id"),
        "final preregistration",
    )
    registry_doc, registry = _verify_registry(
        item["signer_registry"],
        item["campaign_authority_public_key_bytes"],
        item["observer_evidence_public_key_bytes"],
    )
    if (
        item["schema"] != "acfqp.v075_final_preregistration.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"]
        != PROPOSED_CONTRACT_VERSION
        or item["profile_key"]
        != "v075_confirmatory_manifest_preregistration_v1"
        or item["repository_url"] != REPOSITORY_URL
        or item["target_branch"] != TARGET_BRANCH
        or item["confirmatory_execution_manifest_id"]
        != manifest["manifest_id"]
        or item["confirmatory_execution_manifest_bytes_sha256"]
        != hashlib.sha256(manifest_raw).hexdigest()
        or item["family_generation_id"]
        != manifest["family_generation_id"]
        or item["replicate_context_ids"]
        != manifest["replicate_context_ids"]
        or item["opaque_environment_commitment_id"]
        != manifest["opaque_environment_commitment_id"]
        or item["signer_registry_id"] != registry_doc["registry_id"]
        or item["signer_registry_id"] != manifest["signer_registry_id"]
        or item["component_registry_id"]
        != manifest["component_registry_id"]
        or item["authority_registry_id"]
        != manifest["authority_registry_id"]
        or item["exact_test_command"] != list(EXACT_TEST_COMMAND)
        or item["manifest_precedes_final_preregistration"] is not True
        or item["manifest_contains_final_preregistration_id"] is not False
        or item["remote_main_anchor_id"] is not None
        or item["observer_open_allowed"] is not False
        or item["registered_target_execution_allowed"] is not False
        or item["official_execution_allowed"] is not False
        or item["target_accessed"] is not False
        or _content_id("final_preregistration", payload) != final_id
        or final_id.encode("ascii") in manifest_raw
        or b"final_preregistration_id" in manifest_raw
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "final preregistration is stale, circular, or malformed"
        )
    return item, registry


def _parents(root: Path, commit_id: str) -> tuple[str, ...]:
    output = _git(root, "show", "-s", "--format=%P", commit_id)
    assert type(output) is str
    if not output:
        return ()
    result = tuple(output.split())
    for value in result:
        _git_oid(value, "parent commit")
    return result


def _all_ancestors(root: Path, commit_id: str) -> tuple[str, ...]:
    parents = _parents(root, commit_id)
    if not parents:
        return ()
    output = _git(root, "rev-list", *parents)
    assert type(output) is str
    values = tuple(dict.fromkeys(output.splitlines()))
    for value in values:
        _git_oid(value, "ancestor commit")
    return values


def _tree_contains_any_sentinel(
    root: Path,
    commit_id: str,
    sentinels: tuple[bytes, ...],
) -> bool:
    output = _git(root, "ls-tree", "-r", commit_id)
    assert type(output) is str
    total = 0
    for line in output.splitlines():
        if not line or "\t" not in line:
            continue
        prefix, path = line.split("\t", 1)
        fields = prefix.split()
        if len(fields) != 3 or fields[1] != "blob":
            continue
        if any(sentinel in path.encode("utf-8") for sentinel in sentinels):
            return True
        size_text = _git(root, "cat-file", "-s", fields[2])
        assert type(size_text) is str
        try:
            size = int(size_text)
        except ValueError as error:
            raise V075RemoteMainAnchorInvariantViolation(
                "ancestor blob size is malformed"
            ) from error
        total += size
        if (
            size > _MAX_SENTINEL_SCAN_BLOB_BYTES
            or total > _MAX_SENTINEL_SCAN_TOTAL_BYTES
        ):
            raise V075RemoteMainAnchorInvariantViolation(
                "ancestor sentinel scan exceeds registered cap"
            )
        data = _git(root, "cat-file", "blob", fields[2], binary=True)
        assert type(data) is bytes
        if any(sentinel in data for sentinel in sentinels):
            return True
    return False


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075RemoteMainAnchorAttestationV1:
    _issuer: object = field(repr=False, compare=False)
    commit_id: str
    tree_id: str
    parent_commit_ids: tuple[str, ...]
    manifest_blob_id: str
    final_preregistration_blob_id: str
    manifest_id: str
    final_preregistration_id: str
    family_generation_id: str
    opaque_environment_commitment_id: str
    observer_profile_id: str
    signer_registry: public_authority.V075TrustedSignerRegistryV1
    component_registry_id: str
    authority_registry_id: str
    _anchor_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.parent_commit_ids) is not tuple
            or type(self.signer_registry)
            is not public_authority.V075TrustedSignerRegistryV1
        ):
            raise V075RemoteMainAnchorInvariantViolation(
                "remote-main attestation is verifier-issued only"
            )
        _git_oid(self.commit_id, "anchor commit")
        _git_oid(self.tree_id, "anchor tree")
        _git_oid(self.manifest_blob_id, "manifest blob")
        _git_oid(
            self.final_preregistration_blob_id,
            "final preregistration blob",
        )
        for value in self.parent_commit_ids:
            _git_oid(value, "anchor parent")
        ids = (
            self.manifest_id,
            self.final_preregistration_id,
            self.family_generation_id,
            self.opaque_environment_commitment_id,
            self.observer_profile_id,
            self.signer_registry.registry_id,
            self.component_registry_id,
            self.authority_registry_id,
        )
        for value in ids:
            _cid(value, "anchor content identity")
        if len(set(ids)) != len(ids):
            raise V075RemoteMainAnchorInvariantViolation(
                "anchor aliases incompatible identity roles"
            )
        object.__setattr__(
            self,
            "_anchor_id",
            _content_id("anchor_attestation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_independent_remote_main_anchor_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "repository_url": REPOSITORY_URL,
            "target_branch": TARGET_BRANCH,
            "remote_tracking_ref": REMOTE_TRACKING_REF,
            "commit_id": self.commit_id,
            "tree_id": self.tree_id,
            "parent_commit_ids": list(self.parent_commit_ids),
            "manifest_blob_id": self.manifest_blob_id,
            "final_preregistration_blob_id": (
                self.final_preregistration_blob_id
            ),
            "manifest_id": self.manifest_id,
            "final_preregistration_id": self.final_preregistration_id,
            "family_generation_id": self.family_generation_id,
            "opaque_environment_commitment_id": (
                self.opaque_environment_commitment_id
            ),
            "observer_profile_id": self.observer_profile_id,
            "signer_registry_id": self.signer_registry.registry_id,
            "campaign_authority_key_id": (
                self.signer_registry.campaign_authority_key.key_id
            ),
            "observer_evidence_key_id": (
                self.signer_registry.observer_evidence_key.key_id
            ),
            "component_registry_id": self.component_registry_id,
            "authority_registry_id": self.authority_registry_id,
            "first_qualifying_origin_main_commit_verified": True,
            "all_ancestors_lack_both_sentinels": True,
            "component_blob_closure_verified": True,
            "registry_and_exact_key_bytes_pinned": True,
            "caller_claims_consumed": 0,
            "registered_observer_calls": 0,
            "target_accessed": False,
            "observer_open_allowed": False,
        }

    @property
    def anchor_id(self) -> str:
        return self._anchor_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "anchor_id": self.anchor_id}


@dataclass(frozen=True, slots=True)
class V075ProductionOpenAuthorityV1:
    """Exact typed capability for a future private V0-075 observer."""

    _issuer: object = field(repr=False, compare=False)
    anchor: V075RemoteMainAnchorAttestationV1
    _authority_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.anchor) is not V075RemoteMainAnchorAttestationV1
        ):
            raise V075RemoteMainAnchorInvariantViolation(
                "production-open authority is independent-verifier-issued only"
            )
        object.__setattr__(
            self,
            "_authority_id",
            _content_id("production_open", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_open_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "remote_main_anchor_id": self.anchor.anchor_id,
            "anchor_commit_id": self.anchor.commit_id,
            "manifest_id": self.anchor.manifest_id,
            "final_preregistration_id": (
                self.anchor.final_preregistration_id
            ),
            "family_generation_id": self.anchor.family_generation_id,
            "opaque_environment_commitment_id": (
                self.anchor.opaque_environment_commitment_id
            ),
            "observer_profile_id": self.anchor.observer_profile_id,
            "signer_registry_id": self.anchor.signer_registry.registry_id,
            "campaign_authority_key_id": (
                self.anchor.signer_registry.campaign_authority_key.key_id
            ),
            "observer_evidence_key_id": (
                self.anchor.signer_registry.observer_evidence_key.key_id
            ),
            "component_registry_id": self.anchor.component_registry_id,
            "authority_registry_id": self.anchor.authority_registry_id,
            "tracked_final_preregistration_verified": True,
            "first_qualifying_origin_main_anchor_verified": True,
            "registry_exact_key_bytes_verified": True,
            "manifest_component_closure_verified": True,
            "observer_open_allowed": True,
            "target_access_performed": False,
        }

    @property
    def authority_id(self) -> str:
        return self._authority_id

    @property
    def signer_registry(
        self,
    ) -> public_authority.V075TrustedSignerRegistryV1:
        return self.anchor.signer_registry

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "authority_id": self.authority_id}


def verify_v075_remote_main_anchor_independently_v1(
    repository_root: str | os.PathLike[str],
) -> V075RemoteMainAnchorAttestationV1:
    """Derive the anchor from Git objects; accepts no expected IDs or claims."""

    root = Path(repository_root).resolve(strict=True)
    if not root.joinpath(".git").exists():
        raise V075ProductionOpenAuthorityNotReady(
            "repository root is not a Git worktree"
        )
    origin_url = _git(root, "remote", "get-url", "origin")
    push_url = _git(root, "remote", "get-url", "--push", "origin")
    if origin_url != REPOSITORY_URL or push_url != REPOSITORY_URL:
        raise V075ProductionOpenAuthorityNotReady(
            "origin fetch/push URL is not the registered production remote"
        )
    remote_head = _git(root, "rev-parse", "--verify", REMOTE_TRACKING_REF)
    local_head = _git(root, "rev-parse", "--verify", LOCAL_BRANCH_REF)
    worktree_head = _git(root, "rev-parse", "--verify", "HEAD")
    assert (
        type(remote_head) is str
        and type(local_head) is str
        and type(worktree_head) is str
    )
    if not hmac.compare_digest(remote_head, local_head) or not hmac.compare_digest(
        remote_head, worktree_head
    ):
        raise V075ProductionOpenAuthorityNotReady(
            "HEAD, local main, and origin/main are not identical"
        )
    _git_oid(remote_head, "origin/main commit")
    history = _git(
        root,
        "rev-list",
        "--reverse",
        "--topo-order",
        REMOTE_TRACKING_REF,
    )
    assert type(history) is str

    qualifying: tuple[
        str,
        bytes,
        bytes,
        dict[str, Any],
        dict[str, Any],
        public_authority.V075TrustedSignerRegistryV1,
    ] | None = None
    for commit_id in history.splitlines():
        manifest_raw = _read_blob_at(
            root, commit_id, MANIFEST_REPOSITORY_PATH
        )
        final_raw = _read_blob_at(
            root, commit_id, FINAL_PREREGISTRATION_REPOSITORY_PATH
        )
        if manifest_raw is None or final_raw is None:
            continue
        try:
            manifest = _verify_manifest(root, commit_id, manifest_raw)
            final, registry = _verify_final(
                final_raw, manifest, manifest_raw
            )
        except V075RemoteMainAnchorInvariantViolation:
            continue
        qualifying = (
            commit_id,
            manifest_raw,
            final_raw,
            manifest,
            final,
            registry,
        )
        break
    if qualifying is None:
        raise V075ProductionOpenAuthorityNotReady(
            "no complete qualifying origin/main commit exists"
        )

    (
        commit_id,
        manifest_raw,
        final_raw,
        manifest,
        final,
        registry,
    ) = qualifying
    sentinels = (
        final["final_preregistration_id"].encode("ascii"),
        manifest["family_generation_id"].encode("ascii"),
    )
    ancestors = _all_ancestors(root, commit_id)
    if any(
        _tree_contains_any_sentinel(root, ancestor, sentinels)
        for ancestor in ancestors
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "an ancestor already contains a final-preregistration or "
            "family-generation sentinel"
        )

    # The current remote tree must retain the exact qualifying artifacts and
    # exact component closure; a later stale replacement cannot inherit the
    # earlier anchor.
    current_manifest_raw = _read_blob_at(
        root, remote_head, MANIFEST_REPOSITORY_PATH
    )
    current_final_raw = _read_blob_at(
        root, remote_head, FINAL_PREREGISTRATION_REPOSITORY_PATH
    )
    if (
        current_manifest_raw != manifest_raw
        or current_final_raw != final_raw
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "origin/main authority blobs differ from the first qualifying commit"
        )
    current_manifest = _verify_manifest(
        root, remote_head, current_manifest_raw
    )
    current_final, current_registry = _verify_final(
        current_final_raw,
        current_manifest,
        current_manifest_raw,
    )
    if (
        current_manifest != manifest
        or current_final != final
        or current_registry != registry
    ):
        raise V075RemoteMainAnchorInvariantViolation(
            "origin/main semantic authority differs from the anchor"
        )

    tree_id = _git(root, "show", "-s", "--format=%T", commit_id)
    assert type(tree_id) is str
    manifest_blob_id, _ = _tree_blob_record(
        root, commit_id, MANIFEST_REPOSITORY_PATH
    )
    final_blob_id, _ = _tree_blob_record(
        root, commit_id, FINAL_PREREGISTRATION_REPOSITORY_PATH
    )
    return V075RemoteMainAnchorAttestationV1(
        _ISSUER,
        _git_oid(commit_id, "anchor commit"),
        _git_oid(tree_id, "anchor tree"),
        _parents(root, commit_id),
        manifest_blob_id,
        final_blob_id,
        manifest["manifest_id"],
        final["final_preregistration_id"],
        manifest["family_generation_id"],
        manifest["opaque_environment_commitment_id"],
        next(
            item["authority_id"]
            for item in manifest["authority_bindings"]
            if item["role"] == "OBSERVER_PROFILE"
        ),
        registry,
        manifest["component_registry_id"],
        manifest["authority_registry_id"],
    )


def verify_and_mint_v075_production_open_authority_v1(
    repository_root: str | os.PathLike[str],
) -> V075ProductionOpenAuthorityV1:
    """Mint the sole typed observer-open input after complete Git replay."""

    anchor = verify_v075_remote_main_anchor_independently_v1(
        repository_root
    )
    return V075ProductionOpenAuthorityV1(_ISSUER, anchor)


__all__ = [
    "FINAL_PREREGISTRATION_REPOSITORY_PATH",
    "MANIFEST_REPOSITORY_PATH",
    "PROFILE_KEY",
    "REMOTE_TRACKING_REF",
    "REPOSITORY_URL",
    "REQUIRED_AUTHORITY_ROLE_ORDER",
    "REQUIRED_COMPONENT_SPECS",
    "SCHEMA_VERSION",
    "TARGET_BRANCH",
    "V075ProductionOpenAuthorityNotReady",
    "V075ProductionOpenAuthorityV1",
    "V075RemoteMainAnchorAttestationV1",
    "V075RemoteMainAnchorInvariantViolation",
    "verify_and_mint_v075_production_open_authority_v1",
    "verify_v075_remote_main_anchor_independently_v1",
]
