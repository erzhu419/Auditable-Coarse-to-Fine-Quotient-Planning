"""Separately implemented replay of the V0-072 execution environment.

This verifier does not call the production environment builder, its private
helpers, or its freeze function.  It reads repository files and interpreter
metadata again, reconstructs the test/dependency/interpreter documents with
an independent implementation, and compares all semantic content IDs.
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

from acfqp import v072_execution_environment_authority_v1 as production

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 lane.
    import tomli as tomllib  # type: ignore[no-redef]


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_execution_environment_independent_verifier_v1"

_TEST_SPEC = "specs/V072_CONFIRMATORY_TEST_COMMAND.json"
_RUNTIME_SPEC = "specs/V072_RUNTIME_DEPENDENCY_LOCK.json"
_PYPROJECT = "pyproject.toml"
_TEST_ROOT = "tests"
_IMPLEMENTATIONS = (
    "src/acfqp/v072_execution_environment_authority_v1.py",
    "src/acfqp/v072_execution_environment_independent_verifier_v1.py",
    "scripts/generate_v072_execution_environment_specs.py",
    "scripts/run_v072_confirmatory_tests.py",
    "scripts/run_pytest_parallel.py",
)
_COMMAND = (
    "python3",
    "scripts/run_v072_confirmatory_tests.py",
)
_INNER_COMMAND = (
    "python3",
    "scripts/run_pytest_parallel.py",
    "-j",
    "32",
    "--fresh-ids",
    "--no-timing-cache",
    "tests",
)
_ENVIRONMENT = (
    ("LC_ALL", "C.UTF-8"),
    ("PYTHONDONTWRITEBYTECODE", "1"),
    ("PYTHONHASHSEED", "0"),
)

_TEST_DOMAIN = "acfqp:v072-confirmatory-test-command-manifest:v1"
_TEST_TREE_DOMAIN = "acfqp:v072-confirmatory-test-tree:v1"
_RUNTIME_DOMAIN = "acfqp:v072-runtime-dependency-lock:v1"
_INTERPRETER_DOMAIN = "acfqp:v072-interpreter-build-identity:v1"
_DISTRIBUTION_TREE_DOMAIN = (
    "acfqp:v072-installed-distribution-tree:v1"
)
_STDLIB_TREE_DOMAIN = "acfqp:v072-interpreter-stdlib-tree:v1"
_ATTESTATION_DOMAIN = (
    "acfqp:v072-execution-environment-independent-attestation:v1"
)

_ID_PATTERN = re.compile(r"[0-9a-f]{64}")
_ATTESTATION_ISSUER = object()


class V072ExecutionEnvironmentIndependentVerificationFailure(ValueError):
    """Independent replay rejected a spec, environment, or claimed object."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent canonical JSON encoding failed"
        ) from error


def _id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + _canonical_bytes(dict(payload))
    ).hexdigest()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _root(value: str | os.PathLike[str]) -> Path:
    root = Path(value)
    if not root.is_dir() or root.is_symlink():
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent repository root is absent or linked"
        )
    return root.resolve(strict=True)


def _repo_file(root: Path, relative_text: str) -> Path:
    if (
        type(relative_text) is not str
        or not relative_text
        or "\\" in relative_text
        or "\x00" in relative_text
    ):
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent repository path is malformed"
        )
    relative = PurePosixPath(relative_text)
    if (
        relative.is_absolute()
        or str(relative) != relative_text
        or any(part in ("", ".", "..") for part in relative.parts)
    ):
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent repository path traverses or is noncanonical"
        )
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise V072ExecutionEnvironmentIndependentVerificationFailure(
                "independent repository path contains a symlink"
            )
    try:
        resolved = cursor.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as error:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent repository path is absent or escapes"
        ) from error
    if not resolved.is_file():
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent repository path is not a regular file"
        )
    return resolved


def _read(path: Path, *, linked_target: bool = False) -> bytes:
    if path.is_symlink() and not linked_target:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent evidence path is linked"
        )
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW") and not linked_target:
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise V072ExecutionEnvironmentIndependentVerificationFailure(
                "independent evidence descriptor is not regular"
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
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent evidence changed during replay"
        )
    data = b"".join(chunks)
    if len(data) != after.st_size:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent evidence byte count changed"
        )
    return data


def _file_record(root: Path, relative: str) -> dict[str, Any]:
    data = _read(_repo_file(root, relative))
    return {
        "repository_relative_path": relative,
        "sha256_file_bytes": _sha(data),
        "file_byte_count": len(data),
    }


