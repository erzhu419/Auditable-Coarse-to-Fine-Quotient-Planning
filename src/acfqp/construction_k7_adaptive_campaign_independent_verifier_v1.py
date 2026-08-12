"""Producer-free replay of committed adaptive campaign accounting bytes.

The verifier imports neither the adaptive campaign runner nor its actual-
accounting producer.  It starts from the five committed directories and the
frozen V7 registry authority, then independently replays native events,
component CounterRecords, all nine shared receipts, 221 path aggregations,
the WorkVector, the 199-term ComparisonVector projection, projection proof,
and physical output-byte fixed-point equality.

This verifies the committed accounting graph.  It does not turn the in-process
measurement mechanisms into an external OS supervisor, so the official
Counter Completeness and economics gates remain NOT_RUN.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import stat
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    ReducerEnum,
    RouteKindEnum,
    SHARED_AXES,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import ActualProjectionProofV1, ActualWorkScope
from acfqp import construction_accounting_registry_v7 as registry_v7
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_COMPONENT_NATIVE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_NATIVE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_OPERATION_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_OUTPUT_RENDERER_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_PATH_AGGREGATION_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_SHARED_MEASUREMENT_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_SET_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_adaptive_campaign_independent_verifier_v1"
PRODUCER_PROFILE_KEY = "construction_k7_adaptive_campaign_actual_accounting_v1"
OCCURRENCE_VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_INDEPENDENT_VERIFICATION_V1_DOMAIN
)
CAMPAIGN_VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
)
if {
    OCCURRENCE_VERIFICATION_DOMAIN,
    CAMPAIGN_VERIFICATION_DOMAIN,
} - PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("adaptive independent-verification domains are not central")

OUTPUT_ROLES = fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
SHARED_PATHS = (
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
EXPECTED_ROWS = (
    (1, "W5_CONSTRUCT", "opaque_graph_w5_v0", "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED", "LOCAL_ATTEMPT"),
    (2, "W5_REUSE", "opaque_graph_w5_v0", "EXISTING_MODEL_REUSED", "ABSTRACT_ONLY_CERTIFICATE"),
    (3, "K6_CONSTRUCT", "opaque_graph_k6_v0", "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED", "LOCAL_ATTEMPT"),
    (4, "K6_REUSE", "opaque_graph_k6_v0", "EXISTING_MODEL_REUSED", "ABSTRACT_ONLY_CERTIFICATE"),
    (5, "K6_MINUS_EDGE_UNSUPPORTED", "opaque_graph_k6_minus_edge_v0", "NO_CERTIFIABLE_CONSTRUCTOR", "ABSTRACT_FAILED_PREFIX"),
)
DERIVED_PATHS = frozenset(
    {
        "process.exit_failures",
        "process.exit_successes",
        "route.attempts",
        "route.failures",
        "route.successes",
        "solver.attempts",
        "solver.failures",
        "solver.successes",
    }
)


class ConstructionK7AdaptiveCampaignIndependentVerifierV1Error(RuntimeError):
    """Committed adaptive accounting bytes do not replay exactly."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AdaptiveCampaignIndependentVerifierV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AdaptiveCampaignIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{label} field set changed")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        _fail(f"{label} must be one exact list")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _read_roles(directory: Path) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    if not directory.is_dir() or directory.is_symlink():
        _fail("adaptive occurrence output is not one physical directory")
    expected_names = {f"{role}.json" for role in OUTPUT_ROLES}
    if {row.name for row in directory.iterdir()} != expected_names:
        _fail("adaptive occurrence output role inventory changed")
    raw_by_role: dict[str, bytes] = {}
    docs: dict[str, dict[str, Any]] = {}
    for role in OUTPUT_ROLES:
        path = directory / f"{role}.json"
        metadata = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_nlink != 1
        ):
            _fail("adaptive output role is not one private immutable regular file")
        raw = path.read_bytes()
        document = loads_canonical_json(raw)
        if type(document) is not dict or canonical_json_bytes(document) != raw:
            _fail("adaptive output role bytes are not canonical")
        if document.get("artifact_role") != role:
            _fail("adaptive output role label changed")
        raw_by_role[role] = raw
        docs[role] = document
    return raw_by_role, docs


def _event(
    document: Any,
    *,
    occurrence_id: str,
    registry: registry_v7.CounterRegistryV7,
) -> tuple[str, str, int, ReducerEnum]:
    row = _exact(
        document,
        {
            "schema",
            "occurrence_id",
            "operation_boundary_id",
            "phase",
            "target_path",
            "emission_call_count",
            "value",
            "reducer",
            "same_window_native_event",
            "adaptive_operation_event_id",
        },
        "adaptive native event",
    )
    if (
        row["schema"] != "acfqp.construction_k7_adaptive_aggregated_operation_event.v1"
        or row["occurrence_id"] != occurrence_id
        or row["phase"] not in {"COMMON_PREFIX", "LOCAL_RECOVERY", "ABSTRACT_CERTIFICATE"}
        or row["same_window_native_event"] is not True
    ):
        _fail("adaptive native event semantics changed")
    _cid(row["operation_boundary_id"], "operation boundary")
    _nonnegative(row["emission_call_count"], "event emission count")
    if row["emission_call_count"] == 0:
        _fail("adaptive event emission count became zero")
    _nonnegative(row["value"], "event value")
    if row["value"] == 0:
        _fail("adaptive event value became zero")
    leaf = registry.by_path.get(row["target_path"])
    if leaf is None or row["reducer"] != leaf.reducer.value:
        _fail("adaptive native event path or reducer changed")
    payload = {key: value for key, value in row.items() if key != "adaptive_operation_event_id"}
    event_id = content_id(CONSTRUCTION_K7_ADAPTIVE_OPERATION_EVENT_V1_DOMAIN, payload)
    if row["adaptive_operation_event_id"] != event_id:
        _fail("adaptive native event content ID changed")
    return event_id, row["target_path"], row["value"], leaf.reducer


