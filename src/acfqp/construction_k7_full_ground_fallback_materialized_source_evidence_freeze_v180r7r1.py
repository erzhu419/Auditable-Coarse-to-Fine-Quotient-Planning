"""Freeze and independently replay the V180r7r1 materialized source tree."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Mapping, NoReturn

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_domain_registry_extension_v180r7r1m1 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_MATERIALIZATION_MANIFEST_ID = (
    "1480c3e0a5bcfe7e88f9cbd6a346efd500c17a1826ca656aa527567a0c8ae7f3"
)
EXPECTED_MATERIALIZED_SOURCE_TREE_ID = (
    "5cc30a0a9eea4caa239953af930c8382d3194b2f2ad82847eb9c0ba79b7a2993"
)
EXPECTED_CANONICAL_BYTE_COUNT = 340_182
EXPECTED_CANONICAL_SHA256 = (
    "790a2dbc89828bc23938e4b09d2d7e0c292e8b7c3b5f92ee0738d540d20e380c"
)
EXPECTED_SOURCE_CATALOG_MANIFEST_ID = (
    "92e4f36212d957d3701591ee689a23e4446d942c4c3e3b562049290c19ad50d0"
)
EXPECTED_SOURCE_CATALOG_CANONICAL_BYTE_COUNT = 911_647
EXPECTED_SOURCE_CATALOG_CANONICAL_SHA256 = (
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
EXPECTED_REACHABLE_MODULE_COUNT = 307
EXPECTED_REACHABLE_SOURCE_BYTE_COUNT = 15_129_926
EXPECTED_ROOT_MODULE_COUNT = 151
EXPECTED_DIRECTORY_COUNT_BELOW_ROOT = 6

_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST_PATH = (
    _ROOT
    / ".tmp"
    / "exact-freeze"
    / "v180r7r1_materialized_source_manifest.json"
)
_SOURCE_ROOT = (
    _ROOT / ".tmp" / "exact-freeze" / "v180r7r1_materialized_source"
)
_FAILURE_PATH = (
    _ROOT
    / ".tmp"
    / "exact-freeze"
    / "v180r7r1_materialized_source_failure.json"
)
_MANIFEST_DOMAIN = (
    domains.CONSTRUCTION_K7_MATERIALIZED_SOURCE_TREE_MANIFEST_V180R7R1M1_DOMAIN
)
_TREE_DOMAIN = (
    domains.CONSTRUCTION_K7_MATERIALIZED_SOURCE_TREE_V180R7R1M1_DOMAIN
)

_TOP_LEVEL_FIELDS = {
    "BREAK_EVEN_GATE",
    "COUNTER_COMPLETENESS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "comparison_vectors_issued",
    "construction_only",
    "construction_producer_source_facts",
    "construction_work",
    "counter_records_issued",
    "directory_fsync_required",
    "fallback_occurrence_started",
    "file_fsync_required",
    "fresh_execution_authorization_issued",
    "manifest_output_relative_path",
    "materialization_manifest_domain",
    "materialization_manifest_id",
    "materialized_root_relative_path",
    "materialized_source_tree",
    "materialized_source_tree_id",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "producer_free_verification_present",
    "production_outcome_accessed",
    "route_work_vectors_issued",
    "same_materialization_identity_rerun_after_progress_forbidden",
    "schema",
    "scientific_occurrence_executed",
    "source_boundary_commit",
    "source_catalog_manifest_canonical_byte_count",
    "source_catalog_manifest_canonical_sha256",
    "source_catalog_manifest_id",
    "source_closure_repair_id",
    "source_inventory_preregistration_id",
    "success_claimed",
    "unchanged_v2_source_closure",
    "unchanged_v2_source_closure_id",
    "write_once_o_excl_required",
}
_TREE_FIELDS = {
    "candidate_catalog_unreachable_files_materialized",
    "construction_only",
    "materialized_root_relative_path",
    "materialized_source_byte_count",
    "materialized_source_file_count",
    "materialized_source_root_relative_path",
    "materialized_source_tree_domain",
    "materialized_source_tree_id",
    "only_exact_reachable_source_facts_materialized",
    "reachable_source_facts",
    "reachable_source_facts_sha256",
    "schema",
    "source_boundary_commit",
    "source_bytes_executed",
    "source_catalog_manifest_id",
    "source_closure_id",
    "source_closure_repair_id",
    "source_inventory_preregistration_id",
}
_SOURCE_FACT_FIELDS = {
    "module_name",
    "relative_path",
    "source_byte_count",
    "source_sha256",
}
_PRODUCER_SOURCE_FACTS = [
    {
        "relative_path": "scripts/materialize_v180r7r1_reachable_source_tree.py",
        "byte_count": 46_131,
        "sha256": (
            "0dc4a7ab0829b67194cd9dd1877417ea9e77ad1f6243ebc916eb06caf3efa49c"
        ),
        "excluded_from_frozen_worker_source_catalog": True,
    },
    {
        "relative_path": (
            "src/acfqp/construction_k7_domain_registry_extension_v180r7r1m1.py"
        ),
        "byte_count": 1_663,
        "sha256": (
            "63dd8510b26f4c0fab607039a8e1e8cf6f9f7227a96874344e140175e545f8f3"
        ),
        "excluded_from_frozen_worker_source_catalog": True,
    },
]
_CONSTRUCTION_WORK = {
    "construction_producer_identity_reads": {
        "byte_count": 47_794,
        "file_count": 2,
        "sha256_file_identity_checks": 2,
    },
    "construction_work_excluded_from_occurrence_route_vectors": True,
    "directory_fsync_count": 9,
    "durable_file_write_byte_count": 15_470_108,
    "durable_file_write_count": 308,
    "file_fsync_count": 308,
    "live_reachable_source_reads": {
        "byte_count": EXPECTED_REACHABLE_SOURCE_BYTE_COUNT,
        "file_count": EXPECTED_REACHABLE_MODULE_COUNT,
        "sha256_source_fact_checks": EXPECTED_REACHABLE_MODULE_COUNT,
    },
    "materialization_manifest_write": {
        "byte_count": EXPECTED_CANONICAL_BYTE_COUNT,
        "file_count": 1,
        "file_fsync_count": 1,
    },
    "materialized_source_writes": {
        "byte_count": EXPECTED_REACHABLE_SOURCE_BYTE_COUNT,
        "file_count": EXPECTED_REACHABLE_MODULE_COUNT,
        "file_fsync_count": EXPECTED_REACHABLE_MODULE_COUNT,
    },
    "materialized_tree_directories": {
        "created_directory_count": 7,
        "evidence_parent_directory_fsync_count": 2,
        "staged_source_directory_count_below_root": (
            EXPECTED_DIRECTORY_COUNT_BELOW_ROOT
        ),
        "tree_directory_fsync_count": 7,
    },
    "occurrence_comparison_vector_count": 0,
    "occurrence_counter_record_count": 0,
    "occurrence_route_work_vector_count": 0,
    "retained_identity_validation_reads": {
        "byte_count": 3_765_861,
        "file_count": 16,
        "sha256_file_identity_checks": 16,
    },
    "scope": (
        "COLD_ONE_SHOT_PRODUCER_EXACT_SEMANTIC_FILE_IO;"
        "IMPORT_LOADER_IO_AND_FILESYSTEM_METADATA_EXCLUDED"
    ),
    "semantic_file_read_byte_count": 34_073_507,
    "semantic_file_read_count": 632,
    "unchanged_v2_materialized_source_replay_reads": {
        "byte_count": EXPECTED_REACHABLE_SOURCE_BYTE_COUNT,
        "caller_supplied_byte_equality_checks": EXPECTED_REACHABLE_MODULE_COUNT,
        "file_count": EXPECTED_REACHABLE_MODULE_COUNT,
        "source_digest_constructions": EXPECTED_REACHABLE_MODULE_COUNT,
    },
}


class FullGroundFallbackMaterializedSourceEvidenceFreezeV180r7r1Error(
    ValueError
):
    """The retained manifest, staged tree, or construction locks changed."""


def _fail(message: str) -> NoReturn:
    raise FullGroundFallbackMaterializedSourceEvidenceFreezeV180r7r1Error(
        message
    )


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_regular_symlink_free(path: Path) -> bytes:
    try:
        return source_runtime_v2._read_regular_symlink_free(path)  # noqa: SLF001
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise FullGroundFallbackMaterializedSourceEvidenceFreezeV180r7r1Error(
            "materialized evidence path is absent, linked, or nonregular"
        ) from error


def _require_symlink_free_directory(path: Path) -> None:
    if not path.is_absolute():
        _fail("materialized directory is not absolute")
    absolute = Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            item_stat = os.lstat(current)
        except OSError as error:
            raise FullGroundFallbackMaterializedSourceEvidenceFreezeV180r7r1Error(
                "materialized directory component is absent"
            ) from error
        if stat.S_ISLNK(item_stat.st_mode) or not stat.S_ISDIR(item_stat.st_mode):
            _fail("materialized directory contains a link or nondirectory")


def _content_id(domain: str, document: Mapping[str, Any], field: str) -> str:
    if type(document) is not dict:
        _fail("identity-bearing materialization value is not one object")
    payload = dict(document)
    identity = payload.pop(field, None)
    if (
        type(identity) is not str
        or identity
        != domains.extension_content_id_v180r7r1m1(domain, payload)
    ):
        _fail(f"retained {field} changed")
    return identity


def _safe_source_path(value: Any) -> PurePosixPath:
    if type(value) is not str or "\\" in value:
        _fail("materialized source relative path is malformed")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or not relative.parts
        or relative.parts[0] != "acfqp"
        or relative.suffix != ".py"
        or any(part in {"", ".", ".."} for part in relative.parts)
        or relative.as_posix() != value
    ):
        _fail("materialized source relative path escapes its root")
    return relative


def _inventory_tree(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    _require_symlink_free_directory(root)
    directories: list[str] = []
    files: list[str] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda item: item.name)
        except OSError as error:
            raise FullGroundFallbackMaterializedSourceEvidenceFreezeV180r7r1Error(
                "materialized source tree could not be enumerated"
            ) from error
        child_directories: list[Path] = []
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            try:
                item_stat = os.lstat(path)
            except OSError as error:
                raise FullGroundFallbackMaterializedSourceEvidenceFreezeV180r7r1Error(
                    "materialized source entry disappeared"
                ) from error
            if stat.S_ISLNK(item_stat.st_mode):
                _fail("materialized source tree contains a symlink")
            if stat.S_ISDIR(item_stat.st_mode):
                directories.append(relative)
                child_directories.append(path)
            elif stat.S_ISREG(item_stat.st_mode):
                files.append(relative)
            else:
                _fail("materialized source tree contains a nonregular entry")
        pending.extend(reversed(child_directories))
    return tuple(sorted(directories)), tuple(sorted(files))


def _require_exact_inventory(
    root: Path,
    facts: list[dict[str, Any]],
) -> None:
    expected_files: set[str] = set()
    expected_directories: set[str] = set()
    for fact in facts:
        relative = PurePosixPath("src") / _safe_source_path(
            fact["relative_path"]
        )
        expected_files.add(relative.as_posix())
        for parent in relative.parents:
            if parent == PurePosixPath("."):
                break
            expected_directories.add(parent.as_posix())
    directories, files = _inventory_tree(root)
    if not (
        set(directories) == expected_directories
        and set(files) == expected_files
        and len(directories) == EXPECTED_DIRECTORY_COUNT_BELOW_ROOT
        and len(files) == EXPECTED_REACHABLE_MODULE_COUNT
    ):
        _fail("materialized source tree entry set changed")


def _read_and_replay_source_closure(
    *,
    root: Path,
    facts: list[dict[str, Any]],
    expected_closure: dict[str, Any],
) -> dict[str, Any]:
    modules = expected_closure.get("modules")
    root_modules = expected_closure.get("root_modules")
    if not (
        type(modules) is list
        and len(modules) == EXPECTED_REACHABLE_MODULE_COUNT
        and type(root_modules) is list
        and root_modules == sorted(set(root_modules))
        and len(root_modules) == EXPECTED_ROOT_MODULE_COUNT
        and [row["module_name"] for row in modules]
        == [row["module_name"] for row in facts]
    ):
        _fail("embedded unchanged-V2 closure denominator changed")
    _require_exact_inventory(root, facts)
    sources: dict[str, bytes] = {}
    paths: dict[str, Path] = {}
    for fact, module in zip(facts, modules, strict=True):
        if not (
            type(fact) is dict
            and set(fact) == _SOURCE_FACT_FIELDS
            and fact["relative_path"] == module["relative_path"]
            and fact["source_byte_count"] == module["source_byte_count"]
            and fact["source_sha256"] == module["source_sha256"]
        ):
            _fail("materialized source fact and V2 module fact differ")
        relative = _safe_source_path(fact["relative_path"])
        path = root / "src" / Path(*relative.parts)
        raw = _read_regular_symlink_free(path)
        if not (
            type(fact["module_name"]) is str
            and type(fact["source_byte_count"]) is int
            and fact["source_byte_count"] > 0
            and type(fact["source_sha256"]) is str
            and len(fact["source_sha256"]) == 64
            and len(raw) == fact["source_byte_count"]
            and _sha256(raw) == fact["source_sha256"]
        ):
            _fail("materialized source bytes changed")
        name = fact["module_name"]
        if name in sources:
            _fail("materialized source module name is duplicated")
        sources[name] = raw
        paths[name] = path
    if not (
        len(sources) == EXPECTED_REACHABLE_MODULE_COUNT
        and sum(len(raw) for raw in sources.values())
        == EXPECTED_REACHABLE_SOURCE_BYTE_COUNT
    ):
        _fail("materialized source byte denominator changed")
    try:
        replay = source_runtime_v2.build_construction_source_closure_v2(
            root_modules=tuple(root_modules),
            module_sources=sources,
            module_paths=paths,
        )
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise FullGroundFallbackMaterializedSourceEvidenceFreezeV180r7r1Error(
            "unchanged V2 rejected the retained materialized source tree"
        ) from error
    document = replay.to_document()
    if not (
        replay.closure_id == EXPECTED_SOURCE_CLOSURE_ID
        and document == expected_closure
    ):
        _fail("unchanged V2 materialized-source closure replay changed")
    return document


def _verify_producer_source_facts(document: dict[str, Any]) -> None:
    facts = document.get("construction_producer_source_facts")
    if facts != _PRODUCER_SOURCE_FACTS:
        _fail("materialization producer source facts changed")
    for fact in facts:
        path = _ROOT / fact["relative_path"]
        raw = _read_regular_symlink_free(path)
        if not (
            len(raw) == fact["byte_count"]
            and _sha256(raw) == fact["sha256"]
        ):
            _fail("materialization producer source bytes changed")


@dataclass(frozen=True, slots=True)
class FrozenFullGroundFallbackMaterializedSourceV180r7r1:
    canonical_bytes: bytes
    materialization_manifest_id: str
    materialized_source_tree_id: str
    source_closure_id: str
    source_root: Path

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            _fail("retained materialization manifest is not one document")
        return document


def load_frozen_full_ground_fallback_materialized_source_v180r7r1(
) -> FrozenFullGroundFallbackMaterializedSourceV180r7r1:
    """Replay the exact manifest, tree inventory, bytes, and V2 closure."""

    if os.path.lexists(_FAILURE_PATH):
        _fail("V180r7r1 materialization failure evidence is present")
    raw = _read_regular_symlink_free(_MANIFEST_PATH)
    document = loads_canonical_json(raw)
    if not (
        type(document) is dict
        and canonical_json_bytes(document) == raw
        and set(document) == _TOP_LEVEL_FIELDS
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and _sha256(raw) == EXPECTED_CANONICAL_SHA256
        and document["schema"]
        == "acfqp.full_ground_fallback_materialized_source_tree_manifest.v180r7r1m1"
        and document["materialization_manifest_domain"] == _MANIFEST_DOMAIN
        and document["materialization_manifest_id"]
        == EXPECTED_MATERIALIZATION_MANIFEST_ID
        and _content_id(
            _MANIFEST_DOMAIN,
            document,
            "materialization_manifest_id",
        )
        == EXPECTED_MATERIALIZATION_MANIFEST_ID
    ):
        _fail("retained materialization manifest identity changed")

    tree = document["materialized_source_tree"]
    closure = document["unchanged_v2_source_closure"]
    if not (
        type(tree) is dict
        and set(tree) == _TREE_FIELDS
        and tree["schema"]
        == "acfqp.full_ground_fallback_materialized_source_tree.v180r7r1m1"
        and tree["materialized_source_tree_domain"] == _TREE_DOMAIN
        and tree["materialized_source_tree_id"]
        == EXPECTED_MATERIALIZED_SOURCE_TREE_ID
        and document["materialized_source_tree_id"]
        == EXPECTED_MATERIALIZED_SOURCE_TREE_ID
        and _content_id(_TREE_DOMAIN, tree, "materialized_source_tree_id")
        == EXPECTED_MATERIALIZED_SOURCE_TREE_ID
        and type(closure) is dict
        and closure["closure_id"] == EXPECTED_SOURCE_CLOSURE_ID
        and document["unchanged_v2_source_closure_id"]
        == EXPECTED_SOURCE_CLOSURE_ID
    ):
        _fail("retained materialized tree or closure identity changed")

    facts = tree["reachable_source_facts"]
    if not (
        type(facts) is list
        and len(facts) == EXPECTED_REACHABLE_MODULE_COUNT
        and all(type(row) is dict and set(row) == _SOURCE_FACT_FIELDS for row in facts)
        and [row["module_name"] for row in facts]
        == sorted({row["module_name"] for row in facts})
        and sum(row["source_byte_count"] for row in facts)
        == EXPECTED_REACHABLE_SOURCE_BYTE_COUNT
        and _sha256(canonical_json_bytes(facts))
        == EXPECTED_REACHABLE_SOURCE_FACTS_SHA256
        and tree["reachable_source_facts_sha256"]
        == EXPECTED_REACHABLE_SOURCE_FACTS_SHA256
        and tree["materialized_source_file_count"]
        == EXPECTED_REACHABLE_MODULE_COUNT
        and tree["materialized_source_byte_count"]
        == EXPECTED_REACHABLE_SOURCE_BYTE_COUNT
    ):
        _fail("retained materialized source facts changed")

    if not (
        document["source_catalog_manifest_id"]
        == EXPECTED_SOURCE_CATALOG_MANIFEST_ID
        and document["source_catalog_manifest_canonical_byte_count"]
        == EXPECTED_SOURCE_CATALOG_CANONICAL_BYTE_COUNT
        and document["source_catalog_manifest_canonical_sha256"]
        == EXPECTED_SOURCE_CATALOG_CANONICAL_SHA256
        and document["source_boundary_commit"]
        == EXPECTED_SOURCE_BOUNDARY_COMMIT
        and document["source_inventory_preregistration_id"]
        == EXPECTED_SOURCE_INVENTORY_PREREGISTRATION_ID
        and document["source_closure_repair_id"]
        == EXPECTED_SOURCE_CLOSURE_REPAIR_ID
        and tree["source_catalog_manifest_id"]
        == EXPECTED_SOURCE_CATALOG_MANIFEST_ID
        and tree["source_boundary_commit"] == EXPECTED_SOURCE_BOUNDARY_COMMIT
        and tree["source_inventory_preregistration_id"]
        == EXPECTED_SOURCE_INVENTORY_PREREGISTRATION_ID
        and tree["source_closure_repair_id"]
        == EXPECTED_SOURCE_CLOSURE_REPAIR_ID
        and tree["source_closure_id"] == EXPECTED_SOURCE_CLOSURE_ID
        and document["materialized_root_relative_path"]
        == ".tmp/exact-freeze/v180r7r1_materialized_source"
        and tree["materialized_root_relative_path"]
        == ".tmp/exact-freeze/v180r7r1_materialized_source"
        and tree["materialized_source_root_relative_path"]
        == ".tmp/exact-freeze/v180r7r1_materialized_source/src/acfqp"
        and document["manifest_output_relative_path"]
        == ".tmp/exact-freeze/v180r7r1_materialized_source_manifest.json"
    ):
        _fail("retained materialization lineage or paths changed")

    _verify_producer_source_facts(document)
    if document["construction_work"] != _CONSTRUCTION_WORK:
        _fail("retained one-time construction-work accounting changed")
    if not (
        document["write_once_o_excl_required"] is True
        and document["file_fsync_required"] is True
        and document["directory_fsync_required"] is True
        and document["same_materialization_identity_rerun_after_progress_forbidden"]
        is True
        and tree["only_exact_reachable_source_facts_materialized"] is True
        and tree["candidate_catalog_unreachable_files_materialized"] is False
        and tree["source_bytes_executed"] is False
        and tree["construction_only"] is True
        and document["fresh_execution_authorization_issued"] is False
        and document["fallback_occurrence_started"] is False
        and document["scientific_occurrence_executed"] is False
        and document["production_outcome_accessed"] is False
        and document["counter_records_issued"] is False
        and document["route_work_vectors_issued"] is False
        and document["comparison_vectors_issued"] is False
        and document["producer_free_verification_present"] is False
        and document["success_claimed"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
        and document["BREAK_EVEN_GATE"] == "NOT_RUN"
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["official_execution_allowed"] is False
        and document["construction_only"] is True
    ):
        _fail("retained materialization claim locks changed")

    replay = _read_and_replay_source_closure(
        root=_SOURCE_ROOT,
        facts=facts,
        expected_closure=closure,
    )
    if replay["closure_id"] != EXPECTED_SOURCE_CLOSURE_ID:
        _fail("materialized source closure replay identity changed")
    return FrozenFullGroundFallbackMaterializedSourceV180r7r1(
        raw,
        EXPECTED_MATERIALIZATION_MANIFEST_ID,
        EXPECTED_MATERIALIZED_SOURCE_TREE_ID,
        EXPECTED_SOURCE_CLOSURE_ID,
        _SOURCE_ROOT,
    )


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_MATERIALIZATION_MANIFEST_ID",
    "EXPECTED_MATERIALIZED_SOURCE_TREE_ID",
    "EXPECTED_REACHABLE_MODULE_COUNT",
    "EXPECTED_REACHABLE_SOURCE_BYTE_COUNT",
    "EXPECTED_SOURCE_CLOSURE_ID",
    "FrozenFullGroundFallbackMaterializedSourceV180r7r1",
    "FullGroundFallbackMaterializedSourceEvidenceFreezeV180r7r1Error",
    "load_frozen_full_ground_fallback_materialized_source_v180r7r1",
)
