"""Construction-only source/code provenance closure for V0-075.

Contract 1.83 starts with the exact five-input contract-1.82 replay.  Only
after that replay succeeds does it inspect local Git, construct a multi-root
source closure containing every tracked ACFQP Python candidate, compare the
occurrence's older public-replay manifest as an exact subset, bind the
registered Python/dependency lock, and perform a no-target isolated compile
check over one deterministic sealed archive without executing tested code.

The resulting two provenance lanes are deliberately local construction
evidence.  They are not a final manifest, a remote-main anchor, an OS remote
attestation, a production source authority, or evidence that a future target
worker loaded these bytes.  No observer, target tape, kernel, planner worker,
or fresh-heldout API is available here.
"""

from __future__ import annotations

import ast
from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import _v075_construction_source_runtime_v2 as source_runtime
from acfqp import v075_portable_semantic_terminal_closure_v2 as terminal


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.83.0"
PROFILE_KEY = "v075_construction_source_code_provenance_v2"
UPSTREAM_PROFILE_KEY = "v075_portable_semantic_terminal_closure_v2"

UPSTREAM_ROOT_MODULE = (
    "acfqp.v075_portable_semantic_terminal_closure_v2"
)
AUTHORITY_ROOT_MODULE = (
    "acfqp.v075_construction_source_code_provenance_v2"
)
INDEPENDENT_VERIFIER_ROOT_MODULE = (
    "acfqp.v075_construction_source_code_provenance_"
    "independent_verifier_v2"
)
ROOT_MODULES = tuple(
    sorted(
        (
            UPSTREAM_ROOT_MODULE,
            AUTHORITY_ROOT_MODULE,
            INDEPENDENT_VERIFIER_ROOT_MODULE,
        )
    )
)

REGISTERED_LOCAL_BRANCH_REF = "refs/heads/main"
REGISTERED_INTERPRETER = "/usr/bin/python3"
REGISTERED_GIT_EXECUTABLE = "/usr/bin/git"
DEPENDENCY_LOCK_PATH = "specs/V075_DEPENDENCY_LOCK.json"
PYPROJECT_PATH = "pyproject.toml"
SOURCE_PACKAGE_PATH = "src/acfqp"
EXPECTED_OCCURRENCE_SOURCE_ENTRY_COUNT = 64
MAX_SOURCE_MODULES = 512
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_DAG_NODES = 32

CONSTRUCTION_SOURCE_ARCHIVE_REPLAY_COMPLETE = True
CONSTRUCTION_LOCAL_GIT_CODE_CLOSURE_COMPLETE = True
CONSTRUCTION_ALL_TRACKED_ACFQP_SOURCE_CANDIDATES_COMPLETE = True
CONSTRUCTION_SEALED_SOURCE_COMPILE_MANIFEST_COMPLETE = True
CONSTRUCTION_LOADED_SOURCE_MANIFEST_COMPLETE = False
CONSTRUCTION_TWO_LANE_PROVENANCE_DAG_COMPLETE = True

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
ACCOUNTING_GATE_PASSED = False
PORTABLE_SEMANTIC_REGISTRY_PRODUCTION_COMPLETE = False
OBSERVER_OPEN_ALLOWED = False
TARGET_ACCESS_ALLOWED = False
KERNEL_ACCESS_ALLOWED = False
J0_ACCESS_ALLOWED = False
PLANNER_WORKER_LAUNCH_ALLOWED = False
OPERATIONAL_REGISTRIES_ALLOWED = False
PRODUCTION_PRIVATE_INPUT_CHANNEL_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_LOCAL_SOURCE_CODE_PROVENANCE_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_LOCAL_SOURCE_ARCHIVE_COMPILE_PROVENANCE_COMPLETE_"
    "FINAL_MANIFEST_REMOTE_ANCHOR_AND_PRODUCTION_LOCKED"
)

DOMAIN_TAGS = MappingProxyType(
    {
        "git_source_entry": (
            "acfqp:v075-construction-git-source-entry:v2"
        ),
        "repository_closure": (
            "acfqp:v075-construction-local-repository-closure:v2"
        ),
        "occurrence_lane": (
            "acfqp:v075-construction-occurrence-source-lane:v2"
        ),
        "semantic_lane": (
            "acfqp:v075-construction-semantic-code-lane:v2"
        ),
        "dependency_lock_binding": (
            "acfqp:v075-construction-dependency-lock-binding:v2"
        ),
        "archive_binding": (
            "acfqp:v075-construction-source-archive-binding:v2"
        ),
        "dag_node": (
            "acfqp:v075-construction-source-provenance-dag-node:v2"
        ),
        "dag": "acfqp:v075-construction-source-provenance-dag:v2",
        "closure": (
            "acfqp:v075-construction-source-code-provenance-closure:v2"
        ),
    }
)

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("contract 1.83 content domains overlap")

_REPLAY_MISMATCH = (
    "construction source/code provenance did not match registered evidence"
)
_GIT_ENVIRONMENT = MappingProxyType(
    {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": "/nonexistent",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
        "TZ": "UTC",
        "XDG_CONFIG_HOME": "/nonexistent",
    }
)


class V075ConstructionSourceCodeProvenanceV2InvariantViolation(ValueError):
    """Raw replay, Git, source, archive, runtime, or DAG replay failed."""


class V075ConstructionSourceCodeProvenanceProductionV2NotReady(
    RuntimeError
):
    """The local construction provenance cannot authorize production."""


class V075ConstructionProvenanceLaneV2(str, Enum):
    OCCURRENCE_BUNDLE_SOURCE = "OCCURRENCE_BUNDLE_SOURCE"
    SEMANTIC_REPLAY_CODE = "SEMANTIC_REPLAY_CODE"