def _pretty(document: Mapping[str, Any]) -> bytes:
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


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise V072ExecutionEnvironmentIndependentVerificationFailure(
                "independent spec replay found a duplicate JSON key"
            )
        output[key] = value
    return output


def _reject_constant(token: str) -> Any:
    raise V072ExecutionEnvironmentIndependentVerificationFailure(
        f"independent spec replay found non-finite {token}"
    )


def _spec(root: Path, relative: str) -> tuple[dict[str, Any], bytes]:
    data = _read(_repo_file(root, relative))
    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique,
            parse_constant=_reject_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        V072ExecutionEnvironmentIndependentVerificationFailure,
    ) as error:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent spec parsing failed"
        ) from error
    if type(value) is not dict or _pretty(value) != data:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent spec bytes are not canonical pretty JSON"
        )
    return value, data


def _tree_id(domain: str, records: list[dict[str, Any]]) -> str:
    return _id(
        domain,
        {
            "schema": "acfqp.v072_ordered_file_tree.v1",
            "schema_version": SCHEMA_VERSION,
            "records": records,
        },
    )


def _independent_test_document(root: Path) -> dict[str, Any]:
    tests_root = root / _TEST_ROOT
    if not tests_root.is_dir() or tests_root.is_symlink():
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent registered test root is missing or linked"
        )
    relative_tests = sorted(
        candidate.relative_to(root).as_posix()
        for candidate in tests_root.rglob("*.py")
    )
    if not relative_tests or len(relative_tests) != len(set(relative_tests)):
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent test enumeration is empty or aliased"
        )
    test_records = [_file_record(root, path) for path in relative_tests]
    payload = {
        "schema": "acfqp.v072_confirmatory_test_command_manifest.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "1.36.0",
        "profile_key": "v072_confirmatory_test_command_manifest_v1",
        "invocation": {
            "argv": list(_COMMAND),
            "inner_argv": list(_INNER_COMMAND),
            "shell": False,
            "working_directory": "REPOSITORY_ROOT",
            "collection_root": _TEST_ROOT,
            "deterministic_environment": [
                {"name": name, "value": value}
                for name, value in _ENVIRONMENT
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
        "pytest_configuration": _file_record(root, _PYPROJECT),
        "test_tree": {
            "selection": "tests/**/*.py",
            "test_file_count": len(test_records),
            "test_tree_digest": _tree_id(
                _TEST_TREE_DOMAIN,
                test_records,
            ),
        },
        "implementation_files": [
            _file_record(root, path) for path in _IMPLEMENTATIONS
        ],
        "caller_supplied_digest_accepted": False,
        "caller_supplied_status_accepted": False,
        "executes_tests": False,
        "target_access": False,
    }
    return {
        **payload,
        "test_command_manifest_id": _id(_TEST_DOMAIN, payload),
    }


def _project(root: Path) -> dict[str, Any]:
    raw = _read(_repo_file(root, _PYPROJECT))
    try:
        value = tomllib.loads(raw.decode("utf-8", errors="strict"))
        project = value["project"]
        build = value["build-system"]
        pytest_options = value["tool"]["pytest"]["ini_options"]
        record = {
            "requires_python": project["requires-python"],
            "project_dependencies": list(project["dependencies"]),
            "test_dependencies": list(
                project["optional-dependencies"]["test"]
            ),
            "build_dependencies": list(build["requires"]),
            "pytest_pythonpath": list(pytest_options["pythonpath"]),
            "pytest_testpaths": list(pytest_options["testpaths"]),
        }
    except (
        UnicodeDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent pyproject replay failed"
        ) from error
    if (
        record["pytest_pythonpath"] != [".", "src"]
        or record["pytest_testpaths"] != [_TEST_ROOT]
        or any(
            type(item) is not str
            for name, values in record.items()
            if name != "requires_python"
            for item in values
        )
        or type(record["requires_python"]) is not str
    ):
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent pyproject semantics differ"
        )
    return record


def _plugins() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for entry in metadata.entry_points(group="pytest11"):
        if entry.dist is None:
            raise V072ExecutionEnvironmentIndependentVerificationFailure(
                "independent pytest plugin has no distribution"
            )
        output.append(
            {
                "entry_point_name": entry.name,
                "entry_point_value": entry.value,
                "distribution_name": canonicalize_name(
                    entry.dist.metadata["Name"]
                ),
                "distribution_version": entry.dist.version,
            }
        )
    output.sort(
        key=lambda item: (
            item["entry_point_name"],
            item["entry_point_value"],
            item["distribution_name"],
        )
    )
    if len(output) != len(
        {
            (
                item["entry_point_name"],
                item["entry_point_value"],
                item["distribution_name"],
            )
            for item in output
        }
    ):
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent pytest plugin registry aliases entries"
        )
    return output


