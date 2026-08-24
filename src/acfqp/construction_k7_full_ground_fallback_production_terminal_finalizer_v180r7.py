"""Fresh V6-to-V9 full-ground-fallback production finalization for V180.

The source execution emits native V6 CounterRecords for three separate route
families.  This successor performs an exact registered counter-to-counter
lift: every unchanged V6 semantic path is copied record-by-record into V9,
and every additive V9 path absent from V6 receives an explicit native-zero
lineage row.  No historical summary is translated into counters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r7 as domains
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
EXPECTED_SOURCE_VECTOR_COUNT = 3
EXPECTED_SOURCE_RECORD_COUNT_PER_VECTOR = 202
EXPECTED_V9_RECORD_COUNT_PER_VECTOR = 269
EXPECTED_BINDING_BYTE_COUNT = 4_405
EXPECTED_BINDING_SHA256 = "bf5d7f5292a4b38136b141745b9349bc4e86c2ab7e67592e8d25c19b5daa527f"
EXPECTED_SNAPSHOT_BYTE_COUNT = 388_638
EXPECTED_SNAPSHOT_SHA256 = "18056b6f1aba853cb3b705041be93bce31700c79d45fa894fd956b144f0e7823"
EXPECTED_TRANSITION_BYTE_COUNT = 859_154
EXPECTED_TRANSITION_SHA256 = "e2278f8b499b13f45ab1c8fcba29be9665d472d4cd9ab65e1ee124187bfbbe30"
LOGICAL_OCCURRENCE_ID = hashlib.sha256(
    b"acfqp:v180r7:fresh-full-ground-fallback-occurrence\x00ordinal-7"
).hexdigest()
QUERY_ORDINAL = 7


class ConstructionK7FullGroundFallbackFinalizerV180r7Error(RuntimeError):
    """The fresh fallback execution or its exact V9 lift changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FullGroundFallbackFinalizerV180r7Error(message)


def _slot() -> dict[str, Any]:
    rows = protocol.freeze_all_path_production_execution_protocol_v180r3().to_document()[
        "production_execution_slots"
    ]
    matches = [
        row
        for row in rows
        if row["terminal_code"] == TerminalCode.FULL_GROUND_FALLBACK.value
    ]
    if len(matches) != 1:
        _fail("V180r3 protocol lost the full-fallback slot")
    return matches[0]


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