def _fail(message: str) -> NoReturn:
    raise V075ConstructionSourceCodeProvenanceV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ConstructionSourceCodeProvenanceV2InvariantViolation(
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
        raise V075ConstructionSourceCodeProvenanceV2InvariantViolation(
            str(error)
        ) from error


def _strict_document(
    raw: bytes,
    *,
    label: str,
    byte_cap: int,
    require_canonical: bool = True,
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
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionSourceCodeProvenanceV2InvariantViolation(
            f"{label} is not strict UTF-8 JSON"
        ) from error
    if (
        type(value) is not dict
        or (
            require_canonical
            and canonical_json_bytes(value) != raw
        )
    ):
        _fail(f"{label} is not one canonical JSON object")
    return value


def _git(root: Path, *arguments: str) -> str:
    process = subprocess.run(
        (REGISTERED_GIT_EXECUTABLE, "-C", str(root), *arguments),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
        cwd="/",
        env=dict(_GIT_ENVIRONMENT),
    )
    if process.returncode:
        _fail(
            "Git inspection failed: "
            + process.stderr.decode(
                "utf-8", errors="replace"
            ).strip()
        )
    return process.stdout.decode("utf-8").strip()


def _git_blob(root: Path, object_id: str) -> bytes:
    process = subprocess.run(
        (
            REGISTERED_GIT_EXECUTABLE,
            "-C",
            str(root),
            "cat-file",
            "blob",
            object_id,
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
        cwd="/",
        env=dict(_GIT_ENVIRONMENT),
    )
    if process.returncode:
        _fail("registered Git blob cannot be read")
    return process.stdout


def _safe_relative(value: str) -> str:
    if (
        type(value) is not str
        or not value
        or "\\" in value
        or "\x00" in value
    ):
        _fail("source path is malformed")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        _fail("source path is unsafe or noncanonical")
    return value


def _regular_no_symlink(root: Path, relative: str) -> Path:
    relative = _safe_relative(relative)
    cursor = root
    for part in PurePosixPath(relative).parts:
        cursor = cursor / part
        try:
            metadata = cursor.lstat()
        except OSError as error:
            raise V075ConstructionSourceCodeProvenanceV2InvariantViolation(
                "source path is absent"
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            _fail("source path contains a symlink")
    try:
        resolved = cursor.resolve(strict=True)
        repository = root.resolve(strict=True)
    except OSError as error:
        raise V075ConstructionSourceCodeProvenanceV2InvariantViolation(
            "source path cannot be resolved"
        ) from error
    if (
        not resolved.is_relative_to(repository)
        or not stat.S_ISREG(resolved.stat().st_mode)
    ):
        _fail("source path is not one in-repository regular file")
    return resolved


def _read_regular_bytes_now(
    path: Path,
    *,
    byte_cap: int,
    label: str,
) -> bytes:
    """Read one already-resolved regular file without following a replacement."""

    try:
        fd = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as error:
        raise V075ConstructionSourceCodeProvenanceV2InvariantViolation(
            f"{label} could not be opened as a regular nonsymlink file"
        ) from error
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            _fail(f"{label} is not a regular file")
        chunks: list[bytes] = []
        remaining = byte_cap + 1
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        try:
            path_now = path.lstat()
        except OSError as error:
            raise V075ConstructionSourceCodeProvenanceV2InvariantViolation(
                f"{label} disappeared while it was read"
            ) from error
        if (
            not raw
            or len(raw) > byte_cap
            or stat.S_ISLNK(path_now.st_mode)
            or not stat.S_ISREG(path_now.st_mode)
            or (before.st_dev, before.st_ino)
            != (after.st_dev, after.st_ino)
            or (before.st_dev, before.st_ino)
            != (path_now.st_dev, path_now.st_ino)
            or after.st_size != len(raw)
        ):
            _fail(f"{label} changed while it was read or exceeded its cap")
        return raw
    finally:
        os.close(fd)


def _module_name(relative: str) -> str:
    prefix = "src/"
    if not relative.startswith(prefix):
        return ""
    value = relative[len(prefix) :]
    if value == "acfqp/__init__.py":
        return "acfqp"
    if value.startswith("acfqp/") and value.endswith("/__init__.py"):
        return value[: -len("/__init__.py")].replace("/", ".")
    if value.startswith("acfqp/") and value.endswith(".py"):
        return value[:-3].replace("/", ".")
    return ""


def _candidate_sources(
    repository_root: Path,
) -> tuple[dict[str, bytes], dict[str, Path], dict[str, str]]:
    package = repository_root
    for part in PurePosixPath(SOURCE_PACKAGE_PATH).parts:
        package = package / part
        try:
            metadata = package.lstat()
        except OSError as error:
            raise V075ConstructionSourceCodeProvenanceV2InvariantViolation(
                "ACFQP source package is absent"
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            _fail("ACFQP source package path contains a symlink")
    if not package.is_dir():
        _fail("ACFQP source package is absent")
    sources: dict[str, bytes] = {}
    paths: dict[str, Path] = {}
    relatives: dict[str, str] = {}
    for current, directories, filenames in os.walk(
        package,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)
        kept: list[str] = []
        for name in sorted(directories):
            candidate = current_path / name
            if candidate.is_symlink():
                _fail("ACFQP source package contains a symlink directory")
            kept.append(name)
        directories[:] = kept
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            candidate = current_path / name
            relative = candidate.relative_to(repository_root).as_posix()
            resolved = _regular_no_symlink(repository_root, relative)
            module = _module_name(relative)
            if not module or module in sources:
                _fail("ACFQP source module mapping is ambiguous")
            raw = _read_regular_bytes_now(
                resolved,
                byte_cap=source_runtime.MAX_SOURCE_BYTES_PER_MODULE,
                label="ACFQP source candidate",
            )
            sources[module] = raw
            paths[module] = resolved
            relatives[module] = relative
            if len(sources) > MAX_SOURCE_MODULES:
                _fail("ACFQP source candidate set exceeds its cap")
    if not sources or sum(map(len, sources.values())) > MAX_SOURCE_BYTES:
        _fail("ACFQP source candidate bytes are absent or exceed their cap")
    return sources, paths, relatives


def _parse_stage_line(
    line: str,
    *,
    relative: str,
    label: str,
) -> tuple[str, str]:
    if "\t" not in line:
        _fail(f"{label} Git record is malformed")
    prefix, path = line.split("\t", 1)
    fields = prefix.split()
    if (
        path != relative
        or len(fields) != 3
        or fields[2] != "0"
        or fields[0] not in {"100644", "100755"}
    ):
        _fail(f"{label} Git record is not one regular stage-zero blob")
    return fields[0], _git_oid(fields[1], f"{label} blob")


def _tracked_acfqp_python_paths(root: Path) -> tuple[str, ...]:
    lines = _git(root, "ls-files", "--", SOURCE_PACKAGE_PATH).splitlines()
    selected = tuple(
        sorted(
            _safe_relative(line)
            for line in lines
            if line.endswith(".py")
        )
    )
    if (
        not selected
        or len(selected) != len(set(selected))
        or any(_module_name(relative) == "" for relative in selected)
    ):
        _fail("tracked ACFQP Python candidate registry is malformed")
    return selected


def _tracked_blob(
    root: Path,
    *,
    relative: str,
    expected_raw: bytes,
) -> tuple[str, str]:
    stage = _git(root, "ls-files", "--stage", "--", relative).splitlines()
    if len(stage) != 1:
        _fail("source path lacks one stage-zero Git index entry")
    mode, index_blob = _parse_stage_line(
        stage[0],
        relative=relative,
        label="index source",
    )
    tree = _git(root, "ls-tree", "HEAD", "--", relative).splitlines()
    if len(tree) != 1:
        _fail("source path is absent from HEAD")
    if "\t" not in tree[0]:
        _fail("HEAD source record is malformed")
    prefix, tree_path = tree[0].split("\t", 1)
    fields = prefix.split()
    if (
        tree_path != relative
        or len(fields) != 3
        or fields[1] != "blob"
        or fields[0] != mode
    ):
        _fail("HEAD source record changed type, mode, or path")
    head_blob = _git_oid(fields[2], "HEAD source blob")
    live_path = _regular_no_symlink(root, relative)
    live_raw = _read_regular_bytes_now(
        live_path,
        byte_cap=MAX_SOURCE_BYTES,
        label="live tracked source",
    )
    if (
        head_blob != index_blob
        or _git_blob(root, index_blob) != expected_raw
        or live_raw != expected_raw
    ):
        _fail("source worktree, index, and HEAD bytes differ")
    return mode, index_blob


@dataclass(frozen=True, slots=True)
class V075ConstructionGitSourceEntryV2:
    module_name: str
    relative_path: str
    git_mode: str
    git_blob_id: str
    source_sha256: str
    source_byte_count: int
    runtime_source_entry_id: str
    _entry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _git_oid(self.git_blob_id, "source entry Git blob")
        _cid(self.source_sha256, "source entry bytes")
        _cid(self.runtime_source_entry_id, "runtime source entry")
        if (
            type(self.module_name) is not str
            or (
                self.module_name != "acfqp"
                and not self.module_name.startswith("acfqp.")
            )
            or _module_name(self.relative_path) != self.module_name
            or self.git_mode not in {"100644", "100755"}
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
        ):
            _fail("Git source entry is malformed")
        object.__setattr__(
            self,
            "_entry_id",
            _hash("git_source_entry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_construction_git_source_entry.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "module_name": self.module_name,
            "relative_path": self.relative_path,
            "git_mode": self.git_mode,
            "git_blob_id": self.git_blob_id,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
            "runtime_source_entry_id": self.runtime_source_entry_id,
            "regular_file": True,
            "symlink": False,
            "worktree_equals_index_blob": True,
            "index_blob_equals_head_blob": True,
        }

    @property
    def entry_id(self) -> str:
        return self._entry_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


@dataclass(frozen=True, slots=True)
class V075ConstructionLocalRepositoryClosureV2:
    head_commit_id: str
    head_tree_id: str
    local_branch_ref: str
    git_executable: str
    git_executable_sha256: str
    git_executable_byte_count: int
    root_modules: tuple[str, ...]
    runtime_source_closure_id: str
    entries: tuple[V075ConstructionGitSourceEntryV2, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _git_oid(self.head_commit_id, "local repository HEAD")
        _git_oid(self.head_tree_id, "local repository tree")
        _cid(self.git_executable_sha256, "registered Git executable")
        _cid(self.runtime_source_closure_id, "runtime source closure")
        if (
            self.local_branch_ref != REGISTERED_LOCAL_BRANCH_REF
            or self.git_executable != REGISTERED_GIT_EXECUTABLE
            or type(self.git_executable_byte_count) is not int
            or self.git_executable_byte_count <= 0
            or self.root_modules != ROOT_MODULES
            or type(self.entries) is not tuple
            or not self.entries
            or tuple(item.module_name for item in self.entries)
            != tuple(sorted(item.module_name for item in self.entries))
            or len({item.module_name for item in self.entries})
            != len(self.entries)
            or any(
                type(item) is not V075ConstructionGitSourceEntryV2
                for item in self.entries
            )
            or not set(ROOT_MODULES).issubset(
                {item.module_name for item in self.entries}
            )
        ):
            _fail("local repository source closure is malformed")
        object.__setattr__(
            self,
            "_closure_id",
            _hash("repository_closure", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_local_repository_closure.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "head_commit_id": self.head_commit_id,
            "head_tree_id": self.head_tree_id,
            "local_branch_ref": self.local_branch_ref,
            "git_executable": self.git_executable,
            "git_executable_sha256": self.git_executable_sha256,
            "git_executable_byte_count": self.git_executable_byte_count,
            "root_modules": list(self.root_modules),
            "runtime_source_closure_id": self.runtime_source_closure_id,
            "entry_ids": [item.entry_id for item in self.entries],
            "entry_count": len(self.entries),
            "head_equals_local_main": True,
            "all_entries_regular": True,
            "all_entries_no_symlink": True,
            "all_entries_worktree_index_head_equal": True,
            "all_tracked_acfqp_python_candidates_included": True,
            "runtime_closure_roots_are_all_tracked_candidates": True,
            "registered_semantic_roots_remain_explicit_metadata": True,
            "git_environment_sanitized": True,
            "origin_main_required": False,
            "remote_anchor_claimed": False,
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "entries": [item.to_document() for item in self.entries],
            "closure_id": self.closure_id,
        }


@dataclass(frozen=True, slots=True)
class V075ConstructionOccurrenceSourceLaneV2:
    source_manifest_id: str
    source_manifest_sha256: str
    source_manifest_byte_count: int
    repository_closure_id: str
    entry_bindings: tuple[tuple[str, str], ...]
    _lane_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_manifest_id, "occurrence source manifest"),
            (self.source_manifest_sha256, "occurrence source bytes"),
            (self.repository_closure_id, "occurrence repository closure"),
        ):
            _cid(value, label)
        if (
            type(self.source_manifest_byte_count) is not int
            or self.source_manifest_byte_count <= 0
            or type(self.entry_bindings) is not tuple
            or len(self.entry_bindings)
            != EXPECTED_OCCURRENCE_SOURCE_ENTRY_COUNT
            or tuple(name for name, _entry_id in self.entry_bindings)
            != tuple(sorted(name for name, _entry_id in self.entry_bindings))
            or len({name for name, _entry_id in self.entry_bindings})
            != len(self.entry_bindings)
        ):
            _fail("occurrence source provenance lane is malformed")
        for name, entry_id in self.entry_bindings:
            if (
                type(name) is not str
                or (
                    name != "acfqp"
                    and not name.startswith("acfqp.")
                )
            ):
                _fail("occurrence source lane module is malformed")
            _cid(entry_id, "occurrence source lane entry")
        object.__setattr__(
            self,
            "_lane_id",
            _hash("occurrence_lane", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_occurrence_source_lane.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "lane": (
                V075ConstructionProvenanceLaneV2
                .OCCURRENCE_BUNDLE_SOURCE.value
            ),
            "source_manifest_id": self.source_manifest_id,
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_manifest_byte_count": self.source_manifest_byte_count,
            "repository_closure_id": self.repository_closure_id,
            "entry_bindings": [
                {"module_name": name, "git_source_entry_id": entry_id}
                for name, entry_id in self.entry_bindings
            ],
            "entry_count": len(self.entry_bindings),
            "raw_manifest_exact_subset": True,
            "manifest_authority_upgraded": False,
        }

    @property
    def lane_id(self) -> str:
        return self._lane_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "lane_id": self.lane_id}


@dataclass(frozen=True, slots=True)
class V075ConstructionSemanticCodeLaneV2:
    repository_closure_id: str
    runtime_source_closure_id: str
    root_modules: tuple[str, ...]
    entry_ids: tuple[str, ...]
    occurrence_shared_entry_ids: tuple[str, ...]
    semantic_only_entry_ids: tuple[str, ...]
    _lane_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.repository_closure_id, "semantic repository closure")
        _cid(self.runtime_source_closure_id, "semantic runtime closure")
        for value in (
            *self.entry_ids,
            *self.occurrence_shared_entry_ids,
            *self.semantic_only_entry_ids,
        ):
            _cid(value, "semantic code lane entry")
        if (
            self.root_modules != ROOT_MODULES
            or type(self.entry_ids) is not tuple
            or not self.entry_ids
            or len(set(self.entry_ids)) != len(self.entry_ids)
            or tuple(
                sorted(
                    (
                        *self.occurrence_shared_entry_ids,
                        *self.semantic_only_entry_ids,
                    )
                )
            )
            != tuple(sorted(self.entry_ids))
            or set(self.occurrence_shared_entry_ids).intersection(
                self.semantic_only_entry_ids
            )
        ):
            _fail("semantic replay code lane is malformed")
        object.__setattr__(
            self,
            "_lane_id",
            _hash("semantic_lane", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_construction_semantic_code_lane.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "lane": (
                V075ConstructionProvenanceLaneV2
                .SEMANTIC_REPLAY_CODE.value
            ),
            "repository_closure_id": self.repository_closure_id,
            "runtime_source_closure_id": self.runtime_source_closure_id,
            "root_modules": list(self.root_modules),
            "entry_ids": list(self.entry_ids),
            "occurrence_shared_entry_ids": list(
                self.occurrence_shared_entry_ids
            ),
            "semantic_only_entry_ids": list(
                self.semantic_only_entry_ids
            ),
            "entry_count": len(self.entry_ids),
            "occurrence_shared_entry_count": len(
                self.occurrence_shared_entry_ids
            ),
            "semantic_only_entry_count": len(
                self.semantic_only_entry_ids
            ),
            "static_multi_root_closure_exact": True,
            "production_manifest_binding": {
                "kind": "NOT_YET_APPLICABLE",
                "reason": "FINAL_MANIFEST_AND_REMOTE_ANCHOR_NOT_FROZEN",
            },
        }

    @property
    def lane_id(self) -> str:
        return self._lane_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "lane_id": self.lane_id}


@dataclass(frozen=True, slots=True)
class V075ConstructionDependencyLockBindingV2:
    repository_path: str
    git_blob_id: str
    raw_sha256: str
    raw_byte_count: int
    pyproject_path: str
    pyproject_git_blob_id: str
    pyproject_sha256: str
    pyproject_byte_count: int
    registered_runtime_dependency_lock_id: str
    captured_runtime_lock_id: str
    interpreter_path: str
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _git_oid(self.git_blob_id, "dependency-lock Git blob")
        _git_oid(self.pyproject_git_blob_id, "pyproject Git blob")
        for value, label in (
            (self.raw_sha256, "dependency-lock bytes"),
            (self.pyproject_sha256, "pyproject bytes"),
            (
                self.registered_runtime_dependency_lock_id,
                "registered runtime dependency lock",
            ),
            (self.captured_runtime_lock_id, "captured runtime lock"),
        ):
            _cid(value, label)
        if (
            self.repository_path != DEPENDENCY_LOCK_PATH
            or self.pyproject_path != PYPROJECT_PATH
            or type(self.raw_byte_count) is not int
            or self.raw_byte_count <= 0
            or type(self.pyproject_byte_count) is not int
            or self.pyproject_byte_count <= 0
            or self.interpreter_path != REGISTERED_INTERPRETER
        ):
            _fail("dependency lock binding is malformed")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("dependency_lock_binding", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_dependency_lock_binding.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "repository_path": self.repository_path,
            "git_blob_id": self.git_blob_id,
            "raw_sha256": self.raw_sha256,
            "raw_byte_count": self.raw_byte_count,
            "pyproject_path": self.pyproject_path,
            "pyproject_git_blob_id": self.pyproject_git_blob_id,
            "pyproject_sha256": self.pyproject_sha256,
            "pyproject_byte_count": self.pyproject_byte_count,
            "registered_runtime_dependency_lock_id": (
                self.registered_runtime_dependency_lock_id
            ),
            "captured_runtime_lock_id": self.captured_runtime_lock_id,
            "interpreter_path": self.interpreter_path,
            "worktree_index_head_equal": True,
            "registered_lock_semantically_replayed": True,
            "production_dependency_lock_promoted": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class V075ConstructionSourceArchiveBindingV2:
    runtime_source_closure_id: str
    dependency_lock_binding_id: str
    source_archive_id: str
    archive_sha256: str
    archive_byte_count: int
    compile_verification_id: str
    compile_child_result_sha256: str
    runtime_lock_id: str
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.runtime_source_closure_id, "archive source closure"),
            (
                self.dependency_lock_binding_id,
                "archive dependency lock",
            ),
            (self.source_archive_id, "typed source archive"),
            (self.archive_sha256, "archive bytes"),
            (self.compile_verification_id, "sealed-source compile verification"),
            (
                self.compile_child_result_sha256,
                "sealed-source compile child result",
            ),
            (self.runtime_lock_id, "archive runtime lock"),
        ):
            _cid(value, label)
        if (
            type(self.archive_byte_count) is not int
            or not 0 < self.archive_byte_count <= MAX_ARCHIVE_BYTES
        ):
            _fail("source archive binding is malformed")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("archive_binding", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_construction_source_archive_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "runtime_source_closure_id": self.runtime_source_closure_id,
            "dependency_lock_binding_id": self.dependency_lock_binding_id,
            "source_archive_id": self.source_archive_id,
            "archive_sha256": self.archive_sha256,
            "archive_byte_count": self.archive_byte_count,
            "archive_format": "DETERMINISTIC_ZIP_STORED_V2",
            "compile_verification_id": self.compile_verification_id,
            "compile_child_result_sha256": (
                self.compile_child_result_sha256
            ),
            "runtime_lock_id": self.runtime_lock_id,
            "archive_verified_before_child": True,
            "archive_verified_after_child": True,
            "isolated_exact_archive_member_compile": True,
            "tested_source_executed": False,
            "loaded_source_manifest_claimed": False,
            "live_source_fallback_used": False,
            "target_accessed": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class V075ConstructionSourceProvenanceDAGNodeV2:
    index: int
    role: str
    artifact_id: str
    dependency_node_ids: tuple[str, ...]
    _node_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.artifact_id, "provenance DAG artifact")
        for value in self.dependency_node_ids:
            _cid(value, "provenance DAG dependency")
        if (
            type(self.index) is not int
            or self.index < 0
            or type(self.role) is not str
            or not self.role
            or type(self.dependency_node_ids) is not tuple
            or self.dependency_node_ids
            != tuple(sorted(self.dependency_node_ids))
            or len(set(self.dependency_node_ids))
            != len(self.dependency_node_ids)
        ):
            _fail("provenance DAG node is malformed")
        object.__setattr__(
            self,
            "_node_id",
            _hash("dag_node", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_source_provenance_dag_node.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "index": self.index,
            "role": self.role,
            "artifact_id": self.artifact_id,
            "dependency_node_ids": list(self.dependency_node_ids),
        }

    @property
    def node_id(self) -> str:
        return self._node_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "node_id": self.node_id}


@dataclass(frozen=True, slots=True)
class V075ConstructionSourceProvenanceDAGV2:
    nodes: tuple[V075ConstructionSourceProvenanceDAGNodeV2, ...]
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.nodes) is not tuple
            or not self.nodes
            or len(self.nodes) > MAX_DAG_NODES
            or tuple(item.index for item in self.nodes)
            != tuple(range(len(self.nodes)))
            or len({item.node_id for item in self.nodes})
            != len(self.nodes)
            or len({item.role for item in self.nodes}) != len(self.nodes)
        ):
            _fail("source provenance DAG is malformed")
        prior: set[str] = set()
        for node in self.nodes:
            if not set(node.dependency_node_ids) <= prior:
                _fail("source provenance DAG is cyclic or non-topological")
            prior.add(node.node_id)
        object.__setattr__(self, "_dag_id", _hash("dag", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_construction_source_provenance_dag.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "node_ids": [item.node_id for item in self.nodes],
            "node_count": len(self.nodes),
            "topological_order_verified": True,
            "two_provenance_lanes_preserved": True,
        }

    @property
    def dag_id(self) -> str:
        return self._dag_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "nodes": [item.to_document() for item in self.nodes],
            "dag_id": self.dag_id,
        }


_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionSourceCodeProvenanceClosureV2:
    _issuer: InitVar[object]
    semantic_terminal_closure_id: str
    portable_bundle_id: str
    portable_bundle_sha256: str
    occurrence_id: str
    public_context_closure_id: str
    repository_closure: V075ConstructionLocalRepositoryClosureV2
    occurrence_source_lane: V075ConstructionOccurrenceSourceLaneV2
    semantic_code_lane: V075ConstructionSemanticCodeLaneV2
    dependency_lock_binding: V075ConstructionDependencyLockBindingV2
    archive_binding: V075ConstructionSourceArchiveBindingV2
    runtime_source_closure_document: Mapping[str, Any] = field(repr=False)
    runtime_lock_document: Mapping[str, Any] = field(repr=False)
    compile_verification_document: Mapping[str, Any] = field(repr=False)
    provenance_dag: V075ConstructionSourceProvenanceDAGV2
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (
                self.semantic_terminal_closure_id,
                "source provenance semantic terminal",
            ),
            (self.portable_bundle_id, "source provenance bundle"),
            (self.portable_bundle_sha256, "source provenance bundle bytes"),
            (self.occurrence_id, "source provenance occurrence"),
            (self.public_context_closure_id, "source provenance context"),
        ):
            _cid(value, label)
        if (
            _issuer is not _CLOSURE_ISSUER
            or type(self.repository_closure)
            is not V075ConstructionLocalRepositoryClosureV2
            or type(self.occurrence_source_lane)
            is not V075ConstructionOccurrenceSourceLaneV2
            or type(self.semantic_code_lane)
            is not V075ConstructionSemanticCodeLaneV2
            or type(self.dependency_lock_binding)
            is not V075ConstructionDependencyLockBindingV2
            or type(self.archive_binding)
            is not V075ConstructionSourceArchiveBindingV2
            or type(self.runtime_source_closure_document) is not dict
            or type(self.runtime_lock_document) is not dict
            or type(self.compile_verification_document) is not dict
            or type(self.provenance_dag)
            is not V075ConstructionSourceProvenanceDAGV2
            or self.occurrence_source_lane.repository_closure_id
            != self.repository_closure.closure_id
            or self.semantic_code_lane.repository_closure_id
            != self.repository_closure.closure_id
            or self.semantic_code_lane.runtime_source_closure_id
            != self.repository_closure.runtime_source_closure_id
            or self.archive_binding.runtime_source_closure_id
            != self.repository_closure.runtime_source_closure_id
            or self.archive_binding.dependency_lock_binding_id
            != self.dependency_lock_binding.binding_id
            or self.archive_binding.runtime_lock_id
            != self.dependency_lock_binding.captured_runtime_lock_id
        ):
            _fail("construction source/code provenance closure is malformed")
        object.__setattr__(
            self,
            "_closure_id",
            _hash("closure", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_source_code_provenance_closure.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "upstream_profile_key": UPSTREAM_PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "semantic_terminal_closure_id": (
                self.semantic_terminal_closure_id
            ),
            "portable_bundle_id": self.portable_bundle_id,
            "portable_bundle_sha256": self.portable_bundle_sha256,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "repository_closure": self.repository_closure.to_document(),
            "repository_closure_id": self.repository_closure.closure_id,
            "occurrence_source_lane": (
                self.occurrence_source_lane.to_document()
            ),
            "occurrence_source_lane_id": (
                self.occurrence_source_lane.lane_id
            ),
            "semantic_code_lane": self.semantic_code_lane.to_document(),
            "semantic_code_lane_id": self.semantic_code_lane.lane_id,
            "dependency_lock_binding": (
                self.dependency_lock_binding.to_document()
            ),
            "dependency_lock_binding_id": (
                self.dependency_lock_binding.binding_id
            ),
            "source_archive_binding": self.archive_binding.to_document(),
            "source_archive_binding_id": self.archive_binding.binding_id,
            "runtime_source_closure": dict(
                self.runtime_source_closure_document
            ),
            "runtime_lock": dict(self.runtime_lock_document),
            "sealed_source_compile_verification": dict(
                self.compile_verification_document
            ),
            "provenance_dag": self.provenance_dag.to_document(),
            "provenance_dag_id": self.provenance_dag.dag_id,
            "provenance_lane_order": [
                V075ConstructionProvenanceLaneV2
                .OCCURRENCE_BUNDLE_SOURCE.value,
                V075ConstructionProvenanceLaneV2
                .SEMANTIC_REPLAY_CODE.value,
            ],
            "raw_contract_182_replayed_first": True,
            "construction_source_archive_replay_complete": True,
            "construction_local_git_code_closure_complete": True,
            "construction_all_tracked_acfqp_source_candidates_complete": True,
            "construction_sealed_source_compile_manifest_complete": True,
            "construction_loaded_source_manifest_complete": False,
            "construction_two_lane_provenance_dag_complete": True,
            "sealed_source_compile_check_scope": (
                "NO_TARGET_ISOLATED_COMPILE_WITHOUT_TESTED_CODE_EXECUTION"
            ),
            "cryptographic_or_os_remote_attestation": False,
            "future_target_worker_loaded_code_attested": False,
            "final_manifest_binding": {
                "kind": "NOT_YET_APPLICABLE",
                "reason": "FINAL_MANIFEST_NOT_FROZEN",
            },
            "remote_main_anchor_binding": {
                "kind": "NOT_YET_APPLICABLE",
                "reason": "FIRST_QUALIFYING_REMOTE_MAIN_ANCHOR_NOT_FROZEN",
            },
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "accounting_gate_passed": False,
            "portable_semantic_registry_production_complete": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "fresh_heldout_accessed": False,
            "scientific_endpoint_credit_allowed": False,
            "observer_opened": False,
            "target_accessed": False,
            "kernel_accessed": False,
            "planner_worker_launched": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    @property
    def canonical_bytes(self) -> bytes:
        raw = canonical_json_bytes(self.to_document())
        if len(raw) > MAX_OUTPUT_BYTES:
            _fail("source/code provenance closure exceeds its byte cap")
        return raw

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}

    def assert_current(
        self,
        *,
        repository_root: str | Path,
        portable_bundle_bytes: bytes,
        public_context_closure_bytes: bytes,
        private_generation_seed: bytes,
        private_salt: bytes,
    ) -> None:
        current = replay_v075_construction_source_code_provenance_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
            private_generation_seed=private_generation_seed,
            private_salt=private_salt,
        )
        if current.to_document() != self.to_document():
            _fail("construction source/code provenance currentness changed")

    def __reduce__(self) -> NoReturn:
        raise TypeError("source/code provenance closures are in-memory-only")


def _runtime_id(value: Any, *names: str) -> str:
    for name in names:
        candidate = getattr(value, name, None)
        if type(candidate) is str:
            return _cid(candidate, f"runtime helper {name}")
    document = value.to_document()
    for name in names:
        candidate = document.get(name)
        if type(candidate) is str:
            return _cid(candidate, f"runtime helper {name}")
    _fail("runtime helper omitted a registered content identity")


def _freeze_repository_closure(
    *,
    root: Path,
    runtime_closure: source_runtime.ConstructionSourceClosureV2,
    module_sources: Mapping[str, bytes],
    module_paths: Mapping[str, Path],
    relative_paths: Mapping[str, str],
) -> V075ConstructionLocalRepositoryClosureV2:
    head = _git_oid(_git(root, "rev-parse", "HEAD"), "repository HEAD")
    local_main = _git_oid(
        _git(root, "rev-parse", REGISTERED_LOCAL_BRANCH_REF),
        "local main",
    )
    if head != local_main:
        _fail("HEAD and local main differ")
    tree = _git_oid(
        _git(root, "rev-parse", "HEAD^{tree}"),
        "repository tree",
    )
    tracked_paths = _tracked_acfqp_python_paths(root)
    if tracked_paths != tuple(sorted(relative_paths.values())):
        _fail(
            "worktree ACFQP candidates differ from the complete tracked set"
        )
    if (
        runtime_closure.module_names != tuple(sorted(module_sources))
        or runtime_closure.root_modules != tuple(sorted(module_sources))
    ):
        _fail("runtime closure does not contain every tracked ACFQP candidate")
    git_path = _regular_no_symlink(Path("/"), "usr/bin/git")
    if str(git_path) != REGISTERED_GIT_EXECUTABLE:
        _fail("registered Git executable resolved to a foreign path")
    git_raw = _read_regular_bytes_now(
        git_path,
        byte_cap=16 * 1024 * 1024,
        label="registered Git executable",
    )
    runtime_by_name = {
        item.module_name: item for item in runtime_closure.modules
    }
    entries: list[V075ConstructionGitSourceEntryV2] = []
    for name in sorted(runtime_by_name):
        raw = module_sources[name]
        relative = relative_paths[name]
        resolved = _regular_no_symlink(root, relative)
        if resolved != module_paths[name]:
            _fail("source module path changed during closure construction")
        mode, blob = _tracked_blob(
            root,
            relative=relative,
            expected_raw=raw,
        )
        runtime_entry = runtime_by_name[name]
        if (
            runtime_entry.relative_path
            != PurePosixPath(relative).relative_to("src").as_posix()
            or runtime_entry.source_sha256
            != hashlib.sha256(raw).hexdigest()
            or runtime_entry.source_byte_count != len(raw)
        ):
            _fail("runtime source closure differs from tracked source")
        entries.append(
            V075ConstructionGitSourceEntryV2(
                name,
                relative,
                mode,
                blob,
                hashlib.sha256(raw).hexdigest(),
                len(raw),
                _runtime_id(
                    runtime_entry,
                    "source_entry_id",
                    "entry_id",
                    "module_id",
                ),
            )
        )
    return V075ConstructionLocalRepositoryClosureV2(
        head,
        tree,
        REGISTERED_LOCAL_BRANCH_REF,
        REGISTERED_GIT_EXECUTABLE,
        hashlib.sha256(git_raw).hexdigest(),
        len(git_raw),
        ROOT_MODULES,
        _runtime_id(
            runtime_closure,
            "source_closure_id",
            "closure_id",
        ),
        tuple(entries),
    )


def _freeze_occurrence_lane(
    *,
    upstream: terminal.V075PortableSemanticTerminalClosureV2,
    repository: V075ConstructionLocalRepositoryClosureV2,
) -> V075ConstructionOccurrenceSourceLaneV2:
    manifest = upstream.source_manifest
    if (
        len(manifest.entries) != EXPECTED_OCCURRENCE_SOURCE_ENTRY_COUNT
        or manifest.manifest_id != upstream.source_manifest_id
    ):
        _fail("raw occurrence source manifest is not the registered 64 entries")
    by_name = {item.module_name: item for item in repository.entries}
    bindings: list[tuple[str, str]] = []
    for old in manifest.entries:
        current = by_name.get(old.module_name)
        if (
            current is None
            or current.relative_path
            != f"src/{old.relative_path}"
            or current.source_sha256 != old.source_sha256
            or current.source_byte_count != old.source_byte_count
        ):
            _fail(
                "raw occurrence source manifest is not an exact local "
                "semantic-source subset"
            )
        bindings.append((old.module_name, current.entry_id))
    raw = manifest.canonical_bytes
    return V075ConstructionOccurrenceSourceLaneV2(
        manifest.manifest_id,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
        repository.closure_id,
        tuple(bindings),
    )


def _freeze_semantic_lane(
    *,
    repository: V075ConstructionLocalRepositoryClosureV2,
    occurrence: V075ConstructionOccurrenceSourceLaneV2,
) -> V075ConstructionSemanticCodeLaneV2:
    occurrence_ids = tuple(entry_id for _name, entry_id in occurrence.entry_bindings)
    all_ids = tuple(item.entry_id for item in repository.entries)
    occurrence_set = set(occurrence_ids)
    semantic_only = tuple(
        item.entry_id
        for item in repository.entries
        if item.entry_id not in occurrence_set
    )
    if not semantic_only:
        _fail("semantic source lane failed to add contract authorities")
    return V075ConstructionSemanticCodeLaneV2(
        repository.closure_id,
        repository.runtime_source_closure_id,
        ROOT_MODULES,
        all_ids,
        occurrence_ids,
        semantic_only,
    )


def _freeze_dependency_lock(
    *,
    root: Path,
    dependency_lock_bytes: bytes,
    pyproject_bytes: bytes,
) -> tuple[
    V075ConstructionDependencyLockBindingV2,
    source_runtime.ConstructionRuntimeDependencyLockV2,
]:
    path = _regular_no_symlink(root, DEPENDENCY_LOCK_PATH)
    if _read_regular_bytes_now(
        path,
        byte_cap=4 * 1024 * 1024,
        label="dependency-lock bytes",
    ) != dependency_lock_bytes:
        _fail("dependency-lock bytes changed before runtime replay")
    document = _strict_document(
        dependency_lock_bytes,
        label="V0-075 dependency lock",
        byte_cap=4 * 1024 * 1024,
        require_canonical=False,
    )
    registered_id = _cid(
        document.get("runtime_dependency_lock_id"),
        "registered dependency lock",
    )
    mode, blob = _tracked_blob(
        root,
        relative=DEPENDENCY_LOCK_PATH,
        expected_raw=dependency_lock_bytes,
    )
    if mode not in {"100644", "100755"}:
        _fail("dependency lock is not one regular Git blob")
    pyproject_path = _regular_no_symlink(root, PYPROJECT_PATH)
    if _read_regular_bytes_now(
        pyproject_path,
        byte_cap=4 * 1024 * 1024,
        label="pyproject bytes",
    ) != pyproject_bytes:
        _fail("pyproject bytes changed before runtime replay")
    pyproject_mode, pyproject_blob = _tracked_blob(
        root,
        relative=PYPROJECT_PATH,
        expected_raw=pyproject_bytes,
    )
    if pyproject_mode not in {"100644", "100755"}:
        _fail("pyproject is not one regular Git blob")
    runtime_lock = (
        source_runtime.verify_construction_runtime_dependency_lock_v2(
            dependency_lock_bytes=dependency_lock_bytes,
            pyproject_bytes=pyproject_bytes,
        )
    )
    if (
        runtime_lock.dependency_lock_id != registered_id
        or runtime_lock.requested_executable != REGISTERED_INTERPRETER
        or runtime_lock.pyproject_sha256
        != hashlib.sha256(pyproject_bytes).hexdigest()
    ):
        _fail("runtime replay differs from the tracked dependency inputs")
    return (
        V075ConstructionDependencyLockBindingV2(
            DEPENDENCY_LOCK_PATH,
            blob,
            hashlib.sha256(dependency_lock_bytes).hexdigest(),
            len(dependency_lock_bytes),
            PYPROJECT_PATH,
            pyproject_blob,
            hashlib.sha256(pyproject_bytes).hexdigest(),
            len(pyproject_bytes),
            registered_id,
            runtime_lock.verification_id,
            REGISTERED_INTERPRETER,
        ),
        runtime_lock,
    )


def _node(
    nodes: list[V075ConstructionSourceProvenanceDAGNodeV2],
    *,
    role: str,
    artifact_id: str,
    dependencies: tuple[V075ConstructionSourceProvenanceDAGNodeV2, ...] = (),
) -> V075ConstructionSourceProvenanceDAGNodeV2:
    value = V075ConstructionSourceProvenanceDAGNodeV2(
        len(nodes),
        role,
        artifact_id,
        tuple(sorted(item.node_id for item in dependencies)),
    )
    nodes.append(value)
    return value


def _freeze_dag(
    *,
    upstream: terminal.V075PortableSemanticTerminalClosureV2,
    repository: V075ConstructionLocalRepositoryClosureV2,
    occurrence: V075ConstructionOccurrenceSourceLaneV2,
    semantic_lane: V075ConstructionSemanticCodeLaneV2,
    dependency: V075ConstructionDependencyLockBindingV2,
    archive: V075ConstructionSourceArchiveBindingV2,
) -> V075ConstructionSourceProvenanceDAGV2:
    nodes: list[V075ConstructionSourceProvenanceDAGNodeV2] = []
    raw = _node(
        nodes,
        role="RAW_182_SEMANTIC_TERMINAL_CLOSURE",
        artifact_id=upstream.terminal_closure_id,
    )
    manifest = _node(
        nodes,
        role="RAW_PUBLIC_CONTEXT_SOURCE_MANIFEST",
        artifact_id=upstream.source_manifest_id,
        dependencies=(raw,),
    )
    repository_node = _node(
        nodes,
        role="LOCAL_HEAD_INDEX_WORKTREE_SOURCE_CLOSURE",
        artifact_id=repository.closure_id,
        dependencies=(raw,),
    )
    occurrence_node = _node(
        nodes,
        role="OCCURRENCE_BUNDLE_SOURCE_LANE",
        artifact_id=occurrence.lane_id,
        dependencies=(manifest, repository_node),
    )
    semantic_node = _node(
        nodes,
        role="SEMANTIC_REPLAY_CODE_LANE",
        artifact_id=semantic_lane.lane_id,
        dependencies=(raw, occurrence_node, repository_node),
    )
    dependency_node = _node(
        nodes,
        role="TRACKED_RUNTIME_DEPENDENCY_LOCK",
        artifact_id=dependency.binding_id,
        dependencies=(repository_node,),
    )
    archive_node = _node(
        nodes,
        role="DETERMINISTIC_SEALED_SOURCE_ARCHIVE",
        artifact_id=archive.binding_id,
        dependencies=(semantic_node, dependency_node),
    )
    _node(
        nodes,
        role="NO_TARGET_ISOLATED_SEALED_SOURCE_COMPILE_VERIFICATION",
        artifact_id=archive.compile_verification_id,
        dependencies=(archive_node,),
    )
    return V075ConstructionSourceProvenanceDAGV2(tuple(nodes))


def _freeze_after_raw_182(
    *,
    repository_root: str | Path,
    upstream: terminal.V075PortableSemanticTerminalClosureV2,
    portable_bundle_bytes: bytes,
) -> V075ConstructionSourceCodeProvenanceClosureV2:
    if type(upstream) is not terminal.V075PortableSemanticTerminalClosureV2:
        _fail("source/code provenance requires exact raw contract 1.82")
    _ = upstream.terminal_closure_id
    root = Path(repository_root).resolve(strict=True)
    if not root.is_dir() or not root.joinpath(".git").exists():
        _fail("repository root is not one Git worktree")
    module_sources, module_paths, relative_paths = _candidate_sources(root)
    runtime_closure = source_runtime.build_construction_source_closure_v2(
        root_modules=tuple(sorted(module_sources)),
        module_sources=module_sources,
        module_paths=module_paths,
    )
    repository = _freeze_repository_closure(
        root=root,
        runtime_closure=runtime_closure,
        module_sources=module_sources,
        module_paths=module_paths,
        relative_paths=relative_paths,
    )
    occurrence = _freeze_occurrence_lane(
        upstream=upstream,
        repository=repository,
    )
    semantic_lane = _freeze_semantic_lane(
        repository=repository,
        occurrence=occurrence,
    )
    dependency_lock_bytes = _read_regular_bytes_now(
        _regular_no_symlink(root, DEPENDENCY_LOCK_PATH),
        byte_cap=4 * 1024 * 1024,
        label="dependency-lock capture",
    )
    pyproject_bytes = _read_regular_bytes_now(
        _regular_no_symlink(root, PYPROJECT_PATH),
        byte_cap=4 * 1024 * 1024,
        label="pyproject capture",
    )
    dependency, runtime_lock = _freeze_dependency_lock(
        root=root,
        dependency_lock_bytes=dependency_lock_bytes,
        pyproject_bytes=pyproject_bytes,
    )
    source_archive = source_runtime.build_deterministic_source_archive_v2(
        closure=runtime_closure,
        module_sources=module_sources,
    )
    if (
        type(source_archive)
        is not source_runtime.ConstructionSourceArchiveV2
        or not source_archive.archive_bytes
        or source_archive.archive_byte_count > MAX_ARCHIVE_BYTES
        or source_archive.source_closure_id != runtime_closure.closure_id
    ):
        _fail("deterministic source archive is absent or over cap")
    before_sha = hashlib.sha256(
        source_archive.archive_bytes
    ).hexdigest()
    before_size = len(source_archive.archive_bytes)
    if (
        before_sha != source_archive.archive_sha256
        or before_size != source_archive.archive_byte_count
    ):
        _fail("typed source archive identity differs from its bytes")
    compiled = source_runtime.verify_construction_sealed_archive_compile_v2(
        closure=runtime_closure,
        archive=source_archive,
        runtime_lock=runtime_lock,
    )
    if (
        hashlib.sha256(source_archive.archive_bytes).hexdigest()
        != before_sha
        or len(source_archive.archive_bytes) != before_size
        or compiled.source_archive_id != source_archive.archive_id
        or compiled.source_closure_id != runtime_closure.closure_id
        or compiled.runtime_lock_verification_id
        != runtime_lock.verification_id
    ):
        _fail("source archive changed across isolated sealed compile replay")

    # Re-read every live source and both tracked configuration inputs only
    # after the child closes.  This prevents a post-capture mutation from
    # inheriting the earlier Git/worktree equality proof.
    repository_after = _freeze_repository_closure(
        root=root,
        runtime_closure=runtime_closure,
        module_sources=module_sources,
        module_paths=module_paths,
        relative_paths=relative_paths,
    )
    if repository_after != repository:
        _fail("repository identity changed across sealed compile replay")
    for relative, raw, label in (
        (DEPENDENCY_LOCK_PATH, dependency_lock_bytes, "dependency lock"),
        (PYPROJECT_PATH, pyproject_bytes, "pyproject"),
    ):
        _tracked_blob(root, relative=relative, expected_raw=raw)
        if _read_regular_bytes_now(
            _regular_no_symlink(root, relative),
            byte_cap=4 * 1024 * 1024,
            label=f"final {label}",
        ) != raw:
            _fail(f"{label} changed across sealed compile replay")
    archive = V075ConstructionSourceArchiveBindingV2(
        repository.runtime_source_closure_id,
        dependency.binding_id,
        source_archive.archive_id,
        before_sha,
        before_size,
        compiled.verification_id,
        compiled.child_result_sha256,
        dependency.captured_runtime_lock_id,
    )
    dag = _freeze_dag(
        upstream=upstream,
        repository=repository,
        occurrence=occurrence,
        semantic_lane=semantic_lane,
        dependency=dependency,
        archive=archive,
    )
    result = V075ConstructionSourceCodeProvenanceClosureV2(
        _CLOSURE_ISSUER,
        upstream.terminal_closure_id,
        upstream.portable_bundle_id,
        hashlib.sha256(portable_bundle_bytes).hexdigest(),
        upstream.occurrence_id,
        upstream.public_context_closure_id,
        repository,
        occurrence,
        semantic_lane,
        dependency,
        archive,
        dict(runtime_closure.to_document()),
        dict(runtime_lock.to_document()),
        dict(compiled.to_document()),
        dag,
    )
    if len(result.canonical_bytes) > MAX_OUTPUT_BYTES:
        _fail("construction provenance output exceeds its cap")
    return result


def replay_v075_construction_source_code_provenance_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075ConstructionSourceCodeProvenanceClosureV2:
    """Replay contract 1.82 first, then perform no-target provenance work."""

    # Strict first operation: no input is inspected, converted, parsed,
    # hashed, or retained before exact raw contract 1.82 succeeds.
    try:
        upstream = terminal.replay_v075_portable_semantic_terminal_closure_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
            private_generation_seed=private_generation_seed,
            private_salt=private_salt,
        )
        return _freeze_after_raw_182(
            repository_root=repository_root,
            upstream=upstream,
            portable_bundle_bytes=portable_bundle_bytes,
        )
    except Exception:
        raise V075ConstructionSourceCodeProvenanceV2InvariantViolation(
            _REPLAY_MISMATCH
        ) from None


