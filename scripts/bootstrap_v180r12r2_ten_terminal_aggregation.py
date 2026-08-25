#!/usr/bin/python3
"""Execute a V180r12r2 runner from an externally bound source snapshot.

The launch manifest and its digest are materialized outside this bootstrap after
the C_pre copy exists.  Mutation after that external snapshot is deliberately
outside this bootstrap's claim.  Before executing any ``acfqp`` code, the
bootstrap verifies and compiles the complete manifest-listed source closure and
the selected runner, then serves ``acfqp`` imports only from those in-memory
code objects.
"""

from __future__ import annotations

import hashlib
import importlib.abc
import importlib.util
import ast
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import sysconfig
import tokenize


_SCHEMA = "acfqp.v180r12r2_source_bound_launch_manifest.v1"
_MANIFEST_SHA_ENV = "ACFQP_V180R12R2_LAUNCH_MANIFEST_SHA256"
_PREREG_COMMIT_ENV = "ACFQP_V180R12R2_PREREG_COMMIT"
_EXPECTED_EXECUTABLE = "/usr/bin/python3"
_EXPECTED_GIT_EXECUTABLE = "/usr/bin/git"
_EXPECTED_PYCACHE_PREFIX = "/dev/null/v180r12r2"
_MANIFEST_SHA_TEMPLATE = "__V180R12R2_MANIFEST_SHA256__"
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_BOOTSTRAP_BYTE_CAP = 1024 * 1024
_MANIFEST_BYTE_CAP = 16 * 1024 * 1024
_RUNNER_BYTE_CAP = 4 * 1024 * 1024
_EXECUTABLE_BYTE_CAP = 64 * 1024 * 1024
_SOURCE_FILE_BYTE_CAP = 8 * 1024 * 1024
_SOURCE_CLOSURE_FILE_CAP = 4096
_SOURCE_CLOSURE_TOTAL_BYTE_CAP = 128 * 1024 * 1024
_EXPECTED_FLAGS = {
    "isolated": 1,
    "no_site": 1,
    "no_user_site": 1,
    "ignore_environment": 1,
    "dont_write_bytecode": 1,
}
_ORIG_ARGV_PREFIX = [
    _EXPECTED_EXECUTABLE,
    "-I",
    "-S",
    "-B",
    "-X",
    f"pycache_prefix={_EXPECTED_PYCACHE_PREFIX}",
]
_TARGET_RUNNER_PATHS = {
    "production": "scripts/run_v180r12r2_ten_terminal_aggregation.py",
    "verification": "scripts/verify_v180r12r2_ten_terminal_aggregation.py",
}
_AUTHORIZATION_SELF_MODULE = (
    "acfqp."
    "construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2"
)
_AUTHORIZATION_EVIDENCE_MODULE = (
    "acfqp.construction_k7_ten_terminal_aggregation_execution_"
    "authorization_evidence_freeze_v180r12r2"
)
_AUTHORIZATION_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_ten_terminal_aggregation_execution_"
    "authorization_evidence_freeze_v180r12r2.py"
)
_WRAPPER_REDACTED_CONSTANT_NAMES = (
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
_WRAPPER_REDACTED_STRING_LITERAL = b'"__ACFQP_V180R12R2_POST_PREREG_REDACTED__"'
_WRAPPER_REDACTED_INTEGER_LITERAL = b"0"
_CLOSURE_KIND = (
    "EXACT_RAW_AUTHORIZATION_SOURCE_CLOSURE_PLUS_AUTH_SELF_AND_BOUND_RUNNERS"
)
_TOP_LEVEL_KEYS = {
    "schema",
    "repository_root",
    "c_pre_root",
    "manifest_relative_path",
    "c_pre_commit_id",
    "bootstrap",
    "runtime",
    "git",
    "authorization_source_closure_kind",
    "authorization_self_module",
    "authorization_raw_source_modules",
    "authorization_source_closure",
    "source_modules",
    "third_party_source_closure",
    "targets",
    "working_tree_mutation_after_snapshot_in_scope",
}
_RAW_FACT_KEYS = {"relative_path", "byte_count", "sha256"}
_NORMALIZED_WRAPPER_FACT_KEYS = _RAW_FACT_KEYS | {
    "binding_kind",
    "redacted_constant_names",
}
_MODULE_FACT_KEYS = _RAW_FACT_KEYS | {"module", "is_package"}
_THIRD_PARTY_MODULE_FACT_KEYS = _MODULE_FACT_KEYS | {"source_root"}
_CLOSURE_KEYS = {
    "facts",
    "file_count",
    "total_byte_count",
    "facts_sha256",
}
_RUNTIME_KEYS = {
    "requested_executable",
    "resolved_executable",
    "executable_byte_count",
    "executable_sha256",
    "version",
    "version_info",
    "soabi",
    "base_sys_path",
    "orig_argv_prefix",
    "pycache_prefix",
    "flags",
}
_GIT_KEYS = {
    "requested_executable",
    "resolved_executable",
    "executable_mode",
    "executable_byte_count",
    "executable_sha256",
    "version_argv",
    "version_environment",
    "version_stdout",
    "runner_process_count",
    "runner_argv",
    "runner_environment_template",
}
_GIT_VERSION_ARGV = [_EXPECTED_GIT_EXECUTABLE, "--version"]
_GIT_VERSION_ENVIRONMENT = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "LC_ALL": "C",
}
_GIT_SUBCOMMANDS = ("rev-parse", "log", "diff-tree", "log", "archive", "cat-file")


