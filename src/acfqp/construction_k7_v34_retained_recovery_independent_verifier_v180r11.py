"""Producer-free verification of the V180r11 retained V34 finish-forward."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_all_path_v34_execution_authorization_v180r5 as predecessor_authorization
from acfqp import construction_k7_all_path_v34_failure_freeze_v180r5 as predecessor_failure
from acfqp import construction_k7_domain_registry_extension_v180r11 as domains
from acfqp import construction_k7_standard_2048_expression_full_accounted_campaign_v34 as source_campaign
from acfqp import construction_k7_standard_2048_expression_full_accounted_independent_verifier_v34 as source_verifier
from acfqp.accounting_v1 import (
    LaneEnum,
    NativeZeroAttestationV1,
    ReducerEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope, derive_actual_projection_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


_TOP_LEVEL_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "development_fixture_only",
    "finalizer_output_bytes",
    "fixed_point_iteration",
    "formalization_contract_id",
    "historical_summary_translation_used",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "operational_lane_literal_repaired",
    "output_bytes_fixed_point",
    "partial_campaign_cannot_unlock_any_gate",
    "post_failure_finish_forward_only",
    "preserved_v180r5_failure",
    "production_execution_protocol_id",
    "production_execution_slot",
    "retained_fresh_v180r5_observed_occurrence_present",
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
    "terminal_work_vector",
    "v34_retained_recovery_authorization_id",
    "v34_retained_terminal_id",
}
_RECEIPT_FIELDS = {
    "campaign_reconstructed_from_retained_native_bundles",
    "execution_nonce",
    "historical_summary_translation_used",
    "native_v9_counter_records_used",
    "operational_lane_literal_repaired",
    "original_v180r5_execution_authorization_id",
    "predecessor_occurrence_slot_id",
    "preserved_v180r5_failure_id",
    "production_execution_protocol_id",
    "production_execution_slot_id",
    "retained_actual_execution_started_by_v180r5",
    "retained_occurrence_receipt_id",
    "schema",
    "scientific_occurrence_rerun_by_v180r11",
    "source_campaign_byte_count",
    "source_campaign_id",
    "source_campaign_sha256",
    "source_counter_record_count",
    "source_independent_verification_replayed",
    "source_operational_work_vector_count",
    "source_operational_work_vector_ids",
    "source_output_inventory",
    "source_verification_byte_count",
    "source_verification_id",
    "source_verification_sha256",
    "terminal_code",
    "v34_retained_recovery_authorization_id",
}


class ConstructionK7V34RetainedRecoveryIndependentVerifierV180r11Error(
    RuntimeError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7V34RetainedRecoveryIndependentVerifierV180r11Error(
        message
    )


def _object(raw: bytes, label: str) -> dict[str, Any]:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _slot() -> dict[str, Any]:
    rows = protocol.freeze_all_path_production_execution_protocol_v180r3().to_document()[
        "production_execution_slots"
    ]
    matches = [
        row for row in rows if row["terminal_code"] == TerminalCode.ABSTRACT_CERTIFIED.value
    ]
    if len(matches) != 1:
        _fail("V180r11 abstract-certified slot changed")
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
        measurement = document.get("measurement")
        vector_document = document.get("work_vector")
        if not isinstance(measurement, Mapping) or not isinstance(
            vector_document,
            Mapping,
        ):
            continue
        if measurement.get("lane") == "OPERATIONAL":
            rows.append(WorkVectorV1.from_dict(vector_document, registry))
    if len(rows) != 45 or len({row.work_vector_id for row in rows}) != 45:
        _fail("V180r11 replayed operational denominator changed")
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


def verify_v34_retained_recovery_bytes_independently_v180r11(
    terminal_bytes: bytes,
    output_root: Path,
    *,
    recovery_authorization_id: str,
) -> dict[str, Any]:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        _fail("V180r11 retained output root is absent")
    document = _object(terminal_bytes, "V180r11 retained terminal")
    if set(document) != _TOP_LEVEL_FIELDS:
        _fail("V180r11 retained terminal field set changed")
    payload = dict(document)
    terminal_id = payload.pop("v34_retained_terminal_id", None)
    slot = _slot()
    if not (
        terminal_id
        == domains.extension_content_id_v180r11(
            domains.CONSTRUCTION_K7_V34_RETAINED_TERMINAL_V180R11_DOMAIN,
            payload,
        )
        and document["schema"]
        == "acfqp.v34_retained_finish_forward_terminal.v180r11"
        and document["v34_retained_recovery_authorization_id"]
        == recovery_authorization_id
        and document["production_execution_protocol_id"]
        == protocol.EXPECTED_PROTOCOL_ID
        and document["production_execution_slot"] == slot
        and document["terminal_code"] == TerminalCode.ABSTRACT_CERTIFIED.value
    ):
        _fail("V180r11 retained terminal identity changed")
    frozen_failure = predecessor_failure.load_frozen_v34_failure_v180r5()
    if document["preserved_v180r5_failure"] != frozen_failure.to_document():
        _fail("V180r11 predecessor failure binding changed")
    source_campaign_document = document["source_campaign"]
    source_campaign_bytes = canonical_json_bytes(source_campaign_document)
    source_verification_document = document["source_independent_verification"]
    source_verification_bytes = canonical_json_bytes(source_verification_document)
    replayed_source = source_verifier.verify_standard_2048_expression_full_accounting_bytes_independently_v34(
        source_campaign_bytes,
        output_root,
    )
    if not (
        source_campaign_document["expression_full_accounted_campaign_id"]
        == source_campaign.EXPECTED_CAMPAIGN_ID
        and len(source_campaign_bytes) == source_campaign.EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(source_campaign_bytes).hexdigest()
        == source_campaign.EXPECTED_CANONICAL_SHA256
        and replayed_source.canonical_bytes == source_verification_bytes
        and replayed_source.verification_id == source_verifier.EXPECTED_VERIFICATION_ID
    ):
        _fail("V180r11 retained source campaign or replay changed")
    receipt = document["retained_occurrence_receipt"]
    if type(receipt) is not dict or set(receipt) != _RECEIPT_FIELDS:
        _fail("V180r11 retained receipt field set changed")
    receipt_payload = dict(receipt)
    receipt_id = receipt_payload.pop("retained_occurrence_receipt_id", None)
    vectors = _operational_vectors(output_root)
    if not (
        receipt_id
        == domains.extension_content_id_v180r11(
            domains.CONSTRUCTION_K7_V34_RETAINED_OCCURRENCE_RECEIPT_V180R11_DOMAIN,
            receipt_payload,
        )
        and receipt["v34_retained_recovery_authorization_id"]
        == recovery_authorization_id
        and receipt["production_execution_protocol_id"]
        == protocol.EXPECTED_PROTOCOL_ID
        and receipt["production_execution_slot_id"]
        == slot["production_execution_slot_id"]
        and receipt["predecessor_occurrence_slot_id"]
        == slot["predecessor_occurrence_slot_id"]
        and receipt["execution_nonce"] == slot["execution_nonce"]
        and receipt["terminal_code"] == TerminalCode.ABSTRACT_CERTIFIED.value
        and receipt["original_v180r5_execution_authorization_id"]
        == predecessor_authorization.EXPECTED_AUTHORIZATION_ID
        and receipt["preserved_v180r5_failure_id"] == frozen_failure.failure_id
        and receipt["source_campaign_id"] == source_campaign.EXPECTED_CAMPAIGN_ID
        and receipt["source_campaign_byte_count"] == len(source_campaign_bytes)
        and receipt["source_campaign_sha256"]
        == hashlib.sha256(source_campaign_bytes).hexdigest()
        and receipt["source_verification_id"]
        == source_verifier.EXPECTED_VERIFICATION_ID
        and receipt["source_verification_byte_count"]
        == len(source_verification_bytes)
        and receipt["source_verification_sha256"]
        == hashlib.sha256(source_verification_bytes).hexdigest()
        and receipt["source_output_inventory"] == _inventory(output_root)
        and receipt["source_operational_work_vector_ids"]
        == [row.work_vector_id for row in vectors]
        and receipt["source_operational_work_vector_count"] == 45
        and receipt["source_counter_record_count"] == 45 * 269
        and receipt["retained_actual_execution_started_by_v180r5"] is True
        and receipt["scientific_occurrence_rerun_by_v180r11"] is False
        and receipt["campaign_reconstructed_from_retained_native_bundles"] is True
        and receipt["source_independent_verification_replayed"] is True
        and receipt["operational_lane_literal_repaired"] == "OPERATIONAL"
        and receipt["native_v9_counter_records_used"] is True
        and receipt["historical_summary_translation_used"] is False
    ):
        _fail("V180r11 retained receipt semantics changed")
    registry = registry_v9.official_counter_registry_v9()
    embedded_vectors = tuple(
        WorkVectorV1.from_dict(row, registry)
        for row in document["source_operational_work_vectors"]
    )
    if embedded_vectors != vectors:
        _fail("V180r11 embedded and retained WorkVectors differ")
    aggregate = _aggregate(vectors)
    terminal_vector = WorkVectorV1.from_dict(document["terminal_work_vector"], registry)
    expected_values = dict(aggregate)
    expected_values["io.output_bytes"] = aggregate["io.output_bytes"] + len(
        terminal_bytes
    )
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry,
        comparison_profile,
    )
    comparison, proof = derive_actual_projection_v1(
        terminal_vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
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
        and document["output_bytes_fixed_point"]
        == aggregate["io.output_bytes"] + len(terminal_bytes)
        and document["retained_fresh_v180r5_observed_occurrence_present"] is True
        and document["scientific_occurrence_rerun_by_successor"] is False
        and document["post_failure_finish_forward_only"] is True
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
        _fail("V180r11 terminal accounting or claim locks changed")
    verification_payload = {
        "schema": "acfqp.v34_retained_finish_forward_verification.v180r11",
        "v34_retained_recovery_authorization_id": recovery_authorization_id,
        "v34_retained_terminal_id": terminal_id,
        "terminal_byte_count": len(terminal_bytes),
        "terminal_sha256": hashlib.sha256(terminal_bytes).hexdigest(),
        "preserved_v180r5_failure_id": frozen_failure.failure_id,
        "source_campaign_id": source_campaign.EXPECTED_CAMPAIGN_ID,
        "source_verification_id": source_verifier.EXPECTED_VERIFICATION_ID,
        "retained_output_file_count": len(receipt["source_output_inventory"]),
        "operational_work_vector_count": len(vectors),
        "counter_record_count": sum(len(row.records) for row in vectors),
        "source_campaign_replayed_without_recovery_producer_import": True,
        "retained_counter_records_replayed": True,
        "operational_lane_literal_replayed": "OPERATIONAL",
        "terminal_work_vector_reconstructed": True,
        "terminal_comparison_vector_rederived": True,
        "terminal_output_fixed_point_replayed": True,
        "scientific_occurrence_rerun": False,
        "single_terminal_path_verified": True,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    return {
        **verification_payload,
        "verification_id": domains.extension_content_id_v180r11(
            domains.CONSTRUCTION_K7_V34_RETAINED_VERIFICATION_V180R11_DOMAIN,
            verification_payload,
        ),
    }


__all__ = (
    "ConstructionK7V34RetainedRecoveryIndependentVerifierV180r11Error",
    "verify_v34_retained_recovery_bytes_independently_v180r11",
)
