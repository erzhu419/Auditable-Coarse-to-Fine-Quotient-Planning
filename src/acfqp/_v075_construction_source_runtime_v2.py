"""Private construction source/runtime primitives for portable V0-075.

This module deliberately exposes only inert construction operations:

* derive the recursive static ACFQP import closure of multiple root modules
  from caller-supplied source bytes;
* bind those bytes to regular, symlink-free files when paths are supplied;
* encode and independently replay one deterministic ``ZIP_STORED`` archive;
* validate the tracked V0-075 dependency lock against ``/usr/bin/python3``;
  and
* compile every exact source archive member in a ``/usr/bin/python3 -I -S``
  child without ever importing or executing tested source code.

It has no campaign, observer, production, certificate, or environment-law
entrypoint.  The records issued here are construction evidence only.
"""

from __future__ import annotations

import ast
from dataclasses import InitVar, dataclass, field
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
from typing import Any, Mapping, NoReturn
import zipfile

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "2.0.0"
PROFILE_KEY = "v075_construction_source_runtime_v2"
PYTHON_EXECUTABLE = "/usr/bin/python3"
ARCHIVE_FORMAT = "DETERMINISTIC_ZIP_STORED_V2"
STATIC_CLOSURE_RULE = "RECURSIVE_STATIC_MULTIROOT_LOCAL_ACFQP_IMPORTS"
MAX_MODULES = 1024
MAX_SOURCE_BYTES_PER_MODULE = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_CHILD_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_CHILD_STDERR_BYTES = 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 300
MAX_TIMEOUT_SECONDS = 3600
DEPENDENCY_LOCK_SCHEMA = "acfqp.v075_runtime_dependency_lock.v1"
DEPENDENCY_LOCK_PROFILE = (
    "v075_stdlib_runtime_and_exact_test_dependency_lock_v1"
)
DEPENDENCY_LOCK_MODEL = (
    "PYTHON_STDLIB_PLUS_TRACKED_ACFQP_COMPONENT_BLOBS"
)

_DOMAINS = {
    "source_module": "acfqp:v075-construction-source-module:v2",
    "source_closure": "acfqp:v075-construction-source-closure:v2",
    "source_archive": "acfqp:v075-construction-source-archive:v2",
    "runtime_lock": "acfqp:v075-construction-runtime-lock-verification:v2",
    "archive_compile": (
        "acfqp:v075-construction-sealed-archive-compile-verification:v2"
    ),
}
_DEPENDENCY_LOCK_DOMAIN = "acfqp:v075-runtime-dependency-lock:v1"
_ISSUER = object()
_MFD_CLOEXEC = getattr(os, "MFD_CLOEXEC", 0x0001)
_MFD_ALLOW_SEALING = getattr(os, "MFD_ALLOW_SEALING", 0x0002)
_F_ADD_SEALS = 1033
_F_GET_SEALS = 1034
_F_SEAL_SEAL = 0x0001
_F_SEAL_SHRINK = 0x0002
_F_SEAL_GROW = 0x0004
_F_SEAL_WRITE = 0x0008
_REQUIRED_SEALS = (
    _F_SEAL_SEAL | _F_SEAL_SHRINK | _F_SEAL_GROW | _F_SEAL_WRITE
)