def _output_inventory(root: Path) -> tuple[dict[str, Any], ...]:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        raw = path.read_bytes()
        rows.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "canonical_byte_count": len(raw),
                "canonical_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if len(rows) != EXPECTED_SOURCE_OUTPUT_FILE_COUNT:
        _fail("fresh fallback output role denominator changed")
    return tuple(rows)


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
    source_records = {row.path: row for row in source_vector.records}
    if set(source_records) != set(source_registry.required_paths):
        _fail("source fallback vector does not exactly cover V6 required paths")
    recorder_id = hashlib.sha256(
        b"acfqp:v180r7:v9-lift-recorder\x00"
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
            "schema": "acfqp.full_ground_fallback_v9_lift_lineage.v180r7",
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
        }
        lineage.append(
            {
                **lineage_payload,
                "lineage_id": domains.extension_content_id_v180r7(
                    domains.CONSTRUCTION_K7_FALLBACK_V9_LIFT_LINEAGE_V180R7_DOMAIN,
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
    }


def _materialize_bundle(
    *,
    slot: Mapping[str, Any],
    receipt: Mapping[str, Any],
    source_bundle: Any,
    inventory: Sequence[Mapping[str, Any]],
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
            "schema": "acfqp.full_ground_fallback_production_terminal_bundle.v180r7",
            "formalization_contract_id": contract.EXPECTED_CONTRACT_ID,
            "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
            "production_execution_slot": dict(slot),
            "terminal_code": TerminalCode.FULL_GROUND_FALLBACK.value,
            "production_occurrence_receipt": dict(receipt),
            "source_occurrence_accounting_bundle": source_bundle.to_document(),
            "source_output_inventory": [dict(row) for row in inventory],
            "v9_lifted_route_components": lifted,
            "source_output_bytes": source_output_bytes,
            "finalizer_output_bytes": guess,
            "output_bytes_fixed_point": source_output_bytes + guess,
            "fixed_point_iteration": iteration,
            "fresh_v180r7_observed_occurrence_present": True,
            "three_route_family_vectors_remain_separate": True,
            "registered_counter_to_counter_v6_to_v9_lift_used": True,
            "v9_paths_absent_from_source_vector_have_explicit_native_zero_lineage": True,
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
            "production_terminal_bundle_id": domains.extension_content_id_v180r7(
                domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_TERMINAL_V180R7_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("V180r7 fallback terminal output fixed point did not converge")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FullGroundFallbackProductionTerminalBundleV180r7:
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


def run_full_ground_fallback_production_occurrence_v180r7(
    *,
    repository_root: Path,
    runtime_cas_root: Path,
    output_directory: Path,
    binding_bytes: bytes,
    snapshot_bytes: bytes,
    transition_bytes: bytes,
) -> FullGroundFallbackProductionTerminalBundleV180r7:
    if not (
        isinstance(repository_root, Path)
        and repository_root.resolve() == Path(__file__).resolve().parents[2]
        and isinstance(runtime_cas_root, Path)
        and not runtime_cas_root.exists()
        and isinstance(output_directory, Path)
        and not output_directory.exists()
    ):
        _fail("V180r7 repository, CAS, or output boundary changed")
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
    slot = _slot()
    source_bundle = recovery.run_recovery_eligible_occurrence_accounting_v1(
        repository_root=repository_root,
        runtime_cas_root=runtime_cas_root,
        output_directory=output_directory,
        binding_bytes=binding,
        snapshot_bytes=snapshot,
        transition_bytes=transition,
        logical_occurrence_id=LOGICAL_OCCURRENCE_ID,
        query_ordinal=QUERY_ORDINAL,
        timeout_seconds=7_200,
    )
    recovery.verify_recovery_eligible_occurrence_accounting_v1(source_bundle)
    if not (
        source_bundle.to_document()["scientific_terminal_code"]
        == TerminalCode.FULL_GROUND_FALLBACK.value
        and tuple(row.route_kind for row in source_bundle.work_vectors)
        == (
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            RouteKindEnum.LOCAL_ATTEMPT,
            RouteKindEnum.DIRECT_FALLBACK,
        )
        and len(source_bundle.receipt_set.receipts) == 9
        and len(source_bundle.work_vectors) == EXPECTED_SOURCE_VECTOR_COUNT
    ):
        _fail("fresh source occurrence did not reach full-ground fallback")
    inventory = _output_inventory(output_directory)
    if sum(row["canonical_byte_count"] for row in inventory) != (
        source_bundle.fixed_point.output_bytes
    ):
        _fail("fresh fallback source output fixed point changed")
    receipt_payload = {
        "schema": "acfqp.full_ground_fallback_production_occurrence_receipt.v180r7",
        "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "production_execution_slot_id": slot["production_execution_slot_id"],
        "predecessor_occurrence_slot_id": slot["predecessor_occurrence_slot_id"],
        "execution_nonce": slot["execution_nonce"],
        "terminal_code": TerminalCode.FULL_GROUND_FALLBACK.value,
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "query_ordinal": QUERY_ORDINAL,
        "source_occurrence_accounting_bundle_id": source_bundle.bundle_id,
        "source_counter_registry_id": source_bundle.work_vectors[0].counter_registry_id,
        "target_counter_registry_id": registry_v9.official_counter_registry_v9().registry_id,
        "source_work_vector_ids": [
            row.work_vector_id for row in source_bundle.work_vectors
        ],
        "source_shared_resource_receipt_ids": [
            row.receipt_id for row in source_bundle.receipt_set.receipts
        ],
        "source_output_inventory": list(inventory),
        "source_output_bytes": source_bundle.fixed_point.output_bytes,
        "production_execution_started_by_this_call": True,
        "preexisting_occurrence_output_used": False,
        "native_v6_counter_records_used": True,
        "registered_v6_to_v9_counter_lift_required": True,
        "historical_summary_translation_used": False,
    }
    receipt = {
        **receipt_payload,
        "production_occurrence_receipt_id": domains.extension_content_id_v180r7(
            domains.CONSTRUCTION_K7_FALLBACK_OCCURRENCE_RECEIPT_V180R7_DOMAIN,
            receipt_payload,
        ),
    }
    raw = _materialize_bundle(
        slot=slot,
        receipt=receipt,
        source_bundle=source_bundle,
        inventory=inventory,
    )
    document = loads_canonical_json(raw)
    if type(document) is not dict:
        raise AssertionError("fallback terminal bundle is not an object")
    return FullGroundFallbackProductionTerminalBundleV180r7(
        _ISSUER,
        raw,
        document["production_terminal_bundle_id"],
    )


__all__ = (
    "ConstructionK7FullGroundFallbackFinalizerV180r7Error",
    "FullGroundFallbackProductionTerminalBundleV180r7",
    "run_full_ground_fallback_production_occurrence_v180r7",
)
