"""Fresh V9 terminal finalization for preregistered V180r3 executions.

The first public adapter executes the exact V34 production site in a new
output tree, immediately performs its existing independent replay, and then
aggregates the replayed operational CounterRecords into one V180r3 terminal
WorkVector.  It never accepts historical campaign bytes or a caller-created
counter mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r3 as domains
from acfqp import construction_k7_standard_2048_expression_full_accounted_campaign_v34 as v34_campaign
from acfqp import construction_k7_standard_2048_expression_full_accounted_independent_verifier_v34 as v34_verifier
from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    NativeZeroAttestationV1,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope, derive_actual_projection_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


MAXIMUM_FIXED_POINT_ITERATIONS = 32


class ConstructionK7AllPathProductionTerminalFinalizerV180r3Error(RuntimeError):
    """A fresh site execution, V9 record, or terminal fixed point changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AllPathProductionTerminalFinalizerV180r3Error(message)


def _slot(code: TerminalCode) -> dict[str, Any]:
    frozen = protocol.freeze_all_path_production_execution_protocol_v180r3()
    rows = frozen.to_document()["production_execution_slots"]
    matches = [row for row in rows if row["terminal_code"] == code.value]
    if len(matches) != 1:
        _fail("V180r3 execution protocol lost its terminal slot")
    return matches[0]


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


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
    return tuple(rows)


def _operational_vectors(root: Path) -> tuple[WorkVectorV1, ...]:
    registry = registry_v9.official_counter_registry_v9()
    vectors = []
    for path in sorted(item for item in root.rglob("*.json") if item.is_file()):
        document = _canonical_object(path.read_bytes(), path.name)
        measurement = document.get("measurement")
        vector_document = document.get("work_vector")
        if not isinstance(measurement, Mapping) or not isinstance(
            vector_document, Mapping
        ):
            continue
        if measurement.get("lane") != LaneEnum.OPERATIONAL.value:
            continue
        vector = WorkVectorV1.from_dict(vector_document, registry)
        if vector.counter_registry_id != registry.registry_id:
            _fail("V34 operational vector is not V9")
        vectors.append(vector)
    if len(vectors) != 45 or len({row.work_vector_id for row in vectors}) != 45:
        _fail("V34 operational WorkVector denominator changed")
    return tuple(vectors)


def _aggregate_values(vectors: Sequence[WorkVectorV1]) -> dict[str, int]:
    registry = registry_v9.official_counter_registry_v9()
    if type(vectors) not in {tuple, list} or not vectors:
        _fail("production occurrence has no operational WorkVector")
    result = {path: 0 for path in registry.by_path}
    for vector in vectors:
        registry.validate_vector(vector)
        for path, value in vector.values.items():
            if registry.by_path[path].reducer is ReducerEnum.MAX:
                result[path] = max(result[path], value)
            else:
                result[path] += value
    return result


def _work_chain(
    *,
    subject_id: str,
    values: Mapping[str, int],
    recorder_id: str,
) -> tuple[WorkVectorV1, Any, Any, NativeZeroAttestationV1]:
    registry = registry_v9.official_counter_registry_v9()
    records = tuple(
        CounterRecordV1.observe(
            registry,
            path,
            values[path],
            recorder_id=recorder_id,
        )
        for path in sorted(registry.by_path)
    )
    vector = WorkVectorV1(
        registry.registry_id,
        subject_id,
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        records,
    )
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry,
        comparison_profile,
    )
    comparison, proof = derive_actual_projection_v1(
        vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
    )
    return vector, comparison, proof, NativeZeroAttestationV1.derive(vector, registry)


