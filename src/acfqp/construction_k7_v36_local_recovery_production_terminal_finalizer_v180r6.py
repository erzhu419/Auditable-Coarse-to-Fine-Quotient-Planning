"""Fresh V36 local-ground-recovery production finalization for V180.

The public adapter regenerates and independently verifies the frozen V35
predecessor, executes V36 into a new output tree, independently replays the
result, and aggregates its fifteen operational V9 WorkVectors.  Historical
summaries and caller-created counter mappings are not accepted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r6 as domains
from acfqp import construction_k7_standard_2048_adaptive_accounted_campaign_v36 as v36_campaign
from acfqp import construction_k7_standard_2048_adaptive_accounted_independent_verifier_v36 as v36_verifier
from acfqp import construction_k7_standard_2048_adaptive_expression_campaign_v35 as v35_campaign
from acfqp import construction_k7_standard_2048_adaptive_expression_independent_verifier_v35 as v35_verifier
from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as v35_preregistration
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
EXPECTED_OPERATIONAL_WORK_VECTOR_COUNT = 15


class ConstructionK7V36ProductionTerminalFinalizerV180r6Error(RuntimeError):
    """The fresh V36 execution, V9 chain, or output fixed point changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7V36ProductionTerminalFinalizerV180r6Error(message)


def _slot() -> dict[str, Any]:
    rows = protocol.freeze_all_path_production_execution_protocol_v180r3().to_document()[
        "production_execution_slots"
    ]
    matches = [
        row
        for row in rows
        if row["terminal_code"] == TerminalCode.LOCAL_GROUND_RECOVERY.value
    ]
    if len(matches) != 1:
        _fail("V180r3 protocol lost the local-recovery slot")
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
            _fail("V36 operational vector is not V9")
        vectors.append(vector)
    if (
        len(vectors) != EXPECTED_OPERATIONAL_WORK_VECTOR_COUNT
        or len({row.work_vector_id for row in vectors}) != len(vectors)
    ):
        _fail("V36 operational WorkVector denominator changed")
    return tuple(vectors)