def _require_exact_dict(value: object, keys: set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise RuntimeError(f"V180r12r2 {label} schema is not exact")
    return value


def _require_str(value: object, label: str) -> str:
    if type(value) is not str or not value:
        raise RuntimeError(f"V180r12r2 {label} is not a nonempty string")
    return value


def _require_sha256(value: object, label: str) -> str:
    text = _require_str(value, label)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise RuntimeError(f"V180r12r2 {label} is not lowercase SHA-256")
    return text


def _require_nonnegative_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise RuntimeError(f"V180r12r2 {label} is not a nonnegative integer")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _validated_root(text: str, label: str) -> Path:
    root = Path(text)
    if not root.is_absolute() or str(root) != text:
        raise RuntimeError(f"V180r12r2 {label} must be an exact absolute path")
    try:
        metadata = os.lstat(root)
        resolved = root.resolve(strict=True)
    except OSError as error:
        raise RuntimeError(f"V180r12r2 {label} is unavailable") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError(f"V180r12r2 {label} must be a nonsymlink directory")
    if resolved != root:
        raise RuntimeError(f"V180r12r2 {label} has a symlinked path component")
    return root


def _validated_relative_path(text: object, label: str) -> str:
    relative = _require_str(text, label)
    pure = PurePosixPath(relative)
    if (
        pure.is_absolute()
        or str(pure) != relative
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        raise RuntimeError(f"V180r12r2 {label} is not a normalized relative path")
    return relative


def _stable_read(
    root: Path,
    relative: str,
    label: str,
    *,
    byte_cap: int,
    registered_size: int | None = None,
    expected_sha256: str | None = None,
) -> bytes:
    """Read one regular file beneath ``root`` without following symlinks."""

    if type(byte_cap) is not int or byte_cap <= 0:
        raise RuntimeError(f"V180r12r2 {label} byte cap is invalid")
    if registered_size is not None and (
        type(registered_size) is not int
        or registered_size < 0
        or registered_size > byte_cap
    ):
        raise RuntimeError(f"V180r12r2 {label} registered size exceeds its cap")
    if expected_sha256 is not None:
        expected_sha256 = _require_sha256(expected_sha256, f"{label} stream digest")
    relative = _validated_relative_path(relative, f"{label} relative path")
    parts = PurePosixPath(relative).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(root, directory_flags)
    try:
        for part in parts[:-1]:
            child = os.open(part, directory_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(parts[-1], file_flags, dir_fd=descriptor)
    except OSError as error:
        raise RuntimeError(f"V180r12r2 {label} is unavailable or symlinked") from error
    finally:
        os.close(descriptor)

    try:
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError(
                f"V180r12r2 {label} must be a singly linked regular file"
            )
        if before.st_size > byte_cap or (
            registered_size is not None and before.st_size != registered_size
        ):
            raise RuntimeError(
                f"V180r12r2 {label} size disagrees with its registered bound"
            )
        chunks: list[bytes] = []
        byte_count = 0
        digest = hashlib.sha256()
        while True:
            remaining = before.st_size - byte_count
            chunk = os.read(file_descriptor, min(1024 * 1024, remaining + 1))
            if not chunk:
                break
            byte_count += len(chunk)
            if byte_count > before.st_size or byte_count > byte_cap:
                raise RuntimeError(f"V180r12r2 {label} exceeded its read bound")
            digest.update(chunk)
            chunks.append(chunk)
        after = os.fstat(file_descriptor)
    finally:
        os.close(file_descriptor)

    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise RuntimeError(f"V180r12r2 {label} changed during stable read")
    raw = b"".join(chunks)
    if len(raw) != before.st_size:
        raise RuntimeError(f"V180r12r2 {label} byte count changed during stable read")
    if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
        raise RuntimeError(f"V180r12r2 {label} stream digest mismatch")
    return raw


def _relative_to_root(path_text: str, root: Path, label: str) -> str:
    path = Path(path_text)
    if not path.is_absolute() or str(path) != path_text:
        raise RuntimeError(f"V180r12r2 {label} must be an exact absolute path")
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"V180r12r2 {label} is outside its bound root") from error
    return _validated_relative_path(relative.as_posix(), f"{label} relative path")


def _verify_raw_fact(
    root: Path,
    fact: object,
    label: str,
    *,
    expected_relative_path: str | None = None,
    byte_cap: int,
) -> tuple[bytes, str]:
    fact = _require_exact_dict(fact, _RAW_FACT_KEYS, label)
    relative = _validated_relative_path(fact["relative_path"], f"{label} path")
    if expected_relative_path is not None and relative != expected_relative_path:
        raise RuntimeError(f"V180r12r2 {label} path changed")
    byte_count = _require_nonnegative_int(fact["byte_count"], f"{label} byte count")
    digest = _require_sha256(fact["sha256"], f"{label} digest")
    raw = _stable_read(
        root,
        relative,
        label,
        byte_cap=byte_cap,
        registered_size=byte_count,
        expected_sha256=digest,
    )
    if len(raw) != byte_count:
        raise RuntimeError(f"V180r12r2 {label} raw fact mismatch")
    return raw, relative


def _require_sanitized_environment() -> str:
    allowed = {_MANIFEST_SHA_ENV, "LC_CTYPE"}
    if set(os.environ) != allowed or os.environ.get("LC_CTYPE") != "C.UTF-8":
        raise RuntimeError("V180r12r2 bootstrap environment is not sanitized")
    return _require_sha256(
        os.environ.get(_MANIFEST_SHA_ENV), "launch manifest environment digest"
    )


def _normalize_authorization_evidence_wrapper(raw: bytes) -> bytes:
    """Redact exactly the eight authorization wrapper literals by AST span."""

    try:
        tree = ast.parse(raw, filename=_AUTHORIZATION_EVIDENCE_RELATIVE_PATH)
    except (SyntaxError, ValueError) as error:
        raise RuntimeError("V180r12r2 wrapper AST is malformed") from error
    line_offsets = [0]
    for line in raw.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(line))
    wanted = set(_WRAPPER_REDACTED_CONSTANT_NAMES)
    assignments: dict[str, tuple[int, int, bytes]] = {}
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
        if name in assignments or value is None or not isinstance(value, ast.Constant):
            raise RuntimeError("V180r12r2 wrapper literal assignment changed")
        literal = value.value
        if name in _WRAPPER_STRING_CONSTANT_NAMES:
            if type(literal) is not str:
                raise RuntimeError("V180r12r2 wrapper string literal changed")
            replacement = _WRAPPER_REDACTED_STRING_LITERAL
            expected_token = tokenize.STRING
        elif name in _WRAPPER_INTEGER_CONSTANT_NAMES:
            if type(literal) is not int:
                raise RuntimeError("V180r12r2 wrapper integer literal changed")
            replacement = _WRAPPER_REDACTED_INTEGER_LITERAL
            expected_token = tokenize.NUMBER
        else:  # pragma: no cover - the two sets exactly partition the tuple.
            raise AssertionError
        positions = (
            value.lineno,
            value.col_offset,
            value.end_lineno,
            value.end_col_offset,
        )
        if not all(type(item) is int for item in positions):
            raise RuntimeError("V180r12r2 wrapper literal source span changed")
        start = line_offsets[value.lineno - 1] + value.col_offset
        end = line_offsets[value.end_lineno - 1] + value.end_col_offset
        if not (0 <= start < end <= len(raw)):
            raise RuntimeError("V180r12r2 wrapper literal source span is invalid")
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
            raise RuntimeError("V180r12r2 wrapper literal tokenization failed") from error
        if len(tokens) != 1 or tokens[0].type != expected_token:
            raise RuntimeError("V180r12r2 wrapper anchor is not one literal token")
        assignments[name] = (start, end, replacement)
    if set(assignments) != wanted or len(assignments) != 8:
        raise RuntimeError("V180r12r2 wrapper eight-literal allowlist is incomplete")
    result = raw
    previous_start = len(raw)
    for start, end, replacement in sorted(
        assignments.values(), key=lambda item: item[0], reverse=True
    ):
        if end > previous_start:
            raise RuntimeError("V180r12r2 wrapper literal spans overlap")
        result = result[:start] + replacement + result[end:]
        previous_start = start
    return result


def _validated_raw_closure(value: object, label: str) -> list[dict]:
    closure = _require_exact_dict(value, _CLOSURE_KEYS, label)
    facts = closure["facts"]
    if type(facts) is not list or not facts:
        raise RuntimeError(f"V180r12r2 {label} facts are not a nonempty list")
    if len(facts) > _SOURCE_CLOSURE_FILE_CAP:
        raise RuntimeError(f"V180r12r2 {label} exceeds its file cap")
    checked: list[dict] = []
    for index, value in enumerate(facts):
        if type(value) is not dict:
            raise RuntimeError(f"V180r12r2 {label} fact {index} schema is not exact")
        relative_value = value.get("relative_path")
        expected_keys = (
            _NORMALIZED_WRAPPER_FACT_KEYS
            if relative_value == _AUTHORIZATION_EVIDENCE_RELATIVE_PATH
            else _RAW_FACT_KEYS
        )
        fact = _require_exact_dict(value, expected_keys, f"{label} fact {index}")
        relative = _validated_relative_path(
            fact["relative_path"], f"{label} fact {index} path"
        )
        size = _require_nonnegative_int(
            fact["byte_count"], f"{label} fact {index} byte count"
        )
        if size > _SOURCE_FILE_BYTE_CAP:
            raise RuntimeError(f"V180r12r2 {label} fact {index} exceeds its file cap")
        checked_fact = {
            "relative_path": relative,
            "byte_count": size,
            "sha256": _require_sha256(
                fact["sha256"], f"{label} fact {index} digest"
            ),
        }
        if relative == _AUTHORIZATION_EVIDENCE_RELATIVE_PATH:
            if (
                fact["binding_kind"]
                != "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"
                or fact["redacted_constant_names"]
                != list(_WRAPPER_REDACTED_CONSTANT_NAMES)
            ):
                raise RuntimeError("V180r12r2 normalized wrapper fact changed")
            checked_fact.update(
                {
                    "binding_kind": fact["binding_kind"],
                    "redacted_constant_names": fact["redacted_constant_names"],
                }
            )
        checked.append(checked_fact)
    if [fact["relative_path"] for fact in checked] != sorted(
        {fact["relative_path"] for fact in checked}
    ):
        raise RuntimeError(f"V180r12r2 {label} facts are unsorted or duplicated")
    total = sum(fact["byte_count"] for fact in checked)
    if total > _SOURCE_CLOSURE_TOTAL_BYTE_CAP:
        raise RuntimeError(f"V180r12r2 {label} exceeds its aggregate byte cap")
    registered_count = _require_nonnegative_int(
        closure["file_count"], f"{label} file count"
    )
    registered_total = _require_nonnegative_int(
        closure["total_byte_count"], f"{label} total byte count"
    )
    registered_digest = _require_sha256(
        closure["facts_sha256"], f"{label} facts digest"
    )
    if not (
        registered_count == len(checked)
        and registered_total == total
        and registered_digest
        == hashlib.sha256(_canonical_json_bytes(checked)).hexdigest()
    ):
        raise RuntimeError(f"V180r12r2 {label} aggregate registration changed")
    return checked


def _validated_third_party_closure(value: object) -> list[dict]:
    label = "third-party source closure"
    closure = _require_exact_dict(value, _CLOSURE_KEYS, label)
    facts = closure["facts"]
    if type(facts) is not list or not facts:
        raise RuntimeError(f"V180r12r2 {label} facts are not a nonempty list")
    if len(facts) > _SOURCE_CLOSURE_FILE_CAP:
        raise RuntimeError(f"V180r12r2 {label} exceeds its file cap")
    checked: list[dict] = []
    for index, value in enumerate(facts):
        fact = _require_exact_dict(
            value, _THIRD_PARTY_MODULE_FACT_KEYS, f"{label} fact {index}"
        )
        module = _require_str(fact["module"], f"{label} fact {index} module")
        source_root = _require_str(
            fact["source_root"], f"{label} fact {index} source root"
        )
        relative = _validated_relative_path(
            fact["relative_path"], f"{label} fact {index} path"
        )
        size = _require_nonnegative_int(
            fact["byte_count"], f"{label} fact {index} byte count"
        )
        if size > _SOURCE_FILE_BYTE_CAP or type(fact["is_package"]) is not bool:
            raise RuntimeError(f"V180r12r2 {label} fact {index} exceeds its bound")
        checked.append(
            {
                "module": module,
                "is_package": fact["is_package"],
                "source_root": source_root,
                "relative_path": relative,
                "byte_count": size,
                "sha256": _require_sha256(
                    fact["sha256"], f"{label} fact {index} digest"
                ),
            }
        )
    if [fact["module"] for fact in checked] != sorted(
        {fact["module"] for fact in checked}
    ):
        raise RuntimeError(f"V180r12r2 {label} facts are unsorted or duplicated")
    total = sum(fact["byte_count"] for fact in checked)
    if total > _SOURCE_CLOSURE_TOTAL_BYTE_CAP:
        raise RuntimeError(f"V180r12r2 {label} exceeds its aggregate byte cap")
    registered_count = _require_nonnegative_int(
        closure["file_count"], f"{label} file count"
    )
    registered_total = _require_nonnegative_int(
        closure["total_byte_count"], f"{label} total byte count"
    )
    registered_digest = _require_sha256(
        closure["facts_sha256"], f"{label} facts digest"
    )
    if not (
        registered_count == len(checked)
        and registered_total == total
        and registered_digest
        == hashlib.sha256(_canonical_json_bytes(checked)).hexdigest()
    ):
        raise RuntimeError(f"V180r12r2 {label} aggregate registration changed")
    return checked


def _require_runtime_boundary(
    runtime_value: object,
    bootstrap_path: Path,
    target: str,
    repository_root: Path,
    c_pre_root: Path,
    manifest_path: Path,
) -> None:
    runtime = _require_exact_dict(runtime_value, _RUNTIME_KEYS, "runtime")
    if runtime["requested_executable"] != _EXPECTED_EXECUTABLE:
        raise RuntimeError("V180r12r2 requested interpreter changed")
    if sys.executable != _EXPECTED_EXECUTABLE:
        raise RuntimeError("V180r12r2 bootstrap requires /usr/bin/python3")
    if sys.pycache_prefix != _EXPECTED_PYCACHE_PREFIX or sys.dont_write_bytecode is not True:
        raise RuntimeError("V180r12r2 pycache boundary changed")
    actual_flags = {
        name: getattr(sys.flags, name) for name in _EXPECTED_FLAGS
    }
    manifest_flags = _require_exact_dict(
        runtime["flags"], set(_EXPECTED_FLAGS), "runtime flags"
    )
    if actual_flags != _EXPECTED_FLAGS or manifest_flags != _EXPECTED_FLAGS:
        raise RuntimeError("V180r12r2 runtime flags changed")
    if runtime["pycache_prefix"] != _EXPECTED_PYCACHE_PREFIX:
        raise RuntimeError("V180r12r2 runtime pycache prefix changed")

    expected_argv = [
        *_ORIG_ARGV_PREFIX,
        str(bootstrap_path),
        target,
        str(repository_root),
        str(c_pre_root),
        str(manifest_path),
    ]
    if runtime["orig_argv_prefix"] != _ORIG_ARGV_PREFIX or sys.orig_argv != expected_argv:
        raise RuntimeError("V180r12r2 exact original argv changed")
    if sys.argv != expected_argv[len(_ORIG_ARGV_PREFIX) :]:
        raise RuntimeError("V180r12r2 exact argv changed")

    base_sys_path = runtime["base_sys_path"]
    if (
        type(base_sys_path) is not list
        or not all(type(item) is str for item in base_sys_path)
        or sys.path != base_sys_path
    ):
        raise RuntimeError("V180r12r2 initial sys.path changed")
    if runtime["version"] != sys.version:
        raise RuntimeError("V180r12r2 interpreter version changed")
    version_info = runtime["version_info"]
    if type(version_info) is not list or version_info != list(sys.version_info):
        raise RuntimeError("V180r12r2 interpreter version info changed")
    if runtime["soabi"] != sysconfig.get_config_var("SOABI"):
        raise RuntimeError("V180r12r2 interpreter SOABI changed")

    resolved_text = _require_str(
        runtime["resolved_executable"], "resolved interpreter path"
    )
    resolved = Path(resolved_text)
    if not resolved.is_absolute() or str(resolved) != resolved_text:
        raise RuntimeError("V180r12r2 resolved interpreter path is not exact")
    try:
        actual_resolved = Path(sys.executable).resolve(strict=True)
    except OSError as error:
        raise RuntimeError("V180r12r2 interpreter cannot be resolved") from error
    if actual_resolved != resolved:
        raise RuntimeError("V180r12r2 resolved interpreter changed")
    interpreter_root = _validated_root("/", "interpreter filesystem root")
    interpreter_relative = _relative_to_root(
        str(resolved), interpreter_root, "resolved interpreter"
    )
    interpreter_raw = _stable_read(
        interpreter_root,
        interpreter_relative,
        "resolved interpreter",
        byte_cap=_EXECUTABLE_BYTE_CAP,
        registered_size=_require_nonnegative_int(
            runtime["executable_byte_count"], "interpreter byte count"
        ),
        expected_sha256=_require_sha256(
            runtime["executable_sha256"], "interpreter digest"
        ),
    )
    if (
        len(interpreter_raw)
        != runtime["executable_byte_count"]
    ):
        raise RuntimeError("V180r12r2 interpreter raw fact mismatch")

    dev_null = os.lstat("/dev/null")
    if (
        not stat.S_ISCHR(dev_null.st_mode)
        or os.major(dev_null.st_rdev) != 1
        or os.minor(dev_null.st_rdev) != 3
    ):
        raise RuntimeError("V180r12r2 /dev/null is not character device 1:3")


class _GitProcessAudit:
    def __init__(
        self,
        expected_argv: list[list[str]],
        expected_environment: dict[str, str],
    ) -> None:
        self._expected_argv = expected_argv
        self._expected_environment = expected_environment
        self._observed_count = 0

    def __call__(self, event: str, arguments: tuple[object, ...]) -> None:
        if event != "subprocess.Popen":
            return
        if self._observed_count >= len(self._expected_argv):
            raise RuntimeError("V180r12r2 foreign subprocess launch rejected")
        executable, argv, cwd, environment = arguments
        expected = self._expected_argv[self._observed_count]
        if not (
            executable == _EXPECTED_GIT_EXECUTABLE
            and argv == expected
            and cwd is None
            and environment == self._expected_environment
        ):
            raise RuntimeError(
                f"V180r12r2 Git process {self._observed_count} contract changed"
            )
        self._observed_count += 1

    def require_complete(self) -> None:
        if self._observed_count != len(self._expected_argv):
            raise RuntimeError("V180r12r2 six-process Git contract was incomplete")


def _validated_git_boundary(
    value: object,
    repository_root: Path,
    manifest_digest: str,
    commit_id: str,
) -> _GitProcessAudit:
    git = _require_exact_dict(value, _GIT_KEYS, "Git runtime")
    if git["requested_executable"] != _EXPECTED_GIT_EXECUTABLE:
        raise RuntimeError("V180r12r2 requested Git executable changed")
    resolved_text = _require_str(git["resolved_executable"], "resolved Git path")
    resolved = Path(resolved_text)
    try:
        actual_resolved = Path(_EXPECTED_GIT_EXECUTABLE).resolve(strict=True)
    except OSError as error:
        raise RuntimeError("V180r12r2 Git executable cannot be resolved") from error
    if not resolved.is_absolute() or str(resolved) != resolved_text or resolved != actual_resolved:
        raise RuntimeError("V180r12r2 resolved Git executable changed")
    size = _require_nonnegative_int(git["executable_byte_count"], "Git byte count")
    mode = _require_nonnegative_int(git["executable_mode"], "Git executable mode")
    filesystem_root = _validated_root("/", "Git filesystem root")
    relative = _relative_to_root(resolved_text, filesystem_root, "resolved Git executable")
    raw = _stable_read(
        filesystem_root,
        relative,
        "resolved Git executable",
        byte_cap=_EXECUTABLE_BYTE_CAP,
        registered_size=size,
        expected_sha256=_require_sha256(
            git["executable_sha256"], "Git executable digest"
        ),
    )
    metadata = os.lstat(resolved)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_mode != mode
    ):
        raise RuntimeError("V180r12r2 Git executable raw fact mismatch")

    if git["version_argv"] != _GIT_VERSION_ARGV:
        raise RuntimeError("V180r12r2 Git version argv changed")
    version_environment = _require_exact_dict(
        git["version_environment"], set(_GIT_VERSION_ENVIRONMENT), "Git version environment"
    )
    if version_environment != _GIT_VERSION_ENVIRONMENT:
        raise RuntimeError("V180r12r2 Git version environment changed")
    version_stdout = _require_str(git["version_stdout"], "Git version stdout")
    if len(version_stdout.encode("utf-8")) > 1024 or not version_stdout.endswith("\n"):
        raise RuntimeError("V180r12r2 Git version stdout exceeds its bound")
    try:
        completed = subprocess.run(
            _GIT_VERSION_ARGV,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            env=_GIT_VERSION_ENVIRONMENT,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError("V180r12r2 Git version verification failed") from error
    if not (
        completed.returncode == 0
        and completed.stderr == b""
        and completed.stdout == version_stdout.encode("utf-8")
    ):
        raise RuntimeError("V180r12r2 Git version identity changed")

    count = _require_nonnegative_int(git["runner_process_count"], "Git process count")
    argv_values = git["runner_argv"]
    if type(argv_values) is not list or count != 6 or len(argv_values) != count:
        raise RuntimeError("V180r12r2 Git process count changed")
    checked_argv: list[list[str]] = []
    for index, value in enumerate(argv_values):
        if (
            type(value) is not list
            or not all(type(item) is str and item and "\x00" not in item for item in value)
            or value[:3]
            != [_EXPECTED_GIT_EXECUTABLE, "-C", str(repository_root)]
            or len(value) < 4
            or value[3] != _GIT_SUBCOMMANDS[index]
        ):
            raise RuntimeError(f"V180r12r2 Git process {index} argv changed")
        checked_argv.append(value)

    environment_template = _require_exact_dict(
        git["runner_environment_template"],
        {
            _MANIFEST_SHA_ENV,
            _PREREG_COMMIT_ENV,
            "LC_CTYPE",
            "GIT_CONFIG_GLOBAL",
            "GIT_CONFIG_NOSYSTEM",
            "GIT_NO_REPLACE_OBJECTS",
            "GIT_OPTIONAL_LOCKS",
            "LC_ALL",
        },
        "Git runner environment template",
    )
    expected_template = {
        _MANIFEST_SHA_ENV: _MANIFEST_SHA_TEMPLATE,
        _PREREG_COMMIT_ENV: commit_id,
        "LC_CTYPE": "C.UTF-8",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
    }
    if environment_template != expected_template:
        raise RuntimeError("V180r12r2 Git runner environment template changed")
    expected_environment = dict(expected_template)
    expected_environment[_MANIFEST_SHA_ENV] = manifest_digest
    return _GitProcessAudit(checked_argv, expected_environment)


class _BoundSourceLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, records: dict[str, tuple[object, str, bool]]) -> None:
        self._records = records

    def find_spec(self, fullname: str, path=None, target=None):
        del path, target
        namespace = fullname.split(".", 1)[0]
        if namespace not in {"acfqp", "packaging", "tomli"}:
            return None
        if fullname not in self._records:
            raise ImportError(
                f"V180r12r2 unlisted bound module origin rejected: {fullname}"
            )
        _, source_path, is_package = self._records[fullname]
        return importlib.util.spec_from_loader(
            fullname,
            self,
            origin=source_path,
            is_package=is_package,
        )

    def create_module(self, spec):
        del spec
        return None

    def exec_module(self, module) -> None:
        code, source_path, is_package = self._records[module.__name__]
        module.__file__ = source_path
        module.__cached__ = None
        if is_package:
            module.__path__ = [str(Path(source_path).parent)]
        exec(code, module.__dict__)