def _counter_record(
    document: Any,
    registry: registry_v7.CounterRegistryV7,
) -> CounterRecordV1:
    if type(document) is not dict:
        _fail("adaptive CounterRecord is not one exact object")
    record = CounterRecordV1.from_dict(document)
    leaf = registry.by_path.get(record.path)
    if leaf is None or record.counter_registry_id != registry.registry_id:
        _fail("adaptive CounterRecord crossed its registry")
    record.verify_against(leaf)
    return record


def _component(
    document: Any,
    *,
    occurrence_id: str,
    registry: registry_v7.CounterRegistryV7,
) -> tuple[str, str, dict[str, CounterRecordV1]]:
    row = _exact(
        document,
        {
            "schema",
            "occurrence_id",
            "phase",
            "route_kind",
            "recorder_id",
            "event_ids",
            "counter_record_ids",
            "nonshared_required_counter_count",
            "native_zeroes_explicit",
            "shared_resource_placeholder_zeroes_issued",
            "formal_work_vector_issued",
            "events",
            "counter_records",
            "adaptive_native_component_id",
        },
        "adaptive native component",
    )
    if (
        row["schema"] != "acfqp.construction_k7_adaptive_native_component.v1"
        or row["occurrence_id"] != occurrence_id
        or row["native_zeroes_explicit"] is not True
        or row["shared_resource_placeholder_zeroes_issued"] is not False
        or row["formal_work_vector_issued"] is not False
        or row["route_kind"]
        != {
            "COMMON_PREFIX": "ABSTRACT_FAILED_PREFIX",
            "LOCAL_RECOVERY": "LOCAL_ATTEMPT",
            "ABSTRACT_CERTIFICATE": "ABSTRACT_ONLY_CERTIFICATE",
        }.get(row["phase"])
    ):
        _fail("adaptive native component semantics changed")
    events = [
        _event(item, occurrence_id=occurrence_id, registry=registry)
        for item in _list(row["events"], "component events")
    ]
    records = [
        _counter_record(item, registry)
        for item in _list(row["counter_records"], "component records")
    ]
    expected_paths = tuple(
        path for path in registry.required_paths if path not in SHARED_PATHS
    )
    if (
        row["event_ids"] != [item[0] for item in events]
        or row["counter_record_ids"] != [item.record_id for item in records]
        or tuple(item.path for item in records) != expected_paths
        or row["nonshared_required_counter_count"] != len(expected_paths)
        or any(item.recorder_id != row["recorder_id"] for item in records)
    ):
        _fail("adaptive native component event/record inventory changed")
    event_values: dict[str, int] = {}
    for _event_id, path, value, reducer in events:
        if reducer is ReducerEnum.SUM:
            event_values[path] = event_values.get(path, 0) + value
        else:
            event_values[path] = max(event_values.get(path, 0), value)
    if any(item.value != event_values.get(item.path, 0) for item in records):
        _fail("adaptive component CounterRecords differ from native events")
    payload = {
        key: value
        for key, value in row.items()
        if key not in {"events", "counter_records", "adaptive_native_component_id"}
    }
    component_id = content_id(
        CONSTRUCTION_K7_ADAPTIVE_COMPONENT_NATIVE_ACCOUNTING_V1_DOMAIN,
        payload,
    )
    if row["adaptive_native_component_id"] != component_id:
        _fail("adaptive native component content ID changed")
    return component_id, row["phase"], {item.path: item for item in records}