def _aggregate_values(vectors: Sequence[WorkVectorV1]) -> dict[str, int]:
    registry = registry_v9.official_counter_registry_v9()
    if type(vectors) not in {tuple, list} or not vectors:
        _fail("V36 occurrence has no operational WorkVector")
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
    *, subject_id: str, values: Mapping[str, int], recorder_id: str
) -> tuple[WorkVectorV1, Any, Any, NativeZeroAttestationV1]:
    registry = registry_v9.official_counter_registry_v9()
    records = tuple(
        CounterRecordV1.observe(
            registry, path, values[path], recorder_id=recorder_id
        )
        for path in sorted(registry.by_path)
    )
    vector = WorkVectorV1(
        registry.registry_id,
        subject_id,
        RouteKindEnum.LOCAL_ATTEMPT,
        records,
    )
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    comparison, proof = derive_actual_projection_v1(
        vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
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
            "schema": "acfqp.v36_local_recovery_production_terminal_bundle.v180r6",
            "formalization_contract_id": contract.EXPECTED_CONTRACT_ID,
            "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
            "production_execution_slot": dict(slot),
            "terminal_code": TerminalCode.LOCAL_GROUND_RECOVERY.value,
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
            "fresh_v180r6_observed_occurrence_present": True,
            "certificate_failure_before_local_recovery_observed": True,
            "local_ground_distinction_only_after_certificate_failure": True,
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
            "production_terminal_bundle_id": domains.extension_content_id_v180r6(
                domains.CONSTRUCTION_K7_V36_EXECUTION_TERMINAL_V180R6_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("V180r6 terminal output fixed point did not converge")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V36LocalRecoveryProductionTerminalBundleV180r6:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    production_terminal_bundle_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V36 production terminal bundle is not issuer-created")

    def to_document(self) -> dict[str, Any]:
        return _canonical_object(self.canonical_bytes, "V36 production terminal bundle")


def run_v36_local_ground_recovery_production_occurrence_v180r6(
    output_root: Path,
) -> V36LocalRecoveryProductionTerminalBundleV180r6:
    """Regenerate V35, execute/replay V36, and finalize one fresh path."""

    if not isinstance(output_root, Path) or output_root.exists():
        _fail("V180r6 V36 output root must be a new absent Path")
    slot = _slot()
    predecessor = v35_campaign.run_standard_2048_adaptive_expression_campaign_v35()
    predecessor_verification = (
        v35_verifier.verify_standard_2048_adaptive_expression_campaign_bytes_independently_v35(
            predecessor.canonical_bytes,
            v35_preregistration.freeze_standard_2048_adaptive_expression_preregistration_v35().canonical_bytes,
        )
    )
    result = v36_campaign.run_standard_2048_adaptive_accounted_campaign_v36(
        v35_campaign_bytes=predecessor.canonical_bytes,
        v35_verification_bytes=predecessor_verification.canonical_bytes,
        output_root=output_root,
    )
    verified = v36_verifier.verify_standard_2048_adaptive_accounting_bytes_independently_v36(
        campaign_bytes=result.canonical_bytes,
        output_root=output_root,
        v35_campaign_bytes=predecessor.canonical_bytes,
        v35_verification_bytes=predecessor_verification.canonical_bytes,
    )
    if (
        predecessor.campaign_id != v35_campaign.EXPECTED_CAMPAIGN_ID
        or predecessor_verification.verification_id
        != v35_verifier.EXPECTED_VERIFICATION_ID
        or result.campaign_id != v36_campaign.EXPECTED_CAMPAIGN_ID
        or verified.campaign_id != result.campaign_id
        or verified.verification_id != v36_verifier.EXPECTED_VERIFICATION_ID
    ):
        _fail("fresh V35/V36 execution and replay crossed identities")
    campaign_document = result.to_document()
    if (
        campaign_document.get("certificate_failure_count", 0) < 1
        or campaign_document.get("ground_distinction_query_count", 0) < 1
        or campaign_document.get(
            "operational_target_probability_query_count_after_overlay_freeze"
        )
        != 0
    ):
        _fail("V36 did not observe the registered local-recovery path")
    vectors = _operational_vectors(output_root)
    inventory = _output_inventory(output_root)
    receipt_payload = {
        "schema": "acfqp.v36_local_recovery_production_occurrence_receipt.v180r6",
        "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "production_execution_slot_id": slot["production_execution_slot_id"],
        "predecessor_occurrence_slot_id": slot["predecessor_occurrence_slot_id"],
        "execution_nonce": slot["execution_nonce"],
        "terminal_code": TerminalCode.LOCAL_GROUND_RECOVERY.value,
        "v35_source_campaign_id": predecessor.campaign_id,
        "v35_source_campaign_sha256": hashlib.sha256(
            predecessor.canonical_bytes
        ).hexdigest(),
        "v35_source_verification_id": predecessor_verification.verification_id,
        "v35_source_verification_sha256": hashlib.sha256(
            predecessor_verification.canonical_bytes
        ).hexdigest(),
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
        "production_occurrence_receipt_id": domains.extension_content_id_v180r6(
            domains.CONSTRUCTION_K7_V36_OCCURRENCE_RECEIPT_V180R6_DOMAIN,
            receipt_payload,
        ),
    }
    raw = _materialize_bundle(
        slot=slot,
        receipt=receipt,
        source_vectors=vectors,
        source_verification=verified.to_document(),
        source_campaign=campaign_document,
    )
    document = _canonical_object(raw, "V36 production terminal bundle")
    return V36LocalRecoveryProductionTerminalBundleV180r6(
        _ISSUER,
        raw,
        document["production_terminal_bundle_id"],
    )


__all__ = (
    "ConstructionK7V36ProductionTerminalFinalizerV180r6Error",
    "V36LocalRecoveryProductionTerminalBundleV180r6",
    "run_v36_local_ground_recovery_production_occurrence_v180r6",
)
