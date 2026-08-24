"""Fresh repaired full-ground-fallback production finalization for V180.

V180r7 failed before occurrence execution because the frozen V2 construction
source builder received the entire repository catalogue.  The additive
V180r7r1 successor consumes a separately frozen, exact reachable-source tree
and passes that tree to the public recovery occurrence-accounting runner.  It
does not reuse any private V180r7 finalizer helper.

The recovery runner emits three native V6 route components.  This module keeps
those components independent and performs an exact record-by-record V6-to-V9
lift.  Reachable-source materialization remains a referenced one-time
construction axis; its work is never inserted into one of the three route
vectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_domain_registry_extension_v180r7r1 as domains
from acfqp import construction_k7_recovery_eligible_occurrence_accounting_v1 as recovery
from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    NativeZeroAttestationV1,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope, derive_actual_projection_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


MAXIMUM_FIXED_POINT_ITERATIONS = 32
EXPECTED_SOURCE_OUTPUT_FILE_COUNT = 8
EXPECTED_SOURCE_OUTPUT_FILENAMES = frozenset(
    f"{role}.json"
    for role in (
        "BUSINESS_RESULT",
        "OPERATIONAL_TRACE",
        "TERMINAL_ARTIFACT",
        "COUNTER_RECORD_SET",
        "WORK_VECTOR",
        "COMPARISON_VECTOR",
        "ACTUAL_PROJECTION_PROOF",
        "OUTPUT_MANIFEST",
    )
)
EXPECTED_SOURCE_VECTOR_COUNT = 3
EXPECTED_SOURCE_RECORD_COUNT_PER_VECTOR = 202
EXPECTED_V9_RECORD_COUNT_PER_VECTOR = 269
EXPECTED_BINDING_BYTE_COUNT = 4_405
EXPECTED_BINDING_SHA256 = (
    "bf5d7f5292a4b38136b141745b9349bc4e86c2ab7e67592e8d25c19b5daa527f"
)
EXPECTED_SNAPSHOT_BYTE_COUNT = 388_638
EXPECTED_SNAPSHOT_SHA256 = (
    "18056b6f1aba853cb3b705041be93bce31700c79d45fa894fd956b144f0e7823"
)
EXPECTED_TRANSITION_BYTE_COUNT = 859_154
EXPECTED_TRANSITION_SHA256 = (
    "e2278f8b499b13f45ab1c8fcba29be9665d472d4cd9ab65e1ee124187bfbbe30"
)
RETAINED_PREDECESSOR_INPUT_FACTS = (
    {
        "role": "SOURCE_BUNDLE_BINDING",
        "relative_path": (
            ".tmp/recovery-eligible-retained-v1/SOURCE_BUNDLE_BINDING.json"
        ),
        "byte_count": EXPECTED_BINDING_BYTE_COUNT,
        "sha256": EXPECTED_BINDING_SHA256,
    },
    {
        "role": "REUSABLE_RAPM_SNAPSHOT",
        "relative_path": (
            ".tmp/recovery-eligible-retained-v1/REUSABLE_RAPM_SNAPSHOT.json"
        ),
        "byte_count": EXPECTED_SNAPSHOT_BYTE_COUNT,
        "sha256": EXPECTED_SNAPSHOT_SHA256,
    },
    {
        "role": "PROOF_DEPENDENCY_TRANSITION",
        "relative_path": (
            ".tmp/recovery-eligible-retained-v1/PROOF_DEPENDENCY_TRANSITION.json"
        ),
        "byte_count": EXPECTED_TRANSITION_BYTE_COUNT,
        "sha256": EXPECTED_TRANSITION_SHA256,
    },
)
EXPECTED_MATERIALIZED_SOURCE_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r7r1_materialized_source"
)
EXPECTED_RUNTIME_CAS_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r7r1_full_ground_fallback_cas"
)
EXPECTED_OUTPUT_DIRECTORY_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r7r1_full_ground_fallback_output"
)
EXPECTED_MATERIALIZED_SOURCE_MODULE_COUNT = 307
EXPECTED_MATERIALIZED_SOURCE_BYTE_COUNT = 15_129_926
EXPECTED_SOURCE_CLOSURE_ID = (
    "ac3f10ef4eea5c0ecc740d9cecc1991e851a65af198e6696f32bde1965feeb4b"
)
EXPECTED_SOURCE_CATALOG_MANIFEST_ID = (
    "92e4f36212d957d3701591ee689a23e4446d942c4c3e3b562049290c19ad50d0"
)
EXPECTED_SOURCE_CLOSURE_REPAIR_ID = (
    "feb8f6034ef1da9050242fe4e112edb285b77bd63a87642196f8fbc7995544c8"
)
PRESERVED_V180R7_FAILURE_ID = (
    "bd6e022804f5be7dc7ae22e781ce121fe462277858b058bacf8f201f5b234f79"
)
LOGICAL_OCCURRENCE_ID = hashlib.sha256(
    b"acfqp:v180r7r1:fresh-full-ground-fallback-occurrence\x00ordinal-7"
).hexdigest()
QUERY_ORDINAL = 7


class ConstructionK7FullGroundFallbackFinalizerV180r7r1Error(RuntimeError):
    """The repaired fallback execution or its exact V9 lift changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FullGroundFallbackFinalizerV180r7r1Error(message)


