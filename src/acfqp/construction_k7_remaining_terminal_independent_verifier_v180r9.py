"""Producer-free verification of six V180r9 terminal accounting chains."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r9 as domains
from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    NativeZeroAttestationV1,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    verify_actual_projection_v1,
)
from acfqp.construction_k7_remaining_terminal_event_engine_v180r9 import (
    CONTROLLED_CODES_V180R9,
    RemainingTerminalEventObservationV180r9,
    execute_remaining_terminal_event_v180r9,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


WORKING_BYTES_HARD_CAP = 1024 * 1024 * 1024
SHARED_RESOURCE_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)
_INTEGRITY_OBLIGATIONS = (
    "authorization-and-terminal-slot-joined",
    "event-manifest-canonical-and-source-pinned",
    "controlled-mechanism-executed-current-occurrence",
    "event-evidence-content-id-replayed",
    "v9-registry-and-projection-profiles-replayed",
    "all-counter-leaves-explicit",
    "nine-shared-resource-receipts-complete",
    "output-fixed-point-replayed",
)
_PROTOCOL_OBLIGATIONS = (
    "fresh-logical-occurrence-selected-once",
    "controlled-event-code-matches-registered-slot",
    "event-precedes-terminal-classification",
    "counter-cutoff-precedes-accounting-provenance-hashes",
    "no-historical-summary-translation",
    "no-development-fixture-input",
    "one-terminal-bundle-per-code",
    "same-identity-rerun-after-progress-forbidden",
)
_ROUTE_SCOPE = {
    TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: (
        RouteKindEnum.DIRECT_FALLBACK,
        ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    ),
    TerminalCode.INTEGRITY_FAILURE: (
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        ActualWorkScope.COMMON_PREFIX,
    ),
    TerminalCode.PROTOCOL_FAILURE: (
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        ActualWorkScope.COMMON_PREFIX,
    ),
    TerminalCode.REBUILD_REQUIRED: (
        RouteKindEnum.REBUILD,
        ActualWorkScope.REBUILD_EXECUTION,
    ),
    TerminalCode.FALLBACK_CAP_EXHAUSTED: (
        RouteKindEnum.DIRECT_FALLBACK,
        ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    ),
    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: (
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        ActualWorkScope.COMMON_PREFIX,
    ),
}
_PATH_FAMILY = {
    TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: "FALLBACK",
    TerminalCode.INTEGRITY_FAILURE: "FAILURE",
    TerminalCode.PROTOCOL_FAILURE: "FAILURE",
    TerminalCode.REBUILD_REQUIRED: "OOD",
    TerminalCode.FALLBACK_CAP_EXHAUSTED: "FALLBACK",
    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: "FAILURE",
}
_TERMINAL_CLASS = {
    TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: "INFEASIBILITY_CERTIFICATE",
    TerminalCode.INTEGRITY_FAILURE: "ATTEMPT_CLOSURE_NONCERTIFICATE",
    TerminalCode.PROTOCOL_FAILURE: "ATTEMPT_CLOSURE_NONCERTIFICATE",
    TerminalCode.REBUILD_REQUIRED: "ATTEMPT_CLOSURE_NONCERTIFICATE",
    TerminalCode.FALLBACK_CAP_EXHAUSTED: "ATTEMPT_CLOSURE_NONCERTIFICATE",
    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: "ATTEMPT_CLOSURE_NONCERTIFICATE",
}
_TERMINAL_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "development_fixture_only",
    "fixed_point_iteration",
    "formalization_contract_id",
    "fresh_v180r9_observed_occurrence_present",
    "historical_summary_translation_used",
    "integrity_obligations",
    "logical_occurrence_id",
    "mechanism_executed_in_current_occurrence",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "output_bytes_fixed_point",
    "partial_campaign_cannot_unlock_any_gate",
    "path_family",
    "production_execution_protocol_id",
    "production_execution_slot",
    "production_terminal_bundle_id",
    "protocol_obligations",
    "schema",
    "shared_resource_receipt_set",
    "terminal_actual_projection_proof",
    "terminal_class",
    "terminal_classification",
    "terminal_code",
    "terminal_comparison_vector",
    "terminal_native_zero_attestation",
    "terminal_work_vector",
    "event_observation",
    "working_bytes_hard_cap",
}
_CAMPAIGN_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "all_six_controlled_mechanisms_executed",
    "all_six_nine_path_receipt_sets_present",
    "all_six_v9_chains_present",
    "all_ten_paths_verified",
    "campaign_orchestration_actual_projection_proof",
    "campaign_orchestration_comparison_vector",
    "campaign_orchestration_native_zero_attestation",
    "campaign_orchestration_shared_resource_receipt_set",
    "campaign_orchestration_v9_chain_present",
    "campaign_orchestration_work_vector",
    "development_fixture_only",
    "execution_authorization_id",
    "fixed_point_iteration",
    "formalization_contract_id",
    "fresh_v180r9_observed_occurrence_count",
    "historical_summary_translation_used",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "ordered_terminal_codes",
    "output_bytes_fixed_point",
    "partial_campaign_cannot_unlock_any_gate",
    "production_campaign_bundle_id",
    "production_execution_protocol_id",
    "schema",
    "success_fallback_ood_failure_coverage_in_this_successor",
    "terminal_code_count",
    "terminal_rows",
}


class ConstructionK7RemainingTerminalIndependentVerifierV180r9Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RemainingTerminalIndependentVerifierV180r9Error(message)


def _object(raw: bytes, label: str) -> dict[str, Any]:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _values(
    observation: RemainingTerminalEventObservationV180r9,
    output_bytes: int,
) -> dict[str, int]:
    registry = registry_v9.official_counter_registry_v9()
    values = {path: 0 for path in registry.by_path}
    values.update(observation.counter_updates)
    _, scope = _ROUTE_SCOPE[observation.terminal_code]
    if scope is ActualWorkScope.COMMON_PREFIX:
        values["common.integrity_checks"] += len(_INTEGRITY_OBLIGATIONS)
        values["common.protocol_checks"] += len(_PROTOCOL_OBLIGATIONS)
    values.update(
        {
            "io.mounted_bytes_peak": 0,
            "io.output_bytes": output_bytes,
            "io.staged_bytes": 0,
            "memory.working_bytes_peak": WORKING_BYTES_HARD_CAP,
            "process.launches": 0,
        }
    )
    return values


def _verify_receipts(
    document: Any,
    *,
    code: str,
    logical_occurrence_id: str,
    slot_id: str,
    event_evidence_id: str,
    values: Mapping[str, int],
) -> str:
    expected_set_fields = {
        "schema",
        "terminal_code",
        "logical_occurrence_id",
        "production_execution_slot_id",
        "event_evidence_id",
        "ordered_paths",
        "receipts",
        "receipt_count",
        "all_nine_paths_complete_through_terminal_cutoff",
        "missing_path_inferred_zero",
        "shared_resource_receipt_set_id",
    }
    if type(document) is not dict or set(document) != expected_set_fields:
        _fail("V180r9 receipt-set fields changed")
    rows = document["receipts"]
    if (
        document["schema"]
        != "acfqp.remaining_terminal_shared_resource_receipt_set.v180r9"
        or document["terminal_code"] != code
        or document["logical_occurrence_id"] != logical_occurrence_id
        or document["production_execution_slot_id"] != slot_id
        or document["event_evidence_id"] != event_evidence_id
        or document["ordered_paths"] != list(SHARED_RESOURCE_PATHS)
        or type(rows) is not list
        or len(rows) != 9
        or document["receipt_count"] != 9
        or document["all_nine_paths_complete_through_terminal_cutoff"] is not True
        or document["missing_path_inferred_zero"] is not False
    ):
        _fail("V180r9 receipt-set joins changed")
    expected_row_fields = {
        "schema",
        "terminal_code",
        "logical_occurrence_id",
        "production_execution_slot_id",
        "event_evidence_id",
        "path",
        "reducer",
        "value",
        "source_kind",
        "window_start_sequence",
        "window_cutoff_sequence",
        "complete_through_terminal_cutoff",
        "native_zero_observed",
        "accounting_provenance_hashes_excluded",
        "receipt_id",
    }
    registry = registry_v9.official_counter_registry_v9()
    for path, row in zip(SHARED_RESOURCE_PATHS, rows, strict=True):
        if type(row) is not dict or set(row) != expected_row_fields:
            _fail("V180r9 receipt fields changed")
        payload = dict(row)
        receipt_id = payload.pop("receipt_id")
        if not (
            row["path"] == path
            and row["terminal_code"] == code
            and row["logical_occurrence_id"] == logical_occurrence_id
            and row["production_execution_slot_id"] == slot_id
            and row["event_evidence_id"] == event_evidence_id
            and row["reducer"] == registry.by_path[path].reducer.value
            and row["value"] == values[path]
            and row["window_start_sequence"] == 1
            and row["window_cutoff_sequence"] == 9
            and row["complete_through_terminal_cutoff"] is True
            and row["native_zero_observed"] is (values[path] == 0)
            and row["accounting_provenance_hashes_excluded"] is True
            and receipt_id
            == domains.extension_content_id_v180r9(
                domains.CONSTRUCTION_K7_SHARED_RECEIPT_V180R9_DOMAIN,
                payload,
            )
        ):
            _fail("V180r9 receipt semantics or ID changed")
    payload = dict(document)
    receipt_set_id = payload.pop("shared_resource_receipt_set_id")
    if receipt_set_id != domains.extension_content_id_v180r9(
        domains.CONSTRUCTION_K7_RECEIPT_SET_V180R9_DOMAIN,
        payload,
    ):
        _fail("V180r9 receipt-set content ID changed")
    return receipt_set_id


def _verify_chain(
    *,
    vector_document: Any,
    comparison_document: Any,
    proof_document: Any,
    zero_document: Any,
    expected_values: Mapping[str, int],
    expected_subject_id: str,
    expected_route: RouteKindEnum,
    expected_scope: ActualWorkScope,
    expected_recorder_id: str,
) -> None:
    registry = registry_v9.official_counter_registry_v9()
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    vector = WorkVectorV1.from_dict(vector_document, registry)
    comparison = ComparisonVectorV1.from_dict(comparison_document)
    proof = ActualProjectionProofV1.from_dict(proof_document)
    zero = NativeZeroAttestationV1.from_dict(zero_document)
    if not (
        vector.subject_id == expected_subject_id
        and vector.route_kind is expected_route
        and vector.values == dict(expected_values)
        and all(row.recorder_id == expected_recorder_id for row in vector.records)
        and zero == NativeZeroAttestationV1.derive(vector, registry)
        and proof.work_scope is expected_scope
    ):
        _fail("V180r9 CounterRecord or WorkVector reconstruction changed")
    verify_actual_projection_v1(
        proof,
        vector,
        comparison,
        registry,
        comparison_profile,
        actual_profile,
    )


def _verify_terminal(
    raw: bytes,
    *,
    expected_observation: RemainingTerminalEventObservationV180r9,
    expected_slot: Mapping[str, Any],
) -> dict[str, Any]:
    document = _object(raw, f"{expected_observation.terminal_code.value} terminal")
    code = expected_observation.terminal_code
    if set(document) != _TERMINAL_FIELDS:
        _fail("V180r9 terminal bundle fields changed")
    values = _values(expected_observation, len(raw))
    if not (
        document["schema"] == "acfqp.remaining_terminal_production_bundle.v180r9"
        and document["formalization_contract_id"] == contract.EXPECTED_CONTRACT_ID
        and document["production_execution_protocol_id"] == protocol.EXPECTED_PROTOCOL_ID
        and document["production_execution_slot"] == dict(expected_slot)
        and document["terminal_code"] == code.value
        and document["terminal_class"] == _TERMINAL_CLASS[code]
        and document["path_family"] == _PATH_FAMILY[code]
        and document["logical_occurrence_id"]
        == expected_observation.logical_occurrence_id
        and document["event_observation"] == expected_observation.to_document()
        and document["integrity_obligations"] == list(_INTEGRITY_OBLIGATIONS)
        and document["protocol_obligations"] == list(_PROTOCOL_OBLIGATIONS)
        and document["working_bytes_hard_cap"] == WORKING_BYTES_HARD_CAP
        and document["output_bytes_fixed_point"] == len(raw)
        and document["fresh_v180r9_observed_occurrence_present"] is True
        and document["mechanism_executed_in_current_occurrence"] is True
        and document["historical_summary_translation_used"] is False
        and document["development_fixture_only"] is False
        and document["partial_campaign_cannot_unlock_any_gate"] is True
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["official_execution_allowed"] is False
    ):
        _fail("V180r9 terminal identity, fixed point, or claim lock changed")
    receipt_set_id = _verify_receipts(
        document["shared_resource_receipt_set"],
        code=code.value,
        logical_occurrence_id=expected_observation.logical_occurrence_id,
        slot_id=expected_slot["production_execution_slot_id"],
        event_evidence_id=expected_observation.event_evidence_id,
        values=values,
    )
    route, scope = _ROUTE_SCOPE[code]
    _verify_chain(
        vector_document=document["terminal_work_vector"],
        comparison_document=document["terminal_comparison_vector"],
        proof_document=document["terminal_actual_projection_proof"],
        zero_document=document["terminal_native_zero_attestation"],
        expected_values=values,
        expected_subject_id=expected_observation.logical_occurrence_id,
        expected_route=route,
        expected_scope=scope,
        expected_recorder_id=receipt_set_id,
    )
    classification = document["terminal_classification"]
    if type(classification) is not dict:
        _fail("V180r9 terminal classification changed")
    classification_payload = dict(classification)
    classification_id = classification_payload.pop("terminal_classification_id", None)
    if not (
        set(classification_payload)
        == {
            "schema",
            "terminal_code",
            "terminal_class",
            "path_family",
            "logical_occurrence_id",
            "event_evidence_id",
            "work_vector_id",
            "actual_projection_proof_id",
            "shared_resource_receipt_set_id",
            "mechanism_outcome",
        }
        and classification_payload["terminal_code"] == code.value
        and classification_payload["event_evidence_id"]
        == expected_observation.event_evidence_id
        and classification_payload["shared_resource_receipt_set_id"]
        == receipt_set_id
        and classification_payload["mechanism_outcome"]
        == expected_observation.event_document["event_document"]
        and classification_id
        == domains.extension_content_id_v180r9(
            domains.CONSTRUCTION_K7_EVENT_EVIDENCE_V180R9_DOMAIN,
            classification_payload,
        )
    ):
        _fail("V180r9 terminal classification changed")
    payload = dict(document)
    terminal_id = payload.pop("production_terminal_bundle_id")
    if terminal_id != domains.extension_content_id_v180r9(
        domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R9_DOMAIN,
        payload,
    ):
        _fail("V180r9 terminal bundle content ID changed")
    return document


def verify_remaining_terminal_campaign_independently_v180r9(
    campaign_bytes: bytes,
    *,
    execution_authorization_id: str,
    event_manifests: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    document = _object(campaign_bytes, "V180r9 campaign")
    if set(document) != _CAMPAIGN_FIELDS:
        _fail("V180r9 campaign fields changed")
    if (
        type(event_manifests) not in {tuple, list}
        or len(event_manifests) != len(CONTROLLED_CODES_V180R9)
        or document["execution_authorization_id"] != execution_authorization_id
    ):
        _fail("V180r9 verifier inputs changed")
    protocol_slots = protocol.freeze_all_path_production_execution_protocol_v180r3().to_document()[
        "production_execution_slots"
    ]
    slots = {
        code: next(row for row in protocol_slots if row["terminal_code"] == code.value)
        for code in CONTROLLED_CODES_V180R9
    }
    observations = tuple(
        execute_remaining_terminal_event_v180r9(manifest)
        for manifest in event_manifests
    )
    if tuple(row.terminal_code for row in observations) != CONTROLLED_CODES_V180R9:
        _fail("V180r9 event manifest order changed")
    rows = document["terminal_rows"]
    if type(rows) is not list or len(rows) != len(observations):
        _fail("V180r9 terminal row denominator changed")
    terminal_documents = []
    for row, observation in zip(rows, observations, strict=True):
        if type(row) is not dict or set(row) != {
            "terminal_code",
            "production_terminal_bundle_id",
            "canonical_byte_count",
            "canonical_sha256",
            "bundle",
        }:
            _fail("V180r9 terminal campaign row changed")
        raw = canonical_json_bytes(row["bundle"])
        terminal = _verify_terminal(
            raw,
            expected_observation=observation,
            expected_slot=slots[observation.terminal_code],
        )
        if not (
            row["terminal_code"] == observation.terminal_code.value
            and row["production_terminal_bundle_id"]
            == terminal["production_terminal_bundle_id"]
            and row["canonical_byte_count"] == len(raw)
            and row["canonical_sha256"] == hashlib.sha256(raw).hexdigest()
        ):
            _fail("V180r9 terminal row identity changed")
        terminal_documents.append(terminal)
    logical_occurrence_id = hashlib.sha256(
        b"acfqp:v180r9:remaining-terminal-campaign-orchestration\x00"
        + execution_authorization_id.encode()
    ).hexdigest()
    orchestration_values = {
        path: 0 for path in registry_v9.official_counter_registry_v9().by_path
    }
    orchestration_values.update(
        {
            "common.hash_invocations": len(rows),
            "common.integrity_checks": len(rows),
            "common.protocol_checks": len(rows),
            "io.mounted_bytes_peak": 0,
            "io.output_bytes": len(campaign_bytes),
            "io.read_bytes": sum(row["canonical_byte_count"] for row in rows),
            "io.staged_bytes": 0,
            "memory.working_bytes_peak": WORKING_BYTES_HARD_CAP,
            "process.launches": 0,
            "route.attempts": 1,
            "route.successes": 1,
        }
    )
    event_evidence_id = hashlib.sha256(
        canonical_json_bytes(
            {
                "authorization_id": execution_authorization_id,
                "terminal_bundle_ids": [
                    row["production_terminal_bundle_id"] for row in rows
                ],
            }
        )
    ).hexdigest()
    orchestration_receipt_id = _verify_receipts(
        document["campaign_orchestration_shared_resource_receipt_set"],
        code="CAMPAIGN_ORCHESTRATION",
        logical_occurrence_id=logical_occurrence_id,
        slot_id=protocol.EXPECTED_PROTOCOL_ID,
        event_evidence_id=event_evidence_id,
        values=orchestration_values,
    )
    _verify_chain(
        vector_document=document["campaign_orchestration_work_vector"],
        comparison_document=document["campaign_orchestration_comparison_vector"],
        proof_document=document["campaign_orchestration_actual_projection_proof"],
        zero_document=document["campaign_orchestration_native_zero_attestation"],
        expected_values=orchestration_values,
        expected_subject_id=logical_occurrence_id,
        expected_route=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        expected_scope=ActualWorkScope.COMMON_PREFIX,
        expected_recorder_id=orchestration_receipt_id,
    )
    if not (
        document["schema"] == "acfqp.remaining_terminal_production_campaign.v180r9"
        and document["formalization_contract_id"] == contract.EXPECTED_CONTRACT_ID
        and document["production_execution_protocol_id"] == protocol.EXPECTED_PROTOCOL_ID
        and document["ordered_terminal_codes"]
        == [code.value for code in CONTROLLED_CODES_V180R9]
        and document["terminal_code_count"] == 6
        and document["output_bytes_fixed_point"] == len(campaign_bytes)
        and document["fresh_v180r9_observed_occurrence_count"] == 6
        and document["success_fallback_ood_failure_coverage_in_this_successor"] is True
        and document["all_six_controlled_mechanisms_executed"] is True
        and document["all_six_v9_chains_present"] is True
        and document["all_six_nine_path_receipt_sets_present"] is True
        and document["campaign_orchestration_v9_chain_present"] is True
        and document["historical_summary_translation_used"] is False
        and document["development_fixture_only"] is False
        and document["all_ten_paths_verified"] is False
        and document["partial_campaign_cannot_unlock_any_gate"] is True
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_execution_allowed"] is False
    ):
        _fail("V180r9 campaign fixed point or claim locks changed")
    payload = dict(document)
    campaign_id = payload.pop("production_campaign_bundle_id")
    if campaign_id != domains.extension_content_id_v180r9(
        domains.CONSTRUCTION_K7_CAMPAIGN_BUNDLE_V180R9_DOMAIN,
        payload,
    ):
        _fail("V180r9 campaign content ID changed")
    verification_payload = {
        "schema": "acfqp.remaining_terminal_independent_verification.v180r9",
        "execution_authorization_id": execution_authorization_id,
        "production_campaign_bundle_id": campaign_id,
        "campaign_byte_count": len(campaign_bytes),
        "campaign_sha256": hashlib.sha256(campaign_bytes).hexdigest(),
        "verified_terminal_codes": [code.value for code in CONTROLLED_CODES_V180R9],
        "verified_terminal_count": 6,
        "all_counter_records_replayed": True,
        "all_work_vectors_replayed": True,
        "all_comparison_vectors_replayed": True,
        "all_actual_projection_proofs_replayed": True,
        "all_nine_path_receipt_sets_replayed": True,
        "campaign_orchestration_replayed": True,
        "producer_module_imported": False,
        "historical_summary_translation_used": False,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **verification_payload,
        "verification_id": domains.extension_content_id_v180r9(
            domains.CONSTRUCTION_K7_VERIFICATION_V180R9_DOMAIN,
            verification_payload,
        ),
    }


__all__ = (
    "ConstructionK7RemainingTerminalIndependentVerifierV180r9Error",
    "verify_remaining_terminal_campaign_independently_v180r9",
)
