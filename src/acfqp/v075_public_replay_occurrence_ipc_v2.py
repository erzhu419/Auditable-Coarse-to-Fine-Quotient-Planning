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
from dataclasses import InitVar, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, NoReturn


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
_CHILD_ARG = "--acfqp-v075-public-replay-child-v2"
_VERIFIER_MODULE_NAME = (
    "acfqp.v075_portable_occurrence_evidence_bundle_v2"
)
_VERIFIER_FILENAME = "v075_portable_occurrence_evidence_bundle_v2.py"
_VERIFIER_CALLABLE = (
    "verify_v075_portable_occurrence_evidence_bundle_bytes_v2"
)

_DOMAINS = {
    "source_manifest": "acfqp:v075-public-replay-source-manifest:v2",
    "program": "acfqp:v075-public-replay-child-program:v2",
    "profile": "acfqp:v075-public-replay-occurrence-ipc-profile:v2",
    "launch": "acfqp:v075-public-replay-occurrence-ipc-launch:v2",
    "child_result": "acfqp:v075-public-replay-child-result:v2",
    "journal_entry": "acfqp:v075-public-replay-ipc-journal-entry:v2",
    "journal": "acfqp:v075-public-replay-ipc-journal:v2",
    "work": "acfqp:v075-public-replay-ipc-work:v2",
    "result": "acfqp:v075-public-replay-ipc-result:v2",
}

if len(_DOMAINS) != len(set(_DOMAINS.values())):  # pragma: no cover
    raise RuntimeError("public replay IPC content domains must be unique")

_INITIAL_JOURNAL_HASH = hashlib.sha256(
    b"acfqp:v075-public-replay-ipc-journal-initial:v2"
).hexdigest()


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


def _local_imports(module_name: str, path: Path) -> frozenset[str]:
    try:
        tree = ast.parse(path.read_bytes(), filename=str(path))
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


def _source_identity(path: Path) -> tuple[str, int]:
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw)


