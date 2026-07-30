"""Construction-only isolated replay of one portable V0-075 evidence bundle.

The parent finishes acquisition and freezes a canonical portable bundle before
this boundary is opened.  A fresh ``python -I`` child receives exactly two
public frames: a frozen program/profile identity and the canonical bundle
bytes.  The child performs strict raw-byte bundle replay and emits one typed,
content-addressed construction result.

This transport neither opens a target execution path nor upgrades portable
topology replay into a semantic-registry proof, scientific endpoint, or
certificate.
"""

from __future__ import annotations

import ast
import base64
import ctypes
import csv
from dataclasses import InitVar, dataclass, field
import email.parser
import email.policy
import fcntl
import hashlib
import importlib
import importlib.machinery
import importlib.metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import select
import signal
import subprocess
import sys
import sysconfig
import tempfile
import time
from typing import Any, Mapping, NoReturn
import zipfile


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.62.0"
PROFILE_KEY = "v075_public_replay_occurrence_ipc_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
SEMANTIC_REGISTRY_REPLAY_COMPLETE = False

TERMINAL_SCOPE = "CONSTRUCTION_PUBLIC_REPLAY_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = "PORTABLE_GRAPH_REPLAYED_CONSTRUCTION_ONLY"

MAX_LAUNCH_FRAME_BYTES = 1024 * 1024
MAX_RESULT_FRAME_BYTES = 1024 * 1024
MAX_BUNDLE_FRAME_BYTES = 512 * 1024 * 1024
MAX_CHILD_STDERR_BYTES = 256 * 1024
DEFAULT_PROCESS_TIMEOUT_SECONDS = 3_600
MAX_PROCESS_TIMEOUT_SECONDS = 21_600

_FRAME_WIDTH = 8
_VERIFIER_MODULE_NAME = (
    "acfqp.v075_portable_occurrence_evidence_bundle_v2"
)
_VERIFIER_FILENAME = "v075_portable_occurrence_evidence_bundle_v2.py"
_VERIFIER_CALLABLE = (
    "verify_v075_portable_occurrence_evidence_bundle_bytes_v2"
)
_IPC_MODULE_NAME = "acfqp.v075_public_replay_occurrence_ipc_v2"
_F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
_F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
_F_SEAL_SEAL = getattr(fcntl, "F_SEAL_SEAL", 0x0001)
_F_SEAL_SHRINK = getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
_F_SEAL_GROW = getattr(fcntl, "F_SEAL_GROW", 0x0004)
_F_SEAL_WRITE = getattr(fcntl, "F_SEAL_WRITE", 0x0008)
_MFD_CLOEXEC = getattr(os, "MFD_CLOEXEC", 0x0001)
_MFD_ALLOW_SEALING = getattr(os, "MFD_ALLOW_SEALING", 0x0002)
_REQUIRED_SEALS = (
    _F_SEAL_WRITE | _F_SEAL_GROW | _F_SEAL_SHRINK | _F_SEAL_SEAL
)
_BOOTSTRAP_SOURCE = r"""
import fcntl
import hashlib
import importlib
import os
import sys

fd = int(sys.argv[1])
expected_sha256 = sys.argv[2]
expected_size = int(sys.argv[3])
expected_snapshot_id = sys.argv[4]
expected_bootstrap_sha256 = sys.argv[5]
expected_runtime_identity_id = sys.argv[6]
required_seals = (
    0x0008 | 0x0004 | 0x0002 | 0x0001
)
if fcntl.fcntl(fd, 1034) & required_seals != required_seals:
    raise SystemExit(71)
stat = os.fstat(fd)
if stat.st_size != expected_size:
    raise SystemExit(72)
raw = bytearray()
offset = 0
while offset < expected_size:
    chunk = os.pread(fd, min(1024 * 1024, expected_size - offset), offset)
    if not chunk:
        raise SystemExit(73)
    raw.extend(chunk)
    offset += len(chunk)
if hashlib.sha256(raw).hexdigest() != expected_sha256:
    raise SystemExit(74)
archive_path = "/proc/self/fd/" + str(fd)
sys.path.insert(0, archive_path)
module = importlib.import_module("acfqp.v075_public_replay_occurrence_ipc_v2")
raise SystemExit(
    module._sealed_child_main(
        sealed_fd=fd,
        archive_path=archive_path,
        expected_snapshot_id=expected_snapshot_id,
        expected_archive_sha256=expected_sha256,
        expected_archive_size=expected_size,
        expected_bootstrap_sha256=expected_bootstrap_sha256,
        expected_runtime_identity_id=expected_runtime_identity_id,
    )
)
""".strip()
_BOOTSTRAP_SHA256 = hashlib.sha256(
    _BOOTSTRAP_SOURCE.encode("utf-8")
).hexdigest()

_DOMAINS = {
    "source_manifest": "acfqp:v075-public-replay-source-manifest:v2",
    "source_snapshot": "acfqp:v075-public-replay-source-snapshot:v2",
    "dependency_distribution": (
        "acfqp:v075-public-replay-dependency-distribution:v2"
    ),
    "dependency_lock": (
        "acfqp:v075-public-replay-preregistered-dependency-lock:v2"
    ),
    "runtime_identity": "acfqp:v075-public-replay-runtime-identity:v2",
    "stdlib_tree": "acfqp:v075-public-replay-stdlib-tree:v2",
    "loaded_source_manifest": (
        "acfqp:v075-public-replay-loaded-source-manifest:v2"
    ),
    "program": "acfqp:v075-public-replay-child-program:v2",
    "profile": "acfqp:v075-public-replay-occurrence-ipc-profile:v2",
    "launch": "acfqp:v075-public-replay-occurrence-ipc-launch:v2",
    "child_result": "acfqp:v075-public-replay-child-result:v2",
    "journal_entry": "acfqp:v075-public-replay-ipc-journal-entry:v2",
    "journal": "acfqp:v075-public-replay-ipc-journal:v2",
    "work": "acfqp:v075-public-replay-ipc-work:v2",
    "profile_freeze_work": (
        "acfqp:v075-public-replay-profile-freeze-work:v2"
    ),
    "evaluation_work": "acfqp:v075-public-replay-evaluation-work:v2",
    "semantic_evaluation": (
        "acfqp:v075-public-replay-semantic-evaluation:v2"
    ),
    "supervisor_attestation": (
        "acfqp:v075-public-replay-construction-supervisor-attestation:v2"
    ),
    "result": "acfqp:v075-public-replay-ipc-result:v2",
}

if len(_DOMAINS) != len(set(_DOMAINS.values())):  # pragma: no cover
    raise RuntimeError("public replay IPC content domains must be unique")

_INITIAL_JOURNAL_HASH = hashlib.sha256(
    b"acfqp:v075-public-replay-ipc-journal-initial:v2"
).hexdigest()
_SEALED_CHILD_ARCHIVE_PATH: str | None = None


def _expected_child_runtime_flags() -> dict[str, Any]:
    """Return the version-specific, explicitly registered isolation flags."""

    return {
        "isolated": 1,
        "no_site": 1,
        "ignore_environment": 1,
        "safe_path": (
            True
            if hasattr(sys.flags, "safe_path")
            else {
                "kind": "NOT_EXPOSED_BY_PYTHON_LT_3_11",
                "enforced_by_isolated_path_audit": True,
            }
        ),
    }


class V075PublicReplayOccurrenceIPCV2InvariantViolation(ValueError):
    """A public identity, frame, process, or replay invariant failed."""


class V075PublicReplayProductionV2NotReady(RuntimeError):
    """Construction replay cannot authorize a production execution."""


def _fail(message: str) -> NoReturn:
    raise V075PublicReplayOccurrenceIPCV2InvariantViolation(message)


def _canonical_bytes(value: Any) -> bytes:
    def validate(item: Any) -> None:
        if item is None or type(item) in {bool, int, str}:
            return
        if type(item) is list:
            for child in item:
                validate(child)
            return
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                _fail("canonical public replay objects require string keys")
            for child in item.values():
                validate(child)
            return
        _fail("public replay payload contains a non-JSON runtime object")

    validate(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            str(error)
        ) from error


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("canonical public replay JSON contains a duplicate key")
        result[key] = value
    return result


def _load_canonical(
    raw: bytes,
    *,
    field_name: str,
    byte_cap: int,
) -> Any:
    if (
        type(raw) is not bytes
        or not raw
        or type(byte_cap) is not int
        or byte_cap <= 0
        or len(raw) > byte_cap
    ):
        _fail(f"{field_name} is empty, mistyped, or over its byte cap")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_pairs,
            parse_constant=lambda token: _fail(
                f"non-finite JSON constant {token!r} is forbidden"
            ),
        )
    except (
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        if isinstance(
            error,
            V075PublicReplayOccurrenceIPCV2InvariantViolation,
        ):
            raise
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            f"{field_name} is not canonical JSON: {error}"
        ) from error
    if _canonical_bytes(value) != raw:
        _fail(f"{field_name} is not canonical JSON")
    return value


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = _DOMAINS[role].encode("utf-8")
    except KeyError as error:  # pragma: no cover
        raise RuntimeError("unknown public replay IPC content domain") from error
    return hashlib.sha256(
        domain + b"\x00" + _canonical_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field_name} must be one lowercase SHA-256 content ID")
    return value


def _exact_mapping(
    value: Any,
    keys: set[str],
    *,
    field_name: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{field_name} fields are missing, hidden, or malformed")
    return value


def _ipc_module_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _verifier_module_path() -> Path:
    return Path(__file__).resolve().with_name(_VERIFIER_FILENAME)


def _verifier_module_digest() -> str:
    path = _verifier_module_path()
    if not path.is_file():
        _fail("registered public replay verifier module is absent")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _local_module_path(module_name: str) -> Path | None:
    if type(module_name) is not str or (
        module_name != "acfqp" and not module_name.startswith("acfqp.")
    ):
        return None
    relative_parts = module_name.split(".")[1:]
    candidate = _package_root().joinpath(*relative_parts)
    path = (
        candidate / "__init__.py"
        if candidate.is_dir()
        else candidate.with_suffix(".py")
    )
    resolved = path.resolve()
    if (
        not resolved.is_relative_to(_source_root())
        or not resolved.is_file()
        or resolved.suffix != ".py"
    ):
        return None
    return resolved


def _absolute_import_base(
    *,
    current_module: str,
    current_path: Path,
    imported_module: str | None,
    level: int,
) -> str:
    if level == 0:
        return "" if imported_module is None else imported_module
    is_package = current_path.name == "__init__.py"
    package = (
        current_module
        if is_package
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
    module_name: str,
    path: Path,
    raw: bytes,
) -> frozenset[str]:
    try:
        tree = ast.parse(raw, filename=str(path))
    except (OSError, SyntaxError, ValueError) as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "registered verifier source closure could not be parsed"
        ) from error
    discovered: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            candidates = tuple(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _absolute_import_base(
                current_module=module_name,
                current_path=path,
                imported_module=node.module,
                level=node.level,
            )
            candidates = (base,) + tuple(
                f"{base}.{alias.name}" if base else alias.name
                for alias in node.names
                if alias.name != "*"
            )
        else:
            continue
        for candidate in candidates:
            if _local_module_path(candidate) is not None:
                discovered.add(candidate)
    return frozenset(discovered)


def _local_imports(module_name: str, path: Path) -> frozenset[str]:
    return _local_imports_from_raw(module_name, path, path.read_bytes())


def _source_identity(path: Path) -> tuple[str, int]:
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _module_name_for_relative_source(relative_path: str) -> str:
    if relative_path.endswith("/__init__.py"):
        return relative_path[: -len("/__init__.py")].replace("/", ".")
    if relative_path.endswith(".py"):
        return relative_path[:-3].replace("/", ".")
    return ""


@dataclass(frozen=True, slots=True)
class V075PublicReplayDependencySourceEntryV2:
    distribution_name: str
    distribution_version: str
    module_name: str
    relative_path: str
    source_sha256: str
    source_byte_count: int

    def __post_init__(self) -> None:
        _cid(self.source_sha256, "dependency source digest")
        expected_root = self.distribution_name.replace("-", "_")
        if (
            self.distribution_name not in {"packaging", "tomli"}
            or type(self.distribution_version) is not str
            or not self.distribution_version
            or type(self.module_name) is not str
            or (
                self.module_name != expected_root
                and not self.module_name.startswith(expected_root + ".")
            )
            or type(self.relative_path) is not str
            or _module_name_for_relative_source(self.relative_path)
            != self.module_name
            or self.relative_path.startswith("/")
            or ".." in PurePosixPath(self.relative_path).parts
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
        ):
            _fail("preregistered dependency source entry is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "distribution_name": self.distribution_name,
            "distribution_version": self.distribution_version,
            "module_name": self.module_name,
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
        }


@dataclass(frozen=True, slots=True)
class V075PublicReplayDependencyDistributionV2:
    distribution_name: str
    distribution_version: str
    root_module: str
    metadata_relative_path: str
    metadata_distribution_path: str
    metadata_sha256: str
    metadata_byte_count: int
    record_relative_path: str
    record_distribution_path: str
    record_sha256: str
    record_byte_count: int
    source_entries: tuple[V075PublicReplayDependencySourceEntryV2, ...]
    _distribution_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.metadata_sha256, "dependency METADATA digest")
        _cid(self.record_sha256, "dependency RECORD digest")
        expected_root = self.distribution_name.replace("-", "_")
        if (
            self.distribution_name not in {"packaging", "tomli"}
            or type(self.distribution_version) is not str
            or not self.distribution_version
            or self.root_module != expected_root
            or self.metadata_relative_path
            != (
                ".acfqp-dependency-metadata/"
                f"{self.distribution_name}/METADATA"
            )
            or type(self.metadata_distribution_path) is not str
            or not self.metadata_distribution_path.endswith(
                ".dist-info/METADATA"
            )
            or type(self.metadata_byte_count) is not int
            or self.metadata_byte_count <= 0
            or self.record_relative_path
            != (
                ".acfqp-dependency-metadata/"
                f"{self.distribution_name}/RECORD"
            )
            or type(self.record_distribution_path) is not str
            or not self.record_distribution_path.endswith(
                ".dist-info/RECORD"
            )
            or PurePosixPath(self.metadata_distribution_path).parent
            != PurePosixPath(self.record_distribution_path).parent
            or type(self.record_byte_count) is not int
            or self.record_byte_count <= 0
            or type(self.source_entries) is not tuple
            or not self.source_entries
            or any(
                type(item) is not V075PublicReplayDependencySourceEntryV2
                or item.distribution_name != self.distribution_name
                or item.distribution_version != self.distribution_version
                for item in self.source_entries
            )
            or tuple(item.module_name for item in self.source_entries)
            != tuple(
                sorted(item.module_name for item in self.source_entries)
            )
            or len({item.module_name for item in self.source_entries})
            != len(self.source_entries)
            or self.root_module
            not in {item.module_name for item in self.source_entries}
        ):
            _fail("preregistered dependency distribution is malformed")
        object.__setattr__(
            self,
            "_distribution_id",
            _hash("dependency_distribution", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_dependency_distribution.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "distribution_name": self.distribution_name,
            "distribution_version": self.distribution_version,
            "root_module": self.root_module,
            "metadata_relative_path": self.metadata_relative_path,
            "metadata_distribution_path": self.metadata_distribution_path,
            "metadata_sha256": self.metadata_sha256,
            "metadata_byte_count": self.metadata_byte_count,
            "record_relative_path": self.record_relative_path,
            "record_distribution_path": self.record_distribution_path,
            "record_sha256": self.record_sha256,
            "record_byte_count": self.record_byte_count,
            "source_entries": [
                item.to_document() for item in self.source_entries
            ],
            "source_entry_count": len(self.source_entries),
            "pure_python_source_closure_complete": True,
            "native_extension_entries_allowed": False,
            "raw_metadata_name_version_verified": True,
            "raw_record_membership_verified": True,
            "site_package_fallback_allowed": False,
            "dependency_lock_authority": (
                "CONSTRUCTION_LOCAL_PREREGISTERED_CAPTURE_ONLY"
            ),
            "independent_distribution_authority_verified": False,
            "production_dependency_lock": False,
        }

    @property
    def distribution_id(self) -> str:
        return self._distribution_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "distribution_id": self.distribution_id,
        }


def _dependency_lock_document(
    distributions: tuple[V075PublicReplayDependencyDistributionV2, ...],
) -> dict[str, Any]:
    payload = {
        "schema": (
            "acfqp.v075_public_replay_preregistered_dependency_lock.v2"
        ),
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "distribution_bindings": [
            {
                "distribution_name": item.distribution_name,
                "distribution_version": item.distribution_version,
                "distribution_id": item.distribution_id,
                "metadata_distribution_path": (
                    item.metadata_distribution_path
                ),
                "metadata_sha256": item.metadata_sha256,
                "metadata_byte_count": item.metadata_byte_count,
                "record_distribution_path": item.record_distribution_path,
                "record_sha256": item.record_sha256,
                "record_byte_count": item.record_byte_count,
            }
            for item in distributions
        ],
        "distribution_count": len(distributions),
        "lock_authority": (
            "CONSTRUCTION_LOCAL_PREREGISTERED_CAPTURE_ONLY"
        ),
        "installed_record_snapshot_bound": True,
        "independent_distribution_authority_verified": False,
        "external_lockfile_authority_verified": False,
        "production_dependency_lock": False,
        "official_or_scientific_claim_eligible": False,
    }
    return {
        **payload,
        "dependency_lock_id": _hash("dependency_lock", payload),
    }


def _is_native_extension_path(relative_path: str) -> bool:
    lowered = relative_path.lower()
    return (
        lowered.endswith((".so", ".pyd", ".dll", ".dylib"))
        or any(
            lowered.endswith(suffix.lower())
            for suffix in importlib.machinery.EXTENSION_SUFFIXES
        )
    )


def _record_hash(source_sha256: str) -> str:
    return "sha256=" + base64.urlsafe_b64encode(
        bytes.fromhex(source_sha256)
    ).decode("ascii").rstrip("=")


