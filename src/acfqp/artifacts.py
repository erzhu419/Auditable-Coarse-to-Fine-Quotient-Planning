"""Deterministic artifact serialization and integrity manifests."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from enum import Enum
from fractions import Fraction
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Mapping


SCHEMA_VERSION = "phase05.v1"

PHASE05_DOCUMENT_CONTRACTS = {
    "run.json": ("run_metadata", "acfqp.run@phase05.v1"),
    "config/structural.json": ("structural_config", "acfqp.structural_config@phase05.v1"),
    "config/query.json": ("query_config", "acfqp.query_config@phase05.v1"),
    "ground/enumeration.json": ("exact_enumeration", "acfqp.enumeration@phase05.v1"),
    "ground/j0_frontier.json": ("ground_oracle_frontier", "acfqp.frontier@phase05.v1"),
    "rapm/partition_before.json": ("coarse_partition", "acfqp.partition@phase05.v1"),
    "rapm/nominal_before.json": ("nominal_model", "acfqp.nominal_model@phase05.v1"),
    "rapm/envelope_before.json": ("sound_envelope", "acfqp.exact_envelope@phase05.v1"),
    "audit/pre_refinement.json": ("exact_audit", "acfqp.audit@phase05.v1"),
    "refinement/witness.json": ("counterexample_witness", "acfqp.witness@phase05.v1"),
    "refinement/candidates.json": ("split_candidates", "acfqp.split_candidates@phase05.v1"),
    "refinement/accepted_split.json": ("accepted_split", "acfqp.accepted_split@phase05.v1"),
    "rapm/partition_after.json": ("refined_partition", "acfqp.partition@phase05.v1"),
    "rapm/nominal_after.json": ("nominal_model", "acfqp.nominal_model@phase05.v1"),
    "rapm/envelope_after.json": ("sound_envelope", "acfqp.exact_envelope@phase05.v1"),
    "result/policy_graph.json": ("query_policy_graph", "acfqp.policy_graph@phase05.v1"),
    "result/certificate_or_fallback.json": ("terminal_result", "acfqp.result@phase05.v1"),
    "metrics.json": ("run_metrics", "acfqp.metrics@phase05.v1"),
    "events.jsonl": ("event_log", "application/x-ndjson; profile=acfqp.events.phase05.v1"),
}

PHASE05_REQUIRED_PATHS = tuple(PHASE05_DOCUMENT_CONTRACTS)


D4_BASELINE_DOCUMENT_CONTRACTS = {
    "run.json": PHASE05_DOCUMENT_CONTRACTS["run.json"],
    "config/structural.json": PHASE05_DOCUMENT_CONTRACTS["config/structural.json"],
    "config/query.json": PHASE05_DOCUMENT_CONTRACTS["config/query.json"],
    "ground/enumeration.json": PHASE05_DOCUMENT_CONTRACTS["ground/enumeration.json"],
    "ground/j0_frontier.json": PHASE05_DOCUMENT_CONTRACTS["ground/j0_frontier.json"],
    "ground/state_time_graph.json": (
        "complete_state_time_graph",
        "acfqp.state_time_graph@exact_d4.v1",
    ),
    "symmetry/profile.json": ("known_group_profile", "acfqp.d4_profile@v1"),
    "symmetry/automorphism_checks.json": (
        "exhaustive_automorphism_checks",
        "acfqp.d4_automorphism_checks@v1",
    ),
    "symmetry/state_orbits.json": (
        "state_time_orbit_partition",
        "acfqp.d4_state_orbits@v1",
    ),
    "symmetry/canonicalizers.json": (
        "canonicalizer_evidence",
        "acfqp.d4_canonicalizers@v1",
    ),
    "symmetry/action_orbits.json": (
        "stabilizer_action_orbits",
        "acfqp.d4_action_orbits@v1",
    ),
    "symmetry/concretizers.json": (
        "distinct_action_concretizers",
        "acfqp.d4_concretizers@v1",
    ),
    "rapm/nominal_exact.json": (
        "exact_point_quotient_model",
        "acfqp.exact_d4_nominal@v1",
    ),
    "rapm/envelope_exact.json": (
        "singleton_sound_envelope",
        "acfqp.exact_d4_envelope@v1",
    ),
    "audit/representative_independence.json": (
        "representative_independence_proof",
        "acfqp.d4_representative_audit@v1",
    ),
    "audit/value_policy_preservation.json": (
        "value_policy_preservation_proof",
        "acfqp.d4_value_policy_audit@v1",
    ),
    "result/policy_graph.json": PHASE05_DOCUMENT_CONTRACTS["result/policy_graph.json"],
    "result/exact_d4_certificate.json": (
        "exact_d4_certificate",
        "acfqp.exact_d4_certificate@v1",
    ),
    "metrics.json": PHASE05_DOCUMENT_CONTRACTS["metrics.json"],
    "events.jsonl": (
        "event_log",
        "application/x-ndjson; profile=acfqp.events.exact_d4.v1",
    ),
}

D4_BASELINE_REQUIRED_PATHS = tuple(D4_BASELINE_DOCUMENT_CONTRACTS)


ALIASED_CEGAR_DOCUMENT_CONTRACTS = {
    "run.json": ("run_metadata", "acfqp.run@aliased_cegar.v1"),
    "config/structural.json": (
        "structural_config",
        "acfqp.structural_config@aliased_cegar.v1",
    ),
    "config/profile.json": (
        "aliased_cegar_profile",
        "acfqp.profile@aliased_cegar.v1",
    ),
    "config/query.json": ("query_config", "acfqp.query_config@aliased_cegar.v1"),
    "ground/enumeration.json": (
        "exact_enumeration",
        "acfqp.enumeration@aliased_cegar.v1",
    ),
    "ground/j0_frontier.json": (
        "ground_oracle_frontier",
        "acfqp.frontier@aliased_cegar.v1",
    ),
    "audit/alias_source_diagnostic.json": (
        "alias_source_diagnostic",
        "acfqp.alias_source_diagnostic@aliased_cegar.v1",
    ),
    "rapm/partition_00.json": (
        "stage_00_partition",
        "acfqp.partition_00@aliased_cegar.v1",
    ),
    "rapm/nominal_00.json": (
        "stage_00_nominal_model",
        "acfqp.nominal_00@aliased_cegar.v1",
    ),
    "rapm/envelope_00.json": (
        "stage_00_sound_envelope",
        "acfqp.envelope_00@aliased_cegar.v1",
    ),
    "audit/audit_00.json": (
        "stage_00_exact_audit",
        "acfqp.audit_00@aliased_cegar.v1",
    ),
    "rapm/partition_01.json": (
        "stage_01_partition",
        "acfqp.partition_01@aliased_cegar.v1",
    ),
    "rapm/nominal_01.json": (
        "stage_01_nominal_model",
        "acfqp.nominal_01@aliased_cegar.v1",
    ),
    "rapm/envelope_01.json": (
        "stage_01_sound_envelope",
        "acfqp.envelope_01@aliased_cegar.v1",
    ),
    "audit/audit_01.json": (
        "stage_01_exact_audit",
        "acfqp.audit_01@aliased_cegar.v1",
    ),
    "rapm/partition_02.json": (
        "stage_02_partition",
        "acfqp.partition_02@aliased_cegar.v1",
    ),
    "rapm/nominal_02.json": (
        "stage_02_nominal_model",
        "acfqp.nominal_02@aliased_cegar.v1",
    ),
    "rapm/envelope_02.json": (
        "stage_02_sound_envelope",
        "acfqp.envelope_02@aliased_cegar.v1",
    ),
    "audit/audit_02.json": (
        "stage_02_exact_audit",
        "acfqp.audit_02@aliased_cegar.v1",
    ),
    "refinement/iterations/001/witness.json": (
        "iteration_001_counterexample_witness",
        "acfqp.witness_001@aliased_cegar.v1",
    ),
    "refinement/iterations/001/candidates.json": (
        "iteration_001_split_candidates",
        "acfqp.candidates_001@aliased_cegar.v1",
    ),
    "refinement/iterations/001/accepted_split.json": (
        "iteration_001_accepted_split",
        "acfqp.accepted_split_001@aliased_cegar.v1",
    ),
    "refinement/iterations/002/witness.json": (
        "iteration_002_counterexample_witness",
        "acfqp.witness_002@aliased_cegar.v1",
    ),
    "refinement/iterations/002/candidates.json": (
        "iteration_002_split_candidates",
        "acfqp.candidates_002@aliased_cegar.v1",
    ),
    "refinement/iterations/002/accepted_split.json": (
        "iteration_002_accepted_split",
        "acfqp.accepted_split_002@aliased_cegar.v1",
    ),
    "result/policy_graph.json": (
        "query_policy_graph",
        "acfqp.policy_graph@aliased_cegar.v1",
    ),
    "result/cegar_certificate.json": (
        "aliased_cegar_certificate",
        "acfqp.certificate@aliased_cegar.v1",
    ),
    "metrics.json": ("run_metrics", "acfqp.metrics@aliased_cegar.v1"),
    "events.jsonl": ("event_log", "acfqp.events@aliased_cegar.v1"),
}

ALIASED_CEGAR_REQUIRED_PATHS = tuple(ALIASED_CEGAR_DOCUMENT_CONTRACTS)


def _document_contracts_for_required_paths(
    required_paths: set[str],
) -> Mapping[str, tuple[str, str]]:
    """Select the exact document contract identified by a required-path set."""

    if required_paths == set(D4_BASELINE_REQUIRED_PATHS):
        return D4_BASELINE_DOCUMENT_CONTRACTS
    if required_paths == set(ALIASED_CEGAR_REQUIRED_PATHS):
        return ALIASED_CEGAR_DOCUMENT_CONTRACTS
    return PHASE05_DOCUMENT_CONTRACTS


def to_jsonable(value: Any) -> Any:
    """Convert project objects to stable, JSON-compatible values."""

    if dataclasses.is_dataclass(value):
        return {
            field.name: to_jsonable(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(key): to_jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        converted = [to_jsonable(item) for item in value]
        return sorted(converted, key=canonical_json)
    if isinstance(value, float):
        if value == 0.0:
            return 0.0
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return repr(value)


def canonical_json(value: Any) -> str:
    return json.dumps(
        to_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def canonical_sha256(value: Any) -> str:
    """Return a full SHA-256 over the canonical JSON representation."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def object_id(value: Any, prefix: str = "obj") -> str:
    digest = canonical_sha256(value)
    return f"{prefix}-{digest[:16]}"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_jsonable(value), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, values: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(values, (tuple, list)):
        raise TypeError("a .jsonl artifact must be a sequence of records")
    path.write_text(
        "".join(canonical_json(record) + "\n" for record in values),
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(filename: str) -> PurePosixPath:
    relative = PurePosixPath(filename)
    if relative.is_absolute() or not relative.parts or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise ValueError(f"unsafe artifact path: {filename!r}")
    if relative.suffix not in {".json", ".jsonl"}:
        raise ValueError(f"artifact must be .json or .jsonl: {filename!r}")
    return relative


def write_artifact_bundle(
    output_dir: Path,
    documents: Mapping[str, Any],
    *,
    roles: Mapping[str, str] | None = None,
    schemas: Mapping[str, str] | None = None,
    required_paths: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Write JSON documents and a hash manifest, returning the manifest."""

    output_dir.mkdir(parents=True, exist_ok=True)
    missing = sorted(set(required_paths) - set(documents))
    if missing:
        raise ValueError(f"required artifact documents missing: {missing}")
    document_contracts = _document_contracts_for_required_paths(set(required_paths))
    files = []
    for filename, document in sorted(documents.items()):
        relative = _safe_relative_path(filename)
        path = output_dir.joinpath(*relative.parts)
        if relative.suffix == ".jsonl":
            write_jsonl(path, document)
            default_schema = "application/x-ndjson"
        else:
            write_json(path, document)
            default_schema = SCHEMA_VERSION
        contract = document_contracts.get(filename)
        files.append(
            {
                "path": filename,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "role": (roles or {}).get(
                    filename, contract[0] if contract else "phase05_record"
                ),
                "schema": (schemas or {}).get(
                    filename, contract[1] if contract else default_schema
                ),
                "required": filename in required_paths,
            }
        )
    manifest = {
        "schema": "acfqp.manifest@phase05.v1",
        "schema_version": SCHEMA_VERSION,
        "required_paths": sorted(required_paths),
        "files": files,
        "bundle_sha256": canonical_sha256(files),
    }
    write_json(output_dir / "manifest.json", manifest)
    (output_dir / "manifest.sha256").write_text(
        sha256_file(output_dir / "manifest.json") + "  manifest.json\n",
        encoding="ascii",
    )
    return manifest


def _validate_exact_numbers(value: Any, location: str, failures: list[str]) -> None:
    """Validate every serialized Fraction-shaped object recursively."""

    if isinstance(value, dict):
        if "numerator" in value or "denominator" in value:
            if set(value) != {"numerator", "denominator"}:
                failures.append(f"noncanonical rational keys at {location}")
                return
            numerator = value["numerator"]
            denominator = value["denominator"]
            if (
                isinstance(numerator, bool)
                or isinstance(denominator, bool)
                or not isinstance(numerator, int)
                or not isinstance(denominator, int)
            ):
                failures.append(f"non-integer rational at {location}")
                return
            if denominator <= 0:
                failures.append(f"non-positive rational denominator at {location}")
                return
            if math.gcd(abs(numerator), denominator) != 1:
                failures.append(f"unreduced rational at {location}")
                return
        for key, item in value.items():
            _validate_exact_numbers(item, f"{location}.{key}", failures)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_exact_numbers(item, f"{location}[{index}]", failures)


def verify_artifact_bundle(output_dir: Path) -> list[str]:
    """Return integrity failures; an empty list means the bundle verifies."""

    manifest_path = output_dir / "manifest.json"
    if not manifest_path.is_file():
        return ["manifest.json is missing"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    detached = output_dir / "manifest.sha256"
    if not detached.is_file():
        failures.append("manifest.sha256 is missing")
    else:
        expected_detached = detached.read_text(encoding="ascii").split()[0]
        if sha256_file(manifest_path) != expected_detached:
            failures.append("detached manifest hash mismatch")
    records = manifest.get("files", [])
    if not isinstance(records, list):
        return failures + ["manifest files must be a list"]
    declared_list = [record.get("path") for record in records if isinstance(record, dict)]
    declared_paths = set(declared_list)
    if len(declared_paths) != len(declared_list):
        failures.append("manifest contains duplicate paths")
    required_paths = set(manifest.get("required_paths", []))
    document_contracts = _document_contracts_for_required_paths(required_paths)
    for required in sorted(required_paths - declared_paths):
        failures.append(f"required path absent from manifest: {required}")
    actual_paths = {
        path.relative_to(output_dir).as_posix()
        for path in output_dir.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "manifest.sha256"}
    }
    for extra in sorted(actual_paths - declared_paths):
        failures.append(f"unmanifested: {extra}")
    for record in records:
        if not isinstance(record, dict):
            failures.append("manifest file record must be an object")
            continue
        required_keys = {"path", "bytes", "sha256", "role", "schema", "required"}
        if set(record) != required_keys:
            failures.append(f"manifest record has wrong fields: {record.get('path')!r}")
            continue
        try:
            relative = _safe_relative_path(record["path"])
        except ValueError as error:
            failures.append(str(error))
            continue
        path = output_dir.joinpath(*relative.parts)
        if not path.is_file():
            failures.append(f"missing: {record['path']}")
            continue
        if path.stat().st_size != record["bytes"]:
            failures.append(f"size mismatch: {record['path']}")
        if sha256_file(path) != record["sha256"]:
            failures.append(f"hash mismatch: {record['path']}")
        if record["required"] != (record["path"] in required_paths):
            failures.append(f"required flag mismatch: {record['path']}")
        contract = document_contracts.get(record["path"])
        if required_paths and contract:
            expected_role, expected_schema = contract
            if record["role"] != expected_role:
                failures.append(f"role mismatch: {record['path']}")
            if record["schema"] != expected_schema:
                failures.append(f"schema mismatch: {record['path']}")
        try:
            if relative.suffix == ".json":
                parsed = json.loads(path.read_text(encoding="utf-8"))
                _validate_exact_numbers(parsed, record["path"], failures)
            else:
                for line_number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), start=1
                ):
                    parsed = json.loads(line)
                    _validate_exact_numbers(
                        parsed, f"{record['path']}:{line_number}", failures
                    )
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            failures.append(f"invalid JSON: {record['path']}: {error}")
    expected_bundle = canonical_sha256(records)
    if expected_bundle != manifest.get("bundle_sha256"):
        failures.append("bundle hash mismatch")
    return failures
