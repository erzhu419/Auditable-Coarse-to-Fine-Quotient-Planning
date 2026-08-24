"""Shared V9 accounting finalizer for every registered FQ9 terminal code.

This slice is deliberately outcome-free.  It implements one exact
``CounterRecord -> WorkVector -> ComparisonVector`` boundary for all ten
terminal codes and a fixture-only campaign orchestration boundary.  A caller
must later bind the same finalizer to fresh preregistered production
occurrences before Counter Completeness or economics can be evaluated.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract_v180
from acfqp import construction_k7_domain_registry_extension_v180r1 as domains
from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    NativeZeroAttestationV1,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualWorkScope,
    derive_actual_projection_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "1.0.0"
MAXIMUM_FIXED_POINT_ITERATIONS = 24


class ConstructionK7AllPathTerminalFinalizerV180r1Error(RuntimeError):
    """A terminal observation or its exact V9 finalization changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AllPathTerminalFinalizerV180r1Error(message)


_TERMINAL_CLASS = {
    TerminalCode.ABSTRACT_CERTIFIED: "PLAN_CERTIFICATE",
    TerminalCode.LOCAL_GROUND_RECOVERY: "PLAN_CERTIFICATE",
    TerminalCode.FULL_GROUND_FALLBACK: "PLAN_CERTIFICATE",
    TerminalCode.CACHED_EXACT_INFEASIBLE: "INFEASIBILITY_CERTIFICATE",
    TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: "INFEASIBILITY_CERTIFICATE",
    TerminalCode.INTEGRITY_FAILURE: "ATTEMPT_CLOSURE_NONCERTIFICATE",
    TerminalCode.PROTOCOL_FAILURE: "ATTEMPT_CLOSURE_NONCERTIFICATE",
    TerminalCode.REBUILD_REQUIRED: "ATTEMPT_CLOSURE_NONCERTIFICATE",
    TerminalCode.FALLBACK_CAP_EXHAUSTED: "ATTEMPT_CLOSURE_NONCERTIFICATE",
    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: "ATTEMPT_CLOSURE_NONCERTIFICATE",
}
_PATH_FAMILY = {
    TerminalCode.ABSTRACT_CERTIFIED: "SUCCESS",
    TerminalCode.CACHED_EXACT_INFEASIBLE: "SUCCESS",
    TerminalCode.LOCAL_GROUND_RECOVERY: "FALLBACK",
    TerminalCode.FULL_GROUND_FALLBACK: "FALLBACK",
    TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: "FALLBACK",
    TerminalCode.FALLBACK_CAP_EXHAUSTED: "FALLBACK",
    TerminalCode.REBUILD_REQUIRED: "OOD",
    TerminalCode.INTEGRITY_FAILURE: "FAILURE",
    TerminalCode.PROTOCOL_FAILURE: "FAILURE",
    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: "FAILURE",
}
_ROUTE_AND_SCOPE = {
    TerminalCode.ABSTRACT_CERTIFIED: (
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
    ),
    TerminalCode.LOCAL_GROUND_RECOVERY: (
        RouteKindEnum.LOCAL_ATTEMPT,
        ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    ),
    TerminalCode.FULL_GROUND_FALLBACK: (
        RouteKindEnum.DIRECT_FALLBACK,
        ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    ),
    TerminalCode.CACHED_EXACT_INFEASIBLE: (
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
    ),
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
_SUCCESS_TERMINALS = frozenset(
    code
    for code, terminal_class in _TERMINAL_CLASS.items()
    if terminal_class != "ATTEMPT_CLOSURE_NONCERTIFICATE"
)


def _exact_mapping(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{label} is not one mapping")
    raw = canonical_json_bytes(dict(value))
    replay = loads_canonical_json(raw)
    if type(replay) is not dict:
        raise AssertionError("canonical mapping replay changed")
    return replay


def _counter_values(value: Mapping[str, Any], *, require_native_zero_output: bool) -> dict[str, int]:
    registry = registry_v9.official_counter_registry_v9()
    if not isinstance(value, Mapping) or set(value) != set(registry.by_path):
        _fail("counter values do not exactly cover the V9 registry")
    result = dict(value)
    if any(type(item) is not int or item < 0 for item in result.values()):
        _fail("counter value is not an exact nonnegative integer")
    if require_native_zero_output and result["io.output_bytes"] != 0:
        _fail("pre-finalization output bytes are not native zero")
    return result


def _terminal(value: str) -> TerminalCode:
    try:
        return TerminalCode(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AllPathTerminalFinalizerV180r1Error(
            "terminal code is not registered"
        ) from error


def _observation_payload(
    *,
    subject_id: str,
    terminal_code: TerminalCode,
    values: Mapping[str, int],
    evidence_id: str,
    occurrence_source: str,
) -> dict[str, Any]:
    route_kind, work_scope = _ROUTE_AND_SCOPE[terminal_code]
    return {
        "schema": "acfqp.all_path_terminal_observation.v180r1",
        "schema_version": SCHEMA_VERSION,
        "formalization_contract_id": contract_v180.EXPECTED_CONTRACT_ID,
        "subject_id": subject_id,
        "terminal_code": terminal_code.value,
        "terminal_class": _TERMINAL_CLASS[terminal_code],
        "path_family": _PATH_FAMILY[terminal_code],
        "route_kind": route_kind.value,
        "work_scope": work_scope.value,
        "evidence_id": evidence_id,
        "occurrence_source": occurrence_source,
        "counter_values_before_finalizer_output": [
            {"path": path, "value": values[path]} for path in sorted(values)
        ],
        "all_v9_paths_observed_including_native_zero": True,
        "historical_summary_translation_used": False,
        "fresh_v180_production_occurrence": False,
        "development_fixture_only": occurrence_source == "DEVELOPMENT_FIXTURE",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }


def build_terminal_observation_v180r1(
    *,
    subject_id: str,
    terminal_code: TerminalCode | str,
    counter_values: Mapping[str, int],
    evidence_id: str,
    occurrence_source: str = "DEVELOPMENT_FIXTURE",
) -> dict[str, Any]:
    code = _terminal(terminal_code.value if isinstance(terminal_code, TerminalCode) else terminal_code)
    if type(subject_id) is not str or not subject_id:
        _fail("subject ID changed")
    if type(evidence_id) is not str or len(evidence_id) != 64:
        _fail("evidence ID changed")
    if occurrence_source != "DEVELOPMENT_FIXTURE":
        _fail("fresh production issuance is not available in this slice")
    values = _counter_values(counter_values, require_native_zero_output=True)
    expected_success = int(code in _SUCCESS_TERMINALS)
    if (
        values["route.attempts"] != 1
        or values["route.successes"] != expected_success
        or values["route.failures"] != 1 - expected_success
    ):
        _fail("terminal fixture route reconciliation changed")
    payload = _observation_payload(
        subject_id=subject_id,
        terminal_code=code,
        values=values,
        evidence_id=evidence_id,
        occurrence_source=occurrence_source,
    )
    return {
        **payload,
        "terminal_observation_id": domains.extension_content_id_v180r1(
            domains.CONSTRUCTION_K7_TERMINAL_OBSERVATION_V180R1_DOMAIN,
            payload,
        ),
    }


def _values_from_observation(document: Mapping[str, Any]) -> dict[str, int]:
    expected = set(_observation_payload(
        subject_id="x",
        terminal_code=TerminalCode.ABSTRACT_CERTIFIED,
        values={path: 0 for path in registry_v9.official_counter_registry_v9().by_path},
        evidence_id="0" * 64,
        occurrence_source="DEVELOPMENT_FIXTURE",
    )) | {"terminal_observation_id"}
    if not isinstance(document, Mapping) or set(document) != expected:
        _fail("terminal observation field set changed")
    rows = document["counter_values_before_finalizer_output"]
    if not isinstance(rows, list) or any(
        not isinstance(row, Mapping) or set(row) != {"path", "value"}
        for row in rows
    ):
        _fail("terminal observation counter rows changed")
    values = {row["path"]: row["value"] for row in rows}
    if len(values) != len(rows):
        _fail("terminal observation repeats a counter path")
    return _counter_values(values, require_native_zero_output=True)


def verify_terminal_observation_v180r1(document: Mapping[str, Any]) -> dict[str, Any]:
    values = _values_from_observation(document)
    code = _terminal(document["terminal_code"])
    expected = build_terminal_observation_v180r1(
        subject_id=document["subject_id"],
        terminal_code=code,
        counter_values=values,
        evidence_id=document["evidence_id"],
        occurrence_source=document["occurrence_source"],
    )
    if _exact_mapping(document, "terminal observation") != expected:
        _fail("terminal observation does not match exact reconstruction")
    return expected


def _measurement(
    observation: Mapping[str, Any], values: Mapping[str, int]
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


def _accounting_chain(
    observation: Mapping[str, Any], values: Mapping[str, int]
) -> tuple[dict[str, Any], WorkVectorV1, Any, Any, NativeZeroAttestationV1]:
    registry = registry_v9.official_counter_registry_v9()
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    measurement = _measurement(observation, values)
    records = tuple(
        CounterRecordV1.observe(
            registry,
            path,
            values[path],
            recorder_id=measurement["terminal_measurement_id"],
        )
        for path in sorted(values)
    )
    vector = WorkVectorV1(
        registry.registry_id,
        observation["subject_id"],
        observation["route_kind"],
        records,
    )
    comparison, proof = derive_actual_projection_v1(
        vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=observation["work_scope"],
    )
    return (
        measurement,
        vector,
        comparison,
        proof,
        NativeZeroAttestationV1.derive(vector, registry),
    )


def materialize_terminal_accounting_bundle_v180r1(
    observation_document: Mapping[str, Any],
) -> bytes:
    observation = verify_terminal_observation_v180r1(observation_document)
    base_values = _values_from_observation(observation)
    guess = 0
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        values = dict(base_values)
        values["io.output_bytes"] = guess
        measurement, vector, comparison, proof, zero = _accounting_chain(
            observation, values
        )
        payload = {
            "schema": "acfqp.all_path_terminal_accounting_bundle.v180r1",
            "schema_version": SCHEMA_VERSION,
            "formalization_contract_id": contract_v180.EXPECTED_CONTRACT_ID,
            "terminal_observation": observation,
            "terminal_measurement": measurement,
            "work_vector": vector.to_dict(),
            "comparison_vector": comparison.to_dict(),
            "actual_projection_proof": proof.to_dict(),
            "native_zero_attestation": zero.to_dict(),
            "output_bytes_fixed_point": guess,
            "fixed_point_iteration": iteration,
            "shared_v9_finalizer_implementation_present": True,
            "fresh_v180_observed_occurrence_present": False,
            "development_fixture_only": True,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }
        document = {
            **payload,
            "terminal_accounting_bundle_id": domains.extension_content_id_v180r1(
                domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R1_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("terminal accounting output fixed point did not converge")


def _campaign_observation(terminal_bundle_bytes: Mapping[str, bytes]) -> dict[str, Any]:
    expected_codes = {code.value for code in TerminalCode}
    if set(terminal_bundle_bytes) != expected_codes:
        _fail("fixture campaign does not cover every terminal code")
    rows = []
    for code in TerminalCode:
        raw = terminal_bundle_bytes[code.value]
        if type(raw) is not bytes:
            _fail("fixture terminal bundle is not bytes")
        document = loads_canonical_json(raw)
        if type(document) is not dict or canonical_json_bytes(document) != raw:
            _fail("fixture terminal bundle is not canonical")
        if document.get("terminal_observation", {}).get("terminal_code") != code.value:
            _fail("fixture terminal bundle crossed terminal code")
        rows.append(
            {
                "terminal_code": code.value,
                "terminal_accounting_bundle_id": document.get(
                    "terminal_accounting_bundle_id"
                ),
                "canonical_byte_count": len(raw),
                "canonical_sha256": hashlib.sha256(raw).hexdigest(),
                "bundle": document,
            }
        )
    return {
        "terminal_rows": rows,
        "terminal_code_count": len(rows),
        "path_families": sorted({_PATH_FAMILY[code] for code in TerminalCode}),
    }


def materialize_fixture_campaign_bundle_v180r1(
    terminal_bundle_bytes: Mapping[str, bytes],
) -> bytes:
    campaign_input = _campaign_observation(terminal_bundle_bytes)
    registry = registry_v9.official_counter_registry_v9()
    base_values = {path: 0 for path in registry.by_path}
    base_values["common.hash_invocations"] = len(TerminalCode)
    base_values["common.integrity_checks"] = len(TerminalCode)
    base_values["common.protocol_checks"] = len(TerminalCode)
    base_values["io.read_bytes"] = sum(
        row["canonical_byte_count"] for row in campaign_input["terminal_rows"]
    )
    base_values["route.attempts"] = 1
    base_values["route.successes"] = 1
    guess = 0
    observation = {
        "terminal_observation_id": hashlib.sha256(
            canonical_json_bytes(campaign_input)
        ).hexdigest(),
        "subject_id": "v180r1_fixture_campaign_orchestration",
        "terminal_code": TerminalCode.ABSTRACT_CERTIFIED.value,
        "route_kind": RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE.value,
        "work_scope": ActualWorkScope.COMMON_PREFIX.value,
    }
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        values = dict(base_values)
        values["io.output_bytes"] = guess
        measurement, vector, comparison, proof, zero = _accounting_chain(
            observation, values
        )
        payload = {
            "schema": "acfqp.all_path_fixture_campaign_bundle.v180r1",
            "schema_version": SCHEMA_VERSION,
            "formalization_contract_id": contract_v180.EXPECTED_CONTRACT_ID,
            "campaign_input": campaign_input,
            "orchestration_measurement": measurement,
            "orchestration_work_vector": vector.to_dict(),
            "orchestration_comparison_vector": comparison.to_dict(),
            "orchestration_actual_projection_proof": proof.to_dict(),
            "orchestration_native_zero_attestation": zero.to_dict(),
            "output_bytes_fixed_point": guess,
            "fixed_point_iteration": iteration,
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
        document = {
            **payload,
            "fixture_campaign_bundle_id": domains.extension_content_id_v180r1(
                domains.CONSTRUCTION_K7_CAMPAIGN_BUNDLE_V180R1_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("fixture campaign output fixed point did not converge")


@dataclass(frozen=True, slots=True)
class FixtureCounterValuesV180r1:
    terminal_code: TerminalCode
    values: Mapping[str, int]


def fixture_counter_values_v180r1(
    terminal_code: TerminalCode | str,
) -> FixtureCounterValuesV180r1:
    code = _terminal(terminal_code.value if isinstance(terminal_code, TerminalCode) else terminal_code)
    registry = registry_v9.official_counter_registry_v9()
    values = {path: 0 for path in registry.by_path}
    values["route.attempts"] = 1
    if code in _SUCCESS_TERMINALS:
        values["route.successes"] = 1
    else:
        values["route.failures"] = 1
    return FixtureCounterValuesV180r1(code, values)


__all__ = (
    "ConstructionK7AllPathTerminalFinalizerV180r1Error",
    "build_terminal_observation_v180r1",
    "fixture_counter_values_v180r1",
    "materialize_fixture_campaign_bundle_v180r1",
    "materialize_terminal_accounting_bundle_v180r1",
    "verify_terminal_observation_v180r1",
)