def _verify_dependency_metadata_and_record(
    distribution: V075PublicReplayDependencyDistributionV2,
    metadata_raw: bytes,
    record_raw: bytes,
) -> None:
    try:
        message = email.parser.BytesParser(
            policy=email.policy.compat32
        ).parsebytes(metadata_raw, headersonly=True)
        names = message.get_all("Name", [])
        versions = message.get_all("Version", [])
        record_text = record_raw.decode("utf-8", errors="strict")
        rows = list(csv.reader(io.StringIO(record_text, newline="")))
    except (UnicodeError, ValueError, csv.Error) as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "dependency METADATA or RECORD is malformed"
        ) from error
    if (
        len(names) != 1
        or len(versions) != 1
        or type(names[0]) is not str
        or type(versions[0]) is not str
        or names[0].strip().lower().replace("_", "-")
        != distribution.distribution_name
        or versions[0].strip() != distribution.distribution_version
        or any(len(row) != 3 or not row[0] for row in rows)
        or len({row[0] for row in rows}) != len(rows)
    ):
        _fail("dependency raw Name/Version or RECORD identity changed")
    by_path = {row[0]: row for row in rows}
    metadata_row = by_path.get(distribution.metadata_distribution_path)
    if (
        metadata_row is None
        or metadata_row[1] != _record_hash(distribution.metadata_sha256)
        or metadata_row[2] != str(distribution.metadata_byte_count)
    ):
        _fail("dependency RECORD does not bind raw METADATA")
    for entry in distribution.source_entries:
        row = by_path.get(entry.relative_path)
        if (
            row is None
            or row[1] != _record_hash(entry.source_sha256)
            or row[2] != str(entry.source_byte_count)
        ):
            _fail("dependency RECORD does not bind pure-Python source")
    root_prefix = distribution.root_module + "/"
    if any(
        path.startswith(root_prefix) and _is_native_extension_path(path)
        for path in by_path
    ):
        _fail("dependency RECORD contains an unsealed native extension")


def _capture_dependency_distribution(
    distribution_name: str,
) -> tuple[
    V075PublicReplayDependencyDistributionV2,
    dict[str, bytes],
]:
    try:
        distribution = importlib.metadata.distribution(distribution_name)
    except importlib.metadata.PackageNotFoundError as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            f"required dependency distribution is absent: {distribution_name}"
        ) from error
    normalized_name = (
        str(distribution.metadata["Name"]).lower().replace("_", "-")
    )
    if normalized_name != distribution_name:
        _fail("dependency distribution canonical name changed")
    version = distribution.version
    files = distribution.files
    if type(version) is not str or not version or files is None:
        _fail("dependency distribution metadata is incomplete")
    root_module = distribution_name.replace("-", "_")
    captured: dict[str, bytes] = {}
    entries: list[V075PublicReplayDependencySourceEntryV2] = []
    metadata_source: bytes | None = None
    metadata_distribution_path: str | None = None
    record_source: bytes | None = None
    record_distribution_path: str | None = None
    for distribution_file in sorted(files, key=lambda item: str(item)):
        relative = PurePosixPath(str(distribution_file))
        path = Path(distribution.locate_file(distribution_file)).resolve()
        if (
            relative.name == "METADATA"
            and any(part.endswith(".dist-info") for part in relative.parts)
        ):
            if not path.is_file() or metadata_source is not None:
                _fail("dependency distribution METADATA is ambiguous")
            metadata_source = path.read_bytes()
            metadata_distribution_path = relative.as_posix()
        if (
            relative.name == "RECORD"
            and any(part.endswith(".dist-info") for part in relative.parts)
        ):
            if not path.is_file() or record_source is not None:
                _fail("dependency distribution RECORD is ambiguous")
            record_source = path.read_bytes()
            record_distribution_path = relative.as_posix()
        if (
            relative.parts
            and relative.parts[0] == root_module
            and _is_native_extension_path(relative.as_posix())
        ):
            _fail("dependency distribution contains a native extension")
        if (
            not relative.parts
            or relative.parts[0] != root_module
            or relative.suffix != ".py"
        ):
            continue
        if not path.is_file():
            _fail("dependency pure-Python source file is absent")
        raw = path.read_bytes()
        relative_path = relative.as_posix()
        module_name = _module_name_for_relative_source(relative_path)
        entry = V075PublicReplayDependencySourceEntryV2(
            distribution_name,
            version,
            module_name,
            relative_path,
            hashlib.sha256(raw).hexdigest(),
            len(raw),
        )
        entries.append(entry)
        captured[relative_path] = raw
    if (
        metadata_source is None
        or metadata_distribution_path is None
        or record_source is None
        or record_distribution_path is None
    ):
        _fail("dependency distribution raw METADATA or RECORD is absent")
    metadata_relative_path = (
        f".acfqp-dependency-metadata/{distribution_name}/METADATA"
    )
    record_relative_path = (
        f".acfqp-dependency-metadata/{distribution_name}/RECORD"
    )
    captured[metadata_relative_path] = metadata_source
    captured[record_relative_path] = record_source
    frozen = V075PublicReplayDependencyDistributionV2(
        distribution_name,
        version,
        root_module,
        metadata_relative_path,
        metadata_distribution_path,
        hashlib.sha256(metadata_source).hexdigest(),
        len(metadata_source),
        record_relative_path,
        record_distribution_path,
        hashlib.sha256(record_source).hexdigest(),
        len(record_source),
        tuple(sorted(entries, key=lambda item: item.module_name)),
    )
    _verify_dependency_metadata_and_record(
        frozen,
        metadata_source,
        record_source,
    )
    return frozen, captured


def _capture_dependency_distributions() -> tuple[
    tuple[V075PublicReplayDependencyDistributionV2, ...],
    dict[str, bytes],
]:
    names = ["packaging"]
    if sys.version_info < (3, 11):
        names.append("tomli")
    distributions: list[V075PublicReplayDependencyDistributionV2] = []
    captured: dict[str, bytes] = {}
    for name in names:
        distribution, raw_entries = _capture_dependency_distribution(name)
        if set(captured).intersection(raw_entries):
            _fail("dependency archive paths overlap")
        captured.update(raw_entries)
        distributions.append(distribution)
    return tuple(distributions), captured


@dataclass(frozen=True, slots=True)
class V075PublicReplayRuntimeIdentityV2:
    implementation_name: str
    implementation_cache_tag: str
    implementation_version: tuple[int, int, int, str, int]
    sys_version: str
    hexversion: int
    api_version: int
    byteorder: str
    maxsize: int
    abiflags: str
    soabi: str
    multiarch: str
    sysconfig_platform: str
    python_build: tuple[str, str]
    python_compiler: str
    config_args: str
    cc: str
    executable_sha256: str
    executable_byte_count: int
    shared_library_sha256: str
    shared_library_byte_count: int
    stdlib_file_count: int
    stdlib_tree_digest: str
    host_system: str
    host_machine: str
    libc_name: str
    libc_version: str
    _runtime_identity_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.executable_sha256, "runtime executable"),
            (self.shared_library_sha256, "runtime shared library"),
            (self.stdlib_tree_digest, "runtime stdlib tree"),
        ):
            _cid(value, label)
        if (
            self.implementation_name != sys.implementation.name
            or type(self.implementation_cache_tag) is not str
            or type(self.implementation_version) is not tuple
            or len(self.implementation_version) != 5
            or any(
                type(value) is not int
                for value in (
                    self.implementation_version[0],
                    self.implementation_version[1],
                    self.implementation_version[2],
                    self.implementation_version[4],
                )
            )
            or type(self.implementation_version[3]) is not str
            or type(self.sys_version) is not str
            or type(self.hexversion) is not int
            or type(self.api_version) is not int
            or self.byteorder not in {"little", "big"}
            or type(self.maxsize) is not int
            or type(self.abiflags) is not str
            or type(self.soabi) is not str
            or type(self.multiarch) is not str
            or type(self.sysconfig_platform) is not str
            or type(self.python_build) is not tuple
            or len(self.python_build) != 2
            or any(type(item) is not str for item in self.python_build)
            or type(self.python_compiler) is not str
            or type(self.config_args) is not str
            or type(self.cc) is not str
            or type(self.executable_byte_count) is not int
            or self.executable_byte_count <= 0
            or type(self.shared_library_byte_count) is not int
            or self.shared_library_byte_count <= 0
            or type(self.stdlib_file_count) is not int
            or self.stdlib_file_count <= 0
            or type(self.host_system) is not str
            or type(self.host_machine) is not str
            or type(self.libc_name) is not str
            or type(self.libc_version) is not str
        ):
            _fail("public replay runtime identity is malformed")
        object.__setattr__(
            self,
            "_runtime_identity_id",
            _hash("runtime_identity", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_runtime_identity.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "implementation_name": self.implementation_name,
            "implementation_cache_tag": self.implementation_cache_tag,
            "implementation_version": list(self.implementation_version),
            "sys_version": self.sys_version,
            "hexversion": self.hexversion,
            "api_version": self.api_version,
            "byteorder": self.byteorder,
            "maxsize": self.maxsize,
            "abiflags": self.abiflags,
            "soabi": self.soabi,
            "multiarch": self.multiarch,
            "sysconfig_platform": self.sysconfig_platform,
            "python_build": list(self.python_build),
            "python_compiler": self.python_compiler,
            "config_args": self.config_args,
            "cc": self.cc,
            "executable": {
                "sha256_file_bytes": self.executable_sha256,
                "file_byte_count": self.executable_byte_count,
            },
            "shared_library": {
                "sha256_file_bytes": self.shared_library_sha256,
                "file_byte_count": self.shared_library_byte_count,
            },
            "stdlib": {
                "file_count": self.stdlib_file_count,
                "tree_digest": self.stdlib_tree_digest,
            },
            "host_abi": {
                "system": self.host_system,
                "machine": self.host_machine,
                "libc_name": self.libc_name,
                "libc_version": self.libc_version,
            },
            "cryptographic_or_os_remote_attestation": False,
        }

    @property
    def runtime_identity_id(self) -> str:
        return self._runtime_identity_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "runtime_identity_id": self.runtime_identity_id,
        }


def _runtime_file_identity(path: Path) -> tuple[str, int]:
    resolved = path.resolve(strict=True)
    raw = resolved.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _runtime_stdlib_identity() -> tuple[int, str]:
    root = Path(sysconfig.get_path("stdlib")).resolve(strict=True)
    records: list[dict[str, Any]] = []
    for candidate in sorted(
        root.rglob("*"),
        key=lambda item: item.relative_to(root).as_posix(),
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
            raw = resolved.read_bytes()
            records.append(
                {
                    "relative_path": relative,
                    "kind": "SYMLINK",
                    "link_target": os.readlink(candidate),
                    "resolved_sha256": hashlib.sha256(raw).hexdigest(),
                    "resolved_byte_count": len(raw),
                }
            )
        elif candidate.is_file():
            raw = candidate.read_bytes()
            records.append(
                {
                    "relative_path": relative,
                    "kind": "REGULAR_FILE",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "byte_count": len(raw),
                }
            )
    if not records:
        _fail("public replay runtime stdlib tree is empty")
    payload = {
        "schema": "acfqp.v075_public_replay_stdlib_tree.v2",
        "schema_version": SCHEMA_VERSION,
        "records": records,
        "file_count": len(records),
    }
    return len(records), _hash("stdlib_tree", payload)


def _capture_runtime_identity() -> V075PublicReplayRuntimeIdentityV2:
    executable = _interpreter_executable_path()
    libdir = sysconfig.get_config_var("LIBDIR")
    library = sysconfig.get_config_var("LDLIBRARY")
    if type(libdir) is not str or type(library) is not str:
        _fail("public replay runtime shared-library identity is absent")
    executable_sha256, executable_size = _runtime_file_identity(executable)
    library_sha256, library_size = _runtime_file_identity(
        Path(libdir, library)
    )
    stdlib_count, stdlib_digest = _runtime_stdlib_identity()
    version = sys.version_info
    libc_name, libc_version = platform.libc_ver()
    return V075PublicReplayRuntimeIdentityV2(
        sys.implementation.name,
        sys.implementation.cache_tag or "",
        (
            version.major,
            version.minor,
            version.micro,
            version.releaselevel,
            version.serial,
        ),
        sys.version,
        sys.hexversion,
        sys.api_version,
        sys.byteorder,
        sys.maxsize,
        getattr(sys, "abiflags", ""),
        str(sysconfig.get_config_var("SOABI") or ""),
        str(sysconfig.get_config_var("MULTIARCH") or ""),
        sysconfig.get_platform(),
        tuple(platform.python_build()),
        platform.python_compiler(),
        str(sysconfig.get_config_var("CONFIG_ARGS") or ""),
        str(sysconfig.get_config_var("CC") or ""),
        executable_sha256,
        executable_size,
        library_sha256,
        library_size,
        stdlib_count,
        stdlib_digest,
        platform.system(),
        platform.machine(),
        libc_name,
        libc_version,
    )


@dataclass(frozen=True, slots=True)
class V075PublicReplaySourceManifestEntryV2:
    module_name: str
    relative_path: str
    source_sha256: str
    source_byte_count: int

    def __post_init__(self) -> None:
        _cid(self.source_sha256, "public replay source digest")
        derived_module = _module_name_for_relative_source(self.relative_path)
        if (
            type(self.module_name) is not str
            or (
                self.module_name != "acfqp"
                and not self.module_name.startswith("acfqp.")
            )
            or type(self.relative_path) is not str
            or derived_module != self.module_name
            or self.relative_path.startswith("/")
            or ".." in self.relative_path.split("/")
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
        ):
            _fail("public replay source manifest entry is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "module_name": self.module_name,
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
        }


@dataclass(frozen=True, slots=True)
class V075PublicReplaySourceManifestV2:
    entries: tuple[V075PublicReplaySourceManifestEntryV2, ...]
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.entries) is not tuple
            or not self.entries
            or any(
                type(item) is not V075PublicReplaySourceManifestEntryV2
                for item in self.entries
            )
            or tuple(item.module_name for item in self.entries)
            != tuple(sorted(item.module_name for item in self.entries))
            or len({item.module_name for item in self.entries})
            != len(self.entries)
            or _VERIFIER_MODULE_NAME
            not in {item.module_name for item in self.entries}
            or "acfqp.phase3e_ids"
            not in {item.module_name for item in self.entries}
        ):
            _fail("public replay verifier source manifest is incomplete")
        object.__setattr__(
            self,
            "_manifest_id",
            _hash("source_manifest", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_source_manifest.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "root_module": _VERIFIER_MODULE_NAME,
            "closure_rule": "RECURSIVE_STATIC_LOCAL_ACFQP_IMPORTS",
            "entries": [item.to_document() for item in self.entries],
            "entry_count": len(self.entries),
        }

    @property
    def manifest_id(self) -> str:
        return self._manifest_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}


@dataclass(frozen=True, slots=True)
class V075PublicReplaySourceSnapshotV2:
    source_manifest: V075PublicReplaySourceManifestV2
    ipc_module_entry: V075PublicReplaySourceManifestEntryV2
    dependency_distributions: tuple[
        V075PublicReplayDependencyDistributionV2, ...
    ]
    archive_sha256: str
    archive_byte_count: int
    bootstrap_sha256: str
    archive_bytes: bytes = field(repr=False, compare=False)
    _source_snapshot_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.archive_sha256, "public replay source archive"),
            (self.bootstrap_sha256, "public replay bootstrap"),
        ):
            _cid(value, label)
        if (
            type(self.source_manifest) is not V075PublicReplaySourceManifestV2
            or type(self.ipc_module_entry)
            is not V075PublicReplaySourceManifestEntryV2
            or self.ipc_module_entry.module_name != _IPC_MODULE_NAME
            or self.ipc_module_entry.module_name
            in {
                item.module_name for item in self.source_manifest.entries
            }
            or type(self.dependency_distributions) is not tuple
            or tuple(
                item.distribution_name
                for item in self.dependency_distributions
            )
            != (
                ("packaging", "tomli")
                if sys.version_info < (3, 11)
                else ("packaging",)
            )
            or any(
                type(item)
                is not V075PublicReplayDependencyDistributionV2
                for item in self.dependency_distributions
            )
            or len(
                {
                    entry.module_name
                    for distribution in self.dependency_distributions
                    for entry in distribution.source_entries
                }
            )
            != sum(
                len(distribution.source_entries)
                for distribution in self.dependency_distributions
            )
            or {
                entry.module_name
                for distribution in self.dependency_distributions
                for entry in distribution.source_entries
            }.intersection(
                {
                    self.ipc_module_entry.module_name,
                    *(
                        item.module_name
                        for item in self.source_manifest.entries
                    ),
                }
            )
            or type(self.archive_byte_count) is not int
            or self.archive_byte_count <= 0
            or self.bootstrap_sha256 != _BOOTSTRAP_SHA256
            or type(self.archive_bytes) is not bytes
        ):
            _fail("public replay source snapshot is malformed")
        object.__setattr__(
            self,
            "_source_snapshot_id",
            _hash("source_snapshot", self._payload()),
        )
        if self.archive_bytes:
            _verify_source_archive_bytes(self, self.archive_bytes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_source_snapshot.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_manifest": self.source_manifest.to_document(),
            "source_manifest_id": self.source_manifest.manifest_id,
            "ipc_module_entry": self.ipc_module_entry.to_document(),
            "dependency_distributions": [
                item.to_document()
                for item in self.dependency_distributions
            ],
            "dependency_distribution_ids": [
                item.distribution_id
                for item in self.dependency_distributions
            ],
            "dependency_distribution_count": len(
                self.dependency_distributions
            ),
            "preregistered_dependency_lock": (
                _dependency_lock_document(self.dependency_distributions)
            ),
            "preregistered_dependency_lock_id": (
                _dependency_lock_document(
                    self.dependency_distributions
                )["dependency_lock_id"]
            ),
            "archive_sha256": self.archive_sha256,
            "archive_byte_count": self.archive_byte_count,
            "bootstrap_sha256": self.bootstrap_sha256,
            "archive_format": "DETERMINISTIC_ZIP_STORED_V1",
            "archive_entry_count": (
                len(self.executable_entries)
                + 2 * len(self.dependency_distributions)
            ),
            "sealed_memfd_required": True,
            "live_source_root_fallback_allowed": False,
            "site_package_fallback_allowed": False,
            "dependency_metadata_is_nonexecutable": True,
        }

    @property
    def source_snapshot_id(self) -> str:
        return self._source_snapshot_id

    @property
    def executable_entries(self) -> tuple[Any, ...]:
        return tuple(
            sorted(
                (
                    self.ipc_module_entry,
                    *self.source_manifest.entries,
                    *(
                        entry
                        for distribution in self.dependency_distributions
                        for entry in distribution.source_entries
                    ),
                ),
                key=lambda item: item.module_name,
            )
        )

    @property
    def entries(self) -> tuple[Any, ...]:
        """Backward-compatible alias for executable source entries."""

        return self.executable_entries

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_snapshot_id": self.source_snapshot_id,
        }


