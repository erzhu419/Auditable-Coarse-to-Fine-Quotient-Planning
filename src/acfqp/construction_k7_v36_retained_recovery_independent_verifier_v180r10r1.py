"""Producer-free verification of the retained V180r10 V36 finish-forward."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_all_path_v36_resource_successor_authorization_v180r10 as predecessor_authorization
from acfqp import construction_k7_all_path_v36_resource_successor_failure_freeze_v180r10 as predecessor_failure
from acfqp import construction_k7_domain_registry_extension_v180r10r1 as domains
from acfqp import construction_k7_v36_retained_campaign_reconstructor_v180r10r1 as reconstructor
from acfqp.accounting_v1 import LaneEnum, NativeZeroAttestationV1, ReducerEnum, WorkVectorV1
from acfqp.actual_accounting_v1 import ActualWorkScope, derive_actual_projection_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


_TOP_LEVEL_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "certificate_failure_before_local_recovery_observed",
    "development_fixture_only",
    "finalizer_output_bytes",
    "fixed_point_iteration",
    "formalization_contract_id",
    "historical_summary_translation_used",
    "incorrect_missing_field_projection_not_reused",
    "local_ground_distinction_only_after_certificate_failure",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "operational_lane_literal_repaired",
    "output_bytes_fixed_point",
    "partial_campaign_cannot_unlock_any_gate",
    "post_failure_finish_forward_only",
    "preserved_v180r10_failure",
    "production_execution_protocol_id",
    "production_execution_slot",
    "retained_fresh_v180r10_observed_occurrence_present",
    "retained_occurrence_receipt",
    "schema",
    "scientific_occurrence_rerun_by_successor",
    "source_campaign",
    "source_independent_verification",
    "source_operational_work_vectors",
    "source_output_bytes",
    "terminal_actual_projection_proof",
    "terminal_code",
    "terminal_comparison_vector",
    "terminal_native_zero_attestation",
    "terminal_predicate_source_field",
    "terminal_work_scope",
    "terminal_work_vector",
    "v36_retained_recovery_authorization_id",
    "v36_retained_terminal_id",
}
_RECEIPT_FIELDS = {
    "campaigns_reconstructed_from_retained_native_bundles",
    "execution_nonce",
    "historical_summary_translation_used",
    "local_recovery_count",
    "local_recovery_count_source_field",
    "native_v9_counter_records_used",
    "operational_lane_literal_repaired",
    "original_v180r10_execution_authorization_id",
    "predecessor_occurrence_slot_id",
    "preserved_v180r10_failure_id",
    "production_execution_protocol_id",
    "production_execution_slot_id",
    "retained_actual_execution_started_by_v180r10",
    "retained_occurrence_receipt_id",
    "schema",
    "scientific_occurrence_rerun_by_v180r10r1",
    "source_campaign_byte_count",
    "source_campaign_id",
    "source_campaign_sha256",
    "source_counter_record_count",
    "source_operational_work_vector_count",
    "source_operational_work_vector_ids",
    "source_output_inventory",
    "source_semantic_replay_required_by_independent_verifier",
    "source_verification_byte_count",
    "source_verification_id",
    "source_verification_sha256",
    "terminal_code",
    "terminal_work_scope",
    "v35_source_campaign_byte_count",
    "v35_source_campaign_id",
    "v35_source_campaign_sha256",
    "v35_source_verification_byte_count",
    "v35_source_verification_id",
    "v35_source_verification_sha256",
    "v36_retained_recovery_authorization_id",
}


class ConstructionK7V36RetainedRecoveryIndependentVerifierV180r10r1Error(RuntimeError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7V36RetainedRecoveryIndependentVerifierV180r10r1Error(message)


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
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
    rows = []
    for path in sorted(item for item in root.rglob("*.json") if item.is_file()):
        document = _object(path.read_bytes(), path.name)
        if (
            isinstance(document.get("measurement"), Mapping)
            and document["measurement"].get("lane") == "OPERATIONAL"
            and isinstance(document.get("work_vector"), Mapping)
        ):
            rows.append(WorkVectorV1.from_dict(document["work_vector"], registry))
    if len(rows) != 15 or len({row.work_vector_id for row in rows}) != 15:
        _fail("V180r10r1 replayed operational denominator changed")
    return tuple(rows)


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


def verify_v36_retained_recovery_bytes_independently_v180r10r1(
    terminal_bytes: bytes,
    output_root: Path,
    *,
    recovery_authorization_id: str,
) -> dict[str, Any]:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        _fail("V180r10r1 retained output root is absent")
    document = _object(terminal_bytes, "V180r10r1 retained terminal")
    if set(document) != _TOP_LEVEL_FIELDS:
        _fail("V180r10r1 retained terminal field set changed")
    payload = dict(document)
    terminal_id = payload.pop("v36_retained_terminal_id", None)
    slot = _slot()
    if not (
        terminal_id
        == domains.extension_content_id_v180r10r1(
            domains.CONSTRUCTION_K7_V36_RETAINED_TERMINAL_V180R10R1_DOMAIN,
            payload,
        )
        and document["schema"] == "acfqp.v36_retained_finish_forward_terminal.v180r10r1"
        and document["v36_retained_recovery_authorization_id"] == recovery_authorization_id
        and document["production_execution_protocol_id"] == protocol.EXPECTED_PROTOCOL_ID
        and document["production_execution_slot"] == slot
        and document["terminal_code"] == TerminalCode.LOCAL_GROUND_RECOVERY.value
    ):
        _fail("V180r10r1 retained terminal identity changed")
    frozen_failure = predecessor_failure.load_frozen_v36_resource_successor_failure_v180r10()
    if document["preserved_v180r10_failure"] != frozen_failure.to_document():
        _fail("V180r10r1 predecessor failure binding changed")

    reconstructed = reconstructor.reconstruct_retained_v36_campaign_v180r10r1(
        output_root, verify_semantics=True
    )
    source_campaign_bytes = canonical_json_bytes(document["source_campaign"])
    source_verification_bytes = canonical_json_bytes(
        document["source_independent_verification"]
    )
    if not (
        source_campaign_bytes == reconstructed.v36_campaign_bytes
        and source_verification_bytes == reconstructed.v36_verification_bytes
        and reconstructed.semantic_replay_performed is True
    ):
        _fail("V180r10r1 retained source campaign or producer-free replay changed")

    receipt = document["retained_occurrence_receipt"]
    if type(receipt) is not dict or set(receipt) != _RECEIPT_FIELDS:
        _fail("V180r10r1 retained receipt field set changed")
    receipt_payload = dict(receipt)
    receipt_id = receipt_payload.pop("retained_occurrence_receipt_id", None)
    vectors = _operational_vectors(output_root)
    if not (
        receipt_id
        == domains.extension_content_id_v180r10r1(
            domains.CONSTRUCTION_K7_V36_RETAINED_OCCURRENCE_RECEIPT_V180R10R1_DOMAIN,
            receipt_payload,
        )
        and receipt["v36_retained_recovery_authorization_id"] == recovery_authorization_id
        and receipt["production_execution_protocol_id"] == protocol.EXPECTED_PROTOCOL_ID
        and receipt["production_execution_slot_id"] == slot["production_execution_slot_id"]
        and receipt["predecessor_occurrence_slot_id"] == slot["predecessor_occurrence_slot_id"]
        and receipt["execution_nonce"] == slot["execution_nonce"]
        and receipt["terminal_code"] == TerminalCode.LOCAL_GROUND_RECOVERY.value
        and receipt["original_v180r10_execution_authorization_id"] == predecessor_authorization.EXPECTED_AUTHORIZATION_ID
        and receipt["preserved_v180r10_failure_id"] == frozen_failure.failure_id
        and receipt["v35_source_campaign_id"] == reconstructor.V35_CAMPAIGN_ID
        and receipt["v35_source_campaign_byte_count"] == len(reconstructed.v35_campaign_bytes)
        and receipt["v35_source_campaign_sha256"] == hashlib.sha256(reconstructed.v35_campaign_bytes).hexdigest()
        and receipt["v35_source_verification_id"] == reconstructor.V35_VERIFICATION_ID
        and receipt["v35_source_verification_byte_count"] == len(reconstructed.v35_verification_bytes)
        and receipt["v35_source_verification_sha256"] == hashlib.sha256(reconstructed.v35_verification_bytes).hexdigest()
        and receipt["source_campaign_id"] == reconstructor.V36_CAMPAIGN_ID
        and receipt["source_campaign_byte_count"] == len(source_campaign_bytes)
        and receipt["source_campaign_sha256"] == hashlib.sha256(source_campaign_bytes).hexdigest()
        and receipt["source_verification_id"] == reconstructor.V36_VERIFICATION_ID
        and receipt["source_verification_byte_count"] == len(source_verification_bytes)
        and receipt["source_verification_sha256"] == hashlib.sha256(source_verification_bytes).hexdigest()
        and receipt["source_output_inventory"] == _inventory(output_root)
        and receipt["source_operational_work_vector_ids"] == [row.work_vector_id for row in vectors]
        and receipt["source_operational_work_vector_count"] == 15
        and receipt["source_counter_record_count"] == 15 * len(registry_v9.official_counter_registry_v9().leaves)
        and receipt["retained_actual_execution_started_by_v180r10"] is True
        and receipt["scientific_occurrence_rerun_by_v180r10r1"] is False
        and receipt["campaigns_reconstructed_from_retained_native_bundles"] is True
        and receipt["source_semantic_replay_required_by_independent_verifier"] is True
        and receipt["local_recovery_count_source_field"] == "operational_target_probability_label_query_count"
        and receipt["local_recovery_count"] == 6
        and receipt["terminal_work_scope"] == ActualWorkScope.MARGINAL_ROUTE_AGGREGATE.value
        and receipt["native_v9_counter_records_used"] is True
        and receipt["operational_lane_literal_repaired"] == "OPERATIONAL"
        and receipt["historical_summary_translation_used"] is False
    ):
        _fail("V180r10r1 retained receipt semantics changed")

    registry = registry_v9.official_counter_registry_v9()
    embedded = tuple(
        WorkVectorV1.from_dict(row, registry)
        for row in document["source_operational_work_vectors"]
    )
    if embedded != vectors:
        _fail("V180r10r1 embedded and retained WorkVectors differ")
    aggregate = _aggregate(vectors)
    terminal_vector = WorkVectorV1.from_dict(document["terminal_work_vector"], registry)
    expected_values = dict(aggregate)
    expected_values["io.output_bytes"] = aggregate["io.output_bytes"] + len(terminal_bytes)
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    comparison, proof = derive_actual_projection_v1(
        terminal_vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,
    )
    zero = NativeZeroAttestationV1.derive(terminal_vector, registry)
    if not (
        terminal_vector.values == expected_values
        and terminal_vector.subject_id == receipt_id
        and document["terminal_comparison_vector"] == comparison.to_dict()
        and document["terminal_actual_projection_proof"] == proof.to_dict()
        and document["terminal_native_zero_attestation"] == zero.to_dict()
        and document["source_output_bytes"] == aggregate["io.output_bytes"]
        and document["finalizer_output_bytes"] == len(terminal_bytes)
        and document["output_bytes_fixed_point"] == expected_values["io.output_bytes"]
        and document["retained_fresh_v180r10_observed_occurrence_present"] is True
        and document["scientific_occurrence_rerun_by_successor"] is False
        and document["post_failure_finish_forward_only"] is True
        and document["certificate_failure_before_local_recovery_observed"] is True
        and document["local_ground_distinction_only_after_certificate_failure"] is True
        and document["terminal_predicate_source_field"] == "operational_target_probability_label_query_count"
        and document["terminal_work_scope"] == ActualWorkScope.MARGINAL_ROUTE_AGGREGATE.value
        and document["incorrect_missing_field_projection_not_reused"] is True
        and document["operational_lane_literal_repaired"] == "OPERATIONAL"
        and document["historical_summary_translation_used"] is False
        and document["development_fixture_only"] is False
        and document["partial_campaign_cannot_unlock_any_gate"] is True
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["official_execution_allowed"] is False
    ):
        _fail("V180r10r1 terminal accounting or claim locks changed")
    verification_payload = {
        "schema": "acfqp.v36_retained_finish_forward_verification.v180r10r1",
        "v36_retained_recovery_authorization_id": recovery_authorization_id,
        "v36_retained_terminal_id": terminal_id,
        "terminal_byte_count": len(terminal_bytes),
        "terminal_sha256": hashlib.sha256(terminal_bytes).hexdigest(),
        "preserved_v180r10_failure_id": frozen_failure.failure_id,
        "source_campaign_id": reconstructor.V36_CAMPAIGN_ID,
        "source_verification_id": reconstructor.V36_VERIFICATION_ID,
        "retained_output_file_count": len(receipt["source_output_inventory"]),
        "operational_work_vector_count": len(vectors),
        "counter_record_count": sum(len(row.records) for row in vectors),
        "v35_and_v36_campaigns_reconstructed_without_producer_import": True,
        "source_v36_semantics_replayed_producer_free": True,
        "retained_counter_records_replayed": True,
        "terminal_predicate_field_projection_replayed": True,
        "operational_lane_literal_replayed": "OPERATIONAL",
        "terminal_work_vector_reconstructed": True,
        "terminal_work_scope": ActualWorkScope.MARGINAL_ROUTE_AGGREGATE.value,
        "terminal_comparison_vector_rederived": True,
        "terminal_output_fixed_point_replayed": True,
        "certificate_failure_then_local_recovery_verified": True,
        "scientific_occurrence_rerun": False,
        "single_terminal_path_verified": True,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    return {
        **verification_payload,
        "verification_id": domains.extension_content_id_v180r10r1(
            domains.CONSTRUCTION_K7_V36_RETAINED_VERIFICATION_V180R10R1_DOMAIN,
            verification_payload,
        ),
    }


__all__ = (
    "ConstructionK7V36RetainedRecoveryIndependentVerifierV180r10r1Error",
    "verify_v36_retained_recovery_bytes_independently_v180r10r1",
)
