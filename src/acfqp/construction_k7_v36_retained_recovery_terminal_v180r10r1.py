"""Finish-forward the complete retained V180r10 V36 occurrence."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_all_path_v36_resource_successor_authorization_v180r10 as predecessor_authorization
from acfqp import construction_k7_all_path_v36_resource_successor_failure_freeze_v180r10 as predecessor_failure
from acfqp import construction_k7_domain_registry_extension_v180r10r1 as domains
from acfqp import construction_k7_v36_retained_campaign_reconstructor_v180r10r1 as reconstructor
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


class ConstructionK7V36RetainedRecoveryTerminalV180r10r1Error(RuntimeError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7V36RetainedRecoveryTerminalV180r10r1Error(message)


def _object(raw: bytes, label: str) -> dict[str, Any]:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _slot() -> dict[str, Any]:
    matches = [
        row
        for row in protocol.freeze_all_path_production_execution_protocol_v180r3()
        .to_document()["production_execution_slots"]
        if row["terminal_code"] == TerminalCode.LOCAL_GROUND_RECOVERY.value
    ]
    if len(matches) != 1:
        _fail("V180r10r1 local-recovery slot changed")
    return matches[0]


def _inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path.relative_to(root).as_posix(),
            "canonical_byte_count": len(raw),
            "canonical_sha256": hashlib.sha256(raw).hexdigest(),
        }
        for path in sorted(item for item in root.rglob("*") if item.is_file())
        for raw in (path.read_bytes(),)
    ]


def _operational_vectors(root: Path) -> tuple[WorkVectorV1, ...]:
    registry = registry_v9.official_counter_registry_v9()
    vectors = []
    for path in sorted(item for item in root.rglob("*.json") if item.is_file()):
        document = _object(path.read_bytes(), path.name)
        measurement = document.get("measurement")
        vector_document = document.get("work_vector")
        if not isinstance(measurement, Mapping) or not isinstance(vector_document, Mapping):
            continue
        if measurement.get("lane") != "OPERATIONAL":
            continue
        vector = WorkVectorV1.from_dict(vector_document, registry)
        if vector.counter_registry_id != registry.registry_id:
            _fail("V180r10r1 retained operational vector is not V9")
        vectors.append(vector)
    if (
        len(vectors) != EXPECTED_OPERATIONAL_WORK_VECTOR_COUNT
        or len({row.work_vector_id for row in vectors}) != len(vectors)
    ):
        _fail("V180r10r1 operational WorkVector denominator changed")
    return tuple(vectors)


def _aggregate(vectors: Sequence[WorkVectorV1]) -> dict[str, int]:
    registry = registry_v9.official_counter_registry_v9()
    values = {path: 0 for path in registry.by_path}
    for vector in vectors:
        registry.validate_vector(vector)
        for path, value in vector.values.items():
            if registry.by_path[path].reducer is ReducerEnum.MAX:
                values[path] = max(values[path], value)
            else:
                values[path] += value
    return values


def _work_chain(
    *, subject_id: str, values: Mapping[str, int]
) -> tuple[WorkVectorV1, Any, Any, NativeZeroAttestationV1]:
    registry = registry_v9.official_counter_registry_v9()
    records = tuple(
        CounterRecordV1.observe(registry, path, values[path], recorder_id=subject_id)
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
        work_scope=ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,
    )
    return vector, comparison, proof, NativeZeroAttestationV1.derive(vector, registry)


def _materialize_terminal(
    *,
    recovery_authorization_id: str,
    slot: Mapping[str, Any],
    receipt: Mapping[str, Any],
    predecessor_failure_document: Mapping[str, Any],
    source_campaign: Mapping[str, Any],
    source_verification: Mapping[str, Any],
    source_vectors: Sequence[WorkVectorV1],
) -> bytes:
    base = _aggregate(source_vectors)
    source_output_bytes = base["io.output_bytes"]
    guess = 0
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        values = dict(base)
        values["io.output_bytes"] = source_output_bytes + guess
        vector, comparison, proof, zero = _work_chain(
            subject_id=receipt["retained_occurrence_receipt_id"], values=values
        )
        payload = {
            "schema": "acfqp.v36_retained_finish_forward_terminal.v180r10r1",
            "formalization_contract_id": contract.EXPECTED_CONTRACT_ID,
            "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
            "v36_retained_recovery_authorization_id": recovery_authorization_id,
            "production_execution_slot": dict(slot),
            "terminal_code": TerminalCode.LOCAL_GROUND_RECOVERY.value,
            "preserved_v180r10_failure": dict(predecessor_failure_document),
            "retained_occurrence_receipt": dict(receipt),
            "source_campaign": dict(source_campaign),
            "source_independent_verification": dict(source_verification),
            "source_operational_work_vectors": [row.to_dict() for row in source_vectors],
            "terminal_work_vector": vector.to_dict(),
            "terminal_comparison_vector": comparison.to_dict(),
            "terminal_actual_projection_proof": proof.to_dict(),
            "terminal_native_zero_attestation": zero.to_dict(),
            "source_output_bytes": source_output_bytes,
            "finalizer_output_bytes": guess,
            "output_bytes_fixed_point": source_output_bytes + guess,
            "fixed_point_iteration": iteration,
            "retained_fresh_v180r10_observed_occurrence_present": True,
            "scientific_occurrence_rerun_by_successor": False,
            "post_failure_finish_forward_only": True,
            "certificate_failure_before_local_recovery_observed": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "terminal_predicate_source_field": "operational_target_probability_label_query_count",
            "terminal_work_scope": ActualWorkScope.MARGINAL_ROUTE_AGGREGATE.value,
            "incorrect_missing_field_projection_not_reused": True,
            "operational_lane_literal_repaired": "OPERATIONAL",
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
            "v36_retained_terminal_id": domains.extension_content_id_v180r10r1(
                domains.CONSTRUCTION_K7_V36_RETAINED_TERMINAL_V180R10R1_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("V180r10r1 terminal output fixed point did not converge")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V36RetainedRecoveryTerminalV180r10r1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    terminal_id: str

    def to_document(self) -> dict[str, Any]:
        return _object(self.canonical_bytes, "V180r10r1 retained terminal")


def finish_forward_retained_v36_occurrence_v180r10r1(
    output_root: Path,
    *,
    recovery_authorization_id: str,
) -> V36RetainedRecoveryTerminalV180r10r1:
    if type(recovery_authorization_id) is not str or len(recovery_authorization_id) != 64:
        _fail("V180r10r1 recovery authorization identity is invalid")
    frozen_failure = predecessor_failure.load_frozen_v36_resource_successor_failure_v180r10()
    reconstructed = reconstructor.reconstruct_retained_v36_campaign_v180r10r1(
        output_root, verify_semantics=False
    )
    source_campaign = reconstructed.to_document()
    source_verification = _object(
        reconstructed.v36_verification_bytes, "reconstructed V36 verification"
    )
    v35_campaign = _object(
        reconstructed.v35_campaign_bytes, "reconstructed V35 campaign"
    )
    if not (
        source_campaign["certificate_failure_count"] >= 1
        and source_campaign["operational_target_probability_label_query_count"] >= 1
        and v35_campaign["operational_target_probability_query_count_after_overlay_freeze"] == 0
    ):
        _fail("retained V36 evidence did not observe local recovery")
    vectors = _operational_vectors(output_root)
    slot = _slot()
    inventory = _inventory(output_root)
    receipt_payload = {
        "schema": "acfqp.v36_retained_occurrence_receipt.v180r10r1",
        "v36_retained_recovery_authorization_id": recovery_authorization_id,
        "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "production_execution_slot_id": slot["production_execution_slot_id"],
        "predecessor_occurrence_slot_id": slot["predecessor_occurrence_slot_id"],
        "execution_nonce": slot["execution_nonce"],
        "terminal_code": TerminalCode.LOCAL_GROUND_RECOVERY.value,
        "original_v180r10_execution_authorization_id": predecessor_authorization.EXPECTED_AUTHORIZATION_ID,
        "preserved_v180r10_failure_id": frozen_failure.failure_id,
        "v35_source_campaign_id": reconstructor.V35_CAMPAIGN_ID,
        "v35_source_campaign_byte_count": len(reconstructed.v35_campaign_bytes),
        "v35_source_campaign_sha256": hashlib.sha256(reconstructed.v35_campaign_bytes).hexdigest(),
        "v35_source_verification_id": reconstructor.V35_VERIFICATION_ID,
        "v35_source_verification_byte_count": len(reconstructed.v35_verification_bytes),
        "v35_source_verification_sha256": hashlib.sha256(reconstructed.v35_verification_bytes).hexdigest(),
        "source_campaign_id": reconstructed.campaign_id,
        "source_campaign_byte_count": len(reconstructed.v36_campaign_bytes),
        "source_campaign_sha256": hashlib.sha256(reconstructed.v36_campaign_bytes).hexdigest(),
        "source_verification_id": reconstructed.verification_id,
        "source_verification_byte_count": len(reconstructed.v36_verification_bytes),
        "source_verification_sha256": hashlib.sha256(reconstructed.v36_verification_bytes).hexdigest(),
        "source_output_inventory": inventory,
        "source_operational_work_vector_ids": [row.work_vector_id for row in vectors],
        "source_operational_work_vector_count": len(vectors),
        "source_counter_record_count": sum(len(row.records) for row in vectors),
        "retained_actual_execution_started_by_v180r10": True,
        "scientific_occurrence_rerun_by_v180r10r1": False,
        "campaigns_reconstructed_from_retained_native_bundles": True,
        "source_semantic_replay_required_by_independent_verifier": True,
        "local_recovery_count_source_field": "operational_target_probability_label_query_count",
        "local_recovery_count": source_campaign["operational_target_probability_label_query_count"],
        "terminal_work_scope": ActualWorkScope.MARGINAL_ROUTE_AGGREGATE.value,
        "operational_lane_literal_repaired": "OPERATIONAL",
        "native_v9_counter_records_used": True,
        "historical_summary_translation_used": False,
    }
    receipt = {
        **receipt_payload,
        "retained_occurrence_receipt_id": domains.extension_content_id_v180r10r1(
            domains.CONSTRUCTION_K7_V36_RETAINED_OCCURRENCE_RECEIPT_V180R10R1_DOMAIN,
            receipt_payload,
        ),
    }
    raw = _materialize_terminal(
        recovery_authorization_id=recovery_authorization_id,
        slot=slot,
        receipt=receipt,
        predecessor_failure_document=frozen_failure.to_document(),
        source_campaign=source_campaign,
        source_verification=source_verification,
        source_vectors=vectors,
    )
    document = _object(raw, "V180r10r1 retained terminal")
    return V36RetainedRecoveryTerminalV180r10r1(
        _ISSUER, raw, document["v36_retained_terminal_id"]
    )


__all__ = (
    "ConstructionK7V36RetainedRecoveryTerminalV180r10r1Error",
    "V36RetainedRecoveryTerminalV180r10r1",
    "finish_forward_retained_v36_occurrence_v180r10r1",
)