def _deterministic_source_archive(
    captured: Mapping[str, bytes],
) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=True,
    ) as archive:
        for relative_path in sorted(captured):
            raw = captured[relative_path]
            info = zipfile.ZipInfo(
                filename=relative_path,
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (0o100444 & 0xFFFF) << 16
            archive.writestr(info, raw)
    return output.getvalue()


def _verify_source_archive_bytes(
    snapshot: V075PublicReplaySourceSnapshotV2,
    raw: bytes,
) -> None:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) != snapshot.archive_byte_count
        or hashlib.sha256(raw).hexdigest() != snapshot.archive_sha256
    ):
        _fail("public replay source archive bytes differ from registration")
    expected: dict[str, tuple[str, int]] = {
        item.relative_path: (item.source_sha256, item.source_byte_count)
        for item in snapshot.executable_entries
    }
    expected.update(
        {
            relative_path: identity
            for distribution in snapshot.dependency_distributions
            for relative_path, identity in (
                (
                    distribution.metadata_relative_path,
                    (
                        distribution.metadata_sha256,
                        distribution.metadata_byte_count,
                    ),
                ),
                (
                    distribution.record_relative_path,
                    (
                        distribution.record_sha256,
                        distribution.record_byte_count,
                    ),
                ),
            )
        }
    )
    captured: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw), mode="r") as archive:
            infos = archive.infolist()
            if (
                len(infos) != len(expected)
                or {item.filename for item in infos} != set(expected)
                or len({item.filename for item in infos}) != len(infos)
            ):
                _fail("public replay source archive entries changed")
            for info in infos:
                source_sha256, source_byte_count = expected[info.filename]
                source = archive.read(info)
                if (
                    info.compress_type != zipfile.ZIP_STORED
                    or info.date_time != (1980, 1, 1, 0, 0, 0)
                    or info.file_size != source_byte_count
                    or len(source) != source_byte_count
                    or hashlib.sha256(source).hexdigest()
                    != source_sha256
                ):
                    _fail("public replay source archive entry changed")
                captured[info.filename] = source
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "public replay source archive is malformed"
        ) from error
    for distribution in snapshot.dependency_distributions:
        _verify_dependency_metadata_and_record(
            distribution,
            captured[distribution.metadata_relative_path],
            captured[distribution.record_relative_path],
        )
    if _deterministic_source_archive(captured) != raw:
        _fail("public replay source archive is not deterministic canonical ZIP")


def _capture_source_snapshot() -> V075PublicReplaySourceSnapshotV2:
    pending = [_VERIFIER_MODULE_NAME]
    captured_local: dict[str, tuple[Path, bytes]] = {}
    while pending:
        module_name = pending.pop()
        if module_name in captured_local:
            continue
        path = _local_module_path(module_name)
        if path is None:
            _fail("registered verifier source closure contains a missing module")
        raw = path.read_bytes()
        captured_local[module_name] = (path, raw)
        pending.extend(
            sorted(
                _local_imports_from_raw(module_name, path, raw)
                - set(captured_local)
            )
        )
        if module_name != "acfqp":
            components = module_name.split(".")
            for end in range(1, len(components)):
                parent = ".".join(components[:end])
                if _local_module_path(parent) is not None:
                    pending.append(parent)
    ipc_path = Path(__file__).resolve()
    captured_local[_IPC_MODULE_NAME] = (ipc_path, ipc_path.read_bytes())
    entries: dict[str, V075PublicReplaySourceManifestEntryV2] = {}
    archive_sources: dict[str, bytes] = {}
    for module_name, (path, raw) in captured_local.items():
        relative_path = path.relative_to(_source_root()).as_posix()
        entries[module_name] = (
            V075PublicReplaySourceManifestEntryV2(
                module_name,
                relative_path,
                hashlib.sha256(raw).hexdigest(),
                len(raw),
            )
        )
        archive_sources[relative_path] = raw
    source_manifest = V075PublicReplaySourceManifestV2(
        tuple(
            entries[name]
            for name in sorted(entries)
            if name != _IPC_MODULE_NAME
        )
    )
    dependency_distributions, dependency_sources = (
        _capture_dependency_distributions()
    )
    if set(archive_sources).intersection(dependency_sources):
        _fail("local and dependency archive paths overlap")
    archive_sources.update(dependency_sources)
    archive_bytes = _deterministic_source_archive(archive_sources)
    return V075PublicReplaySourceSnapshotV2(
        source_manifest,
        entries[_IPC_MODULE_NAME],
        dependency_distributions,
        hashlib.sha256(archive_bytes).hexdigest(),
        len(archive_bytes),
        _BOOTSTRAP_SHA256,
        archive_bytes,
    )


def _freeze_source_manifest() -> V075PublicReplaySourceManifestV2:
    return _capture_source_snapshot().source_manifest


def _interpreter_version() -> str:
    version = sys.version_info
    return (
        f"{version.major}.{version.minor}.{version.micro}:"
        f"{version.releaselevel}:{version.serial}"
    )


def _interpreter_executable_path() -> Path:
    path = Path(sys.executable).resolve()
    if not path.is_file():
        _fail("registered Python executable is absent")
    return path


def _interpreter_executable_sha256() -> str:
    return hashlib.sha256(
        _interpreter_executable_path().read_bytes()
    ).hexdigest()


def _load_portable_verifier() -> Any:
    if _SEALED_CHILD_ARCHIVE_PATH is None:
        source_root = str(Path(__file__).resolve().parents[1])
        if source_root not in sys.path:
            sys.path.insert(0, source_root)
    try:
        portable = importlib.import_module(
            _VERIFIER_MODULE_NAME
        )
    except ImportError as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "registered public replay verifier could not be imported"
        ) from error
    origin = getattr(getattr(portable, "__spec__", None), "origin", None)
    expected_origin = (
        str(_verifier_module_path())
        if _SEALED_CHILD_ARCHIVE_PATH is None
        else (
            f"{_SEALED_CHILD_ARCHIVE_PATH}/"
            "acfqp/v075_portable_occurrence_evidence_bundle_v2.py"
        )
    )
    if (
        portable.__name__ != _VERIFIER_MODULE_NAME
        or origin != expected_origin
        or not callable(getattr(portable, _VERIFIER_CALLABLE, None))
        or portable.MAX_BUNDLE_BYTES != MAX_BUNDLE_FRAME_BYTES
    ):
        _fail("loaded public replay verifier identity differs from registration")
    return portable


def _verify_bundle(raw: bytes) -> Any:
    portable = _load_portable_verifier()
    try:
        return getattr(portable, _VERIFIER_CALLABLE)(raw)
    except Exception as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "portable evidence bundle raw-byte replay failed"
        ) from error


@dataclass(frozen=True, slots=True)
class V075PublicReplayChildProgramRegistrationV2:
    ipc_module_sha256: str
    verifier_module_sha256: str
    source_snapshot: V075PublicReplaySourceSnapshotV2
    runtime_identity: V075PublicReplayRuntimeIdentityV2
    interpreter_implementation: str
    interpreter_version: str
    interpreter_cache_tag: str
    interpreter_executable_sha256: str
    interpreter_executable_byte_count: int
    verifier_module_name: str = _VERIFIER_MODULE_NAME
    verifier_callable: str = _VERIFIER_CALLABLE
    _registration_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.ipc_module_sha256, "public replay child module digest")
        _cid(self.verifier_module_sha256, "public replay verifier digest")
        _cid(
            self.interpreter_executable_sha256,
            "public replay Python executable digest",
        )
        manifest = self.source_snapshot.source_manifest
        verifier_entries = {
            item.module_name: item for item in manifest.entries
        }
        if (
            type(self.source_snapshot) is not V075PublicReplaySourceSnapshotV2
            or type(self.runtime_identity)
            is not V075PublicReplayRuntimeIdentityV2
            or self.ipc_module_sha256
            != self.source_snapshot.ipc_module_entry.source_sha256
            or _VERIFIER_MODULE_NAME not in verifier_entries
            or self.verifier_module_sha256
            != verifier_entries[_VERIFIER_MODULE_NAME].source_sha256
            or self.source_snapshot.bootstrap_sha256 != _BOOTSTRAP_SHA256
            or self.runtime_identity.implementation_name
            != self.interpreter_implementation
            or self.runtime_identity.implementation_cache_tag
            != self.interpreter_cache_tag
            or self.runtime_identity.executable_sha256
            != self.interpreter_executable_sha256
            or self.runtime_identity.executable_byte_count
            != self.interpreter_executable_byte_count
            or self.interpreter_implementation != sys.implementation.name
            or self.interpreter_version != _interpreter_version()
            or self.interpreter_cache_tag
            != (sys.implementation.cache_tag or "")
            or self.interpreter_executable_sha256
            != _interpreter_executable_sha256()
            or type(self.interpreter_executable_byte_count) is not int
            or self.interpreter_executable_byte_count
            != _interpreter_executable_path().stat().st_size
            or self.verifier_module_name != _VERIFIER_MODULE_NAME
            or self.verifier_callable != _VERIFIER_CALLABLE
        ):
            _fail("public replay child program registration is stale")
        object.__setattr__(
            self,
            "_registration_id",
            _hash("program", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_child_program.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "ipc_module_sha256": self.ipc_module_sha256,
            "verifier_module_sha256": self.verifier_module_sha256,
            "source_snapshot": self.source_snapshot.to_document(),
            "source_snapshot_id": self.source_snapshot.source_snapshot_id,
            "source_manifest_id": (
                self.source_snapshot.source_manifest.manifest_id
            ),
            "source_archive_sha256": self.source_snapshot.archive_sha256,
            "source_archive_byte_count": (
                self.source_snapshot.archive_byte_count
            ),
            "bootstrap_sha256": self.source_snapshot.bootstrap_sha256,
            "runtime_identity": self.runtime_identity.to_document(),
            "runtime_identity_id": self.runtime_identity.runtime_identity_id,
            "interpreter_implementation": self.interpreter_implementation,
            "interpreter_version": self.interpreter_version,
            "interpreter_cache_tag": self.interpreter_cache_tag,
            "interpreter_executable_sha256": (
                self.interpreter_executable_sha256
            ),
            "interpreter_executable_byte_count": (
                self.interpreter_executable_byte_count
            ),
            "verifier_module_name": self.verifier_module_name,
            "verifier_callable": self.verifier_callable,
            "bootstrap_invocation": "PYTHON_I_S_C_SEALED_MEMFD_V2",
            "isolated_python": True,
            "site_initialization_allowed": False,
            "expected_child_runtime_flags": (
                _expected_child_runtime_flags()
            ),
            "canonical_length_prefixed_frames_only": True,
            "portable_bundle_bytes_only": True,
            "caller_module_path_allowed": False,
            "caller_environment_inherited": False,
            "arbitrary_callback_allowed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "fresh_heldout_access_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def source_manifest(self) -> V075PublicReplaySourceManifestV2:
        return self.source_snapshot.source_manifest

    @property
    def registration_id(self) -> str:
        return self._registration_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registration_id": self.registration_id}


def registered_v075_public_replay_child_program_v2(
    *,
    source_snapshot: V075PublicReplaySourceSnapshotV2 | None = None,
    runtime_identity: V075PublicReplayRuntimeIdentityV2 | None = None,
) -> V075PublicReplayChildProgramRegistrationV2:
    snapshot = (
        _capture_source_snapshot()
        if source_snapshot is None
        else source_snapshot
    )
    executable = _interpreter_executable_path()
    runtime = (
        _capture_runtime_identity()
        if runtime_identity is None
        else runtime_identity
    )
    verifier_by_name = {
        item.module_name: item for item in snapshot.source_manifest.entries
    }
    return V075PublicReplayChildProgramRegistrationV2(
        snapshot.ipc_module_entry.source_sha256,
        verifier_by_name[_VERIFIER_MODULE_NAME].source_sha256,
        snapshot,
        runtime,
        sys.implementation.name,
        _interpreter_version(),
        sys.implementation.cache_tag or "",
        _interpreter_executable_sha256(),
        executable.stat().st_size,
    )


@dataclass(frozen=True, slots=True)
class V075PublicReplayIPCProfileFreezeWorkV2:
    source_snapshot_captures: int
    source_archive_validation_passes: int
    source_archive_entries_checked: int
    runtime_identity_captures: int
    stdlib_entries_hashed: int
    raw_bundle_verifier_calls: int
    process_launches: int
    _profile_freeze_work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self.source_snapshot_captures != 1
            or self.source_archive_validation_passes != 1
            or type(self.source_archive_entries_checked) is not int
            or self.source_archive_entries_checked <= 0
            or self.runtime_identity_captures != 1
            or type(self.stdlib_entries_hashed) is not int
            or self.stdlib_entries_hashed <= 0
            or self.raw_bundle_verifier_calls != 1
            or self.process_launches != 0
        ):
            _fail("public replay profile-freeze work is incomplete")
        object.__setattr__(
            self,
            "_profile_freeze_work_id",
            _hash("profile_freeze_work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_profile_freeze_work.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_snapshot_captures": self.source_snapshot_captures,
            "source_archive_validation_passes": (
                self.source_archive_validation_passes
            ),
            "source_archive_entries_checked": (
                self.source_archive_entries_checked
            ),
            "runtime_identity_captures": self.runtime_identity_captures,
            "stdlib_entries_hashed": self.stdlib_entries_hashed,
            "raw_bundle_verifier_calls": self.raw_bundle_verifier_calls,
            "process_launches": self.process_launches,
            "lane": "PROFILE_FREEZE",
            "operational_execution_work": False,
            "evaluation_work": False,
            "official_or_economics_cost_eligible": False,
        }

    @property
    def profile_freeze_work_id(self) -> str:
        return self._profile_freeze_work_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "profile_freeze_work_id": self.profile_freeze_work_id,
        }


def _profile_freeze_work(
    snapshot: V075PublicReplaySourceSnapshotV2,
    runtime: V075PublicReplayRuntimeIdentityV2,
) -> V075PublicReplayIPCProfileFreezeWorkV2:
    return V075PublicReplayIPCProfileFreezeWorkV2(
        1,
        1,
        snapshot.to_document()["archive_entry_count"],
        1,
        runtime.stdlib_file_count,
        1,
        0,
    )


_PROFILE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PublicReplayOccurrenceIPCProfileV2:
    _issuer: InitVar[object]
    occurrence_id: str
    portable_bundle_id: str
    portable_bundle_sha256: str
    portable_bundle_byte_count: int
    portable_artifact_count: int
    portable_root_binding_count: int
    process_timeout_seconds: int
    program_registration: V075PublicReplayChildProgramRegistrationV2
    profile_freeze_work: V075PublicReplayIPCProfileFreezeWorkV2
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.occurrence_id, "public replay occurrence")
        _cid(self.portable_bundle_id, "portable evidence bundle")
        _cid(self.portable_bundle_sha256, "portable bundle byte digest")
        if (
            _issuer is not _PROFILE_ISSUER
            or type(self.portable_bundle_byte_count) is not int
            or not 0
            < self.portable_bundle_byte_count
            <= MAX_BUNDLE_FRAME_BYTES
            or type(self.portable_artifact_count) is not int
            or self.portable_artifact_count <= 0
            or type(self.portable_root_binding_count) is not int
            or self.portable_root_binding_count <= 0
            or type(self.process_timeout_seconds) is not int
            or not 0
            < self.process_timeout_seconds
            <= MAX_PROCESS_TIMEOUT_SECONDS
            or type(self.program_registration)
            is not V075PublicReplayChildProgramRegistrationV2
            or type(self.profile_freeze_work)
            is not V075PublicReplayIPCProfileFreezeWorkV2
            or self.profile_freeze_work
            != _profile_freeze_work(
                self.program_registration.source_snapshot,
                self.program_registration.runtime_identity,
            )
        ):
            _fail("public replay IPC profile is untyped, stale, or over cap")
        object.__setattr__(
            self,
            "_profile_id",
            _hash("profile", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_occurrence_ipc_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "occurrence_id": self.occurrence_id,
            "portable_bundle_id": self.portable_bundle_id,
            "portable_bundle_sha256": self.portable_bundle_sha256,
            "portable_bundle_byte_count": self.portable_bundle_byte_count,
            "portable_artifact_count": self.portable_artifact_count,
            "portable_root_binding_count": self.portable_root_binding_count,
            "source_snapshot_id": (
                self.program_registration.source_snapshot.source_snapshot_id
            ),
            "source_archive_sha256": (
                self.program_registration.source_snapshot.archive_sha256
            ),
            "source_archive_byte_count": (
                self.program_registration.source_snapshot.archive_byte_count
            ),
            "bootstrap_sha256": (
                self.program_registration.source_snapshot.bootstrap_sha256
            ),
            "runtime_identity_id": (
                self.program_registration.runtime_identity.runtime_identity_id
            ),
            "program_registration_id": (
                self.program_registration.registration_id
            ),
            "profile_freeze_work": self.profile_freeze_work.to_document(),
            "profile_freeze_work_id": (
                self.profile_freeze_work.profile_freeze_work_id
            ),
            "process_timeout_seconds": self.process_timeout_seconds,
            "max_launch_frame_bytes": MAX_LAUNCH_FRAME_BYTES,
            "max_bundle_frame_bytes": MAX_BUNDLE_FRAME_BYTES,
            "max_result_frame_bytes": MAX_RESULT_FRAME_BYTES,
            "max_child_stderr_bytes": MAX_CHILD_STDERR_BYTES,
            "parent_completed_acquisition_before_ipc": True,
            "parent_froze_portable_bundle_before_ipc": True,
            "child_observation_access_allowed": False,
            "child_signing_allowed": False,
            "child_acquisition_allowed": False,
            "semantic_registry_replay_complete": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "fresh_heldout_accessed": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "program_registration": self.program_registration.to_document(),
            "profile_id": self.profile_id,
        }


def freeze_v075_public_replay_occurrence_ipc_profile_v2(
    *,
    portable_bundle_bytes: bytes,
    process_timeout_seconds: int = DEFAULT_PROCESS_TIMEOUT_SECONDS,
) -> V075PublicReplayOccurrenceIPCProfileV2:
    """Verify public bytes in the parent and bind one immutable child launch."""

    source_snapshot = _capture_source_snapshot()
    runtime_identity = _capture_runtime_identity()
    program = registered_v075_public_replay_child_program_v2(
        source_snapshot=source_snapshot,
        runtime_identity=runtime_identity,
    )
    bundle = _verify_bundle(portable_bundle_bytes)
    return V075PublicReplayOccurrenceIPCProfileV2(
        _PROFILE_ISSUER,
        bundle.occurrence_id,
        bundle.bundle_id,
        hashlib.sha256(portable_bundle_bytes).hexdigest(),
        len(portable_bundle_bytes),
        len(bundle.records),
        len(bundle.root_bindings),
        process_timeout_seconds,
        program,
        _profile_freeze_work(source_snapshot, runtime_identity),
    )


def _source_manifest_from_document(
    value: Any,
) -> V075PublicReplaySourceManifestV2:
    manifest_item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "profile_key",
            "root_module",
            "closure_rule",
            "entries",
            "entry_count",
            "manifest_id",
        },
        field_name="public replay source manifest",
    )
    raw_entries = manifest_item["entries"]
    if (
        manifest_item["schema"]
        != "acfqp.v075_public_replay_source_manifest.v2"
        or manifest_item["schema_version"] != SCHEMA_VERSION
        or manifest_item["profile_key"] != PROFILE_KEY
        or manifest_item["root_module"] != _VERIFIER_MODULE_NAME
        or manifest_item["closure_rule"]
        != "RECURSIVE_STATIC_LOCAL_ACFQP_IMPORTS"
        or type(raw_entries) is not list
        or manifest_item["entry_count"] != len(raw_entries)
    ):
        _fail("public replay source manifest metadata changed")
    entries: list[V075PublicReplaySourceManifestEntryV2] = []
    for raw_entry in raw_entries:
        source = _exact_mapping(
            raw_entry,
            {
                "module_name",
                "relative_path",
                "source_sha256",
                "source_byte_count",
            },
            field_name="public replay source manifest entry",
        )
        entries.append(
            V075PublicReplaySourceManifestEntryV2(
                source["module_name"],
                source["relative_path"],
                source["source_sha256"],
                source["source_byte_count"],
            )
        )
    manifest = V075PublicReplaySourceManifestV2(tuple(entries))
    if (
        manifest.manifest_id != manifest_item["manifest_id"]
        or manifest.to_document() != manifest_item
    ):
        _fail("public replay source manifest content identity changed")
    return manifest


