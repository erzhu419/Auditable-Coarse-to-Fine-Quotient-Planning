"""Ground-free Phase-3E consumption of the frozen Phase-3C RAPM.

This module is deliberately below the ground-domain binding layer.  It reads
an integrity-verified Phase-3C bundle, validates the serialized RAPM,
BuildEpoch, and portable query selected by a registered key, and then plans
using only :class:`PortableRAPM` and :class:`PortableQuery`.

In particular, this module must not import ``acfqp.domains``,
``acfqp.frozen_phase3c``.  Historical plans/audits are parsed only as opaque
members of the pre-existing bundle semantic-hash verification; their contents
never influence query selection, planning, or routing.  A failed certificate
may cause a later orchestration layer to acquire a ground lease; that is
intentionally outside this source lease.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping
import weakref

from acfqp.artifacts import (
    PHASE3C_DOCUMENT_CONTRACTS,
    PHASE3C_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    serialized_json_bytes,
)
from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    RAPM_SOURCE_LEASE_DOMAIN,
    SELECTED_CONTINGENT_PLAN_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.portable import PortableQuery, PortableRAPM, canonical_json
from acfqp.portable_planner import (
    PortableParetoPoint,
    PortablePlanResult,
    solve_portable_pareto,
)


RAPM_SOURCE_LEASE_SCHEMA = "acfqp.rapm_source_lease.v1"
SELECTED_CONTINGENT_PLAN_SCHEMA = "acfqp.selected_contingent_plan.v1"

ABSTRACT_QUERY_KEY = "g2048.safe_chain.h1.delta0.abstract_control"
LOCAL_QUERY_KEY = "g2048.safe_chain.h2.delta05.local_recovery"
SUPPORTED_QUERY_KEYS = frozenset({ABSTRACT_QUERY_KEY, LOCAL_QUERY_KEY})

CONSTRAINED_SELECTOR_ID = "constrained_max_reward_then_min_risk_then_policy_signature.v1"
RECOVERY_SELECTOR_ID = "max_reward_then_min_risk_then_policy_signature.v1"

_EXPECTED_RUN_STATUS = {
    "schema_version": "phase3c.v1",
    "contract_version": "0.8.0",
    "profile_key": "phase3c_certificate_triggered_local_recovery_v0",
    "execution_profile": "phase3c_certificate_triggered_local_recovery",
    "status": "PHASE3C_LOCAL_RECOVERY_PASS",
    "local_hybrid_gate_status": "LOCAL_HYBRID_GATE_PASS",
    "full_phase3_gate_status": "PHASE3_AGGREGATE_NOT_RUN",
    "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
}

_EPOCH_FIELDS = frozenset(
    {
        "build_epoch_id",
        "structural_id",
        "kernel_sha256",
        "coverage_id",
        "coverage",
        "portable_rapm_id",
        "partition_id",
        "nominal_model_id",
        "sound_envelope_id",
        "concretizer_id",
        "construction_source",
        "consumption_is_query_neutral",
        "query_results_used_for_phase3c_build",
        "covered_ground_states",
        "ground_state_action_pairs",
        "abstract_cells",
        "abstract_state_action_pairs",
        "source_tree_sha256",
    }
)

_QUERY_STREAM_FIELDS = frozenset(
    {
        "ground_query_id",
        "occurrence_id",
        "portable_query",
        "portable_query_id",
        "query_key",
    }
)


class Phase3ERAPMConsumerError(ValueError):
    """The bundle cannot be admitted as a model-only RAPM source."""


@dataclass(frozen=True, slots=True)
class _Phase3CBundleSnapshotV1:
    """One immutable read-set used for every Phase-3C source check.

    A manifest check followed by ordinary path reads is not a provenance
    boundary: a file can be replaced between the two operations.  The loader
    therefore parses and hashes only these retained bytes, then compares every
    consumed path (and the directory topology) with this snapshot before it
    mints a live source authority.
    """

    bundle: Path
    manifest_bytes: bytes
    detached_manifest_bytes: bytes
    files: Mapping[str, bytes]
    actual_paths: tuple[str, ...]


def _read_source_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise Phase3ERAPMConsumerError(
            f"cannot read Phase3C source {path}: {error}"
        ) from error


def _bundle_actual_paths(bundle: Path) -> tuple[str, ...]:
    try:
        return tuple(
            sorted(
                path.relative_to(bundle).as_posix()
                for path in bundle.rglob("*")
                if path.is_file()
                and path.name not in {"manifest.json", "manifest.sha256"}
            )
        )
    except OSError as error:
        raise Phase3ERAPMConsumerError(
            f"cannot enumerate Phase3C source {bundle}: {error}"
        ) from error


def _acquire_bundle_snapshot_v1(bundle: Path) -> _Phase3CBundleSnapshotV1:
    """Read the complete, statically registered Phase-3C bundle once."""

    manifest_bytes = _read_source_bytes(bundle / "manifest.json")
    detached_bytes = _read_source_bytes(bundle / "manifest.sha256")
    files = {
        relative: _read_source_bytes(bundle / relative)
        for relative in PHASE3C_REQUIRED_PATHS
    }
    return _Phase3CBundleSnapshotV1(
        bundle=bundle,
        manifest_bytes=manifest_bytes,
        detached_manifest_bytes=detached_bytes,
        files=MappingProxyType(files),
        actual_paths=_bundle_actual_paths(bundle),
    )


def _recheck_bundle_snapshot_v1(snapshot: _Phase3CBundleSnapshotV1) -> None:
    """Fail closed if any consumed path changed during source acquisition."""

    current = {
        "manifest.json": _read_source_bytes(snapshot.bundle / "manifest.json"),
        "manifest.sha256": _read_source_bytes(
            snapshot.bundle / "manifest.sha256"
        ),
        **{
            relative: _read_source_bytes(snapshot.bundle / relative)
            for relative in PHASE3C_REQUIRED_PATHS
        },
    }
    expected = {
        "manifest.json": snapshot.manifest_bytes,
        "manifest.sha256": snapshot.detached_manifest_bytes,
        **dict(snapshot.files),
    }
    changed = sorted(path for path in expected if current[path] != expected[path])
    if changed:
        raise Phase3ERAPMConsumerError(
            "Phase3C source changed while loading: " + ", ".join(changed)
        )
    if _bundle_actual_paths(snapshot.bundle) != snapshot.actual_paths:
        raise Phase3ERAPMConsumerError(
            "Phase3C source topology changed while loading"
        )


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    """Apply the registered Phase-3E domain-separated identity rule."""

    try:
        return content_id(domain, dict(payload))
    except Phase3EIdentityError as error:
        raise Phase3ERAPMConsumerError(str(error)) from error


def _require_string(value: Any, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise Phase3ERAPMConsumerError(f"{field_name} must be a nonempty string")
    return value


def _require_nonnegative_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or type(value) is not int or value < 0:
        raise Phase3ERAPMConsumerError(
            f"{field_name} must be a nonnegative integer"
        )
    return value


def _load_json_object_bytes(
    source_bytes: bytes,
    *,
    source_name: str,
) -> dict[str, Any]:
    try:
        document = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Phase3ERAPMConsumerError(
            f"cannot parse JSON source {source_name}: {error}"
        ) from error
    if not isinstance(document, dict):
        raise Phase3ERAPMConsumerError(
            f"JSON source must be an object: {source_name}"
        )
    if source_bytes != serialized_json_bytes(document):
        raise Phase3ERAPMConsumerError(
            f"source is not in canonical artifact byte form: {source_name}"
        )
    return document


def _load_json_object(path: Path) -> tuple[dict[str, Any], bytes]:
    source_bytes = _read_source_bytes(path)
    return (
        _load_json_object_bytes(source_bytes, source_name=str(path)),
        source_bytes,
    )


def _load_jsonl_object_bytes(
    source_bytes: bytes,
    *,
    source_name: str,
) -> tuple[tuple[dict[str, Any], bytes], ...]:
    try:
        text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Phase3ERAPMConsumerError(
            f"cannot parse JSONL source {source_name}: {error}"
        ) from error
    if not text.endswith("\n"):
        raise Phase3ERAPMConsumerError(
            f"JSONL source lacks final newline: {source_name}"
        )
    rows: list[tuple[dict[str, Any], bytes]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            raise Phase3ERAPMConsumerError(
                f"JSONL source contains an empty row: {source_name}:{line_number}"
            )
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise Phase3ERAPMConsumerError(
                f"invalid JSONL row {source_name}:{line_number}: {error}"
            ) from error
        if not isinstance(document, dict):
            raise Phase3ERAPMConsumerError(
                f"JSONL row must be an object: {source_name}:{line_number}"
            )
        if line != canonical_json(document):
            raise Phase3ERAPMConsumerError(
                f"JSONL row is not canonical: {source_name}:{line_number}"
            )
        rows.append((document, line.encode("utf-8")))
    if not rows:
        raise Phase3ERAPMConsumerError(f"JSONL source is empty: {source_name}")
    return tuple(rows)


def _load_jsonl_objects(path: Path) -> tuple[tuple[dict[str, Any], bytes], ...]:
    return _load_jsonl_object_bytes(
        _read_source_bytes(path), source_name=str(path)
    )


def _validate_manifest_snapshot_v1(
    snapshot: _Phase3CBundleSnapshotV1,
) -> dict[str, Any]:
    """Verify topology and hashes solely against one retained read-set."""

    manifest = _load_json_object_bytes(
        snapshot.manifest_bytes, source_name="manifest.json"
    )
    if set(manifest) != {
        "schema",
        "schema_version",
        "required_paths",
        "files",
        "bundle_sha256",
    } or (
        manifest.get("schema") != "acfqp.manifest@phase05.v1"
        or manifest.get("schema_version") != "phase05.v1"
    ):
        raise Phase3ERAPMConsumerError(
            "source bundle has an unsupported manifest schema"
        )
    expected_detached = (
        hashlib.sha256(snapshot.manifest_bytes).hexdigest()
        + "  manifest.json\n"
    ).encode("ascii")
    if snapshot.detached_manifest_bytes != expected_detached:
        raise Phase3ERAPMConsumerError(
            "Phase3C bundle integrity failed: detached manifest hash mismatch"
        )
    if manifest.get("required_paths") != sorted(PHASE3C_REQUIRED_PATHS):
        raise Phase3ERAPMConsumerError(
            "source bundle is not the exact Phase3C artifact topology"
        )
    records = manifest.get("files")
    if not isinstance(records, list):
        raise Phase3ERAPMConsumerError("manifest files must be a list")
    if [
        record.get("path") if isinstance(record, dict) else None
        for record in records
    ] != sorted(PHASE3C_REQUIRED_PATHS):
        raise Phase3ERAPMConsumerError(
            "manifest file catalogue must use canonical path order"
        )
    by_path: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or type(record.get("path")) is not str:
            raise Phase3ERAPMConsumerError("manifest has an invalid file record")
        relative = record["path"]
        if relative in by_path:
            raise Phase3ERAPMConsumerError("manifest has duplicate file paths")
        by_path[relative] = record
    if set(by_path) != set(PHASE3C_REQUIRED_PATHS):
        raise Phase3ERAPMConsumerError("manifest file catalogue is not Phase3C")
    if set(snapshot.actual_paths) != set(PHASE3C_REQUIRED_PATHS):
        extra = sorted(set(snapshot.actual_paths) - set(PHASE3C_REQUIRED_PATHS))
        missing = sorted(set(PHASE3C_REQUIRED_PATHS) - set(snapshot.actual_paths))
        raise Phase3ERAPMConsumerError(
            "Phase3C bundle integrity failed: topology mismatch; "
            f"extra={extra!r}; missing={missing!r}"
        )
    for relative, (role, schema) in PHASE3C_DOCUMENT_CONTRACTS.items():
        record = by_path[relative]
        if set(record) != {
            "path",
            "bytes",
            "sha256",
            "role",
            "schema",
            "required",
        }:
            raise Phase3ERAPMConsumerError(
                f"manifest record has wrong fields for {relative}"
            )
        if (
            record.get("role") != role
            or record.get("schema") != schema
            or record.get("required") is not True
        ):
            raise Phase3ERAPMConsumerError(
                f"manifest contract mismatch for {relative}"
            )
        source_bytes = snapshot.files[relative]
        if (
            record.get("bytes") != len(source_bytes)
            or record.get("sha256")
            != hashlib.sha256(source_bytes).hexdigest()
        ):
            raise Phase3ERAPMConsumerError(
                f"Phase3C bundle integrity failed: bytes/hash mismatch: {relative}"
            )
        if relative.endswith(".jsonl"):
            _load_jsonl_object_bytes(source_bytes, source_name=relative)
        else:
            _load_json_object_bytes(source_bytes, source_name=relative)
    if manifest.get("bundle_sha256") != canonical_sha256(records):
        raise Phase3ERAPMConsumerError(
            "Phase3C bundle integrity failed: bundle hash mismatch"
        )
    return manifest


def _validate_manifest(bundle: Path) -> tuple[dict[str, Any], bytes]:
    """Compatibility helper backed by one complete bundle snapshot."""

    snapshot = _acquire_bundle_snapshot_v1(bundle)
    manifest = _validate_manifest_snapshot_v1(snapshot)
    _recheck_bundle_snapshot_v1(snapshot)
    return manifest, snapshot.manifest_bytes


def _stable_documents_for_semantic_hash(bundle: Path) -> dict[str, Any]:
    """Parse the legacy stable bundle solely to verify its semantic hash."""

    stable: dict[str, Any] = {}
    for relative in PHASE3C_REQUIRED_PATHS:
        if relative == "run.json":
            continue
        path = bundle / relative
        if relative.endswith(".jsonl"):
            stable[relative] = [
                document for document, _source_bytes in _load_jsonl_objects(path)
            ]
        else:
            stable[relative] = _load_json_object(path)[0]
    return stable


def _stable_documents_from_snapshot_v1(
    snapshot: _Phase3CBundleSnapshotV1,
) -> dict[str, Any]:
    stable: dict[str, Any] = {}
    for relative in PHASE3C_REQUIRED_PATHS:
        if relative == "run.json":
            continue
        source_bytes = snapshot.files[relative]
        if relative.endswith(".jsonl"):
            stable[relative] = [
                document
                for document, _row_bytes in _load_jsonl_object_bytes(
                    source_bytes, source_name=relative
                )
            ]
        else:
            stable[relative] = _load_json_object_bytes(
                source_bytes, source_name=relative
            )
    return stable


def _validate_run(snapshot: _Phase3CBundleSnapshotV1) -> dict[str, Any]:
    run = _load_json_object_bytes(
        snapshot.files["run.json"], source_name="run.json"
    )
    for field_name, expected in _EXPECTED_RUN_STATUS.items():
        if run.get(field_name) != expected:
            raise Phase3ERAPMConsumerError(
                f"Phase3C run status mismatch for {field_name}"
            )
    _require_string(run.get("run_id"), field_name="run.run_id")
    _require_string(run.get("semantic_hash"), field_name="run.semantic_hash")
    stable = _stable_documents_from_snapshot_v1(snapshot)
    if run["semantic_hash"] != canonical_sha256(stable):
        raise Phase3ERAPMConsumerError("Phase3C run semantic hash mismatch")
    run_payload = {
        field_name: value
        for field_name, value in run.items()
        if field_name not in {"run_id", "started_at", "finished_at"}
    }
    if run["run_id"] != object_id(run_payload, "run"):
        raise Phase3ERAPMConsumerError("Phase3C run ID mismatch")
    return run


def _validate_epoch(
    epoch: dict[str, Any], model: PortableRAPM
) -> None:
    try:
        require_exact_fields(epoch, _EPOCH_FIELDS, context="Phase3C BuildEpoch")
    except Phase3EIdentityError as error:
        raise Phase3ERAPMConsumerError(str(error)) from error
    epoch_payload = dict(epoch)
    claimed_id = epoch_payload.pop("build_epoch_id")
    if claimed_id != object_id(epoch_payload, "build-epoch"):
        raise Phase3ERAPMConsumerError("BuildEpoch legacy ID mismatch")

    model_document = model.to_dict()
    expected = {
        "coverage_id": model.coverage_id,
        "portable_rapm_id": model.model_id,
        "partition_id": object_id(model_document["partition"], "partition"),
        "nominal_model_id": object_id(model_document["nominal"], "nominal"),
        "sound_envelope_id": object_id(model_document["envelope"], "envelope"),
        "concretizer_id": object_id(
            model_document["concretizer_registry"], "concretizer"
        ),
        "covered_ground_states": len(model_document["state_catalog"]),
        "abstract_cells": len(model_document["partition"]),
        "abstract_state_action_pairs": len(model_document["nominal"]),
    }
    for field_name, expected_value in expected.items():
        if epoch.get(field_name) != expected_value:
            raise Phase3ERAPMConsumerError(
                f"BuildEpoch/model mismatch for {field_name}"
            )
    # The legacy epoch counts pre-deduplication state/action occurrences while
    # the portable catalogue stores unique content-addressed actions, so the
    # 144 count cannot be reconstructed by taking catalogue length (136).
    if epoch.get("ground_state_action_pairs") != 144:
        raise Phase3ERAPMConsumerError(
            "BuildEpoch ground_state_action_pairs is not the frozen Phase3C count"
        )
    if (
        epoch.get("consumption_is_query_neutral") is not True
        or epoch.get("query_results_used_for_phase3c_build") is not False
    ):
        raise Phase3ERAPMConsumerError(
            "BuildEpoch does not assert query-neutral model construction"
        )
    for field_name in ("kernel_sha256", "source_tree_sha256"):
        try:
            parse_content_id(epoch[field_name])
        except (KeyError, Phase3EIdentityError) as error:
            raise Phase3ERAPMConsumerError(
                f"BuildEpoch {field_name} is not a full SHA-256"
            ) from error


def _query_registry_binding(
    snapshot: _Phase3CBundleSnapshotV1,
    *,
    query_key: str,
    query_stream_record: Mapping[str, Any],
    model: PortableRAPM,
) -> dict[str, Any]:
    registry = _load_json_object_bytes(
        snapshot.files["workload/query_registry.json"],
        source_name="workload/query_registry.json",
    )
    records = registry.get("records")
    if not isinstance(records, list):
        raise Phase3ERAPMConsumerError("query registry records must be a list")
    matches = [
        record
        for record in records
        if isinstance(record, dict) and record.get("query_key") == query_key
    ]
    if len(matches) != 1:
        raise Phase3ERAPMConsumerError(
            "query registry must contain the selected key exactly once"
        )
    record = matches[0]
    # expected_route is intentionally neither read nor copied: it is a historical
    # expectation, not evidence for the model-only consumer's route.
    expected_bindings = {
        "ground_query_id": query_stream_record["ground_query_id"],
        "occurrence_id": query_stream_record["occurrence_id"],
        "portable_model_id": model.model_id,
        "portable_query_id": query_stream_record["portable_query_id"],
        "query_key": query_key,
    }
    for field_name, expected in expected_bindings.items():
        if record.get(field_name) != expected:
            raise Phase3ERAPMConsumerError(
                f"query registry/stream mismatch for {field_name}"
            )
    _require_nonnegative_int(record.get("ordinal"), field_name="query ordinal")
    return record


@dataclass(frozen=True, slots=True)
class RAPMSourceLeaseV1:
    """Content-addressed evidence for one model/query source acquisition."""

    query_key: str
    source_manifest_sha256: str
    source_bundle_sha256: str
    source_run_id: str
    source_semantic_hash: str
    legacy_structural_id: str
    kernel_sha256: str
    legacy_build_epoch_id: str
    build_epoch_sha256: str
    legacy_portable_rapm_id: str
    portable_rapm_sha256: str
    legacy_ground_query_id: str
    legacy_occurrence_id: str
    legacy_portable_query_id: str
    portable_query_sha256: str

    def __post_init__(self) -> None:
        if self.query_key not in SUPPORTED_QUERY_KEYS:
            raise Phase3ERAPMConsumerError("unsupported Phase3C query key")
        for field_name in (
            "source_manifest_sha256",
            "source_bundle_sha256",
            "source_semantic_hash",
            "kernel_sha256",
            "build_epoch_sha256",
            "portable_rapm_sha256",
            "portable_query_sha256",
        ):
            try:
                parse_content_id(getattr(self, field_name))
            except Phase3EIdentityError as error:
                raise Phase3ERAPMConsumerError(
                    f"{field_name} must be a full SHA-256"
                ) from error
        for field_name in (
            "source_run_id",
            "legacy_structural_id",
            "legacy_build_epoch_id",
            "legacy_portable_rapm_id",
            "legacy_ground_query_id",
            "legacy_occurrence_id",
            "legacy_portable_query_id",
        ):
            _require_string(getattr(self, field_name), field_name=field_name)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": RAPM_SOURCE_LEASE_SCHEMA,
            "query_key": self.query_key,
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_bundle_sha256": self.source_bundle_sha256,
            "source_run_id": self.source_run_id,
            "source_semantic_hash": self.source_semantic_hash,
            "legacy_structural_id": self.legacy_structural_id,
            "kernel_sha256": self.kernel_sha256,
            "legacy_build_epoch_id": self.legacy_build_epoch_id,
            "build_epoch_sha256": self.build_epoch_sha256,
            "legacy_portable_rapm_id": self.legacy_portable_rapm_id,
            "portable_rapm_sha256": self.portable_rapm_sha256,
            "legacy_ground_query_id": self.legacy_ground_query_id,
            "legacy_occurrence_id": self.legacy_occurrence_id,
            "legacy_portable_query_id": self.legacy_portable_query_id,
            "portable_query_sha256": self.portable_query_sha256,
        }

    @property
    def source_lease_id(self) -> str:
        return _content_id(RAPM_SOURCE_LEASE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {"source_lease_id": self.source_lease_id, **self._payload()}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "RAPMSourceLeaseV1":
        fields = {
            "source_lease_id",
            "schema",
            "query_key",
            "source_manifest_sha256",
            "source_bundle_sha256",
            "source_run_id",
            "source_semantic_hash",
            "legacy_structural_id",
            "kernel_sha256",
            "legacy_build_epoch_id",
            "build_epoch_sha256",
            "legacy_portable_rapm_id",
            "portable_rapm_sha256",
            "legacy_ground_query_id",
            "legacy_occurrence_id",
            "legacy_portable_query_id",
            "portable_query_sha256",
        }
        try:
            require_exact_fields(document, fields, context="RAPMSourceLeaseV1")
        except Phase3EIdentityError as error:
            raise Phase3ERAPMConsumerError(str(error)) from error
        if document["schema"] != RAPM_SOURCE_LEASE_SCHEMA:
            raise Phase3ERAPMConsumerError("unsupported source lease schema")
        lease = cls(
            query_key=document["query_key"],
            source_manifest_sha256=document["source_manifest_sha256"],
            source_bundle_sha256=document["source_bundle_sha256"],
            source_run_id=document["source_run_id"],
            source_semantic_hash=document["source_semantic_hash"],
            legacy_structural_id=document["legacy_structural_id"],
            kernel_sha256=document["kernel_sha256"],
            legacy_build_epoch_id=document["legacy_build_epoch_id"],
            build_epoch_sha256=document["build_epoch_sha256"],
            legacy_portable_rapm_id=document["legacy_portable_rapm_id"],
            portable_rapm_sha256=document["portable_rapm_sha256"],
            legacy_ground_query_id=document["legacy_ground_query_id"],
            legacy_occurrence_id=document["legacy_occurrence_id"],
            legacy_portable_query_id=document["legacy_portable_query_id"],
            portable_query_sha256=document["portable_query_sha256"],
        )
        if document["source_lease_id"] != lease.source_lease_id:
            raise Phase3ERAPMConsumerError("source lease content ID mismatch")
        return lease


_LIVE_SOURCE_AUTHORITIES: dict[
    int, tuple[weakref.ReferenceType["ModelOnlyRAPMSourceV1"], object, tuple[Any, ...]]
] = {}
_BUNDLE_SOURCE_MINT_AUTHORITY = object()
_TRANSPORT_SOURCE_MINT_AUTHORITY = object()


@dataclass(frozen=True, init=False, eq=False)
class ModelOnlyRAPMSourceV1:
    """Opaque live source authority; no ground objects are present.

    The serializable :class:`RAPMSourceLeaseV1` is evidence, not authority.
    Instances of this class are minted only after the loader has verified one
    retained bundle snapshot (or after the isolated runtime has verified its
    loader-sealed request material).  Object identity and a private one-use
    token are retained in a weak registry.  Consequently constructor calls,
    copies, ``dataclasses.replace``, pickling, and lease-only reconstruction do
    not acquire source authority.
    """

    lease: RAPMSourceLeaseV1
    model: PortableRAPM
    query: PortableQuery
    build_epoch: dict[str, Any] = field(repr=False)
    source_bundle: Path = field(repr=False)
    portable_rapm_source_bytes: bytes = field(repr=False)
    build_epoch_source_bytes: bytes = field(repr=False)
    portable_query_source_bytes: bytes = field(repr=False)
    _authority_token: object = field(repr=False, compare=False)
    _authority_origin: str = field(repr=False, compare=False)

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise Phase3ERAPMConsumerError(
            "ModelOnlyRAPMSourceV1 is an opaque live authority; use a verified loader"
        )


def _source_authority_fingerprint_v1(
    source: ModelOnlyRAPMSourceV1,
) -> tuple[Any, ...]:
    return (
        source.lease.source_lease_id,
        source.model.model_id,
        source.query.query_id,
        canonical_sha256(source.model.to_dict()),
        canonical_sha256(source.query.to_dict()),
        canonical_sha256(source.build_epoch),
        source.source_bundle.as_posix(),
        hashlib.sha256(source.portable_rapm_source_bytes).hexdigest(),
        hashlib.sha256(source.build_epoch_source_bytes).hexdigest(),
        hashlib.sha256(source.portable_query_source_bytes).hexdigest(),
        source._authority_origin,
    )


def _validate_source_material_v1(source: ModelOnlyRAPMSourceV1) -> None:
    if source.model.model_id != source.lease.legacy_portable_rapm_id:
        raise Phase3ERAPMConsumerError("source lease/model mismatch")
    if source.query.query_id != source.lease.legacy_portable_query_id:
        raise Phase3ERAPMConsumerError("source lease/query mismatch")
    if source.query.model_id != source.model.model_id:
        raise Phase3ERAPMConsumerError("portable query/model mismatch")
    if (
        hashlib.sha256(source.portable_rapm_source_bytes).hexdigest()
        != source.lease.portable_rapm_sha256
        or hashlib.sha256(source.portable_query_source_bytes).hexdigest()
        != source.lease.portable_query_sha256
    ):
        raise Phase3ERAPMConsumerError(
            "retained model/query bytes do not match source lease"
        )
    try:
        model_document = json.loads(source.portable_rapm_source_bytes.decode("utf-8"))
        query_document = json.loads(source.portable_query_source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Phase3ERAPMConsumerError(
            f"retained portable source bytes are invalid: {error}"
        ) from error
    if model_document != source.model.to_dict() or query_document != source.query.to_dict():
        raise Phase3ERAPMConsumerError(
            "retained portable source bytes differ from in-memory objects"
        )
    if source._authority_origin == "verified_phase3c_bundle_snapshot_v1":
        if (
            hashlib.sha256(source.build_epoch_source_bytes).hexdigest()
            != source.lease.build_epoch_sha256
            or _load_json_object_bytes(
                source.build_epoch_source_bytes, source_name="retained BuildEpoch"
            )
            != source.build_epoch
        ):
            raise Phase3ERAPMConsumerError(
                "retained BuildEpoch bytes do not match source lease"
            )
    elif source._authority_origin == "loader_sealed_execution_request_v1":
        if source.build_epoch or source.build_epoch_source_bytes:
            raise Phase3ERAPMConsumerError(
                "transport source must not invent untransported BuildEpoch bytes"
            )
    else:  # defensive against object.__new__/object.__setattr__ construction
        raise Phase3ERAPMConsumerError("unknown model-only source authority origin")


def _mint_model_only_source_v1(
    *,
    lease: RAPMSourceLeaseV1,
    model: PortableRAPM,
    query: PortableQuery,
    build_epoch: dict[str, Any],
    source_bundle: Path,
    portable_rapm_source_bytes: bytes,
    build_epoch_source_bytes: bytes,
    portable_query_source_bytes: bytes,
    mint_authority: object,
) -> ModelOnlyRAPMSourceV1:
    """Internal constructor used only by verified source-material loaders."""

    if mint_authority is _BUNDLE_SOURCE_MINT_AUTHORITY:
        authority_origin = "verified_phase3c_bundle_snapshot_v1"
    elif mint_authority is _TRANSPORT_SOURCE_MINT_AUTHORITY:
        authority_origin = "loader_sealed_execution_request_v1"
    else:
        raise Phase3ERAPMConsumerError(
            "model-only source mint requires an opaque loader authority"
        )
    source = object.__new__(ModelOnlyRAPMSourceV1)
    token = object()
    for name, value in (
        ("lease", lease),
        ("model", model),
        ("query", query),
        ("build_epoch", build_epoch),
        ("source_bundle", source_bundle),
        ("portable_rapm_source_bytes", bytes(portable_rapm_source_bytes)),
        ("build_epoch_source_bytes", bytes(build_epoch_source_bytes)),
        ("portable_query_source_bytes", bytes(portable_query_source_bytes)),
        ("_authority_token", token),
        ("_authority_origin", authority_origin),
    ):
        object.__setattr__(source, name, value)
    _validate_source_material_v1(source)
    identity = id(source)

    def discard(reference: weakref.ReferenceType[ModelOnlyRAPMSourceV1]) -> None:
        current = _LIVE_SOURCE_AUTHORITIES.get(identity)
        if current is not None and current[0] is reference:
            _LIVE_SOURCE_AUTHORITIES.pop(identity, None)

    reference = weakref.ref(source, discard)
    _LIVE_SOURCE_AUTHORITIES[identity] = (
        reference,
        token,
        _source_authority_fingerprint_v1(source),
    )
    return source


def _mint_model_only_source_from_loader_sealed_transport_v1(
    *,
    lease: RAPMSourceLeaseV1,
    model: PortableRAPM,
    query: PortableQuery,
    portable_rapm_source_bytes: bytes,
    portable_query_source_bytes: bytes,
) -> ModelOnlyRAPMSourceV1:
    """Mint the fresh worker's authority after its request-loader replay.

    The narrow transport entry point cannot claim a bundle path or BuildEpoch
    that was not transported.  Its result is process-local and is checked by
    the parent against the parent's independently retained bundle authority.
    """

    return _mint_model_only_source_v1(
        lease=lease,
        model=model,
        query=query,
        build_epoch={},
        source_bundle=Path("/model-only-source-lease"),
        portable_rapm_source_bytes=portable_rapm_source_bytes,
        build_epoch_source_bytes=b"",
        portable_query_source_bytes=portable_query_source_bytes,
        mint_authority=_TRANSPORT_SOURCE_MINT_AUTHORITY,
    )


def require_model_only_source_authority_v1(
    source: object,
) -> ModelOnlyRAPMSourceV1:
    """Require the exact still-live object minted by a verified loader."""

    if type(source) is not ModelOnlyRAPMSourceV1:
        raise Phase3ERAPMConsumerError(
            "a live ModelOnlyRAPMSourceV1 authority is required"
        )
    entry = _LIVE_SOURCE_AUTHORITIES.get(id(source))
    if (
        entry is None
        or entry[0]() is not source
        or entry[1] is not source._authority_token
    ):
        raise Phase3ERAPMConsumerError(
            "model-only source has lost or never held live loader authority"
        )
    _validate_source_material_v1(source)
    if entry[2] != _source_authority_fingerprint_v1(source):
        raise Phase3ERAPMConsumerError(
            "model-only source changed after loader authority was minted"
        )
    return source


def load_phase3c_model_source_v1(
    source_bundle: str | Path,
    *,
    query_key: str,
) -> ModelOnlyRAPMSourceV1:
    """Acquire a verified Phase-3C model/query lease without ground binding."""

    if query_key not in SUPPORTED_QUERY_KEYS:
        raise Phase3ERAPMConsumerError(f"unsupported query key: {query_key!r}")
    bundle = Path(source_bundle).resolve()
    snapshot = _acquire_bundle_snapshot_v1(bundle)
    manifest = _validate_manifest_snapshot_v1(snapshot)
    run = _validate_run(snapshot)

    model_bytes = snapshot.files["build/portable_rapm.json"]
    epoch_bytes = snapshot.files["build/epoch.json"]
    model_document = _load_json_object_bytes(
        model_bytes, source_name="build/portable_rapm.json"
    )
    epoch = _load_json_object_bytes(epoch_bytes, source_name="build/epoch.json")
    try:
        model = PortableRAPM.from_dict(model_document)
    except (TypeError, ValueError) as error:
        raise Phase3ERAPMConsumerError(
            f"portable RAPM validation failed: {error}"
        ) from error
    _validate_epoch(epoch, model)

    rows = _load_jsonl_object_bytes(
        snapshot.files["campaign/portable_queries.jsonl"],
        source_name="campaign/portable_queries.jsonl",
    )
    by_key: dict[str, tuple[dict[str, Any], bytes]] = {}
    for record, source_bytes in rows:
        try:
            require_exact_fields(
                record, _QUERY_STREAM_FIELDS, context="portable query stream row"
            )
        except Phase3EIdentityError as error:
            raise Phase3ERAPMConsumerError(str(error)) from error
        key = record.get("query_key")
        if key not in SUPPORTED_QUERY_KEYS or key in by_key:
            raise Phase3ERAPMConsumerError(
                "portable query stream keys must be the unique supported pair"
            )
        by_key[key] = (record, source_bytes)
    if set(by_key) != set(SUPPORTED_QUERY_KEYS):
        raise Phase3ERAPMConsumerError(
            "portable query stream does not contain the supported H1/H2 pair"
        )
    for record, _ in by_key.values():
        if record.get("portable_query_id") != record.get("portable_query", {}).get(
            "query_id"
        ):
            raise Phase3ERAPMConsumerError("portable query row ID mismatch")
        if record.get("portable_query", {}).get("model_id") != model.model_id:
            raise Phase3ERAPMConsumerError("portable query stream/model mismatch")

    selected_record, selected_row_bytes = by_key[query_key]
    try:
        query = PortableQuery.from_dict(selected_record["portable_query"], model)
    except (TypeError, ValueError) as error:
        raise Phase3ERAPMConsumerError(
            f"portable query validation failed: {error}"
        ) from error
    if query.query_id != selected_record["portable_query_id"]:
        raise Phase3ERAPMConsumerError("selected portable query ID mismatch")
    _query_registry_binding(
        snapshot,
        query_key=query_key,
        query_stream_record=selected_record,
        model=model,
    )

    query_bytes = canonical_json(selected_record["portable_query"]).encode("utf-8")
    lease = RAPMSourceLeaseV1(
        query_key=query_key,
        source_manifest_sha256=hashlib.sha256(snapshot.manifest_bytes).hexdigest(),
        source_bundle_sha256=manifest["bundle_sha256"],
        source_run_id=run["run_id"],
        source_semantic_hash=run["semantic_hash"],
        legacy_structural_id=epoch["structural_id"],
        kernel_sha256=epoch["kernel_sha256"],
        legacy_build_epoch_id=epoch["build_epoch_id"],
        build_epoch_sha256=hashlib.sha256(epoch_bytes).hexdigest(),
        legacy_portable_rapm_id=model.model_id,
        portable_rapm_sha256=hashlib.sha256(model_bytes).hexdigest(),
        legacy_ground_query_id=selected_record["ground_query_id"],
        legacy_occurrence_id=selected_record["occurrence_id"],
        legacy_portable_query_id=query.query_id,
        portable_query_sha256=hashlib.sha256(query_bytes).hexdigest(),
    )
    # Bind the selected row bytes to the manifest-verified stream while storing
    # only the query bytes in the reusable lease.
    if selected_row_bytes != canonical_json(selected_record).encode("utf-8"):
        raise Phase3ERAPMConsumerError("selected query row bytes changed")
    # No path is trusted after this point until every consumed byte and the
    # complete topology has been compared with the retained read-set.
    _recheck_bundle_snapshot_v1(snapshot)
    return _mint_model_only_source_v1(
        lease=lease,
        model=model,
        query=query,
        build_epoch=epoch,
        source_bundle=bundle,
        portable_rapm_source_bytes=model_bytes,
        build_epoch_source_bytes=epoch_bytes,
        portable_query_source_bytes=query_bytes,
        mint_authority=_BUNDLE_SOURCE_MINT_AUTHORITY,
    )


@dataclass(frozen=True, slots=True)
class SelectedContingentPlanV1:
    """A deterministic contingent-plan proposal selected from a RAPM frontier."""

    source_lease_id: str
    query_key: str
    legacy_portable_model_id: str
    legacy_portable_query_id: str
    planner_result: dict[str, Any]
    nominal_query_feasible: bool
    selector_id: str
    selected_frontier_index: int
    proposal_source: str

    def __post_init__(self) -> None:
        try:
            parse_content_id(self.source_lease_id)
        except Phase3EIdentityError as error:
            raise Phase3ERAPMConsumerError(
                "source_lease_id must be a full content ID"
            ) from error
        if self.query_key not in SUPPORTED_QUERY_KEYS:
            raise Phase3ERAPMConsumerError("selected plan has unsupported query key")
        if type(self.nominal_query_feasible) is not bool:
            raise Phase3ERAPMConsumerError("nominal_query_feasible must be boolean")
        _require_nonnegative_int(
            self.selected_frontier_index, field_name="selected_frontier_index"
        )
        for field_name in (
            "legacy_portable_model_id",
            "legacy_portable_query_id",
            "selector_id",
            "proposal_source",
        ):
            _require_string(getattr(self, field_name), field_name=field_name)
        if not isinstance(self.planner_result, dict):
            raise Phase3ERAPMConsumerError("planner_result must be an object")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SELECTED_CONTINGENT_PLAN_SCHEMA,
            "source_lease_id": self.source_lease_id,
            "query_key": self.query_key,
            "legacy_portable_model_id": self.legacy_portable_model_id,
            "legacy_portable_query_id": self.legacy_portable_query_id,
            "planner_result": self.planner_result,
            "nominal_query_feasible": self.nominal_query_feasible,
            "selector_id": self.selector_id,
            "selected_frontier_index": self.selected_frontier_index,
            "proposal_source": self.proposal_source,
        }

    @property
    def selected_contingent_plan_id(self) -> str:
        return _content_id(SELECTED_CONTINGENT_PLAN_DOMAIN, self._payload())

    @property
    def proposal(self) -> PortableParetoPoint:
        result = PortablePlanResult.from_dict(self.planner_result)
        try:
            return result.frontier[self.selected_frontier_index]
        except IndexError as error:  # defensive for objects bypassing construction
            raise Phase3ERAPMConsumerError(
                "selected frontier index exceeds planner frontier"
            ) from error

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_contingent_plan_id": self.selected_contingent_plan_id,
            **self._payload(),
        }

    @classmethod
    def from_dict(
        cls,
        document: Mapping[str, Any],
        *,
        source: ModelOnlyRAPMSourceV1,
    ) -> "SelectedContingentPlanV1":
        require_model_only_source_authority_v1(source)
        fields = {
            "selected_contingent_plan_id",
            "schema",
            "source_lease_id",
            "query_key",
            "legacy_portable_model_id",
            "legacy_portable_query_id",
            "planner_result",
            "nominal_query_feasible",
            "selector_id",
            "selected_frontier_index",
            "proposal_source",
        }
        try:
            require_exact_fields(
                document, fields, context="SelectedContingentPlanV1"
            )
        except Phase3EIdentityError as error:
            raise Phase3ERAPMConsumerError(str(error)) from error
        if document["schema"] != SELECTED_CONTINGENT_PLAN_SCHEMA:
            raise Phase3ERAPMConsumerError("unsupported selected-plan schema")
        try:
            result = PortablePlanResult.from_dict(
                document["planner_result"], model=source.model, query=source.query
            )
        except (TypeError, ValueError) as error:
            raise Phase3ERAPMConsumerError(
                f"invalid embedded portable plan result: {error}"
            ) from error
        expected = _selected_plan_from_result(source, result)
        artifact = cls(
            source_lease_id=document["source_lease_id"],
            query_key=document["query_key"],
            legacy_portable_model_id=document["legacy_portable_model_id"],
            legacy_portable_query_id=document["legacy_portable_query_id"],
            planner_result=document["planner_result"],
            nominal_query_feasible=document["nominal_query_feasible"],
            selector_id=document["selector_id"],
            selected_frontier_index=document["selected_frontier_index"],
            proposal_source=document["proposal_source"],
        )
        if artifact != expected:
            raise Phase3ERAPMConsumerError(
                "selected plan does not match the deterministic selector"
            )
        if document["selected_contingent_plan_id"] != artifact.selected_contingent_plan_id:
            raise Phase3ERAPMConsumerError("selected plan content ID mismatch")
        return artifact


def _selected_plan_from_result(
    source: ModelOnlyRAPMSourceV1,
    result: PortablePlanResult,
) -> SelectedContingentPlanV1:
    require_model_only_source_authority_v1(source)
    if result.model_id != source.model.model_id or result.query_id != source.query.query_id:
        raise Phase3ERAPMConsumerError("portable plan result/source mismatch")
    if result.selected is not None:
        proposal = result.selected
        selector_id = CONSTRAINED_SELECTOR_ID
        proposal_source = "nominal_constrained_selection"
        nominal_feasible = True
    else:
        proposal = min(
            result.frontier,
            key=lambda point: (
                -point.expected_reward,
                point.failure_probability,
                point.policy.signature(),
            ),
        )
        selector_id = RECOVERY_SELECTOR_ID
        proposal_source = (
            "max_reward_then_min_risk_then_policy_signature_for_certificate_recovery"
        )
        nominal_feasible = False
    return SelectedContingentPlanV1(
        source_lease_id=source.lease.source_lease_id,
        query_key=source.lease.query_key,
        legacy_portable_model_id=source.model.model_id,
        legacy_portable_query_id=source.query.query_id,
        planner_result=result.to_dict(),
        nominal_query_feasible=nominal_feasible,
        selector_id=selector_id,
        selected_frontier_index=result.frontier.index(proposal),
        proposal_source=proposal_source,
    )


def select_contingent_plan_v1(
    source: ModelOnlyRAPMSourceV1,
    *,
    operation_counter: Callable[[str, int], None] | None = None,
) -> SelectedContingentPlanV1:
    """Solve and deterministically select a plan without acquiring ground data."""

    require_model_only_source_authority_v1(source)
    return _selected_plan_from_result(
        source,
        solve_portable_pareto(
            source.model,
            source.query,
            operation_counter=operation_counter,
        ),
    )


__all__ = [
    "ABSTRACT_QUERY_KEY",
    "CONSTRAINED_SELECTOR_ID",
    "LOCAL_QUERY_KEY",
    "ModelOnlyRAPMSourceV1",
    "Phase3ERAPMConsumerError",
    "RAPM_SOURCE_LEASE_DOMAIN",
    "RAPM_SOURCE_LEASE_SCHEMA",
    "RAPMSourceLeaseV1",
    "RECOVERY_SELECTOR_ID",
    "SELECTED_CONTINGENT_PLAN_DOMAIN",
    "SELECTED_CONTINGENT_PLAN_SCHEMA",
    "SUPPORTED_QUERY_KEYS",
    "SelectedContingentPlanV1",
    "load_phase3c_model_source_v1",
    "require_model_only_source_authority_v1",
    "select_contingent_plan_v1",
]