def _roots(
    project: Mapping[str, Any],
    plugins: list[dict[str, Any]],
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for source, field_name in (
        ("project.dependencies", "project_dependencies"),
        (
            "project.optional-dependencies.test",
            "test_dependencies",
        ),
        ("build-system.requires", "build_dependencies"),
    ):
        output.extend(
            {"source": source, "requirement": requirement}
            for requirement in project[field_name]
        )
    output.extend(
        {
            "source": (
                f"environment.pytest11:{plugin['entry_point_name']}"
            ),
            "requirement": (
                f"{plugin['distribution_name']}=="
                f"{plugin['distribution_version']}"
            ),
        }
        for plugin in plugins
    )
    output.sort(key=lambda item: (item["source"], item["requirement"]))
    return output


def _distribution_tree(
    distribution: metadata.Distribution,
) -> tuple[int, str]:
    paths = distribution.files
    if not paths:
        top_level = distribution.read_text("top_level.txt")
        if type(top_level) is not str or not top_level.strip():
            raise V072ExecutionEnvironmentIndependentVerificationFailure(
                "independent distribution has no indexed/top-level files"
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
                raise V072ExecutionEnvironmentIndependentVerificationFailure(
                    "independent top-level distribution package is absent"
                )
        base = Path(distribution.locate_file(""))
        paths = tuple(
            PurePosixPath(item.relative_to(base).as_posix())
            for item in discovered
        )
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in sorted(paths, key=lambda row: str(row)):
        relative = str(item).replace("\\", "/")
        if relative in seen:
            raise V072ExecutionEnvironmentIndependentVerificationFailure(
                "independent distribution index duplicates a path"
            )
        seen.add(relative)
        if (
            "/__pycache__/" in f"/{relative}/"
            or relative.endswith((".pyc", ".pyo"))
        ):
            continue
        candidate = Path(distribution.locate_file(item))
        if candidate.is_symlink():
            resolved = candidate.resolve(strict=True)
            data = _read(resolved)
            records.append(
                {
                    "distribution_relative_path": relative,
                    "kind": "SYMLINK",
                    "link_target": os.readlink(candidate),
                    "resolved_sha256_file_bytes": _sha(data),
                    "resolved_file_byte_count": len(data),
                }
            )
        elif candidate.is_file():
            data = _read(candidate)
            records.append(
                {
                    "distribution_relative_path": relative,
                    "kind": "REGULAR_FILE",
                    "sha256_file_bytes": _sha(data),
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
    return len(records), _tree_id(_DISTRIBUTION_TREE_DOMAIN, records)


def _distribution(name: str) -> dict[str, Any]:
    canonical = canonicalize_name(name)
    try:
        installed = metadata.distribution(canonical)
    except metadata.PackageNotFoundError as error:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent locked distribution disappeared"
        ) from error
    metadata_kind = "METADATA"
    metadata_text = installed.read_text(metadata_kind)
    if metadata_text is None:
        metadata_kind = "PKG-INFO"
        metadata_text = installed.read_text(metadata_kind)
    wheel_text = installed.read_text("WHEEL")
    if metadata_text is None:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent distribution metadata is incomplete"
        )
    metadata_bytes = metadata_text.encode("utf-8")
    if wheel_text is None:
        wheel_record: dict[str, Any] = {"kind": "NOT_PRESENT"}
    else:
        wheel_bytes = wheel_text.encode("utf-8")
        wheel_record = {
            "kind": "PRESENT",
            "sha256_file_bytes": _sha(wheel_bytes),
            "file_byte_count": len(wheel_bytes),
        }
    count, tree_digest = _distribution_tree(installed)
    installer = installed.read_text("INSTALLER")
    direct_url = installed.read_text("direct_url.json")
    return {
        "normalized_name": canonical,
        "declared_name": installed.metadata["Name"],
        "version": installed.version,
        "metadata_kind": metadata_kind,
        "metadata_sha256": _sha(metadata_bytes),
        "metadata_byte_count": len(metadata_bytes),
        "wheel_metadata": wheel_record,
        "installed_file_count": count,
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


def _closure(
    roots: list[dict[str, str]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, str]],
    list[dict[str, str]],
]:
    marker_environment = default_environment()
    marker_environment["extra"] = ""
    queue = [("<ROOT>", item["requirement"]) for item in roots]
    visited: set[str] = set()
    edges: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []
    while queue:
        parent, raw = queue.pop(0)
        try:
            requirement = Requirement(raw)
        except ValueError as error:
            raise V072ExecutionEnvironmentIndependentVerificationFailure(
                "independent dependency requirement is invalid"
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
                    "requirement": raw,
                    "child_distribution": child,
                }
            )
        try:
            installed = metadata.distribution(child)
        except metadata.PackageNotFoundError:
            unresolved.append(
                {
                    "parent_distribution": parent,
                    "requirement": raw,
                    "child_distribution": child,
                    "reason": "MISSING_DISTRIBUTION",
                }
            )
            continue
        if requirement.specifier and installed.version not in requirement.specifier:
            unresolved.append(
                {
                    "parent_distribution": parent,
                    "requirement": raw,
                    "child_distribution": child,
                    "reason": "VERSION_OUTSIDE_SPECIFIER",
                }
            )
        if child in visited:
            continue
        visited.add(child)
        for dependency in installed.requires or ():
            parsed = Requirement(dependency)
            if (
                parsed.marker is None
                or parsed.marker.evaluate(marker_environment)
            ):
                queue.append((child, dependency))
    distributions = [_distribution(name) for name in sorted(visited)]
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


def _absolute_record(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    data = _read(resolved)
    return {
        "sha256_file_bytes": _sha(data),
        "file_byte_count": len(data),
    }


def _stdlib() -> tuple[int, str]:
    root = Path(sysconfig.get_path("stdlib")).resolve(strict=True)
    records: list[dict[str, Any]] = []
    for candidate in sorted(
        root.rglob("*"),
        key=lambda path: path.relative_to(root).as_posix(),
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
            data = _read(resolved)
            records.append(
                {
                    "stdlib_relative_path": relative,
                    "kind": "SYMLINK",
                    "link_target": os.readlink(candidate),
                    "resolved_sha256_file_bytes": _sha(data),
                    "resolved_file_byte_count": len(data),
                }
            )
        elif candidate.is_file():
            data = _read(candidate)
            records.append(
                {
                    "stdlib_relative_path": relative,
                    "kind": "REGULAR_FILE",
                    "sha256_file_bytes": _sha(data),
                    "file_byte_count": len(data),
                }
            )
    if not records:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent stdlib tree is empty"
        )
    return len(records), _tree_id(_STDLIB_TREE_DOMAIN, records)


def _interpreter() -> dict[str, Any]:
    command = shutil.which(_INNER_COMMAND[0])
    if command is None:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent python3 resolution failed"
        )
    executable = Path(sys.executable).resolve(strict=True)
    command_path = Path(command).resolve(strict=True)
    if executable != command_path:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent command/interpreter identities differ"
        )
    libdir = sysconfig.get_config_var("LIBDIR")
    library = sysconfig.get_config_var("LDLIBRARY")
    if type(libdir) is not str or type(library) is not str:
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent interpreter library identity is missing"
        )
    stdlib_count, stdlib_digest = _stdlib()
    version = sys.version_info
    libc_name, libc_version = platform.libc_ver()
    payload = {
        "schema": "acfqp.v072_interpreter_build_identity.v1",
        "schema_version": "1.0.0",
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
        "executable": _absolute_record(executable),
        "registered_command_resolves_to_active_interpreter": True,
        "shared_library": _absolute_record(Path(libdir, library)),
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
    return {
        **payload,
        "interpreter_build_identity_id": _id(
            _INTERPRETER_DOMAIN,
            payload,
        ),
    }


def _independent_runtime_document(root: Path) -> dict[str, Any]:
    project = _project(root)
    plugins = _plugins()
    roots = _roots(project, plugins)
    distributions, edges, unresolved = _closure(roots)
    interpreter = _interpreter()
    current_version = (
        f"{sys.version_info.major}."
        f"{sys.version_info.minor}."
        f"{sys.version_info.micro}"
    )
    if current_version not in SpecifierSet(project["requires_python"]):
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent interpreter violates requires-python"
        )
    payload = {
        "schema": "acfqp.v072_runtime_dependency_lock.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "1.36.0",
        "profile_key": "v072_runtime_dependency_lock_v1",
        "pyproject": _file_record(root, _PYPROJECT),
        "project_configuration": project,
        "requirement_roots": roots,
        "pytest11_autoload_plugins": plugins,
        "locked_distributions": distributions,
        "active_dependency_edges": edges,
        "unresolved_declared_requirements": unresolved,
        "interpreter_build_identity": interpreter,
        "implementation_files": [
            _file_record(root, path) for path in _IMPLEMENTATIONS
        ],
        "caller_supplied_digest_accepted": False,
        "caller_supplied_status_accepted": False,
        "executes_package_installer": False,
        "executes_tests": False,
        "target_access": False,
    }
    return {
        **payload,
        "runtime_dependency_lock_id": _id(_RUNTIME_DOMAIN, payload),
    }