def _source_entry_from_document(
    value: Any,
) -> V075PublicReplaySourceManifestEntryV2:
    item = _exact_mapping(
        value,
        {
            "module_name",
            "relative_path",
            "source_sha256",
            "source_byte_count",
        },
        field_name="public replay source snapshot IPC entry",
    )
    return V075PublicReplaySourceManifestEntryV2(
        item["module_name"],
        item["relative_path"],
        item["source_sha256"],
        item["source_byte_count"],
    )


def _dependency_distribution_from_document(
    value: Any,
) -> V075PublicReplayDependencyDistributionV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "profile_key",
            "distribution_name",
            "distribution_version",
            "root_module",
            "metadata_relative_path",
            "metadata_distribution_path",
            "metadata_sha256",
            "metadata_byte_count",
            "record_relative_path",
            "record_distribution_path",
            "record_sha256",
            "record_byte_count",
            "source_entries",
            "source_entry_count",
            "pure_python_source_closure_complete",
            "native_extension_entries_allowed",
            "raw_metadata_name_version_verified",
            "raw_record_membership_verified",
            "site_package_fallback_allowed",
            "dependency_lock_authority",
            "independent_distribution_authority_verified",
            "production_dependency_lock",
            "distribution_id",
        },
        field_name="public replay dependency distribution",
    )
    raw_entries = item["source_entries"]
    if (
        item["schema"]
        != "acfqp.v075_public_replay_dependency_distribution.v2"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != PROFILE_KEY
        or type(raw_entries) is not list
        or item["source_entry_count"] != len(raw_entries)
        or item["pure_python_source_closure_complete"] is not True
        or item["native_extension_entries_allowed"] is not False
        or item["raw_metadata_name_version_verified"] is not True
        or item["raw_record_membership_verified"] is not True
        or item["site_package_fallback_allowed"] is not False
        or item["dependency_lock_authority"]
        != "CONSTRUCTION_LOCAL_PREREGISTERED_CAPTURE_ONLY"
        or item["independent_distribution_authority_verified"] is not False
        or item["production_dependency_lock"] is not False
    ):
        _fail("public replay dependency metadata changed")
    entries: list[V075PublicReplayDependencySourceEntryV2] = []
    for raw_entry in raw_entries:
        entry = _exact_mapping(
            raw_entry,
            {
                "distribution_name",
                "distribution_version",
                "module_name",
                "relative_path",
                "source_sha256",
                "source_byte_count",
            },
            field_name="public replay dependency source entry",
        )
        entries.append(
            V075PublicReplayDependencySourceEntryV2(
                entry["distribution_name"],
                entry["distribution_version"],
                entry["module_name"],
                entry["relative_path"],
                entry["source_sha256"],
                entry["source_byte_count"],
            )
        )
    distribution = V075PublicReplayDependencyDistributionV2(
        item["distribution_name"],
        item["distribution_version"],
        item["root_module"],
        item["metadata_relative_path"],
        item["metadata_distribution_path"],
        item["metadata_sha256"],
        item["metadata_byte_count"],
        item["record_relative_path"],
        item["record_distribution_path"],
        item["record_sha256"],
        item["record_byte_count"],
        tuple(entries),
    )
    if (
        distribution.distribution_id != item["distribution_id"]
        or distribution.to_document() != item
    ):
        _fail("public replay dependency content identity changed")
    return distribution


def _runtime_identity_from_document(
    value: Any,
) -> V075PublicReplayRuntimeIdentityV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "profile_key",
            "implementation_name",
            "implementation_cache_tag",
            "implementation_version",
            "sys_version",
            "hexversion",
            "api_version",
            "byteorder",
            "maxsize",
            "abiflags",
            "soabi",
            "multiarch",
            "sysconfig_platform",
            "python_build",
            "python_compiler",
            "config_args",
            "cc",
            "executable",
            "shared_library",
            "stdlib",
            "host_abi",
            "cryptographic_or_os_remote_attestation",
            "runtime_identity_id",
        },
        field_name="public replay runtime identity",
    )
    executable = _exact_mapping(
        item["executable"],
        {"sha256_file_bytes", "file_byte_count"},
        field_name="public replay runtime executable",
    )
    shared_library = _exact_mapping(
        item["shared_library"],
        {"sha256_file_bytes", "file_byte_count"},
        field_name="public replay runtime shared library",
    )
    stdlib = _exact_mapping(
        item["stdlib"],
        {"file_count", "tree_digest"},
        field_name="public replay runtime stdlib",
    )
    host_abi = _exact_mapping(
        item["host_abi"],
        {"system", "machine", "libc_name", "libc_version"},
        field_name="public replay runtime host ABI",
    )
    if (
        item["schema"] != "acfqp.v075_public_replay_runtime_identity.v2"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != PROFILE_KEY
        or type(item["implementation_version"]) is not list
        or len(item["implementation_version"]) != 5
        or type(item["python_build"]) is not list
        or len(item["python_build"]) != 2
        or item["cryptographic_or_os_remote_attestation"] is not False
    ):
        _fail("public replay runtime identity metadata changed")
    runtime = V075PublicReplayRuntimeIdentityV2(
        item["implementation_name"],
        item["implementation_cache_tag"],
        tuple(item["implementation_version"]),
        item["sys_version"],
        item["hexversion"],
        item["api_version"],
        item["byteorder"],
        item["maxsize"],
        item["abiflags"],
        item["soabi"],
        item["multiarch"],
        item["sysconfig_platform"],
        tuple(item["python_build"]),
        item["python_compiler"],
        item["config_args"],
        item["cc"],
        executable["sha256_file_bytes"],
        executable["file_byte_count"],
        shared_library["sha256_file_bytes"],
        shared_library["file_byte_count"],
        stdlib["file_count"],
        stdlib["tree_digest"],
        host_abi["system"],
        host_abi["machine"],
        host_abi["libc_name"],
        host_abi["libc_version"],
    )
    if (
        runtime.runtime_identity_id != item["runtime_identity_id"]
        or runtime.to_document() != item
    ):
        _fail("public replay runtime content identity changed")
    return runtime


def _source_snapshot_from_document(
    value: Any,
    *,
    archive_bytes: bytes = b"",
) -> V075PublicReplaySourceSnapshotV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "profile_key",
            "source_manifest",
            "source_manifest_id",
            "ipc_module_entry",
            "dependency_distributions",
            "dependency_distribution_ids",
            "dependency_distribution_count",
            "preregistered_dependency_lock",
            "preregistered_dependency_lock_id",
            "archive_sha256",
            "archive_byte_count",
            "bootstrap_sha256",
            "archive_format",
            "archive_entry_count",
            "sealed_memfd_required",
            "live_source_root_fallback_allowed",
            "site_package_fallback_allowed",
            "dependency_metadata_is_nonexecutable",
            "source_snapshot_id",
        },
        field_name="public replay source snapshot",
    )
    manifest = _source_manifest_from_document(item["source_manifest"])
    ipc_entry = _source_entry_from_document(item["ipc_module_entry"])
    raw_dependencies = item["dependency_distributions"]
    if type(raw_dependencies) is not list:
        _fail("public replay dependency distributions are malformed")
    dependencies = tuple(
        _dependency_distribution_from_document(value)
        for value in raw_dependencies
    )
    expected_dependency_lock = _dependency_lock_document(dependencies)
    if (
        item["schema"] != "acfqp.v075_public_replay_source_snapshot.v2"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["source_manifest_id"] != manifest.manifest_id
        or item["dependency_distribution_ids"]
        != [value.distribution_id for value in dependencies]
        or item["dependency_distribution_count"] != len(dependencies)
        or item["preregistered_dependency_lock"]
        != expected_dependency_lock
        or item["preregistered_dependency_lock_id"]
        != expected_dependency_lock["dependency_lock_id"]
        or item["archive_format"] != "DETERMINISTIC_ZIP_STORED_V1"
        or item["archive_entry_count"]
        != (
            len(manifest.entries)
            + 1
            + sum(len(value.source_entries) for value in dependencies)
            + 2 * len(dependencies)
        )
        or item["sealed_memfd_required"] is not True
        or item["live_source_root_fallback_allowed"] is not False
        or item["site_package_fallback_allowed"] is not False
        or item["dependency_metadata_is_nonexecutable"] is not True
    ):
        _fail("public replay source snapshot metadata changed")
    snapshot = V075PublicReplaySourceSnapshotV2(
        manifest,
        ipc_entry,
        dependencies,
        item["archive_sha256"],
        item["archive_byte_count"],
        item["bootstrap_sha256"],
        archive_bytes,
    )
    if (
        snapshot.source_snapshot_id != item["source_snapshot_id"]
        or snapshot.to_document() != item
    ):
        _fail("public replay source snapshot content identity changed")
    return snapshot


def _program_from_document(
    value: Any,
    *,
    archive_bytes: bytes = b"",
) -> V075PublicReplayChildProgramRegistrationV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "ipc_module_sha256",
            "verifier_module_sha256",
            "source_snapshot",
            "source_snapshot_id",
            "source_manifest_id",
            "source_archive_sha256",
            "source_archive_byte_count",
            "bootstrap_sha256",
            "runtime_identity",
            "runtime_identity_id",
            "interpreter_implementation",
            "interpreter_version",
            "interpreter_cache_tag",
            "interpreter_executable_sha256",
            "interpreter_executable_byte_count",
            "verifier_module_name",
            "verifier_callable",
            "bootstrap_invocation",
            "isolated_python",
            "site_initialization_allowed",
            "expected_child_runtime_flags",
            "canonical_length_prefixed_frames_only",
            "portable_bundle_bytes_only",
            "caller_module_path_allowed",
            "caller_environment_inherited",
            "arbitrary_callback_allowed",
            "official_execution_allowed",
            "production_authorizing",
            "fresh_heldout_access_allowed",
            "plan_certificate",
            "infeasibility_certificate",
            "registration_id",
        },
        field_name="public replay program registration",
    )
    if (
        item["schema"] != "acfqp.v075_public_replay_child_program.v2"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["bootstrap_invocation"]
        != "PYTHON_I_S_C_SEALED_MEMFD_V2"
        or item["isolated_python"] is not True
        or item["site_initialization_allowed"] is not False
        or item["expected_child_runtime_flags"]
        != _expected_child_runtime_flags()
        or item["canonical_length_prefixed_frames_only"] is not True
        or item["portable_bundle_bytes_only"] is not True
        or item["caller_module_path_allowed"] is not False
        or item["caller_environment_inherited"] is not False
        or item["arbitrary_callback_allowed"] is not False
        or item["official_execution_allowed"] is not False
        or item["production_authorizing"] is not False
        or item["fresh_heldout_access_allowed"] is not False
        or item["plan_certificate"] is not False
        or item["infeasibility_certificate"] is not False
    ):
        _fail("public replay program registration metadata changed")
    snapshot = _source_snapshot_from_document(
        item["source_snapshot"],
        archive_bytes=archive_bytes,
    )
    runtime_identity = _runtime_identity_from_document(
        item["runtime_identity"]
    )
    if (
        item["source_snapshot_id"] != snapshot.source_snapshot_id
        or item["source_manifest_id"] != snapshot.source_manifest.manifest_id
        or item["source_archive_sha256"] != snapshot.archive_sha256
        or item["source_archive_byte_count"] != snapshot.archive_byte_count
        or item["bootstrap_sha256"] != snapshot.bootstrap_sha256
        or item["runtime_identity_id"]
        != runtime_identity.runtime_identity_id
    ):
        _fail("public replay program source binding changed")
    program = V075PublicReplayChildProgramRegistrationV2(
        item["ipc_module_sha256"],
        item["verifier_module_sha256"],
        snapshot,
        runtime_identity,
        item["interpreter_implementation"],
        item["interpreter_version"],
        item["interpreter_cache_tag"],
        item["interpreter_executable_sha256"],
        item["interpreter_executable_byte_count"],
        item["verifier_module_name"],
        item["verifier_callable"],
    )
    if (
        program.registration_id != item["registration_id"]
        or program.to_document() != item
    ):
        _fail("public replay program content identity changed")
    return program


def _profile_freeze_work_from_document(
    value: Any,
) -> V075PublicReplayIPCProfileFreezeWorkV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "profile_key",
            "source_snapshot_captures",
            "source_archive_validation_passes",
            "source_archive_entries_checked",
            "runtime_identity_captures",
            "stdlib_entries_hashed",
            "raw_bundle_verifier_calls",
            "process_launches",
            "lane",
            "operational_execution_work",
            "evaluation_work",
            "official_or_economics_cost_eligible",
            "profile_freeze_work_id",
        },
        field_name="public replay profile-freeze work",
    )
    if (
        item["schema"] != "acfqp.v075_public_replay_profile_freeze_work.v2"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["lane"] != "PROFILE_FREEZE"
        or item["operational_execution_work"] is not False
        or item["evaluation_work"] is not False
        or item["official_or_economics_cost_eligible"] is not False
    ):
        _fail("public replay profile-freeze work metadata changed")
    work = V075PublicReplayIPCProfileFreezeWorkV2(
        item["source_snapshot_captures"],
        item["source_archive_validation_passes"],
        item["source_archive_entries_checked"],
        item["runtime_identity_captures"],
        item["stdlib_entries_hashed"],
        item["raw_bundle_verifier_calls"],
        item["process_launches"],
    )
    if (
        work.profile_freeze_work_id != item["profile_freeze_work_id"]
        or work.to_document() != item
    ):
        _fail("public replay profile-freeze work identity changed")
    return work


_PROFILE_DOCUMENT_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "terminal_scope",
    "terminal_class",
    "occurrence_id",
    "portable_bundle_id",
    "portable_bundle_sha256",
    "portable_bundle_byte_count",
    "portable_artifact_count",
    "portable_root_binding_count",
    "source_snapshot_id",
    "source_archive_sha256",
    "source_archive_byte_count",
    "bootstrap_sha256",
    "runtime_identity_id",
    "program_registration_id",
    "profile_freeze_work",
    "profile_freeze_work_id",
    "process_timeout_seconds",
    "max_launch_frame_bytes",
    "max_bundle_frame_bytes",
    "max_result_frame_bytes",
    "max_child_stderr_bytes",
    "parent_completed_acquisition_before_ipc",
    "parent_froze_portable_bundle_before_ipc",
    "child_observation_access_allowed",
    "child_signing_allowed",
    "child_acquisition_allowed",
    "semantic_registry_replay_complete",
    "official_execution_allowed",
    "production_authorizing",
    "fresh_heldout_accessed",
    "scientific_endpoint_credit_allowed",
    "plan_certificate",
    "infeasibility_certificate",
    "program_registration",
    "profile_id",
}