def _validated_manifest(
    manifest: object,
    repository_root: Path,
    c_pre_root: Path,
    manifest_relative: str,
) -> dict:
    manifest = _require_exact_dict(manifest, _TOP_LEVEL_KEYS, "launch manifest")
    if manifest["schema"] != _SCHEMA:
        raise RuntimeError("V180r12r2 launch manifest schema changed")
    if manifest["repository_root"] != str(repository_root):
        raise RuntimeError("V180r12r2 manifest repository root changed")
    if manifest["c_pre_root"] != str(c_pre_root):
        raise RuntimeError("V180r12r2 manifest C_pre root changed")
    if manifest["manifest_relative_path"] != manifest_relative:
        raise RuntimeError("V180r12r2 manifest relative path changed")
    commit_id = manifest["c_pre_commit_id"]
    if type(commit_id) is not str or _COMMIT_PATTERN.fullmatch(commit_id) is None:
        raise RuntimeError("V180r12r2 C_pre commit ID changed")
    if manifest["authorization_source_closure_kind"] != _CLOSURE_KIND:
        raise RuntimeError("V180r12r2 authorization closure kind changed")
    if manifest["authorization_self_module"] != _AUTHORIZATION_SELF_MODULE:
        raise RuntimeError("V180r12r2 authorization self module changed")
    if manifest["working_tree_mutation_after_snapshot_in_scope"] is not False:
        raise RuntimeError("V180r12r2 post-snapshot mutation claim changed")
    return manifest