@dataclass(frozen=True, slots=True)
class V075PublicReplaySourceManifestEntryV2:
    module_name: str
    relative_path: str
    source_sha256: str
    source_byte_count: int

    def __post_init__(self) -> None:
        _cid(self.source_sha256, "public replay source digest")
        path = _local_module_path(self.module_name)
        if (
            path is None
            or type(self.relative_path) is not str
            or self.relative_path
            != path.relative_to(_source_root()).as_posix()
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


def _freeze_source_manifest() -> V075PublicReplaySourceManifestV2:
    pending = [_VERIFIER_MODULE_NAME]
    visited: set[str] = set()
    while pending:
        module_name = pending.pop()
        if module_name in visited:
            continue
        path = _local_module_path(module_name)
        if path is None:
            _fail("registered verifier source closure contains a missing module")
        visited.add(module_name)
        pending.extend(sorted(_local_imports(module_name, path) - visited))
        if module_name != "acfqp":
            components = module_name.split(".")
            for end in range(1, len(components)):
                parent = ".".join(components[:end])
                if _local_module_path(parent) is not None:
                    pending.append(parent)
    entries = []
    for module_name in sorted(visited):
        path = _local_module_path(module_name)
        if path is None:  # pragma: no cover
            _fail("registered verifier source disappeared during manifesting")
        source_sha256, source_byte_count = _source_identity(path)
        entries.append(
            V075PublicReplaySourceManifestEntryV2(
                module_name,
                path.relative_to(_source_root()).as_posix(),
                source_sha256,
                source_byte_count,
            )
        )
    return V075PublicReplaySourceManifestV2(tuple(entries))


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
    source_root = str(Path(__file__).resolve().parents[1])
    if source_root not in sys.path:
        sys.path.insert(0, source_root)
    try:
        from acfqp import (
            v075_portable_occurrence_evidence_bundle_v2 as portable,
        )
    except ImportError as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "registered public replay verifier could not be imported"
        ) from error
    if (
        portable.__name__ != _VERIFIER_MODULE_NAME
        or Path(portable.__file__).resolve() != _verifier_module_path()
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
    source_manifest: V075PublicReplaySourceManifestV2
    interpreter_implementation: str
    interpreter_version: str
    interpreter_cache_tag: str
    interpreter_executable_sha256: str
    interpreter_executable_byte_count: int
    verifier_module_name: str = _VERIFIER_MODULE_NAME
    verifier_callable: str = _VERIFIER_CALLABLE
    argv: tuple[str, ...] = (_CHILD_ARG,)
    _registration_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.ipc_module_sha256, "public replay child module digest")
        _cid(self.verifier_module_sha256, "public replay verifier digest")
        _cid(
            self.interpreter_executable_sha256,
            "public replay Python executable digest",
        )
        expected_manifest = _freeze_source_manifest()
        if (
            self.ipc_module_sha256 != _ipc_module_digest()
            or self.verifier_module_sha256 != _verifier_module_digest()
            or type(self.source_manifest)
            is not V075PublicReplaySourceManifestV2
            or self.source_manifest != expected_manifest
            or self.source_manifest.manifest_id
            != expected_manifest.manifest_id
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
            or self.argv != (_CHILD_ARG,)
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
            "source_manifest": self.source_manifest.to_document(),
            "source_manifest_id": self.source_manifest.manifest_id,
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
            "argv": list(self.argv),
            "isolated_python": True,
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
    def registration_id(self) -> str:
        return self._registration_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registration_id": self.registration_id}


def registered_v075_public_replay_child_program_v2(
) -> V075PublicReplayChildProgramRegistrationV2:
    executable = _interpreter_executable_path()
    return V075PublicReplayChildProgramRegistrationV2(
        _ipc_module_digest(),
        _verifier_module_digest(),
        _freeze_source_manifest(),
        sys.implementation.name,
        _interpreter_version(),
        sys.implementation.cache_tag or "",
        _interpreter_executable_sha256(),
        executable.stat().st_size,
    )


_PROFILE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PublicReplayOccurrenceIPCProfileV2:
    _issuer: InitVar[object]
    occurrence_id: str
    portable_bundle_id: str
    portable_bundle_sha256: str
    portable_bundle_byte_count: int
    process_timeout_seconds: int
    program_registration: V075PublicReplayChildProgramRegistrationV2
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
            or type(self.process_timeout_seconds) is not int
            or not 0
            < self.process_timeout_seconds
            <= MAX_PROCESS_TIMEOUT_SECONDS
            or type(self.program_registration)
            is not V075PublicReplayChildProgramRegistrationV2
            or self.program_registration
            != registered_v075_public_replay_child_program_v2()
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
            "program_registration_id": (
                self.program_registration.registration_id
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

    bundle = _verify_bundle(portable_bundle_bytes)
    return V075PublicReplayOccurrenceIPCProfileV2(
        _PROFILE_ISSUER,
        bundle.occurrence_id,
        bundle.bundle_id,
        hashlib.sha256(portable_bundle_bytes).hexdigest(),
        len(portable_bundle_bytes),
        process_timeout_seconds,
        registered_v075_public_replay_child_program_v2(),
    )


def _program_from_document(
    value: Any,
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
            "source_manifest",
            "source_manifest_id",
            "interpreter_implementation",
            "interpreter_version",
            "interpreter_cache_tag",
            "interpreter_executable_sha256",
            "interpreter_executable_byte_count",
            "verifier_module_name",
            "verifier_callable",
            "argv",
            "isolated_python",
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
        or item["isolated_python"] is not True
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
        or type(item["argv"]) is not list
    ):
        _fail("public replay program registration metadata changed")
    manifest_item = _exact_mapping(
        item["source_manifest"],
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
        or manifest.manifest_id != item["source_manifest_id"]
        or manifest.to_document() != manifest_item
    ):
        _fail("public replay source manifest content identity changed")
    program = V075PublicReplayChildProgramRegistrationV2(
        item["ipc_module_sha256"],
        item["verifier_module_sha256"],
        manifest,
        item["interpreter_implementation"],
        item["interpreter_version"],
        item["interpreter_cache_tag"],
        item["interpreter_executable_sha256"],
        item["interpreter_executable_byte_count"],
        item["verifier_module_name"],
        item["verifier_callable"],
        tuple(item["argv"]),
    )
    if (
        program.registration_id != item["registration_id"]
        or program.to_document() != item
    ):
        _fail("public replay program content identity changed")
    return program


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
    "program_registration_id",
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
) -> V075PublicReplayOccurrenceIPCProfileV2:
    item = _exact_mapping(
        value,
        _PROFILE_DOCUMENT_KEYS,
        field_name="public replay IPC profile",
    )
    program = _program_from_document(item["program_registration"])
    if (
        item["schema"]
        != "acfqp.v075_public_replay_occurrence_ipc_profile.v2"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["terminal_scope"] != TERMINAL_SCOPE
        or item["terminal_class"] != TERMINAL_CLASS
        or item["program_registration_id"] != program.registration_id
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
        item["process_timeout_seconds"],
        program,
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
    _child_result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, name in (
            (self.profile_id, "public replay profile"),
            (self.program_registration_id, "public replay program"),
            (self.occurrence_id, "public replay occurrence"),
            (self.portable_bundle_id, "portable evidence bundle"),
            (self.portable_bundle_sha256, "portable bundle byte digest"),
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
    bundle: Any,
    raw: bytes,
) -> V075PublicReplayChildVerificationResultV2:
    if (
        bundle.occurrence_id != profile.occurrence_id
        or bundle.bundle_id != profile.portable_bundle_id
        or hashlib.sha256(raw).hexdigest()
        != profile.portable_bundle_sha256
        or len(raw) != profile.portable_bundle_byte_count
    ):
        _fail("portable bundle bytes differ from the frozen replay profile")
    return V075PublicReplayChildVerificationResultV2(
        _CHILD_RESULT_ISSUER,
        profile.profile_id,
        profile.program_registration.registration_id,
        bundle.occurrence_id,
        bundle.bundle_id,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
        len(bundle.records),
        len(bundle.root_bindings),
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
class V075PublicReplayIPCActualWorkV2:
    process_launches: int
    parent_to_child_frames: int
    child_to_parent_frames: int
    parent_to_child_payload_bytes: int
    child_to_parent_payload_bytes: int
    framing_bytes: int
    protocol_checks: int
    raw_bundle_verifier_calls_parent: int
    raw_bundle_verifier_calls_child: int
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
            or type(self.protocol_checks) is not int
            or self.protocol_checks < 8
            or self.raw_bundle_verifier_calls_parent != 1
            or self.raw_bundle_verifier_calls_child != 1
            or self.process_exit_code != 0
        ):
            _fail("public replay IPC actual work is incomplete")
        object.__setattr__(
            self,
            "_work_id",
            _hash("work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replay_ipc_work.v2",
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
            "protocol_checks": self.protocol_checks,
            "raw_bundle_verifier_calls_parent": (
                self.raw_bundle_verifier_calls_parent
            ),
            "raw_bundle_verifier_calls_child": (
                self.raw_bundle_verifier_calls_child
            ),
            "process_exit_code": self.process_exit_code,
            "operational_lane": "CONSTRUCTION_PUBLIC_REPLAY",
            "evaluation_lane": False,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class V075PublicReplayOccurrenceIPCResultV2:
    profile_id: str
    occurrence_id: str
    portable_bundle_id: str
    child_verification: V075PublicReplayChildVerificationResultV2
    journal: V075PublicReplayIPCJournalV2
    actual_work: V075PublicReplayIPCActualWorkV2
    stderr_sha256: str
    stderr_byte_count: int
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.profile_id, "public replay result profile"),
            (self.occurrence_id, "public replay result occurrence"),
            (self.portable_bundle_id, "public replay result bundle"),
            (self.stderr_sha256, "public replay stderr digest"),
        ):
            _cid(value, name)
        if (
            type(self.child_verification)
            is not V075PublicReplayChildVerificationResultV2
            or type(self.journal) is not V075PublicReplayIPCJournalV2
            or type(self.actual_work) is not V075PublicReplayIPCActualWorkV2
            or self.child_verification.profile_id != self.profile_id
            or self.child_verification.occurrence_id != self.occurrence_id
            or self.child_verification.portable_bundle_id
            != self.portable_bundle_id
            or self.journal.entries[-1].message_id
            != self.child_verification.child_result_id
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
            "child_verification": self.child_verification.to_document(),
            "child_verification_id": (
                self.child_verification.child_result_id
            ),
            "journal": self.journal.to_document(),
            "journal_id": self.journal.journal_id,
            "actual_work": self.actual_work.to_document(),
            "actual_work_id": self.actual_work.work_id,
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


def _read_frame_child(stream: Any, *, byte_cap: int) -> bytes:
    header = stream.read(_FRAME_WIDTH)
    if type(header) is not bytes or len(header) != _FRAME_WIDTH:
        _fail("public replay child received a truncated frame header")
    try:
        length = int(header.decode("ascii"), 16)
    except (UnicodeError, ValueError) as error:
        raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
            "public replay child frame header is malformed"
        ) from error
    if not 0 < length <= byte_cap:
        _fail("public replay child frame length is outside its cap")
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
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.kill()
        except (ProcessLookupError, OSError):
            pass


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
                    length = int(
                        bytes(stdout[:_FRAME_WIDTH]).decode("ascii"),
                        16,
                    )
                except (UnicodeError, ValueError) as error:
                    _terminate_process(process)
                    raise V075PublicReplayOccurrenceIPCV2InvariantViolation(
                        "public replay child result frame header is malformed"
                    ) from error
                if not 0 < length <= MAX_RESULT_FRAME_BYTES:
                    _terminate_process(process)
                    _fail(
                        "public replay child result frame is outside its cap"
                    )
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


def _child_argv(
    registration: V075PublicReplayChildProgramRegistrationV2,
) -> list[str]:
    return [
        sys.executable,
        "-I",
        str(Path(__file__).resolve()),
        *registration.argv,
    ]


def _require_exact_profile(
    claimed: V075PublicReplayOccurrenceIPCProfileV2,
) -> V075PublicReplayOccurrenceIPCProfileV2:
    if type(claimed) is not V075PublicReplayOccurrenceIPCProfileV2:
        _fail("public replay IPC profile is not the registered typed object")
    replayed = _profile_from_document(claimed.to_document())
    if (
        replayed != claimed
        or replayed.profile_id != claimed.profile_id
        or _canonical_bytes(replayed.to_document())
        != _canonical_bytes(claimed.to_document())
    ):
        _fail("public replay IPC profile differs from exact reconstruction")
    return replayed


def _expected_complete_result(
    *,
    profile: V075PublicReplayOccurrenceIPCProfileV2,
    bundle: Any,
    portable_bundle_bytes: bytes,
) -> V075PublicReplayOccurrenceIPCResultV2:
    profile = _require_exact_profile(profile)
    launch = _launch_document(profile)
    launch_raw = _canonical_bytes(launch)
    child = _expected_child_result(
        profile,
        bundle,
        portable_bundle_bytes,
    )
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
        message_id=bundle.bundle_id,
        raw=portable_bundle_bytes,
    )
    _journal_entry(
        entries,
        direction="CHILD_TO_PARENT",
        message_kind="TYPED_VERIFICATION_RESULT",
        message_id=child.child_result_id,
        raw=child_raw,
    )
    journal = V075PublicReplayIPCJournalV2(tuple(entries))
    work = V075PublicReplayIPCActualWorkV2(
        1,
        2,
        1,
        len(launch_raw) + len(portable_bundle_bytes),
        len(child_raw),
        3 * _FRAME_WIDTH,
        10,
        1,
        1,
        0,
    )
    return V075PublicReplayOccurrenceIPCResultV2(
        profile.profile_id,
        profile.occurrence_id,
        profile.portable_bundle_id,
        child,
        journal,
        work,
        hashlib.sha256(b"").hexdigest(),
        0,
    )


def execute_v075_public_replay_occurrence_ipc_v2(
    *,
    profile: V075PublicReplayOccurrenceIPCProfileV2,
    portable_bundle_bytes: bytes,
) -> V075PublicReplayOccurrenceIPCResultV2:
    """Replay one already-frozen public bundle in one isolated child."""

    profile = _require_exact_profile(profile)
    bundle = _verify_bundle(portable_bundle_bytes)
    expected = _expected_child_result(
        profile,
        bundle,
        portable_bundle_bytes,
    )
    launch = _launch_document(profile)
    launch_raw = _canonical_bytes(launch)
    process: subprocess.Popen[bytes] | None = None
    child_raw = b""
    stderr = b""
    exit_code: int | None = None
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
            process = subprocess.Popen(
                _child_argv(profile.program_registration),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=sandbox,
                env=environment,
                close_fds=True,
                start_new_session=True,
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

    if exit_code != 0:
        _fail("public replay child process did not exit successfully")
    if stderr:
        _fail("public replay child emitted forbidden stderr bytes")
    child_verification = _validate_child_result(child_raw, expected)
    reconstructed = _expected_complete_result(
        profile=profile,
        bundle=bundle,
        portable_bundle_bytes=portable_bundle_bytes,
    )
    if (
        child_verification != reconstructed.child_verification
        or child_raw != reconstructed.child_verification.canonical_bytes
    ):
        _fail("public replay child differs from complete host reconstruction")
    return reconstructed


def verify_v075_public_replay_occurrence_ipc_result_v2(
    *,
    claimed: V075PublicReplayOccurrenceIPCResultV2,
    profile: V075PublicReplayOccurrenceIPCProfileV2,
    portable_bundle_bytes: bytes,
) -> V075PublicReplayOccurrenceIPCResultV2:
    """Independently replay public result semantics without launching a child."""

    if type(claimed) is not V075PublicReplayOccurrenceIPCResultV2:
        _fail("public replay result verification received stale typed inputs")
    profile = _require_exact_profile(profile)
    bundle = _verify_bundle(portable_bundle_bytes)
    expected = _expected_complete_result(
        profile=profile,
        bundle=bundle,
        portable_bundle_bytes=portable_bundle_bytes,
    )
    if (
        claimed != expected
        or claimed.result_id != expected.result_id
        or claimed.to_document() != expected.to_document()
        or claimed.canonical_bytes != expected.canonical_bytes
    ):
        _fail("public replay IPC result differs from independent verification")
    return claimed


def open_v075_production_public_replay_occurrence_ipc_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PublicReplayProductionV2NotReady(
        "construction-only public replay does not authorize production, "
        "held-out use, scientific endpoint credit, or certificates"
    )


def _child_main() -> int:
    try:
        launch_raw = _read_frame_child(
            sys.stdin.buffer,
            byte_cap=MAX_LAUNCH_FRAME_BYTES,
        )
        _launch, profile = _load_launch(launch_raw)
        bundle_raw = _read_frame_child(
            sys.stdin.buffer,
            byte_cap=MAX_BUNDLE_FRAME_BYTES,
        )
        if sys.stdin.buffer.read(1) != b"":
            _fail("public replay child received an extra input frame or byte")
        bundle = _verify_bundle(bundle_raw)
        result = _expected_child_result(profile, bundle, bundle_raw)
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
    if len(sys.argv) == 2 and sys.argv[1] == _CHILD_ARG:
        raise SystemExit(_child_main())
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
    "V075PublicReplayIPCActualWorkV2",
    "V075PublicReplayIPCJournalEntryV2",
    "V075PublicReplayIPCJournalV2",
    "V075PublicReplayOccurrenceIPCV2InvariantViolation",
    "V075PublicReplayOccurrenceIPCProfileV2",
    "V075PublicReplayOccurrenceIPCResultV2",
    "V075PublicReplayProductionV2NotReady",
    "V075PublicReplaySourceManifestEntryV2",
    "V075PublicReplaySourceManifestV2",
    "execute_v075_public_replay_occurrence_ipc_v2",
    "freeze_v075_public_replay_occurrence_ipc_profile_v2",
    "open_v075_production_public_replay_occurrence_ipc_v2",
    "registered_v075_public_replay_child_program_v2",
    "verify_v075_public_replay_occurrence_ipc_result_v2",
]