def _profile_from_document(
    value: Any,
    *,
    archive_bytes: bytes = b"",
) -> V075PublicReplayOccurrenceIPCProfileV2:
    item = _exact_mapping(
        value,
        _PROFILE_DOCUMENT_KEYS,
        field_name="public replay IPC profile",
    )
    program = _program_from_document(
        item["program_registration"],
        archive_bytes=archive_bytes,
    )
    profile_freeze_work = _profile_freeze_work_from_document(
        item["profile_freeze_work"]
    )
    if (
        item["schema"]
        != "acfqp.v075_public_replay_occurrence_ipc_profile.v2"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["terminal_scope"] != TERMINAL_SCOPE
        or item["terminal_class"] != TERMINAL_CLASS
        or item["program_registration_id"] != program.registration_id
        or item["profile_freeze_work_id"]
        != profile_freeze_work.profile_freeze_work_id
        or item["source_snapshot_id"]
        != program.source_snapshot.source_snapshot_id
        or item["source_archive_sha256"]
        != program.source_snapshot.archive_sha256
        or item["source_archive_byte_count"]
        != program.source_snapshot.archive_byte_count
        or item["bootstrap_sha256"]
        != program.source_snapshot.bootstrap_sha256
        or item["runtime_identity_id"]
        != program.runtime_identity.runtime_identity_id
        or item["max_launch_frame_bytes"] != MAX_LAUNCH_FRAME_BYTES
        or item["max_bundle_frame_bytes"] != MAX_BUNDLE_FRAME_BYTES
        or item["max_result_frame_bytes"] != MAX_RESULT_FRAME_BYTES
        or item["max_child_stderr_bytes"] != MAX_CHILD_STDERR_BYTES
        or item["parent_completed_acquisition_before_ipc"] is not True
        or item["parent_froze_portable_bundle_before_ipc"] is not True
        or item["child_observation_access_allowed"] is not False
        or item["child_signing_allowed"] is not False
        or item["child_acquisition_allowed"] is not False
        or item["semantic_registry_replay_complete"] is not False
        or item["official_execution_allowed"] is not False
        or item["production_authorizing"] is not False
        or item["fresh_heldout_accessed"] is not False
        or item["scientific_endpoint_credit_allowed"] is not False
        or item["plan_certificate"] is not False
        or item["infeasibility_certificate"] is not False
    ):
        _fail("public replay IPC profile metadata changed")
    profile = V075PublicReplayOccurrenceIPCProfileV2(
        _PROFILE_ISSUER,
        item["occurrence_id"],
        item["portable_bundle_id"],
        item["portable_bundle_sha256"],
        item["portable_bundle_byte_count"],
        item["portable_artifact_count"],
        item["portable_root_binding_count"],
        item["process_timeout_seconds"],
        program,
        profile_freeze_work,
    )
    if profile.profile_id != item["profile_id"] or profile.to_document() != item:
        _fail("public replay IPC profile content identity changed")
    return profile


def _launch_document(
    profile: V075PublicReplayOccurrenceIPCProfileV2,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_public_replay_occurrence_ipc_launch.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "profile": profile.to_document(),
        "one_portable_bundle_frame_follows": True,
        "child_result_frame_count": 1,
        "official_execution_allowed": False,
        "production_authorizing": False,
        "fresh_heldout_accessed": False,
        "plan_certificate": False,
        "infeasibility_certificate": False,
    }
    return {**payload, "launch_id": _hash("launch", payload)}


def _load_launch(
    raw: bytes,
) -> tuple[dict[str, Any], V075PublicReplayOccurrenceIPCProfileV2]:
    item = _exact_mapping(
        _load_canonical(
            raw,
            field_name="public replay launch",
            byte_cap=MAX_LAUNCH_FRAME_BYTES,
        ),
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "profile",
            "one_portable_bundle_frame_follows",
            "child_result_frame_count",
            "official_execution_allowed",
            "production_authorizing",
            "fresh_heldout_accessed",
            "plan_certificate",
            "infeasibility_certificate",
            "launch_id",
        },
        field_name="public replay launch",
    )
    payload = {key: value for key, value in item.items() if key != "launch_id"}
    if (
        item["schema"]
        != "acfqp.v075_public_replay_occurrence_ipc_launch.v2"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["one_portable_bundle_frame_follows"] is not True
        or item["child_result_frame_count"] != 1
        or item["official_execution_allowed"] is not False
        or item["production_authorizing"] is not False
        or item["fresh_heldout_accessed"] is not False
        or item["plan_certificate"] is not False
        or item["infeasibility_certificate"] is not False
        or item["launch_id"] != _hash("launch", payload)
    ):
        _fail("public replay launch metadata or content identity changed")
    return item, _profile_from_document(item["profile"])


_CHILD_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PublicReplayLoadedSourceEntryV2:
    module_name: str
    relative_path: str
    source_sha256: str
    source_byte_count: int
    normalized_origin: str

    def __post_init__(self) -> None:
        _cid(self.source_sha256, "loaded public replay source digest")
        if (
            type(self.module_name) is not str
            or type(self.relative_path) is not str
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
            or self.normalized_origin
            != f"sealed-memfd://snapshot/{self.relative_path}"
        ):
            _fail("loaded public replay source entry is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "module_name": self.module_name,
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
            "normalized_origin": self.normalized_origin,
        }


@dataclass(frozen=True, slots=True)
class V075PublicReplayLoadedSourceManifestV2:
    source_snapshot_id: str
    entries: tuple[V075PublicReplayLoadedSourceEntryV2, ...]
    _loaded_manifest_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.source_snapshot_id, "loaded source snapshot")
        if (
            type(self.entries) is not tuple
            or not self.entries
            or any(
                type(item) is not V075PublicReplayLoadedSourceEntryV2
                for item in self.entries
            )
            or tuple(item.module_name for item in self.entries)
            != tuple(sorted(item.module_name for item in self.entries))
            or len({item.module_name for item in self.entries})
            != len(self.entries)
        ):
            _fail("loaded public replay source manifest is malformed")
        object.__setattr__(
            self,
            "_loaded_manifest_id",
            _hash("loaded_source_manifest", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_loaded_source_manifest.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_snapshot_id": self.source_snapshot_id,
            "entries": [item.to_document() for item in self.entries],
            "entry_count": len(self.entries),
            "all_origins_sealed_memfd": True,
            "live_source_root_fallback_used": False,
        }

    @property
    def loaded_manifest_id(self) -> str:
        return self._loaded_manifest_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "loaded_manifest_id": self.loaded_manifest_id,
        }


def _expected_loaded_source_manifest(
    snapshot: V075PublicReplaySourceSnapshotV2,
) -> V075PublicReplayLoadedSourceManifestV2:
    return V075PublicReplayLoadedSourceManifestV2(
        snapshot.source_snapshot_id,
        tuple(
            V075PublicReplayLoadedSourceEntryV2(
                item.module_name,
                item.relative_path,
                item.source_sha256,
                item.source_byte_count,
                f"sealed-memfd://snapshot/{item.relative_path}",
            )
            for item in snapshot.entries
        ),
    )


@dataclass(frozen=True, slots=True)
class V075PublicReplayChildVerificationResultV2:
    _issuer: InitVar[object]
    profile_id: str
    program_registration_id: str
    occurrence_id: str
    portable_bundle_id: str
    portable_bundle_sha256: str
    portable_bundle_byte_count: int
    artifact_count: int
    root_binding_count: int
    source_snapshot_id: str
    loaded_source_manifest: V075PublicReplayLoadedSourceManifestV2
    _child_result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, name in (
            (self.profile_id, "public replay profile"),
            (self.program_registration_id, "public replay program"),
            (self.occurrence_id, "public replay occurrence"),
            (self.portable_bundle_id, "portable evidence bundle"),
            (self.portable_bundle_sha256, "portable bundle byte digest"),
            (self.source_snapshot_id, "public replay source snapshot"),
        ):
            _cid(value, name)
        if (
            _issuer is not _CHILD_RESULT_ISSUER
            or type(self.portable_bundle_byte_count) is not int
            or not 0
            < self.portable_bundle_byte_count
            <= MAX_BUNDLE_FRAME_BYTES
            or type(self.artifact_count) is not int
            or self.artifact_count <= 0
            or type(self.root_binding_count) is not int
            or self.root_binding_count <= 0
            or type(self.loaded_source_manifest)
            is not V075PublicReplayLoadedSourceManifestV2
            or self.loaded_source_manifest.source_snapshot_id
            != self.source_snapshot_id
        ):
            _fail("public replay child verification result is malformed")
        object.__setattr__(
            self,
            "_child_result_id",
            _hash("child_result", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_child_result.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "profile_id": self.profile_id,
            "program_registration_id": self.program_registration_id,
            "occurrence_id": self.occurrence_id,
            "portable_bundle_id": self.portable_bundle_id,
            "portable_bundle_sha256": self.portable_bundle_sha256,
            "portable_bundle_byte_count": self.portable_bundle_byte_count,
            "artifact_count": self.artifact_count,
            "root_binding_count": self.root_binding_count,
            "source_snapshot_id": self.source_snapshot_id,
            "loaded_source_manifest": (
                self.loaded_source_manifest.to_document()
            ),
            "loaded_source_manifest_id": (
                self.loaded_source_manifest.loaded_manifest_id
            ),
            "raw_bundle_bytes_verified": True,
            "topological_dependency_replay_complete": True,
            "role_specific_raw_replay_complete": True,
            "semantic_registry_replay_complete": False,
            "child_observation_accessed": False,
            "child_signing_performed": False,
            "child_acquisition_performed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "fresh_heldout_accessed": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def child_result_id(self) -> str:
        return self._child_result_id

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "child_result_id": self.child_result_id}


def _expected_child_result(
    profile: V075PublicReplayOccurrenceIPCProfileV2,
    raw: bytes,
    *,
    verified_bundle: Any | None = None,
    loaded_source_manifest: (
        V075PublicReplayLoadedSourceManifestV2 | None
    ) = None,
) -> V075PublicReplayChildVerificationResultV2:
    if (
        hashlib.sha256(raw).hexdigest()
        != profile.portable_bundle_sha256
        or len(raw) != profile.portable_bundle_byte_count
        or (
            verified_bundle is not None
            and (
                verified_bundle.occurrence_id != profile.occurrence_id
                or verified_bundle.bundle_id != profile.portable_bundle_id
                or len(verified_bundle.records)
                != profile.portable_artifact_count
                or len(verified_bundle.root_bindings)
                != profile.portable_root_binding_count
            )
        )
    ):
        _fail("portable bundle bytes differ from the frozen replay profile")
    expected_loaded = _expected_loaded_source_manifest(
        profile.program_registration.source_snapshot
    )
    if (
        loaded_source_manifest is not None
        and loaded_source_manifest != expected_loaded
    ):
        _fail("child loaded source manifest differs from sealed snapshot")
    return V075PublicReplayChildVerificationResultV2(
        _CHILD_RESULT_ISSUER,
        profile.profile_id,
        profile.program_registration.registration_id,
        profile.occurrence_id,
        profile.portable_bundle_id,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
        profile.portable_artifact_count,
        profile.portable_root_binding_count,
        profile.program_registration.source_snapshot.source_snapshot_id,
        expected_loaded,
    )


def _validate_child_result(
    raw: bytes,
    expected: V075PublicReplayChildVerificationResultV2,
) -> V075PublicReplayChildVerificationResultV2:
    claimed = _load_canonical(
        raw,
        field_name="public replay child result",
        byte_cap=MAX_RESULT_FRAME_BYTES,
    )
    if (
        type(claimed) is not dict
        or claimed != expected.to_document()
        or raw != expected.canonical_bytes
    ):
        _fail(
            "child result differs from independent host reconstruction"
        )
    return expected


@dataclass(frozen=True, slots=True)
class V075PublicReplayIPCJournalEntryV2:
    sequence_number: int
    direction: str
    message_kind: str
    message_id: str
    message_byte_count: int
    message_sha256: str
    previous_entry_id: str
    _entry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.message_id, "public replay journal message"),
            (self.message_sha256, "public replay message byte digest"),
            (self.previous_entry_id, "public replay previous journal entry"),
        ):
            _cid(value, name)
        if (
            type(self.sequence_number) is not int
            or self.sequence_number <= 0
            or self.direction
            not in {"PARENT_TO_CHILD", "CHILD_TO_PARENT"}
            or self.message_kind not in {
                "PROGRAM_IDENTITY_AND_LAUNCH",
                "PORTABLE_EVIDENCE_BUNDLE",
                "TYPED_VERIFICATION_RESULT",
            }
            or type(self.message_byte_count) is not int
            or self.message_byte_count <= 0
        ):
            _fail("public replay IPC journal entry is malformed")
        object.__setattr__(
            self,
            "_entry_id",
            _hash("journal_entry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_ipc_journal_entry.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence_number": self.sequence_number,
            "direction": self.direction,
            "message_kind": self.message_kind,
            "message_id": self.message_id,
            "message_byte_count": self.message_byte_count,
            "message_sha256": self.message_sha256,
            "previous_entry_id": self.previous_entry_id,
        }

    @property
    def entry_id(self) -> str:
        return self._entry_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


def _journal_entry(
    entries: list[V075PublicReplayIPCJournalEntryV2],
    *,
    direction: str,
    message_kind: str,
    message_id: str,
    raw: bytes,
) -> V075PublicReplayIPCJournalEntryV2:
    entry = V075PublicReplayIPCJournalEntryV2(
        len(entries) + 1,
        direction,
        message_kind,
        message_id,
        len(raw),
        hashlib.sha256(raw).hexdigest(),
        _INITIAL_JOURNAL_HASH if not entries else entries[-1].entry_id,
    )
    entries.append(entry)
    return entry


@dataclass(frozen=True, slots=True)
class V075PublicReplayIPCJournalV2:
    entries: tuple[V075PublicReplayIPCJournalEntryV2, ...]
    _journal_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.entries) is not tuple
            or len(self.entries) != 3
            or any(
                type(item) is not V075PublicReplayIPCJournalEntryV2
                for item in self.entries
            )
            or tuple(item.sequence_number for item in self.entries)
            != (1, 2, 3)
            or tuple(item.direction for item in self.entries)
            != (
                "PARENT_TO_CHILD",
                "PARENT_TO_CHILD",
                "CHILD_TO_PARENT",
            )
            or tuple(item.message_kind for item in self.entries)
            != (
                "PROGRAM_IDENTITY_AND_LAUNCH",
                "PORTABLE_EVIDENCE_BUNDLE",
                "TYPED_VERIFICATION_RESULT",
            )
        ):
            _fail("public replay IPC journal sequence is incomplete")
        previous = _INITIAL_JOURNAL_HASH
        for entry in self.entries:
            if entry.previous_entry_id != previous:
                _fail("public replay IPC journal hash chain changed")
            previous = entry.entry_id
        object.__setattr__(
            self,
            "_journal_id",
            _hash("journal", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_ipc_journal.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "entries": [item.to_document() for item in self.entries],
            "entry_count": len(self.entries),
            "hash_chain_complete": True,
        }

    @property
    def journal_id(self) -> str:
        return self._journal_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "journal_id": self.journal_id}