def _validate_manifest_resource_contract(manifest: dict) -> tuple[list[dict], dict]:
    bootstrap = _require_exact_dict(
        manifest["bootstrap"], _RAW_FACT_KEYS, "bootstrap raw fact"
    )
    bootstrap_size = _require_nonnegative_int(
        bootstrap["byte_count"], "bootstrap byte count"
    )
    if bootstrap_size > _BOOTSTRAP_BYTE_CAP:
        raise RuntimeError("V180r12r2 bootstrap exceeds its independent byte cap")

    source_values = manifest["source_modules"]
    if type(source_values) is not list or not source_values:
        raise RuntimeError("V180r12r2 source module facts are not a nonempty list")
    if len(source_values) > _SOURCE_CLOSURE_FILE_CAP:
        raise RuntimeError("V180r12r2 source modules exceed their file cap")
    source_raw_by_path: dict[str, dict] = {}
    authorization_self_fact: dict | None = None
    evidence_wrapper_module_present = False
    for index, value in enumerate(source_values):
        fact = _require_exact_dict(value, _MODULE_FACT_KEYS, f"source module {index}")
        module = _require_str(fact["module"], f"source module {index} name")
        relative = _validated_relative_path(
            fact["relative_path"], f"source module {index} path"
        )
        size = _require_nonnegative_int(
            fact["byte_count"], f"source module {index} byte count"
        )
        if size > _SOURCE_FILE_BYTE_CAP or relative in source_raw_by_path:
            raise RuntimeError(f"V180r12r2 source module {index} exceeds its bound")
        raw_fact = {
            "relative_path": relative,
            "byte_count": size,
            "sha256": _require_sha256(
                fact["sha256"], f"source module {index} digest"
            ),
        }
        if module == _AUTHORIZATION_SELF_MODULE:
            authorization_self_fact = raw_fact
        else:
            source_raw_by_path[relative] = raw_fact
        if module == _AUTHORIZATION_EVIDENCE_MODULE:
            evidence_wrapper_module_present = True

    targets = _require_exact_dict(
        manifest["targets"], set(_TARGET_RUNNER_PATHS), "runner targets"
    )
    for name, expected_path in _TARGET_RUNNER_PATHS.items():
        fact = _require_exact_dict(targets[name], _RAW_FACT_KEYS, f"{name} runner")
        relative = _validated_relative_path(fact["relative_path"], f"{name} runner path")
        size = _require_nonnegative_int(fact["byte_count"], f"{name} runner byte count")
        if (
            relative != expected_path
            or size > _RUNNER_BYTE_CAP
            or relative in source_raw_by_path
        ):
            raise RuntimeError(f"V180r12r2 {name} runner exceeds its independent bound")
        source_raw_by_path[relative] = {
            "relative_path": relative,
            "byte_count": size,
            "sha256": _require_sha256(fact["sha256"], f"{name} runner digest"),
        }

    authorization_facts = _validated_raw_closure(
        manifest["authorization_source_closure"],
        "authorization source closure",
    )
    authorization_by_path = {
        fact["relative_path"]: fact for fact in authorization_facts
    }
    if set(authorization_by_path) != set(source_raw_by_path):
        raise RuntimeError("V180r12r2 authorization source closure facts are not exact")
    for path, raw_fact in source_raw_by_path.items():
        if path == _AUTHORIZATION_EVIDENCE_RELATIVE_PATH:
            continue
        if authorization_by_path[path] != raw_fact:
            raise RuntimeError(
                "V180r12r2 authorization source closure facts are not exact"
            )
    if authorization_self_fact is None:
        raise RuntimeError("V180r12r2 authorization self raw fact is absent")
    if not evidence_wrapper_module_present:
        raise RuntimeError("V180r12r2 authorization evidence wrapper is absent")

    third_party_facts = _validated_third_party_closure(
        manifest["third_party_source_closure"]
    )
    targets = manifest["targets"]
    total_file_count = len(source_values) + len(targets) + len(third_party_facts)
    total_byte_count = (
        sum(fact["byte_count"] for fact in source_values)
        + sum(fact["byte_count"] for fact in targets.values())
        + sum(fact["byte_count"] for fact in third_party_facts)
    )
    if (
        total_file_count > _SOURCE_CLOSURE_FILE_CAP
        or total_byte_count > _SOURCE_CLOSURE_TOTAL_BYTE_CAP
    ):
        raise RuntimeError("V180r12r2 combined source closure exceeds its cap")
    return third_party_facts, authorization_by_path[_AUTHORIZATION_EVIDENCE_RELATIVE_PATH]


