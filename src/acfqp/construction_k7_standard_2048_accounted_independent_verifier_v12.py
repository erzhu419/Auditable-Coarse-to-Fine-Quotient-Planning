"""Producer-free replay of V12 CounterRecords, vectors, and durable role bytes."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
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
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    derive_actual_projection_v1,
)
from acfqp import construction_accounting_registry_v8 as registry_v8
from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as pre
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
DOMAINS = pre.FUTURE_DOMAINS
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
ROLE_ORDER = fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
EXPECTED_PREDECESSOR_VERIFICATION_ID = (
    "d5e212e675bd2a2ed37d506ee871a1d6a65de5c8de3dd4c080086fffc7e59736"
)
EXPECTED_OPERATOR_BINDING_ID = (
    "d20ecf7186d8b37337e6c36212ac0aa7c9ee7f2b7e07f885d0c7e1cead330535"
)


class ConstructionK7Standard2048AccountedIndependentVerifierV12Error(
    RuntimeError
):
    """The campaign bytes or any retained accounting artifact changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AccountedIndependentVerifierV12Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048AccountedIndependentVerifierV12Error(
            f"{label} is not one exact content ID"
        ) from error


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048AccountedIndependentVerifierV12Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical object")
    return value


def _document_id(
    document: Mapping[str, Any], *, id_key: str, domain: str, label: str
) -> str:
    if type(document) is not dict or id_key not in document:
        _fail(f"{label} shape changed")
    identity = _cid(document[id_key], label)
    payload = {key: value for key, value in document.items() if key != id_key}
    if content_id(domain, payload) != identity:
        _fail(f"{label} identity changed")
    return identity


def _measurement_id(document: Mapping[str, Any]) -> str:
    return _document_id(
        document,
        id_key="accounting_measurement_id",
        domain=DOMAINS["measurement"],
        label="accounting measurement",
    )


def _expected_measurement(
    *,
    subject_id: str,
    segment_role: str,
    values: Mapping[str, int],
    allocation_profile: str,
) -> dict[str, Any]:
    registry = registry_v8.official_counter_registry_v8()
    payload = {
        "schema": "acfqp.standard_2048_accounting_measurement.v12",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "construction_k7_standard_2048_accounted_artifacts_v12",
        "accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "subject_id": subject_id,
        "measurement_window_role": segment_role,
        "allocation_profile": allocation_profile,
        "shared_resource_rows": [
            {
                "path": path,
                "value": values[path],
                "reducer": registry.by_path[path].reducer.value,
                "value_kind": "EXACT_OR_PREREGISTERED_VERIFIED_UPPER",
            }
            for path in SHARED_PATHS
        ],
        "all_nine_shared_paths_present": True,
        "native_zero_observed_not_inferred": True,
        "accounting_provenance_hashes_excluded": True,
        "complete_window_closed": True,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "accounting_measurement_id": content_id(DOMAINS["measurement"], payload),
    }


def _records(
    values: Mapping[str, int], *, subject_id: str, measurement_id: str
) -> tuple[CounterRecordV1, ...]:
    registry = registry_v8.official_counter_registry_v8()
    if set(values) != set(registry.by_path):
        _fail("counter values do not cover the exact V8 registry")
    return tuple(
        CounterRecordV1.observe(
            registry,
            path,
            values[path],
            recorder_id=(measurement_id if path in SHARED_PATHS else subject_id),
        )
        for path in sorted(values)
    )


def _chain(
    *,
    subject_id: str,
    route_kind: RouteKindEnum,
    work_scope: ActualWorkScope,
    values: Mapping[str, int],
    measurement_id: str,
) -> tuple[WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1]:
    registry = registry_v8.official_counter_registry_v8()
    comparison = registry_v8.official_comparison_profile_v8(registry)
    actual = registry_v8.official_actual_projection_profile_v8(
        registry, comparison
    )
    vector = WorkVectorV1(
        registry.registry_id,
        subject_id,
        route_kind,
        _records(values, subject_id=subject_id, measurement_id=measurement_id),
    )
    projected, proof = derive_actual_projection_v1(
        vector,
        registry,
        comparison,
        actual,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=work_scope,
    )
    return vector, projected, proof


def _segment_semantics(
    segment_role: str,
) -> tuple[RouteKindEnum, ActualWorkScope, str]:
    table = {
        "ABSTRACT_CERTIFIED_SELECTED_ROUTE": (
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
            "PER_DECISION_OUTPUT_ONLY_GLOBAL_PEAKS_ELSEWHERE",
        ),
        "FAILED_ABSTRACT_CERTIFICATE_COMMON_PREFIX": (
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            ActualWorkScope.COMMON_PREFIX,
            "PER_DECISION_OUTPUT_ONLY_GLOBAL_PEAKS_ELSEWHERE",
        ),
        "DIRECT_GROUND_FALLBACK_SELECTED_ROUTE": (
            RouteKindEnum.DIRECT_FALLBACK,
            ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,
            "PER_DECISION_OUTPUT_ONLY_GLOBAL_PEAKS_ELSEWHERE",
        ),
        "CAMPAIGN_BUILD_AND_ACCOUNTING_COMMON": (
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            ActualWorkScope.COMMON_PREFIX,
            "CAMPAIGN_GLOBAL_MOUNT_PEAK_PLUS_OWN_OUTPUT",
        ),
    }
    try:
        return table[segment_role]
    except KeyError as error:
        raise ConstructionK7Standard2048AccountedIndependentVerifierV12Error(
            "unknown operational segment role"
        ) from error