@dataclass(frozen=True, slots=True)
class V075PublicReplayIPCOperationalSuccessWorkV2:
    process_launches: int
    parent_to_child_frames: int
    child_to_parent_frames: int
    parent_to_child_payload_bytes: int
    child_to_parent_payload_bytes: int
    framing_bytes: int
    raw_bundle_verifier_calls_parent_execution: int
    raw_bundle_verifier_calls_child: int
    staged_bytes: int
    source_snapshot_bytes: int
    sealed_memfd_count: int
    source_archive_validation_passes_parent_execution: int
    source_archive_entry_checks_parent_execution: int
    seal_verification_checks_parent_execution: int
    seal_verification_checks_child: int
    loaded_source_checks_child: int
    loaded_source_entry_checks_child: int
    process_exit_code: int
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self.process_launches != 1
            or self.parent_to_child_frames != 2
            or self.child_to_parent_frames != 1
            or type(self.parent_to_child_payload_bytes) is not int
            or self.parent_to_child_payload_bytes <= 0
            or type(self.child_to_parent_payload_bytes) is not int
            or self.child_to_parent_payload_bytes <= 0
            or self.framing_bytes != 3 * _FRAME_WIDTH
            or self.raw_bundle_verifier_calls_parent_execution != 0
            or self.raw_bundle_verifier_calls_child != 1
            or type(self.staged_bytes) is not int
            or self.staged_bytes <= 0
            or self.source_snapshot_bytes != self.staged_bytes
            or self.sealed_memfd_count != 1
            or self.source_archive_validation_passes_parent_execution != 2
            or type(self.source_archive_entry_checks_parent_execution)
            is not int
            or self.source_archive_entry_checks_parent_execution <= 0
            or self.seal_verification_checks_parent_execution != 1
            or self.seal_verification_checks_child != 2
            or self.loaded_source_checks_child != 2
            or type(self.loaded_source_entry_checks_child) is not int
            or self.loaded_source_entry_checks_child <= 0
            or self.process_exit_code != 0
        ):
            _fail("public replay IPC operational success work is incomplete")
        object.__setattr__(
            self,
            "_work_id",
            _hash("work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_public_replay_ipc_"
                "operational_success_work.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "process_launches": self.process_launches,
            "parent_to_child_frames": self.parent_to_child_frames,
            "child_to_parent_frames": self.child_to_parent_frames,
            "parent_to_child_payload_bytes": (
                self.parent_to_child_payload_bytes
            ),
            "child_to_parent_payload_bytes": (
                self.child_to_parent_payload_bytes
            ),
            "framing_bytes": self.framing_bytes,
            "raw_bundle_verifier_calls_parent_execution": (
                self.raw_bundle_verifier_calls_parent_execution
            ),
            "raw_bundle_verifier_calls_child": (
                self.raw_bundle_verifier_calls_child
            ),
            "staged_bytes": self.staged_bytes,
            "source_snapshot_bytes": self.source_snapshot_bytes,
            "source_snapshot_bytes_derived_only": True,
            "sealed_memfd_count": self.sealed_memfd_count,
            "source_archive_validation_passes_parent_execution": (
                self.source_archive_validation_passes_parent_execution
            ),
            "source_archive_entry_checks_parent_execution": (
                self.source_archive_entry_checks_parent_execution
            ),
            "seal_verification_checks_parent_execution": (
                self.seal_verification_checks_parent_execution
            ),
            "seal_verification_checks_child": (
                self.seal_verification_checks_child
            ),
            "loaded_source_checks_child": self.loaded_source_checks_child,
            "loaded_source_entry_checks_child": (
                self.loaded_source_entry_checks_child
            ),
            "process_exit_code": self.process_exit_code,
            "operational_lane": "CONSTRUCTION_PUBLIC_REPLAY",
            "evaluation_lane": False,
            "parent_control_flow_derived_success_path_only": True,
            "parent_execution_source_attested": False,
            "child_internal_counter_observed": False,
            "independently_verified_actual_work": False,
            "failure_path_accounting_complete": False,
            "official_or_economics_cost_eligible": False,
            "accounting_blocker": (
                "TYPED_FAILURE_WORK_ARTIFACT_NOT_IMPLEMENTED"
            ),
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class V075PublicReplayIPCEvaluationWorkV2:
    raw_bundle_verifier_calls: int
    semantic_result_reconstructions: int
    process_launches: int
    _evaluation_work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self.raw_bundle_verifier_calls != 1
            or self.semantic_result_reconstructions != 1
            or self.process_launches != 0
        ):
            _fail("public replay evaluation work is incomplete")
        object.__setattr__(
            self,
            "_evaluation_work_id",
            _hash("evaluation_work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_evaluation_work.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "raw_bundle_verifier_calls": self.raw_bundle_verifier_calls,
            "semantic_result_reconstructions": (
                self.semantic_result_reconstructions
            ),
            "process_launches": self.process_launches,
            "lane": "STANDALONE_EVALUATION_ONLY",
            "operational_route_cost": False,
            "official_economics_cost": False,
        }

    @property
    def evaluation_work_id(self) -> str:
        return self._evaluation_work_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "evaluation_work_id": self.evaluation_work_id,
        }


@dataclass(frozen=True, slots=True)
class V075PublicReplaySemanticEvaluationV2:
    result_id: str
    profile_id: str
    portable_bundle_id: str
    portable_bundle_sha256: str
    child_result_id: str
    evaluation_work: V075PublicReplayIPCEvaluationWorkV2
    _semantic_evaluation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.result_id, "evaluated public replay result"),
            (self.profile_id, "evaluated public replay profile"),
            (self.portable_bundle_id, "evaluated portable bundle"),
            (self.portable_bundle_sha256, "evaluated portable bundle bytes"),
            (self.child_result_id, "evaluated public replay child result"),
        ):
            _cid(value, label)
        if (
            type(self.evaluation_work)
            is not V075PublicReplayIPCEvaluationWorkV2
        ):
            _fail("public replay semantic evaluation is malformed")
        object.__setattr__(
            self,
            "_semantic_evaluation_id",
            _hash("semantic_evaluation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_semantic_evaluation.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "result_id": self.result_id,
            "profile_id": self.profile_id,
            "portable_bundle_id": self.portable_bundle_id,
            "portable_bundle_sha256": self.portable_bundle_sha256,
            "child_result_id": self.child_result_id,
            "evaluation_work": self.evaluation_work.to_document(),
            "evaluation_work_id": self.evaluation_work.evaluation_work_id,
            "raw_bundle_semantics_replayed": True,
            "process_provenance_verified": False,
            "construction_supervisor_attestation_verified": False,
            "cryptographic_or_os_provenance": False,
            "operational_work_verified": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def semantic_evaluation_id(self) -> str:
        return self._semantic_evaluation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "semantic_evaluation_id": self.semantic_evaluation_id,
        }


_SUPERVISOR_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PublicReplayConstructionSupervisorAttestationV2:
    _issuer: InitVar[object]
    supervisor_nonce: str
    child_pid: int
    child_pgid: int
    child_proc_start_ticks: int
    child_executable_sha256: str
    child_executable_byte_count: int
    runtime_identity_id: str
    source_snapshot_id: str
    sealed_fd_number: int
    sealed_fd_device: int
    sealed_fd_inode: int
    sealed_fd_size: int
    sealed_fd_seals: int
    launch_id: str
    portable_bundle_id: str
    child_result_id: str
    child_exit_code: int
    leader_reaped: bool
    process_group_cleanup_attempted: bool
    process_group_absent_after_cleanup: bool
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.supervisor_nonce, "construction supervisor nonce"),
            (
                self.child_executable_sha256,
                "construction child executable",
            ),
            (self.runtime_identity_id, "construction runtime identity"),
            (self.source_snapshot_id, "construction source snapshot"),
            (self.launch_id, "construction launch frame"),
            (self.portable_bundle_id, "construction bundle frame"),
            (self.child_result_id, "construction child result frame"),
        ):
            _cid(value, label)
        if (
            _issuer is not _SUPERVISOR_ATTESTATION_ISSUER
            or type(self.child_pid) is not int
            or self.child_pid <= 0
            or self.child_pgid != self.child_pid
            or type(self.child_proc_start_ticks) is not int
            or self.child_proc_start_ticks <= 0
            or type(self.child_executable_byte_count) is not int
            or self.child_executable_byte_count <= 0
            or type(self.sealed_fd_number) is not int
            or self.sealed_fd_number < 0
            or type(self.sealed_fd_device) is not int
            or self.sealed_fd_device < 0
            or type(self.sealed_fd_inode) is not int
            or self.sealed_fd_inode <= 0
            or type(self.sealed_fd_size) is not int
            or self.sealed_fd_size <= 0
            or self.sealed_fd_seals & _REQUIRED_SEALS != _REQUIRED_SEALS
            or self.child_exit_code != 0
            or self.leader_reaped is not True
            or self.process_group_cleanup_attempted is not True
            or self.process_group_absent_after_cleanup is not True
        ):
            _fail("construction supervisor attestation is malformed")
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("supervisor_attestation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_public_replay_"
                "construction_supervisor_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "supervisor_nonce": self.supervisor_nonce,
            "child_pid": self.child_pid,
            "child_pgid": self.child_pgid,
            "child_proc_start_ticks": self.child_proc_start_ticks,
            "child_executable_sha256": self.child_executable_sha256,
            "child_executable_byte_count": (
                self.child_executable_byte_count
            ),
            "runtime_identity_id": self.runtime_identity_id,
            "source_snapshot_id": self.source_snapshot_id,
            "sealed_fd": {
                "number": self.sealed_fd_number,
                "device": self.sealed_fd_device,
                "inode": self.sealed_fd_inode,
                "size": self.sealed_fd_size,
                "seals": self.sealed_fd_seals,
            },
            "frame_ids": {
                "launch_id": self.launch_id,
                "portable_bundle_id": self.portable_bundle_id,
                "child_result_id": self.child_result_id,
            },
            "child_exit_code": self.child_exit_code,
            "leader_reaped": self.leader_reaped,
            "process_group_cleanup_attempted": (
                self.process_group_cleanup_attempted
            ),
            "process_group_absent_after_cleanup": (
                self.process_group_absent_after_cleanup
            ),
            "attestation_scope": "CONSTRUCTION_TRUSTED_SUPERVISOR_ONLY",
            "cryptographic_or_os_provenance": False,
            "os_remote_attestation": False,
            "persistent_process_provenance_proof": False,
            "parent_execution_source_attested": False,
            "child_loaded_source_os_attested": False,
            "production_authorizing": False,
            "official_execution_allowed": False,
        }

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "attestation_id": self.attestation_id,
        }


@dataclass(frozen=True, slots=True)
class V075PublicReplayOccurrenceIPCResultV2:
    profile_id: str
    occurrence_id: str
    portable_bundle_id: str
    source_snapshot_id: str
    child_verification: V075PublicReplayChildVerificationResultV2
    journal: V075PublicReplayIPCJournalV2
    operational_success_work: V075PublicReplayIPCOperationalSuccessWorkV2
    supervisor_attestation: (
        V075PublicReplayConstructionSupervisorAttestationV2
    )
    stderr_sha256: str
    stderr_byte_count: int
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.profile_id, "public replay result profile"),
            (self.occurrence_id, "public replay result occurrence"),
            (self.portable_bundle_id, "public replay result bundle"),
            (self.source_snapshot_id, "public replay result source snapshot"),
            (self.stderr_sha256, "public replay stderr digest"),
        ):
            _cid(value, name)
        if (
            type(self.child_verification)
            is not V075PublicReplayChildVerificationResultV2
            or type(self.journal) is not V075PublicReplayIPCJournalV2
            or type(self.operational_success_work)
            is not V075PublicReplayIPCOperationalSuccessWorkV2
            or type(self.supervisor_attestation)
            is not V075PublicReplayConstructionSupervisorAttestationV2
            or self.child_verification.profile_id != self.profile_id
            or self.child_verification.occurrence_id != self.occurrence_id
            or self.child_verification.portable_bundle_id
            != self.portable_bundle_id
            or self.child_verification.source_snapshot_id
            != self.source_snapshot_id
            or self.journal.entries[-1].message_id
            != self.child_verification.child_result_id
            or self.supervisor_attestation.source_snapshot_id
            != self.source_snapshot_id
            or self.supervisor_attestation.portable_bundle_id
            != self.portable_bundle_id
            or self.supervisor_attestation.child_result_id
            != self.child_verification.child_result_id
            or self.supervisor_attestation.launch_id
            != self.journal.entries[0].message_id
            or self.supervisor_attestation.runtime_identity_id
            == ""
            or self.stderr_sha256 != hashlib.sha256(b"").hexdigest()
            or self.stderr_byte_count != 0
        ):
            _fail("public replay IPC result is incomplete or transplanted")
        object.__setattr__(
            self,
            "_result_id",
            _hash("result", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_occurrence_ipc_result.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "profile_id": self.profile_id,
            "occurrence_id": self.occurrence_id,
            "portable_bundle_id": self.portable_bundle_id,
            "source_snapshot_id": self.source_snapshot_id,
            "loaded_source_manifest_id": (
                self.child_verification.loaded_source_manifest.loaded_manifest_id
            ),
            "child_verification": self.child_verification.to_document(),
            "child_verification_id": (
                self.child_verification.child_result_id
            ),
            "journal": self.journal.to_document(),
            "journal_id": self.journal.journal_id,
            "operational_success_work": (
                self.operational_success_work.to_document()
            ),
            "operational_success_work_id": (
                self.operational_success_work.work_id
            ),
            "supervisor_attestation": (
                self.supervisor_attestation.to_document()
            ),
            "supervisor_attestation_id": (
                self.supervisor_attestation.attestation_id
            ),
            "cryptographic_or_os_process_provenance": False,
            "parent_execution_source_attested": False,
            "child_internal_counter_observed": False,
            "independently_verified_actual_work": False,
            "failure_path_accounting_complete": False,
            "official_or_economics_cost_eligible": False,
            "accounting_blocker": (
                "TYPED_FAILURE_WORK_ARTIFACT_NOT_IMPLEMENTED"
            ),
            "stderr_sha256": self.stderr_sha256,
            "stderr_byte_count": self.stderr_byte_count,
            "semantic_registry_replay_complete": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "fresh_heldout_accessed": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _loaded_source_manifest_from_document(
    value: Any,
) -> V075PublicReplayLoadedSourceManifestV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "profile_key",
            "source_snapshot_id",
            "entries",
            "entry_count",
            "all_origins_sealed_memfd",
            "live_source_root_fallback_used",
            "loaded_manifest_id",
        },
        field_name="loaded public replay source manifest",
    )
    raw_entries = item["entries"]
    if type(raw_entries) is not list:
        _fail("loaded public replay source entries are malformed")
    entries: list[V075PublicReplayLoadedSourceEntryV2] = []
    for raw_entry in raw_entries:
        entry = _exact_mapping(
            raw_entry,
            {
                "module_name",
                "relative_path",
                "source_sha256",
                "source_byte_count",
                "normalized_origin",
            },
            field_name="loaded public replay source entry",
        )
        entries.append(
            V075PublicReplayLoadedSourceEntryV2(
                entry["module_name"],
                entry["relative_path"],
                entry["source_sha256"],
                entry["source_byte_count"],
                entry["normalized_origin"],
            )
        )
    reconstructed = V075PublicReplayLoadedSourceManifestV2(
        item["source_snapshot_id"],
        tuple(entries),
    )
    if reconstructed.to_document() != item:
        _fail("loaded public replay source manifest identity changed")
    return reconstructed


def _child_result_from_document(
    value: Any,
) -> V075PublicReplayChildVerificationResultV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "terminal_scope",
            "terminal_class",
            "terminal_code",
            "profile_id",
            "program_registration_id",
            "occurrence_id",
            "portable_bundle_id",
            "portable_bundle_sha256",
            "portable_bundle_byte_count",
            "artifact_count",
            "root_binding_count",
            "source_snapshot_id",
            "loaded_source_manifest",
            "loaded_source_manifest_id",
            "raw_bundle_bytes_verified",
            "topological_dependency_replay_complete",
            "role_specific_raw_replay_complete",
            "semantic_registry_replay_complete",
            "child_observation_accessed",
            "child_signing_performed",
            "child_acquisition_performed",
            "official_execution_allowed",
            "production_authorizing",
            "fresh_heldout_accessed",
            "scientific_endpoint_credit_allowed",
            "plan_certificate",
            "infeasibility_certificate",
            "child_result_id",
        },
        field_name="public replay child verification result",
    )
    loaded = _loaded_source_manifest_from_document(
        item["loaded_source_manifest"]
    )
    reconstructed = V075PublicReplayChildVerificationResultV2(
        _CHILD_RESULT_ISSUER,
        item["profile_id"],
        item["program_registration_id"],
        item["occurrence_id"],
        item["portable_bundle_id"],
        item["portable_bundle_sha256"],
        item["portable_bundle_byte_count"],
        item["artifact_count"],
        item["root_binding_count"],
        item["source_snapshot_id"],
        loaded,
    )
    if reconstructed.to_document() != item:
        _fail("public replay child result identity changed")
    return reconstructed


def _journal_entry_from_document(
    value: Any,
) -> V075PublicReplayIPCJournalEntryV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "profile_key",
            "sequence_number",
            "direction",
            "message_kind",
            "message_id",
            "message_byte_count",
            "message_sha256",
            "previous_entry_id",
            "entry_id",
        },
        field_name="public replay IPC journal entry",
    )
    reconstructed = V075PublicReplayIPCJournalEntryV2(
        item["sequence_number"],
        item["direction"],
        item["message_kind"],
        item["message_id"],
        item["message_byte_count"],
        item["message_sha256"],
        item["previous_entry_id"],
    )
    if reconstructed.to_document() != item:
        _fail("public replay IPC journal entry identity changed")
    return reconstructed


def _journal_from_document(value: Any) -> V075PublicReplayIPCJournalV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "profile_key",
            "entries",
            "entry_count",
            "hash_chain_complete",
            "journal_id",
        },
        field_name="public replay IPC journal",
    )
    raw_entries = item["entries"]
    if type(raw_entries) is not list:
        _fail("public replay IPC journal entries are malformed")
    reconstructed = V075PublicReplayIPCJournalV2(
        tuple(_journal_entry_from_document(entry) for entry in raw_entries)
    )
    if reconstructed.to_document() != item:
        _fail("public replay IPC journal identity changed")
    return reconstructed


def _operational_success_work_from_document(
    value: Any,
) -> V075PublicReplayIPCOperationalSuccessWorkV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "profile_key",
            "process_launches",
            "parent_to_child_frames",
            "child_to_parent_frames",
            "parent_to_child_payload_bytes",
            "child_to_parent_payload_bytes",
            "framing_bytes",
            "raw_bundle_verifier_calls_parent_execution",
            "raw_bundle_verifier_calls_child",
            "staged_bytes",
            "source_snapshot_bytes",
            "source_snapshot_bytes_derived_only",
            "sealed_memfd_count",
            "source_archive_validation_passes_parent_execution",
            "source_archive_entry_checks_parent_execution",
            "seal_verification_checks_parent_execution",
            "seal_verification_checks_child",
            "loaded_source_checks_child",
            "loaded_source_entry_checks_child",
            "process_exit_code",
            "operational_lane",
            "evaluation_lane",
            "parent_control_flow_derived_success_path_only",
            "parent_execution_source_attested",
            "child_internal_counter_observed",
            "independently_verified_actual_work",
            "failure_path_accounting_complete",
            "official_or_economics_cost_eligible",
            "accounting_blocker",
            "work_id",
        },
        field_name="public replay IPC operational success work",
    )
    reconstructed = V075PublicReplayIPCOperationalSuccessWorkV2(
        item["process_launches"],
        item["parent_to_child_frames"],
        item["child_to_parent_frames"],
        item["parent_to_child_payload_bytes"],
        item["child_to_parent_payload_bytes"],
        item["framing_bytes"],
        item["raw_bundle_verifier_calls_parent_execution"],
        item["raw_bundle_verifier_calls_child"],
        item["staged_bytes"],
        item["source_snapshot_bytes"],
        item["sealed_memfd_count"],
        item["source_archive_validation_passes_parent_execution"],
        item["source_archive_entry_checks_parent_execution"],
        item["seal_verification_checks_parent_execution"],
        item["seal_verification_checks_child"],
        item["loaded_source_checks_child"],
        item["loaded_source_entry_checks_child"],
        item["process_exit_code"],
    )
    if reconstructed.to_document() != item:
        _fail("public replay operational work identity changed")
    return reconstructed


def _supervisor_attestation_from_document(
    value: Any,
) -> V075PublicReplayConstructionSupervisorAttestationV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "profile_key",
            "supervisor_nonce",
            "child_pid",
            "child_pgid",
            "child_proc_start_ticks",
            "child_executable_sha256",
            "child_executable_byte_count",
            "runtime_identity_id",
            "source_snapshot_id",
            "sealed_fd",
            "frame_ids",
            "child_exit_code",
            "leader_reaped",
            "process_group_cleanup_attempted",
            "process_group_absent_after_cleanup",
            "attestation_scope",
            "cryptographic_or_os_provenance",
            "os_remote_attestation",
            "persistent_process_provenance_proof",
            "parent_execution_source_attested",
            "child_loaded_source_os_attested",
            "production_authorizing",
            "official_execution_allowed",
            "attestation_id",
        },
        field_name="construction supervisor attestation",
    )
    sealed_fd = _exact_mapping(
        item["sealed_fd"],
        {"number", "device", "inode", "size", "seals"},
        field_name="construction supervisor sealed fd",
    )
    frame_ids = _exact_mapping(
        item["frame_ids"],
        {"launch_id", "portable_bundle_id", "child_result_id"},
        field_name="construction supervisor frame IDs",
    )
    reconstructed = V075PublicReplayConstructionSupervisorAttestationV2(
        _SUPERVISOR_ATTESTATION_ISSUER,
        item["supervisor_nonce"],
        item["child_pid"],
        item["child_pgid"],
        item["child_proc_start_ticks"],
        item["child_executable_sha256"],
        item["child_executable_byte_count"],
        item["runtime_identity_id"],
        item["source_snapshot_id"],
        sealed_fd["number"],
        sealed_fd["device"],
        sealed_fd["inode"],
        sealed_fd["size"],
        sealed_fd["seals"],
        frame_ids["launch_id"],
        frame_ids["portable_bundle_id"],
        frame_ids["child_result_id"],
        item["child_exit_code"],
        item["leader_reaped"],
        item["process_group_cleanup_attempted"],
        item["process_group_absent_after_cleanup"],
    )
    if reconstructed.to_document() != item:
        _fail("construction supervisor attestation identity changed")
    return reconstructed


