"""Sealed post-freeze executors backed by a content-addressed runtime tree.

The Phase-3E route decision must be frozen before any route executor exists.
This module therefore separates an inert, serializable executor recipe from a
runtime-only factory.  The factory resolves the recipe's runtime tree from a
CAS, verifies every byte, copies it into a private lease, and only then asks a
trusted constructor to create the selected-route executor.

Snapshot creation is a build-epoch operation.  It is intentionally separate
from :class:`SealedPostFreezeExecutorFactoryV1`: an official route attempt may
only resolve an already existing snapshot and can never fall back to the live
checkout.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field, replace
import hashlib
import importlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import threading
from types import MappingProxyType
from typing import Any, Callable, Iterator, Mapping, Protocol

from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    AccessOperation,
    AccessRouteScope,
    FailClosedAccessController,
    RouteDecisionFreezeAttestationV1,
)
from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    CounterRegistryV1,
    ReducerEnum,
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import (
    NativeCounterRecorderV1,
    RecordedWorkV1,
    derive_failed_recorded_work_v1,
    derive_recorded_work_v1,
    verify_recorded_work_v1,
)
from acfqp.phase3e_ids import (
    EXECUTOR_RECIPE_DOMAIN,
    RUNTIME_FACTORY_CARDINALITY_DOMAIN,
    RUNTIME_MANIFEST_CAP_PROFILE_DOMAIN,
    RUNTIME_TREE_MANIFEST_DOMAIN,
    SEALED_EXECUTOR_CONSTRUCTION_RECEIPT_DOMAIN,
    SEALED_EXECUTOR_EXECUTION_MERGE_PROOF_DOMAIN,
    SEALED_EXECUTOR_FAILURE_MERGE_PROOF_DOMAIN,
    SEALED_EXECUTOR_FAILURE_EVIDENCE_DOMAIN,
    TRUSTED_CONSTRUCTOR_REGISTRY_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)
from acfqp.routing_v1 import RouteSelection, TypedNotApplicable


SCHEMA_VERSION = "1.0.0"

# The manifest is build-time material, but the route upper must be finite
# before its bytes are resolved.  These limits are deliberately independent
# of the worker sandbox caps: the private CAS lease is an additional physical
# copy and is charged exactly once by this factory.
RUNTIME_MANIFEST_MAX_FILE_COUNT = 512
RUNTIME_MANIFEST_MAX_TOTAL_BYTES = 8 * 1024 * 1024
RUNTIME_MANIFEST_MAX_DOCUMENT_BYTES = 1024 * 1024
RUNTIME_MANIFEST_MAX_PATH_BYTES = 512
RUNTIME_FACTORY_WORKING_BYTES_CAP = 64 * 1024 * 1024

# Successful factory replay has four byte/hash passes over the runtime tree:
# CAS verification, private-copy materialization, pre-construction lease
# verification, and post-execution lease verification.
RUNTIME_FACTORY_TREE_PASSES = 4
RUNTIME_FACTORY_PROTOCOL_CHECKS_UPPER = 10
RUNTIME_FACTORY_INTEGRITY_BASE_UPPER = 8
RUNTIME_FACTORY_CAP_CHECKS = 3


class Phase3ESealedExecutorV1Error(ValueError):
    """A runtime tree, recipe, freeze binding, or factory use is invalid."""


def sealed_failure_stage_from_evidence_v1(
    access_log: AccessEventLogV1,
    delegate_partial_work: RecordedWorkV1 | None,
) -> str:
    """Derive a coarse, replayable boundary from retained observable evidence."""

    if type(access_log) is not AccessEventLogV1 or (
        delegate_partial_work is not None
        and type(delegate_partial_work) is not RecordedWorkV1
    ):
        raise Phase3ESealedExecutorV1Error(
            "sealed failure stage requires exact access/work evidence"
        )
    operations = tuple(event.operation for event in access_log.events)
    if AccessOperation.CONSTRUCT_SELECTED_EXECUTOR in operations:
        return (
            "SELECTED_EXECUTOR"
            if delegate_partial_work is not None
            else "TRUSTED_CONSTRUCTOR"
        )
    if AccessOperation.OPEN_RUNTIME_PRIVATE_LEASE in operations:
        return "PRIVATE_LEASE"
    if AccessOperation.RESOLVE_RUNTIME_CAS in operations:
        return "RUNTIME_CAS_RESOLVE"
    return "FROZEN_BINDING"


@dataclass(frozen=True, slots=True)
class RuntimeManifestCapProfileV1:
    """Finite pre-execution limits for the selected runtime snapshot."""

    max_file_count: int = RUNTIME_MANIFEST_MAX_FILE_COUNT
    max_total_bytes: int = RUNTIME_MANIFEST_MAX_TOTAL_BYTES
    max_manifest_document_bytes: int = RUNTIME_MANIFEST_MAX_DOCUMENT_BYTES
    max_path_bytes: int = RUNTIME_MANIFEST_MAX_PATH_BYTES
    factory_working_bytes_cap: int = RUNTIME_FACTORY_WORKING_BYTES_CAP
    tree_passes: int = RUNTIME_FACTORY_TREE_PASSES
    profile_key: str = "phase3e-runtime-manifest-caps-v1"
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        expected = (
            RUNTIME_MANIFEST_MAX_FILE_COUNT,
            RUNTIME_MANIFEST_MAX_TOTAL_BYTES,
            RUNTIME_MANIFEST_MAX_DOCUMENT_BYTES,
            RUNTIME_MANIFEST_MAX_PATH_BYTES,
            RUNTIME_FACTORY_WORKING_BYTES_CAP,
            RUNTIME_FACTORY_TREE_PASSES,
            "phase3e-runtime-manifest-caps-v1",
            SCHEMA_VERSION,
        )
        if (
            self.max_file_count,
            self.max_total_bytes,
            self.max_manifest_document_bytes,
            self.max_path_bytes,
            self.factory_working_bytes_cap,
            self.tree_passes,
            self.profile_key,
            self.schema_version,
        ) != expected:
            raise Phase3ESealedExecutorV1Error(
                "runtime manifest cap profile differs from the frozen V1 profile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.runtime_manifest_cap_profile.v1",
            "schema_version": self.schema_version,
            "profile_key": self.profile_key,
            "max_file_count": self.max_file_count,
            "max_total_bytes": self.max_total_bytes,
            "max_manifest_document_bytes": self.max_manifest_document_bytes,
            "max_path_bytes": self.max_path_bytes,
            "factory_working_bytes_cap": self.factory_working_bytes_cap,
            "tree_passes": self.tree_passes,
        }

    @property
    def runtime_manifest_cap_profile_id(self) -> str:
        return content_id(RUNTIME_MANIFEST_CAP_PROFILE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "runtime_manifest_cap_profile_id": (
                self.runtime_manifest_cap_profile_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "RuntimeManifestCapProfileV1":
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "profile_key",
                "max_file_count",
                "max_total_bytes",
                "max_manifest_document_bytes",
                "max_path_bytes",
                "factory_working_bytes_cap",
                "tree_passes",
                "runtime_manifest_cap_profile_id",
            },
            context="runtime manifest cap profile",
        )
        if document["schema"] != "acfqp.runtime_manifest_cap_profile.v1":
            raise Phase3ESealedExecutorV1Error(
                "runtime manifest cap profile schema mismatch"
            )
        result = cls(
            document["max_file_count"],
            document["max_total_bytes"],
            document["max_manifest_document_bytes"],
            document["max_path_bytes"],
            document["factory_working_bytes_cap"],
            document["tree_passes"],
            document["profile_key"],
            document["schema_version"],
        )
        if (
            document["runtime_manifest_cap_profile_id"]
            != result.runtime_manifest_cap_profile_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "runtime manifest cap profile content ID mismatch"
            )
        return result


OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE = RuntimeManifestCapProfileV1()


def runtime_factory_upper_values_v1(
    profile: RuntimeManifestCapProfileV1 | None = None,
) -> Mapping[str, int]:
    """Return the exact registered formula evaluated at manifest hard caps."""

    cap = profile or OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE
    cap = RuntimeManifestCapProfileV1.from_dict(cap.to_dict())
    files = cap.max_file_count
    total = cap.max_total_bytes
    return MappingProxyType(
        {
            "common.hash_invocations": 1 + cap.tree_passes * files,
            "common.integrity_checks": (
                RUNTIME_FACTORY_INTEGRITY_BASE_UPPER
                + cap.tree_passes * files
            ),
            "common.protocol_checks": RUNTIME_FACTORY_PROTOCOL_CHECKS_UPPER,
            "control.cap_checks": RUNTIME_FACTORY_CAP_CHECKS,
            "io.read_bytes": (
                cap.max_manifest_document_bytes + cap.tree_passes * total
            ),
            "io.staged_bytes": total,
            "io.output_bytes": 0,
            "io.mounted_bytes_peak": total,
            "memory.working_bytes_peak": cap.factory_working_bytes_cap,
        }
    )


def _nonempty_text(value: object, field_name: str) -> str:
    if type(value) is not str or not value:
        raise Phase3ESealedExecutorV1Error(f"{field_name} must be nonempty text")
    return value


def _relative_runtime_path(value: object, field_name: str) -> str:
    text = _nonempty_text(value, field_name)
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or text != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
        or len(text.encode("utf-8")) > RUNTIME_MANIFEST_MAX_PATH_BYTES
    ):
        raise Phase3ESealedExecutorV1Error(
            f"{field_name} must be a bounded normalized relative POSIX path"
        )
    return text


@dataclass(slots=True)
class _FactoryWorkMeterV1:
    recorder: NativeCounterRecorderV1

    def read(self, amount: int) -> None:
        self.recorder.add("io.read_bytes", amount)

    def staged(self, amount: int) -> None:
        self.recorder.add("io.staged_bytes", amount)

    def hash(self, amount: int = 1) -> None:
        self.recorder.add("common.hash_invocations", amount)

    def integrity(self, amount: int = 1) -> None:
        self.recorder.add("common.integrity_checks", amount)

    def protocol(self, amount: int = 1) -> None:
        self.recorder.add("common.protocol_checks", amount)

    def cap_check(self, amount: int = 1) -> None:
        self.recorder.add("control.cap_checks", amount)

    def mounted_peak(self, amount: int) -> None:
        self.recorder.observe_peak("io.mounted_bytes_peak", amount)

    def working_cap(self, amount: int) -> None:
        self.recorder.observe_peak("memory.working_bytes_peak", amount)


def _file_sha256(raw: bytes, meter: _FactoryWorkMeterV1 | None = None) -> str:
    if meter is not None:
        meter.hash()
    return hashlib.sha256(raw).hexdigest()


def _stable_read_regular_file(
    path: Path,
    meter: _FactoryWorkMeterV1 | None = None,
    *,
    max_bytes: int | None = None,
) -> bytes:
    """Read a file without accepting symlink or concurrent-rewrite races."""

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise Phase3ESealedExecutorV1Error(
            f"runtime file cannot be opened safely: {path}"
        ) from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise Phase3ESealedExecutorV1Error(
                f"runtime entry is not a regular file: {path}"
            )
        if max_bytes is not None and before.st_size > max_bytes:
            raise Phase3ESealedExecutorV1Error(
                f"runtime file exceeds its preregistered byte limit: {path}"
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        try:
            path_stat = path.lstat()
        except OSError as error:
            raise Phase3ESealedExecutorV1Error(
                f"runtime file disappeared during verification: {path}"
            ) from error
        stable_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        if stable_identity != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) or (before.st_dev, before.st_ino) != (
            path_stat.st_dev,
            path_stat.st_ino,
        ):
            raise Phase3ESealedExecutorV1Error(
                f"runtime file changed during verification: {path}"
            )
        raw = b"".join(chunks)
        if len(raw) != before.st_size:
            raise Phase3ESealedExecutorV1Error(
                f"runtime file size changed during verification: {path}"
            )
        if meter is not None:
            meter.read(len(raw))
        return raw
    finally:
        os.close(descriptor)


def _regular_tree_paths(root: Path) -> tuple[str, ...]:
    """Enumerate an exact tree while rejecting links and special entries."""

    if root.is_symlink() or not root.is_dir():
        raise Phase3ESealedExecutorV1Error(
            "runtime tree root must be a real directory"
        )
    rows: list[str] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = tuple(os.scandir(directory))
        except OSError as error:
            raise Phase3ESealedExecutorV1Error(
                f"cannot enumerate runtime tree directory: {directory}"
            ) from error
        for entry in entries:
            relative = Path(entry.path).relative_to(root).as_posix()
            if entry.is_symlink():
                raise Phase3ESealedExecutorV1Error(
                    f"runtime tree may not contain symlinks: {relative}"
                )
            if entry.is_dir(follow_symlinks=False):
                pending.append(Path(entry.path))
            elif entry.is_file(follow_symlinks=False):
                rows.append(_relative_runtime_path(relative, "runtime path"))
            else:
                raise Phase3ESealedExecutorV1Error(
                    f"runtime tree may contain only directories/files: {relative}"
                )
    return tuple(sorted(rows))


@dataclass(frozen=True, slots=True, order=True)
class RuntimeTreeEntryV1:
    relative_path: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "relative_path",
            _relative_runtime_path(self.relative_path, "relative_path"),
        )
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise Phase3ESealedExecutorV1Error(
                "runtime file size must be a nonnegative integer"
            )
        try:
            parse_content_id(self.sha256)
        except ValueError as error:
            raise Phase3ESealedExecutorV1Error(
                "runtime file SHA-256 must be 64 lowercase hex characters"
            ) from error

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "RuntimeTreeEntryV1":
        require_exact_fields(
            document,
            {"relative_path", "size_bytes", "sha256"},
            context="runtime tree entry",
        )
        return cls(
            document["relative_path"],
            document["size_bytes"],
            document["sha256"],
        )


@dataclass(frozen=True, slots=True)
class RuntimeTreeManifestV1:
    entries: tuple[RuntimeTreeEntryV1, ...]
    tree_semantics_id: str = "acfqp-python-runtime-tree-v1"
    _runtime_tree_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.entries) is not tuple or not self.entries:
            raise Phase3ESealedExecutorV1Error(
                "runtime tree manifest requires an immutable nonempty entry tuple"
            )
        if not all(type(row) is RuntimeTreeEntryV1 for row in self.entries):
            raise Phase3ESealedExecutorV1Error(
                "runtime tree manifest contains an invalid entry"
            )
        paths = tuple(row.relative_path for row in self.entries)
        if paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
            raise Phase3ESealedExecutorV1Error(
                "runtime tree entries must be unique and canonically sorted"
            )
        if len(self.entries) > RUNTIME_MANIFEST_MAX_FILE_COUNT:
            raise Phase3ESealedExecutorV1Error(
                "runtime tree exceeds the preregistered file-count cap"
            )
        if sum(row.size_bytes for row in self.entries) > RUNTIME_MANIFEST_MAX_TOTAL_BYTES:
            raise Phase3ESealedExecutorV1Error(
                "runtime tree exceeds the preregistered total-byte cap"
            )
        _nonempty_text(self.tree_semantics_id, "tree_semantics_id")
        object.__setattr__(
            self,
            "_runtime_tree_id",
            content_id(RUNTIME_TREE_MANIFEST_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.runtime_tree_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "tree_semantics_id": self.tree_semantics_id,
            "entries": [row.to_dict() for row in self.entries],
        }

    @property
    def runtime_tree_id(self) -> str:
        return self._runtime_tree_id

    @property
    def file_count(self) -> int:
        return len(self.entries)

    @property
    def manifest_document_bytes(self) -> int:
        return len(canonical_json_bytes(self.to_dict()))

    @property
    def total_bytes(self) -> int:
        return sum(row.size_bytes for row in self.entries)

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "runtime_tree_id": self.runtime_tree_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "RuntimeTreeManifestV1":
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "tree_semantics_id",
                "entries",
                "runtime_tree_id",
            },
            context="runtime tree manifest",
        )
        if (
            document["schema"] != "acfqp.runtime_tree_manifest.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["entries"]) is not list
        ):
            raise Phase3ESealedExecutorV1Error(
                "runtime tree manifest schema mismatch"
            )
        result = cls(
            tuple(RuntimeTreeEntryV1.from_dict(row) for row in document["entries"]),
            document["tree_semantics_id"],
        )
        try:
            parse_content_id(document["runtime_tree_id"])
        except ValueError as error:
            raise Phase3ESealedExecutorV1Error(
                "runtime tree manifest ID is invalid"
            ) from error
        if document["runtime_tree_id"] != result.runtime_tree_id:
            raise Phase3ESealedExecutorV1Error(
                "runtime tree manifest content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class RuntimeFactoryCardinalityV1:
    """Exact preselection factory counts derived from one bound manifest."""

    runtime_tree_id: str
    runtime_manifest_cap_profile_id: str
    file_count: int
    total_bytes: int
    manifest_document_bytes: int
    measured_before_execution: bool = True
    depends_on_actual_route_work: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "runtime_tree_id",
            "runtime_manifest_cap_profile_id",
        ):
            try:
                parse_content_id(getattr(self, field_name))
            except ValueError as error:
                raise Phase3ESealedExecutorV1Error(
                    f"{field_name} must be a full content ID"
                ) from error
        cap = OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE
        if self.runtime_manifest_cap_profile_id != (
            cap.runtime_manifest_cap_profile_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "runtime factory cardinality uses another cap profile"
            )
        for field_name, limit in (
            ("file_count", cap.max_file_count),
            ("total_bytes", cap.max_total_bytes),
            ("manifest_document_bytes", cap.max_manifest_document_bytes),
        ):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0 or value > limit:
                raise Phase3ESealedExecutorV1Error(
                    f"{field_name} exceeds the registered runtime cap"
                )
        if (
            self.measured_before_execution is not True
            or self.depends_on_actual_route_work is not False
            or self.schema_version != SCHEMA_VERSION
        ):
            raise Phase3ESealedExecutorV1Error(
                "runtime factory cardinality is not a frozen V1 source"
            )

    @classmethod
    def from_manifest(
        cls,
        manifest: RuntimeTreeManifestV1,
        cap_profile: RuntimeManifestCapProfileV1 | None = None,
    ) -> "RuntimeFactoryCardinalityV1":
        if type(manifest) is not RuntimeTreeManifestV1:
            raise Phase3ESealedExecutorV1Error(
                "runtime factory cardinality requires a typed manifest"
            )
        parsed = RuntimeTreeManifestV1.from_dict(manifest.to_dict())
        if cap_profile is not None and type(cap_profile) is not RuntimeManifestCapProfileV1:
            raise Phase3ESealedExecutorV1Error(
                "runtime factory cardinality requires the exact cap profile type"
            )
        cap = cap_profile or OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE
        cap = RuntimeManifestCapProfileV1.from_dict(cap.to_dict())
        return cls(
            parsed.runtime_tree_id,
            cap.runtime_manifest_cap_profile_id,
            parsed.file_count,
            parsed.total_bytes,
            parsed.manifest_document_bytes,
        )

    def upper_values(self) -> tuple[tuple[str, int], ...]:
        return tuple(
            sorted(
                {
                    "common.hash_invocations": (
                        1 + RUNTIME_FACTORY_TREE_PASSES * self.file_count
                    ),
                    "common.integrity_checks": (
                        RUNTIME_FACTORY_INTEGRITY_BASE_UPPER
                        + RUNTIME_FACTORY_TREE_PASSES * self.file_count
                    ),
                    "common.protocol_checks": (
                        RUNTIME_FACTORY_PROTOCOL_CHECKS_UPPER
                    ),
                    "control.cap_checks": RUNTIME_FACTORY_CAP_CHECKS,
                    "io.read_bytes": (
                        self.manifest_document_bytes
                        + RUNTIME_FACTORY_TREE_PASSES * self.total_bytes
                    ),
                    "io.staged_bytes": self.total_bytes,
                    "io.output_bytes": 0,
                    "io.mounted_bytes_peak": self.total_bytes,
                    "memory.working_bytes_peak": (
                        RUNTIME_FACTORY_WORKING_BYTES_CAP
                    ),
                }.items()
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.runtime_factory_cardinality.v1",
            "schema_version": self.schema_version,
            "runtime_tree_id": self.runtime_tree_id,
            "runtime_manifest_cap_profile_id": (
                self.runtime_manifest_cap_profile_id
            ),
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "manifest_document_bytes": self.manifest_document_bytes,
            "counter_upper_values": [
                {"name": name, "value": value}
                for name, value in self.upper_values()
            ],
            "measured_before_execution": True,
            "depends_on_actual_route_work": False,
        }

    @property
    def runtime_factory_cardinality_id(self) -> str:
        return content_id(RUNTIME_FACTORY_CARDINALITY_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "runtime_factory_cardinality_id": self.runtime_factory_cardinality_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "RuntimeFactoryCardinalityV1":
        fields = {
            "schema", "schema_version", "runtime_tree_id",
            "runtime_manifest_cap_profile_id", "file_count", "total_bytes",
            "manifest_document_bytes", "counter_upper_values",
            "measured_before_execution", "depends_on_actual_route_work",
            "runtime_factory_cardinality_id",
        }
        require_exact_fields(
            document, fields, context="runtime factory cardinality"
        )
        if (
            document["schema"] != "acfqp.runtime_factory_cardinality.v1"
            or type(document["counter_upper_values"]) is not list
        ):
            raise Phase3ESealedExecutorV1Error(
                "runtime factory cardinality schema mismatch"
            )
        rows: list[tuple[str, int]] = []
        for row in document["counter_upper_values"]:
            require_exact_fields(
                row, {"name", "value"}, context="runtime cardinality row"
            )
            rows.append((row["name"], row["value"]))
        result = cls(
            document["runtime_tree_id"],
            document["runtime_manifest_cap_profile_id"],
            document["file_count"],
            document["total_bytes"],
            document["manifest_document_bytes"],
            document["measured_before_execution"],
            document["depends_on_actual_route_work"],
            document["schema_version"],
        )
        if tuple(rows) != result.upper_values() or (
            document["runtime_factory_cardinality_id"]
            != result.runtime_factory_cardinality_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "runtime factory cardinality content/formula mismatch"
            )
        return result


def _manifest_from_root_v1(root: Path) -> RuntimeTreeManifestV1:
    entries: list[RuntimeTreeEntryV1] = []
    for relative in _regular_tree_paths(root):
        raw = _stable_read_regular_file(root / relative)
        entries.append(RuntimeTreeEntryV1(relative, len(raw), _file_sha256(raw)))
    return RuntimeTreeManifestV1(tuple(entries))


def _verify_root_against_manifest_v1(
    root: Path,
    manifest: RuntimeTreeManifestV1,
    meter: _FactoryWorkMeterV1 | None = None,
) -> None:
    observed = _regular_tree_paths(root)
    expected = tuple(row.relative_path for row in manifest.entries)
    if meter is not None:
        meter.integrity()
    if observed != expected:
        raise Phase3ESealedExecutorV1Error(
            "runtime tree file set differs from its content-addressed manifest"
        )
    for row in manifest.entries:
        raw = _stable_read_regular_file(
            root / row.relative_path,
            meter,
            max_bytes=row.size_bytes,
        )
        digest = _file_sha256(raw, meter)
        if meter is not None:
            meter.integrity()
        if len(raw) != row.size_bytes or digest != row.sha256:
            raise Phase3ESealedExecutorV1Error(
                f"runtime tree entry differs from manifest: {row.relative_path}"
            )


_VERIFIED_TREE_TOKEN = object()
_LEASE_TOKEN = object()
_CONSTRUCTION_GRANT_TOKEN = object()


@dataclass(frozen=True, slots=True)
class RuntimeTreeLeaseV1:
    """Private verified copy whose lifetime is one selected-route invocation."""

    root: Path
    manifest: RuntimeTreeManifestV1
    _token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _LEASE_TOKEN:
            raise Phase3ESealedExecutorV1Error(
                "runtime tree leases may only be minted by the CAS verifier"
            )

    @property
    def runtime_tree_id(self) -> str:
        return self.manifest.runtime_tree_id

    def verify(self, meter: _FactoryWorkMeterV1 | None = None) -> None:
        _verify_root_against_manifest_v1(self.root, self.manifest, meter)


@dataclass(frozen=True, slots=True)
class VerifiedRuntimeTreeV1:
    """Runtime-only proof that an existing CAS object replayed exactly."""

    cas_object_root: Path
    tree_root: Path
    manifest: RuntimeTreeManifestV1
    _token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _VERIFIED_TREE_TOKEN:
            raise Phase3ESealedExecutorV1Error(
                "verified runtime trees may only be minted by the CAS verifier"
            )

    @property
    def runtime_tree_id(self) -> str:
        return self.manifest.runtime_tree_id

    def verify(self, meter: _FactoryWorkMeterV1 | None = None) -> None:
        _verify_root_against_manifest_v1(self.tree_root, self.manifest, meter)

    @contextmanager
    def open_private_lease(
        self,
        meter: _FactoryWorkMeterV1 | None = None,
    ) -> Iterator[RuntimeTreeLeaseV1]:
        """Copy verified bytes into a route-private, non-live-checkout tree."""

        with tempfile.TemporaryDirectory(
            prefix=f"acfqp-runtime-{self.runtime_tree_id[:12]}-"
        ) as temporary:
            destination = Path(temporary) / "tree"
            destination.mkdir()
            for row in self.manifest.entries:
                raw = _stable_read_regular_file(
                    self.tree_root / row.relative_path,
                    meter,
                    max_bytes=row.size_bytes,
                )
                digest = _file_sha256(raw, meter)
                if meter is not None:
                    meter.integrity()
                if len(raw) != row.size_bytes or digest != row.sha256:
                    raise Phase3ESealedExecutorV1Error(
                        "CAS runtime changed while creating the private lease"
                    )
                target = destination / row.relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                target.chmod(0o444)
                if meter is not None:
                    meter.staged(len(raw))
            lease = RuntimeTreeLeaseV1(destination, self.manifest, _LEASE_TOKEN)
            if meter is not None:
                meter.mounted_peak(self.manifest.total_bytes)
            lease.verify(meter)
            yield lease
            # A trusted constructor must not mutate the supposedly immutable
            # runtime it received.  Detect such a defect before returning a
            # route result to the runner.
            lease.verify(meter)


@dataclass(frozen=True, slots=True)
class RuntimeTreeCASV1:
    """Read/write build-time handle for a directory-scoped runtime CAS."""

    root: Path

    def __post_init__(self) -> None:
        root = Path(self.root)
        if not root.is_absolute():
            raise Phase3ESealedExecutorV1Error("runtime CAS root must be absolute")
        if root.resolve(strict=False) != root or root.is_symlink():
            raise Phase3ESealedExecutorV1Error(
                "runtime CAS root may not traverse a symlink or alias"
            )
        object.__setattr__(self, "root", root)

    @property
    def objects_root(self) -> Path:
        return self.root / "runtime-trees"

    def object_root(self, runtime_tree_id: str) -> Path:
        try:
            parse_content_id(runtime_tree_id)
        except ValueError as error:
            raise Phase3ESealedExecutorV1Error(
                "runtime tree ID must be a full content ID"
            ) from error
        return self.objects_root / runtime_tree_id

    def snapshot_build_tree(self, source_root: Path) -> RuntimeTreeManifestV1:
        """Create/reuse one immutable snapshot; never call during route execution."""

        source = Path(source_root).resolve(strict=True)
        manifest = _manifest_from_root_v1(source)
        if self.objects_root.is_symlink():
            raise Phase3ESealedExecutorV1Error(
                "runtime CAS objects directory may not be a symlink"
            )
        self.objects_root.mkdir(parents=True, exist_ok=True)
        target = self.object_root(manifest.runtime_tree_id)
        if target.exists():
            resolved = self.resolve(manifest.runtime_tree_id)
            if resolved.manifest != manifest:
                raise Phase3ESealedExecutorV1Error(
                    "existing runtime CAS object has conflicting content"
                )
            return manifest

        staging = Path(
            tempfile.mkdtemp(prefix=".staging-runtime-", dir=self.objects_root)
        )
        try:
            tree = staging / "tree"
            tree.mkdir()
            for row in manifest.entries:
                raw = _stable_read_regular_file(source / row.relative_path)
                if len(raw) != row.size_bytes or _file_sha256(raw) != row.sha256:
                    raise Phase3ESealedExecutorV1Error(
                        "source runtime changed while snapshotting"
                    )
                destination = tree / row.relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
                destination.chmod(0o444)
            (staging / "manifest.json").write_bytes(
                canonical_json_bytes(manifest.to_dict())
            )
            _verify_root_against_manifest_v1(tree, manifest)
            try:
                os.replace(staging, target)
            except FileExistsError:
                # A concurrent builder won the content-addressed race.  Its
                # bytes must still replay exactly below.
                pass
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        self.resolve(manifest.runtime_tree_id)
        return manifest

    def resolve(
        self,
        runtime_tree_id: str,
        *,
        meter: _FactoryWorkMeterV1 | None = None,
        cap_profile: RuntimeManifestCapProfileV1 | None = None,
    ) -> VerifiedRuntimeTreeV1:
        """Replay the manifest and exact file set before granting a lease."""

        if cap_profile is not None and type(cap_profile) is not RuntimeManifestCapProfileV1:
            raise Phase3ESealedExecutorV1Error(
                "runtime CAS resolution requires the exact cap profile type"
            )
        cap = cap_profile or OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE
        if meter is not None:
            meter.working_cap(cap.factory_working_bytes_cap)
        if self.objects_root.is_symlink():
            raise Phase3ESealedExecutorV1Error(
                "runtime CAS objects directory may not be a symlink"
            )
        object_root = self.object_root(runtime_tree_id)
        if object_root.is_symlink() or not object_root.is_dir():
            raise Phase3ESealedExecutorV1Error(
                "runtime tree is absent from the configured CAS"
            )
        manifest_path = object_root / "manifest.json"
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise Phase3ESealedExecutorV1Error(
                "runtime CAS object lacks a regular manifest"
            )
        manifest_raw = _stable_read_regular_file(
            manifest_path,
            meter,
            max_bytes=(
                None
                if cap_profile is None
                else cap.max_manifest_document_bytes
            ),
        )
        document = loads_canonical_json(manifest_raw)
        if not isinstance(document, Mapping):
            raise Phase3ESealedExecutorV1Error(
                "runtime tree manifest root must be an object"
            )
        if meter is not None:
            # RuntimeTreeManifestV1 computes exactly one cached content ID.
            meter.hash()
            meter.integrity()
        manifest = RuntimeTreeManifestV1.from_dict(document)
        if meter is not None:
            for observed, limit, name in (
                (manifest.file_count, cap.max_file_count, "file count"),
                (manifest.total_bytes, cap.max_total_bytes, "total bytes"),
                (
                    len(manifest_raw),
                    cap.max_manifest_document_bytes,
                    "manifest document bytes",
                ),
            ):
                meter.cap_check()
                if observed > limit:
                    raise Phase3ESealedExecutorV1Error(
                        f"runtime {name} exceeds its preregistered cap"
                    )
        if manifest.runtime_tree_id != runtime_tree_id:
            raise Phase3ESealedExecutorV1Error(
                "foreign runtime tree is stored under this CAS key"
            )
        if meter is not None:
            meter.integrity()
        expected_object_entries = {"manifest.json", "tree"}
        actual_object_entries = {row.name for row in os.scandir(object_root)}
        if actual_object_entries != expected_object_entries:
            raise Phase3ESealedExecutorV1Error(
                "runtime CAS object contains unregistered top-level entries"
            )
        if meter is not None:
            meter.integrity()
        tree_root = object_root / "tree"
        _verify_root_against_manifest_v1(tree_root, manifest, meter)
        return VerifiedRuntimeTreeV1(
            object_root,
            tree_root,
            manifest,
            _VERIFIED_TREE_TOKEN,
        )


@dataclass(frozen=True, slots=True)
class ExecutorRecipeV1:
    """Serializable intent; it is not itself executable or callable."""

    runtime_tree_id: str
    selected_route: RouteSelection
    executor_semantics_id: str
    entrypoint_relative_path: str
    executor_configuration_id: str
    _executor_recipe_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            parse_content_id(self.runtime_tree_id)
            parse_content_id(self.executor_configuration_id)
        except ValueError as error:
            raise Phase3ESealedExecutorV1Error(
                "executor recipe content references must be full IDs"
            ) from error
        try:
            object.__setattr__(
                self,
                "selected_route",
                RouteSelection(self.selected_route),
            )
        except ValueError as error:
            raise Phase3ESealedExecutorV1Error(
                "executor recipe has an invalid route"
            ) from error
        _nonempty_text(self.executor_semantics_id, "executor_semantics_id")
        object.__setattr__(
            self,
            "entrypoint_relative_path",
            _relative_runtime_path(
                self.entrypoint_relative_path,
                "entrypoint_relative_path",
            ),
        )
        object.__setattr__(
            self,
            "_executor_recipe_id",
            content_id(EXECUTOR_RECIPE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.executor_recipe.v1",
            "schema_version": SCHEMA_VERSION,
            "runtime_tree_id": self.runtime_tree_id,
            "selected_route": self.selected_route.value,
            "executor_semantics_id": self.executor_semantics_id,
            "entrypoint_relative_path": self.entrypoint_relative_path,
            "executor_configuration_id": self.executor_configuration_id,
        }

    @property
    def executor_recipe_id(self) -> str:
        return self._executor_recipe_id

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "executor_recipe_id": self.executor_recipe_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "ExecutorRecipeV1":
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "runtime_tree_id",
                "selected_route",
                "executor_semantics_id",
                "entrypoint_relative_path",
                "executor_configuration_id",
                "executor_recipe_id",
            },
            context="executor recipe",
        )
        if (
            document["schema"] != "acfqp.executor_recipe.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise Phase3ESealedExecutorV1Error("executor recipe schema mismatch")
        result = cls(
            document["runtime_tree_id"],
            document["selected_route"],
            document["executor_semantics_id"],
            document["entrypoint_relative_path"],
            document["executor_configuration_id"],
        )
        try:
            parse_content_id(document["executor_recipe_id"])
        except ValueError as error:
            raise Phase3ESealedExecutorV1Error(
                "executor recipe ID is invalid"
            ) from error
        if document["executor_recipe_id"] != result.executor_recipe_id:
            raise Phase3ESealedExecutorV1Error(
                "executor recipe content ID mismatch"
            )
        return result

    def validate_runtime(self, manifest: RuntimeTreeManifestV1) -> None:
        if manifest.runtime_tree_id != self.runtime_tree_id:
            raise Phase3ESealedExecutorV1Error(
                "executor recipe resolved a foreign runtime tree"
            )
        if self.entrypoint_relative_path not in {
            row.relative_path for row in manifest.entries
        }:
            raise Phase3ESealedExecutorV1Error(
                "executor recipe entrypoint is absent from its runtime tree"
            )


@dataclass(frozen=True, slots=True, order=True)
class TrustedConstructorSpecV1:
    """One closed semantics/route/entrypoint/exact-Python-type binding."""

    executor_semantics_id: str
    selected_route: RouteSelection
    entrypoint_relative_path: str
    constructor_module: str
    constructor_qualname: str

    def __post_init__(self) -> None:
        _nonempty_text(self.executor_semantics_id, "executor_semantics_id")
        object.__setattr__(
            self, "selected_route", RouteSelection(self.selected_route)
        )
        object.__setattr__(
            self,
            "entrypoint_relative_path",
            _relative_runtime_path(
                self.entrypoint_relative_path, "entrypoint_relative_path"
            ),
        )
        _nonempty_text(self.constructor_module, "constructor_module")
        _nonempty_text(self.constructor_qualname, "constructor_qualname")
        if "<locals>" in self.constructor_qualname:
            raise Phase3ESealedExecutorV1Error(
                "trusted constructors cannot be closures or local classes"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "executor_semantics_id": self.executor_semantics_id,
            "selected_route": self.selected_route.value,
            "entrypoint_relative_path": self.entrypoint_relative_path,
            "constructor_module": self.constructor_module,
            "constructor_qualname": self.constructor_qualname,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "TrustedConstructorSpecV1":
        require_exact_fields(
            document,
            {
                "executor_semantics_id",
                "selected_route",
                "entrypoint_relative_path",
                "constructor_module",
                "constructor_qualname",
            },
            context="trusted constructor spec",
        )
        return cls(
            document["executor_semantics_id"],
            document["selected_route"],
            document["entrypoint_relative_path"],
            document["constructor_module"],
            document["constructor_qualname"],
        )

    def resolve_exact_type(self) -> type[Any]:
        try:
            value: Any = importlib.import_module(self.constructor_module)
            for component in self.constructor_qualname.split("."):
                value = getattr(value, component)
        except (ImportError, AttributeError) as error:
            raise Phase3ESealedExecutorV1Error(
                "trusted constructor registry cannot resolve its exact type"
            ) from error
        if not isinstance(value, type):
            raise Phase3ESealedExecutorV1Error(
                "trusted constructor registry entry does not resolve to a type"
            )
        return value


_OFFICIAL_TRUSTED_CONSTRUCTOR_SPECS = tuple(
    sorted(
        (
            TrustedConstructorSpecV1(
                "phase3e-safe-chain-selected-local-executor-v1",
                RouteSelection.LOCAL,
                "acfqp/general_local_runtime.py",
                "acfqp.phase3e_local_adapter_v1",
                "SafeChainLocalPostFreezeConstructorV1",
            ),
            TrustedConstructorSpecV1(
                "phase3e-isolated-ground-fallback-executor-v1",
                RouteSelection.FALLBACK,
                "acfqp/phase3e_fallback_runtime_v1.py",
                "acfqp.phase3e_isolated_fallback_v1",
                "IsolatedFallbackPostFreezeConstructorV1",
            ),
            # A non-authoritative integrity probe used to audit the sealing
            # mechanism itself.  The main runner rejects its bytes result as
            # a planning result, so it cannot mint a plan certificate.
            TrustedConstructorSpecV1(
                "phase3e-runtime-integrity-probe-v1",
                RouteSelection.FALLBACK,
                "acfqp/worker.py",
                "acfqp.phase3e_sealed_executor_v1",
                "RuntimeIntegrityProbeConstructorV1",
            ),
        ),
        key=lambda row: row.executor_semantics_id,
    )
)


@dataclass(frozen=True, slots=True)
class TrustedConstructorRegistryV1:
    specs: tuple[TrustedConstructorSpecV1, ...] = _OFFICIAL_TRUSTED_CONSTRUCTOR_SPECS
    registry_key: str = "phase3e-exact-trusted-constructor-registry-v1"
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            self.specs != _OFFICIAL_TRUSTED_CONSTRUCTOR_SPECS
            or self.registry_key
            != "phase3e-exact-trusted-constructor-registry-v1"
            or self.schema_version != SCHEMA_VERSION
        ):
            raise Phase3ESealedExecutorV1Error(
                "trusted constructor registry is closed and cannot be extended"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.trusted_constructor_registry.v1",
            "schema_version": self.schema_version,
            "registry_key": self.registry_key,
            "specs": [row.to_dict() for row in self.specs],
        }

    @property
    def trusted_constructor_registry_id(self) -> str:
        return content_id(TRUSTED_CONSTRUCTOR_REGISTRY_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "trusted_constructor_registry_id": self.trusted_constructor_registry_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "TrustedConstructorRegistryV1":
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "registry_key",
                "specs",
                "trusted_constructor_registry_id",
            },
            context="trusted constructor registry",
        )
        if (
            document["schema"] != "acfqp.trusted_constructor_registry.v1"
            or type(document["specs"]) is not list
        ):
            raise Phase3ESealedExecutorV1Error(
                "trusted constructor registry schema mismatch"
            )
        result = cls(
            tuple(TrustedConstructorSpecV1.from_dict(row) for row in document["specs"]),
            document["registry_key"],
            document["schema_version"],
        )
        if (
            document["trusted_constructor_registry_id"]
            != result.trusted_constructor_registry_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "trusted constructor registry content ID mismatch"
            )
        return result

    def require_exact(
        self,
        recipe: ExecutorRecipeV1,
        constructor: object,
    ) -> TrustedConstructorSpecV1:
        matches = tuple(
            row
            for row in self.specs
            if row.executor_semantics_id == recipe.executor_semantics_id
        )
        if len(matches) != 1:
            raise Phase3ESealedExecutorV1Error(
                "executor semantics is absent from the closed constructor registry"
            )
        spec = matches[0]
        if (
            spec.selected_route is not recipe.selected_route
            or spec.entrypoint_relative_path != recipe.entrypoint_relative_path
        ):
            raise Phase3ESealedExecutorV1Error(
                "recipe route/entrypoint differs from its registered semantics"
            )
        expected_type = spec.resolve_exact_type()
        if type(constructor) is not expected_type:
            raise Phase3ESealedExecutorV1Error(
                "factory rejects arbitrary, subclassed, or closure constructors"
            )
        return spec


OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY = TrustedConstructorRegistryV1()


@dataclass(frozen=True, slots=True)
class PostFreezeConstructionGrantV1:
    """Unforgeable-in-profile capability passed only to a trusted constructor."""

    recipe: ExecutorRecipeV1
    runtime_tree: RuntimeTreeLeaseV1
    freeze_attestation: RouteDecisionFreezeAttestationV1
    _token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _CONSTRUCTION_GRANT_TOKEN:
            raise Phase3ESealedExecutorV1Error(
                "post-freeze construction grants may only be minted by the factory"
            )


class TrustedPostFreezeConstructorV1(Protocol):
    """Trusted runtime-only constructor registered for one recipe semantics."""

    def construct_after_freeze(
        self,
        grant: PostFreezeConstructionGrantV1,
    ) -> Callable[[Any, Any, Any], Any]: ...


@dataclass(frozen=True, slots=True)
class RuntimeIntegrityProbeConstructorV1:
    """Non-authoritative diagnostic constructor in the closed registry."""

    def construct_after_freeze(
        self,
        grant: PostFreezeConstructionGrantV1,
    ) -> Callable[[Any, Any, Any], bytes]:
        # Do not perform an unmetered fifth payload read.  The factory has
        # already checked the entrypoint's bytes on every registered pass.
        payload = grant.runtime_tree.runtime_tree_id.encode("ascii")

        def execute(_prepared: Any, _controller: Any, _recorder: Any) -> bytes:
            return payload

        return execute


_FACTORY_COUNTER_PATHS = tuple(
    sorted(runtime_factory_upper_values_v1().keys())
)


@dataclass(frozen=True, slots=True)
class SealedExecutorConstructionReceiptV1:
    """Content-addressed successful CAS/lease/constructor accounting seal."""

    runtime_tree_id: str
    executor_recipe_id: str
    runtime_manifest_cap_profile_id: str
    trusted_constructor_registry_id: str
    executor_semantics_id: str
    constructor_type: str
    selected_route: RouteSelection
    route_subject_id: str
    route_attempt_id: str
    decision_point_id: str
    route_decision_id: str
    route_decision_freeze_attestation_id: str
    file_count: int
    total_bytes: int
    manifest_document_bytes: int
    counter_values: tuple[tuple[str, int], ...]
    counter_record_ids: tuple[str, ...]
    factory_work_vector_id: str
    factory_comparison_vector_id: str
    postconstruction_access_event_log_id: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "runtime_tree_id",
            "executor_recipe_id",
            "runtime_manifest_cap_profile_id",
            "trusted_constructor_registry_id",
            "route_subject_id",
            "route_attempt_id",
            "decision_point_id",
            "route_decision_id",
            "route_decision_freeze_attestation_id",
            "factory_work_vector_id",
            "factory_comparison_vector_id",
            "postconstruction_access_event_log_id",
        ):
            try:
                parse_content_id(getattr(self, field_name))
            except ValueError as error:
                raise Phase3ESealedExecutorV1Error(
                    f"{field_name} must be a full content ID"
                ) from error
        _nonempty_text(self.executor_semantics_id, "executor_semantics_id")
        _nonempty_text(self.constructor_type, "constructor_type")
        object.__setattr__(
            self, "selected_route", RouteSelection(self.selected_route)
        )
        for field_name in ("file_count", "total_bytes", "manifest_document_bytes"):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise Phase3ESealedExecutorV1Error(
                    f"{field_name} must be a nonnegative exact integer"
                )
        if tuple(name for name, _ in self.counter_values) != _FACTORY_COUNTER_PATHS:
            raise Phase3ESealedExecutorV1Error(
                "construction receipt omits or repeats a factory counter"
            )
        if any(type(value) is not int or value < 0 for _, value in self.counter_values):
            raise Phase3ESealedExecutorV1Error(
                "construction receipt counter values must be nonnegative integers"
            )
        if (
            not self.counter_record_ids
            or tuple(sorted(self.counter_record_ids)) != self.counter_record_ids
            or len(set(self.counter_record_ids)) != len(self.counter_record_ids)
        ):
            raise Phase3ESealedExecutorV1Error(
                "construction counter-record IDs must be unique and sorted"
            )
        for record_id in self.counter_record_ids:
            try:
                parse_content_id(record_id)
            except ValueError as error:
                raise Phase3ESealedExecutorV1Error(
                    "construction counter-record ID is invalid"
                ) from error
        if self.schema_version != SCHEMA_VERSION:
            raise Phase3ESealedExecutorV1Error(
                "construction receipt schema version mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sealed_executor_construction_receipt.v1",
            "schema_version": self.schema_version,
            "runtime_tree_id": self.runtime_tree_id,
            "executor_recipe_id": self.executor_recipe_id,
            "runtime_manifest_cap_profile_id": self.runtime_manifest_cap_profile_id,
            "trusted_constructor_registry_id": self.trusted_constructor_registry_id,
            "executor_semantics_id": self.executor_semantics_id,
            "constructor_type": self.constructor_type,
            "selected_route": self.selected_route.value,
            "route_subject_id": self.route_subject_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "route_decision_id": self.route_decision_id,
            "route_decision_freeze_attestation_id": (
                self.route_decision_freeze_attestation_id
            ),
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "manifest_document_bytes": self.manifest_document_bytes,
            "counter_values": [
                {"name": name, "value": value}
                for name, value in self.counter_values
            ],
            "counter_record_ids": list(self.counter_record_ids),
            "factory_work_vector_id": self.factory_work_vector_id,
            "factory_comparison_vector_id": self.factory_comparison_vector_id,
            "postconstruction_access_event_log_id": (
                self.postconstruction_access_event_log_id
            ),
        }

    @property
    def sealed_executor_construction_receipt_id(self) -> str:
        return content_id(
            SEALED_EXECUTOR_CONSTRUCTION_RECEIPT_DOMAIN, self._payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "sealed_executor_construction_receipt_id": (
                self.sealed_executor_construction_receipt_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "SealedExecutorConstructionReceiptV1":
        fields = {
            "schema", "schema_version", "runtime_tree_id", "executor_recipe_id",
            "runtime_manifest_cap_profile_id", "trusted_constructor_registry_id",
            "executor_semantics_id", "constructor_type", "selected_route",
            "route_subject_id", "route_attempt_id", "decision_point_id",
            "route_decision_id", "route_decision_freeze_attestation_id",
            "file_count", "total_bytes", "manifest_document_bytes",
            "counter_values", "counter_record_ids", "factory_work_vector_id",
            "factory_comparison_vector_id", "postconstruction_access_event_log_id",
            "sealed_executor_construction_receipt_id",
        }
        require_exact_fields(document, fields, context="construction receipt")
        if (
            document["schema"] != "acfqp.sealed_executor_construction_receipt.v1"
            or type(document["counter_values"]) is not list
            or type(document["counter_record_ids"]) is not list
        ):
            raise Phase3ESealedExecutorV1Error("construction receipt schema mismatch")
        counters: list[tuple[str, int]] = []
        for row in document["counter_values"]:
            require_exact_fields(
                row, {"name", "value"}, context="construction counter row"
            )
            counters.append((row["name"], row["value"]))
        result = cls(
            document["runtime_tree_id"], document["executor_recipe_id"],
            document["runtime_manifest_cap_profile_id"],
            document["trusted_constructor_registry_id"],
            document["executor_semantics_id"], document["constructor_type"],
            document["selected_route"], document["route_subject_id"],
            document["route_attempt_id"], document["decision_point_id"],
            document["route_decision_id"],
            document["route_decision_freeze_attestation_id"],
            document["file_count"], document["total_bytes"],
            document["manifest_document_bytes"], tuple(counters),
            tuple(document["counter_record_ids"]),
            document["factory_work_vector_id"],
            document["factory_comparison_vector_id"],
            document["postconstruction_access_event_log_id"],
            document["schema_version"],
        )
        if (
            document["sealed_executor_construction_receipt_id"]
            != result.sealed_executor_construction_receipt_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "construction receipt content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class SealedExecutorConstructionAccountingV1:
    """Runner-consumable receipt plus replayable exact factory work."""

    receipt: SealedExecutorConstructionReceiptV1
    recorded_work: RecordedWorkV1

    def __post_init__(self) -> None:
        verify_recorded_work_v1(
            self.recorded_work,
            expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        )
        vector = self.recorded_work.work_vector
        comparison = self.recorded_work.comparison_vector
        expected_kind = (
            RouteKindEnum.LOCAL_ATTEMPT
            if self.receipt.selected_route is RouteSelection.LOCAL
            else RouteKindEnum.DIRECT_FALLBACK
        )
        if (
            vector.subject_id != self.receipt.route_subject_id
            or vector.route_kind is not expected_kind
            or
            self.receipt.factory_work_vector_id != vector.work_vector_id
            or self.receipt.factory_comparison_vector_id
            != comparison.comparison_vector_id
            or self.receipt.counter_record_ids
            != tuple(sorted(row.record_id for row in vector.records))
            or dict(self.receipt.counter_values)
            != {path: vector.value(path) for path in _FACTORY_COUNTER_PATHS}
        ):
            raise Phase3ESealedExecutorV1Error(
                "construction receipt differs from its exact WorkVector"
            )
        expected = {
            "common.hash_invocations": (
                1 + RUNTIME_FACTORY_TREE_PASSES * self.receipt.file_count
            ),
            "common.integrity_checks": (
                RUNTIME_FACTORY_INTEGRITY_BASE_UPPER
                + RUNTIME_FACTORY_TREE_PASSES * self.receipt.file_count
            ),
            "common.protocol_checks": 10,
            "control.cap_checks": RUNTIME_FACTORY_CAP_CHECKS,
            "io.read_bytes": (
                self.receipt.manifest_document_bytes
                + RUNTIME_FACTORY_TREE_PASSES * self.receipt.total_bytes
            ),
            "io.staged_bytes": self.receipt.total_bytes,
            "io.output_bytes": 0,
            "io.mounted_bytes_peak": self.receipt.total_bytes,
            "memory.working_bytes_peak": RUNTIME_FACTORY_WORKING_BYTES_CAP,
        }
        if dict(self.receipt.counter_values) != expected:
            raise Phase3ESealedExecutorV1Error(
                "construction counters do not satisfy the exact manifest formula"
            )


@dataclass(frozen=True, slots=True)
class SealedExecutorFailureEvidenceV1:
    """Typed identity chain attached to a failed sealed construction."""

    runtime_tree_id: str
    executor_recipe_id: str
    runtime_manifest_cap_profile_id: str
    trusted_constructor_registry_id: str
    route_attempt_id: str
    decision_point_id: str
    route_decision_freeze_attestation_id: str
    route_subject_id: str
    failure_stage: str
    partial_factory_work_vector_id: str
    delegate_partial_work_vector_id: str | TypedNotApplicable
    merged_partial_work_vector_id: str
    failure_merge_proof_id: str
    postfailure_access_event_log_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "runtime_tree_id",
            "executor_recipe_id",
            "runtime_manifest_cap_profile_id",
            "trusted_constructor_registry_id",
            "route_attempt_id",
            "decision_point_id",
            "route_decision_freeze_attestation_id",
            "route_subject_id",
            "partial_factory_work_vector_id",
            "merged_partial_work_vector_id",
            "failure_merge_proof_id",
            "postfailure_access_event_log_id",
        ):
            try:
                parse_content_id(getattr(self, field_name))
            except ValueError as error:
                raise Phase3ESealedExecutorV1Error(
                    f"{field_name} must be a full content ID"
                ) from error
        _nonempty_text(self.failure_stage, "failure_stage")
        if self.failure_stage not in {
            "FROZEN_BINDING",
            "RUNTIME_CAS_RESOLVE",
            "PRIVATE_LEASE",
            "TRUSTED_CONSTRUCTOR",
            "SELECTED_EXECUTOR",
        }:
            raise Phase3ESealedExecutorV1Error(
                "sealed executor failure stage is not registered"
            )
        if (
            self.runtime_manifest_cap_profile_id
            != OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE.runtime_manifest_cap_profile_id
            or self.trusted_constructor_registry_id
            != OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY.trusted_constructor_registry_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "sealed executor failure uses foreign cap or constructor authority"
            )
        if type(self.delegate_partial_work_vector_id) is not TypedNotApplicable:
            try:
                parse_content_id(self.delegate_partial_work_vector_id)
            except ValueError as error:
                raise Phase3ESealedExecutorV1Error(
                    "delegate_partial_work_vector_id must be a full content ID or typed null"
                ) from error

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sealed_executor_failure_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "runtime_tree_id": self.runtime_tree_id,
            "executor_recipe_id": self.executor_recipe_id,
            "runtime_manifest_cap_profile_id": self.runtime_manifest_cap_profile_id,
            "trusted_constructor_registry_id": self.trusted_constructor_registry_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "route_decision_freeze_attestation_id": (
                self.route_decision_freeze_attestation_id
            ),
            "route_subject_id": self.route_subject_id,
            "failure_stage": self.failure_stage,
            "partial_factory_work_vector_id": self.partial_factory_work_vector_id,
            "delegate_partial_work_vector_id": (
                self.delegate_partial_work_vector_id.to_dict()
                if type(self.delegate_partial_work_vector_id)
                is TypedNotApplicable
                else self.delegate_partial_work_vector_id
            ),
            "merged_partial_work_vector_id": self.merged_partial_work_vector_id,
            "failure_merge_proof_id": self.failure_merge_proof_id,
            "postfailure_access_event_log_id": self.postfailure_access_event_log_id,
        }

    @property
    def sealed_executor_failure_evidence_id(self) -> str:
        return content_id(SEALED_EXECUTOR_FAILURE_EVIDENCE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "sealed_executor_failure_evidence_id": (
                self.sealed_executor_failure_evidence_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "SealedExecutorFailureEvidenceV1":
        require_exact_fields(
            document,
            {
                "schema", "schema_version", "runtime_tree_id",
                "executor_recipe_id", "runtime_manifest_cap_profile_id",
                "trusted_constructor_registry_id", "route_attempt_id",
                "decision_point_id", "route_decision_freeze_attestation_id",
                "route_subject_id", "failure_stage",
                "partial_factory_work_vector_id",
                "delegate_partial_work_vector_id",
                "merged_partial_work_vector_id",
                "failure_merge_proof_id", "postfailure_access_event_log_id",
                "sealed_executor_failure_evidence_id",
            },
            context="sealed executor failure evidence",
        )
        if (
            document["schema"] != "acfqp.sealed_executor_failure_evidence.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise Phase3ESealedExecutorV1Error(
                "sealed executor failure evidence schema mismatch"
            )
        result = cls(
            document["runtime_tree_id"], document["executor_recipe_id"],
            document["runtime_manifest_cap_profile_id"],
            document["trusted_constructor_registry_id"],
            document["route_attempt_id"], document["decision_point_id"],
            document["route_decision_freeze_attestation_id"],
            document["route_subject_id"], document["failure_stage"],
            document["partial_factory_work_vector_id"],
            (
                TypedNotApplicable.from_dict(
                    document["delegate_partial_work_vector_id"]
                )
                if type(document["delegate_partial_work_vector_id"]) is dict
                else document["delegate_partial_work_vector_id"]
            ),
            document["merged_partial_work_vector_id"],
            document["failure_merge_proof_id"],
            document["postfailure_access_event_log_id"],
        )
        if (
            document["sealed_executor_failure_evidence_id"]
            != result.sealed_executor_failure_evidence_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "sealed executor failure evidence content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class SealedExecutorFailureMergeProofV1:
    """Exact replay seal for normalized factory(+delegate) failure work."""

    route_subject_id: str
    route_kind: RouteKindEnum
    factory_partial_work_vector_id: str
    factory_partial_comparison_vector_id: str
    factory_partial_projection_proof_id: str
    delegate_partial_work_vector_id: str | TypedNotApplicable
    delegate_partial_comparison_vector_id: str | TypedNotApplicable
    delegate_partial_projection_proof_id: str | TypedNotApplicable
    merged_partial_work_vector_id: str
    merged_partial_comparison_vector_id: str
    merged_partial_projection_proof_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "route_kind", RouteKindEnum(self.route_kind))
        if self.route_kind not in {
            RouteKindEnum.LOCAL_ATTEMPT,
            RouteKindEnum.DIRECT_FALLBACK,
        }:
            raise Phase3ESealedExecutorV1Error(
                "sealed failure merge requires a marginal route"
            )
        for field_name in (
            "route_subject_id",
            "factory_partial_work_vector_id",
            "factory_partial_comparison_vector_id",
            "factory_partial_projection_proof_id",
            "merged_partial_work_vector_id",
            "merged_partial_comparison_vector_id",
            "merged_partial_projection_proof_id",
        ):
            try:
                parse_content_id(getattr(self, field_name))
            except ValueError as error:
                raise Phase3ESealedExecutorV1Error(
                    f"{field_name} must be a full content ID"
                ) from error
        delegate_refs = (
            self.delegate_partial_work_vector_id,
            self.delegate_partial_comparison_vector_id,
            self.delegate_partial_projection_proof_id,
        )
        typed_nulls = tuple(type(value) is TypedNotApplicable for value in delegate_refs)
        if any(typed_nulls) and not all(typed_nulls):
            raise Phase3ESealedExecutorV1Error(
                "sealed failure delegate proof references must be all IDs or all typed nulls"
            )
        if not any(typed_nulls):
            for value in delegate_refs:
                try:
                    parse_content_id(value)  # type: ignore[arg-type]
                except ValueError as error:
                    raise Phase3ESealedExecutorV1Error(
                        "sealed failure delegate proof reference is invalid"
                    ) from error

    def _payload(self) -> dict[str, Any]:
        def encode(value: str | TypedNotApplicable) -> str | dict[str, str]:
            return value.to_dict() if type(value) is TypedNotApplicable else value

        return {
            "schema": "acfqp.sealed_executor_failure_merge_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "route_subject_id": self.route_subject_id,
            "route_kind": self.route_kind.value,
            "factory_partial_work_vector_id": self.factory_partial_work_vector_id,
            "factory_partial_comparison_vector_id": self.factory_partial_comparison_vector_id,
            "factory_partial_projection_proof_id": self.factory_partial_projection_proof_id,
            "delegate_partial_work_vector_id": encode(self.delegate_partial_work_vector_id),
            "delegate_partial_comparison_vector_id": encode(self.delegate_partial_comparison_vector_id),
            "delegate_partial_projection_proof_id": encode(self.delegate_partial_projection_proof_id),
            "merged_partial_work_vector_id": self.merged_partial_work_vector_id,
            "merged_partial_comparison_vector_id": self.merged_partial_comparison_vector_id,
            "merged_partial_projection_proof_id": self.merged_partial_projection_proof_id,
        }

    @property
    def sealed_executor_failure_merge_proof_id(self) -> str:
        return content_id(SEALED_EXECUTOR_FAILURE_MERGE_PROOF_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "sealed_executor_failure_merge_proof_id": (
                self.sealed_executor_failure_merge_proof_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "SealedExecutorFailureMergeProofV1":
        fields = {
            "schema", "schema_version", "route_subject_id", "route_kind",
            "factory_partial_work_vector_id",
            "factory_partial_comparison_vector_id",
            "factory_partial_projection_proof_id",
            "delegate_partial_work_vector_id",
            "delegate_partial_comparison_vector_id",
            "delegate_partial_projection_proof_id",
            "merged_partial_work_vector_id",
            "merged_partial_comparison_vector_id",
            "merged_partial_projection_proof_id",
            "sealed_executor_failure_merge_proof_id",
        }
        require_exact_fields(
            document, fields, context="sealed executor failure merge proof"
        )
        if (
            document["schema"]
            != "acfqp.sealed_executor_failure_merge_proof.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise Phase3ESealedExecutorV1Error(
                "sealed executor failure merge proof schema mismatch"
            )

        def decode(value: object) -> str | TypedNotApplicable:
            if type(value) is dict:
                return TypedNotApplicable.from_dict(value)
            return value  # type: ignore[return-value]

        result = cls(
            document["route_subject_id"], document["route_kind"],
            document["factory_partial_work_vector_id"],
            document["factory_partial_comparison_vector_id"],
            document["factory_partial_projection_proof_id"],
            decode(document["delegate_partial_work_vector_id"]),
            decode(document["delegate_partial_comparison_vector_id"]),
            decode(document["delegate_partial_projection_proof_id"]),
            document["merged_partial_work_vector_id"],
            document["merged_partial_comparison_vector_id"],
            document["merged_partial_projection_proof_id"],
        )
        if (
            document["sealed_executor_failure_merge_proof_id"]
            != result.sealed_executor_failure_merge_proof_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "sealed executor failure merge proof content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class SealedExecutorExecutionMergeProofV1:
    """Exact two-source proof for factory + delegate execution work."""

    route_subject_id: str
    route_kind: RouteKindEnum
    construction_receipt_id: str
    factory_work_vector_id: str
    factory_comparison_vector_id: str
    factory_projection_proof_id: str
    delegate_work_vector_id: str
    delegate_comparison_vector_id: str
    delegate_projection_proof_id: str
    merged_work_vector_id: str
    merged_comparison_vector_id: str
    merged_projection_proof_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "route_subject_id",
            "construction_receipt_id",
            "factory_work_vector_id",
            "factory_comparison_vector_id",
            "factory_projection_proof_id",
            "delegate_work_vector_id",
            "delegate_comparison_vector_id",
            "delegate_projection_proof_id",
            "merged_work_vector_id",
            "merged_comparison_vector_id",
            "merged_projection_proof_id",
        ):
            try:
                parse_content_id(getattr(self, field_name))
            except ValueError as error:
                raise Phase3ESealedExecutorV1Error(
                    f"{field_name} must be a full content ID"
                ) from error
        object.__setattr__(self, "route_kind", RouteKindEnum(self.route_kind))
        if self.route_kind not in {
            RouteKindEnum.LOCAL_ATTEMPT,
            RouteKindEnum.DIRECT_FALLBACK,
        }:
            raise Phase3ESealedExecutorV1Error(
                "sealed execution merge requires a marginal route"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sealed_executor_execution_merge_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "route_subject_id": self.route_subject_id,
            "route_kind": self.route_kind.value,
            "construction_receipt_id": self.construction_receipt_id,
            "factory_work_vector_id": self.factory_work_vector_id,
            "factory_comparison_vector_id": self.factory_comparison_vector_id,
            "factory_projection_proof_id": self.factory_projection_proof_id,
            "delegate_work_vector_id": self.delegate_work_vector_id,
            "delegate_comparison_vector_id": self.delegate_comparison_vector_id,
            "delegate_projection_proof_id": self.delegate_projection_proof_id,
            "merged_work_vector_id": self.merged_work_vector_id,
            "merged_comparison_vector_id": self.merged_comparison_vector_id,
            "merged_projection_proof_id": self.merged_projection_proof_id,
        }

    @property
    def sealed_executor_execution_merge_proof_id(self) -> str:
        return content_id(
            SEALED_EXECUTOR_EXECUTION_MERGE_PROOF_DOMAIN, self._payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "sealed_executor_execution_merge_proof_id": (
                self.sealed_executor_execution_merge_proof_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "SealedExecutorExecutionMergeProofV1":
        payload_fields = {
            "schema", "schema_version", "route_subject_id", "route_kind",
            "construction_receipt_id", "factory_work_vector_id",
            "factory_comparison_vector_id", "factory_projection_proof_id",
            "delegate_work_vector_id", "delegate_comparison_vector_id",
            "delegate_projection_proof_id", "merged_work_vector_id",
            "merged_comparison_vector_id", "merged_projection_proof_id",
            "sealed_executor_execution_merge_proof_id",
        }
        require_exact_fields(
            document, payload_fields, context="sealed execution merge proof"
        )
        if (
            document["schema"]
            != "acfqp.sealed_executor_execution_merge_proof.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise Phase3ESealedExecutorV1Error(
                "sealed execution merge proof schema mismatch"
            )
        result = cls(
            document["route_subject_id"], document["route_kind"],
            document["construction_receipt_id"],
            document["factory_work_vector_id"],
            document["factory_comparison_vector_id"],
            document["factory_projection_proof_id"],
            document["delegate_work_vector_id"],
            document["delegate_comparison_vector_id"],
            document["delegate_projection_proof_id"],
            document["merged_work_vector_id"],
            document["merged_comparison_vector_id"],
            document["merged_projection_proof_id"],
        )
        if (
            document["sealed_executor_execution_merge_proof_id"]
            != result.sealed_executor_execution_merge_proof_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "sealed execution merge proof content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class MergedSealedRouteExecutionWorkV1:
    recorded_work: RecordedWorkV1
    merge_proof: SealedExecutorExecutionMergeProofV1


@dataclass(frozen=True, slots=True)
class MergedSealedRouteFailureWorkV1:
    recorded_work: RecordedWorkV1
    merge_proof: SealedExecutorFailureMergeProofV1


def _merge_route_execution_work_v1(
    *,
    factory_work: RecordedWorkV1,
    delegate_work: RecordedWorkV1,
    recorder_id: str,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
) -> RecordedWorkV1:
    """Reducer-merge two exact vectors without inventing missing leaves."""

    for recorded in (factory_work, delegate_work):
        verify_recorded_work_v1(
            recorded,
            expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            registry=registry,
            comparison_profile=comparison_profile,
        )
    if (
        factory_work.work_vector.subject_id
        != delegate_work.work_vector.subject_id
        or factory_work.work_vector.route_kind
        is not delegate_work.work_vector.route_kind
    ):
        raise Phase3ESealedExecutorV1Error(
            "factory and delegate execution work use different route subjects"
        )
    values: dict[str, int] = {}
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        left = factory_work.work_vector.value(path)
        right = delegate_work.work_vector.value(path)
        if path in {"io.mounted_bytes_peak", "memory.working_bytes_peak"}:
            # The route-private runtime lease/factory remains live for the
            # complete delegate call.  Mounted payload and the two process-
            # tree working capacities can therefore coexist and must add.
            values[path] = left + right
        else:
            values[path] = (
                left + right
                if leaf.reducer is ReducerEnum.SUM
                else max(left, right)
            )
    vector = registry.materialize(
        subject_id=factory_work.work_vector.subject_id,
        route_kind=factory_work.work_vector.route_kind,
        records=explicit_records_v1(
            registry,
            values,
            recorder_id=recorder_id,
        ),
    )
    return derive_recorded_work_v1(
        vector,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=comparison_profile,
    )


def merge_sealed_factory_execution_work_v1(
    *,
    factory_accounting: SealedExecutorConstructionAccountingV1,
    delegate_work: RecordedWorkV1,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> MergedSealedRouteExecutionWorkV1:
    """Reducer-merge both selected-route sources without subject laundering."""

    if (
        type(factory_accounting) is not SealedExecutorConstructionAccountingV1
        or type(delegate_work) is not RecordedWorkV1
    ):
        raise Phase3ESealedExecutorV1Error(
            "sealed execution merge requires typed factory/delegate work"
        )
    trusted = registry or official_counter_registry_v1()
    profile = comparison_profile or official_comparison_profile_v1(trusted)
    trusted.validate_official_catalogue()
    profile.validate(trusted)
    factory = factory_accounting.recorded_work
    subject = factory_accounting.receipt.route_subject_id
    route_kind = factory.work_vector.route_kind
    if (
        factory.work_vector.subject_id != subject
        or delegate_work.work_vector.subject_id != subject
        or delegate_work.work_vector.route_kind is not route_kind
    ):
        raise Phase3ESealedExecutorV1Error(
            "factory and delegate execution work use different route subjects"
        )
    merged = _merge_route_execution_work_v1(
        factory_work=factory,
        delegate_work=delegate_work,
        recorder_id="phase3e-sealed-execution-merge-v1",
        registry=trusted,
        comparison_profile=profile,
    )
    proof = SealedExecutorExecutionMergeProofV1(
        subject,
        route_kind,
        factory_accounting.receipt.sealed_executor_construction_receipt_id,
        factory.work_vector.work_vector_id,
        factory.comparison_vector.comparison_vector_id,
        factory.actual_projection_proof.actual_projection_proof_id,
        delegate_work.work_vector.work_vector_id,
        delegate_work.comparison_vector.comparison_vector_id,
        delegate_work.actual_projection_proof.actual_projection_proof_id,
        merged.work_vector.work_vector_id,
        merged.comparison_vector.comparison_vector_id,
        merged.actual_projection_proof.actual_projection_proof_id,
    )
    return MergedSealedRouteExecutionWorkV1(merged, proof)


def merge_sealed_factory_failure_work_v1(
    *,
    factory_partial_work: RecordedWorkV1,
    delegate_partial_work: RecordedWorkV1 | None,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> MergedSealedRouteFailureWorkV1:
    """Normalize and seal every observed selected-route failure component."""

    if type(factory_partial_work) is not RecordedWorkV1 or (
        delegate_partial_work is not None
        and type(delegate_partial_work) is not RecordedWorkV1
    ):
        raise Phase3ESealedExecutorV1Error(
            "sealed failure merge requires exact RecordedWorkV1 inputs"
        )
    trusted = registry or official_counter_registry_v1()
    profile = comparison_profile or official_comparison_profile_v1(trusted)
    if type(trusted) is not CounterRegistryV1 or type(profile) is not ComparisonProfileV1:
        raise Phase3ESealedExecutorV1Error(
            "sealed failure merge requires exact accounting authorities"
        )
    trusted.validate_official_catalogue()
    profile.validate(trusted)
    verify_recorded_work_v1(
        factory_partial_work,
        expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=trusted,
        comparison_profile=profile,
    )
    source = factory_partial_work
    if delegate_partial_work is not None:
        source = _merge_route_execution_work_v1(
            factory_work=factory_partial_work,
            delegate_work=delegate_partial_work,
            recorder_id="phase3e-sealed-failed-execution-merge-v1",
            registry=trusted,
            comparison_profile=profile,
        )
    merged = derive_failed_recorded_work_v1(
        source,
        registry=trusted,
        comparison_profile=profile,
    )
    typed_null = TypedNotApplicable("delegate partial work was not available")
    proof = SealedExecutorFailureMergeProofV1(
        factory_partial_work.work_vector.subject_id,
        factory_partial_work.work_vector.route_kind,
        factory_partial_work.work_vector.work_vector_id,
        factory_partial_work.comparison_vector.comparison_vector_id,
        factory_partial_work.actual_projection_proof.actual_projection_proof_id,
        (
            typed_null
            if delegate_partial_work is None
            else delegate_partial_work.work_vector.work_vector_id
        ),
        (
            typed_null
            if delegate_partial_work is None
            else delegate_partial_work.comparison_vector.comparison_vector_id
        ),
        (
            typed_null
            if delegate_partial_work is None
            else delegate_partial_work.actual_projection_proof.actual_projection_proof_id
        ),
        merged.work_vector.work_vector_id,
        merged.comparison_vector.comparison_vector_id,
        merged.actual_projection_proof.actual_projection_proof_id,
    )
    return MergedSealedRouteFailureWorkV1(merged, proof)


def verify_sealed_factory_failure_merge_v1(
    merged: MergedSealedRouteFailureWorkV1,
    *,
    factory_partial_work: RecordedWorkV1,
    delegate_partial_work: RecordedWorkV1 | None,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> MergedSealedRouteFailureWorkV1:
    if type(merged) is not MergedSealedRouteFailureWorkV1:
        raise Phase3ESealedExecutorV1Error(
            "sealed failure replay requires a typed merged failure"
        )
    replayed = merge_sealed_factory_failure_work_v1(
        factory_partial_work=factory_partial_work,
        delegate_partial_work=delegate_partial_work,
        registry=registry,
        comparison_profile=comparison_profile,
    )
    if replayed != merged:
        raise Phase3ESealedExecutorV1Error(
            "sealed factory/delegate failure merge proof does not replay"
        )
    return merged


def verify_sealed_factory_execution_merge_v1(
    claimed: MergedSealedRouteExecutionWorkV1,
    *,
    factory_accounting: SealedExecutorConstructionAccountingV1,
    delegate_work: RecordedWorkV1,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> MergedSealedRouteExecutionWorkV1:
    replayed = merge_sealed_factory_execution_work_v1(
        factory_accounting=factory_accounting,
        delegate_work=delegate_work,
        registry=registry,
        comparison_profile=comparison_profile,
    )
    if claimed != replayed:
        raise Phase3ESealedExecutorV1Error(
            "sealed factory/delegate execution merge does not replay"
        )
    return replayed


@dataclass(slots=True)
class _InvocationGuardV1:
    lock: threading.Lock = field(default_factory=threading.Lock)
    invoked: bool = False
    construction_accounting: SealedExecutorConstructionAccountingV1 | None = None
    partial_work: RecordedWorkV1 | None = None
    failure_evidence: SealedExecutorFailureEvidenceV1 | None = None

    def consume(self) -> None:
        with self.lock:
            if self.invoked:
                raise Phase3ESealedExecutorV1Error(
                    "sealed executor factory is single-use"
                )
            self.invoked = True

    def close_success(
        self, value: SealedExecutorConstructionAccountingV1
    ) -> None:
        with self.lock:
            if self.construction_accounting is not None or self.partial_work is not None:
                raise Phase3ESealedExecutorV1Error(
                    "sealed executor accounting was already finalized"
                )
            self.construction_accounting = value

    def close_failure(
        self,
        partial: RecordedWorkV1,
        evidence: SealedExecutorFailureEvidenceV1,
    ) -> None:
        with self.lock:
            if self.construction_accounting is not None or self.partial_work is not None:
                raise Phase3ESealedExecutorV1Error(
                    "sealed executor accounting was already finalized"
                )
            self.partial_work = partial
            self.failure_evidence = evidence

    def record_delegate_failure(
        self, evidence: SealedExecutorFailureEvidenceV1
    ) -> None:
        with self.lock:
            if self.construction_accounting is None or self.failure_evidence is not None:
                raise Phase3ESealedExecutorV1Error(
                    "delegate failure does not follow one finalized construction"
                )
            self.failure_evidence = evidence


def _selected_route_subject_id_v1(
    prepared: Any,
    recipe: ExecutorRecipeV1,
) -> str:
    context = getattr(prepared, "context", None)
    if recipe.selected_route is RouteSelection.FALLBACK:
        try:
            return parse_content_id(getattr(context, "route_attempt_id", None))
        except ValueError as error:
            raise Phase3ESealedExecutorV1Error(
                "fallback factory lacks its route-attempt subject"
            ) from error
    try:
        from acfqp.semantic_verification_v1 import (
            SemanticRole,
            require_semantic_verification_result_v1,
        )

        result = require_semantic_verification_result_v1(
            prepared.authorization.selected_upper_result,
            SemanticRole.ROUTE_UPPER,
        )
        transaction_id = result.artifact.transaction_id
        return parse_content_id(transaction_id)
    except (AttributeError, TypeError, ValueError) as error:
        raise Phase3ESealedExecutorV1Error(
            "local factory lacks its authoritative transaction subject"
        ) from error


@dataclass(frozen=True, slots=True)
class SealedPostFreezeExecutorFactoryV1:
    """Executor-shaped factory whose delegate cannot exist before freeze."""

    recipe: ExecutorRecipeV1
    runtime_cas: RuntimeTreeCASV1
    constructor: TrustedPostFreezeConstructorV1 = field(
        repr=False,
        compare=False,
    )
    registry: CounterRegistryV1 = field(
        default_factory=official_counter_registry_v1,
        repr=False,
        compare=False,
        kw_only=True,
    )
    comparison_profile: ComparisonProfileV1 | None = field(
        default=None,
        repr=False,
        compare=False,
        kw_only=True,
    )
    runtime_cap_profile: RuntimeManifestCapProfileV1 = field(
        default_factory=RuntimeManifestCapProfileV1,
        repr=False,
        compare=False,
        kw_only=True,
    )
    _guard: _InvocationGuardV1 = field(
        default_factory=_InvocationGuardV1,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if type(self.recipe) is not ExecutorRecipeV1:
            raise Phase3ESealedExecutorV1Error(
                "sealed executor factory requires a typed recipe"
            )
        if type(self.runtime_cas) is not RuntimeTreeCASV1:
            raise Phase3ESealedExecutorV1Error(
                "sealed executor factory requires a typed runtime CAS"
            )
        if type(self.registry) is not CounterRegistryV1:
            raise Phase3ESealedExecutorV1Error(
                "sealed executor factory requires the typed counter registry"
            )
        self.registry.validate_official_catalogue()
        official_registry = official_counter_registry_v1()
        if (
            self.registry != official_registry
            or self.registry.registry_id != official_registry.registry_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "sealed executor factory requires the exact official counter registry"
            )
        profile = self.comparison_profile or official_comparison_profile_v1(
            self.registry
        )
        if type(profile) is not ComparisonProfileV1:
            raise Phase3ESealedExecutorV1Error(
                "sealed executor factory requires the exact comparison profile type"
            )
        profile.validate(self.registry)
        official_profile = official_comparison_profile_v1(official_registry)
        if (
            profile != official_profile
            or profile.comparison_profile_id
            != official_profile.comparison_profile_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "sealed executor factory requires the exact official comparison profile"
            )
        object.__setattr__(self, "comparison_profile", profile)
        if type(self.runtime_cap_profile) is not RuntimeManifestCapProfileV1:
            raise Phase3ESealedExecutorV1Error(
                "sealed executor factory requires a runtime cap profile"
            )
        RuntimeManifestCapProfileV1.from_dict(self.runtime_cap_profile.to_dict())
        # This is deliberately exact type equality, not Protocol duck typing.
        # An attacker cannot register a local class or wrap the trusted
        # constructor in a closure to broaden post-freeze behavior.
        OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY.require_exact(
            self.recipe, self.constructor
        )

    @property
    def construction_accounting(
        self,
    ) -> SealedExecutorConstructionAccountingV1 | None:
        return self._guard.construction_accounting

    @property
    def partial_factory_work(self) -> RecordedWorkV1 | None:
        return self._guard.partial_work

    @property
    def failure_evidence(self) -> SealedExecutorFailureEvidenceV1 | None:
        return self._guard.failure_evidence

    @property
    def deferred_route_verifier(self) -> Callable[..., tuple[object, ...]] | None:
        """Return only the exact registered constructor's semantic dispatcher."""

        value = getattr(self.constructor, "deferred_route_verifier_v1", None)
        return value if callable(value) else None

    @property
    def deferred_route_verifier_step(self) -> Callable[..., object] | None:
        value = getattr(
            self.constructor, "deferred_route_verifier_step_v1", None
        )
        return value if callable(value) else None

    def validate_preselection_binding_v1(
        self, prepared: Any, selected_upper: Any
    ) -> None:
        """Validate the complete inert recipe/upper chain before route freeze."""

        OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY.require_exact(
            self.recipe, self.constructor
        )
        if (
            getattr(prepared, "runtime_tree_id", None)
            != self.recipe.runtime_tree_id
            or getattr(prepared, "executor_recipe_id", None)
            != self.recipe.executor_recipe_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "prepared runtime bindings differ from the sealed recipe"
            )
        if type(self.constructor) is RuntimeIntegrityProbeConstructorV1:
            return
        runtime = getattr(
            self.constructor, "runtime_factory_cardinality_v1", None
        )
        configuration_id = getattr(
            self.constructor, "executor_configuration_id_v1", None
        )
        selected_upper_id = getattr(
            self.constructor, "selected_upper_id_v1", None
        )
        cardinality_id = getattr(
            self.constructor, "selected_cardinality_evidence_id_v1", None
        )
        source_ids = getattr(
            self.constructor,
            "selected_cardinality_source_artifact_ids_v1",
            None,
        )
        if (
            type(runtime) is not RuntimeFactoryCardinalityV1
            or runtime.runtime_tree_id != self.recipe.runtime_tree_id
            or runtime.runtime_manifest_cap_profile_id
            != self.runtime_cap_profile.runtime_manifest_cap_profile_id
            or configuration_id != self.recipe.executor_configuration_id
            or selected_upper_id
            != getattr(selected_upper, "route_upper_bound_envelope_id", None)
            or cardinality_id
            != getattr(selected_upper, "cardinality_evidence_id", None)
            or type(source_ids) is not tuple
            or runtime.runtime_factory_cardinality_id not in source_ids
        ):
            raise Phase3ESealedExecutorV1Error(
                "sealed recipe/constructor/runtime cardinality/selected upper "
                "identity chain is inconsistent"
            )

    def _validate_frozen_binding(
        self,
        prepared: Any,
        controller: Any,
        meter: _FactoryWorkMeterV1,
    ) -> RouteDecisionFreezeAttestationV1:
        meter.protocol()
        if type(controller) is not FailClosedAccessController:
            raise Phase3ESealedExecutorV1Error(
                "sealed construction requires the fail-closed access controller"
            )
        freeze = getattr(controller, "freeze_attestation", None)
        meter.protocol()
        if type(freeze) is not RouteDecisionFreezeAttestationV1:
            raise Phase3ESealedExecutorV1Error(
                "executor construction is forbidden before a typed route freeze"
            )
        meter.protocol()
        if freeze.selected_route is not self.recipe.selected_route:
            raise Phase3ESealedExecutorV1Error(
                "executor recipe route differs from the frozen decision"
            )
        context = getattr(prepared, "context", None)
        point = getattr(prepared, "decision_point", None)
        meter.protocol()
        if getattr(context, "route_attempt_id", None) != freeze.route_attempt_id:
            raise Phase3ESealedExecutorV1Error(
                "executor factory freeze belongs to another route attempt"
            )
        meter.protocol()
        if getattr(point, "decision_point_id", None) != freeze.decision_point_id:
            raise Phase3ESealedExecutorV1Error(
                "executor factory freeze belongs to another prepared decision"
            )
        meter.protocol()
        if getattr(prepared, "runtime_tree_id", None) != self.recipe.runtime_tree_id:
            raise Phase3ESealedExecutorV1Error(
                "prepared run binds a foreign runtime tree"
            )
        meter.protocol()
        if (
            getattr(prepared, "executor_recipe_id", None)
            != self.recipe.executor_recipe_id
        ):
            raise Phase3ESealedExecutorV1Error(
                "prepared run binds another executor recipe"
            )
        return freeze

    def __call__(self, prepared: Any, controller: Any, recorder: Any) -> Any:
        # Consume before CAS work: a failed or attacked attempt cannot retry the
        # same factory with altered bytes or another freeze.
        self._guard.consume()
        freeze = getattr(controller, "freeze_attestation", None)
        if type(freeze) is not RouteDecisionFreezeAttestationV1:
            # No CAS/constructor work occurred and no route-scoped subject can
            # yet be trusted; fail before creating a misleading WorkVector.
            raise Phase3ESealedExecutorV1Error(
                "executor construction is forbidden before a typed route freeze"
            )
        route_kind = (
            RouteKindEnum.LOCAL_ATTEMPT
            if self.recipe.selected_route is RouteSelection.LOCAL
            else RouteKindEnum.DIRECT_FALLBACK
        )
        route_subject_id = _selected_route_subject_id_v1(prepared, self.recipe)
        factory_recorder = NativeCounterRecorderV1(
            subject_id=route_subject_id,
            route_kind=route_kind,
            work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            registry=self.registry,
            comparison_profile=self.comparison_profile,
            recorder_id="phase3e-sealed-executor-factory-v1",
            allow_selected_route_shared_operations=True,
        )
        meter = _FactoryWorkMeterV1(factory_recorder)
        # The route subject is derived from the selected upper (local) or
        # route context (fallback), never supplied as an unauthenticated
        # caller parameter.
        meter.protocol()
        stage = "FROZEN_BINDING"
        full_accounting: SealedExecutorConstructionAccountingV1 | None = None
        execution_result: Any = None
        try:
            freeze = self._validate_frozen_binding(prepared, controller, meter)
            spec = OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY.require_exact(
                self.recipe, self.constructor
            )
            meter.protocol()
            scope = (
                AccessRouteScope.LOCAL
                if self.recipe.selected_route is RouteSelection.LOCAL
                else AccessRouteScope.FALLBACK
            )
            controller.record(
                AccessOperation.RESOLVE_RUNTIME_CAS,
                scope,
                artifact_id=self.recipe.runtime_tree_id,
            )
            stage = "RUNTIME_CAS_RESOLVE"
            verified = self.runtime_cas.resolve(
                self.recipe.runtime_tree_id,
                meter=meter,
                cap_profile=self.runtime_cap_profile,
            )
            self.recipe.validate_runtime(verified.manifest)
            if type(self.constructor) is not RuntimeIntegrityProbeConstructorV1:
                declared = getattr(
                    self.constructor, "runtime_factory_cardinality_v1", None
                )
                expected = RuntimeFactoryCardinalityV1.from_manifest(
                    verified.manifest, self.runtime_cap_profile
                )
                if type(declared) is not RuntimeFactoryCardinalityV1 or (
                    RuntimeFactoryCardinalityV1.from_dict(declared.to_dict())
                    != expected
                ):
                    raise Phase3ESealedExecutorV1Error(
                        "trusted constructor/selected upper lacks exact runtime "
                        "manifest cardinality"
                    )
            meter.integrity()
            controller.record(
                AccessOperation.OPEN_RUNTIME_PRIVATE_LEASE,
                scope,
                artifact_id=self.recipe.runtime_tree_id,
            )
            stage = "PRIVATE_LEASE"
            executor_error: Exception | None = None
            with verified.open_private_lease(meter) as lease:
                controller.record(
                    AccessOperation.CONSTRUCT_SELECTED_EXECUTOR,
                    scope,
                    artifact_id=self.recipe.executor_recipe_id,
                )
                # One replayable protocol event covers the exact three-event
                # CAS -> lease -> constructor access sequence above.
                meter.protocol()
                stage = "TRUSTED_CONSTRUCTOR"
                grant = PostFreezeConstructionGrantV1(
                    self.recipe,
                    lease,
                    freeze,
                    _CONSTRUCTION_GRANT_TOKEN,
                )
                executor = self.constructor.construct_after_freeze(grant)
                meter.integrity()
                if (
                    type(executor) is SealedPostFreezeExecutorFactoryV1
                    or not callable(executor)
                ):
                    raise Phase3ESealedExecutorV1Error(
                        "trusted constructor did not return a concrete route executor"
                    )
                stage = "SELECTED_EXECUTOR"
                try:
                    execution_result = executor(prepared, controller, recorder)
                except Exception as error:
                    executor_error = error
            recorded = factory_recorder.seal()
            values = tuple(
                (path, recorded.work_vector.value(path))
                for path in _FACTORY_COUNTER_PATHS
            )
            receipt = SealedExecutorConstructionReceiptV1(
                self.recipe.runtime_tree_id,
                self.recipe.executor_recipe_id,
                self.runtime_cap_profile.runtime_manifest_cap_profile_id,
                OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY.trusted_constructor_registry_id,
                self.recipe.executor_semantics_id,
                f"{spec.constructor_module}.{spec.constructor_qualname}",
                self.recipe.selected_route,
                route_subject_id,
                freeze.route_attempt_id,
                freeze.decision_point_id,
                freeze.route_decision_id,
                freeze.route_decision_freeze_attestation_id,
                verified.manifest.file_count,
                verified.manifest.total_bytes,
                verified.manifest.manifest_document_bytes,
                values,
                tuple(sorted(row.record_id for row in recorded.work_vector.records)),
                recorded.work_vector.work_vector_id,
                recorded.comparison_vector.comparison_vector_id,
                controller.snapshot().access_event_log_id,
            )
            full_accounting = SealedExecutorConstructionAccountingV1(
                receipt, recorded
            )
            self._guard.close_success(full_accounting)
            if executor_error is not None:
                delegate_partial = getattr(
                    executor_error, "partial_recorded_work", None
                )
                if type(delegate_partial) is not RecordedWorkV1:
                    delegate_partial = None
                merged_failure = merge_sealed_factory_failure_work_v1(
                    factory_partial_work=full_accounting.recorded_work,
                    delegate_partial_work=delegate_partial,
                    registry=self.registry,
                    comparison_profile=self.comparison_profile,
                )
                combined = merged_failure.recorded_work
                failure_merge_proof = merged_failure.merge_proof
                failure_evidence = SealedExecutorFailureEvidenceV1(
                    self.recipe.runtime_tree_id,
                    self.recipe.executor_recipe_id,
                    self.runtime_cap_profile.runtime_manifest_cap_profile_id,
                    OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY.trusted_constructor_registry_id,
                    freeze.route_attempt_id,
                    freeze.decision_point_id,
                    freeze.route_decision_freeze_attestation_id,
                    route_subject_id,
                    sealed_failure_stage_from_evidence_v1(
                        controller.snapshot(), delegate_partial
                    ),
                    full_accounting.recorded_work.work_vector.work_vector_id,
                    (
                        delegate_partial.work_vector.work_vector_id
                        if type(delegate_partial) is RecordedWorkV1
                        else TypedNotApplicable(
                            "selected executor exposed no delegate partial work"
                        )
                    ),
                    combined.work_vector.work_vector_id,
                    failure_merge_proof.sealed_executor_failure_merge_proof_id,
                    controller.snapshot().access_event_log_id,
                )
                self._guard.record_delegate_failure(failure_evidence)
                attachments = (
                    ("sealed_construction_accounting", full_accounting),
                    ("sealed_construction_failure_evidence", failure_evidence),
                    ("sealed_factory_partial_work", full_accounting.recorded_work),
                    ("sealed_delegate_partial_work", delegate_partial),
                    (
                        "sealed_execution_failure_merge_proof",
                        failure_merge_proof,
                    ),
                    ("partial_recorded_work", combined),
                )
                try:
                    for name, value in attachments:
                        setattr(executor_error, name, value)
                except (AttributeError, TypeError) as attachment_error:
                    wrapped = Phase3ESealedExecutorV1Error(
                        f"selected executor failed after sealed construction: {executor_error}"
                    )
                    for name, value in attachments:
                        setattr(wrapped, name, value)
                    raise wrapped from attachment_error
                raise executor_error
            delegate_work = getattr(
                execution_result, "native_execution_work", None
            )
            if type(delegate_work) is not RecordedWorkV1:
                if type(self.constructor) is RuntimeIntegrityProbeConstructorV1:
                    # The registered probe is a construction-only diagnostic;
                    # it deliberately returns bytes rather than a route result.
                    return execution_result
                raise Phase3ESealedExecutorV1Error(
                    "trusted selected executor did not return owned native work"
                )
            stage = "EXECUTION_WORK_MERGE"
            merged = merge_sealed_factory_execution_work_v1(
                factory_accounting=full_accounting,
                delegate_work=delegate_work,
                registry=self.registry,
                comparison_profile=self.comparison_profile,
            )
            stage = "RESULT_BINDING"
            try:
                return replace(
                    execution_result,
                    native_execution_work=merged.recorded_work,
                    delegate_execution_work=delegate_work,
                    sealed_executor_construction_accounting=full_accounting,
                    sealed_executor_execution_merge_proof=merged.merge_proof,
                )
            except (TypeError, ValueError) as error:
                raise Phase3ESealedExecutorV1Error(
                    "trusted selected executor returned an incompatible result type"
                ) from error
        except Exception as error:
            if full_accounting is None:
                partial = factory_recorder.seal_partial()
                delegate_partial = getattr(
                    error, "partial_recorded_work", None
                )
                if type(delegate_partial) is not RecordedWorkV1:
                    candidate = getattr(
                        execution_result, "native_execution_work", None
                    )
                    delegate_partial = (
                        candidate if type(candidate) is RecordedWorkV1 else None
                    )
                merged_failure = merge_sealed_factory_failure_work_v1(
                    factory_partial_work=partial,
                    delegate_partial_work=delegate_partial,
                    registry=self.registry,
                    comparison_profile=self.comparison_profile,
                )
                combined = merged_failure.recorded_work
                failure_merge_proof = merged_failure.merge_proof
                evidence = SealedExecutorFailureEvidenceV1(
                    self.recipe.runtime_tree_id,
                    self.recipe.executor_recipe_id,
                    self.runtime_cap_profile.runtime_manifest_cap_profile_id,
                    OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY.trusted_constructor_registry_id,
                    freeze.route_attempt_id,
                    freeze.decision_point_id,
                    freeze.route_decision_freeze_attestation_id,
                    route_subject_id,
                    sealed_failure_stage_from_evidence_v1(
                        controller.snapshot(), delegate_partial
                    ),
                    partial.work_vector.work_vector_id,
                    (
                        delegate_partial.work_vector.work_vector_id
                        if type(delegate_partial) is RecordedWorkV1
                        else TypedNotApplicable(
                            "construction failed before delegate work was available"
                        )
                    ),
                    combined.work_vector.work_vector_id,
                    failure_merge_proof.sealed_executor_failure_merge_proof_id,
                    controller.snapshot().access_event_log_id,
                )
                self._guard.close_failure(partial, evidence)
                for name, value in (
                    ("sealed_construction_partial_work", partial),
                    ("sealed_construction_failure_evidence", evidence),
                    ("sealed_factory_partial_work", partial),
                    ("sealed_delegate_partial_work", delegate_partial),
                    (
                        "sealed_execution_failure_merge_proof",
                        failure_merge_proof,
                    ),
                    ("partial_recorded_work", combined),
                ):
                    try:
                        setattr(error, name, value)
                    except (AttributeError, TypeError):
                        pass
                if getattr(error, "partial_recorded_work", None) is not combined:
                    wrapped = Phase3ESealedExecutorV1Error(
                        f"sealed construction failure: {error}"
                    )
                    for name, value in (
                        ("sealed_construction_partial_work", partial),
                        ("sealed_construction_failure_evidence", evidence),
                        ("sealed_factory_partial_work", partial),
                        ("sealed_delegate_partial_work", delegate_partial),
                        (
                            "sealed_execution_failure_merge_proof",
                            failure_merge_proof,
                        ),
                        ("partial_recorded_work", combined),
                    ):
                        setattr(wrapped, name, value)
                    raise wrapped from error
            elif getattr(
                error, "sealed_construction_failure_evidence", None
            ) is None:
                delegate_partial = getattr(
                    error, "partial_recorded_work", None
                )
                if type(delegate_partial) is not RecordedWorkV1:
                    candidate = getattr(
                        execution_result, "native_execution_work", None
                    )
                    delegate_partial = (
                        candidate if type(candidate) is RecordedWorkV1 else None
                    )
                merged_failure = merge_sealed_factory_failure_work_v1(
                    factory_partial_work=full_accounting.recorded_work,
                    delegate_partial_work=delegate_partial,
                    registry=self.registry,
                    comparison_profile=self.comparison_profile,
                )
                combined = merged_failure.recorded_work
                failure_merge_proof = merged_failure.merge_proof
                evidence = SealedExecutorFailureEvidenceV1(
                    self.recipe.runtime_tree_id,
                    self.recipe.executor_recipe_id,
                    self.runtime_cap_profile.runtime_manifest_cap_profile_id,
                    OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY.trusted_constructor_registry_id,
                    freeze.route_attempt_id,
                    freeze.decision_point_id,
                    freeze.route_decision_freeze_attestation_id,
                    route_subject_id,
                    sealed_failure_stage_from_evidence_v1(
                        controller.snapshot(), delegate_partial
                    ),
                    full_accounting.recorded_work.work_vector.work_vector_id,
                    (
                        delegate_partial.work_vector.work_vector_id
                        if type(delegate_partial) is RecordedWorkV1
                        else TypedNotApplicable(
                            "post-construction failure exposed no delegate work"
                        )
                    ),
                    combined.work_vector.work_vector_id,
                    failure_merge_proof.sealed_executor_failure_merge_proof_id,
                    controller.snapshot().access_event_log_id,
                )
                self._guard.record_delegate_failure(evidence)
                for name, value in (
                    ("sealed_construction_accounting", full_accounting),
                    ("sealed_construction_failure_evidence", evidence),
                    ("sealed_factory_partial_work", full_accounting.recorded_work),
                    ("sealed_delegate_partial_work", delegate_partial),
                    (
                        "sealed_execution_failure_merge_proof",
                        failure_merge_proof,
                    ),
                    ("partial_recorded_work", combined),
                ):
                    try:
                        setattr(error, name, value)
                    except (AttributeError, TypeError):
                        pass
                if getattr(error, "partial_recorded_work", None) is not combined:
                    wrapped = Phase3ESealedExecutorV1Error(
                        f"sealed post-construction failure: {error}"
                    )
                    for name, value in (
                        ("sealed_construction_accounting", full_accounting),
                        ("sealed_construction_failure_evidence", evidence),
                        ("sealed_factory_partial_work", full_accounting.recorded_work),
                        ("sealed_delegate_partial_work", delegate_partial),
                        (
                            "sealed_execution_failure_merge_proof",
                            failure_merge_proof,
                        ),
                        ("partial_recorded_work", combined),
                    ):
                        setattr(wrapped, name, value)
                    raise wrapped from error
            raise