def _read_role_set(
    root: Path, output_key: str, seen: set[Path]
) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    directory = root / output_key
    if not directory.is_dir():
        _fail("output-key directory is absent")
    expected = {f"{role}.json" for role in ROLE_ORDER}
    actual = {path.name for path in directory.iterdir() if path.is_file()}
    if actual != expected:
        _fail("operational role file inventory changed")
    raw_by_role = {}
    doc_by_role = {}
    for role in ROLE_ORDER:
        path = directory / f"{role}.json"
        raw = path.read_bytes()
        document = _object(raw, f"{output_key}/{role}")
        if document.get("artifact_role") != role:
            _fail("role-labelled artifact changed roles")
        raw_by_role[role] = raw
        doc_by_role[role] = document
        seen.add(path.resolve())
    manifest = doc_by_role["OUTPUT_MANIFEST"]
    candidate = manifest.get("io.output_bytes")
    if type(candidate) is not int or candidate != sum(map(len, raw_by_role.values())):
        _fail("output manifest is not an exact byte fixed point")
    preceding = [
        {
            "artifact_role": role,
            "byte_count": len(raw_by_role[role]),
            "bytes_sha256": hashlib.sha256(raw_by_role[role]).hexdigest(),
        }
        for role in ROLE_ORDER[:-1]
    ]
    if (
        manifest.get("ordered_preceding_roles") != preceding
        or manifest.get("required_role_order") != list(ROLE_ORDER)
    ):
        _fail("output manifest inventory or digests changed")
    return raw_by_role, doc_by_role


def _static_role_bytes(
    *,
    subject_id: str,
    segment_role: str,
    business_document: Mapping[str, Any],
    trace_document: Mapping[str, Any],
    terminal_document: Mapping[str, Any],
) -> dict[str, bytes]:
    return {
        "BUSINESS_RESULT": canonical_json_bytes(
            {
                "artifact_role": "BUSINESS_RESULT",
                "schema": "acfqp.standard_2048_business_result.v12",
                "subject_id": subject_id,
                "segment_role": segment_role,
                "business_result": dict(business_document),
            }
        ),
        "OPERATIONAL_TRACE": canonical_json_bytes(
            {
                "artifact_role": "OPERATIONAL_TRACE",
                "schema": "acfqp.standard_2048_operational_trace.v12",
                "subject_id": subject_id,
                "segment_role": segment_role,
                "operational_trace": dict(trace_document),
                "accounting_provenance_hashes_excluded": True,
            }
        ),
        "TERMINAL_ARTIFACT": canonical_json_bytes(
            {
                "artifact_role": "TERMINAL_ARTIFACT",
                "schema": "acfqp.standard_2048_segment_terminal.v12",
                "subject_id": subject_id,
                "segment_role": segment_role,
                "terminal": dict(terminal_document),
            }
        ),
    }


def _output_commit(
    *,
    subject_id: str,
    output_key: str,
    fixed_point_id: str | None,
    raw_by_role: Mapping[str, bytes],
    evaluation_only: bool,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_output_commit.v12",
        "schema_version": SCHEMA_VERSION,
        "subject_id": subject_id,
        "output_key": output_key,
        "output_bytes_fixed_point_result_id": fixed_point_id,
        "role_rows": [
            {
                "artifact_role": role,
                "byte_count": len(raw),
                "bytes_sha256": hashlib.sha256(raw).hexdigest(),
            }
            for role, raw in raw_by_role.items()
        ],
        "evaluation_only": evaluation_only,
        "file_fsync_complete": True,
        "directory_fsync_complete": True,
        "committed_once": True,
        "path_independent_identity": True,
    }
    return {**payload, "output_commit_id": content_id(DOMAINS["output_commit"], payload)}


def _operational_render(
    *,
    subject_id: str,
    segment_role: str,
    base_values: Mapping[str, int],
    candidate: int,
    static_roles: Mapping[str, bytes],
    profile: fixed_v1.OutputBytesFixedPointProfileV1,
) -> tuple[dict[str, Any], WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1, dict[str, bytes]]:
    route_kind, work_scope, allocation = _segment_semantics(segment_role)
    values = dict(base_values)
    values["io.output_bytes"] = candidate
    if allocation == "CAMPAIGN_GLOBAL_MOUNT_PEAK_PLUS_OWN_OUTPUT":
        values["io.mounted_bytes_peak"] += candidate
    else:
        values["io.mounted_bytes_peak"] = max(
            values["io.mounted_bytes_peak"], candidate
        )
    measurement = _expected_measurement(
        subject_id=subject_id,
        segment_role=segment_role,
        values=values,
        allocation_profile=allocation,
    )
    vector, comparison, proof = _chain(
        subject_id=subject_id,
        route_kind=route_kind,
        work_scope=work_scope,
        values=values,
        measurement_id=measurement["accounting_measurement_id"],
    )
    roles = dict(static_roles)
    roles["COUNTER_RECORD_SET"] = canonical_json_bytes(
        {
            "artifact_role": "COUNTER_RECORD_SET",
            "schema": "acfqp.standard_2048_counter_record_set.v12",
            "subject_id": subject_id,
            "segment_role": segment_role,
            "io.output_bytes": candidate,
            "accounting_measurement": measurement,
            "counter_records": [row.to_dict() for row in vector.records],
            "counter_record_count": len(vector.records),
        }
    )
    roles["WORK_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "WORK_VECTOR",
            "schema": "acfqp.standard_2048_work_vector_artifact.v12",
            "io.output_bytes": candidate,
            "work_vector": vector.to_dict(),
        }
    )
    roles["COMPARISON_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "COMPARISON_VECTOR",
            "schema": "acfqp.standard_2048_comparison_vector_artifact.v12",
            "io.output_bytes": candidate,
            "comparison_vector": comparison.to_dict(),
            "route_choice_authority": False,
        }
    )
    roles["ACTUAL_PROJECTION_PROOF"] = canonical_json_bytes(
        {
            "artifact_role": "ACTUAL_PROJECTION_PROOF",
            "schema": "acfqp.standard_2048_projection_artifact.v12",
            "io.output_bytes": candidate,
            "actual_projection_proof": proof.to_dict(),
            "all_operational_leaves_projected_exactly_once": True,
        }
    )
    roles["OUTPUT_MANIFEST"] = canonical_json_bytes(
        {
            "artifact_role": "OUTPUT_MANIFEST",
            "schema": "acfqp.standard_2048_output_manifest.v12",
            "subject_id": subject_id,
            "segment_role": segment_role,
            "output_bytes_fixed_point_profile_id": profile.profile_id,
            "io.output_bytes": candidate,
            "ordered_preceding_roles": [
                {
                    "artifact_role": role,
                    "byte_count": len(raw),
                    "bytes_sha256": hashlib.sha256(raw).hexdigest(),
                }
                for role, raw in roles.items()
            ],
            "required_role_order": list(ROLE_ORDER),
        }
    )
    if tuple(roles) != ROLE_ORDER:
        _fail("independent renderer role order changed")
    return measurement, vector, comparison, proof, roles


