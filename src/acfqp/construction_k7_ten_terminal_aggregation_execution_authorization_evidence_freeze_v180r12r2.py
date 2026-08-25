"""Cycle-safe post-prereg evidence for the V180r12r2 authorization.

The authorization binds a canonicalized copy of this wrapper.  Canonicalization
redacts only the eight module-level literal values that cannot be known until
after the outcome-free authorization is frozen.  Every other wrapper byte is
therefore preregistered.  This wrapper independently repeats that normalization,
checks the authorization-bound normalized fact, and uses its frozen literals to
lock the exact authorization identity, canonical bytes, and authorization source
fact.  No V180r12r2 outcome is read while constructing this evidence.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import io
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import subprocess
import tarfile
import tokenize
from typing import Any, NoReturn

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_domain_registry_extension_v180r12r2 as domains
from acfqp import (
    construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2
    as authorization,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_protocol_v180r12r2 as protocol,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


# These eight literal values are the complete post-prereg redaction allowlist.
# Keep each value as one module-level literal: the authorization normalizer
# rejects expressions, aliases, duplicate assignments, and missing constants.
EXPECTED_AUTHORIZATION_EVIDENCE_ID = "0000000000000000000000000000000000000000000000000000000000000000"
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0000000000000000000000000000000000000000000000000000000000000000"
EXPECTED_AUTHORIZATION_ID = "0000000000000000000000000000000000000000000000000000000000000000"
EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT = 0
EXPECTED_AUTHORIZATION_CANONICAL_SHA256 = "0000000000000000000000000000000000000000000000000000000000000000"
EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT = 0
EXPECTED_AUTHORIZATION_SOURCE_SHA256 = "0000000000000000000000000000000000000000000000000000000000000000"

# These predecessor identities are known before the authorization and are not
# redacted.  Any change therefore changes the normalized wrapper source fact.
EXPECTED_PROTOCOL_ID = "d15ec6d29ffbb4908e20cabfbbc98f3aa53ec4ad38d1d4681930c3306737c965"
EXPECTED_AGGREGATION_EXECUTION_SLOT_ID = "98d5ba0a9b04cd444a2d5c159cd719f8e7803934f7cbb8ee9b0ce8947a41e46e"

POST_PREREG_REDACTED_CONSTANTS = (
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
)
_STRING_REDACTED_CONSTANTS = frozenset(
    {
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
        "EXPECTED_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_ID",
        "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
    }
)
_INTEGER_REDACTED_CONSTANTS = frozenset(
    {
        "EXPECTED_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    }
)
_REDACTED_STRING_LITERAL = b'"__ACFQP_V180R12R2_POST_PREREG_REDACTED__"'
_REDACTED_INTEGER_LITERAL = b"0"
_COMMIT_ID = re.compile(r"^[0-9a-f]{40}$")
GIT_EXECUTABLE = "/usr/bin/git"
SOURCE_BOUNDARY_GIT_PROCESS_COUNT = 6
SOURCE_BOUNDARY_COMMAND_TIMEOUT_SECONDS = 120

_ROOT = Path(__file__).resolve().parents[2]
_AUTHORIZATION_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2.py"
)
_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_ten_terminal_aggregation_execution_"
    "authorization_evidence_freeze_v180r12r2.py"
)
SOURCE_FACT_EXCLUSIONS = (_AUTHORIZATION_RELATIVE_PATH,)
EXECUTION_CHAIN_RELATIVE_PATHS = tuple(
    sorted(
        (
            "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py",
            "scripts/launch_v180r12r2_ten_terminal_aggregation_prelaunch.py",
            "scripts/materialize_v180r12r2_ten_terminal_aggregation_prelaunch.py",
            "scripts/run_v180r12r2_ten_terminal_aggregation.py",
            "scripts/verify_v180r12r2_ten_terminal_aggregation.py",
            (
                "src/acfqp/construction_k7_ten_terminal_aggregation_"
                "campaign_accounting_v180r12r2.py"
            ),
            (
                "src/acfqp/construction_k7_ten_terminal_aggregation_"
                "finalizer_v180r12r2.py"
            ),
            (
                "src/acfqp/construction_k7_ten_terminal_aggregation_"
                "independent_verifier_v180r12r2.py"
            ),
        )
    )
)


class TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(ValueError):
    """The preregistered authorization or its exact source anchor changed."""


def _fail(message: str) -> NoReturn:
    raise TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(message)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_regular_symlink_free(path: Path) -> bytes:
    try:
        return source_runtime_v2._read_regular_symlink_free(path)  # noqa: SLF001
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(
            "authorization-evidence source is absent, linked, or nonregular"
        ) from error


def _source_fact(relative_path: str) -> dict[str, Any]:
    raw = _read_regular_symlink_free(_ROOT / relative_path)
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": _sha256(raw),
    }


def _local_literal_spans(raw: bytes) -> dict[str, tuple[int, int, bytes]]:
    """Independently locate the same narrow redaction surface as the auth."""

    try:
        tree = ast.parse(raw, filename=_EVIDENCE_RELATIVE_PATH)
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(
            "authorization-evidence wrapper is not static UTF-8 Python"
        ) from error
    line_offsets = [0]
    for line in raw.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(line))
    wanted = set(POST_PREREG_REDACTED_CONSTANTS)
    spans: dict[str, tuple[int, int, bytes]] = {}
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
            statement.target,
            ast.Name,
        ):
            name = statement.target.id
            value = statement.value
        if name not in wanted:
            continue
        if name in spans or value is None:
            _fail("post-prereg redacted constant is duplicated or valueless")
        literal = value.value if isinstance(value, ast.Constant) else None
        if name in _STRING_REDACTED_CONSTANTS:
            if type(literal) is not str:
                _fail("post-prereg string anchor is not a literal")
            replacement = _REDACTED_STRING_LITERAL
        elif name in _INTEGER_REDACTED_CONSTANTS:
            if type(literal) is not int:
                _fail("post-prereg integer anchor is not a literal")
            replacement = _REDACTED_INTEGER_LITERAL
        else:  # pragma: no cover - the two sets partition the allowlist
            raise AssertionError
        if not (
            type(value.lineno) is int
            and type(value.col_offset) is int
            and type(value.end_lineno) is int
            and type(value.end_col_offset) is int
            and 1 <= value.lineno <= value.end_lineno < len(line_offsets)
        ):
            _fail("post-prereg redacted constant has no exact source span")
        start = line_offsets[value.lineno - 1] + value.col_offset
        end = line_offsets[value.end_lineno - 1] + value.end_col_offset
        if not (0 <= start < end <= len(raw)):
            _fail("post-prereg redacted constant source span is invalid")
        try:
            tokens = tuple(
                token
                for token in tokenize.tokenize(
                    io.BytesIO(raw[start:end]).readline
                )
                if token.type
                not in {
                    tokenize.ENCODING,
                    tokenize.ENDMARKER,
                    tokenize.NEWLINE,
                    tokenize.NL,
                }
            )
        except (IndentationError, SyntaxError, tokenize.TokenError) as error:
            raise TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(
                "post-prereg literal tokenization failed"
            ) from error
        expected_token = (
            tokenize.STRING
            if name in _STRING_REDACTED_CONSTANTS
            else tokenize.NUMBER
        )
        if len(tokens) != 1 or tokens[0].type != expected_token:
            _fail("post-prereg anchor must be exactly one lexical literal token")
        spans[name] = (start, end, replacement)
    if set(spans) != wanted:
        _fail("post-prereg redacted constant allowlist is incomplete")
    return spans


def normalize_own_source_v180r12r2(raw: bytes) -> bytes:
    """Canonicalize only the post-prereg literal values in this wrapper."""

    if type(raw) is not bytes:
        raise TypeError("authorization-evidence wrapper source must be bytes")
    result = raw
    spans = sorted(_local_literal_spans(raw).values(), reverse=True)
    previous_start = len(raw)
    for start, end, replacement in spans:
        if end > previous_start:
            _fail("post-prereg redacted constant source spans overlap")
        result = result[:start] + replacement + result[end:]
        previous_start = start
    return result


def _normalized_evidence_source_fact() -> dict[str, Any]:
    raw = _read_regular_symlink_free(_ROOT / _EVIDENCE_RELATIVE_PATH)
    normalized = normalize_own_source_v180r12r2(raw)
    return {
        "relative_path": _EVIDENCE_RELATIVE_PATH,
        "binding_kind": "POST_PREREG_LITERAL_REDACTED_SOURCE_V1",
        "byte_count": len(normalized),
        "sha256": _sha256(normalized),
        "redacted_constant_names": list(POST_PREREG_REDACTED_CONSTANTS),
    }


def _post_prereg_literal_values(raw: bytes) -> dict[str, str | int]:
    values: dict[str, str | int] = {}
    for name, (start, end, _replacement) in _local_literal_spans(raw).items():
        try:
            value = ast.literal_eval(raw[start:end].decode("utf-8"))
        except (SyntaxError, UnicodeDecodeError, ValueError) as error:
            raise TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(
                "post-prereg literal value is not independently decodable"
            ) from error
        if not (
            (name in _STRING_REDACTED_CONSTANTS and type(value) is str)
            or (name in _INTEGER_REDACTED_CONSTANTS and type(value) is int)
        ):
            _fail("post-prereg literal value type changed")
        values[name] = value
    return values


def _git_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        }
    )
    return environment


def _run_git(
    arguments: tuple[str, ...],
    label: str,
    repository_root: Path = _ROOT,
) -> bytes:
    try:
        completed = subprocess.run(
            (GIT_EXECUTABLE, "-C", str(repository_root), *arguments),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=SOURCE_BOUNDARY_COMMAND_TIMEOUT_SECONDS,
            env=_git_environment(),
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(
            f"source-boundary Git {label} failed"
        ) from error
    if completed.returncode != 0:
        _fail(f"source-boundary Git {label} rejected the prereg commit")
    return completed.stdout


def _validate_source_relative_paths(paths: tuple[str, ...]) -> None:
    if not (
        paths == tuple(sorted(set(paths)))
        and 0 < len(paths) <= authorization.SOURCE_CATALOG_MODULE_CAP + 3
    ):
        _fail("source-boundary path set is unsorted, duplicated, or unbounded")
    for relative_path in paths:
        candidate = PurePosixPath(relative_path)
        if not (
            type(relative_path) is str
            and relative_path == candidate.as_posix()
            and not candidate.is_absolute()
            and candidate.parts
            and all(part not in {"", ".", ".."} for part in candidate.parts)
            and relative_path.startswith(("scripts/", "src/acfqp/"))
        ):
            _fail("source-boundary path escaped the prereg source roots")


def _archive_blobs(
    source_boundary_commit: str,
    paths: tuple[str, ...],
    repository_root: Path = _ROOT,
) -> dict[str, bytes]:
    archive_raw = _run_git(
        (
            "archive",
            "--format=tar",
            source_boundary_commit,
            "--",
            *paths,
        ),
        "archive",
        repository_root,
    )
    archive_cap = authorization.SOURCE_CATALOG_TOTAL_BYTE_CAP + 16 * 1024 * 1024
    if len(archive_raw) > archive_cap:
        _fail("source-boundary Git archive exceeded its frozen byte cap")
    blobs: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_raw), mode="r:") as archive:
            for member in archive.getmembers():
                if member.isdir():
                    continue
                if not member.isfile() or member.name in blobs:
                    _fail("source-boundary Git archive contains a foreign entry")
                extracted = archive.extractfile(member)
                if extracted is None:  # pragma: no cover - guarded by isfile
                    raise AssertionError
                raw = extracted.read()
                if len(raw) != member.size:
                    _fail("source-boundary Git archive entry was truncated")
                blobs[member.name] = raw
    except (tarfile.TarError, OSError) as error:
        raise TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(
            "source-boundary Git archive is malformed"
        ) from error
    if set(blobs) != set(paths):
        _fail("source-boundary Git archive omitted or added a source")
    return blobs


def _git_source_boundary_blobs(
    source_boundary_commit: str,
    paths: tuple[str, ...],
    repository_root: Path = _ROOT,
    *,
    candidate_only: bool,
) -> tuple[str, str, dict[str, bytes], bytes]:
    if type(candidate_only) is not bool:
        raise TypeError("candidate_only must be an explicit bool")
    if type(source_boundary_commit) is not str or _COMMIT_ID.fullmatch(
        source_boundary_commit
    ) is None:
        _fail("source_boundary_commit must be one explicit lowercase commit ID")
    _validate_source_relative_paths(paths)
    revision_raw = _run_git(
        (
            "rev-parse",
            "--show-toplevel",
            "--absolute-git-dir",
            "--git-common-dir",
            f"{source_boundary_commit}^{{commit}}",
            f"{source_boundary_commit}^{{tree}}",
            "HEAD^{commit}",
        ),
        "root-and-revision",
        repository_root,
    )
    try:
        lines = revision_raw.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(
            "source-boundary Git identity output is non-ASCII"
        ) from error
    if len(lines) != 6:
        _fail("source-boundary Git root or revision output changed")
    top_level, git_directory, common_directory, commit_id, tree_id, head_id = lines
    expected_root = repository_root.resolve(strict=True)
    top_path = Path(top_level).resolve(strict=True)
    git_path = Path(git_directory).resolve(strict=True)
    common_path = Path(common_directory)
    if not common_path.is_absolute():
        common_path = expected_root / common_path
    common_path = common_path.resolve(strict=True)
    if not (
        top_path == expected_root
        and git_path == expected_root / ".git"
        and common_path == git_path
        and commit_id == source_boundary_commit
        and _COMMIT_ID.fullmatch(tree_id) is not None
        and _COMMIT_ID.fullmatch(head_id) is not None
        and head_id != source_boundary_commit
    ):
        _fail("source-boundary Git root, commit, tree, or HEAD changed")
    forbidden_history_overlays = (
        git_path / "objects" / "info" / "alternates",
        git_path / "info" / "grafts",
        git_path / "shallow",
        git_path / "refs" / "replace",
    )
    if any(
        os.path.lexists(os.fspath(path))
        for path in forbidden_history_overlays
    ):
        _fail("source-boundary Git history overlays are forbidden")
    packed_refs = git_path / "packed-refs"
    if os.path.lexists(os.fspath(packed_refs)):
        packed_refs_raw = _read_regular_symlink_free(packed_refs)
        if any(
            line.partition(b" ")[2].startswith(b"refs/replace/")
            for line in packed_refs_raw.splitlines()
            if line and not line.startswith((b"#", b"^"))
        ):
            _fail("source-boundary Git history overlays are forbidden")
    chain_raw = _run_git(
        (
            "log",
            "--first-parent",
            "--reverse",
            "--format=%H%x09%P%x09%T",
            f"{source_boundary_commit}..{head_id}",
        ),
        "bridge-chain",
        repository_root,
    )
    try:
        chain_lines = chain_raw.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(
            "source-boundary bridge chain output is non-ASCII"
        ) from error
    previous = source_boundary_commit
    bridge_id: str | None = None
    chain_rows: list[tuple[str, str]] = []
    for line in chain_lines:
        fields = line.split("\t")
        if not (
            len(fields) == 3
            and _COMMIT_ID.fullmatch(fields[0]) is not None
            and fields[1] == previous
            and _COMMIT_ID.fullmatch(fields[2]) is not None
        ):
            _fail("source-boundary first-parent bridge chain changed")
        if bridge_id is None:
            bridge_id = fields[0]
        chain_rows.append((fields[0], fields[2]))
        previous = fields[0]
    if bridge_id is None or previous != head_id:
        _fail("source-boundary commit is not a strict first-parent ancestor")
    if not (
        chain_rows[0] == (bridge_id, tree_id)
        and bridge_id != source_boundary_commit
    ):
        _fail("source-boundary empty bridge commit or tree changed")
    if candidate_only and len(chain_rows) != 1:
        _fail("candidate build is allowed only at the empty bridge HEAD")
    if not candidate_only and len(chain_rows) < 2:
        _fail("runtime freeze requires the committed wrapper literal successor")
    literal_commit = chain_rows[1][0] if len(chain_rows) > 1 else None
    diff_target = literal_commit if literal_commit is not None else bridge_id
    diff_raw = _run_git(
        (
            "diff-tree",
            "--no-commit-id",
            "--raw",
            "--no-renames",
            "-r",
            diff_target,
        ),
        "literal-commit-diff",
        repository_root,
    )
    try:
        diff_lines = tuple(
            line for line in diff_raw.decode("utf-8").splitlines() if line
        )
    except UnicodeDecodeError as error:
        raise TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(
            "source-boundary literal-commit diff is non-UTF-8"
        ) from error
    literal_wrapper_object: str | None = None
    if literal_commit is None:
        if diff_lines:
            _fail("source-boundary empty bridge commit or tree changed")
    else:
        raw_match = re.fullmatch(
            r":100644 100644 ([0-9a-f]{40,64}) ([0-9a-f]{40,64}) M\t"
            + re.escape(_EVIDENCE_RELATIVE_PATH),
            diff_lines[0] if len(diff_lines) == 1 else "",
        )
        if raw_match is None:
            _fail(
                "source-boundary literal commit must modify only the regular wrapper"
            )
        literal_wrapper_object = raw_match.group(2)
    later_range_start = literal_commit if literal_commit is not None else bridge_id
    later_touch_raw = _run_git(
        (
            "log",
            "--first-parent",
            "--format=%H",
            "--name-only",
            "--no-renames",
            f"{later_range_start}..{head_id}",
            "--",
            *paths,
        ),
        "post-literal-bound-history",
        repository_root,
    )
    if later_touch_raw.strip():
        _fail("source-boundary history touched a bound source after literal freeze")
    boundary_blobs = _archive_blobs(source_boundary_commit, paths, repository_root)
    wrapper_object = (
        literal_wrapper_object
        if literal_wrapper_object is not None
        else f"{source_boundary_commit}:{_EVIDENCE_RELATIVE_PATH}"
    )
    committed_wrapper = _run_git(
        ("cat-file", "blob", wrapper_object),
        "committed-wrapper-blob",
        repository_root,
    )
    if len(committed_wrapper) > authorization.SOURCE_CATALOG_TOTAL_BYTE_CAP:
        _fail("source-boundary committed wrapper exceeded its frozen byte cap")
    if literal_commit is None:
        if committed_wrapper != boundary_blobs[_EVIDENCE_RELATIVE_PATH]:
            _fail("candidate bridge wrapper blob differs from C_pre")
    else:
        boundary_wrapper = boundary_blobs[_EVIDENCE_RELATIVE_PATH]
        if not all(
            value == ("0" * 64 if name in _STRING_REDACTED_CONSTANTS else 0)
            for name, value in _post_prereg_literal_values(boundary_wrapper).items()
        ):
            _fail("source-boundary wrapper did not retain all eight sentinels")
        literal_values = _post_prereg_literal_values(committed_wrapper)
        if not all(
            (
                type(value) is str
                and _COMMIT_ID.fullmatch(value) is None
                and re.fullmatch(r"[0-9a-f]{64}", value) is not None
                and value != "0" * 64
            )
            if name in _STRING_REDACTED_CONSTANTS
            else type(value) is int and value > 0
            for name, value in literal_values.items()
        ):
            _fail("source-boundary literal commit did not freeze all eight literals")
        if normalize_own_source_v180r12r2(boundary_wrapper) != (
            normalize_own_source_v180r12r2(committed_wrapper)
        ):
            _fail("source-boundary literal commit changed outside eight literals")
    return tree_id, bridge_id, boundary_blobs, committed_wrapper


def _fact_from_raw(relative_path: str, raw: bytes) -> dict[str, Any]:
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": _sha256(raw),
    }


def _verify_source_boundary_blobs(
    boundary_blobs: dict[str, bytes],
    current_blobs: dict[str, bytes],
    bound_source_facts: dict[str, dict[str, Any]],
    expected_authorization_source_fact: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    closure_paths = tuple(sorted(bound_source_facts))
    all_paths = tuple(sorted((*closure_paths, _AUTHORIZATION_RELATIVE_PATH)))
    if not (
        set(boundary_blobs) == set(all_paths)
        and set(current_blobs) == set(all_paths)
        and _AUTHORIZATION_RELATIVE_PATH not in bound_source_facts
        and _EVIDENCE_RELATIVE_PATH in bound_source_facts
    ):
        _fail("source-boundary blob set changed")
    boundary_facts: list[dict[str, Any]] = []
    for relative_path in closure_paths:
        boundary_raw = boundary_blobs[relative_path]
        current_raw = current_blobs[relative_path]
        if relative_path == _EVIDENCE_RELATIVE_PATH:
            sentinel_values = _post_prereg_literal_values(boundary_raw)
            if not all(
                value == ("0" * 64 if name in _STRING_REDACTED_CONSTANTS else 0)
                for name, value in sentinel_values.items()
            ):
                _fail("source-boundary wrapper did not retain all eight sentinels")
            boundary_normalized = normalize_own_source_v180r12r2(boundary_raw)
            current_normalized = normalize_own_source_v180r12r2(current_raw)
            fact = {
                "relative_path": relative_path,
                "binding_kind": "POST_PREREG_LITERAL_REDACTED_SOURCE_V1",
                "byte_count": len(boundary_normalized),
                "sha256": _sha256(boundary_normalized),
                "redacted_constant_names": list(POST_PREREG_REDACTED_CONSTANTS),
            }
            if boundary_normalized != current_normalized:
                _fail("source-boundary wrapper changed outside eight literals")
        else:
            if boundary_raw != current_raw:
                _fail("source-boundary ordinary source differs from current bytes")
            fact = _fact_from_raw(relative_path, boundary_raw)
        if fact != bound_source_facts[relative_path]:
            _fail("source-boundary source fact differs from authorization closure")
        boundary_facts.append(fact)
    if not (
        boundary_blobs[_AUTHORIZATION_RELATIVE_PATH]
        == current_blobs[_AUTHORIZATION_RELATIVE_PATH]
        and _fact_from_raw(
            _AUTHORIZATION_RELATIVE_PATH,
            boundary_blobs[_AUTHORIZATION_RELATIVE_PATH],
        )
        == expected_authorization_source_fact
    ):
        _fail("source-boundary authorization source differs from frozen bytes")
    return tuple(boundary_facts)


def _replay_git_source_boundary(
    source_boundary_commit: str,
    bound_source_facts: dict[str, dict[str, Any]],
    expected_authorization_source_fact: dict[str, Any],
    *,
    candidate_only: bool,
) -> dict[str, Any]:
    paths = tuple(
        sorted((*bound_source_facts, _AUTHORIZATION_RELATIVE_PATH))
    )
    tree_id, bridge_id, boundary_blobs, committed_wrapper = (
        _git_source_boundary_blobs(
            source_boundary_commit,
            paths,
            _ROOT,
            candidate_only=candidate_only,
        )
    )
    current_blobs = {
        relative_path: _read_regular_symlink_free(_ROOT / relative_path)
        for relative_path in paths
    }
    if not candidate_only and (
        current_blobs[_EVIDENCE_RELATIVE_PATH] != committed_wrapper
    ):
        _fail("current wrapper bytes differ from the literal commit")
    replayed = _verify_source_boundary_blobs(
        boundary_blobs,
        current_blobs,
        bound_source_facts,
        expected_authorization_source_fact,
    )
    return {
        "source_boundary_commit": source_boundary_commit,
        "source_boundary_tree": tree_id,
        "source_boundary_empty_bridge_commit": bridge_id,
        "source_boundary_empty_bridge_tree": tree_id,
        "source_boundary_replayed_source_fact_file_count": len(replayed),
        "source_boundary_replayed_source_fact_byte_count": sum(
            row["byte_count"] for row in replayed
        ),
        "source_boundary_replayed_source_facts_sha256": _sha256(
            canonical_json_bytes(list(replayed))
        ),
        "source_boundary_authorization_source_fact": (
            expected_authorization_source_fact
        ),
        "source_boundary_wrapper_normalized_source_fact": (
            bound_source_facts[_EVIDENCE_RELATIVE_PATH]
        ),
        "source_boundary_git_process_count": SOURCE_BOUNDARY_GIT_PROCESS_COUNT,
        "source_boundary_commit_is_strict_ancestor_of_current_head": True,
        "source_boundary_empty_bridge_is_immediate_child": True,
        "source_boundary_empty_bridge_preserved_entire_tree": True,
        "source_boundary_bridge_then_wrapper_eight_literal_commit_sequence": True,
        "source_boundary_candidate_build_relaxes_only_literal_commit_presence": (
            True
        ),
        "source_boundary_candidate_build_allowed_only_at_empty_bridge_head": True,
        "source_boundary_runtime_freeze_requires_committed_literals": True,
        "source_boundary_runtime_reads_literal_commit_wrapper_blob_and_mode": True,
        "source_boundary_runtime_requires_current_wrapper_exact_literal_commit": True,
        "source_boundary_candidate_and_runtime_payload_identity_equal": True,
        "source_boundary_second_commit_tree_diff_only_wrapper_required": True,
        "source_boundary_second_commit_wrapper_normalizes_to_preboundary": True,
        "source_boundary_post_literal_bound_history_touch_rejected": True,
        "source_boundary_wrapper_eight_sentinels_verified": True,
        "source_boundary_ordinary_and_authorization_sources_equal_current": True,
    }


def _is_frozen_identity(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and value != "0" * 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _require_post_prereg_authorization_constants() -> None:
    identities = (
        EXPECTED_AUTHORIZATION_ID,
        EXPECTED_AUTHORIZATION_CANONICAL_SHA256,
        EXPECTED_AUTHORIZATION_SOURCE_SHA256,
    )
    if not (
        all(_is_frozen_identity(value) for value in identities)
        and type(EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT) is int
        and EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT > 0
        and type(EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT) is int
        and EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT > 0
        and EXPECTED_PROTOCOL_ID == protocol.EXPECTED_PROTOCOL_ID
        and EXPECTED_AGGREGATION_EXECUTION_SLOT_ID
        == protocol.EXPECTED_AGGREGATION_EXECUTION_SLOT_ID
        and authorization.EXPECTED_AUTHORIZATION_ID
        == EXPECTED_AUTHORIZATION_ID
        and authorization.EXPECTED_CANONICAL_BYTE_COUNT
        == EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT
        and authorization.EXPECTED_CANONICAL_SHA256
        == EXPECTED_AUTHORIZATION_CANONICAL_SHA256
        and tuple(POST_PREREG_REDACTED_CONSTANTS)
        == tuple(
            authorization.AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS
        )
    ):
        _fail("post-prereg authorization anchor is not frozen")


def _require_frozen_evidence_constants() -> None:
    if not (
        _is_frozen_identity(EXPECTED_AUTHORIZATION_EVIDENCE_ID)
        and _is_frozen_identity(EXPECTED_CANONICAL_SHA256)
        and type(EXPECTED_CANONICAL_BYTE_COUNT) is int
        and EXPECTED_CANONICAL_BYTE_COUNT > 0
    ):
        _fail("authorization evidence is not frozen")
    _require_post_prereg_authorization_constants()


def build_ten_terminal_aggregation_authorization_evidence_v180r12r2(
    source_boundary_commit: str,
    *,
    candidate_only: bool,
) -> dict[str, Any]:
    if type(candidate_only) is not bool:
        raise TypeError("candidate_only must be an explicit bool")
    _require_post_prereg_authorization_constants()
    frozen = (
        authorization.freeze_ten_terminal_aggregation_execution_authorization_v180r12r2()
    )
    authorization_document = frozen.to_document()
    authorization_raw = frozen.canonical_bytes
    try:
        replayed_source_facts = authorization.replay_authorization_source_facts_v180r12r2(
            authorization_document
        )
    except Exception as error:
        raise TenTerminalAggregationAuthorizationEvidenceV180R12R2Error(
            "authorization source closure did not replay"
        ) from error
    bound_source_facts = {
        row["relative_path"]: row for row in replayed_source_facts
    }
    authorization_source_fact = _source_fact(_AUTHORIZATION_RELATIVE_PATH)
    normalized_evidence_source_fact = _normalized_evidence_source_fact()
    execution_chain_source_facts = [
        _source_fact(relative_path)
        for relative_path in EXECUTION_CHAIN_RELATIVE_PATHS
    ]
    expected_authorization_source_fact = {
        "relative_path": _AUTHORIZATION_RELATIVE_PATH,
        "byte_count": EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT,
        "sha256": EXPECTED_AUTHORIZATION_SOURCE_SHA256,
    }
    if not (
        frozen.authorization_id == EXPECTED_AUTHORIZATION_ID
        and authorization.EXPECTED_AUTHORIZATION_ID
        == EXPECTED_AUTHORIZATION_ID
        and len(authorization_raw) == EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT
        and _sha256(authorization_raw)
        == EXPECTED_AUTHORIZATION_CANONICAL_SHA256
        and authorization.EXPECTED_CANONICAL_BYTE_COUNT
        == EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT
        and authorization.EXPECTED_CANONICAL_SHA256
        == EXPECTED_AUTHORIZATION_CANONICAL_SHA256
        and authorization_document["aggregation_protocol_id"]
        == EXPECTED_PROTOCOL_ID
        and authorization_document["aggregation_execution_slot"][
            "aggregation_execution_slot_id"
        ]
        == EXPECTED_AGGREGATION_EXECUTION_SLOT_ID
        and authorization_source_fact == expected_authorization_source_fact
        and authorization_document["source_fact_exclusions"]
        == list(SOURCE_FACT_EXCLUSIONS)
        and authorization_document[
            "authorization_self_source_bound_by_post_prereg_freeze"
        ]
        is False
        and authorization_document[
            "authorization_evidence_wrapper_source_bound_in_authorization_closure"
        ]
        is True
        and authorization_document[
            "authorization_evidence_wrapper_binding_kind"
        ]
        == "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"
        and authorization_document[
            "authorization_evidence_wrapper_redacted_constant_names"
        ]
        == list(POST_PREREG_REDACTED_CONSTANTS)
        and authorization_document[
            "authorization_evidence_wrapper_self_source_excluded"
        ]
        is False
        and authorization_document[
            "authorization_evidence_source_boundary_commit_required"
        ]
        is True
        and authorization_document[
            "authorization_evidence_empty_bridge_commit_required"
        ]
        is True
        and authorization_document[
            "authorization_evidence_empty_bridge_must_preserve_entire_tree"
        ]
        is True
        and authorization_document[
            "authorization_evidence_bridge_then_wrapper_eight_literal_commit_"
            "sequence_required"
        ]
        is True
        and authorization_document[
            "authorization_evidence_candidate_build_may_relax_only_literal_"
            "commit_presence"
        ]
        is True
        and authorization_document[
            "authorization_evidence_runtime_freeze_requires_committed_wrapper_"
            "literals"
        ]
        is True
        and authorization_document[
            "authorization_evidence_candidate_and_runtime_payload_identity_"
            "must_match"
        ]
        is True
        and authorization_document[
            "authorization_evidence_post_literal_bound_history_touch_forbidden"
        ]
        is True
        and authorization_document[
            "authorization_evidence_source_boundary_git_process_count"
        ]
        == SOURCE_BOUNDARY_GIT_PROCESS_COUNT
        and authorization_document[
            "authorization_evidence_source_boundary_git_processes_are_"
            "preauthorization_not_campaign_actual_measurements"
        ]
        is True
        and authorization_document["prelaunch_contract"]
        == protocol.prelaunch_contract_v180r12r2()
        and authorization_document["prelaunch_contract"][
            "actual_manifest_digest_preregistered"
        ]
        is False
        and authorization_document["prelaunch_contract"]["launch_rule_id"]
        == protocol.PRELAUNCH_LAUNCH_RULE_ID
        and authorization_document[
            "authorization_evidence_verification_is_first_action_inside_runner_"
            "main_after_prelaunch_dispatch"
        ]
        is True
        and authorization_document[
            "authorization_evidence_verification_precedes_scientific_output_"
            "inspection_or_creation_inside_runner"
        ]
        is True
        and authorization_document[
            "authorization_evidence_verification_is_process_first_action"
        ]
        is False
        and authorization_document["self_identity_cycle_avoided"] is True
        and bound_source_facts.get(_EVIDENCE_RELATIVE_PATH)
        == normalized_evidence_source_fact
        and all(
            bound_source_facts.get(row["relative_path"]) == row
            for row in execution_chain_source_facts
        )
        and _AUTHORIZATION_RELATIVE_PATH not in bound_source_facts
        and authorization_document["v180r12r2_outcome_bytes_accessed"] is False
        and authorization_document["official_execution_allowed"] is False
    ):
        _fail("authorization or its preregistered source anchors changed")

    source_boundary = _replay_git_source_boundary(
        source_boundary_commit,
        bound_source_facts,
        expected_authorization_source_fact,
        candidate_only=candidate_only,
    )
    if not (
        source_boundary["source_boundary_replayed_source_fact_file_count"]
        == authorization_document["source_fact_file_count"]
        and source_boundary["source_boundary_replayed_source_fact_byte_count"]
        == authorization_document["source_fact_byte_count"]
        and source_boundary["source_boundary_replayed_source_facts_sha256"]
        == authorization_document["source_facts_sha256"]
    ):
        _fail("source-boundary closure digest differs from authorization")

    payload = {
        "schema": (
            "acfqp.ten_terminal_aggregation_execution_authorization_evidence."
            "v180r12r2"
        ),
        "authorization_evidence_domain": (
            domains.CONSTRUCTION_K7_AUTHORIZATION_EVIDENCE_V180R12R2_DOMAIN
        ),
        "execution_authorization_id": frozen.authorization_id,
        "aggregation_protocol_id": EXPECTED_PROTOCOL_ID,
        "aggregation_execution_slot_id": (
            EXPECTED_AGGREGATION_EXECUTION_SLOT_ID
        ),
        "authorization_canonical_byte_count": len(authorization_raw),
        "authorization_canonical_sha256": _sha256(authorization_raw),
        "authorization_source_fact": authorization_source_fact,
        "authorization_evidence_wrapper_normalized_source_fact": (
            normalized_evidence_source_fact
        ),
        "execution_chain_source_facts": execution_chain_source_facts,
        "prelaunch_contract": authorization_document["prelaunch_contract"],
        **source_boundary,
        "authorization_source_fact_exclusions": list(SOURCE_FACT_EXCLUSIONS),
        "authorization_self_source_bound_by_this_evidence": True,
        "authorization_evidence_wrapper_source_bound_by_authorization": True,
        "authorization_evidence_wrapper_nonliteral_bytes_independently_replayed": (
            True
        ),
        "authorization_evidence_wrapper_redacted_literals_semantically_locked": (
            True
        ),
        "identity_cycle_avoidance_rule": (
            "AUTHORIZATION_BINDS_WRAPPER_AFTER_CANONICAL_REDACTION_OF_ONLY_"
            "THE_ALLOWLISTED_POST_PREREG_LITERAL_VALUES_WRAPPER_LITERALS_"
            "LOCK_EXACT_AUTHORIZATION_AND_EVIDENCE_IDENTITIES"
        ),
        "authorization_preregistered_before_this_evidence": True,
        "source_boundary_replay_required_before_authorization_acceptance": True,
        "preauthorization_source_boundary_git_process_count": (
            SOURCE_BOUNDARY_GIT_PROCESS_COUNT
        ),
        "preauthorization_git_processes_are_not_campaign_actual_measurements": (
            True
        ),
        "authorization_evidence_verification_required_as_first_action_inside_"
        "runner_main_after_prelaunch_dispatch": True,
        "authorization_evidence_verification_required_before_scientific_"
        "output_inspection_or_creation_inside_runner": True,
        "authorization_evidence_verification_is_process_first_action": False,
        "v180r12r2_outcome_bytes_accessed": False,
        "aggregation_execution_count": 0,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "outcome_free": True,
    }
    return {
        **payload,
        "authorization_evidence_id": domains.extension_content_id_v180r12r2(
            domains.CONSTRUCTION_K7_AUTHORIZATION_EVIDENCE_V180R12R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TenTerminalAggregationAuthorizationEvidenceV180R12R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_evidence_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = dict(document) if type(document) is dict else {}
        identity = payload.pop("authorization_evidence_id", None)
        if not (
            self._issuer is _ISSUER
            and type(document) is dict
            and canonical_json_bytes(document) == self.canonical_bytes
            and identity == self.authorization_evidence_id
            and identity
            == domains.extension_content_id_v180r12r2(
                domains.CONSTRUCTION_K7_AUTHORIZATION_EVIDENCE_V180R12R2_DOMAIN,
                payload,
            )
        ):
            _fail("V180r12r2 authorization evidence is foreign or noncanonical")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


@lru_cache(maxsize=1)
def freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2(
    source_boundary_commit: str,
) -> (
    TenTerminalAggregationAuthorizationEvidenceV180R12R2
):
    _require_frozen_evidence_constants()
    document = build_ten_terminal_aggregation_authorization_evidence_v180r12r2(
        source_boundary_commit,
        candidate_only=False,
    )
    raw = canonical_json_bytes(document)
    if not (
        document["authorization_evidence_id"]
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and _sha256(raw) == EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen authorization evidence identity changed")
    return TenTerminalAggregationAuthorizationEvidenceV180R12R2(
        _ISSUER,
        raw,
        document["authorization_evidence_id"],
    )


__all__ = (
    "EXECUTION_CHAIN_RELATIVE_PATHS",
    "EXPECTED_AGGREGATION_EXECUTION_SLOT_ID",
    "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_PROTOCOL_ID",
    "POST_PREREG_REDACTED_CONSTANTS",
    "SOURCE_BOUNDARY_GIT_PROCESS_COUNT",
    "SOURCE_FACT_EXCLUSIONS",
    "TenTerminalAggregationAuthorizationEvidenceV180R12R2",
    "TenTerminalAggregationAuthorizationEvidenceV180R12R2Error",
    "build_ten_terminal_aggregation_authorization_evidence_v180r12r2",
    "freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2",
    "normalize_own_source_v180r12r2",
)
