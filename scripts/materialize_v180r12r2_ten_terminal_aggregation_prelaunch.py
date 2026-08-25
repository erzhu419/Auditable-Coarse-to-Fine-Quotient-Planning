#!/usr/bin/python3
"""Materialize the source-bound V180r12r2 prelaunch exactly once.

This stdlib-only construction step consumes an externally supplied immutable
root record.  That record chooses the exact preregistration commit (``C_pre``);
this program never infers or substitutes it from ``HEAD``.  The program then
checks the exact C_pre -> empty same-tree bridge -> wrapper-only literal commit
history, constructs a launch manifest from C_pre Git blobs plus the independently
normalized current wrapper, and writes the retained bootstrap, manifest, and
terminal with write-once durability.  It does not authorize or execute a
V180r12r2 scientific occurrence.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import sysconfig
import tarfile
import tokenize
from typing import Any, NoReturn


EXTERNAL_ROOT_SCHEMA = "acfqp.v180r12r2_prelaunch_external_root.v1"
LAUNCH_MANIFEST_SCHEMA = "acfqp.v180r12r2_source_bound_launch_manifest.v1"
MATERIALIZATION_TERMINAL_SCHEMA = (
    "acfqp.v180r12r2_prelaunch_materialization_terminal.v1"
)
MATERIALIZATION_FAILURE_SCHEMA = (
    "acfqp.v180r12r2_prelaunch_materialization_failure.v1"
)

OUTPUT_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation_prelaunch"
)
EXTERNAL_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r2_ten_terminal_aggregation_prelaunch_external_root.json"
)
BOOTSTRAP_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/bootstrap.py"
RETAINED_LAUNCHER_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/launcher.py"
LAUNCH_MANIFEST_RELATIVE_PATH = (
    f"{OUTPUT_ROOT_RELATIVE_PATH}/launch_manifest.json"
)
MATERIALIZATION_TERMINAL_RELATIVE_PATH = (
    f"{OUTPUT_ROOT_RELATIVE_PATH}/MATERIALIZATION_TERMINAL.json"
)
MATERIALIZATION_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r2_ten_terminal_aggregation_prelaunch_failure.json"
)

MATERIALIZER_RELATIVE_PATH = (
    "scripts/materialize_v180r12r2_ten_terminal_aggregation_prelaunch.py"
)
SOURCE_BOOTSTRAP_RELATIVE_PATH = (
    "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py"
)
SOURCE_LAUNCHER_RELATIVE_PATH = (
    "scripts/launch_v180r12r2_ten_terminal_aggregation_prelaunch.py"
)
AUTHORIZATION_SELF_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2.py"
)
AUTHORIZATION_SELF_MODULE = (
    "acfqp."
    "construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2"
)
AUTHORIZATION_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_ten_terminal_aggregation_execution_"
    "authorization_evidence_freeze_v180r12r2.py"
)
AUTHORIZATION_EVIDENCE_MODULE = (
    "acfqp.construction_k7_ten_terminal_aggregation_execution_"
    "authorization_evidence_freeze_v180r12r2"
)
TARGET_RUNNER_PATHS = {
    "production": "scripts/run_v180r12r2_ten_terminal_aggregation.py",
    "verification": "scripts/verify_v180r12r2_ten_terminal_aggregation.py",
}

WRAPPER_REDACTED_CONSTANT_NAMES = (
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
)
_WRAPPER_STRING_CONSTANT_NAMES = frozenset(
    {
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
        "EXPECTED_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_ID",
        "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
    }
)
_WRAPPER_INTEGER_CONSTANT_NAMES = frozenset(
    {
        "EXPECTED_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    }
)
_WRAPPER_REDACTED_STRING_LITERAL = (
    b'"__ACFQP_V180R12R2_POST_PREREG_REDACTED__"'
)
_WRAPPER_REDACTED_INTEGER_LITERAL = b"0"

_PRODUCTION_SOURCE_ROOTS = (
    TARGET_RUNNER_PATHS["production"],
    "src/acfqp/construction_k7_ten_terminal_aggregation_finalizer_v180r12r2.py",
)
_VERIFICATION_SOURCE_ROOTS = (
    TARGET_RUNNER_PATHS["verification"],
    (
        "src/acfqp/construction_k7_ten_terminal_aggregation_"
        "independent_verifier_v180r12r2.py"
    ),
)
_CONTRACT_SOURCE_ROOTS = (
    "src/acfqp/abstraction/behavioral.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r2.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r2e.py",
    (
        "src/acfqp/construction_k7_ten_terminal_aggregation_"
        "stale_predecessor_freeze_v180r12r2.py"
    ),
    "src/acfqp/construction_k7_ten_terminal_aggregation_protocol_v180r12r2.py",
    AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
    (
        "src/acfqp/construction_k7_ten_terminal_aggregation_"
        "campaign_accounting_v180r12r2.py"
    ),
    "src/acfqp/v075_production_semantic_authority_registry_v2.py",
)

PYTHON_EXECUTABLE = "/usr/bin/python3"
GIT_EXECUTABLE = "/usr/bin/git"
PYCACHE_PREFIX = "/dev/null/v180r12r2"
EXTERNAL_ROOT_SHA256_ENV = "ACFQP_V180R12R2_EXTERNAL_ROOT_SHA256"
MANIFEST_SHA256_ENV = "ACFQP_V180R12R2_LAUNCH_MANIFEST_SHA256"
PREREG_COMMIT_ENV = "ACFQP_V180R12R2_PREREG_COMMIT"
MANIFEST_SHA256_TEMPLATE = "__V180R12R2_MANIFEST_SHA256__"
ISOLATED_ARGV_PREFIX = (
    PYTHON_EXECUTABLE,
    "-I",
    "-S",
    "-B",
    "-X",
    f"pycache_prefix={PYCACHE_PREFIX}",
)
AUTHORIZATION_SOURCE_CLOSURE_KIND = (
    "EXACT_RAW_AUTHORIZATION_SOURCE_CLOSURE_PLUS_AUTH_SELF_AND_BOUND_RUNNERS"
)
NORMALIZED_WRAPPER_BINDING_KIND = "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"

EXTERNAL_ROOT_BYTE_CAP = 1024 * 1024
BOOTSTRAP_BYTE_CAP = 1024 * 1024
LAUNCHER_BYTE_CAP = 1024 * 1024
MATERIALIZER_BYTE_CAP = 2 * 1024 * 1024
LAUNCH_MANIFEST_BYTE_CAP = 16 * 1024 * 1024
RUNNER_BYTE_CAP = 4 * 1024 * 1024
SOURCE_FILE_BYTE_CAP = 8 * 1024 * 1024
SOURCE_CLOSURE_FILE_CAP = 4096
SOURCE_CLOSURE_TOTAL_BYTE_CAP = 128 * 1024 * 1024
EXECUTABLE_BYTE_CAP = 64 * 1024 * 1024
GIT_ARCHIVE_BYTE_CAP = 256 * 1024 * 1024
GIT_COMMAND_TIMEOUT_SECONDS = 120
FAILURE_MESSAGE_BYTE_CAP = 4096

SOURCE_CLOSURE_RULE_DOCUMENT = {
    "schema": "acfqp.v180r12r2_prelaunch_source_closure_rule.v1",
    "ordinary_source_root_paths": sorted(
        {*_PRODUCTION_SOURCE_ROOTS, *_VERIFICATION_SOURCE_ROOTS, *_CONTRACT_SOURCE_ROOTS}
    ),
    "authorization_self_relative_path": AUTHORIZATION_SELF_RELATIVE_PATH,
    "authorization_self_excluded_from_recursive_closure": True,
    "recursive_rule": "STATIC_LOCAL_ACFQP_IMPORTS_PLUS_PARENT_PACKAGES",
    "runner_binding": "C_PRE_RAW_GIT_BLOBS",
    "ordinary_binding": "C_PRE_RAW_GIT_BLOBS",
    "authorization_self_binding": "C_PRE_RAW_GIT_BLOB",
    "wrapper_binding": NORMALIZED_WRAPPER_BINDING_KIND,
    "wrapper_redacted_constant_names": list(WRAPPER_REDACTED_CONSTANT_NAMES),
    "third_party_namespaces": ["packaging", "tomli"],
    "third_party_binding": "COMPLETE_LIVE_PY_SOURCE_NAMESPACE_SNAPSHOT",
    "prelaunch_special_git_blob_paths": [
        SOURCE_BOOTSTRAP_RELATIVE_PATH,
        SOURCE_LAUNCHER_RELATIVE_PATH,
        MATERIALIZER_RELATIVE_PATH,
    ],
}
MATERIALIZATION_RULE_DOCUMENT = {
    "schema": "acfqp.v180r12r2_prelaunch_materialization_rule.v1",
    "external_root_schema": EXTERNAL_ROOT_SCHEMA,
    "launch_manifest_schema": LAUNCH_MANIFEST_SCHEMA,
    "terminal_schema": MATERIALIZATION_TERMINAL_SCHEMA,
    "failure_schema": MATERIALIZATION_FAILURE_SCHEMA,
    "external_root_relative_path": EXTERNAL_ROOT_RELATIVE_PATH,
    "output_root_relative_path": OUTPUT_ROOT_RELATIVE_PATH,
    "bootstrap_relative_path": BOOTSTRAP_RELATIVE_PATH,
    "retained_launcher_relative_path": RETAINED_LAUNCHER_RELATIVE_PATH,
    "launch_manifest_relative_path": LAUNCH_MANIFEST_RELATIVE_PATH,
    "terminal_relative_path": MATERIALIZATION_TERMINAL_RELATIVE_PATH,
    "failure_relative_path": MATERIALIZATION_FAILURE_RELATIVE_PATH,
    "git_history_rule": "EXACT_C_PRE_EMPTY_SAME_TREE_BRIDGE_WRAPPER_ONLY_LITERAL_HEAD",
    "write_rule": "O_EXCL_O_NOFOLLOW_CLOEXEC_0700_DIR_0400_FILES_FSYNC_TERMINAL_LAST",
    "rerun_rule": "ANY_PROGRESS_OR_TERMINAL_OR_FAILURE_FORBIDS_SAME_IDENTITY_RERUN",
    "identity_cycle_rule": "MANIFEST_DIGEST_RECORDED_ONLY_AFTER_MANIFEST_SERIALIZATION",
    "construction_only": True,
    "preauthorization": True,
    "campaign_actual_measurement": False,
    "bootstrap_byte_cap": BOOTSTRAP_BYTE_CAP,
    "launcher_byte_cap": LAUNCHER_BYTE_CAP,
    "materializer_byte_cap": MATERIALIZER_BYTE_CAP,
    "external_root_byte_cap": EXTERNAL_ROOT_BYTE_CAP,
    "launch_manifest_byte_cap": LAUNCH_MANIFEST_BYTE_CAP,
    "runner_byte_cap": RUNNER_BYTE_CAP,
    "source_file_byte_cap": SOURCE_FILE_BYTE_CAP,
    "source_closure_file_cap": SOURCE_CLOSURE_FILE_CAP,
    "source_closure_total_byte_cap": SOURCE_CLOSURE_TOTAL_BYTE_CAP,
    "executable_byte_cap": EXECUTABLE_BYTE_CAP,
    "git_archive_byte_cap": GIT_ARCHIVE_BYTE_CAP,
    "git_command_timeout_seconds": GIT_COMMAND_TIMEOUT_SECONDS,
    "failure_message_byte_cap": FAILURE_MESSAGE_BYTE_CAP,
}


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


SOURCE_CLOSURE_RULE_ID = hashlib.sha256(
    canonical_json_bytes(SOURCE_CLOSURE_RULE_DOCUMENT)
).hexdigest()
MATERIALIZATION_RULE_ID = hashlib.sha256(
    canonical_json_bytes(MATERIALIZATION_RULE_DOCUMENT)
).hexdigest()

_COMMIT_ID = re.compile(r"^[0-9a-f]{40}$")
_OBJECT_ID = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class V180r12r2PrelaunchMaterializationError(RuntimeError):
    """The external root, source closure, topology, or one-shot write changed."""


class V180r12r2PrelaunchMaterializationReplayForbidden(
    V180r12r2PrelaunchMaterializationError
):
    """A prior attempt exists and the same materialization may not run again."""


def _fail(message: str) -> NoReturn:
    raise V180r12r2PrelaunchMaterializationError(message)


def _require_exact_dict(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{label} schema is not exact")
    return value


def _require_nonempty_string(value: object, label: str) -> str:
    if type(value) is not str or not value or "\x00" in value:
        _fail(f"{label} is not one nonempty string")
    return value


def _require_sha256(value: object, label: str) -> str:
    text = _require_nonempty_string(value, label)
    if _SHA256.fullmatch(text) is None:
        _fail(f"{label} is not one lowercase SHA-256 digest")
    return text


def _require_commit(value: object, label: str) -> str:
    text = _require_nonempty_string(value, label)
    if _COMMIT_ID.fullmatch(text) is None:
        _fail(f"{label} is not one lowercase 40-hex commit ID")
    return text


def _require_object_id(value: object, label: str) -> str:
    text = _require_nonempty_string(value, label)
    if _OBJECT_ID.fullmatch(text) is None:
        _fail(f"{label} is not one lowercase Git object ID")
    return text


def _require_nonnegative_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} is not one nonnegative integer")
    return value


def _validated_relative_path(value: object, label: str) -> str:
    text = _require_nonempty_string(value, label)
    pure = PurePosixPath(text)
    if (
        pure.is_absolute()
        or pure.as_posix() != text
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        _fail(f"{label} is not one normalized relative path")
    return text


def _validated_absolute_directory(value: object, label: str) -> Path:
    text = _require_nonempty_string(value, label)
    path = Path(text)
    if not path.is_absolute() or str(path) != text:
        _fail(f"{label} is not one exact absolute path")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as error:
            raise V180r12r2PrelaunchMaterializationError(
                f"{label} is unavailable"
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            _fail(f"{label} has a symlinked path component")
    if not stat.S_ISDIR(os.lstat(path).st_mode) or path.resolve(strict=True) != path:
        _fail(f"{label} is not one nonsymlink directory")
    return path


def _stable_read_file(
    path: Path,
    *,
    label: str,
    byte_cap: int,
    required_mode: int | None = None,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> bytes:
    """Stream-read a stable, singly linked regular file without symlinks."""

    if not path.is_absolute():
        _fail(f"{label} path is not absolute")
    current = Path(path.anchor)
    for part in path.parts[1:-1]:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as error:
            raise V180r12r2PrelaunchMaterializationError(
                f"{label} parent is unavailable"
            ) from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            _fail(f"{label} parent is symlinked or nondirectory")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise V180r12r2PrelaunchMaterializationError(
            f"{label} is unavailable or symlinked"
        ) from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _fail(f"{label} must be one singly linked regular file")
        if required_mode is not None and stat.S_IMODE(before.st_mode) != required_mode:
            _fail(f"{label} mode is not {required_mode:04o}")
        if before.st_size > byte_cap:
            _fail(f"{label} exceeds its byte cap")
        if expected_size is not None and before.st_size != expected_size:
            _fail(f"{label} byte count differs from its frozen fact")
        chunks: list[bytes] = []
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, byte_cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            digest.update(chunk)
            total += len(chunk)
            if total > byte_cap:
                _fail(f"{label} exceeded its streaming byte cap")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(getattr(before, name) != getattr(after, name) for name in stable_fields):
        _fail(f"{label} changed during its stable read")
    raw = b"".join(chunks)
    observed_digest = digest.hexdigest()
    if len(raw) != before.st_size:
        _fail(f"{label} changed length during its stable read")
    if expected_sha256 is not None and observed_digest != expected_sha256:
        _fail(f"{label} digest differs from its frozen fact")
    return raw


def _parse_canonical_json_object(raw: bytes, label: str) -> dict[str, Any]:
    duplicate = object()

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if type(key) is not str or key in result:
                raise ValueError(duplicate)
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs_hook,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise V180r12r2PrelaunchMaterializationError(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _raw_fact(relative_path: str, raw: bytes) -> dict[str, Any]:
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _closure(facts: list[dict[str, Any]], *, sort_key: str) -> dict[str, Any]:
    ordered = sorted(facts, key=lambda row: row[sort_key])
    if [row[sort_key] for row in ordered] != sorted(
        {row[sort_key] for row in ordered}
    ):
        _fail("source closure facts are duplicated")
    total = sum(_require_nonnegative_int(row["byte_count"], "source byte count") for row in ordered)
    if len(ordered) > SOURCE_CLOSURE_FILE_CAP or total > SOURCE_CLOSURE_TOTAL_BYTE_CAP:
        _fail("source closure exceeds its frozen cap")
    return {
        "facts": ordered,
        "file_count": len(ordered),
        "total_byte_count": total,
        "facts_sha256": hashlib.sha256(canonical_json_bytes(ordered)).hexdigest(),
    }


def _git_environment() -> dict[str, str]:
    return {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
    }


def _run_git(
    repository_root: Path,
    arguments: tuple[str, ...],
    label: str,
    *,
    byte_cap: int = GIT_ARCHIVE_BYTE_CAP,
) -> bytes:
    argv = (GIT_EXECUTABLE, "-C", str(repository_root), *arguments)
    try:
        completed = subprocess.run(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
            env=_git_environment(),
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise V180r12r2PrelaunchMaterializationError(
            f"Git {label} failed"
        ) from error
    if completed.returncode != 0 or completed.stderr:
        _fail(f"Git {label} rejected the frozen boundary")
    if len(completed.stdout) > byte_cap:
        _fail(f"Git {label} exceeded its output byte cap")
    return completed.stdout


def _git_blob_fact_keys() -> set[str]:
    return {
        "relative_path",
        "git_mode",
        "git_blob_id",
        "byte_count",
        "sha256",
    }


def _validated_git_blob_fact(value: object, label: str) -> dict[str, Any]:
    fact = _require_exact_dict(value, _git_blob_fact_keys(), label)
    relative = _validated_relative_path(fact["relative_path"], f"{label} path")
    mode = _require_nonempty_string(fact["git_mode"], f"{label} mode")
    if mode not in {"100644", "100755"}:
        _fail(f"{label} mode is not a regular Git file mode")
    size = _require_nonnegative_int(fact["byte_count"], f"{label} byte count")
    if size > MATERIALIZER_BYTE_CAP:
        _fail(f"{label} exceeds its byte cap")
    return {
        "relative_path": relative,
        "git_mode": mode,
        "git_blob_id": _require_object_id(fact["git_blob_id"], f"{label} blob"),
        "byte_count": size,
        "sha256": _require_sha256(fact["sha256"], f"{label} digest"),
    }


_EXTERNAL_ROOT_KEYS = {
    "schema",
    "materialization_rule_id",
    "source_closure_rule_id",
    "repository_root",
    "git_directory",
    "c_pre_commit_id",
    "c_pre_tree_id",
    "bootstrap_git_blob",
    "launcher_git_blob",
    "materializer_git_blob",
    "third_party_source_roots",
    "created_before_v180r12r2_authorized_production_execution",
    "v180r12r2_outcome_bytes_accessed",
}


def load_external_root_v180r12r2(
    repository_root: Path,
    external_root_path: Path,
    expected_sha256: str,
) -> tuple[dict[str, Any], bytes]:
    """Load and validate the externally chosen immutable C_pre root."""

    repository_root = _validated_absolute_directory(
        str(repository_root), "repository root"
    )
    expected_sha256 = _require_sha256(expected_sha256, "external root digest")
    if (
        not external_root_path.is_absolute()
        or external_root_path != repository_root / EXTERNAL_ROOT_RELATIVE_PATH
    ):
        _fail("external root path differs from its frozen repository path")
    raw = _stable_read_file(
        external_root_path,
        label="external root record",
        byte_cap=EXTERNAL_ROOT_BYTE_CAP,
        required_mode=0o400,
        expected_sha256=expected_sha256,
    )
    document = _require_exact_dict(
        _parse_canonical_json_object(raw, "external root record"),
        _EXTERNAL_ROOT_KEYS,
        "external root record",
    )
    if not (
        document["schema"] == EXTERNAL_ROOT_SCHEMA
        and document["materialization_rule_id"] == MATERIALIZATION_RULE_ID
        and document["source_closure_rule_id"] == SOURCE_CLOSURE_RULE_ID
        and document["repository_root"] == str(repository_root)
        and document[
            "created_before_v180r12r2_authorized_production_execution"
        ]
        is True
        and document["v180r12r2_outcome_bytes_accessed"] is False
    ):
        _fail("external root record changed its frozen construction boundary")
    git_directory = _validated_absolute_directory(
        document["git_directory"], "external root Git directory"
    )
    if git_directory != repository_root / ".git":
        _fail("external root Git directory is not the repository-local .git")
    document["c_pre_commit_id"] = _require_commit(
        document["c_pre_commit_id"], "external C_pre commit"
    )
    document["c_pre_tree_id"] = _require_object_id(
        document["c_pre_tree_id"], "external C_pre tree"
    )
    document["bootstrap_git_blob"] = _validated_git_blob_fact(
        document["bootstrap_git_blob"], "external bootstrap Git blob"
    )
    document["launcher_git_blob"] = _validated_git_blob_fact(
        document["launcher_git_blob"], "external launcher Git blob"
    )
    document["materializer_git_blob"] = _validated_git_blob_fact(
        document["materializer_git_blob"], "external materializer Git blob"
    )
    if (
        document["bootstrap_git_blob"]["relative_path"]
        != SOURCE_BOOTSTRAP_RELATIVE_PATH
        or document["bootstrap_git_blob"]["byte_count"] > BOOTSTRAP_BYTE_CAP
        or document["launcher_git_blob"]["relative_path"]
        != SOURCE_LAUNCHER_RELATIVE_PATH
        or document["launcher_git_blob"]["byte_count"] > LAUNCHER_BYTE_CAP
        or document["materializer_git_blob"]["relative_path"]
        != MATERIALIZER_RELATIVE_PATH
        or document["materializer_git_blob"]["byte_count"] > MATERIALIZER_BYTE_CAP
    ):
        _fail("external bootstrap or materializer Git path changed")
    roots = _require_exact_dict(
        document["third_party_source_roots"],
        {"packaging", "tomli"},
        "external third-party source roots",
    )
    document["third_party_source_roots"] = {
        namespace: str(
            _validated_absolute_directory(
                roots[namespace], f"external {namespace} source root"
            )
        )
        for namespace in ("packaging", "tomli")
    }
    return document, raw


def _reject_git_history_overlays(git_directory: Path) -> None:
    forbidden = (
        git_directory / "objects/info/alternates",
        git_directory / "info/grafts",
        git_directory / "shallow",
        git_directory / "refs/replace",
    )
    if any(os.path.lexists(path) for path in forbidden):
        _fail("Git history overlays are forbidden")
    packed_refs = git_directory / "packed-refs"
    if os.path.lexists(packed_refs):
        raw = _stable_read_file(
            packed_refs,
            label="packed refs",
            byte_cap=16 * 1024 * 1024,
        )
        if any(
            line.partition(b" ")[2].startswith(b"refs/replace/")
            for line in raw.splitlines()
            if line and not line.startswith((b"#", b"^"))
        ):
            _fail("Git replace refs are forbidden")


def _parse_ls_tree(raw: bytes) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    for row in raw.split(b"\x00"):
        if not row:
            continue
        try:
            prefix, path_raw = row.split(b"\t", 1)
            mode_raw, kind_raw, object_raw = prefix.split(b" ")
            mode = mode_raw.decode("ascii")
            kind = kind_raw.decode("ascii")
            object_id = object_raw.decode("ascii")
            relative = path_raw.decode("utf-8")
        except (ValueError, UnicodeError) as error:
            raise V180r12r2PrelaunchMaterializationError(
                "Git tree listing is malformed"
            ) from error
        _validated_relative_path(relative, "Git tree path")
        if (
            relative in rows
            or kind != "blob"
            or mode not in {"100644", "100755"}
            or _OBJECT_ID.fullmatch(object_id) is None
        ):
            _fail("Git tree contains a duplicate or nonregular source entry")
        rows[relative] = (mode, object_id)
    return rows


def _archive_blobs(
    repository_root: Path,
    commit_id: str,
    paths: tuple[str, ...],
) -> dict[str, bytes]:
    if not paths or paths != tuple(sorted(set(paths))):
        _fail("Git archive source paths are empty, unsorted, or duplicated")
    raw = _run_git(
        repository_root,
        ("archive", "--format=tar", commit_id, "--", *paths),
        "C_pre source archive",
    )
    blobs: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            for member in archive.getmembers():
                if member.isdir():
                    continue
                if not member.isfile() or member.name in blobs:
                    _fail("C_pre source archive contains a foreign entry")
                extracted = archive.extractfile(member)
                if extracted is None:
                    _fail("C_pre source archive entry is unreadable")
                source = extracted.read(SOURCE_FILE_BYTE_CAP + 1)
                cap = (
                    MATERIALIZER_BYTE_CAP
                    if member.name == MATERIALIZER_RELATIVE_PATH
                    else LAUNCHER_BYTE_CAP
                    if member.name == SOURCE_LAUNCHER_RELATIVE_PATH
                    else BOOTSTRAP_BYTE_CAP
                    if member.name == SOURCE_BOOTSTRAP_RELATIVE_PATH
                    else SOURCE_FILE_BYTE_CAP
                )
                if len(source) != member.size or len(source) > cap:
                    _fail("C_pre source archive entry exceeds its frozen cap")
                blobs[member.name] = source
    except (tarfile.TarError, OSError) as error:
        raise V180r12r2PrelaunchMaterializationError(
            "C_pre source archive is malformed"
        ) from error
    if set(blobs) != set(paths):
        _fail("C_pre source archive omitted or added a source")
    return blobs


def _git_raw_blob(repository_root: Path, object_id: str, label: str, cap: int) -> bytes:
    raw = _run_git(
        repository_root,
        ("cat-file", "blob", object_id),
        label,
        byte_cap=cap,
    )
    if len(raw) > cap:
        _fail(f"{label} exceeded its frozen cap")
    return raw


def verify_git_boundary_v180r12r2(
    repository_root: Path,
    external_root: dict[str, Any],
) -> dict[str, Any]:
    """Verify exact C_pre -> empty bridge -> wrapper-only HEAD topology."""

    c_pre = external_root["c_pre_commit_id"]
    expected_tree = external_root["c_pre_tree_id"]
    git_directory = Path(external_root["git_directory"])
    _reject_git_history_overlays(git_directory)
    revision_raw = _run_git(
        repository_root,
        (
            "rev-parse",
            "--show-toplevel",
            "--absolute-git-dir",
            "--git-common-dir",
            f"{c_pre}^{{commit}}",
            f"{c_pre}^{{tree}}",
            "HEAD^{commit}",
            "HEAD^{tree}",
        ),
        "root and revisions",
        byte_cap=4096,
    )
    try:
        lines = revision_raw.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise V180r12r2PrelaunchMaterializationError(
            "Git root and revision output is non-ASCII"
        ) from error
    if len(lines) != 7:
        _fail("Git root and revision output changed")
    (
        top_level,
        observed_git,
        common_git,
        observed_c_pre,
        observed_tree,
        head,
        head_tree,
    ) = lines
    common_path = Path(common_git)
    if not common_path.is_absolute():
        common_path = repository_root / common_path
    if not (
        Path(top_level).resolve(strict=True) == repository_root
        and Path(observed_git).resolve(strict=True) == git_directory
        and common_path.resolve(strict=True) == git_directory
        and observed_c_pre == c_pre
        and observed_tree == expected_tree
        and _COMMIT_ID.fullmatch(head) is not None
        and _OBJECT_ID.fullmatch(head_tree) is not None
    ):
        _fail("Git root, C_pre, tree, or HEAD differs from the external root")

    chain_raw = _run_git(
        repository_root,
        (
            "log",
            "--first-parent",
            "--reverse",
            "--format=%H%x09%P%x09%T",
            f"{c_pre}..{head}",
        ),
        "exact bridge chain",
        byte_cap=4096,
    )
    try:
        chain_lines = chain_raw.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise V180r12r2PrelaunchMaterializationError(
            "Git bridge chain is non-ASCII"
        ) from error
    if len(chain_lines) != 2:
        _fail("Git history is not exactly C_pre -> bridge -> literal HEAD")
    rows: list[tuple[str, str, str]] = []
    previous = c_pre
    for line in chain_lines:
        fields = line.split("\t")
        if not (
            len(fields) == 3
            and _COMMIT_ID.fullmatch(fields[0]) is not None
            and fields[1] == previous
            and _OBJECT_ID.fullmatch(fields[2]) is not None
        ):
            _fail("Git bridge chain is merged or malformed")
        rows.append((fields[0], fields[1], fields[2]))
        previous = fields[0]
    bridge, literal = rows[0][0], rows[1][0]
    if not (
        rows[0][2] == expected_tree
        and rows[1][0] == head
        and rows[1][2] == head_tree
        and literal != bridge != c_pre
    ):
        _fail("Git empty bridge or literal HEAD identity changed")

    bridge_diff = _run_git(
        repository_root,
        ("diff-tree", "--no-commit-id", "--raw", "--no-renames", "-r", bridge),
        "empty bridge diff",
        byte_cap=4096,
    )
    if bridge_diff:
        _fail("Git bridge commit is not empty")
    literal_diff = _run_git(
        repository_root,
        ("diff-tree", "--no-commit-id", "--raw", "--no-renames", "-r", literal),
        "wrapper literal diff",
        byte_cap=4096,
    )
    try:
        literal_line = literal_diff.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise V180r12r2PrelaunchMaterializationError(
            "Git literal diff is non-UTF-8"
        ) from error
    match = re.fullmatch(
        r":100644 100644 ([0-9a-f]{40,64}) ([0-9a-f]{40,64}) M\t"
        + re.escape(AUTHORIZATION_EVIDENCE_RELATIVE_PATH),
        literal_line,
    )
    if match is None:
        _fail("Git literal HEAD must modify only the regular wrapper")
    return {
        "c_pre_commit_id": c_pre,
        "c_pre_tree_id": expected_tree,
        "empty_bridge_commit_id": bridge,
        "empty_bridge_tree_id": expected_tree,
        "literal_commit_id": literal,
        "literal_commit_tree_id": head_tree,
        "literal_wrapper_prior_blob_id": match.group(1),
        "literal_wrapper_blob_id": match.group(2),
    }


def _module_name_from_relative(relative_path: str) -> tuple[str, bool]:
    if not relative_path.startswith("src/acfqp/") or not relative_path.endswith(".py"):
        _fail("source module path is outside src/acfqp Python sources")
    path = PurePosixPath(relative_path).relative_to("src")
    is_package = path.name == "__init__.py"
    parts = list(path.parts[:-1])
    if not is_package:
        parts.append(path.stem)
    module = ".".join(parts)
    if not (
        module == "acfqp" or module.startswith("acfqp.")
    ) or not all(part.isidentifier() for part in module.split(".")):
        _fail("source module name is invalid")
    return module, is_package


def _absolute_import_base(
    current_module: str,
    current_is_package: bool,
    imported_module: str | None,
    level: int,
) -> str:
    if level == 0:
        return "" if imported_module is None else imported_module
    package = current_module if current_is_package else current_module.rpartition(".")[0]
    parts = package.split(".") if package else []
    if level > len(parts):
        return ""
    prefix = parts[: len(parts) - level + 1]
    if imported_module:
        prefix.extend(imported_module.split("."))
    return ".".join(prefix)


def _local_imports(
    module: str,
    is_package: bool,
    raw: bytes,
    available_names: frozenset[str],
) -> tuple[str, ...]:
    try:
        tree = ast.parse(raw, filename=module)
    except (SyntaxError, TypeError, ValueError) as error:
        raise V180r12r2PrelaunchMaterializationError(
            f"C_pre source module cannot be parsed: {module}"
        ) from error
    discovered: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                candidate = alias.name
                if candidate == "acfqp" or candidate.startswith("acfqp."):
                    if candidate not in available_names:
                        _fail(f"C_pre static import is absent: {candidate}")
                    discovered.add(candidate)
        elif isinstance(node, ast.ImportFrom):
            base = _absolute_import_base(
                module,
                is_package,
                node.module,
                node.level,
            )
            if base == "acfqp" or base.startswith("acfqp."):
                if base not in available_names:
                    _fail(f"C_pre static import base is absent: {base}")
                discovered.add(base)
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    candidate = f"{base}.{alias.name}"
                    if candidate in available_names:
                        discovered.add(candidate)
    return tuple(sorted(discovered))


def _script_import_roots(
    raw: bytes,
    relative_path: str,
    available_names: frozenset[str],
) -> tuple[str, ...]:
    try:
        tree = ast.parse(raw, filename=relative_path)
    except (SyntaxError, TypeError, ValueError) as error:
        raise V180r12r2PrelaunchMaterializationError(
            f"C_pre script cannot be parsed: {relative_path}"
        ) from error
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in available_names:
                    roots.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            module = node.module
            if type(module) is not str or not module.startswith("acfqp"):
                continue
            if module in available_names:
                roots.add(module)
            for alias in node.names:
                candidate = f"{module}.{alias.name}"
                if candidate in available_names:
                    roots.add(candidate)
    return tuple(sorted(roots))


def _normalize_wrapper(raw: bytes) -> tuple[bytes, dict[str, str | int]]:
    try:
        tree = ast.parse(raw, filename=AUTHORIZATION_EVIDENCE_RELATIVE_PATH)
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise V180r12r2PrelaunchMaterializationError(
            "authorization wrapper is not static UTF-8 Python"
        ) from error
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    wanted = set(WRAPPER_REDACTED_CONSTANT_NAMES)
    assignments: dict[str, tuple[int, int, bytes]] = {}
    values: dict[str, str | int] = {}
    for statement in tree.body:
        name: str | None = None
        value: ast.expr | None = None
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        ):
            name = statement.targets[0].id
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target, ast.Name
        ):
            name = statement.target.id
            value = statement.value
        if name not in wanted:
            continue
        if name in assignments or not isinstance(value, ast.Constant):
            _fail("authorization wrapper literal assignment changed")
        literal = value.value
        if name in _WRAPPER_STRING_CONSTANT_NAMES:
            if type(literal) is not str:
                _fail("authorization wrapper string literal changed")
            replacement = _WRAPPER_REDACTED_STRING_LITERAL
            expected_token = tokenize.STRING
        else:
            if name not in _WRAPPER_INTEGER_CONSTANT_NAMES or type(literal) is not int:
                _fail("authorization wrapper integer literal changed")
            replacement = _WRAPPER_REDACTED_INTEGER_LITERAL
            expected_token = tokenize.NUMBER
        positions = (value.lineno, value.col_offset, value.end_lineno, value.end_col_offset)
        if not all(type(item) is int for item in positions):
            _fail("authorization wrapper literal has no exact source span")
        start = offsets[value.lineno - 1] + value.col_offset
        end = offsets[value.end_lineno - 1] + value.end_col_offset
        if not 0 <= start < end <= len(raw):
            _fail("authorization wrapper literal span changed")
        try:
            tokens = tuple(
                token
                for token in tokenize.tokenize(io.BytesIO(raw[start:end]).readline)
                if token.type
                not in {
                    tokenize.ENCODING,
                    tokenize.ENDMARKER,
                    tokenize.NEWLINE,
                    tokenize.NL,
                }
            )
        except (IndentationError, SyntaxError, tokenize.TokenError) as error:
            raise V180r12r2PrelaunchMaterializationError(
                "authorization wrapper literal tokenization failed"
            ) from error
        if len(tokens) != 1 or tokens[0].type != expected_token:
            _fail("authorization wrapper anchor is not one literal token")
        assignments[name] = (start, end, replacement)
        values[name] = literal
    if set(assignments) != wanted or len(assignments) != 8:
        _fail("authorization wrapper eight-literal allowlist changed")
    normalized = raw
    previous_start = len(raw)
    for start, end, replacement in sorted(
        assignments.values(), key=lambda item: item[0], reverse=True
    ):
        if end > previous_start:
            _fail("authorization wrapper literal spans overlap")
        normalized = normalized[:start] + replacement + normalized[end:]
        previous_start = start
    return normalized, values


def _require_boundary_wrapper_sentinels(values: dict[str, str | int]) -> None:
    if not all(
        value == ("0" * 64 if name in _WRAPPER_STRING_CONSTANT_NAMES else 0)
        for name, value in values.items()
    ):
        _fail("C_pre authorization wrapper did not retain all eight sentinels")


def _require_literal_wrapper_values(values: dict[str, str | int]) -> None:
    for name, value in values.items():
        if name in _WRAPPER_STRING_CONSTANT_NAMES:
            if (
                type(value) is not str
                or _SHA256.fullmatch(value) is None
                or value == "0" * 64
            ):
                _fail("literal HEAD did not freeze every wrapper string identity")
        elif type(value) is not int or value <= 0:
            _fail("literal HEAD did not freeze every wrapper integer identity")


def _catalogue_from_c_pre(
    repository_root: Path,
    c_pre: str,
) -> tuple[dict[str, tuple[str, bool, bytes]], dict[str, tuple[str, str]], dict[str, bytes]]:
    tree_raw = _run_git(
        repository_root,
        ("ls-tree", "-r", "-z", "--full-tree", c_pre, "--", "src/acfqp", "scripts"),
        "C_pre source tree",
        byte_cap=16 * 1024 * 1024,
    )
    tree = _parse_ls_tree(tree_raw)
    required_special = {
        SOURCE_BOOTSTRAP_RELATIVE_PATH,
        SOURCE_LAUNCHER_RELATIVE_PATH,
        MATERIALIZER_RELATIVE_PATH,
        *TARGET_RUNNER_PATHS.values(),
        AUTHORIZATION_SELF_RELATIVE_PATH,
        AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
        *_CONTRACT_SOURCE_ROOTS,
        *_PRODUCTION_SOURCE_ROOTS,
        *_VERIFICATION_SOURCE_ROOTS,
    }
    if not required_special <= set(tree):
        missing = sorted(required_special - set(tree))
        _fail(f"C_pre source tree omitted required paths: {missing!r}")
    python_paths = tuple(
        sorted(
            path
            for path in tree
            if path.startswith("src/acfqp/") and path.endswith(".py")
        )
    )
    archive_paths = tuple(sorted({*python_paths, *required_special}))
    blobs = _archive_blobs(repository_root, c_pre, archive_paths)
    catalogue: dict[str, tuple[str, bool, bytes]] = {}
    for relative in python_paths:
        module, is_package = _module_name_from_relative(relative)
        if module in catalogue:
            _fail("C_pre source module catalogue is duplicated")
        catalogue[module] = (relative, is_package, blobs[relative])
    if (
        not catalogue
        or len(catalogue) > SOURCE_CLOSURE_FILE_CAP
        or tuple(catalogue) != tuple(sorted(catalogue))
    ):
        _fail("C_pre source module catalogue exceeds its frozen cap")
    return catalogue, tree, blobs


def build_c_pre_source_closure_v180r12r2(
    repository_root: Path,
    external_root: dict[str, Any],
    topology: dict[str, Any],
) -> dict[str, Any]:
    """Build exact module, runner, wrapper, bootstrap, and materializer facts."""

    c_pre = external_root["c_pre_commit_id"]
    catalogue, tree, blobs = _catalogue_from_c_pre(repository_root, c_pre)
    available = frozenset(catalogue)
    all_roots = (
        *_PRODUCTION_SOURCE_ROOTS,
        *_VERIFICATION_SOURCE_ROOTS,
        *_CONTRACT_SOURCE_ROOTS,
    )
    script_roots = tuple(path for path in all_roots if path.startswith("scripts/"))
    explicit_modules = {
        _module_name_from_relative(path)[0]
        for path in all_roots
        if path.startswith("src/acfqp/")
    }
    for relative in script_roots:
        explicit_modules.update(
            _script_import_roots(blobs[relative], relative, available)
        )
    if not explicit_modules <= available:
        _fail("C_pre source closure root is absent")
    pending = list(reversed(sorted(explicit_modules)))
    included: set[str] = set()
    while pending:
        module = pending.pop()
        if module in included:
            continue
        if len(included) >= SOURCE_CLOSURE_FILE_CAP:
            _fail("C_pre recursive source closure exceeds its file cap")
        included.add(module)
        relative, is_package, raw = catalogue[module]
        pending.extend(
            reversed(
                tuple(
                    name
                    for name in _local_imports(module, is_package, raw, available)
                    if name not in included
                )
            )
        )
        parts = module.split(".")
        for end in range(1, len(parts)):
            parent = ".".join(parts[:end])
            if parent not in catalogue:
                _fail("C_pre recursive source closure omitted a parent package")
            if parent not in included:
                pending.append(parent)
    included.discard(AUTHORIZATION_SELF_MODULE)
    if AUTHORIZATION_EVIDENCE_MODULE not in included:
        _fail("C_pre recursive source closure omitted the evidence wrapper")

    # The special prelaunch sources are independently bound by the external root.
    for key, relative, cap in (
        ("bootstrap_git_blob", SOURCE_BOOTSTRAP_RELATIVE_PATH, BOOTSTRAP_BYTE_CAP),
        ("launcher_git_blob", SOURCE_LAUNCHER_RELATIVE_PATH, LAUNCHER_BYTE_CAP),
        ("materializer_git_blob", MATERIALIZER_RELATIVE_PATH, MATERIALIZER_BYTE_CAP),
    ):
        fact = external_root[key]
        mode, object_id = tree[relative]
        raw = blobs[relative]
        if not (
            fact["git_mode"] == mode
            and fact["git_blob_id"] == object_id
            and fact["byte_count"] == len(raw) <= cap
            and fact["sha256"] == hashlib.sha256(raw).hexdigest()
        ):
            _fail(f"external {relative} fact differs from its C_pre Git blob")

    current_materializer = _stable_read_file(
        repository_root / MATERIALIZER_RELATIVE_PATH,
        label="current materializer source",
        byte_cap=MATERIALIZER_BYTE_CAP,
        expected_size=len(blobs[MATERIALIZER_RELATIVE_PATH]),
        expected_sha256=hashlib.sha256(blobs[MATERIALIZER_RELATIVE_PATH]).hexdigest(),
    )
    if current_materializer != blobs[MATERIALIZER_RELATIVE_PATH]:
        _fail("executing materializer differs from its C_pre Git blob")
    if Path(__file__).resolve(strict=True) != repository_root / MATERIALIZER_RELATIVE_PATH:
        _fail("executing materializer path differs from the repository binding")

    boundary_wrapper = blobs[AUTHORIZATION_EVIDENCE_RELATIVE_PATH]
    current_wrapper = _stable_read_file(
        repository_root / AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
        label="current literal wrapper source",
        byte_cap=SOURCE_FILE_BYTE_CAP,
    )
    committed_wrapper = _git_raw_blob(
        repository_root,
        topology["literal_wrapper_blob_id"],
        "literal wrapper blob",
        SOURCE_FILE_BYTE_CAP,
    )
    if current_wrapper != committed_wrapper:
        _fail("current wrapper bytes differ from the literal HEAD blob")
    boundary_normalized, boundary_values = _normalize_wrapper(boundary_wrapper)
    current_normalized, current_values = _normalize_wrapper(current_wrapper)
    _require_boundary_wrapper_sentinels(boundary_values)
    _require_literal_wrapper_values(current_values)
    if boundary_normalized != current_normalized:
        _fail("literal HEAD changed wrapper bytes outside the eight literals")

    source_modules: list[dict[str, Any]] = []
    authorization_raw_names: list[str] = []
    authorization_facts: list[dict[str, Any]] = []
    for module in sorted({*included, AUTHORIZATION_SELF_MODULE}):
        relative, is_package, boundary_raw = catalogue[module]
        current_raw = _stable_read_file(
            repository_root / relative,
            label=f"current source module {module}",
            byte_cap=SOURCE_FILE_BYTE_CAP,
        )
        if module == AUTHORIZATION_EVIDENCE_MODULE:
            manifest_raw = current_raw
            if current_raw != current_wrapper:
                _fail("current wrapper source changed during closure replay")
        else:
            if current_raw != boundary_raw:
                _fail(f"current ordinary source differs from C_pre: {relative}")
            manifest_raw = boundary_raw
        source_modules.append(
            {
                "module": module,
                "is_package": is_package,
                **_raw_fact(relative, manifest_raw),
            }
        )
        if module == AUTHORIZATION_SELF_MODULE:
            continue
        authorization_raw_names.append(module)
        if module == AUTHORIZATION_EVIDENCE_MODULE:
            authorization_facts.append(
                {
                    **_raw_fact(relative, boundary_normalized),
                    "binding_kind": NORMALIZED_WRAPPER_BINDING_KIND,
                    "redacted_constant_names": list(WRAPPER_REDACTED_CONSTANT_NAMES),
                }
            )
        else:
            authorization_facts.append(_raw_fact(relative, boundary_raw))

    targets: dict[str, dict[str, Any]] = {}
    for target, relative in TARGET_RUNNER_PATHS.items():
        raw = blobs[relative]
        if len(raw) > RUNNER_BYTE_CAP:
            _fail(f"C_pre {target} runner exceeds its byte cap")
        current = _stable_read_file(
            repository_root / relative,
            label=f"current {target} runner",
            byte_cap=RUNNER_BYTE_CAP,
            expected_size=len(raw),
            expected_sha256=hashlib.sha256(raw).hexdigest(),
        )
        if current != raw:
            _fail(f"current {target} runner differs from C_pre")
        targets[target] = _raw_fact(relative, raw)
        authorization_facts.append(_raw_fact(relative, raw))

    if len(source_modules) + len(targets) > SOURCE_CLOSURE_FILE_CAP:
        _fail("combined C_pre source closure exceeds its file cap")
    return {
        "bootstrap_raw": blobs[SOURCE_BOOTSTRAP_RELATIVE_PATH],
        "launcher_raw": blobs[SOURCE_LAUNCHER_RELATIVE_PATH],
        "materializer_raw_fact": _raw_fact(
            MATERIALIZER_RELATIVE_PATH, blobs[MATERIALIZER_RELATIVE_PATH]
        ),
        "source_modules": source_modules,
        "authorization_raw_source_modules": sorted(authorization_raw_names),
        "authorization_source_closure": _closure(
            authorization_facts, sort_key="relative_path"
        ),
        "targets": targets,
        "boundary_wrapper_normalized_fact": {
            **_raw_fact(AUTHORIZATION_EVIDENCE_RELATIVE_PATH, boundary_normalized),
            "binding_kind": NORMALIZED_WRAPPER_BINDING_KIND,
            "redacted_constant_names": list(WRAPPER_REDACTED_CONSTANT_NAMES),
        },
        "current_wrapper_raw_fact": _raw_fact(
            AUTHORIZATION_EVIDENCE_RELATIVE_PATH, current_wrapper
        ),
    }


def _third_party_module_name(relative: PurePosixPath) -> tuple[str, bool]:
    is_package = relative.name == "__init__.py"
    parts = list(relative.parts[:-1])
    if not is_package:
        parts.append(relative.stem)
    if not parts or not all(part.isidentifier() for part in parts):
        _fail("third-party Python source path is not importable")
    return ".".join(parts), is_package


def build_third_party_source_closure_v180r12r2(
    external_root: dict[str, Any],
) -> dict[str, Any]:
    facts: list[dict[str, Any]] = []
    observed_modules: set[str] = set()
    total = 0
    for namespace in ("packaging", "tomli"):
        root = Path(external_root["third_party_source_roots"][namespace])
        namespace_root = root / namespace
        _validated_absolute_directory(str(namespace_root), f"{namespace} namespace root")
        candidates = sorted(namespace_root.rglob("*.py"))
        if not candidates:
            _fail(f"{namespace} source closure is empty")
        for path in candidates:
            relative = PurePosixPath(path.relative_to(root).as_posix())
            module, is_package = _third_party_module_name(relative)
            if module in observed_modules or not (
                module == namespace or module.startswith(f"{namespace}.")
            ):
                _fail("third-party source closure is duplicated or escaped")
            raw = _stable_read_file(
                path,
                label=f"third-party source {module}",
                byte_cap=SOURCE_FILE_BYTE_CAP,
            )
            total += len(raw)
            if (
                len(facts) >= SOURCE_CLOSURE_FILE_CAP
                or total > SOURCE_CLOSURE_TOTAL_BYTE_CAP
            ):
                _fail("third-party source closure exceeds its frozen cap")
            observed_modules.add(module)
            facts.append(
                {
                    "module": module,
                    "is_package": is_package,
                    "source_root": str(root),
                    **_raw_fact(relative.as_posix(), raw),
                }
            )
    return _closure(facts, sort_key="module")


def _resolved_regular_executable_fact(
    requested: str,
    label: str,
) -> tuple[Path, bytes, int]:
    requested_path = Path(requested)
    if not requested_path.is_absolute() or str(requested_path) != requested:
        _fail(f"requested {label} path changed")
    try:
        resolved = requested_path.resolve(strict=True)
    except OSError as error:
        raise V180r12r2PrelaunchMaterializationError(
            f"requested {label} cannot be resolved"
        ) from error
    raw = _stable_read_file(
        resolved,
        label=f"resolved {label}",
        byte_cap=EXECUTABLE_BYTE_CAP,
    )
    metadata = os.lstat(resolved)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        _fail(f"resolved {label} is not one singly linked regular file")
    return resolved, raw, metadata.st_mode


def build_runtime_tcb_fact_v180r12r2() -> dict[str, Any]:
    if sys.executable != PYTHON_EXECUTABLE:
        _fail("materializer requires exact /usr/bin/python3")
    expected_flags = {
        "isolated": 1,
        "no_site": 1,
        "no_user_site": 1,
        "ignore_environment": 1,
        "dont_write_bytecode": 1,
    }
    if (
        {name: getattr(sys.flags, name) for name in expected_flags} != expected_flags
        or sys.pycache_prefix != PYCACHE_PREFIX
        or sys.dont_write_bytecode is not True
    ):
        _fail("materializer isolated Python flags changed")
    dev_null = os.lstat("/dev/null")
    if not (
        stat.S_ISCHR(dev_null.st_mode)
        and os.major(dev_null.st_rdev) == 1
        and os.minor(dev_null.st_rdev) == 3
    ):
        _fail("/dev/null is not character device 1:3")
    resolved, raw, _mode = _resolved_regular_executable_fact(
        PYTHON_EXECUTABLE, "Python executable"
    )
    return {
        "requested_executable": PYTHON_EXECUTABLE,
        "resolved_executable": str(resolved),
        "executable_byte_count": len(raw),
        "executable_sha256": hashlib.sha256(raw).hexdigest(),
        "version": sys.version,
        "version_info": list(sys.version_info),
        "soabi": sysconfig.get_config_var("SOABI"),
        "base_sys_path": list(sys.path),
        "orig_argv_prefix": list(ISOLATED_ARGV_PREFIX),
        "pycache_prefix": PYCACHE_PREFIX,
        "flags": expected_flags,
    }


def _source_boundary_paths(source_plan: dict[str, Any]) -> tuple[str, ...]:
    paths = {
        fact["relative_path"]
        for fact in source_plan["authorization_source_closure"]["facts"]
    }
    paths.update(
        {
            AUTHORIZATION_SELF_RELATIVE_PATH,
            SOURCE_BOOTSTRAP_RELATIVE_PATH,
            SOURCE_LAUNCHER_RELATIVE_PATH,
            MATERIALIZER_RELATIVE_PATH,
        }
    )
    return tuple(sorted(paths))


def build_git_tcb_fact_v180r12r2(
    repository_root: Path,
    external_root: dict[str, Any],
    topology: dict[str, Any],
    source_plan: dict[str, Any],
) -> dict[str, Any]:
    resolved, raw, mode = _resolved_regular_executable_fact(
        GIT_EXECUTABLE, "Git executable"
    )
    version_argv = [GIT_EXECUTABLE, "--version"]
    version_environment = {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "LC_ALL": "C",
    }
    try:
        completed = subprocess.run(
            version_argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            env=version_environment,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise V180r12r2PrelaunchMaterializationError(
            "Git version probe failed"
        ) from error
    if (
        completed.returncode != 0
        or completed.stderr
        or not completed.stdout.endswith(b"\n")
        or len(completed.stdout) > 1024
    ):
        _fail("Git version probe changed")
    try:
        version_stdout = completed.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise V180r12r2PrelaunchMaterializationError(
            "Git version output is non-UTF-8"
        ) from error

    c_pre = external_root["c_pre_commit_id"]
    head = topology["literal_commit_id"]
    paths = _source_boundary_paths(source_plan)
    prefix = [GIT_EXECUTABLE, "-C", str(repository_root)]
    runner_argv = [
        [
            *prefix,
            "rev-parse",
            "--show-toplevel",
            "--absolute-git-dir",
            "--git-common-dir",
            f"{c_pre}^{{commit}}",
            f"{c_pre}^{{tree}}",
            "HEAD^{commit}",
        ],
        [
            *prefix,
            "log",
            "--first-parent",
            "--reverse",
            "--format=%H%x09%P%x09%T",
            f"{c_pre}..{head}",
        ],
        [
            *prefix,
            "diff-tree",
            "--no-commit-id",
            "--raw",
            "--no-renames",
            "-r",
            head,
        ],
        [
            *prefix,
            "log",
            "--first-parent",
            "--format=%H",
            "--name-only",
            "--no-renames",
            f"{head}..{head}",
            "--",
            *paths,
        ],
        [*prefix, "archive", "--format=tar", c_pre, "--", *paths],
        [*prefix, "cat-file", "blob", topology["literal_wrapper_blob_id"]],
    ]
    return {
        "requested_executable": GIT_EXECUTABLE,
        "resolved_executable": str(resolved),
        "executable_mode": mode,
        "executable_byte_count": len(raw),
        "executable_sha256": hashlib.sha256(raw).hexdigest(),
        "version_argv": version_argv,
        "version_environment": version_environment,
        "version_stdout": version_stdout,
        "runner_process_count": 6,
        "runner_argv": runner_argv,
        "runner_environment_template": {
            MANIFEST_SHA256_ENV: MANIFEST_SHA256_TEMPLATE,
            PREREG_COMMIT_ENV: c_pre,
            "LC_CTYPE": "C.UTF-8",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        },
    }


def build_launch_manifest_v180r12r2(
    repository_root: Path,
    output_root: Path,
    external_root: dict[str, Any],
    topology: dict[str, Any],
    source_plan: dict[str, Any],
    third_party_closure: dict[str, Any],
) -> tuple[dict[str, Any], bytes]:
    """Construct canonical bootstrap-compatible manifest bytes without a cycle."""

    manifest = {
        "schema": LAUNCH_MANIFEST_SCHEMA,
        "repository_root": str(repository_root),
        "c_pre_root": str(output_root),
        "manifest_relative_path": "launch_manifest.json",
        "c_pre_commit_id": external_root["c_pre_commit_id"],
        "bootstrap": _raw_fact("bootstrap.py", source_plan["bootstrap_raw"]),
        "runtime": build_runtime_tcb_fact_v180r12r2(),
        "git": build_git_tcb_fact_v180r12r2(
            repository_root, external_root, topology, source_plan
        ),
        "authorization_source_closure_kind": AUTHORIZATION_SOURCE_CLOSURE_KIND,
        "authorization_self_module": AUTHORIZATION_SELF_MODULE,
        "authorization_raw_source_modules": source_plan[
            "authorization_raw_source_modules"
        ],
        "authorization_source_closure": source_plan[
            "authorization_source_closure"
        ],
        "source_modules": source_plan["source_modules"],
        "third_party_source_closure": third_party_closure,
        "targets": source_plan["targets"],
        "working_tree_mutation_after_snapshot_in_scope": False,
    }
    raw = canonical_json_bytes(manifest)
    if len(raw) > LAUNCH_MANIFEST_BYTE_CAP:
        _fail("launch manifest exceeds its frozen byte cap")
    if MANIFEST_SHA256_TEMPLATE.encode("ascii") in raw:
        # The sentinel belongs only inside the Git environment template.  It is
        # intentionally not replaced with the manifest's self-digest.
        if raw.count(MANIFEST_SHA256_TEMPLATE.encode("ascii")) != 1:
            _fail("launch manifest digest sentinel count changed")
    else:
        _fail("launch manifest digest sentinel is absent")
    return manifest, raw


def _open_or_create_directory_at(parent_fd: int, name: str) -> tuple[int, bool]:
    if "/" in name or name in {"", ".", ".."}:
        _fail("directory component is malformed")
    created = False
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        created = True
        os.fsync(parent_fd)
    except FileExistsError:
        pass
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError as error:
        raise V180r12r2PrelaunchMaterializationError(
            f"directory component is absent, linked, or nondirectory: {name}"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        _fail(f"directory component is nondirectory: {name}")
    if created:
        os.fchmod(descriptor, 0o700)
        os.fsync(descriptor)
    return descriptor, created


def _prepare_exact_freeze_parent(repository_root: Path) -> int:
    root_fd = os.open(
        repository_root,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    descriptor = root_fd
    try:
        for component in (".tmp", "exact-freeze"):
            child, _created = _open_or_create_directory_at(descriptor, component)
            if descriptor != root_fd:
                os.close(descriptor)
            descriptor = child
        os.close(root_fd)
        return descriptor
    except BaseException:
        if descriptor != root_fd:
            os.close(descriptor)
        os.close(root_fd)
        raise


def _entry_exists_at(directory_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise V180r12r2PrelaunchMaterializationError(
            f"cannot inspect prior materialization entry: {name}"
        ) from error
    return True


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    offset = 0
    while offset < len(view):
        written = os.write(descriptor, view[offset : offset + 1024 * 1024])
        if written <= 0:
            _fail("write-once file write made no progress")
        offset += written


def _write_file_once_at(
    directory_fd: int,
    name: str,
    raw: bytes,
) -> None:
    if "/" in name or name in {"", ".", ".."} or type(raw) is not bytes:
        _fail("write-once file request is malformed")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
    )
    descriptor = os.open(name, flags, 0o400, dir_fd=directory_fd)
    try:
        os.fchmod(descriptor, 0o400)
        _write_all(descriptor, raw)
        metadata = os.fstat(descriptor)
        if not (
            stat.S_ISREG(metadata.st_mode)
            and metadata.st_nlink == 1
            and stat.S_IMODE(metadata.st_mode) == 0o400
            and metadata.st_size == len(raw)
        ):
            _fail("write-once file metadata changed")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.fsync(directory_fd)


def _create_output_root(exact_freeze_fd: int) -> int:
    name = PurePosixPath(OUTPUT_ROOT_RELATIVE_PATH).name
    try:
        os.mkdir(name, 0o700, dir_fd=exact_freeze_fd)
    except FileExistsError as error:
        raise V180r12r2PrelaunchMaterializationReplayForbidden(
            "prelaunch materialization output root already exists; rerun forbidden"
        ) from error
    os.fsync(exact_freeze_fd)
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=exact_freeze_fd,
    )
    os.fchmod(descriptor, 0o700)
    os.fsync(descriptor)
    if stat.S_IMODE(os.fstat(descriptor).st_mode) != 0o700:
        os.close(descriptor)
        _fail("prelaunch materialization output root mode changed")
    return descriptor


def _bounded_error_text(error: BaseException) -> tuple[str, str]:
    error_type = type(error).__name__[:128]
    try:
        message = str(error)
    except BaseException:
        message = "UNFORMATTABLE_EXCEPTION"
    raw = message.encode("utf-8", errors="replace")[:FAILURE_MESSAGE_BYTE_CAP]
    while True:
        try:
            message = raw.decode("utf-8")
            break
        except UnicodeDecodeError:
            raw = raw[:-1]
    return error_type, message


def _observe_fixed_entry(path: Path, byte_cap: int) -> dict[str, Any]:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return {"presence": "ABSENT"}
    except OSError:
        return {"presence": "OBSERVATION_ERROR"}
    if stat.S_ISLNK(metadata.st_mode):
        return {"presence": "SYMLINK"}
    if stat.S_ISDIR(metadata.st_mode):
        return {
            "presence": "DIRECTORY",
            "mode": stat.S_IMODE(metadata.st_mode),
        }
    if not stat.S_ISREG(metadata.st_mode):
        return {"presence": "NONREGULAR"}
    observation: dict[str, Any] = {
        "presence": "REGULAR_FILE",
        "mode": stat.S_IMODE(metadata.st_mode),
        "byte_count": metadata.st_size,
    }
    if metadata.st_size <= byte_cap:
        try:
            raw = _stable_read_file(
                path,
                label=f"partial artifact {path.name}",
                byte_cap=byte_cap,
            )
        except BaseException as error:
            observation["read_error_type"] = type(error).__name__[:128]
        else:
            observation["sha256"] = hashlib.sha256(raw).hexdigest()
    else:
        observation["sha256"] = None
        observation["byte_cap_exceeded"] = True
    return observation


def observe_materialization_progress_v180r12r2(
    repository_root: Path,
) -> dict[str, Any]:
    output_root = repository_root / OUTPUT_ROOT_RELATIVE_PATH
    return {
        "output_root": _observe_fixed_entry(output_root, 0),
        "bootstrap": _observe_fixed_entry(
            repository_root / BOOTSTRAP_RELATIVE_PATH, BOOTSTRAP_BYTE_CAP
        ),
        "launcher": _observe_fixed_entry(
            repository_root / RETAINED_LAUNCHER_RELATIVE_PATH, LAUNCHER_BYTE_CAP
        ),
        "launch_manifest": _observe_fixed_entry(
            repository_root / LAUNCH_MANIFEST_RELATIVE_PATH,
            LAUNCH_MANIFEST_BYTE_CAP,
        ),
        "materialization_terminal": _observe_fixed_entry(
            repository_root / MATERIALIZATION_TERMINAL_RELATIVE_PATH,
            LAUNCH_MANIFEST_BYTE_CAP,
        ),
        "materialization_failure": _observe_fixed_entry(
            repository_root / MATERIALIZATION_FAILURE_RELATIVE_PATH,
            LAUNCH_MANIFEST_BYTE_CAP,
        ),
    }


def build_materialization_terminal_v180r12r2(
    *,
    repository_root: Path,
    external_root_path: Path,
    external_root_raw: bytes,
    external_root: dict[str, Any],
    topology: dict[str, Any],
    source_plan: dict[str, Any],
    third_party_closure: dict[str, Any],
    manifest_raw: bytes,
) -> tuple[dict[str, Any], bytes]:
    payload = {
        "schema": MATERIALIZATION_TERMINAL_SCHEMA,
        "materialization_rule_id": MATERIALIZATION_RULE_ID,
        "source_closure_rule_id": SOURCE_CLOSURE_RULE_ID,
        "repository_root": str(repository_root),
        "external_root": {
            "absolute_path": str(external_root_path),
            "byte_count": len(external_root_raw),
            "sha256": hashlib.sha256(external_root_raw).hexdigest(),
            "immutable_mode": "0400",
        },
        "git_topology": topology,
        "bootstrap_source_git_blob": external_root["bootstrap_git_blob"],
        "launcher_source_git_blob": external_root["launcher_git_blob"],
        "materializer_source_git_blob": external_root["materializer_git_blob"],
        "retained_bootstrap": _raw_fact(
            BOOTSTRAP_RELATIVE_PATH, source_plan["bootstrap_raw"]
        ),
        "retained_launcher": _raw_fact(
            RETAINED_LAUNCHER_RELATIVE_PATH, source_plan["launcher_raw"]
        ),
        "launch_manifest": _raw_fact(
            LAUNCH_MANIFEST_RELATIVE_PATH, manifest_raw
        ),
        "materialization_terminal_relative_path": (
            MATERIALIZATION_TERMINAL_RELATIVE_PATH
        ),
        "materialization_failure_relative_path": (
            MATERIALIZATION_FAILURE_RELATIVE_PATH
        ),
        "authorization_source_closure_file_count": source_plan[
            "authorization_source_closure"
        ]["file_count"],
        "authorization_source_closure_total_byte_count": source_plan[
            "authorization_source_closure"
        ]["total_byte_count"],
        "authorization_source_closure_facts_sha256": source_plan[
            "authorization_source_closure"
        ]["facts_sha256"],
        "third_party_source_closure_file_count": third_party_closure["file_count"],
        "third_party_source_closure_total_byte_count": third_party_closure[
            "total_byte_count"
        ],
        "third_party_source_closure_facts_sha256": third_party_closure[
            "facts_sha256"
        ],
        "normalized_wrapper_fact": source_plan[
            "boundary_wrapper_normalized_fact"
        ],
        "current_literal_wrapper_raw_observation": source_plan[
            "current_wrapper_raw_fact"
        ],
        "launch_manifest_digest_is_runtime_supplied_not_protocol_frozen": True,
        "launch_manifest_has_no_self_digest": True,
        "external_root_created_before_authorized_production_execution": True,
        "external_root_required_before_authorization_issuance": False,
        "materialization_terminal_written_last": True,
        "write_once_o_excl": True,
        "write_no_follow": True,
        "close_on_exec": True,
        "output_directory_mode": "0700",
        "output_file_mode": "0400",
        "file_and_directory_fsync_required": True,
        "same_materialization_identity_rerun_forbidden": True,
        "construction_only": True,
        "preauthorization_supervision": True,
        "campaign_actual_measurement": False,
        "scientific_occurrence_executed": False,
        "v180r12r2_outcome_bytes_accessed": False,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_execution_allowed": False,
        "success": True,
    }
    terminal_id = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    document = {**payload, "materialization_terminal_id": terminal_id}
    return document, canonical_json_bytes(document)


def build_materialization_failure_v180r12r2(
    *,
    repository_root: Path,
    external_root_path: Path,
    expected_external_root_sha256: str,
    failed_phase: str,
    error: BaseException,
) -> tuple[dict[str, Any], bytes]:
    error_type, message = _bounded_error_text(error)
    payload = {
        "schema": MATERIALIZATION_FAILURE_SCHEMA,
        "materialization_rule_id": MATERIALIZATION_RULE_ID,
        "source_closure_rule_id": SOURCE_CLOSURE_RULE_ID,
        "repository_root": str(repository_root),
        "external_root_absolute_path": str(external_root_path),
        "expected_external_root_sha256": expected_external_root_sha256,
        "failed_phase": failed_phase,
        "failure_type": error_type,
        "failure_message": message,
        "partial_artifact_observations": observe_materialization_progress_v180r12r2(
            repository_root
        ),
        "same_materialization_identity_rerun_forbidden": True,
        "partial_artifacts_preserved": True,
        "construction_only": True,
        "preauthorization_supervision": True,
        "campaign_actual_measurement": False,
        "scientific_occurrence_executed": False,
        "v180r12r2_outcome_bytes_accessed": False,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_execution_allowed": False,
        "success": False,
    }
    failure_id = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    document = {**payload, "materialization_failure_id": failure_id}
    return document, canonical_json_bytes(document)


def _require_materializer_process_boundary(
    repository_root: Path,
    external_root_path: Path,
    expected_sha256: str,
) -> None:
    expected_environment = {EXTERNAL_ROOT_SHA256_ENV, "LC_CTYPE"}
    if (
        set(os.environ) != expected_environment
        or os.environ.get("LC_CTYPE") != "C.UTF-8"
        or os.environ.get(EXTERNAL_ROOT_SHA256_ENV) != expected_sha256
    ):
        _fail("materializer environment is not exact and sanitized")
    script_path = repository_root / MATERIALIZER_RELATIVE_PATH
    expected_orig_argv = [
        *ISOLATED_ARGV_PREFIX,
        str(script_path),
        str(repository_root),
        str(external_root_path),
    ]
    expected_argv = [
        str(script_path),
        str(repository_root),
        str(external_root_path),
    ]
    if (
        sys.orig_argv != expected_orig_argv
        or sys.argv != expected_argv
        or Path.cwd().resolve(strict=True) != repository_root
        or Path(__file__).resolve(strict=True) != script_path
    ):
        _fail("materializer exact argv, cwd, or source path changed")
    # This also rejects missing isolation flags and binds /dev/null.
    build_runtime_tcb_fact_v180r12r2()


def _write_failure_if_absent(
    *,
    exact_freeze_fd: int,
    repository_root: Path,
    external_root_path: Path,
    expected_external_root_sha256: str,
    failed_phase: str,
    error: BaseException,
) -> None:
    failure_name = PurePosixPath(MATERIALIZATION_FAILURE_RELATIVE_PATH).name
    if _entry_exists_at(exact_freeze_fd, failure_name):
        return
    _document, raw = build_materialization_failure_v180r12r2(
        repository_root=repository_root,
        external_root_path=external_root_path,
        expected_external_root_sha256=expected_external_root_sha256,
        failed_phase=failed_phase,
        error=error,
    )
    _write_file_once_at(exact_freeze_fd, failure_name, raw)


def materialize_prelaunch_v180r12r2(
    repository_root: Path,
    external_root_path: Path,
    expected_external_root_sha256: str,
    *,
    enforce_process_boundary: bool = True,
) -> dict[str, Any]:
    """Perform the fixed one-shot prelaunch materialization.

    The returned document is exactly the retained terminal.  Any failure after
    the fixed path is resolved freezes typed sibling evidence and preserves all
    partial artifacts.  Existing progress, success, or failure forbids replay.
    """

    repository_root = _validated_absolute_directory(
        str(repository_root), "repository root"
    )
    expected_external_root_sha256 = _require_sha256(
        expected_external_root_sha256, "external root environment digest"
    )
    if not external_root_path.is_absolute():
        _fail("external root path must be absolute")
    expected_external_path = repository_root / EXTERNAL_ROOT_RELATIVE_PATH
    if external_root_path != expected_external_path:
        _fail("external root path differs from its frozen sibling path")
    if enforce_process_boundary:
        _require_materializer_process_boundary(
            repository_root,
            external_root_path,
            expected_external_root_sha256,
        )

    exact_freeze_fd = _prepare_exact_freeze_parent(repository_root)
    output_name = PurePosixPath(OUTPUT_ROOT_RELATIVE_PATH).name
    failure_name = PurePosixPath(MATERIALIZATION_FAILURE_RELATIVE_PATH).name
    terminal_path = repository_root / MATERIALIZATION_TERMINAL_RELATIVE_PATH
    failed_phase = "PREEXISTING_PROGRESS_CHECK"
    try:
        if _entry_exists_at(exact_freeze_fd, failure_name):
            raise V180r12r2PrelaunchMaterializationReplayForbidden(
                "prelaunch materialization failure already exists; rerun forbidden"
            )
        if _entry_exists_at(exact_freeze_fd, output_name):
            if terminal_path.exists():
                raise V180r12r2PrelaunchMaterializationReplayForbidden(
                    "prelaunch materialization terminal already exists; rerun forbidden"
                )
            error = V180r12r2PrelaunchMaterializationReplayForbidden(
                "prelaunch materialization partial output exists; rerun forbidden"
            )
            _write_failure_if_absent(
                exact_freeze_fd=exact_freeze_fd,
                repository_root=repository_root,
                external_root_path=external_root_path,
                expected_external_root_sha256=expected_external_root_sha256,
                failed_phase=failed_phase,
                error=error,
            )
            raise error

        failed_phase = "EXTERNAL_ROOT_VALIDATION"
        external_root, external_root_raw = load_external_root_v180r12r2(
            repository_root,
            external_root_path,
            expected_external_root_sha256,
        )
        failed_phase = "GIT_TOPOLOGY_VALIDATION"
        topology = verify_git_boundary_v180r12r2(repository_root, external_root)
        failed_phase = "C_PRE_SOURCE_CLOSURE"
        source_plan = build_c_pre_source_closure_v180r12r2(
            repository_root, external_root, topology
        )
        failed_phase = "THIRD_PARTY_SOURCE_CLOSURE"
        third_party_closure = build_third_party_source_closure_v180r12r2(
            external_root
        )
        if (
            len(source_plan["source_modules"])
            + len(source_plan["targets"])
            + third_party_closure["file_count"]
            > SOURCE_CLOSURE_FILE_CAP
            or sum(row["byte_count"] for row in source_plan["source_modules"])
            + sum(row["byte_count"] for row in source_plan["targets"].values())
            + third_party_closure["total_byte_count"]
            > SOURCE_CLOSURE_TOTAL_BYTE_CAP
        ):
            _fail("combined bootstrap source closure exceeds its frozen cap")
        failed_phase = "LAUNCH_MANIFEST_CONSTRUCTION"
        _manifest, manifest_raw = build_launch_manifest_v180r12r2(
            repository_root,
            repository_root / OUTPUT_ROOT_RELATIVE_PATH,
            external_root,
            topology,
            source_plan,
            third_party_closure,
        )
        terminal, terminal_raw = build_materialization_terminal_v180r12r2(
            repository_root=repository_root,
            external_root_path=external_root_path,
            external_root_raw=external_root_raw,
            external_root=external_root,
            topology=topology,
            source_plan=source_plan,
            third_party_closure=third_party_closure,
            manifest_raw=manifest_raw,
        )

        failed_phase = "OUTPUT_ROOT_CREATE"
        output_fd = _create_output_root(exact_freeze_fd)
        try:
            failed_phase = "BOOTSTRAP_WRITE"
            _write_file_once_at(output_fd, "bootstrap.py", source_plan["bootstrap_raw"])
            failed_phase = "LAUNCHER_WRITE"
            _write_file_once_at(output_fd, "launcher.py", source_plan["launcher_raw"])
            failed_phase = "LAUNCH_MANIFEST_WRITE"
            _write_file_once_at(output_fd, "launch_manifest.json", manifest_raw)
            failed_phase = "PRETERMINAL_REPLAY"
            retained_bootstrap = _stable_read_file(
                repository_root / BOOTSTRAP_RELATIVE_PATH,
                label="retained bootstrap",
                byte_cap=BOOTSTRAP_BYTE_CAP,
                required_mode=0o400,
                expected_size=len(source_plan["bootstrap_raw"]),
                expected_sha256=hashlib.sha256(
                    source_plan["bootstrap_raw"]
                ).hexdigest(),
            )
            retained_manifest = _stable_read_file(
                repository_root / LAUNCH_MANIFEST_RELATIVE_PATH,
                label="retained launch manifest",
                byte_cap=LAUNCH_MANIFEST_BYTE_CAP,
                required_mode=0o400,
                expected_size=len(manifest_raw),
                expected_sha256=hashlib.sha256(manifest_raw).hexdigest(),
            )
            retained_launcher = _stable_read_file(
                repository_root / RETAINED_LAUNCHER_RELATIVE_PATH,
                label="retained launcher",
                byte_cap=LAUNCHER_BYTE_CAP,
                required_mode=0o400,
                expected_size=len(source_plan["launcher_raw"]),
                expected_sha256=hashlib.sha256(
                    source_plan["launcher_raw"]
                ).hexdigest(),
            )
            if (
                retained_bootstrap != source_plan["bootstrap_raw"]
                or retained_launcher != source_plan["launcher_raw"]
                or retained_manifest != manifest_raw
            ):
                _fail("retained prelaunch bytes changed before terminal write")
            failed_phase = "MATERIALIZATION_TERMINAL_WRITE"
            _write_file_once_at(output_fd, "MATERIALIZATION_TERMINAL.json", terminal_raw)
        finally:
            os.close(output_fd)
        failed_phase = "POSTTERMINAL_REPLAY"
        retained_terminal = _stable_read_file(
            terminal_path,
            label="retained materialization terminal",
            byte_cap=LAUNCH_MANIFEST_BYTE_CAP,
            required_mode=0o400,
            expected_size=len(terminal_raw),
            expected_sha256=hashlib.sha256(terminal_raw).hexdigest(),
        )
        if retained_terminal != terminal_raw:
            _fail("retained materialization terminal changed")
        return terminal
    except V180r12r2PrelaunchMaterializationReplayForbidden:
        raise
    except BaseException as error:
        _write_failure_if_absent(
            exact_freeze_fd=exact_freeze_fd,
            repository_root=repository_root,
            external_root_path=external_root_path,
            expected_external_root_sha256=expected_external_root_sha256,
            failed_phase=failed_phase,
            error=error,
        )
        raise
    finally:
        os.close(exact_freeze_fd)


def main() -> None:
    if len(sys.argv) != 3:
        _fail("materializer API is exact repository root and EXTERNAL_ROOT path")
    repository_root = Path(sys.argv[1])
    external_root_path = Path(sys.argv[2])
    expected_digest = _require_sha256(
        os.environ.get(EXTERNAL_ROOT_SHA256_ENV),
        "external root environment digest",
    )
    terminal = materialize_prelaunch_v180r12r2(
        repository_root,
        external_root_path,
        expected_digest,
        enforce_process_boundary=True,
    )
    print(
        json.dumps(
            {
                "materialization_terminal_id": terminal[
                    "materialization_terminal_id"
                ],
                "launch_manifest_sha256": terminal["launch_manifest"]["sha256"],
                "success": True,
            },
            sort_keys=True,
        ),
        flush=True,
    )


__all__ = (
    "BOOTSTRAP_RELATIVE_PATH",
    "EXTERNAL_ROOT_RELATIVE_PATH",
    "EXTERNAL_ROOT_SCHEMA",
    "EXTERNAL_ROOT_SHA256_ENV",
    "LAUNCH_MANIFEST_RELATIVE_PATH",
    "LAUNCH_MANIFEST_SCHEMA",
    "LAUNCHER_BYTE_CAP",
    "MATERIALIZER_RELATIVE_PATH",
    "MATERIALIZATION_FAILURE_RELATIVE_PATH",
    "MATERIALIZATION_FAILURE_SCHEMA",
    "MATERIALIZATION_RULE_DOCUMENT",
    "MATERIALIZATION_RULE_ID",
    "MATERIALIZATION_TERMINAL_RELATIVE_PATH",
    "MATERIALIZATION_TERMINAL_SCHEMA",
    "OUTPUT_ROOT_RELATIVE_PATH",
    "RETAINED_LAUNCHER_RELATIVE_PATH",
    "SOURCE_BOOTSTRAP_RELATIVE_PATH",
    "SOURCE_CLOSURE_RULE_DOCUMENT",
    "SOURCE_CLOSURE_RULE_ID",
    "SOURCE_LAUNCHER_RELATIVE_PATH",
    "V180r12r2PrelaunchMaterializationError",
    "V180r12r2PrelaunchMaterializationReplayForbidden",
    "build_c_pre_source_closure_v180r12r2",
    "build_launch_manifest_v180r12r2",
    "build_materialization_failure_v180r12r2",
    "build_materialization_terminal_v180r12r2",
    "build_third_party_source_closure_v180r12r2",
    "load_external_root_v180r12r2",
    "materialize_prelaunch_v180r12r2",
    "observe_materialization_progress_v180r12r2",
    "verify_git_boundary_v180r12r2",
)


if __name__ == "__main__":
    main()
