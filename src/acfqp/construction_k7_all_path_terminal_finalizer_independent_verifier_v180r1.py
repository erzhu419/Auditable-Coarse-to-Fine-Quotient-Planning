"""Producer-free verifier for V180r1 all-terminal V9 finalization."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_domain_registry_extension_v180r1 as domains
from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    LaneEnum,
    NativeZeroAttestationV1,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    verify_actual_projection_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "1.0.0"
FORMALIZATION_CONTRACT_ID = (
    "f392e9178e8c9c69150567ce210ad146ab96d61aa5925c34b133415fa86737fd"
)


class ConstructionK7AllPathTerminalFinalizerIndependentVerifierV180r1Error(
    RuntimeError
):
    """The portable terminal/campaign graph cannot be reconstructed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AllPathTerminalFinalizerIndependentVerifierV180r1Error(
        message
    )


_TERMINAL_CLASS = {
    "ABSTRACT_CERTIFIED": "PLAN_CERTIFICATE",
    "LOCAL_GROUND_RECOVERY": "PLAN_CERTIFICATE",
    "FULL_GROUND_FALLBACK": "PLAN_CERTIFICATE",
    "CACHED_EXACT_INFEASIBLE": "INFEASIBILITY_CERTIFICATE",
    "FULL_GROUND_EXACT_INFEASIBLE": "INFEASIBILITY_CERTIFICATE",
    "INTEGRITY_FAILURE": "ATTEMPT_CLOSURE_NONCERTIFICATE",
    "PROTOCOL_FAILURE": "ATTEMPT_CLOSURE_NONCERTIFICATE",
    "REBUILD_REQUIRED": "ATTEMPT_CLOSURE_NONCERTIFICATE",
    "FALLBACK_CAP_EXHAUSTED": "ATTEMPT_CLOSURE_NONCERTIFICATE",
    "ATTEMPT_BUDGET_EXHAUSTED": "ATTEMPT_CLOSURE_NONCERTIFICATE",
}
_PATH_FAMILY = {
    "ABSTRACT_CERTIFIED": "SUCCESS",
    "CACHED_EXACT_INFEASIBLE": "SUCCESS",
    "LOCAL_GROUND_RECOVERY": "FALLBACK",
    "FULL_GROUND_FALLBACK": "FALLBACK",
    "FULL_GROUND_EXACT_INFEASIBLE": "FALLBACK",
    "FALLBACK_CAP_EXHAUSTED": "FALLBACK",
    "REBUILD_REQUIRED": "OOD",
    "INTEGRITY_FAILURE": "FAILURE",
    "PROTOCOL_FAILURE": "FAILURE",
    "ATTEMPT_BUDGET_EXHAUSTED": "FAILURE",
}
_ROUTE_AND_SCOPE = {
    "ABSTRACT_CERTIFIED": (
        "ABSTRACT_ONLY_CERTIFICATE",
        "ABSTRACT_SELECTED_ROUTE_EXECUTION",
    ),
    "LOCAL_GROUND_RECOVERY": ("LOCAL_ATTEMPT", "MARGINAL_ROUTE_EXECUTION"),
    "FULL_GROUND_FALLBACK": ("DIRECT_FALLBACK", "MARGINAL_ROUTE_EXECUTION"),
    "CACHED_EXACT_INFEASIBLE": (
        "ABSTRACT_ONLY_CERTIFICATE",
        "ABSTRACT_SELECTED_ROUTE_EXECUTION",
    ),
    "FULL_GROUND_EXACT_INFEASIBLE": (
        "DIRECT_FALLBACK",
        "MARGINAL_ROUTE_EXECUTION",
    ),
    "INTEGRITY_FAILURE": ("ABSTRACT_FAILED_PREFIX", "COMMON_PREFIX"),
    "PROTOCOL_FAILURE": ("ABSTRACT_FAILED_PREFIX", "COMMON_PREFIX"),
    "REBUILD_REQUIRED": ("REBUILD", "REBUILD_EXECUTION"),
    "FALLBACK_CAP_EXHAUSTED": (
        "DIRECT_FALLBACK",
        "MARGINAL_ROUTE_EXECUTION",
    ),
    "ATTEMPT_BUDGET_EXHAUSTED": ("ABSTRACT_FAILED_PREFIX", "COMMON_PREFIX"),
}
_SUCCESS_CODES = frozenset(
    code
    for code, terminal_class in _TERMINAL_CLASS.items()
    if terminal_class != "ATTEMPT_CLOSURE_NONCERTIFICATE"
)