def _verify_operational_bundle(
    *,
    root: Path,
    summary: Mapping[str, Any],
    seen: set[Path],
    subject_id: str,
    business_document: Mapping[str, Any],
    trace_document: Mapping[str, Any],
    terminal_document: Mapping[str, Any],
) -> tuple[WorkVectorV1, ComparisonVectorV1]:
    _cid(subject_id, "operational subject")
    segment_role = summary["segment_role"]
    raw_by_role, docs = _read_role_set(root, summary["output_key"], seen)
    expected_static = _static_role_bytes(
        subject_id=subject_id,
        segment_role=segment_role,
        business_document=business_document,
        trace_document=trace_document,
        terminal_document=terminal_document,
    )
    if any(raw_by_role[role] != raw for role, raw in expected_static.items()):
        _fail("durable operational source roles differ from campaign bytes")
    if any(
        docs[role]["subject_id"] != subject_id
        for role in ROLE_ORDER
        if "subject_id" in docs[role]
    ):
        _fail("operational role subject join changed")
    final_vector = WorkVectorV1.from_dict(
        docs["WORK_VECTOR"]["work_vector"],
        registry_v8.official_counter_registry_v8(),
    )
    candidate = sum(map(len, raw_by_role.values()))
    if final_vector.value("io.output_bytes") != candidate:
        _fail("work vector output bytes differ from committed role bytes")
    base_values = final_vector.values
    base_values["io.output_bytes"] = 0
    if segment_role == "CAMPAIGN_BUILD_AND_ACCOUNTING_COMMON":
        base_values["io.mounted_bytes_peak"] -= candidate
        if base_values["io.mounted_bytes_peak"] < 0:
            _fail("campaign mounted-byte base became negative")
    else:
        if base_values["io.mounted_bytes_peak"] != candidate:
            _fail("per-decision mounted-byte peak is not its exact output")
        base_values["io.mounted_bytes_peak"] = 0
    renderer_id = content_id(
        DOMAINS["output_renderer"],
        {
            "subject_id": subject_id,
            "segment_role": segment_role,
            "required_roles": list(ROLE_ORDER),
            "renderer_semantics": "STANDARD_2048_V12_OPERATIONAL_VECTOR_RENDERER",
        },
    )
    profile = fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=renderer_id,
        execution_identity_id=subject_id,
        max_total_bytes=64 * 1024 * 1024,
        max_iterations=32,
    )
    static_roles = {role: raw_by_role[role] for role in ROLE_ORDER[:3]}
    cache: dict[int, tuple[Any, ...]] = {}

    def renderer(value: int) -> dict[str, bytes]:
        row = cache.get(value)
        if row is None:
            row = _operational_render(
                subject_id=subject_id,
                segment_role=segment_role,
                base_values=base_values,
                candidate=value,
                static_roles=static_roles,
                profile=profile,
            )
            cache[value] = row
        return dict(row[4])

    fixed_point = fixed_v1.solve_output_bytes_fixed_point_v1(
        profile=profile, renderer=renderer
    )
    measurement, vector, comparison, proof, rendered = _operational_render(
        subject_id=subject_id,
        segment_role=segment_role,
        base_values=base_values,
        candidate=fixed_point.output_bytes,
        static_roles=static_roles,
        profile=profile,
    )
    if rendered != raw_by_role:
        _fail("independent operational renderer differs from committed bytes")
    commit = _output_commit(
        subject_id=subject_id,
        output_key=summary["output_key"],
        fixed_point_id=fixed_point.result_id,
        raw_by_role=raw_by_role,
        evaluation_only=False,
    )
    bundle_payload = {
        "schema": "acfqp.standard_2048_operational_counter_bundle.v12",
        "schema_version": SCHEMA_VERSION,
        "subject_id": subject_id,
        "segment_role": segment_role,
        "accounting_measurement": measurement,
        "work_vector": vector.to_dict(),
        "comparison_vector": comparison.to_dict(),
        "actual_projection_proof": proof.to_dict(),
        "output_bytes_fixed_point_result": fixed_point.to_document(),
        "output_commit": commit,
        "counter_record_count": len(vector.records),
        "counter_record_to_work_vector_to_comparison_vector_complete": True,
        "official_execution_allowed": False,
    }
    bundle_id = content_id(DOMAINS["counter_bundle"], bundle_payload)
    expected_summary = {
        "accounted_counter_bundle_id": bundle_id,
        "segment_role": segment_role,
        "accounting_measurement_id": measurement["accounting_measurement_id"],
        "work_vector_id": vector.work_vector_id,
        "comparison_vector_id": comparison.comparison_vector_id,
        "actual_projection_proof_id": proof.actual_projection_proof_id,
        "output_bytes_fixed_point_result_id": fixed_point.result_id,
        "output_commit_id": commit["output_commit_id"],
        "output_key": summary["output_key"],
        "io.output_bytes": fixed_point.output_bytes,
    }
    if dict(summary) != expected_summary:
        _fail("operational counter-bundle summary changed")
    return vector, comparison


