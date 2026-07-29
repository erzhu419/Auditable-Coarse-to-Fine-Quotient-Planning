"""Typed, locally replayed V0-072 test and runtime environment authorities.

The two checked-in JSON specifications are descriptive inputs, never trusted
claims.  This module derives the exact test command, repository test tree,
active dependency environment, and interpreter build from the current
repository/process, then requires byte-for-byte agreement with those
specifications before minting a typed authority.

No public constructor accepts a digest, identifier, validity flag, status, or
precomputed environment description.  The module does not execute pytest,
open a registered observer, access a target tape, inspect a remote, or enable
confirmatory execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import sys
import sysconfig
from typing import Any, Mapping

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id

try:  # Python 3.10 uses the locked backport.
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10.
    import tomli as tomllib  # type: ignore[no-redef]


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_execution_environment_authorities_v1"

TEST_COMMAND_SPEC_PATH = "specs/V072_CONFIRMATORY_TEST_COMMAND.json"
RUNTIME_LOCK_SPEC_PATH = "specs/V072_RUNTIME_DEPENDENCY_LOCK.json"
PYPROJECT_PATH = "pyproject.toml"
TEST_ROOT = "tests"

PRODUCTION_IMPLEMENTATION_PATH = (
    "src/acfqp/v072_execution_environment_authority_v1.py"
)
INDEPENDENT_IMPLEMENTATION_PATH = (
    "src/acfqp/v072_execution_environment_independent_verifier_v1.py"
)
SPEC_GENERATOR_PATH = (
    "scripts/generate_v072_execution_environment_specs.py"
)
TEST_WRAPPER_PATH = "scripts/run_v072_confirmatory_tests.py"
PARALLEL_TEST_RUNNER_PATH = "scripts/run_pytest_parallel.py"
IMPLEMENTATION_PATHS = (
    PRODUCTION_IMPLEMENTATION_PATH,
    INDEPENDENT_IMPLEMENTATION_PATH,
    SPEC_GENERATOR_PATH,
    TEST_WRAPPER_PATH,
    PARALLEL_TEST_RUNNER_PATH,
)

EXACT_TEST_COMMAND = (
    "python3",
    TEST_WRAPPER_PATH,
)
INNER_TEST_COMMAND = (
    "python3",
    PARALLEL_TEST_RUNNER_PATH,
    "-j",
    "32",
    "--fresh-ids",
    "--no-timing-cache",
    "tests",
)
DETERMINISTIC_ENVIRONMENT_SETTINGS = (
    ("LC_ALL", "C.UTF-8"),
    ("PYTHONDONTWRITEBYTECODE", "1"),
    ("PYTHONHASHSEED", "0"),
)

TEST_COMMAND_DOMAIN = "acfqp:v072-confirmatory-test-command-manifest:v1"
TEST_TREE_DOMAIN = "acfqp:v072-confirmatory-test-tree:v1"
RUNTIME_LOCK_DOMAIN = "acfqp:v072-runtime-dependency-lock:v1"
INTERPRETER_BUILD_DOMAIN = "acfqp:v072-interpreter-build-identity:v1"
INSTALLED_TREE_DOMAIN = "acfqp:v072-installed-distribution-tree:v1"
STDLIB_TREE_DOMAIN = "acfqp:v072-interpreter-stdlib-tree:v1"

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_ISSUER = object()


class V072ExecutionEnvironmentAuthorityInvariantViolation(ValueError):
    """The checked-in environment description is stale or malformed."""


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            f"{field_name} is not one canonical nonempty string"
        )
    return value


def _repo_root(value: str | os.PathLike[str]) -> Path:
    root = Path(value)
    if not root.is_dir() or root.is_symlink():
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "repository root must be one existing non-symlink directory"
        )
    return root.resolve(strict=True)


def _safe_repo_path(root: Path, value: str) -> Path:
    if (
        type(value) is not str
        or not value
        or "\\" in value
        or "\x00" in value
    ):
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "repository path is not canonical POSIX relative text"
        )
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or str(relative) != value
        or any(part in ("", ".", "..") for part in relative.parts)
    ):
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "repository path is absolute, noncanonical, or traverses"
        )
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                "repository evidence path contains a symlink"
            )
    try:
        resolved = cursor.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as error:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "repository evidence path is missing or escapes the root"
        ) from error
    if not resolved.is_file():
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "repository evidence path is not one regular file"
        )
    return resolved


def _read_regular_file(path: Path, *, allow_symlink: bool = False) -> bytes:
    if path.is_symlink() and not allow_symlink:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "evidence path is a symlink"
        )
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW") and not allow_symlink:
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                "evidence path is not a regular file"
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
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "evidence file changed while being read"
        )
    data = b"".join(chunks)
    if len(data) != after.st_size:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "evidence byte count differs from file metadata"
        )
    return data


def _repo_file_record(root: Path, relative_path: str) -> dict[str, Any]:
    data = _read_regular_file(_safe_repo_path(root, relative_path))
    return {
        "repository_relative_path": relative_path,
        "sha256_file_bytes": _sha256(data),
        "file_byte_count": len(data),
    }


def _render_spec(document: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(document),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                f"duplicate JSON key: {key}"
            )
        result[key] = value
    return result


def _reject_constant(token: str) -> Any:
    raise V072ExecutionEnvironmentAuthorityInvariantViolation(
        f"non-finite JSON constant is forbidden: {token}"
    )


def _load_spec(root: Path, relative_path: str) -> tuple[dict[str, Any], bytes]:
    data = _read_regular_file(_safe_repo_path(root, relative_path))
    try:
        parsed = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        V072ExecutionEnvironmentAuthorityInvariantViolation,
    ) as error:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            f"{relative_path} is not strict UTF-8 JSON"
        ) from error
    if type(parsed) is not dict or _render_spec(parsed) != data:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            f"{relative_path} is not the canonical pretty JSON rendering"
        )
    return parsed, data


def _tree_digest(domain: str, records: list[dict[str, Any]]) -> str:
    return _content_id(
        domain,
        {
            "schema": "acfqp.v072_ordered_file_tree.v1",
            "schema_version": SCHEMA_VERSION,
            "records": records,
        },
    )


def _test_files(root: Path) -> list[dict[str, Any]]:
    test_root = root / TEST_ROOT
    if (
        not test_root.is_dir()
        or test_root.is_symlink()
        or test_root.resolve(strict=True).parent != root
    ):
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "registered test root is missing, linked, or misplaced"
        )
    relative_paths: list[str] = []
    for candidate in test_root.rglob("*.py"):
        relative = candidate.relative_to(root).as_posix()
        _safe_repo_path(root, relative)
        relative_paths.append(relative)
    if len(relative_paths) != len(set(relative_paths)) or not relative_paths:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "registered test tree is empty or aliases a file"
        )
    return [
        _repo_file_record(root, path)
        for path in sorted(relative_paths)
    ]


def _test_command_payload(root: Path) -> dict[str, Any]:
    test_files = _test_files(root)
    implementations = [
        _repo_file_record(root, path) for path in IMPLEMENTATION_PATHS
    ]
    return {
        "schema": "acfqp.v072_confirmatory_test_command_manifest.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": "v072_confirmatory_test_command_manifest_v1",
        "invocation": {
            "argv": list(EXACT_TEST_COMMAND),
            "inner_argv": list(INNER_TEST_COMMAND),
            "shell": False,
            "working_directory": "REPOSITORY_ROOT",
            "collection_root": TEST_ROOT,
            "deterministic_environment": [
                {"name": name, "value": value}
                for name, value in DETERMINISTIC_ENVIRONMENT_SETTINGS
            ],
            "pytest_cache_provider_disabled": True,
            "temporary_directory_policy": {
                "kind": "PRIVATE_MKDTEMP_UNDER_REPOSITORY_TMP",
                "host_tmp_environment_inherited": False,
                "runtime_random_path_in_content_id": False,
                "overridden_variables": [
                    "ACFQP_PARALLEL_TEMP_ROOT",
                    "TEMP",
                    "TMP",
                    "TMPDIR",
                ],
                "cleanup_required": True,
                "module_process_isolation": True,
            },
            "parallel_module_workers": 32,
            "fresh_content_id_recomputation": True,
        },
        "pytest_configuration": _repo_file_record(root, PYPROJECT_PATH),
        "test_tree": {
            "selection": "tests/**/*.py",
            "test_file_count": len(test_files),
            "test_tree_digest": _tree_digest(
                TEST_TREE_DOMAIN,
                test_files,
            ),
        },
        "implementation_files": implementations,
        "caller_supplied_digest_accepted": False,
        "caller_supplied_status_accepted": False,
        "executes_tests": False,
        "target_access": False,
    }


def build_expected_confirmatory_test_command_document_v1(
    repository_root: str | os.PathLike[str],
) -> dict[str, Any]:
    """Derive the canonical test-command specification from current bytes."""

    payload = _test_command_payload(_repo_root(repository_root))
    return {
        **payload,
        "test_command_manifest_id": _content_id(
            TEST_COMMAND_DOMAIN,
            payload,
        ),
    }


def render_expected_confirmatory_test_command_spec_v1(
    repository_root: str | os.PathLike[str],
) -> bytes:
    return _render_spec(
        build_expected_confirmatory_test_command_document_v1(
            repository_root
        )
    )


def _distribution_file_tree(
    distribution: metadata.Distribution,
) -> tuple[int, str]:
    records: list[dict[str, Any]] = []
    paths = distribution.files
    if not paths:
        top_level = distribution.read_text("top_level.txt")
        if type(top_level) is not str or not top_level.strip():
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                f"distribution {distribution.metadata['Name']} has no "
                "file index or top-level package record"
            )
        discovered: list[Path] = []
        for name in sorted(set(top_level.split())):
            candidate = Path(distribution.locate_file(name))
            if candidate.is_dir():
                discovered.extend(
                    item
                    for item in candidate.rglob("*")
                    if item.is_file() or item.is_symlink()
                )
            elif candidate.is_file() or candidate.is_symlink():
                discovered.append(candidate)
            else:
                raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                    "top-level distribution package is absent"
                )
        base = Path(distribution.locate_file(""))
        paths = tuple(
            PurePosixPath(item.relative_to(base).as_posix())
            for item in discovered
        )
    seen: set[str] = set()
    for item in sorted(paths, key=lambda value: str(value)):
        relative = str(item).replace("\\", "/")
        if (
            relative in seen
            or "\x00" in relative
            or "/__pycache__/" in f"/{relative}/"
            or relative.endswith((".pyc", ".pyo"))
        ):
            if relative in seen:
                raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                    "distribution file index contains a duplicate path"
                )
            continue
        seen.add(relative)
        candidate = Path(distribution.locate_file(item))
        if candidate.is_symlink():
            resolved = candidate.resolve(strict=True)
            data = _read_regular_file(resolved)
            records.append(
                {
                    "distribution_relative_path": relative,
                    "kind": "SYMLINK",
                    "link_target": os.readlink(candidate),
                    "resolved_sha256_file_bytes": _sha256(data),
                    "resolved_file_byte_count": len(data),
                }
            )
        elif candidate.is_file():
            data = _read_regular_file(candidate)
            records.append(
                {
                    "distribution_relative_path": relative,
                    "kind": "REGULAR_FILE",
                    "sha256_file_bytes": _sha256(data),
                    "file_byte_count": len(data),
                }
            )
        else:
            records.append(
                {
                    "distribution_relative_path": relative,
                    "kind": "ABSENT_INDEXED_FILE",
                }
            )
    return len(records), _tree_digest(INSTALLED_TREE_DOMAIN, records)


def _distribution_record(name: str) -> dict[str, Any]:
    canonical_name = canonicalize_name(name)
    try:
        distribution = metadata.distribution(canonical_name)
    except metadata.PackageNotFoundError as error:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            f"locked distribution is absent: {canonical_name}"
        ) from error
    metadata_kind = "METADATA"
    metadata_text = distribution.read_text(metadata_kind)
    if metadata_text is None:
        metadata_kind = "PKG-INFO"
        metadata_text = distribution.read_text(metadata_kind)
    wheel_text = distribution.read_text("WHEEL")
    if metadata_text is None:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            f"distribution metadata is incomplete: {canonical_name}"
        )
    metadata_bytes = metadata_text.encode("utf-8")
    wheel_record: dict[str, Any]
    if wheel_text is None:
        wheel_record = {"kind": "NOT_PRESENT"}
    else:
        wheel_bytes = wheel_text.encode("utf-8")
        wheel_record = {
            "kind": "PRESENT",
            "sha256_file_bytes": _sha256(wheel_bytes),
            "file_byte_count": len(wheel_bytes),
        }
    file_count, tree_digest = _distribution_file_tree(distribution)
    installer = distribution.read_text("INSTALLER")
    direct_url = distribution.read_text("direct_url.json")
    return {
        "normalized_name": canonical_name,
        "declared_name": _strict_token(
            distribution.metadata["Name"],
            "distribution declared name",
        ),
        "version": _strict_token(
            distribution.version,
            "distribution version",
        ),
        "metadata_kind": metadata_kind,
        "metadata_sha256": _sha256(metadata_bytes),
        "metadata_byte_count": len(metadata_bytes),
        "wheel_metadata": wheel_record,
        "installed_file_count": file_count,
        "installed_file_tree_digest": tree_digest,
        "installer": (
            installer.strip()
            if type(installer) is str and installer.strip()
            else {"kind": "NOT_RECORDED"}
        ),
        "direct_url": (
            json.loads(direct_url)
            if type(direct_url) is str and direct_url.strip()
            else {"kind": "NOT_PRESENT"}
        ),
    }


def _project_configuration(root: Path) -> dict[str, Any]:
    data = _read_regular_file(_safe_repo_path(root, PYPROJECT_PATH))
    try:
        parsed = tomllib.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, ValueError) as error:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "pyproject.toml is not parseable UTF-8 TOML"
        ) from error
    try:
        project = parsed["project"]
        build = parsed["build-system"]
        pytest_config = parsed["tool"]["pytest"]["ini_options"]
        project_dependencies = project["dependencies"]
        test_dependencies = project["optional-dependencies"]["test"]
        build_dependencies = build["requires"]
        requires_python = project["requires-python"]
        pythonpath = pytest_config["pythonpath"]
        testpaths = pytest_config["testpaths"]
    except (KeyError, TypeError) as error:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "pyproject.toml lacks the registered project/test fields"
        ) from error
    string_lists = (
        project_dependencies,
        test_dependencies,
        build_dependencies,
        pythonpath,
        testpaths,
    )
    if any(
        type(values) is not list
        or any(type(value) is not str for value in values)
        for values in string_lists
    ):
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "pyproject dependency or pytest lists are malformed"
        )
    if testpaths != [TEST_ROOT] or pythonpath != [".", "src"]:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "pytest testpaths/pythonpath differ from the registered layout"
        )
    return {
        "requires_python": _strict_token(
            requires_python,
            "project requires-python",
        ),
        "project_dependencies": list(project_dependencies),
        "test_dependencies": list(test_dependencies),
        "build_dependencies": list(build_dependencies),
        "pytest_pythonpath": list(pythonpath),
        "pytest_testpaths": list(testpaths),
    }


def _pytest_plugin_roots() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for entry_point in metadata.entry_points(group="pytest11"):
        distribution = entry_point.dist
        if distribution is None:
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                "pytest11 entry point has no owning distribution"
            )
        records.append(
            {
                "entry_point_name": _strict_token(
                    entry_point.name,
                    "pytest plugin entry-point name",
                ),
                "entry_point_value": _strict_token(
                    entry_point.value,
                    "pytest plugin entry-point value",
                ),
                "distribution_name": canonicalize_name(
                    distribution.metadata["Name"]
                ),
                "distribution_version": distribution.version,
            }
        )
    records.sort(
        key=lambda item: (
            item["entry_point_name"],
            item["entry_point_value"],
            item["distribution_name"],
        )
    )
    if len(records) != len(
        {
            (
                item["entry_point_name"],
                item["entry_point_value"],
                item["distribution_name"],
            )
            for item in records
        }
    ):
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "pytest plugin registry contains duplicate semantic entries"
        )
    return records


def _requirement_roots(
    project: Mapping[str, Any],
    plugins: list[dict[str, Any]],
) -> list[dict[str, str]]:
    roots: list[dict[str, str]] = []
    for source, requirements in (
        ("project.dependencies", project["project_dependencies"]),
        (
            "project.optional-dependencies.test",
            project["test_dependencies"],
        ),
        ("build-system.requires", project["build_dependencies"]),
    ):
        roots.extend(
            {
                "source": source,
                "requirement": requirement,
            }
            for requirement in requirements
        )
    roots.extend(
        {
            "source": (
                "environment.pytest11:"
                f"{plugin['entry_point_name']}"
            ),
            "requirement": (
                f"{plugin['distribution_name']}=="
                f"{plugin['distribution_version']}"
            ),
        }
        for plugin in plugins
    )
    roots.sort(key=lambda item: (item["source"], item["requirement"]))
    return roots


def _dependency_closure(
    roots: list[dict[str, str]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, str]],
    list[dict[str, str]],
]:
    marker_environment = default_environment()
    marker_environment["extra"] = ""
    queue: list[tuple[str, str]] = [
        ("<ROOT>", item["requirement"]) for item in roots
    ]
    visited: set[str] = set()
    edges: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []
    while queue:
        parent, raw_requirement = queue.pop(0)
        try:
            requirement = Requirement(raw_requirement)
        except ValueError as error:
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                f"invalid dependency requirement: {raw_requirement}"
            ) from error
        if (
            requirement.marker is not None
            and not requirement.marker.evaluate(marker_environment)
        ):
            continue
        child = canonicalize_name(requirement.name)
        if parent != "<ROOT>":
            edges.append(
                {
                    "parent_distribution": parent,
                    "requirement": raw_requirement,
                    "child_distribution": child,
                }
            )
        try:
            distribution = metadata.distribution(child)
        except metadata.PackageNotFoundError:
            unresolved.append(
                {
                    "parent_distribution": parent,
                    "requirement": raw_requirement,
                    "child_distribution": child,
                    "reason": "MISSING_DISTRIBUTION",
                }
            )
            continue
        if (
            requirement.specifier
            and distribution.version not in requirement.specifier
        ):
            unresolved.append(
                {
                    "parent_distribution": parent,
                    "requirement": raw_requirement,
                    "child_distribution": child,
                    "reason": "VERSION_OUTSIDE_SPECIFIER",
                }
            )
        if child in visited:
            continue
        visited.add(child)
        for dependency in distribution.requires or ():
            parsed = Requirement(dependency)
            if (
                parsed.marker is None
                or parsed.marker.evaluate(marker_environment)
            ):
                queue.append((child, dependency))
    distributions = [
        _distribution_record(name) for name in sorted(visited)
    ]
    edges.sort(
        key=lambda item: (
            item["parent_distribution"],
            item["child_distribution"],
            item["requirement"],
        )
    )
    unresolved.sort(
        key=lambda item: (
            item["parent_distribution"],
            item["child_distribution"],
            item["requirement"],
            item["reason"],
        )
    )
    return distributions, edges, unresolved


def _stdlib_tree() -> tuple[int, str]:
    stdlib = Path(sysconfig.get_path("stdlib"))
    if not stdlib.is_dir():
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "interpreter stdlib directory is missing"
        )
    root = stdlib.resolve(strict=True)
    records: list[dict[str, Any]] = []
    for candidate in sorted(
        root.rglob("*"),
        key=lambda value: value.relative_to(root).as_posix(),
    ):
        relative = candidate.relative_to(root).as_posix()
        parts = PurePosixPath(relative).parts
        if (
            "__pycache__" in parts
            or "site-packages" in parts
            or "dist-packages" in parts
            or candidate.name.endswith((".pyc", ".pyo"))
        ):
            continue
        if candidate.is_symlink():
            resolved = candidate.resolve(strict=True)
            if not resolved.is_file():
                continue
            data = _read_regular_file(resolved)
            records.append(
                {
                    "stdlib_relative_path": relative,
                    "kind": "SYMLINK",
                    "link_target": os.readlink(candidate),
                    "resolved_sha256_file_bytes": _sha256(data),
                    "resolved_file_byte_count": len(data),
                }
            )
        elif candidate.is_file():
            data = _read_regular_file(candidate)
            records.append(
                {
                    "stdlib_relative_path": relative,
                    "kind": "REGULAR_FILE",
                    "sha256_file_bytes": _sha256(data),
                    "file_byte_count": len(data),
                }
            )
    if not records:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "interpreter stdlib tree is empty"
        )
    return len(records), _tree_digest(STDLIB_TREE_DOMAIN, records)


def _absolute_file_record(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    data = _read_regular_file(resolved)
    return {
        "sha256_file_bytes": _sha256(data),
        "file_byte_count": len(data),
    }


def _interpreter_build_payload() -> dict[str, Any]:
    executable = Path(sys.executable)
    if not executable.exists():
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "sys.executable does not exist"
        )
    command = shutil.which(INNER_TEST_COMMAND[0])
    if command is None:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "registered python command cannot be resolved through PATH"
        )
    command_path = Path(command).resolve(strict=True)
    executable_path = executable.resolve(strict=True)
    if command_path != executable_path:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "registered python3 command does not resolve to this interpreter"
        )
    libdir = sysconfig.get_config_var("LIBDIR")
    ld_library = sysconfig.get_config_var("LDLIBRARY")
    if type(libdir) is not str or type(ld_library) is not str:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "interpreter shared-library build fields are missing"
        )
    library_path = Path(libdir, ld_library)
    stdlib_count, stdlib_digest = _stdlib_tree()
    version = sys.version_info
    libc_name, libc_version = platform.libc_ver()
    return {
        "schema": "acfqp.v072_interpreter_build_identity.v1",
        "schema_version": SCHEMA_VERSION,
        "implementation_name": sys.implementation.name,
        "implementation_cache_tag": sys.implementation.cache_tag,
        "implementation_version": {
            "major": version.major,
            "minor": version.minor,
            "micro": version.micro,
            "releaselevel": version.releaselevel,
            "serial": version.serial,
        },
        "sys_version": sys.version,
        "hexversion": sys.hexversion,
        "api_version": sys.api_version,
        "byteorder": sys.byteorder,
        "maxsize": sys.maxsize,
        "abiflags": getattr(sys, "abiflags", ""),
        "soabi": sysconfig.get_config_var("SOABI"),
        "multiarch": sysconfig.get_config_var("MULTIARCH"),
        "sysconfig_platform": sysconfig.get_platform(),
        "python_build": list(platform.python_build()),
        "python_compiler": platform.python_compiler(),
        "config_args": sysconfig.get_config_var("CONFIG_ARGS"),
        "cc": sysconfig.get_config_var("CC"),
        "executable": _absolute_file_record(executable_path),
        "registered_command_resolves_to_active_interpreter": True,
        "shared_library": _absolute_file_record(library_path),
        "stdlib": {
            "file_count": stdlib_count,
            "tree_digest": stdlib_digest,
        },
        "host_abi": {
            "system": platform.system(),
            "machine": platform.machine(),
            "libc_name": libc_name,
            "libc_version": libc_version,
        },
    }


def _interpreter_build_document() -> dict[str, Any]:
    payload = _interpreter_build_payload()
    return {
        **payload,
        "interpreter_build_identity_id": _content_id(
            INTERPRETER_BUILD_DOMAIN,
            payload,
        ),
    }


def _runtime_lock_payload(root: Path) -> dict[str, Any]:
    project = _project_configuration(root)
    plugins = _pytest_plugin_roots()
    roots = _requirement_roots(project, plugins)
    distributions, edges, unresolved = _dependency_closure(roots)
    interpreter = _interpreter_build_document()
    requires_python = SpecifierSet(project["requires_python"])
    version_text = (
        f"{sys.version_info.major}."
        f"{sys.version_info.minor}."
        f"{sys.version_info.micro}"
    )
    if version_text not in requires_python:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "active interpreter violates project requires-python"
        )
    return {
        "schema": "acfqp.v072_runtime_dependency_lock.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": "v072_runtime_dependency_lock_v1",
        "pyproject": _repo_file_record(root, PYPROJECT_PATH),
        "project_configuration": project,
        "requirement_roots": roots,
        "pytest11_autoload_plugins": plugins,
        "locked_distributions": distributions,
        "active_dependency_edges": edges,
        "unresolved_declared_requirements": unresolved,
        "interpreter_build_identity": interpreter,
        "implementation_files": [
            _repo_file_record(root, path)
            for path in IMPLEMENTATION_PATHS
        ],
        "caller_supplied_digest_accepted": False,
        "caller_supplied_status_accepted": False,
        "executes_package_installer": False,
        "executes_tests": False,
        "target_access": False,
    }


def build_expected_runtime_dependency_lock_document_v1(
    repository_root: str | os.PathLike[str],
) -> dict[str, Any]:
    """Derive the runtime lock from the current interpreter and installs."""

    payload = _runtime_lock_payload(_repo_root(repository_root))
    return {
        **payload,
        "runtime_dependency_lock_id": _content_id(
            RUNTIME_LOCK_DOMAIN,
            payload,
        ),
    }


def render_expected_runtime_dependency_lock_spec_v1(
    repository_root: str | os.PathLike[str],
) -> bytes:
    return _render_spec(
        build_expected_runtime_dependency_lock_document_v1(
            repository_root
        )
    )


@dataclass(frozen=True, slots=True)
class ConfirmatoryTestCommandManifestV1:
    """Exact command/test-tree identity minted only after local replay."""

    _issuer: object = field(repr=False)
    _document_json: bytes = field(repr=False)
    spec_file_sha256: str
    spec_file_byte_count: int

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self._document_json) is not bytes
            or not _SHA256_PATTERN.fullmatch(self.spec_file_sha256)
            or type(self.spec_file_byte_count) is not int
            or self.spec_file_byte_count <= 0
        ):
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                "test-command authority was not internally replay-minted"
            )
        document = self.to_document()
        parse_content_id(document.get("test_command_manifest_id"))

    @property
    def test_command_manifest_id(self) -> str:
        return self.to_document()["test_command_manifest_id"]

    @property
    def exact_test_command(self) -> tuple[str, ...]:
        return tuple(self.to_document()["invocation"]["argv"])

    @property
    def deterministic_environment_settings(
        self,
    ) -> tuple[tuple[str, str], ...]:
        return tuple(
            (item["name"], item["value"])
            for item in self.to_document()["invocation"][
                "deterministic_environment"
            ]
        )

    def to_document(self) -> dict[str, Any]:
        document = json.loads(self._document_json)
        if type(document) is not dict:
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                "test-command authority document is not an object"
            )
        return document


@dataclass(frozen=True, slots=True)
class InterpreterBuildIdentityV1:
    """Exact running-interpreter build identity nested in the runtime lock."""

    _issuer: object = field(repr=False)
    _document_json: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self._document_json) is not bytes:
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                "interpreter authority was not internally replay-minted"
            )
        parse_content_id(self.interpreter_build_identity_id)

    @property
    def interpreter_build_identity_id(self) -> str:
        return self.to_document()["interpreter_build_identity_id"]

    def to_document(self) -> dict[str, Any]:
        document = json.loads(self._document_json)
        if type(document) is not dict:
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                "interpreter authority document is not an object"
            )
        return document


@dataclass(frozen=True, slots=True)
class RuntimeDependencyLockV1:
    """Exact installed dependency and interpreter binding."""

    _issuer: object = field(repr=False)
    _document_json: bytes = field(repr=False)
    spec_file_sha256: str
    spec_file_byte_count: int
    interpreter_build_identity: InterpreterBuildIdentityV1

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self._document_json) is not bytes
            or not _SHA256_PATTERN.fullmatch(self.spec_file_sha256)
            or type(self.spec_file_byte_count) is not int
            or self.spec_file_byte_count <= 0
            or type(self.interpreter_build_identity)
            is not InterpreterBuildIdentityV1
        ):
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                "runtime-lock authority was not internally replay-minted"
            )
        document = self.to_document()
        parse_content_id(document.get("runtime_dependency_lock_id"))
        if (
            document["interpreter_build_identity"]
            != self.interpreter_build_identity.to_document()
        ):
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                "runtime lock and interpreter authority diverge"
            )

    @property
    def runtime_dependency_lock_id(self) -> str:
        return self.to_document()["runtime_dependency_lock_id"]

    def to_document(self) -> dict[str, Any]:
        document = json.loads(self._document_json)
        if type(document) is not dict:
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                "runtime-lock authority document is not an object"
            )
        return document


@dataclass(frozen=True, slots=True)
class V072ExecutionEnvironmentAuthoritiesV1:
    test_command_manifest: ConfirmatoryTestCommandManifestV1
    runtime_dependency_lock: RuntimeDependencyLockV1
    interpreter_build_identity: InterpreterBuildIdentityV1

    def __post_init__(self) -> None:
        if (
            type(self.test_command_manifest)
            is not ConfirmatoryTestCommandManifestV1
            or type(self.runtime_dependency_lock)
            is not RuntimeDependencyLockV1
            or type(self.interpreter_build_identity)
            is not InterpreterBuildIdentityV1
            or self.runtime_dependency_lock.interpreter_build_identity
            is not self.interpreter_build_identity
        ):
            raise V072ExecutionEnvironmentAuthorityInvariantViolation(
                "execution-environment authority bundle is malformed"
            )


def freeze_v072_execution_environment_authorities_v1(
    repository_root: str | os.PathLike[str],
) -> V072ExecutionEnvironmentAuthoritiesV1:
    """Replay both specs and mint the three exact typed authorities."""

    root = _repo_root(repository_root)
    expected_test = (
        build_expected_confirmatory_test_command_document_v1(root)
    )
    claimed_test, test_bytes = _load_spec(root, TEST_COMMAND_SPEC_PATH)
    if claimed_test != expected_test:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "test-command spec differs from current command or test bytes"
        )

    expected_runtime = (
        build_expected_runtime_dependency_lock_document_v1(root)
    )
    claimed_runtime, runtime_bytes = _load_spec(
        root,
        RUNTIME_LOCK_SPEC_PATH,
    )
    if claimed_runtime != expected_runtime:
        raise V072ExecutionEnvironmentAuthorityInvariantViolation(
            "runtime lock differs from current dependencies or interpreter"
        )

    test_authority = ConfirmatoryTestCommandManifestV1(
        _ISSUER,
        canonical_json_bytes(expected_test),
        _sha256(test_bytes),
        len(test_bytes),
    )
    interpreter = InterpreterBuildIdentityV1(
        _ISSUER,
        canonical_json_bytes(
            expected_runtime["interpreter_build_identity"]
        ),
    )
    runtime_authority = RuntimeDependencyLockV1(
        _ISSUER,
        canonical_json_bytes(expected_runtime),
        _sha256(runtime_bytes),
        len(runtime_bytes),
        interpreter,
    )
    return V072ExecutionEnvironmentAuthoritiesV1(
        test_authority,
        runtime_authority,
        interpreter,
    )


__all__ = [
    "ConfirmatoryTestCommandManifestV1",
    "DETERMINISTIC_ENVIRONMENT_SETTINGS",
    "EXACT_TEST_COMMAND",
    "IMPLEMENTATION_PATHS",
    "INDEPENDENT_IMPLEMENTATION_PATH",
    "INNER_TEST_COMMAND",
    "InterpreterBuildIdentityV1",
    "PRODUCTION_IMPLEMENTATION_PATH",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RUNTIME_LOCK_SPEC_PATH",
    "RuntimeDependencyLockV1",
    "SCHEMA_VERSION",
    "SPEC_GENERATOR_PATH",
    "TEST_COMMAND_SPEC_PATH",
    "TEST_WRAPPER_PATH",
    "V072ExecutionEnvironmentAuthoritiesV1",
    "V072ExecutionEnvironmentAuthorityInvariantViolation",
    "build_expected_confirmatory_test_command_document_v1",
    "build_expected_runtime_dependency_lock_document_v1",
    "freeze_v072_execution_environment_authorities_v1",
    "render_expected_confirmatory_test_command_spec_v1",
    "render_expected_runtime_dependency_lock_spec_v1",
]