def _parse_canonical(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not bytes")
    try:
        document = loads_canonical_json(raw)
    except Exception as error:  # noqa: BLE001 - verifier boundary
        raise ConstructionK7AllPathTerminalFinalizerIndependentVerifierV180r1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} did not round-trip canonically")
    return document


def _fields(document: Mapping[str, Any], expected: set[str], label: str) -> None:
    if not isinstance(document, Mapping) or set(document) != expected:
        _fail(f"{label} field set changed")


_OBSERVATION_FIELDS = {
    "schema",
    "schema_version",
    "formalization_contract_id",
    "subject_id",
    "terminal_code",
    "terminal_class",
    "path_family",
    "route_kind",
    "work_scope",
    "evidence_id",
    "occurrence_source",
    "counter_values_before_finalizer_output",
    "all_v9_paths_observed_including_native_zero",
    "historical_summary_translation_used",
    "fresh_v180_production_occurrence",
    "development_fixture_only",
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "official_scalar_cost",
    "official_N_break_even",
    "official_execution_allowed",
    "terminal_observation_id",
}
_MEASUREMENT_FIELDS = {
    "schema",
    "schema_version",
    "terminal_observation_id",
    "subject_id",
    "terminal_code",
    "measured_values",
    "native_measurement_not_summary_translation",
    "terminal_measurement_id",
}


def _rows_to_values(rows: Any, label: str) -> dict[str, int]:
    if not isinstance(rows, list):
        _fail(f"{label} is not a list")
    values: dict[str, int] = {}
    for row in rows:
        _fields(row, {"path", "value"}, f"{label} row")
        path, value = row["path"], row["value"]
        if (
            type(path) is not str
            or path in values
            or type(value) is not int
            or value < 0
        ):
            _fail(f"{label} row changed")
        values[path] = value
    registry = registry_v9.official_counter_registry_v9()
    if list(values) != sorted(values) or set(values) != set(registry.by_path):
        _fail(f"{label} does not exactly cover sorted V9 paths")
    return values


def _id_without(document: Mapping[str, Any], id_key: str, domain: str) -> str:
    payload = {key: value for key, value in document.items() if key != id_key}
    return domains.extension_content_id_v180r1(domain, payload)