def require_sealed_executor_factory_v1(value: object) -> SealedPostFreezeExecutorFactoryV1:
    """Reject a preconstructed/legacy route callable under the sealed profile."""

    if type(value) is not SealedPostFreezeExecutorFactoryV1:
        raise Phase3ESealedExecutorV1Error(
            "sealed Phase-3E profile rejects preconstructed legacy executors"
        )
    return value


__all__ = [
    "EXECUTOR_RECIPE_DOMAIN",
    "ExecutorRecipeV1",
    "MergedSealedRouteExecutionWorkV1",
    "MergedSealedRouteFailureWorkV1",
    "OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE",
    "OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY",
    "Phase3ESealedExecutorV1Error",
    "PostFreezeConstructionGrantV1",
    "RUNTIME_FACTORY_CAP_CHECKS",
    "RUNTIME_FACTORY_INTEGRITY_BASE_UPPER",
    "RUNTIME_FACTORY_PROTOCOL_CHECKS_UPPER",
    "RUNTIME_FACTORY_TREE_PASSES",
    "RUNTIME_FACTORY_WORKING_BYTES_CAP",
    "RUNTIME_MANIFEST_MAX_DOCUMENT_BYTES",
    "RUNTIME_MANIFEST_MAX_FILE_COUNT",
    "RUNTIME_MANIFEST_MAX_PATH_BYTES",
    "RUNTIME_MANIFEST_MAX_TOTAL_BYTES",
    "RUNTIME_TREE_MANIFEST_DOMAIN",
    "RuntimeIntegrityProbeConstructorV1",
    "RuntimeFactoryCardinalityV1",
    "RuntimeManifestCapProfileV1",
    "RuntimeTreeCASV1",
    "RuntimeTreeEntryV1",
    "RuntimeTreeLeaseV1",
    "RuntimeTreeManifestV1",
    "SealedExecutorConstructionAccountingV1",
    "SealedExecutorConstructionReceiptV1",
    "SealedExecutorExecutionMergeProofV1",
    "SealedExecutorFailureEvidenceV1",
    "SealedExecutorFailureMergeProofV1",
    "SealedPostFreezeExecutorFactoryV1",
    "TrustedConstructorRegistryV1",
    "TrustedConstructorSpecV1",
    "TrustedPostFreezeConstructorV1",
    "VerifiedRuntimeTreeV1",
    "merge_sealed_factory_execution_work_v1",
    "merge_sealed_factory_failure_work_v1",
    "require_sealed_executor_factory_v1",
    "runtime_factory_upper_values_v1",
    "verify_sealed_factory_execution_merge_v1",
    "verify_sealed_factory_failure_merge_v1",
]