_LOCK_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "runtime_dependency_model",
    "runtime_third_party_distributions",
    "test_dependency_distributions",
    "interpreter",
    "project",
    "exact_test_command",
    "required_environment",
    "pytest_plugin_autoload_allowed",
    "package_installer_execution_allowed",
    "network_access_required",
    "caller_supplied_digest_accepted",
    "caller_supplied_status_accepted",
    "target_access",
    "runtime_dependency_lock_id",
}
_LOCK_INTERPRETER_KEYS = {
    "implementation",
    "version_info",
    "hexversion",
    "cache_tag",
    "soabi",
    "platform",
    "machine",
    "byteorder",
    "maxsize",
    "hash_algorithm",
    "hash_width",
    "hash_modulus",
    "compiler",
    "build",
    "config_args_sha256",
}
_LOCK_PROJECT_KEYS = {
    "name",
    "version",
    "requires_python",
    "declared_runtime_dependencies",
    "pyproject_sha256",
}
_LOCK_DISTRIBUTION_KEYS = {
    "name",
    "version",
    "metadata_sha256",
    "wheel_sha256",
}
_EXPECTED_TEST_COMMAND = [
    "python3",
    "-m",
    "pytest",
    "-q",
    "-s",
    "tests/test_v075_registered_campaign.py",
]
_EXPECTED_ENVIRONMENT = [
    {"name": "LC_ALL", "value": "C.UTF-8"},
    {"name": "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "value": "1"},
    {"name": "PYTHONDONTWRITEBYTECODE", "value": "1"},
    {"name": "PYTHONHASHSEED", "value": "0"},
    {"name": "TZ", "value": "UTC"},
]

_RUNTIME_PROBE = r"""
import hashlib
import importlib.metadata
import json
import platform
import sys
import sysconfig

def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

request_raw = sys.stdin.buffer.read()
request = json.loads(request_raw.decode("utf-8"))
if canonical(request) != request_raw:
    raise SystemExit(71)
if set(request) != {"distribution_names"}:
    raise SystemExit(72)
names = request["distribution_names"]
if (
    type(names) is not list
    or names != sorted(set(names))
    or any(type(name) is not str or not name for name in names)
):
    raise SystemExit(73)
distributions = []
for name in names:
    distribution = importlib.metadata.distribution(name)
    metadata = distribution.read_text("METADATA")
    wheel = distribution.read_text("WHEEL")
    if type(metadata) is not str or type(wheel) is not str:
        raise SystemExit(74)
    distributions.append(
        {
            "name": str(distribution.metadata["Name"])
                .lower().replace("_", "-"),
            "version": distribution.version,
            "metadata_sha256": hashlib.sha256(
                metadata.encode("utf-8")
            ).hexdigest(),
            "wheel_sha256": hashlib.sha256(
                wheel.encode("utf-8")
            ).hexdigest(),
        }
    )
result = {
    "executable": sys.executable,
    "interpreter": {
        "implementation": sys.implementation.name,
        "version_info": [
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
            sys.version_info.releaselevel,
            sys.version_info.serial,
        ],
        "hexversion": sys.hexversion,
        "cache_tag": sys.implementation.cache_tag,
        "soabi": sysconfig.get_config_var("SOABI"),
        "platform": sysconfig.get_platform(),
        "machine": platform.machine(),
        "byteorder": sys.byteorder,
        "maxsize": sys.maxsize,
        "hash_algorithm": sys.hash_info.algorithm,
        "hash_width": sys.hash_info.width,
        "hash_modulus": sys.hash_info.modulus,
        "compiler": platform.python_compiler(),
        "build": list(platform.python_build()),
        "config_args_sha256": hashlib.sha256(
            str(sysconfig.get_config_var("CONFIG_ARGS")).encode("utf-8")
        ).hexdigest(),
    },
    "test_dependency_distributions": distributions,
}
sys.stdout.buffer.write(canonical(result))
""".strip()

_SEALED_ARCHIVE_COMPILE_CHILD = r"""
import hashlib
import json
import sys
import zipfile

def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

request_raw = sys.stdin.buffer.read()
request = json.loads(request_raw.decode("utf-8"))
if canonical(request) != request_raw:
    raise SystemExit(81)
required_keys = {
    "archive_byte_count",
    "archive_path",
    "archive_sha256",
    "entries",
    "expected_module_names",
}
if set(request) != required_keys:
    raise SystemExit(82)
archive_path = request["archive_path"]
if (
    type(archive_path) is not str
    or archive_path != sys.argv[1]
    or type(request["archive_byte_count"]) is not int
    or type(request["archive_sha256"]) is not str
):
    raise SystemExit(83)
with open(archive_path, "rb") as handle:
    archive_raw = handle.read()
if (
    len(archive_raw) != request["archive_byte_count"]
    or hashlib.sha256(archive_raw).hexdigest()
    != request["archive_sha256"]
):
    raise SystemExit(84)
entries = request["entries"]
expected_names = request["expected_module_names"]
if (
    type(entries) is not list
    or type(expected_names) is not list
    or expected_names != sorted(set(expected_names))
    or [entry["module_name"] for entry in entries] != expected_names
):
    raise SystemExit(85)
compiled_entries = []
with zipfile.ZipFile(archive_path, "r") as archive:
    infos = archive.infolist()
    expected_paths = [entry["relative_path"] for entry in entries]
    if (
        len(infos) != len(entries)
        or [info.filename for info in infos] != sorted(expected_paths)
        or len(set(expected_paths)) != len(expected_paths)
    ):
        raise SystemExit(86)
    by_path = {entry["relative_path"]: entry for entry in entries}
    for info in infos:
        entry = by_path[info.filename]
        raw = archive.read(info)
        if (
            info.compress_type != zipfile.ZIP_STORED
            or info.date_time != (1980, 1, 1, 0, 0, 0)
            or len(raw) != entry["source_byte_count"]
            or hashlib.sha256(raw).hexdigest()
            != entry["source_sha256"]
        ):
            raise SystemExit(87)
        # Compile is the strongest trusted construction claim available here.
        # The resulting code object is deliberately discarded and never
        # executed, so archive members cannot forge this child result.
        compile(
            raw,
            "SEALED_CONSTRUCTION_SOURCE_ARCHIVE/" + info.filename,
            "exec",
            dont_inherit=True,
            optimize=0,
        )
        compiled_entries.append(
            {
                "module_name": entry["module_name"],
                "relative_path": entry["relative_path"],
                "source_byte_count": entry["source_byte_count"],
                "source_sha256": entry["source_sha256"],
            }
        )
before = sorted(
    name
    for name in sys.modules
    if name == "acfqp" or name.startswith("acfqp.")
)
if before:
    raise SystemExit(88)
if (
    sys.flags.isolated != 1
    or sys.flags.no_site != 1
    or sys.flags.ignore_environment != 1
    or (
        hasattr(sys.flags, "safe_path")
        and sys.flags.safe_path is not True
    )
):
    raise SystemExit(89)
if archive_path in sys.path:
    raise SystemExit(90)
after = sorted(
    name
    for name in sys.modules
    if name == "acfqp" or name.startswith("acfqp.")
)
if after:
    raise SystemExit(91)
result = {
    "archive_byte_count": request["archive_byte_count"],
    "archive_sha256": request["archive_sha256"],
    "before_acfqp_modules": before,
    "after_acfqp_modules": after,
    "compiled_entries": compiled_entries,
    "tested_source_execution_allowed": False,
    "archive_added_to_sys_path": False,
    "runtime_flags": {
        "isolated": sys.flags.isolated,
        "no_site": sys.flags.no_site,
        "ignore_environment": sys.flags.ignore_environment,
        "safe_path": (
            sys.flags.safe_path
            if hasattr(sys.flags, "safe_path")
            else "NOT_EXPOSED"
        ),
    },
}
sys.stdout.buffer.write(canonical(result))
""".strip()


class V075ConstructionSourceRuntimeV2InvariantViolation(ValueError):
    """A source, archive, runtime, lock, or isolated import invariant failed."""


def _fail(message: str) -> NoReturn:
    raise V075ConstructionSourceRuntimeV2InvariantViolation(message)


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = _DOMAINS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V075ConstructionSourceRuntimeV2InvariantViolation(
            "construction source/runtime identity is malformed"
        ) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _dependency_lock_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        _DEPENDENCY_LOCK_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ConstructionSourceRuntimeV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _strict_json_object(
    raw: bytes,
    *,
    label: str,
    byte_cap: int,
) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > byte_cap:
        _fail(f"{label} is empty, mistyped, or over its byte cap")

    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(f"{label} contains a duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=unique_pairs,
            parse_constant=lambda token: _fail(
                f"{label} contains forbidden numeric constant {token}"
            ),
        )
    except (
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
        if type(error) is V075ConstructionSourceRuntimeV2InvariantViolation:
            raise
        raise V075ConstructionSourceRuntimeV2InvariantViolation(
            f"{label} is not strict UTF-8 JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} is not one JSON object")
    try:
        canonical_json_bytes(value)
    except (TypeError, ValueError) as error:
        raise V075ConstructionSourceRuntimeV2InvariantViolation(
            f"{label} is outside canonical JSON"
        ) from error
    return value


def _module_relative_path(module_name: str, *, is_package: bool) -> str:
    base = module_name.replace(".", "/")
    return f"{base}/__init__.py" if is_package else f"{base}.py"


def _valid_module_name(value: Any) -> bool:
    if type(value) is not str or (
        value != "acfqp" and not value.startswith("acfqp.")
    ):
        return False
    return all(
        part.isidentifier() and not part.startswith("_abc_invalid_")
        for part in value.split(".")
    )


def _read_regular_symlink_free(path_value: str | os.PathLike[str]) -> bytes:
    try:
        path = Path(path_value)
    except TypeError as error:
        raise V075ConstructionSourceRuntimeV2InvariantViolation(
            "source path is not path-like"
        ) from error
    if not path.is_absolute():
        _fail("source path must be absolute")
    absolute = Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            item_stat = os.lstat(current)
        except OSError as error:
            raise V075ConstructionSourceRuntimeV2InvariantViolation(
                "source path component is absent"
            ) from error
        if stat.S_ISLNK(item_stat.st_mode):
            _fail("source path contains a symlink")
    try:
        fd = os.open(
            absolute,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as error:
        raise V075ConstructionSourceRuntimeV2InvariantViolation(
            "source path could not be opened without following symlinks"
        ) from error
    try:
        opened_stat = os.fstat(fd)
        if not stat.S_ISREG(opened_stat.st_mode):
            _fail("source path is not a regular file")
        chunks: list[bytes] = []
        remaining = MAX_SOURCE_BYTES_PER_MODULE + 1
        while remaining > 0:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if not raw or len(raw) > MAX_SOURCE_BYTES_PER_MODULE:
            _fail("source file is empty or over its byte cap")
        final_stat = os.fstat(fd)
        if (
            final_stat.st_dev != opened_stat.st_dev
            or final_stat.st_ino != opened_stat.st_ino
            or final_stat.st_size != len(raw)
        ):
            _fail("source file changed while it was read")
        return raw
    finally:
        os.close(fd)


def _absolute_import_base(
    *,
    current_module: str,
    current_is_package: bool,
    imported_module: str | None,
    level: int,
) -> str:
    if level == 0:
        return "" if imported_module is None else imported_module
    package = (
        current_module
        if current_is_package
        else current_module.rpartition(".")[0]
    )
    parts = package.split(".") if package else []
    if level > len(parts):
        return ""
    prefix = parts[: len(parts) - level + 1]
    if imported_module:
        prefix.extend(imported_module.split("."))
    return ".".join(prefix)


def _local_imports_from_raw(
    *,
    module_name: str,
    is_package: bool,
    raw: bytes,
    available_names: frozenset[str],
) -> tuple[str, ...]:
    try:
        tree = ast.parse(raw, filename=module_name)
    except (SyntaxError, TypeError, ValueError) as error:
        raise V075ConstructionSourceRuntimeV2InvariantViolation(
            f"source module could not be parsed: {module_name}"
        ) from error
    discovered: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                candidate = alias.name
                if candidate == "acfqp" or candidate.startswith("acfqp."):
                    if candidate not in available_names:
                        _fail(
                            "static ACFQP import is absent from supplied "
                            f"sources: {candidate}"
                        )
                    discovered.add(candidate)
        elif isinstance(node, ast.ImportFrom):
            base = _absolute_import_base(
                current_module=module_name,
                current_is_package=is_package,
                imported_module=node.module,
                level=node.level,
            )
            if base == "acfqp" or base.startswith("acfqp."):
                if base not in available_names:
                    _fail(
                        "static ACFQP import is absent from supplied "
                        f"sources: {base}"
                    )
                discovered.add(base)
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    candidate = f"{base}.{alias.name}"
                    if candidate in available_names:
                        discovered.add(candidate)
    return tuple(sorted(discovered))


@dataclass(frozen=True, slots=True)
class ConstructionSourceModuleV2:
    _issuer: InitVar[object]
    module_name: str
    relative_path: str
    is_package: bool
    source_sha256: str
    source_byte_count: int
    static_local_imports: tuple[str, ...]
    regular_file_verified: bool
    symlink_free_verified: bool
    _module_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.source_sha256, "construction source digest")
        if (
            _issuer is not _ISSUER
            or not _valid_module_name(self.module_name)
            or type(self.is_package) is not bool
            or self.relative_path
            != _module_relative_path(
                self.module_name,
                is_package=self.is_package,
            )
            or PurePosixPath(self.relative_path).is_absolute()
            or ".." in PurePosixPath(self.relative_path).parts
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
            or self.source_byte_count > MAX_SOURCE_BYTES_PER_MODULE
            or type(self.static_local_imports) is not tuple
            or self.static_local_imports
            != tuple(sorted(set(self.static_local_imports)))
            or any(
                not _valid_module_name(value)
                for value in self.static_local_imports
            )
            or self.regular_file_verified is not True
            or self.symlink_free_verified is not True
        ):
            _fail("construction source module is malformed or caller-minted")
        object.__setattr__(
            self,
            "_module_id",
            _content_id("source_module", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_construction_source_module.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "module_name": self.module_name,
            "relative_path": self.relative_path,
            "is_package": self.is_package,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
            "static_local_imports": list(self.static_local_imports),
            "regular_file_verified": self.regular_file_verified,
            "symlink_free_verified": self.symlink_free_verified,
        }

    @property
    def module_id(self) -> str:
        return self._module_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "module_id": self.module_id}


@dataclass(frozen=True, slots=True)
class ConstructionSourceClosureV2:
    _issuer: InitVar[object]
    root_modules: tuple[str, ...]
    modules: tuple[ConstructionSourceModuleV2, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        names = tuple(item.module_name for item in self.modules)
        present = frozenset(names)
        if (
            _issuer is not _ISSUER
            or type(self.root_modules) is not tuple
            or self.root_modules != tuple(sorted(set(self.root_modules)))
            or not self.root_modules
            or any(not _valid_module_name(value) for value in self.root_modules)
            or type(self.modules) is not tuple
            or not self.modules
            or len(self.modules) > MAX_MODULES
            or any(
                type(item) is not ConstructionSourceModuleV2
                for item in self.modules
            )
            or names != tuple(sorted(set(names)))
            or not set(self.root_modules) <= present
            or "acfqp" not in present
            or any(
                not set(item.static_local_imports) <= present
                for item in self.modules
            )
        ):
            _fail("construction source closure is incomplete or caller-minted")
        object.__setattr__(
            self,
            "_closure_id",
            _content_id("source_closure", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_construction_source_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "closure_rule": STATIC_CLOSURE_RULE,
            "root_modules": list(self.root_modules),
            "modules": [item.to_document() for item in self.modules],
            "module_ids": [item.module_id for item in self.modules],
            "module_count": len(self.modules),
            "all_sources_regular_files": True,
            "all_source_paths_symlink_free": True,
            "caller_supplied_source_bytes_replayed": True,
            "construction_only": True,
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    @property
    def module_names(self) -> tuple[str, ...]:
        return tuple(item.module_name for item in self.modules)

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}


@dataclass(frozen=True, slots=True)
class ConstructionSourceArchiveV2:
    _issuer: InitVar[object]
    source_closure_id: str
    entries: tuple[ConstructionSourceModuleV2, ...]
    archive_bytes: bytes = field(repr=False)
    archive_sha256: str
    archive_byte_count: int
    _archive_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.source_closure_id, "archive source closure")
        _cid(self.archive_sha256, "construction source archive")
        if (
            _issuer is not _ISSUER
            or type(self.entries) is not tuple
            or not self.entries
            or any(
                type(item) is not ConstructionSourceModuleV2
                for item in self.entries
            )
            or tuple(item.module_name for item in self.entries)
            != tuple(sorted(item.module_name for item in self.entries))
            or type(self.archive_bytes) is not bytes
            or not self.archive_bytes
            or len(self.archive_bytes) != self.archive_byte_count
            or len(self.archive_bytes) > MAX_ARCHIVE_BYTES
            or hashlib.sha256(self.archive_bytes).hexdigest()
            != self.archive_sha256
        ):
            _fail("construction source archive is malformed or caller-minted")
        object.__setattr__(
            self,
            "_archive_id",
            _content_id("source_archive", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_construction_source_archive.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_closure_id": self.source_closure_id,
            "entry_ids": [item.module_id for item in self.entries],
            "entry_count": len(self.entries),
            "archive_format": ARCHIVE_FORMAT,
            "archive_sha256": self.archive_sha256,
            "archive_byte_count": self.archive_byte_count,
            "zip_compression": "STORED",
            "canonical_member_timestamp": [1980, 1, 1, 0, 0, 0],
            "canonical_member_mode": "100444",
            "construction_only": True,
        }

    @property
    def archive_id(self) -> str:
        return self._archive_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "archive_id": self.archive_id}


@dataclass(frozen=True, slots=True)
class ConstructionRuntimeDependencyLockV2:
    _issuer: InitVar[object]
    dependency_lock_id: str
    dependency_lock_document_bytes: bytes = field(repr=False)
    dependency_lock_canonical_sha256: str
    dependency_lock_canonical_byte_count: int
    dependency_lock_raw_sha256: str
    dependency_lock_raw_byte_count: int
    pyproject_sha256: str
    requested_executable: str
    resolved_executable: str
    resolved_executable_sha256: str
    resolved_executable_byte_count: int
    runtime_probe_sha256: str
    runtime_probe_byte_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.dependency_lock_id, "runtime dependency lock"),
            (
                self.dependency_lock_canonical_sha256,
                "canonical dependency lock",
            ),
            (self.dependency_lock_raw_sha256, "raw dependency lock"),
            (self.pyproject_sha256, "pyproject bytes"),
            (self.resolved_executable_sha256, "resolved Python executable"),
            (self.runtime_probe_sha256, "runtime probe"),
        ):
            _cid(value, label)
        if (
            _issuer is not _ISSUER
            or type(self.dependency_lock_document_bytes) is not bytes
            or not self.dependency_lock_document_bytes
            or hashlib.sha256(
                self.dependency_lock_document_bytes
            ).hexdigest()
            != self.dependency_lock_canonical_sha256
            or len(self.dependency_lock_document_bytes)
            != self.dependency_lock_canonical_byte_count
            or type(self.dependency_lock_raw_byte_count) is not int
            or self.dependency_lock_raw_byte_count <= 0
            or self.requested_executable != PYTHON_EXECUTABLE
            or type(self.resolved_executable) is not str
            or not self.resolved_executable.startswith("/")
            or type(self.resolved_executable_byte_count) is not int
            or self.resolved_executable_byte_count <= 0
            or type(self.runtime_probe_byte_count) is not int
            or self.runtime_probe_byte_count <= 0
        ):
            _fail("runtime dependency-lock verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _content_id("runtime_lock", self._payload()),
        )

    @property
    def dependency_lock_document(self) -> dict[str, Any]:
        return _strict_json_object(
            self.dependency_lock_document_bytes,
            label="canonical dependency-lock document",
            byte_cap=4 * 1024 * 1024,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_runtime_lock_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "dependency_lock_id": self.dependency_lock_id,
            "dependency_lock_canonical_sha256": (
                self.dependency_lock_canonical_sha256
            ),
            "dependency_lock_canonical_byte_count": (
                self.dependency_lock_canonical_byte_count
            ),
            "dependency_lock_raw_sha256": self.dependency_lock_raw_sha256,
            "dependency_lock_raw_byte_count": (
                self.dependency_lock_raw_byte_count
            ),
            "pyproject_sha256": self.pyproject_sha256,
            "requested_executable": self.requested_executable,
            "resolved_executable": self.resolved_executable,
            "resolved_executable_sha256": self.resolved_executable_sha256,
            "resolved_executable_byte_count": (
                self.resolved_executable_byte_count
            ),
            "runtime_probe_sha256": self.runtime_probe_sha256,
            "runtime_probe_byte_count": self.runtime_probe_byte_count,
            "runtime_identity_recomputed_by_requested_executable": True,
            "installed_distribution_metadata_recomputed": True,
            "project_bytes_recomputed": True,
            "construction_only": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


@dataclass(frozen=True, slots=True)
class ConstructionSealedArchiveCompileVerificationV2:
    _issuer: InitVar[object]
    source_closure_id: str
    source_archive_id: str
    runtime_lock_verification_id: str
    archive_sha256: str
    archive_byte_count: int
    expected_module_names: tuple[str, ...]
    before_acfqp_modules: tuple[str, ...]
    after_acfqp_modules: tuple[str, ...]
    child_result_bytes: bytes = field(repr=False)
    child_result_sha256: str
    child_result_byte_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.source_closure_id, "archive-compile source closure"),
            (self.source_archive_id, "archive-compile source archive"),
            (
                self.runtime_lock_verification_id,
                "archive-compile runtime lock",
            ),
            (self.archive_sha256, "archive-compile archive bytes"),
            (self.child_result_sha256, "archive-compile child result"),
        ):
            _cid(value, label)
        if (
            _issuer is not _ISSUER
            or type(self.expected_module_names) is not tuple
            or self.expected_module_names
            != tuple(sorted(set(self.expected_module_names)))
            or not self.expected_module_names
            or self.before_acfqp_modules != ()
            or self.after_acfqp_modules != ()
            or type(self.child_result_bytes) is not bytes
            or not self.child_result_bytes
            or len(self.child_result_bytes) != self.child_result_byte_count
            or hashlib.sha256(self.child_result_bytes).hexdigest()
            != self.child_result_sha256
            or type(self.archive_byte_count) is not int
            or self.archive_byte_count <= 0
        ):
            _fail("archive-compile verification is malformed or caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _content_id("archive_compile", self._payload()),
        )

    @property
    def child_result_document(self) -> dict[str, Any]:
        return _strict_json_object(
            self.child_result_bytes,
            label="isolated sealed-archive compile child result",
            byte_cap=MAX_CHILD_OUTPUT_BYTES,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_sealed_archive_compile_"
                "verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_closure_id": self.source_closure_id,
            "source_archive_id": self.source_archive_id,
            "runtime_lock_verification_id": (
                self.runtime_lock_verification_id
            ),
            "archive_sha256": self.archive_sha256,
            "archive_byte_count": self.archive_byte_count,
            "expected_module_names": list(self.expected_module_names),
            "before_acfqp_modules": list(self.before_acfqp_modules),
            "after_acfqp_modules": list(self.after_acfqp_modules),
            "child_result_sha256": self.child_result_sha256,
            "child_result_byte_count": self.child_result_byte_count,
            "child_executable": PYTHON_EXECUTABLE,
            "child_flags": ["-I", "-S"],
            "exact_archive_member_set_compiled": True,
            "tested_source_execution_allowed": False,
            "loaded_source_manifest_claimed": False,
            "target_worker_receipt_claimed": False,
            "construction_only": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def build_construction_source_closure_v2(
    *,
    root_modules: tuple[str, ...],
    module_sources: Mapping[str, bytes],
    module_paths: Mapping[str, str | os.PathLike[str]],
) -> ConstructionSourceClosureV2:
    """Build an exact recursive static ACFQP closure from supplied bytes."""

    if (
        type(root_modules) is not tuple
        or root_modules != tuple(sorted(set(root_modules)))
        or not root_modules
        or len(root_modules) > MAX_MODULES
        or any(not _valid_module_name(value) for value in root_modules)
        or not isinstance(module_sources, Mapping)
        or not isinstance(module_paths, Mapping)
        or set(module_sources) != set(module_paths)
        or len(module_sources) > MAX_MODULES
        or any(not _valid_module_name(value) for value in module_sources)
        or any(type(raw) is not bytes for raw in module_sources.values())
        or not set(root_modules) <= set(module_sources)
        or "acfqp" not in module_sources
    ):
        _fail("construction source inputs are malformed or incomplete")
    sources = dict(module_sources)
    paths = dict(module_paths)
    is_package_by_name: dict[str, bool] = {}
    for name in sorted(sources):
        raw = sources[name]
        if (
            not raw
            or len(raw) > MAX_SOURCE_BYTES_PER_MODULE
            or _read_regular_symlink_free(paths[name]) != raw
        ):
            _fail("supplied source bytes differ from regular source file")
        path = Path(paths[name])
        is_package = path.name == "__init__.py"
        expected_suffix = PurePosixPath(
            _module_relative_path(name, is_package=is_package)
        ).parts
        if tuple(path.parts[-len(expected_suffix) :]) != expected_suffix:
            _fail("source path suffix does not match its module name")
        is_package_by_name[name] = is_package

    available = frozenset(sources)
    pending = list(reversed(root_modules))
    included: set[str] = set()
    imports_by_name: dict[str, tuple[str, ...]] = {}
    while pending:
        name = pending.pop()
        if name in included:
            continue
        if len(included) >= MAX_MODULES:
            _fail("construction source closure exceeded its module cap")
        included.add(name)
        imports = _local_imports_from_raw(
            module_name=name,
            is_package=is_package_by_name[name],
            raw=sources[name],
            available_names=available,
        )
        imports_by_name[name] = imports
        pending.extend(reversed(tuple(
            value for value in imports if value not in included
        )))
        components = name.split(".")
        for end in range(1, len(components)):
            parent = ".".join(components[:end])
            if parent not in sources:
                _fail(f"source closure omitted parent package: {parent}")
            if parent not in included:
                pending.append(parent)

    # Parent packages added late must also contribute their own imports.
    while any(name not in imports_by_name for name in included):
        for name in tuple(sorted(included)):
            if name in imports_by_name:
                continue
            imports = _local_imports_from_raw(
                module_name=name,
                is_package=is_package_by_name[name],
                raw=sources[name],
                available_names=available,
            )
            imports_by_name[name] = imports
            for dependency in imports:
                if dependency not in included:
                    included.add(dependency)
            components = name.split(".")
            for end in range(1, len(components)):
                parent = ".".join(components[:end])
                if parent not in sources:
                    _fail(f"source closure omitted parent package: {parent}")
                included.add(parent)
            if len(included) > MAX_MODULES:
                _fail("construction source closure exceeded its module cap")

    modules = tuple(
        ConstructionSourceModuleV2(
            _ISSUER,
            name,
            _module_relative_path(
                name,
                is_package=is_package_by_name[name],
            ),
            is_package_by_name[name],
            hashlib.sha256(sources[name]).hexdigest(),
            len(sources[name]),
            imports_by_name[name],
            True,
            True,
        )
        for name in sorted(included)
    )
    return ConstructionSourceClosureV2(
        _ISSUER,
        root_modules,
        modules,
    )


def _deterministic_archive_bytes(
    entries: tuple[ConstructionSourceModuleV2, ...],
    sources: Mapping[str, bytes],
) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=True,
    ) as archive:
        for entry in sorted(entries, key=lambda item: item.relative_path):
            raw = sources[entry.module_name]
            info = zipfile.ZipInfo(
                filename=entry.relative_path,
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (0o100444 & 0xFFFF) << 16
            archive.writestr(info, raw)
    return output.getvalue()


def _verify_archive(
    archive: ConstructionSourceArchiveV2,
    sources: Mapping[str, bytes],
) -> None:
    expected = {
        item.relative_path: item for item in archive.entries
    }
    try:
        with zipfile.ZipFile(
            io.BytesIO(archive.archive_bytes),
            mode="r",
        ) as handle:
            infos = handle.infolist()
            if (
                [item.filename for item in infos] != sorted(expected)
                or len(infos) != len(expected)
                or len({item.filename for item in infos}) != len(infos)
            ):
                _fail("construction source archive member set changed")
            for info in infos:
                entry = expected[info.filename]
                raw = handle.read(info)
                if (
                    info.compress_type != zipfile.ZIP_STORED
                    or info.date_time != (1980, 1, 1, 0, 0, 0)
                    or info.create_system != 3
                    or (info.external_attr >> 16) != 0o100444
                    or raw != sources[entry.module_name]
                    or len(raw) != entry.source_byte_count
                    or hashlib.sha256(raw).hexdigest()
                    != entry.source_sha256
                ):
                    _fail("construction source archive member changed")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        if type(error) is V075ConstructionSourceRuntimeV2InvariantViolation:
            raise
        raise V075ConstructionSourceRuntimeV2InvariantViolation(
            "construction source archive is malformed"
        ) from error
    if _deterministic_archive_bytes(archive.entries, sources) != (
        archive.archive_bytes
    ):
        _fail("construction source archive is not canonical deterministic ZIP")


def build_deterministic_source_archive_v2(
    *,
    closure: ConstructionSourceClosureV2,
    module_sources: Mapping[str, bytes],
) -> ConstructionSourceArchiveV2:
    """Create and replay the canonical stored ZIP for one source closure."""

    if (
        type(closure) is not ConstructionSourceClosureV2
        or not isinstance(module_sources, Mapping)
        or set(closure.module_names) - set(module_sources)
        or any(
            type(module_sources[name]) is not bytes
            or hashlib.sha256(module_sources[name]).hexdigest()
            != entry.source_sha256
            or len(module_sources[name]) != entry.source_byte_count
            for name, entry in (
                (item.module_name, item) for item in closure.modules
            )
        )
    ):
        _fail("archive source bytes differ from the exact source closure")
    selected = {
        name: module_sources[name] for name in closure.module_names
    }
    raw = _deterministic_archive_bytes(closure.modules, selected)
    if not raw or len(raw) > MAX_ARCHIVE_BYTES:
        _fail("construction source archive is empty or over its byte cap")
    result = ConstructionSourceArchiveV2(
        _ISSUER,
        closure.closure_id,
        closure.modules,
        raw,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )
    _verify_archive(result, selected)
    return result


def _run_child(
    *,
    argv: list[str],
    input_bytes: bytes,
    timeout_seconds: int,
    pass_fds: tuple[int, ...] = (),
) -> bytes:
    if (
        type(timeout_seconds) is not int
        or timeout_seconds <= 0
        or timeout_seconds > MAX_TIMEOUT_SECONDS
    ):
        _fail("child timeout is outside the construction profile")
    try:
        completed = subprocess.run(
            argv,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
            pass_fds=pass_fds,
            cwd="/",
            env={
                "LC_ALL": "C.UTF-8",
                "TZ": "UTC",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
            },
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise V075ConstructionSourceRuntimeV2InvariantViolation(
            "construction child could not complete"
        ) from error
    if (
        completed.returncode != 0
        or not completed.stdout
        or len(completed.stdout) > MAX_CHILD_OUTPUT_BYTES
        or len(completed.stderr) > MAX_CHILD_STDERR_BYTES
        or completed.stderr
    ):
        _fail(
            "construction child failed or emitted unexpected output "
            f"(exit={completed.returncode})"
        )
    return completed.stdout


def verify_construction_runtime_dependency_lock_v2(
    *,
    dependency_lock_bytes: bytes,
    pyproject_bytes: bytes,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> ConstructionRuntimeDependencyLockV2:
    """Bind the tracked lock to an independent ``/usr/bin/python3`` probe."""

    lock = _strict_json_object(
        dependency_lock_bytes,
        label="V0-075 dependency lock",
        byte_cap=4 * 1024 * 1024,
    )
    if set(lock) != _LOCK_KEYS:
        _fail("V0-075 dependency lock field set changed")
    interpreter = lock.get("interpreter")
    project = lock.get("project")
    distributions = lock.get("test_dependency_distributions")
    if (
        type(interpreter) is not dict
        or set(interpreter) != _LOCK_INTERPRETER_KEYS
        or type(project) is not dict
        or set(project) != _LOCK_PROJECT_KEYS
        or type(distributions) is not list
        or any(
            type(item) is not dict
            or set(item) != _LOCK_DISTRIBUTION_KEYS
            for item in distributions
        )
        or type(pyproject_bytes) is not bytes
        or not pyproject_bytes
    ):
        _fail("V0-075 dependency lock nested shape changed")
    payload = dict(lock)
    claimed_id = _cid(
        payload.pop("runtime_dependency_lock_id", None),
        "V0-075 runtime dependency lock",
    )
    names = [item["name"] for item in distributions]
    if (
        lock["schema"] != DEPENDENCY_LOCK_SCHEMA
        or lock["schema_version"] != "1.0.0"
        or lock["proposed_contract_version"] != "1.40.0"
        or lock["profile_key"] != DEPENDENCY_LOCK_PROFILE
        or lock["runtime_dependency_model"] != DEPENDENCY_LOCK_MODEL
        or lock["runtime_third_party_distributions"] != []
        or lock["exact_test_command"] != _EXPECTED_TEST_COMMAND
        or lock["required_environment"] != _EXPECTED_ENVIRONMENT
        or lock["pytest_plugin_autoload_allowed"] is not False
        or lock["package_installer_execution_allowed"] is not False
        or lock["network_access_required"] is not False
        or lock["caller_supplied_digest_accepted"] is not False
        or lock["caller_supplied_status_accepted"] is not False
        or lock["target_access"] is not False
        or _dependency_lock_id(payload) != claimed_id
        or names != sorted(set(names))
        or project
        != {
            "name": "acfqp",
            "version": "0.0.1",
            "requires_python": ">=3.10",
            "declared_runtime_dependencies": [],
            "pyproject_sha256": hashlib.sha256(
                pyproject_bytes
            ).hexdigest(),
        }
    ):
        _fail("V0-075 dependency lock contract or content ID changed")
    request = canonical_json_bytes({"distribution_names": names})
    probe_raw = _run_child(
        # The tracked test distributions currently live in the registered
        # user-site tree.  This probe therefore validates that exact
        # /usr/bin/python3 environment without ``-I``.  The executable-source
        # replay below is the separate, stricter ``-I -S`` boundary.
        argv=[PYTHON_EXECUTABLE, "-c", _RUNTIME_PROBE],
        input_bytes=request,
        timeout_seconds=timeout_seconds,
    )
    probe = _strict_json_object(
        probe_raw,
        label="/usr/bin/python3 runtime probe",
        byte_cap=MAX_CHILD_OUTPUT_BYTES,
    )
    if (
        canonical_json_bytes(probe) != probe_raw
        or set(probe)
        != {
            "executable",
            "interpreter",
            "test_dependency_distributions",
        }
        or probe["executable"] != PYTHON_EXECUTABLE
        or probe["interpreter"] != interpreter
        or probe["test_dependency_distributions"] != distributions
    ):
        _fail("/usr/bin/python3 runtime or installed dependency lock changed")
    try:
        requested_lstat = os.lstat(PYTHON_EXECUTABLE)
        resolved = Path(PYTHON_EXECUTABLE).resolve(strict=True)
    except OSError as error:
        raise V075ConstructionSourceRuntimeV2InvariantViolation(
            "/usr/bin/python3 could not be resolved"
        ) from error
    if (
        not stat.S_ISLNK(requested_lstat.st_mode)
        or not resolved.is_absolute()
    ):
        _fail("/usr/bin/python3 link or resolved executable shape changed")
    resolved_raw = _read_regular_symlink_free(resolved)
    canonical_lock = canonical_json_bytes(lock)
    return ConstructionRuntimeDependencyLockV2(
        _ISSUER,
        claimed_id,
        canonical_lock,
        hashlib.sha256(canonical_lock).hexdigest(),
        len(canonical_lock),
        hashlib.sha256(dependency_lock_bytes).hexdigest(),
        len(dependency_lock_bytes),
        hashlib.sha256(pyproject_bytes).hexdigest(),
        PYTHON_EXECUTABLE,
        str(resolved),
        hashlib.sha256(resolved_raw).hexdigest(),
        len(resolved_raw),
        hashlib.sha256(probe_raw).hexdigest(),
        len(probe_raw),
    )


def _sealed_archive_fd(raw: bytes) -> int:
    if not hasattr(os, "memfd_create"):
        _fail("sealed construction archive requires memfd_create")
    try:
        fd = os.memfd_create(
            "acfqp-v075-construction-source",
            _MFD_CLOEXEC | _MFD_ALLOW_SEALING,
        )
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0:
                raise OSError("short memfd write")
            offset += written
        os.fsync(fd)
        import fcntl

        fcntl.fcntl(fd, _F_ADD_SEALS, _REQUIRED_SEALS)
        if fcntl.fcntl(fd, _F_GET_SEALS) & _REQUIRED_SEALS != (
            _REQUIRED_SEALS
        ):
            raise OSError("required memfd seals absent")
        if os.fstat(fd).st_size != len(raw):
            raise OSError("sealed memfd size changed")
        return fd
    except OSError as error:
        try:
            os.close(fd)
        except (OSError, UnboundLocalError):
            pass
        raise V075ConstructionSourceRuntimeV2InvariantViolation(
            "construction archive could not be sealed"
        ) from error


def verify_construction_sealed_archive_compile_v2(
    *,
    closure: ConstructionSourceClosureV2,
    archive: ConstructionSourceArchiveV2,
    runtime_lock: ConstructionRuntimeDependencyLockV2,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> ConstructionSealedArchiveCompileVerificationV2:
    """Compile every sealed member without importing or executing it."""

    if (
        type(closure) is not ConstructionSourceClosureV2
        or type(archive) is not ConstructionSourceArchiveV2
        or type(runtime_lock) is not ConstructionRuntimeDependencyLockV2
        or archive.source_closure_id != closure.closure_id
        or archive.entries != closure.modules
        or runtime_lock.requested_executable != PYTHON_EXECUTABLE
    ):
        _fail("isolated archive-compile inputs are foreign or stale")
    expected_entries = [
        {
            "module_name": item.module_name,
            "relative_path": item.relative_path,
            "source_sha256": item.source_sha256,
            "source_byte_count": item.source_byte_count,
        }
        for item in archive.entries
    ]
    fd = _sealed_archive_fd(archive.archive_bytes)
    try:
        archive_path = f"/proc/self/fd/{fd}"
        request = canonical_json_bytes(
            {
                "archive_byte_count": archive.archive_byte_count,
                "archive_path": archive_path,
                "archive_sha256": archive.archive_sha256,
                "entries": expected_entries,
                "expected_module_names": list(closure.module_names),
            }
        )
        child_raw = _run_child(
            argv=[
                PYTHON_EXECUTABLE,
                "-I",
                "-S",
                "-c",
                _SEALED_ARCHIVE_COMPILE_CHILD,
                archive_path,
            ],
            input_bytes=request,
            timeout_seconds=timeout_seconds,
            pass_fds=(fd,),
        )
    finally:
        os.close(fd)
    child = _strict_json_object(
        child_raw,
        label="isolated sealed-archive compile child result",
        byte_cap=MAX_CHILD_OUTPUT_BYTES,
    )
    locked_version = runtime_lock.dependency_lock_document["interpreter"][
        "version_info"
    ]
    expected_safe_path: bool | str = (
        True
        if tuple(locked_version[:2]) >= (3, 11)
        else "NOT_EXPOSED"
    )
    if (
        canonical_json_bytes(child) != child_raw
        or set(child)
        != {
            "archive_byte_count",
            "archive_sha256",
            "before_acfqp_modules",
            "after_acfqp_modules",
            "compiled_entries",
            "tested_source_execution_allowed",
            "archive_added_to_sys_path",
            "runtime_flags",
        }
        or child["archive_byte_count"] != archive.archive_byte_count
        or child["archive_sha256"] != archive.archive_sha256
        or child["before_acfqp_modules"] != []
        or child["after_acfqp_modules"] != []
        or child["tested_source_execution_allowed"] is not False
        or child["archive_added_to_sys_path"] is not False
        or type(child["compiled_entries"]) is not list
        or len(child["compiled_entries"]) != len(expected_entries)
        or any(
            type(item) is not dict
            or set(item)
            != {
                "module_name",
                "relative_path",
                "source_sha256",
                "source_byte_count",
            }
            for item in child["compiled_entries"]
        )
        or child["compiled_entries"] != expected_entries
        or child["runtime_flags"]
        != {
            "isolated": 1,
            "no_site": 1,
            "ignore_environment": 1,
            "safe_path": expected_safe_path,
        }
    ):
        _fail(
            "isolated child archive compile, source identity, or flags changed"
        )
    return ConstructionSealedArchiveCompileVerificationV2(
        _ISSUER,
        closure.closure_id,
        archive.archive_id,
        runtime_lock.verification_id,
        archive.archive_sha256,
        archive.archive_byte_count,
        closure.module_names,
        (),
        (),
        child_raw,
        hashlib.sha256(child_raw).hexdigest(),
        len(child_raw),
    )


__all__ = [
    "ARCHIVE_FORMAT",
    "ConstructionSealedArchiveCompileVerificationV2",
    "ConstructionRuntimeDependencyLockV2",
    "ConstructionSourceArchiveV2",
    "ConstructionSourceClosureV2",
    "ConstructionSourceModuleV2",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_TIMEOUT_SECONDS",
    "PROFILE_KEY",
    "PYTHON_EXECUTABLE",
    "SCHEMA_VERSION",
    "STATIC_CLOSURE_RULE",
    "V075ConstructionSourceRuntimeV2InvariantViolation",
    "build_construction_source_closure_v2",
    "build_deterministic_source_archive_v2",
    "verify_construction_sealed_archive_compile_v2",
    "verify_construction_runtime_dependency_lock_v2",
]