def _materialize_bundle(
    *,
    slot: Mapping[str, Any],
    receipt: Mapping[str, Any],
    source_vectors: Sequence[WorkVectorV1],
    source_verification: Mapping[str, Any],
    source_campaign: Mapping[str, Any],
) -> bytes:
    base_values = _aggregate_values(source_vectors)
    source_output_bytes = base_values["io.output_bytes"]
    guess = 0
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        values = dict(base_values)
        values["io.output_bytes"] = source_output_bytes + guess
        vector, comparison, proof, zero = _work_chain(
            subject_id=receipt["production_occurrence_receipt_id"],
            values=values,
            recorder_id=receipt["production_occurrence_receipt_id"],
        )
        payload = {
            "schema": "acfqp.all_path_production_terminal_bundle.v180r3",
            "formalization_contract_id": contract.EXPECTED_CONTRACT_ID,
            "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
            "production_execution_slot": dict(slot),
            "terminal_code": slot["terminal_code"],
            "production_occurrence_receipt": dict(receipt),
            "source_campaign": dict(source_campaign),
            "source_independent_verification": dict(source_verification),
            "source_operational_work_vectors": [
                row.to_dict() for row in source_vectors
            ],
            "terminal_work_vector": vector.to_dict(),
            "terminal_comparison_vector": comparison.to_dict(),
            "terminal_actual_projection_proof": proof.to_dict(),
            "terminal_native_zero_attestation": zero.to_dict(),
            "source_output_bytes": source_output_bytes,
            "finalizer_output_bytes": guess,
            "output_bytes_fixed_point": source_output_bytes + guess,
            "fixed_point_iteration": iteration,
            "fresh_v180r3_observed_occurrence_present": True,
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
            "production_terminal_bundle_id": domains.extension_content_id_v180r3(
                domains.CONSTRUCTION_K7_PRODUCTION_TERMINAL_BUNDLE_V180R3_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("V180r3 terminal output fixed point did not converge")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProductionTerminalBundleV180r3:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    terminal_code: TerminalCode
    production_terminal_bundle_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("production terminal bundle is not issuer-created")

    def to_document(self) -> dict[str, Any]:
        return _canonical_object(self.canonical_bytes, "production terminal bundle")


def run_v34_abstract_certified_production_occurrence_v180r3(
    output_root: Path,
) -> ProductionTerminalBundleV180r3:
    """Execute, independently replay, and finalize the fresh V34 site once."""

    if type(output_root) is not Path or output_root.exists():
        _fail("V180r3 V34 output root must be a new absent Path")
    slot = _slot(TerminalCode.ABSTRACT_CERTIFIED)
    result = v34_campaign.run_standard_2048_expression_full_accounted_campaign_v34(
        output_root
    )
    verified = (
        v34_verifier.verify_standard_2048_expression_full_accounting_bytes_independently_v34(
            result.canonical_bytes,
            output_root,
        )
    )
    campaign_document = result.to_document()
    verification_document = verified.to_document()
    if (
        result.campaign_id != v34_campaign.EXPECTED_CAMPAIGN_ID
        or verified.campaign_id != result.campaign_id
        or verified.verification_id != v34_verifier.EXPECTED_VERIFICATION_ID
    ):
        _fail("fresh V34 execution and independent replay crossed identities")
    vectors = _operational_vectors(output_root)
    inventory = _output_inventory(output_root)
    receipt_payload = {
        "schema": "acfqp.all_path_production_occurrence_receipt.v180r3",
        "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "production_execution_slot_id": slot["production_execution_slot_id"],
        "predecessor_occurrence_slot_id": slot["predecessor_occurrence_slot_id"],
        "execution_nonce": slot["execution_nonce"],
        "terminal_code": TerminalCode.ABSTRACT_CERTIFIED.value,
        "source_campaign_id": result.campaign_id,
        "source_campaign_byte_count": len(result.canonical_bytes),
        "source_campaign_sha256": hashlib.sha256(result.canonical_bytes).hexdigest(),
        "source_verification_id": verified.verification_id,
        "source_verification_byte_count": len(verified.canonical_bytes),
        "source_verification_sha256": hashlib.sha256(
            verified.canonical_bytes
        ).hexdigest(),
        "source_output_inventory": list(inventory),
        "source_operational_work_vector_ids": [
            row.work_vector_id for row in vectors
        ],
        "source_operational_work_vector_count": len(vectors),
        "source_counter_record_count": sum(len(row.records) for row in vectors),
        "production_execution_started_by_this_call": True,
        "preexisting_retained_output_used": False,
        "native_v9_counter_records_used": True,
        "historical_summary_translation_used": False,
    }
    receipt = {
        **receipt_payload,
        "production_occurrence_receipt_id": domains.extension_content_id_v180r3(
            domains.CONSTRUCTION_K7_PRODUCTION_OCCURRENCE_RECEIPT_V180R3_DOMAIN,
            receipt_payload,
        ),
    }
    raw = _materialize_bundle(
        slot=slot,
        receipt=receipt,
        source_vectors=vectors,
        source_verification=verification_document,
        source_campaign=campaign_document,
    )
    document = _canonical_object(raw, "V34 production terminal bundle")
    return ProductionTerminalBundleV180r3(
        _ISSUER,
        raw,
        TerminalCode.ABSTRACT_CERTIFIED,
        document["production_terminal_bundle_id"],
    )


__all__ = (
    "ConstructionK7AllPathProductionTerminalFinalizerV180r3Error",
    "ProductionTerminalBundleV180r3",
    "run_v34_abstract_certified_production_occurrence_v180r3",
)
