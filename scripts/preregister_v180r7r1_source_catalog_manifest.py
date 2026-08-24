#!/usr/bin/env python3
"""Write the outcome-free V180r7r1 source-catalog manifest exactly once.

The source boundary is the already committed V180r7r1 repair slice.  This
script is intentionally outside ``src/acfqp`` so its computed manifest ID and
future source changes cannot feed back into the catalogue that it freezes.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import subprocess
from typing import Any, NoReturn

from acfqp import construction_k7_full_ground_fallback_source_inventory_preregistration_v180r7r1 as preregistration
from acfqp import construction_k7_recovery_eligible_source_closure_successor_v180r7r1 as selector
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src" / "acfqp"
OUTPUT_PATH = (
    ROOT / ".tmp" / "exact-freeze" / "v180r7r1_source_catalog_manifest.json"
)
SOURCE_BOUNDARY_COMMIT = "0d9d32dcb2aa3652696ccc0b5010dfc39455e8af"
SOURCE_INVENTORY_PREREGISTRATION_ID = (
    "30a0aa732e44389f9b246a3664bacf13f5465233c7a1e3a1782baac80dbf38b8"
)
SOURCE_CATALOG_MANIFEST_DOMAIN = (
    "acfqp:construction-k7-full-ground-fallback-source-catalog-manifest:"
    "v180r7r1"
)
EXPECTED_SOURCE_MODULE_COUNT = 1_955
EXPECTED_SOURCE_BYTE_COUNT = 49_484_313
EXPECTED_ROOT_MODULE_COUNT = 151
EXPECTED_REACHABLE_MODULE_COUNT = 307
EXPECTED_REACHABLE_SOURCE_BYTE_COUNT = 15_129_926
MAXIMUM_MANIFEST_BYTES = 32 * 1024 * 1024


class V180r7r1SourceCatalogManifestError(RuntimeError):
    """The committed namespace, repair, or durable write boundary changed."""


def _fail(message: str) -> NoReturn:
    raise V180r7r1SourceCatalogManifestError(message)


def _git(*arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ("git", *arguments),
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise V180r7r1SourceCatalogManifestError(
            "git source-boundary replay could not start"
        ) from error
    if completed.returncode != 0:
        diagnostic = completed.stderr[-4_096:].decode("utf-8", errors="replace")
        _fail(f"git source-boundary replay failed: {diagnostic}")
    return completed.stdout


def _content_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        SOURCE_CATALOG_MANIFEST_DOMAIN.encode()
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()


def _module_name(relative_path: str) -> str:
    if not relative_path.startswith("src/acfqp/") or not relative_path.endswith(
        ".py"
    ):
        _fail("committed source path is outside the ACFQP Python namespace")
    parts = list(Path(relative_path).relative_to("src").with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    value = ".".join(parts)
    if not (
        value == "acfqp"
        or value.startswith("acfqp.")
        and all(part.isidentifier() for part in value.split("."))
    ):
        _fail("committed source path does not encode one valid module")
    return value


def _committed_python_paths() -> tuple[str, ...]:
    resolved = _git("rev-parse", SOURCE_BOUNDARY_COMMIT).strip().decode("ascii")
    if resolved != SOURCE_BOUNDARY_COMMIT:
        _fail("source-boundary commit identity changed")
    _git("merge-base", "--is-ancestor", SOURCE_BOUNDARY_COMMIT, "HEAD")
    _git("diff", "--quiet", SOURCE_BOUNDARY_COMMIT, "--", "src/acfqp")
    raw = _git(
        "ls-tree",
        "-r",
        "-z",
        "--name-only",
        SOURCE_BOUNDARY_COMMIT,
        "--",
        "src/acfqp",
    )
    try:
        values = tuple(
            item.decode("utf-8", errors="strict")
            for item in raw.split(b"\x00")
            if item
        )
    except UnicodeError as error:
        raise V180r7r1SourceCatalogManifestError(
            "committed source path is not strict UTF-8"
        ) from error
    python_paths = tuple(value for value in values if value.endswith(".py"))
    if python_paths != tuple(sorted(set(python_paths))):
        _fail("committed Python source inventory is unsorted or duplicated")
    return python_paths


def _catalogue() -> tuple[
    dict[str, bytes],
    dict[str, str],
    list[dict[str, Any]],
]:
    committed_paths = _committed_python_paths()
    live_paths = tuple(
        path.relative_to(ROOT).as_posix()
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
    )
    if live_paths != committed_paths:
        _fail("live ACFQP namespace differs from the source-boundary commit")
    sources: dict[str, bytes] = {}
    paths: dict[str, str] = {}
    facts: list[dict[str, Any]] = []
    for relative_path in committed_paths:
        path = ROOT / relative_path
        try:
            path_stat = os.lstat(path)
        except OSError as error:
            raise V180r7r1SourceCatalogManifestError(
                "committed source path is absent"
            ) from error
        if stat.S_ISLNK(path_stat.st_mode) or not stat.S_ISREG(path_stat.st_mode):
            _fail("committed source path is linked or nonregular")
        module_name = _module_name(relative_path)
        raw = path.read_bytes()
        if not raw or module_name in sources:
            _fail("committed module is empty or duplicated")
        archive_relative_path = Path(relative_path).relative_to("src").as_posix()
        fact = {
            "module_name": module_name,
            "relative_path": archive_relative_path,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "source_byte_count": len(raw),
        }
        sources[module_name] = raw
        paths[module_name] = str(path.resolve(strict=True))
        facts.append(fact)
    if not (
        len(facts) == EXPECTED_SOURCE_MODULE_COUNT
        and sum(row["source_byte_count"] for row in facts)
        == EXPECTED_SOURCE_BYTE_COUNT
        and [row["module_name"] for row in facts]
        == sorted({row["module_name"] for row in facts})
    ):
        _fail("committed source-catalog denominator changed")
    return sources, paths, facts


def build_v180r7r1_source_catalog_manifest() -> dict[str, Any]:
    frozen_preregistration = (
        preregistration.freeze_full_ground_fallback_source_inventory_preregistration_v180r7r1()
    )
    if frozen_preregistration.preregistration_id != SOURCE_INVENTORY_PREREGISTRATION_ID:
        _fail("source-inventory preregistration identity changed")
    sources, paths, facts = _catalogue()
    repair = selector.build_recovery_eligible_source_closure_successor_v180r7r1(
        module_sources=sources,
        module_paths=paths,
    )
    repair_document = repair.to_document()
    facts_sha256 = hashlib.sha256(canonical_json_bytes(facts)).hexdigest()
    candidate = repair_document["candidate_catalog"]
    reachable = repair_document["reachable_runtime"]
    if not (
        candidate["module_count"] == EXPECTED_SOURCE_MODULE_COUNT
        and candidate["source_byte_count"] == EXPECTED_SOURCE_BYTE_COUNT
        and candidate["source_facts_sha256"] == facts_sha256
        and len(repair_document["root_modules"]) == EXPECTED_ROOT_MODULE_COUNT
        and reachable["module_count"] == EXPECTED_REACHABLE_MODULE_COUNT
        and reachable["source_byte_count"]
        == EXPECTED_REACHABLE_SOURCE_BYTE_COUNT
        and repair_document["scientific_occurrence_executed"] is False
        and repair_document["target_outcomes_accessed"] is False
        and repair_document["official_execution_allowed"] is False
    ):
        _fail("source-closure repair differs from its preregistered denominator")
    source_tree_id = _git(
        "rev-parse", f"{SOURCE_BOUNDARY_COMMIT}:src/acfqp"
    ).strip().decode("ascii")
    producer_raw = Path(__file__).read_bytes()
    payload = {
        "schema": "acfqp.full_ground_fallback_source_catalog_manifest.v180r7r1",
        "source_catalog_manifest_domain": SOURCE_CATALOG_MANIFEST_DOMAIN,
        "source_boundary_commit": SOURCE_BOUNDARY_COMMIT,
        "source_boundary_tree_id": source_tree_id,
        "source_root_relative_path": "src/acfqp",
        "source_inventory_preregistration_id": (
            frozen_preregistration.preregistration_id
        ),
        "source_inventory_preregistration_canonical_sha256": (
            preregistration.EXPECTED_CANONICAL_SHA256
        ),
        "source_catalog_module_count": len(facts),
        "source_catalog_source_byte_count": sum(
            row["source_byte_count"] for row in facts
        ),
        "source_catalog_facts_sha256": facts_sha256,
        "source_catalog_facts": facts,
        "source_closure_repair_id": repair.repair_id,
        "source_closure_repair": repair_document,
        "manifest_producer_source_fact": {
            "relative_path": Path(__file__).relative_to(ROOT).as_posix(),
            "byte_count": len(producer_raw),
            "sha256": hashlib.sha256(producer_raw).hexdigest(),
            "excluded_from_frozen_worker_source_catalog": True,
        },
        "manifest_identity_hardcoded_in_catalogued_source": False,
        "manifest_output_relative_path": OUTPUT_PATH.relative_to(ROOT).as_posix(),
        "write_once_o_excl_required": True,
        "file_fsync_required": True,
        "directory_fsync_required": True,
        "same_manifest_identity_rerun_after_progress_forbidden": True,
        "fresh_execution_authorization_issued": False,
        "fresh_fallback_execution_started": False,
        "scientific_occurrence_executed": False,
        "production_outcome_accessed": False,
        "producer_free_verification_present": False,
        "success_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "construction_only": True,
    }
    return {
        **payload,
        "source_catalog_manifest_id": _content_id(payload),
    }


def _write_once(path: Path, raw: bytes) -> None:
    if (
        path != OUTPUT_PATH
        and path.parent == OUTPUT_PATH.parent
    ):
        _fail("manifest write target changed within the evidence directory")
    if type(raw) is not bytes or not raw or len(raw) > MAXIMUM_MANIFEST_BYTES:
        _fail("manifest bytes are absent or over their finite cap")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        _fail("manifest output directory is absent or linked")
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
                raise OSError("V180r7r1 source-catalog manifest short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(
        parent,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> None:
    if OUTPUT_PATH.exists():
        _fail("V180r7r1 source-catalog manifest already exists")
    document = build_v180r7r1_source_catalog_manifest()
    raw = canonical_json_bytes(document)
    _write_once(OUTPUT_PATH, raw)
    print(
        "V180R7R1_SOURCE_CATALOG_MANIFEST",
        document["source_catalog_manifest_id"],
        len(raw),
        hashlib.sha256(raw).hexdigest(),
        flush=True,
    )


if __name__ == "__main__":
    main()