@dataclass(frozen=True, slots=True)
class IndependentExecutionEnvironmentAttestationV1:
    _issuer: object = field(repr=False)
    test_command_manifest_id: str
    runtime_dependency_lock_id: str
    interpreter_build_identity_id: str
    test_spec_sha256: str
    runtime_spec_sha256: str

    def __post_init__(self) -> None:
        if self._issuer is not _ATTESTATION_ISSUER or any(
            _ID_PATTERN.fullmatch(value) is None
            for value in (
                self.test_command_manifest_id,
                self.runtime_dependency_lock_id,
                self.interpreter_build_identity_id,
                self.test_spec_sha256,
                self.runtime_spec_sha256,
            )
        ):
            raise V072ExecutionEnvironmentIndependentVerificationFailure(
                "independent environment attestation was not replay-minted"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_execution_environment_independent_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "test_command_manifest_id": self.test_command_manifest_id,
            "runtime_dependency_lock_id": self.runtime_dependency_lock_id,
            "interpreter_build_identity_id": (
                self.interpreter_build_identity_id
            ),
            "test_spec_sha256": self.test_spec_sha256,
            "runtime_spec_sha256": self.runtime_spec_sha256,
            "production_builder_called": False,
            "caller_supplied_digest_accepted": False,
            "caller_supplied_status_accepted": False,
            "target_access": False,
        }

    @property
    def attestation_id(self) -> str:
        return _id(_ATTESTATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


def verify_execution_environment_authorities_independently_v1(
    repository_root: str | os.PathLike[str],
    authorities: production.V072ExecutionEnvironmentAuthoritiesV1,
) -> IndependentExecutionEnvironmentAttestationV1:
    """Recompute every environment fact without calling production replay."""

    if (
        type(authorities)
        is not production.V072ExecutionEnvironmentAuthoritiesV1
        or type(authorities.test_command_manifest)
        is not production.ConfirmatoryTestCommandManifestV1
        or type(authorities.runtime_dependency_lock)
        is not production.RuntimeDependencyLockV1
        or type(authorities.interpreter_build_identity)
        is not production.InterpreterBuildIdentityV1
    ):
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent verifier requires exact production artifact types"
        )
    root = _root(repository_root)
    expected_test = _independent_test_document(root)
    expected_runtime = _independent_runtime_document(root)
    claimed_test_spec, test_bytes = _spec(root, _TEST_SPEC)
    claimed_runtime_spec, runtime_bytes = _spec(root, _RUNTIME_SPEC)

    if (
        claimed_test_spec != expected_test
        or claimed_runtime_spec != expected_runtime
        or authorities.test_command_manifest.to_document()
        != expected_test
        or authorities.runtime_dependency_lock.to_document()
        != expected_runtime
        or authorities.interpreter_build_identity.to_document()
        != expected_runtime["interpreter_build_identity"]
        or authorities.test_command_manifest.spec_file_sha256
        != _sha(test_bytes)
        or authorities.test_command_manifest.spec_file_byte_count
        != len(test_bytes)
        or authorities.runtime_dependency_lock.spec_file_sha256
        != _sha(runtime_bytes)
        or authorities.runtime_dependency_lock.spec_file_byte_count
        != len(runtime_bytes)
        or authorities.runtime_dependency_lock.interpreter_build_identity
        is not authorities.interpreter_build_identity
    ):
        raise V072ExecutionEnvironmentIndependentVerificationFailure(
            "independent replay differs from checked-in or typed authorities"
        )

    return IndependentExecutionEnvironmentAttestationV1(
        _ATTESTATION_ISSUER,
        expected_test["test_command_manifest_id"],
        expected_runtime["runtime_dependency_lock_id"],
        expected_runtime["interpreter_build_identity"][
            "interpreter_build_identity_id"
        ],
        _sha(test_bytes),
        _sha(runtime_bytes),
    )


__all__ = [
    "IndependentExecutionEnvironmentAttestationV1",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "V072ExecutionEnvironmentIndependentVerificationFailure",
    "verify_execution_environment_authorities_independently_v1",
]