def _verify_evaluation_bundle(
    *,
    root: Path,
    summary: Mapping[str, Any],
    seen: set[Path],
    expected_subject_id: str,
    expected_transport_id: str,
    expected_episode_index: int,
    expected_decision_index: int,
    expected_state: Mapping[str, Any],
    expected_action: str,
) -> WorkVectorV1:
    directory = root / summary["output_key"]
    expected_file = directory / "EVALUATION_WORK_VECTOR.json"
    if not directory.is_dir() or {path.name for path in directory.iterdir()} != {
        expected_file.name
    }:
        _fail("evaluation output inventory changed")
    raw = expected_file.read_bytes()
    seen.add(expected_file.resolve())
    document = _object(raw, "evaluation work vector")
    subject_id = _cid(document["subject_id"], "evaluation subject")
    if subject_id != expected_subject_id:
        _fail("evaluation subject differs from its business decision")
    registry = registry_v8.official_counter_registry_v8()
    vector = WorkVectorV1.from_dict(document["work_vector"], registry)
    if vector.subject_id != subject_id or any(
        vector.value(leaf.path) for leaf in registry.operational_leaves
    ):
        _fail("evaluation vector contains operational route work")
    transport = document["evaluation_transport"]
    transport_id = _document_id(
        transport,
        id_key="accounted_counter_bundle_id",
        domain=DOMAINS["counter_bundle"],
        label="evaluation transport",
    )
    transport_bytes = canonical_json_bytes(transport)
    if transport_id != expected_transport_id:
        _fail("evaluation transport differs from its matched business reference")
    if (
        transport.get("accounted_preregistration_id") != pre.PREREGISTRATION_ID
        or transport.get("episode_index") != expected_episode_index
        or transport.get("decision_index") != expected_decision_index
        or transport.get("state_before_decision") != expected_state
        or transport.get("selected_action") != expected_action
        or transport.get("selected_action_exact_value_and_loss_equivalent")
        is not True
        or transport.get("selected_action_label_identical") is not True
        or transport.get("operational_route_work_present") is not False
        or document.get("exact_plan") != transport.get("exact_plan")
        or document.get("forced_selected_action_exact_evaluation")
        != transport.get("forced_selected_action_exact_evaluation")
    ):
        _fail("evaluation exact evidence differs from its retained transport")
    base_values = transport.get("evaluation_counter_values")
    if type(base_values) is not dict or set(base_values) != set(registry.by_path):
        _fail("evaluation transport does not cover the exact counter registry")
    values = dict(base_values)
    for path in (
        "evaluation.hash_invocations",
        "evaluation.semantic_integrity_checks",
        "evaluation.semantic_protocol_checks",
    ):
        values[path] += 1
    values["evaluation.io_read_bytes"] = len(transport_bytes)
    candidate = len(transport_bytes)
    expected_raw = b""
    expected_measurement: dict[str, Any] = {}
    expected_vector: WorkVectorV1 | None = None
    evaluation_paths = {leaf.path for leaf in registry.evaluation_leaves}
    for _ in range(32):
        values["evaluation.io_output_bytes"] = candidate
        values["evaluation.io_mounted_bytes_peak"] = max(
            base_values["evaluation.io_mounted_bytes_peak"], candidate
        )
        values["evaluation.memory_working_bytes_peak"] = max(
            base_values["evaluation.memory_working_bytes_peak"],
            pre.EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER,
        )
        measurement_payload = {
            "schema": "acfqp.standard_2048_evaluation_measurement.v12",
            "schema_version": SCHEMA_VERSION,
            "subject_id": subject_id,
            "evaluation_lane_values": {
                leaf.path: values[leaf.path] for leaf in registry.evaluation_leaves
            },
            "evaluation_diagnostic_values": {
                leaf.path: values[leaf.path]
                for leaf in registry.leaves
                if leaf.path.startswith("evaluation.")
                and leaf.path not in evaluation_paths
            },
            "operational_route_values_zero": True,
            "accounting_provenance_hashes_excluded": True,
        }
        expected_measurement = {
            **measurement_payload,
            "accounting_measurement_id": content_id(
                DOMAINS["measurement"], measurement_payload
            ),
        }
        records = tuple(
            CounterRecordV1.observe(
                registry,
                path,
                values[path],
                recorder_id=(
                    expected_measurement["accounting_measurement_id"]
                    if path.startswith("evaluation.")
                    else subject_id
                ),
            )
            for path in sorted(values)
        )
        expected_vector = WorkVectorV1(
            registry.registry_id,
            subject_id,
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            records,
        )
        expected_document = {
            "artifact_role": "EVALUATION_WORK_VECTOR",
            "schema": "acfqp.standard_2048_evaluation_artifact.v12",
            "schema_version": SCHEMA_VERSION,
            "subject_id": subject_id,
            "evaluation.io_output_bytes": candidate,
            "evaluation_transport": transport,
            "accounting_measurement": expected_measurement,
            "exact_plan": transport["exact_plan"],
            "forced_selected_action_exact_evaluation": transport[
                "forced_selected_action_exact_evaluation"
            ],
            "work_vector": expected_vector.to_dict(),
            "comparison_vector_issued": False,
            "evaluation_lane_excluded_from_operational_route_vector": True,
        }
        expected_raw = canonical_json_bytes(expected_document)
        rendered = len(transport_bytes) + len(expected_raw)
        if rendered == candidate:
            break
        if rendered < candidate:
            _fail("evaluation output-byte fixed point decreased")
        candidate = rendered
    else:
        _fail("evaluation output-byte fixed point did not converge")
    if raw != expected_raw or vector != expected_vector:
        _fail("evaluation bytes differ from exact counter replay")
    measurement = document["accounting_measurement"]
    measurement_id = _measurement_id(measurement)
    if measurement != expected_measurement:
        _fail("evaluation measurement differs from exact replay")
    raw_by_role = {"EVALUATION_WORK_VECTOR": raw}
    commit = _output_commit(
        subject_id=subject_id,
        output_key=summary["output_key"],
        fixed_point_id=None,
        raw_by_role=raw_by_role,
        evaluation_only=True,
    )
    bundle_payload = {
        "schema": "acfqp.standard_2048_evaluation_counter_bundle.v12",
        "schema_version": SCHEMA_VERSION,
        "subject_id": subject_id,
        "accounting_measurement": measurement,
        "work_vector_id": vector.work_vector_id,
        "output_commit": commit,
        "canonical_byte_count": len(raw),
        "transport_output_byte_count": len(transport_bytes),
        "total_evaluation_output_byte_count": len(raw) + len(transport_bytes),
        "canonical_bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "evaluation_lane_excluded_from_operational_comparison": True,
        "comparison_vector_issued": False,
        "official_execution_allowed": False,
    }
    bundle_id = content_id(DOMAINS["counter_bundle"], bundle_payload)
    expected_summary = {
        "accounted_counter_bundle_id": bundle_id,
        "work_vector_id": vector.work_vector_id,
        "accounting_measurement_id": measurement_id,
        "output_commit_id": commit["output_commit_id"],
        "output_key": summary["output_key"],
        "evaluation.io.output_bytes": vector.value(
            "evaluation.io_output_bytes"
        ),
        "comparison_vector_issued": False,
    }
    if dict(summary) != expected_summary:
        _fail("evaluation bundle summary changed")
    return vector