def _measurement(
    document: Any,
    *,
    occurrence_id: str,
    route_input_bytes: bytes,
    shared_events: list[tuple[str, str, int, ReducerEnum]],
) -> tuple[str, dict[str, int]]:
    row = _exact(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "adaptive_native_occurrence_id",
            "route_input_bytes_sha256",
            "io.read_bytes",
            "common.hash_invocations",
            "common.integrity_checks",
            "common.protocol_checks",
            "io.staged_bytes",
            "process.launches",
            "memory.working_bytes_peak",
            "native_shared_event_ids",
            "read_bytes_kind",
            "working_bytes_kind",
            "same_process_zero_staging_explicit_when_no_worker",
            "complete_window_closed",
            "official_execution_allowed",
            "shared_measurement_id",
        },
        "adaptive shared measurement",
    )
    values = {path: 0 for path in SHARED_PATHS}
    ids: list[str] = []
    for event_id, path, value, reducer in shared_events:
        ids.append(event_id)
        if reducer is ReducerEnum.SUM:
            values[path] += value
        else:
            values[path] = max(values[path], value)
    if (
        row["schema"] != "acfqp.construction_k7_adaptive_shared_measurement.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PRODUCER_PROFILE_KEY
        or row["occurrence_id"] != occurrence_id
        or row["adaptive_native_occurrence_id"] != occurrence_id
        or row["route_input_bytes_sha256"]
        != hashlib.sha256(route_input_bytes).hexdigest()
        or row["io.read_bytes"] != len(route_input_bytes)
        or row["native_shared_event_ids"] != sorted(ids)
        or row["read_bytes_kind"] != "EXACT_CANONICAL_ROUTE_INPUT_ENVELOPE"
        or row["working_bytes_kind"] != "VERIFIED_CONSERVATIVE_UPPER_BOUND"
        or row["same_process_zero_staging_explicit_when_no_worker"] is not True
        or row["complete_window_closed"] is not True
        or row["official_execution_allowed"] is not False
    ):
        _fail("adaptive shared measurement identity or method changed")
    for path in (
        "io.read_bytes",
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "io.staged_bytes",
        "process.launches",
        "memory.working_bytes_peak",
    ):
        if row[path] != values[path]:
            _fail("adaptive shared measurement differs from native events")
    payload = {key: value for key, value in row.items() if key != "shared_measurement_id"}
    measurement_id = content_id(
        CONSTRUCTION_K7_ADAPTIVE_SHARED_MEASUREMENT_V1_DOMAIN,
        payload,
    )
    if row["shared_measurement_id"] != measurement_id:
        _fail("adaptive shared measurement content ID changed")
    return measurement_id, values


def _receipt(
    document: Any,
    *,
    occurrence_id: str,
    measurement_id: str,
    registry: registry_v7.CounterRegistryV7,
) -> tuple[str, str, int, list[str], str, str, str | None]:
    row = _exact(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "shared_measurement_id",
            "path",
            "reducer",
            "value",
            "source_kind",
            "source_evidence_id",
            "native_event_ids",
            "output_fixed_point_profile_id",
            "one_occurrence_charge",
            "official_execution_allowed",
            "shared_resource_receipt_id",
        },
        "adaptive shared receipt",
    )
    leaf = registry.by_path.get(row["path"])
    if (
        row["schema"] != "acfqp.construction_k7_adaptive_shared_receipt.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PRODUCER_PROFILE_KEY
        or row["occurrence_id"] != occurrence_id
        or row["shared_measurement_id"] != measurement_id
        or leaf is None
        or row["path"] not in SHARED_PATHS
        or row["reducer"] != leaf.reducer.value
        or row["one_occurrence_charge"] is not True
        or row["official_execution_allowed"] is not False
    ):
        _fail("adaptive shared receipt identity or reducer changed")
    _nonnegative(row["value"], "shared receipt value")
    native_ids = _list(row["native_event_ids"], "receipt native events")
    if native_ids != sorted(set(native_ids)):
        _fail("adaptive shared receipt repeats native events")
    payload = {key: value for key, value in row.items() if key != "shared_resource_receipt_id"}
    receipt_id = content_id(CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_V1_DOMAIN, payload)
    if row["shared_resource_receipt_id"] != receipt_id:
        _fail("adaptive shared receipt content ID changed")
    return (
        receipt_id,
        row["path"],
        row["value"],
        native_ids,
        row["source_kind"],
        row["source_evidence_id"],
        row["output_fixed_point_profile_id"],
    )


def _aggregation(
    document: Any,
    *,
    occurrence_id: str,
    registry: registry_v7.CounterRegistryV7,
) -> tuple[str, str, int, tuple[str, ...], str, str]:
    row = _exact(
        document,
        {
            "schema",
            "schema_version",
            "occurrence_id",
            "path",
            "reducer",
            "value",
            "component_record_ids",
            "source_kind",
            "source_evidence_id",
            "all_component_instances_retained",
            "path_aggregation_id",
        },
        "adaptive path aggregation",
    )
    leaf = registry.by_path.get(row["path"])
    if (
        row["schema"] != "acfqp.construction_k7_adaptive_path_aggregation.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["occurrence_id"] != occurrence_id
        or leaf is None
        or row["reducer"] != leaf.reducer.value
        or row["all_component_instances_retained"] is not True
    ):
        _fail("adaptive path aggregation identity or reducer changed")
    component_ids = tuple(_list(row["component_record_ids"], "aggregation records"))
    for value in component_ids:
        _cid(value, "aggregation component record")
    _cid(row["source_evidence_id"], "aggregation source")
    _nonnegative(row["value"], "aggregation value")
    payload = {key: value for key, value in row.items() if key != "path_aggregation_id"}
    aggregation_id = content_id(
        CONSTRUCTION_K7_ADAPTIVE_PATH_AGGREGATION_V1_DOMAIN,
        payload,
    )
    if row["path_aggregation_id"] != aggregation_id:
        _fail("adaptive path aggregation content ID changed")
    return (
        aggregation_id,
        row["path"],
        row["value"],
        component_ids,
        row["source_kind"],
        row["source_evidence_id"],
    )