@dataclass(frozen=True, slots=True)
class _MaterializedSourceEvidenceReferenceV180r7r1:
    source_root: Path
    reference_document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class _ExecutionProtocolSlotReferenceV180r7r1:
    execution_protocol_id: str
    slot: Mapping[str, Any]


def _load_materialized_source_evidence(
    repository_root: Path,
) -> _MaterializedSourceEvidenceReferenceV180r7r1:
    """Adapt the independently frozen materialization evidence in one place."""

    # This local import deliberately isolates the independently implemented
    # materialization evidence-freeze API from all execution/lift semantics.
    from acfqp import (  # noqa: PLC0415
        construction_k7_full_ground_fallback_materialized_source_evidence_freeze_v180r7r1
        as materialization,
    )

    frozen = (
        materialization.load_frozen_full_ground_fallback_materialized_source_v180r7r1()
    )
    raw = frozen.canonical_bytes
    document = frozen.to_document()
    source_root = Path(frozen.source_root)
    expected_root = repository_root / EXPECTED_MATERIALIZED_SOURCE_RELATIVE_PATH
    tree = document.get("materialized_source_tree")
    closure = document.get("unchanged_v2_source_closure")
    construction_work = document.get("construction_work")
    if not (
        type(raw) is bytes
        and type(document) is dict
        and canonical_json_bytes(document) == raw
        and source_root == expected_root
        and source_root.resolve(strict=True) == expected_root.resolve(strict=True)
        and not source_root.is_symlink()
        and not (source_root / "src").is_symlink()
        and not (source_root / "src" / "acfqp").is_symlink()
        and (source_root / "src" / "acfqp").is_dir()
        and document.get("materialization_manifest_id")
        == frozen.materialization_manifest_id
        and document.get("materialized_source_tree_id")
        == frozen.materialized_source_tree_id
        and document.get("source_catalog_manifest_id")
        == EXPECTED_SOURCE_CATALOG_MANIFEST_ID
        and document.get("source_closure_repair_id")
        == EXPECTED_SOURCE_CLOSURE_REPAIR_ID
        and document.get("materialized_root_relative_path")
        == EXPECTED_MATERIALIZED_SOURCE_RELATIVE_PATH
        and type(tree) is dict
        and tree.get("materialized_source_tree_id")
        == frozen.materialized_source_tree_id
        and tree.get("materialized_source_file_count")
        == EXPECTED_MATERIALIZED_SOURCE_MODULE_COUNT
        and tree.get("materialized_source_byte_count")
        == EXPECTED_MATERIALIZED_SOURCE_BYTE_COUNT
        and type(closure) is dict
        and closure.get("closure_id")
        == EXPECTED_SOURCE_CLOSURE_ID
        and document.get("unchanged_v2_source_closure_id")
        == EXPECTED_SOURCE_CLOSURE_ID
        and type(construction_work) is dict
        and construction_work.get(
            "construction_work_excluded_from_occurrence_route_vectors"
        )
        is True
        and construction_work.get("occurrence_counter_record_count") == 0
        and construction_work.get("occurrence_route_work_vector_count") == 0
        and construction_work.get("occurrence_comparison_vector_count") == 0
        and document.get("fresh_execution_authorization_issued") is False
        and document.get("fallback_occurrence_started") is False
        and document.get("scientific_occurrence_executed") is False
        and document.get("production_outcome_accessed") is False
        and document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and document.get("official_execution_allowed") is False
        and document.get("construction_only") is True
    ):
        _fail("frozen V180r7r1 materialized source evidence changed")
    reference = {
        "schema": "acfqp.full_ground_fallback_materialized_source_reference.v180r7r1",
        "materialization_manifest_id": frozen.materialization_manifest_id,
        "materialization_manifest_canonical_byte_count": len(raw),
        "materialization_manifest_canonical_sha256": hashlib.sha256(raw).hexdigest(),
        "materialized_source_tree_id": frozen.materialized_source_tree_id,
        "materialized_source_relative_path": EXPECTED_MATERIALIZED_SOURCE_RELATIVE_PATH,
        "source_catalog_manifest_id": EXPECTED_SOURCE_CATALOG_MANIFEST_ID,
        "source_closure_repair_id": EXPECTED_SOURCE_CLOSURE_REPAIR_ID,
        "source_closure_id": EXPECTED_SOURCE_CLOSURE_ID,
        "materialized_source_module_count": EXPECTED_MATERIALIZED_SOURCE_MODULE_COUNT,
        "materialized_source_byte_count": EXPECTED_MATERIALIZED_SOURCE_BYTE_COUNT,
        "construction_work": construction_work,
        "one_time_construction_axis": True,
        "charged_to_any_route_component": False,
        "scientific_occurrence_execution_work": False,
    }
    return _MaterializedSourceEvidenceReferenceV180r7r1(source_root, reference)