def _verify_observation(document: Mapping[str, Any]) -> dict[str, int]:
    _fields(document, _OBSERVATION_FIELDS, "terminal observation")
    code = document["terminal_code"]
    if code not in _TERMINAL_CLASS:
        _fail("terminal observation code changed")
    route_kind, work_scope = _ROUTE_AND_SCOPE[code]
    expected_scalars = {
        "schema": "acfqp.all_path_terminal_observation.v180r1",
        "schema_version": SCHEMA_VERSION,
        "formalization_contract_id": FORMALIZATION_CONTRACT_ID,
        "terminal_class": _TERMINAL_CLASS[code],
        "path_family": _PATH_FAMILY[code],
        "route_kind": route_kind,
        "work_scope": work_scope,
        "occurrence_source": "DEVELOPMENT_FIXTURE",
        "all_v9_paths_observed_including_native_zero": True,
        "historical_summary_translation_used": False,
        "fresh_v180_production_occurrence": False,
        "development_fixture_only": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    if any(document[key] != value for key, value in expected_scalars.items()):
        _fail("terminal observation semantics changed")
    if (
        type(document["subject_id"]) is not str
        or not document["subject_id"]
        or type(document["evidence_id"]) is not str
        or len(document["evidence_id"]) != 64
    ):
        _fail("terminal observation identity changed")
    values = _rows_to_values(
        document["counter_values_before_finalizer_output"],
        "terminal observation values",
    )
    expected_success = int(code in _SUCCESS_CODES)
    if (
        values["io.output_bytes"] != 0
        or values["route.attempts"] != 1
        or values["route.successes"] != expected_success
        or values["route.failures"] != 1 - expected_success
    ):
        _fail("terminal observation reconciliation changed")
    if document["terminal_observation_id"] != _id_without(
        document,
        "terminal_observation_id",
        domains.CONSTRUCTION_K7_TERMINAL_OBSERVATION_V180R1_DOMAIN,
    ):
        _fail("terminal observation content ID changed")
    return values


def _expected_measurement(
    *, observation: Mapping[str, Any], values: Mapping[str, int]
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.all_path_terminal_measurement.v180r1",
        "schema_version": SCHEMA_VERSION,
        "terminal_observation_id": observation["terminal_observation_id"],
        "subject_id": observation["subject_id"],
        "terminal_code": observation["terminal_code"],
        "measured_values": [
            {"path": path, "value": values[path]} for path in sorted(values)
        ],
        "native_measurement_not_summary_translation": True,
    }
    return {
        **payload,
        "terminal_measurement_id": domains.extension_content_id_v180r1(
            domains.CONSTRUCTION_K7_TERMINAL_MEASUREMENT_V180R1_DOMAIN,
            payload,
        ),
    }


def _verify_chain(
    *,
    observation: Mapping[str, Any],
    measurement: Mapping[str, Any],
    work_vector_document: Mapping[str, Any],
    comparison_document: Mapping[str, Any],
    proof_document: Mapping[str, Any],
    zero_document: Mapping[str, Any],
    expected_values: Mapping[str, int],
) -> WorkVectorV1:
    registry = registry_v9.official_counter_registry_v9()
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    _fields(measurement, _MEASUREMENT_FIELDS, "terminal measurement")
    expected_measurement = _expected_measurement(
        observation=observation, values=expected_values
    )
    if dict(measurement) != expected_measurement:
        _fail("terminal measurement changed")
    try:
        vector = WorkVectorV1.from_dict(work_vector_document, registry)
        comparison = ComparisonVectorV1.from_dict(comparison_document)
        proof = ActualProjectionProofV1.from_dict(proof_document)
        zero = NativeZeroAttestationV1.from_dict(zero_document)
        recomputed = verify_actual_projection_v1(
            proof,
            vector,
            comparison,
            registry,
            comparison_profile,
            actual_profile,
        )
        expected_zero = NativeZeroAttestationV1.derive(vector, registry)
    except Exception as error:  # noqa: BLE001 - verifier boundary
        raise ConstructionK7AllPathTerminalFinalizerIndependentVerifierV180r1Error(
            "V9 accounting chain replay failed"
        ) from error
    if (
        vector.subject_id != observation["subject_id"]
        or vector.route_kind.value != observation["route_kind"]
        or vector.values != dict(expected_values)
        or any(
            row.recorder_id != measurement["terminal_measurement_id"]
            for row in vector.records
        )
        or recomputed != comparison
        or zero != expected_zero
        or proof.work_scope.value != observation["work_scope"]
    ):
        _fail("V9 accounting chain cross-join changed")
    return vector


_TERMINAL_BUNDLE_FIELDS = {
    "schema",
    "schema_version",
    "formalization_contract_id",
    "terminal_observation",
    "terminal_measurement",
    "work_vector",
    "comparison_vector",
    "actual_projection_proof",
    "native_zero_attestation",
    "output_bytes_fixed_point",
    "fixed_point_iteration",
    "shared_v9_finalizer_implementation_present",
    "fresh_v180_observed_occurrence_present",
    "development_fixture_only",
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "official_scalar_cost",
    "official_N_break_even",
    "official_execution_allowed",
    "terminal_accounting_bundle_id",
}


def _verify_terminal_bundle(raw: bytes) -> dict[str, Any]:
    document = _parse_canonical(raw, "terminal accounting bundle")
    _fields(document, _TERMINAL_BUNDLE_FIELDS, "terminal accounting bundle")
    expected_locks = {
        "schema": "acfqp.all_path_terminal_accounting_bundle.v180r1",
        "schema_version": SCHEMA_VERSION,
        "formalization_contract_id": FORMALIZATION_CONTRACT_ID,
        "shared_v9_finalizer_implementation_present": True,
        "fresh_v180_observed_occurrence_present": False,
        "development_fixture_only": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    if any(document[key] != value for key, value in expected_locks.items()):
        _fail("terminal accounting claim lock changed")
    base_values = _verify_observation(document["terminal_observation"])
    values = dict(base_values)
    if (
        type(document["output_bytes_fixed_point"]) is not int
        or document["output_bytes_fixed_point"] != len(raw)
        or type(document["fixed_point_iteration"]) is not int
        or not 0 <= document["fixed_point_iteration"] < 24
    ):
        _fail("terminal output fixed point changed")
    values["io.output_bytes"] = len(raw)
    vector = _verify_chain(
        observation=document["terminal_observation"],
        measurement=document["terminal_measurement"],
        work_vector_document=document["work_vector"],
        comparison_document=document["comparison_vector"],
        proof_document=document["actual_projection_proof"],
        zero_document=document["native_zero_attestation"],
        expected_values=values,
    )
    if vector.value("io.output_bytes") != len(raw):
        _fail("terminal work vector output fixed point changed")
    if document["terminal_accounting_bundle_id"] != _id_without(
        document,
        "terminal_accounting_bundle_id",
        domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R1_DOMAIN,
    ):
        _fail("terminal accounting bundle content ID changed")
    return document


_CAMPAIGN_FIELDS = {
    "schema",
    "schema_version",
    "formalization_contract_id",
    "campaign_input",
    "orchestration_measurement",
    "orchestration_work_vector",
    "orchestration_comparison_vector",
    "orchestration_actual_projection_proof",
    "orchestration_native_zero_attestation",
    "output_bytes_fixed_point",
    "fixed_point_iteration",
    "success_fallback_ood_failure_fixture_coverage_complete",
    "shared_v9_terminal_finalizer_implemented_for_all_ten_codes",
    "fresh_v180_observed_occurrence_count",
    "development_fixture_only",
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "official_scalar_cost",
    "official_N_break_even",
    "official_execution_allowed",
    "fixture_campaign_bundle_id",
}


def verify_fixture_campaign_independently_v180r1(campaign_bytes: bytes) -> bytes:
    document = _parse_canonical(campaign_bytes, "fixture campaign bundle")
    _fields(document, _CAMPAIGN_FIELDS, "fixture campaign bundle")
    expected_locks = {
        "schema": "acfqp.all_path_fixture_campaign_bundle.v180r1",
        "schema_version": SCHEMA_VERSION,
        "formalization_contract_id": FORMALIZATION_CONTRACT_ID,
        "success_fallback_ood_failure_fixture_coverage_complete": True,
        "shared_v9_terminal_finalizer_implemented_for_all_ten_codes": True,
        "fresh_v180_observed_occurrence_count": 0,
        "development_fixture_only": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    if any(document[key] != value for key, value in expected_locks.items()):
        _fail("fixture campaign claim lock changed")
    campaign_input = document["campaign_input"]
    _fields(
        campaign_input,
        {"terminal_rows", "terminal_code_count", "path_families"},
        "fixture campaign input",
    )
    if (
        campaign_input["terminal_code_count"] != len(TerminalCode)
        or campaign_input["path_families"]
        != ["FAILURE", "FALLBACK", "OOD", "SUCCESS"]
        or not isinstance(campaign_input["terminal_rows"], list)
        or len(campaign_input["terminal_rows"]) != len(TerminalCode)
    ):
        _fail("fixture campaign coverage changed")
    terminal_ids: list[str] = []
    total_read = 0
    for expected_code, row in zip(TerminalCode, campaign_input["terminal_rows"]):
        _fields(
            row,
            {
                "terminal_code",
                "terminal_accounting_bundle_id",
                "canonical_byte_count",
                "canonical_sha256",
                "bundle",
            },
            "fixture terminal row",
        )
        raw = canonical_json_bytes(row["bundle"])
        terminal = _verify_terminal_bundle(raw)
        if (
            row["terminal_code"] != expected_code.value
            or terminal["terminal_observation"]["terminal_code"]
            != expected_code.value
            or row["terminal_accounting_bundle_id"]
            != terminal["terminal_accounting_bundle_id"]
            or row["canonical_byte_count"] != len(raw)
            or row["canonical_sha256"] != hashlib.sha256(raw).hexdigest()
        ):
            _fail("fixture terminal row cross-join changed")
        terminal_ids.append(terminal["terminal_accounting_bundle_id"])
        total_read += len(raw)
    registry = registry_v9.official_counter_registry_v9()
    values = {path: 0 for path in registry.by_path}
    values["common.hash_invocations"] = len(TerminalCode)
    values["common.integrity_checks"] = len(TerminalCode)
    values["common.protocol_checks"] = len(TerminalCode)
    values["io.read_bytes"] = total_read
    values["io.output_bytes"] = len(campaign_bytes)
    values["route.attempts"] = 1
    values["route.successes"] = 1
    observation = {
        "terminal_observation_id": hashlib.sha256(
            canonical_json_bytes(campaign_input)
        ).hexdigest(),
        "subject_id": "v180r1_fixture_campaign_orchestration",
        "terminal_code": "ABSTRACT_CERTIFIED",
        "route_kind": RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE.value,
        "work_scope": ActualWorkScope.COMMON_PREFIX.value,
    }
    _verify_chain(
        observation=observation,
        measurement=document["orchestration_measurement"],
        work_vector_document=document["orchestration_work_vector"],
        comparison_document=document["orchestration_comparison_vector"],
        proof_document=document["orchestration_actual_projection_proof"],
        zero_document=document["orchestration_native_zero_attestation"],
        expected_values=values,
    )
    if (
        document["output_bytes_fixed_point"] != len(campaign_bytes)
        or type(document["fixed_point_iteration"]) is not int
        or not 0 <= document["fixed_point_iteration"] < 24
        or document["fixture_campaign_bundle_id"]
        != _id_without(
            document,
            "fixture_campaign_bundle_id",
            domains.CONSTRUCTION_K7_CAMPAIGN_BUNDLE_V180R1_DOMAIN,
        )
    ):
        _fail("fixture campaign fixed point or content ID changed")
    payload = {
        "schema": "acfqp.all_path_terminal_finalizer_verification.v180r1",
        "schema_version": SCHEMA_VERSION,
        "fixture_campaign_bundle_id": document["fixture_campaign_bundle_id"],
        "fixture_campaign_canonical_byte_count": len(campaign_bytes),
        "fixture_campaign_canonical_sha256": hashlib.sha256(campaign_bytes).hexdigest(),
        "terminal_accounting_bundle_ids": terminal_ids,
        "terminal_code_count": len(terminal_ids),
        "producer_module_imported": False,
        "all_terminal_counter_records_replayed": True,
        "all_terminal_work_vectors_replayed": True,
        "all_terminal_comparison_vectors_rederived": True,
        "all_terminal_output_fixed_points_replayed": True,
        "campaign_orchestration_work_vector_replayed": True,
        "fresh_v180_observed_occurrence_count": 0,
        "development_fixture_only": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    verification = {
        **payload,
        "terminal_finalizer_verification_id": domains.extension_content_id_v180r1(
            domains.CONSTRUCTION_K7_VERIFICATION_V180R1_DOMAIN,
            payload,
        ),
    }
    return canonical_json_bytes(verification)


__all__ = (
    "ConstructionK7AllPathTerminalFinalizerIndependentVerifierV180r1Error",
    "verify_fixture_campaign_independently_v180r1",
)