def _project(
    vector: WorkVectorV1,
    comparison: registry_v7.ComparisonProfileV7,
) -> ComparisonVectorV1:
    axes = {axis: 0 for axis in SHARED_AXES}
    for term in comparison.terms:
        contribution = vector.values[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            axes[term.target_axis] += contribution
        else:
            axes[term.target_axis] = max(axes[term.target_axis], contribution)
    return ComparisonVectorV1(
        comparison.comparison_profile_id,
        vector.work_vector_id,
        vector.subject_id,
        vector.route_kind,
        tuple(sorted(axes.items())),
    )


def _derived(outcome: str, process_launches: int) -> dict[str, int]:
    certified = outcome != "NO_CERTIFIABLE_CONSTRUCTOR"
    return {
        "process.exit_failures": 0,
        "process.exit_successes": process_launches,
        "route.attempts": 1,
        "route.failures": 0 if certified else 1,
        "route.successes": 1 if certified else 0,
        "solver.attempts": 1 if certified else 0,
        "solver.failures": 0,
        "solver.successes": 1 if certified else 0,
    }


@dataclass(frozen=True, slots=True)
class AdaptiveOccurrenceIndependentVerificationV1:
    occurrence_id: str
    occurrence_index: int
    occurrence_role: str
    route_kind: str
    receipt_set_id: str
    work_vector_id: str
    comparison_vector_id: str
    projection_proof_id: str
    output_bytes: int
    output_role_sha256: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "verification occurrence"),
            (self.receipt_set_id, "verification receipt set"),
            (self.work_vector_id, "verification work vector"),
            (self.comparison_vector_id, "verification comparison vector"),
            (self.projection_proof_id, "verification projection proof"),
        ):
            _cid(value, label)
        if (
            type(self.occurrence_index) is not int
            or type(self.occurrence_role) is not str
            or self.route_kind not in {item.value for item in RouteKindEnum}
            or type(self.output_role_sha256) is not tuple
            or len(self.output_role_sha256) != len(OUTPUT_ROLES)
            or self.output_bytes <= 0
        ):
            _fail("adaptive occurrence independent verification is malformed")
        for value in self.output_role_sha256:
            _cid(value, "verification output digest")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_occurrence_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "occurrence_index": self.occurrence_index,
            "occurrence_role": self.occurrence_role,
            "route_kind": self.route_kind,
            "shared_resource_receipt_set_id": self.receipt_set_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "actual_projection_proof_id": self.projection_proof_id,
            "io.output_bytes": self.output_bytes,
            "output_role_sha256": list(self.output_role_sha256),
            "native_event_graph_replayed": True,
            "all_nine_shared_receipts_replayed": True,
            "all_required_counter_records_replayed": True,
            "all_operational_projection_terms_replayed": True,
            "physical_output_fixed_point_replayed": True,
            "external_os_measurement_authority_present": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return content_id(OCCURRENCE_VERIFICATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "independent_verification_id": self.verification_id}


