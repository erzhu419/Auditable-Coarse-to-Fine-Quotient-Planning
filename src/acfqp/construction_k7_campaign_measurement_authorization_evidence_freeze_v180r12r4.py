"""External, non-bootstrapping evidence for the V180r12r4 authorization.

The authorization deliberately retains zero self-identity and source-closure
literals.  An external ``C_pre`` commit freezes its exact candidate source
closure, an immediate empty bridge preserves the whole tree, and one following
commit may change only the twelve allowlisted literal values in this wrapper.
Normalizing those literals must reproduce the exact ``C_pre`` wrapper bytes.
No campaign outcome is read or produced by this module.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tarfile
import tokenize
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v180r12r4 as domains
from acfqp import (
    construction_k7_campaign_measurement_execution_authorization_v180r12r4
    as authorization,
)
from acfqp import construction_k7_campaign_measurement_protocol_v180r12r4 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ZERO_ID = "0" * 64

# These are the complete post-C_pre literal allowlist.  They intentionally
# remain sentinels in this outcome-free preregistration slice.  Keep every value
# as one direct module-level literal; the independent normalizer rejects aliases,
# expressions, duplicate assignments, and missing names.
EXPECTED_AUTHORIZATION_EVIDENCE_ID = "14f24d7f6a66ea37174cc700c3325ecd64dc360bc91777d77d61f7eb3f6ece09"
EXPECTED_CANONICAL_BYTE_COUNT = 76448
EXPECTED_CANONICAL_SHA256 = "20ee9254f9ca91f1f1b1d5365b576954a13fa8023a132247fd4e4334e4056669"
EXPECTED_AUTHORIZATION_ID = "b4a62ae6656e12ed4a097d7369d881f127e546b6658708ddc5cf9d599b55f6f9"
EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT = 384019
EXPECTED_AUTHORIZATION_CANONICAL_SHA256 = "7dac84d9a2ed34a1927d39d1a80f086e8a70b8a9d7f629384df762350ecccebf"
EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT = 60742
EXPECTED_AUTHORIZATION_SOURCE_SHA256 = "a4e0620120aba3a6bd3fe41ee9f9905c3d3c7145f37b2850ddeb66717c1f0d04"
EXPECTED_SOURCE_CLOSURE_ID = "e0ecd5337a58a5ba2a675879c18c95ca147b14da972352a50879cdd33830e698"
EXPECTED_SOURCE_CLOSURE_BYTE_COUNT = 5823
EXPECTED_SOURCE_CLOSURE_SHA256 = "e0ecd5337a58a5ba2a675879c18c95ca147b14da972352a50879cdd33830e698"
EXPECTED_SOURCE_CLOSURE_FILE_COUNT = 22

POST_PREREG_REDACTED_CONSTANTS = (
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
    "EXPECTED_SOURCE_CLOSURE_ID",
    "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT",
    "EXPECTED_SOURCE_CLOSURE_SHA256",
    "EXPECTED_SOURCE_CLOSURE_FILE_COUNT",
)
_STRING_REDACTED_CONSTANTS = frozenset(
    {
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
        "EXPECTED_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_ID",
        "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
        "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
        "EXPECTED_SOURCE_CLOSURE_ID",
        "EXPECTED_SOURCE_CLOSURE_SHA256",
    }
)
_INTEGER_REDACTED_CONSTANTS = frozenset(
    {
        "EXPECTED_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
        "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
        "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT",
        "EXPECTED_SOURCE_CLOSURE_FILE_COUNT",
    }
)
_REDACTED_STRING_LITERAL = b'"0000000000000000000000000000000000000000000000000000000000000000"'
_REDACTED_INTEGER_LITERAL = b"0"

GIT_EXECUTABLE = "/usr/bin/git"
SOURCE_BOUNDARY_GIT_PROCESS_COUNT = 6
SOURCE_BOUNDARY_COMMAND_TIMEOUT_SECONDS = 120
_COMMIT_ID = re.compile(r"^[0-9a-f]{40}$")
_OBJECT_ID = re.compile(r"^[0-9a-f]{40,64}$")

_ROOT = Path(__file__).resolve().parents[2]
_AUTHORIZATION_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_execution_authorization_v180r12r4.py"
)
_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_authorization_evidence_freeze_v180r12r4.py"
)
SOURCE_FACT_EXCLUSIONS: tuple[str, ...] = ()
SOURCE_BOUNDARY_REQUIRED_PATHS = tuple(authorization.SOURCE_CLOSURE_REQUIRED_ROOTS)
EXECUTION_CHAIN_RELATIVE_PATHS = tuple(
    path
    for path in SOURCE_BOUNDARY_REQUIRED_PATHS
    if path not in {_AUTHORIZATION_RELATIVE_PATH, _EVIDENCE_RELATIVE_PATH}
)


class CampaignMeasurementAuthorizationEvidenceV180R12R4Error(ValueError):
    """The external source boundary or authorization candidate changed."""


def _fail(message: str) -> NoReturn:
    raise CampaignMeasurementAuthorizationEvidenceV180R12R4Error(message)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_frozen_identity(value: object) -> bool:
    return (
        type(value) is str
        and value != ZERO_ID
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    )


def _normalized_relative_path(value: Any, label: str) -> str:
    if type(value) is not str:
        _fail(f"{label} must be one relative path")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or candidate.as_posix() != value
        or not value.startswith(("scripts/", "src/acfqp/"))
    ):
        _fail(f"{label} escaped the preregistered source roots")
    return value


def _read_regular_stable(path: Path) -> bytes:
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _fail("authorization-evidence source is linked or nonregular")
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as error:
        raise CampaignMeasurementAuthorizationEvidenceV180R12R4Error(
            "authorization-evidence source is absent or unreadable"
        ) from error
    try:
        opened = os.fstat(descriptor)
        chunks: list[bytes] = []
        total = 0
        while True:
            remaining = authorization.SOURCE_CATALOG_TOTAL_BYTE_CAP + 1 - total
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > authorization.SOURCE_CATALOG_TOTAL_BYTE_CAP:
                _fail("authorization-evidence source exceeded the source cap")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fact = lambda row: (  # noqa: E731
        row.st_dev,
        row.st_ino,
        row.st_mode,
        row.st_nlink,
        row.st_size,
        row.st_mtime_ns,
        row.st_ctime_ns,
    )
    raw = b"".join(chunks)
    if not (fact(before) == fact(opened) == fact(after) and len(raw) == before.st_size):
        _fail("authorization-evidence source changed during stable read")
    return raw


def _literal_spans(raw: bytes) -> dict[str, tuple[int, int, bytes]]:
    """Locate the exact twelve-literal post-C_pre mutation surface."""

    if type(raw) is not bytes:
        raise TypeError("authorization-evidence wrapper source must be bytes")
    try:
        tree = ast.parse(raw, filename=_EVIDENCE_RELATIVE_PATH)
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise CampaignMeasurementAuthorizationEvidenceV180R12R4Error(
            "authorization-evidence wrapper is not static UTF-8 Python"
        ) from error
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
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
            statement.target, ast.Name
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
                _fail("post-prereg string anchor is not one literal")
            replacement = _REDACTED_STRING_LITERAL
            expected_token = tokenize.STRING
        elif name in _INTEGER_REDACTED_CONSTANTS:
            if type(literal) is not int:
                _fail("post-prereg integer anchor is not one literal")
            replacement = _REDACTED_INTEGER_LITERAL
            expected_token = tokenize.NUMBER
        else:  # pragma: no cover - the two sets partition the allowlist
            raise AssertionError
        if not all(
            type(row) is int
            for row in (
                value.lineno,
                value.col_offset,
                value.end_lineno,
                value.end_col_offset,
            )
        ):
            _fail("post-prereg literal lacks one exact source span")
        start = offsets[value.lineno - 1] + value.col_offset
        end = offsets[value.end_lineno - 1] + value.end_col_offset
        if not (0 <= start < end <= len(raw)):
            _fail("post-prereg literal source span is invalid")
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
            raise CampaignMeasurementAuthorizationEvidenceV180R12R4Error(
                "post-prereg literal tokenization failed"
            ) from error
        if len(tokens) != 1 or tokens[0].type != expected_token:
            _fail("post-prereg anchor must be exactly one lexical literal token")
        spans[name] = (start, end, replacement)
    if set(spans) != wanted:
        _fail("post-prereg redacted constant allowlist is incomplete")
    return spans


def normalize_own_source_v180r12r4(raw: bytes) -> bytes:
    """Replace only the twelve allowlisted values with their C_pre sentinels."""

    result = raw
    previous_start = len(raw)
    for start, end, replacement in sorted(
        _literal_spans(raw).values(), reverse=True
    ):
        if end > previous_start:
            _fail("post-prereg literal source spans overlap")
        result = result[:start] + replacement + result[end:]
        previous_start = start
    return result


def _literal_values(raw: bytes) -> dict[str, str | int]:
    result: dict[str, str | int] = {}
    for name, (start, end, _replacement) in _literal_spans(raw).items():
        try:
            value = ast.literal_eval(raw[start:end].decode("utf-8"))
        except (SyntaxError, UnicodeDecodeError, ValueError) as error:
            raise CampaignMeasurementAuthorizationEvidenceV180R12R4Error(
                "post-prereg literal is not independently decodable"
            ) from error
        result[name] = value
    return result


def _all_sentinels(values: Mapping[str, str | int]) -> bool:
    return all(
        value == (ZERO_ID if name in _STRING_REDACTED_CONSTANTS else 0)
        for name, value in values.items()
    )


def _all_frozen_literals(values: Mapping[str, str | int]) -> bool:
    return all(
        _is_frozen_identity(value)
        if name in _STRING_REDACTED_CONSTANTS
        else type(value) is int and value > 0
        for name, value in values.items()
    )


def _fact_from_raw(relative_path: str, raw: bytes) -> dict[str, Any]:
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": _sha256(raw),
    }


def _git_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
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
        raise CampaignMeasurementAuthorizationEvidenceV180R12R4Error(
            f"source-boundary Git {label} failed"
        ) from error
    if completed.returncode != 0:
        _fail(f"source-boundary Git {label} rejected the prereg commit")
    return completed.stdout


def _validate_source_paths(paths: tuple[str, ...]) -> None:
    if not (
        paths == tuple(sorted(set(paths)))
        and 0 < len(paths) <= authorization.SOURCE_CATALOG_MODULE_CAP
        and _AUTHORIZATION_RELATIVE_PATH in paths
        and _EVIDENCE_RELATIVE_PATH in paths
    ):
        _fail("source-boundary path set is incomplete, duplicated, or unbounded")
    for path in paths:
        _normalized_relative_path(path, "source-boundary path")


def _archive_blobs(
    source_boundary_commit: str,
    paths: tuple[str, ...],
    repository_root: Path,
) -> dict[str, bytes]:
    raw = _run_git(
        ("archive", "--format=tar", source_boundary_commit, "--", *paths),
        "archive",
        repository_root,
    )
    if len(raw) > authorization.SOURCE_CATALOG_TOTAL_BYTE_CAP + 16 * 1024 * 1024:
        _fail("source-boundary archive exceeded its frozen byte cap")
    result: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            for member in archive.getmembers():
                if member.isdir():
                    continue
                if not member.isfile() or member.name in result:
                    _fail("source-boundary archive contains a foreign entry")
                extracted = archive.extractfile(member)
                if extracted is None:  # pragma: no cover
                    raise AssertionError
                blob = extracted.read()
                if len(blob) != member.size:
                    _fail("source-boundary archive entry was truncated")
                result[member.name] = blob
    except (tarfile.TarError, OSError) as error:
        raise CampaignMeasurementAuthorizationEvidenceV180R12R4Error(
            "source-boundary archive is malformed"
        ) from error
    if set(result) != set(paths):
        _fail("source-boundary archive omitted or added a source")
    return result


def _git_source_boundary_blobs(
    source_boundary_commit: str,
    paths: tuple[str, ...],
    repository_root: Path = _ROOT,
    *,
    candidate_only: bool,
) -> tuple[str, str, dict[str, bytes], bytes]:
    """Replay C_pre -> empty bridge -> wrapper-only literal commit."""

    if type(candidate_only) is not bool:
        raise TypeError("candidate_only must be an explicit bool")
    if type(source_boundary_commit) is not str or _COMMIT_ID.fullmatch(
        source_boundary_commit
    ) is None:
        _fail("source_boundary_commit must be one explicit lowercase commit ID")
    _validate_source_paths(paths)
    revision = _run_git(
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
        lines = revision.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise CampaignMeasurementAuthorizationEvidenceV180R12R4Error(
            "source-boundary revision output is non-ASCII"
        ) from error
    if len(lines) != 6:
        _fail("source-boundary root or revision output changed")
    top, git_dir, common_dir, commit_id, tree_id, head_id = lines
    expected_root = repository_root.resolve(strict=True)
    common_path = Path(common_dir)
    if not common_path.is_absolute():
        common_path = expected_root / common_path
    if not (
        Path(top).resolve(strict=True) == expected_root
        and Path(git_dir).resolve(strict=True) == expected_root / ".git"
        and common_path.resolve(strict=True) == expected_root / ".git"
        and commit_id == source_boundary_commit
        and _COMMIT_ID.fullmatch(tree_id) is not None
        and _COMMIT_ID.fullmatch(head_id) is not None
        and head_id != source_boundary_commit
    ):
        _fail("source-boundary root, commit, tree, or HEAD changed")
    git_path = expected_root / ".git"
    overlays = (
        git_path / "objects" / "info" / "alternates",
        git_path / "info" / "grafts",
        git_path / "shallow",
        git_path / "refs" / "replace",
    )
    if any(os.path.lexists(os.fspath(path)) for path in overlays):
        _fail("source-boundary Git history overlays are forbidden")
    packed_refs = git_path / "packed-refs"
    if os.path.lexists(os.fspath(packed_refs)):
        packed = _read_regular_stable(packed_refs)
        if any(
            line.partition(b" ")[2].startswith(b"refs/replace/")
            for line in packed.splitlines()
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
        raise CampaignMeasurementAuthorizationEvidenceV180R12R4Error(
            "source-boundary bridge chain is non-ASCII"
        ) from error
    previous = source_boundary_commit
    rows: list[tuple[str, str]] = []
    for line in chain_lines:
        fields = line.split("\t")
        if not (
            len(fields) == 3
            and _COMMIT_ID.fullmatch(fields[0]) is not None
            and fields[1] == previous
            and _COMMIT_ID.fullmatch(fields[2]) is not None
        ):
            _fail("source-boundary first-parent bridge chain changed")
        rows.append((fields[0], fields[2]))
        previous = fields[0]
    if not rows or previous != head_id or rows[0][1] != tree_id:
        _fail("source-boundary empty bridge commit or tree changed")
    bridge_id = rows[0][0]
    if candidate_only and len(rows) != 1:
        _fail("candidate build is allowed only at the empty bridge HEAD")
    if not candidate_only and len(rows) < 2:
        _fail("runtime freeze requires the wrapper-only literal successor")
    literal_commit = rows[1][0] if len(rows) >= 2 else None
    diff_target = literal_commit or bridge_id
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
        raise CampaignMeasurementAuthorizationEvidenceV180R12R4Error(
            "source-boundary literal diff is non-UTF-8"
        ) from error
    literal_wrapper_object: str | None = None
    if literal_commit is None:
        if diff_lines:
            _fail("source-boundary empty bridge commit or tree changed")
    else:
        pattern = (
            r":100644 100644 ([0-9a-f]{40,64}) ([0-9a-f]{40,64}) M\t"
            + re.escape(_EVIDENCE_RELATIVE_PATH)
        )
        match = re.fullmatch(pattern, diff_lines[0] if len(diff_lines) == 1 else "")
        if match is None:
            _fail("literal commit must modify only the regular evidence wrapper")
        literal_wrapper_object = match.group(2)
    later_start = literal_commit or bridge_id
    later_touches = _run_git(
        (
            "log",
            "--first-parent",
            "--format=%H",
            "--name-only",
            "--no-renames",
            f"{later_start}..{head_id}",
            "--",
            *paths,
        ),
        "post-literal-bound-history",
        repository_root,
    )
    if later_touches.strip():
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
    boundary_wrapper = boundary_blobs[_EVIDENCE_RELATIVE_PATH]
    if not _all_sentinels(_literal_values(boundary_wrapper)):
        _fail("C_pre wrapper did not retain all twelve sentinels")
    if literal_commit is None:
        if committed_wrapper != boundary_wrapper:
            _fail("candidate bridge wrapper differs from C_pre")
    else:
        if not _all_frozen_literals(_literal_values(committed_wrapper)):
            _fail("wrapper-only literal commit did not freeze all twelve literals")
        if normalize_own_source_v180r12r4(committed_wrapper) != boundary_wrapper:
            _fail("wrapper-only literal commit changed nonallowlisted bytes")
    return tree_id, bridge_id, boundary_blobs, committed_wrapper


def _verify_boundary_blobs(
    boundary_blobs: Mapping[str, bytes],
    current_blobs: Mapping[str, bytes],
) -> tuple[dict[str, Any], ...]:
    paths = SOURCE_BOUNDARY_REQUIRED_PATHS
    if set(boundary_blobs) != set(paths) or set(current_blobs) != set(paths):
        _fail("source-boundary blob set changed")
    if not _all_sentinels(_literal_values(boundary_blobs[_EVIDENCE_RELATIVE_PATH])):
        _fail("C_pre wrapper did not retain all twelve sentinels")
    facts: list[dict[str, Any]] = []
    for relative_path in paths:
        boundary = boundary_blobs[relative_path]
        current = current_blobs[relative_path]
        if relative_path == _EVIDENCE_RELATIVE_PATH:
            if normalize_own_source_v180r12r4(current) != boundary:
                _fail("current wrapper changed outside twelve allowlisted literals")
        elif current != boundary:
            _fail("ordinary source differs from the external C_pre bytes")
        facts.append(_fact_from_raw(relative_path, boundary))
    return tuple(facts)


def _replay_external_source_boundary(
    source_boundary_commit: str,
    *,
    candidate_only: bool,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    paths = SOURCE_BOUNDARY_REQUIRED_PATHS
    tree_id, bridge_id, boundary_blobs, committed_wrapper = (
        _git_source_boundary_blobs(
            source_boundary_commit,
            paths,
            _ROOT,
            candidate_only=candidate_only,
        )
    )
    current_blobs = {
        path: _read_regular_stable(_ROOT / path) for path in paths
    }
    if not candidate_only and current_blobs[_EVIDENCE_RELATIVE_PATH] != committed_wrapper:
        _fail("current wrapper differs from the wrapper-only literal commit")
    source_facts = _verify_boundary_blobs(boundary_blobs, current_blobs)
    wrapper_fact = next(
        row for row in source_facts if row["relative_path"] == _EVIDENCE_RELATIVE_PATH
    )
    authorization_fact = next(
        row
        for row in source_facts
        if row["relative_path"] == _AUTHORIZATION_RELATIVE_PATH
    )
    record = {
        "source_boundary_commit": source_boundary_commit,
        "source_boundary_tree": tree_id,
        "source_boundary_empty_bridge_commit": bridge_id,
        "source_boundary_empty_bridge_tree": tree_id,
        "source_boundary_source_fact_count": len(source_facts),
        "source_boundary_source_total_byte_count": sum(
            row["byte_count"] for row in source_facts
        ),
        "source_boundary_source_facts_sha256": _sha256(
            canonical_json_bytes(list(source_facts))
        ),
        "source_boundary_authorization_source_fact": authorization_fact,
        "source_boundary_wrapper_normalized_source_fact": wrapper_fact,
        "source_boundary_git_process_count": SOURCE_BOUNDARY_GIT_PROCESS_COUNT,
        "source_boundary_is_external_not_self_derived": True,
        "source_boundary_commit_is_strict_ancestor": True,
        "source_boundary_empty_bridge_is_immediate_child": True,
        "source_boundary_empty_bridge_preserved_entire_tree": True,
        "source_boundary_wrapper_only_allowlisted_literal_commit_required": True,
        "source_boundary_candidate_allowed_only_at_empty_bridge_head": True,
        "source_boundary_runtime_requires_committed_wrapper_literals": True,
        "source_boundary_candidate_and_runtime_payload_identity_equal": True,
        "source_boundary_post_literal_bound_source_touch_forbidden": True,
        "source_boundary_ordinary_sources_equal_current_bytes": True,
        "source_boundary_wrapper_twelve_sentinels_verified": True,
    }
    return record, source_facts


def _require_external_authorization_anchors() -> None:
    try:
        protocol_anchors = (
            protocol.require_frozen_protocol_final_anchor_set_v180r12r4()
        )
    except protocol.CampaignMeasurementProtocolV180R12R4Error as error:
        raise CampaignMeasurementAuthorizationEvidenceV180R12R4Error(
            "protocol final anchor set is not frozen before authorization evidence"
        ) from error
    if not (
        authorization.EXPECTED_PROTOCOL_ID
        == protocol_anchors["EXPECTED_PROTOCOL_ID"]
        == protocol.EXPECTED_PROTOCOL_ID
        and authorization.EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID
        == protocol_anchors[
            "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"
        ]
        == protocol.EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID
        and protocol.prelaunch_contract_v180r12r4()[
            "rule_identities_frozen"
        ]
        is True
    ):
        _fail(
            "protocol and authorization external prelaunch anchors are not "
            "frozen or equal"
        )
    identities = (
        EXPECTED_AUTHORIZATION_ID,
        EXPECTED_AUTHORIZATION_CANONICAL_SHA256,
        EXPECTED_AUTHORIZATION_SOURCE_SHA256,
        EXPECTED_SOURCE_CLOSURE_ID,
        EXPECTED_SOURCE_CLOSURE_SHA256,
    )
    integers = (
        EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT,
        EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT,
        EXPECTED_SOURCE_CLOSURE_BYTE_COUNT,
        EXPECTED_SOURCE_CLOSURE_FILE_COUNT,
    )
    authorization_sentinels = (
        authorization.EXPECTED_AUTHORIZATION_ID,
        authorization.EXPECTED_CANONICAL_SHA256,
        authorization.EXPECTED_SOURCE_CLOSURE_ID,
        authorization.EXPECTED_SOURCE_CLOSURE_SHA256,
    )
    authorization_integer_sentinels = (
        authorization.EXPECTED_CANONICAL_BYTE_COUNT,
        authorization.EXPECTED_SOURCE_CLOSURE_BYTE_COUNT,
        authorization.EXPECTED_SOURCE_CLOSURE_FILE_COUNT,
    )
    if not (
        all(_is_frozen_identity(value) for value in identities)
        and all(type(value) is int and value > 0 for value in integers)
        and all(value == ZERO_ID for value in authorization_sentinels)
        and all(value == 0 for value in authorization_integer_sentinels)
        and tuple(POST_PREREG_REDACTED_CONSTANTS)
        == tuple(authorization.AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS)
    ):
        _fail("external post-prereg authorization anchors are not frozen")


def _require_frozen_evidence_anchors() -> None:
    _require_external_authorization_anchors()
    if not (
        _is_frozen_identity(EXPECTED_AUTHORIZATION_EVIDENCE_ID)
        and _is_frozen_identity(EXPECTED_CANONICAL_SHA256)
        and type(EXPECTED_CANONICAL_BYTE_COUNT) is int
        and EXPECTED_CANONICAL_BYTE_COUNT > 0
    ):
        _fail("authorization evidence literals are not frozen")


def build_campaign_measurement_authorization_evidence_v180r12r4(
    source_boundary_commit: str,
    *,
    cgroup_parent_fact: Mapping[str, Any],
    runtime_capability_fact: Mapping[str, Any],
    candidate_only: bool,
) -> dict[str, Any]:
    """Build outcome-free evidence over an externally bounded auth candidate."""

    if type(candidate_only) is not bool:
        raise TypeError("candidate_only must be an explicit bool")
    _require_external_authorization_anchors()
    source_boundary, source_facts = _replay_external_source_boundary(
        source_boundary_commit,
        candidate_only=candidate_only,
    )
    frozen = authorization.freeze_campaign_measurement_execution_authorization_v180r12r4(
        cgroup_parent_fact=cgroup_parent_fact,
        runtime_capability_fact=runtime_capability_fact,
        source_facts=source_facts,
    )
    document = frozen.to_document()
    raw = frozen.canonical_bytes
    closure = document.get("source_closure_candidate")
    source_contract = document.get("source_closure_contract")
    repair_lineage = (
        protocol.failed_dispatch_repair_lineage_contract_v180r12r4()
    )
    immediate_repair_lineage = (
        protocol.failed_external_replay_repair_lineage_contract_v180r12r4()
    )
    scientific_birth_repair_lineage = (
        protocol.failed_scientific_birth_repair_lineage_contract_v180r12r4()
    )
    runner_execution_envelope = (
        protocol.source_bound_runner_execution_envelope_contract_v180r12r4()
    )
    authorization_source_fact = source_boundary[
        "source_boundary_authorization_source_fact"
    ]
    if not (
        frozen.execution_authorization_id == EXPECTED_AUTHORIZATION_ID
        and document.get("campaign_measurement_protocol_id")
        == protocol.EXPECTED_PROTOCOL_ID
        and document.get("campaign_measurement_execution_slot_id")
        == protocol.EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID
        and len(raw) == EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT
        and _sha256(raw) == EXPECTED_AUTHORIZATION_CANONICAL_SHA256
        and authorization_source_fact
        == {
            "relative_path": _AUTHORIZATION_RELATIVE_PATH,
            "byte_count": EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT,
            "sha256": EXPECTED_AUTHORIZATION_SOURCE_SHA256,
        }
        and type(closure) is dict
        and closure.get("source_facts") == list(source_facts)
        and closure.get("source_fact_count") == EXPECTED_SOURCE_CLOSURE_FILE_COUNT
        and closure.get("source_total_byte_count")
        == source_boundary["source_boundary_source_total_byte_count"]
        and closure.get("required_static_roots")
        == list(SOURCE_BOUNDARY_REQUIRED_PATHS)
        and closure.get("authorization_self_normalized_by_evidence_freeze") is True
        and closure.get("source_closure_id") == EXPECTED_SOURCE_CLOSURE_ID
        and closure.get("source_closure_byte_count")
        == EXPECTED_SOURCE_CLOSURE_BYTE_COUNT
        and closure.get("source_closure_sha256") == EXPECTED_SOURCE_CLOSURE_SHA256
        and document.get("source_closure_facts_supplied") is True
        and document.get("failed_dispatch_repair_lineage") == repair_lineage
        and document.get("failed_external_replay_repair_lineage")
        == immediate_repair_lineage
        and document.get("failed_scientific_birth_repair_lineage")
        == scientific_birth_repair_lineage
        and document.get("failed_v180r12r3_identity_rerun_forbidden") is True
        and document.get("failed_v180r12r3r1_identity_rerun_forbidden") is True
        and document.get("failed_v180r12r3r2_identity_rerun_forbidden") is True
        and document.get(
            "fresh_v180r12r4_physical_paths_and_identities_required"
        )
        is True
        and document.get("repair_scope")
        == protocol.V180R12R4_REPAIR_SCOPE
        and document.get(
            "repair_changes_campaign_path_roles_event_schedule_evidence_"
            "cardinality_or_reducers"
        )
        is False
        and document.get("source_bound_runner_execution_envelope_contract")
        == runner_execution_envelope
        and document.get("prelaunch_contract", {}).get(
            "precompiled_runner_module_contract"
        )
        == runner_execution_envelope
        and repair_lineage["scientific_attempt_record_present"] is False
        and repair_lineage["campaign_actual_measurement"] is False
        and repair_lineage["measurement_cgroup_created"] is False
        and repair_lineage[
            "all_required_successor_paths_absent_at_failure_freeze"
        ]
        is True
        and repair_lineage["fresh_successor_identity_required"] is True
        and immediate_repair_lineage["scientific_attempt_record_present"] is False
        and immediate_repair_lineage["campaign_actual_measurement"] is False
        and immediate_repair_lineage["measurement_cgroup_created"] is False
        and immediate_repair_lineage[
            "all_required_successor_paths_absent_at_failure_freeze"
        ]
        is True
        and immediate_repair_lineage["fresh_successor_identity_required"] is True
        and immediate_repair_lineage["repair_scope"]
        == "AUTHORIZATION_EVIDENCE_WRAPPER_SOURCE_FACT_NORMALIZATION_ONLY"
        and scientific_birth_repair_lineage["scientific_attempt_record_present"]
        is True
        and scientific_birth_repair_lineage["scientific_occurrence_started"]
        is True
        and scientific_birth_repair_lineage[
            "durable_scientific_event_prefix_present"
        ]
        is True
        and scientific_birth_repair_lineage["campaign_counter_records_issued"]
        is False
        and scientific_birth_repair_lineage["successful_ledger_claimed"] is False
        and scientific_birth_repair_lineage[
            "producer_free_verification_attempted"
        ]
        is False
        and scientific_birth_repair_lineage["fresh_successor_identity_required"]
        is True
        and scientific_birth_repair_lineage["repair_scope"]
        == protocol.V180R12R4_REPAIR_SCOPE
        and source_contract == protocol.source_closure_contract_v180r12r4()
        and source_contract.get("required_static_roots")
        == list(SOURCE_BOUNDARY_REQUIRED_PATHS)
        and source_contract.get("authorization_self_source_excluded_from_initial_fixed_point")
        is True
        and source_contract.get("authorization_self_source_bound_by_post_prereg_evidence_freeze")
        is True
        and source_contract.get("normalized_wrapper_literal_freeze_required") is True
        and document.get("source_closure_identity_frozen") is False
        and document.get("source_closure_placeholder_only") is True
        and document.get("authorization_self_source_bound_by_post_prereg_freeze")
        is False
        and document.get("identity_literals_frozen") is False
        and document.get("execution_authorization_effective") is False
        and document.get("zero_sentinel_draft_is_executable_authorization") is False
        and document.get(
            "execution_forbidden_until_all_protocol_authorization_source_closure_"
            "prelaunch_rule_and_evidence_identities_are_frozen"
        )
        is True
        and document.get("authorization_evidence_freeze_required_before_execution")
        is True
        and document.get("source_bound_prelaunch_required_before_real_outcome_execution")
        is True
        and document.get("campaign_measurement_authorization_issued") is False
        and document.get("campaign_measurement_execution_started") is False
        and document.get("campaign_measurement_execution_count") == 0
        and document.get("V180R12R2_COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and document.get("SCALAR_CALIBRATION_GATE") == "NOT_RUN"
        and document.get("BREAK_EVEN_GATE") == "NOT_RUN"
        and document.get("OFFICIAL_EXECUTION_GATE") == "NOT_RUN"
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and document.get("official_execution_allowed") is False
        and document.get("outcome_free") is True
    ):
        _fail("authorization candidate or external source anchor changed")
    payload = {
        "schema": "acfqp.campaign_measurement_authorization_evidence.v180r12r4",
        "authorization_evidence_domain": (
            domains.CONSTRUCTION_K7_AUTHORIZATION_EVIDENCE_V180R12R4_DOMAIN
        ),
        "execution_authorization_id": frozen.execution_authorization_id,
        "campaign_measurement_protocol_id": document[
            "campaign_measurement_protocol_id"
        ],
        "campaign_measurement_execution_slot_id": document[
            "campaign_measurement_execution_slot_id"
        ],
        "authorization_canonical_byte_count": len(raw),
        "authorization_canonical_sha256": _sha256(raw),
        "authorization_source_fact": authorization_source_fact,
        "source_closure_id": closure["source_closure_id"],
        "source_closure_byte_count": closure["source_closure_byte_count"],
        "source_closure_sha256": closure["source_closure_sha256"],
        "source_closure_file_count": closure["source_fact_count"],
        "authorization_evidence_wrapper_normalized_source_fact": source_boundary[
            "source_boundary_wrapper_normalized_source_fact"
        ],
        "prelaunch_contract": document["prelaunch_contract"],
        "failed_dispatch_repair_lineage": repair_lineage,
        "failed_external_replay_repair_lineage": immediate_repair_lineage,
        "failed_scientific_birth_repair_lineage": (
            scientific_birth_repair_lineage
        ),
        "failed_v180r12r3_identity_rerun_forbidden": True,
        "failed_v180r12r3r1_identity_rerun_forbidden": True,
        "failed_v180r12r3r2_identity_rerun_forbidden": True,
        "fresh_v180r12r4_physical_paths_and_identities_required": True,
        "repair_scope": protocol.V180R12R4_REPAIR_SCOPE,
        "repair_changes_campaign_path_roles_event_schedule_evidence_"
        "cardinality_or_reducers": False,
        "source_bound_runner_execution_envelope_contract": (
            runner_execution_envelope
        ),
        "cgroup_parent_fact": document["cgroup_parent_fact"],
        "runtime_capability_fact": document["runtime_capability_fact"],
        **source_boundary,
        "source_fact_exclusions": list(SOURCE_FACT_EXCLUSIONS),
        "authorization_source_excluded_from_self_derived_fixed_point": True,
        "authorization_source_included_only_as_external_c_pre_fact": True,
        "authorization_module_self_identity_literals_remain_zero": True,
        "authorization_module_source_closure_literals_remain_zero": True,
        "authorization_candidate_identity_bound_only_by_external_evidence": True,
        "authorization_self_bootstrap_forbidden": True,
        "authorization_source_must_equal_external_c_pre_bytes": True,
        "authorization_evidence_wrapper_nonliteral_bytes_bound_at_c_pre": True,
        "authorization_evidence_wrapper_allowlisted_literals_semantically_locked": True,
        "identity_cycle_avoidance_rule": (
            "EXTERNAL_C_PRE_BINDS_AUTHORIZATION_AND_ZERO_SENTINEL_WRAPPER_"
            "EMPTY_BRIDGE_PRESERVES_TREE_WRAPPER_ONLY_COMMIT_FREEZES_TWELVE_"
            "ALLOWLISTED_LITERALS"
        ),
        "preauthorization_source_boundary_git_process_count": (
            SOURCE_BOUNDARY_GIT_PROCESS_COUNT
        ),
        "preauthorization_git_processes_are_campaign_actual_measurement": False,
        "authorization_evidence_makes_execution_effective": False,
        "source_bound_prelaunch_still_required_before_any_real_outcome": True,
        "v180r12r4_outcome_bytes_accessed": False,
        "campaign_measurement_execution_count": 0,
        "V180R12R2_COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "outcome_free": True,
    }
    return {
        **payload,
        "authorization_evidence_id": domains.extension_content_id_v180r12r4(
            domains.CONSTRUCTION_K7_AUTHORIZATION_EVIDENCE_V180R12R4_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CampaignMeasurementAuthorizationEvidenceV180R12R4:
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
            == domains.extension_content_id_v180r12r4(
                domains.CONSTRUCTION_K7_AUTHORIZATION_EVIDENCE_V180R12R4_DOMAIN,
                payload,
            )
        ):
            _fail("V180r12r4 authorization evidence is foreign or noncanonical")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document

    def __reduce__(self) -> NoReturn:
        raise TypeError("V180r12r4 authorization evidence is not picklable")


def freeze_campaign_measurement_authorization_evidence_v180r12r4(
    source_boundary_commit: str,
    *,
    cgroup_parent_fact: Mapping[str, Any],
    runtime_capability_fact: Mapping[str, Any],
) -> CampaignMeasurementAuthorizationEvidenceV180R12R4:
    _require_frozen_evidence_anchors()
    document = build_campaign_measurement_authorization_evidence_v180r12r4(
        source_boundary_commit,
        cgroup_parent_fact=cgroup_parent_fact,
        runtime_capability_fact=runtime_capability_fact,
        candidate_only=False,
    )
    raw = canonical_json_bytes(document)
    if not (
        document["authorization_evidence_id"] == EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and _sha256(raw) == EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V180r12r4 authorization evidence identity changed")
    return CampaignMeasurementAuthorizationEvidenceV180R12R4(
        _ISSUER,
        raw,
        document["authorization_evidence_id"],
    )


__all__ = (
    "CampaignMeasurementAuthorizationEvidenceV180R12R4",
    "CampaignMeasurementAuthorizationEvidenceV180R12R4Error",
    "EXECUTION_CHAIN_RELATIVE_PATHS",
    "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT",
    "EXPECTED_SOURCE_CLOSURE_FILE_COUNT",
    "EXPECTED_SOURCE_CLOSURE_ID",
    "EXPECTED_SOURCE_CLOSURE_SHA256",
    "POST_PREREG_REDACTED_CONSTANTS",
    "SOURCE_BOUNDARY_GIT_PROCESS_COUNT",
    "SOURCE_BOUNDARY_REQUIRED_PATHS",
    "SOURCE_FACT_EXCLUSIONS",
    "ZERO_ID",
    "build_campaign_measurement_authorization_evidence_v180r12r4",
    "freeze_campaign_measurement_authorization_evidence_v180r12r4",
    "normalize_own_source_v180r12r4",
)