def _compile_bound_sources(
    manifest: dict,
    repository_root: Path,
    normalized_wrapper_fact: dict,
) -> dict[str, tuple[object, str, bool]]:
    source_values = manifest["source_modules"]
    authorization_names = manifest["authorization_raw_source_modules"]
    if type(source_values) is not list or not source_values:
        raise RuntimeError("V180r12r2 source module facts are not a nonempty list")
    if (
        type(authorization_names) is not list
        or not all(type(name) is str for name in authorization_names)
        or authorization_names != sorted(set(authorization_names))
    ):
        raise RuntimeError("V180r12r2 authorization source module names changed")

    records: dict[str, tuple[object, str, bool]] = {}
    paths: set[str] = set()
    for index, value in enumerate(source_values):
        fact = _require_exact_dict(value, _MODULE_FACT_KEYS, f"source module {index}")
        module = _require_str(fact["module"], f"source module {index} name")
        is_package = fact["is_package"]
        if type(is_package) is not bool:
            raise RuntimeError(f"V180r12r2 source module {index} package flag changed")
        raw_fact = {key: fact[key] for key in _RAW_FACT_KEYS}
        raw, relative = _verify_raw_fact(
            repository_root,
            raw_fact,
            f"source module {module}",
            byte_cap=_SOURCE_FILE_BYTE_CAP,
        )
        if module == _AUTHORIZATION_EVIDENCE_MODULE:
            normalized = _normalize_authorization_evidence_wrapper(raw)
            if not (
                relative == _AUTHORIZATION_EVIDENCE_RELATIVE_PATH
                and len(normalized) == normalized_wrapper_fact["byte_count"]
                and hashlib.sha256(normalized).hexdigest()
                == normalized_wrapper_fact["sha256"]
            ):
                raise RuntimeError(
                    "V180r12r2 normalized authorization wrapper fact mismatch"
                )
        pure = PurePosixPath(relative)
        if (
            (module != "acfqp" and not module.startswith("acfqp."))
            or not relative.startswith("src/acfqp/")
            or pure.suffix != ".py"
            or is_package != (pure.name == "__init__.py")
            or module in records
            or relative in paths
        ):
            raise RuntimeError(f"V180r12r2 source module {module} binding changed")
        expected_parts = ["acfqp", *module.split(".")[1:]]
        expected_relative = PurePosixPath("src", *expected_parts)
        if is_package:
            expected_relative /= "__init__.py"
        else:
            expected_relative = expected_relative.with_suffix(".py")
        if relative != expected_relative.as_posix():
            raise RuntimeError(f"V180r12r2 source module {module} path changed")
        source_path = str(repository_root / relative)
        try:
            code = compile(raw, source_path, "exec", dont_inherit=True, optimize=0)
        except (SyntaxError, ValueError) as error:
            raise RuntimeError(
                f"V180r12r2 source module {module} cannot be compiled"
            ) from error
        records[module] = (code, source_path, is_package)
        paths.add(relative)

    names = sorted(records)
    expected_names = sorted([*authorization_names, _AUTHORIZATION_SELF_MODULE])
    if (
        names != expected_names
        or _AUTHORIZATION_SELF_MODULE in authorization_names
        or "acfqp" not in records
        or _AUTHORIZATION_SELF_MODULE not in records
    ):
        raise RuntimeError("V180r12r2 authorization source closure is not exact")
    return records