def verify_adaptive_occurrence_directory_independently_v1(
    directory: str | Path,
) -> AdaptiveOccurrenceIndependentVerificationV1:
    path = Path(directory)
    raw, docs = _read_roles(path)
    registry = registry_v7.official_counter_registry_v7()
    comparison = registry_v7.official_comparison_profile_v7(registry)
    actual = registry_v7.official_actual_projection_profile_v7(registry, comparison)
    trace = _exact(
        docs["OPERATIONAL_TRACE"],
        {
            "artifact_role",
            "schema",
            "native_occurrence",
            "route_input_envelope",
            "native_components",
            "native_shared_events",
            "shared_measurement",
            "counter_registry",
            "comparison_profile",
            "actual_projection_profile",
            "evaluation_replay_included",
        },
        "adaptive operational trace",
    )
    if (
        trace["schema"] != "acfqp.construction_k7_adaptive_operational_trace.v1"
        or trace["counter_registry"] != registry.to_document()
        or trace["comparison_profile"] != comparison.to_document()
        or trace["actual_projection_profile"] != actual.to_document()
        or trace["evaluation_replay_included"] is not False
    ):
        _fail("adaptive operational trace authority changed")
    native = _exact(
        trace["native_occurrence"],
        {
            "schema",
            "schema_version",
            "preregistration_id",
            "occurrence_index",
            "occurrence_role",
            "context_key",
            "context_id",
            "result_outcome",
            "synthesis_result_id",
            "catalogue_id_before",
            "catalogue_id_after",
            "component_ids",
            "shared_native_event_ids",
            "route_input_bytes_sha256",
            "route_input_byte_count",
            "route_input_envelope_retained_out_of_band",
            "same_window_native_events_present",
            "nonshared_counter_records_complete",
            "shared_resource_receipts_present",
            "formal_work_vectors_issued",
            "counter_completeness_gate_status",
            "official_execution_allowed",
            "adaptive_occurrence_native_accounting_id",
        },
        "adaptive native occurrence summary",
    )
    occurrence_id = _cid(
        native.get("adaptive_occurrence_native_accounting_id"),
        "native occurrence",
    )
    identity = {
        "schema": "acfqp.construction_k7_adaptive_occurrence_identity.v1",
        "preregistration_id": native.get("preregistration_id"),
        "occurrence_index": native.get("occurrence_index"),
        "occurrence_role": native.get("occurrence_role"),
        "context_id": native.get("context_id"),
    }
    if content_id(CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_NATIVE_ACCOUNTING_V1_DOMAIN, identity) != occurrence_id:
        _fail("adaptive native occurrence identity changed")
    route_envelope = _exact(
        trace["route_input_envelope"],
        {
            "schema",
            "schema_version",
            "preregistration_id",
            "occurrence_id",
            "occurrence_index",
            "occurrence_role",
            "public_context",
            "catalogue",
            "catalogue_entries",
            "selected_reuse_result",
            "selected_reuse_present",
        },
        "adaptive route-input envelope",
    )
    route_input = canonical_json_bytes(route_envelope)
    if (
        native["schema"]
        != "acfqp.construction_k7_adaptive_occurrence_native_accounting.v1"
        or native["schema_version"] != "1.1.0"
        or native["route_input_envelope_retained_out_of_band"] is not True
        or native["same_window_native_events_present"] is not True
        or native["nonshared_counter_records_complete"] is not True
        or native["shared_resource_receipts_present"] is not False
        or native["formal_work_vectors_issued"] is not False
        or native["counter_completeness_gate_status"] != "NOT_RUN"
        or native["official_execution_allowed"] is not False
        or native.get("route_input_bytes_sha256")
        != hashlib.sha256(route_input).hexdigest()
        or native.get("route_input_byte_count") != len(route_input)
        or route_envelope["schema"]
        != "acfqp.construction_k7_adaptive_route_input_envelope.v1"
        or route_envelope["schema_version"] != "1.1.0"
        or route_envelope["preregistration_id"] != native["preregistration_id"]
        or route_envelope["occurrence_id"] != occurrence_id
        or route_envelope["occurrence_index"] != native["occurrence_index"]
        or route_envelope["occurrence_role"] != native["occurrence_role"]
        or route_envelope.get("public_context", {}).get("context_id")
        != native.get("context_id")
        or route_envelope.get("catalogue", {}).get("model_catalogue_id")
        != native.get("catalogue_id_before")
        or route_envelope["selected_reuse_present"]
        is not (native["result_outcome"] == "EXISTING_MODEL_REUSED")
        or (route_envelope["selected_reuse_result"] is not None)
        is not route_envelope["selected_reuse_present"]
    ):
        _fail("adaptive route-input envelope join changed")
    components = [
        _component(item, occurrence_id=occurrence_id, registry=registry)
        for item in _list(trace["native_components"], "native components")
    ]
    shared_events = [
        _event(item, occurrence_id=occurrence_id, registry=registry)
        for item in _list(trace["native_shared_events"], "native shared events")
    ]
    shared_event_ids_by_path: dict[str, list[str]] = {
        path_name: [] for path_name in SHARED_PATHS
    }
    for event_id, path_name, _value, _reducer in shared_events:
        shared_event_ids_by_path[path_name].append(event_id)
    for event_ids in shared_event_ids_by_path.values():
        event_ids.sort()
    if (
        native.get("component_ids") != [item[0] for item in components]
        or native.get("shared_native_event_ids") != [item[0] for item in shared_events]
        or tuple(item[1] for item in components)
        != {
            "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED": (
                "COMMON_PREFIX",
                "LOCAL_RECOVERY",
                "ABSTRACT_CERTIFICATE",
            ),
            "EXISTING_MODEL_REUSED": (
                "COMMON_PREFIX",
                "ABSTRACT_CERTIFICATE",
            ),
            "NO_CERTIFIABLE_CONSTRUCTOR": ("COMMON_PREFIX",),
        }[native["result_outcome"]]
    ):
        _fail("adaptive native occurrence child IDs changed")
    measurement_id, native_shared_values = _measurement(
        trace["shared_measurement"],
        occurrence_id=occurrence_id,
        route_input_bytes=route_input,
        shared_events=shared_events,
    )
    counter_set = _exact(
        docs["COUNTER_RECORD_SET"],
        {
            "artifact_role",
            "schema",
            "io.output_bytes",
            "shared_resource_receipt_set",
            "shared_resource_receipts",
            "path_aggregation_ids",
            "path_aggregations",
            "counter_record_ids",
            "counter_record_count",
        },
        "adaptive counter-record set",
    )
    receipts = [
        _receipt(
            item,
            occurrence_id=occurrence_id,
            measurement_id=measurement_id,
            registry=registry,
        )
        for item in _list(counter_set["shared_resource_receipts"], "shared receipts")
    ]
    if tuple(item[1] for item in receipts) != SHARED_PATHS:
        _fail("adaptive shared receipt path order changed")
    receipt_set = _exact(
        counter_set["shared_resource_receipt_set"],
        {
            "schema",
            "schema_version",
            "occurrence_id",
            "shared_measurement_id",
            "shared_resource_paths",
            "shared_resource_receipt_ids",
            "receipt_count",
            "all_nine_shared_paths_present",
            "official_execution_allowed",
            "shared_resource_receipt_set_id",
        },
        "adaptive shared receipt set",
    )
    receipt_set_payload = {
        key: value
        for key, value in receipt_set.items()
        if key != "shared_resource_receipt_set_id"
    }
    receipt_set_id = content_id(
        CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_SET_V1_DOMAIN,
        receipt_set_payload,
    )
    if (
        receipt_set["schema"]
        != "acfqp.construction_k7_adaptive_shared_receipt_set.v1"
        or receipt_set["schema_version"] != SCHEMA_VERSION
        or receipt_set["occurrence_id"] != occurrence_id
        or receipt_set["shared_measurement_id"] != measurement_id
        or receipt_set["shared_resource_paths"] != list(SHARED_PATHS)
        or receipt_set["shared_resource_receipt_ids"] != [item[0] for item in receipts]
        or receipt_set["receipt_count"] != 9
        or receipt_set["all_nine_shared_paths_present"] is not True
        or receipt_set["official_execution_allowed"] is not False
        or receipt_set["shared_resource_receipt_set_id"] != receipt_set_id
    ):
        _fail("adaptive shared receipt-set replay changed")
    aggregations = [
        _aggregation(item, occurrence_id=occurrence_id, registry=registry)
        for item in _list(counter_set["path_aggregations"], "path aggregations")
    ]
    if (
        tuple(item[1] for item in aggregations) != registry.required_paths
        or counter_set["path_aggregation_ids"] != [item[0] for item in aggregations]
    ):
        _fail("adaptive required path-aggregation inventory changed")
    work_doc = _exact(
        docs["WORK_VECTOR"],
        {"artifact_role", "schema", "io.output_bytes", "work_vector"},
        "adaptive WorkVector role",
    )
    vector = WorkVectorV1.from_dict(work_doc["work_vector"], registry)
    if (
        counter_set["schema"]
        != "acfqp.construction_k7_adaptive_counter_record_set.v1"
        or work_doc["schema"]
        != "acfqp.construction_k7_adaptive_work_vector_artifact.v1"
        or vector.subject_id != occurrence_id
        or counter_set["counter_record_ids"] != [row.record_id for row in vector.records]
        or counter_set["counter_record_count"] != len(vector.records)
        or len(vector.records) != registry_v7.EXPECTED_V7_REQUIRED_LEAF_COUNT
    ):
        _fail("adaptive WorkVector occurrence or record inventory changed")
    component_rows = [item[2] for item in components]
    receipt_values = {row[1]: row[2] for row in receipts}
    receipt_ids = {row[1]: row[0] for row in receipts}
    derived = _derived(native.get("result_outcome"), receipt_values["process.launches"])
    for aggregation, record in zip(aggregations, vector.records):
        identifier, path_name, value, component_ids, kind, source = aggregation
        rows = tuple(rows[path_name] for rows in component_rows if path_name in rows)
        if path_name in receipt_values:
            expected_value = receipt_values[path_name]
            expected_kind = "SHARED_RESOURCE_RECEIPT"
            expected_source = receipt_ids[path_name]
        elif path_name in derived:
            expected_value = derived[path_name]
            expected_kind = "SEMANTIC_DERIVED_RECONCILIATION"
            expected_source = occurrence_id
        elif registry.by_path[path_name].reducer is ReducerEnum.SUM:
            expected_value = sum(row.value for row in rows)
            expected_kind = "COMPONENT_SUM"
            expected_source = occurrence_id
        else:
            expected_value = max((row.value for row in rows), default=0)
            expected_kind = "COMPONENT_MAX"
            expected_source = occurrence_id
        if (
            value != expected_value
            or component_ids != tuple(row.record_id for row in rows)
            or kind != expected_kind
            or source != expected_source
            or record.path != path_name
            or record.value != value
            or record.recorder_id != identifier
        ):
            _fail("adaptive path aggregation differs from native sources")
    comparison_role = _exact(
        docs["COMPARISON_VECTOR"],
        {"artifact_role", "schema", "io.output_bytes", "comparison_vector", "route_choice_authority"},
        "adaptive ComparisonVector role",
    )
    projected = ComparisonVectorV1.from_dict(comparison_role["comparison_vector"])
    if (
        comparison_role["schema"]
        != "acfqp.construction_k7_adaptive_comparison_vector_artifact.v1"
        or comparison_role["route_choice_authority"] is not False
        or projected != _project(vector, comparison)
    ):
        _fail("adaptive ComparisonVector differs from exact V7 projection")
    proof_role = _exact(
        docs["ACTUAL_PROJECTION_PROOF"],
        {
            "artifact_role",
            "schema",
            "io.output_bytes",
            "actual_projection_proof",
            "all_operational_leaves_projected_exactly_once",
        },
        "adaptive projection-proof role",
    )
    proof = ActualProjectionProofV1.from_dict(proof_role["actual_projection_proof"])
    expected_scope = (
        ActualWorkScope.MARGINAL_ROUTE_AGGREGATE
        if vector.route_kind is RouteKindEnum.LOCAL_ATTEMPT
        else ActualWorkScope.COMMON_PREFIX
    )
    if (
        proof_role["schema"]
        != "acfqp.construction_k7_adaptive_projection_artifact.v1"
        or proof.actual_projection_profile_id != actual.actual_projection_profile_id
        or proof.counter_registry_id != registry.registry_id
        or proof.comparison_profile_id != comparison.comparison_profile_id
        or proof.work_vector_id != vector.work_vector_id
        or proof.comparison_vector_id != projected.comparison_vector_id
        or proof.source_lane is not LaneEnum.OPERATIONAL
        or proof.work_scope is not expected_scope
        or proof.projection_term_count != registry_v7.EXPECTED_V7_OPERATIONAL_LEAF_COUNT
        or proof_role["all_operational_leaves_projected_exactly_once"] is not True
    ):
        _fail("adaptive actual projection proof changed")
    business = _exact(
        docs["BUSINESS_RESULT"],
        {
            "artifact_role",
            "schema",
            "adaptive_native_occurrence_id",
            "synthesis_result_id",
            "result_outcome",
            "context_id",
            "catalogue_id_before",
            "catalogue_id_after",
            "route_kind",
        },
        "adaptive business result",
    )
    terminal = _exact(
        docs["TERMINAL_ARTIFACT"],
        {
            "artifact_role",
            "schema",
            "occurrence_id",
            "terminal_scope",
            "terminal_class",
            "terminal_code",
            "plan_certificate_present",
            "work_vector_id",
            "comparison_vector_id",
            "official_execution_allowed",
        },
        "adaptive terminal artifact",
    )
    certified = native["result_outcome"] != "NO_CERTIFIABLE_CONSTRUCTOR"
    expected_terminal = (
        ("PLAN_CERTIFICATE", "LOCAL_GROUND_RECOVERY")
        if vector.route_kind is RouteKindEnum.LOCAL_ATTEMPT
        else ("PLAN_CERTIFICATE", "ABSTRACT_CERTIFIED")
        if vector.route_kind is RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
        else ("ATTEMPT_CLOSURE_NONCERTIFICATE", "NO_CERTIFIABLE_CONSTRUCTOR")
    )
    if (
        business["schema"] != "acfqp.construction_k7_adaptive_business_result.v1"
        or business.get("adaptive_native_occurrence_id") != occurrence_id
        or business.get("synthesis_result_id") != native.get("synthesis_result_id")
        or business.get("result_outcome") != native.get("result_outcome")
        or business.get("context_id") != native.get("context_id")
        or business.get("catalogue_id_before") != native.get("catalogue_id_before")
        or business.get("catalogue_id_after") != native.get("catalogue_id_after")
        or business.get("route_kind") != vector.route_kind.value
        or terminal.get("occurrence_id") != occurrence_id
        or terminal.get("work_vector_id") != vector.work_vector_id
        or terminal.get("comparison_vector_id") != projected.comparison_vector_id
        or terminal["schema"] != "acfqp.construction_k7_adaptive_terminal_artifact.v1"
        or terminal["terminal_scope"] != "LOGICAL_OCCURRENCE_CONSTRUCTION"
        or (terminal["terminal_class"], terminal["terminal_code"])
        != expected_terminal
        or terminal["plan_certificate_present"] is not certified
        or terminal.get("official_execution_allowed") is not False
    ):
        _fail("adaptive business or terminal identity join changed")
    output_manifest = _exact(
        docs["OUTPUT_MANIFEST"],
        {
            "artifact_role",
            "schema",
            "occurrence_id",
            "output_bytes_fixed_point_profile_id",
            "io.output_bytes",
            "ordered_preceding_roles",
            "required_role_order",
        },
        "adaptive output manifest",
    )
    output_bytes = _nonnegative(output_manifest["io.output_bytes"], "output bytes")
    if (
        output_manifest["schema"]
        != "acfqp.construction_k7_adaptive_output_manifest.v1"
        or output_bytes <= 0
        or sum(len(raw[role]) for role in OUTPUT_ROLES) != output_bytes
    ):
        _fail("adaptive physical output bytes are not at a fixed point")
    if any(
        document.get("io.output_bytes") != output_bytes
        for role, document in docs.items()
        if role in {
            "COUNTER_RECORD_SET",
            "WORK_VECTOR",
            "COMPARISON_VECTOR",
            "ACTUAL_PROJECTION_PROOF",
            "OUTPUT_MANIFEST",
        }
    ):
        _fail("adaptive output-byte candidate differs across roles")
    preceding = _list(output_manifest["ordered_preceding_roles"], "manifest preceding roles")
    if (
        output_manifest["occurrence_id"] != occurrence_id
        or output_manifest["required_role_order"] != list(OUTPUT_ROLES)
        or [row.get("artifact_role") for row in preceding] != list(OUTPUT_ROLES[:-1])
        or any(
            set(row) != {"artifact_role", "byte_count", "bytes_sha256"}
            or row["byte_count"] != len(raw[row["artifact_role"]])
            or row["bytes_sha256"]
            != hashlib.sha256(raw[row["artifact_role"]]).hexdigest()
            for row in preceding
        )
    ):
        _fail("adaptive output manifest extent or digest changed")
    renderer_id = content_id(
        CONSTRUCTION_K7_ADAPTIVE_OUTPUT_RENDERER_V1_DOMAIN,
        {
            "occurrence_id": occurrence_id,
            "shared_measurement_id": measurement_id,
            "required_roles": list(OUTPUT_ROLES),
        },
    )
    profile = fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=renderer_id,
        execution_identity_id=occurrence_id,
        max_total_bytes=512 * 1024 * 1024,
        role_byte_caps={role: 256 * 1024 * 1024 for role in OUTPUT_ROLES},
        max_iterations=32,
    )
    if output_manifest["output_bytes_fixed_point_profile_id"] != profile.profile_id:
        _fail("adaptive output fixed-point profile changed")
    shared_expected = {
        **native_shared_values,
        "io.output_bytes": output_bytes,
        "io.mounted_bytes_peak": (
            native_shared_values["io.read_bytes"]
            + native_shared_values["io.staged_bytes"]
            + output_bytes
        ),
    }
    shared_expected["memory.working_bytes_peak"] = max(
        native_shared_values["memory.working_bytes_peak"],
        shared_expected["io.mounted_bytes_peak"],
    )
    if any(receipt_values[path_name] != shared_expected[path_name] for path_name in SHARED_PATHS):
        _fail("adaptive shared receipt values differ from complete-window sources")
    for (
        _receipt_id,
        path_name,
        value,
        native_event_ids,
        source_kind,
        source_evidence_id,
        fixed_point_profile_id,
    ) in receipts:
        expected_native_ids = shared_event_ids_by_path[path_name]
        if path_name == "io.output_bytes":
            expected_kind = "OUTPUT_FIXED_POINT"
            expected_source = profile.profile_id
            expected_profile: str | None = profile.profile_id
            expected_native_ids = []
        elif path_name == "io.mounted_bytes_peak":
            expected_kind = "DERIVED_MOUNTED_BYTES_UPPER"
            expected_source = measurement_id
            expected_profile = None
            expected_native_ids = []
        elif expected_native_ids:
            expected_kind = "NATIVE_EVENT_REDUCTION"
            expected_source = measurement_id
            expected_profile = None
        elif value == 0:
            expected_kind = "COMPLETE_WINDOW_ZERO_ATTESTATION"
            expected_source = measurement_id
            expected_profile = None
        else:  # pragma: no cover - every positive native source must have an event
            _fail("adaptive positive shared receipt has no native evidence")
        if (
            native_event_ids != expected_native_ids
            or source_kind != expected_kind
            or source_evidence_id != expected_source
            or fixed_point_profile_id != expected_profile
        ):
            _fail("adaptive shared receipt provenance changed")
    expected_row = EXPECTED_ROWS[native["occurrence_index"] - 1]
    if (
        (
            native["occurrence_index"],
            native["occurrence_role"],
            native["context_key"],
            native["result_outcome"],
            vector.route_kind.value,
        )
        != expected_row
    ):
        _fail("adaptive occurrence differs from the frozen campaign ordering")
    return AdaptiveOccurrenceIndependentVerificationV1(
        occurrence_id,
        native["occurrence_index"],
        native["occurrence_role"],
        vector.route_kind.value,
        receipt_set_id,
        vector.work_vector_id,
        projected.comparison_vector_id,
        proof.actual_projection_proof_id,
        output_bytes,
        tuple(hashlib.sha256(raw[role]).hexdigest() for role in OUTPUT_ROLES),
    )