def assert_v075_construction_source_code_provenance_production_gate_v2(
    closure: V075ConstructionSourceCodeProvenanceClosureV2,
) -> NoReturn:
    if type(closure) is not V075ConstructionSourceCodeProvenanceClosureV2:
        _fail("source/code provenance production gate rejects duck types")
    _ = closure.closure_id
    raise V075ConstructionSourceCodeProvenanceProductionV2NotReady(
        "contract 1.83 establishes local construction provenance only; "
        "the final manifest, signed preregistration, remote-main anchor, "
        "future target-worker loaded-code receipt, production, science, "
        "accounting, and certificates remain locked"
    )


__all__ = [
    "ACCOUNTING_GATE_PASSED",
    "AUTHORITY_ROOT_MODULE",
    "CODE_PROVENANCE_COMPLETE",
    "CONSTRUCTION_ALL_TRACKED_ACFQP_SOURCE_CANDIDATES_COMPLETE",
    "CONSTRUCTION_LOADED_SOURCE_MANIFEST_COMPLETE",
    "CONSTRUCTION_LOCAL_GIT_CODE_CLOSURE_COMPLETE",
    "CONSTRUCTION_SEALED_SOURCE_COMPILE_MANIFEST_COMPLETE",
    "CONSTRUCTION_SOURCE_ARCHIVE_REPLAY_COMPLETE",
    "CONSTRUCTION_TWO_LANE_PROVENANCE_DAG_COMPLETE",
    "DEPENDENCY_LOCK_PATH",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INDEPENDENT_VERIFIER_ROOT_MODULE",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "REGISTERED_GIT_EXECUTABLE",
    "REGISTERED_INTERPRETER",
    "ROOT_MODULES",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "UPSTREAM_ROOT_MODULE",
    "V075ConstructionDependencyLockBindingV2",
    "V075ConstructionGitSourceEntryV2",
    "V075ConstructionLocalRepositoryClosureV2",
    "V075ConstructionOccurrenceSourceLaneV2",
    "V075ConstructionProvenanceLaneV2",
    "V075ConstructionSemanticCodeLaneV2",
    "V075ConstructionSourceArchiveBindingV2",
    "V075ConstructionSourceCodeProvenanceClosureV2",
    "V075ConstructionSourceCodeProvenanceProductionV2NotReady",
    "V075ConstructionSourceCodeProvenanceV2InvariantViolation",
    "V075ConstructionSourceProvenanceDAGNodeV2",
    "V075ConstructionSourceProvenanceDAGV2",
    "assert_v075_construction_source_code_provenance_production_gate_v2",
    "replay_v075_construction_source_code_provenance_v2",
]
