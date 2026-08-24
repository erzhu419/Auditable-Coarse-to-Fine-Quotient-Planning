#!/usr/bin/env python3
"""Materialize the frozen V180r7r1 reachable source tree exactly once.

This is a construction-only transport step.  It consumes the already frozen
source-catalog manifest, copies only its 307-module reachable closure, and
replays the unchanged V2 closure builder against the copied files.  It neither
issues an occurrence authorization nor imports or executes the staged source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Mapping, NoReturn

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_domain_registry_extension_v180r7r1m1 as domains
from acfqp import (
    construction_k7_full_ground_fallback_source_catalog_evidence_freeze_v180r7r1
    as catalog_freeze,
)
from acfqp import (
    construction_k7_full_ground_fallback_source_inventory_preregistration_v180r7r1
    as preregistration,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
LIVE_SOURCE_ROOT = ROOT / "src"
CATALOG_MANIFEST_PATH = (
    ROOT / ".tmp" / "exact-freeze" / "v180r7r1_source_catalog_manifest.json"
)
MATERIALIZED_ROOT = (
    ROOT / ".tmp" / "exact-freeze" / "v180r7r1_materialized_source"
)
MATERIALIZED_SOURCE_ROOT = MATERIALIZED_ROOT / "src" / "acfqp"
OUTPUT_MANIFEST_PATH = (
    ROOT
    / ".tmp"
    / "exact-freeze"
    / "v180r7r1_materialized_source_manifest.json"
)
FAILURE_PATH = (
    ROOT
    / ".tmp"
    / "exact-freeze"
    / "v180r7r1_materialized_source_failure.json"
)

EXPECTED_CATALOG_MANIFEST_ID = (
    "92e4f36212d957d3701591ee689a23e4446d942c4c3e3b562049290c19ad50d0"
)
EXPECTED_CATALOG_CANONICAL_BYTE_COUNT = 911_647
EXPECTED_CATALOG_CANONICAL_SHA256 = (
    "16dc6c70a266224b3fb59d0850c432d6996c72e1a5868340e3878c9fdffde66e"
)
EXPECTED_SOURCE_BOUNDARY_COMMIT = (
    "0d9d32dcb2aa3652696ccc0b5010dfc39455e8af"
)
EXPECTED_SOURCE_INVENTORY_PREREGISTRATION_ID = (
    "30a0aa732e44389f9b246a3664bacf13f5465233c7a1e3a1782baac80dbf38b8"
)
EXPECTED_SOURCE_CLOSURE_REPAIR_ID = (
    "feb8f6034ef1da9050242fe4e112edb285b77bd63a87642196f8fbc7995544c8"
)
EXPECTED_SOURCE_CLOSURE_ID = (
    "ac3f10ef4eea5c0ecc740d9cecc1991e851a65af198e6696f32bde1965feeb4b"
)
EXPECTED_REACHABLE_SOURCE_FACTS_SHA256 = (
    "a087ecfac3bcd6132a2242a670b9c38273de3e7bd823b5687e8223a73069772d"
)
EXPECTED_ROOT_MODULE_COUNT = 151
EXPECTED_REACHABLE_MODULE_COUNT = 307
EXPECTED_REACHABLE_SOURCE_BYTE_COUNT = 15_129_926
EXPECTED_STAGED_SOURCE_DIRECTORY_COUNT = 6

# A cold, one-shot evidence replay reads the retained catalogue twice: once
# through the symlink-free reader here and once through its existing evidence
# freezer.  The freezer additionally reads its producer, nine preregistered
# source files, three retained predecessor inputs, and the preserved failure.
EXPECTED_RETAINED_VALIDATION_FILE_READ_COUNT = 16
EXPECTED_RETAINED_VALIDATION_BYTE_COUNT = 3_765_861
MAXIMUM_MATERIALIZATION_MANIFEST_BYTES = 8 * 1024 * 1024
MAXIMUM_FIXED_POINT_STEPS = 32
MAXIMUM_FAILURE_INVENTORY_ENTRIES = 4_096
MAXIMUM_FAILURE_INVENTORY_REGULAR_BYTES = 64 * 1024 * 1024
MATERIALIZED_SOURCE_TREE_DOMAIN = (
    domains.CONSTRUCTION_K7_MATERIALIZED_SOURCE_TREE_V180R7R1M1_DOMAIN
)
MATERIALIZATION_MANIFEST_DOMAIN = (
    domains.CONSTRUCTION_K7_MATERIALIZED_SOURCE_TREE_MANIFEST_V180R7R1M1_DOMAIN
)
MATERIALIZATION_FAILURE_DOMAIN = (
    domains.CONSTRUCTION_K7_MATERIALIZED_SOURCE_TREE_FAILURE_V180R7R1M1_DOMAIN
)


class V180r7r1MaterializedSourceTreeError(RuntimeError):
    """The frozen inputs, staged tree, or write-once boundary changed."""


class V180r7r1MaterializationReplayForbidden(
    V180r7r1MaterializedSourceTreeError
):
    """An exact completed terminal was detected and must remain unchanged."""


def _fail(message: str) -> NoReturn:
    raise V180r7r1MaterializedSourceTreeError(message)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_hex_digest(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} is not one lowercase SHA-256 digest")
    return value


def _validated_source_relative_path(value: Any) -> PurePosixPath:
    if type(value) is not str or "\\" in value:
        _fail("reachable source relative path is malformed")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or not relative.parts
        or relative.parts[0] != "acfqp"
        or relative.suffix != ".py"
        or any(part in {"", ".", ".."} for part in relative.parts)
        or relative.as_posix() != value
    ):
        _fail("reachable source path escapes its frozen namespace")
    return relative


@dataclass(frozen=True, slots=True)
class ReachableSourceV180r7r1m1:
    module_name: str
    relative_path: str
    source_sha256: str
    source_byte_count: int
    source_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        relative = _validated_source_relative_path(self.relative_path)
        is_package = relative.name == "__init__.py"
        expected = PurePosixPath(
            source_runtime_v2._module_relative_path(  # noqa: SLF001
                self.module_name,
                is_package=is_package,
            )
        )
        if (
            type(self.module_name) is not str
            or not source_runtime_v2._valid_module_name(  # noqa: SLF001
                self.module_name
            )
            or relative != expected
            or type(self.source_sha256) is not str
            or _require_hex_digest(self.source_sha256, "source fact")
            != self.source_sha256
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
            or type(self.source_bytes) is not bytes
            or len(self.source_bytes) != self.source_byte_count
            or _sha256(self.source_bytes) != self.source_sha256
        ):
            _fail("reachable source fact and bytes differ")

    @property
    def staged_relative_path(self) -> str:
        return (PurePosixPath("src") / self.relative_path).as_posix()

    def to_fact(self) -> dict[str, Any]:
        return {
            "module_name": self.module_name,
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
        }


@dataclass(frozen=True, slots=True)
class MaterializationPlanV180r7r1m1:
    catalog_manifest_id: str
    source_boundary_commit: str
    source_inventory_preregistration_id: str
    source_closure_repair_id: str
    root_modules: tuple[str, ...]
    expected_source_closure: Mapping[str, Any] = field(repr=False)
    reachable_sources: tuple[ReachableSourceV180r7r1m1, ...] = field(
        repr=False
    )
    producer_source_facts: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        names = tuple(item.module_name for item in self.reachable_sources)
        facts = [item.to_fact() for item in self.reachable_sources]
        if not (
            self.catalog_manifest_id == EXPECTED_CATALOG_MANIFEST_ID
            and self.source_boundary_commit == EXPECTED_SOURCE_BOUNDARY_COMMIT
            and self.source_inventory_preregistration_id
            == EXPECTED_SOURCE_INVENTORY_PREREGISTRATION_ID
            and self.source_closure_repair_id
            == EXPECTED_SOURCE_CLOSURE_REPAIR_ID
            and type(self.root_modules) is tuple
            and self.root_modules == tuple(sorted(set(self.root_modules)))
            and len(self.root_modules) == EXPECTED_ROOT_MODULE_COUNT
            and type(self.expected_source_closure) is dict
            and self.expected_source_closure.get("closure_id")
            == EXPECTED_SOURCE_CLOSURE_ID
            and names == tuple(sorted(set(names)))
            and len(names) == EXPECTED_REACHABLE_MODULE_COUNT
            and sum(item.source_byte_count for item in self.reachable_sources)
            == EXPECTED_REACHABLE_SOURCE_BYTE_COUNT
            and _sha256(canonical_json_bytes(facts))
            == EXPECTED_REACHABLE_SOURCE_FACTS_SHA256
            and type(self.producer_source_facts) is tuple
            and len(self.producer_source_facts) == 2
            and [row.get("relative_path") for row in self.producer_source_facts]
            == [
                "scripts/materialize_v180r7r1_reachable_source_tree.py",
                "src/acfqp/construction_k7_domain_registry_extension_v180r7r1m1.py",
            ]
            and all(
                type(row) is dict
                and set(row)
                == {
                    "relative_path",
                    "byte_count",
                    "sha256",
                    "excluded_from_frozen_worker_source_catalog",
                }
                and type(row["byte_count"]) is int
                and row["byte_count"] > 0
                and _require_hex_digest(row["sha256"], "producer source fact")
                == row["sha256"]
                and row["excluded_from_frozen_worker_source_catalog"] is True
                for row in self.producer_source_facts
            )
        ):
            _fail("materialization plan differs from the frozen repair")

    @property
    def reachable_source_facts(self) -> list[dict[str, Any]]:
        return [item.to_fact() for item in self.reachable_sources]

    @property
    def reachable_source_byte_count(self) -> int:
        return sum(item.source_byte_count for item in self.reachable_sources)


def _read_exact_source(
    fact: Mapping[str, Any], *, source_root: Path
) -> ReachableSourceV180r7r1m1:
    if type(fact) is not dict or set(fact) != {
        "module_name",
        "relative_path",
        "source_byte_count",
        "source_sha256",
    }:
        _fail("reachable catalogue fact is malformed")
    relative = _validated_source_relative_path(fact["relative_path"])
    if not source_root.is_absolute():
        _fail("live source root must be absolute")
    path = source_root / Path(*relative.parts)
    try:
        raw = source_runtime_v2._read_regular_symlink_free(path)  # noqa: SLF001
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise V180r7r1MaterializedSourceTreeError(
            "reachable live source is absent, linked, or nonregular"
        ) from error
    return ReachableSourceV180r7r1m1(
        fact["module_name"],
        fact["relative_path"],
        fact["source_sha256"],
        fact["source_byte_count"],
        raw,
    )


def _producer_source_facts() -> tuple[Mapping[str, Any], ...]:
    paths = (Path(__file__), Path(domains.__file__))
    rows: list[Mapping[str, Any]] = []
    for path in paths:
        if not path.is_absolute():
            _fail("construction producer source path is not absolute")
        try:
            raw = source_runtime_v2._read_regular_symlink_free(  # noqa: SLF001
                path
            )
        except (
            source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation
        ) as error:
            raise V180r7r1MaterializedSourceTreeError(
                "construction producer source is absent, linked, or nonregular"
            ) from error
        relative_path = path.relative_to(ROOT).as_posix()
        rows.append(
            {
                "relative_path": relative_path,
                "byte_count": len(raw),
                "sha256": _sha256(raw),
                "excluded_from_frozen_worker_source_catalog": True,
            }
        )
    if [row["relative_path"] for row in rows] != [
        "scripts/materialize_v180r7r1_reachable_source_tree.py",
        "src/acfqp/construction_k7_domain_registry_extension_v180r7r1m1.py",
    ]:
        _fail("construction producer source paths changed")
    return tuple(rows)


def _strict_catalogue_bytes() -> bytes:
    try:
        raw = source_runtime_v2._read_regular_symlink_free(  # noqa: SLF001
            CATALOG_MANIFEST_PATH
        )
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise V180r7r1MaterializedSourceTreeError(
            "frozen source-catalog manifest is absent, linked, or nonregular"
        ) from error
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError, UnicodeError) as error:
        raise V180r7r1MaterializedSourceTreeError(
            "frozen source-catalog manifest is not canonical JSON"
        ) from error
    if not (
        type(document) is dict
        and canonical_json_bytes(document) == raw
        and len(raw) == EXPECTED_CATALOG_CANONICAL_BYTE_COUNT
        and _sha256(raw) == EXPECTED_CATALOG_CANONICAL_SHA256
        and document.get("source_catalog_manifest_id")
        == EXPECTED_CATALOG_MANIFEST_ID
    ):
        _fail("frozen source-catalog manifest bytes changed")
    return raw


def build_materialization_plan_v180r7r1m1() -> MaterializationPlanV180r7r1m1:
    """Load the frozen catalogue and read each exact reachable source once."""

    strict_catalogue_raw = _strict_catalogue_bytes()
    # Force the preregistration replay to be a cold replay so the accounting in
    # the resulting one-shot manifest is invariant even in an embedding process.
    freeze_preregistration = getattr(
        preregistration,
        "freeze_full_ground_fallback_source_inventory_preregistration_v180r7r1",
    )
    freeze_preregistration.cache_clear()
    load_catalogue = getattr(
        catalog_freeze,
        "load_frozen_full_ground_fallback_source_catalog_manifest_v180r7r1",
    )
    frozen = load_catalogue()
    if frozen.canonical_bytes != strict_catalogue_raw:
        _fail("strict catalogue read and frozen evidence replay differ")
    document = frozen.to_document()
    repair = document["source_closure_repair"]
    closure = repair["source_closure"]
    catalogue_facts = document["source_catalog_facts"]
    if not (
        type(repair) is dict
        and type(closure) is dict
        and type(catalogue_facts) is list
        and document["source_boundary_commit"]
        == EXPECTED_SOURCE_BOUNDARY_COMMIT
        and document["source_inventory_preregistration_id"]
        == EXPECTED_SOURCE_INVENTORY_PREREGISTRATION_ID
        and document["source_closure_repair_id"]
        == EXPECTED_SOURCE_CLOSURE_REPAIR_ID
        and repair["source_closure_repair_id"]
        == EXPECTED_SOURCE_CLOSURE_REPAIR_ID
        and closure["closure_id"] == EXPECTED_SOURCE_CLOSURE_ID
        and repair["reachable_runtime"]["source_facts_sha256"]
        == EXPECTED_REACHABLE_SOURCE_FACTS_SHA256
    ):
        _fail("frozen source-catalog repair identity changed")

    by_name = {row["module_name"]: row for row in catalogue_facts}
    closure_modules = closure["modules"]
    reachable_names = repair["reachable_runtime"]["module_names"]
    if not (
        type(closure_modules) is list
        and type(reachable_names) is list
        and [row["module_name"] for row in closure_modules]
        == reachable_names
        and reachable_names == sorted(set(reachable_names))
        and set(reachable_names) <= set(by_name)
    ):
        _fail("frozen reachable module inventory changed")

    selected_facts: list[dict[str, Any]] = []
    for module in closure_modules:
        fact = by_name[module["module_name"]]
        if not (
            fact["relative_path"] == module["relative_path"]
            and fact["source_sha256"] == module["source_sha256"]
            and fact["source_byte_count"] == module["source_byte_count"]
        ):
            _fail("reachable catalogue and V2 closure facts differ")
        selected_facts.append(fact)
    if not (
        len(selected_facts) == EXPECTED_REACHABLE_MODULE_COUNT
        and sum(row["source_byte_count"] for row in selected_facts)
        == EXPECTED_REACHABLE_SOURCE_BYTE_COUNT
        and _sha256(canonical_json_bytes(selected_facts))
        == EXPECTED_REACHABLE_SOURCE_FACTS_SHA256
    ):
        _fail("reachable source fact denominator changed")

    sources = tuple(
        _read_exact_source(fact, source_root=LIVE_SOURCE_ROOT)
        for fact in selected_facts
    )
    return MaterializationPlanV180r7r1m1(
        frozen.manifest_id,
        document["source_boundary_commit"],
        document["source_inventory_preregistration_id"],
        frozen.repair_id,
        tuple(closure["root_modules"]),
        closure,
        sources,
        _producer_source_facts(),
    )


def _staged_source_directories(
    sources: tuple[ReachableSourceV180r7r1m1, ...],
) -> tuple[PurePosixPath, ...]:
    directories: set[PurePosixPath] = set()
    for item in sources:
        relative = PurePosixPath(item.staged_relative_path)
        for parent in relative.parents:
            if parent == PurePosixPath("."):
                break
            directories.add(parent)
    result = tuple(sorted(directories, key=lambda item: (len(item.parts), str(item))))
    if (
        len(result) != EXPECTED_STAGED_SOURCE_DIRECTORY_COUNT
        or PurePosixPath("src/acfqp") not in result
    ):
        _fail("staged source directory denominator changed")
    return result


def _require_existing_symlink_free_directory(path: Path) -> None:
    if not path.is_absolute():
        _fail("construction directory path must be absolute")
    absolute = Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            item_stat = os.lstat(current)
        except OSError as error:
            raise V180r7r1MaterializedSourceTreeError(
                "construction directory component is absent"
            ) from error
        if stat.S_ISLNK(item_stat.st_mode) or not stat.S_ISDIR(item_stat.st_mode):
            _fail("construction directory contains a link or nondirectory")


def _write_file_once(path: Path, raw: bytes) -> None:
    if type(raw) is not bytes or not raw:
        _fail("write-once construction bytes are absent")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(path, flags, 0o400)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V180r7r1 materialization short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _path_label(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return os.fspath(path)


def _entry_state(path: Path) -> dict[str, Any]:
    if not os.path.lexists(path):
        return {"presence": "ABSENT", "byte_count": None, "sha256": None}
    try:
        item_stat = os.lstat(path)
    except OSError as error:
        raise V180r7r1MaterializedSourceTreeError(
            "failure progress entry could not be inspected"
        ) from error
    if stat.S_ISLNK(item_stat.st_mode):
        return {"presence": "SYMLINK", "byte_count": None, "sha256": None}
    if stat.S_ISDIR(item_stat.st_mode):
        return {"presence": "DIRECTORY", "byte_count": None, "sha256": None}
    if not stat.S_ISREG(item_stat.st_mode):
        return {"presence": "OTHER", "byte_count": None, "sha256": None}
    try:
        raw = source_runtime_v2._read_regular_symlink_free(path)  # noqa: SLF001
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise V180r7r1MaterializedSourceTreeError(
            "failure progress regular entry changed while inspected"
        ) from error
    return {
        "presence": "REGULAR_FILE",
        "byte_count": len(raw),
        "sha256": _sha256(raw),
    }


def _failure_progress_inventory(materialized_root: Path) -> dict[str, Any]:
    root_state = _entry_state(materialized_root)
    rows: list[dict[str, Any]] = []
    regular_bytes = 0
    if root_state["presence"] == "DIRECTORY":
        pending = [materialized_root]
        while pending:
            directory = pending.pop()
            try:
                entries = sorted(os.scandir(directory), key=lambda item: item.name)
            except OSError as error:
                raise V180r7r1MaterializedSourceTreeError(
                    "failure progress directory could not be enumerated"
                ) from error
            next_directories: list[Path] = []
            for entry in entries:
                path = Path(entry.path)
                relative_path = path.relative_to(materialized_root).as_posix()
                item_state = _entry_state(path)
                row = {"relative_path": relative_path, **item_state}
                rows.append(row)
                if len(rows) > MAXIMUM_FAILURE_INVENTORY_ENTRIES:
                    _fail("failure progress inventory exceeds its entry cap")
                if item_state["presence"] == "REGULAR_FILE":
                    regular_bytes += item_state["byte_count"]
                    if regular_bytes > MAXIMUM_FAILURE_INVENTORY_REGULAR_BYTES:
                        _fail("failure progress inventory exceeds its byte cap")
                elif item_state["presence"] == "DIRECTORY":
                    next_directories.append(path)
            pending.extend(reversed(next_directories))
    rows.sort(key=lambda row: row["relative_path"])
    return {
        "materialized_root": root_state,
        "entries": rows,
        "entry_count": len(rows),
        "directory_count_below_root": sum(
            row["presence"] == "DIRECTORY" for row in rows
        ),
        "regular_file_count": sum(
            row["presence"] == "REGULAR_FILE" for row in rows
        ),
        "regular_file_byte_count": regular_bytes,
        "symlink_count": sum(row["presence"] == "SYMLINK" for row in rows),
        "other_entry_count": sum(
            row["presence"] == "OTHER" for row in rows
        ),
        "entries_sha256": _sha256(canonical_json_bytes(rows)),
        "inventory_complete_within_frozen_caps": True,
    }


def _require_exact_staged_inventory(
    *,
    plan: MaterializationPlanV180r7r1m1,
    materialized_root: Path,
    staged_directories: tuple[PurePosixPath, ...],
) -> None:
    expected_files = {
        item.staged_relative_path for item in plan.reachable_sources
    }
    expected_directories = {item.as_posix() for item in staged_directories}
    actual_files: set[str] = set()
    actual_directories: set[str] = set()
    for path in materialized_root.rglob("*"):
        relative = path.relative_to(materialized_root).as_posix()
        item_stat = os.lstat(path)
        if stat.S_ISLNK(item_stat.st_mode):
            _fail("materialized tree contains a symlink")
        if stat.S_ISREG(item_stat.st_mode):
            actual_files.add(relative)
        elif stat.S_ISDIR(item_stat.st_mode):
            actual_directories.add(relative)
        else:
            _fail("materialized tree contains a nonregular entry")
    if (
        actual_files != expected_files
        or actual_directories != expected_directories
    ):
        _fail("materialized tree inventory differs from reachable facts")


def materialize_source_tree_v180r7r1m1(
    plan: MaterializationPlanV180r7r1m1,
    *,
    materialized_root: Path = MATERIALIZED_ROOT,
) -> tuple[dict[str, Any], int]:
    """Write the exact files and replay unchanged V2 against their paths."""

    if not isinstance(plan, MaterializationPlanV180r7r1m1):
        _fail("materialization plan is foreign")
    if not materialized_root.is_absolute():
        _fail("materialized root must be absolute")
    parent = materialized_root.parent
    _require_existing_symlink_free_directory(parent)
    if os.path.lexists(materialized_root):
        _fail("materialized source root already exists")

    os.mkdir(materialized_root, 0o700)
    staged_directories = _staged_source_directories(plan.reachable_sources)
    for relative in staged_directories:
        os.mkdir(materialized_root / Path(*relative.parts), 0o700)
    for item in plan.reachable_sources:
        _write_file_once(
            materialized_root / Path(*PurePosixPath(item.staged_relative_path).parts),
            item.source_bytes,
        )
    _require_exact_staged_inventory(
        plan=plan,
        materialized_root=materialized_root,
        staged_directories=staged_directories,
    )

    module_sources = {
        item.module_name: item.source_bytes for item in plan.reachable_sources
    }
    module_paths = {
        item.module_name: materialized_root
        / Path(*PurePosixPath(item.staged_relative_path).parts)
        for item in plan.reachable_sources
    }
    try:
        closure = source_runtime_v2.build_construction_source_closure_v2(
            root_modules=plan.root_modules,
            module_sources=module_sources,
            module_paths=module_paths,
        )
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise V180r7r1MaterializedSourceTreeError(
            "unchanged V2 rejected the materialized source tree"
        ) from error
    closure_document = closure.to_document()
    if not (
        closure.closure_id == EXPECTED_SOURCE_CLOSURE_ID
        and closure_document == plan.expected_source_closure
    ):
        _fail("materialized unchanged-V2 closure identity changed")

    tree_directories = (PurePosixPath("."), *staged_directories)
    for relative in reversed(tree_directories):
        directory = (
            materialized_root
            if relative == PurePosixPath(".")
            else materialized_root / Path(*relative.parts)
        )
        os.chmod(directory, 0o500)
        _fsync_directory(directory)
    _fsync_directory(parent)
    return closure_document, len(tree_directories)


def _materialized_tree_document(
    plan: MaterializationPlanV180r7r1m1,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.full_ground_fallback_materialized_source_tree.v180r7r1m1",
        "materialized_source_tree_domain": (
            MATERIALIZED_SOURCE_TREE_DOMAIN
        ),
        "source_catalog_manifest_id": plan.catalog_manifest_id,
        "source_boundary_commit": plan.source_boundary_commit,
        "source_inventory_preregistration_id": (
            plan.source_inventory_preregistration_id
        ),
        "source_closure_repair_id": plan.source_closure_repair_id,
        "source_closure_id": EXPECTED_SOURCE_CLOSURE_ID,
        "materialized_root_relative_path": MATERIALIZED_ROOT.relative_to(
            ROOT
        ).as_posix(),
        "materialized_source_root_relative_path": (
            MATERIALIZED_SOURCE_ROOT.relative_to(ROOT).as_posix()
        ),
        "reachable_source_facts_sha256": (
            EXPECTED_REACHABLE_SOURCE_FACTS_SHA256
        ),
        "reachable_source_facts": plan.reachable_source_facts,
        "materialized_source_file_count": len(plan.reachable_sources),
        "materialized_source_byte_count": plan.reachable_source_byte_count,
        "only_exact_reachable_source_facts_materialized": True,
        "candidate_catalog_unreachable_files_materialized": False,
        "source_bytes_executed": False,
        "construction_only": True,
    }
    return {
        **payload,
        "materialized_source_tree_id": domains.extension_content_id_v180r7r1m1(
            MATERIALIZED_SOURCE_TREE_DOMAIN,
            payload,
        ),
    }


def _construction_work_accounting(
    plan: MaterializationPlanV180r7r1m1,
    *,
    tree_directory_count: int,
    manifest_byte_count: int,
) -> dict[str, Any]:
    producer_bytes = sum(
        row["byte_count"] for row in plan.producer_source_facts
    )
    source_files = len(plan.reachable_sources)
    source_bytes = plan.reachable_source_byte_count
    semantic_read_files = (
        EXPECTED_RETAINED_VALIDATION_FILE_READ_COUNT
        + len(plan.producer_source_facts)
        + source_files
        + source_files
    )
    semantic_read_bytes = (
        EXPECTED_RETAINED_VALIDATION_BYTE_COUNT
        + producer_bytes
        + source_bytes
        + source_bytes
    )
    return {
        "scope": (
            "COLD_ONE_SHOT_PRODUCER_EXACT_SEMANTIC_FILE_IO;"
            "IMPORT_LOADER_IO_AND_FILESYSTEM_METADATA_EXCLUDED"
        ),
        "retained_identity_validation_reads": {
            "file_count": EXPECTED_RETAINED_VALIDATION_FILE_READ_COUNT,
            "byte_count": EXPECTED_RETAINED_VALIDATION_BYTE_COUNT,
            "sha256_file_identity_checks": (
                EXPECTED_RETAINED_VALIDATION_FILE_READ_COUNT
            ),
        },
        "construction_producer_identity_reads": {
            "file_count": len(plan.producer_source_facts),
            "byte_count": producer_bytes,
            "sha256_file_identity_checks": len(plan.producer_source_facts),
        },
        "live_reachable_source_reads": {
            "file_count": source_files,
            "byte_count": source_bytes,
            "sha256_source_fact_checks": source_files,
        },
        "materialized_source_writes": {
            "file_count": source_files,
            "byte_count": source_bytes,
            "file_fsync_count": source_files,
        },
        "unchanged_v2_materialized_source_replay_reads": {
            "file_count": source_files,
            "byte_count": source_bytes,
            "caller_supplied_byte_equality_checks": source_files,
            "source_digest_constructions": source_files,
        },
        "materialized_tree_directories": {
            "created_directory_count": tree_directory_count,
            "staged_source_directory_count_below_root": (
                tree_directory_count - 1
            ),
            "tree_directory_fsync_count": tree_directory_count,
            "evidence_parent_directory_fsync_count": 2,
        },
        "materialization_manifest_write": {
            "file_count": 1,
            "byte_count": manifest_byte_count,
            "file_fsync_count": 1,
        },
        "semantic_file_read_count": semantic_read_files,
        "semantic_file_read_byte_count": semantic_read_bytes,
        "durable_file_write_count": source_files + 1,
        "durable_file_write_byte_count": source_bytes + manifest_byte_count,
        "file_fsync_count": source_files + 1,
        "directory_fsync_count": tree_directory_count + 2,
        "occurrence_counter_record_count": 0,
        "occurrence_route_work_vector_count": 0,
        "occurrence_comparison_vector_count": 0,
        "construction_work_excluded_from_occurrence_route_vectors": True,
    }


def build_materialization_manifest_v180r7r1m1(
    *,
    plan: MaterializationPlanV180r7r1m1,
    materialized_source_closure: Mapping[str, Any],
    tree_directory_count: int,
) -> tuple[dict[str, Any], bytes]:
    """Build the canonical manifest, including its exact output byte count."""

    if (
        not isinstance(plan, MaterializationPlanV180r7r1m1)
        or type(materialized_source_closure) is not dict
        or materialized_source_closure != plan.expected_source_closure
        or materialized_source_closure.get("closure_id")
        != EXPECTED_SOURCE_CLOSURE_ID
        or type(tree_directory_count) is not int
        or tree_directory_count != EXPECTED_STAGED_SOURCE_DIRECTORY_COUNT + 1
    ):
        _fail("materialized closure or directory count is not exact")
    tree = _materialized_tree_document(plan)
    manifest_byte_count = 0
    for _step in range(MAXIMUM_FIXED_POINT_STEPS):
        payload = {
            "schema": (
                "acfqp.full_ground_fallback_materialized_source_tree_manifest."
                "v180r7r1m1"
            ),
            "materialization_manifest_domain": (
                MATERIALIZATION_MANIFEST_DOMAIN
            ),
            "source_catalog_manifest_id": plan.catalog_manifest_id,
            "source_catalog_manifest_canonical_byte_count": (
                EXPECTED_CATALOG_CANONICAL_BYTE_COUNT
            ),
            "source_catalog_manifest_canonical_sha256": (
                EXPECTED_CATALOG_CANONICAL_SHA256
            ),
            "source_boundary_commit": plan.source_boundary_commit,
            "source_inventory_preregistration_id": (
                plan.source_inventory_preregistration_id
            ),
            "source_closure_repair_id": plan.source_closure_repair_id,
            "materialized_source_tree": tree,
            "materialized_source_tree_id": tree["materialized_source_tree_id"],
            "unchanged_v2_source_closure": dict(materialized_source_closure),
            "unchanged_v2_source_closure_id": EXPECTED_SOURCE_CLOSURE_ID,
            "construction_producer_source_facts": [
                dict(row) for row in plan.producer_source_facts
            ],
            "construction_work": _construction_work_accounting(
                plan,
                tree_directory_count=tree_directory_count,
                manifest_byte_count=manifest_byte_count,
            ),
            "materialized_root_relative_path": MATERIALIZED_ROOT.relative_to(
                ROOT
            ).as_posix(),
            "manifest_output_relative_path": OUTPUT_MANIFEST_PATH.relative_to(
                ROOT
            ).as_posix(),
            "write_once_o_excl_required": True,
            "file_fsync_required": True,
            "directory_fsync_required": True,
            "same_materialization_identity_rerun_after_progress_forbidden": True,
            "fresh_execution_authorization_issued": False,
            "fallback_occurrence_started": False,
            "scientific_occurrence_executed": False,
            "production_outcome_accessed": False,
            "counter_records_issued": False,
            "route_work_vectors_issued": False,
            "comparison_vectors_issued": False,
            "producer_free_verification_present": False,
            "success_claimed": False,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "SCALAR_CALIBRATION_GATE": "NOT_RUN",
            "BREAK_EVEN_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
            "construction_only": True,
        }
        document = {
            **payload,
            "materialization_manifest_id": (
                domains.extension_content_id_v180r7r1m1(
                    MATERIALIZATION_MANIFEST_DOMAIN,
                    payload,
                )
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == manifest_byte_count:
            if len(raw) > MAXIMUM_MATERIALIZATION_MANIFEST_BYTES:
                _fail("materialization manifest exceeds its finite byte cap")
            return document, raw
        manifest_byte_count = len(raw)
    _fail("materialization manifest byte-count fixed point did not converge")


def _write_manifest_once(path: Path, raw: bytes) -> None:
    if (
        path not in {OUTPUT_MANIFEST_PATH, FAILURE_PATH}
        and path.parent == OUTPUT_MANIFEST_PATH.parent
    ):
        _fail("materialization manifest target changed inside evidence directory")
    if len(raw) > MAXIMUM_MATERIALIZATION_MANIFEST_BYTES:
        _fail("materialization manifest exceeds its finite byte cap")
    _require_existing_symlink_free_directory(path.parent)
    _write_file_once(path, raw)
    _fsync_directory(path.parent)


def build_materialization_failure_v180r7r1m1(
    error: BaseException,
    *,
    failed_phase: str,
    plan_built: bool,
    unchanged_v2_closure_replayed: bool,
    materialized_root: Path = MATERIALIZED_ROOT,
    output_manifest_path: Path = OUTPUT_MANIFEST_PATH,
) -> tuple[dict[str, Any], bytes]:
    """Describe exact bounded progress without following partial-tree links."""

    if (
        not isinstance(error, BaseException)
        or type(failed_phase) is not str
        or not failed_phase
        or len(failed_phase) > 128
        or type(plan_built) is not bool
        or type(unchanged_v2_closure_replayed) is not bool
    ):
        _fail("materialization failure inputs are malformed")
    failure_message = str(error)
    if len(failure_message.encode("utf-8")) > 64 * 1024:
        _fail("materialization failure message exceeds its finite cap")
    progress = _failure_progress_inventory(materialized_root)
    output_state = _entry_state(output_manifest_path)
    payload = {
        "schema": (
            "acfqp.full_ground_fallback_materialized_source_tree_failure."
            "v180r7r1m1"
        ),
        "materialized_source_tree_failure_domain": (
            MATERIALIZATION_FAILURE_DOMAIN
        ),
        "source_catalog_manifest_id": EXPECTED_CATALOG_MANIFEST_ID,
        "source_catalog_manifest_canonical_byte_count": (
            EXPECTED_CATALOG_CANONICAL_BYTE_COUNT
        ),
        "source_catalog_manifest_canonical_sha256": (
            EXPECTED_CATALOG_CANONICAL_SHA256
        ),
        "source_inventory_preregistration_id": (
            EXPECTED_SOURCE_INVENTORY_PREREGISTRATION_ID
        ),
        "source_closure_repair_id": EXPECTED_SOURCE_CLOSURE_REPAIR_ID,
        "expected_source_closure_id": EXPECTED_SOURCE_CLOSURE_ID,
        "failed_phase": failed_phase,
        "failure_type": f"{type(error).__module__}.{type(error).__qualname__}",
        "failure_message": failure_message,
        "failure_message_sha256": _sha256(failure_message.encode("utf-8")),
        "plan_built_before_failure": plan_built,
        "unchanged_v2_closure_replayed_before_failure": (
            unchanged_v2_closure_replayed
        ),
        "materialized_root_relative_path": _path_label(materialized_root),
        "materialized_progress_inventory": progress,
        "materialization_manifest_relative_path": _path_label(
            output_manifest_path
        ),
        "materialization_manifest_state": output_state,
        "progress_inventory_is_failure_evidence_not_success_evidence": True,
        "same_materialization_identity_rerun_forbidden": True,
        "failure_evidence_write_once_o_excl_required": True,
        "failure_evidence_file_fsync_required": True,
        "failure_evidence_directory_fsync_required": True,
        "fresh_execution_authorization_issued": False,
        "fallback_occurrence_started": False,
        "scientific_occurrence_executed": False,
        "production_outcome_accessed": False,
        "counter_records_issued": False,
        "route_work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "success_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "construction_only": True,
    }
    document = {
        **payload,
        "materialized_source_tree_failure_id": (
            domains.extension_content_id_v180r7r1m1(
                MATERIALIZATION_FAILURE_DOMAIN,
                payload,
            )
        ),
    }
    raw = canonical_json_bytes(document)
    if len(raw) > MAXIMUM_MATERIALIZATION_MANIFEST_BYTES:
        _fail("materialization failure evidence exceeds its finite byte cap")
    return document, raw


def _write_failure_once(path: Path, raw: bytes) -> None:
    _write_manifest_once(path, raw)


def _exact_completed_materialization_present() -> bool:
    """Recognize a completed exact terminal without mutating or reissuing it."""

    try:
        raw = source_runtime_v2._read_regular_symlink_free(  # noqa: SLF001
            OUTPUT_MANIFEST_PATH
        )
        document = loads_canonical_json(raw)
        if type(document) is not dict or canonical_json_bytes(document) != raw:
            return False
        tree = document["materialized_source_tree"]
        closure = document["unchanged_v2_source_closure"]
        facts = tree["reachable_source_facts"]
        if not (
            type(tree) is dict
            and type(closure) is dict
            and type(facts) is list
            and document["schema"]
            == "acfqp.full_ground_fallback_materialized_source_tree_manifest.v180r7r1m1"
            and document["source_catalog_manifest_id"]
            == EXPECTED_CATALOG_MANIFEST_ID
            and document["source_closure_repair_id"]
            == EXPECTED_SOURCE_CLOSURE_REPAIR_ID
            and document["unchanged_v2_source_closure_id"]
            == EXPECTED_SOURCE_CLOSURE_ID
            and closure["closure_id"] == EXPECTED_SOURCE_CLOSURE_ID
            and tree["reachable_source_facts_sha256"]
            == EXPECTED_REACHABLE_SOURCE_FACTS_SHA256
            and tree["materialized_source_file_count"]
            == EXPECTED_REACHABLE_MODULE_COUNT
            and tree["materialized_source_byte_count"]
            == EXPECTED_REACHABLE_SOURCE_BYTE_COUNT
            and document["construction_work"]["materialization_manifest_write"][
                "byte_count"
            ]
            == len(raw)
        ):
            return False
        sources = tuple(
            _read_exact_source(
                fact,
                source_root=MATERIALIZED_ROOT / "src",
            )
            for fact in facts
        )
        plan = MaterializationPlanV180r7r1m1(
            document["source_catalog_manifest_id"],
            document["source_boundary_commit"],
            document["source_inventory_preregistration_id"],
            document["source_closure_repair_id"],
            tuple(closure["root_modules"]),
            closure,
            sources,
            tuple(document["construction_producer_source_facts"]),
        )
        staged_directories = _staged_source_directories(plan.reachable_sources)
        _require_exact_staged_inventory(
            plan=plan,
            materialized_root=MATERIALIZED_ROOT,
            staged_directories=staged_directories,
        )
        replay = source_runtime_v2.build_construction_source_closure_v2(
            root_modules=plan.root_modules,
            module_sources={
                item.module_name: item.source_bytes
                for item in plan.reachable_sources
            },
            module_paths={
                item.module_name: MATERIALIZED_ROOT
                / Path(*PurePosixPath(item.staged_relative_path).parts)
                for item in plan.reachable_sources
            },
        ).to_document()
        if replay != closure:
            return False
        rebuilt, rebuilt_raw = build_materialization_manifest_v180r7r1m1(
            plan=plan,
            materialized_source_closure=replay,
            tree_directory_count=len(staged_directories) + 1,
        )
        return rebuilt == document and rebuilt_raw == raw
    except (
        KeyError,
        AttributeError,
        IndexError,
        OSError,
        TypeError,
        ValueError,
        V180r7r1MaterializedSourceTreeError,
        source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation,
    ):
        return False


def main() -> None:
    if os.path.lexists(FAILURE_PATH):
        _fail("V180r7r1 materialization failure evidence already exists")
    failed_phase = "PREEXISTING_PROGRESS_CHECK"
    plan_built = False
    unchanged_v2_closure_replayed = False
    try:
        if (
            os.path.lexists(MATERIALIZED_ROOT)
            and os.path.lexists(OUTPUT_MANIFEST_PATH)
            and _exact_completed_materialization_present()
        ):
            raise V180r7r1MaterializationReplayForbidden(
                "V180r7r1 exact materialization already completed; "
                "replay forbidden"
            )
        if os.path.lexists(MATERIALIZED_ROOT):
            _fail("V180r7r1 materialized source root already exists")
        if os.path.lexists(OUTPUT_MANIFEST_PATH):
            _fail("V180r7r1 materialization manifest already exists")
        failed_phase = "FROZEN_CATALOGUE_AND_LIVE_SOURCE_REPLAY"
        plan = build_materialization_plan_v180r7r1m1()
        plan_built = True
        failed_phase = "WRITE_AND_REPLAY_MATERIALIZED_SOURCE_TREE"
        closure_document, tree_directory_count = (
            materialize_source_tree_v180r7r1m1(plan)
        )
        unchanged_v2_closure_replayed = True
        failed_phase = "BUILD_CANONICAL_MATERIALIZATION_MANIFEST"
        document, raw = build_materialization_manifest_v180r7r1m1(
            plan=plan,
            materialized_source_closure=closure_document,
            tree_directory_count=tree_directory_count,
        )
        failed_phase = "DURABLE_MATERIALIZATION_MANIFEST_WRITE"
        _write_manifest_once(OUTPUT_MANIFEST_PATH, raw)
        print(
            "V180R7R1_MATERIALIZED_SOURCE_TREE",
            document["materialization_manifest_id"],
            document["materialized_source_tree_id"],
            len(raw),
            _sha256(raw),
            flush=True,
        )
    except V180r7r1MaterializationReplayForbidden:
        raise
    except BaseException as error:
        _failure_document, failure_raw = build_materialization_failure_v180r7r1m1(
            error,
            failed_phase=failed_phase,
            plan_built=plan_built,
            unchanged_v2_closure_replayed=unchanged_v2_closure_replayed,
            materialized_root=MATERIALIZED_ROOT,
            output_manifest_path=OUTPUT_MANIFEST_PATH,
        )
        _write_failure_once(FAILURE_PATH, failure_raw)
        raise


if __name__ == "__main__":
    main()