def _slot() -> _ExecutionProtocolSlotReferenceV180r7r1:
    """Load the fresh successor slot without touching the consumed V180r3 slot."""

    from acfqp import (  # noqa: PLC0415
        construction_k7_full_ground_fallback_execution_protocol_v180r7r1
        as successor_protocol,
    )

    frozen = successor_protocol.freeze_full_ground_fallback_execution_protocol_v180r7r1()
    document = frozen.to_document()
    slot = document.get("production_execution_slot")
    protocol_id = document.get("fallback_execution_protocol_id")
    if not (
        type(document) is dict
        and type(slot) is dict
        and type(protocol_id) is str
        and protocol_id == successor_protocol.EXPECTED_PROTOCOL_ID
        and slot.get("terminal_code") == TerminalCode.FULL_GROUND_FALLBACK.value
        and slot.get("logical_occurrence_id") == LOGICAL_OCCURRENCE_ID
        and slot.get("query_ordinal") == QUERY_ORDINAL
        and slot.get("preserved_v180r7_failure_id") == PRESERVED_V180R7_FAILURE_ID
        and slot.get("source_closure_repair_id") == EXPECTED_SOURCE_CLOSURE_REPAIR_ID
        and type(slot.get("production_execution_slot_id")) is str
        and type(slot.get("execution_nonce")) is str
        and len(slot["production_execution_slot_id"]) == 64
        and len(slot["execution_nonce"]) == 64
        and document.get("production_outcome_accessed") is False
        and document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and document.get("official_execution_allowed") is False
    ):
        _fail("fresh V180r7r1 fallback execution protocol changed")
    return _ExecutionProtocolSlotReferenceV180r7r1(protocol_id, slot)