def _verify_worker_chain(
    episode: Mapping[str, Any], operational_reply_bytes: int
) -> tuple[WorkVectorV1, ComparisonVectorV1]:
    subject_id = _document_id(
        episode["business_episode"],
        id_key="accounted_episode_id",
        domain=DOMAINS["episode"],
        label="business episode",
    )
    task = episode["worker_task"]
    task_id = _document_id(
        task,
        id_key="accounted_measurement_id",
        domain=DOMAINS["measurement"],
        label="worker task",
    )
    episode_index = episode.get("episode_index")
    decision_limit = task.get("decision_limit")
    if (
        type(episode_index) is not int
        or episode_index < 0
        or episode_index >= len(pre.PREREGISTERED_INITIAL_BOARDS)
        or type(decision_limit) is not int
        or decision_limit <= 0
        or decision_limit > pre.MAXIMUM_DECISIONS_PER_EPISODE
    ):
        _fail("worker task registered bounds changed")
    task_payload = {
        "schema": "acfqp.standard_2048_accounted_episode_task.v12",
        "schema_version": SCHEMA_VERSION,
        "accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_index": episode_index,
        "initial_board_ranks": list(
            pre.PREREGISTERED_INITIAL_BOARDS[episode_index]
        ),
        "execution_seed": pre.PREREGISTERED_EPISODE_SEEDS[episode_index],
        "decision_limit": decision_limit,
        "planning_horizon": pre.PLANNING_HORIZON,
        "operator_binding_expected": EXPECTED_OPERATOR_BINDING_ID,
        "evaluation_lane_separate_from_operational_route": True,
    }
    expected_task = {
        **task_payload,
        "accounted_measurement_id": content_id(
            DOMAINS["measurement"], task_payload
        ),
    }
    if task != expected_task or task_id != expected_task["accounted_measurement_id"]:
        _fail("worker task differs from preregistration")
    business_episode = episode["business_episode"]
    business_decision_count = business_episode.get("decision_count")
    if (
        type(business_decision_count) is not int
        or business_decision_count < 0
        or business_decision_count > decision_limit
        or business_episode.get("episode_index") != episode_index
        or business_episode.get("execution_seed")
        != pre.PREREGISTERED_EPISODE_SEEDS[episode_index]
        or business_episode.get("operator_binding_id")
        != EXPECTED_OPERATOR_BINDING_ID
        or business_episode.get("accounted_preregistration_id")
        != pre.PREREGISTRATION_ID
    ):
        _fail("worker business episode differs from its frozen task")
    measurement = episode["worker_accounting_measurement"]
    measurement_id = _measurement_id(measurement)
    registry = registry_v8.official_counter_registry_v8()
    vector = WorkVectorV1.from_dict(episode["worker_work_vector"], registry)
    comparison = ComparisonVectorV1.from_dict(episode["worker_comparison_vector"])
    proof = ActualProjectionProofV1.from_dict(
        episode["worker_actual_projection_proof"]
    )
    values = {path: 0 for path in registry.by_path}
    values.update(
        {
            "common.hash_invocations": 2,
            "common.integrity_checks": 2,
            "common.protocol_checks": 1,
            "io.read_bytes": len(canonical_json_bytes(task)),
            "io.output_bytes": operational_reply_bytes,
            "memory.working_bytes_peak": (
                pre.EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER
            ),
            "process.launches": 1,
            "process.exit_successes": 1,
        }
    )
    expected_measurement = _expected_measurement(
        subject_id=subject_id,
        segment_role="EPISODE_WORKER_PROCESS_AND_OPERATIONAL_PIPE",
        values=values,
        allocation_profile="ONE_FORKED_WORKER_TASK_AND_OPERATIONAL_REPLY",
    )
    expected_vector, expected_comparison, expected_proof = _chain(
        subject_id=subject_id,
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        values=values,
        measurement_id=expected_measurement["accounting_measurement_id"],
    )
    if (
        measurement != expected_measurement
        or measurement_id != expected_measurement["accounting_measurement_id"]
        or vector != expected_vector
        or comparison != expected_comparison
        or proof != expected_proof
    ):
        _fail("worker accounting chain differs from exact replay")
    return vector, comparison


