"""Independent construction-only verifier for contract 1.83.

The verifier first replays the exact five-input contract 1.82.  It then
reconstructs the local Git closure, two provenance lanes, deterministic source
archive, locked runtime, no-execute sealed-archive compile result, and
provenance DAG using its own document and content-ID implementation.  Only the
inert source-runtime primitives are shared with the producer.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
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
PROFILE_KEY = (
    "v075_construction_source_code_provenance_independent_verifier_v2"
)
PRODUCER_PROFILE_KEY = "v075_construction_source_code_provenance_v2"
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

SOURCE_PACKAGE_PATH = "src/acfqp"
DEPENDENCY_LOCK_PATH = "specs/V075_DEPENDENCY_LOCK.json"
PYPROJECT_PATH = "pyproject.toml"
LOCAL_MAIN_REF = "refs/heads/main"
REGISTERED_INTERPRETER = "/usr/bin/python3"
REGISTERED_GIT_EXECUTABLE = "/usr/bin/git"
EXPECTED_OCCURRENCE_ENTRY_COUNT = 64
MAX_CLAIMED_BYTES = 64 * 1024 * 1024
MAX_SOURCE_MODULES = 512
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024

TERMINAL_SCOPE = "CONSTRUCTION_LOCAL_SOURCE_CODE_PROVENANCE_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_LOCAL_SOURCE_ARCHIVE_COMPILE_PROVENANCE_COMPLETE_"
    "FINAL_MANIFEST_REMOTE_ANCHOR_AND_PRODUCTION_LOCKED"
)

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
ACCOUNTING_GATE_PASSED = False
TARGET_ACCESS_ALLOWED = False
OBSERVER_OPEN_ALLOWED = False

_DOMAINS = MappingProxyType(
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
        "verification": (
            "acfqp:v075-construction-source-code-provenance-"
            "independent-verification:v2"
        ),
    }
)

_REPLAY_MISMATCH = (
    "independent construction provenance verification did not match "
    "registered evidence"
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


class V075ConstructionSourceCodeProvenanceIndependentV2Violation(
    ValueError
):
    """The raw chain, claimed closure, or independent replay changed."""


def _fail(message: str) -> NoReturn:
    raise V075ConstructionSourceCodeProvenanceIndependentV2Violation(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ConstructionSourceCodeProvenanceIndependentV2Violation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _git_oid(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) not in (40, 64)
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} is not one full lowercase Git object ID")
    return value


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            _DOMAINS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ConstructionSourceCodeProvenanceIndependentV2Violation(
            str(error)
        ) from error


def _strict_document(
    raw: bytes,
    *,
    label: str = "claimed provenance",
    byte_cap: int = MAX_CLAIMED_BYTES,
    require_canonical: bool = True,
) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > byte_cap:
        _fail(f"{label} bytes are absent, mistyped, or over cap")

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(f"{label} contains duplicate JSON keys")
            result[key] = value
        return result

    try:
        document = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=no_duplicates,
            parse_constant=lambda item: _fail(
                f"{label} contains forbidden constant {item}"
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionSourceCodeProvenanceIndependentV2Violation(
            f"{label} is not strict UTF-8 JSON"
        ) from error
    if (
        type(document) is not dict
        or (
            require_canonical
            and canonical_json_bytes(document) != raw
        )
    ):
        _fail(f"{label} is not canonical")
    return document


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
        _fail("independent Git inspection failed")
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
        _fail("independent Git blob read failed")
    return process.stdout


def _safe_relative(value: str) -> str:
    if (
        type(value) is not str
        or not value
        or "\\" in value
        or "\x00" in value
    ):
        _fail("independent source path is malformed")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        _fail("independent source path is unsafe")
    return value


def _regular_no_symlink(root: Path, relative: str) -> Path:
    cursor = root
    for part in PurePosixPath(_safe_relative(relative)).parts:
        cursor /= part
        try:
            metadata = cursor.lstat()
        except OSError as error:
            raise V075ConstructionSourceCodeProvenanceIndependentV2Violation(
                "independent source path is absent"
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            _fail("independent source path contains a symlink")
    try:
        resolved = cursor.resolve(strict=True)
        repository = root.resolve(strict=True)
    except OSError as error:
        raise V075ConstructionSourceCodeProvenanceIndependentV2Violation(
            "independent source path cannot be resolved"
        ) from error
    try:
        resolved.relative_to(repository)
    except ValueError:
        _fail("independent source path escaped repository")
    if not stat.S_ISREG(resolved.stat().st_mode):
        _fail("independent source path is not regular")
    return resolved


def _read_regular_bytes_now(
    path: Path,
    *,
    byte_cap: int,
    label: str,
) -> bytes:
    try:
        fd = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as error:
        raise V075ConstructionSourceCodeProvenanceIndependentV2Violation(
            f"{label} could not be opened as a regular nonsymlink file"
        ) from error
    try:
        before = os.fstat(fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size <= 0
            or before.st_size > byte_cap
        ):
            _fail(f"{label} is empty, nonregular, or exceeds its cap")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, byte_cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > byte_cap:
                _fail(f"{label} exceeds its cap")
        after = os.fstat(fd)
        raw = b"".join(chunks)
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ctime_ns != after.st_ctime_ns
            or len(raw) != after.st_size
        ):
            _fail(f"{label} changed while it was read or exceeded its cap")
        return raw
    finally:
        os.close(fd)


def _module_name(relative: str) -> str:
    path = PurePosixPath(_safe_relative(relative))
    if path.parts[:2] != ("src", "acfqp") or path.suffix != ".py":
        _fail("independent source is outside the ACFQP package")
    suffix = path.relative_to("src").with_suffix("")
    parts = list(suffix.parts)
    if parts[-1] == "__init__":
        parts.pop()
    value = ".".join(parts)
    if value != "acfqp" and not value.startswith("acfqp."):
        _fail("independent module name is malformed")
    return value


def _candidate_sources(
    root: Path,
) -> tuple[dict[str, bytes], dict[str, Path], dict[str, str]]:
    package = root
    for part in PurePosixPath(SOURCE_PACKAGE_PATH).parts:
        package /= part
        try:
            metadata = package.lstat()
        except OSError as error:
            raise V075ConstructionSourceCodeProvenanceIndependentV2Violation(
                "independent source package is absent"
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            _fail("independent source package path contains a symlink")
    if not package.is_dir():
        _fail("independent source package is absent")
    sources: dict[str, bytes] = {}
    paths: dict[str, Path] = {}
    relatives: dict[str, str] = {}
    total = 0
    for current, directories, filenames in os.walk(
        package,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)
        kept: list[str] = []
        for directory in sorted(directories):
            candidate = current_path / directory
            if candidate.is_symlink():
                _fail("independent source package contains a symlink directory")
            kept.append(directory)
        directories[:] = kept
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            candidate = current_path / filename
            relative = candidate.relative_to(root).as_posix()
            resolved = _regular_no_symlink(root, relative)
            name = _module_name(relative)
            raw = _read_regular_bytes_now(
                resolved,
                byte_cap=source_runtime.MAX_SOURCE_BYTES_PER_MODULE,
                label="independent ACFQP source candidate",
            )
            if name in sources:
                _fail("independent package contains duplicate module")
            total += len(raw)
            if len(sources) >= MAX_SOURCE_MODULES or total > MAX_SOURCE_BYTES:
                _fail("independent source candidate set exceeds cap")
            sources[name] = raw
            paths[name] = resolved
            relatives[name] = relative
    if "acfqp" not in sources or not set(ROOT_MODULES) <= set(sources):
        _fail("independent source metadata roots are absent")
    return sources, paths, relatives


def _tracked_acfqp_python_paths(root: Path) -> tuple[str, ...]:
    selected = tuple(
        sorted(
            _safe_relative(line)
            for line in _git(
                root,
                "ls-files",
                "--",
                SOURCE_PACKAGE_PATH,
            ).splitlines()
            if line.endswith(".py")
        )
    )
    if (
        not selected
        or len(selected) != len(set(selected))
        or any(_module_name(relative) == "" for relative in selected)
    ):
        _fail("independent tracked ACFQP candidate registry is malformed")
    return selected


def _tracked_blob(
    root: Path,
    *,
    relative: str,
    expected_raw: bytes,
) -> tuple[str, str]:
    stage = _git(root, "ls-files", "--stage", "--", relative).splitlines()
    if len(stage) != 1:
        _fail("independent source is absent or multiply staged")
    prefix, separator, staged_path = stage[0].partition("\t")
    fields = prefix.split()
    if (
        separator != "\t"
        or staged_path != relative
        or len(fields) != 3
        or fields[2] != "0"
        or fields[0] not in {"100644", "100755"}
    ):
        _fail("independent source index record is invalid")
    mode = fields[0]
    index_blob = _git_oid(fields[1], "independent index blob")
    tree = _git(
        root,
        "ls-tree",
        "HEAD",
        "--",
        relative,
    ).splitlines()
    if len(tree) != 1:
        _fail("independent source is absent from HEAD")
    tree_prefix, tree_separator, tree_path = tree[0].partition("\t")
    tree_fields = tree_prefix.split()
    if (
        tree_separator != "\t"
        or tree_path != relative
        or len(tree_fields) != 3
        or tree_fields[0] != mode
        or tree_fields[1] != "blob"
    ):
        _fail("independent HEAD source record is invalid")
    head_blob = _git_oid(tree_fields[2], "independent HEAD blob")
    if (
        index_blob != head_blob
        or _git_blob(root, index_blob) != expected_raw
        or _read_regular_bytes_now(
            _regular_no_symlink(root, relative),
            byte_cap=MAX_SOURCE_BYTES,
            label="independent live tracked source",
        )
        != expected_raw
    ):
        _fail("independent worktree, index, and HEAD source bytes differ")
    return mode, index_blob


def _with_id(
    role: str,
    field_name: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {**dict(payload), field_name: _hash(role, payload)}


def _dag_node(
    nodes: list[dict[str, Any]],
    *,
    role: str,
    artifact_id: str,
    dependencies: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    payload = {
        "schema": (
            "acfqp.v075_construction_source_provenance_dag_node.v2"
        ),
        "schema_version": SCHEMA_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "index": len(nodes),
        "role": role,
        "artifact_id": artifact_id,
        "dependency_node_ids": sorted(
            item["node_id"] for item in dependencies
        ),
    }
    node = _with_id("dag_node", "node_id", payload)
    nodes.append(node)
    return node


def _reconstruct_document(
    *,
    root: Path,
    upstream: terminal.V075PortableSemanticTerminalClosureV2,
    portable_bundle_bytes: bytes,
) -> dict[str, Any]:
    sources, paths, relatives = _candidate_sources(root)
    tracked_paths = _tracked_acfqp_python_paths(root)
    if tracked_paths != tuple(sorted(relatives.values())):
        _fail(
            "independent worktree candidates differ from complete tracked set"
        )
    runtime_closure = source_runtime.build_construction_source_closure_v2(
        root_modules=tuple(sorted(sources)),
        module_sources=sources,
        module_paths=paths,
    )
    if (
        runtime_closure.module_names != tuple(sorted(sources))
        or runtime_closure.root_modules != tuple(sorted(sources))
    ):
        _fail("independent runtime closure omitted a tracked ACFQP candidate")
    head = _git_oid(_git(root, "rev-parse", "HEAD"), "independent HEAD")
    if head != _git_oid(
        _git(root, "rev-parse", LOCAL_MAIN_REF),
        "independent local main",
    ):
        _fail("independent HEAD differs from local main")
    tree = _git_oid(
        _git(root, "rev-parse", "HEAD^{tree}"),
        "independent HEAD tree",
    )
    git_path = _regular_no_symlink(Path("/"), "usr/bin/git")
    if str(git_path) != REGISTERED_GIT_EXECUTABLE:
        _fail("independent registered Git resolved to a foreign path")
    git_raw = _read_regular_bytes_now(
        git_path,
        byte_cap=16 * 1024 * 1024,
        label="independent registered Git executable",
    )

    git_entries: list[dict[str, Any]] = []
    entry_ids: dict[str, str] = {}
    for runtime_entry in runtime_closure.modules:
        name = runtime_entry.module_name
        raw = sources[name]
        relative = relatives[name]
        if (
            paths[name] != _regular_no_symlink(root, relative)
            or runtime_entry.relative_path
            != PurePosixPath(relative).relative_to("src").as_posix()
            or runtime_entry.source_sha256
            != hashlib.sha256(raw).hexdigest()
            or runtime_entry.source_byte_count != len(raw)
        ):
            _fail("independent runtime closure differs from source bytes")
        mode, blob = _tracked_blob(
            root,
            relative=relative,
            expected_raw=raw,
        )
        payload = {
            "schema": "acfqp.v075_construction_git_source_entry.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PRODUCER_PROFILE_KEY,
            "module_name": name,
            "relative_path": relative,
            "git_mode": mode,
            "git_blob_id": blob,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "source_byte_count": len(raw),
            "runtime_source_entry_id": runtime_entry.module_id,
            "regular_file": True,
            "symlink": False,
            "worktree_equals_index_blob": True,
            "index_blob_equals_head_blob": True,
        }
        entry = _with_id("git_source_entry", "entry_id", payload)
        git_entries.append(entry)
        entry_ids[name] = entry["entry_id"]

    repository_payload = {
        "schema": (
            "acfqp.v075_construction_local_repository_closure.v2"
        ),
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "head_commit_id": head,
        "head_tree_id": tree,
        "local_branch_ref": LOCAL_MAIN_REF,
        "git_executable": REGISTERED_GIT_EXECUTABLE,
        "git_executable_sha256": hashlib.sha256(git_raw).hexdigest(),
        "git_executable_byte_count": len(git_raw),
        "root_modules": list(ROOT_MODULES),
        "runtime_source_closure_id": runtime_closure.closure_id,
        "entry_ids": [item["entry_id"] for item in git_entries],
        "entry_count": len(git_entries),
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
    repository = {
        **repository_payload,
        "entries": git_entries,
        "closure_id": _hash("repository_closure", repository_payload),
    }

    manifest = upstream.source_manifest
    if (
        len(manifest.entries) != EXPECTED_OCCURRENCE_ENTRY_COUNT
        or manifest.manifest_id != upstream.source_manifest_id
    ):
        _fail("independent raw source manifest is not the 64-entry lane")
    bindings: list[dict[str, str]] = []
    occurrence_ids: list[str] = []
    previous_name: str | None = None
    for old in manifest.entries:
        name = old.module_name
        if previous_name is not None and name <= previous_name:
            _fail("independent raw source manifest order changed")
        previous_name = name
        current_id = entry_ids.get(name)
        relative = relatives.get(name)
        raw = sources.get(name)
        if (
            current_id is None
            or relative != f"src/{old.relative_path}"
            or raw is None
            or hashlib.sha256(raw).hexdigest() != old.source_sha256
            or len(raw) != old.source_byte_count
        ):
            _fail("independent raw source lane is not an exact subset")
        bindings.append(
            {"module_name": name, "git_source_entry_id": current_id}
        )
        occurrence_ids.append(current_id)
    manifest_raw = manifest.canonical_bytes
    occurrence_payload = {
        "schema": "acfqp.v075_construction_occurrence_source_lane.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "lane": "OCCURRENCE_BUNDLE_SOURCE",
        "source_manifest_id": manifest.manifest_id,
        "source_manifest_sha256": hashlib.sha256(
            manifest_raw
        ).hexdigest(),
        "source_manifest_byte_count": len(manifest_raw),
        "repository_closure_id": repository["closure_id"],
        "entry_bindings": bindings,
        "entry_count": len(bindings),
        "raw_manifest_exact_subset": True,
        "manifest_authority_upgraded": False,
    }
    occurrence_lane = _with_id(
        "occurrence_lane",
        "lane_id",
        occurrence_payload,
    )

    all_ids = [item["entry_id"] for item in git_entries]
    occurrence_set = set(occurrence_ids)
    semantic_only = [
        item["entry_id"]
        for item in git_entries
        if item["entry_id"] not in occurrence_set
    ]
    if not semantic_only:
        _fail("independent semantic lane added no contract code")
    semantic_payload = {
        "schema": "acfqp.v075_construction_semantic_code_lane.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "lane": "SEMANTIC_REPLAY_CODE",
        "repository_closure_id": repository["closure_id"],
        "runtime_source_closure_id": runtime_closure.closure_id,
        "root_modules": list(ROOT_MODULES),
        "entry_ids": all_ids,
        "occurrence_shared_entry_ids": occurrence_ids,
        "semantic_only_entry_ids": semantic_only,
        "entry_count": len(all_ids),
        "occurrence_shared_entry_count": len(occurrence_ids),
        "semantic_only_entry_count": len(semantic_only),
        "static_multi_root_closure_exact": True,
        "production_manifest_binding": {
            "kind": "NOT_YET_APPLICABLE",
            "reason": "FINAL_MANIFEST_AND_REMOTE_ANCHOR_NOT_FROZEN",
        },
    }
    semantic_lane = _with_id(
        "semantic_lane",
        "lane_id",
        semantic_payload,
    )

    lock_bytes = _read_regular_bytes_now(
        _regular_no_symlink(root, DEPENDENCY_LOCK_PATH),
        byte_cap=4 * 1024 * 1024,
        label="independent dependency-lock capture",
    )
    pyproject_bytes = _read_regular_bytes_now(
        _regular_no_symlink(root, PYPROJECT_PATH),
        byte_cap=4 * 1024 * 1024,
        label="independent pyproject capture",
    )
    lock_mode, lock_blob = _tracked_blob(
        root,
        relative=DEPENDENCY_LOCK_PATH,
        expected_raw=lock_bytes,
    )
    project_mode, project_blob = _tracked_blob(
        root,
        relative=PYPROJECT_PATH,
        expected_raw=pyproject_bytes,
    )
    if lock_mode not in {"100644", "100755"} or project_mode not in {
        "100644",
        "100755",
    }:
        _fail("independent runtime inputs are not regular Git blobs")
    lock_document = _strict_document(
        lock_bytes,
        label="independent V0-075 dependency lock",
        byte_cap=4 * 1024 * 1024,
        require_canonical=False,
    )
    registered_lock_id = _cid(
        lock_document.get("runtime_dependency_lock_id"),
        "independent registered runtime lock",
    )
    runtime_lock = (
        source_runtime.verify_construction_runtime_dependency_lock_v2(
            dependency_lock_bytes=lock_bytes,
            pyproject_bytes=pyproject_bytes,
        )
    )
    if (
        runtime_lock.dependency_lock_id != registered_lock_id
        or runtime_lock.requested_executable != REGISTERED_INTERPRETER
        or runtime_lock.pyproject_sha256
        != hashlib.sha256(pyproject_bytes).hexdigest()
    ):
        _fail("independent runtime replay differs from tracked lock")
    dependency_payload = {
        "schema": "acfqp.v075_construction_dependency_lock_binding.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "repository_path": DEPENDENCY_LOCK_PATH,
        "git_blob_id": lock_blob,
        "raw_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        "raw_byte_count": len(lock_bytes),
        "pyproject_path": PYPROJECT_PATH,
        "pyproject_git_blob_id": project_blob,
        "pyproject_sha256": hashlib.sha256(
            pyproject_bytes
        ).hexdigest(),
        "pyproject_byte_count": len(pyproject_bytes),
        "registered_runtime_dependency_lock_id": registered_lock_id,
        "captured_runtime_lock_id": runtime_lock.verification_id,
        "interpreter_path": REGISTERED_INTERPRETER,
        "worktree_index_head_equal": True,
        "registered_lock_semantically_replayed": True,
        "production_dependency_lock_promoted": False,
    }
    dependency = _with_id(
        "dependency_lock_binding",
        "binding_id",
        dependency_payload,
    )

    archive = source_runtime.build_deterministic_source_archive_v2(
        closure=runtime_closure,
        module_sources=sources,
    )
    if (
        type(archive) is not source_runtime.ConstructionSourceArchiveV2
        or not archive.archive_bytes
        or archive.archive_byte_count > MAX_ARCHIVE_BYTES
        or hashlib.sha256(archive.archive_bytes).hexdigest()
        != archive.archive_sha256
    ):
        _fail("independent deterministic archive is malformed")
    before = (archive.archive_sha256, archive.archive_byte_count)
    compiled = source_runtime.verify_construction_sealed_archive_compile_v2(
        closure=runtime_closure,
        archive=archive,
        runtime_lock=runtime_lock,
    )
    after = (
        hashlib.sha256(archive.archive_bytes).hexdigest(),
        len(archive.archive_bytes),
    )
    if (
        before != after
        or compiled.source_archive_id != archive.archive_id
        or compiled.source_closure_id != runtime_closure.closure_id
        or compiled.runtime_lock_verification_id
        != runtime_lock.verification_id
    ):
        _fail("independent isolated compile changed archive identity")

    # Match the producer's post-child currentness proof without calling it:
    # recompute Git, Git executable, every tracked ACFQP source, dependency
    # lock, and pyproject after the child has closed.
    final_sources, final_paths, final_relatives = _candidate_sources(root)
    if (
        final_sources != sources
        or final_paths != paths
        or final_relatives != relatives
        or _tracked_acfqp_python_paths(root) != tracked_paths
        or _git_oid(_git(root, "rev-parse", "HEAD"), "final HEAD") != head
        or _git_oid(
            _git(root, "rev-parse", LOCAL_MAIN_REF),
            "final local main",
        )
        != head
        or _git_oid(
            _git(root, "rev-parse", "HEAD^{tree}"),
            "final HEAD tree",
        )
        != tree
        or _read_regular_bytes_now(
            _regular_no_symlink(Path("/"), "usr/bin/git"),
            byte_cap=16 * 1024 * 1024,
            label="final independent Git executable",
        )
        != git_raw
    ):
        _fail("independent repository identity changed across compile replay")
    for name in sorted(sources):
        _tracked_blob(
            root,
            relative=relatives[name],
            expected_raw=sources[name],
        )
    for relative, raw, label in (
        (DEPENDENCY_LOCK_PATH, lock_bytes, "dependency lock"),
        (PYPROJECT_PATH, pyproject_bytes, "pyproject"),
    ):
        _tracked_blob(root, relative=relative, expected_raw=raw)
        if (
            _read_regular_bytes_now(
                _regular_no_symlink(root, relative),
                byte_cap=4 * 1024 * 1024,
                label=f"final independent {label}",
            )
            != raw
        ):
            _fail(f"independent {label} changed across compile replay")

    archive_payload = {
        "schema": "acfqp.v075_construction_source_archive_binding.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "runtime_source_closure_id": runtime_closure.closure_id,
        "dependency_lock_binding_id": dependency["binding_id"],
        "source_archive_id": archive.archive_id,
        "archive_sha256": archive.archive_sha256,
        "archive_byte_count": archive.archive_byte_count,
        "archive_format": "DETERMINISTIC_ZIP_STORED_V2",
        "compile_verification_id": compiled.verification_id,
        "compile_child_result_sha256": compiled.child_result_sha256,
        "runtime_lock_id": runtime_lock.verification_id,
        "archive_verified_before_child": True,
        "archive_verified_after_child": True,
        "isolated_exact_archive_member_compile": True,
        "tested_source_executed": False,
        "loaded_source_manifest_claimed": False,
        "live_source_fallback_used": False,
        "target_accessed": False,
    }
    archive_binding = _with_id(
        "archive_binding",
        "binding_id",
        archive_payload,
    )

    nodes: list[dict[str, Any]] = []
    raw_node = _dag_node(
        nodes,
        role="RAW_182_SEMANTIC_TERMINAL_CLOSURE",
        artifact_id=upstream.terminal_closure_id,
    )
    manifest_node = _dag_node(
        nodes,
        role="RAW_PUBLIC_CONTEXT_SOURCE_MANIFEST",
        artifact_id=upstream.source_manifest_id,
        dependencies=(raw_node,),
    )
    repository_node = _dag_node(
        nodes,
        role="LOCAL_HEAD_INDEX_WORKTREE_SOURCE_CLOSURE",
        artifact_id=repository["closure_id"],
        dependencies=(raw_node,),
    )
    occurrence_node = _dag_node(
        nodes,
        role="OCCURRENCE_BUNDLE_SOURCE_LANE",
        artifact_id=occurrence_lane["lane_id"],
        dependencies=(manifest_node, repository_node),
    )
    semantic_node = _dag_node(
        nodes,
        role="SEMANTIC_REPLAY_CODE_LANE",
        artifact_id=semantic_lane["lane_id"],
        dependencies=(raw_node, occurrence_node, repository_node),
    )
    dependency_node = _dag_node(
        nodes,
        role="TRACKED_RUNTIME_DEPENDENCY_LOCK",
        artifact_id=dependency["binding_id"],
        dependencies=(repository_node,),
    )
    archive_node = _dag_node(
        nodes,
        role="DETERMINISTIC_SEALED_SOURCE_ARCHIVE",
        artifact_id=archive_binding["binding_id"],
        dependencies=(semantic_node, dependency_node),
    )
    _dag_node(
        nodes,
        role="NO_TARGET_ISOLATED_SEALED_SOURCE_COMPILE_VERIFICATION",
        artifact_id=compiled.verification_id,
        dependencies=(archive_node,),
    )
    dag_payload = {
        "schema": "acfqp.v075_construction_source_provenance_dag.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "node_ids": [item["node_id"] for item in nodes],
        "node_count": len(nodes),
        "topological_order_verified": True,
        "two_provenance_lanes_preserved": True,
    }
    dag = {
        **dag_payload,
        "nodes": nodes,
        "dag_id": _hash("dag", dag_payload),
    }

    payload = {
        "schema": (
            "acfqp.v075_construction_source_code_provenance_closure.v2"
        ),
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "upstream_profile_key": UPSTREAM_PROFILE_KEY,
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS,
        "terminal_code": TERMINAL_CODE,
        "semantic_terminal_closure_id": upstream.terminal_closure_id,
        "portable_bundle_id": upstream.portable_bundle_id,
        "portable_bundle_sha256": hashlib.sha256(
            portable_bundle_bytes
        ).hexdigest(),
        "occurrence_id": upstream.occurrence_id,
        "public_context_closure_id": upstream.public_context_closure_id,
        "repository_closure": repository,
        "repository_closure_id": repository["closure_id"],
        "occurrence_source_lane": occurrence_lane,
        "occurrence_source_lane_id": occurrence_lane["lane_id"],
        "semantic_code_lane": semantic_lane,
        "semantic_code_lane_id": semantic_lane["lane_id"],
        "dependency_lock_binding": dependency,
        "dependency_lock_binding_id": dependency["binding_id"],
        "source_archive_binding": archive_binding,
        "source_archive_binding_id": archive_binding["binding_id"],
        "runtime_source_closure": runtime_closure.to_document(),
        "runtime_lock": runtime_lock.to_document(),
        "sealed_source_compile_verification": compiled.to_document(),
        "provenance_dag": dag,
        "provenance_dag_id": dag["dag_id"],
        "provenance_lane_order": [
            "OCCURRENCE_BUNDLE_SOURCE",
            "SEMANTIC_REPLAY_CODE",
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
    return {**payload, "closure_id": _hash("closure", payload)}


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionSourceCodeProvenanceIndependentVerificationV2:
    _issuer: InitVar[object]
    closure_id: str
    closure_sha256: str
    closure_byte_count: int
    semantic_terminal_closure_id: str
    repository_closure_id: str
    source_archive_binding_id: str
    provenance_dag_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.closure_id, "verified closure"),
            (self.closure_sha256, "verified closure bytes"),
            (
                self.semantic_terminal_closure_id,
                "verified semantic terminal",
            ),
            (self.repository_closure_id, "verified repository closure"),
            (
                self.source_archive_binding_id,
                "verified archive binding",
            ),
            (self.provenance_dag_id, "verified provenance DAG"),
        ):
            _cid(value, label)
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.closure_byte_count) is not int
            or self.closure_byte_count <= 0
        ):
            _fail("independent verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_source_code_provenance_"
                "independent_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "closure_id": self.closure_id,
            "closure_sha256": self.closure_sha256,
            "closure_byte_count": self.closure_byte_count,
            "semantic_terminal_closure_id": (
                self.semantic_terminal_closure_id
            ),
            "repository_closure_id": self.repository_closure_id,
            "source_archive_binding_id": self.source_archive_binding_id,
            "provenance_dag_id": self.provenance_dag_id,
            "producer_entry_called": False,
            "producer_freezer_called": False,
            "producer_issuer_used": False,
            "independent_git_replay": True,
            "independent_document_reconstruction": True,
            "shared_inert_runtime_primitives_only": True,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "fresh_heldout_accessed": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "accounting_gate_passed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }

    def __reduce__(self) -> NoReturn:
        raise TypeError("independent construction verifications are in-memory-only")


def verify_v075_construction_source_code_provenance_bytes_v2(
    *,
    closure_bytes: bytes,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075ConstructionSourceCodeProvenanceIndependentVerificationV2:
    """Replay raw 1.82 first, then independently reconstruct contract 1.83."""

    # Strict first operation: closure_bytes and every local construction
    # resource remain untouched until exact raw contract 1.82 succeeds.
    try:
        upstream = terminal.replay_v075_portable_semantic_terminal_closure_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
            private_generation_seed=private_generation_seed,
            private_salt=private_salt,
        )
        claimed = _strict_document(closure_bytes)
        root = Path(repository_root).resolve(strict=True)
        if not root.is_dir() or not root.joinpath(".git").exists():
            _fail("independent repository root is not one Git worktree")
        expected = _reconstruct_document(
            root=root,
            upstream=upstream,
            portable_bundle_bytes=portable_bundle_bytes,
        )
        expected_bytes = canonical_json_bytes(expected)
        if closure_bytes != expected_bytes or claimed != expected:
            _fail("claimed provenance differs from independent replay")
        return V075ConstructionSourceCodeProvenanceIndependentVerificationV2(
            _VERIFICATION_ISSUER,
            _cid(expected["closure_id"], "independent closure"),
            hashlib.sha256(expected_bytes).hexdigest(),
            len(expected_bytes),
            _cid(
                expected["semantic_terminal_closure_id"],
                "independent semantic terminal",
            ),
            _cid(
                expected["repository_closure_id"],
                "independent repository closure",
            ),
            _cid(
                expected["source_archive_binding_id"],
                "independent source archive binding",
            ),
            _cid(
                expected["provenance_dag_id"],
                "independent provenance DAG",
            ),
        )
    except Exception:
        raise V075ConstructionSourceCodeProvenanceIndependentV2Violation(
            _REPLAY_MISMATCH
        ) from None


__all__ = [
    "ACCOUNTING_GATE_PASSED",
    "CODE_PROVENANCE_COMPLETE",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "V075ConstructionSourceCodeProvenanceIndependentV2Violation",
    "V075ConstructionSourceCodeProvenanceIndependentVerificationV2",
    "verify_v075_construction_source_code_provenance_bytes_v2",
]