def _compile_third_party_sources(
    facts: list[dict],
) -> dict[str, tuple[object, str, bool]]:
    records: dict[str, tuple[object, str, bool]] = {}
    roots: dict[str, Path] = {}
    paths: set[tuple[str, str]] = set()
    for index, fact in enumerate(facts):
        module = fact["module"]
        namespace = module.split(".", 1)[0]
        if namespace not in {"packaging", "tomli"}:
            raise RuntimeError(
                f"V180r12r2 foreign third-party namespace rejected: {module}"
            )
        root_text = fact["source_root"]
        root = roots.setdefault(
            root_text,
            _validated_root(root_text, f"third-party source root {root_text}"),
        )
        relative = fact["relative_path"]
        pure = PurePosixPath(relative)
        is_package = fact["is_package"]
        expected = PurePosixPath(*module.split("."))
        if is_package:
            expected /= "__init__.py"
        else:
            expected = expected.with_suffix(".py")
        if (
            relative != expected.as_posix()
            or pure.suffix != ".py"
            or is_package != (pure.name == "__init__.py")
            or module in records
            or (root_text, relative) in paths
        ):
            raise RuntimeError(
                f"V180r12r2 third-party source module {module} binding changed"
            )
        raw_fact = {key: fact[key] for key in _RAW_FACT_KEYS}
        raw, _ = _verify_raw_fact(
            root,
            raw_fact,
            f"third-party source module {module}",
            byte_cap=_SOURCE_FILE_BYTE_CAP,
        )
        source_path = str(root / relative)
        try:
            code = compile(raw, source_path, "exec", dont_inherit=True, optimize=0)
        except (SyntaxError, ValueError) as error:
            raise RuntimeError(
                f"V180r12r2 third-party source module {module} cannot be compiled"
            ) from error
        records[module] = (code, source_path, is_package)
        paths.add((root_text, relative))
    if "packaging" not in records or "tomli" not in records:
        raise RuntimeError("V180r12r2 required third-party source roots are absent")
    return records