def _accumulate(
    current: dict[str, int], comparison: ComparisonVectorV1
) -> dict[str, int]:
    profile = registry_v8.official_comparison_profile_v8()
    reducer = {row.name: row.reducer for row in profile.axes}
    result = dict(current)
    for axis, value in comparison.values:
        if reducer[axis] is ReducerEnum.SUM:
            result[axis] += value
        else:
            result[axis] = max(result[axis], value)
    return result


@dataclass(frozen=True, slots=True)
class Standard2048AccountedIndependentVerificationV12:
    campaign_id: str
    operational_work_vector_count: int
    evaluation_work_vector_count: int
    output_file_count: int

    @property
    def verification_id(self) -> str:
        payload = {
            "campaign_id": self.campaign_id,
            "operational_work_vector_count": self.operational_work_vector_count,
            "evaluation_work_vector_count": self.evaluation_work_vector_count,
            "output_file_count": self.output_file_count,
            "counter_record_vector_projection_replay_passed": True,
            "durable_output_byte_replay_passed": True,
            "producer_imported": False,
            "full_dynamics_semantic_replay_present": False,
            "official_execution_allowed": False,
        }
        return content_id(DOMAINS["verification"], payload)

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_accounted_independent_verification.v12",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "operational_work_vector_count": self.operational_work_vector_count,
            "evaluation_work_vector_count": self.evaluation_work_vector_count,
            "output_file_count": self.output_file_count,
            "counter_record_vector_projection_replay_passed": True,
            "durable_output_byte_replay_passed": True,
            "all_nine_shared_resource_paths_replayed": True,
            "producer_imported": False,
            "full_dynamics_semantic_replay_present": False,
            "counter_completeness_gate_status": "NOT_RUN",
            "official_execution_allowed": False,
            "independent_verification_id": self.verification_id,
        }


