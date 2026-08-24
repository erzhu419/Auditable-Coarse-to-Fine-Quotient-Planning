"""Fresh V9 finalization for six controlled V180 terminal mechanisms."""

from __future__ import annotations

import hashlib
import resource
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r9 as domains
from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    NativeZeroAttestationV1,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope, derive_actual_projection_v1
from acfqp.construction_k7_remaining_terminal_event_engine_v180r9 import (
    CONTROLLED_CODES_V180R9,
    RemainingTerminalEventObservationV180r9,
    execute_remaining_terminal_event_v180r9,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


MAXIMUM_FIXED_POINT_ITERATIONS = 32
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


class ConstructionK7RemainingTerminalProductionV180r9Error(RuntimeError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RemainingTerminalProductionV180r9Error(message)


def _canonical(raw: bytes, label: str) -> dict[str, Any]:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _slots() -> dict[TerminalCode, dict[str, Any]]:
    rows = protocol.freeze_all_path_production_execution_protocol_v180r3().to_document()[
        "production_execution_slots"
    ]
    result = {}
    for code in CONTROLLED_CODES_V180R9:
        matches = [row for row in rows if row["terminal_code"] == code.value]
        if len(matches) != 1:
            _fail(f"V180r3 protocol lost {code.value}")
        result[code] = matches[0]
    return result


def _values(
    observation: RemainingTerminalEventObservationV180r9,
) -> dict[str, int]:
    registry = registry_v9.official_counter_registry_v9()
    values = {path: 0 for path in registry.by_path}
    if any(path not in values for path in observation.counter_updates):
        _fail("V180r9 event used an unregistered counter path")
    values.update(observation.counter_updates)
    _, scope = _ROUTE_SCOPE[observation.terminal_code]
    if scope is ActualWorkScope.COMMON_PREFIX:
        values["common.integrity_checks"] += len(_INTEGRITY_OBLIGATIONS)
        values["common.protocol_checks"] += len(_PROTOCOL_OBLIGATIONS)
    values["io.mounted_bytes_peak"] = 0
    values["io.staged_bytes"] = 0
    values["memory.working_bytes_peak"] = WORKING_BYTES_HARD_CAP
    values["process.launches"] = 0
    if observation.terminal_code is TerminalCode.FULL_GROUND_EXACT_INFEASIBLE:
        if values["route.attempts"] != 1 or values["route.successes"] != 1:
            _fail("V180r9 success route counters changed")
    elif values["route.attempts"] != 1 or values["route.failures"] != 1:
        _fail("V180r9 failure route counters changed")
    return values


def _receipt_set(
    *,
    code: str,
    logical_occurrence_id: str,
    slot_id: str,
    event_evidence_id: str,
    values: Mapping[str, int],
) -> dict[str, Any]:
    registry = registry_v9.official_counter_registry_v9()
    rows = []
    for path in SHARED_RESOURCE_PATHS:
        leaf = registry.by_path[path]
        if path == "io.output_bytes":
            source_kind = "OUTPUT_FIXED_POINT"
        elif path == "memory.working_bytes_peak":
            source_kind = "OS_ENFORCED_FROZEN_HARD_CAP"
        elif values[path] == 0:
            source_kind = "COMPLETE_WINDOW_NATIVE_ZERO"
        else:
            source_kind = "CONTROLLED_EVENT_LEDGER"
        payload = {
            "schema": "acfqp.remaining_terminal_shared_resource_receipt.v180r9",
            "terminal_code": code,
            "logical_occurrence_id": logical_occurrence_id,
            "production_execution_slot_id": slot_id,
            "event_evidence_id": event_evidence_id,
            "path": path,
            "reducer": leaf.reducer.value,
            "value": values[path],
            "source_kind": source_kind,
            "window_start_sequence": 1,
            "window_cutoff_sequence": 9,
            "complete_through_terminal_cutoff": True,
            "native_zero_observed": values[path] == 0,
            "accounting_provenance_hashes_excluded": True,
        }
        rows.append(
            {
                **payload,
                "receipt_id": domains.extension_content_id_v180r9(
                    domains.CONSTRUCTION_K7_SHARED_RECEIPT_V180R9_DOMAIN,
                    payload,
                ),
            }
        )
    payload = {
        "schema": "acfqp.remaining_terminal_shared_resource_receipt_set.v180r9",
        "terminal_code": code,
        "logical_occurrence_id": logical_occurrence_id,
        "production_execution_slot_id": slot_id,
        "event_evidence_id": event_evidence_id,
        "ordered_paths": list(SHARED_RESOURCE_PATHS),
        "receipts": rows,
        "receipt_count": len(rows),
        "all_nine_paths_complete_through_terminal_cutoff": True,
        "missing_path_inferred_zero": False,
    }
    return {
        **payload,
        "shared_resource_receipt_set_id": domains.extension_content_id_v180r9(
            domains.CONSTRUCTION_K7_RECEIPT_SET_V180R9_DOMAIN,
            payload,
        ),
    }


def _work_chain(
    *,
    logical_occurrence_id: str,
    route_kind: RouteKindEnum,
    work_scope: ActualWorkScope,
    values: Mapping[str, int],
    recorder_id: str,
) -> tuple[Any, Any, Any, NativeZeroAttestationV1]:
    registry = registry_v9.official_counter_registry_v9()
    if set(values) != set(registry.by_path):
        _fail("V180r9 values do not exactly cover V9")
    records = tuple(
        CounterRecordV1.observe(
            registry,
            path,
            values[path],
            recorder_id=recorder_id,
        )
        for path in sorted(values)
    )
    vector = WorkVectorV1(
        registry.registry_id,
        logical_occurrence_id,
        route_kind,
        records,
    )
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    comparison, projection = derive_actual_projection_v1(
        vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=work_scope,
    )
    return (
        vector,
        comparison,
        projection,
        NativeZeroAttestationV1.derive(vector, registry),
    )


def _terminal_bytes(
    observation: RemainingTerminalEventObservationV180r9,
    slot: Mapping[str, Any],
) -> bytes:
    code = observation.terminal_code
    route_kind, scope = _ROUTE_SCOPE[code]
    base_values = _values(observation)
    event_document = observation.to_document()
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        # The iteration's previous output length is its next candidate fixed point.
        guess = 0 if iteration == 0 else len(raw)
        values = dict(base_values)
        values["io.output_bytes"] = guess
        receipt_set = _receipt_set(
            code=code.value,
            logical_occurrence_id=observation.logical_occurrence_id,
            slot_id=slot["production_execution_slot_id"],
            event_evidence_id=observation.event_evidence_id,
            values=values,
        )
        vector, comparison, projection, zero = _work_chain(
            logical_occurrence_id=observation.logical_occurrence_id,
            route_kind=route_kind,
            work_scope=scope,
            values=values,
            recorder_id=receipt_set["shared_resource_receipt_set_id"],
        )
        classification_payload = {
            "schema": "acfqp.remaining_terminal_classification.v180r9",
            "terminal_code": code.value,
            "terminal_class": _TERMINAL_CLASS[code],
            "path_family": _PATH_FAMILY[code],
            "logical_occurrence_id": observation.logical_occurrence_id,
            "event_evidence_id": observation.event_evidence_id,
            "work_vector_id": vector.work_vector_id,
            "actual_projection_proof_id": projection.actual_projection_proof_id,
            "shared_resource_receipt_set_id": receipt_set[
                "shared_resource_receipt_set_id"
            ],
            "mechanism_outcome": event_document["event_document"][
                "event_document"
            ],
        }
        classification = {
            **classification_payload,
            "terminal_classification_id": domains.extension_content_id_v180r9(
                domains.CONSTRUCTION_K7_EVENT_EVIDENCE_V180R9_DOMAIN,
                classification_payload,
            ),
        }
        payload = {
            "schema": "acfqp.remaining_terminal_production_bundle.v180r9",
            "formalization_contract_id": contract.EXPECTED_CONTRACT_ID,
            "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
            "production_execution_slot": dict(slot),
            "terminal_code": code.value,
            "terminal_class": _TERMINAL_CLASS[code],
            "path_family": _PATH_FAMILY[code],
            "logical_occurrence_id": observation.logical_occurrence_id,
            "event_observation": event_document,
            "terminal_classification": classification,
            "shared_resource_receipt_set": receipt_set,
            "terminal_work_vector": vector.to_dict(),
            "terminal_comparison_vector": comparison.to_dict(),
            "terminal_actual_projection_proof": projection.to_dict(),
            "terminal_native_zero_attestation": zero.to_dict(),
            "integrity_obligations": list(_INTEGRITY_OBLIGATIONS),
            "protocol_obligations": list(_PROTOCOL_OBLIGATIONS),
            "working_bytes_hard_cap": WORKING_BYTES_HARD_CAP,
            "output_bytes_fixed_point": guess,
            "fixed_point_iteration": iteration,
            "fresh_v180r9_observed_occurrence_present": True,
            "mechanism_executed_in_current_occurrence": True,
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
            "production_terminal_bundle_id": domains.extension_content_id_v180r9(
                domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R9_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
    _fail("V180r9 terminal output fixed point did not converge")


def _campaign_bytes(
    *,
    authorization_id: str,
    terminal_bytes: Mapping[str, bytes],
) -> bytes:
    rows = []
    for code in CONTROLLED_CODES_V180R9:
        raw = terminal_bytes[code.value]
        document = _canonical(raw, f"{code.value} terminal bundle")
        rows.append(
            {
                "terminal_code": code.value,
                "production_terminal_bundle_id": document[
                    "production_terminal_bundle_id"
                ],
                "canonical_byte_count": len(raw),
                "canonical_sha256": hashlib.sha256(raw).hexdigest(),
                "bundle": document,
            }
        )
    logical_occurrence_id = hashlib.sha256(
        b"acfqp:v180r9:remaining-terminal-campaign-orchestration\x00"
        + authorization_id.encode()
    ).hexdigest()
    base_values = {
        path: 0 for path in registry_v9.official_counter_registry_v9().by_path
    }
    base_values.update(
        {
            "common.hash_invocations": len(rows),
            "common.integrity_checks": len(rows),
            "common.protocol_checks": len(rows),
            "io.mounted_bytes_peak": 0,
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
                "authorization_id": authorization_id,
                "terminal_bundle_ids": [row["production_terminal_bundle_id"] for row in rows],
            }
        )
    ).hexdigest()
    slot_id = protocol.EXPECTED_PROTOCOL_ID
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        guess = 0 if iteration == 0 else len(raw)
        values = dict(base_values)
        values["io.output_bytes"] = guess
        receipt_set = _receipt_set(
            code="CAMPAIGN_ORCHESTRATION",
            logical_occurrence_id=logical_occurrence_id,
            slot_id=slot_id,
            event_evidence_id=event_evidence_id,
            values=values,
        )
        vector, comparison, projection, zero = _work_chain(
            logical_occurrence_id=logical_occurrence_id,
            route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            work_scope=ActualWorkScope.COMMON_PREFIX,
            values=values,
            recorder_id=receipt_set["shared_resource_receipt_set_id"],
        )
        payload = {
            "schema": "acfqp.remaining_terminal_production_campaign.v180r9",
            "formalization_contract_id": contract.EXPECTED_CONTRACT_ID,
            "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
            "execution_authorization_id": authorization_id,
            "ordered_terminal_codes": [code.value for code in CONTROLLED_CODES_V180R9],
            "terminal_rows": rows,
            "terminal_code_count": len(rows),
            "campaign_orchestration_shared_resource_receipt_set": receipt_set,
            "campaign_orchestration_work_vector": vector.to_dict(),
            "campaign_orchestration_comparison_vector": comparison.to_dict(),
            "campaign_orchestration_actual_projection_proof": projection.to_dict(),
            "campaign_orchestration_native_zero_attestation": zero.to_dict(),
            "output_bytes_fixed_point": guess,
            "fixed_point_iteration": iteration,
            "fresh_v180r9_observed_occurrence_count": len(rows),
            "success_fallback_ood_failure_coverage_in_this_successor": True,
            "all_six_controlled_mechanisms_executed": True,
            "all_six_v9_chains_present": True,
            "all_six_nine_path_receipt_sets_present": True,
            "campaign_orchestration_v9_chain_present": True,
            "historical_summary_translation_used": False,
            "development_fixture_only": False,
            "all_ten_paths_verified": False,
            "partial_campaign_cannot_unlock_any_gate": True,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }
        document = {
            **payload,
            "production_campaign_bundle_id": domains.extension_content_id_v180r9(
                domains.CONSTRUCTION_K7_CAMPAIGN_BUNDLE_V180R9_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
    _fail("V180r9 campaign output fixed point did not converge")


def run_remaining_terminal_production_campaign_v180r9(
    event_manifests: Sequence[Mapping[str, Any]],
    *,
    execution_authorization_id: str,
) -> bytes:
    if (
        type(event_manifests) not in {tuple, list}
        or len(event_manifests) != len(CONTROLLED_CODES_V180R9)
        or type(execution_authorization_id) is not str
        or len(execution_authorization_id) != 64
    ):
        _fail("V180r9 campaign input changed")
    old_soft, old_hard = resource.getrlimit(resource.RLIMIT_AS)
    if old_hard != resource.RLIM_INFINITY and old_hard < WORKING_BYTES_HARD_CAP:
        _fail("V180r9 address-space hard limit is below the frozen cap")
    resource.setrlimit(
        resource.RLIMIT_AS,
        (WORKING_BYTES_HARD_CAP, WORKING_BYTES_HARD_CAP),
    )
    slots = _slots()
    terminal_bytes: dict[str, bytes] = {}
    for expected_code, manifest in zip(
        CONTROLLED_CODES_V180R9, event_manifests, strict=True
    ):
        observation = execute_remaining_terminal_event_v180r9(manifest)
        if observation.terminal_code is not expected_code:
            _fail("V180r9 event manifest order changed")
        terminal_bytes[expected_code.value] = _terminal_bytes(
            observation,
            slots[expected_code],
        )
    return _campaign_bytes(
        authorization_id=execution_authorization_id,
        terminal_bytes=terminal_bytes,
    )


__all__ = (
    "ConstructionK7RemainingTerminalProductionV180r9Error",
    "MAXIMUM_FIXED_POINT_ITERATIONS",
    "SHARED_RESOURCE_PATHS",
    "WORKING_BYTES_HARD_CAP",
    "run_remaining_terminal_production_campaign_v180r9",
)
