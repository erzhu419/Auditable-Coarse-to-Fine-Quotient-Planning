#!/usr/bin/env python3
"""Source-only controller for V0-075 source-work replay/materialization.

The registered V0-072 replay is expensive, so this controller separates a
fast immutable-snapshot preflight from the explicit replay operation.  The
preflight imports no ACFQP package code and opens no target data.  It checks:

* one clean detached worktree at the exact registered commit and tree;
* the exact canonical source-reconstruction recipe bytes and identity;
* the frozen test/runtime specifications and their content identities; and
* the active interpreter executable/build identity needed by that recipe.

The historical recipe's generic freeze helper lazily imports the V0-072
confirmatory manifest.  That manifest's component tree includes target and
held-out modules, so this controller does not call that helper.  Instead it
runs only the registered V0-068 source constructor/verifier and source
archive authorities, then independently checks the frozen recipe inputs,
expected output identities, ordered commitments, and compact artifacts.

The exact historical replay object remains alive while digest-bound current
V0-075 materializer code is dynamically loaded into the same process.  An
import guard rejects every target/held-out/confirmatory-manifest module.  The
command line accepts no counter document, pickle, expected identity, target
input, caller runner, worker override, or reduced-work override.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from importlib import abc as importlib_abc
from importlib import import_module
from importlib import util as importlib_util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
from types import ModuleType
from typing import Any, Iterator, Mapping, Protocol, Sequence


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v075_source_replay_materialization_controller_v1"
REQUIRED_SOURCE_REPLAY_COMMIT = (
    "63cc0f5f78f64b7845319d1c1a5856212e3b8097"
)
REQUIRED_SOURCE_REPLAY_TREE = (
    "8c88ef5e2747267a309834d155136c40ba926b61"
)
REQUIRED_SOURCE_RECIPE_ID = (
    "7f6cebc1edf2bf007ae63a165866b8a3e6c6c4cb47b23a120eb1fa874be1e1d1"
)
REQUIRED_SOURCE_RECIPE_BYTES_SHA256 = (
    "041d52af80d56de3d427c8d44a3048d77521f15da9dcbc476659fd7724c6c76b"
)

RECIPE_PATH = "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json"
TEST_SPEC_PATH = "specs/V072_CONFIRMATORY_TEST_COMMAND.json"
RUNTIME_SPEC_PATH = "specs/V072_RUNTIME_DEPENDENCY_LOCK.json"
RECIPE_IMPLEMENTATION_PATH = (
    "src/acfqp/v072_source_reconstruction_recipe_v1.py"
)
CONFIRMATORY_MANIFEST_PATH = (
    "src/acfqp/v072_confirmatory_execution_manifest_v1.py"
)
REQUIRED_COMPONENT_TREE_DIGEST = (
    "6d7162892046ff0080bd9df1440a950af978df0d8c9f3e44206db1719bda73d7"
)

CURRENT_PINNED_CODE_PATHS = (
    "scripts/replay_and_materialize_v075_source_work.py",
    "src/acfqp/v075_frozen_source_proposal_archive_v1.py",
    "src/acfqp/v075_source_offline_work_materializer_v1.py",
)

PRODUCTION_REPLAY_STATUS = "NOT_RUN"
PRODUCTION_MATERIALIZATION_STATUS = "NOT_RUN"
STATUS_FILENAME = "v075_source_replay_materialization_status_v1.json"
MATERIALIZATION_FILENAME = (
    "v075_source_offline_work_materialization_v1.json"
)
VERIFICATION_FILENAME = (
    "v075_source_offline_work_materialization_verification_v1.json"
)

TEST_COMMAND_DOMAIN = (
    "acfqp:v072-confirmatory-test-command-manifest:v1"
)
RUNTIME_LOCK_DOMAIN = "acfqp:v072-runtime-dependency-lock:v1"
INTERPRETER_BUILD_DOMAIN = (
    "acfqp:v072-interpreter-build-identity:v1"
)
ENVIRONMENT_ATTESTATION_DOMAIN = (
    "acfqp:v072-execution-environment-independent-attestation:v1"
)
RECIPE_DOMAIN = "acfqp:v072-source-reconstruction-recipe:v1"

DOMAIN_TAGS = {
    "snapshot_preflight": (
        "acfqp:v075-source-replay-snapshot-preflight:v1"
    ),
    "controller_code_manifest": (
        "acfqp:v075-source-replay-controller-code-manifest:v1"
    ),
    "blocker_evidence": (
        "acfqp:v075-source-replay-import-closure-blocker-evidence:v1"
    ),
    "source_only_bypass": (
        "acfqp:v075-source-only-replay-bypass-evidence:v1"
    ),
    "source_only_readiness": (
        "acfqp:v075-source-only-replay-readiness:v1"
    ),
    "source_graph_verification": (
        "acfqp:v075-source-only-replayed-graph-verification:v1"
    ),
    "status": (
        "acfqp:v075-source-replay-materialization-status:v1"
    ),
    "injected_protocol": (
        "acfqp:v075-source-replay-injected-protocol:v1"
    ),
}

_FORBIDDEN_TARGET_REGISTRY_PATHS = (
    "src/acfqp/v072_registered_target_selector_v1.py",
    "src/acfqp/heldout_graph_transition_observer_v2.py",
)
_FORBIDDEN_ACFQP_MODULE_MARKERS = (
    "heldout",
    "target",
)
_FORBIDDEN_ACFQP_MODULE_NAMES = frozenset(
    {
        "acfqp.v072_confirmatory_execution_manifest_v1",
    }
)
_HISTORICAL_SOURCE_MODULE_NAMES = (
    "acfqp.observation_support_campaign_v1",
    "acfqp.verified_source_acquisition_archive_v2",
    (
        "acfqp."
        "verified_source_acquisition_archive_independent_verifier_v2"
    ),
    "acfqp.v072_verified_source_archive_component_v1",
    "acfqp.v072_source_reconstruction_recipe_v1",
)
_CURRENT_DYNAMIC_MODULE_PATHS = (
    "src/acfqp/v075_frozen_source_proposal_archive_v1.py",
    "src/acfqp/v075_source_offline_work_materializer_v1.py",
)
_SOURCE_ONLY_ACFQP_IMPORT_ALLOWLIST = (
    "acfqp",
    "acfqp.artifacts",
    "acfqp.build_coverage",
    "acfqp.core",
    "acfqp.enumeration",
    "acfqp.observation_support_campaign_v1",
    "acfqp.observation_support_coordinate_refinement_v1",
    "acfqp.observation_support_exact_evaluation_v1",
    "acfqp.observation_support_graph_acquisition_v1",
    "acfqp.observation_support_graph_model_v1",
    "acfqp.observation_support_grouped_replay_v1",
    "acfqp.observation_support_h2_closure_v1",
    "acfqp.observation_support_promoted_h2_consumer_v1",
    "acfqp.observation_support_relational_adapter_v1",
    "acfqp.partial_support_confidence_v1",
    "acfqp.partial_support_expansion_authority_v1",
    "acfqp.partial_support_family_confidence_v1",
    "acfqp.partial_support_robust_planner_v1",
    "acfqp.phase3e_ids",
    "acfqp.portable_relational_skeleton_v1",
    "acfqp.relational_graph_core_v1",
    "acfqp.sequential_bernoulli_acquisition_v1",
    "acfqp.transition_tuple_observer_v1",
    "acfqp.v072_execution_environment_authority_v1",
    "acfqp.v072_execution_environment_independent_verifier_v1",
    "acfqp.v072_source_reconstruction_recipe_v1",
    "acfqp.v072_verified_source_archive_component_v1",
    "acfqp.v075_frozen_source_proposal_archive_v1",
    "acfqp.v075_source_offline_work_materializer_v1",
    "acfqp.verified_source_acquisition_archive_independent_verifier_v2",
    "acfqp.verified_source_acquisition_archive_v2",
)
_SOURCE_ONLY_IMPORT_ALLOWLIST_DOMAIN = (
    b"acfqp:v075-source-only-import-allowlist:v1\x00"
)
_SOURCE_ONLY_IMPORT_ALLOWLIST_ID = (
    "5331c095db4e0c97a0706e95861bdaa5c2f388995ee1b5b5ea8165ab339b5614"
)
_MERKLE_LEAF_DOMAIN = b"acfqp:v072-source-recipe-merkle-leaf:v1\x00"
_MERKLE_NODE_DOMAIN = b"acfqp:v072-source-recipe-merkle-node:v1\x00"
_ID_LENGTH = 64


class V075SourceReplayControllerViolation(RuntimeError):
    """The snapshot, replay protocol, or exclusive output is invalid."""


def _fail(message: str) -> None:
    raise V075SourceReplayControllerViolation(message)


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise V075SourceReplayControllerViolation(
            "controller document is not canonical-JSON serializable"
        ) from error


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + _canonical_json_bytes(dict(payload))
    ).hexdigest()


def _role_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
    except KeyError as error:
        raise V075SourceReplayControllerViolation(
            "unknown controller content-ID role"
        ) from error
    return _content_id(domain, payload)


def _require_id(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) != _ID_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field_name} is not one lowercase SHA-256 identity")
    return value


def _safe_repo_path(root: Path, relative_text: str) -> Path:
    if (
        type(relative_text) is not str
        or not relative_text
        or "\\" in relative_text
        or "\x00" in relative_text
    ):
        _fail("repository-relative evidence path is not canonical")
    relative = PurePosixPath(relative_text)
    if (
        relative.is_absolute()
        or str(relative) != relative_text
        or any(part in ("", ".", "..") for part in relative.parts)
    ):
        _fail("repository-relative evidence path escapes its root")
    candidate = root.joinpath(*relative.parts)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            _fail("repository evidence path contains a symlink")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as error:
        raise V075SourceReplayControllerViolation(
            "repository evidence path is missing or escapes its root"
        ) from error
    return resolved


def _read_regular(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise V075SourceReplayControllerViolation(
            "controller evidence cannot be opened without following links"
        ) from error
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            _fail("controller evidence is not one regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def _strict_json_object(raw: bytes, role: str) -> dict[str, Any]:
    try:
        document = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                V075SourceReplayControllerViolation(
                    f"{role} contains non-finite JSON token {token}"
                )
            ),
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        V075SourceReplayControllerViolation,
    ) as error:
        raise V075SourceReplayControllerViolation(
            f"{role} is not strict canonical JSON"
        ) from error
    if type(document) is not dict:
        _fail(f"{role} is not one JSON object")
    return document


def _strict_canonical_object(raw: bytes, role: str) -> dict[str, Any]:
    document = _strict_json_object(raw, role)
    if _canonical_json_bytes(document) != raw:
        _fail(f"{role} is not one canonical JSON object")
    return document


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate canonical JSON key: {key}")
        result[key] = value
    return result


def _git(
    root: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            ("git", "-C", str(root), *arguments),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise V075SourceReplayControllerViolation(
            "git is unavailable for immutable snapshot verification"
        ) from error
    if check and result.returncode != 0:
        _fail("git rejected immutable snapshot verification")
    return result


def _one_git_line(root: Path, *arguments: str) -> str:
    result = _git(root, *arguments)
    try:
        value = result.stdout.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError as error:
        raise V075SourceReplayControllerViolation(
            "git snapshot identity is not ASCII"
        ) from error
    if not value or "\n" in value or "\r" in value:
        _fail("git returned a noncanonical snapshot identity")
    return value


def _absolute_real_directory(value: str | os.PathLike[str]) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute() or candidate.is_symlink():
        _fail("snapshot root must be one absolute non-symlink directory")
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as error:
        raise V075SourceReplayControllerViolation(
            "snapshot root does not exist"
        ) from error
    if resolved != candidate or not resolved.is_dir():
        _fail("snapshot root contains a symlink or is not a directory")
    return resolved


def _verify_embedded_content_id(
    document: dict[str, Any],
    *,
    field_name: str,
    domain: str,
) -> str:
    claimed = _require_id(document.get(field_name), field_name)
    payload = dict(document)
    payload.pop(field_name)
    if _content_id(domain, payload) != claimed:
        _fail(f"{field_name} differs from canonical specification bytes")
    return claimed


def _verify_frozen_recipe_and_environment(
    root: Path,
) -> dict[str, Any]:
    recipe_raw = _read_regular(_safe_repo_path(root, RECIPE_PATH))
    if (
        hashlib.sha256(recipe_raw).hexdigest()
        != REQUIRED_SOURCE_RECIPE_BYTES_SHA256
    ):
        _fail("registered source recipe raw bytes changed")
    recipe = _strict_canonical_object(recipe_raw, "source recipe")
    recipe_id = _verify_embedded_content_id(
        recipe,
        field_name="recipe_id",
        domain=RECIPE_DOMAIN,
    )
    if recipe_id != REQUIRED_SOURCE_RECIPE_ID:
        _fail("registered source recipe identity changed")
    if recipe.get("replay_ready") is not True:
        _fail("registered source recipe is not replay-ready")

    test_raw = _read_regular(_safe_repo_path(root, TEST_SPEC_PATH))
    runtime_raw = _read_regular(_safe_repo_path(root, RUNTIME_SPEC_PATH))
    # These two legacy V0-072 specifications are intentionally rendered as
    # indented JSON with a final newline.  Their exact raw-byte digests are
    # bound by the independent environment attestation below; their semantic
    # IDs are still recomputed from canonical payload JSON.
    test_spec = _strict_json_object(
        test_raw,
        "frozen test-command specification",
    )
    runtime_spec = _strict_json_object(
        runtime_raw,
        "frozen runtime-lock specification",
    )
    test_id = _verify_embedded_content_id(
        test_spec,
        field_name="test_command_manifest_id",
        domain=TEST_COMMAND_DOMAIN,
    )
    runtime_id = _verify_embedded_content_id(
        runtime_spec,
        field_name="runtime_dependency_lock_id",
        domain=RUNTIME_LOCK_DOMAIN,
    )
    interpreter = runtime_spec.get("interpreter_build_identity")
    if type(interpreter) is not dict:
        _fail("runtime lock omits its interpreter build identity")
    interpreter_id = _verify_embedded_content_id(
        interpreter,
        field_name="interpreter_build_identity_id",
        domain=INTERPRETER_BUILD_DOMAIN,
    )

    inputs = recipe.get("reconstruction_inputs")
    if (
        type(inputs) is not dict
        or inputs.get("test_command_manifest_id") != test_id
        or inputs.get("runtime_dependency_lock_id") != runtime_id
        or inputs.get("interpreter_build_identity_id") != interpreter_id
    ):
        _fail("recipe and frozen environment specifications diverge")

    attestation_payload = {
        "schema": (
            "acfqp.v072_execution_environment_independent_attestation.v1"
        ),
        "schema_version": "1.0.0",
        "profile_key": (
            "v072_execution_environment_independent_verifier_v1"
        ),
        "test_command_manifest_id": test_id,
        "runtime_dependency_lock_id": runtime_id,
        "interpreter_build_identity_id": interpreter_id,
        "test_spec_sha256": hashlib.sha256(test_raw).hexdigest(),
        "runtime_spec_sha256": hashlib.sha256(runtime_raw).hexdigest(),
        "production_builder_called": False,
        "caller_supplied_digest_accepted": False,
        "caller_supplied_status_accepted": False,
        "target_access": False,
    }
    attestation_id = _content_id(
        ENVIRONMENT_ATTESTATION_DOMAIN,
        attestation_payload,
    )
    if inputs.get("environment_independent_attestation_id") != attestation_id:
        _fail("recipe environment attestation identity changed")

    executable = interpreter.get("executable")
    if type(executable) is not dict:
        _fail("runtime lock omits the interpreter executable record")
    active_executable = Path(sys.executable).resolve(strict=True)
    active_executable_raw = _read_regular(active_executable)
    if (
        executable.get("file_byte_count") != len(active_executable_raw)
        or executable.get("sha256_file_bytes")
        != hashlib.sha256(active_executable_raw).hexdigest()
        or interpreter.get("implementation_cache_tag")
        != sys.implementation.cache_tag
        or interpreter.get("implementation_name")
        != sys.implementation.name
        or interpreter.get("sys_version") != sys.version
        or interpreter.get("maxsize") != sys.maxsize
    ):
        _fail("active interpreter differs from the frozen source interpreter")

    return {
        "source_recipe_id": recipe_id,
        "source_recipe_bytes_sha256": hashlib.sha256(recipe_raw).hexdigest(),
        "test_command_manifest_id": test_id,
        "runtime_dependency_lock_id": runtime_id,
        "interpreter_build_identity_id": interpreter_id,
        "environment_independent_attestation_id": attestation_id,
        "active_interpreter_executable_sha256": hashlib.sha256(
            active_executable_raw
        ).hexdigest(),
        "canonical_recipe_checked": True,
        "frozen_environment_spec_identities_checked": True,
        "active_interpreter_checked": True,
        "full_environment_reconstruction_run": False,
        "target_access": False,
    }


def _static_source_only_bypass_evidence(root: Path) -> dict[str, Any]:
    recipe_source = _read_regular(
        _safe_repo_path(root, RECIPE_IMPLEMENTATION_PATH)
    )
    manifest_source = _read_regular(
        _safe_repo_path(root, CONFIRMATORY_MANIFEST_PATH)
    )
    try:
        tree = ast.parse(recipe_source.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, SyntaxError) as error:
        raise V075SourceReplayControllerViolation(
            "registered source recipe implementation cannot be audited"
        ) from error
    imports_manifest = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "acfqp"
        and any(
            alias.name == "v072_confirmatory_execution_manifest_v1"
            for alias in node.names
        )
        for node in ast.walk(tree)
    )
    exposed = tuple(
        value
        for value in _FORBIDDEN_TARGET_REGISTRY_PATHS
        if value.encode("utf-8") in manifest_source
    )
    if not imports_manifest or exposed != _FORBIDDEN_TARGET_REGISTRY_PATHS:
        _fail("registered source-only bypass evidence changed")
    payload = {
        "schema": "acfqp.v075_source_only_replay_bypass_evidence.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "recipe_implementation_path": RECIPE_IMPLEMENTATION_PATH,
        "recipe_implementation_sha256": hashlib.sha256(
            recipe_source
        ).hexdigest(),
        "confirmatory_manifest_path": CONFIRMATORY_MANIFEST_PATH,
        "confirmatory_manifest_sha256": hashlib.sha256(
            manifest_source
        ).hexdigest(),
        "manifest_import_reachable_from_exact_replay": True,
        "generic_recipe_freeze_helper_called": False,
        "source_only_independent_graph_check_required": True,
        "confirmatory_manifest_import_forbidden": True,
        "forbidden_target_registry_paths": list(exposed),
        "source_child_launched": False,
        "sample_draws_started": False,
        "target_access": False,
    }
    return {**payload, "source_only_bypass_evidence_id": _role_id(
        "source_only_bypass",
        payload,
    )}


def verify_snapshot_preflight_v1(
    snapshot_root: str | os.PathLike[str],
) -> dict[str, Any]:
    root = _absolute_real_directory(snapshot_root)
    top = Path(
        _one_git_line(root, "rev-parse", "--show-toplevel")
    ).resolve(strict=True)
    if top != root:
        _fail("snapshot path is not the Git worktree root")
    commit = _one_git_line(root, "rev-parse", "HEAD")
    tree = _one_git_line(root, "rev-parse", "HEAD^{tree}")
    if (
        commit != REQUIRED_SOURCE_REPLAY_COMMIT
        or tree != REQUIRED_SOURCE_REPLAY_TREE
    ):
        _fail("snapshot commit/tree differs from the registered replay")
    branch = _git(root, "symbolic-ref", "-q", "HEAD", check=False)
    if branch.returncode == 0:
        _fail("source replay snapshot must have detached HEAD")
    if branch.returncode != 1:
        _fail("Git could not prove detached HEAD")
    status = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if status.stdout:
        _fail("source replay snapshot is not clean")

    frozen = _verify_frozen_recipe_and_environment(root)
    bypass = _static_source_only_bypass_evidence(root)
    payload = {
        "schema": "acfqp.v075_source_replay_snapshot_preflight.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "snapshot_root": str(root),
        "required_commit": REQUIRED_SOURCE_REPLAY_COMMIT,
        "observed_commit": commit,
        "required_tree": REQUIRED_SOURCE_REPLAY_TREE,
        "observed_tree": tree,
        "git_worktree_root_exact": True,
        "detached_head": True,
        "clean_worktree": True,
        "frozen_recipe_environment": frozen,
        "source_only_bypass_evidence_id": (
            bypass["source_only_bypass_evidence_id"]
        ),
        "production_replay_eligible": True,
        "generic_recipe_freeze_helper_allowed": False,
        "source_only_replay_required": True,
        "source_child_launched": False,
        "sample_draws_started": False,
        "target_access": False,
    }
    return {
        **payload,
        "preflight_id": _role_id("snapshot_preflight", payload),
        "source_only_bypass_evidence": bypass,
    }


def _current_repository_root() -> Path:
    root = Path(__file__).resolve().parents[1]
    if root.is_symlink() or not root.is_dir():
        _fail("current V0-075 code root is not one real directory")
    return root


def freeze_controller_code_manifest_v1() -> dict[str, Any]:
    root = _current_repository_root()
    commit = _one_git_line(root, "rev-parse", "HEAD")
    tree = _one_git_line(root, "rev-parse", "HEAD^{tree}")
    files: list[dict[str, Any]] = []
    for relative in CURRENT_PINNED_CODE_PATHS:
        raw = _read_regular(_safe_repo_path(root, relative))
        files.append(
            {
                "repository_relative_path": relative,
                "file_byte_count": len(raw),
                "sha256_file_bytes": hashlib.sha256(raw).hexdigest(),
            }
        )
    relevant_status = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *CURRENT_PINNED_CODE_PATHS,
    ).stdout
    tracked_result = _git(
        root,
        "ls-files",
        "--error-unmatch",
        "--",
        *CURRENT_PINNED_CODE_PATHS,
        check=False,
    )
    tracked_paths = tuple(
        line
        for line in tracked_result.stdout.decode(
            "utf-8",
            errors="strict",
        ).splitlines()
        if line
    )
    all_paths_tracked = (
        tracked_result.returncode == 0
        and set(tracked_paths) == set(CURRENT_PINNED_CODE_PATHS)
    )
    payload = {
        "schema": "acfqp.v075_source_replay_controller_code_manifest.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "repository_commit": commit,
        "repository_tree": tree,
        "files": files,
        "relevant_git_status_sha256": hashlib.sha256(
            relevant_status
        ).hexdigest(),
        "relevant_paths_clean": relevant_status == b"",
        "all_paths_tracked": all_paths_tracked,
        "tracked_paths": list(sorted(tracked_paths)),
        "dynamic_current_code_loading_required_after_replay": True,
        "same_process_materialization_required": True,
        "target_access": False,
    }
    return {
        **payload,
        "controller_code_manifest_id": _role_id(
            "controller_code_manifest",
            payload,
        ),
    }


def _require_production_code_manifest_v1(
    code_manifest: Mapping[str, Any],
) -> None:
    payload = dict(code_manifest)
    claimed_id = payload.pop("controller_code_manifest_id", None)
    if (
        claimed_id != _role_id("controller_code_manifest", payload)
        or code_manifest.get("schema")
        != "acfqp.v075_source_replay_controller_code_manifest.v1"
        or code_manifest.get("profile_key") != PROFILE_KEY
        or code_manifest.get("relevant_paths_clean") is not True
        or code_manifest.get("all_paths_tracked") is not True
        or code_manifest.get("tracked_paths")
        != list(sorted(CURRENT_PINNED_CODE_PATHS))
        or code_manifest.get("relevant_git_status_sha256")
        != hashlib.sha256(b"").hexdigest()
    ):
        _fail(
            "production source replay requires tracked, clean current "
            "controller/archive/materializer paths"
        )


def _is_forbidden_acfqp_module(fullname: str) -> bool:
    if fullname in _FORBIDDEN_ACFQP_MODULE_NAMES:
        return True
    if not fullname.startswith("acfqp."):
        return False
    leaf = fullname.rsplit(".", 1)[-1].lower()
    return any(marker in leaf for marker in _FORBIDDEN_ACFQP_MODULE_MARKERS)


class _SourceOnlyImportGuard(importlib_abc.MetaPathFinder):
    def __init__(self) -> None:
        self.denied_attempts: list[str] = []

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: ModuleType | None = None,
    ) -> None:
        del path, target
        if _is_forbidden_acfqp_module(fullname):
            self.denied_attempts.append(fullname)
            raise ImportError(
                f"source-only replay denied forbidden module {fullname}"
            )
        return None


@contextmanager
def _isolated_historical_acfqp_runtime(
    snapshot_root: Path,
) -> Iterator[_SourceOnlyImportGuard]:
    """Temporarily make the detached snapshot the only ACFQP import root."""

    source_root = _safe_repo_path(snapshot_root, "src")
    stashed = {
        name: module
        for name, module in tuple(sys.modules.items())
        if name == "acfqp" or name.startswith("acfqp.")
    }
    for name in stashed:
        del sys.modules[name]
    original_path = list(sys.path)
    guard = _SourceOnlyImportGuard()
    sys.path.insert(0, str(source_root))
    sys.meta_path.insert(0, guard)
    try:
        yield guard
    finally:
        if guard in sys.meta_path:
            sys.meta_path.remove(guard)
        sys.path[:] = original_path
        for name in tuple(sys.modules):
            if name == "acfqp" or name.startswith("acfqp."):
                del sys.modules[name]
        sys.modules.update(stashed)


def _import_historical_source_recipe_v1() -> ModuleType:
    module = import_module("acfqp.v072_source_reconstruction_recipe_v1")
    if module.__name__ != "acfqp.v072_source_reconstruction_recipe_v1":
        _fail("historical source recipe import was role-confused")
    return module


def _load_historical_recipe_v1(
    root: Path,
    recipe_module: ModuleType,
) -> Any:
    recipe = recipe_module.load_source_reconstruction_recipe_v1(
        str(_safe_repo_path(root, RECIPE_PATH))
    )
    if (
        type(recipe) is not recipe_module.SourceReconstructionRecipeV1
        or recipe.recipe_id != REQUIRED_SOURCE_RECIPE_ID
        or recipe.replay_ready is not True
    ):
        _fail("historical source recipe did not load as the exact ready type")
    return recipe


def _registered_source_inputs_v1(
    *,
    recipe_module: ModuleType,
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    campaign = recipe_module.campaign_v1
    archive = recipe_module.archive_v2
    frozen = preflight["frozen_recipe_environment"]
    return {
        "constructor": recipe_module.REGISTERED_CONSTRUCTOR,
        "verifier": recipe_module.REGISTERED_VERIFIER,
        "max_workers": recipe_module.RECONSTRUCTION_MAX_WORKERS,
        "registered_context_order": list(campaign.REGISTERED_CONTEXT_ORDER),
        "registered_context_documents": [
            item.to_document()
            for item in campaign.observer.registered_public_graph_contexts_v1()
        ],
        "registered_checkpoints": list(campaign.REGISTERED_CHECKPOINTS),
        "registered_adjacent_pairs": [
            {
                "context_key": key,
                "checkpoint_pairs": [list(pair) for pair in pairs],
            }
            for key, pairs in archive.REGISTERED_ADJACENT_PAIRS.items()
        ],
        "discovery_draw_count": (
            recipe_module.acquisition_v1.DISCOVERY_DRAW_COUNT
        ),
        "randomness_implementation": campaign.RANDOMNESS_IMPLEMENTATION,
        # The complete historical component tree contains target modules.
        # Its already-frozen digest is checked from the exact recipe bytes,
        # never recomputed in this source-only process.
        "component_tree_digest": REQUIRED_COMPONENT_TREE_DIGEST,
        "test_command_manifest_id": frozen["test_command_manifest_id"],
        "runtime_dependency_lock_id": frozen["runtime_dependency_lock_id"],
        "interpreter_build_identity_id": (
            frozen["interpreter_build_identity_id"]
        ),
        "environment_independent_attestation_id": (
            frozen["environment_independent_attestation_id"]
        ),
    }


def _verify_registered_source_inputs_v1(
    *,
    recipe: Any,
    recipe_module: ModuleType,
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    document = recipe.to_document()
    expected = _registered_source_inputs_v1(
        recipe_module=recipe_module,
        preflight=preflight,
    )
    if (
        document.get("recipe_id") != REQUIRED_SOURCE_RECIPE_ID
        or document.get("reconstruction_inputs") != expected
        or document.get("replay_ready") is not True
        or document.get("source_graph_commitment_complete") is not True
        or document.get("replay_blocker") is not None
        or document.get("raw_observation_ids_persisted") is not False
        or document.get("caller_supplied_expected_ids_accepted") is not False
        or document.get("caller_supplied_runner_accepted") is not False
        or document.get("official_execution_allowed") is not False
    ):
        _fail("registered source-only recipe inputs or claim scope changed")
    return document


def _ordered_merkle_commitment_v1(
    values: Sequence[str],
    *,
    role: str,
) -> dict[str, Any]:
    if type(values) not in (tuple, list):
        _fail(f"{role} values are not one ordered sequence")
    ordered = tuple(_require_id(value, role) for value in values)
    leaves = [
        hashlib.sha256(
            _MERKLE_LEAF_DOMAIN
            + role.encode("utf-8")
            + b"\x00"
            + index.to_bytes(8, "big")
            + bytes.fromhex(value)
        ).digest()
        for index, value in enumerate(ordered)
    ]
    if not leaves:
        root = hashlib.sha256(
            _MERKLE_NODE_DOMAIN + role.encode("utf-8") + b"\x00EMPTY"
        ).hexdigest()
    else:
        level = leaves
        while len(level) > 1:
            if len(level) % 2:
                level = [*level, level[-1]]
            level = [
                hashlib.sha256(
                    _MERKLE_NODE_DOMAIN + level[index] + level[index + 1]
                ).digest()
                for index in range(0, len(level), 2)
            ]
        root = level[0].hex()
    return {
        "role": role,
        "count": len(ordered),
        "ordered_merkle_root": root,
    }


def _component_summary_v1(component: Any) -> dict[str, Any]:
    document = component.to_document()
    if type(document) is not dict:
        _fail("source archive component is not one document")
    summary = dict(document)
    for key in (
        "archive",
        "production_verification",
        "independent_attestation",
    ):
        if key not in summary:
            _fail("source archive component omits a bound artifact")
        summary.pop(key)
    return summary


def _verify_replayed_source_graph_v1(
    *,
    recipe: Any,
    recipe_document: Mapping[str, Any],
    recipe_module: ModuleType,
    source_campaign: Any,
    source_verification: Any,
    archive: Any,
    production: Any,
    independent: Any,
    component: Any,
) -> dict[str, Any]:
    campaign_module = recipe_module.campaign_v1
    archive_module = recipe_module.archive_v2
    independent_module = recipe_module.independent_v2
    component_module = recipe_module.component_v1
    exact_types = (
        (source_campaign, campaign_module.ObservationSupportCampaignV1),
        (
            source_verification,
            campaign_module.ObservationSupportCampaignVerificationV1,
        ),
        (archive, archive_module.VerifiedSourceAcquisitionArchiveV2),
        (
            production,
            archive_module.VerifiedSourceAcquisitionArchiveVerificationV2,
        ),
        (
            independent,
            independent_module
            .IndependentSourceAcquisitionArchiveVerificationV2,
        ),
        (
            component,
            component_module.V072VerifiedSourceArchiveComponentV1,
        ),
    )
    if any(type(value) is not expected for value, expected in exact_types):
        _fail("source-only replay graph contains a nonexact artifact type")

    output_ids = {
        "source_campaign_id": source_campaign.campaign_id,
        "source_campaign_verification_id": (
            source_verification.verification_id
        ),
        "source_archive_id": archive.archive_id,
        "production_archive_verification_id": production.verification_id,
        "independent_archive_attestation_id": independent.verification_id,
        "source_archive_component_id": component.component_id,
    }
    if output_ids != recipe_document.get("expected_output_ids"):
        _fail("source-only replay output identities differ from frozen recipe")

    commitments = {
        "context_results": _ordered_merkle_commitment_v1(
            tuple(item.context_result_id for item in source_campaign.context_results),
            role="CONTEXT_RESULT_IDS",
        ),
        "replayed_source_rows": _ordered_merkle_commitment_v1(
            tuple(source_verification.replayed_row_ids),
            role="REPLAYED_SOURCE_ROW_IDS",
        ),
        "archive_adjacent_pairs": _ordered_merkle_commitment_v1(
            tuple(item.pair_id for item in archive.adjacent_pairs),
            role="ARCHIVE_ADJACENT_PAIR_IDS",
        ),
        "archive_trials": _ordered_merkle_commitment_v1(
            tuple(item.trial_id for item in archive.trials),
            role="ARCHIVE_TRIAL_IDS",
        ),
        "archive_feature_consensus": _ordered_merkle_commitment_v1(
            tuple(item.consensus_id for item in archive.consensus),
            role="ARCHIVE_FEATURE_CONSENSUS_IDS",
        ),
        "family_manifest_id": source_campaign.family_manifest.manifest_id,
        "family_authority_id": source_campaign.family_authority.authority_id,
        "campaign_counters_id": source_campaign.counters.counters_id,
    }
    if commitments != recipe_document.get("ordered_commitments"):
        _fail("source-only replay ordered commitments differ from frozen recipe")

    compact = {
        "source_archive": archive.to_document(),
        "production_archive_verification": production.to_document(),
        "independent_archive_attestation": independent.to_document(),
        "source_archive_component_summary": _component_summary_v1(component),
    }
    if compact != recipe_document.get("compact_derived_artifacts"):
        _fail("source-only replay compact artifacts differ from frozen recipe")

    payload = {
        "schema": "acfqp.v075_source_only_replayed_graph_verification.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "source_recipe_id": recipe.recipe_id,
        "expected_output_ids": output_ids,
        "ordered_commitments": commitments,
        "compact_artifacts_exactly_matched": True,
        "generic_recipe_freeze_helper_called": False,
        "confirmatory_manifest_imported": False,
        "caller_expected_ids_accepted": False,
        "caller_counter_document_accepted": False,
        "target_access": False,
        "hidden_law_access": False,
        "valid": True,
    }
    return {
        **payload,
        "source_graph_verification_id": _role_id(
            "source_graph_verification",
            payload,
        ),
    }


def _replay_registered_source_only_v1(
    *,
    recipe: Any,
    recipe_document: Mapping[str, Any],
    recipe_module: ModuleType,
) -> tuple[Any, dict[str, Any]]:
    campaign_module = recipe_module.campaign_v1
    archive_module = recipe_module.archive_v2
    independent_module = recipe_module.independent_v2
    component_module = recipe_module.component_v1
    source_campaign = campaign_module.run_observation_support_campaign_v1(
        max_workers=recipe_module.RECONSTRUCTION_MAX_WORKERS
    )
    source_verification = (
        campaign_module.verify_observation_support_campaign_v1(
            source_campaign,
            max_workers=recipe_module.RECONSTRUCTION_MAX_WORKERS,
        )
    )
    archive = archive_module.freeze_verified_source_acquisition_archive_v2(
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    production = archive_module.verify_verified_source_acquisition_archive_v2(
        source_campaign=source_campaign,
        source_verification=source_verification,
        claimed=archive,
    )
    independent = (
        independent_module
        .verify_source_acquisition_archive_independently_v2(
            source_campaign=source_campaign,
            source_verification=source_verification,
            claimed=archive,
        )
    )
    component = (
        component_module.bind_v072_verified_source_archive_component_v1(
            archive=archive,
            production_verification=production,
            independent_attestation=independent,
        )
    )
    verification = _verify_replayed_source_graph_v1(
        recipe=recipe,
        recipe_document=recipe_document,
        recipe_module=recipe_module,
        source_campaign=source_campaign,
        source_verification=source_verification,
        archive=archive,
        production=production,
        independent=independent,
        component=component,
    )
    replay = recipe_module.SourceReconstructionReplayV1(
        recipe.recipe_id,
        source_campaign,
        source_verification,
        archive,
        production,
        independent,
        component,
    )
    if type(replay) is not recipe_module.SourceReconstructionReplayV1:
        _fail("source-only replay did not retain the exact historical type")
    return replay, verification


def _manifest_file_digest(
    code_manifest: Mapping[str, Any],
    relative_path: str,
) -> str:
    matches = [
        item
        for item in code_manifest["files"]
        if item["repository_relative_path"] == relative_path
    ]
    if len(matches) != 1:
        _fail("current code manifest does not bind one required module")
    return _require_id(matches[0]["sha256_file_bytes"], relative_path)


def _load_digest_bound_current_module_v1(
    *,
    module_name: str,
    relative_path: str,
    code_manifest: Mapping[str, Any],
) -> ModuleType:
    path = _safe_repo_path(_current_repository_root(), relative_path)
    raw = _read_regular(path)
    if hashlib.sha256(raw).hexdigest() != _manifest_file_digest(
        code_manifest,
        relative_path,
    ):
        _fail("current V0-075 module differs from its frozen code manifest")
    if module_name in sys.modules:
        _fail("current V0-075 dynamic module was already imported")
    spec = importlib_util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        _fail("current V0-075 dynamic module has no exact file loader")
    module = importlib_util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    if Path(module.__file__).resolve(strict=True) != path:
        _fail("current V0-075 dynamic module origin changed")
    return module


class _DigestBoundMaterializerAdapter:
    def __init__(
        self,
        *,
        module: ModuleType,
        recipe_module: ModuleType,
    ) -> None:
        if (
            module.recipe_v1 is not recipe_module
            or module.campaign_v1 is not recipe_module.campaign_v1
        ):
            _fail("current materializer does not share historical exact types")
        self._module = module

    def materialize(self, replay: Any) -> Any:
        return self._module.materialize_v075_source_offline_work_v1(replay)

    def verify(self, *, replay: Any, claimed: Any) -> Any:
        return (
            self._module
            .verify_v075_source_offline_work_independently_v1(
                replay=replay,
                claimed=claimed,
            )
        )


def _load_digest_bound_current_materializer_v1(
    *,
    recipe_module: ModuleType,
    code_manifest: Mapping[str, Any],
) -> _DigestBoundMaterializerAdapter:
    _load_digest_bound_current_module_v1(
        module_name="acfqp.v075_frozen_source_proposal_archive_v1",
        relative_path=_CURRENT_DYNAMIC_MODULE_PATHS[0],
        code_manifest=code_manifest,
    )
    materializer = _load_digest_bound_current_module_v1(
        module_name="acfqp.v075_source_offline_work_materializer_v1",
        relative_path=_CURRENT_DYNAMIC_MODULE_PATHS[1],
        code_manifest=code_manifest,
    )
    return _DigestBoundMaterializerAdapter(
        module=materializer,
        recipe_module=recipe_module,
    )


def _assert_source_only_import_state_v1(
    guard: _SourceOnlyImportGuard,
    *,
    snapshot_root: Path,
) -> tuple[str, ...]:
    forbidden_loaded = tuple(
        sorted(name for name in sys.modules if _is_forbidden_acfqp_module(name))
    )
    if guard.denied_attempts or forbidden_loaded:
        _fail("source-only replay attempted or loaded a forbidden module")
    observed = tuple(
        sorted(
            name
            for name in sys.modules
            if name == "acfqp" or name.startswith("acfqp.")
        )
    )
    _verify_loaded_module_allowlist_v1(observed)

    historical_root = _safe_repo_path(snapshot_root, "src/acfqp")
    current_root = _current_repository_root()
    current_names = {
        "acfqp.v075_frozen_source_proposal_archive_v1": (
            _CURRENT_DYNAMIC_MODULE_PATHS[0]
        ),
        "acfqp.v075_source_offline_work_materializer_v1": (
            _CURRENT_DYNAMIC_MODULE_PATHS[1]
        ),
    }
    for name in observed:
        module_file = getattr(sys.modules[name], "__file__", None)
        if type(module_file) is not str:
            _fail("source-only allowlisted module has no regular-file origin")
        try:
            origin = Path(module_file).resolve(strict=True)
        except FileNotFoundError as error:
            raise V075SourceReplayControllerViolation(
                "source-only module origin disappeared"
            ) from error
        if name in current_names:
            expected = _safe_repo_path(current_root, current_names[name])
            if origin != expected:
                _fail("current V0-075 module escaped its digest-bound origin")
        else:
            try:
                origin.relative_to(historical_root)
            except ValueError:
                _fail("historical source module escaped the detached snapshot")
    return observed


def _verify_loaded_module_allowlist_v1(
    observed: Sequence[str],
) -> None:
    allowlist_id = hashlib.sha256(
        _SOURCE_ONLY_IMPORT_ALLOWLIST_DOMAIN
        + _canonical_json_bytes(list(_SOURCE_ONLY_ACFQP_IMPORT_ALLOWLIST))
    ).hexdigest()
    if (
        allowlist_id != _SOURCE_ONLY_IMPORT_ALLOWLIST_ID
        or tuple(observed) != _SOURCE_ONLY_ACFQP_IMPORT_ALLOWLIST
    ):
        _fail("source-only loaded-module closure differs from exact allowlist")


def verify_source_only_replay_readiness_v1(
    snapshot_root: str | os.PathLike[str],
    *,
    preflight: Mapping[str, Any] | None = None,
    code_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = _absolute_real_directory(snapshot_root)
    checked = (
        verify_snapshot_preflight_v1(root)
        if preflight is None
        else dict(preflight)
    )
    manifest = (
        freeze_controller_code_manifest_v1()
        if code_manifest is None
        else dict(code_manifest)
    )
    _require_production_code_manifest_v1(manifest)
    with _isolated_historical_acfqp_runtime(root) as guard:
        recipe_module = _import_historical_source_recipe_v1()
        recipe = _load_historical_recipe_v1(root, recipe_module)
        _verify_registered_source_inputs_v1(
            recipe=recipe,
            recipe_module=recipe_module,
            preflight=checked,
        )
        _load_digest_bound_current_materializer_v1(
            recipe_module=recipe_module,
            code_manifest=manifest,
        )
        imported = _assert_source_only_import_state_v1(
            guard,
            snapshot_root=root,
        )
    payload = {
        "schema": "acfqp.v075_source_only_replay_readiness.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "snapshot_preflight_id": checked["preflight_id"],
        "controller_code_manifest_id": (
            manifest["controller_code_manifest_id"]
        ),
        "source_recipe_id": REQUIRED_SOURCE_RECIPE_ID,
        "historical_source_modules": list(_HISTORICAL_SOURCE_MODULE_NAMES),
        "loaded_acfqp_modules": list(imported),
        "loaded_acfqp_module_allowlist_id": (
            _SOURCE_ONLY_IMPORT_ALLOWLIST_ID
        ),
        "imported_acfqp_module_count": len(imported),
        "forbidden_import_attempt_count": 0,
        "generic_recipe_freeze_helper_called": False,
        "digest_bound_current_materializer_loaded": True,
        "exact_historical_type_alignment_verified": True,
        "production_replay_eligible": True,
        "source_child_launched": False,
        "sample_draws_started": False,
        "target_access": False,
        "hidden_law_access": False,
        "ready": True,
    }
    return {
        **payload,
        "readiness_id": _role_id("source_only_readiness", payload),
    }


def _status_document(
    *,
    preflight: dict[str, Any],
    code_manifest: dict[str, Any],
    readiness: Mapping[str, Any] | None = None,
    protocol: InjectedProtocolResultV1 | None = None,
) -> dict[str, Any]:
    completed = protocol is not None
    materialization = None if protocol is None else protocol.materialization
    verification = None if protocol is None else protocol.verification
    protocol_document = (
        None if protocol is None else protocol.protocol_document
    )
    payload = {
        "schema": "acfqp.v075_source_replay_materialization_status.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "snapshot_preflight_id": preflight["preflight_id"],
        "controller_code_manifest_id": (
            code_manifest["controller_code_manifest_id"]
        ),
        "source_only_bypass_evidence_id": (
            preflight["source_only_bypass_evidence"][
                "source_only_bypass_evidence_id"
            ]
        ),
        "source_only_readiness_id": (
            None if readiness is None else readiness["readiness_id"]
        ),
        "same_process_protocol_id": (
            None if protocol_document is None
            else protocol_document["protocol_id"]
        ),
        "source_graph_verification_id": (
            None if protocol_document is None
            else protocol_document["source_graph_verification_id"]
        ),
        "blocker": None,
        "source_only_snapshot_eligible": (
            preflight["production_replay_eligible"]
        ),
        "current_code_production_ready": (
            code_manifest["relevant_paths_clean"] is True
            and code_manifest["all_paths_tracked"] is True
        ),
        "production_replay_status": (
            "COMPLETED" if completed else PRODUCTION_REPLAY_STATUS
        ),
        "production_materialization_status": (
            "COMPLETED"
            if completed
            else PRODUCTION_MATERIALIZATION_STATUS
        ),
        "source_replay_id": None,
        "source_replay_object_persisted": False,
        "source_replay_object_consumed_same_process": completed,
        "source_work_materialization_id": (
            None
            if materialization is None
            else materialization.materialization_id
        ),
        "source_work_verification_id": (
            None if verification is None else verification.verification_id
        ),
        "source_child_launched": False,
        "sample_draws_started": completed,
        "materialization_artifact_written": completed,
        "verification_artifact_written": completed,
        "counter_document_accepted": False,
        "pickle_transport_accepted": False,
        "caller_supplied_expected_ids_accepted": False,
        "current_tree_recomputation_used_as_source_replay": False,
        "generic_recipe_freeze_helper_called": False,
        "confirmatory_manifest_imported": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "target_access": False,
        "hidden_law_access": False,
    }
    return {**payload, "status_id": _role_id("status", payload)}


def _write_exclusive(path: Path, raw: bytes) -> None:
    if not path.is_absolute() or path.exists() or path.is_symlink():
        _fail("controller output must be one new absolute regular path")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as error:
        raise V075SourceReplayControllerViolation(
            "controller output could not be created exclusively"
        ) from error
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _create_output_directory(value: str | os.PathLike[str]) -> Path:
    candidate = _validate_output_directory_candidate(value)
    try:
        os.mkdir(candidate, 0o700)
    except OSError as error:
        raise V075SourceReplayControllerViolation(
            "output directory could not be created exclusively"
        ) from error
    return candidate


def _validate_output_directory_candidate(
    value: str | os.PathLike[str],
) -> Path:
    candidate = Path(value)
    if (
        not candidate.is_absolute()
        or candidate.exists()
        or candidate.is_symlink()
    ):
        _fail("output directory must be one new absolute path")
    parent = candidate.parent
    if (
        not parent.is_dir()
        or parent.is_symlink()
        or parent.resolve(strict=True) != parent
    ):
        _fail("output parent must be one existing real directory")
    return candidate


class _InjectedReplayMechanics(Protocol):
    target_accessed: bool
    hidden_law_accessed: bool

    def check_frozen_environment(self) -> Any: ...

    def replay_exact_source(self) -> Any: ...

    def load_current_v075_materializer(self) -> Any: ...


@dataclass(frozen=True)
class InjectedProtocolResultV1:
    materialization: Any
    verification: Any
    protocol_document: dict[str, Any]


def _run_injected_same_process_protocol_v1(
    mechanics: _InjectedReplayMechanics,
) -> InjectedProtocolResultV1:
    """Test/future hook; never selectable from the production command line."""

    pid = os.getpid()
    order: list[str] = []
    environment = mechanics.check_frozen_environment()
    order.append("CHECK_FROZEN_ENVIRONMENT")
    if os.getpid() != pid:
        _fail("environment check left the source replay process")
    replay = mechanics.replay_exact_source()
    order.append("REPLAY_EXACT_SOURCE")
    if os.getpid() != pid:
        _fail("source replay left the materialization process")
    materializer = mechanics.load_current_v075_materializer()
    order.append("LOAD_DIGEST_BOUND_CURRENT_V075_MATERIALIZER")
    if os.getpid() != pid:
        _fail("current materializer was not loaded in the replay process")
    materialization = materializer.materialize(replay)
    order.append("MATERIALIZE_REPLAY_OBJECT_DIRECTLY")
    verification = materializer.verify(
        replay=replay,
        claimed=materialization,
    )
    order.append("VERIFY_MATERIALIZATION_DIRECTLY")
    if os.getpid() != pid:
        _fail("verification left the source replay process")
    if (
        getattr(mechanics, "target_accessed", None) is not False
        or getattr(mechanics, "hidden_law_accessed", None) is not False
    ):
        _fail("injected source mechanics accessed target or hidden law")
    materialization_id = _require_id(
        getattr(materialization, "materialization_id", None),
        "injected materialization",
    )
    verification_id = _require_id(
        getattr(verification, "verification_id", None),
        "injected materialization verification",
    )
    if (
        getattr(verification, "materialization_id", None)
        != materialization_id
        or getattr(verification, "recomputed_materialization_id", None)
        != materialization_id
        or type(getattr(materialization, "canonical_bytes", None))
        is not bytes
    ):
        _fail("injected materialization/verification identity chain is open")
    payload = {
        "schema": "acfqp.v075_source_replay_injected_protocol.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "process_id_stable": True,
        "operation_order": order,
        "environment_check_result_type": type(environment).__name__,
        "replay_result_type": type(replay).__name__,
        "materialization_id": materialization_id,
        "verification_id": verification_id,
        "counter_document_accepted": False,
        "pickle_transport_accepted": False,
        "target_access": False,
        "hidden_law_access": False,
    }
    return InjectedProtocolResultV1(
        materialization,
        verification,
        {
            **payload,
            "protocol_id": _role_id("injected_protocol", payload),
        },
    )


class _RegisteredSourceOnlyMechanics:
    target_accessed = False
    hidden_law_accessed = False

    def __init__(
        self,
        *,
        preflight: Mapping[str, Any],
        code_manifest: Mapping[str, Any],
        recipe: Any,
        recipe_document: Mapping[str, Any],
        recipe_module: ModuleType,
    ) -> None:
        self.preflight = preflight
        self.code_manifest = code_manifest
        self.recipe = recipe
        self.recipe_document = recipe_document
        self.recipe_module = recipe_module
        self.source_graph_verification: dict[str, Any] | None = None

    def check_frozen_environment(self) -> Mapping[str, Any]:
        return self.preflight["frozen_recipe_environment"]

    def replay_exact_source(self) -> Any:
        replay, verification = _replay_registered_source_only_v1(
            recipe=self.recipe,
            recipe_document=self.recipe_document,
            recipe_module=self.recipe_module,
        )
        self.source_graph_verification = verification
        return replay

    def load_current_v075_materializer(
        self,
    ) -> _DigestBoundMaterializerAdapter:
        return _load_digest_bound_current_materializer_v1(
            recipe_module=self.recipe_module,
            code_manifest=self.code_manifest,
        )


def _run_registered_source_only_protocol_v1(
    *,
    snapshot_root: str | os.PathLike[str],
    preflight: Mapping[str, Any],
    code_manifest: Mapping[str, Any],
) -> InjectedProtocolResultV1:
    root = _absolute_real_directory(snapshot_root)
    _require_production_code_manifest_v1(code_manifest)
    with _isolated_historical_acfqp_runtime(root) as guard:
        recipe_module = _import_historical_source_recipe_v1()
        recipe = _load_historical_recipe_v1(root, recipe_module)
        recipe_document = _verify_registered_source_inputs_v1(
            recipe=recipe,
            recipe_module=recipe_module,
            preflight=preflight,
        )
        mechanics = _RegisteredSourceOnlyMechanics(
            preflight=preflight,
            code_manifest=code_manifest,
            recipe=recipe,
            recipe_document=recipe_document,
            recipe_module=recipe_module,
        )
        result = _run_injected_same_process_protocol_v1(mechanics)
        imported = _assert_source_only_import_state_v1(
            guard,
            snapshot_root=root,
        )
        graph = mechanics.source_graph_verification
        if graph is None:
            _fail("source-only replay omitted graph verification")
        protocol_payload = dict(result.protocol_document)
        protocol_payload.pop("protocol_id")
        protocol_payload.update(
            {
                "source_graph_verification_id": (
                    graph["source_graph_verification_id"]
                ),
                "historical_source_module_count": len(imported),
                "loaded_acfqp_module_allowlist_id": (
                    _SOURCE_ONLY_IMPORT_ALLOWLIST_ID
                ),
                "forbidden_import_attempt_count": 0,
                "generic_recipe_freeze_helper_called": False,
                "confirmatory_manifest_imported": False,
            }
        )
        result = InjectedProtocolResultV1(
            result.materialization,
            result.verification,
            {
                **protocol_payload,
                "protocol_id": _role_id(
                    "injected_protocol",
                    protocol_payload,
                ),
            },
        )
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "preflight or explicitly attempt the V0-075 source replay"
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-snapshot", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--replay-and-materialize", action="store_true")
    parser.add_argument("--snapshot-root", required=True)
    parser.add_argument("--output-dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if (
            (args.check_snapshot or args.preflight_only)
            and args.output_dir is not None
        ):
            _fail("preflight modes perform no output writes")
        if args.replay_and_materialize and args.output_dir is None:
            _fail("--replay-and-materialize requires --output-dir")
        if args.replay_and_materialize:
            _validate_output_directory_candidate(args.output_dir)
        preflight = verify_snapshot_preflight_v1(args.snapshot_root)
        code_manifest = freeze_controller_code_manifest_v1()
        if args.check_snapshot:
            status = _status_document(
                preflight=preflight,
                code_manifest=code_manifest,
            )
            sys.stdout.buffer.write(_canonical_json_bytes(status) + b"\n")
            return 0
        readiness = verify_source_only_replay_readiness_v1(
            args.snapshot_root,
            preflight=preflight,
            code_manifest=code_manifest,
        )
        if args.preflight_only:
            sys.stdout.buffer.write(
                _canonical_json_bytes(readiness) + b"\n"
            )
            return 0

        protocol = _run_registered_source_only_protocol_v1(
            snapshot_root=args.snapshot_root,
            preflight=preflight,
            code_manifest=code_manifest,
        )
        materialization_raw = protocol.materialization.canonical_bytes
        verification_raw = _canonical_json_bytes(
            protocol.verification.to_document()
        )
        status = _status_document(
            preflight=preflight,
            code_manifest=code_manifest,
            readiness=readiness,
            protocol=protocol,
        )
        output = _create_output_directory(args.output_dir)
        _write_exclusive(
            output / MATERIALIZATION_FILENAME,
            materialization_raw,
        )
        _write_exclusive(
            output / VERIFICATION_FILENAME,
            verification_raw,
        )
        _write_exclusive(
            output / STATUS_FILENAME,
            _canonical_json_bytes(status),
        )
        sys.stdout.buffer.write(_canonical_json_bytes(status) + b"\n")
        return 0
    except V075SourceReplayControllerViolation as error:
        sys.stderr.write(f"{error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