def verify_standard_2048_accounted_campaign_bundle_independently_v12(
    *, campaign_bytes: bytes, output_root: str | Path
) -> Standard2048AccountedIndependentVerificationV12:
    document = _object(campaign_bytes, "accounted campaign")
    campaign_id = _document_id(
        document,
        id_key="accounted_campaign_id",
        domain=DOMAINS["campaign"],
        label="accounted campaign",
    )
    expected_root_keys = {
        "schema",
        "schema_version",
        "profile_key",
        "accounted_preregistration_id",
        "predecessor_verification",
        "business_campaign",
        "episodes",
        "episode_count",
        "decision_count",
        "abstract_route_count",
        "fallback_route_count",
        "offline_transition_observation_count",
        "additional_model_acquisition_observation_count",
        "online_target_transition_observation_count",
        "operational_work_vector_count",
        "evaluation_work_vector_count",
        "campaign_counter_bundle",
        "vector_prefix_totals",
        "final_operational_comparison_totals",
        "evaluation_lane_totals",
        "all_selected_actions_exact_value_and_loss_equivalent",
        "full_standard_2048_game_completed",
        "tile_2048_reached",
        "maximum_final_board_tile_rank",
        "counter_record_to_work_vector_to_comparison_vector_complete",
        "all_nine_shared_resource_paths_closed",
        "evaluation_excluded_from_operational_route_vectors",
        "independent_complete_bundle_verifier_present",
        "broad_sample_efficiency_claimed",
        "total_operational_work_saving_claimed",
        "counter_completeness_gate_status",
        "workload_economics_gate_status",
        "official_execution_allowed",
        "official_scalar_cost",
        "official_N_break_even",
        "accounted_campaign_id",
    }
    if (
        set(document) != expected_root_keys
        or document.get("schema") != "acfqp.standard_2048_accounted_campaign.v12"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("profile_key") != pre.PROFILE_KEY
        or document.get("accounted_preregistration_id") != pre.PREREGISTRATION_ID
        or type(document.get("episodes")) is not list
        or not document.get("episodes")
        or len(document["episodes"]) > pre.EPISODE_WORKER_COUNT
        or document.get("counter_completeness_gate_status") != "NOT_RUN"
        or document.get("workload_economics_gate_status") != "NOT_RUN"
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("independent_complete_bundle_verifier_present") is not False
        or document.get("counter_record_to_work_vector_to_comparison_vector_complete")
        is not True
        or document.get("all_nine_shared_resource_paths_closed") is not True
        or document.get("evaluation_excluded_from_operational_route_vectors")
        is not True
        or document.get("broad_sample_efficiency_claimed") is not False
        or document.get("total_operational_work_saving_claimed") is not False
    ):
        _fail("accounted campaign lock or preregistration changed")
    predecessor = document.get("predecessor_verification")
    _document_id(
        predecessor,
        id_key="accounted_verification_id",
        domain=DOMAINS["verification"],
        label="predecessor verification binding",
    )
    if (
        predecessor.get("v169_independent_verification", {}).get(
            "independent_verification_id"
        )
        != EXPECTED_PREDECESSOR_VERIFICATION_ID
        or predecessor.get("v169_campaign_canonical_byte_count") != 431255
        or predecessor.get("v169_campaign_canonical_sha256")
        != "d23ae1212c073343ee63395c759bec7dfb08a65e8734f88c66ec137253238ee9"
        or predecessor.get("producer_and_independent_replay_byte_count_identical")
        is not True
        or predecessor.get("producer_and_independent_replay_sha256_identical")
        is not True
    ):
        _fail("predecessor byte-exact verification binding changed")
    business_campaign = document.get("business_campaign")
    business_campaign_id = _document_id(
        business_campaign,
        id_key="accounted_campaign_id",
        domain=DOMAINS["campaign"],
        label="business campaign",
    )
    root = Path(output_root)
    if not root.is_dir():
        _fail("accounted output root is absent")
    seen: set[Path] = set()
    operational: list[tuple[WorkVectorV1, ComparisonVectorV1]] = []
    evaluation: list[WorkVectorV1] = []
    total_decisions = 0
    total_abstract = 0
    total_fallback = 0
    for episode_ordinal, episode in enumerate(document["episodes"]):
        episode_id = _document_id(
            episode,
            id_key="accounted_episode_id",
            domain=DOMAINS["episode"],
            label="accounted episode",
        )
        business_episode = episode["business_episode"]
        business_episode_id = _document_id(
            business_episode,
            id_key="accounted_episode_id",
            domain=DOMAINS["episode"],
            label="business episode",
        )
        if (
            episode.get("episode_index") != episode_ordinal
            or business_episode.get("episode_index") != episode_ordinal
            or episode.get("business_episode_id") != business_episode_id
            or episode.get("decision_count") != len(episode.get("decisions", ()))
            or business_episode.get("decision_count")
            != len(business_episode.get("decisions", ()))
            or episode.get("decision_count") != business_episode.get("decision_count")
        ):
            _fail("episode/business-episode identity or cardinality changed")
        raw_episode = canonical_json_bytes(episode["business_episode"])
        operational.append(_verify_worker_chain(episode, len(raw_episode)))
        if len(episode["decisions"]) != len(business_episode["decisions"]):
            _fail("episode decision join changed")
        for decision_index, (decision, business_decision) in enumerate(
            zip(
                episode["decisions"],
                business_episode["decisions"],
                strict=True,
            )
        ):
            decision_id = _document_id(
                decision,
                id_key="accounted_decision_id",
                domain=DOMAINS["decision"],
                label="accounted decision",
            )
            business_decision_id = _document_id(
                business_decision,
                id_key="accounted_decision_id",
                domain=DOMAINS["decision"],
                label="business decision",
            )
            draft = business_decision["operational_draft"]
            route = draft["route"]
            if (
                decision.get("business_decision_id") != business_decision_id
                or decision.get("episode_index") != episode_ordinal
                or decision.get("decision_index") != decision_index
                or business_decision.get("decision_index") != decision_index
                or business_decision.get("episode_index") != episode_ordinal
                or business_decision.get("accounted_preregistration_id")
                != pre.PREREGISTRATION_ID
                or business_decision.get("evaluation_not_used_for_route_selection")
                is not True
                or decision.get("route") != route
                or decision.get("selected_action") != draft.get("selected_action")
                or decision.get(
                    "selected_action_exact_value_and_loss_equivalent"
                )
                is not True
                or draft.get("selected_action_exact_value_and_loss_equivalent")
                is not True
                or decision.get("evaluation_excluded_from_operational_comparison")
                is not True
                or decision.get("official_execution_allowed") is not False
            ):
                _fail("decision/business-decision join changed")
            summaries = decision["operational_counter_bundles"]
            if route == "ABSTRACT_CERTIFIED":
                if (
                    len(summaries) != 1
                    or summaries[0].get("segment_role")
                    != "ABSTRACT_CERTIFIED_SELECTED_ROUTE"
                    or summaries[0].get("output_key")
                    != (
                        f"episode-{episode_ordinal:04d}/"
                        f"decision-{decision_index:04d}/abstract"
                    )
                ):
                    _fail("abstract selected-route bundle sequence changed")
                operational.append(
                    _verify_operational_bundle(
                        root=root,
                        summary=summaries[0],
                        seen=seen,
                        subject_id=business_decision_id,
                        business_document=business_decision,
                        trace_document=draft,
                        terminal_document={
                            "terminal_scope": "LOGICAL_DECISION",
                            "terminal_class": "PLAN_CERTIFICATE",
                            "terminal_code": "ABSTRACT_CERTIFIED",
                        },
                    )
                )
                evaluation_summary = decision["evaluation_counter_bundle"]
                if evaluation_summary is None:
                    _fail("abstract selected route lost evaluation evidence")
                evaluation.append(
                    _verify_evaluation_bundle(
                        root=root,
                        summary=evaluation_summary,
                        seen=seen,
                        expected_subject_id=business_decision_id,
                        expected_transport_id=business_decision[
                            "matched_evaluation_transport_id"
                        ],
                        expected_episode_index=episode_ordinal,
                        expected_decision_index=decision_index,
                        expected_state=draft["state_before_decision"],
                        expected_action=draft["selected_action"],
                    )
                )
                total_abstract += 1
            elif route == "COLD_EXACT_DIRECT_GROUND_FALLBACK":
                expected_keys = (
                    (
                        "FAILED_ABSTRACT_CERTIFICATE_COMMON_PREFIX",
                        "common",
                    ),
                    (
                        "DIRECT_GROUND_FALLBACK_SELECTED_ROUTE",
                        "fallback",
                    ),
                )
                if len(summaries) != 2:
                    _fail("fallback route segment count changed")
                for summary, (role, suffix) in zip(
                    summaries, expected_keys, strict=True
                ):
                    if (
                        summary.get("segment_role") != role
                        or summary.get("output_key")
                        != (
                            f"episode-{episode_ordinal:04d}/"
                            f"decision-{decision_index:04d}/{suffix}"
                        )
                    ):
                        _fail("fallback route segment order changed")
                operational.append(
                    _verify_operational_bundle(
                        root=root,
                        summary=summaries[0],
                        seen=seen,
                        subject_id=business_decision_id,
                        business_document={
                            "certificate": draft["certificate"],
                            "route": route,
                        },
                        trace_document=draft,
                        terminal_document={
                            "terminal_scope": "NONTERMINAL_ROUTE_SEGMENT",
                            "terminal_class": "SEGMENT_CLOSURE_NONTERMINAL",
                            "terminal_code": (
                                "ABSTRACT_CERTIFICATE_FAILED_FALLBACK_PENDING"
                            ),
                        },
                    )
                )
                operational.append(
                    _verify_operational_bundle(
                        root=root,
                        summary=summaries[1],
                        seen=seen,
                        subject_id=business_decision_id,
                        business_document=business_decision,
                        trace_document=draft,
                        terminal_document={
                            "terminal_scope": "LOGICAL_DECISION",
                            "terminal_class": "PLAN_CERTIFICATE",
                            "terminal_code": "FULL_GROUND_FALLBACK",
                        },
                    )
                )
                if decision["evaluation_counter_bundle"] is not None:
                    _fail("fallback route acquired evaluation-only evidence")
                total_fallback += 1
            else:
                _fail("business decision used an unknown route")
            total_decisions += 1
        if (
            episode.get("abstract_route_count")
            != sum(row["route"] == "ABSTRACT_CERTIFIED" for row in episode["decisions"])
            or episode.get("fallback_route_count")
            != sum(
                row["route"] == "COLD_EXACT_DIRECT_GROUND_FALLBACK"
                for row in episode["decisions"]
            )
            or episode_id != episode["accounted_episode_id"]
        ):
            _fail("episode route aggregate changed")
    if (
        document.get("episode_count") != len(document["episodes"])
        or document.get("decision_count") != total_decisions
        or document.get("abstract_route_count") != total_abstract
        or document.get("fallback_route_count") != total_fallback
        or business_campaign.get("decision_count") != total_decisions
        or business_campaign.get("abstract_route_count") != total_abstract
        or business_campaign.get("fallback_route_count") != total_fallback
        or business_campaign.get("business_episode_ids")
        != [episode["business_episode_id"] for episode in document["episodes"]]
        or business_campaign.get("profile_key") != pre.PROFILE_KEY
        or business_campaign.get("accounted_preregistration_id")
        != pre.PREREGISTRATION_ID
        or business_campaign.get("predecessor_verification_id")
        != predecessor["accounted_verification_id"]
        or business_campaign.get("offline_transition_observation_count")
        != pre.OFFLINE_OBSERVATION_COUNT
        or business_campaign.get("additional_model_acquisition_observation_count")
        != 0
        or business_campaign.get("online_target_transition_observation_count")
        != total_decisions
        or document.get("offline_transition_observation_count")
        != pre.OFFLINE_OBSERVATION_COUNT
        or document.get("additional_model_acquisition_observation_count") != 0
        or document.get("online_target_transition_observation_count")
        != total_decisions
        or document.get("all_selected_actions_exact_value_and_loss_equivalent")
        is not True
        or business_campaign.get(
            "all_selected_actions_exact_value_and_loss_equivalent"
        )
        is not True
    ):
        _fail("campaign business aggregate changed")
    operational.append(
        _verify_operational_bundle(
            root=root,
            summary=document["campaign_counter_bundle"],
            seen=seen,
            subject_id=business_campaign_id,
            business_document=business_campaign,
            trace_document={
                "preregistration": pre.freeze_standard_2048_accounted_preregistration_v12().to_document(),
                "predecessor_verification": predecessor,
                "episodes": document["episodes"],
            },
            terminal_document={
                "terminal_scope": "REGISTERED_CAMPAIGN_EVIDENCE",
                "terminal_class": "CAMPAIGN_EVIDENCE_CLOSURE",
                "terminal_code": "REGISTERED_DECISION_LIMIT_EVIDENCE_COMPLETE",
            },
        )
    )
    all_files = {path.resolve() for path in root.rglob("*") if path.is_file()}
    if seen != all_files:
        _fail("output root contains missing or unreferenced files")
    if (
        len(operational) != document["operational_work_vector_count"]
        or len(evaluation) != document["evaluation_work_vector_count"]
    ):
        _fail("campaign vector cardinality changed")
    totals = {axis: 0 for axis in SHARED_AXES}
    expected_prefix = []
    for sequence_index, (vector, comparison) in enumerate(operational):
        totals = _accumulate(totals, comparison)
        expected_prefix.append(
            {
                "sequence_index": sequence_index,
                "work_vector_id": vector.work_vector_id,
                "comparison_vector_id": comparison.comparison_vector_id,
                "subject_id": vector.subject_id,
                "route_kind": vector.route_kind.value,
                "cumulative_axis_values": [
                    {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
                ],
            }
        )
    if (
        document["vector_prefix_totals"] != expected_prefix
        or document["final_operational_comparison_totals"]
        != [{"axis": axis, "value": totals[axis]} for axis in SHARED_AXES]
    ):
        _fail("campaign comparison prefix accumulation changed")
    registry = registry_v8.official_counter_registry_v8()
    evaluation_totals = {
        path: sum(vector.value(path) for vector in evaluation)
        for path in registry.by_path
        if path.startswith("evaluation.")
    }
    if document["evaluation_lane_totals"] != evaluation_totals:
        _fail("campaign evaluation-lane accumulation changed")
    return Standard2048AccountedIndependentVerificationV12(
        campaign_id,
        len(operational),
        len(evaluation),
        len(all_files),
    )


__all__ = (
    "ConstructionK7Standard2048AccountedIndependentVerifierV12Error",
    "Standard2048AccountedIndependentVerificationV12",
    "verify_standard_2048_accounted_campaign_bundle_independently_v12",
)