def _compile_runners(
    manifest: dict,
    repository_root: Path,
    target: str,
) -> tuple[object, str]:
    targets = _require_exact_dict(
        manifest["targets"], set(_TARGET_RUNNER_PATHS), "runner targets"
    )
    selected: tuple[object, str] | None = None
    for name, expected_path in _TARGET_RUNNER_PATHS.items():
        fact = _require_exact_dict(targets[name], _RAW_FACT_KEYS, f"{name} runner")
        if fact["relative_path"] != expected_path:
            raise RuntimeError(f"V180r12r2 {name} runner path changed")
        raw, relative = _verify_raw_fact(
            repository_root,
            fact,
            f"{name} runner",
            expected_relative_path=expected_path,
            byte_cap=_RUNNER_BYTE_CAP,
        )
        source_path = str(repository_root / relative)
        try:
            code = compile(raw, source_path, "exec", dont_inherit=True, optimize=0)
        except (SyntaxError, ValueError) as error:
            raise RuntimeError(f"V180r12r2 {name} runner cannot be compiled") from error
        if name == target:
            selected = (code, source_path)
    if selected is None:  # pragma: no cover - target checked by the public API.
        raise RuntimeError("V180r12r2 selected runner is absent")
    return selected


class _RunnerSecondaryObservation(RuntimeError):
    def __init__(self, observations: tuple[BaseException, ...]) -> None:
        if not observations:
            raise ValueError("secondary observations must be nonempty")
        self.observations = observations
        summary = "; ".join(
            f"{type(error).__name__}: {error}" for error in observations
        )
        super().__init__(f"V180r12r2 runner secondary observations: {summary}")