def _result_from_document(
    value: Any,
) -> V075PublicReplayOccurrenceIPCResultV2:
    item = _exact_mapping(
        value,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "terminal_scope",
            "terminal_class",
            "terminal_code",
            "profile_id",
            "occurrence_id",
            "portable_bundle_id",
            "source_snapshot_id",
            "loaded_source_manifest_id",
            "child_verification",
            "child_verification_id",
            "journal",
            "journal_id",
            "operational_success_work",
            "operational_success_work_id",
            "supervisor_attestation",
            "supervisor_attestation_id",
            "cryptographic_or_os_process_provenance",
            "parent_execution_source_attested",
            "child_internal_counter_observed",
            "independently_verified_actual_work",
            "failure_path_accounting_complete",
            "official_or_economics_cost_eligible",
            "accounting_blocker",
            "stderr_sha256",
            "stderr_byte_count",
            "semantic_registry_replay_complete",
            "official_execution_allowed",
            "production_authorizing",
            "fresh_heldout_accessed",
            "scientific_endpoint_credit_allowed",
            "plan_certificate",
            "infeasibility_certificate",
            "result_id",
        },
        field_name="public replay IPC result",
    )
    child = _child_result_from_document(item["child_verification"])
    journal = _journal_from_document(item["journal"])
    work = _operational_success_work_from_document(
        item["operational_success_work"]
    )
    attestation = _supervisor_attestation_from_document(
        item["supervisor_attestation"]
    )
    reconstructed = V075PublicReplayOccurrenceIPCResultV2(
        item["profile_id"],
        item["occurrence_id"],
        item["portable_bundle_id"],
        item["source_snapshot_id"],
        child,
        journal,
        work,
        attestation,
        item["stderr_sha256"],
        item["stderr_byte_count"],
    )
    if reconstructed.to_document() != item:
        _fail("public replay IPC result identity changed")
    return reconstructed


def _write_frame_child(stream: Any, raw: bytes, *, byte_cap: int) -> None:
    if (
        type(raw) is not bytes
        or not raw
        or type(byte_cap) is not int
        or byte_cap <= 0
        or len(raw) > byte_cap
    ):
        _fail("public replay frame is empty, mistyped, or over cap")
    header = f"{len(raw):0{_FRAME_WIDTH}x}".encode("ascii")
    try:
        stream.write(header)
        view = memoryview(raw)
        cursor = 0
        while cursor < len(view):
            written = stream.write(view[cursor : cursor + 1024 * 1024])
            if type(written) is not int or written <= 0:
                _fail("public replay IPC frame write made no progress")
            cursor += written
        stream.flush()
    except (BrokenPipeError, OSError) as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "public replay IPC frame write failed"
        ) from error


def _parse_canonical_frame_header(
    header: bytes,
    *,
    byte_cap: int,
    field_name: str,
) -> int:
    if (
        type(header) is not bytes
        or len(header) != _FRAME_WIDTH
        or type(byte_cap) is not int
        or byte_cap <= 0
        or type(field_name) is not str
        or not field_name
    ):
        _fail(f"{field_name} frame header is truncated or mistyped")
    try:
        text = header.decode("ascii", errors="strict")
        if any(character not in "0123456789abcdef" for character in text):
            raise ValueError("non-lowercase hexadecimal digit")
        length = int(text, 16)
    except (UnicodeError, ValueError) as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            f"{field_name} frame header is noncanonical"
        ) from error
    if (
        header != f"{length:0{_FRAME_WIDTH}x}".encode("ascii")
        or not 0 < length <= byte_cap
    ):
        _fail(f"{field_name} frame header is noncanonical or outside its cap")
    return length


def _read_frame_child(stream: Any, *, byte_cap: int) -> bytes:
    header = stream.read(_FRAME_WIDTH)
    length = _parse_canonical_frame_header(
        header,
        byte_cap=byte_cap,
        field_name="public replay child",
    )
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = stream.read(min(1024 * 1024, remaining))
        if type(chunk) is not bytes or not chunk:
            _fail("public replay child received a truncated frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except (PermissionError, OSError):
        try:
            process.kill()
        except (ProcessLookupError, OSError):
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except (ProcessLookupError, OSError):
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def _capture_supervised_process_start(
    process: subprocess.Popen[bytes],
    runtime: V075PublicReplayRuntimeIdentityV2,
) -> dict[str, int | str]:
    pid = process.pid
    try:
        pgid = os.getpgid(pid)
        stat_text = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        tail = stat_text[stat_text.rfind(")") + 2 :].split()
        start_ticks = int(tail[19])
        executable = Path(os.readlink(f"/proc/{pid}/exe")).resolve(strict=True)
        executable_sha256, executable_size = _runtime_file_identity(executable)
    except (OSError, ValueError, IndexError) as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "construction supervisor could not capture child start identity"
        ) from error
    if (
        pgid != pid
        or executable_sha256 != runtime.executable_sha256
        or executable_size != runtime.executable_byte_count
    ):
        _fail("construction child process identity differs from registration")
    return {
        "pid": pid,
        "pgid": pgid,
        "start_ticks": start_ticks,
        "executable_sha256": executable_sha256,
        "executable_size": executable_size,
    }


def _process_group_is_absent(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def _construction_supervisor_attestation(
    *,
    nonce: str,
    process_start: Mapping[str, int | str],
    profile: V075PublicReplayOccurrenceIPCProfileV2,
    sealed_fd: int,
    launch_id: str,
    child_result_id: str,
    exit_code: int,
    process: subprocess.Popen[bytes],
) -> V075PublicReplayConstructionSupervisorAttestationV2:
    try:
        stat = os.fstat(sealed_fd)
        seals = fcntl.fcntl(sealed_fd, _F_GET_SEALS)
    except OSError as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "construction supervisor lost the sealed source fd"
        ) from error
    pid = int(process_start["pid"])
    pgid = int(process_start["pgid"])
    if (
        process.poll() is None
        or not _process_group_is_absent(pgid)
        or exit_code != 0
    ):
        _fail("construction child was not fully reaped after cleanup")
    return V075PublicReplayConstructionSupervisorAttestationV2(
        _SUPERVISOR_ATTESTATION_ISSUER,
        nonce,
        pid,
        pgid,
        int(process_start["start_ticks"]),
        str(process_start["executable_sha256"]),
        int(process_start["executable_size"]),
        profile.program_registration.runtime_identity.runtime_identity_id,
        profile.program_registration.source_snapshot.source_snapshot_id,
        sealed_fd,
        stat.st_dev,
        stat.st_ino,
        stat.st_size,
        seals,
        launch_id,
        profile.portable_bundle_id,
        child_result_id,
        exit_code,
        True,
        True,
        True,
    )


def _require_sealed_memfd_platform() -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if not hasattr(libc, "memfd_create") or not Path("/proc/self/fd").is_dir():
        _fail("sealed memfd source execution is unavailable on this platform")


def _memfd_create(name: str) -> int:
    _require_sealed_memfd_platform()
    if hasattr(os, "memfd_create"):
        return os.memfd_create(
            name,
            flags=_MFD_ALLOW_SEALING | _MFD_CLOEXEC,
        )
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.memfd_create
    function.argtypes = (ctypes.c_char_p, ctypes.c_uint)
    function.restype = ctypes.c_int
    fd = function(
        name.encode("ascii", errors="strict"),
        _MFD_ALLOW_SEALING | _MFD_CLOEXEC,
    )
    if fd < 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))
    return fd


def _verify_sealed_source_fd(
    fd: int,
    snapshot: V075PublicReplaySourceSnapshotV2,
) -> None:
    _require_sealed_memfd_platform()
    if type(fd) is not int or fd < 0:
        _fail("public replay source snapshot fd is invalid")
    try:
        seals = fcntl.fcntl(fd, _F_GET_SEALS)
        stat = os.fstat(fd)
    except OSError as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "public replay source snapshot fd cannot be inspected"
        ) from error
    if seals & _REQUIRED_SEALS != _REQUIRED_SEALS:
        _fail("public replay source snapshot fd is writable or unsealed")
    if stat.st_size != snapshot.archive_byte_count:
        _fail("sealed public replay source archive size changed")
    digest = hashlib.sha256()
    offset = 0
    while offset < stat.st_size:
        try:
            chunk = os.pread(
                fd,
                min(1024 * 1024, stat.st_size - offset),
                offset,
            )
        except OSError as error:
            raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
                "sealed public replay source archive cannot be read"
            ) from error
        if not chunk:
            _fail("sealed public replay source archive is truncated")
        digest.update(chunk)
        offset += len(chunk)
    if digest.hexdigest() != snapshot.archive_sha256:
        _fail("sealed public replay source archive digest changed")


def _stage_sealed_source_snapshot(
    snapshot: V075PublicReplaySourceSnapshotV2,
    *,
    recorder: _ExecutionWorkRecorder | None = None,
) -> int:
    _require_sealed_memfd_platform()
    if not snapshot.archive_bytes:
        _fail("execution requires retained registered source archive bytes")
    _verify_source_archive_bytes(snapshot, snapshot.archive_bytes)
    if recorder is not None:
        recorder.record_source_archive_validation(snapshot)
    try:
        fd = _memfd_create(
            f"acfqp-v075-{snapshot.source_snapshot_id[:16]}"
        )
    except OSError as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "public replay source memfd creation failed"
        ) from error
    try:
        view = memoryview(snapshot.archive_bytes)
        offset = 0
        while offset < len(view):
            written = os.write(fd, view[offset : offset + 1024 * 1024])
            if written <= 0:
                _fail("public replay source memfd staging made no progress")
            offset += written
        fcntl.fcntl(fd, _F_ADD_SEALS, _REQUIRED_SEALS)
        _verify_sealed_source_fd(fd, snapshot)
        if recorder is not None:
            recorder.record_parent_seal_verification()
            recorder.record_staged_snapshot(snapshot)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _supervised_exchange(
    process: subprocess.Popen[bytes],
    *,
    parent_frames: tuple[tuple[bytes, int], ...],
    deadline: float,
) -> tuple[bytes, bytes, int]:
    if (
        process.stdin is None
        or process.stdout is None
        or process.stderr is None
        or type(parent_frames) is not tuple
        or len(parent_frames) != 2
    ):
        _fail("public replay child lacks exact isolated protocol pipes")
    segments: list[memoryview] = []
    for raw, cap in parent_frames:
        if (
            type(raw) is not bytes
            or not raw
            or type(cap) is not int
            or cap <= 0
            or len(raw) > cap
        ):
            _fail("supervised parent frame is empty, mistyped, or over cap")
        segments.extend(
            (
                memoryview(
                    f"{len(raw):0{_FRAME_WIDTH}x}".encode("ascii")
                ),
                memoryview(raw),
            )
        )
    stdin_fd = process.stdin.fileno()
    stdout_fd = process.stdout.fileno()
    stderr_fd = process.stderr.fileno()
    try:
        os.set_blocking(stdin_fd, False)
        os.set_blocking(stdout_fd, False)
        os.set_blocking(stderr_fd, False)
    except OSError as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "public replay protocol pipes could not enter supervised mode"
        ) from error
    readable_fds = {stdout_fd, stderr_fd}
    stdin_open = True
    segment_index = 0
    segment_offset = 0
    stdout = bytearray()
    stderr = bytearray()
    expected_stdout_bytes: int | None = None
    while stdin_open or readable_fds:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _terminate_process(process)
            _fail("public replay child exceeded its frozen timeout")
        write_fds = [stdin_fd] if stdin_open else []
        ready_read, ready_write, _ = select.select(
            list(readable_fds),
            write_fds,
            [],
            remaining,
        )
        if not ready_read and not ready_write:
            _terminate_process(process)
            _fail("public replay child exceeded its frozen timeout")
        if stdin_open and stdin_fd in ready_write:
            segment = segments[segment_index]
            try:
                written = os.write(
                    stdin_fd,
                    segment[
                        segment_offset : segment_offset + 64 * 1024
                    ],
                )
            except BlockingIOError:
                written = 0
            except (BrokenPipeError, OSError) as error:
                _terminate_process(process)
                raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
                    "public replay child stopped draining its input"
                ) from error
            if written < 0:  # pragma: no cover
                _terminate_process(process)
                _fail("supervised public replay write regressed")
            segment_offset += written
            if segment_offset == len(segment):
                segment_index += 1
                segment_offset = 0
                if segment_index == len(segments):
                    process.stdin.close()
                    process.stdin = None
                    stdin_open = False
        for fd in ready_read:
            chunk = os.read(fd, 64 * 1024)
            if not chunk:
                readable_fds.remove(fd)
                continue
            if fd == stderr_fd:
                stderr.extend(chunk)
                if len(stderr) > MAX_CHILD_STDERR_BYTES:
                    _terminate_process(process)
                    _fail("public replay child exceeded its stderr cap")
                _terminate_process(process)
                _fail("public replay child emitted forbidden stderr bytes")
                continue
            stdout.extend(chunk)
            if (
                expected_stdout_bytes is None
                and len(stdout) >= _FRAME_WIDTH
            ):
                try:
                    length = _parse_canonical_frame_header(
                        bytes(stdout[:_FRAME_WIDTH]),
                        byte_cap=MAX_RESULT_FRAME_BYTES,
                        field_name="public replay child result",
                    )
                except V075PublicReplayOccurrenceIPCV2InvariantViolation:
                    _terminate_process(process)
                    raise
                expected_stdout_bytes = _FRAME_WIDTH + length
            if (
                expected_stdout_bytes is not None
                and len(stdout) > expected_stdout_bytes
            ):
                _terminate_process(process)
                _fail("public replay child emitted extra stdout frames or bytes")
            if len(stdout) > _FRAME_WIDTH + MAX_RESULT_FRAME_BYTES:
                _terminate_process(process)
                _fail("public replay child exceeded its stdout cap")
        if (
            process.poll() is not None
            and stdin_open
            and stdout_fd not in readable_fds
            and stderr_fd not in readable_fds
        ):
            _terminate_process(process)
            _fail("public replay child exited before draining exact input")
    remaining = max(0.001, deadline - time.monotonic())
    try:
        exit_code = process.wait(timeout=remaining)
    except subprocess.TimeoutExpired as error:
        _terminate_process(process)
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "public replay child exceeded its frozen timeout"
        ) from error
    if expected_stdout_bytes is None or len(stdout) != expected_stdout_bytes:
        _fail("public replay child emitted a missing or truncated result frame")
    return bytes(stdout[_FRAME_WIDTH:]), bytes(stderr), exit_code


@dataclass(slots=True)
class _ExecutionWorkRecorder:
    process_launches: int = 0
    parent_to_child_frames: int = 0
    child_to_parent_frames: int = 0
    parent_to_child_payload_bytes: int = 0
    child_to_parent_payload_bytes: int = 0
    framing_bytes: int = 0
    raw_bundle_verifier_calls_parent_execution: int = 0
    raw_bundle_verifier_calls_child: int = 0
    staged_bytes: int = 0
    sealed_memfd_count: int = 0
    source_archive_validation_passes_parent_execution: int = 0
    source_archive_entry_checks_parent_execution: int = 0
    seal_verification_checks_parent_execution: int = 0
    seal_verification_checks_child: int = 0
    loaded_source_checks_child: int = 0
    loaded_source_entry_checks_child: int = 0
    process_exit_code: int | None = None

    def record_source_archive_validation(
        self,
        snapshot: V075PublicReplaySourceSnapshotV2,
    ) -> None:
        self.source_archive_validation_passes_parent_execution += 1
        self.source_archive_entry_checks_parent_execution += (
            snapshot.to_document()["archive_entry_count"]
        )

    def record_parent_seal_verification(self) -> None:
        self.seal_verification_checks_parent_execution += 1

    def record_staged_snapshot(
        self,
        snapshot: V075PublicReplaySourceSnapshotV2,
    ) -> None:
        self.staged_bytes += snapshot.archive_byte_count
        self.sealed_memfd_count += 1

    def record_process_launch(self) -> None:
        self.process_launches += 1

    def record_successful_exchange(
        self,
        *,
        launch_raw: bytes,
        bundle_raw: bytes,
        child_raw: bytes,
        snapshot: V075PublicReplaySourceSnapshotV2,
        exit_code: int,
    ) -> None:
        self.parent_to_child_frames += 2
        self.child_to_parent_frames += 1
        self.parent_to_child_payload_bytes += len(launch_raw) + len(bundle_raw)
        self.child_to_parent_payload_bytes += len(child_raw)
        self.framing_bytes += 3 * _FRAME_WIDTH
        # A successful registered child necessarily passed the bootstrap seal
        # check, the child seal check, both exact loaded-set/origin checks, and
        # one raw semantic verifier invocation.
        self.seal_verification_checks_child += 2
        self.loaded_source_checks_child += 2
        self.loaded_source_entry_checks_child += (
            2 * len(snapshot.executable_entries)
        )
        self.raw_bundle_verifier_calls_child += 1
        self.process_exit_code = exit_code

    def freeze_success(
        self,
        snapshot: V075PublicReplaySourceSnapshotV2,
    ) -> V075PublicReplayIPCOperationalSuccessWorkV2:
        return V075PublicReplayIPCOperationalSuccessWorkV2(
            self.process_launches,
            self.parent_to_child_frames,
            self.child_to_parent_frames,
            self.parent_to_child_payload_bytes,
            self.child_to_parent_payload_bytes,
            self.framing_bytes,
            self.raw_bundle_verifier_calls_parent_execution,
            self.raw_bundle_verifier_calls_child,
            self.staged_bytes,
            self.staged_bytes,
            self.sealed_memfd_count,
            self.source_archive_validation_passes_parent_execution,
            self.source_archive_entry_checks_parent_execution,
            self.seal_verification_checks_parent_execution,
            self.seal_verification_checks_child,
            self.loaded_source_checks_child,
            self.loaded_source_entry_checks_child,
            -1 if self.process_exit_code is None else self.process_exit_code,
        )