def _exact_input(raw: bytes, *, byte_count: int, sha256: str, label: str) -> bytes:
    if not (
        type(raw) is bytes
        and len(raw) == byte_count
        and hashlib.sha256(raw).hexdigest() == sha256
    ):
        _fail(f"{label} retained predecessor changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return raw


def _require_absent_path_with_real_parents(
    repository_root: Path,
    candidate: Path,
    expected_relative_path: str,
) -> None:
    expected = repository_root / expected_relative_path
    if candidate != expected or os.path.lexists(candidate):
        _fail("fresh fallback CAS or output path changed or already exists")
    relative = Path(expected_relative_path)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise AssertionError("invalid frozen V180r7r1 output path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        directory_fd = os.open(repository_root, flags)
    except OSError as exc:  # pragma: no cover - repository already imported
        _fail(f"repository root cannot be opened safely: {exc}")
    try:
        for part in relative.parts[:-1]:
            try:
                next_fd = os.open(part, flags, dir_fd=directory_fd)
            except OSError as exc:
                _fail(f"fresh fallback output parent changed: {exc}")
            os.close(directory_fd)
            directory_fd = next_fd
        try:
            os.stat(relative.parts[-1], dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        except OSError as exc:
            _fail(f"fresh fallback output leaf cannot be inspected safely: {exc}")
        _fail("fresh fallback CAS or output path changed or already exists")
    finally:
        os.close(directory_fd)


def _output_inventory(root: Path) -> tuple[dict[str, Any], ...]:
    def identity(row: os.stat_result) -> tuple[int, ...]:
        return (
            row.st_dev,
            row.st_ino,
            row.st_mode,
            row.st_nlink,
            row.st_size,
            row.st_mtime_ns,
            row.st_ctime_ns,
        )

    try:
        before = os.lstat(root)
        if not stat.S_ISDIR(before.st_mode) or stat.S_ISLNK(before.st_mode):
            _fail("fresh fallback output root is not a real directory")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        directory_fd = os.open(root, flags)
    except (OSError, ValueError) as exc:
        _fail(f"fresh fallback output root cannot be opened safely: {exc}")
    try:
        opened = os.fstat(directory_fd)
        if identity(opened) != identity(before):
            _fail("fresh fallback output root changed while opening")
        names = sorted(os.listdir(directory_fd))
        if set(names) != EXPECTED_SOURCE_OUTPUT_FILENAMES:
            _fail("fresh fallback output role set changed")
        rows = []
        for name in names:
            try:
                path_before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if not stat.S_ISREG(path_before.st_mode) or path_before.st_nlink != 1:
                    _fail("fresh fallback output role is not one regular file")
                file_flags = os.O_RDONLY | os.O_CLOEXEC
                if hasattr(os, "O_NOFOLLOW"):
                    file_flags |= os.O_NOFOLLOW
                file_fd = os.open(name, file_flags, dir_fd=directory_fd)
            except (OSError, ValueError) as exc:
                _fail(f"fresh fallback output role cannot be opened safely: {exc}")
            try:
                opened_file = os.fstat(file_fd)
                if identity(opened_file) != identity(path_before):
                    _fail("fresh fallback output role changed while opening")
                chunks = []
                while True:
                    chunk = os.read(file_fd, 1 << 20)
                    if not chunk:
                        break
                    chunks.append(chunk)
                raw = b"".join(chunks)
                opened_after = os.fstat(file_fd)
                path_after = os.stat(
                    name, dir_fd=directory_fd, follow_symlinks=False
                )
                if not (
                    identity(opened_file)
                    == identity(opened_after)
                    == identity(path_after)
                    and len(raw) == opened_file.st_size
                ):
                    _fail("fresh fallback output role changed while reading")
            finally:
                os.close(file_fd)
            rows.append(
                {
                    "relative_path": name,
                    "canonical_byte_count": len(raw),
                    "canonical_sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
        root_after = os.lstat(root)
        opened_after = os.fstat(directory_fd)
        if not (
            identity(opened)
            == identity(opened_after)
            == identity(root_after)
            and sorted(os.listdir(directory_fd)) == names
        ):
            _fail("fresh fallback output root changed while reading")
        if len(rows) != EXPECTED_SOURCE_OUTPUT_FILE_COUNT:
            _fail("fresh fallback output role denominator changed")
        return tuple(rows)
    finally:
        os.close(directory_fd)


def _require_output_commit_matches_inventory(
    source_bundle: Any,
    inventory: Sequence[Mapping[str, Any]],
) -> None:
    expected = tuple(
        sorted(
            (
                {
                    "relative_path": row.filename,
                    "canonical_byte_count": row.byte_count,
                    "canonical_sha256": row.bytes_sha256,
                }
                for row in source_bundle.output_commit.role_commits
            ),
            key=lambda row: row["relative_path"],
        )
    )
    if tuple(dict(row) for row in inventory) != expected:
        _fail("fresh fallback output inventory changed from its durable commit")


_SCOPE_BY_ROUTE = {
    RouteKindEnum.ABSTRACT_FAILED_PREFIX: ActualWorkScope.COMMON_PREFIX,
    RouteKindEnum.LOCAL_ATTEMPT: ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    RouteKindEnum.DIRECT_FALLBACK: ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
}


def _verify_registry_extension() -> tuple[Any, Any]:
    source = registry_v6.official_counter_registry_v6()
    target = registry_v9.official_counter_registry_v9()
    if not (
        len(source.required_paths) == EXPECTED_SOURCE_RECORD_COUNT_PER_VECTOR
        and len(target.by_path) == EXPECTED_V9_RECORD_COUNT_PER_VECTOR
        and set(source.by_path) <= set(target.by_path)
    ):
        _fail("V6 to V9 registry cardinality or inclusion changed")
    semantic_fields = (
        "path",
        "semantics_id",
        "owner",
        "unit",
        "lane",
        "scope",
        "reducer",
        "comparison_axis",
        "required",
    )
    for path, source_semantics in source.by_path.items():
        target_semantics = target.by_path[path]
        if any(
            getattr(source_semantics, field_name)
            != getattr(target_semantics, field_name)
            for field_name in semantic_fields
        ):
            _fail(f"V9 changed inherited counter semantics for {path}")
    return source, target


def _lift_component(
    *,
    source_vector: WorkVectorV1,
    receipt_id: str,
    finalizer_output_bytes: int,
) -> dict[str, Any]:
    source_registry, target_registry = _verify_registry_extension()
    source_registry.validate_vector(source_vector)
    if source_vector.route_kind not in _SCOPE_BY_ROUTE:
        _fail("source fallback route component changed")
    source_records = {row.path: row for row in source_vector.records}
    if set(source_records) != set(source_registry.required_paths):
        _fail("source fallback vector does not exactly cover V6 required paths")
    recorder_id = hashlib.sha256(
        b"acfqp:v180r7r1:v9-lift-recorder\x00"
        + receipt_id.encode()
        + b"\x00"
        + source_vector.route_kind.value.encode()
    ).hexdigest()
    records = []
    lineage = []
    for path in sorted(target_registry.by_path):
        source_record = source_records.get(path)
        value = source_record.value if source_record is not None else 0
        finalizer_increment = 0
        if (
            source_vector.route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX
            and path == "io.output_bytes"
        ):
            value += finalizer_output_bytes
            finalizer_increment = finalizer_output_bytes
        record = CounterRecordV1.observe(
            target_registry,
            path,
            value,
            recorder_id=recorder_id,
        )
        records.append(record)
        lineage_payload = {
            "schema": "acfqp.full_ground_fallback_v9_lift_lineage.v180r7r1",
            "source_counter_registry_id": source_registry.registry_id,
            "target_counter_registry_id": target_registry.registry_id,
            "source_work_vector_id": source_vector.work_vector_id,
            "route_kind": source_vector.route_kind.value,
            "path": path,
            "source_counter_record_id": (
                source_record.record_id if source_record is not None else None
            ),
            "source_value": source_record.value if source_record is not None else None,
            "target_counter_record_id": record.record_id,
            "value": value,
            "inherited_semantics_exact": source_record is not None,
            "source_value_plus_finalizer_increment_equals_target_value": (
                source_record is not None
                and source_record.value + finalizer_increment == value
            ),
            "finalizer_output_increment": finalizer_increment,
            "target_path_absent_from_source_vector_native_zero_observation": (
                source_record is None
            ),
            "historical_summary_translation_used": False,
            "materialized_source_construction_work_charged_to_this_route": False,
        }
        lineage.append(
            {
                **lineage_payload,
                "lineage_id": domains.extension_content_id_v180r7r1(
                    domains.CONSTRUCTION_K7_FALLBACK_V9_LIFT_LINEAGE_V180R7R1_DOMAIN,
                    lineage_payload,
                ),
            }
        )
    vector = WorkVectorV1(
        target_registry.registry_id,
        source_vector.subject_id,
        source_vector.route_kind,
        tuple(records),
    )
    comparison_profile = registry_v9.official_comparison_profile_v9(target_registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        target_registry, comparison_profile
    )
    comparison, proof = derive_actual_projection_v1(
        vector,
        target_registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=_SCOPE_BY_ROUTE[source_vector.route_kind],
    )
    zero = NativeZeroAttestationV1.derive(vector, target_registry)
    return {
        "source_work_vector": source_vector.to_dict(),
        "v9_work_vector": vector.to_dict(),
        "v9_comparison_vector": comparison.to_dict(),
        "v9_actual_projection_proof": proof.to_dict(),
        "v9_native_zero_attestation": zero.to_dict(),
        "counter_lift_lineage": lineage,
        "independent_route_component": True,
        "materialized_source_construction_work_charged_to_component": False,
    }


def _source_route_components(source_bundle: Any) -> list[dict[str, Any]]:
    if not (
        len(source_bundle.work_vectors) == EXPECTED_SOURCE_VECTOR_COUNT
        and len(source_bundle.comparison_vectors) == EXPECTED_SOURCE_VECTOR_COUNT
        and len(source_bundle.actual_projection_proofs) == EXPECTED_SOURCE_VECTOR_COUNT
    ):
        _fail("source route component chain denominator changed")
    rows = []
    for vector, comparison, proof in zip(
        source_bundle.work_vectors,
        source_bundle.comparison_vectors,
        source_bundle.actual_projection_proofs,
        strict=True,
    ):
        if not (
            vector.subject_id == LOGICAL_OCCURRENCE_ID
            and comparison.work_vector_id == vector.work_vector_id
            and proof.work_vector_id == vector.work_vector_id
        ):
            _fail("source route component identity chain changed")
        rows.append(
            {
                "route_kind": vector.route_kind.value,
                "source_work_vector_id": vector.work_vector_id,
                "source_comparison_vector_id": comparison.comparison_vector_id,
                "source_actual_projection_proof_id": proof.actual_projection_proof_id,
                "independent_route_component": True,
            }
        )
    if tuple(row["route_kind"] for row in rows) != tuple(
        route.value for route in _SCOPE_BY_ROUTE
    ):
        _fail("source route component order changed")
    return rows


def _build_occurrence_receipt(
    *,
    execution_protocol_id: str,
    slot: Mapping[str, Any],
    source_bundle: Any,
    inventory: Sequence[Mapping[str, Any]],
    materialization_reference: Mapping[str, Any],
) -> dict[str, Any]:
    route_components = _source_route_components(source_bundle)
    receipt_payload = {
        "schema": "acfqp.full_ground_fallback_production_occurrence_receipt.v180r7r1",
        "fallback_execution_protocol_id": execution_protocol_id,
        "production_execution_slot_id": slot["production_execution_slot_id"],
        "predecessor_occurrence_slot_id": slot["predecessor_occurrence_slot_id"],
        "execution_nonce": slot["execution_nonce"],
        "terminal_code": TerminalCode.FULL_GROUND_FALLBACK.value,
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "query_ordinal": QUERY_ORDINAL,
        "source_occurrence_accounting_bundle_id": source_bundle.bundle_id,
        "source_counter_registry_id": source_bundle.work_vectors[0].counter_registry_id,
        "target_counter_registry_id": registry_v9.official_counter_registry_v9().registry_id,
        "source_route_components": route_components,
        "source_work_vector_ids": [
            row.work_vector_id for row in source_bundle.work_vectors
        ],
        "source_shared_resource_receipt_ids": [
            row.receipt_id for row in source_bundle.receipt_set.receipts
        ],
        "source_output_inventory": [dict(row) for row in inventory],
        "source_output_bytes": source_bundle.fixed_point.output_bytes,
        "retained_predecessor_input_facts": [
            dict(row) for row in RETAINED_PREDECESSOR_INPUT_FACTS
        ],
        "materialized_source_reference": dict(materialization_reference),
        "production_execution_started_by_this_call": True,
        "preexisting_occurrence_output_used": False,
        "native_v6_counter_records_used": True,
        "registered_v6_to_v9_counter_lift_required": True,
        "three_route_components_independent": True,
        "materialization_is_separate_one_time_construction_axis": True,
        "materialization_work_charged_to_any_route_component": False,
        "historical_summary_translation_used": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **receipt_payload,
        "production_occurrence_receipt_id": domains.extension_content_id_v180r7r1(
            domains.CONSTRUCTION_K7_FALLBACK_OCCURRENCE_RECEIPT_V180R7R1_DOMAIN,
            receipt_payload,
        ),
    }


def _materialize_bundle(
    *,
    execution_protocol_id: str,
    slot: Mapping[str, Any],
    receipt: Mapping[str, Any],
    source_bundle: Any,
    inventory: Sequence[Mapping[str, Any]],
    materialization_reference: Mapping[str, Any],
) -> bytes:
    source_output_bytes = source_bundle.fixed_point.output_bytes
    guess = 0
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        lifted = [
            _lift_component(
                source_vector=vector,
                receipt_id=receipt["production_occurrence_receipt_id"],
                finalizer_output_bytes=guess,
            )
            for vector in source_bundle.work_vectors
        ]
        payload = {
            "schema": "acfqp.full_ground_fallback_production_terminal_bundle.v180r7r1",
            "formalization_contract_id": contract.EXPECTED_CONTRACT_ID,
            "fallback_execution_protocol_id": execution_protocol_id,
            "production_execution_slot": dict(slot),
            "terminal_code": TerminalCode.FULL_GROUND_FALLBACK.value,
            "production_occurrence_receipt": dict(receipt),
            "materialized_source_reference": dict(materialization_reference),
            "source_occurrence_accounting_bundle": source_bundle.to_document(),
            "source_output_inventory": [dict(row) for row in inventory],
            "v9_lifted_route_components": lifted,
            "source_output_bytes": source_output_bytes,
            "finalizer_output_bytes": guess,
            "output_bytes_fixed_point": source_output_bytes + guess,
            "fixed_point_iteration": iteration,
            "fresh_v180r7r1_observed_occurrence_present": True,
            "three_route_family_vectors_remain_separate": True,
            "registered_counter_to_counter_v6_to_v9_lift_used": True,
            "v9_paths_absent_from_source_vector_have_explicit_native_zero_lineage": True,
            "materialization_is_separate_one_time_construction_axis": True,
            "materialization_work_charged_to_any_route_component": False,
            "terminal_serialization_bytes_charged_as_output_bytes": True,
            "materialization_reference_serialization_is_output_metadata_not_construction_work": True,
            "historical_summary_translation_used": False,
            "development_fixture_only": False,
            "partial_campaign_cannot_unlock_any_gate": True,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }
        document = {
            **payload,
            "production_terminal_bundle_id": domains.extension_content_id_v180r7r1(
                domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_TERMINAL_V180R7R1_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("V180r7r1 fallback terminal output fixed point did not converge")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FullGroundFallbackProductionTerminalBundleV180r7r1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    production_terminal_bundle_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("fallback production terminal bundle is not issuer-created")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("fallback production terminal bundle bytes changed")
        return document


def run_full_ground_fallback_production_occurrence_v180r7r1(
    *,
    repository_root: Path,
    runtime_cas_root: Path,
    output_directory: Path,
    binding_bytes: bytes,
    snapshot_bytes: bytes,
    transition_bytes: bytes,
) -> FullGroundFallbackProductionTerminalBundleV180r7r1:
    expected_repository_root = Path(__file__).resolve().parents[2]
    if not (
        isinstance(repository_root, Path)
        and repository_root.resolve() == expected_repository_root
        and isinstance(runtime_cas_root, Path)
        and isinstance(output_directory, Path)
    ):
        _fail("V180r7r1 repository, CAS, or output boundary changed")
    _require_absent_path_with_real_parents(
        expected_repository_root,
        runtime_cas_root,
        EXPECTED_RUNTIME_CAS_RELATIVE_PATH,
    )
    _require_absent_path_with_real_parents(
        expected_repository_root,
        output_directory,
        EXPECTED_OUTPUT_DIRECTORY_RELATIVE_PATH,
    )
    binding = _exact_input(
        binding_bytes,
        byte_count=EXPECTED_BINDING_BYTE_COUNT,
        sha256=EXPECTED_BINDING_SHA256,
        label="source binding",
    )
    snapshot = _exact_input(
        snapshot_bytes,
        byte_count=EXPECTED_SNAPSHOT_BYTE_COUNT,
        sha256=EXPECTED_SNAPSHOT_SHA256,
        label="RAPM snapshot",
    )
    transition = _exact_input(
        transition_bytes,
        byte_count=EXPECTED_TRANSITION_BYTE_COUNT,
        sha256=EXPECTED_TRANSITION_SHA256,
        label="dependency transition",
    )
    materialization = _load_materialized_source_evidence(expected_repository_root)
    execution_protocol = _slot()
    slot = execution_protocol.slot
    if slot.get("materialization_manifest_id") != materialization.reference_document.get(
        "materialization_manifest_id"
    ):
        _fail("fresh execution slot does not bind the frozen materialized source")
    source_bundle = recovery.run_recovery_eligible_occurrence_accounting_v1(
        repository_root=materialization.source_root,
        runtime_cas_root=runtime_cas_root,
        output_directory=output_directory,
        binding_bytes=binding,
        snapshot_bytes=snapshot,
        transition_bytes=transition,
        logical_occurrence_id=LOGICAL_OCCURRENCE_ID,
        query_ordinal=QUERY_ORDINAL,
        timeout_seconds=7_200,
    )
    if not (
        source_bundle.to_document()["scientific_terminal_code"]
        == TerminalCode.FULL_GROUND_FALLBACK.value
        and tuple(row.route_kind for row in source_bundle.work_vectors)
        == tuple(_SCOPE_BY_ROUTE)
        and len(source_bundle.receipt_set.receipts) == 9
        and len(source_bundle.work_vectors) == EXPECTED_SOURCE_VECTOR_COUNT
        and len({row.work_vector_id for row in source_bundle.work_vectors})
        == EXPECTED_SOURCE_VECTOR_COUNT
    ):
        _fail("fresh source occurrence did not reach full-ground fallback")
    inventory = _output_inventory(output_directory)
    _require_output_commit_matches_inventory(source_bundle, inventory)
    if sum(row["canonical_byte_count"] for row in inventory) != (
        source_bundle.fixed_point.output_bytes
    ):
        _fail("fresh fallback source output fixed point changed")
    receipt = _build_occurrence_receipt(
        execution_protocol_id=execution_protocol.execution_protocol_id,
        slot=slot,
        source_bundle=source_bundle,
        inventory=inventory,
        materialization_reference=materialization.reference_document,
    )
    raw = _materialize_bundle(
        execution_protocol_id=execution_protocol.execution_protocol_id,
        slot=slot,
        receipt=receipt,
        source_bundle=source_bundle,
        inventory=inventory,
        materialization_reference=materialization.reference_document,
    )
    document = loads_canonical_json(raw)
    if type(document) is not dict:
        raise AssertionError("fallback terminal bundle is not an object")
    return FullGroundFallbackProductionTerminalBundleV180r7r1(
        _ISSUER,
        raw,
        document["production_terminal_bundle_id"],
    )


__all__ = (
    "ConstructionK7FullGroundFallbackFinalizerV180r7r1Error",
    "FullGroundFallbackProductionTerminalBundleV180r7r1",
    "LOGICAL_OCCURRENCE_ID",
    "QUERY_ORDINAL",
    "run_full_ground_fallback_production_occurrence_v180r7r1",
)