def _execute_precompiled_runner(
    code: object,
    source_path: str,
    records: dict[str, tuple[object, str, bool]],
    git_audit: _GitProcessAudit,
) -> None:
    namespaces = {"acfqp", "packaging", "tomli"}
    if any(name.split(".", 1)[0] in namespaces for name in sys.modules):
        raise RuntimeError("V180r12r2 bound source was imported before dispatch")
    loader = _BoundSourceLoader(records)
    original_meta_path = list(sys.meta_path)
    sys.meta_path.insert(0, loader)
    sys.addaudithook(git_audit)
    sys.argv = [source_path]
    globals_dict = {
        "__name__": "__main__",
        "__file__": source_path,
        "__package__": None,
        "__cached__": None,
        "__loader__": None,
        "__spec__": None,
    }
    primary_error: BaseException | None = None
    primary_traceback = None
    try:
        exec(code, globals_dict)
    except BaseException as error:
        primary_error = error
        primary_traceback = error.__traceback__

    secondary_errors: list[BaseException] = []

    def observe(check) -> None:
        try:
            check()
        except BaseException as error:
            secondary_errors.append(error)

    def check_meta_path() -> None:
        if sys.meta_path != [loader, *original_meta_path]:
            raise RuntimeError("V180r12r2 bound meta_path changed during dispatch")

    def check_loaded_modules() -> None:
        for name, module in tuple(sys.modules.items()):
            if name.split(".", 1)[0] not in namespaces:
                continue
            if name not in records or getattr(module, "__loader__", None) is not loader:
                raise RuntimeError(
                    f"V180r12r2 non-bound source module loaded: {name}"
                )
            _, expected_path, _ = records[name]
            if (
                getattr(module, "__file__", None) != expected_path
                or getattr(module, "__cached__", None) is not None
            ):
                raise RuntimeError(f"V180r12r2 bound source origin changed: {name}")

    observe(check_meta_path)
    observe(git_audit.require_complete)
    observe(check_loaded_modules)
    secondary = (
        _RunnerSecondaryObservation(tuple(secondary_errors))
        if secondary_errors
        else None
    )
    if primary_error is not None:
        if secondary is not None:
            raise primary_error.with_traceback(primary_traceback) from secondary
        raise primary_error.with_traceback(primary_traceback)
    if secondary is not None:
        raise secondary


def main() -> None:
    manifest_digest = _require_sanitized_environment()
    if len(sys.argv) != 5 or sys.argv[1] not in _TARGET_RUNNER_PATHS:
        raise RuntimeError(
            "V180r12r2 bootstrap API is target, repository root, C_pre root, manifest"
        )
    target, repository_text, c_pre_text, manifest_text = sys.argv[1:]
    repository_root = _validated_root(repository_text, "repository root")
    c_pre_root = _validated_root(c_pre_text, "C_pre root")
    manifest_relative = _relative_to_root(
        manifest_text, c_pre_root, "launch manifest"
    )
    manifest_path = c_pre_root / manifest_relative
    manifest_raw = _stable_read(
        c_pre_root,
        manifest_relative,
        "launch manifest",
        byte_cap=_MANIFEST_BYTE_CAP,
        expected_sha256=manifest_digest,
    )
    try:
        manifest_value = json.loads(manifest_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("V180r12r2 launch manifest is not canonical JSON") from error
    if _canonical_json_bytes(manifest_value) != manifest_raw:
        raise RuntimeError("V180r12r2 launch manifest bytes are not canonical")
    manifest = _validated_manifest(
        manifest_value, repository_root, c_pre_root, manifest_relative
    )
    third_party_facts, normalized_wrapper_fact = (
        _validate_manifest_resource_contract(manifest)
    )

    bootstrap_fact = _require_exact_dict(
        manifest["bootstrap"], _RAW_FACT_KEYS, "bootstrap raw fact"
    )
    bootstrap_relative = _validated_relative_path(
        bootstrap_fact["relative_path"], "bootstrap path"
    )
    bootstrap_path = c_pre_root / bootstrap_relative
    if Path(__file__).absolute() != bootstrap_path or sys.argv[0] != str(bootstrap_path):
        raise RuntimeError("V180r12r2 executing bootstrap path changed")
    _verify_raw_fact(
        c_pre_root,
        bootstrap_fact,
        "executing bootstrap",
        expected_relative_path=bootstrap_relative,
        byte_cap=_BOOTSTRAP_BYTE_CAP,
    )
    _require_runtime_boundary(
        manifest["runtime"],
        bootstrap_path,
        target,
        repository_root,
        c_pre_root,
        manifest_path,
    )
    commit_id = manifest["c_pre_commit_id"]
    git_audit = _validated_git_boundary(
        manifest["git"], repository_root, manifest_digest, commit_id
    )

    records = _compile_bound_sources(
        manifest, repository_root, normalized_wrapper_fact
    )
    third_party_records = _compile_third_party_sources(third_party_facts)
    if set(records) & set(third_party_records):
        raise RuntimeError("V180r12r2 source namespace collision")
    records.update(third_party_records)
    runner_code, runner_path = _compile_runners(
        manifest, repository_root, target
    )
    os.environ[_PREREG_COMMIT_ENV] = commit_id
    if set(os.environ) != {_MANIFEST_SHA_ENV, _PREREG_COMMIT_ENV, "LC_CTYPE"}:
        raise RuntimeError("V180r12r2 runner environment injection changed")
    _execute_precompiled_runner(runner_code, runner_path, records, git_audit)


if __name__ == "__main__":
    main()