def _child_argv(
    registration: V075PublicReplayChildProgramRegistrationV2,
    sealed_fd: int,
) -> list[str]:
    snapshot = registration.source_snapshot
    if (
        snapshot.bootstrap_sha256 != _BOOTSTRAP_SHA256
        or hashlib.sha256(_BOOTSTRAP_SOURCE.encode("utf-8")).hexdigest()
        != snapshot.bootstrap_sha256
        or type(sealed_fd) is not int
        or sealed_fd < 0
    ):
        _fail("public replay sealed bootstrap registration changed")
    return [
        sys.executable,
        "-I",
        "-S",
        "-c",
        _BOOTSTRAP_SOURCE,
        str(sealed_fd),
        snapshot.archive_sha256,
        str(snapshot.archive_byte_count),
        snapshot.source_snapshot_id,
        snapshot.bootstrap_sha256,
        registration.runtime_identity.runtime_identity_id,
    ]


def _require_exact_profile(
    claimed: V075PublicReplayOccurrenceIPCProfileV2,
    *,
    require_archive_bytes: bool,
    recorder: _ExecutionWorkRecorder | None = None,
) -> V075PublicReplayOccurrenceIPCProfileV2:
    if type(claimed) is not V075PublicReplayOccurrenceIPCProfileV2:
        _fail("public replay IPC profile is not the registered typed object")
    archive_bytes = claimed.program_registration.source_snapshot.archive_bytes
    if require_archive_bytes and not archive_bytes:
        _fail("execution profile lost its registered source archive bytes")
    replayed = _profile_from_document(
        claimed.to_document(),
        archive_bytes=archive_bytes if require_archive_bytes else b"",
    )
    if (
        replayed != claimed
        or replayed.profile_id != claimed.profile_id
        or _canonical_bytes(replayed.to_document())
        != _canonical_bytes(claimed.to_document())
    ):
        _fail("public replay IPC profile differs from exact reconstruction")
    if require_archive_bytes and recorder is not None:
        recorder.record_source_archive_validation(
            replayed.program_registration.source_snapshot
        )
    return replayed


def _expected_journal(
    *,
    profile: V075PublicReplayOccurrenceIPCProfileV2,
    portable_bundle_bytes: bytes,
    child: V075PublicReplayChildVerificationResultV2,
) -> V075PublicReplayIPCJournalV2:
    launch = _launch_document(profile)
    launch_raw = _canonical_bytes(launch)
    child_raw = child.canonical_bytes
    entries: list[V075PublicReplayIPCJournalEntryV2] = []
    _journal_entry(
        entries,
        direction="PARENT_TO_CHILD",
        message_kind="PROGRAM_IDENTITY_AND_LAUNCH",
        message_id=launch["launch_id"],
        raw=launch_raw,
    )
    _journal_entry(
        entries,
        direction="PARENT_TO_CHILD",
        message_kind="PORTABLE_EVIDENCE_BUNDLE",
        message_id=profile.portable_bundle_id,
        raw=portable_bundle_bytes,
    )
    _journal_entry(
        entries,
        direction="CHILD_TO_PARENT",
        message_kind="TYPED_VERIFICATION_RESULT",
        message_id=child.child_result_id,
        raw=child_raw,
    )
    return V075PublicReplayIPCJournalV2(tuple(entries))


def execute_v075_public_replay_occurrence_ipc_v2(
    *,
    profile: V075PublicReplayOccurrenceIPCProfileV2,
    portable_bundle_bytes: bytes,
) -> V075PublicReplayOccurrenceIPCResultV2:
    """Replay one already-frozen public bundle in one isolated child."""

    recorder = _ExecutionWorkRecorder()
    profile = _require_exact_profile(
        profile,
        require_archive_bytes=True,
        recorder=recorder,
    )
    expected = _expected_child_result(
        profile,
        portable_bundle_bytes,
    )
    launch = _launch_document(profile)
    launch_raw = _canonical_bytes(launch)
    process: subprocess.Popen[bytes] | None = None
    child_raw = b""
    stderr = b""
    exit_code: int | None = None
    sealed_fd: int | None = None
    process_start: dict[str, int | str] | None = None
    supervisor_attestation: (
        V075PublicReplayConstructionSupervisorAttestationV2 | None
    ) = None
    supervisor_nonce = os.urandom(32).hex()
    snapshot = profile.program_registration.source_snapshot
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v075-public-replay-"
    ) as sandbox:
        environment = {
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "TZ": "UTC",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        try:
            sealed_fd = _stage_sealed_source_snapshot(
                snapshot,
                recorder=recorder,
            )
            process = subprocess.Popen(
                _child_argv(profile.program_registration, sealed_fd),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=sandbox,
                env=environment,
                close_fds=True,
                pass_fds=(sealed_fd,),
                start_new_session=True,
            )
            recorder.record_process_launch()
            process_start = _capture_supervised_process_start(
                process,
                profile.program_registration.runtime_identity,
            )
            if process.stdin is None:
                _fail("public replay child lacks an isolated input pipe")
            deadline = time.monotonic() + profile.process_timeout_seconds
            child_raw, stderr, exit_code = _supervised_exchange(
                process,
                parent_frames=(
                    (launch_raw, MAX_LAUNCH_FRAME_BYTES),
                    (portable_bundle_bytes, MAX_BUNDLE_FRAME_BYTES),
                ),
                deadline=deadline,
            )
            if exit_code != 0:
                _fail("public replay child process did not exit successfully")
            if stderr:
                _fail("public replay child emitted forbidden stderr bytes")
            child_verification = _validate_child_result(child_raw, expected)
            recorder.record_successful_exchange(
                launch_raw=launch_raw,
                bundle_raw=portable_bundle_bytes,
                child_raw=child_raw,
                snapshot=snapshot,
                exit_code=exit_code,
            )
            _terminate_process(process)
            if process_start is None:
                _fail("construction supervisor lost child start identity")
            supervisor_attestation = _construction_supervisor_attestation(
                nonce=supervisor_nonce,
                process_start=process_start,
                profile=profile,
                sealed_fd=sealed_fd,
                launch_id=launch["launch_id"],
                child_result_id=child_verification.child_result_id,
                exit_code=exit_code,
                process=process,
            )
        except BaseException:
            if process is not None:
                _terminate_process(process)
                try:
                    process.wait(timeout=5)
                except subprocess.SubprocessError:
                    pass
            raise
        finally:
            if process is not None:
                _terminate_process(process)
            if sealed_fd is not None:
                try:
                    os.close(sealed_fd)
                except OSError:
                    pass
                sealed_fd = None

    if supervisor_attestation is None:
        _fail("construction supervisor attestation was not emitted")
    child_verification = _validate_child_result(child_raw, expected)
    journal = _expected_journal(
        profile=profile,
        portable_bundle_bytes=portable_bundle_bytes,
        child=child_verification,
    )
    return V075PublicReplayOccurrenceIPCResultV2(
        profile.profile_id,
        profile.occurrence_id,
        profile.portable_bundle_id,
        snapshot.source_snapshot_id,
        child_verification,
        journal,
        recorder.freeze_success(snapshot),
        supervisor_attestation,
        hashlib.sha256(b"").hexdigest(),
        0,
    )


def verify_v075_public_replay_occurrence_ipc_result_v2(
    *,
    claimed: V075PublicReplayOccurrenceIPCResultV2,
    profile: V075PublicReplayOccurrenceIPCProfileV2,
    portable_bundle_bytes: bytes,
) -> V075PublicReplaySemanticEvaluationV2:
    """Replay bundle semantics in the standalone evaluation lane.

    This verifier does not prove that the claimed subprocess or work history
    occurred.  It only replays the public bundle semantics and checks the
    construction result's canonical content.
    """

    if type(claimed) is not V075PublicReplayOccurrenceIPCResultV2:
        _fail("public replay result verification received stale typed inputs")
    claimed_document = claimed.to_document()
    try:
        claimed = _result_from_document(claimed_document)
    except V075PublicReplayOccurrenceIPCV2InvariantViolation as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "public replay semantic result or internal binding changed"
        ) from error
    if claimed.to_document() != claimed_document:
        _fail("public replay semantic result reconstruction changed")
    profile = _require_exact_profile(
        profile,
        require_archive_bytes=False,
    )
    verified_bundle = _verify_bundle(portable_bundle_bytes)
    expected_child = _expected_child_result(
        profile,
        portable_bundle_bytes,
        verified_bundle=verified_bundle,
    )
    expected_journal = _expected_journal(
        profile=profile,
        portable_bundle_bytes=portable_bundle_bytes,
        child=expected_child,
    )
    snapshot = profile.program_registration.source_snapshot
    runtime = profile.program_registration.runtime_identity
    work = claimed.operational_success_work
    attestation = claimed.supervisor_attestation
    if (
        claimed.profile_id != profile.profile_id
        or claimed.occurrence_id != profile.occurrence_id
        or claimed.portable_bundle_id != verified_bundle.bundle_id
        or claimed.source_snapshot_id != snapshot.source_snapshot_id
        or claimed.child_verification != expected_child
        or claimed.child_verification.to_document()
        != expected_child.to_document()
        or claimed.journal != expected_journal
        or claimed.journal.to_document() != expected_journal.to_document()
        or attestation.runtime_identity_id != runtime.runtime_identity_id
        or attestation.child_executable_sha256
        != runtime.executable_sha256
        or attestation.child_executable_byte_count
        != runtime.executable_byte_count
        or attestation.sealed_fd_size != snapshot.archive_byte_count
        or attestation.sealed_fd_seals != _REQUIRED_SEALS
        or work.staged_bytes != snapshot.archive_byte_count
        or work.source_archive_entry_checks_parent_execution
        != 2 * snapshot.to_document()["archive_entry_count"]
        or work.loaded_source_entry_checks_child
        != 2 * len(snapshot.executable_entries)
        or claimed.result_id != _hash("result", claimed._payload())
        or claimed.canonical_bytes
        != _canonical_bytes(claimed.to_document())
    ):
        _fail("public replay semantic result or internal binding changed")
    return V075PublicReplaySemanticEvaluationV2(
        claimed.result_id,
        profile.profile_id,
        verified_bundle.bundle_id,
        hashlib.sha256(portable_bundle_bytes).hexdigest(),
        expected_child.child_result_id,
        V075PublicReplayIPCEvaluationWorkV2(1, 1, 0),
    )


def open_v075_production_public_replay_occurrence_ipc_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PublicReplayProductionV2NotReady(
        "construction-only public replay does not authorize production, "
        "held-out use, scientific endpoint credit, or certificates"
    )


def _actual_loaded_source_manifest(
    *,
    snapshot: V075PublicReplaySourceSnapshotV2,
    archive_path: str,
) -> V075PublicReplayLoadedSourceManifestV2:
    expected_names = {
        item.module_name for item in snapshot.executable_entries
    }
    for module_name in sorted(expected_names):
        importlib.import_module(module_name)
    dependency_roots = {
        item.root_module for item in snapshot.dependency_distributions
    }
    loaded_executable = {
        name
        for name in sys.modules
        if (
            name == "acfqp"
            or name.startswith("acfqp.")
            or name in dependency_roots
            or any(
                name.startswith(root + ".") for root in dependency_roots
            )
        )
    }
    if loaded_executable != expected_names:
        _fail("sealed child loaded an unregistered executable module set")
    for entry in snapshot.executable_entries:
        module = sys.modules[entry.module_name]
        origin = getattr(getattr(module, "__spec__", None), "origin", None)
        if origin != f"{archive_path}/{entry.relative_path}":
            _fail("sealed child local module origin escaped the memfd archive")
    return _expected_loaded_source_manifest(snapshot)


def _require_exact_sealed_child_runtime(
    *,
    archive_path: str,
    expected_runtime_identity_id: str,
) -> V075PublicReplayRuntimeIdentityV2:
    flags = sys.flags
    if (
        flags.isolated != 1
        or flags.no_site != 1
        or flags.ignore_environment != 1
        or (
            hasattr(flags, "safe_path")
            and getattr(flags, "safe_path") is not True
        )
    ):
        _fail("sealed child interpreter flags differ from registration")
    if (
        not sys.path
        or sys.path[0] != archive_path
        or any(
            "site-packages" in value
            or "dist-packages" in value
            or value == str(_source_root())
            for value in sys.path[1:]
        )
    ):
        _fail("sealed child import path permits an unregistered source root")
    runtime = _capture_runtime_identity()
    if runtime.runtime_identity_id != expected_runtime_identity_id:
        _fail("sealed child runtime identity differs from registration")
    return runtime


def _verify_bundle_with_loaded_source_recheck(
    *,
    raw: bytes,
    snapshot: V075PublicReplaySourceSnapshotV2,
    archive_path: str,
    before: V075PublicReplayLoadedSourceManifestV2,
) -> tuple[Any, V075PublicReplayLoadedSourceManifestV2]:
    bundle = _verify_bundle(raw)
    after = _actual_loaded_source_manifest(
        snapshot=snapshot,
        archive_path=archive_path,
    )
    if after != before:
        _fail("sealed child loaded source set changed during raw verification")
    return bundle, after


def _sealed_child_main(
    *,
    sealed_fd: int,
    archive_path: str,
    expected_snapshot_id: str,
    expected_archive_sha256: str,
    expected_archive_size: int,
    expected_bootstrap_sha256: str,
    expected_runtime_identity_id: str,
) -> int:
    global _SEALED_CHILD_ARCHIVE_PATH
    try:
        if _SEALED_CHILD_ARCHIVE_PATH is not None:
            _fail("sealed public replay child was entered more than once")
        _SEALED_CHILD_ARCHIVE_PATH = archive_path
        child_runtime = _require_exact_sealed_child_runtime(
            archive_path=archive_path,
            expected_runtime_identity_id=expected_runtime_identity_id,
        )
        launch_raw = _read_frame_child(
            sys.stdin.buffer,
            byte_cap=MAX_LAUNCH_FRAME_BYTES,
        )
        _launch, profile = _load_launch(launch_raw)
        snapshot = profile.program_registration.source_snapshot
        if (
            snapshot.source_snapshot_id != expected_snapshot_id
            or snapshot.archive_sha256 != expected_archive_sha256
            or snapshot.archive_byte_count != expected_archive_size
            or snapshot.bootstrap_sha256 != expected_bootstrap_sha256
            or expected_bootstrap_sha256 != _BOOTSTRAP_SHA256
            or profile.program_registration.runtime_identity.to_document()
            != child_runtime.to_document()
            or profile.program_registration.runtime_identity.runtime_identity_id
            != expected_runtime_identity_id
            or archive_path != f"/proc/self/fd/{sealed_fd}"
        ):
            _fail("sealed child source snapshot differs from launch identity")
        _verify_sealed_source_fd(sealed_fd, snapshot)
        loaded_manifest = _actual_loaded_source_manifest(
            snapshot=snapshot,
            archive_path=archive_path,
        )
        bundle_raw = _read_frame_child(
            sys.stdin.buffer,
            byte_cap=MAX_BUNDLE_FRAME_BYTES,
        )
        if sys.stdin.buffer.read(1) != b"":
            _fail("public replay child received an extra input frame or byte")
        bundle, loaded_manifest = _verify_bundle_with_loaded_source_recheck(
            raw=bundle_raw,
            snapshot=snapshot,
            archive_path=archive_path,
            before=loaded_manifest,
        )
        result = _expected_child_result(
            profile,
            bundle_raw,
            verified_bundle=bundle,
            loaded_source_manifest=loaded_manifest,
        )
        _write_frame_child(
            sys.stdout.buffer,
            result.canonical_bytes,
            byte_cap=MAX_RESULT_FRAME_BYTES,
        )
        return 0
    except BaseException as error:
        # Only the exception class crosses this failure path.
        sys.stderr.write(type(error).__name__ + "\n")
        return 74


if __name__ == "__main__":
    raise SystemExit(64)


__all__ = [
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SEMANTIC_REGISTRY_REPLAY_COMPLETE",
    "V075PublicReplayChildProgramRegistrationV2",
    "V075PublicReplayChildVerificationResultV2",
    "V075PublicReplayConstructionSupervisorAttestationV2",
    "V075PublicReplayDependencyDistributionV2",
    "V075PublicReplayDependencySourceEntryV2",
    "V075PublicReplayIPCEvaluationWorkV2",
    "V075PublicReplayIPCJournalEntryV2",
    "V075PublicReplayIPCJournalV2",
    "V075PublicReplayIPCOperationalSuccessWorkV2",
    "V075PublicReplayIPCProfileFreezeWorkV2",
    "V075PublicReplayOccurrenceIPCV2InvariantViolation",
    "V075PublicReplayOccurrenceIPCProfileV2",
    "V075PublicReplayOccurrenceIPCResultV2",
    "V075PublicReplayProductionV2NotReady",
    "V075PublicReplayLoadedSourceEntryV2",
    "V075PublicReplayLoadedSourceManifestV2",
    "V075PublicReplaySourceManifestEntryV2",
    "V075PublicReplaySourceManifestV2",
    "V075PublicReplaySourceSnapshotV2",
    "V075PublicReplayRuntimeIdentityV2",
    "V075PublicReplaySemanticEvaluationV2",
    "execute_v075_public_replay_occurrence_ipc_v2",
    "freeze_v075_public_replay_occurrence_ipc_profile_v2",
    "open_v075_production_public_replay_occurrence_ipc_v2",
    "registered_v075_public_replay_child_program_v2",
    "verify_v075_public_replay_occurrence_ipc_result_v2",
]