@dataclass(frozen=True, slots=True)
class AdaptiveCampaignIndependentVerificationV1:
    occurrence_verifications: tuple[AdaptiveOccurrenceIndependentVerificationV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.occurrence_verifications) is not tuple
            or len(self.occurrence_verifications) != len(EXPECTED_ROWS)
            or tuple(
                (row.occurrence_index, row.occurrence_role, row.route_kind)
                for row in self.occurrence_verifications
            )
            != tuple(
                (index, role, route)
                for index, role, _context, _outcome, route in EXPECTED_ROWS
            )
        ):
            _fail("adaptive campaign independent verification order changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_campaign_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_verification_ids": [
                row.verification_id for row in self.occurrence_verifications
            ],
            "logical_occurrence_count": len(self.occurrence_verifications),
            "construct_count": 2,
            "abstract_reuse_count": 2,
            "unsupported_noncertificate_count": 1,
            "all_occurrence_native_event_graphs_replayed": True,
            "all_occurrence_formal_vectors_replayed": True,
            "all_output_fixed_points_replayed": True,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return content_id(CAMPAIGN_VERIFICATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "independent_verification_id": self.verification_id}


def verify_adaptive_campaign_directory_independently_v1(
    campaign_directory: str | Path,
) -> AdaptiveCampaignIndependentVerificationV1:
    root = Path(campaign_directory)
    if not root.is_dir() or root.is_symlink():
        _fail("adaptive campaign output root is not one physical directory")
    expected_names = tuple(
        f"{index:04d}-{role}"
        for index, role, _context, _outcome, _route in EXPECTED_ROWS
    )
    if tuple(sorted(row.name for row in root.iterdir())) != expected_names:
        _fail("adaptive campaign occurrence-directory inventory changed")
    results = tuple(
        verify_adaptive_occurrence_directory_independently_v1(root / name)
        for name in expected_names
    )
    traces = [
        loads_canonical_json((root / name / "OPERATIONAL_TRACE.json").read_bytes())
        for name in expected_names
    ]
    native = [row["native_occurrence"] for row in traces]
    if any(
        left["catalogue_id_after"] != right["catalogue_id_before"]
        for left, right in zip(native, native[1:])
    ):
        _fail("adaptive independently replayed catalogue lineage changed")
    return AdaptiveCampaignIndependentVerificationV1(results)


__all__ = (
    "AdaptiveCampaignIndependentVerificationV1",
    "AdaptiveOccurrenceIndependentVerificationV1",
    "ConstructionK7AdaptiveCampaignIndependentVerifierV1Error",
    "verify_adaptive_campaign_directory_independently_v1",
    "verify_adaptive_occurrence_directory_independently_v1",
)
